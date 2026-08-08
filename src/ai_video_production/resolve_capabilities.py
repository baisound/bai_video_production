from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import platform
import re
import time
from typing import Any, Callable, Iterable

from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id
from .serialization import utc_now_iso


class CapabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNSUPPORTED = "UNSUPPORTED"
    PROBE_REQUIRED = "PROBE_REQUIRED"


class ProbeMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    SANDBOX_MUTATION = "SANDBOX_MUTATION"


_SANDBOX_PREFIX = "BAI_CAPABILITY_PROBE_"
_SECRET_KEY = re.compile(r"(?:secret|token|password|api[_-]?key|credential|authorization)", re.I)
_PATHISH = re.compile(r"^(?:[A-Za-z]:[\\/]|/home/|/Users/|\\\\)")


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    capability_id: str
    area: str
    object_name: str
    method_candidates: tuple[str, ...]
    safe_read_call: bool
    fallback: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    capability_id: str
    area: str
    status: CapabilityStatus
    object_name: str
    method_candidates: tuple[str, ...]
    observed_methods: tuple[str, ...] = ()
    elapsed_ms: float | None = None
    return_kind: str | None = None
    studio_requirement: str = "UNCONFIRMED"
    fallback: str = ""
    notes: tuple[str, ...] = ()
    error_code: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "area": self.area,
            "status": self.status.value,
            "object_name": self.object_name,
            "method_candidates": list(self.method_candidates),
            "observed_methods": list(self.observed_methods),
            "elapsed_ms": self.elapsed_ms,
            "return_kind": self.return_kind,
            "studio_requirement": self.studio_requirement,
            "fallback": self.fallback,
            "notes": list(self.notes),
            "error_code": self.error_code,
            "error_type": self.error_type,
        }


CAPABILITY_SPECS: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("resolve.connection", "HEALTH", "resolve", (), True, "Manual Resolve launch/check"),
    CapabilitySpec("resolve.version", "HEALTH", "resolve", ("GetVersionString", "GetVersion"), True, "Record version manually"),
    CapabilitySpec("resolve.product_name", "HEALTH", "resolve", ("GetProductName",), True, "Record edition manually"),
    CapabilitySpec("project_manager.access", "PROJECT", "resolve", ("GetProjectManager",), True, "Manual Project selection"),
    CapabilitySpec("project.current", "PROJECT", "project_manager", ("GetCurrentProject",), True, "Manual Project selection"),
    CapabilitySpec("project.create", "PROJECT", "project_manager", ("CreateProject",), False, "Create Project manually"),
    CapabilitySpec("project.open", "PROJECT", "project_manager", ("LoadProject",), False, "Open Project manually"),
    CapabilitySpec("project.save", "PROJECT", "project_manager", ("SaveProject",), False, "Save Project manually"),
    CapabilitySpec("project.snapshot", "PROJECT", "project_manager", ("ExportProject",), False, "Export/backup Project manually"),
    CapabilitySpec("media_pool.access", "MEDIA", "project", ("GetMediaPool",), True, "Use Media page manually"),
    CapabilitySpec("media.import", "MEDIA", "media_pool", ("ImportMedia",), False, "Import media manually"),
    CapabilitySpec("media.relink", "MEDIA", "media_pool", ("RelinkClips",), False, "Relink media manually"),
    CapabilitySpec("bin.ensure", "MEDIA", "media_pool", ("AddSubFolder",), False, "Create bins manually"),
    CapabilitySpec("timeline.current", "TIMELINE", "project", ("GetCurrentTimeline",), True, "Select Timeline manually"),
    CapabilitySpec("timeline.create", "TIMELINE", "media_pool", ("CreateEmptyTimeline", "CreateTimelineFromClips"), False, "Create Timeline manually"),
    CapabilitySpec("timeline.build", "TIMELINE", "media_pool", ("AppendToTimeline",), False, "Place clips manually"),
    CapabilitySpec("timeline.markers", "TIMELINE", "timeline", ("AddMarker",), False, "Place review markers manually"),
    CapabilitySpec(
        "timeline.subtitles",
        "TIMELINE",
        "timeline",
        ("ImportIntoTimeline",),
        False,
        "Import SRT or add subtitles manually",
        "Product operation may require a version-specific path; method presence is not semantic proof.",
    ),
    CapabilitySpec("render.settings", "RENDER", "project", ("SetRenderSettings",), False, "Configure Deliver page manually"),
    CapabilitySpec("render.submit", "RENDER", "project", ("AddRenderJob",), False, "Add Render Queue job manually"),
    CapabilitySpec("render.start", "RENDER", "project", ("StartRendering",), False, "Start render manually"),
    CapabilitySpec("render.status", "RENDER", "project", ("GetRenderJobStatus", "IsRenderingInProgress"), False, "Inspect Render Queue manually"),
    CapabilitySpec("render.cancel", "RENDER", "project", ("StopRendering",), False, "Cancel render manually"),
)

_SAFE_QUERY_METHODS = {
    "GetVersionString",
    "GetVersion",
    "GetProductName",
    "GetProjectManager",
    "GetCurrentProject",
    "GetMediaPool",
    "GetCurrentTimeline",
}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _SECRET_KEY.search(str(key)):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = _sanitize(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, str) and _PATHISH.search(value):
        return "[HOST_PATH_REDACTED]"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return f"<{type(value).__name__}>"


def _return_kind(value: Any) -> str:
    if value is None:
        return "NONE"
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, (list, tuple)):
        return "SEQUENCE"
    if isinstance(value, dict):
        return "MAPPING"
    return "OBJECT"


def authorize_mutation_probe(*, allow_mutation: bool, sandbox_project: str | None, current_project_name: str | None) -> str:
    if not allow_mutation:
        raise ProductError(
            "ERR_RESOLVE_MUTATION_NOT_AUTHORIZED",
            "Resolve mutation probe requires explicit runtime authorization",
            ProductErrorCategory.AUTHORIZATION,
        )
    if not sandbox_project or not sandbox_project.startswith(_SANDBOX_PREFIX):
        raise ProductError(
            "ERR_RESOLVE_SANDBOX_REQUIRED",
            f"mutation probe project must start with {_SANDBOX_PREFIX}",
            ProductErrorCategory.SECURITY,
        )
    if current_project_name and not current_project_name.startswith(_SANDBOX_PREFIX):
        raise ProductError(
            "ERR_RESOLVE_EXISTING_PROJECT_PROTECTED",
            "mutation probes are forbidden while a non-sandbox Project is current",
            ProductErrorCategory.SECURITY,
        )
    return sandbox_project


@dataclass(slots=True)
class ResolveCapabilityProbe:
    resolve: object | None
    module_source_kind: str = "UNKNOWN"
    mode: ProbeMode = ProbeMode.READ_ONLY
    operation_timeout_ms: int = 60_000
    _objects: dict[str, object | None] = field(default_factory=dict, init=False)
    _safe_call_results: dict[tuple[str, str], tuple[bool, Any, float, str | None]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._objects["resolve"] = self.resolve

    def _methods(self, obj: object | None, candidates: Iterable[str]) -> tuple[str, ...]:
        if obj is None:
            return ()
        found: list[str] = []
        for name in candidates:
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            if callable(attr):
                found.append(name)
        return tuple(found)

    def _safe_call(self, object_name: str, method_name: str) -> tuple[bool, Any, float, str | None]:
        key = (object_name, method_name)
        if key in self._safe_call_results:
            return self._safe_call_results[key]
        if method_name not in _SAFE_QUERY_METHODS:
            raise RuntimeError(f"unsafe method in read-only probe: {method_name}")
        obj = self._objects.get(object_name)
        if obj is None:
            result = (False, None, 0.0, "PARENT_UNAVAILABLE")
            self._safe_call_results[key] = result
            return result
        fn = getattr(obj, method_name, None)
        if not callable(fn):
            result = (False, None, 0.0, "METHOD_ABSENT")
            self._safe_call_results[key] = result
            return result
        start = time.perf_counter()
        try:
            value = fn()
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            result = (False, None, elapsed, type(exc).__name__)
        else:
            elapsed = (time.perf_counter() - start) * 1000
            result = (True, value, elapsed, None)
        self._safe_call_results[key] = result
        return result

    def _hydrate_graph(self) -> None:
        if self.resolve is None:
            for name in ("project_manager", "project", "media_pool", "timeline"):
                self._objects[name] = None
            return

        ok, pm, _, _ = self._safe_call("resolve", "GetProjectManager")
        self._objects["project_manager"] = pm if ok else None

        ok, project, _, _ = self._safe_call("project_manager", "GetCurrentProject")
        self._objects["project"] = project if ok else None

        ok, media_pool, _, _ = self._safe_call("project", "GetMediaPool")
        self._objects["media_pool"] = media_pool if ok else None

        ok, timeline, _, _ = self._safe_call("project", "GetCurrentTimeline")
        self._objects["timeline"] = timeline if ok else None

    def _probe_safe(self, spec: CapabilitySpec, observed: tuple[str, ...]) -> CapabilityResult:
        if spec.capability_id == "resolve.connection":
            if self.resolve is None:
                return CapabilityResult(
                    spec.capability_id, spec.area, CapabilityStatus.PROBE_REQUIRED, spec.object_name,
                    spec.method_candidates, (), return_kind="NONE", fallback=spec.fallback,
                    notes=("Resolve scripting root unavailable.",), error_code="ERR_RESOLVE_NOT_AVAILABLE",
                )
            return CapabilityResult(
                spec.capability_id, spec.area, CapabilityStatus.SUPPORTED, spec.object_name,
                spec.method_candidates, (), return_kind="OBJECT", fallback=spec.fallback,
                notes=("Resolve scripting root object obtained.",),
            )

        if not observed:
            parent = self._objects.get(spec.object_name)
            note = (
                "Parent object unavailable; retry with an open sandbox/current Project."
                if parent is None
                else "Declared candidate method was not observed; absence alone is not semantic proof of unsupported behavior."
            )
            return CapabilityResult(
                spec.capability_id, spec.area, CapabilityStatus.PROBE_REQUIRED,
                spec.object_name, spec.method_candidates, observed, fallback=spec.fallback,
                notes=(note,),
            )

        method = observed[0]
        ok, value, elapsed, error = self._safe_call(spec.object_name, method)
        if not ok:
            return CapabilityResult(
                spec.capability_id, spec.area, CapabilityStatus.PROBE_REQUIRED, spec.object_name,
                spec.method_candidates, observed, elapsed_ms=round(elapsed, 3), fallback=spec.fallback,
                notes=("Safe query raised or parent was unavailable.",), error_type=error,
            )

        notes = []
        if elapsed > self.operation_timeout_ms:
            notes.append("Call returned after configured operation timeout; treat as LIMITED until supervised live retest.")
            status = CapabilityStatus.LIMITED
        else:
            status = CapabilityStatus.SUPPORTED
        if value is None and spec.capability_id in {"project.current", "media_pool.access", "timeline.current"}:
            notes.append("None is a valid runtime state when no current Project/Timeline exists; method call itself succeeded.")
        return CapabilityResult(
            spec.capability_id, spec.area, status, spec.object_name, spec.method_candidates, observed,
            elapsed_ms=round(elapsed, 3), return_kind=_return_kind(value), fallback=spec.fallback,
            notes=tuple(notes),
        )

    def run(self) -> dict[str, Any]:
        self._hydrate_graph()
        results: list[CapabilityResult] = []
        for spec in CAPABILITY_SPECS:
            obj = self._objects.get(spec.object_name)
            observed = self._methods(obj, spec.method_candidates)
            if spec.safe_read_call:
                results.append(self._probe_safe(spec, observed))
                continue

            if obj is None:
                status = CapabilityStatus.PROBE_REQUIRED
                note = "Parent object unavailable in this run."
            elif observed:
                status = CapabilityStatus.PROBE_REQUIRED
                note = "Mutating/behavioral capability is method-present but not executed in read-only mode."
            else:
                status = CapabilityStatus.PROBE_REQUIRED
                note = "No declared candidate method was observed; operation remains unresolved until authoritative live behavior or target documentation proves support status."
            notes = [note]
            if spec.notes:
                notes.append(spec.notes)
            results.append(CapabilityResult(
                spec.capability_id, spec.area, status, spec.object_name, spec.method_candidates, observed,
                fallback=spec.fallback, notes=tuple(notes),
            ))

        version_value = None
        for method in ("GetVersionString", "GetVersion"):
            ok, value, _, _ = self._safe_call_results.get(("resolve", method), (False, None, 0.0, None))
            if ok and value is not None:
                version_value = _sanitize(value)
                break
        product_value = None
        ok, value, _, _ = self._safe_call_results.get(("resolve", "GetProductName"), (False, None, 0.0, None))
        if ok:
            product_value = _sanitize(value)

        return {
            "schema_version": "1.0.0",
            "probe_id": generate_id(IdKind.EVIDENCE),
            "created_at": utc_now_iso(),
            "mode": self.mode.value,
            "host": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "resolve": {
                "connected": self.resolve is not None,
                "module_source_kind": self.module_source_kind,
                "version": version_value,
                "product_name": product_value,
            },
            "capabilities": [r.to_dict() for r in results],
            "summary": {
                "supported": sum(r.status is CapabilityStatus.SUPPORTED for r in results),
                "limited": sum(r.status is CapabilityStatus.LIMITED for r in results),
                "unsupported": sum(r.status is CapabilityStatus.UNSUPPORTED for r in results),
                "probe_required": sum(r.status is CapabilityStatus.PROBE_REQUIRED for r in results),
                "live_resolve_connected": self.resolve is not None,
                "mutation_probe_executed": False,
            },
        }


class FakeResolveGraph:
    """Tiny deterministic object graph used only by tests/fixtures."""

    def __init__(self, resolve: object | None) -> None:
        self.resolve = resolve
