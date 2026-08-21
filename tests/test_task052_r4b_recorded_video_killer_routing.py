from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_hud_detectors import SurvivorHudStateDetector
from ai_video_production.dbd_killer_capability_registry import (
    KillerCapability, KillerCapabilityRegistry, KillerDetectorType, KillerEffectFamily,
    KillerRoiFamily, KillerSpecificDetection, initial_killer_capabilities,
)
from ai_video_production.dbd_killer_knowledge import KillerPowerVisualRecognizer
from ai_video_production.dbd_recorded_video_recognition import DbDRecordedVideoRecognizer
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI, ReferenceSliceIndex


def _pgm(path: Path, seed: int) -> Path:
    pixels = bytearray()
    for y in range(16):
        for x in range(16):
            pixels.append(255 if ((x * (seed + 1) + y * (seed + 3) + seed) % 11) < 5 else 0)
    path.write_bytes(b"P5\n16 16\n255\n" + bytes(pixels))
    return path


class FakeExtractor:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls: list[tuple[int, str]] = []

    def extract_frame_roi(self, *, video_path, frame_index, roi, output_path, width=64, height=64):
        self.calls.append((frame_index, roi.roi_id))
        source = self.mapping[(frame_index, roi.roi_id)]
        Path(output_path).write_bytes(Path(source).read_bytes())
        return Path(output_path)


class FakeSpecificDetector:
    def __init__(self, namespace: str, *, stage: int | None = 2, progress: int | None = 300) -> None:
        self.namespace = namespace
        self.stage = stage
        self.progress = progress
        self.calls: list[int | None] = []

    def detect(self, image, *, capability, survivor_slot):
        self.calls.append(survivor_slot)
        return KillerSpecificDetection(self.namespace, True, self.stage, self.progress, 900)


def _killer_recognizer(onryo: Path, other: Path) -> KillerPowerVisualRecognizer:
    index = ReferenceSliceIndex.train_from_pgm(
        index_id="killer-r4b", samples=[("killer_onryo", onryo), ("power_other", other)]
    )
    return KillerPowerVisualRecognizer(index, acceptance_milli=500)


def test_recorded_video_routes_known_killer_overlays_and_reuses_common_survivor_slices(tmp_path: Path) -> None:
    onryo_image = _pgm(tmp_path / "onryo.pgm", 1)
    other_image = _pgm(tmp_path / "other.pgm", 2)
    survivor_image = _pgm(tmp_path / "survivor.pgm", 3)
    injured_image = _pgm(tmp_path / "injured.pgm", 4)
    profile = DBDHudRoiProfile(killer_power_hud=NormalizedROI("killer_power", 0.4, 0.8, 0.1, 0.1))
    mapping = {(10, "killer_power"): onryo_image}
    for slot in range(4):
        mapping[(10, profile.survivor_slot_roi(slot).roi_id)] = survivor_image
    extractor = FakeExtractor(mapping)
    survivor_index = ReferenceSliceIndex.train_from_pgm(
        index_id="survivor-r4b", samples=[("HEALTHY", survivor_image), ("INJURED", injured_image)]
    )
    capability = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = FakeSpecificDetector(capability.training_label_namespace)
    registry = KillerCapabilityRegistry((capability,), {(capability.killer_id, capability.effect_id): detector})
    recognizer = DbDRecordedVideoRecognizer(
        roi_profile=profile,
        extractor=extractor,
        survivor_detector=SurvivorHudStateDetector(survivor_index, acceptance_milli=500),
        killer_power_recognizer=_killer_recognizer(onryo_image, other_image),
        killer_capability_registry=registry,
    )

    result = recognizer.recognize_frame(
        video_path=tmp_path / "fake.mp4", frame_index=10,
        working_directory=tmp_path / "work", match_id="match-r4b",
    )
    assert result.killer_power.entity_id == "killer_onryo"
    assert result.killer_specific.selected_killer_id == "killer_onryo"
    assert [item.survivor_slot for item in result.killer_specific.observations] == [0, 1, 2, 3]
    assert detector.calls == [0, 1, 2, 3]
    assert len(result.slice_artifacts) == 5
    assert len(extractor.calls) == 5
    assert all(item.evidence_ref.startswith("recognition://roi-slice/survivor_slot_") for item in result.killer_specific.observations)
    assert all(str(tmp_path) not in item.evidence_ref for item in result.killer_specific.observations)
    with pytest.raises(ValueError, match="must match the frame"):
        replace(result, frame_index=11)


def test_unknown_or_power_only_identity_does_not_slice_or_invoke_specific_overlay(tmp_path: Path) -> None:
    onryo_image = _pgm(tmp_path / "onryo.pgm", 1)
    power_image = _pgm(tmp_path / "power.pgm", 2)
    profile = DBDHudRoiProfile(killer_power_hud=NormalizedROI("killer_power", 0.4, 0.8, 0.1, 0.1))
    extractor = FakeExtractor({(20, "killer_power"): power_image})
    capability = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = FakeSpecificDetector(capability.training_label_namespace)
    recognizer = DbDRecordedVideoRecognizer(
        roi_profile=profile,
        extractor=extractor,
        killer_power_recognizer=_killer_recognizer(onryo_image, power_image),
        killer_capability_registry=KillerCapabilityRegistry(
            (capability,), {(capability.killer_id, capability.effect_id): detector}
        ),
    )
    result = recognizer.recognize_frame(
        video_path=tmp_path / "fake.mp4", frame_index=20,
        working_directory=tmp_path / "work", match_id="match-r4b",
    )
    assert result.killer_power.kind.value == "POWER"
    assert result.killer_specific.selected_killer_id is None
    assert result.killer_specific.records[0].reason_codes == ("KILLER_IDENTITY_UNKNOWN",)
    assert extractor.calls == [(20, "killer_power")]
    assert detector.calls == []


def test_registry_without_identity_recognizer_returns_unknown_without_media_slice(tmp_path: Path) -> None:
    capability = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = FakeSpecificDetector(capability.training_label_namespace)
    extractor = FakeExtractor({})
    recognizer = DbDRecordedVideoRecognizer(
        extractor=extractor,
        killer_capability_registry=KillerCapabilityRegistry(
            (capability,), {(capability.killer_id, capability.effect_id): detector}
        ),
    )
    result = recognizer.recognize_frame(
        video_path=tmp_path / "fake.mp4", frame_index=30,
        working_directory=tmp_path / "work", match_id="match-r4b",
    )
    assert result.killer_specific.records[0].reason_codes == ("KILLER_IDENTITY_UNKNOWN",)
    assert result.killer_specific.observations[0].evidence_ref == "recognition://killer-identity-unavailable/30"
    assert extractor.calls == []
    assert detector.calls == []


def test_registry_requires_match_identity_before_any_slice(tmp_path: Path) -> None:
    capability = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    extractor = FakeExtractor({})
    recognizer = DbDRecordedVideoRecognizer(
        extractor=extractor,
        killer_capability_registry=KillerCapabilityRegistry((capability,), {}),
    )
    with pytest.raises(ValueError, match="match_id is required"):
        recognizer.recognize_frame(video_path=tmp_path / "fake.mp4", frame_index=1)
    assert extractor.calls == []


def test_global_killer_power_capability_reuses_identity_slice(tmp_path: Path) -> None:
    onryo_image = _pgm(tmp_path / "onryo.pgm", 1)
    other_image = _pgm(tmp_path / "other.pgm", 2)
    profile = DBDHudRoiProfile(killer_power_hud=NormalizedROI("killer_power", 0.4, 0.8, 0.1, 0.1))
    namespace = "KILLER_SPECIFIC_HUD/killer_onryo/power_mode"
    capability = KillerCapability(
        "killer_onryo", "power_mode", KillerEffectFamily.POWER_STATE,
        KillerRoiFamily.KILLER_POWER_HUD, KillerDetectorType.REFERENCE_SLICE,
        False, namespace, ("KILLER_SPECIFIC_HUD/killer_doctor/madness",),
    )
    detector = FakeSpecificDetector(namespace, stage=None, progress=None)
    extractor = FakeExtractor({(40, "killer_power"): onryo_image})
    recognizer = DbDRecordedVideoRecognizer(
        roi_profile=profile,
        extractor=extractor,
        killer_power_recognizer=_killer_recognizer(onryo_image, other_image),
        killer_capability_registry=KillerCapabilityRegistry(
            (capability,), {(capability.killer_id, capability.effect_id): detector}
        ),
    )
    result = recognizer.recognize_frame(
        video_path=tmp_path / "fake.mp4", frame_index=40,
        working_directory=tmp_path / "work", match_id="match-r4b",
    )
    assert detector.calls == [None]
    assert len(result.slice_artifacts) == 1
    assert extractor.calls == [(40, "killer_power")]
    assert result.killer_specific.observations[0].evidence_ref == result.slice_artifacts[0].evidence_ref
