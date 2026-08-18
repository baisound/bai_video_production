"""TASK-049 R10B bounded real-media pilot orchestration.

This module is deliberately an *accuracy-evaluation* lane, not a production
recognition claim.  It provides:

- deterministic bounded frame sampling;
- a Windows/Linux compatible FFmpeg PNG frame source;
- a detector port that receives pixels but no Human Gold label;
- projection into existing R4 Evidence -> Candidate -> CGEL resolution;
- optional append-only persistence through the existing R2 Store;
- Human-Gold benchmark evaluation with native-media provenance.

It does not ship a trained DbD detector.  A concrete detector must be supplied
and evaluated against Human Gold before accuracy can be discussed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
from typing import Any, Protocol, Sequence

from .canonical_game_event import (
    EventConfirmationState,
    GameEventType,
    GameMatch,
)
from .dbd_event_resolver import (
    BoundedDBDEventProducer,
    DBDEventResolver,
    DBDVisualMarkerKind,
)
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from .game_event_store import GameIntelligenceStore
from .game_intelligence_benchmark import (
    BenchmarkDatasetKind,
    EventBenchmarkDataset,
    EventBenchmarkEvaluator,
    EventBenchmarkPrediction,
    EventBenchmarkReport,
)
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _bounded_text(value: str, *, field_name: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} must be a non-empty bounded string")
    return value


def _external(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.EXTERNAL_DEPENDENCY, False, details=details)


def _timeout(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.TIMEOUT, True, details=details)


@dataclass(frozen=True, slots=True)
class NativeFrameSample:
    frame_index: int
    png_bytes: bytes
    png_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.frame_index, bool) or not isinstance(self.frame_index, int) or self.frame_index < 0:
            raise ValueError("frame_index must be a non-negative integer")
        if not isinstance(self.png_bytes, bytes) or not self.png_bytes.startswith(_PNG_SIGNATURE):
            raise ValueError("png_bytes must contain a PNG image")
        expected = "sha256:" + hashlib.sha256(self.png_bytes).hexdigest()
        if self.png_sha256 != expected:
            raise ValueError("png_sha256 does not match png_bytes")


@dataclass(frozen=True, slots=True)
class BoundedFrameSamplingPolicy:
    max_frames_per_case: int = 5

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_frames_per_case, bool)
            or not isinstance(self.max_frames_per_case, int)
            or not 1 <= self.max_frames_per_case <= 32
        ):
            raise ValueError("max_frames_per_case must be 1..32")

    def sample_indices(self, source_range: SourceFrameRange) -> tuple[int, ...]:
        if not isinstance(source_range, SourceFrameRange):
            raise ValueError("source_range must be SourceFrameRange")
        count = min(source_range.duration_frames, self.max_frames_per_case)
        if count == 1:
            return (source_range.start_frame,)
        if source_range.duration_frames <= count:
            return tuple(range(source_range.start_frame, source_range.end_frame_exclusive))
        span = source_range.duration_frames - 1
        values = {
            source_range.start_frame + (span * index) // (count - 1)
            for index in range(count)
        }
        return tuple(sorted(values))


class NativeFrameSource(Protocol):
    def read_frames(self, video_path: Path, frame_indices: Sequence[int]) -> tuple[NativeFrameSample, ...]: ...


class FFmpegPNGFrameSource:
    """Read exact decoded frame indices through the existing FFmpeg dependency.

    R10B is intentionally bounded, so one FFmpeg process per selected frame is
    acceptable for a pilot and keeps frame-index provenance simple.  Full-match
    high-throughput decoding belongs to a later detector/runtime optimization.
    """

    def __init__(
        self,
        executable: str = "ffmpeg",
        *,
        timeout_seconds: int = 30,
        max_png_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        _bounded_text(executable, field_name="executable", maximum=256)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be 1..300")
        if isinstance(max_png_bytes, bool) or not isinstance(max_png_bytes, int) or not 1024 <= max_png_bytes <= 256 * 1024 * 1024:
            raise ValueError("max_png_bytes out of range")
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_png_bytes = max_png_bytes

    def _read_one(self, path: Path, frame_index: int) -> NativeFrameSample:
        filter_expr = f"select=eq(n\\,{frame_index})"
        argv = [
            self.executable,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            filter_expr,
            "-vsync",
            "0",
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise _external("ERR_DBD_NATIVE_FFMPEG_NOT_FOUND", "ffmpeg executable is unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise _timeout(
                "ERR_DBD_NATIVE_FRAME_TIMEOUT",
                "ffmpeg frame extraction timed out",
                frame_index=frame_index,
            ) from exc
        stderr_hash = "sha256:" + hashlib.sha256(proc.stderr).hexdigest()
        if proc.returncode != 0:
            raise _external(
                "ERR_DBD_NATIVE_FRAME_EXTRACTION_FAILED",
                "ffmpeg could not decode the requested frame",
                frame_index=frame_index,
                exit_code=proc.returncode,
                stderr_sha256=stderr_hash,
            )
        if not proc.stdout.startswith(_PNG_SIGNATURE):
            raise _external(
                "ERR_DBD_NATIVE_FRAME_NOT_PRODUCED",
                "ffmpeg did not return a PNG frame",
                frame_index=frame_index,
                stderr_sha256=stderr_hash,
            )
        if len(proc.stdout) > self.max_png_bytes:
            raise _external(
                "ERR_DBD_NATIVE_FRAME_TOO_LARGE",
                "decoded PNG exceeds the bounded pilot limit",
                frame_index=frame_index,
                size_bytes=len(proc.stdout),
            )
        digest = "sha256:" + hashlib.sha256(proc.stdout).hexdigest()
        return NativeFrameSample(frame_index, proc.stdout, digest)

    def read_frames(self, video_path: Path, frame_indices: Sequence[int]) -> tuple[NativeFrameSample, ...]:
        path = Path(video_path)
        if not path.exists() or not path.is_file():
            raise ValueError("video_path must be an existing file")
        if path.is_symlink():
            raise ValueError("video_path symlinks are not admitted for the native pilot")
        indices = tuple(frame_indices)
        if not indices or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in indices):
            raise ValueError("frame_indices must contain non-negative integers")
        if tuple(sorted(set(indices))) != indices:
            raise ValueError("frame_indices must be unique and sorted")
        return tuple(self._read_one(path, frame_index) for frame_index in indices)


@dataclass(frozen=True, slots=True)
class NativeMediaPreflightCase:
    case_id: str
    evaluation_range: SourceFrameRange
    sampled_frame_indices: tuple[int, ...]
    sampled_frame_sha256: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "evaluation_range": self.evaluation_range.to_dict(),
            "sampled_frame_indices": list(self.sampled_frame_indices),
            "sampled_frame_sha256": list(self.sampled_frame_sha256),
        }


@dataclass(frozen=True, slots=True)
class NativeMediaPreflightReport:
    source_asset_id: str
    source_rate: FrameRate
    dataset_id: str
    dataset_revision: int
    dataset_sha256: str
    cases: tuple[NativeMediaPreflightCase, ...]

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "source_asset_id": self.source_asset_id,
            "source_rate": {
                "numerator": self.source_rate.numerator,
                "denominator": self.source_rate.denominator,
            },
            "dataset_id": self.dataset_id,
            "dataset_revision": self.dataset_revision,
            "dataset_sha256": self.dataset_sha256,
            "cases": [item.to_dict() for item in self.cases],
            "native_media_decode_observed": True,
            "detector_execution_performed": False,
            "accuracy_measured": False,
            "production_accuracy_claim_authorized": False,
            "provider_execution_performed": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
        }
        return {**body, "preflight_report_sha256": sha256_bytes(canonical_json_bytes(body))}


def run_native_media_preflight(
    *,
    analysis_video_path: Path,
    source_rate: FrameRate,
    dataset: EventBenchmarkDataset,
    frame_source: NativeFrameSource,
    sampling_policy: BoundedFrameSamplingPolicy = BoundedFrameSamplingPolicy(),
) -> NativeMediaPreflightReport:
    """Verify exact real-media frame readability without running a detector.

    Expected labels are intentionally ignored; only evaluation windows are read.
    """
    if not isinstance(source_rate, FrameRate):
        raise ValueError("source_rate must be an exact FrameRate")
    if dataset.kind is not BenchmarkDatasetKind.HUMAN_GOLD:
        raise ValueError("native media preflight requires a HUMAN_GOLD dataset")
    source_refs = {case.source_ref for case in dataset.cases}
    if len(source_refs) != 1:
        raise ValueError("Human Gold preflight cases must reference one source Asset")
    rows: list[NativeMediaPreflightCase] = []
    for case in dataset.cases:
        if case.evaluation_range is None:
            raise ValueError("every native preflight case requires an explicit evaluation_range")
        indices = sampling_policy.sample_indices(case.evaluation_range)
        samples = frame_source.read_frames(Path(analysis_video_path), indices)
        if tuple(item.frame_index for item in samples) != indices:
            raise ValueError("frame source must return exactly the requested frame indices in order")
        rows.append(
            NativeMediaPreflightCase(
                case_id=case.case_id,
                evaluation_range=case.evaluation_range,
                sampled_frame_indices=indices,
                sampled_frame_sha256=tuple(item.png_sha256 for item in samples),
            )
        )
    return NativeMediaPreflightReport(
        source_asset_id=next(iter(source_refs)),
        source_rate=source_rate,
        dataset_id=dataset.dataset_id,
        dataset_revision=dataset.revision,
        dataset_sha256=dataset.to_dict()["dataset_sha256"],
        cases=tuple(rows),
    )


@dataclass(frozen=True, slots=True)
class NativeVisualDetection:
    detector_id: str
    detector_version: str
    marker: DBDVisualMarkerKind | None
    confidence_milli: int
    source_range: SourceFrameRange | None = None
    supporting_frame_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _bounded_text(self.detector_id, field_name="detector_id", maximum=128)
        SemVer.parse(self.detector_version)
        if self.marker is not None and not isinstance(self.marker, DBDVisualMarkerKind):
            raise ValueError("marker must be DBDVisualMarkerKind or None")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.marker is None:
            if self.source_range is not None or self.supporting_frame_indices:
                raise ValueError("abstained detection cannot assert source/support frames")
        else:
            if not isinstance(self.source_range, SourceFrameRange):
                raise ValueError("marker detection requires source_range")
            if not self.supporting_frame_indices:
                raise ValueError("marker detection requires supporting frame indices")
            if tuple(sorted(set(self.supporting_frame_indices))) != self.supporting_frame_indices:
                raise ValueError("supporting_frame_indices must be unique and sorted")

    @property
    def abstained(self) -> bool:
        return self.marker is None


class NativeDBDVisualDetector(Protocol):
    detector_id: str
    detector_version: str

    def detect_case(
        self,
        *,
        samples: tuple[NativeFrameSample, ...],
        evaluation_range: SourceFrameRange,
        source_rate: FrameRate,
    ) -> NativeVisualDetection: ...


@dataclass(frozen=True, slots=True)
class NativePilotCaseResult:
    case_id: str
    sampled_frame_indices: tuple[int, ...]
    sampled_frame_sha256: tuple[str, ...]
    prediction: EventBenchmarkPrediction
    evidence_id: str | None = None
    event_id: str | None = None
    event_revision: int | None = None
    confirmation_state: EventConfirmationState | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "sampled_frame_indices": list(self.sampled_frame_indices),
            "sampled_frame_sha256": list(self.sampled_frame_sha256),
            "prediction": self.prediction.to_dict(),
            "evidence_id": self.evidence_id,
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "confirmation_state": None if self.confirmation_state is None else self.confirmation_state.value,
        }


@dataclass(frozen=True, slots=True)
class NativeMediaPilotReport:
    match_id: str
    source_asset_id: str
    dataset_id: str
    dataset_revision: int
    detector_id: str
    detector_version: str
    cases: tuple[NativePilotCaseResult, ...]
    benchmark: EventBenchmarkReport

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "match_id": self.match_id,
            "source_asset_id": self.source_asset_id,
            "dataset_id": self.dataset_id,
            "dataset_revision": self.dataset_revision,
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "cases": [item.to_dict() for item in self.cases],
            "benchmark": self.benchmark.to_dict(),
            "native_media_evidence": True,
            "production_accuracy_claim_authorized": False,
            "provider_execution_performed": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
        }
        return {**body, "native_pilot_report_sha256": sha256_bytes(canonical_json_bytes(body))}


class DBDNativeMediaPilotRunner:
    """Evaluate one supplied detector against bounded Human Gold media windows."""

    def __init__(
        self,
        *,
        sampling_policy: BoundedFrameSamplingPolicy = BoundedFrameSamplingPolicy(),
        producer: BoundedDBDEventProducer | None = None,
        resolver: DBDEventResolver | None = None,
    ) -> None:
        self.sampling_policy = sampling_policy
        self.producer = producer or BoundedDBDEventProducer(producer="task049.r10b-native-pilot", producer_version="1.0.0")
        self.resolver = resolver or DBDEventResolver()

    @staticmethod
    def _validate_detection(
        detection: NativeVisualDetection,
        *,
        detector: NativeDBDVisualDetector,
        evaluation_range: SourceFrameRange,
        sampled_indices: tuple[int, ...],
    ) -> None:
        if detection.detector_id != detector.detector_id or detection.detector_version != detector.detector_version:
            raise ValueError("detector result identity/version does not match the admitted detector")
        if detection.abstained:
            return
        assert detection.source_range is not None
        if (
            detection.source_range.start_frame < evaluation_range.start_frame
            or detection.source_range.end_frame_exclusive > evaluation_range.end_frame_exclusive
        ):
            raise ValueError("detector source_range must remain inside the Human Gold evaluation window")
        if any(frame not in sampled_indices for frame in detection.supporting_frame_indices):
            raise ValueError("detector support must reference only supplied sampled frames")

    def run(
        self,
        *,
        match: GameMatch,
        analysis_video_path: Path,
        dataset: EventBenchmarkDataset,
        frame_source: NativeFrameSource,
        detector: NativeDBDVisualDetector,
        store: GameIntelligenceStore | None = None,
    ) -> NativeMediaPilotReport:
        if not isinstance(match, GameMatch):
            raise ValueError("match must be GameMatch")
        if dataset.kind is not BenchmarkDatasetKind.HUMAN_GOLD:
            raise ValueError("R10B native pilot requires a HUMAN_GOLD dataset")
        _bounded_text(detector.detector_id, field_name="detector.detector_id", maximum=128)
        SemVer.parse(detector.detector_version)
        if any(case.source_ref != match.source_asset_id for case in dataset.cases):
            raise ValueError("every Human Gold case must reference the Match analysis source Asset")
        if store is not None:
            store.put_match(match)

        case_results: list[NativePilotCaseResult] = []
        predictions: list[EventBenchmarkPrediction] = []
        for case in dataset.cases:
            evaluation_range = case.evaluation_range
            if evaluation_range is None:
                raise ValueError("every R10B case requires an explicit evaluation_range")
            sample_indices = self.sampling_policy.sample_indices(evaluation_range)
            samples = frame_source.read_frames(Path(analysis_video_path), sample_indices)
            if tuple(item.frame_index for item in samples) != sample_indices:
                raise ValueError("frame source must return exactly the requested frame indices in order")
            detection = detector.detect_case(
                samples=samples,
                evaluation_range=evaluation_range,
                source_rate=match.source_rate,
            )
            if not isinstance(detection, NativeVisualDetection):
                raise ValueError("detector must return NativeVisualDetection")
            self._validate_detection(
                detection,
                detector=detector,
                evaluation_range=evaluation_range,
                sampled_indices=sample_indices,
            )

            evidence_id = event_id = None
            event_revision: int | None = None
            confirmation_state: EventConfirmationState | None = None
            if detection.abstained:
                prediction = EventBenchmarkPrediction(
                    case.case_id,
                    None,
                    detection.confidence_milli,
                    abstained=True,
                )
            else:
                assert detection.marker is not None and detection.source_range is not None
                frame_digest = sha256_bytes(
                    canonical_json_bytes(
                        [[item.frame_index, item.png_sha256] for item in samples]
                    )
                )
                evidence = GameEvidence(
                    production_job_id=match.production_job_id,
                    match_id=match.match_id,
                    source_asset_id=match.source_asset_id,
                    producer=detection.detector_id,
                    producer_version=detection.detector_version,
                    evidence_type=GameEvidenceType.VISION,
                    source_range=detection.source_range,
                    confidence_milli=detection.confidence_milli,
                    artifact_ref=f"native-frame-set://{case.case_id}/{frame_digest}",
                )
                candidate = self.producer.from_visual_marker(
                    match_id=match.match_id,
                    marker=detection.marker,
                    source_range=detection.source_range,
                    evidence_refs=(evidence.game_evidence_id,),
                    confidence_milli=detection.confidence_milli,
                )
                resolved = self.resolver.resolve_candidate(
                    match,
                    candidate,
                    {evidence.game_evidence_id: evidence},
                )
                if store is not None:
                    store.append_evidence(evidence)
                    store.append_event(resolved.event)
                evidence_id = evidence.game_evidence_id
                event_id = resolved.event.event_id
                event_revision = resolved.event.revision
                confirmation_state = resolved.event.confirmation_state
                if resolved.event.event_type is GameEventType.UNKNOWN_EVENT:
                    prediction = EventBenchmarkPrediction(
                        case.case_id,
                        None,
                        detection.confidence_milli,
                        abstained=True,
                    )
                else:
                    prediction = EventBenchmarkPrediction(
                        case.case_id,
                        resolved.event.event_type,
                        detection.confidence_milli,
                        resolved.event.source_range,
                    )
            predictions.append(prediction)
            case_results.append(
                NativePilotCaseResult(
                    case_id=case.case_id,
                    sampled_frame_indices=sample_indices,
                    sampled_frame_sha256=tuple(item.png_sha256 for item in samples),
                    prediction=prediction,
                    evidence_id=evidence_id,
                    event_id=event_id,
                    event_revision=event_revision,
                    confirmation_state=confirmation_state,
                )
            )

        benchmark = EventBenchmarkEvaluator.evaluate(
            dataset,
            tuple(predictions),
            native_media_evidence=True,
            production_accuracy_claim_authorized=False,
        )
        if store is not None:
            store.create_checkpoint(
                match.match_id,
                stage="R10B_NATIVE_PILOT",
                state={
                    "dataset_id": dataset.dataset_id,
                    "dataset_revision": dataset.revision,
                    "detector_id": detector.detector_id,
                    "detector_version": detector.detector_version,
                    "native_media_evidence": True,
                    "production_accuracy_claim_authorized": False,
                },
            )
        return NativeMediaPilotReport(
            match_id=match.match_id,
            source_asset_id=match.source_asset_id,
            dataset_id=dataset.dataset_id,
            dataset_revision=dataset.revision,
            detector_id=detector.detector_id,
            detector_version=detector.detector_version,
            cases=tuple(case_results),
            benchmark=benchmark,
        )


__all__ = [
    "BoundedFrameSamplingPolicy",
    "DBDNativeMediaPilotRunner",
    "FFmpegPNGFrameSource",
    "NativeDBDVisualDetector",
    "NativeFrameSample",
    "NativeFrameSource",
    "NativeMediaPilotReport",
    "NativeMediaPreflightCase",
    "NativeMediaPreflightReport",
    "NativePilotCaseResult",
    "NativeVisualDetection",
    "run_native_media_preflight",
]
