from pathlib import Path

from ai_video_production.ipc_probe import IpcCandidate, run_ipc_probe
from ai_video_production.schema_contracts import validate_instance

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "resolve-ipc-probe-report.schema.json"


def test_ipc_probe_http_auth_restart_and_provisional_adr():
    report = run_ipc_probe()
    validate_instance(report, SCHEMA)
    rows = {row["candidate"]: row for row in report["results"]}
    http = rows[IpcCandidate.LOCALHOST_HTTP_JSON.value]
    assert http["status"] == "MEASURED"
    assert http["auth_verified"] is True
    assert http["restart_verified"] is True
    assert http["round_trips"] >= 1
    assert report["adr"]["status"] == "PROVISIONAL"
    assert report["adr"]["selected"] == "LOCALHOST_HTTP_JSON"
    assert report["adr"]["wsl2_reachability_verified"] is False


def test_non_windows_does_not_infer_named_pipe_support(monkeypatch):
    import ai_video_production.ipc_probe as module
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    report = module.run_ipc_probe()
    rows = {row["candidate"]: row for row in report["results"]}
    pipe = rows[IpcCandidate.WINDOWS_NAMED_PIPE.value]
    assert pipe["status"] == "PROBE_REQUIRED"
    assert pipe["target_platform_measured"] is False
