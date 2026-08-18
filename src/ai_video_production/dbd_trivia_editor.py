"""Small Windows-friendly Tkinter editor for DbD commentary trivia knowledge."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from .canonical_game_event import GameEventType
from .dbd_commentary_knowledge import DbDTriviaStore, TriviaCandidateMiner, TriviaSourceKind, TriviaStatus
from .dbd_perk_knowledge import PerkEnvironment


def default_trivia_database_path() -> Path:
    override = os.environ.get("BVP_DBD_TRIVIA_DB")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) if local else Path.home() / ".local" / "share"
    return root / "BAI Video Production" / "knowledge" / "dbd-commentary-knowledge.sqlite3"


def launch_editor(argv: Sequence[str] | None = None) -> int:
    import argparse
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    parser = argparse.ArgumentParser(description="BAI DbD Trivia Editor")
    parser.add_argument("--database", default=str(default_trivia_database_path()))
    args = parser.parse_args(list(argv) if argv is not None else None)
    store = DbDTriviaStore(args.database)

    root = tk.Tk(); root.title("BAI DbD Trivia Editor"); root.geometry("1000x700")
    root.columnconfigure(0, weight=1); root.rowconfigure(1, weight=1)
    form = ttk.Frame(root, padding=12); form.grid(row=0, column=0, sticky="nsew")
    form.columnconfigure(1, weight=1)
    fields: dict[str, tk.StringVar] = {}
    def row(label: str, key: str, index: int, default: str = "") -> None:
        ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", padx=(0,8), pady=3)
        var = tk.StringVar(value=default); fields[key] = var
        ttk.Entry(form, textvariable=var).grid(row=index, column=1, sticky="ew", pady=3)
    row("Title", "title", 0)
    row("Category", "category", 1, "GENERAL")
    row("Tags (comma)", "tags", 2)
    row("Event types (comma)", "event_types", 3)
    row("Entity refs (comma)", "entity_refs", 4)
    row("Source ref", "source_ref", 5, "manual://owner")
    row("Game version from", "version_from", 6)
    row("Game version to", "version_to", 7)
    ttk.Label(form, text="Environment").grid(row=8, column=0, sticky="w")
    env = tk.StringVar(value="LIVE"); ttk.Combobox(form, textvariable=env, values=[x.value for x in PerkEnvironment], state="readonly").grid(row=8,column=1,sticky="ew")
    verify = tk.BooleanVar(value=False); ttk.Checkbutton(form, text="Register as VERIFIED (manual owner fact)", variable=verify).grid(row=9,column=1,sticky="w",pady=4)
    ttk.Label(form, text="Trivia text").grid(row=10,column=0,sticky="nw")
    text = tk.Text(form, height=6, wrap="word"); text.grid(row=10,column=1,sticky="ew")

    lower = ttk.Frame(root, padding=(12,0,12,12)); lower.grid(row=1,column=0,sticky="nsew"); lower.rowconfigure(1,weight=1); lower.columnconfigure(0,weight=1)
    status_label = ttk.Label(lower, text=f"DB: {args.database}"); status_label.grid(row=0,column=0,sticky="w")
    tree = ttk.Treeview(lower, columns=("status","title","category"), show="headings")
    for col, title, width in (("status","Status",110),("title","Title",520),("category","Category",160)):
        tree.heading(col,text=title); tree.column(col,width=width,anchor="w")
    tree.grid(row=1,column=0,sticky="nsew",pady=8)

    def refresh() -> None:
        for item in tree.get_children(): tree.delete(item)
        for entry in store.list_latest():
            tree.insert("", "end", iid=entry.trivia_id, values=(entry.status.value, entry.title, entry.category))
        status_label.configure(text=f"DB: {args.database} | {len(store.list_latest())} entries")

    def parse_csv(value: str) -> tuple[str, ...]: return tuple(x.strip() for x in value.split(",") if x.strip())
    def register() -> None:
        try:
            events = tuple(GameEventType(x.strip().upper()) for x in parse_csv(fields["event_types"].get()))
            entry = store.create_manual(title=fields["title"].get(), text=text.get("1.0","end").strip(), source_ref=fields["source_ref"].get(), category=fields["category"].get(),
                                        tags=parse_csv(fields["tags"].get()), event_types=events, entity_refs=parse_csv(fields["entity_refs"].get()), environment=PerkEnvironment(env.get()),
                                        game_version_from=fields["version_from"].get().strip() or None, game_version_to=fields["version_to"].get().strip() or None, verify=verify.get())
            messagebox.showinfo("Saved", f"Saved {entry.trivia_id} as {entry.status.value}"); fields["title"].set(""); text.delete("1.0","end"); refresh()
        except Exception as exc: messagebox.showerror("Registration failed", str(exc))

    def selected_id() -> str | None:
        values = tree.selection(); return values[0] if values else None
    def verify_selected() -> None:
        item = selected_id()
        if not item: return
        try: store.verify(item); refresh()
        except Exception as exc: messagebox.showerror("Verify failed", str(exc))
    def reject_selected() -> None:
        item = selected_id()
        if not item: return
        try: store.reject(item); refresh()
        except Exception as exc: messagebox.showerror("Reject failed", str(exc))

    def import_commentary() -> None:
        chosen = filedialog.askopenfilename(title="Import commentary/transcript text", filetypes=[("Text / Markdown / SRT", "*.txt *.md *.srt"), ("All files", "*.*")])
        if not chosen: return
        try:
            path = Path(chosen); raw = path.read_text(encoding="utf-8-sig", errors="replace")
            source_kind = TriviaSourceKind.TRANSCRIPT_EXTRACTED if path.suffix.casefold() == ".srt" else TriviaSourceKind.COMMENTARY_EXTRACTED
            rows = TriviaCandidateMiner().capture(store, text=raw, source_ref=path.resolve().as_uri(), source_kind=source_kind)
            refresh(); messagebox.showinfo("Import complete", f"Captured {len(rows)} CANDIDATE trivia items. Review before verifying.")
        except Exception as exc: messagebox.showerror("Import failed", str(exc))

    buttons = ttk.Frame(form); buttons.grid(row=11,column=1,sticky="w",pady=8)
    ttk.Button(buttons,text="Register",command=register).pack(side="left",padx=(0,6))
    ttk.Button(buttons,text="Verify selected",command=verify_selected).pack(side="left",padx=(0,6))
    ttk.Button(buttons,text="Reject selected",command=reject_selected).pack(side="left",padx=(0,6))
    ttk.Button(buttons,text="Import commentary file",command=import_commentary).pack(side="left")
    refresh(); root.mainloop(); return 0


def main() -> int:
    return launch_editor()


if __name__ == "__main__":
    raise SystemExit(main())
