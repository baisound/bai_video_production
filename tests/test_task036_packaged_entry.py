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


def test_packaged_entry_preflights_then_starts_shell():
    calls = []
    result = packaged_main(
        ["--layout-spike"],
        probe=ReadyProbe(),
        presenter=lambda *_args: calls.append("error"),
        app_main=lambda args: calls.append(args) or 0,
    )
    assert result == 0
    assert calls == [["--layout-spike"]]


def test_packaged_entry_presents_actionable_error_without_console():
    shown = []
    result = packaged_main([], probe=FailingProbe(), presenter=lambda title, body: shown.append((title, body)))
    assert result == 2
    assert len(shown) == 1
    assert "ERR_TASK036_WEBVIEW2_RUNTIME_REQUIRED" in shown[0][1]
    assert "Install WebView2 and retry." in shown[0][1]
    assert "https://example.test/" in shown[0][1]
