"""Trusted pre-edit composition for TASK-036.

The WebView chooses only an allowlisted stage action. Native paths and Product
ports remain Python-only runtime bindings and are never returned to JavaScript
or persisted in general Evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import secrets
from threading import Lock
from typing import Any, Callable, Protocol

from .cut_candidates import CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_media_workflow import MediaIngestPort, Task036MediaWorkflowFacade
from .desktop_pre_edit_binding import Task036PreEditBinding
from .desktop_shell import ShellCommand
from .errors import ProductError, ProductErrorCategory
from .subtitles import TranscriptManifest
from .subtitle_workspace import SubtitleWorkspace
from .task036_native_dialog import Task036NativeDialogService


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
    recovery: bool = False


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


@dataclass(slots=True)
class Task036PreEditRuntime:
    """Compose Media, local ASR, Subtitle and Cut services behind one gate."""

    coordinator: DesktopEditingCoordinator
    native_dialog: Task036NativeDialogService
    ingest_port: MediaIngestPort
    transcription_port: LocalTranscriptionPort
    cut_candidate_port: CutCandidateGenerationPort
    media: Task036MediaWorkflowFacade = field(init=False)
    binding: Task036PreEditBinding = field(init=False)
    application: Task036EditingApplication | None = field(default=None, init=False)
    _promoted_workflow_runtime: Any | None = field(default=None, init=False, repr=False)
    _transcription_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _pre_edit_stage_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _confirmation_lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _transcription_confirmations: dict[str, _PendingTranscription] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.media = Task036MediaWorkflowFacade(self.coordinator, self.native_dialog, self.ingest_port)
        self.binding = Task036PreEditBinding(self.coordinator)

    def status(self) -> dict[str, Any]:
        state = self.coordinator.state
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
        }

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

    def prepare_local_transcription(self, *, recovery: bool = False) -> dict[str, Any]:
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
                state.source_asset_sha256, source_path, project.context_revision, recovery,
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
        if pending.recovery:
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

    def recover_local_transcription(self, confirmation_id: str) -> dict[str, Any]:
        with self._confirmation_lock:
            pending = self._transcription_confirmations.pop(confirmation_id, None)
        if pending is None or not pending.recovery:
            raise ProductError(
                "ERR_TASK036_TRANSCRIPTION_CONFIRMATION_INVALID",
                "Local transcription recovery confirmation is missing or already consumed",
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
            outcome = self.transcription_port.recover_local_media(
                project_id=pending.project_id,
                source_path=pending.source_path,
                source_asset_id=pending.source_asset_id,
                source_asset_sha256=pending.source_asset_sha256,
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
            return {
                **result,
                "provider_execution_started": False,
                "provider_execution_completed": True,
                "provider_execution_mode": "LOCAL",
                "provider_configuration_from_javascript": False,
                "recovered_from_durable_result": True,
            }
        finally:
            self._transcription_lock.release()

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
            else expected_action in state.available_commands()
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
