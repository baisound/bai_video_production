from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path

import pytest

from ai_video_production.scene_boundary import (
    DetectedSceneRange,
    DetectorProfile,
    FrameRate,
    SceneBoundaryDetectorAdapter,
    SceneSourceBinding,
    build_scene_boundary_manifest,
)
from ai_video_production.scene_boundary_adapter import (
    BoundedSyntheticSceneBoundaryDetectorAdapter,
)


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "ASSET-01J00000000000000000000000"
SOURCE_SHA = "sha256:" + "a" * 64


def source(**overrides: object) -> SceneSourceBinding:
    values: dict[str, object] = {
        "source_asset_id": ASSET_ID,
        "source_sha256": SOURCE_SHA,
        "frame_rate": FrameRate(30000, 1001),
        "total_frames": 300,
    }
    values.update(overrides)
    return SceneSourceBinding(**values)  # type: ignore[arg-type]


def profile(**overrides: object) -> DetectorProfile:
    values: dict[str, object] = {
        "profile_id": "synthetic.histogram-cut",
        "profile_version": "1.0.0",
        "config_sha256": "sha256:" + "b" * 64,
    }
    values.update(overrides)
    return DetectorProfile(**values)  # type: ignore[arg-type]


def ranges() -> tuple[DetectedSceneRange, ...]:
    return (
        DetectedSceneRange(0, 100, 900, ("FIRST_FRAME", "HISTOGRAM_CUT")),
        DetectedSceneRange(100, 225, 750, ("HISTOGRAM_CUT",)),
        DetectedSceneRange(225, 300, 1000, ("END_OF_SOURCE",)),
    )


def adapter() -> BoundedSyntheticSceneBoundaryDetectorAdapter:
    return BoundedSyntheticSceneBoundaryDetectorAdapter(source(), profile(), ranges())


def test_adapter_conforms_to_r0_protocol_and_is_explicitly_no_effect():
    candidate = adapter()
    assert isinstance(candidate, SceneBoundaryDetectorAdapter)
    assert candidate.synthetic_only is True
    assert candidate.media_read_performed is False
    assert candidate.external_effect_performed is False


def test_detection_is_deterministic_immutable_and_manifest_compatible():
    candidate = adapter()
    first = candidate.detect(source(), profile())
    second = candidate.detect(source(), profile())
    assert first is second
    assert first == ranges()
    assert build_scene_boundary_manifest(source(), profile(), first).to_dict() == build_scene_boundary_manifest(
        source(), profile(), second
    ).to_dict()
    with pytest.raises(FrozenInstanceError):
        candidate.bound_source = source(total_frames=1)  # type: ignore[misc]


@pytest.mark.parametrize(
    "mismatched_source",
    [
        source(source_asset_id="ASSET-01J00000000000000000000001"),
        source(source_sha256="sha256:" + "c" * 64),
        source(frame_rate=FrameRate(24, 1)),
        source(total_frames=301),
    ],
)
def test_every_source_binding_dimension_must_match(mismatched_source):
    with pytest.raises(ValueError, match="ERR_SYNTHETIC_SCENE_SOURCE_MISMATCH"):
        adapter().detect(mismatched_source, profile())


@pytest.mark.parametrize(
    "mismatched_profile",
    [
        profile(profile_id="synthetic.other"),
        profile(profile_version="1.0.1"),
        profile(config_sha256="sha256:" + "d" * 64),
    ],
)
def test_every_detector_profile_dimension_must_match(mismatched_profile):
    with pytest.raises(ValueError, match="ERR_SYNTHETIC_DETECTOR_PROFILE_MISMATCH"):
        adapter().detect(source(), mismatched_profile)


@pytest.mark.parametrize(
    "bad_ranges, message",
    [
        ((), "1-100000"),
        ((DetectedSceneRange(1, 300, 500, ("CUT",)),), "gapless"),
        (
            (
                DetectedSceneRange(0, 200, 500, ("CUT",)),
                DetectedSceneRange(199, 300, 500, ("CUT",)),
            ),
            "gapless",
        ),
        ((DetectedSceneRange(0, 299, 500, ("CUT",)),), "complete"),
        ((DetectedSceneRange(0, 301, 500, ("CUT",)),), "exceeds"),
    ],
)
def test_r0_compiler_rejects_malformed_proposal_sets(bad_ranges, message):
    with pytest.raises(ValueError, match=message):
        BoundedSyntheticSceneBoundaryDetectorAdapter(source(), profile(), bad_ranges)


def test_cap_plus_one_and_wrong_types_fail_closed_before_detection():
    one = DetectedSceneRange(0, 300, 500, ("CUT",))
    with pytest.raises(ValueError, match="1-100000"):
        BoundedSyntheticSceneBoundaryDetectorAdapter(source(), profile(), (one,) * 100_001)
    with pytest.raises(TypeError, match="every proposal"):
        BoundedSyntheticSceneBoundaryDetectorAdapter(source(), profile(), (object(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="source"):
        BoundedSyntheticSceneBoundaryDetectorAdapter(object(), profile(), ranges())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="profile"):
        BoundedSyntheticSceneBoundaryDetectorAdapter(source(), object(), ranges())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact tuple"):
        BoundedSyntheticSceneBoundaryDetectorAdapter(source(), profile(), list(ranges()))  # type: ignore[arg-type]


def test_constructor_has_no_path_bytes_callback_runner_or_effect_surface():
    parameters = set(inspect.signature(BoundedSyntheticSceneBoundaryDetectorAdapter).parameters)
    assert parameters == {"source", "profile", "proposals"}
    with pytest.raises(TypeError):
        BoundedSyntheticSceneBoundaryDetectorAdapter(  # type: ignore[call-arg]
            source(), profile(), ranges(), path="video.mp4"
        )

    module_path = ROOT / "src" / "ai_video_production" / "scene_boundary_adapter.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported_roots.isdisjoint(
        {"pathlib", "subprocess", "socket", "urllib", "requests", "cv2", "opencv", "ffmpeg"}
    )
    assert not any(isinstance(node, (ast.With, ast.AsyncWith)) for node in ast.walk(tree))
