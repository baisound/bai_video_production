"""TASK-014 R24-S2 restricted publication contract and fake owner store.

This module is deliberately effect-zero.  It validates body-free synthetic POST
candidates and keeps canonical bytes only in a process-local fake port.  It
cannot mint a narration publication receipt or a publication-current runtime
type, and it has no filesystem, private-body, model, Provider, audio or Asset
surface.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
import json
import re
import threading
from types import FunctionType, MappingProxyType
from typing import Any, Mapping
import unicodedata
from weakref import WeakKeyDictionary

from . import owner_voice_authority as _task074
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


R24_S2_VERSION = "TASK014_R24_S2_RESTRICTED_PUBLICATION_STORE_V1"
POST_RECORD_TYPE = "TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1"
POST_HISTORY_TYPE = "TASK014_R24_POST_HISTORY_V1"
FIXTURE_SCOPE = "TASK014_R24_S2_SYNTHETIC_EFFECT_ZERO"
TASK014_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "A398A9FE13F886DC6A4783B2AB3EEAB61721598F20F27ABAC2C0EB2811CBB06B"
)
TASK074_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0"
)
R24_S1_COMPLETION_RECEIPT_SHA256 = (
    "899F74513B141255B5B052431AADE820EE3DD118E174122B05E5AC663827152D"
)
R24_S1_SOURCE_SHA256 = (
    "B2450071427D2752C4FF381746EE680E1025C8E8BB89AD6FAB1C81EDA4CC2BD3"
)
MAX_ENTRIES = 10_000
MAX_BYTES = 16 * 1024 * 1024

_POST_DOMAIN = b"TASK014_R24_S2_POST_CANDIDATE_V1\0"
_HISTORY_DOMAIN = b"TASK014_R24_S2_POST_HISTORY_V1\0"
_S1_COORDINATE_DOMAIN = b"TASK074_R24_S1_EFFECT_ZERO_COORDINATE_V1\0"
_S1_DECISION_DOMAIN = b"TASK074_R24_S1_EFFECT_ZERO_DECISION_V1\0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_UPPER_SHA_RE = re.compile(r"^[0-9A-F]{64}$")

_POST_FIELDS = {
    "version",
    "record_type",
    "owner_task",
    "fixture_scope",
    "project_id",
    "operation_id",
    "ticket_id",
    "candidate_id",
    "revision",
    "parent_record_sha256",
    "call_sha256",
    "sink_sha256",
    "result_sha256",
    "publication_readback_sha256",
    "task014_owner_acceptance_record_sha256",
    "task074_owner_acceptance_record_sha256",
    "task074_s1_coordinate_sha256",
    "task074_s1_decision_sha256",
    "publication_state",
    "fixture_only",
    "body_embedded",
    "source_authority",
    "effect_authority",
    "canonical_publication_type_minted",
    "private_body_present",
    "model_entered",
    "provider_entered",
    "audio_entered",
    "wav_created",
    "asset_created",
    "publication_current",
    "record_sha256",
}
_HISTORY_FIELDS = {
    "version",
    "record_type",
    "owner_task",
    "fixture_scope",
    "project_id",
    "store_revision",
    "entries",
    "fake_persistence_only",
    "body_embedded",
    "source_authority",
    "effect_authority",
    "filesystem_write_authority",
    "publication_authority",
    "snapshot_sha256",
}
_FALSE_POST_FIELDS = (
    "body_embedded",
    "source_authority",
    "effect_authority",
    "canonical_publication_type_minted",
    "private_body_present",
    "model_entered",
    "provider_entered",
    "audio_entered",
    "wav_created",
    "asset_created",
    "publication_current",
)
_FALSE_HISTORY_FIELDS = (
    "body_embedded",
    "source_authority",
    "effect_authority",
    "filesystem_write_authority",
    "publication_authority",
)


class Task014R24CurrentState(str, Enum):
    CURRENT_EFFECT_ZERO = "CURRENT_EFFECT_ZERO"
    STORE_NOT_FOUND = "STORE_NOT_FOUND"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    STALE_UPSTREAM = "STALE_UPSTREAM"
    BROKEN_CHAIN = "BROKEN_CHAIN"
    FOREIGN_PROJECT = "FOREIGN_PROJECT"
    UNSAFE_AUTHORITY = "UNSAFE_AUTHORITY"


class _HistoryFault(Exception):
    def __init__(self, state: Task014R24CurrentState, reason: str) -> None:
        super().__init__(reason)
        self.state = state
        self.reason = reason


def _exact_mapping(value: Any, fields: set[str], name: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")
    return value


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not 1 <= len(value) <= 200:
        raise ValueError(f"{name} is invalid")
    if unicodedata.normalize("NFC", value) != value or not value.isascii():
        raise ValueError(f"{name} must be canonical ASCII")
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str:
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _acceptance_digest(value: Any, expected: str, name: str) -> str:
    if type(value) is not str or not _UPPER_SHA_RE.fullmatch(value) or value != expected:
        raise ValueError(f"{name} must be the exact accepted R24 record")
    return value


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive bounded integer")
    return value


def _canonical_copy(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(copy.deepcopy(dict(value)))


def _hash_without(domain: bytes, value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(
        domain + canonical_json_bytes({key: copy.deepcopy(item) for key, item in value.items() if key != field})
    )


@dataclass(frozen=True, slots=True)
class _CandidateState:
    data: Mapping[str, Any]


def _build_candidate_registry():
    states: WeakKeyDictionary[object, _CandidateState] = WeakKeyDictionary()
    registry_lock = threading.RLock()

    def register(value: object, state: _CandidateState) -> None:
        if type(value) is not Task014R24PostCandidate or type(state) is not _CandidateState:
            raise TypeError("R24-S2 POST candidate registration is invalid")
        with registry_lock:
            if value in states:
                raise TypeError("R24-S2 POST candidate is already initialized")
            states[value] = state

    def read_data(value: object) -> dict[str, Any]:
        if type(value) is not Task014R24PostCandidate:
            raise TypeError("R24-S2 POST candidate type is invalid")
        with registry_lock:
            state = states.get(value)
        if type(state) is not _CandidateState:
            raise TypeError("R24-S2 POST candidate provenance is invalid")
        return copy.deepcopy(dict(state.data))

    return register, read_data


_register_candidate, _read_candidate_data = _build_candidate_registry()
del _build_candidate_registry


class Task014R24PostCandidate:
    """Body-free serializable candidate record; never publication-current."""

    __slots__ = ("__weakref__",)

    def __init__(self, *_: Any, **__: Any) -> None:
        raise TypeError("R24-S2 POST candidates must use create_synthetic/from_dict")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("R24-S2 POST candidate types are sealed")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("R24-S2 POST candidates are immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("R24-S2 POST candidates are immutable")

    def __copy__(self) -> None:
        raise TypeError("R24-S2 POST candidates are non-copyable")

    def __deepcopy__(self, memo: dict[int, Any]) -> None:
        raise TypeError("R24-S2 POST candidates are non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("R24-S2 POST candidate objects are non-pickleable")

    def __reduce_ex__(self, protocol: int) -> None:
        raise TypeError("R24-S2 POST candidate objects are non-pickleable")

    @classmethod
    def create_synthetic(
        cls,
        *,
        project_id: str,
        operation_id: str,
        ticket_id: str,
        candidate_id: str,
        revision: int,
        parent_record_sha256: str | None,
        call_sha256: str,
        sink_sha256: str,
        result_sha256: str,
        publication_readback_sha256: str,
        task074_s1_coordinate_sha256: str,
        task074_s1_decision_sha256: str,
    ) -> Task014R24PostCandidate:
        value: dict[str, Any] = {
            "version": 1,
            "record_type": POST_RECORD_TYPE,
            "owner_task": "TASK-014",
            "fixture_scope": FIXTURE_SCOPE,
            "project_id": project_id,
            "operation_id": operation_id,
            "ticket_id": ticket_id,
            "candidate_id": candidate_id,
            "revision": revision,
            "parent_record_sha256": parent_record_sha256,
            "call_sha256": call_sha256,
            "sink_sha256": sink_sha256,
            "result_sha256": result_sha256,
            "publication_readback_sha256": publication_readback_sha256,
            "task014_owner_acceptance_record_sha256": TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task074_owner_acceptance_record_sha256": TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task074_s1_coordinate_sha256": task074_s1_coordinate_sha256,
            "task074_s1_decision_sha256": task074_s1_decision_sha256,
            "publication_state": "NOT_MINTED_EFFECT_ZERO",
            "fixture_only": True,
            "body_embedded": False,
            "source_authority": False,
            "effect_authority": False,
            "canonical_publication_type_minted": False,
            "private_body_present": False,
            "model_entered": False,
            "provider_entered": False,
            "audio_entered": False,
            "wav_created": False,
            "asset_created": False,
            "publication_current": False,
        }
        value["record_sha256"] = _hash_without(_POST_DOMAIN, value, "record_sha256")
        return cls.from_dict(value)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Task014R24PostCandidate:
        document = _exact_mapping(value, _POST_FIELDS, "R24-S2 POST candidate")
        if (
            type(document["version"]) is not int
            or document["version"] != 1
            or document["record_type"] != POST_RECORD_TYPE
            or document["owner_task"] != "TASK-014"
            or document["fixture_scope"] != FIXTURE_SCOPE
            or document["publication_state"] != "NOT_MINTED_EFFECT_ZERO"
            or document["fixture_only"] is not True
        ):
            raise ValueError("R24-S2 POST candidate identity is invalid")
        for name in ("project_id", "operation_id", "ticket_id", "candidate_id"):
            _identifier(document[name], name)
        _positive(document["revision"], "revision")
        _digest(document["parent_record_sha256"], "parent_record_sha256", nullable=True)
        for name in (
            "call_sha256",
            "sink_sha256",
            "result_sha256",
            "publication_readback_sha256",
            "task074_s1_coordinate_sha256",
            "task074_s1_decision_sha256",
            "record_sha256",
        ):
            _digest(document[name], name)
        _acceptance_digest(
            document["task014_owner_acceptance_record_sha256"],
            TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task014_owner_acceptance_record_sha256",
        )
        _acceptance_digest(
            document["task074_owner_acceptance_record_sha256"],
            TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task074_owner_acceptance_record_sha256",
        )
        if any(document[name] is not False for name in _FALSE_POST_FIELDS):
            raise ValueError("R24-S2 POST candidate violates the effect-zero boundary")
        if document["record_sha256"] != _hash_without(_POST_DOMAIN, document, "record_sha256"):
            raise ValueError("R24-S2 POST candidate digest mismatch")
        result = object.__new__(cls)
        _register_candidate(result, _CandidateState(_canonical_copy(document)))
        return result

    @property
    def record_sha256(self) -> str:
        return str(_read_candidate_data(self)["record_sha256"])

    def to_dict(self) -> dict[str, Any]:
        return _read_candidate_data(self)


@dataclass(slots=True)
class _PortState:
    lock: threading.RLock
    snapshot_bytes: bytes | None
    owner_written: bool


def _build_port_surface():
    states: WeakKeyDictionary[object, _PortState] = WeakKeyDictionary()
    registry_lock = threading.RLock()

    class Task014R24FakePublicationPort:
        """Process-local test port.  It never touches the Product filesystem."""

        __slots__ = ("__weakref__",)

        def __init__(self, *, fixture_snapshot_bytes: bytes | None = None) -> None:
            if type(self) is not Task014R24FakePublicationPort:
                raise TypeError("R24-S2 fake persistence port type is invalid")
            if fixture_snapshot_bytes is not None and type(fixture_snapshot_bytes) is not bytes:
                raise TypeError("fixture_snapshot_bytes must be exact bytes")
            if fixture_snapshot_bytes is not None and not 0 < len(fixture_snapshot_bytes) <= MAX_BYTES:
                raise ValueError("fixture_snapshot_bytes is outside the bounded size")
            with registry_lock:
                if self in states:
                    raise TypeError("R24-S2 fake persistence port is already initialized")
                states[self] = _PortState(threading.RLock(), fixture_snapshot_bytes, False)

        def __init_subclass__(cls, **kwargs: Any) -> None:
            raise TypeError("R24-S2 fake persistence port types are sealed")

        def __setattr__(self, name: str, value: Any) -> None:
            raise AttributeError("R24-S2 fake persistence ports are sealed")

        def __delattr__(self, name: str) -> None:
            raise AttributeError("R24-S2 fake persistence ports are sealed")

        def __copy__(self) -> None:
            raise TypeError("R24-S2 fake persistence ports are non-copyable")

        def __deepcopy__(self, memo: dict[int, Any]) -> None:
            raise TypeError("R24-S2 fake persistence ports are non-copyable")

        def __reduce__(self) -> None:
            raise TypeError("R24-S2 fake persistence ports are non-serializable")

        def __reduce_ex__(self, protocol: int) -> None:
            raise TypeError("R24-S2 fake persistence ports are non-serializable")

        def fixture_snapshot_bytes(self) -> bytes | None:
            snapshot_bytes, _ = read_snapshot(self)
            return snapshot_bytes

    def read_snapshot(port: object) -> tuple[bytes | None, bool]:
        if type(port) is not Task014R24FakePublicationPort:
            raise TypeError("R24-S2 fake persistence port type is invalid")
        with registry_lock:
            state = states.get(port)
        if type(state) is not _PortState:
            raise TypeError("R24-S2 fake persistence port provenance is invalid")
        with state.lock:
            return state.snapshot_bytes, state.owner_written

    def owner_transaction(port: object, update: Any) -> None:
        if type(port) is not Task014R24FakePublicationPort:
            raise TypeError("R24-S2 fake persistence port type is invalid")
        with registry_lock:
            state = states.get(port)
        if type(state) is not _PortState:
            raise TypeError("R24-S2 fake persistence port provenance is invalid")
        with state.lock:
            encoded = update(state.snapshot_bytes, state.owner_written)
            if type(encoded) is not bytes or not 0 < len(encoded) <= MAX_BYTES:
                raise TypeError("R24-S2 owner transaction returned invalid bytes")
            state.snapshot_bytes = encoded
            state.owner_written = True

    return Task014R24FakePublicationPort, read_snapshot, owner_transaction


(
    Task014R24FakePublicationPort,
    _read_port_snapshot,
    _owner_port_transaction,
) = _build_port_surface()
del _build_port_surface


@dataclass(frozen=True, slots=True)
class _CurrentReadState:
    state: Task014R24CurrentState
    project_id: str
    operation_id: str
    ticket_id: str
    candidate_id: str
    store_revision: int | None
    snapshot_sha256: str | None
    record_sha256: str | None
    reason_codes: tuple[str, ...]
    owner_store_read: bool
    owner_origin_authenticated: bool
    currentness_verified: bool


def _build_read_registry():
    states: WeakKeyDictionary[object, _CurrentReadState] = WeakKeyDictionary()
    registry_lock = threading.RLock()
    allowed_fields = frozenset(
        {
            "state",
            "project_id",
            "operation_id",
            "ticket_id",
            "candidate_id",
            "store_revision",
            "snapshot_sha256",
            "record_sha256",
            "reason_codes",
            "owner_store_read",
            "owner_origin_authenticated",
            "currentness_verified",
        }
    )

    def read_field(value: object, name: str) -> object:
        if type(value) is not _Task014R24EffectZeroCurrentRead:
            raise TypeError("R24-S2 current-read type is invalid")
        if name not in allowed_fields:
            raise TypeError("R24-S2 current-read field is invalid")
        with registry_lock:
            state = states.get(value)
        if type(state) is not _CurrentReadState:
            raise TypeError("R24-S2 current-read provenance is invalid")
        return getattr(state, name)

    def issue_read(read_state: _CurrentReadState) -> object:
        if type(read_state) is not _CurrentReadState:
            raise TypeError("R24-S2 current-read issuance state is invalid")
        result = object.__new__(_Task014R24EffectZeroCurrentRead)
        with registry_lock:
            states[result] = read_state
        return result

    return read_field, issue_read


_read_field, _issue_read_capability = _build_read_registry()
del _build_read_registry


class _Task014R24EffectZeroCurrentRead:
    """Sealed owner read; deliberately not publication-current."""

    __slots__ = ("__weakref__",)

    def __init__(self, *_: Any, **__: Any) -> None:
        raise TypeError("R24-S2 current reads may only be issued by the fake owner store")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("R24-S2 current-read types are sealed")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("R24-S2 current reads are immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("R24-S2 current reads are immutable")

    def __copy__(self) -> None:
        raise TypeError("R24-S2 current reads are non-copyable")

    def __deepcopy__(self, memo: dict[int, Any]) -> None:
        raise TypeError("R24-S2 current reads are non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("R24-S2 current reads are non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        raise TypeError("R24-S2 current reads are non-serializable")

    def __getstate__(self) -> None:
        raise TypeError("R24-S2 current reads are non-serializable")

    @property
    def state(self) -> Task014R24CurrentState:
        return _read_field(self, "state")  # type: ignore[return-value]

    @property
    def project_id(self) -> str:
        return _read_field(self, "project_id")  # type: ignore[return-value]

    @property
    def operation_id(self) -> str:
        return _read_field(self, "operation_id")  # type: ignore[return-value]

    @property
    def ticket_id(self) -> str:
        return _read_field(self, "ticket_id")  # type: ignore[return-value]

    @property
    def candidate_id(self) -> str:
        return _read_field(self, "candidate_id")  # type: ignore[return-value]

    @property
    def store_revision(self) -> int | None:
        return _read_field(self, "store_revision")  # type: ignore[return-value]

    @property
    def snapshot_sha256(self) -> str | None:
        return _read_field(self, "snapshot_sha256")  # type: ignore[return-value]

    @property
    def record_sha256(self) -> str | None:
        return _read_field(self, "record_sha256")  # type: ignore[return-value]

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return _read_field(self, "reason_codes")  # type: ignore[return-value]

    @property
    def owner_store_read(self) -> bool:
        return _read_field(self, "owner_store_read")  # type: ignore[return-value]

    @property
    def owner_origin_authenticated(self) -> bool:
        return _read_field(self, "owner_origin_authenticated")  # type: ignore[return-value]

    @property
    def currentness_verified(self) -> bool:
        return _read_field(self, "currentness_verified")  # type: ignore[return-value]

    @property
    def fixture_only(self) -> bool:
        return True

    @property
    def source_authority(self) -> bool:
        return False

    @property
    def effect_authority(self) -> bool:
        return False

    @property
    def canonical_publication_type_minted(self) -> bool:
        return False

    @property
    def private_body_present(self) -> bool:
        return False

    @property
    def model_entered(self) -> bool:
        return False

    @property
    def provider_entered(self) -> bool:
        return False

    @property
    def audio_entered(self) -> bool:
        return False

    @property
    def wav_created(self) -> bool:
        return False

    @property
    def asset_created(self) -> bool:
        return False

    @property
    def publication_current(self) -> bool:
        return False


def _parse_document_bytes(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes or not 0 < len(value) <= MAX_BYTES:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_BYTES_INVALID")
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = item
        return result

    try:
        document = json.loads(value.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_JSON_INVALID") from exc
    if type(document) is not dict:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_ROOT_INVALID")
    if canonical_json_bytes(document) != value:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_BYTES_NONCANONICAL")
    return document


def _parse_history(
    document: Mapping[str, Any], *, expected_project_id: str | None = None,
) -> tuple[str, list[Task014R24PostCandidate], int, str]:
    if type(document) is not dict or set(document) != _HISTORY_FIELDS:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_FIELDS_INVALID")
    if any(document.get(name) is not False for name in _FALSE_HISTORY_FIELDS):
        raise _HistoryFault(Task014R24CurrentState.UNSAFE_AUTHORITY, "UNSAFE_AUTHORITY_FLAG")
    if document.get("fake_persistence_only") is not True:
        raise _HistoryFault(Task014R24CurrentState.UNSAFE_AUTHORITY, "REAL_PERSISTENCE_CLAIMED")
    if (
        type(document.get("version")) is not int
        or document.get("version") != 1
        or document.get("record_type") != POST_HISTORY_TYPE
        or document.get("owner_task") != "TASK-014"
        or document.get("fixture_scope") != FIXTURE_SCOPE
    ):
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_IDENTITY_INVALID")
    try:
        project_id = _identifier(document.get("project_id"), "project_id")
    except ValueError as exc:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_PROJECT_INVALID") from exc
    if expected_project_id is not None and project_id != expected_project_id:
        raise _HistoryFault(Task014R24CurrentState.FOREIGN_PROJECT, "FOREIGN_PROJECT")
    revision = document.get("store_revision")
    rows = document.get("entries")
    if isinstance(revision, bool) or type(revision) is not int or revision < 0:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_REVISION_INVALID")
    if type(rows) is not list or len(rows) > MAX_ENTRIES or revision != len(rows):
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_ENTRY_COUNT_INVALID")
    expected_snapshot = _hash_without(_HISTORY_DOMAIN, document, "snapshot_sha256")
    if document.get("snapshot_sha256") != expected_snapshot:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "STORE_DIGEST_MISMATCH")
    entries: list[Task014R24PostCandidate] = []
    heads: dict[tuple[str, str], Task014R24PostCandidate] = {}
    seen: set[str] = set()
    try:
        for row in rows:
            if type(row) is dict and any(
                row.get(name) is not False for name in _FALSE_POST_FIELDS
            ):
                raise _HistoryFault(
                    Task014R24CurrentState.UNSAFE_AUTHORITY,
                    "UNSAFE_ENTRY_AUTHORITY_FLAG",
                )
            candidate = Task014R24PostCandidate.from_dict(row)
            body = candidate.to_dict()
            if body["project_id"] != project_id:
                raise ValueError("entry belongs to another Project")
            key = (body["operation_id"], body["candidate_id"])
            current = heads.get(key)
            if current is None:
                if body["revision"] != 1 or body["parent_record_sha256"] is not None:
                    raise ValueError("first candidate revision is invalid")
            else:
                parent = current.to_dict()
                if (
                    body["revision"] != parent["revision"] + 1
                    or body["parent_record_sha256"] != current.record_sha256
                ):
                    raise ValueError("candidate chain is forked or discontinuous")
                for stable_name in (
                    "project_id",
                    "operation_id",
                    "ticket_id",
                    "candidate_id",
                    "task014_owner_acceptance_record_sha256",
                    "task074_owner_acceptance_record_sha256",
                    "task074_s1_coordinate_sha256",
                    "task074_s1_decision_sha256",
                ):
                    if body[stable_name] != parent[stable_name]:
                        raise ValueError("candidate chain changed a stable coordinate")
            if candidate.record_sha256 in seen:
                raise ValueError("duplicate candidate digest")
            seen.add(candidate.record_sha256)
            entries.append(candidate)
            heads[key] = candidate
    except _HistoryFault:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise _HistoryFault(Task014R24CurrentState.BROKEN_CHAIN, "ENTRY_CHAIN_INVALID") from exc
    return project_id, entries, revision, expected_snapshot


def _snapshot(project_id: str, entries: list[Task014R24PostCandidate]) -> dict[str, Any]:
    document: dict[str, Any] = {
        "version": 1,
        "record_type": POST_HISTORY_TYPE,
        "owner_task": "TASK-014",
        "fixture_scope": FIXTURE_SCOPE,
        "project_id": _identifier(project_id, "project_id"),
        "store_revision": len(entries),
        "entries": [entry.to_dict() for entry in entries],
        "fake_persistence_only": True,
        "body_embedded": False,
        "source_authority": False,
        "effect_authority": False,
        "filesystem_write_authority": False,
        "publication_authority": False,
    }
    document["snapshot_sha256"] = _hash_without(_HISTORY_DOMAIN, document, "snapshot_sha256")
    return document


def _validated_s1_decision(
    value: object,
    *,
    project_id: str,
    operation_id: str,
    ticket_id: str,
) -> tuple[str, str]:
    if type(value) is not _task074._Task074R24EffectZeroDecision:
        raise TypeError("R24-S2 requires the exact R24-S1 decision type")
    if (
        value.owner_acceptance_record_sha256 != TASK074_OWNER_ACCEPTANCE_RECORD_SHA256
        or value.fixture_only is not True
        or value.source_authority is not False
        or value.effect_authority is not False
        or value.canonical_runtime_type_minted is not False
        or value.private_body_present is not False
        or value.model_entered is not False
        or value.provider_entered is not False
        or value.audio_entered is not False
        or value.wav_created is not False
        or value.publication_current is not False
    ):
        raise ValueError("R24-S1 decision violates the effect-zero boundary")
    if (
        value.predecessor_kind is not _task074.R24PredecessorKind.UNKNOWN
        or value.post is not _task074.R24TruthValue.UNKNOWN
        or value.job_terminal is not _task074.R24TruthValue.UNKNOWN
        or value.retirement is not _task074.R24TruthValue.UNKNOWN
        or value.branch is not _task074.R24GlobalBranch.CONTAINED_PARTIAL_TRUTH
        or value.prepare_continuity_context
        is not _task074.R24PrepareContinuityContext.NO_PREPARE_RECOVERY_EVENT
    ):
        raise ValueError("R24-S2 accepts only the all-UNKNOWN contained S1 fixture")
    coordinate_body = {
        "producer_version": _task074.R24_S1_PRODUCER_VERSION,
        "fixture_scope": _task074.R24_S1_FIXTURE_SCOPE,
        "owner_acceptance_record_sha256": value.owner_acceptance_record_sha256,
        "project_id": project_id,
        "operation_id": operation_id,
        "ticket_id": ticket_id,
        "predecessor_kind": value.predecessor_kind.value,
        "post": value.post.value,
        "job_terminal": value.job_terminal.value,
        "retirement": value.retirement.value,
        "prepare_continuity_context": value.prepare_continuity_context.value,
    }
    expected_coordinate = sha256_bytes(
        _S1_COORDINATE_DOMAIN + canonical_json_bytes(coordinate_body)
    )
    if value.coordinate_sha256 != expected_coordinate:
        raise ValueError("R24-S1 decision does not bind the exact S1 coordinate supplied to S2")
    expected_decision = sha256_bytes(
        _S1_DECISION_DOMAIN
        + canonical_json_bytes(
            {
                "branch": value.branch.value,
                "coordinate_sha256": expected_coordinate,
                "effect_authority": False,
                "fixture_only": True,
                "source_authority": False,
            }
        )
    )
    if value.decision_sha256 != expected_decision:
        raise ValueError("R24-S1 decision digest is invalid")
    return expected_coordinate, expected_decision


@dataclass(slots=True)
class _ConsumerState:
    lock: threading.Lock
    burned: bool


def _build_consumer_registry():
    states: WeakKeyDictionary[object, _ConsumerState] = WeakKeyDictionary()
    registry_lock = threading.RLock()

    def initialize(value: object) -> None:
        if type(value) is not Task014R24RestrictedConsumer:
            raise TypeError("R24-S2 restricted consumer type is invalid")
        with registry_lock:
            if value in states:
                raise TypeError("R24-S2 restricted consumer is already initialized")
            states[value] = _ConsumerState(threading.Lock(), False)

    def burn(value: object) -> None:
        if type(value) is not Task014R24RestrictedConsumer:
            raise TypeError("R24-S2 restricted consumer type is invalid")
        with registry_lock:
            state = states.get(value)
        if type(state) is not _ConsumerState:
            raise TypeError("R24-S2 restricted consumer provenance is invalid")
        with state.lock:
            if state.burned:
                raise RuntimeError("R24-S2 restricted consumer has already been burned")
            state.burned = True

    return initialize, burn


_initialize_consumer, _burn_consumer = _build_consumer_registry()
del _build_consumer_registry


class Task014R24RestrictedConsumer:
    """One-use effect-zero consumer for the exact S1 contained fixture."""

    __slots__ = ("__weakref__",)

    def __init__(
        self,
        *,
        task014_owner_acceptance_record_sha256: str,
        task074_owner_acceptance_record_sha256: str,
        r24_s1_completion_receipt_sha256: str,
        r24_s1_source_sha256: str,
    ) -> None:
        if type(self) is not Task014R24RestrictedConsumer:
            raise TypeError("R24-S2 restricted consumer type is invalid")
        _acceptance_digest(
            task014_owner_acceptance_record_sha256,
            TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task014_owner_acceptance_record_sha256",
        )
        _acceptance_digest(
            task074_owner_acceptance_record_sha256,
            TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
            "task074_owner_acceptance_record_sha256",
        )
        _acceptance_digest(
            r24_s1_completion_receipt_sha256,
            R24_S1_COMPLETION_RECEIPT_SHA256,
            "r24_s1_completion_receipt_sha256",
        )
        _acceptance_digest(
            r24_s1_source_sha256,
            R24_S1_SOURCE_SHA256,
            "r24_s1_source_sha256",
        )
        _initialize_consumer(self)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("R24-S2 restricted consumer types are sealed")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("R24-S2 restricted consumers are sealed")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("R24-S2 restricted consumers are sealed")

    def __copy__(self) -> None:
        raise TypeError("R24-S2 restricted consumers are non-copyable")

    def __deepcopy__(self, memo: dict[int, Any]) -> None:
        raise TypeError("R24-S2 restricted consumers are non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("R24-S2 restricted consumers are non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        raise TypeError("R24-S2 restricted consumers are non-serializable")

    def __iter__(self) -> None:
        raise TypeError("R24-S2 restricted consumers are non-iterable")

    def append_candidate(
        self,
        *,
        port: Task014R24FakePublicationPort,
        s1_decision: object,
        candidate: Task014R24PostCandidate,
        project_id: str,
        operation_id: str,
        ticket_id: str,
        expected_previous_snapshot_sha256: str | None,
    ) -> _Task014R24EffectZeroCurrentRead:
        _burn_consumer(self)
        project = _identifier(project_id, "project_id")
        operation = _identifier(operation_id, "operation_id")
        ticket = _identifier(ticket_id, "ticket_id")
        if expected_previous_snapshot_sha256 is not None:
            _digest(expected_previous_snapshot_sha256, "expected_previous_snapshot_sha256")
        coordinate, decision = _validated_s1_decision(
            s1_decision,
            project_id=project,
            operation_id=operation,
            ticket_id=ticket,
        )
        if type(candidate) is not Task014R24PostCandidate:
            raise TypeError("R24-S2 POST candidate type is invalid")
        body = candidate.to_dict()
        if (
            body["project_id"] != project
            or body["operation_id"] != operation
            or body["ticket_id"] != ticket
            or body["task074_s1_coordinate_sha256"] != coordinate
            or body["task074_s1_decision_sha256"] != decision
        ):
            raise ValueError("R24-S2 POST candidate does not bind the exact S1 coordinate")
        def update_port(snapshot_bytes: bytes | None, owner_written: bool) -> bytes:
            if snapshot_bytes is None:
                if expected_previous_snapshot_sha256 is not None:
                    raise ValueError("expected previous snapshot does not exist")
                entries: list[Task014R24PostCandidate] = []
            else:
                if owner_written is not True:
                    raise ValueError("R24-S2 cannot append to an untrusted fixture snapshot")
                document = _parse_document_bytes(snapshot_bytes)
                _, entries, _, current_snapshot = _parse_history(
                    document, expected_project_id=project,
                )
                if expected_previous_snapshot_sha256 is None:
                    raise ValueError("replacing fake owner history requires exact snapshot CAS")
                if expected_previous_snapshot_sha256 != current_snapshot:
                    raise ValueError("fake owner history changed before append")
            key_entries = [
                entry
                for entry in entries
                if entry.to_dict()["operation_id"] == operation
                and entry.to_dict()["candidate_id"] == body["candidate_id"]
            ]
            if key_entries:
                head = key_entries[-1]
                head_body = head.to_dict()
                if (
                    body["revision"] != head_body["revision"] + 1
                    or body["parent_record_sha256"] != head.record_sha256
                ):
                    raise ValueError("R24-S2 candidate does not extend the exact owner head")
                for stable_name in (
                    "project_id",
                    "operation_id",
                    "ticket_id",
                    "candidate_id",
                    "task014_owner_acceptance_record_sha256",
                    "task074_owner_acceptance_record_sha256",
                    "task074_s1_coordinate_sha256",
                    "task074_s1_decision_sha256",
                ):
                    if body[stable_name] != head_body[stable_name]:
                        raise ValueError("R24-S2 candidate changed a stable owner coordinate")
            elif body["revision"] != 1 or body["parent_record_sha256"] is not None:
                raise ValueError("R24-S2 first candidate must start at revision one")
            if any(entry.record_sha256 == candidate.record_sha256 for entry in entries):
                raise ValueError("R24-S2 candidate replay is not appendable")
            if len(entries) >= MAX_ENTRIES:
                raise ValueError("R24-S2 fake owner history reached its entry bound")
            document = _snapshot(project, [*entries, candidate])
            encoded = canonical_json_bytes(document)
            if len(encoded) > MAX_BYTES:
                raise ValueError("R24-S2 fake owner history exceeds its byte bound")
            _parse_history(document, expected_project_id=project)
            return encoded

        _owner_port_transaction(port, update_port)
        return read_current(
            port,
            project_id=project,
            operation_id=operation,
            expected_ticket_id=ticket,
            candidate_id=str(body["candidate_id"]),
            expected_call_sha256=str(body["call_sha256"]),
            expected_sink_sha256=str(body["sink_sha256"]),
            expected_result_sha256=str(body["result_sha256"]),
            expected_publication_readback_sha256=str(body["publication_readback_sha256"]),
            expected_task074_s1_coordinate_sha256=coordinate,
            expected_task074_s1_decision_sha256=decision,
            expected_record_sha256=candidate.record_sha256,
        )


def read_current(
    port: Task014R24FakePublicationPort,
    *,
    project_id: str,
    operation_id: str,
    expected_ticket_id: str,
    candidate_id: str,
    expected_call_sha256: str,
    expected_sink_sha256: str,
    expected_result_sha256: str,
    expected_publication_readback_sha256: str,
    expected_task074_s1_coordinate_sha256: str,
    expected_task074_s1_decision_sha256: str,
    expected_record_sha256: str | None = None,
) -> _Task014R24EffectZeroCurrentRead:
    project = _identifier(project_id, "project_id")
    operation = _identifier(operation_id, "operation_id")
    ticket = _identifier(expected_ticket_id, "expected_ticket_id")
    candidate_key = _identifier(candidate_id, "candidate_id")
    expected = {
        "TICKET_CHANGED": ticket,
        "CALL_CHANGED": _digest(expected_call_sha256, "expected_call_sha256"),
        "SINK_CHANGED": _digest(expected_sink_sha256, "expected_sink_sha256"),
        "RESULT_CHANGED": _digest(expected_result_sha256, "expected_result_sha256"),
        "PUBLICATION_READBACK_CHANGED": _digest(
            expected_publication_readback_sha256,
            "expected_publication_readback_sha256",
        ),
        "S1_COORDINATE_CHANGED": _digest(
            expected_task074_s1_coordinate_sha256,
            "expected_task074_s1_coordinate_sha256",
        ),
        "S1_DECISION_CHANGED": _digest(
            expected_task074_s1_decision_sha256,
            "expected_task074_s1_decision_sha256",
        ),
    }
    if expected_record_sha256 is not None:
        _digest(expected_record_sha256, "expected_record_sha256")

    def issue_read(
        *,
        state: Task014R24CurrentState,
        store_revision: int | None,
        snapshot_sha256: str | None,
        record_sha256: str | None,
        reason_codes: tuple[str, ...],
        owner_store_read: bool,
        owner_origin_authenticated: bool,
        currentness_verified: bool,
    ) -> _Task014R24EffectZeroCurrentRead:
        read_state = _CurrentReadState(
            state,
            project,
            operation,
            ticket,
            candidate_key,
            store_revision,
            snapshot_sha256,
            record_sha256,
            reason_codes,
            owner_store_read,
            owner_origin_authenticated,
            currentness_verified,
        )
        return _issue_read_capability(read_state)  # type: ignore[return-value]

    snapshot_bytes, owner_written = _read_port_snapshot(port)
    if snapshot_bytes is None:
        return issue_read(
            state=Task014R24CurrentState.STORE_NOT_FOUND,
            store_revision=None,
            snapshot_sha256=None,
            record_sha256=None,
            reason_codes=("OWNER_STORE_NOT_FOUND",),
            owner_store_read=False,
            owner_origin_authenticated=False,
            currentness_verified=False,
        )
    try:
        document = _parse_document_bytes(snapshot_bytes)
        _, entries, revision, snapshot_sha = _parse_history(
            document, expected_project_id=project,
        )
    except _HistoryFault as exc:
        return issue_read(
            state=exc.state,
            store_revision=None,
            snapshot_sha256=None,
            record_sha256=None,
            reason_codes=(exc.reason,),
            owner_store_read=True,
            owner_origin_authenticated=False,
            currentness_verified=False,
        )
    if owner_written is not True:
        return issue_read(
            state=Task014R24CurrentState.BROKEN_CHAIN,
            store_revision=revision,
            snapshot_sha256=snapshot_sha,
            record_sha256=None,
            reason_codes=("UNTRUSTED_FIXTURE_SNAPSHOT",),
            owner_store_read=True,
            owner_origin_authenticated=False,
            currentness_verified=False,
        )
    matching = [
        entry
        for entry in entries
        if entry.to_dict()["operation_id"] == operation
        and entry.to_dict()["candidate_id"] == candidate_key
    ]
    if not matching:
        return issue_read(
            state=Task014R24CurrentState.RECORD_NOT_FOUND,
            store_revision=revision,
            snapshot_sha256=snapshot_sha,
            record_sha256=None,
            reason_codes=("POST_CANDIDATE_NOT_FOUND",),
            owner_store_read=True,
            owner_origin_authenticated=True,
            currentness_verified=False,
        )
    head = matching[-1]
    body = head.to_dict()
    reasons: list[str] = []
    for reason, field in (
        ("TICKET_CHANGED", "ticket_id"),
        ("CALL_CHANGED", "call_sha256"),
        ("SINK_CHANGED", "sink_sha256"),
        ("RESULT_CHANGED", "result_sha256"),
        ("PUBLICATION_READBACK_CHANGED", "publication_readback_sha256"),
        ("S1_COORDINATE_CHANGED", "task074_s1_coordinate_sha256"),
        ("S1_DECISION_CHANGED", "task074_s1_decision_sha256"),
    ):
        if body[field] != expected[reason]:
            reasons.append(reason)
    if expected_record_sha256 is not None and head.record_sha256 != expected_record_sha256:
        reasons.append("POST_HEAD_CHANGED")
    current = not reasons
    return issue_read(
        state=(
            Task014R24CurrentState.CURRENT_EFFECT_ZERO
            if current
            else Task014R24CurrentState.STALE_UPSTREAM
        ),
        store_revision=revision,
        snapshot_sha256=snapshot_sha,
        record_sha256=head.record_sha256,
        reason_codes=tuple(sorted(reasons)),
        owner_store_read=True,
        owner_origin_authenticated=True,
        currentness_verified=current,
    )


def _bind_hidden_globals(function: Any) -> Any:
    sealed = FunctionType(
        function.__code__,
        dict(function.__globals__),
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    sealed.__kwdefaults__ = function.__kwdefaults__
    sealed.__annotations__ = dict(function.__annotations__)
    sealed.__qualname__ = function.__qualname__
    sealed.__doc__ = function.__doc__
    return sealed


read_current = _bind_hidden_globals(read_current)
Task014R24PostCandidate.from_dict = classmethod(
    _bind_hidden_globals(Task014R24PostCandidate.from_dict.__func__)
)
Task014R24PostCandidate.record_sha256 = property(
    _bind_hidden_globals(Task014R24PostCandidate.record_sha256.fget)
)
Task014R24PostCandidate.to_dict = _bind_hidden_globals(
    Task014R24PostCandidate.to_dict
)
Task014R24RestrictedConsumer.__init__ = _bind_hidden_globals(
    Task014R24RestrictedConsumer.__init__
)
Task014R24RestrictedConsumer.append_candidate = _bind_hidden_globals(
    Task014R24RestrictedConsumer.append_candidate
)
del (
    _bind_hidden_globals,
    _burn_consumer,
    _initialize_consumer,
    _issue_read_capability,
    _owner_port_transaction,
    _read_candidate_data,
    _read_port_snapshot,
    _register_candidate,
)


__all__ = [
    "FIXTURE_SCOPE",
    "MAX_BYTES",
    "MAX_ENTRIES",
    "POST_HISTORY_TYPE",
    "POST_RECORD_TYPE",
    "R24_S1_COMPLETION_RECEIPT_SHA256",
    "R24_S1_SOURCE_SHA256",
    "R24_S2_VERSION",
    "TASK014_OWNER_ACCEPTANCE_RECORD_SHA256",
    "TASK074_OWNER_ACCEPTANCE_RECORD_SHA256",
    "Task014R24CurrentState",
    "Task014R24FakePublicationPort",
    "Task014R24PostCandidate",
    "Task014R24RestrictedConsumer",
    "read_current",
]
