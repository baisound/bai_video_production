"""Private launch configuration and composition root for TASK-036 W2.

The packaged WebView never receives this configuration. It is read once by the
trusted Python host and binds every path, Product port and external target before
the window is created.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import contextmanager
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable

from .ai_connections import AiWorkload, ConnectionAvailability, CostClass, ProviderFamily
from .comfyui import ComfyEndpointPolicy, ComfyUIClient
from .creative_generation_execution_application import Task013CreativeGenerationExecutionApplication
from .generation_output_adoption_application import (
    Task027GeneratedOutputAssetPort,
    Task027GenerationOutputAdoptionApplication,
)
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_post_resolve_workflow import Task036PostResolveWorkflowFacade
from .desktop_resolve_workflow import Task036ResolveWorkflowFacade
from .errors import ProductError, ProductErrorCategory
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from .ids import IdKind, validate_id, validate_project_id
from .ingest import AssetIngestService
from .paths import LogicalPathResolver, PathMapping, SourcePathPolicy
from .resolve_assembly import ResolveAssetBindings, ResolveScriptingAssemblyAdapter
from .store import SQLiteProductStore
from .task036_native_dialog import Task036NativeDialogService
from .task036_native_render_port import Task036Task011NativeRenderPort
from .task036_pre_edit_runtime import Task036PreEditRuntime
from .task036_product_ports import (
    FixedAnalysisAudioBinding,
    Task036AssetIngestPort,
    Task036CutCandidatePort,
    Task036LocalTranscriptionPort,
)
from .task036_shell_ui import HTML, Task036ShellBridge
from .game_intelligence_shell import GameIntelligenceShellApplication
from .task044_nle_shell import Task044NleShellController
from .interactive_timeline_application import Task044TimelineEditApplication
from .interactive_timeline_projection import InteractiveTimelineProjectionService
from .export_queue_application import ExportQueueApplication
from .export_queue import ExportPreparation
from .final_review import FinalReviewApprovalReceipt
from .final_review_application import FinalReviewApprovalApplication
from .final_review_gate import FinalReviewExternalGateReceipt
from .product_project_store import ProductProjectManifestStore
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import _exclusive_snapshot_lock
from .audit_application import Task038AuditApplication
from .planning_application import Task027PlanningApplication
from .task036_planning_generation_application import Task036PlanningGenerationApplication
from .generation_safety_application import Task013GenerationSafetyApplication
from .continuity_application import Task039ContinuityApplication
from .connection_settings_web import ConnectionSettingsWebService
from .credential_vault import WindowsCredentialManagerStore
from .provider_execution import (AiProviderExecutionService, AnthropicMessagesAdapter, GoogleInteractionsAdapter, OpenAiResponsesAdapter, UrllibJsonTransport)
from .prompt_evidence_application import Task040PromptEvidenceApplication
from .generation_queue_application import Task027GenerationQueueApplication
from .audio_workspace_application import Task041AudioWorkspaceApplication
from .audio_placement_application import Task026AudioPlacementApplication
from .quick_generation_application import Task042QuickGenerationApplication
from .local_comfy_generation_port import (
    LocalComfyGenerationConfig, LocalComfyTextToVideoPort,
    MINIMAX_H3_NATIVE_WORKFLOW_SHA256, default_minimax_h3_workflow_path,
)
from .local_comfy_image_generation_port import (
    FLUX1_SCHNELL_FP8_WORKFLOW_SHA256,
    LocalComfyImageGenerationConfig,
    LocalComfyTextToImagePort,
    default_flux1_schnell_fp8_workflow_path,
)
from .task036_workflow_runtime import Task036WorkflowRuntime
from .task036_visual_asset_placement import Task036VisualAssetPlacementApplication
from .timebase import FrameRate


TASK036_LAUNCH_CONFIG_MAX_BYTES = 256 * 1024


def _path(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{field} must be a non-empty path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{field} must be absolute")
    if path.is_symlink():
        raise ValueError(f"{field} must not be a symlink")
    return path.resolve(strict=False)


def _require_exact_keys(section: dict[str, Any], expected: set[str], *, name: str) -> None:
    if set(section) != expected:
        raise ValueError(f"{name} contains unknown or missing fields")


def _required_text(value: Any, *, field: str, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    result = value.strip()
    if not result or len(result) > maximum:
        raise ValueError(f"{field} is invalid")
    return result


def _contained(root: Path, candidate: Path, *, field: str) -> Path:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field} must remain inside project_root") from exc
    return candidate


@dataclass(frozen=True, slots=True)
class Task036LaunchConfiguration:
    project_id: str
    display_name: str
    project_root: Path
    source_roots: tuple[Path, ...]
    asset_root: Path
    job_root: Path
    database_path: Path
    production_job_id: str
    profile_snapshot_id: str
    owner: str
    analysis_source_path: Path
    analysis_audio_path: Path
    transcription_output: Path
    cut_output: Path
    handoff_destination: Path
    native_render_evidence_root: Path
    native_render_report_path: Path
    resolve_project: str
    timeline_rate: FrameRate
    source_frame_rate: FrameRate
    asr_config: FasterWhisperConfig
    asr_language: str | None
    local_generation: LocalComfyGenerationConfig | None
    local_image_generation: LocalComfyImageGenerationConfig | None

    @classmethod
    def load(cls, path: str | Path) -> "Task036LaunchConfiguration":
        source = Path(path)
        if source.is_symlink() or not source.is_file():
            raise ProductError(
                "ERR_TASK036_LAUNCH_CONFIG_FILE_INVALID",
                "TASK-036 launch configuration must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        if not 0 < source.stat().st_size <= TASK036_LAUNCH_CONFIG_MAX_BYTES:
            raise ProductError(
                "ERR_TASK036_LAUNCH_CONFIG_SIZE",
                "TASK-036 launch configuration is outside the allowed size bound",
                ProductErrorCategory.VALIDATION,
            )
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            return cls.from_dict(raw)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK036_LAUNCH_CONFIG_INVALID",
                "TASK-036 launch configuration is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"exception_type": type(exc).__name__},
            ) from exc

    @classmethod
    def from_dict(cls, raw: Any) -> "Task036LaunchConfiguration":
        if not isinstance(raw, dict) or raw.get("launch_config_version") not in {"1.0.0", "1.1.0", "1.2.0"}:
            raise ValueError("unsupported launch_config_version")
        version = raw["launch_config_version"]
        allowed = {
            "launch_config_version", "project", "paths", "ingest", "asr", "resolve",
        }
        if version in {"1.1.0", "1.2.0"}:
            allowed.add("local_generation")
        if version == "1.2.0":
            allowed.add("local_image_generation")
        if set(raw) != allowed:
            raise ValueError("launch configuration contains unknown or missing sections")
        project = raw["project"]
        paths = raw["paths"]
        ingest = raw["ingest"]
        asr = raw["asr"]
        resolve = raw["resolve"]
        if not all(isinstance(item, dict) for item in (project, paths, ingest, asr, resolve)):
            raise ValueError("launch configuration sections must be objects")

        _require_exact_keys(
            project,
            {"project_id", "display_name", "project_root"},
            name="project",
        )
        _require_exact_keys(
            paths,
            {
                "source_roots",
                "asset_root",
                "job_root",
                "database_path",
                "analysis_source_path",
                "analysis_audio_path",
                "asr_cache_directory",
                "transcription_output",
                "cut_output",
                "handoff_destination",
                "native_render_evidence_root",
                "native_render_report_path",
            },
            name="paths",
        )
        _require_exact_keys(
            ingest,
            {"production_job_id", "profile_snapshot_id", "owner"},
            name="ingest",
        )
        _require_exact_keys(
            asr,
            {
                "model",
                "device",
                "compute_type",
                "beam_size",
                "vad_filter",
                "allow_model_download",
                "language",
            },
            name="asr",
        )
        _require_exact_keys(
            resolve,
            {"sandbox_project", "timeline_rate", "source_frame_rate"},
            name="resolve",
        )

        project_id = validate_project_id(_required_text(project["project_id"], field="project_id"))
        display_name = _required_text(project["display_name"], field="display_name")
        project_root = _path(project["project_root"], field="project_root")
        if project_root.is_symlink() or not project_root.is_dir():
            raise ValueError("project_root must be an existing regular directory")

        roots_raw = paths["source_roots"]
        if not isinstance(roots_raw, list) or not roots_raw:
            raise ValueError("source_roots must be a non-empty list")
        source_roots = tuple(_path(item, field="source_roots") for item in roots_raw)
        if any(root.is_symlink() or not root.is_dir() for root in source_roots):
            raise ValueError("source_roots must be existing regular directories")

        def project_path(name: str) -> Path:
            return _contained(project_root, _path(paths[name], field=name), field=name)

        local_generation_config: LocalComfyGenerationConfig | None = None
        if version == "1.1.0" and raw["local_generation"] is None:
            raise ValueError("launch config 1.1.0 requires local_generation")
        if version in {"1.1.0", "1.2.0"} and raw["local_generation"] is not None:
            local_generation = raw["local_generation"]
            if not isinstance(local_generation, dict):
                raise ValueError("local_generation must be an object")
            _require_exact_keys(
                local_generation,
                {
                    "endpoint", "comfy_output_root", "project_output_root", "staging_root",
                    "dispatch_journal_root", "route_id", "provider_id", "model_id",
                    "width", "height", "length", "steps", "poll_interval_seconds",
                    "completion_timeout_seconds", "max_output_bytes",
                },
                name="local_generation",
            )
            video_comfy_output_root = _path(
                local_generation["comfy_output_root"],
                field="local_generation.comfy_output_root",
            )
            if version == "1.1.0":
                video_comfy_output_root = _contained(
                    project_root,
                    video_comfy_output_root,
                    field="local_generation.comfy_output_root",
                )
            local_roots = {
                "comfy_output_root": video_comfy_output_root,
                **{
                    name: _contained(
                        project_root,
                        _path(local_generation[name], field=f"local_generation.{name}"),
                        field=f"local_generation.{name}",
                    )
                    for name in ("project_output_root", "staging_root", "dispatch_journal_root")
                },
            }
            if any(path.is_symlink() or not path.is_dir() for path in local_roots.values()):
                raise ValueError("local_generation roots must be existing regular project directories")
            try:
                endpoint = ComfyEndpointPolicy().authorize(
                    _required_text(local_generation["endpoint"], field="local_generation.endpoint", maximum=500)
                )
            except ProductError as exc:
                raise ValueError("local_generation.endpoint is not an authorized local origin") from exc
            local_generation_config = LocalComfyGenerationConfig(
                endpoint=endpoint,
                workflow_path=default_minimax_h3_workflow_path(),
                workflow_sha256=MINIMAX_H3_NATIVE_WORKFLOW_SHA256,
                comfy_output_root=local_roots["comfy_output_root"],
                project_output_root=local_roots["project_output_root"],
                staging_root=local_roots["staging_root"],
                dispatch_journal_root=local_roots["dispatch_journal_root"],
                route_id=_required_text(local_generation["route_id"], field="local_generation.route_id"),
                provider_id=_required_text(local_generation["provider_id"], field="local_generation.provider_id"),
                model_id=_required_text(local_generation["model_id"], field="local_generation.model_id"),
                width=local_generation["width"], height=local_generation["height"],
                length=local_generation["length"], steps=local_generation["steps"],
                poll_interval_seconds=local_generation["poll_interval_seconds"],
                completion_timeout_seconds=local_generation["completion_timeout_seconds"],
                max_output_bytes=local_generation["max_output_bytes"],
            )

        local_image_generation_config: LocalComfyImageGenerationConfig | None = None
        if version == "1.2.0" and raw["local_image_generation"] is not None:
            local_image_generation = raw["local_image_generation"]
            if not isinstance(local_image_generation, dict):
                raise ValueError("local_image_generation must be an object or null")
            _require_exact_keys(
                local_image_generation,
                {
                    "endpoint", "comfy_output_root", "project_output_root", "staging_root",
                    "dispatch_journal_root", "route_id", "provider_id", "model_id",
                    "width", "height", "steps", "poll_interval_seconds",
                    "completion_timeout_seconds", "max_output_bytes",
                },
                name="local_image_generation",
            )
            comfy_output_root = _path(
                local_image_generation["comfy_output_root"],
                field="local_image_generation.comfy_output_root",
            )
            image_project_roots = {
                name: _contained(
                    project_root,
                    _path(local_image_generation[name], field=f"local_image_generation.{name}"),
                    field=f"local_image_generation.{name}",
                )
                for name in ("project_output_root", "staging_root", "dispatch_journal_root")
            }
            if (
                comfy_output_root.is_symlink() or not comfy_output_root.is_dir()
                or any(path.is_symlink() or not path.is_dir() for path in image_project_roots.values())
            ):
                raise ValueError("local_image_generation roots must be existing regular directories")
            local_image_generation_config = LocalComfyImageGenerationConfig(
                endpoint=_required_text(
                    local_image_generation["endpoint"],
                    field="local_image_generation.endpoint",
                    maximum=500,
                ),
                workflow_path=default_flux1_schnell_fp8_workflow_path(),
                workflow_sha256=FLUX1_SCHNELL_FP8_WORKFLOW_SHA256,
                comfy_output_root=comfy_output_root,
                project_output_root=image_project_roots["project_output_root"],
                staging_root=image_project_roots["staging_root"],
                dispatch_journal_root=image_project_roots["dispatch_journal_root"],
                route_id=_required_text(local_image_generation["route_id"], field="local_image_generation.route_id"),
                provider_id=_required_text(local_image_generation["provider_id"], field="local_image_generation.provider_id"),
                model_id=_required_text(local_image_generation["model_id"], field="local_image_generation.model_id"),
                width=local_image_generation["width"],
                height=local_image_generation["height"],
                steps=local_image_generation["steps"],
                poll_interval_seconds=local_image_generation["poll_interval_seconds"],
                completion_timeout_seconds=local_image_generation["completion_timeout_seconds"],
                max_output_bytes=local_image_generation["max_output_bytes"],
            )
        if version == "1.2.0" and local_generation_config is None and local_image_generation_config is None:
            raise ValueError("launch config 1.2.0 requires at least one local generation runtime")
        if local_generation_config is not None and local_image_generation_config is not None:
            if (
                local_generation_config.endpoint != local_image_generation_config.endpoint
                or local_generation_config.comfy_output_root != local_image_generation_config.comfy_output_root
                or local_generation_config.project_output_root != local_image_generation_config.project_output_root
                or local_generation_config.route_id == local_image_generation_config.route_id
            ):
                raise ValueError("video/image local generation must share one runtime/output root and use distinct routes")

        analysis_source = _path(paths["analysis_source_path"], field="analysis_source_path")
        if analysis_source.is_symlink() or not analysis_source.is_file():
            raise ValueError("analysis_source_path must be an existing regular file")
        if not any(_is_within(root, analysis_source) for root in source_roots):
            raise ValueError("analysis_source_path must be inside source_roots")
        analysis_audio = project_path("analysis_audio_path")
        if analysis_audio.is_symlink() or not analysis_audio.is_file():
            raise ValueError("analysis_audio_path must be an existing regular file")

        production_job_id = validate_id(
            _required_text(ingest["production_job_id"], field="production_job_id"),
            IdKind.JOB,
        )
        profile_snapshot_id = validate_id(
            _required_text(ingest["profile_snapshot_id"], field="profile_snapshot_id"),
            IdKind.PROFILE_SNAPSHOT,
        )
        owner = _required_text(ingest["owner"], field="owner")
        allow_download = asr.get("allow_model_download")
        if allow_download is not False:
            raise ValueError("trusted W2 launch requires allow_model_download=false")
        model = _required_text(asr["model"], field="asr.model")
        device = _required_text(asr["device"], field="asr.device")
        compute_type = _required_text(asr["compute_type"], field="asr.compute_type")
        beam_size = asr["beam_size"]
        if isinstance(beam_size, bool) or not isinstance(beam_size, int) or not 1 <= beam_size <= 100:
            raise ValueError("asr.beam_size must be an integer from 1 through 100")
        vad_filter = asr["vad_filter"]
        if not isinstance(vad_filter, bool):
            raise ValueError("asr.vad_filter must be a boolean")
        language = asr.get("language")
        if language is not None and (not isinstance(language, str) or not language.strip()):
            raise ValueError("ASR language is invalid")
        cache = project_path("asr_cache_directory")
        if not cache.is_dir():
            raise ValueError("asr_cache_directory must be an existing directory")
        asr_config = FasterWhisperConfig(
            model=model,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            vad_filter=vad_filter,
            allow_model_download=False,
            cache_directory=cache,
        )
        resolve_project = _required_text(resolve["sandbox_project"], field="resolve.sandbox_project")
        if not resolve_project.startswith("BAI_CAPABILITY_PROBE_"):
            raise ValueError("Resolve target must be an explicit BAI_CAPABILITY_PROBE_* sandbox")

        return cls(
            project_id=project_id,
            display_name=display_name,
            project_root=project_root,
            source_roots=source_roots,
            asset_root=project_path("asset_root"),
            job_root=project_path("job_root"),
            database_path=project_path("database_path"),
            production_job_id=production_job_id,
            profile_snapshot_id=profile_snapshot_id,
            owner=owner,
            analysis_source_path=analysis_source,
            analysis_audio_path=analysis_audio,
            transcription_output=project_path("transcription_output"),
            cut_output=project_path("cut_output"),
            handoff_destination=project_path("handoff_destination"),
            native_render_evidence_root=project_path("native_render_evidence_root"),
            native_render_report_path=project_path("native_render_report_path"),
            resolve_project=resolve_project,
            timeline_rate=FrameRate.parse(str(resolve["timeline_rate"])),
            source_frame_rate=FrameRate.parse(str(resolve["source_frame_rate"])),
            asr_config=asr_config,
            asr_language=None if language is None else language.strip(),
            local_generation=local_generation_config,
            local_image_generation=local_image_generation_config,
        )


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(slots=True)
class Task036TrustedLaunch:
    configuration: Task036LaunchConfiguration
    coordinator: DesktopEditingCoordinator
    pre_edit_runtime: Task036PreEditRuntime
    bridge: Task036ShellBridge
    _runtime_lease: "_Task036ProjectRuntimeLease | None" = field(default=None, repr=False)
    _product_store: SQLiteProductStore | None = field(default=None, repr=False)

    def close(self) -> None:
        """Release the private mutation-runtime lease, if this launch owns one."""

        lease = self._runtime_lease
        if lease is not None:
            lease.close()
            self._runtime_lease = None
        store = self._product_store
        if store is not None:
            store.close()
            self._product_store = None

    def __enter__(self) -> "Task036TrustedLaunch":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class _Task036ProjectRuntimeLease:
    """One live TASK-036 mutation composition per Project, held for launch life."""

    _NAME = ".task036-runtime.lock"

    def __init__(self, path: Path, handle: Any) -> None:
        self._path = path
        self._handle: Any | None = handle
        self._condition = threading.Condition(threading.RLock())
        self._local = threading.local()
        self._closing = False
        self._active_operation_count = 0

    @property
    def active(self) -> bool:
        with self._condition:
            return self._handle is not None and not self._closing

    def require_active(self) -> None:
        if not self.active:
            raise ProductError(
                "ERR_TASK036_RUNTIME_LEASE_REQUIRED",
                "TASK-036 Project runtime lease is no longer active",
                ProductErrorCategory.STATE,
            )

    def require_operation_active(self) -> None:
        """Allow a previously admitted same-thread operation to finish on close."""

        with self._condition:
            if self._handle is None or (
                self._closing and getattr(self._local, "depth", 0) == 0
            ):
                raise ProductError(
                    "ERR_TASK036_RUNTIME_LEASE_REQUIRED",
                    "TASK-036 Project runtime lease is no longer active",
                    ProductErrorCategory.STATE,
                )

    @contextmanager
    def operation(self):
        """Hold the runtime lease throughout one public TASK-044 operation."""

        with self._condition:
            depth = getattr(self._local, "depth", 0)
            if depth == 0:
                if self._handle is None or self._closing:
                    raise ProductError(
                        "ERR_TASK036_RUNTIME_LEASE_REQUIRED",
                        "TASK-036 Project runtime lease is no longer active",
                        ProductErrorCategory.STATE,
                    )
                self._active_operation_count += 1
            elif self._handle is None:
                raise ProductError(
                    "ERR_TASK036_RUNTIME_LEASE_REQUIRED",
                    "TASK-036 Project runtime lease is no longer active",
                    ProductErrorCategory.STATE,
                )
            self._local.depth = depth + 1
        try:
            yield
        finally:
            with self._condition:
                depth = getattr(self._local, "depth", 1) - 1
                self._local.depth = depth
                if depth == 0:
                    self._active_operation_count -= 1
                    self._condition.notify_all()

    @classmethod
    def acquire(cls, project_root: Path) -> "_Task036ProjectRuntimeLease":
        manifest_path = ProductProjectManifestStore.path(project_root)
        control = manifest_path.parent
        if control.is_symlink() or not control.is_dir():
            raise ProductError(
                "ERR_TASK036_RUNTIME_LEASE_INVALID",
                "TASK-036 Project runtime lock directory is invalid",
                ProductErrorCategory.SECURITY,
            )
        path = control / cls._NAME
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ProductError(
                "ERR_TASK036_RUNTIME_LEASE_INVALID",
                "TASK-036 Project runtime lock must be a regular non-symlink file",
                ProductErrorCategory.SECURITY,
            )
        try:
            handle = path.open("a+b")
            if path.is_symlink() or not path.is_file():
                handle.close()
                raise ProductError(
                    "ERR_TASK036_RUNTIME_LEASE_INVALID",
                    "TASK-036 Project runtime lock must be a regular non-symlink file",
                    ProductErrorCategory.SECURITY,
                )
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ProductError:
            raise
        except OSError as exc:
            try:
                handle.close()
            except (OSError, UnboundLocalError):
                pass
            raise ProductError(
                "ERR_TASK036_RUNTIME_ALREADY_ACTIVE",
                "Another TASK-036 mutation runtime is already active for this Project",
                ProductErrorCategory.STATE,
            ) from exc
        return cls(path, handle)

    def close(self) -> None:
        with self._condition:
            if self._handle is None:
                return
            if getattr(self._local, "depth", 0):
                raise ProductError(
                    "ERR_TASK036_RUNTIME_CLOSE_IN_FLIGHT",
                    "TASK-036 runtime lease cannot close from its active operation",
                    ProductErrorCategory.STATE,
                )
            if self._closing:
                while self._handle is not None:
                    self._condition.wait()
                return
            self._closing = True
            while self._active_operation_count:
                self._condition.wait()
            handle = self._handle
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
                self._handle = None
                self._condition.notify_all()

    def __del__(self) -> None:
        try:
            self.close()
        except OSError:
            pass


def _resolve_asset_bindings(
    configuration: Task036LaunchConfiguration,
    source_path: Path,
) -> ResolveAssetBindings:
    return ResolveAssetBindings(
        source_path,
        configuration.source_frame_rate,
        subtitle_srt_path=configuration.transcription_output / "subtitles.srt",
        subtitle_derived_srt_path=configuration.transcription_output / "subtitles.edit-aware.srt",
    )


def _handoff_subtitle_path(path: Path) -> Path | None:
    if not path.is_symlink() and path.is_file() and path.stat().st_size == 0:
        return None
    return path


def build_trusted_launch(
    configuration: Task036LaunchConfiguration,
    *,
    native_dialog: Task036NativeDialogService | None = None,
    asr_provider: FasterWhisperProvider | None = None,
    resolve_adapter: ResolveScriptingAssemblyAdapter | None = None,
    comfy_client: ComfyUIClient | None = None,
    final_review_external_gate_provider: Callable[
        [], tuple[FinalReviewExternalGateReceipt, ...]
    ] | None = None,
    final_review_export_preparation_provider: Callable[
        [FinalReviewApprovalReceipt], ExportPreparation
    ] | None = None,
    allow_product_job_bootstrap: bool = True,
) -> Task036TrustedLaunch:
    if not allow_product_job_bootstrap:
        for directory in (
            configuration.asset_root,
            configuration.job_root,
            configuration.transcription_output,
            configuration.cut_output,
            configuration.handoff_destination,
            configuration.native_render_evidence_root.parent,
            configuration.native_render_report_path.parent,
        ):
            if directory.is_symlink() or not directory.is_dir():
                raise ProductError(
                    "ERR_TASK036_TRUSTED_PROJECT_NOT_INITIALIZED",
                    "The trusted Product Project directories must already exist",
                    ProductErrorCategory.STATE,
                )
    if allow_product_job_bootstrap:
        for directory in (
            configuration.asset_root,
            configuration.job_root,
            configuration.transcription_output,
            configuration.cut_output,
            configuration.handoff_destination,
            configuration.native_render_evidence_root.parent,
            configuration.native_render_report_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    try:
        store = SQLiteProductStore(
            configuration.database_path,
            require_existing=not allow_product_job_bootstrap,
            required_job_id=(
                configuration.production_job_id
                if not allow_product_job_bootstrap
                else None
            ),
        )
    except ProductError as exc:
        if exc.code == "ERR_STORE_EXISTING_JOB_REQUIRED":
            raise ProductError(
                "ERR_TASK036_TRUSTED_PROJECT_NOT_INITIALIZED",
                "The trusted Product Project must already contain its configured Product Job",
                ProductErrorCategory.STATE,
            ) from exc
        raise
    if allow_product_job_bootstrap:
        try:
            store.get_job_state(configuration.production_job_id)
        except ProductError as exc:
            if exc.code != "ERR_INPUT_JOB_NOT_FOUND":
                raise
            store.create_job(configuration.profile_snapshot_id, job_id=configuration.production_job_id)
    resolver = LogicalPathResolver(
        [
            PathMapping("asset://", configuration.asset_root),
            PathMapping("job://", configuration.job_root),
        ]
    )
    ingest_service = AssetIngestService(
        store=store,
        resolver=resolver,
        source_policy=SourcePathPolicy(configuration.source_roots),
    )
    ingest_port = Task036AssetIngestPort(
        ingest_service,
        configuration.production_job_id,
        configuration.owner,
    )
    transcription_port = Task036LocalTranscriptionPort(
        asr_provider or FasterWhisperProvider(configuration.asr_config),
        configuration.transcription_output,
        language=configuration.asr_language,
        timeline_rate=configuration.timeline_rate,
    )
    cut_port = Task036CutCandidatePort(
        FixedAnalysisAudioBinding(configuration.analysis_source_path, configuration.analysis_audio_path),
        configuration.cut_output,
    )
    coordinator = DesktopEditingCoordinator.create(
        product_version="0.22.0",
        project_id=configuration.project_id,
        display_name=configuration.display_name,
    )
    dialog = native_dialog or Task036NativeDialogService()
    pre_edit = Task036PreEditRuntime(coordinator, dialog, ingest_port, transcription_port, cut_port)
    adapter = resolve_adapter or ResolveScriptingAssemblyAdapter()

    workflow_runtimes: dict[int, Task036WorkflowRuntime] = {}

    def downstream(application):
        cached = workflow_runtimes.get(id(application))
        if cached is not None:
            if cached.application is not application:
                raise ProductError(
                    "ERR_TASK036_WORKFLOW_RUNTIME_IDENTITY",
                    "Trusted workflow runtime identity changed",
                    ProductErrorCategory.INTERNAL,
                )
            return cached
        source_path = pre_edit.media.runtime_source_path
        if source_path is None:
            raise ProductError(
                "ERR_TASK036_RUNTIME_SOURCE_NOT_BOUND",
                "Trusted downstream runtime requires the exact selected source",
                ProductErrorCategory.STATE,
            )
        resolve = Task036ResolveWorkflowFacade(application)
        post_resolve = Task036PostResolveWorkflowFacade(application, resolve)
        runtime = Task036WorkflowRuntime(
            application,
            resolve,
            post_resolve,
            adapter,
            _resolve_asset_bindings(configuration, source_path),
            configuration.timeline_rate,
            configuration.resolve_project,
            native_render_port=Task036Task011NativeRenderPort(
                configuration.native_render_evidence_root,
                configuration.native_render_report_path,
            ),
            handoff_destination=configuration.handoff_destination,
            subtitle_srt_path=_handoff_subtitle_path(configuration.transcription_output / "subtitles.srt"),
        )
        workflow_runtimes[id(application)] = runtime
        return runtime

    production_control = Task037ProductionControlApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
    )
    planning_application = Task027PlanningApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        production_control=production_control,
    )
    audit_application = Task038AuditApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
    )
    generation_safety_application = Task013GenerationSafetyApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        planning_application=planning_application,
        audit_application=audit_application,
    )
    continuity_application = Task039ContinuityApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        production_control=production_control,
    )
    prompt_evidence_application = Task040PromptEvidenceApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        production_control=production_control,
        audit_application=audit_application,
    )
    generation_queue_application = Task027GenerationQueueApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        production_control=production_control,
        planning_application=planning_application,
        generation_safety_application=generation_safety_application,
        continuity_application=continuity_application,
        prompt_evidence_application=prompt_evidence_application,
    )
    audio_workspace_application = Task041AudioWorkspaceApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
        production_control=production_control,
    )
    audio_placement_application = None
    if ProductProjectManifestStore.path(configuration.project_root).exists():
        audio_placement_application = Task026AudioPlacementApplication(
            project_root=configuration.project_root,
            project_id=configuration.project_id,
            production_control=production_control,
        )
    quick_generation_application = None
    quick_inputs = (
        configuration.project_root / "prompt-registry.json",
        configuration.project_root / "production-control.json",
    )
    if all(path.is_file() and not path.is_symlink() for path in quick_inputs):
        quick_generation_application = Task042QuickGenerationApplication(
            project_root=configuration.project_root,
            project_id=configuration.project_id,
        )
    connection_settings = None
    game_intelligence_provider_service = None
    connection_settings_path = configuration.project_root / "ai-connection-settings.json"
    if connection_settings_path.is_symlink():
        raise ProductError(
            "ERR_TASK028_CONNECTION_SETTINGS_FILE_INVALID",
            "AI Connection Settings must not be a symlink",
            ProductErrorCategory.SECURITY,
        )
    if connection_settings_path.exists():
        if not connection_settings_path.is_file():
            raise ProductError(
                "ERR_TASK028_CONNECTION_SETTINGS_FILE_INVALID",
                "AI Connection Settings must be a regular file",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            credential_vault = WindowsCredentialManagerStore() if os.name == "nt" else None
            connection_settings = ConnectionSettingsWebService.from_paths(
                connection_settings_path,
                None,
                credential_vault=credential_vault,
            )
            if credential_vault is not None:
                transport = UrllibJsonTransport()
                game_intelligence_provider_service = AiProviderExecutionService(
                    (OpenAiResponsesAdapter(transport), AnthropicMessagesAdapter(transport), GoogleInteractionsAdapter(transport)),
                    credential_vault,
                )
        except (OSError, UnicodeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK028_CONNECTION_SETTINGS_INVALID",
                "AI Connection Settings failed current-valid validation",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"exception_type": type(exc).__name__},
            ) from exc

    has_mutation_composition = ProductProjectManifestStore.path(
        configuration.project_root
    ).exists()
    runtime_lease: _Task036ProjectRuntimeLease | None = None

    def nle_controller(application) -> Task044NleShellController:
        timeline = InteractiveTimelineProjectionService.from_editing_projection(
            project_id=configuration.project_id,
            timeline_id=f"task036:{configuration.project_id}",
            timeline_rate=configuration.timeline_rate,
            projection=application.projection(),
        )
        edit_application = None
        visual_asset_placement = None
        export_application = None
        if has_mutation_composition:
            if runtime_lease is None:
                raise ProductError(
                    "ERR_TASK036_RUNTIME_LEASE_REQUIRED",
                    "TASK-036 mutation composition requires its active Project runtime lease",
                    ProductErrorCategory.STATE,
                )
            runtime_lease.require_operation_active()
            placement_holder: dict[str, Task036VisualAssetPlacementApplication] = {}
            edit_application = Task044TimelineEditApplication(
                project_root=configuration.project_root,
                project_id=configuration.project_id,
                placement_guard_resolver=lambda command: placement_holder[
                    "application"
                ].commit_guard_for_command(command),
            )

            @contextmanager
            def production_guard(expected_snapshot_sha256: str):
                with _exclusive_snapshot_lock(production_control.snapshot_path):
                    guarded_snapshot = production_control.snapshot()
                    if guarded_snapshot["snapshot_sha256"] != expected_snapshot_sha256:
                        raise ProductError(
                            "ERR_VISUAL_PLACEMENT_SOURCE_STALE",
                            "Production Control changed before Timeline commit",
                            ProductErrorCategory.STATE,
                        )
                    yield guarded_snapshot

            visual_asset_placement = Task036VisualAssetPlacementApplication(
                project_id=configuration.project_id,
                product_job_id=configuration.production_job_id,
                production_snapshot_provider=production_control.snapshot,
                production_guard_factory=production_guard,
                asset_provider=store.get_asset,
                timeline_application=edit_application,
            )
            placement_holder["application"] = visual_asset_placement
            export_application = ExportQueueApplication(
                project_root=configuration.project_root, project_id=configuration.project_id,
            )
            export_application.recover_interrupted_on_startup()
        preparation_provider = None
        destination_provider = None
        dispatcher = None
        if export_application is not None and final_review_export_preparation_provider is not None:
            def preparation_provider(job_id: str) -> ExportPreparation:
                application_boundary = bridge._final_review_export_application
                if application_boundary is None:
                    raise ProductError(
                        "ERR_FINAL_REVIEW_EXPORT_PREPARATION_NOT_BOUND",
                        "Private Export preparation is not bound to this launcher",
                        ProductErrorCategory.STATE,
                    )
                return application_boundary.preparation_for_dispatch(job_id=job_id)

            def destination_provider(job_id: str, _preparation: ExportPreparation) -> Path:
                root = configuration.native_render_evidence_root.resolve()
                destination = root / "exports" / job_id / "render-output"
                try:
                    destination.relative_to(root)
                except ValueError as exc:
                    raise ProductError(
                        "ERR_TASK036_EXPORT_DESTINATION_INVALID",
                        "Private Export destination escapes the trusted evidence root",
                        ProductErrorCategory.SECURITY,
                    ) from exc
                return destination
            dispatcher = lambda job, preparation, destination: downstream(
                application
            ).dispatch_export(job, preparation, destination)
        return Task044NleShellController(
            timeline=timeline, edit_application=edit_application,
            export_application=export_application,
            export_preparation_provider=preparation_provider,
            export_destination_provider=destination_provider,
            export_dispatcher=dispatcher,
            visual_asset_placement=visual_asset_placement,
        )
    generation_execution_application = None
    generation_output_adoption_application = None
    if configuration.local_generation is not None or configuration.local_image_generation is not None:
        runtime_config = configuration.local_image_generation or configuration.local_generation
        assert runtime_config is not None
        local_client = comfy_client or ComfyUIClient(runtime_config.endpoint)
        video_port = None
        image_port = None
        if configuration.local_generation is not None:
            video_port = LocalComfyTextToVideoPort(config=configuration.local_generation, client=local_client)
        if configuration.local_image_generation is not None:
            image_port = LocalComfyTextToImagePort(config=configuration.local_image_generation, client=local_client)
        route_ids = frozenset(
            config.route_id
            for config in (configuration.local_generation, configuration.local_image_generation)
            if config is not None
        )
        selector = None
        fixed_port = image_port or video_port
        if image_port is not None and video_port is not None:
            fixed_port = None

            def matches_trusted_route(route, capability, config, workload):
                return (
                    route.enabled
                    and route.workload is workload
                    and route.cost_class is CostClass.LOCAL_FREE_AI
                    and route.credential_ref is None
                    and route.endpoint_ref is None
                    and route.settings == {}
                    and route.capabilities == (capability,)
                    and route.route_id == config.route_id
                    and route.provider_family is ProviderFamily.COMFYUI
                    and route.provider_id == config.provider_id
                    and route.model_id == config.model_id
                )

            def selector(route, capability):
                if (
                    capability == "TEXT_TO_IMAGE"
                    and matches_trusted_route(
                        route,
                        capability,
                        configuration.local_image_generation,
                        AiWorkload.IMAGE,
                    )
                ):
                    return image_port
                if (
                    capability == "TEXT_TO_VIDEO"
                    and matches_trusted_route(
                        route,
                        capability,
                        configuration.local_generation,
                        AiWorkload.VIDEO,
                    )
                ):
                    return video_port
                raise ProductError(
                    "ERR_TASK036_LOCAL_GENERATION_ROUTE_UNBOUND",
                    "No trusted local generation port matches the exact local-free route and capability",
                    ProductErrorCategory.NOT_SUPPORTED,
                )

        generation_execution_application = Task013CreativeGenerationExecutionApplication(
            project_root=configuration.project_root,
            project_id=configuration.project_id,
            generation_queue=generation_queue_application,
            execution_port=fixed_port,
            execution_port_selector=selector,
            availability_factory=lambda: ConnectionAvailability(
                route_ids
            ),
        )
        output_config = configuration.local_image_generation or configuration.local_generation
        assert output_config is not None
        generated_output_ingest = AssetIngestService(
            store=store,
            resolver=resolver,
            source_policy=SourcePathPolicy((output_config.project_output_root,)),
        )
        generation_output_adoption_application = Task027GenerationOutputAdoptionApplication(
            project_root=configuration.project_root,
            project_id=configuration.project_id,
            generation_execution=generation_execution_application,
            generation_queue=generation_queue_application,
            production_control=production_control,
            prompt_evidence=prompt_evidence_application,
            asset_port=Task027GeneratedOutputAssetPort(
                service=generated_output_ingest,
                project_output_root=output_config.project_output_root,
                production_job_id=configuration.production_job_id,
                owner=configuration.owner,
                max_output_bytes=max(
                    config.max_output_bytes
                    for config in (configuration.local_generation, configuration.local_image_generation)
                    if config is not None
                ),
            ),
        )
    final_review_application = FinalReviewApprovalApplication(
        project_root=configuration.project_root,
        project_id=configuration.project_id,
    )
    game_intelligence_application = GameIntelligenceShellApplication(
        configuration.project_root, connection_settings=connection_settings, provider_execution_service=game_intelligence_provider_service
    )
    if has_mutation_composition:
        # Validate the canonical manifest before creating a lock file.  This is
        # the only mutation-capable TASK-044 composition path in this launcher.
        ProductProjectManifestStore.load(configuration.project_root)
        runtime_lease = _Task036ProjectRuntimeLease.acquire(configuration.project_root)
    planning_generation_application = None
    try:
        def edit_persistence_provider():
            if runtime_lease is None:
                return None
            with runtime_lease.operation():
                controller = bridge._ensure_nle_controller()
                return None if controller is None else controller.edit_persistence_receipt()

        if connection_settings is not None and has_mutation_composition:
            planning_generation_application = Task036PlanningGenerationApplication(
                planning_application=planning_application,
                connection_provider=connection_settings.current_connection,
            )
        bridge = Task036ShellBridge(
            coordinator.shell,
            native_dialog=dialog,
            pre_edit_runtime=pre_edit,
            workflow_runtime_factory=downstream,
            production_control=production_control,
            audit_application=audit_application,
            planning_application=planning_application,
            planning_generation_application=planning_generation_application,
            generation_safety_application=generation_safety_application,
            continuity_application=continuity_application,
            prompt_evidence_application=prompt_evidence_application,
            generation_queue_application=generation_queue_application,
            generation_execution_application=generation_execution_application,
            generation_output_adoption_application=generation_output_adoption_application,
            audio_workspace_application=audio_workspace_application,
            audio_placement_application=audio_placement_application,
            quick_generation_application=quick_generation_application,
            connection_settings=connection_settings,
            final_review_application=final_review_application,
            final_review_external_gate_provider=final_review_external_gate_provider,
            final_review_edit_persistence_provider=edit_persistence_provider,
            final_review_export_preparation_provider=final_review_export_preparation_provider,
            game_intelligence_application=game_intelligence_application,
            nle_controller_factory=nle_controller,
            nle_runtime_guard=(
                None if runtime_lease is None else runtime_lease.operation
            ),
        )
        return Task036TrustedLaunch(
            configuration, coordinator, pre_edit, bridge, runtime_lease, store,
        )
    except BaseException:
        if runtime_lease is not None:
            runtime_lease.close()
        store.close()
        raise


def run_trusted_native_shell(config_path: str | Path) -> None:
    try:
        import webview  # type: ignore
    except ModuleNotFoundError as exc:
        raise ProductError(
            "ERR_TASK036_PYWEBVIEW_NOT_INSTALLED",
            "TASK-036 trusted native Shell requires pywebview",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
        ) from exc
    launch = build_trusted_launch(Task036LaunchConfiguration.load(config_path))
    try:
        webview.create_window(
            f"BAI Video Production — {launch.configuration.display_name}",
            html=HTML,
            js_api=launch.bridge,
            width=1600,
            height=900,
            min_size=(760, 600),
        )
        webview.start(gui="edgechromium", private_mode=True)
    finally:
        launch.close()
