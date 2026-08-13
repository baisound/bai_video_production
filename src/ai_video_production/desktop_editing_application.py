"""TASK-036 integrated minimum-editing application service.

This module is the first bounded composition root for the desktop editing MVP.
It joins Shell stage authority, TASK-024/TASK-007 human cut review and the
transport-neutral NLE projection without invoking Resolve, rendering, paid
providers or any GUI toolkit.  Native/external mutation remains owned by the
existing task adapters and explicit Shell confirmation gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cut_candidates import CutCandidateManifest
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_editing_review import ReviewWorkspaceState, Task036ReviewFacade
from .desktop_shell_projection import DesktopEditingProjectionService, EditingProjection
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitle_workspace import SubtitleWorkspace
from .task036_view_model import Task036DesktopViewModel


def _workspace_sha256(workspace: SubtitleWorkspace) -> str:
    return sha256_bytes(canonical_json_bytes(workspace.to_dict()))


@dataclass(slots=True)
class Task036EditingApplication:
    """Compose the current minimum editing workflow into one application state.

    The application deliberately owns *coordination*, not provider execution.
    It makes one important contract real: after the human approves TASK-007,
    the Shell's stage authority advances to ``resolve.assembly.prepare`` rather
    than leaving the UI review state disconnected from the workflow state.
    """

    coordinator: DesktopEditingCoordinator
    cut_manifest: CutCandidateManifest
    review: Task036ReviewFacade
    subtitle_workspace: SubtitleWorkspace | None = None

    @classmethod
    def create(
        cls,
        *,
        product_version: str,
        project_id: str,
        display_name: str,
        source_asset_sha256: str,
        cut_manifest: CutCandidateManifest,
        subtitle_workspace: SubtitleWorkspace | None = None,
        token_factory: Any | None = None,
    ) -> "Task036EditingApplication":
        coordinator = DesktopEditingCoordinator.create(
            product_version=product_version,
            project_id=project_id,
            display_name=display_name,
            token_factory=token_factory,
        )
        coordinator.bind_source(asset_id=cut_manifest.source_asset_id, asset_sha256=source_asset_sha256)
        coordinator.bind_transcript(cut_manifest.transcript_manifest_sha256)
        if subtitle_workspace is not None:
            coordinator.bind_subtitle_workspace(_workspace_sha256(subtitle_workspace))
        coordinator.bind_cut_candidates(cut_manifest.to_dict()["manifest_sha256"])
        review = Task036ReviewFacade(coordinator.shell, ReviewWorkspaceState(cut_manifest))
        return cls(coordinator, cut_manifest, review, subtitle_workspace)

    @classmethod
    def from_pre_edit_results(
        cls,
        *,
        coordinator: DesktopEditingCoordinator,
        cut_manifest: CutCandidateManifest,
        subtitle_workspace: SubtitleWorkspace | None = None,
    ) -> "Task036EditingApplication":
        """Promote validated pre-edit artifacts into the Human cut-review app.

        This constructor never runs ASR/candidate detection.  It only accepts
        artifacts already bound to the same coordinator source/transcript and
        installs the exact Cut Candidate manifest identity when needed.
        """
        state = coordinator.state
        manifest_sha = cut_manifest.to_dict()["manifest_sha256"]
        if state.source_asset_id != cut_manifest.source_asset_id:
            raise ValueError("pre-edit Cut Candidate source does not match desktop source Asset")
        if (
            cut_manifest.transcript_manifest_sha256 is not None
            and state.transcript_sha256 != cut_manifest.transcript_manifest_sha256
        ):
            raise ValueError("pre-edit Cut Candidate transcript does not match desktop transcript")
        if state.cut_candidate_manifest_sha256 is None:
            coordinator.bind_cut_candidates(manifest_sha)
        elif state.cut_candidate_manifest_sha256 != manifest_sha:
            raise ValueError("desktop session already references a different Cut Candidate manifest")
        if subtitle_workspace is not None:
            workspace_sha = _workspace_sha256(subtitle_workspace)
            if coordinator.state.subtitle_workspace_sha256 is None:
                coordinator.bind_subtitle_workspace(workspace_sha)
            elif coordinator.state.subtitle_workspace_sha256 != workspace_sha:
                raise ValueError("desktop session already references a different Subtitle Workspace")
        review = Task036ReviewFacade(coordinator.shell, ReviewWorkspaceState(cut_manifest))
        return cls(coordinator, cut_manifest, review, subtitle_workspace)

    @classmethod
    def from_recovered(
        cls,
        *,
        coordinator: DesktopEditingCoordinator,
        cut_manifest: CutCandidateManifest,
        review_state: ReviewWorkspaceState,
        approved_by: str | None = None,
        subtitle_workspace: SubtitleWorkspace | None = None,
    ) -> "Task036EditingApplication":
        manifest_sha = cut_manifest.to_dict()["manifest_sha256"]
        if coordinator.state.cut_candidate_manifest_sha256 != manifest_sha:
            raise ValueError("recovered editing state does not match the supplied Cut Candidate manifest")
        review = Task036ReviewFacade(coordinator.shell, review_state)
        if coordinator.state.edit_plan_approved:
            if not approved_by:
                raise ValueError("approved recovered Edit Plan requires approved_by")
            plan = review_state.build_plan(approve=True, approved_by=approved_by)
            if plan.to_dict()["plan_sha256"] != coordinator.state.edit_plan_sha256:
                raise ValueError("recovered Edit Plan identity does not match review decisions")
            review.approved_plan = plan
        return cls(coordinator, cut_manifest, review, subtitle_workspace)

    @property
    def shell(self):
        return self.coordinator.shell

    def draft_plan(self):
        """Return the deterministic current draft, including unresolved REVIEW nodes."""

        return self.review.state.build_plan(approve=False)

    def projection(self) -> EditingProjection:
        # The draft is intentional: CUT/KEEP gestures become visible immediately
        # while unresolved candidates remain REVIEW.  Approval state is separate.
        plan = self.review.approved_plan or self.draft_plan()
        return DesktopEditingProjectionService.build(
            source_duration_us=self.cut_manifest.source_duration_us,
            subtitle_workspace=self.subtitle_workspace,
            cut_candidates=self.cut_manifest.candidates,
            edit_plan=plan,
        )

    def view_model(self) -> dict[str, Any]:
        return Task036DesktopViewModel(self.shell.snapshot(), self.projection()).to_dict()

    def snapshot(self) -> dict[str, Any]:
        return {
            "application_state_version": "1.0.0",
            "task_owner": "TASK-036",
            "coordinator": self.coordinator.to_dict(),
            "review": self.review.snapshot(),
            "view_model": self.view_model(),
        }

    def select_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self.review.select_candidate(candidate_id)

    def seek(self, playhead_us: int) -> dict[str, Any]:
        return self.review.seek(playhead_us)

    def review_candidate(
        self,
        *,
        candidate_id: str,
        decision: str,
        override_start_us: int | None = None,
        override_end_us: int | None = None,
    ) -> dict[str, Any]:
        return self.review.review_candidate(
            candidate_id=candidate_id,
            decision=decision,
            override_start_us=override_start_us,
            override_end_us=override_end_us,
        )

    def prepare_edit_plan_approval(self) -> dict[str, Any]:
        return self.review.prepare_plan_approval()

    def approve_edit_plan(
        self,
        *,
        confirmation_id: str,
        draft_plan_sha256: str,
        approved_by: str,
    ) -> dict[str, Any]:
        result = self.review.approve_plan(
            confirmation_id=confirmation_id,
            approved_by=approved_by,
            draft_plan_sha256=draft_plan_sha256,
        )
        assert self.review.approved_plan is not None
        plan_sha = self.review.approved_plan.to_dict()["plan_sha256"]
        # This is the critical cross-service transition: the human-approved plan
        # becomes the coordinator's canonical stage identity.  It also invalidates
        # stale downstream confirmation tokens through the coordinator.
        self.coordinator.bind_edit_plan(plan_sha256=plan_sha, approved=True)
        return {
            **result,
            "editing_session": self.coordinator.state.to_dict(),
            "available_commands": list(self.shell.snapshot().available_commands),
            "next_recommended_action": self.coordinator.state.next_recommended_action,
        }
