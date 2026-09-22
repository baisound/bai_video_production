"""Deterministic TASK-098 extensions for the owner-canonical V6.1.1 Shell."""

from __future__ import annotations

import json

from .task036_pre_edit_runtime import (
    _RUNTIME_CONTROL_EXACT_ROWS,
    _RUNTIME_CONTROL_KEYS,
)


def _compose_runtime_managed_v611_html(html: str) -> str:
    """Add the bounded v2 transcription route without changing v1 behavior."""

    control_keys_json = json.dumps(
        list(_RUNTIME_CONTROL_KEYS), ensure_ascii=False, separators=(",", ":"),
    )
    control_rows_json = json.dumps(
        [list(row) for row in sorted(_RUNTIME_CONTROL_EXACT_ROWS, key=repr)],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    replacements = (
        (
            "action.disabled=transcriptionInFlight||preEditStageInFlight||!workflow.next_recommended_action;action.dataset.nextAction=workflow.next_recommended_action||'';action.textContent=workflow.next_recommended_label||workflow.next_recommended_action||'次の工程'",
            "const v2Transcription=workflow.transcription_runtime_mode==='RUNTIME_MANAGED_V2'&&workflow.next_recommended_action==='transcription.start';action.disabled=transcriptionInFlight||preEditStageInFlight||!workflow.next_recommended_action||(v2Transcription&&workflow.transcription_available_action==='NONE');action.dataset.nextAction=workflow.next_recommended_action||'';action.textContent=v2Transcription?(workflow.transcription_status_label||'次の工程'):(workflow.next_recommended_label||workflow.next_recommended_action||'次の工程')",
        ),
        (
            "const recovery=workflow.transcription_recovery_required===true;prepared=await call(recovery?'prepare_local_transcription_recovery':'prepare_local_transcription',{});",
            "const v2=workflow.transcription_runtime_mode==='RUNTIME_MANAGED_V2',action=v2?workflow.transcription_available_action:(workflow.transcription_recovery_required===true?'RECOVER':'START'),route={START:['prepare_local_transcription','run_local_transcription'],RECOVER:['prepare_local_transcription_recovery','recover_local_transcription'],VERIFY:['prepare_local_transcription_verification','verify_local_transcription']}[action];if(!route){notify('現在の文字起こし状態では実行できません。',true);return}const recovery=action==='RECOVER',verification=action==='VERIFY';prepared=await call(route[0],{});",
        ),
        (
            "const prompt=recovery?`完了済みのローカル文字起こしEvidenceを照合して再結合しますか？\\nSource: ${prepared.source_asset_id}\\nSHA-256: ${prepared.source_asset_sha256}\\nProviderは再実行しません。`:`現在の動画を無償ローカルFasterWhisperで文字起こししますか？\\nSource: ${prepared.source_asset_id}\\nSHA-256: ${prepared.source_asset_sha256}\\nモデルの自動ダウンロード・有償Provider・Cloudは使用しません。`;",
            "const prompt=v2?prepared.transcription_status_label:(recovery?`完了済みのローカル文字起こしEvidenceを照合して再結合しますか？\\nSource: ${prepared.source_asset_id}\\nSHA-256: ${prepared.source_asset_sha256}\\nProviderは再実行しません。`:`現在の動画を無償ローカルFasterWhisperで文字起こししますか？\\nSource: ${prepared.source_asset_id}\\nSHA-256: ${prepared.source_asset_sha256}\\nモデルの自動ダウンロード・有償Provider・Cloudは使用しません。`);",
        ),
        (
            "const result=await call(recovery?'recover_local_transcription':'run_local_transcription',{confirmation_id:prepared.confirmation_id}),identity=transcriptionIdentity(result);",
            "const runtimeControlDuringTranscription=$('runtimeControlButton');if(v2&&action==='START'){runtimeControlDuringTranscription.disabled=false;runtimeControlDuringTranscription.textContent='文字起こしをキャンセル'}const result=await call(route[1],{confirmation_id:prepared.confirmation_id}),identity=transcriptionIdentity(result);",
        ),
        (
            "notify(`${recovery?'文字起こしEvidenceを再結合':'ローカル文字起こしを完了'}しました: ${identity.digest}`)",
            "notify(`${verification?'文字起こしEvidenceを検証':recovery?'文字起こしEvidenceを再結合':'ローカル文字起こしを完了'}しました: ${identity.digest}`)",
        ),
    )
    for old, new in replacements:
        if html.count(old) != 1:
            raise RuntimeError("V6.1.1 transcription HTML anchor changed")
        html = html.replace(old, new)
    inflight_anchor = "let transcriptionInFlight=false;"
    if html.count(inflight_anchor) != 1:
        raise RuntimeError("V6.1.1 transcription in-flight anchor changed")
    html = html.replace(
        inflight_anchor,
        inflight_anchor + "let runtimeControlInFlightEligible=false;",
    )
    enable_anchor = "if(v2&&action==='START'){runtimeControlDuringTranscription.disabled=false;"
    if html.count(enable_anchor) != 1:
        raise RuntimeError("V6.1.1 runtime control enable anchor changed")
    html = html.replace(
        enable_anchor,
        "if(v2&&action==='START'){runtimeControlInFlightEligible=true;"
        "runtimeControlDuringTranscription.disabled=false;",
    )
    finally_anchor = "finally{transcriptionInFlight=false;"
    if html.count(finally_anchor) != 1:
        raise RuntimeError("V6.1.1 transcription finally anchor changed")
    html = html.replace(
        finally_anchor,
        "finally{transcriptionInFlight=false;runtimeControlInFlightEligible=false;",
    )
    button_anchor = '<button class="btn" id="workflowActionButton" disabled>次の編集工程</button>'
    if html.count(button_anchor) != 1:
        raise RuntimeError("V6.1.1 runtime control button anchor changed")
    html = html.replace(
        button_anchor,
        button_anchor + '<button class="btn" id="runtimeControlButton" disabled>文字起こし制御</button>',
    )
    refresh_anchor = "}else{action.disabled=true;action.textContent='次の工程'}}const mediaReady="
    if html.count(refresh_anchor) != 1:
        raise RuntimeError("V6.1.1 runtime control refresh anchor changed")
    html = html.replace(
        refresh_anchor,
        "}else{action.disabled=true;action.textContent='次の工程'}}"
        "const runtimeControl=$('runtimeControlButton'),nested=workflow?.transcription_control,"
        "nestedAction=nested?.available_action,topAction=workflow?.transcription_available_action,"
        "controlAvailable=workflow?.transcription_runtime_mode==='RUNTIME_MANAGED_V2'&&"
        "workflow?.next_recommended_action==='transcription.start'&&topAction==='NONE'&&"
        "['REQUEST_CANCEL','CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY'].includes(nestedAction);"
        "runtimeControl.disabled=preEditStageInFlight||(!runtimeControlInFlightEligible&&!controlAvailable);"
        "runtimeControl.textContent=runtimeControlInFlightEligible?'文字起こしをキャンセル':(controlAvailable?(nested.status_label||'文字起こし制御'):'文字起こし制御');"
        "const mediaReady=",
    )
    function_anchor = "async function workflowAction(){"
    if html.count(function_anchor) != 1:
        raise RuntimeError("V6.1.1 runtime control function anchor changed")
    control_function = (
        f"const runtimeControlProjectionKeys={control_keys_json};"
        f"const runtimeControlProjectionRows=new Set({control_rows_json}.map(row=>JSON.stringify(row)));"
        "function isExactRuntimeControlProjection(value){"
        "if(!value||Array.isArray(value)||typeof value!=='object')return false;"
        "if(JSON.stringify(Object.keys(value))!==JSON.stringify(runtimeControlProjectionKeys))return false;"
        "if(value.control_mode!=='PHASE_ONLY_V1'||value.no_replay!==true)return false;"
        "for(const key of ['provider_execution_started','provider_execution_known','provider_stop_confirmed','slot_release_allowed','no_replay'])if(typeof value[key]!=='boolean')return false;"
        "const row=[value.phase,value.cancel_state,value.adjudication_state,value.available_action,value.status_label,value.provider_execution_started,value.provider_execution_known,value.provider_stop_confirmed,value.stop_evidence,value.slot_release_allowed];"
        "return runtimeControlProjectionRows.has(JSON.stringify(row))}"
        "function isExactRuntimeControlApplyResult(value){"
        "if(!value||Array.isArray(value)||typeof value!=='object')return false;"
        "if(JSON.stringify(Object.keys(value))!==JSON.stringify(['task_owner','status','transcription_control']))return false;"
        "return value.task_owner==='TASK-098'&&value.status==='RUNTIME_TRANSCRIPTION_CONTROL_APPLIED'&&isExactRuntimeControlProjection(value.transcription_control)}"
        "async function runRuntimeTranscriptionControl(){"
        "const prepared=await call('prepare_runtime_transcription_control',{});if(!prepared?.confirmation_id)return;"
        "if(!window.confirm(`${prepared.status_label}\\n\\n${prepared.warning}`)){await call('cancel_runtime_transcription_control',{confirmation_id:prepared.confirmation_id});return;}"
        "try{const applied=await call('apply_runtime_transcription_control',{confirmation_id:prepared.confirmation_id});"
        "if(isExactRuntimeControlApplyResult(applied))notify('文字起こし制御を受け付けました')}"
        "finally{await refreshShell()}}"
    )
    html = html.replace(function_anchor, control_function + function_anchor)
    listener_anchor = "$('workflowActionButton').addEventListener('click',workflowAction);"
    if html.count(listener_anchor) != 1:
        raise RuntimeError("V6.1.1 runtime control listener anchor changed")
    return html.replace(
        listener_anchor,
        listener_anchor + "$('runtimeControlButton').addEventListener('click',runRuntimeTranscriptionControl);",
    )


def _compose_review_html(html: str) -> str:
    """Add Human-only local WAV review controls to the unified Product UI."""

    button_anchor = '<button class="btn" id="runtimeControlButton" disabled>文字起こし制御</button>'
    if html.count(button_anchor) != 1:
        raise RuntimeError("TASK-098 review control button anchor changed")
    review_markup = (
        '<section class="record" id="universalWavReview" aria-label="Universal WAV Review">'
        '<strong>Universal WAV Review</strong>'
        '<div class="muted small" id="universalWavReviewStatus">canonical Asset未接続</div>'
        '<canvas id="universalWavReviewWaveform" width="640" height="120" '
        'aria-label="private音声の一時波形" style="width:100%;height:90px;background:#090c10;margin:8px 0"></canvas>'
        '<button class="btn" id="universalWavReviewButton" disabled>音声を再生して波形を表示</button>'
        '</section>'
    )
    html = html.replace(button_anchor, button_anchor + review_markup)

    function_anchor = "async function workflowAction(){"
    if html.count(function_anchor) != 1:
        raise RuntimeError("TASK-098 review function anchor changed")
    review_functions = (
        "function clearUniversalWavReviewWaveform(){const canvas=$('universalWavReviewWaveform'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height)}"
        "function renderUniversalWavReviewWaveform(points){const canvas=$('universalWavReviewWaveform'),ctx=canvas.getContext('2d');clearUniversalWavReviewWaveform();if(!Array.isArray(points)||!points.length)return;ctx.strokeStyle='#69d2a4';ctx.lineWidth=1;ctx.beginPath();const mid=canvas.height/2;for(let i=0;i<points.length;i++){const value=points[i];if(!Number.isInteger(value)||value<0||value>1000){clearUniversalWavReviewWaveform();return}const x=i*(canvas.width-1)/Math.max(1,points.length-1),height=value*(canvas.height-4)/2000;ctx.moveTo(x,mid-height);ctx.lineTo(x,mid+height)}ctx.stroke()}"
        "async function refreshUniversalWavReview(){const model=await call('view_model',{}),review=model?.universal_wav_review,button=$('universalWavReviewButton'),status=$('universalWavReviewStatus'),ready=review?.available===true&&review?.capabilities?.audition===true&&review?.capabilities?.waveform_render===true;button.disabled=!ready;status.textContent=ready?'Human操作時のみ再生・波形表示できます':'canonical Asset review runtime未接続';if(!ready)clearUniversalWavReviewWaveform()}"
        "async function runUniversalWavReview(){const button=$('universalWavReviewButton');button.disabled=true;clearUniversalWavReviewWaveform();let prepared=null,finalStatus=null;try{prepared=await call('universal_wav_review_prepare',{});if(!prepared?.confirmation_id)return;if(!window.confirm(`${prepared.status_label}を実行しますか？\\n\\n${prepared.warning}`)){await call('universal_wav_review_cancel',{confirmation_id:prepared.confirmation_id});return}const result=await call('universal_wav_review_apply',{confirmation_id:prepared.confirmation_id});const valid=result?.task_owner==='TASK-098'&&result?.runtime_state==='SUCCEEDED'&&result?.playback_observed===true&&result?.waveform_observed===true&&result?.canonical_receipt_created===false&&result?.review_completion_claimed===false&&result?.review_state_persisted===false&&result?.human_decision_authorized===false&&result?.media_mutation_started===false&&result?.waveform_ephemeral===true&&result?.audio_body_exposed===false&&result?.private_identity_exposed===false&&Array.isArray(result?.waveform_envelope_milli)&&result.waveform_envelope_milli.length>0&&result.waveform_envelope_milli.length<=2048;if(!valid){finalStatus='再生・波形結果を検証できませんでした';return}renderUniversalWavReviewWaveform(result.waveform_envelope_milli);finalStatus=`再生・波形表示完了 · ${result.waveform_envelope_milli.length} points · canonical state未変更`}finally{await refreshUniversalWavReview();if(finalStatus)$('universalWavReviewStatus').textContent=finalStatus}}"
    )
    html = html.replace(function_anchor, review_functions + function_anchor)

    refresh_anchor = "if(page==='edit'){await refreshReview();await refreshTimeline();await refreshSpeechCues()}"
    if html.count(refresh_anchor) != 1:
        raise RuntimeError("TASK-098 review refresh anchor changed")
    html = html.replace(
        refresh_anchor,
        "if(page==='edit'){await refreshReview();await refreshTimeline();await refreshSpeechCues();await refreshUniversalWavReview()}",
    )

    listener_anchor = "$('runtimeControlButton').addEventListener('click',runRuntimeTranscriptionControl);"
    if html.count(listener_anchor) != 1:
        raise RuntimeError("TASK-098 review listener anchor changed")
    return html.replace(
        listener_anchor,
        listener_anchor + "$('universalWavReviewButton').addEventListener('click',runUniversalWavReview);",
    )


def compose_task098_product_shell_html(html: str) -> str:
    """Return the single canonical Product HTML including bounded TASK-098 UI."""

    return _compose_review_html(_compose_runtime_managed_v611_html(html))


__all__ = ["compose_task098_product_shell_html"]
