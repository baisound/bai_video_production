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

    for name in ("resolve-capability-report.schema.json", "resolve-ipc-probe-report.schema.json", "resolve-wsl-ipc-probe-report.schema.json"):
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


def test_worker_preserves_fail_closed_sandbox_error_as_schema_valid_evidence(tmp_path, monkeypatch):
    class UnnamedProject:
        pass
    class PM:
        def GetCurrentProject(self):
            return UnnamedProject()
    class Resolve:
        def GetProjectManager(self):
            return PM()
        def GetVersionString(self):
            return '21.0.2.4'
        def GetVersion(self):
            return [21, 0, 2, 4, '']
        def GetProductName(self):
            return 'DaVinci Resolve Studio'

    monkeypatch.setattr(resolve_probe_cli.ResolveModuleLoader, 'connect', lambda _self: (Resolve(), 'TEST'))
    output = tmp_path / 'sandbox-refused.json'
    args = resolve_probe_cli.build_parser().parse_args([
        '--worker', '--kind', 'resolve', '--output', str(output),
        '--allow-mutation-probes', '--sandbox-project', 'BAI_CAPABILITY_PROBE_UNIT',
        '--probe-assets-dir', str(tmp_path / 'probe-assets'),
    ])
    assert resolve_probe_cli._run_worker(args) == 2
    payload = json.loads(output.read_text())
    validate_instance(payload, ROOT / 'schemas' / 'resolve-capability-report.schema.json')
    assert payload['resolve']['connected'] is True
    assert payload['mode'] == 'SANDBOX_MUTATION'
    assert payload['mutation_gate']['authorized'] is False
    assert payload['mutation_gate']['executed'] is False
    assert payload['mutation_error']['code'] == 'ERR_RESOLVE_CURRENT_PROJECT_NAME_UNVERIFIED'


def test_supervisor_derives_persistent_probe_assets_dir_when_omitted(tmp_path, monkeypatch):
    from types import SimpleNamespace

    captured = {}

    def fake_run(command, **_kwargs):
        captured['command'] = command
        worker_output = Path(command[command.index('--output') + 1])
        payload = resolve_probe_cli.ResolveCapabilityProbe(None, module_source_kind='TEST').run()
        resolve_probe_cli._write_report(worker_output, payload, 'resolve-capability-report.schema.json')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(resolve_probe_cli.subprocess, 'run', fake_run)
    output = tmp_path / 'evidence' / 'report.json'
    args = resolve_probe_cli.build_parser().parse_args([
        '--kind', 'resolve', '--output', str(output), '--timeout-seconds', '5',
        '--allow-mutation-probes', '--sandbox-project', 'BAI_CAPABILITY_PROBE_UNIT',
    ])
    assert resolve_probe_cli._run_supervised(args) == 0
    expected = output.parent / 'probe-assets' / 'BAI_CAPABILITY_PROBE_UNIT'
    command = captured['command']
    assert command[command.index('--probe-assets-dir') + 1] == str(expected)


def test_supervisor_forwards_persistent_probe_assets_dir_to_worker(tmp_path, monkeypatch):
    from types import SimpleNamespace

    captured = {}

    def fake_run(command, **_kwargs):
        captured['command'] = command
        worker_output = Path(command[command.index('--output') + 1])
        payload = resolve_probe_cli.ResolveCapabilityProbe(None, module_source_kind='TEST').run()
        resolve_probe_cli._write_report(worker_output, payload, 'resolve-capability-report.schema.json')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(resolve_probe_cli.subprocess, 'run', fake_run)
    output = tmp_path / 'evidence' / 'report.json'
    assets = tmp_path / 'evidence' / 'probe-assets' / 'BAI_CAPABILITY_PROBE_UNIT'
    args = resolve_probe_cli.build_parser().parse_args([
        '--kind', 'resolve', '--output', str(output), '--timeout-seconds', '5',
        '--allow-mutation-probes', '--sandbox-project', 'BAI_CAPABILITY_PROBE_UNIT',
        '--probe-assets-dir', str(assets),
    ])
    assert resolve_probe_cli._run_supervised(args) == 0
    command = captured['command']
    assert command[command.index('--probe-assets-dir') + 1] == str(assets)


def test_supervisor_preserves_schema_valid_nonzero_worker_evidence(tmp_path, monkeypatch):
    from types import SimpleNamespace

    def fake_run(command, **_kwargs):
        worker_output = Path(command[command.index('--output') + 1])
        payload = resolve_probe_cli.ResolveCapabilityProbe(None, module_source_kind='TEST').run()
        payload['mutation_error'] = {
            'code': 'ERR_TEST_FAIL_CLOSED',
            'category': 'SECURITY',
            'message': 'blocked',
            'retryable': False,
            'details': {},
        }
        resolve_probe_cli._write_report(worker_output, payload, 'resolve-capability-report.schema.json')
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(resolve_probe_cli.subprocess, 'run', fake_run)
    output = tmp_path / 'preserved.json'
    args = resolve_probe_cli.build_parser().parse_args([
        '--kind', 'resolve', '--output', str(output), '--timeout-seconds', '5'
    ])
    assert resolve_probe_cli._run_supervised(args) == 2
    payload = json.loads(output.read_text())
    validate_instance(payload, ROOT / 'schemas' / 'resolve-capability-report.schema.json')
    assert payload['mutation_error']['code'] == 'ERR_TEST_FAIL_CLOSED'
    assert 'connection_error' not in payload
