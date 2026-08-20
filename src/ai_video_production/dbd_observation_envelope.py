"""TASK-050 R5 reusable DbD observation/provenance/export contracts.

Observation is evidence, not a Canonical Game Event.  This module keeps the
recognition context needed to reproduce and audit downstream decisions.

The same envelope can carry Perk/Item/Add-on visibility, heartbeat intensity,
notification/OCR state, killer-power identity, or future HUD observations
without granting CGEL or Production Timeline authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import csv
import io
import json
import os
from pathlib import Path
from typing import Iterable, Mapping

from .dbd_hud_visibility import HudVisibility
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


class DbDObservationType(str, Enum):
    SURVIVOR_STATUS = "SURVIVOR_STATUS"
    HOOK_COUNT = "HOOK_COUNT"
    CHASE_STATE = "CHASE_STATE"
    PERK = "PERK"
    ITEM = "ITEM"
    ADDON = "ADDON"
    UPPER_RIGHT_NOTIFICATION = "UPPER_RIGHT_NOTIFICATION"
    KILLER_POWER = "KILLER_POWER"
    HEARTBEAT = "HEARTBEAT"


class SurvivorSignalKind(str, Enum):
    HOOK_COUNT = "HOOK_COUNT"
    CHASE_STATE = "CHASE_STATE"
    SURVIVOR_STATE = "SURVIVOR_STATE"


_SURVIVOR_OBSERVATION_TYPES = {
    DbDObservationType.HOOK_COUNT: SurvivorSignalKind.HOOK_COUNT,
    DbDObservationType.CHASE_STATE: SurvivorSignalKind.CHASE_STATE,
    DbDObservationType.SURVIVOR_STATUS: SurvivorSignalKind.SURVIVOR_STATE,
}
_SURVIVOR_SIGNAL_VALUES = {
    SurvivorSignalKind.HOOK_COUNT: {"0", "1", "2", "UNKNOWN"},
    SurvivorSignalKind.CHASE_STATE: {
        "NOT_CHASE", "CHASE_CANDIDATE", "CHASE_ACTIVE", "CHASE_END_CANDIDATE", "UNKNOWN",
    },
    SurvivorSignalKind.SURVIVOR_STATE: {
        "HEALTHY", "INJURED", "DOWNED", "HOOKED", "DEAD", "ESCAPED", "UNKNOWN",
    },
}


def normalize_survivor_signal_value(signal_kind: SurvivorSignalKind, value: str) -> str:
    if not isinstance(signal_kind, SurvivorSignalKind):
        raise ValueError("signal_kind must be a SurvivorSignalKind")
    normalized = value.strip().upper()
    if normalized not in _SURVIVOR_SIGNAL_VALUES[signal_kind]:
        allowed = "/".join(sorted(_SURVIVOR_SIGNAL_VALUES[signal_kind]))
        raise ValueError(f"{signal_kind.value} value must be one of {allowed}")
    return normalized


@dataclass(frozen=True, slots=True)
class ObservationProvenance:
    workspace_id: str
    runtime_profile_id: str | None
    hud_profile_id: str
    hud_profile_version: int
    roi_id: str
    detector_version: str
    anchor_offset_x_px: int = 0
    anchor_offset_y_px: int = 0
    knowledge_revision_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.workspace_id.strip():
            raise ValueError("workspace_id is required")
        if not self.hud_profile_id.strip():
            raise ValueError("hud_profile_id is required")
        if self.hud_profile_version < 1:
            raise ValueError("hud_profile_version must be positive")
        if not self.roi_id.strip():
            raise ValueError("roi_id is required")
        if not self.detector_version.strip():
            raise ValueError("detector_version is required")
        if self.knowledge_revision_refs != tuple(sorted(set(self.knowledge_revision_refs))):
            raise ValueError("knowledge_revision_refs must be unique and sorted")

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "runtime_profile_id": self.runtime_profile_id,
            "hud_profile_id": self.hud_profile_id,
            "hud_profile_version": self.hud_profile_version,
            "roi_id": self.roi_id,
            "detector_version": self.detector_version,
            "anchor_offset_x_px": self.anchor_offset_x_px,
            "anchor_offset_y_px": self.anchor_offset_y_px,
            "knowledge_revision_refs": list(self.knowledge_revision_refs),
        }


@dataclass(frozen=True, slots=True)
class DbDObservationEnvelope:
    observation_id: str
    observation_type: DbDObservationType
    frame_start: int
    frame_end_exclusive: int
    confidence_milli: int
    provenance: ObservationProvenance
    visibility: HudVisibility = HudVisibility.UNKNOWN
    entity_id: str | None = None
    state: str | None = None
    intensity_milli: int | None = None
    trend: str | None = None
    candidates: tuple[str, ...] = ()
    evidence_ref: str | None = None
    match_id: str | None = None
    survivor_slot: int | None = None
    signal_kind: SurvivorSignalKind | None = None
    source_frame: int | None = None
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id is required")
        if self.frame_start < 0 or self.frame_end_exclusive <= self.frame_start:
            raise ValueError("invalid frame range")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.intensity_milli is not None and not 0 <= self.intensity_milli <= 1000:
            raise ValueError("intensity_milli must be 0..1000")
        if self.candidates != tuple(sorted(set(self.candidates))):
            raise ValueError("candidates must be unique and sorted")
        expected_signal = _SURVIVOR_OBSERVATION_TYPES.get(self.observation_type)
        if expected_signal is not None:
            if self.signal_kind is not expected_signal:
                raise ValueError("survivor observation signal_kind does not match observation_type")
            if self.match_id is None or not self.match_id.strip() or len(self.match_id) > 256:
                raise ValueError("survivor observation requires bounded match_id")
            if self.survivor_slot is not None and not 0 <= self.survivor_slot <= 3:
                raise ValueError("survivor_slot must be 0..3 when known")
            if self.survivor_slot is None and self.state != "UNKNOWN":
                raise ValueError("unknown survivor slot may only emit UNKNOWN")
            if self.source_frame is None or not self.frame_start <= self.source_frame < self.frame_end_exclusive:
                raise ValueError("survivor observation source_frame must be inside its frame range")
        elif any(value is not None for value in (self.match_id, self.survivor_slot, self.signal_kind, self.source_frame)):
            raise ValueError("survivor subject fields are valid only for survivor observations")

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": "1.1.0",
            "observation_id": self.observation_id,
            "observation_type": self.observation_type.value,
            "frame_start": self.frame_start,
            "frame_end_exclusive": self.frame_end_exclusive,
            "confidence_milli": self.confidence_milli,
            "visibility": self.visibility.value,
            "entity_id": self.entity_id,
            "state": self.state,
            "intensity_milli": self.intensity_milli,
            "trend": self.trend,
            "candidates": list(self.candidates),
            "evidence_ref": self.evidence_ref,
            "match_id": self.match_id,
            "survivor_slot": self.survivor_slot,
            "signal_kind": None if self.signal_kind is None else self.signal_kind.value,
            "source_frame": self.source_frame,
            "provenance": self.provenance.to_dict(),
            "created_at": self.created_at,
        }
        return {**body, "observation_sha256": sha256_bytes(canonical_json_bytes(body))}


def observation_csv_header() -> tuple[str, ...]:
    return (
        "observation_id",
        "observation_type",
        "frame_start",
        "frame_end_exclusive",
        "entity_id",
        "visibility",
        "state",
        "intensity_milli",
        "trend",
        "confidence_milli",
        "workspace_id",
        "runtime_profile_id",
        "hud_profile_id",
        "hud_profile_version",
        "roi_id",
        "anchor_offset_x_px",
        "anchor_offset_y_px",
        "detector_version",
        "knowledge_revision_refs",
        "evidence_ref",
        "match_id",
        "survivor_slot",
        "signal_kind",
        "source_frame",
    )


def observation_csv_row(item: DbDObservationEnvelope) -> tuple[object, ...]:
    p = item.provenance
    return (
        item.observation_id,
        item.observation_type.value,
        item.frame_start,
        item.frame_end_exclusive,
        item.entity_id or "",
        item.visibility.value,
        item.state or "",
        "" if item.intensity_milli is None else item.intensity_milli,
        item.trend or "",
        item.confidence_milli,
        p.workspace_id,
        p.runtime_profile_id or "",
        p.hud_profile_id,
        p.hud_profile_version,
        p.roi_id,
        p.anchor_offset_x_px,
        p.anchor_offset_y_px,
        p.detector_version,
        "|".join(p.knowledge_revision_refs),
        item.evidence_ref or "",
        item.match_id or "",
        "" if item.survivor_slot is None else item.survivor_slot,
        "" if item.signal_kind is None else item.signal_kind.value,
        "" if item.source_frame is None else item.source_frame,
    )


def serialize_observations_jsonl(items: Iterable[DbDObservationEnvelope]) -> bytes:
    values = sorted(items, key=lambda x: (x.frame_start, x.observation_type.value, x.observation_id))
    return b"".join(canonical_json_bytes(item.to_dict()) + b"\n" for item in values)


def serialize_observations_csv(items: Iterable[DbDObservationEnvelope]) -> str:
    values = sorted(items, key=lambda x: (x.frame_start, x.observation_type.value, x.observation_id))
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(observation_csv_header())
    for item in values:
        writer.writerow(observation_csv_row(item))
    return buf.getvalue()


def heartbeat_to_observation(
    *,
    observation_id: str,
    frame_index: int,
    active: bool | None,
    intensity_milli: int | None,
    trend: str,
    confidence_milli: int,
    provenance: ObservationProvenance,
    evidence_ref: str | None = None,
) -> DbDObservationEnvelope:
    state = "UNKNOWN" if active is None else ("ACTIVE" if active else "OFF")
    return DbDObservationEnvelope(
        observation_id=observation_id,
        observation_type=DbDObservationType.HEARTBEAT,
        frame_start=frame_index,
        frame_end_exclusive=frame_index + 1,
        confidence_milli=confidence_milli,
        provenance=provenance,
        visibility=HudVisibility.UNKNOWN,
        state=state,
        intensity_milli=intensity_milli,
        trend=trend,
        evidence_ref=evidence_ref,
    )


def survivor_signal_to_observation(
    *,
    observation_id: str,
    match_id: str,
    survivor_slot: int | None,
    signal_kind: SurvivorSignalKind,
    value: str,
    confidence_milli: int,
    source_frame: int,
    provenance: ObservationProvenance,
    evidence_ref: str | None = None,
) -> DbDObservationEnvelope:
    normalized = normalize_survivor_signal_value(signal_kind, value)
    observation_type = {
        SurvivorSignalKind.HOOK_COUNT: DbDObservationType.HOOK_COUNT,
        SurvivorSignalKind.CHASE_STATE: DbDObservationType.CHASE_STATE,
        SurvivorSignalKind.SURVIVOR_STATE: DbDObservationType.SURVIVOR_STATUS,
    }[signal_kind]
    return DbDObservationEnvelope(
        observation_id=observation_id,
        observation_type=observation_type,
        frame_start=source_frame,
        frame_end_exclusive=source_frame + 1,
        confidence_milli=confidence_milli,
        provenance=provenance,
        state=normalized,
        evidence_ref=evidence_ref,
        match_id=match_id,
        survivor_slot=survivor_slot,
        signal_kind=signal_kind,
        source_frame=source_frame,
    )
