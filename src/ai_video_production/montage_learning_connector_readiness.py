"""TASK-058 immutable advisory Profile transport and readiness evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import re
from typing import Any, Mapping

from .montage_learning_file_bridge import (
    BridgeLayout,
    load_bridge_owner,
    publish_current_profile,
)
from .serialization import sha256_json


_BINDING_TOKEN = object()
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_CONTEXT_MARKER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:transcript|password|secret|api[_ ]key|access[_ ]token)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_ALLOWED_BRIDGE_STATES = frozenset(
    {"NOT_PROVISIONED", "OWNERSHIP_UNVERIFIED", "AVAILABLE"}
)
_ALLOWED_IMPORT_STATES = frozenset(
    {
        "NO_DELIVERY",
        "PENDING",
        "OBSERVATION_RECORDED",
        "EXACT_ACCEPTED",
        "DUPLICATE",
        "REJECTED",
        "RECOVERY_REQUIRED",
    }
)
_ALLOWED_PROFILE_STATES = frozenset(
    {"SOURCE_NOT_BOUND", "PUBLISHED", "LOAD_PASS", "STALE", "INVALID"}
)
_ALLOWED_ADAPTER_STATES = frozenset(
    {
        "NOT_RUN",
        "CONNECTOR_READY",
        "PUBLISH_STAGED",
        "MATCHING_RECEIPT_PASS",
        "LOAD_PROFILE_PASS",
        "FAIL",
    }
)
_DELIVERY_FIELDS = {
    "schema_version",
    "message_type",
    "contract_profile",
    "profile_contract",
    "profile_id",
    "profile_version",
    "owner_scope_hash",
    "source_record_count",
    "profile_sha256",
    "advisory_only",
    "canonical_timeline",
    "auto_apply_authorized",
    "payload",
}
_PREFERENCE_FIELDS = {
    "preference_id",
    "decision",
    "target",
    "contexts",
    "confidence",
    "confirmation_count",
    "reason_codes",
    "ranking_bias",
}
_READINESS_COMPONENT_PREDICATES = {
    "BRIDGE_ROOT_READY": (
        "OWNER_IDENTITY", "WINDOWS_DACL", "NO_REPARSE", "ANCESTOR_IDENTITY",
        "LAYOUT_COMPLETE", "MIGRATION_TERMINAL",
    ),
    "GENERIC_INTAKE_READY": (
        "A_AUTHORITY_CORE", "A_GENERIC_JOURNAL_RECOVERY",
        "DUPLICATE_REVISION_INVARIANT",
        "MANIFEST_CURRENTNESS_ROLLBACK_REJECTED", "IMPORTER_CLAIM_RECOVERY",
        "GENERIC_E2E",
    ),
    "EXACT_ADMISSION_READY": (
        "P1CB_REVALIDATION", "LEDGER_ANCHOR_MARKER_READBACK",
        "PUBLIC_V2_RECEIPT", "EXACT_E2E",
    ),
    "RECEIPT_CORRELATION_READY": (
        "TRUSTED_A_READBACK", "GENERIC_COMMIT_DOMAIN",
        "IMMUTABLE_OUTER_RECEIPT_IDENTITY", "OUTER_RECEIPT_EXACT_MATCH",
        "FORGED_RECEIPT_REJECTED", "LEGACY_STATUS_NON_AUTHORITY",
    ),
    "PROFILE_TRANSPORT_READY": (
        "PRODUCTION_SOURCE_BOUND", "IMMUTABLE_PAYLOAD", "POINTER_CAS_READBACK",
        "V1_VIEW_BYTE_MATCH", "SKILL_LOAD_PROFILE_E2E",
    ),
    "CONNECTOR_E2E_READY": (
        "DISABLED_DEFAULT", "LEGACY_SAFE", "NO_TIMELINE_RESOLVE_EFFECT",
        "NO_AUTOMATIC_PROMOTION", "PACKAGE_SCHEMA_IDENTITY",
    ),
}
_COMPONENT_STATES = frozenset({"PASS", "FAIL", "NOT_RUN", "SOURCE_NOT_BOUND"})
_PREDICATE_STATES = frozenset({"PASS", "FAIL", "NOT_RUN"})
_EVALUATION_MODES = frozenset({"STATUS_ONLY", "FULL_E2E"})
_OVERALL_STATES = frozenset(
    {"DISABLED", "SOURCE_NOT_BOUND", "BLOCKED"}
)
_BRIDGE_SECURITY_MODEL = "COOPERATIVE_SAME_USER_WINDOWS_DACL"
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class MontageLearningConnectorReadinessError(ValueError):
    """Raised when Profile transport or readiness claims are invalid."""


class ProfileSourceBinding:
    """Sealed capability separating fixture compatibility from production source."""

    __slots__ = (
        "source_id", "production_profile_source_bound", "isolated_fixture",
        "envelope_sha256",
    )

    def __init__(
        self,
        *,
        source_id: str | None,
        production_profile_source_bound: bool,
        isolated_fixture: bool,
        envelope_sha256: str | None,
        _token: object | None = None,
    ) -> None:
        if _token is not _BINDING_TOKEN:
            raise TypeError("ProfileSourceBinding must use a sealed constructor")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(
            self,
            "production_profile_source_bound",
            production_profile_source_bound,
        )
        object.__setattr__(self, "isolated_fixture", isolated_fixture)
        object.__setattr__(self, "envelope_sha256", envelope_sha256)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ProfileSourceBinding is immutable")

    @classmethod
    def unbound_production(cls) -> "ProfileSourceBinding":
        return cls(
            source_id=None,
            production_profile_source_bound=False,
            isolated_fixture=False,
            envelope_sha256=None,
            _token=_BINDING_TOKEN,
        )

    @classmethod
    def bound_isolated_fixture(
        cls,
        *,
        source_id: str = "canonical-prebuilt-advisory-fixture",
    ) -> "ProfileSourceBinding":
        _require_id(source_id, "source_id")
        return cls(
            source_id=source_id,
            production_profile_source_bound=False,
            isolated_fixture=True,
            envelope_sha256=None,
            _token=_BINDING_TOKEN,
        )

    @classmethod
    def bound_verified_production(cls, source_read: object) -> "ProfileSourceBinding":
        """Mint the production capability only from an exact TASK-060 read-back."""

        from .montage_preference_source import PromotedPreferenceSourceRead

        if (
            type(source_read) is not PromotedPreferenceSourceRead
            or source_read.production_source_bound is not True
        ):
            raise TypeError("exact verified TASK-060 production source read-back is required")
        source_read.verify_current()
        if source_read.to_dict()["exact_current_source_verified"] is not True:
            raise TypeError("exact verified TASK-060 production source read-back is required")
        _require_id(source_read.source_id, "source_id")
        return cls(
            source_id=source_read.source_id,
            production_profile_source_bound=True,
            isolated_fixture=False,
            envelope_sha256=source_read.envelope_sha256,
            _token=_BINDING_TOKEN,
        )


@dataclass(frozen=True, slots=True)
class ProfilePublishResult:
    status: str
    profile_id: str | None
    profile_sha256: str | None
    written: bool
    production_profile_source_bound: bool
    semantic_projection_generated: bool = False
    timeline_mutation_authorized: bool = False
    resolve_write_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "written": self.written,
            "production_profile_source_bound": self.production_profile_source_bound,
            "semantic_projection_generated": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class ConnectorReadinessEvidence:
    bridge_state: str
    import_state: str
    profile_state: str
    adapter_state: str
    production_profile_source_bound: bool
    adapter_contract_e2e_pass: bool
    default_skill_config_unchanged: bool
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field, allowed in (
            ("bridge_state", _ALLOWED_BRIDGE_STATES),
            ("import_state", _ALLOWED_IMPORT_STATES),
            ("profile_state", _ALLOWED_PROFILE_STATES),
            ("adapter_state", _ALLOWED_ADAPTER_STATES),
        ):
            value = getattr(self, field)
            if type(value) is not str or value not in allowed:
                raise MontageLearningConnectorReadinessError(
                    f"{field} is invalid"
                )
        for field in (
            "production_profile_source_bound",
            "adapter_contract_e2e_pass",
            "default_skill_config_unchanged",
        ):
            if type(getattr(self, field)) is not bool:
                raise MontageLearningConnectorReadinessError(
                    f"{field} must be a built-in bool"
                )
        if self.production_profile_source_bound is not False:
            raise MontageLearningConnectorReadinessError(
                "production profile source must be exactly false (SOURCE_NOT_BOUND)"
            )
        if self.profile_state != "SOURCE_NOT_BOUND":
            raise MontageLearningConnectorReadinessError(
                "profile_state must be SOURCE_NOT_BOUND"
            )
        if type(self.reason_codes) is not tuple:
            raise MontageLearningConnectorReadinessError(
                "reason_codes must be a tuple"
            )
        for reason in self.reason_codes:
            _require_token(reason, "reason_code")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningConnectorReadiness",
            "task_id": "TASK-058",
            "bridge_state": self.bridge_state,
            "import_state": self.import_state,
            "profile_state": (
                self.profile_state
                if self.production_profile_source_bound
                else "SOURCE_NOT_BOUND"
            ),
            "adapter_state": self.adapter_state,
            "activation_state": "BLOCKED",
            "connector_enabled": False,
            "activation_authorized": False,
            "production_profile_source_bound": self.production_profile_source_bound,
            "adapter_contract_e2e_pass": self.adapter_contract_e2e_pass,
            "default_skill_config_unchanged": self.default_skill_config_unchanged,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class _ConnectorReadinessPredicateV2:
    """Private V2 evaluation detail; not a public/package contract."""
    predicate_id: str
    state: str
    evidence_sha256: str | None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_token(self.predicate_id, "predicate_id")
        if type(self.state) is not str or self.state not in _PREDICATE_STATES:
            raise MontageLearningConnectorReadinessError("predicate state is invalid")
        if self.evidence_sha256 is not None:
            _require_sha(self.evidence_sha256, "predicate evidence_sha256")
        if self.state == "PASS" and self.evidence_sha256 is None:
            raise MontageLearningConnectorReadinessError(
                "passing predicate requires evidence"
            )
        _require_sorted_reason_codes(self.reason_codes, "predicate reason_codes")

    def to_dict(self) -> dict[str, object]:
        return {
            "predicate_id": self.predicate_id,
            "state": self.state,
            "evidence_sha256": self.evidence_sha256,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> "_ConnectorReadinessPredicateV2":
        body = _plain_snapshot(value, path="$predicate", max_depth=4)
        if type(body) is not dict or set(body) != {
            "predicate_id", "state", "evidence_sha256", "reason_codes"
        }:
            raise MontageLearningConnectorReadinessError(
                "predicate fields mismatch"
            )
        reasons = body["reason_codes"]
        if type(reasons) is not list:
            raise MontageLearningConnectorReadinessError(
                "predicate reason_codes must be a list"
            )
        return cls(
            predicate_id=body["predicate_id"],
            state=body["state"],
            evidence_sha256=body["evidence_sha256"],
            reason_codes=tuple(reasons),
        )


@dataclass(frozen=True, slots=True)
class _ConnectorReadinessComponentV2:
    """Private V2 component snapshot; never an activation capability."""
    component_id: str
    component_version: str
    state: str
    code_sha256: str
    schema_sha256: str
    test_vector_sha256: str
    observed_at: str
    expires_at: str
    evidence_sha256: tuple[str, ...]
    predicates: tuple[_ConnectorReadinessPredicateV2, ...]
    reason_codes: tuple[str, ...]
    component_self_hash: str

    def __post_init__(self) -> None:
        if self.component_id not in _READINESS_COMPONENT_PREDICATES:
            raise MontageLearningConnectorReadinessError("component_id is invalid")
        if type(self.component_version) is not str or _SEMVER_RE.fullmatch(
            self.component_version
        ) is None:
            raise MontageLearningConnectorReadinessError(
                "component_version is invalid"
            )
        if type(self.state) is not str or self.state not in _COMPONENT_STATES:
            raise MontageLearningConnectorReadinessError("component state is invalid")
        if self.state == "SOURCE_NOT_BOUND" and self.component_id != "PROFILE_TRANSPORT_READY":
            raise MontageLearningConnectorReadinessError(
                "SOURCE_NOT_BOUND is profile-only"
            )
        for field in ("code_sha256", "schema_sha256", "test_vector_sha256"):
            _require_sha(getattr(self, field), field)
        observed = _parse_utc(self.observed_at, "component observed_at")
        expires = _parse_utc(self.expires_at, "component expires_at")
        if expires <= observed:
            raise MontageLearningConnectorReadinessError(
                "component freshness interval is invalid"
            )
        if type(self.evidence_sha256) is not tuple or tuple(sorted(set(self.evidence_sha256))) != self.evidence_sha256:
            raise MontageLearningConnectorReadinessError(
                "component evidence must be sorted unique"
            )
        for digest in self.evidence_sha256:
            _require_sha(digest, "component evidence_sha256")
        if type(self.predicates) is not tuple or any(
            not isinstance(item, _ConnectorReadinessPredicateV2)
            for item in self.predicates
        ):
            raise MontageLearningConnectorReadinessError(
                "component predicates are invalid"
            )
        predicate_ids = tuple(item.predicate_id for item in self.predicates)
        if predicate_ids != _READINESS_COMPONENT_PREDICATES[self.component_id]:
            raise MontageLearningConnectorReadinessError(
                "component predicate set/order mismatch"
            )
        if self.state == "PASS" and any(item.state != "PASS" for item in self.predicates):
            raise MontageLearningConnectorReadinessError(
                "passing component has a non-passing predicate"
            )
        if self.state == "NOT_RUN" and any(item.state != "NOT_RUN" for item in self.predicates):
            raise MontageLearningConnectorReadinessError(
                "not-run component has evaluated predicates"
            )
        if self.state == "SOURCE_NOT_BOUND" and self.predicates[0].state == "PASS":
            raise MontageLearningConnectorReadinessError(
                "unbound Profile component claims a bound producer"
            )
        expected_evidence = tuple(
            sorted(
                {
                    self.code_sha256,
                    self.schema_sha256,
                    self.test_vector_sha256,
                    *(
                        item.evidence_sha256
                        for item in self.predicates
                        if item.evidence_sha256 is not None
                    ),
                }
            )
        )
        if self.state == "PASS" and self.evidence_sha256 != expected_evidence:
            raise MontageLearningConnectorReadinessError(
                "passing component evidence set is incomplete"
            )
        if self.state != "PASS" and self.evidence_sha256:
            raise MontageLearningConnectorReadinessError(
                "non-passing component cannot claim complete evidence"
            )
        _require_sorted_reason_codes(self.reason_codes, "component reason_codes")
        _require_sha(self.component_self_hash, "component_self_hash")
        if sha256_json(self._body()) != self.component_self_hash:
            raise MontageLearningConnectorReadinessError(
                "component self-hash mismatch"
            )

    def _body(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "state": self.state,
            "code_sha256": self.code_sha256,
            "schema_sha256": self.schema_sha256,
            "test_vector_sha256": self.test_vector_sha256,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "evidence_sha256": list(self.evidence_sha256),
            "predicates": [item.to_dict() for item in self.predicates],
            "reason_codes": list(self.reason_codes),
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "component_self_hash": self.component_self_hash}

    @classmethod
    def compile(
        cls,
        *,
        component_id: str,
        state: str,
        code_sha256: str,
        schema_sha256: str,
        test_vector_sha256: str,
        observed_at: str,
        expires_at: str,
        evidence_sha256: tuple[str, ...],
        predicates: tuple[_ConnectorReadinessPredicateV2, ...],
        reason_codes: tuple[str, ...] = (),
        component_version: str = "1.0.0",
    ) -> "_ConnectorReadinessComponentV2":
        provisional = {
            "component_id": component_id,
            "component_version": component_version,
            "state": state,
            "code_sha256": code_sha256,
            "schema_sha256": schema_sha256,
            "test_vector_sha256": test_vector_sha256,
            "observed_at": observed_at,
            "expires_at": expires_at,
            "evidence_sha256": list(evidence_sha256),
            "predicates": [item.to_dict() for item in predicates],
            "reason_codes": list(reason_codes),
        }
        return cls(
            component_id=component_id,
            component_version=component_version,
            state=state,
            code_sha256=code_sha256,
            schema_sha256=schema_sha256,
            test_vector_sha256=test_vector_sha256,
            observed_at=observed_at,
            expires_at=expires_at,
            evidence_sha256=evidence_sha256,
            predicates=predicates,
            reason_codes=reason_codes,
            component_self_hash=sha256_json(provisional),
        )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> "_ConnectorReadinessComponentV2":
        body = _plain_snapshot(value, path="$component", max_depth=8)
        expected = {
            "component_id", "component_version", "state", "code_sha256",
            "schema_sha256", "test_vector_sha256", "observed_at", "expires_at",
            "evidence_sha256", "predicates", "reason_codes", "component_self_hash",
        }
        if type(body) is not dict or set(body) != expected:
            raise MontageLearningConnectorReadinessError(
                "component fields mismatch"
            )
        evidence = body["evidence_sha256"]
        predicates = body["predicates"]
        reasons = body["reason_codes"]
        if type(evidence) is not list or type(predicates) is not list or type(reasons) is not list:
            raise MontageLearningConnectorReadinessError(
                "component collections are invalid"
            )
        return cls(
            component_id=body["component_id"],
            component_version=body["component_version"],
            state=body["state"],
            code_sha256=body["code_sha256"],
            schema_sha256=body["schema_sha256"],
            test_vector_sha256=body["test_vector_sha256"],
            observed_at=body["observed_at"],
            expires_at=body["expires_at"],
            evidence_sha256=tuple(evidence),
            predicates=tuple(
                _ConnectorReadinessPredicateV2.from_dict(item) for item in predicates
            ),
            reason_codes=tuple(reasons),
            component_self_hash=body["component_self_hash"],
        )


@dataclass(frozen=True, slots=True)
class _ConnectorReadinessEvidenceV2:
    """Private readiness diagnostic; public serialization remains V1 only."""
    readiness_id: str
    bvp_main_sha256: str
    bvp_package_sha256: str
    skill_package_sha256: str
    connector_config_sha256: str
    bridge_owner_attestation_sha256: str
    bridge_security_model: str
    evaluation_mode: str
    activation_record_sha256: str | None
    config_enabled: bool
    verified_at: str
    expires_at: str
    components: tuple[_ConnectorReadinessComponentV2, ...]
    overall_state: str
    reason_codes: tuple[str, ...]
    readiness_self_hash: str

    def __post_init__(self) -> None:
        for field in (
            "readiness_id", "bvp_main_sha256", "bvp_package_sha256",
            "skill_package_sha256", "connector_config_sha256",
            "bridge_owner_attestation_sha256", "readiness_self_hash",
        ):
            _require_sha(getattr(self, field), field)
        if self.bridge_security_model != _BRIDGE_SECURITY_MODEL:
            raise MontageLearningConnectorReadinessError(
                "bridge security model mismatch"
            )
        if self.evaluation_mode not in _EVALUATION_MODES:
            raise MontageLearningConnectorReadinessError(
                "evaluation mode is invalid"
            )
        if self.activation_record_sha256 is not None:
            _require_sha(self.activation_record_sha256, "activation_record_sha256")
        if type(self.config_enabled) is not bool:
            raise MontageLearningConnectorReadinessError(
                "config_enabled must be a built-in bool"
            )
        verified = _parse_utc(self.verified_at, "readiness verified_at")
        expires = _parse_utc(self.expires_at, "readiness expires_at")
        if expires <= verified:
            raise MontageLearningConnectorReadinessError(
                "readiness freshness interval is invalid"
            )
        if type(self.components) is not tuple or tuple(
            item.component_id for item in self.components
        ) != tuple(_READINESS_COMPONENT_PREDICATES):
            raise MontageLearningConnectorReadinessError(
                "readiness component set/order mismatch"
            )
        for component in self.components:
            if _parse_utc(component.observed_at, "component observed_at") > verified:
                raise MontageLearningConnectorReadinessError(
                    "component observation is after readiness evaluation"
                )
            if _parse_utc(component.expires_at, "component expires_at") < expires:
                raise MontageLearningConnectorReadinessError(
                    "component expires before readiness evidence"
                )
        if self.overall_state not in _OVERALL_STATES:
            raise MontageLearningConnectorReadinessError("overall_state is invalid")
        _require_sorted_reason_codes(self.reason_codes, "readiness reason_codes")
        expected_state = _classify_readiness(
            self.components,
            evaluation_mode=self.evaluation_mode,
            config_enabled=self.config_enabled,
            activation_record_sha256=self.activation_record_sha256,
            reason_codes=self.reason_codes,
        )
        if self.overall_state != expected_state:
            raise MontageLearningConnectorReadinessError(
                "overall readiness classification mismatch"
            )
        body = self._body()
        if sha256_json({"domain": "BVP_MONTAGE_CONNECTOR_READINESS_ID_V2", **body}) != self.readiness_id:
            raise MontageLearningConnectorReadinessError("readiness_id mismatch")
        if sha256_json({**body, "readiness_id": self.readiness_id}) != self.readiness_self_hash:
            raise MontageLearningConnectorReadinessError(
                "readiness self-hash mismatch"
            )

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": "2.0.0",
            "message_type": "BvpMontageLearningConnectorReadiness",
            "task_id": "TASK-058",
            "bvp_main_sha256": self.bvp_main_sha256,
            "bvp_package_sha256": self.bvp_package_sha256,
            "skill_package_sha256": self.skill_package_sha256,
            "connector_config_sha256": self.connector_config_sha256,
            "bridge_owner_attestation_sha256": self.bridge_owner_attestation_sha256,
            "bridge_security_model": self.bridge_security_model,
            "evaluation_mode": self.evaluation_mode,
            "activation_record_sha256": self.activation_record_sha256,
            "config_enabled": self.config_enabled,
            "verified_at": self.verified_at,
            "expires_at": self.expires_at,
            "components": {item.component_id: item.to_dict() for item in self.components},
            "overall_state": self.overall_state,
            "reason_codes": list(self.reason_codes),
            "connector_enabled": False,
            "activation_authorized": False,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._body(),
            "readiness_id": self.readiness_id,
            "readiness_self_hash": self.readiness_self_hash,
        }

    @classmethod
    def compile(
        cls,
        *,
        bvp_main_sha256: str,
        bvp_package_sha256: str,
        skill_package_sha256: str,
        connector_config_sha256: str,
        bridge_owner_attestation_sha256: str,
        evaluation_mode: str,
        activation_record_sha256: str | None,
        config_enabled: bool,
        verified_at: str,
        expires_at: str,
        components: tuple[_ConnectorReadinessComponentV2, ...],
        reason_codes: tuple[str, ...],
    ) -> "_ConnectorReadinessEvidenceV2":
        overall = _classify_readiness(
            components,
            evaluation_mode=evaluation_mode,
            config_enabled=config_enabled,
            activation_record_sha256=activation_record_sha256,
            reason_codes=reason_codes,
        )
        body = {
            "schema_version": "2.0.0",
            "message_type": "BvpMontageLearningConnectorReadiness",
            "task_id": "TASK-058",
            "bvp_main_sha256": bvp_main_sha256,
            "bvp_package_sha256": bvp_package_sha256,
            "skill_package_sha256": skill_package_sha256,
            "connector_config_sha256": connector_config_sha256,
            "bridge_owner_attestation_sha256": bridge_owner_attestation_sha256,
            "bridge_security_model": _BRIDGE_SECURITY_MODEL,
            "evaluation_mode": evaluation_mode,
            "activation_record_sha256": activation_record_sha256,
            "config_enabled": config_enabled,
            "verified_at": verified_at,
            "expires_at": expires_at,
            "components": {item.component_id: item.to_dict() for item in components},
            "overall_state": overall,
            "reason_codes": list(reason_codes),
            "connector_enabled": False,
            "activation_authorized": False,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }
        readiness_id = sha256_json(
            {"domain": "BVP_MONTAGE_CONNECTOR_READINESS_ID_V2", **body}
        )
        return cls(
            readiness_id=readiness_id,
            bvp_main_sha256=bvp_main_sha256,
            bvp_package_sha256=bvp_package_sha256,
            skill_package_sha256=skill_package_sha256,
            connector_config_sha256=connector_config_sha256,
            bridge_owner_attestation_sha256=bridge_owner_attestation_sha256,
            bridge_security_model=_BRIDGE_SECURITY_MODEL,
            evaluation_mode=evaluation_mode,
            activation_record_sha256=activation_record_sha256,
            config_enabled=config_enabled,
            verified_at=verified_at,
            expires_at=expires_at,
            components=components,
            overall_state=overall,
            reason_codes=reason_codes,
            readiness_self_hash=sha256_json({**body, "readiness_id": readiness_id}),
        )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> "_ConnectorReadinessEvidenceV2":
        body = _plain_snapshot(value, path="$readiness", max_depth=12)
        expected = {
            "schema_version", "message_type", "task_id", "readiness_id",
            "bvp_main_sha256", "bvp_package_sha256", "skill_package_sha256",
            "connector_config_sha256", "bridge_owner_attestation_sha256",
            "bridge_security_model", "evaluation_mode", "activation_record_sha256",
            "config_enabled", "verified_at", "expires_at", "components",
            "overall_state", "reason_codes", "connector_enabled",
            "activation_authorized", "learning_adoption_authorized",
            "automatic_promotion_authorized", "timeline_mutation_authorized",
            "resolve_write_authorized", "readiness_self_hash",
        }
        if type(body) is not dict or set(body) != expected:
            raise MontageLearningConnectorReadinessError(
                "readiness fields mismatch"
            )
        constants = {
            "schema_version": "2.0.0",
            "message_type": "BvpMontageLearningConnectorReadiness",
            "task_id": "TASK-058",
            "connector_enabled": False,
            "activation_authorized": False,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }
        if any(body[field] != expected_value for field, expected_value in constants.items()):
            raise MontageLearningConnectorReadinessError(
                "readiness identity/authority constant mismatch"
            )
        component_values = body["components"]
        reasons = body["reason_codes"]
        if type(component_values) is not dict or set(component_values) != set(
            _READINESS_COMPONENT_PREDICATES
        ) or type(reasons) is not list:
            raise MontageLearningConnectorReadinessError(
                "readiness collections mismatch"
            )
        return cls(
            readiness_id=body["readiness_id"],
            bvp_main_sha256=body["bvp_main_sha256"],
            bvp_package_sha256=body["bvp_package_sha256"],
            skill_package_sha256=body["skill_package_sha256"],
            connector_config_sha256=body["connector_config_sha256"],
            bridge_owner_attestation_sha256=body["bridge_owner_attestation_sha256"],
            bridge_security_model=body["bridge_security_model"],
            evaluation_mode=body["evaluation_mode"],
            activation_record_sha256=body["activation_record_sha256"],
            config_enabled=body["config_enabled"],
            verified_at=body["verified_at"],
            expires_at=body["expires_at"],
            components=tuple(
                _ConnectorReadinessComponentV2.from_dict(component_values[key])
                for key in _READINESS_COMPONENT_PREDICATES
            ),
            overall_state=body["overall_state"],
            reason_codes=tuple(reasons),
            readiness_self_hash=body["readiness_self_hash"],
        )


def publish_prebuilt_advisory_profile(
    layout: BridgeLayout,
    envelope: Mapping[str, object],
    *,
    source_binding: ProfileSourceBinding,
    expected_previous_profile_sha256: str | None = None,
) -> ProfilePublishResult:
    """Revalidate and copy a prebuilt SKILL v1 envelope without derivation."""

    load_bridge_owner(layout)
    if source_binding.production_profile_source_bound is False and not (
        source_binding.isolated_fixture and not layout.production_path
    ):
        return ProfilePublishResult(
            status="SOURCE_NOT_BOUND",
            profile_id=None,
            profile_sha256=None,
            written=False,
            production_profile_source_bound=False,
        )
    if layout.production_path and source_binding.isolated_fixture:
        raise MontageLearningConnectorReadinessError(
            "isolated fixture binding cannot publish to production layout"
        )
    value = validate_prebuilt_advisory_profile(envelope)
    if (
        source_binding.production_profile_source_bound
        and source_binding.envelope_sha256 != sha256_json(value)
    ):
        raise MontageLearningConnectorReadinessError(
            "production source binding does not match the exact envelope"
        )
    status = publish_current_profile(
        layout,
        value,
        expected_previous_profile_sha256=expected_previous_profile_sha256,
    )
    return ProfilePublishResult(
        status=status,
        profile_id=value["profile_id"],
        profile_sha256=value["profile_sha256"],
        written=status == "PUBLISHED",
        # Fixture PASS is transport compatibility, never a production binding.
        production_profile_source_bound=source_binding.production_profile_source_bound,
    )


def validate_prebuilt_advisory_profile(
    envelope: Mapping[str, object],
) -> dict[str, Any]:
    """Strict independent mirror of the SKILL v1 Profile delivery contract."""

    value = _plain_snapshot(envelope, path="$", max_depth=16)
    if type(value) is not dict or set(value) != _DELIVERY_FIELDS:
        raise MontageLearningConnectorReadinessError("profile delivery fields mismatch")
    constants = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontagePreferenceProfileDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "profile_contract": "bvp-task029-montage-preference-projection-v1",
        "advisory_only": True,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
    }
    for field, expected in constants.items():
        if value[field] != expected or type(value[field]) is not type(expected):
            raise MontageLearningConnectorReadinessError(
                f"profile delivery {field} mismatch"
            )
    _require_id(value["profile_id"], "profile_id")
    version = value["profile_version"]
    if isinstance(version, bool) or not (
        (type(version) is int and version >= 0)
        or (type(version) is str and bool(version.strip()))
    ):
        raise MontageLearningConnectorReadinessError("profile_version is invalid")
    _require_sha(value["owner_scope_hash"], "owner_scope_hash")
    count = value["source_record_count"]
    if isinstance(count, bool) or type(count) is not int or count < 0:
        raise MontageLearningConnectorReadinessError(
            "source_record_count is invalid"
        )
    supplied_hash = _require_sha(value["profile_sha256"], "profile_sha256")
    payload = _validate_projection(value["payload"])
    if sha256_json(payload) != supplied_hash:
        raise MontageLearningConnectorReadinessError("profile_sha256 mismatch")
    value["payload"] = payload
    return value


def production_readiness_evidence(
    *,
    bridge_state: str,
    import_state: str,
    adapter_state: str,
    adapter_contract_e2e_pass: bool,
    default_skill_config_unchanged: bool,
) -> ConnectorReadinessEvidence:
    """Return honest Batch evidence while the production producer is unbound."""

    return ConnectorReadinessEvidence(
        bridge_state=bridge_state,
        import_state=import_state,
        profile_state="SOURCE_NOT_BOUND",
        adapter_state=adapter_state,
        production_profile_source_bound=False,
        adapter_contract_e2e_pass=adapter_contract_e2e_pass,
        default_skill_config_unchanged=default_skill_config_unchanged,
        reason_codes=("SOURCE_NOT_BOUND",),
    )


def _validate_projection(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"projection_version", "preferences"}:
        raise MontageLearningConnectorReadinessError("projection fields mismatch")
    if value["projection_version"] != "1.0.0":
        raise MontageLearningConnectorReadinessError("projection version mismatch")
    preferences = value["preferences"]
    if type(preferences) is not list or len(preferences) > 1000:
        raise MontageLearningConnectorReadinessError("preferences are invalid")
    seen: set[str] = set()
    for index, item in enumerate(preferences):
        if type(item) is not dict or set(item) != _PREFERENCE_FIELDS:
            raise MontageLearningConnectorReadinessError(
                f"preference {index} fields mismatch"
            )
        preference_id = _require_id(item["preference_id"], "preference_id")
        if preference_id in seen:
            raise MontageLearningConnectorReadinessError(
                "duplicate preference_id"
            )
        seen.add(preference_id)
        if item["decision"] not in {"PREFER", "AVOID", "PROTECT", "DEPRIORITIZE"}:
            raise MontageLearningConnectorReadinessError("decision is invalid")
        _require_token(item["target"], "target")
        contexts = item["contexts"]
        if type(contexts) is not list or not 1 <= len(contexts) <= 16:
            raise MontageLearningConnectorReadinessError("contexts are invalid")
        for context in contexts:
            _validate_preference_context(context)
        for field, low, high in (
            ("confidence", 0.0, 1.0),
            ("ranking_bias", -1.0, 1.0),
        ):
            number = item[field]
            if isinstance(number, bool) or type(number) not in {int, float}:
                raise MontageLearningConnectorReadinessError(f"{field} is invalid")
            if not math.isfinite(float(number)) or not low <= number <= high:
                raise MontageLearningConnectorReadinessError(f"{field} is invalid")
        confirmation_count = item["confirmation_count"]
        if (
            isinstance(confirmation_count, bool)
            or type(confirmation_count) is not int
            or confirmation_count < 1
        ):
            raise MontageLearningConnectorReadinessError(
                "confirmation_count is invalid"
            )
        reasons = item["reason_codes"]
        if type(reasons) is not list or not 1 <= len(reasons) <= 16:
            raise MontageLearningConnectorReadinessError("reason_codes are invalid")
        for reason in reasons:
            _require_token(reason, "reason_code")
    return value


def _plain_snapshot(value: object, *, path: str, max_depth: int) -> Any:
    if max_depth < 0:
        raise MontageLearningConnectorReadinessError("profile nesting is too deep")
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise MontageLearningConnectorReadinessError(f"{path} is not finite")
        return value
    if type(value) is list:
        return [
            _plain_snapshot(item, path=f"{path}[{index}]", max_depth=max_depth - 1)
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise MontageLearningConnectorReadinessError(f"{path} has invalid key")
        return {
            key: _plain_snapshot(
                child,
                path=f"{path}.{key}",
                max_depth=max_depth - 1,
            )
            for key, child in value.items()
        }
    raise MontageLearningConnectorReadinessError(
        f"{path} must contain built-in JSON values only"
    )


def _require_id(value: object, field: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _require_sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _require_token(value: object, field: str) -> str:
    if type(value) is not str or _TOKEN_RE.fullmatch(value) is None:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    return value


def _require_sorted_reason_codes(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or tuple(sorted(set(value))) != value:
        raise MontageLearningConnectorReadinessError(
            f"{field} must be sorted unique"
        )
    for reason in value:
        _require_token(reason, field)
    return value


def _parse_utc(value: object, field: str) -> datetime:
    if type(value) is not str or len(value) != 20:
        raise MontageLearningConnectorReadinessError(f"{field} is invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise MontageLearningConnectorReadinessError(
            f"{field} is invalid"
        ) from exc
    return parsed


def _classify_readiness(
    components: tuple[_ConnectorReadinessComponentV2, ...],
    *,
    evaluation_mode: str,
    config_enabled: bool,
    activation_record_sha256: str | None,
    reason_codes: tuple[str, ...],
) -> str:
    del activation_record_sha256  # TASK-058 cannot authenticate activation currentness.
    states = {item.component_id: item.state for item in components}
    if config_enabled:
        return "BLOCKED"
    if (
        evaluation_mode == "STATUS_ONLY"
        and all(state == "NOT_RUN" for state in states.values())
        and "READINESS_NOT_REQUESTED" in reason_codes
    ):
        return "DISABLED"
    if evaluation_mode == "FULL_E2E":
        non_profile = [
            state for key, state in states.items()
            if key != "PROFILE_TRANSPORT_READY"
        ]
        if (
            all(state == "PASS" for state in non_profile)
            and states.get("PROFILE_TRANSPORT_READY") == "SOURCE_NOT_BOUND"
        ):
            return "SOURCE_NOT_BOUND"
        # TASK-058 owns no trusted current-HEAD/package-byte oracle.  Even a
        # complete caller-shaped diagnostic must therefore remain non-ready.
        if all(state == "PASS" for state in states.values()):
            return "BLOCKED"
    return "BLOCKED"


def _validate_preference_context(value: object) -> str:
    """Validate private/free-form source material used as a preference context."""

    if type(value) is not str or not 1 <= len(value) <= 128:
        raise MontageLearningConnectorReadinessError("context is invalid")
    if any(char in value for char in "/\\@") or any(
        ord(char) < 32 or ord(char) == 127 for char in value
    ):
        raise MontageLearningConnectorReadinessError(
            "context contains invalid private/free-form source material"
        )
    if _CONTEXT_MARKER_RE.search(value) is not None:
        raise MontageLearningConnectorReadinessError(
            "context contains restricted private/free-form source material"
        )
    return value


__all__ = [
    "ConnectorReadinessEvidence",
    "MontageLearningConnectorReadinessError",
    "ProfilePublishResult",
    "ProfileSourceBinding",
    "production_readiness_evidence",
    "publish_prebuilt_advisory_profile",
    "validate_prebuilt_advisory_profile",
]
