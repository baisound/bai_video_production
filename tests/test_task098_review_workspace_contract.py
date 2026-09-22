from __future__ import annotations

from dataclasses import asdict

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.task098_review_workspace_contract import (
    EFFECT_SURFACE,
    ProjectedHalfOpenRange,
    ReviewCompletionClassification,
    ReviewCompletionResult,
    ReviewViewport,
    TimingUnit,
    classify_review_completion,
    project_microseconds_to_samples,
    project_milliseconds_to_samples,
)


NOW = "2026-09-22T00:00:00Z"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64


def policy() -> review.AudioMediaReviewPolicyRevision:
    return review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a4", revision=1, parent_record_sha256=None,
        required_sample_rate_hz=48_000, max_review_duration_samples=480_000,
        max_observation_age_seconds=3600, official_policy_ref="policy:official:1",
        official_policy_sha256=H1, effective_at=NOW, expires_at=None,
        audio_read_started=False, media_mutation_started=False,
    )


def source(**changes: object) -> review.AudioMediaSourceBinding:
    values = dict(
        source_id="source:task098:a4", media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED", canonical_ref="asset-revision:1",
        canonical_sha256=H1, canonical_revision=1, candidate_id="candidate:1",
        asset_id="asset:1", rights_state="PASS", sample_rate_hz=48_000,
        channel_count=2, duration_samples=480_000, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    values.update(changes)
    return review.AudioMediaSourceBinding.create(**values)


def capability(**changes: object) -> review.PlaybackWaveformCapabilityBinding:
    values = dict(
        capability_id="capability:task098:a4", contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED", waveform_state="SUPPORTED",
        decode_state="SUPPORTED", sample_accurate_range_state="SUPPORTED",
        capability_profile_ref="profile:task098:a4",
        capability_profile_sha256=H1, app_identity_sha256=H2, observed_at=NOW,
        body_included=False, absolute_path_included=False,
    )
    values.update(changes)
    return review.PlaybackWaveformCapabilityBinding.create(**values)


def intent(
    p: review.AudioMediaReviewPolicyRevision,
    s: review.AudioMediaSourceBinding,
    c: review.PlaybackWaveformCapabilityBinding,
    *,
    requested_operations: list[str] | None = None,
) -> review.AudioMediaReviewIntent:
    return review.AudioMediaReviewIntent.create(
        intent_id="intent:task098:a4", revision=1, parent_record_sha256=None,
        project_id="project:1", policy_sha256=p.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=requested_operations or ["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=0, range_end_sample=240_000, requested_at=NOW,
        body_included=False, absolute_path_included=False,
        playback_started=False, waveform_render_started=False,
        media_mutation_started=False,
    )


def receipt(
    i: review.AudioMediaReviewIntent,
    s: review.AudioMediaSourceBinding,
    c: review.PlaybackWaveformCapabilityBinding,
    **changes: object,
) -> review.ExternalAudioReviewReceiptBinding:
    values = dict(
        contract_state="BOUND_VERIFIED", receipt_ref="receipt:task098:a4",
        receipt_sha256=H1, intent_sha256=i.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256,
        range_start_sample=0, range_end_sample=240_000,
        external_state="COMPLETED", audition_completed=True,
        waveform_available=True, observed_at=NOW,
        canonical_persistence_verified=True, effect_started_by_module=False,
    )
    values.update(changes)
    return review.ExternalAudioReviewReceiptBinding.create(**values)


def test_exact_inclusion_and_all_completion_conditions_are_required() -> None:
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    result = classify_review_completion(receipt=receipt(i, s, c), intent=i, source=s, capability=c)
    assert result.classification is ReviewCompletionClassification.COMPLETE
    assert result.reason_codes == ()
    assert all(value is False for key, value in result.to_dict().items() if key.endswith(("_started", "_authorized")))


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"external_state": "FAILED"}, "EXTERNAL_REVIEW_NOT_COMPLETED"),
        ({"external_state": "CANCELLED_SAFE"}, "EXTERNAL_REVIEW_NOT_COMPLETED"),
        ({"external_state": "UNKNOWN"}, "EXTERNAL_REVIEW_NOT_COMPLETED"),
        ({"external_state": "UNKNOWN", "canonical_persistence_verified": False},
         "CANONICAL_PERSISTENCE_NOT_VERIFIED"),
        ({"external_state": "UNKNOWN", "audition_completed": False},
         "AUDITION_NOT_COMPLETED"),
        ({"external_state": "UNKNOWN", "waveform_available": False},
         "WAVEFORM_NOT_AVAILABLE"),
    ],
)
def test_exact_inclusion_is_not_completion(changes: dict[str, object], reason: str) -> None:
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    result = classify_review_completion(
        receipt=receipt(i, s, c, **changes), intent=i, source=s, capability=c
    )
    assert result.classification is ReviewCompletionClassification.INCOMPLETE
    assert reason in result.reason_codes


def test_requested_operation_implications_are_exact() -> None:
    p, s, c = policy(), source(), capability()
    audition_only = intent(p, s, c, requested_operations=["AUDITION"])
    result = classify_review_completion(
        receipt=receipt(audition_only, s, c, waveform_available=False),
        intent=audition_only,
        source=s,
        capability=c,
    )
    assert result.classification is ReviewCompletionClassification.COMPLETE
    assert "WAVEFORM_NOT_AVAILABLE" not in result.reason_codes


def test_inclusion_mismatch_stays_visible_and_fails_closed() -> None:
    p, s, c = policy(), source(), capability()
    i = intent(p, s, c)
    other_source = source(source_id="source:other", canonical_ref="asset-revision:2")
    result = classify_review_completion(
        receipt=receipt(i, s, c), intent=i, source=other_source, capability=c
    )
    assert result.classification is ReviewCompletionClassification.INCOMPLETE
    assert result.reason_codes == ("INCLUSION_NOT_PROVEN", "SOURCE_MISMATCH")


def test_completion_result_cannot_be_forged_directly() -> None:
    with pytest.raises(ValueError, match="reasons disagree"):
        ReviewCompletionResult(
            ReviewCompletionClassification.COMPLETE,
            ("AUDITION_NOT_COMPLETED",), H1, H2,
        )
    with pytest.raises(ValueError, match="effects or Human authority"):
        ReviewCompletionResult(
            ReviewCompletionClassification.COMPLETE, (), H1, H2,
            playback_started=True,
        )
    with pytest.raises(ValueError, match="closed, unique, and ordered"):
        ReviewCompletionResult(
            ReviewCompletionClassification.INCOMPLETE, ("PRIVATE_PATH",), H1, H2,
        )


def test_microsecond_projection_covers_half_open_boundaries_without_float() -> None:
    one_us = project_microseconds_to_samples(0, 1)
    assert one_us.source_unit is TimingUnit.MICROSECONDS
    assert (one_us.sample_start, one_us.sample_end_exclusive) == (0, 1)
    exact = project_microseconds_to_samples(1_000_000, 2_000_000)
    assert (exact.sample_start, exact.sample_end_exclusive) == (48_000, 96_000)
    fractional = project_microseconds_to_samples(1, 1_001)
    assert (fractional.sample_start, fractional.sample_end_exclusive) == (0, 49)


def test_millisecond_projection_is_exact_at_48khz() -> None:
    projected = project_milliseconds_to_samples(1, 1_001)
    assert projected.source_unit is TimingUnit.MILLISECONDS
    assert (projected.sample_start, projected.sample_end_exclusive) == (48, 48_048)


def test_projected_range_cannot_be_forged_directly() -> None:
    with pytest.raises(ValueError, match="does not match"):
        ProjectedHalfOpenRange(TimingUnit.MICROSECONDS, 0, 1, 48_000, 0, 2)
    with pytest.raises(ValueError, match="48000"):
        ProjectedHalfOpenRange(TimingUnit.MILLISECONDS, 0, 1, 44_100, 0, 48)


@pytest.mark.parametrize(
    "args",
    [(True, 1), (0, False), (-1, 1), (2, 1), (0, 86_400_000_001)],
)
def test_projection_rejects_boolean_invalid_and_unbounded_values(args: tuple[object, object]) -> None:
    with pytest.raises(ValueError):
        project_microseconds_to_samples(args[0], args[1])  # type: ignore[arg-type]


def test_waveform_and_segment_scroll_axes_are_independent_and_clamped() -> None:
    initial = ReviewViewport(
        source_duration_samples=48_000,
        waveform_start_sample=0,
        waveform_span_samples=12_000,
        segment_count=100,
        segment_scroll_index=0,
        visible_segment_count=10,
    )
    waveform = initial.scroll_waveform(100_000)
    assert waveform.waveform_start_sample == 36_000
    assert waveform.segment_scroll_index == initial.segment_scroll_index
    segments = waveform.scroll_segments(1_000)
    assert segments.segment_scroll_index == 90
    assert segments.waveform_start_sample == waveform.waveform_start_sample
    assert segments.scroll_waveform(-100_000).waveform_start_sample == 0
    assert segments.scroll_segments(-1_000).segment_scroll_index == 0


def test_viewport_rejects_boolean_and_out_of_range_state_or_delta() -> None:
    with pytest.raises(ValueError):
        ReviewViewport(True, 0, 1, 0, 0, 1)  # type: ignore[arg-type]
    viewport = ReviewViewport(100, 0, 10, 1, 0, 1)
    with pytest.raises(ValueError):
        viewport.scroll_waveform(True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        viewport.scroll_segments(1_000_001)


def test_contract_surface_is_body_path_and_effect_free() -> None:
    assert set(EFFECT_SURFACE.values()) == {False}
    assert not ({"text", "audio", "media_bytes", "path", "receipt_body"} & set(EFFECT_SURFACE))
    viewport = ReviewViewport(100, 0, 10, 0, 0, 1)
    assert not ({"text", "path", "body"} & set(asdict(viewport)))
