"""TASK-049 exact source-range and game Evidence contracts.

This module is deliberately side-effect free.  It performs no media I/O,
detection, provider execution, filesystem mutation, or production-timeline
mutation.  It defines immutable evidence records that downstream resolvers may
admit into the Canonical Game Event Timeline (CGEL).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .ids import IdKind, generate_id, validate_id
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso
from .timebase import FrameRate, FrameRounding


class GameEvidenceType(str, Enum):
    VISION = "VISION"
    HUD = "HUD"
    ASR = "ASR"
    AUDIO = "AUDIO"
    STATE_TRANSITION = "STATE_TRANSITION"
    KNOWLEDGE_MATCH = "KNOWLEDGE_MATCH"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass(frozen=True, slots=True)
class SourceFrameRange:
    """Exact end-exclusive source-frame range.

    Frame numbers, rather than floating seconds, are canonical.  Display or
    interoperability timestamps may be derived from a separately admitted
    exact :class:`FrameRate`.
    """

    start_frame: int
    end_frame_exclusive: int

    def __post_init__(self) -> None:
        if isinstance(self.start_frame, bool) or not isinstance(self.start_frame, int):
            raise ValueError("start_frame must be an integer")
        if isinstance(self.end_frame_exclusive, bool) or not isinstance(self.end_frame_exclusive, int):
            raise ValueError("end_frame_exclusive must be an integer")
        if self.start_frame < 0:
            raise ValueError("start_frame must be >= 0")
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("frame range must be positive and end-exclusive")

    @property
    def duration_frames(self) -> int:
        return self.end_frame_exclusive - self.start_frame

    def to_microsecond_range(self, rate: FrameRate) -> dict[str, int]:
        if not isinstance(rate, FrameRate):
            raise ValueError("rate must be an exact FrameRate")
        return {
            "start": rate.frame_to_us(self.start_frame, rounding=FrameRounding.FLOOR),
            "end_exclusive": rate.frame_to_us(
                self.end_frame_exclusive, rounding=FrameRounding.CEIL
            ),
        }

    def to_dict(self) -> dict[str, int]:
        return {
            "start_frame": self.start_frame,
            "end_frame_exclusive": self.end_frame_exclusive,
        }


def _validate_text(value: str, *, field_name: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be a non-empty string up to {maximum} characters")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value


@dataclass(frozen=True, slots=True)
class GameEvidence:
    production_job_id: str
    match_id: str
    source_asset_id: str
    producer: str
    producer_version: str
    evidence_type: GameEvidenceType
    source_range: SourceFrameRange
    confidence_milli: int
    artifact_ref: str | None = None
    bvp_evidence_id: str | None = None
    game_evidence_id: str = field(default_factory=lambda: generate_id(IdKind.GAME_EVIDENCE))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.source_asset_id, IdKind.ASSET)
        validate_id(self.game_evidence_id, IdKind.GAME_EVIDENCE)
        if self.bvp_evidence_id is not None:
            validate_id(self.bvp_evidence_id, IdKind.EVIDENCE)
        _validate_text(self.producer, field_name="producer")
        SemVer.parse(self.producer_version)
        if not isinstance(self.evidence_type, GameEvidenceType):
            raise ValueError("evidence_type must be a GameEvidenceType")
        if not isinstance(self.source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int):
            raise ValueError("confidence_milli must be an integer")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.artifact_ref is not None:
            _validate_text(self.artifact_ref, field_name="artifact_ref", maximum=512)
        _validate_text(self.created_at, field_name="created_at", maximum=64)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": "1.0.0",
            "game_evidence_id": self.game_evidence_id,
            "production_job_id": self.production_job_id,
            "match_id": self.match_id,
            "source_asset_id": self.source_asset_id,
            "producer": self.producer,
            "producer_version": self.producer_version,
            "evidence_type": self.evidence_type.value,
            "source_range": self.source_range.to_dict(),
            "confidence_milli": self.confidence_milli,
            "artifact_ref": self.artifact_ref,
            "bvp_evidence_id": self.bvp_evidence_id,
            "created_at": self.created_at,
        }
        return {
            **body,
            "game_evidence_sha256": sha256_bytes(canonical_json_bytes(body)),
        }


def parse_source_frame_range(payload: Any) -> SourceFrameRange:
    if not isinstance(payload, dict):
        raise ValueError("source range payload must be an object")
    if set(payload) != {"start_frame", "end_frame_exclusive"}:
        raise ValueError("source range payload has unexpected fields")
    return SourceFrameRange(payload["start_frame"], payload["end_frame_exclusive"])


def parse_game_evidence(payload: Any) -> GameEvidence:
    if not isinstance(payload, dict):
        raise ValueError("game evidence payload must be an object")
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported game evidence schema_version")
    try:
        item = GameEvidence(
            production_job_id=payload["production_job_id"],
            match_id=payload["match_id"],
            source_asset_id=payload["source_asset_id"],
            producer=payload["producer"],
            producer_version=payload["producer_version"],
            evidence_type=GameEvidenceType(payload["evidence_type"]),
            source_range=parse_source_frame_range(payload["source_range"]),
            confidence_milli=payload["confidence_milli"],
            artifact_ref=payload["artifact_ref"],
            bvp_evidence_id=payload["bvp_evidence_id"],
            game_evidence_id=payload["game_evidence_id"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid game evidence payload") from exc
    if item.to_dict() != payload:
        raise ValueError("game evidence payload/hash is not canonical")
    return item


__all__ = [
    "GameEvidence",
    "GameEvidenceType",
    "SourceFrameRange",
    "parse_game_evidence",
    "parse_source_frame_range",
]
