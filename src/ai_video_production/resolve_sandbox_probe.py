from __future__ import annotations

from pathlib import Path
import tempfile
import time
import wave
from typing import Any, Callable

from .errors import ProductError, ProductErrorCategory
from .resolve_capabilities import (
    CapabilityStatus,
    ProbeMode,
    ResolveCapabilityProbe,
    authorize_mutation_probe,
)

def _project_name(project: object | None) -> str | None:
    if project is None:
        return None
    fn = getattr(project, "GetName", None)
    if not callable(fn):
        return None
    try:
        value = fn()
    except Exception:
        return None
    return value if isinstance(value, str) and value else None




def _require_sandbox_identity(project: object, expected_name: str) -> str:
    name = _project_name(project)
    if name is None:
        raise ProductError(
            "ERR_RESOLVE_SANDBOX_IDENTITY_UNVERIFIED",
            "sandbox mutation stopped because the active Project identity could not be verified",
            ProductErrorCategory.SECURITY,
        )
    if name != expected_name:
        raise ProductError(
            "ERR_RESOLVE_SANDBOX_NAME_MISMATCH",
            "current sandbox Project name does not match requested probe Project",
            ProductErrorCategory.SECURITY,
        )
    return name

def _silent_wav(path: Path) -> None:
    sample_rate = 8_000
    frames = sample_rate
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)


def _elapsed_call(fn: Callable[..., Any], *args: Any) -> tuple[bool, Any, float, str | None]:
    started = time.perf_counter()
    try:
        value = fn(*args)
    except Exception as exc:
        return False, None, (time.perf_counter() - started) * 1000, type(exc).__name__
    return True, value, (time.perf_counter() - started) * 1000, None


def _update_row(report: dict[str, Any], capability_id: str, *, status: CapabilityStatus,
                elapsed_ms: float | None = None, return_kind: str | None = None,
                notes: list[str] | None = None, error_type: str | None = None) -> None:
    for row in report["capabilities"]:
        if row["capability_id"] != capability_id:
            continue
        row["status"] = status.value
        row["elapsed_ms"] = round(elapsed_ms, 3) if elapsed_ms is not None else None
        row["return_kind"] = return_kind
        row["notes"] = list(notes or [])
        row["error_type"] = error_type
        row["error_code"] = None
        return
    raise KeyError(capability_id)


def _kind(value: Any) -> str:
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


def run_resolve_sandbox_probe(resolve: object, *, module_source_kind: str, sandbox_project: str) -> dict[str, Any]:
    """Exercise a minimal, disposable Resolve sandbox sequence.

    The sequence never deletes a Project, never starts/cancels rendering, never
    terminates Resolve, and refuses to begin while a non-sandbox Project is
    current. It is intended only for explicitly invoked TASK-002 live evidence.
    """
    base_probe = ResolveCapabilityProbe(resolve, module_source_kind=module_source_kind, mode=ProbeMode.SANDBOX_MUTATION)
    report = base_probe.run()

    pm = getattr(resolve, "GetProjectManager", lambda: None)()
    if pm is None:
        raise ProductError("ERR_RESOLVE_PROJECT_MANAGER_UNAVAILABLE", "Project Manager unavailable", ProductErrorCategory.EXTERNAL_DEPENDENCY)
    current = getattr(pm, "GetCurrentProject", lambda: None)()
    current_name = _project_name(current)
    if current is not None and current_name is None:
        raise ProductError(
            "ERR_RESOLVE_CURRENT_PROJECT_NAME_UNVERIFIED",
            "mutation probe refused because the current Project name could not be positively verified",
            ProductErrorCategory.SECURITY,
        )
    authorize_mutation_probe(allow_mutation=True, sandbox_project=sandbox_project, current_project_name=current_name)

    project = current
    if project is None:
        fn = getattr(pm, "CreateProject", None)
        if not callable(fn):
            raise ProductError("ERR_RESOLVE_CREATE_PROJECT_UNAVAILABLE", "CreateProject unavailable", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        ok, project, elapsed, error = _elapsed_call(fn, sandbox_project)
        success = ok and project is not None
        _update_row(report, "project.create", status=CapabilityStatus.SUPPORTED if success else CapabilityStatus.PROBE_REQUIRED,
                    elapsed_ms=elapsed, return_kind=_kind(project), notes=["Created isolated TASK-002 sandbox Project." if success else "Sandbox Project creation failed."], error_type=error)
        if not success:
            report["mutation_gate"] = {"authorized": True, "sandbox_project": sandbox_project, "executed": True,
                                       "note": "Sandbox sequence stopped after Project creation failure."}
            report["summary"]["mutation_probe_executed"] = True
            _recount(report)
            return report
    else:
        _update_row(report, "project.create", status=CapabilityStatus.LIMITED, return_kind="OBJECT",
                    notes=["Existing sandbox Project was already current; creation was intentionally not repeated."])

    _require_sandbox_identity(project, sandbox_project)

    load = getattr(pm, "LoadProject", None)
    if callable(load):
        ok, loaded, elapsed, error = _elapsed_call(load, sandbox_project)
        _update_row(report, "project.open", status=CapabilityStatus.SUPPORTED if ok and loaded is not None else CapabilityStatus.PROBE_REQUIRED,
                    elapsed_ms=elapsed, return_kind=_kind(loaded), notes=["Loaded the same isolated sandbox Project by name." if ok and loaded is not None else "LoadProject did not return a Project."], error_type=error)
        if ok and loaded is not None:
            _require_sandbox_identity(loaded, sandbox_project)
            project = loaded

    save = getattr(pm, "SaveProject", None)
    if callable(save):
        ok, value, elapsed, error = _elapsed_call(save)
        _update_row(report, "project.save", status=CapabilityStatus.SUPPORTED if ok and value is not False else CapabilityStatus.PROBE_REQUIRED,
                    elapsed_ms=elapsed, return_kind=_kind(value), notes=["Saved isolated sandbox Project." if ok and value is not False else "SaveProject failed."], error_type=error)

    with tempfile.TemporaryDirectory(prefix="bai-resolve-sandbox-") as tmp:
        tmpdir = Path(tmp)
        export_path = tmpdir / "sandbox.drp"
        export = getattr(pm, "ExportProject", None)
        if callable(export):
            ok, value, elapsed, error = _elapsed_call(export, sandbox_project, str(export_path))
            verified = ok and value is not False and export_path.exists() and export_path.stat().st_size > 0
            _update_row(report, "project.snapshot", status=CapabilityStatus.SUPPORTED if verified else CapabilityStatus.PROBE_REQUIRED,
                        elapsed_ms=elapsed, return_kind=_kind(value), notes=["ExportProject produced a non-empty temporary .drp snapshot." if verified else "Project export did not produce a verifiable temporary snapshot."], error_type=error)

        media_pool = getattr(project, "GetMediaPool", lambda: None)()
        if media_pool is not None:
            _update_row(
                report,
                "media_pool.access",
                status=CapabilityStatus.SUPPORTED,
                return_kind="OBJECT",
                notes=["Media Pool obtained from the isolated sandbox Project during behavioral probe."],
            )
        imported_items: list[Any] = []
        timeline = None
        if media_pool is not None:
            get_root = getattr(media_pool, "GetRootFolder", None)
            add_folder = getattr(media_pool, "AddSubFolder", None)
            if callable(get_root) and callable(add_folder):
                root = get_root()
                ok, folder, elapsed, error = _elapsed_call(add_folder, root, "BAI_TASK002_PROBE")
                _update_row(report, "bin.ensure", status=CapabilityStatus.SUPPORTED if ok and folder is not None else CapabilityStatus.PROBE_REQUIRED,
                            elapsed_ms=elapsed, return_kind=_kind(folder), notes=["Created isolated probe Bin." if ok and folder is not None else "Probe Bin creation failed."], error_type=error)

            wav_path = tmpdir / "task002_probe.wav"
            _silent_wav(wav_path)
            import_media = getattr(media_pool, "ImportMedia", None)
            if callable(import_media):
                ok, value, elapsed, error = _elapsed_call(import_media, [str(wav_path)])
                if ok and isinstance(value, (list, tuple)):
                    imported_items = list(value)
                verified = bool(imported_items)
                _update_row(report, "media.import", status=CapabilityStatus.SUPPORTED if verified else CapabilityStatus.PROBE_REQUIRED,
                            elapsed_ms=elapsed, return_kind=_kind(value), notes=["Imported generated one-second silent WAV from a temporary probe directory." if verified else "Temporary WAV import returned no media items."], error_type=error)

            create_timeline = getattr(media_pool, "CreateEmptyTimeline", None)
            if callable(create_timeline):
                ok, timeline, elapsed, error = _elapsed_call(create_timeline, "BAI_TASK002_PROBE_TIMELINE")
                _update_row(report, "timeline.create", status=CapabilityStatus.SUPPORTED if ok and timeline is not None else CapabilityStatus.PROBE_REQUIRED,
                            elapsed_ms=elapsed, return_kind=_kind(timeline), notes=["Created isolated probe Timeline." if ok and timeline is not None else "Probe Timeline creation failed."], error_type=error)

            append = getattr(media_pool, "AppendToTimeline", None)
            if callable(append) and imported_items:
                ok, value, elapsed, error = _elapsed_call(append, imported_items)
                verified = ok and value not in (None, False, [])
                _update_row(report, "timeline.build", status=CapabilityStatus.SUPPORTED if verified else CapabilityStatus.PROBE_REQUIRED,
                            elapsed_ms=elapsed, return_kind=_kind(value), notes=["Appended imported probe media to isolated Timeline." if verified else "AppendToTimeline returned no verifiable Timeline item."], error_type=error)

        if timeline is not None:
            current_timeline = getattr(project, "GetCurrentTimeline", lambda: None)()
            if current_timeline is not None:
                _update_row(
                    report,
                    "timeline.current",
                    status=CapabilityStatus.SUPPORTED,
                    return_kind="OBJECT",
                    notes=["Current Timeline obtained after isolated sandbox Timeline creation."],
                )
            add_marker = getattr(timeline, "AddMarker", None)
            if callable(add_marker):
                get_start = getattr(timeline, "GetStartFrame", None)
                marker_frame = 0
                if callable(get_start):
                    try:
                        observed_start = get_start()
                    except Exception:
                        observed_start = None
                    if isinstance(observed_start, (int, float)):
                        marker_frame = observed_start
                ok, value, elapsed, error = _elapsed_call(
                    add_marker, marker_frame, "Blue", "BAI TASK-002", "Sandbox capability probe", 1, "TASK002"
                )
                _update_row(report, "timeline.markers", status=CapabilityStatus.SUPPORTED if ok and value is not False else CapabilityStatus.PROBE_REQUIRED,
                            elapsed_ms=elapsed, return_kind=_kind(value), notes=["Added marker at the sandbox Timeline start frame." if ok and value is not False else "AddMarker failed."], error_type=error)

    report["mutation_gate"] = {
        "authorized": True,
        "sandbox_project": sandbox_project,
        "executed": True,
        "note": "Minimal TASK-002 sandbox sequence executed. Project deletion, render start/cancel, Resolve termination, relink and subtitle mutation were not requested.",
    }
    report["summary"]["mutation_probe_executed"] = True
    _recount(report)
    return report


def _recount(report: dict[str, Any]) -> None:
    counts = {status.value.lower(): 0 for status in CapabilityStatus}
    for row in report["capabilities"]:
        counts[row["status"].lower()] += 1
    report["summary"].update(counts)
