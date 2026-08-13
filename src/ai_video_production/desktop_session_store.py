"""TASK-036 crash-safe editing-shell checkpoint persistence.

Only canonical editing identities and presentation context are persisted. One-shot
confirmation tokens and background job objects are intentionally never serialized.
A durable checkpoint is allowed only while the Shell is quiescent; worker-specific
resume/reattach semantics remain owned by their respective task implementations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_editing_session import EditingSessionState
from .desktop_shell import WorkspaceId
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_CHECKPOINT_BYTES = 1024 * 1024


def _editing_state(raw: dict[str, Any]) -> EditingSessionState:
    try:
        return EditingSessionState(
            project_id=str(raw["project_id"]),
            revision=int(raw["revision"]),
            source_asset_id=raw.get("source_asset_id"),
            source_asset_sha256=raw.get("source_asset_sha256"),
            transcript_sha256=raw.get("transcript_sha256"),
            subtitle_workspace_sha256=raw.get("subtitle_workspace_sha256"),
            cut_candidate_manifest_sha256=raw.get("cut_candidate_manifest_sha256"),
            edit_plan_sha256=raw.get("edit_plan_sha256"),
            edit_plan_approved=bool(raw.get("edit_plan_approved", False)),
            resolve_assembly_sha256=raw.get("resolve_assembly_sha256"),
            resolve_applied=bool(raw.get("resolve_applied", False)),
            render_qa_sha256=raw.get("render_qa_sha256"),
            render_qa_status=raw.get("render_qa_status"),
            handoff_manifest_sha256=raw.get("handoff_manifest_sha256"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_EDITING_STATE_INVALID",
            "Desktop checkpoint contains an invalid editing session",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc


def _body(coordinator: DesktopEditingCoordinator) -> dict[str, Any]:
    shell = coordinator.shell.snapshot()
    if shell.project is None:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_PROJECT_REQUIRED",
            "A desktop checkpoint requires an open Project",
            ProductErrorCategory.STATE,
        )
    if shell.active_jobs:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_ACTIVE_JOBS",
            "Desktop checkpoint requires a quiescent Shell with no active background jobs",
            ProductErrorCategory.STATE,
            details={"active_job_ids": [item.job_id for item in shell.active_jobs]},
        )
    body: dict[str, Any] = {
        "checkpoint_version": "1.0.0",
        "task_owner": "TASK-036",
        "product_version": shell.product_version,
        "project": {
            "project_id": shell.project.project_id,
            "display_name": shell.project.display_name,
            "selected_asset_id": shell.project.selected_asset_id,
            "resolve_project_name": shell.project.resolve_project_name,
            "resolve_timeline_name": shell.project.resolve_timeline_name,
        },
        "workspace": shell.current_workspace.value,
        "editing_session": coordinator.state.to_dict(),
        "next_recommended_action": coordinator.state.next_recommended_action,
        "confirmation_tokens_persisted": False,
        "background_jobs_persisted": False,
        "host_paths_persisted": False,
    }
    body["checkpoint_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> tuple[str, str, WorkspaceId, EditingSessionState, dict[str, Any]]:
    if document.get("checkpoint_version") != "1.0.0":
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_VERSION",
            "Unsupported desktop checkpoint version",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    expected = document.get("checkpoint_sha256")
    body = {key: value for key, value in document.items() if key != "checkpoint_sha256"}
    actual = sha256_bytes(canonical_json_bytes(body))
    if expected != actual:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_CHECKSUM",
            "Desktop checkpoint checksum mismatch",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if (
        document.get("confirmation_tokens_persisted") is not False
        or document.get("background_jobs_persisted") is not False
        or document.get("host_paths_persisted") is not False
    ):
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_BOUNDARY",
            "Desktop checkpoint violates confirmation/job/path persistence boundaries",
            ProductErrorCategory.SECURITY,
        )
    project = document.get("project")
    if not isinstance(project, dict):
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_PROJECT_INVALID",
            "Desktop checkpoint Project record is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    try:
        project_id = str(project["project_id"])
        display_name = str(project["display_name"])
        workspace = WorkspaceId(str(document["workspace"]))
        product_version = str(document["product_version"])
    except (KeyError, ValueError) as exc:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_INVALID",
            "Desktop checkpoint contains invalid Shell metadata",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    if not project_id.strip() or not display_name.strip() or not product_version.strip():
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_INVALID",
            "Desktop checkpoint contains empty Shell identity fields",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    editing_raw = document.get("editing_session")
    if not isinstance(editing_raw, dict):
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_EDITING_STATE_INVALID",
            "Desktop checkpoint editing session must be an object",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    state = _editing_state(editing_raw)
    if state.project_id != project_id:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_PROJECT_MISMATCH",
            "Shell and editing-session Project identities do not match",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if project.get("selected_asset_id") != state.source_asset_id:
        raise ProductError(
            "ERR_SHELL_CHECKPOINT_ASSET_MISMATCH",
            "Shell selected Asset does not match the editing-session source Asset",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return product_version, display_name, workspace, state, project


class DesktopSessionCheckpointStore:
    @staticmethod
    def snapshot(coordinator: DesktopEditingCoordinator) -> dict[str, Any]:
        return _body(coordinator)

    @staticmethod
    def validate_document(document: dict[str, Any]) -> None:
        _parse(document)

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_FILE_INVALID",
                "Desktop checkpoint must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        size = target.stat().st_size
        if size <= 0 or size > _MAX_CHECKPOINT_BYTES:
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_SIZE",
                "Desktop checkpoint size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
                details={"size_bytes": size},
            )
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_READ",
                "Desktop checkpoint could not be read as UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_INVALID",
                "Desktop checkpoint root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        _parse(document)
        return document

    @staticmethod
    def save(
        path: str | Path,
        coordinator: DesktopEditingCoordinator,
        *,
        expected_previous_checkpoint_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_FILE_INVALID",
                "Refusing to replace a symlink desktop checkpoint",
                ProductErrorCategory.SECURITY,
            )
        if target.exists():
            if not target.is_file():
                raise ProductError(
                    "ERR_SHELL_CHECKPOINT_FILE_INVALID",
                    "Desktop checkpoint target must be a regular file",
                    ProductErrorCategory.VALIDATION,
                )
            if expected_previous_checkpoint_sha256 is None:
                raise ProductError(
                    "ERR_SHELL_CHECKPOINT_CAS_REQUIRED",
                    "Replacing an existing desktop checkpoint requires its exact previous checksum",
                    ProductErrorCategory.AUTHORIZATION,
                )
            current = DesktopSessionCheckpointStore.load_document(target)["checkpoint_sha256"]
            if current != expected_previous_checkpoint_sha256:
                raise ProductError(
                    "ERR_SHELL_CHECKPOINT_REVISION_CONFLICT",
                    "Desktop checkpoint changed before save; reload before retry",
                    ProductErrorCategory.STATE,
                    details={"current_checkpoint_sha256": current},
                )
        elif expected_previous_checkpoint_sha256 is not None:
            raise ProductError(
                "ERR_SHELL_CHECKPOINT_PREVIOUS_MISSING",
                "Expected previous desktop checkpoint does not exist",
                ProductErrorCategory.STATE,
            )
        document = _body(coordinator)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))

    @staticmethod
    def recover(path: str | Path, *, token_factory: Any | None = None) -> DesktopEditingCoordinator:
        document = DesktopSessionCheckpointStore.load_document(path)
        return DesktopSessionCheckpointStore.recover_document(document, token_factory=token_factory)

    @staticmethod
    def recover_document(
        document: dict[str, Any],
        *,
        token_factory: Any | None = None,
    ) -> DesktopEditingCoordinator:
        product_version, display_name, workspace, state, project = _parse(document)
        coordinator = DesktopEditingCoordinator.create(
            product_version=product_version,
            project_id=state.project_id,
            display_name=display_name,
            token_factory=token_factory,
        )
        coordinator.state = state
        if state.source_asset_id is not None:
            coordinator.shell.update_project_selection(selected_asset_id=state.source_asset_id)
        coordinator.shell.set_workspace(workspace)
        # Resolve names are presentation-only pointers. Rebind them by reopening
        # the Shell context without carrying old one-shot confirmations.
        if project.get("resolve_project_name") is not None or project.get("resolve_timeline_name") is not None:
            coordinator.shell.open_project_context(
                project_id=state.project_id,
                display_name=display_name,
                selected_asset_id=state.source_asset_id,
                resolve_project_name=project.get("resolve_project_name"),
                resolve_timeline_name=project.get("resolve_timeline_name"),
            )
            coordinator.shell.set_workspace(workspace)
        coordinator._sync_recommendation()
        return coordinator
