from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "packaging" / "release-assets" / "task047"
INSTALLER = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.8-installer.4-windows-x64-setup.exe"
RUNTIME = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.8-windows-x64.zip"
SOURCE = ASSET_ROOT / "bai-voice-capture-0.1.0-dev.8-source.zip"
SUMS = ASSET_ROOT / "SHA256SUMS"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


EXPECTED = {
    INSTALLER.name: "7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6",
    RUNTIME.name: "4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f",
    SOURCE.name: "4dcd50f3aadaf95798a4d82ad511a66b14ad5a1e81a131a3bd65c0c5f933b0a4",
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
    assert "dist/task047-obs" in text
    assert "gh release create" in text


def test_readmes_document_complete_plugin_and_installer_build() -> None:
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for token in (
            "bai-voice-capture-0.1.0-dev.8-installer.4-windows-x64-setup.exe",
            "bai-voice-capture-0.1.0-dev.8-windows-x64.zip",
            "bai-voice-capture-0.1.0-dev.8-source.zip",
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
