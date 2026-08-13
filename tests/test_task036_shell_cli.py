from __future__ import annotations

from ai_video_production import task036_shell_cli


def test_cli_routes_explicit_launch_config_to_trusted_shell(monkeypatch):
    calls = []
    monkeypatch.setattr(task036_shell_cli, "run_trusted_native_shell", lambda path: calls.append(("trusted", path)))
    monkeypatch.setattr(task036_shell_cli, "run_native_layout_spike", lambda: calls.append(("spike", None)))
    assert task036_shell_cli.main(["--launch-config", "C:/private/task036-launch.json"]) == 0
    assert calls == [("trusted", "C:/private/task036-launch.json")]


def test_cli_uses_environment_config_and_keeps_spike_as_explicit_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(task036_shell_cli, "run_trusted_native_shell", lambda path: calls.append(("trusted", path)))
    monkeypatch.setattr(task036_shell_cli, "run_native_layout_spike", lambda: calls.append(("spike", None)))
    monkeypatch.setenv("BAI_TASK036_LAUNCH_CONFIG", "C:/private/env-launch.json")
    assert task036_shell_cli.main([]) == 0
    assert calls == [("trusted", "C:/private/env-launch.json")]

    calls.clear()
    monkeypatch.delenv("BAI_TASK036_LAUNCH_CONFIG")
    assert task036_shell_cli.main(["--layout-spike"]) == 0
    assert calls == [("spike", None)]
