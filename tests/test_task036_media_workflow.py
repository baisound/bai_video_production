from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import pytest

from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_media_workflow import IngestedMediaIdentity, Task036MediaWorkflowFacade
from ai_video_production.errors import ProductError
from ai_video_production.task036_native_dialog import Task036NativeDialogService

H = "sha256:" + "a" * 64


class Backend:
    def __init__(self, path): self.path = path; self.calls = 0
    def choose_open_media(self): self.calls += 1; return self.path
    def choose_project_folder(self): return None
    def choose_handoff_folder(self): return None


class Ingest:
    def __init__(self): self.paths = []
    def ingest_local_media(self, source_path: Path):
        self.paths.append(source_path)
        return IngestedMediaIdentity("asset-1", H, source_path)


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


def test_runtime_uses_managed_canonical_asset_instead_of_original_picker_path(tmp_path: Path):
    selected = tmp_path / "selected.mp4"; selected.write_bytes(b"untrusted original")
    managed = tmp_path / "managed" / "asset.mp4"; managed.parent.mkdir(); managed.write_bytes(b"canonical copy")

    class ManagedIngest(Ingest):
        def ingest_local_media(self, source_path: Path):
            self.paths.append(source_path)
            return IngestedMediaIdentity("asset-1", H, managed)

    facade = Task036MediaWorkflowFacade(
        coordinator(), Task036NativeDialogService(Backend(str(selected))), ManagedIngest(),
    )
    facade.choose_and_ingest()
    selected.write_bytes(b"changed after ingest")

    assert facade.runtime_source_path == managed
    assert facade.runtime_source_path.read_bytes() == b"canonical copy"


def test_cancelled_native_dialog_does_not_call_ingest_or_change_state():
    ingest = Ingest(); c = coordinator()
    result = Task036MediaWorkflowFacade(c, Task036NativeDialogService(Backend(None)), ingest).choose_and_ingest()
    assert result["status"] == "CANCELLED"
    assert ingest.paths == []
    assert c.state.source_asset_id is None


def test_stage_policy_blocks_second_ingest_after_source_is_bound(tmp_path: Path):
    media = tmp_path / "source.mp4"; media.write_bytes(b"media")
    ingest = Ingest(); c = coordinator()
    backend = Backend(str(media))
    facade = Task036MediaWorkflowFacade(c, Task036NativeDialogService(backend), ingest)
    facade.choose_and_ingest()
    with pytest.raises(ProductError) as exc:
        facade.choose_and_ingest()
    assert exc.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"
    assert len(ingest.paths) == 1
    assert backend.calls == 1


def test_parallel_choose_and_ingest_admits_exactly_one_native_picker_and_ingest(tmp_path: Path):
    media = tmp_path / "source.mp4"; media.write_bytes(b"media")
    entered, release = Event(), Event()

    class BlockingBackend(Backend):
        def choose_open_media(self):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return self.path

    backend = BlockingBackend(str(media)); ingest = Ingest(); c = coordinator()
    facade = Task036MediaWorkflowFacade(c, Task036NativeDialogService(backend), ingest)
    completed = []
    first = Thread(target=lambda: completed.append(facade.choose_and_ingest()))
    first.start()
    assert entered.wait(5)
    with pytest.raises(ProductError) as duplicate:
        facade.choose_and_ingest()
    assert duplicate.value.code == "ERR_TASK036_MEDIA_INGEST_IN_PROGRESS"
    assert backend.calls == 1
    assert ingest.paths == []
    release.set()
    first.join(5)
    assert not first.is_alive()
    assert len(completed) == 1
    assert completed[0]["status"] == "INGESTED"
    assert ingest.paths == [media]


def test_stage_drift_while_native_picker_is_open_rejects_before_ingest(tmp_path: Path):
    media = tmp_path / "source.mp4"; media.write_bytes(b"media")
    entered, release = Event(), Event()

    class BlockingBackend(Backend):
        def choose_open_media(self):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return self.path

    backend = BlockingBackend(str(media)); ingest = Ingest(); c = coordinator()
    facade = Task036MediaWorkflowFacade(c, Task036NativeDialogService(backend), ingest)
    errors = []

    def choose():
        try:
            facade.choose_and_ingest()
        except ProductError as exc:
            errors.append(exc)

    operation = Thread(target=choose)
    operation.start()
    assert entered.wait(5)
    c.bind_source(asset_id="asset-other", asset_sha256=H)
    release.set()
    operation.join(5)
    assert not operation.is_alive()
    assert len(errors) == 1
    assert errors[0].code in {"ERR_SHELL_CONTEXT_STALE", "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"}
    assert ingest.paths == []
    assert facade.runtime_source_path is None
