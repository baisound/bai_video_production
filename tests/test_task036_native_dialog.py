from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.native_file_dialog import NativeFileDialogUnavailable
from ai_video_production.task036_native_dialog import DialogPurpose, Task036NativeDialogService


class Backend:
    def __init__(self, *, media=None, project=None, handoff=None, error=False):
        self.media = media
        self.project = project
        self.handoff = handoff
        self.error = error

    def _value(self, value):
        if self.error:
            raise NativeFileDialogUnavailable("no native dialog")
        return value

    def choose_open_media(self):
        return self._value(self.media)

    def choose_project_folder(self):
        return self._value(self.project)

    def choose_handoff_folder(self):
        return self._value(self.handoff)


def test_media_selection_is_ephemeral_and_evidence_is_path_free(tmp_path: Path):
    media = tmp_path / "日本語 動画.mp4"
    media.write_bytes(b"media")
    result = Task036NativeDialogService(Backend(media=str(media))).choose_media_source()
    ui = result.to_ui_dict()
    evidence = result.to_evidence_dict()
    assert ui["purpose"] == DialogPurpose.MEDIA_SOURCE.value
    assert ui["host_path"] == str(media)
    assert ui["operation_started"] is False
    assert "host_path" not in evidence
    assert evidence["host_path_persisted"] is False


def test_cancel_does_not_become_operation():
    result = Task036NativeDialogService(Backend(media=None)).choose_media_source()
    assert result.selected is False
    assert result.to_ui_dict()["operation_started"] is False


def test_project_and_handoff_folders_require_real_non_symlink_directory(tmp_path: Path):
    project = tmp_path / "project"
    handoff = tmp_path / "handoff"
    project.mkdir(); handoff.mkdir()
    service = Task036NativeDialogService(Backend(project=str(project), handoff=str(handoff)))
    assert service.choose_project_folder().path_kind == "DIRECTORY"
    assert service.choose_handoff_folder().host_path == str(handoff)


def test_media_selection_rejects_directory(tmp_path: Path):
    with pytest.raises(ProductError) as exc:
        Task036NativeDialogService(Backend(media=str(tmp_path))).choose_media_source()
    assert exc.value.code == "ERR_TASK036_NATIVE_MEDIA_NOT_REGULAR_FILE"


def test_folder_selection_rejects_file(tmp_path: Path):
    target = tmp_path / "not-folder"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task036NativeDialogService(Backend(project=str(target))).choose_project_folder()
    assert exc.value.code == "ERR_TASK036_NATIVE_FOLDER_NOT_DIRECTORY"


def test_native_backend_error_becomes_structured_product_error():
    with pytest.raises(ProductError) as exc:
        Task036NativeDialogService(Backend(error=True)).choose_handoff_folder()
    assert exc.value.code == "ERR_TASK036_NATIVE_DIALOG_UNAVAILABLE"
