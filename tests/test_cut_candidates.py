from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import subprocess
import wave

import pytest

from ai_video_production.cut_candidates import (
    CutCandidateAnalyzer,
    CutCandidateConfig,
    CutCandidateKind,
    CutCandidatePublicationService,
    FfmpegSilenceDetector,
    SilenceRange,
    load_transcript_manifest,
)
from ai_video_production.errors import ProductError
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment


ASSET_ID = "ASSET-00000000000000000000000000"


def write_wav(path: Path, seconds: float = 4.0, *, rate: int = 16000, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(sample_width)
        out.setframerate(rate)
        count = int(round(seconds * rate))
        if sample_width == 2:
            values = [
                int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / rate))
                for i in range(count)
            ]
            payload = struct.pack("<" + "h" * count, *values)
        else:
            payload = b"\x80" * count
        out.writeframes(payload)


class StaticDetector:
    def __init__(self, *ranges: tuple[int, int]):
        self.ranges = tuple(SilenceRange(*item) for item in ranges)

    def detect(self, source, *, duration_us, config):
        return self.ranges


def transcript(*segments: TranscriptSegment) -> TranscriptManifest:
    return TranscriptManifest(ASSET_ID, "ja", "faster-whisper", "small", tuple(segments))


def test_detects_deterministic_silence_core(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio)
    result = CutCandidateAnalyzer.analyze(
        audio,
        source_asset_id=ASSET_ID,
        detector=StaticDetector((1_000_000, 3_000_000)),
    )

    assert result.source_duration_us == 4_000_000
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.kind is CutCandidateKind.SILENCE
    assert (candidate.start_us, candidate.end_us) == (1_080_000, 2_880_000)
    assert candidate.evidence_codes == ("FFMPEG_SILENCEDETECT", "LONG_PAUSE")
    assert result.to_dict()["auto_apply_authorized"] is False


def test_transcript_keep_block_splits_silence_candidate(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio)
    tx = transcript(TranscriptSegment("seg-000001", 1_400_000, 1_600_000, "重要な発話"))

    result = CutCandidateAnalyzer.analyze(
        audio,
        source_asset_id=ASSET_ID,
        transcript=tx,
        detector=StaticDetector((1_000_000, 3_000_000)),
    )

    assert [(c.start_us, c.end_us) for c in result.candidates] == [
        (1_080_000, 1_320_000),
        (1_680_000, 2_880_000),
    ]
    assert [(k.start_us, k.end_us) for k in result.keep_blocks] == [(1_320_000, 1_680_000)]


def test_filler_only_segment_becomes_review_candidate_without_text_leak(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 2.0)
    tx = transcript(
        TranscriptSegment("seg-000001", 200_000, 500_000, "えっと"),
        TranscriptSegment("seg-000002", 700_000, 1_400_000, "本題です"),
    )

    result = CutCandidateAnalyzer.analyze(
        audio, source_asset_id=ASSET_ID, transcript=tx, detector=StaticDetector()
    )
    assert [item.kind for item in result.candidates] == [CutCandidateKind.FILLER]
    assert result.candidates[0].source_segment_ids == ("seg-000001",)
    payload = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "えっと" not in payload
    assert "本題です" not in payload
    assert result.to_dict()["transcript_text_in_manifest"] is False


def test_exact_adjacent_repeat_marks_earlier_only(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 2.0)
    tx = transcript(
        TranscriptSegment("seg-000001", 200_000, 500_000, "これはテストです"),
        TranscriptSegment("seg-000002", 600_000, 900_000, "これはテストです"),
    )
    result = CutCandidateAnalyzer.analyze(
        audio, source_asset_id=ASSET_ID, transcript=tx, detector=StaticDetector()
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].kind is CutCandidateKind.REPEATED_UTTERANCE
    assert result.candidates[0].source_segment_ids == ("seg-000001",)
    assert result.keep_blocks[0].source_segment_ids == ("seg-000002",)


def test_short_repetition_is_not_flagged(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 2.0)
    tx = transcript(
        TranscriptSegment("seg-000001", 200_000, 400_000, "はい"),
        TranscriptSegment("seg-000002", 500_000, 700_000, "はい"),
    )
    result = CutCandidateAnalyzer.analyze(
        audio, source_asset_id=ASSET_ID, transcript=tx, detector=StaticDetector()
    )
    assert result.candidates == ()
    assert len(result.keep_blocks) == 1


def test_publication_report_is_text_free_and_review_only(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 3.0)
    tx = transcript(TranscriptSegment("seg-000001", 100_000, 300_000, "秘密の本文"))
    result = CutCandidateAnalyzer.analyze(
        audio,
        source_asset_id=ASSET_ID,
        transcript=tx,
        detector=StaticDetector((1_000_000, 2_000_000)),
    )

    publication = CutCandidatePublicationService.publish(result, tmp_path / "out")
    manifest_text = publication.manifest_path.read_text(encoding="utf-8")
    report_text = publication.report_path.read_text(encoding="utf-8")
    assert "秘密の本文" not in manifest_text + report_text
    report = json.loads(report_text)
    assert report["auto_apply_authorized"] is False
    assert report["downstream_execution_owner"] == "TASK-010"


def test_loader_verifies_transcript_hash(tmp_path: Path) -> None:
    tx = transcript(TranscriptSegment("seg-000001", 100_000, 300_000, "本文"))
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(tx.to_dict(), ensure_ascii=False), encoding="utf-8")
    loaded = load_transcript_manifest(path)
    assert loaded.to_dict() == tx.to_dict()

    tampered = tx.to_dict()
    tampered["segments"][0]["text"] = "改ざん"
    path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ProductError) as error:
        load_transcript_manifest(path)
    assert error.value.code == "ERR_CUT_TRANSCRIPT_HASH"


def test_source_change_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 1.0)
    import ai_video_production.cut_candidates as module

    values = iter(["sha256:" + "a" * 64, "sha256:" + "b" * 64])
    monkeypatch.setattr(module, "_file_sha256", lambda _: next(values))
    with pytest.raises(ProductError) as error:
        CutCandidateAnalyzer.analyze(
            audio, source_asset_id=ASSET_ID, detector=StaticDetector()
        )
    assert error.value.code == "ERR_CUT_SOURCE_CHANGED"


def test_unsupported_sample_width_fails_closed(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 1.0, sample_width=1)
    with pytest.raises(ProductError) as error:
        CutCandidateAnalyzer.analyze(
            audio, source_asset_id=ASSET_ID, detector=StaticDetector()
        )
    assert error.value.code == "ERR_CUT_AUDIO_FORMAT"


def test_config_hash_is_stable_and_changes_with_threshold() -> None:
    first = CutCandidateConfig()
    second = CutCandidateConfig()
    changed = CutCandidateConfig(silence_threshold_dbfs=-40.0)
    assert first.config_sha256 == second.config_sha256
    assert first.config_sha256 != changed.config_sha256


def test_ffmpeg_detector_uses_fixed_argv_and_parses_trailing_silence(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 4.0)
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        stderr = (
            "[silencedetect] silence_start: 1.000\n"
            "[silencedetect] silence_end: 2.500 | silence_duration: 1.500\n"
            "[silencedetect] silence_start: 3.500\n"
        )
        return subprocess.CompletedProcess(argv, 0, "", stderr)

    detector = FfmpegSilenceDetector(executable="ffmpeg-test", runner=runner)
    ranges = detector.detect(audio, duration_us=4_000_000, config=CutCandidateConfig())

    assert [(item.start_us, item.end_us) for item in ranges] == [
        (1_000_000, 2_500_000),
        (3_500_000, 4_000_000),
    ]
    argv, kwargs = calls[0]
    assert argv[0] == "ffmpeg-test"
    assert "silencedetect=noise=-45dB:d=0.500" in argv
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 1800


def test_ffmpeg_detector_rejects_malformed_event_order(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 2.0)

    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, "", "silence_end: 1.0\n")

    detector = FfmpegSilenceDetector(runner=runner)
    with pytest.raises(ProductError) as error:
        detector.detect(audio, duration_us=2_000_000, config=CutCandidateConfig())
    assert error.value.code == "ERR_CUT_FFMPEG_OUTPUT"


def test_ffmpeg_failure_is_text_free_structured_error(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 2.0)

    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 7, "", "private ffmpeg stderr")

    detector = FfmpegSilenceDetector(runner=runner)
    with pytest.raises(ProductError) as error:
        detector.detect(audio, duration_us=2_000_000, config=CutCandidateConfig())
    assert error.value.code == "ERR_CUT_FFMPEG_EXECUTION"
    assert error.value.details == {"returncode": 7}


def test_transcript_longer_than_audio_fails_closed(tmp_path: Path) -> None:
    audio = tmp_path / "analysis.wav"
    write_wav(audio, 1.0)
    tx = transcript(TranscriptSegment("seg-000001", 100_000, 1_700_000, "長すぎる"))
    with pytest.raises(ProductError) as error:
        CutCandidateAnalyzer.analyze(
            audio,
            source_asset_id=ASSET_ID,
            transcript=tx,
            detector=StaticDetector(),
        )
    assert error.value.code == "ERR_CUT_TRANSCRIPT_DURATION"
