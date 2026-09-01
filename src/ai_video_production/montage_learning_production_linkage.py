"""Effect-zero TASK-065 validation of synthetic integration fixtures.

The objects in this module are audit projections and consumer-local replay
guards.  They do not create Product authority and never call the montage
adapter, TASK-036, or a Product store.
"""

from __future__ import annotations

from dataclasses import dataclass
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
COMMON_INSTALLED_CONTRACT = "TASK065-P0L-COMMON-INSTALLED-DISCOVERY-RECEIPT-V1"
COMMON_INSTALLED_MODE = "SYNTHETIC_EXPECTED_COORDINATES"
COMMON_INSTALLED_VALIDATION_MESSAGE_TYPE = (
    "Task065CommonInstalledDiscoveryFixtureValidation"
)
COMMON_INSTALLED_VALIDATED_STATUS = "SYNTHETIC_COMMON_COORDINATES_VALIDATED"

_OPAQUE_ID_RE = re.compile(r"^(?:op|inst|rec|prof|rcpt)_[0-9a-f]{32}$")
_COMMON_ID_RE = re.compile(r"^(?:inst|desc|receipt)_[0-9a-f]{32}$")
_RAW_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_DEPTH = 10
_MAX_NODES = 256
_MAX_MAPPING_MEMBERS = 32
_MAX_SEQUENCE_ITEMS = 32
_MAX_STRING_CODEPOINTS = 512
_MAX_STRING_BYTES = 2048
_EVIDENCE_DOMAIN = b"TASK-065-PREACTIVATION-CHAIN-EVIDENCE-V1\x00"
_VALIDATION_DOMAIN = b"TASK-065-PREACTIVATION-FIXTURE-VALIDATION-V1\x00"
_COMMON_PLAN_DOMAIN = b"TASK-065-COMMON-INSTALLED-PLAN-V1\x00"
_COMMON_FIXTURE_DOMAIN = b"TASK-065-COMMON-INSTALLED-FIXTURE-V1\x00"
_COMMON_VALIDATION_DOMAIN = b"TASK-065-COMMON-INSTALLED-VALIDATION-V1\x00"
_COMMON_MAX_CANONICAL_BYTES = 8192


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


def _require_common_id(value: object, prefix: str, code: str) -> str:
    if (
        type(value) is not str
        or _COMMON_ID_RE.fullmatch(value) is None
        or not value.startswith(f"{prefix}_")
    ):
        _fail(code)
    return value


def _require_raw_sha(value: object, code: str) -> str:
    if type(value) is not str or _RAW_SHA_RE.fullmatch(value) is None:
        _fail(code)
    return value


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
    nodes = 0

    def copy_bounded(current: object, depth: int) -> object:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_NODES or depth > _MAX_DEPTH:
            _fail("ERR_TASK065_FIXTURE_BOUNDS")
        if type(current) is dict:
            if len(current) > _MAX_MAPPING_MEMBERS:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            copied: dict[str, object] = {}
            for key, child in current.items():
                if type(key) is not str:
                    _fail("ERR_TASK065_FIXTURE_TYPE")
                if (
                    len(key) > _MAX_STRING_CODEPOINTS
                    or len(key.encode("utf-8")) > _MAX_STRING_BYTES
                ):
                    _fail("ERR_TASK065_FIXTURE_BOUNDS")
                copied[key] = copy_bounded(child, depth + 1)
            return copied
        elif type(current) is list:
            if len(current) > _MAX_SEQUENCE_ITEMS:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            return [copy_bounded(child, depth + 1) for child in current]
        elif type(current) is str:
            if (
                len(current) > _MAX_STRING_CODEPOINTS
                or len(current.encode("utf-8")) > _MAX_STRING_BYTES
                or "\x00" in current
            ):
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            return current
        elif type(current) is int:
            if current < -(2**63) or current > 2**63 - 1:
                _fail("ERR_TASK065_FIXTURE_BOUNDS")
            return current
        elif type(current) is bool or current is None:
            return current
        else:
            _fail("ERR_TASK065_FIXTURE_TYPE")

    try:
        snapshot = copy_bounded(value, 0)
    except RuntimeError:
        _fail("ERR_TASK065_FIXTURE_ENCODING")
    if type(snapshot) is not dict:
        _fail("ERR_TASK065_FIXTURE_SHAPE")
    try:
        canonical_json_bytes(snapshot)
    except (RecursionError, TypeError, UnicodeError, ValueError):
        _fail("ERR_TASK065_FIXTURE_ENCODING")
    return snapshot


_COMMON_TOP_FIELDS = frozenset(
    {
        "fixture_version",
        "contract",
        "mode",
        "fixture_only",
        "authority_created",
        "currentness_selected",
        "task063_completion_receipt_present",
        "task072_design_receipt_sha256",
        "task072_implementation_receipt_verified",
        "installed_snapshot_verified",
        "native_broker_executed",
        "expected_coordinates",
        "effects",
        "lanes",
        "public_diagnostics",
    }
)
_COMMON_COORDINATE_FIELDS = frozenset(
    {
        "install_instance_id",
        "descriptor_generation_id",
        "product_build_sha256",
        "package_payload_sha256",
        "product_exe_sha256",
        "owner_manifest_sha256",
        "task036_receipt_id",
        "task061b_receipt_id",
    }
)
_COMMON_EFFECT_FIELDS = frozenset(
    {
        "installed_discovery_started",
        "packaged_exe_started",
        "adapter_stage_started",
        "task036_import_started",
        "wav_body_read",
        "provider_started",
        "install_started",
        "release_started",
        "deploy_started",
        "production_activation_started",
    }
)
_COMMON_LANE_FIELDS = frozenset({"P0_L", "P0_E", "P0_V"})
_COMMON_P0L_FIELDS = frozenset(
    {
        "status",
        "expected_historical_adapter_stage_count",
        "expected_historical_task036_import_count",
        "task065_adapter_call_count",
        "task065_task036_call_count",
        "task065_project_delta",
        "task065_bridge_delta",
        "task065_profile_delta",
        "task065_config_history_delta",
    }
)
_COMMON_P0E_FIELDS = frozenset(
    {
        "status",
        "installed_package_readback_verified",
        "packaged_exe_started",
        "first_run_readback_verified",
        "startup_settings_readback_verified",
    }
)
_COMMON_P0V_FIELDS = frozenset(
    {
        "status",
        "wav_receipt_verified",
        "wav_body_read",
        "media_qa_executed",
        "provider_started",
    }
)
_COMMON_DIAGNOSTIC_FIELDS = frozenset(
    {
        "code",
        "absolute_path_count",
        "private_body_count",
        "secret_count",
        "os_detail_count",
    }
)


@dataclass(frozen=True, slots=True)
class CommonInstalledDiscoveryFixturePlan:
    """Public-safe expected coordinates; never a currentness/effect authority."""

    install_instance_id: str
    descriptor_generation_id: str
    product_build_sha256: str
    package_payload_sha256: str
    product_exe_sha256: str
    owner_manifest_sha256: str
    task036_receipt_id: str
    task061b_receipt_id: str

    def __post_init__(self) -> None:
        _require_common_id(
            self.install_instance_id, "inst", "ERR_TASK065_COMMON_PLAN_ID"
        )
        _require_common_id(
            self.descriptor_generation_id, "desc", "ERR_TASK065_COMMON_PLAN_ID"
        )
        _require_common_id(
            self.task036_receipt_id, "receipt", "ERR_TASK065_COMMON_PLAN_ID"
        )
        _require_common_id(
            self.task061b_receipt_id, "receipt", "ERR_TASK065_COMMON_PLAN_ID"
        )
        for field in (
            "product_build_sha256",
            "package_payload_sha256",
            "product_exe_sha256",
            "owner_manifest_sha256",
        ):
            _require_raw_sha(getattr(self, field), "ERR_TASK065_COMMON_PLAN_DIGEST")

    def expected_coordinates(self) -> dict[str, str]:
        return {
            "install_instance_id": self.install_instance_id,
            "descriptor_generation_id": self.descriptor_generation_id,
            "product_build_sha256": self.product_build_sha256,
            "package_payload_sha256": self.package_payload_sha256,
            "product_exe_sha256": self.product_exe_sha256,
            "owner_manifest_sha256": self.owner_manifest_sha256,
            "task036_receipt_id": self.task036_receipt_id,
            "task061b_receipt_id": self.task061b_receipt_id,
        }

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "contract": COMMON_INSTALLED_CONTRACT,
            "mode": COMMON_INSTALLED_MODE,
            "task072_design_receipt_sha256": TASK072_DESIGN_SHA256,
            "expected_coordinates": self.expected_coordinates(),
            "authority_created": False,
            "currentness_selected": False,
            "local_effects_authorized": False,
        }
        body["plan_sha256"] = sha256_bytes(
            _COMMON_PLAN_DOMAIN + canonical_json_bytes(body)
        )
        return body


@dataclass(frozen=True, slots=True)
class CommonInstalledDiscoveryFixtureValidation:
    install_instance_id: str
    descriptor_generation_id: str
    plan_sha256: str
    fixture_sha256: str

    def __post_init__(self) -> None:
        _require_common_id(
            self.install_instance_id, "inst", "ERR_TASK065_COMMON_VALIDATION_ID"
        )
        _require_common_id(
            self.descriptor_generation_id,
            "desc",
            "ERR_TASK065_COMMON_VALIDATION_ID",
        )
        _require_sha(self.plan_sha256, "ERR_TASK065_COMMON_VALIDATION_DIGEST")
        _require_sha(self.fixture_sha256, "ERR_TASK065_COMMON_VALIDATION_DIGEST")

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "message_type": COMMON_INSTALLED_VALIDATION_MESSAGE_TYPE,
            "status": COMMON_INSTALLED_VALIDATED_STATUS,
            "contract": COMMON_INSTALLED_CONTRACT,
            "mode": COMMON_INSTALLED_MODE,
            "fixture_only": True,
            "authority_created": False,
            "currentness_selected": False,
            "currentness_lease_created": False,
            "lane_effect_authority_created": False,
            "task063_completion_receipt_present": False,
            "task072_design_receipt_sha256": TASK072_DESIGN_SHA256,
            "task072_implementation_receipt_verified": False,
            "installed_snapshot_verified": False,
            "native_broker_executed": False,
            "install_instance_id": self.install_instance_id,
            "descriptor_generation_id": self.descriptor_generation_id,
            "plan_sha256": self.plan_sha256,
            "fixture_sha256": self.fixture_sha256,
            "p0_l_status": "NOT_CONFIRMED",
            "p0_e_status": "NOT_CONFIRMED",
            "p0_v_status": "NOT_CONFIRMED",
            "installed_discovery_started": False,
            "packaged_exe_started": False,
            "adapter_stage_started": False,
            "task036_import_started": False,
            "wav_body_read": False,
            "provider_started": False,
            "install_started": False,
            "release_started": False,
            "deploy_started": False,
            "production_activation_started": False,
        }
        body["validation_sha256"] = sha256_bytes(
            _COMMON_VALIDATION_DOMAIN + canonical_json_bytes(body)
        )
        return body


class CommonInstalledDiscoveryFixtureConsumerPort:
    """Validate an already-decoded synthetic mapping without minting authority.

    Raw fixture bytes require the separate strict fixture parser Gate. This
    audit-only port never treats a caller's decoder as Product currentness.
    """

    __slots__ = ("_plan", "_state", "_lock")

    def __init__(self, plan: CommonInstalledDiscoveryFixturePlan) -> None:
        if type(plan) is not CommonInstalledDiscoveryFixturePlan:
            raise TypeError("exact CommonInstalledDiscoveryFixturePlan is required")
        self._plan = plan
        self._state = "ARMED"
        self._lock = Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def validate(self, fixture: object) -> CommonInstalledDiscoveryFixtureValidation:
        with self._lock:
            if self._state != "ARMED":
                _fail("ERR_TASK065_COMMON_CONSUMER_ALREADY_USED")
            self._state = "IN_FLIGHT"
        try:
            snapshot = _bounded_builtin_snapshot(fixture)
            canonical = canonical_json_bytes(snapshot)
            if len(canonical) > _COMMON_MAX_CANONICAL_BYTES:
                _fail("ERR_TASK065_COMMON_FIXTURE_BOUNDS")
            validation = self._validate_snapshot(snapshot, canonical)
        except Exception as exc:
            with self._lock:
                self._state = "FAILED_CLOSED"
            if isinstance(exc, MontageLearningProductionLinkageError):
                raise
            raise MontageLearningProductionLinkageError(
                "ERR_TASK065_COMMON_FIXTURE_REJECTED"
            ) from None
        with self._lock:
            self._state = "COMPLETED"
        return validation

    def _validate_snapshot(
        self, fixture: dict[str, Any], canonical: bytes
    ) -> CommonInstalledDiscoveryFixtureValidation:
        fixture = _exact_mapping(
            fixture, _COMMON_TOP_FIELDS, "ERR_TASK065_COMMON_FIXTURE_SHAPE"
        )
        if (
            fixture["fixture_version"] != "1.0"
            or fixture["contract"] != COMMON_INSTALLED_CONTRACT
            or fixture["mode"] != COMMON_INSTALLED_MODE
            or fixture["task072_design_receipt_sha256"] != TASK072_DESIGN_SHA256
        ):
            _fail("ERR_TASK065_COMMON_FIXTURE_CONTRACT")
        _require_bool(
            fixture["fixture_only"], True, "ERR_TASK065_COMMON_AUTHORITY_CLAIM"
        )
        for field in (
            "authority_created",
            "currentness_selected",
            "task063_completion_receipt_present",
            "task072_implementation_receipt_verified",
            "installed_snapshot_verified",
            "native_broker_executed",
        ):
            _require_bool(
                fixture[field], False, "ERR_TASK065_COMMON_AUTHORITY_CLAIM"
            )

        coordinates = _exact_mapping(
            fixture["expected_coordinates"],
            _COMMON_COORDINATE_FIELDS,
            "ERR_TASK065_COMMON_COORDINATE_SHAPE",
        )
        for field, prefix in (
            ("install_instance_id", "inst"),
            ("descriptor_generation_id", "desc"),
            ("task036_receipt_id", "receipt"),
            ("task061b_receipt_id", "receipt"),
        ):
            _require_common_id(
                coordinates[field], prefix, "ERR_TASK065_COMMON_COORDINATE_ID"
            )
        for field in (
            "product_build_sha256",
            "package_payload_sha256",
            "product_exe_sha256",
            "owner_manifest_sha256",
        ):
            _require_raw_sha(
                coordinates[field], "ERR_TASK065_COMMON_COORDINATE_DIGEST"
            )
        if coordinates != self._plan.expected_coordinates():
            _fail("ERR_TASK065_COMMON_COORDINATE_MISMATCH")

        effects = _exact_mapping(
            fixture["effects"],
            _COMMON_EFFECT_FIELDS,
            "ERR_TASK065_COMMON_EFFECT_SHAPE",
        )
        for value in effects.values():
            _require_bool(value, False, "ERR_TASK065_COMMON_EFFECT_CLAIM")

        lanes = _exact_mapping(
            fixture["lanes"], _COMMON_LANE_FIELDS, "ERR_TASK065_COMMON_LANE_SHAPE"
        )
        p0_l = _exact_mapping(
            lanes["P0_L"], _COMMON_P0L_FIELDS, "ERR_TASK065_COMMON_LANE_SHAPE"
        )
        p0_e = _exact_mapping(
            lanes["P0_E"], _COMMON_P0E_FIELDS, "ERR_TASK065_COMMON_LANE_SHAPE"
        )
        p0_v = _exact_mapping(
            lanes["P0_V"], _COMMON_P0V_FIELDS, "ERR_TASK065_COMMON_LANE_SHAPE"
        )
        if (
            p0_l["status"] != "NOT_CONFIRMED"
            or p0_l["expected_historical_adapter_stage_count"] != "1"
            or p0_l["expected_historical_task036_import_count"] != "1"
        ):
            _fail("ERR_TASK065_COMMON_LANE_CLAIM")
        for field in (
            "task065_adapter_call_count",
            "task065_task036_call_count",
            "task065_project_delta",
            "task065_bridge_delta",
            "task065_profile_delta",
            "task065_config_history_delta",
        ):
            if p0_l[field] != "0":
                _fail("ERR_TASK065_COMMON_LANE_CLAIM")
        for lane in (p0_e, p0_v):
            if lane["status"] != "NOT_CONFIRMED":
                _fail("ERR_TASK065_COMMON_LANE_CLAIM")
            for field, value in lane.items():
                if field != "status":
                    _require_bool(value, False, "ERR_TASK065_COMMON_LANE_CLAIM")

        diagnostics = _exact_mapping(
            fixture["public_diagnostics"],
            _COMMON_DIAGNOSTIC_FIELDS,
            "ERR_TASK065_COMMON_DIAGNOSTIC_SHAPE",
        )
        if diagnostics["code"] != "NOT_CONFIRMED":
            _fail("ERR_TASK065_COMMON_DIAGNOSTIC_CLAIM")
        for field in (
            "absolute_path_count",
            "private_body_count",
            "secret_count",
            "os_detail_count",
        ):
            if diagnostics[field] != "0":
                _fail("ERR_TASK065_COMMON_DIAGNOSTIC_CLAIM")

        plan = self._plan.to_dict()
        return CommonInstalledDiscoveryFixtureValidation(
            install_instance_id=self._plan.install_instance_id,
            descriptor_generation_id=self._plan.descriptor_generation_id,
            plan_sha256=plan["plan_sha256"],
            fixture_sha256=sha256_bytes(_COMMON_FIXTURE_DOMAIN + canonical),
        )


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
            "fixture_only": True,
            "native_broker_executed": False,
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
            "fixture_only": True,
            "native_broker_executed": False,
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
        "fixture_only",
        "native_broker_executed",
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
        _require_bool(fixture["fixture_only"], True, "ERR_TASK065_NOT_FIXTURE")
        _require_bool(
            fixture["native_broker_executed"],
            False,
            "ERR_TASK065_NATIVE_BROKER_CLAIM",
        )
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
    "COMMON_INSTALLED_CONTRACT",
    "COMMON_INSTALLED_MODE",
    "COMMON_INSTALLED_VALIDATED_STATUS",
    "COMMON_INSTALLED_VALIDATION_MESSAGE_TYPE",
    "CommonInstalledDiscoveryFixtureConsumerPort",
    "CommonInstalledDiscoveryFixturePlan",
    "CommonInstalledDiscoveryFixtureValidation",
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
