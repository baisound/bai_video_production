from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.assets import AssetRecord, AssetType, RightsStatus
from ai_video_production.canonical_game_event import GameEnvironment, GamePerspective
from ai_video_production.errors import ProductError
from ai_video_production.game_intelligence_adapters import (
    GameIntelligenceNormalizationAdapter,
    TranscriptClockDomain,
    TranscriptEvidenceAdapter,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.normalization import NormalizationResult
from ai_video_production.store import OperationRecord
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.timebase import FrameRate, TimingInspection, TimingKind


SHA = "sha256:" + "a" * 64


def asset(
    job_id: str,
    asset_type: AssetType,
    name: str,
    *,
    source_ref: str | None = None,
    duration_us: int = 10_000_000,
    frame_rate: str | None = None,
) -> AssetRecord:
    streams: list[dict[str, object]] = []
    if asset_type in {AssetType.VIDEO, AssetType.GENERATED_VIDEO}:
        stream: dict[str, object] = {"codec_type": "video"}
        if frame_rate is not None:
            stream["avg_frame_rate"] = frame_rate
        streams.append(stream)
    else:
        streams.append({"codec_type": "audio", "sample_rate": 48_000})
    return AssetRecord(
        production_job_id=job_id,
        asset_type=asset_type,
        logical_uri=f"asset://{job_id}/{name}",
        checksum=SHA,
        rights_status=RightsStatus.OWNED,
        owner="USER",
        source_ref=source_ref,
        media_metadata={"duration_us": duration_us, "streams": streams},
    )


def op(job_id: str) -> OperationRecord:
    return OperationRecord(
        operation_id=generate_id(IdKind.OPERATION),
        job_id=job_id,
        command_type="MEDIA_NORMALIZE",
        idempotency_key="task049-r3",
        status="COMPLETED",
        attempt=1,
        created_at="2026-08-18T00:00:00.000Z",
    )


def timing(kind: TimingKind, rate: FrameRate | None, duration_us: int = 10_000_000) -> TimingInspection:
    return TimingInspection(
        kind,
        duration_us,
        rate,
        rate,
        "1/90000",
        100,
        99,
        0 if kind is TimingKind.CFR else 5,
        33366,
        33367,
        "fixture",
    )


def cfr_result() -> NormalizationResult:
    job = generate_id(IdKind.JOB)
    source = asset(job, AssetType.VIDEO, "source.mp4", frame_rate="24/1")
    return NormalizationResult(
        op(job),
        source,
        timing(TimingKind.CFR, FrameRate(24, 1)),
        source,
        None,
        None,
        "job://manifest/normalization.json",
        "job://evidence/normalization.json",
    )


def vfr_proxy_result() -> NormalizationResult:
    job = generate_id(IdKind.JOB)
    source = asset(job, AssetType.VIDEO, "source-vfr.mp4", duration_us=10_000_000, frame_rate="30000/1001")
    proxy = asset(
        job,
        AssetType.VIDEO,
        "cfr-proxy.mp4",
        source_ref=source.asset_id,
        duration_us=10_010_000,
        frame_rate="30000/1001",
    )
    audio = asset(
        job,
        AssetType.AUDIO,
        "analysis.wav",
        source_ref=source.asset_id,
        duration_us=10_000_000,
    )
    return NormalizationResult(
        op(job),
        source,
        timing(TimingKind.VFR, FrameRate(30000, 1001)),
        proxy,
        proxy,
        audio,
        "job://manifest/normalization.json",
        "job://evidence/normalization.json",
    )


def test_cfr_source_is_reused_without_duplicate_asset_or_affine_map() -> None:
    result = cfr_result()
    binding = GameIntelligenceNormalizationAdapter.bind(result)
    assert binding.original_source_asset is result.source_asset
    assert binding.analysis_video_asset is result.source_asset
    assert binding.analysis_rate == FrameRate(24, 1)
    assert binding.upstream_to_analysis_map is None
    game_match = binding.create_match(
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
    )
    assert game_match.source_asset_id == result.source_asset.asset_id
    assert binding.analysis_clock_range(1_000_000, 2_000_000).to_dict() == {
        "start_frame": 24,
        "end_frame_exclusive": 48,
    }


def test_vfr_source_uses_existing_task004_cfr_proxy_as_cgel_clock_anchor() -> None:
    result = vfr_proxy_result()
    binding = GameIntelligenceNormalizationAdapter.bind(result)
    assert binding.analysis_video_asset.asset_id == result.proxy_asset.asset_id  # type: ignore[union-attr]
    assert binding.original_source_asset.asset_id == result.source_asset.asset_id
    assert binding.analysis_rate == FrameRate(30000, 1001)
    assert binding.upstream_to_analysis_map is not None
    assert binding.upstream_source_clock_range(5_000_000, 6_000_000).to_dict() == {
        "start_frame": 150,
        "end_frame_exclusive": 180,
    }


def test_vfr_without_normalized_proxy_fails_closed() -> None:
    result = cfr_result()
    broken = replace(result, timing=timing(TimingKind.VFR, FrameRate(24, 1)))
    with pytest.raises(ProductError) as caught:
        GameIntelligenceNormalizationAdapter.bind(broken)
    assert caught.value.code == "ERR_GAME_TIMEBASE_VFR_REQUIRES_NORMALIZED_CFR"


def test_proxy_without_exact_rate_fails_closed() -> None:
    result = vfr_proxy_result()
    assert result.proxy_asset is not None
    broken_proxy = replace(result.proxy_asset, media_metadata={"duration_us": 10_010_000, "streams": [{"codec_type": "video"}]})
    broken = replace(result, proxy_asset=broken_proxy, video_reference_asset=broken_proxy)
    with pytest.raises(ProductError) as caught:
        GameIntelligenceNormalizationAdapter.bind(broken)
    assert caught.value.code == "ERR_GAME_ANALYSIS_PROXY_RATE_MISSING"


def test_existing_transcript_is_projected_to_text_free_asr_game_evidence() -> None:
    result = vfr_proxy_result()
    binding = GameIntelligenceNormalizationAdapter.bind(result)
    game_match = binding.create_match(
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
    )
    assert result.analysis_audio_asset is not None
    transcript = TranscriptManifest(
        result.analysis_audio_asset.asset_id,
        "ja",
        "faster-whisper",
        "small",
        (
            TranscriptSegment("seg-000001", 5_000_000, 6_000_000, "窓を越えた", 0.913),
            TranscriptSegment("seg-000002", 6_000_000, 7_000_000, "次の発話", None),
        ),
    )
    rows = TranscriptEvidenceAdapter.compile(
        match=game_match,
        media_binding=binding,
        transcript=transcript,
        transcript_asset=result.analysis_audio_asset,
        clock_domain=TranscriptClockDomain.UPSTREAM_SOURCE_CLOCK,
        producer_version="1.0.0",
        artifact_ref="asset://transcript/transcript.json",
    )
    assert len(rows) == 2
    assert rows[0].source_asset_id == game_match.source_asset_id
    assert rows[0].source_range.to_dict() == {"start_frame": 150, "end_frame_exclusive": 180}
    assert rows[0].confidence_milli == 913
    assert rows[1].confidence_milli == 0
    serialized = rows[0].to_dict()
    assert serialized["artifact_ref"].endswith("#seg-000001")
    assert "窓を越えた" not in str(serialized)
    assert serialized["evidence_type"] == "ASR"


def test_transcript_clock_domain_must_be_explicit_and_lineage_must_match() -> None:
    result = vfr_proxy_result()
    binding = GameIntelligenceNormalizationAdapter.bind(result)
    game_match = binding.create_match(
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
    )
    unrelated = asset(game_match.production_job_id, AssetType.AUDIO, "other.wav")
    transcript = TranscriptManifest(
        unrelated.asset_id,
        "ja",
        "faster-whisper",
        "small",
        (TranscriptSegment("seg-000001", 0, 1_000_000, "x", 1.0),),
    )
    with pytest.raises(ProductError) as caught:
        TranscriptEvidenceAdapter.compile(
            match=game_match,
            media_binding=binding,
            transcript=transcript,
            transcript_asset=unrelated,
            clock_domain=TranscriptClockDomain.UPSTREAM_SOURCE_CLOCK,
            producer_version="1.0.0",
            artifact_ref="asset://transcript/transcript.json",
        )
    assert caught.value.code == "ERR_GAME_TRANSCRIPT_LINEAGE_MISMATCH"


def test_match_clock_transcript_mapping_uses_exact_ntsc_rational() -> None:
    result = vfr_proxy_result()
    binding = GameIntelligenceNormalizationAdapter.bind(result)
    game_match = binding.create_match(
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
    )
    assert result.proxy_asset is not None
    transcript = TranscriptManifest(
        result.proxy_asset.asset_id,
        "ja",
        "faster-whisper",
        "small",
        (TranscriptSegment("seg-000001", 0, 10_010_000, "ten-ish seconds", 1.0),),
    )
    rows = TranscriptEvidenceAdapter.compile(
        match=game_match,
        media_binding=binding,
        transcript=transcript,
        transcript_asset=result.proxy_asset,
        clock_domain=TranscriptClockDomain.MATCH_CLOCK,
        producer_version="1.0.0",
        artifact_ref="asset://transcript/transcript.json",
    )
    assert rows[0].source_range.to_dict() == {"start_frame": 0, "end_frame_exclusive": 300}
    assert isinstance(rows[0].source_range.start_frame, int)
    assert game_match.to_dict()["source_rate"] == {"numerator": 30000, "denominator": 1001}
