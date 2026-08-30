"""TASK-061 connector source binding and activation boundary.

CA-B may publish one exact TASK-060 advisory Profile into the installer-selected
bridge, but it never enables the connector.  CA-C activation transactions are a
later unit and must consume this exact read-back evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from .montage_learning_bridge_migration import BridgeMigrationReadback
from .montage_learning_bridge_security import (
    BridgeSecurityAttestation,
    BridgeSecurityBackend,
    BridgeSecurityState,
    attest_bridge_security,
)
from .montage_learning_connector_readiness import (
    ConnectorReadinessEvidence,
    ProfileSourceBinding,
    publish_prebuilt_advisory_profile,
    validate_prebuilt_advisory_profile,
)
from .montage_learning_file_bridge import recover_current_profile
from .montage_learning_installation import (
    InstalledBridgeDiscovery,
    discover_installed_bridge,
)
from .montage_preference_source import (
    PromotedPreferenceSource,
    PromotedPreferenceSourceRead,
)
from .serialization import canonical_json_bytes, sha256_json


SOURCE_BINDING_SCHEMA_VERSION = "1.0.0"
SOURCE_BINDING_MESSAGE_TYPE = "BvpMontageLearningConnectorSourceBindingReadiness"
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BINDING_ID_RE = re.compile(r"^source-binding-[0-9a-f]{32}$")
_PLAN_SEAL = object()
_RESULT_SEAL = object()
_WINDOWS_REPARSE_POINT = 0x400
_MAX_PROFILE_BYTES = 4 * 1024 * 1024


class MontageLearningConnectorActivationError(ValueError):
    """Raised when CA-B source binding cannot remain fail-closed."""


@dataclass(frozen=True, slots=True)
class ConnectorSourceBindingPlan:
    binding_id: str
    target_install_instance_id: str
    target_descriptor_sha256: str
    target_owner_manifest_sha256: str
    migration_snapshot_readback_sha256: str
    preference_source_readback_sha256: str
    preference_envelope_sha256: str
    preference_profile_sha256: str
    preference_profile_id: str
    preference_profile_version: int
    task058_public_readiness_sha256: str
    security_attestation_id: str
    security_attestation_sha256: str
    security_owner_sid_sha256: str
    security_current_user_sid_sha256: str
    security_ancestor_count: int
    expected_previous_profile_sha256: str | None
    plan_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _PLAN_SEAL or _BINDING_ID_RE.fullmatch(self.binding_id) is None:
            raise MontageLearningConnectorActivationError("source binding plan is not sealed")
        for value in (
            self.target_descriptor_sha256,
            self.target_owner_manifest_sha256,
            self.migration_snapshot_readback_sha256,
            self.preference_source_readback_sha256,
            self.preference_envelope_sha256,
            self.preference_profile_sha256,
            self.task058_public_readiness_sha256,
            self.security_attestation_sha256,
            self.security_owner_sid_sha256,
            self.security_current_user_sid_sha256,
            self.plan_sha256,
        ):
            _require_sha(value)
        if self.expected_previous_profile_sha256 is not None:
            _require_sha(self.expected_previous_profile_sha256)
        if type(self.preference_profile_version) is not int or self.preference_profile_version < 1:
            raise MontageLearningConnectorActivationError("profile version is invalid")
        if type(self.security_ancestor_count) is not int or self.security_ancestor_count < 0:
            raise MontageLearningConnectorActivationError("security ancestor count is invalid")

    def confirmation(self) -> str:
        return f"BIND_MONTAGE_PROFILE_SOURCE:{self.binding_id}:{self.plan_sha256}"


@dataclass(frozen=True, slots=True)
class ConnectorSourceBindingReadiness:
    binding_id: str
    plan_sha256: str
    target_install_instance_id: str
    target_descriptor_sha256: str
    target_owner_manifest_sha256: str
    security_attestation_sha256: str
    migration_snapshot_readback_sha256: str
    preference_source_readback_sha256: str
    preference_envelope_sha256: str
    task058_public_readiness_sha256: str
    profile_id: str
    profile_version: int
    profile_sha256: str
    profile_publish_status: str
    binding_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _RESULT_SEAL:
            raise MontageLearningConnectorActivationError("source binding read-back is not sealed")
        body = self._body()
        if self.binding_sha256 != sha256_json(body):
            raise MontageLearningConnectorActivationError("source binding hash mismatch")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SOURCE_BINDING_SCHEMA_VERSION,
            "message_type": SOURCE_BINDING_MESSAGE_TYPE,
            "task_owner": "TASK-061",
            "binding_id": self.binding_id,
            "plan_sha256": self.plan_sha256,
            "target_install_instance_id": self.target_install_instance_id,
            "target_descriptor_sha256": self.target_descriptor_sha256,
            "target_owner_manifest_sha256": self.target_owner_manifest_sha256,
            "security_attestation_sha256": self.security_attestation_sha256,
            "migration_snapshot_readback_sha256": self.migration_snapshot_readback_sha256,
            "preference_source_readback_sha256": self.preference_source_readback_sha256,
            "preference_envelope_sha256": self.preference_envelope_sha256,
            "task058_public_readiness_sha256": self.task058_public_readiness_sha256,
            "task058_public_readiness_version": "1.0.0",
            "task058_public_v1_source_not_bound_baseline_validated": True,
            "private_v2_persistent_receipt_accepted": False,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "profile_sha256": self.profile_sha256,
            "profile_publish_status": self.profile_publish_status,
            "state": "SOURCE_BOUND_ACTIVATION_BLOCKED",
            "production_profile_source_bound": True,
            "profile_view_readback_verified": True,
            "real_adapter_e2e_verified": False,
            "connector_config_modified": False,
            "connector_enabled": False,
            "activation_authorized": False,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "binding_sha256": self.binding_sha256}


BindingHook = Callable[[str, Path], None]


def plan_connector_source_binding(
    target: InstalledBridgeDiscovery,
    *,
    migration_readback: BridgeMigrationReadback,
    preference_source: PromotedPreferenceSource,
    task058_public_readiness: ConnectorReadinessEvidence,
    security_attestation_id: str,
    security_backend: BridgeSecurityBackend | None = None,
    expected_previous_profile_sha256: str | None = None,
) -> ConnectorSourceBindingPlan:
    """Build an effect-zero exact plan for CA-B profile source binding."""

    current_target = _rediscover_exact(target)
    migration = _validate_migration_readback(migration_readback, current_target)
    source_read = _read_preference_source(preference_source)
    public_readiness = _validate_public_readiness(task058_public_readiness)
    security = _secure_attestation(
        current_target,
        attestation_id=security_attestation_id,
        backend=security_backend,
    )
    if expected_previous_profile_sha256 is not None:
        _require_sha(expected_previous_profile_sha256)
    body: dict[str, object] = {
        "schema_version": SOURCE_BINDING_SCHEMA_VERSION,
        "target_install_instance_id": current_target.descriptor.install_instance_id,
        "target_descriptor_sha256": current_target.descriptor.descriptor_sha256,
        "target_owner_manifest_sha256": current_target.owner_manifest_sha256,
        "migration_snapshot_readback_sha256": migration["snapshot_readback_sha256"],
        "preference_source_readback_sha256": source_read.readback_sha256,
        "preference_envelope_sha256": source_read.envelope_sha256,
        "preference_profile_sha256": source_read.active_payload_sha256,
        "preference_profile_id": source_read.profile_id,
        "preference_profile_version": source_read.profile_version,
        "task058_public_readiness_sha256": sha256_json(public_readiness),
        "security_attestation_id": security_attestation_id,
        "security_attestation_sha256": security.to_dict()["attestation_sha256"],
        "security_owner_sid_sha256": _require_sha(security.owner_sid_sha256),
        "security_current_user_sid_sha256": _require_sha(security.current_user_sid_sha256),
        "security_ancestor_count": security.ancestor_count,
        "expected_previous_profile_sha256": expected_previous_profile_sha256,
    }
    plan_sha = sha256_json(body)
    return ConnectorSourceBindingPlan(
        binding_id=f"source-binding-{plan_sha.removeprefix('sha256:')[:32]}",
        target_install_instance_id=str(body["target_install_instance_id"]),
        target_descriptor_sha256=str(body["target_descriptor_sha256"]),
        target_owner_manifest_sha256=str(body["target_owner_manifest_sha256"]),
        migration_snapshot_readback_sha256=str(body["migration_snapshot_readback_sha256"]),
        preference_source_readback_sha256=str(body["preference_source_readback_sha256"]),
        preference_envelope_sha256=str(body["preference_envelope_sha256"]),
        preference_profile_sha256=str(body["preference_profile_sha256"]),
        preference_profile_id=str(body["preference_profile_id"]),
        preference_profile_version=int(body["preference_profile_version"]),
        task058_public_readiness_sha256=str(body["task058_public_readiness_sha256"]),
        security_attestation_id=security_attestation_id,
        security_attestation_sha256=str(body["security_attestation_sha256"]),
        security_owner_sid_sha256=str(body["security_owner_sid_sha256"]),
        security_current_user_sid_sha256=str(body["security_current_user_sid_sha256"]),
        security_ancestor_count=int(body["security_ancestor_count"]),
        expected_previous_profile_sha256=expected_previous_profile_sha256,
        plan_sha256=plan_sha,
        _seal=_PLAN_SEAL,
    )


def execute_connector_source_binding(
    plan: ConnectorSourceBindingPlan,
    target: InstalledBridgeDiscovery,
    *,
    migration_readback: BridgeMigrationReadback,
    preference_source: PromotedPreferenceSource,
    task058_public_readiness: ConnectorReadinessEvidence,
    confirmation: str,
    security_backend: BridgeSecurityBackend | None = None,
    hook: BindingHook | None = None,
) -> ConnectorSourceBindingReadiness:
    """Publish/read back one exact advisory Profile; activation remains blocked."""

    if type(plan) is not ConnectorSourceBindingPlan or plan._seal is not _PLAN_SEAL:
        raise MontageLearningConnectorActivationError("source binding plan is not sealed")
    if confirmation != plan.confirmation():
        raise MontageLearningConnectorActivationError("exact source binding confirmation required")
    current_plan = plan_connector_source_binding(
        target,
        migration_readback=migration_readback,
        preference_source=preference_source,
        task058_public_readiness=task058_public_readiness,
        security_attestation_id=plan.security_attestation_id,
        security_backend=security_backend,
        expected_previous_profile_sha256=plan.expected_previous_profile_sha256,
    )
    if current_plan != plan:
        raise MontageLearningConnectorActivationError("source binding plan is stale")
    current_target = discover_installed_bridge(target.install_root)
    _require_target_matches(plan, current_target)
    source_read = _read_preference_source(preference_source)
    if source_read.readback_sha256 != plan.preference_source_readback_sha256:
        raise MontageLearningConnectorActivationError("preference source changed before publish")
    if hook is not None:
        hook("after_source_read", current_target.layout.current_profile)
    binding = ProfileSourceBinding.bound_verified_production(source_read)
    published = publish_prebuilt_advisory_profile(
        current_target.layout,
        source_read.envelope,
        source_binding=binding,
        expected_previous_profile_sha256=plan.expected_previous_profile_sha256,
    )
    if published.status not in {"PUBLISHED", "DUPLICATE"} or not published.production_profile_source_bound:
        raise MontageLearningConnectorActivationError("exact Profile publication did not complete")
    if hook is not None:
        hook("after_profile_publish", current_target.layout.current_profile)
    try:
        post_source = _read_preference_source(preference_source)
    except Exception as exc:
        raise MontageLearningConnectorActivationError(
            "preference source drifted after publication; activation remains blocked"
        ) from exc
    if post_source.readback_sha256 != plan.preference_source_readback_sha256:
        raise MontageLearningConnectorActivationError(
            "preference source drifted after publication; activation remains blocked"
        )
    recover_current_profile(current_target.layout)
    profile = _read_pinned_profile(current_target.layout.current_profile)
    if canonical_json_bytes(profile) != canonical_json_bytes(source_read.envelope):
        raise MontageLearningConnectorActivationError("Profile view read-back mismatch")
    final_target = discover_installed_bridge(target.install_root)
    _require_target_matches(plan, final_target)
    final_security = _secure_attestation(
        final_target,
        attestation_id=plan.security_attestation_id,
        backend=security_backend,
    )
    if final_security.to_dict()["attestation_sha256"] != plan.security_attestation_sha256:
        raise MontageLearningConnectorActivationError("bridge security identity drifted")
    result_body: dict[str, object] = {
        "schema_version": SOURCE_BINDING_SCHEMA_VERSION,
        "message_type": SOURCE_BINDING_MESSAGE_TYPE,
        "task_owner": "TASK-061",
        "binding_id": plan.binding_id,
        "plan_sha256": plan.plan_sha256,
        "target_install_instance_id": plan.target_install_instance_id,
        "target_descriptor_sha256": plan.target_descriptor_sha256,
        "target_owner_manifest_sha256": plan.target_owner_manifest_sha256,
        "security_attestation_sha256": str(final_security.to_dict()["attestation_sha256"]),
        "migration_snapshot_readback_sha256": plan.migration_snapshot_readback_sha256,
        "preference_source_readback_sha256": plan.preference_source_readback_sha256,
        "preference_envelope_sha256": plan.preference_envelope_sha256,
        "task058_public_readiness_sha256": plan.task058_public_readiness_sha256,
        "task058_public_readiness_version": "1.0.0",
        "task058_public_v1_source_not_bound_baseline_validated": True,
        "private_v2_persistent_receipt_accepted": False,
        "profile_id": plan.preference_profile_id,
        "profile_version": plan.preference_profile_version,
        "profile_sha256": plan.preference_profile_sha256,
        "profile_publish_status": "CURRENT_EXACT_PROFILE",
        "state": "SOURCE_BOUND_ACTIVATION_BLOCKED",
        "production_profile_source_bound": True,
        "profile_view_readback_verified": True,
        "real_adapter_e2e_verified": False,
        "connector_config_modified": False,
        "connector_enabled": False,
        "activation_authorized": False,
        "learning_adoption_authorized": False,
        "automatic_promotion_authorized": False,
        "timeline_mutation_authorized": False,
        "resolve_write_authorized": False,
        "external_effect_authorized": False,
    }
    return ConnectorSourceBindingReadiness(
        plan.binding_id,
        plan.plan_sha256,
        plan.target_install_instance_id,
        plan.target_descriptor_sha256,
        plan.target_owner_manifest_sha256,
        str(result_body["security_attestation_sha256"]),
        plan.migration_snapshot_readback_sha256,
        plan.preference_source_readback_sha256,
        plan.preference_envelope_sha256,
        plan.task058_public_readiness_sha256,
        plan.preference_profile_id,
        plan.preference_profile_version,
        plan.preference_profile_sha256,
        "CURRENT_EXACT_PROFILE",
        sha256_json(result_body),
        _RESULT_SEAL,
    )


def _validate_migration_readback(
    value: BridgeMigrationReadback,
    target: InstalledBridgeDiscovery,
) -> dict[str, object]:
    if type(value) is not BridgeMigrationReadback:
        raise MontageLearningConnectorActivationError("exact sealed migration read-back required")
    value.__post_init__()
    body = value.to_dict()
    receipt = body["receipt"]
    if (
        receipt["target_install_instance_id"] != target.descriptor.install_instance_id
        or receipt["target_descriptor_sha256"] != target.descriptor.descriptor_sha256
        or receipt["target_owner_manifest_sha256"] != target.owner_manifest_sha256
        or body["exact_snapshot_verified"] is not True
    ):
        raise MontageLearningConnectorActivationError("migration read-back target mismatch")
    return body


def _read_preference_source(source: PromotedPreferenceSource) -> PromotedPreferenceSourceRead:
    if type(source) is not PromotedPreferenceSource:
        raise MontageLearningConnectorActivationError("exact TASK-060 source port required")
    try:
        value = source.read_current()
        value.verify_current()
        return value
    except Exception as exc:
        raise MontageLearningConnectorActivationError("TASK-060 source read-back failed") from exc


def _validate_public_readiness(value: ConnectorReadinessEvidence) -> dict[str, object]:
    if type(value) is not ConnectorReadinessEvidence:
        raise MontageLearningConnectorActivationError("exact TASK-058 public v1 readiness required")
    body = value.to_dict()
    if (
        body["schema_version"] != "1.0.0"
        or body["message_type"] != "BvpMontageLearningConnectorReadiness"
        or body["task_id"] != "TASK-058"
        or body["bridge_state"] != "AVAILABLE"
        or body["import_state"] != "OBSERVATION_RECORDED"
        or body["adapter_state"] != "LOAD_PROFILE_PASS"
        or body["profile_state"] != "SOURCE_NOT_BOUND"
        or body["production_profile_source_bound"] is not False
        or body["adapter_contract_e2e_pass"] is not True
        or body["default_skill_config_unchanged"] is not True
        or body["connector_enabled"] is not False
        or body["activation_authorized"] is not False
    ):
        raise MontageLearningConnectorActivationError("TASK-058 public v1 baseline is not exact")
    return body


def _secure_attestation(
    target: InstalledBridgeDiscovery,
    *,
    attestation_id: str,
    backend: BridgeSecurityBackend | None,
) -> BridgeSecurityAttestation:
    result = attest_bridge_security(target.layout.root, attestation_id=attestation_id, backend=backend)
    if result.state is not BridgeSecurityState.SECURE:
        raise MontageLearningConnectorActivationError("bridge security is not SECURE")
    return result


def _rediscover_exact(target: InstalledBridgeDiscovery) -> InstalledBridgeDiscovery:
    current = discover_installed_bridge(target.install_root)
    if current.public_receipt() != target.public_receipt():
        raise MontageLearningConnectorActivationError("installed bridge discovery drifted")
    return current


def _require_target_matches(plan: ConnectorSourceBindingPlan, target: InstalledBridgeDiscovery) -> None:
    if (
        target.descriptor.install_instance_id != plan.target_install_instance_id
        or target.descriptor.descriptor_sha256 != plan.target_descriptor_sha256
        or target.owner_manifest_sha256 != plan.target_owner_manifest_sha256
    ):
        raise MontageLearningConnectorActivationError("installed bridge identity mismatch")


def _read_pinned_profile(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise MontageLearningConnectorActivationError("Profile view must not be a symlink")
    try:
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or getattr(before, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
                or getattr(before, "st_nlink", 1) != 1
                or not 1 <= before.st_size <= _MAX_PROFILE_BYTES
            ):
                raise MontageLearningConnectorActivationError("Profile view identity is unsafe")
            data = handle.read(_MAX_PROFILE_BYTES + 1)
            after = os.fstat(handle.fileno())
        current = os.lstat(path)
    except OSError as exc:
        raise MontageLearningConnectorActivationError("Profile view read failed") from exc
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if len(data) > _MAX_PROFILE_BYTES or identity(before) != identity(after) or identity(after) != identity(current):
        raise MontageLearningConnectorActivationError("Profile view changed during read")
    try:
        value = json.loads(data)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningConnectorActivationError("Profile view JSON is invalid") from exc
    return validate_prebuilt_advisory_profile(value)


def _require_sha(value: str | None) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningConnectorActivationError("required sha256 coordinate is invalid")
    return value


__all__ = [
    "ConnectorSourceBindingPlan",
    "ConnectorSourceBindingReadiness",
    "MontageLearningConnectorActivationError",
    "execute_connector_source_binding",
    "plan_connector_source_binding",
]
