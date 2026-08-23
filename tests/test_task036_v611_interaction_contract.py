from __future__ import annotations

import re

from ai_video_production.task036_shell_v611 import HTML


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
        "action.disabled=transcriptionInFlight||!workflow.next_recommended_action",
        "if(next==='transcription.start'){await runLocalTranscription();return}",
    ):
        assert marker in HTML
    assert "run_local_transcription',{model" not in HTML
    assert "allow_model_download" not in HTML
