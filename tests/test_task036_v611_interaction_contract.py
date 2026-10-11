from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from ai_video_production.task036_shell_v611 import HTML

# Node startup exceeded 90 seconds under a contended Windows xdist worker.
# Keep this below the outer 120-second pytest timeout while preserving all assertions and bounded failure.
NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS = 110


def test_audit_input_endpoints_are_declared_in_production_bridge_contract() -> None:
    match = re.search(r"production:\[(?P<methods>[^\]]+)\]", HTML)
    assert match is not None
    methods = match.group("methods")
    for method in (
        "audit_prepare_record",
        "audit_apply_record",
        "audit_cancel_record",
    ):
        assert f"'{method}'" in methods


@pytest.mark.parametrize("observation,expected", [
    ({"system": {"comfyui_version": "test"}, "devices": []}, "READY"),
    ({"system": {}, "devices": [{"name": "private-device"}]}, "READY"),
    ({}, "UNKNOWN"),
    ({"system": {}, "devices": ["invalid"]}, "UNKNOWN"),
    ([], "UNKNOWN"),
    ("unreachable", "UNREACHABLE"),
    ("http-error", "UNKNOWN"),
    ("invalid-json", "UNKNOWN"),
    ("oversize", "UNKNOWN"),
])
def test_trusted_comfyui_warning_binding_is_lazy_bounded_and_read_only(
    tmp_path, monkeypatch, observation, expected,
) -> None:
    from urllib.error import HTTPError, URLError
    from ai_video_production import comfyui
    from ai_video_production.errors import ProductError
    from ai_video_production.task036_native_dialog import Task036NativeDialogService
    from ai_video_production.task036_trusted_launcher import (
        Task036LaunchConfiguration, build_trusted_launch,
    )
    from test_task036_trusted_launcher import (
        AsrProvider, ComfyClient, DialogBackend, ResolveAdapter, config_document,
    )

    path, raw = config_document(tmp_path)
    project = path.parent
    roots = {name: project / name for name in (
        "comfy-output", "generation-output", "generation-stage", "generation-journal",
    )}
    for root in roots.values():
        root.mkdir()
    raw["launch_config_version"] = "1.1.0"
    raw["local_generation"] = {
        "endpoint": "http://127.0.0.1:8188",
        "comfy_output_root": str(roots["comfy-output"]),
        "project_output_root": str(roots["generation-output"]),
        "staging_root": str(roots["generation-stage"]),
        "dispatch_journal_root": str(roots["generation-journal"]),
        "route_id": "local-video", "provider_id": "comfy",
        "model_id": "minimax-h3-native", "width": 832, "height": 480,
        "length": 124, "steps": 20, "poll_interval_seconds": 1.0,
        "completion_timeout_seconds": 3600, "max_output_bytes": 16 * 1024**3,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    calls = []
    reads = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            reads.append(size)
            if observation == "invalid-json":
                return b"not-json"
            if observation == "oversize":
                return b"x" * size
            return json.dumps(observation).encode()

    def read_only_get(request, *, timeout):
        calls.append((request.full_url, request.get_method(), request.data, timeout))
        if observation == "unreachable":
            raise URLError("private diagnostic")
        if observation == "http-error":
            raise HTTPError(request.full_url, 500, "private diagnostic", {}, None)
        return Response()

    monkeypatch.setattr(comfyui, "urlopen", read_only_get)
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(), resolve_adapter=ResolveAdapter(),
        comfy_client=ComfyClient(), meter_host_factory=lambda *_: None,
    )
    try:
        assert calls == []  # Constructing the app does not probe or queue.
        files_before = {p for p in project.rglob("*") if p.is_file()}
        # Windows intentionally locks the live lease file against byte reads.
        before = {p: p.read_bytes() for p in files_before if p.name != ".task036-runtime.lock"}
        with pytest.raises(ProductError) as invalid:
            launch.bridge.comfyui_runtime_snapshot({"start": True})
        assert invalid.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
        assert calls == []
        result = launch.bridge.comfyui_runtime_snapshot({})
        assert result["state"] == expected
        assert calls == [("http://127.0.0.1:8188/system_stats", "GET", None, 2)]
        assert reads in ([], [65537])
        assert all(result[key] is False for key in (
            "provider_execution_started", "paid_execution_authorized",
            "generation_started", "execution_authorized",
        ))
        assert "private" not in json.dumps(result)
        assert "127.0.0.1" not in json.dumps(result)
        assert {p for p in project.rglob("*") if p.is_file()} == files_before
        assert {p: p.read_bytes() for p in files_before if p.name != ".task036-runtime.lock"} == before
    finally:
        launch.close()
    count = len(calls)
    assert launch.bridge.comfyui_runtime_snapshot({})["state"] == "UNKNOWN"
    assert len(calls) == count  # Closed app cannot retain a live health callback.


def test_trusted_launch_without_comfyui_config_does_not_probe(tmp_path, monkeypatch) -> None:
    from ai_video_production import comfyui
    from ai_video_production.task036_native_dialog import Task036NativeDialogService
    from ai_video_production.task036_trusted_launcher import Task036LaunchConfiguration, build_trusted_launch
    from test_task036_trusted_launcher import AsrProvider, DialogBackend, ResolveAdapter, config_document

    path, _ = config_document(tmp_path)
    def deny_probe(*args, **kwargs):
        raise AssertionError("Unconfigured ComfyUI must not be contacted")
    monkeypatch.setattr(comfyui, "urlopen", deny_probe)
    launch = build_trusted_launch(
        Task036LaunchConfiguration.load(path),
        native_dialog=Task036NativeDialogService(DialogBackend()),
        asr_provider=AsrProvider(), resolve_adapter=ResolveAdapter(),
        meter_host_factory=lambda *_: None,
    )
    try:
        assert launch.bridge.comfyui_runtime_snapshot({})["reason_code"] == "COMFYUI_RUNTIME_NOT_BOUND"
    finally:
        launch.close()


@pytest.mark.parametrize("state", ["READY", "UNREACHABLE", "UNKNOWN"])
def test_comfyui_status_bridge_projects_read_only_observation(state: str) -> None:
    from ai_video_production.desktop_shell import ShellApplicationService
    from ai_video_production.task036_shell_ui import Task036ShellBridge

    calls = []

    def observe():
        calls.append("observe")
        return {"state": state}

    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"),
                               comfyui_runtime_snapshot_provider=observe)
    result = bridge.comfyui_runtime_snapshot({})
    assert result["state"] == state
    assert calls == ["observe"]
    assert all(result[key] is False for key in (
        "provider_execution_started", "paid_execution_authorized",
        "generation_started", "execution_authorized"))


@pytest.mark.parametrize("raw", [None, {}, {"state": "READY", "path": "private"},
                                 {"state": ["READY"]}, {"state": "STOPPED"}])
def test_comfyui_status_bridge_does_not_promote_invalid_or_unbound_state(raw) -> None:
    from ai_video_production.desktop_shell import ShellApplicationService
    from ai_video_production.errors import ProductError
    from ai_video_production.task036_shell_ui import Task036ShellBridge

    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"),
                               comfyui_runtime_snapshot_provider=lambda: raw)
    result = bridge.comfyui_runtime_snapshot({})
    assert result["state"] == "UNKNOWN"
    assert result["available"] is False
    assert "private" not in str(result)
    with pytest.raises(ProductError):
        bridge.comfyui_runtime_snapshot({"start": True})
    unbound = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    assert unbound.comfyui_runtime_snapshot({})["reason_code"] == "COMFYUI_RUNTIME_NOT_BOUND"


def test_central_model_selection_change_save_failure_and_reopen_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the central Settings behavior contract")
    names = ("settingsWorkloadName", "settingsModelLabel", "settingsAvailabilityText",
             "centralPreferredRouteValue", "requiredLocalRuntimeNames",
             "localRuntimeWarning", "renderRequiredRuntimeWarnings",
             "renderCentralModelSettings")
    functions = []
    for name in names:
        match = re.search(rf"function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.listeners={};this.attributes={};this.style={};this.disabled=false;this._value='';}
  append(...items){this.children.push(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this.attributes[name]=value;}
  removeAttribute(name){delete this.attributes[name];}
  get value(){if(this.tag==='select')return (this.children.find(item=>item.selected)||this.children[0])?.value||'';return this._value;}
  set value(value){this._value=value;if(this.tag==='select')this.children.forEach(item=>item.selected=item.value===value);}
}
const document={createElement:tag=>new Node(tag)},host=new Node('host');
const $=()=>host,clear=node=>{node.children=[];},element=(tag,cls,text)=>{const n=new Node(tag);n.textContent=text;return n;};
const card=(title,body)=>element('card','',body);
function walk(node){return node.children.flatMap(child=>[child,...walk(child)]);}
const q=(selector,node)=>walk(node).find(item=>item.dataset.connectionRoute===selector.match(/="([^"]+)"/)[1]);
host.querySelector=selector=>q(selector,host);
const PLANNING_STATE_SAFE_ERROR='safe planning state';
let headerRefreshes=0;
const refreshGlobalPlanningAiStatus=async()=>{headerRefreshes++;};
const CENTRAL_MODEL_WORKLOADS=new Set(['PLANNING','IMAGE','VIDEO','AUDIO','MUSIC']);
const renderOllamaRuntimeStatus=()=>{throw new Error('stale saved-route runtime card');},renderComputeSettings=()=>{};
let currentSettingsView='models',readbacks=0,saveResult=null,payload=null,calls=[],notices=[];
const notify=(...args)=>notices.push(args);
const call=async(method,args)=>{calls.push(method);payload=args;return saveResult;};
const renderSettingsView=async()=>{readbacks++;};
""" + "\n".join(functions) + r"""
(async()=>{
  const form={available:true,revision:7,workloads:[{workload:'PLANNING',selection_mode:'AUTO',preferred_route_id:'plan-1',routes:[
    {route_id:'plan-1',model_id:'qwen3:8b',provider_id:'ollama',selectable:true},
    {route_id:'plan-2',model_id:'gemma3:12b',local:false,cost_class:'CLOUD_PAID_AI',selectable:true},
    {route_id:'plan-3',model_id:'missing-model',selectable:false}
  ]}]};
  renderCentralModelSettings(form,{},{});
  let select=walk(host).find(item=>item.tag==='select'),button=walk(host).find(item=>item.tag==='button');
  assert.equal(select.value,'plan-1');
  assert.equal(walk(host).filter(item=>item.attributes.role==='alert').length,1);
  assert.match(select.children.find(item=>item.value==='plan-2').textContent,/gemma3:12b/);
  assert.equal(select.children.find(item=>item.value==='plan-3').disabled,true);
  const availability=walk(host).find(item=>item.textContent===settingsAvailabilityText(form.workloads[0].routes[0]));
  select.value='';select.listeners.change();
  assert.equal(walk(host).filter(item=>item.attributes.role==='alert').length,0);
  assert.equal(availability.textContent,settingsAvailabilityText(undefined));
  select.value='plan-2';select.listeners.change();
  assert.equal(walk(host).filter(item=>item.attributes.role==='alert').length,0);
  assert.equal(availability.textContent,settingsAvailabilityText(form.workloads[0].routes[1]));
  await button.listeners.click();
  assert.equal(payload.preferred_route_ids.PLANNING,'plan-2');
  assert.equal(payload.revision,7);
  assert.equal(readbacks,0);assert.equal(notices.length,0);
  assert.equal(headerRefreshes,0);
  assert.equal(select.value,'plan-2');assert.equal(button.disabled,false);
  saveResult={revision:8};await button.listeners.click();
  assert.equal(readbacks,1);assert.equal(notices.length,1);
  assert.equal(headerRefreshes,1);
  assert.deepEqual(calls,['connection_settings_update','connection_settings_update']);
  // Later opening uses the saved canonical form, not a browser-side store.
  const reopened=structuredClone(form);reopened.revision=8;reopened.workloads[0].preferred_route_id=payload.preferred_route_ids.PLANNING;
  renderCentralModelSettings(reopened,{},{});
  assert.equal(walk(host).find(item=>item.tag==='select').value,'plan-2');
  reopened.workloads[0].preferred_route_id='plan-3';renderCentralModelSettings(reopened,{},{});
  select=walk(host).find(item=>item.tag==='select');button=walk(host).find(item=>item.tag==='button');
  assert.equal(select.value,'plan-3');assert.match(select.children.find(item=>item.selected).textContent,/missing-model/);
  assert.equal(select.dataset.preserveUnavailablePreferred,'true');
  await button.listeners.click();assert.equal(Object.hasOwn(payload.preferred_route_ids,'PLANNING'),false);
  select.value='plan-2';select.listeners.change();await button.listeners.click();
  assert.equal(payload.preferred_route_ids.PLANNING,'plan-2');
  console.log('OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    completed = subprocess.run([node, "-e", script], check=False, capture_output=True,
                               text=True, timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_audit_input_rpc_rejections_never_render_private_backend_errors_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Audit input RPC error contract")
    call_match = re.search(
        r"async function call\(method,args=\{\},publicError=null\)\{[^\r\n]+",
        HTML,
    )
    assert call_match is not None
    script = f"""
const assert=require('node:assert/strict');
const notifications=[];
function notify(message,isError=false){{notifications.push({{message,isError}})}}
const privateError='C:'+String.fromCharCode(92)+'Users'+String.fromCharCode(92)+'owner'+String.fromCharCode(92)+'private-audit.json';
const methods=['audit_prepare_record','audit_apply_record','audit_cancel_record'];
const api=Object.fromEntries(methods.map(method=>[method,async()=>{{throw new Error(privateError)}}]));
const window={{pywebview:{{api}}}};
{call_match.group(0)}
(async()=>{{
  const publicError='監査記録を保存できませんでした。監査画面を更新して、入力内容を確認してください。自動では再実行しません。';
  for(const method of methods)assert.equal(await call(method,{{}},publicError),null);
  assert.equal(notifications.length,3);
  assert.ok(notifications.every(item=>item.message===publicError&&item.isError===true));
  assert.doesNotMatch(notifications.map(item=>item.message).join('\\n'),/Users|owner|private-audit/);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_required_local_runtime_warnings_are_truthful_and_route_scoped_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for local runtime warning behavior")
    functions = []
    for name in ("requiredLocalRuntimeNames", "localRuntimeWarning", "renderRequiredRuntimeWarnings"):
        match = re.search(rf"function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
const host={children:[],append(node){this.children.push(node);}};
const card=(title,message)=>({title,message,style:{},attributes:{},setAttribute(name,value){this.attributes[name]=value;}});
""" + "\n".join(functions) + r"""
const ollama={provider_id:'ollama',cost_class:'LOCAL_FREE_AI'};
const comfy={provider_family:'COMFYUI',cost_class:'LOCAL_FREE_AI'};
assert.deepEqual(requiredLocalRuntimeNames([ollama,comfy,comfy]),['Ollama','ComfyUI']);
assert.deepEqual(requiredLocalRuntimeNames([undefined,{provider_id:'cloud'}, {...comfy,cost_class:'CLOUD_PAID_AI'}]),[]);
for(const name of ['Ollama','ComfyUI']) {
  assert.equal(localRuntimeWarning(name,{state:'READY'}),null);
  assert.equal(localRuntimeWarning(name,{state:'NO_MODEL'}),null);
  assert.match(localRuntimeWarning(name,{state:'UNREACHABLE'}).message,/起動していないか、接続できません/);
  const unknown=localRuntimeWarning(name,null);
  assert.match(unknown.message,/起動状態を確認できません/);
  assert.doesNotMatch(unknown.message,/起動していません/);
}
assert.match(localRuntimeWarning('Ollama',{state:'FAILED',reason_code:'OLLAMA_NOT_RUNNING'}).message,/接続できません/);
assert.match(localRuntimeWarning('Ollama',{state:'STARTING'}).message,/起動中/);
assert.match(localRuntimeWarning('Ollama',{state:'NOT_INSTALLED'}).message,/導入されていません/);
renderRequiredRuntimeWarnings(host,[ollama,comfy],{state:'FAILED',reason_code:'OLLAMA_NOT_RUNNING'},{state:'UNREACHABLE'});
assert.equal(host.children.length,2);
assert.equal(host.children[0].attributes.role,'alert');
assert.equal(host.children[0].style.borderColor,'#c9953f');
host.children=[];
renderRequiredRuntimeWarnings(host,[{provider_id:'cloud'}],{state:'FAILED'},{state:'UNREACHABLE'});
assert.equal(host.children.length,0);
renderRequiredRuntimeWarnings(host,[ollama,comfy],{state:'READY'},{state:'READY'});
assert.equal(host.children.length,0);
renderRequiredRuntimeWarnings(host,[comfy],{state:'FAILED'},null);
assert.equal(host.children.length,1);assert.match(host.children[0].message,/確認できません/);
console.log('OK');
"""
    completed = subprocess.run([node, "-e", script], check=False, capture_output=True,
                               text=True, timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"
    assert "call('comfyui_runtime_snapshot',{})" in HTML
    assert "page==='planning'&&required.includes('Ollama')" in HTML


def test_planning_generated_target_selection_refresh_and_saved_reopen_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Planning selection behavior contract")
    names = ("renderPlanningProposalSelection", "renderPlanning", "renderSceneDetail",
             "renderScenes", "refreshPlanning", "generatePlanning", "finalizeScenes")
    functions = []
    for name in names:
        match = re.search(rf"(?:async )?function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.attributes={};this.value='';this.textContent='';}
  append(...items){this.children.push(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this.attributes[name]=value;}
}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new Node(id));return nodes.get(id);};
const clear=n=>{n.children=[];n.textContent='';},element=(tag,cls,text)=>{const n=new Node(tag);n.textContent=text;return n;};
const card=(title,body)=>element('card','',body),walk=n=>n.children.flatMap(c=>[c,...walk(c)]);
const qa=(selector,n)=>walk(n).filter(c=>c.tag===selector),renderModel=()=>{};
const renderFeatureModelReadiness=()=>({}),renderPlanningGenerationStatus=()=>{};
let currentPlanningModel=null,currentPlanningGeneration={available:true},currentSceneId=null;
let currentPlanningReadiness=null,planningGenerationInFlight=false;
const PLANNING_GENERATION_SAFE_ERROR='safe generation',PLANNING_STATE_SAFE_ERROR='safe state';
let calls=[],notices=[],approveTargets=[],confirmDecision=true,scenario='success';
const notify=(...args)=>notices.push(args),approvePlanning=(model,workspace)=>approveTargets.push(workspace.proposal_id);
const revisePlanning=()=>{},installPlanning=()=>{};
const window={confirm:()=>confirmDecision,prompt:()=> 'owner'};
function fixture(id){return {available:true,proposal_ids:['PROPOSAL-A','PROPOSAL-Z'],selected_proposal_id:id,snapshot_sha256:'snapshot-'+id,
  workspace:{proposal_id:id,latest_revision:1,go_status:'GO_REQUIRED',creation_intent:{},provider_policy:{},
    estimated_cost_range:{min:0,max:0,currency:'JPY'},sections:[],rights_warnings:[],
    blueprint:{blueprint_id:'blueprint-'+id,title:id,timeline_rate:{numerator:24,denominator:1},target_duration_frames:24,
      scenes:[{scene_id:'scene-'+id,narrative_role:id,range_frames:{start:0,end_exclusive:24},source_strategy:'REAL_CAPTURE',audio:{}}]}},
  installation:{status:'NOT_INSTALLED'},scene_contract:{status:'GO_REQUIRED',snapshot_sha256:'scene-snapshot-'+id}};}
const saved=new Map(['PROPOSAL-A','PROPOSAL-Z'].map(id=>[id,fixture(id)]));
async function call(method,args={}){
  calls.push([method,args]);
  if(method==='planning_snapshot')return structuredClone(saved.get(args.proposal_id||'PROPOSAL-A'));
  if(method==='planning_generation_prepare')return scenario==='prepare-fail'?null:{confirmation_id:'generate-confirm',already_generated:scenario==='idempotent'};
  if(method==='planning_generation_apply')return scenario==='apply-fail'?null:{proposal_id:'PROPOSAL-Z',application:structuredClone(saved.get('PROPOSAL-Z')),idempotent:scenario==='idempotent',apply_recovery_state:scenario==='recovered'?'COMMITTED_READBACK':null};
  if(method==='planning_generation_cancel')return {cancelled:true};
  if(method==='planning_prepare_scene_finalization')return {confirmation_id:'final-confirm',receipt:{proposal_id:args.proposal_id}};
  if(method==='planning_apply_scene_finalization')return {applied:true};
  if(method==='planning_generation_status')return {available:true};
  if(['model_selection_snapshot','ollama_runtime_snapshot','desktop_compute_settings_snapshot','comfyui_runtime_snapshot'].includes(method))return {};
  throw new Error('unexpected method '+method);
}
__FUNCTIONS__
function selector(){return walk($('planningContent')).find(n=>n.tag==='select');}
function assertTarget(id){
  assert.equal(currentPlanningModel.selected_proposal_id,id);
  assert.equal(currentSceneId,'scene-'+id);
  assert.equal(selector().children.find(n=>n.selected).value,id);
  assert.match($('sceneDetail').textContent,new RegExp('scene-'+id));
}
(async()=>{
  await refreshPlanning();assertTarget('PROPOSAL-A');
  $('planningRequest').value='new request';await generatePlanning();assertTarget('PROPOSAL-Z');
  assert.equal($('planningRequest').value,'');
  assert.equal(calls.findLast(c=>c[0]==='planning_snapshot')[1].proposal_id,'PROPOSAL-Z');
  const generatedCount=calls.filter(c=>c[0].startsWith('planning_generation_')&&c[0]!=='planning_generation_status').length;
  await refreshPlanning();assertTarget('PROPOSAL-Z');
  const go=walk($('planningContent')).find(n=>n.tag==='button'&&n.textContent.includes('GO'));
  go.listeners.click();assert.deepEqual(approveTargets,['PROPOSAL-Z']);
  selector().value='PROPOSAL-A';await selector().listeners.change();assertTarget('PROPOSAL-A');
  assert.equal(calls.filter(c=>c[0].startsWith('planning_generation_')&&c[0]!=='planning_generation_status').length,generatedCount);
  // Fresh UI session can explicitly reopen the existing canonical Proposal/Scene; no browser-side canonical store.
  currentPlanningModel=null;currentSceneId=null;await refreshPlanning();assertTarget('PROPOSAL-A');
  selector().value='PROPOSAL-Z';await selector().listeners.change();assertTarget('PROPOSAL-Z');
  saved.get('PROPOSAL-Z').workspace.go_status='APPROVED';saved.get('PROPOSAL-Z').scene_contract.status='READY_TO_FINALIZE';
  await refreshPlanning();await finalizeScenes();assertTarget('PROPOSAL-Z');
  const finalArgs=calls.find(c=>c[0]==='planning_prepare_scene_finalization')[1];
  assert.equal(finalArgs.proposal_id,'PROPOSAL-Z');assert.equal(finalArgs.expected_proposal_snapshot_sha256,'snapshot-PROPOSAL-Z');
  for(const failed of ['prepare-fail','apply-fail','cancel']){
    scenario=failed;confirmDecision=failed!=='cancel';$('planningRequest').value='keep my request';const before=calls.length;
    await generatePlanning();assertTarget('PROPOSAL-Z');assert.equal($('planningRequest').value,'keep my request');
    const methods=calls.slice(before).map(c=>c[0]);assert.ok(methods.includes('planning_snapshot'));
    assert.equal(calls.findLast(c=>c[0]==='planning_snapshot')[1].proposal_id,'PROPOSAL-Z');
    if(failed==='cancel'){assert.ok(methods.includes('planning_generation_cancel'));assert.ok(!methods.includes('planning_generation_apply'));}
  }
  scenario='idempotent';confirmDecision=true;await generatePlanning();assertTarget('PROPOSAL-Z');
  await refreshPlanning('PROPOSAL-A');scenario='recovered';$('planningRequest').value='recover';
  await generatePlanning();assertTarget('PROPOSAL-Z');
  saved.get('PROPOSAL-Z').proposal_ids=['PROPOSAL-Z'];await refreshPlanning();assert.equal(selector(),undefined);
  console.log('OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace("__FUNCTIONS__", "\n".join(functions))
    completed = subprocess.run([node, "-e", script], check=False, capture_output=True,
                               text=True, timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_generation_runtime_recheck_invalidates_controls_and_ignores_old_response_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the generation readiness behavior contract")
    names = ("generationReadinessCoordinate", "preflightLocalGeneration",
             "prepareLocalGenerationExecution", "renderGenerationQueue", "refreshQueue")
    functions = []
    for name in names:
        match = re.search(rf"(?:async )?function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.attributes={};this.dataset={};this.disabled=false;this.textContent='';}
  append(...items){this.children.push(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this.attributes[name]=value;}
}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new Node(id));return nodes.get(id);};
const clear=n=>{n.children=[];n.textContent='';},element=(tag,cls,text)=>{const n=new Node(tag);n.textContent=text;return n;};
const card=(title,body)=>element('card','',title+' '+body),renderModel=()=>{};
const walk=n=>n.children.flatMap(c=>[c,...walk(c)]);
const generationRuntimeReadiness=new Map(),generationRuntimePreflights=new Map();
let calls=[],notices=[],pending=null,queuePending=null,scenario='pass',model;
const notify=(...args)=>notices.push(args),window={confirm:()=>false};
const entry={queue_entry_id:'queue-image',scene_id:'scene-1',slot_id:'slot-start',input_bindings:[]};
function fixture(revision){return {available:true,entry_count:1,queue_snapshot_sha256:'queue-'+revision,entries:[entry],
  execution_control:{available:true,queue_snapshot_sha256:'queue-'+revision,execution_snapshot_sha256:'execution-'+revision,
    available_queue_entries:[entry],latest_executions:[],recovery:{required:false}},output_adoption_control:{available:false}};}
const pass={result:'SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED',route_id:'route-image',provider_id:'comfy',model_id:'image-model',workflow_sha256:'workflow'};
async function call(method,args={}){
  calls.push([method,args]);
  if(method==='generation_execution_preflight'){
    if(scenario==='pending')return await new Promise(resolve=>{pending=resolve;});
    if(scenario==='failure')return null;
    if(scenario==='blocked')return {result:'BLOCKED'};
    return pass;
  }
  if(method==='generation_queue_snapshot')return scenario==='queue-pending'?await new Promise(resolve=>{queuePending=resolve;}):model;
  if(method==='generation_execution_prepare')return {confirmation_id:'confirm-image',scene_id:'scene-1',slot_id:'slot-start'};
  if(method==='generation_execution_cancel')return {cancelled:true};
  throw new Error('unexpected effect '+method);
}
__FUNCTIONS__
const button=label=>walk($('generationQueueContent')).find(n=>n.tag==='button'&&n.textContent===label);
const execute=()=>button('この1件を確認して生成'),check=()=>button('Runtimeを確認');
(async()=>{
  model=fixture('1');await refreshQueue();assert.equal(execute().disabled,true);
  await preflightLocalGeneration(model,entry);assert.equal(execute().disabled,false);
  assert.deepEqual(calls.findLast(c=>c[0]==='generation_execution_preflight')[1],{queue_entry_id:'queue-image'});
  scenario='pending';const recheck=preflightLocalGeneration(model,entry);
  assert.equal(execute().disabled,true);assert.equal(check().disabled,true);assert.equal(check().attributes['aria-busy'],'true');
  const count=calls.filter(c=>c[0]==='generation_execution_preflight').length;
  await preflightLocalGeneration(model,entry);assert.equal(calls.filter(c=>c[0]==='generation_execution_preflight').length,count);
  pending(null);await recheck;assert.equal(execute().disabled,true);assert.equal(check().disabled,false);
  assert.equal(generationRuntimeReadiness.has(entry.queue_entry_id),false);
  assert.ok(notices.some(n=>n[1]===true&&n[0].includes('再確認')));
  for(const failure of ['failure','blocked']){
    scenario='pass';await preflightLocalGeneration(model,entry);assert.equal(execute().disabled,false);
    scenario=failure;await preflightLocalGeneration(model,entry);assert.equal(execute().disabled,true);
  }
  scenario='pass';await preflightLocalGeneration(model,entry);await prepareLocalGenerationExecution(model,entry);
  assert.equal(calls.filter(c=>c[0]==='generation_execution_prepare').length,1);
  assert.equal(calls.filter(c=>c[0]==='generation_execution_cancel').length,1);
  assert.equal(execute().disabled,true);
  scenario='pending';const oldModel=model,oldCheck=preflightLocalGeneration(oldModel,entry);
  model=fixture('2');await refreshQueue();pending(pass);await oldCheck;
  assert.equal(execute().disabled,true);assert.equal(generationRuntimeReadiness.size,0);assert.equal(generationRuntimePreflights.size,0);
  // Refresh removes old controls immediately, and also invalidates checks started during its snapshot wait.
  scenario='queue-pending';const refreshing=refreshQueue();assert.equal(execute(),undefined);assert.equal(check(),undefined);
  scenario='pending';const staleCheck=preflightLocalGeneration(model,entry);
  model=fixture('3');queuePending(model);await refreshing;pending(pass);await staleCheck;
  assert.equal(execute().disabled,true);assert.equal(generationRuntimeReadiness.size,0);assert.equal(generationRuntimePreflights.size,0);
  await prepareLocalGenerationExecution(model,entry);
  assert.equal(calls.filter(c=>c[0]==='generation_execution_prepare').length,1);
  assert.equal(calls.filter(c=>c[0]==='generation_execution_apply').length,0);
  console.log('OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace("__FUNCTIONS__", "\n".join(functions))
    completed = subprocess.run([node, "-e", script], check=False, capture_output=True,
                               text=True, timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_output_adoption_refreshes_exact_visual_lineage_and_keeps_human_review_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the output-adoption handoff contract")
    names = ("refreshGenerationAdoptionHandoff", "prepareGenerationOutputAdoption",
             "recoverGenerationOutputAdoption", "visualHandoffTarget", "renderVisualGenerationHandoff")
    functions = []
    for name in names:
        match = re.search(rf"(?:async )?function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent='';}
  append(...items){this.children.push(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
}
const panels=new Map(),q=selector=>{if(!panels.has(selector))panels.set(selector,new Node('panel'));return panels.get(selector);};
const clear=n=>{n.children=[];n.textContent='';},element=(tag,cls,text)=>{const n=new Node(tag);n.textContent=text;return n;};
const card=(title,body)=>element('card','',title+' '+body),walk=n=>n.children.flatMap(c=>[c,...walk(c)]);
const panel=page=>q(`[data-visual-handoff="${page}"]`);
let calls=[],navigation=[],approve=true,mode='success',queueReads=[],projectionRead=0;
const window={confirm:()=>approve},navigate=target=>navigation.push(target);
const prepared={confirmation_id:'confirmation-1',execution_id:'execution-1',candidate_id:'candidate-1',slot_id:'slot-1'};
const recovery={adoption_id:'adoption-1',execution_id:'execution-1',candidate_id:'candidate-1',state:'ASSET_REGISTERED'};
const model={execution_control:{execution_snapshot_sha256:'execution-snapshot'},queue_snapshot_sha256:'queue-snapshot',
  output_adoption_control:{adoption_snapshot_sha256:'adoption-snapshot'}};
function row(kind,state){return {scene_id:'scene-1',slot_id:'slot-'+kind,slot_kind:kind,state,blockers:[],stale_prompt_count:0,
  execution_id:'execution-1',adoption_id:state==='READY_FOR_AUDIT'?'adoption-1':null};}
function visual(state){return {available:true,required_blocker_count:2,all_required_visual_slots_adopted:false,
  projection_sha256:'projection-'+state,delegated_audio_owner:'DEVELOPER2',audio_slot_counted:0,
  rows:[row('START_FRAME',state),row('VIDEO',state)]};}
function result(){
  if(mode==='null')return null;
  const latest={...recovery,state:'READY_FOR_AUDIT'};
  if(mode==='partial')latest.state='ASSET_REGISTERED';
  if(mode==='wrong-execution')latest.execution_id='other-execution';
  if(mode==='wrong-candidate')latest.candidate_id='other-candidate';
  if(mode==='wrong-adoption')latest.adoption_id='other-adoption';
  return {latest_adoptions:[latest],candidate_accepted:false,candidate_locked:false};
}
async function call(method,args={}){
  calls.push([method,args]);
  if(method==='production_snapshot')return {snapshot_sha256:'production-snapshot'};
  if(method==='prompt_evidence_snapshot')return {prompt_snapshot_sha256:'prompt-snapshot'};
  if(method==='generation_output_adoption_prepare')return mode==='prepare-fail'?null:prepared;
  if(['generation_output_adoption_apply','generation_output_adoption_recover'].includes(method))return result();
  if(method==='generation_queue_snapshot')return {output_adoption_control:{recovery:{required:mode==='partial'||mode==='null'}}};
  if(method==='visual_generation_handoff_snapshot'){projectionRead++;return mode==='projection-fail'?null:visual('READY_FOR_AUDIT');}
  throw new Error('unexpected effect '+method);
}
async function refreshQueue(){queueReads.push(await call('generation_queue_snapshot'));}
__FUNCTIONS__
function reset(next){mode=next;approve=true;calls=[];navigation=[];queueReads=[];projectionRead=0;
  renderVisualGenerationHandoff(visual('OUTPUT_READY_FOR_ADOPTION'),'imageGen');
  renderVisualGenerationHandoff(visual('OUTPUT_READY_FOR_ADOPTION'),'videoGen');}
function assertStale(){assert.equal(projectionRead,0);assert.ok(walk(panel('video')).some(n=>n.textContent.includes('OUTPUT_READY_FOR_ADOPTION')));assert.deepEqual(navigation,[]);}
(async()=>{
  for(const action of ['apply','recovery']){
    reset('success');
    if(action==='apply')await prepareGenerationOutputAdoption(model,{execution_id:'execution-1'});
    else await recoverGenerationOutputAdoption(recovery);
    assert.equal(projectionRead,1);assert.equal(queueReads.length,1);assert.deepEqual(navigation,[]);
    for(const kind of ['image','video']){
      assert.ok(walk(panel(kind)).some(n=>n.textContent.includes('READY_FOR_AUDIT')));
      assert.ok(!walk(panel(kind)).some(n=>n.textContent.includes('OUTPUT_READY_FOR_ADOPTION')));
      const button=walk(panel(kind)).find(n=>n.tag==='button');assert.ok(button);button.listeners.click();
    }
    assert.deepEqual(navigation,['assetReview','assetReview']);
    const effects=calls.filter(c=>c[0].endsWith('_apply')||c[0].endsWith('_recover'));
    assert.equal(effects.length,1);
    assert.deepEqual(effects[0],action==='apply'?['generation_output_adoption_apply',{confirmation_id:'confirmation-1'}]:['generation_output_adoption_recover',{adoption_id:'adoption-1'}]);
  }
  reset('success');approve=false;await prepareGenerationOutputAdoption(model,{execution_id:'execution-1'});assertStale();assert.equal(queueReads.length,0);
  assert.equal(calls.filter(c=>c[0]==='generation_output_adoption_apply').length,0);
  reset('success');approve=false;await recoverGenerationOutputAdoption(recovery);assertStale();assert.equal(calls.length,0);
  reset('prepare-fail');await prepareGenerationOutputAdoption(model,{execution_id:'execution-1'});assertStale();assert.equal(queueReads.length,0);
  for(const failure of ['null','partial','wrong-execution','wrong-candidate']){
    for(const action of ['apply','recovery']){
      reset(failure);
      if(action==='apply')await prepareGenerationOutputAdoption(model,{execution_id:'execution-1'});
      else await recoverGenerationOutputAdoption(recovery);
      assertStale();assert.equal(queueReads.length,1);
      if(['null','partial'].includes(failure))assert.equal(queueReads[0].output_adoption_control.recovery.required,true);
    }
  }
  reset('wrong-adoption');await recoverGenerationOutputAdoption(recovery);assertStale();
  reset('success');await refreshGenerationAdoptionHandoff(result(),{execution_id:'',candidate_id:'candidate-1'});assertStale();
  await refreshGenerationAdoptionHandoff(result(),{execution_id:'execution-1',candidate_id:'candidate-1',adoption_id:''});assertStale();
  reset('projection-fail');await prepareGenerationOutputAdoption(model,{execution_id:'execution-1'});
  assert.equal(projectionRead,1);assert.deepEqual(navigation,[]);
  for(const kind of ['image','video'])assert.equal(walk(panel(kind)).filter(n=>n.tag==='button').length,0);
  console.log('OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace("__FUNCTIONS__", "\n".join(functions))
    completed = subprocess.run([node, "-e", script], check=False, capture_output=True,
                               text=True, timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_asset_review_preserves_exact_decision_recovery_and_missing_audit_projection_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Asset Review interaction contract")
    functions = []
    for name in (
        "auditJsonInput", "prepareAssetAuditRecord", "decideAssetReview",
        "recoverAssetReview", "renderAssetReview",
    ):
        match = re.search(rf"(?:async )?function {name}\([^\r\n]+", HTML)
        assert match is not None
        functions.append(match.group(0))
    script = r"""
const assert=require('node:assert/strict');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent='';}
  append(...items){this.children.push(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
}
const host=new Node('host'),$=()=>host,clear=n=>{n.children=[];},
  element=(tag,cls,text)=>Object.assign(new Node(tag),{textContent:text}),
  card=(title,body)=>element('card','',title+' '+body),
  walk=n=>n.children.flatMap(c=>[c,...walk(c)]);
const missingAuditLabel='\u76e3\u67fb\u8a18\u9332\u304c\u307e\u3060\u3042\u308a\u307e\u305b\u3093\u3002\u63a1\u5426\u5224\u65ad\u306b\u306f\u5148\u306bimmutable Audit\u3092\u4fdd\u5b58\u3057\u3066\u304f\u3060\u3055\u3044\u3002';
const hasMissingAuditLabel=()=>walk(host).some(n=>n.textContent===missingAuditLabel);
let calls=[],publicErrors=[],promptValues=[],confirmed=true,prepareFailed=false,applyNull=false,
  refreshed=0,confirmCalls=0,promptCalls=0;
const AUDIT_INPUT_PUBLIC_ERROR='public-safe-audit-input-error';
const window={prompt:()=>{promptCalls++;return promptValues.shift();},confirm:()=>{confirmCalls++;return confirmed;}};
const refreshProduction=async()=>{refreshed++;};
async function call(method,args,publicError=null){
  calls.push([method,args]);
  publicErrors.push(publicError);
  if(method==='audit_prepare_human_decision')return prepareFailed?null:{
    confirmation_id:'confirm-'+args.candidate_id,candidate_id:args.candidate_id,
    asset_sha256:'sha-'+args.candidate_id,audit_refs:['audit-'+args.candidate_id],
    critical_violation_present:false,decision:args.decision};
  if(method==='audit_apply_human_decision')return applyNull?null:{saved:true};
  if(method==='audit_prepare_record')return {
    confirmation_id:'audit-record-confirm',candidate_id:args.candidate_id,
    asset_id:args.asset_id,asset_sha256:args.asset_sha256,
    record:{audit_id:args.audit_id,auditor_id:args.auditor_id,
      auditor_version:args.auditor_version,record_sha256:'record-exact'}};
  if(method==='audit_apply_record')return {saved:true};
  if(method==='audit_cancel_record')return {status:'CANCELLED'};
  if(method==='audit_apply_recovery')return null;
  throw Error('unexpected effect '+method);
}
function candidate(id,actions=['ACCEPT','REJECT']){
  return {candidate_id:id,scene_id:'scene-'+id,slot_id:'slot-'+id,
    lifecycle_state:'READY_FOR_AUDIT',asset_id:'asset-'+id,asset_sha256:'sha-'+id,
    audit_count:1,ai_audit_count:1,human_audit_count:0,audit_history:[],
    available_human_actions:actions};
}
function fixture(){
  return {available:true,production_snapshot_sha256:'production-exact',
    audit_snapshot_sha256:'audit-exact',recovery:{required:false},
    workspace:{candidates:[candidate('A'),candidate('B')]}};
}
function reset(){
  calls=[];publicErrors=[];promptValues=[' owner ','memo'];confirmed=true;prepareFailed=false;
  applyNull=false;refreshed=0;confirmCalls=0;promptCalls=0;host.children=[];
}
let passed=0;
async function scenario(name,fn){reset();await fn();passed++;}
__FUNCTIONS__
(async()=>{
  await scenario('exact multiple candidate target',async()=>{
    const audit=fixture();renderAssetReview(audit);
    const b=host.children.find(n=>n.textContent.includes('B \u00b7'));assert.ok(b);
    const accept=walk(b).find(n=>n.tag==='button'&&n.textContent==='ACCEPT');
    await accept.listeners.click();
    assert.deepEqual(calls[0],['audit_prepare_human_decision',{
      candidate_id:'B',decision:'ACCEPT',
      expected_production_snapshot_sha256:'production-exact',
      expected_audit_snapshot_sha256:'audit-exact'}]);
    assert.deepEqual(calls[1],['audit_apply_human_decision',{
      confirmation_id:'confirm-B',actor_id:'owner',notes:'memo'}]);
    assert.equal(refreshed,1);
  });
  for(const actor of [null,'   '])await scenario('actor cancel/blank',async()=>{
    promptValues=[actor,'memo'];await decideAssetReview(fixture(),candidate('B'),'REJECT');
    assert.equal(calls.length,0);assert.equal(refreshed,0);
  });
  await scenario('notes cancel',async()=>{
    promptValues=['owner',null];await decideAssetReview(fixture(),candidate('B'),'ACCEPT');
    assert.equal(calls.length,0);
  });
  await scenario('confirm cancel',async()=>{
    confirmed=false;await decideAssetReview(fixture(),candidate('B'),'REJECT');
    assert.equal(calls.length,1);assert.equal(refreshed,0);
  });
  await scenario('prepare failure',async()=>{
    prepareFailed=true;await decideAssetReview(fixture(),candidate('B'),'ACCEPT');
    assert.equal(calls.length,1);assert.equal(confirmCalls,0);assert.equal(refreshed,0);
  });
  await scenario('apply null canonical reread',async()=>{
    applyNull=true;promptValues=['owner',''];
    await decideAssetReview(fixture(),candidate('B'),'ACCEPT');
    assert.equal(calls.length,2);assert.equal(calls[1][1].notes,null);assert.equal(refreshed,1);
  });
  await scenario('required recovery prevents decision',async()=>{
    const audit=fixture();audit.recovery.required=true;
    await decideAssetReview(audit,candidate('A'),'ACCEPT');
    assert.equal(calls.length,0);assert.equal(promptValues.length,2);
  });
  for(const action of ['COMPLETE','ABANDON','FINALIZE'])await scenario('recovery exact '+action,async()=>{
    await recoverAssetReview({recovery:{required:true,available_actions:[action],
      transaction_id:'tx',candidate_id:'B'}},action);
    assert.deepEqual(calls,[['audit_apply_recovery',{action}]]);assert.equal(refreshed,1);
  });
  await scenario('closed recovery guards',async()=>{
    await recoverAssetReview({recovery:{required:true,available_actions:['DELETE']}},'DELETE');
    await recoverAssetReview({recovery:{required:true,available_actions:['COMPLETE']}},'FINALIZE');
    await recoverAssetReview({recovery:{required:false,available_actions:['COMPLETE']}},'COMPLETE');
    assert.equal(calls.length,0);assert.equal(confirmCalls,0);
  });
  await scenario('recovery cancel',async()=>{
    confirmed=false;await recoverAssetReview({recovery:{required:true,available_actions:['COMPLETE']}},'COMPLETE');
    assert.equal(calls.length,0);assert.equal(refreshed,0);
  });
  await scenario('zero audit no actions plus explanation',async()=>{
    const audit=fixture();audit.workspace.candidates=[{...candidate('Z',[]),audit_count:0,ai_audit_count:0}];
    renderAssetReview(audit);
    assert.deepEqual(walk(host).filter(n=>n.tag==='button').map(n=>n.textContent),['\u76e3\u67fb\u8a18\u9332\u3092\u5165\u529b']);
    assert.ok(walk(host).some(n=>n.textContent.includes('Audit: 0')));
    assert.ok(hasMissingAuditLabel());assert.equal(calls.length,0);
  });
  await scenario('zero audit explicit input and confirmation',async()=>{
    const audit=fixture(),row={...candidate('Z',[]),audit_count:0,ai_audit_count:0};
    audit.workspace.candidates=[row];renderAssetReview(audit);
    promptValues=['audit-human-Z',' owner ','','["visual-contract-1"]','{"CONTRACT":95}',
      '[]','[]','[]'];
    const input=walk(host).find(n=>n.tag==='button'&&n.textContent==='\u76e3\u67fb\u8a18\u9332\u3092\u5165\u529b');
    await input.listeners.click();
    assert.deepEqual(calls[0],['audit_prepare_record',{
      audit_id:'audit-human-Z',candidate_id:'Z',asset_id:'asset-Z',asset_sha256:'sha-Z',
      auditor_id:'owner',auditor_version:null,contract_refs:['visual-contract-1'],
      dimension_scores:{CONTRACT:95},findings:[],failure_codes:[],alternate_use_proposals:[],
      expected_production_snapshot_sha256:'production-exact',
      expected_audit_snapshot_sha256:'audit-exact'}]);
    assert.deepEqual(calls[1],['audit_apply_record',{
      confirmation_id:'audit-record-confirm',explicit_human_confirmation:true}]);
    assert.deepEqual(publicErrors,[AUDIT_INPUT_PUBLIC_ERROR,AUDIT_INPUT_PUBLIC_ERROR]);
    assert.equal(refreshed,1);
  });
  await scenario('audit input confirmation cancel consumes preparation without write',async()=>{
    const audit=fixture(),row={...candidate('Z',[]),audit_count:0,ai_audit_count:0};
    audit.workspace.candidates=[row];renderAssetReview(audit);confirmed=false;
    promptValues=['audit-human-Z','owner','','[]','{"CONTRACT":90}','[]','[]','[]'];
    const input=walk(host).find(n=>n.tag==='button'&&n.textContent==='\u76e3\u67fb\u8a18\u9332\u3092\u5165\u529b');
    await input.listeners.click();
    assert.equal(calls[0][0],'audit_prepare_record');
    assert.deepEqual(calls[1],['audit_cancel_record',{confirmation_id:'audit-record-confirm'}]);
    assert.deepEqual(publicErrors,[AUDIT_INPUT_PUBLIC_ERROR,AUDIT_INPUT_PUBLIC_ERROR]);
    assert.equal(calls.filter(c=>c[0]==='audit_apply_record').length,0);assert.equal(refreshed,0);
  });
  await scenario('invalid audit JSON is effect zero and public safe',async()=>{
    const audit=fixture(),row={...candidate('Z',[]),audit_count:0,ai_audit_count:0};
    audit.workspace.candidates=[row];renderAssetReview(audit);
    promptValues=['audit-human-Z','owner','','not-json'];
    const input=walk(host).find(n=>n.tag==='button'&&n.textContent==='\u76e3\u67fb\u8a18\u9332\u3092\u5165\u529b');
    await input.listeners.click();assert.equal(calls.length,0);assert.equal(refreshed,0);
    assert.equal(promptCalls,4);
  });
  await scenario('cancelled first audit JSON stops later prompts',async()=>{
    const audit=fixture(),row={...candidate('Z',[]),audit_count:0,ai_audit_count:0};
    audit.workspace.candidates=[row];renderAssetReview(audit);
    promptValues=['audit-human-Z','owner','',null,'should-not-be-read'];
    const input=walk(host).find(n=>n.tag==='button'&&n.textContent==='\u76e3\u67fb\u8a18\u9332\u3092\u5165\u529b');
    await input.listeners.click();assert.equal(calls.length,0);assert.equal(refreshed,0);
    assert.equal(promptCalls,4);assert.equal(promptValues.length,1);
  });
  await scenario('saved decision reopen no redecision',async()=>{
    const audit=fixture();audit.workspace.candidates=[{...candidate('B',[]),
      lifecycle_state:'ACCEPTED',human_decision_record:{decision:'ACCEPT',actor_id:'owner',decision_id:'decision-B'}}];
    renderAssetReview(audit);
    assert.equal(walk(host).filter(n=>n.tag==='button').length,0);
    assert.ok(walk(host).some(n=>n.textContent.includes('Human Decision: ACCEPT')&&n.textContent.includes('Decision ID: decision-B')));
    assert.equal(calls.length,0);assert.equal(hasMissingAuditLabel(),false);
  });
  await scenario('recovery render suppresses decisions and invalid actions',async()=>{
    const audit=fixture();audit.recovery={required:true,available_actions:['COMPLETE','DELETE','FINALIZE'],state:'RECOVERY',candidate_id:'B'};
    renderAssetReview(audit);
    assert.deepEqual(walk(host).filter(n=>n.tag==='button').map(n=>n.textContent),['COMPLETE','FINALIZE']);
  });
  await scenario('audited ready omits missing audit explanation',async()=>{
    renderAssetReview(fixture());assert.equal(hasMissingAuditLabel(),false);assert.equal(calls.length,0);
  });
  await scenario('recovery zero audit omits missing audit explanation',async()=>{
    const audit=fixture();audit.recovery={required:true,available_actions:[],state:'RECOVERY'};
    audit.workspace.candidates=[{...candidate('Z',[]),audit_count:0,ai_audit_count:0}];
    renderAssetReview(audit);assert.equal(hasMissingAuditLabel(),false);
    assert.equal(walk(host).filter(n=>n.tag==='button').length,0);assert.equal(calls.length,0);
  });
  await scenario('non ready zero audit omits missing audit explanation',async()=>{
    const audit=fixture();audit.workspace.candidates=[{...candidate('Z',[]),lifecycle_state:'ACCEPTED',audit_count:0,ai_audit_count:0}];
    renderAssetReview(audit);assert.equal(hasMissingAuditLabel(),false);assert.equal(calls.length,0);
  });
  console.log(JSON.stringify({result:'PASS',scenarios:passed,actual_functions:5,real_store_writes:0}));
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace("__FUNCTIONS__", "\n".join(functions))
    completed = subprocess.run(
        [node, "-e", script], check=False, capture_output=True, text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout) == {
        "result": "PASS", "scenarios": 23, "actual_functions": 5, "real_store_writes": 0,
    }


def test_export_unbound_actions_are_disabled_with_public_safe_reasons_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Export binding behavior contract")
    helpers = "\n".join(
        re.search(rf"(?:async )?function {name}\(.*?\r?\n\}}", HTML, re.DOTALL).group(0)
        for name in (
            "exportBindingReason", "exportPreparationBindingMessage",
            "bindExportActionAvailability", "exportJourneyState", "refreshExport",
        )
    )
    script = f"""
const assert=require('node:assert/strict');
const EXPORT_SAFE_ERROR='safe',EXPORT_STAGE_COPY={{}},EXPORT_STAGE_PROGRESS={{}};
const view={{project:{{project_id:'project-1'}}}},review={{readiness:{{available:true}},approval:{{approval_current:true}}}};
const n=tag=>({{tag,children:[],dataset:{{}},style:{{}},append(...v){{this.children.push(...v)}},setAttribute(){{}},addEventListener(){{}}}});
const nodes=new Map(),$=id=>{{if(!nodes.has(id))nodes.set(id,n('div'));return nodes.get(id)}};
const document={{createElement:n}},element=(tag,cls,text)=>Object.assign(n(tag),{{className:cls,textContent:text}});
const clear=host=>host.children=[];const renderExportJourney=()=>{{}},scheduleExportRefresh=()=>{{}};
let model,prep;const call=async method=>({{export_queue_snapshot:model,final_review_export_snapshot:prep,snapshot:view,workflow_status:{{}},final_review_snapshot:review}})[method];
{helpers}
const all=host=>host.children.flatMap(child=>[child,...all(child)]);
(async()=>{{
  const cases=[['QUEUED','事前確認を開始','preflight_available'],['READY','書き出しを開始','dispatch_available'],['HUMAN_REQUIRED','設定を確認して再試行','preflight_available'],['SUCCEEDED','保存先を開く','destination_open_available']];
  for(const [stage,label,field] of cases){{
    for(const available of [false,true,undefined,'true',1]){{
      const row={{job_id:'job-1',stage,individual_confirmation_required:stage==='READY',recovery_actions:stage==='HUMAN_REQUIRED'?['RESUME_PREFLIGHT']:[],binding_blockers:['PREPARATION_UNBOUND'],[field]:available}};
      model={{available:true,rows:[row]}};prep={{available:true}};await refreshExport();
      const button=all($('exportContent')).find(v=>v.tag==='button'&&v.textContent===label);
      assert.ok(button,label);assert.equal(button.disabled,available!==true);
      assert.equal(!!button.dataset.disabledReason,available!==true);
      if(available!==true)assert.match(button.title,/未接続/);
      if(stage==='READY'&&available!==true)assert.equal(all($('exportContent')).find(v=>v.tag==='h3').textContent,'事前確認済み／実行接続待ち');
    }}
  }}
  for(const value of [undefined,null,{{}},{{dispatch_available:'true'}},{{dispatch_available:true}}]){{
    const button=n('button');bindExportActionAvailability(button,value,'dispatch_available');
    assert.equal(button.disabled,value?.dispatch_available!==true);
  }}
  model={{available:true,rows:[]}};prep={{available:false,state:'PRIVATE_EXPORT_PREPARATION_UNBOUND'}};await refreshExport();
  assert.equal($('exportPreparationState').textContent,'書き出し接続待ち');
  assert.equal($('addExportQueueButton').disabled,true);
  assert.match($('exportPreparationContent').textContent,/最終承認だけでは解消しません/);
  const pending=exportJourneyState(view,{{}},review,prep,[]);assert.equal(pending.blocked,true);assert.match(pending.message,/未実装/);
  const ready=exportJourneyState(view,{{}},review,{{}},[{{stage:'READY',binding_blockers:['DISPATCHER_UNBOUND'],dispatch_available:false}}]);
  assert.equal(ready.blocked,true);assert.doesNotMatch(ready.message,/開始できます/);
  const unknown=exportJourneyState(view,{{}},review,prep,[{{stage:'UNKNOWN'}}]);assert.match(unknown.message,/自動再試行せず/);
  console.log('OK');
}})().catch(err=>{{console.error(err);process.exit(1)}});
"""
    completed = subprocess.run(
        [node, "-e", script], check=False, capture_output=True, text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_top_menu_uses_explicit_command_registry_and_focus_contract() -> None:
    commands = set(re.findall(r'data-command="([^"]+)"', HTML))
    assert commands == {"fitEntire", "fitSelection", "jobs", "setIn", "setOut"}
    for command in commands:
        assert f"{command}:" in HTML
    for marker in (
        "const COMMAND_REGISTRY=Object.freeze",
        "aria-haspopup",
        "aria-expanded",
        "openMenu(button,true)",
        "closeMenus(true)",
        "lastMenuButton?.focus()",
        "ArrowDown",
        "ArrowUp",
        "Escape",
    ):
        assert marker in HTML
    assert "if(command==='" not in HTML


def test_settings_nine_category_tabs_are_read_only_but_interactive() -> None:
    categories = re.findall(r'data-settings-view="([^"]+)"', HTML)
    assert categories == [
        "general",
        "project",
        "models",
        "secret",
        "profile",
        "editing",
        "audio",
        "export",
        "advanced",
    ]
    assert "const SETTINGS_VIEWS=Object.freeze" in HTML
    assert "function renderSettingsView(view)" in HTML
    assert "role=\"tablist\"" in HTML
    assert "role=\"tabpanel\"" in HTML
    assert "credential_values_redisplayed:false" in HTML
    assert "provider_execution_authorized:false" in HTML
    assert "paid_execution_authorized:false" in HTML


def test_audio_and_quick_pages_only_show_central_settings_readiness() -> None:
    for marker in (
        "audioModelReadiness",
        "quickModelReadiness",
        "function featureSelectionState",
        "音声・音楽用AIモデル",
        "クイック生成用AIモデル",
        "画像・動画用のAIモデル設定を使います。",
        "AIモデル設定を開く",
    ):
        assert marker in HTML

    for local_editor_marker in (
        "audioModelSelection",
        "quickModelSelection",
        "data.modelSelectionPage",
        "Project既定Routeを保存",
        "function renderModelSelection",
    ):
        assert local_editor_marker not in HTML


def test_central_settings_keeps_unavailable_audio_routes_disabled_and_explained() -> None:
    for marker in (
        "CENTRAL_MODEL_WORKLOADS=new Set(['PLANNING','IMAGE','VIDEO','AUDIO','MUSIC'])",
        "ここだけで企画・画像・動画・音声・音楽のAIモデルを選択して保存します。",
        "クイック生成は画像・動画の設定を使います。",
        "option.disabled=route.selectable===false",
        "settingsAvailabilityText",
        "現在は利用できません。設定または準備状態を確認してください。",
        "function centralPreferredRouteValue",
        "preserveUnavailablePreferred",
        "if(preferredRouteId!==undefined)preferredRouteIds[row.workload]=preferredRouteId",
        "AIモデル設定を保存",
    ):
        assert marker in HTML


def test_central_settings_preserves_unavailable_route_until_user_changes_it_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the central Settings behavior contract")

    match = re.search(r"function centralPreferredRouteValue\(select\)\{[^\r\n]+", HTML)
    assert match is not None
    script = f"""
const assert=require('node:assert/strict');
{match.group(0)}
assert.equal(centralPreferredRouteValue({{dataset:{{preserveUnavailablePreferred:'true'}},value:''}}),undefined);
assert.equal(centralPreferredRouteValue({{dataset:{{}},value:'local-audio-route'}}),'local-audio-route');
assert.equal(centralPreferredRouteValue({{dataset:{{}},value:''}}),null);
console.log('OK');
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_central_settings_save_uses_shipped_selector_with_nonempty_workload_in_node() -> None:
    node_executable = shutil.which("node")
    if node_executable is None:
        pytest.skip("Node.js is required for the central Settings save contract")

    def javascript_function(name: str) -> str:
        match = re.search(rf"(?:async )?function {re.escape(name)}\([^\r\n]+", HTML)
        assert match is not None
        return match.group(0)

    functions = "\n".join(
        javascript_function(name)
        for name in ("centralPreferredRouteValue", "requiredLocalRuntimeNames",
                     "localRuntimeWarning", "renderRequiredRuntimeWarnings",
                     "renderCentralModelSettings")
    )
    script = f"""
const assert=require('node:assert/strict');
const PLANNING_STATE_SAFE_ERROR='企画の状態を確認できませんでした。プロジェクトを開き直してから、もう一度確認してください。';
const CENTRAL_MODEL_WORKLOADS=new Set(['PLANNING','IMAGE','VIDEO','AUDIO','MUSIC']);
function node(tag='div',text=''){{return {{tag,textContent:text,children:[],dataset:{{}},listeners:{{}},attrs:new Map(),disabled:false,value:'',append(...items){{this.children.push(...items)}},replaceChildren(...items){{this.children=[...items]}},addEventListener(name,listener){{this.listeners[name]=listener}},setAttribute(name,value){{this.attrs.set(name,value)}},removeAttribute(name){{this.attrs.delete(name)}},querySelector(selector){{const match=selector.match(/^\\[data-connection-route="([^"]+)"\\]$/);if(!match)return null;const route=match[1];const visit=current=>{{if(current.dataset?.connectionRoute===route)return current;for(const child of current.children||[]){{const found=visit(child);if(found)return found}}return null}};return visit(this)}}}}}}
const elements={{settingsContent:node('div')}};
const document={{createElement(tag){{return node(tag)}}}};
function $(id){{return elements[id]}}
function clear(host){{host.replaceChildren()}}
function element(tag,_className,text){{return node(tag,text)}}
function card(title,body){{const item=node('div',title);item.body=body;return item}}
function renderOllamaRuntimeStatus(){{}}
function renderComputeSettings(){{}}
function settingsWorkloadName(row){{return row.workload}}
function settingsModelLabel(route){{return route.model_id||''}}
function settingsAvailabilityText(){{return ''}}
const notifications=[];
function notify(message,isError=false){{notifications.push({{message,isError}})}}
let refreshCount=0;
async function refreshGlobalPlanningAiStatus(){{refreshCount+=1}}
let renderSettingsCount=0;
async function renderSettingsView(){{renderSettingsCount+=1}}
let currentSettingsView='models';
const rpc=[];
async function call(method,args={{}},publicError=null){{rpc.push({{method,args,publicError}});return {{revision:8}}}}
{functions}
(async()=>{{
  const form={{available:true,revision:7,workloads:[
    {{workload:'PLANNING',selection_mode:'MANUAL',preferred_route_id:'plan-local',routes:[{{route_id:'plan-local',model_id:'qwen3:8b',selectable:true}}]}},
    {{workload:'IMAGE',selection_mode:'AUTOMATIC',preferred_route_id:null,routes:[]}},
  ]}};
  renderCentralModelSettings(form,{{}},{{}});
  const planning=elements.settingsContent.querySelector('[data-connection-route="PLANNING"]');
  const image=elements.settingsContent.querySelector('[data-connection-route="IMAGE"]');
  assert.ok(planning);
  assert.ok(image);
  planning.value='plan-local';
  image.value='';
  const save=elements.settingsContent.children.find(item=>item.textContent==='AIモデル設定を保存');
  assert.ok(save);
  await save.listeners.click();
  assert.equal(rpc.length,1);
  assert.equal(rpc[0].method,'connection_settings_update');
  assert.equal(rpc[0].publicError,PLANNING_STATE_SAFE_ERROR);
  assert.deepEqual(rpc[0].args,{{
    revision:7,
    workload_modes:{{PLANNING:'MANUAL',IMAGE:'AUTOMATIC'}},
    preferred_route_ids:{{PLANNING:'plan-local',IMAGE:null}},
  }});
  assert.equal(refreshCount,1);
  assert.equal(renderSettingsCount,1);
  assert.equal(save.disabled,false);
  assert.equal(save.attrs.has('aria-busy'),false);
  assert.deepEqual(notifications,[{{message:'AIモデル設定を保存しました。AIの実行・課金・生成は開始していません。',isError:false}}]);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node_executable, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_planning_readiness_separates_settings_runtime_and_application_failures_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the planning readiness behavior contract")

    copy_match = re.search(r"const FEATURE_MODEL_COPY=Object\.freeze\(\{[^\r\n]+", HTML)
    selection_match = re.search(r"function featureSelectionState\(model,copy\)\{[^\r\n]+", HTML)
    readiness_match = re.search(r"function featureReadinessState\(model,page,runtime,compute,operationStatus\)\{[^\r\n]+", HTML)
    presentation_match = re.search(r"function planningGenerationPresentation\(status,readiness\)\{[^\r\n]+", HTML)
    runtime_match = re.search(r"function renderOllamaRuntimeStatus\(host,runtime\)\{[^\r\n]+", HTML)
    label_match = re.search(r"function settingsModelLabel\(route,index\)\{[^\r\n]+", HTML)
    assert all((copy_match, selection_match, readiness_match, presentation_match, runtime_match, label_match))
    script = f"""
const assert=require('node:assert/strict');
{copy_match.group(0)}
{selection_match.group(0)}
{readiness_match.group(0)}
{presentation_match.group(0)}
{runtime_match.group(0)}
{label_match.group(0)}
const centralSelection={{available:true,selectors:[{{page_id:'PLANNING',available:true,preferred_route_id:'plan-route',candidates:[{{route_id:'plan-route',configuration_selectable:true,display_name_ja:'企画用ローカルAI',model_id:'qwen3:8b'}}]}}]}};
const combinedReady=featureReadinessState(centralSelection,'planning',{{state:'READY'}},{{workloads:[]}},{{available:true}});
assert.equal(combinedReady.ready,true);
assert.equal(combinedReady.computeRequired,false);
assert.equal(featureReadinessState({{available:false}},'planning',{{state:'READY'}},{{workloads:[]}},{{available:true}}).ready,false);
assert.equal(featureReadinessState(centralSelection,'planning',{{state:'STARTING'}},{{workloads:[]}},{{available:true}}).ready,false);
assert.equal(featureReadinessState(centralSelection,'planning',{{state:'READY'}},{{workloads:[]}},{{available:false}}).ready,false);
const missing=planningGenerationPresentation({{available:false,blocker_code:'ERR_TASK036_PLANNING_CONNECTION_STALE'}},{{selectionReady:false,computeReady:true,runtimeReady:true,runtimeState:'READY'}});
assert.equal(missing.ready,false);
assert.equal(missing.state,'MODEL_SELECTION_MISSING');
assert.match(missing.message,/設定/);
assert.doesNotMatch(missing.message,/ERR_TASK036/);
const starting=planningGenerationPresentation({{available:true,model_id:'qwen3:8b'}},{{selectionReady:true,computeReady:true,runtimeReady:false,runtimeState:'STARTING'}});
assert.equal(starting.ready,false);
assert.equal(starting.state,'RUNTIME_STARTING');
assert.match(starting.message,/準備中/);
const unbound=planningGenerationPresentation({{available:false}},{{selectionReady:true,computeReady:true,runtimeReady:true,runtimeState:'READY'}});
assert.equal(unbound.ready,false);
assert.equal(unbound.state,'APPLICATION_UNBOUND');
assert.match(unbound.message,/プロジェクト/);
const configuredBlocker=planningGenerationPresentation({{available:false,blocker_code:'ERR_TASK036_PLANNING_CONNECTION_STALE'}},{{selectionReady:true,computeReady:true,runtimeReady:true,runtimeState:'READY'}});
assert.equal(configuredBlocker.ready,false);
assert.equal(configuredBlocker.state,'MODEL_CONFIGURATION_INVALID');
const ready=planningGenerationPresentation({{available:true,model_id:'qwen3:8b'}},{{selectionReady:true,computeReady:true,runtimeReady:true,runtimeState:'READY'}});
assert.equal(ready.ready,true);
assert.equal(ready.state,'READY');
assert.doesNotMatch(ready.message,/qwen3:8b/);
assert.equal(settingsModelLabel({{display_name_ja:'qwen3:8b',model_id:'qwen3:8b'}},1),'qwen3:8b');
assert.equal(settingsModelLabel({{model_id:'qwen3:8b'}},1),'qwen3:8b');
assert.equal(settingsModelLabel({{display_name_ja:'Planning AI',model_id:'qwen3:8b'}},1),'Planning AI / qwen3:8b');
for(const unsafe of ['private/model','C:\\\\private','user@host','https://host','token=value','SECRET','api_key=value','apikey=value','x'.repeat(81),'x'+String.fromCharCode(0),'x'+String.fromCharCode(127),'e'+String.fromCharCode(769),'😀'.repeat(65),'ſecret-model']){{
  assert.equal(settingsModelLabel({{display_name_ja:'登録済みローカルAIモデル',model_id:unsafe}},1),'登録済みローカルAIモデル');
}}
const host={{items:[],append(item){{this.items.push(item)}}}};
function card(title,body){{return `${{title}}\n${{body}}`;}}
renderOllamaRuntimeStatus(host,{{state:'FAILED',message_ja:'ERR_TASK036_SECRET C:\\Users\\owner\\token.txt'}});
assert.doesNotMatch(host.items.join(String.fromCharCode(10)),/ERR_TASK036|token\\.txt|C:\\Users/);
console.log('OK');
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_planning_generation_is_single_flight_public_safe_and_header_synced_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Planning generation behavior contract")

    def javascript_function(name: str) -> str:
        match = re.search(rf"(?:async )?function {re.escape(name)}\([^\r\n]+", HTML)
        assert match is not None
        return match.group(0)

    presentation = javascript_function("planningGenerationPresentation")
    render_global = javascript_function("renderGlobalPlanningAiStatus")
    render_status = javascript_function("renderPlanningGenerationStatus")
    generate = javascript_function("generatePlanning")
    script = f"""
const assert=require('node:assert/strict');
const PLANNING_GENERATION_SAFE_ERROR='企画候補を作成できませんでした。企画の保存状態を再確認します。自動では再実行しません。';
const calls=[];
const notifications=[];
const elements={{
  planningGenerateButton:{{disabled:false,attrs:new Map(),setAttribute(k,v){{this.attrs.set(k,v)}}}},
  planningGenerationStatus:{{textContent:''}},
  planningRequest:{{value:'2秒の紹介動画'}},
  globalModelButton:{{textContent:'',title:''}},
  planningContent:{{querySelector(){{return null}}}},
}};
function $(id){{return elements[id]}}
function notify(message,isError=false){{notifications.push({{message,isError}})}}
let confirmValue=true;
const window={{confirm(){{return confirmValue}}}};
let releasePrepare;
let prepareGate=new Promise(resolve=>{{releasePrepare=resolve}});
let failApply=false;
async function call(method,args={{}},publicError=null){{
  calls.push({{method,args,publicError}});
  if(method==='planning_generation_prepare'){{
    await prepareGate;
    return {{confirmation_id:'confirm-1',already_generated:false}};
  }}
  if(method==='planning_generation_apply'){{
    if(failApply){{
      notify(publicError||'planning_generation_apply: [Errno 36] C:\\private\\proposal.json',true);
      return null;
    }}
    return {{idempotent:false}};
  }}
  if(method==='planning_generation_cancel')return {{cancelled:true}};
  throw new Error('unexpected method '+method);
}}
let refreshCount=0;
async function refreshPlanning(){{refreshCount+=1;renderPlanningGenerationStatus(currentPlanningGeneration,currentPlanningReadiness)}}
let currentPlanningModel={{snapshot_sha256:'sha256:'+'a'.repeat(64),workspace:{{}}}};
let currentPlanningGeneration={{available:true}};
let currentPlanningReadiness={{selectionReady:true,computeReady:true,runtimeReady:true,runtimeState:'READY'}};
let planningGenerationInFlight=false;
{presentation}
{render_global}
{render_status}
{generate}
(async()=>{{
  renderPlanningGenerationStatus(currentPlanningGeneration,currentPlanningReadiness);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 設定済み');
  assert.equal(elements.planningGenerateButton.attrs.get('aria-busy'),'false');
  const first=generatePlanning();
  const duplicate=generatePlanning();
  assert.equal(elements.globalModelButton.textContent,'企画AI: 生成中');
  assert.equal(elements.planningGenerateButton.attrs.get('aria-busy'),'true');
  releasePrepare();
  await Promise.all([first,duplicate]);
  assert.equal(calls.filter(item=>item.method==='planning_generation_prepare').length,1);
  assert.equal(calls.filter(item=>item.method==='planning_generation_apply').length,1);
  assert.equal(refreshCount,1);
  assert.equal(planningGenerationInFlight,false);
  assert.equal(elements.planningGenerateButton.attrs.get('aria-busy'),'false');
  assert.equal(elements.globalModelButton.textContent,'企画AI: 設定済み');

  elements.planningRequest.value='キャンセル';
  confirmValue=false;
  prepareGate=Promise.resolve();
  await generatePlanning();
  assert.equal(calls.filter(item=>item.method==='planning_generation_cancel').length,1);
  assert.equal(refreshCount,2);
  assert.equal(planningGenerationInFlight,false);

  elements.planningRequest.value='失敗';
  confirmValue=true;
  failApply=true;
  await generatePlanning();
  assert.equal(calls.filter(item=>item.method==='planning_generation_apply').length,2);
  assert.equal(refreshCount,3);
  assert.equal(planningGenerationInFlight,false);
  assert.equal(notifications.at(-1).message,PLANNING_GENERATION_SAFE_ERROR);
  assert.doesNotMatch(notifications.at(-1).message,/Errno|planning_generation_apply|private|proposal\\.json/i);
  for(const item of calls.filter(item=>item.method.startsWith('planning_generation_'))){{
    assert.equal(item.publicError,PLANNING_GENERATION_SAFE_ERROR);
  }}

  currentPlanningReadiness={{selectionReady:true,computeReady:true,runtimeReady:false,runtimeState:'STARTING'}};
  renderPlanningGenerationStatus(currentPlanningGeneration,currentPlanningReadiness);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 準備中');
  currentPlanningReadiness={{selectionReady:false,computeReady:true,runtimeReady:true,runtimeState:'READY'}};
  renderPlanningGenerationStatus(currentPlanningGeneration,currentPlanningReadiness);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 未設定');
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_home_startup_settings_save_and_close_refresh_global_planning_header_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the global Planning header lifecycle contract")

    def javascript_function(name: str) -> str:
        match = re.search(rf"(?:async )?function {re.escape(name)}\([^\r\n]+", HTML)
        assert match is not None
        return match.group(0)

    copy_match = re.search(r"const FEATURE_MODEL_COPY=Object\.freeze\(\{[^\r\n]+", HTML)
    assert copy_match is not None
    lifecycle_match = re.search(
        r"window\.addEventListener\('pywebviewready',initializeShell\);"
        r"window\.setTimeout\(async\(\)=>\{if\(window\.pywebview\)await initializeShell\(\)\},350\);",
        HTML,
    )
    assert lifecycle_match is not None
    functions = "\n".join(
        javascript_function(name)
        for name in (
            "featureSelectionState",
            "featureReadinessState",
            "planningGenerationPresentation",
            "renderGlobalPlanningAiStatus",
            "refreshGlobalPlanningAiStatus",
            "refreshPage",
            "initializeShell",
            "closeSettings",
            "renderCentralModelSettings",
        )
    )
    script = f"""
const assert=require('node:assert/strict');
const PLANNING_STATE_SAFE_ERROR='企画の状態を確認できませんでした。プロジェクトを開き直してから、もう一度確認してください。';
{copy_match.group(0)}
const CENTRAL_MODEL_WORKLOADS=new Set(['PLANNING','IMAGE','VIDEO','AUDIO','MUSIC']);
const lifecycle={{}};
const window={{pywebview:null,addEventListener(name,handler){{lifecycle[name]=handler}},setTimeout(handler,delay){{lifecycle.fallback=handler;lifecycle.delay=delay}}}};
function node(text=''){{return {{textContent:text,children:[],dataset:{{}},listeners:{{}},attrs:new Map(),disabled:false,append(...items){{this.children.push(...items)}},replaceChildren(...items){{this.children=[...items]}},addEventListener(name,listener){{this.listeners[name]=listener}},setAttribute(name,value){{this.attrs.set(name,value)}},removeAttribute(name){{this.attrs.delete(name)}},focus(){{this.focused=true}}}}}}
const elements={{
  globalModelButton:node(),
  settingsContent:node(),
  settingsOverlay:node(),
  settingsButton:node(),
}};
elements.settingsOverlay.classList={{open:true,contains(name){{return name==='open'&&this.open}},remove(name){{if(name==='open')this.open=false}}}};
function $(id){{return elements[id]}}
function clear(host){{host.replaceChildren()}}
function element(_tag,_className,text){{return node(text)}}
function card(title,body){{const item=node(title);item.body=body;return item}}
function renderOllamaRuntimeStatus(){{}}
function renderComputeSettings(){{}}
function settingsWorkloadName(row){{return row.workload}}
function settingsModelLabel(route){{return route.model_id||''}}
function settingsAvailabilityText(){{return ''}}
function centralPreferredRouteValue(){{return null}}
const notifications=[];
function notify(message,isError=false){{notifications.push({{message,isError}})}}
let renderSettingsCount=0;
async function renderSettingsView(){{renderSettingsCount+=1}}
let refreshShellCount=0;
async function refreshShell(){{refreshShellCount+=1}}
let planningStatus={{available:false}};
let selection={{available:true,selectors:[]}};
let runtime={{state:'READY'}};
let compute={{workloads:[]}};
const rpc=[];
async function call(method,args={{}},publicError=null){{
  rpc.push({{method,args,publicError}});
  if(method==='planning_generation_status')return planningStatus;
  if(method==='model_selection_snapshot')return selection;
  if(method==='ollama_runtime_snapshot')return runtime;
  if(method==='desktop_compute_settings_snapshot')return compute;
  if(method==='connection_settings_update'){{
    selection={{available:true,selectors:[{{page_id:'PLANNING',available:true,preferred_route_id:'plan-route',candidates:[{{route_id:'plan-route',configuration_selectable:true,model_id:'qwen3:8b'}}]}}]}};
    planningStatus={{available:false,blocker_code:'ERR_TASK036_PLANNING_CONNECTION_STALE'}};
    return {{revision:2}};
  }}
  throw new Error('unexpected method '+method);
}}
let planningGenerationInFlight=false;
let currentPage='home';
let currentSettingsView='models';
let currentOwnerSigningKeyImport=null;
function ownerSigningKeyImportId(){{return null}}
{functions}
{lifecycle_match.group(0)}
(async()=>{{
  assert.equal(lifecycle.delay,350);
  await lifecycle.pywebviewready();
  assert.equal(refreshShellCount,1);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 未設定');
  const startupReads=rpc.filter(item=>['planning_generation_status','model_selection_snapshot','ollama_runtime_snapshot','desktop_compute_settings_snapshot'].includes(item.method));
  assert.equal(startupReads.length,4);
  startupReads.forEach(item=>assert.equal(item.publicError,PLANNING_STATE_SAFE_ERROR));

  renderCentralModelSettings({{available:true,revision:1,workloads:[]}},compute,runtime);
  const save=elements.settingsContent.children.find(item=>item.textContent==='AIモデル設定を保存');
  assert.ok(save);
  await save.listeners.click();
  assert.equal(elements.globalModelButton.textContent,'企画AI: 要確認');
  assert.equal(renderSettingsCount,1);
  assert.equal(save.attrs.has('aria-busy'),false);
  assert.equal(rpc.find(item=>item.method==='connection_settings_update').publicError,PLANNING_STATE_SAFE_ERROR);

  planningStatus={{available:true}};
  await closeSettings();
  assert.equal(elements.settingsOverlay.classList.open,false);
  assert.equal(elements.settingsButton.focused,true);
  assert.equal(refreshShellCount,2);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 設定済み');

  runtime={{state:'STARTING'}};
  await refreshGlobalPlanningAiStatus();
  assert.equal(elements.globalModelButton.textContent,'企画AI: 準備中');

  runtime={{state:'READY'}};
  selection=null;
  window.pywebview={{}};
  await lifecycle.fallback();
  assert.equal(refreshShellCount,3);
  assert.equal(elements.globalModelButton.textContent,'企画AI: 要確認');
  assert.ok(rpc.filter(item=>['planning_generation_status','model_selection_snapshot','ollama_runtime_snapshot','desktop_compute_settings_snapshot'].includes(item.method)).every(item=>item.publicError===PLANNING_STATE_SAFE_ERROR));
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_export_dispatch_ui_confirms_once_cancels_cleanly_and_reads_durable_state_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Export dispatch behavior contract")

    match = re.search(
        r"async function prepareExportDispatch\(row\)\{.*?\r?\n\}",
        HTML,
        re.DOTALL,
    )
    assert match is not None
    script = f"""
const assert=require('node:assert/strict');
const window={{confirm(){{return confirmDecision}}}};
const notifications=[];
function notify(message,isError=false){{notifications.push({{message,isError}})}}
let refreshCount=0;
async function refreshExport(){{refreshCount+=1}}
const EXPORT_SAFE_ERROR='書き出し操作の結果を確認できませんでした。状態を再読込してください。';
const exportDispatchInFlight=new Set();
let confirmDecision=true;
let calls=[];
let scenario='success';
async function call(method,args,publicError){{
  calls.push([method,args,publicError]);
  if(method==='export_queue_preflight')return {{state:'READY'}};
  if(method==='export_queue_prepare_dispatch')return {{confirmation_id:'confirmation-1',operation_identity:'operation-1'}};
  if(method==='export_queue_cancel_dispatch')return scenario==='cancel-unconfirmed'?null:{{confirmation_id:'confirmation-1',job_id:'job-1',cancelled:true,external_mutation_started:false}};
  if(method==='export_queue_apply_dispatch')return scenario==='ambiguous'?null:{{state:'SUCCEEDED'}};
  if(method==='export_queue_snapshot'){{
    const stage=scenario==='ambiguous'?'DISPATCHING':scenario==='cancel'?'READY':'SUCCEEDED';
    return {{available:true,rows:[{{job_id:'job-1',stage,evidence_ref:stage==='SUCCEEDED'?'render-artifact:'+'a'.repeat(64):null}}]}};
  }}
  throw new Error('unexpected method '+method);
}}
{match.group(0)}
(async()=>{{
  await Promise.all([
    prepareExportDispatch({{job_id:'job-1',stage:'READY'}}),
    prepareExportDispatch({{job_id:'job-1',stage:'READY'}}),
  ]);
  assert.deepEqual(calls.map(item=>item[0]),[
    'export_queue_prepare_dispatch','export_queue_apply_dispatch','export_queue_snapshot'
  ]);
  assert.ok(calls.every(item=>item[2]===EXPORT_SAFE_ERROR));
  assert.match(notifications.at(-1).message,/書き出し状態の再読込: SUCCEEDED/);
  assert.match(notifications.at(-1).message,/render-artifact:/);
  assert.equal(exportDispatchInFlight.size,0);
  assert.equal(refreshCount,1);

  calls=[];scenario='cancel';confirmDecision=false;
  await prepareExportDispatch({{job_id:'job-1',stage:'READY'}});
  assert.deepEqual(calls.map(item=>item[0]),[
    'export_queue_prepare_dispatch','export_queue_cancel_dispatch'
  ]);
  assert.doesNotMatch(calls.map(item=>item[0]).join(','),/apply_dispatch/);
  assert.match(notifications.at(-1).message,/Jobは実行していません/);

  calls=[];scenario='cancel-unconfirmed';confirmDecision=false;
  await prepareExportDispatch({{job_id:'job-1',stage:'READY'}});
  assert.deepEqual(calls.map(item=>item[0]),[
    'export_queue_prepare_dispatch','export_queue_cancel_dispatch'
  ]);
  assert.match(notifications.at(-1).message,/取消結果を確認できません/);
  assert.equal(notifications.at(-1).isError,true);
  assert.doesNotMatch(notifications.at(-1).message,/取り消しました|Jobは実行していません/);

  calls=[];scenario='ambiguous';confirmDecision=true;
  await prepareExportDispatch({{job_id:'job-1',stage:'READY'}});
  assert.deepEqual(calls.map(item=>item[0]),[
    'export_queue_prepare_dispatch','export_queue_apply_dispatch','export_queue_snapshot'
  ]);
  assert.match(notifications.at(-1).message,/書き出し状態の再読込: DISPATCHING/);
  assert.match(notifications.at(-1).message,/出力: 未確認/);
  assert.doesNotMatch(notifications.at(-1).message,/SUCCEEDED/);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_export_rpc_rejections_use_public_safe_error_copy_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Export RPC error behavior contract")

    call_match = re.search(r"async function call\(method,args=\{\},publicError=null\)\{[^\r\n]+", HTML)
    assert call_match is not None
    script = f"""
const assert=require('node:assert/strict');
const notifications=[];
function notify(message,isError=false){{notifications.push({{message,isError}})}}
const privateError='C:'+String.fromCharCode(92)+'Users'+String.fromCharCode(92)+'owner'+String.fromCharCode(92)+'exports'+String.fromCharCode(92)+'secret.mp4';
const window={{pywebview:{{api:{{
  export_queue_apply_dispatch:async()=>{{throw new Error(privateError)}},
  export_queue_snapshot:async()=>{{throw new Error(privateError)}},
}}}}}};
{call_match.group(0)}
(async()=>{{
  const publicError='書き出し操作の結果を確認できませんでした。状態を再読込してください。';
  assert.equal(await call('export_queue_apply_dispatch',{{confirmation_id:'confirmation-1'}},publicError),null);
  assert.equal(await call('export_queue_snapshot',{{}},publicError),null);
  assert.equal(notifications.length,2);
  assert.ok(notifications.every(item=>item.message===publicError&&item.isError===true));
  assert.doesNotMatch(notifications.map(item=>item.message).join('\\n'),/Users|owner|secret[.]mp4/);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_export_journey_projects_each_user_visible_state_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the Export journey behavior contract")

    match = re.search(
        r"function exportJourneyState\(.*?\r?\n\}",
        HTML,
        re.DOTALL,
    )
    assert match is not None
    helpers = "\n".join(
        re.search(rf"function {name}\(.*?\r?\n\}}", HTML, re.DOTALL).group(0)
        for name in ("exportBindingReason", "exportPreparationBindingMessage")
    )
    script = f"""
const assert=require('node:assert/strict');
{helpers}
{match.group(0)}
const project={{project:{{project_id:'project-1'}}}};
const editing={{next_recommended_action:'edit_plan.approve'}};
const reviewReady={{readiness:{{available:true}},approval:{{approval_current:false}}}};
const approved={{readiness:{{available:true}},approval:{{approval_current:true}}}};
const preparation={{available:true}};
assert.equal(exportJourneyState({{}},{{}},{{}},{{}},[]).current,'source');
assert.equal(exportJourneyState(project,editing,{{readiness:{{available:false}}}},{{}},[]).current,'edit');
assert.equal(exportJourneyState(project,editing,reviewReady,preparation,[]).current,'approval');
assert.equal(exportJourneyState(project,editing,approved,preparation,[]).current,'settings');
assert.equal(exportJourneyState(project,editing,approved,preparation,[{{stage:'QUEUED'}}]).current,'preflight');
assert.equal(exportJourneyState(project,editing,approved,preparation,[{{stage:'READY'}}]).current,'render');
const running=exportJourneyState(project,editing,approved,preparation,[{{stage:'RUNNING'}}]);
assert.equal(running.current,'render');
assert.match(running.message,/書き出し中/);
const succeeded=exportJourneyState(project,editing,approved,preparation,[{{stage:'SUCCEEDED',destination_open_available:true}}]);
assert.equal(succeeded.done.result,true);
assert.match(succeeded.message,/保存先を開けます/);
const retry=exportJourneyState(project,editing,approved,preparation,[{{stage:'HUMAN_REQUIRED',preflight_available:true}}]);
assert.equal(retry.current,'preflight');
assert.equal(retry.blocked,true);
assert.match(retry.message,/再試行/);
const failed=exportJourneyState(project,editing,approved,preparation,[{{stage:'FAILED'}}]);
assert.equal(failed.current,'render');
assert.match(failed.message,/失敗/);
const unknown=exportJourneyState(project,editing,approved,preparation,[{{stage:'UNKNOWN'}}]);
assert.equal(unknown.current,'result');
assert.match(unknown.message,/自動再試行せず/);
console.log('OK');
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_timeline_scrub_uses_python_owned_seek_without_frontend_truth() -> None:
    for marker in (
        "function startTimelineScrub(event,target)",
        "function queueTimelineScrub(clientX,target)",
        "interactive_timeline_seek",
        "addEventListener('pointerdown'",
        "role','slider'",
        "aria-valuenow",
        "durable_state_in_javascript=${model.durable_state_in_javascript}",
    ):
        assert marker in HTML
    assert "button.addEventListener('click',async event=>{event.stopPropagation();await call('interactive_timeline_select'" in HTML
    assert "lane.addEventListener('click',event=>{if(event.target!==lane||track.locked)return;seekFromClient" in HTML


def test_timeline_toolbar_retains_descriptive_native_accessibility_names() -> None:
    for label in (
        "タイムラインを拡大",
        "タイムラインを縮小",
        "タイムラインを左へスクロール",
        "タイムラインを右へスクロール",
        "前のトラックページ",
        "次のトラックページ",
    ):
        assert f'aria-label="{label}"' in HTML
    assert 'role="toolbar" aria-label="タイムライン表示操作"' in HTML


def test_v611_track_parts_match_canonical_mock_and_spec() -> None:
    for category in ("VIDEO", "SUBTITLE", "AUDIO", "SE", "BGM"):
        assert f'data-add-track="{category}"' in HTML
    for marker in (
        "function trackControl(",
        "interactive_timeline_update_track_state",
        "interactive_timeline_update_track_height",
        "interactive_timeline_prepare_add_track",
        "interactive_timeline_prepare_remove_track",
        "track.visible",
        "track.locked",
        "track.muted",
        "track.solo",
        "track.remove_available",
        "installTrackHeightControl",
    ):
        assert marker in HTML


def test_background_jobs_keeps_generation_and_export_recovery_visible() -> None:
    for marker in (
        'id="jobList"',
        'id="jobExportList"',
        "async function refreshJobs()",
        "generation_queue_snapshot",
        "export_queue_snapshot",
        "No replay",
    ):
        assert marker in HTML


def test_home_and_file_media_controls_use_the_canonical_ingest_route() -> None:
    for marker in (
        "async function chooseAndIngestMedia()",
        "workflow.next_recommended_action==='media.choose_and_ingest'",
        "call('choose_and_ingest_media',{},MEDIA_INGEST_PUBLIC_ERROR)",
        "result.status==='CANCELLED'",
        "result.status==='INGESTED'?mediaIngestIdentity(result):null",
        "Assetは登録していません",
        "動画をTASK-003 Assetへ登録しました",
        "$('chooseMediaButton').addEventListener('click',chooseAndIngestMedia)",
        "$('homeMediaButton').addEventListener('click',chooseAndIngestMedia)",
    ):
        assert marker in HTML
    assert "chooseAndReport('choose_media_source','メディア')" not in HTML
    assert "source_name" not in HTML
    assert "source_path" not in HTML


def test_native_dialog_failures_use_public_japanese_messages() -> None:
    assert "const FOLDER_SELECTION_PUBLIC_ERROR='フォルダー選択画面を開けませんでした。" in HTML
    assert "const MEDIA_INGEST_PUBLIC_ERROR='動画を読み込めませんでした。" in HTML
    assert "call(method,{},FOLDER_SELECTION_PUBLIC_ERROR)" in HTML
    assert "call('choose_and_ingest_media',{},MEDIA_INGEST_PUBLIC_ERROR)" in HTML


def test_media_controls_fail_closed_after_the_single_source_stage() -> None:
    for marker in (
        "const mediaReady=workflow?.available===true&&workflow.next_recommended_action==='media.choose_and_ingest'",
        "action.disabled=!mediaReady",
        "現在のProjectではSource Media追加工程を実行できません",
        "trusted pre-edit runtimeが接続されていません",
        "function mediaIngestIdentity(result)",
        "/^sha256:[0-9a-f]{64}$/",
    ):
        assert marker in HTML


def test_recommended_transcription_controls_use_one_local_safe_route() -> None:
    for marker in (
        "let transcriptionInFlight=false",
        "function transcriptionIdentity(result)",
        "async function runLocalTranscription()",
        "workflow.next_recommended_action!=='transcription.start'",
        "無償ローカルFasterWhisper",
        "モデルの自動ダウンロード・有償Provider・Cloudは使用しません",
        "call(route[1],{confirmation_id:prepared.confirmation_id})",
        "prepare_local_transcription_recovery",
        "cancel_local_transcription",
        "result?.status!=='TRANSCRIBED'",
        "result.provider_execution_mode!=='LOCAL'",
        "result.transcript_text_exposed!==false",
        "button.setAttribute('aria-busy','true')",
        "action.disabled=transcriptionInFlight||preEditStageInFlight||!workflow.next_recommended_action",
        "if(next==='transcription.start'){await runLocalTranscription();return}",
    ):
        assert marker in HTML
    assert "run_local_transcription',{model" not in HTML
    assert "allow_model_download" not in HTML


def test_subtitle_and_cut_controls_share_a_fail_closed_single_flight_route() -> None:
    for marker in (
        "let preEditStageInFlight=false",
        "function deterministicPreEditIdentity(result,next)",
        "async function runDeterministicPreEdit(next)",
        "if(preEditStageInFlight||transcriptionInFlight)return",
        "preEditStageInFlight=true",
        "workflow.next_recommended_action!==next",
        "create_runtime_subtitle_workspace",
        "generate_runtime_cut_candidates",
        "result.transcript_text_exposed!==false",
        "result.candidate_details_exposed!==false",
        "result.host_path_exposed!==false",
        "button.setAttribute('aria-busy','true')",
        "if(next==='subtitle.save'||next==='cut_candidates.generate')",
        "await runDeterministicPreEdit(next)",
    ):
        assert marker in HTML

def test_subtitle_and_cut_single_flight_route_behaves_fail_closed_in_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the V6.1.1 behavioral contract")

    def javascript_function(name: str) -> str:
        match = re.search(
            rf"(?:async )?function {re.escape(name)}\([^\r\n]+",
            HTML,
        )
        assert match is not None
        return match.group(0)

    identity = javascript_function("deterministicPreEditIdentity")
    runner = javascript_function("runDeterministicPreEdit")
    script = f"""
const assert=require('node:assert/strict');
const calls=[];
const notifications=[];
const buttons={{
  workflowActionButton:{{disabled:false,attrs:new Map(),setAttribute(k,v){{this.attrs.set(k,v)}},removeAttribute(k){{this.attrs.delete(k)}}}},
  homeWorkflowButton:{{disabled:false,attrs:new Map(),setAttribute(k,v){{this.attrs.set(k,v)}},removeAttribute(k){{this.attrs.delete(k)}}}},
}};
function $(id){{return buttons[id]}}
function notify(message,isError=false){{notifications.push({{message,isError}})}}
let refreshCount=0;
async function refreshShell(){{refreshCount+=1}}
let workflowAction='subtitle.save';
let releaseSubtitle;
const subtitleGate=new Promise(resolve=>{{releaseSubtitle=resolve}});
let cutResult={{status:'INVALID'}};
async function call(method){{
  calls.push(method);
  if(method==='workflow_status')return {{available:true,next_recommended_action:workflowAction}};
  if(method==='create_runtime_subtitle_workspace'){{
    await subtitleGate;
    return {{status:'SUBTITLE_READY',subtitle_workspace_sha256:'sha256:'+'a'.repeat(64),cue_count:2,next_recommended_action:'cut_candidates.generate',provider_execution_started:false,host_path_exposed:false,transcript_text_exposed:false}};
  }}
  if(method==='generate_runtime_cut_candidates')return cutResult;
  throw new Error('unexpected method '+method);
}}
let transcriptionInFlight=false;
let preEditStageInFlight=false;
{identity}
{runner}
(async()=>{{
  const first=runDeterministicPreEdit('subtitle.save');
  const second=runDeterministicPreEdit('subtitle.save');
  assert.equal(buttons.workflowActionButton.attrs.get('aria-busy'),'true');
  assert.equal(buttons.homeWorkflowButton.attrs.get('aria-busy'),'true');
  releaseSubtitle();
  await Promise.all([first,second]);
  assert.equal(calls.filter(method=>method==='create_runtime_subtitle_workspace').length,1);
  assert.equal(refreshCount,1);
  assert.equal(buttons.workflowActionButton.attrs.has('aria-busy'),false);
  assert.equal(buttons.homeWorkflowButton.attrs.has('aria-busy'),false);

  workflowAction='cut_candidates.generate';
  await runDeterministicPreEdit('subtitle.save');
  assert.equal(calls.filter(method=>method==='create_runtime_subtitle_workspace').length,1);
  assert.equal(notifications.at(-1).isError,true);
  assert.equal(refreshCount,2);

  await runDeterministicPreEdit('cut_candidates.generate');
  assert.equal(calls.filter(method=>method==='generate_runtime_cut_candidates').length,1);
  assert.equal(notifications.at(-1).isError,true);
  assert.equal(refreshCount,3);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"
