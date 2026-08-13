from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_media_workflow import IngestedMediaIdentity, Task036MediaWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.task036_native_dialog import Task036NativeDialogService

H = "sha256:" + "a" * 64


class Backend:
    def __init__(self, path): self.path = path
    def choose_open_media(self): return self.path
    def choose_project_folder(self): return None
    def choose_handoff_folder(self): return None


class Ingest:
    def __init__(self): self.paths = []
    def ingest_local_media(self, source_path: Path):
        self.paths.append(source_path)
        return IngestedMediaIdentity("asset-1", H)


def coordinator():
    return DesktopEditingCoordinator.create(product_version="0.19.0", project_id="project-1", display_name="Project 1")


def test_native_choose_and_ingest_binds_asset_without_persisting_host_path(tmp_path: Path):
    media = tmp_path / "日本語 source.mp4"; media.write_bytes(b"media")
    ingest = Ingest()
    c = coordinator()
    result = Task036MediaWorkflowFacade(c, Task036NativeDialogService(Backend(str(media))), ingest).choose_and_ingest()
    assert ingest.paths == [media]
    assert c.state.source_asset_id == "asset-1"
    assert c.state.source_asset_sha256 == H
    assert result["host_path_persisted"] is False
    assert result["receipt"]["result"]["source_name"] == media.name
    assert "host_path" not in result["receipt"]["result"]
    assert result["next_recommended_action"] == "transcription.start"


def test_cancelled_native_dialog_does_not_call_ingest_or_change_state():
    ingest = Ingest(); c = coordinator()
    result = Task036MediaWorkflowFacade(c, Task036NativeDialogService(Backend(None)), ingest).choose_and_ingest()
    assert result["status"] == "CANCELLED"
    assert ingest.paths == []
    assert c.state.source_asset_id is None


def test_stage_policy_blocks_second_ingest_after_source_is_bound(tmp_path: Path):
    media = tmp_path / "source.mp4"; media.write_bytes(b"media")
    ingest = Ingest(); c = coordinator()
    facade = Task036MediaWorkflowFacade(c, Task036NativeDialogService(Backend(str(media))), ingest)
    facade.choose_and_ingest()
    with pytest.raises(ProductError) as exc:
        facade.choose_and_ingest()
    assert exc.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert len(ingest.paths) == 1
