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
    PERK = "PERK"
    ITEM = "ITEM"
    ADDON = "ADDON"
    UPPER_RIGHT_NOTIFICATION = "UPPER_RIGHT_NOTIFICATION"
    KILLER_POWER = "KILLER_POWER"
    HEARTBEAT = "HEARTBEAT"


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

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": "1.0.0",
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
