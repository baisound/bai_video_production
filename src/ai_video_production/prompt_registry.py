"""TASK-040 Prompt Registry and adaptive regeneration routing foundation.

No provider call is executed here. The module stores prompt/attempt identity and
returns routing/admission decisions for higher-level orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class GenerationResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CANCELLED = "CANCELLED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class RegenerationStrategy(int, Enum):
    TEXT_PROMPT = 0
    PROMPT_RESTRUCTURE = 1
    LAYOUT_REFERENCE = 2
    CONTROL_GUIDANCE = 3
    REGION_REPAIR = 4
    PROVIDER_SWITCH = 5
    HUMAN_COMPOSITION_FIX = 6


@dataclass(frozen=True, slots=True)
class PromptEntity:
    prompt_id: str
    prompt_version: int
    purpose: str
    body_sha256: str
    provider_profile_id: str
    provider_profile_version: str
    keep_conditions: tuple[str, ...]
    scene_id: str | None = None
    slot_id: str | None = None
    body_ref: str | None = None
    input_asset_hashes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.prompt_id, "prompt_id")
        if isinstance(self.prompt_version, bool) or not isinstance(self.prompt_version, int) or self.prompt_version < 1:
            raise ValueError("prompt_version must be >= 1")
        if not isinstance(self.purpose, str) or not self.purpose.strip() or len(self.purpose) > 200:
            raise ValueError("purpose is invalid")
        _sha(self.body_sha256, "body_sha256")
        _id(self.provider_profile_id, "provider_profile_id")
        if not isinstance(self.provider_profile_version, str) or not self.provider_profile_version.strip() or len(self.provider_profile_version) > 100:
            raise ValueError("provider_profile_version is invalid")
        if not isinstance(self.keep_conditions, tuple) or not self.keep_conditions:
            raise ValueError("keep_conditions must not be empty")
        for item in self.keep_conditions:
            if not isinstance(item, str) or not item.strip() or len(item) > 1000 or "\x00" in item:
                raise ValueError("keep condition is invalid")
        if len(set(self.keep_conditions)) != len(self.keep_conditions):
            raise ValueError("keep_conditions must be unique")
        for name, value in (("scene_id", self.scene_id), ("slot_id", self.slot_id)):
            if value is not None:
                _id(value, name)
        if self.body_ref is not None and (not isinstance(self.body_ref, str) or not self.body_ref.strip() or len(self.body_ref) > 1000):
            raise ValueError("body_ref is invalid")
        if not isinstance(self.input_asset_hashes, tuple):
            raise ValueError("input_asset_hashes must be a tuple")
        for value in self.input_asset_hashes:
            _sha(value, "input_asset_hash")
        if len(set(self.input_asset_hashes)) != len(self.input_asset_hashes):
            raise ValueError("input_asset_hashes must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "purpose": self.purpose,
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "body_ref": self.body_ref,
            "body_sha256": self.body_sha256,
            "provider_profile_id": self.provider_profile_id,
            "provider_profile_version": self.provider_profile_version,
            "input_asset_hashes": list(self.input_asset_hashes),
            "keep_conditions": list(self.keep_conditions),
            "prompt_body_embedded_in_general_evidence": False,
        }


@dataclass(frozen=True, slots=True)
class GenerationAttempt:
    generation_job_id: str
    slot_id: str
    prompt_id: str
    prompt_version: int
    prompt_sha256: str
    provider_id: str
    model_id: str
    strategy_level: RegenerationStrategy
    result: GenerationResult
    failure_codes: tuple[str, ...] = ()
    output_candidate_id: str | None = None
    parent_attempt_id: str | None = None
    provider_profile_version: str | None = None
    input_asset_hashes: tuple[str, ...] = ()
    cost: float | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("generation_job_id", self.generation_job_id),
            ("slot_id", self.slot_id),
            ("prompt_id", self.prompt_id),
            ("provider_id", self.provider_id),
            ("model_id", self.model_id),
        ):
            _id(value, name)
        if isinstance(self.prompt_version, bool) or not isinstance(self.prompt_version, int) or self.prompt_version < 1:
            raise ValueError("prompt_version must be >= 1")
        _sha(self.prompt_sha256, "prompt_sha256")
        if not isinstance(self.strategy_level, RegenerationStrategy):
            raise ValueError("strategy_level is invalid")
        if not isinstance(self.result, GenerationResult):
            raise ValueError("result is invalid")
        if not isinstance(self.failure_codes, tuple):
            raise ValueError("failure_codes must be a tuple")
        for value in self.failure_codes:
            _id(value, "failure_code")
        if len(set(self.failure_codes)) != len(self.failure_codes):
            raise ValueError("failure_codes must be unique")
        for name, value in (("output_candidate_id", self.output_candidate_id), ("parent_attempt_id", self.parent_attempt_id)):
            if value is not None:
                _id(value, name)
        if self.provider_profile_version is not None and (
            not isinstance(self.provider_profile_version, str)
            or not self.provider_profile_version.strip()
            or len(self.provider_profile_version) > 100
        ):
            raise ValueError("provider_profile_version is invalid")
        if not isinstance(self.input_asset_hashes, tuple):
            raise ValueError("input_asset_hashes must be a tuple")
        for value in self.input_asset_hashes:
            _sha(value, "input_asset_hash")
        if len(set(self.input_asset_hashes)) != len(self.input_asset_hashes):
            raise ValueError("input_asset_hashes must be unique")
        if self.cost is not None and (
            isinstance(self.cost, bool)
            or not isinstance(self.cost, (int, float))
            or not math.isfinite(float(self.cost))
            or self.cost < 0
        ):
            raise ValueError("cost must be non-negative or null")
        if self.latency_ms is not None and (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, int)
            or self.latency_ms < 0
        ):
            raise ValueError("latency_ms must be non-negative or null")
        if self.result is GenerationResult.PASS and self.output_candidate_id is None:
            raise ValueError("PASS generation Attempt requires output_candidate_id")
        if self.result is not GenerationResult.PASS and self.output_candidate_id is not None:
            raise ValueError("Only PASS generation Attempt may name output_candidate_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_job_id": self.generation_job_id,
            "slot_id": self.slot_id,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "provider_profile_version": self.provider_profile_version,
            "strategy_level": int(self.strategy_level),
            "result": self.result.value,
            "failure_codes": list(self.failure_codes),
            "output_candidate_id": self.output_candidate_id,
            "parent_attempt_id": self.parent_attempt_id,
            "input_asset_hashes": list(self.input_asset_hashes),
            "cost": self.cost,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True, slots=True)
class GenerationAdmission:
    plan_approved: bool
    feasibility_pass: bool
    required_inputs_locked: bool
    cost_authorized: bool

    @property
    def ready(self) -> bool:
        return self.plan_approved and self.feasibility_pass and self.required_inputs_locked and self.cost_authorized

    def require_ready(self) -> None:
        if self.ready:
            return
        missing = []
        if not self.plan_approved:
            missing.append("PLAN_APPROVED")
        if not self.feasibility_pass:
            missing.append("FEASIBILITY_PASS")
        if not self.required_inputs_locked:
            missing.append("REQUIRED_INPUT_LOCKED")
        if not self.cost_authorized:
            missing.append("COST_AUTHORIZED")
        raise ProductError(
            "ERR_GENERATION_ADMISSION_BLOCKED",
            "High-cost generation prerequisites are not satisfied",
            ProductErrorCategory.AUTHORIZATION,
            details={"missing": missing},
        )


class PromptGenerationRegistry:
    def __init__(self) -> None:
        self.prompts: dict[tuple[str, int], PromptEntity] = {}
        self.attempts: dict[str, GenerationAttempt] = {}

    def add_prompt(self, prompt: PromptEntity) -> None:
        key = (prompt.prompt_id, prompt.prompt_version)
        if key in self.prompts:
            raise ProductError("ERR_PROMPT_VERSION_CONFLICT", "Prompt version already exists", ProductErrorCategory.STATE)
        versions = [version for pid, version in self.prompts if pid == prompt.prompt_id]
        expected = max(versions) + 1 if versions else 1
        if prompt.prompt_version != expected:
            raise ProductError(
                "ERR_PROMPT_VERSION_SEQUENCE",
                "Prompt versions must append without overwrite or gaps",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"expected_version": expected},
            )
        self.prompts[key] = prompt

    def add_attempt(self, attempt: GenerationAttempt) -> None:
        if attempt.generation_job_id in self.attempts:
            raise ProductError("ERR_GENERATION_ATTEMPT_CONFLICT", "generation_job_id already exists", ProductErrorCategory.STATE)
        prompt = self.prompts.get((attempt.prompt_id, attempt.prompt_version))
        if prompt is None:
            raise ProductError("ERR_GENERATION_PROMPT_NOT_FOUND", "GenerationAttempt references unknown Prompt version", ProductErrorCategory.DATA_INTEGRITY)
        if prompt.body_sha256 != attempt.prompt_sha256:
            raise ProductError("ERR_GENERATION_PROMPT_HASH_MISMATCH", "GenerationAttempt Prompt hash does not match registry", ProductErrorCategory.DATA_INTEGRITY)
        if prompt.slot_id is not None and prompt.slot_id != attempt.slot_id:
            raise ProductError(
                "ERR_GENERATION_PROMPT_SLOT_MISMATCH",
                "GenerationAttempt slot does not match the registered Prompt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if tuple(prompt.input_asset_hashes) != tuple(attempt.input_asset_hashes):
            raise ProductError(
                "ERR_GENERATION_PROMPT_INPUT_HASH_MISMATCH",
                "GenerationAttempt input Asset hashes do not match the registered Prompt version",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if attempt.provider_profile_version != prompt.provider_profile_version:
            raise ProductError(
                "ERR_GENERATION_PROFILE_VERSION_MISMATCH",
                "GenerationAttempt provider profile version does not match the registered Prompt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if attempt.output_candidate_id is not None and any(
            item.output_candidate_id == attempt.output_candidate_id for item in self.attempts.values()
        ):
            raise ProductError(
                "ERR_GENERATION_OUTPUT_CANDIDATE_CONFLICT",
                "Production Candidate is already owned by another Generation Attempt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if attempt.parent_attempt_id is not None:
            parent = self.attempts.get(attempt.parent_attempt_id)
            if parent is None:
                raise ProductError("ERR_GENERATION_PARENT_ATTEMPT_NOT_FOUND", "parent_attempt_id does not exist", ProductErrorCategory.DATA_INTEGRITY)
            if parent.slot_id != attempt.slot_id:
                raise ProductError(
                    "ERR_GENERATION_PARENT_SLOT_MISMATCH",
                    "Regeneration parent attempt belongs to a different Slot",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if parent.prompt_id != attempt.prompt_id or parent.prompt_version > attempt.prompt_version:
                raise ProductError(
                    "ERR_GENERATION_PARENT_PROMPT_LINEAGE",
                    "Regeneration parent Prompt lineage is incompatible with this Attempt",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if parent.strategy_level > attempt.strategy_level:
                raise ProductError(
                    "ERR_GENERATION_PARENT_STRATEGY_REGRESSION",
                    "Regeneration strategy must not move backwards from its parent Attempt",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        self.attempts[attempt.generation_job_id] = attempt

    def slot_attempts(self, slot_id: str) -> tuple[GenerationAttempt, ...]:
        return tuple(item for item in self.attempts.values() if item.slot_id == slot_id)


class AdaptiveRegenerationRouter:
    @staticmethod
    def next_strategy(
        attempts: Iterable[GenerationAttempt],
        *,
        repeated_failure_threshold: int = 2,
    ) -> RegenerationStrategy:
        if repeated_failure_threshold < 2:
            raise ValueError("repeated_failure_threshold must be >= 2")
        rows = tuple(attempts)
        if not rows:
            return RegenerationStrategy.TEXT_PROMPT
        last = rows[-1]
        if last.result is GenerationResult.PASS:
            return last.strategy_level
        if last.result is GenerationResult.HUMAN_REQUIRED:
            return RegenerationStrategy.HUMAN_COMPOSITION_FIX
        if not last.failure_codes:
            return last.strategy_level
        streak = 0
        target = set(last.failure_codes)
        for attempt in reversed(rows):
            if attempt.result is not GenerationResult.FAIL or not target.intersection(attempt.failure_codes):
                break
            streak += 1
        if streak < repeated_failure_threshold:
            return last.strategy_level
        return RegenerationStrategy(min(int(last.strategy_level) + 1, int(RegenerationStrategy.HUMAN_COMPOSITION_FIX)))
