from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.montage_learning_installation import (
    BRIDGE_RELATIVE_PATH,
    MontageLearningInstallationError,
    discover_installed_bridge,
    provision_installed_bridge,
)
from ai_video_production.task036_packaged_entry import packaged_main


MANIFEST_SHA = "sha256:" + "a" * 64


def test_custom_unicode_install_root_provisions_exact_relative_tree(tmp_path: Path) -> None:
    install_root = tmp_path / "BAI 動画 Production"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )

    assert discovery.layout.root == install_root / "data" / "montage-learning-bridge"
    assert discovery.descriptor.bridge_relative_path == BRIDGE_RELATIVE_PATH
    assert discovery.descriptor.install_instance_id.startswith("bvp-install-")
    for relative in (
        "learning-inbox",
        "learning-processing",
        "learning-quarantine",
        "learning-receipts",
        "preference",
        "preference/profiles",
        "state",
        "migration",
    ):
        assert (discovery.layout.root / relative).is_dir()
    assert not discovery.layout.current_profile.exists()
    assert discovery.public_receipt()["connector_enabled"] is False


def test_repair_preserves_instance_and_readback_detects_descriptor_tamper(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "app"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    repaired = provision_installed_bridge(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )
    assert repaired.descriptor.install_instance_id == first.descriptor.install_instance_id
    assert repaired.descriptor.created_at == first.descriptor.created_at
    assert repaired.descriptor.updated_at == "2026-08-30T01:00:00Z"

    descriptor_path = repaired.layout.root / "bridge-instance.json"
    value = json.loads(descriptor_path.read_text(encoding="utf-8"))
    value["bridge_relative_path"] = "elsewhere"
    descriptor_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(MontageLearningInstallationError):
        discover_installed_bridge(install_root)


def test_packaged_private_installer_command_bypasses_desktop_probe(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()

    class ProbeMustNotRun:
        def require_ready(self):
            raise AssertionError("desktop probe must not run for installer operation")

    result = packaged_main(
        [
            "--bvp-installer-bridge",
            "provision",
            "--install-root",
            str(install_root),
            "--installer-manifest-sha256",
            MANIFEST_SHA,
        ],
        probe=ProbeMustNotRun(),
    )
    assert result == 0
    assert discover_installed_bridge(install_root).layout.root.is_dir()


def test_active_source_has_no_programdata_bridge_literal() -> None:
    root = Path(__file__).resolve().parents[1]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src" / "ai_video_production").glob(
            "montage_learning*.py"
        )
    )
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in combined
