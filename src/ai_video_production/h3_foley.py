from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import shutil
import time
import uuid
from typing import Any

from .assets import AssetType, AudioRightsStatus, PermissionState, RightsStatus
from .comfyui import (
    ComfyResourcePolicy,
    ComfyUIClient,
    _admit_comfy_input_staging_disk,
    _history_entry,
    _load_workflow_json,
    _prepare_owned_comfy_subdir,
    _queue_or_resume_comfy_prompt,
    _mark_comfy_failure,
    _request_bound_command,
    _validate_license_authorization_ref,
    _video_descriptors,
    admit_comfy_resources,
    assert_workflow_inputs_available,
    assert_workflow_supported,
    render_workflow_placeholders,
    resolve_comfy_output,
)
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec, sha256_file
from .errors import ProductError, ProductErrorCategory
from .media_probe import FFprobeMediaProbe
from .normalization import FFmpegRunner
from .paths import LogicalPathResolver, SourcePathPolicy
from .serialization import canonical_json_bytes, sha256_bytes
from .store import OperationRecord, SQLiteProductStore
from .task004_manifest import Task004ManifestWriter


class H3FoleyMode(str, Enum):
    STANDARD = "STANDARD"
    FAST_32 = "FAST_32"


class H3FoleyDurationTier(str, Enum):
    STANDARD_1_15 = "STANDARD_1_15"
    EXPERIMENTAL_16_45 = "EXPERIMENTAL_16_45"


@dataclass(frozen=True, slots=True)
class H3FoleyRequest:
    production_job_id: str
    idempotency_key: str
    workflow_path: Path
    substitutions: dict[str, Any]
    prompt: str
    seed: int
    authorize_execution: bool
    license_authorization_ref: str | None
    mode: H3FoleyMode = H3FoleyMode.FAST_32
    target_duration_seconds: int = 5
    width: int = 768
    height: int = 432
    reference_audio_asset_id: str | None = None
    accept_experimental_low_resolution_audio: bool = False
    accept_experimental_long_duration: bool = False
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 3600
    ffmpeg_timeout_seconds: int = 300

    @property
    def effective_width(self) -> int:
        return 32 if self.mode is H3FoleyMode.FAST_32 else self.width

    @property
    def effective_height(self) -> int:
        return 32 if self.mode is H3FoleyMode.FAST_32 else self.height

    @property
    def duration_tier(self) -> H3FoleyDurationTier:
        return H3FoleyDurationTier.STANDARD_1_15 if self.target_duration_seconds <= 15 else H3FoleyDurationTier.EXPERIMENTAL_16_45


@dataclass(frozen=True, slots=True)
class H3FoleyResult:
    operation: OperationRecord
    asset_id: str
    manifest_uri: str
    evidence_uri: str
    prompt_id: str


class H3FoleyService:
    """MiniMax H3 audio-only/Foley experimental path through ComfyUI.

    The FAST_32 strategy is intentionally labeled experimental community-derived
    behavior. The Product never upgrades it to an official model guarantee.
    """

    _RESERVED = {"PROMPT", "SEED", "WIDTH", "HEIGHT", "DURATION_SECONDS", "REFERENCE_AUDIO"}

    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        client: ComfyUIClient,
        workflow_policy: SourcePathPolicy,
        comfy_output_root: Path,
        staging_root: Path,
        comfy_input_root: Path | None = None,
        resource_policy: ComfyResourcePolicy | None = None,
        media_probe: FFprobeMediaProbe | None = None,
        ffmpeg: FFmpegRunner | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.client = client
        self.workflow_policy = workflow_policy
        self.comfy_output_root = comfy_output_root.resolve(strict=True)
        self.staging_root = staging_root.resolve(strict=False)
        self.comfy_input_root = comfy_input_root.resolve(strict=True) if comfy_input_root is not None else None
        self.resource_policy = resource_policy or ComfyResourcePolicy()
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.ffmpeg = ffmpeg or FFmpegRunner()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)

    def _completed(self, request: H3FoleyRequest, operation: OperationRecord) -> H3FoleyResult:
        manifest = self.store.find_manifest_by_operation(operation.operation_id, "h3-foley-manifest")
        if manifest is None:
            raise ProductError("ERR_INTEGRITY_H3_FOLEY_MANIFEST_MISSING", "completed H3 Foley manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
        doc = self.manifests.load_verified(manifest)
        ids = [a["asset_id"] for a in doc["payload"]["output_assets"]]
        if len(ids) != 1:
            raise ProductError("ERR_INTEGRITY_H3_FOLEY_RESULT", "H3 Foley manifest must contain one output Asset", ProductErrorCategory.DATA_INTEGRITY)
        return H3FoleyResult(operation, ids[0], manifest.uri, f"job://{request.production_job_id}/evidence/task004.jsonl", doc["payload"]["details"].get("prompt_id", ""))

    def _validate_request(self, request: H3FoleyRequest) -> str:
        if not request.authorize_execution:
            raise ProductError("ERR_AUTH_H3_FOLEY_EXECUTION_REQUIRED", "H3 Foley generation requires explicit execution authorization", ProductErrorCategory.AUTHORIZATION)
        license_ref = _validate_license_authorization_ref(request.license_authorization_ref)
        if not license_ref:
            raise ProductError("ERR_AUTH_H3_FOLEY_MODEL_LICENSE", "MiniMax H3 Foley execution requires explicit model-license acknowledgement", ProductErrorCategory.AUTHORIZATION)
        if not request.prompt.strip() or len(request.prompt) > 20_000 or "\x00" in request.prompt:
            raise ProductError("ERR_INPUT_H3_FOLEY_PROMPT", "H3 Foley prompt must be non-empty bounded text", ProductErrorCategory.VALIDATION)
        if request.seed < 0 or request.seed > 2**63 - 1:
            raise ProductError("ERR_INPUT_H3_FOLEY_SEED", "H3 Foley seed is out of range", ProductErrorCategory.VALIDATION)
        if not 1 <= request.target_duration_seconds <= 45:
            raise ProductError("ERR_INPUT_H3_FOLEY_DURATION", "TASK-004 H3 Foley duration must be 1-45 seconds", ProductErrorCategory.VALIDATION)
        if request.target_duration_seconds > 15 and not request.accept_experimental_long_duration:
            raise ProductError("ERR_AUTH_H3_FOLEY_EXPERIMENTAL_DURATION", "H3 Foley duration above 15 seconds is experimental and requires explicit acknowledgement", ProductErrorCategory.AUTHORIZATION)
        if request.mode is H3FoleyMode.FAST_32 and not request.accept_experimental_low_resolution_audio:
            raise ProductError("ERR_AUTH_H3_FOLEY_FAST32_EXPERIMENTAL", "32x32 H3 audio generation is community-derived experimental behavior and requires explicit acknowledgement", ProductErrorCategory.AUTHORIZATION)
        if request.mode is H3FoleyMode.STANDARD:
            if request.width < 32 or request.height < 32 or request.width > 4096 or request.height > 4096:
                raise ProductError("ERR_INPUT_H3_FOLEY_DIMENSIONS", "standard H3 Foley dimensions must be within 32..4096", ProductErrorCategory.VALIDATION)
        if self._RESERVED.intersection(request.substitutions):
            raise ProductError("ERR_INPUT_H3_FOLEY_RESERVED_SUBSTITUTION", "caller substitutions must not override managed H3 Foley fields", ProductErrorCategory.VALIDATION)
        if not 0.1 <= request.poll_interval_seconds <= 30 or not 1 <= request.completion_timeout_seconds <= 86400:
            raise ValueError("invalid H3 Foley polling configuration")
        if not 1 <= request.ffmpeg_timeout_seconds <= 7200:
            raise ValueError("invalid H3 Foley ffmpeg timeout")
        return license_ref

    def _stage_audio_reference(self, request: H3FoleyRequest, operation: OperationRecord) -> tuple[tuple[str, ...], tuple[str, ...], Path | None, dict[str, str]]:
        if request.reference_audio_asset_id is None:
            return (), (), None, {}
        if self.comfy_input_root is None:
            raise ProductError("ERR_PROVIDER_COMFY_INPUT_ROOT_REQUIRED", "H3 Foley audio reference requires a configured ComfyUI input root", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        asset = self.store.get_asset(request.reference_audio_asset_id)
        if asset.production_job_id != request.production_job_id:
            raise ProductError("ERR_SECURITY_H3_FOLEY_REFERENCE_SCOPE", "H3 Foley audio reference belongs to another Job", ProductErrorCategory.SECURITY)
        if asset.asset_type not in {AssetType.AUDIO, AssetType.SFX, AssetType.BGM}:
            raise ProductError("ERR_INPUT_H3_FOLEY_REFERENCE_TYPE", "H3 Foley reference must be AUDIO/SFX/BGM", ProductErrorCategory.VALIDATION)
        if not asset.derivative_use_allowed:
            raise ProductError("ERR_AUTH_H3_FOLEY_REFERENCE_RIGHTS", "H3 Foley reference is not authorized for derivative generation", ProductErrorCategory.AUTHORIZATION)
        source = self.resolver.resolve(asset.logical_uri)
        if not isinstance(source, Path) or not source.exists() or source.is_symlink() or sha256_file(source) != asset.checksum:
            raise ProductError("ERR_INTEGRITY_H3_FOLEY_REFERENCE", "H3 Foley audio reference is missing, symlinked or tampered", ProductErrorCategory.DATA_INTEGRITY)
        _admit_comfy_input_staging_disk(self.comfy_input_root, source.stat().st_size, self.resource_policy)
        relative_dir = Path("bai-task004-h3-foley") / request.production_job_id / operation.operation_id
        target_dir = _prepare_owned_comfy_subdir(self.comfy_input_root, relative_dir)
        try:
            suffix = source.suffix.lower() or ".wav"
            target = target_dir / f"reference-audio{suffix}"
            shutil.copyfile(source, target)
            if sha256_file(target) != asset.checksum:
                raise ProductError("ERR_INTEGRITY_H3_FOLEY_REFERENCE_COPY", "H3 Foley reference copy checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            return (asset.logical_uri,), (asset.checksum,), target_dir, {"REFERENCE_AUDIO": (relative_dir / target.name).as_posix()}
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

    def generate(self, request: H3FoleyRequest) -> H3FoleyResult:
        license_ref = self._validate_request(request)
        workflow_path = self.workflow_policy.authorize_file(request.workflow_path)
        workflow_raw = _load_workflow_json(workflow_path)
        request_command = _request_bound_command("LOCAL_H3_FOLEY", {
            "workflow_checksum": sha256_bytes(canonical_json_bytes(workflow_raw)),
            "substitutions": request.substitutions,
            "prompt_checksum": sha256_bytes(request.prompt.encode("utf-8")),
            "seed": request.seed, "mode": request.mode.value,
            "target_duration_seconds": request.target_duration_seconds,
            "width": request.width, "height": request.height,
            "reference_audio_asset_id": request.reference_audio_asset_id,
            "experimental_low_resolution": request.accept_experimental_low_resolution_audio,
            "experimental_long_duration": request.accept_experimental_long_duration,
            "license_authorization_ref_checksum": sha256_bytes(license_ref.encode("utf-8")),
        })
        operation, _ = self.store.reserve_operation(request.production_job_id, request_command, request.idempotency_key)
        if operation.status == "COMPLETED":
            return self._completed(request, operation)
        reference_root: Path | None = None
        source_refs: tuple[str, ...] = ()
        source_checksums: tuple[str, ...] = ()
        prompt_id = ""
        dispatched = bool(operation.result_ref)
        job_stage = self.staging_root / request.production_job_id / operation.operation_id
        job_stage.mkdir(parents=True, exist_ok=True)
        try:
            source_refs, source_checksums, reference_root, reference_subs = self._stage_audio_reference(request, operation)
            substitutions = dict(request.substitutions)
            substitutions.update(reference_subs)
            substitutions.update({
                "PROMPT": request.prompt,
                "SEED": request.seed,
                "WIDTH": request.effective_width,
                "HEIGHT": request.effective_height,
                "DURATION_SECONDS": request.target_duration_seconds,
            })
            workflow = render_workflow_placeholders(workflow_raw, substitutions)
            object_info = self.client.object_info()
            assert_workflow_supported(workflow, object_info)
            assert_workflow_inputs_available(workflow, object_info)
            stats = self.client.system_stats()
            resource = admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
            operation, prompt_id, _resumed = _queue_or_resume_comfy_prompt(
                store=self.store, operation=operation, client=self.client, workflow=workflow
            )
            dispatched = True
            deadline = time.monotonic() + request.completion_timeout_seconds
            entry: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                entry = _history_entry(self.client.history(prompt_id), prompt_id)
                if entry is not None:
                    status = entry.get("status")
                    if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                        raise ProductError("ERR_PROVIDER_H3_FOLEY_FAILED", "ComfyUI H3 Foley workflow reported failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                    if _video_descriptors(entry):
                        break
                time.sleep(request.poll_interval_seconds)
            else:
                raise ProductError("ERR_PROVIDER_H3_FOLEY_TIMEOUT", "H3 Foley generation timed out", ProductErrorCategory.TIMEOUT, retryable=True)
            assert entry is not None
            videos = _video_descriptors(entry)
            if len(videos) != 1:
                raise ProductError("ERR_PROVIDER_H3_FOLEY_AMBIGUOUS", "H3 Foley workflow must expose exactly one canonical video container output", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"video_count": len(videos)})
            container_path = resolve_comfy_output(self.comfy_output_root, videos[0])
            container_probe = self.media_probe.probe(container_path)
            if not container_probe.has_audio:
                raise ProductError("ERR_INTEGRITY_H3_FOLEY_NO_AUDIO", "H3 Foley output container contains no audio stream", ProductErrorCategory.DATA_INTEGRITY)
            wav_path = job_stage / "h3-foley.wav"
            ffmpeg_diag = self.ffmpeg.run([
                "-i", str(container_path), "-vn", "-c:a", "pcm_s16le", "-ar", "48000", "-y", str(wav_path)
            ], timeout_seconds=request.ffmpeg_timeout_seconds)
            audio_probe = self.media_probe.probe(wav_path)
            if not audio_probe.has_audio:
                raise ProductError("ERR_INTEGRITY_H3_FOLEY_EXTRACT", "extracted H3 Foley WAV contains no audio stream", ProductErrorCategory.DATA_INTEGRITY)
            audio_streams = [s for s in audio_probe.streams if s.get("codec_type") == "audio"]
            if not audio_streams or audio_streams[0].get("sample_rate") != 48000:
                raise ProductError("ERR_INTEGRITY_H3_FOLEY_SAMPLE_RATE", "H3 Foley canonical audio derivative must be 48 kHz", ProductErrorCategory.DATA_INTEGRITY)
            raw_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow_raw))
            rendered_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow))
            prompt_checksum = sha256_bytes(request.prompt.encode("utf-8"))
            provenance = {
                "provider": "COMFYUI_MINIMAX_H3_FOLEY",
                "model_family": "MiniMax-H3",
                "model_license_id": "MiniMax-H3-Community-License-Agreement",
                "license_authorization_ref_checksum": sha256_bytes(license_ref.encode("utf-8")),
                "prompt_checksum": prompt_checksum,
                "workflow_checksum": raw_workflow_checksum,
                "rendered_workflow_checksum": rendered_workflow_checksum,
                "seed": request.seed,
                "mode": request.mode.value,
                "width": request.effective_width,
                "height": request.effective_height,
                "target_duration_seconds": request.target_duration_seconds,
                "duration_tier": request.duration_tier.value,
                "community_derived_fast_path": request.mode is H3FoleyMode.FAST_32,
                "official_capability_claim": False,
                "reference_audio_asset_id": request.reference_audio_asset_id,
                "ffmpeg_diagnostics": ffmpeg_diag,
            }
            restrictions = ["MODEL_LICENSE_REVIEW_REQUIRED", "HUMAN_AUDIO_QA_REQUIRED"]
            if request.mode is H3FoleyMode.FAST_32:
                restrictions.append("EXPERIMENTAL_COMMUNITY_FAST_PATH")
            if request.duration_tier is H3FoleyDurationTier.EXPERIMENTAL_16_45:
                restrictions.append("EXPERIMENTAL_DURATION")
            asset = self.publisher.publish(
                wav_path,
                DerivedAssetSpec(
                    production_job_id=request.production_job_id,
                    namespace="generated-sfx",
                    asset_type=AssetType.SFX,
                    owner="LOCAL_AI_OUTPUT",
                    rights_status=RightsStatus.UNKNOWN,
                    commercial_use=PermissionState.UNKNOWN,
                    derivative_allowed=PermissionState.UNKNOWN,
                    reuse_allowed=PermissionState.UNKNOWN,
                    audio_rights_status=AudioRightsStatus.REVIEW,
                    generation_provenance=provenance,
                    source_ref=request.reference_audio_asset_id,
                    media_metadata=audio_probe.to_dict(),
                    publication_restrictions=tuple(restrictions),
                ),
                operation_id=operation.operation_id,
            )
            details = dict(provenance)
            details.update({
                "prompt_id": prompt_id,
                "resource_admission": resource,
                "source_refs": list(source_refs),
                "source_container_media": container_probe.to_dict(),
                "output_binding": {"asset_id": asset.asset_id, "checksum": asset.checksum},
            })
            manifest = self.manifests.write(
                job_id=request.production_job_id,
                operation_id=operation.operation_id,
                manifest_type="h3-foley-manifest",
                schema_id="ai-video.h3-foley-manifest",
                lane="LOCAL_AUDIO_AI",
                operation_kind="MINIMAX_H3_FOLEY",
                source_refs=source_refs,
                input_checksums=(raw_workflow_checksum, rendered_workflow_checksum, prompt_checksum, *source_checksums),
                output_assets=(asset,),
                details=details,
                evidence_category="H3_FOLEY_GENERATION",
                producer_component="comfyui-minimax-h3-foley-adapter",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=asset.asset_id)
            return H3FoleyResult(operation, asset.asset_id, manifest.manifest.uri, manifest.evidence_uri, prompt_id)
        except Exception as exc:
            _mark_comfy_failure(self.store, operation, exc, dispatched=dispatched)
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_H3_FOLEY_FAILED", "H3 Foley generation failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
        finally:
            if reference_root is not None:
                shutil.rmtree(reference_root, ignore_errors=True)
            shutil.rmtree(job_stage, ignore_errors=True)
