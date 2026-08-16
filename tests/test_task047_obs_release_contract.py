from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "packaging" / "release-assets" / "task047"
INSTALLER = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe"
RUNTIME = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.10-windows-x64.zip"
SOURCE = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.10-source.zip"
SUMS = ASSET_ROOT / "SHA256SUMS"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


EXPECTED = {
    INSTALLER.name: "5eb7b00aa3830f880c724538023c6f7b0b52a032e2c1ed880d497cdd8cce1908",
    RUNTIME.name: "03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558",
    SOURCE.name: "0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_release_assets_are_exact_and_manifested() -> None:
    sums = SUMS.read_text(encoding="utf-8").splitlines()
    assert len(sums) == 3
    for name, expected in EXPECTED.items():
        artifact = ASSET_ROOT / name
        assert artifact.is_file()
        assert _sha256(artifact) == expected
        assert f"{expected}  {name}" in sums


def test_release_workflow_verifies_and_uploads_obs_assets() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    assert "Verify TASK-047 OBS release assets" in text
    assert "sha256sum --check SHA256SUMS" in text
    assert "packaging/release-assets/task047/*" in text
    assert "cp packaging/release-assets/task047/* dist/" in text
    assert "gh release create" in text


def test_readmes_document_complete_plugin_and_installer_build() -> None:
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for token in (
            "bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe",
            "bai-voice-capture-0.1.0-dev.10-windows-x64.zip",
            "bai-voice-capture-0.1.0-dev.10-source.zip",
            "CMake\\3.30.5\\bin\\cmake.exe",
            "build-task047-obs-installer.ps1",
            "SHA256SUMS",
        ):
            assert token in text
        assert "docs/user/OBS-VOICE-CAPTURE-PLUGIN.md" in text


def test_release_asset_paths_do_not_expose_private_roots() -> None:
    public = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "README.en.md", "packaging/release-assets/task047/SHA256SUMS")
    )
    assert "BAI_WORKSPACES" not in public
    assert "BAI_AI" not in public
    assert "E:\\" not in public
