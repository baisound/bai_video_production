from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_environment_probe import (
    BoundedEnvironmentProbe,
    COMMAND_SET_SHA256,
    EnvironmentProbeStatus,
    ProbeCheckId,
    ProbeCheckStatus,
    ProbeCommandResult,
    ProbeGateBinding,
    admit_environment_probe_report,
    subprocess_probe_runner,
)


SHA = "sha256:" + "a" * 64
AUTHORITY_REF = "authorization://task054/01ARZ3NDEKTSV4RRFFQ69G5FAV"
OBSERVED_AT = "2026-08-25T01:00:00Z"


def _gate(**changes: object) -> ProbeGateBinding:
    values: dict[str, object] = {
        "authority_ref": AUTHORITY_REF,
        "authority_evidence_sha256": SHA,
        "confirmed_at": "2026-08-25T00:00:00Z",
        "expires_at": "2026-08-25T02:00:00Z",
    }
    values.update(changes)
    return ProbeGateBinding(**values)


def _outputs(*, gpu_exit: int = 0):
    return {
        "WSL": ProbeCommandResult(0, b"Default Distribution: Ubuntu\n"),
        "PYTHON": ProbeCommandResult(0, b"Python 3.12.3\n"),
        "GPU": ProbeCommandResult(gpu_exit, b"NVIDIA RTX 4090, 24564, 560.12\n" if gpu_exit == 0 else b""),
        "STORAGE": ProbeCommandResult(0, b"Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sda 100 20 80 20% /home/baisound\n"),
    }


def _probe(outputs):
    calls: list[tuple[tuple[str, ...], int]] = []

    def runner(command: tuple[str, ...], timeout: int) -> ProbeCommandResult:
        calls.append((command, timeout))
        if command == ("wsl.exe", "--status"):
            return outputs["WSL"]
        names = {"python3": "PYTHON", "nvidia-smi": "GPU", "df": "STORAGE"}
        return outputs[names[command[4]]]

    return BoundedEnvironmentProbe(command_runner=runner), calls


def test_exact_fixture_probe_is_available_and_body_free() -> None:
    probe, calls = _probe(_outputs())
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    assert report.status is EnvironmentProbeStatus.AVAILABLE
    assert tuple(item.check_id for item in report.checks) == tuple(ProbeCheckId)
    assert all(item.status is ProbeCheckStatus.AVAILABLE for item in report.checks)
    assert report.command_set_sha256 == COMMAND_SET_SHA256
    assert len(calls) == 4
    assert all(timeout == 15 for _, timeout in calls)
    payload = report.to_dict()
    assert "stdout" not in str(payload).casefold()
    assert "NVIDIA RTX 4090" in report.checks[2].version_summary
    assert admit_environment_probe_report(payload) == report


def test_missing_gpu_is_blocked_runtime_not_install_permission() -> None:
    probe, _ = _probe(_outputs(gpu_exit=127))
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    assert report.status is EnvironmentProbeStatus.BLOCKED_RUNTIME
    gpu = report.checks[2]
    assert gpu.status is ProbeCheckStatus.BLOCKED_RUNTIME
    assert gpu.detail_code == "COMMAND_UNAVAILABLE"
    assert report.state == "EVIDENCE_ONLY_NO_INSTALL_DOWNLOAD_TRAINING_OR_EXECUTION_AUTHORITY"


def test_expired_or_wrong_scope_gate_fails_before_any_command() -> None:
    probe, calls = _probe(_outputs())
    with pytest.raises(ValueError, match="not active"):
        probe.execute(gate=_gate(), observed_at="2026-08-25T03:00:00Z")
    assert calls == []
    with pytest.raises(ValueError, match="exact and approved"):
        _gate(scope="MODEL_DOWNLOAD")


def test_report_tamper_and_authority_forge_fail_closed() -> None:
    probe, _ = _probe(_outputs())
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    tampered = report.to_dict()
    tampered["status"] = "BLOCKED_RUNTIME"
    with pytest.raises(ValueError):
        admit_environment_probe_report(tampered)
    with pytest.raises(ValueError, match="cannot grant"):
        replace(report, state="INSTALL_ALLOWED")


def test_malformed_and_timeout_observations_are_blocked() -> None:
    outputs = _outputs()
    outputs["PYTHON"] = ProbeCommandResult(0, b"password=forbidden\n")
    outputs["STORAGE"] = ProbeCommandResult(-1, b"", timed_out=True)
    probe, _ = _probe(outputs)
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    assert report.status is EnvironmentProbeStatus.BLOCKED_RUNTIME
    assert report.checks[1].detail_code == "MALFORMED_VERSION"
    assert report.checks[3].detail_code == "PROBE_TIMEOUT"
    assert report.checks[1].version_summary is None


def test_command_result_and_runner_are_bounded_and_allowlisted() -> None:
    with pytest.raises(ValueError, match="outside bounds"):
        ProbeCommandResult(0, b"x" * (64 * 1024 + 1))
    with pytest.raises(ValueError, match="not allowlisted"):
        subprocess_probe_runner(("cmd.exe", "/c", "whoami"), 1)
    outputs = _outputs()
    outputs["GPU"] = ProbeCommandResult(
        -1, b"x" * (64 * 1024), output_truncated=True,
    )
    probe, _ = _probe(outputs)
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    assert report.checks[2].detail_code == "OUTPUT_LIMIT"
    assert report.checks[2].version_summary is None




def test_gate_binding_cannot_reverse_time_or_claim_rejected_decision() -> None:
    with pytest.raises(ValueError, match="expiry"):
        _gate(expires_at="2026-08-24T23:00:00Z")
    with pytest.raises(ValueError, match="exact and approved"):
        _gate(decision="REJECTED")


def test_report_schema_and_packaged_mirror_are_exact() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schemas" / "dbd-reasoning-environment-probe-report.schema.json"
    mirror_path = root / "src" / "ai_video_production" / "schema_resources" / schema_path.name
    assert schema_path.read_bytes() == mirror_path.read_bytes()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    probe, _ = _probe(_outputs())
    report = probe.execute(gate=_gate(), observed_at=OBSERVED_AT)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(report.to_dict())
    invalid = report.to_dict()
    invalid["checks"] = list(reversed(invalid["checks"]))
    with pytest.raises(Exception):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)
