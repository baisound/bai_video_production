"""Installer-relative montage-learning bridge discovery and provisioning.

The active bridge is never derived from a machine-global fixed directory.  The
installer-selected application root is the only coordinate accepted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import uuid

from .atomic import AtomicJsonWriter
from .montage_learning_file_bridge import (
    BridgeLayout,
    MontageLearningFileBridgeError,
    load_bridge_owner,
    provision_bridge,
)
from .serialization import sha256_json


DESCRIPTOR_FILENAME = "bridge-instance.json"
DESCRIPTOR_MESSAGE_TYPE = "BvpMontageLearningBridgeInstance"
DESCRIPTOR_SCHEMA_VERSION = "1.0.0"
PRODUCT_ID = "BAI_VIDEO_PRODUCTION"
BRIDGE_RELATIVE_PATH = "data/montage-learning-bridge"
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_INSTANCE_RE = re.compile(r"^bvp-install-[0-9a-f]{32}$")
_MAX_DESCRIPTOR_BYTES = 64 * 1024


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


def _read_descriptor(path: Path) -> BridgeInstanceDescriptor:
    if path.is_symlink():
        raise MontageLearningInstallationError("descriptor must not be a symlink")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise MontageLearningInstallationError("descriptor is unavailable") from exc
    reparse = getattr(metadata, "st_file_attributes", 0) & 0x400
    if not stat.S_ISREG(metadata.st_mode) or reparse:
        raise MontageLearningInstallationError("descriptor must be a regular file")
    if not 1 <= metadata.st_size <= _MAX_DESCRIPTOR_BYTES:
        raise MontageLearningInstallationError("descriptor size is invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningInstallationError("descriptor JSON is invalid") from exc
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
    "InstalledBridgeDiscovery",
    "MontageLearningInstallationError",
    "discover_installed_bridge",
    "provision_installed_bridge",
]
