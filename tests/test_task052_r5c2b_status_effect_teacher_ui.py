from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.dbd_killer_status_temporal import (
    EffectPolarity,
    EffectSourceKind,
    StatusEffectDefinition,
)
from ai_video_production.dbd_status_effect_registry import (
    StatusEffectRegistry, status_effect_teacher_label,
)
from ai_video_production.dbd_training_form_support import VISUAL_TRAINING_DOMAIN_JA
from ai_video_production.dbd_training_hud_binding import slot_specifications, training_roi
from ai_video_production.dbd_training_workspace import VisualTrainingDomain
from ai_video_production.dbd_vision_slices import DBDHudRoiProfile, NormalizedROI


def _definition(effect_id: str = "status_bloodlust") -> StatusEffectDefinition:
    return StatusEffectDefinition(
        effect_id, EffectPolarity.POSITIVE, EffectSourceKind.GAME_MECHANIC,
        survivor_scoped=False,
    )


def _profile() -> DBDHudRoiProfile:
    return DBDHudRoiProfile(
        profile_id="profile", calibrated_frame_width=1920,
        calibrated_frame_height=1080, ui_scale_percent=100,
        bottom_right_positive_effects=NormalizedROI("bottom_right_positive_effects", 0.7, 0.7, 0.1, 0.1),
        bottom_right_negative_effects=NormalizedROI("bottom_right_negative_effects", 0.7, 0.6, 0.1, 0.1),
    )


def test_registry_is_atomic_revisioned_and_round_trips(tmp_path: Path) -> None:
    registry = StatusEffectRegistry(tmp_path / "knowledge" / "status-effect-definitions.json")
    assert registry.snapshot().revision == 0
    first = registry.upsert(_definition(), expected_revision=0)
    assert first.revision == 1
    assert registry.snapshot().definitions == (_definition(),)
    with pytest.raises(ValueError, match="revision conflict"):
        registry.upsert(_definition("status_haste"), expected_revision=0)


def test_registry_rejects_tampered_schema_and_duplicate_identity(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    registry = StatusEffectRegistry(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "99.0.0"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        registry.snapshot()

    registry = StatusEffectRegistry(tmp_path / "clean.json")
    with pytest.raises(ValueError, match="unique"):
        registry.replace((_definition(), _definition()), expected_revision=0)


def test_status_domains_have_japanese_labels_and_exact_profile_regions() -> None:
    assert VISUAL_TRAINING_DOMAIN_JA["STATUS_EFFECT_POSITIVE"] == "ポジティブ状態効果"
    assert VISUAL_TRAINING_DOMAIN_JA["STATUS_EFFECT_NEGATIVE"] == "ネガティブ状態効果"
    assert slot_specifications(VisualTrainingDomain.STATUS_EFFECT_POSITIVE) == ((None, "ポジティブ状態効果"),)
    assert slot_specifications(VisualTrainingDomain.STATUS_EFFECT_NEGATIVE) == ((None, "ネガティブ状態効果"),)
    assert training_roi(_profile(), VisualTrainingDomain.STATUS_EFFECT_POSITIVE, None).roi_id == "bottom_right_positive_effects"
    assert training_roi(_profile(), VisualTrainingDomain.STATUS_EFFECT_NEGATIVE, None).roi_id == "bottom_right_negative_effects"


def test_operator_label_builder_keeps_identity_polarity_and_perk_hard_negative_separate() -> None:
    assert status_effect_teacher_label(
        polarity=EffectPolarity.POSITIVE, definition=_definition(),
    ) == "STATUS_EFFECT_POSITIVE/status_bloodlust"
    assert status_effect_teacher_label(
        polarity=EffectPolarity.NEGATIVE, hard_negative_perk_id="perk_sprint_burst",
    ) == "PERK_ICON/perk_sprint_burst"
    with pytest.raises(ValueError, match="polarity"):
        status_effect_teacher_label(
            polarity=EffectPolarity.NEGATIVE, definition=_definition(),
        )
    with pytest.raises(ValueError, match="mutually exclusive"):
        status_effect_teacher_label(
            polarity=EffectPolarity.POSITIVE, definition=_definition(),
            hard_negative_perk_id="perk_sprint_burst",
        )


def test_training_studio_exposes_registry_bound_status_teacher_controls() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    for marker in (
        "StatusEffectRegistry", "status-effect-definitions.json",
        "status_effect_definitions=", "STATUS_EFFECT_POSITIVE",
        "STATUS_EFFECT_NEGATIVE", "status_effect_teacher_label", "状態効果定義を登録",
        "status_single_icon_confirmed",
    ):
        assert marker in text
