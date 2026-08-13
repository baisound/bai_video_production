from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.prompt_registry import (
    GenerationAttempt, GenerationResult, PromptEntity, PromptGenerationRegistry,
    RegenerationStrategy,
)
from ai_video_production.regeneration_planning import RegenerationPlan
from ai_video_production.regeneration_prompt_draft import RegenerationPromptDraftService

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def registry() -> PromptGenerationRegistry:
    value = PromptGenerationRegistry()
    prompt = PromptEntity(
        "prompt-1", 1, "scene", SHA_A, "profile", "1", ("keep-character",),
        scene_id="SC01", slot_id="slot:SC01:VIDEO", body_ref="prompt://project/prompt-1/v1",
    )
    value.add_prompt(prompt)
    value.add_attempt(GenerationAttempt(
        "job-1", "slot:SC01:VIDEO", "prompt-1", 1, SHA_A,
        "provider", "model", RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS,
        output_candidate_id="candidate-1", provider_profile_version="1",
    ))
    return value


def plan(*, current=RegenerationStrategy.TEXT_PROMPT, next_strategy=RegenerationStrategy.TEXT_PROMPT):
    return RegenerationPlan(
        "candidate-1", "slot:SC01:VIDEO", "job-1", "prompt-1", 1,
        current, next_strategy, ("SPATIAL_RELATION_FAILURE",), 1, 2,
    )


def test_regeneration_draft_creates_and_registers_next_immutable_prompt_version() -> None:
    prompts = registry()
    draft = RegenerationPromptDraftService.compile(
        plan(), registry=prompts, new_body_sha256=SHA_B,
        new_body_ref="prompt://project/prompt-1/v2",
    )
    assert draft.prompt.prompt_version == 2
    assert draft.prompt.body_sha256 == SHA_B
    assert draft.to_dict()["provider_execution_started"] is False
    registered = RegenerationPromptDraftService.register(draft, registry=prompts)
    assert prompts.prompts[("prompt-1", 2)] == registered


def test_provider_profile_cannot_change_before_provider_switch_strategy() -> None:
    prompts = registry()
    with pytest.raises(ProductError) as exc:
        RegenerationPromptDraftService.compile(
            plan(next_strategy=RegenerationStrategy.PROMPT_RESTRUCTURE),
            registry=prompts, new_body_sha256=SHA_B,
            new_body_ref="prompt://project/prompt-1/v2",
            provider_profile_id="other-profile", provider_profile_version="2",
        )
    assert exc.value.code == "ERR_REGENERATION_PROVIDER_SWITCH_NOT_AUTHORIZED"


def test_strategy_escalation_may_create_new_version_even_if_prompt_body_is_unchanged() -> None:
    prompts = registry()
    draft = RegenerationPromptDraftService.compile(
        plan(next_strategy=RegenerationStrategy.LAYOUT_REFERENCE),
        registry=prompts, new_body_sha256=SHA_A,
        new_body_ref="prompt://project/prompt-1/v1",
    )
    assert draft.strategy is RegenerationStrategy.LAYOUT_REFERENCE
    assert draft.prompt.prompt_version == 2


def test_no_change_without_strategy_escalation_is_rejected() -> None:
    prompts = registry()
    with pytest.raises(ProductError) as exc:
        RegenerationPromptDraftService.compile(
            plan(), registry=prompts, new_body_sha256=SHA_A,
            new_body_ref="prompt://project/prompt-1/v1",
        )
    assert exc.value.code == "ERR_REGENERATION_DRAFT_NO_CHANGE"


def test_regeneration_draft_registration_fails_if_prompt_lineage_advanced() -> None:
    prompts = registry()
    draft = RegenerationPromptDraftService.compile(
        plan(), registry=prompts, new_body_sha256=SHA_B,
        new_body_ref="prompt://project/prompt-1/v2",
    )
    prompts.add_prompt(PromptEntity(
        "prompt-1", 2, "scene", SHA_B, "profile", "1", ("keep-character",),
        scene_id="SC01", slot_id="slot:SC01:VIDEO", body_ref="prompt://other/v2",
    ))
    with pytest.raises(ProductError) as exc:
        RegenerationPromptDraftService.register(draft, registry=prompts)
    assert exc.value.code == "ERR_REGENERATION_DRAFT_STALE"
