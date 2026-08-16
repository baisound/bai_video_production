from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production import audio_workspace_media_review as review


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64
NOW = "2026-08-17T02:00:00Z"


def policy(**overrides):
    fields = dict(
        policy_id="policy:task041:review:r0", revision=1, parent_record_sha256=None,
        required_sample_rate_hz=48_000, max_review_duration_samples=480_000,
        max_observation_age_seconds=3_600, official_policy_ref="task041:policy:review:r0",
        official_policy_sha256=H1, effective_at="2026-08-17T00:00:00Z",
        expires_at=None, audio_read_started=False, media_mutation_started=False,
    )
    fields.update(overrides)
    return review.AudioMediaReviewPolicyRevision.create(**fields)


def source(**overrides):
    fields = dict(
        source_id="source:audio:1", media_kind="VIDEO_WITH_EMBEDDED_AUDIO",
        contract_state="BOUND_VERIFIED", canonical_ref="asset-revision:1",
        canonical_sha256=H1, canonical_revision=1, candidate_id="candidate:1",
        asset_id="asset:1", rights_state="PASS", sample_rate_hz=48_000,
        channel_count=2, duration_samples=480_000,
        observed_at="2026-08-17T01:50:00Z", body_included=False,
        absolute_path_included=False,
    )
    fields.update(overrides)
    return review.AudioMediaSourceBinding.create(**fields)


def capability(**overrides):
    fields = dict(
        capability_id="capability:audio-review:1", contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED", waveform_state="SUPPORTED", decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED", capability_profile_ref="profile:audio-review:1",
        capability_profile_sha256=H2, app_identity_sha256=H3,
        observed_at="2026-08-17T01:55:00Z", body_included=False,
        absolute_path_included=False,
    )
    fields.update(overrides)
    return review.PlaybackWaveformCapabilityBinding.create(**fields)


def intent(p, s, c, **overrides):
    fields = dict(
        intent_id="intent:audio-review:1", revision=1, parent_record_sha256=None,
        project_id="project:1", policy_sha256=p.record_sha256,
        source_binding_sha256=s.record_sha256, capability_binding_sha256=c.record_sha256,
        audio_workspace_snapshot_sha256=H4,
        requested_operations=["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=0, range_end_sample=240_000, requested_at=NOW,
        body_included=False, absolute_path_included=False, playback_started=False,
        waveform_render_started=False, media_mutation_started=False,
    )
    fields.update(overrides)
    return review.AudioMediaReviewIntent.create(**fields)


def receipt(i, s, c, **overrides):
    fields = dict(
        contract_state="BOUND_VERIFIED", receipt_ref="receipt:audio-review:1",
        receipt_sha256=H1, intent_sha256=i.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256, range_start_sample=0,
        range_end_sample=240_000, external_state="COMPLETED",
        audition_completed=True, waveform_available=True, observed_at=NOW,
        canonical_persistence_verified=True, effect_started_by_module=False,
    )
    fields.update(overrides)
    return review.ExternalAudioReviewReceiptBinding.create(**fields)


def unresolved_receipt(**overrides):
    fields = dict(
        contract_state="CANONICAL_REF_NOT_PROVIDED", receipt_ref=None,
        receipt_sha256=None, intent_sha256=None, source_binding_sha256=None,
        capability_binding_sha256=None, range_start_sample=None, range_end_sample=None,
        external_state=None, audition_completed=None, waveform_available=None,
        observed_at=None, canonical_persistence_verified=None,
        effect_started_by_module=False,
    )
    fields.update(overrides)
    return review.ExternalAudioReviewReceiptBinding.create(**fields)


def test_schema_mirror_is_byte_exact_and_all_eight_types_round_trip():
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "audio-workspace-media-review.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / public.name
    assert public.read_bytes() == mirror.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    r = receipt(i, s, c)
    proposal = review.DerivedAudioAssetProposal.create(
        proposal_id="proposal:strip:1", revision=1, parent_record_sha256=None,
        source_binding_sha256=s.record_sha256, review_intent_sha256=i.record_sha256,
        derivation_kind="AUDIO_STRIPPED_VIDEO", proposed_asset_identity="asset-proposal:no-audio:1",
        lineage_sha256=H4, source_bytes_preserved=True, derived_bytes_present=False,
        asset_registration_started=False, media_mutation_started=False,
    )
    decision = review.AudioMediaReviewDecision.create(
        decision_id="decision:audio:1", revision=1, parent_record_sha256=None,
        intent_sha256=i.record_sha256, source_binding_sha256=s.record_sha256,
        external_review_receipt_sha256=r.record_sha256, audio_decision="STRIP_AUDIO",
        visual_decision="PASS", derived_proposal_sha256=proposal.record_sha256,
        reviewer_kind="OWNER_HUMAN", decided_at=NOW, evidence_ref="evidence:human:1",
        evidence_sha256=H3, reason_codes=["AUDIO_REJECTED"],
        asset_mutation_started=False, placement_mutation_started=False,
    )
    handoff = review.DawRoundTripStatusBinding.create(
        contract_state="BOUND_VERIFIED", handoff_ref="handoff:reaper:1",
        handoff_sha256=H1, review_decision_sha256=decision.record_sha256,
        task035_manifest_sha256=H2, returned_candidate_binding_sha256=None,
        handoff_state="EXTERNAL_PENDING", observed_at=NOW, reaper_launch_started=False,
        audio_render_started=False, asset_promotion_started=False,
    )
    records = [p, s, c, i, r, proposal, decision, handoff]
    assert {item.RECORD_TYPE for item in records} == set(review._CLASSES)
    for item in records:
        validator.validate(item.to_dict())
        assert review.validate_record(item.to_dict()).record_sha256 == item.record_sha256


def test_hash_is_deterministic_and_tamper_is_rejected():
    assert policy().record_sha256 == policy().record_sha256
    payload = policy().to_dict()
    payload["max_review_duration_samples"] = 1
    with pytest.raises(ValueError, match="record_sha256 mismatch"):
        review.validate_record(payload)


@pytest.mark.parametrize("bad", [r"C:\\private\\voice.wav", "/private/voice.wav", "../voice.wav", "credential:secret"])
def test_body_path_and_credentials_are_rejected(bad):
    with pytest.raises(ValueError, match="boundary|invalid"):
        source(canonical_ref=bad)


def test_unknown_fields_and_forgeable_execution_boolean_are_rejected():
    payload = intent(policy(), source(), capability()).to_dict()
    payload["execution_authorized"] = True
    with pytest.raises(ValueError, match="fields"):
        review.validate_record(payload)


def test_unresolved_bindings_cannot_invent_truth():
    with pytest.raises(ValueError, match="invents canonical truth"):
        source(contract_state="CANONICAL_REF_NOT_PROVIDED", canonical_ref="asset:1",
               canonical_sha256=None, canonical_revision=None, candidate_id=None,
               asset_id=None, rights_state="UNKNOWN", sample_rate_hz=None,
               channel_count=None, duration_samples=None, observed_at=None)
    with pytest.raises(ValueError, match="invents fields"):
        unresolved_receipt(receipt_ref="receipt:fake")


def test_admission_is_ready_without_starting_any_effect():
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    result = review.classify_review_admission(
        policy=p, source=s, capability=c, intent=i, evaluated_at=NOW,
    )
    assert result["decision"] == "READY_FOR_HUMAN_REVIEW"
    assert all(value is False for key, value in result.items() if key.endswith("_started"))


def test_admission_is_fail_closed_for_rights_unknown_and_capability_probe():
    p = policy()
    s = source(rights_state="UNKNOWN")
    c = capability(waveform_state="PROBE_REQUIRED")
    i = intent(p, s, c)
    result = review.classify_review_admission(
        policy=p, source=s, capability=c, intent=i, evaluated_at=NOW,
    )
    assert result["decision"] == "UNKNOWN"
    assert "SOURCE_RIGHTS_NOT_PASS" in result["reason_codes"]
    assert "WAVEFORM_VIEW_NOT_SUPPORTED" in result["reason_codes"]


def test_admission_rejects_hash_range_rate_and_staleness_drift():
    p = policy(max_observation_age_seconds=60)
    s = source(sample_rate_hz=44_100, duration_samples=100,
               observed_at="2026-08-17T01:00:00Z")
    c = capability(observed_at="2026-08-17T01:00:00Z")
    i = intent(p, s, c, source_binding_sha256=H1, range_end_sample=101)
    result = review.classify_review_admission(
        policy=p, source=s, capability=c, intent=i, evaluated_at=NOW,
    )
    assert result["decision"] == "BLOCKED"
    assert {"SOURCE_HASH_MISMATCH", "SAMPLE_RATE_MISMATCH", "RANGE_OUTSIDE_SOURCE",
            "SOURCE_OBSERVATION_STALE", "CAPABILITY_OBSERVATION_STALE"}.issubset(result["reason_codes"])


def test_external_receipt_inclusion_is_exact_and_cannot_be_forged_by_module():
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    r = receipt(i, s, c)
    result = review.validate_external_review_inclusion(receipt=r, intent=i, source=s, capability=c)
    assert result["classification"] == "ACCEPT_PROVEN_EXTERNAL_REVIEW"
    assert result["effect_started_by_module"] is False
    bad = receipt(i, s, c, range_end_sample=239_999)
    assert "RANGE_MISMATCH" in review.validate_external_review_inclusion(
        receipt=bad, intent=i, source=s, capability=c,
    )["reason_codes"]
    with pytest.raises(ValueError, match="cannot play"):
        receipt(i, s, c, effect_started_by_module=True)


def test_completed_receipt_requires_authoritative_persistence():
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    with pytest.raises(ValueError, match="persistence"):
        receipt(i, s, c, canonical_persistence_verified=False)
    unknown = receipt(i, s, c, external_state="UNKNOWN", audition_completed=False,
                      waveform_available=False, canonical_persistence_verified=False)
    assert unknown.to_dict()["external_state"] == "UNKNOWN"


def test_visual_and_audio_decisions_are_independent_and_derived_decisions_need_proposal():
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    common = dict(
        decision_id="decision:1", revision=1, parent_record_sha256=None,
        intent_sha256=i.record_sha256, source_binding_sha256=s.record_sha256,
        external_review_receipt_sha256=None, reviewer_kind="OWNER_HUMAN",
        decided_at=NOW, evidence_ref="evidence:1", evidence_sha256=H1,
        reason_codes=[], asset_mutation_started=False, placement_mutation_started=False,
    )
    accepted = review.AudioMediaReviewDecision.create(
        audio_decision="ACCEPT_AUDIO", visual_decision="FAIL",
        derived_proposal_sha256=None, **common,
    )
    assert accepted.to_dict()["visual_decision"] == "FAIL"
    with pytest.raises(ValueError, match="requires an exact proposal"):
        review.AudioMediaReviewDecision.create(
            audio_decision="STRIP_AUDIO", visual_decision="PASS",
            derived_proposal_sha256=None, **common,
        )


def test_derived_proposal_never_claims_bytes_registration_or_mutation():
    with pytest.raises(ValueError, match="cannot claim"):
        review.DerivedAudioAssetProposal.create(
            proposal_id="proposal:1", revision=1, parent_record_sha256=None,
            source_binding_sha256=H1, review_intent_sha256=H2,
            derivation_kind="AUDIO_STRIPPED_VIDEO", proposed_asset_identity="asset-proposal:1",
            lineage_sha256=H3, source_bytes_preserved=True, derived_bytes_present=True,
            asset_registration_started=False, media_mutation_started=False,
        )


def test_daw_round_trip_is_task035_binding_only_and_return_requires_candidate():
    with pytest.raises(ValueError, match="RETURN_RECEIVED"):
        review.DawRoundTripStatusBinding.create(
            contract_state="BOUND_VERIFIED", handoff_ref="handoff:1", handoff_sha256=H1,
            review_decision_sha256=H2, task035_manifest_sha256=H3,
            returned_candidate_binding_sha256=None, handoff_state="RETURN_RECEIVED",
            observed_at=NOW, reaper_launch_started=False, audio_render_started=False,
            asset_promotion_started=False,
        )
    with pytest.raises(ValueError, match="cannot start DAW"):
        review.DawRoundTripStatusBinding.create(
            contract_state="BOUND_VERIFIED", handoff_ref="handoff:1", handoff_sha256=H1,
            review_decision_sha256=H2, task035_manifest_sha256=H3,
            returned_candidate_binding_sha256=None, handoff_state="PROPOSED",
            observed_at=NOW, reaper_launch_started=True, audio_render_started=False,
            asset_promotion_started=False,
        )


def test_public_projection_and_static_surface_never_expose_private_audio_or_effects():
    projection = review.public_projection(source())
    assert projection["body_included"] is False
    assert projection["absolute_path_included"] is False
    assert projection["private_reference_included"] is False
    assert "canonical_ref" not in projection
    assert "canonical_sha256" not in projection
    assert set(review.EFFECT_SURFACE.values()) == {False}
    module_text = Path(review.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "requests", "urllib", "open(", "Path.write"):
        assert forbidden not in module_text
