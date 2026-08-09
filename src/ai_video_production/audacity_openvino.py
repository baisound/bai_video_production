from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

from .assets import AssetRecord, AssetType, PermissionState
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec, sha256_file
from .errors import ProductError, ProductErrorCategory
from .media_probe import FFprobeMediaProbe
from .paths import LogicalPathResolver
from .serialization import canonical_json_bytes, sha256_bytes
from .store import OperationRecord, SQLiteProductStore
from .task004_manifest import Task004ManifestWriter


class AudioAiOperation(str, Enum):
    NOISE_SUPPRESSION = "NOISE_SUPPRESSION"
    MUSIC_SEPARATION = "MUSIC_SEPARATION"


class SeparationMode(str, Enum):
    TWO_STEM = "2_STEM"
    FOUR_STEM = "4_STEM"


@dataclass(frozen=True, slots=True)
class AudioAiRequest:
    production_job_id: str
    source_asset_id: str
    idempotency_key: str
    operation: AudioAiOperation
    authorize_execution: bool
    separation_mode: SeparationMode | None = None
    effect_parameters: dict[str, Any] | None = None
    timeout_seconds: int = 1800


@dataclass(frozen=True, slots=True)
class AudioAiResult:
    operation: OperationRecord
    output_assets: tuple[AssetRecord, ...]
    roles: tuple[str, ...]
    manifest_uri: str
    evidence_uri: str
    capability_report: dict[str, Any]


class AudacityOpenVinoService:
    """BAI-owned supervisor/adapter. Intel GPL plugin remains external in Audacity."""

    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        media_probe: FFprobeMediaProbe | None = None,
        worker_runner: Callable[[dict[str, Any], Path, int], dict[str, Any]] | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)
        self.worker_runner = worker_runner or self._run_worker

    def _run_worker(self, request: dict[str, Any], work_root: Path, timeout_seconds: int) -> dict[str, Any]:
        work_root.mkdir(parents=True, exist_ok=True)
        req = work_root / "request.json"
        report = work_root / "report.json"
        req.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        progress = work_root / "progress.json"
        progress.unlink(missing_ok=True)
        try:
            proc = subprocess.run(
                [
                    sys.executable, "-m", "ai_video_production.audacity_openvino_worker",
                    "--request", str(req), "--report", str(report), "--progress", str(progress),
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                timeout=timeout_seconds, check=False, shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            details: dict[str, Any] = {"timeout_seconds": timeout_seconds}
            if progress.exists():
                try:
                    progress_value = json.loads(progress.read_text(encoding="utf-8"))
                    if isinstance(progress_value, dict):
                        details["progress"] = progress_value
                except (OSError, json.JSONDecodeError):
                    pass
            raise ProductError(
                "ERR_PROVIDER_AUDACITY_OPENVINO_TIMEOUT",
                "Audacity OpenVINO worker timed out",
                ProductErrorCategory.TIMEOUT,
                retryable=True,
                details=details,
            ) from exc
        if not report.exists():
            raise ProductError("ERR_PROVIDER_AUDACITY_OPENVINO_REPORT_MISSING", "Audacity OpenVINO worker did not produce a report", ProductErrorCategory.EXTERNAL_DEPENDENCY, details={"exit_code": proc.returncode})
        try:
            value = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProductError("ERR_PROVIDER_AUDACITY_OPENVINO_REPORT_INVALID", "Audacity OpenVINO worker report is invalid JSON", ProductErrorCategory.EXTERNAL_DEPENDENCY) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_PROVIDER_AUDACITY_OPENVINO_REPORT_INVALID", "Audacity OpenVINO worker report must be an object", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return value

    def capability_report(self, *, timeout_seconds: int = 120, work_root: Path) -> dict[str, Any]:
        report = self.worker_runner({"operation": "CAPABILITY"}, work_root, timeout_seconds)
        if report.get("ok") is False:
            self._raise_report_error(report)
        return report

    @staticmethod
    def _raise_report_error(report: dict[str, Any]) -> None:
        code = str(report.get("error_code") or "ERR_PROVIDER_AUDACITY_OPENVINO_FAILED")
        category_name = str(report.get("category") or "EXTERNAL_DEPENDENCY")
        try:
            category = ProductErrorCategory(category_name)
        except ValueError:
            category = ProductErrorCategory.EXTERNAL_DEPENDENCY
        details = {
            key: report[key]
            for key in ("command_id", "phase", "reply_sha256")
            if isinstance(report.get(key), str)
        }
        raise ProductError(code if code.startswith("ERR_") else "ERR_PROVIDER_AUDACITY_OPENVINO_FAILED", str(report.get("message") or "Audacity/OpenVINO operation failed"), category, retryable=category in {ProductErrorCategory.TIMEOUT, ProductErrorCategory.TRANSIENT, ProductErrorCategory.EXTERNAL_DEPENDENCY}, details=details)

    def _source(self, request: AudioAiRequest) -> tuple[AssetRecord, Path]:
        asset = self.store.get_asset(request.source_asset_id)
        if asset.production_job_id != request.production_job_id:
            raise ProductError("ERR_SECURITY_ASSET_JOB_MISMATCH", "audio AI source Asset belongs to another Job", ProductErrorCategory.SECURITY)
        if asset.asset_type not in {AssetType.AUDIO, AssetType.BGM, AssetType.SFX}:
            raise ProductError("ERR_INPUT_AUDIO_AI_SOURCE_TYPE", "OpenVINO audio processing requires an audio Asset", ProductErrorCategory.VALIDATION)
        if asset.derivative_allowed is PermissionState.DENIED:
            raise ProductError("ERR_POLICY_DERIVATIVE_DENIED", "audio AI source explicitly forbids derivative processing", ProductErrorCategory.AUTHORIZATION)
        path = self.resolver.resolve(asset.logical_uri)
        if not isinstance(path, Path) or not path.exists() or path.is_symlink() or sha256_file(path) != asset.checksum:
            raise ProductError("ERR_INTEGRITY_AUDIO_AI_SOURCE", "audio AI source Asset is missing, symlinked, or tampered", ProductErrorCategory.DATA_INTEGRITY)
        return asset, path

    def _load_completed(self, request: AudioAiRequest, operation: OperationRecord) -> AudioAiResult:
        manifest = self.store.find_manifest_by_operation(operation.operation_id, "local-audio-ai-manifest")
        if manifest is None:
            raise ProductError("ERR_INTEGRITY_LOCAL_AUDIO_MANIFEST_MISSING", "completed local-audio manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
        doc = self.manifests.load_verified(manifest)
        outputs = tuple(self.store.get_asset(item["asset_id"]) for item in doc["payload"]["output_assets"])
        details = doc["payload"]["details"]
        return AudioAiResult(operation, outputs, tuple(details.get("roles", [])), manifest.uri, f"job://{request.production_job_id}/evidence/task004.jsonl", details.get("capability_summary", {}))

    @staticmethod
    def _safe_effect_summary(report: dict[str, Any]) -> dict[str, Any]:
        effect = report.get("effect") if isinstance(report.get("effect"), dict) else {}
        command_id = effect.get("command_id") if isinstance(effect.get("command_id"), str) else None
        parameters = effect.get("parameters") if isinstance(effect.get("parameters"), dict) else {}
        summary: dict[str, Any] = {
            "command_id": command_id,
            "parameter_names": sorted(str(key) for key in parameters),
            "parameters_sha256": sha256_bytes(canonical_json_bytes(parameters)),
        }
        strategy = effect.get("parameter_strategy")
        if isinstance(strategy, str) and strategy in {
            "RUNTIME_DEFAULTS",
            "EXPLICIT_DISCOVERED_PARAMETERS",
            "DISCOVERED_MODE_PARAMETER",
            "INTEL_RUNTIME_DEFAULT_2_STEM",
        }:
            summary["parameter_strategy"] = strategy
        for key, value in parameters.items():
            if "device" in str(key).lower() and isinstance(value, str) and value.strip().upper() in {"CPU", "GPU", "NPU", "AUTO"}:
                summary["device"] = value.strip().upper()
                break
        return summary

    def process(self, request: AudioAiRequest) -> AudioAiResult:
        if not request.authorize_execution:
            raise ProductError("ERR_AUTH_LOCAL_AUDIO_EXECUTION_REQUIRED", "local audio AI execution requires explicit authorization", ProductErrorCategory.AUTHORIZATION)
        if not 1 <= request.timeout_seconds <= 7200:
            raise ValueError("timeout_seconds must be 1-7200")
        if request.operation is AudioAiOperation.MUSIC_SEPARATION and request.separation_mode is None:
            raise ProductError("ERR_INPUT_SEPARATION_MODE_REQUIRED", "music separation requires 2_STEM or 4_STEM mode", ProductErrorCategory.VALIDATION)
        source, source_path = self._source(request)
        request_fingerprint = sha256_bytes(canonical_json_bytes({
            "operation": request.operation.value,
            "source_asset_id": source.asset_id,
            "source_checksum": source.checksum,
            "separation_mode": request.separation_mode.value if request.separation_mode else None,
            "effect_parameters": request.effect_parameters or {},
        })).removeprefix("sha256:")
        operation, _ = self.store.reserve_operation(
            request.production_job_id, f"LOCAL_AUDIO_{request.operation.value}:{request_fingerprint}", request.idempotency_key
        )
        if operation.status == "COMPLETED":
            return self._load_completed(request, operation)
        if operation.status in {"IN_PROGRESS", "PARTIAL"}:
            raise ProductError(
                "ERR_STATE_AUDACITY_RECONCILIATION_REQUIRED",
                "a prior Audacity/OpenVINO dispatch may still have external side effects; automatic replay is unsafe",
                ProductErrorCategory.STATE,
                operation_id=operation.operation_id,
            )
        operation = self.store.update_operation_status(operation.operation_id, "IN_PROGRESS", increment_attempt=True)
        staging_uri = f"job://{request.production_job_id}/.staging/task004-audio/{operation.operation_id}"
        work_root = self.resolver.resolve(staging_uri)
        assert isinstance(work_root, Path)
        work_root.mkdir(parents=True, exist_ok=True)
        output_dir = work_root / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            report = self.worker_runner({
                "operation": request.operation.value,
                "source_path": str(source_path),
                "output_dir": str(output_dir),
                "separation_mode": request.separation_mode.value if request.separation_mode else None,
                "effect_parameters": dict(request.effect_parameters or {}),
            }, work_root, request.timeout_seconds)
            if report.get("ok") is not True:
                self._raise_report_error(report)
            raw_outputs = report.get("outputs")
            if not isinstance(raw_outputs, list) or not raw_outputs:
                raise ProductError("ERR_INTEGRITY_AUDIO_AI_OUTPUTS_MISSING", "Audacity worker did not report output files", ProductErrorCategory.DATA_INTEGRITY)
            output_root = output_dir.resolve(strict=True)
            expected = {"noise_suppressed"} if request.operation is AudioAiOperation.NOISE_SUPPRESSION else ({"vocals", "instrumental"} if request.separation_mode is SeparationMode.TWO_STEM else {"drums", "bass", "other", "vocals"})
            checksums_seen: set[str] = set()
            validated: list[tuple[str, Path, Any, str]] = []
            for item in raw_outputs:
                if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not isinstance(item.get("path"), str):
                    raise ProductError("ERR_INTEGRITY_AUDIO_AI_OUTPUT_DESCRIPTOR", "Audacity output descriptor is invalid", ProductErrorCategory.DATA_INTEGRITY)
                candidate = Path(item["path"])
                if candidate.is_symlink():
                    raise ProductError("ERR_SECURITY_AUDIO_AI_OUTPUT_SYMLINK", "Audacity output symlink is forbidden", ProductErrorCategory.SECURITY)
                try:
                    resolved = candidate.resolve(strict=True)
                    resolved.relative_to(output_root)
                except (FileNotFoundError, ValueError) as exc:
                    raise ProductError("ERR_SECURITY_AUDIO_AI_OUTPUT_ESCAPE", "Audacity output escapes Product staging", ProductErrorCategory.SECURITY) from exc
                probe = self.media_probe.probe(resolved)
                if not probe.has_audio:
                    raise ProductError("ERR_INTEGRITY_AUDIO_AI_OUTPUT_NOT_AUDIO", "Audacity output contains no audio stream", ProductErrorCategory.DATA_INTEGRITY)
                checksum = sha256_file(resolved)
                if checksum in checksums_seen:
                    raise ProductError("ERR_INTEGRITY_AUDIO_AI_DUPLICATE_OUTPUT", "multiple audio roles produced identical bytes", ProductErrorCategory.DATA_INTEGRITY)
                checksums_seen.add(checksum)
                role = item["role"].strip().lower()
                if not role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in role):
                    raise ProductError("ERR_INTEGRITY_AUDIO_AI_ROLE", "audio AI role is invalid", ProductErrorCategory.DATA_INTEGRITY)
                validated.append((role, resolved, probe, checksum))
            roles = [role for role, *_ in validated]
            if set(roles) != expected or len(roles) != len(expected):
                raise ProductError("ERR_INTEGRITY_AUDIO_AI_STEM_SET", "audio AI output roles do not match the requested complete set", ProductErrorCategory.DATA_INTEGRITY, details={"expected": sorted(expected), "actual": sorted(roles)})

            # All sibling outputs have passed QA; canonical publication may now begin.
            safe_effect = self._safe_effect_summary(report)
            published: list[AssetRecord] = []
            output_bindings: list[dict[str, str]] = []
            for role, resolved, probe, _checksum in validated:
                asset = self.publisher.publish(
                    resolved,
                    DerivedAssetSpec(
                        production_job_id=request.production_job_id,
                        namespace="audio-ai",
                        asset_type=AssetType.AUDIO,
                        owner=source.owner,
                        rights_status=source.rights_status,
                        retention_class=source.retention_class,
                        commercial_use=source.commercial_use,
                        derivative_allowed=source.derivative_allowed,
                        reuse_allowed=source.reuse_allowed,
                        audio_rights_status=source.audio_rights_status,
                        source_ref=source.asset_id,
                        source_project=source.source_project,
                        attribution=source.attribution,
                        publication_restrictions=source.publication_restrictions,
                        generation_provenance={
                            "provider": "AUDACITY_OPENVINO_EXTERNAL",
                            "operation": request.operation.value,
                            "role": role,
                            "effect": safe_effect,
                        },
                        media_metadata=probe.to_dict(),
                    ),
                    operation_id=operation.operation_id,
                )
                published.append(asset)
                output_bindings.append({"role": role, "asset_id": asset.asset_id, "checksum": asset.checksum})
            capability = report.get("capabilities") if isinstance(report.get("capabilities"), dict) else {}
            capability_summary = {
                "current_track_count": capability.get("current_track_count"),
                "features": {k: bool(v.get("available")) for k, v in (capability.get("features") or {}).items() if isinstance(v, dict)},
            }
            details = {
                "provider": "AUDACITY_OPENVINO_EXTERNAL",
                "operation": request.operation.value,
                "separation_mode": request.separation_mode.value if request.separation_mode else None,
                "roles": roles,
                "effect": safe_effect,
                "output_bindings": output_bindings,
                "capability_summary": capability_summary,
                "license_boundary": "EXTERNAL_GPL_RUNTIME_NOT_COPIED_INTO_CORE",
            }
            manifest = self.manifests.write(
                job_id=request.production_job_id, operation_id=operation.operation_id,
                manifest_type="local-audio-ai-manifest", schema_id="ai-video.local-audio-ai-manifest",
                lane="LOCAL_AUDIO_AI", operation_kind=request.operation.value,
                source_refs=(source.logical_uri,), input_checksums=(source.checksum,), output_assets=tuple(published),
                details=details, evidence_category="LOCAL_AUDIO_AI", producer_component="audacity-openvino-external-adapter",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=manifest.manifest.manifest_id)
            return AudioAiResult(operation, tuple(published), tuple(roles), manifest.manifest.uri, manifest.evidence_uri, capability_summary)
        except Exception as exc:
            code = exc.code if isinstance(exc, ProductError) else "ERR_INTERNAL_LOCAL_AUDIO_AI_FAILED"
            # A worker timeout after the first Audacity mutation may mean the external
            # effect/import/export completed even though Product never received a
            # durable result.  Do not convert that ambiguous state to FAILED because
            # FAILED is replayable.  Keep it PARTIAL so the next identical request
            # requires explicit reconciliation instead of blindly repeating work.
            ambiguous_external_state = False
            if isinstance(exc, ProductError) and exc.code == "ERR_PROVIDER_AUDACITY_OPENVINO_TIMEOUT":
                details = exc.details if isinstance(exc.details, dict) else {}
                progress = details.get("progress") if isinstance(details.get("progress"), dict) else {}
                phase = str(progress.get("phase") or "")
                ambiguous_external_state = phase in {
                    "IMPORTING_SOURCE",
                    "SOURCE_IMPORTED",
                    "APPLYING_NOISE_SUPPRESSION",
                    "NOISE_SUPPRESSION_APPLIED",
                    "EXPORTING_NOISE_SUPPRESSION",
                    "NOISE_SUPPRESSION_EXPORTED",
                    "APPLYING_MUSIC_SEPARATION",
                    "MUSIC_SEPARATION_APPLIED",
                    "MUSIC_SEPARATION_TRACKS_DISCOVERED",
                    "EXPORTING_MUSIC_SEPARATION_STEM",
                    "MUSIC_SEPARATION_EXPORTED",
                    "CLEANING_AUDACITY_PROJECT",
                    "AUDACITY_PROJECT_CLEANED",
                }
            self.store.update_operation_status(
                operation.operation_id,
                "PARTIAL" if ambiguous_external_state else "FAILED",
                last_error_code=code,
            )
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_LOCAL_AUDIO_AI_FAILED", "local audio AI processing failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
        finally:
            shutil.rmtree(work_root, ignore_errors=True)
