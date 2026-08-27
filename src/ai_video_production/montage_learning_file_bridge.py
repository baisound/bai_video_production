"""TASK-058 BVP-owned montage-learning file bridge primitives.

This module owns transport paths and bytes only.  It does not admit learning,
generate a Profile, mutate a Timeline, or know the canonical store layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .serialization import canonical_json_bytes, sha256_json


PRODUCTION_BRIDGE_ROOT = Path(
    r"C:\ProgramData\BAI Video Production\montage-learning-bridge"
)
BRIDGE_CONTRACT_PROFILE = "bvp-task029-file-bridge-v1"
OWNER_MANIFEST_TYPE = "BvpMontageLearningBridgeOwnerManifest"
OWNER_MANIFEST_VERSION = "1.0.0"
MAX_DELIVERY_BYTES = 4 * 1024 * 1024
MAX_IMPORT_FILES = 256

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DELIVERY_RE = re.compile(
    r"^(?P<record>[A-Za-z0-9][A-Za-z0-9._-]{0,191})--(?P<digest>[0-9a-f]{64})\.json$"
)
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WINDOWS_REPARSE_POINT = 0x400


class MontageLearningFileBridgeError(ValueError):
    """Raised when bridge path, identity, bytes, or publication is unsafe."""


@dataclass(frozen=True, slots=True)
class BridgeLayout:
    root: Path
    production_path: bool

    @classmethod
    def production(cls) -> "BridgeLayout":
        return cls(PRODUCTION_BRIDGE_ROOT, True)

    @classmethod
    def for_isolated_test(cls, root: str | Path) -> "BridgeLayout":
        candidate = Path(root)
        if not candidate.is_absolute():
            raise MontageLearningFileBridgeError("isolated root must be absolute")
        if _same_path(candidate, PRODUCTION_BRIDGE_ROOT):
            raise MontageLearningFileBridgeError(
                "isolated layout cannot target the production bridge root"
            )
        return cls(candidate, False)

    def __post_init__(self) -> None:
        if self.production_path and not _same_path(self.root, PRODUCTION_BRIDGE_ROOT):
            raise MontageLearningFileBridgeError(
                "production layout root is fixed and cannot be overridden"
            )

    @property
    def inbox(self) -> Path:
        return self.root / "learning-inbox"

    @property
    def receipts(self) -> Path:
        return self.root / "learning-receipts"

    @property
    def preference(self) -> Path:
        return self.root / "preference"

    @property
    def current_profile(self) -> Path:
        return self.preference / "current-profile.json"

    @property
    def owner_manifest(self) -> Path:
        return self.root / "bridge-owner.json"


@dataclass(frozen=True, slots=True)
class BridgeOwner:
    bridge_instance_id: str
    root_identity: str
    production_path: bool
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class DeliverySnapshot:
    path: Path
    record_id: str
    source_sha256: str
    file_sha256: str
    file_identity: tuple[int, int, int, int]
    document: dict[str, Any]


def provision_bridge(
    layout: BridgeLayout,
    *,
    bridge_instance_id: str,
) -> BridgeOwner:
    """Create and revalidate the fixed BVP-owned bridge layout idempotently."""

    _require_id(bridge_instance_id, "bridge_instance_id")
    _reject_unsafe_existing_ancestors(layout.root)
    for directory in (layout.root, layout.inbox, layout.receipts, layout.preference):
        _mkdir_safe(directory)

    manifest_body = {
        "schema_version": OWNER_MANIFEST_VERSION,
        "message_type": OWNER_MANIFEST_TYPE,
        "contract_profile": BRIDGE_CONTRACT_PROFILE,
        "bridge_instance_id": bridge_instance_id,
        "root_identity": _root_identity(layout.root),
        "production_path": layout.production_path,
    }
    manifest = dict(manifest_body)
    manifest["manifest_sha256"] = sha256_json(manifest_body)
    _write_new_or_identical(layout.owner_manifest, manifest)
    return load_bridge_owner(layout)


def load_bridge_owner(layout: BridgeLayout) -> BridgeOwner:
    for directory in (layout.root, layout.inbox, layout.receipts, layout.preference):
        _require_safe_directory(directory)
    value = _read_json_regular(layout.owner_manifest, max_bytes=64 * 1024)
    expected_fields = {
        "schema_version",
        "message_type",
        "contract_profile",
        "bridge_instance_id",
        "root_identity",
        "production_path",
        "manifest_sha256",
    }
    if set(value) != expected_fields:
        raise MontageLearningFileBridgeError("owner manifest fields mismatch")
    if value["schema_version"] != OWNER_MANIFEST_VERSION:
        raise MontageLearningFileBridgeError("owner manifest version mismatch")
    if value["message_type"] != OWNER_MANIFEST_TYPE:
        raise MontageLearningFileBridgeError("owner manifest type mismatch")
    if value["contract_profile"] != BRIDGE_CONTRACT_PROFILE:
        raise MontageLearningFileBridgeError("owner manifest profile mismatch")
    bridge_instance_id = _require_id(
        value["bridge_instance_id"], "bridge_instance_id"
    )
    if type(value["production_path"]) is not bool:
        raise MontageLearningFileBridgeError("production_path must be boolean")
    if value["production_path"] is not layout.production_path:
        raise MontageLearningFileBridgeError("production_path claim mismatch")
    root_identity = _root_identity(layout.root)
    if value["root_identity"] != root_identity:
        raise MontageLearningFileBridgeError("bridge root identity mismatch")
    supplied_hash = value["manifest_sha256"]
    if not isinstance(supplied_hash, str) or _SHA_RE.fullmatch(supplied_hash) is None:
        raise MontageLearningFileBridgeError("manifest_sha256 is invalid")
    body = dict(value)
    body.pop("manifest_sha256")
    if sha256_json(body) != supplied_hash:
        raise MontageLearningFileBridgeError("owner manifest hash mismatch")
    return BridgeOwner(
        bridge_instance_id=bridge_instance_id,
        root_identity=root_identity,
        production_path=layout.production_path,
        manifest_sha256=supplied_hash,
    )


def list_delivery_paths(layout: BridgeLayout) -> tuple[Path, ...]:
    """Return a bounded deterministic list of candidate delivery files."""

    load_bridge_owner(layout)
    paths: list[Path] = []
    with os.scandir(layout.inbox) as entries:
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if _DELIVERY_RE.fullmatch(entry.name) is None:
                raise MontageLearningFileBridgeError(
                    f"unknown inbox entry: {entry.name}"
                )
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise MontageLearningFileBridgeError("inbox entry must be a regular file")
            paths.append(Path(entry.path))
            if len(paths) > MAX_IMPORT_FILES:
                raise MontageLearningFileBridgeError("inbox file bound exceeded")
    return tuple(sorted(paths, key=lambda item: item.name))


def snapshot_delivery(path: str | Path, layout: BridgeLayout) -> DeliverySnapshot:
    """Read one filename-bound delivery exactly once through a pinned handle."""

    owner = load_bridge_owner(layout)
    del owner
    candidate = Path(path)
    if candidate.parent != layout.inbox:
        raise MontageLearningFileBridgeError("delivery must be inside fixed inbox")
    match = _DELIVERY_RE.fullmatch(candidate.name)
    if match is None:
        raise MontageLearningFileBridgeError("delivery filename is invalid")
    _reject_unsafe_path(candidate)

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(candidate, flags)
    try:
        before = os.fstat(fd)
        if not _is_regular_stat(before) or _stat_is_reparse(before):
            raise MontageLearningFileBridgeError("delivery handle is not regular")
        if before.st_size <= 0 or before.st_size > MAX_DELIVERY_BYTES:
            raise MontageLearningFileBridgeError("delivery size is outside bound")
        chunks: list[bytes] = []
        remaining = MAX_DELIVERY_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(128 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    before_identity = _stat_identity(before)
    if before_identity != _stat_identity(after) or len(raw) != before.st_size:
        raise MontageLearningFileBridgeError("delivery changed during pinned read")
    _reject_unsafe_path(candidate)
    current = candidate.stat(follow_symlinks=False)
    if before_identity != _stat_identity(current):
        raise MontageLearningFileBridgeError("delivery identity changed after read")

    document = _decode_builtin_json(raw)
    record_id = match.group("record")
    filename_digest = f"sha256:{match.group('digest')}"
    if document.get("record_id") != record_id:
        raise MontageLearningFileBridgeError("filename record_id mismatch")
    message_type = document.get("message_type")
    if message_type == "BvpMontageLearningDelivery":
        source_digest = document.get("learning_sha256")
    elif message_type == "BvpMontageExactEvidenceDelivery":
        source_digest = document.get("evidence_sha256")
    else:
        raise MontageLearningFileBridgeError("unsupported delivery message_type")
    if source_digest != filename_digest:
        raise MontageLearningFileBridgeError("filename source digest mismatch")
    return DeliverySnapshot(
        path=candidate,
        record_id=record_id,
        source_sha256=filename_digest,
        file_sha256=f"sha256:{sha256(raw).hexdigest()}",
        file_identity=before_identity,
        document=document,
    )


def publish_receipt_new_or_identical(
    layout: BridgeLayout,
    *,
    record_id: str,
    source_sha256: str,
    receipt: Mapping[str, object],
    exact_v2: bool,
) -> Path:
    """Publish a validated receipt without replacing another receipt identity."""

    load_bridge_owner(layout)
    _require_id(record_id, "record_id")
    if not isinstance(source_sha256, str) or _SHA_RE.fullmatch(source_sha256) is None:
        raise MontageLearningFileBridgeError("source_sha256 is invalid")
    suffix = ".admission-v2.json" if exact_v2 else ".receipt.json"
    target = layout.receipts / (
        f"{record_id}--{source_sha256.removeprefix('sha256:')}{suffix}"
    )
    _write_new_or_identical(target, dict(receipt))
    return target


def publish_current_profile(
    layout: BridgeLayout,
    envelope: Mapping[str, object],
    *,
    expected_previous_profile_sha256: str | None,
) -> str:
    """CAS-publish an already validated envelope without transforming it."""

    load_bridge_owner(layout)
    target = layout.current_profile
    supplied = envelope.get("profile_sha256")
    if not isinstance(supplied, str) or _SHA_RE.fullmatch(supplied) is None:
        raise MontageLearningFileBridgeError("profile_sha256 is invalid")
    with exclusive_file_update_lock(target):
        if target.is_symlink():
            raise MontageLearningFileBridgeError("symlink path is forbidden")
        if target.exists():
            existing = _read_json_regular(target, max_bytes=MAX_DELIVERY_BYTES)
            current = existing.get("profile_sha256")
            if existing == dict(envelope):
                return "DUPLICATE"
            if expected_previous_profile_sha256 is None or current != expected_previous_profile_sha256:
                raise MontageLearningFileBridgeError("profile CAS expectation mismatch")
        elif expected_previous_profile_sha256 is not None:
            raise MontageLearningFileBridgeError("expected previous profile is missing")
        AtomicJsonWriter.write(target, dict(envelope))
        if _read_json_regular(target, max_bytes=MAX_DELIVERY_BYTES) != dict(envelope):
            raise MontageLearningFileBridgeError("profile durable read-back mismatch")
        return "PUBLISHED"


def _write_new_or_identical(path: Path, value: Mapping[str, object]) -> None:
    _require_safe_directory(path.parent)
    data = canonical_json_bytes(value) + b"\n"
    fd, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            existing = _read_regular_bytes(path, max_bytes=max(len(data), 64 * 1024))
            if existing != data:
                raise MontageLearningFileBridgeError("immutable publication collision")
        else:
            _directory_fsync(path.parent)
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass


def _decode_builtin_json(raw: bytes) -> dict[str, Any]:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                raise MontageLearningFileBridgeError("duplicate or invalid JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningFileBridgeError("delivery is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise MontageLearningFileBridgeError("delivery root must be an object")
    return value


def _read_json_regular(path: Path, *, max_bytes: int) -> dict[str, Any]:
    return _decode_builtin_json(_read_regular_bytes(path, max_bytes=max_bytes))


def _read_regular_bytes(path: Path, *, max_bytes: int) -> bytes:
    _reject_unsafe_path(path)
    stat = path.stat(follow_symlinks=False)
    if not _is_regular_stat(stat) or _stat_is_reparse(stat):
        raise MontageLearningFileBridgeError("path must be a regular file")
    if stat.st_size <= 0 or stat.st_size > max_bytes:
        raise MontageLearningFileBridgeError("file size is outside bound")
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) != stat.st_size:
        raise MontageLearningFileBridgeError("file read-back is unstable")
    return data


def _mkdir_safe(path: Path) -> None:
    if path.exists() or path.is_symlink():
        _require_safe_directory(path)
        return
    path.mkdir(mode=0o700)
    _require_safe_directory(path)
    _directory_fsync(path.parent)


def _require_safe_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise MontageLearningFileBridgeError("bridge path must be a directory")
    stat = path.stat(follow_symlinks=False)
    if _stat_is_reparse(stat):
        raise MontageLearningFileBridgeError("bridge directory must not be reparse")


def _reject_unsafe_existing_ancestors(path: Path) -> None:
    current = path
    existing: list[Path] = []
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for item in reversed(existing):
        _require_safe_directory(item)


def _reject_unsafe_path(path: Path) -> None:
    if path.is_symlink():
        raise MontageLearningFileBridgeError("symlink path is forbidden")
    try:
        stat = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return
    if _stat_is_reparse(stat):
        raise MontageLearningFileBridgeError("reparse path is forbidden")


def _stat_is_reparse(stat: os.stat_result) -> bool:
    return bool(getattr(stat, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)


def _is_regular_stat(stat: os.stat_result) -> bool:
    import stat as stat_module

    return stat_module.S_ISREG(stat.st_mode)


def _stat_identity(stat: os.stat_result) -> tuple[int, int, int, int]:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _root_identity(path: Path) -> str:
    stat = path.stat(follow_symlinks=False)
    body = {
        "resolved_path": str(path.resolve(strict=True)),
        "st_dev": stat.st_dev,
        "st_ino": stat.st_ino,
    }
    return sha256_json(body)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
        os.path.abspath(right)
    )


def _require_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise MontageLearningFileBridgeError(f"{field} is invalid")
    return value


def _directory_fsync(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


__all__ = [
    "BRIDGE_CONTRACT_PROFILE",
    "BridgeLayout",
    "BridgeOwner",
    "DeliverySnapshot",
    "MAX_DELIVERY_BYTES",
    "MAX_IMPORT_FILES",
    "MontageLearningFileBridgeError",
    "PRODUCTION_BRIDGE_ROOT",
    "list_delivery_paths",
    "load_bridge_owner",
    "provision_bridge",
    "publish_current_profile",
    "publish_receipt_new_or_identical",
    "snapshot_delivery",
]
