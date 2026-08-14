from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
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
from ai_video_production.generation_safety_application import Task013GenerationSafetyApplication
from ai_video_production.continuity_application import Task039ContinuityApplication


class DialogBackend:
    def choose_open_media(self):
        return None

    def choose_project_folder(self):
        return None

    def choose_handoff_folder(self):
        return None


class AsrProvider:
    config = type("Config", (), {"allow_model_download": False})()

    def transcribe(self, request):
        raise AssertionError("provider must not execute during launch")


class ResolveAdapter:
    def applied_hash(self, timeline_name):
        raise AssertionError("Resolve must not be inspected during launch")

    def assemble(self, plan, bindings):
        raise AssertionError("Resolve must not mutate during launch")


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
    assert isinstance(launch.bridge.production_control, Task037ProductionControlApplication)
    assert launch.bridge.production_control.project_root == config.project_root
    assert launch.bridge.production_control.project_id == config.project_id
    assert isinstance(launch.bridge.audit_application, Task038AuditApplication)
    assert launch.bridge.audit_application.project_root == config.project_root
    assert launch.bridge.audit_application.project_id == config.project_id
    assert isinstance(launch.bridge.planning_application, Task027PlanningApplication)
    assert launch.bridge.planning_application.project_root == config.project_root
    assert launch.bridge.planning_application.project_id == config.project_id
    assert launch.bridge.planning_application.production_control is launch.bridge.production_control
    assert isinstance(launch.bridge.generation_safety_application, Task013GenerationSafetyApplication)
    assert launch.bridge.generation_safety_application.project_root == config.project_root
    assert launch.bridge.generation_safety_application.project_id == config.project_id
    assert launch.bridge.generation_safety_application.planning_application is launch.bridge.planning_application
    assert launch.bridge.generation_safety_application.audit_application is launch.bridge.audit_application
    assert isinstance(launch.bridge.continuity_application, Task039ContinuityApplication)
    assert launch.bridge.continuity_application.project_root == config.project_root
    assert launch.bridge.continuity_application.project_id == config.project_id
    assert launch.bridge.continuity_application.production_control is launch.bridge.production_control
    continuity = launch.bridge.continuity_snapshot({})
    assert continuity["available"] is True
    assert continuity["provider_execution_started"] is False
    assert continuity["resolve_mutation_started"] is False
    production = launch.bridge.production_snapshot({})
    assert production["available"] is True
    assert production["project_id"] == config.project_id
    assert production["provider_execution_started"] is False
    assert production["resolve_mutation_started"] is False


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
