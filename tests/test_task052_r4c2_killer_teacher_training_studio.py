from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_killer_capability_registry import (
    KillerCapabilityRegistry,
    initial_killer_capabilities,
)
from ai_video_production.dbd_killer_specific_detector import KillerSpecificTeacherRole
from ai_video_production.dbd_observation_envelope import SurvivorSignalKind
from ai_video_production.dbd_safe_visual_learning import BatchVisualTarget, SafeVisualLearningService
from ai_video_production.dbd_training_hud_binding import slot_specifications, training_roi
from ai_video_production.dbd_training_workspace import VisualTrainingDomain, VisualTrainingManifest
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI


class Extractor:
    ffmpeg_executable = "fake-ffmpeg"

    def extract_frame_roi(self, **kwargs):
        output = Path(kwargs["output_path"])
        seed = int(kwargs["frame_index"]) % 2
        pixels = bytes((0, 255, 255 if seed else 0, 0 if seed else 255))
        output.write_bytes(b"P5\n2 2\n255\n" + pixels)
        return output


def _service(tmp_path: Path, *, with_registry: bool = True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"owned-video")
    registry = KillerCapabilityRegistry(initial_killer_capabilities(), {}) if with_registry else None
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    service = SafeVisualLearningService(
        workspace_root=tmp_path,
        manifest=manifest,
        killer_capability_registry=registry,
    )
    service.extractor = Extractor()
    return service, manifest, video


def _target(*, role: KillerSpecificTeacherRole) -> BatchVisualTarget:
    namespace = (
        "KILLER_SPECIFIC_HUD/killer_onryo/condemn"
        if role is KillerSpecificTeacherRole.POSITIVE
        else "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress"
    )
    return BatchVisualTarget(
        domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
        label="condemn-positive" if role is KillerSpecificTeacherRole.POSITIVE else "condemn-hard-negative",
        visibility=HudVisibility.VISIBLE,
        roi=NormalizedROI("survivor_slot_0", 0.0, 0.0, 0.1, 0.1),
        group="positive" if role is KillerSpecificTeacherRole.POSITIVE else "hard-negative",
        match_id="match-r4c2",
        survivor_slot=0,
        killer_id="killer_onryo",
        effect_id="condemn",
        label_namespace=namespace,
        teacher_role=role,
        active=True if role is KillerSpecificTeacherRole.POSITIVE else None,
        stage=2 if role is KillerSpecificTeacherRole.POSITIVE else None,
        progress_milli=300 if role is KillerSpecificTeacherRole.POSITIVE else None,
    )


def test_batch_preview_receipt_and_confirm_preserve_teacher_contract(tmp_path: Path) -> None:
    service, manifest, video = _service(tmp_path)
    report = service.preview_video_batch(
        video_path=video,
        start_frame=0,
        end_frame_exclusive=1,
        frame_step=1,
        targets=(
            _target(role=KillerSpecificTeacherRole.POSITIVE),
            _target(role=KillerSpecificTeacherRole.HARD_NEGATIVE),
        ),
    )
    assert report.total_samples == 2
    restored = tuple(service.load_staged(item.staging_id) for item in report.staged)
    assert {item.teacher_role for item in restored} == {
        KillerSpecificTeacherRole.POSITIVE,
        KillerSpecificTeacherRole.HARD_NEGATIVE,
    }
    assert restored[0].killer_id == "killer_onryo"
    receipt = json.loads(
        (tmp_path / "staging" / "visual-learning" / restored[0].staging_id / "receipt.json")
        .read_text(encoding="utf-8")
    )
    assert receipt["schema_version"] == "1.2.0"
    assert receipt["label_namespace"].startswith("KILLER_SPECIFIC_HUD/")

    confirmed = service.confirm_batch(restored)
    assert confirmed.confirm_count == 2
    assert confirmed.failed_count == 0
    assert confirmed.affected_domains == ("KILLER_SPECIFIC_HUD",)
    assert len(confirmed.index_paths) == 1 and Path(confirmed.index_paths[0]).is_file()
    samples = manifest.list(domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD)
    assert {item.teacher_role for item in samples} == {
        KillerSpecificTeacherRole.POSITIVE,
        KillerSpecificTeacherRole.HARD_NEGATIVE,
    }
    assert {item.label_namespace for item in samples} == {
        "KILLER_SPECIFIC_HUD/killer_onryo/condemn",
        "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress",
    }


def test_preview_fails_closed_without_registry_or_registered_namespace(tmp_path: Path) -> None:
    service, _manifest, video = _service(tmp_path, with_registry=False)
    target = _target(role=KillerSpecificTeacherRole.POSITIVE)
    with pytest.raises(ValueError, match="Capability Registry"):
        service.preview_video_frame(
            domain=target.domain, label=target.label, visibility=target.visibility,
            video_path=video, frame_index=0, roi=target.roi,
            match_id=target.match_id, survivor_slot=target.survivor_slot,
            killer_id=target.killer_id, effect_id=target.effect_id,
            label_namespace=target.label_namespace, teacher_role=target.teacher_role,
            active=target.active, stage=target.stage, progress_milli=target.progress_milli,
        )

    service, _manifest, video = _service(tmp_path / "registered")
    invalid = _target(role=KillerSpecificTeacherRole.HARD_NEGATIVE)
    with pytest.raises(ValueError, match="Hard Negative"):
        service.preview_video_frame(
            domain=invalid.domain, label=invalid.label, visibility=invalid.visibility,
            video_path=video, frame_index=0, roi=invalid.roi,
            match_id=invalid.match_id, survivor_slot=invalid.survivor_slot,
            killer_id=invalid.killer_id, effect_id=invalid.effect_id,
            label_namespace="KILLER_SPECIFIC_HUD/killer_test/other",
            teacher_role=invalid.teacher_role,
        )


def test_confirm_revalidates_tampered_teacher_receipt_before_commit(tmp_path: Path) -> None:
    service, manifest, video = _service(tmp_path)
    target = _target(role=KillerSpecificTeacherRole.HARD_NEGATIVE)
    staged = service.preview_video_frame(
        domain=target.domain, label=target.label, visibility=target.visibility,
        video_path=video, frame_index=0, roi=target.roi,
        group=target.group, match_id=target.match_id,
        survivor_slot=target.survivor_slot, killer_id=target.killer_id,
        effect_id=target.effect_id, label_namespace=target.label_namespace,
        teacher_role=target.teacher_role,
    )
    receipt_path = (
        tmp_path / "staging" / "visual-learning" / staged.staging_id / "receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["label_namespace"] = "KILLER_SPECIFIC_HUD/killer_test/other"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="Hard Negative"):
        service.confirm_batch((staged,), rebuild_indexes=False)
    assert manifest.list() == ()
    assert not tuple((tmp_path / "training-data").rglob("*.pgm"))


def test_survivor_domain_rejects_killer_teacher_field_mixing(tmp_path: Path) -> None:
    service, _manifest, video = _service(tmp_path)
    with pytest.raises(ValueError, match="キラー固有HUD専用"):
        service.preview_video_frame(
            domain=VisualTrainingDomain.SURVIVOR_HUD,
            label="CHASE_ACTIVE",
            visibility=HudVisibility.VISIBLE,
            video_path=video,
            frame_index=0,
            roi=NormalizedROI("survivor_slot_0", 0.0, 0.0, 0.1, 0.1),
            match_id="match-r4c2",
            survivor_slot=0,
            signal_kind=SurvivorSignalKind.CHASE_STATE,
            killer_id="killer_onryo",
        )

def test_killer_specific_training_uses_existing_survivor_slot_rois() -> None:
    profile = DBDHudRoiProfile()
    specs = slot_specifications(VisualTrainingDomain.KILLER_SPECIFIC_HUD)
    assert tuple(slot for slot, _ in specs) == (0, 1, 2, 3)
    assert training_roi(profile, VisualTrainingDomain.KILLER_SPECIFIC_HUD, 2) == profile.survivor_slot_roi(2)


def test_training_studio_routes_only_through_capability_bound_teacher_controls() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "KillerCapabilityRegistry(initial_killer_capabilities(), {})" in text
    assert "killer_capability_registry=killer_capability_registry" in text
    assert "selected_killer_teacher_values" in text
    assert "teacher_role=teacher_role" in text
    assert "汎用編集は使用できません" in text
    assert '"KILLER_SPECIFIC_HUD": "キラー固有HUD（Teacher）"' in Path(
        "src/ai_video_production/dbd_training_form_support.py"
    ).read_text(encoding="utf-8")
