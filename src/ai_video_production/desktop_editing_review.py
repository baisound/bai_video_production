"""TASK-036 human cut-review interaction and plan-approval bridge.

The module keeps candidate review in Product application state rather than in the
HTML surface.  A CUT/KEEP click is itself the explicit human decision; the shell
still issues and consumes a one-shot intent token inside that same user gesture,
so the UI does not need an additional confirmation dialog for every candidate.
Final Edit Plan approval remains a separate two-step summary/commit action.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .cut_candidates import CutCandidate, CutCandidateManifest
from .desktop_shell import ShellApplicationService, ShellCommand
from .edit_plan import CandidateReviewDecision, EditDecision, EditPlan, EditPlanService
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


def _candidate(manifest: CutCandidateManifest, candidate_id: str) -> CutCandidate:
    for item in manifest.candidates:
        if item.candidate_id == candidate_id:
            return item
    raise ProductError(
        "ERR_SHELL_CUT_CANDIDATE_NOT_FOUND",
        "The selected cut candidate is not part of the current manifest",
        ProductErrorCategory.STATE,
        details={"candidate_id": candidate_id},
    )


@dataclass(frozen=True, slots=True)
class ReviewWorkspaceState:
    manifest: CutCandidateManifest
    decisions: tuple[CandidateReviewDecision, ...] = ()
    selected_candidate_id: str | None = None
    playhead_us: int = 0
    target_duration_us: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.playhead_us <= self.manifest.source_duration_us:
            raise ValueError("playhead_us must be inside the source duration")
        if self.target_duration_us is not None and not 1 <= self.target_duration_us <= self.manifest.source_duration_us:
            raise ValueError("target_duration_us must be inside the source duration")
        valid_ids = {item.candidate_id for item in self.manifest.candidates}
        if self.selected_candidate_id is not None and self.selected_candidate_id not in valid_ids:
            raise ValueError("selected_candidate_id is not in the current manifest")
        seen: set[str] = set()
        for item in self.decisions:
            if item.candidate_id not in valid_ids:
                raise ValueError("review decision references an unknown candidate")
            if item.candidate_id in seen:
                raise ValueError("duplicate review decision")
            seen.add(item.candidate_id)

    @property
    def decision_map(self) -> dict[str, CandidateReviewDecision]:
        return {item.candidate_id: item for item in self.decisions}

    @property
    def unresolved_candidate_ids(self) -> tuple[str, ...]:
        reviewed = set(self.decision_map)
        return tuple(item.candidate_id for item in self.manifest.candidates if item.candidate_id not in reviewed)

    @property
    def review_sha256(self) -> str:
        body = {
            "review_state_version": "1.0.0",
            "manifest_sha256": self.manifest.to_dict()["manifest_sha256"],
            "target_duration_us": self.target_duration_us,
            "decisions": [
                {
                    "candidate_id": item.candidate_id,
                    "decision": item.decision.value,
                    "override_start_us": item.override_start_us,
                    "override_end_us": item.override_end_us,
                }
                for item in sorted(self.decisions, key=lambda value: value.candidate_id)
            ],
        }
        return sha256_bytes(canonical_json_bytes(body))

    def select_candidate(self, candidate_id: str) -> "ReviewWorkspaceState":
        item = _candidate(self.manifest, candidate_id)
        return replace(self, selected_candidate_id=item.candidate_id, playhead_us=item.start_us)

    def seek(self, playhead_us: int) -> "ReviewWorkspaceState":
        if not 0 <= playhead_us <= self.manifest.source_duration_us:
            raise ProductError(
                "ERR_SHELL_PLAYHEAD_OUT_OF_RANGE",
                "Playhead seek is outside the current source duration",
                ProductErrorCategory.VALIDATION,
                details={"source_duration_us": self.manifest.source_duration_us},
            )
        return replace(self, playhead_us=playhead_us)

    def decide(
        self,
        *,
        candidate_id: str,
        decision: EditDecision,
        override_start_us: int | None = None,
        override_end_us: int | None = None,
    ) -> "ReviewWorkspaceState":
        _candidate(self.manifest, candidate_id)
        review = CandidateReviewDecision(
            candidate_id=candidate_id,
            decision=decision,
            override_start_us=override_start_us,
            override_end_us=override_end_us,
        )
        values = [item for item in self.decisions if item.candidate_id != candidate_id]
        values.append(review)
        values.sort(key=lambda item: item.candidate_id)
        return replace(self, decisions=tuple(values), selected_candidate_id=candidate_id)

    def build_plan(self, *, approve: bool = False, approved_by: str | None = None) -> EditPlan:
        return EditPlanService.build(
            self.manifest,
            reviews=self.decisions,
            target_duration_us=self.target_duration_us,
            approve=approve,
            approved_by=approved_by,
        )

    def to_dict(self) -> dict[str, Any]:
        decision_map = self.decision_map
        candidates = []
        for item in self.manifest.candidates:
            review = decision_map.get(item.candidate_id)
            candidates.append(
                {
                    "candidate_id": item.candidate_id,
                    "kind": item.kind.value,
                    "start_us": item.start_us,
                    "end_us": item.end_us,
                    "strength_score": item.strength_score,
                    "evidence_codes": list(item.evidence_codes),
                    "review_state": "REVIEW" if review is None else review.decision.value,
                    "selected": item.candidate_id == self.selected_candidate_id,
                }
            )
        return {
            "review_workspace_version": "1.0.0",
            "task_owner": "TASK-036",
            "manifest_sha256": self.manifest.to_dict()["manifest_sha256"],
            "review_sha256": self.review_sha256,
            "selected_candidate_id": self.selected_candidate_id,
            "playhead_us": self.playhead_us,
            "target_duration_us": self.target_duration_us,
            "reviewed_count": len(self.decisions),
            "unresolved_count": len(self.unresolved_candidate_ids),
            "unresolved_candidate_ids": list(self.unresolved_candidate_ids),
            "candidates": candidates,
        }


class Task036ReviewFacade:
    """Bounded UI-facing review facade with human-intent token binding."""

    def __init__(self, shell: ShellApplicationService, state: ReviewWorkspaceState) -> None:
        self.shell = shell
        self.state = state
        self.approved_plan: EditPlan | None = None

    def _project_identity(self) -> tuple[str, int]:
        if self.shell.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        return self.shell.project.project_id, self.shell.project.context_revision

    @staticmethod
    def _intent_hash(payload: Mapping[str, Any]) -> str:
        return sha256_bytes(canonical_json_bytes(dict(payload)))

    def snapshot(self) -> dict[str, Any]:
        body = self.state.to_dict()
        body["approved_plan"] = None if self.approved_plan is None else {
            "plan_sha256": self.approved_plan.to_dict()["plan_sha256"],
            "projected_duration_us": self.approved_plan.projected_duration_us,
            "cut_count": len(self.approved_plan.cut_ranges),
            "keep_count": len(self.approved_plan.keep_ranges),
            "approval_state": self.approved_plan.approval_state,
        }
        return body

    def select_candidate(self, candidate_id: str) -> dict[str, Any]:
        self.state = self.state.select_candidate(candidate_id)
        return self.snapshot()

    def seek(self, playhead_us: int) -> dict[str, Any]:
        self.state = self.state.seek(playhead_us)
        return self.snapshot()

    def review_candidate(
        self,
        *,
        candidate_id: str,
        decision: str,
        override_start_us: int | None = None,
        override_end_us: int | None = None,
    ) -> dict[str, Any]:
        """Apply one explicit CUT/KEEP gesture without a redundant modal.

        The one-shot Shell confirmation is generated and consumed within this
        exact call.  It is bound to current review state and exact decision intent.
        """

        try:
            parsed_decision = EditDecision(decision)
        except ValueError as exc:
            raise ProductError(
                "ERR_SHELL_EDIT_DECISION_INVALID",
                "Candidate review decision must be CUT or KEEP",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if parsed_decision is EditDecision.REVIEW:
            raise ProductError(
                "ERR_SHELL_EDIT_DECISION_INVALID",
                "Candidate review decision must be CUT or KEEP",
                ProductErrorCategory.VALIDATION,
            )
        candidate = _candidate(self.state.manifest, candidate_id)
        if override_start_us is not None or override_end_us is not None:
            if parsed_decision is not EditDecision.CUT or override_start_us is None or override_end_us is None:
                raise ProductError(
                    "ERR_SHELL_CUT_OVERRIDE_INVALID",
                    "Cut range override requires a CUT decision and both range boundaries",
                    ProductErrorCategory.VALIDATION,
                )
            if override_start_us < candidate.start_us or override_end_us > candidate.end_us:
                raise ProductError(
                    "ERR_EDIT_PLAN_OVERRIDE_OUTSIDE_CANDIDATE",
                    "review override must stay within the source candidate range",
                    ProductErrorCategory.VALIDATION,
                    details={"candidate_id": candidate_id},
                )
        project_id, revision = self._project_identity()
        intent = {
            "candidate_id": candidate_id,
            "decision": parsed_decision.value,
            "override_start_us": override_start_us,
            "override_end_us": override_end_us,
            "review_sha256": self.state.review_sha256,
        }
        intent_hash = self._intent_hash(intent)
        upstream = {
            "candidate_manifest_sha256": self.state.manifest.to_dict()["manifest_sha256"],
            "review_sha256": self.state.review_sha256,
            "review_intent_sha256": intent_hash,
        }
        confirmation = self.shell.prepare_confirmation(
            command_type="edit_candidate.review",
            expected_upstream_hashes=upstream,
            target_application="BAI Video Production",
            target_project=project_id,
            destination=f"{candidate_id}:{parsed_decision.value}",
        )
        command = ShellCommand(
            command_id=f"review-{candidate_id}-{revision}",
            command_type="edit_candidate.review",
            project_id=project_id,
            expected_context_revision=revision,
            expected_upstream_hashes=upstream,
            payload=intent,
            confirmation_id=confirmation["confirmation_id"],
        )

        def execute(received: ShellCommand) -> Mapping[str, Any]:
            if self._intent_hash(received.payload) != intent_hash:
                raise ProductError(
                    "ERR_SHELL_REVIEW_INTENT_MISMATCH",
                    "Candidate review payload changed after authorization",
                    ProductErrorCategory.AUTHORIZATION,
                )
            self.state = self.state.decide(
                candidate_id=candidate.candidate_id,
                decision=parsed_decision,
                override_start_us=override_start_us,
                override_end_us=override_end_us,
            )
            self.approved_plan = None
            self.shell.advance_context_revision()
            return {
                "candidate_id": candidate.candidate_id,
                "decision": parsed_decision.value,
                "review_sha256": self.state.review_sha256,
                "unresolved_count": len(self.state.unresolved_candidate_ids),
            }

        receipt = self.shell.dispatch(command, executor=execute)
        return {"receipt": receipt, "review": self.snapshot()}

    def prepare_plan_approval(self) -> dict[str, Any]:
        if self.state.unresolved_candidate_ids:
            raise ProductError(
                "ERR_SHELL_EDIT_PLAN_REVIEW_INCOMPLETE",
                "Every cut candidate must be explicitly CUT or KEEP before plan approval",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"unresolved_count": len(self.state.unresolved_candidate_ids)},
            )
        draft = self.state.build_plan(approve=False)
        draft_dict = draft.to_dict()
        project_id, _ = self._project_identity()
        upstream = {
            "candidate_manifest_sha256": self.state.manifest.to_dict()["manifest_sha256"],
            "review_sha256": self.state.review_sha256,
            "draft_plan_sha256": draft_dict["plan_sha256"],
        }
        confirmation = self.shell.prepare_confirmation(
            command_type="edit_plan.approve",
            expected_upstream_hashes=upstream,
            target_application="BAI Video Production",
            target_project=project_id,
            destination="APPROVED_EDIT_PLAN",
        )
        return {
            **confirmation,
            "draft_plan_sha256": draft_dict["plan_sha256"],
            "projected_duration_us": draft.projected_duration_us,
            "cut_count": len(draft.cut_ranges),
            "keep_count": len(draft.keep_ranges),
            "review_sha256": self.state.review_sha256,
        }

    def approve_plan(self, *, confirmation_id: str, approved_by: str, draft_plan_sha256: str) -> dict[str, Any]:
        if not approved_by.strip():
            raise ProductError(
                "ERR_SHELL_EDIT_PLAN_APPROVER_REQUIRED",
                "Edit Plan approval requires a non-empty human approver identity",
                ProductErrorCategory.AUTHORIZATION,
            )
        if self.state.unresolved_candidate_ids:
            raise ProductError(
                "ERR_SHELL_EDIT_PLAN_REVIEW_INCOMPLETE",
                "Every cut candidate must be explicitly CUT or KEEP before plan approval",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        draft = self.state.build_plan(approve=False)
        actual_draft_hash = draft.to_dict()["plan_sha256"]
        if draft_plan_sha256 != actual_draft_hash:
            raise ProductError(
                "ERR_SHELL_EDIT_PLAN_DRAFT_STALE",
                "Edit Plan changed after the approval summary was prepared",
                ProductErrorCategory.STATE,
            )
        project_id, revision = self._project_identity()
        upstream = {
            "candidate_manifest_sha256": self.state.manifest.to_dict()["manifest_sha256"],
            "review_sha256": self.state.review_sha256,
            "draft_plan_sha256": actual_draft_hash,
        }
        command = ShellCommand(
            command_id=f"approve-plan-{revision}",
            command_type="edit_plan.approve",
            project_id=project_id,
            expected_context_revision=revision,
            expected_upstream_hashes=upstream,
            payload={"approved_by": approved_by.strip(), "draft_plan_sha256": actual_draft_hash},
            confirmation_id=confirmation_id,
        )

        def execute(_: ShellCommand) -> Mapping[str, Any]:
            plan = self.state.build_plan(approve=True, approved_by=approved_by.strip())
            self.approved_plan = plan
            self.shell.advance_context_revision()
            return {
                "plan_sha256": plan.to_dict()["plan_sha256"],
                "approval_state": plan.approval_state,
                "projected_duration_us": plan.projected_duration_us,
                "cut_count": len(plan.cut_ranges),
                "keep_count": len(plan.keep_ranges),
            }

        receipt = self.shell.dispatch(command, executor=execute)
        return {"receipt": receipt, "review": self.snapshot()}
