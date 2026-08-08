from pathlib import Path

ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "tools" / "windows" / "run-resolve-capability-spike.ps1"


def test_windows_runner_is_read_only_and_writes_both_evidence_reports():
    text = RUNNER.read_text(encoding="utf-8")
    assert "--allow-mutation-probes" not in text
    assert "taskkill" not in text.lower()
    assert "resolve-capability-report.json" in text
    assert "resolve-ipc-probe-report.json" in text
    assert "--kind resolve" in text
    assert "--kind ipc" in text
    assert "WSL2-to-Windows reachability is NOT proven" in text


def test_windows_runner_can_import_project_from_checkout_without_auto_installing():
    text = RUNNER.read_text(encoding="utf-8")
    assert 'Join-Path $repoRoot "src"' in text
    assert "$env:PYTHONPATH" in text
    assert "pip install" in text  # guidance only in the preflight failure message
    assert "& $Python -m pip" not in text  # runner itself never installs packages
