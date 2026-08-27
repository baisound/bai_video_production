"""TASK-058 BVP-owned montage-learning file bridge primitives.

This module owns transport paths and bytes only.  It does not admit learning,
generate a Profile, mutate a Timeline, or know the canonical store layout.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterator, Mapping

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
RECEIPT_PENDING_SCHEMA_VERSION = "1.0.0"
RECEIPT_PENDING_MESSAGE_TYPE = "BvpMontageLearningReceiptPublicationPending"
GENERIC_RECEIPT_NAMESPACE = "GENERIC_REVIEW_OBSERVATION_ONLY"
EXACT_RECEIPT_NAMESPACE = "EXACT_EVIDENCE_ONLY"
IMPORT_JOURNAL_SCHEMA_VERSION = "1.0.0"
IMPORT_JOURNAL_MESSAGE_TYPE = "BvpMontageLearningImportJournal"
IMPORT_PREPARED = "PREPARED"
IMPORT_CLAIMED = "CLAIMED"
IMPORT_QUARANTINE_PREPARED = "QUARANTINE_PREPARED"
IMPORT_QUARANTINED = "QUARANTINED"
IMPORT_RECEIPT_PUBLISHED = "RECEIPT_PUBLISHED"

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
    def processing(self) -> Path:
        return self.root / "processing"

    @property
    def quarantine(self) -> Path:
        return self.root / "quarantine"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def import_journal(self) -> Path:
        return self.state / "import-journal"

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
    handle_inheritable: bool
    document: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DeliveryClaim:
    """Strict journal-backed ownership of one delivery in processing."""

    journal_path: Path
    original_path: Path
    processing_path: Path
    quarantine_path: Path
    record_id: str
    source_sha256: str
    pre_claim_file_identity: tuple[int, int, int, int]
    ancestor_identities: Mapping[str, Mapping[str, object]]
    state: str


@dataclass(frozen=True, slots=True)
class ReceiptPublicationPaths:
    """One receipt identity and its private, crash-recovery marker."""

    receipt_path: Path
    pending_path: Path
    exact_v2: bool


def provision_bridge(
    layout: BridgeLayout,
    *,
    bridge_instance_id: str,
) -> BridgeOwner:
    """Create and revalidate the fixed BVP-owned bridge layout idempotently."""

    _require_id(bridge_instance_id, "bridge_instance_id")
    _reject_unsafe_existing_ancestors(layout.root)
    for directory in _bridge_directories(layout):
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
    for directory in _bridge_directories(layout):
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
    """Return inbox names plus restartable processing journals, once and bounded."""

    load_bridge_owner(layout)
    paths_by_name: dict[str, Path] = {}
    with os.scandir(layout.import_journal) as entries:
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if not entry.name.endswith(".import-journal.json"):
                raise MontageLearningFileBridgeError(
                    f"unknown import-journal entry: {entry.name}"
                )
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise MontageLearningFileBridgeError(
                    "import-journal entry must be a regular file"
                )
            value = _load_import_journal(Path(entry.path), layout)
            if value["state"] in {
                IMPORT_PREPARED,
                IMPORT_CLAIMED,
                IMPORT_QUARANTINE_PREPARED,
            }:
                original = layout.root / str(value["original_relative_path"])
                paths_by_name[original.name] = original
            if len(paths_by_name) > MAX_IMPORT_FILES:
                raise MontageLearningFileBridgeError("import file bound exceeded")
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
            paths_by_name.setdefault(entry.name, Path(entry.path))
            if len(paths_by_name) > MAX_IMPORT_FILES:
                raise MontageLearningFileBridgeError("import file bound exceeded")
    return tuple(paths_by_name[name] for name in sorted(paths_by_name))


def claim_delivery(path: str | Path, layout: BridgeLayout) -> DeliveryClaim:
    """Claim one exact inbox filename or resume its strict import journal."""

    owner = load_bridge_owner(layout)
    original = Path(path)
    if original.parent != layout.inbox:
        raise MontageLearningFileBridgeError("delivery must name the fixed inbox")
    match = _DELIVERY_RE.fullmatch(original.name)
    if match is None:
        raise MontageLearningFileBridgeError("delivery filename is invalid")
    journal_path = _import_journal_path(layout, original.name)
    with exclusive_file_update_lock(journal_path):
        if journal_path.exists():
            value = _load_import_journal(journal_path, layout)
            _require_journal_filename_binding(value, original.name)
        else:
            _reject_unsafe_path(original)
            source_stat = original.stat(follow_symlinks=False)
            if not _is_regular_stat(source_stat) or _stat_is_reparse(source_stat):
                raise MontageLearningFileBridgeError("delivery must be a regular file")
            processing_stat = layout.processing.stat(follow_symlinks=False)
            if source_stat.st_dev != processing_stat.st_dev:
                raise MontageLearningFileBridgeError(
                    "processing claim must remain on one volume"
                )
            processing = layout.processing / original.name
            quarantine = layout.quarantine / original.name
            if processing.exists() or processing.is_symlink():
                raise MontageLearningFileBridgeError("processing collision")
            if quarantine.exists() or quarantine.is_symlink():
                raise MontageLearningFileBridgeError("quarantine collision")
            identities = _capture_bridge_ancestor_identities(layout)
            value = _new_import_journal(
                layout,
                owner=owner,
                match=match,
                original=original,
                processing=processing,
                quarantine=quarantine,
                pre_claim_identity=_stat_identity(source_stat),
                ancestor_identities=identities,
            )
            _write_import_journal(journal_path, value, layout)
        value = _resume_claim_locked(journal_path, value, layout)
        return _claim_from_journal(journal_path, value, layout)


def quarantine_claim(claim: DeliveryClaim, layout: BridgeLayout) -> DeliveryClaim:
    """Move a claimed malformed delivery to quarantine without overwriting."""

    _require_claim_object(claim, layout)
    with exclusive_file_update_lock(claim.journal_path):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        state = value["state"]
        if state == IMPORT_QUARANTINED:
            _verify_identity_path(
                claim.quarantine_path, claim.pre_claim_file_identity, "quarantine"
            )
            return _claim_from_journal(claim.journal_path, value, layout)
        if state == IMPORT_RECEIPT_PUBLISHED:
            raise MontageLearningFileBridgeError(
                "published delivery cannot be quarantined"
            )
        if state == IMPORT_PREPARED:
            value = _resume_claim_locked(claim.journal_path, value, layout)
        if value["state"] == IMPORT_CLAIMED:
            value = _advance_import_journal(
                claim.journal_path,
                value,
                IMPORT_QUARANTINE_PREPARED,
                layout,
            )
        if value["state"] != IMPORT_QUARANTINE_PREPARED:
            raise MontageLearningFileBridgeError("import journal state cannot quarantine")
        _verify_ancestor_identities(value, layout)
        processing_exists = claim.processing_path.exists() or claim.processing_path.is_symlink()
        quarantine_exists = claim.quarantine_path.exists() or claim.quarantine_path.is_symlink()
        if processing_exists and not quarantine_exists:
            _verify_identity_path(
                claim.processing_path, claim.pre_claim_file_identity, "processing"
            )
            _atomic_rename_noreplace(claim.processing_path, claim.quarantine_path)
            _directory_fsync(layout.processing)
            _directory_fsync(layout.quarantine)
        elif processing_exists or not quarantine_exists:
            raise MontageLearningFileBridgeError(
                "quarantine rename position is ambiguous"
            )
        _verify_ancestor_identities(value, layout)
        _verify_identity_path(
            claim.quarantine_path, claim.pre_claim_file_identity, "quarantine"
        )
        value = _advance_import_journal(
            claim.journal_path, value, IMPORT_QUARANTINED, layout
        )
        return _claim_from_journal(claim.journal_path, value, layout)


def mark_claim_receipt_published(
    claim: DeliveryClaim, layout: BridgeLayout
) -> DeliveryClaim:
    """Durably retain successful import evidence without deleting source bytes."""

    _require_claim_object(claim, layout)
    with exclusive_file_update_lock(claim.journal_path):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        if value["state"] == IMPORT_RECEIPT_PUBLISHED:
            _verify_identity_path(
                claim.processing_path, claim.pre_claim_file_identity, "processing"
            )
            return _claim_from_journal(claim.journal_path, value, layout)
        if value["state"] != IMPORT_CLAIMED:
            raise MontageLearningFileBridgeError(
                "only a claimed delivery can publish a receipt"
            )
        _verify_ancestor_identities(value, layout)
        _verify_identity_path(
            claim.processing_path, claim.pre_claim_file_identity, "processing"
        )
        value = _advance_import_journal(
            claim.journal_path, value, IMPORT_RECEIPT_PUBLISHED, layout
        )
        return _claim_from_journal(claim.journal_path, value, layout)


def snapshot_delivery(claim: DeliveryClaim, layout: BridgeLayout) -> DeliverySnapshot:
    """Read only a validated claim once through a non-inheritable pinned handle."""

    _require_claim_object(claim, layout)
    with exclusive_file_update_lock(claim.journal_path):
        journal = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, journal, layout)
        if journal["state"] not in {IMPORT_CLAIMED, IMPORT_RECEIPT_PUBLISHED}:
            raise MontageLearningFileBridgeError("delivery claim is not readable")
        _verify_ancestor_identities(journal, layout)
        candidate = claim.processing_path
        _verify_identity_path(candidate, claim.pre_claim_file_identity, "processing")

        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(candidate, flags)
        try:
            os.set_inheritable(fd, False)
            handle_inheritable = os.get_inheritable(fd)
            if handle_inheritable:
                raise MontageLearningFileBridgeError(
                    "delivery handle remained inheritable"
                )
            before = os.fstat(fd)
            if not _is_regular_stat(before) or _stat_is_reparse(before):
                raise MontageLearningFileBridgeError("delivery handle is not regular")
            if _stat_identity(before) != claim.pre_claim_file_identity:
                raise MontageLearningFileBridgeError(
                    "delivery handle identity differs from claim"
                )
            if before.st_size <= 0 or before.st_size > MAX_DELIVERY_BYTES:
                raise MontageLearningFileBridgeError("delivery size is outside bound")
            digest = sha256()
            chunks: list[bytes] = []
            remaining = MAX_DELIVERY_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(128 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        before_identity = _stat_identity(before)
        if before_identity != _stat_identity(after) or len(raw) != before.st_size:
            raise MontageLearningFileBridgeError("delivery changed during pinned read")
        _verify_ancestor_identities(journal, layout)
        _verify_identity_path(candidate, before_identity, "processing")

    document = _decode_builtin_json(raw)
    match = _DELIVERY_RE.fullmatch(candidate.name)
    if match is None:
        raise MontageLearningFileBridgeError("claimed delivery filename is invalid")
    record_id = match.group("record")
    filename_digest = f"sha256:{match.group('digest')}"
    if record_id != claim.record_id or filename_digest != claim.source_sha256:
        raise MontageLearningFileBridgeError("claim filename binding mismatch")
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
        file_sha256=f"sha256:{digest.hexdigest()}",
        file_identity=before_identity,
        handle_inheritable=handle_inheritable,
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
    target = receipt_publication_paths(
        layout,
        record_id=record_id,
        source_sha256=source_sha256,
        exact_v2=exact_v2,
    ).receipt_path
    _write_new_or_identical(target, dict(receipt))
    return target


def receipt_publication_paths(
    layout: BridgeLayout,
    *,
    record_id: str,
    source_sha256: str,
    exact_v2: bool,
) -> ReceiptPublicationPaths:
    """Return the fixed public receipt and private pending paths for one identity."""

    load_bridge_owner(layout)
    _require_id(record_id, "record_id")
    if not isinstance(source_sha256, str) or _SHA_RE.fullmatch(source_sha256) is None:
        raise MontageLearningFileBridgeError("source_sha256 is invalid")
    if type(exact_v2) is not bool:
        raise MontageLearningFileBridgeError("exact_v2 must be boolean")
    suffix = ".admission-v2.json" if exact_v2 else ".receipt.json"
    receipt_path = layout.receipts / (
        f"{record_id}--{source_sha256.removeprefix('sha256:')}{suffix}"
    )
    return ReceiptPublicationPaths(
        receipt_path=receipt_path,
        pending_path=layout.receipts / f".{receipt_path.name}.pending.json",
        exact_v2=exact_v2,
    )


@contextmanager
def receipt_identity_publisher_guard(
    layout: BridgeLayout,
    *,
    record_id: str,
    source_sha256: str,
    exact_v2: bool,
) -> Iterator[ReceiptPublicationPaths]:
    """Serialize recovery, A mutation, receipt publication, and marker cleanup."""

    paths = receipt_publication_paths(
        layout,
        record_id=record_id,
        source_sha256=source_sha256,
        exact_v2=exact_v2,
    )
    _require_safe_directory(paths.receipt_path.parent)
    with exclusive_file_update_lock(paths.receipt_path):
        yield paths


def build_receipt_publication_pending(
    paths: ReceiptPublicationPaths,
    *,
    lane: str,
    namespace: str,
    record_id: str,
    source_sha256: str,
    delivery_file_sha256: str,
    expected_revision: int,
    coordinates: Mapping[str, object],
) -> dict[str, object]:
    """Create a strict, body-free request identity before canonical mutation."""

    body: dict[str, object] = {
        "schema_version": RECEIPT_PENDING_SCHEMA_VERSION,
        "message_type": RECEIPT_PENDING_MESSAGE_TYPE,
        "lane": lane,
        "namespace": namespace,
        "record_id": record_id,
        "source_sha256": source_sha256,
        "delivery_file_sha256": delivery_file_sha256,
        "expected_revision": expected_revision,
        "coordinates": dict(coordinates),
        "output_receipt_relative_path": f"learning-receipts/{paths.receipt_path.name}",
        "directory_durability_confirmed": False,
    }
    body["request_sha256"] = sha256_json(body)
    pending = dict(body)
    pending["pending_sha256"] = sha256_json(pending)
    return _validate_receipt_publication_pending(pending, paths)


def load_published_receipt(
    paths: ReceiptPublicationPaths,
) -> dict[str, Any] | None:
    """Strictly load an already-public receipt without granting it authority."""

    _require_safe_directory(paths.receipt_path.parent)
    if not paths.receipt_path.exists():
        return None
    return _read_json_regular(paths.receipt_path, max_bytes=MAX_DELIVERY_BYTES)


def load_receipt_publication_pending(
    paths: ReceiptPublicationPaths,
) -> dict[str, object] | None:
    """Strictly load and self-hash-check the private publication marker."""

    _require_safe_directory(paths.pending_path.parent)
    if not paths.pending_path.exists():
        return None
    value = _read_json_regular(paths.pending_path, max_bytes=64 * 1024)
    return _validate_receipt_publication_pending(value, paths)


def create_pending_receipt_publication_new_or_identical(
    paths: ReceiptPublicationPaths,
    pending: Mapping[str, object],
) -> None:
    """Durably create the exact request marker, never replacing a conflicting one."""

    expected = _validate_receipt_publication_pending(pending, paths)
    expected_bytes = canonical_json_bytes(expected) + b"\n"
    if paths.pending_path.exists():
        actual = _read_regular_bytes(paths.pending_path, max_bytes=64 * 1024)
        loaded = _validate_receipt_publication_pending(
            _decode_builtin_json(actual), paths
        )
        if actual != expected_bytes or loaded != expected:
            raise MontageLearningFileBridgeError("pending receipt request conflicts")
        return
    _write_new_or_identical(paths.pending_path, expected)
    actual = _read_regular_bytes(paths.pending_path, max_bytes=64 * 1024)
    if actual != expected_bytes:
        raise MontageLearningFileBridgeError("pending receipt durable read-back mismatch")


def clear_pending_receipt_publication_exact(
    paths: ReceiptPublicationPaths,
    pending: Mapping[str, object],
) -> None:
    """Clear only the exact marker after a strict final re-read and directory fsync."""

    expected = _validate_receipt_publication_pending(pending, paths)
    expected_bytes = canonical_json_bytes(expected) + b"\n"
    actual = _read_regular_bytes(paths.pending_path, max_bytes=64 * 1024)
    current = _validate_receipt_publication_pending(
        _decode_builtin_json(actual), paths
    )
    if actual != expected_bytes or current != expected:
        raise MontageLearningFileBridgeError("pending receipt cleanup identity mismatch")
    paths.pending_path.unlink()
    _directory_fsync(paths.pending_path.parent)


def _validate_receipt_publication_pending(
    value: Mapping[str, object],
    paths: ReceiptPublicationPaths,
) -> dict[str, object]:
    if type(value) is not dict:
        raise MontageLearningFileBridgeError("pending receipt must be an object")
    expected_fields = {
        "schema_version", "message_type", "lane", "namespace", "record_id",
        "source_sha256", "delivery_file_sha256", "expected_revision", "coordinates",
        "output_receipt_relative_path", "directory_durability_confirmed",
        "request_sha256", "pending_sha256",
    }
    if set(value) != expected_fields:
        raise MontageLearningFileBridgeError("pending receipt fields mismatch")
    if (value["schema_version"] != RECEIPT_PENDING_SCHEMA_VERSION or
            value["message_type"] != RECEIPT_PENDING_MESSAGE_TYPE):
        raise MontageLearningFileBridgeError("pending receipt identity mismatch")
    lane = value["lane"]
    namespace = value["namespace"]
    if paths.exact_v2:
        if lane != "EXACT_EVIDENCE" or namespace != EXACT_RECEIPT_NAMESPACE:
            raise MontageLearningFileBridgeError("exact pending lane mismatch")
    elif lane != "GENERIC_REVIEW_OBSERVATION" or namespace != GENERIC_RECEIPT_NAMESPACE:
        raise MontageLearningFileBridgeError("generic pending lane mismatch")
    _require_id(value["record_id"], "pending record_id")
    for field in ("source_sha256", "delivery_file_sha256", "request_sha256", "pending_sha256"):
        digest = value[field]
        if not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None:
            raise MontageLearningFileBridgeError(f"pending {field} is invalid")
    expected_filename = (
        f"{value['record_id']}--{str(value['source_sha256']).removeprefix('sha256:')}"
        f"{'.admission-v2.json' if paths.exact_v2 else '.receipt.json'}"
    )
    expected_relative_path = f"learning-receipts/{expected_filename}"
    if (
        value["output_receipt_relative_path"] != expected_relative_path
        or value["output_receipt_relative_path"]
        != f"learning-receipts/{paths.receipt_path.name}"
    ):
        raise MontageLearningFileBridgeError("pending output receipt path mismatch")
    if value["directory_durability_confirmed"] is not False:
        raise MontageLearningFileBridgeError(
            "pending directory durability must remain false"
        )
    revision = value["expected_revision"]
    minimum = 1 if paths.exact_v2 else 0
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < minimum:
        raise MontageLearningFileBridgeError("pending expected_revision is invalid")
    coordinates = value["coordinates"]
    if type(coordinates) is not dict:
        raise MontageLearningFileBridgeError("pending coordinates must be an object")
    if paths.exact_v2:
        _validate_exact_pending_coordinates(coordinates, revision)
    else:
        _validate_generic_pending_coordinates(coordinates, revision)
    request_body = dict(value)
    request_sha256 = request_body.pop("request_sha256")
    request_body.pop("pending_sha256")
    if sha256_json(request_body) != request_sha256:
        raise MontageLearningFileBridgeError("pending request hash mismatch")
    pending_body = dict(value)
    pending_sha256 = pending_body.pop("pending_sha256")
    if sha256_json(pending_body) != pending_sha256:
        raise MontageLearningFileBridgeError("pending hash mismatch")
    return dict(value)


def _validate_generic_pending_coordinates(
    value: dict[str, object], expected_revision: int,
) -> None:
    if set(value) != {"expected_revision", "generic_store_id"}:
        raise MontageLearningFileBridgeError("generic pending coordinates mismatch")
    if (isinstance(value["expected_revision"], bool) or
            not isinstance(value["expected_revision"], int) or
            value["expected_revision"] != expected_revision):
        raise MontageLearningFileBridgeError("generic pending revision mismatch")
    _require_id(value["generic_store_id"], "generic_store_id")


def _validate_exact_pending_coordinates(
    value: dict[str, object], expected_revision: int,
) -> None:
    expected = {
        "staging_store_id", "expected_owner_scope_hash", "expected_staging_revision",
        "expected_staging_entry_sha256", "expected_canonical_store_commit_sha256",
        "expected_external_anchor_document_sha256",
    }
    if set(value) != expected:
        raise MontageLearningFileBridgeError("exact pending coordinates mismatch")
    _require_id(value["staging_store_id"], "staging_store_id")
    if (isinstance(value["expected_staging_revision"], bool) or
            not isinstance(value["expected_staging_revision"], int) or
            value["expected_staging_revision"] != expected_revision):
        raise MontageLearningFileBridgeError("exact pending revision mismatch")
    for field in ("expected_owner_scope_hash", "expected_staging_entry_sha256"):
        digest = value[field]
        if not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None:
            raise MontageLearningFileBridgeError(f"{field} is invalid")
    for field in (
        "expected_canonical_store_commit_sha256",
        "expected_external_anchor_document_sha256",
    ):
        digest = value[field]
        if digest is not None and (
            not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None
        ):
            raise MontageLearningFileBridgeError(f"{field} is invalid")


def _bridge_directories(layout: BridgeLayout) -> tuple[Path, ...]:
    return (
        layout.root,
        layout.inbox,
        layout.processing,
        layout.quarantine,
        layout.receipts,
        layout.preference,
        layout.state,
        layout.import_journal,
    )


def _capture_bridge_ancestor_identities(
    layout: BridgeLayout,
) -> dict[str, dict[str, object]]:
    identities: dict[str, dict[str, object]] = {}
    for directory in _bridge_directories(layout):
        _require_safe_directory(directory)
        relative = "." if directory == layout.root else directory.relative_to(layout.root).as_posix()
        stat = directory.stat(follow_symlinks=False)
        body: dict[str, object] = {
            "relative_path": relative,
            "resolved_path": str(directory.resolve(strict=True)),
            "st_dev": stat.st_dev,
            "st_ino": stat.st_ino,
        }
        body["identity_sha256"] = sha256_json(body)
        identities[relative] = body
    return identities


def _verify_ancestor_identities(
    value: Mapping[str, object], layout: BridgeLayout
) -> None:
    expected = value.get("ancestor_identities")
    if type(expected) is not dict:
        raise MontageLearningFileBridgeError("journal ancestor identities are invalid")
    current = _capture_bridge_ancestor_identities(layout)
    if current != expected:
        raise MontageLearningFileBridgeError("bridge root/ancestor identity changed")
    if value.get("root_identity") != _root_identity(layout.root):
        raise MontageLearningFileBridgeError("journal root identity changed")


def _file_identity_document(identity: tuple[int, int, int, int]) -> dict[str, int]:
    return {
        "st_dev": identity[0],
        "st_ino": identity[1],
        "st_size": identity[2],
        "st_mtime_ns": identity[3],
    }


def _identity_from_document(value: object) -> tuple[int, int, int, int]:
    if type(value) is not dict or set(value) != {
        "st_dev", "st_ino", "st_size", "st_mtime_ns"
    }:
        raise MontageLearningFileBridgeError("journal file identity fields mismatch")
    fields = tuple(value[field] for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns"))
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in fields):
        raise MontageLearningFileBridgeError("journal file identity is invalid")
    return fields  # type: ignore[return-value]


def _import_journal_path(layout: BridgeLayout, filename: str) -> Path:
    return layout.import_journal / f"{filename}.import-journal.json"


def _new_import_journal(
    layout: BridgeLayout,
    *,
    owner: BridgeOwner,
    match: re.Match[str],
    original: Path,
    processing: Path,
    quarantine: Path,
    pre_claim_identity: tuple[int, int, int, int],
    ancestor_identities: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": IMPORT_JOURNAL_SCHEMA_VERSION,
        "message_type": IMPORT_JOURNAL_MESSAGE_TYPE,
        "contract_profile": BRIDGE_CONTRACT_PROFILE,
        "bridge_instance_id": owner.bridge_instance_id,
        "record_id": match.group("record"),
        "source_sha256": f"sha256:{match.group('digest')}",
        "original_relative_path": original.relative_to(layout.root).as_posix(),
        "processing_relative_path": processing.relative_to(layout.root).as_posix(),
        "quarantine_relative_path": quarantine.relative_to(layout.root).as_posix(),
        "root_identity": owner.root_identity,
        "ancestor_identities": {
            key: dict(identity) for key, identity in ancestor_identities.items()
        },
        "pre_claim_file_identity": _file_identity_document(pre_claim_identity),
        "state": IMPORT_PREPARED,
        "states": [IMPORT_PREPARED],
        "journal_revision": 1,
    }
    body["journal_sha256"] = sha256_json(body)
    return _validate_import_journal(body, layout)


def _validate_import_journal(
    value: Mapping[str, object], layout: BridgeLayout
) -> dict[str, object]:
    if type(value) is not dict:
        raise MontageLearningFileBridgeError("import journal must be an object")
    expected_fields = {
        "schema_version", "message_type", "contract_profile", "bridge_instance_id",
        "record_id", "source_sha256", "original_relative_path",
        "processing_relative_path", "quarantine_relative_path", "root_identity",
        "ancestor_identities", "pre_claim_file_identity", "state", "states",
        "journal_revision", "journal_sha256",
    }
    if set(value) != expected_fields:
        raise MontageLearningFileBridgeError("import journal fields mismatch")
    if (
        value["schema_version"] != IMPORT_JOURNAL_SCHEMA_VERSION
        or value["message_type"] != IMPORT_JOURNAL_MESSAGE_TYPE
        or value["contract_profile"] != BRIDGE_CONTRACT_PROFILE
    ):
        raise MontageLearningFileBridgeError("import journal identity mismatch")
    owner = load_bridge_owner(layout)
    if value["bridge_instance_id"] != owner.bridge_instance_id:
        raise MontageLearningFileBridgeError("import journal owner mismatch")
    record_id = _require_id(value["record_id"], "journal record_id")
    source_sha256 = value["source_sha256"]
    if not isinstance(source_sha256, str) or _SHA_RE.fullmatch(source_sha256) is None:
        raise MontageLearningFileBridgeError("journal source_sha256 is invalid")
    filename = f"{record_id}--{source_sha256.removeprefix('sha256:')}.json"
    expected_paths = {
        "original_relative_path": f"learning-inbox/{filename}",
        "processing_relative_path": f"processing/{filename}",
        "quarantine_relative_path": f"quarantine/{filename}",
    }
    for field, expected in expected_paths.items():
        if value[field] != expected:
            raise MontageLearningFileBridgeError(f"journal {field} mismatch")
    if value["root_identity"] != owner.root_identity:
        raise MontageLearningFileBridgeError("import journal root mismatch")
    identities = value["ancestor_identities"]
    if type(identities) is not dict or set(identities) != {
        ".", "learning-inbox", "processing", "quarantine", "learning-receipts",
        "preference", "state", "state/import-journal",
    }:
        raise MontageLearningFileBridgeError("journal ancestor identity set mismatch")
    for relative, identity in identities.items():
        if type(identity) is not dict or set(identity) != {
            "relative_path", "resolved_path", "st_dev", "st_ino", "identity_sha256"
        }:
            raise MontageLearningFileBridgeError("journal ancestor identity fields mismatch")
        if identity["relative_path"] != relative:
            raise MontageLearningFileBridgeError("journal ancestor path mismatch")
        if (
            not isinstance(identity["resolved_path"], str)
            or not identity["resolved_path"]
        ):
            raise MontageLearningFileBridgeError(
                "journal ancestor resolved path is invalid"
            )
        for field in ("st_dev", "st_ino"):
            item = identity[field]
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise MontageLearningFileBridgeError("journal ancestor identity is invalid")
        supplied = identity["identity_sha256"]
        if not isinstance(supplied, str) or _SHA_RE.fullmatch(supplied) is None:
            raise MontageLearningFileBridgeError("journal ancestor hash is invalid")
        identity_body = dict(identity)
        identity_body.pop("identity_sha256")
        if sha256_json(identity_body) != supplied:
            raise MontageLearningFileBridgeError("journal ancestor hash mismatch")
    _identity_from_document(value["pre_claim_file_identity"])
    states = value["states"]
    state = value["state"]
    valid_sequences = {
        IMPORT_PREPARED: [IMPORT_PREPARED],
        IMPORT_CLAIMED: [IMPORT_PREPARED, IMPORT_CLAIMED],
        IMPORT_QUARANTINE_PREPARED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_QUARANTINE_PREPARED
        ],
        IMPORT_QUARANTINED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_QUARANTINE_PREPARED,
            IMPORT_QUARANTINED,
        ],
        IMPORT_RECEIPT_PUBLISHED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_RECEIPT_PUBLISHED
        ],
    }
    if state not in valid_sequences or states != valid_sequences[state]:
        raise MontageLearningFileBridgeError("import journal state sequence mismatch")
    if (
        isinstance(value["journal_revision"], bool)
        or not isinstance(value["journal_revision"], int)
        or value["journal_revision"] != len(states)
    ):
        raise MontageLearningFileBridgeError("import journal revision mismatch")
    supplied_hash = value["journal_sha256"]
    if not isinstance(supplied_hash, str) or _SHA_RE.fullmatch(supplied_hash) is None:
        raise MontageLearningFileBridgeError("journal_sha256 is invalid")
    body = dict(value)
    body.pop("journal_sha256")
    if sha256_json(body) != supplied_hash:
        raise MontageLearningFileBridgeError("import journal hash mismatch")
    return dict(value)


def _load_import_journal(path: Path, layout: BridgeLayout) -> dict[str, object]:
    value = _read_json_regular(path, max_bytes=128 * 1024)
    return _validate_import_journal(value, layout)


def _write_import_journal(
    path: Path, value: Mapping[str, object], layout: BridgeLayout
) -> None:
    expected = _validate_import_journal(value, layout)
    _require_safe_directory(path.parent)
    AtomicJsonWriter.write(path, expected)
    if _load_import_journal(path, layout) != expected:
        raise MontageLearningFileBridgeError("import journal read-back mismatch")


def _advance_import_journal(
    path: Path,
    current: Mapping[str, object],
    state: str,
    layout: BridgeLayout,
) -> dict[str, object]:
    value = _validate_import_journal(current, layout)
    transitions = {
        IMPORT_PREPARED: {IMPORT_CLAIMED},
        IMPORT_CLAIMED: {IMPORT_QUARANTINE_PREPARED, IMPORT_RECEIPT_PUBLISHED},
        IMPORT_QUARANTINE_PREPARED: {IMPORT_QUARANTINED},
    }
    if state not in transitions.get(str(value["state"]), set()):
        raise MontageLearningFileBridgeError("invalid import journal transition")
    value["state"] = state
    value["states"] = [*list(value["states"]), state]
    value["journal_revision"] = int(value["journal_revision"]) + 1
    value.pop("journal_sha256")
    value["journal_sha256"] = sha256_json(value)
    _write_import_journal(path, value, layout)
    return value


def _resume_claim_locked(
    journal_path: Path, value: Mapping[str, object], layout: BridgeLayout
) -> dict[str, object]:
    current = _validate_import_journal(value, layout)
    _verify_ancestor_identities(current, layout)
    identity = _identity_from_document(current["pre_claim_file_identity"])
    original = layout.root / str(current["original_relative_path"])
    processing = layout.root / str(current["processing_relative_path"])
    quarantine = layout.root / str(current["quarantine_relative_path"])
    state = current["state"]
    if state == IMPORT_PREPARED:
        original_exists = original.exists() or original.is_symlink()
        processing_exists = processing.exists() or processing.is_symlink()
        if original_exists and not processing_exists:
            _verify_identity_path(original, identity, "pre-claim")
            _atomic_rename_noreplace(original, processing)
            _directory_fsync(layout.inbox)
            _directory_fsync(layout.processing)
        elif original_exists or not processing_exists:
            raise MontageLearningFileBridgeError("claim rename position is ambiguous")
        _verify_ancestor_identities(current, layout)
        _verify_identity_path(processing, identity, "processing")
        current = _advance_import_journal(
            journal_path, current, IMPORT_CLAIMED, layout
        )
    if current["state"] == IMPORT_QUARANTINE_PREPARED:
        processing_exists = processing.exists() or processing.is_symlink()
        quarantine_exists = quarantine.exists() or quarantine.is_symlink()
        if processing_exists and not quarantine_exists:
            _verify_identity_path(processing, identity, "processing")
            _atomic_rename_noreplace(processing, quarantine)
            _directory_fsync(layout.processing)
            _directory_fsync(layout.quarantine)
        elif processing_exists or not quarantine_exists:
            raise MontageLearningFileBridgeError(
                "quarantine recovery position is ambiguous"
            )
        _verify_ancestor_identities(current, layout)
        _verify_identity_path(quarantine, identity, "quarantine")
        current = _advance_import_journal(
            journal_path, current, IMPORT_QUARANTINED, layout
        )
    if current["state"] == IMPORT_QUARANTINED:
        raise MontageLearningFileBridgeError("delivery is quarantined")
    if current["state"] not in {IMPORT_CLAIMED, IMPORT_RECEIPT_PUBLISHED}:
        raise MontageLearningFileBridgeError("import journal is not recoverable")
    _verify_identity_path(processing, identity, "processing")
    return current


def _claim_from_journal(
    journal_path: Path, value: Mapping[str, object], layout: BridgeLayout
) -> DeliveryClaim:
    current = _validate_import_journal(value, layout)
    return DeliveryClaim(
        journal_path=journal_path,
        original_path=layout.root / str(current["original_relative_path"]),
        processing_path=layout.root / str(current["processing_relative_path"]),
        quarantine_path=layout.root / str(current["quarantine_relative_path"]),
        record_id=str(current["record_id"]),
        source_sha256=str(current["source_sha256"]),
        pre_claim_file_identity=_identity_from_document(
            current["pre_claim_file_identity"]
        ),
        ancestor_identities=dict(current["ancestor_identities"]),
        state=str(current["state"]),
    )


def _require_claim_object(claim: object, layout: BridgeLayout) -> DeliveryClaim:
    if not isinstance(claim, DeliveryClaim):
        raise MontageLearningFileBridgeError(
            "snapshot requires a validated delivery claim"
        )
    expected_journal = _import_journal_path(layout, claim.original_path.name)
    if claim.journal_path != expected_journal:
        raise MontageLearningFileBridgeError("claim journal path mismatch")
    return claim


def _require_claim_matches_journal(
    claim: DeliveryClaim, value: Mapping[str, object], layout: BridgeLayout
) -> None:
    expected = _claim_from_journal(claim.journal_path, value, layout)
    if claim != expected:
        raise MontageLearningFileBridgeError("delivery claim no longer matches journal")


def _require_journal_filename_binding(
    value: Mapping[str, object], filename: str
) -> None:
    if Path(str(value["original_relative_path"])).name != filename:
        raise MontageLearningFileBridgeError("journal filename binding mismatch")


def _verify_identity_path(
    path: Path, identity: tuple[int, int, int, int], label: str
) -> None:
    _reject_unsafe_path(path)
    try:
        current = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise MontageLearningFileBridgeError(f"{label} file is missing") from exc
    if not _is_regular_stat(current) or _stat_is_reparse(current):
        raise MontageLearningFileBridgeError(f"{label} path is not regular")
    if _stat_identity(current) != identity:
        raise MontageLearningFileBridgeError(f"{label} file identity mismatch")


def _atomic_rename_noreplace(source: Path, destination: Path) -> None:
    """Use a same-volume atomic no-replace rename or fail closed."""

    _require_safe_directory(source.parent)
    _require_safe_directory(destination.parent)
    source_stat = source.stat(follow_symlinks=False)
    destination_parent_stat = destination.parent.stat(follow_symlinks=False)
    if source_stat.st_dev != destination_parent_stat.st_dev:
        raise MontageLearningFileBridgeError("atomic rename must remain on one volume")
    if destination.exists() or destination.is_symlink():
        raise MontageLearningFileBridgeError("atomic rename destination collision")
    if os.name == "nt":
        MOVEFILE_WRITE_THROUGH = 0x00000008
        ERROR_FILE_EXISTS = 80
        ERROR_ALREADY_EXISTS = 183
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            move_file_ex = kernel32.MoveFileExW
            move_file_ex.argtypes = [
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_uint,
            ]
            move_file_ex.restype = ctypes.c_int
        except (AttributeError, OSError) as exc:
            raise MontageLearningFileBridgeError(
                "atomic no-replace write-through rename is unavailable"
            ) from exc
        ctypes.set_last_error(0)
        if not move_file_ex(str(source), str(destination), MOVEFILE_WRITE_THROUGH):
            error_number = ctypes.get_last_error()
            if error_number in {ERROR_FILE_EXISTS, ERROR_ALREADY_EXISTS}:
                raise MontageLearningFileBridgeError(
                    "atomic rename destination collision"
                )
            raise MontageLearningFileBridgeError(
                "atomic no-replace write-through rename failed: "
                f"winerror {error_number}"
            )
        return
    if os.name == "posix":
        import ctypes
        import errno

        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise MontageLearningFileBridgeError(
                "atomic no-replace rename is unavailable"
            )
        renameat2.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(source),
            -100,
            os.fsencode(destination),
            1,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number == errno.EEXIST:
                raise MontageLearningFileBridgeError(
                    "atomic rename destination collision"
                )
            raise MontageLearningFileBridgeError(
                f"atomic no-replace rename failed: errno {error_number}"
            )
        return
    raise MontageLearningFileBridgeError("atomic no-replace rename is unsupported")


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
    if os.name == "nt":
        # MoveFileExW WRITE_THROUGH owns rename durability on Windows. File-write
        # durability remains the responsibility of AtomicJsonWriter.
        return
    if os.name != "posix":
        raise MontageLearningFileBridgeError(
            "directory durability is unsupported on this platform"
        )
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise MontageLearningFileBridgeError(
            f"directory durability failed for {path}"
        ) from exc


__all__ = [
    "BRIDGE_CONTRACT_PROFILE",
    "BridgeLayout",
    "BridgeOwner",
    "DeliveryClaim",
    "DeliverySnapshot",
    "EXACT_RECEIPT_NAMESPACE",
    "GENERIC_RECEIPT_NAMESPACE",
    "MAX_DELIVERY_BYTES",
    "MAX_IMPORT_FILES",
    "MontageLearningFileBridgeError",
    "PRODUCTION_BRIDGE_ROOT",
    "ReceiptPublicationPaths",
    "build_receipt_publication_pending",
    "claim_delivery",
    "clear_pending_receipt_publication_exact",
    "create_pending_receipt_publication_new_or_identical",
    "list_delivery_paths",
    "load_bridge_owner",
    "load_published_receipt",
    "load_receipt_publication_pending",
    "mark_claim_receipt_published",
    "provision_bridge",
    "publish_current_profile",
    "publish_receipt_new_or_identical",
    "quarantine_claim",
    "receipt_identity_publisher_guard",
    "receipt_publication_paths",
    "snapshot_delivery",
]
