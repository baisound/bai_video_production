"""TASK-054 R6A gated, read-only Windows/WSL environment probe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
import subprocess
from typing import Callable, Mapping

from .dbd_reasoning_worker_lifecycle import no_console_popen_options
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_AUTHORITY_REF_RE = re.compile(r"authorization://task054/[0-9A-HJKMNP-TV-Z]{26}")
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._+:/(),-]{0,159}")
_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_MAX_OUTPUT_BYTES = 64 * 1024
_PROBE_STATE = "EVIDENCE_ONLY_NO_INSTALL_DOWNLOAD_TRAINING_OR_EXECUTION_AUTHORITY"


class ProbeCheckId(str, Enum):
    WSL = "WSL"
    PYTHON = "PYTHON"
    GPU = "GPU"
    STORAGE = "STORAGE"


class ProbeCheckStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED_RUNTIME = "BLOCKED_RUNTIME"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class EnvironmentProbeStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED_RUNTIME = "BLOCKED_RUNTIME"
    NOT_CONFIRMED = "NOT_CONFIRMED"


def _utc(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be UTC")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return parsed


@dataclass(frozen=True, slots=True)
class ProbeGateBinding:
    authority_ref: str
    authority_evidence_sha256: str
    confirmed_at: str
    expires_at: str
    scope: str = "HOST_RUNTIME_PROBE_ONLY"
    decision: str = "APPROVED"

    def __post_init__(self) -> None:
        if not isinstance(self.authority_ref, str) or not _AUTHORITY_REF_RE.fullmatch(self.authority_ref):
            raise ValueError("authority_ref is invalid")
        validate_sha256(self.authority_evidence_sha256, field_name="authority_evidence_sha256")
        confirmed = _utc(self.confirmed_at, "confirmed_at")
        expires = _utc(self.expires_at, "expires_at")
        if expires <= confirmed:
            raise ValueError("probe authority expiry is invalid")
        if self.scope != "HOST_RUNTIME_PROBE_ONLY" or self.decision != "APPROVED":
            raise ValueError("probe authority must be exact and approved")

    def require_active(self, observed_at: str) -> None:
        observed = _utc(observed_at, "observed_at")
        if not _utc(self.confirmed_at, "confirmed_at") <= observed <= _utc(self.expires_at, "expires_at"):
            raise ValueError("probe authority is not active at observation time")


@dataclass(frozen=True, slots=True)
class ProbeCommandResult:
    exit_code: int
    stdout: bytes
    timed_out: bool = False
    output_truncated: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise ValueError("exit_code is invalid")
        if not isinstance(self.stdout, bytes) or len(self.stdout) > _MAX_OUTPUT_BYTES:
            raise ValueError("probe stdout is invalid or outside bounds")
        if not isinstance(self.timed_out, bool):
            raise ValueError("timed_out must be boolean")
        if not isinstance(self.output_truncated, bool):
            raise ValueError("output_truncated must be boolean")


@dataclass(frozen=True, slots=True)
class EnvironmentProbeCheck:
    check_id: ProbeCheckId
    status: ProbeCheckStatus
    version_summary: str | None
    detail_code: str
    observation_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.check_id, ProbeCheckId) or not isinstance(self.status, ProbeCheckStatus):
            raise ValueError("probe check enum is invalid")
        if self.version_summary is not None and (
            not isinstance(self.version_summary, str) or not _VERSION_RE.fullmatch(self.version_summary)
        ):
            raise ValueError("version_summary is invalid")
        if self.status is ProbeCheckStatus.AVAILABLE and self.version_summary is None:
            raise ValueError("AVAILABLE check requires a version summary")
        if not isinstance(self.detail_code, str) or not _CODE_RE.fullmatch(self.detail_code):
            raise ValueError("detail_code is invalid")
        validate_sha256(self.observation_sha256, field_name="observation_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id.value, "status": self.status.value,
            "version_summary": self.version_summary, "detail_code": self.detail_code,
            "observation_sha256": self.observation_sha256,
        }


@dataclass(frozen=True, slots=True)
class EnvironmentProbeReport:
    authority_ref: str
    authority_evidence_sha256: str
    observed_at: str
    command_set_sha256: str
    checks: tuple[EnvironmentProbeCheck, ...]
    status: EnvironmentProbeStatus
    state: str = _PROBE_STATE

    def __post_init__(self) -> None:
        if not isinstance(self.authority_ref, str) or not _AUTHORITY_REF_RE.fullmatch(self.authority_ref):
            raise ValueError("authority_ref is invalid")
        validate_sha256(self.authority_evidence_sha256, field_name="authority_evidence_sha256")
        _utc(self.observed_at, "observed_at")
        validate_sha256(self.command_set_sha256, field_name="command_set_sha256")
        if tuple(item.check_id for item in self.checks) != tuple(ProbeCheckId):
            raise ValueError("checks must use canonical WSL/PYTHON/GPU/STORAGE order")
        if self.status is not _overall_status(self.checks):
            raise ValueError("probe status does not match checks")
        if self.state != _PROBE_STATE:
            raise ValueError("R6A cannot grant install or execution authority")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "record_kind": "DBD_REASONING_ENVIRONMENT_PROBE_REPORT",
            "authority_ref": self.authority_ref,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "observed_at": self.observed_at,
            "command_set_sha256": self.command_set_sha256,
            "checks": [item.to_dict() for item in self.checks],
            "status": self.status.value,
            "state": self.state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "report_sha256": sha256_bytes(canonical_json_bytes(body))}


def _overall_status(checks: tuple[EnvironmentProbeCheck, ...]) -> EnvironmentProbeStatus:
    statuses = {item.status for item in checks}
    if ProbeCheckStatus.BLOCKED_RUNTIME in statuses:
        return EnvironmentProbeStatus.BLOCKED_RUNTIME
    if ProbeCheckStatus.NOT_CONFIRMED in statuses:
        return EnvironmentProbeStatus.NOT_CONFIRMED
    return EnvironmentProbeStatus.AVAILABLE


_COMMANDS: dict[ProbeCheckId, tuple[str, ...]] = {
    ProbeCheckId.WSL: ("wsl.exe", "--status"),
    ProbeCheckId.PYTHON: ("wsl.exe", "-d", "Ubuntu", "--", "python3", "--version"),
    ProbeCheckId.GPU: (
        "wsl.exe", "-d", "Ubuntu", "--", "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits",
    ),
    ProbeCheckId.STORAGE: ("wsl.exe", "-d", "Ubuntu", "--", "df", "-Pk", "/home/baisound"),
}
COMMAND_SET_SHA256 = sha256_bytes(canonical_json_bytes({key.value: list(value) for key, value in _COMMANDS.items()}))


def _safe_summary(check_id: ProbeCheckId, result: ProbeCommandResult) -> tuple[str | None, str]:
    if result.output_truncated:
        return None, "OUTPUT_LIMIT"
    if result.timed_out:
        return None, "PROBE_TIMEOUT"
    if result.exit_code != 0:
        return None, "COMMAND_UNAVAILABLE"
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return None, "EMPTY_OBSERVATION"
    if check_id is ProbeCheckId.WSL:
        return "WSL configured", "PASS"
    if check_id is ProbeCheckId.PYTHON:
        first = text.splitlines()[0].strip()
        return (first, "PASS") if _VERSION_RE.fullmatch(first) else (None, "MALFORMED_VERSION")
    if check_id is ProbeCheckId.GPU:
        first = text.splitlines()[0].strip()
        if len(first.split(",")) != 3 or not _VERSION_RE.fullmatch(first):
            return None, "MALFORMED_GPU_OBSERVATION"
        return first, "PASS"
    lines = [line for line in text.splitlines() if line.strip()]
    fields = lines[-1].split() if lines else []
    if len(fields) < 6 or not fields[3].isdigit():
        return None, "MALFORMED_STORAGE_OBSERVATION"
    return f"free_kib {fields[3]}", "PASS"


class BoundedEnvironmentProbe:
    def __init__(self, *, command_runner: Callable[[tuple[str, ...], int], ProbeCommandResult]) -> None:
        if not callable(command_runner):
            raise ValueError("command_runner must be callable")
        self._run = command_runner

    def execute(
        self, *, gate: ProbeGateBinding, observed_at: str,
    ) -> EnvironmentProbeReport:
        if not isinstance(gate, ProbeGateBinding):
            raise ValueError("gate must be ProbeGateBinding")
        gate.require_active(observed_at)
        checks = []
        for check_id in ProbeCheckId:
            result = self._run(_COMMANDS[check_id], 15)
            if not isinstance(result, ProbeCommandResult):
                raise ValueError("command runner returned an invalid result")
            summary, code = _safe_summary(check_id, result)
            checks.append(EnvironmentProbeCheck(
                check_id=check_id,
                status=ProbeCheckStatus.AVAILABLE if code == "PASS" else ProbeCheckStatus.BLOCKED_RUNTIME,
                version_summary=summary,
                detail_code=code,
                observation_sha256=sha256_bytes(result.stdout),
            ))
        values = tuple(checks)
        return EnvironmentProbeReport(
            authority_ref=gate.authority_ref,
            authority_evidence_sha256=gate.authority_evidence_sha256,
            observed_at=observed_at,
            command_set_sha256=COMMAND_SET_SHA256,
            checks=values,
            status=_overall_status(values),
        )


def subprocess_probe_runner(command: tuple[str, ...], timeout_seconds: int) -> ProbeCommandResult:
    if command not in _COMMANDS.values():
        raise ValueError("probe command is not allowlisted")
    try:
        completed = subprocess.run(
            list(command), timeout=timeout_seconds, check=False,
            **{
                **no_console_popen_options(),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
            },
        )
    except subprocess.TimeoutExpired as exc:
        raw = bytes(exc.stdout or b"") + b"\n" + bytes(exc.stderr or b"")
        return ProbeCommandResult(-1, raw[:_MAX_OUTPUT_BYTES], timed_out=True, output_truncated=len(raw) > _MAX_OUTPUT_BYTES)
    output = bytes(completed.stdout or b"") + b"\n" + bytes(completed.stderr or b"")
    if len(output) > _MAX_OUTPUT_BYTES:
        return ProbeCommandResult(-1, output[:_MAX_OUTPUT_BYTES], output_truncated=True)
    return ProbeCommandResult(completed.returncode, output)


def admit_environment_probe_report(record: Mapping[str, object]) -> EnvironmentProbeReport:
    if not isinstance(record, Mapping):
        raise ValueError("probe report must be a mapping")
    expected = {
        "schema_version", "record_kind", "authority_ref", "authority_evidence_sha256",
        "observed_at", "command_set_sha256", "checks", "status", "state", "report_sha256",
    }
    if set(record) != expected or record.get("schema_version") != "1.0.0" or record.get("record_kind") != "DBD_REASONING_ENVIRONMENT_PROBE_REPORT":
        raise ValueError("probe report shape is invalid")
    raw_checks = record.get("checks")
    if not isinstance(raw_checks, list):
        raise ValueError("probe checks must be a list")
    checks = tuple(EnvironmentProbeCheck(
        check_id=ProbeCheckId(item["check_id"]), status=ProbeCheckStatus(item["status"]),
        version_summary=item["version_summary"], detail_code=item["detail_code"],
        observation_sha256=item["observation_sha256"],
    ) for item in raw_checks if isinstance(item, dict) and set(item) == {
        "check_id", "status", "version_summary", "detail_code", "observation_sha256",
    })
    if len(checks) != len(raw_checks):
        raise ValueError("probe check shape is invalid")
    report = EnvironmentProbeReport(
        authority_ref=record["authority_ref"], authority_evidence_sha256=record["authority_evidence_sha256"],
        observed_at=record["observed_at"], command_set_sha256=record["command_set_sha256"],
        checks=checks, status=EnvironmentProbeStatus(record["status"]), state=record["state"],
    )
    if report.to_dict() != dict(record):
        raise ValueError("probe report is not canonical")
    return report


__all__ = [
    "BoundedEnvironmentProbe", "COMMAND_SET_SHA256", "EnvironmentProbeCheck",
    "EnvironmentProbeReport", "EnvironmentProbeStatus", "ProbeCheckId",
    "ProbeCheckStatus", "ProbeCommandResult", "ProbeGateBinding",
    "admit_environment_probe_report", "subprocess_probe_runner",
]
