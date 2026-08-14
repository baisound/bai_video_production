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
<header class="top"><div class="brand">BAI Video Production</div><div class="project" id="projectName">プロジェクト未選択</div><button class="workspace active" data-w="EDIT">編集</button><button class="workspace" data-w="PLANNING">企画</button><button class="workspace" data-w="GENERATION_SAFETY">生成安全</button><button class="workspace" data-w="SUBTITLE">字幕</button><button class="workspace" data-w="REVIEW">レビュー</button><button class="workspace" data-w="PRODUCTION_CONTROL">制作管理</button><button class="workspace" data-w="EXPORT">書き出し</button><div class="spacer"></div><span id="dialogStatus" class="dialog-status" role="status" aria-live="polite">選択操作なし</span><span id="job">待機中</span><button class="action" id="workflowActionButton" aria-label="次の編集工程を実行" disabled>Continue</button><button class="action" id="chooseProjectButton" aria-label="プロジェクトフォルダーを選択">プロジェクト</button><button class="action" id="chooseMediaButton" aria-label="メディアファイルを選択">メディア</button><button class="action" id="chooseHandoffButton" aria-label="EDITOR WORK保存先を選択">保存先</button></header>
<aside id="productionWorkspace" class="production-drawer" aria-label="制作管理" hidden><div class="production-heading"><h2>制作管理</h2><div class="spacer"></div><button class="action" id="closeProductionButton" aria-label="制作管理を閉じる">閉じる</button></div><p class="production-summary" id="productionSummary">制作管理データを読み込み中です。</p><div id="productionSlots"></div></aside>
<aside id="planningWorkspace" class="production-drawer" aria-label="企画" hidden><div class="production-heading"><h2>企画 / Scene Contract</h2><div class="spacer"></div><button class="action" id="closePlanningButton" aria-label="企画を閉じる">閉じる</button></div><p class="production-summary" id="planningSummary">企画データを読み込み中です。</p><div id="planningContent"></div></aside>
<aside id="generationSafetyWorkspace" class="production-drawer" aria-label="生成安全" hidden><div class="production-heading"><h2>生成安全 / Shot Feasibility</h2><div class="spacer"></div><button class="action" id="closeGenerationSafetyButton" aria-label="生成安全を閉じる">閉じる</button></div><p class="production-summary" id="generationSafetySummary">生成安全データを読み込み中です。</p><div id="generationSafetyContent"></div></aside>
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
async function refresh(){const vm=await call('view_model');const x=vm?.shell||await call('snapshot');if(!x)return;const p=x.project;document.querySelector('#projectName').textContent=p?p.display_name:'プロジェクト未選択';document.querySelector('#job').textContent=x.active_jobs?.length?`${x.active_jobs.length} job`:'待機中';document.querySelectorAll('.workspace').forEach(b=>b.classList.toggle('active',b.dataset.w===x.current_workspace));if(vm){renderRows(vm);renderTimeline(vm)}const review=await call('review_snapshot');if(review)renderReview(review);const drawer=document.querySelector('#productionWorkspace'),planningDrawer=document.querySelector('#planningWorkspace'),safetyDrawer=document.querySelector('#generationSafetyWorkspace');if(x.current_workspace==='PRODUCTION_CONTROL'){const production=await call('production_snapshot');const audit=await call('audit_snapshot');renderProduction(production,audit);planningDrawer.hidden=true;safetyDrawer.hidden=true}else if(x.current_workspace==='PLANNING'){const planning=await call('planning_snapshot');renderPlanning(planning);drawer.hidden=true;safetyDrawer.hidden=true}else if(x.current_workspace==='GENERATION_SAFETY'){const safety=await call('generation_safety_snapshot');renderGenerationSafety(safety);drawer.hidden=true;planningDrawer.hidden=true}else{drawer.hidden=true;planningDrawer.hidden=true;safetyDrawer.hidden=true}const runtime=await call('workflow_status');const action=document.querySelector('#workflowActionButton');action.disabled=!runtime?.available||!['media.choose_and_ingest','transcription.start','subtitle.save','cut_candidates.generate','resolve.assembly.prepare','resolve.assembly.apply','render.start','render.qa.inspect','handoff.create'].includes(runtime.next_recommended_action);action.textContent=runtime?.next_recommended_action||'Continue'}
document.querySelectorAll('.workspace').forEach(b=>b.addEventListener('click',async()=>{await call('set_workspace',{workspace:b.dataset.w});await refresh()}));
document.querySelector('#closeProductionButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closePlanningButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
document.querySelector('#closeGenerationSafetyButton').addEventListener('click',async()=>{await call('set_workspace',{workspace:'EDIT'});await refresh()});
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
