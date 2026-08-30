from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import ai_video_production.desktop_install_layout as install_layout
from ai_video_production.atomic import AtomicJsonWriter
from ai_video_production.desktop_install_layout import (
    AclAceSnapshot,
    DesktopInstallLayoutError,
    SIDECAR_FILENAME,
    WRITABLE_LEAVES,
    build_install_layout_document,
    derive_binary_root,
    expected_data_root,
    read_task063_descriptor_identity,
    resolve_desktop_install_layout,
)
from ai_video_production.montage_learning_installation import provision_installed_bridge


MANIFEST_SHA = "sha256:" + "a" * 64
USER_SID = "S-1-5-21-1000"
SYSTEM_USER_SID = "S-1-5-21-2000"


@pytest.fixture(autouse=True)
def _synthetic_acl_readback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        install_layout,
        "_verify_protected_data_root_acl",
        lambda path, scope, principals: None,
    )


def _provision_task063(root: Path):
    root.mkdir(parents=True)
    discovery = provision_installed_bridge(
        root,
        installer_manifest_sha256=MANIFEST_SHA,
        now="2026-08-31T00:00:00Z",
    )
    for relative in WRITABLE_LEAVES.values():
        (root / "data" / relative).mkdir(parents=True, exist_ok=True)
    return discovery


def _write_layout(root: Path) -> dict[str, object]:
    identity = read_task063_descriptor_identity(root)
    document = build_install_layout_document(
        binary_root=root,
        data_root=root / "data",
        install_scope="PER_USER",
        acl_principal_sids=(USER_SID,),
        descriptor=identity,
    )
    AtomicJsonWriter.write(root / SIDECAR_FILENAME, document)
    return document


def test_per_user_layout_consumes_exact_task063_identity_and_ignores_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "BAI 動画"
    discovery = _provision_task063(root)
    document = _write_layout(root)
    unrelated = tmp_path / "cwd"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    layout = resolve_desktop_install_layout(root)

    assert layout.install_instance_id == discovery.descriptor.install_instance_id
    assert layout.task063_descriptor_sha256 == discovery.descriptor.descriptor_sha256
    assert layout.binary_root == root.resolve()
    assert layout.data_root == (root / "data").resolve()
    assert layout.layout_sha256 == document["layout_sha256"]
    assert layout.profile_path == root / "data" / "settings" / "desktop-compute-profile.json"
    assert layout.installer_receipt_path.parts[-3:] == (
        "settings",
        "installation",
        "task066-installer-readback.json",
    )


def test_system_wide_layout_uses_programdata_instance_coordinate(tmp_path: Path) -> None:
    root = tmp_path / "Program Files" / "BAI"
    discovery = _provision_task063(root)
    program_data = tmp_path / "ProgramData"
    program_data.mkdir()
    expected = expected_data_root(
        root,
        "SYSTEM_WIDE",
        discovery.descriptor.install_instance_id,
        program_data_root=program_data,
    )
    for relative in WRITABLE_LEAVES.values():
        (expected / relative).mkdir(parents=True, exist_ok=True)
    document = build_install_layout_document(
        binary_root=root,
        data_root=expected,
        install_scope="SYSTEM_WIDE",
        acl_principal_sids=(SYSTEM_USER_SID,),
        descriptor=discovery.descriptor,
        program_data_root=program_data,
    )
    AtomicJsonWriter.write(root / SIDECAR_FILENAME, document)

    layout = resolve_desktop_install_layout(root, program_data_root=program_data)

    assert layout.install_scope == "SYSTEM_WIDE"
    assert layout.data_root == expected.resolve()


def test_resolver_verifies_data_root_and_each_owned_leaf_acl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "app"
    _provision_task063(root)
    _write_layout(root)
    observed: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        install_layout,
        "_verify_protected_data_root_acl",
        lambda path, scope, principals: observed.append((path.resolve(), scope, principals)),
    )
    layout = resolve_desktop_install_layout(root)
    assert observed == [
        (layout.data_root, "PER_USER", (USER_SID,)),
        (layout.settings_root, "PER_USER", (USER_SID,)),
        (layout.logs_root, "PER_USER", (USER_SID,)),
        (layout.runtime_cache_root, "PER_USER", (USER_SID,)),
    ]


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("install_instance_id", "bvp-install-" + "f" * 32, "digest"),
        ("binary_root", "C:/substituted", "digest"),
        ("data_root", "C:/substituted", "digest"),
        ("task063_descriptor_sha256", "sha256:" + "f" * 64, "digest"),
    ],
)
def test_substitution_or_tamper_fails_closed(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    root = tmp_path / "app"
    _provision_task063(root)
    document = _write_layout(root)
    document[field] = replacement
    (root / SIDECAR_FILENAME).write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DesktopInstallLayoutError, match=message):
        resolve_desktop_install_layout(root)


def test_missing_leaf_and_sidecar_symlink_are_not_guessed(tmp_path: Path) -> None:
    root = tmp_path / "app"
    _provision_task063(root)
    _write_layout(root)
    (root / "data" / "logs").rmdir()
    with pytest.raises(DesktopInstallLayoutError, match="logs"):
        resolve_desktop_install_layout(root)

    (root / "data" / "logs").mkdir()
    target = root / SIDECAR_FILENAME
    copy = root / "layout-copy.json"
    copy.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(copy)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(DesktopInstallLayoutError, match="single-link|symlink|reparse"):
        resolve_desktop_install_layout(root)


def test_executable_root_requires_absolute_safe_regular_file(tmp_path: Path) -> None:
    executable = tmp_path / "BAI Video Production.exe"
    executable.write_bytes(b"synthetic")
    assert derive_binary_root(executable.resolve()) == tmp_path.resolve()
    with pytest.raises(DesktopInstallLayoutError, match="absolute"):
        derive_binary_root(Path("relative.exe"))


def test_schema_mirror_is_byte_exact() -> None:
    root = Path(__file__).parents[1]
    assert (root / "schemas" / "desktop-install-layout.schema.json").read_bytes() == (
        root
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / "desktop-install-layout.schema.json"
    ).read_bytes()


def test_per_user_acl_requires_protection_owner_and_no_broad_write() -> None:
    owner = "S-1-5-21-1000"
    admitted = (
        AclAceSnapshot(owner, 0x40000000, False, True),
        AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
        AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
    )
    install_layout._validate_acl_snapshot(
        owner_sid=owner,
        dacl_protected=True,
        aces=admitted,
        install_scope="PER_USER",
        admitted_principal_sids=(owner,),
    )
    with pytest.raises(DesktopInstallLayoutError, match="inheritance"):
        install_layout._validate_acl_snapshot(
            owner_sid=owner,
            dacl_protected=False,
            aces=admitted,
            install_scope="PER_USER",
            admitted_principal_sids=(owner,),
        )
    with pytest.raises(DesktopInstallLayoutError, match="broad"):
        install_layout._validate_acl_snapshot(
            owner_sid=owner,
            dacl_protected=True,
            aces=admitted
            + (AclAceSnapshot("S-1-1-0", 0x40000000, False, True),),
            install_scope="PER_USER",
            admitted_principal_sids=(owner,),
        )


@pytest.mark.parametrize("denied_sid", [USER_SID, "S-1-1-0", "S-1-5-11"])
def test_acl_rejects_admitted_or_broad_write_deny_ace(denied_sid: str) -> None:
    admitted = (
        AclAceSnapshot(USER_SID, 0x40000000, False, True),
        AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
        AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
    )
    with pytest.raises(DesktopInstallLayoutError, match="write deny"):
        install_layout._validate_acl_snapshot(
            owner_sid=USER_SID,
            dacl_protected=True,
            aces=admitted + (AclAceSnapshot(denied_sid, 0x40000000, False, False),),
            install_scope="PER_USER",
            admitted_principal_sids=(USER_SID,),
        )


def test_acl_does_not_misclassify_read_only_deny_as_write_deny() -> None:
    install_layout._validate_acl_snapshot(
        owner_sid=USER_SID,
        dacl_protected=True,
        aces=(
            AclAceSnapshot(USER_SID, 0x40000000, False, True),
            AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
            AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
            AclAceSnapshot("S-1-1-0", 0x00000001, False, False),
        ),
        install_scope="PER_USER",
        admitted_principal_sids=(USER_SID,),
    )


def test_system_wide_acl_requires_system_and_administrators_without_inherited_write() -> None:
    admitted = (
        AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
        AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
        AclAceSnapshot("S-1-5-21-2000", 0x40000000, False, True),
    )
    install_layout._validate_acl_snapshot(
        owner_sid="S-1-5-32-544",
        dacl_protected=True,
        aces=admitted,
        install_scope="SYSTEM_WIDE",
        admitted_principal_sids=(SYSTEM_USER_SID,),
    )
    with pytest.raises(DesktopInstallLayoutError, match="inherited"):
        install_layout._validate_acl_snapshot(
            owner_sid="S-1-5-32-544",
            dacl_protected=True,
            aces=admitted
            + (AclAceSnapshot("S-1-5-21-2001", 0x40000000, True, True),),
            install_scope="SYSTEM_WIDE",
            admitted_principal_sids=(SYSTEM_USER_SID,),
        )


def test_acl_rejects_owner_or_writer_outside_sidecar_principal_binding() -> None:
    per_user_aces = (
        AclAceSnapshot(USER_SID, 0x40000000, False, True),
        AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
        AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
    )
    with pytest.raises(DesktopInstallLayoutError, match="owner"):
        install_layout._validate_acl_snapshot(
            owner_sid="S-1-5-21-9999",
            dacl_protected=True,
            aces=per_user_aces,
            install_scope="PER_USER",
            admitted_principal_sids=(USER_SID,),
        )


def test_unknown_or_compound_acl_ace_type_fails_closed() -> None:
    with pytest.raises(DesktopInstallLayoutError, match="unsupported"):
        install_layout._ace_allow_classification(0x04)
    with pytest.raises(DesktopInstallLayoutError, match="unsupported"):
        install_layout._ace_allow_classification(0x7F)
    with pytest.raises(DesktopInstallLayoutError, match="explicitly admitted"):
        install_layout._validate_acl_snapshot(
            owner_sid="S-1-5-32-544",
            dacl_protected=True,
            aces=(
                AclAceSnapshot("S-1-5-18", 0x10000000, False, True),
                AclAceSnapshot("S-1-5-32-544", 0x10000000, False, True),
                AclAceSnapshot(SYSTEM_USER_SID, 0x40000000, False, True),
                AclAceSnapshot("S-1-5-21-666", 0x40000000, False, True),
            ),
            install_scope="SYSTEM_WIDE",
            admitted_principal_sids=(SYSTEM_USER_SID,),
        )
