"""TASK-058 BVP-owned montage-learning file bridge primitives.

This module owns transport paths and bytes only.  It does not admit learning,
generate a Profile, mutate a Timeline, or know the canonical store layout.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Callable, Iterator, Mapping

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
IMPORT_CLASSIFIED = "CLASSIFIED"
IMPORT_STORE_PREPARED = "STORE_PREPARED"
IMPORT_STORE_COMMITTED = "STORE_COMMITTED"
IMPORT_QUARANTINE_PREPARED = "QUARANTINE_PREPARED"
IMPORT_QUARANTINED = "QUARANTINED"
IMPORT_RECEIPT_PUBLISHED = "RECEIPT_PUBLISHED"
IMPORT_COMPLETED = "COMPLETED"
PROFILE_JOURNAL_VERSION = "1.0.0"
PROFILE_JOURNAL_TYPE = "BvpMontagePreferenceProfilePromotionJournal"
PROFILE_POINTER_VERSION = "1.0.0"
PROFILE_POINTER_TYPE = "BvpMontagePreferenceProfilePointer"
PROFILE_MARKER_TYPE = "BvpMontagePreferenceProfileCommitMarker"
PROFILE_PHASES = (
    "PREPARED",
    "PAYLOAD_WRITTEN",
    "POINTER_COMMITTED",
    "VIEW_COMMITTED",
    "MARKER_COMMITTED",
    "READBACK_VERIFIED",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DELIVERY_RE = re.compile(
    r"^(?P<record>[A-Za-z0-9][A-Za-z0-9._-]{0,191})--(?P<digest>[0-9a-f]{64})\.json$"
)
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WINDOWS_REPARSE_POINT = 0x400
_IMPORTER_LOCKS_GUARD = threading.Lock()
_IMPORTER_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_IMPORTER_THREAD_STATE = threading.local()


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
        return self.root / "learning-processing"

    @property
    def quarantine(self) -> Path:
        return self.root / "learning-quarantine"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def import_journal(self) -> Path:
        return self.state / "importer-journal.json"

    @property
    def preference(self) -> Path:
        return self.root / "preference"

    @property
    def current_profile(self) -> Path:
        return self.preference / "current-profile.json"

    @property
    def profiles(self) -> Path:
        return self.preference / "profiles"

    @property
    def profile_pointer(self) -> Path:
        return self.preference / "current-profile.pointer.json"

    @property
    def profile_journal(self) -> Path:
        return self.state / "profile-promotion-journal.json"

    @property
    def profile_marker(self) -> Path:
        return self.state / "profile-promotion-commit-marker.json"

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
    correlation_path: Path
    exact_v2: bool


@contextmanager
def bridge_importer_guard(layout: BridgeLayout) -> Iterator[None]:
    """Hold one bridge-root global importer lock from scan through terminal state."""

    key = os.path.normcase(os.path.abspath(layout.import_journal))
    with _IMPORTER_LOCKS_GUARD:
        process_lock = _IMPORTER_PROCESS_LOCKS.setdefault(key, threading.RLock())
    depths = getattr(_IMPORTER_THREAD_STATE, "depths", None)
    if depths is None:
        depths = {}
        _IMPORTER_THREAD_STATE.depths = depths
    with process_lock:
        depth = int(depths.get(key, 0))
        depths[key] = depth + 1
        try:
            if depth:
                yield
            else:
                with exclusive_file_update_lock(layout.import_journal):
                    yield
        finally:
            remaining = int(depths[key]) - 1
            if remaining:
                depths[key] = remaining
            else:
                depths.pop(key, None)


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

    with bridge_importer_guard(layout):
        load_bridge_owner(layout)
        paths_by_name: dict[str, Path] = {}
        if layout.import_journal.exists():
            value = _load_import_journal(layout.import_journal, layout)
            if value["state"] in {IMPORT_COMPLETED, IMPORT_QUARANTINED}:
                _clear_terminal_import_journal(value, layout)
            else:
                original = layout.root / str(value["original_relative_path"])
                paths_by_name[original.name] = original
        with os.scandir(layout.inbox) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                if _DELIVERY_RE.fullmatch(entry.name) is None:
                    raise MontageLearningFileBridgeError(
                        f"unknown inbox entry: {entry.name}"
                    )
                if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                    raise MontageLearningFileBridgeError(
                        "inbox entry must be a regular file"
                    )
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
    with bridge_importer_guard(layout):
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
    with bridge_importer_guard(layout):
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
    with bridge_importer_guard(layout):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        if value["state"] == IMPORT_RECEIPT_PUBLISHED:
            _verify_identity_path(
                claim.processing_path, claim.pre_claim_file_identity, "processing"
            )
            return _claim_from_journal(claim.journal_path, value, layout)
        if value["state"] != IMPORT_STORE_COMMITTED:
            raise MontageLearningFileBridgeError(
                "only a store-committed delivery can publish a receipt"
            )
        _verify_ancestor_identities(value, layout)
        _verify_identity_path(
            claim.processing_path, claim.pre_claim_file_identity, "processing"
        )
        value = _advance_import_journal(
            claim.journal_path, value, IMPORT_RECEIPT_PUBLISHED, layout
        )
        return _claim_from_journal(claim.journal_path, value, layout)


def advance_claim_state(
    claim: DeliveryClaim,
    layout: BridgeLayout,
    state: str,
) -> DeliveryClaim:
    """Advance one claimed import through the closed B-to-A transaction phases."""

    if state not in {IMPORT_CLASSIFIED, IMPORT_STORE_PREPARED, IMPORT_STORE_COMMITTED}:
        raise MontageLearningFileBridgeError("requested import phase is not public")
    _require_claim_object(claim, layout)
    with bridge_importer_guard(layout):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        value = _advance_import_journal(claim.journal_path, value, state, layout)
        return _claim_from_journal(claim.journal_path, value, layout)


def complete_claim(claim: DeliveryClaim, layout: BridgeLayout) -> None:
    """Durably close and remove only the exact successful single-active journal."""

    _require_claim_object(claim, layout)
    with bridge_importer_guard(layout):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        if value["state"] == IMPORT_RECEIPT_PUBLISHED:
            value = _advance_import_journal(
                claim.journal_path, value, IMPORT_COMPLETED, layout
            )
        if value["state"] != IMPORT_COMPLETED:
            raise MontageLearningFileBridgeError(
                "only a receipt-published import can complete"
            )
        _clear_terminal_import_journal(value, layout)


def complete_quarantined_claim(claim: DeliveryClaim, layout: BridgeLayout) -> None:
    """Read back and clear only the exact terminal quarantine journal."""

    _require_claim_object(claim, layout)
    with bridge_importer_guard(layout):
        value = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, value, layout)
        if value["state"] != IMPORT_QUARANTINED:
            raise MontageLearningFileBridgeError(
                "only a quarantined import can clear its journal"
            )
        _clear_terminal_import_journal(value, layout)


def snapshot_delivery(claim: DeliveryClaim, layout: BridgeLayout) -> DeliverySnapshot:
    """Read only a validated claim once through a non-inheritable pinned handle."""

    _require_claim_object(claim, layout)
    with bridge_importer_guard(layout):
        journal = _load_import_journal(claim.journal_path, layout)
        _require_claim_matches_journal(claim, journal, layout)
        if journal["state"] not in {
            IMPORT_CLAIMED,
            IMPORT_CLASSIFIED,
            IMPORT_STORE_PREPARED,
            IMPORT_STORE_COMMITTED,
            IMPORT_RECEIPT_PUBLISHED,
        }:
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
        correlation_path=layout.receipts / f".{receipt_path.name}.correlation.json",
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


def build_generic_receipt_correlation(
    paths: ReceiptPublicationPaths,
    *,
    record_id: str,
    source_sha256: str,
    generic_store_id: str,
    store_revision: int,
    canonical_commit_sha256: str,
    internal_receipt_self_hash: str,
    product_project_manifest_revision: int,
    product_project_manifest_sha256: str,
    child_binding_sha256: str,
    ledger_head_sha256: str,
    public_receipt_sha256: str,
) -> dict[str, object]:
    """Build the permanent body-free authority correlation for a public v1 receipt."""

    if paths.exact_v2:
        raise MontageLearningFileBridgeError(
            "generic correlation cannot target an exact receipt"
        )
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningGenericReceiptCorrelation",
        "namespace": GENERIC_RECEIPT_NAMESPACE,
        "store_kind": "REVIEW_OBSERVATION",
        "record_id": record_id,
        "source_sha256": source_sha256,
        "generic_store_id": generic_store_id,
        "store_revision": store_revision,
        "canonical_commit_sha256": canonical_commit_sha256,
        "internal_receipt_self_hash": internal_receipt_self_hash,
        "product_project_manifest_revision": product_project_manifest_revision,
        "product_project_manifest_sha256": product_project_manifest_sha256,
        "child_binding_sha256": child_binding_sha256,
        "ledger_head_sha256": ledger_head_sha256,
        "public_receipt_sha256": public_receipt_sha256,
        "learning_adopted": False,
        "profile_promoted": False,
        "timeline_mutated": False,
    }
    body["correlation_self_hash"] = sha256_json(body)
    return _validate_generic_receipt_correlation(body, paths)


def publish_generic_receipt_correlation_new_or_identical(
    paths: ReceiptPublicationPaths,
    correlation: Mapping[str, object],
) -> None:
    expected = _validate_generic_receipt_correlation(correlation, paths)
    _write_new_or_identical(paths.correlation_path, expected)
    actual = _read_json_regular(paths.correlation_path, max_bytes=64 * 1024)
    if _validate_generic_receipt_correlation(actual, paths) != expected:
        raise MontageLearningFileBridgeError(
            "generic receipt correlation read-back mismatch"
        )


def load_generic_receipt_correlation(
    paths: ReceiptPublicationPaths,
) -> dict[str, object] | None:
    if paths.exact_v2:
        raise MontageLearningFileBridgeError(
            "generic correlation cannot target an exact receipt"
        )
    if not paths.correlation_path.exists():
        return None
    value = _read_json_regular(paths.correlation_path, max_bytes=64 * 1024)
    return _validate_generic_receipt_correlation(value, paths)


def _validate_generic_receipt_correlation(
    value: Mapping[str, object],
    paths: ReceiptPublicationPaths,
) -> dict[str, object]:
    expected_fields = {
        "schema_version", "message_type", "namespace", "store_kind",
        "record_id", "source_sha256", "generic_store_id", "store_revision",
        "canonical_commit_sha256", "internal_receipt_self_hash",
        "product_project_manifest_revision", "product_project_manifest_sha256",
        "child_binding_sha256", "ledger_head_sha256", "public_receipt_sha256",
        "learning_adopted", "profile_promoted", "timeline_mutated",
        "correlation_self_hash",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise MontageLearningFileBridgeError(
            "generic receipt correlation fields mismatch"
        )
    if (
        value["schema_version"] != "1.0.0"
        or value["message_type"] != "BvpMontageLearningGenericReceiptCorrelation"
        or value["namespace"] != GENERIC_RECEIPT_NAMESPACE
        or value["store_kind"] != "REVIEW_OBSERVATION"
    ):
        raise MontageLearningFileBridgeError(
            "generic receipt correlation identity mismatch"
        )
    _require_id(value["record_id"], "correlation record_id")
    _require_id(value["generic_store_id"], "correlation generic_store_id")
    for field in (
        "source_sha256", "canonical_commit_sha256",
        "internal_receipt_self_hash", "product_project_manifest_sha256",
        "child_binding_sha256", "ledger_head_sha256",
        "public_receipt_sha256", "correlation_self_hash",
    ):
        if not isinstance(value[field], str) or _SHA_RE.fullmatch(value[field]) is None:
            raise MontageLearningFileBridgeError(
                f"generic receipt correlation {field} is invalid"
            )
    for field in ("store_revision", "product_project_manifest_revision"):
        item = value[field]
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise MontageLearningFileBridgeError(
                f"generic receipt correlation {field} is invalid"
            )
    for field in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if value[field] is not False:
            raise MontageLearningFileBridgeError(
                f"generic receipt correlation {field} must remain false"
            )
    expected_name = (
        f"{value['record_id']}--{str(value['source_sha256']).removeprefix('sha256:')}"
        ".receipt.json"
    )
    if paths.receipt_path.name != expected_name:
        raise MontageLearningFileBridgeError(
            "generic receipt correlation path mismatch"
        )
    body = dict(value)
    supplied = body.pop("correlation_self_hash")
    if sha256_json(body) != supplied:
        raise MontageLearningFileBridgeError(
            "generic receipt correlation hash mismatch"
        )
    return dict(value)


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
        layout.profiles,
        layout.state,
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
    if _DELIVERY_RE.fullmatch(filename) is None:
        raise MontageLearningFileBridgeError("import journal filename is invalid")
    return layout.import_journal


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
        "operation_id": sha256_json(
            {
                "domain": "BVP_MONTAGE_LEARNING_IMPORT_OPERATION_V1",
                "bridge_instance_id": owner.bridge_instance_id,
                "record_id": match.group("record"),
                "source_sha256": f"sha256:{match.group('digest')}",
                "root_identity": owner.root_identity,
                "pre_claim_file_identity": _file_identity_document(pre_claim_identity),
            }
        ),
        "state": IMPORT_PREPARED,
        "states": [IMPORT_PREPARED],
        "journal_revision": 1,
        "previous_journal_sha256": None,
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
        "ancestor_identities", "pre_claim_file_identity", "operation_id", "state",
        "states", "journal_revision", "previous_journal_sha256", "journal_sha256",
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
        "processing_relative_path": f"learning-processing/{filename}",
        "quarantine_relative_path": f"learning-quarantine/{filename}",
    }
    for field, expected in expected_paths.items():
        if value[field] != expected:
            raise MontageLearningFileBridgeError(f"journal {field} mismatch")
    if value["root_identity"] != owner.root_identity:
        raise MontageLearningFileBridgeError("import journal root mismatch")
    identities = value["ancestor_identities"]
    if type(identities) is not dict or set(identities) != {
        ".", "learning-inbox", "learning-processing", "learning-quarantine",
        "learning-receipts", "preference", "preference/profiles", "state",
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
    operation_id = value["operation_id"]
    if not isinstance(operation_id, str) or _SHA_RE.fullmatch(operation_id) is None:
        raise MontageLearningFileBridgeError("journal operation_id is invalid")
    states = value["states"]
    state = value["state"]
    valid_sequences = {
        IMPORT_PREPARED: [IMPORT_PREPARED],
        IMPORT_CLAIMED: [IMPORT_PREPARED, IMPORT_CLAIMED],
        IMPORT_CLASSIFIED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_CLASSIFIED,
        ],
        IMPORT_STORE_PREPARED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_CLASSIFIED,
            IMPORT_STORE_PREPARED,
        ],
        IMPORT_STORE_COMMITTED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_CLASSIFIED,
            IMPORT_STORE_PREPARED, IMPORT_STORE_COMMITTED,
        ],
        IMPORT_QUARANTINE_PREPARED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_QUARANTINE_PREPARED
        ],
        IMPORT_QUARANTINED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_QUARANTINE_PREPARED,
            IMPORT_QUARANTINED,
        ],
        IMPORT_RECEIPT_PUBLISHED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_CLASSIFIED,
            IMPORT_STORE_PREPARED, IMPORT_STORE_COMMITTED,
            IMPORT_RECEIPT_PUBLISHED,
        ],
        IMPORT_COMPLETED: [
            IMPORT_PREPARED, IMPORT_CLAIMED, IMPORT_CLASSIFIED,
            IMPORT_STORE_PREPARED, IMPORT_STORE_COMMITTED,
            IMPORT_RECEIPT_PUBLISHED, IMPORT_COMPLETED,
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
    previous = value["previous_journal_sha256"]
    if len(states) == 1:
        if previous is not None:
            raise MontageLearningFileBridgeError(
                "initial import journal previous hash must be null"
            )
    elif not isinstance(previous, str) or _SHA_RE.fullmatch(previous) is None:
        raise MontageLearningFileBridgeError(
            "import journal previous hash is invalid"
        )
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
        IMPORT_CLAIMED: {IMPORT_CLASSIFIED, IMPORT_QUARANTINE_PREPARED},
        IMPORT_CLASSIFIED: {IMPORT_STORE_PREPARED},
        IMPORT_STORE_PREPARED: {IMPORT_STORE_COMMITTED},
        IMPORT_STORE_COMMITTED: {IMPORT_RECEIPT_PUBLISHED},
        IMPORT_RECEIPT_PUBLISHED: {IMPORT_COMPLETED},
        IMPORT_QUARANTINE_PREPARED: {IMPORT_QUARANTINED},
    }
    if state not in transitions.get(str(value["state"]), set()):
        raise MontageLearningFileBridgeError("invalid import journal transition")
    on_disk = _load_import_journal(path, layout)
    if on_disk["journal_sha256"] != value["journal_sha256"]:
        raise MontageLearningFileBridgeError("import journal CAS is stale")
    value["previous_journal_sha256"] = value["journal_sha256"]
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
    if current["state"] not in {
        IMPORT_CLAIMED, IMPORT_CLASSIFIED, IMPORT_STORE_PREPARED,
        IMPORT_STORE_COMMITTED, IMPORT_RECEIPT_PUBLISHED,
    }:
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


def _clear_terminal_import_journal(
    value: Mapping[str, object], layout: BridgeLayout
) -> None:
    current = _validate_import_journal(value, layout)
    state = current["state"]
    identity = _identity_from_document(current["pre_claim_file_identity"])
    if state == IMPORT_COMPLETED:
        _verify_identity_path(
            layout.root / str(current["processing_relative_path"]),
            identity,
            "completed processing",
        )
    elif state == IMPORT_QUARANTINED:
        _verify_identity_path(
            layout.root / str(current["quarantine_relative_path"]),
            identity,
            "terminal quarantine",
        )
    else:
        raise MontageLearningFileBridgeError("import journal is not terminal")
    on_disk = _load_import_journal(layout.import_journal, layout)
    if on_disk != current:
        raise MontageLearningFileBridgeError("terminal import journal changed")
    layout.import_journal.unlink()
    _directory_fsync(layout.state)


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
    failure_hook: Callable[[str, Path], None] | None = None,
) -> str:
    """Durably promote one prevalidated envelope through immutable object + pointer."""

    load_bridge_owner(layout)
    value = _exact_json_snapshot(envelope, path="$profile", max_depth=16)
    coordinates = _profile_coordinates(value, layout)
    with exclusive_file_update_lock(layout.profile_journal):
        if layout.profile_journal.exists():
            pending = _validate_profile_journal(
                _read_json_regular(layout.profile_journal, max_bytes=128 * 1024),
                layout,
            )
            if pending["state"] == "PREPARED":
                if any(
                    pending[field] != coordinates[field]
                    for field in (
                        "profile_id", "profile_version", "profile_sha256",
                        "payload_relative_path", "payload_document_sha256",
                    )
                ):
                    raise MontageLearningFileBridgeError(
                        "prepared profile transaction coordinates mismatch"
                    )
                _write_profile_payload_and_recover(
                    layout, pending, value, failure_hook=failure_hook
                )
                return "PUBLISHED"
            _recover_profile_promotion_locked(layout, failure_hook=failure_hook)
        current_pointer = _load_profile_pointer(layout)
        if current_pointer is not None:
            current_sha = str(current_pointer["profile_sha256"])
            if all(
                current_pointer[field] == coordinates[field]
                for field in ("profile_id", "profile_version", "profile_sha256")
            ):
                _verify_profile_publication(layout, current_pointer)
                if _read_json_regular(
                    layout.current_profile, max_bytes=MAX_DELIVERY_BYTES
                ) != value:
                    raise MontageLearningFileBridgeError(
                        "duplicate profile bytes do not match current view"
                    )
                return "DUPLICATE"
            if (
                expected_previous_profile_sha256 is None
                or current_sha != expected_previous_profile_sha256
            ):
                raise MontageLearningFileBridgeError(
                    "profile CAS expectation mismatch"
                )
            _require_profile_version_advance(
                current_pointer["profile_version"], coordinates["profile_version"]
            )
        elif expected_previous_profile_sha256 is not None:
            raise MontageLearningFileBridgeError(
                "expected previous profile is missing"
            )

        journal = _new_profile_journal(
            layout,
            coordinates,
            previous_pointer=current_pointer,
        )
        AtomicJsonWriter.write(layout.profile_journal, journal)
        _require_profile_journal_exact(layout, journal)
        _call_profile_failure(failure_hook, "after_profile_prepared", layout.profile_journal)
        _write_profile_payload_and_recover(
            layout, journal, value, failure_hook=failure_hook
        )
        return "PUBLISHED"


def recover_current_profile(
    layout: BridgeLayout,
    *,
    failure_hook: Callable[[str, Path], None] | None = None,
) -> dict[str, object] | None:
    """Recover one fixed Profile promotion journal and return the trusted pointer."""

    load_bridge_owner(layout)
    with exclusive_file_update_lock(layout.profile_journal):
        if not layout.profile_journal.exists():
            pointer = _load_profile_pointer(layout)
            if pointer is not None:
                _verify_profile_publication(layout, pointer)
            return pointer
        return _recover_profile_promotion_locked(layout, failure_hook=failure_hook)


def _profile_coordinates(
    envelope: Mapping[str, object], layout: BridgeLayout
) -> dict[str, object]:
    profile_id = _require_id(envelope.get("profile_id"), "profile_id")
    version = envelope.get("profile_version")
    segment = _profile_version_segment(version)
    supplied = envelope.get("profile_sha256")
    if type(supplied) is not str or _SHA_RE.fullmatch(supplied) is None:
        raise MontageLearningFileBridgeError("profile_sha256 is invalid")
    payload_bytes = canonical_json_bytes(dict(envelope)) + b"\n"
    payload_document_sha256 = f"sha256:{sha256(payload_bytes).hexdigest()}"
    payload_relative_path = (
        Path("preference")
        / "profiles"
        / profile_id
        / f"{segment}--{supplied.removeprefix('sha256:')}.json"
    ).as_posix()
    payload_path = layout.root / payload_relative_path
    if payload_path.parent.parent != layout.profiles:
        raise MontageLearningFileBridgeError("profile payload path escaped layout")
    return {
        "profile_id": profile_id,
        "profile_version": version,
        "profile_sha256": supplied,
        "payload_relative_path": payload_relative_path,
        "payload_document_sha256": payload_document_sha256,
    }


def _profile_version_segment(value: object) -> str:
    if type(value) is int and value >= 0:
        return str(value)
    if type(value) is str and _ID_RE.fullmatch(value) is not None:
        return value
    raise MontageLearningFileBridgeError("profile_version is not path-safe")


def _require_profile_version_advance(current: object, proposed: object) -> None:
    if type(current) is int and type(proposed) is int and proposed > current:
        return
    raise MontageLearningFileBridgeError("profile version is stale or incomparable")


def _new_profile_journal(
    layout: BridgeLayout,
    coordinates: Mapping[str, object],
    *,
    previous_pointer: Mapping[str, object] | None,
) -> dict[str, object]:
    owner = load_bridge_owner(layout)
    promoted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pointer_revision = (
        1 if previous_pointer is None else int(previous_pointer["pointer_revision"]) + 1
    )
    previous_pointer_sha256 = (
        None if previous_pointer is None else previous_pointer["pointer_self_hash"]
    )
    operation_id = sha256_json(
        {
            "domain": "BVP_MONTAGE_PROFILE_PROMOTION_OPERATION_V1",
            "bridge_instance_id": owner.bridge_instance_id,
            "root_identity": owner.root_identity,
            **dict(coordinates),
            "pointer_revision": pointer_revision,
            "previous_pointer_sha256": previous_pointer_sha256,
        }
    )
    body: dict[str, object] = {
        "schema_version": PROFILE_JOURNAL_VERSION,
        "message_type": PROFILE_JOURNAL_TYPE,
        "operation_id": operation_id,
        "bridge_instance_id": owner.bridge_instance_id,
        "root_identity": owner.root_identity,
        **dict(coordinates),
        "pointer_revision": pointer_revision,
        "previous_pointer_sha256": previous_pointer_sha256,
        "promoted_at": promoted_at,
        "state": PROFILE_PHASES[0],
        "states": [PROFILE_PHASES[0]],
        "journal_revision": 1,
        "previous_journal_sha256": None,
    }
    body["journal_sha256"] = sha256_json(body)
    return _validate_profile_journal(body, layout)


def _validate_profile_journal(
    value: Mapping[str, object], layout: BridgeLayout
) -> dict[str, object]:
    expected = {
        "schema_version", "message_type", "operation_id", "bridge_instance_id",
        "root_identity", "profile_id", "profile_version", "profile_sha256",
        "payload_relative_path", "payload_document_sha256", "pointer_revision",
        "previous_pointer_sha256", "promoted_at", "state", "states",
        "journal_revision", "previous_journal_sha256", "journal_sha256",
    }
    if type(value) is not dict or set(value) != expected:
        raise MontageLearningFileBridgeError("profile journal fields mismatch")
    owner = load_bridge_owner(layout)
    if (
        value["schema_version"] != PROFILE_JOURNAL_VERSION
        or value["message_type"] != PROFILE_JOURNAL_TYPE
        or value["bridge_instance_id"] != owner.bridge_instance_id
        or value["root_identity"] != owner.root_identity
    ):
        raise MontageLearningFileBridgeError("profile journal identity mismatch")
    profile_id = _require_id(value["profile_id"], "profile journal profile_id")
    version_segment = _profile_version_segment(value["profile_version"])
    if type(value["profile_sha256"]) is not str or _SHA_RE.fullmatch(
        value["profile_sha256"]
    ) is None:
        raise MontageLearningFileBridgeError("profile journal digest is invalid")
    expected_relative = (
        Path("preference") / "profiles" / profile_id
        / f"{version_segment}--{str(value['profile_sha256']).removeprefix('sha256:')}.json"
    ).as_posix()
    if value["payload_relative_path"] != expected_relative:
        raise MontageLearningFileBridgeError("profile journal payload path mismatch")
    if type(value["payload_document_sha256"]) is not str or _SHA_RE.fullmatch(
        value["payload_document_sha256"]
    ) is None:
        raise MontageLearningFileBridgeError("profile journal payload hash is invalid")
    if value["state"] != "PREPARED":
        coordinates = _profile_coordinates(
            _read_json_regular(
                layout.root / str(value["payload_relative_path"]),
                max_bytes=MAX_DELIVERY_BYTES,
            ),
            layout,
        )
        for field in (
            "profile_id", "profile_version", "profile_sha256",
            "payload_relative_path", "payload_document_sha256",
        ):
            if coordinates[field] != value[field]:
                raise MontageLearningFileBridgeError(
                    "profile journal coordinates mismatch"
                )
    revision = value["pointer_revision"]
    if type(revision) is not int or revision <= 0:
        raise MontageLearningFileBridgeError("profile pointer revision is invalid")
    for field in (
        "operation_id", "profile_sha256", "payload_document_sha256",
        "previous_pointer_sha256", "previous_journal_sha256", "journal_sha256",
    ):
        candidate = value[field]
        if candidate is not None and (
            type(candidate) is not str or _SHA_RE.fullmatch(candidate) is None
        ):
            raise MontageLearningFileBridgeError(f"profile journal {field} is invalid")
    states = value["states"]
    state = value["state"]
    journal_revision = value["journal_revision"]
    if (
        type(states) is not list
        or not states
        or states != list(PROFILE_PHASES[: len(states)])
        or state != states[-1]
        or type(journal_revision) is not int
        or journal_revision != len(states)
    ):
        raise MontageLearningFileBridgeError("profile journal phase chain mismatch")
    static = {
        key: item for key, item in value.items()
        if key not in {
            "state", "states", "journal_revision", "previous_journal_sha256",
            "journal_sha256",
        }
    }
    expected_document: dict[str, object] = {
        **static,
        "state": PROFILE_PHASES[0],
        "states": [PROFILE_PHASES[0]],
        "journal_revision": 1,
        "previous_journal_sha256": None,
    }
    expected_document["journal_sha256"] = sha256_json(expected_document)
    for phase in PROFILE_PHASES[1 : len(states)]:
        previous_hash = expected_document["journal_sha256"]
        expected_document["state"] = phase
        expected_document["states"] = [*expected_document["states"], phase]
        expected_document["journal_revision"] = int(
            expected_document["journal_revision"]
        ) + 1
        expected_document["previous_journal_sha256"] = previous_hash
        expected_document.pop("journal_sha256")
        expected_document["journal_sha256"] = sha256_json(expected_document)
    if expected_document != dict(value):
        raise MontageLearningFileBridgeError("profile journal hash chain mismatch")
    return dict(value)


def _require_profile_journal_exact(
    layout: BridgeLayout, expected: Mapping[str, object]
) -> None:
    actual = _read_json_regular(layout.profile_journal, max_bytes=128 * 1024)
    if _validate_profile_journal(actual, layout) != dict(expected):
        raise MontageLearningFileBridgeError("profile journal durable read-back mismatch")


def _advance_profile_journal(
    layout: BridgeLayout, current: Mapping[str, object], state: str
) -> dict[str, object]:
    value = _validate_profile_journal(current, layout)
    current_index = PROFILE_PHASES.index(str(value["state"]))
    if current_index + 1 >= len(PROFILE_PHASES) or PROFILE_PHASES[current_index + 1] != state:
        raise MontageLearningFileBridgeError("invalid profile journal transition")
    previous = value["journal_sha256"]
    value["state"] = state
    value["states"] = [*value["states"], state]
    value["journal_revision"] = int(value["journal_revision"]) + 1
    value["previous_journal_sha256"] = previous
    value.pop("journal_sha256")
    value["journal_sha256"] = sha256_json(value)
    AtomicJsonWriter.write(layout.profile_journal, value)
    _require_profile_journal_exact(layout, value)
    return value


def _profile_pointer_from_journal(journal: Mapping[str, object]) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": PROFILE_POINTER_VERSION,
        "message_type": PROFILE_POINTER_TYPE,
        "operation_id": journal["operation_id"],
        "profile_id": journal["profile_id"],
        "profile_version": journal["profile_version"],
        "profile_sha256": journal["profile_sha256"],
        "payload_relative_path": journal["payload_relative_path"],
        "payload_document_sha256": journal["payload_document_sha256"],
        "pointer_revision": journal["pointer_revision"],
        "previous_pointer_sha256": journal["previous_pointer_sha256"],
        "promoted_at": journal["promoted_at"],
    }
    body["pointer_self_hash"] = sha256_json(body)
    return body


def _profile_marker_from_journal(
    journal: Mapping[str, object], pointer: Mapping[str, object]
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": PROFILE_POINTER_VERSION,
        "message_type": PROFILE_MARKER_TYPE,
        "operation_id": journal["operation_id"],
        "profile_id": journal["profile_id"],
        "profile_sha256": journal["profile_sha256"],
        "payload_document_sha256": journal["payload_document_sha256"],
        "pointer_revision": journal["pointer_revision"],
        "pointer_self_hash": pointer["pointer_self_hash"],
        "promoted_at": journal["promoted_at"],
        "advisory_only": True,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
    }
    body["marker_self_hash"] = sha256_json(body)
    return body


def _load_profile_pointer(layout: BridgeLayout) -> dict[str, object] | None:
    if not layout.profile_pointer.exists():
        return None
    value = _read_json_regular(layout.profile_pointer, max_bytes=128 * 1024)
    expected = {
        "schema_version", "message_type", "operation_id", "profile_id", "profile_version",
        "profile_sha256", "payload_relative_path", "payload_document_sha256",
        "pointer_revision", "previous_pointer_sha256", "promoted_at",
        "pointer_self_hash",
    }
    if type(value) is not dict or set(value) != expected:
        raise MontageLearningFileBridgeError("profile pointer fields mismatch")
    if (
        value["schema_version"] != PROFILE_POINTER_VERSION
        or value["message_type"] != PROFILE_POINTER_TYPE
    ):
        raise MontageLearningFileBridgeError("profile pointer identity mismatch")
    coordinates = _profile_coordinates(
        _read_json_regular(
            layout.root / str(value["payload_relative_path"]),
            max_bytes=MAX_DELIVERY_BYTES,
        ),
        layout,
    )
    for field in (
        "profile_id", "profile_version", "profile_sha256", "payload_relative_path",
        "payload_document_sha256",
    ):
        if coordinates[field] != value[field]:
            raise MontageLearningFileBridgeError("profile pointer binding mismatch")
    body = dict(value)
    supplied_hash = body.pop("pointer_self_hash")
    if sha256_json(body) != supplied_hash:
        raise MontageLearningFileBridgeError("profile pointer hash mismatch")
    return value


def _recover_profile_promotion_locked(
    layout: BridgeLayout,
    *,
    failure_hook: Callable[[str, Path], None] | None,
) -> dict[str, object]:
    journal = _validate_profile_journal(
        _read_json_regular(layout.profile_journal, max_bytes=128 * 1024), layout
    )
    pointer = _profile_pointer_from_journal(journal)
    marker = _profile_marker_from_journal(journal, pointer)
    payload_path = layout.root / str(journal["payload_relative_path"])
    payload_parent = payload_path.parent
    _mkdir_safe(payload_parent)

    if journal["state"] == "PREPARED":
        # A PREPARED journal has no durable body.  The caller must still own the
        # envelope during the initial invocation; recovery begins after payload.
        raise MontageLearningFileBridgeError(
            "profile PREPARED recovery requires the original envelope"
        )
    payload = _read_json_regular(payload_path, max_bytes=MAX_DELIVERY_BYTES)
    payload_bytes = canonical_json_bytes(payload) + b"\n"
    if f"sha256:{sha256(payload_bytes).hexdigest()}" != journal["payload_document_sha256"]:
        raise MontageLearningFileBridgeError("profile payload durable hash mismatch")

    if journal["state"] == "PAYLOAD_WRITTEN":
        AtomicJsonWriter.write(layout.profile_pointer, pointer)
        if _load_profile_pointer(layout) != pointer:
            raise MontageLearningFileBridgeError("profile pointer read-back mismatch")
        journal = _advance_profile_journal(layout, journal, "POINTER_COMMITTED")
        _call_profile_failure(failure_hook, "after_profile_pointer", layout.profile_pointer)
    if journal["state"] == "POINTER_COMMITTED":
        AtomicJsonWriter.write(layout.current_profile, payload)
        if _read_regular_bytes(
            layout.current_profile, max_bytes=MAX_DELIVERY_BYTES
        ) != payload_bytes:
            raise MontageLearningFileBridgeError("profile v1 view byte mismatch")
        journal = _advance_profile_journal(layout, journal, "VIEW_COMMITTED")
        _call_profile_failure(failure_hook, "after_profile_view", layout.current_profile)
    if journal["state"] == "VIEW_COMMITTED":
        AtomicJsonWriter.write(layout.profile_marker, marker)
        if _read_json_regular(layout.profile_marker, max_bytes=128 * 1024) != marker:
            raise MontageLearningFileBridgeError("profile marker read-back mismatch")
        journal = _advance_profile_journal(layout, journal, "MARKER_COMMITTED")
        _call_profile_failure(failure_hook, "after_profile_marker", layout.profile_marker)
    if journal["state"] == "MARKER_COMMITTED":
        _verify_profile_publication(layout, pointer)
        journal = _advance_profile_journal(layout, journal, "READBACK_VERIFIED")
    if journal["state"] != "READBACK_VERIFIED":
        raise MontageLearningFileBridgeError("profile recovery did not reach terminal")
    _verify_profile_publication(layout, pointer)
    layout.profile_journal.unlink()
    _directory_fsync(layout.state)
    return pointer


def _write_profile_payload_and_recover(
    layout: BridgeLayout,
    journal: Mapping[str, object],
    envelope: Mapping[str, object],
    *,
    failure_hook: Callable[[str, Path], None] | None,
) -> dict[str, object]:
    payload_path = layout.root / str(journal["payload_relative_path"])
    _mkdir_safe(payload_path.parent)
    _write_new_or_identical(payload_path, envelope)
    if _read_regular_bytes(payload_path, max_bytes=MAX_DELIVERY_BYTES) != (
        canonical_json_bytes(dict(envelope)) + b"\n"
    ):
        raise MontageLearningFileBridgeError("profile immutable payload mismatch")
    current = _advance_profile_journal(layout, journal, "PAYLOAD_WRITTEN")
    _call_profile_failure(failure_hook, "after_profile_payload", payload_path)
    return _recover_profile_promotion_locked(layout, failure_hook=failure_hook)


def _verify_profile_publication(
    layout: BridgeLayout, pointer: Mapping[str, object]
) -> None:
    current = _load_profile_pointer(layout)
    if current != dict(pointer):
        raise MontageLearningFileBridgeError("profile pointer currentness mismatch")
    payload_path = layout.root / str(pointer["payload_relative_path"])
    payload_bytes = _read_regular_bytes(payload_path, max_bytes=MAX_DELIVERY_BYTES)
    if f"sha256:{sha256(payload_bytes).hexdigest()}" != pointer["payload_document_sha256"]:
        raise MontageLearningFileBridgeError("profile payload hash mismatch")
    if _read_regular_bytes(layout.current_profile, max_bytes=MAX_DELIVERY_BYTES) != payload_bytes:
        raise MontageLearningFileBridgeError("profile compatibility view mismatch")
    marker = _read_json_regular(layout.profile_marker, max_bytes=128 * 1024)
    expected_marker = _profile_marker_from_journal(pointer, pointer)
    if marker != expected_marker:
        raise MontageLearningFileBridgeError("profile marker binding mismatch")


def _call_profile_failure(
    hook: Callable[[str, Path], None] | None, phase: str, path: Path
) -> None:
    if hook is not None:
        hook(phase, path)


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


def _exact_json_snapshot(value: object, *, path: str, max_depth: int) -> Any:
    if max_depth < 0:
        raise MontageLearningFileBridgeError("JSON nesting is too deep")
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise MontageLearningFileBridgeError(f"{path} is not finite")
        return value
    if type(value) is list:
        return [
            _exact_json_snapshot(
                item, path=f"{path}[{index}]", max_depth=max_depth - 1
            )
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise MontageLearningFileBridgeError(f"{path} has an invalid key")
        return {
            key: _exact_json_snapshot(
                item, path=f"{path}.{key}", max_depth=max_depth - 1
            )
            for key, item in value.items()
        }
    raise MontageLearningFileBridgeError(
        f"{path} must contain exact built-in JSON values"
    )


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
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
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
    "build_generic_receipt_correlation",
    "bridge_importer_guard",
    "advance_claim_state",
    "claim_delivery",
    "clear_pending_receipt_publication_exact",
    "complete_claim",
    "complete_quarantined_claim",
    "create_pending_receipt_publication_new_or_identical",
    "list_delivery_paths",
    "load_generic_receipt_correlation",
    "load_bridge_owner",
    "load_published_receipt",
    "load_receipt_publication_pending",
    "mark_claim_receipt_published",
    "provision_bridge",
    "publish_current_profile",
    "publish_generic_receipt_correlation_new_or_identical",
    "publish_receipt_new_or_identical",
    "quarantine_claim",
    "recover_current_profile",
    "receipt_identity_publisher_guard",
    "receipt_publication_paths",
    "snapshot_delivery",
]
