from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .assets import AssetRecord, AssetType, PermissionState
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec, sha256_file
from .errors import ProductError, ProductErrorCategory
from .media_probe import FFprobeMediaProbe
from .paths import LogicalPathResolver
from .state import JobStateService, ProductionJobState
from .store import OperationRecord, SQLiteProductStore
from .task004_manifest import Task004ManifestWriter
from .timebase import FFprobeTimingProbe, FrameRate, TimingInspection, TimingKind

_TASK004_VERSION = "0.4.0"


@dataclass(frozen=True, slots=True)
class NormalizationProfile:
    target_frame_rate: FrameRate = FrameRate(30000, 1001)
    audio_sample_rate: int = 48_000
    force_cfr_proxy: bool = False
    max_duration_drift_us: int = 100_000
    ffmpeg_timeout_seconds: int = 900

    def __post_init__(self) -> None:
        if self.audio_sample_rate != 48_000:
            raise ValueError("TASK-004 analysis audio contract is fixed at 48000 Hz")
        if not 0 <= self.max_duration_drift_us <= 5_000_000:
            raise ValueError("max_duration_drift_us out of range")
        if not 1 <= self.ffmpeg_timeout_seconds <= 7200:
            raise ValueError("ffmpeg_timeout_seconds out of range")


@dataclass(frozen=True, slots=True)
class NormalizationRequest:
    production_job_id: str
    source_asset_id: str
    idempotency_key: str
    profile: NormalizationProfile = NormalizationProfile()


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    operation: OperationRecord
    source_asset: AssetRecord
    timing: TimingInspection
    video_reference_asset: AssetRecord | None
    proxy_asset: AssetRecord | None
    analysis_audio_asset: AssetRecord | None
    manifest_uri: str
    evidence_uri: str


class FFmpegRunner:
    def __init__(self, executable: str = "ffmpeg") -> None:
        if not executable.strip():
            raise ValueError("ffmpeg executable must be non-empty")
        self.executable = executable

    def run(self, args: list[str], *, timeout_seconds: int) -> dict[str, Any]:
        argv = [self.executable, "-nostdin", "-hide_banner", "-loglevel", "error", *args]
        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise ProductError(
                "ERR_PROVIDER_FFMPEG_NOT_FOUND", "ffmpeg executable is not available",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProductError(
                "ERR_PROVIDER_FFMPEG_TIMEOUT", "ffmpeg transformation timed out",
                ProductErrorCategory.TIMEOUT, retryable=True,
                details={"timeout_seconds": timeout_seconds},
            ) from exc
        stderr_bytes = proc.stderr.encode("utf-8", errors="replace")
        diag = {
            "exit_code": proc.returncode,
            "stderr_sha256": "sha256:" + hashlib.sha256(stderr_bytes).hexdigest(),
            # Intentionally no raw stderr/path in canonical diagnostics.
        }
        if proc.returncode != 0:
            raise ProductError(
                "ERR_PROVIDER_FFMPEG_FAILED", "ffmpeg transformation failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details=diag,
            )
        return diag


class MediaNormalizationService:
    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        media_probe: FFprobeMediaProbe | None = None,
        timing_probe: FFprobeTimingProbe | None = None,
        ffmpeg: FFmpegRunner | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.timing_probe = timing_probe or FFprobeTimingProbe()
        self.ffmpeg = ffmpeg or FFmpegRunner()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)

    def _source(self, request: NormalizationRequest) -> tuple[AssetRecord, Path]:
        source = self.store.get_asset(request.source_asset_id)
        if source.production_job_id != request.production_job_id:
            raise ProductError("ERR_SECURITY_ASSET_JOB_MISMATCH", "source Asset belongs to another Job", ProductErrorCategory.SECURITY)
        if source.asset_type not in {AssetType.VIDEO, AssetType.AUDIO, AssetType.GENERATED_VIDEO}:
            raise ProductError("ERR_INPUT_NORMALIZE_ASSET_TYPE", "normalization requires video/audio Asset", ProductErrorCategory.VALIDATION)
        if source.derivative_allowed is PermissionState.DENIED:
            raise ProductError(
                "ERR_POLICY_DERIVATIVE_DENIED", "source explicitly forbids derivative processing",
                ProductErrorCategory.AUTHORIZATION,
            )
        path = self.resolver.resolve(source.logical_uri)
        if not isinstance(path, Path) or not path.exists():
            raise ProductError("ERR_INTEGRITY_SOURCE_ASSET_MISSING", "registered source Asset file is missing", ProductErrorCategory.DATA_INTEGRITY)
        if path.is_symlink():
            raise ProductError("ERR_SECURITY_SOURCE_ASSET_SYMLINK", "registered source Asset symlink is forbidden", ProductErrorCategory.SECURITY)
        if sha256_file(path) != source.checksum:
            raise ProductError("ERR_INTEGRITY_SOURCE_ASSET_CHECKSUM_MISMATCH", "registered source Asset checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        return source, path

    @staticmethod
    def _derived_spec(source: AssetRecord, *, namespace: str, asset_type: AssetType, metadata: dict[str, Any], provenance: dict[str, Any]) -> DerivedAssetSpec:
        return DerivedAssetSpec(
            production_job_id=source.production_job_id,
            namespace=namespace,
            asset_type=asset_type,
            owner=source.owner,
            rights_status=source.rights_status,
            retention_class=source.retention_class,
            commercial_use=source.commercial_use,
            derivative_allowed=source.derivative_allowed,
            reuse_allowed=source.reuse_allowed,
            audio_rights_status=source.audio_rights_status,
            generation_provenance=provenance,
            media_metadata=metadata,
            source_ref=source.asset_id,
            source_project=source.source_project,
            attribution=source.attribution,
            publication_restrictions=source.publication_restrictions,
        )

    @staticmethod
    def _duration_drift(a: int | None, b: int | None) -> int | None:
        if a is None or b is None:
            return None
        return abs(a - b)

    def _load_completed(self, request: NormalizationRequest, operation: OperationRecord) -> NormalizationResult:
        manifest = self.store.find_manifest_by_operation(operation.operation_id, "normalization-manifest")
        if manifest is None:
            raise ProductError("ERR_INTEGRITY_NORMALIZATION_MANIFEST_MISSING", "completed normalization manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
        doc = self.manifests.load_verified(manifest)
        payload = doc["payload"]
        by_id = {a.asset_id: a for a in self.store.list_assets(request.production_job_id)}
        details = payload["details"]
        source = self.store.get_asset(request.source_asset_id)
        timing_dict = details["source_timing"]
        timing = TimingInspection(
            TimingKind(timing_dict["kind"]), timing_dict.get("duration_us"),
            FrameRate.parse(timing_dict["avg_frame_rate"]) if timing_dict.get("avg_frame_rate") else None,
            FrameRate.parse(timing_dict["nominal_frame_rate"]) if timing_dict.get("nominal_frame_rate") else None,
            timing_dict.get("time_base"), int(timing_dict.get("sampled_packet_count", 0)),
            int(timing_dict.get("sampled_delta_count", 0)), int(timing_dict.get("variable_delta_count", 0)),
            timing_dict.get("min_delta_us"), timing_dict.get("max_delta_us"), timing_dict.get("reason", "replay"),
        )
        return NormalizationResult(
            operation, source, timing,
            by_id.get(details.get("video_reference_asset_id")),
            by_id.get(details.get("proxy_asset_id")),
            by_id.get(details.get("analysis_audio_asset_id")),
            manifest.uri,
            f"job://{request.production_job_id}/evidence/task004.jsonl",
        )

    def normalize(self, request: NormalizationRequest) -> NormalizationResult:
        operation, _ = self.store.reserve_operation(request.production_job_id, "MEDIA_NORMALIZE", request.idempotency_key)
        if operation.status == "COMPLETED":
            return self._load_completed(request, operation)

        source, source_path = self._source(request)
        state = self.store.get_job_state(request.production_job_id)
        if state.state not in {ProductionJobState.INGESTING, ProductionJobState.NORMALIZING}:
            raise ProductError(
                "ERR_STATE_NORMALIZATION_NOT_ALLOWED",
                f"normalization is not allowed while job state is {state.state.value}",
                ProductErrorCategory.STATE,
            )
        if state.state is ProductionJobState.INGESTING:
            JobStateService(self.store).transition(
                request.production_job_id, ProductionJobState.NORMALIZING, expected_version=state.state_version,
            )
        operation = self.store.update_operation_status(operation.operation_id, "IN_PROGRESS", increment_attempt=True)

        try:
            structural = self.media_probe.probe(source_path)
            timing = self.timing_probe.inspect(source_path)
            proxy: AssetRecord | None = None
            audio: AssetRecord | None = None
            with tempfile.TemporaryDirectory(prefix="bai-task004-normalize-") as tmp:
                work = Path(tmp)
                wav: Path | None = None
                wav_probe = None
                proxy_path: Path | None = None
                proxy_probe = None
                fps = request.profile.target_frame_rate.to_rational()

                # Produce and QA the complete requested output batch before any canonical publication.
                if structural.has_audio:
                    wav = work / "analysis-48k.wav"
                    self.ffmpeg.run([
                        "-i", str(source_path), "-vn", "-map", "0:a:0", "-ar", "48000", "-c:a", "pcm_s16le", "-y", str(wav),
                    ], timeout_seconds=request.profile.ffmpeg_timeout_seconds)
                    wav_probe = self.media_probe.probe(wav)
                    if not wav_probe.has_audio:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_AUDIO_MISSING", "normalized WAV has no audio stream", ProductErrorCategory.DATA_INTEGRITY)
                    audio_streams = [s for s in wav_probe.streams if s.get("codec_type") == "audio"]
                    if not audio_streams or audio_streams[0].get("sample_rate") != 48_000:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_AUDIO_RATE", "normalized WAV is not 48 kHz", ProductErrorCategory.DATA_INTEGRITY)
                    drift = self._duration_drift(structural.duration_us, wav_probe.duration_us)
                    if drift is not None and drift > request.profile.max_duration_drift_us:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_AUDIO_DURATION", "normalized audio duration drift exceeds tolerance", ProductErrorCategory.DATA_INTEGRITY, details={"drift_us": drift})

                needs_proxy = structural.has_video and (request.profile.force_cfr_proxy or timing.kind is TimingKind.VFR)
                if needs_proxy:
                    proxy_path = work / "cfr-proxy.mp4"
                    self.ffmpeg.run([
                        "-i", str(source_path), "-map", "0:v:0", "-map", "0:a?", "-vf", f"fps={fps}",
                        "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                        "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-y", str(proxy_path),
                    ], timeout_seconds=request.profile.ffmpeg_timeout_seconds)
                    proxy_probe = self.media_probe.probe(proxy_path)
                    proxy_timing = self.timing_probe.inspect(proxy_path)
                    if not proxy_probe.has_video or proxy_timing.kind is not TimingKind.CFR:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_PROXY_NOT_CFR", "proxy did not validate as CFR video", ProductErrorCategory.DATA_INTEGRITY)
                    actual_rate = proxy_timing.avg_frame_rate or proxy_timing.nominal_frame_rate
                    if actual_rate != request.profile.target_frame_rate:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_PROXY_RATE", "proxy frame rate differs from target", ProductErrorCategory.DATA_INTEGRITY, details={"expected": fps, "actual": actual_rate.to_rational() if actual_rate else None})
                    drift = self._duration_drift(structural.duration_us, proxy_probe.duration_us)
                    if drift is not None and drift > request.profile.max_duration_drift_us:
                        raise ProductError("ERR_INTEGRITY_NORMALIZED_PROXY_DURATION", "proxy duration drift exceeds tolerance", ProductErrorCategory.DATA_INTEGRITY, details={"drift_us": drift})

                if wav is not None and wav_probe is not None:
                    audio = self.publisher.publish(
                        wav,
                        self._derived_spec(
                            source, namespace="analysis-audio", asset_type=AssetType.AUDIO,
                            metadata=wav_probe.to_dict(),
                            provenance={"kind": "TASK004_NORMALIZED_AUDIO", "sample_rate": 48000, "source_asset_id": source.asset_id},
                        ),
                        operation_id=operation.operation_id,
                    )
                if proxy_path is not None and proxy_probe is not None:
                    proxy = self.publisher.publish(
                        proxy_path,
                        self._derived_spec(
                            source, namespace="cfr-proxy", asset_type=AssetType.VIDEO,
                            metadata=proxy_probe.to_dict(),
                            provenance={"kind": "TASK004_CFR_PROXY", "target_frame_rate": fps, "source_asset_id": source.asset_id},
                        ),
                        operation_id=operation.operation_id,
                    )

            video_reference = proxy if proxy is not None else (source if structural.has_video else None)
            output_assets = tuple(x for x in (proxy, audio) if x is not None)
            details = {
                "source_asset_id": source.asset_id,
                "source_timing": timing.to_dict(),
                "target_frame_rate": request.profile.target_frame_rate.to_rational(),
                "proxy_required": proxy is not None,
                "proxy_asset_id": proxy.asset_id if proxy else None,
                "analysis_audio_asset_id": audio.asset_id if audio else None,
                "video_reference_asset_id": video_reference.asset_id if video_reference else None,
                "time_mapping_handoff": {
                    "mapping_kind": "WHOLE_FILE_AFFINE",
                    "source_start_us": 0,
                    "normalized_start_us": 0,
                    "source_duration_us": structural.duration_us,
                    "normalized_duration_us": video_reference.media_metadata.get("duration_us") if video_reference else structural.duration_us,
                    "source_rate": (timing.avg_frame_rate or timing.nominal_frame_rate).to_rational() if (timing.avg_frame_rate or timing.nominal_frame_rate) else None,
                    "normalized_rate": request.profile.target_frame_rate.to_rational() if proxy else ((timing.avg_frame_rate or timing.nominal_frame_rate).to_rational() if (timing.avg_frame_rate or timing.nominal_frame_rate) else None),
                    "owner_task": "TASK-022",
                },
            }
            manifest = self.manifests.write(
                job_id=request.production_job_id,
                operation_id=operation.operation_id,
                manifest_type="normalization-manifest",
                schema_id="ai-video.normalization-manifest",
                lane="TIMEBASE_NORMALIZATION",
                operation_kind="MEDIA_NORMALIZE",
                source_refs=(source.logical_uri,),
                input_checksums=(source.checksum,),
                output_assets=output_assets,
                details=details,
                evidence_category="MEDIA_NORMALIZATION",
                producer_component="media-normalization-service",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=manifest.manifest.manifest_id)
            return NormalizationResult(operation, source, timing, video_reference, proxy, audio, manifest.manifest.uri, manifest.evidence_uri)
        except Exception as exc:
            code = exc.code if isinstance(exc, ProductError) else "ERR_INTERNAL_MEDIA_NORMALIZATION_FAILED"
            self.store.update_operation_status(operation.operation_id, "FAILED", last_error_code=code)
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_MEDIA_NORMALIZATION_FAILED", "media normalization failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
