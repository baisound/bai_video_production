"""TASK-042 P-V6-3 immutable Visual Prompt compilation.

Private prompt bodies exist only on the in-memory result.  Durable/public
serialization exposes references, hashes, structured intent hashes and explicit
non-execution flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_DIRECTOR_FIELDS = (
    "world", "before", "now", "trace", "physics", "place", "owner_constraints",
    "subject", "space", "off_screen", "camera", "light", "frame", "after",
)


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _text(value: str, name: str, *, maximum: int = 100_000) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > maximum:
        raise ValueError(f"{name} is invalid")
    return value


def _optional_text(value: str | None, name: str, *, maximum: int = 100_000) -> str | None:
    if value is None:
        return None
    return _text(value, name, maximum=maximum)


def _string_tuple(value: tuple[str, ...], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, tuple) or (not allow_empty and not value):
        raise ValueError(f"{name} is invalid")
    for item in value:
        _text(item, name, maximum=2_000)
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must be unique")
    return value


class ProofreadingState(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    AI_PROOFREAD = "AI_PROOFREAD"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"


class ManualEnglishOverrideState(str, Enum):
    NONE = "NONE"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True)
class VisualPromptCompilationRequest:
    project_id: str
    scene_id: str
    slot_id: str
    blueprint_world_lock_sha256: str
    provider_profile_id: str
    provider_profile_version: str
    provider_profile_sha256: str
    selected_route_id: str
    required_capabilities: tuple[str, ...]
    input_asset_hashes: tuple[str, ...]
    source_ja_ref: str
    source_ja: str
    normalized_ja_ref: str
    normalized_ja: str
    runtime_en_ref: str
    runtime_en: str
    proofreading_state: ProofreadingState
    manual_english_override_state: ManualEnglishOverrideState
    world: tuple[str, ...]
    before: tuple[str, ...]
    now: tuple[str, ...]
    trace: tuple[str, ...]
    physics: tuple[str, ...]
    place: tuple[str, ...]
    owner_constraints: tuple[str, ...]
    subject: tuple[str, ...]
    space: tuple[str, ...]
    off_screen: tuple[str, ...]
    camera: tuple[str, ...]
    light: tuple[str, ...]
    frame: tuple[str, ...]
    after: tuple[str, ...]
    narration_intent: str
    music_direction: str
    se_intent: str
    ambience_intent: str
    generate_bgm: bool
    generate_se: bool
    generate_ambience: bool
    negative_prompt_ref: str | None = None
    negative_prompt: str | None = None

    def __post_init__(self) -> None:
        for name in ("project_id", "scene_id", "slot_id", "provider_profile_id", "selected_route_id"):
            _id(getattr(self, name), name)
        _text(self.provider_profile_version, "provider_profile_version", maximum=100)
        _sha(self.blueprint_world_lock_sha256, "blueprint_world_lock_sha256")
        _sha(self.provider_profile_sha256, "provider_profile_sha256")
        if not isinstance(self.proofreading_state, ProofreadingState):
            raise ValueError("proofreading_state is invalid")
        if not isinstance(self.manual_english_override_state, ManualEnglishOverrideState):
            raise ValueError("manual_english_override_state is invalid")
        _string_tuple(self.required_capabilities, "required_capabilities", allow_empty=False)
        if tuple(sorted(self.required_capabilities)) != self.required_capabilities:
            raise ValueError("required_capabilities must be sorted")
        _string_tuple(self.input_asset_hashes, "input_asset_hashes")
        for value in self.input_asset_hashes:
            _sha(value, "input_asset_hash")
        for name in ("source_ja_ref", "normalized_ja_ref", "runtime_en_ref"):
            _text(getattr(self, name), name, maximum=1_000)
        for name in ("source_ja", "normalized_ja", "runtime_en"):
            _text(getattr(self, name), name)
        for name in _DIRECTOR_FIELDS:
            _string_tuple(getattr(self, name), name)
        for name in ("narration_intent", "music_direction", "se_intent", "ambience_intent"):
            _text(getattr(self, name), name, maximum=10_000)
        for name in ("generate_bgm", "generate_se", "generate_ambience"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")
        _optional_text(self.negative_prompt_ref, "negative_prompt_ref", maximum=1_000)
        _optional_text(self.negative_prompt, "negative_prompt")
        if (self.negative_prompt_ref is None) != (self.negative_prompt is None):
            raise ValueError("negative prompt ref and body must be supplied together")


@dataclass(frozen=True, slots=True)
class PromptCompilationResult:
    source_ja: str
    normalized_ja: str
    runtime_en: str
    negative_prompt: str | None
    _manifest: Mapping[str, Any]

    def to_manifest(self) -> dict[str, Any]:
        """Return a body-free durable/public copy."""
        return {key: list(value) if isinstance(value, tuple) else value for key, value in self._manifest.items()}


class PromptCompilationService:
    VERSION = "1.0.0"

    @staticmethod
    def compile(request: VisualPromptCompilationRequest) -> PromptCompilationResult:
        director = {
            "project_id": request.project_id,
            "scene_id": request.scene_id,
            "slot_id": request.slot_id,
            **{name: list(getattr(request, name)) for name in _DIRECTOR_FIELDS},
        }
        director_sha = sha256_bytes(canonical_json_bytes(director))
        intent_hashes = {
            "narration_intent_sha256": sha256_bytes(request.narration_intent.encode("utf-8")),
            "music_direction_sha256": sha256_bytes(request.music_direction.encode("utf-8")),
            "se_intent_sha256": sha256_bytes(request.se_intent.encode("utf-8")),
            "ambience_intent_sha256": sha256_bytes(request.ambience_intent.encode("utf-8")),
        }
        manifest: dict[str, Any] = {
            "compilation_version": PromptCompilationService.VERSION,
            "project_id": request.project_id,
            "scene_id": request.scene_id,
            "slot_id": request.slot_id,
            "source_ja_ref": request.source_ja_ref,
            "source_ja_sha256": sha256_bytes(request.source_ja.encode("utf-8")),
            "normalized_ja_ref": request.normalized_ja_ref,
            "normalized_ja_sha256": sha256_bytes(request.normalized_ja.encode("utf-8")),
            "runtime_en_ref": request.runtime_en_ref,
            "runtime_en_sha256": sha256_bytes(request.runtime_en.encode("utf-8")),
            "negative_prompt_ref": request.negative_prompt_ref,
            "negative_prompt_sha256": None if request.negative_prompt is None else sha256_bytes(request.negative_prompt.encode("utf-8")),
            "proofreading_state": request.proofreading_state.value,
            "manual_english_override_state": request.manual_english_override_state.value,
            "director_sha256": director_sha,
            "blueprint_world_lock_sha256": request.blueprint_world_lock_sha256,
            **intent_hashes,
            "generate_bgm": request.generate_bgm,
            "generate_se": request.generate_se,
            "generate_ambience": request.generate_ambience,
            "provider_profile_id": request.provider_profile_id,
            "provider_profile_version": request.provider_profile_version,
            "provider_profile_sha256": request.provider_profile_sha256,
            "selected_route_id": request.selected_route_id,
            "required_capabilities": request.required_capabilities,
            "input_asset_hashes": request.input_asset_hashes,
            "prompt_bodies_embedded": False,
            "provider_execution_started": False,
        }
        manifest["compilation_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
        return PromptCompilationResult(
            source_ja=request.source_ja,
            normalized_ja=request.normalized_ja,
            runtime_en=request.runtime_en,
            negative_prompt=request.negative_prompt,
            _manifest=MappingProxyType(manifest),
        )


__all__ = [
    "ManualEnglishOverrideState",
    "PromptCompilationResult",
    "PromptCompilationService",
    "ProofreadingState",
    "VisualPromptCompilationRequest",
]
