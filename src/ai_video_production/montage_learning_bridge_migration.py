"""TASK-061 crash-safe archival migration for legacy bridge evidence.

Migration is deliberately non-admitting: every source object is copied into a
private snapshot below the installer-selected bridge migration directory.  No
file is placed in the active inbox or preference view, and the source is never
renamed or deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Callable

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .montage_learning_bridge_security import (
    BridgeSecurityAttestation,
    BridgeSecurityBackend,
    BridgeSecurityState,
    attest_bridge_security,
)
from .montage_learning_installation import (
    InstalledBridgeDiscovery,
    discover_installed_bridge,
)
from .serialization import sha256_bytes, sha256_json


MIGRATION_SCHEMA_VERSION = "1.0.0"
MIGRATION_RECEIPT_TYPE = "BvpMontageLearningBridgeMigrationReceipt"
MIGRATION_JOURNAL_TYPE = "BvpMontageLearningBridgeMigrationJournal"
MIGRATION_MANIFEST_TYPE = "BvpMontageLearningBridgeMigrationManifest"
_MAX_FILES = 1024
_MAX_DIRECTORIES = 1024
_MAX_BYTES = 256 * 1024 * 1024
_MAX_FILE_BYTES = 16 * 1024 * 1024
_WINDOWS_REPARSE_POINT = 0x400
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^migration-[0-9a-f]{32}$")
_PLAN_SEAL = object()


class MontageLearningBridgeMigrationError(ValueError):
    """Raised when a migration plan, source, target, or recovery is unsafe."""


@dataclass(frozen=True, slots=True)
class MigrationEntry:
    relative_path: str
    kind: str
    bytes: int
    content_sha256: str | None
    identity: tuple[int, int, int, int]

    def manifest_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "kind": self.kind,
            "bytes": self.bytes,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True, slots=True)
class BridgeMigrationPlan:
    migration_id: str
    source_root: Path
    source_root_identity_sha256: str
    source_tree_sha256: str
    entries: tuple[MigrationEntry, ...]
    target_install_root: Path
    target_install_instance_id: str
    target_descriptor_sha256: str
    target_owner_manifest_sha256: str
    security_attestation_id: str
    security_attestation_sha256: str
    security_owner_sid_sha256: str
    security_current_user_sid_sha256: str
    security_ancestor_count: int
    plan_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _PLAN_SEAL:
            raise MontageLearningBridgeMigrationError("migration plan is not sealed")
        if _ID_RE.fullmatch(self.migration_id) is None:
            raise MontageLearningBridgeMigrationError("migration id is invalid")
        for value in (
            self.source_root_identity_sha256,
            self.source_tree_sha256,
            self.target_descriptor_sha256,
            self.target_owner_manifest_sha256,
            self.security_attestation_sha256,
            self.security_owner_sid_sha256,
            self.security_current_user_sid_sha256,
            self.plan_sha256,
        ):
            _required_sha(value)
        if type(self.security_ancestor_count) is not int or self.security_ancestor_count < 0:
            raise MontageLearningBridgeMigrationError("security ancestor count is invalid")
        if not self.source_root.is_absolute() or not self.target_install_root.is_absolute():
            raise MontageLearningBridgeMigrationError("migration coordinates must be absolute")
        if type(self.entries) is not tuple or any(type(item) is not MigrationEntry for item in self.entries):
            raise MontageLearningBridgeMigrationError("migration entries are invalid")

    @property
    def file_count(self) -> int:
        return sum(item.kind == "FILE" for item in self.entries)

    @property
    def directory_count(self) -> int:
        return sum(item.kind == "DIRECTORY" for item in self.entries)

    @property
    def total_bytes(self) -> int:
        return sum(item.bytes for item in self.entries)

    def confirmation(self) -> str:
        return f"MIGRATE_LEGACY_BRIDGE:{self.migration_id}"


MigrationHook = Callable[[str, Path], None]


def plan_legacy_bridge_migration(
    source_root: str | Path,
    target: InstalledBridgeDiscovery,
    *,
    attestation_id: str,
    security_backend: BridgeSecurityBackend | None = None,
) -> BridgeMigrationPlan:
    """Pin an explicit source tree and exact installer-selected target."""

    source = _absolute_path(source_root, "source root")
    install_root = _absolute_path(target.install_root, "target install root")
    _reject_path_overlap(source, target.layout.root)
    current_target = _rediscover_exact(target)
    security = _secure_attestation(
        current_target, attestation_id=attestation_id, backend=security_backend
    )
    entries, source_identity, tree_sha = _snapshot_source(source)
    attestation_sha = security.to_dict()["attestation_sha256"]
    body = _plan_body(
        source_identity=source_identity,
        source_tree_sha256=tree_sha,
        entries=entries,
        target=current_target,
        attestation_id=attestation_id,
        attestation_sha256=attestation_sha,
        owner_sid_sha256=_required_sha(security.owner_sid_sha256),
        current_user_sid_sha256=_required_sha(security.current_user_sid_sha256),
        ancestor_count=security.ancestor_count,
    )
    plan_sha = sha256_json(body)
    migration_id = f"migration-{plan_sha.removeprefix('sha256:')[:32]}"
    return BridgeMigrationPlan(
        migration_id=migration_id,
        source_root=source,
        source_root_identity_sha256=source_identity,
        source_tree_sha256=tree_sha,
        entries=entries,
        target_install_root=install_root,
        target_install_instance_id=current_target.descriptor.install_instance_id,
        target_descriptor_sha256=current_target.descriptor.descriptor_sha256,
        target_owner_manifest_sha256=current_target.owner_manifest_sha256,
        security_attestation_id=attestation_id,
        security_attestation_sha256=attestation_sha,
        security_owner_sid_sha256=_required_sha(security.owner_sid_sha256),
        security_current_user_sid_sha256=_required_sha(security.current_user_sid_sha256),
        security_ancestor_count=security.ancestor_count,
        plan_sha256=plan_sha,
        _seal=_PLAN_SEAL,
    )


def execute_legacy_bridge_migration(
    plan: BridgeMigrationPlan,
    *,
    confirmation: str,
    security_backend: BridgeSecurityBackend | None = None,
    hook: MigrationHook | None = None,
) -> dict[str, object]:
    """Copy a sealed source into an archival snapshot and return read-back proof."""

    if not isinstance(plan, BridgeMigrationPlan) or plan._seal is not _PLAN_SEAL:
        raise MontageLearningBridgeMigrationError("migration plan is not sealed")
    if confirmation != plan.confirmation():
        raise MontageLearningBridgeMigrationError("exact migration confirmation required")
    target = discover_installed_bridge(plan.target_install_root)
    _require_target_matches(plan, target)
    _require_security_matches(plan, target, security_backend)
    _require_source_matches(plan)

    private_root = target.layout.migration / "task061"
    journal_root = private_root / "journals"
    staging_root = private_root / "staging" / plan.migration_id
    snapshot_root = private_root / "snapshots" / plan.migration_id
    journal_path = journal_root / f"{plan.migration_id}.json"
    for directory in (private_root, journal_root, staging_root.parent, snapshot_root.parent):
        _ensure_safe_directory(directory)

    with exclusive_file_update_lock(journal_path):
        existing = _read_json_if_exists(journal_path)
        if existing is not None:
            _validate_journal(existing, plan)
            if existing["phase"] == "READBACK_VERIFIED":
                receipt = existing["receipt"]
                _validate_receipt(receipt, plan)
                _verify_snapshot(snapshot_root, plan)
                _require_source_matches(plan)
                _require_target_matches(plan, discover_installed_bridge(plan.target_install_root))
                _require_security_matches(plan, target, security_backend)
                return dict(receipt)
        else:
            _write_journal(journal_path, plan, "PREPARED", None)
            _call_hook(hook, "after_prepared", journal_path)

        if snapshot_root.exists() or snapshot_root.is_symlink():
            if staging_root.exists() or staging_root.is_symlink():
                raise MontageLearningBridgeMigrationError(
                    "snapshot and staging both exist; recovery is ambiguous"
                )
            _verify_snapshot(snapshot_root, plan)
        else:
            _copy_snapshot_payload(plan, staging_root)
            _write_manifest(staging_root, plan)
            _verify_snapshot(staging_root, plan)
            _write_journal(journal_path, plan, "COPIED", None)
            _call_hook(hook, "after_copy", staging_root)
            _require_source_matches(plan)
            _require_target_matches(plan, discover_installed_bridge(plan.target_install_root))
            _require_security_matches(plan, target, security_backend)
            if snapshot_root.exists() or snapshot_root.is_symlink():
                raise MontageLearningBridgeMigrationError("snapshot appeared before commit")
            os.replace(staging_root, snapshot_root)
            _sync_directory(snapshot_root.parent)
            _call_hook(hook, "after_snapshot_commit", snapshot_root)

        _verify_snapshot(snapshot_root, plan)
        _write_journal(journal_path, plan, "SNAPSHOT_COMMITTED", None)
        _call_hook(hook, "before_readback", snapshot_root)
        _require_source_matches(plan)
        final_target = discover_installed_bridge(plan.target_install_root)
        _require_target_matches(plan, final_target)
        final_security = _require_security_matches(plan, final_target, security_backend)
        receipt = _build_receipt(
            plan, str(final_security.to_dict()["attestation_sha256"])
        )
        _validate_receipt(receipt, plan)
        _write_journal(journal_path, plan, "READBACK_VERIFIED", receipt)
        readback = _read_json(journal_path)
        _validate_journal(readback, plan)
        if readback["phase"] != "READBACK_VERIFIED" or readback["receipt"] != receipt:
            raise MontageLearningBridgeMigrationError("terminal receipt read-back mismatch")
        return receipt


def _plan_body(
    *,
    source_identity: str,
    source_tree_sha256: str,
    entries: tuple[MigrationEntry, ...],
    target: InstalledBridgeDiscovery,
    attestation_id: str,
    attestation_sha256: str,
    owner_sid_sha256: str,
    current_user_sid_sha256: str,
    ancestor_count: int,
) -> dict[str, object]:
    return {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "source_root_identity_sha256": source_identity,
        "source_tree_sha256": source_tree_sha256,
        "entries_sha256": sha256_json([item.manifest_dict() for item in entries]),
        "target_install_instance_id": target.descriptor.install_instance_id,
        "target_descriptor_sha256": target.descriptor.descriptor_sha256,
        "target_owner_manifest_sha256": target.owner_manifest_sha256,
        "security_attestation_id": attestation_id,
        "security_attestation_sha256": attestation_sha256,
        "security_owner_sid_sha256": owner_sid_sha256,
        "security_current_user_sid_sha256": current_user_sid_sha256,
        "security_ancestor_count": ancestor_count,
    }


def _snapshot_source(
    root: Path,
) -> tuple[tuple[MigrationEntry, ...], str, str]:
    ancestor_identities = _safe_ancestor_chain(root)
    root_info = _require_safe_directory(root)
    root_identity = _identity_sha(root, root_info)
    entries: list[MigrationEntry] = []
    seen_casefold: set[str] = set()
    total = 0
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        directory_names.sort(key=str.casefold)
        file_names.sort(key=str.casefold)
        current_path = Path(current)
        _require_safe_directory(current_path)
        for name in tuple(directory_names):
            path = current_path / name
            info = _require_safe_directory(path)
            relative = _relative(root, path)
            _claim_casefold(relative, seen_casefold)
            entries.append(MigrationEntry(relative, "DIRECTORY", 0, None, _identity(info)))
        for name in file_names:
            path = current_path / name
            relative = _relative(root, path)
            _claim_casefold(relative, seen_casefold)
            body, info = _read_pinned_file(path)
            total += len(body)
            if total > _MAX_BYTES:
                raise MontageLearningBridgeMigrationError("source tree exceeds byte limit")
            entries.append(
                MigrationEntry(relative, "FILE", len(body), sha256_bytes(body), _identity(info))
            )
    entries.sort(key=lambda item: (item.relative_path.casefold(), item.relative_path))
    if sum(item.kind == "FILE" for item in entries) > _MAX_FILES:
        raise MontageLearningBridgeMigrationError("source tree exceeds file limit")
    if sum(item.kind == "DIRECTORY" for item in entries) > _MAX_DIRECTORIES:
        raise MontageLearningBridgeMigrationError("source tree exceeds directory limit")
    end_info = _require_safe_directory(root)
    if _identity_sha(root, end_info) != root_identity:
        raise MontageLearningBridgeMigrationError("source root changed during discovery")
    if _safe_ancestor_chain(root) != ancestor_identities:
        raise MontageLearningBridgeMigrationError("source ancestor identity changed")
    tree_sha = sha256_json([item.manifest_dict() for item in entries])
    return tuple(entries), root_identity, tree_sha


def _read_pinned_file(path: Path) -> tuple[bytes, os.stat_result]:
    if path.is_symlink():
        raise MontageLearningBridgeMigrationError("source symlink is forbidden")
    try:
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            _require_regular_file(before)
            if before.st_size > _MAX_FILE_BYTES:
                raise MontageLearningBridgeMigrationError("source file exceeds byte limit")
            body = handle.read(_MAX_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise MontageLearningBridgeMigrationError("source file read failed") from exc
    if len(body) > _MAX_FILE_BYTES or _identity(before) != _identity(after):
        raise MontageLearningBridgeMigrationError("source file changed during read")
    path_info = os.lstat(path)
    _require_regular_file(path_info)
    if _identity(path_info) != _identity(after):
        raise MontageLearningBridgeMigrationError("source path identity changed")
    return body, after


def _copy_snapshot_payload(plan: BridgeMigrationPlan, staging_root: Path) -> None:
    _ensure_safe_directory(staging_root)
    payload_root = staging_root / "payload"
    _ensure_safe_directory(payload_root)
    for item in plan.entries:
        target = payload_root.joinpath(*PurePosixPath(item.relative_path).parts)
        _require_contained(payload_root, target)
        if item.kind == "DIRECTORY":
            _ensure_safe_directory(target)
            continue
        _ensure_safe_directory(target.parent)
        body, info = _read_pinned_file(
            plan.source_root.joinpath(*PurePosixPath(item.relative_path).parts)
        )
        if _identity(info) != item.identity or sha256_bytes(body) != item.content_sha256:
            raise MontageLearningBridgeMigrationError("source entry no longer matches plan")
        if target.exists() or target.is_symlink():
            existing, _ = _read_pinned_file(target)
            if existing != body:
                raise MontageLearningBridgeMigrationError("staging collision")
            continue
        _write_new_file(target, body)


def _write_manifest(root: Path, plan: BridgeMigrationPlan) -> None:
    body: dict[str, object] = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "message_type": MIGRATION_MANIFEST_TYPE,
        "migration_id": plan.migration_id,
        "plan_sha256": plan.plan_sha256,
        "source_root_identity_sha256": plan.source_root_identity_sha256,
        "source_tree_sha256": plan.source_tree_sha256,
        "entries": [item.manifest_dict() for item in plan.entries],
    }
    body["manifest_sha256"] = sha256_json(body)
    path = root / "manifest.json"
    if path.exists() or path.is_symlink():
        if _read_json(path) != body:
            raise MontageLearningBridgeMigrationError("migration manifest collision")
        return
    AtomicJsonWriter.write(path, body)


def _verify_snapshot(root: Path, plan: BridgeMigrationPlan) -> None:
    _require_safe_directory(root)
    manifest = _read_json(root / "manifest.json")
    expected_entries = [item.manifest_dict() for item in plan.entries]
    expected = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "message_type": MIGRATION_MANIFEST_TYPE,
        "migration_id": plan.migration_id,
        "plan_sha256": plan.plan_sha256,
        "source_root_identity_sha256": plan.source_root_identity_sha256,
        "source_tree_sha256": plan.source_tree_sha256,
        "entries": expected_entries,
    }
    supplied_hash = manifest.get("manifest_sha256") if isinstance(manifest, dict) else None
    if supplied_hash != sha256_json(expected) or manifest != {**expected, "manifest_sha256": supplied_hash}:
        raise MontageLearningBridgeMigrationError("migration manifest is invalid")
    actual: list[dict[str, object]] = []
    payload_root = root / "payload"
    _require_safe_directory(payload_root)
    for current, directory_names, file_names in os.walk(payload_root, topdown=True, followlinks=False):
        directory_names.sort(key=str.casefold)
        file_names.sort(key=str.casefold)
        current_path = Path(current)
        _require_safe_directory(current_path)
        for name in directory_names:
            path = current_path / name
            _require_safe_directory(path)
            actual.append({"relative_path": _relative(payload_root, path), "kind": "DIRECTORY", "bytes": 0, "content_sha256": None})
        for name in file_names:
            path = current_path / name
            body, _ = _read_pinned_file(path)
            actual.append({"relative_path": _relative(payload_root, path), "kind": "FILE", "bytes": len(body), "content_sha256": sha256_bytes(body)})
    actual.sort(key=lambda item: (str(item["relative_path"]).casefold(), str(item["relative_path"])))
    if actual != expected_entries:
        raise MontageLearningBridgeMigrationError("snapshot read-back mismatch")


def _build_receipt(
    plan: BridgeMigrationPlan,
    final_security_attestation_sha256: str,
) -> dict[str, object]:
    _required_sha(final_security_attestation_sha256)
    body: dict[str, object] = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "message_type": MIGRATION_RECEIPT_TYPE,
        "task_owner": "TASK-061",
        "migration_id": plan.migration_id,
        "plan_sha256": plan.plan_sha256,
        "source_root_identity_sha256": plan.source_root_identity_sha256,
        "source_tree_sha256": plan.source_tree_sha256,
        "target_install_instance_id": plan.target_install_instance_id,
        "target_descriptor_sha256": plan.target_descriptor_sha256,
        "target_owner_manifest_sha256": plan.target_owner_manifest_sha256,
        "security_attestation_sha256": plan.security_attestation_sha256,
        "final_security_attestation_sha256": final_security_attestation_sha256,
        "file_count": plan.file_count,
        "directory_count": plan.directory_count,
        "total_bytes": plan.total_bytes,
        "state": "READBACK_VERIFIED",
        "unknown_files_preserved": True,
        "source_deleted": False,
        "source_modified": False,
        "active_bridge_view_modified": False,
        "profile_admitted": False,
        "learning_adopted": False,
        "connector_config_modified": False,
        "activation_authorized": False,
        "timeline_mutated": False,
        "resolve_written": False,
        "external_effect_authorized": False,
    }
    body["receipt_sha256"] = sha256_json(body)
    return body


def _validate_receipt(value: object, plan: BridgeMigrationPlan) -> None:
    if type(value) is not dict:
        raise MontageLearningBridgeMigrationError("migration receipt mismatch")
    final_security = value.get("final_security_attestation_sha256")
    if type(final_security) is not str:
        raise MontageLearningBridgeMigrationError("migration receipt mismatch")
    expected = _build_receipt(plan, final_security)
    if value != expected:
        raise MontageLearningBridgeMigrationError("migration receipt mismatch")


def _write_journal(
    path: Path,
    plan: BridgeMigrationPlan,
    phase: str,
    receipt: dict[str, object] | None,
) -> None:
    if phase not in {"PREPARED", "COPIED", "SNAPSHOT_COMMITTED", "READBACK_VERIFIED"}:
        raise MontageLearningBridgeMigrationError("migration journal phase is invalid")
    body: dict[str, object] = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "message_type": MIGRATION_JOURNAL_TYPE,
        "migration_id": plan.migration_id,
        "plan_sha256": plan.plan_sha256,
        "phase": phase,
        "receipt": receipt,
    }
    body["journal_sha256"] = sha256_json(body)
    AtomicJsonWriter.write(path, body)


def _validate_journal(value: object, plan: BridgeMigrationPlan) -> None:
    if type(value) is not dict:
        raise MontageLearningBridgeMigrationError("migration journal is invalid")
    expected_fields = {"schema_version", "message_type", "migration_id", "plan_sha256", "phase", "receipt", "journal_sha256"}
    if set(value) != expected_fields:
        raise MontageLearningBridgeMigrationError("migration journal fields mismatch")
    body = dict(value)
    supplied = body.pop("journal_sha256")
    if (
        value["schema_version"] != MIGRATION_SCHEMA_VERSION
        or value["message_type"] != MIGRATION_JOURNAL_TYPE
        or value["migration_id"] != plan.migration_id
        or value["plan_sha256"] != plan.plan_sha256
        or value["phase"] not in {"PREPARED", "COPIED", "SNAPSHOT_COMMITTED", "READBACK_VERIFIED"}
        or supplied != sha256_json(body)
    ):
        raise MontageLearningBridgeMigrationError("migration journal identity mismatch")
    if (value["phase"] == "READBACK_VERIFIED") is not (value["receipt"] is not None):
        raise MontageLearningBridgeMigrationError("migration journal receipt phase mismatch")


def _require_source_matches(plan: BridgeMigrationPlan) -> None:
    entries, identity, tree_sha = _snapshot_source(plan.source_root)
    if identity != plan.source_root_identity_sha256 or tree_sha != plan.source_tree_sha256 or entries != plan.entries:
        raise MontageLearningBridgeMigrationError("source tree no longer matches plan")


def _rediscover_exact(target: InstalledBridgeDiscovery) -> InstalledBridgeDiscovery:
    current = discover_installed_bridge(target.install_root)
    if current.public_receipt() != target.public_receipt():
        raise MontageLearningBridgeMigrationError("installed bridge discovery drifted")
    return current


def _require_target_matches(plan: BridgeMigrationPlan, target: InstalledBridgeDiscovery) -> None:
    if (
        target.descriptor.install_instance_id != plan.target_install_instance_id
        or target.descriptor.descriptor_sha256 != plan.target_descriptor_sha256
        or target.owner_manifest_sha256 != plan.target_owner_manifest_sha256
    ):
        raise MontageLearningBridgeMigrationError("installed bridge identity mismatch")


def _secure_attestation(
    target: InstalledBridgeDiscovery,
    *,
    attestation_id: str,
    backend: BridgeSecurityBackend | None,
) -> BridgeSecurityAttestation:
    result = attest_bridge_security(
        target.layout.root,
        attestation_id=attestation_id,
        backend=backend,
    )
    if result.state is not BridgeSecurityState.SECURE:
        raise MontageLearningBridgeMigrationError("target bridge security is not SECURE")
    return result


def _require_security_matches(
    plan: BridgeMigrationPlan,
    target: InstalledBridgeDiscovery,
    backend: BridgeSecurityBackend | None,
) -> BridgeSecurityAttestation:
    current = _secure_attestation(
        target,
        attestation_id=plan.security_attestation_id,
        backend=backend,
    )
    if (
        current.owner_sid_sha256 != plan.security_owner_sid_sha256
        or current.current_user_sid_sha256 != plan.security_current_user_sid_sha256
        or current.ancestor_count != plan.security_ancestor_count
    ):
        raise MontageLearningBridgeMigrationError("bridge security identity drifted")
    return current


def _required_sha(value: str | None) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningBridgeMigrationError("required security digest is unavailable")
    return value


def _absolute_path(value: str | Path, field: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise MontageLearningBridgeMigrationError(f"{field} must be absolute and normalized")
    return path


def _reject_path_overlap(source: Path, target: Path) -> None:
    left = os.path.normcase(os.path.abspath(source))
    right = os.path.normcase(os.path.abspath(target))
    try:
        common = os.path.commonpath((left, right))
    except ValueError as exc:
        raise MontageLearningBridgeMigrationError("source and target drives differ unexpectedly") from exc
    if common in {left, right}:
        raise MontageLearningBridgeMigrationError("source and target must not contain each other")


def _relative(root: Path, path: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise MontageLearningBridgeMigrationError("source path escaped root") from exc
    pure = PurePosixPath(value)
    if not value or value.startswith("/") or any(part in {"", ".", ".."} for part in pure.parts):
        raise MontageLearningBridgeMigrationError("source relative path is invalid")
    return value


def _claim_casefold(relative: str, seen: set[str]) -> None:
    folded = relative.casefold()
    if folded in seen:
        raise MontageLearningBridgeMigrationError("case-colliding source paths")
    seen.add(folded)


def _require_contained(root: Path, candidate: Path) -> None:
    if os.path.commonpath((os.path.abspath(root), os.path.abspath(candidate))) != os.path.abspath(root):
        raise MontageLearningBridgeMigrationError("migration target escaped snapshot root")


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _identity_sha(path: Path, info: os.stat_result) -> str:
    return sha256_json({"resolved_path": str(path.resolve(strict=True)), "st_dev": info.st_dev, "st_ino": info.st_ino})


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)


def _require_safe_directory(path: Path) -> os.stat_result:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise MontageLearningBridgeMigrationError("required directory is unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or _is_reparse(info) or path.is_symlink():
        raise MontageLearningBridgeMigrationError("directory must be non-reparse and non-symlink")
    return info


def _ensure_safe_directory(path: Path) -> os.stat_result:
    if path.exists() or path.is_symlink():
        return _require_safe_directory(path)
    _ensure_safe_directory(path.parent)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    return _require_safe_directory(path)


def _require_regular_file(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode) or _is_reparse(info) or getattr(info, "st_nlink", 1) != 1:
        raise MontageLearningBridgeMigrationError("source must be a non-reparse non-hardlinked regular file")


def _write_new_file(path: Path, body: bytes) -> None:
    digest = sha256(body).hexdigest()
    temporary = path.with_name(f".{path.name}.task061-{digest}.tmp")
    try:
        if temporary.exists() or temporary.is_symlink():
            try:
                temporary_body, _ = _read_pinned_file(temporary)
            except MontageLearningBridgeMigrationError:
                temporary.unlink(missing_ok=True)
            else:
                if temporary_body != body:
                    temporary.unlink(missing_ok=True)
        if not temporary.exists():
            with temporary.open("xb", buffering=0) as handle:
                handle.write(body)
                os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing, _ = _read_pinned_file(path)
            if existing != body:
                raise MontageLearningBridgeMigrationError("migration output collision")
        temporary.unlink(missing_ok=True)
        _sync_directory(path.parent)
    except MontageLearningBridgeMigrationError:
        raise
    except OSError as exc:
        raise MontageLearningBridgeMigrationError("atomic migration file write failed") from exc


def _safe_ancestor_chain(path: Path) -> tuple[tuple[str, int, int], ...]:
    identities: list[tuple[str, int, int]] = []
    current = path
    while True:
        info = _require_safe_directory(current)
        identities.append((os.path.normcase(os.path.abspath(current)), info.st_dev, info.st_ino))
        if current.parent == current:
            break
        current = current.parent
    return tuple(identities)


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() and not path.is_symlink():
        return None
    return _read_json(path)


def _read_json(path: Path) -> dict[str, Any]:
    body, _ = _read_pinned_file(path)
    try:
        value = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningBridgeMigrationError("migration JSON is invalid") from exc
    if type(value) is not dict:
        raise MontageLearningBridgeMigrationError("migration JSON must be an object")
    return value


def _sync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise MontageLearningBridgeMigrationError("migration directory durability failed") from exc


def _call_hook(hook: MigrationHook | None, phase: str, path: Path) -> None:
    if hook is not None:
        hook(phase, path)


__all__ = [
    "BridgeMigrationPlan",
    "MIGRATION_SCHEMA_VERSION",
    "MigrationEntry",
    "MontageLearningBridgeMigrationError",
    "execute_legacy_bridge_migration",
    "plan_legacy_bridge_migration",
]
