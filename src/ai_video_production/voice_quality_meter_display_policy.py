"""TASK-048 body-free Peak-dBFS meter display policy.

The contract exposes only versioned display thresholds and their currentness.
It accepts scalar meter facts, never audio, and cannot issue quality, capture,
gain-change, Dataset, Training, Model, or Production authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import json
import math
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


POLICY_RECORD_TYPE = "Task048MeterDisplayPolicyRevisionV1"
DECISION_RECORD_TYPE = "Task048MeterDisplayDecisionV1"
SCHEMA_VERSION = 1
CANONICAL_OWNER_TASK = "TASK-048"
POLICY_DIGEST_DOMAIN = b"TASK048_METER_DISPLAY_POLICY_REVISION_V1\0"
DECISION_DIGEST_DOMAIN = b"TASK048_METER_DISPLAY_DECISION_V1\0"
FIXTURE_CURRENTNESS_DIGEST_DOMAIN = b"TASK048_METER_DISPLAY_FIXTURE_CURRENTNESS_V1\0"
UNCONFIRMED_LABEL = "適正判定 未確定"

_PUBLIC_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_POLICY_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "policy_ref",
    "policy_revision",
    "predecessor_policy_sha256",
    "target_floor_dbfs",
    "target_ceiling_dbfs",
    "warning_dbfs",
    "true_clip_dbfs",
    "policy_revision_sha256",
}
_DECISION_FALSE_FLAGS = (
    "audio_body_read",
    "analyzer_executed",
    "quality_receipt_issued",
    "capture_authorized",
    "gain_change_authorized",
    "hardware_or_obs_setting_changed",
    "dataset_training_model_authorized",
    "production_backend_invoked",
    "capture_transport_blocked",
    "emergency_stop_blocked",
)
_DECISION_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "binding_state",
    "reason_codes",
    "policy_ref",
    "policy_revision",
    "predecessor_policy_sha256",
    "policy_revision_sha256",
    "currentness_receipt_sha256",
    "policy_currentness_confirmed",
    "fixture_policy_currentness_matched",
    "thresholds_available",
    "target_floor_dbfs",
    "target_ceiling_dbfs",
    "warning_dbfs",
    "true_clip_dbfs",
    "observation_state",
    "sample_peak_dbfs",
    "measured_sample_values",
    "display_band",
    "operator_label",
    *_DECISION_FALSE_FLAGS,
    "external_effect_count",
    "fixture_only",
    "authority_created",
    "production_eligible",
    "trusted_currentness_admitted",
    "decision_sha256",
}


class PolicyBindingState(str, Enum):
    NOT_BOUND = "NOT_BOUND"
    FIXTURE_BOUND_VERIFIED = "FIXTURE_BOUND_VERIFIED"
    STALE = "STALE"
    REVOKED = "REVOKED"
    MISMATCH = "MISMATCH"


class PeakObservationState(str, Enum):
    MEASURED = "MEASURED"
    MEASURED_LINEAR_ZERO = "MEASURED_LINEAR_ZERO"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    INVALID_NONFINITE = "INVALID_NONFINITE"
    INVALID_OUT_OF_RANGE = "INVALID_OUT_OF_RANGE"


class MeterDisplayBand(str, Enum):
    UNCONFIRMED = "UNCONFIRMED"
    BELOW_TARGET = "BELOW_TARGET"
    TARGET = "TARGET"
    ABOVE_TARGET = "ABOVE_TARGET"
    WARNING = "WARNING"
    TRUE_CLIP = "TRUE_CLIP"


class MeterDisplayReason(str, Enum):
    POLICY_NOT_BOUND = "POLICY_NOT_BOUND"
    POLICY_STALE = "POLICY_STALE"
    POLICY_REVOKED = "POLICY_REVOKED"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    POLICY_DOCUMENT_MISSING = "POLICY_DOCUMENT_MISSING"
    POLICY_DOCUMENT_INVALID = "POLICY_DOCUMENT_INVALID"
    POLICY_BINDING_MISMATCH = "POLICY_BINDING_MISMATCH"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    INVALID_METER_SCALAR = "INVALID_METER_SCALAR"


class MeterDisplayPolicyError(ValueError):
    """Strict policy or decision contract rejection."""


def _snapshot_mapping(
    value: Mapping[str, Any], expected: set[str], name: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MeterDisplayPolicyError(f"{name} must be a mapping")
    try:
        outer_snapshot = dict(value)
        snapshot = json.loads(canonical_json_bytes(outer_snapshot))
    except Exception as exc:
        raise MeterDisplayPolicyError(f"{name} could not be snapshotted") from exc
    if set(snapshot) != expected:
        raise MeterDisplayPolicyError(f"{name} fields are incomplete or unknown")
    return snapshot


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise MeterDisplayPolicyError(f"{name} is invalid") from exc


def _public_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _PUBLIC_ID_RE.fullmatch(value):
        raise MeterDisplayPolicyError(f"{name} is invalid")
    if "://" in value or "\\" in value or "/" in value:
        raise MeterDisplayPolicyError(f"{name} must not contain a host path or URI")
    return value


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise MeterDisplayPolicyError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MeterDisplayPolicyError(f"{name} must be a non-negative integer")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise MeterDisplayPolicyError(f"{name} is invalid")
    try:
        return validate_sha256(value, field_name=name)
    except ValueError as exc:
        raise MeterDisplayPolicyError(str(exc)) from exc


def _dbfs(value: Any, name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise MeterDisplayPolicyError(f"{name} must be finite dBFS")
    result = float(value)
    if result > 0.0:
        raise MeterDisplayPolicyError(f"{name} must not exceed the 0 dBFS digital bound")
    return result


def _hash(domain: bytes, body: Mapping[str, Any], digest_field: str) -> str:
    return sha256_bytes(
        domain
        + canonical_json_bytes(
            {key: value for key, value in body.items() if key != digest_field}
        )
    )


@dataclass(frozen=True, slots=True)
class MeterDisplayPolicyRevision:
    policy_ref: str
    policy_revision: int
    predecessor_policy_sha256: str | None
    target_floor_dbfs: float
    target_ceiling_dbfs: float
    warning_dbfs: float
    true_clip_dbfs: float

    def __post_init__(self) -> None:
        _public_id(self.policy_ref, "policy_ref")
        _positive_int(self.policy_revision, "policy_revision")
        _digest(
            self.predecessor_policy_sha256,
            "predecessor_policy_sha256",
            nullable=True,
        )
        values = (
            _dbfs(self.target_floor_dbfs, "target_floor_dbfs"),
            _dbfs(self.target_ceiling_dbfs, "target_ceiling_dbfs"),
            _dbfs(self.warning_dbfs, "warning_dbfs"),
            _dbfs(self.true_clip_dbfs, "true_clip_dbfs"),
        )
        if not values[0] < values[1] < values[2] < values[3]:
            raise MeterDisplayPolicyError(
                "meter thresholds must be strictly ordered from target floor to true clip"
            )
        if self.policy_revision == 1 and self.predecessor_policy_sha256 is not None:
            raise MeterDisplayPolicyError("first policy revision cannot have a predecessor")
        if self.policy_revision > 1 and self.predecessor_policy_sha256 is None:
            raise MeterDisplayPolicyError("later policy revision requires a predecessor")
        for name, value in zip(
            (
                "target_floor_dbfs",
                "target_ceiling_dbfs",
                "warning_dbfs",
                "true_clip_dbfs",
            ),
            values,
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_type": POLICY_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": CANONICAL_OWNER_TASK,
            "policy_ref": self.policy_ref,
            "policy_revision": self.policy_revision,
            "predecessor_policy_sha256": self.predecessor_policy_sha256,
            "target_floor_dbfs": self.target_floor_dbfs,
            "target_ceiling_dbfs": self.target_ceiling_dbfs,
            "warning_dbfs": self.warning_dbfs,
            "true_clip_dbfs": self.true_clip_dbfs,
        }
        body["policy_revision_sha256"] = _hash(
            POLICY_DIGEST_DOMAIN, body, "policy_revision_sha256"
        )
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeterDisplayPolicyRevision":
        snapshot = _snapshot_mapping(value, _POLICY_FIELDS, "meter display policy")
        if (
            snapshot["record_type"] != POLICY_RECORD_TYPE
            or type(snapshot["schema_version"]) is not int
            or snapshot["schema_version"] != SCHEMA_VERSION
            or snapshot["canonical_owner_task"] != CANONICAL_OWNER_TASK
        ):
            raise MeterDisplayPolicyError("meter display policy discriminator is invalid")
        _digest(snapshot["policy_revision_sha256"], "policy_revision_sha256")
        if snapshot["policy_revision_sha256"] != _hash(
            POLICY_DIGEST_DOMAIN, snapshot, "policy_revision_sha256"
        ):
            raise MeterDisplayPolicyError("policy_revision_sha256 mismatch")
        result = cls(
            policy_ref=snapshot["policy_ref"],
            policy_revision=snapshot["policy_revision"],
            predecessor_policy_sha256=snapshot["predecessor_policy_sha256"],
            target_floor_dbfs=snapshot["target_floor_dbfs"],
            target_ceiling_dbfs=snapshot["target_ceiling_dbfs"],
            warning_dbfs=snapshot["warning_dbfs"],
            true_clip_dbfs=snapshot["true_clip_dbfs"],
        )
        if result.to_dict() != snapshot:
            raise MeterDisplayPolicyError("meter display policy is noncanonical")
        return result


_FIXTURE_SEAL_TOKEN = object()


def _fixture_currentness_sha256(policy: MeterDisplayPolicyRevision) -> str:
    policy_document = policy.to_dict()
    return sha256_bytes(
        FIXTURE_CURRENTNESS_DIGEST_DOMAIN
        + canonical_json_bytes(
            {
                "record_type": "Task048FixtureMeterDisplayCurrentnessV1",
                "schema_version": SCHEMA_VERSION,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "policy_ref": policy.policy_ref,
                "policy_revision": policy.policy_revision,
                "predecessor_policy_sha256": policy.predecessor_policy_sha256,
                "policy_revision_sha256": policy_document[
                    "policy_revision_sha256"
                ],
                "fixture_only": True,
                "authority_created": False,
                "production_eligible": False,
            }
        )
    )


class FixtureMeterDisplayCurrentnessSeal:
    """Non-serializable fixture capability; it never proves Product currentness."""

    __slots__ = (
        "policy_ref",
        "policy_revision",
        "predecessor_policy_sha256",
        "policy_revision_sha256",
        "currentness_receipt_sha256",
        "_token",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("fixture currentness seal cannot be subclassed")

    def __init__(
        self,
        *,
        policy: MeterDisplayPolicyRevision,
        token: object,
    ) -> None:
        if token is not _FIXTURE_SEAL_TOKEN:
            raise MeterDisplayPolicyError("fixture currentness seal factory is required")
        policy_document = policy.to_dict()
        object.__setattr__(self, "_sealed", False)
        object.__setattr__(self, "policy_ref", policy.policy_ref)
        object.__setattr__(self, "policy_revision", policy.policy_revision)
        object.__setattr__(
            self, "predecessor_policy_sha256", policy.predecessor_policy_sha256
        )
        object.__setattr__(
            self, "policy_revision_sha256", policy_document["policy_revision_sha256"]
        )
        object.__setattr__(
            self,
            "currentness_receipt_sha256",
            _fixture_currentness_sha256(policy),
        )
        object.__setattr__(self, "_token", token)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("fixture currentness seal is immutable")
        object.__setattr__(self, name, value)

    def _assert_valid_for(self, policy: MeterDisplayPolicyRevision) -> None:
        if type(self) is not FixtureMeterDisplayCurrentnessSeal:
            raise MeterDisplayPolicyError("fixture currentness seal type is invalid")
        if self._token is not _FIXTURE_SEAL_TOKEN:
            raise MeterDisplayPolicyError("fixture currentness seal identity is invalid")
        document = policy.to_dict()
        if (
            self.policy_ref != policy.policy_ref
            or self.policy_revision != policy.policy_revision
            or self.predecessor_policy_sha256 != policy.predecessor_policy_sha256
            or self.policy_revision_sha256 != document["policy_revision_sha256"]
        ):
            raise MeterDisplayPolicyError("fixture currentness seal policy mismatch")
        if self.currentness_receipt_sha256 != _fixture_currentness_sha256(policy):
            raise MeterDisplayPolicyError("fixture currentness receipt mismatch")

    def __copy__(self) -> "FixtureMeterDisplayCurrentnessSeal":
        raise TypeError("fixture currentness seal cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> "FixtureMeterDisplayCurrentnessSeal":
        raise TypeError("fixture currentness seal cannot be deep-copied")

    def __reduce__(self) -> tuple[Any, ...]:
        raise TypeError("fixture currentness seal cannot be serialized")


def compile_fixture_meter_display_currentness(
    *,
    policy_document: Mapping[str, Any],
    current_head_document: Mapping[str, Any],
) -> FixtureMeterDisplayCurrentnessSeal:
    """Create only a synthetic current-head seal for effect-zero contract tests."""

    policy = MeterDisplayPolicyRevision.from_dict(policy_document)
    current_head = MeterDisplayPolicyRevision.from_dict(current_head_document)
    if policy.to_dict() != current_head.to_dict():
        raise MeterDisplayPolicyError(
            "fixture currentness requires exact policy/current-head readback"
        )
    return FixtureMeterDisplayCurrentnessSeal(
        policy=policy,
        token=_FIXTURE_SEAL_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class MeterDisplayPolicyBinding:
    state: PolicyBindingState
    policy_ref: str | None
    policy_revision: int | None
    predecessor_policy_sha256: str | None
    policy_revision_sha256: str | None
    currentness_receipt_sha256: str | None
    _admission: InitVar[
        tuple[object, FixtureMeterDisplayCurrentnessSeal] | None
    ] = None
    _fixture_seal: FixtureMeterDisplayCurrentnessSeal | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(
        self,
        _admission: tuple[object, FixtureMeterDisplayCurrentnessSeal] | None,
    ) -> None:
        state = _enum(PolicyBindingState, self.state, "state")
        object.__setattr__(self, "state", state)
        seal: FixtureMeterDisplayCurrentnessSeal | None = None
        if _admission is not None:
            if (
                type(_admission) is not tuple
                or len(_admission) != 2
                or _admission[0] is not _FIXTURE_SEAL_TOKEN
                or type(_admission[1]) is not FixtureMeterDisplayCurrentnessSeal
            ):
                raise MeterDisplayPolicyError("binding admission is invalid")
            seal = _admission[1]
            object.__setattr__(self, "_fixture_seal", seal)
        values = (
            self.policy_ref,
            self.policy_revision,
            self.predecessor_policy_sha256,
            self.policy_revision_sha256,
            self.currentness_receipt_sha256,
        )
        if state is PolicyBindingState.NOT_BOUND:
            if any(value is not None for value in values) or seal is not None:
                raise MeterDisplayPolicyError("NOT_BOUND cannot contain policy identity")
            return
        if any(
            value is None
            for value in (
                self.policy_ref,
                self.policy_revision,
                self.policy_revision_sha256,
                self.currentness_receipt_sha256,
            )
        ):
            raise MeterDisplayPolicyError(f"{state.value} requires complete policy identity")
        _public_id(self.policy_ref, "policy_ref")
        revision = _positive_int(self.policy_revision, "policy_revision")
        predecessor = _digest(
            self.predecessor_policy_sha256,
            "predecessor_policy_sha256",
            nullable=True,
        )
        if (revision == 1) != (predecessor is None):
            raise MeterDisplayPolicyError("binding revision/predecessor chain is invalid")
        _digest(self.policy_revision_sha256, "policy_revision_sha256")
        _digest(self.currentness_receipt_sha256, "currentness_receipt_sha256")
        if state is PolicyBindingState.FIXTURE_BOUND_VERIFIED:
            if type(seal) is not FixtureMeterDisplayCurrentnessSeal:
                raise MeterDisplayPolicyError(
                    "fixture-bound state requires a non-serializable fixture seal"
                )
            if (
                seal._token is not _FIXTURE_SEAL_TOKEN
                or seal.policy_ref != self.policy_ref
                or seal.policy_revision != revision
                or seal.predecessor_policy_sha256 != predecessor
                or seal.policy_revision_sha256 != self.policy_revision_sha256
                or seal.currentness_receipt_sha256
                != self.currentness_receipt_sha256
            ):
                raise MeterDisplayPolicyError("fixture currentness seal identity mismatch")
        elif seal is not None:
            raise MeterDisplayPolicyError("non-fixture binding cannot contain a fixture seal")

    @classmethod
    def from_fixture_seal(
        cls,
        *,
        seal: FixtureMeterDisplayCurrentnessSeal,
    ) -> "MeterDisplayPolicyBinding":
        if type(seal) is not FixtureMeterDisplayCurrentnessSeal:
            raise MeterDisplayPolicyError("fixture currentness seal type is invalid")
        if seal._token is not _FIXTURE_SEAL_TOKEN:
            raise MeterDisplayPolicyError("fixture currentness seal identity is invalid")
        return cls(
            state=PolicyBindingState.FIXTURE_BOUND_VERIFIED,
            policy_ref=seal.policy_ref,
            policy_revision=seal.policy_revision,
            predecessor_policy_sha256=seal.predecessor_policy_sha256,
            policy_revision_sha256=seal.policy_revision_sha256,
            currentness_receipt_sha256=seal.currentness_receipt_sha256,
            _admission=(_FIXTURE_SEAL_TOKEN, seal),
        )

    def assert_fixture_policy(self, policy: MeterDisplayPolicyRevision) -> None:
        if self.state is not PolicyBindingState.FIXTURE_BOUND_VERIFIED:
            raise MeterDisplayPolicyError("binding is not fixture-verified")
        if type(self._fixture_seal) is not FixtureMeterDisplayCurrentnessSeal:
            raise MeterDisplayPolicyError("fixture currentness seal is absent")
        self._fixture_seal._assert_valid_for(policy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "policy_ref": self.policy_ref,
            "policy_revision": self.policy_revision,
            "predecessor_policy_sha256": self.predecessor_policy_sha256,
            "policy_revision_sha256": self.policy_revision_sha256,
            "currentness_receipt_sha256": self.currentness_receipt_sha256,
            "fixture_only": True,
            "authority_created": False,
            "production_eligible": False,
        }

    def __copy__(self) -> "MeterDisplayPolicyBinding":
        raise TypeError("meter display binding cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> "MeterDisplayPolicyBinding":
        raise TypeError("meter display binding cannot be deep-copied")

    def __reduce__(self) -> tuple[Any, ...]:
        raise TypeError("meter display binding cannot be serialized")


@dataclass(frozen=True, slots=True)
class PeakObservation:
    state: PeakObservationState
    sample_peak_dbfs: float | None
    measured_sample_values: int

    def __post_init__(self) -> None:
        state = _enum(PeakObservationState, self.state, "state")
        object.__setattr__(self, "state", state)
        measured = _nonnegative_int(self.measured_sample_values, "measured_sample_values")
        if state is PeakObservationState.MEASURED:
            if measured == 0 or self.sample_peak_dbfs is None:
                raise MeterDisplayPolicyError("MEASURED requires a numeric peak")
            peak = _dbfs(self.sample_peak_dbfs, "sample_peak_dbfs")
            object.__setattr__(self, "sample_peak_dbfs", peak)
        elif state is PeakObservationState.MEASURED_LINEAR_ZERO:
            if measured == 0 or self.sample_peak_dbfs is not None:
                raise MeterDisplayPolicyError("MEASURED_LINEAR_ZERO is inconsistent")
        elif state is PeakObservationState.INSUFFICIENT_INPUT:
            if measured != 0 or self.sample_peak_dbfs is not None:
                raise MeterDisplayPolicyError("INSUFFICIENT_INPUT is inconsistent")
        elif measured == 0 or self.sample_peak_dbfs is not None:
            raise MeterDisplayPolicyError(
                f"{state.value} requires measured samples without a serialized scalar"
            )

    @classmethod
    def from_scalar(
        cls,
        sample_peak_dbfs: float | None,
        *,
        measured_sample_values: int,
    ) -> "PeakObservation":
        measured = _nonnegative_int(measured_sample_values, "measured_sample_values")
        if measured == 0:
            if sample_peak_dbfs is not None:
                raise MeterDisplayPolicyError("unmeasured observation cannot contain a peak")
            return cls(PeakObservationState.INSUFFICIENT_INPUT, None, 0)
        if sample_peak_dbfs is None:
            return cls(PeakObservationState.MEASURED_LINEAR_ZERO, None, measured)
        if (
            not isinstance(sample_peak_dbfs, (int, float))
            or isinstance(sample_peak_dbfs, bool)
            or not math.isfinite(sample_peak_dbfs)
        ):
            return cls(PeakObservationState.INVALID_NONFINITE, None, measured)
        if float(sample_peak_dbfs) > 0.0:
            return cls(
                PeakObservationState.INVALID_OUT_OF_RANGE, None, measured
            )
        return cls(PeakObservationState.MEASURED, float(sample_peak_dbfs), measured)


def _classify_band(
    policy: MeterDisplayPolicyRevision, observation: PeakObservation
) -> MeterDisplayBand:
    if observation.state is PeakObservationState.MEASURED_LINEAR_ZERO:
        return MeterDisplayBand.BELOW_TARGET
    if observation.state is not PeakObservationState.MEASURED:
        raise MeterDisplayPolicyError("invalid observation cannot produce a display band")
    peak = observation.sample_peak_dbfs
    if peak < policy.target_floor_dbfs:
        return MeterDisplayBand.BELOW_TARGET
    if peak <= policy.target_ceiling_dbfs:
        return MeterDisplayBand.TARGET
    if peak < policy.warning_dbfs:
        return MeterDisplayBand.ABOVE_TARGET
    if peak < policy.true_clip_dbfs:
        return MeterDisplayBand.WARNING
    return MeterDisplayBand.TRUE_CLIP


@dataclass(frozen=True, slots=True)
class MeterDisplayDecision:
    binding_state: PolicyBindingState
    reason_codes: tuple[MeterDisplayReason, ...]
    policy_ref: str | None
    policy_revision: int | None
    predecessor_policy_sha256: str | None
    policy_revision_sha256: str | None
    currentness_receipt_sha256: str | None
    policy_currentness_confirmed: bool
    fixture_policy_currentness_matched: bool
    thresholds_available: bool
    target_floor_dbfs: float | None
    target_ceiling_dbfs: float | None
    warning_dbfs: float | None
    true_clip_dbfs: float | None
    observation_state: PeakObservationState
    sample_peak_dbfs: float | None
    measured_sample_values: int
    display_band: MeterDisplayBand
    operator_label: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "binding_state", _enum(PolicyBindingState, self.binding_state, "binding_state")
        )
        object.__setattr__(
            self,
            "observation_state",
            _enum(PeakObservationState, self.observation_state, "observation_state"),
        )
        object.__setattr__(
            self, "display_band", _enum(MeterDisplayBand, self.display_band, "display_band")
        )
        reasons = tuple(
            sorted(
                (_enum(MeterDisplayReason, item, "reason_code") for item in self.reason_codes),
                key=lambda item: item.value,
            )
        )
        if len(reasons) != len(set(reasons)) or len(reasons) > 1:
            raise MeterDisplayPolicyError("reason_codes must contain at most one reason")
        object.__setattr__(self, "reason_codes", reasons)
        if any(
            type(value) is not bool
            for value in (
                self.policy_currentness_confirmed,
                self.fixture_policy_currentness_matched,
                self.thresholds_available,
            )
        ):
            raise MeterDisplayPolicyError("decision flags must be boolean")
        observation = PeakObservation(
            self.observation_state, self.sample_peak_dbfs, self.measured_sample_values
        )
        policy_identity = (
            self.policy_ref,
            self.policy_revision,
            self.predecessor_policy_sha256,
            self.policy_revision_sha256,
            self.currentness_receipt_sha256,
        )
        thresholds = (
            self.target_floor_dbfs,
            self.target_ceiling_dbfs,
            self.warning_dbfs,
            self.true_clip_dbfs,
        )
        if self.binding_state is PolicyBindingState.NOT_BOUND:
            if any(value is not None for value in policy_identity):
                raise MeterDisplayPolicyError(
                    "NOT_BOUND decision cannot contain policy identity"
                )
        else:
            if any(
                value is None
                for value in (
                    self.policy_ref,
                    self.policy_revision,
                    self.policy_revision_sha256,
                    self.currentness_receipt_sha256,
                )
            ):
                raise MeterDisplayPolicyError(
                    "non-NOT_BOUND decision requires complete policy identity"
                )
            _public_id(self.policy_ref, "policy_ref")
            revision = _positive_int(self.policy_revision, "policy_revision")
            predecessor = _digest(
                self.predecessor_policy_sha256,
                "predecessor_policy_sha256",
                nullable=True,
            )
            if (revision == 1) != (predecessor is None):
                raise MeterDisplayPolicyError(
                    "decision revision/predecessor chain is invalid"
                )
            _digest(self.policy_revision_sha256, "policy_revision_sha256")
            _digest(self.currentness_receipt_sha256, "currentness_receipt_sha256")
        if self.policy_currentness_confirmed:
            raise MeterDisplayPolicyError(
                "Product currentness cannot be confirmed by the fixture-only contract"
            )
        if self.fixture_policy_currentness_matched:
            if self.binding_state is not PolicyBindingState.FIXTURE_BOUND_VERIFIED:
                raise MeterDisplayPolicyError(
                    "fixture currentness requires FIXTURE_BOUND_VERIFIED"
                )
            if any(
                value is None
                for value in (
                    self.policy_ref,
                    self.policy_revision,
                    self.policy_revision_sha256,
                    self.currentness_receipt_sha256,
                )
            ) or any(
                value is None for value in thresholds
            ) or not self.thresholds_available:
                raise MeterDisplayPolicyError("fixture policy decision is incomplete")
            policy = MeterDisplayPolicyRevision(
                policy_ref=self.policy_ref,
                policy_revision=self.policy_revision,
                predecessor_policy_sha256=self.predecessor_policy_sha256,
                target_floor_dbfs=self.target_floor_dbfs,
                target_ceiling_dbfs=self.target_ceiling_dbfs,
                warning_dbfs=self.warning_dbfs,
                true_clip_dbfs=self.true_clip_dbfs,
            )
            if policy.to_dict()["policy_revision_sha256"] != self.policy_revision_sha256:
                raise MeterDisplayPolicyError(
                    "decision thresholds do not match policy_revision_sha256"
                )
            if self.currentness_receipt_sha256 != _fixture_currentness_sha256(
                policy
            ):
                raise MeterDisplayPolicyError(
                    "decision fixture currentness receipt mismatch"
                )
        else:
            if any(value is not None for value in thresholds) or self.thresholds_available:
                raise MeterDisplayPolicyError("unconfirmed policy must suppress thresholds")

        if self.display_band is MeterDisplayBand.UNCONFIRMED:
            if len(reasons) != 1 or self.operator_label != UNCONFIRMED_LABEL:
                raise MeterDisplayPolicyError("unconfirmed display requires a reason and safe label")
            reason = reasons[0]
            if self.fixture_policy_currentness_matched:
                expected_reason = {
                    PeakObservationState.INSUFFICIENT_INPUT: MeterDisplayReason.INSUFFICIENT_INPUT,
                    PeakObservationState.INVALID_NONFINITE: MeterDisplayReason.INVALID_METER_SCALAR,
                    PeakObservationState.INVALID_OUT_OF_RANGE: MeterDisplayReason.INVALID_METER_SCALAR,
                }.get(observation.state)
                if reason is not expected_reason:
                    raise MeterDisplayPolicyError(
                        "fixture observation state and reason disagree"
                    )
            else:
                allowed_reasons = {
                    PolicyBindingState.NOT_BOUND: {
                        MeterDisplayReason.POLICY_NOT_BOUND,
                        MeterDisplayReason.POLICY_MISMATCH,
                    },
                    PolicyBindingState.FIXTURE_BOUND_VERIFIED: {
                        MeterDisplayReason.POLICY_DOCUMENT_MISSING,
                        MeterDisplayReason.POLICY_DOCUMENT_INVALID,
                        MeterDisplayReason.POLICY_BINDING_MISMATCH,
                    },
                    PolicyBindingState.STALE: {MeterDisplayReason.POLICY_STALE},
                    PolicyBindingState.REVOKED: {MeterDisplayReason.POLICY_REVOKED},
                    PolicyBindingState.MISMATCH: {MeterDisplayReason.POLICY_MISMATCH},
                }[self.binding_state]
                if reason not in allowed_reasons:
                    raise MeterDisplayPolicyError(
                        "binding state and unconfirmed reason disagree"
                    )
        else:
            if reasons or not self.fixture_policy_currentness_matched:
                raise MeterDisplayPolicyError(
                    "classified display requires matched fixture currentness"
                )
            expected_band = _classify_band(policy, observation)
            if self.display_band is not expected_band:
                raise MeterDisplayPolicyError(
                    "display band does not match observation and thresholds"
                )
            if self.operator_label != _BAND_LABELS[self.display_band]:
                raise MeterDisplayPolicyError("display band and operator label disagree")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_type": DECISION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": CANONICAL_OWNER_TASK,
            "binding_state": self.binding_state.value,
            "reason_codes": [item.value for item in self.reason_codes],
            "policy_ref": self.policy_ref,
            "policy_revision": self.policy_revision,
            "predecessor_policy_sha256": self.predecessor_policy_sha256,
            "policy_revision_sha256": self.policy_revision_sha256,
            "currentness_receipt_sha256": self.currentness_receipt_sha256,
            "policy_currentness_confirmed": self.policy_currentness_confirmed,
            "fixture_policy_currentness_matched": self.fixture_policy_currentness_matched,
            "thresholds_available": self.thresholds_available,
            "target_floor_dbfs": self.target_floor_dbfs,
            "target_ceiling_dbfs": self.target_ceiling_dbfs,
            "warning_dbfs": self.warning_dbfs,
            "true_clip_dbfs": self.true_clip_dbfs,
            "observation_state": self.observation_state.value,
            "sample_peak_dbfs": self.sample_peak_dbfs,
            "measured_sample_values": self.measured_sample_values,
            "display_band": self.display_band.value,
            "operator_label": self.operator_label,
            **{name: False for name in _DECISION_FALSE_FLAGS},
            "external_effect_count": 0,
            "fixture_only": True,
            "authority_created": False,
            "production_eligible": False,
            "trusted_currentness_admitted": False,
        }
        body["decision_sha256"] = _hash(
            DECISION_DIGEST_DOMAIN, body, "decision_sha256"
        )
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeterDisplayDecision":
        snapshot = _snapshot_mapping(value, _DECISION_FIELDS, "meter display decision")
        if (
            snapshot["record_type"] != DECISION_RECORD_TYPE
            or type(snapshot["schema_version"]) is not int
            or snapshot["schema_version"] != SCHEMA_VERSION
            or snapshot["canonical_owner_task"] != CANONICAL_OWNER_TASK
        ):
            raise MeterDisplayPolicyError("meter display decision discriminator is invalid")
        for name in _DECISION_FALSE_FLAGS:
            if snapshot[name] is not False:
                raise MeterDisplayPolicyError(f"{name} must remain false")
        if snapshot["external_effect_count"] != 0 or isinstance(
            snapshot["external_effect_count"], bool
        ):
            raise MeterDisplayPolicyError("external_effect_count must remain zero")
        if (
            snapshot["fixture_only"] is not True
            or snapshot["authority_created"] is not False
            or snapshot["production_eligible"] is not False
            or snapshot["trusted_currentness_admitted"] is not False
        ):
            raise MeterDisplayPolicyError(
                "fixture/authority/currentness boundary flags are invalid"
            )
        _digest(snapshot["decision_sha256"], "decision_sha256")
        if snapshot["decision_sha256"] != _hash(
            DECISION_DIGEST_DOMAIN, snapshot, "decision_sha256"
        ):
            raise MeterDisplayPolicyError("decision_sha256 mismatch")
        result = cls(
            binding_state=snapshot["binding_state"],
            reason_codes=tuple(snapshot["reason_codes"]),
            policy_ref=snapshot["policy_ref"],
            policy_revision=snapshot["policy_revision"],
            predecessor_policy_sha256=snapshot["predecessor_policy_sha256"],
            policy_revision_sha256=snapshot["policy_revision_sha256"],
            currentness_receipt_sha256=snapshot["currentness_receipt_sha256"],
            policy_currentness_confirmed=snapshot["policy_currentness_confirmed"],
            fixture_policy_currentness_matched=snapshot[
                "fixture_policy_currentness_matched"
            ],
            thresholds_available=snapshot["thresholds_available"],
            target_floor_dbfs=snapshot["target_floor_dbfs"],
            target_ceiling_dbfs=snapshot["target_ceiling_dbfs"],
            warning_dbfs=snapshot["warning_dbfs"],
            true_clip_dbfs=snapshot["true_clip_dbfs"],
            observation_state=snapshot["observation_state"],
            sample_peak_dbfs=snapshot["sample_peak_dbfs"],
            measured_sample_values=snapshot["measured_sample_values"],
            display_band=snapshot["display_band"],
            operator_label=snapshot["operator_label"],
        )
        if result.to_dict() != snapshot:
            raise MeterDisplayPolicyError("meter display decision is noncanonical")
        return result


_BAND_LABELS = {
    MeterDisplayBand.BELOW_TARGET: "目標未満",
    MeterDisplayBand.TARGET: "目標範囲",
    MeterDisplayBand.ABOVE_TARGET: "目標超過",
    MeterDisplayBand.WARNING: "警告",
    MeterDisplayBand.TRUE_CLIP: "クリップ",
}

_BINDING_REASONS = {
    PolicyBindingState.NOT_BOUND: MeterDisplayReason.POLICY_NOT_BOUND,
    PolicyBindingState.STALE: MeterDisplayReason.POLICY_STALE,
    PolicyBindingState.REVOKED: MeterDisplayReason.POLICY_REVOKED,
    PolicyBindingState.MISMATCH: MeterDisplayReason.POLICY_MISMATCH,
}


def _unconfirmed(
    *,
    binding: MeterDisplayPolicyBinding,
    observation: PeakObservation,
    reason: MeterDisplayReason,
    fixture_policy: MeterDisplayPolicyRevision | None = None,
) -> MeterDisplayDecision:
    fixture_matched = fixture_policy is not None
    return MeterDisplayDecision(
        binding_state=binding.state,
        reason_codes=(reason,),
        policy_ref=binding.policy_ref,
        policy_revision=binding.policy_revision,
        predecessor_policy_sha256=binding.predecessor_policy_sha256,
        policy_revision_sha256=binding.policy_revision_sha256,
        currentness_receipt_sha256=binding.currentness_receipt_sha256,
        policy_currentness_confirmed=False,
        fixture_policy_currentness_matched=fixture_matched,
        thresholds_available=fixture_matched,
        target_floor_dbfs=(None if fixture_policy is None else fixture_policy.target_floor_dbfs),
        target_ceiling_dbfs=(
            None if fixture_policy is None else fixture_policy.target_ceiling_dbfs
        ),
        warning_dbfs=None if fixture_policy is None else fixture_policy.warning_dbfs,
        true_clip_dbfs=None if fixture_policy is None else fixture_policy.true_clip_dbfs,
        observation_state=observation.state,
        sample_peak_dbfs=observation.sample_peak_dbfs,
        measured_sample_values=observation.measured_sample_values,
        display_band=MeterDisplayBand.UNCONFIRMED,
        operator_label=UNCONFIRMED_LABEL,
    )


def compile_meter_display(
    *,
    policy_document: Mapping[str, Any] | None,
    binding: MeterDisplayPolicyBinding,
    sample_peak_dbfs: float | None,
    measured_sample_values: int,
) -> MeterDisplayDecision:
    """Compile one body-free display decision without reading or changing audio."""

    if type(binding) is not MeterDisplayPolicyBinding:
        raise MeterDisplayPolicyError("binding type is invalid")
    observation = PeakObservation.from_scalar(
        sample_peak_dbfs, measured_sample_values=measured_sample_values
    )
    if binding.state is PolicyBindingState.NOT_BOUND:
        if policy_document is not None:
            return _unconfirmed(
                binding=binding,
                observation=observation,
                reason=MeterDisplayReason.POLICY_MISMATCH,
            )
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.POLICY_NOT_BOUND,
        )
    if binding.state in {
        PolicyBindingState.STALE,
        PolicyBindingState.REVOKED,
        PolicyBindingState.MISMATCH,
    }:
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=_BINDING_REASONS[binding.state],
        )
    if policy_document is None:
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.POLICY_DOCUMENT_MISSING,
        )
    try:
        policy = MeterDisplayPolicyRevision.from_dict(policy_document)
    except (MeterDisplayPolicyError, TypeError):
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.POLICY_DOCUMENT_INVALID,
        )
    if (
        policy.policy_ref != binding.policy_ref
        or policy.policy_revision != binding.policy_revision
        or policy.predecessor_policy_sha256 != binding.predecessor_policy_sha256
        or policy.to_dict()["policy_revision_sha256"]
        != binding.policy_revision_sha256
    ):
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.POLICY_BINDING_MISMATCH,
        )
    try:
        binding.assert_fixture_policy(policy)
    except MeterDisplayPolicyError:
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.POLICY_BINDING_MISMATCH,
        )
    if observation.state is PeakObservationState.INSUFFICIENT_INPUT:
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.INSUFFICIENT_INPUT,
            fixture_policy=policy,
        )
    if observation.state in {
        PeakObservationState.INVALID_NONFINITE,
        PeakObservationState.INVALID_OUT_OF_RANGE,
    }:
        return _unconfirmed(
            binding=binding,
            observation=observation,
            reason=MeterDisplayReason.INVALID_METER_SCALAR,
            fixture_policy=policy,
        )
    band = _classify_band(policy, observation)
    return MeterDisplayDecision(
        binding_state=binding.state,
        reason_codes=(),
        policy_ref=policy.policy_ref,
        policy_revision=policy.policy_revision,
        predecessor_policy_sha256=policy.predecessor_policy_sha256,
        policy_revision_sha256=policy.to_dict()["policy_revision_sha256"],
        currentness_receipt_sha256=binding.currentness_receipt_sha256,
        policy_currentness_confirmed=False,
        fixture_policy_currentness_matched=True,
        thresholds_available=True,
        target_floor_dbfs=policy.target_floor_dbfs,
        target_ceiling_dbfs=policy.target_ceiling_dbfs,
        warning_dbfs=policy.warning_dbfs,
        true_clip_dbfs=policy.true_clip_dbfs,
        observation_state=observation.state,
        sample_peak_dbfs=observation.sample_peak_dbfs,
        measured_sample_values=observation.measured_sample_values,
        display_band=band,
        operator_label=_BAND_LABELS[band],
    )


__all__ = [
    "CANONICAL_OWNER_TASK",
    "DECISION_RECORD_TYPE",
    "FixtureMeterDisplayCurrentnessSeal",
    "MeterDisplayBand",
    "MeterDisplayDecision",
    "MeterDisplayPolicyBinding",
    "MeterDisplayPolicyError",
    "MeterDisplayPolicyRevision",
    "MeterDisplayReason",
    "POLICY_RECORD_TYPE",
    "PeakObservation",
    "PeakObservationState",
    "PolicyBindingState",
    "SCHEMA_VERSION",
    "UNCONFIRMED_LABEL",
    "compile_fixture_meter_display_currentness",
    "compile_meter_display",
]
