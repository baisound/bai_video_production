"""TASK-036 native media chooser -> ingest identity application-service boundary.

The chooser returns an ephemeral host path.  The path is captured only inside
this local call and is never placed into Shell durable state/Evidence.  Actual
secure ingest is delegated to an injected Product port so TASK-036 does not
reimplement TASK-003.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .task036_native_dialog import Task036NativeDialogService


@dataclass(frozen=True, slots=True)
class IngestedMediaIdentity:
    asset_id: str
    asset_sha256: str

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id must be non-empty")
        if not self.asset_sha256.startswith("sha256:") or len(self.asset_sha256) != 71:
            raise ValueError("asset_sha256 must be sha256:...")


class MediaIngestPort(Protocol):
    def ingest_local_media(self, source_path: Path) -> IngestedMediaIdentity: ...


@dataclass(slots=True)
class Task036MediaWorkflowFacade:
    coordinator: DesktopEditingCoordinator
    native_dialog: Task036NativeDialogService
    ingest_port: MediaIngestPort

    def choose_and_ingest(self) -> dict[str, Any]:
        selection = self.native_dialog.choose_media_source()
        if not selection.selected:
            return {
                "task_owner": "TASK-036",
                "operation": "MEDIA_CHOOSE_AND_INGEST",
                "status": "CANCELLED",
                "host_path_persisted": False,
                "ingest_started": False,
                "editing_session": self.coordinator.state.to_dict(),
            }
        assert selection.host_path is not None
        source_path = Path(selection.host_path)
        project = self.coordinator.shell.project
        if project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        command = ShellCommand(
            command_id=f"media-ingest-{project.context_revision}",
            command_type="media.choose_and_ingest",
            project_id=project.project_id,
            expected_context_revision=project.context_revision,
            payload={"source_name": source_path.name, "source_path_persisted": False},
        )

        runtime: dict[str, Any] = {}

        def execute(_: ShellCommand) -> Mapping[str, Any]:
            identity = self.ingest_port.ingest_local_media(source_path)
            runtime["identity"] = identity
            self.coordinator.bind_source(asset_id=identity.asset_id, asset_sha256=identity.asset_sha256)
            return {
                "asset_id": identity.asset_id,
                "asset_sha256": identity.asset_sha256,
                "source_name": source_path.name,
                "host_path_persisted": False,
            }

        receipt = self.coordinator.shell.dispatch(command, executor=execute)
        return {
            "task_owner": "TASK-036",
            "operation": "MEDIA_CHOOSE_AND_INGEST",
            "status": "INGESTED",
            "receipt": receipt,
            "host_path_persisted": False,
            "editing_session": self.coordinator.state.to_dict(),
            "available_commands": list(self.coordinator.shell.snapshot().available_commands),
            "next_recommended_action": self.coordinator.state.next_recommended_action,
        }
