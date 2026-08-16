from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "tools" / "windows" / "run-task036-pux1c-native-closure.ps1"
).read_text(encoding="utf-8")


def test_pux1c_gate_uses_owned_short_package_and_explicit_private_mode() -> None:
    for marker in (
        "bai-task036-pux1c-",
        "package_copied_to_owned_short_path = $true",
        "pywebview_private_mode_explicit = $true",
        "private_mode_recreated_without_conversation = $true",
        "Remove-Item -LiteralPath $runRoot -Recurse -Force",
        "PostMessage($Handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)",
        "Stop-Process -Id $value.process.Id -Force",
    ):
        assert marker in SCRIPT
    assert "PostMessage([IntPtr]::Zero" not in SCRIPT
    assert "Get-Process | Stop-Process" not in SCRIPT
    assert "taskkill" not in SCRIPT.lower()

    shell = (ROOT / "src" / "ai_video_production" / "task036_shell_ui.py").read_text(encoding="utf-8")
    trusted = (ROOT / "src" / "ai_video_production" / "task036_trusted_launcher.py").read_text(encoding="utf-8")
    assert 'webview.start(gui="edgechromium", private_mode=True)' in shell
    assert 'webview.start(gui="edgechromium", private_mode=True)' in trusted


def test_pux1c_gate_records_real_scaling_without_conflating_text_and_dpi() -> None:
    for marker in (
        "TextScaleFactor",
        "text_scale_percent = $textScale",
        "monitor_dpi_x = $dpiX",
        "monitor_scale_percent",
        "monitor_dpi_and_text_scale_recorded_separately = $true",
        "all_display_moves_passed",
    ):
        assert marker in SCRIPT


def test_pux1c_gate_exercises_visual_interaction_focus_and_restart() -> None:
    for marker in (
        "01-home.png",
        "02-file-menu.png",
        "03-settings-audio.png",
        "04-export.png",
        "05-edit-after-scrub.png",
        "06-world-lock.png",
        "07-scene-design.png",
        "08-quick.png",
        "required_surface_captures_complete",
        "required_surface_anchor_bounds_passed",
        "Assert-VisibleWithinRoot",
        "all_top_menus_verified",
        "top_menu_contracts",
        "disabled_menu_reasons_present",
        "Assert-MenuContract",
        "menu_escape_focus_restored",
        "settings_escape_focus_restored",
        "timeline_zoom_changed_geometry",
        "timeline_scroll_changed_geometry",
        "timeline_native_pointer_scrub_changed_controller_value",
        "canonical_track_controls_present",
        "track_visibility_lock_mute_round_trip",
        "track_height_python_round_trip",
        "$nameTrackHeight",
        "$nameAddBgm",
        "$nameAudioMute",
        "native_picker_cancelled_without_exit",
        "conversation_free_restart_passed",
        "Assert-DarkClientCoverage",
        "maximized_client_coverage_passed = $maximizedClientCoverage",
    ):
        assert marker in SCRIPT

    for menu_name in ("$nameFile", "$nameEdit", "$nameView", "$nameProject", "$nameGenerate", "$nameExport"):
        assert f"Assert-MenuContract $first.process {menu_name}" in SCRIPT

    required_capture_list = SCRIPT[SCRIPT.index("required_surface_capture_files"):]
    for file_name in (
        "01-home.png",
        "03-settings-audio.png",
        "04-export.png",
        "05-edit-after-scrub.png",
        "06-world-lock.png",
        "07-scene-design.png",
        "08-quick.png",
    ):
        assert file_name in required_capture_list

    semantic_ready = SCRIPT.index('if (-not $semanticReady) {\n    throw "Packaged Shell attempt')
    post_ready_restore = SCRIPT.index("ShowWindow($handle, 9)")
    post_ready_maximize = SCRIPT.index("ShowWindow($handle, 3)", post_ready_restore)
    closure_return = SCRIPT.index("return [ordered]@{ process = $process", post_ready_maximize)
    assert semantic_ready < post_ready_restore < post_ready_maximize < closure_return


def test_pux1c_gate_keeps_external_and_human_authority_false() -> None:
    for marker in (
        "mock_demo_state_used = $false",
        "provider_execution_started = $false",
        "paid_execution_authorized = $false",
        "credential_mutation_started = $false",
        "human_accept_or_lock_started = $false",
        "resolve_mutation_started = $false",
        "cubase_mutation_started = $false",
        "release_or_deploy_started = $false",
    ):
        assert marker in SCRIPT
