from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def run(root: Path, command: list[str], *, env=None, timeout=None) -> None:
    print("[RUN]", " ".join(command), flush=True)
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}"
        )


def ensure_pyinstaller(root: Path) -> None:
    probe = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            "PyInstallerが現在のPython環境にありません。\n"
            "TASK-051では依存パッケージを自動インストールしません。\n"
            "先に次を実行してからR7を再実行してください:\n"
            "python -m pip install -e .[windows-build]"
        )
    print("[PASS] PyInstaller available:", probe.stdout.strip())


def package_acceptance(root: Path, launcher: Path, evidence: Path) -> Path:
    ensure_pyinstaller(root)
    package_root = evidence / "package"
    work = package_root / "work"
    dist = package_root / "dist"
    spec = package_root / "spec"
    for path in (work, dist, spec):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    name = "BAI-DbD-Training-Studio-R7"
    run(
        root,
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--name", name,
            "--collect-submodules", "ai_video_production",
            "--collect-data", "jsonschema_specifications",
            "--collect-data", "faster_whisper",
            "--distpath", str(dist),
            "--workpath", str(work),
            "--specpath", str(spec),
            str(launcher),
        ],
        timeout=1200,
    )

    exe = dist / name / f"{name}.exe"
    if not exe.is_file():
        raise RuntimeError(f"Packaged executable was not created: {exe}")
    print("[PASS] Windows packaged executable build:", exe)

    marker = exe.parent / "BAI_DIAGNOSTICS.ENABLE"
    marker.write_text("", encoding="utf-8")
    smoke_env = os.environ.copy()
    smoke_env["BAI_TRAINING_STUDIO_SMOKE_EXIT"] = "1"
    try:
        run(root, [str(exe)], env=smoke_env, timeout=120)
        latest = exe.parent / "diagnostics" / "latest.jsonl"
        if not latest.is_file():
            raise RuntimeError("packaged diagnostics log was not created")
        diagnostics_text = latest.read_text(encoding="utf-8")
        if "PACKAGED_TK_SMOKE_PASS" not in diagnostics_text:
            raise RuntimeError("packaged Tk render diagnostics evidence is missing")
    finally:
        marker.unlink(missing_ok=True)
    print("[PASS] packaged executable import/Tk/diagnostics smoke")
    return exe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--pack-root", required=True)
    args = parser.parse_args()

    root = Path(args.target_root).resolve()
    pack = Path(args.pack_root).resolve()
    launcher = pack / "tools" / "task051" / "task051_training_studio_launcher.py"
    evidence = root.parent / (
        f"{root.name}-task051-r7-evidence-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    evidence.mkdir(parents=True, exist_ok=True)

    focused = [
        "tests/test_task051_r6_unified_review_ui.py",
        "tests/test_task051_r6_review_model.py",
        "tests/test_task051_r5_trivia_revision_management.py",
        "tests/test_task051_r5_trivia_operational.py",
        "tests/test_task051_r5_trivia_ui.py",
        "tests/test_task051_r4_workspace_editing.py",
        "tests/test_task051_r4_semantics.py",
        "tests/test_task051_r4_ui.py",
        "tests/test_task051_r3_hud_profile_binding.py",
        "tests/test_task051_r3_training_studio_multi_slot.py",
        "tests/test_task051_r2_video_transport.py",
        "tests/test_task051_r2_training_studio_transport_integration.py",
        "tests/test_task051_r1_training_presentation.py",
        "tests/test_task050_training_studio_ux_followup.py",
    ]
    run(root, [sys.executable, "-m", "pytest", "-q", *focused], timeout=900)
    print("[PASS] focused lineage regression")

    run(root, [sys.executable, "-m", "pytest", "-q"], timeout=1800)
    print("[PASS] full pytest")

    run(
        root,
        [sys.executable, "-m", "compileall", "-q", "src/ai_video_production"],
        timeout=300,
    )
    print("[PASS] compileall")

    run(root, ["git", "diff", "--check"], timeout=120)
    print("[PASS] git diff --check")

    run(
        root,
        [
            sys.executable,
            "-c",
            (
                "import ai_video_production.dbd_training_studio;"
                "import ai_video_production.dbd_training_review_ui_v2;"
                "import ai_video_production.dbd_trivia_operational;"
                "import ai_video_production.dbd_notification_semantics;"
                "print('TASK051_IMPORT_SMOKE_PASS')"
            ),
        ],
        timeout=120,
    )
    print("[PASS] source import smoke")

    exe = package_acceptance(root, launcher, evidence)

    status = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    (evidence / "git-status.txt").write_text(status.stdout, encoding="utf-8")

    diffstat = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    (evidence / "git-diff-stat.txt").write_text(diffstat.stdout, encoding="utf-8")

    report = {
        "task": "TASK-051",
        "unit": "R7",
        "focused_regression": "PASS",
        "full_pytest": "PASS",
        "compileall": "PASS",
        "git_diff_check": "PASS",
        "source_import_smoke": "PASS",
        "windows_packaged_executable": str(exe),
        "packaged_import_tk_diagnostics_smoke": "PASS",
        "closure_ready_automated": True,
        "human_acceptance_still_required": True,
    }
    (evidence / "TASK051-R7-ACCEPTANCE.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("[PASS] TASK-051 R7 focused lineage regression")
    print("[PASS] TASK-051 R7 full pytest")
    print("[PASS] compileall")
    print("[PASS] git diff --check")
    print("[PASS] source import smoke")
    print("[PASS] Windows packaged executable build")
    print("[PASS] packaged executable import/Tk/diagnostics smoke")
    print("[EVIDENCE]", evidence)
    print(
        "[HUMAN] 実DBD動画を使ったGUI目視・OCR・FasterWhisper・HUD Crop確認は"
        "Human Acceptanceとして別途実施してください。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
