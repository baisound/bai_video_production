from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from ai_video_production.task036_shell_v611 import HTML

# Node startup exceeded 90 seconds under a contended Windows xdist worker.
# Keep this below the outer 120-second pytest timeout while preserving all assertions and bounded failure.
NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS = 110


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


def test_feature_pages_keep_model_readiness_read_only_and_route_unavailable_states_to_settings() -> None:
    for marker in (
        "function renderModelReadiness(model,page)",
        "function openModelSettings()",
        "NO_SELECTABLE_LOCAL_AUDIO_MODEL",
        "利用可能な無料ローカル音声AIモデルがありません",
        "selected?.configuration_selectable===true",
        "selected?.configuration_blockers",
        "AIモデル設定を開く",
        "右上の［設定］→［AIモデル］で確認してください。",
        "button.addEventListener('click',openModelSettings)",
        'role="status">AIモデル設定を読み込んでいます。',
    ):
        assert marker in HTML

    for obsolete_host in (
        "planningModelSelection",
        "imageModelSelection",
        "videoModelSelection",
        "audioModelSelection",
        "quickModelSelection",
        "data-model-selection-page",
        "Project既定Routeを保存",
    ):
        assert obsolete_host not in HTML

    assert HTML.count("call('connection_settings_update',{") == 1


def test_model_readiness_state_transitions_and_settings_cta_execute_in_node() -> None:
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

    unavailable_message = javascript_function("modelSelectionUnavailableMessage")
    open_settings = javascript_function("openModelSettings")
    readiness_host = javascript_function("modelReadinessHost")
    readiness_workloads = javascript_function("modelReadinessWorkloads")
    readiness_summary = javascript_function("modelReadinessSummary")
    render_readiness = javascript_function("renderModelReadiness")
    script = f"""
const assert=require('node:assert/strict');
const host={{children:[],append(...items){{this.children.push(...items)}}}};
const queriedIds=[];
function $(id){{queriedIds.push(id);return host}}
function clear(target){{target.children=[]}}
function card(title,text){{return {{kind:'card',title,text}}}}
function element(tag,className,text){{return {{kind:tag,className,text,type:null,listener:null,addEventListener(name,handler){{assert.equal(name,'click');this.listener=handler}}}}}}
const MODEL_WORKLOAD_LABELS={{PLANNING:'企画'}};
let currentSettingsView='general';
let openSettingsCount=0;
function openSettings(){{openSettingsCount+=1}}
{unavailable_message}
{open_settings}
{readiness_host}
{readiness_workloads}
{readiness_summary}
{render_readiness}
function snapshot(selectable,preferredRouteId='route-a'){{
  return {{available:true,selectors:[{{
    workload:'PLANNING',available:true,preferred_route_id:preferredRouteId,status:'READY',
    candidates:[{{route_id:'route-a',model_id:'qwen-local',provider_family:'Ollama',configuration_selectable:selectable,configuration_blockers:selectable?[]:['ROUTE_DISABLED']}}]
  }}]}};
}}
for(const [page,contract] of Object.entries({{
  planning:{{hostId:'planningModelReadiness',workloads:['PLANNING']}},
  imageGen:{{hostId:'imageModelReadiness',workloads:['IMAGE']}},
  videoGen:{{hostId:'videoModelReadiness',workloads:['VIDEO']}},
  audio:{{hostId:'audioModelReadiness',workloads:['AUDIO','MUSIC']}},
  quick:{{hostId:'quickModelReadiness',workloads:['QUICK_IMAGE','QUICK_VIDEO']}},
}})){{
  assert.deepEqual(modelReadinessWorkloads(page),contract.workloads);
  assert.equal(modelReadinessHost(page),host);
  assert.equal(queriedIds.at(-1),contract.hostId);
}}
renderModelReadiness(snapshot(false),'planning');
assert.match(host.children.find(item=>item.kind==='card').text,/未設定または利用できません/);
let cta=host.children.find(item=>item.kind==='button');
assert.ok(cta);
cta.listener();
assert.equal(currentSettingsView,'models');
assert.equal(openSettingsCount,1);

renderModelReadiness(snapshot(true),'planning');
assert.match(host.children.find(item=>item.kind==='card').text,/設定状態: 設定済み/);
assert.equal(host.children.some(item=>item.kind==='button'),false);

renderModelReadiness(snapshot(true,null),'planning');
assert.match(host.children.find(item=>item.kind==='card').text,/未設定または利用できません/);
assert.equal(host.children.filter(item=>item.kind==='button').length,1);
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


def test_connection_settings_keeps_unavailable_audio_routes_disabled_and_explained() -> None:
    for marker in (
        "const unavailable=item.selectable===false",
        "option.disabled=unavailable",
        "item.disabled_reasons||[]",
        "Installed/runtime/current:",
        "Availability: ${availability}",
        "modeLabel.htmlFor=mode.id",
        "routeLabel.htmlFor=route.id",
        "mode.setAttribute('aria-label',`${workloadLabel}の選択モード`)",
        "route.setAttribute('aria-label',`${workloadLabel}の優先AIモデル`)",
    ):
        assert marker in HTML


def test_ollama_runtime_uses_japanese_primary_status_and_keeps_codes_in_technical_details() -> None:
    for marker in (
        "function ollamaRuntimePresentation(state,reason)",
        "READY:'利用できます'",
        "NO_MODEL:'AIモデルが未導入です'",
        "STARTING:'準備しています'",
        "NOT_INSTALLED:'実行環境が未導入です'",
        "FAILED:'起動に失敗しました'",
        "OLLAMA_START_TIMEOUT",
        "起動待ちが時間切れになりました。",
        "technical.append(summary,codes)",
        "feedback.setAttribute('role','status')",
        "feedback.setAttribute('aria-live','polite')",
        "if(ollamaRuntimeRefreshInFlight)return",
        "refresh.setAttribute('aria-busy','true')",
        "const refreshed=await renderSettingsView('models')",
        "refreshed===true?'状態を更新しました。':'状態を確認できませんでした。時間をおいて再確認してください。'",
        "return form!==null&&(currentSettingsView!=='models'||runtime!==null)",
        "if(currentSettingsView==='models'&&!ollamaRuntimeRefreshInFlight)ollamaRuntimeRefreshMessage=''",
    ):
        assert marker in HTML
    assert "Ollama local runtime" not in HTML
    assert "状態理由: ${reason}" not in HTML

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the V6.1.1 behavioral contract")
    presentation = re.search(r"function ollamaRuntimePresentation\([^\r\n]+", HTML)
    renderer = re.search(r"function renderOllamaRuntimeStatus\([^\r\n]+", HTML)
    assert presentation is not None
    assert renderer is not None
    completed = subprocess.run(
        [
            node,
            "-e",
            f"""
const assert=require('node:assert/strict');
let ollamaRuntimeRefreshInFlight=false,ollamaRuntimeRefreshMessage='';
const currentById=new Map();
function $(id){{return currentById.get(id)||null}}
function element(tag,className,text){{return {{tag,className,textContent:String(text??''),children:[],attributes:{{}},disabled:false,type:null,listener:null,append(...items){{this.children.push(...items)}},setAttribute(name,value){{this.attributes[name]=String(value)}},removeAttribute(name){{delete this.attributes[name]}},addEventListener(name,handler){{assert.equal(name,'click');this.listener=handler}}}}}}
function card(title,text){{const value=element('div','card','');value.title=title;value.text=text;return value}}
let refreshCalls=0,releaseRefresh=null,refreshOutcome='success',refreshTargetState=null;
async function renderSettingsView(view){{
  assert.equal(view,'models');
  refreshCalls+=1;
  await new Promise(resolve=>{{releaseRefresh=resolve}});
  if(refreshOutcome==='throw')throw new Error('snapshot failed');
  if(refreshTargetState)installRuntime(refreshTargetState);
  return refreshOutcome!=='failure';
}}
{presentation.group(0)}
{renderer.group(0)}
function installRuntime(state){{
  currentById.clear();
  const host={{children:[],append(...items){{this.children.push(...items)}}}};
  renderOllamaRuntimeStatus(host,{{state,model_ids:state==='READY'?['qwen3:8b']:[],reason_code:state==='FAILED'?'OLLAMA_START_TIMEOUT':'INTERNAL_CODE',message_ja:'runtime port internal message'}});
  const runtimeCard=host.children[0],feedback=runtimeCard.children.find(item=>item.attributes.role==='status'),button=runtimeCard.children.find(item=>item.tag==='button');
  currentById.set('ollamaRuntimeRefreshStatus',feedback);
  if(button)currentById.set('ollamaRuntimeRefreshButton',button);
  return {{runtimeCard,feedback,button}};
}}
assert.equal(ollamaRuntimePresentation('READY',null).label,'利用できます');
assert.equal(ollamaRuntimePresentation('NO_MODEL','OLLAMA_MODEL_NOT_INSTALLED').label,'AIモデルが未導入です');
assert.equal(ollamaRuntimePresentation('STARTING',null).label,'準備しています');
assert.equal(ollamaRuntimePresentation('NOT_INSTALLED','OLLAMA_EXECUTABLE_NOT_FOUND').label,'実行環境が未導入です');
assert.equal(ollamaRuntimePresentation('FAILED','OLLAMA_START_EXITED').label,'起動に失敗しました');
assert.match(ollamaRuntimePresentation('FAILED','OLLAMA_START_TIMEOUT').message,/時間切れ/);
assert.equal(ollamaRuntimePresentation('UNKNOWN','UNKNOWN').label,'状態を確認できません');
const ready=installRuntime('READY');
assert.equal(ready.button,undefined);
assert.equal(ready.feedback.attributes['aria-live'],'polite');
for(const state of ['NO_MODEL','STARTING','NOT_INSTALLED','FAILED','UNAVAILABLE_CONFIGURATION']){{
  ollamaRuntimeRefreshInFlight=false;
  assert.ok(installRuntime(state).button);
}}
ollamaRuntimeRefreshInFlight=false;
let rendered=installRuntime('FAILED'),runtimeCard=rendered.runtimeCard,details=runtimeCard.children.find(item=>item.tag==='details'),feedback=rendered.feedback,button=rendered.button;
assert.doesNotMatch(runtimeCard.title,/FAILED|OLLAMA_START_TIMEOUT/);
assert.doesNotMatch(runtimeCard.text,/FAILED|OLLAMA_START_TIMEOUT|runtime port/);
assert.match(details.children.find(item=>item.tag==='div').textContent,/FAILED[^]*OLLAMA_START_TIMEOUT[^]*runtime port/);
assert.equal(feedback.attributes['aria-live'],'polite');
(async()=>{{
  const first=button.listener(),second=button.listener();
  assert.equal(refreshCalls,1);
  assert.equal(button.disabled,true);
  assert.equal(button.attributes['aria-busy'],'true');
  assert.equal(feedback.textContent,'状態を確認しています…');
  releaseRefresh();
  await Promise.all([first,second]);
  assert.equal(feedback.textContent,'状態を更新しました。');
  assert.equal(button.disabled,false);
  assert.equal(button.attributes['aria-busy'],undefined);

  rendered=installRuntime('FAILED');
  refreshOutcome='failure';refreshTargetState=null;
  const failed=rendered.button.listener();releaseRefresh();await failed;
  assert.equal(rendered.feedback.textContent,'状態を確認できませんでした。時間をおいて再確認してください。');
  assert.equal(rendered.button.disabled,false);

  rendered=installRuntime('FAILED');
  refreshOutcome='throw';
  const rejected=rendered.button.listener();releaseRefresh();await rejected;
  assert.equal(rendered.feedback.textContent,'状態を確認できませんでした。時間をおいて再確認してください。');

  rendered=installRuntime('STARTING');
  refreshOutcome='success';refreshTargetState='READY';
  const transitioned=rendered.button.listener();releaseRefresh();await transitioned;
  assert.equal(currentById.get('ollamaRuntimeRefreshStatus').textContent,'状態を更新しました。');
  assert.equal(currentById.has('ollamaRuntimeRefreshButton'),false);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
""",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"


def test_model_settings_readback_reports_actual_call_null_as_failure() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the V6.1.1 behavioral contract")
    call_function = re.search(r"async function call\([^\r\n]+", HTML)
    settings_renderer = re.search(r"async function renderSettingsView\([^\r\n]+", HTML)
    assert call_function is not None
    assert settings_renderer is not None
    completed = subprocess.run(
        [
            node,
            "-e",
            f"""
const assert=require('node:assert/strict');
let currentSettingsView='general',ollamaRuntimeRefreshInFlight=false,ollamaRuntimeRefreshMessage='old result';
const SETTINGS_VIEWS={{general:{{title:'一般',summary:'',boundary:''}},models:{{title:'AIモデル',summary:'',boundary:''}}}};
const nodes=new Map([
  ['settingsPaneTitle',{{textContent:''}}],
  ['settingsPaneSummary',{{textContent:''}}],
  ['settingsPaneBoundary',{{textContent:''}}],
  ['settingsContent',{{}}],
]);
const $=id=>nodes.get(id)||null,qa=()=>[];
let notified=0,connectionRender=null,runtimeRender=null;
function notify(){{notified+=1}}
function renderConnectionSettings(value){{connectionRender=value}}
function renderOllamaRuntimeStatus(_host,value){{runtimeRender=value}}
function renderModel(){{throw new Error('unexpected generic renderer')}}
async function refreshOwnerSigningKeyImport(){{throw new Error('unexpected secret renderer')}}
const window={{pywebview:{{api:{{
  connection_settings_snapshot:async()=>{{throw new Error('connection failed')}},
  ollama_runtime_snapshot:async()=>{{throw new Error('runtime failed')}},
}}}}}};
{call_function.group(0)}
{settings_renderer.group(0)}
(async()=>{{
  const result=await renderSettingsView('models');
  assert.equal(result,false);
  assert.equal(connectionRender,null);
  assert.equal(runtimeRender,null);
  assert.equal(notified,2);
  assert.equal(ollamaRuntimeRefreshMessage,'');
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
""",
        ],
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
        "call('choose_and_ingest_media',{})",
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
        "call(recovery?'recover_local_transcription':'run_local_transcription',{confirmation_id:prepared.confirmation_id})",
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
