from __future__ import annotations

import json
import gc
from pathlib import Path
import sqlite3
import subprocess
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.faster_whisper_asr import FasterWhisperConfig
from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.task036_native_dialog import Task036NativeDialogService
from ai_video_production.task036_trusted_launcher import (
    Task036LaunchConfiguration,
    _handoff_subtitle_path,
    _resolve_asset_bindings,
    build_trusted_launch,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.audit_application import Task038AuditApplication
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.task036_planning_generation_application import Task036PlanningGenerationApplication
from ai_video_production.generation_safety_application import Task013GenerationSafetyApplication
from ai_video_production.continuity_application import Task039ContinuityApplication
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.generation_queue_application import Task027GenerationQueueApplication
from ai_video_production.audio_workspace_application import Task041AudioWorkspaceApplication
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.desktop_shell_projection import EditingProjection
from ai_video_production.desktop_media_workflow import IngestedMediaIdentity
from ai_video_production.durable_product_job import (
    DurableProductJobService,
    DurableProductJobState,
    DurableProductJobStore,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import sha256_bytes
from ai_video_production.store import SQLiteProductStore
from ai_video_production.local_comfy_image_generation_port import LocalComfyTextToImagePort
from ai_video_production.local_comfy_generation_port import LocalComfyTextToVideoPort
from ai_video_production.creative_generation_execution_application import LocalGenerationRuntimeReadiness
from ai_video_production.task036_native_image_vertical_cli import _load_config_scope
from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_pre_edit_runtime import LocalTranscriptionOutcome


class DialogBackend:
    def choose_open_media(self):
        return None

    def choose_project_folder(self):
        return None

    def choose_handoff_folder(self):
        return None


class AsrProvider:
    provider_id = "faster-whisper"
    model_id = "cached-local-model"
    config = FasterWhisperConfig(model="cached-local-model", allow_model_download=False)

    def transcribe(self, request):
        raise AssertionError("provider must not execute during launch")


class OwnerSigningKeyImportStub:
    def __init__(self, *, fail_close: bool = False):
        self.close_count = 0
        self.fail_close = fail_close

    def snapshot(self):
        return {
            "available": True,
            "state": "IDLE_NOT_CONFIGURED",
            "passphrase_exposed": False,
        }

    def close(self):
        self.close_count += 1
        if self.fail_close:
            raise RuntimeError("owner signing key import close failed")


class ExecutingAsrProvider:
    provider_id = "faster-whisper"
    model_id = "cached-local-model"
    config = FasterWhisperConfig(model="cached-local-model", allow_model_download=False)

    def __init__(self):
        self.calls = 0
        self.media_bytes = []

    def transcribe(self, request):
        self.calls += 1
        self.media_bytes.append(Path(request.media_path).read_bytes())
        return TranscriptManifest(
            request.source_asset_id,
            "ja",
            self.provider_id,
            self.model_id,
            (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
        )


class ResolveAdapter:
    def applied_hash(self, timeline_name):
        raise AssertionError("Resolve must not be inspected during launch")

    def assemble(self, plan, bindings):
        raise AssertionError("Resolve must not mutate during launch")


class ComfyClient:
    endpoint = "http://127.0.0.1:8188"

    def object_info(self):
        raise AssertionError("ComfyUI must not be inspected during launch")

    def system_stats(self):
        raise AssertionError("ComfyUI must not be inspected during launch")

    def queue(self, workflow, *, client_id):
        raise AssertionError("ComfyUI must not execute during launch")


def config_document(tmp_path: Path) -> tuple[Path, dict]:
    project = tmp_path / "private-project"
    source_root = tmp_path / "incoming"
    project.mkdir()
    source_root.mkdir()
    source = source_root / "source.mp4"
    source.write_bytes(b"source")
    analysis = project / "analysis.wav"
    analysis.write_bytes(b"wav")
    cache = project / "model-cache"
    cache.mkdir()
    raw = {
        "launch_config_version": "1.0.0",
        "project": {
            "project_id": "phase-g-w2-sandbox",
            "display_name": "Phase G W2 Sandbox",
            "project_root": str(project),
        },
        "paths": {
            "source_roots": [str(source_root)],
            "asset_root": str(project / "assets"),
            "job_root": str(project / "jobs"),
            "database_path": str(project / "product.sqlite3"),
            "analysis_source_path": str(source),
            "analysis_audio_path": str(analysis),
            "asr_cache_directory": str(cache),
            "transcription_output": str(project / "transcription"),
            "cut_output": str(project / "cut"),
            "handoff_destination": str(project / "handoff"),
            "native_render_evidence_root": str(project / "native-render"),
            "native_render_report_path": str(project / "native-render-report.json"),
        },
        "ingest": {
            "production_job_id": "JOB-00000000000000000000000000",
            "profile_snapshot_id": "PSN-00000000000000000000000000",
            "owner": "phase-g-owner",
        },
        "asr": {
            "model": "cached-local-model",
            "device": "cpu",
            "compute_type": "int8",
            "beam_size": 5,
            "vad_filter": True,
            "allow_model_download": False,
            "language": "ja",
        },
        "resolve": {
            "sandbox_project": "BAI_CAPABILITY_PROBE_PHASEG_TASK036_W2",
            "timeline_rate": "30",
            "source_frame_rate": "30",
        },
    }
    path = project / "task036-launch.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path, raw


def test_native_cli_loads_one_stable_launch_config_identity(tmp_path: Path):
    path, _raw = config_document(tmp_path)
    config, config_sha = _load_config_scope(path)
    assert config.project_id == "phase-g-w2-sandbox"
    assert config_sha == sha256_bytes(path.read_bytes())

    link = path.with_name("task036-launch-link.json")
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("symlink creation is unavailable on this test host")
    with pytest.raises(ProductError) as rejected:
        _load_config_scope(link)
    assert rejected.value.code == "ERR_TASK036_NATIVE_LAUNCH_CONFIG_INVALID"

    path.write_bytes(b" " * (256 * 1024 + 1))
    with pytest.raises(ProductError) as oversized:
        _load_config_scope(path)
    assert oversized.value.code == "ERR_TASK036_NATIVE_LAUNCH_CONFIG_INVALID"


def test_private_launch_config_builds_trusted_ports_without_provider_or_resolve_execution(tmp_path: Path):
    path, raw = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    assert launch.bridge.workflow_status()["next_recommended_action"] == "media.choose_and_ingest"
    assert launch.bridge.workflow_status()["host_paths_exposed"] is False
    assert launch.coordinator.shell.project.project_id == "phase-g-w2-sandbox"
    assert config.resolve_project == "BAI_CAPABILITY_PROBE_PHASEG_TASK036_W2"
    assert config.database_path.is_file()
    assert config.asset_root.is_dir()
    assert config.handoff_destination.is_dir()
    public = json.dumps([launch.bridge.snapshot(), launch.bridge.workflow_status()])
    assert str(config.project_root) not in public
    assert str(config.analysis_source_path) not in public
    assert isinstance(launch.bridge._production_control, Task037ProductionControlApplication)
    assert launch.bridge._production_control.project_root == config.project_root
    assert launch.bridge._production_control.project_id == config.project_id
    assert isinstance(launch.bridge._audit_application, Task038AuditApplication)
    assert launch.bridge._audit_application.project_root == config.project_root
    assert launch.bridge._audit_application.project_id == config.project_id

    assert isinstance(launch.bridge._planning_application, Task027PlanningApplication)
    assert launch.bridge._planning_application.project_root == config.project_root
    assert launch.bridge._planning_application.project_id == config.project_id
    assert launch.bridge._planning_application.production_control is launch.bridge._production_control
    assert isinstance(launch.bridge._generation_safety_application, Task013GenerationSafetyApplication)
    assert launch.bridge._generation_safety_application.project_root == config.project_root
    assert launch.bridge._generation_safety_application.project_id == config.project_id
    assert launch.bridge._generation_safety_application.planning_application is launch.bridge._planning_application
    assert launch.bridge._generation_safety_application.audit_application is launch.bridge._audit_application
    assert isinstance(launch.bridge._final_review_application, FinalReviewApprovalApplication)
    assert launch.bridge._final_review_application.project_root == config.project_root
    assert launch.bridge._final_review_external_gate_provider is None
    assert callable(launch.bridge._final_review_edit_persistence_provider)
    final_review = launch.bridge.final_review_snapshot({})
    assert final_review["approval"]["available"] is True
    assert final_review["export_job_created"] is False
    assert final_review["render_or_publish_started"] is False
    assert isinstance(launch.bridge._continuity_application, Task039ContinuityApplication)
    assert launch.bridge._continuity_application.project_root == config.project_root
    assert launch.bridge._continuity_application.project_id == config.project_id
    assert launch.bridge._continuity_application.production_control is launch.bridge._production_control
    continuity = launch.bridge.continuity_snapshot({})
    assert continuity["available"] is True
    assert continuity["provider_execution_started"] is False
    assert continuity["resolve_mutation_started"] is False
    assert isinstance(launch.bridge._prompt_evidence_application, Task040PromptEvidenceApplication)
    assert launch.bridge._prompt_evidence_application.project_root == config.project_root
    assert launch.bridge._prompt_evidence_application.project_id == config.project_id
    assert launch.bridge._prompt_evidence_application.production_control is launch.bridge._production_control
    assert launch.bridge._prompt_evidence_application.audit_application is launch.bridge._audit_application
    prompt_evidence = launch.bridge.prompt_evidence_snapshot({})
    assert prompt_evidence["available"] is True
    assert prompt_evidence["provider_execution_started"] is False
    assert prompt_evidence["candidate_creation_started"] is False
    assert isinstance(launch.bridge._generation_queue_application, Task027GenerationQueueApplication)
    assert launch.bridge._generation_queue_application.production_control is launch.bridge._production_control
    assert launch.bridge._generation_queue_application.planning_application is launch.bridge._planning_application
    assert launch.bridge._generation_queue_application.generation_safety_application is launch.bridge._generation_safety_application
    assert launch.bridge._generation_queue_application.continuity_application is launch.bridge._continuity_application
    assert launch.bridge._generation_queue_application.prompt_evidence_application is launch.bridge._prompt_evidence_application
    queue = launch.bridge.generation_queue_snapshot({})
    assert queue["available"] is True
    assert queue["provider_execution_started"] is False
    assert queue["paid_execution_authorized"] is False
    assert isinstance(launch.bridge._audio_workspace_application, Task041AudioWorkspaceApplication)
    assert launch.bridge._audio_workspace_application.production_control is launch.bridge._production_control
    audio = launch.bridge.audio_workspace_snapshot({})
    assert audio["available"] is True
    assert audio["provider_execution_started"] is False
    assert audio["task026_compile_started"] is False
    assert audio["resolve_mutation_started"] is False


def test_trusted_launch_owns_body_free_signing_key_service_lifetime(tmp_path: Path):
    path, _raw = config_document(tmp_path)
    service = OwnerSigningKeyImportStub()
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        owner_signing_key_import=service,
    )

    snapshot = launch.bridge.owner_signing_key_import_snapshot({})
    assert snapshot == {
        "available": True,
        "state": "IDLE_NOT_CONFIGURED",
        "passphrase_exposed": False,
    }
    assert launch._owner_signing_key_import is service

    launch.close()
    launch.close()
    assert service.close_count == 1
    assert launch._owner_signing_key_import is None


def test_trusted_launch_releases_other_resources_when_signing_service_close_fails(
    tmp_path: Path,
):
    path, _raw = config_document(tmp_path)
    service = OwnerSigningKeyImportStub(fail_close=True)
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        owner_signing_key_import=service,
    )

    with pytest.raises(RuntimeError, match="owner signing key import close failed"):
        launch.close()

    assert service.close_count == 1
    assert launch._owner_signing_key_import is None
    assert launch._local_operation_lifetime is None
    assert launch._runtime_lease is None
    assert launch._product_store is None
    launch.close()


def test_trusted_composition_transcribes_managed_asset_and_promotes_fixed_outputs(
    tmp_path: Path,
):
    path, raw = config_document(tmp_path)
    source = Path(raw["paths"]["analysis_source_path"])
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:r=24:d=0.2",
            "-c:v", "mpeg4", "-y", str(source),
        ],
        check=True,
    )

    class SelectionBackend(DialogBackend):
        def choose_open_media(self):
            return source

    provider = ExecutingAsrProvider()
    config = Task036LaunchConfiguration.load(path)
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(SelectionBackend()),
        asr_provider=provider,
        resolve_adapter=ResolveAdapter(),
    )
    bridge = launch.bridge
    ingested = bridge.choose_and_ingest_media({})
    assert ingested["status"] == "INGESTED"
    managed = launch.pre_edit_runtime.media.runtime_source_path
    assert managed is not None
    assert managed != source
    assert managed.is_relative_to(config.asset_root)
    assert managed.read_bytes() == source.read_bytes()
    source_bytes = source.read_bytes()
    source.unlink()

    prepared = bridge.prepare_local_transcription({})
    result = bridge.run_local_transcription(
        {"confirmation_id": prepared["confirmation_id"]},
    )
    assert result["provider_execution_started"] is True
    assert result["provider_execution_mode"] == "LOCAL"
    assert provider.calls == 1
    assert provider.media_bytes == [source_bytes]
    assert (config.transcription_output / "transcript.json").is_file()
    assert (config.transcription_output / "subtitles.srt").is_file()
    assert (config.transcription_output / "transcription-report.json").is_file()
    analysis_binding = launch.pre_edit_runtime.cut_candidate_port.analysis_audio
    assert analysis_binding.analysis_audio_for(managed) == config.analysis_audio_path.resolve()

    launch.close()
    with pytest.raises(ProductError) as closed:
        bridge.workflow_status({})
    assert closed.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    production = launch.bridge.production_snapshot({})
    assert production["available"] is True
    assert production["project_id"] == config.project_id
    assert production["provider_execution_started"] is False
    assert production["resolve_mutation_started"] is False


def test_trusted_launcher_can_refuse_missing_product_job_bootstrap(tmp_path: Path):
    path, _raw = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    store = SQLiteProductStore(config.database_path)
    with pytest.raises(ProductError) as missing_before:
        store.get_job_state(config.production_job_id)
    assert missing_before.value.code == "ERR_INPUT_JOB_NOT_FOUND"
    database_before = config.database_path.read_bytes()
    sidecars = tuple(
        config.database_path.with_name(config.database_path.name + suffix)
        for suffix in ("-wal", "-shm")
    )
    sidecars_before = {
        item: item.read_bytes() if item.exists() else None
        for item in sidecars
    }

    with pytest.raises(ProductError) as blocked:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
            allow_product_job_bootstrap=False,
        )
    assert blocked.value.code == "ERR_TASK036_TRUSTED_PROJECT_NOT_INITIALIZED"
    with pytest.raises(ProductError) as still_missing:
        store.get_job_state(config.production_job_id)
    assert still_missing.value.code == "ERR_INPUT_JOB_NOT_FOUND"
    assert config.database_path.read_bytes() == database_before
    assert {
        item: item.read_bytes() if item.exists() else None
        for item in sidecars
    } == sidecars_before


def test_trusted_launcher_refuses_partial_existing_database_without_mutation(tmp_path: Path):
    path, _raw = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    for directory in (
        config.asset_root,
        config.job_root,
        config.transcription_output,
        config.cut_output,
        config.handoff_destination,
        config.native_render_evidence_root.parent,
        config.native_render_report_path.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.database_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE production_jobs ("
            "job_id TEXT PRIMARY KEY, state TEXT NOT NULL, state_version INTEGER NOT NULL, "
            "profile_snapshot_id TEXT NOT NULL, resume_to_state TEXT, last_error_code TEXT, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO production_jobs VALUES (?,?,?,?,?,?,?,?)",
            (
                config.production_job_id,
                "CREATED",
                1,
                config.profile_snapshot_id,
                None,
                None,
                "2026-08-21T00:00:00.000Z",
                "2026-08-21T00:00:00.000Z",
            ),
        )
    before = config.database_path.read_bytes()
    sidecars = tuple(
        config.database_path.with_name(config.database_path.name + suffix)
        for suffix in ("-wal", "-shm")
    )
    sidecars_before = {
        item: item.read_bytes() if item.exists() else None
        for item in sidecars
    }
    with pytest.raises(ProductError) as blocked:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
            comfy_client=ComfyClient(),
            allow_product_job_bootstrap=False,
        )
    assert blocked.value.code == "ERR_STORE_EXISTING_DATABASE_INVALID"
    assert config.database_path.read_bytes() == before
    assert {
        item: item.read_bytes() if item.exists() else None
        for item in sidecars
    } == sidecars_before


@pytest.mark.parametrize(
    "interrupted_state", [DurableProductJobState.DISPATCHING, DurableProductJobState.RUNNING],
)
def test_trusted_launcher_lease_prevents_live_recovery_and_scopes_restart_recovery(
    tmp_path: Path, interrupted_state: DurableProductJobState,
) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.21.0",
            timebase=ProjectTimebase(config.timeline_rate.numerator, config.timeline_rate.denominator),
            child_bindings=(),
            created_at="2026-08-17T07:00:00.000Z",
            updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    first = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    class ProjectionApplication:
        def projection(self) -> EditingProjection:
            return EditingProjection(1_000_000, (), ())

    first.bridge._application = ProjectionApplication()  # type: ignore[assignment]
    first.bridge.export_queue_snapshot({})
    assert first.bridge._nle_controller is not None
    export = first.bridge._nle_controller.export_application
    assert export is not None
    job = DurableProductJobService().enqueue(
        config.project_root,
        kind="EXPORT",
        target_identity="export:restart-recovery",
        input_hashes={"final_approval": sha256_bytes(b"restart-approval")},
    )
    preflight = export.jobs.transition(
        config.project_root, job.job_id, DurableProductJobState.PREFLIGHT,
        expected_state_version=job.state_version,
    )
    ready = export.jobs.transition(
        config.project_root, job.job_id, DurableProductJobState.READY,
        expected_state_version=preflight.state_version,
    )
    dispatching = export.jobs.transition(
        config.project_root, job.job_id, DurableProductJobState.DISPATCHING,
        expected_state_version=ready.state_version,
    )
    live_state = dispatching
    if interrupted_state is DurableProductJobState.RUNNING:
        live_state = export.jobs.transition(
            config.project_root, job.job_id, DurableProductJobState.RUNNING,
            expected_state_version=dispatching.state_version,
        )
    non_export = DurableProductJobService().enqueue(
        config.project_root,
        kind="LOCAL_ANALYSIS",
        target_identity="analysis:restart-recovery",
        input_hashes={"source": sha256_bytes(b"restart-source")},
    )
    analysis_preflight = export.jobs.transition(
        config.project_root, non_export.job_id, DurableProductJobState.PREFLIGHT,
        expected_state_version=non_export.state_version,
    )
    analysis_ready = export.jobs.transition(
        config.project_root, non_export.job_id, DurableProductJobState.READY,
        expected_state_version=analysis_preflight.state_version,
    )
    analysis_dispatching = export.jobs.transition(
        config.project_root, non_export.job_id, DurableProductJobState.DISPATCHING,
        expected_state_version=analysis_ready.state_version,
    )
    analysis_running = export.jobs.transition(
        config.project_root, non_export.job_id, DurableProductJobState.RUNNING,
        expected_state_version=analysis_dispatching.state_version,
    )

    with pytest.raises(ProductError) as exc:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
        )
    assert exc.value.code == "ERR_TASK036_RUNTIME_ALREADY_ACTIVE"
    live_export = DurableProductJobStore.load(config.project_root).get(job.job_id)
    assert live_export.state is interrupted_state
    assert live_export.state_version == live_state.state_version

    old_bridge = first.bridge
    first.close()
    first.close()
    for operation, args in (
        (old_bridge.export_queue_snapshot, {}),
        (old_bridge.export_queue_prepare_dispatch, {}),
        (old_bridge.export_queue_cancel, {}),
        (old_bridge.interactive_timeline_snapshot, {}),
        (old_bridge.interactive_timeline_select, {}),
    ):
        with pytest.raises(ProductError) as exc:
            operation(args)
        assert exc.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    with pytest.raises(ProductError) as exc:
        old_bridge._final_review_edit_persistence_provider()
    assert exc.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert DurableProductJobStore.load(config.project_root).get(job.job_id) == live_export
    restarted = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    assert restarted.bridge._nle_controller is None
    restarted.bridge._application = ProjectionApplication()  # type: ignore[assignment]
    restarted.bridge.export_queue_snapshot({})
    recovered = DurableProductJobStore.load(config.project_root).get(job.job_id)
    assert recovered.state is DurableProductJobState.UNKNOWN
    assert recovered.state_version == live_state.state_version + 1
    preserved_analysis = DurableProductJobStore.load(config.project_root).get(non_export.job_id)
    assert preserved_analysis == analysis_running
    restarted.bridge.export_queue_snapshot({})
    assert DurableProductJobStore.load(config.project_root).get(job.job_id) == recovered
    restarted.close()


def test_collected_launch_leaves_cached_bridge_lease_inactive_and_allows_successor(tmp_path: Path) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.21.0",
            timebase=ProjectTimebase(config.timeline_rate.numerator, config.timeline_rate.denominator),
            child_bindings=(),
            created_at="2026-08-17T07:00:00.000Z",
            updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    class ProjectionApplication:
        def projection(self) -> EditingProjection:
            return EditingProjection(1_000_000, (), ())

    bridge = launch.bridge
    bridge._application = ProjectionApplication()  # type: ignore[assignment]
    assert bridge.export_queue_snapshot({})["available"] is True
    del launch
    gc.collect()
    successor = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    with pytest.raises(ProductError) as exc:
        bridge.export_queue_snapshot({})
    assert exc.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    successor.close()


def test_close_waits_for_inflight_export_mutation_before_releasing_runtime_lease(tmp_path: Path) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.21.0",
            timebase=ProjectTimebase(config.timeline_rate.numerator, config.timeline_rate.denominator),
            child_bindings=(),
            created_at="2026-08-17T07:00:00.000Z",
            updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    class ProjectionApplication:
        def projection(self) -> EditingProjection:
            return EditingProjection(1_000_000, (), ())

    bridge = launch.bridge
    bridge._application = ProjectionApplication()  # type: ignore[assignment]
    bridge.export_queue_snapshot({})
    controller = bridge._nle_controller
    assert controller is not None and controller.export_application is not None
    assert controller.visual_asset_placement is not None
    export = controller.export_application
    job = DurableProductJobService().enqueue(
        config.project_root, kind="EXPORT", target_identity="export:lease-barrier",
        input_hashes={"final_approval": sha256_bytes(b"lease-barrier")},
    )
    entered, release = Event(), Event()
    original_cancel = export.cancel

    def blocking_cancel(*, job_id: str, expected_state_version: int):
        entered.set()
        assert release.wait(5)
        return original_cancel(job_id=job_id, expected_state_version=expected_state_version)

    export.cancel = blocking_cancel  # type: ignore[method-assign]
    result: list[dict[str, object]] = []
    operation_thread = Thread(
        target=lambda: result.append(bridge.export_queue_cancel({
            "job_id": job.job_id, "expected_state_version": job.state_version,
        })),
    )
    operation_thread.start()
    assert entered.wait(5)
    lease = launch._runtime_lease
    assert lease is not None
    close_thread = Thread(target=launch.close)
    close_thread.start()
    deadline = monotonic() + 5
    while not lease._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lease._closing  # type: ignore[attr-defined]
    with pytest.raises(ProductError) as old_call:
        bridge.export_queue_snapshot({})
    assert old_call.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    with pytest.raises(ProductError) as successor_error:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
        )
    assert successor_error.value.code == "ERR_TASK036_RUNTIME_ALREADY_ACTIVE"
    assert DurableProductJobStore.load(config.project_root).get(job.job_id) == job
    release.set()
    operation_thread.join(5)
    close_thread.join(5)
    assert not operation_thread.is_alive() and not close_thread.is_alive()
    assert result == [{
        "job_id": job.job_id, "state": "CANCELLED", "state_version": job.state_version + 1,
        "external_mutation_started": False,
    }]
    successor = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    assert DurableProductJobStore.load(config.project_root).get(job.job_id).state is DurableProductJobState.CANCELLED
    successor.close()


def test_admitted_lazy_factory_finishes_after_close_starts_and_self_close_is_rejected(tmp_path: Path) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id, project_revision=1, product_version="0.21.0",
            timebase=ProjectTimebase(config.timeline_rate.numerator, config.timeline_rate.denominator),
            child_bindings=(), created_at="2026-08-17T07:00:00.000Z",
            updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    launch = build_trusted_launch(
        config, native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(), resolve_adapter=ResolveAdapter(),
    )
    class ProjectionApplication:
        def projection(self) -> EditingProjection:
            return EditingProjection(1_000_000, (), ())

    bridge = launch.bridge
    bridge._application = ProjectionApplication()  # type: ignore[assignment]
    original_factory = bridge._nle_controller_factory
    assert original_factory is not None
    entered, release = Event(), Event()

    def pausing_factory(application):
        entered.set()
        assert release.wait(5)
        return original_factory(application)

    bridge._nle_controller_factory = pausing_factory
    snapshot: list[dict[str, object]] = []
    operation_thread = Thread(target=lambda: snapshot.append(bridge.export_queue_snapshot({})))
    operation_thread.start()
    assert entered.wait(5)
    close_thread = Thread(target=launch.close)
    close_thread.start()
    lease = launch._runtime_lease
    assert lease is not None
    deadline = monotonic() + 5
    while not lease._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lease._closing  # type: ignore[attr-defined]
    release.set()
    operation_thread.join(5)
    close_thread.join(5)
    assert snapshot and snapshot[0]["available"] is True
    assert not operation_thread.is_alive() and not close_thread.is_alive()

    retry = build_trusted_launch(
        config, native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(), resolve_adapter=ResolveAdapter(),
    )
    retry_lease = retry._runtime_lease
    assert retry_lease is not None
    with retry_lease.operation():
        with pytest.raises(ProductError) as exc:
            retry.close()
    assert exc.value.code == "ERR_TASK036_RUNTIME_CLOSE_IN_FLIGHT"
    assert retry._runtime_lease is retry_lease
    retry.close()


@pytest.mark.parametrize("dangling", [False, True])
def test_trusted_launcher_runtime_lease_rejects_valid_and_dangling_symlinks(
    tmp_path: Path, dangling: bool,
) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.21.0",
            timebase=ProjectTimebase(config.timeline_rate.numerator, config.timeline_rate.denominator),
            child_bindings=(),
            created_at="2026-08-17T07:00:00.000Z",
            updated_at="2026-08-17T07:00:00.000Z",
        ),
    )
    lock_path = config.project_root / ".bai-project" / ".task036-runtime.lock"
    target = lock_path.with_name("runtime-lock-target")
    try:
        if not dangling:
            target.write_bytes(b"0")
            lock_path.symlink_to(target)
        else:
            lock_path.symlink_to(lock_path.with_name("missing-runtime-lock"))
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError) as exc:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
        )
    assert exc.value.code == "ERR_TASK036_RUNTIME_LEASE_INVALID"
    assert lock_path.is_symlink()


def test_trusted_launcher_without_manifest_creates_no_runtime_lease_or_job_store(tmp_path: Path) -> None:
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    assert not (config.project_root / ".bai-project" / ".task036-runtime.lock").exists()
    assert not DurableProductJobStore.path(config.project_root).exists()
    launch.close()


def test_pre_manifest_media_ingest_holds_launch_lifetime_until_operation_finishes(tmp_path: Path) -> None:
    path, raw = config_document(tmp_path)
    source = Path(raw["paths"]["analysis_source_path"])
    entered, release = Event(), Event()

    class BlockingDialogBackend(DialogBackend):
        calls = 0

        def choose_open_media(self):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return str(source)

    dialog_backend = BlockingDialogBackend()
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(dialog_backend),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    ingested = []

    class IngestStub:
        def ingest_local_media(self, source_path):
            assert launch._product_store is not None
            ingested.append(source_path)
            return IngestedMediaIdentity(
                "ASSET-00000000000000000000000000", "sha256:" + "a" * 64,
                source_path,
            )

    launch.pre_edit_runtime.media.ingest_port = IngestStub()
    bridge = launch.bridge
    completed = []
    operation = Thread(target=lambda: completed.append(bridge.choose_and_ingest_media({})))
    operation.start()
    assert entered.wait(5)
    lifetime = launch._local_operation_lifetime
    assert lifetime is not None
    closing = Thread(target=launch.close)
    closing.start()
    deadline = monotonic() + 5
    while not lifetime._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lifetime._closing  # type: ignore[attr-defined]
    assert closing.is_alive()
    with pytest.raises(ProductError) as rejected:
        bridge.choose_and_ingest_media({})
    assert rejected.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert dialog_backend.calls == 1
    release.set()
    operation.join(5)
    closing.join(5)
    assert not operation.is_alive() and not closing.is_alive()
    assert completed[0]["status"] == "INGESTED"
    assert completed[0]["asset_sha256"].startswith("sha256:")
    assert ingested == [source]
    with pytest.raises(ProductError) as after_close:
        bridge.choose_and_ingest_media({})
    assert after_close.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert dialog_backend.calls == 1
    assert launch._product_store is None


def test_pre_manifest_transcription_holds_launch_lifetime_and_old_bridge_cannot_reexecute(tmp_path: Path) -> None:
    path, raw = config_document(tmp_path)
    source = Path(raw["paths"]["analysis_source_path"])

    class SourceDialogBackend(DialogBackend):
        def choose_open_media(self):
            return str(source)

    entered, release = Event(), Event()

    class BlockingTranscriptionPort:
        calls = 0

        def transcribe_local_media(self, *, project_id, source_path, source_asset_id, source_asset_sha256):
            self.calls += 1
            assert source_path == source
            entered.set()
            assert release.wait(5)
            return LocalTranscriptionOutcome(
                TranscriptManifest(
                    source_asset_id, "ja", "faster-whisper", "local-cached-model",
                    (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
                ), True,
            )

    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(SourceDialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )

    class IngestStub:
        def ingest_local_media(self, source_path):
            return IngestedMediaIdentity(
                "ASSET-00000000000000000000000000", "sha256:" + "a" * 64,
                source_path,
            )

    transcription = BlockingTranscriptionPort()
    launch.pre_edit_runtime.media.ingest_port = IngestStub()
    launch.pre_edit_runtime.transcription_port = transcription
    bridge = launch.bridge
    assert bridge.choose_and_ingest_media({})["status"] == "INGESTED"
    completed = []
    prepared = bridge.prepare_local_transcription({})
    operation = Thread(target=lambda: completed.append(bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})))
    operation.start()
    assert entered.wait(5)
    lifetime = launch._local_operation_lifetime
    assert lifetime is not None
    closing = Thread(target=launch.close)
    closing.start()
    deadline = monotonic() + 5
    while not lifetime._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lifetime._closing  # type: ignore[attr-defined]
    assert closing.is_alive()
    with pytest.raises(ProductError) as rejected:
        bridge.run_local_transcription({"confirmation_id": "blocked-after-close"})
    assert rejected.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert transcription.calls == 1
    release.set()
    operation.join(5)
    closing.join(5)
    assert not operation.is_alive() and not closing.is_alive()
    assert completed[0]["status"] == "TRANSCRIBED"
    assert completed[0]["transcript_text_exposed"] is False
    with pytest.raises(ProductError) as after_close:
        bridge.run_local_transcription({"confirmation_id": "blocked-after-close"})
    assert after_close.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert transcription.calls == 1
    assert launch._product_store is None


def test_trusted_launch_binds_existing_task028_settings_without_provider_execution(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    profile = AiConnectionProfile(
        "desktop-profile",
        "1",
        SelectionMode.OFFLINE_ONLY,
        (
            ModelRoute(
                "local-image",
                AiWorkload.IMAGE,
                ProviderFamily.COMFYUI,
                "comfyui",
                "workflow-v1",
                CostClass.LOCAL_FREE_AI,
                capabilities=("IMAGE_GENERATION",),
            ),
        ),
    )
    ConnectionSettingsStore.save(project / "ai-connection-settings.json", profile)
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    snapshot = launch.bridge.connection_settings_snapshot({})
    assert snapshot["available"] is True
    assert snapshot["profile_id"] == "desktop-profile"
    assert snapshot["revision"] == 1
    assert snapshot["provider_execution_started"] is False
    assert snapshot["generation_started"] is False
    assert snapshot["credential_values_redisplayed"] is False
    assert launch.bridge._planning_generation_application is None
    assert launch.bridge.planning_generation_status({})["available"] is False


def test_trusted_launcher_binds_local_free_planning_and_invalidates_old_bridge_on_close(tmp_path: Path):
    path, raw = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.22.0",
            timebase=ProjectTimebase(
                config.timeline_rate.numerator,
                config.timeline_rate.denominator,
            ),
            child_bindings=(),
        ),
    )
    profile = AiConnectionProfile(
        "local-planning-profile",
        "1.0.0",
        SelectionMode.OFFLINE_ONLY,
        (
            ModelRoute(
                "planning-local",
                AiWorkload.PLANNING,
                ProviderFamily.LOCAL_OPEN_SOURCE,
                "ollama",
                "qwen3:8b",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_GENERATION",),
            ),
        ),
    )
    ConnectionSettingsStore.save(
        Path(raw["project"]["project_root"]) / "ai-connection-settings.json",
        profile,
    )
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )
    bridge = launch.bridge
    assert isinstance(
        bridge._planning_generation_application,
        Task036PlanningGenerationApplication,
    )
    assert bridge._planning_generation_application.planning is bridge._planning_application
    assert bridge.planning_generation_status({})["available"] is True
    expected = bridge.planning_snapshot({})["snapshot_sha256"]
    launch.close()
    closed_status = bridge.planning_generation_status({})
    assert closed_status["available"] is False
    assert closed_status["blocker_code"] == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    with pytest.raises(ProductError) as exc:
        bridge.planning_generation_prepare({
            "vague_request": "must not reach Ollama",
            "expected_planning_snapshot_sha256": expected,
        })
    assert exc.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"


def test_v11_launch_explicitly_composes_bounded_local_generation_without_execution(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    roots = {name: project / name for name in ("comfy-output", "generation-output", "generation-stage", "generation-journal")}
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.1.0"
    raw["local_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(roots["comfy-output"]),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["generation-stage"]),
        "dispatch_journal_root": str(roots["generation-journal"]),
        "route_id": "local-video",
        "provider_id": "comfy",
        "model_id": "minimax-h3-native",
        "width": 832,
        "height": 480,
        "length": 124,
        "steps": 20,
        "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024**3,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = Task036LaunchConfiguration.load(path)
    assert config.local_generation is not None
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(),
    )
    assert launch.bridge._generation_execution_application is not None
    execution = launch.bridge._generation_execution_application
    assert isinstance(execution.execution_port, LocalComfyTextToVideoPort)
    assert execution.execution_port_selector is None
    execution.execution_port.preflight = lambda: LocalGenerationRuntimeReadiness(
        "local-video", "comfy", "minimax-h3-native",
        "sha256:" + "8" * 64, 13,
        "DEFAULT_DYNAMIC_VRAM_INCIDENT_HARDENED_V1",
    )
    assert launch.bridge.generation_execution_preflight({})["route_id"] == "local-video"
    assert launch.bridge._generation_output_adoption_application is not None
    snapshot = launch.bridge.generation_execution_snapshot({})
    assert snapshot["available"] is True
    assert snapshot["events"] == []
    assert snapshot["paid_execution_authorized"] is False
    combined = launch.bridge.generation_queue_snapshot({})
    assert combined["output_adoption_control"]["available"] is True
    assert combined["output_adoption_control"]["eligible_completed_outputs"] == []
    assert combined["output_adoption_control"]["publication_authorized"] is False
    assert not any(roots["generation-output"].iterdir())


def test_v11_local_generation_rejects_non_loopback_or_out_of_project_root(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    roots = {name: project / name for name in ("comfy-output", "generation-output", "generation-stage", "generation-journal")}
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.1.0"
    raw["local_generation"] = {
        "endpoint": "https://example.com:8188",
        "comfy_output_root": str(roots["comfy-output"]),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["generation-stage"]),
        "dispatch_journal_root": str(roots["generation-journal"]),
        "route_id": "local-video", "provider_id": "comfy", "model_id": "minimax-h3-native",
        "width": 832, "height": 480, "length": 124, "steps": 20,
        "poll_interval_seconds": 1.0, "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024**3,
    }
    with pytest.raises(ValueError):
        Task036LaunchConfiguration.from_dict(raw)

    raw["local_generation"]["endpoint"] = "http://127.0.0.1:8188"
    external_comfy = tmp_path / "external-comfy"
    external_comfy.mkdir()
    raw["local_generation"]["comfy_output_root"] = str(external_comfy)
    with pytest.raises(ValueError):
        Task036LaunchConfiguration.from_dict(raw)
    raw["local_generation"]["comfy_output_root"] = str(roots["comfy-output"])
    outside = tmp_path / "outside"
    outside.mkdir()
    raw["local_generation"]["project_output_root"] = str(outside)
    with pytest.raises(ValueError):
        Task036LaunchConfiguration.from_dict(raw)


def test_v11_local_generation_remains_required_for_backward_compatibility(tmp_path: Path):
    _path, raw = config_document(tmp_path)
    raw["launch_config_version"] = "1.1.0"
    raw["local_generation"] = None
    with pytest.raises(ValueError, match="requires local_generation"):
        Task036LaunchConfiguration.from_dict(raw)


def test_v12_launch_composes_image_selector_without_provider_execution(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    runtime_output = tmp_path / "external-comfy-output"
    roots = {
        name: project / name
        for name in ("generation-output", "image-stage", "image-journal")
    }
    runtime_output.mkdir()
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.2.0"
    raw["local_generation"] = None
    raw["local_image_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(runtime_output),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["image-stage"]),
        "dispatch_journal_root": str(roots["image-journal"]),
        "route_id": "local-image",
        "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8",
        "width": 64,
        "height": 64,
        "steps": 4,
        "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024 * 1024,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = Task036LaunchConfiguration.load(path)
    assert config.local_generation is None
    assert config.local_image_generation is not None
    assert config.local_image_generation.comfy_output_root == runtime_output
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.22.0",
            timebase=ProjectTimebase(
                config.timeline_rate.numerator, config.timeline_rate.denominator,
            ),
            child_bindings=(),
            created_at="2026-08-21T00:00:00.000Z",
            updated_at="2026-08-21T00:00:00.000Z",
        ),
    )
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(),
    )
    application = launch.bridge._generation_execution_application
    assert application is not None
    assert isinstance(application.execution_port, LocalComfyTextToImagePort)
    assert application.execution_port_selector is None
    assert not any(runtime_output.iterdir())
    assert not any(roots["generation-output"].iterdir())
    assert not any(roots["image-journal"].iterdir())
    bridge = launch.bridge
    launch.close()
    with pytest.raises(ProductError) as closed:
        bridge.generation_execution_snapshot({})
    assert closed.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert not any(runtime_output.iterdir())


def test_v12_image_config_rejects_project_output_escape_and_empty_runtimes(tmp_path: Path):
    _path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    runtime_output = tmp_path / "external-comfy-output"
    runtime_output.mkdir()
    for name in ("generation-output", "image-stage", "image-journal"):
        (project / name).mkdir()
    raw["launch_config_version"] = "1.2.0"
    raw["local_generation"] = None
    raw["local_image_generation"] = None
    with pytest.raises(ValueError):
        Task036LaunchConfiguration.from_dict(raw)
    raw["local_image_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(runtime_output),
        "project_output_root": str(tmp_path / "outside-project"),
        "staging_root": str(project / "image-stage"),
        "dispatch_journal_root": str(project / "image-journal"),
        "route_id": "local-image", "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8", "width": 64, "height": 64,
        "steps": 4, "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024 * 1024,
    }
    with pytest.raises(ValueError):
        Task036LaunchConfiguration.from_dict(raw)


def test_v12_dual_runtime_shares_external_comfy_root_and_selects_exact_ports(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    runtime_output = tmp_path / "external-comfy-output"
    runtime_output.mkdir()
    roots = {
        name: project / name
        for name in (
            "generation-output",
            "video-stage",
            "video-journal",
            "image-stage",
            "image-journal",
        )
    }
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.2.0"
    raw["local_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(runtime_output),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["video-stage"]),
        "dispatch_journal_root": str(roots["video-journal"]),
        "route_id": "local-video",
        "provider_id": "comfy-video",
        "model_id": "minimax-h3-native",
        "width": 832,
        "height": 480,
        "length": 124,
        "steps": 20,
        "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024**3,
    }
    raw["local_image_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(runtime_output),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["image-stage"]),
        "dispatch_journal_root": str(roots["image-journal"]),
        "route_id": "local-image",
        "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8",
        "width": 64,
        "height": 64,
        "steps": 4,
        "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024 * 1024,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = Task036LaunchConfiguration.load(path)
    assert config.local_generation.comfy_output_root == runtime_output
    assert config.local_image_generation.comfy_output_root == runtime_output
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(),
    )
    application = launch.bridge._generation_execution_application
    assert application is not None
    assert application.execution_port is None
    assert application.execution_port_selector is not None
    image = application.execution_port_selector(
        ModelRoute(
            "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
            "comfy-image", "flux-schnell-fp8", CostClass.LOCAL_FREE_AI,
            capabilities=("TEXT_TO_IMAGE",),
        ),
        "TEXT_TO_IMAGE",
    )
    video = application.execution_port_selector(
        ModelRoute(
            "local-video", AiWorkload.VIDEO, ProviderFamily.COMFYUI,
            "comfy-video", "minimax-h3-native", CostClass.LOCAL_FREE_AI,
            capabilities=("TEXT_TO_VIDEO",),
        ),
        "TEXT_TO_VIDEO",
    )
    assert isinstance(image, LocalComfyTextToImagePort)
    assert isinstance(video, LocalComfyTextToVideoPort)
    route_body = {
        "route_id": "local-image",
        "workload": AiWorkload.IMAGE,
        "provider_family": ProviderFamily.COMFYUI,
        "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8",
        "cost_class": CostClass.LOCAL_FREE_AI,
        "capabilities": ("TEXT_TO_IMAGE",),
    }
    for override in (
        {"enabled": False},
        {"workload": AiWorkload.VIDEO},
        {"cost_class": CostClass.CLOUD_PAID_AI},
        {"credential_ref": "credential://must-not-be-used"},
        {"endpoint_ref": "endpoint://must-not-be-used"},
        {"settings": {"ignored": True}},
        {"capabilities": ("TEXT_TO_IMAGE", "TEXT_TO_VIDEO")},
    ):
        with pytest.raises(ProductError) as unbound:
            application.execution_port_selector(
                ModelRoute(**{**route_body, **override}),
                "TEXT_TO_IMAGE",
            )
        assert unbound.value.code == "ERR_TASK036_LOCAL_GENERATION_ROUTE_UNBOUND"
    assert not any(runtime_output.iterdir())
    launch.close()


def test_generation_and_adoption_bridge_obey_inflight_close_lease_barrier(tmp_path: Path):
    path, raw = config_document(tmp_path)
    project = Path(raw["project"]["project_root"])
    runtime_output = tmp_path / "external-comfy-output"
    runtime_output.mkdir()
    roots = {
        name: project / name
        for name in ("generation-output", "image-stage", "image-journal")
    }
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.2.0"
    raw["local_generation"] = None
    raw["local_image_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(runtime_output),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["image-stage"]),
        "dispatch_journal_root": str(roots["image-journal"]),
        "route_id": "local-image", "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8", "width": 64, "height": 64,
        "steps": 4, "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600,
        "max_output_bytes": 16 * 1024 * 1024,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = Task036LaunchConfiguration.load(path)
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.22.0",
            timebase=ProjectTimebase(
                config.timeline_rate.numerator, config.timeline_rate.denominator,
            ),
            child_bindings=(),
            created_at="2026-08-21T00:00:00.000Z",
            updated_at="2026-08-21T00:00:00.000Z",
        ),
    )
    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(),
    )
    bridge = launch.bridge
    entered, release = Event(), Event()
    counters = {"provider": 0, "execution_store": 0, "asset": 0}

    class BlockingExecution:
        def apply_execution(self, *, confirmation_id):
            assert confirmation_id == "inflight-confirm"
            entered.set()
            assert release.wait(5)
            counters["provider"] += 1
            counters["execution_store"] += 1
            return {"events": [{"state": "COMPLETED"}]}

        def snapshot(self):
            return {
                "execution_snapshot_sha256": "sha256:" + "2" * 64,
                "latest_executions": [],
                "recovery": {"required": False},
            }

    class BlockingAdoption:
        def apply_adoption(self, *, confirmation_id):
            counters["asset"] += 1
            return {"confirmation_id": confirmation_id}

        def snapshot(self):
            return {
                "adoption_snapshot_sha256": "sha256:" + "3" * 64,
                "latest_adoptions": [],
                "eligible_completed_outputs": [],
                "recovery": {"required": False},
            }

    bridge._generation_execution_application = BlockingExecution()
    bridge._generation_output_adoption_application = BlockingAdoption()
    result = []
    operation_thread = Thread(
        target=lambda: result.append(
            bridge.generation_execution_apply({"confirmation_id": "inflight-confirm"})
        ),
    )
    operation_thread.start()
    assert entered.wait(5)
    lease = launch._runtime_lease
    assert lease is not None
    close_thread = Thread(target=launch.close)
    close_thread.start()
    deadline = monotonic() + 5
    while not lease._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lease._closing  # type: ignore[attr-defined]
    assert counters == {"provider": 0, "execution_store": 0, "asset": 0}
    with pytest.raises(ProductError) as rejected_execution:
        bridge.generation_execution_apply({"confirmation_id": "new-confirm"})
    assert rejected_execution.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    with pytest.raises(ProductError) as rejected_adoption:
        bridge.generation_output_adoption_apply({"confirmation_id": "adopt-confirm"})
    assert rejected_adoption.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert counters == {"provider": 0, "execution_store": 0, "asset": 0}
    with pytest.raises(ProductError) as successor_error:
        build_trusted_launch(
            config,
            native_dialog=Task036NativeDialogService(DialogBackend()),
            asr_provider=AsrProvider(),
            resolve_adapter=ResolveAdapter(),
            comfy_client=ComfyClient(),
        )
    assert successor_error.value.code == "ERR_TASK036_RUNTIME_ALREADY_ACTIVE"
    release.set()
    operation_thread.join(5)
    close_thread.join(5)
    assert not operation_thread.is_alive() and not close_thread.is_alive()
    assert result == [{"events": [{"state": "COMPLETED"}]}]
    assert counters == {"provider": 1, "execution_store": 1, "asset": 0}
    with pytest.raises(ProductError) as after_close:
        bridge.generation_output_adoption_apply({"confirmation_id": "after-close"})
    assert after_close.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert counters == {"provider": 1, "execution_store": 1, "asset": 0}
    successor = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(),
    )
    successor.close()


def test_trusted_resolve_bindings_use_managed_derived_subtitle_path(tmp_path: Path):
    path, _ = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    bindings = _resolve_asset_bindings(config, config.analysis_source_path)
    assert bindings.subtitle_srt_path == config.transcription_output / "subtitles.srt"
    assert bindings.subtitle_derived_srt_path == config.transcription_output / "subtitles.edit-aware.srt"
    assert bindings.subtitle_derived_srt_path.is_relative_to(config.project_root)


def test_empty_runtime_subtitle_is_omitted_from_editor_handoff(tmp_path: Path):
    empty = tmp_path / "subtitles.srt"
    empty.write_bytes(b"")
    assert _handoff_subtitle_path(empty) is None
    empty.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
    assert _handoff_subtitle_path(empty) == empty


def test_launch_config_rejects_paths_outside_private_project_root(tmp_path: Path):
    path, raw = config_document(tmp_path)
    raw["paths"]["handoff_destination"] = str(tmp_path / "outside")
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036LaunchConfiguration.load(path)
    assert exc.value.code == "ERR_TASK036_LAUNCH_CONFIG_INVALID"


def test_launch_config_rejects_model_download_and_non_sandbox_resolve_target(tmp_path: Path):
    path, raw = config_document(tmp_path)
    raw["asr"]["allow_model_download"] = True
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError):
        Task036LaunchConfiguration.load(path)

    raw["asr"]["allow_model_download"] = False
    raw["resolve"]["sandbox_project"] = "HumanProject"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError):
        Task036LaunchConfiguration.load(path)


def test_launch_config_rejects_unknown_top_level_authority(tmp_path: Path):
    path, raw = config_document(tmp_path)
    raw["external_write_authorized"] = True
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036LaunchConfiguration.load(path)
    assert exc.value.code == "ERR_TASK036_LAUNCH_CONFIG_INVALID"


def test_launch_config_rejects_unknown_nested_authority(tmp_path: Path):
    path, raw = config_document(tmp_path)
    raw["resolve"]["external_write_authorized"] = True
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036LaunchConfiguration.load(path)
    assert exc.value.code == "ERR_TASK036_LAUNCH_CONFIG_INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    (("beam_size", "5"), ("beam_size", True), ("vad_filter", "false")),
)
def test_launch_config_rejects_ambiguous_asr_types(tmp_path: Path, field: str, value: object):
    path, raw = config_document(tmp_path)
    raw["asr"][field] = value
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036LaunchConfiguration.load(path)
    assert exc.value.code == "ERR_TASK036_LAUNCH_CONFIG_INVALID"


def test_launch_config_rejects_explicit_symlink_path(tmp_path: Path):
    path, raw = config_document(tmp_path)
    target = Path(raw["paths"]["analysis_audio_path"])
    link = target.with_name("analysis-link.wav")
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this test host")
    raw["paths"]["analysis_audio_path"] = str(link)
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036LaunchConfiguration.load(path)
    assert exc.value.code == "ERR_TASK036_LAUNCH_CONFIG_INVALID"


def test_subtitle_stage_holds_launch_lifetime_and_old_bridge_cannot_reexecute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, raw = config_document(tmp_path)
    source = Path(raw["paths"]["analysis_source_path"])

    class SourceDialogBackend(DialogBackend):
        def choose_open_media(self):
            return str(source)

    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(SourceDialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )

    class IngestStub:
        def ingest_local_media(self, source_path):
            return IngestedMediaIdentity(
                "ASSET-00000000000000000000000000",
                "sha256:" + "a" * 64,
                source_path,
            )

    runtime = launch.pre_edit_runtime
    runtime.media.ingest_port = IngestStub()
    bridge = launch.bridge
    assert bridge.choose_and_ingest_media({})["status"] == "INGESTED"
    runtime.binding.bind_transcript(
        TranscriptManifest(
            "ASSET-00000000000000000000000000",
            "ja",
            "faster-whisper",
            "local-cached-model",
            (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
        )
    )
    entered, release = Event(), Event()
    runtime_type = runtime.__class__
    original = runtime_type.create_subtitle_workspace

    def blocking_create(self):
        assert self is runtime
        entered.set()
        assert release.wait(5)
        return original(self)

    monkeypatch.setattr(runtime_type, "create_subtitle_workspace", blocking_create)
    completed: list[dict[str, object]] = []
    operation = Thread(
        target=lambda: completed.append(bridge.create_runtime_subtitle_workspace({}))
    )
    operation.start()
    assert entered.wait(5)
    lifetime = launch._local_operation_lifetime
    assert lifetime is not None
    closing = Thread(target=launch.close)
    closing.start()
    deadline = monotonic() + 5
    while not lifetime._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lifetime._closing  # type: ignore[attr-defined]
    assert closing.is_alive()
    with pytest.raises(ProductError) as rejected:
        bridge.create_runtime_subtitle_workspace({})
    assert rejected.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    release.set()
    operation.join(5)
    closing.join(5)
    assert not operation.is_alive() and not closing.is_alive()
    assert completed[0]["status"] == "SUBTITLE_READY"
    assert completed[0]["transcript_text_exposed"] is False
    with pytest.raises(ProductError) as after_close:
        bridge.create_runtime_subtitle_workspace({})
    assert after_close.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert launch._product_store is None

def test_cut_stage_holds_launch_lifetime_and_old_bridge_cannot_reexecute(
    tmp_path: Path,
) -> None:
    path, raw = config_document(tmp_path)
    source = Path(raw["paths"]["analysis_source_path"])

    class SourceDialogBackend(DialogBackend):
        def choose_open_media(self):
            return str(source)

    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(SourceDialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
    )

    class IngestStub:
        def ingest_local_media(self, source_path):
            return IngestedMediaIdentity(
                "ASSET-00000000000000000000000000",
                "sha256:" + "a" * 64,
                source_path,
            )

    entered, release = Event(), Event()

    class BlockingCutPort:
        calls = 0

        def generate_cut_candidates(self, *, source_path, transcript):
            self.calls += 1
            assert source_path == source
            entered.set()
            assert release.wait(5)
            return CutCandidateManifest(
                transcript.source_asset_id,
                "sha256:" + "a" * 64,
                48_000,
                2_000_000,
                "sha256:" + "c" * 64,
                transcript.to_dict()["manifest_sha256"],
                (
                    CutCandidate(
                        "cut-000001",
                        CutCandidateKind.SILENCE,
                        1_000_000,
                        1_500_000,
                        90,
                        ("SILENCE",),
                    ),
                ),
                (),
            )

    runtime = launch.pre_edit_runtime
    runtime.media.ingest_port = IngestStub()
    cut_port = BlockingCutPort()
    runtime.cut_candidate_port = cut_port
    bridge = launch.bridge
    assert bridge.choose_and_ingest_media({})["status"] == "INGESTED"
    runtime.binding.bind_transcript(
        TranscriptManifest(
            "ASSET-00000000000000000000000000",
            "ja",
            "faster-whisper",
            "local-cached-model",
            (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
        )
    )
    completed: list[dict[str, object]] = []
    operation = Thread(
        target=lambda: completed.append(bridge.generate_runtime_cut_candidates({}))
    )
    operation.start()
    assert entered.wait(5)
    lifetime = launch._local_operation_lifetime
    assert lifetime is not None
    closing = Thread(target=launch.close)
    closing.start()
    deadline = monotonic() + 5
    while not lifetime._closing and monotonic() < deadline:  # type: ignore[attr-defined]
        sleep(0.01)
    assert lifetime._closing  # type: ignore[attr-defined]
    assert closing.is_alive()
    with pytest.raises(ProductError) as rejected:
        bridge.generate_runtime_cut_candidates({})
    assert rejected.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert cut_port.calls == 1
    release.set()
    operation.join(5)
    closing.join(5)
    assert not operation.is_alive() and not closing.is_alive()
    assert completed[0]["status"] == "CUT_CANDIDATES_READY"
    assert completed[0]["candidate_details_exposed"] is False
    with pytest.raises(ProductError) as after_close:
        bridge.generate_runtime_cut_candidates({})
    assert after_close.value.code == "ERR_TASK036_RUNTIME_LEASE_REQUIRED"
    assert cut_port.calls == 1
    assert launch._product_store is None


def test_trusted_export_dispatcher_uses_only_exact_promoted_workflow_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, raw = config_document(tmp_path)
    config = Task036LaunchConfiguration.load(path)
    source = Path(raw["paths"]["analysis_source_path"])
    ProductProjectManifestStore.save(
        config.project_root,
        ProductProjectManifest.create(
            project_id=config.project_id,
            project_revision=1,
            product_version="0.22.0",
            timebase=ProjectTimebase(
                config.timeline_rate.numerator,
                config.timeline_rate.denominator,
            ),
            child_bindings=(),
            created_at="2026-08-25T00:00:00.000Z",
            updated_at="2026-08-25T00:00:00.000Z",
        ),
    )

    class SourceDialogBackend(DialogBackend):
        def choose_open_media(self):
            return str(source)

    launch = build_trusted_launch(
        config,
        native_dialog=Task036NativeDialogService(SourceDialogBackend()),
        asr_provider=AsrProvider(),
        resolve_adapter=ResolveAdapter(),
        final_review_export_preparation_provider=lambda _receipt: None,
    )
    bridge = launch.bridge
    promoted = None
    try:
        class IngestStub:
            def ingest_local_media(self, source_path):
                return IngestedMediaIdentity(
                    "ASSET-00000000000000000000000000",
                    "sha256:" + "a" * 64,
                    source_path,
                )

        class CutPort:
            def generate_cut_candidates(self, *, source_path, transcript):
                assert source_path == source
                return CutCandidateManifest(
                    transcript.source_asset_id,
                    "sha256:" + "a" * 64,
                    48_000,
                    2_000_000,
                    "sha256:" + "c" * 64,
                    transcript.to_dict()["manifest_sha256"],
                    (
                        CutCandidate(
                            "cut-000001",
                            CutCandidateKind.SILENCE,
                            1_000_000,
                            1_500_000,
                            90,
                            ("SILENCE",),
                        ),
                    ),
                    (),
                )

        runtime = launch.pre_edit_runtime
        runtime.media.ingest_port = IngestStub()
        runtime.cut_candidate_port = CutPort()
        assert bridge.choose_and_ingest_media({})["status"] == "INGESTED"
        runtime.binding.bind_transcript(
            TranscriptManifest(
                "ASSET-00000000000000000000000000",
                "ja",
                "faster-whisper",
                "local-cached-model",
                (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
            )
        )
        assert bridge.generate_runtime_cut_candidates({})["status"] == "CUT_CANDIDATES_READY"
        promoted = bridge._workflow_runtime
        assert promoted is runtime.promoted_workflow_runtime
        assert promoted is not None
        with bridge._nle_operation():
            controller = bridge._ensure_nle_controller()
        assert controller is not None
        dispatcher = controller.export_dispatcher
        assert dispatcher is not None

        observed = []

        def dispatch_export(self, job, preparation, destination):
            assert self is promoted
            observed.append((job, preparation, destination))
            return "DISPATCHED"

        monkeypatch.setattr(type(promoted), "dispatch_export", dispatch_export)
        job, preparation = object(), object()
        destination = config.native_render_evidence_root / "exports" / "job" / "render-output"
        with bridge._nle_operation():
            assert dispatcher(job, preparation, destination) == "DISPATCHED"
        assert observed == [(job, preparation, destination)]

        bridge._workflow_runtime = None
        with bridge._nle_operation(), pytest.raises(ProductError) as missing:
            dispatcher(job, preparation, destination)
        assert missing.value.code == "ERR_TASK036_WORKFLOW_RUNTIME_IDENTITY"
        assert observed == [(job, preparation, destination)]

        class ForeignRuntime:
            application = object()

            def dispatch_export(self, *_args):
                raise AssertionError("identity mismatch must reject before external dispatch")

        bridge._workflow_runtime = ForeignRuntime()
        with bridge._nle_operation(), pytest.raises(ProductError) as mismatched:
            dispatcher(job, preparation, destination)
        assert mismatched.value.code == "ERR_TASK036_WORKFLOW_RUNTIME_IDENTITY"
        assert observed == [(job, preparation, destination)]
    finally:
        if promoted is not None:
            bridge._workflow_runtime = promoted
        launch.close()
