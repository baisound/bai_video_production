from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
import wave

from ai_video_production import (
    AssetIngestRequest,
    AssetIngestService,
    AssetType,
    AudioRightsStatus,
    FrameRate,
    LogicalPathResolver,
    MediaNormalizationService,
    NormalizationRequest,
    PathMapping,
    PermissionState,
    ProfileSnapshot,
    RightsStatus,
    SQLiteProductStore,
    SourcePathPolicy,
)
from ai_video_production.cut_candidates import (
    CutCandidateAnalyzer,
    CutCandidateKind,
    CutCandidatePublicationService,
)
from ai_video_production.editing_skill_handoff import (
    KNOWLEDGE_COMMENTARY,
    SOURCE_READY,
    project_optional_editing_skill_handoff,
)
from ai_video_production.faster_whisper_asr import FasterWhisperConfig
from ai_video_production.large_media_transcription import (
    ChunkedTranscriptionConfig,
    ResumableTranscriptionService,
    TranscriptionChunk,
)
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.resolve_subtitle_handoff import ResolveSubtitleHandoffService
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes, sha256_json
from ai_video_production.subtitle_workspace import SubtitleWorkspace, SubtitleWorkspaceStore
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.timebase import TimingInspection, TimingKind


def _write_wav(path: Path, *, rate: int, frames: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(b"\x00\x00" * frames)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _WaveProbe:
    def probe(self, path: str | Path) -> MediaProbeResult:
        source = Path(path)
        with wave.open(str(source), "rb") as stream:
            rate = stream.getframerate()
            frames = stream.getnframes()
        duration_us = frames * 1_000_000 // rate
        return MediaProbeResult(
            format_name="wav",
            duration_us=duration_us,
            size_bytes=source.stat().st_size,
            bit_rate=None,
            streams=(
                {
                    "codec_type": "audio",
                    "sample_rate": rate,
                    "duration_us": duration_us,
                },
            ),
        )


class _AudioOnlyTimingProbe:
    def inspect(self, path: str | Path) -> TimingInspection:
        result = _WaveProbe().probe(path)
        return TimingInspection(
            TimingKind.AUDIO_ONLY,
            result.duration_us,
            None,
            None,
            None,
            0,
            0,
            0,
            None,
            None,
            "fixture audio",
        )


class _FixtureFfmpeg:
    def run(self, args: list[str], *, timeout_seconds: int) -> dict[str, object]:
        assert timeout_seconds > 0
        target = Path(args[-1])
        _write_wav(target, rate=48_000, frames=48_000)
        return {"returncode": 0}


class _ChunkExtractor:
    def extract(self, source: Path, chunk: TranscriptionChunk, target: Path) -> None:
        assert source.is_file()
        assert chunk.extraction_end_us > chunk.extraction_start_us
        _write_wav(target, rate=16_000, frames=16_000)


class _FixtureProvider:
    provider_id = "fixture-asr"
    model_id = "fixture-model"

    def __init__(self) -> None:
        self.config = FasterWhisperConfig(model="small", allow_model_download=False)

    def transcribe(self, request) -> TranscriptManifest:
        return TranscriptManifest(
            request.source_asset_id,
            request.language or "ja",
            self.provider_id,
            self.model_id,
            (
                TranscriptSegment("seg-000001", 100_000, 300_000, "えっと"),
                TranscriptSegment("seg-000002", 400_000, 900_000, "本題です"),
            ),
        )


class _NoSilenceDetector:
    def detect(self, source: Path, *, duration_us: int, config) -> tuple[()]:
        assert source.is_file()
        assert duration_us == 1_000_000
        return ()


def _exercise_fixture_pipeline(root: Path) -> None:
    incoming = root / "incoming"
    assets = root / "assets"
    jobs = root / "jobs"
    incoming.mkdir()
    assets.mkdir()
    jobs.mkdir()

    source = incoming / "commentary.wav"
    _write_wav(source, rate=8_000, frames=8_000)
    source_before = _sha256(source)

    store = SQLiteProductStore(root / "product.sqlite3")
    profile = ProfileSnapshot.create("knowledge-commentary-fixture", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    resolver = LogicalPathResolver(
        (
            PathMapping("asset://", assets, PureWindowsPath("D:/AI/assets")),
            PathMapping("job://", jobs, PureWindowsPath("D:/AI/jobs")),
        )
    )
    ingest = AssetIngestService(
        store=store,
        resolver=resolver,
        source_policy=SourcePathPolicy((incoming,)),
    )
    ingested = ingest.ingest(
        AssetIngestRequest(
            job.job_id,
            source,
            AssetType.AUDIO,
            RightsStatus.OWNED,
            "USER",
            "knowledge-commentary-ingest",
            commercial_use=PermissionState.ALLOWED,
            derivative_allowed=PermissionState.ALLOWED,
            reuse_allowed=PermissionState.ALLOWED,
            audio_rights_status=AudioRightsStatus.SAFE,
        )
    )

    normalized = MediaNormalizationService(
        store=store,
        resolver=resolver,
        media_probe=_WaveProbe(),
        timing_probe=_AudioOnlyTimingProbe(),
        ffmpeg=_FixtureFfmpeg(),
    ).normalize(
        NormalizationRequest(job.job_id, ingested.asset.asset_id, "knowledge-commentary-normalize")
    )
    assert normalized.operation.status == "COMPLETED"
    assert normalized.analysis_audio_asset is not None
    analysis_audio = resolver.resolve(normalized.analysis_audio_asset.logical_uri)
    assert isinstance(analysis_audio, Path)
    assert _WaveProbe().probe(analysis_audio).streams[0]["sample_rate"] == 48_000

    transcription = ResumableTranscriptionService.run(
        analysis_audio,
        root / "transcription",
        provider=_FixtureProvider(),
        config=ChunkedTranscriptionConfig(chunk_seconds=10, overlap_seconds=2),
        source_asset_id=normalized.analysis_audio_asset.asset_id,
        language="ja",
        probe=_WaveProbe(),
        extractor=_ChunkExtractor(),
    )
    assert transcription.transcript.source_asset_id == normalized.analysis_audio_asset.asset_id
    assert not (root / "transcription" / ".bai-transcription-work").exists()

    candidates = CutCandidateAnalyzer.analyze(
        analysis_audio,
        source_asset_id=normalized.analysis_audio_asset.asset_id,
        transcript=transcription.transcript,
        detector=_NoSilenceDetector(),
    )
    assert [item.kind for item in candidates.candidates] == [CutCandidateKind.FILLER]
    assert candidates.candidates[0].source_segment_ids == ("chunk-000001-seg-000001",)
    assert candidates.transcript_manifest_sha256 == transcription.transcript.to_dict()["manifest_sha256"]
    assert candidates.to_dict()["auto_apply_authorized"] is False
    publication = CutCandidatePublicationService.publish(candidates, root / "cut-candidates")
    report_text = publication.report_path.read_text(encoding="utf-8")
    assert "えっと" not in report_text
    assert "本題です" not in report_text

    workspace = SubtitleWorkspace.from_transcript(transcription.transcript)
    assert workspace.ai_typo_check_enabled is False
    for cue in tuple(workspace.cues):
        workspace = workspace.update(
            cue.cue_id,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            text=cue.text,
            approved=True,
        )
    workspace_path = root / "subtitle-workspace.json"
    SubtitleWorkspaceStore.save(workspace_path, workspace)
    stored_workspace = SubtitleWorkspaceStore.load(workspace_path)
    assert stored_workspace == workspace

    handoff_path = root / "resolve-subtitle-handoff.json"
    plan, write = ResolveSubtitleHandoffService.write(
        handoff_path,
        stored_workspace,
        timeline_rate=FrameRate(30),
    )
    assert write.path == handoff_path.resolve()
    assert plan.ready_for_resolve_write is True
    assert len(plan.placements) == 2
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert handoff == plan.to_dict()
    assert handoff["source_workspace_sha256"] == sha256_json(
        stored_workspace.to_dict()
    )
    handoff_body = {
        key: value for key, value in handoff.items() if key != "plan_sha256"
    }
    assert handoff["plan_sha256"] == sha256_bytes(
        canonical_json_bytes(handoff_body)
    )
    common_evidence = project_optional_editing_skill_handoff(
        editing_mode=KNOWLEDGE_COMMENTARY,
        value=handoff,
    )
    assert common_evidence["source_sha256"] == handoff["plan_sha256"]
    assert common_evidence["source_readiness"] == SOURCE_READY
    assert common_evidence["resolve_write_authorized"] is False
    assert common_evidence["runtime_authority_created"] is False
    common_unsigned = {
        key: value
        for key, value in common_evidence.items()
        if key != "evidence_sha256"
    }
    assert common_evidence["evidence_sha256"] == sha256_bytes(
        canonical_json_bytes(common_unsigned)
    )
    common_text = json.dumps(common_evidence, ensure_ascii=False)
    assert "えっと" not in common_text
    assert "本題です" not in common_text

    assert _sha256(source) == source_before
    assert normalized.analysis_audio_asset.asset_id == transcription.transcript.source_asset_id


def test_knowledge_commentary_fixture_pipeline_reaches_reviewed_resolve_handoff(
    tmp_path: Path,
) -> None:
    _exercise_fixture_pipeline(tmp_path)


def test_unreviewed_transcript_never_authorizes_resolve_write() -> None:
    transcript = TranscriptManifest(
        "ASSET-00000000000000000000000000",
        "ja",
        "fixture-asr",
        "fixture-model",
        (TranscriptSegment("seg-000001", 0, 1_000_000, "未承認"),),
    )
    workspace = SubtitleWorkspace.from_transcript(transcript)
    plan = ResolveSubtitleHandoffService.build(workspace, timeline_rate=FrameRate(30))
    assert plan.ready_for_resolve_write is False
