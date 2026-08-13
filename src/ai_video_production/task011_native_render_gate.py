"""TASK-011 bounded native Resolve render + real artifact QA acceptance gate.

This module is an internal/native validation harness. It never mutates an
arbitrary Resolve Project: a caller must explicitly name a BAI_CAPABILITY_PROBE
sandbox and explicitly authorize the render operation for the current run.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import time
from typing import Any, Callable

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .render_qa import LoudnessProfile, RenderQAService
from .resolve_capabilities import authorize_mutation_probe
from .resolve_loader import ResolveModuleLoader
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate


_SANDBOX_RE = re.compile(r"^BAI_CAPABILITY_PROBE_[A-Za-z0-9_-]+$")
_AUTOMATION_TIMELINE_RE = re.compile(r"^BAI_AUTO_[A-F0-9]{12}$")
_RATE_ALIASES = {
    "23.976": FrameRate(24_000, 1_001),
    "29.97": FrameRate(30_000, 1_001),
    "47.952": FrameRate(48_000, 1_001),
    "59.94": FrameRate(60_000, 1_001),
    "95.904": FrameRate(96_000, 1_001),
    "119.88": FrameRate(120_000, 1_001),
}


def _parse_resolve_rate(value: Any) -> FrameRate:
    raw = str(value).strip()
    if raw in _RATE_ALIASES:
        return _RATE_ALIASES[raw]
    try:
        decimal = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ProductError(
            "ERR_TASK011_NATIVE_TIMELINE_RATE_UNREADABLE",
            "Resolve timelineFrameRate could not be parsed",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"observed": raw},
        ) from exc
    if decimal == decimal.to_integral_value() and decimal > 0:
        return FrameRate(int(decimal))
    raise ProductError(
        "ERR_TASK011_NATIVE_TIMELINE_RATE_UNSUPPORTED",
        "Resolve reported an unsupported non-integer timelineFrameRate",
        ProductErrorCategory.NOT_SUPPORTED,
        details={"observed": raw},
    )


def _regular_json(path: str | Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
        raise ProductError(
            "ERR_TASK011_NATIVE_INPUT_INVALID",
            f"{label} must be a non-empty regular non-symlink file",
            ProductErrorCategory.VALIDATION,
        )
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductError(
            "ERR_TASK011_NATIVE_INPUT_JSON_INVALID",
            f"{label} is not valid UTF-8 JSON",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    if not isinstance(value, dict):
        raise ProductError(
            "ERR_TASK011_NATIVE_INPUT_JSON_INVALID",
            f"{label} root must be a JSON object",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return value


@dataclass(frozen=True, slots=True)
class Task011NativeRenderRequest:
    sandbox_project: str
    timeline_name: str
    expected_duration_frames: int
    evidence_root: Path
    assembly_sha256: str | None = None
    duration_tolerance_frames: int = 2
    timeout_seconds: int = 1800
    poll_interval_seconds: float = 1.0
    render_format: str | None = None
    render_codec: str | None = None
    loudness_profile: LoudnessProfile | None = LoudnessProfile()

    def __post_init__(self) -> None:
        if _SANDBOX_RE.fullmatch(self.sandbox_project) is None:
            raise ValueError("sandbox_project must match BAI_CAPABILITY_PROBE_*")
        if _AUTOMATION_TIMELINE_RE.fullmatch(self.timeline_name) is None:
            raise ValueError("timeline_name must be a deterministic BAI_AUTO_<12HEX> Timeline")
        if self.expected_duration_frames <= 0:
            raise ValueError("expected_duration_frames must be positive")
        if not 0 <= self.duration_tolerance_frames <= 300:
            raise ValueError("duration_tolerance_frames must be 0-300")
        if not 1 <= self.timeout_seconds <= 7200:
            raise ValueError("timeout_seconds must be 1-7200")
        if not 0.1 <= self.poll_interval_seconds <= 60:
            raise ValueError("poll_interval_seconds must be 0.1-60")
        if (self.render_format is None) != (self.render_codec is None):
            raise ValueError("render_format and render_codec must be provided together")
        if self.assembly_sha256 is not None and not self.assembly_sha256.startswith("sha256:"):
            raise ValueError("assembly_sha256 must use sha256: prefix")

    @classmethod
    def from_assembly_plan(
        cls,
        assembly_plan_path: str | Path,
        *,
        sandbox_project: str,
        evidence_root: str | Path,
        duration_tolerance_frames: int = 2,
        timeout_seconds: int = 1800,
        poll_interval_seconds: float = 1.0,
        render_format: str | None = None,
        render_codec: str | None = None,
        loudness_profile: LoudnessProfile | None = LoudnessProfile(),
    ) -> "Task011NativeRenderRequest":
        payload = _regular_json(assembly_plan_path, label="TASK-010 assembly plan")
        if payload.get("task_owner") != "TASK-010":
            raise ProductError(
                "ERR_TASK011_NATIVE_ASSEMBLY_PLAN_OWNER",
                "native render requires a TASK-010 assembly plan",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        timeline_name = payload.get("timeline_name")
        expected = payload.get("expected_duration_frames")
        assembly_sha256 = payload.get("assembly_sha256")
        if not isinstance(timeline_name, str) or not isinstance(expected, int):
            raise ProductError(
                "ERR_TASK011_NATIVE_ASSEMBLY_PLAN_FIELDS",
                "TASK-010 assembly plan is missing native render linkage fields",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not isinstance(assembly_sha256, str) or not assembly_sha256.startswith("sha256:"):
            raise ProductError(
                "ERR_TASK011_NATIVE_ASSEMBLY_PLAN_FIELDS",
                "TASK-010 assembly plan is missing assembly_sha256",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        unhashed = dict(payload)
        unhashed.pop("assembly_sha256", None)
        if sha256_bytes(canonical_json_bytes(unhashed)) != assembly_sha256:
            raise ProductError(
                "ERR_TASK011_NATIVE_ASSEMBLY_PLAN_HASH",
                "TASK-010 assembly plan self-hash is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return cls(
            sandbox_project=sandbox_project,
            timeline_name=timeline_name,
            expected_duration_frames=expected,
            evidence_root=Path(evidence_root),
            assembly_sha256=assembly_sha256,
            duration_tolerance_frames=duration_tolerance_frames,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            render_format=render_format,
            render_codec=render_codec,
            loudness_profile=loudness_profile,
        )


class Task011NativeRenderGateRunner:
    """Run one explicitly-authorized native render and validate its real artifact."""

    def __init__(
        self,
        request: Task011NativeRenderRequest,
        *,
        loader: ResolveModuleLoader | Any | None = None,
        qa_service: RenderQAService | Any | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.request = request
        self.loader = loader or ResolveModuleLoader()
        self.qa_service = qa_service or RenderQAService()
        self.sleep_fn = sleep_fn
        self.monotonic_fn = monotonic_fn

    def _project(self) -> tuple[Any, Any]:
        resolve, _ = self.loader.connect()
        manager = getattr(resolve, "GetProjectManager", lambda: None)()
        project = getattr(manager, "GetCurrentProject", lambda: None)() if manager is not None else None
        if project is None:
            raise ProductError(
                "ERR_TASK011_NATIVE_CURRENT_PROJECT_REQUIRED",
                "open the intended Resolve sandbox Project before TASK-011 native validation",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )
        name_fn = getattr(project, "GetName", None)
        try:
            current_name = name_fn() if callable(name_fn) else None
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_PROJECT_NAME_UNVERIFIED",
                "current Resolve Project name could not be verified",
                ProductErrorCategory.SECURITY,
            ) from exc
        if not isinstance(current_name, str) or not current_name:
            raise ProductError(
                "ERR_TASK011_NATIVE_PROJECT_NAME_UNVERIFIED",
                "current Resolve Project name could not be verified",
                ProductErrorCategory.SECURITY,
            )
        authorize_mutation_probe(
            allow_mutation=True,
            sandbox_project=self.request.sandbox_project,
            current_project_name=current_name,
        )
        if current_name != self.request.sandbox_project:
            raise ProductError(
                "ERR_TASK011_NATIVE_SANDBOX_MISMATCH",
                "current Resolve Project does not exactly match the authorized sandbox",
                ProductErrorCategory.SECURITY,
                details={"expected": self.request.sandbox_project, "observed": current_name},
            )
        return resolve, project

    def _timeline(self, project: Any) -> Any:
        count_fn = getattr(project, "GetTimelineCount", None)
        get_fn = getattr(project, "GetTimelineByIndex", None)
        if not callable(count_fn) or not callable(get_fn):
            raise ProductError(
                "ERR_TASK011_NATIVE_TIMELINE_API_UNAVAILABLE",
                "Resolve does not expose the Timeline enumeration API required for safe targeting",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        try:
            count = int(count_fn())
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_TIMELINE_ENUMERATION_FAILED",
                "Resolve Timeline enumeration failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        matches: list[Any] = []
        for index in range(1, count + 1):
            try:
                timeline = get_fn(index)
                name = getattr(timeline, "GetName", lambda: None)() if timeline is not None else None
            except Exception as exc:
                raise ProductError(
                    "ERR_TASK011_NATIVE_TIMELINE_ENUMERATION_FAILED",
                    "Resolve Timeline inspection failed",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from exc
            if name == self.request.timeline_name:
                matches.append(timeline)
        if len(matches) != 1:
            code = "ERR_TASK011_NATIVE_TIMELINE_NOT_FOUND" if not matches else "ERR_TASK011_NATIVE_TIMELINE_AMBIGUOUS"
            raise ProductError(
                code,
                "native render requires exactly one matching Automation-owned Timeline",
                ProductErrorCategory.STATE if not matches else ProductErrorCategory.DATA_INTEGRITY,
                details={"timeline_name": self.request.timeline_name, "match_count": len(matches)},
            )
        return matches[0]

    @staticmethod
    def _project_rate(project: Any) -> FrameRate:
        get_setting = getattr(project, "GetSetting", None)
        if not callable(get_setting):
            raise ProductError(
                "ERR_TASK011_NATIVE_TIMELINE_RATE_API_UNAVAILABLE",
                "Resolve Project does not expose GetSetting for timelineFrameRate",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        try:
            return _parse_resolve_rate(get_setting("timelineFrameRate"))
        except ProductError:
            raise
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_TIMELINE_RATE_READ_FAILED",
                "Resolve Project timelineFrameRate read failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc

    def _validate_report_path(self, output_path: str | Path) -> Path:
        root = self.request.evidence_root.expanduser().resolve()
        render_dir = root / "render-output"
        output = Path(output_path).expanduser().resolve()
        try:
            output.relative_to(render_dir)
        except ValueError:
            return output
        raise ProductError(
            "ERR_TASK011_NATIVE_REPORT_LOCATION_INVALID",
            "TASK-011 native Evidence report must be outside the dedicated render-output directory",
            ProductErrorCategory.VALIDATION,
        )

    @staticmethod
    def _render_status_apis(project: Any) -> tuple[Callable[[], Any], Callable[[str], Any]]:
        is_rendering = getattr(project, "IsRenderingInProgress", None)
        status_fn = getattr(project, "GetRenderJobStatus", None)
        if not callable(is_rendering) or not callable(status_fn):
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_STATUS_API_UNAVAILABLE",
                "Resolve does not expose the render status APIs required for bounded native validation",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        return is_rendering, status_fn

    @staticmethod
    def _stop_rendering_best_effort(project: Any) -> None:
        stop = getattr(project, "StopRendering", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass

    def _render_dir(self) -> Path:
        root = self.request.evidence_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / "render-output"
        if target.exists():
            if target.is_symlink() or not target.is_dir():
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_DIR_INVALID",
                    "native render output must be a regular directory",
                    ProductErrorCategory.VALIDATION,
                )
            if any(target.iterdir()):
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_DIR_NOT_EMPTY",
                    "native render output directory must be empty before the gate starts",
                    ProductErrorCategory.STATE,
                )
        else:
            target.mkdir()
        return target

    @staticmethod
    def _single_artifact(render_dir: Path) -> Path:
        files = [
            item for item in render_dir.iterdir()
            if item.is_file() and not item.is_symlink() and item.stat().st_size > 0
        ]
        if len(files) != 1:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_ARTIFACT_AMBIGUOUS",
                "Resolve render must produce exactly one non-empty regular artifact in the dedicated output directory",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"artifact_count": len(files)},
            )
        return files[0]

    def run(
        self,
        *,
        explicit_external_write_authorization: bool,
        output_path: str | Path,
    ) -> dict[str, Any]:
        if not explicit_external_write_authorization:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_NOT_AUTHORIZED",
                "TASK-011 native Resolve render requires explicit runtime external-write authorization",
                ProductErrorCategory.AUTHORIZATION,
            )

        _, project = self._project()
        timeline = self._timeline(project)
        project_rate = self._project_rate(project)
        output = self._validate_report_path(output_path)
        is_rendering, status_fn = self._render_status_apis(project)

        # Validate every API needed to submit the bounded render before changing
        # current Timeline/render settings or adding a Render Queue job.
        set_current = getattr(project, "SetCurrentTimeline", None)
        set_settings = getattr(project, "SetRenderSettings", None)
        add_job = getattr(project, "AddRenderJob", None)
        start = getattr(project, "StartRendering", None)
        if not all(callable(fn) for fn in (set_current, set_settings, add_job, start)):
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_API_UNAVAILABLE",
                "Resolve does not expose the complete render API required for bounded native validation",
                ProductErrorCategory.NOT_SUPPORTED,
            )

        try:
            selected = set_current(timeline) if callable(set_current) else False
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_SET_TIMELINE_FAILED",
                "Resolve could not select the requested Automation-owned Timeline",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        if selected is not True:
            raise ProductError(
                "ERR_TASK011_NATIVE_SET_TIMELINE_FAILED",
                "Resolve could not select the requested Automation-owned Timeline",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        render_dir = self._render_dir()

        if self.request.render_format is not None:
            setter = getattr(project, "SetCurrentRenderFormatAndCodec", None)
            if not callable(setter):
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_FORMAT_API_UNAVAILABLE",
                    "Resolve does not expose SetCurrentRenderFormatAndCodec",
                    ProductErrorCategory.NOT_SUPPORTED,
                )
            try:
                accepted = setter(self.request.render_format, self.request.render_codec)
            except Exception as exc:
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_FORMAT_FAILED",
                    "Resolve render format/codec selection failed",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from exc
            if accepted is not True:
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_FORMAT_REJECTED",
                    "Resolve rejected the requested render format/codec pair",
                    ProductErrorCategory.NOT_SUPPORTED,
                    details={"format": self.request.render_format, "codec": self.request.render_codec},
                )

        settings = {
            "SelectAllFrames": True,
            "TargetDir": str(render_dir),
            "CustomName": "BAI_TASK011_NATIVE_RENDER",
            "ExportVideo": True,
            "ExportAudio": True,
        }
        try:
            settings_ok = set_settings(settings)
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_SETTINGS_FAILED",
                "Resolve SetRenderSettings failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        if settings_ok is not True:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_SETTINGS_REJECTED",
                "Resolve rejected the bounded TASK-011 render settings",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        try:
            job_id = add_job()
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_ADD_RENDER_JOB_FAILED",
                "Resolve AddRenderJob failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        if not isinstance(job_id, str) or not job_id:
            raise ProductError(
                "ERR_TASK011_NATIVE_ADD_RENDER_JOB_FAILED",
                "Resolve did not return a unique render job id",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        try:
            started = start(job_id)
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_START_RENDER_FAILED",
                "Resolve StartRendering failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        if started is not True:
            raise ProductError(
                "ERR_TASK011_NATIVE_START_RENDER_FAILED",
                "Resolve did not start the requested render job",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            )

        deadline = self.monotonic_fn() + self.request.timeout_seconds
        while True:
            try:
                active = bool(is_rendering())
            except Exception as exc:
                self._stop_rendering_best_effort(project)
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_PROGRESS_FAILED",
                    "Resolve render progress query failed after render dispatch; rendering was stopped best-effort",
                    ProductErrorCategory.EXTERNAL_DEPENDENCY,
                ) from exc
            if not active:
                break
            if self.monotonic_fn() >= deadline:
                self._stop_rendering_best_effort(project)
                raise ProductError(
                    "ERR_TASK011_NATIVE_RENDER_TIMEOUT",
                    "Resolve native render exceeded the configured timeout",
                    ProductErrorCategory.TIMEOUT,
                    retryable=False,
                    details={"timeout_seconds": self.request.timeout_seconds},
                )
            self.sleep_fn(self.request.poll_interval_seconds)

        try:
            job_status = status_fn(job_id)
        except Exception as exc:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_STATUS_FAILED",
                "Resolve render job status query failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
            ) from exc
        if not isinstance(job_status, dict):
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_STATUS_INVALID",
                "Resolve returned an invalid render job status payload",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        status_text = str(job_status.get("JobStatus", "")).strip()
        if status_text.casefold() not in {"complete", "completed"}:
            raise ProductError(
                "ERR_TASK011_NATIVE_RENDER_JOB_NOT_COMPLETE",
                "Resolve render job did not finish in a completed state",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"job_status": status_text or "UNKNOWN"},
            )

        artifact = self._single_artifact(render_dir)
        qa = self.qa_service.verify(
            artifact,
            expected_duration_frames=self.request.expected_duration_frames,
            timeline_rate=project_rate,
            duration_tolerance_frames=self.request.duration_tolerance_frames,
            require_video=True,
            require_audio=True,
            loudness_profile=self.request.loudness_profile,
        )
        qa_dict = qa.to_dict()

        report: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-011",
            "gate": "NATIVE_RESOLVE_RENDER_QA",
            "status": "PASS" if qa_dict.get("status") == "PASS" else "FAIL",
            "sandbox_project": self.request.sandbox_project,
            "timeline_name": self.request.timeline_name,
            "assembly_sha256": self.request.assembly_sha256,
            "project_timeline_rate": {
                "numerator": project_rate.numerator,
                "denominator": project_rate.denominator,
            },
            "expected_duration_frames": self.request.expected_duration_frames,
            "duration_tolerance_frames": self.request.duration_tolerance_frames,
            "render_job": {
                "id_persisted": False,
                "status": status_text,
            },
            "render_artifact": {
                "path_persisted": False,
                "count": 1,
                "sha256": qa_dict.get("artifact_sha256"),
                "size_bytes": qa_dict.get("artifact_size_bytes"),
            },
            "qa_report": qa_dict,
        }
        report["report_sha256"] = sha256_bytes(canonical_json_bytes(report))
        AtomicJsonWriter.write(output, report)
        return report
