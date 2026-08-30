from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

import ai_video_production.montage_learning_installation as installation
from ai_video_production.montage_learning_installer_cli import main as installer_main
from ai_video_production.montage_learning_installation import (
    BRIDGE_RELATIVE_PATH,
    INSTALLER_READBACK_FILENAME,
    MontageLearningInstallationError,
    discover_installed_bridge,
    provision_and_write_installer_readback,
    provision_installed_bridge,
    write_installer_readback,
)


MANIFEST_SHA = "sha256:" + "a" * 64


def test_installer_cli_provision_readback_is_one_bounded_operation(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()

    assert installer_main(
        [
            "provision-readback",
            "--install-root",
            str(install_root),
            "--installer-manifest-sha256",
            MANIFEST_SHA,
        ]
    ) == 0
    first = discover_installed_bridge(install_root)
    target = first.layout.migration / INSTALLER_READBACK_FILENAME
    assert json.loads(target.read_text(encoding="utf-8")) == first.public_receipt()

    assert installer_main(
        [
            "provision-readback",
            "--install-root",
            str(install_root),
            "--installer-manifest-sha256",
            "sha256:" + "b" * 64,
        ]
    ) == 0
    second = discover_installed_bridge(install_root)
    assert second.descriptor.descriptor_sha256 != first.descriptor.descriptor_sha256
    assert json.loads(target.read_text(encoding="utf-8")) == second.public_receipt()


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
    from ai_video_production.task036_packaged_entry import packaged_main

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
    from ai_video_production.task036_packaged_entry import packaged_main

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
    descriptor = first.layout.root / "bridge-instance.json"
    original_descriptor = descriptor.read_bytes()
    real_replace = installation.os.replace

    def fail_replace(source: object, destination: object) -> None:
        if Path(destination) == target:
            raise OSError("injected replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(installation.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
            now="2026-08-30T01:00:00Z",
    )
    assert target.read_bytes() == original
    assert descriptor.read_bytes() == original_descriptor
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
    second, updated_target = provision_and_write_installer_readback(
        install_root,
        installer_manifest_sha256="sha256:" + "b" * 64,
        now="2026-08-30T01:00:00Z",
    )

    assert updated_target == target
    assert json.loads(target.read_text(encoding="utf-8")) == second.public_receipt()
    assert target.stat(follow_symlinks=False).st_nlink == 1
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_installer_readback_rejects_upper_ancestor_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    real_identity = installation._safe_directory_identity
    drift = False

    def identity(path: Path) -> tuple[int, int, str]:
        result = real_identity(path)
        if drift and path == tmp_path.parent:
            return result[0], result[1] + 1, result[2]
        return result

    def inject(phase: str, path: Path) -> None:
        nonlocal drift
        if phase == "after_temp_fsync":
            drift = True

    monkeypatch.setattr(installation, "_safe_directory_identity", identity)
    with pytest.raises(MontageLearningInstallationError, match="ancestor identity"):
        write_installer_readback(discovery, failure_injector=inject)
    assert not target.exists()


def test_installer_readback_rejects_forged_predecessor_descriptor(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = write_installer_readback(discovery)
    descriptor = discovery.layout.root / "bridge-instance.json"
    original_descriptor = descriptor.read_bytes()
    forged = json.loads(target.read_text(encoding="utf-8"))
    forged["descriptor_sha256"] = "sha256:" + "c" * 64
    target.write_text(json.dumps(forged), encoding="utf-8")
    original = target.read_bytes()

    with pytest.raises(MontageLearningInstallationError, match="transition mismatch"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
        )
    assert target.read_bytes() == original
    assert descriptor.read_bytes() == original_descriptor


def test_installer_readback_rejects_update_without_predecessor_receipt(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    descriptor = discovery.layout.root / "bridge-instance.json"
    original = descriptor.read_bytes()

    with pytest.raises(MontageLearningInstallationError):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
        )
    assert descriptor.read_bytes() == original


def test_installer_readback_new_target_unlink_failure_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    discovery = provision_installed_bridge(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
    )
    target = discovery.layout.migration / INSTALLER_READBACK_FILENAME
    real_unlink = Path.unlink
    injected = False

    def fail_once(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal injected
        if path.suffix == ".tmp" and not injected:
            injected = True
            raise OSError("injected temporary unlink failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_once)
    with pytest.raises(MontageLearningInstallationError, match="cleanup failed"):
        write_installer_readback(discovery)
    assert not target.exists()
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_unified_update_rolls_back_descriptor_and_receipt_on_readback_failure(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()
    first, target = provision_and_write_installer_readback(
        install_root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-30T00:00:00Z",
    )
    descriptor_path = first.layout.root / "bridge-instance.json"
    original_descriptor = descriptor_path.read_bytes()
    original_receipt = target.read_bytes()

    def corrupt(phase: str, path: Path) -> None:
        if phase == "before_readback":
            path.write_bytes(b"corrupt\n")

    with pytest.raises(MontageLearningInstallationError):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256="sha256:" + "b" * 64,
            now="2026-08-30T01:00:00Z",
            failure_injector=corrupt,
        )
    assert descriptor_path.read_bytes() == original_descriptor
    assert target.read_bytes() == original_receipt
    assert discover_installed_bridge(install_root) == first


def test_unified_fresh_failure_removes_unpublished_descriptor_and_receipt(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "installed"
    install_root.mkdir()

    def fail(phase: str, path: Path) -> None:
        if phase == "after_temp_fsync":
            raise OSError("injected publication failure")

    with pytest.raises(OSError, match="injected publication failure"):
        provision_and_write_installer_readback(
            install_root,
            installer_manifest_sha256=MANIFEST_SHA,
            failure_injector=fail,
        )
    layout = installation.BridgeLayout.production(install_root)
    assert not (layout.root / "bridge-instance.json").exists()
    assert not (layout.migration / INSTALLER_READBACK_FILENAME).exists()


def test_active_source_has_no_programdata_bridge_literal() -> None:
    root = Path(__file__).resolve().parents[1]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src" / "ai_video_production").glob(
            "montage_learning*.py"
        )
    )
    assert r"C:\ProgramData\BAI Video Production\montage-learning-bridge" not in combined
