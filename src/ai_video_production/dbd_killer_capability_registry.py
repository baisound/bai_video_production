"""Killer-conditioned routing for DbD killer-specific HUD detectors.

The registry is deliberately detector-implementation agnostic.  It selects an
exact killer namespace first and only then invokes registered detectors.  An
unknown identity, a missing ROI or a detector failure becomes explicit UNKNOWN
state rather than falling through to a different killer's visual vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Mapping, Protocol

from .dbd_killer_knowledge import KillerKnowledgeKind, KillerPowerVisualObservation
from .dbd_killer_status_temporal import KillerSpecificObservation
from .dbd_vision_slices import GrayImage


_ID = re.compile(r"^[a-z][a-z0-9_]{1,127}$")
_NAMESPACE = re.compile(r"^KILLER_SPECIFIC_HUD/killer_[a-z0-9_]+/[a-z][a-z0-9_]*$")


class KillerEffectFamily(str, Enum):
    CIRCULAR_PROGRESS = "CIRCULAR_PROGRESS"
    STAGE_INDICATOR = "STAGE_INDICATOR"
    POWER_STATE = "POWER_STATE"


class KillerRoiFamily(str, Enum):
    SURVIVOR_PORTRAIT_OVERLAY = "SURVIVOR_PORTRAIT_OVERLAY"
    KILLER_POWER_HUD = "KILLER_POWER_HUD"


class KillerDetectorType(str, Enum):
    PROGRESS_RING = "PROGRESS_RING"
    STAGE_CLASSIFIER = "STAGE_CLASSIFIER"
    REFERENCE_SLICE = "REFERENCE_SLICE"


class KillerEffectProjection(str, Enum):
    STATE_EVIDENCE = "STATE_EVIDENCE"
    CGEL_CANDIDATE = "CGEL_CANDIDATE"


def _identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical lowercase identifier")


@dataclass(frozen=True, slots=True)
class KillerCapability:
    killer_id: str
    effect_id: str
    effect_family: KillerEffectFamily
    required_roi_family: KillerRoiFamily
    detector_type: KillerDetectorType
    survivor_scoped: bool
    training_label_namespace: str
    hard_negative_namespaces: tuple[str, ...]
    projection: KillerEffectProjection = KillerEffectProjection.STATE_EVIDENCE
    max_stage: int | None = None
    stage_monotonic: bool = False
    progress_monotonic: bool = False

    def __post_init__(self) -> None:
        _identifier(self.killer_id, "killer_id")
        _identifier(self.effect_id, "effect_id")
        if not self.killer_id.startswith("killer_"):
            raise ValueError("killer_id must start with killer_")
        if not all(
            isinstance(value, enum_type)
            for value, enum_type in (
                (self.effect_family, KillerEffectFamily),
                (self.required_roi_family, KillerRoiFamily),
                (self.detector_type, KillerDetectorType),
                (self.projection, KillerEffectProjection),
            )
        ):
            raise ValueError("invalid killer capability enum")
        if not isinstance(self.survivor_scoped, bool):
            raise ValueError("survivor_scoped must be bool")
        expected_namespace = f"KILLER_SPECIFIC_HUD/{self.killer_id}/{self.effect_id}"
        if self.training_label_namespace != expected_namespace or not _NAMESPACE.fullmatch(expected_namespace):
            raise ValueError("training_label_namespace must match the exact killer/effect namespace")
        if (
            not self.hard_negative_namespaces
            or tuple(sorted(set(self.hard_negative_namespaces))) != self.hard_negative_namespaces
            or any(not _NAMESPACE.fullmatch(item) for item in self.hard_negative_namespaces)
            or self.training_label_namespace in self.hard_negative_namespaces
        ):
            raise ValueError("hard_negative_namespaces must be unique, sorted and cross-namespace")
        if self.max_stage is not None and (
            isinstance(self.max_stage, bool) or not isinstance(self.max_stage, int) or self.max_stage < 1
        ):
            raise ValueError("max_stage must be positive when configured")
        if self.stage_monotonic and self.max_stage is None:
            raise ValueError("stage_monotonic requires max_stage")


@dataclass(frozen=True, slots=True)
class KillerSpecificRoiKey:
    family: KillerRoiFamily
    survivor_slot: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.family, KillerRoiFamily):
            raise ValueError("invalid ROI family")
        if self.survivor_slot is not None and (
            isinstance(self.survivor_slot, bool)
            or not isinstance(self.survivor_slot, int)
            or not 0 <= self.survivor_slot <= 3
        ):
            raise ValueError("survivor_slot must be 0..3 when known")
        if self.family is KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY and self.survivor_slot is None:
            raise ValueError("Survivor overlay ROI requires a survivor_slot")


@dataclass(frozen=True, slots=True)
class KillerSpecificDetection:
    label_namespace: str
    active: bool | None
    stage: int | None
    progress_milli: int | None
    confidence_milli: int

    def __post_init__(self) -> None:
        if not isinstance(self.label_namespace, str) or not _NAMESPACE.fullmatch(self.label_namespace):
            raise ValueError("label_namespace must be a killer-specific teacher namespace")
        if self.active is not None and not isinstance(self.active, bool):
            raise ValueError("active must be bool or None")
        if self.stage is not None and (
            isinstance(self.stage, bool) or not isinstance(self.stage, int) or self.stage < 0
        ):
            raise ValueError("stage must be non-negative when known")
        if self.progress_milli is not None and (
            isinstance(self.progress_milli, bool)
            or not isinstance(self.progress_milli, int)
            or not 0 <= self.progress_milli <= 1000
        ):
            raise ValueError("progress_milli must be 0..1000 when known")
        if (
            isinstance(self.confidence_milli, bool)
            or not isinstance(self.confidence_milli, int)
            or not 0 <= self.confidence_milli <= 1000
        ):
            raise ValueError("confidence_milli must be 0..1000")
        if self.active is False and (self.stage is not None or self.progress_milli is not None):
            raise ValueError("inactive detection cannot carry stage/progress")


class KillerSpecificDetector(Protocol):
    def detect(
        self,
        image: GrayImage,
        *,
        capability: KillerCapability,
        survivor_slot: int | None,
    ) -> KillerSpecificDetection: ...


@dataclass(frozen=True, slots=True)
class KillerRouteRecord:
    capability: KillerCapability | None
    observation: KillerSpecificObservation
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KillerConditionedRouteResult:
    selected_killer_id: str | None
    records: tuple[KillerRouteRecord, ...]

    @property
    def observations(self) -> tuple[KillerSpecificObservation, ...]:
        return tuple(item.observation for item in self.records)


class KillerCapabilityRegistry:
    def __init__(
        self,
        capabilities: tuple[KillerCapability, ...],
        detectors: Mapping[tuple[str, str], KillerSpecificDetector],
        *,
        identity_confidence_milli: int = 800,
        detection_confidence_milli: int = 700,
    ) -> None:
        keys = tuple((item.killer_id, item.effect_id) for item in capabilities)
        if len(keys) != len(set(keys)):
            raise ValueError("killer capabilities must be unique")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000
            for value in (identity_confidence_milli, detection_confidence_milli)
        ):
            raise ValueError("confidence thresholds must be 0..1000")
        known_keys = set(keys)
        if any(key not in known_keys for key in detectors):
            raise ValueError("detector registered without a matching capability")
        self.capabilities = tuple(sorted(capabilities, key=lambda item: (item.killer_id, item.effect_id)))
        self.detectors = dict(detectors)
        self.identity_confidence_milli = identity_confidence_milli
        self.detection_confidence_milli = detection_confidence_milli

    def route(
        self,
        identity: KillerPowerVisualObservation,
        *,
        match_id: str,
        frame_index: int,
        identity_evidence_ref: str,
        images: Mapping[KillerSpecificRoiKey, GrayImage],
        evidence_refs: Mapping[KillerSpecificRoiKey, str],
    ) -> KillerConditionedRouteResult:
        killer_id = self._selected_killer(identity)
        if killer_id is None:
            unknown = KillerSpecificObservation(
                match_id, None, None, None, None, None, None,
                identity.confidence_milli, frame_index, identity_evidence_ref,
            )
            return KillerConditionedRouteResult(
                None, (KillerRouteRecord(None, unknown, ("KILLER_IDENTITY_UNKNOWN",)),)
            )

        selected = tuple(item for item in self.capabilities if item.killer_id == killer_id)
        if not selected:
            unknown = KillerSpecificObservation(
                match_id, None, killer_id, None, None, None, None,
                identity.confidence_milli, frame_index, identity_evidence_ref,
            )
            return KillerConditionedRouteResult(
                killer_id, (KillerRouteRecord(None, unknown, ("KILLER_CAPABILITY_UNAVAILABLE",)),)
            )

        records: list[KillerRouteRecord] = []
        for capability in selected:
            slots: tuple[int | None, ...] = (0, 1, 2, 3) if capability.survivor_scoped else (None,)
            for survivor_slot in slots:
                key = KillerSpecificRoiKey(capability.required_roi_family, survivor_slot)
                image = images.get(key)
                evidence_ref = evidence_refs.get(key, identity_evidence_ref)
                detector = self.detectors.get((capability.killer_id, capability.effect_id))
                if image is None:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "REQUIRED_ROI_MISSING"))
                    continue
                if detector is None:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "DETECTOR_UNAVAILABLE"))
                    continue
                if key not in evidence_refs:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "ROI_EVIDENCE_REF_MISSING"))
                    continue
                try:
                    detection = detector.detect(image, capability=capability, survivor_slot=survivor_slot)
                except Exception:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "DETECTOR_FAILED"))
                    continue
                if detection.label_namespace != capability.training_label_namespace:
                    reason = (
                        "HARD_NEGATIVE_NAMESPACE"
                        if detection.label_namespace in capability.hard_negative_namespaces
                        else "DETECTION_NAMESPACE_MISMATCH"
                    )
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, reason))
                    continue
                if detection.confidence_milli < self.detection_confidence_milli:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "DETECTION_CONFIDENCE_LOW", detection.confidence_milli))
                    continue
                if capability.max_stage is not None and detection.stage is not None and detection.stage > capability.max_stage:
                    records.append(self._unknown(capability, match_id, survivor_slot, frame_index, evidence_ref, "DETECTION_SEMANTICS_INVALID", detection.confidence_milli))
                    continue
                observation = KillerSpecificObservation(
                    match_id, survivor_slot, capability.killer_id, capability.effect_id,
                    detection.active, detection.stage, detection.progress_milli,
                    detection.confidence_milli, frame_index, evidence_ref,
                )
                records.append(KillerRouteRecord(capability, observation, ("KILLER_CAPABILITY_ROUTED",)))
        return KillerConditionedRouteResult(killer_id, tuple(records))

    def _selected_killer(self, identity: KillerPowerVisualObservation) -> str | None:
        if (
            identity.kind is not KillerKnowledgeKind.KILLER
            or identity.entity_id is None
            or not identity.entity_id.startswith("killer_")
            or not _ID.fullmatch(identity.entity_id)
            or identity.confidence_milli < self.identity_confidence_milli
        ):
            return None
        return identity.entity_id

    @staticmethod
    def _unknown(
        capability: KillerCapability,
        match_id: str,
        survivor_slot: int | None,
        frame_index: int,
        evidence_ref: str,
        reason: str,
        confidence_milli: int = 0,
    ) -> KillerRouteRecord:
        observation = KillerSpecificObservation(
            match_id, survivor_slot, capability.killer_id, capability.effect_id,
            None, None, None, confidence_milli, frame_index, evidence_ref,
        )
        return KillerRouteRecord(capability, observation, (reason,))


def initial_killer_capabilities() -> tuple[KillerCapability, ...]:
    """Owner-observed starter fixtures; not a complete live-game killer catalog."""
    namespaces = {
        "ghost": "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress",
        "onryo": "KILLER_SPECIFIC_HUD/killer_onryo/condemn",
        "doctor": "KILLER_SPECIFIC_HUD/killer_doctor/madness",
    }
    return (
        KillerCapability(
            "killer_ghost_face", "mark_progress", KillerEffectFamily.CIRCULAR_PROGRESS,
            KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, KillerDetectorType.PROGRESS_RING,
            True, namespaces["ghost"], tuple(sorted((namespaces["doctor"], namespaces["onryo"]))),
            progress_monotonic=False,
        ),
        KillerCapability(
            "killer_onryo", "condemn", KillerEffectFamily.CIRCULAR_PROGRESS,
            KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, KillerDetectorType.PROGRESS_RING,
            True, namespaces["onryo"], tuple(sorted((namespaces["doctor"], namespaces["ghost"]))),
            max_stage=7, stage_monotonic=True, progress_monotonic=True,
        ),
        KillerCapability(
            "killer_doctor", "madness", KillerEffectFamily.STAGE_INDICATOR,
            KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, KillerDetectorType.STAGE_CLASSIFIER,
            True, namespaces["doctor"], tuple(sorted((namespaces["ghost"], namespaces["onryo"]))),
            max_stage=3, stage_monotonic=False, progress_monotonic=False,
        ),
    )


__all__ = [
    "KillerCapability", "KillerCapabilityRegistry", "KillerConditionedRouteResult",
    "KillerDetectorType", "KillerEffectFamily", "KillerEffectProjection", "KillerRouteRecord",
    "KillerRoiFamily", "KillerSpecificDetection", "KillerSpecificDetector", "KillerSpecificRoiKey",
    "initial_killer_capabilities",
]
