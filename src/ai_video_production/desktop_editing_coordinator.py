"""TASK-036 coordinator joining Shell authority with minimum editing state.

This is still transport/toolkit neutral.  It converts EditingSessionState into a
real command allowlist and invalidates mutation confirmations whenever upstream
workflow identity changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .desktop_editing_session import EditingSessionState
from .desktop_shell import ShellApplicationService, ShellSnapshot


_ALWAYS_AVAILABLE = (
    "project.open",
    "project.create",
    "settings.read",
    "settings.update",
)


@dataclass(slots=True)
class DesktopEditingCoordinator:
    shell: ShellApplicationService
    state: EditingSessionState

    @classmethod
    def create(
        cls,
        *,
        product_version: str,
        project_id: str,
        display_name: str,
        token_factory: Any | None = None,
    ) -> "DesktopEditingCoordinator":
        shell = ShellApplicationService(product_version=product_version, token_factory=token_factory)
        state = EditingSessionState(project_id=project_id)
        value = cls(shell=shell, state=state)
        shell.bind_command_policy(value._policy)
        shell.open_project_context(project_id=project_id, display_name=display_name)
        value._sync_recommendation()
        return value

    def _policy(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*_ALWAYS_AVAILABLE, *self.state.available_commands())))

    def _sync_recommendation(self) -> None:
        self.shell.next_recommended_action = self.state.next_recommended_action

    def _advance(self, state: EditingSessionState, *, selection_changed: bool = False) -> EditingSessionState:
        self.state = state
        if selection_changed:
            self.shell.update_project_selection(selected_asset_id=state.source_asset_id)
        else:
            self.shell.advance_context_revision()
        self._sync_recommendation()
        return self.state

    def bind_source(self, *, asset_id: str, asset_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_source(asset_id=asset_id, asset_sha256=asset_sha256), selection_changed=True)

    def bind_transcript(self, transcript_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_transcript(transcript_sha256))

    def bind_subtitle_workspace(self, workspace_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_subtitle_workspace(workspace_sha256))

    def bind_cut_candidates(self, manifest_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_cut_candidates(manifest_sha256))

    def bind_edit_plan(self, *, plan_sha256: str, approved: bool) -> EditingSessionState:
        return self._advance(self.state.bind_edit_plan(plan_sha256=plan_sha256, approved=approved))

    def bind_resolve_assembly(self, assembly_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_resolve_assembly(assembly_sha256))

    def mark_resolve_applied(self) -> EditingSessionState:
        return self._advance(self.state.mark_resolve_applied())

    def bind_render_qa(self, *, report_sha256: str, status: str) -> EditingSessionState:
        return self._advance(self.state.bind_render_qa(report_sha256=report_sha256, status=status))

    def bind_handoff(self, manifest_sha256: str) -> EditingSessionState:
        return self._advance(self.state.bind_handoff(manifest_sha256))

    def snapshot(self) -> ShellSnapshot:
        return self.shell.snapshot()

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinator_version": "1.0.0",
            "task_owner": "TASK-036",
            "shell": self.shell.snapshot().to_dict(),
            "editing_session": self.state.to_dict(),
        }
