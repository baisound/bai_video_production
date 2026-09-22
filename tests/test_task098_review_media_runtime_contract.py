from __future__ import annotations

from dataclasses import replace
from typing import get_type_hints

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.task098_review_media_runtime_contract import (
    EFFECT_SURFACE,
    MAX_WAVEFORM_POINT_COUNT,
    ReviewMediaRuntimeObservation,
    ReviewMediaRuntimePort,
    ReviewMediaRuntimeRequest,
    ReviewMediaRuntimeState,
    build_review_media_runtime_request,
    reduce_review_media_runtime,
)
from ai_video_production.task098_review_workspace_contract import ReviewViewport
from ai_video_production.task098_review_workspace_coordinator import ReviewWorkspaceViewModel


NOW = "2026-09-22T00:00:00Z"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
ASSET_ID = "ASSET-00000000000000000000000001"


def policy() -> review.AudioMediaReviewPolicyRevision:
    return review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a4-r2a", revision=1, parent_record_sha256=None,
        required_sample_rate_hz=48_000, max_review_duration_samples=480_000,
        max_observation_age_seconds=3600, official_policy_ref="policy:official:1",
        official_policy_sha256=H1, effective_at=NOW, expires_at=None,
        audio_read_started=False, media_mutation_started=False,
    )


def source(**changes: object) -> review.AudioMediaSourceBinding:
    values = dict(
        source_id="source:task098:a4-r2a", media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED", canonical_ref="asset-revision:1",
        canonical_sha256=H1, canonical_revision=1, candidate_id="candidate:1",
        asset_id=ASSET_ID, rights_state="PASS", sample_rate_hz=48_000,
        channel_count=2, duration_samples=480_000, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    values.update(changes)
    return review.AudioMediaSourceBinding.create(**values)


def capability(**changes: object) -> review.PlaybackWaveformCapabilityBinding:
    values = dict(
        capability_id="capability:task098:a4-r2a", contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED", waveform_state="SUPPORTED", decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED", capability_profile_ref="profile:a4-r2a",
        capability_profile_sha256=H1, app_identity_sha256=H2, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    values.update(changes)
    return review.PlaybackWaveformCapabilityBinding.create(**values)


def intent(
    p: review.AudioMediaReviewPolicyRevision,
    s: review.AudioMediaSourceBinding,
    c: review.PlaybackWaveformCapabilityBinding,
    operations: list[str] | None = None,
) -> review.AudioMediaReviewIntent:
    return review.AudioMediaReviewIntent.create(
        intent_id="intent:task098:a4-r2a", revision=1, parent_record_sha256=None,
        project_id="project:1", policy_sha256=p.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=operations or ["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=48_000, range_end_sample=240_000, requested_at=NOW,
        body_included=False, absolute_path_included=False,
        playback_started=False, waveform_render_started=False, media_mutation_started=False,
    )


def view(s: review.AudioMediaSourceBinding, i: review.AudioMediaReviewIntent) -> ReviewWorkspaceViewModel:
    return ReviewWorkspaceViewModel(
        source_binding_sha256=s.record_sha256, source_asset_id=ASSET_ID,
        source_candidate_id="candidate:1", intent_sha256=i.record_sha256,
        intent_id="intent:task098:a4-r2a", transcript_manifest_sha256=H1,
        workspace_id="workspace.a4-r2a", workspace_revision=1,
        workspace_snapshot_sha256=H2, transcript_rows=(), subtitle_rows=(),
        viewport=ReviewViewport(480_000, 48_000, 192_000, 0, 0, 1),
    )


def request(operations: list[str] | None = None) -> ReviewMediaRuntimeRequest:
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c, operations)
    return build_review_media_runtime_request(
        policy=p, source=s, capability=c, intent=i, view_model=view(s, i),
        evaluated_at=NOW,
    )


def observation(
    req: ReviewMediaRuntimeRequest,
    state: ReviewMediaRuntimeState,
    *, playback: bool = False,
    waveform: bool = False,
    points: int | None = None,
    reasons: tuple[str, ...] = (),
    connected: bool = True,
) -> ReviewMediaRuntimeObservation:
    return ReviewMediaRuntimeObservation(
        req.request_sha256, state, connected, playback, waveform, points, reasons
    )


def test_request_is_exact_hashed_path_free_and_matches_workspace_range() -> None:
    req = request()
    assert req.requested_operations == ("AUDITION", "WAVEFORM_VIEW")
    assert (req.range_start_sample, req.range_end_sample_exclusive) == (48_000, 240_000)
    assert req.sample_rate_hz == 48_000
    assert not any("path" in name for name in req.__dataclass_fields__)
    assert all(EFFECT_SURFACE.values()) is False


def test_request_rejects_exact_identity_capability_and_range_drift() -> None:
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    with pytest.raises(ValueError, match="identity"):
        build_review_media_runtime_request(
            policy=p, source=s, capability=c, intent=i,
            view_model=replace(view(s, i), source_binding_sha256=H1),
            evaluated_at=NOW,
        )
    limited = capability(waveform_state="LIMITED")
    limited_intent = intent(p, s, limited)
    with pytest.raises(ValueError, match="identity"):
        build_review_media_runtime_request(
            policy=p, source=s, capability=limited, intent=limited_intent,
            view_model=view(s, limited_intent),
            evaluated_at=NOW,
        )
    with pytest.raises(ValueError, match="identity"):
        build_review_media_runtime_request(
            policy=p, source=s, capability=c, intent=i,
            view_model=replace(view(s, i), viewport=ReviewViewport(480_000, 0, 192_000, 0, 0, 1)),
            evaluated_at=NOW,
        )
    with pytest.raises(ValueError, match="identity"):
        build_review_media_runtime_request(
            policy=p, source=s, capability=c, intent=i, view_model=view(s, i),
            evaluated_at="2026-09-22T02:00:00Z",
        )


def test_request_constructor_rejects_hash_range_operation_and_rate_forgery() -> None:
    req = request()
    with pytest.raises(ValueError, match="does not match"):
        replace(req, request_sha256=H1)
    with pytest.raises(ValueError, match="operations"):
        replace(req, requested_operations=("WAVEFORM_VIEW", "AUDITION"))
    with pytest.raises(ValueError, match="48000"):
        replace(req, sample_rate_hz=44_100)
    with pytest.raises(ValueError, match="range"):
        replace(req, range_end_sample_exclusive=req.range_start_sample)
    with pytest.raises(ValueError, match="ASSET"):
        replace(req, source_asset_id="not-an-asset")


def test_no_observation_is_not_bound_and_public_projection_is_body_free() -> None:
    req = request()
    status = reduce_review_media_runtime(req)
    assert status.state is ReviewMediaRuntimeState.NOT_BOUND
    assert status.reason_codes == ("PORT_NOT_BOUND",)
    body = status.to_public_dict()
    assert body["canonical_receipt_created"] is False
    assert body["review_completion_claimed"] is False
    serialized = repr(body).lower()
    for forbidden in ("path", "sha256", ASSET_ID.lower(), req.request_sha256):
        assert forbidden not in serialized


def test_ready_and_running_observations_do_not_claim_completion() -> None:
    req = request()
    ready = reduce_review_media_runtime(req, observation(req, ReviewMediaRuntimeState.READY))
    running = reduce_review_media_runtime(
        req, observation(req, ReviewMediaRuntimeState.RUNNING, playback=True)
    )
    assert ready.state is ReviewMediaRuntimeState.READY
    assert running.state is ReviewMediaRuntimeState.RUNNING
    assert running.playback_observed is True
    assert running.to_public_dict()["review_completion_claimed"] is False


def test_success_requires_every_requested_explicit_observation() -> None:
    req = request()
    succeeded = reduce_review_media_runtime(
        req,
        observation(
            req, ReviewMediaRuntimeState.SUCCEEDED,
            playback=True, waveform=True, points=4096,
        ),
    )
    assert succeeded.state is ReviewMediaRuntimeState.SUCCEEDED
    assert succeeded.waveform_point_count == 4096
    assert succeeded.to_public_dict()["canonical_receipt_created"] is False

    missing = reduce_review_media_runtime(
        req, observation(req, ReviewMediaRuntimeState.SUCCEEDED, playback=True)
    )
    assert missing.state is ReviewMediaRuntimeState.FAILED_KNOWN
    assert missing.reason_codes == ("WAVEFORM_NOT_OBSERVED",)


def test_request_identity_mismatch_and_unrequested_effects_fail_closed() -> None:
    req = request(["AUDITION"])
    other = request(["WAVEFORM_VIEW"])
    mismatch = reduce_review_media_runtime(
        req, observation(other, ReviewMediaRuntimeState.SUCCEEDED, waveform=True, points=10)
    )
    assert mismatch.reason_codes == ("REQUEST_IDENTITY_MISMATCH",)
    extra = reduce_review_media_runtime(
        req,
        observation(
            req, ReviewMediaRuntimeState.SUCCEEDED,
            playback=True, waveform=True, points=10,
        ),
    )
    assert extra.reason_codes == ("UNREQUESTED_WAVEFORM_OBSERVED",)
    assert extra.waveform_point_count is None


@pytest.mark.parametrize(
    ("state", "connected", "reasons"),
    [
        (ReviewMediaRuntimeState.FAILED_KNOWN, True, ("RUNTIME_FAILED",)),
        (ReviewMediaRuntimeState.CANCELLED_SAFE, True, ("CANCELLED_BY_RUNTIME",)),
        (ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT, False, ("RUNTIME_DISCONNECTED",)),
    ],
)
def test_terminal_non_success_states_never_claim_completion(
    state: ReviewMediaRuntimeState, connected: bool, reasons: tuple[str, ...]
) -> None:
    req = request()
    status = reduce_review_media_runtime(
        req, observation(req, state, reasons=reasons, connected=connected)
    )
    assert status.state is state
    assert status.playback_observed is False
    assert status.waveform_observed is False
    assert status.to_public_dict()["review_completion_claimed"] is False


def test_observation_constructor_rejects_partial_or_forged_state() -> None:
    req = request()
    with pytest.raises(ValueError, match="waveform metadata"):
        observation(req, ReviewMediaRuntimeState.RUNNING, points=1)
    with pytest.raises(ValueError, match="supported range"):
        observation(
            req, ReviewMediaRuntimeState.RUNNING,
            waveform=True, points=MAX_WAVEFORM_POINT_COUNT + 1,
        )
    with pytest.raises(ValueError, match="FAILED_KNOWN"):
        observation(
            req, ReviewMediaRuntimeState.FAILED_KNOWN,
            playback=True, reasons=("RUNTIME_FAILED",),
        )
    with pytest.raises(ValueError, match="UNKNOWN_AFTER_DISCONNECT"):
        observation(
            req, ReviewMediaRuntimeState.UNKNOWN_AFTER_DISCONNECT,
            connected=True, reasons=("RUNTIME_DISCONNECTED",),
        )
    with pytest.raises(ValueError, match="coordinator-only"):
        observation(req, ReviewMediaRuntimeState.NOT_BOUND)


def test_status_constructor_rejects_forged_success_and_effect_state() -> None:
    from ai_video_production.task098_review_media_runtime_contract import ReviewMediaRuntimeStatus

    with pytest.raises(ValueError, match="SUCCEEDED"):
        ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.SUCCEEDED, True, True, False, False, None, ()
        )
    with pytest.raises(ValueError, match="READY"):
        ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.READY, True, False, True, False, None, ()
        )
    with pytest.raises(ValueError, match="FAILED_KNOWN"):
        ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.FAILED_KNOWN,
            True, True, False, False, None, ("PORT_NOT_BOUND",),
        )
    with pytest.raises(ValueError, match="CANCELLED_SAFE"):
        ReviewMediaRuntimeStatus(
            ReviewMediaRuntimeState.CANCELLED_SAFE,
            True, True, False, False, None, ("RUNTIME_FAILED",),
        )


def test_port_is_protocol_only_and_contract_has_no_effect_method() -> None:
    hints = get_type_hints(ReviewMediaRuntimePort.execute)
    assert hints["request"] is ReviewMediaRuntimeRequest
    assert set(EFFECT_SURFACE.values()) == {False}
    assert not hasattr(ReviewMediaRuntimeRequest, "execute")
    assert not hasattr(ReviewMediaRuntimeRequest, "open")
