from __future__ import annotations

import pytest

from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.candidate_audit import (
    AuditDimension, AuditFinding, AuditRecord, AuditorKind, CandidateAuditRegistry,
    FindingSeverity, HumanCandidateDecision, HumanDecision,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_control import AssetCandidate, ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.prompt_registry import (
    GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry, RegenerationStrategy,
)
from ai_video_production.regeneration_planning import HumanRegenerationPlanner

H = lambda ch: "sha256:" + ch * 64


def state(*, prior_same_failure: bool = False):
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-1", "project-1", "scene-1", SlotKind.START_FRAME, True))
    production.add_candidate(AssetCandidate("candidate-1", "slot-1", "asset-1", H("a"), 1, generation_job_id="job-current"))

    prompts = PromptGenerationRegistry()
    prompts.add_prompt(PromptEntity("prompt-1", 1, "start frame", H("1"), "provider", "v1", ("keep face",), slot_id="slot-1"))
    if prior_same_failure:
        prompts.add_attempt(GenerationAttempt(
            "job-prior", "slot-1", "prompt-1", 1, H("1"), "provider", "model",
            RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL, ("DEPTH_REVERSED",),
            provider_profile_version="v1",
        ))
    prompts.add_attempt(GenerationAttempt(
        "job-current", "slot-1", "prompt-1", 1, H("1"), "provider", "model",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-1",
        parent_attempt_id="job-prior" if prior_same_failure else None,
        provider_profile_version="v1",
    ))

    audits = CandidateAuditRegistry()
    AuditProductionControlBinding.record_audit(production, audits, AuditRecord(
        "audit-1", "candidate-1", H("a"), ("contract-1",), AuditorKind.AI, "vision", "v1",
        {"GEOMETRY": 10.0},
        (AuditFinding("finding-1", AuditDimension.GEOMETRY, FindingSeverity.CRITICAL, "DEPTH_REVERSED", "depth is reversed", True),),
        ("DEPTH_REVERSED",),
    ))
    AuditProductionControlBinding.apply_human_decision(production, audits, HumanDecision(
        "decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.NEEDS_REGENERATION, "owner"
    ))
    return production, audits, prompts


def test_single_audited_failure_keeps_current_strategy_without_provider_execution():
    production, audits, prompts = state()
    plan = HumanRegenerationPlanner.compile(candidate_id="candidate-1", production=production, audits=audits, prompts=prompts)
    body = plan.to_dict()
    assert plan.next_strategy is RegenerationStrategy.TEXT_PROMPT
    assert plan.same_failure_streak == 1
    assert body["provider_execution_started"] is False
    assert body["requires_new_prompt_version"] is True


def test_repeated_same_failure_escalates_control_strategy():
    production, audits, prompts = state(prior_same_failure=True)
    plan = HumanRegenerationPlanner.compile(candidate_id="candidate-1", production=production, audits=audits, prompts=prompts)
    assert plan.same_failure_streak == 2
    assert plan.next_strategy is RegenerationStrategy.PROMPT_RESTRUCTURE


def test_regeneration_plan_requires_human_needs_regeneration_decision():
    production, audits, prompts = state()
    audits.decisions.clear()
    with pytest.raises(ProductError) as exc:
        HumanRegenerationPlanner.compile(candidate_id="candidate-1", production=production, audits=audits, prompts=prompts)
    assert exc.value.code == "ERR_REGENERATION_HUMAN_DECISION_REQUIRED"


def test_regeneration_plan_fails_closed_on_candidate_attempt_mismatch():
    production, audits, prompts = state()
    production.candidates["candidate-1"] = AssetCandidate(
        "candidate-1", "slot-1", "asset-1", H("a"), 1, generation_job_id="missing-job"
    )
    with pytest.raises(ProductError) as exc:
        HumanRegenerationPlanner.compile(candidate_id="candidate-1", production=production, audits=audits, prompts=prompts)
    assert exc.value.code == "ERR_REGENERATION_PARENT_ATTEMPT_NOT_FOUND"
