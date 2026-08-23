from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.cut_candidates import load_transcript_manifest
from ai_video_production.faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.large_media_transcription import (
    ChunkedTranscriptionConfig,
    _owned_segments,
    build_chunk_plan,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.semantic_audio_cues import (
    CueReviewState,
    KeywordProfile,
    SpeechCueDetectionService,
    SpeechCueManifest,
    SpeechCuePublicationService,
    build_montage_semantic_audio_cues_projection,
    parse_montage_semantic_audio_cues_projection,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.subtitles import AsrRequest, TranscriptManifest, TranscriptSegment, TranscriptWord
from ai_video_production.timebase import FrameRate, FrameRounding


ASSET_ID = "ASSET-00000000000000000000000000"


def profile(*, threshold: float = 0.65) -> KeywordProfile:
    return KeywordProfile.from_dict({
        "profile_id": "dbd-chase-call-ja-v1",
        "language": "ja",
        "keywords": [{
            "keyword_id": "CHASE_CALL",
            "aliases": ["チェイス", "チェース", "chase"],
            "match_mode": "PHRASE",
            "minimum_confidence": threshold,
        }],
    })


def word_segment(
    segment_id: str,
    start: int,
    end: int,
    text: str,
    words: tuple[TranscriptWord, ...],
) -> TranscriptSegment:
    return TranscriptSegment(segment_id, start, end, text, words=words)


def timed_transcript(*segments: TranscriptSegment) -> TranscriptManifest:
    return TranscriptManifest(
        ASSET_ID,
        "ja",
        "faster-whisper",
        "small",
        tuple(segments),
        True,
    )


def test_legacy_transcript_serialization_shape_is_unchanged() -> None:
    transcript = TranscriptManifest(
        ASSET_ID,
        "ja",
        "fixture",
        "model",
        (TranscriptSegment("seg-1", 0, 1_000_000, "本文"),),
    )
    payload = transcript.to_dict()
    assert payload["manifest_version"] == "1.0.0"
    assert "words" not in payload["segments"][0]
    expected_keys = {
        "manifest_version", "source_asset_id", "language", "provider_id",
        "model_id", "segments", "manifest_sha256",
    }
    assert set(payload) == expected_keys


def test_word_timed_transcript_v11_schema_and_loader_round_trip(tmp_path: Path) -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-1", 100_000, 900_000, "チェイスです",
            (TranscriptWord(150_000, 450_000, "チェイス", 0.93),),
        )
    )
    payload = transcript.to_dict()
    assert payload["manifest_version"] == "1.1.0"
    assert payload["segments"][0]["words"][0]["text"] == "チェイス"
    validate_instance(payload, Path("schemas/transcript-manifest-v1.1.schema.json"))
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    loaded = load_transcript_manifest(path)
    assert loaded.word_timestamps_included is True
    assert loaded.to_dict() == payload


@dataclass
class _RawWord:
    start: float
    end: float
    word: str
    probability: float | None = None


@dataclass
class _RawSegment:
    start: float
    end: float
    text: str
    words: list[_RawWord]


class _Info:
    language = "ja"


class _CaptureModel:
    calls: list[dict] = []

    def __init__(self, model: str, **kwargs) -> None:
        self.model = model

    def transcribe(self, path: str, **kwargs):
        type(self).calls.append(dict(kwargs))
        segment = _RawSegment(
            0.1,
            1.0,
            "チェイス",
            [_RawWord(0.2, 0.5, " チェイス ", 0.91)],
        )
        return iter([segment]), _Info()


def test_faster_whisper_word_timestamps_are_explicit_opt_in(tmp_path: Path) -> None:
    media = tmp_path / "sample.wav"
    media.write_bytes(b"fixture")
    _CaptureModel.calls.clear()
    provider = FasterWhisperProvider(FasterWhisperConfig(), model_factory=_CaptureModel)

    legacy = provider.transcribe(AsrRequest(generate_id(IdKind.ASSET), str(media)))
    worded = provider.transcribe(
        AsrRequest(generate_id(IdKind.ASSET), str(media), include_word_timestamps=True)
    )

    assert "word_timestamps" not in _CaptureModel.calls[0]
    assert _CaptureModel.calls[1]["word_timestamps"] is True
    assert legacy.word_timestamps_included is False
    assert legacy.segments[0].words == ()
    assert worded.word_timestamps_included is True
    assert [(w.start_us, w.end_us, w.text, w.confidence) for w in worded.segments[0].words] == [
        (200_000, 500_000, "チェイス", 0.91)
    ]


def test_two_non_overlapping_chase_calls_are_two_confirmed_cues() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス!", 0.93),),
        ),
        word_segment(
            "seg-b", 2_000_000, 3_000_000, "chase",
            (TranscriptWord(2_100_000, 2_400_000, "ＣＨＡＳＥ", 0.89),),
        ),
    )
    manifest = SpeechCueDetectionService.detect(
        transcript,
        source_frame_rate=FrameRate(60000, 1001),
        keyword_profile=profile(),
    )
    assert manifest.counts == {"confirmed": 2, "review": 0, "rejected": 0}
    assert [cue.review_state for cue in manifest.cues] == [
        CueReviewState.CONFIRMED, CueReviewState.CONFIRMED,
    ]
    assert manifest.cues[0].cue_id != manifest.cues[1].cue_id


def test_low_confidence_is_review_and_confirmed_projection_excludes_it() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.40),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(60, 1), keyword_profile=profile()
    )
    assert manifest.counts == {"confirmed": 0, "review": 1, "rejected": 0}
    projection = build_montage_semantic_audio_cues_projection(manifest)
    assert projection["confirmed_count"] == 0
    assert projection["review_count"] == 1
    assert projection["cues"] == []


def test_missing_word_timing_never_becomes_confirmed() -> None:
    transcript = TranscriptManifest(
        ASSET_ID,
        "ja",
        "fixture",
        "model",
        (TranscriptSegment("seg-a", 0, 1_000_000, "いまチェイスしてます"),),
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    assert manifest.counts["confirmed"] == 0
    assert manifest.counts["review"] == 1
    assert manifest.cues[0].timing_granularity.value == "SEGMENT_FALLBACK"


def test_zero_hits_is_success_and_legacy_fallback_sidecar_is_empty() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "発電機",
            (TranscriptWord(100_000, 400_000, "発電機", 0.98),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    assert manifest.counts == {"confirmed": 0, "review": 0, "rejected": 0}
    projection = build_montage_semantic_audio_cues_projection(manifest)
    assert projection["cues"] == []
    assert projection["canonical_timeline"] is False
    assert projection["auto_apply_authorized"] is False


@pytest.mark.parametrize(
    "rate",
    [
        FrameRate(30000, 1001), FrameRate(60000, 1001), FrameRate(24, 1),
        FrameRate(25, 1), FrameRate(30, 1), FrameRate(60, 1),
    ],
)
def test_source_frame_conversion_is_exact_and_deterministic(rate: FrameRate) -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 30_000_000, 31_000_000, "チェイス",
            (TranscriptWord(30_030_000, 30_530_500, "チェイス", 0.99),),
        )
    )
    first = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=rate, keyword_profile=profile()
    ).cues[0]
    second = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=rate, keyword_profile=profile()
    ).cues[0]
    assert first == second
    assert first.source_start_frame == rate.us_to_frame(30_030_000, rounding=FrameRounding.FLOOR)
    assert first.source_end_frame_exclusive == max(
        first.source_start_frame + 1,
        rate.us_to_frame(30_530_500, rounding=FrameRounding.CEIL),
    )


def test_manifest_and_ids_are_deterministic_across_100_runs() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    documents = [
        SpeechCueDetectionService.detect(
            transcript, source_frame_rate=FrameRate(60000, 1001), keyword_profile=profile()
        ).to_dict()
        for _ in range(100)
    ]
    canonical = [canonical_json_bytes(item) for item in documents]
    assert len(set(canonical)) == 1
    body = dict(documents[0])
    claimed = body.pop("manifest_sha256")
    assert claimed == sha256_bytes(canonical_json_bytes(body))
    assert SpeechCueManifest.from_dict(documents[0]).to_dict() == documents[0]


def test_projection_hash_and_authority_tampering_fail_closed() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    projection = build_montage_semantic_audio_cues_projection(manifest)
    assert parse_montage_semantic_audio_cues_projection(projection) == projection

    tampered = dict(projection)
    tampered["auto_apply_authorized"] = True
    body = dict(tampered)
    body.pop("projection_sha256")
    tampered["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="cannot authorize"):
        parse_montage_semantic_audio_cues_projection(tampered)


def test_manifest_binding_detects_transcript_and_profile_drift() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    base_profile = profile()
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=base_profile
    )
    manifest.assert_bound_to(transcript=transcript, keyword_profile=base_profile)
    changed = profile(threshold=0.70)
    with pytest.raises(ValueError, match="profile hash mismatch"):
        manifest.assert_bound_to(transcript=transcript, keyword_profile=changed)


def test_publication_is_text_free_and_schema_valid(tmp_path: Path) -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-secret", 0, 1_000_000, "秘密の発言 チェイス",
            (TranscriptWord(500_000, 800_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    publication = SpeechCuePublicationService.publish(manifest, tmp_path / "private-output")
    manifest_text = publication.manifest_path.read_text(encoding="utf-8")
    projection_text = publication.projection_path.read_text(encoding="utf-8")
    report_text = publication.report_path.read_text(encoding="utf-8")
    joined = manifest_text + projection_text + report_text
    assert "秘密の発言" not in joined
    assert str(tmp_path) not in joined
    assert "seg-secret" in manifest_text  # opaque provenance ID is allowed only in private manifest
    assert "seg-secret" not in projection_text + report_text

    validate_instance(json.loads(manifest_text), Path("schemas/speech-cue-manifest.schema.json"))
    validate_instance(json.loads(projection_text), Path("schemas/montage-semantic-audio-cues.schema.json"))
    validate_instance(json.loads(report_text), Path("schemas/speech-cue-report.schema.json"))


def test_profile_is_bounded_and_alias_conflicts_fail_closed() -> None:
    with pytest.raises(ValueError, match="multiple keyword IDs"):
        KeywordProfile.from_dict({
            "profile_id": "bad",
            "language": "ja",
            "keywords": [
                {"keyword_id": "A", "aliases": ["ＣＨＡＳＥ"], "match_mode": "PHRASE", "minimum_confidence": 0.5},
                {"keyword_id": "B", "aliases": ["chase"], "match_mode": "PHRASE", "minimum_confidence": 0.5},
            ],
        })
    with pytest.raises(ValueError, match="without NUL"):
        KeywordProfile.from_dict({
            "profile_id": "bad",
            "language": "ja",
            "keywords": [
                {"keyword_id": "A", "aliases": ["チェ\x00イス"], "match_mode": "PHRASE", "minimum_confidence": 0.5}
            ],
        })


def test_chunk_overlap_same_utterance_has_single_core_owner_and_keeps_word_timing() -> None:
    chunks, _ = build_chunk_plan(20_000_000, ChunkedTranscriptionConfig(chunk_seconds=10, overlap_seconds=2))
    first, second = chunks

    first_tx = TranscriptManifest(
        ASSET_ID, "ja", "faster-whisper", "small",
        (TranscriptSegment(
            "local-a", 9_500_000, 10_200_000, "チェイス",
            words=(TranscriptWord(9_600_000, 9_900_000, "チェイス", 0.9),),
        ),), True,
    )
    second_tx = TranscriptManifest(
        ASSET_ID, "ja", "faster-whisper", "small",
        (TranscriptSegment(
            "local-b", 1_500_000, 2_200_000, "チェイス",
            words=(TranscriptWord(1_600_000, 1_900_000, "チェイス", 0.9),),
        ),), True,
    )

    owned_first = _owned_segments(first_tx, first)
    owned_second = _owned_segments(second_tx, second)
    assert len(owned_first) == 1
    assert owned_second == ()
    assert [(word.start_us, word.end_us) for word in owned_first[0].words] == [
        (9_600_000, 9_900_000)
    ]


def test_non_overlapping_repeated_calls_in_one_segment_remain_distinct() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-repeat", 0, 1_000_000, "チェイス、チェイス",
            (
                TranscriptWord(100_000, 300_000, "チェイス", 0.95),
                TranscriptWord(500_000, 700_000, "チェイス", 0.94),
            ),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(60, 1), keyword_profile=profile()
    )
    assert manifest.counts == {"confirmed": 2, "review": 0, "rejected": 0}
    assert [(cue.source_start_us, cue.source_end_us) for cue in manifest.cues] == [
        (100_000, 300_000), (500_000, 700_000)
    ]


def test_multi_token_phrase_alias_is_detected_as_one_word_timed_cue() -> None:
    phrase_profile = KeywordProfile.from_dict({
        "profile_id": "dbd-chase-start-ja-v1",
        "language": "ja",
        "keywords": [{
            "keyword_id": "CHASE_START_CALL",
            "aliases": ["チェイス開始"],
            "match_mode": "PHRASE",
            "minimum_confidence": 0.65,
        }],
    })
    transcript = timed_transcript(
        word_segment(
            "seg-phrase", 0, 1_000_000, "チェイス 開始",
            (
                TranscriptWord(100_000, 300_000, "チェイス", 0.92),
                TranscriptWord(320_000, 520_000, "開始", 0.90),
            ),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=phrase_profile
    )
    assert manifest.counts == {"confirmed": 1, "review": 0, "rejected": 0}
    assert manifest.cues[0].source_start_us == 100_000
    assert manifest.cues[0].source_end_us == 520_000


def test_overlapping_raw_word_timing_is_not_repaired_into_confirmed_evidence(tmp_path: Path) -> None:
    class _OverlapModel:
        def __init__(self, model: str, **kwargs) -> None:
            pass

        def transcribe(self, path: str, **kwargs):
            segment = _RawSegment(
                0.0,
                1.0,
                "発電機 チェイス",
                [
                    _RawWord(0.10, 0.60, "発電機", 0.99),
                    _RawWord(0.50, 0.80, "チェイス", 0.99),
                ],
            )
            return iter([segment]), _Info()

    media = tmp_path / "sample.wav"
    media.write_bytes(b"fixture")
    provider = FasterWhisperProvider(FasterWhisperConfig(), model_factory=_OverlapModel)
    transcript = provider.transcribe(
        AsrRequest(ASSET_ID, str(media), include_word_timestamps=True)
    )
    assert [word.text for word in transcript.segments[0].words] == ["発電機"]
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    assert manifest.counts == {"confirmed": 0, "review": 1, "rejected": 0}
    assert manifest.cues[0].timing_granularity.value == "SEGMENT_FALLBACK"


def test_projection_recomputed_count_tampering_fails_closed() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    projection = build_montage_semantic_audio_cues_projection(manifest)
    tampered = dict(projection)
    tampered["confirmed_count"] = 2
    body = dict(tampered)
    body.pop("projection_sha256")
    tampered["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="confirmed_count"):
        parse_montage_semantic_audio_cues_projection(tampered)


def test_projection_unknown_field_fails_even_with_valid_recomputed_hash() -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    projection = build_montage_semantic_audio_cues_projection(manifest)
    tampered = dict(projection)
    tampered["resolve_write_authorized"] = True
    body = dict(tampered)
    body.pop("projection_sha256")
    tampered["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="unknown fields"):
        parse_montage_semantic_audio_cues_projection(tampered)


def test_legacy_and_new_schemas_and_packaged_mirrors_are_exact() -> None:
    from importlib import resources

    legacy = TranscriptManifest(
        ASSET_ID, "ja", "fixture", "model",
        (TranscriptSegment("seg-legacy", 0, 1_000_000, "本文"),),
    ).to_dict()
    validate_instance(legacy, Path("schemas/transcript-manifest.schema.json"))

    canonical_names = [
        "keyword-profile.schema.json",
        "transcript-manifest-v1.1.schema.json",
        "speech-cue-manifest.schema.json",
        "montage-semantic-audio-cues.schema.json",
        "speech-cue-report.schema.json",
    ]
    from jsonschema import Draft202012Validator

    for name in canonical_names:
        public = Path("schemas") / name
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name)
        assert packaged.read_bytes() == public.read_bytes(), name
        Draft202012Validator.check_schema(json.loads(public.read_text(encoding="utf-8")))


def test_keyword_profile_parser_rejects_boolean_confidence_and_non_text_ids() -> None:
    with pytest.raises(ValueError, match="minimum_confidence"):
        KeywordProfile.from_dict({
            "profile_id": "bad",
            "language": "ja",
            "keywords": [{
                "keyword_id": "CHASE_CALL",
                "aliases": ["チェイス"],
                "match_mode": "PHRASE",
                "minimum_confidence": True,
            }],
        })
    with pytest.raises(ValueError, match="must be text"):
        KeywordProfile.from_dict({
            "profile_id": "bad",
            "language": "ja",
            "keywords": [{
                "keyword_id": 123,
                "aliases": ["チェイス"],
                "match_mode": "PHRASE",
                "minimum_confidence": 0.65,
            }],
        })


def test_speech_cue_cli_source_has_no_shell_execution_and_status_is_path_free(tmp_path: Path, capsys) -> None:
    from ai_video_production import speech_cue_cli

    source = Path(speech_cue_cli.__file__).read_text(encoding="utf-8")
    assert "shell=True" not in source

    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript.to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    out = tmp_path / "private-cues"
    assert speech_cue_cli.main([
        str(transcript_path),
        "--output-dir", str(out),
        "--source-frame-rate", "60000/1001",
    ]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["host_path_in_status"] is False
    assert str(tmp_path) not in json.dumps(status, ensure_ascii=False)
    report = json.loads((out / "speech-cue-report.json").read_text(encoding="utf-8"))
    assert report["publication_complete"] is True
    assert report["projection_sha256"].startswith("sha256:")


def test_creator_application_service_runs_existing_provider_with_word_timing(tmp_path: Path) -> None:
    from ai_video_production.speech_cue_application import SpeechCueApplicationService

    media = tmp_path / "gameplay.wav"
    media.write_bytes(b"fixture")
    _CaptureModel.calls.clear()
    provider = FasterWhisperProvider(FasterWhisperConfig(), model_factory=_CaptureModel)
    result = SpeechCueApplicationService.transcribe_and_detect(
        media,
        source_asset_id=ASSET_ID,
        source_frame_rate=FrameRate(60000, 1001),
        keyword_profile=profile(),
        output_directory=tmp_path / "creator-job",
        provider=provider,
        language="ja",
    )
    assert _CaptureModel.calls == [{
        "language": "ja",
        "beam_size": 5,
        "vad_filter": True,
        "word_timestamps": True,
    }]
    assert result.transcript.word_timestamps_included is True
    assert result.cue_publication.manifest.counts["confirmed"] == 1
    status = result.public_status()
    assert status["transcription_generated"] is True
    assert status["host_path_in_status"] is False
    assert status["transcript_text_in_status"] is False
    assert str(tmp_path) not in json.dumps(status, ensure_ascii=False)
    assert (tmp_path / "creator-job" / "transcription" / "transcript.json").is_file()
    assert (tmp_path / "creator-job" / "semantic-cues" / "montage-semantic-audio-cues.json").is_file()


def test_creator_resumable_route_preserves_word_timing_and_resume(tmp_path: Path) -> None:
    from ai_video_production.errors import ProductError, ProductErrorCategory
    from ai_video_production.large_media_transcription import TranscriptionChunk
    from ai_video_production.media_probe import MediaProbeResult
    from ai_video_production.speech_cue_application import SpeechCueApplicationService

    class _Probe:
        def probe(self, path: str | Path) -> MediaProbeResult:
            return MediaProbeResult(
                format_name="fake",
                duration_us=20_000_000,
                size_bytes=Path(path).stat().st_size,
                bit_rate=None,
                streams=({"codec_type": "audio", "duration_us": 20_000_000},),
            )

    class _Extractor:
        def __init__(self) -> None:
            self.chunks: list[str] = []

        def extract(self, source: Path, chunk: TranscriptionChunk, target: Path) -> None:
            self.chunks.append(chunk.chunk_id)
            target.write_bytes(b"fake wav")

    class _WordProvider:
        provider_id = "fake-word-asr"
        model_id = "fake-model"

        def __init__(self, *, fail_on_call: int | None = None) -> None:
            self.config = FasterWhisperConfig(model="small", allow_model_download=False)
            self.fail_on_call = fail_on_call
            self.calls = 0

        def transcribe(self, request: AsrRequest) -> TranscriptManifest:
            self.calls += 1
            assert request.include_word_timestamps is True
            if self.fail_on_call == self.calls:
                raise ProductError(
                    "ERR_FAKE_ASR_FAILURE",
                    "synthetic interruption",
                    ProductErrorCategory.TRANSIENT,
                    retryable=True,
                )
            return TranscriptManifest(
                request.source_asset_id,
                request.language or "ja",
                self.provider_id,
                self.model_id,
                (
                    TranscriptSegment(
                        "seg-1",
                        2_000_000,
                        4_000_000,
                        "チェイス",
                        words=(TranscriptWord(2_500_000, 3_000_000, "チェイス", 0.95),),
                    ),
                ),
                True,
            )

    media = tmp_path / "long-gameplay.bin"
    media.write_bytes(b"media")
    out = tmp_path / "creator-long-job"
    cfg = ChunkedTranscriptionConfig(chunk_seconds=10, overlap_seconds=2)

    with pytest.raises(ProductError, match="synthetic interruption"):
        SpeechCueApplicationService.transcribe_resumable_and_detect(
            media,
            source_asset_id=ASSET_ID,
            source_frame_rate=FrameRate(60000, 1001),
            keyword_profile=profile(),
            output_directory=out,
            provider=_WordProvider(fail_on_call=2),
            config=cfg,
            language="ja",
            probe=_Probe(),
            extractor=_Extractor(),
        )

    checkpoint = out / "transcription" / ".bai-transcription-work" / "checkpoint.json"
    assert checkpoint.is_file()
    resumed_provider = _WordProvider()
    extractor = _Extractor()
    result = SpeechCueApplicationService.transcribe_resumable_and_detect(
        media,
        source_asset_id=ASSET_ID,
        source_frame_rate=FrameRate(60000, 1001),
        keyword_profile=profile(),
        output_directory=out,
        provider=resumed_provider,
        config=cfg,
        language="ja",
        resume=True,
        probe=_Probe(),
        extractor=extractor,
    )
    assert resumed_provider.calls == 1
    assert extractor.chunks == ["chunk-000002"]
    assert result.transcript.word_timestamps_included is True
    assert result.cue_publication.manifest.counts == {
        "confirmed": 2,
        "review": 0,
        "rejected": 0,
    }
    report = json.loads(
        (out / "transcription" / "transcription-report.json").read_text(encoding="utf-8")
    )
    assert report["execution_mode"] == "CHUNKED_RESUMABLE"
    assert report["resumed_chunk_count"] == 1


def test_publication_reader_requires_complete_cross_bound_set(tmp_path: Path) -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    out = tmp_path / "publication"
    SpeechCuePublicationService.publish(manifest, out)
    verified = SpeechCuePublicationService.read_verified(out)
    assert verified.manifest.to_dict() == manifest.to_dict()

    projection_path = out / "montage-semantic-audio-cues.json"
    report_path = out / "speech-cue-report.json"
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["cues"][0]["source_start_frame"] += 1
    body = dict(projection)
    body.pop("projection_sha256")
    projection["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
    projection_path.write_text(json.dumps(projection, ensure_ascii=False), encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["projection_sha256"] = projection["projection_sha256"]
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    from ai_video_production.errors import ProductError
    with pytest.raises(ProductError) as exc:
        SpeechCuePublicationService.read_verified(out)
    assert exc.value.code == "ERR_SPEECH_CUE_PUBLICATION_INVALID"


def test_publication_reader_rejects_missing_commit_marker(tmp_path: Path) -> None:
    transcript = timed_transcript(
        word_segment(
            "seg-a", 0, 1_000_000, "チェイス",
            (TranscriptWord(100_000, 400_000, "チェイス", 0.93),),
        )
    )
    manifest = SpeechCueDetectionService.detect(
        transcript, source_frame_rate=FrameRate(30, 1), keyword_profile=profile()
    )
    out = tmp_path / "publication"
    SpeechCuePublicationService.publish(manifest, out)
    (out / "speech-cue-report.json").unlink()
    from ai_video_production.errors import ProductError
    with pytest.raises(ProductError) as exc:
        SpeechCuePublicationService.read_verified(out)
    assert exc.value.code == "ERR_SPEECH_CUE_PUBLICATION_INCOMPLETE"


def test_cli_language_defaults_to_profile_and_resume_requires_resumable() -> None:
    from ai_video_production import speech_cue_cli

    parser = speech_cue_cli.build_parser()
    args = parser.parse_args([
        "--media", "gameplay.mp4",
        "--source-asset-id", ASSET_ID,
        "--output-dir", "out",
        "--source-frame-rate", "60/1",
    ])
    assert args.language is None
    assert args.resumable is False
