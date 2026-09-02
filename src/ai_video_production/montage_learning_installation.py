"""Installer-relative montage-learning bridge discovery and provisioning.

The active bridge is never derived from a machine-global fixed directory.  The
installer-selected application root is the only coordinate accepted here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Callable
import uuid

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .montage_learning_file_bridge import (
    BridgeLayout,
    MontageLearningFileBridgeError,
    load_bridge_owner,
    provision_bridge,
)
from .secure_authority_io import SecureAuthorityIO, SecureAuthorityIOError
from .serialization import canonical_json_bytes, sha256_json


DESCRIPTOR_FILENAME = "bridge-instance.json"
DESCRIPTOR_MESSAGE_TYPE = "BvpMontageLearningBridgeInstance"
DESCRIPTOR_SCHEMA_VERSION = "1.0.0"
PRODUCT_ID = "BAI_VIDEO_PRODUCTION"
BRIDGE_RELATIVE_PATH = "data/montage-learning-bridge"
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_INSTANCE_RE = re.compile(r"^bvp-install-[0-9a-f]{32}$")
_MAX_DESCRIPTOR_BYTES = 64 * 1024
INSTALLER_READBACK_FILENAME = "installer-readback.json"
_MAX_INSTALLER_READBACK_BYTES = 64 * 1024
_WINDOWS_REPARSE_POINT = 0x400

ReceiptFailureInjector = Callable[[str, Path], None]


class MontageLearningInstallationError(ValueError):
    """Raised when an installer instance or descriptor is not trustworthy."""


@dataclass(frozen=True, slots=True)
class BridgeInstanceDescriptor:
    install_instance_id: str
    bridge_relative_path: str
    installer_manifest_sha256: str
    created_at: str
    updated_at: str
    descriptor_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DESCRIPTOR_SCHEMA_VERSION,
            "message_type": DESCRIPTOR_MESSAGE_TYPE,
            "product_id": PRODUCT_ID,
            "install_instance_id": self.install_instance_id,
            "bridge_relative_path": self.bridge_relative_path,
            "installer_manifest_sha256": self.installer_manifest_sha256,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "descriptor_sha256": self.descriptor_sha256,
        }


@dataclass(frozen=True, slots=True)
class InstalledBridgeDiscovery:
    install_root: Path
    layout: BridgeLayout
    descriptor: BridgeInstanceDescriptor
    owner_manifest_sha256: str

    def public_receipt(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningBridgeDiscoveryReceipt",
            "product_id": PRODUCT_ID,
            "install_instance_id": self.descriptor.install_instance_id,
            "bridge_relative_path": self.descriptor.bridge_relative_path,
            "descriptor_sha256": self.descriptor.descriptor_sha256,
            "owner_manifest_sha256": self.owner_manifest_sha256,
            "capability": "INSTALL_RELATIVE_BRIDGE_DISCOVERY",
            "status": "READY_DISABLED_BY_DEFAULT",
            "connector_enabled": False,
            "activation_authorized": False,
        }


def provision_installed_bridge(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
) -> InstalledBridgeDiscovery:
    """Provision one bridge as an installer-owned, idempotent operation."""

    _require_sha(installer_manifest_sha256, "installer_manifest_sha256")
    layout = BridgeLayout.production(install_root)
    _ensure_installer_data_root(layout)
    descriptor_path = layout.root / DESCRIPTOR_FILENAME
    existing: BridgeInstanceDescriptor | None = None
    if descriptor_path.exists() or descriptor_path.is_symlink():
        existing = _read_descriptor(descriptor_path)

    owner_path = layout.owner_manifest
    if existing is not None:
        instance_id = existing.install_instance_id
        created_at = existing.created_at
    elif owner_path.exists() or owner_path.is_symlink():
        owner = load_bridge_owner(layout)
        instance_id = owner.bridge_instance_id
        created_at = _timestamp(now)
    else:
        instance_id = f"bvp-install-{uuid.uuid4().hex}"
        created_at = _timestamp(now)

    owner = provision_bridge(layout, bridge_instance_id=instance_id)
    updated_at = _timestamp(now)
    body = {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "message_type": DESCRIPTOR_MESSAGE_TYPE,
        "product_id": PRODUCT_ID,
        "install_instance_id": instance_id,
        "bridge_relative_path": BRIDGE_RELATIVE_PATH,
        "installer_manifest_sha256": installer_manifest_sha256,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    document = dict(body)
    document["descriptor_sha256"] = sha256_json(body)
    AtomicJsonWriter.write(
        descriptor_path,
        document,
        validator=_validate_descriptor_document,
    )
    return discover_installed_bridge(install_root)


def discover_installed_bridge(install_root: str | Path) -> InstalledBridgeDiscovery:
    """Read back one exact installer instance without creating or repairing it."""

    root = Path(install_root)
    layout = BridgeLayout.production(root)
    descriptor = _read_descriptor(layout.root / DESCRIPTOR_FILENAME)
    owner = load_bridge_owner(layout)
    if owner.bridge_instance_id != descriptor.install_instance_id:
        raise MontageLearningInstallationError(
            "bridge descriptor and owner instance mismatch"
        )
    return InstalledBridgeDiscovery(
        install_root=root,
        layout=layout,
        descriptor=descriptor,
        owner_manifest_sha256=owner.manifest_sha256,
    )


def provision_and_write_installer_readback(
    install_root: str | Path,
    *,
    installer_manifest_sha256: str,
    now: str | None = None,
    failure_injector: ReceiptFailureInjector | None = None,
) -> tuple[InstalledBridgeDiscovery, Path]:
    """Provision and publish while binding an update to its exact predecessor."""

    root = Path(install_root)
    layout = BridgeLayout.production(root)
    descriptor_path = layout.root / DESCRIPTOR_FILENAME
    if not (descriptor_path.exists() or descriptor_path.is_symlink()):
        discovery = provision_installed_bridge(
            root,
            installer_manifest_sha256=installer_manifest_sha256,
            now=now,
        )
        try:
            return discovery, write_installer_readback(
                discovery,
                failure_injector=failure_injector,
            )
        except Exception:
            _rollback_fresh_installer_publication(discovery)
            raise

    previous = discover_installed_bridge(root)
    target, _ = _installer_readback_coordinates(previous)
    try:
        with exclusive_file_update_lock(target):
            previous = _capture_discovery_source_binding(previous)
            previous_descriptor_bytes = _read_stable_regular_bytes(descriptor_path)
            existing_bytes = _read_stable_regular_bytes(target)
            _validate_existing_installer_readback(
                existing_bytes,
                previous,
                allowed_descriptor_sha256={previous.descriptor.descriptor_sha256},
            )
            discovery = provision_installed_bridge(
                root,
                installer_manifest_sha256=installer_manifest_sha256,
                now=now,
            )
            try:
                return discovery, _write_installer_readback_locked(
                    discovery,
                    allowed_existing_descriptor_sha256={
                        previous.descriptor.descriptor_sha256,
                        discovery.descriptor.descriptor_sha256,
                    },
                    failure_injector=failure_injector,
                )
            except Exception:
                _rollback_installer_update(
                    previous,
                    descriptor_bytes=previous_descriptor_bytes,
                    receipt_bytes=existing_bytes,
                )
                raise
    except ValueError as exc:
        if isinstance(exc, MontageLearningInstallationError):
            raise
        raise MontageLearningInstallationError(
            "installer readback update lock failed"
        ) from exc


def _rollback_fresh_installer_publication(
    discovery: InstalledBridgeDiscovery,
) -> None:
    target, _ = _installer_readback_coordinates(discovery)
    descriptor_path = discovery.layout.root / DESCRIPTOR_FILENAME
    try:
        if _safe_receipt_identity(target) is not None:
            target.unlink()
        current = _capture_discovery_source_binding(discovery)
        if current != discovery:
            raise MontageLearningInstallationError(
                "fresh installer discovery changed before rollback"
            )
        descriptor_path.unlink()
        _directory_fsync(target.parent)
        _directory_fsync(descriptor_path.parent)
    except Exception as rollback_exc:
        raise MontageLearningInstallationError(
            "fresh installer publication rollback requires recovery"
        ) from rollback_exc


def _rollback_installer_update(
    previous: InstalledBridgeDiscovery,
    *,
    descriptor_bytes: bytes,
    receipt_bytes: bytes,
) -> None:
    target, _ = _installer_readback_coordinates(previous)
    descriptor_path = previous.layout.root / DESCRIPTOR_FILENAME
    try:
        current_receipt = (
            None
            if _safe_receipt_identity(target) is None
            else _read_stable_regular_bytes(target)
        )
        if current_receipt != receipt_bytes:
            receipt_document = json.loads(receipt_bytes.decode("utf-8"))
            AtomicJsonWriter.write(target, receipt_document)
        descriptor_document = json.loads(descriptor_bytes.decode("utf-8"))
        _validate_descriptor_document(descriptor_document)
        AtomicJsonWriter.write(
            descriptor_path,
            descriptor_document,
            validator=_validate_descriptor_document,
        )
        _capture_discovery_source_binding(previous)
        restored_receipt = _read_stable_regular_bytes(target)
        _validate_existing_installer_readback(
            restored_receipt,
            previous,
            allowed_descriptor_sha256={previous.descriptor.descriptor_sha256},
        )
    except Exception as rollback_exc:
        raise MontageLearningInstallationError(
            "installer update rollback requires recovery"
        ) from rollback_exc


def write_installer_readback(
    discovery: InstalledBridgeDiscovery,
    *,
    failure_injector: ReceiptFailureInjector | None = None,
) -> Path:
    """Atomically publish the discovery receipt at its sole installer-owned path."""

    target, _ = _installer_readback_coordinates(discovery)
    try:
        with exclusive_file_update_lock(target):
            return _write_installer_readback_locked(
                discovery,
                allowed_existing_descriptor_sha256={
                    discovery.descriptor.descriptor_sha256
                },
                failure_injector=failure_injector,
            )
    except ValueError as exc:
        if isinstance(exc, MontageLearningInstallationError):
            raise
        raise MontageLearningInstallationError(
            "installer readback update lock failed"
        ) from exc


def _write_installer_readback_locked(
    discovery: InstalledBridgeDiscovery,
    *,
    allowed_existing_descriptor_sha256: set[str],
    failure_injector: ReceiptFailureInjector | None,
) -> Path:
    discovery = _capture_discovery_source_binding(discovery)
    target, directories = _installer_readback_coordinates(discovery)
    ancestor_identities = tuple(_safe_directory_identity(path) for path in directories)
    existing_identity = _safe_receipt_identity(target)
    existing_digest: bytes | None = None
    if existing_identity is not None:
        existing_bytes = _read_stable_regular_bytes(target)
        _validate_existing_installer_readback(
            existing_bytes,
            discovery,
            allowed_descriptor_sha256=allowed_existing_descriptor_sha256,
        )
        existing_digest = sha256(existing_bytes).digest()
    data = canonical_json_bytes(discovery.public_receipt()) + b"\n"
    if len(data) > _MAX_INSTALLER_READBACK_BYTES:
        raise MontageLearningInstallationError("installer readback is too large")

    fd, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    replaced = False
    try:
        _verify_directory_identities(directories, ancestor_identities)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _require_safe_regular_file(temporary, expected_size=len(data))
        if _read_stable_regular_bytes(temporary) != data:
            raise MontageLearningInstallationError(
                "installer readback temporary verification failed"
            )
        _call_receipt_failure(failure_injector, "after_temp_fsync", temporary)

        _call_receipt_failure(failure_injector, "before_replace", target)
        discovery = _capture_discovery_source_binding(discovery)
        _verify_directory_identities(directories, ancestor_identities)
        if _safe_receipt_identity(target) != existing_identity:
            raise MontageLearningInstallationError(
                "installer readback target identity changed"
            )
        if existing_identity is not None:
            current_bytes = _read_stable_regular_bytes(target)
            _validate_existing_installer_readback(
                current_bytes,
                discovery,
                allowed_descriptor_sha256=allowed_existing_descriptor_sha256,
            )
            if sha256(current_bytes).digest() != existing_digest:
                raise MontageLearningInstallationError(
                    "installer readback target bytes changed"
                )
        if existing_identity is None:
            try:
                os.link(temporary, target, follow_symlinks=False)
            except FileExistsError as exc:
                raise MontageLearningInstallationError(
                    "installer readback target appeared concurrently"
                ) from exc
            try:
                temporary.unlink()
            except OSError as exc:
                try:
                    target.unlink()
                except OSError as rollback_exc:
                    raise MontageLearningInstallationError(
                        "installer readback new-target cleanup requires recovery"
                    ) from rollback_exc
                raise MontageLearningInstallationError(
                    "installer readback new-target cleanup failed"
                ) from exc
        else:
            os.replace(temporary, target)
        replaced = True
        _directory_fsync(target.parent)

        _verify_directory_identities(directories, ancestor_identities)
        _call_receipt_failure(failure_injector, "before_readback", target)
        _require_safe_regular_file(target, expected_size=len(data))
        readback = _read_stable_regular_bytes(target)
        if readback != data or sha256(readback).digest() != sha256(data).digest():
            raise MontageLearningInstallationError(
                "installer readback byte verification failed"
            )
        _capture_discovery_source_binding(discovery)
        return target
    finally:
        if not replaced:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _installer_readback_coordinates(
    discovery: InstalledBridgeDiscovery,
) -> tuple[Path, tuple[Path, ...]]:
    install_root = discovery.install_root
    if not install_root.is_absolute():
        raise MontageLearningInstallationError("install root must be absolute")
    expected_layout = BridgeLayout.production(install_root)
    if expected_layout.root != discovery.layout.root:
        raise MontageLearningInstallationError("discovery layout mismatch")
    data_root = install_root / "data"
    bridge_root = data_root / "montage-learning-bridge"
    migration_root = bridge_root / "migration"
    if (
        data_root.parent != install_root
        or bridge_root.parent != data_root
        or migration_root.parent != bridge_root
        or discovery.layout.migration != migration_root
    ):
        raise MontageLearningInstallationError("installer readback path mismatch")
    target = migration_root / INSTALLER_READBACK_FILENAME
    if target.parent != discovery.layout.migration:
        raise MontageLearningInstallationError("installer readback target escaped")
    return target, _complete_directory_chain(migration_root)


def _complete_directory_chain(path: Path) -> tuple[Path, ...]:
    if not path.is_absolute():
        raise MontageLearningInstallationError(
            "installer readback ancestor chain must be absolute"
        )
    return tuple(reversed(path.parents)) + (path,)


def _capture_discovery_source_binding(
    expected: InstalledBridgeDiscovery,
) -> InstalledBridgeDiscovery:
    descriptor_path = expected.layout.root / DESCRIPTOR_FILENAME
    owner_path = expected.layout.owner_manifest
    before = (
        _safe_receipt_identity(descriptor_path),
        _safe_receipt_identity(owner_path),
    )
    if None in before:
        raise MontageLearningInstallationError(
            "installer discovery source is unavailable"
        )
    current = discover_installed_bridge(expected.install_root)
    after = (
        _safe_receipt_identity(descriptor_path),
        _safe_receipt_identity(owner_path),
    )
    if before != after or current != expected:
        raise MontageLearningInstallationError(
            "installer discovery source identity changed"
        )
    return current


def _safe_directory_identity(path: Path) -> tuple[int, int, str]:
    if path.is_symlink():
        raise MontageLearningInstallationError(
            "installer readback ancestor must not be a symlink"
        )
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback ancestor is unavailable"
        ) from exc
    if not stat.S_ISDIR(metadata.st_mode) or _stat_is_reparse(metadata):
        raise MontageLearningInstallationError(
            "installer readback ancestor must be a safe directory"
        )
    if os.name == "nt" and not hasattr(metadata, "st_file_attributes"):
        raise MontageLearningInstallationError(
            "installer readback ancestor safety is not observable"
        )
    if metadata.st_dev < 0 or metadata.st_ino <= 0:
        raise MontageLearningInstallationError(
            "installer readback ancestor identity is unavailable"
        )
    try:
        resolved = str(path.resolve(strict=True))
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback ancestor cannot be resolved"
        ) from exc
    return metadata.st_dev, metadata.st_ino, resolved


def _verify_directory_identities(
    paths: tuple[Path, ...],
    expected: tuple[tuple[int, int, str], ...],
) -> None:
    current = tuple(_safe_directory_identity(path) for path in paths)
    if current != expected:
        raise MontageLearningInstallationError(
            "installer readback ancestor identity changed"
        )


def _safe_receipt_identity(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        metadata = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback target is unavailable"
        ) from exc
    _require_safe_regular_metadata(path, metadata)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
    )


def _require_safe_regular_file(path: Path, *, expected_size: int) -> None:
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback file is unavailable"
        ) from exc
    _require_safe_regular_metadata(path, metadata)
    if metadata.st_size != expected_size:
        raise MontageLearningInstallationError(
            "installer readback file size mismatch"
        )


def _require_safe_regular_metadata(path: Path, metadata: os.stat_result) -> None:
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or _stat_is_reparse(metadata)
    ):
        raise MontageLearningInstallationError(
            "installer readback target must be a safe regular file"
        )
    if metadata.st_nlink != 1:
        raise MontageLearningInstallationError(
            "installer readback target must not be hard linked"
        )
    if os.name == "nt" and not hasattr(metadata, "st_file_attributes"):
        raise MontageLearningInstallationError(
            "installer readback target safety is not observable"
        )


def _read_stable_regular_bytes(path: Path) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be inspected"
        ) from exc
    _require_safe_regular_metadata(path, before)
    if not 1 <= before.st_size <= _MAX_INSTALLER_READBACK_BYTES:
        raise MontageLearningInstallationError("installer readback size is invalid")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be read"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        _require_safe_regular_metadata(path, opened)
        if _regular_identity(opened) != _regular_identity(before):
            raise MontageLearningInstallationError(
                "installer readback changed before open"
            )
        chunks: list[bytes] = []
        remaining = _MAX_INSTALLER_READBACK_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError(
            "installer readback cannot be re-inspected"
        ) from exc
    _require_safe_regular_metadata(path, after)
    if (
        _regular_identity(before) != _regular_identity(after_open)
        or _regular_identity(after_open) != _regular_identity(after)
        or len(data) != after.st_size
    ):
        raise MontageLearningInstallationError("installer readback is unstable")
    return data


def _regular_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
    )


def _validate_existing_installer_readback(
    data: bytes,
    discovery: InstalledBridgeDiscovery,
    *,
    allowed_descriptor_sha256: set[str],
) -> None:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_receipt_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningInstallationError(
            "existing installer readback JSON is invalid"
        ) from exc
    expected = discovery.public_receipt()
    if type(value) is not dict or set(value) != set(expected):
        raise MontageLearningInstallationError(
            "existing installer readback fields mismatch"
        )
    for field in (
        "schema_version",
        "message_type",
        "product_id",
        "install_instance_id",
        "bridge_relative_path",
        "owner_manifest_sha256",
        "capability",
        "status",
        "connector_enabled",
        "activation_authorized",
    ):
        if value[field] != expected[field]:
            raise MontageLearningInstallationError(
                "existing installer readback ownership mismatch"
            )
    descriptor_sha256 = _require_sha(
        value["descriptor_sha256"], "descriptor_sha256"
    )
    if descriptor_sha256 not in allowed_descriptor_sha256:
        raise MontageLearningInstallationError(
            "existing installer readback descriptor transition mismatch"
        )


def _reject_duplicate_receipt_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise MontageLearningInstallationError(
                "existing installer readback has duplicate fields"
            )
        result[key] = value
    return result


def _stat_is_reparse(metadata: os.stat_result) -> bool:
    return bool(getattr(metadata, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)


def _directory_fsync(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _call_receipt_failure(
    failure_injector: ReceiptFailureInjector | None,
    phase: str,
    path: Path,
) -> None:
    if failure_injector is not None:
        failure_injector(phase, path)


def _read_descriptor(path: Path) -> BridgeInstanceDescriptor:
    try:
        snapshot = SecureAuthorityIO(
            path.parent,
            max_bytes=_MAX_DESCRIPTOR_BYTES,
            max_json_depth=2,
            max_json_nodes=32,
        ).read_json(path.name)
    except SecureAuthorityIOError:
        raise MontageLearningInstallationError(
            "descriptor secure read rejected"
        ) from None
    if not isinstance(snapshot.document, Mapping):
        raise MontageLearningInstallationError(
            "descriptor secure read rejected"
        ) from None
    value = dict(snapshot.document)
    _validate_descriptor_document(value)
    return BridgeInstanceDescriptor(
        install_instance_id=value["install_instance_id"],
        bridge_relative_path=value["bridge_relative_path"],
        installer_manifest_sha256=value["installer_manifest_sha256"],
        created_at=value["created_at"],
        updated_at=value["updated_at"],
        descriptor_sha256=value["descriptor_sha256"],
    )


def _ensure_installer_data_root(layout: BridgeLayout) -> None:
    install_root = layout.root.parent.parent
    data_root = layout.root.parent
    for path in (install_root,):
        if path.is_symlink() or not path.is_dir():
            raise MontageLearningInstallationError(
                "installer-selected root must be an existing non-symlink directory"
            )
        metadata = path.stat(follow_symlinks=False)
        if getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise MontageLearningInstallationError(
                "installer-selected root must not be a reparse point"
            )
    if data_root.exists() or data_root.is_symlink():
        if data_root.is_symlink() or not data_root.is_dir():
            raise MontageLearningInstallationError(
                "installer data root must be a non-symlink directory"
            )
        metadata = data_root.stat(follow_symlinks=False)
        if getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise MontageLearningInstallationError(
                "installer data root must not be a reparse point"
            )
    else:
        data_root.mkdir(mode=0o700)


def _validate_descriptor_document(value: object) -> None:
    expected = {
        "schema_version",
        "message_type",
        "product_id",
        "install_instance_id",
        "bridge_relative_path",
        "installer_manifest_sha256",
        "created_at",
        "updated_at",
        "descriptor_sha256",
    }
    if type(value) is not dict or set(value) != expected:
        raise MontageLearningInstallationError("descriptor fields mismatch")
    if value["schema_version"] != DESCRIPTOR_SCHEMA_VERSION:
        raise MontageLearningInstallationError("descriptor version mismatch")
    if value["message_type"] != DESCRIPTOR_MESSAGE_TYPE:
        raise MontageLearningInstallationError("descriptor type mismatch")
    if value["product_id"] != PRODUCT_ID:
        raise MontageLearningInstallationError("descriptor product mismatch")
    if (
        type(value["install_instance_id"]) is not str
        or _INSTANCE_RE.fullmatch(value["install_instance_id"]) is None
    ):
        raise MontageLearningInstallationError("install instance id is invalid")
    if value["bridge_relative_path"] != BRIDGE_RELATIVE_PATH:
        raise MontageLearningInstallationError("bridge relative path mismatch")
    _require_sha(value["installer_manifest_sha256"], "installer_manifest_sha256")
    _require_timestamp(value["created_at"], "created_at")
    _require_timestamp(value["updated_at"], "updated_at")
    _require_sha(value["descriptor_sha256"], "descriptor_sha256")
    body = dict(value)
    supplied = body.pop("descriptor_sha256")
    if sha256_json(body) != supplied:
        raise MontageLearningInstallationError("descriptor hash mismatch")


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
    _require_timestamp(value, "timestamp")
    return value


def _require_timestamp(value: object, field: str) -> None:
    if type(value) is not str or not value.endswith("Z"):
        raise MontageLearningInstallationError(f"{field} is invalid")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MontageLearningInstallationError(f"{field} is invalid") from exc


def _require_sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningInstallationError(f"{field} is invalid")
    return value


__all__ = [
    "BRIDGE_RELATIVE_PATH",
    "BridgeInstanceDescriptor",
    "INSTALLER_READBACK_FILENAME",
    "InstalledBridgeDiscovery",
    "MontageLearningInstallationError",
    "discover_installed_bridge",
    "provision_and_write_installer_readback",
    "provision_installed_bridge",
    "write_installer_readback",
]
