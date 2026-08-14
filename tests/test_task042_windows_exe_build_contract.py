from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tomllib


ROOT = Path(__file__).parents[1]


def test_windows_build_contract_reuses_native_validated_task036_spec() -> None:
    batch = (ROOT / "build-windows-exe.bat").read_text(encoding="utf-8")
    assert "packaging\\task036_shell.spec" in batch
    assert "--distpath \"%CD%\\builds\"" in batch
    assert "--workpath \"%CD%\\builds\\work\"" in batch
    assert "builds\\BAI Video Production\\BAI Video Production.exe" in batch
    assert "BVP_BUILD_PYTHON" in batch
    assert "pip install -e" in batch
    assert "-m pip install" in batch
    assert "call pip" not in batch.lower()


def test_build_outputs_are_ignored_but_placeholder_is_kept() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/builds/*" in ignore
    assert "!/builds/.gitkeep" in ignore
    assert (ROOT / "builds" / ".gitkeep").is_file()


def test_windows_build_dependencies_and_user_docs_are_explicit() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = config["project"]["optional-dependencies"]["windows-build"]
    assert "pyinstaller==6.22.0" in dependencies
    assert "pywebview==6.2.1" in dependencies
    assert any(item.startswith("faster-whisper>=1.2.1") for item in dependencies)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "windows" / "BUILDING-WINDOWS-EXE.md").read_text(encoding="utf-8")
    assert readme.index("### Windows EXE build") > readme.index("## Installation")
    assert readme.index("### Windows EXE build") < readme.index("## Verification")
    assert "## AUTONOMYを使った開発" in readme
    assert readme.count("Codexへの依頼例") >= 3
    assert "Handoff → Current State → Authority → Current Task → Development Profile → 対象Source → 関連Test" in readme
    assert "TASK_BLOCKED != SYSTEM_BLOCKED" in readme
    assert "### 一番よく使う標準の開始指示" in readme
    assert "### 使用例10：夜間に安全な単位で長時間進める" in readme
    assert "Conversation-free Handoff" in readme
    assert "build-windows-exe.bat" in guide
    assert "Tag、GitHub Release、Deploy" in guide


def test_batch_help_is_side_effect_free_on_windows() -> None:
    if os.name != "nt":
        return
    before = sorted(path.relative_to(ROOT) for path in (ROOT / "builds").rglob("*"))
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(ROOT / "build-windows-exe.bat"), "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    after = sorted(path.relative_to(ROOT) for path in (ROOT / "builds").rglob("*"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Usage: build-windows-exe.bat" in result.stdout
    assert before == after
