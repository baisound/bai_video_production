from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Iterable

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


class AiWorkload(str, Enum):
    PLANNING = "PLANNING"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    MUSIC = "MUSIC"


class SelectionMode(str, Enum):
    AI = "AI"
    FREE = "FREE"
    AUTO = "AUTO"
    OFFLINE_ONLY = "OFFLINE_ONLY"
    DISABLED = "DISABLED"


class ProviderFamily(str, Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    ELEVENLABS = "ELEVENLABS"
    SUNO_API = "SUNO_API"
    RUNWAY = "RUNWAY"
    LUMA = "LUMA"
    STABILITY_AI = "STABILITY_AI"
    REPLICATE = "REPLICATE"
    FAL_AI = "FAL_AI"
    MINIMAX = "MINIMAX"
    KLING = "KLING"
    COMFYUI = "COMFYUI"
    AUDACITY_OPENVINO = "AUDACITY_OPENVINO"
    LOCAL_OPEN_SOURCE = "LOCAL_OPEN_SOURCE"
    NON_AI_LIBRARY = "NON_AI_LIBRARY"
    OTHER = "OTHER"


class CostClass(str, Enum):
    CLOUD_PAID_AI = "CLOUD_PAID_AI"
    CLOUD_FREE_TIER_AI = "CLOUD_FREE_TIER_AI"
    LOCAL_FREE_AI = "LOCAL_FREE_AI"
    LOCAL_LICENSED_AI = "LOCAL_LICENSED_AI"
    NON_AI_FREE = "NON_AI_FREE"


class ReasoningEffort(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_CREDENTIAL_REF = re.compile(r"^credential://[a-z0-9][a-z0-9._/-]{0,127}$")
_FORBIDDEN_SETTING_KEYS = {"api_key", "apikey", "access_token", "token", "secret", "password", "credential"}


def _validate_settings(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in _FORBIDDEN_SETTING_KEYS:
                raise ValueError(f"secret setting is forbidden at {'.'.join(path + (str(key),))}")
            _validate_settings(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_settings(child, path + (str(index),))
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("route settings must contain JSON-compatible values")


@dataclass(frozen=True, slots=True)
class ModelRoute:
    route_id: str
    workload: AiWorkload
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    cost_class: CostClass
    priority: int = 100
    reasoning_effort: ReasoningEffort = ReasoningEffort.NONE
    credential_ref: str | None = None
    endpoint_ref: str | None = None
    capabilities: tuple[str, ...] = ()
    settings: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        for name, value in (("route_id", self.route_id), ("provider_id", self.provider_id), ("model_id", self.model_id)):
            if not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if not 0 <= self.priority <= 10000:
            raise ValueError("priority must be 0-10000")
        if self.credential_ref is not None and not _CREDENTIAL_REF.fullmatch(self.credential_ref):
            raise ValueError("credential_ref must use credential:// and contain no secret")
        if self.endpoint_ref is not None and not self.endpoint_ref.startswith("endpoint://"):
            raise ValueError("endpoint_ref must use endpoint://")
        if len(set(self.capabilities)) != len(self.capabilities) or any(not _SAFE_ID.fullmatch(x) for x in self.capabilities):
            raise ValueError("capabilities must be unique safe identifiers")
        _validate_settings(self.settings)
        if self.workload is not AiWorkload.PLANNING and self.reasoning_effort is not ReasoningEffort.NONE:
            raise ValueError("reasoning_effort is supported only for PLANNING routes")
        if self.provider_family is ProviderFamily.NON_AI_LIBRARY and self.cost_class is not CostClass.NON_AI_FREE:
            raise ValueError("NON_AI_LIBRARY routes must use NON_AI_FREE")

    @property
    def is_ai(self) -> bool:
        return self.provider_family is not ProviderFamily.NON_AI_LIBRARY

    @property
    def is_free(self) -> bool:
        return self.cost_class in {
            CostClass.CLOUD_FREE_TIER_AI,
            CostClass.LOCAL_FREE_AI,
            CostClass.NON_AI_FREE,
        }

    @property
    def is_offline(self) -> bool:
        return self.cost_class in {
            CostClass.LOCAL_FREE_AI,
            CostClass.LOCAL_LICENSED_AI,
            CostClass.NON_AI_FREE,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "workload": self.workload.value,
            "provider_family": self.provider_family.value,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "cost_class": self.cost_class.value,
            "priority": self.priority,
            "reasoning_effort": self.reasoning_effort.value,
            "credential_ref": self.credential_ref,
            "endpoint_ref": self.endpoint_ref,
            "capabilities": list(self.capabilities),
            "settings": self.settings,
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class AiConnectionProfile:
    profile_id: str
    profile_version: str
    default_mode: SelectionMode
    routes: tuple[ModelRoute, ...]
    workload_modes: dict[AiWorkload, SelectionMode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.profile_id):
            raise ValueError("profile_id is invalid")
        if not self.profile_version or len(self.profile_version) > 64:
            raise ValueError("profile_version is invalid")
        route_ids = [route.route_id for route in self.routes]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("duplicate route_id")
        for workload, mode in self.workload_modes.items():
            if not isinstance(workload, AiWorkload) or not isinstance(mode, SelectionMode):
                raise ValueError("workload_modes must use AiWorkload and SelectionMode")

    def mode_for(self, workload: AiWorkload) -> SelectionMode:
        return self.workload_modes.get(workload, self.default_mode)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "default_mode": self.default_mode.value,
            "workload_modes": {key.value: value.value for key, value in sorted(self.workload_modes.items(), key=lambda x: x[0].value)},
            "routes": [route.to_dict() for route in sorted(self.routes, key=lambda x: (x.workload.value, x.priority, x.route_id))],
        }
        body["profile_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, document: dict[str, Any], *, verify_checksum: bool = True) -> "AiConnectionProfile":
        """Load a persisted profile and reject tampered or unsupported documents."""
        if document.get("schema_version") != "1.0.0":
            raise ValueError("unsupported AI connection profile schema_version")
        expected = document.get("profile_sha256")
        body = {key: value for key, value in document.items() if key != "profile_sha256"}
        if verify_checksum and expected != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("AI connection profile checksum mismatch")
        routes = tuple(
            ModelRoute(
                route_id=item["route_id"],
                workload=AiWorkload(item["workload"]),
                provider_family=ProviderFamily(item["provider_family"]),
                provider_id=item["provider_id"],
                model_id=item["model_id"],
                cost_class=CostClass(item["cost_class"]),
                priority=item.get("priority", 100),
                reasoning_effort=ReasoningEffort(item.get("reasoning_effort", "none")),
                credential_ref=item.get("credential_ref"),
                endpoint_ref=item.get("endpoint_ref"),
                capabilities=tuple(item.get("capabilities", ())),
                settings=item.get("settings", {}),
                enabled=item.get("enabled", True),
            )
            for item in document["routes"]
        )
        return cls(
            profile_id=document["profile_id"],
            profile_version=document["profile_version"],
            default_mode=SelectionMode(document["default_mode"]),
            routes=routes,
            workload_modes={AiWorkload(key): SelectionMode(value) for key, value in document.get("workload_modes", {}).items()},
        )


@dataclass(frozen=True, slots=True)
class ConnectionAvailability:
    available_route_ids: frozenset[str]
    available_credential_refs: frozenset[str] = frozenset()


class AiConnectionResolver:
    """Resolve the configured route; adapters execute only the returned choice."""

    @staticmethod
    def resolve(
        profile: AiConnectionProfile,
        workload: AiWorkload,
        availability: ConnectionAvailability,
        *,
        required_capabilities: Iterable[str] = (),
    ) -> ModelRoute:
        mode = profile.mode_for(workload)
        if mode is SelectionMode.DISABLED:
            raise ProductError(
                "ERR_PROVIDER_WORKLOAD_DISABLED",
                f"{workload.value} provider routing is disabled",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        required = frozenset(required_capabilities)
        candidates = sorted(
            (route for route in profile.routes if route.workload is workload),
            key=lambda route: (route.priority, route.route_id),
        )
        eligible: list[ModelRoute] = []
        for route in candidates:
            if not route.enabled or route.route_id not in availability.available_route_ids:
                continue
            if route.credential_ref and route.credential_ref not in availability.available_credential_refs:
                continue
            if not required.issubset(route.capabilities):
                continue
            if mode is SelectionMode.AI and not route.is_ai:
                continue
            if mode is SelectionMode.FREE and not route.is_free:
                continue
            if mode is SelectionMode.OFFLINE_ONLY and not route.is_offline:
                continue
            eligible.append(route)
        if not eligible:
            raise ProductError(
                "ERR_PROVIDER_ROUTE_UNAVAILABLE",
                f"no eligible {workload.value} provider route is available",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=True,
                details={
                    "workload": workload.value,
                    "selection_mode": mode.value,
                    "required_capabilities": sorted(required),
                    "configured_route_ids": [route.route_id for route in candidates],
                },
            )
        return eligible[0]
