"""TASK-036 native file/folder chooser boundary for the desktop editing shell.

The service intentionally separates an ephemeral local host path from durable
Product state.  Selecting a path is never equivalent to ingesting media,
opening a canonical Project, creating EDITOR_WORK, or authorizing an external
mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .errors import ProductError, ProductErrorCategory
from .native_file_dialog import NativeFileDialogUnavailable, WindowsNativeFileDialog


class DialogPurpose(str, Enum):
    MEDIA_SOURCE = "MEDIA_SOURCE"
    PROJECT_FOLDER = "PROJECT_FOLDER"
    HANDOFF_FOLDER = "HANDOFF_FOLDER"


class NativeDialogBackend(Protocol):
    def choose_open_media(self) -> str | None: ...
    def choose_project_folder(self) -> str | None: ...
    def choose_handoff_folder(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class NativeDialogSelection:
    purpose: DialogPurpose
    selected: bool
    host_path: str | None
    path_kind: str | None

    def to_ui_dict(self) -> dict[str, Any]:
        return {
            "selection_version": "1.0.0",
            "task_owner": "TASK-036",
            "purpose": self.purpose.value,
            "selected": self.selected,
            "host_path": self.host_path,
            "path_kind": self.path_kind,
            "host_path_is_ephemeral": True,
            "persisted_to_product_state": False,
            "operation_started": False,
        }

    def to_evidence_dict(self) -> dict[str, Any]:
        """Path-free shape safe for general evidence/logging."""
        return {
            "selection_version": "1.0.0",
            "task_owner": "TASK-036",
            "purpose": self.purpose.value,
            "selected": self.selected,
            "path_kind": self.path_kind,
            "host_path_persisted": False,
            "operation_started": False,
        }


class Task036NativeDialogService:
    """Validate local chooser results without turning selection into mutation."""

    def __init__(self, backend: NativeDialogBackend | None = None) -> None:
        self.backend = backend or WindowsNativeFileDialog()

    @staticmethod
    def _regular_file(path_text: str, *, purpose: DialogPurpose) -> NativeDialogSelection:
        path = Path(path_text)
        try:
            valid = not path.is_symlink() and path.is_file()
        except OSError as exc:
            raise ProductError(
                "ERR_TASK036_NATIVE_SELECTION_UNREADABLE",
                "Selected media path could not be inspected",
                ProductErrorCategory.VALIDATION,
                details={"purpose": purpose.value, "exception_type": type(exc).__name__},
            ) from exc
        if not valid:
            raise ProductError(
                "ERR_TASK036_NATIVE_MEDIA_NOT_REGULAR_FILE",
                "Selected media source must be an existing regular non-symlink file",
                ProductErrorCategory.VALIDATION,
                details={"purpose": purpose.value},
            )
        return NativeDialogSelection(purpose, True, str(path), "FILE")

    @staticmethod
    def _directory(path_text: str, *, purpose: DialogPurpose) -> NativeDialogSelection:
        path = Path(path_text)
        try:
            valid = not path.is_symlink() and path.is_dir()
        except OSError as exc:
            raise ProductError(
                "ERR_TASK036_NATIVE_SELECTION_UNREADABLE",
                "Selected folder could not be inspected",
                ProductErrorCategory.VALIDATION,
                details={"purpose": purpose.value, "exception_type": type(exc).__name__},
            ) from exc
        if not valid:
            raise ProductError(
                "ERR_TASK036_NATIVE_FOLDER_NOT_DIRECTORY",
                "Selected destination must be an existing regular non-symlink directory",
                ProductErrorCategory.VALIDATION,
                details={"purpose": purpose.value},
            )
        return NativeDialogSelection(purpose, True, str(path), "DIRECTORY")

    @staticmethod
    def _cancelled(purpose: DialogPurpose) -> NativeDialogSelection:
        return NativeDialogSelection(purpose, False, None, None)

    def choose_media_source(self) -> NativeDialogSelection:
        try:
            selected = self.backend.choose_open_media()
        except NativeFileDialogUnavailable as exc:
            raise ProductError(
                "ERR_TASK036_NATIVE_DIALOG_UNAVAILABLE",
                "Native media chooser is unavailable",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"purpose": DialogPurpose.MEDIA_SOURCE.value},
            ) from exc
        if selected is None:
            return self._cancelled(DialogPurpose.MEDIA_SOURCE)
        return self._regular_file(selected, purpose=DialogPurpose.MEDIA_SOURCE)

    def choose_project_folder(self) -> NativeDialogSelection:
        try:
            selected = self.backend.choose_project_folder()
        except NativeFileDialogUnavailable as exc:
            raise ProductError(
                "ERR_TASK036_NATIVE_DIALOG_UNAVAILABLE",
                "Native Project-folder chooser is unavailable",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"purpose": DialogPurpose.PROJECT_FOLDER.value},
            ) from exc
        if selected is None:
            return self._cancelled(DialogPurpose.PROJECT_FOLDER)
        return self._directory(selected, purpose=DialogPurpose.PROJECT_FOLDER)

    def choose_handoff_folder(self) -> NativeDialogSelection:
        try:
            selected = self.backend.choose_handoff_folder()
        except NativeFileDialogUnavailable as exc:
            raise ProductError(
                "ERR_TASK036_NATIVE_DIALOG_UNAVAILABLE",
                "Native EDITOR_WORK-folder chooser is unavailable",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"purpose": DialogPurpose.HANDOFF_FOLDER.value},
            ) from exc
        if selected is None:
            return self._cancelled(DialogPurpose.HANDOFF_FOLDER)
        return self._directory(selected, purpose=DialogPurpose.HANDOFF_FOLDER)
