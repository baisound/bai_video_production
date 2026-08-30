from __future__ import annotations

from ai_video_production.errors import ProductError, ProductErrorCategory
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


def test_packaged_entry_presents_actionable_error_without_console():
    shown = []
    result = packaged_main([], probe=FailingProbe(), instance_guard=AvailableGuard(), presenter=lambda title, body: shown.append((title, body)))
    assert result == 2
    assert len(shown) == 1
    assert "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED" in shown[0][1]
    assert "Install WebView2 and retry." in shown[0][1]
    assert "https://example.test/" in shown[0][1]


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
    assert "ERR_TASK036_PACKAGED_STARTUP" in shown[0][1]