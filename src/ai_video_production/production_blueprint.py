"""Validated Scene Ledger foundation derived from real production workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


class ReferenceKind(str, Enum):
    PERSON = "PERSON"
    SPACE = "SPACE"
    PROMPT = "PROMPT"
    ASSET = "ASSET"
    AUDIO = "AUDIO"


class ReferenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PLANNED = "PLANNED"
    LOCKED = "LOCKED"


class AssetSourceStrategy(str, Enum):
    REAL_CAPTURE = "REAL_CAPTURE"
    REUSE_EXISTING = "REUSE_EXISTING"
    COMPOSITE = "COMPOSITE"
    AI_GENERATED = "AI_GENERATED"

    @property
    def trust_priority(self) -> int:
        return list(AssetSourceStrategy).index(self)


class GenerationRisk(str, Enum):
    A_LOW_TEXT = "A_LOW_TEXT"
    B_HEADLINE = "B_HEADLINE"
    C_DENSE_UI = "C_DENSE_UI"


class CameraMotion(str, Enum):
    STATIC = "STATIC"
    SUBTLE = "SUBTLE"
    DYNAMIC = "DYNAMIC"


_REFERENCE_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:[-_][A-Z0-9]+){1,7}$")
_SCENE_ID = re.compile(r"^SC[0-9]{2,3}(?:-[A-Z])?$")


@dataclass(frozen=True, slots=True)
class BlueprintReference:
    reference_id: str
    kind: ReferenceKind
    status: ReferenceStatus
    filename: str | None = None

    def __post_init__(self) -> None:
        if not _REFERENCE_ID.fullmatch(self.reference_id):
            raise ValueError("reference_id must be a stable uppercase identifier")
        if self.filename is not None:
            if not self.filename or "\x00" in self.filename or "/" in self.filename or "\\" in self.filename:
                raise ValueError("reference filename must be a basename")
            if self.status is ReferenceStatus.PLANNED:
                raise ValueError("planned references cannot claim an existing filename")

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_id": self.reference_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "filename": self.filename,
        }


@dataclass(frozen=True, slots=True)
class SceneAudioPlan:
    narration: bool = False
    dialogue: bool = False
    sound_effects: tuple[str, ...] = ()
    bgm: bool = True
    sound_logo: bool = False

    def __post_init__(self) -> None:
        if len(self.sound_effects) > 32:
            raise ValueError("a scene supports at most 32 sound-effect intents")
        for item in self.sound_effects:
            if not item.strip() or len(item) > 128 or "\x00" in item:
                raise ValueError("sound-effect intent is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "narration": self.narration,
            "dialogue": self.dialogue,
            "sound_effects": list(self.sound_effects),
            "bgm": self.bgm,
            "sound_logo": self.sound_logo,
        }


@dataclass(frozen=True, slots=True)
class BlueprintScene:
    scene_id: str
    start_frame: int
    end_frame: int
    narrative_role: str
    source_strategy: AssetSourceStrategy
    generation_risk: GenerationRisk
    camera_motion: CameraMotion
    reference_ids: tuple[str, ...]
    audio: SceneAudioPlan = SceneAudioPlan()
    locked_reference: bool = False
    post_composite_text: bool = False
    final_hold_frames: int = 0

    def __post_init__(self) -> None:
        if not _SCENE_ID.fullmatch(self.scene_id):
            raise ValueError("scene_id must use SC01 or SC09-A form")
        if self.start_frame < 0 or self.end_frame <= self.start_frame:
            raise ValueError("scene frame range must be positive and end-exclusive")
        if not self.narrative_role.strip() or len(self.narrative_role) > 256 or "\x00" in self.narrative_role:
            raise ValueError("narrative_role is invalid")
        if len(set(self.reference_ids)) != len(self.reference_ids):
            raise ValueError("scene reference_ids must be unique")
        if self.final_hold_frames < 0 or self.final_hold_frames >= self.end_frame - self.start_frame:
            raise ValueError("final_hold_frames must fit inside the scene")
        if self.generation_risk is GenerationRisk.C_DENSE_UI:
            if not self.locked_reference or self.camera_motion is not CameraMotion.STATIC:
                raise ValueError("dense UI scenes require a locked reference and static camera")
            if not self.post_composite_text:
                raise ValueError("dense UI text must be composed after generation")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "range_frames": {"start": self.start_frame, "end_exclusive": self.end_frame},
            "narrative_role": self.narrative_role,
            "source_strategy": self.source_strategy.value,
            "generation_risk": self.generation_risk.value,
            "camera_motion": self.camera_motion.value,
            "reference_ids": list(self.reference_ids),
            "audio": self.audio.to_dict(),
            "locked_reference": self.locked_reference,
            "post_composite_text": self.post_composite_text,
            "final_hold_frames": self.final_hold_frames,
        }


@dataclass(frozen=True, slots=True)
class ProductionBlueprint:
    blueprint_id: str
    title: str
    timeline_rate: FrameRate
    target_duration_frames: int
    references: tuple[BlueprintReference, ...]
    scenes: tuple[BlueprintScene, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"BP-[A-Z0-9][A-Z0-9._-]{2,63}", self.blueprint_id):
            raise ValueError("blueprint_id is invalid")
        if not self.title.strip() or len(self.title) > 256 or "\x00" in self.title:
            raise ValueError("title is invalid")
        if self.target_duration_frames <= 0:
            raise ValueError("target_duration_frames must be positive")
        reference_ids = [item.reference_id for item in self.references]
        if len(reference_ids) != len(set(reference_ids)):
            raise ValueError("reference registry contains duplicate IDs")
        known = set(reference_ids)
        cursor = 0
        scene_ids: set[str] = set()
        for scene in self.scenes:
            if scene.scene_id in scene_ids:
                raise ValueError("scene ledger contains duplicate scene IDs")
            if scene.start_frame != cursor:
                raise ValueError("scene ledger must cover the Timeline without gaps or overlaps")
            missing = set(scene.reference_ids) - known
            if missing:
                raise ValueError("scene references an undeclared registry ID")
            scene_ids.add(scene.scene_id)
            cursor = scene.end_frame
        if cursor != self.target_duration_frames:
            raise ValueError("scene ledger must end at target_duration_frames")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "blueprint_version": "1.0.0",
            "blueprint_id": self.blueprint_id,
            "title": self.title,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "target_duration_frames": self.target_duration_frames,
            "asset_source_priority": [item.value for item in AssetSourceStrategy],
            "references": [item.to_dict() for item in self.references],
            "scenes": [item.to_dict() for item in self.scenes],
        }
        body["blueprint_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body
