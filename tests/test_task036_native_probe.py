from __future__ import annotations

from pathlib import Path

from ai_video_production.task036_native_probe import Task036NativeProbe


def test_non_windows_probe_never_claims_native_ready():
    report = Task036NativeProbe(platform_name="Linux", module_finder=lambda _name: object()).run()
    assert report.pywebview_available is True
    assert report.webview2_runtime_candidates == ()
    assert report.ready_to_launch_layout_spike is False
    assert report.to_dict()["renderer_native_validated"] is False


def test_windows_probe_requires_both_pywebview_and_webview2_candidate(tmp_path: Path):
    program_files = tmp_path / "Program Files (x86)"
    version = program_files / "Microsoft" / "EdgeWebView" / "Application" / "140.0.1"
    version.mkdir(parents=True)
    report = Task036NativeProbe(
        platform_name="Windows",
        environ={"PROGRAMFILES(X86)": str(program_files)},
        module_finder=lambda name: object() if name == "webview" else None,
    ).run()
    assert report.ready_to_launch_layout_spike is True
    assert report.webview2_runtime_candidates == (str(version),)
    body = report.to_dict()
    assert body["dependency_install_performed"] is False
    assert body["renderer_native_validated"] is False


def test_windows_probe_does_not_treat_webview2_runtime_as_pywebview(tmp_path: Path):
    root = tmp_path / "pf" / "Microsoft" / "EdgeWebView" / "Application" / "1"
    root.mkdir(parents=True)
    report = Task036NativeProbe(
        platform_name="Windows",
        environ={"PROGRAMFILES": str(tmp_path / "pf")},
        module_finder=lambda _name: None,
    ).run()
    assert report.webview2_runtime_candidates
    assert report.pywebview_available is False
    assert report.ready_to_launch_layout_spike is False

def test_windows_probe_ignores_non_version_directories_and_sorts_versions_numerically(tmp_path: Path):
    application = tmp_path / "pf" / "Microsoft" / "EdgeWebView" / "Application"
    older = application / "9.0.0.0"
    newest = application / "10.0.0.0"
    older.mkdir(parents=True)
    newest.mkdir()
    (application / "SetupMetrics").mkdir()

    report = Task036NativeProbe(
        platform_name="Windows",
        environ={"PROGRAMFILES": str(tmp_path / "pf")},
        module_finder=lambda name: object() if name == "webview" else None,
    ).run()

    assert report.webview2_runtime_candidates == (str(newest),)
    assert report.ready_to_launch_layout_spike is True
