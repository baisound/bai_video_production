from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .ai_connections import AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability, ModelRoute, ProviderFamily, ReasoningEffort
from .errors import ProductError, ProductErrorCategory


class CredentialStore(Protocol):
    def resolve(self, credential_ref: str) -> str: ...


class JsonHttpTransport(Protocol):
    def post_json(
        self, url: str, *, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int
    ) -> Mapping[str, Any]: ...


class EnvironmentCredentialStore:
    """Resolve explicitly mapped references without serializing secret values."""

    def __init__(self, reference_to_environment: Mapping[str, str]) -> None:
        self.mapping = dict(reference_to_environment)
        if any(not key.startswith("credential://") or not value or not value.replace("_", "").isalnum() for key, value in self.mapping.items()):
            raise ValueError("credential environment mapping is invalid")

    def resolve(self, credential_ref: str) -> str:
        variable = self.mapping.get(credential_ref)
        value = os.environ.get(variable, "") if variable else ""
        if not value:
            raise ProductError("ERR_PROVIDER_CREDENTIAL_MISSING", "provider credential is unavailable", ProductErrorCategory.AUTHORIZATION, details={"credential_ref": credential_ref})
        return value


class UrllibJsonTransport:
    def __init__(self, *, max_response_bytes: int = 8 * 1024 * 1024) -> None:
        if not 1024 <= max_response_bytes <= 64 * 1024 * 1024:
            raise ValueError("max_response_bytes must be 1 KiB-64 MiB")
        self.max_response_bytes = max_response_bytes

    def post_json(self, url: str, *, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int) -> Mapping[str, Any]:
        if url not in {OpenAiResponsesAdapter.endpoint, AnthropicMessagesAdapter.endpoint, GoogleInteractionsAdapter.endpoint}:
            raise ProductError("ERR_SECURITY_PROVIDER_ENDPOINT", "provider endpoint is not allowlisted", ProductErrorCategory.SECURITY)
        request = Request(url, data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), method="POST", headers=dict(headers))
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
        except HTTPError as exc:
            category = ProductErrorCategory.AUTHORIZATION if exc.code in {401, 403} else ProductErrorCategory.EXTERNAL_DEPENDENCY
            raise ProductError("ERR_PROVIDER_HTTP", "provider returned an HTTP error", category, retryable=exc.code == 429 or 500 <= exc.code < 600, details={"status": exc.code}) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProductError("ERR_PROVIDER_UNREACHABLE", "provider endpoint is unreachable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if len(raw) > self.max_response_bytes:
            raise ProductError("ERR_PROVIDER_RESPONSE_TOO_LARGE", "provider response exceeded the size limit", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROVIDER_INVALID_JSON", "provider returned invalid JSON", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_PROVIDER_INVALID_JSON", "provider response must be a JSON object", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return value


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    prompt: str
    system_instruction: str | None = None
    max_output_tokens: int = 4096
    temperature: float | None = None
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if not self.prompt.strip() or len(self.prompt) > 1_000_000 or "\x00" in self.prompt:
            raise ValueError("prompt must be non-empty bounded text")
        if self.system_instruction is not None and (len(self.system_instruction) > 200_000 or "\x00" in self.system_instruction):
            raise ValueError("system_instruction is invalid")
        if not 1 <= self.max_output_tokens <= 131_072:
            raise ValueError("max_output_tokens must be 1-131072")
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be 0-2")
        if not 1 <= self.timeout_seconds <= 1800:
            raise ValueError("timeout_seconds must be 1-1800")


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    route_id: str
    provider_id: str
    model_id: str
    text: str
    provider_request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class TextProviderAdapter(Protocol):
    family: ProviderFamily

    def generate(self, route: ModelRoute, request: TextGenerationRequest, credential: str | None) -> TextGenerationResult: ...


def _required_credential(route: ModelRoute, credential: str | None) -> str:
    if route.credential_ref is None or not credential:
        raise ProductError("ERR_PROVIDER_CREDENTIAL_MISSING", "provider credential is unavailable", ProductErrorCategory.AUTHORIZATION, details={"route_id": route.route_id})
    return credential


def _text_or_error(value: Any, route: ModelRoute) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductError("ERR_PROVIDER_EMPTY_TEXT", "provider returned no text output", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True, details={"route_id": route.route_id})
    return value


class OpenAiResponsesAdapter:
    family = ProviderFamily.OPENAI
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, transport: JsonHttpTransport) -> None:
        self.transport = transport

    def generate(self, route: ModelRoute, request: TextGenerationRequest, credential: str | None) -> TextGenerationResult:
        key = _required_credential(route, credential)
        body: dict[str, Any] = {"model": route.model_id, "input": request.prompt, "max_output_tokens": request.max_output_tokens, "store": False}
        if request.system_instruction is not None:
            body["instructions"] = request.system_instruction
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if route.reasoning_effort is not ReasoningEffort.NONE:
            body["reasoning"] = {"effort": route.reasoning_effort.value}
        response = self.transport.post_json(self.endpoint, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body=body, timeout_seconds=request.timeout_seconds)
        text = response.get("output_text")
        if not isinstance(text, str):
            blocks = [content.get("text") for item in response.get("output", []) if isinstance(item, dict) for content in item.get("content", []) if isinstance(content, dict) and content.get("type") == "output_text"]
            text = "".join(x for x in blocks if isinstance(x, str))
        usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
        return TextGenerationResult(route.route_id, route.provider_id, route.model_id, _text_or_error(text, route), _optional_str(response.get("id")), _optional_int(usage.get("input_tokens")), _optional_int(usage.get("output_tokens")))


class AnthropicMessagesAdapter:
    family = ProviderFamily.ANTHROPIC
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, transport: JsonHttpTransport, *, api_version: str = "2023-06-01") -> None:
        self.transport, self.api_version = transport, api_version

    def generate(self, route: ModelRoute, request: TextGenerationRequest, credential: str | None) -> TextGenerationResult:
        key = _required_credential(route, credential)
        body: dict[str, Any] = {"model": route.model_id, "max_tokens": request.max_output_tokens, "messages": [{"role": "user", "content": request.prompt}]}
        if request.system_instruction is not None:
            body["system"] = request.system_instruction
        if request.temperature is not None:
            body["temperature"] = request.temperature
        response = self.transport.post_json(self.endpoint, headers={"x-api-key": key, "anthropic-version": self.api_version, "Content-Type": "application/json"}, body=body, timeout_seconds=request.timeout_seconds)
        blocks = response.get("content", [])
        text = "".join(x.get("text", "") for x in blocks if isinstance(x, dict) and x.get("type") == "text") if isinstance(blocks, list) else ""
        usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
        return TextGenerationResult(route.route_id, route.provider_id, route.model_id, _text_or_error(text, route), _optional_str(response.get("id")), _optional_int(usage.get("input_tokens")), _optional_int(usage.get("output_tokens")))


class GoogleInteractionsAdapter:
    family = ProviderFamily.GOOGLE
    endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def __init__(self, transport: JsonHttpTransport) -> None:
        self.transport = transport

    def generate(self, route: ModelRoute, request: TextGenerationRequest, credential: str | None) -> TextGenerationResult:
        key = _required_credential(route, credential)
        config: dict[str, Any] = {"max_output_tokens": request.max_output_tokens}
        if request.temperature is not None:
            config["temperature"] = request.temperature
        if route.reasoning_effort not in {ReasoningEffort.NONE, ReasoningEffort.MAX, ReasoningEffort.XHIGH}:
            config["thinking_level"] = route.reasoning_effort.value
        body: dict[str, Any] = {"model": route.model_id, "input": request.prompt, "store": False, "generation_config": config}
        if request.system_instruction is not None:
            body["system_instruction"] = request.system_instruction
        response = self.transport.post_json(self.endpoint, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, body=body, timeout_seconds=request.timeout_seconds)
        text = response.get("output_text")
        if not isinstance(text, str):
            text = _google_step_text(response.get("steps"))
        usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
        return TextGenerationResult(route.route_id, route.provider_id, route.model_id, _text_or_error(text, route), _optional_str(response.get("id")), _optional_int(usage.get("input_tokens")), _optional_int(usage.get("output_tokens")))


def _google_step_text(steps: Any) -> str:
    if not isinstance(steps, list):
        return ""
    values: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        content = step.get("content", [])
        if isinstance(content, list):
            values.extend(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return "".join(values)


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


class RouteDiagnosticStatus(str, Enum):
    READY = "READY"
    DISABLED = "DISABLED"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    CREDENTIAL_MISSING = "CREDENTIAL_MISSING"
    ADAPTER_MISSING = "ADAPTER_MISSING"


@dataclass(frozen=True, slots=True)
class RouteDiagnostic:
    route_id: str
    workload: AiWorkload
    status: RouteDiagnosticStatus
    provider_family: ProviderFamily
    model_id: str


class AiProviderExecutionService:
    def __init__(self, adapters: tuple[TextProviderAdapter, ...], credentials: CredentialStore) -> None:
        families = [adapter.family for adapter in adapters]
        if len(families) != len(set(families)):
            raise ValueError("duplicate provider adapter family")
        self.adapters = {adapter.family: adapter for adapter in adapters}
        self.credentials = credentials

    def generate_planning_text(self, profile: AiConnectionProfile, availability: ConnectionAvailability, request: TextGenerationRequest) -> TextGenerationResult:
        route = AiConnectionResolver.resolve(profile, AiWorkload.PLANNING, availability, required_capabilities=("TEXT_GENERATION",))
        adapter = self.adapters.get(route.provider_family)
        if adapter is None:
            raise ProductError("ERR_PROVIDER_ADAPTER_MISSING", "selected provider adapter is not installed", ProductErrorCategory.NOT_SUPPORTED, details={"route_id": route.route_id, "provider_family": route.provider_family.value})
        credential = self.credentials.resolve(route.credential_ref) if route.credential_ref else None
        return adapter.generate(route, request, credential)

    def diagnose(self, profile: AiConnectionProfile, availability: ConnectionAvailability) -> tuple[RouteDiagnostic, ...]:
        values: list[RouteDiagnostic] = []
        for route in sorted(profile.routes, key=lambda x: (x.workload.value, x.priority, x.route_id)):
            if not route.enabled:
                status = RouteDiagnosticStatus.DISABLED
            elif route.route_id not in availability.available_route_ids:
                status = RouteDiagnosticStatus.ROUTE_UNAVAILABLE
            elif route.credential_ref and route.credential_ref not in availability.available_credential_refs:
                status = RouteDiagnosticStatus.CREDENTIAL_MISSING
            elif route.workload is AiWorkload.PLANNING and route.provider_family not in self.adapters:
                status = RouteDiagnosticStatus.ADAPTER_MISSING
            else:
                status = RouteDiagnosticStatus.READY
            values.append(RouteDiagnostic(route.route_id, route.workload, status, route.provider_family, route.model_id))
        return tuple(values)
