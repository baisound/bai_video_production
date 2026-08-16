"""Pure TASK-005 Scene Boundary contract foundation.

The module validates in-memory detector proposals and produces a deterministic,
review-only manifest.  It deliberately has no media reader, detector runtime,
provider client, subprocess, filesystem writer, or downstream edit/generation
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
import json
import re
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_EVIDENCE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SCENE_ID_RE = re.compile(r"^scene-[0-9]{6}$")
_MAX_FRAMES = (1 << 63) - 1
_MAX_SCENES = 100_000
_MAX_CONFIG_BYTES = 1_048_576


def _require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


@dataclass(frozen=True, slots=True)
class FrameRate:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.numerator, bool)
            or not isinstance(self.numerator, int)
            or not 1 <= self.numerator <= 1_000_000
        ):
            raise ValueError("frame-rate numerator must be 1-1000000")
        if (
            isinstance(self.denominator, bool)
            or not isinstance(self.denominator, int)
            or not 1 <= self.denominator <= 100_000
        ):
            raise ValueError("frame-rate denominator must be 1-100000")
        if gcd(self.numerator, self.denominator) != 1:
            raise ValueError("frame rate must be reduced to its canonical rational form")

    def to_dict(self) -> dict[str, int]:
        return {"numerator": self.numerator, "denominator": self.denominator}


@dataclass(frozen=True, slots=True)
class SceneSourceBinding:
    source_asset_id: str
    source_sha256: str
    frame_rate: FrameRate
    total_frames: int

    def __post_init__(self) -> None:
        validate_id(self.source_asset_id, IdKind.ASSET)
        _require_sha256(self.source_sha256, "source_sha256")
        if (
            isinstance(self.total_frames, bool)
            or not isinstance(self.total_frames, int)
            or not 1 <= self.total_frames <= _MAX_FRAMES
        ):
            raise ValueError("total_frames must be 1..2^63-1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_asset_id": self.source_asset_id,
            "source_sha256": self.source_sha256,
            "frame_rate": self.frame_rate.to_dict(),
            "total_frames": self.total_frames,
        }


@dataclass(frozen=True, slots=True)
class DetectorProfile:
    profile_id: str
    profile_version: str
    config_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not _PROFILE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile_id is invalid")
        if not isinstance(self.profile_version, str) or not _SEMVER_RE.fullmatch(self.profile_version):
            raise ValueError("profile_version must be semantic version x.y.z")
        _require_sha256(self.config_sha256, "config_sha256")

    @classmethod
    def from_config(
        cls,
        profile_id: str,
        profile_version: str,
        config: Mapping[str, Any],
    ) -> "DetectorProfile":
        if not isinstance(config, Mapping):
            raise TypeError("config must be a mapping")
        try:
            config_bytes = json.dumps(
                dict(config),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("config must be strict canonical JSON data") from exc
        if len(config_bytes) > _MAX_CONFIG_BYTES:
            raise ValueError("canonical detector config exceeds 1048576 bytes")
        return cls(
            profile_id,
            profile_version,
            sha256_bytes(config_bytes),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "config_sha256": self.config_sha256,
        }


@dataclass(frozen=True, slots=True)
class DetectedSceneRange:
    start_frame: int
    end_frame_exclusive: int
    confidence_milli: int
    evidence_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.start_frame, bool)
            or not isinstance(self.start_frame, int)
            or self.start_frame < 0
        ):
            raise ValueError("start_frame must be a non-negative integer")
        if (
            isinstance(self.end_frame_exclusive, bool)
            or not isinstance(self.end_frame_exclusive, int)
            or self.end_frame_exclusive <= self.start_frame
            or self.end_frame_exclusive > _MAX_FRAMES
        ):
            raise ValueError("scene range must be positive and end-exclusive")
        if (
            isinstance(self.confidence_milli, bool)
            or not isinstance(self.confidence_milli, int)
            or not 0 <= self.confidence_milli <= 1000
        ):
            raise ValueError("confidence_milli must be 0-1000")
        if not 1 <= len(self.evidence_codes) <= 64:
            raise ValueError("evidence_codes must contain 1-64 values")
        if any(not isinstance(code, str) or not _EVIDENCE_CODE_RE.fullmatch(code) for code in self.evidence_codes):
            raise ValueError("evidence code is invalid")
        if self.evidence_codes != tuple(sorted(set(self.evidence_codes))):
            raise ValueError("evidence_codes must be unique and canonically sorted")


@runtime_checkable
class SceneBoundaryDetectorAdapter(Protocol):
    """Future detector boundary; this R0 package supplies no implementation."""

    def detect(
        self,
        source: SceneSourceBinding,
        profile: DetectorProfile,
    ) -> Sequence[DetectedSceneRange]: ...


@dataclass(frozen=True, slots=True)
class SceneBoundary:
    scene_id: str
    start_frame: int
    end_frame_exclusive: int
    confidence_milli: int
    evidence_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _SCENE_ID_RE.fullmatch(self.scene_id):
            raise ValueError("scene_id is invalid")
        DetectedSceneRange(
            self.start_frame,
            self.end_frame_exclusive,
            self.confidence_milli,
            self.evidence_codes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "range_frames": {
                "start": self.start_frame,
                "end_exclusive": self.end_frame_exclusive,
            },
            "confidence_milli": self.confidence_milli,
            "evidence_codes": list(self.evidence_codes),
            "decision_state": "PROPOSED_FOR_REVIEW",
        }


@dataclass(frozen=True, slots=True)
class SceneBoundaryManifest:
    source: SceneSourceBinding
    detector_profile: DetectorProfile
    scenes: tuple[SceneBoundary, ...]

    def __post_init__(self) -> None:
        if not 1 <= len(self.scenes) <= _MAX_SCENES:
            raise ValueError("scenes must contain 1-100000 rows")
        expected_start = 0
        for ordinal, scene in enumerate(self.scenes, start=1):
            if scene.scene_id != f"scene-{ordinal:06d}":
                raise ValueError("scene IDs must be contiguous and canonical")
            if scene.start_frame != expected_start:
                raise ValueError("scene ranges must be ordered, gapless, and non-overlapping")
            if scene.end_frame_exclusive > self.source.total_frames:
                raise ValueError("scene range exceeds the bound source")
            expected_start = scene.end_frame_exclusive
        if expected_start != self.source.total_frames:
            raise ValueError("scene ranges must cover the complete bound source")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "manifest_version": "1.0.0",
            "task_owner": "TASK-005",
            "source": self.source.to_dict(),
            "detector_profile": self.detector_profile.to_dict(),
            "scenes": [scene.to_dict() for scene in self.scenes],
            "review_state": "REVIEW_REQUIRED",
            "media_read_performed": False,
            "auto_apply_authorized": False,
            "generation_authorized": False,
            "timeline_mutation_authorized": False,
        }
        body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def build_scene_boundary_manifest(
    source: SceneSourceBinding,
    detector_profile: DetectorProfile,
    detected_ranges: Sequence[DetectedSceneRange],
) -> SceneBoundaryManifest:
    """Compile already-observed in-memory proposals into the immutable R0 contract."""

    if not isinstance(detected_ranges, Sequence):
        raise TypeError("detected_ranges must be a sequence")
    if not 1 <= len(detected_ranges) <= _MAX_SCENES:
        raise ValueError("detected_ranges must contain 1-100000 rows")
    scenes = tuple(
        SceneBoundary(
            scene_id=f"scene-{ordinal:06d}",
            start_frame=item.start_frame,
            end_frame_exclusive=item.end_frame_exclusive,
            confidence_milli=item.confidence_milli,
            evidence_codes=item.evidence_codes,
        )
        for ordinal, item in enumerate(detected_ranges, start=1)
    )
    return SceneBoundaryManifest(source, detector_profile, scenes)


def verify_scene_boundary_manifest_hash(payload: Mapping[str, Any]) -> None:
    """Verify the non-self manifest hash without accepting a digest-only substitute."""

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    body = dict(payload)
    claimed = body.pop("manifest_sha256", None)
    _require_sha256(claimed, "manifest_sha256")
    expected = sha256_bytes(canonical_json_bytes(body))
    if claimed != expected:
        raise ValueError("manifest_sha256 does not match the canonical manifest body")
