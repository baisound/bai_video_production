from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task036_shell_ui import Task036ShellBridge
from test_task098_faster_whisper_model_settings import Backend, make_config, make_model, service


def test_symbolic_model_snapshot_is_read_only_and_does_not_claim_cache_hit(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    backend = Backend(None)
    manager = service(config, backend)
    before = config.read_bytes()
    snapshot = manager.snapshot(expected_launch_config_sha256=sha256_bytes(before))
    assert snapshot["status"] == "LOCAL_MODEL_NOT_CONFIGURED"
    assert snapshot["reason_codes"] == ["LOCAL_MODEL_NOT_CONFIGURED"]
    assert snapshot["cache_reuse_available"] is True
    assert snapshot["cache_hit_observed"] is False
    assert snapshot["model_manifest_continuity_confirmed"] is False
    assert snapshot["runtime_compatibility_confirmed"] is False
    assert snapshot["settings_updated"] is False
    assert backend.model_calls == 0
    assert config.read_bytes() == before
    assert not config.with_name(f".{config.name}.lock").exists()


def test_new_service_reads_back_r2_model_and_existing_cache_without_paths(tmp_path: Path) -> None:
    config, raw = make_config(tmp_path)
    model = make_model(tmp_path / "private-model")
    first = service(config, Backend(str(model)), token="first-confirmation")
    prepared = first.prepare(expected_launch_config_sha256=sha256_bytes(config.read_bytes()))
    applied = first.apply(confirmation_id=prepared["confirmation_id"])

    restarted = service(config, Backend(None), token="restart-token")
    snapshot = restarted.snapshot(
        expected_launch_config_sha256=applied["launch_config_sha256"]
    )
    body = json.dumps(snapshot, ensure_ascii=False)
    assert snapshot["status"] == "READY"
    assert snapshot["model_id"] == applied["model_id"]
    assert snapshot["launch_config_sha256"] == sha256_bytes(config.read_bytes())
    assert snapshot["cache_reuse_available"] is True
    assert snapshot["cache_hit_observed"] is False
    assert snapshot["restart_readback"] is True
    assert snapshot["model_manifest_continuity_confirmed"] is False
    assert snapshot["runtime_compatibility_confirmed"] is False
    assert str(model) not in body
    assert raw["paths"]["asr_cache_directory"] not in body
    assert all(snapshot[field] is False for field in (
        "model_download_authorized", "model_load_started", "inference_started",
        "network_used", "provider_execution_started", "settings_updated",
    ))


def test_pending_confirmation_does_not_survive_service_reconstruction(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    first = service(config, Backend(str(model)), token="process-local-token")
    prepared = first.prepare(expected_launch_config_sha256=sha256_bytes(config.read_bytes()))
    restarted = service(config, Backend(None), token="new-token")
    before = config.read_bytes()
    with pytest.raises(ProductError) as rejected:
        restarted.apply(confirmation_id=prepared["confirmation_id"])
    assert rejected.value.code == "ERR_TASK098_MODEL_SETTINGS_CONFIRMATION_INVALID"
    assert config.read_bytes() == before


def test_snapshot_stale_model_missing_and_invalid_model_fail_closed(tmp_path: Path) -> None:
    config, _raw = make_config(tmp_path)
    model = make_model(tmp_path / "model")
    first = service(config, Backend(str(model)))
    prepared = first.prepare(expected_launch_config_sha256=sha256_bytes(config.read_bytes()))
    applied = first.apply(confirmation_id=prepared["confirmation_id"])
    restarted = service(config, Backend(None))

    with pytest.raises(ProductError) as stale:
        restarted.snapshot(expected_launch_config_sha256="sha256:" + "0" * 64)
    assert stale.value.code == "ERR_TASK098_MODEL_SETTINGS_STALE"

    (model / "tokenizer.json").unlink()
    before = config.read_bytes()
    missing = restarted.snapshot(expected_launch_config_sha256=applied["launch_config_sha256"])
    assert missing["status"] == "BLOCKED"
    assert missing["reason_codes"] == ["REQUIRED_FILE_MISSING"]
    assert missing["cache_hit_observed"] is False
    assert config.read_bytes() == before


def test_cache_alias_ancestry_is_blocked_without_path_disclosure(tmp_path: Path) -> None:
    config, raw = make_config(tmp_path)
    project = Path(raw["project"]["project_root"])
    real_cache = project / "real-cache"
    child = real_cache / "child"
    child.mkdir(parents=True)
    alias = project / "cache-alias"
    try:
        alias.symlink_to(real_cache, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    raw["paths"]["asr_cache_directory"] = str(alias / "child")
    config.write_text(json.dumps(raw), encoding="utf-8")
    manager = service(config, Backend(None))
    snapshot = manager.snapshot(
        expected_launch_config_sha256=sha256_bytes(config.read_bytes())
    )
    body = json.dumps(snapshot)
    assert snapshot["status"] == "BLOCKED"
    assert snapshot["reason_codes"] == ["CACHE_DIRECTORY_UNSAFE"]
    assert snapshot["cache_reuse_available"] is False
    assert str(alias) not in body


def test_shell_snapshot_request_is_exact_read_only_and_path_free(tmp_path: Path) -> None:
    config, raw = make_config(tmp_path)
    manager = service(config, Backend(None))
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.24.3"),
        faster_whisper_model_settings=manager,
    )
    before = config.read_bytes()
    snapshot = bridge.faster_whisper_model_settings_snapshot(
        {"expected_launch_config_sha256": sha256_bytes(before)}
    )
    assert snapshot["status"] == "LOCAL_MODEL_NOT_CONFIGURED"
    assert raw["paths"]["asr_cache_directory"] not in json.dumps(snapshot)
    assert config.read_bytes() == before
    for request in (None, {}, {"expected_launch_config_sha256": "x", "path": "private"}):
        with pytest.raises(ProductError):
            bridge.faster_whisper_model_settings_snapshot(request)
