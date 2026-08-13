from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_media_workflow import IngestedMediaIdentity
from ai_video_production.errors import ProductError
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_native_dialog import Task036NativeDialogService
from ai_video_production.task036_pre_edit_runtime import Task036PreEditRuntime
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
        return IngestedMediaIdentity("ASSET-00000000000000000000000000", sha("a"))


class TranscriptionPort:
    def __init__(self):
        self.calls: list[tuple[Path, str]] = []

    def transcribe_local_media(self, *, source_path: Path, source_asset_id: str):
        self.calls.append((source_path, source_asset_id))
        return TranscriptManifest(
            source_asset_id,
            "ja",
            "faster-whisper",
            "local-cached-model",
            (TranscriptSegment("seg-000001", 0, 1_000_000, "hello"),),
        )


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


def test_bridge_composes_trusted_media_transcript_subtitle_and_cut_route(tmp_path: Path):
    source, runtime, ingest, transcription, cut = make_runtime(tmp_path)
    bridge = Task036ShellBridge(runtime.coordinator.shell, pre_edit_runtime=runtime)

    assert bridge.workflow_status()["next_recommended_action"] == "media.choose_and_ingest"
    ingest_result = bridge.choose_and_ingest_media({})
    assert ingest_result["host_path_persisted"] is False
    assert bridge.workflow_status()["next_recommended_action"] == "transcription.start"

    transcript_result = bridge.run_local_transcription({})
    assert transcript_result["provider_execution_started"] is True
    assert transcript_result["provider_execution_completed"] is True
    assert transcript_result["provider_execution_mode"] == "LOCAL"
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
    bridge.run_local_transcription()
    bridge.create_runtime_subtitle_workspace()
    bridge.generate_runtime_cut_candidates()

    assert len(created) == 1
    assert created[0].application is runtime.application
    assert bridge.workflow_status()["next_recommended_action"] == "edit_plan.approve"
