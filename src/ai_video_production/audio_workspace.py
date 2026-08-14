"""TASK-041 non-destructive Audio Workspace domain foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .timeline_audio import TimelinePlacementBinding


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,179}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class AudioSlotKind(str, Enum):
    SOURCE_AUDIO = "SOURCE_AUDIO"
    VFX_EMBEDDED_AUDIO = "VFX_EMBEDDED_AUDIO"
    SE = "SE"
    BGM = "BGM"
    AMBIENCE = "AMBIENCE"
    NARRATION = "NARRATION"
    MIX_STEM = "MIX_STEM"
    FINAL_MIX = "FINAL_MIX"


class AudioDecisionKind(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ALTERNATE_USE = "ALTERNATE_USE"
    STRIP_AUDIO = "STRIP_AUDIO"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AudioDerivationType(str, Enum):
    AUDIO_STRIPPED_VIDEO = "AUDIO_STRIPPED_VIDEO"
    AUDIO_ONLY = "AUDIO_ONLY"
    NORMALIZED_AUDIO = "NORMALIZED_AUDIO"
    MIX_STEM = "MIX_STEM"


class PlacementDecision(str, Enum):
    REVIEW = "REVIEW"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ALTERNATE_USE = "ALTERNATE_USE"


@dataclass(frozen=True, slots=True)
class AudioCandidateDecision:
    decision_id: str
    candidate_id: str
    audio_slot_kind: AudioSlotKind
    decision: AudioDecisionKind
    actor_id: str
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (("decision_id", self.decision_id), ("candidate_id", self.candidate_id), ("actor_id", self.actor_id)):
            _id(value, name)
        for value in self.reason_codes:
            _id(value, "reason_code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "audio_slot_kind": self.audio_slot_kind.value,
            "decision": self.decision.value,
            "actor_id": self.actor_id,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class AudioDerivedAsset:
    derived_asset_id: str
    source_asset_id: str
    source_sha256: str
    derived_sha256: str
    derivation_type: AudioDerivationType

    def __post_init__(self) -> None:
        _id(self.derived_asset_id, "derived_asset_id")
        _id(self.source_asset_id, "source_asset_id")
        _sha(self.source_sha256, "source_sha256")
        _sha(self.derived_sha256, "derived_sha256")
        if self.source_sha256 == self.derived_sha256:
            raise ValueError("derived Asset must have distinct bytes/hash")

    def to_dict(self) -> dict[str, Any]:
        return {
            "derived_asset_id": self.derived_asset_id,
            "source_asset_id": self.source_asset_id,
            "source_sha256": self.source_sha256,
            "derived_sha256": self.derived_sha256,
            "derivation_type": self.derivation_type.value,
            "destructive_source_write": False,
        }


@dataclass(frozen=True, slots=True)
class PlacementReview:
    review_id: str
    candidate_id: str
    timeline_start_frame: int
    duration_frames: int
    track_role: str
    decision: PlacementDecision = PlacementDecision.REVIEW
    gain_db: float | None = None
    timeline_binding: TimelinePlacementBinding | None = None

    def __post_init__(self) -> None:
        _id(self.review_id, "review_id")
        _id(self.candidate_id, "candidate_id")
        if self.timeline_start_frame < 0 or self.duration_frames < 1:
            raise ValueError("placement frame range is invalid")
        if self.track_role not in {"SOURCE", "SE", "BGM", "AMBIENCE", "NARRATION", "MIX_STEM"}:
            raise ValueError("track_role is invalid")
        if self.gain_db is not None and not -120.0 <= self.gain_db <= 24.0:
            raise ValueError("gain_db must be -120..24")

    def to_dict(self) -> dict[str, Any]:
        value = {
            "review_id": self.review_id,
            "candidate_id": self.candidate_id,
            "timeline_start_frame": self.timeline_start_frame,
            "duration_frames": self.duration_frames,
            "track_role": self.track_role,
            "gain_db": self.gain_db,
            "decision": self.decision.value,
        }
        if self.timeline_binding is not None:
            value["timeline_binding"] = self.timeline_binding.to_dict()
        return value


class AudioWorkspaceRegistry:
    def __init__(self) -> None:
        self.decisions: dict[str, AudioCandidateDecision] = {}
        self.derived_assets: dict[str, AudioDerivedAsset] = {}
        self.placements: dict[str, PlacementReview] = {}

    def add_decision(self, decision: AudioCandidateDecision) -> None:
        if decision.decision_id in self.decisions:
            raise ProductError("ERR_AUDIO_DECISION_CONFLICT", "decision_id already exists", ProductErrorCategory.STATE)
        self.decisions[decision.decision_id] = decision

    def add_derived_asset(self, derived: AudioDerivedAsset) -> None:
        if derived.derived_asset_id in self.derived_assets:
            raise ProductError("ERR_AUDIO_DERIVED_ASSET_CONFLICT", "derived_asset_id already exists", ProductErrorCategory.STATE)
        self.derived_assets[derived.derived_asset_id] = derived

    def add_placement(self, review: PlacementReview) -> None:
        if review.review_id in self.placements:
            raise ProductError("ERR_AUDIO_PLACEMENT_CONFLICT", "review_id already exists", ProductErrorCategory.STATE)
        self.placements[review.review_id] = review

    def replace_placement_decision(self, review_id: str, decision: PlacementDecision) -> PlacementReview:
        current = self.placements.get(review_id)
        if current is None:
            raise ProductError("ERR_AUDIO_PLACEMENT_NOT_FOUND", "review_id does not exist", ProductErrorCategory.STATE)
        updated = PlacementReview(
            current.review_id,
            current.candidate_id,
            current.timeline_start_frame,
            current.duration_frames,
            current.track_role,
            decision,
            current.gain_db,
            current.timeline_binding,
        )
        self.placements[review_id] = updated
        return updated

    def accepted_placements(self) -> tuple[PlacementReview, ...]:
        return tuple(item for item in self.placements.values() if item.decision is PlacementDecision.ACCEPT)
