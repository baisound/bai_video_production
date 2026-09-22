"""Trusted pre-edit composition for TASK-036.

The WebView chooses only an allowlisted stage action. Native paths and Product
ports remain Python-only runtime bindings and are never returned to JavaScript
or persisted in general Evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import re
import secrets
from threading import Lock
from time import monotonic
from typing import Any, Callable, Protocol

from .cut_candidates import CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_media_workflow import MediaIngestPort, Task036MediaWorkflowFacade
from .desktop_pre_edit_binding import Task036PreEditBinding
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .subtitles import TranscriptManifest
from .subtitle_workspace import SubtitleWorkspace
from .task036_native_dialog import Task036NativeDialogService


_RUNTIME_CONTROL_KEYS = (
    "control_mode", "phase", "cancel_state", "adjudication_state",
    "available_action", "status_label", "provider_execution_started",
    "provider_execution_known", "provider_stop_confirmed", "stop_evidence",
    "slot_release_allowed", "no_replay",
)
_RUNTIME_CONTROL_ACTIONS = {
    "NONE", "REQUEST_CANCEL",
    "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY",
}
_RUNTIME_CONTROL_PHASES = {
    "NOT_STARTED", "ADMISSION", "PROVIDER_STARTING", "PROVIDER_RUNNING",
    "PUBLICATION_VALIDATING", "PUBLICATION_COMMITTING", "COMPLETED",
    "UNKNOWN_AFTER_DISCONNECT", "BLOCKED",
}
_RUNTIME_CONTROL_CANCEL_STATES = {
    "NOT_REQUESTED", "CANCEL_REQUESTED", "CANCELLED_BEFORE_PROVIDER_EFFECT",
    "CANCELLED_AFTER_COOPERATIVE_BOUNDARY", "STOP_NOT_CONFIRMED",
}
_RUNTIME_CONTROL_ADJUDICATION_STATES = {
    "NOT_REQUIRED", "REQUIRED", "CLOSED_FAILED_NO_REPLAY",
}
_RUNTIME_CONTROL_STOP_EVIDENCE = {
    "NONE", "PRE_PROVIDER", "COOPERATIVE_CHECKPOINT", "HUMAN_ATTESTATION",
}
_RUNTIME_CONTROL_STATUS_LABELS = {
    "状態が不正なため操作できません", "結果の確定処理が開始されています",
    "キャンセル終了処理を安全に確定できません",
    "Human終了処理を安全に確定できません", "Provider開始前にキャンセルしました",
    "協調停止を確認してキャンセルしました",
    "Human確認により失敗終了しました（再実行なし）",
    "キャンセルを要求しました。停止確認中です", "Provider停止を確認できません",
    "Provider停止のHuman確認が必要です", "既存結果の復旧が必要です",
    "音声認識は完了しています", "実行許可を確認中です",
    "音声認識を開始しています", "音声認識を実行中です", "結果を検証中です",
    "結果確定の排他状態を確認できません", "実行状態を確認できません",
    "開始待ちです", "音声認識は開始されていません", "失敗状態を確認してください",
}


def _runtime_control_signature(
    phase: str, cancel: str, adjudication: str, action: str, label: str,
    started: bool, known: bool, stopped: bool = False,
    evidence: str = "NONE", release: bool = False,
) -> tuple[Any, ...]:
    return (
        phase, cancel, adjudication, action, label, started, known, stopped,
        evidence, release,
    )


_RUNTIME_CONTROL_EXACT_ROWS = frozenset({
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "状態が不正なため操作できません", False, False),
    _runtime_control_signature("PUBLICATION_COMMITTING", "NOT_REQUESTED", "NOT_REQUIRED", "NONE", "結果の確定処理が開始されています", True, True),
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "キャンセル終了処理を安全に確定できません", False, False),
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "REQUIRED", "NONE", "Human終了処理を安全に確定できません", False, False, evidence="HUMAN_ATTESTATION"),
    _runtime_control_signature("BLOCKED", "CANCELLED_BEFORE_PROVIDER_EFFECT", "NOT_REQUIRED", "NONE", "Provider開始前にキャンセルしました", False, True, True, "PRE_PROVIDER", True),
    _runtime_control_signature("BLOCKED", "CANCELLED_AFTER_COOPERATIVE_BOUNDARY", "NOT_REQUIRED", "NONE", "協調停止を確認してキャンセルしました", True, True, True, "COOPERATIVE_CHECKPOINT", True),
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "CLOSED_FAILED_NO_REPLAY", "NONE", "Human確認により失敗終了しました（再実行なし）", False, False, evidence="HUMAN_ATTESTATION", release=True),
    _runtime_control_signature("UNKNOWN_AFTER_DISCONNECT", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "Provider停止を確認できません", False, True),
    _runtime_control_signature("UNKNOWN_AFTER_DISCONNECT", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "Provider停止を確認できません", True, True),
    _runtime_control_signature("UNKNOWN_AFTER_DISCONNECT", "STOP_NOT_CONFIRMED", "REQUIRED", "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY", "Provider停止のHuman確認が必要です", False, False),
    _runtime_control_signature("PUBLICATION_COMMITTING", "NOT_REQUESTED", "NOT_REQUIRED", "NONE", "既存結果の復旧が必要です", True, True),
    _runtime_control_signature("COMPLETED", "NOT_REQUESTED", "NOT_REQUIRED", "NONE", "音声認識は完了しています", True, True),
    _runtime_control_signature("ADMISSION", "NOT_REQUESTED", "NOT_REQUIRED", "REQUEST_CANCEL", "実行許可を確認中です", False, True),
    _runtime_control_signature("PROVIDER_STARTING", "NOT_REQUESTED", "NOT_REQUIRED", "REQUEST_CANCEL", "音声認識を開始しています", False, True),
    _runtime_control_signature("PROVIDER_RUNNING", "NOT_REQUESTED", "NOT_REQUIRED", "REQUEST_CANCEL", "音声認識を実行中です", True, True),
    _runtime_control_signature("PUBLICATION_VALIDATING", "NOT_REQUESTED", "NOT_REQUIRED", "REQUEST_CANCEL", "結果を検証中です", True, True),
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "結果確定の排他状態を確認できません", True, True),
    _runtime_control_signature("UNKNOWN_AFTER_DISCONNECT", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "実行状態を確認できません", False, False),
    _runtime_control_signature("NOT_STARTED", "NOT_REQUESTED", "NOT_REQUIRED", "NONE", "開始待ちです", False, True),
    _runtime_control_signature("NOT_STARTED", "NOT_REQUESTED", "NOT_REQUIRED", "NONE", "音声認識は開始されていません", False, True),
    _runtime_control_signature("BLOCKED", "STOP_NOT_CONFIRMED", "NOT_REQUIRED", "NONE", "失敗状態を確認してください", False, False),
    *(
        _runtime_control_signature(
            phase, "CANCEL_REQUESTED", "NOT_REQUIRED", "NONE",
            "キャンセルを要求しました。停止確認中です",
            phase in {"PROVIDER_RUNNING", "PUBLICATION_VALIDATING"},
            phase != "UNKNOWN_AFTER_DISCONNECT",
        )
        for phase in (
            "ADMISSION", "PROVIDER_STARTING", "PROVIDER_RUNNING",
            "PUBLICATION_VALIDATING", "UNKNOWN_AFTER_DISCONNECT",
        )
    ),
})


def _blocked_runtime_control() -> dict[str, Any]:
    return {
        "control_mode": "PHASE_ONLY_V1",
        "phase": "BLOCKED",
        "cancel_state": "STOP_NOT_CONFIRMED",
        "adjudication_state": "NOT_REQUIRED",
        "available_action": "NONE",
        "status_label": "状態が不正なため操作できません",
        "provider_execution_started": False,
        "provider_execution_known": False,
        "provider_stop_confirmed": False,
        "stop_evidence": "NONE",
        "slot_release_allowed": False,
        "no_replay": True,
    }


def _validate_runtime_control_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or tuple(value) != _RUNTIME_CONTROL_KEYS:
        raise ValueError("runtime control projection keys are invalid")
    if (
        value["control_mode"] != "PHASE_ONLY_V1"
        or value["available_action"] not in _RUNTIME_CONTROL_ACTIONS
        or value["phase"] not in _RUNTIME_CONTROL_PHASES
        or value["cancel_state"] not in _RUNTIME_CONTROL_CANCEL_STATES
        or value["adjudication_state"] not in _RUNTIME_CONTROL_ADJUDICATION_STATES
        or value["status_label"] not in _RUNTIME_CONTROL_STATUS_LABELS
        or value["stop_evidence"] not in _RUNTIME_CONTROL_STOP_EVIDENCE
        or any(type(value[key]) is not bool for key in (
            "provider_execution_started", "provider_execution_known",
            "provider_stop_confirmed", "slot_release_allowed", "no_replay",
        ))
        or value["no_replay"] is not True
    ):
        raise ValueError("runtime control projection values are invalid")
    signature = _runtime_control_signature(
        value["phase"], value["cancel_state"], value["adjudication_state"],
        value["available_action"], value["status_label"],
        value["provider_execution_started"], value["provider_execution_known"],
        value["provider_stop_confirmed"], value["stop_evidence"],
        value["slot_release_allowed"],
    )
    if signature not in _RUNTIME_CONTROL_EXACT_ROWS:
        raise ValueError("runtime control projection row is invalid")
    return {key: value[key] for key in _RUNTIME_CONTROL_KEYS}


@dataclass(frozen=True, slots=True)
class LocalTranscriptionOutcome:
    transcript: TranscriptManifest
    provider_execution_started: bool
    recovered_from_durable_result: bool = False
    operation_id: str | None = None
    slot_operation_id: str | None = None
    publication_set_sha256: str | None = None


class LocalTranscriptionPort(Protocol):
    def transcribe_local_media(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> LocalTranscriptionOutcome: ...

    def recover_local_media(
        self,
        *,
        project_id: str,
        source_path: Path,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> LocalTranscriptionOutcome: ...

    def recovery_required(
        self,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
    ) -> bool: ...

    def finalize_local_media_binding(
        self,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        transcript_manifest_sha256: str,
        operation_id: str,
        slot_operation_id: str,
        publication_set_sha256: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class _PendingTranscription:
    confirmation_id: str
    project_id: str
    session_revision: int
    source_asset_id: str
    source_asset_sha256: str
    source_path: Path
    context_revision: int
    action: str = "START"

    @property
    def recovery(self) -> bool:
        return self.action == "RECOVER"


@dataclass(frozen=True, slots=True)
class _PendingRuntimeTranscriptionControl:
    confirmation_id: str
    project_id: str
    session_revision: int
    source_asset_id: str
    source_asset_sha256: str
    source_path: Path
    context_revision: int
    action: str
    public_projection: tuple[tuple[str, Any], ...]
    private_snapshot: Any
    prepared_at: float


@dataclass(frozen=True, slots=True)
class _PreEditCoordinate:
    project_id: str
    session_revision: int
    source_asset_id: str
    source_asset_sha256: str
    source_path: Path
    transcript_sha256: str
    subtitle_workspace_sha256: str | None
    context_revision: int
    transcript: TranscriptManifest


class CutCandidateGenerationPort(Protocol):
    def generate_cut_candidates(
        self,
        *,
        source_path: Path,
        transcript: TranscriptManifest,
    ) -> CutCandidateManifest: ...


class SpeechCueGenerationPort(Protocol):
    def snapshot(self, transcript: TranscriptManifest | None) -> dict[str, Any]: ...

    def generate(
        self,
        *,
        project_id: str,
        transcript: TranscriptManifest,
    ) -> dict[str, Any]: ...

    def prepare_human_decision(
        self,
        *,
        transcript: TranscriptManifest,
        cue_id: str,
        decision: str,
    ) -> dict[str, Any]: ...

    def apply_human_decision(
        self,
        *,
        transcript: TranscriptManifest,
        confirmation_id: str,
    ) -> dict[str, Any]: ...

    def cancel_human_decision(self, *, confirmation_id: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class Task036PreEditRuntime:
    """Compose Media, local ASR, Subtitle and Cut services behind one gate."""

    coordinator: DesktopEditingCoordinator
    native_dialog: Task036NativeDialogService
    ingest_port: MediaIngestPort
    transcription_port: LocalTranscriptionPort
    cut_candidate_port: CutCandidateGenerationPort
    speech_cue_port: SpeechCueGenerationPort | None = None
    transcription_runtime_mode: str = "LEGACY_V1"
    confirmation_clock: Callable[[], float] = monotonic
    media: Task036MediaWorkflowFacade = field(init=False)
    binding: Task036PreEditBinding = field(init=False)
    application: Task036EditingApplication | None = field(default=None, init=False)
    _promoted_workflow_runtime: Any | None = field(default=None, init=False, repr=False)
    _transcription_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _pre_edit_stage_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _confirmation_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _transcription_confirmations: dict[str, _PendingTranscription] = field(default_factory=dict, init=False, repr=False)
    _runtime_control_confirmations: dict[str, _PendingRuntimeTranscriptionControl] = field(default_factory=dict, init=False, repr=False)
    _runtime_control_last_clock: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.transcription_runtime_mode not in {"LEGACY_V1", "RUNTIME_MANAGED_V2"}:
            raise ValueError("transcription_runtime_mode is invalid")
        if not callable(self.confirmation_clock):
            raise TypeError("confirmation_clock must be callable")
        self.media = Task036MediaWorkflowFacade(self.coordinator, self.native_dialog, self.ingest_port)
        self.binding = Task036PreEditBinding(self.coordinator)

    def status(self) -> dict[str, Any]:
        state = self.coordinator.state
        if self.transcription_runtime_mode == "RUNTIME_MANAGED_V2":
            return self._runtime_managed_status()
        recovery_required = False
        if state.source_asset_id is not None and state.source_asset_sha256 is not None and self.media.runtime_source_path is not None:
            status_reader = getattr(self.transcription_port, "recovery_required", None)
            if callable(status_reader):
                recovery_required = bool(
                    status_reader(
                        state.project_id,
                        state.source_asset_id,
                        state.source_asset_sha256,
                    )
                )
        return {
            "available": True,
            "task_owner": "TASK-036",
            "next_recommended_action": state.next_recommended_action,
            "current_stage": state.current_stage.value,
            "source_bound": state.source_asset_id is not None,
            "transcript_bound": state.transcript_sha256 is not None,
            "subtitle_workspace_bound": state.subtitle_workspace_sha256 is not None,
            "cut_candidates_bound": state.cut_candidate_manifest_sha256 is not None,
            "review_application_bound": self.application is not None,
            "host_paths_exposed": False,
            "provider_configuration_from_javascript": False,
            "transcription_recovery_required": recovery_required,
            "speech_cues": self.speech_cue_snapshot(),
        }

    def _runtime_managed_status(self) -> dict[str, Any]:
        state = self.coordinator.state
        source_bound = (
            state.source_asset_id is not None
            and state.source_asset_sha256 is not None
            and self.media.runtime_source_path is not None
        )
        recovery_state: str | None = None
        if source_bound:
            reader = getattr(self.transcription_port, "recovery_state", None)
            try:
                observed = reader(
                    project_id=state.project_id,
                    source_asset_id=state.source_asset_id,
                    source_asset_sha256=state.source_asset_sha256,
                ) if callable(reader) else None
            except Exception:
                observed = None
            known = {
                "PENDING_ADMISSION", "RECOVERABLE_PUBLICATION", "VERIFICATION_ONLY",
                "ACTIVE_UNKNOWN", "ADJUDICATION_REQUIRED_NO_PUBLICATION",
                "FAILED_TERMINAL", "CORRUPT_BLOCKED",
            }
            recovery_state = observed if type(observed) is str and observed in known else "CORRUPT_BLOCKED"
        labels = {
            "PENDING_ADMISSION": "文字起こしを開始できます",
            "RECOVERABLE_PUBLICATION": "文字起こし結果を復旧できます",
            "VERIFICATION_ONLY": "文字起こし結果を検証できます",
            "ACTIVE_UNKNOWN": "文字起こし処理の状態を確認できません",
            "ADJUDICATION_REQUIRED_NO_PUBLICATION": "人による確認が必要です",
            "FAILED_TERMINAL": "文字起こしは失敗しました",
            "CORRUPT_BLOCKED": "文字起こし状態が破損しているため停止しました",
        }
        action = "NONE"
        label = None if recovery_state is None else labels[recovery_state]
        transcription_stage = (
            source_bound
            and state.transcript_sha256 is None
            and state.next_recommended_action == "transcription.start"
        )
        if transcription_stage:
            action = {
                "PENDING_ADMISSION": "START",
                "RECOVERABLE_PUBLICATION": "RECOVER",
                "VERIFICATION_ONLY": "VERIFY",
            }.get(recovery_state, "NONE")
        elif recovery_state == "VERIFICATION_ONLY":
            label = "文字起こし結果は検証済みです"
        control = _blocked_runtime_control()
        if source_bound:
            capture = getattr(
                self.transcription_port,
                "capture_runtime_transcription_control",
                None,
            )
            try:
                snapshot = capture(
                    project_id=state.project_id,
                    source_asset_id=state.source_asset_id,
                    source_asset_sha256=state.source_asset_sha256,
                ) if callable(capture) else None
                projection_reader = getattr(snapshot, "public_projection", None)
                control = _validate_runtime_control_projection(
                    projection_reader() if callable(projection_reader) else None,
                )
            except Exception:
                control = _blocked_runtime_control()
        nested_action = control["available_action"]
        if action != "NONE" and nested_action != "NONE":
            action = "NONE"
            label = "文字起こし制御状態が競合しているため停止しました"
            control = _blocked_runtime_control()
        return {
            "available": True,
            "task_owner": "TASK-036",
            "next_recommended_action": state.next_recommended_action,
            "current_stage": state.current_stage.value,
            "source_bound": state.source_asset_id is not None,
            "transcript_bound": state.transcript_sha256 is not None,
            "subtitle_workspace_bound": state.subtitle_workspace_sha256 is not None,
            "cut_candidates_bound": state.cut_candidate_manifest_sha256 is not None,
            "review_application_bound": self.application is not None,
            "host_paths_exposed": False,
            "provider_configuration_from_javascript": False,
            "transcription_runtime_mode": "RUNTIME_MANAGED_V2",
            "transcription_recovery_state": recovery_state,
            "transcription_available_action": action,
            "transcription_status_label": label,
            "transcription_control": control,
            "speech_cues": self.speech_cue_snapshot(),
        }

    def speech_cue_snapshot(self) -> dict[str, Any]:
        if self.speech_cue_port is None:
            return {"available": False, "task_owner": "TASK-056"}
        return self.speech_cue_port.snapshot(self.binding.transcript)

    def generate_speech_cues(self) -> dict[str, Any]:
        if self.speech_cue_port is None:
            raise ProductError(
                "ERR_TASK056_PRODUCT_INTEGRATION_NOT_BOUND",
                "TASK-056 Product integration is not bound",
                ProductErrorCategory.STATE,
            )
        transcript = self.binding.transcript
        if transcript is None:
            raise ProductError(
                "ERR_TASK056_TRANSCRIPT_NOT_BOUND",
                "Speech cue generation requires the bound Product Transcript",
                ProductErrorCategory.STATE,
            )
        result = self.speech_cue_port.generate(
            project_id=self.coordinator.state.project_id,
            transcript=transcript,
        )
        if (
            not isinstance(result, dict)
            or result.get("available") is not True
            or result.get("generated") is not True
            or result.get("task_owner") != "TASK-056"
            or result.get("transcript_text_exposed") is not False
            or result.get("host_path_exposed") is not False
            or result.get("canonical_timeline") is not False
            or result.get("auto_apply_authorized") is not False
        ):
            raise ProductError(
                "ERR_TASK056_PRODUCT_RESULT_INVALID",
                "TASK-056 Product integration returned an invalid result",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return result

    def prepare_speech_cue_decision(
        self,
        *,
        cue_id: str,
        decision: str,
    ) -> dict[str, Any]:
        if self.speech_cue_port is None:
            raise ProductError(
                "ERR_TASK056_PRODUCT_INTEGRATION_NOT_BOUND",
                "TASK-056 Product integration is not bound",
                ProductErrorCategory.STATE,
            )
        transcript = self.binding.transcript
        if transcript is None:
            raise ProductError(
                "ERR_TASK056_TRANSCRIPT_NOT_BOUND",
                "Speech cue review requires the bound Product Transcript",
                ProductErrorCategory.STATE,
            )
        return self.speech_cue_port.prepare_human_decision(
            transcript=transcript,
            cue_id=cue_id,
            decision=decision,
        )

    def cancel_speech_cue_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        if self.speech_cue_port is None:
            raise ProductError(
                "ERR_TASK056_PRODUCT_INTEGRATION_NOT_BOUND",
                "TASK-056 Product integration is not bound",
                ProductErrorCategory.STATE,
            )
        result = self.speech_cue_port.cancel_human_decision(
            confirmation_id=confirmation_id,
        )
        if (
            not isinstance(result, dict)
            or result.get("status") != "HUMAN_DECISION_CANCELLED"
            or result.get("task_owner") != "TASK-056"
            or result.get("decision_persisted") is not False
            or result.get("confirmation_token_persisted") is not False
            or result.get("canonical_timeline") is not False
            or result.get("auto_apply_authorized") is not False
        ):
            raise ProductError(
                "ERR_TASK056_HUMAN_DECISION_RESULT_INVALID",
                "TASK-056 Human decision cancellation violated Product boundaries",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return result

    def apply_speech_cue_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        if self.speech_cue_port is None:
            raise ProductError(
                "ERR_TASK056_PRODUCT_INTEGRATION_NOT_BOUND",
                "TASK-056 Product integration is not bound",
                ProductErrorCategory.STATE,
            )
        transcript = self.binding.transcript
        if transcript is None:
            raise ProductError(
                "ERR_TASK056_TRANSCRIPT_NOT_BOUND",
                "Speech cue review requires the bound Product Transcript",
                ProductErrorCategory.STATE,
            )
        result = self.speech_cue_port.apply_human_decision(
            transcript=transcript,
            confirmation_id=confirmation_id,
        )
        if (
            not isinstance(result, dict)
            or result.get("status") != "HUMAN_DECISION_RECORDED"
            or result.get("task_owner") != "TASK-056"
            or result.get("confirmation_token_persisted") is not False
            or result.get("transcript_text_exposed") is not False
            or result.get("host_path_exposed") is not False
            or result.get("canonical_timeline") is not False
            or result.get("auto_apply_authorized") is not False
        ):
            raise ProductError(
                "ERR_TASK056_HUMAN_DECISION_RESULT_INVALID",
                "TASK-056 Human decision result violated Product boundaries",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return result

    def choose_and_ingest_media(self) -> dict[str, Any]:
        return self.media.choose_and_ingest()

    def _finalize_transcription_binding(
        self,
        outcome: LocalTranscriptionOutcome,
        *,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        transcript_manifest_sha256: str,
    ) -> None:
        coordinates = (
            outcome.operation_id,
            outcome.slot_operation_id,
            outcome.publication_set_sha256,
        )
        if coordinates == (None, None, None):
            return
        if not all(isinstance(item, str) and item for item in coordinates):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable transcription binding coordinates are incomplete",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        finalizer = getattr(self.transcription_port, "finalize_local_media_binding", None)
        if not callable(finalizer):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID",
                "Durable transcription port cannot finalize its output slot",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        finalizer(
            project_id=project_id,
            source_asset_id=source_asset_id,
            source_asset_sha256=source_asset_sha256,
            transcript_manifest_sha256=transcript_manifest_sha256,
            operation_id=outcome.operation_id,
            slot_operation_id=outcome.slot_operation_id,
            publication_set_sha256=outcome.publication_set_sha256,
        )

    def _validate_runtime_managed_outcome(
        self,
        outcome: Any,
        *,
        action: str,
    ) -> dict[str, Any] | None:
        """Reject every untrusted v2 return before Product binding/finalization."""

        if self.transcription_runtime_mode != "RUNTIME_MANAGED_V2":
            return None
        # Local import avoids reversing task036_product_ports -> pre-edit runtime.
        from .task036_product_ports import RuntimeManagedLocalTranscriptionOutcomeV2

        if (
            type(outcome) is not RuntimeManagedLocalTranscriptionOutcomeV2
            or type(outcome.transcript) is not TranscriptManifest
            or action not in {"START", "RECOVER", "VERIFY"}
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_OUTCOME_INVALID",
                "Runtime-managed transcription returned an invalid outcome type",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        coordinates = (
            outcome.operation_id,
            outcome.slot_operation_id,
            outcome.publication_set_sha256,
        )
        try:
            if (
                not all(type(value) is str for value in coordinates)
                or not all(value for value in coordinates)
                or validate_id(outcome.operation_id, IdKind.OPERATION) != outcome.operation_id
                or validate_id(outcome.slot_operation_id, IdKind.OPERATION) != outcome.slot_operation_id
                or re.fullmatch(r"sha256:[0-9a-f]{64}", outcome.publication_set_sha256) is None
            ):
                raise ValueError("runtime outcome coordinates are invalid")
        except (TypeError, ValueError):
            raise ProductError(
                "ERR_TASK098_RUNTIME_OUTCOME_INVALID",
                "Runtime-managed transcription binding coordinates are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from None
        expected_flags = (True, False) if action == "START" else (False, True)
        if (
            type(outcome.provider_execution_started) is not bool
            or type(outcome.recovered_from_durable_result) is not bool
            or (
                outcome.provider_execution_started,
                outcome.recovered_from_durable_result,
            ) != expected_flags
            or not callable(getattr(self.transcription_port, "finalize_local_media_binding", None))
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_OUTCOME_INVALID",
                "Runtime-managed transcription outcome violates its action contract",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            request = dict(outcome.runtime_request_public)
            decision = dict(outcome.runtime_decision_public)
        except Exception as exc:
            raise ProductError(
                "ERR_TASK098_RUNTIME_OUTCOME_INVALID",
                "Runtime-managed transcription metadata is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        request_keys = {
            "record_type", "schema_version", "requested_device", "compute_policy",
            "model_download_authorized",
        }
        decision_keys = {
            "record_type", "schema_version", "outcome", "reason_code",
            "effective_device", "effective_compute_type", "fallback_applied",
            "model_load_started", "inference_started", "partial_output_present",
            "execution_authorized",
        }
        expected = {
            ("cpu", "READY_CPU", "REQUESTED_CPU_AVAILABLE"): ("cpu", "int8", False),
            ("cuda", "READY_CUDA", "REQUESTED_CUDA_AVAILABLE"): ("cuda", "float16", False),
            ("auto", "READY_CUDA", "AUTO_CUDA_AVAILABLE"): ("cuda", "float16", False),
            ("auto", "READY_CPU", "AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE"): ("cpu", "int8", True),
        }
        key = (request.get("requested_device"), decision.get("outcome"), decision.get("reason_code"))
        if (
            set(request) != request_keys
            or set(decision) != decision_keys
            or request.get("record_type") != "FasterWhisperRuntimeRequestV1"
            or request.get("schema_version") != "1.0.0"
            or request.get("compute_policy") != "UWR_BALANCED_V1"
            or request.get("model_download_authorized") is not False
            or decision.get("record_type") != "FasterWhisperRuntimeDecisionV1"
            or decision.get("schema_version") != "1.0.0"
            or any(
                type(value) is not str
                for value in (
                    request.get("record_type"), request.get("schema_version"),
                    request.get("requested_device"), request.get("compute_policy"),
                    decision.get("record_type"), decision.get("schema_version"),
                    decision.get("outcome"), decision.get("reason_code"),
                    decision.get("effective_device"),
                    decision.get("effective_compute_type"),
                )
            )
            or type(decision.get("fallback_applied")) is not bool
            or any(decision.get(flag) is not False for flag in (
                "model_load_started", "inference_started", "partial_output_present",
                "execution_authorized",
            ))
            or key not in expected
            or (
                decision.get("effective_device"),
                decision.get("effective_compute_type"),
                decision.get("fallback_applied"),
            ) != expected[key]
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_OUTCOME_INVALID",
                "Runtime-managed transcription metadata is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return {
            "requested_device": request["requested_device"],
            "outcome": decision["outcome"],
            "reason_code": decision["reason_code"],
            "effective_device": decision["effective_device"],
            "effective_compute_type": decision["effective_compute_type"],
            "fallback_applied": decision["fallback_applied"],
            "model_download_authorized": False,
            "provider_configuration_from_javascript": False,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
        }

    def _prepare_runtime_transcription_action(self, action: str) -> dict[str, Any]:
        status = self._runtime_managed_status()
        if status["transcription_available_action"] != action:
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                "Runtime-managed transcription action is not available",
                ProductErrorCategory.AUTHORIZATION,
            )
        with self._confirmation_lock:
            if len(self._transcription_confirmations) >= 256:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_CAPACITY",
                    "Too many local transcription confirmations are pending",
                    ProductErrorCategory.STATE,
                )
            state = self.coordinator.state
            source_path = self.media.runtime_source_path
            project = self.coordinator.shell.project
            if (
                state.source_asset_id is None or state.source_asset_sha256 is None
                or source_path is None or project is None
                or state.next_recommended_action != "transcription.start"
            ):
                raise ProductError(
                    "ERR_TASK036_RUNTIME_SOURCE_NOT_BOUND",
                    "Runtime-managed transcription requires the exact source binding",
                    ProductErrorCategory.STATE,
                )
            token = secrets.token_urlsafe(24)
            if token in self._transcription_confirmations:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_CONFLICT",
                    "Local transcription confirmation identity collided",
                    ProductErrorCategory.STATE,
                )
            self._transcription_confirmations[token] = _PendingTranscription(
                token, state.project_id, state.revision, state.source_asset_id,
                state.source_asset_sha256, source_path, project.context_revision, action,
            )
        return {
            "task_owner": "TASK-036",
            "operation": "LOCAL_TRANSCRIPTION_PREPARE",
            "confirmation_id": token,
            "project_id": state.project_id,
            "source_asset_id": state.source_asset_id,
            "source_asset_sha256": state.source_asset_sha256,
            "provider_execution_mode": "LOCAL",
            "model_download_authorized": False,
            "provider_execution_started": False,
            "transcription_runtime_mode": "RUNTIME_MANAGED_V2",
            "transcription_action": action,
            "transcription_status_label": status["transcription_status_label"],
            "recovery": action == "RECOVER",
        }

    def _runtime_control_now(self) -> float:
        value = self.confirmation_clock()
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0.0
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_CONTROL_CLOCK_INVALID",
                "Runtime control confirmation clock is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        observed = float(value)
        if (
            self._runtime_control_last_clock is not None
            and observed < self._runtime_control_last_clock
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_CONTROL_CLOCK_INVALID",
                "Runtime control confirmation clock regressed",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        self._runtime_control_last_clock = observed
        return observed

    def _purge_runtime_control_confirmations(self, now: float) -> None:
        expired = [
            token for token, pending in self._runtime_control_confirmations.items()
            if now - pending.prepared_at >= 300.0
        ]
        for token in expired:
            self._runtime_control_confirmations.pop(token, None)

    def _require_runtime_control_coordinate(self) -> tuple[Any, Path, Any]:
        state = self.coordinator.state
        source_path = self.media.runtime_source_path
        project = self.coordinator.shell.project
        if (
            self.transcription_runtime_mode != "RUNTIME_MANAGED_V2"
            or state.source_asset_id is None
            or state.source_asset_sha256 is None
            or source_path is None
            or project is None
            or state.next_recommended_action != "transcription.start"
        ):
            raise ProductError(
                "ERR_TASK098_RUNTIME_CONTROL_NOT_AVAILABLE",
                "Runtime transcription control requires the exact source stage",
                ProductErrorCategory.AUTHORIZATION,
            )
        return state, source_path, project

    def prepare_runtime_transcription_control(self) -> dict[str, Any]:
        with self._confirmation_lock:
            state, source_path, project = self._require_runtime_control_coordinate()
            top = self._runtime_managed_status()
            if top["transcription_available_action"] != "NONE":
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_ROUTE_CONFLICT",
                    "Runtime control cannot shadow START, RECOVER, or VERIFY",
                    ProductErrorCategory.AUTHORIZATION,
                )
            capture_reader = getattr(
                self.transcription_port,
                "capture_runtime_transcription_control",
                None,
            )
            if not callable(capture_reader):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_NOT_BOUND",
                    "Runtime transcription control port is not bound",
                    ProductErrorCategory.STATE,
                )
            snapshot = capture_reader(
                project_id=state.project_id,
                source_asset_id=state.source_asset_id,
                source_asset_sha256=state.source_asset_sha256,
            )
            projection_reader = getattr(snapshot, "public_projection", None)
            try:
                projection = _validate_runtime_control_projection(
                    projection_reader() if callable(projection_reader) else None,
                )
            except ValueError as exc:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_INVALID",
                    "Runtime transcription control projection is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            action = projection["available_action"]
            if action not in {
                "REQUEST_CANCEL",
                "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY",
            } or top["transcription_control"] != projection:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_NOT_AVAILABLE",
                    "Runtime transcription control action is not available",
                    ProductErrorCategory.AUTHORIZATION,
                )
            if (
                action == "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY"
                and getattr(snapshot, "active_worker_coordinate", None) is not None
            ):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_WORKER_ACTIVE",
                    "Human closure is unavailable while the exact worker is active",
                    ProductErrorCategory.AUTHORIZATION,
                )
            now = self._runtime_control_now()
            self._purge_runtime_control_confirmations(now)
            if len(self._runtime_control_confirmations) >= 256:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_CAPACITY",
                    "Too many runtime control confirmations are pending",
                    ProductErrorCategory.STATE,
                )
            token = secrets.token_urlsafe(24)
            if not 0 < len(token) <= 256 or token in self._runtime_control_confirmations:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_CONFLICT",
                    "Runtime control confirmation identity collided",
                    ProductErrorCategory.STATE,
                )
            self._runtime_control_confirmations[token] = _PendingRuntimeTranscriptionControl(
                confirmation_id=token,
                project_id=state.project_id,
                session_revision=state.revision,
                source_asset_id=state.source_asset_id,
                source_asset_sha256=state.source_asset_sha256,
                source_path=source_path,
                context_revision=project.context_revision,
                action=action,
                public_projection=tuple(
                    (key, projection[key]) for key in _RUNTIME_CONTROL_KEYS
                ),
                private_snapshot=snapshot,
                prepared_at=now,
            )
        warning = (
            "キャンセル要求は停止完了の証明ではありません。協調停止が確認されるまで停止確認中のままです。"
            if action == "REQUEST_CANCEL"
            else "この操作は音声を復旧せず、文字起こし成功も宣言しません。Provider停止をHuman確認し、再実行なしで失敗終了を確定します。"
        )
        return {
            "task_owner": "TASK-098",
            "operation": "RUNTIME_TRANSCRIPTION_CONTROL_PREPARE",
            "confirmation_id": token,
            "action": action,
            "status_label": projection["status_label"],
            "warning": warning,
            "expires_in_seconds": 300,
        }

    def apply_runtime_transcription_control(
        self, confirmation_id: str,
    ) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._runtime_control_confirmations.pop(confirmation_id, None)
            if pending is None:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_MISSING",
                    "Runtime control confirmation is missing or already consumed",
                    ProductErrorCategory.AUTHORIZATION,
                )
            now = self._runtime_control_now()
            if now - pending.prepared_at >= 300.0:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_EXPIRED",
                    "Runtime control confirmation expired",
                    ProductErrorCategory.AUTHORIZATION,
                )
            state, source_path, project = self._require_runtime_control_coordinate()
            if (
                state.project_id != pending.project_id
                or state.revision != pending.session_revision
                or state.source_asset_id != pending.source_asset_id
                or state.source_asset_sha256 != pending.source_asset_sha256
                or source_path is not pending.source_path
                or project.context_revision != pending.context_revision
            ):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_STALE",
                    "Runtime control confirmation no longer binds the source context",
                    ProductErrorCategory.AUTHORIZATION,
                )
            status = self._runtime_managed_status()
            if (
                status["transcription_available_action"] != "NONE"
                or status["transcription_control"]
                != dict(pending.public_projection)
                or status["transcription_control"]["available_action"]
                != pending.action
            ):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_STALE",
                    "Runtime control action changed after confirmation",
                    ProductErrorCategory.AUTHORIZATION,
                )
            apply = getattr(
                self.transcription_port,
                "apply_runtime_transcription_control",
                None,
            )
            if not callable(apply):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_NOT_BOUND",
                    "Runtime transcription control port is not bound",
                    ProductErrorCategory.STATE,
                )
            result = apply(
                pending.private_snapshot,
                action=pending.action,
                project_id=pending.project_id,
                source_asset_id=pending.source_asset_id,
                source_asset_sha256=pending.source_asset_sha256,
            )
            try:
                projection = _validate_runtime_control_projection(result)
            except ValueError as exc:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_INVALID",
                    "Runtime transcription control result is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            return {
                "task_owner": "TASK-098",
                "status": "RUNTIME_TRANSCRIPTION_CONTROL_APPLIED",
                "transcription_control": projection,
            }

    def cancel_runtime_transcription_control(
        self, confirmation_id: str,
    ) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._runtime_control_confirmations.pop(confirmation_id, None)
            if pending is None:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_MISSING",
                    "Runtime control confirmation is missing or already consumed",
                    ProductErrorCategory.AUTHORIZATION,
                )
            now = self._runtime_control_now()
            if now - pending.prepared_at >= 300.0:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_CONFIRMATION_EXPIRED",
                    "Runtime control confirmation expired",
                    ProductErrorCategory.AUTHORIZATION,
                )
            state, _source_path, _project = self._require_runtime_control_coordinate()
            capture = getattr(
                self.transcription_port,
                "capture_runtime_transcription_control",
                None,
            )
            if not callable(capture):
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_NOT_BOUND",
                    "Runtime transcription control port is not bound",
                    ProductErrorCategory.STATE,
                )
            snapshot = capture(
                project_id=state.project_id,
                source_asset_id=state.source_asset_id,
                source_asset_sha256=state.source_asset_sha256,
            )
            projection_reader = getattr(snapshot, "public_projection", None)
            try:
                projection = _validate_runtime_control_projection(
                    projection_reader() if callable(projection_reader) else None,
                )
            except ValueError as exc:
                raise ProductError(
                    "ERR_TASK098_RUNTIME_CONTROL_INVALID",
                    "Runtime transcription control projection is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
            return {
                "task_owner": "TASK-098",
                "status": "RUNTIME_TRANSCRIPTION_CONTROL_CANCELLED",
                "transcription_control": projection,
            }

    def prepare_local_transcription(self, *, recovery: bool = False) -> dict[str, Any]:
        if self.transcription_runtime_mode == "RUNTIME_MANAGED_V2":
            return self._prepare_runtime_transcription_action("RECOVER" if recovery else "START")
        with self._confirmation_lock:
            if len(self._transcription_confirmations) >= 256:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_CAPACITY",
                    "Too many local transcription confirmations are pending",
                    ProductErrorCategory.STATE,
                )
            state = self.coordinator.state
            source_path = self.media.runtime_source_path
            project = self.coordinator.shell.project
            if state.source_asset_id is None or state.source_asset_sha256 is None or source_path is None:
                raise ProductError(
                    "ERR_TASK036_RUNTIME_SOURCE_NOT_BOUND",
                    "Local transcription requires the trusted ingested source binding",
                    ProductErrorCategory.STATE,
                )
            if project is None or state.next_recommended_action != "transcription.start":
                raise ProductError(
                    "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                    "Local transcription is not available in the current editing stage",
                    ProductErrorCategory.AUTHORIZATION,
                )
            token = secrets.token_urlsafe(24)
            if token in self._transcription_confirmations:
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_CONFLICT",
                    "Local transcription confirmation identity collided",
                    ProductErrorCategory.STATE,
                )
            pending = _PendingTranscription(
                token, state.project_id, state.revision, state.source_asset_id,
                state.source_asset_sha256, source_path, project.context_revision,
                "RECOVER" if recovery else "START",
            )
            self._transcription_confirmations[token] = pending
            return {
                "task_owner": "TASK-036",
                "operation": "LOCAL_TRANSCRIPTION_PREPARE",
                "confirmation_id": token,
                "project_id": state.project_id,
                "source_asset_id": state.source_asset_id,
                "source_asset_sha256": state.source_asset_sha256,
                "provider_execution_mode": "LOCAL",
                "model_download_authorized": False,
                "provider_execution_started": False,
                "recovery": recovery,
            }

    def prepare_local_transcription_verification(self) -> dict[str, Any]:
        if self.transcription_runtime_mode != "RUNTIME_MANAGED_V2":
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                "Runtime-managed verification is not available in legacy mode",
                ProductErrorCategory.AUTHORIZATION,
            )
        return self._prepare_runtime_transcription_action("VERIFY")

    def cancel_local_transcription(self, confirmation_id: str) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._transcription_confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID",
                "Local transcription confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        return {
            "task_owner": "TASK-036",
            "operation": "LOCAL_TRANSCRIPTION_CANCEL",
            "status": "CANCELLED",
            "provider_execution_started": False,
        }

    def run_local_transcription(self, confirmation_id: str) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._transcription_confirmations.pop(confirmation_id, None)
        if pending is None:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID",
                "Local transcription confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        if pending.action != "START":
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID",
                "Recovery confirmation cannot authorize Provider execution",
                ProductErrorCategory.AUTHORIZATION,
            )
        if not self._transcription_lock.acquire(blocking=False):
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_IN_PROGRESS",
                "A local transcription operation is already active",
                ProductErrorCategory.STATE,
            )
        try:
            state = self.coordinator.state
            source_path = self.media.runtime_source_path
            project = self.coordinator.shell.project
            if (
                state.project_id != pending.project_id
                or state.revision != pending.session_revision
                or state.source_asset_id != pending.source_asset_id
                or state.source_asset_sha256 != pending.source_asset_sha256
                or source_path != pending.source_path
                or project is None
                or project.project_id != pending.project_id
                or project.context_revision != pending.context_revision
                or state.next_recommended_action != "transcription.start"
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE",
                    "Editing source changed before local transcription started",
                    ProductErrorCategory.STATE,
                )
            if (
                self.transcription_runtime_mode == "RUNTIME_MANAGED_V2"
                and self._runtime_managed_status()["transcription_available_action"] != "START"
            ):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE",
                    "Runtime-managed transcription authority changed before apply",
                    ProductErrorCategory.STATE,
                )
            expected = (
                pending.project_id,
                pending.session_revision,
                pending.source_asset_id,
                pending.source_asset_sha256,
                source_path,
                pending.context_revision,
            )
            command = ShellCommand(
                command_id=f"local-transcription-{project.context_revision}",
                command_type="transcription.start",
                project_id=project.project_id,
                expected_context_revision=project.context_revision,
                payload={"provider_mode": "LOCAL", "host_path_persisted": False},
            )

            def execute(_: ShellCommand) -> dict[str, Any]:
                outcome = self.transcription_port.transcribe_local_media(
                    project_id=pending.project_id,
                    source_path=source_path,
                    source_asset_id=pending.source_asset_id,
                    source_asset_sha256=pending.source_asset_sha256,
                )
                runtime_projection = self._validate_runtime_managed_outcome(
                    outcome,
                    action="START",
                )
                if self.media.runtime_source_path != source_path:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE",
                        "Editing source changed while local transcription was running",
                        ProductErrorCategory.STATE,
                    )
                result = self.binding.bind_transcript_if_current(
                    outcome.transcript,
                    expected_project_id=expected[0],
                    expected_revision=expected[1],
                    expected_source_asset_id=expected[2],
                    expected_source_asset_sha256=expected[3],
                    expected_context_revision=expected[5],
                )
                self._finalize_transcription_binding(
                    outcome,
                    project_id=pending.project_id,
                    source_asset_id=pending.source_asset_id,
                    source_asset_sha256=pending.source_asset_sha256,
                    transcript_manifest_sha256=result["transcript_manifest_sha256"],
                )
                result["provider_execution_started"] = outcome.provider_execution_started
                result["recovered_from_durable_result"] = outcome.recovered_from_durable_result
                if runtime_projection is not None:
                    result["runtime_transcription"] = runtime_projection
                return result

            receipt = self.coordinator.shell.dispatch(command, executor=execute)
            result = receipt.get("result")
            if not isinstance(result, dict):
                raise ProductError(
                    "ERR_TASK036_TRANSCRIPTION_RESULT_INVALID",
                    "Local transcription returned an invalid binding result",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            return {
                **result,
                "provider_execution_started": result.get("provider_execution_started") is True,
                "provider_execution_completed": True,
                "provider_execution_mode": "LOCAL",
                "provider_configuration_from_javascript": False,
                "recovered_from_durable_result": result.get("recovered_from_durable_result") is True,
            }
        finally:
            self._transcription_lock.release()

    def _apply_provider_zero_local_transcription(
        self,
        confirmation_id: str,
        *,
        required_action: str,
    ) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._transcription_confirmations.pop(confirmation_id, None)
        if pending is None or pending.action != required_action:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID",
                "Provider-zero transcription confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        if not self._transcription_lock.acquire(blocking=False):
            raise ProductError("ERR_TASK036_TRANSCRIPTION_IN_PROGRESS", "A local transcription operation is already active", ProductErrorCategory.STATE)
        try:
            state = self.coordinator.state
            project = self.coordinator.shell.project
            if (
                state.project_id != pending.project_id
                or state.revision != pending.session_revision
                or state.source_asset_id != pending.source_asset_id
                or state.source_asset_sha256 != pending.source_asset_sha256
                or self.media.runtime_source_path != pending.source_path
                or project is None
                or project.context_revision != pending.context_revision
                or state.next_recommended_action != "transcription.start"
            ):
                raise ProductError("ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE", "Editing source changed before recovery", ProductErrorCategory.STATE)
            if self.transcription_runtime_mode == "RUNTIME_MANAGED_V2":
                available = self._runtime_managed_status()["transcription_available_action"]
                if available != required_action:
                    raise ProductError(
                        "ERR_TASK036_TRANSCRIPTION_CONTEXT_STALE",
                        "Runtime-managed transcription authority changed before apply",
                        ProductErrorCategory.STATE,
                    )
            outcome = self.transcription_port.recover_local_media(
                project_id=pending.project_id,
                source_path=pending.source_path,
                source_asset_id=pending.source_asset_id,
                source_asset_sha256=pending.source_asset_sha256,
            )
            runtime_projection = self._validate_runtime_managed_outcome(
                outcome,
                action=required_action,
            )
            result = self.binding.bind_transcript_if_current(
                outcome.transcript,
                expected_project_id=pending.project_id,
                expected_revision=pending.session_revision,
                expected_source_asset_id=pending.source_asset_id,
                expected_source_asset_sha256=pending.source_asset_sha256,
                expected_context_revision=pending.context_revision,
            )
            self._finalize_transcription_binding(
                outcome,
                project_id=pending.project_id,
                source_asset_id=pending.source_asset_id,
                source_asset_sha256=pending.source_asset_sha256,
                transcript_manifest_sha256=result["transcript_manifest_sha256"],
            )
            response = {
                **result,
                "provider_execution_started": False,
                "provider_execution_completed": True,
                "provider_execution_mode": "LOCAL",
                "provider_configuration_from_javascript": False,
                "recovered_from_durable_result": True,
            }
            if runtime_projection is not None:
                response["runtime_transcription"] = runtime_projection
            return response
        finally:
            self._transcription_lock.release()

    def recover_local_transcription(self, confirmation_id: str) -> dict[str, Any]:
        return self._apply_provider_zero_local_transcription(
            confirmation_id, required_action="RECOVER",
        )

    def verify_local_transcription(self, confirmation_id: str) -> dict[str, Any]:
        if self.transcription_runtime_mode != "RUNTIME_MANAGED_V2":
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                "Runtime-managed verification is not available in legacy mode",
                ProductErrorCategory.AUTHORIZATION,
            )
        return self._apply_provider_zero_local_transcription(
            confirmation_id, required_action="VERIFY",
        )

    def _capture_pre_edit_coordinate(self, expected_action: str) -> _PreEditCoordinate:
        state = self.coordinator.state
        project = self.coordinator.shell.project
        source_path = self.media.runtime_source_path
        transcript = self.binding.transcript
        if (
            state.source_asset_id is None
            or state.source_asset_sha256 is None
            or state.transcript_sha256 is None
            or source_path is None
            or transcript is None
            or project is None
        ):
            raise ProductError(
                "ERR_TASK036_RUNTIME_PRE_EDIT_INPUT_NOT_BOUND",
                "Pre-edit stage requires the trusted source and Transcript objects",
                ProductErrorCategory.STATE,
            )
        action_admitted = (
            state.next_recommended_action == expected_action
            if expected_action == "subtitle.save"
            else (
                expected_action in state.available_commands()
                and state.cut_candidate_manifest_sha256 is None
            )
        )
        if not action_admitted:
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                "Pre-edit operation is not available in the current editing stage",
                ProductErrorCategory.AUTHORIZATION,
            )
        transcript_sha = transcript.to_dict()["manifest_sha256"]
        if (
            transcript.source_asset_id != state.source_asset_id
            or transcript_sha != state.transcript_sha256
            or project.project_id != state.project_id
        ):
            raise ProductError(
                "ERR_TASK036_PRE_EDIT_CONTEXT_STALE",
                "Trusted pre-edit inputs do not match the current editing coordinate",
                ProductErrorCategory.STATE,
            )
        return _PreEditCoordinate(
            state.project_id,
            state.revision,
            state.source_asset_id,
            state.source_asset_sha256,
            source_path,
            transcript_sha,
            state.subtitle_workspace_sha256,
            project.context_revision,
            transcript,
        )

    def _require_runtime_source_current(self, coordinate: _PreEditCoordinate) -> None:
        if self.media.runtime_source_path != coordinate.source_path:
            raise ProductError(
                "ERR_TASK036_PRE_EDIT_CONTEXT_STALE",
                "Trusted source path changed while the pre-edit operation was running",
                ProductErrorCategory.STATE,
            )

    def create_subtitle_workspace(self) -> dict[str, Any]:
        if not self._pre_edit_stage_lock.acquire(blocking=False):
            raise ProductError(
                "ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS",
                "A deterministic pre-edit stage operation is already active",
                ProductErrorCategory.STATE,
            )
        try:
            coordinate = self._capture_pre_edit_coordinate("subtitle.save")
            workspace = SubtitleWorkspace.from_transcript(coordinate.transcript)
            self._require_runtime_source_current(coordinate)
            return self.binding.bind_subtitle_workspace_if_current(
                workspace,
                expected_project_id=coordinate.project_id,
                expected_revision=coordinate.session_revision,
                expected_source_asset_id=coordinate.source_asset_id,
                expected_source_asset_sha256=coordinate.source_asset_sha256,
                expected_transcript_sha256=coordinate.transcript_sha256,
                expected_context_revision=coordinate.context_revision,
            )
        finally:
            self._pre_edit_stage_lock.release()

    @property
    def promoted_workflow_runtime(self) -> Any | None:
        return self._promoted_workflow_runtime

    def generate_cut_candidates(
        self,
        *,
        workflow_runtime_factory: Callable[[Task036EditingApplication], Any] | None = None,
    ) -> dict[str, Any]:
        if not self._pre_edit_stage_lock.acquire(blocking=False):
            raise ProductError(
                "ERR_TASK036_PRE_EDIT_STAGE_IN_PROGRESS",
                "A deterministic pre-edit stage operation is already active",
                ProductErrorCategory.STATE,
            )
        try:
            coordinate = self._capture_pre_edit_coordinate("cut_candidates.generate")
            manifest = self.cut_candidate_port.generate_cut_candidates(
                source_path=coordinate.source_path,
                transcript=coordinate.transcript,
            )
            self._require_runtime_source_current(coordinate)
            application = self.binding.prepare_cut_candidates(
                manifest,
                expected_source_asset_id=coordinate.source_asset_id,
                expected_transcript_sha256=coordinate.transcript_sha256,
                expected_subtitle_workspace_sha256=coordinate.subtitle_workspace_sha256,
            )
            promoted_workflow_runtime = None
            if workflow_runtime_factory is not None:
                promoted_workflow_runtime = workflow_runtime_factory(application)
                if (
                    promoted_workflow_runtime is None
                    or promoted_workflow_runtime.application is not application
                ):
                    raise ValueError("trusted runtime factory returned a different editing application")
            self._require_runtime_source_current(coordinate)
            application = self.binding.commit_cut_candidates_if_current(
                application,
                expected_project_id=coordinate.project_id,
                expected_revision=coordinate.session_revision,
                expected_source_asset_id=coordinate.source_asset_id,
                expected_source_asset_sha256=coordinate.source_asset_sha256,
                expected_transcript_sha256=coordinate.transcript_sha256,
                expected_context_revision=coordinate.context_revision,
            )
            self.application = application
            self._promoted_workflow_runtime = promoted_workflow_runtime
            return {
                "task_owner": "TASK-036",
                "operation": "CUT_CANDIDATE_GENERATE_AND_BIND",
                "candidate_count": len(manifest.candidates),
                "manifest_sha256": manifest.to_dict()["manifest_sha256"],
                "provider_execution_started": False,
                "host_path_persisted": False,
                "provider_configuration_from_javascript": False,
                "editing_session": self.coordinator.state.to_dict(),
                "next_recommended_action": self.coordinator.state.next_recommended_action,
            }
        finally:
            self._pre_edit_stage_lock.release()
