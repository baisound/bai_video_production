from __future__ import annotations

import json

import pytest

from ai_video_production import task036_shell_cli
from ai_video_production.errors import ProductError, ProductErrorCategory


def test_cli_routes_explicit_launch_config_to_trusted_shell(monkeypatch):
    calls = []
    monkeypatch.setattr(task036_shell_cli, "run_trusted_native_shell", lambda path: calls.append(("trusted", path)))
    monkeypatch.setattr(task036_shell_cli, "run_native_layout_spike", lambda: calls.append(("spike", None)))
    assert task036_shell_cli.main(["--launch-config", "C:/private/task036-launch.json"]) == 0
    assert calls == [("trusted", "C:/private/task036-launch.json")]


def test_cli_bootstraps_ordinary_start_and_keeps_spike_explicit(monkeypatch):
    calls = []
    monkeypatch.setattr(task036_shell_cli, "run_trusted_native_shell", lambda path: calls.append(("trusted", path)))
    monkeypatch.setattr(task036_shell_cli, "run_native_layout_spike", lambda: calls.append(("spike", None)))
    monkeypatch.setattr(
        task036_shell_cli,
        "ensure_first_run_launch_configuration",
        lambda: "C:/private/first-run-launch.json",
    )
    monkeypatch.delenv("BAI_TASK036_LAUNCH_CONFIG", raising=False)

    assert task036_shell_cli.main([]) == 0
    assert calls == [("trusted", "C:/private/first-run-launch.json")]

    calls.clear()
    assert task036_shell_cli.main(["--layout-spike"]) == 0
    assert calls == [("spike", None)]


def test_cli_uses_environment_config_without_bootstrapping(monkeypatch):
    calls = []
    monkeypatch.setattr(task036_shell_cli, "run_trusted_native_shell", lambda path: calls.append(("trusted", path)))
    monkeypatch.setattr(task036_shell_cli, "run_native_layout_spike", lambda: calls.append(("spike", None)))
    monkeypatch.setattr(task036_shell_cli, "ensure_first_run_launch_configuration", lambda: (_ for _ in ()).throw(AssertionError("must not bootstrap")))
    monkeypatch.setenv("BAI_TASK036_LAUNCH_CONFIG", "C:/private/env-launch.json")

    assert task036_shell_cli.main([]) == 0
    assert calls == [("trusted", "C:/private/env-launch.json")]


def test_product_host_run_preserves_typed_failure_without_console(monkeypatch, capsys):
    failure = ProductError(
        "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
        "typed fixture",
        ProductErrorCategory.DATA_INTEGRITY,
    )
    monkeypatch.setattr(
        task036_shell_cli,
        "ensure_first_run_launch_configuration",
        lambda: (_ for _ in ()).throw(failure),
    )
    monkeypatch.delenv("BAI_TASK036_LAUNCH_CONFIG", raising=False)

    with pytest.raises(ProductError) as raised:
        task036_shell_cli.run([])

    assert raised.value is failure
    assert capsys.readouterr().out == ""


def test_direct_cli_keeps_json_error_envelope(monkeypatch, capsys):
    monkeypatch.setattr(
        task036_shell_cli,
        "ensure_first_run_launch_configuration",
        lambda: (_ for _ in ()).throw(
            ProductError(
                "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
                "direct CLI fixture",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        ),
    )
    monkeypatch.delenv("BAI_TASK036_LAUNCH_CONFIG", raising=False)

    assert task036_shell_cli.main([]) == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["status"] == "ERROR"
    assert envelope["code"] == "ERR_TASK036_FIRST_RUN_CONFIG_INVALID"
    assert envelope["message"] == "direct CLI fixture"


def test_product_host_rejects_conflicting_routes_without_printing(monkeypatch, capsys):
    monkeypatch.setenv("BAI_TASK036_LAUNCH_CONFIG", "C:/private/env-launch.json")

    with pytest.raises(ValueError):
        task036_shell_cli.run(["--layout-spike"])

    assert capsys.readouterr().out == ""
    assert task036_shell_cli.main(["--layout-spike"]) == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["code"] == "ERR_TASK036_SHELL_CLI"
