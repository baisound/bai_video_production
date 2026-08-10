from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .ai_connections import AiWorkload, ModelRoute, ProviderFamily
from .errors import ProductError, ProductErrorCategory
from .provider_execution import JsonHttpTransport


_SAFE_EXTERNAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


@dataclass(frozen=True, slots=True)
class BinaryResponse:
    data: bytes
    content_type: str
    provider_request_id: str | None = None


class BinaryHttpTransport(Protocol):
    def post_binary(self, url: str, *, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int) -> BinaryResponse: ...


class UrllibBinaryTransport:
    """Bounded binary transport restricted to reviewed media-provider origins."""

    def __init__(self, *, max_response_bytes: int = 256 * 1024 * 1024) -> None:
        if not 1024 <= max_response_bytes <= 1024 * 1024 * 1024:
            raise ValueError("max_response_bytes must be 1 KiB-1 GiB")
        self.max_response_bytes = max_response_bytes

    def post_binary(self, url: str, *, headers: Mapping[str, str], body: Mapping[str, Any], timeout_seconds: int) -> BinaryResponse:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "api.elevenlabs.io" or not parsed.path.startswith("/v1/") or parsed.username or parsed.password:
            raise ProductError("ERR_SECURITY_MEDIA_PROVIDER_ENDPOINT", "media provider endpoint is not allowlisted", ProductErrorCategory.SECURITY)
        request = Request(url, data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), method="POST", headers=dict(headers))
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
                content_type = response.headers.get_content_type()
                request_id = response.headers.get("request-id")
        except HTTPError as exc:
            category = ProductErrorCategory.AUTHORIZATION if exc.code in {401, 403} else ProductErrorCategory.EXTERNAL_DEPENDENCY
            raise ProductError("ERR_MEDIA_PROVIDER_HTTP", "media provider returned an HTTP error", category, retryable=exc.code == 429 or 500 <= exc.code < 600, details={"status": exc.code}) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProductError("ERR_MEDIA_PROVIDER_UNREACHABLE", "media provider endpoint is unreachable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if len(raw) > self.max_response_bytes:
            raise ProductError("ERR_MEDIA_PROVIDER_RESPONSE_TOO_LARGE", "media provider response exceeded the size limit", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        if not raw:
            raise ProductError("ERR_MEDIA_PROVIDER_EMPTY", "media provider returned an empty file", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True)
        return BinaryResponse(raw, content_type, request_id)


@dataclass(frozen=True, slots=True)
class ElevenLabsTtsRequest:
    text: str
    voice_id: str
    rights_authorization_ref: str
    output_format: str = "mp3_44100_128"
    language_code: str | None = None
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        _bounded_text(self.text, "text", 100_000)
        _safe_id(self.voice_id, "voice_id")
        _authorization_ref(self.rights_authorization_ref)
        _safe_id(self.output_format, "output_format")


@dataclass(frozen=True, slots=True)
class ElevenLabsSoundEffectRequest:
    prompt: str
    rights_authorization_ref: str
    duration_seconds: float | None = None
    loop: bool = False
    output_format: str = "mp3_44100_128"
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        _bounded_text(self.prompt, "prompt", 10_000)
        _authorization_ref(self.rights_authorization_ref)
        if self.duration_seconds is not None and not 0.5 <= self.duration_seconds <= 30:
            raise ValueError("duration_seconds must be 0.5-30")
        _safe_id(self.output_format, "output_format")


@dataclass(frozen=True, slots=True)
class ElevenLabsMusicRequest:
    prompt: str
    rights_authorization_ref: str
    duration_ms: int | None = None
    instrumental: bool = True
    timeout_seconds: int = 1800

    def __post_init__(self) -> None:
        _bounded_text(self.prompt, "prompt", 4100)
        _authorization_ref(self.rights_authorization_ref)
        if self.duration_ms is not None and not 3000 <= self.duration_ms <= 600_000:
            raise ValueError("duration_ms must be 3000-600000")


class ElevenLabsMediaAdapter:
    family = ProviderFamily.ELEVENLABS
    origin = "https://api.elevenlabs.io"

    def __init__(self, transport: BinaryHttpTransport) -> None:
        self.transport = transport

    def text_to_speech(self, route: ModelRoute, request: ElevenLabsTtsRequest, credential: str) -> BinaryResponse:
        _route(route, ProviderFamily.ELEVENLABS, AiWorkload.AUDIO, "TTS")
        body: dict[str, Any] = {"text": request.text, "model_id": route.model_id}
        if request.language_code:
            body["language_code"] = request.language_code
        url = f"{self.origin}/v1/text-to-speech/{quote(request.voice_id, safe='')}?output_format={quote(request.output_format, safe='')}"
        return self.transport.post_binary(url, headers=_eleven_headers(credential), body=body, timeout_seconds=request.timeout_seconds)

    def sound_effect(self, route: ModelRoute, request: ElevenLabsSoundEffectRequest, credential: str) -> BinaryResponse:
        _route(route, ProviderFamily.ELEVENLABS, AiWorkload.AUDIO, "SFX")
        body: dict[str, Any] = {"text": request.prompt, "loop": request.loop, "model_id": route.model_id}
        if request.duration_seconds is not None:
            body["duration_seconds"] = request.duration_seconds
        url = f"{self.origin}/v1/sound-generation?output_format={quote(request.output_format, safe='')}"
        return self.transport.post_binary(url, headers=_eleven_headers(credential), body=body, timeout_seconds=request.timeout_seconds)

    def music(self, route: ModelRoute, request: ElevenLabsMusicRequest, credential: str) -> BinaryResponse:
        _route(route, ProviderFamily.ELEVENLABS, AiWorkload.MUSIC, "MUSIC_GENERATION")
        body: dict[str, Any] = {"prompt": request.prompt, "model_id": route.model_id, "force_instrumental": request.instrumental}
        if request.duration_ms is not None:
            body["music_length_ms"] = request.duration_ms
        return self.transport.post_binary(f"{self.origin}/v1/music", headers=_eleven_headers(credential), body=body, timeout_seconds=request.timeout_seconds)


@dataclass(frozen=True, slots=True)
class SunoMusicRequest:
    prompt: str
    title: str
    style: str
    callback_url: str
    rights_authorization_ref: str
    instrumental: bool = True
    custom_mode: bool = True
    duration_seconds: int | None = None
    negative_tags: str | None = None
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        _bounded_text(self.prompt, "prompt", 5000)
        _bounded_text(self.title, "title", 100)
        _bounded_text(self.style, "style", 1000)
        _authorization_ref(self.rights_authorization_ref)
        parsed = urlparse(self.callback_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("callback_url must be a public HTTPS URL without credentials or fragment")
        if self.duration_seconds is not None and not 10 <= self.duration_seconds <= 600:
            raise ValueError("duration_seconds must be 10-600")
        if self.negative_tags is not None:
            _bounded_text(self.negative_tags, "negative_tags", 1000)


@dataclass(frozen=True, slots=True)
class ExternalMediaJob:
    provider_family: ProviderFamily
    route_id: str
    provider_task_id: str
    state: str = "SUBMITTED"


class SunoApiMusicAdapter:
    family = ProviderFamily.SUNO_API
    endpoint = "https://api.sunoapi.org/api/v1/generate"

    def __init__(self, transport: JsonHttpTransport) -> None:
        self.transport = transport

    def submit(self, route: ModelRoute, request: SunoMusicRequest, credential: str) -> ExternalMediaJob:
        _route(route, ProviderFamily.SUNO_API, AiWorkload.MUSIC, "MUSIC_GENERATION")
        body: dict[str, Any] = {"customMode": request.custom_mode, "instrumental": request.instrumental, "model": route.model_id, "callBackUrl": request.callback_url, "prompt": request.prompt, "style": request.style, "title": request.title}
        if request.duration_seconds is not None:
            body["duration"] = request.duration_seconds
        if request.negative_tags:
            body["negativeTags"] = request.negative_tags
        response = self.transport.post_json(self.endpoint, headers={"Authorization": f"Bearer {credential}", "Content-Type": "application/json"}, body=body, timeout_seconds=request.timeout_seconds)
        data = response.get("data")
        task_id = data.get("taskId") if isinstance(data, dict) else None
        if response.get("code") != 200 or not isinstance(task_id, str) or not task_id:
            raise ProductError("ERR_PROVIDER_SUNO_SUBMIT", "SunoAPI did not return a generation task ID", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True)
        return ExternalMediaJob(self.family, route.route_id, task_id)


class ProviderIntegrationStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    LOCAL_RUNTIME = "LOCAL_RUNTIME"
    PLANNED_ADAPTER = "PLANNED_ADAPTER"


@dataclass(frozen=True, slots=True)
class ProviderCatalogEntry:
    family: ProviderFamily
    workloads: tuple[AiWorkload, ...]
    capabilities: tuple[str, ...]
    status: ProviderIntegrationStatus


def builtin_media_provider_catalog() -> tuple[ProviderCatalogEntry, ...]:
    return (
        ProviderCatalogEntry(ProviderFamily.ELEVENLABS, (AiWorkload.AUDIO, AiWorkload.MUSIC), ("TTS", "SFX", "MUSIC_GENERATION"), ProviderIntegrationStatus.IMPLEMENTED),
        ProviderCatalogEntry(ProviderFamily.SUNO_API, (AiWorkload.MUSIC,), ("MUSIC_GENERATION",), ProviderIntegrationStatus.IMPLEMENTED),
        ProviderCatalogEntry(ProviderFamily.COMFYUI, (AiWorkload.IMAGE, AiWorkload.VIDEO), ("TEXT_TO_IMAGE", "IMAGE_TO_VIDEO"), ProviderIntegrationStatus.LOCAL_RUNTIME),
        ProviderCatalogEntry(ProviderFamily.AUDACITY_OPENVINO, (AiWorkload.AUDIO,), ("DENOISE", "SEPARATION"), ProviderIntegrationStatus.LOCAL_RUNTIME),
        ProviderCatalogEntry(ProviderFamily.RUNWAY, (AiWorkload.IMAGE, AiWorkload.VIDEO, AiWorkload.AUDIO), ("TEXT_TO_IMAGE", "TEXT_TO_VIDEO", "IMAGE_TO_VIDEO", "SFX", "TTS"), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.LUMA, (AiWorkload.IMAGE, AiWorkload.VIDEO), ("TEXT_TO_IMAGE", "TEXT_TO_VIDEO", "IMAGE_TO_VIDEO"), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.STABILITY_AI, (AiWorkload.IMAGE, AiWorkload.VIDEO, AiWorkload.AUDIO), ("TEXT_TO_IMAGE", "IMAGE_TO_VIDEO", "SFX"), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.REPLICATE, (AiWorkload.IMAGE, AiWorkload.VIDEO, AiWorkload.AUDIO, AiWorkload.MUSIC), ("MODEL_HOSTING",), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.FAL_AI, (AiWorkload.IMAGE, AiWorkload.VIDEO, AiWorkload.AUDIO), ("MODEL_HOSTING",), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.MINIMAX, (AiWorkload.VIDEO, AiWorkload.AUDIO, AiWorkload.MUSIC), ("TEXT_TO_VIDEO", "IMAGE_TO_VIDEO", "TTS", "MUSIC_GENERATION"), ProviderIntegrationStatus.PLANNED_ADAPTER),
        ProviderCatalogEntry(ProviderFamily.KLING, (AiWorkload.IMAGE, AiWorkload.VIDEO), ("TEXT_TO_IMAGE", "TEXT_TO_VIDEO", "IMAGE_TO_VIDEO"), ProviderIntegrationStatus.PLANNED_ADAPTER),
    )


def _route(route: ModelRoute, family: ProviderFamily, workload: AiWorkload, capability: str) -> None:
    if route.provider_family is not family or route.workload is not workload or capability not in route.capabilities:
        raise ProductError("ERR_PROVIDER_ROUTE_INCOMPATIBLE", "media provider route does not support this operation", ProductErrorCategory.NOT_SUPPORTED, details={"route_id": route.route_id, "required_capability": capability})


def _eleven_headers(credential: str) -> dict[str, str]:
    if not credential:
        raise ProductError("ERR_PROVIDER_CREDENTIAL_MISSING", "ElevenLabs credential is unavailable", ProductErrorCategory.AUTHORIZATION)
    return {"xi-api-key": credential, "Content-Type": "application/json"}


def _safe_id(value: str, name: str) -> None:
    if not _SAFE_EXTERNAL_ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")


def _bounded_text(value: str, name: str, maximum: int) -> None:
    if not value.strip() or "\x00" in value or len(value) > maximum:
        raise ValueError(f"{name} must be non-empty bounded text")


def _authorization_ref(value: str) -> None:
    if not value.startswith("authorization://") or len(value) > 500 or "\x00" in value:
        raise ValueError("rights_authorization_ref must use authorization://")
