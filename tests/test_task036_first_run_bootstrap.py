from __future__ import annotations

import json

import pytest

from ai_video_production import task036_first_run_bootstrap
from ai_video_production.errors import ProductError
from ai_video_production.local_ollama_planning import LocalOllamaTransport
from ai_video_production.task036_ollama_runtime import OllamaRuntimeLifecycle
from ai_video_production.task036_first_run_bootstrap import (
    ensure_first_run_launch_configuration,
)
from ai_video_production.task036_trusted_launcher import (
    Task036LaunchConfiguration,
    build_trusted_launch,
)


def test_first_run_bootstrap_creates_one_valid_private_configuration(tmp_path) -> None:
    application_root = tmp_path / "local-app-data" / "BAISOUND" / "BAI Video Production"

    path = ensure_first_run_launch_configuration(application_root=application_root)
    first_bytes = path.read_bytes()
    configuration = Task036LaunchConfiguration.load(path)

    assert path == application_root / "control" / "task036-first-run-launch.json"
    assert configuration.project_id == "bvp-first-run-project"
    assert configuration.display_name == "新しいBAI Video Production Project"
    assert configuration.project_root == application_root / "projects" / "bvp-first-run-project"
    assert configuration.asr_config.allow_model_download is False
    assert configuration.analysis_source_path.is_file()
    assert configuration.analysis_audio_path.is_file()
    assert ensure_first_run_launch_configuration(application_root=application_root) == path
    assert path.read_bytes() == first_bytes
    assert "新しいBAI Video Production Project".encode("utf-8") in first_bytes


def test_first_run_bootstrap_rejects_malformed_existing_configuration(tmp_path) -> None:
    application_root = tmp_path / "local-app-data"
    config = application_root / "control" / "task036-first-run-launch.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"unexpected": True}), encoding="utf-8")

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_CONFIG_INVALID"


def test_first_run_bootstrap_rejects_oversized_existing_configuration_without_rewrite(
    tmp_path,
) -> None:
    application_root = tmp_path / "local-app-data"
    config = application_root / "control" / "task036-first-run-launch.json"
    config.parent.mkdir(parents=True)
    config.write_bytes(b"{" + b" " * (256 * 1024) + b"}")
    before = config.read_bytes()

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_CONFIG_INVALID"
    assert config.read_bytes() == before


def test_first_run_bootstrap_requires_an_absolute_application_root(tmp_path) -> None:
    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root="relative-root")

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_PATH_UNSAFE"


def test_first_run_bootstrap_repairs_only_the_known_legacy_display_name(tmp_path) -> None:
    application_root = tmp_path / "local-app-data"
    path = ensure_first_run_launch_configuration(application_root=application_root)
    document = json.loads(path.read_text(encoding="utf-8"))
    legacy = json.loads(json.dumps(document))
    legacy["project"]["display_name"] = "�V����BAI Video Production Project"
    path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

    assert ensure_first_run_launch_configuration(application_root=application_root) == path

    repaired = json.loads(path.read_text(encoding="utf-8"))
    expected = json.loads(json.dumps(legacy))
    expected["project"]["display_name"] = "新しいBAI Video Production Project"
    assert repaired == expected
    assert Task036LaunchConfiguration.load(path).display_name == "新しいBAI Video Production Project"


def test_first_run_bootstrap_preserves_unknown_existing_display_name(tmp_path) -> None:
    application_root = tmp_path / "local-app-data"
    path = ensure_first_run_launch_configuration(application_root=application_root)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["project"]["display_name"] = "利用者が設定したプロジェクト名"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_DISPLAY_NAME_UNKNOWN"
    assert path.read_bytes() == before


def test_first_run_legacy_repair_rejects_path_swap_and_preserves_foreign_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    application_root = tmp_path / "local-app-data"
    path = ensure_first_run_launch_configuration(application_root=application_root)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["project"]["display_name"] = "�V����BAI Video Production Project"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    original_write = task036_first_run_bootstrap.AtomicJsonWriter.write
    foreign_bytes = b'{"foreign":true}\n'

    def swap_then_write(target, value, *, validator=None, failure_injector=None):
        candidate = type(path)(target)
        candidate.unlink()
        candidate.write_bytes(foreign_bytes)
        return original_write(
            candidate,
            value,
            validator=validator,
            failure_injector=failure_injector,
        )

    monkeypatch.setattr(
        task036_first_run_bootstrap.AtomicJsonWriter,
        "write",
        staticmethod(swap_then_write),
    )

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE"
    assert path.read_bytes() == foreign_bytes


def test_first_run_legacy_repair_rejects_symlink_swap_without_touching_target(
    tmp_path,
    monkeypatch,
) -> None:
    application_root = tmp_path / "local-app-data"
    path = ensure_first_run_launch_configuration(application_root=application_root)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["project"]["display_name"] = "�V����BAI Video Production Project"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    original_write = task036_first_run_bootstrap.AtomicJsonWriter.write
    foreign = tmp_path / "foreign.json"
    foreign_bytes = b'{"foreign":true}\n'
    foreign.write_bytes(foreign_bytes)

    def swap_then_write(target, value, *, validator=None, failure_injector=None):
        candidate = type(path)(target)
        candidate.unlink()
        candidate.symlink_to(foreign)
        return original_write(
            candidate,
            value,
            validator=validator,
            failure_injector=failure_injector,
        )

    monkeypatch.setattr(
        task036_first_run_bootstrap.AtomicJsonWriter,
        "write",
        staticmethod(swap_then_write),
    )

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE"
    assert path.is_symlink()
    assert foreign.read_bytes() == foreign_bytes


class _UnreachableOllamaTransport(LocalOllamaTransport):
    def request(self, method: str, url: str, payload: bytes | None, timeout_seconds: float) -> bytes:
        raise ProductError("ERR_LOCAL_OLLAMA_UNREACHABLE", "fixture only")


def test_first_run_bootstrap_binds_settings_when_ollama_is_not_installed(tmp_path) -> None:
    path = ensure_first_run_launch_configuration(application_root=tmp_path / "local-app-data")
    runtime = OllamaRuntimeLifecycle(
        transport=_UnreachableOllamaTransport(),
        executable_resolver=lambda: None,
    )

    launch = build_trusted_launch(Task036LaunchConfiguration.load(path), ollama_runtime=runtime)
    try:
        settings = launch.bridge.connection_settings_snapshot({})
        model_selection = launch.bridge.model_selection_snapshot({})
        ollama = launch.bridge.ollama_runtime_snapshot({})
    finally:
        launch.close()

    assert settings["available"] is True
    assert model_selection["available"] is True
    assert ollama["state"] == "NOT_INSTALLED"
    assert ollama["reason_code"] == "OLLAMA_EXECUTABLE_NOT_FOUND"
    assert ollama["model_ids"] == []
