from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.prompt_registry import (
    AdaptiveRegenerationRouter,
    GenerationAdmission,
    GenerationAttempt,
    GenerationResult,
    PromptEntity,
    PromptGenerationRegistry,
    RegenerationStrategy,
)


SHA = "sha256:" + "c" * 64


def prompt(version: int = 1) -> PromptEntity:
    return PromptEntity(
        "prompt-1", version, "scene frame", SHA, "profile-1", "v1", ("monitor foreground",),
        scene_id="scene-1", slot_id="slot-1", body_ref="project-private://prompts/prompt-1"
    )


def attempt(job: str, *, strategy=RegenerationStrategy.TEXT_PROMPT, failures=("DEPTH_ORDER",), result=GenerationResult.FAIL, parent=None):
    return GenerationAttempt(job, "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1", strategy, result, failures, parent_attempt_id=parent, provider_profile_version="v1")


def test_prompt_versions_are_append_only():
    registry = PromptGenerationRegistry()
    registry.add_prompt(prompt(1))
    with pytest.raises(ProductError) as exc:
        registry.add_prompt(prompt(3))
    assert exc.value.code == "ERR_PROMPT_VERSION_SEQUENCE"


def test_attempt_requires_exact_registered_prompt_hash():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    bad = GenerationAttempt("job-1", "slot-1", "prompt-1", 1, "sha256:" + "d"*64, "provider-1", "model-1", RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL, provider_profile_version="v1")
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(bad)
    assert exc.value.code == "ERR_GENERATION_PROMPT_HASH_MISMATCH"


def test_repeated_structural_failure_escalates_strategy_after_threshold():
    rows = (attempt("job-1"), attempt("job-2", parent="job-1"))
    assert AdaptiveRegenerationRouter.next_strategy(rows, repeated_failure_threshold=2) == RegenerationStrategy.PROMPT_RESTRUCTURE


def test_human_required_routes_to_human_composition_fix():
    row = attempt("job-1", result=GenerationResult.HUMAN_REQUIRED, failures=())
    assert AdaptiveRegenerationRouter.next_strategy((row,)) == RegenerationStrategy.HUMAN_COMPOSITION_FIX


def test_generation_admission_fails_closed_with_missing_prerequisites():
    gate = GenerationAdmission(True, False, True, False)
    with pytest.raises(ProductError) as exc:
        gate.require_ready()
    assert exc.value.code == "ERR_GENERATION_ADMISSION_BLOCKED"
    assert exc.value.details["missing"] == ["FEASIBILITY_PASS", "COST_AUTHORIZED"]


def test_attempt_cannot_drift_to_different_slot_than_prompt():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    bad = GenerationAttempt(
        "job-slot", "slot-other", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL, provider_profile_version="v1",
    )
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(bad)
    assert exc.value.code == "ERR_GENERATION_PROMPT_SLOT_MISMATCH"


def test_attempt_must_preserve_prompt_input_asset_identity():
    registry = PromptGenerationRegistry()
    value = PromptEntity(
        "prompt-input", 1, "scene frame", SHA, "profile-1", "v1", ("keep",),
        scene_id="scene-1", slot_id="slot-1", input_asset_hashes=("sha256:" + "e" * 64,),
    )
    registry.add_prompt(value)
    bad = GenerationAttempt(
        "job-input", "slot-1", "prompt-input", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL,
        input_asset_hashes=("sha256:" + "f" * 64,),
        provider_profile_version="v1",
    )
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(bad)
    assert exc.value.code == "ERR_GENERATION_PROMPT_INPUT_HASH_MISMATCH"


def test_regeneration_parent_must_belong_to_same_slot():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    parent = GenerationAttempt(
        "job-parent", "slot-other", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL, provider_profile_version="v1",
    )
    # Use a prompt version without a slot constraint only for this imported-lineage fixture.
    loose = PromptEntity("prompt-loose", 1, "loose", SHA, "profile-1", "v1", ("keep",))
    registry.add_prompt(loose)
    parent = GenerationAttempt(
        "job-parent", "slot-other", "prompt-loose", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL, provider_profile_version="v1",
    )
    registry.add_attempt(parent)
    child = GenerationAttempt(
        "job-child", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.PROMPT_RESTRUCTURE, GenerationResult.FAIL,
        parent_attempt_id="job-parent", provider_profile_version="v1",
    )
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(child)
    assert exc.value.code == "ERR_GENERATION_PARENT_SLOT_MISMATCH"


def test_attempt_requires_exact_provider_profile_version():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    row = GenerationAttempt(
        "job-profile", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.FAIL,
        provider_profile_version=None,
    )
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(row)
    assert exc.value.code == "ERR_GENERATION_PROFILE_VERSION_MISMATCH"


def test_output_candidate_is_owned_by_exactly_one_attempt():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    first = GenerationAttempt(
        "job-pass-1", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-1",
        provider_profile_version="v1",
    )
    second = GenerationAttempt(
        "job-pass-2", "slot-1", "prompt-1", 1, SHA, "provider-1", "model-1",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-1",
        provider_profile_version="v1",
    )
    registry.add_attempt(first)
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(second)
    assert exc.value.code == "ERR_GENERATION_OUTPUT_CANDIDATE_CONFLICT"


def test_child_attempt_cannot_reduce_parent_strategy_level():
    registry = PromptGenerationRegistry(); registry.add_prompt(prompt())
    registry.add_attempt(attempt("job-parent", strategy=RegenerationStrategy.LAYOUT_REFERENCE))
    child = attempt(
        "job-child", strategy=RegenerationStrategy.PROMPT_RESTRUCTURE,
        parent="job-parent",
    )
    with pytest.raises(ProductError) as exc:
        registry.add_attempt(child)
    assert exc.value.code == "ERR_GENERATION_PARENT_STRATEGY_REGRESSION"
