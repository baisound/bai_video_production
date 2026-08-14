"""Closed Production Blueprint v2 contract with frame-specific references."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from importlib import resources
import re
from typing import Any, Mapping

from .production_blueprint import (
    AssetSourceStrategy,
    BlueprintReference,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
    ReferenceKind,
    ReferenceStatus,
    SceneAudioPlan,
)
from .schema_contracts import validate_instance
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .timebase import FrameRate


class CharacterRole(str, Enum):
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"
    BACKGROUND = "BACKGROUND"


class FrameKind(str, Enum):
    START = "START"
    END = "END"


_IDENTITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SCENE_ID = re.compile(r"^SC[0-9]{2,3}(?:-[A-Z])?$")
_BLUEPRINT_ID = re.compile(r"^BP-[A-Z0-9][A-Z0-9._-]{2,63}$")


def _identity(value: str, field_name: str) -> str:
    if not _IDENTITY_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a stable identifier")
    return value


def _text(value: str, field_name: str, *, maximum: int = 512) -> str:
    if not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} is invalid")
    return value


def _unique_texts(values: tuple[str, ...], field_name: str) -> None:
    if len(values) > 128 or len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique and contain at most 128 items")
    for value in values:
        _text(value, field_name, maximum=256)


@dataclass(frozen=True, slots=True)
class AssetLockBinding:
    asset_id: str
    asset_sha256: str
    slot_id: str
    candidate_id: str

    def __post_init__(self) -> None:
        _identity(self.asset_id, "asset_id")
        validate_sha256(self.asset_sha256, field_name="asset_sha256")
        _identity(self.slot_id, "slot_id")
        _identity(self.candidate_id, "candidate_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class CharacterLockBinding:
    role: CharacterRole
    asset_id: str
    asset_sha256: str
    slot_id: str
    candidate_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, CharacterRole):
            raise ValueError("role must be a CharacterRole")
        _identity(self.asset_id, "asset_id")
        validate_sha256(self.asset_sha256, field_name="asset_sha256")
        _identity(self.slot_id, "slot_id")
        _identity(self.candidate_id, "candidate_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role.value,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class FrameReferenceBinding:
    character_locks: tuple[CharacterLockBinding, ...] = ()
    space_lock: AssetLockBinding | None = None
    composition_lock: AssetLockBinding | None = None

    def __post_init__(self) -> None:
        if any(not isinstance(item, CharacterLockBinding) for item in self.character_locks):
            raise ValueError("character_locks must contain CharacterLockBinding values")
        if self.space_lock is not None and not isinstance(self.space_lock, AssetLockBinding):
            raise ValueError("space_lock must be an AssetLockBinding")
        if self.composition_lock is not None and not isinstance(self.composition_lock, AssetLockBinding):
            raise ValueError("composition_lock must be an AssetLockBinding")
        if len(self.character_locks) > 64:
            raise ValueError("character_locks supports at most 64 ordered bindings")
        if sum(item.role is CharacterRole.PRIMARY for item in self.character_locks) > 1:
            raise ValueError("a frame supports at most one PRIMARY character")
        all_items: tuple[CharacterLockBinding | AssetLockBinding, ...] = self.character_locks + tuple(
            item for item in (self.space_lock, self.composition_lock) if item is not None
        )
        for field_name in ("asset_id", "candidate_id", "slot_id"):
            values = [getattr(item, field_name) for item in all_items]
            if len(values) != len(set(values)):
                raise ValueError(f"frame binding contains duplicate {field_name}")

    def to_dict(self) -> dict[str, object]:
        return {
            "character_locks": [item.to_dict() for item in self.character_locks],
            "space_lock": None if self.space_lock is None else self.space_lock.to_dict(),
            "composition_lock": None if self.composition_lock is None else self.composition_lock.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FrameIntent:
    frame_kind: FrameKind
    visual_intent: str
    task_axis_target: str
    required_visible: tuple[str, ...]
    forbidden_visible: tuple[str, ...]
    depth_order: tuple[str, ...]
    camera_semantic: str
    binding: FrameReferenceBinding
    lens_framing: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.frame_kind, FrameKind):
            raise ValueError("frame_kind must be START or END")
        if not isinstance(self.binding, FrameReferenceBinding):
            raise ValueError("binding must be a FrameReferenceBinding")
        _text(self.visual_intent, "visual_intent", maximum=1024)
        _text(self.task_axis_target, "task_axis_target", maximum=512)
        _text(self.camera_semantic, "camera_semantic", maximum=512)
        if self.lens_framing is not None:
            _text(self.lens_framing, "lens_framing", maximum=256)
        _unique_texts(self.required_visible, "required_visible")
        _unique_texts(self.forbidden_visible, "forbidden_visible")
        _unique_texts(self.depth_order, "depth_order")
        overlap = set(self.required_visible) & set(self.forbidden_visible)
        if overlap:
            raise ValueError("required_visible and forbidden_visible must not overlap")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_kind": self.frame_kind.value,
            "visual_intent": self.visual_intent,
            "task_axis_target": self.task_axis_target,
            "required_visible": list(self.required_visible),
            "forbidden_visible": list(self.forbidden_visible),
            "depth_order": list(self.depth_order),
            "camera_semantic": self.camera_semantic,
            "lens_framing": self.lens_framing,
            "binding": self.binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class BlueprintSceneV2:
    scene_id: str
    start_frame: int
    end_frame: int
    narrative_role: str
    source_strategy: AssetSourceStrategy
    generation_risk: GenerationRisk
    camera_motion: CameraMotion
    start_frame_intent: FrameIntent
    end_frame_intent: FrameIntent
    audio: SceneAudioPlan = SceneAudioPlan()
    post_composite_text: bool = False
    final_hold_frames: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.source_strategy, AssetSourceStrategy):
            raise ValueError("source_strategy is invalid")
        if not isinstance(self.generation_risk, GenerationRisk):
            raise ValueError("generation_risk is invalid")
        if not isinstance(self.camera_motion, CameraMotion):
            raise ValueError("camera_motion is invalid")
        if not isinstance(self.start_frame_intent, FrameIntent) or not isinstance(self.end_frame_intent, FrameIntent):
            raise ValueError("scene frame intents must be FrameIntent values")
        if not isinstance(self.audio, SceneAudioPlan):
            raise ValueError("audio must be a SceneAudioPlan")
        if not _SCENE_ID.fullmatch(self.scene_id):
            raise ValueError("scene_id must use SC01 or SC09-A form")
        if self.start_frame < 0 or self.end_frame <= self.start_frame:
            raise ValueError("scene frame range must be positive and end-exclusive")
        _text(self.narrative_role, "narrative_role", maximum=256)
        if self.start_frame_intent.frame_kind is not FrameKind.START:
            raise ValueError("start_frame_intent must have START frame_kind")
        if self.end_frame_intent.frame_kind is not FrameKind.END:
            raise ValueError("end_frame_intent must have END frame_kind")
        if self.final_hold_frames < 0 or self.final_hold_frames >= self.end_frame - self.start_frame:
            raise ValueError("final_hold_frames must fit inside the scene")
        if self.generation_risk is GenerationRisk.C_DENSE_UI:
            if self.camera_motion is not CameraMotion.STATIC:
                raise ValueError("dense UI scenes require a static camera")
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
            "start_frame_intent": self.start_frame_intent.to_dict(),
            "end_frame_intent": self.end_frame_intent.to_dict(),
            "audio": self.audio.to_dict(),
            "post_composite_text": self.post_composite_text,
            "final_hold_frames": self.final_hold_frames,
        }


@dataclass(frozen=True, slots=True)
class ProductionBlueprintV2:
    blueprint_id: str
    title: str
    timeline_rate: FrameRate
    target_duration_frames: int
    scenes: tuple[BlueprintSceneV2, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.timeline_rate, FrameRate):
            raise ValueError("timeline_rate must be a FrameRate")
        if any(not isinstance(scene, BlueprintSceneV2) for scene in self.scenes):
            raise ValueError("scenes must contain BlueprintSceneV2 values")
        if not _BLUEPRINT_ID.fullmatch(self.blueprint_id):
            raise ValueError("blueprint_id is invalid")
        _text(self.title, "title", maximum=256)
        if self.target_duration_frames <= 0:
            raise ValueError("target_duration_frames must be positive")
        if not self.scenes:
            raise ValueError("scene ledger must not be empty")
        cursor = 0
        scene_ids: set[str] = set()
        for scene in self.scenes:
            if scene.scene_id in scene_ids:
                raise ValueError("scene ledger contains duplicate scene IDs")
            if scene.start_frame != cursor:
                raise ValueError("scene ledger must cover the Timeline without gaps or overlaps")
            scene_ids.add(scene.scene_id)
            cursor = scene.end_frame
        if cursor != self.target_duration_frames:
            raise ValueError("scene ledger must end at target_duration_frames")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "blueprint_version": "2.0.0",
            "blueprint_id": self.blueprint_id,
            "title": self.title,
            "timeline_rate": {
                "numerator": self.timeline_rate.numerator,
                "denominator": self.timeline_rate.denominator,
            },
            "target_duration_frames": self.target_duration_frames,
            "asset_source_priority": [item.value for item in AssetSourceStrategy],
            "scenes": [item.to_dict() for item in self.scenes],
        }
        body["blueprint_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _verify_document_checksum(document: Mapping[str, Any]) -> None:
    claimed = document.get("blueprint_sha256")
    if not isinstance(claimed, str):
        raise ValueError("blueprint_sha256 is required")
    validate_sha256(claimed, field_name="blueprint_sha256")
    body = dict(document)
    del body["blueprint_sha256"]
    if sha256_bytes(canonical_json_bytes(body)) != claimed:
        raise ValueError("blueprint_sha256 does not match the document")


def _schema(name: str) -> Any:
    return resources.files("ai_video_production").joinpath("schema_resources", name)


def parse_production_blueprint_document(document: Mapping[str, Any]) -> ProductionBlueprint | ProductionBlueprintV2:
    """Parse exactly v1 or v2 and reject unknown versions, fields and tampering."""

    if not isinstance(document, Mapping):
        raise ValueError("blueprint document must be an object")
    version = document.get("blueprint_version")
    schema_name = {
        "1.0.0": "production-blueprint.schema.json",
        "2.0.0": "production-blueprint-v2.schema.json",
    }.get(version)
    if schema_name is None:
        raise ValueError("blueprint_version must be exactly 1.0.0 or 2.0.0")
    payload = dict(document)
    validate_instance(payload, _schema(schema_name))
    _verify_document_checksum(payload)
    rate_data = payload["timeline_rate"]
    rate = FrameRate(rate_data["numerator"], rate_data["denominator"])
    if version == "1.0.0":
        references = tuple(
            BlueprintReference(
                item["reference_id"], ReferenceKind(item["kind"]), ReferenceStatus(item["status"]), item["filename"]
            )
            for item in payload["references"]
        )
        scenes = tuple(_parse_scene_v1(item) for item in payload["scenes"])
        return ProductionBlueprint(
            payload["blueprint_id"], payload["title"], rate, payload["target_duration_frames"], references, scenes
        )
    scenes_v2 = tuple(_parse_scene_v2(item) for item in payload["scenes"])
    return ProductionBlueprintV2(
        payload["blueprint_id"], payload["title"], rate, payload["target_duration_frames"], scenes_v2
    )


def _audio(data: Mapping[str, Any]) -> SceneAudioPlan:
    return SceneAudioPlan(
        narration=data["narration"],
        dialogue=data["dialogue"],
        sound_effects=tuple(data["sound_effects"]),
        bgm=data["bgm"],
        sound_logo=data["sound_logo"],
    )


def _parse_scene_v1(data: Mapping[str, Any]) -> BlueprintScene:
    frames = data["range_frames"]
    return BlueprintScene(
        data["scene_id"], frames["start"], frames["end_exclusive"], data["narrative_role"],
        AssetSourceStrategy(data["source_strategy"]), GenerationRisk(data["generation_risk"]),
        CameraMotion(data["camera_motion"]), tuple(data["reference_ids"]), _audio(data["audio"]),
        data["locked_reference"], data["post_composite_text"], data["final_hold_frames"],
    )


def _asset_binding(data: Mapping[str, Any] | None) -> AssetLockBinding | None:
    if data is None:
        return None
    return AssetLockBinding(data["asset_id"], data["asset_sha256"], data["slot_id"], data["candidate_id"])


def _frame_intent(data: Mapping[str, Any]) -> FrameIntent:
    binding_data = data["binding"]
    binding = FrameReferenceBinding(
        tuple(
            CharacterLockBinding(
                CharacterRole(item["role"]), item["asset_id"], item["asset_sha256"],
                item["slot_id"], item["candidate_id"]
            )
            for item in binding_data["character_locks"]
        ),
        _asset_binding(binding_data["space_lock"]),
        _asset_binding(binding_data["composition_lock"]),
    )
    return FrameIntent(
        FrameKind(data["frame_kind"]), data["visual_intent"], data["task_axis_target"],
        tuple(data["required_visible"]), tuple(data["forbidden_visible"]), tuple(data["depth_order"]),
        data["camera_semantic"], binding, data["lens_framing"],
    )


def _parse_scene_v2(data: Mapping[str, Any]) -> BlueprintSceneV2:
    frames = data["range_frames"]
    return BlueprintSceneV2(
        data["scene_id"], frames["start"], frames["end_exclusive"], data["narrative_role"],
        AssetSourceStrategy(data["source_strategy"]), GenerationRisk(data["generation_risk"]),
        CameraMotion(data["camera_motion"]), _frame_intent(data["start_frame_intent"]),
        _frame_intent(data["end_frame_intent"]), _audio(data["audio"]),
        data["post_composite_text"], data["final_hold_frames"],
    )
