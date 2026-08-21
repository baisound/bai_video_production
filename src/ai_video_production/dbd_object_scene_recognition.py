"""Fail-closed Tier 3 DbD object/scene recognition baseline."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Sequence

from .canonical_game_event import GameKnowledgeKind
from .dbd_hud_detectors import RecognitionCandidate, ReferenceSliceClassifier
from .dbd_vision_slices import GrayImage, NormalizedROI, ReferenceSliceIndex
from .serialization import sha256_bytes


_ID = re.compile(r"^[a-z][a-z0-9_]{1,127}$")


class ObjectSceneKind(str, Enum):
    PALLET = "PALLET"
    WINDOW = "WINDOW"
    MAP_FEATURE = "MAP_FEATURE"
    MAIN_BUILDING = "MAIN_BUILDING"
    TILE = "TILE"


class ObjectSceneRecognitionStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    HARD_NEGATIVE = "HARD_NEGATIVE"
    ABSTAINED = "ABSTAINED"
    CONTRADICTION = "CONTRADICTION"


@dataclass(frozen=True, slots=True)
class ObjectSceneDefinition:
    object_id: str
    kind: ObjectSceneKind
    owner_kind: GameKnowledgeKind
    map_id: str = ""

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.object_id):
            raise ValueError("object_id must be a canonical lowercase identifier")
        if not isinstance(self.kind, ObjectSceneKind) or not isinstance(self.owner_kind, GameKnowledgeKind):
            raise ValueError("invalid object/scene definition enum")
        allowed = {
            ObjectSceneKind.PALLET: {GameKnowledgeKind.MECHANIC},
            ObjectSceneKind.WINDOW: {GameKnowledgeKind.MECHANIC},
            ObjectSceneKind.MAP_FEATURE: {GameKnowledgeKind.MAP},
            ObjectSceneKind.MAIN_BUILDING: {GameKnowledgeKind.MAP},
            ObjectSceneKind.TILE: {GameKnowledgeKind.TILE},
        }
        if self.owner_kind not in allowed[self.kind]:
            raise ValueError("object/scene kind and canonical owner disagree")
        if self.map_id and not _ID.fullmatch(self.map_id):
            raise ValueError("map_id must be canonical when present")
        if self.kind in {ObjectSceneKind.MAP_FEATURE, ObjectSceneKind.MAIN_BUILDING} and not self.map_id:
            raise ValueError("map-bound scene definition requires map_id")

    @property
    def label(self) -> str:
        return f"OBJECT_SCENE/{self.kind.value}/{self.object_id}"


def hard_negative_label(negative_id: str) -> str:
    if not _ID.fullmatch(negative_id):
        raise ValueError("hard-negative id must be canonical")
    return f"OBJECT_SCENE/HARD_NEGATIVE/{negative_id}"


@dataclass(frozen=True, slots=True)
class ObjectSceneCrop:
    frame_index: int
    roi: NormalizedROI
    image: GrayImage
    evidence_ref: str
    map_id: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.frame_index, bool) or not isinstance(self.frame_index, int) or self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if not isinstance(self.roi, NormalizedROI) or not isinstance(self.image, GrayImage):
            raise ValueError("object/scene crop requires ROI and GrayImage")
        if not self.evidence_ref.strip() or len(self.evidence_ref) > 1024:
            raise ValueError("evidence_ref must be bounded text")
        if self.map_id and not _ID.fullmatch(self.map_id):
            raise ValueError("map_id must be canonical when present")

    @property
    def crop_sha256(self) -> str:
        body = f"{self.image.width}x{self.image.height}\0".encode("ascii") + self.image.pixels
        return sha256_bytes(body)


@dataclass(frozen=True, slots=True)
class ObjectSceneRecognition:
    status: ObjectSceneRecognitionStatus
    frame_index: int
    roi_id: str
    object_id: str | None
    kind: ObjectSceneKind | None
    owner_kind: GameKnowledgeKind | None
    map_id: str
    confidence_milli: int
    candidates: tuple[RecognitionCandidate, ...]
    crop_sha256: str
    evidence_ref: str
    reason_codes: tuple[str, ...]
    event_claim_allowed: bool = False


class ObjectSceneRecognizer:
    """Classify caller-provided bounded crops; never infer action events."""

    def __init__(
        self,
        index: ReferenceSliceIndex,
        *,
        definitions: Sequence[ObjectSceneDefinition],
        acceptance_milli: int = 820,
        ambiguity_margin_milli: int = 80,
    ) -> None:
        rows = tuple(definitions)
        if not rows or any(not isinstance(item, ObjectSceneDefinition) for item in rows):
            raise ValueError("definitions must be non-empty ObjectSceneDefinition values")
        self.definitions = {item.label: item for item in rows}
        if len(self.definitions) != len(rows) or len({item.object_id for item in rows}) != len(rows):
            raise ValueError("object/scene definitions must be unique")
        labels = {item.label for item in index.references}
        malformed_hard_negatives = {
            label for label in labels
            if label.startswith("OBJECT_SCENE/HARD_NEGATIVE/")
            and not _ID.fullmatch(label.removeprefix("OBJECT_SCENE/HARD_NEGATIVE/"))
        }
        if malformed_hard_negatives:
            raise ValueError("reference index contains malformed hard-negative labels")
        unsupported = {
            label for label in labels
            if label not in self.definitions and not label.startswith("OBJECT_SCENE/HARD_NEGATIVE/")
        }
        if unsupported:
            raise ValueError("reference index contains unregistered object/scene labels")
        if not labels.intersection(self.definitions) or not any(
            label.startswith("OBJECT_SCENE/HARD_NEGATIVE/") for label in labels
        ):
            raise ValueError("object/scene index requires identity and hard-negative coverage")
        self.classifier = ReferenceSliceClassifier(
            index, acceptance_milli=acceptance_milli,
            ambiguity_margin_milli=ambiguity_margin_milli,
        )

    def recognize(self, crop: ObjectSceneCrop) -> ObjectSceneRecognition:
        if not isinstance(crop, ObjectSceneCrop):
            raise ValueError("crop must be ObjectSceneCrop")
        result = self.classifier.classify(crop.image, top_k=4)
        base = dict(
            frame_index=crop.frame_index, roi_id=crop.roi.roi_id,
            map_id=crop.map_id, confidence_milli=result.confidence_milli,
            candidates=result.candidates, crop_sha256=crop.crop_sha256,
            evidence_ref=crop.evidence_ref, event_claim_allowed=False,
        )
        if result.unknown:
            return ObjectSceneRecognition(
                ObjectSceneRecognitionStatus.ABSTAINED, object_id=None, kind=None,
                owner_kind=None, reason_codes=("OBJECT_SCENE_IDENTITY_UNKNOWN",), **base,
            )
        if result.selected_label.startswith("OBJECT_SCENE/HARD_NEGATIVE/"):
            return ObjectSceneRecognition(
                ObjectSceneRecognitionStatus.HARD_NEGATIVE, object_id=None, kind=None,
                owner_kind=None, reason_codes=("OBJECT_SCENE_HARD_NEGATIVE",), **base,
            )
        definition = self.definitions.get(result.selected_label)
        if definition is None:
            return ObjectSceneRecognition(
                ObjectSceneRecognitionStatus.CONTRADICTION, object_id=None, kind=None,
                owner_kind=None, reason_codes=("UNREGISTERED_OBJECT_SCENE_LABEL",), **base,
            )
        if definition.map_id and crop.map_id != definition.map_id:
            return ObjectSceneRecognition(
                ObjectSceneRecognitionStatus.CONTRADICTION,
                object_id=definition.object_id, kind=definition.kind,
                owner_kind=definition.owner_kind,
                reason_codes=("OBJECT_SCENE_MAP_NAMESPACE_MISMATCH",), **base,
            )
        return ObjectSceneRecognition(
            ObjectSceneRecognitionStatus.IDENTIFIED,
            object_id=definition.object_id, kind=definition.kind,
            owner_kind=definition.owner_kind,
            reason_codes=("OBJECT_SCENE_IDENTITY_MATCHED",), **base,
        )


__all__ = [
    "ObjectSceneCrop", "ObjectSceneDefinition", "ObjectSceneKind",
    "ObjectSceneRecognition", "ObjectSceneRecognitionStatus", "ObjectSceneRecognizer",
    "hard_negative_label",
]
