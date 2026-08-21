from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_hud_visibility import HudVisibility
from ai_video_production.dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    StatusEffectDefinition,
)
from ai_video_production.dbd_safe_visual_learning import SafeVisualLearningService
from ai_video_production.dbd_status_effect_recognition import StatusEffectIconRecognizer
from ai_video_production.dbd_training_workspace import (
    VisualTrainingDomain,
    VisualTrainingManifest,
    VisualTrainingSample,
)
from ai_video_production.dbd_vision_slices import NormalizedROI, ReferenceSliceIndex


DEFINITIONS = (
    StatusEffectDefinition(
        "status_bloodlust", EffectPolarity.POSITIVE, EffectSourceKind.GAME_MECHANIC,
        survivor_scoped=False,
    ),
    StatusEffectDefinition(
        "status_hindered", EffectPolarity.NEGATIVE, EffectSourceKind.PERK,
        survivor_scoped=False,
    ),
)


def _pgm(path: Path, seed: int) -> Path:
    pixels = bytearray()
    for y in range(16):
        for x in range(16):
            pixels.append(255 if ((x * (seed + 1) + y * (seed + 3) + seed) % 13) < 6 else 0)
    path.write_bytes(b"P5\n16 16\n255\n" + bytes(pixels))
    return path


def _sample(path: Path, *, hard_negative: bool = False) -> VisualTrainingSample:
    return VisualTrainingSample(
        domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
        label=(
            "PERK_ICON/perk_sprint_burst"
            if hard_negative else "STATUS_EFFECT_POSITIVE/status_bloodlust"
        ),
        image_path=str(path),
        group="hard-negative" if hard_negative else "normal",
        source_ref="video://owned/status-effect",
        registration_origin="MANUAL_IMAGE",
        slot="bottom_right_positive_effects/segment_0",
        display_state=HudVisibility.VISIBLE.value,
    )


def test_status_teacher_manifest_round_trip_and_safe_index_build(tmp_path: Path) -> None:
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    positive = _sample(_pgm(tmp_path / "bloodlust.pgm", 1))
    hard_negative = _sample(_pgm(tmp_path / "perk.pgm", 7), hard_negative=True)
    assert manifest.append(positive)
    assert manifest.append(hard_negative)
    assert manifest.list(domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE) == (
        positive, hard_negative,
    )

    index_path = manifest.build_reference_index(
        domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
        output_path=tmp_path / "status-positive.json",
        index_id="status-positive",
        status_effect_definitions=DEFINITIONS,
    )
    index = ReferenceSliceIndex.load(index_path)
    StatusEffectIconRecognizer(index, definitions=DEFINITIONS)
    assert {item.label for item in index.references} == {
        "STATUS_EFFECT_POSITIVE/status_bloodlust",
        "PERK_ICON/perk_sprint_burst",
    }


def test_status_teacher_requires_identity_hard_negative_and_registered_definition(tmp_path: Path) -> None:
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    manifest.append(_sample(_pgm(tmp_path / "bloodlust.pgm", 1)))
    with pytest.raises(ValueError, match="identity and hard-negative"):
        manifest.build_reference_index(
            domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
            output_path=tmp_path / "unsafe.json",
            index_id="unsafe",
            status_effect_definitions=DEFINITIONS,
        )
    manifest.append(_sample(_pgm(tmp_path / "perk.pgm", 7), hard_negative=True))
    with pytest.raises(ValueError, match="unregistered effect_id"):
        manifest.build_reference_index(
            domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
            output_path=tmp_path / "unsafe.json",
            index_id="unsafe",
            status_effect_definitions=(DEFINITIONS[1],),
        )


def test_status_teacher_namespace_and_group_crossings_fail_closed(tmp_path: Path) -> None:
    image = _pgm(tmp_path / "sample.pgm", 1)
    with pytest.raises(ValueError, match="hard-negative sample"):
        replace(_sample(image, hard_negative=True), group="normal")
    with pytest.raises(ValueError, match="identity hard-negative"):
        replace(
            _sample(image),
            label="STATUS_EFFECT_NEGATIVE/VISIBILITY/HIDDEN",
            group="hard-negative",
        )
    with pytest.raises(ValueError, match="Survivor subject"):
        replace(_sample(image), match_id="foreign-subject")


class FakeExtractor:
    def extract_frame_roi(self, *, output_path, **_kwargs):
        return _pgm(Path(output_path), 3)


def test_safe_visual_learning_revalidates_status_domain_roi_and_receipt(tmp_path: Path) -> None:
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"video")
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    service = SafeVisualLearningService(
        workspace_root=tmp_path,
        manifest=manifest,
        status_effect_definitions=DEFINITIONS,
    )
    service.extractor = FakeExtractor()
    roi = NormalizedROI(
        "bottom_right_positive_effects/segment_0", 0.7, 0.7, 0.05, 0.08,
    )
    staged = service.preview_video_frame(
        domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
        label="STATUS_EFFECT_POSITIVE/status_bloodlust",
        visibility=HudVisibility.VISIBLE,
        video_path=video,
        frame_index=10,
        roi=roi,
    )
    tampered = replace(staged, label="STATUS_EFFECT_NEGATIVE/status_hindered")
    service._write_receipt(tampered)
    with pytest.raises(ValueError, match="逆極性Teacher"):
        service.confirm_register(staged)
    assert manifest.list() == ()

    with pytest.raises(ValueError, match="極性とROI"):
        service.preview_video_frame(
            domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
            label="STATUS_EFFECT_POSITIVE/status_bloodlust",
            visibility=HudVisibility.VISIBLE,
            video_path=video,
            frame_index=11,
            roi=NormalizedROI(
                "bottom_right_negative_effects/segment_0", 0.7, 0.6, 0.05, 0.08,
            ),
        )
    with pytest.raises(ValueError, match="未登録"):
        service.preview_video_frame(
            domain=VisualTrainingDomain.STATUS_EFFECT_POSITIVE,
            label="STATUS_EFFECT_POSITIVE/status_unknown",
            visibility=HudVisibility.VISIBLE,
            video_path=video,
            frame_index=12,
            roi=roi,
        )
