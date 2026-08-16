"""Deterministic, provider-neutral TASK-018 Smart Reframe contract.

The module compiles already-authored in-memory crop proposals.  It has no
media reader, detector, renderer, filesystem, subprocess, network, provider,
or timeline mutation surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .timebase import FrameRate


_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ROW_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_DIMENSION = 32768
_MAX_FRAMES = (1 << 63) - 1
_MAX_KEEP_RANGES = 100_000
_MAX_SEGMENTS = 100_000
_MAX_EVIDENCE_PER_SEGMENT = 32


def _strict_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class ReframeEvidenceSource(str, Enum):
    TASK005_SCENE_BOUNDARY = "TASK005_SCENE_BOUNDARY"
    TASK008_MULTIMODAL_SCORING = "TASK008_MULTIMODAL_SCORING"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class EvidenceValidity(str, Enum):
    CURRENT_VALID = "CURRENT_VALID"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    REVOKED = "REVOKED"


class ReframePlanState(str, Enum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"


@dataclass(frozen=True, slots=True)
class SourceVideoBinding:
    asset_id: str
    asset_sha256: str
    width: int
    height: int
    frame_rate: FrameRate
    total_frames: int

    def __post_init__(self) -> None:
        validate_id(self.asset_id, IdKind.ASSET)
        validate_sha256(self.asset_sha256, field_name="asset_sha256")
        _strict_int(self.width, "width", 1, _MAX_DIMENSION)
        _strict_int(self.height, "height", 1, _MAX_DIMENSION)
        if not isinstance(self.frame_rate, FrameRate):
            raise ValueError("frame_rate must be the canonical FrameRate type")
        _strict_int(self.frame_rate.numerator, "frame_rate numerator", 1, 1_000_000)
        _strict_int(self.frame_rate.denominator, "frame_rate denominator", 1, 100_000)
        _strict_int(self.total_frames, "total_frames", 1, _MAX_FRAMES)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "geometry": {"width": self.width, "height": self.height},
            "pixel_aspect_ratio": {"numerator": 1, "denominator": 1},
            "frame_rate": {
                "numerator": self.frame_rate.numerator,
                "denominator": self.frame_rate.denominator,
            },
            "total_frames": self.total_frames,
        }


@dataclass(frozen=True, slots=True)
class ReframeTargetProfile:
    profile_id: str
    profile_version: str
    width: int
    height: int
    frame_rate: FrameRate

    def __post_init__(self) -> None:
        _token(self.profile_id, "profile_id")
        if not isinstance(self.profile_version, str) or not _SEMVER_RE.fullmatch(self.profile_version):
            raise ValueError("profile_version must be semantic version x.y.z")
        _strict_int(self.width, "width", 1, _MAX_DIMENSION)
        _strict_int(self.height, "height", 1, _MAX_DIMENSION)
        if self.width >= self.height:
            raise ValueError("R0 target must be portrait")
        if not isinstance(self.frame_rate, FrameRate):
            raise ValueError("frame_rate must be the canonical FrameRate type")
        _strict_int(self.frame_rate.numerator, "frame_rate numerator", 1, 1_000_000)
        _strict_int(self.frame_rate.denominator, "frame_rate denominator", 1, 100_000)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "width": self.width,
            "height": self.height,
            "frame_rate": {
                "numerator": self.frame_rate.numerator,
                "denominator": self.frame_rate.denominator,
            },
            "output_family": "VERTICAL",
            "adapter_family": "PROVIDER_NEUTRAL",
            "remotion_compatibility": "CONTRACT_ONLY_UNPROVEN",
        }
        return {**body, "profile_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class FrameRange:
    start_frame: int
    end_frame_exclusive: int

    def __post_init__(self) -> None:
        _strict_int(self.start_frame, "start_frame", 0, _MAX_FRAMES - 1)
        _strict_int(self.end_frame_exclusive, "end_frame_exclusive", 1, _MAX_FRAMES)
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("frame range must be positive and end-exclusive")

    def to_dict(self) -> dict[str, int]:
        return {"start": self.start_frame, "end_exclusive": self.end_frame_exclusive}


@dataclass(frozen=True, slots=True)
class CropWindow:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        _strict_int(self.x, "x", 0, _MAX_DIMENSION - 1)
        _strict_int(self.y, "y", 0, _MAX_DIMENSION - 1)
        _strict_int(self.width, "width", 1, _MAX_DIMENSION)
        _strict_int(self.height, "height", 1, _MAX_DIMENSION)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class ReframeEvidenceRef:
    source: ReframeEvidenceSource
    contract_version: str
    manifest_sha256: str
    row_id: str
    row_sha256: str
    validity: EvidenceValidity

    def __post_init__(self) -> None:
        if not isinstance(self.source, ReframeEvidenceSource):
            raise ValueError("source must be a ReframeEvidenceSource")
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")
        if not isinstance(self.contract_version, str) or not _SEMVER_RE.fullmatch(self.contract_version):
            raise ValueError("contract_version must be semantic version x.y.z")
        validate_sha256(self.manifest_sha256, field_name="manifest_sha256")
        if not isinstance(self.row_id, str) or not _ROW_ID_RE.fullmatch(self.row_id):
            raise ValueError("row_id is invalid")
        validate_sha256(self.row_sha256, field_name="row_sha256")

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.source.value, self.manifest_sha256, self.row_id, self.row_sha256)

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source.value,
            "contract_version": self.contract_version,
            "manifest_sha256": self.manifest_sha256,
            "row_id": self.row_id,
            "row_sha256": self.row_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class ReframeSegmentProposal:
    source_range: FrameRange
    crop: CropWindow
    evidence: tuple[ReframeEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_range, FrameRange) or not isinstance(self.crop, CropWindow):
            raise ValueError("source_range and crop must use canonical contract types")
        if not 1 <= len(self.evidence) <= _MAX_EVIDENCE_PER_SEGMENT:
            raise ValueError("evidence must contain 1-32 rows")
        if any(not isinstance(item, ReframeEvidenceRef) for item in self.evidence):
            raise ValueError("evidence must contain ReframeEvidenceRef rows")
        keys = tuple(item.key for item in self.evidence)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("evidence must be unique and canonically sorted")


@dataclass(frozen=True, slots=True)
class ReframeSegment:
    segment_id: str
    source_range: FrameRange
    output_range: FrameRange
    crop: CropWindow
    evidence: tuple[ReframeEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"reframe-[0-9]{6}", self.segment_id):
            raise ValueError("segment_id is invalid")
        ReframeSegmentProposal(self.source_range, self.crop, self.evidence)
        if not isinstance(self.output_range, FrameRange):
            raise ValueError("output_range must be a FrameRange")

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "source_range_frames": self.source_range.to_dict(),
            "output_range_frames": self.output_range.to_dict(),
            "crop": self.crop.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "decision_state": "PROPOSED_FOR_HUMAN_REVIEW",
        }


@dataclass(frozen=True, slots=True)
class SmartReframePlan:
    source: SourceVideoBinding
    source_edit_plan_sha256: str
    source_keep_ranges: tuple[FrameRange, ...]
    target: ReframeTargetProfile
    segments: tuple[ReframeSegment, ...]
    state: ReframePlanState

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceVideoBinding) or not isinstance(self.target, ReframeTargetProfile):
            raise ValueError("source and target must use canonical contract types")
        validate_sha256(self.source_edit_plan_sha256, field_name="source_edit_plan_sha256")
        if not isinstance(self.state, ReframePlanState):
            raise ValueError("state must be a ReframePlanState")
        if not 1 <= len(self.source_keep_ranges) <= _MAX_KEEP_RANGES:
            raise ValueError("source_keep_ranges must contain 1-100000 rows")
        if not 1 <= len(self.segments) <= _MAX_SEGMENTS:
            raise ValueError("segments must contain 1-100000 rows")
        _validate_keep_ranges(self.source_keep_ranges, self.source.total_frames)
        expected_output_start = 0
        for ordinal, segment in enumerate(self.segments, start=1):
            if not isinstance(segment, ReframeSegment):
                raise ValueError("segments must contain ReframeSegment rows")
            if segment.segment_id != f"reframe-{ordinal:06d}":
                raise ValueError("segment IDs must be contiguous and canonical")
            if segment.output_range.start_frame != expected_output_start:
                raise ValueError("output ranges must be ordered and gapless")
            source_duration = segment.source_range.end_frame_exclusive - segment.source_range.start_frame
            output_duration = segment.output_range.end_frame_exclusive - segment.output_range.start_frame
            if source_duration != output_duration:
                raise ValueError("source and output segment durations must match")
            _validate_crop(segment.crop, self.source, self.target)
            expected_output_start = segment.output_range.end_frame_exclusive
        _require_exact_partition(self.source_keep_ranges, tuple(item.source_range for item in self.segments))

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-018",
            "upstream_edit_plan_owner": "TASK-007",
            "source": self.source.to_dict(),
            "source_edit_plan_sha256": self.source_edit_plan_sha256,
            "source_keep_ranges": [item.to_dict() for item in self.source_keep_ranges],
            "target": self.target.to_dict(),
            "segments": [item.to_dict() for item in self.segments],
            "state": self.state.value,
            "human_review_required": True,
            "media_read_performed": False,
            "remotion_execution_performed": False,
            "render_authorized": False,
            "timeline_mutation_authorized": False,
            "external_write_authorized": False,
        }
        return {**body, "plan_sha256": sha256_bytes(canonical_json_bytes(body))}


def compile_smart_reframe_plan(
    source: SourceVideoBinding,
    source_edit_plan_sha256: str,
    source_keep_ranges: Iterable[FrameRange],
    target: ReframeTargetProfile,
    proposals: Iterable[ReframeSegmentProposal],
) -> SmartReframePlan:
    """Compile bounded crop proposals without reading or rendering media."""

    if not isinstance(source, SourceVideoBinding) or not isinstance(target, ReframeTargetProfile):
        raise ValueError("source and target must use canonical contract types")
    validate_sha256(source_edit_plan_sha256, field_name="source_edit_plan_sha256")
    if target.frame_rate != source.frame_rate:
        raise ValueError("target frame rate must exactly equal the bound source rate")

    keep_ranges = tuple(source_keep_ranges)
    proposal_rows = tuple(proposals)
    if not 1 <= len(keep_ranges) <= _MAX_KEEP_RANGES:
        raise ValueError("source_keep_ranges must contain 1-100000 rows")
    if not 1 <= len(proposal_rows) <= _MAX_SEGMENTS:
        raise ValueError("proposals must contain 1-100000 rows")
    _validate_keep_ranges(keep_ranges, source.total_frames)

    segments: list[ReframeSegment] = []
    output_start = 0
    for ordinal, proposal in enumerate(proposal_rows, start=1):
        if not isinstance(proposal, ReframeSegmentProposal):
            raise ValueError("proposals must contain ReframeSegmentProposal rows")
        _validate_crop(proposal.crop, source, target)
        duration = proposal.source_range.end_frame_exclusive - proposal.source_range.start_frame
        output_range = FrameRange(output_start, output_start + duration)
        segments.append(
            ReframeSegment(
                f"reframe-{ordinal:06d}",
                proposal.source_range,
                output_range,
                proposal.crop,
                proposal.evidence,
            )
        )
        output_start += duration

    _require_exact_partition(keep_ranges, tuple(item.source_range for item in segments))
    validity = {ref.validity for item in segments for ref in item.evidence}
    if EvidenceValidity.REVOKED in validity or EvidenceValidity.STALE in validity:
        state = ReframePlanState.STALE_OR_REVOKED_EVIDENCE
    elif EvidenceValidity.UNKNOWN in validity:
        state = ReframePlanState.UNKNOWN_EVIDENCE
    else:
        state = ReframePlanState.READY_FOR_HUMAN_REVIEW
    return SmartReframePlan(source, source_edit_plan_sha256, keep_ranges, target, tuple(segments), state)


def verify_smart_reframe_plan_hash(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    body = dict(payload)
    claimed = body.pop("plan_sha256", None)
    validate_sha256(claimed, field_name="plan_sha256")
    target = body.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("target must be a mapping")
    target_body = dict(target)
    target_claimed = target_body.pop("profile_sha256", None)
    validate_sha256(target_claimed, field_name="target.profile_sha256")
    if target_claimed != sha256_bytes(canonical_json_bytes(target_body)):
        raise ValueError("target.profile_sha256 does not match the canonical target body")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("plan_sha256 does not match the canonical plan body")


def _validate_keep_ranges(ranges: tuple[FrameRange, ...], total_frames: int) -> None:
    previous_end = -1
    for item in ranges:
        if not isinstance(item, FrameRange):
            raise ValueError("source_keep_ranges must contain FrameRange rows")
        if item.end_frame_exclusive > total_frames:
            raise ValueError("keep range exceeds the bound source")
        if item.start_frame < previous_end:
            raise ValueError("keep ranges must be ordered and non-overlapping")
        previous_end = item.end_frame_exclusive


def _validate_crop(crop: CropWindow, source: SourceVideoBinding, target: ReframeTargetProfile) -> None:
    if crop.x + crop.width > source.width or crop.y + crop.height > source.height:
        raise ValueError("crop must be contained by the bound source geometry")
    if crop.width * target.height != crop.height * target.width:
        raise ValueError("crop aspect ratio must exactly equal the target aspect ratio")


def _require_exact_partition(expected: tuple[FrameRange, ...], actual: tuple[FrameRange, ...]) -> None:
    expected_frames = [(item.start_frame, item.end_frame_exclusive) for item in expected]
    index = 0
    for keep_start, keep_end in expected_frames:
        cursor = keep_start
        while index < len(actual) and actual[index].start_frame < keep_end:
            row = actual[index]
            if row.start_frame != cursor or row.end_frame_exclusive > keep_end:
                raise ValueError("proposal ranges must exactly partition the ordered keep ranges")
            cursor = row.end_frame_exclusive
            index += 1
        if cursor != keep_end:
            raise ValueError("proposal ranges must exactly cover every keep range")
    if index != len(actual):
        raise ValueError("proposal range exists outside the keep-range set")


__all__ = [
    "CropWindow",
    "EvidenceValidity",
    "FrameRange",
    "ReframeEvidenceRef",
    "ReframeEvidenceSource",
    "ReframePlanState",
    "ReframeSegmentProposal",
    "ReframeTargetProfile",
    "SmartReframePlan",
    "SourceVideoBinding",
    "compile_smart_reframe_plan",
    "verify_smart_reframe_plan_hash",
]
