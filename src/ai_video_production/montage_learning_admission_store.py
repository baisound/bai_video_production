"""TASK-058 P1B body-free exact montage-learning admission ledger."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .montage_learning_bridge_contracts import EXACT_CONTRACT_PROFILE, GENERIC_CONTRACT_PROFILE
from .montage_learning_receipt_contracts import derive_montage_learning_idempotency_key_sha256
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
RECORD_TYPE = "MONTAGE_LEARNING_ADMISSION_STAGING_LEDGER"
TASK_OWNER = "TASK-058"
RELATIVE_PATH = Path("state") / "montage-learning-admission-staging-ledger.json"
ENTRY_DOMAIN = b"TASK058_MONTAGE_LEARNING_ADMISSION_ENTRY_V1\0"
LEDGER_DOMAIN = b"TASK058_MONTAGE_LEARNING_ADMISSION_LEDGER_V1\0"
STAGED = "STAGED"
DUPLICATE_STAGED = "DUPLICATE_STAGED"
_MAX_STORE_BYTES = 32 * 1024 * 1024
_REPARSE_POINT = 0x400
_LOCK_TARGET_NAME = "task058-montage-learning-admission-staging"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_ENTRY_FIELDS = frozenset({
    "record_version", "record_type", "task_owner", "sequence",
    "canonical_evidence_id", "source_contract_profile", "source_record_id",
    "source_sha256", "owner_scope_hash", "idempotency_key_sha256",
    "canonical_evidence_sha256", "human_binding_sha256", "committed_at",
    "previous_entry_sha256", "exact_evidence_coordinates_structurally_verified",
    "human_binding_origin_verified_by_store", "staging_store_written",
    "canonical_store_written", "canonical_admission_authority_created",
    "rollback_detection_authority_created",
    "receipt_minted", "automatic_learning_promotion_authorized",
    "timeline_mutation_authorized", "external_effect_authorized", "entry_sha256",
})
_LEDGER_FIELDS = frozenset({
    "schema_version", "record_type", "task_owner", "store_id",
    "owner_scope_hash", "revision", "entries",
    "generic_observation_admission_authorized",
    "automatic_learning_promotion_authorized", "receipt_mint_authorized",
    "canonical_store_write_authorized", "monotonic_head_anchored",
    "rollback_detection_authority_created",
    "path_security_model", "hostile_path_race_protection_verified",
    "handle_bound_canonical_promotion_required",
    "timeline_mutation_authorized", "resolve_write_authorized",
    "external_effect_authorized", "ledger_sha256",
})


def _error(code: str, message: str, category: ProductErrorCategory, **details: object) -> ProductError:
    return ProductError(code, message, category, details=dict(details))


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _utc_timestamp(value: object, name: str) -> str:
    if type(value) is not str or _UTC_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be an exact UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{name} must be UTC")
    return value


def _domain_hash(domain: bytes, value: Mapping[str, object]) -> str:
    return sha256_bytes(domain + canonical_json_bytes(value))


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _require_false(value: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if value[field] is not False:
            raise ValueError(f"{field} must remain false")


@dataclass(frozen=True, slots=True)
class MontageLearningAdmissionEntry:
    sequence: int
    canonical_evidence_id: str
    source_record_id: str
    source_sha256: str
    owner_scope_hash: str
    idempotency_key_sha256: str
    canonical_evidence_sha256: str
    human_binding_sha256: str
    committed_at: str
    previous_entry_sha256: str | None

    def __post_init__(self) -> None:
        _integer(self.sequence, "sequence", 1)
        _identifier(self.canonical_evidence_id, "canonical_evidence_id")
        _identifier(self.source_record_id, "source_record_id")
        _digest(self.source_sha256, "source_sha256")
        _digest(self.owner_scope_hash, "owner_scope_hash")
        supplied = _digest(self.idempotency_key_sha256, "idempotency_key_sha256")
        expected = derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id=self.source_record_id,
            source_sha256=self.source_sha256,
            owner_scope_hash=self.owner_scope_hash,
        )
        if supplied != expected:
            raise ValueError("idempotency_key_sha256 mismatch")
        _digest(self.canonical_evidence_sha256, "canonical_evidence_sha256")
        _digest(self.human_binding_sha256, "human_binding_sha256")
        _utc_timestamp(self.committed_at, "committed_at")
        if self.sequence == 1:
            if self.previous_entry_sha256 is not None:
                raise ValueError("first entry cannot bind a predecessor")
        else:
            _digest(self.previous_entry_sha256, "previous_entry_sha256")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "record_version": SCHEMA_VERSION,
            "record_type": "MONTAGE_LEARNING_ADMISSION_ENTRY",
            "task_owner": TASK_OWNER,
            "sequence": self.sequence,
            "canonical_evidence_id": self.canonical_evidence_id,
            "source_contract_profile": EXACT_CONTRACT_PROFILE,
            "source_record_id": self.source_record_id,
            "source_sha256": self.source_sha256,
            "owner_scope_hash": self.owner_scope_hash,
            "idempotency_key_sha256": self.idempotency_key_sha256,
            "canonical_evidence_sha256": self.canonical_evidence_sha256,
            "human_binding_sha256": self.human_binding_sha256,
            "committed_at": self.committed_at,
            "previous_entry_sha256": self.previous_entry_sha256,
            "exact_evidence_coordinates_structurally_verified": False,
            "human_binding_origin_verified_by_store": False,
            "staging_store_written": True,
            "canonical_store_written": False,
            "canonical_admission_authority_created": False,
            "rollback_detection_authority_created": False,
            "receipt_minted": False,
            "automatic_learning_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "external_effect_authorized": False,
        }
        body["entry_sha256"] = _domain_hash(ENTRY_DOMAIN, body)
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MontageLearningAdmissionEntry":
        if type(value) is not dict or set(value) != _ENTRY_FIELDS:
            raise ValueError("admission entry fields are incomplete or unknown")
        if (
            value["record_version"] != SCHEMA_VERSION
            or value["record_type"] != "MONTAGE_LEARNING_ADMISSION_ENTRY"
            or value["task_owner"] != TASK_OWNER
            or value["source_contract_profile"] != EXACT_CONTRACT_PROFILE
        ):
            raise ValueError("admission entry identity mismatch")
        if value["staging_store_written"] is not True:
            raise ValueError("staging store marker must remain true")
        _require_false(value, (
            "exact_evidence_coordinates_structurally_verified",
            "human_binding_origin_verified_by_store", "canonical_store_written",
            "canonical_admission_authority_created",
            "rollback_detection_authority_created",
            "receipt_minted",
            "automatic_learning_promotion_authorized",
            "timeline_mutation_authorized", "external_effect_authorized",
        ))
        result = cls(
            value["sequence"], value["canonical_evidence_id"],
            value["source_record_id"], value["source_sha256"],
            value["owner_scope_hash"], value["idempotency_key_sha256"],
            value["canonical_evidence_sha256"], value["human_binding_sha256"],
            value["committed_at"], value["previous_entry_sha256"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("admission entry hash or derived field mismatch")
        return result


@dataclass(frozen=True, slots=True)
class MontageLearningAdmissionLedger:
    store_id: str
    owner_scope_hash: str
    revision: int
    entries: tuple[MontageLearningAdmissionEntry, ...]

    def __post_init__(self) -> None:
        _identifier(self.store_id, "store_id")
        _digest(self.owner_scope_hash, "owner_scope_hash")
        _integer(self.revision, "revision")
        if self.revision != len(self.entries):
            raise ValueError("revision must equal entry count")
        previous: str | None = None
        record_ids: set[str] = set()
        source_hashes: set[str] = set()
        evidence_ids: set[str] = set()
        evidence_hashes: set[str] = set()
        keys: set[str] = set()
        for sequence, entry in enumerate(self.entries, 1):
            if (
                entry.sequence != sequence
                or entry.previous_entry_sha256 != previous
                or entry.owner_scope_hash != self.owner_scope_hash
            ):
                raise ValueError("admission ledger chain or scope is invalid")
            if (
                entry.source_record_id in record_ids
                or entry.source_sha256 in source_hashes
                or entry.canonical_evidence_id in evidence_ids
                or entry.canonical_evidence_sha256 in evidence_hashes
                or entry.idempotency_key_sha256 in keys
            ):
                raise ValueError("admission ledger contains a replay")
            record_ids.add(entry.source_record_id)
            source_hashes.add(entry.source_sha256)
            evidence_ids.add(entry.canonical_evidence_id)
            evidence_hashes.add(entry.canonical_evidence_sha256)
            keys.add(entry.idempotency_key_sha256)
            previous = str(entry.to_dict()["entry_sha256"])

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "task_owner": TASK_OWNER,
            "store_id": self.store_id,
            "owner_scope_hash": self.owner_scope_hash,
            "revision": self.revision,
            "entries": [entry.to_dict() for entry in self.entries],
            "generic_observation_admission_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "receipt_mint_authorized": False,
            "timeline_mutation_authorized": False,
            "canonical_store_write_authorized": False,
            "monotonic_head_anchored": False,
            "rollback_detection_authority_created": False,
            "resolve_write_authorized": False,
            "path_security_model": "COOPERATIVE_LOCAL_WRITER_ONLY",
            "hostile_path_race_protection_verified": False,
            "handle_bound_canonical_promotion_required": True,
            "external_effect_authorized": False,
        }
        body["ledger_sha256"] = _domain_hash(LEDGER_DOMAIN, body)
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MontageLearningAdmissionLedger":
        if type(value) is not dict or set(value) != _LEDGER_FIELDS:
            raise ValueError("admission ledger fields are incomplete or unknown")
        if (
            value["schema_version"] != SCHEMA_VERSION
            or value["record_type"] != RECORD_TYPE
            or value["task_owner"] != TASK_OWNER
        ):
            raise ValueError("admission ledger identity mismatch")
        if value["path_security_model"] != "COOPERATIVE_LOCAL_WRITER_ONLY":
            raise ValueError("path security model mismatch")
        if value["handle_bound_canonical_promotion_required"] is not True:
            raise ValueError("handle-bound canonical promotion must remain required")
        _require_false(value, (
            "generic_observation_admission_authorized",
            "automatic_learning_promotion_authorized", "receipt_mint_authorized",
            "canonical_store_write_authorized", "monotonic_head_anchored",
            "rollback_detection_authority_created",
            "hostile_path_race_protection_verified",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized",
        ))
        if type(value["entries"]) is not list:
            raise ValueError("entries must be an exact JSON array")
        result = cls(
            value["store_id"], value["owner_scope_hash"], value["revision"],
            tuple(MontageLearningAdmissionEntry.from_dict(row) for row in value["entries"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("admission ledger hash or derived field mismatch")
        return result


@dataclass(frozen=True, slots=True)
class MontageLearningAdmissionStoreResult:
    outcome: str
    entry: MontageLearningAdmissionEntry
    ledger: MontageLearningAdmissionLedger
    write: AtomicWriteResult | None

    def __post_init__(self) -> None:
        if self.outcome not in {STAGED, DUPLICATE_STAGED}:
            raise ValueError("store outcome is invalid")
        if (self.outcome == STAGED) != (self.write is not None):
            raise ValueError("write evidence must exist only for STAGED")

    @property
    def durability_state(self) -> str:
        return "DIRECTORY_DURABILITY_NOT_CONFIRMED" if self.write else "NO_WRITE"




    @property
    def path_security_state(self) -> str:
        return "HOSTILE_PATH_RACE_PROTECTION_NOT_CONFIRMED"
class MontageLearningAdmissionStore:
    """CAS append/read for one exact body-free Project admission ledger."""

    def __init__(self, project_root: str | Path) -> None:
        root = Path(project_root)
        if not root.is_absolute():
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE",
                "Montage learning Project root must be absolute",
                ProductErrorCategory.AUTHORIZATION,
            )
        self.project_root = root
        self.path = root / RELATIVE_PATH
        self.lock_target = root / _LOCK_TARGET_NAME
        self._root_identity: tuple[int, int] | None = None
        self._validate_path(create_state=True)
        self._root_identity = self._directory_identity()

    def _directory_identity(self) -> tuple[int, int]:
        info = self.project_root.stat()
        return (info.st_dev, info.st_ino)

    def _validate_path(self, *, create_state: bool) -> None:
        state_path = self.path.parent
        try:
            if (
                not self.project_root.exists()
                or not self.project_root.is_dir()
                or _is_reparse(self.project_root)
            ):
                raise ValueError("Project root is not a regular directory")
            if self._root_identity is not None:
                if self._directory_identity() != self._root_identity:
                    raise ValueError("Project root identity changed")
            if state_path.exists():
                if not state_path.is_dir() or _is_reparse(state_path):
                    raise ValueError("state is not a regular directory")
            elif create_state:
                state_path.mkdir()
            else:
                raise ValueError("state is missing")
            for candidate in (
                self.path,
                self.project_root / f".{_LOCK_TARGET_NAME}.lock",
            ):
                if _is_reparse(candidate) or (
                    candidate.exists()
                    and not candidate.is_file()
                ):
                    raise ValueError("store or lock path is unsafe")
        except (OSError, ValueError) as exc:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE",
                "Montage learning admission store path is unsafe",
                ProductErrorCategory.AUTHORIZATION,
                reason=type(exc).__name__,
            ) from exc

    @staticmethod
    def _validate_serialized_document(
        value: Mapping[str, Any],
    ) -> MontageLearningAdmissionLedger:
        encoded = canonical_json_bytes(value) + b"\n"
        if len(encoded) > _MAX_STORE_BYTES:
            raise ValueError("staging ledger exceeds the write size limit")
        return MontageLearningAdmissionLedger.from_dict(value)


    def _load_verified(self) -> MontageLearningAdmissionLedger:
        self._validate_path(create_state=False)
        try:
            size = self.path.stat().st_size
            if not 1 <= size <= _MAX_STORE_BYTES:
                raise ValueError("ledger size is invalid")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if type(document) is not dict:
                raise ValueError("ledger root must be an exact JSON object")
            return MontageLearningAdmissionLedger.from_dict(document)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                "Montage learning admission ledger failed verification",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def load(self) -> MontageLearningAdmissionLedger:
        if not self.path.exists():
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                "Montage learning admission ledger is missing",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return self._load_verified()

    def load_or_empty(
        self, *, store_id: str, owner_scope_hash: str
    ) -> MontageLearningAdmissionLedger:
        try:
            store = _identifier(store_id, "store_id")
            scope = _digest(owner_scope_hash, "owner_scope_hash")
        except ValueError as exc:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                "Montage learning store coordinates are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not self.path.exists():
            self._validate_path(create_state=False)
            return MontageLearningAdmissionLedger(store, scope, 0, ())
        current = self._load_verified()
        self._require_scope(current, store, scope)
        return current

    @staticmethod
    def _require_scope(
        ledger: MontageLearningAdmissionLedger,
        store_id: str,
        owner_scope_hash: str,
    ) -> None:
        if ledger.store_id != store_id or ledger.owner_scope_hash != owner_scope_hash:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_SCOPE",
                "Montage learning admission store scope mismatch",
                ProductErrorCategory.AUTHORIZATION,
            )

    def append(
        self, *, store_id: str, owner_scope_hash: str,
        source_contract_profile: str, source_record_id: str, source_sha256: str,
        idempotency_key_sha256: str, canonical_evidence_id: str,
        canonical_evidence_sha256: str, human_binding_sha256: str,
        committed_at: str, expected_revision: int,
        failure_injector: FailureInjector | None = None,
    ) -> MontageLearningAdmissionStoreResult:
        if source_contract_profile == GENERIC_CONTRACT_PROFILE:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_GENERIC_FORBIDDEN",
                "Generic montage observations cannot enter the admission ledger",
                ProductErrorCategory.AUTHORIZATION,
            )
        if source_contract_profile != EXACT_CONTRACT_PROFILE:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                "Montage learning source profile is unsupported",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            store = _identifier(store_id, "store_id")
            scope = _digest(owner_scope_hash, "owner_scope_hash")
            record = _identifier(source_record_id, "source_record_id")
            source = _digest(source_sha256, "source_sha256")
            key = _digest(idempotency_key_sha256, "idempotency_key_sha256")
            evidence_id = _identifier(canonical_evidence_id, "canonical_evidence_id")
            evidence_sha = _digest(canonical_evidence_sha256, "canonical_evidence_sha256")
            binding_sha = _digest(human_binding_sha256, "human_binding_sha256")
            timestamp = _utc_timestamp(committed_at, "committed_at")
            revision = _integer(expected_revision, "expected_revision")
            derived = derive_montage_learning_idempotency_key_sha256(
                source_contract_profile=EXACT_CONTRACT_PROFILE,
                source_record_id=record,
                source_sha256=source,
                owner_scope_hash=scope,
            )
            if key != derived:
                raise ValueError("idempotency key does not bind source coordinates")
        except ValueError as exc:
            raise _error(
                "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                "Montage learning append coordinates are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

        self._validate_path(create_state=False)
        with exclusive_file_update_lock(self.lock_target):
            self._validate_path(create_state=False)
            current = self.load_or_empty(store_id=store, owner_scope_hash=scope)
            self._require_scope(current, store, scope)
            immutable = (
                record, source, scope, key, evidence_id, evidence_sha, binding_sha,
            )
            for existing in current.entries:
                prior = (
                    existing.source_record_id, existing.source_sha256,
                    existing.owner_scope_hash, existing.idempotency_key_sha256,
                    existing.canonical_evidence_id,
                    existing.canonical_evidence_sha256,
                    existing.human_binding_sha256,
                )
                if existing.idempotency_key_sha256 == key:
                    if prior != immutable:
                        raise _error(
                            "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                            "Idempotency key collision detected",
                            ProductErrorCategory.DATA_INTEGRITY,
                        )
                    return MontageLearningAdmissionStoreResult(
                        DUPLICATE_STAGED, existing, current, None
                    )
                if (
                    existing.source_record_id == record
                    or existing.source_sha256 == source
                    or existing.canonical_evidence_id == evidence_id
                    or existing.canonical_evidence_sha256 == evidence_sha
                ):
                    raise _error(
                        "ERR_TASK058_MONTAGE_STORE_INTEGRITY",
                        "Montage learning identity collision or replay detected",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
            if current.revision != revision:
                raise _error(
                    "ERR_TASK058_MONTAGE_STORE_CONFLICT",
                    "Montage learning admission ledger changed since read",
                    ProductErrorCategory.STATE,
                    expected_revision=revision,
                    current_revision=current.revision,
                )
            previous = (
                str(current.entries[-1].to_dict()["entry_sha256"])
                if current.entries else None
            )
            entry = MontageLearningAdmissionEntry(
                current.revision + 1, evidence_id, record, source, scope, key,
                evidence_sha, binding_sha, timestamp, previous,
            )
            ledger = MontageLearningAdmissionLedger(
                store, scope, current.revision + 1, current.entries + (entry,)
            )
            document = ledger.to_dict()
            try:
                self._validate_serialized_document(document)
            except ValueError as exc:
                raise _error(
                    "ERR_TASK058_MONTAGE_STORE_SIZE",
                    "Montage learning staging ledger exceeds its safe size",
                    ProductErrorCategory.RESOURCE_EXHAUSTED,
                ) from exc

            def guarded_failure(phase: str, temp: Path) -> None:
                self._validate_path(create_state=False)
                if failure_injector is not None:
                    failure_injector(phase, temp)

            write = AtomicJsonWriter.write(
                self.path,
                document,
                validator=self._validate_serialized_document,
                failure_injector=guarded_failure,
            )
            readback = self._load_verified()
            if (
                readback.to_dict() != ledger.to_dict()
                or readback.entries[-1].to_dict() != entry.to_dict()
            ):
                raise _error(
                    "ERR_TASK058_MONTAGE_STORE_READBACK",
                    "Montage learning admission commit read-back mismatch",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            return MontageLearningAdmissionStoreResult(STAGED, entry, readback, write)


__all__ = [
    "DUPLICATE_STAGED", "ENTRY_DOMAIN", "LEDGER_DOMAIN", "STAGED",
    "MontageLearningAdmissionEntry", "MontageLearningAdmissionLedger",
    "MontageLearningAdmissionStore", "MontageLearningAdmissionStoreResult",
    "RECORD_TYPE", "RELATIVE_PATH", "SCHEMA_VERSION",
]
