from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

import ai_video_production.montage_learning_installation as installation
from ai_video_production.montage_learning_installation import (
    BRIDGE_RELATIVE_PATH,
    INSTALLER_READBACK_FILENAME,
    MontageLearningInstallationError,
    discover_installed_bridge,
    provision_installed_bridge,
    write_installer_readback,
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


def test_discover_command_writes_only_the_fixed_installer_readback(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )

    result = packaged_main(
        [
            "--bvp-installer-bridge",
            "discover",
            "--install-root",
            str(install_root),
        ]
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    assert result == 0
    assert json.loads(target.read_text(encoding="utf-8")) == discovery.public_receipt()
    assert target.read_bytes().endswith(b"\n")

    outside = tmp_path / "outside.json"
    rejected = packaged_main(
        [
            "--bvp-installer-bridge",
            "discover",
            "--install-root",
            str(install_root),
            "--receipt-output",
            str(outside),
        ]
    )
    assert rejected == 2
    assert not outside.exists()


def test_installer_readback_rejects_forged_layout_root(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    forged = replace(discovery, install_root=tmp_path / "other")

    with pytest.raises(MontageLearningInstallationError, match="layout mismatch"):
        write_installer_readback(forged)


@pytest.mark.parametrize("kind", ["directory", "symlink", "hardlink"])
def test_installer_readback_rejects_unsafe_existing_target(
    tmp_path: Path, kind: str
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    if kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        source = tmp_path / "symlink-source"
        source.write_text("not a receipt", encoding="utf-8")
        try:
            target.symlink_to(source)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
    else:
        source = tmp_path / "hardlink-source"
        source.write_text("not a receipt", encoding="utf-8")
        try:
            os.link(source, target)
        except OSError as exc:
            pytest.skip(f"hardlink creation unavailable: {exc}")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(discovery)


def test_installer_readback_rejects_ancestor_swap(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    migration = discovery.layout.migration
    outside = tmp_path / "outside"
    outside.mkdir()
    migration.rmdir()
    try:
        migration.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        migration.mkdir()
        pytest.skip(f"directory symlink creation unavailable: {exc}")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(discovery)
    assert not (outside / INSTALLER_READBACK_FILENAME).exists()


def test_installer_readback_replace_failure_preserves_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    target = write_installer_readback(first)
    original = target.read_bytes()
    second = provision_installed_bridge(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(installation.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        write_installer_readback(second)
    assert target.read_bytes() == original
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_rejects_unowned_existing_regular_file(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    original = b"not an installer receipt\n"
    target.write_bytes(original)

    with pytest.raises(MontageLearningInstallationError, match="JSON is invalid"):
        write_installer_readback(discovery)
    assert target.read_bytes() == original


def test_installer_readback_does_not_clobber_concurrent_new_target(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    concurrent = b"concurrent owner\n"

    def create_before_replace(phase: str, path: Path) -> None:
        if phase == "before_replace":
            path.write_bytes(concurrent)

    with pytest.raises(
        MontageLearningInstallationError,
        match="target identity changed",
    ):
        write_installer_readback(
            discovery,
            failure_injector=create_before_replace,
        )
    assert target.read_bytes() == concurrent
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_fails_on_post_write_readback_mismatch(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )

    def corrupt_before_readback(phase: str, path: Path) -> None:
        if phase == "before_readback":
            path.write_bytes(b"corrupt\n")

    with pytest.raises(MontageLearningInstallationError):
        write_installer_readback(
            discovery,
            failure_injector=corrupt_before_readback,
        )


def test_installer_readback_safe_update_is_exact_and_single_link(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    target = write_installer_readback(first)
    second = provision_installed_bridge(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )

    assert write_installer_readback(second) == target
    assert json.loads(target.read_text(encoding="utf-8")) == second.public_receipt()
    assert target.stat(follow_symlinks=False).st_nlink == 1
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_active_source_has_no_programdata_bridge_literal() -> None:
    root = Path(__file__).resolve().parents[1]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src" / "ai_video_production").glob(
            "montage_learning*.py"
        )
    )
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in combined
