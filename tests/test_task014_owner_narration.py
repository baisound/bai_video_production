from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.owner_narration import (
    CharacterAlignment,
    NarrationAlignmentService,
    NarrationGenerationMode,
    NarrationPlanningService,
    NarrationScript,
    VoiceProfile,
)


def profile(**overrides):
    values = dict(
        voice_profile_id="voice-profile-owner",
        provider_family="ELEVENLABS",
        credential_ref="credential://elevenlabs-owner",
        private_voice_id="private-provider-voice-id",
        ownership_verified=True,
        fine_tuned=True,
        approved_languages=("ja",),
        approved_model_ids=("eleven_multilingual_v2",),
        consent_subject_ref="owner-self",
        consent_scope="BAI project narration",
    )
    values.update(overrides)
    return VoiceProfile(**values)


def test_public_voice_profile_never_exposes_private_voice_id_or_credential_ref():
    body = profile().to_public_dict()
    assert body["raw_voice_id_persisted"] is False
    assert body["credential_ref_persisted"] is False
    assert "private-provider-voice-id" not in repr(body)
    assert "credential://elevenlabs-owner" not in repr(body)


def test_narration_plan_is_deterministic_and_does_not_persist_script_body():
    script = NarrationScript("script-1", "一つ目の段落。\n二つ目の段落。", "owner")
    first = NarrationPlanningService.compile(script, profile(), mode=NarrationGenerationMode.PREVIEW, model_id="eleven_multilingual_v2", language_code="ja", max_chars_per_chunk=100)
    second = NarrationPlanningService.compile(script, profile(), mode=NarrationGenerationMode.PREVIEW, model_id="eleven_multilingual_v2", language_code="ja", max_chars_per_chunk=100)
    assert first.to_dict()["plan_sha256"] == second.to_dict()["plan_sha256"]
    assert all(item["text_persisted"] is False for item in first.to_dict()["chunks"])
    assert "一つ目" not in repr(first.to_dict())


def test_paid_execution_is_separately_authorized_from_plan_compilation():
    plan = NarrationPlanningService.compile(NarrationScript("script-1", "テストです。", "owner"), profile(), mode=NarrationGenerationMode.FULL_RENDER, model_id="eleven_multilingual_v2", language_code="ja")
    with pytest.raises(ProductError) as exc:
        NarrationPlanningService.require_paid_execution_authorized(plan, explicit_paid_execution_authorization=False)
    assert exc.value.code == "ERR_NARRATION_PAID_EXECUTION_NOT_AUTHORIZED"
    NarrationPlanningService.require_paid_execution_authorized(plan, explicit_paid_execution_authorization=True)


def test_revoked_or_unapproved_voice_profile_fails_before_paid_call():
    script = NarrationScript("script-1", "テストです。", "owner")
    with pytest.raises(ProductError) as exc:
        NarrationPlanningService.compile(script, profile(revoked=True), mode=NarrationGenerationMode.PREVIEW, model_id="eleven_multilingual_v2", language_code="ja")
    assert exc.value.code == "ERR_VOICE_PROFILE_REVOKED"


def test_character_alignment_maps_to_narration_cues_and_detects_mismatch():
    rows = (
        CharacterAlignment("こ", 0, 100),
        CharacterAlignment("ん", 100, 200),
        CharacterAlignment("。", 200, 300),
        CharacterAlignment("次", 1200, 1300),
    )
    cues = NarrationAlignmentService.to_narration_cues("こん。次", rows)
    assert [(c.start_ms, c.end_ms, c.text) for c in cues] == [(0, 300, "こん。"), (1200, 1300, "次")]
    with pytest.raises(ProductError) as exc:
        NarrationAlignmentService.to_narration_cues("違う", rows)
    assert exc.value.code == "ERR_NARRATION_ALIGNMENT_TEXT_MISMATCH"
