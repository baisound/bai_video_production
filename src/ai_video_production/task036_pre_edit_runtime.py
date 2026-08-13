"""Trusted pre-edit composition for TASK-036.

The WebView chooses only an allowlisted stage action. Native paths and Product
ports remain Python-only runtime bindings and are never returned to JavaScript
or persisted in general Evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .cut_candidates import CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .desktop_media_workflow import MediaIngestPort, Task036MediaWorkflowFacade
from .desktop_pre_edit_binding import Task036PreEditBinding
from .errors import ProductError, ProductErrorCategory
from .subtitles import TranscriptManifest
from .task036_native_dialog import Task036NativeDialogService


class LocalTranscriptionPort(Protocol):
    def transcribe_local_media(self, *, source_path: Path, source_asset_id: str) -> TranscriptManifest: ...


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

    def __post_init__(self) -> None:
        self.media = Task036MediaWorkflowFacade(self.coordinator, self.native_dialog, self.ingest_port)
        self.binding = Task036PreEditBinding(self.coordinator)

    def status(self) -> dict[str, Any]:
        state = self.coordinator.state
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
        }

    def choose_and_ingest_media(self) -> dict[str, Any]:
        return self.media.choose_and_ingest()

    def run_local_transcription(self) -> dict[str, Any]:
        state = self.coordinator.state
        source_path = self.media.runtime_source_path
        if state.source_asset_id is None or source_path is None:
            raise ProductError(
                "ERR_TASK036_RUNTIME_SOURCE_NOT_BOUND",
                "Local transcription requires the trusted ingested source binding",
                ProductErrorCategory.STATE,
            )
        transcript = self.transcription_port.transcribe_local_media(
            source_path=source_path,
            source_asset_id=state.source_asset_id,
        )
        result = self.binding.bind_transcript(transcript)
        return {
            **result,
            "provider_execution_started": True,
            "provider_execution_completed": True,
            "provider_execution_mode": "LOCAL",
        }

    def create_subtitle_workspace(self) -> dict[str, Any]:
        return self.binding.create_subtitle_workspace()

    def generate_cut_candidates(self) -> dict[str, Any]:
        source_path = self.media.runtime_source_path
        transcript = self.binding.transcript
        if source_path is None or transcript is None:
            raise ProductError(
                "ERR_TASK036_RUNTIME_PRE_EDIT_INPUT_NOT_BOUND",
                "Cut Candidate generation requires the trusted source and Transcript objects",
                ProductErrorCategory.STATE,
            )
        manifest = self.cut_candidate_port.generate_cut_candidates(
            source_path=source_path,
            transcript=transcript,
        )
        self.application = self.binding.bind_cut_candidates(manifest)
        return {
            "task_owner": "TASK-036",
            "operation": "CUT_CANDIDATE_GENERATE_AND_BIND",
            "candidate_count": len(manifest.candidates),
            "manifest_sha256": manifest.to_dict()["manifest_sha256"],
            "host_path_persisted": False,
            "provider_configuration_from_javascript": False,
            "editing_session": self.coordinator.state.to_dict(),
            "next_recommended_action": self.coordinator.state.next_recommended_action,
        }
