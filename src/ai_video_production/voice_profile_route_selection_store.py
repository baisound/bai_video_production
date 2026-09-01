"""Fixture-only in-memory CAS seam for TASK-074 route-selection tests.

This module deliberately is not the TASK-043 canonical Project transaction
adapter.  Every result remains producer-unbound, non-executable fixture
evidence through :class:`VoiceRouteSelectionCASReadback`.  It performs no
filesystem, database, media, model, provider, native, or clock I/O.

The seam exists only to exercise the frozen F01-F03 recovery boundaries before
the canonical TASK-043/TASK-071/TASK-072 producer contracts are available.
It cannot satisfy G01, G02, G06, G07, or G10 and is not wired into Product
composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from threading import Lock
from typing import Any, Mapping, final
import unicodedata

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_route_selection import (
    CASOutcome,
    VoiceProfileRouteSelection,
    VoiceRouteSelectionCASReadback,
    VoiceRouteSelectionCASRequest,
)


FIXTURE_STORE_CONTRACT_VERSION = "VOICE_ROUTE_SELECTION_FIXTURE_STORE_V1"
FIXTURE_SCOPE = "TASK074_PURE_TEST_ONLY"
EXPECTED_CONSUMER = "TASK-074"

_PROJECT_HEAD_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_FIXTURE_PROJECT_HEAD_V1\0"
_EXTERNAL_HEAD_DOMAIN = b"TASK074_VOICE_ROUTE_SELECTION_FIXTURE_EXTERNAL_HEAD_V1\0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class FixtureCASFault(str, Enum):
    """One-shot deterministic fault injected into the next valid CAS."""

    NONE = "NONE"
    BEFORE_COMMIT = "BEFORE_COMMIT"
    AFTER_COMMIT_BEFORE_PINNED_READBACK = "AFTER_COMMIT_BEFORE_PINNED_READBACK"
    PROJECT_HEAD_CHANGED_DURING_CAS = "PROJECT_HEAD_CHANGED_DURING_CAS"


class FixtureCASResultState(str, Enum):
    """Nominal fixture result states; not the canonical port result type."""

    COMMITTED_FIXTURE = "COMMITTED_FIXTURE"
    CONFLICT_FIXTURE = "CONFLICT_FIXTURE"
    NOT_CONFIRMED_FIXTURE = "NOT_CONFIRMED_FIXTURE"


class _OperationState(str, Enum):
    COMMITTED = "COMMITTED"
    CONFLICT = "CONFLICT"
    FAILED_BEFORE_COMMIT = "FAILED_BEFORE_COMMIT"
    AMBIGUOUS_AFTER_COMMIT = "AMBIGUOUS_AFTER_COMMIT"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True)
class _OperationRecord:
    request_sha256: str
    selection_sha256: str
    result_project_transaction_head_sha256: str
    state: _OperationState


_RESULT_STATE_BY_OUTCOME = {
    CASOutcome.COMMITTED: FixtureCASResultState.COMMITTED_FIXTURE,
    CASOutcome.CONFLICT: FixtureCASResultState.CONFLICT_FIXTURE,
    CASOutcome.NOT_CONFIRMED: FixtureCASResultState.NOT_CONFIRMED_FIXTURE,
}
_RESULT_CONSTRUCTION_TOKEN = object()
_ATOMIC_EXECUTION_TOKEN = object()


@final
class VoiceRouteSelectionFixtureCASResult:
    """Nominal fixture result that cannot satisfy the canonical store port."""

    __slots__ = ("_readback",)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("fixture CAS result cannot be subclassed")

    def __init__(
        self,
        readback: VoiceRouteSelectionCASReadback,
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_CONSTRUCTION_TOKEN:
            raise TypeError("fixture CAS result is created only by the fixture seam")
        if not isinstance(readback, VoiceRouteSelectionCASReadback):
            raise TypeError("fixture CAS result requires a typed fixture readback")
        object.__setattr__(self, "_readback", readback)

    @classmethod
    def _create(
        cls,
        readback: VoiceRouteSelectionCASReadback,
    ) -> "VoiceRouteSelectionFixtureCASResult":
        return cls(readback, _token=_RESULT_CONSTRUCTION_TOKEN)

    def __copy__(self) -> None:
        raise TypeError("fixture CAS result is non-copyable")

    def __deepcopy__(self, memo: Mapping[int, object]) -> None:
        del memo
        raise TypeError("fixture CAS result is non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("fixture CAS result is non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("fixture CAS result is non-serializable")

    @property
    def state(self) -> FixtureCASResultState:
        return _RESULT_STATE_BY_OUTCOME[CASOutcome(self._readback.to_dict()["outcome"])]

    @property
    def fixture_only(self) -> bool:
        return True

    @property
    def canonical_port_compatible(self) -> bool:
        return False

    @property
    def producer_binding_state(self) -> str:
        return "NOT_BOUND"

    @property
    def execution_ready(self) -> bool:
        return False

    def fixture_readback(self) -> VoiceRouteSelectionCASReadback:
        """Return typed body-free fixture evidence, never canonical authority."""

        return VoiceRouteSelectionCASReadback.from_dict(self._readback.to_dict())


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError(f"{name} is invalid")
    normalized = unicodedata.normalize("NFKC", value)
    if (
        any(token in normalized for token in ("/", "\\", ":"))
        or normalized.startswith(".")
        or normalized.endswith(".")
        or ".." in normalized
        or _ID_RE.fullmatch(normalized) is None
    ):
        raise ValueError(f"{name} contains a host path or violates the closed identifier grammar")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or _TIME_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical UTC timestamp")
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} is invalid") from exc


def _next_project_head(
    previous_head_sha256: str,
    request: Mapping[str, Any],
    selection_sha256: str,
) -> str:
    return sha256_bytes(
        _PROJECT_HEAD_DOMAIN
        + canonical_json_bytes(
            {
                "previous_project_transaction_head_sha256": previous_head_sha256,
                "operation_id": request["operation_id"],
                "cas_request_sha256": request["cas_request_sha256"],
                "selection_sha256": selection_sha256,
            }
        )
    )


def _externally_advanced_project_head(
    previous_head_sha256: str,
    request: Mapping[str, Any],
) -> str:
    return sha256_bytes(
        _EXTERNAL_HEAD_DOMAIN
        + canonical_json_bytes(
            {
                "previous_project_transaction_head_sha256": previous_head_sha256,
                "operation_id": request["operation_id"],
                "cas_request_sha256": request["cas_request_sha256"],
            }
        )
    )


@final
class VoiceRouteSelectionFixtureStore:
    """Non-serializable, producer-unbound in-memory CAS test seam.

    Its nominal ``simulate_*`` API intentionally does not satisfy the frozen
    ``VoiceRouteSelectionStorePort`` Protocol.  Results retain the TASK074-B
    fixture boundary, so the object cannot substitute for a canonical Project
    transaction adapter.
    """

    __slots__ = (
        "_project_id",
        "_project_transaction_head_sha256",
        "_selection_head_sha256",
        "_selection_revision",
        "_pinned_store_identity_sha256",
        "_readback_at",
        "_reconciliation_readback_at",
        "_next_fault",
        "_operations",
        "_ambiguous_operation_id",
        "_lock",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("fixture store cannot be subclassed or promoted to a producer adapter")

    def __init__(
        self,
        *,
        project_id: str,
        initial_project_transaction_head_sha256: str,
        pinned_fixture_store_identity_sha256: str,
        readback_at: str,
        reconciliation_readback_at: str,
        expected_consumer: str,
        fixture_scope: str,
        next_fault: FixtureCASFault = FixtureCASFault.NONE,
    ) -> None:
        if expected_consumer != EXPECTED_CONSUMER:
            raise ValueError("fixture store consumer must be TASK-074")
        if fixture_scope != FIXTURE_SCOPE:
            raise ValueError("fixture store requires the exact pure-test scope")
        if not isinstance(next_fault, FixtureCASFault):
            raise TypeError("next_fault must use FixtureCASFault")
        self._project_id = _identifier(project_id, "project_id")
        self._project_transaction_head_sha256 = validate_sha256(
            initial_project_transaction_head_sha256,
            field_name="initial_project_transaction_head_sha256",
        )
        self._pinned_store_identity_sha256 = validate_sha256(
            pinned_fixture_store_identity_sha256,
            field_name="pinned_fixture_store_identity_sha256",
        )
        self._selection_head_sha256: str | None = None
        self._selection_revision = 0
        readback_time = _timestamp(readback_at, "readback_at")
        reconciliation_time = _timestamp(
            reconciliation_readback_at,
            "reconciliation_readback_at",
        )
        if reconciliation_time < readback_time:
            raise ValueError("reconciliation readback cannot predate the initial readback")
        self._readback_at = readback_at
        self._reconciliation_readback_at = reconciliation_readback_at
        self._next_fault = next_fault
        self._operations: dict[str, _OperationRecord] = {}
        self._ambiguous_operation_id: str | None = None
        self._lock = Lock()

    def __copy__(self) -> None:
        raise TypeError("fixture store is non-copyable")

    def __deepcopy__(self, memo: Mapping[int, object]) -> None:
        del memo
        raise TypeError("fixture store is non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("fixture store is non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("fixture store is non-serializable")

    @property
    def contract_version(self) -> str:
        return FIXTURE_STORE_CONTRACT_VERSION

    @property
    def expected_consumer(self) -> str:
        return EXPECTED_CONSUMER

    @property
    def fixture_scope(self) -> str:
        return FIXTURE_SCOPE

    @property
    def canonical_port_compatible(self) -> bool:
        return False

    @property
    def fixture_only(self) -> bool:
        return True

    @property
    def producer_binding_state(self) -> str:
        return "NOT_BOUND"

    @property
    def canonical_producer_readback(self) -> bool:
        return False

    @property
    def authority_created(self) -> bool:
        return False

    @property
    def execution_ready(self) -> bool:
        return False

    @property
    def production_eligible(self) -> bool:
        return False

    @property
    def durable_persistence_performed(self) -> bool:
        return False

    @property
    def external_effect_performed(self) -> bool:
        return False

    @property
    def private_body_present(self) -> bool:
        return False

    @property
    def path_present(self) -> bool:
        return False

    @property
    def secret_present(self) -> bool:
        return False

    @property
    def project_transaction_head_sha256(self) -> str:
        with self._lock:
            return self._project_transaction_head_sha256

    @property
    def selection_head_sha256(self) -> str | None:
        with self._lock:
            return self._selection_head_sha256

    @property
    def selection_revision(self) -> int:
        with self._lock:
            return self._selection_revision

    def _validate_inputs(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(request, VoiceRouteSelectionCASRequest):
            raise TypeError("request must be VoiceRouteSelectionCASRequest")
        if not isinstance(selection, VoiceProfileRouteSelection):
            raise TypeError("selection must be VoiceProfileRouteSelection")
        request_value = request.to_dict()
        selection_value = selection.to_dict()
        if selection_value["project_id"] != self._project_id:
            raise ValueError("selection Project does not match the fixture store")
        if request_value["selection_sha256"] != selection_value["selection_sha256"]:
            raise ValueError("CAS request/selection digest mismatch")
        if request_value["selection_revision"] != selection_value["selection_revision"]:
            raise ValueError("CAS request/selection revision mismatch")
        if (
            request_value["expected_selection_head_sha256"]
            != selection_value["predecessor_selection_sha256"]
        ):
            raise ValueError("CAS request does not bind the selection predecessor")
        if request_value["operation_id"] in self._operations:
            raise ValueError("fixture operation id is terminal and non-replayable")
        if self._ambiguous_operation_id is not None:
            raise RuntimeError("ambiguous post-commit state must be reconciled before another CAS")
        return request_value, selection_value

    def _readback(
        self,
        *,
        request: VoiceRouteSelectionCASRequest,
        outcome: CASOutcome,
        committed_selection_sha256: str | None,
        pinned_readback_match: bool,
        readback_at: str,
    ) -> VoiceRouteSelectionFixtureCASResult:
        readback = VoiceRouteSelectionCASReadback.create(
            request=request,
            outcome=outcome,
            result_project_transaction_head_sha256=self._project_transaction_head_sha256,
            result_selection_head_sha256=self._selection_head_sha256,
            committed_selection_sha256=committed_selection_sha256,
            pinned_store_identity_sha256=self._pinned_store_identity_sha256,
            pinned_readback_match=pinned_readback_match,
            readback_at=readback_at,
        )
        return VoiceRouteSelectionFixtureCASResult._create(readback)

    def simulate_compare_and_append(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
    ) -> VoiceRouteSelectionFixtureCASResult:
        """Atomically simulate one fixture CAS under a single in-memory lock."""

        with self._lock:
            return self.__simulate_compare_and_append_locked(
                request,
                selection,
                _token=_ATOMIC_EXECUTION_TOKEN,
            )

    def __simulate_compare_and_append_locked(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
        *,
        _token: object | None = None,
    ) -> VoiceRouteSelectionFixtureCASResult:
        """Run one fixture CAS without any durable or external effect."""

        if _token is not _ATOMIC_EXECUTION_TOKEN:
            raise RuntimeError("fixture CAS internals require the atomic public seam")
        request_value, selection_value = self._validate_inputs(request, selection)
        operation_id = request_value["operation_id"]
        selection_sha256 = selection_value["selection_sha256"]
        expected_matches = (
            request_value["expected_project_transaction_head_sha256"]
            == self._project_transaction_head_sha256
            and request_value["expected_selection_head_sha256"] == self._selection_head_sha256
            and selection_value["predecessor_selection_sha256"] == self._selection_head_sha256
            and selection_value["selection_revision"] == self._selection_revision + 1
        )
        if not expected_matches:
            self._operations[operation_id] = _OperationRecord(
                request_value["cas_request_sha256"],
                selection_sha256,
                self._project_transaction_head_sha256,
                _OperationState.CONFLICT,
            )
            return self._readback(
                request=request,
                outcome=CASOutcome.CONFLICT,
                committed_selection_sha256=None,
                pinned_readback_match=False,
                readback_at=self._readback_at,
            )

        fault = self._next_fault
        self._next_fault = FixtureCASFault.NONE

        if fault is FixtureCASFault.PROJECT_HEAD_CHANGED_DURING_CAS:
            self._project_transaction_head_sha256 = _externally_advanced_project_head(
                self._project_transaction_head_sha256,
                request_value,
            )
            self._operations[operation_id] = _OperationRecord(
                request_value["cas_request_sha256"],
                selection_sha256,
                self._project_transaction_head_sha256,
                _OperationState.CONFLICT,
            )
            return self._readback(
                request=request,
                outcome=CASOutcome.CONFLICT,
                committed_selection_sha256=None,
                pinned_readback_match=False,
                readback_at=self._readback_at,
            )

        if fault is FixtureCASFault.BEFORE_COMMIT:
            self._operations[operation_id] = _OperationRecord(
                request_value["cas_request_sha256"],
                selection_sha256,
                self._project_transaction_head_sha256,
                _OperationState.FAILED_BEFORE_COMMIT,
            )
            return self._readback(
                request=request,
                outcome=CASOutcome.NOT_CONFIRMED,
                committed_selection_sha256=None,
                pinned_readback_match=False,
                readback_at=self._readback_at,
            )

        self._project_transaction_head_sha256 = _next_project_head(
            self._project_transaction_head_sha256,
            request_value,
            selection_sha256,
        )
        self._selection_head_sha256 = selection_sha256
        self._selection_revision = selection_value["selection_revision"]

        if fault is FixtureCASFault.AFTER_COMMIT_BEFORE_PINNED_READBACK:
            self._operations[operation_id] = _OperationRecord(
                request_value["cas_request_sha256"],
                selection_sha256,
                self._project_transaction_head_sha256,
                _OperationState.AMBIGUOUS_AFTER_COMMIT,
            )
            self._ambiguous_operation_id = operation_id
            return self._readback(
                request=request,
                outcome=CASOutcome.NOT_CONFIRMED,
                committed_selection_sha256=None,
                pinned_readback_match=False,
                readback_at=self._readback_at,
            )

        self._operations[operation_id] = _OperationRecord(
            request_value["cas_request_sha256"],
            selection_sha256,
            self._project_transaction_head_sha256,
            _OperationState.COMMITTED,
        )
        return self._readback(
            request=request,
            outcome=CASOutcome.COMMITTED,
            committed_selection_sha256=selection_sha256,
            pinned_readback_match=True,
            readback_at=self._readback_at,
        )

    def simulate_reconcile_after_unknown(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
    ) -> VoiceRouteSelectionFixtureCASResult:
        """Atomically reconcile one exact F02 fixture commit after reply loss."""

        with self._lock:
            return self.__simulate_reconcile_after_unknown_locked(
                request,
                selection,
                _token=_ATOMIC_EXECUTION_TOKEN,
            )

    def __simulate_reconcile_after_unknown_locked(
        self,
        request: VoiceRouteSelectionCASRequest,
        selection: VoiceProfileRouteSelection,
        *,
        _token: object | None = None,
    ) -> VoiceRouteSelectionFixtureCASResult:
        """Pin/read back one exact F02 fixture commit after reply loss."""

        if _token is not _ATOMIC_EXECUTION_TOKEN:
            raise RuntimeError("fixture reconciliation internals require the atomic public seam")
        if not isinstance(request, VoiceRouteSelectionCASRequest):
            raise TypeError("request must be VoiceRouteSelectionCASRequest")
        if not isinstance(selection, VoiceProfileRouteSelection):
            raise TypeError("selection must be VoiceProfileRouteSelection")
        request_value = request.to_dict()
        selection_value = selection.to_dict()
        operation_id = request_value["operation_id"]
        record = self._operations.get(operation_id)
        if (
            self._ambiguous_operation_id != operation_id
            or record is None
            or record.state is not _OperationState.AMBIGUOUS_AFTER_COMMIT
        ):
            raise ValueError("operation has no reconcilable ambiguous fixture commit")
        if (
            record.request_sha256 != request_value["cas_request_sha256"]
            or record.selection_sha256 != selection_value["selection_sha256"]
            or request_value["selection_sha256"] != selection_value["selection_sha256"]
            or record.result_project_transaction_head_sha256
            != self._project_transaction_head_sha256
            or selection_value["selection_sha256"] != self._selection_head_sha256
        ):
            raise ValueError("ambiguous fixture reconciliation lineage or pinned state mismatch")

        self._operations[operation_id] = _OperationRecord(
            record.request_sha256,
            record.selection_sha256,
            record.result_project_transaction_head_sha256,
            _OperationState.RECONCILED,
        )
        self._ambiguous_operation_id = None
        return self._readback(
            request=request,
            outcome=CASOutcome.COMMITTED,
            committed_selection_sha256=selection_value["selection_sha256"],
            pinned_readback_match=True,
            readback_at=self._reconciliation_readback_at,
        )


__all__ = [
    "EXPECTED_CONSUMER",
    "FIXTURE_SCOPE",
    "FIXTURE_STORE_CONTRACT_VERSION",
    "FixtureCASFault",
    "FixtureCASResultState",
    "VoiceRouteSelectionFixtureCASResult",
    "VoiceRouteSelectionFixtureStore",
]
