from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.generation_output_binding import GenerationOutputProductionBinding
from ai_video_production.production_control import AssetCandidate, EntityRef, EntityType, ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.prompt_registry import (
    GenerationAttempt,
    GenerationResult,
    PromptEntity,
    PromptGenerationRegistry,
    RegenerationStrategy,
)


PROMPT_SHA = "sha256:" + "c" * 64
ASSET_SHA = "sha256:" + "a" * 64


def prompt_registry(*, result=GenerationResult.PASS, output_candidate_id="candidate-1"):
    r = PromptGenerationRegistry()
    r.add_prompt(PromptEntity(
        "prompt-1", 1, "frame", PROMPT_SHA, "profile-1", "v1", ("keep",), slot_id="slot-1"
    ))
    r.add_attempt(GenerationAttempt(
        "job-1", "slot-1", "prompt-1", 1, PROMPT_SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, result, (), output_candidate_id=output_candidate_id,
    ))
    return r


def production(*, job_id="job-1", slot_id="slot-1"):
    r = ProductionControlRegistry()
    r.add_slot(SceneAssetSlot(slot_id, "project-1", "scene-1", SlotKind.START_FRAME, True))
    r.add_candidate(AssetCandidate("candidate-1", slot_id, "asset-1", ASSET_SHA, 1, generation_job_id=job_id))
    return r


def test_pass_attempt_binds_prompt_lineage_to_exact_candidate():
    prompts = prompt_registry(); prod = production()
    result = GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    assert result.status == "BOUND"
    edge = prod.edges[result.edge_id]
    assert edge.from_ref == EntityRef(EntityType.PROMPT, "prompt-1:v1")
    assert edge.to_ref == EntityRef(EntityType.CANDIDATE, "candidate-1")
    assert edge.from_hash == PROMPT_SHA


def test_binding_is_idempotent_for_exact_same_attempt_output():
    prompts = prompt_registry(); prod = production()
    first = GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    second = GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    assert first.edge_id == second.edge_id
    assert second.status == "ALREADY_BOUND"


def test_failed_attempt_cannot_claim_production_output_lineage():
    prompts = prompt_registry(result=GenerationResult.FAIL, output_candidate_id=None); prod = production()
    with pytest.raises(ProductError) as exc:
        GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    assert exc.value.code == "ERR_GENERATION_OUTPUT_NOT_PASS"


def test_candidate_generation_job_identity_must_match_attempt():
    prompts = prompt_registry(); prod = production(job_id="job-other")
    with pytest.raises(ProductError) as exc:
        GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    assert exc.value.code == "ERR_GENERATION_OUTPUT_JOB_MISMATCH"


def test_attempt_output_candidate_must_exist():
    prompts = prompt_registry(output_candidate_id="candidate-missing"); prod = production()
    with pytest.raises(ProductError) as exc:
        GenerationOutputProductionBinding.bind(generation_job_id="job-1", prompts=prompts, production=prod)
    assert exc.value.code == "ERR_GENERATION_OUTPUT_CANDIDATE_NOT_FOUND"
