"""Loopback-only Subtitle Workspace editor."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
from typing import Any
from urllib.parse import urlsplit
import webbrowser

from .native_file_dialog import NativeFileDialogUnavailable, WindowsNativeFileDialog
from .subtitle_workspace import SrtWorkspaceCodec, SubtitleWorkspace, SubtitleWorkspaceStore


PRODUCT_VERSION = "0.23.0"
MAX_REQUEST_BYTES = 256 * 1024

_HTML = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BAI Subtitle Workspace</title><style nonce="__NONCE__">body{font:15px/1.5 system-ui;margin:auto;max-width:1200px;padding:20px;background:#f5f7fa;color:#17202a}button,input,textarea{font:inherit}button{padding:8px 12px;margin:3px;border:0;border-radius:7px;background:#1769e0;color:#fff;cursor:pointer}button.secondary{background:#425466}button.danger{background:#b42318}.bar,.cue{background:#fff;border:1px solid #d5dde5;border-radius:10px;padding:12px;margin:10px 0}.file-grid{display:grid;grid-template-columns:110px minmax(220px,1fr) auto auto;gap:8px;align-items:center;margin:8px 0}.file-grid input{width:100%;padding:8px;box-sizing:border-box}.row{display:grid;grid-template-columns:130px 130px 1fr auto;gap:8px;align-items:start}.row input,.row textarea{width:100%;padding:7px;box-sizing:border-box}.muted{color:#657382}.notice{display:none;border-radius:8px;padding:10px 12px;margin:10px 0;font-weight:600;white-space:pre-wrap;overflow-wrap:anywhere}.notice.ok{display:block;color:#146c43;background:#e9f8ef;border:1px solid #9bd8b5}.notice.error{display:block;color:#9f1c14;background:#fff0ee;border:1px solid #efaaa4}@media(max-width:760px){.file-grid,.row{grid-template-columns:1fr}.file-grid button,.row button{width:100%}}</style></head>
<body><h1>字幕Workspace / Subtitle Workspace</h1><p class="muted">企画SRT、ASR、持込SRTを同じ画面で編集します。AI誤字・脱字チェックをONにしても、この画面ではAI通信・課金を開始しません。</p>
<section class="bar"><div class="file-grid"><strong>読み込み</strong><input id="importPath" placeholder="SRTファイルを選択してください"><button id="browseImport" class="secondary">ファイルを選択…</button><button id="import">SRTを読込</button></div><div class="file-grid"><strong>書き出し</strong><input id="exportPath" placeholder="保存先とファイル名を選択してください"><button id="browseExport" class="secondary">保存先を選択…</button><button id="export">SRTを書出</button></div><p class="muted">Windowsでは選択ボタンからExplorer形式のファイル／保存ダイアログを開けます。パス欄へ直接入力することもできます。</p><div id="msg" class="notice" role="status" aria-live="polite"></div><label><input id="ai" type="checkbox"> AI誤字・脱字チェックを許可（既定OFF）</label></section>
<button id="append">＋末尾に追加</button><div id="cues"></div><footer class="muted">BAI Video Production v__VERSION__ — <span id="rev"></span></footer>
<script nonce="__NONCE__">const CSRF=__CSRF__;let w;const cues=document.querySelector('#cues'),msg=document.querySelector('#msg');
function ms(v){const m=/^(\d+):(\d\d):(\d\d)[,.](\d\d\d)$/.exec(v);if(!m)throw Error('時刻はHH:MM:SS,mmm形式です');return((+m[1]*60 + +m[2])*60 + +m[3])*1000 + +m[4]}function ts(v){let h=Math.floor(v/3600000);v%=3600000;let m=Math.floor(v/60000);v%=60000;let s=Math.floor(v/1000),x=v%1000;return`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(x).padStart(3,'0')}`}
function show(value,bad=false){const text=value instanceof Error?value.message:String(value);msg.className=`notice ${bad?'error':'ok'}`;msg.textContent=text}
function networkError(){return Error('ローカルサーバーに接続できません。Subtitle Workspaceを再起動してから、このページを再読み込みしてください。')}
async function api(url,options){let r;try{r=await fetch(url,options)}catch(_){throw networkError()}let d;try{d=await r.json()}catch(_){if(!r.ok)throw Error(`操作に失敗しました (HTTP ${r.status})`);throw Error('ローカルサーバーから不正な応答を受信しました')}if(!r.ok)throw Error(d.message||'操作に失敗しました');return d}
async function call(payload){if(!w)throw networkError();const d=await api('/api/workspace',{method:'POST',headers:{'Content-Type':'application/json','X-BAI-CSRF':CSRF},body:JSON.stringify({...payload,revision:w.revision})});w=d;render();return d}
async function choose(kind){const d=await api('/api/dialog',{method:'POST',headers:{'Content-Type':'application/json','X-BAI-CSRF':CSRF},body:JSON.stringify({kind})});return d.cancelled?null:d.path}
function render(){if(!w)return;document.querySelector('#rev').textContent=`Revision ${w.revision}`;document.querySelector('#ai').checked=w.ai_typo_check_enabled;cues.replaceChildren();w.cues.forEach(c=>{const box=document.createElement('section');box.className='cue';box.innerHTML=`<div class="row"><input value="${ts(c.start_ms)}" aria-label="開始"><input value="${ts(c.end_ms)}" aria-label="終了"><textarea rows="2"></textarea><div><button data-a="save">保存</button><button data-a="before">前に挿入</button><button data-a="after">後に挿入</button><button data-a="delete" class="danger">削除</button></div></div><small class="muted">${c.origin} / ${c.review_state} / ${c.cue_id}</small>`;box.querySelector('textarea').value=c.text;box.addEventListener('click',async e=>{if(!e.target.dataset.a)return;try{const a=e.target.dataset.a;if(a==='save'){const q=box.querySelectorAll('input');await call({operation:'update',cue_id:c.cue_id,start_ms:ms(q[0].value),end_ms:ms(q[1].value),text:box.querySelector('textarea').value});show('字幕を保存しました。')}else if(a==='delete'){await call({operation:'delete',cue_id:c.cue_id});show('字幕を削除しました。')}else{await call({operation:'insert_relative',cue_id:c.cue_id,position:a,text:'新しい字幕'});show(a==='before'?'選択した字幕の前に追加しました。':'選択した字幕の後に追加しました。')}}catch(e){show(e,true)}});cues.append(box)})}
document.querySelector('#append').onclick=async()=>{try{await call({operation:'insert_relative',cue_id:null,position:'append',text:'新しい字幕'});show('末尾に字幕を追加しました。')}catch(e){show(e,true)}};
document.querySelector('#ai').onchange=async e=>{try{await call({operation:'set_ai',enabled:e.target.checked});show(e.target.checked?'AI候補を許可しました。AIはまだ実行していません。':'AIチェックをOFFにしました。')}catch(err){show(err,true)}};
document.querySelector('#browseImport').onclick=async()=>{try{const p=await choose('open_srt');if(p){document.querySelector('#importPath').value=p;show(`読み込みファイルを選択しました:
${p}`)}}catch(e){show(e,true)}};
document.querySelector('#browseExport').onclick=async()=>{try{const p=await choose('save_srt');if(p){document.querySelector('#exportPath').value=p;show(`書き出し先を選択しました:
${p}`)}}catch(e){show(e,true)}};
document.querySelector('#import').onclick=async()=>{try{let input=document.querySelector('#importPath');if(!input.value){const p=await choose('open_srt');if(!p)return;input.value=p}if(w&&w.cues.length&&!window.confirm('現在の字幕Workspaceを選択したSRTで置き換えます。続行しますか？'))return;const result=await call({operation:'import_srt',path:input.value});show(`SRTを取り込みました (${result.cues.length}件):
${input.value}`)}catch(e){show(e,true)}};
document.querySelector('#export').onclick=async()=>{try{let input=document.querySelector('#exportPath');if(!input.value){const p=await choose('save_srt');if(!p)return;input.value=p}const result=await call({operation:'export_srt',path:input.value});show(`SRT書き出し成功 (${result.exported_bytes} bytes):
${result.exported_path}`)}catch(e){show(e,true)}};
api('/api/workspace').then(x=>{w=x;render()}).catch(e=>show(e,true));</script></body></html>"""


class SubtitleWorkspaceWebService:
    def __init__(self, workspace_path: str | Path, *, file_dialog: Any | None = None) -> None:
        self.path = Path(workspace_path).expanduser().resolve()
        self.workspace = SubtitleWorkspaceStore.load(self.path) if self.path.exists() else SubtitleWorkspace.empty()
        self._lock = threading.Lock()
        self._dialog_lock = threading.Lock()
        self.file_dialog = file_dialog or WindowsNativeFileDialog()

    def form(self) -> dict[str, Any]:
        with self._lock: return self.workspace.to_dict()

    def apply(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("request must be an object")
        with self._lock:
            if payload.get("revision") != self.workspace.revision:
                raise ValueError("workspace revision conflict; reload before editing")
            op = payload.get("operation")
            old = self.workspace
            if op == "insert": self.workspace = old.insert(int(payload["index"]), int(payload["start_ms"]), int(payload["end_ms"]), str(payload["text"]))
            elif op == "insert_relative": self.workspace = old.insert_relative(
                str(payload["cue_id"]) if payload.get("cue_id") is not None else None,
                str(payload["position"]),
                str(payload.get("text", "新しい字幕")),
            )
            elif op == "update": self.workspace = old.update(str(payload["cue_id"]), start_ms=int(payload["start_ms"]), end_ms=int(payload["end_ms"]), text=str(payload["text"]))
            elif op == "delete": self.workspace = old.delete(str(payload["cue_id"]))
            elif op == "set_ai": self.workspace = old.set_ai_typo_check(payload.get("enabled") is True)
            elif op == "import_srt":
                imported = SrtWorkspaceCodec.import_path(str(payload["path"]))
                self.workspace = SubtitleWorkspace(old.workspace_id, old.revision + 1, imported.cues, old.ai_typo_check_enabled)
            elif op == "export_srt":
                target = Path(str(payload["path"])).expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(SrtWorkspaceCodec.render(old)); handle.flush(); os.fsync(handle.fileno())
                    os.replace(temporary, target)
                except Exception:
                    Path(temporary).unlink(missing_ok=True)
                    raise
                result = old.to_dict()
                result["exported_path"] = str(target)
                result["exported_bytes"] = target.stat().st_size
                return result
            else: raise ValueError("unsupported workspace operation")
            SubtitleWorkspaceStore.save(self.path, self.workspace, expected_revision=old.revision if self.path.exists() else None)
            return self.workspace.to_dict()

    def choose_path(self, kind: str) -> dict[str, Any]:
        with self._dialog_lock:
            if kind == "open_srt":
                selected = self.file_dialog.choose_open_srt()
            elif kind == "save_srt":
                selected = self.file_dialog.choose_save_srt()
            else:
                raise ValueError("unsupported dialog kind")
        return {"path": selected, "cancelled": selected is None}


def launch_server(service: SubtitleWorkspaceWebService, port: int = 8770):
    csrf=secrets.token_urlsafe(32); html=_HTML.replace("__NONCE__", csrf).replace("__CSRF__", json.dumps(csrf)).replace("__VERSION__", PRODUCT_VERSION).encode()
    class Handler(BaseHTTPRequestHandler):
        def _send(self,status:int,body:bytes,content_type="application/json"):
            self.send_response(status);self.send_header("Content-Type",f"{content_type}; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-store");self.send_header("Content-Security-Policy",f"default-src 'none'; style-src 'nonce-{csrf}'; script-src 'nonce-{csrf}'; connect-src 'self'");self.end_headers();self.wfile.write(body)
        def _valid(self):
            actual_port = self.server.server_address[1]
            return urlsplit(self.path).path in {"/","/api/workspace","/api/dialog"} and self.headers.get("Host") in {f"127.0.0.1:{actual_port}",f"localhost:{actual_port}"}
        def do_GET(self):
            if not self._valid(): return self._send(400,b'{"message":"invalid request"}')
            if urlsplit(self.path).path=="/": return self._send(200,html,"text/html")
            self._send(200,json.dumps(service.form(),ensure_ascii=False).encode())
        def do_POST(self):
            try:
                if not self._valid() or self.headers.get("X-BAI-CSRF")!=csrf: raise ValueError("invalid request")
                size=int(self.headers.get("Content-Length","0"));
                if not 0<size<=MAX_REQUEST_BYTES: raise ValueError("request size is invalid")
                payload=json.loads(self.rfile.read(size))
                if urlsplit(self.path).path=="/api/dialog": result=service.choose_path(str(payload.get("kind", "")))
                else: result=service.apply(payload)
                self._send(200,json.dumps(result,ensure_ascii=False).encode())
            except (ValueError,KeyError,TypeError,json.JSONDecodeError,NativeFileDialogUnavailable) as exc: self._send(400,json.dumps({"message":str(exc)},ensure_ascii=False).encode())
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler); actual_port=server.server_address[1]; thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();return server,thread,f"http://127.0.0.1:{actual_port}/"


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--workspace",type=Path,default=Path("subtitle-workspace.json"));p.add_argument("--port",type=int,default=8770);p.add_argument("--no-browser",action="store_true");a=p.parse_args(argv)
    server,thread,url=launch_server(SubtitleWorkspaceWebService(a.workspace),a.port);print(f"Subtitle Workspace: {url}")
    if not a.no_browser:webbrowser.open(url)
    try: thread.join()
    except KeyboardInterrupt: server.shutdown();thread.join();return 0

if __name__=="__main__": raise SystemExit(main())
