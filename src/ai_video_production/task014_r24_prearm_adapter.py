"""R24-S3 synthetic, effect-zero coordinated-prearm adapter.

This module models the accepted TASK-014/TASK-072/TASK-075/TASK-076
coordination amendment without calling a canonical broker, arm ABI, custody
owner, process, Project store, Provider, model, audio or publication surface.
All positive objects are sealed process-local fixture capabilities.
"""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from threading import Lock, RLock
from types import FunctionType
from typing import Any
from weakref import WeakKeyDictionary


R24_S3_VERSION = "TASK014_R24_S3_COORDINATED_PREARM_EFFECT_ZERO_V1"
AMENDMENT_IDENTITY = (
    "TASK014_TASK072_TASK075_TASK076_"
    "COORDINATED_PREARM_RESERVATION_AMENDMENT_V1"
)
FIXTURE_SCOPE = "TASK014_R24_S3_SYNTHETIC_EFFECT_ZERO"

R24_DESIGN_SHA256 = (
    "80A8D48BDF4D7A29D11DF07780CEDDB4D707135D47A8833F616D76BF8B18FFB5"
)
R24_S0A_RECEIPT_SHA256 = (
    "128024E0EF509BA857F5B882363886BFF19BE79FCD569569B48FFFAB292EA9F2"
)
R24_S1_SOURCE_SHA256 = (
    "B2450071427D2752C4FF381746EE680E1025C8E8BB89AD6FAB1C81EDA4CC2BD3"
)
R24_S2_SOURCE_SHA256 = (
    "9F3462E2FDE7CAE5B330888EEAA2A88FA87FFF439B31BC5CB1FDBB3D4204A880"
)
TASK014_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "A398A9FE13F886DC6A4783B2AB3EEAB61721598F20F27ABAC2C0EB2811CBB06B"
)
TASK074_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0"
)
TASK041_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "AFDDFDF428BB0A98272F20E68CFBE906266218C40D2BFA1955F7ED23480A6853"
)
TASK036_OWNER_ACCEPTANCE_RECORD_SHA256 = (
    "78A998DDD65209EBF108755599A1AD755843F022B692277CADD18DD099BE5BAB"
)

_FALSE_EFFECT_NAMES = (
    "source_authority",
    "effect_authority",
    "canonical_runtime_type_minted",
    "project_store_written",
    "filesystem_written",
    "network_entered",
    "process_started",
    "private_body_read",
    "provider_entered",
    "model_loaded",
    "audio_read",
    "wav_written",
    "asset_written",
    "publication_current_minted",
    "downstream_pass_minted",
)


class Task014R24PrearmOwner(str, Enum):
    TASK014 = "TASK-014"
    TASK072 = "TASK-072"
    TASK075 = "TASK-075"
    TASK076 = "TASK-076"


class Task014R24ReservationState(str, Enum):
    RESERVED = "RESERVED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED_KNOWN = "CANCELLED_KNOWN"
    CANCEL_UNKNOWN = "CANCEL_UNKNOWN"
    ARMING = "ARMING"
    JOIN_PENDING = "JOIN_PENDING"
    ARMED_CONSUMED = "ARMED_CONSUMED"
    ARM_REJECTED = "ARM_REJECTED"
    ARM_UNKNOWN = "ARM_UNKNOWN"


class Task014R24CoordinatorState(str, Enum):
    CLAIM_INTENT = "CLAIM_INTENT"
    TASK014_CLAIMED = "TASK014_CLAIMED"
    ARM_CALL_ENTERING = "ARM_CALL_ENTERING"
    TASK076_RESULT_OBSERVED = "TASK076_RESULT_OBSERVED"
    JOINED = "JOINED"


class Task014R24OwnerQuery(str, Enum):
    NOT_ENTERED_KNOWN = "NOT_ENTERED_KNOWN"
    JOB_CHILD_ARMED_READBACK_V3 = "JOB_CHILD_ARMED_READBACK_V3"
    JOB_CHILD_REJECTED_READBACK_V3 = "JOB_CHILD_REJECTED_READBACK_V3"
    JOB_CHILD_BURNED_UNKNOWN_READBACK_V3 = (
        "JOB_CHILD_BURNED_UNKNOWN_READBACK_V3"
    )
    ATTEMPT_TRUTH_UNKNOWN = "ATTEMPT_TRUTH_UNKNOWN"


class Task014R24PrearmScenario(str, Enum):
    CANCEL_KNOWN = "CANCEL_KNOWN"
    CANCEL_UNKNOWN = "CANCEL_UNKNOWN"
    FAILURE_BEFORE_TASK014_CLAIM = "FAILURE_BEFORE_TASK014_CLAIM"
    ARM_NOT_ENTERED = "ARM_NOT_ENTERED"
    ARM_ARMED = "ARM_ARMED"
    ARM_REJECTED = "ARM_REJECTED"
    ARM_UNKNOWN = "ARM_UNKNOWN"
    ATTEMPT_TRUTH_UNKNOWN = "ATTEMPT_TRUTH_UNKNOWN"


class Task014R24PrearmCurrentState(str, Enum):
    CURRENT_EFFECT_ZERO = "CURRENT_EFFECT_ZERO"
    STORE_MISSING = "STORE_MISSING"
    FOREIGN_PROJECT = "FOREIGN_PROJECT"
    STALE_COORDINATE = "STALE_COORDINATE"
    FORKED_CHAIN = "FORKED_CHAIN"
    AMBIGUOUS_TRUTH = "AMBIGUOUS_TRUTH"
    BROKEN_CHAIN = "BROKEN_CHAIN"


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not value or len(value) > 128:
        raise ValueError(f"{name} is invalid")
    if not value.isascii() or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:/"
        for character in value
    ):
        raise ValueError(f"{name} is invalid")
    return value


def _digest_text(*parts: str) -> str:
    material = "\x00".join(parts).encode("ascii")
    return sha256(material).hexdigest().upper()


def _owner_receipt_digest(owner: Task014R24PrearmOwner) -> str:
    return _digest_text(
        "BAI:R24:S3:OWNER-RECEIPT:V1",
        AMENDMENT_IDENTITY,
        owner.value,
        R24_DESIGN_SHA256,
        R24_S0A_RECEIPT_SHA256,
        R24_S1_SOURCE_SHA256,
        R24_S2_SOURCE_SHA256,
        TASK014_OWNER_ACCEPTANCE_RECORD_SHA256,
        TASK074_OWNER_ACCEPTANCE_RECORD_SHA256,
        TASK041_OWNER_ACCEPTANCE_RECORD_SHA256,
        TASK036_OWNER_ACCEPTANCE_RECORD_SHA256,
        FIXTURE_SCOPE,
    )


def _snapshot_digest(state: dict[str, Any]) -> str:
    reservation_trace = ",".join(item.value for item in state["reservation_trace"])
    coordinator_trace = ",".join(item.value for item in state["coordinator_trace"])
    return _digest_text(
        "BAI:R24:S3:SNAPSHOT:V1",
        state["project_id"],
        state["operation_id"],
        state["ticket_id"],
        state["reservation_id"],
        state["claim_id"],
        reservation_trace,
        coordinator_trace,
        state["initial_query"].value if state["initial_query"] else "<NONE>",
        state["join_query"].value if state["join_query"] else "<NONE>",
        str(state["revision"]),
        FIXTURE_SCOPE,
    )


class _SealedCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("R24-S3 capabilities are owner-issued only")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if cls.__bases__ != (_SealedCapability,):
            raise TypeError("R24-S3 capability types are sealed")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("R24-S3 capabilities are immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("R24-S3 capabilities are immutable")

    def __copy__(self) -> Any:
        raise TypeError("R24-S3 capabilities are non-copyable")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("R24-S3 capabilities are non-copyable")

    def __reduce__(self) -> Any:
        raise TypeError("R24-S3 capabilities are non-serializable")

    def __reduce_ex__(self, protocol: int) -> Any:
        raise TypeError("R24-S3 capabilities are non-serializable")


class Task014R24PrearmOwnerReceipt(_SealedCapability):
    __slots__ = ()

    @property
    def owner(self) -> Task014R24PrearmOwner:
        return _receipt_value(self, "owner")

    @property
    def record_sha256(self) -> str:
        return _receipt_value(self, "record_sha256")

    @property
    def fixture_only(self) -> bool:
        return True

    @property
    def source_authority(self) -> bool:
        return False

    @property
    def effect_authority(self) -> bool:
        return False


class Task014R24PrearmOwnerReceiptSet(_SealedCapability):
    __slots__ = ()

    @property
    def amendment_identity(self) -> str:
        _receipt_set_items(self)
        return AMENDMENT_IDENTITY

    @property
    def owners(self) -> tuple[Task014R24PrearmOwner, ...]:
        return tuple(item.owner for item in _receipt_set_items(self))

    def receipt_for(
        self, owner: Task014R24PrearmOwner
    ) -> Task014R24PrearmOwnerReceipt:
        if type(owner) is not Task014R24PrearmOwner:
            raise TypeError("R24-S3 owner type is invalid")
        for item in _receipt_set_items(self):
            if item.owner is owner:
                return item
        raise RuntimeError("R24-S3 owner receipt is missing")

    @property
    def fixture_only(self) -> bool:
        _receipt_set_items(self)
        return True

    @property
    def source_authority(self) -> bool:
        _receipt_set_items(self)
        return False

    @property
    def effect_authority(self) -> bool:
        _receipt_set_items(self)
        return False


class Task014R24FakePrearmPort:
    __slots__ = ("__weakref__",)

    def __init__(self) -> None:
        _register_port(self, failure_mode=None)

    @classmethod
    def create_broken_fixture(cls) -> "Task014R24FakePrearmPort":
        instance = object.__new__(cls)
        _register_port(instance, failure_mode="broken")
        return instance

    @classmethod
    def create_forked_fixture(cls) -> "Task014R24FakePrearmPort":
        instance = object.__new__(cls)
        _register_port(instance, failure_mode="forked")
        return instance

    @classmethod
    def create_ambiguous_fixture(cls) -> "Task014R24FakePrearmPort":
        instance = object.__new__(cls)
        _register_port(instance, failure_mode="ambiguous")
        return instance

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("R24-S3 fake port types are sealed")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("R24-S3 fake ports are sealed")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("R24-S3 fake ports are sealed")

    def __copy__(self) -> Any:
        raise TypeError("R24-S3 fake ports are non-copyable")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("R24-S3 fake ports are non-copyable")

    def __reduce__(self) -> Any:
        raise TypeError("R24-S3 fake ports are non-serializable")

    def __reduce_ex__(self, protocol: int) -> Any:
        raise TypeError("R24-S3 fake ports are non-serializable")


class Task014R24PrearmAdapter(_SealedCapability):
    __slots__ = ()

    @property
    def reserved_snapshot_sha256(self) -> str:
        return _adapter_value(self, "reserved_snapshot_sha256")

    @classmethod
    def create_synthetic(
        cls,
        *,
        port: Task014R24FakePrearmPort,
        owner_receipts: Task014R24PrearmOwnerReceiptSet,
        project_id: str,
        operation_id: str,
        ticket_id: str,
        reservation_id: str,
        claim_id: str,
    ) -> "Task014R24PrearmAdapter":
        instance = object.__new__(cls)
        _register_adapter(
            instance,
            port=port,
            owner_receipts=owner_receipts,
            project_id=_identifier(project_id, "project_id"),
            operation_id=_identifier(operation_id, "operation_id"),
            ticket_id=_identifier(ticket_id, "ticket_id"),
            reservation_id=_identifier(reservation_id, "reservation_id"),
            claim_id=_identifier(claim_id, "claim_id"),
        )
        return instance

    def execute(
        self,
        *,
        scenario: Task014R24PrearmScenario,
        project_id: str,
        operation_id: str,
        ticket_id: str,
    ) -> "Task014R24PrearmCurrentRead":
        return _run_adapter(
            self,
            scenario=scenario,
            project_id=project_id,
            operation_id=operation_id,
            ticket_id=ticket_id,
        )


class Task014R24PrearmCurrentRead(_SealedCapability):
    __slots__ = ()

    @property
    def state(self) -> Task014R24PrearmCurrentState:
        return _read_value(self, "state")

    @property
    def reservation_state(self) -> Task014R24ReservationState | None:
        return _read_value(self, "reservation_state")

    @property
    def coordinator_state(self) -> Task014R24CoordinatorState | None:
        return _read_value(self, "coordinator_state")

    @property
    def initial_query(self) -> Task014R24OwnerQuery | None:
        return _read_value(self, "initial_query")

    @property
    def join_query(self) -> Task014R24OwnerQuery | None:
        return _read_value(self, "join_query")

    @property
    def reservation_trace(self) -> tuple[Task014R24ReservationState, ...]:
        return _read_value(self, "reservation_trace")

    @property
    def coordinator_trace(self) -> tuple[Task014R24CoordinatorState, ...]:
        return _read_value(self, "coordinator_trace")

    @property
    def store_revision(self) -> int:
        return _read_value(self, "store_revision")

    @property
    def snapshot_sha256(self) -> str | None:
        return _read_value(self, "snapshot_sha256")

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return _read_value(self, "reason_codes")

    @property
    def owner_store_read(self) -> bool:
        return _read_value(self, "owner_store_read")

    @property
    def currentness_verified(self) -> bool:
        return _read_value(self, "currentness_verified")

    @property
    def fixture_only(self) -> bool:
        return True

    def __getattr__(self, name: str) -> Any:
        if name in _FALSE_EFFECT_NAMES:
            return False
        raise AttributeError(name)


def _build_surfaces():
    receipts: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
    receipt_sets: WeakKeyDictionary[Any, tuple[Any, ...]] = WeakKeyDictionary()
    ports: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
    adapters: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
    reads: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
    registry_lock = RLock()

    exact_owners = (
        Task014R24PrearmOwner.TASK014,
        Task014R24PrearmOwner.TASK072,
        Task014R24PrearmOwner.TASK075,
        Task014R24PrearmOwner.TASK076,
    )

    def receipt_value(instance: Any, field: str) -> Any:
        with registry_lock:
            data = receipts.get(instance)
            if data is None or type(instance) is not Task014R24PrearmOwnerReceipt:
                raise TypeError("R24-S3 owner receipt provenance is invalid")
            return data[field]

    def receipt_set_items(instance: Any) -> tuple[Any, ...]:
        with registry_lock:
            items = receipt_sets.get(instance)
            if items is None or type(instance) is not Task014R24PrearmOwnerReceiptSet:
                raise TypeError("R24-S3 owner receipt set provenance is invalid")
            if tuple(item.owner for item in items) != exact_owners:
                raise TypeError("R24-S3 owner receipt set is incomplete")
            return items

    def issue_receipts() -> Task014R24PrearmOwnerReceiptSet:
        with registry_lock:
            items: list[Any] = []
            for owner in exact_owners:
                receipt = object.__new__(Task014R24PrearmOwnerReceipt)
                receipts[receipt] = {
                    "owner": owner,
                    "record_sha256": _owner_receipt_digest(owner),
                }
                items.append(receipt)
            receipt_set = object.__new__(Task014R24PrearmOwnerReceiptSet)
            receipt_sets[receipt_set] = tuple(items)
            return receipt_set

    def register_port(instance: Any, *, failure_mode: str | None) -> None:
        if type(instance) is not Task014R24FakePrearmPort:
            raise TypeError("R24-S3 fake port type is invalid")
        if failure_mode not in (None, "broken", "forked", "ambiguous"):
            raise ValueError("R24-S3 fake port failure mode is invalid")
        with registry_lock:
            if instance in ports:
                raise TypeError("R24-S3 fake port is already initialized")
            ports[instance] = {
                "lock": Lock(),
                "failure_mode": failure_mode,
                "snapshot": None,
            }

    def register_adapter(instance: Any, **data: Any) -> None:
        if type(instance) is not Task014R24PrearmAdapter:
            raise TypeError("R24-S3 adapter type is invalid")
        if type(data["port"]) is not Task014R24FakePrearmPort:
            raise TypeError("R24-S3 fake port type is invalid")
        receipt_set_items(data["owner_receipts"])
        with registry_lock:
            port_data = ports.get(data["port"])
            if port_data is None:
                raise TypeError("R24-S3 fake port provenance is invalid")
            if instance in adapters:
                raise TypeError("R24-S3 adapter is already initialized")
        initial_snapshot = {
            "project_id": data["project_id"],
            "operation_id": data["operation_id"],
            "ticket_id": data["ticket_id"],
            "reservation_id": data["reservation_id"],
            "claim_id": data["claim_id"],
            "reservation_trace": (Task014R24ReservationState.RESERVED,),
            "coordinator_trace": (),
            "initial_query": None,
            "join_query": None,
            "revision": 1,
        }
        initial_snapshot["snapshot_sha256"] = _snapshot_digest(initial_snapshot)
        with port_data["lock"]:
            if port_data["failure_mode"] is not None:
                raise ValueError("R24-S3 cannot reserve an untrusted fixture")
            if port_data["snapshot"] is not None:
                raise ValueError("R24-S3 fake port already contains a reservation")
            port_data["snapshot"] = initial_snapshot
        with registry_lock:
            adapters[instance] = {
                **data,
                "lock": Lock(),
                "burned": False,
                "reserved_snapshot_sha256": initial_snapshot["snapshot_sha256"],
            }

    def adapter_value(instance: Any, field: str) -> Any:
        with registry_lock:
            data = adapters.get(instance)
            if data is None or type(instance) is not Task014R24PrearmAdapter:
                raise TypeError("R24-S3 adapter provenance is invalid")
            return data[field]

    def issue_read(**data: Any) -> Task014R24PrearmCurrentRead:
        instance = object.__new__(Task014R24PrearmCurrentRead)
        with registry_lock:
            reads[instance] = data
        return instance

    def read_value(instance: Any, field: str) -> Any:
        with registry_lock:
            data = reads.get(instance)
            if data is None or type(instance) is not Task014R24PrearmCurrentRead:
                raise TypeError("R24-S3 current-read provenance is invalid")
            return data[field]

    def read_port(
        port: Task014R24FakePrearmPort,
        *,
        project_id: str,
        operation_id: str,
        ticket_id: str,
        expected_reservation_id: str | None,
        expected_claim_id: str | None,
        expected_snapshot_sha256: str | None,
    ) -> Task014R24PrearmCurrentRead:
        if type(port) is not Task014R24FakePrearmPort:
            raise TypeError("R24-S3 fake port type is invalid")
        project = _identifier(project_id, "project_id")
        operation = _identifier(operation_id, "operation_id")
        ticket = _identifier(ticket_id, "ticket_id")
        reservation = (
            _identifier(expected_reservation_id, "expected_reservation_id")
            if expected_reservation_id is not None
            else None
        )
        claim = (
            _identifier(expected_claim_id, "expected_claim_id")
            if expected_claim_id is not None
            else None
        )
        if expected_snapshot_sha256 is not None:
            if (
                type(expected_snapshot_sha256) is not str
                or len(expected_snapshot_sha256) != 64
                or any(c not in "0123456789ABCDEF" for c in expected_snapshot_sha256)
            ):
                raise ValueError("expected_snapshot_sha256 is invalid")
        with registry_lock:
            port_data = ports.get(port)
        if port_data is None:
            raise TypeError("R24-S3 fake port provenance is invalid")
        with port_data["lock"]:
            snapshot = port_data["snapshot"]
            failure_mode = port_data["failure_mode"]
            if failure_mode is not None:
                failure_state, failure_reason = {
                    "broken": (
                        Task014R24PrearmCurrentState.BROKEN_CHAIN,
                        "UNTRUSTED_FIXTURE_SNAPSHOT",
                    ),
                    "forked": (
                        Task014R24PrearmCurrentState.FORKED_CHAIN,
                        "MULTIPLE_RESERVATION_HEADS",
                    ),
                    "ambiguous": (
                        Task014R24PrearmCurrentState.AMBIGUOUS_TRUTH,
                        "OWNER_QUERY_TRUTH_AMBIGUOUS",
                    ),
                }[failure_mode]
                return issue_read(
                    state=failure_state,
                    reservation_state=None,
                    coordinator_state=None,
                    initial_query=None,
                    join_query=None,
                    reservation_trace=(),
                    coordinator_trace=(),
                    store_revision=0,
                    snapshot_sha256=None,
                    reason_codes=(failure_reason,),
                    owner_store_read=True,
                    currentness_verified=False,
                )
            if snapshot is None:
                return issue_read(
                    state=Task014R24PrearmCurrentState.STORE_MISSING,
                    reservation_state=None,
                    coordinator_state=None,
                    initial_query=None,
                    join_query=None,
                    reservation_trace=(),
                    coordinator_trace=(),
                    store_revision=0,
                    snapshot_sha256=None,
                    reason_codes=("PREARM_RESERVATION_NOT_FOUND",),
                    owner_store_read=True,
                    currentness_verified=False,
                )
            actual_digest = _snapshot_digest(snapshot)
            if actual_digest != snapshot["snapshot_sha256"]:
                return issue_read(
                    state=Task014R24PrearmCurrentState.BROKEN_CHAIN,
                    reservation_state=snapshot["reservation_trace"][-1],
                    coordinator_state=(
                        snapshot["coordinator_trace"][-1]
                        if snapshot["coordinator_trace"]
                        else None
                    ),
                    initial_query=snapshot["initial_query"],
                    join_query=snapshot["join_query"],
                    reservation_trace=snapshot["reservation_trace"],
                    coordinator_trace=snapshot["coordinator_trace"],
                    store_revision=snapshot["revision"],
                    snapshot_sha256=actual_digest,
                    reason_codes=("PREARM_SNAPSHOT_DIGEST_MISMATCH",),
                    owner_store_read=True,
                    currentness_verified=False,
                )
            if project != snapshot["project_id"]:
                state = Task014R24PrearmCurrentState.FOREIGN_PROJECT
                reasons = ("FOREIGN_PROJECT",)
            else:
                reasons_list: list[str] = []
                if operation != snapshot["operation_id"]:
                    reasons_list.append("OPERATION_CHANGED")
                if ticket != snapshot["ticket_id"]:
                    reasons_list.append("TICKET_CHANGED")
                if reservation is None:
                    reasons_list.append("RESERVATION_EXPECTATION_MISSING")
                elif reservation != snapshot["reservation_id"]:
                    reasons_list.append("RESERVATION_CHANGED")
                if claim is None:
                    reasons_list.append("CLAIM_EXPECTATION_MISSING")
                elif claim != snapshot["claim_id"]:
                    reasons_list.append("CLAIM_CHANGED")
                if expected_snapshot_sha256 is None:
                    reasons_list.append("SNAPSHOT_EXPECTATION_MISSING")
                elif expected_snapshot_sha256 != actual_digest:
                    reasons_list.append("SNAPSHOT_CHANGED")
                state = (
                    Task014R24PrearmCurrentState.CURRENT_EFFECT_ZERO
                    if not reasons_list
                    else Task014R24PrearmCurrentState.STALE_COORDINATE
                )
                reasons = tuple(sorted(reasons_list))
            return issue_read(
                state=state,
                reservation_state=snapshot["reservation_trace"][-1],
                coordinator_state=(
                    snapshot["coordinator_trace"][-1]
                    if snapshot["coordinator_trace"]
                    else None
                ),
                initial_query=snapshot["initial_query"],
                join_query=snapshot["join_query"],
                reservation_trace=snapshot["reservation_trace"],
                coordinator_trace=snapshot["coordinator_trace"],
                store_revision=snapshot["revision"],
                snapshot_sha256=actual_digest,
                reason_codes=reasons,
                owner_store_read=True,
                currentness_verified=(
                    state is Task014R24PrearmCurrentState.CURRENT_EFFECT_ZERO
                ),
            )

    def run_adapter(instance: Any, **values: Any) -> Task014R24PrearmCurrentRead:
        with registry_lock:
            adapter = adapters.get(instance)
        if adapter is None or type(instance) is not Task014R24PrearmAdapter:
            raise TypeError("R24-S3 adapter provenance is invalid")
        with adapter["lock"]:
            if adapter["burned"]:
                raise RuntimeError("R24-S3 adapter has already been burned")
            adapter["burned"] = True
        scenario = values["scenario"]
        if type(scenario) is not Task014R24PrearmScenario:
            raise TypeError("R24-S3 scenario type is invalid")
        project = _identifier(values["project_id"], "project_id")
        operation = _identifier(values["operation_id"], "operation_id")
        ticket = _identifier(values["ticket_id"], "ticket_id")
        if (
            project != adapter["project_id"]
            or operation != adapter["operation_id"]
            or ticket != adapter["ticket_id"]
        ):
            raise ValueError("R24-S3 foreign coordinate rejected before mutation")
        receipt_set_items(adapter["owner_receipts"])
        with registry_lock:
            port_data = ports.get(adapter["port"])
        if port_data is None:
            raise TypeError("R24-S3 fake port provenance is invalid")
        with port_data["lock"]:
            if port_data["failure_mode"] is not None:
                raise ValueError("R24-S3 cannot write an untrusted fixture")
            existing = port_data["snapshot"]
            if (
                existing is None
                or existing["snapshot_sha256"]
                != adapter["reserved_snapshot_sha256"]
                or _snapshot_digest(existing) != existing["snapshot_sha256"]
                or existing["reservation_trace"]
                != (Task014R24ReservationState.RESERVED,)
                or existing["coordinator_trace"]
                or existing["initial_query"] is not None
                or existing["join_query"] is not None
                or existing["revision"] != 1
            ):
                raise ValueError("R24-S3 initial RESERVED snapshot is not current")

            if scenario is Task014R24PrearmScenario.CANCEL_KNOWN:
                reservation_trace = (
                    Task014R24ReservationState.RESERVED,
                    Task014R24ReservationState.CANCEL_PENDING,
                    Task014R24ReservationState.CANCELLED_KNOWN,
                )
                coordinator_trace = ()
                initial_query = Task014R24OwnerQuery.NOT_ENTERED_KNOWN
                join_query = Task014R24OwnerQuery.JOB_CHILD_REJECTED_READBACK_V3
            elif scenario is Task014R24PrearmScenario.CANCEL_UNKNOWN:
                reservation_trace = (
                    Task014R24ReservationState.RESERVED,
                    Task014R24ReservationState.CANCEL_PENDING,
                    Task014R24ReservationState.CANCEL_UNKNOWN,
                )
                coordinator_trace = ()
                initial_query = Task014R24OwnerQuery.ATTEMPT_TRUTH_UNKNOWN
                join_query = (
                    Task014R24OwnerQuery.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
                )
            elif scenario is Task014R24PrearmScenario.FAILURE_BEFORE_TASK014_CLAIM:
                reservation_trace = (Task014R24ReservationState.RESERVED,)
                coordinator_trace = (Task014R24CoordinatorState.CLAIM_INTENT,)
                initial_query = Task014R24OwnerQuery.NOT_ENTERED_KNOWN
                join_query = None
            else:
                reservation_terminal: Task014R24ReservationState
                initial_query: Task014R24OwnerQuery
                join_query: Task014R24OwnerQuery
                coordinator_prefix = (
                    Task014R24CoordinatorState.CLAIM_INTENT,
                    Task014R24CoordinatorState.TASK014_CLAIMED,
                )
                if scenario is Task014R24PrearmScenario.ARM_NOT_ENTERED:
                    initial_query = Task014R24OwnerQuery.NOT_ENTERED_KNOWN
                    join_query = (
                        Task014R24OwnerQuery.JOB_CHILD_REJECTED_READBACK_V3
                    )
                    reservation_terminal = Task014R24ReservationState.ARM_REJECTED
                    coordinator_trace = coordinator_prefix + (
                        Task014R24CoordinatorState.TASK076_RESULT_OBSERVED,
                        Task014R24CoordinatorState.JOINED,
                    )
                else:
                    coordinator_prefix = coordinator_prefix + (
                        Task014R24CoordinatorState.ARM_CALL_ENTERING,
                    )
                    if scenario is Task014R24PrearmScenario.ARM_ARMED:
                        initial_query = (
                            Task014R24OwnerQuery.JOB_CHILD_ARMED_READBACK_V3
                        )
                        join_query = initial_query
                        reservation_terminal = (
                            Task014R24ReservationState.ARMED_CONSUMED
                        )
                    elif scenario is Task014R24PrearmScenario.ARM_REJECTED:
                        initial_query = (
                            Task014R24OwnerQuery.JOB_CHILD_REJECTED_READBACK_V3
                        )
                        join_query = initial_query
                        reservation_terminal = (
                            Task014R24ReservationState.ARM_REJECTED
                        )
                    elif scenario is Task014R24PrearmScenario.ARM_UNKNOWN:
                        initial_query = (
                            Task014R24OwnerQuery.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
                        )
                        join_query = initial_query
                        reservation_terminal = (
                            Task014R24ReservationState.ARM_UNKNOWN
                        )
                    elif scenario is Task014R24PrearmScenario.ATTEMPT_TRUTH_UNKNOWN:
                        initial_query = Task014R24OwnerQuery.ATTEMPT_TRUTH_UNKNOWN
                        join_query = (
                            Task014R24OwnerQuery.JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
                        )
                        reservation_terminal = (
                            Task014R24ReservationState.ARM_UNKNOWN
                        )
                    else:
                        raise AssertionError("closed R24-S3 scenario is unhandled")
                    coordinator_trace = coordinator_prefix + (
                        Task014R24CoordinatorState.TASK076_RESULT_OBSERVED,
                        Task014R24CoordinatorState.JOINED,
                    )
                reservation_trace = (
                    Task014R24ReservationState.RESERVED,
                    Task014R24ReservationState.ARMING,
                    Task014R24ReservationState.JOIN_PENDING,
                    reservation_terminal,
                )

            snapshot = {
                "project_id": project,
                "operation_id": operation,
                "ticket_id": ticket,
                "reservation_id": adapter["reservation_id"],
                "claim_id": adapter["claim_id"],
                "reservation_trace": reservation_trace,
                "coordinator_trace": coordinator_trace,
                "initial_query": initial_query,
                "join_query": join_query,
                "revision": len(reservation_trace) + len(coordinator_trace),
            }
            snapshot["snapshot_sha256"] = _snapshot_digest(snapshot)
            port_data["snapshot"] = snapshot
        return read_port(
            adapter["port"],
            project_id=project,
            operation_id=operation,
            ticket_id=ticket,
            expected_reservation_id=adapter["reservation_id"],
            expected_claim_id=adapter["claim_id"],
            expected_snapshot_sha256=snapshot["snapshot_sha256"],
        )

    return (
        receipt_value,
        receipt_set_items,
        issue_receipts,
        register_port,
        register_adapter,
        adapter_value,
        run_adapter,
        read_port,
        read_value,
    )


(
    _receipt_value,
    _receipt_set_items,
    issue_effect_zero_owner_receipts,
    _register_port,
    _register_adapter,
    _adapter_value,
    _run_adapter,
    read_current,
    _read_value,
) = _build_surfaces()
del _build_surfaces


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


for _owner_receipt_property in ("owner", "record_sha256"):
    _descriptor = getattr(Task014R24PrearmOwnerReceipt, _owner_receipt_property)
    setattr(
        Task014R24PrearmOwnerReceipt,
        _owner_receipt_property,
        property(_bind_hidden_globals(_descriptor.fget)),
    )
for _receipt_set_property in (
    "amendment_identity",
    "owners",
    "fixture_only",
    "source_authority",
    "effect_authority",
):
    _descriptor = getattr(Task014R24PrearmOwnerReceiptSet, _receipt_set_property)
    setattr(
        Task014R24PrearmOwnerReceiptSet,
        _receipt_set_property,
        property(_bind_hidden_globals(_descriptor.fget)),
    )
Task014R24PrearmOwnerReceiptSet.receipt_for = _bind_hidden_globals(
    Task014R24PrearmOwnerReceiptSet.receipt_for
)
Task014R24FakePrearmPort.__init__ = _bind_hidden_globals(
    Task014R24FakePrearmPort.__init__
)
for _port_factory in (
    "create_broken_fixture",
    "create_forked_fixture",
    "create_ambiguous_fixture",
):
    setattr(
        Task014R24FakePrearmPort,
        _port_factory,
        classmethod(
            _bind_hidden_globals(
                Task014R24FakePrearmPort.__dict__[_port_factory].__func__
            )
        ),
    )
Task014R24PrearmAdapter.create_synthetic = classmethod(
    _bind_hidden_globals(Task014R24PrearmAdapter.create_synthetic.__func__)
)
Task014R24PrearmAdapter.reserved_snapshot_sha256 = property(
    _bind_hidden_globals(Task014R24PrearmAdapter.reserved_snapshot_sha256.fget)
)
Task014R24PrearmAdapter.execute = _bind_hidden_globals(
    Task014R24PrearmAdapter.execute
)
for _read_property in (
    "state",
    "reservation_state",
    "coordinator_state",
    "initial_query",
    "join_query",
    "reservation_trace",
    "coordinator_trace",
    "store_revision",
    "snapshot_sha256",
    "reason_codes",
    "owner_store_read",
    "currentness_verified",
):
    _descriptor = getattr(Task014R24PrearmCurrentRead, _read_property)
    setattr(
        Task014R24PrearmCurrentRead,
        _read_property,
        property(_bind_hidden_globals(_descriptor.fget)),
    )
del (
    _bind_hidden_globals,
    _descriptor,
    _owner_receipt_property,
    _read_property,
    _receipt_set_items,
    _receipt_set_property,
    _receipt_value,
    _adapter_value,
    _register_adapter,
    _register_port,
    _run_adapter,
    _read_value,
    _port_factory,
)


__all__ = [
    "AMENDMENT_IDENTITY",
    "FIXTURE_SCOPE",
    "R24_S3_VERSION",
    "Task014R24CoordinatorState",
    "Task014R24FakePrearmPort",
    "Task014R24OwnerQuery",
    "Task014R24PrearmAdapter",
    "Task014R24PrearmCurrentRead",
    "Task014R24PrearmCurrentState",
    "Task014R24PrearmOwner",
    "Task014R24PrearmOwnerReceipt",
    "Task014R24PrearmOwnerReceiptSet",
    "Task014R24PrearmScenario",
    "Task014R24ReservationState",
    "issue_effect_zero_owner_receipts",
    "read_current",
]
