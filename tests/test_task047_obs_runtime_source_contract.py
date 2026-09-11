from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native" / "task047_obs_voice_capture"


def test_managed_meter_source_keeps_owned_worker_isolated_from_capture():
    controller = _text("controller/BaiVoiceCaptureController.cs")
    assert "--bvp-meter-managed-v1" in controller
    assert "BaiMeterNativeWindows" in controller
    assert "BaiMeterBuildIdentity.Files" in controller
    assert "actual.SetEquals(admitted)" in controller
    assert "FileAttributes.ReparsePoint" in controller
    assert "--bvp-meter-protocol-self-test" in controller
    assert "--bvp-meter-scalar-self-test" in controller
    refresh = controller.split("private void RefreshUi()", 1)[1].split(
        "private static string FormatBytes", 1)[0]
    assert "SnapshotAndReset" in refresh
    assert "meterSession.Offer(window, samples, clips, paused)" in refresh
    capture_update = controller.split("private void UpdateMetrics(byte[] payload)", 1)[1].split(
        "private void PauseCapture()", 1)[0]
    assert "BaiMeterScalarWindow" not in capture_update
    assert "WriteFile" not in capture_update
    assert "SessionMaximum" in controller
    assert "CreateJobObjectW" in controller
    assert "TerminateJobObject" not in controller


def test_managed_meter_legacy_wire_explicitly_keeps_loss_unknown():
    controller = _text("controller/BaiVoiceCaptureController.cs")
    scalar = controller.split("internal static class BaiMeterScalarWindow", 1)[1].split(
        "internal sealed class BaiMeterManagedSession", 1)[0]
    assert "BaiMeterProtocol.LegacyLossUnknown" in scalar
    assert "BaiMeterProtocol.LegacyWindow(stream.ToArray())" in scalar
    assert "payload" not in scalar


def test_concrete_worker_partial_create_publishes_raw_receipt_before_validation():
    controller = _text("controller/BaiVoiceCaptureController.cs")
    create = controller.split("public BaiMeterProcessIdentity CreateProcessW(", 1)[1].split(
        "private static IntPtr TokenInfo", 1)[0]
    assert create.index("var rawOwner = new BaiMeterProcessIdentity()") < create.index("effects.Create(")
    assert create.index("ownedChild = rawOwner") < create.index("Own(result.Process)") < create.index("Own(result.Thread)")
    assert "rawOwner.Process = result.Process; rawOwner.Thread = result.Thread" in create
    cleanup = controller.split("private bool CleanupRound(", 1)[1].split("private void StartCleanup", 1)[0]
    assert "TryAction(CloseParentCopiesOfChildPipeEndsAndAttributes)" in cleanup
    assert "TryAction(() => CloseOwned(parentInput))" in cleanup
    assert "TryAction(() => BaiMeterProtocol.Require(effects.Terminate(ownedChild.Process)))" in cleanup
    assert "TryAction(() => CloseOwned(job))" in cleanup
    assert cleanup.index("effects.Terminate") < cleanup.index("if (!childExited) childExited = WaitExact()")
    assert cleanup.index("if (!childExited) return false") < cleanup.index("TryAction(FinishCleanup)")
    assert "pendingCleanup.Add(this)" in controller
    assert "cleanupState = \"CLEANUP_PENDING\"" in controller
    assert "Only our raw CreateProcess success can authorize a process effect" in controller


def test_concrete_cleanup_inert_self_tests_cover_combined_faults_without_obs():
    controller = _text("controller/BaiVoiceCaptureController.cs")
    tests = controller.split("internal static void AssertCleanupContracts()", 1)[1].split(
        "internal sealed class BaiMeterNativeOwnedWorker", 1)[0]
    for scenario in ("thread-invalid", "pipe", "parent-pipe", "attributes", "free", "resume-pipe",
                     "resume-attributes", "resume-uncertain", "graceful-parent-pipe", "delayed-exit",
                     "terminate-failure", "wait-failure"):
        assert '"' + scenario + '"' in tests
    assert 'owner.cleanupState == "CLEANUP_PENDING"' in tests
    assert 'fake.Calls.IndexOf("wait:0") < fake.Calls.IndexOf("close:120")' in tests
    assert "empty.CleanupOwnedFailure" in tests
    assert "BaiMeterNativeWindows.AssertCleanupContracts();" in controller
    assert "new CaptureForm" not in tests and "Process.Start" not in tests


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
        "0 dBFS = 基準線 / +値 = 基準超過 / 適正判定 未確定",
        "peakHold.Observe(peakDb, meterClock.Elapsed.Ticks)",
        "Math.Max(MinimumDb, Math.Min(MaximumDb, value))",
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
    assert "Math.Log10(Math.Min(1.0, amplitude))" not in controller
    assert 'Math.Log10(amplitude)).ToString("+0.0;-0.0;0.0"' in controller
    assert "window.RangeState" in controller
    assert "入力範囲外(今回)" in controller
    assert "入力範囲外(履歴)" in controller
    assert "quiet_window_clears_red_bar_but_preserves_history" in controller
    assert "overrange_numeric_value_is_positive_and_explicit" in controller
    assert "public const double MaximumDb = 12.0;" in controller
    assert "new[] { -60, -48, -36, -24, -12, 0, 6, 12 }" in controller
    assert "meter_has_visible_positive_headroom" in controller
    assert "only_drawing_saturates_above_positive_scale" in controller
    assert "above_scale_current_and_history_remain_explicit" in controller
    assert "positive_peak_hold_is_not_clamped_to_zero" in controller


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


def test_gain_summary_survives_timer_refresh_without_hiding_terminal_failure() -> None:
    controller = _text("controller/BaiVoiceCaptureController.cs")
    start = controller.split("private async void StartOperation(bool measureGain)", 1)[1].split(
        "private bool ValidateSameObsProcess", 1
    )[0]
    stop = controller.split("private void BeginStop(string reason)", 1)[1].split(
        "private void WriteGainReceipt", 1
    )[0]
    refresh = controller.split("private void RefreshUi()", 1)[1].split(
        "private static string FormatBytes", 1
    )[0]
    assert "completedGainSummary = null;" in start
    assert "completedGainSummary = completedGainMeasurement ? FormatGainSummary() : null;" in stop
    assert stop.index("completedGainSummary =") < stop.index("RefreshUi();")
    assert "detail.Text = FormatGainSummary()" not in stop
    assert "CaptureTerminalDisplay.Format(terminalReason, completedGainSummary)" in refresh
    for case in (
        "gain_summary_and_reason_remain_visible",
        "gain_summary_survives_repeated_refresh",
        "gain_summary_does_not_hide_finalize_failure",
        "ordinary_recording_has_no_previous_gain_summary",
    ):
        assert case in controller
