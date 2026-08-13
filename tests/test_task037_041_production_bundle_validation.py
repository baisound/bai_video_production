from __future__ import annotations

import pytest

from ai_video_production.audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from ai_video_production.audit_production_binding import AuditProductionControlBinding
from ai_video_production.candidate_audit import AuditRecord, AuditorKind, CandidateAuditRegistry, HumanCandidateDecision, HumanDecision
from ai_video_production.continuity_map import ContinuityBoundaryType, ContinuityEdge
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.errors import ProductError
from ai_video_production.generation_output_binding import GenerationOutputProductionBinding
from ai_video_production.production_bundle_validation import ProductionBundleValidator
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.prompt_registry import GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry, RegenerationStrategy


SHA1 = "sha256:" + "a" * 64
SHA2 = "sha256:" + "b" * 64
PSHA = "sha256:" + "c" * 64


def locked_candidate(r: ProductionControlRegistry, slot_id: str, candidate_id: str, asset_id: str, sha: str, version: int, job=None):
    r.add_candidate(AssetCandidate(candidate_id, slot_id, asset_id, sha, version, generation_job_id=job))
    r.transition_candidate(candidate_id, CandidateLifecycle.READY_FOR_AUDIT)
    r.transition_candidate(candidate_id, CandidateLifecycle.ACCEPTED)
    slot = r.slots[slot_id]
    r.lock_candidate(slot_id=slot_id, candidate_id=candidate_id, expected_revision=slot.revision)


def bundle():
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-from", "project-1", "scene-1", SlotKind.START_FRAME, True))
    production.add_slot(SceneAssetSlot("slot-to", "project-1", "scene-2", SlotKind.START_FRAME, True))
    locked_candidate(production, "slot-from", "candidate-from", "asset-shared", SHA1, 1)
    locked_candidate(production, "slot-to", "candidate-to", "asset-shared", SHA1, 1)

    audits = CandidateAuditRegistry()
    # Exact audit/decision for source candidate; add directly since it is already locked in this cross-store fixture.
    audits.add_audit(AuditRecord("audit-1", "candidate-from", SHA1, ("contract-1",), AuditorKind.AI, "judge", "v1", {"CONTRACT":100.0}, (), ()))
    audits.add_human_decision(HumanDecision("decision-1", "candidate-from", ("audit-1",), HumanCandidateDecision.ACCEPT, "owner"))

    prompts = PromptGenerationRegistry()
    prompts.add_prompt(PromptEntity("prompt-1", 1, "frame", PSHA, "profile-1", "v1", ("keep",), slot_id="slot-from"))
    prompts.add_attempt(GenerationAttempt("job-pass", "slot-from", "prompt-1", 1, PSHA, "provider", "model", RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL))

    continuity = ContinuityRegistry()
    edge = ContinuityEdge("cont-1", "scene-1", "slot-from", "candidate-from", "asset-shared", SHA1, "scene-2", "slot-to", ContinuityBoundaryType.DIRECT_CONTINUATION)
    continuity.add_edge(edge)
    continuity.inspect_target("cont-1", target_asset_id="asset-shared", target_asset_sha256=SHA1)

    audio = AudioWorkspaceRegistry()
    audio.add_placement(PlacementReview("placement-1", "candidate-from", 0, 30, "BGM", PlacementDecision.ACCEPT))
    return production, audits, prompts, continuity, audio


def test_consistent_cross_task_bundle_passes_without_repair():
    production, audits, prompts, continuity, audio = bundle()
    report = ProductionBundleValidator.validate(
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio
    ).to_dict()
    assert report["status"] == "PASS"
    assert report["automatic_repair_performed"] is False
    assert report["automatic_regeneration_started"] is False


def test_audit_hash_drift_is_detected_cross_store():
    production, audits, prompts, continuity, audio = bundle()
    bad = CandidateAuditRegistry()
    bad.add_audit(AuditRecord("audit-bad", "candidate-from", SHA2, ("contract-1",), AuditorKind.AI, "judge", "v1", {}, (), ()))
    with pytest.raises(ProductError) as exc:
        ProductionBundleValidator.validate(production=production, audits=bad, prompts=prompts, continuity=continuity, audio=audio)
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_AUDIT_HASH_MISMATCH"


def test_resolved_continuity_target_must_still_match_locked_target_asset():
    production, audits, prompts, continuity, audio = bundle()
    # Simulate valid per-store state that became inconsistent with Production Control.
    continuity.resolutions["cont-1"] = continuity.resolutions["cont-1"].__class__(
        "cont-1", "asset-other", SHA2, "PASS", "PASS"
    )
    with pytest.raises(ProductError) as exc:
        ProductionBundleValidator.validate(production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio)
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_CONTINUITY_TARGET_MISMATCH"


def test_accepted_audio_placement_detects_candidate_that_is_no_longer_locked():
    production, audits, prompts, continuity, audio = bundle()
    production.candidates["candidate-from"] = production.candidates["candidate-from"].__class__(
        "candidate-from", "slot-from", "asset-shared", SHA1, 1, CandidateLifecycle.STALE
    )
    with pytest.raises(ProductError) as exc:
        ProductionBundleValidator.validate(production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio)
    # Continuity source is still exact; audio check catches the lifecycle drift.
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_AUDIO_ACCEPT_NOT_LOCKED"


def test_pass_generation_output_can_be_required_to_exist_in_production():
    production, audits, prompts, continuity, audio = bundle()
    prompts.add_prompt(PromptEntity("prompt-2", 1, "frame2", PSHA, "profile-1", "v1", ("keep",), slot_id="slot-from"))
    prompts.add_attempt(GenerationAttempt(
        "job-missing", "slot-from", "prompt-2", 1, PSHA, "provider", "model",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), output_candidate_id="candidate-missing",
    ))
    with pytest.raises(ProductError) as exc:
        ProductionBundleValidator.validate(production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio)
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_GENERATION_OUTPUT_MISSING"
