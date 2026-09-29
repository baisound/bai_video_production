from __future__ import annotations

import json
from dataclasses import replace
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.audio_workspace_media_review_store import (
    AudioMediaReviewCurrentState,
    AudioMediaReviewHistory,
    AudioMediaReviewHistoryEntry,
    AudioMediaReviewHistoryStore,
    RELATIVE_PATH,
)
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64
NOW = "2026-09-29T00:00:00Z"


def source(**overrides):
    fields = dict(
        source_id="source:audio:1", media_kind="VIDEO_WITH_EMBEDDED_AUDIO",
        contract_state="BOUND_VERIFIED", canonical_ref="asset-revision:1",
        canonical_sha256=H1, canonical_revision=1, candidate_id="candidate:1",
        asset_id="asset:1", rights_state="PASS", sample_rate_hz=48_000,
        channel_count=2, duration_samples=480_000, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    fields.update(overrides)
    return review.AudioMediaSourceBinding.create(**fields)


def capability(**overrides):
    fields = dict(
        capability_id="capability:audio-review:1", contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED", waveform_state="SUPPORTED", decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED", capability_profile_ref="profile:audio-review:1",
        capability_profile_sha256=H2, app_identity_sha256=H3, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    fields.update(overrides)
    return review.PlaybackWaveformCapabilityBinding.create(**fields)


def intent(s, c, *, project_id="project:1", workspace_sha=H4, suffix="1"):
    return review.AudioMediaReviewIntent.create(
        intent_id=f"intent:audio-review:{suffix}", revision=1, parent_record_sha256=None,
        project_id=project_id, policy_sha256=H1,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256,
        audio_workspace_snapshot_sha256=workspace_sha,
        requested_operations=["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=0, range_end_sample=240_000, requested_at=NOW,
        body_included=False, absolute_path_included=False, playback_started=False,
        waveform_render_started=False, media_mutation_started=False,
    )


def receipt(i, s, c):
    return review.ExternalAudioReviewReceiptBinding.create(
        contract_state="BOUND_VERIFIED", receipt_ref="receipt:audio-review:1",
        receipt_sha256=H1, intent_sha256=i.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256, range_start_sample=0,
        range_end_sample=240_000, external_state="COMPLETED",
        audition_completed=True, waveform_available=True, observed_at=NOW,
        canonical_persistence_verified=True, effect_started_by_module=False,
    )


def decision(i, s, r=None, *, revision=1, parent=None, suffix="1"):
    return review.AudioMediaReviewDecision.create(
        decision_id="decision:audio:1", revision=revision, parent_record_sha256=parent,
        intent_sha256=i.record_sha256, source_binding_sha256=s.record_sha256,
        external_review_receipt_sha256=None if r is None else r.record_sha256,
        audio_decision="ACCEPT_AUDIO", visual_decision="PASS",
        derived_proposal_sha256=None, reviewer_kind="OWNER_HUMAN",
        decided_at=NOW, evidence_ref=f"evidence:human:{suffix}", evidence_sha256=H3,
        reason_codes=["AUDIO_ACCEPTED"], asset_mutation_started=False,
        placement_mutation_started=False,
    )


def entry(*, project_id="project:1", workspace_sha=H4, revision=1, parent=None, suffix="1"):
    s, c = source(), capability()
    i = intent(s, c, project_id=project_id, workspace_sha=workspace_sha, suffix=suffix)
    r = receipt(i, s, c)
    d = decision(i, s, r, revision=revision, parent=parent, suffix=suffix)
    return AudioMediaReviewHistoryEntry.create(
        source=s, capability=c, intent=i, receipt=r, decision=d,
    )


def persisted_project(tmp_path: Path):
    history = AudioMediaReviewHistory("project:1")
    first = entry()
    history.append(first)
    result = AudioMediaReviewHistoryStore.save_project(tmp_path, history)
    return history, first, result


def rehash(document: dict) -> None:
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    document["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))


def test_history_round_trip_selects_exact_latest_owner_head() -> None:
    history = AudioMediaReviewHistory("project:1")
    first = entry()
    assert history.append(first) is True
    assert history.append(first) is False
    second = entry(revision=2, parent=first.decision.record_sha256, workspace_sha=H3, suffix="2")
    assert history.append(second) is True
    loaded = AudioMediaReviewHistoryStore.parse_bytes(
        AudioMediaReviewHistoryStore.serialize(history), expected_project_id="project:1"
    )
    assert loaded.store_revision == 2
    assert loaded.current("decision:audio:1") == second


def test_fixed_project_store_save_and_current_read_are_effect_zero(tmp_path: Path) -> None:
    _, first, _ = persisted_project(tmp_path)
    assert (tmp_path / RELATIVE_PATH).is_file()
    result = AudioMediaReviewHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        decision_id="decision:audio:1",
        expected_audio_workspace_snapshot_sha256=H4,
        expected_decision_sha256=first.decision.record_sha256,
    )
    assert result.state is AudioMediaReviewCurrentState.CURRENT
    assert result.entry == first
    assert result.owner_store_read is True
    assert result.owner_origin_authenticated is True
    assert result.currentness_verified is True
    public = result.to_dict()
    assert all(public[key] is False for key in (
        "audio_read_started", "playback_started", "waveform_render_started",
        "media_mutation_started", "external_execution_started",
    ))
    assert "canonical_ref" not in public
    assert "receipt_ref" not in public


def test_current_read_reports_workspace_and_head_drift(tmp_path: Path) -> None:
    _, _, _ = persisted_project(tmp_path)
    result = AudioMediaReviewHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        decision_id="decision:audio:1",
        expected_audio_workspace_snapshot_sha256=H2,
        expected_decision_sha256=H1,
    )
    assert result.state is AudioMediaReviewCurrentState.STALE
    assert result.currentness_verified is False
    assert result.reason_codes == ("AUDIO_WORKSPACE_SNAPSHOT_CHANGED", "DECISION_HEAD_CHANGED")


def test_owner_read_result_rejects_effect_forgery(tmp_path: Path) -> None:
    persisted_project(tmp_path)
    result = AudioMediaReviewHistoryStore.read_current(
        tmp_path,
        project_id="project:1",
        decision_id="decision:audio:1",
        expected_audio_workspace_snapshot_sha256=H4,
    )
    with pytest.raises(ValueError, match="effect authority"):
        replace(result, playback_started=True)


def test_current_read_distinguishes_missing_store_and_missing_decision(tmp_path: Path) -> None:
    missing_store = AudioMediaReviewHistoryStore.read_current(
        tmp_path,
        project_id="project:1", decision_id="decision:audio:1",
        expected_audio_workspace_snapshot_sha256=H4,
    )
    assert missing_store.state is AudioMediaReviewCurrentState.STORE_NOT_FOUND
    assert missing_store.owner_origin_authenticated is False
    history = AudioMediaReviewHistory("project:1")
    AudioMediaReviewHistoryStore.save_project(tmp_path, history)
    missing_decision = AudioMediaReviewHistoryStore.read_current(
        tmp_path,
        project_id="project:1", decision_id="decision:audio:1",
        expected_audio_workspace_snapshot_sha256=H4,
    )
    assert missing_decision.state is AudioMediaReviewCurrentState.NOT_FOUND
    assert missing_decision.owner_origin_authenticated is True
    assert missing_decision.currentness_verified is False


def test_history_rejects_revision_gaps_and_wrong_parent() -> None:
    history = AudioMediaReviewHistory("project:1")
    first = entry()
    history.append(first)
    with pytest.raises(ProductError) as gap:
        history.append(entry(revision=3, parent=first.decision.record_sha256, suffix="3"))
    assert gap.value.code == "ERR_AUDIO_REVIEW_REVISION_CONFLICT"
    with pytest.raises(ProductError) as parent_error:
        history.append(entry(revision=2, parent=H1, suffix="2"))
    assert parent_error.value.code == "ERR_AUDIO_REVIEW_PARENT_CONFLICT"


def test_bundle_rejects_cross_record_mismatch_and_missing_bound_records() -> None:
    s, c = source(), capability()
    i = intent(s, c)
    r = receipt(i, s, c)
    wrong_source = source(source_id="source:audio:2")
    d = decision(i, wrong_source, r)
    with pytest.raises(ValueError, match="source mismatch"):
        AudioMediaReviewHistoryEntry.create(
            source=s, capability=c, intent=i, receipt=r, decision=d,
        )
    valid_decision = decision(i, s, r)
    with pytest.raises(ValueError, match="receipt is missing"):
        AudioMediaReviewHistoryEntry.create(
            source=s, capability=c, intent=i, receipt=None, decision=valid_decision,
        )


def test_derived_decision_requires_exact_proposal_bundle() -> None:
    s, c = source(), capability()
    i = intent(s, c)
    proposal = review.DerivedAudioAssetProposal.create(
        proposal_id="proposal:strip:1", revision=1, parent_record_sha256=None,
        source_binding_sha256=s.record_sha256, review_intent_sha256=i.record_sha256,
        derivation_kind="AUDIO_STRIPPED_VIDEO", proposed_asset_identity="asset-proposal:no-audio:1",
        lineage_sha256=H4, source_bytes_preserved=True, derived_bytes_present=False,
        asset_registration_started=False, media_mutation_started=False,
    )
    d = review.AudioMediaReviewDecision.create(
        decision_id="decision:audio:1", revision=1, parent_record_sha256=None,
        intent_sha256=i.record_sha256, source_binding_sha256=s.record_sha256,
        external_review_receipt_sha256=None, audio_decision="STRIP_AUDIO",
        visual_decision="PASS", derived_proposal_sha256=proposal.record_sha256,
        reviewer_kind="OWNER_HUMAN", decided_at=NOW, evidence_ref="evidence:human:1",
        evidence_sha256=H3, reason_codes=["AUDIO_REJECTED"],
        asset_mutation_started=False, placement_mutation_started=False,
    )
    with pytest.raises(ValueError, match="proposal is missing"):
        AudioMediaReviewHistoryEntry.create(source=s, capability=c, intent=i, decision=d)
    accepted = AudioMediaReviewHistoryEntry.create(
        source=s, capability=c, intent=i, decision=d, proposal=proposal,
    )
    assert accepted.proposal == proposal


def test_snapshot_tamper_unknown_fields_and_authority_are_fail_closed() -> None:
    history = AudioMediaReviewHistory("project:1")
    history.append(entry())
    original = AudioMediaReviewHistoryStore.snapshot(history)
    mutations = (
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"playback_authority": True}),
        lambda value: value["entries"][0]["review_decision"].update({"asset_mutation_started": True}),
        lambda value: value["entries"][0].update({"entry_sha256": H1}),
    )
    for mutate in mutations:
        changed = json.loads(json.dumps(original))
        mutate(changed)
        rehash(changed)
        with pytest.raises(ProductError):
            AudioMediaReviewHistoryStore.parse(changed)

    duplicate = json.loads(json.dumps(original))
    duplicate["entries"].append(json.loads(json.dumps(duplicate["entries"][0])))
    duplicate["store_revision"] = 1
    rehash(duplicate)
    with pytest.raises(ProductError, match="invalid records"):
        AudioMediaReviewHistoryStore.parse(duplicate)


def test_project_mismatch_and_compare_and_swap_are_rejected(tmp_path: Path) -> None:
    history, _, _ = persisted_project(tmp_path)
    previous_snapshot_sha = AudioMediaReviewHistoryStore.snapshot(history)["snapshot_sha256"]
    with pytest.raises(ProductError) as mismatch:
        AudioMediaReviewHistoryStore.load_project(tmp_path, expected_project_id="project:2")
    assert mismatch.value.code == "ERR_AUDIO_REVIEW_PROJECT_MISMATCH"
    with pytest.raises(ProductError) as missing_cas:
        AudioMediaReviewHistoryStore.save_project(tmp_path, history)
    assert missing_cas.value.code == "ERR_AUDIO_REVIEW_CAS_REQUIRED"
    with pytest.raises(ProductError) as stale_cas:
        AudioMediaReviewHistoryStore.save_project(
            tmp_path, history, expected_previous_snapshot_sha256=H1,
        )
    assert stale_cas.value.code == "ERR_AUDIO_REVIEW_REVISION_CONFLICT"
    AudioMediaReviewHistoryStore.save_project(
        tmp_path, history, expected_previous_snapshot_sha256=previous_snapshot_sha,
    )


def test_static_surface_has_no_audio_or_external_effect_primitives() -> None:
    module = Path(__file__).parents[1] / "src/ai_video_production/audio_workspace_media_review_store.py"
    text = module.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "requests", "urllib", "wave.open", "soundfile", "os.system"):
        assert forbidden not in text


def test_schema_is_valid_packaged_and_reuses_exact_media_review_records() -> None:
    root = Path(__file__).parents[1]
    public = root / "schemas/audio-media-review-history.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    media_schema = json.loads(
        (root / "schemas/audio-workspace-media-review.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    resolver = RefResolver.from_schema(
        schema, store={media_schema["$id"]: media_schema}
    )
    history = AudioMediaReviewHistory("project:1")
    history.append(entry())
    Draft202012Validator(schema, resolver=resolver).validate(
        AudioMediaReviewHistoryStore.snapshot(history)
    )
