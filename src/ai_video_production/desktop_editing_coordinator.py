"""TASK-036 coordinator joining Shell authority with minimum editing state.

This is still transport/toolkit neutral.  It converts EditingSessionState into a
real command allowlist and invalidates mutation confirmations whenever upstream
workflow identity changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from .desktop_editing_session import EditingSessionState
from .desktop_shell import ShellApplicationService, ShellSnapshot
from .errors import ProductError, ProductErrorCategory


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
    _state_lock: RLock

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
        value = cls(shell=shell, state=state, _state_lock=RLock())
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
        with self._state_lock:
            return self._advance(self.state.bind_source(asset_id=asset_id, asset_sha256=asset_sha256), selection_changed=True)

    def bind_transcript(self, transcript_sha256: str) -> EditingSessionState:
        with self._state_lock:
            return self._advance(self.state.bind_transcript(transcript_sha256))

    def bind_transcript_if_current(
        self,
        transcript_sha256: str,
        *,
        expected_project_id: str,
        expected_revision: int,
        expected_source_asset_id: str,
        expected_source_asset_sha256: str,
        expected_context_revision: int,
    ) -> EditingSessionState:
        """Atomically compare the full pre-edit coordinate and bind Transcript."""

        with self._state_lock:
            project = self.shell.project
            state = self.state
            if (
                state.project_id != expected_project_id
                or state.revision != expected_revision
                or state.source_asset_id != expected_source_asset_id
                or state.source_asset_sha256 != expected_source_asset_sha256
                or state.next_recommended_action != "transcription.start"
                or project is None
                or project.project_id != expected_project_id
                or project.context_revision != expected_context_revision
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE",
                    "Editing source changed before Transcript binding",
                    ProductErrorCategory.STATE,
                )
            return self._advance(state.bind_transcript(transcript_sha256))

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
