from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.scene_boundary import (
    DetectedSceneRange,
    DetectorProfile,
    FrameRate,
    SceneBoundaryDetectorAdapter,
    SceneSourceBinding,
    build_scene_boundary_manifest,
    verify_scene_boundary_manifest_hash,
)
from ai_video_production.schema_contracts import validate_instance


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "ASSET-01J00000000000000000000000"
SOURCE_SHA = "sha256:" + "a" * 64


def source(*, total_frames: int = 300) -> SceneSourceBinding:
    return SceneSourceBinding(ASSET_ID, SOURCE_SHA, FrameRate(30000, 1001), total_frames)


def profile() -> DetectorProfile:
    return DetectorProfile.from_config(
        "synthetic.histogram-cut",
        "1.0.0",
        {"metric": "HISTOGRAM_DISTANCE", "threshold_milli": 420},
    )


def ranges() -> tuple[DetectedSceneRange, ...]:
    return (
        DetectedSceneRange(0, 100, 900, ("FIRST_FRAME", "HISTOGRAM_CUT")),
        DetectedSceneRange(100, 225, 750, ("HISTOGRAM_CUT",)),
        DetectedSceneRange(225, 300, 1000, ("END_OF_SOURCE",)),
    )


def test_manifest_is_deterministic_gapless_review_only_and_schema_valid():
    first = build_scene_boundary_manifest(source(), profile(), ranges())
    second = build_scene_boundary_manifest(source(), profile(), ranges())
    payload = first.to_dict()

    assert payload == second.to_dict()
    assert [row["scene_id"] for row in payload["scenes"]] == [
        "scene-000001",
        "scene-000002",
        "scene-000003",
    ]
    assert payload["scenes"][0]["range_frames"]["start"] == 0
    assert payload["scenes"][-1]["range_frames"]["end_exclusive"] == 300
    assert payload["review_state"] == "REVIEW_REQUIRED"
    assert payload["media_read_performed"] is False
    assert payload["auto_apply_authorized"] is False
    assert payload["generation_authorized"] is False
    assert payload["timeline_mutation_authorized"] is False
    verify_scene_boundary_manifest_hash(payload)
    validate_instance(payload, ROOT / "schemas" / "scene-boundary-manifest.schema.json")


def test_public_and_packaged_schema_are_byte_identical_and_meta_valid():
    public = (ROOT / "schemas" / "scene-boundary-manifest.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "scene-boundary-manifest.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(
        build_scene_boundary_manifest(source(), profile(), ranges()).to_dict(),
        json.loads(public),
    )


@pytest.mark.parametrize(
    "bad_ranges, message",
    [
        ((DetectedSceneRange(1, 300, 500, ("CUT",)),), "gapless"),
        (
            (
                DetectedSceneRange(0, 200, 500, ("CUT",)),
                DetectedSceneRange(199, 300, 500, ("CUT",)),
            ),
            "gapless",
        ),
        (
            (
                DetectedSceneRange(0, 100, 500, ("CUT",)),
                DetectedSceneRange(101, 300, 500, ("CUT",)),
            ),
            "gapless",
        ),
        ((DetectedSceneRange(0, 299, 500, ("CUT",)),), "complete"),
        ((DetectedSceneRange(0, 301, 500, ("CUT",)),), "exceeds"),
    ],
)
def test_invalid_range_gap_overlap_and_coverage_fail_closed(bad_ranges, message):
    with pytest.raises(ValueError, match=message):
        build_scene_boundary_manifest(source(), profile(), bad_ranges)


def test_empty_and_nonpositive_ranges_fail_closed():
    with pytest.raises(ValueError, match="1-100000"):
        build_scene_boundary_manifest(source(), profile(), ())
    with pytest.raises(ValueError, match="positive"):
        DetectedSceneRange(10, 10, 500, ("CUT",))


@pytest.mark.parametrize(
    "values, message",
    [
        ((0.0, 1, 500), "start_frame"),
        ((0, 1.0, 500), "positive"),
        ((0, 1, 500.0), "confidence_milli"),
        ((False, 1, 500), "start_frame"),
    ],
)
def test_frame_and_confidence_values_require_exact_integers(values, message):
    with pytest.raises(ValueError, match=message):
        DetectedSceneRange(*values, ("CUT",))


def test_asset_checksum_frame_rate_and_total_frame_binding_are_strict():
    with pytest.raises(ValueError, match="ASSET"):
        SceneSourceBinding("asset-display-name", SOURCE_SHA, FrameRate(24, 1), 10)
    with pytest.raises(ValueError, match="source_sha256"):
        SceneSourceBinding(ASSET_ID, "a" * 64, FrameRate(24, 1), 10)
    with pytest.raises(ValueError, match="canonical rational"):
        FrameRate(60000, 2002)
    with pytest.raises(ValueError, match="total_frames"):
        source(total_frames=0)
    with pytest.raises(ValueError, match="total_frames"):
        source(total_frames=300.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="numerator"):
        FrameRate(24.0, 1)  # type: ignore[arg-type]


def test_detector_profile_config_digest_is_canonical_and_versioned():
    left = DetectorProfile.from_config("detector", "1.2.3", {"b": 2, "a": 1})
    right = DetectorProfile.from_config("detector", "1.2.3", {"a": 1, "b": 2})
    assert left == right
    with pytest.raises(ValueError, match="semantic version"):
        DetectorProfile("detector", "latest", left.config_sha256)
    with pytest.raises(ValueError, match="config_sha256"):
        DetectorProfile("detector", "1.2.3", "sha256:unknown")


def test_detector_profile_rejects_non_json_non_finite_and_oversized_config():
    with pytest.raises(ValueError, match="strict canonical JSON"):
        DetectorProfile.from_config("detector", "1.0.0", {"threshold": float("nan")})
    with pytest.raises(ValueError, match="strict canonical JSON"):
        DetectorProfile.from_config("detector", "1.0.0", {"unsupported": object()})
    with pytest.raises(ValueError, match="exceeds 1048576"):
        DetectorProfile.from_config("detector", "1.0.0", {"payload": "x" * 1_048_576})


def test_manifest_hash_rejects_tamper_and_missing_digest():
    payload = build_scene_boundary_manifest(source(), profile(), ranges()).to_dict()
    payload["scenes"][0]["confidence_milli"] = 1
    with pytest.raises(ValueError, match="does not match"):
        verify_scene_boundary_manifest_hash(payload)
    payload.pop("manifest_sha256")
    with pytest.raises(ValueError, match="manifest_sha256"):
        verify_scene_boundary_manifest_hash(payload)


def test_contract_objects_are_immutable():
    bound = source()
    with pytest.raises(FrozenInstanceError):
        bound.total_frames = 1  # type: ignore[misc]


def test_evidence_codes_are_bounded_unique_and_canonically_sorted():
    with pytest.raises(ValueError, match="canonically sorted"):
        DetectedSceneRange(0, 1, 500, ("Z_CODE", "A_CODE"))
    with pytest.raises(ValueError, match="canonically sorted"):
        DetectedSceneRange(0, 1, 500, ("CUT", "CUT"))
    with pytest.raises(ValueError, match="evidence code"):
        DetectedSceneRange(0, 1, 500, ("free text",))
    with pytest.raises(ValueError, match="1-64"):
        DetectedSceneRange(0, 1, 500, tuple(f"CODE_{index:02d}" for index in range(65)))


def test_adapter_is_protocol_only_and_synthetic_fixture_can_conform():
    class SyntheticDetector:
        def detect(self, bound, detector_profile):
            assert bound == source()
            assert detector_profile == profile()
            return ranges()

    adapter = SyntheticDetector()
    assert isinstance(adapter, SceneBoundaryDetectorAdapter)
    manifest = build_scene_boundary_manifest(source(), profile(), adapter.detect(source(), profile()))
    assert len(manifest.scenes) == 3


def test_module_has_no_effect_or_existing_scene_orchestration_imports():
    text = (ROOT / "src" / "ai_video_production" / "scene_boundary.py").read_text(encoding="utf-8")
    forbidden = (
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "ffmpeg",
        "opencv",
        "cv2",
        "comfyui",
        "shot_feasibility",
        "production_blueprint",
        "production_control",
        "interactive_timeline",
    )
    assert all(f"import {name}" not in text and f"from .{name}" not in text for name in forbidden)
