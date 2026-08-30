"""TASK-061 connector source binding and activation boundary.

CA-B may publish one exact TASK-060 advisory Profile into the installer-selected
bridge, but it never enables the connector.  CA-C activation transactions are a
later unit and must consume this exact read-back evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
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
_HUMAN_EVIDENCE_SEAL = object()
_ADAPTER_E2E_SEAL = object()
_TRANSACTION_SEAL = object()
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


@dataclass(frozen=True, slots=True)
class HumanActivationEvidence:
    evidence_id: str
    action: str
    target_install_instance_id: str
    source_binding_sha256: str
    issued_at: str
    expires_at: str
    evidence_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _HUMAN_EVIDENCE_SEAL:
            raise MontageLearningConnectorActivationError("Human evidence is not sealed")
        if self.action not in {"ACTIVATE", "DEACTIVATE"}:
            raise MontageLearningConnectorActivationError("Human action is invalid")
        issued = _utc(self.issued_at)
        expires = _utc(self.expires_at)
        if not issued < expires <= issued + timedelta(hours=24):
            raise MontageLearningConnectorActivationError("Human evidence expiry is invalid")
        if self.evidence_sha256 != sha256_json(self._body()):
            raise MontageLearningConnectorActivationError("Human evidence hash mismatch")

    def _body(self) -> dict[str, object]:
        return {
            "record_version": "1.0.0",
            "record_type": "BvpMontageLearningHumanActivationEvidence",
            "task_owner": "TASK-061",
            "evidence_id": self.evidence_id,
            "action": self.action,
            "target_install_instance_id": self.target_install_instance_id,
            "source_binding_sha256": self.source_binding_sha256,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "one_shot": True,
            "private_data_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "evidence_sha256": self.evidence_sha256}


@dataclass(frozen=True, slots=True)
class InstalledAdapterE2EReadback:
    target_install_instance_id: str
    source_binding_sha256: str
    connector_status_sha256: str
    publish_learning_receipt_sha256: str
    profile_readback_sha256: str
    synthetic_fixture: bool
    adapter_e2e_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _ADAPTER_E2E_SEAL:
            raise MontageLearningConnectorActivationError("adapter E2E read-back is not sealed")
        for value in (
            self.source_binding_sha256, self.connector_status_sha256,
            self.publish_learning_receipt_sha256, self.profile_readback_sha256,
        ):
            _require_sha(value)
        if type(self.synthetic_fixture) is not bool:
            raise MontageLearningConnectorActivationError("adapter E2E fixture flag is invalid")
        if self.adapter_e2e_sha256 != sha256_json(self._body()):
            raise MontageLearningConnectorActivationError("adapter E2E hash mismatch")

    @property
    def real_installed_verified(self) -> bool:
        return not self.synthetic_fixture

    def _body(self) -> dict[str, object]:
        return {
            "record_version": "1.0.0",
            "record_type": "BvpMontageLearningInstalledAdapterE2EReadback",
            "task_owner": "TASK-061",
            "target_install_instance_id": self.target_install_instance_id,
            "source_binding_sha256": self.source_binding_sha256,
            "connector_status_sha256": self.connector_status_sha256,
            "publish_learning_receipt_sha256": self.publish_learning_receipt_sha256,
            "profile_readback_sha256": self.profile_readback_sha256,
            "execution_mode": "SYNTHETIC_PUBLIC_SAFE_FIXTURE" if self.synthetic_fixture else "REAL_INSTALLED_PUBLIC_SAFE",
            "synthetic_fixture": self.synthetic_fixture,
            "owner_private_data_used": False,
            "raw_transcript_used": False,
            "secret_used": False,
            "timeline_mutated": False,
            "resolve_written": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "adapter_e2e_sha256": self.adapter_e2e_sha256}


@dataclass(frozen=True, slots=True)
class ConnectorActivationTransactionReceipt:
    transaction_id: str
    target_install_instance_id: str
    source_binding_sha256: str
    human_evidence_sha256: str
    adapter_e2e_sha256: str | None
    revision: int
    enabled: bool
    action: str
    history_sha256: str
    config_readback_sha256: str
    transaction_sha256: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _TRANSACTION_SEAL:
            raise MontageLearningConnectorActivationError("activation receipt is not sealed")
        if self.transaction_sha256 != sha256_json(self._body()):
            raise MontageLearningConnectorActivationError("activation receipt hash mismatch")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningConnectorActivationTransactionReceipt",
            "task_owner": "TASK-061",
            "transaction_id": self.transaction_id,
            "target_install_instance_id": self.target_install_instance_id,
            "source_binding_sha256": self.source_binding_sha256,
            "human_evidence_sha256": self.human_evidence_sha256,
            "adapter_e2e_sha256": self.adapter_e2e_sha256,
            "revision": self.revision,
            "enabled": self.enabled,
            "action": self.action,
            "state": "ENABLED" if self.enabled else "DISABLED",
            "history_sha256": self.history_sha256,
            "config_readback_sha256": self.config_readback_sha256,
            "one_shot_human_evidence_consumed": True,
            "repository_default_enabled": False,
            "external_skill_config_modified": False,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "transaction_sha256": self.transaction_sha256}


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


def issue_human_activation_evidence(
    source_binding: ConnectorSourceBindingReadiness,
    *,
    action: str,
    evidence_id: str,
    issued_at: str,
    expires_at: str,
    confirmation: str,
) -> HumanActivationEvidence:
    """Mint one in-memory Human action only from the exact visible confirmation."""

    _validate_source_binding_readiness(source_binding)
    if action not in {"ACTIVATE", "DEACTIVATE"}:
        raise MontageLearningConnectorActivationError("Human action is invalid")
    if type(evidence_id) is not str or not evidence_id.startswith("human-action-"):
        raise MontageLearningConnectorActivationError("Human evidence id is invalid")
    expected = (
        f"{action}_MONTAGE_CONNECTOR:"
        f"{source_binding.target_install_instance_id}:"
        f"{source_binding.binding_sha256}"
    )
    if confirmation != expected:
        raise MontageLearningConnectorActivationError("exact Human confirmation required")
    body: dict[str, object] = {
        "record_version": "1.0.0",
        "record_type": "BvpMontageLearningHumanActivationEvidence",
        "task_owner": "TASK-061",
        "evidence_id": evidence_id,
        "action": action,
        "target_install_instance_id": source_binding.target_install_instance_id,
        "source_binding_sha256": source_binding.binding_sha256,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "one_shot": True,
        "private_data_authorized": False,
        "timeline_mutation_authorized": False,
        "resolve_write_authorized": False,
    }
    return HumanActivationEvidence(
        evidence_id, action, source_binding.target_install_instance_id,
        source_binding.binding_sha256, issued_at, expires_at,
        sha256_json(body), _HUMAN_EVIDENCE_SEAL,
    )


def admit_adapter_e2e_observation(
    source_binding: ConnectorSourceBindingReadiness,
    *,
    connector_status_sha256: str,
    publish_learning_receipt_sha256: str,
    profile_readback_sha256: str,
    synthetic_fixture: bool,
) -> InstalledAdapterE2EReadback:
    """Seal public-safe adapter observations; synthetic evidence cannot activate."""

    _validate_source_binding_readiness(source_binding)
    for value in (
        connector_status_sha256, publish_learning_receipt_sha256,
        profile_readback_sha256,
    ):
        _require_sha(value)
    if type(synthetic_fixture) is not bool:
        raise MontageLearningConnectorActivationError("synthetic fixture flag is invalid")
    if synthetic_fixture is not True:
        raise MontageLearningConnectorActivationError(
            "real installed adapter E2E admission gate is not available in this implementation candidate"
        )
    body: dict[str, object] = {
        "record_version": "1.0.0",
        "record_type": "BvpMontageLearningInstalledAdapterE2EReadback",
        "task_owner": "TASK-061",
        "target_install_instance_id": source_binding.target_install_instance_id,
        "source_binding_sha256": source_binding.binding_sha256,
        "connector_status_sha256": connector_status_sha256,
        "publish_learning_receipt_sha256": publish_learning_receipt_sha256,
        "profile_readback_sha256": profile_readback_sha256,
        "execution_mode": "SYNTHETIC_PUBLIC_SAFE_FIXTURE" if synthetic_fixture else "REAL_INSTALLED_PUBLIC_SAFE",
        "synthetic_fixture": synthetic_fixture,
        "owner_private_data_used": False,
        "raw_transcript_used": False,
        "secret_used": False,
        "timeline_mutated": False,
        "resolve_written": False,
    }
    return InstalledAdapterE2EReadback(
        source_binding.target_install_instance_id,
        source_binding.binding_sha256,
        connector_status_sha256,
        publish_learning_receipt_sha256,
        profile_readback_sha256,
        synthetic_fixture,
        sha256_json(body),
        _ADAPTER_E2E_SEAL,
    )


def read_connector_activation_config(
    target: InstalledBridgeDiscovery,
) -> dict[str, object]:
    """Read exact BVP-owned config; absence is the immutable disabled default."""

    current = _rediscover_exact(target)
    path = current.layout.state / "connector-activation-history.json"
    if not path.exists() and not path.is_symlink():
        return _default_config(current)
    return _read_config(path, current)


def apply_connector_activation_transaction(
    target: InstalledBridgeDiscovery,
    source_binding: ConnectorSourceBindingReadiness,
    human_evidence: HumanActivationEvidence,
    *,
    expected_revision: int,
    now: str,
    security_attestation_id: str,
    security_backend: BridgeSecurityBackend | None = None,
    adapter_e2e: InstalledAdapterE2EReadback | None = None,
    hook: BindingHook | None = None,
) -> ConnectorActivationTransactionReceipt:
    """Atomically append ACTIVATE/DEACTIVATE history in the BVP-owned config."""

    current_target = _rediscover_exact(target)
    initial_security = _secure_attestation(
        current_target,
        attestation_id=security_attestation_id,
        backend=security_backend,
    )
    _validate_source_binding_readiness(source_binding)
    human_evidence.__post_init__()
    if (
        source_binding.target_install_instance_id != current_target.descriptor.install_instance_id
        or human_evidence.target_install_instance_id != current_target.descriptor.install_instance_id
        or human_evidence.source_binding_sha256 != source_binding.binding_sha256
    ):
        raise MontageLearningConnectorActivationError("activation identity mismatch")
    current_time = _utc(now)
    if not _utc(human_evidence.issued_at) <= current_time < _utc(human_evidence.expires_at):
        raise MontageLearningConnectorActivationError("Human evidence is expired or not current")
    desired_enabled = human_evidence.action == "ACTIVATE"
    adapter_sha: str | None = None
    if desired_enabled:
        if type(adapter_e2e) is not InstalledAdapterE2EReadback:
            raise MontageLearningConnectorActivationError("real installed adapter E2E is required")
        adapter_e2e.__post_init__()
        if (
            not adapter_e2e.real_installed_verified
            or adapter_e2e.target_install_instance_id != current_target.descriptor.install_instance_id
            or adapter_e2e.source_binding_sha256 != source_binding.binding_sha256
        ):
            raise MontageLearningConnectorActivationError("real installed adapter E2E is required")
        adapter_sha = adapter_e2e.adapter_e2e_sha256
    elif adapter_e2e is not None:
        raise MontageLearningConnectorActivationError("deactivation must not depend on adapter E2E")
    if type(expected_revision) is not int or expected_revision < 0:
        raise MontageLearningConnectorActivationError("expected revision is invalid")

    config_path = current_target.layout.state / "connector-activation-history.json"
    config_ancestor_identities = _json_ancestor_chain(config_path)
    if hook is not None:
        hook("before_config_lock", config_path)
    _require_json_ancestors_unchanged(config_path, config_ancestor_identities)
    with exclusive_file_update_lock(config_path):
        _require_json_ancestors_unchanged(config_path, config_ancestor_identities)
        config = read_connector_activation_config(current_target)
        events = list(config["events"])
        if events and events[-1]["human_evidence_sha256"] == human_evidence.evidence_sha256:
            if events[-1]["action"] != human_evidence.action:
                raise MontageLearningConnectorActivationError("Human evidence collision")
            return _transaction_receipt(config, events[-1])
        if any(event["human_evidence_sha256"] == human_evidence.evidence_sha256 for event in events):
            raise MontageLearningConnectorActivationError("one-shot Human evidence was already consumed")
        if config["revision"] != expected_revision:
            raise MontageLearningConnectorActivationError("activation config CAS mismatch")
        previous_event_sha = None if not events else events[-1]["event_sha256"]
        revision = expected_revision + 1
        event_body: dict[str, object] = {
            "revision": revision,
            "action": human_evidence.action,
            "enabled": desired_enabled,
            "source_binding_sha256": source_binding.binding_sha256,
            "human_evidence_sha256": human_evidence.evidence_sha256,
            "adapter_e2e_sha256": adapter_sha,
            "occurred_at": now,
            "previous_event_sha256": previous_event_sha,
        }
        event = {**event_body, "event_sha256": sha256_json(event_body)}
        events.append(event)
        history_sha = sha256_json(events)
        config_body: dict[str, object] = {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningConnectorActivationConfigHistory",
            "task_owner": "TASK-061",
            "target_install_instance_id": current_target.descriptor.install_instance_id,
            "target_descriptor_sha256": current_target.descriptor.descriptor_sha256,
            "target_owner_manifest_sha256": current_target.owner_manifest_sha256,
            "revision": revision,
            "enabled": desired_enabled,
            "current_source_binding_sha256": source_binding.binding_sha256,
            "events": events,
            "history_sha256": history_sha,
            "repository_default_enabled": False,
            "external_skill_config_modified": False,
        }
        document = {**config_body, "config_sha256": sha256_json(config_body)}
        if hook is not None:
            hook("before_config_replace", config_path)
        _require_json_ancestors_unchanged(config_path, config_ancestor_identities)
        AtomicJsonWriter.write(config_path, document, validator=lambda value: _validate_config(value, current_target))
        if hook is not None:
            hook("after_config_replace", config_path)
        _require_json_ancestors_unchanged(config_path, config_ancestor_identities)
        readback = _read_config(config_path, current_target)
        if readback != document:
            raise MontageLearningConnectorActivationError("activation config read-back mismatch")
        final_target = discover_installed_bridge(current_target.install_root)
        if final_target.public_receipt() != current_target.public_receipt():
            raise MontageLearningConnectorActivationError("installed bridge drifted during config write")
        final_security = _secure_attestation(
            final_target,
            attestation_id=security_attestation_id,
            backend=security_backend,
        )
        if (
            final_security.to_dict()["attestation_sha256"]
            != initial_security.to_dict()["attestation_sha256"]
        ):
            raise MontageLearningConnectorActivationError("bridge security identity drifted during config write")
        return _transaction_receipt(readback, event)


def _default_config(target: InstalledBridgeDiscovery) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningConnectorActivationConfigHistory",
        "task_owner": "TASK-061",
        "target_install_instance_id": target.descriptor.install_instance_id,
        "target_descriptor_sha256": target.descriptor.descriptor_sha256,
        "target_owner_manifest_sha256": target.owner_manifest_sha256,
        "revision": 0,
        "enabled": False,
        "current_source_binding_sha256": None,
        "events": [],
        "history_sha256": sha256_json([]),
        "repository_default_enabled": False,
        "external_skill_config_modified": False,
    }
    return {**body, "config_sha256": sha256_json(body)}


def _read_config(path: Path, target: InstalledBridgeDiscovery) -> dict[str, object]:
    value = _read_pinned_json(path, max_bytes=4 * 1024 * 1024)
    _validate_config(value, target)
    return value


def _validate_config(value: object, target: InstalledBridgeDiscovery) -> None:
    fields = {
        "schema_version", "message_type", "task_owner", "target_install_instance_id",
        "target_descriptor_sha256", "target_owner_manifest_sha256", "revision",
        "enabled", "current_source_binding_sha256", "events", "history_sha256",
        "repository_default_enabled", "external_skill_config_modified", "config_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise MontageLearningConnectorActivationError("activation config fields mismatch")
    body = dict(value)
    supplied = body.pop("config_sha256")
    if (
        value["schema_version"] != "1.0.0"
        or value["message_type"] != "BvpMontageLearningConnectorActivationConfigHistory"
        or value["task_owner"] != "TASK-061"
        or value["target_install_instance_id"] != target.descriptor.install_instance_id
        or value["target_descriptor_sha256"] != target.descriptor.descriptor_sha256
        or value["target_owner_manifest_sha256"] != target.owner_manifest_sha256
        or value["repository_default_enabled"] is not False
        or value["external_skill_config_modified"] is not False
        or supplied != sha256_json(body)
    ):
        raise MontageLearningConnectorActivationError("activation config identity mismatch")
    revision = value["revision"]
    events = value["events"]
    if type(revision) is not int or revision < 0 or type(events) is not list or len(events) != revision:
        raise MontageLearningConnectorActivationError("activation history revision mismatch")
    previous = None
    for index, event in enumerate(events, 1):
        event_fields = {
            "revision", "action", "enabled", "source_binding_sha256",
            "human_evidence_sha256", "adapter_e2e_sha256", "occurred_at",
            "previous_event_sha256", "event_sha256",
        }
        if type(event) is not dict or set(event) != event_fields:
            raise MontageLearningConnectorActivationError("activation event fields mismatch")
        event_body = dict(event)
        event_sha = event_body.pop("event_sha256")
        if (
            event["revision"] != index
            or event["action"] not in {"ACTIVATE", "DEACTIVATE"}
            or event["enabled"] is not (event["action"] == "ACTIVATE")
            or event["previous_event_sha256"] != previous
            or event_sha != sha256_json(event_body)
        ):
            raise MontageLearningConnectorActivationError("activation event chain mismatch")
        _require_sha(event["source_binding_sha256"])
        _require_sha(event["human_evidence_sha256"])
        if event["action"] == "ACTIVATE":
            _require_sha(event["adapter_e2e_sha256"])
        elif event["adapter_e2e_sha256"] is not None:
            raise MontageLearningConnectorActivationError("deactivation adapter evidence mismatch")
        _utc(event["occurred_at"])
        previous = event_sha
    if value["history_sha256"] != sha256_json(events):
        raise MontageLearningConnectorActivationError("activation history hash mismatch")
    expected_enabled = False if not events else events[-1]["enabled"]
    expected_binding = None if not events else events[-1]["source_binding_sha256"]
    if value["enabled"] is not expected_enabled or value["current_source_binding_sha256"] != expected_binding:
        raise MontageLearningConnectorActivationError("activation config projection mismatch")


def _transaction_receipt(
    config: dict[str, object],
    event: dict[str, object],
) -> ConnectorActivationTransactionReceipt:
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningConnectorActivationTransactionReceipt",
        "task_owner": "TASK-061",
        "transaction_id": f"activation-{str(event['human_evidence_sha256']).removeprefix('sha256:')[:32]}",
        "target_install_instance_id": config["target_install_instance_id"],
        "source_binding_sha256": event["source_binding_sha256"],
        "human_evidence_sha256": event["human_evidence_sha256"],
        "adapter_e2e_sha256": event["adapter_e2e_sha256"],
        "revision": event["revision"],
        "enabled": event["enabled"],
        "action": event["action"],
        "state": "ENABLED" if event["enabled"] else "DISABLED",
        "history_sha256": config["history_sha256"],
        "config_readback_sha256": config["config_sha256"],
        "one_shot_human_evidence_consumed": True,
        "repository_default_enabled": False,
        "external_skill_config_modified": False,
        "learning_adoption_authorized": False,
        "automatic_promotion_authorized": False,
        "timeline_mutation_authorized": False,
        "resolve_write_authorized": False,
    }
    return ConnectorActivationTransactionReceipt(
        str(body["transaction_id"]), str(body["target_install_instance_id"]),
        str(body["source_binding_sha256"]), str(body["human_evidence_sha256"]),
        None if body["adapter_e2e_sha256"] is None else str(body["adapter_e2e_sha256"]),
        int(body["revision"]), bool(body["enabled"]), str(body["action"]),
        str(body["history_sha256"]), str(body["config_readback_sha256"]),
        sha256_json(body), _TRANSACTION_SEAL,
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


def _validate_source_binding_readiness(
    value: ConnectorSourceBindingReadiness,
) -> dict[str, object]:
    if type(value) is not ConnectorSourceBindingReadiness:
        raise MontageLearningConnectorActivationError("exact sealed source binding readiness required")
    value.__post_init__()
    body = value.to_dict()
    if (
        body["state"] != "SOURCE_BOUND_ACTIVATION_BLOCKED"
        or body["production_profile_source_bound"] is not True
        or body["profile_view_readback_verified"] is not True
        or body["real_adapter_e2e_verified"] is not False
        or body["connector_config_modified"] is not False
        or body["connector_enabled"] is not False
        or body["activation_authorized"] is not False
    ):
        raise MontageLearningConnectorActivationError("source binding authority boundary mismatch")
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
    return validate_prebuilt_advisory_profile(
        _read_pinned_json(path, max_bytes=_MAX_PROFILE_BYTES)
    )


def _read_pinned_json(path: Path, *, max_bytes: int) -> dict[str, object]:
    ancestors = _json_ancestor_chain(path)
    if path.is_symlink():
        raise MontageLearningConnectorActivationError("JSON path must not be a symlink")
    try:
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or getattr(before, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
                or getattr(before, "st_nlink", 1) != 1
                or not 1 <= before.st_size <= max_bytes
            ):
                raise MontageLearningConnectorActivationError("JSON path identity is unsafe")
            data = handle.read(max_bytes + 1)
            after = os.fstat(handle.fileno())
        current = os.lstat(path)
    except OSError as exc:
        raise MontageLearningConnectorActivationError("JSON read failed") from exc
    identity = lambda info: (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        getattr(info, "st_file_attributes", 0),
        getattr(info, "st_nlink", 1),
    )
    current_is_safe = (
        stat.S_ISREG(current.st_mode)
        and not getattr(current, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
        and getattr(current, "st_nlink", 1) == 1
    )
    if (
        len(data) > max_bytes
        or not current_is_safe
        or identity(before) != identity(after)
        or identity(after) != identity(current)
    ):
        raise MontageLearningConnectorActivationError("JSON path changed during read")
    _require_json_ancestors_unchanged(path, ancestors)
    try:
        value = json.loads(data)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MontageLearningConnectorActivationError("JSON is invalid") from exc
    if type(value) is not dict:
        raise MontageLearningConnectorActivationError("JSON must be an object")
    return value


def _json_ancestor_chain(path: Path) -> tuple[tuple[str, int, int, int], ...]:
    identities: list[tuple[str, int, int, int]] = []
    current = path.parent
    try:
        while True:
            info = os.lstat(current)
            if (
                not stat.S_ISDIR(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
            ):
                raise MontageLearningConnectorActivationError(
                    "JSON ancestor identity is unsafe"
                )
            identities.append(
                (str(current), int(info.st_dev), int(info.st_ino), int(info.st_mode))
            )
            if current.parent == current:
                break
            current = current.parent
    except OSError as exc:
        raise MontageLearningConnectorActivationError(
            "JSON ancestor identity cannot be inspected"
        ) from exc
    return tuple(identities)


def _require_json_ancestors_unchanged(
    path: Path,
    expected: tuple[tuple[str, int, int, int], ...],
) -> None:
    if _json_ancestor_chain(path) != expected:
        raise MontageLearningConnectorActivationError(
            "JSON ancestor identity changed"
        )


def _utc(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise MontageLearningConnectorActivationError("UTC timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MontageLearningConnectorActivationError("UTC timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise MontageLearningConnectorActivationError("UTC timestamp is invalid")
    return parsed.astimezone(timezone.utc)


def _require_sha(value: str | None) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningConnectorActivationError("required sha256 coordinate is invalid")
    return value


__all__ = [
    "ConnectorActivationTransactionReceipt",
    "ConnectorSourceBindingPlan",
    "ConnectorSourceBindingReadiness",
    "HumanActivationEvidence",
    "InstalledAdapterE2EReadback",
    "MontageLearningConnectorActivationError",
    "admit_adapter_e2e_observation",
    "apply_connector_activation_transaction",
    "execute_connector_source_binding",
    "issue_human_activation_evidence",
    "plan_connector_source_binding",
    "read_connector_activation_config",
]
