"""TASK-058 FAST-BATCH-1A canonical admission transaction.

Only a raw exact TASK-055 delivery enters this writer.  P1C-B/C/D are rerun
inside the Product Project lock and a separately rooted anchor guard.  Public
v2 receipts are published only after ProjectSave, canonical child, manifest,
anchor and receipt-registry read-back all agree.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable, Iterator, Mapping

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError
from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
    validate_generic_learning_delivery,
)
from .montage_learning_canonical_promotion_ledger_contract import (
    AppendDecision,
    MontageLearningCanonicalLedgerCandidate,
    MontageLearningCanonicalLedgerCasExpectation,
    evaluate_montage_learning_canonical_append,
)
from .montage_learning_durable_staging_readback import (
    verify_montage_learning_durable_staging_readback,
)
from .montage_learning_external_monotonic_anchor_contract import (
    AnchorDecision,
    MontageLearningExternalMonotonicAnchorCandidate,
    MontageLearningExternalMonotonicAnchorExpectation,
    evaluate_montage_learning_external_monotonic_anchor,
)
from .montage_learning_receipt_contracts import (
    ACCEPTED, DUPLICATE, EXACT_EVIDENCE,
    CONTRACT_PROFILE as RECEIPT_CONTRACT_PROFILE,
    MESSAGE_TYPE as RECEIPT_MESSAGE_TYPE,
    SCHEMA_VERSION as RECEIPT_SCHEMA_VERSION,
    MontageLearningAdmissionReceipt,
    compute_montage_learning_receipt_sha256,
    parse_montage_learning_admission_receipt,
)
from .product_project import (
    ProductProjectManifest, ProjectChildBinding, parse_product_project_manifest,
)
from .product_project_store import ProductProjectManifestStore, _exclusive_project_lock
from .project_save import (
    ProductProjectSaveCoordinator,
    ProjectSaveParticipantOutcome,
    ProjectSaveParticipantPlan,
    ProjectSaveParticipantResult,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
TASK_OWNER = "TASK-058"
CANONICAL_RELATIVE_PATH = Path("state/montage-learning-canonical-admission.json")
RECEIPT_RELATIVE_PATH = Path("state/montage-learning-admission-receipts-v2.json")
JOURNAL_RELATIVE_PATH = Path("state/montage-learning-canonical-admission-transaction.json")
ANCHOR_FILE_NAME = "montage-learning-external-monotonic-anchor.json"
ANCHOR_RECOVERY_FILE_NAME = ".montage-learning-external-monotonic-anchor.recovery.json"
CANONICAL_FORMAT_ID = "bai.montage-learning-canonical-admission"
CANONICAL_FORMAT_VERSION = "1.0.0"
GENERIC_OBSERVATION_RELATIVE_PATH = Path("state/montage-learning-generic-review-observations.json")
GENERIC_OBSERVATION_COMMIT_RELATIVE_PATH = Path(
    "state/montage-learning-generic-review-observation-commit.json"
)
GENERIC_OBSERVATION_JOURNAL_RELATIVE_PATH = Path(
    "state/montage-learning/review-observation-admission-journal.json"
)
GENERIC_OBSERVATION_OBJECT_DIRECTORY = Path(
    "state/montage-learning/review-observations"
)
GENERIC_OBSERVATION_MARKER_DIRECTORY = Path(
    "state/montage-learning/review-observation-markers"
)
GENERIC_OBSERVATION_FORMAT_ID = "bai.montage-learning-generic-review-observations"
GENERIC_OBSERVATION_FORMAT_VERSION = "1.0.0"
GENERIC_OBSERVATION_OBJECT_FORMAT_ID = "bai.montage-learning-generic-review-observation-object"
_PARTICIPANT_ID = "TASK058/MONTAGE-ANCHOR"
_PARTICIPANT_VERSION = "1.0.0"

_CANONICAL_DOMAIN = b"TASK058_CANONICAL_ADMISSION_STORE_V1\0"
_ANCHOR_DOMAIN = b"TASK058_EXTERNAL_MONOTONIC_ANCHOR_STORE_V1\0"
_REGISTRY_DOMAIN = b"TASK058_ADMISSION_RECEIPT_REGISTRY_V1\0"
_JOURNAL_DOMAIN = b"TASK058_CANONICAL_ADMISSION_TRANSACTION_JOURNAL_V1\0"
_RECEIPT_ID_DOMAIN = b"TASK058_CANONICAL_ADMISSION_RECEIPT_ID_V1\0"
_GENERIC_EMPTY_LEDGER_DOMAIN = "BVP_REVIEW_OBSERVATION_LEDGER_EMPTY_V1"
_GENERIC_ENTRY_DOMAIN = "BVP_REVIEW_OBSERVATION_LEDGER_ENTRY_V1"
_GENERIC_TRANSACTION_DOMAIN_V1 = "BVP_REVIEW_OBSERVATION_TRANSACTION_ID_V1"
_GENERIC_CHILD_BINDING_DOMAIN = "BVP_REVIEW_OBSERVATION_PROJECT_CHILD_BINDING_V1"
_GENERIC_MARKER_BODY_DOMAIN = "BVP_REVIEW_OBSERVATION_MARKER_BODY_V1"
_GENERIC_COMMIT_DOMAIN_V1 = "BVP_REVIEW_OBSERVATION_CANONICAL_COMMIT_V1"
_GENERIC_MARKER_SELF_DOMAIN = "BVP_REVIEW_OBSERVATION_MARKER_SELF_V1"
_GENERIC_INTERNAL_RECEIPT_DOMAIN = "BVP_REVIEW_OBSERVATION_CANONICAL_READBACK_V1"
_GENERIC_OPERATION_RESULT_DOMAIN = "BVP_REVIEW_OBSERVATION_ADMISSION_RESULT_V1"
_GENERIC_PROJECT_SCOPE_DOMAIN = "BVP_REVIEW_OBSERVATION_PROJECT_SCOPE_V1"
_GENERIC_UNBOUND_OWNER_SCOPE = "sha256:" + "0" * 64
_MAX_BYTES = 64 * 1024 * 1024
_MAX_RECEIPTS = 8192
_REPARSE_POINT = 0x400
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
FailureHook = Callable[[str, Path], None]


class MontageLearningCanonicalAdmissionError(ValueError):
    """Fail-closed canonical admission error."""


def _exact(value: object, name: str, *, max_nodes: int = 400_000) -> Any:
    count = 0
    active: set[int] = set()

    def copy(item: object, path: str, depth: int) -> Any:
        nonlocal count
        count += 1
        if count > max_nodes or depth > 40:
            raise MontageLearningCanonicalAdmissionError(f"{name} exceeds bounds")
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) not in {dict, list}:
            raise MontageLearningCanonicalAdmissionError(f"{path} is not exact JSON")
        marker = id(item)
        if marker in active:
            raise MontageLearningCanonicalAdmissionError(f"{path} contains a cycle")
        active.add(marker)
        try:
            if type(item) is list:
                return [copy(child, f"{path}[]", depth + 1) for child in item]
            output: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise MontageLearningCanonicalAdmissionError(f"{path} has a non-string key")
                output[key] = copy(child, f"{path}.{key}", depth + 1)
            return output
        finally:
            active.remove(marker)

    return copy(value, name, 0)


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _sha(value: object, name: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _hash(domain: bytes, body: Mapping[str, Any]) -> str:
    return sha256_bytes(domain + canonical_json_bytes(body))


def _bare_sha(value: object, name: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _domain_hash(domain: str, body: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({"domain": domain, **dict(body)})).removeprefix(
        "sha256:"
    )


def _as_bare_sha(value: str) -> str:
    return value.removeprefix("sha256:")


def _without(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: value for key, value in body.items() if key != field}


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _root(value: str | Path, name: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir() or _is_reparse(path):
        raise MontageLearningCanonicalAdmissionError(f"{name} must be an existing safe root")
    return path.resolve(strict=True)


def _target(path: Path) -> None:
    if not path.parent.is_dir() or _is_reparse(path.parent):
        raise MontageLearningCanonicalAdmissionError("target parent is unsafe")
    if _is_reparse(path) or (path.exists() and not path.is_file()):
        raise MontageLearningCanonicalAdmissionError("target is unsafe")


def _ensure_safe_directory_locked(path: Path, name: str) -> None:
    """Create one authority directory while the Product Project lock is held."""

    try:
        parent_before = path.parent.lstat()
        if (
            not stat.S_ISDIR(parent_before.st_mode)
            or stat.S_ISLNK(parent_before.st_mode)
            or bool(getattr(parent_before, "st_file_attributes", 0) & _REPARSE_POINT)
        ):
            raise MontageLearningCanonicalAdmissionError(f"{name} parent is unsafe")
        path.mkdir()
    except FileExistsError:
        pass
    except MontageLearningCanonicalAdmissionError:
        raise
    except OSError as exc:
        raise MontageLearningCanonicalAdmissionError(f"{name} could not be initialized") from exc
    try:
        current = path.lstat()
        parent_after = path.parent.lstat()
    except OSError as exc:
        raise MontageLearningCanonicalAdmissionError(f"{name} is unavailable") from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or bool(getattr(current, "st_file_attributes", 0) & _REPARSE_POINT)
        or _file_identity(parent_after) != _file_identity(parent_before)
    ):
        raise MontageLearningCanonicalAdmissionError(f"{name} is unsafe")


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(info.st_dev), int(info.st_ino), stat.S_IFMT(info.st_mode),
        int(getattr(info, "st_file_attributes", 0)),
    )


def _ancestor_snapshot(path: Path) -> tuple[tuple[Path, tuple[int, int, int, int]], ...]:
    chain: list[Path] = []
    current = path.parent
    while True:
        chain.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    snapshot: list[tuple[Path, tuple[int, int, int, int]]] = []
    for ancestor in reversed(chain):
        info = ancestor.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            bool(getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)):
            raise MontageLearningCanonicalAdmissionError("document ancestor is unsafe")
        snapshot.append((ancestor, _file_identity(info)))
    return tuple(snapshot)


def _require_pinned_path_unchanged(
    path: Path,
    handle_identity: tuple[int, int, int, int],
    ancestors: tuple[tuple[Path, tuple[int, int, int, int]], ...],
) -> None:
    current = path.lstat()
    if (not stat.S_ISREG(current.st_mode) or stat.S_ISLNK(current.st_mode) or
        bool(getattr(current, "st_file_attributes", 0) & _REPARSE_POINT) or
        _file_identity(current) != handle_identity):
        raise MontageLearningCanonicalAdmissionError("document target changed during pinned read")
    if _ancestor_snapshot(path) != ancestors:
        raise MontageLearningCanonicalAdmissionError("document ancestor changed during pinned read")


def _open_existing_lock_nofollow(path: Path, name: str) -> Any:
    """Open an existing lock without following a final-component link."""

    file_descriptor: int | None = None
    try:
        if os.name == "nt":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
            create_file.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
            )
            create_file.restype = wintypes.HANDLE
            raw_handle = create_file(
                str(path),
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0x00000001 | 0x00000002 | 0x00000004,  # shared read/write/delete
                None,
                3,  # OPEN_EXISTING
                0x00000080 | 0x00200000,  # NORMAL | OPEN_REPARSE_POINT
                None,
            )
            invalid_handle = ctypes.c_void_p(-1).value
            if raw_handle == invalid_handle:
                raise OSError(ctypes.get_last_error(), "CreateFileW failed")
            try:
                file_descriptor = msvcrt.open_osfhandle(
                    int(raw_handle), os.O_RDWR | os.O_BINARY | os.O_NOINHERIT
                )
            except BaseException:
                ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(raw_handle)
                raise
            raw_handle = None  # CRT fd owns the native HANDLE from this point.
        else:
            nofollow = getattr(os, "O_NOFOLLOW", None)
            if nofollow is None:
                raise OSError("nofollow open is unavailable")
            file_descriptor = os.open(
                path,
                os.O_RDWR | nofollow | getattr(os, "O_CLOEXEC", 0),
            )
        try:
            os.set_inheritable(file_descriptor, False)
            handle = os.fdopen(file_descriptor, "r+b", closefd=True)
        except BaseException:
            closing_descriptor = file_descriptor
            file_descriptor = None
            os.close(closing_descriptor)
            raise
        file_descriptor = None  # The returned file object now owns the fd.
    except (FileNotFoundError, OSError) as exc:
        raise MontageLearningCanonicalAdmissionError(
            f"RECOVERY_REQUIRED: {name} lock changed or cannot be pinned"
        ) from exc
    return handle


def _acquire_windows_lock_bounded(handle: Any, name: str) -> None:
    """Acquire one CRT byte lock with a finite contention deadline."""

    import msvcrt

    deadline = time.monotonic() + 10.0
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EDEADLK}:
                raise
            if time.monotonic() >= deadline:
                raise MontageLearningCanonicalAdmissionError(
                    f"RECOVERY_REQUIRED: {name} lock contention timed out"
                ) from exc
            time.sleep(0.01)


@contextmanager
def _exclusive_existing_read_lock(path: Path, name: str) -> Iterator[None]:
    """Lock an established one-byte lock artifact without creating or writing it."""

    try:
        ancestors = _ancestor_snapshot(path)
        before = path.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise MontageLearningCanonicalAdmissionError(
            f"RECOVERY_REQUIRED: {name} lock is absent or unreadable"
        ) from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or bool(getattr(before, "st_file_attributes", 0) & _REPARSE_POINT)
        or before.st_size != 1
    ):
        raise MontageLearningCanonicalAdmissionError(
            f"RECOVERY_REQUIRED: {name} lock is invalid before open"
        )
    before_identity = _file_identity(before)
    handle = _open_existing_lock_nofollow(path, name)
    with handle:
        os.set_inheritable(handle.fileno(), False)

        def validate(*, check_content: bool) -> tuple[int, int, int, int]:
            info = os.fstat(handle.fileno())
            identity = _file_identity(info)
            if (
                not stat.S_ISREG(info.st_mode)
                or bool(getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)
                or info.st_size != 1
                or identity != before_identity
            ):
                raise MontageLearningCanonicalAdmissionError(
                    f"RECOVERY_REQUIRED: {name} lock is invalid"
                )
            if check_content:
                handle.seek(0)
                if handle.read(1) != b"0" or handle.read(1) != b"":
                    raise MontageLearningCanonicalAdmissionError(
                        f"RECOVERY_REQUIRED: {name} lock content is invalid"
                    )
            _require_pinned_path_unchanged(path, identity, ancestors)
            return identity

        # A Windows byte lock also denies reads of the locked byte. Validate
        # pinned structure first, then validate content after lock ownership.
        identity = validate(check_content=False)
        handle.seek(0)
        locked = False
        try:
            if os.name == "nt":
                _acquire_windows_lock_bounded(handle, name)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            if validate(check_content=True) != identity:
                raise MontageLearningCanonicalAdmissionError(
                    f"RECOVERY_REQUIRED: {name} lock identity changed"
                )
            yield
            if validate(check_content=True) != identity:
                raise MontageLearningCanonicalAdmissionError(
                    f"RECOVERY_REQUIRED: {name} lock identity changed"
                )
        finally:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _exclusive_existing_project_lock(
    project_root: Path,
) -> Iterator[ProductProjectManifest]:
    """Acquire the canonical Product lock without provisioning invalid Projects."""

    try:
        lock_path = ProductProjectManifestStore.path(project_root).with_name(
            ".project.json.lock"
        )
    except (ProductError, OSError) as exc:
        raise MontageLearningCanonicalAdmissionError(
            "RECOVERY_REQUIRED: Product Project authority is unavailable"
        ) from exc
    with _exclusive_existing_read_lock(lock_path, "Product Project"):
        try:
            manifest = ProductProjectManifestStore.load(project_root)
        except (ProductError, OSError) as exc:
            raise MontageLearningCanonicalAdmissionError(
                "RECOVERY_REQUIRED: Product Project manifest is unavailable"
            ) from exc
        yield manifest


def _read(path: Path, parser: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Read one authoritative document through a pinned, non-inheritable handle."""
    _target(path)
    try:
        ancestors = _ancestor_snapshot(path)
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or
            bool(getattr(before, "st_file_attributes", 0) & _REPARSE_POINT)):
            raise ValueError("type")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            os.set_inheritable(descriptor, False)
            opened = os.fstat(descriptor)
            identity = _file_identity(opened)
            if (not stat.S_ISREG(opened.st_mode) or identity != _file_identity(before) or
                not 1 <= opened.st_size <= _MAX_BYTES):
                raise ValueError("pinned identity/size")
            chunks: list[bytes] = []
            remaining = opened.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError("short read")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise ValueError("document grew during read")
            after = os.fstat(descriptor)
            if (_file_identity(after) != identity or after.st_size != opened.st_size or
                getattr(after, "st_mtime_ns", None) != getattr(opened, "st_mtime_ns", None)):
                raise ValueError("handle changed during read")
            raw = b"".join(chunks)
            _require_pinned_path_unchanged(path, identity, ancestors)
        finally:
            os.close(descriptor)
        value = json.loads(raw.decode("utf-8"))
        if type(value) is not dict or raw != canonical_json_bytes(value) + b"\n":
            raise ValueError("canonical")
        return parser(value)
    except MontageLearningCanonicalAdmissionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise MontageLearningCanonicalAdmissionError(f"invalid document: {path.name}") from exc


def _parse_canonical(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "canonical")
    expected = {
        "schema_version", "record_type", "task_owner", "project_id",
        "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
        "source_project_manifest_sha256", "ledger", "external_anchor_sha256",
        "canonical_state", "canonical_store_written", "durable_readback_required",
        "directory_durability_confirmed", "hostile_path_race_protection_verified",
        "automatic_learning_promotion_authorized", "profile_generation_authorized",
        "timeline_mutation_authorized", "resolve_write_authorized",
        "release_authorized", "deploy_authorized", "production_authorized",
        "canonical_store_commit_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("canonical fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_CANONICAL_ADMISSION_STORE" or
        body["task_owner"] != TASK_OWNER or body["canonical_state"] != "COMMITTED" or
        body["canonical_store_written"] is not True or
        body["durable_readback_required"] is not True):
        raise MontageLearningCanonicalAdmissionError("canonical identity mismatch")
    for name in ("project_id", "canonical_store_id"):
        _identifier(body[name], name)
    for name in ("owner_scope_hash", "ledger_key_sha256", "source_project_manifest_sha256",
                 "external_anchor_sha256", "canonical_store_commit_sha256"):
        _sha(body[name], name)
    if body["directory_durability_confirmed"] is not False:
        raise MontageLearningCanonicalAdmissionError("directory durability is not claimed")
    for name in ("hostile_path_race_protection_verified", "automatic_learning_promotion_authorized",
                 "profile_generation_authorized", "timeline_mutation_authorized",
                 "resolve_write_authorized", "release_authorized", "deploy_authorized",
                 "production_authorized"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    ledger = MontageLearningCanonicalLedgerCandidate.from_dict(body["ledger"]).to_dict()
    if ledger["ledger_revision"] <= 0:
        raise MontageLearningCanonicalAdmissionError("canonical ledger is empty")
    for name in ("project_id", "canonical_store_id", "owner_scope_hash", "ledger_key_sha256"):
        if body[name] != ledger[name]:
            raise MontageLearningCanonicalAdmissionError("canonical ledger scope mismatch")
    if body["canonical_store_commit_sha256"] != _hash(
        _CANONICAL_DOMAIN, _without(body, "canonical_store_commit_sha256")
    ):
        raise MontageLearningCanonicalAdmissionError("canonical digest mismatch")
    body["ledger"] = ledger
    return body


def _parse_anchor(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "anchor")
    expected = {
        "schema_version", "record_type", "task_owner", "project_id",
        "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
        "canonical_store_commit_sha256", "target_project_manifest_sha256",
        "target_project_manifest_revision", "anchor",
        "anchor_state", "external_anchor_written", "external_snapshot_coordinate_only",
        "origin_authenticated_by_store", "rollback_detection_authority_created",
        "directory_durability_confirmed", "hostile_path_race_protection_verified",
        "external_anchor_document_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("anchor fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_STORE" or
        body["task_owner"] != TASK_OWNER or body["anchor_state"] != "ESTABLISHED" or
        body["external_anchor_written"] is not True or
        body["external_snapshot_coordinate_only"] is not True):
        raise MontageLearningCanonicalAdmissionError("anchor identity mismatch")
    for name in ("origin_authenticated_by_store", "rollback_detection_authority_created",
                 "directory_durability_confirmed", "hostile_path_race_protection_verified"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    for name in ("project_id", "canonical_store_id"):
        _identifier(body[name], name)
    for name in ("owner_scope_hash", "ledger_key_sha256", "canonical_store_commit_sha256",
                 "target_project_manifest_sha256", "external_anchor_document_sha256"):
        _sha(body[name], name)
    _integer(body["target_project_manifest_revision"], "target_project_manifest_revision", 1, 2**63 - 1)
    anchor = MontageLearningExternalMonotonicAnchorCandidate.from_dict(body["anchor"]).to_dict()
    for name in ("project_id", "canonical_store_id", "owner_scope_hash", "ledger_key_sha256"):
        if body[name] != anchor[name]:
            raise MontageLearningCanonicalAdmissionError("anchor scope mismatch")
    if body["external_anchor_document_sha256"] != _hash(
        _ANCHOR_DOMAIN, _without(body, "external_anchor_document_sha256")
    ):
        raise MontageLearningCanonicalAdmissionError("anchor digest mismatch")
    body["anchor"] = anchor
    return body


def _parse_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "receipt registry")
    expected = {"schema_version", "record_type", "task_owner", "project_id",
                "canonical_store_id", "owner_scope_hash", "revision", "receipts",
                "registry_sha256"}
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("registry fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_ADMISSION_RECEIPT_REGISTRY_V2" or
        body["task_owner"] != TASK_OWNER):
        raise MontageLearningCanonicalAdmissionError("registry identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["canonical_store_id"], "canonical_store_id")
    _sha(body["owner_scope_hash"], "owner_scope_hash")
    revision = _integer(body["revision"], "revision", 0, _MAX_RECEIPTS)
    if type(body["receipts"]) is not list or len(body["receipts"]) != revision:
        raise MontageLearningCanonicalAdmissionError("registry count mismatch")
    accepted: dict[str, str] = {}
    ids: set[str] = set()
    hashes: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for raw in body["receipts"]:
        receipt = parse_montage_learning_admission_receipt(raw).to_dict()
        if receipt["owner_scope_hash"] != body["owner_scope_hash"]:
            raise MontageLearningCanonicalAdmissionError("registry scope mismatch")
        if receipt["receipt_id"] in ids or receipt["receipt_sha256"] in hashes:
            raise MontageLearningCanonicalAdmissionError("registry replay")
        key = receipt["idempotency_key_sha256"]
        if receipt["status"] == ACCEPTED:
            if key in accepted:
                raise MontageLearningCanonicalAdmissionError("multiple ACCEPTED lineage roots")
            accepted[key] = receipt["receipt_sha256"]
        elif accepted.get(key) != receipt["duplicate_of_receipt_sha256"]:
            raise MontageLearningCanonicalAdmissionError("DUPLICATE lineage mismatch")
        ids.add(receipt["receipt_id"])
        hashes.add(receipt["receipt_sha256"])
        parsed.append(receipt)
    if body["registry_sha256"] != _hash(_REGISTRY_DOMAIN, _without(body, "registry_sha256")):
        raise MontageLearningCanonicalAdmissionError("registry digest mismatch")
    body["receipts"] = parsed
    return body


def _empty_registry(project_id: str, store_id: str, scope: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_ADMISSION_RECEIPT_REGISTRY_V2",
        "task_owner": TASK_OWNER,
        "project_id": project_id,
        "canonical_store_id": store_id,
        "owner_scope_hash": scope,
        "revision": 0,
        "receipts": [],
    }
    body["registry_sha256"] = _hash(_REGISTRY_DOMAIN, body)
    return _parse_registry(body)


def _append_registry(registry: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    body = _without(registry, "registry_sha256")
    body["receipts"] = [*registry["receipts"], dict(receipt)]
    body["revision"] = len(body["receipts"])
    if body["revision"] > _MAX_RECEIPTS:
        raise MontageLearningCanonicalAdmissionError("registry is full")
    body["registry_sha256"] = _hash(_REGISTRY_DOMAIN, body)
    return _parse_registry(body)


def _build_canonical(source_manifest_sha256: str, ledger: Mapping[str, Any],
                     anchor: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_CANONICAL_ADMISSION_STORE",
        "task_owner": TASK_OWNER,
        "project_id": ledger["project_id"],
        "canonical_store_id": ledger["canonical_store_id"],
        "owner_scope_hash": ledger["owner_scope_hash"],
        "ledger_key_sha256": ledger["ledger_key_sha256"],
        "source_project_manifest_sha256": source_manifest_sha256,
        "ledger": dict(ledger),
        "external_anchor_sha256": anchor["anchor_sha256"],
        "canonical_state": "COMMITTED",
        "canonical_store_written": True,
        "durable_readback_required": True,
        "directory_durability_confirmed": False,
        "hostile_path_race_protection_verified": False,
        "automatic_learning_promotion_authorized": False,
        "profile_generation_authorized": False,
        "timeline_mutation_authorized": False,
        "resolve_write_authorized": False,
        "release_authorized": False,
        "deploy_authorized": False,
        "production_authorized": False,
    }
    body["canonical_store_commit_sha256"] = _hash(_CANONICAL_DOMAIN, body)
    return _parse_canonical(body)


def _build_anchor(canonical: Mapping[str, Any], anchor: Mapping[str, Any],
                  target_manifest_sha256: str, target_manifest_revision: int) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_STORE",
        "task_owner": TASK_OWNER,
        "project_id": canonical["project_id"],
        "canonical_store_id": canonical["canonical_store_id"],
        "owner_scope_hash": canonical["owner_scope_hash"],
        "ledger_key_sha256": canonical["ledger_key_sha256"],
        "canonical_store_commit_sha256": canonical["canonical_store_commit_sha256"],
        "target_project_manifest_sha256": target_manifest_sha256,
        "target_project_manifest_revision": target_manifest_revision,
        "anchor": dict(anchor),
        "anchor_state": "ESTABLISHED",
        "external_anchor_written": True,
        "external_snapshot_coordinate_only": True,
        "origin_authenticated_by_store": False,
        "rollback_detection_authority_created": False,
        "directory_durability_confirmed": False,
        "hostile_path_race_protection_verified": False,
    }
    body["external_anchor_document_sha256"] = _hash(_ANCHOR_DOMAIN, body)
    return _parse_anchor(body)


def _receipt_id(commit: str, key: str, attempt: int) -> str:
    digest = _hash(_RECEIPT_ID_DOMAIN, {
        "canonical_store_commit_sha256": commit,
        "idempotency_key_sha256": key,
        "attempt": attempt,
    }).removeprefix("sha256:")
    return f"task058-{digest[:40]}-{attempt}"


def _mint_receipt(*, readback: Mapping[str, Any], commit: str, status: str,
                  duplicate_of: str | None, attempt: int, bridge_instance_id: str,
                  processed_at: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "message_type": RECEIPT_MESSAGE_TYPE,
        "contract_profile": RECEIPT_CONTRACT_PROFILE,
        "receipt_id": _receipt_id(commit, readback["idempotency_key_sha256"], attempt),
        "admission_class": EXACT_EVIDENCE,
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": readback["source_record_id"],
        "source_sha256": readback["source_sha256"],
        "owner_scope_hash": readback["owner_scope_hash"],
        "idempotency_key_sha256": readback["idempotency_key_sha256"],
        "status": status,
        "canonical_store_written": True,
        "canonical_evidence_id": readback["canonical_evidence_id"],
        "canonical_evidence_sha256": readback["canonical_evidence_sha256"],
        "canonical_store_commit_sha256": commit,
        "duplicate_of_receipt_sha256": duplicate_of,
        "reason_codes": [] if status == ACCEPTED else ["DUPLICATE_IDEMPOTENCY_KEY"],
        "attempt": attempt,
        "processed_at": processed_at,
        "bridge_instance_id": bridge_instance_id,
    }
    body["receipt_sha256"] = compute_montage_learning_receipt_sha256(body)
    return parse_montage_learning_admission_receipt(body).to_dict()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _AnchorParticipant:
    participant_id = _PARTICIPANT_ID
    participant_version = _PARTICIPANT_VERSION

    def __init__(self, *, project_id: str, anchor_path: Path, recovery_path: Path,
                 expected_sha256: str | None, target_anchor: Mapping[str, Any],
                 source_manifest_sha256: str, target_manifest_sha256: str,
                 failure_hook: FailureHook | None = None) -> None:
        self.project_id = project_id
        self.anchor_path = anchor_path
        self.recovery_path = recovery_path
        self.expected_sha256 = expected_sha256
        self.target_anchor = _parse_anchor(target_anchor)
        self.source_manifest_sha256 = source_manifest_sha256
        self.target_manifest_sha256 = target_manifest_sha256
        self.failure_hook = failure_hook

    def _current_sha(self) -> str | None:
        if not self.anchor_path.exists():
            return None
        return str(_read(self.anchor_path, _parse_anchor)["external_anchor_document_sha256"])

    def plan_locked(self, project_root: Path, source_manifest: ProductProjectManifest,
                    target_manifest: ProductProjectManifest) -> ProjectSaveParticipantPlan:
        del project_root
        if (source_manifest.project_id != self.project_id or
            source_manifest.project_manifest_sha256 != self.source_manifest_sha256 or
            target_manifest.project_manifest_sha256 != self.target_manifest_sha256 or
            self._current_sha() != self.expected_sha256):
            raise MontageLearningCanonicalAdmissionError("anchor participant CAS conflict")
        return ProjectSaveParticipantPlan.create(
            participant_id=self.participant_id,
            participant_version=self.participant_version,
            project_id=self.project_id,
            source_manifest_sha256=self.source_manifest_sha256,
            target_manifest_sha256=self.target_manifest_sha256,
            source_content_sha256=self.expected_sha256,
            target_content_sha256=self.target_anchor["external_anchor_document_sha256"],
        )

    def _recovery(self, transaction_id: str, plan: ProjectSaveParticipantPlan) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "MONTAGE_LEARNING_ANCHOR_PARTICIPANT_RECOVERY",
            "participant_id": self.participant_id,
            "participant_version": self.participant_version,
            "project_id": self.project_id,
            "transaction_id": transaction_id,
            "binding_sha256": plan.binding_sha256,
            "source_manifest_sha256": plan.source_manifest_sha256,
            "target_manifest_sha256": plan.target_manifest_sha256,
            "expected_anchor_document_sha256": self.expected_sha256,
            "target_anchor": self.target_anchor,
        }
        body["recovery_sha256"] = _hash(_JOURNAL_DOMAIN, body)
        return body

    def _load_recovery(self) -> dict[str, Any]:
        value = _read(self.recovery_path, lambda item: _exact(item, "anchor recovery"))
        if type(value) is not dict or value.get("recovery_sha256") != _hash(
            _JOURNAL_DOMAIN, _without(value, "recovery_sha256")
        ):
            raise MontageLearningCanonicalAdmissionError("anchor recovery digest mismatch")
        return value

    def prepare_locked(self, project_root: Path, transaction_id: str,
                       plan: ProjectSaveParticipantPlan) -> str:
        del project_root
        body = self._recovery(transaction_id, plan)
        if self.recovery_path.exists():
            if self._load_recovery() != body:
                raise MontageLearningCanonicalAdmissionError("anchor recovery conflicts")
        else:
            AtomicJsonWriter.write(self.recovery_path, body)
        return str(body["recovery_sha256"])

    def _scope(self, transaction_id: str, plan: ProjectSaveParticipantPlan,
               receipt: str) -> dict[str, Any]:
        body = self._load_recovery()
        expected = self._recovery(transaction_id, plan)
        if body != expected or body["recovery_sha256"] != receipt:
            raise MontageLearningCanonicalAdmissionError("anchor recovery scope mismatch")
        return body

    def reconcile_locked(self, project_root: Path, transaction_id: str,
                         plan: ProjectSaveParticipantPlan, prepared_receipt_sha256: str,
                         outcome: ProjectSaveParticipantOutcome) -> ProjectSaveParticipantResult:
        del project_root
        current = self._current_sha()
        if self.recovery_path.exists():
            self._scope(transaction_id, plan, prepared_receipt_sha256)
        else:
            expected_without_recovery = (
                plan.target_content_sha256
                if outcome is ProjectSaveParticipantOutcome.COMPLETE
                else plan.source_content_sha256
            )
            if current != expected_without_recovery:
                raise MontageLearningCanonicalAdmissionError("anchor recovery is missing")
            return ProjectSaveParticipantResult.create(
                participant_id=self.participant_id,
                binding_sha256=plan.binding_sha256,
                transaction_id=transaction_id,
                outcome=outcome,
                result_content_sha256=current,
            )
        if outcome is ProjectSaveParticipantOutcome.COMPLETE:
            if current == plan.source_content_sha256:
                AtomicJsonWriter.write(self.anchor_path, self.target_anchor, validator=_parse_anchor)
                current = self._current_sha()
            if current != plan.target_content_sha256:
                raise MontageLearningCanonicalAdmissionError("anchor commit/read-back failed")
            if self.failure_hook is not None:
                self.failure_hook("after_anchor_write_before_participant_result", self.anchor_path)
        elif current != plan.source_content_sha256:
            raise MontageLearningCanonicalAdmissionError("anchor rollback conflict")
        self.recovery_path.unlink()
        return ProjectSaveParticipantResult.create(
            participant_id=self.participant_id,
            binding_sha256=plan.binding_sha256,
            transaction_id=transaction_id,
            outcome=outcome,
            result_content_sha256=current,
        )

    def abort_prejournal_locked(self, project_root: Path, transaction_id: str,
                                plan: ProjectSaveParticipantPlan,
                                prepared_receipt_sha256: str) -> None:
        del project_root
        self._scope(transaction_id, plan, prepared_receipt_sha256)
        if self._current_sha() != plan.source_content_sha256:
            raise MontageLearningCanonicalAdmissionError("anchor changed before abort")
        self.recovery_path.unlink()

    def reconcile_orphan_locked(self, project_root: Path,
                                current_manifest: ProductProjectManifest) -> str | None:
        del project_root
        if not self.recovery_path.exists():
            return None
        body = self._load_recovery()
        if (body["source_manifest_sha256"] != current_manifest.project_manifest_sha256 or
            self._current_sha() != body["expected_anchor_document_sha256"]):
            raise MontageLearningCanonicalAdmissionError("unsafe anchor orphan")
        receipt = str(body["recovery_sha256"])
        self.recovery_path.unlink()
        return receipt


def _parse_journal(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "transaction journal")
    expected = {
        "schema_version", "record_type", "task_owner", "operation", "project_id",
        "canonical_store_id", "owner_scope_hash", "staging_readback_sha256",
        "expected_previous_commit_sha256", "expected_previous_anchor_document_sha256",
        "expected_previous_registry_sha256", "proposed_canonical", "proposed_anchor",
        "proposed_registry", "target_manifest", "receipt_sha256", "journal_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("journal fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_CANONICAL_ADMISSION_TRANSACTION" or
        body["task_owner"] != TASK_OWNER or body["operation"] not in {ACCEPTED, DUPLICATE}):
        raise MontageLearningCanonicalAdmissionError("journal identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["canonical_store_id"], "canonical_store_id")
    for name in ("owner_scope_hash", "staging_readback_sha256", "receipt_sha256"):
        _sha(body[name], name)
    for name in ("expected_previous_commit_sha256",
                 "expected_previous_anchor_document_sha256",
                 "expected_previous_registry_sha256"):
        _sha(body[name], name, nullable=True)
    canonical = _parse_canonical(body["proposed_canonical"])
    anchor = _parse_anchor(body["proposed_anchor"])
    registry = _parse_registry(body["proposed_registry"])
    manifest = parse_product_project_manifest(body["target_manifest"])
    if (body["project_id"] != canonical["project_id"] or
        body["canonical_store_id"] != canonical["canonical_store_id"] or
        body["owner_scope_hash"] != canonical["owner_scope_hash"] or
        anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
        anchor["target_project_manifest_sha256"] != manifest.project_manifest_sha256 or
        anchor["target_project_manifest_revision"] != manifest.project_revision or
        registry["receipts"][-1]["receipt_sha256"] != body["receipt_sha256"] or
        registry["receipts"][-1]["status"] != body["operation"]):
        raise MontageLearningCanonicalAdmissionError("journal cross-binding mismatch")
    if body["journal_sha256"] != _hash(_JOURNAL_DOMAIN, _without(body, "journal_sha256")):
        raise MontageLearningCanonicalAdmissionError("journal digest mismatch")
    body["proposed_canonical"] = canonical
    body["proposed_anchor"] = anchor
    body["proposed_registry"] = registry
    body["target_manifest"] = manifest.to_dict()
    return body


@dataclass(frozen=True, slots=True)
class MontageLearningCanonicalAdmissionResult:
    receipt: MontageLearningAdmissionReceipt
    canonical_store_commit_sha256: str
    external_anchor_document_sha256: str
    recovered: bool

    @property
    def status(self) -> str:
        return str(self.receipt.to_dict()["status"])


_VERIFIED_TOKEN = object()


class MontageLearningVerifiedAdmissionReceipt:
    __slots__ = ("_receipt", "_manifest", "_anchor")

    def __init__(self, receipt: MontageLearningAdmissionReceipt, manifest: str,
                 anchor: str, *, _token: object | None = None) -> None:
        if _token is not _VERIFIED_TOKEN:
            raise TypeError("use the trusted canonical reader")
        object.__setattr__(self, "_receipt", receipt)
        object.__setattr__(self, "_manifest", manifest)
        object.__setattr__(self, "_anchor", anchor)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("verified receipt is immutable")

    @property
    def receipt(self) -> MontageLearningAdmissionReceipt:
        return self._receipt

    def to_public_projection(self) -> dict[str, object]:
        receipt = self._receipt.to_dict()
        return {
            "receipt_id": receipt["receipt_id"],
            "receipt_sha256": receipt["receipt_sha256"],
            "status": receipt["status"],
            "canonical_store_commit_sha256": receipt["canonical_store_commit_sha256"],
            "project_manifest_sha256": self._manifest,
            "external_anchor_document_sha256": self._anchor,
            "canonical_currentness_verified": True,
            "manifest_child_binding_verified": True,
            "external_anchor_currentness_verified": True,
            "receipt_origin_verified_by_trusted_reader": True,
            "rollback_detection_authority_created": False,
            "automatic_learning_promotion_authorized": False,
            "profile_generation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "release_authorized": False,
            "deploy_authorized": False,
            "production_authorized": False,
        }


def _parse_generic_timestamp(value: object, name: str) -> str:
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid") from exc
    return value


def _parse_generic_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic child binding")
    expected = {
        "domain_owner", "relative_path", "format_id", "format_version",
        "content_sha256", "required", "dependency_hashes",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic child binding fields mismatch")
    if (
        body["domain_owner"] != TASK_OWNER
        or body["relative_path"] != GENERIC_OBSERVATION_RELATIVE_PATH.as_posix()
        or body["format_id"] != GENERIC_OBSERVATION_FORMAT_ID
        or body["format_version"] != GENERIC_OBSERVATION_FORMAT_VERSION
        or body["required"] is not True
        or body["dependency_hashes"] != []
    ):
        raise MontageLearningCanonicalAdmissionError("generic child binding identity mismatch")
    _sha(body["content_sha256"], "generic child content_sha256")
    return body


def _generic_child_binding_sha256(binding: Mapping[str, Any]) -> str:
    return _domain_hash(_GENERIC_CHILD_BINDING_DOMAIN, {"binding": dict(binding)})


def _generic_empty_head() -> str:
    return _domain_hash(_GENERIC_EMPTY_LEDGER_DOMAIN, {"entries": []})


def _parse_generic_ledger_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic observation ledger v1")
    expected = {
        "schema_version", "message_type", "project_id", "project_scope_hash",
        "owner_scope_hash", "store_kind", "store_revision", "entries",
        "ledger_head_sha256", "learning_adopted", "profile_promoted",
        "timeline_mutated",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic ledger fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationLedger"
        or body["store_kind"] != "REVIEW_OBSERVATION"
    ):
        raise MontageLearningCanonicalAdmissionError("generic ledger identity mismatch")
    _identifier(body["project_id"], "project_id")
    _bare_sha(body["project_scope_hash"], "project_scope_hash")
    _bare_sha(body["owner_scope_hash"], "owner_scope_hash")
    revision = _integer(body["store_revision"], "store_revision", 1, _MAX_RECEIPTS)
    if type(body["entries"]) is not list or len(body["entries"]) != revision:
        raise MontageLearningCanonicalAdmissionError("generic ledger revision mismatch")
    for name in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    previous = _generic_empty_head()
    seen: set[str] = set()
    for index, entry in enumerate(body["entries"], start=1):
        fields = {
            "store_revision", "transaction_id", "record_id", "source_digest_sha256",
            "project_scope_hash", "owner_scope_hash", "payload_object_sha256",
            "admission_timestamp", "previous_ledger_head_sha256", "ledger_head_sha256",
        }
        if type(entry) is not dict or set(entry) != fields:
            raise MontageLearningCanonicalAdmissionError("generic ledger entry fields mismatch")
        if entry["store_revision"] != index:
            raise MontageLearningCanonicalAdmissionError("generic ledger entry revision gap")
        for name in (
            "transaction_id", "source_digest_sha256", "project_scope_hash",
            "owner_scope_hash", "payload_object_sha256", "previous_ledger_head_sha256",
            "ledger_head_sha256",
        ):
            _bare_sha(entry[name], name)
        _identifier(entry["record_id"], "record_id")
        _parse_generic_timestamp(entry["admission_timestamp"], "admission_timestamp")
        if (
            entry["project_scope_hash"] != body["project_scope_hash"]
            or entry["owner_scope_hash"] != body["owner_scope_hash"]
            or entry["previous_ledger_head_sha256"] != previous
        ):
            raise MontageLearningCanonicalAdmissionError("generic ledger scope/chain mismatch")
        expected_transaction = _domain_hash(
            _GENERIC_TRANSACTION_DOMAIN_V1,
            {
                "project_scope_hash": entry["project_scope_hash"],
                "owner_scope_hash": entry["owner_scope_hash"],
                "record_id": entry["record_id"],
                "source_digest_sha256": entry["source_digest_sha256"],
            },
        )
        expected_head = _domain_hash(
            _GENERIC_ENTRY_DOMAIN,
            {name: entry[name] for name in fields if name != "ledger_head_sha256"},
        )
        if entry["transaction_id"] != expected_transaction or entry["ledger_head_sha256"] != expected_head:
            raise MontageLearningCanonicalAdmissionError("generic ledger entry digest mismatch")
        if entry["record_id"] in seen:
            raise MontageLearningCanonicalAdmissionError("generic record replay in ledger")
        seen.add(entry["record_id"])
        previous = entry["ledger_head_sha256"]
    if body["ledger_head_sha256"] != previous:
        raise MontageLearningCanonicalAdmissionError("generic ledger head mismatch")
    return body


def _parse_generic_object_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic immutable payload", max_nodes=200_000)
    expected = {
        "schema_version", "message_type", "record_id", "source_digest_sha256",
        "source_delivery", "source_delivery_sha256", "store_kind",
        "learning_adopted", "profile_promoted", "timeline_mutated",
        "payload_object_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic payload fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationPayloadObject"
        or body["store_kind"] != "REVIEW_OBSERVATION"
    ):
        raise MontageLearningCanonicalAdmissionError("generic payload identity mismatch")
    _identifier(body["record_id"], "record_id")
    for name in ("source_digest_sha256", "source_delivery_sha256", "payload_object_sha256"):
        _bare_sha(body[name], name)
    for name in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    candidate = validate_generic_learning_delivery(body["source_delivery"])
    if (
        candidate.record_id != body["record_id"]
        or _as_bare_sha(candidate.source_sha256) != body["source_digest_sha256"]
        or _as_bare_sha(sha256_bytes(canonical_json_bytes(body["source_delivery"])))
        != body["source_delivery_sha256"]
    ):
        raise MontageLearningCanonicalAdmissionError("generic payload source mismatch")
    expected_hash = _domain_hash(
        "BVP_REVIEW_OBSERVATION_PAYLOAD_OBJECT_V1",
        _without(body, "payload_object_sha256"),
    )
    if body["payload_object_sha256"] != expected_hash:
        raise MontageLearningCanonicalAdmissionError("generic payload digest mismatch")
    return body


def _parse_generic_marker_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic commit marker")
    marker_fields = {
        "transaction_id", "record_id", "source_digest_sha256", "project_scope_hash",
        "owner_scope_hash", "product_project_manifest_id",
        "product_project_manifest_revision", "product_project_manifest_sha256",
        "child_binding_sha256", "store_kind", "store_revision",
        "payload_object_sha256", "previous_ledger_head_sha256", "ledger_head_sha256",
        "admission_timestamp",
    }
    expected = marker_fields | {
        "schema_version", "message_type", "marker_body_sha256",
        "canonical_commit_sha256", "marker_self_hash",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic marker fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationCommitMarker"
        or body["store_kind"] != "REVIEW_OBSERVATION"
    ):
        raise MontageLearningCanonicalAdmissionError("generic marker identity mismatch")
    _identifier(body["record_id"], "record_id")
    _identifier(body["product_project_manifest_id"], "product_project_manifest_id")
    _integer(body["product_project_manifest_revision"], "manifest revision", 1, 2**63 - 1)
    _integer(body["store_revision"], "store revision", 1, _MAX_RECEIPTS)
    for name in marker_fields - {
        "record_id", "product_project_manifest_id", "product_project_manifest_revision",
        "store_kind", "store_revision", "admission_timestamp",
    }:
        _bare_sha(body[name], name)
    for name in ("marker_body_sha256", "canonical_commit_sha256", "marker_self_hash"):
        _bare_sha(body[name], name)
    _parse_generic_timestamp(body["admission_timestamp"], "admission_timestamp")
    marker_body = {name: body[name] for name in marker_fields}
    if body["marker_body_sha256"] != _domain_hash(_GENERIC_MARKER_BODY_DOMAIN, marker_body):
        raise MontageLearningCanonicalAdmissionError("generic marker body digest mismatch")
    commit_body = {**marker_body, "marker_body_sha256": body["marker_body_sha256"]}
    if body["canonical_commit_sha256"] != _domain_hash(_GENERIC_COMMIT_DOMAIN_V1, commit_body):
        raise MontageLearningCanonicalAdmissionError("generic canonical commit digest mismatch")
    if body["marker_self_hash"] != _domain_hash(
        _GENERIC_MARKER_SELF_DOMAIN, _without(body, "marker_self_hash")
    ):
        raise MontageLearningCanonicalAdmissionError("generic marker self hash mismatch")
    return body


def _parse_generic_readback_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic canonical readback")
    expected = {
        "schema_version", "message_type", "transaction_id", "record_id",
        "source_digest_sha256", "project_scope_hash", "owner_scope_hash",
        "product_project_manifest_id", "product_project_manifest_revision",
        "product_project_manifest_sha256", "child_binding", "child_binding_sha256",
        "store_kind", "store_revision", "payload_object_sha256",
        "previous_ledger_head_sha256", "ledger_head_sha256", "marker_body_sha256",
        "marker_self_hash", "canonical_commit_sha256", "admission_timestamp",
        "anchor_coordinate", "learning_adopted", "profile_promoted",
        "timeline_mutated", "internal_receipt_self_hash",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic readback fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationCanonicalReadback"
        or body["store_kind"] != "REVIEW_OBSERVATION"
        or body["anchor_coordinate"] is not None
    ):
        raise MontageLearningCanonicalAdmissionError("generic readback identity mismatch")
    _identifier(body["record_id"], "record_id")
    _identifier(body["product_project_manifest_id"], "product_project_manifest_id")
    _integer(body["product_project_manifest_revision"], "manifest revision", 1, 2**63 - 1)
    _integer(body["store_revision"], "store revision", 1, _MAX_RECEIPTS)
    for name in (
        "transaction_id", "source_digest_sha256", "project_scope_hash", "owner_scope_hash",
        "product_project_manifest_sha256", "child_binding_sha256",
        "payload_object_sha256", "previous_ledger_head_sha256", "ledger_head_sha256",
        "marker_body_sha256", "marker_self_hash", "canonical_commit_sha256",
        "internal_receipt_self_hash",
    ):
        _bare_sha(body[name], name)
    _parse_generic_timestamp(body["admission_timestamp"], "admission_timestamp")
    binding = _parse_generic_binding(body["child_binding"])
    if body["child_binding_sha256"] != _generic_child_binding_sha256(binding):
        raise MontageLearningCanonicalAdmissionError("generic readback binding digest mismatch")
    for name in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    if body["internal_receipt_self_hash"] != _domain_hash(
        _GENERIC_INTERNAL_RECEIPT_DOMAIN, _without(body, "internal_receipt_self_hash")
    ):
        raise MontageLearningCanonicalAdmissionError("generic readback self hash mismatch")
    return body


def _parse_generic_result_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic admission result")
    expected = {
        "schema_version", "message_type", "operation_outcome", "canonical_readback",
        "store_kind", "learning_adopted", "profile_promoted", "timeline_mutated",
        "current_product_project_manifest_revision", "current_product_project_manifest_sha256",
        "current_child_binding_sha256", "current_store_revision",
        "current_ledger_head_sha256", "durable_readback_verified",
        "operation_result_self_hash",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic result fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationAdmissionResult"
        or body["operation_outcome"] not in {ACCEPTED, DUPLICATE}
        or body["store_kind"] != "REVIEW_OBSERVATION"
        or body["durable_readback_verified"] is not True
    ):
        raise MontageLearningCanonicalAdmissionError("generic result identity mismatch")
    for name in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    readback = _parse_generic_readback_v1(body["canonical_readback"])
    current_revision = _integer(
        body["current_product_project_manifest_revision"], "current manifest revision", 1, 2**63 - 1
    )
    current_store = _integer(body["current_store_revision"], "current store revision", 1, _MAX_RECEIPTS)
    for name in (
        "current_product_project_manifest_sha256", "current_child_binding_sha256",
        "current_ledger_head_sha256", "operation_result_self_hash",
    ):
        _bare_sha(body[name], name)
    if current_revision < readback["product_project_manifest_revision"] or current_store < readback["store_revision"]:
        raise MontageLearningCanonicalAdmissionError("generic result currentness regressed")
    if body["operation_result_self_hash"] != _domain_hash(
        _GENERIC_OPERATION_RESULT_DOMAIN, _without(body, "operation_result_self_hash")
    ):
        raise MontageLearningCanonicalAdmissionError("generic result self hash mismatch")
    return body


class ReviewObservationCanonicalReadback:
    __slots__ = ("_document",)

    def __init__(self, document: bytes, *, _token: object | None = None) -> None:
        if _token is not _VERIFIED_TOKEN:
            raise TypeError("canonical readback is returned only after trusted current read-back")
        object.__setattr__(self, "_document", document)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("canonical readback is immutable")

    @classmethod
    def _from_dict(cls, value: Mapping[str, Any]) -> "ReviewObservationCanonicalReadback":
        body = _parse_generic_readback_v1(value)
        return cls(canonical_json_bytes(body), _token=_VERIFIED_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._document.decode("utf-8"))

    def __getattr__(self, name: str) -> Any:
        body = self.to_dict()
        if name in body:
            return body[name]
        raise AttributeError(name)


class ReviewObservationAdmissionResult:
    __slots__ = ("_document",)

    def __init__(self, document: bytes, *, _token: object | None = None) -> None:
        if _token is not _VERIFIED_TOKEN:
            raise TypeError("admission results are returned only after durable read-back")
        object.__setattr__(self, "_document", document)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("admission result is immutable")

    @classmethod
    def _from_dict(cls, value: Mapping[str, Any]) -> "ReviewObservationAdmissionResult":
        body = _parse_generic_result_v1(value)
        return cls(canonical_json_bytes(body), _token=_VERIFIED_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._document.decode("utf-8"))

    @property
    def canonical_readback(self) -> ReviewObservationCanonicalReadback:
        return ReviewObservationCanonicalReadback._from_dict(self.to_dict()["canonical_readback"])

    @property
    def status(self) -> str:
        return self.to_dict()["operation_outcome"]

    def __getattr__(self, name: str) -> Any:
        body = self.to_dict()
        if name in body:
            return body[name]
        readback = body["canonical_readback"]
        compatibility = {
            "project_id": "product_project_manifest_id",
            "learning_sha256": "source_digest_sha256",
            "ledger_revision": "store_revision",
            "canonical_commit_sha256": "canonical_commit_sha256",
            "owner_scope_hash": "owner_scope_hash",
            "record_id": "record_id",
        }
        if name in compatibility:
            return readback[compatibility[name]]
        raise AttributeError(name)


# Compatibility name for the already-hosted B+C dependency.  Its value is the
# closed A operation result, never a public SKILL receipt.
GenericReviewObservationReceipt = ReviewObservationAdmissionResult


def _parse_generic_journal_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic PREPARED journal", max_nodes=300_000)
    expected = {
        "schema_version", "message_type", "state", "journal_revision",
        "previous_journal_sha256", "transaction_id", "project_id",
        "project_scope_hash", "owner_scope_hash", "source_project_manifest_revision",
        "source_project_manifest_sha256", "target_project_manifest_revision",
        "target_project_manifest_sha256", "record_id", "source_digest_sha256",
        "source_delivery_sha256", "payload_object_relative_path", "payload_object_sha256",
        "payload_document_sha256", "ledger_document_sha256", "store_revision",
        "previous_ledger_head_sha256", "ledger_head_sha256", "marker_relative_path",
        "marker_body_sha256", "marker_self_hash", "canonical_commit_sha256",
        "admission_timestamp", "canonical_readback", "learning_adopted",
        "profile_promoted", "timeline_mutated", "journal_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic journal fields mismatch")
    if (
        body["schema_version"] != SCHEMA_VERSION
        or body["message_type"] != "ReviewObservationAdmissionJournal"
        or body["state"] not in {
            "PREPARED", "PAYLOAD_WRITTEN", "LEDGER_COMMITTED",
            "MANIFEST_COMMITTED", "MARKER_COMMITTED", "READBACK_VERIFIED", "ABORTED",
        }
    ):
        raise MontageLearningCanonicalAdmissionError("generic journal identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["record_id"], "record_id")
    revision = _integer(body["journal_revision"], "journal revision", 1, 2**63 - 1)
    if body["previous_journal_sha256"] is not None:
        _bare_sha(body["previous_journal_sha256"], "previous_journal_sha256")
    if (revision == 1) != (body["previous_journal_sha256"] is None):
        raise MontageLearningCanonicalAdmissionError("generic journal lineage mismatch")
    for name in (
        "transaction_id", "project_scope_hash", "owner_scope_hash",
        "source_project_manifest_sha256", "target_project_manifest_sha256",
        "source_digest_sha256", "source_delivery_sha256", "payload_object_sha256",
        "payload_document_sha256", "ledger_document_sha256",
        "previous_ledger_head_sha256", "ledger_head_sha256", "marker_body_sha256",
        "marker_self_hash", "canonical_commit_sha256", "journal_sha256",
    ):
        _bare_sha(body[name], name)
    _integer(body["source_project_manifest_revision"], "source manifest revision", 1, 2**63 - 1)
    _integer(body["target_project_manifest_revision"], "target manifest revision", 1, 2**63 - 1)
    _integer(body["store_revision"], "store revision", 1, _MAX_RECEIPTS)
    _parse_generic_timestamp(body["admission_timestamp"], "admission_timestamp")
    if type(body["payload_object_relative_path"]) is not str or type(body["marker_relative_path"]) is not str:
        raise MontageLearningCanonicalAdmissionError("generic journal path invalid")
    for name in ("learning_adopted", "profile_promoted", "timeline_mutated"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    readback = _parse_generic_readback_v1(body["canonical_readback"])
    for field in (
        "transaction_id", "record_id", "source_digest_sha256", "project_scope_hash",
        "owner_scope_hash", "payload_object_sha256", "previous_ledger_head_sha256",
        "ledger_head_sha256", "marker_body_sha256", "marker_self_hash",
        "canonical_commit_sha256", "admission_timestamp",
    ):
        if readback[field] != body[field]:
            raise MontageLearningCanonicalAdmissionError("generic journal/readback mismatch")
    if body["journal_sha256"] != _domain_hash(
        "BVP_REVIEW_OBSERVATION_JOURNAL_V1", _without(body, "journal_sha256")
    ):
        raise MontageLearningCanonicalAdmissionError("generic journal digest mismatch")
    return body


class MontageLearningCanonicalAdmissionTransactionStore:
    """Canonical exact-admission writer and trusted latest-reader."""

    def __init__(self, project_root: str | Path, external_anchor_root: str | Path,
                 *, canonical_store_id: str, bridge_instance_id: str) -> None:
        self.project_root = _root(project_root, "project_root")
        self.external_anchor_root = _root(external_anchor_root, "external_anchor_root")
        try:
            self.external_anchor_root.relative_to(self.project_root)
        except ValueError:
            pass
        else:
            raise MontageLearningCanonicalAdmissionError("anchor root must be external")
        try:
            self.project_root.relative_to(self.external_anchor_root)
        except ValueError:
            pass
        else:
            raise MontageLearningCanonicalAdmissionError("Project root must be external to anchor")
        self.canonical_store_id = _identifier(canonical_store_id, "canonical_store_id")
        self.bridge_instance_id = _identifier(bridge_instance_id, "bridge_instance_id")
        state = self.project_root / "state"
        self.canonical_path = self.project_root / CANONICAL_RELATIVE_PATH
        self.receipt_path = self.project_root / RECEIPT_RELATIVE_PATH
        self.journal_path = self.project_root / JOURNAL_RELATIVE_PATH
        self.generic_observation_path = self.project_root / GENERIC_OBSERVATION_RELATIVE_PATH
        self.generic_commit_path = self.project_root / GENERIC_OBSERVATION_COMMIT_RELATIVE_PATH
        self.generic_journal_path = self.project_root / GENERIC_OBSERVATION_JOURNAL_RELATIVE_PATH
        self.generic_object_root = self.project_root / GENERIC_OBSERVATION_OBJECT_DIRECTORY
        self.generic_marker_root = self.project_root / GENERIC_OBSERVATION_MARKER_DIRECTORY
        with _exclusive_existing_project_lock(self.project_root):
            # Exact and Generic writers share these authority directories.  Keep
            # first-use initialization inside the same Product lock used by both
            # transactions so concurrent constructors cannot leak raw mkdir races.
            _ensure_safe_directory_locked(state, "state root")
            generic_root = self.generic_journal_path.parent
            _ensure_safe_directory_locked(generic_root, "generic authority root")
            _ensure_safe_directory_locked(
                self.generic_object_root, "generic observation object directory"
            )
            _ensure_safe_directory_locked(
                self.generic_marker_root, "generic observation marker directory"
            )
        self.anchor_path = self.external_anchor_root / ANCHOR_FILE_NAME
        self.anchor_recovery_path = self.external_anchor_root / ANCHOR_RECOVERY_FILE_NAME
        self._validate_paths()

    def _validate_paths(self) -> None:
        for path in (self.canonical_path, self.receipt_path, self.journal_path,
                     self.generic_observation_path, self.generic_commit_path,
                     self.generic_journal_path, self.anchor_path,
                     self.anchor_recovery_path):
            _target(path)

    @contextmanager
    def _locks(self) -> Iterator[None]:
        with _exclusive_project_lock(ProductProjectManifestStore.path(self.project_root)):
            with exclusive_file_update_lock(self.anchor_path):
                self._validate_paths()
                yield

    @staticmethod
    def _optional(path: Path, parser: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        return None if not path.exists() else _read(path, parser)

    def _readback(self, raw: Mapping[str, Any], *, staging_store_id: str,
                  owner_scope_hash: str, staging_revision: int,
                  staging_entry_sha256: str):
        return verify_montage_learning_durable_staging_readback(
            raw,
            project_root=self.project_root,
            store_id=staging_store_id,
            expected_owner_scope_hash=owner_scope_hash,
            expected_revision=staging_revision,
            expected_staging_entry_sha256=staging_entry_sha256,
        )

    def _current(self, manifest: ProductProjectManifest, scope: str) -> tuple[
        dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]
    ]:
        canonical = self._optional(self.canonical_path, _parse_canonical)
        anchor = self._optional(self.anchor_path, _parse_anchor)
        if (canonical is None) != (anchor is None):
            raise MontageLearningCanonicalAdmissionError("canonical/anchor split brain")
        registry = (_empty_registry(manifest.project_id, self.canonical_store_id, scope)
                    if not self.receipt_path.exists() else _read(self.receipt_path, _parse_registry))
        if registry["project_id"] != manifest.project_id or registry["canonical_store_id"] != self.canonical_store_id or registry["owner_scope_hash"] != scope:
            raise MontageLearningCanonicalAdmissionError("registry scope mismatch")
        if canonical is not None:
            if (canonical["project_id"] != manifest.project_id or
                canonical["canonical_store_id"] != self.canonical_store_id or
                canonical["owner_scope_hash"] != scope or anchor is None or
                anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
                anchor["anchor"]["anchor_sha256"] != canonical["external_anchor_sha256"]):
                raise MontageLearningCanonicalAdmissionError("canonical/anchor binding mismatch")
        return canonical, anchor, registry

    def _target_manifest(self, source: ProductProjectManifest,
                         canonical_bytes: bytes, updated_at: str) -> ProductProjectManifest:
        binding = ProjectChildBinding(
            domain_owner=TASK_OWNER,
            relative_path=CANONICAL_RELATIVE_PATH.as_posix(),
            format_id=CANONICAL_FORMAT_ID,
            format_version=CANONICAL_FORMAT_VERSION,
            content_sha256=sha256_bytes(canonical_bytes),
            required=True,
        )
        bindings = [item for item in source.child_bindings if item.identity != binding.identity]
        bindings.append(binding)
        return ProductProjectManifest.create(
            project_id=source.project_id,
            project_revision=source.project_revision + 1,
            product_version=source.product_version,
            timebase=source.timebase,
            child_bindings=bindings,
            created_at=source.created_at,
            updated_at=updated_at,
        )

    def _require_terminal_generic_currentness_locked(
        self, manifest: ProductProjectManifest,
    ) -> tuple[dict[str, Any], ProjectChildBinding]:
        """Verify every committed Generic entry before rebasing Exact work."""
        if self.generic_journal_path.exists():
            raise MontageLearningCanonicalAdmissionError(
                "generic recovery must finish before exact rebase"
            )
        binding = next((
            item for item in manifest.child_bindings
            if item.identity == (TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix())
        ), None)
        if binding is None:
            if self.generic_observation_path.exists():
                raise MontageLearningCanonicalAdmissionError(
                    "unbound generic ledger blocks exact rebase"
                )
            raise MontageLearningCanonicalAdmissionError(
                "generic advance is absent during exact rebase"
            )
        ledger = _read(self.generic_observation_path, _parse_generic_ledger_v1)
        if (
            binding.to_dict()
            != self._generic_binding_for_ledger(canonical_json_bytes(ledger) + b"\n").to_dict()
        ):
            raise MontageLearningCanonicalAdmissionError(
                "generic ledger binding blocks exact rebase"
            )
        last = ledger["entries"][-1]
        marker = _read(
            self.project_root /
            self._generic_marker_relative_path(last["transaction_id"]),
            _parse_generic_marker_v1,
        )
        anchored = self._generic_make_readback(marker, binding)
        _, _, current_binding, current_ledger = self._generic_trusted_readback_locked(
            anchored, current_manifest=manifest
        )
        return current_ledger, current_binding

    @staticmethod
    def _is_generic_payload_binding(binding: ProjectChildBinding) -> bool:
        prefix = GENERIC_OBSERVATION_OBJECT_DIRECTORY.as_posix() + "/"
        return (
            binding.domain_owner == TASK_OWNER
            and binding.relative_path.startswith(prefix)
            and binding.relative_path.endswith(".json")
        )

    def _require_single_generic_manifest_advance_locked(
        self,
        journal: Mapping[str, Any],
        live: ProductProjectManifest,
    ) -> None:
        """Accept only one terminal Generic append over the Exact source projection."""
        old_target = parse_product_project_manifest(journal["target_manifest"])
        operation = str(journal["operation"])
        expected_live_revision = (
            old_target.project_revision
            if operation == ACCEPTED
            else old_target.project_revision + 1
        )
        if (
            live.project_id != old_target.project_id
            or live.project_revision != expected_live_revision
            or live.product_version != old_target.product_version
            or live.timebase != old_target.timebase
            or live.created_at != old_target.created_at
        ):
            raise MontageLearningCanonicalAdmissionError(
                "Project advance is not one Generic transaction"
            )
        exact_identity = (TASK_OWNER, CANONICAL_RELATIVE_PATH.as_posix())
        ledger_identity = (TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix())
        excluded_identities = {ledger_identity}
        if operation == ACCEPTED:
            excluded_identities.add(exact_identity)

        def other_projection(manifest: ProductProjectManifest) -> dict[
            tuple[str, str], dict[str, Any]
        ]:
            return {
                item.identity: item.to_dict()
                for item in manifest.child_bindings
                if item.identity not in excluded_identities
                and not self._is_generic_payload_binding(item)
            }

        if other_projection(live) != other_projection(old_target):
            raise MontageLearningCanonicalAdmissionError(
                "non-Generic Project child changed during exact recovery"
            )
        ledger, live_ledger_binding = self._require_terminal_generic_currentness_locked(live)
        new_revision = int(ledger["store_revision"])
        old_revision = new_revision - 1
        if old_revision < 0:
            raise MontageLearningCanonicalAdmissionError(
                "generic revision did not advance exactly once"
            )
        old_ledger_binding = next((
            item for item in old_target.child_bindings if item.identity == ledger_identity
        ), None)
        if old_revision == 0:
            if old_ledger_binding is not None:
                raise MontageLearningCanonicalAdmissionError(
                    "generic source projection is inconsistent"
                )
        else:
            expected_old_ledger = self._generic_binding_for_ledger(
                canonical_json_bytes(self._generic_prefix_ledger(ledger, old_revision)) + b"\n"
            )
            if (
                old_ledger_binding is None
                or old_ledger_binding.to_dict() != expected_old_ledger.to_dict()
            ):
                raise MontageLearningCanonicalAdmissionError(
                    "generic ledger did not append from the Exact source projection"
                )
        live_ledger = next((
            item for item in live.child_bindings if item.identity == ledger_identity
        ), None)
        if live_ledger is None or live_ledger.to_dict() != live_ledger_binding.to_dict():
            raise MontageLearningCanonicalAdmissionError(
                "generic live ledger projection changed"
            )

        def payload_projection(
            manifest: ProductProjectManifest,
        ) -> dict[tuple[str, str], dict[str, Any]]:
            return {
                item.identity: item.to_dict()
                for item in manifest.child_bindings
                if self._is_generic_payload_binding(item)
            }

        expected_old_payloads: dict[tuple[str, str], dict[str, Any]] = {}
        expected_live_payloads: dict[tuple[str, str], dict[str, Any]] = {}
        for index, entry in enumerate(ledger["entries"], start=1):
            relative_path = (
                GENERIC_OBSERVATION_OBJECT_DIRECTORY /
                f"{entry['payload_object_sha256']}.json"
            ).as_posix()
            document = canonical_json_bytes(
                _read(self.project_root / relative_path, _parse_generic_object_v1)
            ) + b"\n"
            binding = self._generic_payload_binding(relative_path, document)
            expected_live_payloads[binding.identity] = binding.to_dict()
            if index <= old_revision:
                expected_old_payloads[binding.identity] = binding.to_dict()
        if (
            payload_projection(old_target) != expected_old_payloads
            or payload_projection(live) != expected_live_payloads
            or len(expected_live_payloads) != len(expected_old_payloads) + 1
        ):
            raise MontageLearningCanonicalAdmissionError(
                "generic payload projection did not advance exactly once"
            )

    def _rebase_pending_exact_after_project_advance_locked(
        self,
        journal: Mapping[str, Any],
        raw: Mapping[str, Any],
        *,
        staging_store_id: str,
        owner_scope_hash: str,
        staging_revision: int,
        staging_entry_sha256: str,
    ) -> dict[str, Any]:
        """Recompile an uncommitted Exact journal from verified current Project truth."""
        live = self._load_manifest_pinned()
        source_sha = str(journal["proposed_canonical"]["source_project_manifest_sha256"])
        target_sha = str(journal["target_manifest"]["project_manifest_sha256"])
        if live.project_manifest_sha256 in {source_sha, target_sha}:
            return dict(journal)
        coordinator = ProductProjectSaveCoordinator()
        if coordinator.recovery_status(self.project_root)["required"]:
            raise MontageLearningCanonicalAdmissionError(
                "Product recovery must finish before exact rebase"
            )
        if self.anchor_recovery_path.exists():
            raise MontageLearningCanonicalAdmissionError(
                "anchor recovery must finish before exact rebase"
            )
        coordinator.require_current_integrity(self.project_root, live)
        self._require_single_generic_manifest_advance_locked(journal, live)
        if journal["operation"] == DUPLICATE:
            # A DUPLICATE journal is already a sealed body-free result over the
            # existing Exact commit.  Keep its historical manifest/anchor
            # coordinates immutable; the finish path revalidates the one
            # Generic advance and consumes only this pending operation journal.
            return dict(journal)
        rebased = self._make_proposal(
            raw,
            staging_store_id=staging_store_id,
            owner_scope_hash=owner_scope_hash,
            staging_revision=staging_revision,
            staging_entry_sha256=staging_entry_sha256,
            expected_commit=journal["expected_previous_commit_sha256"],
            expected_anchor=journal["expected_previous_anchor_document_sha256"],
            processed_at=journal["proposed_registry"]["receipts"][-1]["processed_at"],
        )
        for name in (
            "operation", "project_id", "canonical_store_id", "owner_scope_hash",
            "staging_readback_sha256", "expected_previous_commit_sha256",
            "expected_previous_anchor_document_sha256", "expected_previous_registry_sha256",
        ):
            if rebased[name] != journal[name]:
                raise MontageLearningCanonicalAdmissionError(
                    "exact rebase operation identity changed"
                )
        AtomicJsonWriter.write(self.journal_path, rebased, validator=_parse_journal)
        durable = _read(self.journal_path, _parse_journal)
        if durable != rebased:
            raise MontageLearningCanonicalAdmissionError(
                "rebased exact journal durable read-back failed"
            )
        return durable

    def _make_proposal(self, raw: Mapping[str, Any], *, staging_store_id: str,
                       owner_scope_hash: str, staging_revision: int,
                       staging_entry_sha256: str, expected_commit: str | None,
                       expected_anchor: str | None, processed_at: str) -> dict[str, Any]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        readback_result = self._readback(
            raw, staging_store_id=staging_store_id, owner_scope_hash=owner_scope_hash,
            staging_revision=staging_revision,
            staging_entry_sha256=staging_entry_sha256,
        )
        readback = readback_result.to_dict()
        if readback["project_id"] != manifest.project_id:
            raise MontageLearningCanonicalAdmissionError("staging Project mismatch")
        canonical, anchor_doc, registry = self._current(manifest, owner_scope_hash)
        current_commit = None if canonical is None else canonical["canonical_store_commit_sha256"]
        current_anchor = None if anchor_doc is None else anchor_doc["external_anchor_document_sha256"]
        if current_commit != expected_commit or current_anchor != expected_anchor:
            raise MontageLearningCanonicalAdmissionError("canonical CAS is stale")
        ledger = (MontageLearningCanonicalLedgerCandidate.empty(
            project_id=manifest.project_id,
            canonical_store_id=self.canonical_store_id,
            owner_scope_hash=owner_scope_hash,
        ) if canonical is None else MontageLearningCanonicalLedgerCandidate.from_dict(canonical["ledger"]))
        append = evaluate_montage_learning_canonical_append(
            ledger, MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
            readback_result,
        ).to_dict()
        if append["decision"] == AppendDecision.ID_COLLISION_REJECTED.value:
            raise MontageLearningCanonicalAdmissionError("canonical identity collision")
        if append["decision"] == AppendDecision.STALE_CAS_REJECTED.value:
            raise MontageLearningCanonicalAdmissionError("canonical append CAS rejected")
        attempt = 1 + sum(
            item["idempotency_key_sha256"] == readback["idempotency_key_sha256"]
            for item in registry["receipts"]
        )
        if append["decision"] == AppendDecision.DUPLICATE_CANDIDATE.value:
            if canonical is None or anchor_doc is None:
                raise MontageLearningCanonicalAdmissionError("duplicate lacks committed state")
            roots = [item for item in registry["receipts"]
                     if item["status"] == ACCEPTED and
                     item["idempotency_key_sha256"] == readback["idempotency_key_sha256"] and
                     item["canonical_store_commit_sha256"] == current_commit]
            if len(roots) != 1:
                raise MontageLearningCanonicalAdmissionError("duplicate lineage is not exact")
            target_manifest = manifest
            proposed_canonical = canonical
            proposed_anchor = anchor_doc
            status = DUPLICATE
            duplicate_of = roots[0]["receipt_sha256"]
        elif append["decision"] == AppendDecision.APPEND_CANDIDATE.value:
            proposed_ledger = MontageLearningCanonicalLedgerCandidate.from_dict(
                append["proposed_ledger"]
            )
            current_anchor_candidate = (None if anchor_doc is None else
                MontageLearningExternalMonotonicAnchorCandidate.from_dict(anchor_doc["anchor"]))
            expectation = (
                MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(proposed_ledger)
                if current_anchor_candidate is None else
                MontageLearningExternalMonotonicAnchorExpectation.for_anchor(current_anchor_candidate)
            )
            anchor_evaluation = evaluate_montage_learning_external_monotonic_anchor(
                current_anchor_candidate, expectation,
                None if canonical is None else ledger, proposed_ledger,
            ).to_dict()
            if anchor_evaluation["decision"] not in {
                AnchorDecision.BOOTSTRAP_CANDIDATE.value,
                AnchorDecision.ADVANCE_CANDIDATE.value,
            }:
                raise MontageLearningCanonicalAdmissionError("external anchor transition rejected")
            anchor_candidate = anchor_evaluation["proposed_anchor"]
            proposed_canonical = _build_canonical(
                manifest.project_manifest_sha256, proposed_ledger.to_dict(), anchor_candidate
            )
            canonical_bytes = canonical_json_bytes(proposed_canonical) + b"\n"
            target_manifest = self._target_manifest(manifest, canonical_bytes, processed_at)
            proposed_anchor = _build_anchor(
                proposed_canonical, anchor_candidate, target_manifest.project_manifest_sha256,
                target_manifest.project_revision,
            )
            status = ACCEPTED
            duplicate_of = None
        else:
            raise MontageLearningCanonicalAdmissionError("append decision is unsupported")
        receipt = _mint_receipt(
            readback=readback,
            commit=proposed_canonical["canonical_store_commit_sha256"],
            status=status,
            duplicate_of=duplicate_of,
            attempt=attempt,
            bridge_instance_id=self.bridge_instance_id,
            processed_at=processed_at,
        )
        proposed_registry = _append_registry(registry, receipt)
        journal: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "MONTAGE_LEARNING_CANONICAL_ADMISSION_TRANSACTION",
            "task_owner": TASK_OWNER,
            "operation": status,
            "project_id": manifest.project_id,
            "canonical_store_id": self.canonical_store_id,
            "owner_scope_hash": owner_scope_hash,
            "staging_readback_sha256": readback["readback_sha256"],
            "expected_previous_commit_sha256": current_commit,
            "expected_previous_anchor_document_sha256": current_anchor,
            "expected_previous_registry_sha256": registry["registry_sha256"] if self.receipt_path.exists() else None,
            "proposed_canonical": proposed_canonical,
            "proposed_anchor": proposed_anchor,
            "proposed_registry": proposed_registry,
            "target_manifest": target_manifest.to_dict(),
            "receipt_sha256": receipt["receipt_sha256"],
        }
        journal["journal_sha256"] = _hash(_JOURNAL_DOMAIN, journal)
        return _parse_journal(journal)

    def _participant(self, journal: Mapping[str, Any],
                     failure_hook: FailureHook | None = None) -> _AnchorParticipant:
        source_manifest_sha256 = str(journal["proposed_canonical"]["source_project_manifest_sha256"])
        return _AnchorParticipant(
            project_id=str(journal["project_id"]),
            anchor_path=self.anchor_path,
            recovery_path=self.anchor_recovery_path,
            expected_sha256=journal["expected_previous_anchor_document_sha256"],
            target_anchor=journal["proposed_anchor"],
            source_manifest_sha256=source_manifest_sha256,
            target_manifest_sha256=str(journal["target_manifest"]["project_manifest_sha256"]),
            failure_hook=failure_hook,
        )

    @contextmanager
    def _commit_guard(self, journal: Mapping[str, Any], raw: Mapping[str, Any], *,
                      staging_store_id: str, owner_scope_hash: str,
                      staging_revision: int, staging_entry_sha256: str) -> Iterator[None]:
        with exclusive_file_update_lock(self.anchor_path):
            self._validate_paths()
            readback = self._readback(
                raw, staging_store_id=staging_store_id,
                owner_scope_hash=owner_scope_hash,
                staging_revision=staging_revision,
                staging_entry_sha256=staging_entry_sha256,
            )
            if readback.to_dict()["readback_sha256"] != journal["staging_readback_sha256"]:
                raise MontageLearningCanonicalAdmissionError("staging changed before commit")
            live = ProductProjectManifestStore.load(self.project_root)
            source_sha = journal["proposed_canonical"]["source_project_manifest_sha256"]
            target_sha = journal["target_manifest"]["project_manifest_sha256"]
            if live.project_manifest_sha256 not in {source_sha, target_sha}:
                raise MontageLearningCanonicalAdmissionError("Project moved outside transaction")
            current_canonical = self._optional(self.canonical_path, _parse_canonical)
            current_anchor = self._optional(self.anchor_path, _parse_anchor)
            current_anchor_sha = None if current_anchor is None else current_anchor["external_anchor_document_sha256"]
            if current_anchor_sha not in {
                journal["expected_previous_anchor_document_sha256"],
                journal["proposed_anchor"]["external_anchor_document_sha256"],
            }:
                raise MontageLearningCanonicalAdmissionError("anchor changed outside transaction")
            current_commit = (None if current_canonical is None else
                              current_canonical["canonical_store_commit_sha256"])
            if (live.project_manifest_sha256 == source_sha and
                current_commit == journal["expected_previous_commit_sha256"] and
                current_anchor_sha == journal["expected_previous_anchor_document_sha256"]):
                recompiled = self._make_proposal(
                    raw,
                    staging_store_id=staging_store_id,
                    owner_scope_hash=owner_scope_hash,
                    staging_revision=staging_revision,
                    staging_entry_sha256=staging_entry_sha256,
                    expected_commit=journal["expected_previous_commit_sha256"],
                    expected_anchor=journal["expected_previous_anchor_document_sha256"],
                    processed_at=journal["proposed_registry"]["receipts"][-1]["processed_at"],
                )
                if recompiled != journal:
                    raise MontageLearningCanonicalAdmissionError("P1C-B/C/D recompile drifted")
            elif current_commit not in {
                journal["expected_previous_commit_sha256"],
                journal["proposed_canonical"]["canonical_store_commit_sha256"],
            }:
                raise MontageLearningCanonicalAdmissionError("canonical changed outside transaction")
            if not self.journal_path.exists():
                AtomicJsonWriter.write(self.journal_path, journal, validator=_parse_journal)
            elif _read(self.journal_path, _parse_journal) != journal:
                raise MontageLearningCanonicalAdmissionError("pending transaction conflicts")
            yield

    def _finish(self, journal: Mapping[str, Any], *, recovered: bool,
                failure_hook: FailureHook | None) -> MontageLearningCanonicalAdmissionResult:
        coordinator = ProductProjectSaveCoordinator()
        with self._locks():
            manifest = ProductProjectManifestStore.load(self.project_root)
            target_manifest = parse_product_project_manifest(journal["target_manifest"])
            if journal["operation"] == DUPLICATE:
                coordinator.require_current_integrity(self.project_root, manifest)
                if manifest.project_manifest_sha256 != target_manifest.project_manifest_sha256:
                    self._require_single_generic_manifest_advance_locked(journal, manifest)
            else:
                if manifest.project_manifest_sha256 != target_manifest.project_manifest_sha256:
                    raise MontageLearningCanonicalAdmissionError("target manifest is not committed")
                coordinator.require_current_integrity(self.project_root, target_manifest)
            canonical = _read(self.canonical_path, _parse_canonical)
            anchor = _read(self.anchor_path, _parse_anchor)
            if canonical != journal["proposed_canonical"] or anchor != journal["proposed_anchor"]:
                raise MontageLearningCanonicalAdmissionError("canonical/anchor read-back mismatch")
            registry = (None if not self.receipt_path.exists() else
                        _read(self.receipt_path, _parse_registry))
            expected_registry_sha = journal["expected_previous_registry_sha256"]
            proposed = journal["proposed_registry"]
            if journal["operation"] == DUPLICATE:
                if (
                    registry is None
                    or registry["registry_sha256"] != expected_registry_sha
                    or proposed["receipts"][:-1] != registry["receipts"]
                ):
                    raise MontageLearningCanonicalAdmissionError(
                        "duplicate receipt registry currentness mismatch"
                    )
                receipt_body = proposed["receipts"][-1]
                if (
                    receipt_body["status"] != DUPLICATE
                    or receipt_body["receipt_sha256"] != journal["receipt_sha256"]
                    or not any(
                        item["status"] == ACCEPTED
                        and item["receipt_sha256"]
                        == receipt_body["duplicate_of_receipt_sha256"]
                        for item in registry["receipts"]
                    )
                ):
                    raise MontageLearningCanonicalAdmissionError(
                        "duplicate receipt lineage changed"
                    )
                self.journal_path.unlink(missing_ok=True)
                return MontageLearningCanonicalAdmissionResult(
                    receipt=parse_montage_learning_admission_receipt(receipt_body),
                    canonical_store_commit_sha256=canonical[
                        "canonical_store_commit_sha256"
                    ],
                    external_anchor_document_sha256=anchor[
                        "external_anchor_document_sha256"
                    ],
                    recovered=recovered,
                )
            if registry is None:
                if expected_registry_sha is not None:
                    raise MontageLearningCanonicalAdmissionError("receipt registry disappeared")
            elif registry["registry_sha256"] not in {expected_registry_sha, proposed["registry_sha256"]}:
                raise MontageLearningCanonicalAdmissionError("receipt registry split brain")
            if registry != proposed:
                AtomicJsonWriter.write(self.receipt_path, proposed, validator=_parse_registry)
                if failure_hook is not None:
                    failure_hook("after_receipt_write", self.receipt_path)
            registry = _read(self.receipt_path, _parse_registry)
            if registry != proposed:
                raise MontageLearningCanonicalAdmissionError("receipt durable read-back failed")
            receipt_body = registry["receipts"][-1]
            if receipt_body["receipt_sha256"] != journal["receipt_sha256"]:
                raise MontageLearningCanonicalAdmissionError("receipt lineage changed")
            self.journal_path.unlink(missing_ok=True)
            return MontageLearningCanonicalAdmissionResult(
                receipt=parse_montage_learning_admission_receipt(receipt_body),
                canonical_store_commit_sha256=canonical["canonical_store_commit_sha256"],
                external_anchor_document_sha256=anchor["external_anchor_document_sha256"],
                recovered=recovered,
            )

    def _run_accepted(self, journal: Mapping[str, Any], raw: Mapping[str, Any], *,
                      staging_store_id: str, owner_scope_hash: str,
                      staging_revision: int, staging_entry_sha256: str,
                      failure_hook: FailureHook | None, recovered: bool) -> None:
        coordinator = ProductProjectSaveCoordinator()
        participant = self._participant(journal, failure_hook)
        target_manifest = parse_product_project_manifest(journal["target_manifest"])
        canonical_bytes = canonical_json_bytes(journal["proposed_canonical"]) + b"\n"

        def guard() -> Iterator[None]:
            return self._commit_guard(
                journal, raw,
                staging_store_id=staging_store_id,
                owner_scope_hash=owner_scope_hash,
                staging_revision=staging_revision,
                staging_entry_sha256=staging_entry_sha256,
            )

        status = coordinator.recovery_status(self.project_root)
        if status["required"]:
            coordinator.recover_complete(
                self.project_root,
                transaction_id=str(status["transaction_id"]),
                participant=participant,
                commit_guard=guard,
            )
        else:
            live = ProductProjectManifestStore.load(self.project_root)
            if live.project_manifest_sha256 != target_manifest.project_manifest_sha256:
                coordinator.save(
                    self.project_root,
                    target_manifest,
                    {CANONICAL_RELATIVE_PATH.as_posix(): canonical_bytes},
                    expected_previous_manifest_sha256=str(
                        journal["proposed_canonical"]["source_project_manifest_sha256"]
                    ),
                    participant=participant,
                    commit_guard=guard,
                )
        if failure_hook is not None:
            failure_hook(
                "after_project_save_committed" if not recovered else "after_project_save_recovered",
                self.canonical_path,
            )

    def admit_exact(
        self,
        delivery: Mapping[str, Any],
        *,
        staging_store_id: str,
        expected_owner_scope_hash: str,
        expected_staging_revision: int,
        expected_staging_entry_sha256: str,
        expected_canonical_store_commit_sha256: str | None,
        expected_external_anchor_document_sha256: str | None,
        failure_hook: FailureHook | None = None,
    ) -> MontageLearningCanonicalAdmissionResult:
        """Serialize one complete admission attempt on a stable lock inode."""
        # ``exclusive_file_update_lock`` locks the sibling ``.<name>.lock``.
        # The transaction journal itself may be atomically replaced/unlinked,
        # but this stable lock file is never a transaction payload and remains
        # locked through proposal, ProjectSave, receipt read-back and cleanup.
        with exclusive_file_update_lock(self.journal_path):
            return self._admit_exact_serialized(
                delivery,
                staging_store_id=staging_store_id,
                expected_owner_scope_hash=expected_owner_scope_hash,
                expected_staging_revision=expected_staging_revision,
                expected_staging_entry_sha256=expected_staging_entry_sha256,
                expected_canonical_store_commit_sha256=expected_canonical_store_commit_sha256,
                expected_external_anchor_document_sha256=expected_external_anchor_document_sha256,
                failure_hook=failure_hook,
            )

    def _admit_exact_serialized(
        self,
        delivery: Mapping[str, Any],
        *,
        staging_store_id: str,
        expected_owner_scope_hash: str,
        expected_staging_revision: int,
        expected_staging_entry_sha256: str,
        expected_canonical_store_commit_sha256: str | None,
        expected_external_anchor_document_sha256: str | None,
        failure_hook: FailureHook | None = None,
    ) -> MontageLearningCanonicalAdmissionResult:
        """Commit or recover one attempt while the stable operation lock is held."""
        if failure_hook is not None and not callable(failure_hook):
            raise TypeError("failure_hook must be callable")
        raw = _exact(delivery, "delivery", max_nodes=200_000)
        store_id = _identifier(staging_store_id, "staging_store_id")
        scope = _sha(expected_owner_scope_hash, "expected_owner_scope_hash")
        revision = _integer(expected_staging_revision, "expected_staging_revision", 1, 4096)
        entry_sha = _sha(expected_staging_entry_sha256, "expected_staging_entry_sha256")
        expected_commit = _sha(
            expected_canonical_store_commit_sha256,
            "expected_canonical_store_commit_sha256", nullable=True,
        )
        expected_anchor = _sha(
            expected_external_anchor_document_sha256,
            "expected_external_anchor_document_sha256", nullable=True,
        )
        recovered = False
        with self._locks():
            if self.journal_path.exists():
                journal = _read(self.journal_path, _parse_journal)
                recovered = True
                readback = self._readback(
                    raw, staging_store_id=store_id, owner_scope_hash=scope,
                    staging_revision=revision, staging_entry_sha256=entry_sha,
                )
                if (journal["staging_readback_sha256"] != readback.to_dict()["readback_sha256"] or
                    journal["owner_scope_hash"] != scope or
                    journal["expected_previous_commit_sha256"] != expected_commit or
                    journal["expected_previous_anchor_document_sha256"] != expected_anchor):
                    raise MontageLearningCanonicalAdmissionError("retry does not match pending transaction")
                journal = self._rebase_pending_exact_after_project_advance_locked(
                    journal,
                    raw,
                    staging_store_id=store_id,
                    owner_scope_hash=scope,
                    staging_revision=revision,
                    staging_entry_sha256=entry_sha,
                )
            else:
                journal = self._make_proposal(
                    raw,
                    staging_store_id=store_id,
                    owner_scope_hash=scope,
                    staging_revision=revision,
                    staging_entry_sha256=entry_sha,
                    expected_commit=expected_commit,
                    expected_anchor=expected_anchor,
                    processed_at=_now(),
                )
                if journal["operation"] == DUPLICATE:
                    AtomicJsonWriter.write(self.journal_path, journal, validator=_parse_journal)
                    if failure_hook is not None:
                        failure_hook("after_journal_write", self.journal_path)
        if journal["operation"] == ACCEPTED:
            self._run_accepted(
                journal, raw,
                staging_store_id=store_id,
                owner_scope_hash=scope,
                staging_revision=revision,
                staging_entry_sha256=entry_sha,
                failure_hook=failure_hook,
                recovered=recovered,
            )
        return self._finish(journal, recovered=recovered, failure_hook=failure_hook)

    def get_verified_receipt(
        self, *, receipt_sha256: str | None = None,
    ) -> MontageLearningVerifiedAdmissionReceipt:
        """Return a sealed receipt only after canonical currentness revalidation."""
        wanted = _sha(receipt_sha256, "receipt_sha256", nullable=True)
        coordinator = ProductProjectSaveCoordinator()
        with self._locks():
            if self.journal_path.exists() or coordinator.recovery_status(self.project_root)["required"]:
                raise MontageLearningCanonicalAdmissionError("canonical recovery is pending")
            manifest = ProductProjectManifestStore.load(self.project_root)
            coordinator.require_current_integrity(self.project_root, manifest)
            canonical = _read(self.canonical_path, _parse_canonical)
            anchor = _read(self.anchor_path, _parse_anchor)
            registry = _read(self.receipt_path, _parse_registry)
            binding = next((item for item in manifest.child_bindings
                            if item.identity == (TASK_OWNER, CANONICAL_RELATIVE_PATH.as_posix())), None)
            canonical_bytes = canonical_json_bytes(canonical) + b"\n"
            if (binding is None or binding.format_id != CANONICAL_FORMAT_ID or
                binding.format_version != CANONICAL_FORMAT_VERSION or
                binding.content_sha256 != sha256_bytes(canonical_bytes) or
                manifest.project_revision < anchor["target_project_manifest_revision"] or
                anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
                anchor["anchor"]["anchor_sha256"] != canonical["external_anchor_sha256"]):
                raise MontageLearningCanonicalAdmissionError("canonical currentness mismatch")
            matches = [item for item in registry["receipts"]
                       if wanted is None or item["receipt_sha256"] == wanted]
            if len(matches) != 1 and wanted is not None:
                raise MontageLearningCanonicalAdmissionError("receipt is not uniquely present")
            if wanted is None:
                if not registry["receipts"]:
                    raise MontageLearningCanonicalAdmissionError("receipt registry is empty")
                matches = [registry["receipts"][-1]]
            selected = matches[0]
            if selected["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"]:
                raise MontageLearningCanonicalAdmissionError("receipt is not current")
            return MontageLearningVerifiedAdmissionReceipt(
                parse_montage_learning_admission_receipt(selected),
                manifest.project_manifest_sha256,
                anchor["external_anchor_document_sha256"],
                _token=_VERIFIED_TOKEN,
            )

    @staticmethod
    def _generic_project_scope_hash(project_id: str) -> str:
        return _domain_hash(_GENERIC_PROJECT_SCOPE_DOMAIN, {"project_id": project_id})

    @staticmethod
    def _generic_marker_relative_path(transaction_id: str) -> str:
        _bare_sha(transaction_id, "transaction_id")
        return (GENERIC_OBSERVATION_MARKER_DIRECTORY / f"{transaction_id}.json").as_posix()

    def _load_manifest_pinned(self) -> ProductProjectManifest:
        document = _read(
            ProductProjectManifestStore.path(self.project_root),
            lambda value: parse_product_project_manifest(value).to_dict(),
        )
        return parse_product_project_manifest(document)

    @staticmethod
    def _generic_binding_for_ledger(ledger_document: bytes) -> ProjectChildBinding:
        return ProjectChildBinding(
            TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix(),
            GENERIC_OBSERVATION_FORMAT_ID, GENERIC_OBSERVATION_FORMAT_VERSION,
            sha256_bytes(ledger_document), True,
        )

    @staticmethod
    def _generic_payload_binding(relative_path: str, document: bytes) -> ProjectChildBinding:
        return ProjectChildBinding(
            TASK_OWNER, relative_path, GENERIC_OBSERVATION_OBJECT_FORMAT_ID,
            GENERIC_OBSERVATION_FORMAT_VERSION, sha256_bytes(document), True,
        )

    @staticmethod
    def _generic_target_manifest_v1(
        source: ProductProjectManifest, ledger_document: bytes,
        payload_relative_path: str, payload_document: bytes, *, updated_at: str,
    ) -> ProductProjectManifest:
        replacements = {
            (TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix()):
                MontageLearningCanonicalAdmissionTransactionStore._generic_binding_for_ledger(
                    ledger_document
                ),
            (TASK_OWNER, payload_relative_path):
                MontageLearningCanonicalAdmissionTransactionStore._generic_payload_binding(
                    payload_relative_path, payload_document
                ),
        }
        bindings = [item for item in source.child_bindings if item.identity not in replacements]
        bindings.extend(replacements.values())
        return ProductProjectManifest.create(
            project_id=source.project_id,
            project_revision=source.project_revision + 1,
            product_version=source.product_version,
            timebase=source.timebase,
            child_bindings=bindings,
            created_at=source.created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _generic_make_readback(
        marker: Mapping[str, Any], binding: ProjectChildBinding,
    ) -> dict[str, Any]:
        marker_body = _parse_generic_marker_v1(marker)
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationCanonicalReadback",
            "transaction_id": marker_body["transaction_id"],
            "record_id": marker_body["record_id"],
            "source_digest_sha256": marker_body["source_digest_sha256"],
            "project_scope_hash": marker_body["project_scope_hash"],
            "owner_scope_hash": marker_body["owner_scope_hash"],
            "product_project_manifest_id": marker_body["product_project_manifest_id"],
            "product_project_manifest_revision": marker_body["product_project_manifest_revision"],
            "product_project_manifest_sha256": marker_body["product_project_manifest_sha256"],
            "child_binding": binding.to_dict(),
            "child_binding_sha256": marker_body["child_binding_sha256"],
            "store_kind": "REVIEW_OBSERVATION",
            "store_revision": marker_body["store_revision"],
            "payload_object_sha256": marker_body["payload_object_sha256"],
            "previous_ledger_head_sha256": marker_body["previous_ledger_head_sha256"],
            "ledger_head_sha256": marker_body["ledger_head_sha256"],
            "marker_body_sha256": marker_body["marker_body_sha256"],
            "marker_self_hash": marker_body["marker_self_hash"],
            "canonical_commit_sha256": marker_body["canonical_commit_sha256"],
            "admission_timestamp": marker_body["admission_timestamp"],
            "anchor_coordinate": None,
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
        }
        body["internal_receipt_self_hash"] = _domain_hash(
            _GENERIC_INTERNAL_RECEIPT_DOMAIN, body
        )
        return _parse_generic_readback_v1(body)

    @staticmethod
    def _generic_make_result(
        outcome: str, readback: Mapping[str, Any],
        current_manifest: ProductProjectManifest, current_binding: ProjectChildBinding,
        current_ledger: Mapping[str, Any],
    ) -> ReviewObservationAdmissionResult:
        if outcome not in {ACCEPTED, DUPLICATE}:
            raise MontageLearningCanonicalAdmissionError("generic operation outcome invalid")
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationAdmissionResult",
            "operation_outcome": outcome,
            "canonical_readback": _parse_generic_readback_v1(readback),
            "store_kind": "REVIEW_OBSERVATION",
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
            "current_product_project_manifest_revision": current_manifest.project_revision,
            "current_product_project_manifest_sha256": _as_bare_sha(
                current_manifest.project_manifest_sha256
            ),
            "current_child_binding_sha256": _generic_child_binding_sha256(
                current_binding.to_dict()
            ),
            "current_store_revision": current_ledger["store_revision"],
            "current_ledger_head_sha256": current_ledger["ledger_head_sha256"],
            "durable_readback_verified": True,
        }
        body["operation_result_self_hash"] = _domain_hash(
            _GENERIC_OPERATION_RESULT_DOMAIN, body
        )
        return ReviewObservationAdmissionResult._from_dict(body)

    def _generic_load_current_v1(
        self, manifest: ProductProjectManifest, *,
        project_scope_hash: str, owner_scope_hash: str,
    ) -> tuple[dict[str, Any], ProjectChildBinding] | None:
        binding = next((
            item for item in manifest.child_bindings
            if item.identity == (TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix())
        ), None)
        if binding is None:
            if self.generic_observation_path.exists():
                raise MontageLearningCanonicalAdmissionError("unbound generic ledger exists")
            return None
        if (
            binding.format_id != GENERIC_OBSERVATION_FORMAT_ID
            or binding.format_version != GENERIC_OBSERVATION_FORMAT_VERSION
            or binding.required is not True
            or binding.dependency_hashes != ()
        ):
            raise MontageLearningCanonicalAdmissionError("generic ledger binding mismatch")
        ledger = _read(self.generic_observation_path, _parse_generic_ledger_v1)
        if (
            binding.content_sha256 != sha256_bytes(canonical_json_bytes(ledger) + b"\n")
            or ledger["project_id"] != manifest.project_id
            or ledger["project_scope_hash"] != project_scope_hash
            or ledger["owner_scope_hash"] != owner_scope_hash
        ):
            raise MontageLearningCanonicalAdmissionError("generic ledger currentness mismatch")
        return ledger, binding

    @staticmethod
    def _generic_prefix_ledger(
        current_ledger: Mapping[str, Any], revision: int,
    ) -> dict[str, Any]:
        return _parse_generic_ledger_v1({
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationLedger",
            "project_id": current_ledger["project_id"],
            "project_scope_hash": current_ledger["project_scope_hash"],
            "owner_scope_hash": current_ledger["owner_scope_hash"],
            "store_kind": "REVIEW_OBSERVATION",
            "store_revision": revision,
            "entries": list(current_ledger["entries"][:revision]),
            "ledger_head_sha256": current_ledger["entries"][revision - 1]["ledger_head_sha256"],
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
        })

    def _generic_trusted_readback_locked(
        self, readback: Mapping[str, Any], *,
        current_manifest: ProductProjectManifest | None = None,
    ) -> tuple[dict[str, Any], ProductProjectManifest, ProjectChildBinding, dict[str, Any]]:
        anchored = _parse_generic_readback_v1(readback)
        manifest = self._load_manifest_pinned() if current_manifest is None else current_manifest
        if manifest.project_id != anchored["product_project_manifest_id"]:
            raise MontageLearningCanonicalAdmissionError("generic Project identity changed")
        if manifest.project_revision < anchored["product_project_manifest_revision"]:
            raise MontageLearningCanonicalAdmissionError("generic manifest rollback detected")
        if (
            manifest.project_revision == anchored["product_project_manifest_revision"]
            and _as_bare_sha(manifest.project_manifest_sha256)
            != anchored["product_project_manifest_sha256"]
        ):
            raise MontageLearningCanonicalAdmissionError("generic anchored manifest mismatch")
        current = self._generic_load_current_v1(
            manifest,
            project_scope_hash=anchored["project_scope_hash"],
            owner_scope_hash=anchored["owner_scope_hash"],
        )
        if current is None:
            raise MontageLearningCanonicalAdmissionError("generic ledger is absent")
        ledger, binding = current
        revision = anchored["store_revision"]
        if ledger["store_revision"] < revision:
            raise MontageLearningCanonicalAdmissionError("generic store rollback detected")
        rebuilt_readbacks: list[dict[str, Any]] = []
        for entry_revision, current_entry in enumerate(ledger["entries"], start=1):
            prefix = self._generic_prefix_ledger(ledger, entry_revision)
            prefix_document = canonical_json_bytes(prefix) + b"\n"
            prefix_binding = self._generic_binding_for_ledger(prefix_document)
            payload_relative = (
                GENERIC_OBSERVATION_OBJECT_DIRECTORY /
                f"{current_entry['payload_object_sha256']}.json"
            ).as_posix()
            payload_path = self.project_root / payload_relative
            payload = _read(payload_path, _parse_generic_object_v1)
            payload_document = canonical_json_bytes(payload) + b"\n"
            if (
                payload["payload_object_sha256"]
                != current_entry["payload_object_sha256"]
                or payload["record_id"] != current_entry["record_id"]
                or payload["source_digest_sha256"]
                != current_entry["source_digest_sha256"]
            ):
                raise MontageLearningCanonicalAdmissionError(
                    "generic payload/ledger entry mismatch"
                )
            payload_binding = next((
                item for item in manifest.child_bindings
                if item.identity == (TASK_OWNER, payload_relative)
            ), None)
            expected_payload_binding = self._generic_payload_binding(
                payload_relative, payload_document
            )
            if (
                payload_binding is None
                or payload_binding.to_dict() != expected_payload_binding.to_dict()
            ):
                raise MontageLearningCanonicalAdmissionError(
                    "generic payload Project binding mismatch"
                )
            marker = _read(
                self.project_root /
                self._generic_marker_relative_path(current_entry["transaction_id"]),
                _parse_generic_marker_v1,
            )
            for left, right in (
                (marker["transaction_id"], current_entry["transaction_id"]),
                (marker["record_id"], current_entry["record_id"]),
                (marker["source_digest_sha256"], current_entry["source_digest_sha256"]),
                (marker["project_scope_hash"], current_entry["project_scope_hash"]),
                (marker["owner_scope_hash"], current_entry["owner_scope_hash"]),
                (marker["store_revision"], current_entry["store_revision"]),
                (marker["payload_object_sha256"], current_entry["payload_object_sha256"]),
                (
                    marker["previous_ledger_head_sha256"],
                    current_entry["previous_ledger_head_sha256"],
                ),
                (marker["ledger_head_sha256"], current_entry["ledger_head_sha256"]),
                (marker["admission_timestamp"], current_entry["admission_timestamp"]),
                (marker["product_project_manifest_id"], manifest.project_id),
                (
                    marker["child_binding_sha256"],
                    _generic_child_binding_sha256(prefix_binding.to_dict()),
                ),
            ):
                if left != right:
                    raise MontageLearningCanonicalAdmissionError(
                        "generic marker/ledger entry mismatch"
                    )
            if marker["product_project_manifest_revision"] > manifest.project_revision:
                raise MontageLearningCanonicalAdmissionError(
                    "generic marker manifest revision is from the future"
                )
            if (
                marker["product_project_manifest_revision"] == manifest.project_revision
                and marker["product_project_manifest_sha256"]
                != _as_bare_sha(manifest.project_manifest_sha256)
            ):
                raise MontageLearningCanonicalAdmissionError(
                    "generic marker current manifest mismatch"
                )
            rebuilt_readbacks.append(self._generic_make_readback(marker, prefix_binding))

        entry = ledger["entries"][revision - 1]
        for left, right in (
            (entry["transaction_id"], anchored["transaction_id"]),
            (entry["record_id"], anchored["record_id"]),
            (entry["source_digest_sha256"], anchored["source_digest_sha256"]),
            (entry["payload_object_sha256"], anchored["payload_object_sha256"]),
            (entry["previous_ledger_head_sha256"], anchored["previous_ledger_head_sha256"]),
            (entry["ledger_head_sha256"], anchored["ledger_head_sha256"]),
            (entry["admission_timestamp"], anchored["admission_timestamp"]),
        ):
            if left != right:
                raise MontageLearningCanonicalAdmissionError("generic anchored ledger entry changed")
        prefix = self._generic_prefix_ledger(ledger, revision)
        anchored_binding = self._generic_binding_for_ledger(canonical_json_bytes(prefix) + b"\n")
        if (
            anchored_binding.to_dict() != anchored["child_binding"]
            or _generic_child_binding_sha256(anchored_binding.to_dict())
            != anchored["child_binding_sha256"]
        ):
            raise MontageLearningCanonicalAdmissionError("generic anchored child binding changed")
        rebuilt = rebuilt_readbacks[revision - 1]
        if rebuilt != anchored:
            raise MontageLearningCanonicalAdmissionError("generic marker/readback mismatch")
        return anchored, manifest, binding, ledger

    def _generic_result_from_readback(
        self, outcome: str, readback: Mapping[str, Any],
    ) -> ReviewObservationAdmissionResult:
        with _exclusive_project_lock(ProductProjectManifestStore.path(self.project_root)):
            anchored, manifest, binding, ledger = self._generic_trusted_readback_locked(readback)
            return self._generic_make_result(outcome, anchored, manifest, binding, ledger)

    @staticmethod
    def _generic_payload_for(
        raw: Mapping[str, Any], candidate: Any,
    ) -> tuple[dict[str, Any], bytes, str]:
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationPayloadObject",
            "record_id": candidate.record_id,
            "source_digest_sha256": _as_bare_sha(candidate.source_sha256),
            "source_delivery": dict(raw),
            "source_delivery_sha256": _as_bare_sha(
                sha256_bytes(canonical_json_bytes(raw))
            ),
            "store_kind": "REVIEW_OBSERVATION",
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
        }
        body["payload_object_sha256"] = _domain_hash(
            "BVP_REVIEW_OBSERVATION_PAYLOAD_OBJECT_V1", body
        )
        payload = _parse_generic_object_v1(body)
        document = canonical_json_bytes(payload) + b"\n"
        relative = (
            GENERIC_OBSERVATION_OBJECT_DIRECTORY /
            f"{payload['payload_object_sha256']}.json"
        ).as_posix()
        return payload, document, relative

    def _generic_duplicate_v1(
        self, raw: Mapping[str, Any], candidate: Any,
        current: tuple[dict[str, Any], ProjectChildBinding] | None,
    ) -> ReviewObservationAdmissionResult | None:
        if current is None:
            return None
        ledger, _ = current
        matches = [entry for entry in ledger["entries"] if entry["record_id"] == candidate.record_id]
        if not matches:
            return None
        entry = matches[0]
        payload = self._generic_payload_for(raw, candidate)[0]
        if (
            entry["source_digest_sha256"] != _as_bare_sha(candidate.source_sha256)
            or entry["payload_object_sha256"] != payload["payload_object_sha256"]
        ):
            raise MontageLearningCanonicalAdmissionError("generic record identity collision")
        marker = _read(
            self.project_root / self._generic_marker_relative_path(entry["transaction_id"]),
            _parse_generic_marker_v1,
        )
        anchored_binding = self._generic_binding_for_ledger(
            canonical_json_bytes(self._generic_prefix_ledger(ledger, entry["store_revision"]))
            + b"\n"
        )
        return self._generic_result_from_readback(
            DUPLICATE, self._generic_make_readback(marker, anchored_binding)
        )

    def _generic_prepare_v1(
        self, raw: Mapping[str, Any], candidate: Any,
        manifest: ProductProjectManifest,
        current: tuple[dict[str, Any], ProjectChildBinding] | None,
        *, owner_scope_hash: str, admission_timestamp: str | None = None,
    ) -> tuple[dict[str, Any], ProductProjectManifest, dict[str, bytes], dict[str, Any]]:
        project_scope = self._generic_project_scope_hash(manifest.project_id)
        owner_scope = _as_bare_sha(owner_scope_hash)
        source_digest = _as_bare_sha(candidate.source_sha256)
        transaction_id = _domain_hash(
            _GENERIC_TRANSACTION_DOMAIN_V1,
            {
                "project_scope_hash": project_scope,
                "owner_scope_hash": owner_scope,
                "record_id": candidate.record_id,
                "source_digest_sha256": source_digest,
            },
        )
        timestamp = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if admission_timestamp is None
            else _parse_generic_timestamp(admission_timestamp, "admission_timestamp")
        )
        payload, payload_document, payload_relative = self._generic_payload_for(raw, candidate)
        prior_entries = [] if current is None else list(current[0]["entries"])
        previous_head = _generic_empty_head() if current is None else current[0]["ledger_head_sha256"]
        revision = len(prior_entries) + 1
        entry: dict[str, Any] = {
            "store_revision": revision,
            "transaction_id": transaction_id,
            "record_id": candidate.record_id,
            "source_digest_sha256": source_digest,
            "project_scope_hash": project_scope,
            "owner_scope_hash": owner_scope,
            "payload_object_sha256": payload["payload_object_sha256"],
            "admission_timestamp": timestamp,
            "previous_ledger_head_sha256": previous_head,
        }
        entry["ledger_head_sha256"] = _domain_hash(_GENERIC_ENTRY_DOMAIN, entry)
        ledger = _parse_generic_ledger_v1({
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationLedger",
            "project_id": manifest.project_id,
            "project_scope_hash": project_scope,
            "owner_scope_hash": owner_scope,
            "store_kind": "REVIEW_OBSERVATION",
            "store_revision": revision,
            "entries": [*prior_entries, entry],
            "ledger_head_sha256": entry["ledger_head_sha256"],
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
        })
        ledger_document = canonical_json_bytes(ledger) + b"\n"
        target = self._generic_target_manifest_v1(
            manifest, ledger_document, payload_relative, payload_document,
            updated_at=timestamp,
        )
        ledger_binding = next(
            item for item in target.child_bindings
            if item.identity == (TASK_OWNER, GENERIC_OBSERVATION_RELATIVE_PATH.as_posix())
        )
        marker_body = {
            "transaction_id": transaction_id,
            "record_id": candidate.record_id,
            "source_digest_sha256": source_digest,
            "project_scope_hash": project_scope,
            "owner_scope_hash": owner_scope,
            "product_project_manifest_id": target.project_id,
            "product_project_manifest_revision": target.project_revision,
            "product_project_manifest_sha256": _as_bare_sha(target.project_manifest_sha256),
            "child_binding_sha256": _generic_child_binding_sha256(ledger_binding.to_dict()),
            "store_kind": "REVIEW_OBSERVATION",
            "store_revision": revision,
            "payload_object_sha256": payload["payload_object_sha256"],
            "previous_ledger_head_sha256": previous_head,
            "ledger_head_sha256": entry["ledger_head_sha256"],
            "admission_timestamp": timestamp,
        }
        marker: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationCommitMarker",
            **marker_body,
        }
        marker["marker_body_sha256"] = _domain_hash(_GENERIC_MARKER_BODY_DOMAIN, marker_body)
        marker["canonical_commit_sha256"] = _domain_hash(
            _GENERIC_COMMIT_DOMAIN_V1,
            {**marker_body, "marker_body_sha256": marker["marker_body_sha256"]},
        )
        marker["marker_self_hash"] = _domain_hash(_GENERIC_MARKER_SELF_DOMAIN, marker)
        marker = _parse_generic_marker_v1(marker)
        readback = self._generic_make_readback(marker, ledger_binding)
        journal: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationAdmissionJournal",
            "state": "PREPARED",
            "journal_revision": 1,
            "previous_journal_sha256": None,
            "transaction_id": transaction_id,
            "project_id": manifest.project_id,
            "project_scope_hash": project_scope,
            "owner_scope_hash": owner_scope,
            "source_project_manifest_revision": manifest.project_revision,
            "source_project_manifest_sha256": _as_bare_sha(manifest.project_manifest_sha256),
            "target_project_manifest_revision": target.project_revision,
            "target_project_manifest_sha256": _as_bare_sha(target.project_manifest_sha256),
            "record_id": candidate.record_id,
            "source_digest_sha256": source_digest,
            "source_delivery_sha256": _as_bare_sha(sha256_bytes(canonical_json_bytes(raw))),
            "payload_object_relative_path": payload_relative,
            "payload_object_sha256": payload["payload_object_sha256"],
            "payload_document_sha256": _as_bare_sha(sha256_bytes(payload_document)),
            "ledger_document_sha256": _as_bare_sha(sha256_bytes(ledger_document)),
            "store_revision": revision,
            "previous_ledger_head_sha256": previous_head,
            "ledger_head_sha256": entry["ledger_head_sha256"],
            "marker_relative_path": self._generic_marker_relative_path(transaction_id),
            "marker_body_sha256": marker["marker_body_sha256"],
            "marker_self_hash": marker["marker_self_hash"],
            "canonical_commit_sha256": marker["canonical_commit_sha256"],
            "admission_timestamp": timestamp,
            "canonical_readback": readback,
            "learning_adopted": False,
            "profile_promoted": False,
            "timeline_mutated": False,
        }
        journal["journal_sha256"] = _domain_hash(
            "BVP_REVIEW_OBSERVATION_JOURNAL_V1", journal
        )
        journal = _parse_generic_journal_v1(journal)
        return journal, target, {
            GENERIC_OBSERVATION_RELATIVE_PATH.as_posix(): ledger_document,
            payload_relative: payload_document,
        }, marker

    @staticmethod
    def _generic_marker_from_readback(readback: Mapping[str, Any]) -> dict[str, Any]:
        body = _parse_generic_readback_v1(readback)
        marker = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "ReviewObservationCommitMarker",
            **{
                name: body[name] for name in (
                    "transaction_id", "record_id", "source_digest_sha256",
                    "project_scope_hash", "owner_scope_hash",
                    "product_project_manifest_id", "product_project_manifest_revision",
                    "product_project_manifest_sha256", "child_binding_sha256",
                    "store_kind", "store_revision", "payload_object_sha256",
                    "previous_ledger_head_sha256", "ledger_head_sha256",
                    "admission_timestamp", "marker_body_sha256", "marker_self_hash",
                    "canonical_commit_sha256",
                )
            },
        }
        return _parse_generic_marker_v1(marker)

    def _generic_transition_journal(
        self, journal: Mapping[str, Any], target_state: str,
    ) -> dict[str, Any]:
        current = _read(self.generic_journal_path, _parse_generic_journal_v1)
        if current != journal:
            raise MontageLearningCanonicalAdmissionError("generic journal CAS mismatch")
        order = [
            "PREPARED", "PAYLOAD_WRITTEN", "LEDGER_COMMITTED",
            "MANIFEST_COMMITTED", "MARKER_COMMITTED", "READBACK_VERIFIED",
        ]
        if target_state not in order or current["state"] not in order:
            raise MontageLearningCanonicalAdmissionError("generic journal transition invalid")
        if order.index(target_state) != order.index(current["state"]) + 1:
            raise MontageLearningCanonicalAdmissionError("generic journal transition skipped")
        updated = dict(current)
        updated["state"] = target_state
        updated["journal_revision"] = current["journal_revision"] + 1
        updated["previous_journal_sha256"] = current["journal_sha256"]
        updated.pop("journal_sha256")
        updated["journal_sha256"] = _domain_hash(
            "BVP_REVIEW_OBSERVATION_JOURNAL_V1", updated
        )
        parsed = _parse_generic_journal_v1(updated)
        AtomicJsonWriter.write(
            self.generic_journal_path, parsed, validator=_parse_generic_journal_v1
        )
        if _read(self.generic_journal_path, _parse_generic_journal_v1) != parsed:
            raise MontageLearningCanonicalAdmissionError("generic journal transition read-back failed")
        return parsed

    def _generic_finish_v1(
        self, journal: Mapping[str, Any], marker: Mapping[str, Any], *,
        failure_hook: FailureHook | None,
    ) -> ReviewObservationAdmissionResult:
        journal = _parse_generic_journal_v1(journal)
        marker = _parse_generic_marker_v1(marker)
        order = [
            "PREPARED", "PAYLOAD_WRITTEN", "LEDGER_COMMITTED",
            "MANIFEST_COMMITTED", "MARKER_COMMITTED", "READBACK_VERIFIED",
        ]
        if journal["state"] not in order:
            raise MontageLearningCanonicalAdmissionError("generic journal is terminally aborted")
        payload = _read(
            self.project_root / journal["payload_object_relative_path"],
            _parse_generic_object_v1,
        )
        if (
            payload["payload_object_sha256"] != journal["payload_object_sha256"]
            or _as_bare_sha(sha256_bytes(canonical_json_bytes(payload) + b"\n"))
            != journal["payload_document_sha256"]
        ):
            raise MontageLearningCanonicalAdmissionError("generic payload commit mismatch")
        if order.index(journal["state"]) < order.index("PAYLOAD_WRITTEN"):
            journal = self._generic_transition_journal(journal, "PAYLOAD_WRITTEN")
        ledger = _read(self.generic_observation_path, _parse_generic_ledger_v1)
        if (
            ledger["store_revision"] < journal["store_revision"]
            or ledger["entries"][journal["store_revision"] - 1]["transaction_id"]
            != journal["transaction_id"]
        ):
            raise MontageLearningCanonicalAdmissionError("generic ledger commit mismatch")
        if order.index(journal["state"]) < order.index("LEDGER_COMMITTED"):
            journal = self._generic_transition_journal(journal, "LEDGER_COMMITTED")
        manifest = self._load_manifest_pinned()
        if (
            manifest.project_revision < journal["target_project_manifest_revision"]
            or (
                manifest.project_revision == journal["target_project_manifest_revision"]
                and _as_bare_sha(manifest.project_manifest_sha256)
                != journal["target_project_manifest_sha256"]
            )
        ):
            raise MontageLearningCanonicalAdmissionError("generic manifest commit mismatch")
        if order.index(journal["state"]) < order.index("MANIFEST_COMMITTED"):
            journal = self._generic_transition_journal(journal, "MANIFEST_COMMITTED")
        marker_path = self.project_root / journal["marker_relative_path"]
        if marker_path.exists():
            if _read(marker_path, _parse_generic_marker_v1) != marker:
                raise MontageLearningCanonicalAdmissionError("generic marker collision")
        else:
            AtomicJsonWriter.write(marker_path, marker, validator=_parse_generic_marker_v1)
        if _read(marker_path, _parse_generic_marker_v1) != marker:
            raise MontageLearningCanonicalAdmissionError("generic marker durable read-back failed")
        if failure_hook is not None:
            failure_hook("after_generic_marker_write", marker_path)
        if order.index(journal["state"]) < order.index("MARKER_COMMITTED"):
            journal = self._generic_transition_journal(journal, "MARKER_COMMITTED")
        result = self._generic_result_from_readback(ACCEPTED, journal["canonical_readback"])
        if order.index(journal["state"]) < order.index("READBACK_VERIFIED"):
            journal = self._generic_transition_journal(journal, "READBACK_VERIFIED")
        if failure_hook is not None:
            failure_hook("before_generic_journal_cleanup", self.generic_journal_path)
        self.generic_journal_path.unlink()
        return result

    def _generic_recover_v1_locked(
        self, raw: Mapping[str, Any], candidate: Any, *,
        owner_scope_hash: str, failure_hook: FailureHook | None,
    ) -> ReviewObservationAdmissionResult:
        journal = _read(self.generic_journal_path, _parse_generic_journal_v1)
        if (
            journal["record_id"] != candidate.record_id
            or journal["source_digest_sha256"] != _as_bare_sha(candidate.source_sha256)
            or journal["owner_scope_hash"] != _as_bare_sha(owner_scope_hash)
            or journal["source_delivery_sha256"]
            != _as_bare_sha(sha256_bytes(canonical_json_bytes(raw)))
        ):
            raise MontageLearningCanonicalAdmissionError("generic recovery source mismatch")
        coordinator = ProductProjectSaveCoordinator()
        status = coordinator.recovery_status(self.project_root)
        if status["required"]:
            coordinator.recover_complete(self.project_root, transaction_id=status["transaction_id"])
        manifest = self._load_manifest_pinned()
        current = self._generic_load_current_v1(
            manifest,
            project_scope_hash=journal["project_scope_hash"],
            owner_scope_hash=journal["owner_scope_hash"],
        )
        committed_entry = None if current is None else next((
            entry for entry in current[0]["entries"]
            if entry["transaction_id"] == journal["transaction_id"]
        ), None)
        if committed_entry is None:
            if journal["state"] != "PREPARED":
                raise MontageLearningCanonicalAdmissionError(
                    "generic non-PREPARED journal has no committed ledger entry"
                )
            rebuilt, target, documents, marker = self._generic_prepare_v1(
                raw, candidate, manifest, current,
                owner_scope_hash="sha256:" + journal["owner_scope_hash"],
                admission_timestamp=journal["admission_timestamp"],
            )
            for name in (
                "transaction_id", "record_id", "source_digest_sha256",
                "source_delivery_sha256", "project_scope_hash", "owner_scope_hash",
                "payload_object_relative_path", "payload_object_sha256",
                "payload_document_sha256", "admission_timestamp",
            ):
                if rebuilt[name] != journal[name]:
                    raise MontageLearningCanonicalAdmissionError(
                        "generic recovery operation identity changed"
                    )
            if (
                rebuilt["source_project_manifest_sha256"]
                != journal["source_project_manifest_sha256"]
            ):
                rebuilt["journal_revision"] = journal["journal_revision"] + 1
                rebuilt["previous_journal_sha256"] = journal["journal_sha256"]
                rebuilt["journal_sha256"] = _domain_hash(
                    "BVP_REVIEW_OBSERVATION_JOURNAL_V1",
                    _without(rebuilt, "journal_sha256"),
                )
                rebuilt = _parse_generic_journal_v1(rebuilt)
                AtomicJsonWriter.write(
                    self.generic_journal_path, rebuilt,
                    validator=_parse_generic_journal_v1,
                )
                if _read(
                    self.generic_journal_path, _parse_generic_journal_v1
                ) != rebuilt:
                    raise MontageLearningCanonicalAdmissionError(
                        "generic rebased PREPARED journal read-back failed"
                    )
                journal = rebuilt
            coordinator.save(
                self.project_root, target, documents,
                expected_previous_manifest_sha256=manifest.project_manifest_sha256,
            )
        else:
            if (
                committed_entry["store_revision"] != journal["store_revision"]
                or committed_entry["record_id"] != journal["record_id"]
                or committed_entry["source_digest_sha256"] != journal["source_digest_sha256"]
                or committed_entry["payload_object_sha256"] != journal["payload_object_sha256"]
                or committed_entry["ledger_head_sha256"] != journal["ledger_head_sha256"]
            ):
                raise MontageLearningCanonicalAdmissionError(
                    "generic recovery committed entry mismatch"
                )
            marker = self._generic_marker_from_readback(journal["canonical_readback"])
        return self._generic_finish_v1(journal, marker, failure_hook=failure_hook)

    def admit_generic_observation(
        self, delivery: Mapping[str, Any], *, expected_revision: int,
        generic_store_id: str = "task058-generic-review-observations",
        owner_scope_hash: str = _GENERIC_UNBOUND_OWNER_SCOPE,
        failure_hook: FailureHook | None = None,
    ) -> ReviewObservationAdmissionResult:
        raw = _exact(delivery, "generic delivery", max_nodes=200_000)
        candidate = validate_generic_learning_delivery(raw)
        if _identifier(generic_store_id, "generic_store_id") != "task058-generic-review-observations":
            raise MontageLearningCanonicalAdmissionError("generic store identity is fixed")
        scope = _sha(owner_scope_hash, "owner_scope_hash")
        expected = _integer(expected_revision, "expected_revision", 0, _MAX_RECEIPTS - 1)
        if failure_hook is not None and not callable(failure_hook):
            raise TypeError("failure_hook must be callable")
        with exclusive_file_update_lock(self.generic_journal_path):
            if self.generic_journal_path.exists():
                return self._generic_recover_v1_locked(
                    raw, candidate, owner_scope_hash=scope, failure_hook=failure_hook
                )
            manifest = self._load_manifest_pinned()
            current = self._generic_load_current_v1(
                manifest,
                project_scope_hash=self._generic_project_scope_hash(manifest.project_id),
                owner_scope_hash=_as_bare_sha(scope),
            )
            revision = 0 if current is None else current[0]["store_revision"]
            if revision != expected:
                raise MontageLearningCanonicalAdmissionError("generic CAS is stale")
            duplicate = self._generic_duplicate_v1(raw, candidate, current)
            if duplicate is not None:
                return duplicate
            journal, target, documents, marker = self._generic_prepare_v1(
                raw, candidate, manifest, current, owner_scope_hash=scope
            )
            AtomicJsonWriter.write(
                self.generic_journal_path, journal, validator=_parse_generic_journal_v1
            )
            if failure_hook is not None:
                failure_hook("after_generic_journal_write", self.generic_journal_path)
            ProductProjectSaveCoordinator().save(
                self.project_root, target, documents,
                expected_previous_manifest_sha256=manifest.project_manifest_sha256,
            )
            if failure_hook is not None:
                failure_hook("after_generic_project_commit", self.generic_observation_path)
            return self._generic_finish_v1(journal, marker, failure_hook=failure_hook)

    def record_exact_generic_observation(
        self, delivery: Mapping[str, Any], *, expected_revision: int,
        generic_store_id: str = "task058-generic-review-observations",
        owner_scope_hash: str = _GENERIC_UNBOUND_OWNER_SCOPE,
        failure_hook: FailureHook | None = None,
    ) -> ReviewObservationAdmissionResult:
        return self.admit_generic_observation(
            delivery, expected_revision=expected_revision,
            generic_store_id=generic_store_id, owner_scope_hash=owner_scope_hash,
            failure_hook=failure_hook,
        )

    def recover_generic_observation(
        self, delivery: Mapping[str, Any], *,
        generic_store_id: str = "task058-generic-review-observations",
        owner_scope_hash: str = _GENERIC_UNBOUND_OWNER_SCOPE,
        failure_hook: FailureHook | None = None,
    ) -> ReviewObservationAdmissionResult:
        raw = _exact(delivery, "generic delivery", max_nodes=200_000)
        candidate = validate_generic_learning_delivery(raw)
        if _identifier(generic_store_id, "generic_store_id") != "task058-generic-review-observations":
            raise MontageLearningCanonicalAdmissionError("generic store identity is fixed")
        scope = _sha(owner_scope_hash, "owner_scope_hash")
        if failure_hook is not None and not callable(failure_hook):
            raise TypeError("failure_hook must be callable")
        with exclusive_file_update_lock(self.generic_journal_path):
            if not self.generic_journal_path.exists():
                raise MontageLearningCanonicalAdmissionError("generic recovery is not required")
            return self._generic_recover_v1_locked(
                raw, candidate, owner_scope_hash=scope, failure_hook=failure_hook
            )

    def get_verified_generic_observation(
        self, *, record_id: str, learning_sha256: str,
        canonical_commit_sha256: str,
        generic_store_id: str = "task058-generic-review-observations",
        owner_scope_hash: str = _GENERIC_UNBOUND_OWNER_SCOPE,
    ) -> ReviewObservationAdmissionResult:
        wanted_record = _identifier(record_id, "record_id")
        wanted_digest = _as_bare_sha(_sha(learning_sha256, "learning_sha256"))
        wanted_commit = _as_bare_sha(_sha(canonical_commit_sha256, "canonical_commit_sha256"))
        if _identifier(generic_store_id, "generic_store_id") != "task058-generic-review-observations":
            raise MontageLearningCanonicalAdmissionError("generic store identity is fixed")
        scope = _as_bare_sha(_sha(owner_scope_hash, "owner_scope_hash"))
        with exclusive_file_update_lock(self.generic_journal_path):
            if self.generic_journal_path.exists():
                raise MontageLearningCanonicalAdmissionError("generic recovery is required")
            with _exclusive_project_lock(ProductProjectManifestStore.path(self.project_root)):
                manifest = self._load_manifest_pinned()
                current = self._generic_load_current_v1(
                    manifest,
                    project_scope_hash=self._generic_project_scope_hash(manifest.project_id),
                    owner_scope_hash=scope,
                )
                if current is None:
                    raise MontageLearningCanonicalAdmissionError("generic observation is absent")
                ledger, _ = current
                matches = [
                    entry for entry in ledger["entries"]
                    if entry["record_id"] == wanted_record
                    and entry["source_digest_sha256"] == wanted_digest
                ]
                if len(matches) != 1:
                    raise MontageLearningCanonicalAdmissionError(
                        "generic observation coordinates are not uniquely current"
                    )
                entry = matches[0]
                marker = _read(
                    self.project_root / self._generic_marker_relative_path(entry["transaction_id"]),
                    _parse_generic_marker_v1,
                )
                if marker["canonical_commit_sha256"] != wanted_commit:
                    raise MontageLearningCanonicalAdmissionError("generic commit coordinate mismatch")
                anchored_binding = self._generic_binding_for_ledger(
                    canonical_json_bytes(self._generic_prefix_ledger(ledger, entry["store_revision"]))
                    + b"\n"
                )
                readback = self._generic_make_readback(marker, anchored_binding)
                anchored, current_manifest, binding, current_ledger = (
                    self._generic_trusted_readback_locked(readback, current_manifest=manifest)
                )
                return self._generic_make_result(
                    ACCEPTED, anchored, current_manifest, binding, current_ledger
                )

    def _lookup_trusted_review_observation(
        self, *, record_id: str, learning_sha256: str, project_id: str,
        owner_scope_hash: str, store_kind: str, generic_store_id: str,
    ) -> ReviewObservationCanonicalReadback:
        """Read an already-committed Generic observation without creating effects."""

        wanted_record = _identifier(record_id, "record_id")
        wanted_digest = _as_bare_sha(_sha(learning_sha256, "learning_sha256"))
        wanted_project = _identifier(project_id, "project_id")
        scope = _as_bare_sha(_sha(owner_scope_hash, "owner_scope_hash"))
        if _identifier(store_kind, "store_kind") != "REVIEW_OBSERVATION":
            raise MontageLearningCanonicalAdmissionError("generic store kind mismatch")
        if _identifier(generic_store_id, "generic_store_id") != "task058-generic-review-observations":
            raise MontageLearningCanonicalAdmissionError("generic store identity is fixed")

        generic_lock_path = self.generic_journal_path.with_name(
            f".{self.generic_journal_path.name}.lock"
        )
        product_lock_path = ProductProjectManifestStore.path(self.project_root).with_name(
            ".project.json.lock"
        )
        with _exclusive_existing_read_lock(generic_lock_path, "Generic operation"):
            if self.generic_journal_path.exists():
                raise MontageLearningCanonicalAdmissionError(
                    "RECOVERY_REQUIRED: generic admission journal is pending or corrupt"
                )
            with _exclusive_existing_read_lock(product_lock_path, "Product Project"):
                recovery = ProductProjectSaveCoordinator().recovery_status(
                    self.project_root
                )
                if recovery["required"]:
                    raise MontageLearningCanonicalAdmissionError(
                        "RECOVERY_REQUIRED: Product Project transaction is pending"
                    )
                manifest = self._load_manifest_pinned()
                if manifest.project_id != wanted_project:
                    raise MontageLearningCanonicalAdmissionError(
                        "RECOVERY_REQUIRED: generic Project scope mismatch"
                    )
                project_scope = self._generic_project_scope_hash(wanted_project)
                current = self._generic_load_current_v1(
                    manifest,
                    project_scope_hash=project_scope,
                    owner_scope_hash=scope,
                )
                if current is None:
                    raise MontageLearningCanonicalAdmissionError(
                        "RECOVERY_REQUIRED: generic observation is absent"
                    )
                ledger, _ = current
                matches = [
                    entry for entry in ledger["entries"]
                    if entry["record_id"] == wanted_record
                    and entry["source_digest_sha256"] == wanted_digest
                    and entry["project_scope_hash"] == project_scope
                    and entry["owner_scope_hash"] == scope
                ]
                if len(matches) != 1:
                    raise MontageLearningCanonicalAdmissionError(
                        "RECOVERY_REQUIRED: generic observation coordinates are not uniquely current"
                    )
                entry = matches[0]
                marker = _read(
                    self.project_root /
                    self._generic_marker_relative_path(entry["transaction_id"]),
                    _parse_generic_marker_v1,
                )
                anchored_binding = self._generic_binding_for_ledger(
                    canonical_json_bytes(
                        self._generic_prefix_ledger(ledger, entry["store_revision"])
                    ) + b"\n"
                )
                readback = self._generic_make_readback(marker, anchored_binding)
                anchored, _, _, _ = self._generic_trusted_readback_locked(
                    readback, current_manifest=manifest
                )
                return ReviewObservationCanonicalReadback._from_dict(anchored)

    def lookup_trusted_review_observation(
        self, *, record_id: str, learning_sha256: str, project_id: str,
        owner_scope_hash: str, store_kind: str, generic_store_id: str,
    ) -> ReviewObservationCanonicalReadback:
        try:
            return self._lookup_trusted_review_observation(
                record_id=record_id,
                learning_sha256=learning_sha256,
                project_id=project_id,
                owner_scope_hash=owner_scope_hash,
                store_kind=store_kind,
                generic_store_id=generic_store_id,
            )
        except (MontageLearningCanonicalAdmissionError, ProductError, OSError) as exc:
            if str(exc).startswith("RECOVERY_REQUIRED:"):
                raise
            raise MontageLearningCanonicalAdmissionError(
                f"RECOVERY_REQUIRED: {exc}"
            ) from exc

    admit_review_observation = admit_generic_observation
    recover_review_observation = recover_generic_observation
    get_current_review_observation = get_verified_generic_observation
    lookup_generic_observation = lookup_trusted_review_observation

__all__ = [
    "ANCHOR_FILE_NAME", "CANONICAL_RELATIVE_PATH", "JOURNAL_RELATIVE_PATH",
    "RECEIPT_RELATIVE_PATH", "SCHEMA_VERSION",
    "MontageLearningCanonicalAdmissionError",
    "MontageLearningCanonicalAdmissionResult",
    "MontageLearningCanonicalAdmissionTransactionStore",
    "MontageLearningVerifiedAdmissionReceipt",
    "GENERIC_OBSERVATION_RELATIVE_PATH",
    "GENERIC_OBSERVATION_JOURNAL_RELATIVE_PATH",
    "GENERIC_OBSERVATION_OBJECT_DIRECTORY",
    "GENERIC_OBSERVATION_MARKER_DIRECTORY",
    "ReviewObservationCanonicalReadback",
    "ReviewObservationAdmissionResult",
    "GenericReviewObservationReceipt",
]
