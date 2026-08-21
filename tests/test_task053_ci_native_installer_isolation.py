from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
NATIVE_INSTALLER_TEST = "tests/test_task047_obs_installer_contract.py"


def test_windows_native_installer_is_serial_without_reducing_full_coverage() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "Run bounded parallel test suite on Linux" in text
    assert "if: runner.os == 'Linux'" in text
    assert "Run bounded parallel non-installer suite on Windows" in text
    assert "Run native installer contract serially on Windows" in text
    assert text.count("if: runner.os == 'Windows'") == 3  # FFmpeg + parallel + serial.

    parallel = text.split("Run bounded parallel non-installer suite on Windows", 1)[1].split(
        "Run native installer contract serially on Windows", 1,
    )[0]
    assert "python -m pytest -q -n 2 --dist loadfile" in parallel
    assert "--timeout=120 --max-worker-restart=0 --durations=20" in parallel
    assert f"--ignore={NATIVE_INSTALLER_TEST}" in parallel

    serial = text.split("Run native installer contract serially on Windows", 1)[1].split(
        "python -m compileall", 1,
    )[0]
    assert f"python -m pytest -q {NATIVE_INSTALLER_TEST}" in serial
    assert "--timeout=300 --durations=20" in serial
    assert "-n " not in serial
    assert "--dist" not in serial
    assert "--ignore" not in serial

    # The file is excluded exactly once from the Windows parallel invocation
    # and selected exactly once by the serial invocation in the same matrix job.
    assert text.count(NATIVE_INSTALLER_TEST) == 2
    assert "--deselect" not in text


def test_linux_keeps_the_unfiltered_bounded_parallel_suite() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    linux = text.split("Run bounded parallel test suite on Linux", 1)[1].split(
        "Run bounded parallel non-installer suite on Windows", 1,
    )[0]
    assert "python -m pytest -q -n 2 --dist loadfile" in linux
    assert "--timeout=120 --max-worker-restart=0 --durations=20" in linux
    assert NATIVE_INSTALLER_TEST not in linux
    assert "--ignore" not in linux
