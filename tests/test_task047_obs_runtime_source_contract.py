from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native" / "task047_obs_voice_capture"


def _text(relative: str) -> str:
    return (SOURCE / relative).read_text(encoding="utf-8")


def test_reviewable_dev10_source_has_no_generated_binary() -> None:
    assert _text("VERSION").strip() == "0.1.0-dev.10"
    generated = [
        path
        for path in SOURCE.rglob("*")
        if path.is_file()
        and "build" not in path.relative_to(SOURCE).parts
        and path.suffix.lower() in {".dll", ".exe", ".obj", ".pdb"}
    ]
    assert generated == []


def test_handshake_is_memory_only_same_user_and_fixed_width() -> None:
    protocol = _text("include/bai_obs_capture/capture_protocol.hpp")
    client = _text("src/ipc_client.cpp")
    controller = _text("controller/BaiVoiceCaptureController.cs")

    assert "kSessionHelloMagic = 0x32484342U" in protocol
    assert "kSessionHelloVersion = 2" in protocol
    assert "sizeof(SessionHello) == 40" in protocol
    assert "OpenProcessToken(server" in client
    assert "EqualSid" in client
    assert "GetNamedPipeClientProcessId" in controller
    assert "PIPE_CLIENT_NOT_OBS" in controller
    assert "PIPE_CLIENT_OBS_PATH_MISMATCH" in controller
    for text in (client, controller):
        assert "BAI_OBS_CAPTURE_SESSION_KEY" not in text
        assert 'GetEnvironmentVariable("BAI_OBS_CAPTURE_SESSION_KEY")' not in text


def test_reconnect_keeps_nonce_and_advances_sequence() -> None:
    client = _text("src/ipc_client.cpp")
    security = _text("tests/security_tests.cpp")

    assert "header.sequence = sequence++" in client
    assert "header.session_nonce = nonce_" in client
    assert "header.sequence <= first_sequence" in security
    assert "header.session_nonce != first_nonce" in security
    assert "run_same_user_handshake_and_resume_test" in security


def test_controller_anchors_first_sequence_and_does_not_report_terminal_reconnect() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")

    assert "bool sequenceInitialized = false;" in controller
    assert "if (!sequenceInitialized)" in controller
    assert "expectedSequence = sequence;" in controller
    assert "terminalStopRequested = true;" in controller
    assert "!terminalStopRequested" in controller


def test_running_obs_start_pause_resume_stop_uses_one_exact_process() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")

    assert 'start.Text = "録音開始（OBS起動中でも可）"' in controller
    assert "obsProcessId = existingObs.Id" in controller
    for operation in ("PAUSE", "RESUME", "STOP"):
        assert f'ValidateSameObsProcess("{operation}")' in controller
    assert '"VERIFIED_SAME_PROCESS"' in controller
    assert '\\"obs_process_id\\"' in controller
    assert '\\"obs_process_reused\\"' in controller


def test_controller_has_live_gain_meter_and_persistent_recording_banners() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")

    for token in (
        "AudioLevelMeter",
        'AddRow(table, 4, "入力レベル", levelMeter, null)',
        "levelMeter.UpdateLevels(livePeakDb, liveRmsDb, window.Packet.ClipSampleCount > 0, clips > 0)",
        'status.Text = "● 学習データ録音中"',
        'status.Text = "⏸ 学習データ録音 一時停止中"',
        'dialog.Description = "学習データ録音の保存先を選択"',
    ):
        assert token in controller


def test_packaging_supports_isolated_output_roots() -> None:
    package = _text("scripts/package.ps1")

    for token in (
        "$ControllerPath",
        "$StageDirectory",
        "$ArtifactDirectory",
        "$operationRoot",
        "Package output escapes the operation root",
        "UPSTREAM-OBS-COPYING.txt",
    ):
        assert token in package


def test_plugin_callback_stays_bounded_and_effect_free() -> None:
    plugin = _text("src/obs_plugin.cpp")
    capture = _text("src/capture_core.cpp")

    callback = plugin.split("obs_audio_data *filter_audio", 1)[1].split(
        "obs_source_info filter_info", 1
    )[0]
    for forbidden in ("CreateFile", "WriteFile", "std::ofstream", "Sleep(", "WinHttp"):
        assert forbidden not in callback
    assert "context->core.on_audio" in callback
    assert "std::ofstream" not in capture


def test_meter_coalesces_packets_under_the_existing_metric_lock() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")
    update = controller.split("private void UpdateMetrics(byte[] payload)", 1)[1].split(
        "private void PauseCapture()", 1
    )[0]
    assert "AudioMeterPacket.Measure(payload)" in update
    locked_update = update.split("lock (metricLock)", 1)[1]
    assert "meterWindow.Accumulate(packet)" in locked_update
    assert "latestMetricPeak" not in controller
    refresh = controller.split("private void RefreshUi()", 1)[1].split(
        "private static string FormatBytes", 1
    )[0]
    assert "window = meterWindow.SnapshotAndReset();" in refresh.split("lock (metricLock)", 1)[1]
    assert "window.Packet.Rms" in refresh
    assert "window.SessionMaximum" in refresh
    assert "window.Packet.ClipSampleCount" in refresh
    assert "window.ObservationState" in refresh


def test_meter_preserves_session_facts_and_unconfirmed_quality_boundary() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")
    assert controller.count("peak = meterWindow.SessionMaximum;") == 2
    assert "meterWindow.ResetSession();" in controller
    pause_resume = controller.split("private void PauseCapture()", 1)[1].split(
        "private void StopCapture()", 1
    )[0]
    assert "ResetSession" not in pause_resume
    assert "ResetLevels" not in pause_resume
    for expected in (
        "0 dBFS = デジタル上限 / 警告・適正判定 未確定",
        "peakHold.Observe(peakDb, meterClock.Elapsed.Ticks)",
        "Math.Max(-60.0, Math.Min(0.0, value))",
        "clipDisplay.SessionClipped ? Color.Red : Color.DimGray",
        "UNKNOWN_POLICY_NOT_BOUND",
    ):
        assert expected in controller
    hold = controller.split("internal sealed class AudioMeterPeakHold", 1)[1].split(
        "internal sealed class AudioLevelMeter", 1
    )[0]
    assert "DateTime" not in hold


def test_meter_separates_current_clip_bar_history_and_overrange_display() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")
    paint = controller.split("protected override void OnPaint(PaintEventArgs e)", 1)[1].split(
        "private static double ClampDb", 1
    )[0]
    assert paint.count("clipDisplay.WindowClipped ? Color.FromArgb(220, 45, 45)") == 2
    assert "clipDisplay.SessionClipped ? Color.Red : Color.DimGray" in paint
    assert "Math.Log10(Math.Min(1.0, amplitude))" in controller
    assert "window.RangeState" in controller
    assert "入力範囲外(今回)" in controller
    assert "入力範囲外(履歴)" in controller
    assert "quiet_window_clears_red_bar_but_preserves_history" in controller
    assert "overrange_display_clamped_and_explicit" in controller


def test_meter_native_self_test_is_explicit_and_has_no_capture_or_file_effect() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")
    assert controller.index('x == "--meter-self-test"') < controller.index("Application.Run(")
    self_test = controller.split("internal static class MeterObservationSelfTest", 1)[1].split(
        "internal static class ControllerSelfTest", 1
    )[0]
    for forbidden in ("new CaptureForm", "File.", "Directory.", "Process.", "NamedPipe", "WaveFloatWriter"):
        assert forbidden not in self_test
    for case in (
        "high_then_low_preserves_peak",
        "sample_weighted_window_rms",
        "snapshot_resets_only_window",
        "session_maximum_monotonic",
        "silence_vs_missing_reading",
        "window_clip_delta_not_replayed",
        "nonfinite_samples_excluded_and_reported",
        "full_scale_and_overrange_observed_before_drawing_clamp",
        "hold_expires_at_exact_boundary",
        "pause_or_no_input_expires_hold",
    ):
        assert case in self_test
