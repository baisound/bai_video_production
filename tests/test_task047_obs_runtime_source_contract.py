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
        "levelMeter.UpdateLevels(livePeakDb, liveRmsDb, clips > 0)",
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
