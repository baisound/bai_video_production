"""Local-only interactive AI Connection settings screen."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from typing import Any, Sequence
from urllib.parse import urlsplit
import webbrowser

from .ai_connections import AiConnectionProfile, ConnectionAvailability
from .connection_settings import AiConnectionSettingsService
from .connection_settings_store import (
    ConnectionCatalogEditor, ConnectionSettingsEditor, ConnectionSettingsFormBuilder,
    ConnectionSettingsStore,
)
from .errors import ProductError, ProductErrorCategory


MAX_REQUEST_BYTES = 64 * 1024


_HTML = r"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BAI Video Production — AI Connection Settings</title>
  <style nonce="__NONCE__">
    :root{color-scheme:light;--ink:#18202b;--muted:#607080;--line:#d8e0e8;--blue:#1769e0;--ok:#18794e;--warn:#a15c00;--bg:#f4f7fa}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
    header,main{max-width:1100px;margin:auto;padding:24px}header{padding-bottom:8px}h1{font-size:clamp(1.55rem,4vw,2.3rem);margin:.2rem 0}.lead{color:var(--muted);max-width:850px}
    .notice{background:#eaf3ff;border-left:5px solid var(--blue);padding:14px 18px;border-radius:8px;margin:18px 0}.grid{display:grid;gap:16px}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 2px 8px #24364b0d}
    .card-head{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}.badge{font-weight:700;padding:4px 10px;border-radius:999px;background:#eef2f6}.READY{color:var(--ok);background:#e8f6ef}.BLOCKED{color:#9a3412;background:#fff0e8}.DISABLED{color:#59636e}
    .fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:14px}label{font-weight:700;display:block}select,input{width:100%;font:inherit;margin-top:6px;padding:10px;border:1px solid #9aa8b6;border-radius:8px;background:white}input[type=checkbox]{width:auto;margin-right:8px}.help,.route-meta{color:var(--muted);font-size:.9rem;margin:.35rem 0 0}
    details.card{margin-top:18px}summary{font-size:1.25rem;font-weight:800;cursor:pointer}.catalog-list{display:grid;gap:8px;margin-top:16px}.catalog-row{display:flex;gap:10px;justify-content:space-between;align-items:center;border-top:1px solid var(--line);padding-top:10px}.catalog-row button,.secondary{background:#425466;padding:7px 12px}.checks{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.checks label{font-weight:600}
    .actions{position:sticky;bottom:0;background:#ffffffed;border:1px solid var(--line);border-radius:14px;padding:14px;margin-top:18px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}button{font:inherit;font-weight:700;padding:11px 20px;border:0;border-radius:9px;background:var(--blue);color:white;cursor:pointer}button:disabled{opacity:.55;cursor:wait}#message{font-weight:700}.error{color:#b42318}.success{color:var(--ok)}
    footer{color:var(--muted);font-size:.88rem;margin:28px 0}@media(max-width:600px){header,main{padding:16px}.actions{position:static}}
  </style>
</head>
<body>
<header><h1>AI Connection 設定</h1><p class="lead">企画・動画・画像・音声・音楽で使う方法と優先Modelを選びます。専門用語が分からなくても、各選択肢の説明を確認しながら設定できます。</p></header>
<main>
  <div class="notice"><strong>安全について：</strong> この画面の保存操作だけでは、API課金、素材生成、動画編集は始まりません。開始には別の「GO」確認が必要です。<br><span lang="en">Saving here never starts paid APIs, generation, or editing. A separate GO approval is required.</span></div>
  <div id="cards" class="grid" aria-live="polite"></div>
  <div class="actions"><button id="save" type="button">設定を保存 / Save settings</button><span id="message" role="status"></span></div>
  <details class="card" id="catalog"><summary>Provider・Model候補 / Provider &amp; model catalog</summary>
    <p class="help">候補の登録は実行Adapterの完成を意味しません。APIキーはここへ入力しないでください。 / Catalog registration does not mean its execution adapter is implemented. Never enter an API key here.</p>
    <div class="fields">
      <label>Route ID<input id="cat-route" maxlength="128" placeholder="planning-openai"></label>
      <label>用途 / Workload<select id="cat-workload"></select></label>
      <label>Provider family<select id="cat-family"></select></label>
      <label>Provider ID<input id="cat-provider" maxlength="128" placeholder="openai"></label>
      <label>Model ID<input id="cat-model" maxlength="128" placeholder="configured-model"></label>
      <label>費用区分 / Cost class<select id="cat-cost"></select></label>
      <label>Reasoning<select id="cat-reasoning"></select></label>
      <label>Capabilities（カンマ区切り）<input id="cat-capabilities" placeholder="SCRIPT,PROPOSAL"></label>
    </div>
    <div class="checks"><label><input type="checkbox" id="cat-credential">Credentialが必要 / required</label><label><input type="checkbox" id="cat-enabled" checked>有効 / enabled</label></div>
    <div class="actions"><button id="catalog-save" type="button">候補を保存 / Save candidate</button><button id="catalog-new" class="secondary" type="button">新規入力 / New</button><span id="catalog-message" role="status"></span></div>
    <div id="catalog-list" class="catalog-list"></div>
  </details>
  <footer>Local-only screen — BAI Video Production <span id="revision"></span></footer>
</main>
<script nonce="__NONCE__">const CSRF=__CSRF_JSON__;
const cards=document.getElementById('cards'), save=document.getElementById('save'), message=document.getElementById('message'),catMessage=document.getElementById('catalog-message');let form;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function routeText(r){return `${r.provider_family} / ${r.model_id} / ${r.cost_class}${r.credential_required?' / Credential required':''}`}
function options(select,values){select.replaceChildren();values.forEach(v=>{const o=el('option',v);o.value=v;select.append(o)})}
function allRoutes(){return form.workloads.flatMap(w=>w.routes.map(r=>({...r,workload:w.workload})))}
function resetCatalog(){document.getElementById('cat-route').disabled=false;document.getElementById('cat-workload').disabled=false;document.getElementById('cat-route').value='';document.getElementById('cat-provider').value='';document.getElementById('cat-model').value='';document.getElementById('cat-capabilities').value='';document.getElementById('cat-credential').checked=false;document.getElementById('cat-enabled').checked=true;catMessage.textContent=''}
function editRoute(r){document.getElementById('catalog').open=true;document.getElementById('cat-route').value=r.route_id;document.getElementById('cat-route').disabled=true;document.getElementById('cat-workload').value=r.workload;document.getElementById('cat-workload').disabled=true;document.getElementById('cat-family').value=r.provider_family;document.getElementById('cat-provider').value=r.provider_id;document.getElementById('cat-model').value=r.model_id;document.getElementById('cat-cost').value=r.cost_class;document.getElementById('cat-reasoning').value=r.reasoning_effort;document.getElementById('cat-capabilities').value=r.capabilities.join(',');document.getElementById('cat-credential').checked=r.credential_required;document.getElementById('cat-enabled').checked=r.enabled;document.getElementById('cat-route').scrollIntoView({behavior:'smooth',block:'center'})}
function renderCatalog(){const o=form.catalog_options;options(document.getElementById('cat-workload'),o.workloads);options(document.getElementById('cat-family'),o.provider_families);options(document.getElementById('cat-cost'),o.cost_classes);options(document.getElementById('cat-reasoning'),o.reasoning_efforts);const list=document.getElementById('catalog-list');list.replaceChildren();allRoutes().forEach(r=>{const row=el('div',undefined,'catalog-row');const text=el('div',`${r.workload} — ${r.provider_family} / ${r.model_id} — ${r.implementation_status}${r.enabled?'':' — DISABLED'}`);const b=el('button','編集 / Edit');b.type='button';b.addEventListener('click',()=>editRoute(r));row.append(text,b);list.append(row)})}
function render(data){form=data;cards.replaceChildren();document.getElementById('revision').textContent=`Revision ${data.revision}`;
 data.workloads.forEach(w=>{const card=el('section',undefined,'card');card.dataset.workload=w.workload;const head=el('div',undefined,'card-head');head.append(el('h2',`${w.label.ja} / ${w.label.en}`),el('span',w.status_message.ja+' / '+w.status_message.en,`badge ${w.status}`));card.append(head);
 const fields=el('div',undefined,'fields');const modeBox=el('div');const ml=el('label','利用方法 / Usage mode');ml.htmlFor=`mode-${w.workload}`;const mode=el('select');mode.id=ml.htmlFor;mode.dataset.kind='mode';w.mode_options.forEach(v=>{const o=el('option',v);o.value=v;o.selected=v===w.selection_mode;mode.append(o)});const mh=el('p',w.mode_help[w.selection_mode].ja+' / '+w.mode_help[w.selection_mode].en,'help');mode.addEventListener('change',()=>mh.textContent=w.mode_help[mode.value].ja+' / '+w.mode_help[mode.value].en);modeBox.append(ml,mode,mh);
 const routeBox=el('div');const rl=el('label','優先Model / Preferred model');rl.htmlFor=`route-${w.workload}`;const route=el('select');route.id=rl.htmlFor;route.dataset.kind='route';const none=el('option','候補なし / No configured route');none.value='';route.append(none);w.routes.forEach(r=>{const o=el('option',routeText(r));o.value=r.route_id;o.selected=r.route_id===w.preferred_route_id;route.append(o)});route.disabled=w.routes.length===0;const rh=el('p',w.routes.length?`${w.routes.length} candidate(s) configured`:'下のCatalogから候補を追加できます / Add a candidate in the catalog below','route-meta');routeBox.append(rl,route,rh);fields.append(modeBox,routeBox);card.append(fields);cards.append(card)});renderCatalog()}
async function load(){const res=await fetch('/api/form',{cache:'no-store'});if(!res.ok)throw new Error('設定を読み込めませんでした');render(await res.json())}
save.addEventListener('click',async()=>{save.disabled=true;message.className='';message.textContent='保存しています…';const modes={},preferred={};cards.querySelectorAll('.card').forEach(c=>{modes[c.dataset.workload]=c.querySelector('[data-kind=mode]').value;preferred[c.dataset.workload]=c.querySelector('[data-kind=route]').value||null});try{const res=await fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json','X-BAI-CSRF':CSRF},body:JSON.stringify({revision:form.revision,workload_modes:modes,preferred_route_ids:preferred})});const data=await res.json();if(!res.ok)throw new Error(data.message||data.error_code||'保存できませんでした');render(data);message.className='success';message.textContent='保存しました。生成は開始されていません。 / Saved; generation has not started.'}catch(e){message.className='error';message.textContent=e.message}finally{save.disabled=false}});
document.getElementById('catalog-new').addEventListener('click',resetCatalog);
document.getElementById('catalog-save').addEventListener('click',async()=>{const button=document.getElementById('catalog-save');button.disabled=true;catMessage.className='';catMessage.textContent='保存しています…';const capabilities=document.getElementById('cat-capabilities').value.split(',').map(x=>x.trim()).filter(Boolean);const entry={route_id:document.getElementById('cat-route').value.trim(),workload:document.getElementById('cat-workload').value,provider_family:document.getElementById('cat-family').value,provider_id:document.getElementById('cat-provider').value.trim(),model_id:document.getElementById('cat-model').value.trim(),cost_class:document.getElementById('cat-cost').value,reasoning_effort:document.getElementById('cat-reasoning').value,capabilities,credential_required:document.getElementById('cat-credential').checked,enabled:document.getElementById('cat-enabled').checked};try{const res=await fetch('/api/catalog',{method:'PUT',headers:{'Content-Type':'application/json','X-BAI-CSRF':CSRF},body:JSON.stringify({revision:form.revision,entry})});const data=await res.json();if(!res.ok)throw new Error(data.message||data.error_code||'候補を保存できませんでした');render(data);resetCatalog();catMessage.className='success';catMessage.textContent='候補を保存しました。実行・課金は開始されていません。 / Candidate saved; nothing executed.'}catch(e){catMessage.className='error';catMessage.textContent=e.message}finally{button.disabled=false}});
load().catch(e=>{message.className='error';message.textContent=e.message});</script>
</body></html>"""


class ConnectionSettingsWebService:
    def __init__(
        self,
        settings_path: Path,
        profile: AiConnectionProfile,
        revision: int,
        availability: ConnectionAvailability,
    ) -> None:
        self.settings_path = settings_path
        self.profile = profile
        self.revision = revision
        self.availability = availability
        self._lock = threading.Lock()

    @classmethod
    def from_paths(
        cls,
        settings_path: str | Path,
        profile_path: str | Path | None,
        *,
        available_credential_refs: frozenset[str] = frozenset(),
    ) -> "ConnectionSettingsWebService":
        if any(not ref.startswith("credential://") for ref in available_credential_refs):
            raise ValueError("--credential-ready accepts credential:// references, never secret values")
        settings = Path(settings_path).resolve()
        if settings.exists():
            loaded = ConnectionSettingsStore.load(settings).record
            profile, revision = loaded.profile, loaded.revision
        else:
            if profile_path is None:
                raise ValueError("--profile is required when the settings file does not exist")
            raw = json.loads(Path(profile_path).read_text(encoding="utf-8"))
            profile, revision = AiConnectionProfile.from_dict(raw), 0
        route_ids = frozenset(route.route_id for route in profile.routes if route.enabled)
        return cls(settings, profile, revision, ConnectionAvailability(route_ids, available_credential_refs))

    def form(self) -> dict[str, object]:
        with self._lock:
            return self._form_unlocked()

    def _form_unlocked(self) -> dict[str, object]:
        preflight = AiConnectionSettingsService.preflight(self.profile, self.availability)
        return ConnectionSettingsFormBuilder.build(self.profile, preflight, revision=self.revision)

    def _refresh_availability_unlocked(self) -> None:
        self.availability = ConnectionAvailability(
            frozenset(route.route_id for route in self.profile.routes if route.enabled),
            self.availability.available_credential_refs,
        )

    def update(self, payload: Any) -> dict[str, object]:
        if not isinstance(payload, dict) or set(payload) != {
            "revision", "workload_modes", "preferred_route_ids"
        }:
            raise ValueError("request must contain revision, workload_modes, and preferred_route_ids")
        if not isinstance(payload["revision"], int) or isinstance(payload["revision"], bool):
            raise ValueError("revision must be an integer")
        if not isinstance(payload["workload_modes"], dict) or not isinstance(payload["preferred_route_ids"], dict):
            raise ValueError("settings selections must be objects")
        with self._lock:
            if self.settings_path.exists():
                latest = ConnectionSettingsStore.load(self.settings_path).record
                self.profile, self.revision = latest.profile, latest.revision
            if payload["revision"] != self.revision:
                raise ProductError(
                    "ERR_CONNECTION_SETTINGS_CONFLICT",
                    "Settings changed in another screen. Reload before saving.",
                    ProductErrorCategory.STATE,
                    details={"expected_revision": payload["revision"], "current_revision": self.revision},
                )
            edited = ConnectionSettingsEditor.apply(
                self.profile,
                workload_modes=payload["workload_modes"],
                preferred_route_ids=payload["preferred_route_ids"],
            )
            result = ConnectionSettingsStore.save(
                self.settings_path, edited, expected_revision=self.revision
            )
            self.profile, self.revision = edited, result.record.revision
            self._refresh_availability_unlocked()
            return self._form_unlocked()

    def update_catalog(self, payload: Any) -> dict[str, object]:
        if not isinstance(payload, dict) or set(payload) != {"revision", "entry"}:
            raise ValueError("request must contain revision and entry")
        if not isinstance(payload["revision"], int) or isinstance(payload["revision"], bool):
            raise ValueError("revision must be an integer")
        if not isinstance(payload["entry"], dict):
            raise ValueError("catalog entry must be an object")
        with self._lock:
            if self.settings_path.exists():
                latest = ConnectionSettingsStore.load(self.settings_path).record
                self.profile, self.revision = latest.profile, latest.revision
                self._refresh_availability_unlocked()
            if payload["revision"] != self.revision:
                raise ProductError(
                    "ERR_CONNECTION_SETTINGS_CONFLICT",
                    "Settings changed in another screen. Reload before saving.",
                    ProductErrorCategory.STATE,
                )
            edited = ConnectionCatalogEditor.upsert(self.profile, payload["entry"])
            result = ConnectionSettingsStore.save(
                self.settings_path, edited, expected_revision=self.revision
            )
            self.profile, self.revision = edited, result.record.revision
            self._refresh_availability_unlocked()
            return self._form_unlocked()


def launch_server(
    service: ConnectionSettingsWebService,
    *,
    port: int = 8765,
) -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "BAISettings/1.0"

        def _allowed_host(self) -> bool:
            host = self.headers.get("Host", "")
            actual_port = self.server.server_address[1]
            return host in {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}

        def _headers(self, status: int, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", f"default-src 'none'; style-src 'nonce-{csrf}'; script-src 'nonce-{csrf}'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'")

        def _json(self, status: int, value: object) -> None:
            data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if not self._allowed_host():
                self._json(421, {"error_code": "ERR_SETTINGS_HOST", "message": "Untrusted Host header"})
                return
            path = urlsplit(self.path).path
            if path == "/":
                html = _HTML.replace("__NONCE__", csrf).replace("__CSRF_JSON__", json.dumps(csrf))
                data = html.encode("utf-8")
                self._headers(200, "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path == "/api/form":
                self._json(200, service.form())
            else:
                self._json(404, {"error_code": "ERR_SETTINGS_NOT_FOUND", "message": "Not found"})

        def do_PUT(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if not self._allowed_host() or path not in {"/api/settings", "/api/catalog"}:
                self._json(404, {"error_code": "ERR_SETTINGS_NOT_FOUND", "message": "Not found"})
                return
            if self.headers.get("X-BAI-CSRF") != csrf:
                self._json(403, {"error_code": "ERR_SETTINGS_CSRF", "message": "Security token mismatch"})
                return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"error_code": "ERR_SETTINGS_CONTENT_TYPE", "message": "JSON required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_REQUEST_BYTES:
                self._json(413, {"error_code": "ERR_SETTINGS_REQUEST_SIZE", "message": "Request size is invalid"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = service.update(payload) if path == "/api/settings" else service.update_catalog(payload)
                self._json(200, result)
            except ProductError as exc:
                self._json(409, {"error_code": exc.code, "message": exc.message})
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                self._json(400, {"error_code": "ERR_SETTINGS_INPUT", "message": str(exc)})

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="bai-settings", daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    return server, thread, url


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=Path("ai-connection-settings.json"))
    parser.add_argument("--profile", type=Path, default=Path("profiles/ai-connection-creator.example.json"))
    parser.add_argument("--credential-ready", action="append", default=[], help="Credential reference known to be configured; never pass a secret value")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be 0-65535")
    service = ConnectionSettingsWebService.from_paths(
        args.settings,
        args.profile if not args.settings.exists() else None,
        available_credential_refs=frozenset(args.credential_ready),
    )
    server, thread, url = launch_server(service, port=args.port)
    print(json.dumps({"ok": True, "url": url, "settings": str(service.settings_path), "paid_call_started": False}))
    if not args.no_browser:
        webbrowser.open(url)
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        thread.join(timeout=5)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
