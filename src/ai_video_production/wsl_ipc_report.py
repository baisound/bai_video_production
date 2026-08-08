from __future__ import annotations
import argparse, json, statistics
from pathlib import Path
from typing import Any
from .ids import IdKind, generate_id
from .serialization import utc_now_iso
from .schema_contracts import validate_instance
from importlib import resources

def build_wsl_ipc_report(phase1: dict[str,Any], phase2: dict[str,Any]) -> dict[str,Any]:
    required=('host_kind','port','auth_rejection_verified','authenticated_roundtrip_verified','round_trips','latency_p50_ms','latency_p95_ms')
    if not all(k in phase1 and k in phase2 for k in required): raise ValueError('both WSL phases must be successful')
    if not (phase1['auth_rejection_verified'] and phase2['auth_rejection_verified']):
        raise ValueError('both WSL phases must prove unauthenticated HTTP rejection')
    if not (phase1['authenticated_roundtrip_verified'] and phase2['authenticated_roundtrip_verified']):
        raise ValueError('both WSL phases must prove authenticated round trips')
    same=phase1['host_kind']==phase2['host_kind'] and phase1['port']==phase2['port']
    if not same:
        raise ValueError('WSL restart evidence must use the same endpoint host kind and port')
    vals=[phase1['latency_p50_ms'],phase2['latency_p50_ms']]
    p95=max(phase1['latency_p95_ms'],phase2['latency_p95_ms'])
    return {
        'schema_version':'1.0.0','probe_id':generate_id(IdKind.EVIDENCE),'created_at':utc_now_iso(),
        'source_platform':'WSL2','candidate':'LOCALHOST_HTTP_JSON','endpoint_host_kind':phase1['host_kind'],'endpoint_port':phase1['port'],
        'auth_rejection_verified':bool(phase1['auth_rejection_verified'] and phase2['auth_rejection_verified']),
        'authenticated_roundtrip_verified':bool(phase1['authenticated_roundtrip_verified'] and phase2['authenticated_roundtrip_verified']),
        'same_endpoint_restart_verified':same,'round_trips':int(phase1['round_trips']+phase2['round_trips']),
        'latency_p50_ms':round(statistics.median(vals),3),'latency_p95_ms':round(p95,3),'token_persisted':False,
        'notes':['Windows probe server was stopped and restarted on the same port between WSL2 phases.','No bearer token is written to Evidence.']
    }

def main():
    p=argparse.ArgumentParser(); p.add_argument('--phase1',required=True); p.add_argument('--phase2',required=True); p.add_argument('--output',required=True); args=p.parse_args()
    a=json.loads(Path(args.phase1).read_text()); b=json.loads(Path(args.phase2).read_text()); report=build_wsl_ipc_report(a,b)
    schema=json.loads(resources.files('ai_video_production').joinpath('schema_resources','resolve-wsl-ipc-probe-report.schema.json').read_text())
    validate_instance(report,schema); Path(args.output).write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
if __name__=='__main__': main()
