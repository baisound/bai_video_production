"""Strict local-only Ollama planning candidate boundary for TASK-036 P-UX-2F."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import socket
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily, ReasoningEffort
from .errors import ProductError, ProductErrorCategory


_TAGS_URL = "http://127.0.0.1:11434/api/tags"
_CHAT_URL = "http://127.0.0.1:11434/api/chat"
_MAX_RESPONSE_BYTES = 256 * 1024
_MAX_PROMPT_BYTES = 16 * 1024
_MAX_REQUEST_BYTES = 512 * 1024
_SCENE_ID = re.compile(r"^SC[0-9]{2,3}(?:-[A-Z])?$")
_SECTION_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_SECTION_KIND = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_HOST_PATH = re.compile(
    r"(?:file://|\\\\|(?<![A-Za-z0-9])[A-Za-z]:[^\s]*|(?<![A-Za-z0-9:/])/(?!/)[^\s]*|(?<![A-Za-z0-9])(?:~|\.{1,2})[\\/][^\s]*)",
    re.IGNORECASE,
)


def _closed_object(properties: Mapping[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "properties": dict(properties), "required": list(required)}


_AUDIO_SCHEMA = _closed_object(
    {
        "narration": {"type": "boolean"}, "dialogue": {"type": "boolean"},
        "sound_effects": {"type": "array", "maxItems": 32, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 128}},
        "bgm": {"type": "boolean"}, "sound_logo": {"type": "boolean"},
    },
    ("narration", "dialogue", "sound_effects", "bgm", "sound_logo"),
)
_SCENE_SCHEMA = _closed_object(
    {
        "scene_id": {"type": "string", "pattern": r"^SC[0-9]{2,3}(?:-[A-Z])?$"},
        "start_frame": {"type": "integer", "minimum": 0}, "end_frame": {"type": "integer", "minimum": 1},
        "narrative_role": {"type": "string", "minLength": 1, "maxLength": 256},
        "source_strategy": {"type": "string", "enum": ["REAL_CAPTURE", "REUSE_EXISTING", "COMPOSITE", "AI_GENERATED"]},
        "generation_risk": {"type": "string", "enum": ["A_LOW_TEXT", "B_HEADLINE", "C_DENSE_UI"]},
        "camera_motion": {"type": "string", "enum": ["STATIC", "SUBTLE", "DYNAMIC"]},
        "audio": _AUDIO_SCHEMA, "locked_reference": {"type": "boolean"},
        "post_composite_text": {"type": "boolean"}, "final_hold_frames": {"type": "integer", "minimum": 0},
    },
    ("scene_id", "start_frame", "end_frame", "narrative_role", "source_strategy", "generation_risk", "camera_motion", "audio", "locked_reference", "post_composite_text", "final_hold_frames"),
)
_INTENT_SCHEMA = _closed_object(
    {
        "purpose": {"type": "string", "minLength": 1, "maxLength": 512},
        "audience": {"type": "string", "minLength": 1, "maxLength": 512},
        "platform": {"type": "string", "minLength": 1, "maxLength": 128},
        "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1", "4:3"]},
        "target_duration_seconds": {"type": "integer", "minimum": 1, "maximum": 3600},
        "style_tone": {"type": "string", "minLength": 1, "maxLength": 512},
        "story_message": {"type": "string", "minLength": 1, "maxLength": 4000},
        "language": {"type": "string", "pattern": r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"},
        "free_text": {"type": "string", "maxLength": 16000},
        "rights_constraints": {"type": "array", "maxItems": 32, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 1000}},
    },
    ("purpose", "audience", "platform", "aspect_ratio", "target_duration_seconds", "style_tone", "story_message", "language", "free_text", "rights_constraints"),
)
_SECTION_SCHEMA = _closed_object(
    {
        "section_id": {"type": "string", "pattern": r"^[a-z][a-z0-9_-]{1,63}$"},
        "kind": {"type": "string", "pattern": r"^[A-Z][A-Z0-9_]{1,63}$"},
        "title": {"type": "string", "minLength": 1, "maxLength": 256},
        "body": {"type": "string", "minLength": 1, "maxLength": 64000},
    },
    ("section_id", "kind", "title", "body"),
)
LOCAL_PLANNING_CANDIDATE_SCHEMA = _closed_object(
    {
        "intent": _INTENT_SCHEMA, "proposal_title": {"type": "string", "minLength": 1, "maxLength": 256},
        "timeline_fps": {"type": "integer", "enum": [24, 25, 30, 60]},
        "sections": {"type": "array", "minItems": 1, "maxItems": 12, "items": _SECTION_SCHEMA},
        "scenes": {"type": "array", "minItems": 1, "maxItems": 128, "items": _SCENE_SCHEMA},
        "rights_warnings": {"type": "array", "maxItems": 32, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 1000}},
    },
    ("intent", "proposal_title", "timeline_fps", "sections", "scenes", "rights_warnings"),
)


class LocalOllamaTransport(Protocol):
    def request(self, method: str, url: str, body: bytes | None, timeout_seconds: float) -> bytes: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class UrllibLocalOllamaTransport:
    """HTTP transport that cannot leave the exact Product-owned loopback API surface."""

    def __init__(self, *, max_response_bytes: int = _MAX_RESPONSE_BYTES) -> None:
        if not 1024 <= max_response_bytes <= _MAX_RESPONSE_BYTES:
            raise ValueError("max_response_bytes is invalid")
        self.max_response_bytes = max_response_bytes
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def request(self, method: str, url: str, body: bytes | None, timeout_seconds: float) -> bytes:
        if (method, url) not in {("GET", _TAGS_URL), ("POST", _CHAT_URL)}:
            raise ProductError("ERR_LOCAL_OLLAMA_ENDPOINT_FORBIDDEN", "Ollama request is outside the fixed loopback API", ProductErrorCategory.SECURITY)
        if (method == "GET" and body is not None) or (method == "POST" and (not isinstance(body, bytes) or not body or len(body) > _MAX_REQUEST_BYTES)):
            raise ProductError("ERR_LOCAL_OLLAMA_REQUEST_INVALID", "Ollama request body is invalid", ProductErrorCategory.VALIDATION)
        request = Request(url, data=body, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
        except HTTPError as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_HTTP", "Local Ollama returned an HTTP error", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=500 <= exc.code < 600, details={"status": exc.code}) from exc
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_UNREACHABLE", "Local Ollama is unavailable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if len(raw) > self.max_response_bytes:
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_TOO_LARGE", "Local Ollama response exceeded the size bound", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return raw


@dataclass(frozen=True, slots=True)
class LocalPlanningIntent:
    purpose: str; audience: str; platform: str; aspect_ratio: str; target_duration_seconds: int
    style_tone: str; story_message: str; language: str; free_text: str; rights_constraints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LocalPlanningSection:
    section_id: str; kind: str; title: str; body: str


@dataclass(frozen=True, slots=True)
class LocalPlanningScene:
    scene_id: str; start_frame: int; end_frame: int; narrative_role: str; source_strategy: str
    generation_risk: str; camera_motion: str; narration: bool; dialogue: bool
    sound_effects: tuple[str, ...]; bgm: bool; sound_logo: bool; locked_reference: bool
    post_composite_text: bool; final_hold_frames: int


@dataclass(frozen=True, slots=True)
class LocalPlanningCandidate:
    intent: LocalPlanningIntent; proposal_title: str; timeline_fps: int
    sections: tuple[LocalPlanningSection, ...]; scenes: tuple[LocalPlanningScene, ...]
    rights_warnings: tuple[str, ...]


def validate_local_planning_route(route: ModelRoute) -> None:
    if not (route.enabled and route.workload is AiWorkload.PLANNING and route.provider_family is ProviderFamily.LOCAL_OPEN_SOURCE and route.provider_id.casefold() == "ollama" and route.cost_class is CostClass.LOCAL_FREE_AI and route.capabilities == ("TEXT_GENERATION",) and route.reasoning_effort is ReasoningEffort.NONE and route.credential_ref is None and route.endpoint_ref is None and not route.settings):
        raise ProductError("ERR_LOCAL_OLLAMA_ROUTE_INELIGIBLE", "Planning route is not eligible for local Ollama", ProductErrorCategory.AUTHORIZATION)


def _text(value: Any, *, field: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} is invalid")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} is invalid") from exc
    if "\x00" in value or len(value) > maximum or _HOST_PATH.search(value) or (not allow_empty and not value.strip()):
        raise ValueError(f"{field} is invalid")
    return value if allow_empty else value.strip()


def _string_tuple(value: Any, *, field: str, maximum_items: int, maximum_text: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise ValueError(f"{field} is invalid")
    parsed = tuple(_text(item, field=field, maximum=maximum_text) for item in value)
    if len(parsed) != len(set(parsed)):
        raise ValueError(f"{field} must be unique")
    return parsed


def _exact_object(value: Any, fields: set[str], *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{name} fields are invalid")
    return value


def parse_local_planning_candidate(value: Any) -> LocalPlanningCandidate:
    root = _exact_object(value, {"intent", "proposal_title", "timeline_fps", "sections", "scenes", "rights_warnings"}, name="candidate")
    intent_row = _exact_object(root["intent"], {"purpose", "audience", "platform", "aspect_ratio", "target_duration_seconds", "style_tone", "story_message", "language", "free_text", "rights_constraints"}, name="intent")
    seconds = intent_row["target_duration_seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 3600:
        raise ValueError("target_duration_seconds is invalid")
    aspect, language = intent_row["aspect_ratio"], intent_row["language"]
    if aspect not in {"16:9", "9:16", "1:1", "4:3"} or not isinstance(language, str) or not _LANGUAGE.fullmatch(language):
        raise ValueError("intent enum is invalid")
    intent = LocalPlanningIntent(
        _text(intent_row["purpose"], field="purpose", maximum=512), _text(intent_row["audience"], field="audience", maximum=512),
        _text(intent_row["platform"], field="platform", maximum=128), aspect, seconds,
        _text(intent_row["style_tone"], field="style_tone", maximum=512), _text(intent_row["story_message"], field="story_message", maximum=4000),
        language, _text(intent_row["free_text"], field="free_text", maximum=16000, allow_empty=True),
        _string_tuple(intent_row["rights_constraints"], field="rights_constraints", maximum_items=32, maximum_text=1000),
    )
    fps = root["timeline_fps"]
    if isinstance(fps, bool) or not isinstance(fps, int) or fps not in {24, 25, 30, 60}:
        raise ValueError("timeline_fps is invalid")
    section_rows = root["sections"]
    if not isinstance(section_rows, list) or not 1 <= len(section_rows) <= 12:
        raise ValueError("sections are invalid")
    sections: list[LocalPlanningSection] = []
    for row in section_rows:
        item = _exact_object(row, {"section_id", "kind", "title", "body"}, name="section")
        if not isinstance(item["section_id"], str) or not _SECTION_ID.fullmatch(item["section_id"]) or not isinstance(item["kind"], str) or not _SECTION_KIND.fullmatch(item["kind"]):
            raise ValueError("section identity is invalid")
        sections.append(LocalPlanningSection(item["section_id"], item["kind"], _text(item["title"], field="section title", maximum=256), _text(item["body"], field="section body", maximum=64000)))
    if len({item.section_id for item in sections}) != len(sections):
        raise ValueError("section IDs must be unique")
    target_frames = seconds * fps
    scene_rows = root["scenes"]
    if not isinstance(scene_rows, list) or not 1 <= len(scene_rows) <= 128:
        raise ValueError("scenes are invalid")
    scenes: list[LocalPlanningScene] = []
    cursor = 0
    for row in scene_rows:
        item = _exact_object(row, {"scene_id", "start_frame", "end_frame", "narrative_role", "source_strategy", "generation_risk", "camera_motion", "audio", "locked_reference", "post_composite_text", "final_hold_frames"}, name="scene")
        audio = _exact_object(item["audio"], {"narration", "dialogue", "sound_effects", "bgm", "sound_logo"}, name="audio")
        if not isinstance(item["scene_id"], str) or not _SCENE_ID.fullmatch(item["scene_id"]):
            raise ValueError("scene_id is invalid")
        start, end, hold = item["start_frame"], item["end_frame"], item["final_hold_frames"]
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (start, end, hold)) or start != cursor or end <= start or end > target_frames or hold < 0 or hold >= end - start:
            raise ValueError("scene frame contract is invalid")
        source, risk, camera = item["source_strategy"], item["generation_risk"], item["camera_motion"]
        if source not in {"REAL_CAPTURE", "REUSE_EXISTING", "COMPOSITE", "AI_GENERATED"} or risk not in {"A_LOW_TEXT", "B_HEADLINE", "C_DENSE_UI"} or camera not in {"STATIC", "SUBTLE", "DYNAMIC"}:
            raise ValueError("scene enum is invalid")
        booleans = (audio["narration"], audio["dialogue"], audio["bgm"], audio["sound_logo"], item["locked_reference"], item["post_composite_text"])
        if any(not isinstance(x, bool) for x in booleans):
            raise ValueError("scene booleans are invalid")
        if risk == "C_DENSE_UI" and (not item["locked_reference"] or camera != "STATIC" or not item["post_composite_text"]):
            raise ValueError("dense UI invariant is invalid")
        scenes.append(LocalPlanningScene(
            item["scene_id"], start, end, _text(item["narrative_role"], field="narrative_role", maximum=256), source, risk, camera,
            audio["narration"], audio["dialogue"], _string_tuple(audio["sound_effects"], field="sound_effects", maximum_items=32, maximum_text=128),
            audio["bgm"], audio["sound_logo"], item["locked_reference"], item["post_composite_text"], hold,
        ))
        cursor = end
    if cursor != target_frames or len({item.scene_id for item in scenes}) != len(scenes):
        raise ValueError("scene ledger does not exactly cover the target")
    return LocalPlanningCandidate(intent, _text(root["proposal_title"], field="proposal_title", maximum=256), fps, tuple(sections), tuple(scenes), _string_tuple(root["rights_warnings"], field="rights_warnings", maximum_items=32, maximum_text=1000))


class LocalOllamaPlanningAdapter:
    def __init__(self, route: ModelRoute, transport: LocalOllamaTransport | None = None, *, timeout_seconds: float = 120) -> None:
        validate_local_planning_route(route)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 1 <= timeout_seconds <= 300:
            raise ValueError("timeout_seconds is invalid")
        self.route, self._transport, self._timeout = route, transport or UrllibLocalOllamaTransport(), float(timeout_seconds)

    @staticmethod
    def _json(raw: bytes) -> dict[str, Any]:
        if not isinstance(raw, bytes) or not raw or len(raw) > _MAX_RESPONSE_BYTES:
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama response violates the size bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama response is not UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama response must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return value

    def _require_model(self) -> None:
        document = self._json(self._transport.request("GET", _TAGS_URL, None, self._timeout))
        models = document.get("models")
        if not isinstance(models, list) or any(
            not isinstance(item, dict)
            or not any(isinstance(item.get(key), str) and item.get(key) for key in ("name", "model"))
            for item in models
        ):
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama model inventory is malformed", ProductErrorCategory.DATA_INTEGRITY)
        if not any(self.route.model_id in {item.get("name"), item.get("model")} for item in models):
            raise ProductError("ERR_LOCAL_OLLAMA_MODEL_MISSING", "Configured Ollama model is not installed locally", ProductErrorCategory.EXTERNAL_DEPENDENCY)

    def ready(self) -> bool:
        try:
            self._require_model()
        except ProductError as exc:
            if exc.code == "ERR_LOCAL_OLLAMA_MODEL_MISSING":
                return False
            raise
        return True

    def generate(self, prompt: str) -> LocalPlanningCandidate:
        try:
            prompt_bytes = prompt.encode("utf-8", errors="strict") if isinstance(prompt, str) else b""
        except UnicodeEncodeError as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_PROMPT_INVALID", "Planning prompt is invalid", ProductErrorCategory.VALIDATION) from exc
        if not isinstance(prompt, str) or not prompt.strip() or "\x00" in prompt or len(prompt_bytes) > _MAX_PROMPT_BYTES:
            raise ProductError("ERR_LOCAL_OLLAMA_PROMPT_INVALID", "Planning prompt is invalid", ProductErrorCategory.VALIDATION)
        self._require_model()
        schema_text = json.dumps(LOCAL_PLANNING_CANDIDATE_SCHEMA, ensure_ascii=False, separators=(",", ":"))
        body = {
            "model": self.route.model_id, "stream": False, "think": False, "format": LOCAL_PLANNING_CANDIDATE_SCHEMA,
            "options": {"temperature": 0, "num_predict": 8192},
            "messages": [
                {"role": "system", "content": "Return exactly one JSON object matching this schema. Do not add Markdown or host paths. The final end_frame must equal target_duration_seconds * timeline_fps; scenes start at zero, are contiguous without gaps or overlaps, and end exactly at that product. Dense UI requires locked_reference=true, camera_motion=STATIC, and post_composite_text=true. Schema: " + schema_text},
                {"role": "user", "content": prompt.strip()},
            ],
        }
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > _MAX_REQUEST_BYTES:
            raise ProductError("ERR_LOCAL_OLLAMA_REQUEST_INVALID", "Planning request exceeds the private request bound", ProductErrorCategory.VALIDATION)
        envelope = self._json(self._transport.request("POST", _CHAT_URL, encoded, self._timeout))
        message = envelope.get("message")
        raw = message.get("content") if isinstance(message, dict) else None
        try:
            raw_bytes = raw.encode("utf-8", errors="strict") if isinstance(raw, str) else b""
        except UnicodeEncodeError as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama chat content is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(raw, str) or not raw or len(raw_bytes) > _MAX_RESPONSE_BYTES:
            raise ProductError("ERR_LOCAL_OLLAMA_RESPONSE_INVALID", "Ollama chat content is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            return parse_local_planning_candidate(json.loads(raw))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_LOCAL_OLLAMA_CANDIDATE_INVALID", "Ollama candidate violates the closed planning schema", ProductErrorCategory.DATA_INTEGRITY) from exc
