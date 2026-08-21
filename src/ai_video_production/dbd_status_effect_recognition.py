"""Reference recognition for segmented bottom-right DbD status icons."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Sequence

from .dbd_hud_detectors import RecognitionCandidate, ReferenceSliceClassifier
from .dbd_hud_visibility import HudVisibility
from .dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    StatusEffectDefinition,
    StatusEffectObservation,
)
from .dbd_status_icon_segmentation import StatusIconSegmentCandidate
from .dbd_vision_slices import GrayImage, ReferenceSliceIndex
from .serialization import sha256_bytes


_EFFECT_ID = re.compile(r"^[a-z][a-z0-9_]{1,127}$")
_PERK_ID = re.compile(r"^perk_[a-z0-9_]{1,122}$")
_NAMESPACE_BY_POLARITY = {
    EffectPolarity.POSITIVE: "STATUS_EFFECT_POSITIVE",
    EffectPolarity.NEGATIVE: "STATUS_EFFECT_NEGATIVE",
}


class StatusEffectReferenceKind(str, Enum):
    IDENTITY = "IDENTITY"
    VISIBILITY = "VISIBILITY"
    PERK_HARD_NEGATIVE = "PERK_HARD_NEGATIVE"


class StatusIconRecognitionStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    VISIBILITY_ONLY = "VISIBILITY_ONLY"
    HARD_NEGATIVE = "HARD_NEGATIVE"
    ABSTAINED = "ABSTAINED"
    CONTRADICTION = "CONTRADICTION"


@dataclass(frozen=True, slots=True)
class StatusEffectReferenceLabel:
    kind: StatusEffectReferenceKind
    polarity: EffectPolarity | None = None
    effect_id: str | None = None
    visibility: HudVisibility | None = None
    perk_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, StatusEffectReferenceKind):
            raise ValueError("invalid status-effect reference kind")
        if self.kind is StatusEffectReferenceKind.IDENTITY:
            if not isinstance(self.polarity, EffectPolarity):
                raise ValueError("identity reference requires polarity")
            if self.effect_id is None or not _EFFECT_ID.fullmatch(self.effect_id):
                raise ValueError("identity reference requires canonical effect_id")
            if self.visibility is not None or self.perk_id is not None:
                raise ValueError("identity reference contains unrelated fields")
        elif self.kind is StatusEffectReferenceKind.VISIBILITY:
            if not isinstance(self.polarity, EffectPolarity):
                raise ValueError("visibility reference requires polarity")
            if self.visibility not in {
                HudVisibility.VISIBLE,
                HudVisibility.PARTIALLY_OCCLUDED,
                HudVisibility.HIDDEN,
                HudVisibility.UNREADABLE,
            }:
                raise ValueError("visibility reference requires an explicit visibility")
            if self.effect_id is not None or self.perk_id is not None:
                raise ValueError("visibility reference contains unrelated fields")
        else:
            if self.perk_id is None or not _PERK_ID.fullmatch(self.perk_id):
                raise ValueError("perk hard-negative requires canonical perk_id")
            if self.polarity is not None or self.effect_id is not None or self.visibility is not None:
                raise ValueError("perk hard-negative contains unrelated fields")

    def encode(self) -> str:
        if self.kind is StatusEffectReferenceKind.PERK_HARD_NEGATIVE:
            return f"PERK_ICON/{self.perk_id}"
        namespace = _NAMESPACE_BY_POLARITY[self.polarity]  # type: ignore[index]
        if self.kind is StatusEffectReferenceKind.IDENTITY:
            return f"{namespace}/{self.effect_id}"
        return f"{namespace}/VISIBILITY/{self.visibility.value}"  # type: ignore[union-attr]

    @classmethod
    def decode(cls, value: str) -> "StatusEffectReferenceLabel":
        if not isinstance(value, str) or not value or len(value) > 256:
            raise ValueError("status-effect reference label must be bounded text")
        parts = value.split("/")
        if len(parts) == 2 and parts[0] == "PERK_ICON":
            return cls(StatusEffectReferenceKind.PERK_HARD_NEGATIVE, perk_id=parts[1])
        polarity = next(
            (item for item, namespace in _NAMESPACE_BY_POLARITY.items() if namespace == parts[0]),
            None,
        )
        if polarity is None:
            raise ValueError("status-effect reference label has an unsupported namespace")
        if len(parts) == 2:
            return cls(StatusEffectReferenceKind.IDENTITY, polarity=polarity, effect_id=parts[1])
        if len(parts) == 3 and parts[1] == "VISIBILITY":
            try:
                visibility = HudVisibility(parts[2])
            except ValueError as exc:
                raise ValueError("status-effect reference label has invalid visibility") from exc
            return cls(StatusEffectReferenceKind.VISIBILITY, polarity=polarity, visibility=visibility)
        raise ValueError("status-effect reference label is not canonical")


@dataclass(frozen=True, slots=True)
class StatusIconRecognition:
    ordinal: int
    region_roi_id: str
    polarity: EffectPolarity
    status: StatusIconRecognitionStatus
    effect_id: str | None
    source_kind: EffectSourceKind
    visibility: HudVisibility
    confidence_milli: int
    candidates: tuple[RecognitionCandidate, ...]
    evidence_ref: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ValueError("status icon ordinal must be non-negative")
        if not self.region_roi_id or len(self.region_roi_id) > 128:
            raise ValueError("status icon region_roi_id must be bounded text")
        if not isinstance(self.polarity, EffectPolarity) or not isinstance(self.status, StatusIconRecognitionStatus):
            raise ValueError("invalid status icon recognition enum")
        expected_region = (
            "bottom_right_positive_effects"
            if self.polarity is EffectPolarity.POSITIVE
            else "bottom_right_negative_effects"
        )
        if self.region_roi_id != expected_region:
            raise ValueError("status icon polarity and region namespace must agree")
        if not isinstance(self.source_kind, EffectSourceKind) or not isinstance(self.visibility, HudVisibility):
            raise ValueError("invalid status icon source or visibility")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if not self.evidence_ref or len(self.evidence_ref) > 1024:
            raise ValueError("evidence_ref must be bounded text")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("reason_codes must be unique and sorted")
        if self.status is StatusIconRecognitionStatus.IDENTIFIED:
            if self.effect_id is None or not _EFFECT_ID.fullmatch(self.effect_id):
                raise ValueError("identified status icon requires canonical effect_id")
            if self.source_kind is EffectSourceKind.UNKNOWN or self.visibility is not HudVisibility.VISIBLE:
                raise ValueError("identified status icon requires known source and VISIBLE state")
        elif self.effect_id is not None or self.source_kind is not EffectSourceKind.UNKNOWN:
            raise ValueError("non-identified status icon cannot claim identity or source")

    def to_temporal_observation(
        self, *, match_id: str, frame_index: int, survivor_slot: int | None = None,
    ) -> StatusEffectObservation:
        if self.status is not StatusIconRecognitionStatus.IDENTIFIED or self.effect_id is None:
            raise ValueError("only an identified status icon can become a temporal observation")
        return StatusEffectObservation(
            match_id=match_id,
            survivor_slot=survivor_slot,
            effect_id=self.effect_id,
            polarity=self.polarity,
            source_kind=self.source_kind,
            active=True,
            stack_or_level=None,
            progress_milli=None,
            confidence_milli=self.confidence_milli,
            frame_index=frame_index,
            evidence_ref=self.evidence_ref,
        )


class StatusEffectIconRecognizer:
    """Classify segmented icons while enforcing registry and namespace truth."""

    def __init__(
        self,
        index: ReferenceSliceIndex,
        *,
        definitions: Sequence[StatusEffectDefinition],
        acceptance_milli: int = 800,
        ambiguity_margin_milli: int = 75,
    ) -> None:
        if not isinstance(index, ReferenceSliceIndex):
            raise ValueError("index must be a ReferenceSliceIndex")
        self.index = index
        definitions = tuple(definitions)
        if not definitions or any(not isinstance(item, StatusEffectDefinition) for item in definitions):
            raise ValueError("definitions must contain StatusEffectDefinition values")
        self.definitions = {item.effect_id: item for item in definitions}
        if len(self.definitions) != len(definitions):
            raise ValueError("status-effect definitions must be non-empty and unique")
        semantics_by_feature: dict[str, set[str]] = {}
        for reference in index.references:
            decoded = StatusEffectReferenceLabel.decode(reference.label)
            if decoded.kind is StatusEffectReferenceKind.IDENTITY:
                definition = self.definitions.get(decoded.effect_id or "")
                if definition is None:
                    raise ValueError("status-effect reference uses an unregistered effect_id")
                if definition.polarity is not decoded.polarity:
                    raise ValueError("status-effect reference polarity contradicts registry")
            semantics_by_feature.setdefault(reference.feature_hex, set()).add(reference.label)
        if any(len(labels) > 1 for labels in semantics_by_feature.values()):
            raise ValueError("one status-icon feature cannot carry conflicting labels")
        self.classifier = ReferenceSliceClassifier(
            index,
            acceptance_milli=acceptance_milli,
            ambiguity_margin_milli=ambiguity_margin_milli,
        )

    @staticmethod
    def crop_segment(image: GrayImage, candidate: StatusIconSegmentCandidate) -> GrayImage:
        if not isinstance(image, GrayImage) or not isinstance(candidate, StatusIconSegmentCandidate):
            raise ValueError("image and candidate must use status recognition contracts")
        roi = candidate.crop_roi
        left = max(0, min(image.width - 1, round(roi.x * image.width)))
        top = max(0, min(image.height - 1, round(roi.y * image.height)))
        right = max(left + 1, min(image.width, round((roi.x + roi.width) * image.width)))
        bottom = max(top + 1, min(image.height, round((roi.y + roi.height) * image.height)))
        width, height = right - left, bottom - top
        pixels = bytearray(width * height)
        for y in range(height):
            source = (top + y) * image.width + left
            pixels[y * width:(y + 1) * width] = image.pixels[source:source + width]
        crop = GrayImage(width, height, bytes(pixels))
        digest_input = f"{crop.width}x{crop.height}\0".encode("ascii") + crop.pixels
        if sha256_bytes(digest_input) != candidate.crop_sha256:
            raise ValueError("status segment crop checksum does not match candidate evidence")
        return crop

    def recognize(
        self,
        image: GrayImage,
        *,
        candidate: StatusIconSegmentCandidate,
        evidence_ref: str,
    ) -> StatusIconRecognition:
        if not isinstance(candidate, StatusIconSegmentCandidate):
            raise ValueError("candidate must be a StatusIconSegmentCandidate")
        classified = self.classifier.classify(image, top_k=3)
        confidence = min(candidate.segmentation_score_milli, classified.confidence_milli)
        common = dict(
            ordinal=candidate.ordinal,
            region_roi_id=candidate.region_roi_id,
            polarity=candidate.polarity,
            confidence_milli=confidence,
            candidates=classified.candidates,
            evidence_ref=evidence_ref,
        )
        if classified.unknown:
            return StatusIconRecognition(
                **common,
                status=StatusIconRecognitionStatus.ABSTAINED,
                effect_id=None,
                source_kind=EffectSourceKind.UNKNOWN,
                visibility=HudVisibility.VISIBLE,
                reason_codes=("STATUS_EFFECT_IDENTITY_UNKNOWN",),
            )
        decoded = StatusEffectReferenceLabel.decode(classified.selected_label)
        if decoded.kind is StatusEffectReferenceKind.PERK_HARD_NEGATIVE:
            return StatusIconRecognition(
                **common,
                status=StatusIconRecognitionStatus.HARD_NEGATIVE,
                effect_id=None,
                source_kind=EffectSourceKind.UNKNOWN,
                visibility=HudVisibility.UNKNOWN,
                reason_codes=("STATUS_ICON_MATCHED_PERK_HARD_NEGATIVE",),
            )
        if decoded.polarity is not candidate.polarity:
            return StatusIconRecognition(
                **common,
                status=StatusIconRecognitionStatus.CONTRADICTION,
                effect_id=None,
                source_kind=EffectSourceKind.UNKNOWN,
                visibility=HudVisibility.UNKNOWN,
                reason_codes=("STATUS_EFFECT_POLARITY_CONTRADICTION",),
            )
        if decoded.kind is StatusEffectReferenceKind.VISIBILITY:
            return StatusIconRecognition(
                **common,
                status=StatusIconRecognitionStatus.VISIBILITY_ONLY,
                effect_id=None,
                source_kind=EffectSourceKind.UNKNOWN,
                visibility=decoded.visibility or HudVisibility.UNKNOWN,
                reason_codes=("STATUS_EFFECT_VISIBILITY_ONLY",),
            )
        definition = self.definitions[decoded.effect_id or ""]
        return StatusIconRecognition(
            **common,
            status=StatusIconRecognitionStatus.IDENTIFIED,
            effect_id=definition.effect_id,
            source_kind=definition.source_kind,
            visibility=HudVisibility.VISIBLE,
            reason_codes=("STATUS_EFFECT_IDENTITY_MATCHED",),
        )


__all__ = [
    "StatusEffectIconRecognizer", "StatusEffectReferenceKind", "StatusEffectReferenceLabel",
    "StatusIconRecognition", "StatusIconRecognitionStatus",
]
