from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_editing_session import EditingSessionState
from ai_video_production.desktop_media_workflow import IngestedMediaIdentity
from ai_video_production.errors import ProductError
from ai_video_production.faster_whisper_runtime_contract import (
    FasterWhisperRuntimeDecisionV1,
    FasterWhisperRuntimeRequestV1,
)
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_native_dialog import Task036NativeDialogService
from ai_video_production.task036_product_ports import RuntimeManagedLocalTranscriptionOutcomeV2
from ai_video_production.task036_pre_edit_runtime import LocalTranscriptionOutcome, Task036PreEditRuntime
from ai_video_production.task036_shell_ui import Task036ShellBridge


def sha(ch: str) -> str:
    return "sha256:" + ch * 64


class DialogBackend:
    def __init__(self, source: Path):
        self.source = source

    def choose_open_media(self):
        return str(self.source)

    def choose_project_folder(self):
        return None

    def choose_handoff_folder(self):
        return None


class IngestPort:
    def __init__(self):
        self.paths: list[Path] = []

    def ingest_local_media(self, source_path: Path):
        self.paths.append(source_path)
        return IngestedMediaIdentity("ASSET-00000000000000000000000000", sha("a"), source_path)


class TranscriptionPort:
    def __init__(self):
        self.calls: list[tuple[Path, str]] = []

    def transcribe_local_media(self, *, project_id: str, source_path: Path, source_asset_id: str, source_asset_sha256: str):
        self.calls.append((source_path, source_asset_id))
        return LocalTranscriptionOutcome(
            TranscriptManifest(
                source_asset_id, "ja", "faster-whisper", "local-cached-model",
                (TranscriptSegment("seg-000001", 0, 1_000_000, "hello"),),
            ), True,
        )

    def recover_local_media(self, **kwargs):
        raise AssertionError("recovery must not execute")


class CutPort:
    def __init__(self):
        self.calls: list[tuple[Path, TranscriptManifest]] = []

    def generate_cut_candidates(self, *, source_path: Path, transcript: TranscriptManifest):
        self.calls.append((source_path, transcript))
        return CutCandidateManifest(
            transcript.source_asset_id,
            sha("b"),
            48_000,
            2_000_000,
            sha("c"),
            transcript.to_dict()["manifest_sha256"],
            (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_500_000, 90, ("SILENCE",)),),
            (),
        )


def make_runtime(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    coordinator = DesktopEditingCoordinator.create(
        product_version="0.19.0",
        project_id="phase-g-sandbox",
        display_name="Phase G Sandbox",
    )
    ingest = IngestPort()
    transcription = TranscriptionPort()
    cut = CutPort()
    runtime = Task036PreEditRuntime(
        coordinator,
        Task036NativeDialogService(DialogBackend(source)),
        ingest,
        transcription,
        cut,
    )
    return source, runtime, ingest, transcription, cut


def make_v2_outcome(*, provider_started: bool = True) -> RuntimeManagedLocalTranscriptionOutcomeV2:
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    decision = FasterWhisperRuntimeDecisionV1.create(
        request=request,
        outcome="READY_CPU",
        reason_code="REQUESTED_CPU_AVAILABLE",
        capability_observation_sha256=sha("d"),
        issued_at="2026-09-19T12:00:00Z",
        expires_at="2026-09-19T12:05:00Z",
    )
    return RuntimeManagedLocalTranscriptionOutcomeV2(
        transcript=TranscriptManifest(
            "ASSET-00000000000000000000000000", "ja", "faster-whisper", "local-cached-model",
            (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
        ),
        provider_execution_started=provider_started,
        recovered_from_durable_result=not provider_started,
        operation_id="OP-00000000000000000000000000",
        slot_operation_id="OP-11111111111111111111111111",
        publication_set_sha256=sha("e"),
        runtime_request=request,
        runtime_decision=decision,
    )


class RuntimeManagedPort(TranscriptionPort):
    def __init__(self, recovery_state: object, outcome: RuntimeManagedLocalTranscriptionOutcomeV2):
        super().__init__()
        self.state = recovery_state
        self.outcome = outcome
        self.recovery_state_calls = 0
        self.recovery_calls = 0
        self.transcribe_calls = 0
        self.finalize_calls = 0
        self.probe_calls = 0
        self.factory_calls = 0
        self.slot_release_calls = 0
        self.durable_row_calls = 0

    def recovery_state(self, **_kwargs):
        self.recovery_state_calls += 1
        return self.state

    def transcribe_local_media(self, **_kwargs):
        self.transcribe_calls += 1
        self.calls.append((_kwargs["source_path"], _kwargs["source_asset_id"]))
        return self.outcome

    def recover_local_media(self, **_kwargs):
        self.recovery_calls += 1
        return self.outcome

    def finalize_local_media_binding(self, **_kwargs):
        self.finalize_calls += 1

    def effect_counts(self) -> dict[str, int]:
        return {
            "probe": self.probe_calls,
            "factory": self.factory_calls,
            "recover": self.recovery_calls,
            "transcribe": self.transcribe_calls,
            "finalize": self.finalize_calls,
            "slot_release": self.slot_release_calls,
            "durable_row": self.durable_row_calls,
        }


class MissingRecoveryStatePort(RuntimeManagedPort):
    recovery_state = None


class RaisingRecoveryStatePort(RuntimeManagedPort):
    def recovery_state(self, **_kwargs):
        self.recovery_state_calls += 1
        raise RuntimeError("synthetic recovery classifier failure")


def run_transcription(bridge: Task036ShellBridge) -> dict:
    prepared = bridge.prepare_local_transcription({})
    return bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})


def test_bridge_composes_trusted_media_transcript_subtitle_and_cut_route(tmp_path: Path):
    source, runtime, ingest, transcription, cut = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)

    assert bridge.workflow_status()["next_recommended_action"] == "media.choose_and_ingest"
    ingest_result = bridge.choose_and_ingest_media({})
    assert set(ingest_result) == {
        "task_owner", "operation", "status", "asset_id", "asset_sha256", "host_path_persisted",
    }
    assert ingest_result["asset_id"] == "ASSET-00000000000000000000000000"
    assert ingest_result["asset_sha256"] == sha("a")
    assert "source.mp4" not in json.dumps(ingest_result)
    assert "receipt" not in ingest_result
    assert ingest_result["host_path_persisted"] is False
    assert bridge.workflow_status()["next_recommended_action"] == "transcription.start"

    transcript_result = run_transcription(bridge)
    assert set(transcript_result) == {
        "task_owner", "operation", "status", "transcript_manifest_sha256",
        "next_recommended_action", "provider_execution_started",
        "provider_execution_completed", "provider_execution_mode",
        "provider_configuration_from_javascript", "transcript_text_exposed",
        "host_path_exposed", "recovered_from_durable_result",
    }
    assert transcript_result["status"] == "TRANSCRIBED"
    assert transcript_result["provider_execution_started"] is True
    assert transcript_result["provider_execution_completed"] is True
    assert transcript_result["provider_execution_mode"] == "LOCAL"
    assert transcript_result["provider_configuration_from_javascript"] is False
    assert transcript_result["transcript_text_exposed"] is False
    assert transcript_result["host_path_exposed"] is False
    assert "hello" not in json.dumps(transcript_result)
    assert "editing_session" not in transcript_result
    assert bridge.workflow_status()["next_recommended_action"] == "subtitle.save"

    bridge.create_runtime_subtitle_workspace({})
    assert bridge.workflow_status()["next_recommended_action"] == "cut_candidates.generate"
    cut_result = bridge.generate_runtime_cut_candidates({})

    assert ingest.paths == [source]
    assert transcription.calls == [(source, "ASSET-00000000000000000000000000")]
    assert cut.calls[0][0] == source
    assert cut_result["candidate_count"] == 1
    assert bridge.review_snapshot()["available"] is True
    assert bridge.view_model()["transcript_rows"]
    assert str(source) not in json.dumps(
        [bridge.workflow_status(), ingest_result, transcript_result, cut_result],
        ensure_ascii=False,
    )

    bridge.review_candidate({"candidate_id": "cut-000001", "decision": "KEEP"})
    approval = bridge.prepare_edit_plan_approval({})
    bridge.approve_edit_plan(
        {
            "confirmation_id": approval["confirmation_id"],
            "draft_plan_sha256": approval["draft_plan_sha256"],
            "approved_by": "owner",
        }
    )
    downstream = bridge.workflow_status()
    assert downstream["next_recommended_action"] == "resolve.assembly.prepare"
    assert downstream["available"] is False
    assert downstream["post_review_runtime_bound"] is False
    approved_state = runtime.coordinator.state
    with pytest.raises(ProductError) as repeated:
        bridge.generate_runtime_cut_candidates({})
    assert repeated.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert runtime.coordinator.state == approved_state
    assert len(cut.calls) == 1


def test_bridge_rejects_javascript_paths_and_provider_configuration(tmp_path: Path):
    _, runtime, ingest, transcription, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    with pytest.raises(ProductError) as exc:
        bridge.choose_and_ingest_media({"source_path": "C:/human-owned.mp4"})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert ingest.paths == []

    bridge.choose_and_ingest_media()
    with pytest.raises(ProductError) as exc:
        bridge.run_local_transcription({"model": "remote-paid-model", "allow_download": True})
    assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert transcription.calls == []


class SpeechCuePort:
    def __init__(self):
        self.generated: list[tuple[str, TranscriptManifest]] = []
        self.confirmation_counter = 0

    def snapshot(self, transcript: TranscriptManifest | None):
        return {
            "available": True,
            "task_owner": "TASK-056",
            "generated": False,
            "can_generate": transcript is not None,
        }

    def generate(self, *, project_id: str, transcript: TranscriptManifest):
        self.generated.append((project_id, transcript))
        return {
            "available": True,
            "task_owner": "TASK-056",
            "generated": True,
            "can_generate": True,
            "confirmed_count": 1,
            "review_count": 0,
            "rejected_count": 0,
            "review_items": [],
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def prepare_human_decision(self, *, transcript, cue_id, decision):
        self.confirmation_counter += 1
        return {
            "confirmation_id": f"cue-confirmation-{self.confirmation_counter}",
            "cue_id": cue_id,
            "decision": decision,
        }

    def cancel_human_decision(self, *, confirmation_id):
        return {
            "task_owner": "TASK-056",
            "status": "HUMAN_DECISION_CANCELLED",
            "confirmation_id": confirmation_id,
            "decision_persisted": False,
            "confirmation_token_persisted": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def apply_human_decision(self, *, transcript, confirmation_id):
        return {
            "task_owner": "TASK-056",
            "status": "HUMAN_DECISION_RECORDED",
            "decision_id": "SCD-000000000000000000000000",
            "cue_id": "CUE-000000000000000000000000",
            "decision": "ACCEPT",
            "review_store_sha256": sha("d"),
            "review_revision": 1,
            "confirmation_token_persisted": False,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

def test_speech_cue_bridge_reuses_bound_transcript_and_rejects_javascript_configuration(
    tmp_path: Path,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    cues = SpeechCuePort()
    runtime.speech_cue_port = cues
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)

    assert bridge.speech_cue_snapshot()["can_generate"] is False
    with pytest.raises(ProductError) as absent:
        bridge.generate_speech_cues()
    assert absent.value.code == "ERR_TASK056_TRANSCRIPT_NOT_BOUND"

    bridge.choose_and_ingest_media()
    run_transcription(bridge)
    assert bridge.speech_cue_snapshot()["can_generate"] is True
    with pytest.raises(ProductError) as configured:
        bridge.generate_speech_cues({"output_path": "C:/private", "profile": "other"})
    assert configured.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"

    result = bridge.generate_speech_cues()
    assert result["generated"] is True
    assert result["transcript_text_exposed"] is False
    assert result["host_path_exposed"] is False
    assert cues.generated[0][0] == "phase-g-sandbox"
    assert cues.generated[0][1] is runtime.binding.transcript
    assert "hello" not in json.dumps(result)

    with pytest.raises(ProductError) as unsafe_review:
        bridge.prepare_speech_cue_decision(
            {"cue_id": "CUE-000000000000000000000000", "decision": "ACCEPT", "path": "C:/private"}
        )
    assert unsafe_review.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"

    prepared = bridge.prepare_speech_cue_decision(
        {"cue_id": "CUE-000000000000000000000000", "decision": "ACCEPT"}
    )
    cancelled = bridge.cancel_speech_cue_decision(
        {"confirmation_id": prepared["confirmation_id"]}
    )
    assert cancelled["decision_persisted"] is False

    prepared = bridge.prepare_speech_cue_decision(
        {"cue_id": "CUE-000000000000000000000000", "decision": "ACCEPT"}
    )
    applied = bridge.apply_speech_cue_decision(
        {"confirmation_id": prepared["confirmation_id"]}
    )
    assert applied["status"] == "HUMAN_DECISION_RECORDED"
    assert applied["confirmation_token_persisted"] is False
    assert applied["canonical_timeline"] is False
    assert applied["auto_apply_authorized"] is False
def test_local_transcription_requires_single_use_python_confirmation(tmp_path: Path):
    _, runtime, _, transcription, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})

    for invalid in ({}, {"confirmation_id": 1}, {"confirmation_id": "unknown"}):
        with pytest.raises(ProductError):
            bridge.run_local_transcription(invalid)
    assert transcription.calls == []

    prepared = bridge.prepare_local_transcription({})
    cancelled = bridge.cancel_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert cancelled["provider_execution_started"] is False
    with pytest.raises(ProductError) as consumed:
        bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert consumed.value.code == "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID"
    assert transcription.calls == []


def test_explicit_recovery_binds_completed_transcript_without_provider_execution(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)

    class RecoveryPort(TranscriptionPort):
        recovery_calls = 0

        def recovery_required(self, project_id, source_asset_id, source_asset_sha256):
            return True

        def recover_local_media(self, *, project_id, source_path, source_asset_id, source_asset_sha256):
            self.recovery_calls += 1
            return LocalTranscriptionOutcome(
                TranscriptManifest(
                    source_asset_id, "ja", "faster-whisper", "local-cached-model",
                    (TranscriptSegment("seg-000001", 0, 1_000_000, "private recovered text"),),
                ),
                False,
                True,
            )

    recovery = RecoveryPort()
    runtime.transcription_port = recovery
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    assert bridge.workflow_status()["transcription_recovery_required"] is True
    prepared = bridge.prepare_local_transcription_recovery({})
    result = bridge.recover_local_transcription({"confirmation_id": prepared["confirmation_id"]})

    assert recovery.calls == []
    assert recovery.recovery_calls == 1
    assert result["provider_execution_started"] is False
    assert result["recovered_from_durable_result"] is True
    assert result["transcript_text_exposed"] is False
    assert runtime.coordinator.state.next_recommended_action == "subtitle.save"

def test_bridge_projects_picker_cancel_as_closed_no_effect_envelope(tmp_path: Path):
    _, runtime, ingest, _, _ = make_runtime(tmp_path)

    class CancelDialog:
        def choose_open_media(self): return None
        def choose_project_folder(self): return None
        def choose_handoff_folder(self): return None

    runtime.media.native_dialog = Task036NativeDialogService(CancelDialog())
    result = Task036ShellBridge(
        runtime.coordinator.shell, pre_edit_runtime=runtime,
    ).choose_and_ingest_media({})
    assert result == {
        "task_owner": "TASK-036",
        "operation": "MEDIA_CHOOSE_AND_INGEST",
        "status": "CANCELLED",
        "ingest_started": False,
        "host_path_persisted": False,
    }
    assert ingest.paths == []
    assert runtime.coordinator.state.source_asset_id is None


def test_local_transcription_is_single_flight_and_repeated_call_does_not_reexecute(tmp_path: Path):
    source, runtime, _, _, _ = make_runtime(tmp_path)
    entered, release = Event(), Event()

    class BlockingTranscriptionPort(TranscriptionPort):
        def transcribe_local_media(self, *, project_id: str, source_path: Path, source_asset_id: str, source_asset_sha256: str):
            self.calls.append((source_path, source_asset_id))
            entered.set()
            assert release.wait(5)
            return LocalTranscriptionOutcome(
                TranscriptManifest(
                    source_asset_id, "ja", "faster-whisper", "local-cached-model",
                    (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
                ), True,
            )

    port = BlockingTranscriptionPort()
    runtime.transcription_port = port
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    completed: list[dict] = []
    prepared = bridge.prepare_local_transcription({})
    worker = Thread(target=lambda: completed.append(bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})))
    worker.start()
    assert entered.wait(5)
    with pytest.raises(ProductError) as parallel:
        second = bridge.prepare_local_transcription({})
        bridge.run_local_transcription({"confirmation_id": second["confirmation_id"]})
    assert parallel.value.code == "ERR_TASK036_TRANSCRIPTION_IN_PROGRESS"
    assert port.calls == [(source, "ASSET-00000000000000000000000000")]
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert completed[0]["status"] == "TRANSCRIBED"
    with pytest.raises(ProductError) as repeated:
        run_transcription(bridge)
    assert repeated.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert len(port.calls) == 1


def test_local_transcription_source_drift_after_provider_fails_before_binding(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    entered, release = Event(), Event()

    class BlockingTranscriptionPort(TranscriptionPort):
        def transcribe_local_media(self, *, project_id: str, source_path: Path, source_asset_id: str, source_asset_sha256: str):
            self.calls.append((source_path, source_asset_id))
            entered.set()
            assert release.wait(5)
            return LocalTranscriptionOutcome(
                TranscriptManifest(
                    source_asset_id, "ja", "faster-whisper", "local-cached-model",
                    (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
                ), True,
            )

    port = BlockingTranscriptionPort()
    runtime.transcription_port = port
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    errors: list[ProductError] = []

    def invoke() -> None:
        try:
            run_transcription(bridge)
        except ProductError as exc:
            errors.append(exc)

    worker = Thread(target=invoke)
    worker.start()
    assert entered.wait(5)
    runtime.coordinator.bind_source(asset_id="ASSET-11111111111111111111111111", asset_sha256=sha("b"))
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert [error.code for error in errors] == ["ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE"]
    assert runtime.coordinator.state.transcript_sha256 is None
    assert runtime.binding.transcript is None


def test_bridge_rejects_malformed_private_transcription_result_without_leaking_it(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)

    class InvalidRuntime:
        coordinator = runtime.coordinator

        def run_local_transcription(self, confirmation_id):
            return {
                "task_owner": "TASK-036",
                "operation": "TRANSCRIPT_RESULT_BIND",
                "transcript_manifest_sha256": "C:/private/transcript.json",
                "next_recommended_action": "subtitle.save",
                "provider_execution_started": True,
                "provider_execution_completed": True,
                "provider_execution_mode": "LOCAL",
                "provider_configuration_from_javascript": False,
                "private_text": "do not expose",
            }

    invalid_runtime = InvalidRuntime()
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=invalid_runtime)
    with pytest.raises(ProductError) as invalid:
        bridge.run_local_transcription({"confirmation_id": "confirm"})
    assert invalid.value.code == "ERR_TASK036_TRANSCRIPTION_RESULT_INVALID"


@pytest.mark.parametrize(
    ("classifier", "action", "label"),
    [
        ("PENDING_ADMISSION", "START", "文字起こしを開始できます"),
        ("RECOVERABLE_PUBLICATION", "RECOVER", "文字起こし結果を復旧できます"),
        ("VERIFICATION_ONLY", "VERIFY", "文字起こし結果を検証できます"),
        ("ACTIVE_UNKNOWN", "NONE", "文字起こし処理の状態を確認できません"),
        ("ADJUDICATION_REQUIRED_NO_PUBLICATION", "NONE", "人による確認が必要です"),
        ("FAILED_TERMINAL", "NONE", "文字起こしは失敗しました"),
        ("CORRUPT_BLOCKED", "NONE", "文字起こし状態が破損しているため停止しました"),
    ],
)
def test_v2_status_projects_exact_classifier_action_and_label(
    tmp_path: Path, classifier: str, action: str, label: str,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort(classifier, make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})

    status = bridge.workflow_status({})
    assert status["transcription_runtime_mode"] == "RUNTIME_MANAGED_V2"
    assert status["transcription_recovery_state"] == classifier
    assert status["transcription_available_action"] == action
    assert status["transcription_status_label"] == label
    assert "transcription_recovery_required" not in status


def test_v2_source_less_status_does_not_call_classifier_or_expose_action(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("PENDING_ADMISSION", make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)

    status = bridge.workflow_status({})
    assert status["transcription_recovery_state"] is None
    assert status["transcription_available_action"] == "NONE"
    assert status["transcription_status_label"] is None
    assert port.recovery_state_calls == 0


@pytest.mark.parametrize(
    ("port_type", "classifier"),
    [
        (MissingRecoveryStatePort, "missing"),
        (RaisingRecoveryStatePort, "raises"),
        (RuntimeManagedPort, 123),
        (RuntimeManagedPort, "UNKNOWN"),
    ],
)
def test_v2_malformed_recovery_state_fails_closed_to_blocked_status(
    tmp_path: Path, port_type: type[RuntimeManagedPort], classifier: object,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = port_type(classifier, make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})

    status = bridge.workflow_status({})
    assert status["transcription_recovery_state"] == "CORRUPT_BLOCKED"
    assert status["transcription_available_action"] == "NONE"
    assert status["transcription_status_label"] == "文字起こし状態が破損しているため停止しました"
    with pytest.raises(ProductError) as rejected:
        bridge.prepare_local_transcription({})
    assert rejected.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"


def test_v2_bound_verification_is_read_only_and_later_stage_keeps_existing_action_priority(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("VERIFICATION_ONLY", make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    coordinate = runtime.coordinator.state
    project = runtime.coordinator.shell.project
    assert project is not None
    runtime.binding.bind_transcript_if_current(
        port.outcome.transcript,
        expected_project_id=coordinate.project_id,
        expected_revision=coordinate.revision,
        expected_source_asset_id=coordinate.source_asset_id,
        expected_source_asset_sha256=coordinate.source_asset_sha256,
        expected_context_revision=project.context_revision,
    )

    status = bridge.workflow_status({})
    assert status["transcription_available_action"] == "NONE"
    assert status["transcription_status_label"] == "文字起こし結果は検証済みです"
    assert status["next_recommended_action"] == "subtitle.save"
    with pytest.raises(ProductError) as rejected:
        bridge.prepare_local_transcription_verification({})
    assert rejected.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert port.recovery_calls == 0


@pytest.mark.parametrize(
    "classifier",
    [
        "PENDING_ADMISSION", "VERIFICATION_ONLY", "ACTIVE_UNKNOWN",
        "ADJUDICATION_REQUIRED_NO_PUBLICATION", "FAILED_TERMINAL", "CORRUPT_BLOCKED",
    ],
)
def test_v2_nonrecoverable_direct_recovery_is_effect_zero(tmp_path: Path, classifier: str):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort(classifier, make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})

    with pytest.raises(ProductError) as rejected:
        bridge.prepare_local_transcription_recovery({})
    assert rejected.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert port.recovery_calls == 0
    assert port.calls == []
    assert port.finalize_calls == 0


@pytest.mark.parametrize(
    "classifier",
    [
        "PENDING_ADMISSION",
        "ACTIVE_UNKNOWN",
        "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        "FAILED_TERMINAL",
        "CORRUPT_BLOCKED",
    ],
)
def test_v2_status_and_prepare_leave_available_fake_effect_counters_at_zero(
    tmp_path: Path, classifier: str,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort(classifier, make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})

    status = bridge.workflow_status({})
    assert status["transcription_recovery_state"] == classifier
    if classifier == "PENDING_ADMISSION":
        assert status["transcription_available_action"] == "START"
        prepared = bridge.prepare_local_transcription({})
        assert bridge.cancel_local_transcription(
            {"confirmation_id": prepared["confirmation_id"]}
        )["status"] == "CANCELLED"
    else:
        assert status["transcription_available_action"] == "NONE"
        with pytest.raises(ProductError) as rejected:
            bridge.prepare_local_transcription({})
        assert rejected.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"

    assert port.effect_counts() == {
        "probe": 0,
        "factory": 0,
        "recover": 0,
        "transcribe": 0,
        "finalize": 0,
        "slot_release": 0,
        "durable_row": 0,
    }


def test_v2_recoverable_positive_path_is_provider_zero_and_single_use(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("RECOVERABLE_PUBLICATION", make_v2_outcome(provider_started=False))
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    prepared = bridge.prepare_local_transcription_recovery({})
    result = bridge.recover_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert result["runtime_transcription"]["outcome"] == "READY_CPU"
    assert port.recovery_calls == 1
    assert port.calls == []
    assert port.finalize_calls == 1
    with pytest.raises(ProductError) as repeated:
        bridge.recover_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert repeated.value.code == "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID"
    assert port.recovery_calls == 1


def test_v2_verification_positive_path_is_distinct_provider_zero_action(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("VERIFICATION_ONLY", make_v2_outcome(provider_started=False))
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    prepared = bridge.prepare_local_transcription_verification({})
    result = bridge.verify_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert result["runtime_transcription"]["outcome"] == "READY_CPU"
    assert port.recovery_calls == 1
    assert port.calls == []


def test_v2_negative_and_stale_confirmation_have_zero_apply_effect(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("PENDING_ADMISSION", make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    cancelled = bridge.prepare_local_transcription({})
    assert bridge.cancel_local_transcription({"confirmation_id": cancelled["confirmation_id"]})["status"] == "CANCELLED"
    assert port.calls == []

    stale = bridge.prepare_local_transcription({})
    runtime.coordinator.bind_source(
        asset_id="ASSET-11111111111111111111111111", asset_sha256=sha("b"),
    )
    with pytest.raises(ProductError) as rejected:
        bridge.run_local_transcription({"confirmation_id": stale["confirmation_id"]})
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE"
    assert port.calls == []


def test_v2_projection_is_exact_and_invalid_outcome_cannot_bind_or_finalize(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort("PENDING_ADMISSION", make_v2_outcome())
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    prepared = bridge.prepare_local_transcription({})
    result = bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    projection = result["runtime_transcription"]
    assert set(projection) == {
        "requested_device", "outcome", "reason_code", "effective_device",
        "effective_compute_type", "fallback_applied", "model_download_authorized",
        "provider_configuration_from_javascript", "transcript_text_exposed", "host_path_exposed",
    }
    assert projection == {
        "requested_device": "cpu", "outcome": "READY_CPU",
        "reason_code": "REQUESTED_CPU_AVAILABLE", "effective_device": "cpu",
        "effective_compute_type": "int8", "fallback_applied": False,
        "model_download_authorized": False,
        "provider_configuration_from_javascript": False,
        "transcript_text_exposed": False, "host_path_exposed": False,
    }
    assert "private text" not in json.dumps(result)
    assert port.finalize_calls == 1
    request_copy = port.outcome.runtime_request_public
    request_copy["requested_device"] = "cuda"
    assert result["runtime_transcription"]["requested_device"] == "cpu"


@pytest.mark.parametrize(
    "invalid_kind",
    [
        "dict", "subclass", "extra_private", "all_none", "partial",
        "start_flags", "missing_finalizer",
    ],
)
def test_v2_invalid_outcome_is_rejected_before_binding_finalize_or_slot_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid_kind: str,
):
    tmp_path = tmp_path / invalid_kind
    tmp_path.mkdir()
    _, runtime, _, _, _ = make_runtime(tmp_path)
    valid = make_v2_outcome()
    if invalid_kind == "dict":
        invalid = {"runtime_request_public": {"private": "value"}}
    elif invalid_kind == "subclass":
        class OutcomeSubclass(RuntimeManagedLocalTranscriptionOutcomeV2):
            pass
        invalid = OutcomeSubclass(
            transcript=valid.transcript,
            provider_execution_started=valid.provider_execution_started,
            recovered_from_durable_result=valid.recovered_from_durable_result,
            operation_id=valid.operation_id,
            slot_operation_id=valid.slot_operation_id,
            publication_set_sha256=valid.publication_set_sha256,
            runtime_request=valid._runtime_request,
            runtime_decision=valid._runtime_decision,
        )
    elif invalid_kind == "extra_private":
        original = RuntimeManagedLocalTranscriptionOutcomeV2.runtime_request_public.fget
        assert original is not None
        monkeypatch.setattr(
            RuntimeManagedLocalTranscriptionOutcomeV2,
            "runtime_request_public",
            property(lambda self: {**original(self), "private": "value"}),
        )
        invalid = valid
    elif invalid_kind == "all_none":
        object.__setattr__(valid, "operation_id", None)
        object.__setattr__(valid, "slot_operation_id", None)
        object.__setattr__(valid, "publication_set_sha256", None)
        invalid = valid
    elif invalid_kind == "partial":
        object.__setattr__(valid, "slot_operation_id", None)
        invalid = valid
    elif invalid_kind == "start_flags":
        object.__setattr__(valid, "provider_execution_started", False)
        object.__setattr__(valid, "recovered_from_durable_result", True)
        invalid = valid
    else:
        invalid = valid
    port = RuntimeManagedPort("PENDING_ADMISSION", invalid)  # type: ignore[arg-type]
    if invalid_kind == "missing_finalizer":
        port.finalize_local_media_binding = None  # type: ignore[method-assign]
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    prepared = bridge.prepare_local_transcription({})
    bind_calls = 0
    binding_type = type(runtime.binding)
    original_bind = binding_type.bind_transcript_if_current

    def counting_bind(binding, *args, **kwargs):
        nonlocal bind_calls
        bind_calls += 1
        return original_bind(binding, *args, **kwargs)

    monkeypatch.setattr(binding_type, "bind_transcript_if_current", counting_bind)
    with pytest.raises(ProductError) as rejected:
        bridge.run_local_transcription({"confirmation_id": prepared["confirmation_id"]})
    assert rejected.value.code == "ERR_TASK098_RUNTIME_OUTCOME_INVALID"
    assert bind_calls == 0
    assert runtime.binding.transcript is None
    assert port.finalize_calls == 0
    assert port.slot_release_calls == 0


@pytest.mark.parametrize(
    ("classifier", "prepare_name", "apply_name"),
    [
        ("RECOVERABLE_PUBLICATION", "prepare_local_transcription_recovery", "recover_local_transcription"),
        ("VERIFICATION_ONLY", "prepare_local_transcription_verification", "verify_local_transcription"),
    ],
)
def test_v2_provider_zero_actions_reject_provider_execution_flags_before_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    classifier: str,
    prepare_name: str,
    apply_name: str,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    port = RuntimeManagedPort(classifier, make_v2_outcome(provider_started=True))
    runtime.transcription_port = port
    runtime.transcription_runtime_mode = "RUNTIME_MANAGED_V2"
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    prepared = getattr(bridge, prepare_name)({})
    bind_calls = 0
    binding_type = type(runtime.binding)
    original_bind = binding_type.bind_transcript_if_current

    def counting_bind(binding, *args, **kwargs):
        nonlocal bind_calls
        bind_calls += 1
        return original_bind(binding, *args, **kwargs)

    monkeypatch.setattr(binding_type, "bind_transcript_if_current", counting_bind)
    with pytest.raises(ProductError) as rejected:
        getattr(bridge, apply_name)({"confirmation_id": prepared["confirmation_id"]})
    assert rejected.value.code == "ERR_TASK098_RUNTIME_OUTCOME_INVALID"
    assert bind_calls == 0
    assert runtime.binding.transcript is None
    assert port.finalize_calls == 0
    assert port.slot_release_calls == 0


def test_trusted_factory_binds_post_review_runtime_after_cut_promotion(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    created = []

    class DownstreamRuntime:
        def __init__(self, application):
            self.application = application

        def status(self):
            return {
                "available": True,
                "next_recommended_action": self.application.coordinator.state.next_recommended_action,
                "host_paths_exposed": False,
            }

    def factory(application):
        value = DownstreamRuntime(application)
        created.append(value)
        return value

    bridge = Task036ShellBridge(
        runtime.coordinator.shell,
        pre_edit_runtime=runtime,
        workflow_runtime_factory=factory,
    )
    bridge.choose_and_ingest_media()
    run_transcription(bridge)
    bridge.create_runtime_subtitle_workspace()
    bridge.generate_runtime_cut_candidates()

    assert len(created) == 1
    assert created[0].application is runtime.application
    assert bridge.workflow_status()["next_recommended_action"] == "edit_plan.approve"


def test_subtitle_and_cut_bridge_results_are_closed_public_envelopes(tmp_path: Path):
    source, runtime, _, _, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)

    subtitle = bridge.create_runtime_subtitle_workspace({})
    assert set(subtitle) == {
        "task_owner", "operation", "status", "subtitle_workspace_sha256",
        "cue_count", "next_recommended_action", "provider_execution_started",
        "transcript_text_exposed", "host_path_exposed",
    }
    assert subtitle["status"] == "SUBTITLE_READY"
    assert subtitle["transcript_text_exposed"] is False
    assert subtitle["host_path_exposed"] is False

    cut = bridge.generate_runtime_cut_candidates({})
    assert set(cut) == {
        "task_owner", "operation", "status", "manifest_sha256",
        "candidate_count", "next_recommended_action", "provider_execution_started",
        "provider_configuration_from_javascript", "candidate_details_exposed",
        "host_path_exposed",
    }
    assert cut["status"] == "CUT_CANDIDATES_READY"
    assert cut["candidate_details_exposed"] is False
    assert cut["host_path_exposed"] is False
    public = json.dumps([subtitle, cut], ensure_ascii=False)
    assert str(source) not in public
    assert "hello" not in public
    assert "editing_session" not in public


def test_subtitle_stage_is_single_flight_and_drift_rejects_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)
    entered, release = Event(), Event()
    calls = 0
    original = runtime.binding.__class__.bind_subtitle_workspace_if_current

    def blocking(binding, workspace, **kwargs):
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(5)
        return original(binding, workspace, **kwargs)

    monkeypatch.setattr(runtime.binding.__class__, "bind_subtitle_workspace_if_current", blocking)
    errors: list[ProductError] = []

    def invoke() -> None:
        try:
            bridge.create_runtime_subtitle_workspace({})
        except ProductError as exc:
            errors.append(exc)

    worker = Thread(target=invoke)
    worker.start()
    assert entered.wait(5)
    with pytest.raises(ProductError) as parallel:
        bridge.create_runtime_subtitle_workspace({})
    assert parallel.value.code == "ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS"
    with pytest.raises(ProductError) as cross_action:
        bridge.generate_runtime_cut_candidates({})
    assert cross_action.value.code == "ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS"
    runtime.coordinator.bind_source(
        asset_id="ASSET-11111111111111111111111111",
        asset_sha256=sha("d"),
    )
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert calls == 1
    assert [error.code for error in errors] == ["ERR_TASK036_SUBTITLE_CONTEXT_STALE"]
    assert runtime.binding.subtitle_workspace is None
    assert runtime.coordinator.state.subtitle_workspace_sha256 is None


def test_cut_stage_is_single_flight_and_transcript_drift_rejects_application(tmp_path: Path):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)
    bridge.create_runtime_subtitle_workspace({})
    entered, release = Event(), Event()

    class BlockingCutPort(CutPort):
        def generate_cut_candidates(self, *, source_path: Path, transcript: TranscriptManifest):
            self.calls.append((source_path, transcript))
            entered.set()
            assert release.wait(5)
            return CutPort().generate_cut_candidates(source_path=source_path, transcript=transcript)

    cut = BlockingCutPort()
    runtime.cut_candidate_port = cut
    errors: list[ProductError] = []

    def invoke() -> None:
        try:
            bridge.generate_runtime_cut_candidates({})
        except ProductError as exc:
            errors.append(exc)

    worker = Thread(target=invoke)
    worker.start()
    assert entered.wait(5)
    with pytest.raises(ProductError) as parallel:
        bridge.generate_runtime_cut_candidates({})
    assert parallel.value.code == "ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS"
    runtime.coordinator.bind_transcript(sha("d"))
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert len(cut.calls) == 1
    assert [error.code for error in errors] == ["ERR_TASK036_CUT_CONTEXT_STALE"]
    assert runtime.application is None
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is None


def test_cut_generation_preserves_the_optional_subtitle_route(tmp_path: Path):
    _, runtime, _, _, cut = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)

    result = bridge.generate_runtime_cut_candidates({})
    assert result["status"] == "CUT_CANDIDATES_READY"
    assert len(cut.calls) == 1
    assert runtime.coordinator.state.subtitle_workspace_sha256 is None
    assert runtime.coordinator.state.next_recommended_action == "edit_plan.approve"


def test_subtitle_and_cut_bridges_reject_javascript_inputs_before_runtime(tmp_path: Path):
    _, runtime, _, _, cut = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)

    with pytest.raises(ProductError) as subtitle:
        bridge.create_runtime_subtitle_workspace({"transcript_text": "private"})
    with pytest.raises(ProductError) as candidate:
        bridge.generate_runtime_cut_candidates({"source_path": "C:/private/source.mp4"})
    assert subtitle.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert candidate.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert cut.calls == []
    assert runtime.binding.subtitle_workspace is None
    assert runtime.application is None


def test_cut_factory_failure_never_partially_promotes_and_retry_remains_available(
    tmp_path: Path,
):
    _, runtime, _, _, cut = make_runtime(tmp_path)

    class DownstreamRuntime:
        def __init__(self, application):
            self.application = application

        def status(self):
            return {"available": True}

    def failing_factory(application):
        raise RuntimeError("factory failed")

    bridge = Task036ShellBridge(
        runtime.coordinator.shell,
        pre_edit_runtime=runtime,
        workflow_runtime_factory=failing_factory,
    )
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)
    bridge.create_runtime_subtitle_workspace({})
    before = runtime.coordinator.state
    before_context = runtime.coordinator.shell.project.context_revision

    with pytest.raises(RuntimeError, match="factory failed"):
        bridge.generate_runtime_cut_candidates({})
    assert runtime.coordinator.state == before
    assert runtime.coordinator.shell.project.context_revision == before_context
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is None
    assert runtime.coordinator.state.next_recommended_action == "cut_candidates.generate"
    assert runtime.application is None
    assert runtime.promoted_workflow_runtime is None
    assert bridge._workflow_runtime is None

    bridge._workflow_runtime_factory = lambda application: DownstreamRuntime(object())
    with pytest.raises(ValueError, match="different editing application"):
        bridge.generate_runtime_cut_candidates({})
    assert runtime.coordinator.state == before
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is None
    assert runtime.application is None
    assert runtime.promoted_workflow_runtime is None

    class PublishingFactory:
        def __init__(self):
            self.prepared = []
            self.publisher_called = False

        def __call__(self, application):
            self.prepared.append(application)
            if len(self.prepared) == 1:
                runtime.coordinator.shell.bind_resolve_target(
                    resolve_project_name="drifted-project",
                    resolve_timeline_name="drifted-timeline",
                )
            return DownstreamRuntime(application)

        def publish(self, application, downstream_runtime):
            self.publisher_called = True
            raise AssertionError("publisher-like attributes are not part of the runtime contract")

    publishing_factory = PublishingFactory()
    bridge._workflow_runtime_factory = publishing_factory
    with pytest.raises(ProductError) as drifted:
        bridge.generate_runtime_cut_candidates({})
    assert drifted.value.code == "ERR_TASK036_CUT_CONTEXT_STALE"
    assert publishing_factory.publisher_called is False
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is None
    assert runtime.application is None
    assert runtime.promoted_workflow_runtime is None

    result = bridge.generate_runtime_cut_candidates({})
    assert result["status"] == "CUT_CANDIDATES_READY"
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is not None
    assert bridge._workflow_runtime is runtime.promoted_workflow_runtime
    assert publishing_factory.publisher_called is False
    assert len(cut.calls) == 4

def test_cut_commit_serializes_shell_context_mutation_with_state_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _, runtime, _, _, _ = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)
    bridge.choose_and_ingest_media({})
    run_transcription(bridge)
    entered, release = Event(), Event()
    original = EditingSessionState.bind_cut_candidates

    def blocking_bind(state, manifest_sha256):
        entered.set()
        assert release.wait(5)
        return original(state, manifest_sha256)

    monkeypatch.setattr(EditingSessionState, "bind_cut_candidates", blocking_bind)
    completed: list[dict] = []
    worker = Thread(target=lambda: completed.append(bridge.generate_runtime_cut_candidates({})))
    worker.start()
    assert entered.wait(5)

    mutation_started, mutation_completed = Event(), Event()

    def mutate_shell_context() -> None:
        mutation_started.set()
        runtime.coordinator.shell.bind_resolve_target(
            resolve_project_name="Sandbox",
            resolve_timeline_name="Timeline",
        )
        mutation_completed.set()

    mutator = Thread(target=mutate_shell_context)
    mutator.start()
    assert mutation_started.wait(5)
    assert not mutation_completed.wait(0.2)
    release.set()
    worker.join(5)
    mutator.join(5)
    assert not worker.is_alive() and not mutator.is_alive()
    assert completed[0]["status"] == "CUT_CANDIDATES_READY"
    assert mutation_completed.is_set()
    assert runtime.coordinator.state.cut_candidate_manifest_sha256 is not None
    assert runtime.coordinator.shell.project.resolve_timeline_name == "Timeline"
