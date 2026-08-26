from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
HELPER_FILENAME = "BAI Video Production Key Helper.exe"
IDENTITY_FILENAME = "_bvp_task059_packaged_helper_identity.py"
IDENTITY_ATTRIBUTE = "EXPECTED_PACKAGED_HELPER_SHA256"


def _verifier_module():
    path = ROOT / "tools" / "windows" / "verify-task059-packaged-helper.py"
    spec = importlib.util.spec_from_file_location("task059_build_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_task059_helper_is_internal_one_file_stdio_executable() -> None:
    entry = (
        ROOT / "packaging" / "task059_ppk_helper_windows_entry.py"
    ).read_text(encoding="utf-8")
    spec = (ROOT / "packaging" / "task059_ppk_helper.spec").read_text(
        encoding="utf-8"
    )
    assert (
        "from ai_video_production.owner_signing_key_ppk_helper import main"
        in entry
    )
    assert 'name="BAI Video Production Key Helper"' in spec
    assert "console=True" in spec
    assert "COLLECT(" not in spec
    assert "analysis.binaries" in spec
    assert "analysis.datas" in spec
    assert 'schema_directory.glob("*.json")' in spec


def test_main_spec_embeds_digest_and_collects_exact_adjacent_helper() -> None:
    spec = (ROOT / "packaging" / "task036_shell.spec").read_text(
        encoding="utf-8"
    )
    assert 'os.environ.get("BVP_TASK059_HELPER_EXE")' in spec
    assert "PACKAGED_HELPER_IDENTITY_MODULE" in spec
    assert "PACKAGED_HELPER_DIGEST_ATTRIBUTE" in spec
    assert "generated_module.write_text(" in spec
    assert "[PACKAGED_HELPER_IDENTITY_MODULE]" in spec
    assert '(PACKAGED_HELPER_FILENAME, str(helper_path), "EXECUTABLE")' in spec
    assert spec.count('name="BAI Video Production"') == 2
    assert "COLLECT(" in spec


def test_windows_batch_builds_verifies_and_smokes_internal_helper() -> None:
    batch = (ROOT / "build-windows-exe.bat").read_text(encoding="utf-8")
    assert "packaging\\task059_ppk_helper.spec" in batch
    assert 'set "BVP_TASK059_HELPER_EXE=%TASK059_HELPER_EXE%"' in batch
    assert 'set "BVP_TASK059_HELPER_EXE="' in batch
    assert "verify-task059-packaged-helper.py" in batch
    assert "BAI Video Production\\BAI Video Production Key Helper.exe" in batch
    assert "--protocol-version 1 <nul >nul 2>nul" in batch
    assert "--protocol-version 0 <nul >nul 2>nul" in batch
    assert '"64"' in batch
    assert "The helper is not a second user entrypoint." in batch


def test_packaged_helper_verifier_requires_three_exact_matching_identities(
    tmp_path,
) -> None:
    verifier = _verifier_module()
    staged = tmp_path / "staged" / HELPER_FILENAME
    bundled = tmp_path / "bundled" / HELPER_FILENAME
    identity = tmp_path / "work" / IDENTITY_FILENAME
    for path in (staged, bundled, identity):
        path.parent.mkdir()
    body = b"synthetic packaged helper"
    staged.write_bytes(body)
    bundled.write_bytes(body)
    digest = sha256_bytes(body)
    identity.write_text(
        f'{IDENTITY_ATTRIBUTE} = "{digest}"\n',
        encoding="ascii",
    )

    assert verifier.verify_packaged_helper(staged, bundled, identity) == digest

    bundled.write_bytes(b"tampered helper")
    with pytest.raises(ValueError):
        verifier.verify_packaged_helper(staged, bundled, identity)
    bundled.write_bytes(body)
    identity.write_text(
        f'{IDENTITY_ATTRIBUTE} = "sha256:{"0" * 64}"\n',
        encoding="ascii",
    )
    with pytest.raises(ValueError):
        verifier.verify_packaged_helper(staged, bundled, identity)


def test_packaged_helper_verifier_cli_is_body_free(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    verifier = _verifier_module()
    assert verifier.main([]) == 64
    assert verifier.main([str(tmp_path), str(tmp_path), str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert str(tmp_path) not in output
    assert output == "[ERROR] TASK-059 packaged helper verification failed.\n"

    def unexpected(*_args):
        raise RuntimeError("forbidden-path-or-body")

    monkeypatch.setattr(verifier, "verify_packaged_helper", unexpected)
    assert verifier.main(["one", "two", "three"]) == 2
    output = capsys.readouterr().out
    assert "forbidden" not in output
    assert output == "[ERROR] TASK-059 packaged helper verification failed.\n"
