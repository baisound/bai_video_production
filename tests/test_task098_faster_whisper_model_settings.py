from __future__ import annotations

import base64
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.native_file_dialog import WindowsNativeFileDialog
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task036_native_dialog import Task036NativeDialogService
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task098_faster_whisper_model_settings import (
    Task098FasterWhisperModelSettingsService,
)


def make_model(root: Path) -> Path:
    root.mkdir()
    (root / "config.json").write_text('{"model_type":"whisper"}', encoding="utf-8")
    (root / "model.bin").write_bytes(b"model-body")
    (root / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    (root / "vocabulary.txt").write_text("token\n", encoding="utf-8")
    return root


def make_config(tmp_path: Path) -> tuple[Path, dict]:
    project = tmp_path / "private-project"
    incoming = tmp_path / "incoming"
    project.mkdir(parents=True)
    incoming.mkdir()
    source = incoming / "source.mp4"
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
            "source_roots": [str(incoming)],
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


class Backend:
    def __init__(self, model: str | None) -> None:
        self.model = model
        self.model_calls = 0

    def choose_open_media(self):
        return None

    def choose_project_folder(self):
        return None

    def choose_handoff_folder(self):
        return None

    def choose_faster_whisper_model_folder(self):
        self.model_calls += 1
        return self.model


def service(
    config: Path,
    backend: Backend,
    *,
    token: str = "confirm-model-1",
    clock=lambda: 0.0,
    ttl: float = 300.0,
    failure_injector=None,
) -> Task098FasterWhisperModelSettingsService:
    return Task098FasterWhisperModelSettingsService(
        launch_config_path=config,
        native_dialog=Task036NativeDialogService(backend),
        token_factory=lambda: token,
        monotonic_clock=clock,
        pending_ttl_seconds=ttl,
        failure_injector=failure_injector,
    )


def test_stale_digest_fails_before_picker_or_write(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    backend = Backend(str(model))
    before = config.read_bytes()
    with pytest.raises(ProductError) as rejected:
        service(config, backend).prepare(expected_launch_config_sha256="sha256:" + "0" * 64)
    assert rejected.value.code == "ERR_TASK098_MODEL_SETTINGS_STALE"
    assert backend.model_calls == 0
    assert config.read_bytes() == before


def test_config_must_be_inside_its_validated_project_before_picker(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    outside = tmp_path / "outside-launch.json"
    outside.write_bytes(config.read_bytes())
    backend = Backend(str(make_model(tmp_path / "model")))
    with pytest.raises(ProductError) as rejected:
        service(outside, backend).prepare(
            expected_launch_config_sha256=sha256_bytes(outside.read_bytes())
        )
    assert rejected.value.code == "ERR_TASK098_MODEL_SETTINGS_CONFIG_INVALID"
    assert backend.model_calls == 0
    assert not outside.with_name(f".{outside.name}.lock").exists()


def test_cancel_and_blocked_selection_are_path_free_and_non_pending(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    expected = sha256_bytes(config.read_bytes())
    cancelled_service = service(config, Backend(None), token="cancel-token")
    cancelled = cancelled_service.prepare(expected_launch_config_sha256=expected)
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["confirmation_id"] is None
    with pytest.raises(ProductError):
        cancelled_service.apply(confirmation_id="cancel-token")

    invalid = tmp_path / "private-invalid-model"
    invalid.mkdir()
    blocked_service = service(config, Backend(str(invalid)), token="blocked-token")
    blocked = blocked_service.prepare(expected_launch_config_sha256=expected)
    body = json.dumps(blocked)
    assert blocked["status"] == "BLOCKED"
    assert blocked["confirmation_id"] is None
    assert "REQUIRED_FILE_MISSING" in blocked["reason_codes"]
    assert str(invalid) not in body
    with pytest.raises(ProductError):
        blocked_service.apply(confirmation_id="blocked-token")


def test_prepare_apply_updates_only_model_and_preserves_cache(tmp_path: Path) -> None:
    config, original = make_config(tmp_path)
    model = make_model(tmp_path / "private-model")
    manager = service(config, Backend(str(model)))
    expected = sha256_bytes(config.read_bytes())

    prepared = manager.prepare(expected_launch_config_sha256=expected)
    prepared_body = json.dumps(prepared, ensure_ascii=False)
    assert prepared["status"] == "READY_FOR_CONFIRMATION"
    assert prepared["settings_updated"] is False
    assert prepared["cache_directory_preserved"] is True
    assert str(model) not in prepared_body
    assert prepared["inspection"]["execution_authorized"] is False
    assert not config.with_name(f".{config.name}.lock").exists()

    result = manager.apply(confirmation_id=prepared["confirmation_id"])
    updated = json.loads(config.read_text(encoding="utf-8"))
    expected_document = json.loads(json.dumps(original))
    expected_document["asr"]["model"] = str(model.resolve(strict=True))
    assert updated == expected_document
    assert updated["paths"]["asr_cache_directory"] == original["paths"]["asr_cache_directory"]
    assert updated["asr"]["allow_model_download"] is False
    assert result["status"] == "UPDATED"
    assert result["settings_updated"] is True
    assert result["launch_config_sha256"] == sha256_bytes(config.read_bytes())
    assert str(model) not in json.dumps(result)
    assert all(result[field] is False for field in (
        "model_download_authorized", "model_load_started", "inference_started",
        "network_used", "provider_execution_started", "private_path_exposed",
    ))
    with pytest.raises(ProductError) as repeated:
        manager.apply(confirmation_id=prepared["confirmation_id"])
    assert repeated.value.code == "ERR_TASK098_MODEL_SETTINGS_CONFIRMATION_INVALID"


def test_wrong_expired_and_malformed_confirmation_fail_before_write(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    expected = sha256_bytes(config.read_bytes())
    now = [0.0]
    manager = service(config, Backend(str(model)), clock=lambda: now[0], ttl=5.0)
    prepared = manager.prepare(expected_launch_config_sha256=expected)
    before = config.read_bytes()
    with pytest.raises(ProductError):
        manager.apply(confirmation_id="wrong")
    assert config.read_bytes() == before
    now[0] = 6.0
    with pytest.raises(ProductError) as expired:
        manager.apply(confirmation_id=prepared["confirmation_id"])
    assert expired.value.code == "ERR_TASK098_MODEL_SETTINGS_CONFIRMATION_INVALID"
    with pytest.raises(ProductError):
        manager.apply(confirmation_id="")
    assert config.read_bytes() == before


def test_config_or_model_drift_fails_before_write(tmp_path: Path) -> None:
    config, raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    expected = sha256_bytes(config.read_bytes())
    config_manager = service(config, Backend(str(model)), token="config-drift")
    prepared = config_manager.prepare(expected_launch_config_sha256=expected)
    raw["asr"]["beam_size"] = 6
    config.write_text(json.dumps(raw), encoding="utf-8")
    drifted = config.read_bytes()
    with pytest.raises(ProductError) as stale:
        config_manager.apply(confirmation_id=prepared["confirmation_id"])
    assert stale.value.code == "ERR_TASK098_MODEL_SETTINGS_STALE"
    assert config.read_bytes() == drifted

    config.unlink()
    config, _raw = make_config(tmp_path / "second")
    model2 = make_model(tmp_path / "second-model")
    model_manager = service(config, Backend(str(model2)), token="model-drift")
    prepared = model_manager.prepare(
        expected_launch_config_sha256=sha256_bytes(config.read_bytes())
    )
    (model2 / "model.bin").write_bytes(b"changed-model")
    before = config.read_bytes()
    with pytest.raises(ProductError) as changed:
        model_manager.apply(confirmation_id=prepared["confirmation_id"])
    assert changed.value.code == "ERR_TASK098_MODEL_SETTINGS_MODEL_DRIFT"
    assert config.read_bytes() == before


def test_pre_replace_failure_preserves_config_and_cleans_temp(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")

    def fail(stage: str, _temporary: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("injected")

    manager = service(config, Backend(str(model)), failure_injector=fail)
    before = config.read_bytes()
    prepared = manager.prepare(expected_launch_config_sha256=sha256_bytes(before))
    with pytest.raises(RuntimeError, match="injected"):
        manager.apply(confirmation_id=prepared["confirmation_id"])
    assert config.read_bytes() == before
    assert list(config.parent.glob(f".{config.name}.*.tmp")) == []


class Meter:
    def __init__(self) -> None:
        self.events: list[str] = []

    @contextmanager
    def project_write(self):
        self.events.append("invalidate")
        try:
            yield
        finally:
            self.events.append("write-finished")


def test_shell_projection_is_closed_path_free_and_apply_is_write_guarded(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    manager = service(config, Backend(str(model)))
    meter = Meter()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.24.3"),
        faster_whisper_model_settings=manager,
        meter_controller_host=meter,
    )
    prepared = bridge.prepare_faster_whisper_model_folder_update(
        {"expected_launch_config_sha256": sha256_bytes(config.read_bytes())}
    )
    assert meter.events == []
    result = bridge.apply_faster_whisper_model_folder_update(
        {"confirmation_id": prepared["confirmation_id"]}
    )
    assert result["status"] == "UPDATED"
    assert meter.events == ["invalidate", "write-finished"]
    assert str(model) not in json.dumps(result)
    for request in (None, {}, {"expected_launch_config_sha256": "x", "path": "private"}):
        with pytest.raises(ProductError):
            bridge.prepare_faster_whisper_model_folder_update(request)
    with pytest.raises(ProductError):
        bridge.apply_faster_whisper_model_folder_update({"confirmation_id": "x", "path": "private"})
    unbound = Task036ShellBridge(ShellApplicationService(product_version="0.24.3"))
    with pytest.raises(ProductError) as rejected:
        unbound.prepare_faster_whisper_model_folder_update(
            {"expected_launch_config_sha256": "sha256:" + "1" * 64}
        )
    assert rejected.value.code == "ERR_TASK098_MODEL_SETTINGS_NOT_BOUND"


def test_fixed_windows_model_folder_script_uses_existing_folder_only() -> None:
    captured = {}
    selected = r"C:\private\faster-whisper-model"
    encoded = base64.b64encode(selected.encode("utf-8")).decode("ascii")

    def runner(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=f"BAI_DIALOG_OK:{encoded}".encode("ascii"),
            stderr=b"",
        )

    result = WindowsNativeFileDialog(
        runner=runner,
        platform_name="nt",
    ).choose_faster_whisper_model_folder()
    assert result == selected
    script = base64.b64decode(captured["args"][7]).decode("utf-16le")
    assert "FolderBrowserDialog" in script
    assert "FasterWhisper" in script
    assert "ShowNewFolderButton = $false" in script
    assert selected not in script
