"""TASK-040 Human-authorized regeneration planning without Provider execution.

A generated Candidate can pass the Provider transport layer and still fail Human
or Visual audit.  This planner joins that Human NEEDS_REGENERATION decision with
Prompt/Attempt lineage and chooses the *next control strategy* without starting
any paid/local generation, creating media, or mutating the Prompt Registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision
from .errors import ProductError, ProductErrorCategory
from .production_control import ProductionControlRegistry, SlotStatus
from .prompt_registry import PromptGenerationRegistry, RegenerationStrategy
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class RegenerationPlan:
    candidate_id: str
    slot_id: str
    parent_attempt_id: str
    parent_prompt_id: str
    parent_prompt_version: int
    current_strategy: RegenerationStrategy
    next_strategy: RegenerationStrategy
    failure_codes: tuple[str, ...]
    same_failure_streak: int
    repeated_failure_threshold: int

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-040",
            "candidate_id": self.candidate_id,
            "slot_id": self.slot_id,
            "parent_attempt_id": self.parent_attempt_id,
            "parent_prompt_id": self.parent_prompt_id,
            "parent_prompt_version": self.parent_prompt_version,
            "current_strategy": int(self.current_strategy),
            "next_strategy": int(self.next_strategy),
            "failure_codes": list(self.failure_codes),
            "same_failure_streak": self.same_failure_streak,
            "repeated_failure_threshold": self.repeated_failure_threshold,
            "requires_new_prompt_version": True,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "automatic_candidate_creation": False,
            "human_regeneration_authority_present": True,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class HumanRegenerationPlanner:
    @staticmethod
    def _human_regeneration_decision(audits: CandidateAuditRegistry, candidate_id: str):
        decisions = [item for item in audits.decisions.values() if item.candidate_id == candidate_id]
        if len(decisions) != 1 or decisions[0].decision is not HumanCandidateDecision.NEEDS_REGENERATION:
            raise ProductError(
                "ERR_REGENERATION_HUMAN_DECISION_REQUIRED",
                "Regeneration planning requires exactly one Human NEEDS_REGENERATION decision",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"decision_count": len(decisions)},
            )
        return decisions[0]

    @classmethod
    def compile(
        cls,
        *,
        candidate_id: str,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        prompts: PromptGenerationRegistry,
        repeated_failure_threshold: int = 2,
    ) -> RegenerationPlan:
        if repeated_failure_threshold < 2:
            raise ValueError("repeated_failure_threshold must be >= 2")
        candidate = production.candidates.get(candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_REGENERATION_CANDIDATE_NOT_FOUND",
                "Regeneration Candidate is not registered in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        slot = production.slots.get(candidate.slot_id)
        if slot is None:
            raise ProductError(
                "ERR_REGENERATION_SLOT_NOT_FOUND",
                "Regeneration Candidate references a missing Slot",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if slot.status in {SlotStatus.LOCKED, SlotStatus.STALE}:
            raise ProductError(
                "ERR_REGENERATION_SLOT_NOT_MUTABLE",
                "Regeneration planning is blocked for locked/stale Slot state",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"slot_status": slot.status.value},
            )
        decision = cls._human_regeneration_decision(audits, candidate_id)
        referenced_audits = []
        for audit_id in decision.audit_refs:
            record = audits.audit_records.get(audit_id)
            if record is None:
                raise ProductError(
                    "ERR_REGENERATION_AUDIT_NOT_FOUND",
                    "Human regeneration decision references an unavailable Audit",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if record.candidate_id != candidate_id or record.asset_sha256 != candidate.asset_sha256:
                raise ProductError(
                    "ERR_REGENERATION_AUDIT_IDENTITY_MISMATCH",
                    "Regeneration decision Audit does not match exact Candidate bytes",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            referenced_audits.append(record)
        failure_codes = tuple(sorted(set(
            decision.reason_codes
            + tuple(code for record in referenced_audits for code in record.failure_codes)
        )))
        if not failure_codes:
            raise ProductError(
                "ERR_REGENERATION_FAILURE_REASON_REQUIRED",
                "Regeneration planning requires an explicit Audit/decision failure reason",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        if candidate.generation_job_id is None:
            raise ProductError(
                "ERR_REGENERATION_PARENT_ATTEMPT_REQUIRED",
                "Generated Candidate must retain generation_job_id before regeneration can be planned",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        parent = prompts.attempts.get(candidate.generation_job_id)
        if parent is None:
            raise ProductError(
                "ERR_REGENERATION_PARENT_ATTEMPT_NOT_FOUND",
                "Candidate generation_job_id does not exist in Prompt Registry",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if parent.output_candidate_id != candidate_id or parent.slot_id != candidate.slot_id:
            raise ProductError(
                "ERR_REGENERATION_PARENT_IDENTITY_MISMATCH",
                "Prompt Attempt lineage does not match the exact Production Candidate/Slot",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        prompt = prompts.prompts.get((parent.prompt_id, parent.prompt_version))
        if prompt is None or prompt.body_sha256 != parent.prompt_sha256:
            raise ProductError(
                "ERR_REGENERATION_PARENT_PROMPT_MISMATCH",
                "Parent generation Attempt no longer matches an immutable Prompt version",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        # Count current audited failure as the first occurrence, then inspect
        # previous attempts in this Slot backwards.  The current Provider PASS is
        # still a Visual/Human failure, so it participates in the escalation
        # threshold even though GenerationAttempt.result is PASS.
        streak = 1
        history = list(prompts.slot_attempts(candidate.slot_id))
        try:
            parent_index = next(i for i, item in enumerate(history) if item.generation_job_id == parent.generation_job_id)
        except StopIteration as exc:  # defensive: registry lookup above should imply membership
            raise ProductError(
                "ERR_REGENERATION_PARENT_ATTEMPT_NOT_IN_SLOT_HISTORY",
                "Parent generation Attempt is missing from Slot history",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        target = set(failure_codes)
        for previous in reversed(history[:parent_index]):
            if not target.intersection(previous.failure_codes):
                break
            streak += 1

        next_level = int(parent.strategy_level)
        if streak >= repeated_failure_threshold:
            next_level = min(next_level + 1, int(RegenerationStrategy.HUMAN_COMPOSITION_FIX))
        next_strategy = RegenerationStrategy(next_level)
        return RegenerationPlan(
            candidate_id=candidate_id,
            slot_id=candidate.slot_id,
            parent_attempt_id=parent.generation_job_id,
            parent_prompt_id=parent.prompt_id,
            parent_prompt_version=parent.prompt_version,
            current_strategy=parent.strategy_level,
            next_strategy=next_strategy,
            failure_codes=failure_codes,
            same_failure_streak=streak,
            repeated_failure_threshold=repeated_failure_threshold,
        )
