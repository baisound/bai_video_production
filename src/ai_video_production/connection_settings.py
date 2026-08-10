"""Secret-free preflight projection for a future AI Connection settings GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .ai_connections import (
    AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability,
    ModelRoute, SelectionMode,
)
from .errors import ProductError
from .serialization import canonical_json_bytes, sha256_bytes


class SettingsRouteStatus(str, Enum):
    READY = "READY"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class WorkloadSettingsStatus:
    workload: AiWorkload
    selection_mode: SelectionMode
    status: SettingsRouteStatus
    configured_route_count: int
    selected_route_id: str | None = None
    provider_family: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    cost_class: str | None = None
    credential_required: bool = False
    credential_configured: bool = False
    reasoning_effort: str | None = None
    error_code: str | None = None

    @classmethod
    def ready(
        cls,
        workload: AiWorkload,
        mode: SelectionMode,
        count: int,
        route: ModelRoute,
        availability: ConnectionAvailability,
    ) -> "WorkloadSettingsStatus":
        return cls(
            workload, mode, SettingsRouteStatus.READY, count,
            selected_route_id=route.route_id,
            provider_family=route.provider_family.value,
            provider_id=route.provider_id,
            model_id=route.model_id,
            cost_class=route.cost_class.value,
            credential_required=route.credential_ref is not None,
            credential_configured=route.credential_ref is None or route.credential_ref in availability.available_credential_refs,
            reasoning_effort=route.reasoning_effort.value,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "workload": self.workload.value,
            "selection_mode": self.selection_mode.value,
            "status": self.status.value,
            "configured_route_count": self.configured_route_count,
            "selected_route_id": self.selected_route_id,
            "provider_family": self.provider_family,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "cost_class": self.cost_class,
            "credential_required": self.credential_required,
            "credential_configured": self.credential_configured,
            "reasoning_effort": self.reasoning_effort,
            "error_code": self.error_code,
        }


@dataclass(frozen=True, slots=True)
class SettingsPreflightReport:
    profile_id: str
    profile_version: str
    workloads: tuple[WorkloadSettingsStatus, ...]

    @property
    def ready(self) -> bool:
        return all(item.status in {SettingsRouteStatus.READY, SettingsRouteStatus.DISABLED} for item in self.workloads)

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "report_version": "1.0.0",
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "ready": self.ready,
            "workloads": [item.to_dict() for item in self.workloads],
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class AiConnectionSettingsService:
    """Build the complete GUI projection without executing a provider."""

    @staticmethod
    def preflight(
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        *,
        required_capabilities: Mapping[AiWorkload, tuple[str, ...]] | None = None,
    ) -> SettingsPreflightReport:
        required = required_capabilities or {}
        statuses: list[WorkloadSettingsStatus] = []
        for workload in AiWorkload:
            mode = profile.mode_for(workload)
            count = sum(1 for route in profile.routes if route.workload is workload)
            if mode is SelectionMode.DISABLED:
                statuses.append(WorkloadSettingsStatus(workload, mode, SettingsRouteStatus.DISABLED, count))
                continue
            try:
                route = AiConnectionResolver.resolve(
                    profile, workload, availability,
                    required_capabilities=required.get(workload, ()),
                )
            except ProductError as exc:
                statuses.append(WorkloadSettingsStatus(
                    workload, mode, SettingsRouteStatus.BLOCKED, count, error_code=exc.code
                ))
            else:
                statuses.append(WorkloadSettingsStatus.ready(workload, mode, count, route, availability))
        return SettingsPreflightReport(profile.profile_id, profile.profile_version, tuple(statuses))
