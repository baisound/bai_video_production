from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess

import pytest

from ai_video_production.canonical_game_event import (
    EventConfirmationState,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_event_resolver import DBDVisualMarkerKind
from ai_video_production.dbd_native_pilot import (
    BoundedFrameSamplingPolicy,
    DBDNativeMediaPilotRunner,
    FFmpegPNGFrameSource,
    NativeFrameSample,
    NativeVisualDetection,
)
from ai_video_production.game_event_evidence import SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_benchmark import (
    BenchmarkDatasetKind,
    EventBenchmarkCase,
    EventBenchmarkDataset,
    parse_event_benchmark_dataset,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate


PNG = b"\x89PNG\r\n\x1a\n" + b"bounded-test-png"


def match() -> GameMatch:
    return GameMatch(
        production_job_id=generate_id(IdKind.JOB),
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001),
        status=GameMatchStatus.ANALYZING,
    )


def gold(game_match: GameMatch) -> EventBenchmarkDataset:
    return EventBenchmarkDataset(
        "dbd-r10b-human-gold",
        1,
        BenchmarkDatasetKind.HUMAN_GOLD,
        (
            EventBenchmarkCase(
                "case-001",
                game_match.source_asset_id,
                GameEventType.WINDOW_VAULT,
                SourceFrameRange(104, 106),
                labeler_ref="human://owner-review-1",
                evaluation_range=SourceFrameRange(100, 110),
            ),
            EventBenchmarkCase(
                "case-002",
                game_match.source_asset_id,
                None,
                None,
                expected_abstention=True,
                labeler_ref="human://owner-review-1",
                evaluation_range=SourceFrameRange(200, 210),
            ),
        ),
    )


class FakeFrameSource:
    def read_frames(self, video_path: Path, frame_indices):
        assert video_path.name == "match.mp4"
        return tuple(
            NativeFrameSample(
                frame_index=index,
                png_bytes=PNG + str(index).encode("ascii"),
                png_sha256="sha256:" + __import__("hashlib").sha256(PNG + str(index).encode("ascii")).hexdigest(),
            )
            for index in frame_indices
        )


class FakeDetector:
    detector_id = "task049.fake-native-visual"
    detector_version = "1.0.0"

    def detect_case(self, *, samples, evaluation_range, source_rate):
        assert source_rate == FrameRate(30000, 1001)
        if evaluation_range.start_frame >= 200:
            return NativeVisualDetection(self.detector_id, self.detector_version, None, 100)
        assert 104 in tuple(sample.frame_index for sample in samples)
        return NativeVisualDetection(
            self.detector_id,
            self.detector_version,
            DBDVisualMarkerKind.WINDOW_VAULT,
            950,
            SourceFrameRange(104, 106),
            (104,),
        )


def test_sampling_policy_is_bounded_deterministic_and_end_exclusive() -> None:
    policy = BoundedFrameSamplingPolicy(max_frames_per_case=5)
    assert policy.sample_indices(SourceFrameRange(100, 110)) == (100, 102, 104, 106, 109)
    assert policy.sample_indices(SourceFrameRange(3, 6)) == (3, 4, 5)
    assert BoundedFrameSamplingPolicy(1).sample_indices(SourceFrameRange(8, 20)) == (8,)


def test_human_gold_round_trip_parser_preserves_evaluation_windows() -> None:
    ds = gold(match())
    payload = ds.to_dict()
    parsed = parse_event_benchmark_dataset(payload)
    assert parsed == ds
    assert parsed.cases[1].native_evaluation_range == SourceFrameRange(200, 210)
    tampered = dict(payload)
    tampered["revision"] = 2
    with pytest.raises(ValueError, match="dataset_sha256"):
        parse_event_benchmark_dataset(tampered)


def test_native_pilot_projects_pixels_to_evidence_cgel_and_native_benchmark(tmp_path: Path) -> None:
    game_match = match()
    media = tmp_path / "match.mp4"
    media.write_bytes(b"not-read-by-fake-source")
    store = GameIntelligenceStore(tmp_path / "analysis.sqlite3")
    report = DBDNativeMediaPilotRunner().run(
        match=game_match,
        analysis_video_path=media,
        dataset=gold(game_match),
        frame_source=FakeFrameSource(),
        detector=FakeDetector(),
        store=store,
    )
    assert report.benchmark.true_positive == 1
    assert report.benchmark.correct_abstention_count == 1
    assert report.benchmark.native_media_evidence is True
    assert report.benchmark.production_accuracy_claim_authorized is False
    assert report.cases[0].confirmation_state is EventConfirmationState.CONFIRMED
    assert report.cases[1].event_id is None
    stored = store.list_events(game_match.match_id)
    assert len(stored) == 1
    assert stored[0].event_type is GameEventType.WINDOW_VAULT
    checkpoint = store.latest_checkpoint(game_match.match_id)
    assert checkpoint.stage == "R10B_NATIVE_PILOT"
    payload = report.to_dict()
    assert payload["native_media_evidence"] is True
    assert payload["production_accuracy_claim_authorized"] is False
    assert payload["production_timeline_mutated"] is False
    assert payload["resolve_write_performed"] is False


def test_native_pilot_rejects_synthetic_wrong_source_and_missing_window(tmp_path: Path) -> None:
    game_match = match()
    media = tmp_path / "match.mp4"
    media.write_bytes(b"x")
    runner = DBDNativeMediaPilotRunner()
    synthetic = replace(gold(game_match), kind=BenchmarkDatasetKind.SYNTHETIC)
    with pytest.raises(ValueError, match="HUMAN_GOLD"):
        runner.run(
            match=game_match,
            analysis_video_path=media,
            dataset=synthetic,
            frame_source=FakeFrameSource(),
            detector=FakeDetector(),
        )
    wrong = EventBenchmarkDataset(
        "wrong-source",
        1,
        BenchmarkDatasetKind.HUMAN_GOLD,
        (
            EventBenchmarkCase(
                "case-001",
                generate_id(IdKind.ASSET),
                None,
                None,
                expected_abstention=True,
                labeler_ref="human://reviewer",
                evaluation_range=SourceFrameRange(1, 3),
            ),
        ),
    )
    with pytest.raises(ValueError, match="analysis source Asset"):
        runner.run(
            match=game_match,
            analysis_video_path=media,
            dataset=wrong,
            frame_source=FakeFrameSource(),
            detector=FakeDetector(),
        )
    no_window = EventBenchmarkDataset(
        "no-window",
        1,
        BenchmarkDatasetKind.HUMAN_GOLD,
        (EventBenchmarkCase("case-001", game_match.source_asset_id, None, None, labeler_ref="human://reviewer"),),
    )
    with pytest.raises(ValueError, match="explicit evaluation_range"):
        runner.run(
            match=game_match,
            analysis_video_path=media,
            dataset=no_window,
            frame_source=FakeFrameSource(),
            detector=FakeDetector(),
        )


def test_detector_cannot_escape_gold_window_or_reference_unsampled_frame(tmp_path: Path) -> None:
    game_match = match()
    media = tmp_path / "match.mp4"
    media.write_bytes(b"x")

    class BadRange(FakeDetector):
        def detect_case(self, **kwargs):
            return NativeVisualDetection(
                self.detector_id,
                self.detector_version,
                DBDVisualMarkerKind.WINDOW_VAULT,
                950,
                SourceFrameRange(90, 106),
                (104,),
            )

    with pytest.raises(ValueError, match="inside the Human Gold evaluation window"):
        DBDNativeMediaPilotRunner().run(
            match=game_match,
            analysis_video_path=media,
            dataset=gold(game_match),
            frame_source=FakeFrameSource(),
            detector=BadRange(),
        )

    class BadSupport(FakeDetector):
        def detect_case(self, **kwargs):
            return NativeVisualDetection(
                self.detector_id,
                self.detector_version,
                DBDVisualMarkerKind.WINDOW_VAULT,
                950,
                SourceFrameRange(104, 106),
                (105,),
            )

    with pytest.raises(ValueError, match="only supplied sampled frames"):
        DBDNativeMediaPilotRunner().run(
            match=game_match,
            analysis_video_path=media,
            dataset=gold(game_match),
            frame_source=FakeFrameSource(),
            detector=BadSupport(),
        )


def test_ffmpeg_frame_source_uses_exact_frame_select_and_no_shell(tmp_path: Path, monkeypatch) -> None:
    media = tmp_path / "match.mp4"
    media.write_bytes(b"x")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        frame = argv[argv.index("-vf") + 1]
        payload = PNG + frame.encode("ascii")
        return subprocess.CompletedProcess(argv, 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rows = FFmpegPNGFrameSource().read_frames(media, (7, 11))
    assert [row.frame_index for row in rows] == [7, 11]
    assert calls[0][0][calls[0][0].index("-vf") + 1] == "select=eq(n\\,7)"
    assert all(call[1]["shell"] is False for call in calls)
    assert all(call[1]["check"] is False for call in calls)


def test_production_accuracy_authority_cannot_be_minted_from_synthetic_or_non_native() -> None:
    game_match = match()
    from ai_video_production.game_intelligence_benchmark import EventBenchmarkEvaluator, EventBenchmarkPrediction

    ds = gold(game_match)
    predictions = (
        EventBenchmarkPrediction("case-001", GameEventType.WINDOW_VAULT, 900, SourceFrameRange(104, 106)),
        EventBenchmarkPrediction("case-002", None, 0, abstained=True),
    )
    with pytest.raises(ValueError, match="HUMAN_GOLD native-media"):
        EventBenchmarkEvaluator.evaluate(ds, predictions, production_accuracy_claim_authorized=True)
    synthetic = replace(ds, kind=BenchmarkDatasetKind.SYNTHETIC)
    with pytest.raises(ValueError, match="HUMAN_GOLD native-media"):
        EventBenchmarkEvaluator.evaluate(
            synthetic,
            predictions,
            native_media_evidence=True,
            production_accuracy_claim_authorized=True,
        )


def test_benchmark_schema_mirror_is_byte_identical_meta_valid_and_accepts_gold() -> None:
    import json
    from importlib import resources
    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[1]
    public = (root / "schemas/game-event-benchmark-dataset.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "game-event-benchmark-dataset.schema.json"
    ).read_bytes()
    assert public == packaged
    schema = json.loads(public)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(gold(match()).to_dict())


def test_native_media_preflight_reads_only_evaluation_windows_and_emits_no_labels(tmp_path: Path) -> None:
    from ai_video_production.dbd_native_pilot import run_native_media_preflight

    game_match = match()
    media = tmp_path / "match.mp4"
    media.write_bytes(b"x")
    report = run_native_media_preflight(
        analysis_video_path=media,
        source_rate=game_match.source_rate,
        dataset=gold(game_match),
        frame_source=FakeFrameSource(),
        sampling_policy=BoundedFrameSamplingPolicy(3),
    )
    payload = report.to_dict()
    assert payload["native_media_decode_observed"] is True
    assert payload["detector_execution_performed"] is False
    assert payload["accuracy_measured"] is False
    assert payload["production_accuracy_claim_authorized"] is False
    serialized = __import__("json").dumps(payload, sort_keys=True)
    assert "WINDOW_VAULT" not in serialized
    assert "human://owner-review-1" not in serialized
    assert [row["sampled_frame_indices"] for row in payload["cases"]] == [[100, 104, 109], [200, 204, 209]]
