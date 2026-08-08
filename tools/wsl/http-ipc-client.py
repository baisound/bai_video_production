from __future__ import annotations
import argparse, json, os, socket, statistics, time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def gateway_from_proc():
    try:
        for line in Path('/proc/net/route').read_text().splitlines()[1:]:
            fields=line.split()
            if len(fields) >= 3 and fields[1] == '00000000':
                raw=bytes.fromhex(fields[2]); return socket.inet_ntoa(raw[::-1])
    except Exception: pass
    return None

def candidates():
    out=[('LOOPBACK','127.0.0.1')]
    gw=gateway_from_proc()
    if gw: out.append(('DEFAULT_GATEWAY',gw))
    try:
        for line in Path('/etc/resolv.conf').read_text().splitlines():
            if line.startswith('nameserver '): out.append(('RESOLV_NAMESERVER',line.split()[1]))
    except Exception: pass
    seen=set(); result=[]
    for kind,host in out:
        if host not in seen: seen.add(host); result.append((kind,host))
    return result

def pct(vals,q):
    s=sorted(vals); return s[max(0,min(len(s)-1,round((len(s)-1)*q)))]

p=argparse.ArgumentParser(); p.add_argument('--port',type=int,required=True); p.add_argument('--phase',type=int,choices=(1,2),required=True); p.add_argument('--output',required=True); p.add_argument('--expect-host-kind',default=''); args=p.parse_args()
token=os.environ.get('BAI_IPC_PROBE_TOKEN','')
if len(token)<24: raise SystemExit('BAI_IPC_PROBE_TOKEN missing/too short')
errors=[]
for kind,host in candidates():
    if args.expect_host_kind and kind != args.expect_host_kind: continue
    url=f'http://{host}:{args.port}/health'
    try:
        rejected=False
        try: urlopen(url,timeout=2)
        except HTTPError as exc: rejected=exc.code==401
        if not rejected:
            raise RuntimeError('unauthenticated request was not rejected with HTTP 401')
        vals=[]
        for _ in range(8):
            req=Request(url,headers={'Authorization':f'Bearer {token}'})
            start=time.perf_counter()
            with urlopen(req,timeout=2) as res:
                payload=json.loads(res.read())
                if res.status != 200 or payload != {'ok':True}: raise RuntimeError('unexpected response')
            vals.append((time.perf_counter()-start)*1000)
        result={'phase':args.phase,'source_platform':'WSL2','host_kind':kind,'port':args.port,'auth_rejection_verified':rejected,'authenticated_roundtrip_verified':True,'round_trips':len(vals),'latency_p50_ms':round(statistics.median(vals),3),'latency_p95_ms':round(pct(vals,0.95),3)}
        Path(args.output).write_text(json.dumps(result,separators=(',',':')),encoding='utf-8'); raise SystemExit(0)
    except Exception as exc: errors.append(f'{kind}:{type(exc).__name__}')
Path(args.output).write_text(json.dumps({'phase':args.phase,'source_platform':'WSL2','port':args.port,'errors':errors},separators=(',',':')),encoding='utf-8')
raise SystemExit(1)
