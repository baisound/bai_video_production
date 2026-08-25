from __future__ import annotations

import sys

import pytest


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows native Tk acceptance requires a Windows desktop session",
)


def _walk_widgets(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _button_by_text(root, text: str):
    from tkinter import ttk

    matches = [
        widget
        for widget in _walk_widgets(root)
        if isinstance(widget, ttk.Button) and widget.cget("text") == text
    ]
    assert len(matches) == 1, f"expected one button {text!r}, got {len(matches)}"
    return matches[0]


def test_training_studio_native_tk_tab_traversal_and_safe_preflight(
    tmp_path, monkeypatch
) -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    from ai_video_production.dbd_training_studio import launch_training_studio
    from ai_video_production.dbd_training_studio_foundation import (
        WorkspaceRegistry,
        WorkspaceService,
    )

    try:
        probe = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    else:
        probe.destroy()

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    workspace = WorkspaceService(WorkspaceRegistry()).create(
        display_name="TASK-054 R7 native acceptance",
        parent_directory=tmp_path / "workspaces",
    )

    real_tk = tk.Tk
    observed: dict[str, object] = {}
    dialogs: list[tuple[str, str]] = []

    class InspectingTk(real_tk):
        def mainloop(self, n: int = 0) -> None:
            observed["root"] = self
            self.update_idletasks()
            notebooks = [
                child for child in self.winfo_children() if isinstance(child, ttk.Notebook)
            ]
            assert len(notebooks) == 1
            outer = notebooks[0]
            outer_labels = [outer.tab(tab_id, "text") for tab_id in outer.tabs()]
            assert outer_labels.count("実況・解説AI") == 1

            reasoning_tab_id = outer.tabs()[outer_labels.index("実況・解説AI")]
            outer.select(reasoning_tab_id)
            self.update_idletasks()
            assert outer.select() == reasoning_tab_id

            reasoning_page = self.nametowidget(reasoning_tab_id)
            inner_notebooks = [
                child
                for child in reasoning_page.winfo_children()
                if isinstance(child, ttk.Notebook)
            ]
            assert len(inner_notebooks) == 1
            inner = inner_notebooks[0]
            expected_labels = [
                "現在の実況・解説",
                "モデルと事前チェック",
                "Datasetと評価",
                "処理状況と復旧",
            ]
            assert [inner.tab(tab_id, "text") for tab_id in inner.tabs()] == expected_labels

            selected_labels: list[str] = []
            for tab_id, label in zip(inner.tabs(), expected_labels, strict=True):
                inner.select(tab_id)
                self.update_idletasks()
                page = self.nametowidget(tab_id)
                assert inner.select() == tab_id
                assert page.winfo_reqwidth() > 1
                assert page.winfo_reqheight() > 1
                selected_labels.append(label)

            execute = _button_by_text(reasoning_page, "現在の実況・解説を確認")
            review = _button_by_text(reasoning_page, "生成結果をレビュー")
            cancel = _button_by_text(reasoning_page, "安全にキャンセル")
            resume = _button_by_text(
                reasoning_page, "検証済みCheckpointから再開計画を作る"
            )
            assert execute.instate(["disabled"])
            assert review.instate(["disabled"])
            assert cancel.instate(["disabled"])
            assert resume.instate(["disabled"])

            preflight = _button_by_text(reasoning_page, "事前チェック")
            preflight.invoke()
            assert dialogs
            assert dialogs[-1][0] == "解説AIの事前チェック"
            assert "ERR_TASK054_R3D_REQUIRED" in dialogs[-1][1]
            assert execute.instate(["disabled"])
            assert review.instate(["disabled"])

            observed["outer_labels"] = outer_labels
            observed["selected_labels"] = selected_labels
            observed["preflight_error"] = "ERR_TASK054_R3D_REQUIRED"

    monkeypatch.setattr(tk, "Tk", InspectingTk)
    monkeypatch.setattr(
        messagebox,
        "showerror",
        lambda title, message, **_kwargs: dialogs.append((str(title), str(message))),
    )

    try:
        assert launch_training_studio(["--workspace", str(workspace.root)]) == 0
        assert observed["selected_labels"] == [
            "現在の実況・解説",
            "モデルと事前チェック",
            "Datasetと評価",
            "処理状況と復旧",
        ]
        assert observed["preflight_error"] == "ERR_TASK054_R3D_REQUIRED"
    finally:
        root = observed.get("root")
        if root is not None:
            root.destroy()
