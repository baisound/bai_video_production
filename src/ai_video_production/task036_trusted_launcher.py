"""Private launch configuration and composition root for TASK-036 W2.

The packaged WebView never receives this configuration. It is read once by the
trusted Python host and binds every path, Product port and external target before
the window is created.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .ai_connections import ConnectionAvailability
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
from .task044_nle_shell import Task044NleShellController
from .interactive_timeline_application import Task044TimelineEditApplication
from .interactive_timeline_projection import InteractiveTimelineProjectionService
from .export_queue_application import ExportQueueApplication
from .product_project_store import ProductProjectManifestStore
from .production_control_application import Task037ProductionControlApplication
from .audit_application import Task038AuditApplication
from .planning_application import Task027PlanningApplication
from .generation_safety_application import Task013GenerationSafetyApplication
from .continuity_application import Task039ContinuityApplication
from .connection_settings_web import ConnectionSettingsWebService
from .prompt_evidence_application import Task040PromptEvidenceApplication
from .generation_queue_application import Task027GenerationQueueApplication
from .audio_workspace_application import Task041AudioWorkspaceApplication
from .audio_placement_application import Task026AudioPlacementApplication
from .quick_generation_application import Task042QuickGenerationApplication
from .local_comfy_generation_port import (
    LocalComfyGenerationConfig, LocalComfyTextToVideoPort,
    MINIMAX_H3_NATIVE_WORKFLOW_SHA256, default_minimax_h3_workflow_path,
)
from .task036_workflow_runtime import Task036WorkflowRuntime
from .timebase import FrameRate


_MAX_CONFIG_BYTES = 256 * 1024


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

    @classmethod
    def load(cls, path: str | Path) -> "Task036LaunchConfiguration":
        source = Path(path)
        if source.is_symlink() or not source.is_file():
            raise ProductError(
                "ERR_TASK036_LAUNCH_CONFIG_FILE_INVALID",
                "TASK-036 launch configuration must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        if not 0 < source.stat().st_size <= _MAX_CONFIG_BYTES:
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
        if not isinstance(raw, dict) or raw.get("launch_config_version") not in {"1.0.0", "1.1.0"}:
            raise ValueError("unsupported launch_config_version")
        version = raw["launch_config_version"]
        allowed = {
            "launch_config_version", "project", "paths", "ingest", "asr", "resolve",
        }
        if version == "1.1.0":
            allowed.add("local_generation")
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
        if version == "1.1.0":
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
            local_roots = {
                name: _contained(
                    project_root,
                    _path(local_generation[name], field=f"local_generation.{name}"),
                    field=f"local_generation.{name}",
                )
                for name in ("comfy_output_root", "project_output_root", "staging_root", "dispatch_journal_root")
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
) -> Task036TrustedLaunch:
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

    store = SQLiteProductStore(configuration.database_path)
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
        product_version="0.21.0",
        project_id=configuration.project_id,
        display_name=configuration.display_name,
    )
    dialog = native_dialog or Task036NativeDialogService()
    pre_edit = Task036PreEditRuntime(coordinator, dialog, ingest_port, transcription_port, cut_port)
    adapter = resolve_adapter or ResolveScriptingAssemblyAdapter()

    def downstream(application):
        source_path = pre_edit.media.runtime_source_path
        if source_path is None:
            raise ProductError(
                "ERR_TASK036_RUNTIME_SOURCE_NOT_BOUND",
                "Trusted downstream runtime requires the exact selected source",
                ProductErrorCategory.STATE,
            )
        resolve = Task036ResolveWorkflowFacade(application)
        post_resolve = Task036PostResolveWorkflowFacade(application, resolve)
        return Task036WorkflowRuntime(
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
            connection_settings = ConnectionSettingsWebService.from_paths(
                connection_settings_path,
                None,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK028_CONNECTION_SETTINGS_INVALID",
                "AI Connection Settings failed current-valid validation",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"exception_type": type(exc).__name__},
            ) from exc

    def nle_controller(application) -> Task044NleShellController:
        timeline = InteractiveTimelineProjectionService.from_editing_projection(
            project_id=configuration.project_id,
            timeline_id=f"task036:{configuration.project_id}",
            timeline_rate=configuration.timeline_rate,
            projection=application.projection(),
        )
        edit_application = None
        export_application = None
        if ProductProjectManifestStore.path(configuration.project_root).exists():
            edit_application = Task044TimelineEditApplication(
                project_root=configuration.project_root, project_id=configuration.project_id,
            )
            export_application = ExportQueueApplication(
                project_root=configuration.project_root, project_id=configuration.project_id,
            )
        return Task044NleShellController(
            timeline=timeline, edit_application=edit_application,
            export_application=export_application,
        )
    generation_execution_application = None
    generation_output_adoption_application = None
    if configuration.local_generation is not None:
        local_client = comfy_client or ComfyUIClient(configuration.local_generation.endpoint)
        local_port = LocalComfyTextToVideoPort(config=configuration.local_generation, client=local_client)
        generation_execution_application = Task013CreativeGenerationExecutionApplication(
            project_root=configuration.project_root,
            project_id=configuration.project_id,
            generation_queue=generation_queue_application,
            execution_port=local_port,
            availability_factory=lambda: ConnectionAvailability(
                frozenset({configuration.local_generation.route_id})
            ),
        )
        generated_output_ingest = AssetIngestService(
            store=store,
            resolver=resolver,
            source_policy=SourcePathPolicy((configuration.local_generation.project_output_root,)),
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
                project_output_root=configuration.local_generation.project_output_root,
                production_job_id=configuration.production_job_id,
                owner=configuration.owner,
                max_output_bytes=configuration.local_generation.max_output_bytes,
            ),
        )
    bridge = Task036ShellBridge(
        coordinator.shell,
        native_dialog=dialog,
        pre_edit_runtime=pre_edit,
        workflow_runtime_factory=downstream,
        production_control=production_control,
        audit_application=audit_application,
        planning_application=planning_application,
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
        nle_controller_factory=nle_controller,
    )
    return Task036TrustedLaunch(configuration, coordinator, pre_edit, bridge)


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
    webview.create_window(
        f"BAI Video Production — {launch.configuration.display_name}",
        html=HTML,
        js_api=launch.bridge,
        width=1600,
        height=900,
        min_size=(760, 600),
    )
    webview.start(gui="edgechromium", private_mode=True)
