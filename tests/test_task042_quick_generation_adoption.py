from __future__ import annotations

from ai_video_production.candidate_audit import (
    AuditRecord, AuditorKind, CandidateAuditRegistry, HumanCandidateDecision, HumanDecision,
)
from ai_video_production.production_control import (
    AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind,
)
from ai_video_production.prompt_registry import (
    GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry, RegenerationStrategy,
)
from ai_video_production.quick_generation import (
    QuickGenerationAdoptionProjection, QuickGenerationIntent, QuickGenerationMode,
)


H = lambda ch: "sha256:" + ch * 64


def intent() -> QuickGenerationIntent:
    return QuickGenerationIntent(
        "quick-1", 1, "project-1", "scene-1", QuickGenerationMode.IMAGE, "slot-target",
        "prompt-1", 1, H("1"), H("2"), "profile", "v1", H("3"), "route", "GENERATE",
        ("GENERATE",), (), "rights://owner/1", "USD", "0", "decision", H("4"), H("5"), H("6"), H("7"),
    )


def registries():
    prompts = PromptGenerationRegistry()
    prompts.add_prompt(PromptEntity(
        "prompt-1", 1, "quick", H("1"), "profile", "v1", ("keep",),
        scene_id="scene-1", slot_id="slot-target",
    ))
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-target", "project-1", "scene-1", SlotKind.START_FRAME, False))
    return prompts, production, CandidateAuditRegistry()


def project(prompts, production, audits):
    return QuickGenerationAdoptionProjection.project(
        intent=intent(), generation_job_id="job-1", prompts=prompts,
        production=production, audits=audits,
    )["status"]


def test_adoption_projection_requires_attempt_audit_accept_and_lock_in_order() -> None:
    prompts, production, audits = registries()
    assert project(prompts, production, audits) == "OUTPUT_NOT_REGISTERED"

    production.add_candidate(AssetCandidate("candidate-1", "slot-target", "asset-1", H("a"), 1, generation_job_id="job-1"))
    prompts.add_attempt(GenerationAttempt(
        "job-1", "slot-target", "prompt-1", 1, H("1"), "provider", "model",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-1",
        provider_profile_version="v1",
    ))
    assert project(prompts, production, audits) == "AUDIT_REQUIRED"

    production.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    audits.add_audit(AuditRecord(
        "audit-1", "candidate-1", H("a"), ("contract",), AuditorKind.HUMAN,
        "auditor", None, {"TECHNICAL": 100.0}, (), (),
    ))
    assert project(prompts, production, audits) == "ACCEPT_REQUIRED"

    audits.add_human_decision(HumanDecision(
        "decision-1", "candidate-1", ("audit-1",), HumanCandidateDecision.ACCEPT, "owner",
    ))
    assert project(prompts, production, audits) == "LOCK_REQUIRED"

    production.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    production.lock_candidate(slot_id="slot-target", candidate_id="candidate-1", expected_revision=production.slots["slot-target"].revision)
    result = QuickGenerationAdoptionProjection.project(
        intent=intent(), generation_job_id="job-1", prompts=prompts,
        production=production, audits=audits,
    )
    assert result["status"] == "PRODUCTION_ADOPTED"
    assert result["read_only"] is True
    assert result["candidate_created"] is False
