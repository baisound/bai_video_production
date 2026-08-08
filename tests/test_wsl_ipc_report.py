import json
from pathlib import Path
from importlib import resources

from ai_video_production.schema_contracts import validate_instance
from ai_video_production.wsl_ipc_report import build_wsl_ipc_report


def phase(n, p50):
    return {'phase':n,'source_platform':'WSL2','host_kind':'DEFAULT_GATEWAY','port':43123,'auth_rejection_verified':True,'authenticated_roundtrip_verified':True,'round_trips':8,'latency_p50_ms':p50,'latency_p95_ms':p50+2}


def test_wsl_report_requires_same_endpoint_and_never_persists_token():
    report=build_wsl_ipc_report(phase(1,1.0),phase(2,1.5))
    schema=json.loads(resources.files('ai_video_production').joinpath('schema_resources','resolve-wsl-ipc-probe-report.schema.json').read_text())
    validate_instance(report,schema)
    assert report['same_endpoint_restart_verified'] is True
    assert report['auth_rejection_verified'] is True
    assert report['token_persisted'] is False
    assert set(report) >= {'token_persisted','same_endpoint_restart_verified'}
    assert not any(k for k in report if k in {'token','secret','authorization'})


def test_wsl_report_rejects_endpoint_change():
    import pytest
    p2=phase(2,1.5); p2['port']=43124
    with pytest.raises(ValueError, match='same endpoint'):
        build_wsl_ipc_report(phase(1,1.0),p2)


def test_wsl_report_rejects_missing_auth_isolation():
    import pytest
    p2=phase(2,1.5); p2['auth_rejection_verified']=False
    with pytest.raises(ValueError, match='unauthenticated'):
        build_wsl_ipc_report(phase(1,1.0),p2)


def test_windows_wsl_runner_does_not_touch_resolve_process():
    text=(Path(__file__).parents[1]/'tools/windows/run-wsl2-ipc-probe.ps1').read_text(encoding='utf-8')
    assert 'Get-Process -Name "Resolve"' not in text
    assert 'taskkill' not in text.lower()
    assert 'Stop-Process' in text  # only the temporary probe server process
    assert 'wsl.exe' in text
    assert 'same-port Windows server restart' in text
