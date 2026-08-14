"""TASK-042 secret-free Provider -> compatible Model readiness projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from .capability_execution import ModelCapabilityCatalog
from .errors import ProductError
from .serialization import canonical_json_bytes, sha256_bytes


def _mode_allows(mode: SelectionMode, route: ModelRoute) -> bool:
    if mode is SelectionMode.DISABLED:
        return False
    if mode is SelectionMode.AI:
        return route.is_ai
    if mode is SelectionMode.FREE:
        return route.is_free
    if mode is SelectionMode.OFFLINE_ONLY:
        return route.is_offline
    return True


@dataclass(frozen=True, slots=True)
class GenerationRouteRow:
    provider_family: str
    provider_id: str
    model_id: str
    route_id: str
    workload: str
    selection_mode: str
    cost_class: str
    local_mode: bool
    cloud_mode: bool
    enabled: bool
    declared_capabilities: tuple[str, ...]
    catalog_capabilities: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    adapter_capabilities: tuple[str, ...]
    route_available: bool
    credential_required: bool
    credential_configured: bool
    ready: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_family": self.provider_family,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "route_id": self.route_id,
            "workload": self.workload,
            "selection_mode": self.selection_mode,
            "cost_class": self.cost_class,
            "local_mode": self.local_mode,
            "cloud_mode": self.cloud_mode,
            "enabled": self.enabled,
            "declared_capabilities": list(self.declared_capabilities),
            "catalog_capabilities": list(self.catalog_capabilities),
            "required_capabilities": list(self.required_capabilities),
            "adapter_capabilities": list(self.adapter_capabilities),
            "route_available": self.route_available,
            "credential_required": self.credential_required,
            "credential_configured": self.credential_configured,
            "ready": self.ready,
            "blockers": list(self.blockers),
        }


class GenerationRouteProjectionService:
    """Project every configured model without probing or mutating a Provider."""

    @staticmethod
    def project(
        profile: AiConnectionProfile,
        workload: AiWorkload,
        availability: ConnectionAvailability,
        *,
        required_capabilities: tuple[str, ...],
        catalog: ModelCapabilityCatalog | None,
        installed_adapter_capabilities: Mapping[ProviderFamily, frozenset[str]],
    ) -> dict[str, Any]:
        if not isinstance(profile, AiConnectionProfile) or not isinstance(workload, AiWorkload):
            raise ValueError("profile and workload are invalid")
        if not isinstance(required_capabilities, tuple) or not required_capabilities:
            raise ValueError("required_capabilities must be non-empty")
        if len(set(required_capabilities)) != len(required_capabilities):
            raise ValueError("required_capabilities must be unique")
        required = tuple(sorted(required_capabilities))
        mode = profile.mode_for(workload)
        routes = sorted(
            (route for route in profile.routes if route.workload is workload),
            key=lambda route: (
                route.provider_family.value, route.provider_id, route.priority,
                route.model_id, route.route_id,
            ),
        )
        rows: list[GenerationRouteRow] = []
        for route in routes:
            blockers: list[str] = []
            declared = tuple(sorted(route.capabilities))
            adapter = tuple(sorted(installed_adapter_capabilities.get(route.provider_family, frozenset())))
            catalog_capabilities: tuple[str, ...] = ()
            if mode is SelectionMode.DISABLED:
                blockers.append("WORKLOAD_DISABLED")
            if not route.enabled:
                blockers.append("ROUTE_DISABLED")
            if not _mode_allows(mode, route):
                blockers.append("SELECTION_MODE_INCOMPATIBLE")
            if not set(required).issubset(route.capabilities):
                blockers.append("ROUTE_CAPABILITY_UNDECLARED")
            if catalog is None:
                blockers.append("MODEL_CATALOG_UNAVAILABLE")
            else:
                try:
                    descriptor = catalog.descriptor_for(route)
                except ProductError:
                    blockers.append("MODEL_NOT_CATALOGED")
                else:
                    catalog_capabilities = tuple(sorted(descriptor.capabilities))
                    if workload not in descriptor.workloads or not set(required).issubset(descriptor.capabilities):
                        blockers.append("MODEL_CAPABILITY_UNSUPPORTED")
            if not set(required).issubset(adapter):
                blockers.append("ADAPTER_CAPABILITY_MISSING")
            route_available = route.route_id in availability.available_route_ids
            if not route_available:
                blockers.append("ROUTE_UNAVAILABLE")
            credential_required = route.credential_ref is not None
            credential_configured = not credential_required or route.credential_ref in availability.available_credential_refs
            if not credential_configured:
                blockers.append("CREDENTIAL_MISSING")
            rows.append(GenerationRouteRow(
                provider_family=route.provider_family.value,
                provider_id=route.provider_id,
                model_id=route.model_id,
                route_id=route.route_id,
                workload=workload.value,
                selection_mode=mode.value,
                cost_class=route.cost_class.value,
                local_mode=route.is_offline,
                cloud_mode=not route.is_offline,
                enabled=route.enabled,
                declared_capabilities=declared,
                catalog_capabilities=catalog_capabilities,
                required_capabilities=required,
                adapter_capabilities=adapter,
                route_available=route_available,
                credential_required=credential_required,
                credential_configured=credential_configured,
                ready=not blockers,
                blockers=tuple(blockers),
            ))
        body: dict[str, Any] = {
            "projection_version": "1.0.0",
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "workload": workload.value,
            "selection_mode": mode.value,
            "required_capabilities": list(required),
            "routes": [row.to_dict() for row in rows],
            "provider_probe_performed": False,
            "credential_values_embedded": False,
            "provider_execution_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = ["GenerationRouteProjectionService", "GenerationRouteRow"]
