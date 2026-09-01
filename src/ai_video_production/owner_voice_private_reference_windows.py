"""Effect-zero Windows preparation trace fixtures for TASK-074.

This module is not the native private-reference broker.  It does not open
audio or transcript files, inspect a DACL, encrypt data, wrap keys, construct
private capabilities, mutate a canonical reference domain, or call a model.
It provides one closed in-memory simulation seam so non-biometric tests can
exercise preparation fault classification and post-commit reply loss while
all producer and native gates remain explicitly unconfirmed.

The nominal public types intentionally do not implement the canonical custody
or reference-domain ports and are not wired into Product composition.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from threading import Lock
from types import MappingProxyType
from typing import Any, Mapping, final
import unicodedata

from .owner_voice_private_reference import (
    OwnerVoiceReferenceMediaFacts,
    OwnerVoiceReferencePreparePlan,
    OwnerVoiceReferenceTranscriptFacts,
    Task046OwnerReferenceTranscriptBindingFixture,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


FIXTURE_REQUEST_CONTRACT_VERSION = (
    "TASK074_WINDOWS_PREPARATION_TRACE_REQUEST_FIXTURE_V1"
)
FIXTURE_RESULT_CONTRACT_VERSION = (
    "TASK074_WINDOWS_PREPARATION_TRACE_RESULT_FIXTURE_V1"
)
FIXTURE_SCOPE = "TASK074_NONNATIVE_WINDOWS_PREPARATION_TRACE_TEST_ONLY"
EXPECTED_CONSUMER = "TASK-074"

EXPECTED_ENCRYPTION_ALGORITHM = "AES-256-GCM"
EXPECTED_KEY_WRAP_SCOPE = "WINDOWS_CURRENT_USER"
EXPECTED_BODY_PROCESSING_MODE = "STREAMING_ONLY"
EXPECTED_PAIR_PUBLISH_MODE = "ALL_OR_NONE"
EXPECTED_DACL_VERIFICATION_MODE = "PINNED_ROOT_IDENTITY"

_REQUEST_HASH_DOMAIN = (
    b"TASK074_WINDOWS_PREPARATION_TRACE_REQUEST_FIXTURE_V1\0"
)
_TRACE_HASH_DOMAIN = b"TASK074_WINDOWS_PREPARATION_TRACE_FIXTURE_V1\0"
_HEAD_HASH_DOMAIN = b"TASK074_WINDOWS_PREPARATION_TRACE_HEAD_FIXTURE_V1\0"
_IDENTITY_HASH_DOMAIN = (
    b"TASK074_WINDOWS_PREPARATION_SYNTHETIC_IDENTITY_FIXTURE_V1\0"
)
_RESULT_HASH_DOMAIN = b"TASK074_WINDOWS_PREPARATION_TRACE_RESULT_FIXTURE_V1\0"
_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$"
)
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$"
)


class PreparationTraceFault(str, Enum):
    NONE = "NONE"
    BEFORE_CHILD_CREATION = "BEFORE_CHILD_CREATION"
    AUDIO_CHILD_BEFORE_IDENTITY_CAS = "AUDIO_CHILD_BEFORE_IDENTITY_CAS"
    TRANSCRIPT_CHILD_BEFORE_IDENTITY_CAS = (
        "TRANSCRIPT_CHILD_BEFORE_IDENTITY_CAS"
    )
    AUDIO_IDENTITY_RECORDED_BEFORE_WRITE = (
        "AUDIO_IDENTITY_RECORDED_BEFORE_WRITE"
    )
    TRANSCRIPT_IDENTITY_RECORDED_BEFORE_WRITE = (
        "TRANSCRIPT_IDENTITY_RECORDED_BEFORE_WRITE"
    )
    AUDIO_ENCRYPTED_BEFORE_READBACK = "AUDIO_ENCRYPTED_BEFORE_READBACK"
    TRANSCRIPT_ENCRYPTED_BEFORE_READBACK = (
        "TRANSCRIPT_ENCRYPTED_BEFORE_READBACK"
    )
    AUDIO_PUBLISHED_BEFORE_TRANSCRIPT = "AUDIO_PUBLISHED_BEFORE_TRANSCRIPT"
    TRANSCRIPT_PUBLISHED_BEFORE_AUDIO = "TRANSCRIPT_PUBLISHED_BEFORE_AUDIO"
    BOTH_PUBLISHED_BEFORE_PAIR = "BOTH_PUBLISHED_BEFORE_PAIR"
    PAIR_PUBLISHED_BEFORE_LIFECYCLE = "PAIR_PUBLISHED_BEFORE_LIFECYCLE"


class PreparationDeliveryFault(str, Enum):
    NONE = "NONE"
    AFTER_COMMIT_BEFORE_READBACK = "AFTER_COMMIT_BEFORE_READBACK"


class PreparationFixtureOutcome(str, Enum):
    PREPARED_SIMULATION_FIXTURE = "PREPARED_SIMULATION_FIXTURE"
    PREPARE_FAILED_NO_DERIVATIVE_FIXTURE = (
        "PREPARE_FAILED_NO_DERIVATIVE_FIXTURE"
    )
    PREPARE_FAILED_FOREIGN_PRESERVED_FIXTURE = (
        "PREPARE_FAILED_FOREIGN_PRESERVED_FIXTURE"
    )
    PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE = (
        "PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE"
    )
    OUTCOME_NOT_CONFIRMED_FIXTURE = "OUTCOME_NOT_CONFIRMED_FIXTURE"


class SimulatedReferenceLifecycleState(str, Enum):
    PREPARED_SIMULATION = "PREPARED_SIMULATION"
    PREPARE_FAILED_NO_DERIVATIVE_SIMULATION = (
        "PREPARE_FAILED_NO_DERIVATIVE_SIMULATION"
    )
    PREPARE_FAILED_RETAINED_SIMULATION = (
        "PREPARE_FAILED_RETAINED_SIMULATION"
    )


class SimulatedRetainedObjectState(str, Enum):
    NONE_SIMULATION = "NONE_SIMULATION"
    PUBLISHED_SIMULATION = "PUBLISHED_SIMULATION"
    FOREIGN_PRESERVED_SIMULATION = "FOREIGN_PRESERVED_SIMULATION"
    RECONCILIATION_REQUIRED_SIMULATION = (
        "RECONCILIATION_REQUIRED_SIMULATION"
    )


class SimulatedRoleState(str, Enum):
    ABSENT_PROVEN_SIMULATION = "ABSENT_PROVEN_SIMULATION"
    FOREIGN_PRESERVED_SIMULATION = "FOREIGN_PRESERVED_SIMULATION"
    IDENTITY_RECORDED_SIMULATION = "IDENTITY_RECORDED_SIMULATION"
    ENCRYPTED_UNPUBLISHED_SIMULATION = "ENCRYPTED_UNPUBLISHED_SIMULATION"
    PUBLISHED_SIMULATION = "PUBLISHED_SIMULATION"


class SimulatedPairLedgerState(str, Enum):
    ABSENT_SIMULATION = "ABSENT_SIMULATION"
    PUBLISHED_SIMULATION = "PUBLISHED_SIMULATION"


class SimulatedLifecyclePublishState(str, Enum):
    NOT_COMMITTED_SIMULATION = "NOT_COMMITTED_SIMULATION"
    COMMITTED_SIMULATION = "COMMITTED_SIMULATION"


class _OperationState(str, Enum):
    CONFLICT_TERMINAL = "CONFLICT_TERMINAL"
    COMMITTED = "COMMITTED"
    AMBIGUOUS_AFTER_COMMIT = "AMBIGUOUS_AFTER_COMMIT"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True)
class _TraceRow:
    outcome: PreparationFixtureOutcome
    lifecycle: SimulatedReferenceLifecycleState
    retained: SimulatedRetainedObjectState
    audio_role: SimulatedRoleState
    transcript_role: SimulatedRoleState
    pair_ledger: SimulatedPairLedgerState
    lifecycle_publish: SimulatedLifecyclePublishState


_ABSENT = SimulatedRoleState.ABSENT_PROVEN_SIMULATION
_FOREIGN = SimulatedRoleState.FOREIGN_PRESERVED_SIMULATION
_IDENTITY = SimulatedRoleState.IDENTITY_RECORDED_SIMULATION
_ENCRYPTED = SimulatedRoleState.ENCRYPTED_UNPUBLISHED_SIMULATION
_PUBLISHED = SimulatedRoleState.PUBLISHED_SIMULATION
_PAIR_ABSENT = SimulatedPairLedgerState.ABSENT_SIMULATION
_PAIR_PUBLISHED = SimulatedPairLedgerState.PUBLISHED_SIMULATION
_LIFECYCLE_UNPUBLISHED = (
    SimulatedLifecyclePublishState.NOT_COMMITTED_SIMULATION
)
_LIFECYCLE_PUBLISHED = SimulatedLifecyclePublishState.COMMITTED_SIMULATION
_FAILED_NO_DERIVATIVE = (
    PreparationFixtureOutcome.PREPARE_FAILED_NO_DERIVATIVE_FIXTURE
)
_FAILED_FOREIGN = (
    PreparationFixtureOutcome.PREPARE_FAILED_FOREIGN_PRESERVED_FIXTURE
)
_FAILED_RECONCILIATION = (
    PreparationFixtureOutcome.PREPARE_FAILED_RECONCILIATION_REQUIRED_FIXTURE
)
_FAILED_RETAINED_STATE = (
    SimulatedReferenceLifecycleState.PREPARE_FAILED_RETAINED_SIMULATION
)
_RECONCILIATION_REQUIRED = (
    SimulatedRetainedObjectState.RECONCILIATION_REQUIRED_SIMULATION
)


TRACE_ROW_BY_FAULT: Mapping[PreparationTraceFault, _TraceRow] = MappingProxyType(
    {
        PreparationTraceFault.NONE: _TraceRow(
            PreparationFixtureOutcome.PREPARED_SIMULATION_FIXTURE,
            SimulatedReferenceLifecycleState.PREPARED_SIMULATION,
            SimulatedRetainedObjectState.PUBLISHED_SIMULATION,
            _PUBLISHED,
            _PUBLISHED,
            _PAIR_PUBLISHED,
            _LIFECYCLE_PUBLISHED,
        ),
        PreparationTraceFault.BEFORE_CHILD_CREATION: _TraceRow(
            _FAILED_NO_DERIVATIVE,
            SimulatedReferenceLifecycleState.PREPARE_FAILED_NO_DERIVATIVE_SIMULATION,
            SimulatedRetainedObjectState.NONE_SIMULATION,
            _ABSENT,
            _ABSENT,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.AUDIO_CHILD_BEFORE_IDENTITY_CAS: _TraceRow(
            _FAILED_FOREIGN,
            _FAILED_RETAINED_STATE,
            SimulatedRetainedObjectState.FOREIGN_PRESERVED_SIMULATION,
            _FOREIGN,
            _ABSENT,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.TRANSCRIPT_CHILD_BEFORE_IDENTITY_CAS: _TraceRow(
            _FAILED_FOREIGN,
            _FAILED_RETAINED_STATE,
            SimulatedRetainedObjectState.FOREIGN_PRESERVED_SIMULATION,
            _ABSENT,
            _FOREIGN,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.AUDIO_IDENTITY_RECORDED_BEFORE_WRITE: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _IDENTITY,
            _ABSENT,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.TRANSCRIPT_IDENTITY_RECORDED_BEFORE_WRITE: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _ABSENT,
            _IDENTITY,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.AUDIO_ENCRYPTED_BEFORE_READBACK: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _ENCRYPTED,
            _ABSENT,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.TRANSCRIPT_ENCRYPTED_BEFORE_READBACK: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _ABSENT,
            _ENCRYPTED,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.AUDIO_PUBLISHED_BEFORE_TRANSCRIPT: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _PUBLISHED,
            _ABSENT,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.TRANSCRIPT_PUBLISHED_BEFORE_AUDIO: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _ABSENT,
            _PUBLISHED,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.BOTH_PUBLISHED_BEFORE_PAIR: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _PUBLISHED,
            _PUBLISHED,
            _PAIR_ABSENT,
            _LIFECYCLE_UNPUBLISHED,
        ),
        PreparationTraceFault.PAIR_PUBLISHED_BEFORE_LIFECYCLE: _TraceRow(
            _FAILED_RECONCILIATION,
            _FAILED_RETAINED_STATE,
            _RECONCILIATION_REQUIRED,
            _PUBLISHED,
            _PUBLISHED,
            _PAIR_PUBLISHED,
            _LIFECYCLE_UNPUBLISHED,
        ),
    }
)


_PRODUCER_GATE_STATES = MappingProxyType(
    {
        "G01_PROJECT_BOOTSTRAP": "NOT_CONFIRMED",
        "G02_INSTALLED_STARTUP": "NOT_CONFIRMED",
        "G03_VOICE_PROFILE": "NOT_CONFIRMED",
        "G04_CONSENT": "NOT_CONFIRMED",
        "G05_LOCAL_ROUTE": "NOT_CONFIRMED",
        "G06_HUMAN_ACTION": "NOT_CONFIRMED",
        "G07_OPERATION_TICKET": "NOT_CONFIRMED",
        "G08_PRIVATE_CUSTODY": "NOT_CONFIRMED",
        "G09_PURGE": "NOT_EVALUATED",
        "G10_TASK046_AMENDMENT": "NOT_CONFIRMED",
        "G11_TASK075_CONSUMER": "NOT_EVALUATED",
        "G12_TRUSTED_TIME": "NOT_CONFIRMED",
        "G13_EXECUTION_CURRENTNESS": "NOT_EVALUATED",
        "G14_REFERENCE_TRANSCRIPT": "NOT_CONFIRMED",
    }
)
_FALSE_EFFECT_FLAGS = MappingProxyType(
    {
        "authority_created": False,
        "private_body_present": False,
        "path_present": False,
        "secret_present": False,
        "filesystem_read_performed": False,
        "filesystem_write_performed": False,
        "native_execution_performed": False,
        "encryption_performed": False,
        "key_wrap_performed": False,
        "dacl_observation_performed": False,
        "clock_read_performed": False,
        "model_loaded": False,
        "inference_started": False,
        "wav_created": False,
        "external_effect_started": False,
    }
)
_FIXTURE_BOUNDARY = MappingProxyType(
    {
        "producer_binding_state": "NOT_BOUND",
        "fixture_only": True,
        "canonical_producer_readback": False,
        "execution_ready": False,
        "canonical_reference_snapshot_created": False,
        "private_capability_created": False,
        "prepared_verification_receipt_created": False,
        "revoke_api_available": False,
        "purge_api_available": False,
        "body_read_api_available": False,
    }
)
_REQUEST_TOKEN = object()
_RESULT_TOKEN = object()
_ATOMIC_TOKEN = object()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    record_name: str,
) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{record_name} fields are not exact")


def _validate_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError(f"{field_name} is invalid")
    normalized = unicodedata.normalize("NFKC", value)
    if (
        _IDENTIFIER_RE.fullmatch(normalized) is None
        or normalized.startswith(".")
        or normalized.endswith(".")
        or ".." in normalized
        or any(token in normalized for token in ("/", "\\", ":"))
    ):
        raise ValueError(
            f"{field_name} contains a host path or violates the identifier grammar"
        )
    return value


def _validate_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or _TIMESTAMP_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical UTC timestamp")
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field_name} is invalid") from exc


def _validate_fixed_boundary(value: Mapping[str, Any]) -> None:
    for name, expected in _FIXTURE_BOUNDARY.items():
        if isinstance(expected, bool):
            if value[name] is not expected:
                raise ValueError(f"{name} violates the fixture boundary")
        elif value[name] != expected:
            raise ValueError(f"{name} violates the fixture boundary")
    for name in _FALSE_EFFECT_FLAGS:
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")


@final
class WindowsPreparationTraceFixtureRequest:
    """Closed body-free request bound to all four typed pure inputs."""

    __slots__ = ("_data",)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("fixture request cannot be subclassed")

    def __init__(
        self,
        data: Mapping[str, Any],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _REQUEST_TOKEN:
            raise TypeError("fixture request must use create/from_dict")
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError("fixture request is immutable")

    def __delattr__(self, name: str) -> None:
        del name
        raise AttributeError("fixture request is immutable")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        fixture_domain_sha256: str,
        expected_fixture_head_sha256: str,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
        trace_fault: PreparationTraceFault = PreparationTraceFault.NONE,
        delivery_fault: PreparationDeliveryFault = PreparationDeliveryFault.NONE,
    ) -> "WindowsPreparationTraceFixtureRequest":
        if not isinstance(plan, OwnerVoiceReferencePreparePlan):
            raise TypeError("plan must be OwnerVoiceReferencePreparePlan")
        if not isinstance(media_facts, OwnerVoiceReferenceMediaFacts):
            raise TypeError("media_facts must be OwnerVoiceReferenceMediaFacts")
        if not isinstance(transcript_facts, OwnerVoiceReferenceTranscriptFacts):
            raise TypeError(
                "transcript_facts must be OwnerVoiceReferenceTranscriptFacts"
            )
        if not isinstance(
            transcript_binding,
            Task046OwnerReferenceTranscriptBindingFixture,
        ):
            raise TypeError(
                "transcript_binding must be "
                "Task046OwnerReferenceTranscriptBindingFixture"
            )
        plan_value = plan.to_dict()
        if operation_id != plan_value["operation_id"]:
            raise ValueError("fixture and prepare-plan operation identities differ")
        body: dict[str, Any] = {
            "contract_version": FIXTURE_REQUEST_CONTRACT_VERSION,
            "record_type": "WindowsPreparationTraceFixtureRequest",
            "task_id": EXPECTED_CONSUMER,
            "expected_consumer": EXPECTED_CONSUMER,
            "fixture_scope": FIXTURE_SCOPE,
            "operation_id": operation_id,
            "fixture_domain_sha256": fixture_domain_sha256,
            "expected_fixture_head_sha256": expected_fixture_head_sha256,
            "prepare_plan_sha256": plan_value["prepare_plan_sha256"],
            "media_facts_sha256": media_facts.to_dict()["media_facts_sha256"],
            "transcript_facts_sha256": transcript_facts.to_dict()[
                "transcript_facts_sha256"
            ],
            "transcript_binding_receipt_sha256": transcript_binding.to_dict()[
                "transcript_binding_receipt_sha256"
            ],
            "trace_fault": (
                trace_fault.value
                if isinstance(trace_fault, PreparationTraceFault)
                else trace_fault
            ),
            "delivery_fault": (
                delivery_fault.value
                if isinstance(delivery_fault, PreparationDeliveryFault)
                else delivery_fault
            ),
            "expected_encryption_algorithm": EXPECTED_ENCRYPTION_ALGORITHM,
            "expected_key_wrap_scope": EXPECTED_KEY_WRAP_SCOPE,
            "expected_body_processing_mode": EXPECTED_BODY_PROCESSING_MODE,
            "expected_pair_publish_mode": EXPECTED_PAIR_PUBLISH_MODE,
            "expected_dacl_verification_mode": EXPECTED_DACL_VERIFICATION_MODE,
            **dict(_FIXTURE_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        body["request_sha256"] = sha256_bytes(
            _REQUEST_HASH_DOMAIN + canonical_json_bytes(body)
        )
        return cls.from_dict(body)

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "WindowsPreparationTraceFixtureRequest":
        expected_fields = {
            "contract_version",
            "record_type",
            "task_id",
            "expected_consumer",
            "fixture_scope",
            "operation_id",
            "fixture_domain_sha256",
            "expected_fixture_head_sha256",
            "prepare_plan_sha256",
            "media_facts_sha256",
            "transcript_facts_sha256",
            "transcript_binding_receipt_sha256",
            "trace_fault",
            "delivery_fault",
            "expected_encryption_algorithm",
            "expected_key_wrap_scope",
            "expected_body_processing_mode",
            "expected_pair_publish_mode",
            "expected_dacl_verification_mode",
            *set(_FIXTURE_BOUNDARY),
            *set(_FALSE_EFFECT_FLAGS),
            "request_sha256",
        }
        _require_exact_fields(
            value,
            expected_fields,
            "WindowsPreparationTraceFixtureRequest",
        )
        if (
            value["contract_version"] != FIXTURE_REQUEST_CONTRACT_VERSION
            or value["record_type"]
            != "WindowsPreparationTraceFixtureRequest"
            or value["task_id"] != EXPECTED_CONSUMER
            or value["expected_consumer"] != EXPECTED_CONSUMER
            or value["fixture_scope"] != FIXTURE_SCOPE
        ):
            raise ValueError("fixture request identity or scope is invalid")
        _validate_identifier(value["operation_id"], "operation_id")
        for name in (
            "fixture_domain_sha256",
            "expected_fixture_head_sha256",
            "prepare_plan_sha256",
            "media_facts_sha256",
            "transcript_facts_sha256",
            "transcript_binding_receipt_sha256",
        ):
            validate_sha256(value[name], field_name=name)
        PreparationTraceFault(value["trace_fault"])
        PreparationDeliveryFault(value["delivery_fault"])
        expected_policy = {
            "expected_encryption_algorithm": EXPECTED_ENCRYPTION_ALGORITHM,
            "expected_key_wrap_scope": EXPECTED_KEY_WRAP_SCOPE,
            "expected_body_processing_mode": EXPECTED_BODY_PROCESSING_MODE,
            "expected_pair_publish_mode": EXPECTED_PAIR_PUBLISH_MODE,
            "expected_dacl_verification_mode": EXPECTED_DACL_VERIFICATION_MODE,
        }
        if any(
            value[name] != expected
            for name, expected in expected_policy.items()
        ):
            raise ValueError("fixture expected policy is not fixed")
        _validate_fixed_boundary(value)
        unsigned = {
            key: copy.deepcopy(item)
            for key, item in value.items()
            if key != "request_sha256"
        }
        expected_digest = sha256_bytes(
            _REQUEST_HASH_DOMAIN + canonical_json_bytes(unsigned)
        )
        if value["request_sha256"] != expected_digest:
            raise ValueError("fixture request digest mismatch")
        return cls(
            _freeze(copy.deepcopy(dict(value))),
            _token=_REQUEST_TOKEN,
        )

    def __copy__(self) -> None:
        raise TypeError("fixture request is non-copyable")

    def __deepcopy__(self, memo: Mapping[int, object]) -> None:
        del memo
        raise TypeError("fixture request is non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("fixture request is non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("fixture request is non-serializable")

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@final
class WindowsPreparationTraceFixtureResult:
    """Nominal fixture result that cannot satisfy a canonical producer port."""

    __slots__ = ("_trace", "_receipt")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("fixture result cannot be subclassed")

    def __init__(
        self,
        trace: Mapping[str, Any] | None,
        receipt: Mapping[str, Any],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise TypeError("fixture result is created only by its runtime")
        stored_trace = (
            None
            if trace is None
            else _freeze(copy.deepcopy(dict(trace)))
        )
        object.__setattr__(self, "_trace", stored_trace)
        object.__setattr__(
            self,
            "_receipt",
            _freeze(copy.deepcopy(dict(receipt))),
        )

    def __setattr__(self, name: str, value: Any) -> None:
        del name, value
        raise AttributeError("fixture result is immutable")

    def __delattr__(self, name: str) -> None:
        del name
        raise AttributeError("fixture result is immutable")

    @classmethod
    def _from_runtime(
        cls,
        *,
        trace: Mapping[str, Any],
        outcome: PreparationFixtureOutcome,
        underlying_outcome: PreparationFixtureOutcome | None,
        delivery_fault: PreparationDeliveryFault,
        delivery_state: str,
        terminal_trace_disclosed: bool,
        readback_at: str,
        _token: object | None = None,
    ) -> "WindowsPreparationTraceFixtureResult":
        if _token is not _ATOMIC_TOKEN:
            raise TypeError("fixture result factory requires the atomic runtime")
        if terminal_trace_disclosed is not True and (
            outcome
            is not PreparationFixtureOutcome.OUTCOME_NOT_CONFIRMED_FIXTURE
            or underlying_outcome is not None
        ):
            raise ValueError(
                "an undisclosed terminal trace must remain outcome-not-confirmed"
            )
        if terminal_trace_disclosed is True and underlying_outcome is None:
            raise ValueError("a disclosed terminal trace requires its outcome")
        _validate_timestamp(readback_at, "readback_at")
        trace_value = copy.deepcopy(dict(trace))
        receipt: dict[str, Any] = {
            "contract_version": FIXTURE_RESULT_CONTRACT_VERSION,
            "record_type": "WindowsPreparationTraceFixtureResult",
            "task_id": EXPECTED_CONSUMER,
            "expected_consumer": EXPECTED_CONSUMER,
            "fixture_scope": FIXTURE_SCOPE,
            "operation_id": trace_value["operation_id"],
            "fixture_domain_sha256": trace_value[
                "fixture_domain_sha256"
            ],
            "request_sha256": trace_value["request_sha256"],
            "predecessor_fixture_head_sha256": trace_value[
                "predecessor_fixture_head_sha256"
            ],
            "result_fixture_head_sha256": (
                trace_value["result_fixture_head_sha256"]
                if terminal_trace_disclosed
                else None
            ),
            "simulated_trace_sha256": (
                trace_value["simulated_trace_sha256"]
                if terminal_trace_disclosed
                else None
            ),
            "trace_truth": "SIMULATED_ONLY",
            "trace_fault": trace_value["trace_fault"],
            "delivery_fault": delivery_fault.value,
            "delivery_state": delivery_state,
            "terminal_trace_disclosed": terminal_trace_disclosed,
            "fixture_outcome": outcome.value,
            "underlying_fixture_outcome": (
                underlying_outcome.value
                if underlying_outcome is not None
                else None
            ),
            "automatic_retry_allowed": False,
            "replay": False,
            "readback_at": readback_at,
            **dict(_FIXTURE_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        receipt["result_receipt_sha256"] = sha256_bytes(
            _RESULT_HASH_DOMAIN + canonical_json_bytes(receipt)
        )
        return cls(
            trace_value if terminal_trace_disclosed else None,
            receipt,
            _token=_RESULT_TOKEN,
        )

    def __copy__(self) -> None:
        raise TypeError("fixture result is non-copyable")

    def __deepcopy__(self, memo: Mapping[int, object]) -> None:
        del memo
        raise TypeError("fixture result is non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("fixture result is non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("fixture result is non-serializable")

    @property
    def outcome(self) -> PreparationFixtureOutcome:
        return PreparationFixtureOutcome(self._receipt["fixture_outcome"])

    @property
    def underlying_outcome(self) -> PreparationFixtureOutcome | None:
        value = self._receipt["underlying_fixture_outcome"]
        return None if value is None else PreparationFixtureOutcome(value)

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

    def fixture_trace(self) -> dict[str, Any] | None:
        return None if self._trace is None else _thaw(self._trace)

    def fixture_receipt(self) -> dict[str, Any]:
        return _thaw(self._receipt)

    def status_only_completion_reference_fields(self) -> dict[str, None]:
        """Return the only safe completion composition for this fixture."""

        return {
            "reference_lifecycle_snapshot_sha256": None,
            "reference_preparation_receipt_sha256": None,
            "reference_capability_binding_sha256": None,
            "reference_media_policy_sha256": None,
            "reference_transcript_binding_receipt_sha256": None,
        }


@dataclass(frozen=True, slots=True)
class _OperationRecord:
    request_sha256: str
    state: _OperationState
    trace_fault: PreparationTraceFault | None
    delivery_fault: PreparationDeliveryFault | None
    underlying_outcome: PreparationFixtureOutcome | None
    result_fixture_head_sha256: str
    trace: Mapping[str, Any] | None


def _synthetic_identity(
    label: str,
    fixture_domain_sha256: str,
    request_sha256: str,
) -> str:
    return sha256_bytes(
        _IDENTITY_HASH_DOMAIN
        + label.encode("ascii")
        + b"\0"
        + canonical_json_bytes(
            {
                "fixture_domain_sha256": fixture_domain_sha256,
                "request_sha256": request_sha256,
            }
        )
    )


@final
class WindowsPreparationTraceFixtureRuntime:
    """Single-operation, in-memory, effect-zero fault trace simulator."""

    __slots__ = (
        "_lock",
        "_fixture_domain_sha256",
        "_fixture_head_sha256",
        "_readback_at",
        "_reconciliation_readback_at",
        "_operations",
        "_ambiguous_operation_id",
        "_terminal",
        "_terminal_append_count",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("fixture runtime cannot be subclassed")

    def __init__(
        self,
        *,
        expected_consumer: str,
        fixture_scope: str,
        fixture_domain_sha256: str,
        initial_fixture_head_sha256: str,
        readback_at: str,
        reconciliation_readback_at: str,
    ) -> None:
        if (
            expected_consumer != EXPECTED_CONSUMER
            or fixture_scope != FIXTURE_SCOPE
        ):
            raise ValueError("fixture runtime consumer or scope is invalid")
        validate_sha256(
            fixture_domain_sha256,
            field_name="fixture_domain_sha256",
        )
        validate_sha256(
            initial_fixture_head_sha256,
            field_name="initial_fixture_head_sha256",
        )
        first = _validate_timestamp(readback_at, "readback_at")
        second = _validate_timestamp(
            reconciliation_readback_at,
            "reconciliation_readback_at",
        )
        if second < first:
            raise ValueError(
                "reconciliation readback precedes the initial readback"
            )
        self._lock = Lock()
        self._fixture_domain_sha256 = fixture_domain_sha256
        self._fixture_head_sha256 = initial_fixture_head_sha256
        self._readback_at = readback_at
        self._reconciliation_readback_at = reconciliation_readback_at
        self._operations: dict[str, _OperationRecord] = {}
        self._ambiguous_operation_id: str | None = None
        self._terminal = False
        self._terminal_append_count = 0

    def __copy__(self) -> None:
        raise TypeError("fixture runtime is non-copyable")

    def __deepcopy__(self, memo: Mapping[int, object]) -> None:
        del memo
        raise TypeError("fixture runtime is non-copyable")

    def __reduce__(self) -> None:
        raise TypeError("fixture runtime is non-serializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("fixture runtime is non-serializable")

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

    @property
    def fixture_head_sha256(self) -> str:
        with self._lock:
            return self._fixture_head_sha256

    @property
    def terminal_append_count(self) -> int:
        with self._lock:
            return self._terminal_append_count

    @property
    def operation_count(self) -> int:
        with self._lock:
            return len(self._operations)

    @property
    def ambiguous_operation_id(self) -> str | None:
        with self._lock:
            return self._ambiguous_operation_id

    def _validated_values(
        self,
        request: WindowsPreparationTraceFixtureRequest,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        if not isinstance(request, WindowsPreparationTraceFixtureRequest):
            raise TypeError(
                "request must be WindowsPreparationTraceFixtureRequest"
            )
        if not isinstance(plan, OwnerVoiceReferencePreparePlan):
            raise TypeError("plan must be OwnerVoiceReferencePreparePlan")
        if not isinstance(media_facts, OwnerVoiceReferenceMediaFacts):
            raise TypeError("media_facts must be OwnerVoiceReferenceMediaFacts")
        if not isinstance(transcript_facts, OwnerVoiceReferenceTranscriptFacts):
            raise TypeError(
                "transcript_facts must be OwnerVoiceReferenceTranscriptFacts"
            )
        if not isinstance(
            transcript_binding,
            Task046OwnerReferenceTranscriptBindingFixture,
        ):
            raise TypeError(
                "transcript_binding must be "
                "Task046OwnerReferenceTranscriptBindingFixture"
            )
        request_value = request.to_dict()
        plan_value = plan.to_dict()
        media_value = media_facts.to_dict()
        transcript_value = transcript_facts.to_dict()
        binding_value = transcript_binding.to_dict()
        if request_value["fixture_domain_sha256"] != (
            self._fixture_domain_sha256
        ):
            raise ValueError("request belongs to a different fixture domain")
        digest_bindings = {
            "prepare_plan_sha256": plan_value["prepare_plan_sha256"],
            "media_facts_sha256": media_value["media_facts_sha256"],
            "transcript_facts_sha256": transcript_value[
                "transcript_facts_sha256"
            ],
            "transcript_binding_receipt_sha256": binding_value[
                "transcript_binding_receipt_sha256"
            ],
        }
        if any(
            request_value[name] != expected
            for name, expected in digest_bindings.items()
        ):
            raise ValueError("request and typed-input digest binding differ")
        if (
            request_value["operation_id"] != plan_value["operation_id"]
            or plan_value["project_id"] != binding_value["project_id"]
            or plan_value["voice_profile_id"]
            != binding_value["voice_profile_id"]
            or plan_value["voice_profile_revision_sha256"]
            != binding_value["voice_profile_revision_sha256"]
            or plan_value["consent_current_evaluation_sha256"]
            != binding_value["consent_current_evaluation_sha256"]
            or plan_value["audio_source_identity_sha256"]
            != binding_value["audio_source_identity_sha256"]
            or media_value["audio_sha256"] != binding_value["audio_sha256"]
            or transcript_value["transcript_utf8_sha256"]
            != binding_value["transcript_utf8_sha256"]
            or transcript_value["transcript_facts_sha256"]
            != binding_value["transcript_facts_sha256"]
            or plan_value["media_facts_sha256"]
            != media_value["media_facts_sha256"]
            or plan_value["transcript_facts_sha256"]
            != transcript_value["transcript_facts_sha256"]
            or plan_value["transcript_binding_receipt_sha256"]
            != binding_value["transcript_binding_receipt_sha256"]
            or not (
                plan_value["media_policy_sha256"]
                == media_value["media_policy_sha256"]
                == transcript_value["media_policy_sha256"]
                == binding_value["media_policy_sha256"]
            )
        ):
            raise ValueError(
                "plan/media/transcript/TASK-046 fixture cross-binding differs"
            )
        return (
            request_value,
            plan_value,
            media_value,
            transcript_value,
            binding_value,
        )

    def _build_trace_locked(
        self,
        *,
        request_value: Mapping[str, Any],
        plan_value: Mapping[str, Any],
        media_value: Mapping[str, Any],
        transcript_value: Mapping[str, Any],
        binding_value: Mapping[str, Any],
        _token: object | None = None,
    ) -> tuple[dict[str, Any], PreparationFixtureOutcome]:
        if _token is not _ATOMIC_TOKEN:
            raise RuntimeError("trace construction requires the atomic runtime")
        fault = PreparationTraceFault(request_value["trace_fault"])
        row = TRACE_ROW_BY_FAULT[fault]
        identities = {
            field_name: _synthetic_identity(
                label,
                self._fixture_domain_sha256,
                request_value["request_sha256"],
            )
            for field_name, label in (
                (
                    "simulated_reservation_identity_sha256",
                    "RESERVATION",
                ),
                (
                    "simulated_intended_audio_identity_sha256",
                    "REFERENCE_AUDIO",
                ),
                (
                    "simulated_intended_transcript_identity_sha256",
                    "REFERENCE_TRANSCRIPT_UTF8",
                ),
                (
                    "simulated_pair_ledger_identity_sha256",
                    "PAIR_LEDGER",
                ),
            )
        }
        if len(set(identities.values())) != len(identities):
            raise RuntimeError("synthetic identities are not domain-separated")
        trace: dict[str, Any] = {
            "contract_version": FIXTURE_RESULT_CONTRACT_VERSION,
            "record_type": "WindowsPreparationTraceFixture",
            "task_id": EXPECTED_CONSUMER,
            "expected_consumer": EXPECTED_CONSUMER,
            "fixture_scope": FIXTURE_SCOPE,
            "operation_id": request_value["operation_id"],
            "fixture_domain_sha256": self._fixture_domain_sha256,
            "predecessor_fixture_head_sha256": self._fixture_head_sha256,
            "request_sha256": request_value["request_sha256"],
            "prepare_plan_sha256": plan_value["prepare_plan_sha256"],
            "media_facts_sha256": media_value["media_facts_sha256"],
            "transcript_facts_sha256": transcript_value[
                "transcript_facts_sha256"
            ],
            "transcript_binding_receipt_sha256": binding_value[
                "transcript_binding_receipt_sha256"
            ],
            "trace_fault": fault.value,
            "trace_truth": "SIMULATED_ONLY",
            "underlying_fixture_outcome": row.outcome.value,
            "simulated_reference_lifecycle_state": row.lifecycle.value,
            "simulated_retained_object_state": row.retained.value,
            "simulated_audio_role_state": row.audio_role.value,
            "simulated_transcript_role_state": row.transcript_role.value,
            "simulated_pair_ledger_state": row.pair_ledger.value,
            "simulated_lifecycle_publish_state": row.lifecycle_publish.value,
            "simulated_capability_issue_state": "NOT_EXECUTED_SIMULATION",
            **identities,
            "expected_encryption_algorithm": EXPECTED_ENCRYPTION_ALGORITHM,
            "expected_key_wrap_scope": EXPECTED_KEY_WRAP_SCOPE,
            "expected_body_processing_mode": EXPECTED_BODY_PROCESSING_MODE,
            "expected_pair_publish_mode": EXPECTED_PAIR_PUBLISH_MODE,
            "expected_dacl_verification_mode": (
                EXPECTED_DACL_VERIFICATION_MODE
            ),
            "encryption_observation": "NOT_EXECUTED",
            "key_wrap_observation": "NOT_EXECUTED",
            "streaming_observation": "NOT_EXECUTED",
            "native_observation": "NOT_EXECUTED",
            "dacl_observation": "NOT_CONFIRMED",
            "custody_observation": "NOT_CONFIRMED",
            "producer_gates": dict(_PRODUCER_GATE_STATES),
            "actual_native_contract_coverage": "NOT_CONFIRMED",
            "task074_c_completion_state": "NOT_CONFIRMED",
            "task074_d_completion_state": "NOT_CONFIRMED",
            **dict(_FIXTURE_BOUNDARY),
            **dict(_FALSE_EFFECT_FLAGS),
        }
        trace_sha256 = sha256_bytes(
            _TRACE_HASH_DOMAIN + canonical_json_bytes(trace)
        )
        result_head = sha256_bytes(
            _HEAD_HASH_DOMAIN
            + canonical_json_bytes(
                {
                    "fixture_domain_sha256": self._fixture_domain_sha256,
                    "predecessor_fixture_head_sha256": (
                        self._fixture_head_sha256
                    ),
                    "request_sha256": request_value["request_sha256"],
                    "simulated_trace_sha256": trace_sha256,
                }
            )
        )
        trace["simulated_trace_sha256"] = trace_sha256
        trace["result_fixture_head_sha256"] = result_head
        return trace, row.outcome

    def simulate_prepare(
        self,
        request: WindowsPreparationTraceFixtureRequest,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
    ) -> WindowsPreparationTraceFixtureResult:
        with self._lock:
            return self.__simulate_prepare_locked(
                request,
                plan,
                media_facts,
                transcript_facts,
                transcript_binding,
                _token=_ATOMIC_TOKEN,
            )

    def __simulate_prepare_locked(
        self,
        request: WindowsPreparationTraceFixtureRequest,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
        *,
        _token: object | None = None,
    ) -> WindowsPreparationTraceFixtureResult:
        if _token is not _ATOMIC_TOKEN:
            raise RuntimeError(
                "fixture preparation internals require the atomic public seam"
            )
        if self._ambiguous_operation_id is not None:
            raise RuntimeError(
                "ambiguous fixture commit must be reconciled before any operation"
            )
        if self._terminal:
            raise RuntimeError("fixture runtime is terminal and single-use")
        (
            request_value,
            plan_value,
            media_value,
            transcript_value,
            binding_value,
        ) = self._validated_values(
            request,
            plan,
            media_facts,
            transcript_facts,
            transcript_binding,
        )
        operation_id = request_value["operation_id"]
        if operation_id in self._operations:
            raise ValueError("fixture operation is terminal and non-replayable")
        if (
            request_value["expected_fixture_head_sha256"]
            != self._fixture_head_sha256
        ):
            self._operations[operation_id] = _OperationRecord(
                request_value["request_sha256"],
                _OperationState.CONFLICT_TERMINAL,
                None,
                None,
                None,
                self._fixture_head_sha256,
                None,
            )
            raise ValueError("fixture head conflict")
        trace, underlying_outcome = self._build_trace_locked(
            request_value=request_value,
            plan_value=plan_value,
            media_value=media_value,
            transcript_value=transcript_value,
            binding_value=binding_value,
            _token=_ATOMIC_TOKEN,
        )
        result_head = trace["result_fixture_head_sha256"]
        delivery_fault = PreparationDeliveryFault(
            request_value["delivery_fault"]
        )
        operation_state = (
            _OperationState.AMBIGUOUS_AFTER_COMMIT
            if delivery_fault
            is PreparationDeliveryFault.AFTER_COMMIT_BEFORE_READBACK
            else _OperationState.COMMITTED
        )
        self._fixture_head_sha256 = result_head
        self._terminal_append_count += 1
        self._terminal = True
        self._operations[operation_id] = _OperationRecord(
            request_value["request_sha256"],
            operation_state,
            PreparationTraceFault(request_value["trace_fault"]),
            delivery_fault,
            underlying_outcome,
            result_head,
            _freeze(trace),
        )
        if operation_state is _OperationState.AMBIGUOUS_AFTER_COMMIT:
            self._ambiguous_operation_id = operation_id
            outward_outcome = (
                PreparationFixtureOutcome.OUTCOME_NOT_CONFIRMED_FIXTURE
            )
            delivery_state = "REPLY_LOST_SIMULATION"
        else:
            outward_outcome = underlying_outcome
            delivery_state = "DELIVERED_SIMULATION"
        return WindowsPreparationTraceFixtureResult._from_runtime(
            trace=trace,
            outcome=outward_outcome,
            underlying_outcome=(
                None
                if operation_state
                is _OperationState.AMBIGUOUS_AFTER_COMMIT
                else underlying_outcome
            ),
            delivery_fault=delivery_fault,
            delivery_state=delivery_state,
            terminal_trace_disclosed=(
                operation_state is not _OperationState.AMBIGUOUS_AFTER_COMMIT
            ),
            readback_at=self._readback_at,
            _token=_ATOMIC_TOKEN,
        )

    def simulate_reconcile_prepare_unknown(
        self,
        request: WindowsPreparationTraceFixtureRequest,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
    ) -> WindowsPreparationTraceFixtureResult:
        with self._lock:
            return self.__simulate_reconcile_prepare_unknown_locked(
                request,
                plan,
                media_facts,
                transcript_facts,
                transcript_binding,
                _token=_ATOMIC_TOKEN,
            )

    def __simulate_reconcile_prepare_unknown_locked(
        self,
        request: WindowsPreparationTraceFixtureRequest,
        plan: OwnerVoiceReferencePreparePlan,
        media_facts: OwnerVoiceReferenceMediaFacts,
        transcript_facts: OwnerVoiceReferenceTranscriptFacts,
        transcript_binding: Task046OwnerReferenceTranscriptBindingFixture,
        *,
        _token: object | None = None,
    ) -> WindowsPreparationTraceFixtureResult:
        if _token is not _ATOMIC_TOKEN:
            raise RuntimeError(
                "fixture reconciliation internals require the atomic public seam"
            )
        (
            request_value,
            _plan_value,
            _media_value,
            _transcript_value,
            _binding_value,
        ) = self._validated_values(
            request,
            plan,
            media_facts,
            transcript_facts,
            transcript_binding,
        )
        operation_id = request_value["operation_id"]
        record = self._operations.get(operation_id)
        if (
            self._ambiguous_operation_id != operation_id
            or record is None
            or record.state is not _OperationState.AMBIGUOUS_AFTER_COMMIT
            or record.request_sha256 != request_value["request_sha256"]
            or record.delivery_fault
            is not PreparationDeliveryFault.AFTER_COMMIT_BEFORE_READBACK
            or record.underlying_outcome is None
            or record.trace is None
            or record.result_fixture_head_sha256
            != self._fixture_head_sha256
        ):
            raise ValueError(
                "operation has no exact reconcilable fixture commit"
            )
        trace = _thaw(record.trace)
        if trace["result_fixture_head_sha256"] != (
            self._fixture_head_sha256
        ):
            raise RuntimeError("fixture trace and head are not exact")
        self._operations[operation_id] = _OperationRecord(
            record.request_sha256,
            _OperationState.RECONCILED,
            record.trace_fault,
            record.delivery_fault,
            record.underlying_outcome,
            record.result_fixture_head_sha256,
            record.trace,
        )
        self._ambiguous_operation_id = None
        return WindowsPreparationTraceFixtureResult._from_runtime(
            trace=trace,
            outcome=record.underlying_outcome,
            underlying_outcome=record.underlying_outcome,
            delivery_fault=(
                PreparationDeliveryFault.AFTER_COMMIT_BEFORE_READBACK
            ),
            delivery_state="RECONCILED_SIMULATION",
            terminal_trace_disclosed=True,
            readback_at=self._reconciliation_readback_at,
            _token=_ATOMIC_TOKEN,
        )


__all__ = [
    "EXPECTED_BODY_PROCESSING_MODE",
    "EXPECTED_CONSUMER",
    "EXPECTED_DACL_VERIFICATION_MODE",
    "EXPECTED_ENCRYPTION_ALGORITHM",
    "EXPECTED_KEY_WRAP_SCOPE",
    "EXPECTED_PAIR_PUBLISH_MODE",
    "FIXTURE_REQUEST_CONTRACT_VERSION",
    "FIXTURE_RESULT_CONTRACT_VERSION",
    "FIXTURE_SCOPE",
    "PreparationDeliveryFault",
    "PreparationFixtureOutcome",
    "PreparationTraceFault",
    "SimulatedLifecyclePublishState",
    "SimulatedPairLedgerState",
    "SimulatedReferenceLifecycleState",
    "SimulatedRetainedObjectState",
    "SimulatedRoleState",
    "TRACE_ROW_BY_FAULT",
    "WindowsPreparationTraceFixtureRequest",
    "WindowsPreparationTraceFixtureResult",
    "WindowsPreparationTraceFixtureRuntime",
]
