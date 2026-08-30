from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.montage_learning_bridge_migration import (
    MontageLearningBridgeMigrationError,
    execute_legacy_bridge_migration,
    plan_legacy_bridge_migration,
    read_legacy_bridge_migration,
)
from ai_video_production.montage_learning_bridge_security import (
    BridgeAce,
    BridgeSecurityDescriptor,
    BridgeSecurityState,
    attest_bridge_security,
)
from ai_video_production.montage_learning_installation import provision_installed_bridge
from ai_video_production.serialization import sha256_json


SHA = "sha256:" + "a" * 64


class SecureBackend:
    def inspect(self, _path: Path) -> BridgeSecurityDescriptor:
        return BridgeSecurityDescriptor(
            owner_sid="S-1-5-21-1",
            current_user_sid="S-1-5-21-1",
            dacl_present=True,
            aces=(BridgeAce(0, 0, 0x1F01FF, "S-1-5-21-1"),),
        )


class SharedWriterBackend:
    def inspect(self, _path: Path) -> BridgeSecurityDescriptor:
        return BridgeSecurityDescriptor(
            owner_sid="S-1-5-21-1",
            current_user_sid="S-1-5-21-1",
            dacl_present=True,
            aces=(BridgeAce(0, 0, 0x00000002, "S-1-1-0"),),
        )


def _fixture(tmp_path: Path):
    source = tmp_path / "legacy-explicit"
    source.mkdir()
    (source / "learning-inbox").mkdir()
    (source / "learning-inbox" / "unknown.json").write_bytes(b'{"legacy":true}\n')
    (source / "preference").mkdir()
    (source / "preference" / "current-profile.json").write_bytes(b'{"unbound":true}\n')
    (source / "empty-unknown").mkdir()
    install = tmp_path / "custom-install"
    install.mkdir()
    target = provision_installed_bridge(install, installer_manifest_sha256=SHA, now="2026-08-30T00:00:00Z")
    return source, target


def _plan(tmp_path: Path):
    source, target = _fixture(tmp_path)
    plan = plan_legacy_bridge_migration(
        source,
        target,
        attestation_id="task061-test-attestation",
        security_backend=SecureBackend(),
    )
    return source, target, plan


def _snapshot(target, migration_id: str) -> Path:
    return target.layout.migration / "task061" / "snapshots" / migration_id


def test_migrates_all_unknown_evidence_to_non_admitting_snapshot(tmp_path: Path) -> None:
    source, target, plan = _plan(tmp_path)
    before = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    receipt = execute_legacy_bridge_migration(
        plan,
        confirmation=plan.confirmation(),
        security_backend=SecureBackend(),
    )
    assert receipt["state"] == "READBACK_VERIFIED"
    assert receipt["file_count"] == 2
    assert receipt["directory_count"] == 3
    assert receipt["unknown_files_preserved"] is True
    for name in ("source_deleted", "source_modified", "active_bridge_view_modified", "profile_admitted", "learning_adopted", "connector_config_modified", "activation_authorized", "timeline_mutated", "resolve_written", "external_effect_authorized"):
        assert receipt[name] is False
    after = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert after == before
    snapshot = _snapshot(target, plan.migration_id) / "payload"
    assert (snapshot / "learning-inbox" / "unknown.json").read_bytes() == before["learning-inbox/unknown.json"]
    assert (snapshot / "preference" / "current-profile.json").read_bytes() == before["preference/current-profile.json"]
    assert not any(target.layout.inbox.iterdir())
    assert not target.layout.current_profile.exists()


def test_receipt_validates_against_closed_schema_and_mirror(tmp_path: Path) -> None:
    _source, _target, plan = _plan(tmp_path)
    receipt = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    root = Path(__file__).resolve().parents[1]
    public = root / "schemas" / "montage-learning-bridge-migration.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / public.name
    assert public.read_bytes() == mirror.read_bytes()
    Draft202012Validator(json.loads(public.read_text(encoding="utf-8"))).validate(receipt)
    body = dict(receipt)
    supplied = body.pop("receipt_sha256")
    assert supplied == sha256_json(body)
    assert not any("path" in key for key in receipt)


def test_duplicate_exact_migration_is_a_readback_noop(tmp_path: Path) -> None:
    _source, _target, plan = _plan(tmp_path)
    first = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    second = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert second == first


def test_terminal_migration_can_be_reopened_as_sealed_exact_readback(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)
    receipt = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    readback = read_legacy_bridge_migration(target, migration_id=plan.migration_id)
    value = readback.to_dict()
    assert value["receipt"] == receipt
    assert value["exact_snapshot_verified"] is True
    assert value["active_bridge_view_modified"] is False
    assert value["profile_admitted"] is False
    assert value["activation_authorized"] is False


def test_exact_confirmation_is_required_before_any_migration_write(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)
    with pytest.raises(MontageLearningBridgeMigrationError, match="exact migration confirmation"):
        execute_legacy_bridge_migration(plan, confirmation="yes", security_backend=SecureBackend())
    assert not (target.layout.migration / "task061").exists()


def test_source_drift_after_plan_fails_before_snapshot(tmp_path: Path) -> None:
    source, target, plan = _plan(tmp_path)
    (source / "learning-inbox" / "unknown.json").write_bytes(b"changed")
    with pytest.raises(MontageLearningBridgeMigrationError, match="source tree no longer matches plan"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert not _snapshot(target, plan.migration_id).exists()


def test_target_descriptor_drift_fails_before_snapshot(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)
    descriptor = target.layout.root / "bridge-instance.json"
    value = json.loads(descriptor.read_text(encoding="utf-8"))
    value["installer_manifest_sha256"] = "sha256:" + "b" * 64
    descriptor.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(Exception):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert not _snapshot(target, plan.migration_id).exists()


def test_non_secure_target_cannot_be_planned(tmp_path: Path) -> None:
    source, target = _fixture(tmp_path)
    with pytest.raises(MontageLearningBridgeMigrationError, match="not SECURE"):
        plan_legacy_bridge_migration(source, target, attestation_id="unsafe", security_backend=SharedWriterBackend())


@pytest.mark.parametrize("phase", ["after_prepared", "after_copy", "after_snapshot_commit"])
def test_every_crash_phase_recovers_without_clobber(tmp_path: Path, phase: str) -> None:
    _source, target, plan = _plan(tmp_path)
    raised = False

    def crash(current: str, _path: Path) -> None:
        nonlocal raised
        if current == phase and not raised:
            raised = True
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend(), hook=crash)
    receipt = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert receipt["state"] == "READBACK_VERIFIED"
    assert (_snapshot(target, plan.migration_id) / "manifest.json").is_file()


def test_staging_collision_is_never_overwritten(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)

    def crash(phase: str, _path: Path) -> None:
        if phase == "after_prepared":
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend(), hook=crash)
    staging = target.layout.migration / "task061" / "staging" / plan.migration_id / "payload" / "learning-inbox"
    staging.mkdir(parents=True)
    (staging / "unknown.json").write_bytes(b"attacker")
    with pytest.raises(MontageLearningBridgeMigrationError, match="staging collision"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert (staging / "unknown.json").read_bytes() == b"attacker"


def test_committed_snapshot_tamper_is_rejected(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)
    execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    payload = _snapshot(target, plan.migration_id) / "payload" / "learning-inbox" / "unknown.json"
    payload.write_bytes(b"tampered")
    with pytest.raises(MontageLearningBridgeMigrationError, match="snapshot read-back mismatch"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())


def test_symlink_and_hardlink_sources_are_rejected(tmp_path: Path) -> None:
    source, target = _fixture(tmp_path)
    external = tmp_path / "external"
    external.write_bytes(b"external")
    link = source / "link"
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(MontageLearningBridgeMigrationError):
        plan_legacy_bridge_migration(source, target, attestation_id="symlink", security_backend=SecureBackend())
    link.unlink()
    hardlink = source / "hardlink"
    try:
        os.link(external, hardlink)
    except OSError:
        pytest.skip("hardlink creation unavailable")
    with pytest.raises(MontageLearningBridgeMigrationError, match="hardlinked"):
        plan_legacy_bridge_migration(source, target, attestation_id="hardlink", security_backend=SecureBackend())


def test_source_and_target_containment_is_rejected(tmp_path: Path) -> None:
    install = tmp_path / "install"
    install.mkdir()
    target = provision_installed_bridge(install, installer_manifest_sha256=SHA, now="2026-08-30T00:00:00Z")
    nested = target.layout.root / "legacy"
    nested.mkdir()
    with pytest.raises(MontageLearningBridgeMigrationError, match="must not contain"):
        plan_legacy_bridge_migration(nested, target, attestation_id="nested", security_backend=SecureBackend())


def test_source_under_symlink_ancestor_is_rejected(tmp_path: Path) -> None:
    source, target = _fixture(tmp_path)
    alias = tmp_path / "legacy-alias"
    try:
        alias.symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation unavailable")
    with pytest.raises(MontageLearningBridgeMigrationError, match="non-reparse"):
        plan_legacy_bridge_migration(alias, target, attestation_id="alias", security_backend=SecureBackend())


def test_interrupted_atomic_file_publish_recovers_from_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source, target, plan = _plan(tmp_path)
    real_link = os.link
    raised = False

    def crash_link(source: str | bytes | Path, destination: str | bytes | Path, *args, **kwargs):
        nonlocal raised
        if not raised and ".task061-" in str(source):
            raised = True
            raise OSError("synthetic link interruption")
        return real_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "link", crash_link)
    with pytest.raises(MontageLearningBridgeMigrationError, match="atomic migration file write failed"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    monkeypatch.setattr(os, "link", real_link)
    receipt = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    assert receipt["state"] == "READBACK_VERIFIED"
    assert (_snapshot(target, plan.migration_id) / "payload" / "learning-inbox" / "unknown.json").is_file()


def test_unknown_extra_snapshot_file_fails_closed(tmp_path: Path) -> None:
    _source, target, plan = _plan(tmp_path)
    execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())
    (_snapshot(target, plan.migration_id) / "payload" / "extra.bin").write_bytes(b"extra")
    with pytest.raises(MontageLearningBridgeMigrationError, match="snapshot read-back mismatch"):
        execute_legacy_bridge_migration(plan, confirmation=plan.confirmation(), security_backend=SecureBackend())


def test_real_windows_temporary_directory_migration(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("real Windows security descriptor test")
    source, target = _fixture(tmp_path)
    security = attest_bridge_security(
        target.layout.root,
        attestation_id="real-windows-temp-preflight",
    )
    if security.reason_codes == ("WRONG_OWNER",):
        assert security.state is BridgeSecurityState.BRIDGE_REPAIR_REQUIRED
        pytest.skip(
            "host temporary directory is not owned by the current Windows user"
        )
    plan = plan_legacy_bridge_migration(source, target, attestation_id="real-windows-temp")
    receipt = execute_legacy_bridge_migration(plan, confirmation=plan.confirmation())
    assert receipt["state"] == "READBACK_VERIFIED"
