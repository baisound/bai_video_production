"""Effect-zero TASK-065 validation of a synthetic preactivation fixture.

The objects in this module are audit projections and consumer-local replay
guards.  They do not create Product authority and never call the montage
adapter, TASK-036, or a Product store.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from threading import Lock
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
FIXTURE_MESSAGE_TYPE = "Task065PreactivationChainFixture"
VALIDATION_MESSAGE_TYPE = "Task065PreactivationFixtureValidation"
PREACTIVATION_PHASE = "PREACTIVATION"
VALIDATED_STATUS = "SYNTHETIC_FIXTURE_VALIDATED"
EVIDENCE_MODE = "SYNTHETIC_PUBLIC_SAFE_FIXTURE"
TASK072_DESIGN_SHA256 = (
    "sha256:4f6f21e97d96aa3ffca16f57679abf80d081de6d85d599347fd955c8899ce3c7"
)

_OPAQUE_ID_RE = re.compile(r"^(?:op|inst|rec|prof|rcpt)_[0-9a-f]{32}$")
_MAX_DEPTH = 10
_MAX_NODES = 256
_MAX_MAPPING_MEMBERS = 32
_MAX_SEQUENCE_ITEMS = 32
_MAX_STRING_CODEPOINTS = 512
_MAX_STRING_BYTES = 2048
_EVIDENCE_DOMAIN = b"TASK-065-PREACTIVATION-CHAIN-EVIDENCE-V1\x00"
_VALIDATION_DOMAIN = b"TASK-065-PREACTIVATION-FIXTURE-VALIDATION-V1\x00"


class MontageLearningProductionLinkageError(ValueError):
    """Body-free stable rejection from the TASK-065 consumer boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise MontageLearningProductionLinkageError(code)


def _require_opaque_id(value: object, prefix: str, code: str) -> str:
    if (
        type(value) is not str
        or _OPAQUE_ID_RE.fullmatch(value) is None
        or not value.startswith(f"{prefix}_")
    ):
        _fail(code)
    return value


def _require_sha(value: object, code: str) -> str:
    if type(value) is not str:
        _fail(code)
    try:
        return validate_sha256(value)
    except ValueError:
        _fail(code)


def _require_bool(value: object, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        _fail(code)


def _exact_mapping(value: object, fields: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != fields:
        _fail(code)
    return value


def _bounded_builtin_snapshot(value: object) -> dict[str, Any]:
    """Copy one bounded built-in JSON tree before canonicalization.

    This prevents mapping subclasses, non-finite numbers, recursive structures,
    and resource-heavy trees from reaching hashing first.
    """

    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES or depth > _MAX_DEPTH:
            _fail("ERR_TASK065_FIXTURE_BOUNDS")
        if type(current) is dict:
            if len(current) > _MAX_MAPPING_MEMBERS:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            for key, child in current.items():
                if type(key) is not str:
                    _fail("ERR_TASK065_FIXTURE_TYPE")
                if (
                    len(key) > _MAX_STRING_CODEPOINTS
                    or len(key.encode("utf-8")) > _MAX_STRING_BYTES
                ):
                    _fail("ERR_TASK065_FIXTURE_BOUNDS")
                stack.append((child, depth + 1))
        elif type(current) is list:
            if len(current) > _MAX_SEQUENCE_ITEMS:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            stack.extend((child, depth + 1) for child in current)
        elif type(current) is str:
            if (
                len(current) > _MAX_STRING_CODEPOINTS
                or len(current.encode("utf-8")) > _MAX_STRING_BYTES
                or "\x00" in current
            ):
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
        elif type(current) is int:
            if current < -(2**63) or current > 2**63 - 1:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
        elif type(current) is bool or current is None:
            pass
        else:
            _fail("ERR_TASK065_FIXTURE_TYPE")
    if type(value) is not dict:
        _fail("ERR_TASK065_FIXTURE_SHAPE")
    try:
        return json.loads(canonical_json_bytes(value))
    except (RecursionError, TypeError, UnicodeError, ValueError):
        _fail("ERR_TASK065_FIXTURE_ENCODING")


@dataclass(frozen=True, slots=True)
class PreactivationChainPlan:
    """Closed expected coordinates for one effect-zero fixture validation."""

    operation_id: str
    install_instance_id: str
    record_id: str
    learning_sha256: str
    config_sha256: str
    adapter_build_sha256: str
    adapter_stage_receipt_sha256: str
    task036_import_receipt_sha256: str
    task036_completion_receipt_sha256: str
    task061b_completion_receipt_sha256: str
    public_receipt_id: str
    public_receipt_sha256: str
    hidden_correlation_sha256: str
    canonical_readback_sha256: str
    profile_id: str
    profile_sha256: str
    profile_readback_sha256: str

    def __post_init__(self) -> None:
        for field, prefix in (
            ("operation_id", "op"),
            ("install_instance_id", "inst"),
            ("record_id", "rec"),
            ("profile_id", "prof"),
            ("public_receipt_id", "rcpt"),
        ):
            _require_opaque_id(getattr(self, field), prefix, "ERR_TASK065_PLAN_ID")
        for field in (
            "learning_sha256",
            "config_sha256",
            "adapter_build_sha256",
            "adapter_stage_receipt_sha256",
            "task036_import_receipt_sha256",
            "task036_completion_receipt_sha256",
            "task061b_completion_receipt_sha256",
            "public_receipt_sha256",
            "hidden_correlation_sha256",
            "canonical_readback_sha256",
            "profile_sha256",
            "profile_readback_sha256",
        ):
            _require_sha(getattr(self, field), "ERR_TASK065_PLAN_DIGEST")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": "Task065PreactivationChainPlan",
            "phase": PREACTIVATION_PHASE,
            "evidence_mode": EVIDENCE_MODE,
            "task072_design_sha256": TASK072_DESIGN_SHA256,
            "operation_id": self.operation_id,
            "install_instance_id": self.install_instance_id,
            "record_id": self.record_id,
            "learning_sha256": self.learning_sha256,
            "config_sha256": self.config_sha256,
            "adapter_build_sha256": self.adapter_build_sha256,
            "adapter_stage_receipt_sha256": self.adapter_stage_receipt_sha256,
            "task036_import_receipt_sha256": self.task036_import_receipt_sha256,
            "task036_completion_receipt_sha256": self.task036_completion_receipt_sha256,
            "task061b_completion_receipt_sha256": self.task061b_completion_receipt_sha256,
            "public_receipt_id": self.public_receipt_id,
            "public_receipt_sha256": self.public_receipt_sha256,
            "canonical_readback_sha256": self.canonical_readback_sha256,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "profile_readback_sha256": self.profile_readback_sha256,
            "authority_created": False,
            "local_effects_authorized": False,
        }
        private_binding = {
            "adapter_stage_receipt_sha256": self.adapter_stage_receipt_sha256,
            "task036_import_receipt_sha256": self.task036_import_receipt_sha256,
            "public_receipt_id": self.public_receipt_id,
            "public_receipt_sha256": self.public_receipt_sha256,
            "hidden_correlation_sha256": self.hidden_correlation_sha256,
            "canonical_readback_sha256": self.canonical_readback_sha256,
            "profile_readback_sha256": self.profile_readback_sha256,
        }
        body["expected_evidence_binding_sha256"] = sha256_bytes(
            _EVIDENCE_DOMAIN + canonical_json_bytes(private_binding)
        )
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class PreactivationFixtureValidation:
    operation_id: str
    install_instance_id: str
    record_id: str
    learning_sha256: str
    profile_id: str
    profile_sha256: str
    public_receipt_id: str
    plan_sha256: str
    task036_completion_receipt_sha256: str
    task061b_completion_receipt_sha256: str
    public_receipt_sha256: str
    canonical_readback_sha256: str
    profile_readback_sha256: str
    evidence_binding_sha256: str
    task072_design_sha256: str = TASK072_DESIGN_SHA256

    def __post_init__(self) -> None:
        for field, prefix in (
            ("operation_id", "op"),
            ("install_instance_id", "inst"),
            ("record_id", "rec"),
            ("profile_id", "prof"),
            ("public_receipt_id", "rcpt"),
        ):
            _require_opaque_id(
                getattr(self, field), prefix, "ERR_TASK065_VALIDATION_ID"
            )
        for field in (
            "learning_sha256",
            "profile_sha256",
            "plan_sha256",
            "task036_completion_receipt_sha256",
            "task061b_completion_receipt_sha256",
            "public_receipt_sha256",
            "canonical_readback_sha256",
            "profile_readback_sha256",
            "evidence_binding_sha256",
            "task072_design_sha256",
        ):
            _require_sha(getattr(self, field), "ERR_TASK065_VALIDATION_DIGEST")
        if self.task072_design_sha256 != TASK072_DESIGN_SHA256:
            _fail("ERR_TASK065_TASK072_DESIGN_MISMATCH")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": VALIDATION_MESSAGE_TYPE,
            "phase": PREACTIVATION_PHASE,
            "status": VALIDATED_STATUS,
            "evidence_mode": EVIDENCE_MODE,
            "task072_design_sha256": self.task072_design_sha256,
            "operation_id": self.operation_id,
            "install_instance_id": self.install_instance_id,
            "record_id": self.record_id,
            "learning_sha256": self.learning_sha256,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "public_receipt_id": self.public_receipt_id,
            "plan_sha256": self.plan_sha256,
            "task036_completion_receipt_sha256": self.task036_completion_receipt_sha256,
            "task061b_completion_receipt_sha256": self.task061b_completion_receipt_sha256,
            "public_receipt_sha256": self.public_receipt_sha256,
            "canonical_readback_sha256": self.canonical_readback_sha256,
            "profile_readback_sha256": self.profile_readback_sha256,
            "evidence_binding_sha256": self.evidence_binding_sha256,
            "hidden_correlation_fixture_matched": True,
            "historical_stage_invocation_count": 1,
            "historical_import_invocation_count": 1,
            "task065_adapter_call_count": 0,
            "task065_task036_call_count": 0,
            "project_delta_count": 0,
            "bridge_delta_count": 0,
            "profile_delta_count": 0,
            "config_delta_count": 0,
            "history_delta_count": 0,
            "authority_created": False,
            "activation_authorized": False,
            "steady_state_authorized": False,
            "real_installed_adapter_verified": False,
            "activation_prerequisite_satisfied": False,
            "production_chain_complete": False,
            "task072_implementation_receipt_verified": False,
        }
        body["validation_sha256"] = sha256_bytes(
            _VALIDATION_DOMAIN + canonical_json_bytes(body)
        )
        return body


_TOP_FIELDS = frozenset(
    {
        "schema_version",
        "message_type",
        "phase",
        "evidence_mode",
        "task072_design_sha256",
        "plan_sha256",
        "operation_id",
        "install_instance_id",
        "task036_completion_receipt_sha256",
        "task061b_completion_receipt_sha256",
        "adapter_stage",
        "task036_import",
        "public_receipt",
        "hidden_correlation",
        "canonical_readback",
        "profile_readback",
        "evidence_complete",
        "authority_created",
    }
)
_STAGE_FIELDS = frozenset(
    {
        "operation_id",
        "record_id",
        "learning_sha256",
        "config_sha256",
        "adapter_build_sha256",
        "invocation_count",
        "status",
        "receipt_sha256",
    }
)
_IMPORT_FIELDS = frozenset(
    {
        "operation_id",
        "record_id",
        "learning_sha256",
        "invocation_count",
        "status",
        "receipt_sha256",
    }
)
_PUBLIC_RECEIPT_FIELDS = frozenset(
    {
        "receipt_id",
        "record_id",
        "learning_sha256",
        "status",
        "receipt_sha256",
        "authority_created",
    }
)
_CORRELATION_FIELDS = frozenset(
    {
        "operation_id",
        "install_instance_id",
        "config_sha256",
        "record_id",
        "learning_sha256",
        "public_receipt_sha256",
        "canonical_readback_sha256",
        "profile_readback_sha256",
        "correlation_sha256",
    }
)
_CANONICAL_FIELDS = frozenset(
    {
        "record_id",
        "learning_sha256",
        "canonical_revision",
        "readback_sha256",
        "durable_readback_verified",
        "authority_created",
    }
)
_PROFILE_FIELDS = frozenset(
    {
        "profile_id",
        "profile_sha256",
        "source_record_id",
        "source_learning_sha256",
        "readback_sha256",
        "advisory_only",
        "canonical_timeline",
        "auto_apply_authorized",
        "durable_readback_verified",
        "authority_created",
    }
)


class PreactivationChainConsumerPort:
    """One-use, fail-closed validation of synthetic chain Evidence."""

    __slots__ = ("_plan", "_state", "_lock")

    def __init__(self, plan: PreactivationChainPlan) -> None:
        if type(plan) is not PreactivationChainPlan:
            raise TypeError("exact PreactivationChainPlan is required")
        self._plan = plan
        self._state = "ARMED"
        self._lock = Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def validate(self, fixture: object) -> PreactivationFixtureValidation:
        with self._lock:
            if self._state != "ARMED":
                _fail("ERR_TASK065_CONSUMER_ALREADY_USED")
            self._state = "IN_FLIGHT"
        try:
            snapshot = _bounded_builtin_snapshot(fixture)
            validation = self._validate_snapshot(snapshot)
        except Exception as exc:
            with self._lock:
                self._state = "FAILED_CLOSED"
            if isinstance(exc, MontageLearningProductionLinkageError):
                raise
            raise MontageLearningProductionLinkageError(
                "ERR_TASK065_CHAIN_REJECTED"
            ) from None
        with self._lock:
            self._state = "COMPLETED"
        return validation

    def _validate_snapshot(self, fixture: dict[str, Any]) -> PreactivationFixtureValidation:
        fixture = _exact_mapping(fixture, _TOP_FIELDS, "ERR_TASK065_FIXTURE_SHAPE")
        plan_value = self._plan.to_dict()
        if (
            fixture["schema_version"] != SCHEMA_VERSION
            or fixture["message_type"] != FIXTURE_MESSAGE_TYPE
            or fixture["phase"] != PREACTIVATION_PHASE
            or fixture["evidence_mode"] != EVIDENCE_MODE
            or fixture["task072_design_sha256"] != TASK072_DESIGN_SHA256
        ):
            _fail("ERR_TASK065_FIXTURE_CONTRACT")
        _require_bool(fixture["evidence_complete"], True, "ERR_TASK065_EVIDENCE_INCOMPLETE")
        _require_bool(fixture["authority_created"], False, "ERR_TASK065_AUTHORITY_CLAIM")
        if fixture["plan_sha256"] != plan_value["plan_sha256"]:
            _fail("ERR_TASK065_PLAN_MISMATCH")
        for field in ("operation_id", "install_instance_id"):
            if fixture[field] != getattr(self._plan, field):
                _fail("ERR_TASK065_COORDINATE_MISMATCH")
        for field in (
            "task036_completion_receipt_sha256",
            "task061b_completion_receipt_sha256",
        ):
            _require_sha(fixture[field], "ERR_TASK065_RECEIPT_DIGEST")
            if fixture[field] != getattr(self._plan, field):
                _fail("ERR_TASK065_RECEIPT_MISMATCH")

        stage = _exact_mapping(
            fixture["adapter_stage"], _STAGE_FIELDS, "ERR_TASK065_STAGE_SHAPE"
        )
        imported = _exact_mapping(
            fixture["task036_import"], _IMPORT_FIELDS, "ERR_TASK065_IMPORT_SHAPE"
        )
        public = _exact_mapping(
            fixture["public_receipt"],
            _PUBLIC_RECEIPT_FIELDS,
            "ERR_TASK065_PUBLIC_RECEIPT_SHAPE",
        )
        correlation = _exact_mapping(
            fixture["hidden_correlation"],
            _CORRELATION_FIELDS,
            "ERR_TASK065_CORRELATION_SHAPE",
        )
        canonical = _exact_mapping(
            fixture["canonical_readback"],
            _CANONICAL_FIELDS,
            "ERR_TASK065_CANONICAL_SHAPE",
        )
        profile = _exact_mapping(
            fixture["profile_readback"],
            _PROFILE_FIELDS,
            "ERR_TASK065_PROFILE_SHAPE",
        )

        if type(stage["invocation_count"]) is not int or stage["invocation_count"] != 1:
            _fail("ERR_TASK065_STAGE_COUNT")
        if type(imported["invocation_count"]) is not int or imported["invocation_count"] != 1:
            _fail("ERR_TASK065_IMPORT_COUNT")
        if stage["status"] != "STAGED":
            _fail("ERR_TASK065_STAGE_STATUS")
        if imported["status"] not in {"ACCEPTED", "DUPLICATE"}:
            _fail("ERR_TASK065_IMPORT_STATUS")
        if public["status"] != imported["status"]:
            _fail("ERR_TASK065_RECEIPT_STATUS")

        for mapping in (stage, imported, public, correlation, canonical):
            if mapping["record_id"] != self._plan.record_id:
                _fail("ERR_TASK065_RECORD_MISMATCH")
            if mapping["learning_sha256"] != self._plan.learning_sha256:
                _fail("ERR_TASK065_LEARNING_MISMATCH")
        if profile["source_record_id"] != self._plan.record_id:
            _fail("ERR_TASK065_RECORD_MISMATCH")
        if profile["source_learning_sha256"] != self._plan.learning_sha256:
            _fail("ERR_TASK065_LEARNING_MISMATCH")
        if stage["operation_id"] != self._plan.operation_id:
            _fail("ERR_TASK065_OPERATION_MISMATCH")
        if imported["operation_id"] != self._plan.operation_id:
            _fail("ERR_TASK065_OPERATION_MISMATCH")
        if correlation["operation_id"] != self._plan.operation_id:
            _fail("ERR_TASK065_OPERATION_MISMATCH")
        if correlation["install_instance_id"] != self._plan.install_instance_id:
            _fail("ERR_TASK065_INSTANCE_MISMATCH")
        if stage["config_sha256"] != self._plan.config_sha256:
            _fail("ERR_TASK065_CONFIG_MISMATCH")
        if correlation["config_sha256"] != self._plan.config_sha256:
            _fail("ERR_TASK065_CONFIG_MISMATCH")
        if stage["adapter_build_sha256"] != self._plan.adapter_build_sha256:
            _fail("ERR_TASK065_ADAPTER_BUILD_MISMATCH")
        if stage["receipt_sha256"] != self._plan.adapter_stage_receipt_sha256:
            _fail("ERR_TASK065_STAGE_RECEIPT_MISMATCH")
        if imported["receipt_sha256"] != self._plan.task036_import_receipt_sha256:
            _fail("ERR_TASK065_IMPORT_RECEIPT_MISMATCH")

        for value in (
            stage["learning_sha256"],
            stage["config_sha256"],
            stage["adapter_build_sha256"],
            stage["receipt_sha256"],
            imported["learning_sha256"],
            imported["receipt_sha256"],
            public["learning_sha256"],
            public["receipt_sha256"],
            correlation["learning_sha256"],
            correlation["config_sha256"],
            correlation["public_receipt_sha256"],
            correlation["canonical_readback_sha256"],
            correlation["profile_readback_sha256"],
            correlation["correlation_sha256"],
            canonical["learning_sha256"],
            canonical["readback_sha256"],
            profile["profile_sha256"],
            profile["source_learning_sha256"],
            profile["readback_sha256"],
        ):
            _require_sha(value, "ERR_TASK065_EVIDENCE_DIGEST")

        if public["receipt_sha256"] != self._plan.public_receipt_sha256:
            _fail("ERR_TASK065_PUBLIC_RECEIPT_MISMATCH")
        if correlation["public_receipt_sha256"] != self._plan.public_receipt_sha256:
            _fail("ERR_TASK065_CORRELATION_MISMATCH")
        if correlation["correlation_sha256"] != self._plan.hidden_correlation_sha256:
            _fail("ERR_TASK065_CORRELATION_MISMATCH")
        if canonical["readback_sha256"] != self._plan.canonical_readback_sha256:
            _fail("ERR_TASK065_CANONICAL_MISMATCH")
        if correlation["canonical_readback_sha256"] != self._plan.canonical_readback_sha256:
            _fail("ERR_TASK065_CORRELATION_MISMATCH")
        if profile["profile_id"] != self._plan.profile_id:
            _fail("ERR_TASK065_PROFILE_MISMATCH")
        if profile["profile_sha256"] != self._plan.profile_sha256:
            _fail("ERR_TASK065_PROFILE_MISMATCH")
        if profile["readback_sha256"] != self._plan.profile_readback_sha256:
            _fail("ERR_TASK065_PROFILE_MISMATCH")
        if correlation["profile_readback_sha256"] != self._plan.profile_readback_sha256:
            _fail("ERR_TASK065_CORRELATION_MISMATCH")

        _require_opaque_id(
            public["receipt_id"], "rcpt", "ERR_TASK065_PUBLIC_RECEIPT_ID"
        )
        if public["receipt_id"] != self._plan.public_receipt_id:
            _fail("ERR_TASK065_PUBLIC_RECEIPT_ID_MISMATCH")
        if type(canonical["canonical_revision"]) is not int or canonical["canonical_revision"] < 1:
            _fail("ERR_TASK065_CANONICAL_REVISION")
        for mapping in (public, canonical, profile):
            _require_bool(mapping["authority_created"], False, "ERR_TASK065_AUTHORITY_CLAIM")
        _require_bool(
            canonical["durable_readback_verified"],
            True,
            "ERR_TASK065_CANONICAL_NOT_DURABLE",
        )
        _require_bool(profile["advisory_only"], True, "ERR_TASK065_PROFILE_AUTHORITY")
        _require_bool(profile["canonical_timeline"], False, "ERR_TASK065_PROFILE_AUTHORITY")
        _require_bool(profile["auto_apply_authorized"], False, "ERR_TASK065_PROFILE_AUTHORITY")
        _require_bool(
            profile["durable_readback_verified"],
            True,
            "ERR_TASK065_PROFILE_NOT_DURABLE",
        )

        private_binding = {
            "adapter_stage_receipt_sha256": stage["receipt_sha256"],
            "task036_import_receipt_sha256": imported["receipt_sha256"],
            "public_receipt_id": public["receipt_id"],
            "public_receipt_sha256": public["receipt_sha256"],
            "hidden_correlation_sha256": correlation["correlation_sha256"],
            "canonical_readback_sha256": canonical["readback_sha256"],
            "profile_readback_sha256": profile["readback_sha256"],
        }
        evidence_binding = sha256_bytes(
            _EVIDENCE_DOMAIN + canonical_json_bytes(private_binding)
        )
        if evidence_binding != plan_value["expected_evidence_binding_sha256"]:
            _fail("ERR_TASK065_EVIDENCE_BINDING_MISMATCH")
        return PreactivationFixtureValidation(
            operation_id=self._plan.operation_id,
            install_instance_id=self._plan.install_instance_id,
            record_id=self._plan.record_id,
            learning_sha256=self._plan.learning_sha256,
            profile_id=self._plan.profile_id,
            profile_sha256=self._plan.profile_sha256,
            public_receipt_id=self._plan.public_receipt_id,
            plan_sha256=plan_value["plan_sha256"],
            task036_completion_receipt_sha256=self._plan.task036_completion_receipt_sha256,
            task061b_completion_receipt_sha256=self._plan.task061b_completion_receipt_sha256,
            public_receipt_sha256=self._plan.public_receipt_sha256,
            canonical_readback_sha256=self._plan.canonical_readback_sha256,
            profile_readback_sha256=self._plan.profile_readback_sha256,
            evidence_binding_sha256=evidence_binding,
            task072_design_sha256=TASK072_DESIGN_SHA256,
        )


__all__ = [
    "EVIDENCE_MODE",
    "FIXTURE_MESSAGE_TYPE",
    "MontageLearningProductionLinkageError",
    "PreactivationChainConsumerPort",
    "PreactivationChainPlan",
    "PreactivationFixtureValidation",
    "PREACTIVATION_PHASE",
    "SCHEMA_VERSION",
    "TASK072_DESIGN_SHA256",
    "VALIDATED_STATUS",
    "VALIDATION_MESSAGE_TYPE",
]
