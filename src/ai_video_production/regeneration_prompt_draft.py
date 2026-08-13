"""TASK-040 regeneration Prompt-version draft/registration boundary.

Consumes a Human-authorized ``RegenerationPlan`` and creates a new immutable
Prompt version without executing any provider.  Registration fails closed if
the Prompt lineage advanced after the draft was compiled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .prompt_registry import PromptEntity, PromptGenerationRegistry, RegenerationStrategy
from .regeneration_planning import RegenerationPlan
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class RegenerationPromptDraft:
    parent_prompt_id: str
    parent_prompt_version: int
    parent_prompt_sha256: str
    prompt: PromptEntity
    strategy: RegenerationStrategy
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "draft_version": "1.0.0",
            "task_owner": "TASK-040",
            "parent_prompt_id": self.parent_prompt_id,
            "parent_prompt_version": self.parent_prompt_version,
            "parent_prompt_sha256": self.parent_prompt_sha256,
            "new_prompt": self.prompt.to_dict(),
            "strategy_level": int(self.strategy),
            "reason_codes": list(self.reason_codes),
            "prompt_body_embedded": False,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
        }
        body["draft_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class RegenerationPromptDraftService:
    @staticmethod
    def compile(
        plan: RegenerationPlan,
        *,
        registry: PromptGenerationRegistry,
        new_body_sha256: str,
        new_body_ref: str | None,
        provider_profile_id: str | None = None,
        provider_profile_version: str | None = None,
        input_asset_hashes: Iterable[str] | None = None,
        keep_conditions: Iterable[str] | None = None,
    ) -> RegenerationPromptDraft:
        parent = registry.prompts.get((plan.parent_prompt_id, plan.parent_prompt_version))
        if parent is None:
            raise ProductError(
                "ERR_REGENERATION_DRAFT_PARENT_PROMPT_MISSING",
                "Regeneration Prompt draft parent version is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        attempt = registry.attempts.get(plan.parent_attempt_id)
        if (
            attempt is None
            or attempt.prompt_id != parent.prompt_id
            or attempt.prompt_version != parent.prompt_version
            or attempt.prompt_sha256 != parent.body_sha256
            or attempt.slot_id != plan.slot_id
        ):
            raise ProductError(
                "ERR_REGENERATION_DRAFT_PARENT_ATTEMPT_MISMATCH",
                "Regeneration Prompt parent Attempt no longer matches Prompt/Slot bytes",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        versions = [version for pid, version in registry.prompts if pid == parent.prompt_id]
        expected_version = max(versions) + 1
        if expected_version != parent.prompt_version + 1:
            raise ProductError(
                "ERR_REGENERATION_DRAFT_PARENT_NOT_LATEST",
                "Regeneration must derive from the latest immutable Prompt version",
                ProductErrorCategory.STATE,
                details={"latest_version": max(versions)},
            )
        next_profile_id = provider_profile_id or parent.provider_profile_id
        next_profile_version = provider_profile_version or parent.provider_profile_version
        profile_changed = (
            next_profile_id != parent.provider_profile_id
            or next_profile_version != parent.provider_profile_version
        )
        if profile_changed and plan.next_strategy < RegenerationStrategy.PROVIDER_SWITCH:
            raise ProductError(
                "ERR_REGENERATION_PROVIDER_SWITCH_NOT_AUTHORIZED",
                "Provider Profile may change only after regeneration strategy escalates to PROVIDER_SWITCH or higher",
                ProductErrorCategory.AUTHORIZATION,
            )
        next_inputs = tuple(parent.input_asset_hashes if input_asset_hashes is None else input_asset_hashes)
        next_keep = tuple(parent.keep_conditions if keep_conditions is None else keep_conditions)
        prompt = PromptEntity(
            prompt_id=parent.prompt_id,
            prompt_version=expected_version,
            purpose=parent.purpose,
            body_sha256=new_body_sha256,
            provider_profile_id=next_profile_id,
            provider_profile_version=next_profile_version,
            keep_conditions=next_keep,
            scene_id=parent.scene_id,
            slot_id=parent.slot_id,
            body_ref=new_body_ref,
            input_asset_hashes=next_inputs,
        )
        no_prompt_change = (
            prompt.body_sha256 == parent.body_sha256
            and prompt.body_ref == parent.body_ref
            and prompt.provider_profile_id == parent.provider_profile_id
            and prompt.provider_profile_version == parent.provider_profile_version
            and prompt.input_asset_hashes == parent.input_asset_hashes
            and prompt.keep_conditions == parent.keep_conditions
        )
        if no_prompt_change and plan.next_strategy == plan.current_strategy:
            raise ProductError(
                "ERR_REGENERATION_DRAFT_NO_CHANGE",
                "Regeneration draft must change Prompt/control identity or escalate strategy",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        return RegenerationPromptDraft(
            parent.prompt_id,
            parent.prompt_version,
            parent.body_sha256,
            prompt,
            plan.next_strategy,
            plan.failure_codes,
        )

    @staticmethod
    def register(draft: RegenerationPromptDraft, *, registry: PromptGenerationRegistry) -> PromptEntity:
        current = registry.prompts.get((draft.parent_prompt_id, draft.parent_prompt_version))
        versions = [version for pid, version in registry.prompts if pid == draft.parent_prompt_id]
        if (
            current is None
            or current.body_sha256 != draft.parent_prompt_sha256
            or not versions
            or max(versions) != draft.parent_prompt_version
            or draft.prompt.prompt_version != draft.parent_prompt_version + 1
        ):
            raise ProductError(
                "ERR_REGENERATION_DRAFT_STALE",
                "Prompt lineage changed after regeneration draft was compiled",
                ProductErrorCategory.STATE,
            )
        registry.add_prompt(draft.prompt)
        return draft.prompt
