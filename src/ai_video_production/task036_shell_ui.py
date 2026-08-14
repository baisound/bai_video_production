"""TASK-036 native desktop shell layout spike.

The spike deliberately exposes only a tiny allowlisted Python bridge.  It is not
wired to Product mutations; it proves window hosting, layout, focus and bridge
shape before the real workflow is connected.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_review import ReviewWorkspaceState, Task036ReviewFacade
from .desktop_shell import ShellApplicationService, WorkspaceId
from .desktop_shell_projection import DesktopEditingProjectionService, EditingProjection
from .task036_view_model import Task036DesktopViewModel
from .task036_native_dialog import Task036NativeDialogService
from .task036_pre_edit_runtime import Task036PreEditRuntime
from .task036_workflow_runtime import Task036WorkflowRuntime
from .errors import ProductError, ProductErrorCategory
from .production_control_application import Task037ProductionControlApplication
from .audit_application import Task038AuditApplication
from .planning_application import Task027PlanningApplication
from .generation_safety_application import Task013GenerationSafetyApplication
from .continuity_application import Task039ContinuityApplication
from .prompt_evidence_application import Task040PromptEvidenceApplication
from .generation_queue_application import Task027GenerationQueueApplication


HTML = r'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BAI Video Production</title>
<style>
:root{color-scheme:dark;--bg:#090b0e;--panel:#11151b;--panel2:#151a21;--line:#262d37;--text:#e7ebf2;--muted:#8c96a5;--accent:#4c83e7;--purple:#6d4acb;--audio:#21785e;--warn:#d28a34}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:13px/1.35 "Segoe UI","Noto Sans JP",sans-serif;overflow:hidden}button:focus-visible,a:focus-visible{outline:3px solid #ffcc4d;outline-offset:2px}.skip-link{position:fixed;left:8px;top:-60px;z-index:100;background:#fff;color:#000;padding:10px}.skip-link:focus{top:8px}
button,select{font:inherit;color:inherit}.app{height:100vh;display:grid;grid-template-rows:46px minmax(0,1fr) 300px;background:linear-gradient(180deg,#0c0f13,#080a0d)}
.top{display:flex;align-items:center;gap:8px;padding:0 14px;border-bottom:1px solid var(--line);background:#0c1015}.brand{font-weight:700}.project{color:#cdd3dd}.spacer{flex:1}.workspace{background:transparent;border:0;padding:9px 10px;border-bottom:2px solid transparent;cursor:pointer}.workspace.active{border-color:var(--accent);color:#fff}.action{background:#181d24;border:1px solid #303844;border-radius:6px;padding:7px 12px}.dialog-status{position:fixed;z-index:20;top:54px;right:16px;max-width:min(420px,calc(100vw - 32px));padding:7px 10px;border:1px solid #394553;border-radius:6px;background:#111820ee;color:#d7deea;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 5px 18px #0008}.main{min-height:0;display:grid;grid-template-columns:320px minmax(420px,1fr) 330px;gap:8px;padding:8px}.panel{min-width:0;min-height:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel-title{height:38px;display:flex;align-items:center;padding:0 12px;border-bottom:1px solid var(--line);font-weight:650}.tabs{display:flex;gap:4px;padding:8px;border-bottom:1px solid var(--line)}.tab{border:0;background:transparent;color:var(--muted);padding:7px 9px}.tab.active{background:#1a2535;color:#fff;border-radius:5px}.rows{height:calc(100% - 82px);overflow:auto}.row{display:grid;grid-template-columns:80px 1fr auto;gap:8px;padding:10px 12px;border-bottom:1px solid #1c222b}.row:hover{background:#171d25}.time{font-variant-numeric:tabular-nums;color:#aeb7c4}.status{font-size:11px;color:#8fb3ff}.viewer{display:grid;grid-template-rows:minmax(0,1fr) 54px;background:#07090b}.screen{margin:10px;background:radial-gradient(circle at 50% 20%,#354653 0,#1c2b32 25%,#0c1115 65%);border:1px solid #20262e;border-radius:6px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}.screen:before{content:"";position:absolute;inset:0;background:linear-gradient(140deg,transparent 0 42%,rgba(255,255,255,.06) 43% 44%,transparent 45% 100%)}.tc{position:absolute;bottom:18px;background:#050607cc;padding:6px 12px;border-radius:5px;font:28px/1 monospace}.controls{display:flex;align-items:center;gap:16px;padding:0 14px;border-top:1px solid var(--line);color:#c7ced8}.scrub{height:4px;background:#353c47;flex:1;border-radius:3px;overflow:hidden}.scrub i{display:block;width:31%;height:100%;background:var(--accent)}.inspector{padding:12px}.field{margin-bottom:14px}.field label{display:block;color:#aab3c0;margin-bottom:6px}.value{background:#0d1116;border:1px solid #2a313b;border-radius:6px;padding:9px}.hint{color:var(--muted);font-size:12px}.timeline{margin:0 8px 8px;display:grid;grid-template-columns:116px minmax(0,1fr);grid-template-rows:30px repeat(6,44px);border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#0e1217}.ruler{grid-column:2;border-bottom:1px solid var(--line);background:#12171d;position:relative}.ruler:after{content:"00:00        00:20        00:40        01:00        01:20";position:absolute;left:12px;right:10px;top:7px;color:#85909f;word-spacing:55px;font-size:10px}.track-name{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:13px 10px;color:#aeb7c4;background:#10151a}.track{border-bottom:1px solid var(--line);position:relative;overflow:hidden}.clip{position:absolute;top:5px;bottom:5px;border-radius:4px;padding:7px 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.video{left:1%;width:94%;background:#25303a;border:1px solid #3b4f63}.sub1{left:2%;width:17%;background:#54389a}.sub2{left:20%;width:16%;background:#5e3da8}.sub3{left:37%;width:23%;background:#6742b4}.audio{left:1%;width:94%;background:#165942}.se{left:8%;width:32%;background:#275b87}.narr{left:42%;width:44%;background:#9a5428}.cut{background:#6c2f35;border:1px solid #b45a64}.review-actions{display:flex;gap:8px;margin-top:12px}.review-actions button{flex:1}.review-actions button:disabled{opacity:.4;cursor:not-allowed}.selection{outline:2px solid #8fb3ff;outline-offset:-2px}.progress-note{margin-top:10px;color:#aab3c0}.approve{margin-top:12px;width:100%}.playhead{position:absolute;left:31%;top:0;bottom:0;width:2px;background:#e75f51;z-index:5}.timeline-wrap{position:relative;grid-column:1/-1;display:contents}@media(max-width:1320px){.top .action{padding-inline:8px}}@media(max-width:1150px){.main{grid-template-columns:250px minmax(360px,1fr) 270px}.app{grid-template-rows:46px minmax(0,1fr) 250px}}@media(max-width:900px){body{overflow:auto}.app{height:auto;min-height:100vh;grid-template-rows:auto auto auto}.top{flex-wrap:wrap;min-height:46px;padding-block:6px}.main{grid-template-columns:1fr}.panel{min-height:260px}.viewer{min-height:420px}.timeline{min-width:720px}}
.production-drawer{position:fixed;z-index:30;top:46px;right:0;bottom:0;width:min(620px,100vw);padding:14px;background:#0d1117f7;border-left:1px solid var(--line);box-shadow:-12px 0 30px #0009;overflow:auto}.production-drawer[hidden]{display:none}.production-heading{display:flex;align-items:center;gap:10px;margin-bottom:12px}.production-heading h2{margin:0;font-size:17px}.production-summary{color:var(--muted);margin:0 0 12px}.production-slot{border:1px solid var(--line);border-radius:8px;background:var(--panel);margin-bottom:10px;overflow:hidden}.production-slot-head{display:flex;justify-content:space-between;gap:8px;padding:10px 12px;background:var(--panel2)}.production-candidate{padding:10px 12px;border-top:1px solid var(--line)}.production-meta{color:var(--muted);font:11px/1.45 monospace;white-space:pre-wrap;overflow-wrap:anywhere}.production-lock{margin-top:8px}.production-empty{padding:18px;border:1px dashed #394553;border-radius:8px;color:var(--muted)}.audit-card{margin-top:9px;padding:9px;border-left:3px solid #587bb8;background:#0b1016}.audit-card.critical{border-left-color:#d35d5d}.audit-title{font-weight:650}.audit-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}.audit-actions button{font-size:12px}.audit-decision{margin-top:8px;color:#9fd0b5}.audit-recovery{padding:10px;margin-bottom:10px;border:1px solid #d28a34;background:#2a1d0e;color:#ffd49a}.audit-recovery button{margin:8px 6px 0 0}.planning-card{border:1px solid var(--line);border-radius:8px;background:var(--panel);margin-bottom:10px;padding:11px}.planning-scene{margin-top:8px;padding:10px;border-left:3px solid var(--purple);background:#0b1016}.planning-section{margin-top:8px;padding:9px;background:#121820}.planning-actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.planning-warning{color:#ffd49a}.planning-ok{color:#9fd0b5}@media(max-width:900px){.production-drawer{top:92px}}
</style></head>
<body><a class="skip-link" href="#transcriptRows">編集内容へ移動</a><div class="app">
<header class="top"><div class="brand">BAI Video Production</div><div class="project" id="projectName">プロジェクト未選択</div><button class="workspace active" data-w="EDIT">編集</button><button class="workspace" data-w="PLANNING">企画</button><button class="workspace" data-w="GENERATION_SAFETY">生成安全</button><button class="workspace" data-w="CONTINUITY">連続性</button><button class="workspace" data-w="PROMPT_EVIDENCE">Prompt証跡</button><button class="workspace" data-w="GENERATION_QUEUE">生成Queue</button><button class="workspace" data-w="SUBTITLE">字幕</button><button class="workspace" data-w="REVIEW">レビュー</button><button class="workspace" data-w="PRODUCTION_CONTROL">制作管理</button><button class="workspace" data-w="EXPORT">書き出し</button><div class="spacer"></div><span id="dialogStatus" class="dialog-status" role="status" aria-live="polite">選択操作なし</span><span id="job">待機中</span><button class="action" id="workflowActionButton" aria-label="次の編集工程を実行" disabled>Continue</button><button class="action" id="chooseProjectButton" aria-label="プロジェクトフォルダーを選択">プロジェクト</button><button class="action" id="chooseMediaButton" aria-label="メディアファイルを選択">メディア</button><button class="action" id="chooseHandoffButton" aria-label="EDITOR WORK保存先を選択">保存先</button></header>
<aside id="productionWorkspace" class="production-drawer" aria-label="制作管理" hidden><div class="production-heading"><h2>制作管理</h2><div class="spacer"></div><button class="action" id="closeProductionButton" aria-label="制作管理を閉じる">閉じる</button></div><p class="production-summary" id="productionSummary">制作管理データを読み込み中です。</p><div id="productionSlots"></div></aside>
<aside id="planningWorkspace" class="production-drawer" aria-label="企画" hidden><div class="production-heading"><h2>企画 / Scene Contract</h2><div class="spacer"></div><button class="action" id="closePlanningButton" aria-label="企画を閉じる">閉じる</button></div><p class="production-summary" id="planningSummary">企画データを読み込み中です。</p><div id="planningContent"></div></aside>
<aside id="generationSafetyWorkspace" class="production-drawer" aria-label="生成安全" hidden><div class="production-heading"><h2>生成安全 / Shot Feasibility</h2><div class="spacer"></div><button class="action" id="closeGenerationSafetyButton" aria-label="生成安全を閉じる">閉じる</button></div><p class="production-summary" id="generationSafetySummary">生成安全データを読み込み中です。</p><div id="generationSafetyContent"></div></aside>
<aside id="continuityWorkspace" class="production-drawer" aria-label="連続性" hidden><div class="production-heading"><h2>連続性 / Continuity Map</h2><div class="spacer"></div><button class="action" id="closeContinuityButton" aria-label="連続性を閉じる">閉じる</button></div><p class="production-summary" id="continuitySummary">連続性データを読み込み中です。</p><div id="continuityContent"></div></aside>
<aside id="promptEvidenceWorkspace" class="production-drawer" aria-label="Prompt証跡" hidden><div class="production-heading"><h2>Prompt証跡 / Generation Evidence</h2><div class="spacer"></div><button class="action" id="closePromptEvidenceButton" aria-label="Prompt証跡を閉じる">閉じる</button></div><p class="production-summary" id="promptEvidenceSummary">Prompt証跡を読み込み中です。</p><div id="promptEvidenceContent"></div></aside>
<aside id="generationQueueWorkspace" class="production-drawer" aria-label="生成Queue" hidden><div class="production-heading"><h2>生成Queue / Admission</h2><div class="spacer"></div><button class="action" id="closeGenerationQueueButton" aria-label="生成Queueを閉じる">閉じる</button></div><p class="production-summary" id="generationQueueSummary">Queue Evidenceを読み込み中です。</p><div id="generationQueueContent"></div></aside>
<section class="main">
<aside class="panel"><div class="panel-title">文字起こし / カット候補</div><div class="tabs"><button class="tab active">文字起こし</button><button class="tab">候補</button><button class="tab">検索</button></div><div class="rows" id="transcriptRows">
<div class="row"><div class="time">00:00:00</div><div>みなさん こんにちは バイサウンドです</div><div class="status">未確認</div></div>
<div class="row"><div class="time">00:00:04</div><div>今日もサバイバーでやっていきます</div><div class="status">未確認</div></div>
<div class="row"><div class="time">00:00:08</div><div>キラーは誰かな どんなパーク構成かな</div><div class="status">未確認</div></div>
<div class="row"><div class="time">00:00:14</div><div>さあ 試合が始まりました</div><div class="status">KEEP</div></div>
<div class="row"><div class="time">00:00:20</div><div>ここにありましたね 修理していきます</div><div class="status">CUT?</div></div>
</div></aside>
<main class="panel viewer"><div class="screen"><div class="tc">00:28:47:23</div></div><div class="controls"><span>◀</span><span>▶</span><span>▶|</span><div class="scrub"><i></i></div><span>100%</span></div></main>
<aside class="panel"><div class="panel-title">インスペクタ / AI</div><div class="inspector"><div class="field"><label>選択</label><div class="value" id="reviewSelection">カット候補を選択</div></div><div class="field"><label>AI提案</label><div class="value" id="reviewSuggestion">候補を選択すると理由を表示します</div><div class="hint">AI候補は承認済み編集ではありません。KEEP/CUTは明示的なHuman Decisionです。</div></div><div class="field"><label>影響</label><div class="value" id="reviewRange">—</div></div><div class="field"><label>状態</label><div class="value" id="reviewState">Human Review Required</div></div><div class="review-actions"><button class="action" id="keepButton" disabled>KEEP</button><button class="action" id="cutButton" disabled>CUT</button></div><div class="progress-note" id="reviewProgress">カット候補データ未接続</div><button class="action approve" id="approvePlanButton" disabled>編集プランを承認</button></div></aside>
</section>
<section class="timeline"><div></div><div class="ruler"></div><div class="track-name">V1　映像</div><div class="track" data-track="V1"><div class="clip video">Source Video</div></div><div class="track-name">S1　字幕</div><div class="track" data-track="S1"><div class="clip sub1">みなさん こんにちは…</div><div class="clip sub2">今日もサバイバー…</div><div class="clip sub3">キラーは誰かな…</div></div><div class="track-name">C1　カット候補</div><div class="track" data-track="CUT_OVERLAY"></div><div class="track-name">A1　音声</div><div class="track" data-track="A1"><div class="clip audio">Source Audio</div></div><div class="track-name">A2　SE</div><div class="track" data-track="A2"><div class="clip se">SE candidates</div></div><div class="track-name">A3　ナレーション</div><div class="track" data-track="A3"><div class="clip narr">Narration</div></div><div class="playhead"></div></section>
</div>
<script>
async function call(name,args){if(!window.pywebview?.api) return null; try{return await window.pywebview.api[name](args||{})}catch(e){console.error(e);return null}}
function renderRows(vm){const host=document.querySelector('#transcriptRows');if(!host||!vm?.transcript_rows?.length)return;host.replaceChildren();for(const item of vm.transcript_rows){const row=document.createElement('div');row.className='row';const time=document.createElement('div');time.className='time';time.textContent=item.start_label;const text=document.createElement('div');text.textContent=item.text;const status=document.createElement('div');status.className='status';status.textContent=item.review_state;row.append(time,text,status);host.append(row)}}
function renderTimeline(vm){if(!vm?.timeline_tracks)return;for(const [track,blocks] of Object.entries(vm.timeline_tracks)){const host=document.querySelector(`[data-track="${CSS.escape(track)}"]`);if(!host)continue;host.replaceChildren();for(const item of blocks){const clip=document.createElement('div');clip.className='clip '+(item.block_type==='SUBTITLE'?'sub1':item.block_type.includes('CUT')?'cut':'video');clip.style.left=item.left_percent+'%';clip.style.width=Math.max(item.width_percent,.4)+'%';clip.textContent=item.label;clip.title=`${item.start_label} – ${item.end_label} | ${item.state}`;if(item.block_type==='CUT_CANDIDATE'&&item.source_ids?.length){clip.dataset.candidate=item.source_ids[0];clip.addEventListener('click',async()=>{await call('select_candidate',{candidate_id:clip.dataset.candidate});await refresh()})}host.append(clip)}}}
function renderReview(review){const keep=document.querySelector('#keepButton'),cut=document.querySelector('#cutButton'),approve=document.querySelector('#approvePlanButton');if(!review?.available){keep.disabled=cut.disabled=approve.disabled=true;document.querySelector('#reviewProgress').textContent='カット候補データ未接続';return}const selected=review.candidates?.find(x=>x.selected);document.querySelector('#reviewSelection').textContent=selected?selected.candidate_id:'カット候補を選択';document.querySelector('#reviewSuggestion').textContent=selected?`${selected.kind} / 強度 ${selected.strength_score}`:'候補を選択すると理由を表示します';document.querySelector('#reviewRange').textContent=selected?`${selected.start_us} – ${selected.end_us} μs`:'—';document.querySelector('#reviewState').textContent=selected?selected.review_state:'Human Review Required';document.querySelector('#reviewProgress').textContent=`確認済み ${review.reviewed_count} / ${review.candidates.length}　未確認 ${review.unresolved_count}`;keep.disabled=cut.disabled=!selected;approve.disabled=review.unresolved_count!==0||!!review.approved_plan;document.querySelectorAll('[data-candidate]').forEach(el=>el.classList.toggle('selection',selected&&el.dataset.candidate===selected.candidate_id))}
function renderProduction(model,audit){const drawer=document.querySelector('#productionWorkspace'),host=document.querySelector('#productionSlots'),summary=document.querySelector('#productionSummary');host.replaceChildren();if(!model?.available){summary.textContent='このプロジェクトには制作管理が接続されていません。';drawer.hidden=false;return}summary.textContent=`Slot ${model.slot_count} / Candidate ${model.candidate_count} / LOCK ${model.locked_slot_count} / STALE ${model.stale_slot_count}`;if(audit?.recovery?.required){const warning=document.createElement('section');warning.className='audit-recovery';const text=document.createElement('div');text.textContent=`保存中断を検出: ${audit.recovery.state} / ${audit.recovery.candidate_id} / ${audit.recovery.decision}`;warning.append(text);for(const actionName of audit.recovery.available_actions||[]){const button=document.createElement('button');button.className='action';button.textContent=actionName==='COMPLETE'?'同じ判断の保存を完了':actionName==='ABANDON'?'未適用として中止':'完了状態を確定';button.addEventListener('click',async()=>{if(window.confirm(`${button.textContent}しますか？\n別の判断への変更は行いません。`)){await call('audit_apply_recovery',{action:actionName});await refresh()}});warning.append(button)}host.append(warning)}if(!model.slots?.length){const empty=document.createElement('div');empty.className='production-empty';empty.textContent='承認済みPlanから作られたAsset Slotはまだありません。';host.append(empty);drawer.hidden=false;return}const auditRows=new Map((audit?.workspace?.candidates||[]).map(item=>[item.candidate_id,item]));for(const slot of model.slots){const card=document.createElement('section');card.className='production-slot';const head=document.createElement('div');head.className='production-slot-head';const title=document.createElement('strong');title.textContent=`${slot.scene_id} / ${slot.slot_kind}`;const state=document.createElement('span');state.textContent=slot.status;head.append(title,state);card.append(head);for(const candidate of slot.candidates||[]){const review=auditRows.get(candidate.candidate_id);const row=document.createElement('div');row.className='production-candidate';const name=document.createElement('strong');name.textContent=`${candidate.candidate_id} · ${candidate.lifecycle_state}`;const meta=document.createElement('div');meta.className='production-meta';meta.textContent=`Asset: ${candidate.asset_id}\nSHA-256: ${candidate.asset_sha256}`;row.append(name,meta);for(const record of review?.audit_history||[]){const auditCard=document.createElement('div');auditCard.className='audit-card'+(record.critical_violation?' critical':'');const auditTitle=document.createElement('div');auditTitle.className='audit-title';auditTitle.textContent=`監査 ${record.audit_id} · ${record.auditor_kind} / ${record.auditor_id}${record.auditor_version?' '+record.auditor_version:''}`;const auditMeta=document.createElement('div');auditMeta.className='production-meta';const findings=(record.findings||[]).map(x=>`${x.severity}: ${x.code} — ${x.summary}`).join('\n')||'指摘なし';const scores=Object.entries(record.dimension_scores||{}).map(([key,value])=>`${key} ${value}`).join(' / ')||'採点なし';auditMeta.textContent=`Score: ${scores}\nFindings: ${findings}\nFailure: ${(record.failure_codes||[]).join(', ')||'なし'}\nAlternate: ${(record.alternate_use_proposals||[]).join(' / ')||'なし'}`;auditCard.append(auditTitle,auditMeta);row.append(auditCard)}if(review?.human_decision_record){const decision=document.createElement('div');decision.className='audit-decision';decision.textContent=`Human Decision: ${review.human_decision_record.decision} / ${review.human_decision_record.actor_id}`;row.append(decision)}if(review?.available_human_actions?.length){const actions=document.createElement('div');actions.className='audit-actions';for(const decisionName of review.available_human_actions){const button=document.createElement('button');button.className='action';button.textContent=decisionName;button.addEventListener('click',async()=>{const actor=window.prompt('判断者IDを入力してください（必須）','desktop-owner');if(actor===null||!actor.trim())return;const notes=window.prompt('判断メモ（任意）','');if(notes===null)return;const prepared=await call('audit_prepare_human_decision',{candidate_id:candidate.candidate_id,decision:decisionName,expected_production_snapshot_sha256:audit.production_snapshot_sha256,expected_audit_snapshot_sha256:audit.audit_snapshot_sha256});if(!prepared)return;const ok=window.confirm(`このHuman Decisionを保存しますか？\nCandidate: ${prepared.candidate_id}\nAsset SHA-256: ${prepared.asset_sha256}\nAudit: ${prepared.audit_refs.join(', ')}\nCritical: ${prepared.critical_violation_present?'あり':'なし'}\nDecision: ${prepared.decision}\n\nLOCKは別操作です。`);if(ok){await call('audit_apply_human_decision',{confirmation_id:prepared.confirmation_id,actor_id:actor.trim(),notes:notes||null});await refresh()}});actions.append(button)}row.append(actions)}if(candidate.available_actions?.includes('PREPARE_LOCK')){const button=document.createElement('button');button.className='action production-lock';button.textContent='この候補をLOCK';button.addEventListener('click',async()=>{const prepared=await call('production_prepare_lock',{slot_id:slot.slot_id,candidate_id:candidate.candidate_id,expected_snapshot_sha256:model.snapshot_sha256});if(!prepared)return;const ok=window.confirm(`この候補をLOCKしますか？\nSlot: ${prepared.slot_id}\nCandidate: ${prepared.candidate_id}\nAsset: ${prepared.asset_id}\nSHA-256: ${prepared.asset_sha256}`);if(ok){await call('production_apply_lock',{confirmation_id:prepared.confirmation_id});await refresh()}});row.append(button)}card.append(row)}host.append(card)}drawer.hidden=false}
function renderPlanning(model){const drawer=document.querySelector('#planningWorkspace'),host=document.querySelector('#planningContent'),summary=document.querySelector('#planningSummary');host.replaceChildren();if(!model?.available){summary.textContent='このプロジェクトには企画Applicationが接続されていません。';drawer.hidden=false;return}if(!model.workspace){summary.textContent='production-proposal.json にProposalがありません。';const empty=document.createElement('div');empty.className='production-empty';empty.textContent='このminimumは既存の永続Proposalをレビューします。AI Proposal生成は実行しません。';host.append(empty);drawer.hidden=false;return}const w=model.workspace,bp=w.blueprint,intent=w.creation_intent;summary.textContent=`${model.selected_proposal_id} revision ${w.latest_revision} / ${w.go_status} / Slot投入 ${model.installation.status}`;const intentCard=document.createElement('section');intentCard.className='planning-card';const intentTitle=document.createElement('strong');intentTitle.textContent=`Intent: ${intent.purpose}`;const intentMeta=document.createElement('div');intentMeta.className='production-meta';intentMeta.textContent=`Audience: ${intent.audience}\nPlatform: ${intent.platform} / ${intent.aspect_ratio}\nDuration: ${intent.target_duration_seconds}s\nTone: ${intent.style_tone}\nMessage: ${intent.story_message}\nBudget: ${intent.budget_ceiling??'未設定'} ${intent.currency}`;intentCard.append(intentTitle,intentMeta);host.append(intentCard);const proposalCard=document.createElement('section');proposalCard.className='planning-card';const proposalTitle=document.createElement('strong');proposalTitle.textContent=`Proposal / ${w.go_status}`;proposalCard.append(proposalTitle);for(const section of w.sections||[]){const item=document.createElement('div');item.className='planning-section';const title=document.createElement('strong');title.textContent=`${section.title}${w.changed_section_ids_from_previous?.includes(section.section_id)?'（前版から変更）':''}`;const body=document.createElement('div');body.textContent=section.body;item.append(title,body);proposalCard.append(item)}const policy=document.createElement('div');policy.className='production-meta';policy.textContent=`Policy: ${w.provider_policy.policy_id} / ${w.provider_policy.policy_version}\nCost estimate: ${w.estimated_cost_range.min}–${w.estimated_cost_range.max} ${w.estimated_cost_range.currency}\nRights: ${(w.rights_warnings||[]).join(' / ')||'警告なし'}`;proposalCard.append(policy);host.append(proposalCard);const scenes=document.createElement('section');scenes.className='planning-card';const sceneTitle=document.createElement('strong');sceneTitle.textContent=`Scene Contract: ${bp.title} / ${bp.timeline_rate.numerator}/${bp.timeline_rate.denominator} fps / ${bp.target_duration_frames} frames`;scenes.append(sceneTitle);for(const scene of bp.scenes||[]){const card=document.createElement('div');card.className='planning-scene';const title=document.createElement('strong');title.textContent=`${scene.scene_id} · ${scene.narrative_role}`;const meta=document.createElement('div');meta.className='production-meta';meta.textContent=`Frames: ${scene.range_frames.start}–${scene.range_frames.end_exclusive}\nSource: ${scene.source_strategy} / Risk: ${scene.generation_risk}\nCamera: ${scene.camera_motion}\nReferences: ${(scene.reference_ids||[]).join(', ')||'なし'}\nAudio: Narration ${scene.audio.narration?'yes':'no'} / BGM ${scene.audio.bgm?'yes':'no'} / SE ${(scene.audio.sound_effects||[]).join(', ')||'なし'}`;card.append(title,meta);scenes.append(card)}host.append(scenes);const actions=document.createElement('div');actions.className='planning-actions';if(w.go_status==='GO_REQUIRED'){const go=document.createElement('button');go.className='action';go.textContent='このProposalをGO承認';go.addEventListener('click',async()=>{const bindings=[];for(const ref of bp.references||[]){if(ref.status==='PLANNED')continue;const assetId=window.prompt(`${ref.reference_id} のAsset ID（必須）`,'');if(assetId===null||!assetId.trim())return;const assetSha=window.prompt(`${ref.reference_id} のAsset SHA-256（必須）`,'sha256:');if(assetSha===null||!assetSha.trim())return;bindings.push({reference_id:ref.reference_id,asset_id:assetId.trim(),asset_sha256:assetSha.trim()})}const ceiling=window.prompt(`Cost ceiling (${w.estimated_cost_range.currency})`,String(w.estimated_cost_range.max));if(ceiling===null||!ceiling.trim())return;const rights=(w.rights_warnings||[]).length?window.confirm(`Rights警告を確認しましたか？\n${w.rights_warnings.join('\n')}`):false;const actor=window.prompt('GO承認者ID（必須）','desktop-owner');if(actor===null||!actor.trim())return;const prepared=await call('planning_prepare_go',{proposal_id:w.proposal_id,proposal_revision:w.latest_revision,reference_bindings:bindings,cost_ceiling:ceiling.trim(),rights_warnings_acknowledged:rights,expected_snapshot_sha256:model.snapshot_sha256});if(!prepared)return;const ok=window.confirm(`Human GOを保存しますか？\nProposal: ${prepared.proposal_id} rev ${prepared.proposal_revision}\nCost ceiling: ${prepared.cost_ceiling} ${prepared.currency}\nReferences: ${prepared.reference_bindings.length}\n\nProvider/課金/Resolveは開始しません。`);if(ok){await call('planning_approve_go',{confirmation_id:prepared.confirmation_id,approved_by:actor.trim()});await refresh()}});actions.append(go)}if(w.go_status==='APPROVED'&&model.installation.status==='NOT_INSTALLED'){const install=document.createElement('button');install.className='action';install.textContent='承認PlanからAsset Slotを作成';install.addEventListener('click',async()=>{const plan=w.approved_plan;const prepared=await call('planning_prepare_install_plan',{plan_id:plan.plan_id,expected_proposal_snapshot_sha256:model.snapshot_sha256,expected_production_snapshot_sha256:model.installation.production.snapshot_sha256});if(!prepared)return;const ok=window.confirm(`承認Planを制作管理へ投入しますか？\nPlan: ${prepared.plan_id}\nBlueprint: ${prepared.blueprint_id}\nScenes: ${prepared.scene_count}\n\n生成・課金・Resolve操作は開始しません。`);if(ok){await call('planning_apply_install_plan',{confirmation_id:prepared.confirmation_id});await refresh()}});actions.append(install)}host.append(actions);const boundary=document.createElement('div');boundary.className='production-meta '+(w.go_status==='APPROVED'?'planning-ok':'planning-warning');boundary.textContent=`Provider: 未開始 / Paid: 未許可 / Budget reservation: なし / Resolve: 未変更 / Publish: 未開始`;host.append(boundary);drawer.hidden=false}
const generationCheckLabels={subject_position_exists:'人物の立ち位置が成立する',orientation_camera_compatible:'人物の向きとカメラが両立する',required_visible_coexists:'必要な物を同時に映せる',prohibited_change_not_required:'禁止した家具変更が不要',shot_reference_matches_final_camera:'ショット参照と最終カメラが一致する',task_axis_valid:'作業の向きが正しい',depth_order_valid:'前後関係が正しい',occlusion_valid:'必要な物が隠れない',furniture_integrity_valid:'家具の形と配置を保てる',room_anchor_integrity_valid:'窓・扉など部屋の基準を保てる',production_gear_absent:'撮影機材が映り込まない',character_identity_valid:'人物Identityを保てる'};
function promptText(label,initial=''){const value=window.prompt(label,initial);return value===null?null:value.trim()}
function csv(value){return value?value.split(',').map(x=>x.trim()).filter(Boolean):[]}
async function reviewGenerationScene(model,row){const scene=row.scene,characterRequired=window.confirm('このSceneには人物が必要ですか？');const characterProfile=promptText('Character Identity Profile ID（不要なら空欄）',characterRequired?'CHAR-':'');if(characterProfile===null)return;const characterRefs=promptText('Character参照Asset ID（カンマ区切り・不要なら空欄）','');if(characterRefs===null)return;const roomMaster=promptText('Room Master Asset ID（不要なら空欄）','');if(roomMaster===null)return;const shotRef=promptText('Scene Shot Reference Asset ID（人物を部屋に配置する場合は必須）','');if(shotRef===null)return;const styleRef=promptText('Style Reference Asset ID（任意）','');if(styleRef===null)return;const required=promptText('同時に映す必要がある物（コードをカンマ区切り）','FACE,MONITOR');if(required===null||!csv(required).length)return;const orientation=promptText('人物の向き','THREE_QUARTER_FRONT_TO_CAMERA');if(!orientation)return;const camera=promptText('最終カメラ位置','DESK_FRONT_LEFT');if(!camera)return;const prohibited=promptText('禁止する変更（カンマ区切り）','ADD_DESK,MOVE_FURNITURE');if(prohibited===null)return;const continuity=promptText('Continuity: CUT / DIRECT_CONTINUATION / MATCH_CUT / GRAPHIC_TRANSITION','CUT');if(!['CUT','DIRECT_CONTINUATION','MATCH_CUT','GRAPHIC_TRANSITION'].includes(continuity))return;const startSource=continuity==='DIRECT_CONTINUATION'?'PREV_END':promptText('Start source: NEW / PREV_END','NEW');if(!['NEW','PREV_END'].includes(startSource))return;let previousId=null,previousSha=null,startId=null,startSha=null;if(startSource==='PREV_END'){previousId=promptText('前Scene End Asset ID','');previousSha=promptText('前Scene End SHA-256','sha256:');startId=promptText('このScene Start Asset ID（同じID）',previousId||'');startSha=promptText('このScene Start SHA-256（同じSHA）',previousSha||'');if(!previousId||!previousSha||!startId||!startSha)return}const checks={};for(const [name,label] of Object.entries(generationCheckLabels)){const value=promptText(`${label}: PASS または FAIL`,'PASS');if(!['PASS','FAIL'].includes(value))return;checks[name]=value}const reasonsText=promptText('Blocking Reasonコード（なければ空欄、複数はカンマ区切り）','');if(reasonsText===null)return;const reviewer=promptText('確認者ID','desktop-owner');if(!reviewer)return;const spec={scene_id:scene.scene_id,continuity_type:continuity,character_required:characterRequired,character_identity_profile_id:characterProfile||null,character_reference_asset_ids:csv(characterRefs),room_master_asset_id:roomMaster||null,room_shot_reference_asset_id:shotRef||null,style_reference_asset_id:styleRef||null,required_visible:csv(required),subject_orientation:orientation,camera_semantic:camera,start_frame_source:startSource,previous_end_asset_id:previousId,previous_end_sha256:previousSha,start_asset_id:startId,start_asset_sha256:startSha,prohibited_changes:csv(prohibited)};const prepared=await call('generation_safety_prepare_review',{spec,human_reviewed_checks:checks,blocking_reasons:csv(reasonsText),expected_planning_snapshot_sha256:model.planning_snapshot_sha256,expected_safety_snapshot_sha256:model.safety_snapshot_sha256});if(!prepared)return;const ok=window.confirm(`構造チェックを保存しますか？\nScene: ${prepared.scene_id}\nResult: ${prepared.assessment.status}\n\nProvider・課金・Candidate生成は開始しません。`);if(ok){await call('generation_safety_apply_review',{confirmation_id:prepared.confirmation_id,reviewed_by:reviewer});await refresh()}}
function renderGenerationSafety(model){const drawer=document.querySelector('#generationSafetyWorkspace'),host=document.querySelector('#generationSafetyContent'),summary=document.querySelector('#generationSafetySummary');host.replaceChildren();if(!model?.available){summary.textContent='このプロジェクトには生成安全Applicationが接続されていません。';drawer.hidden=false;return}if(model.plan_status!=='APPROVED'){summary.textContent='先に企画でHuman GOを完了してください。';const empty=document.createElement('div');empty.className='production-empty';empty.textContent='Shot Feasibilityは現在のHuman-approved Planにだけ記録できます。';host.append(empty);drawer.hidden=false;return}summary.textContent=`Plan ${model.plan.plan_id} / 全Scene PASS: ${model.all_current_feasibility_pass?'はい':'いいえ'}`;for(const row of model.scenes||[]){const card=document.createElement('section');card.className='planning-card';const title=document.createElement('strong');title.textContent=`${row.scene.scene_id} · ${row.scene.narrative_role} · ${row.feasibility_status}`;const meta=document.createElement('div');meta.className='production-meta';const a=row.current_record?.assessment;meta.textContent=`判定: ${row.feasibility_status}\n古い記録: ${row.stale_record_count}\nBlocking: ${(a?.blocking_reasons||[]).join(', ')||'なし'}\nAssessment: ${a?.assessment_sha256||'未記録'}`;const button=document.createElement('button');button.className='action';button.textContent=row.current_record?'構造チェックを再確認':'構造チェックを記録';button.addEventListener('click',()=>reviewGenerationScene(model,row));card.append(title,meta,button);host.append(card)}const boundary=document.createElement('div');boundary.className='production-meta planning-warning';boundary.textContent='この画面はFEASIBILITYだけを記録します。Provider・課金・Candidate生成・Human ACCEPT・Resolve/Cubase操作は開始しません。生成後のVisual Complianceと最終判断は制作管理 / TASK-038で行います。';host.append(boundary);drawer.hidden=false}
async function prepareContinuityEdge(model){const edgeId=promptText('Continuity Edge ID','edge-');if(!edgeId)return;const fromSlot=promptText('前Scene END_FRAME Slot ID','slot:');if(!fromSlot)return;const toSlot=promptText('次Scene START_FRAME Slot ID','slot:');if(!toSlot)return;const boundary=promptText('DIRECT_CONTINUATION / SOFT_CONTINUITY / DISCONTINUOUS','DIRECT_CONTINUATION');if(!['DIRECT_CONTINUATION','SOFT_CONTINUITY','DISCONTINUOUS'].includes(boundary))return;const chars=promptText('Character Contract refs（カンマ区切り・任意）','');if(chars===null)return;const spaces=promptText('Space Contract refs（カンマ区切り・任意）','');if(spaces===null)return;const prepared=await call('continuity_prepare_edge',{edge_id:edgeId,from_slot_id:fromSlot,to_slot_id:toSlot,boundary_type:boundary,character_contract_refs:csv(chars),space_contract_refs:csv(spaces),expected_production_snapshot_sha256:model.production_snapshot_sha256,expected_continuity_snapshot_sha256:model.continuity_snapshot_sha256});if(!prepared)return;const ok=window.confirm(`連続性Edgeを登録しますか？\n${prepared.edge.from_scene_id} -> ${prepared.edge.to_scene_id}\n${prepared.edge.boundary_type}\n\n再生成・削除は行いません。`);if(ok){await call('continuity_apply_edge',{confirmation_id:prepared.confirmation_id});await refresh()}}
function renderContinuity(model){const drawer=document.querySelector('#continuityWorkspace'),host=document.querySelector('#continuityContent'),summary=document.querySelector('#continuitySummary');host.replaceChildren();if(!model?.available){summary.textContent='このプロジェクトにはContinuity Applicationが接続されていません。';drawer.hidden=false;return}summary.textContent=`Edges: ${model.workspace.edges.length} / Recovery: ${model.recovery.required?model.recovery.state:'NONE'}`;if(model.recovery.required){const box=document.createElement('div');box.className='audit-recovery';box.textContent=`中断したEdge登録: ${model.recovery.edge_id} / ${model.recovery.state}`;for(const action of model.recovery.available_actions||[]){const button=document.createElement('button');button.className='action';button.textContent=action;button.addEventListener('click',async()=>{if(window.confirm(`${action}で復旧しますか？`)){await call('continuity_apply_recovery',{action});await refresh()}});box.append(button)}host.append(box)}else{const add=document.createElement('button');add.className='action';add.textContent='End → Start 連続性を登録';add.addEventListener('click',()=>prepareContinuityEdge(model));host.append(add)}for(const row of model.workspace.edges||[]){const card=document.createElement('section');card.className='planning-card';const title=document.createElement('strong');title.textContent=`${row.edge_id} · ${row.from_scene_id} → ${row.to_scene_id}`;const meta=document.createElement('div');meta.className='production-meta';meta.textContent=`Type: ${row.boundary_type}\nSource: ${row.from_candidate_id} / ${row.from_asset_sha256}\nTarget Slot: ${row.to_slot_id} / ${row.target_slot_status}\nResolution: ${row.resolution?.status||'未検査'}\nGeneration safe: ${row.generation_safe?'YES':'NO'}\nHuman override for DIRECT: NO`;card.append(title,meta);if(!model.recovery.required&&!row.resolution){const inspect=document.createElement('button');inspect.className='action';inspect.textContent='現在のLOCK済みStartを検査';inspect.addEventListener('click',async()=>{if(window.confirm('現在のLOCK済みStart Assetを検査しますか？')){await call('continuity_inspect',{edge_id:row.edge_id,expected_production_snapshot_sha256:model.production_snapshot_sha256,expected_continuity_snapshot_sha256:model.continuity_snapshot_sha256});await refresh()}});card.append(inspect)}if(!model.recovery.required&&row.human_soft_approval_available){const soft=document.createElement('button');soft.className='action';soft.textContent='Soft ContinuityをHuman承認';soft.addEventListener('click',async()=>{const actor=promptText('承認者ID','desktop-owner');if(!actor)return;const prepared=await call('continuity_prepare_soft_approval',{edge_id:row.edge_id,expected_production_snapshot_sha256:model.production_snapshot_sha256,expected_continuity_snapshot_sha256:model.continuity_snapshot_sha256});if(prepared&&window.confirm('このSoft Continuityを承認しますか？')){await call('continuity_apply_soft_approval',{confirmation_id:prepared.confirmation_id,approved_by:actor});await refresh()}});card.append(soft)}if(!model.recovery.required&&row.target_slot_status==='LOCKED'){const stale=document.createElement('button');stale.className='action';stale.textContent='上流変更をSTALE伝播';stale.addEventListener('click',async()=>{if(window.confirm('上流Endと下流依存をSTALEにしますか？\n自動再生成は行いません。')){await call('continuity_propagate_stale',{root_slot_id:row.from_slot_id,expected_production_snapshot_sha256:model.production_snapshot_sha256,expected_continuity_snapshot_sha256:model.continuity_snapshot_sha256});await refresh()}});card.append(stale)}host.append(card)}const boundary=document.createElement('div');boundary.className='production-meta planning-warning';boundary.textContent='DIRECT_CONTINUATIONは完全一致のみ。Humanは上書きできません。STALEは過去の判断やAssetを削除せず、自動再生成も開始しません。';host.append(boundary);drawer.hidden=false}
async function preparePromptEvidencePrompt(model){const promptId=promptText('Prompt ID','prompt-');if(!promptId)return;const version=Number(promptText('Prompt version','1'));if(!Number.isInteger(version)||version<1)return;const purpose=promptText('目的','scene frame');if(!purpose)return;const sceneId=promptText('Scene ID','SC01');if(!sceneId)return;const slotId=promptText('Production Slot ID','slot:');if(!slotId)return;const bodyRef=promptText('private body ref','project-private://prompts/');if(!bodyRef)return;const bodySha=promptText('Prompt body SHA-256','sha256:');if(!bodySha)return;const profileId=promptText('Provider Profile ID','profile-1');if(!profileId)return;const profileVersion=promptText('Provider Profile version','v1');if(!profileVersion)return;const inputs=promptText('Input Asset SHA-256（カンマ区切り）','');if(inputs===null)return;const keeps=promptText('Keep Conditions（カンマ区切り）','keep-character');if(!keeps||!csv(keeps).length)return;const prepared=await call('prompt_evidence_prepare_prompt',{prompt_id:promptId,prompt_version:version,purpose,scene_id:sceneId,slot_id:slotId,body_ref:bodyRef,body_sha256:bodySha,provider_profile_id:profileId,provider_profile_version:profileVersion,input_asset_hashes:csv(inputs),keep_conditions:csv(keeps),expected_prompt_snapshot_sha256:model.prompt_snapshot_sha256,expected_production_snapshot_sha256:model.production_snapshot_sha256});if(prepared&&window.confirm('Promptメタデータを登録しますか？\n本文は保存せず、Providerも実行しません。')){await call('prompt_evidence_apply_prompt',{confirmation_id:prepared.confirmation_id});await refresh()}}
async function preparePromptEvidenceAttempt(model){const job=promptText('Generation Job ID（既に終了した実行のEvidence）','job-');if(!job)return;const slot=promptText('Slot ID','slot:');if(!slot)return;const promptId=promptText('Prompt ID','prompt-');if(!promptId)return;const version=Number(promptText('Prompt version','1'));if(!Number.isInteger(version)||version<1)return;const provider=promptText('Provider ID','provider-1');if(!provider)return;const modelId=promptText('Model ID','model-1');if(!modelId)return;const strategy=Number(promptText('Strategy level 0..6','0'));if(!Number.isInteger(strategy)||strategy<0||strategy>6)return;const result=promptText('Result: PASS / FAIL / CANCELLED / HUMAN_REQUIRED','FAIL');if(!['PASS','FAIL','CANCELLED','HUMAN_REQUIRED'].includes(result))return;const failures=promptText('Failure Codes（カンマ区切り）','');if(failures===null)return;const output=promptText('Output Candidate ID（PASSのみ必須）',result==='PASS'?'candidate-':'');if(output===null||((result==='PASS')!==!!output))return;const parent=promptText('Parent Attempt ID（任意）','');if(parent===null)return;const costText=promptText('記録済みCost（不明なら空欄）','');if(costText===null)return;const latencyText=promptText('Latency ms（不明なら空欄）','');if(latencyText===null)return;const cost=costText===''?null:Number(costText),latency=latencyText===''?null:Number(latencyText);if((cost!==null&&(!Number.isFinite(cost)||cost<0))||(latency!==null&&(!Number.isInteger(latency)||latency<0)))return;const prepared=await call('prompt_evidence_prepare_attempt',{generation_job_id:job,slot_id:slot,prompt_id:promptId,prompt_version:version,provider_id:provider,model_id:modelId,strategy_level:strategy,result,failure_codes:csv(failures),output_candidate_id:output||null,parent_attempt_id:parent||null,cost,latency_ms:latency,expected_prompt_snapshot_sha256:model.prompt_snapshot_sha256,expected_production_snapshot_sha256:model.production_snapshot_sha256});if(prepared&&window.confirm('終了済みGeneration Evidenceを取り込みますか？\nProvider実行・課金・Candidate作成は行いません。')){await call('prompt_evidence_apply_attempt',{confirmation_id:prepared.confirmation_id});await refresh()}}
async function preparePromptRegeneration(model,candidateId){const bodySha=promptText('次版Prompt body SHA-256','sha256:');if(!bodySha)return;const bodyRef=promptText('次版private body ref','project-private://prompts/');if(!bodyRef)return;const profileId=promptText('Provider Profile ID変更（継承は空欄）','');if(profileId===null)return;const profileVersion=profileId?promptText('新Provider Profile version',''):'';if(profileId&&!profileVersion)return;const prepared=await call('prompt_evidence_prepare_regeneration',{candidate_id:candidateId,new_body_sha256:bodySha,new_body_ref:bodyRef,provider_profile_id:profileId||null,provider_profile_version:profileVersion||null,input_asset_hashes:null,keep_conditions:null,repeated_failure_threshold:2,expected_prompt_snapshot_sha256:model.prompt_snapshot_sha256,expected_production_snapshot_sha256:model.production_snapshot_sha256,expected_audit_snapshot_sha256:model.audit_snapshot_sha256});if(prepared&&window.confirm(`Human NEEDS_REGENERATIONから次版Promptを登録しますか？\nStrategy: ${prepared.plan.next_strategy}\nProviderは実行しません。`)){await call('prompt_evidence_apply_regeneration',{confirmation_id:prepared.confirmation_id});await refresh()}}
function renderPromptEvidence(model){const drawer=document.querySelector('#promptEvidenceWorkspace'),host=document.querySelector('#promptEvidenceContent'),summary=document.querySelector('#promptEvidenceSummary');host.replaceChildren();if(!model?.available){summary.textContent='このプロジェクトにはPrompt Evidence Applicationが接続されていません。';drawer.hidden=false;return}summary.textContent=`Prompt ${model.prompt_count} / Attempt ${model.attempt_count} / Recovery ${model.recovery.required?model.recovery.state:'NONE'}`;if(model.recovery.required){const box=document.createElement('div');box.className='audit-recovery';box.textContent=`中断したEvidence登録: ${model.recovery.generation_job_id} / ${model.recovery.state}`;for(const action of model.recovery.available_actions||[]){const button=document.createElement('button');button.className='action';button.textContent=action;button.addEventListener('click',async()=>{if(window.confirm(`${action}で復旧しますか？`)){await call('prompt_evidence_apply_recovery',{action});await refresh()}});box.append(button)}host.append(box)}else{const actions=document.createElement('div');actions.className='planning-actions';const add=document.createElement('button');add.className='action';add.textContent='Promptメタデータ登録';add.addEventListener('click',()=>preparePromptEvidencePrompt(model));const attempt=document.createElement('button');attempt.className='action';attempt.textContent='終了済みGeneration Evidence取込';attempt.addEventListener('click',()=>preparePromptEvidenceAttempt(model));actions.append(add,attempt);host.append(actions)}for(const prompt of model.prompts||[]){const card=document.createElement('section');card.className='planning-card';const title=document.createElement('strong');title.textContent=`${prompt.prompt_id} v${prompt.prompt_version} · ${prompt.slot_id}`;const meta=document.createElement('div');meta.className='production-meta';meta.textContent=`Purpose: ${prompt.purpose}\nBody: ${prompt.body_sha256}\nPrivate ref: ${prompt.body_ref}\nProfile: ${prompt.provider_profile_id} / ${prompt.provider_profile_version}\nInputs: ${(prompt.input_asset_hashes||[]).join(', ')||'NONE'}\nKeep: ${(prompt.keep_conditions||[]).join(', ')}`;card.append(title,meta);for(const attempt of prompt.attempts||[]){const row=document.createElement('div');row.className='audit-card';const detail=document.createElement('div');detail.className='production-meta';detail.textContent=`${attempt.generation_job_id} · ${attempt.result}\nProvider/Model: ${attempt.provider_id} / ${attempt.model_id}\nStrategy: ${attempt.strategy_level} / Parent: ${attempt.parent_attempt_id||'NONE'}\nOutput Candidate: ${attempt.output_candidate_id||'NONE'}\nFailure: ${(attempt.failure_codes||[]).join(', ')||'NONE'}\nCost/Latency: ${attempt.cost??'unknown'} / ${attempt.latency_ms??'unknown'} ms`;row.append(detail);if(model.actions_allowed&&attempt.human_regeneration_available){const regen=document.createElement('button');regen.className='action';regen.textContent='Human再生成判断から次版Prompt';regen.addEventListener('click',()=>preparePromptRegeneration(model,attempt.output_candidate_id));row.append(regen)}card.append(row)}host.append(card)}const boundary=document.createElement('div');boundary.className='production-meta planning-warning';boundary.textContent='これはEvidence取込と次版Prompt登録だけです。Provider実行・課金・Candidate作成・自動再生成・Human判断は行いません。';host.append(boundary);drawer.hidden=false}
async function prepareGenerationQueue(model,prompt){const prepared=await call('generation_queue_prepare',{prompt_id:prompt.prompt_id,prompt_version:prompt.prompt_version,expected_queue_snapshot_sha256:model.queue_snapshot_sha256,expected_upstream_snapshots:model.upstream_snapshots});if(prepared&&window.confirm(`このPromptを生成Queue Evidenceへ登録しますか？\n${prompt.prompt_id} v${prompt.prompt_version}\nProviderは実行しません。`)){await call('generation_queue_apply',{confirmation_id:prepared.confirmation_id});renderGenerationQueue(await call('generation_queue_snapshot'))}}
function renderGenerationQueue(model){const drawer=document.querySelector('#generationQueueWorkspace'),host=document.querySelector('#generationQueueContent'),summary=document.querySelector('#generationQueueSummary');host.replaceChildren();if(!model?.available){summary.textContent='Generation Queue Applicationが接続されていません。';drawer.hidden=false;return}summary.textContent=`Admission ${model.entry_count} / Provider execution: NOT AUTHORIZED`;if(model.admission_blocker){const blocked=document.createElement('div');blocked.className='audit-recovery';blocked.textContent=`BLOCKED: ${model.admission_blocker.code} — ${model.admission_blocker.message}`;host.append(blocked)}for(const prompt of model.available_prompts||[]){const card=document.createElement('section');card.className='planning-card';card.textContent=`${prompt.prompt_id} v${prompt.prompt_version} · ${prompt.scene_id} / ${prompt.slot_id}`;const button=document.createElement('button');button.className='action';button.textContent='Admission Evidenceを登録';button.addEventListener('click',()=>prepareGenerationQueue(model,prompt));card.append(button);host.append(card)}for(const entry of model.entries||[]){const card=document.createElement('section');card.className='planning-card';const title=document.createElement('strong');title.textContent=`${entry.queue_entry_id} · ${entry.queue_status}`;const detail=document.createElement('div');detail.className='production-meta';detail.textContent=`Plan: ${entry.plan_id}\nScene/Slot: ${entry.scene_id} / ${entry.slot_id}\nPrompt: ${entry.prompt_id} v${entry.prompt_version}\nInputs: ${entry.input_bindings.length}\nContinuity: ${entry.continuity_proof?.edge_id||'CUT/NONE'}\nExecution: ${entry.execution_status}`;card.append(title,detail);host.append(card)}const boundary=document.createElement('div');boundary.className='production-meta planning-warning';boundary.textContent='EXECUTION_NOT_AUTHORIZED: Queue登録は実行許可ではありません。Provider呼出し・課金・Budget予約・Candidate作成・自動再生成は行いません。';host.append(boundary);drawer.hidden=false}
async function refresh(){const vm=await call('view_model');const x=vm?.shell||await call('snapshot');if(!x)return;const p=x.project;document.querySelector('#projectName').textContent=p?p.display_name:'プロジェクト未選択';document.querySelector('#job').textContent=x.active_jobs?.length?`${x.active_jobs.length} job`:'待機中';document.querySelectorAll('.workspace').forEach(b=>b.classList.toggle('active',b.dataset.w===x.current_workspace));if(vm){renderRows(vm);renderTimeline(vm)}const review=await call('review_snapshot');if(review)renderReview(review);const drawer=document.querySelector('#productionWorkspace'),planningDrawer=document.querySelector('#planningWorkspace'),safetyDrawer=document.querySelector('#generationSafetyWorkspace'),continuityDrawer=document.querySelector('#continuityWorkspace'),promptDrawer=document.querySelector('#promptEvidenceWorkspace');if(x.current_workspace==='PRODUCTION_CONTROL'){const production=await call('production_snapshot');const audit=await call('audit_snapshot');renderProduction(production,audit);planningDrawer.hidden=true;safetyDrawer.hidden=true;continuityDrawer.hidden=true;promptDrawer.hidden=true}else if(x.current_workspace==='PLANNING'){const planning=await call('planning_snapshot');renderPlanning(planning);drawer.hidden=true;safetyDrawer.hidden=true;continuityDrawer.hidden=true;promptDrawer.hidden=true}else if(x.current_workspace==='GENERATION_SAFETY'){const safety=await call('generation_safety_snapshot');renderGenerationSafety(safety);drawer.hidden=true;planningDrawer.hidden=true;continuityDrawer.hidden=true;promptDrawer.hidden=true}else if(x.current_workspace==='CONTINUITY'){const continuity=await call('continuity_snapshot');renderContinuity(continuity);drawer.hidden=true;planningDrawer.hidden=true;safetyDrawer.hidden=true;promptDrawer.hidden=true}else if(x.current_workspace==='PROMPT_EVIDENCE'){const promptEvidence=await call('prompt_evidence_snapshot');renderPromptEvidence(promptEvidence);drawer.hidden=true;planningDrawer.hidden=true;safetyDrawer.hidden=true;continuityDrawer.hidden=true}else{drawer.hidden=true;planningDrawer.hidden=true;safetyDrawer.hidden=true;continuityDrawer.hidden=true;promptDrawer.hidden=true}const runtime=await call('workflow_status');const action=document.querySelector('#workflowActionButton');action.disabled=!runtime?.available||!['media.choose_and_ingest','transcription.start','subtitle.save','cut_candidates.generate','resolve.assembly.prepare','resolve.assembly.apply','render.start','render.qa.inspect','handoff.create'].includes(runtime.next_recommended_action);action.textContent=runtime?.next_recommended_action||'Continue'}
document.querySelectorAll('.workspace').forEach(b=>b.addEventListener('click',async()=>{await call('set_workspace',{workspace:b.dataset.w});await refresh();const queueDrawer=document.querySelector('#generationQueueWorkspace');if(b.dataset.w==='GENERATION_QUEUE'){renderGenerationQueue(await call('generation_queue_snapshot'))}else{queueDrawer.hidden=true}}));
document.querySelector('#closeProductionButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closePlanningButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closeGenerationSafetyButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closeContinuityButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closePromptEvidenceButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closeGenerationQueueButton').addEventListener('click',async()=>{document.querySelector('#generationQueueWorkspace').hidden=true;await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#keepButton').addEventListener('click',async()=>{const review=await call('review_snapshot');const selected=review?.candidates?.find(x=>x.selected);if(selected){await call('review_candidate',{candidate_id:selected.candidate_id,decision:'KEEP'});await refresh()}});
document.querySelector('#cutButton').addEventListener('click',async()=>{const review=await call('review_snapshot');const selected=review?.candidates?.find(x=>x.selected);if(selected){await call('review_candidate',{candidate_id:selected.candidate_id,decision:'CUT'});await refresh()}});
document.querySelector('#approvePlanButton').addEventListener('click',async()=>{const p=await call('prepare_edit_plan_approval');if(!p)return;const ok=window.confirm(`編集プランを承認しますか？\nCUT: ${p.cut_count} / KEEP: ${p.keep_count}`);if(ok){await call('approve_edit_plan',{confirmation_id:p.confirmation_id,draft_plan_sha256:p.draft_plan_sha256,approved_by:'desktop-owner'});await refresh()}});
document.querySelector('#workflowActionButton').addEventListener('click',async()=>{const runtime=await call('workflow_status');if(!runtime?.available)return;let result=null;if(runtime.next_recommended_action==='media.choose_and_ingest')result=await call('choose_and_ingest_media',{});else if(runtime.next_recommended_action==='transcription.start')result=await call('run_local_transcription',{});else if(runtime.next_recommended_action==='subtitle.save')result=await call('create_runtime_subtitle_workspace',{});else if(runtime.next_recommended_action==='cut_candidates.generate')result=await call('generate_runtime_cut_candidates',{});else if(runtime.next_recommended_action==='resolve.assembly.prepare')result=await call('compile_resolve_assembly',{});else if(runtime.next_recommended_action==='resolve.assembly.apply'){const p=await call('prepare_resolve_apply',{});if(p&&window.confirm(`DaVinci Resolveへ適用しますか？\nProject: ${p.target_project}\nTimeline: ${p.target_timeline}`))result=await call('apply_resolve_assembly',{confirmation_id:p.confirmation_id})}else if(runtime.next_recommended_action==='render.start'){const p=await call('prepare_native_render_confirmation',{});if(p&&window.confirm(`DaVinci Resolveで書き出しますか？\nProject: ${p.target_project}\nTimeline: ${p.target_timeline}\nDestination: ${p.destination}`))result=await call('execute_native_render',{confirmation_id:p.confirmation_id})}else if(runtime.next_recommended_action==='render.qa.inspect')result=await call('bind_runtime_render_qa',{});else if(runtime.next_recommended_action==='handoff.create')result=await call('create_editor_handoff',{});const status=document.querySelector('#dialogStatus');status.textContent=result?'工程を完了しました':'工程を完了できませんでした';await refresh()});
async function chooseAndReport(method,label){const status=document.querySelector('#dialogStatus');status.textContent=`${label}を選択中`;const result=await call(method,{});if(!result){status.textContent=`${label}を選択できませんでした`;return}status.textContent=result.selected?`${label}を選択しました（操作は未開始）`:`${label}の選択をキャンセルしました`}
document.querySelector('#chooseProjectButton').addEventListener('click',()=>chooseAndReport('choose_project_folder','プロジェクト'));
document.querySelector('#chooseMediaButton').addEventListener('click',()=>chooseAndReport('choose_media_source','メディア'));
document.querySelector('#chooseHandoffButton').addEventListener('click',()=>chooseAndReport('choose_handoff_folder','保存先'));
function applyAccessibility(){const main=document.querySelector('main.viewer');if(main){main.id='editingCanvas';main.setAttribute('aria-label','映像プレビュー');main.tabIndex=0}const timeline=document.querySelector('section.timeline');if(timeline){timeline.setAttribute('role','region');timeline.setAttribute('aria-label','編集タイムライン')}const labels={keepButton:'候補を残す',cutButton:'候補をカットする',approvePlanButton:'編集プランを承認する'};for(const [id,label] of Object.entries(labels)){document.querySelector('#'+id)?.setAttribute('aria-label',label)}}
applyAccessibility();window.addEventListener('pywebviewready',refresh);setTimeout(refresh,300);
</script></body></html>'''


class Task036ShellBridge:
    """Allowlisted bridge used only by the native layout/runtime spike."""

    def __init__(
        self,
        service: ShellApplicationService,
        *,
        projection: EditingProjection | None = None,
        review: Task036ReviewFacade | None = None,
        application: Task036EditingApplication | None = None,
        native_dialog: Task036NativeDialogService | None = None,
        pre_edit_runtime: Task036PreEditRuntime | None = None,
        workflow_runtime: Task036WorkflowRuntime | None = None,
        workflow_runtime_factory: Callable[[Task036EditingApplication], Task036WorkflowRuntime] | None = None,
        production_control: Task037ProductionControlApplication | None = None,
        audit_application: Task038AuditApplication | None = None,
        planning_application: Task027PlanningApplication | None = None,
        generation_safety_application: Task013GenerationSafetyApplication | None = None,
        continuity_application: Task039ContinuityApplication | None = None,
        prompt_evidence_application: Task040PromptEvidenceApplication | None = None,
        generation_queue_application: Task027GenerationQueueApplication | None = None,
    ) -> None:
        if application is not None and application.shell is not service:
            raise ValueError("integrated application must use the supplied Shell service")
        self.service = service
        self.projection = projection
        self.review = review
        self.application = application
        self.native_dialog = native_dialog
        if pre_edit_runtime is not None and pre_edit_runtime.coordinator.shell is not service:
            raise ValueError("pre-edit runtime must use the supplied Shell service")
        self.pre_edit_runtime = pre_edit_runtime
        if workflow_runtime is not None and workflow_runtime.application is not application:
            raise ValueError("workflow runtime must use the supplied integrated application")
        if workflow_runtime is not None and workflow_runtime_factory is not None:
            raise ValueError("bind either a workflow runtime or a trusted runtime factory, not both")
        self.workflow_runtime = workflow_runtime
        self.workflow_runtime_factory = workflow_runtime_factory
        self.production_control = production_control
        self.audit_application = audit_application
        self.planning_application = planning_application
        self.generation_safety_application = generation_safety_application
        self.continuity_application = continuity_application
        self.prompt_evidence_application = prompt_evidence_application
        self.generation_queue_application = generation_queue_application

    def _current_application(self) -> Task036EditingApplication | None:
        if self.application is not None:
            return self.application
        if self.pre_edit_runtime is not None:
            return self.pre_edit_runtime.application
        return None

    def _require_native_dialog(self) -> Task036NativeDialogService:
        if self.native_dialog is None:
            raise ProductError(
                "ERR_TASK036_NATIVE_DIALOG_NOT_BOUND",
                "Native file/folder dialog service is not bound to this Shell",
                ProductErrorCategory.STATE,
            )
        return self.native_dialog

    def _require_workflow_runtime(self) -> Task036WorkflowRuntime:
        if self.workflow_runtime is None:
            raise ProductError(
                "ERR_TASK036_WORKFLOW_RUNTIME_NOT_BOUND",
                "Trusted minimum-editing runtime is not bound to this Shell",
                ProductErrorCategory.STATE,
            )
        return self.workflow_runtime

    @staticmethod
    def _empty_args(args: Any, operation: str) -> None:
        if args not in (None, {}):
            raise ProductError(
                "ERR_SHELL_BRIDGE_REQUEST_INVALID",
                f"{operation} request is invalid",
                ProductErrorCategory.VALIDATION,
            )

    def workflow_status(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "workflow status")
        if self.workflow_runtime is not None:
            return self.workflow_runtime.status()
        if self.pre_edit_runtime is not None:
            status = self.pre_edit_runtime.status()
            if status["next_recommended_action"] not in {
                "media.choose_and_ingest",
                "transcription.start",
                "subtitle.save",
                "cut_candidates.generate",
                "edit_plan.approve",
            }:
                status["available"] = False
                status["post_review_runtime_bound"] = False
            return status
        return {"available": False}

    def choose_and_ingest_media(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "media choose and ingest")
        if self.pre_edit_runtime is None:
            raise ProductError("ERR_TASK036_PRE_EDIT_RUNTIME_NOT_BOUND", "Trusted pre-edit runtime is not bound", ProductErrorCategory.STATE)
        return self.pre_edit_runtime.choose_and_ingest_media()

    def run_local_transcription(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "local transcription")
        if self.pre_edit_runtime is None:
            raise ProductError("ERR_TASK036_PRE_EDIT_RUNTIME_NOT_BOUND", "Trusted pre-edit runtime is not bound", ProductErrorCategory.STATE)
        return self.pre_edit_runtime.run_local_transcription()

    def create_runtime_subtitle_workspace(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Subtitle Workspace creation")
        if self.pre_edit_runtime is None:
            raise ProductError("ERR_TASK036_PRE_EDIT_RUNTIME_NOT_BOUND", "Trusted pre-edit runtime is not bound", ProductErrorCategory.STATE)
        return self.pre_edit_runtime.create_subtitle_workspace()

    def generate_runtime_cut_candidates(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Cut Candidate generation")
        if self.pre_edit_runtime is None:
            raise ProductError("ERR_TASK036_PRE_EDIT_RUNTIME_NOT_BOUND", "Trusted pre-edit runtime is not bound", ProductErrorCategory.STATE)
        result = self.pre_edit_runtime.generate_cut_candidates()
        application = self.pre_edit_runtime.application
        if application is not None and self.workflow_runtime_factory is not None:
            runtime = self.workflow_runtime_factory(application)
            if runtime.application is not application:
                raise ValueError("trusted runtime factory returned a different editing application")
            self.workflow_runtime = runtime
        return result

    def compile_resolve_assembly(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Resolve assembly compile")
        return self._require_workflow_runtime().compile_resolve_assembly()

    def prepare_resolve_apply(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Resolve apply preparation")
        return self._require_workflow_runtime().prepare_resolve_apply()

    def apply_resolve_assembly(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"}:
            raise ProductError(
                "ERR_SHELL_BRIDGE_REQUEST_INVALID",
                "Resolve apply request is invalid",
                ProductErrorCategory.VALIDATION,
            )
        return self._require_workflow_runtime().apply_resolve_assembly(str(args["confirmation_id"]))

    def prepare_native_render_gate(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "native render preparation")
        return self._require_workflow_runtime().prepare_native_render_gate()

    def prepare_native_render_confirmation(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "native render confirmation")
        return self._require_workflow_runtime().prepare_native_render_confirmation()

    def execute_native_render(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"}:
            raise ProductError(
                "ERR_SHELL_BRIDGE_REQUEST_INVALID",
                "native render request is invalid",
                ProductErrorCategory.VALIDATION,
            )
        return self._require_workflow_runtime().execute_native_render(str(args["confirmation_id"]))

    def bind_runtime_render_qa(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Render QA binding")
        return self._require_workflow_runtime().bind_runtime_render_qa()

    def create_editor_handoff(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "EDITOR_WORK creation")
        return self._require_workflow_runtime().create_editor_handoff()

    def choose_media_source(self, args: Any = None) -> dict[str, Any]:
        if args not in (None, {}):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "media chooser request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_native_dialog().choose_media_source().to_ui_dict()

    def choose_project_folder(self, args: Any = None) -> dict[str, Any]:
        if args not in (None, {}):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Project folder chooser request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_native_dialog().choose_project_folder().to_ui_dict()

    def choose_handoff_folder(self, args: Any = None) -> dict[str, Any]:
        if args not in (None, {}):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "handoff folder chooser request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_native_dialog().choose_handoff_folder().to_ui_dict()

    def snapshot(self, _args: Any = None) -> dict[str, Any]:
        return self.service.snapshot().to_dict()

    def view_model(self, _args: Any = None) -> dict[str, Any]:
        application = self._current_application()
        if application is not None:
            return application.view_model()
        return Task036DesktopViewModel(self.service.snapshot(), self.projection).to_dict()

    def set_workspace(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"workspace"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "workspace request is invalid", ProductErrorCategory.VALIDATION)
        self.service.set_workspace(str(args["workspace"]))
        return self.service.snapshot().to_dict()

    def _require_production_control(self) -> Task037ProductionControlApplication:
        if self.production_control is None:
            raise ProductError(
                "ERR_TASK037_PRODUCTION_CONTROL_NOT_BOUND",
                "Production Control is not bound to this Shell",
                ProductErrorCategory.STATE,
            )
        return self.production_control

    def production_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Production Control snapshot")
        if self.production_control is None:
            return {"available": False}
        return {"available": True, **self.production_control.snapshot()}

    def production_register_candidate(self, args: Any) -> dict[str, Any]:
        required = {"candidate_id", "slot_id", "asset_id", "asset_sha256", "expected_snapshot_sha256"}
        optional = {"generation_job_id", "parent_candidate_id", "supersedes"}
        if not isinstance(args, dict) or not required.issubset(args) or set(args) - required - optional:
            raise ProductError(
                "ERR_SHELL_BRIDGE_REQUEST_INVALID",
                "Production Candidate request is invalid",
                ProductErrorCategory.VALIDATION,
            )
        values = {key: args.get(key) for key in required | optional}
        return self._require_production_control().register_candidate(**values)

    def production_mark_ready_for_audit(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"candidate_id", "expected_snapshot_sha256"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Production audit-ready request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_production_control().mark_ready_for_audit(
            candidate_id=str(args["candidate_id"]),
            expected_snapshot_sha256=str(args["expected_snapshot_sha256"]),
        )

    def production_prepare_lock(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"slot_id", "candidate_id", "expected_snapshot_sha256"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Production lock preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_production_control().prepare_lock(
            slot_id=str(args["slot_id"]),
            candidate_id=str(args["candidate_id"]),
            expected_snapshot_sha256=str(args["expected_snapshot_sha256"]),
        )

    def production_apply_lock(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Production lock request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_production_control().apply_lock(confirmation_id=str(args["confirmation_id"]))

    def _require_audit_application(self) -> Task038AuditApplication:
        if self.audit_application is None:
            raise ProductError("ERR_TASK038_AUDIT_APPLICATION_NOT_BOUND", "Audit Workspace is not bound to this Shell", ProductErrorCategory.STATE)
        return self.audit_application

    def audit_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Audit Workspace snapshot")
        if self.audit_application is None:
            return {"available": False}
        return {"available": True, **self.audit_application.snapshot()}

    def audit_prepare_human_decision(self, args: Any) -> dict[str, Any]:
        required = {"candidate_id", "decision", "expected_production_snapshot_sha256", "expected_audit_snapshot_sha256"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Audit decision preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_audit_application().prepare_human_decision(**{key: str(args[key]) for key in required})

    def audit_apply_human_decision(self, args: Any) -> dict[str, Any]:
        required = {"confirmation_id", "actor_id"}
        if not isinstance(args, dict) or not required.issubset(args) or set(args) - required - {"notes"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Audit Human decision request is invalid", ProductErrorCategory.VALIDATION)
        notes = args.get("notes")
        return self._require_audit_application().apply_human_decision(
            confirmation_id=str(args["confirmation_id"]),
            actor_id=str(args["actor_id"]),
            notes=None if notes is None else str(notes),
        )

    def audit_apply_recovery(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"action"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Audit recovery request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_audit_application().apply_recovery(action=str(args["action"]))

    def _require_planning_application(self) -> Task027PlanningApplication:
        if self.planning_application is None:
            raise ProductError("ERR_TASK027_PLANNING_APPLICATION_NOT_BOUND", "Planning Workspace is not bound to this Shell", ProductErrorCategory.STATE)
        return self.planning_application

    def planning_snapshot(self, args: Any = None) -> dict[str, Any]:
        if args in (None, {}):
            proposal_id = None
        elif isinstance(args, dict) and set(args) == {"proposal_id"}:
            proposal_id = str(args["proposal_id"])
        else:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Planning snapshot request is invalid", ProductErrorCategory.VALIDATION)
        if self.planning_application is None:
            return {"available": False}
        return {"available": True, **self.planning_application.snapshot(proposal_id=proposal_id)}

    def planning_prepare_go(self, args: Any) -> dict[str, Any]:
        required = {
            "proposal_id", "proposal_revision", "reference_bindings", "cost_ceiling",
            "rights_warnings_acknowledged", "expected_snapshot_sha256",
        }
        if (
            not isinstance(args, dict)
            or set(args) != required
            or not isinstance(args["reference_bindings"], list)
            or not isinstance(args["rights_warnings_acknowledged"], bool)
            or isinstance(args["proposal_revision"], bool)
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Planning GO preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_planning_application().prepare_go(
            proposal_id=str(args["proposal_id"]),
            proposal_revision=int(args["proposal_revision"]),
            reference_bindings=args["reference_bindings"],
            cost_ceiling=str(args["cost_ceiling"]),
            rights_warnings_acknowledged=args["rights_warnings_acknowledged"],
            expected_snapshot_sha256=str(args["expected_snapshot_sha256"]),
        )

    def planning_approve_go(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id", "approved_by"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Planning GO request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_planning_application().approve_go(
            confirmation_id=str(args["confirmation_id"]),
            approved_by=str(args["approved_by"]),
        )

    def planning_prepare_install_plan(self, args: Any) -> dict[str, Any]:
        required = {"plan_id", "expected_proposal_snapshot_sha256", "expected_production_snapshot_sha256"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Planning install preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_planning_application().prepare_install_plan(**{key: str(args[key]) for key in required})

    def planning_apply_install_plan(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Planning install request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_planning_application().apply_install_plan(confirmation_id=str(args["confirmation_id"]))

    def _require_generation_safety_application(self) -> Task013GenerationSafetyApplication:
        if self.generation_safety_application is None:
            raise ProductError("ERR_TASK013_GENERATION_SAFETY_NOT_BOUND", "Generation Safety is not bound to this Shell", ProductErrorCategory.STATE)
        return self.generation_safety_application

    def generation_safety_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Generation Safety snapshot")
        if self.generation_safety_application is None:
            return {"available": False}
        return {"available": True, **self.generation_safety_application.snapshot()}

    def generation_safety_prepare_review(self, args: Any) -> dict[str, Any]:
        required = {
            "spec", "human_reviewed_checks", "blocking_reasons",
            "expected_planning_snapshot_sha256", "expected_safety_snapshot_sha256",
        }
        if (
            not isinstance(args, dict)
            or set(args) != required
            or not isinstance(args["spec"], dict)
            or not isinstance(args["human_reviewed_checks"], dict)
            or not isinstance(args["blocking_reasons"], list)
            or not all(isinstance(item, str) for item in args["blocking_reasons"])
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Safety preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_generation_safety_application().prepare_feasibility(
            spec=args["spec"],
            human_reviewed_checks=args["human_reviewed_checks"],
            blocking_reasons=tuple(args["blocking_reasons"]),
            expected_planning_snapshot_sha256=str(args["expected_planning_snapshot_sha256"]),
            expected_safety_snapshot_sha256=str(args["expected_safety_snapshot_sha256"]),
        )

    def generation_safety_apply_review(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id", "reviewed_by"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Safety apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_generation_safety_application().apply_feasibility(
            confirmation_id=str(args["confirmation_id"]),
            reviewed_by=str(args["reviewed_by"]),
        )

    def _require_continuity_application(self) -> Task039ContinuityApplication:
        if self.continuity_application is None:
            raise ProductError("ERR_TASK039_CONTINUITY_NOT_BOUND", "Continuity is not bound to this Shell", ProductErrorCategory.STATE)
        return self.continuity_application

    def continuity_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Continuity snapshot")
        if self.continuity_application is None:
            return {"available": False}
        return {"available": True, **self.continuity_application.snapshot()}

    def continuity_prepare_edge(self, args: Any) -> dict[str, Any]:
        required = {"edge_id", "from_slot_id", "to_slot_id", "boundary_type", "character_contract_refs", "space_contract_refs", "expected_production_snapshot_sha256", "expected_continuity_snapshot_sha256"}
        text_fields = required - {"character_contract_refs", "space_contract_refs"}
        if (
            not isinstance(args, dict)
            or set(args) != required
            or not all(isinstance(args[key], str) for key in text_fields)
            or not isinstance(args["character_contract_refs"], list)
            or not isinstance(args["space_contract_refs"], list)
            or not all(isinstance(item, str) for item in args["character_contract_refs"] + args["space_contract_refs"])
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity Edge preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().prepare_register_edge(
            edge_id=args["edge_id"], from_slot_id=args["from_slot_id"], to_slot_id=args["to_slot_id"],
            boundary_type=args["boundary_type"], character_contract_refs=tuple(args["character_contract_refs"]),
            space_contract_refs=tuple(args["space_contract_refs"]),
            expected_production_snapshot_sha256=args["expected_production_snapshot_sha256"],
            expected_continuity_snapshot_sha256=args["expected_continuity_snapshot_sha256"],
        )

    def continuity_apply_edge(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity Edge apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().apply_register_edge(confirmation_id=args["confirmation_id"])

    def continuity_inspect(self, args: Any) -> dict[str, Any]:
        required = {"edge_id", "expected_production_snapshot_sha256", "expected_continuity_snapshot_sha256"}
        if not isinstance(args, dict) or set(args) != required or not all(isinstance(args[key], str) for key in required):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity inspection request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().inspect_locked_target(**{key: args[key] for key in required})

    def continuity_prepare_soft_approval(self, args: Any) -> dict[str, Any]:
        required = {"edge_id", "expected_production_snapshot_sha256", "expected_continuity_snapshot_sha256"}
        if not isinstance(args, dict) or set(args) != required or not all(isinstance(args[key], str) for key in required):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity soft approval preparation is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().prepare_soft_approval(**{key: args[key] for key in required})

    def continuity_apply_soft_approval(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id", "approved_by"} or not all(isinstance(args[key], str) for key in args):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity soft approval request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().apply_soft_approval(confirmation_id=args["confirmation_id"], approved_by=args["approved_by"])

    def continuity_propagate_stale(self, args: Any) -> dict[str, Any]:
        required = {"root_slot_id", "expected_production_snapshot_sha256", "expected_continuity_snapshot_sha256"}
        if not isinstance(args, dict) or set(args) != required or not all(isinstance(args[key], str) for key in required):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity STALE request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().propagate_stale(**{key: args[key] for key in required})

    def continuity_apply_recovery(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"action"} or not isinstance(args["action"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Continuity recovery request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_continuity_application().apply_recovery(action=args["action"])

    def _require_prompt_evidence_application(self) -> Task040PromptEvidenceApplication:
        if self.prompt_evidence_application is None:
            raise ProductError("ERR_TASK040_PROMPT_EVIDENCE_NOT_BOUND", "Prompt Evidence is not bound to this Shell", ProductErrorCategory.STATE)
        return self.prompt_evidence_application

    def prompt_evidence_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Prompt Evidence snapshot")
        if self.prompt_evidence_application is None:
            return {"available": False}
        return {"available": True, **self.prompt_evidence_application.snapshot()}

    def prompt_evidence_prepare_prompt(self, args: Any) -> dict[str, Any]:
        required = {
            "prompt_id", "prompt_version", "purpose", "scene_id", "slot_id", "body_ref",
            "body_sha256", "provider_profile_id", "provider_profile_version", "input_asset_hashes",
            "keep_conditions", "expected_prompt_snapshot_sha256", "expected_production_snapshot_sha256",
        }
        text_fields = required - {"prompt_version", "input_asset_hashes", "keep_conditions"}
        if (
            not isinstance(args, dict) or set(args) != required
            or not all(isinstance(args[key], str) for key in text_fields)
            or isinstance(args["prompt_version"], bool) or not isinstance(args["prompt_version"], int)
            or not isinstance(args["input_asset_hashes"], list)
            or not isinstance(args["keep_conditions"], list)
            or not all(isinstance(item, str) for item in args["input_asset_hashes"] + args["keep_conditions"])
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Prompt preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().prepare_prompt(
            **{key: args[key] for key in text_fields}, prompt_version=args["prompt_version"],
            input_asset_hashes=tuple(args["input_asset_hashes"]), keep_conditions=tuple(args["keep_conditions"]),
        )

    def prompt_evidence_apply_prompt(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Prompt apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().apply_prompt(confirmation_id=args["confirmation_id"])

    def prompt_evidence_prepare_attempt(self, args: Any) -> dict[str, Any]:
        required = {
            "generation_job_id", "slot_id", "prompt_id", "prompt_version", "provider_id", "model_id",
            "strategy_level", "result", "failure_codes", "output_candidate_id", "parent_attempt_id",
            "cost", "latency_ms", "expected_prompt_snapshot_sha256", "expected_production_snapshot_sha256",
        }
        text_fields = {"generation_job_id", "slot_id", "prompt_id", "provider_id", "model_id", "result", "expected_prompt_snapshot_sha256", "expected_production_snapshot_sha256"}
        nullable_text = {"output_candidate_id", "parent_attempt_id"}
        if (
            not isinstance(args, dict) or set(args) != required
            or not all(isinstance(args[key], str) for key in text_fields)
            or not all(args[key] is None or isinstance(args[key], str) for key in nullable_text)
            or isinstance(args["prompt_version"], bool) or not isinstance(args["prompt_version"], int)
            or isinstance(args["strategy_level"], bool) or not isinstance(args["strategy_level"], int)
            or not isinstance(args["failure_codes"], list) or not all(isinstance(item, str) for item in args["failure_codes"])
            or (args["cost"] is not None and (isinstance(args["cost"], bool) or not isinstance(args["cost"], (int, float))))
            or (args["latency_ms"] is not None and (isinstance(args["latency_ms"], bool) or not isinstance(args["latency_ms"], int)))
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Evidence preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().prepare_attempt(
            generation_job_id=args["generation_job_id"], slot_id=args["slot_id"], prompt_id=args["prompt_id"],
            prompt_version=args["prompt_version"], provider_id=args["provider_id"], model_id=args["model_id"],
            strategy_level=args["strategy_level"], result=args["result"], failure_codes=tuple(args["failure_codes"]),
            output_candidate_id=args["output_candidate_id"], parent_attempt_id=args["parent_attempt_id"],
            cost=args["cost"], latency_ms=args["latency_ms"],
            expected_prompt_snapshot_sha256=args["expected_prompt_snapshot_sha256"],
            expected_production_snapshot_sha256=args["expected_production_snapshot_sha256"],
        )

    def prompt_evidence_apply_attempt(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Evidence apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().apply_attempt(confirmation_id=args["confirmation_id"])

    def prompt_evidence_prepare_regeneration(self, args: Any) -> dict[str, Any]:
        required = {
            "candidate_id", "new_body_sha256", "new_body_ref", "provider_profile_id",
            "provider_profile_version", "input_asset_hashes", "keep_conditions", "repeated_failure_threshold",
            "expected_prompt_snapshot_sha256", "expected_production_snapshot_sha256", "expected_audit_snapshot_sha256",
        }
        text_fields = {"candidate_id", "new_body_sha256", "new_body_ref", "expected_prompt_snapshot_sha256", "expected_production_snapshot_sha256", "expected_audit_snapshot_sha256"}
        nullable_text = {"provider_profile_id", "provider_profile_version"}
        nullable_lists = {"input_asset_hashes", "keep_conditions"}
        if (
            not isinstance(args, dict) or set(args) != required
            or not all(isinstance(args[key], str) for key in text_fields)
            or not all(args[key] is None or isinstance(args[key], str) for key in nullable_text)
            or not all(args[key] is None or (isinstance(args[key], list) and all(isinstance(item, str) for item in args[key])) for key in nullable_lists)
            or isinstance(args["repeated_failure_threshold"], bool) or not isinstance(args["repeated_failure_threshold"], int)
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Regeneration Prompt preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().prepare_regeneration(
            candidate_id=args["candidate_id"], new_body_sha256=args["new_body_sha256"], new_body_ref=args["new_body_ref"],
            provider_profile_id=args["provider_profile_id"], provider_profile_version=args["provider_profile_version"],
            input_asset_hashes=None if args["input_asset_hashes"] is None else tuple(args["input_asset_hashes"]),
            keep_conditions=None if args["keep_conditions"] is None else tuple(args["keep_conditions"]),
            repeated_failure_threshold=args["repeated_failure_threshold"],
            expected_prompt_snapshot_sha256=args["expected_prompt_snapshot_sha256"],
            expected_production_snapshot_sha256=args["expected_production_snapshot_sha256"],
            expected_audit_snapshot_sha256=args["expected_audit_snapshot_sha256"],
        )

    def prompt_evidence_apply_regeneration(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Regeneration Prompt apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().apply_regeneration(confirmation_id=args["confirmation_id"])

    def prompt_evidence_apply_recovery(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"action"} or not isinstance(args["action"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Prompt Evidence recovery request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_prompt_evidence_application().apply_recovery(action=args["action"])

    def _require_generation_queue_application(self) -> Task027GenerationQueueApplication:
        if self.generation_queue_application is None:
            raise ProductError("ERR_TASK027_GENERATION_QUEUE_NOT_BOUND", "Generation Queue is not bound to this Shell", ProductErrorCategory.STATE)
        return self.generation_queue_application

    def generation_queue_snapshot(self, args: Any = None) -> dict[str, Any]:
        self._empty_args(args, "Generation Queue snapshot")
        if self.generation_queue_application is None:
            return {"available": False}
        return {"available": True, **self.generation_queue_application.snapshot()}

    def generation_queue_prepare(self, args: Any) -> dict[str, Any]:
        required = {"prompt_id", "prompt_version", "expected_queue_snapshot_sha256", "expected_upstream_snapshots"}
        if (
            not isinstance(args, dict) or set(args) != required
            or not isinstance(args["prompt_id"], str)
            or isinstance(args["prompt_version"], bool) or not isinstance(args["prompt_version"], int)
            or not isinstance(args["expected_queue_snapshot_sha256"], str)
            or not isinstance(args["expected_upstream_snapshots"], dict)
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in args["expected_upstream_snapshots"].items())
        ):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Queue preparation request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_generation_queue_application().prepare_enqueue(
            prompt_id=args["prompt_id"], prompt_version=args["prompt_version"],
            expected_queue_snapshot_sha256=args["expected_queue_snapshot_sha256"],
            expected_upstream_snapshots=args["expected_upstream_snapshots"],
        )

    def generation_queue_apply(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"confirmation_id"} or not isinstance(args["confirmation_id"], str):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "Generation Queue apply request is invalid", ProductErrorCategory.VALIDATION)
        return self._require_generation_queue_application().apply_enqueue(confirmation_id=args["confirmation_id"])

    def review_snapshot(self, _args: Any = None) -> dict[str, Any]:
        application = self._current_application()
        review = application.review if application is not None else self.review
        if review is None:
            return {"available": False}
        return {"available": True, **review.snapshot()}

    def select_candidate(self, args: Any) -> dict[str, Any]:
        application = self._current_application()
        review = application.review if application is not None else self.review
        if review is None:
            raise ProductError("ERR_SHELL_REVIEW_NOT_AVAILABLE", "Cut review is not bound to this Shell", ProductErrorCategory.STATE)
        if not isinstance(args, dict) or set(args) != {"candidate_id"}:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "candidate selection request is invalid", ProductErrorCategory.VALIDATION)
        return review.select_candidate(str(args["candidate_id"]))

    def review_candidate(self, args: Any) -> dict[str, Any]:
        application = self._current_application()
        review = application.review if application is not None else self.review
        if review is None:
            raise ProductError("ERR_SHELL_REVIEW_NOT_AVAILABLE", "Cut review is not bound to this Shell", ProductErrorCategory.STATE)
        allowed = {"candidate_id", "decision", "override_start_us", "override_end_us"}
        if not isinstance(args, dict) or set(args) - allowed or not {"candidate_id", "decision"}.issubset(args):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "candidate review request is invalid", ProductErrorCategory.VALIDATION)
        return review.review_candidate(
            candidate_id=str(args["candidate_id"]),
            decision=str(args["decision"]),
            override_start_us=args.get("override_start_us"),
            override_end_us=args.get("override_end_us"),
        )

    def prepare_edit_plan_approval(self, args: Any = None) -> dict[str, Any]:
        if args not in (None, {}):
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "plan approval preview request is invalid", ProductErrorCategory.VALIDATION)
        application = self._current_application()
        review = application.review if application is not None else self.review
        if review is None:
            raise ProductError("ERR_SHELL_REVIEW_NOT_AVAILABLE", "Cut review is not bound to this Shell", ProductErrorCategory.STATE)
        return review.prepare_plan_approval()

    def approve_edit_plan(self, args: Any) -> dict[str, Any]:
        application = self._current_application()
        review = application.review if application is not None else self.review
        if review is None:
            raise ProductError("ERR_SHELL_REVIEW_NOT_AVAILABLE", "Cut review is not bound to this Shell", ProductErrorCategory.STATE)
        required = {"confirmation_id", "draft_plan_sha256", "approved_by"}
        if not isinstance(args, dict) or set(args) != required:
            raise ProductError("ERR_SHELL_BRIDGE_REQUEST_INVALID", "plan approval request is invalid", ProductErrorCategory.VALIDATION)
        if application is not None:
            return application.approve_edit_plan(
                confirmation_id=str(args["confirmation_id"]),
                draft_plan_sha256=str(args["draft_plan_sha256"]),
                approved_by=str(args["approved_by"]),
            )
        return review.approve_plan(
            confirmation_id=str(args["confirmation_id"]),
            draft_plan_sha256=str(args["draft_plan_sha256"]),
            approved_by=str(args["approved_by"]),
        )


def run_native_layout_spike(*, product_version: str = "0.20.1") -> None:
    """Launch the native layout spike when optional pywebview is installed.

    This function does not install dependencies and does not mutate Product data.
    """

    try:
        import webview  # type: ignore
    except ModuleNotFoundError as exc:
        raise ProductError(
            "ERR_TASK036_PYWEBVIEW_NOT_INSTALLED",
            "TASK-036 native layout spike requires the optional pywebview package",
            ProductErrorCategory.EXTERNAL_DEPENDENCY,
            details={"install_or_packaging_change_authorized": False},
        ) from exc

    demo_manifest = CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256="sha256:" + "1" * 64,
        analysis_sample_rate=48_000,
        source_duration_us=10_000_000,
        config_sha256="sha256:" + "2" * 64,
        transcript_manifest_sha256="sha256:" + "3" * 64,
        candidates=(
            CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_500_000, 2_200_000, 92, ("SILENCE",)),
            CutCandidate("cut-000002", CutCandidateKind.FILLER, 4_000_000, 4_600_000, 78, ("FILLER",)),
        ),
        keep_blocks=(),
    )
    application = Task036EditingApplication.create(
        product_version=product_version,
        project_id="TASK036_LAYOUT_SPIKE",
        display_name="DbD 朝活ドキュメント",
        source_asset_sha256="sha256:" + "4" * 64,
        cut_manifest=demo_manifest,
    )
    application.shell.set_workspace(WorkspaceId.EDIT)
    application.select_candidate("cut-000001")
    bridge = Task036ShellBridge(
        application.shell,
        application=application,
        native_dialog=Task036NativeDialogService(),
    )
    webview.create_window(
        "BAI Video Production — TASK-036 Layout Spike",
        html=HTML,
        js_api=bridge,
        width=1600,
        height=900,
        min_size=(1100, 700),
    )
    # TASK-036 supports the Windows EdgeChromium/WebView2 renderer only.
    webview.start(gui="edgechromium")
