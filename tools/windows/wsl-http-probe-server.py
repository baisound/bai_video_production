from __future__ import annotations
import argparse, json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class Handler(BaseHTTPRequestHandler):
    token = ""
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404); self.end_headers(); return
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self.send_response(401); self.end_headers(); return
        payload=b'{"ok":true}'
        self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def log_message(self, fmt, *args): return

p=argparse.ArgumentParser(); p.add_argument('--port',type=int,required=True); p.add_argument('--ready-file',required=True); args=p.parse_args()
token=os.environ.get('BAI_IPC_PROBE_TOKEN','')
if len(token) < 24: raise SystemExit('BAI_IPC_PROBE_TOKEN missing/too short')
handler=type('ProbeHandler',(Handler,),{'token':token})
server=ThreadingHTTPServer(('0.0.0.0',args.port),handler)
Path(args.ready_file).write_text(json.dumps({'ready':True,'port':args.port}),encoding='utf-8')
try: server.serve_forever()
finally: server.server_close()
