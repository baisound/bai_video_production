"""TASK-036 binding of completed transcript/subtitle/cut artifacts into one Shell.

Provider execution remains outside this module.  The binder accepts immutable
completed results and verifies exact source/transcript identity before advancing
the stage-aware desktop command surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cut_candidates import CutCandidateManifest
from .desktop_editing_application import Task036EditingApplication
from .desktop_editing_coordinator import DesktopEditingCoordinator
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitle_workspace import SubtitleWorkspace
from .subtitles import TranscriptManifest


def _workspace_sha256(workspace: SubtitleWorkspace) -> str:
    return sha256_bytes(canonical_json_bytes(workspace.to_dict()))


@dataclass(slots=True)
class Task036PreEditBinding:
    coordinator: DesktopEditingCoordinator
    transcript: TranscriptManifest | None = None
    subtitle_workspace: SubtitleWorkspace | None = None

    def bind_transcript(self, transcript: TranscriptManifest) -> dict[str, Any]:
        state = self.coordinator.state
        if state.source_asset_id is None:
            raise ProductError(
                "ERR_SHELL_SOURCE_REQUIRED",
                "Completed transcript cannot bind before a source Asset is selected",
                ProductErrorCategory.STATE,
            )
        if transcript.source_asset_id != state.source_asset_id:
            raise ProductError(
                "ERR_SHELL_TRANSCRIPT_SOURCE_MISMATCH",
                "Completed transcript belongs to a different source Asset",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        transcript_sha = transcript.to_dict()["manifest_sha256"]
        if state.transcript_sha256 is not None and state.transcript_sha256 != transcript_sha:
            raise ProductError(
                "ERR_SHELL_TRANSCRIPT_ALREADY_BOUND",
                "Desktop session already references a different Transcript",
                ProductErrorCategory.STATE,
            )
        if state.transcript_sha256 is None:
            self.coordinator.bind_transcript(transcript_sha)
        self.transcript = transcript
        return {
            "task_owner": "TASK-036",
            "operation": "TRANSCRIPT_RESULT_BIND",
            "transcript_manifest_sha256": transcript_sha,
            "provider_execution_started": False,
            "editing_session": self.coordinator.state.to_dict(),
            "next_recommended_action": self.coordinator.state.next_recommended_action,
        }

    def bind_transcript_if_current(
        self,
        transcript: TranscriptManifest,
        *,
        expected_project_id: str,
        expected_revision: int,
        expected_source_asset_id: str,
        expected_source_asset_sha256: str,
        expected_context_revision: int,
    ) -> dict[str, Any]:
        if transcript.source_asset_id != expected_source_asset_id:
            raise ProductError(
                "ERR_SHELL_TRANSCRIPT_SOURCE_MISMATCH",
                "Completed transcript belongs to a different source Asset",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        transcript_sha = transcript.to_dict()["manifest_sha256"]
        self.coordinator.bind_transcript_if_current(
            transcript_sha,
            expected_project_id=expected_project_id,
            expected_revision=expected_revision,
            expected_source_asset_id=expected_source_asset_id,
            expected_source_asset_sha256=expected_source_asset_sha256,
            expected_context_revision=expected_context_revision,
        )
        self.transcript = transcript
        return {
            "task_owner": "TASK-036",
            "operation": "TRANSCRIPT_RESULT_BIND",
            "transcript_manifest_sha256": transcript_sha,
            "provider_execution_started": False,
            "editing_session": self.coordinator.state.to_dict(),
            "next_recommended_action": self.coordinator.state.next_recommended_action,
        }

    def create_subtitle_workspace(self) -> dict[str, Any]:
        state = self.coordinator.state
        if self.transcript is None:
            raise ProductError(
                "ERR_SHELL_TRANSCRIPT_OBJECT_REQUIRED",
                "Subtitle Workspace creation requires the exact completed Transcript object",
                ProductErrorCategory.STATE,
            )
        transcript_sha = self.transcript.to_dict()["manifest_sha256"]
        if state.transcript_sha256 != transcript_sha:
            raise ProductError(
                "ERR_SHELL_TRANSCRIPT_CONTEXT_STALE",
                "Transcript context changed before Subtitle Workspace creation",
                ProductErrorCategory.STATE,
            )
        workspace = SubtitleWorkspace.from_transcript(self.transcript)
        workspace_sha = _workspace_sha256(workspace)
        self.coordinator.bind_subtitle_workspace(workspace_sha)
        self.subtitle_workspace = workspace
        return {
            "task_owner": "TASK-036",
            "operation": "SUBTITLE_WORKSPACE_CREATE",
            "subtitle_workspace_sha256": workspace_sha,
            "cue_count": len(workspace.cues),
            "provider_execution_started": False,
            "editing_session": self.coordinator.state.to_dict(),
        }

    def bind_cut_candidates(self, manifest: CutCandidateManifest) -> Task036EditingApplication:
        state = self.coordinator.state
        if state.source_asset_id != manifest.source_asset_id:
            raise ProductError(
                "ERR_SHELL_CUT_SOURCE_MISMATCH",
                "Cut Candidate manifest belongs to a different source Asset",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if manifest.transcript_manifest_sha256 is None or manifest.transcript_manifest_sha256 != state.transcript_sha256:
            raise ProductError(
                "ERR_SHELL_CUT_TRANSCRIPT_MISMATCH",
                "Cut Candidate manifest does not reference the current Transcript",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return Task036EditingApplication.from_pre_edit_results(
            coordinator=self.coordinator,
            cut_manifest=manifest,
            subtitle_workspace=self.subtitle_workspace,
        )
