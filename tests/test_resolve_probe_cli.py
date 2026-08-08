import json
from pathlib import Path

from ai_video_production import resolve_probe_cli
from ai_video_production.schema_contracts import validate_instance

ROOT = Path(__file__).parents[1]


def test_cli_worker_writes_disconnected_schema_valid_report(tmp_path, monkeypatch):
    def fail_connect(self):
        from ai_video_production.errors import ProductError, ProductErrorCategory
        raise ProductError(
            "ERR_RESOLVE_NOT_AVAILABLE",
            "not running",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            True,
            details={"module_source_kind": "WINDOWS_PROGRAMDATA"},
        )

    monkeypatch.setattr(resolve_probe_cli.ResolveModuleLoader, "connect", fail_connect)
    args = resolve_probe_cli.build_parser().parse_args(["--worker", "--kind", "resolve", "--output", str(tmp_path / "out.json")])
    assert resolve_probe_cli._run_worker(args) == 0
    payload = json.loads((tmp_path / "out.json").read_text())
    validate_instance(payload, ROOT / "schemas" / "resolve-capability-report.schema.json")
    assert payload["resolve"]["connected"] is False
    assert payload["connection_error"]["code"] == "ERR_RESOLVE_NOT_AVAILABLE"
    assert payload["resolve"]["module_source_kind"] == "WINDOWS_PROGRAMDATA"
    root = next(row for row in payload["capabilities"] if row["capability_id"] == "resolve.connection")
    assert root["error_code"] == "ERR_RESOLVE_NOT_AVAILABLE"
    assert root["error_type"] == "EXTERNAL_DEPENDENCY"
    assert root["notes"] == ["not running"]


def test_supervisor_timeout_writes_schema_valid_resolve_evidence(tmp_path, monkeypatch):
    import subprocess

    def time_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["python"], timeout=1)

    monkeypatch.setattr(resolve_probe_cli.subprocess, "run", time_out)
    output = tmp_path / "timeout.json"
    args = resolve_probe_cli.build_parser().parse_args([
        "--kind", "resolve", "--output", str(output), "--timeout-seconds", "1"
    ])
    assert resolve_probe_cli._run_supervised(args) == 124
    payload = json.loads(output.read_text())
    validate_instance(payload, ROOT / "schemas" / "resolve-capability-report.schema.json")
    assert payload["supervision"] == {"timed_out": True, "timeout_seconds": 1, "worker_exit_code": None}
    assert payload["connection_error"]["code"] == "ERR_RESOLVE_PROBE_TIMEOUT"


def test_supervisor_worker_failure_writes_schema_valid_ipc_evidence(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(resolve_probe_cli.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=7))
    output = tmp_path / "ipc-failed.json"
    args = resolve_probe_cli.build_parser().parse_args([
        "--kind", "ipc", "--output", str(output), "--timeout-seconds", "5"
    ])
    assert resolve_probe_cli._run_supervised(args) == 7
    payload = json.loads(output.read_text())
    validate_instance(payload, ROOT / "schemas" / "resolve-ipc-probe-report.schema.json")
    assert payload["supervision"]["timed_out"] is False
    assert payload["supervision"]["worker_exit_code"] == 7
    assert all(row["status"] == "PROBE_REQUIRED" for row in payload["results"])


def test_packaged_schema_resources_match_canonical_schemas():
    from importlib import resources

    for name in ("resolve-capability-report.schema.json", "resolve-ipc-probe-report.schema.json"):
        canonical = json.loads((ROOT / "schemas" / name).read_text())
        packaged_text = resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8")
        assert json.loads(packaged_text) == canonical


def test_cli_worker_distinguishes_actual_module_discovery_failure(tmp_path, monkeypatch):
    def fail_connect(self):
        from ai_video_production.errors import ProductError, ProductErrorCategory
        raise ProductError(
            "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND",
            "bridge missing",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            False,
            details={"platform": "Windows"},
        )

    monkeypatch.setattr(resolve_probe_cli.ResolveModuleLoader, "connect", fail_connect)
    output = tmp_path / "module-missing.json"
    args = resolve_probe_cli.build_parser().parse_args([
        "--worker", "--kind", "resolve", "--output", str(output)
    ])
    assert resolve_probe_cli._run_worker(args) == 0
    payload = json.loads(output.read_text())
    validate_instance(payload, ROOT / "schemas" / "resolve-capability-report.schema.json")
    assert payload["resolve"]["module_source_kind"] == "MODULE_NOT_FOUND"
    assert payload["connection_error"]["code"] == "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND"
    root = next(row for row in payload["capabilities"] if row["capability_id"] == "resolve.connection")
    assert root["error_code"] == "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND"
