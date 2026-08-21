from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .ai_connections import (
    AiConnectionProfile,
    AiConnectionResolver,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ProviderFamily,
    ReasoningEffort,
)
from .dbd_reasoning_contracts import CONTEXT_SCHEMA_VERSION, PROPOSAL_SCHEMA_VERSION
from .dbd_tuned_model_registry import (
    DbDTunedModelRegistry,
    DbDTunedModelResolution,
    admit_tuned_model_registry_record,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


ROUTE_DECISION_SCHEMA_VERSION = "1.0.0"
ROUTE_DECISION_RECORD_KIND = "DBD_REASONING_ROUTE_DECISION"
ROUTE_CAPABILITY = "DBD_TUNED_COMMENTARY_REASONING"
EXECUTION_AUTHORITY_STATE = "NOT_AUTHORIZED_R3D_REQUIRED"

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:-]{0,127}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_EXACT_FIELDS = frozenset({
    "schema_version", "record_kind", "binding_id", "binding_revision",
    "binding_sha256", "registry_record_sha256", "profile_id",
    "profile_version", "profile_sha256", "route_id", "provider_family",
    "provider_id", "model_id", "cost_class", "reasoning_effort",
    "credential_required", "endpoint_configured", "route_capability",
    "execution_authority_state", "route_decision_sha256",
})


def _safe_id(value: str, *, name: str, model: bool = False) -> None:
    matcher = _MODEL_ID if model else _SAFE_ID
    if not isinstance(value, str) or not matcher.fullmatch(value):
        raise ValueError(f"{name} is invalid")


def _sha(value: str, *, name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a canonical sha256 digest")


@dataclass(frozen=True, slots=True)
class DbDReasoningRouteDecision:
    binding_id: str
    binding_revision: int
    binding_sha256: str
    registry_record_sha256: str
    profile_id: str
    profile_version: str
    profile_sha256: str
    route_id: str
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    cost_class: CostClass
    reasoning_effort: ReasoningEffort
    credential_required: bool
    endpoint_configured: bool
    route_capability: str = ROUTE_CAPABILITY
    execution_authority_state: str = EXECUTION_AUTHORITY_STATE

    def __post_init__(self) -> None:
        for name in ("binding_id", "profile_id", "route_id", "provider_id"):
            _safe_id(getattr(self, name), name=name)
        _safe_id(self.model_id, name="model_id", model=True)
        if not isinstance(self.profile_version, str) or not self.profile_version or len(self.profile_version) > 64:
            raise ValueError("profile_version is invalid")
        if isinstance(self.binding_revision, bool) or not isinstance(self.binding_revision, int) or self.binding_revision < 1:
            raise ValueError("binding_revision must be positive")
        for name in ("binding_sha256", "registry_record_sha256", "profile_sha256"):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.provider_family, ProviderFamily):
            raise ValueError("provider_family must be ProviderFamily")
        if not isinstance(self.cost_class, CostClass):
            raise ValueError("cost_class must be CostClass")
        if not isinstance(self.reasoning_effort, ReasoningEffort):
            raise ValueError("reasoning_effort must be ReasoningEffort")
        if not isinstance(self.credential_required, bool) or not isinstance(self.endpoint_configured, bool):
            raise ValueError("route configuration indicators must be booleans")
        if self.route_capability != ROUTE_CAPABILITY:
            raise ValueError("route capability is not the DbD tuned reasoning capability")
        if self.execution_authority_state != EXECUTION_AUTHORITY_STATE:
            raise ValueError("R3B cannot grant execution authority")

    def _body(self) -> dict[str, Any]:
        return {
            "schema_version": ROUTE_DECISION_SCHEMA_VERSION,
            "record_kind": ROUTE_DECISION_RECORD_KIND,
            "binding_id": self.binding_id,
            "binding_revision": self.binding_revision,
            "binding_sha256": self.binding_sha256,
            "registry_record_sha256": self.registry_record_sha256,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "profile_sha256": self.profile_sha256,
            "route_id": self.route_id,
            "provider_family": self.provider_family.value,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "cost_class": self.cost_class.value,
            "reasoning_effort": self.reasoning_effort.value,
            "credential_required": self.credential_required,
            "endpoint_configured": self.endpoint_configured,
            "route_capability": self.route_capability,
            "execution_authority_state": self.execution_authority_state,
        }

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        return {**body, "route_decision_sha256": sha256_bytes(canonical_json_bytes(body))}


def admit_dbd_reasoning_route_decision(record: Mapping[str, Any]) -> DbDReasoningRouteDecision:
    if not isinstance(record, Mapping) or set(record) != _EXACT_FIELDS:
        raise ValueError("route decision has unknown or missing fields")
    if record["schema_version"] != ROUTE_DECISION_SCHEMA_VERSION:
        raise ValueError("unsupported route decision schema_version")
    if record["record_kind"] != ROUTE_DECISION_RECORD_KIND:
        raise ValueError("unsupported route decision record_kind")
    body = {key: record[key] for key in record if key != "route_decision_sha256"}
    if record["route_decision_sha256"] != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("route decision checksum mismatch")
    try:
        decision = DbDReasoningRouteDecision(
            binding_id=record["binding_id"],
            binding_revision=record["binding_revision"],
            binding_sha256=record["binding_sha256"],
            registry_record_sha256=record["registry_record_sha256"],
            profile_id=record["profile_id"],
            profile_version=record["profile_version"],
            profile_sha256=record["profile_sha256"],
            route_id=record["route_id"],
            provider_family=ProviderFamily(record["provider_family"]),
            provider_id=record["provider_id"],
            model_id=record["model_id"],
            cost_class=CostClass(record["cost_class"]),
            reasoning_effort=ReasoningEffort(record["reasoning_effort"]),
            credential_required=record["credential_required"],
            endpoint_configured=record["endpoint_configured"],
            route_capability=record["route_capability"],
            execution_authority_state=record["execution_authority_state"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("route decision is not canonical") from exc
    if decision.to_dict() != dict(record):
        raise ValueError("route decision is not exact canonical form")
    return decision


def _admit_registry(registry: DbDTunedModelRegistry) -> DbDTunedModelRegistry:
    if not isinstance(registry, DbDTunedModelRegistry):
        raise ValueError("registry must be DbDTunedModelRegistry")
    admitted = tuple(admit_tuned_model_registry_record(item.to_dict()) for item in registry.records)
    rebuilt = DbDTunedModelRegistry(admitted)
    if rebuilt != registry:
        raise ValueError("registry is not exact canonical form")
    return rebuilt


def _admit_profile(profile: AiConnectionProfile) -> tuple[AiConnectionProfile, dict[str, Any]]:
    if not isinstance(profile, AiConnectionProfile):
        raise ValueError("profile must be AiConnectionProfile")
    document = profile.to_dict()
    rebuilt = AiConnectionProfile.from_dict(document)
    if rebuilt.to_dict() != document:
        raise ValueError("connection profile is not exact canonical form")
    return rebuilt, document


def _require_route_pin(settings: Mapping[str, Any], resolution: DbDTunedModelResolution) -> None:
    if not isinstance(settings, Mapping):
        raise ProductError(
            "ERR_DBD_TUNED_ROUTE_BINDING_PIN_INVALID",
            "Selected route does not have a canonical tuned binding pin",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    binding_document = resolution.binding.to_dict()
    expected = {
        "dbd_tuned_binding_id": resolution.binding.binding_id,
        "dbd_tuned_binding_revision": resolution.binding.revision,
        "dbd_tuned_binding_sha256": binding_document["binding_sha256"],
    }
    actual = {key: settings.get(key) for key in expected}
    if actual != expected:
        raise ProductError(
            "ERR_DBD_TUNED_ROUTE_BINDING_PIN_MISMATCH",
            "Selected route is pinned to a different tuned binding revision",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"binding_id": resolution.binding.binding_id, "binding_revision": resolution.binding.revision},
        )


def _admit_availability(availability: ConnectionAvailability) -> ConnectionAvailability:
    if not isinstance(availability, ConnectionAvailability):
        raise ValueError("availability must be ConnectionAvailability")
    if not isinstance(availability.available_route_ids, frozenset):
        raise ValueError("available_route_ids must be a frozenset")
    if not isinstance(availability.available_credential_refs, frozenset):
        raise ValueError("available_credential_refs must be a frozenset")
    if any(not isinstance(value, str) or not _SAFE_ID.fullmatch(value) for value in availability.available_route_ids):
        raise ValueError("available_route_ids contains an invalid route ID")
    credential_pattern = re.compile(r"^credential://[a-z0-9][a-z0-9._/-]{0,127}$")
    if any(not isinstance(value, str) or not credential_pattern.fullmatch(value) for value in availability.available_credential_refs):
        raise ValueError("available_credential_refs contains an invalid reference")
    return availability


class DbDReasoningRouteCapabilityResolver:
    """Compile one non-executing DbD tuned reasoning route decision."""

    @staticmethod
    def resolve(
        registry: DbDTunedModelRegistry,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        *,
        locale: str,
        context_schema: str = CONTEXT_SCHEMA_VERSION,
        output_schema: str = PROPOSAL_SCHEMA_VERSION,
        binding_id: str | None = None,
    ) -> DbDReasoningRouteDecision:
        admitted_registry = _admit_registry(registry)
        admitted_profile, profile_document = _admit_profile(profile)
        admitted_availability = _admit_availability(availability)
        resolution = admitted_registry.resolve(
            locale=locale,
            binding_id=binding_id,
            context_schema=context_schema,
            output_schema=output_schema,
        )
        route = AiConnectionResolver.resolve(
            admitted_profile,
            AiWorkload.PLANNING,
            admitted_availability,
            required_capabilities=(ROUTE_CAPABILITY,),
        )
        if not route.is_ai:
            raise ProductError(
                "ERR_DBD_TUNED_ROUTE_NOT_AI",
                "DbD tuned reasoning requires an AI Provider route",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        _require_route_pin(route.settings, resolution)
        binding_document = resolution.binding.to_dict()
        decision = DbDReasoningRouteDecision(
            binding_id=resolution.binding.binding_id,
            binding_revision=resolution.binding.revision,
            binding_sha256=binding_document["binding_sha256"],
            registry_record_sha256=resolution.registry_record_sha256,
            profile_id=admitted_profile.profile_id,
            profile_version=admitted_profile.profile_version,
            profile_sha256=profile_document["profile_sha256"],
            route_id=route.route_id,
            provider_family=route.provider_family,
            provider_id=route.provider_id,
            model_id=route.model_id,
            cost_class=route.cost_class,
            reasoning_effort=route.reasoning_effort,
            credential_required=route.credential_ref is not None,
            endpoint_configured=route.endpoint_ref is not None,
        )
        return admit_dbd_reasoning_route_decision(decision.to_dict())

    @staticmethod
    def validate_current(
        decision: DbDReasoningRouteDecision,
        registry: DbDTunedModelRegistry,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        *,
        locale: str,
        context_schema: str = CONTEXT_SCHEMA_VERSION,
        output_schema: str = PROPOSAL_SCHEMA_VERSION,
        binding_id: str | None = None,
    ) -> DbDReasoningRouteDecision:
        if not isinstance(decision, DbDReasoningRouteDecision):
            raise ValueError("decision must be DbDReasoningRouteDecision")
        admitted = admit_dbd_reasoning_route_decision(decision.to_dict())
        expected = DbDReasoningRouteCapabilityResolver.resolve(
            registry,
            profile,
            availability,
            locale=locale,
            context_schema=context_schema,
            output_schema=output_schema,
            binding_id=binding_id,
        )
        if admitted != expected:
            raise ProductError(
                "ERR_DBD_TUNED_ROUTE_DECISION_STALE",
                "Route decision no longer matches current binding and connection state",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return admitted


__all__ = [
    "DbDReasoningRouteCapabilityResolver", "DbDReasoningRouteDecision",
    "EXECUTION_AUTHORITY_STATE", "ROUTE_CAPABILITY", "ROUTE_DECISION_RECORD_KIND",
    "ROUTE_DECISION_SCHEMA_VERSION", "admit_dbd_reasoning_route_decision",
]
