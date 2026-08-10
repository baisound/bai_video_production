from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Protocol

from .ai_connections import AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability, ModelRoute, ProviderFamily
from .errors import ProductError, ProductErrorCategory
from .provider_execution import CredentialStore, TextGenerationRequest, TextGenerationResult, TextProviderAdapter


_CAPABILITY = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_FORBIDDEN_KEYS = {"api_key", "apikey", "authorization", "credential", "password", "secret", "token"}


def _validate_payload(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("capability payload keys must be strings")
            normalized = key.casefold().replace("-", "_")
            if normalized in _FORBIDDEN_KEYS:
                raise ValueError(f"secret-bearing capability payload key is forbidden at {'.'.join(path + (key,))}")
            _validate_payload(child, path + (key,))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_payload(child, path + (str(index),))
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("capability payload must contain JSON-compatible values")


@dataclass(frozen=True, slots=True)
class CapabilityExecutionRequest:
    workload: AiWorkload
    capability: str
    payload: Mapping[str, Any]
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if not _CAPABILITY.fullmatch(self.capability):
            raise ValueError("capability must be an uppercase safe identifier")
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be 1-3600")
        _validate_payload(self.payload)


@dataclass(frozen=True, slots=True)
class CapabilityExecutionResult:
    route_id: str
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    workload: AiWorkload
    capability: str
    output_kind: str
    output: Mapping[str, Any] = field(default_factory=dict)
    provider_operation_id: str | None = None

    def __post_init__(self) -> None:
        if not _CAPABILITY.fullmatch(self.capability) or not _CAPABILITY.fullmatch(self.output_kind):
            raise ValueError("capability and output_kind must be uppercase safe identifiers")
        _validate_payload(self.output)


class CapabilityAdapter(Protocol):
    provider_family: ProviderFamily
    capabilities: frozenset[str]

    def execute(self, route: ModelRoute, request: CapabilityExecutionRequest, credential: str | None) -> CapabilityExecutionResult: ...


@dataclass(frozen=True, slots=True)
class ModelCapabilityDescriptor:
    provider_family: ProviderFamily
    provider_id: str
    model_id: str
    capabilities: frozenset[str]
    workloads: frozenset[AiWorkload]
    catalog_version: str = "1"

    def __post_init__(self) -> None:
        if not _MODEL_ID.fullmatch(self.provider_id) or not _MODEL_ID.fullmatch(self.model_id):
            raise ValueError("provider_id and model_id must be safe identifiers")
        if not self.capabilities or any(not _CAPABILITY.fullmatch(x) for x in self.capabilities):
            raise ValueError("capabilities must be non-empty uppercase identifiers")
        if not self.workloads:
            raise ValueError("workloads must not be empty")

    def supports(self, workload: AiWorkload, capability: str) -> bool:
        return workload in self.workloads and capability in self.capabilities


class ModelCapabilityCatalog:
    """Model-level truth; provider family alone never determines a workload."""

    def __init__(self, descriptors: tuple[ModelCapabilityDescriptor, ...]) -> None:
        keys = [(x.provider_family, x.provider_id, x.model_id) for x in descriptors]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate model capability descriptor")
        self._values = {key: value for key, value in zip(keys, descriptors)}

    def descriptor_for(self, route: ModelRoute) -> ModelCapabilityDescriptor:
        value = self._values.get((route.provider_family, route.provider_id, route.model_id))
        if value is None:
            raise ProductError("ERR_PROVIDER_MODEL_NOT_CATALOGED", "configured model is not present in the capability catalog", ProductErrorCategory.NOT_SUPPORTED, details={"provider_family": route.provider_family.value, "provider_id": route.provider_id, "model_id": route.model_id})
        return value

    def assert_route_supported(self, route: ModelRoute, capability: str) -> None:
        descriptor = self.descriptor_for(route)
        if not descriptor.supports(route.workload, capability):
            raise ProductError("ERR_PROVIDER_MODEL_CAPABILITY_UNSUPPORTED", "configured model does not support the requested workload and capability", ProductErrorCategory.NOT_SUPPORTED, details={"route_id": route.route_id, "workload": route.workload.value, "capability": capability})


class CapabilityExecutionRegistry:
    def __init__(self, adapters: tuple[CapabilityAdapter, ...], credentials: CredentialStore, *, catalog: ModelCapabilityCatalog | None = None) -> None:
        bindings: dict[tuple[ProviderFamily, str], CapabilityAdapter] = {}
        for adapter in adapters:
            if not adapter.capabilities or any(not _CAPABILITY.fullmatch(x) for x in adapter.capabilities):
                raise ValueError("adapter capabilities are invalid")
            for capability in adapter.capabilities:
                key = (adapter.provider_family, capability)
                if key in bindings:
                    raise ValueError("duplicate provider capability adapter binding")
                bindings[key] = adapter
        self._bindings = bindings
        self.credentials = credentials
        self.catalog = catalog

    def execute(self, profile: AiConnectionProfile, availability: ConnectionAvailability, request: CapabilityExecutionRequest) -> CapabilityExecutionResult:
        route = AiConnectionResolver.resolve(profile, request.workload, availability, required_capabilities=(request.capability,))
        if self.catalog is not None:
            self.catalog.assert_route_supported(route, request.capability)
        adapter = self._bindings.get((route.provider_family, request.capability))
        if adapter is None:
            raise ProductError("ERR_PROVIDER_CAPABILITY_ADAPTER_MISSING", "selected provider capability adapter is not installed", ProductErrorCategory.NOT_SUPPORTED, details={"route_id": route.route_id, "provider_family": route.provider_family.value, "capability": request.capability})
        credential = self.credentials.resolve(route.credential_ref) if route.credential_ref else None
        result = adapter.execute(route, request, credential)
        if result.route_id != route.route_id or result.workload is not request.workload or result.capability != request.capability or result.model_id != route.model_id:
            raise ProductError("ERR_PROVIDER_CAPABILITY_RESULT_MISMATCH", "provider adapter returned a result for a different route, model, workload, or capability", ProductErrorCategory.DATA_INTEGRITY)
        return result

    def installed_capabilities(self, family: ProviderFamily) -> frozenset[str]:
        return frozenset(capability for provider, capability in self._bindings if provider is family)


class TextCapabilityAdapter:
    """Expose any text-capable provider model to declared workloads/capabilities."""

    def __init__(self, adapter: TextProviderAdapter, capabilities: frozenset[str] = frozenset({"TEXT_GENERATION", "PLANNING", "SCRIPT"})) -> None:
        self.adapter = adapter
        self.provider_family = adapter.family
        self.capabilities = capabilities

    def execute(self, route: ModelRoute, request: CapabilityExecutionRequest, credential: str | None) -> CapabilityExecutionResult:
        prompt = request.payload.get("prompt")
        if not isinstance(prompt, str):
            raise ProductError("ERR_INPUT_CAPABILITY_PROMPT", "text capability requires a prompt", ProductErrorCategory.VALIDATION)
        generation = TextGenerationRequest(
            prompt=prompt,
            system_instruction=request.payload.get("system_instruction") if isinstance(request.payload.get("system_instruction"), str) else None,
            max_output_tokens=request.payload.get("max_output_tokens", 4096),
            temperature=request.payload.get("temperature"),
            timeout_seconds=request.timeout_seconds,
        )
        result: TextGenerationResult = self.adapter.generate(route, generation, credential)
        output: dict[str, Any] = {"text": result.text}
        if result.input_tokens is not None:
            output["input_tokens"] = result.input_tokens
        if result.output_tokens is not None:
            output["output_tokens"] = result.output_tokens
        return CapabilityExecutionResult(route.route_id, route.provider_family, route.provider_id, route.model_id, request.workload, request.capability, "TEXT", output, result.provider_request_id)
