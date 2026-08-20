from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"tools"/"task051"/"run_task051_r7_acceptance.py"

def test_r7_acceptance_gate_contains_required_checks():
    text=RUNNER.read_text(encoding="utf-8")
    ast.parse(text)
    assert '"-m", "pytest", "-q"' in text
    assert '"compileall"' in text
    assert '"diff", "--check"' in text
    assert "PyInstaller" in text
    assert '"--collect-data", "jsonschema_specifications"' in text
    assert "BAI_TRAINING_STUDIO_SMOKE_EXIT" in text
    assert "BAI_DIAGNOSTICS.ENABLE" in text
    assert "PACKAGED_TK_SMOKE_PASS" in text
    launcher = (ROOT / "tools" / "task051" / "task051_training_studio_launcher.py").read_text(encoding="utf-8")
    assert "from jsonschema_specifications import REGISTRY" in launcher
    assert "len(REGISTRY)" in launcher
    assert "tk.PhotoImage" in launcher
    assert "PACKAGED_TK_SMOKE_PASS" in launcher
    assert "get_diagnostic_logger" in launcher
    assert "closure_ready_automated" in text

def test_r7_does_not_auto_install_dependencies():
    text=RUNNER.read_text(encoding="utf-8")
    assert "python -m pip install -e .[windows-build]" in text
    assert 'run(root, [sys.executable, "-m", "pip"' not in text


def test_r7_packaged_smoke_requires_pyav_runtime():
    launcher = Path("tools/task051/task051_training_studio_launcher.py").read_text(encoding="utf-8")
    assert "import av" in launcher
    assert "PyAV runtime is unavailable" in launcher
