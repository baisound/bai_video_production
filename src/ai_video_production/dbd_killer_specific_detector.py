"""Namespaced reference baseline for Killer-specific HUD teacher samples."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .dbd_killer_capability_registry import KillerCapability, KillerSpecificDetection
from .dbd_vision_slices import GrayImage, ReferenceSliceIndex


class KillerSpecificTeacherRole(str, Enum):
    POSITIVE = "POSITIVE"
    HARD_NEGATIVE = "HARD_NEGATIVE"


@dataclass(frozen=True, slots=True)
class KillerSpecificTeacherLabel:
    role: KillerSpecificTeacherRole
    label_namespace: str
    active: bool | None
    stage: int | None
    progress_milli: int | None

    def __post_init__(self) -> None:
        # Reuse the runtime detection contract as the canonical value validator.
        KillerSpecificDetection(
            self.label_namespace, self.active, self.stage, self.progress_milli, 0
        )
        if not isinstance(self.role, KillerSpecificTeacherRole):
            raise ValueError("invalid Killer-specific teacher role")
        if self.role is KillerSpecificTeacherRole.POSITIVE and self.active is None:
            raise ValueError("positive Killer-specific teacher label requires active state")
        if self.role is KillerSpecificTeacherRole.HARD_NEGATIVE and any(
            value is not None for value in (self.active, self.stage, self.progress_milli)
        ):
            raise ValueError("hard-negative teacher label cannot carry positive state")

    def encode(self) -> str:
        active = "-" if self.active is None else "1" if self.active else "0"
        stage = "-" if self.stage is None else str(self.stage)
        progress = "-" if self.progress_milli is None else str(self.progress_milli)
        return f"KST1|{self.role.value}|{self.label_namespace}|{active}|{stage}|{progress}"

    @classmethod
    def decode(cls, value: str) -> "KillerSpecificTeacherLabel":
        if not isinstance(value, str):
            raise ValueError("Killer-specific teacher label must be text")
        parts = value.split("|")
        if len(parts) != 6 or parts[0] != "KST1":
            raise ValueError("unsupported Killer-specific teacher label")

        def optional_int(raw: str) -> int | None:
            return None if raw == "-" else int(raw)

        if parts[3] not in {"-", "0", "1"}:
            raise ValueError("invalid Killer-specific active state")
        active = None if parts[3] == "-" else parts[3] == "1"
        return cls(
            KillerSpecificTeacherRole(parts[1]), parts[2], active,
            optional_int(parts[4]), optional_int(parts[5]),
        )


class KillerSpecificReferenceDetector:
    """Deterministic starter detector; real-media accuracy remains unclaimed."""

    def __init__(
        self,
        index: ReferenceSliceIndex,
        *,
        acceptance_milli: int = 800,
        ambiguity_margin_milli: int = 70,
    ) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000
            for value in (acceptance_milli, ambiguity_margin_milli)
        ):
            raise ValueError("detector thresholds must be 0..1000")
        self.index = index
        self.acceptance_milli = acceptance_milli
        self.ambiguity_margin_milli = ambiguity_margin_milli

    def detect(
        self,
        image: GrayImage,
        *,
        capability: KillerCapability,
        survivor_slot: int | None,
    ) -> KillerSpecificDetection:
        rows = self.index.match(image, top_k=max(2, len(self.index.references)))
        best_by_label = {}
        for row in rows:
            best_by_label.setdefault(row.label, row)
        unique = sorted(
            best_by_label.values(),
            key=lambda item: (-item.confidence_milli, item.distance_bits, item.label, item.source_ref),
        )
        if not unique or unique[0].confidence_milli < self.acceptance_milli:
            return KillerSpecificDetection(
                capability.training_label_namespace, None, None, None,
                unique[0].confidence_milli if unique else 0,
            )
        if len(unique) > 1 and unique[0].confidence_milli - unique[1].confidence_milli < self.ambiguity_margin_milli:
            return KillerSpecificDetection(
                capability.training_label_namespace, None, None, None, 0,
            )
        label = KillerSpecificTeacherLabel.decode(unique[0].label)
        return KillerSpecificDetection(
            label.label_namespace, label.active, label.stage, label.progress_milli,
            unique[0].confidence_milli,
        )


__all__ = [
    "KillerSpecificReferenceDetector", "KillerSpecificTeacherLabel", "KillerSpecificTeacherRole",
]
