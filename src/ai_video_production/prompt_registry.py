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
from .serialization import canonical_json_bytes, sha256_bytes


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
class PromptCompilationBinding:
    compilation_version: str
    compilation_manifest_ref: str
    compilation_sha256: str
    source_ja_ref: str
    source_ja_sha256: str
    normalized_ja_ref: str
    normalized_ja_sha256: str
    runtime_en_ref: str
    runtime_en_sha256: str
    negative_prompt_ref: str | None
    negative_prompt_sha256: str | None
    proofreading_state: str
    manual_english_override_state: str
    director_sha256: str
    blueprint_world_lock_sha256: str
    narration_intent_sha256: str
    music_direction_sha256: str
    se_intent_sha256: str
    ambience_intent_sha256: str
    generate_bgm: bool
    generate_se: bool
    generate_ambience: bool
    provider_profile_id: str
    provider_profile_version: str
    provider_profile_sha256: str
    selected_route_id: str
    required_capabilities: tuple[str, ...]
    input_asset_hashes: tuple[str, ...]
    scene_id: str
    slot_id: str

    def __post_init__(self) -> None:
        if self.compilation_version != "1.0.0":
            raise ValueError("compilation_version is unsupported")
        for name in (
            "compilation_manifest_ref", "source_ja_ref", "normalized_ja_ref", "runtime_en_ref",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("project-private://") or len(value) > 1000:
                raise ValueError(f"{name} is invalid")
        for name in (
            "compilation_sha256", "source_ja_sha256", "normalized_ja_sha256", "runtime_en_sha256",
            "director_sha256", "blueprint_world_lock_sha256", "narration_intent_sha256",
            "music_direction_sha256", "se_intent_sha256", "ambience_intent_sha256",
            "provider_profile_sha256",
        ):
            _sha(getattr(self, name), name)
        if (self.negative_prompt_ref is None) != (self.negative_prompt_sha256 is None):
            raise ValueError("negative Prompt identity is incomplete")
        if self.negative_prompt_ref is not None:
            if not self.negative_prompt_ref.startswith("project-private://") or len(self.negative_prompt_ref) > 1000:
                raise ValueError("negative_prompt_ref is invalid")
            _sha(self.negative_prompt_sha256, "negative_prompt_sha256")
        if self.proofreading_state not in {"NOT_REQUESTED", "AI_PROOFREAD", "HUMAN_REVIEWED"}:
            raise ValueError("proofreading_state is invalid")
        if self.manual_english_override_state not in {"NONE", "ACTIVE"}:
            raise ValueError("manual_english_override_state is invalid")
        for name in ("generate_bgm", "generate_se", "generate_ambience"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")
        for name in ("provider_profile_id", "selected_route_id", "scene_id", "slot_id"):
            _id(getattr(self, name), name)
        if not isinstance(self.provider_profile_version, str) or not self.provider_profile_version.strip():
            raise ValueError("provider_profile_version is invalid")
        for name, values in (
            ("required_capabilities", self.required_capabilities),
            ("input_asset_hashes", self.input_asset_hashes),
        ):
            if not isinstance(values, tuple) or len(set(values)) != len(values):
                raise ValueError(f"{name} is invalid")
        if not self.required_capabilities or tuple(sorted(self.required_capabilities)) != self.required_capabilities:
            raise ValueError("required_capabilities must be non-empty and sorted")
        for capability in self.required_capabilities:
            _id(capability, "required_capability")
        for value in self.input_asset_hashes:
            _sha(value, "input_asset_hash")

    @classmethod
    def from_manifest(cls, *, manifest_ref: str, manifest: dict[str, Any]) -> "PromptCompilationBinding":
        expected = {
            "compilation_version", "project_id", "scene_id", "slot_id", "source_ja_ref",
            "source_ja_sha256", "normalized_ja_ref", "normalized_ja_sha256", "runtime_en_ref",
            "runtime_en_sha256", "negative_prompt_ref", "negative_prompt_sha256",
            "proofreading_state", "manual_english_override_state", "director_sha256",
            "blueprint_world_lock_sha256", "narration_intent_sha256", "music_direction_sha256",
            "se_intent_sha256", "ambience_intent_sha256", "generate_bgm", "generate_se",
            "generate_ambience", "provider_profile_id", "provider_profile_version",
            "provider_profile_sha256", "selected_route_id", "required_capabilities",
            "input_asset_hashes", "prompt_bodies_embedded", "provider_execution_started",
            "compilation_sha256",
        }
        if not isinstance(manifest, dict) or set(manifest) != expected:
            raise ValueError("compilation manifest fields are invalid")
        if manifest["prompt_bodies_embedded"] is not False or manifest["provider_execution_started"] is not False:
            raise ValueError("compilation manifest violates authority boundary")
        body = {key: value for key, value in manifest.items() if key != "compilation_sha256"}
        if manifest["compilation_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("compilation manifest checksum is invalid")
        return cls(
            compilation_version=manifest["compilation_version"],
            compilation_manifest_ref=manifest_ref,
            compilation_sha256=manifest["compilation_sha256"],
            source_ja_ref=manifest["source_ja_ref"], source_ja_sha256=manifest["source_ja_sha256"],
            normalized_ja_ref=manifest["normalized_ja_ref"], normalized_ja_sha256=manifest["normalized_ja_sha256"],
            runtime_en_ref=manifest["runtime_en_ref"], runtime_en_sha256=manifest["runtime_en_sha256"],
            negative_prompt_ref=manifest["negative_prompt_ref"], negative_prompt_sha256=manifest["negative_prompt_sha256"],
            proofreading_state=manifest["proofreading_state"],
            manual_english_override_state=manifest["manual_english_override_state"],
            director_sha256=manifest["director_sha256"],
            blueprint_world_lock_sha256=manifest["blueprint_world_lock_sha256"],
            narration_intent_sha256=manifest["narration_intent_sha256"],
            music_direction_sha256=manifest["music_direction_sha256"],
            se_intent_sha256=manifest["se_intent_sha256"],
            ambience_intent_sha256=manifest["ambience_intent_sha256"],
            generate_bgm=manifest["generate_bgm"], generate_se=manifest["generate_se"],
            generate_ambience=manifest["generate_ambience"],
            provider_profile_id=manifest["provider_profile_id"],
            provider_profile_version=manifest["provider_profile_version"],
            provider_profile_sha256=manifest["provider_profile_sha256"],
            selected_route_id=manifest["selected_route_id"],
            required_capabilities=tuple(manifest["required_capabilities"]),
            input_asset_hashes=tuple(manifest["input_asset_hashes"]),
            scene_id=manifest["scene_id"], slot_id=manifest["slot_id"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "compilation_version": self.compilation_version,
            "compilation_manifest_ref": self.compilation_manifest_ref,
            "compilation_sha256": self.compilation_sha256,
            "source_ja_ref": self.source_ja_ref, "source_ja_sha256": self.source_ja_sha256,
            "normalized_ja_ref": self.normalized_ja_ref, "normalized_ja_sha256": self.normalized_ja_sha256,
            "runtime_en_ref": self.runtime_en_ref, "runtime_en_sha256": self.runtime_en_sha256,
            "negative_prompt_ref": self.negative_prompt_ref, "negative_prompt_sha256": self.negative_prompt_sha256,
            "proofreading_state": self.proofreading_state,
            "manual_english_override_state": self.manual_english_override_state,
            "director_sha256": self.director_sha256,
            "blueprint_world_lock_sha256": self.blueprint_world_lock_sha256,
            "narration_intent_sha256": self.narration_intent_sha256,
            "music_direction_sha256": self.music_direction_sha256,
            "se_intent_sha256": self.se_intent_sha256,
            "ambience_intent_sha256": self.ambience_intent_sha256,
            "generate_bgm": self.generate_bgm, "generate_se": self.generate_se,
            "generate_ambience": self.generate_ambience,
            "provider_profile_id": self.provider_profile_id,
            "provider_profile_version": self.provider_profile_version,
            "provider_profile_sha256": self.provider_profile_sha256,
            "selected_route_id": self.selected_route_id,
            "required_capabilities": list(self.required_capabilities),
            "input_asset_hashes": list(self.input_asset_hashes),
            "scene_id": self.scene_id, "slot_id": self.slot_id,
            "prompt_bodies_embedded": False, "provider_execution_started": False,
        }


@dataclass(frozen=True, slots=True)
class PromptRegenerationBinding:
    """Immutable intended lineage for one regenerated Prompt version."""

    binding_version: str
    parent_prompt_id: str
    parent_prompt_version: int
    parent_prompt_sha256: str
    parent_attempt_id: str
    strategy_level: RegenerationStrategy
    reason_codes: tuple[str, ...]
    regeneration_plan_sha256: str

    def __post_init__(self) -> None:
        if self.binding_version != "1.0.0":
            raise ValueError("regeneration binding version is invalid")
        _id(self.parent_prompt_id, "parent_prompt_id")
        if (
            isinstance(self.parent_prompt_version, bool)
            or not isinstance(self.parent_prompt_version, int)
            or self.parent_prompt_version < 1
        ):
            raise ValueError("parent_prompt_version must be >= 1")
        _sha(self.parent_prompt_sha256, "parent_prompt_sha256")
        _id(self.parent_attempt_id, "parent_attempt_id")
        if not isinstance(self.strategy_level, RegenerationStrategy):
            raise ValueError("strategy_level is invalid")
        if not isinstance(self.reason_codes, tuple) or not self.reason_codes:
            raise ValueError("reason_codes must be a non-empty tuple")
        for value in self.reason_codes:
            _id(value, "reason_code")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("reason_codes must be sorted and unique")
        _sha(self.regeneration_plan_sha256, "regeneration_plan_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_version": self.binding_version,
            "parent_prompt_id": self.parent_prompt_id,
            "parent_prompt_version": self.parent_prompt_version,
            "parent_prompt_sha256": self.parent_prompt_sha256,
            "parent_attempt_id": self.parent_attempt_id,
            "strategy_level": int(self.strategy_level),
            "reason_codes": list(self.reason_codes),
            "regeneration_plan_sha256": self.regeneration_plan_sha256,
        }


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
    compilation_binding: PromptCompilationBinding | None = None
    regeneration_binding: PromptRegenerationBinding | None = None

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
        if self.compilation_binding is not None:
            binding = self.compilation_binding
            if not isinstance(binding, PromptCompilationBinding):
                raise ValueError("compilation_binding is invalid")
            if self.body_ref != binding.runtime_en_ref or self.body_sha256 != binding.runtime_en_sha256:
                raise ValueError("compiled Prompt body must equal runtime English identity")
            if self.input_asset_hashes != binding.input_asset_hashes:
                raise ValueError("compiled Prompt input Asset hashes differ from compilation")
            if self.provider_profile_id != binding.provider_profile_id or self.provider_profile_version != binding.provider_profile_version:
                raise ValueError("compiled Prompt Provider profile differs from compilation")
            if self.scene_id != binding.scene_id or self.slot_id != binding.slot_id:
                raise ValueError("compiled Prompt Scene/Slot differs from compilation")
        if self.regeneration_binding is not None:
            binding = self.regeneration_binding
            if not isinstance(binding, PromptRegenerationBinding):
                raise ValueError("regeneration_binding is invalid")
            if self.prompt_version != binding.parent_prompt_version + 1:
                raise ValueError("regenerated Prompt must immediately follow its parent version")
            if self.prompt_id != binding.parent_prompt_id:
                raise ValueError("regenerated Prompt ID differs from its parent lineage")

    def to_dict(self) -> dict[str, Any]:
        value = {
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
        if self.compilation_binding is not None:
            value["compilation_binding"] = self.compilation_binding.to_dict()
        if self.regeneration_binding is not None:
            value["regeneration_binding"] = self.regeneration_binding.to_dict()
        return value


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
        binding = prompt.regeneration_binding
        if binding is not None and (
            attempt.parent_attempt_id != binding.parent_attempt_id
            or attempt.strategy_level is not binding.strategy_level
        ):
            raise ProductError(
                "ERR_GENERATION_REGENERATION_BINDING_MISMATCH",
                "Generation Attempt differs from the immutable Prompt regeneration binding",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self.attempts[attempt.generation_job_id] = attempt

    def require_regeneration_binding_valid(self, prompt: PromptEntity) -> None:
        binding = prompt.regeneration_binding
        if binding is None:
            return
        parent_prompt = self.prompts.get((binding.parent_prompt_id, binding.parent_prompt_version))
        parent_attempt = self.attempts.get(binding.parent_attempt_id)
        if parent_prompt is None or parent_prompt.body_sha256 != binding.parent_prompt_sha256:
            raise ProductError(
                "ERR_PROMPT_REGENERATION_PARENT_PROMPT_MISMATCH",
                "Prompt regeneration binding references a missing or changed parent Prompt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if (
            parent_attempt is None
            or parent_attempt.prompt_id != binding.parent_prompt_id
            or parent_attempt.prompt_version != binding.parent_prompt_version
            or parent_attempt.prompt_sha256 != binding.parent_prompt_sha256
            or parent_attempt.slot_id != prompt.slot_id
        ):
            raise ProductError(
                "ERR_PROMPT_REGENERATION_PARENT_ATTEMPT_MISMATCH",
                "Prompt regeneration binding references an incompatible parent Attempt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if parent_attempt.strategy_level > binding.strategy_level:
            raise ProductError(
                "ERR_PROMPT_REGENERATION_STRATEGY_REGRESSION",
                "Prompt regeneration Strategy moves backwards from its parent Attempt",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    def validate_regeneration_bindings(self) -> None:
        for prompt in self.prompts.values():
            self.require_regeneration_binding_valid(prompt)

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
