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


HTML = r'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BAI Video Production</title>
<style>
:root{color-scheme:dark;--bg:#090b0e;--panel:#11151b;--panel2:#151a21;--line:#262d37;--text:#e7ebf2;--muted:#8c96a5;--accent:#4c83e7;--purple:#6d4acb;--audio:#21785e;--warn:#d28a34}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:13px/1.35 "Segoe UI","Noto Sans JP",sans-serif;overflow:hidden}button:focus-visible,a:focus-visible{outline:3px solid #ffcc4d;outline-offset:2px}.skip-link{position:fixed;left:8px;top:-60px;z-index:100;background:#fff;color:#000;padding:10px}.skip-link:focus{top:8px}
button,select{font:inherit;color:inherit}.app{height:100vh;display:grid;grid-template-rows:46px minmax(0,1fr) 300px;background:linear-gradient(180deg,#0c0f13,#080a0d)}
.top{display:flex;align-items:center;gap:8px;padding:0 14px;border-bottom:1px solid var(--line);background:#0c1015}.brand{font-weight:700}.project{color:#cdd3dd}.spacer{flex:1}.workspace{background:transparent;border:0;padding:9px 10px;border-bottom:2px solid transparent;cursor:pointer}.workspace.active{border-color:var(--accent);color:#fff}.action{background:#181d24;border:1px solid #303844;border-radius:6px;padding:7px 12px}.dialog-status{position:fixed;z-index:20;top:54px;right:16px;max-width:min(420px,calc(100vw - 32px));padding:7px 10px;border:1px solid #394553;border-radius:6px;background:#111820ee;color:#d7deea;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 5px 18px #0008}.main{min-height:0;display:grid;grid-template-columns:320px minmax(420px,1fr) 330px;gap:8px;padding:8px}.panel{min-width:0;min-height:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel-title{height:38px;display:flex;align-items:center;padding:0 12px;border-bottom:1px solid var(--line);font-weight:650}.tabs{display:flex;gap:4px;padding:8px;border-bottom:1px solid var(--line)}.tab{border:0;background:transparent;color:var(--muted);padding:7px 9px}.tab.active{background:#1a2535;color:#fff;border-radius:5px}.rows{height:calc(100% - 82px);overflow:auto}.row{display:grid;grid-template-columns:80px 1fr auto;gap:8px;padding:10px 12px;border-bottom:1px solid #1c222b}.row:hover{background:#171d25}.time{font-variant-numeric:tabular-nums;color:#aeb7c4}.status{font-size:11px;color:#8fb3ff}.viewer{display:grid;grid-template-rows:minmax(0,1fr) 54px;background:#07090b}.screen{margin:10px;background:radial-gradient(circle at 50% 20%,#354653 0,#1c2b32 25%,#0c1115 65%);border:1px solid #20262e;border-radius:6px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}.screen:before{content:"";position:absolute;inset:0;background:linear-gradient(140deg,transparent 0 42%,rgba(255,255,255,.06) 43% 44%,transparent 45% 100%)}.tc{position:absolute;bottom:18px;background:#050607cc;padding:6px 12px;border-radius:5px;font:28px/1 monospace}.controls{display:flex;align-items:center;gap:16px;padding:0 14px;border-top:1px solid var(--line);color:#c7ced8}.scrub{height:4px;background:#353c47;flex:1;border-radius:3px;overflow:hidden}.scrub i{display:block;width:31%;height:100%;background:var(--accent)}.inspector{padding:12px}.field{margin-bottom:14px}.field label{display:block;color:#aab3c0;margin-bottom:6px}.value{background:#0d1116;border:1px solid #2a313b;border-radius:6px;padding:9px}.hint{color:var(--muted);font-size:12px}.timeline{margin:0 8px 8px;display:grid;grid-template-columns:116px minmax(0,1fr);grid-template-rows:30px repeat(6,44px);border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#0e1217}.ruler{grid-column:2;border-bottom:1px solid var(--line);background:#12171d;position:relative}.ruler:after{content:"00:00        00:20        00:40        01:00        01:20";position:absolute;left:12px;right:10px;top:7px;color:#85909f;word-spacing:55px;font-size:10px}.track-name{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:13px 10px;color:#aeb7c4;background:#10151a}.track{border-bottom:1px solid var(--line);position:relative;overflow:hidden}.clip{position:absolute;top:5px;bottom:5px;border-radius:4px;padding:7px 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.video{left:1%;width:94%;background:#25303a;border:1px solid #3b4f63}.sub1{left:2%;width:17%;background:#54389a}.sub2{left:20%;width:16%;background:#5e3da8}.sub3{left:37%;width:23%;background:#6742b4}.audio{left:1%;width:94%;background:#165942}.se{left:8%;width:32%;background:#275b87}.narr{left:42%;width:44%;background:#9a5428}.cut{background:#6c2f35;border:1px solid #b45a64}.review-actions{display:flex;gap:8px;margin-top:12px}.review-actions button{flex:1}.review-actions button:disabled{opacity:.4;cursor:not-allowed}.selection{outline:2px solid #8fb3ff;outline-offset:-2px}.progress-note{margin-top:10px;color:#aab3c0}.approve{margin-top:12px;width:100%}.playhead{position:absolute;left:31%;top:0;bottom:0;width:2px;background:#e75f51;z-index:5}.timeline-wrap{position:relative;grid-column:1/-1;display:contents}@media(max-width:1320px){.top .action{padding-inline:8px}}@media(max-width:1150px){.main{grid-template-columns:250px minmax(360px,1fr) 270px}.app{grid-template-rows:46px minmax(0,1fr) 250px}}@media(max-width:900px){body{overflow:auto}.app{height:auto;min-height:100vh;grid-template-rows:auto auto auto}.top{flex-wrap:wrap;min-height:46px;padding-block:6px}.main{grid-template-columns:1fr}.panel{min-height:260px}.viewer{min-height:420px}.timeline{min-width:720px}}
</style></head>
<body><a class="skip-link" href="#transcriptRows">編集内容へ移動</a><div class="app">
<header class="top"><div class="brand">BAI Video Production</div><div class="project" id="projectName">プロジェクト未選択</div><button class="workspace active" data-w="EDIT">編集</button><button class="workspace" data-w="SUBTITLE">字幕</button><button class="workspace" data-w="REVIEW">レビュー</button><button class="workspace" data-w="EXPORT">書き出し</button><div class="spacer"></div><span id="dialogStatus" class="dialog-status" role="status" aria-live="polite">選択操作なし</span><span id="job">待機中</span><button class="action" id="workflowActionButton" aria-label="次の編集工程を実行" disabled>Continue</button><button class="action" id="chooseProjectButton" aria-label="プロジェクトフォルダーを選択">プロジェクト</button><button class="action" id="chooseMediaButton" aria-label="メディアファイルを選択">メディア</button><button class="action" id="chooseHandoffButton" aria-label="EDITOR WORK保存先を選択">保存先</button></header>
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
async function refresh(){const vm=await call('view_model');const x=vm?.shell||await call('snapshot');if(!x)return;const p=x.project;document.querySelector('#projectName').textContent=p?p.display_name:'プロジェクト未選択';document.querySelector('#job').textContent=x.active_jobs?.length?`${x.active_jobs.length} job`:'待機中';document.querySelectorAll('.workspace').forEach(b=>b.classList.toggle('active',b.dataset.w===x.current_workspace));if(vm){renderRows(vm);renderTimeline(vm)}const review=await call('review_snapshot');if(review)renderReview(review);const runtime=await call('workflow_status');const action=document.querySelector('#workflowActionButton');action.disabled=!runtime?.available||!['media.choose_and_ingest','transcription.start','subtitle.save','cut_candidates.generate','resolve.assembly.prepare','resolve.assembly.apply','render.start','render.qa.inspect','handoff.create'].includes(runtime.next_recommended_action);action.textContent=runtime?.next_recommended_action||'Continue'}
document.querySelectorAll('.workspace').forEach(b=>b.addEventListener('click',async()=>{await call('set_workspace',{workspace:b.dataset.w});await refresh()}));
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
