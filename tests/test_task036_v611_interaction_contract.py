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
assert.equal(missing.state,'MODEL_SETTINGS_REQUIRED');
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
const ready=planningGenerationPresentation({{available:true,model_id:'qwen3:8b'}},{{selectionReady:true,computeReady:true,runtimeReady:true,runtimeState:'READY'}});
assert.equal(ready.ready,true);
assert.equal(ready.state,'READY');
assert.doesNotMatch(ready.message,/qwen3:8b/);
assert.equal(settingsModelLabel({{model_id:'qwen3:8b'}},1),'登録済みローカルAIモデル');
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
