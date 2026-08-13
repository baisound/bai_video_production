"""TASK-036 crash-safe checkpoint for the integrated editing application.

Unlike the Shell-only checkpoint, this store also preserves in-progress human
CUT/KEEP review decisions.  It never persists one-shot confirmation tokens,
background jobs, arbitrary host paths or media bytes.  Recovery requires the
caller's current canonical Cut Candidate manifest and rejects identity drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .cut_candidates import CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_review import ReviewWorkspaceState
from .desktop_session_store import DesktopSessionCheckpointStore
from .edit_plan import CandidateReviewDecision, EditDecision
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitle_workspace import SubtitleWorkspace


_MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024


def _review_body(application: Task036EditingApplication) -> dict[str, Any]:
    state = application.review.state
    approved = application.review.approved_plan
    return {
        "manifest_sha256": application.cut_manifest.to_dict()["manifest_sha256"],
        "review_sha256": state.review_sha256,
        "selected_candidate_id": state.selected_candidate_id,
        "playhead_us": state.playhead_us,
        "target_duration_us": state.target_duration_us,
        "decisions": [
            {
                "candidate_id": item.candidate_id,
                "decision": item.decision.value,
                "override_start_us": item.override_start_us,
                "override_end_us": item.override_end_us,
            }
            for item in state.decisions
        ],
        "approved_plan_sha256": None if approved is None else approved.to_dict()["plan_sha256"],
        "approved_by": None if approved is None else approved.approved_by,
    }


def _document(application: Task036EditingApplication) -> dict[str, Any]:
    shell_checkpoint = DesktopSessionCheckpointStore.snapshot(application.coordinator)
    body: dict[str, Any] = {
        "application_checkpoint_version": "1.0.0",
        "task_owner": "TASK-036",
        "shell_checkpoint": shell_checkpoint,
        "review_checkpoint": _review_body(application),
        "confirmation_tokens_persisted": False,
        "background_jobs_persisted": False,
        "host_paths_persisted": False,
        "media_bytes_persisted": False,
    }
    body["application_checkpoint_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _validated(document: dict[str, Any]) -> None:
    if document.get("application_checkpoint_version") != "1.0.0":
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_VERSION",
            "Unsupported integrated desktop checkpoint version",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    expected = document.get("application_checkpoint_sha256")
    body = {key: value for key, value in document.items() if key != "application_checkpoint_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_CHECKSUM",
            "Integrated desktop checkpoint checksum mismatch",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    for key in (
        "confirmation_tokens_persisted",
        "background_jobs_persisted",
        "host_paths_persisted",
        "media_bytes_persisted",
    ):
        if document.get(key) is not False:
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_BOUNDARY",
                "Integrated desktop checkpoint violates persistence boundaries",
                ProductErrorCategory.SECURITY,
                details={"field": key},
            )
    if not isinstance(document.get("shell_checkpoint"), dict) or not isinstance(document.get("review_checkpoint"), dict):
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_INVALID",
            "Integrated desktop checkpoint sections are invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    DesktopSessionCheckpointStore.validate_document(document["shell_checkpoint"])


def _review_state(raw: dict[str, Any], manifest: CutCandidateManifest) -> tuple[ReviewWorkspaceState, str | None]:
    manifest_sha = manifest.to_dict()["manifest_sha256"]
    if raw.get("manifest_sha256") != manifest_sha:
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_MANIFEST_MISMATCH",
            "Checkpoint review state does not match the supplied Cut Candidate manifest",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    try:
        decisions = tuple(
            CandidateReviewDecision(
                candidate_id=str(item["candidate_id"]),
                decision=EditDecision(str(item["decision"])),
                override_start_us=item.get("override_start_us"),
                override_end_us=item.get("override_end_us"),
            )
            for item in raw.get("decisions", [])
        )
        state = ReviewWorkspaceState(
            manifest=manifest,
            decisions=decisions,
            selected_candidate_id=raw.get("selected_candidate_id"),
            playhead_us=int(raw.get("playhead_us", 0)),
            target_duration_us=raw.get("target_duration_us"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_REVIEW_INVALID",
            "Checkpoint contains invalid cut-review state",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    if state.review_sha256 != raw.get("review_sha256"):
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_REVIEW_HASH",
            "Checkpoint cut-review hash does not match reconstructed decisions",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    approved_by = raw.get("approved_by")
    approved_hash = raw.get("approved_plan_sha256")
    if (approved_by is None) != (approved_hash is None):
        raise ProductError(
            "ERR_SHELL_APPLICATION_CHECKPOINT_APPROVAL_INVALID",
            "Checkpoint approved plan identity is incomplete",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if approved_by is not None:
        if not str(approved_by).strip():
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_APPROVAL_INVALID",
                "Checkpoint approved_by is empty",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        plan = state.build_plan(approve=True, approved_by=str(approved_by))
        if plan.to_dict()["plan_sha256"] != approved_hash:
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_APPROVAL_HASH",
                "Checkpoint approved Edit Plan does not match the review decisions",
                ProductErrorCategory.DATA_INTEGRITY,
            )
    return state, None if approved_by is None else str(approved_by)


class DesktopEditingApplicationCheckpointStore:
    @staticmethod
    def snapshot(application: Task036EditingApplication) -> dict[str, Any]:
        return _document(application)

    @staticmethod
    def validate_document(document: dict[str, Any]) -> None:
        _validated(document)

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_FILE_INVALID",
                "Integrated desktop checkpoint must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        size = target.stat().st_size
        if size <= 0 or size > _MAX_CHECKPOINT_BYTES:
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_SIZE",
                "Integrated desktop checkpoint size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
                details={"size_bytes": size},
            )
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_READ",
                "Integrated desktop checkpoint could not be read as UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_INVALID",
                "Integrated desktop checkpoint root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        _validated(document)
        return document

    @staticmethod
    def save(
        path: str | Path,
        application: Task036EditingApplication,
        *,
        expected_previous_checkpoint_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_FILE_INVALID",
                "Refusing to replace a symlink integrated desktop checkpoint",
                ProductErrorCategory.SECURITY,
            )
        if target.exists():
            if not target.is_file():
                raise ProductError(
                    "ERR_SHELL_APPLICATION_CHECKPOINT_FILE_INVALID",
                    "Integrated desktop checkpoint target must be a regular file",
                    ProductErrorCategory.VALIDATION,
                )
            if expected_previous_checkpoint_sha256 is None:
                raise ProductError(
                    "ERR_SHELL_APPLICATION_CHECKPOINT_CAS_REQUIRED",
                    "Replacing an integrated desktop checkpoint requires its exact previous checksum",
                    ProductErrorCategory.AUTHORIZATION,
                )
            current = DesktopEditingApplicationCheckpointStore.load_document(target)["application_checkpoint_sha256"]
            if current != expected_previous_checkpoint_sha256:
                raise ProductError(
                    "ERR_SHELL_APPLICATION_CHECKPOINT_REVISION_CONFLICT",
                    "Integrated desktop checkpoint changed before save; reload before retry",
                    ProductErrorCategory.STATE,
                )
        return AtomicJsonWriter.write(target, _document(application))

    @staticmethod
    def recover(
        path: str | Path,
        *,
        cut_manifest: CutCandidateManifest,
        subtitle_workspace: SubtitleWorkspace | None = None,
        token_factory: Any | None = None,
    ) -> Task036EditingApplication:
        document = DesktopEditingApplicationCheckpointStore.load_document(path)
        coordinator = DesktopSessionCheckpointStore.recover_document(
            document["shell_checkpoint"],
            token_factory=token_factory,
        )
        review_state, approved_by = _review_state(document["review_checkpoint"], cut_manifest)
        try:
            return Task036EditingApplication.from_recovered(
                coordinator=coordinator,
                cut_manifest=cut_manifest,
                review_state=review_state,
                approved_by=approved_by,
                subtitle_workspace=subtitle_workspace,
            )
        except ValueError as exc:
            raise ProductError(
                "ERR_SHELL_APPLICATION_CHECKPOINT_CROSS_STATE_MISMATCH",
                "Integrated checkpoint workflow identities are inconsistent",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
