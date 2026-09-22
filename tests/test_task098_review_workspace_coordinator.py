from __future__ import annotations

from dataclasses import asdict, FrozenInstanceError

import pytest

from ai_video_production import audio_workspace_media_review as review
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.subtitle_workspace import (
    SubtitleOrigin,
    SubtitleWorkspace,
    WorkspaceCue,
)
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task098_review_workspace_coordinator import (
    EFFECT_SURFACE,
    ReviewWorkspaceOpenError,
    ReviewWorkspaceViewModel,
    open_review_workspace,
)


NOW = "2026-09-22T00:00:00Z"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
PRIVATE_TRANSCRIPT_TEXT = "private transcript body must not escape"
PRIVATE_SUBTITLE_TEXT = "private subtitle body must not escape"
ASSET_ID = "ASSET-00000000000000000000000001"
OTHER_ASSET_ID = "ASSET-00000000000000000000000002"


def policy() -> review.AudioMediaReviewPolicyRevision:
    return review.AudioMediaReviewPolicyRevision.create(
        policy_id="policy:task098:a4-r1a",
        revision=1,
        parent_record_sha256=None,
        required_sample_rate_hz=48_000,
        max_review_duration_samples=480_000,
        max_observation_age_seconds=3600,
        official_policy_ref="policy:official:1",
        official_policy_sha256=H1,
        effective_at=NOW,
        expires_at=None,
        audio_read_started=False,
        media_mutation_started=False,
    )


def source(**changes: object) -> review.AudioMediaSourceBinding:
    values = dict(
        source_id="source:task098:a4-r1a",
        media_kind="AUDIO_ASSET",
        contract_state="BOUND_VERIFIED",
        canonical_ref="asset-revision:1",
        canonical_sha256=H1,
        canonical_revision=1,
        candidate_id="candidate:1",
        asset_id=ASSET_ID,
        rights_state="PASS",
        sample_rate_hz=48_000,
        channel_count=2,
        duration_samples=480_000,
        observed_at=NOW,
        body_included=False,
        absolute_path_included=False,
    )
    values.update(changes)
    return review.AudioMediaSourceBinding.create(**values)


def capability() -> review.PlaybackWaveformCapabilityBinding:
    return review.PlaybackWaveformCapabilityBinding.create(
        capability_id="capability:task098:a4-r1a",
        contract_state="BOUND_VERIFIED",
        player_state="SUPPORTED",
        waveform_state="SUPPORTED",
        decode_state="SUPPORTED",
        sample_accurate_range_state="SUPPORTED",
        capability_profile_ref="profile:task098:a4-r1a",
        capability_profile_sha256=H1,
        app_identity_sha256=H2,
        observed_at=NOW,
        body_included=False,
        absolute_path_included=False,
    )


def intent(
    p: review.AudioMediaReviewPolicyRevision,
    s: review.AudioMediaSourceBinding,
    c: review.PlaybackWaveformCapabilityBinding,
) -> review.AudioMediaReviewIntent:
    return review.AudioMediaReviewIntent.create(
        intent_id="intent:task098:a4-r1a",
        revision=1,
        parent_record_sha256=None,
        project_id="project:1",
        policy_sha256=p.record_sha256,
        source_binding_sha256=s.record_sha256,
        capability_binding_sha256=c.record_sha256,
        audio_workspace_snapshot_sha256=H2,
        requested_operations=["AUDITION", "WAVEFORM_VIEW"],
        range_start_sample=48_000,
        range_end_sample=240_000,
        requested_at=NOW,
        body_included=False,
        absolute_path_included=False,
        playback_started=False,
        waveform_render_started=False,
        media_mutation_started=False,
    )


def transcript(*, source_asset_id: str = ASSET_ID, end_us: int = 2_000_000) -> TranscriptManifest:
    return TranscriptManifest(
        source_asset_id=source_asset_id,
        language="ja",
        provider_id="provider.test",
        model_id="model.test",
        segments=(
            TranscriptSegment("segment-1", 1_000_000, end_us, PRIVATE_TRANSCRIPT_TEXT),
        ),
    )


def workspace(*, end_ms: int = 2_000) -> SubtitleWorkspace:
    return SubtitleWorkspace(
        workspace_id="workspace.task098.a4-r1a",
        revision=3,
        cues=(
            WorkspaceCue(
                "cue-1",
                1_000,
                end_ms,
                PRIVATE_SUBTITLE_TEXT,
                PRIVATE_SUBTITLE_TEXT,
                SubtitleOrigin.ASR,
            ),
        ),
    )


def workspace_digest(value: SubtitleWorkspace) -> str:
    return sha256_bytes(canonical_json_bytes(value.to_dict()))


def open_ready(
    *,
    source_value: review.AudioMediaSourceBinding | None = None,
    transcript_value: TranscriptManifest | None = None,
    workspace_value: SubtitleWorkspace | None = None,
    expected_transcript_sha256: str | None = None,
    expected_workspace_snapshot_sha256: str | None = None,
    evaluated_at: str = NOW,
    visible_segment_count: int = 20,
) -> ReviewWorkspaceViewModel:
    p = policy()
    s = source_value or source()
    c = capability()
    i = intent(p, s, c)
    t = transcript_value or transcript()
    w = workspace_value or workspace()
    return open_review_workspace(
        policy=p,
        source=s,
        capability=c,
        intent=i,
        transcript=t,
        expected_transcript_sha256=(
            expected_transcript_sha256 or t.to_dict()["manifest_sha256"]
        ),
        workspace=w,
        expected_workspace_snapshot_sha256=(
            expected_workspace_snapshot_sha256 or workspace_digest(w)
        ),
        evaluated_at=evaluated_at,
        visible_segment_count=visible_segment_count,
    )


def test_ready_inputs_open_immutable_body_free_exact_hash_view_model() -> None:
    result = open_ready()
    assert result.transcript_manifest_sha256 == transcript().to_dict()["manifest_sha256"]
    assert result.workspace_revision == 3
    assert result.workspace_transcript_lineage_confirmed is False
    assert result.viewport.waveform_start_sample == 48_000
    assert result.viewport.waveform_span_samples == 192_000
    assert (result.transcript_rows[0].projected_range.sample_start,
            result.transcript_rows[0].projected_range.sample_end_exclusive) == (48_000, 96_000)
    assert (result.subtitle_rows[0].projected_range.sample_start,
            result.subtitle_rows[0].projected_range.sample_end_exclusive) == (48_000, 96_000)
    with pytest.raises(FrozenInstanceError):
        result.workspace_revision = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"expected_transcript_sha256": H1}, "TRANSCRIPT_DIGEST_MISMATCH"),
        ({"expected_workspace_snapshot_sha256": H1}, "WORKSPACE_SNAPSHOT_DIGEST_MISMATCH"),
        ({"expected_transcript_sha256": "not-a-digest"}, "IDENTITY_FORMAT_INVALID"),
        ({"transcript_value": transcript(source_asset_id=OTHER_ASSET_ID)}, "SOURCE_ASSET_MISMATCH"),
        ({"evaluated_at": "2026-09-22T02:00:00Z"}, "ADMISSION_NOT_READY"),
    ],
)
def test_identity_asset_and_admission_failures_use_closed_body_free_codes(
    kwargs: dict[str, object], code: str
) -> None:
    with pytest.raises(ReviewWorkspaceOpenError) as caught:
        open_ready(**kwargs)  # type: ignore[arg-type]
    assert caught.value.code == code
    assert caught.value.reason_codes == (code,)
    assert PRIVATE_TRANSCRIPT_TEXT not in str(caught.value)
    assert PRIVATE_SUBTITLE_TEXT not in str(caught.value)


@pytest.mark.parametrize(
    "source_value",
    [
        source(sample_rate_hz=44_100),
        source(rights_state="BLOCKED"),
        source(contract_state="UNKNOWN"),
    ],
)
def test_non_ready_source_contract_fails_closed(
    source_value: review.AudioMediaSourceBinding,
) -> None:
    with pytest.raises(ReviewWorkspaceOpenError) as caught:
        open_ready(source_value=source_value)
    assert caught.value.code == "ADMISSION_NOT_READY"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"transcript_value": transcript(end_us=11_000_000)},
        {"workspace_value": workspace(end_ms=11_000)},
    ],
)
def test_projected_rows_must_fit_source_duration(kwargs: dict[str, object]) -> None:
    with pytest.raises(ReviewWorkspaceOpenError) as caught:
        open_ready(**kwargs)  # type: ignore[arg-type]
    assert caught.value.code == "TIMING_OUTSIDE_SOURCE"


def test_row_limit_is_checked_before_body_free_materialization(monkeypatch: pytest.MonkeyPatch) -> None:
    import ai_video_production.task098_review_workspace_coordinator as coordinator

    monkeypatch.setattr(coordinator, "MAX_SEGMENT_COUNT", 0)
    with pytest.raises(ReviewWorkspaceOpenError) as caught:
        open_ready()
    assert caught.value.code == "ROW_LIMIT_EXCEEDED"


def test_view_model_does_not_retain_text_path_body_or_canonical_objects() -> None:
    result = open_ready()
    materialized = asdict(result)
    serialized = repr(materialized)
    forbidden_field_fragments = ("text", "raw_text", "path", "media", "receipt", "store", "service")
    assert PRIVATE_TRANSCRIPT_TEXT not in serialized
    assert PRIVATE_SUBTITLE_TEXT not in serialized
    assert not any(
        fragment in key.lower()
        for key in materialized
        for fragment in forbidden_field_fragments
    )
    assert not hasattr(result, "to_dict")
    assert set(EFFECT_SURFACE.values()) == {False}


def test_coordinator_preserves_independent_waveform_and_segment_scrolling() -> None:
    result = open_ready(visible_segment_count=1)
    waveform = result.scroll_waveform(999_999)
    assert waveform.viewport.waveform_start_sample == 288_000
    assert waveform.viewport.segment_scroll_index == 0
    segments = waveform.scroll_segments(999_999)
    assert segments.viewport.segment_scroll_index == 0
    assert segments.viewport.waveform_start_sample == 288_000


def test_lineage_claim_cannot_be_forged() -> None:
    result = open_ready()
    values = {field: value for field, value in asdict(result).items()}
    values["workspace_transcript_lineage_confirmed"] = True
    with pytest.raises((TypeError, ValueError), match="lineage"):
        ReviewWorkspaceViewModel(**values)  # type: ignore[arg-type]


def test_body_rows_and_viewport_count_cannot_be_forged_directly() -> None:
    result = open_ready()
    values = {
        field: getattr(result, field)
        for field in result.__dataclass_fields__
    }
    values["transcript_rows"] = ({"text": PRIVATE_TRANSCRIPT_TEXT},)
    with pytest.raises(ValueError, match="body-free"):
        ReviewWorkspaceViewModel(**values)  # type: ignore[arg-type]

    values["transcript_rows"] = result.transcript_rows
    values["viewport"] = result.viewport.__class__(
        source_duration_samples=result.viewport.source_duration_samples,
        waveform_start_sample=result.viewport.waveform_start_sample,
        waveform_span_samples=result.viewport.waveform_span_samples,
        segment_count=2,
        segment_scroll_index=0,
        visible_segment_count=20,
    )
    with pytest.raises(ValueError, match="segment_count"):
        ReviewWorkspaceViewModel(**values)  # type: ignore[arg-type]
