from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_observation_envelope import (
    ObservationProvenance,
    SurvivorSignalKind,
    serialize_observations_csv,
    serialize_observations_jsonl,
    survivor_signal_to_observation,
)
from ai_video_production.dbd_observation_gold import (
    HudObservationGoldCase,
    HudObservationGoldEvaluator,
)
from ai_video_production.dbd_safe_visual_learning import SafeVisualLearningService
from ai_video_production.dbd_training_workspace import (
    VisualTrainingDomain,
    VisualTrainingManifest,
    VisualTrainingSample,
    VisualVideoTrainingRequest,
)
from ai_video_production.dbd_vision_slices import GrayImage, NormalizedROI, ReferenceSliceIndex


def provenance(slot: int) -> ObservationProvenance:
    return ObservationProvenance(
        workspace_id="workspace-1",
        runtime_profile_id="runtime-1",
        hud_profile_id="hud-1",
        hud_profile_version=2,
        roi_id=f"survivor_slot_{slot}",
        detector_version="survivor-v1",
    )


def pgm(path: Path, value: int = 0) -> Path:
    path.write_bytes(b"P5\n2 2\n255\n" + bytes([value]) * 4)
    return path


def test_four_survivor_slots_keep_independent_observation_identity() -> None:
    rows = tuple(
        survivor_signal_to_observation(
            observation_id=f"obs-{slot}",
            match_id="match-1",
            survivor_slot=slot,
            signal_kind=SurvivorSignalKind.CHASE_STATE,
            value="CHASE_ACTIVE" if slot == 2 else "NOT_CHASE",
            confidence_milli=900,
            source_frame=120,
            provenance=provenance(slot),
        )
        for slot in range(4)
    )
    payloads = [json.loads(line) for line in serialize_observations_jsonl(rows).splitlines()]
    assert {row["schema_version"] for row in payloads} == {"1.1.0"}
    assert [row["survivor_slot"] for row in payloads] == [0, 1, 2, 3]
    assert {row["match_id"] for row in payloads} == {"match-1"}
    assert {row["signal_kind"] for row in payloads} == {"CHASE_STATE"}
    csv_text = serialize_observations_csv(rows)
    assert "match_id,survivor_slot,signal_kind,source_frame" in csv_text


def test_unknown_slot_can_only_abstain() -> None:
    unknown = survivor_signal_to_observation(
        observation_id="obs-unknown", match_id="match-1", survivor_slot=None,
        signal_kind=SurvivorSignalKind.HOOK_COUNT, value="UNKNOWN",
        confidence_milli=0, source_frame=30, provenance=provenance(0),
    )
    assert unknown.survivor_slot is None and unknown.state == "UNKNOWN"
    with pytest.raises(ValueError, match="only emit UNKNOWN"):
        survivor_signal_to_observation(
            observation_id="obs-guessed", match_id="match-1", survivor_slot=None,
            signal_kind=SurvivorSignalKind.HOOK_COUNT, value="1",
            confidence_milli=800, source_frame=30, provenance=provenance(0),
        )
    with pytest.raises(ValueError, match="HOOK_COUNT value"):
        survivor_signal_to_observation(
            observation_id="obs-invalid", match_id="match-1", survivor_slot=0,
            signal_kind=SurvivorSignalKind.HOOK_COUNT, value="HOOKED",
            confidence_milli=800, source_frame=30, provenance=provenance(0),
        )


def test_gold_evaluator_keys_same_frame_by_survivor_subject() -> None:
    observations = tuple(
        survivor_signal_to_observation(
            observation_id=f"obs-{slot}", match_id="match-1", survivor_slot=slot,
            signal_kind=SurvivorSignalKind.SURVIVOR_STATE, value="HEALTHY",
            confidence_milli=950, source_frame=10, provenance=provenance(slot),
        )
        for slot in range(4)
    )
    cases = tuple(
        HudObservationGoldCase(
            case_id=f"case-{slot}", observation_type="SURVIVOR_STATUS", frame_index=10,
            expected_visibility=HudVisibility.UNKNOWN, expected_entity_id=None,
            expected_abstention=True, labeler_ref="owner-review",
            match_id="match-1", survivor_slot=slot,
        )
        for slot in range(4)
    )
    report = HudObservationGoldEvaluator.evaluate(cases, observations)
    assert report.case_count == 4


def test_survivor_teacher_manifest_requires_and_round_trips_subject(tmp_path: Path) -> None:
    image = pgm(tmp_path / "hook.pgm")
    with pytest.raises(ValueError, match="match_id"):
        VisualTrainingSample(
            domain=VisualTrainingDomain.SURVIVOR_HUD, label="1", image_path=str(image),
            registration_origin="MANUAL_IMAGE", survivor_slot=0,
            signal_kind=SurvivorSignalKind.HOOK_COUNT,
        )
    sample = VisualTrainingSample(
        domain=VisualTrainingDomain.SURVIVOR_HUD, label="1", image_path=str(image),
        registration_origin="MANUAL_IMAGE", slot="survivor_slot_2",
        match_id="match-1", survivor_slot=2,
        signal_kind=SurvivorSignalKind.HOOK_COUNT, source_frame=99,
    )
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    assert manifest.append(sample)
    assert manifest.list() == (sample,)
    assert "match_id,survivor_slot,signal_kind" in manifest.path.read_text(encoding="utf-8-sig")


def test_survivor_video_request_requires_exact_subject() -> None:
    with pytest.raises(ValueError, match="match_id"):
        VisualVideoTrainingRequest(
            domain=VisualTrainingDomain.SURVIVOR_HUD, label="HOOKED",
            video_path="owned.mp4", start_frame=0, end_frame_exclusive=2, slot=1,
        )
    request = VisualVideoTrainingRequest(
        domain=VisualTrainingDomain.SURVIVOR_HUD, label="HOOKED",
        video_path="owned.mp4", start_frame=0, end_frame_exclusive=2, slot=1,
        match_id="match-1", signal_kind=SurvivorSignalKind.SURVIVOR_STATE,
    )
    assert request.slot == 1 and request.match_id == "match-1"


def test_reference_index_round_trips_subject_metadata(tmp_path: Path) -> None:
    image = pgm(tmp_path / "chase.pgm", 7)
    index = ReferenceSliceIndex.train_from_pgm(
        index_id="survivor-chase",
        samples=[("CHASE_ACTIVE", image, "active", "match-1", 3, "CHASE_STATE")],
    )
    path = index.save(tmp_path / "index.json")
    loaded = ReferenceSliceIndex.load(path)
    ref = loaded.references[0]
    assert (ref.match_id, ref.survivor_slot, ref.signal_kind) == ("match-1", 3, "CHASE_STATE")
    match = loaded.match(GrayImage.read_pgm(image))[0]
    assert (match.match_id, match.survivor_slot, match.signal_kind) == ("match-1", 3, "CHASE_STATE")


def test_safe_preview_receipt_and_confirm_keep_survivor_subject(tmp_path: Path) -> None:
    class Extractor:
        def extract_frame_roi(self, **kwargs):
            output = Path(kwargs["output_path"])
            pgm(output, 3)
            return output

    video = tmp_path / "owned.mp4"
    video.write_bytes(b"owned-video")
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    service = SafeVisualLearningService(workspace_root=tmp_path, manifest=manifest)
    service.extractor = Extractor()
    staged = service.preview_video_frame(
        domain=VisualTrainingDomain.SURVIVOR_HUD, label="CHASE_ACTIVE",
        visibility=HudVisibility.VISIBLE, video_path=video, frame_index=42,
        roi=NormalizedROI("survivor_slot_1", 0.0, 0.0, 0.1, 0.1),
        match_id="match-1", survivor_slot=1,
        signal_kind=SurvivorSignalKind.CHASE_STATE,
    )
    receipt = json.loads((tmp_path / "staging" / "visual-learning" / staged.staging_id / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "1.2.0"
    assert (receipt["match_id"], receipt["survivor_slot"], receipt["signal_kind"]) == ("match-1", 1, "CHASE_STATE")
    assert service.confirm_register(staged)
    row = manifest.list()[0]
    assert (row.match_id, row.survivor_slot, row.signal_kind) == (
        "match-1", 1, SurvivorSignalKind.CHASE_STATE,
    )


def test_training_studio_exposes_survivor_subject_fields() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "サバイバー主体（SURVIVOR_HUD時は必須）" in text
    assert 'match_id=target.match_id' in Path("src/ai_video_production/dbd_safe_visual_learning.py").read_text(encoding="utf-8")
    assert 'SurvivorSignalKind(video_vars["signal_kind"].get())' in text
    assert "survivor_slot=(slot if domain is VisualTrainingDomain.SURVIVOR_HUD else None)" in text
