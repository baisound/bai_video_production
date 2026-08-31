from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production import task036_packaged_entry
from ai_video_production.task036_packaged_entry import packaged_main


class ReadyProbe:
    def require_ready(self):
        return object()


class FailingProbe:
    def require_ready(self):
        raise ProductError(
            "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED",
            "Microsoft Edge WebView2 Runtime is required.",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            retryable=True,
            details={"recovery_action": "Install WebView2 and retry.", "download_url": "https://example.test/"},
        )


class AvailableLease:
    def __enter__(self):
        return self

    def __exit__(self, *_unused):
        return None


class AvailableGuard:
    def acquire(self):
        return AvailableLease()


class BusyGuard:
    def acquire(self):
        raise ProductError(
            "ERR_TASK036_ALREADY_RUNNING",
            "BAI Video Productionは既に起動しています。既存のウィンドウを確認してください。",
            ProductErrorCategory.STATE,
        )


def test_packaged_entry_preflights_then_starts_shell():
    calls = []
    result = packaged_main(
        ["--layout-spike"],
        probe=ReadyProbe(),
        instance_guard=AvailableGuard(),
        presenter=lambda *_args: calls.append("error"),
        app_main=lambda args: calls.append(args) or 0,
    )
    assert result == 0
    assert calls == [["--layout-spike"]]


def test_packaged_entry_default_success_calls_shell_once_without_dialog(monkeypatch):
    calls = []
    shown = []
    monkeypatch.setattr(
        task036_packaged_entry,
        "shell_run",
        lambda argv: calls.append(argv),
    )

    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=AvailableGuard(),
        presenter=lambda title, body: shown.append((title, body)),
    )

    assert result == 0
    assert calls == [[]]
    assert shown == []


def test_packaged_entry_presents_actionable_error_without_console():
    shown = []
    result = packaged_main([], probe=FailingProbe(), instance_guard=AvailableGuard(), presenter=lambda title, body: shown.append((title, body)))
    assert result == 2
    assert len(shown) == 1
    assert shown[0][0] == "BAI Video Productionを起動できません"
    assert "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED" in shown[0][1]
    assert "WebView2 Runtimeをインストールまたは修復" in shown[0][1]
    assert "Install WebView2 and retry." not in shown[0][1]
    assert "https://example.test/" not in shown[0][1]


def test_packaged_entry_rejects_a_second_product_instance():
    shown = []
    calls = []
    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=BusyGuard(),
        presenter=lambda title, body: shown.append((title, body)),
        app_main=lambda args: calls.append(args) or 0,
    )
    assert result == 2
    assert calls == []
    assert len(shown) == 1
    assert "ERR_TASK036_ALREADY_RUNNING" in shown[0][1]


class TrackingLease:
    def __init__(self) -> None:
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_unused):
        self.closed = True


class TrackingGuard:
    def __init__(self) -> None:
        self.lease = TrackingLease()

    def acquire(self):
        return self.lease


def test_packaged_entry_releases_the_instance_guard_when_shell_fails():
    guard = TrackingGuard()
    shown = []
    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda title, body: shown.append((title, body)),
        app_main=lambda _args: (_ for _ in ()).throw(RuntimeError("fixture failure")),
    )
    assert result == 2
    assert guard.lease.closed is True
    assert len(shown) == 1
    assert "ERR_TASK036_PACKAGED_STARTUP" in shown[0][1]
    assert "fixture failure" not in shown[0][1]


def test_packaged_entry_default_route_surfaces_typed_shell_failure_without_stdout(
    monkeypatch,
    capsys,
):
    guard = TrackingGuard()
    shown = []

    def fail(_argv):
        raise ProductError(
            "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
            "secret=C:/private/user/project.json",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"recovery_action": "delete private data"},
        )

    monkeypatch.setattr(task036_packaged_entry, "shell_run", fail)
    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda title, body: shown.append((title, body)),
    )

    assert result == 2
    assert guard.lease.closed is True
    assert capsys.readouterr().out == ""
    assert len(shown) == 1
    assert "ERR_TASK036_FIRST_RUN_CONFIG_INVALID" in shown[0][1]
    assert "secret=" not in shown[0][1]
    assert "C:/private" not in shown[0][1]
    assert "delete private data" not in shown[0][1]


def test_packaged_entry_nonzero_result_never_exits_silently():
    guard = TrackingGuard()
    shown = []

    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda title, body: shown.append((title, body)),
        app_main=lambda _argv: 2,
    )

    assert result == 2
    assert guard.lease.closed is True
    assert len(shown) == 1
    assert "ERR_TASK036_PACKAGED_APP_NONZERO" in shown[0][1]
    assert "次の操作" in shown[0][1]


def test_packaged_entry_value_error_is_public_safe_and_releases_lease():
    guard = TrackingGuard()
    shown = []

    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda title, body: shown.append((title, body)),
        app_main=lambda _argv: (_ for _ in ()).throw(
            ValueError("C:/private/path must not be displayed")
        ),
    )

    assert result == 2
    assert guard.lease.closed is True
    assert len(shown) == 1
    assert "ERR_TASK036_SHELL_CLI" in shown[0][1]
    assert "C:/private" not in shown[0][1]


def test_packaged_entry_presenter_failure_does_not_retain_lease_or_hang():
    guard = TrackingGuard()

    result = packaged_main(
        [],
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda *_args: (_ for _ in ()).throw(RuntimeError("fixture")),
        app_main=lambda _argv: 2,
    )

    assert result == 2
    assert guard.lease.closed is True


@pytest.mark.parametrize("argv", [["--unknown-option"], ["--launch-config"]])
def test_packaged_entry_malformed_arguments_show_one_dialog_without_console(
    argv,
    capsys,
):
    guard = TrackingGuard()
    shown = []

    result = packaged_main(
        argv,
        probe=ReadyProbe(),
        instance_guard=guard,
        presenter=lambda title, body: shown.append((title, body)),
    )

    captured = capsys.readouterr()
    assert result == 2
    assert guard.lease.closed is True
    assert len(shown) == 1
    assert "ERR_TASK036_SHELL_CLI" in shown[0][1]
    assert captured.out == ""
    assert captured.err == ""
