"""TASK-050 R6 Workspace management controls."""
from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from .dbd_training_studio_foundation import WorkspaceService
from .dbd_workspace_relocation import WorkspaceRelocationService

def build_workspace_management_panel(parent: ttk.Frame, *, workspace, on_workspace_changed=None) -> dict[str, object]:
    state={"workspace":workspace}
    info=tk.StringVar(value=f"{workspace.display_name}\n{workspace.root_path}")
    box=ttk.LabelFrame(parent,text="ワークスペース管理",padding=10)
    box.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    ttk.Label(box,textvariable=info,justify="left",wraplength=820).pack(anchor="w",pady=(0,8))
    buttons=ttk.Frame(box); buttons.pack(anchor="w")
    def notify(updated):
        state["workspace"]=updated; info.set(f"{updated.display_name}\n{updated.root_path}")
        if on_workspace_changed: on_workspace_changed(updated)
    def rename_workspace():
        current=state["workspace"]
        name=simpledialog.askstring("ワークスペース名を変更","新しいワークスペース名を入力してください。",initialvalue=current.display_name,parent=parent)
        if not name:return
        try: updated=WorkspaceService().rename(current,name)
        except Exception as exc:
            messagebox.showerror("ワークスペース名を変更できませんでした",f"{type(exc).__name__}: {exc}"); return
        notify(updated)
    def move_workspace():
        current=state["workspace"]
        dest=filedialog.askdirectory(title="新しい保存先の親フォルダを選択",parent=parent)
        if not dest:return
        preflight=WorkspaceService().migration_preflight(current,dest)
        if not preflight.can_migrate:
            messagebox.showwarning("保存場所を変更できません","\n".join(preflight.blockers));return
        if not messagebox.askyesno("ワークスペースの保存場所を変更",
            f"現在:\n{preflight.source_path}\n\n変更先:\n{preflight.destination_path}\n\n"
            f"{preflight.source_file_count}ファイル / 約{preflight.source_bytes/(1024*1024):.1f} MB\n\n"
            "コピー後に整合性を確認します。元データは自動削除しません。"):
            return
        try:
            receipt=WorkspaceRelocationService().relocate(current,dest)
            updated=WorkspaceService().open(receipt.destination_path)
        except Exception as exc:
            messagebox.showerror("ワークスペースを移動できませんでした",f"{type(exc).__name__}: {exc}");return
        notify(updated)
        messagebox.showinfo("ワークスペース移行完了",f"新しい保存場所:\n{updated.root_path}\n\n元データ:\n{receipt.source_path}")
    ttk.Button(buttons,text="名前を変更",command=rename_workspace).pack(side="left",padx=(0,6))
    ttk.Button(buttons,text="保存場所を変更",command=move_workspace).pack(side="left",padx=6)
    return state
