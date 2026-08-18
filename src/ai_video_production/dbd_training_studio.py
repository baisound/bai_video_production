"""Windows-friendly DbD Training Studio for single and bulk teacher-data intake."""
from __future__ import annotations

import csv
from pathlib import Path
import threading
from typing import Sequence

from .canonical_game_event import GameEventType
from .dbd_perk_knowledge import PerkEnvironment
from .dbd_data_migration import DbDDataMigrationService
from .dbd_hud_calibration import DBDHudVideoProfileResolver, FFmpegFrameInspector, HudAnchorAligner, HudProfileRegistry
from .dbd_kamigame_collector import KamigameDbDKnowledgeCollector
from .dbd_vision_slices import DBDHudRoiProfile, GrayImage, NormalizedROI
from .dbd_training_workspace import (
    DbDTrainingWorkspace,
    OcrVideoCandidate,
    OcrVocabularySample,
    VisualTrainingDomain,
    VisualTrainingSample,
    VisualVideoTrainingRequest,
    default_training_workspace_root,
)


def ensure_csv_templates(root: str | Path) -> tuple[Path, Path, Path, Path]:
    base = Path(root) / "templates"
    base.mkdir(parents=True, exist_ok=True)
    visual = base / "visual-training-template.csv"
    ocr = base / "upper-right-ocr-vocabulary-template.csv"
    trivia = base / "commentary-trivia-template.csv"
    video = base / "video-training-ranges-template.csv"
    if not visual.exists():
        with visual.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["domain","label","image_path","group","source_ref","notes"])
            w.writerow(["PERK_ICON","perk_windows_of_opportunity",r"D:\dbd-dataset\perk.png","normal","manual://owner",""])
    if not ocr.exists():
        with ocr.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["signal_id","phrase","locale","source_ref"])
            w.writerow(["CHASE","追跡","ja-JP","manual://owner"])
    if not trivia.exists():
        with trivia.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["title","text","category","tags","event_types","entity_refs","source_ref","environment","game_version_from","game_version_to","verify"])
            w.writerow(["窓枠の基本","窓枠はチェイスで距離を作る代表的な地形要素です。","BEGINNER","CHASE,WINDOW","WINDOW_VAULT","","manual://owner","LIVE","","","false"])
    if not video.exists():
        with video.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain","label","video_path","start_frame","end_frame_exclusive","frame_step","slot","group","source_ref","notes","roi_profile_path","max_samples"])
            w.writerow(["PERK_ICON","perk_windows_of_opportunity",r"D:\dbd-dataset\match.mp4","300","1800","60","0","normal","","sampled from owned recording","","500"])
    return visual, ocr, trivia, video


def launch_training_studio(argv: Sequence[str] | None = None) -> int:
    import argparse
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    parser = argparse.ArgumentParser(description="BAI DbD Training Studio")
    parser.add_argument("--workspace", default=str(default_training_workspace_root()))
    args = parser.parse_args(list(argv) if argv is not None else None)

    workspace = DbDTrainingWorkspace(args.workspace)
    templates = ensure_csv_templates(workspace.root)

    root = tk.Tk()
    root.title("BAI DbD Training Studio")
    root.geometry("1120x780")
    root.minsize(980, 680)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    header = ttk.Frame(root, padding=(12, 10, 12, 4))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)
    ttk.Label(header, text="Training workspace").grid(row=0, column=0, sticky="w", padx=(0, 8))
    root_var = tk.StringVar(value=str(workspace.root))
    ttk.Entry(header, textvariable=root_var, state="readonly").grid(row=0, column=1, sticky="ew")
    ttk.Label(header, text="1件登録 / CSV一括登録の両方に対応").grid(row=1, column=1, sticky="w", pady=(4, 0))

    notebook = ttk.Notebook(root)
    notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

    status = tk.StringVar(value="Ready")
    ttk.Label(root, textvariable=status, anchor="w").grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

    def report_message(title: str, report) -> None:
        lines = [f"Accepted: {report.accepted}", f"Rejected: {report.rejected}"]
        if report.errors:
            lines += ["", *report.errors[:12]]
            if len(report.errors) > 12:
                lines.append(f"... and {len(report.errors)-12} more")
        status.set(f"{title}: accepted={report.accepted} rejected={report.rejected}")
        (messagebox.showinfo if report.rejected == 0 else messagebox.showwarning)(title, "\n".join(lines))

    background_state = {"active": False}

    def run_background(title: str, fn, on_success) -> None:
        """Keep long FFmpeg/OCR/ASR jobs off the Tk event loop."""
        if background_state["active"]:
            messagebox.showwarning("Training Studio busy", "Another video/OCR/ASR job is still running. Wait for it to finish before starting another job.")
            return
        background_state["active"] = True
        status.set(f"{title}: running...")

        def worker() -> None:
            try:
                result = fn()
            except Exception as exc:  # surfaced on UI thread
                def failed() -> None:
                    background_state["active"] = False
                    status.set(f"{title}: failed")
                    messagebox.showerror(title, str(exc))
                root.after(0, failed)
                return
            def succeeded() -> None:
                background_state["active"] = False
                on_success(result)
            root.after(0, succeeded)

        threading.Thread(target=worker, daemon=True).start()

    # ---- Video learning tab --------------------------------------------------
    video_tab = ttk.Frame(notebook, padding=12)
    notebook.add(video_tab, text="Video Learning")
    video_tab.columnconfigure(1, weight=1)

    video_vars = {
        "video": tk.StringVar(),
        "roi_profile": tk.StringVar(),
        "domain": tk.StringVar(value=VisualTrainingDomain.PERK_ICON.value),
        "slot": tk.StringVar(value="0"),
        "label": tk.StringVar(),
        "group": tk.StringVar(value="normal"),
        "start": tk.StringVar(value="0"),
        "end": tk.StringVar(value="300"),
        "step": tk.StringVar(value="30"),
        "max_samples": tk.StringVar(value="500"),
        "ffmpeg": tk.StringVar(value="ffmpeg"),
    }

    ttk.Label(video_tab, text="Owned / permitted recording").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(video_tab, textvariable=video_vars["video"]).grid(row=0, column=1, sticky="ew", pady=3)
    def choose_video() -> None:
        chosen = filedialog.askopenfilename(title="Select DbD recording", filetypes=[("Video","*.mp4 *.mkv *.mov *.avi *.webm"),("All files","*.*")])
        if chosen: video_vars["video"].set(chosen)
    ttk.Button(video_tab, text="Browse video", command=choose_video).grid(row=0, column=2, padx=(8,0))

    ttk.Label(video_tab, text="ROI profile JSON (optional)").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(video_tab, textvariable=video_vars["roi_profile"]).grid(row=1, column=1, sticky="ew", pady=3)
    def choose_roi_profile() -> None:
        chosen = filedialog.askopenfilename(title="Select DbD ROI profile", filetypes=[("JSON","*.json"),("All files","*.*")])
        if chosen: video_vars["roi_profile"].set(chosen)
    ttk.Button(video_tab, text="Browse ROI", command=choose_roi_profile).grid(row=1, column=2, padx=(8,0))

    ttk.Label(video_tab, text="Visual target").grid(row=2, column=0, sticky="w", pady=3)
    ttk.Combobox(video_tab, textvariable=video_vars["domain"], values=[x.value for x in VisualTrainingDomain], state="readonly").grid(row=2, column=1, sticky="ew", pady=3)
    ttk.Label(video_tab, text="Slot (Survivor/Perk 0-3; Add-on 0-1; blank Item/Killer-Power)").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Entry(video_tab, textvariable=video_vars["slot"]).grid(row=3, column=1, sticky="ew", pady=3)
    ttk.Label(video_tab, text="Label").grid(row=4, column=0, sticky="w", pady=3)
    ttk.Entry(video_tab, textvariable=video_vars["label"]).grid(row=4, column=1, sticky="ew", pady=3)
    ttk.Label(video_tab, text="Visual group").grid(row=5, column=0, sticky="w", pady=3)
    ttk.Entry(video_tab, textvariable=video_vars["group"]).grid(row=5, column=1, sticky="ew", pady=3)

    range_frame = ttk.Frame(video_tab); range_frame.grid(row=6, column=1, sticky="ew", pady=3)
    for idx in range(4): range_frame.columnconfigure(idx, weight=1)
    ttk.Label(video_tab, text="Exact frame sampling").grid(row=6, column=0, sticky="w", pady=3)
    ttk.Entry(range_frame, textvariable=video_vars["start"], width=10).grid(row=0,column=0,sticky="ew",padx=(0,4))
    ttk.Entry(range_frame, textvariable=video_vars["end"], width=10).grid(row=0,column=1,sticky="ew",padx=4)
    ttk.Entry(range_frame, textvariable=video_vars["step"], width=10).grid(row=0,column=2,sticky="ew",padx=4)
    ttk.Entry(range_frame, textvariable=video_vars["max_samples"], width=10).grid(row=0,column=3,sticky="ew",padx=(4,0))
    ttk.Label(range_frame, text="start / end-exclusive / step / max", anchor="center").grid(row=1,column=0,columnspan=4,sticky="ew")

    video_learning_result = tk.StringVar(value="No video learning run yet.")
    ttk.Label(video_tab, textvariable=video_learning_result, wraplength=900).grid(row=7,column=1,sticky="w",pady=(8,4))

    def make_video_request() -> VisualVideoTrainingRequest:
        slot_text = video_vars["slot"].get().strip()
        return VisualVideoTrainingRequest(
            domain=VisualTrainingDomain(video_vars["domain"].get()),
            label=video_vars["label"].get().strip(),
            video_path=video_vars["video"].get().strip(),
            start_frame=int(video_vars["start"].get()),
            end_frame_exclusive=int(video_vars["end"].get()),
            frame_step=int(video_vars["step"].get()),
            slot=None if not slot_text else int(slot_text),
            group=video_vars["group"].get().strip() or "normal",
            source_ref="",
            roi_profile_path=video_vars["roi_profile"].get().strip() or None,
            max_samples=int(video_vars["max_samples"].get()),
        )

    def extract_video_learning() -> None:
        try:
            request = make_video_request()
        except Exception as exc:
            messagebox.showerror("Video learning", str(exc)); return
        def done(report) -> None:
            video_learning_result.set(
                f"Extracted={report.extracted} Registered={report.registered} Duplicates={report.duplicates} "
                f"Rejected={report.rejected} | {report.output_directory}"
            )
            status.set(f"Video learning: registered={report.registered} rejected={report.rejected}")
            if report.rejected:
                messagebox.showwarning("Video learning", "\n".join([video_learning_result.get(), *report.errors[:10]]))
            else:
                messagebox.showinfo("Video learning", video_learning_result.get())
            refresh_visual_count()
        run_background(
            "Video learning",
            lambda: workspace.extract_visual_from_video(request, ffmpeg_executable=video_vars["ffmpeg"].get().strip() or "ffmpeg"),
            done,
        )

    def import_video_ranges_csv() -> None:
        chosen = filedialog.askopenfilename(title="Import video learning ranges CSV", filetypes=[("CSV","*.csv"),("All files","*.*")])
        if not chosen: return
        domain = VisualTrainingDomain(video_vars["domain"].get())
        run_background(
            "Video ranges CSV",
            lambda: workspace.import_video_training_csv(chosen, default_domain=domain, ffmpeg_executable=video_vars["ffmpeg"].get().strip() or "ffmpeg"),
            lambda report: (report_message("Video ranges CSV", report), refresh_visual_count()),
        )

    video_buttons = ttk.Frame(video_tab); video_buttons.grid(row=8,column=1,sticky="w",pady=8)
    ttk.Button(video_buttons,text="Extract + register from video",command=extract_video_learning).pack(side="left",padx=(0,6))
    ttk.Button(video_buttons,text="Import video ranges CSV (1 or many rows)",command=import_video_ranges_csv).pack(side="left")
    ttk.Label(video_tab,text=f"Video CSV template: {templates[3]}",wraplength=900).grid(row=9,column=1,sticky="w",pady=(4,12))

    # OCR candidate scan from video. Candidate text is never inserted until the
    # user explicitly selects it and presses Register.
    ttk.Separator(video_tab, orient="horizontal").grid(row=10,column=0,columnspan=3,sticky="ew",pady=8)
    ttk.Label(video_tab,text="Upper-right OCR candidates from video").grid(row=11,column=0,sticky="nw",pady=3)
    ocr_video_side = ttk.Frame(video_tab); ocr_video_side.grid(row=11,column=1,columnspan=2,sticky="nsew")
    ocr_video_side.columnconfigure(1,weight=1)
    ocr_video_signal = tk.StringVar(value="CHASE")
    ocr_video_language = tk.StringVar(value="jpn+eng")
    ocr_video_tesseract = tk.StringVar(value="tesseract")
    for row_no,(label,var) in enumerate((("Signal ID for selected phrase",ocr_video_signal),("OCR language",ocr_video_language),("Tesseract executable",ocr_video_tesseract))):
        ttk.Label(ocr_video_side,text=label).grid(row=row_no,column=0,sticky="w",pady=2)
        ttk.Entry(ocr_video_side,textvariable=var).grid(row=row_no,column=1,sticky="ew",pady=2)
    ocr_candidate_list = tk.Listbox(ocr_video_side,height=7,selectmode="extended")
    ocr_candidate_list.grid(row=3,column=0,columnspan=2,sticky="nsew",pady=(6,4))
    ocr_video_side.rowconfigure(3,weight=1)
    ocr_candidates: list[OcrVideoCandidate] = []

    def scan_ocr_video() -> None:
        try:
            video = video_vars["video"].get().strip()
            start = int(video_vars["start"].get()); end = int(video_vars["end"].get()); step = int(video_vars["step"].get())
            maximum = int(video_vars["max_samples"].get())
        except Exception as exc:
            messagebox.showerror("OCR video scan",str(exc)); return
        def done(report) -> None:
            ocr_candidates.clear(); ocr_candidates.extend(report.candidates)
            ocr_candidate_list.delete(0,"end")
            for item in report.candidates:
                ocr_candidate_list.insert("end",f"frame {item.frame_index}: {item.text}")
            status.set(f"OCR video scan: candidates={len(report.candidates)} rejected={report.rejected}")
            if report.rejected:
                messagebox.showwarning("OCR video scan", "\n".join([f"Candidates: {len(report.candidates)}", *report.errors[:10]]))
        run_background(
            "OCR video scan",
            lambda: workspace.scan_upper_right_ocr_from_video(
                video_path=video,start_frame=start,end_frame_exclusive=end,frame_step=step,
                roi_profile_path=video_vars["roi_profile"].get().strip() or None,
                ffmpeg_executable=video_vars["ffmpeg"].get().strip() or "ffmpeg",
                tesseract_executable=ocr_video_tesseract.get().strip() or "tesseract",
                language=ocr_video_language.get().strip() or "jpn+eng",max_samples=maximum,
            ),
            done,
        )

    def register_selected_ocr_candidates() -> None:
        selected = tuple(int(i) for i in ocr_candidate_list.curselection())
        if not selected:
            messagebox.showinfo("OCR video learning","Select one or more OCR candidates first."); return
        accepted = duplicates = 0
        for index in selected:
            candidate = ocr_candidates[index]
            item = OcrVocabularySample(
                signal_id=ocr_video_signal.get().strip().upper(),
                phrase=candidate.text.strip(),
                locale="ja-JP",
                source_ref=f"{Path(candidate.image_path).resolve().as_uri()}#frame={candidate.frame_index}",
            )
            if workspace.ocr.append(item): accepted += 1
            else: duplicates += 1
        refresh_ocr()
        messagebox.showinfo("OCR video learning",f"Registered={accepted} Duplicates={duplicates}")

    ocr_video_buttons=ttk.Frame(ocr_video_side); ocr_video_buttons.grid(row=4,column=0,columnspan=2,sticky="w",pady=4)
    ttk.Button(ocr_video_buttons,text="Scan video OCR candidates",command=scan_ocr_video).pack(side="left",padx=(0,6))
    ttk.Button(ocr_video_buttons,text="Register selected phrases",command=register_selected_ocr_candidates).pack(side="left")

    # ---- Visual training tab -------------------------------------------------
    visual_tab = ttk.Frame(notebook, padding=12)
    notebook.add(visual_tab, text="Visual Training")
    visual_tab.columnconfigure(1, weight=1)
    visual_vars = {
        "domain": tk.StringVar(value=VisualTrainingDomain.PERK_ICON.value),
        "label": tk.StringVar(),
        "image": tk.StringVar(),
        "group": tk.StringVar(value="normal"),
        "source": tk.StringVar(value="manual://owner"),
        "notes": tk.StringVar(),
        "index_id": tk.StringVar(value="dbd-perk-icons-v1"),
    }
    ttk.Label(visual_tab, text="Target").grid(row=0, column=0, sticky="w", pady=3)
    domain_combo = ttk.Combobox(visual_tab, textvariable=visual_vars["domain"], values=[x.value for x in VisualTrainingDomain], state="readonly")
    domain_combo.grid(row=0, column=1, sticky="ew", pady=3)
    for row_no, (label, key) in enumerate((("Label", "label"),("Image slice", "image"),("Visual group", "group"),("Source ref", "source"),("Notes", "notes"),("Index ID", "index_id")), start=1):
        ttk.Label(visual_tab, text=label).grid(row=row_no, column=0, sticky="w", pady=3)
        ttk.Entry(visual_tab, textvariable=visual_vars[key]).grid(row=row_no, column=1, sticky="ew", pady=3)
    def choose_visual_image() -> None:
        chosen = filedialog.askopenfilename(title="Select training slice", filetypes=[("Image", "*.pgm *.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if chosen: visual_vars["image"].set(chosen)
    ttk.Button(visual_tab, text="Browse image", command=choose_visual_image).grid(row=2, column=2, padx=(8,0))

    visual_count = tk.StringVar()
    ttk.Label(visual_tab, textvariable=visual_count).grid(row=7, column=1, sticky="w", pady=(8,4))

    def refresh_visual_count() -> None:
        domain = VisualTrainingDomain(visual_vars["domain"].get())
        visual_count.set(f"Registered: {len(workspace.visual.list(domain=domain))} samples for {domain.value}")
        defaults = {
            VisualTrainingDomain.PERK_ICON: "dbd-perk-icons-v1",
            VisualTrainingDomain.SURVIVOR_HUD: "dbd-survivor-hud-v1",
            VisualTrainingDomain.ITEM_ICON: "dbd-item-icons-v1",
            VisualTrainingDomain.ADDON_ICON: "dbd-addon-icons-v1",
            VisualTrainingDomain.KILLER_POWER: "dbd-killer-power-v1",
        }
        if not visual_vars["index_id"].get().strip() or visual_vars["index_id"].get().startswith("dbd-"):
            visual_vars["index_id"].set(defaults[domain])

    def add_visual_one() -> None:
        try:
            path = Path(visual_vars["image"].get())
            if not path.is_file():
                raise ValueError("Image slice does not exist")
            item = VisualTrainingSample(
                domain=VisualTrainingDomain(visual_vars["domain"].get()),
                label=visual_vars["label"].get(), image_path=str(path), group=visual_vars["group"].get(),
                source_ref=visual_vars["source"].get(), notes=visual_vars["notes"].get(),
            )
            added = workspace.visual.append(item)
            messagebox.showinfo("Visual sample", "Registered 1 sample." if added else "The same sample is already registered; no duplicate was added.")
            refresh_visual_count()
        except Exception as exc:
            messagebox.showerror("Visual registration failed", str(exc))

    def import_visual_csv() -> None:
        chosen = filedialog.askopenfilename(title="Import visual training CSV", filetypes=[("CSV","*.csv"),("All files","*.*")])
        if not chosen: return
        report_message("Visual CSV import", workspace.visual.import_csv(chosen, default_domain=VisualTrainingDomain(visual_vars["domain"].get())))
        refresh_visual_count()

    def build_visual_index() -> None:
        try:
            domain = VisualTrainingDomain(visual_vars["domain"].get())
            default_name = {
                VisualTrainingDomain.PERK_ICON: "perk-index.json",
                VisualTrainingDomain.SURVIVOR_HUD: "survivor-index.json",
                VisualTrainingDomain.KILLER_POWER: "killer-power-index.json",
            }[domain]
            target = filedialog.asksaveasfilename(title="Save reference index", initialdir=str(workspace.root / "indexes"), initialfile=default_name, defaultextension=".json", filetypes=[("JSON","*.json")])
            if not target: return
            path = workspace.visual.build_reference_index(domain=domain, output_path=target, index_id=visual_vars["index_id"].get().strip())
            status.set(f"Built {domain.value} index: {path}")
            messagebox.showinfo("Reference index", f"Built:\n{path}")
        except Exception as exc:
            messagebox.showerror("Index build failed", str(exc))

    visual_buttons = ttk.Frame(visual_tab); visual_buttons.grid(row=8, column=1, sticky="w", pady=8)
    ttk.Button(visual_buttons, text="Register 1 sample", command=add_visual_one).pack(side="left", padx=(0,6))
    ttk.Button(visual_buttons, text="Import CSV (1 or many rows)", command=import_visual_csv).pack(side="left", padx=(0,6))
    ttk.Button(visual_buttons, text="Build reference index", command=build_visual_index).pack(side="left")
    ttk.Label(visual_tab, text=f"CSV template: {templates[0]}", wraplength=900).grid(row=9, column=1, sticky="w", pady=(8,0))
    domain_combo.bind("<<ComboboxSelected>>", lambda _event: refresh_visual_count())
    refresh_visual_count()

    # ---- OCR vocabulary tab --------------------------------------------------
    ocr_tab = ttk.Frame(notebook, padding=12); notebook.add(ocr_tab, text="Upper-right OCR")
    ocr_tab.columnconfigure(1, weight=1)
    ocr_signal = tk.StringVar(value="CHASE"); ocr_phrase = tk.StringVar(); ocr_locale = tk.StringVar(value="ja-JP"); ocr_source = tk.StringVar(value="manual://owner"); ocr_id = tk.StringVar(value="dbd-upper-right-vocabulary-v1")
    for row_no, (label, var) in enumerate((("Signal ID",ocr_signal),("Phrase",ocr_phrase),("Locale",ocr_locale),("Source ref",ocr_source),("Vocabulary ID",ocr_id))):
        ttk.Label(ocr_tab, text=label).grid(row=row_no,column=0,sticky="w",pady=3)
        ttk.Entry(ocr_tab,textvariable=var).grid(row=row_no,column=1,sticky="ew",pady=3)
    ocr_count = tk.StringVar(); ttk.Label(ocr_tab,textvariable=ocr_count).grid(row=5,column=1,sticky="w",pady=(8,4))
    def refresh_ocr() -> None: ocr_count.set(f"Registered: {len(workspace.ocr.list())} phrases")
    def add_ocr_one() -> None:
        try:
            added=workspace.ocr.append(OcrVocabularySample(ocr_signal.get().strip().upper(),ocr_phrase.get().strip(),ocr_locale.get().strip(),ocr_source.get().strip()))
            messagebox.showinfo("OCR vocabulary", "Registered 1 phrase." if added else "The same phrase is already registered."); refresh_ocr()
        except Exception as exc: messagebox.showerror("OCR registration failed",str(exc))
    def import_ocr_csv() -> None:
        chosen=filedialog.askopenfilename(title="Import OCR vocabulary CSV",filetypes=[("CSV","*.csv"),("All files","*.*")])
        if chosen: report_message("OCR CSV import",workspace.ocr.import_csv(chosen)); refresh_ocr()
    def build_ocr() -> None:
        try:
            target=filedialog.asksaveasfilename(title="Save OCR vocabulary",initialdir=str(workspace.root/"indexes"),initialfile="upper-right-vocabulary.json",defaultextension=".json",filetypes=[("JSON","*.json")])
            if target:
                path=workspace.ocr.build_vocabulary(output_path=target,vocabulary_id=ocr_id.get().strip()); messagebox.showinfo("OCR vocabulary",f"Built:\n{path}")
        except Exception as exc: messagebox.showerror("Vocabulary build failed",str(exc))
    ocr_buttons=ttk.Frame(ocr_tab); ocr_buttons.grid(row=6,column=1,sticky="w",pady=8)
    ttk.Button(ocr_buttons,text="Register 1 phrase",command=add_ocr_one).pack(side="left",padx=(0,6))
    ttk.Button(ocr_buttons,text="Import CSV (1 or many rows)",command=import_ocr_csv).pack(side="left",padx=(0,6))
    ttk.Button(ocr_buttons,text="Build vocabulary JSON",command=build_ocr).pack(side="left")
    ttk.Label(ocr_tab,text=f"CSV template: {templates[1]}",wraplength=900).grid(row=7,column=1,sticky="w",pady=(8,0)); refresh_ocr()

    # ---- Trivia tab ----------------------------------------------------------
    trivia_tab=ttk.Frame(notebook,padding=12); notebook.add(trivia_tab,text="Commentary Trivia")
    trivia_tab.columnconfigure(1,weight=1)
    trivia_title=tk.StringVar(); trivia_category=tk.StringVar(value="GENERAL"); trivia_tags=tk.StringVar(); trivia_events=tk.StringVar(); trivia_entities=tk.StringVar(); trivia_source=tk.StringVar(value="manual://owner"); trivia_env=tk.StringVar(value="LIVE"); trivia_from=tk.StringVar(); trivia_to=tk.StringVar(); trivia_verify=tk.BooleanVar(value=False)
    rows=(("Title",trivia_title),("Category",trivia_category),("Tags (comma)",trivia_tags),("Event types (comma)",trivia_events),("Entity refs (comma)",trivia_entities),("Source ref",trivia_source),("Game version from",trivia_from),("Game version to",trivia_to))
    for row_no,(label,var) in enumerate(rows):
        ttk.Label(trivia_tab,text=label).grid(row=row_no,column=0,sticky="w",pady=3); ttk.Entry(trivia_tab,textvariable=var).grid(row=row_no,column=1,sticky="ew",pady=3)
    ttk.Label(trivia_tab,text="Environment").grid(row=8,column=0,sticky="w",pady=3); ttk.Combobox(trivia_tab,textvariable=trivia_env,values=[x.value for x in PerkEnvironment],state="readonly").grid(row=8,column=1,sticky="ew",pady=3)
    ttk.Checkbutton(trivia_tab,text="Register as VERIFIED (manual owner fact)",variable=trivia_verify).grid(row=9,column=1,sticky="w",pady=3)
    ttk.Label(trivia_tab,text="Trivia text").grid(row=10,column=0,sticky="nw",pady=3); trivia_text=tk.Text(trivia_tab,height=7,wrap="word"); trivia_text.grid(row=10,column=1,sticky="ew",pady=3)
    trivia_count=tk.StringVar(); ttk.Label(trivia_tab,textvariable=trivia_count).grid(row=11,column=1,sticky="w",pady=(8,4))
    def refresh_trivia() -> None: trivia_count.set(f"Registered: {len(workspace.trivia.list_latest())} trivia entries")
    def split(value: str) -> tuple[str,...]: return tuple(x.strip() for x in value.split(",") if x.strip())
    def add_trivia_one() -> None:
        try:
            events=tuple(GameEventType(x.upper()) for x in split(trivia_events.get()))
            workspace.trivia.create_manual(title=trivia_title.get(),text=trivia_text.get("1.0","end").strip(),source_ref=trivia_source.get(),category=trivia_category.get(),tags=split(trivia_tags.get()),event_types=events,entity_refs=split(trivia_entities.get()),environment=PerkEnvironment(trivia_env.get()),game_version_from=trivia_from.get().strip() or None,game_version_to=trivia_to.get().strip() or None,verify=trivia_verify.get())
            messagebox.showinfo("Trivia", "Registered 1 trivia entry."); refresh_trivia()
        except Exception as exc: messagebox.showerror("Trivia registration failed",str(exc))
    def import_trivia_csv() -> None:
        chosen=filedialog.askopenfilename(title="Import trivia CSV",filetypes=[("CSV","*.csv"),("All files","*.*")])
        if chosen: report_message("Trivia CSV import",workspace.import_trivia_csv(chosen)); refresh_trivia()
    trivia_buttons=ttk.Frame(trivia_tab); trivia_buttons.grid(row=12,column=1,sticky="w",pady=8)
    ttk.Button(trivia_buttons,text="Register 1 trivia",command=add_trivia_one).pack(side="left",padx=(0,6))
    ttk.Button(trivia_buttons,text="Import CSV (1 or many rows)",command=import_trivia_csv).pack(side="left")
    ttk.Label(trivia_tab,text=f"CSV template: {templates[2]}",wraplength=900).grid(row=13,column=1,sticky="w",pady=(8,0))

    ttk.Separator(trivia_tab, orient="horizontal").grid(row=14,column=0,columnspan=2,sticky="ew",pady=8)
    trivia_video = tk.StringVar(); trivia_model = tk.StringVar(value="small"); trivia_device = tk.StringVar(value="auto"); trivia_compute = tk.StringVar(value="int8"); trivia_language = tk.StringVar(value="ja"); trivia_allow_download = tk.BooleanVar(value=False)
    ttk.Label(trivia_tab,text="Mine CANDIDATE trivia from video").grid(row=15,column=0,sticky="w",pady=3)
    trivia_video_frame=ttk.Frame(trivia_tab); trivia_video_frame.grid(row=15,column=1,sticky="ew",pady=3); trivia_video_frame.columnconfigure(0,weight=1)
    ttk.Entry(trivia_video_frame,textvariable=trivia_video).grid(row=0,column=0,sticky="ew")
    def choose_trivia_video() -> None:
        chosen=filedialog.askopenfilename(title="Select commentary / gameplay video",filetypes=[("Video","*.mp4 *.mkv *.mov *.avi *.webm"),("All files","*.*")])
        if chosen: trivia_video.set(chosen)
    ttk.Button(trivia_video_frame,text="Browse",command=choose_trivia_video).grid(row=0,column=1,padx=(8,0))
    trivia_asr_frame=ttk.Frame(trivia_tab); trivia_asr_frame.grid(row=16,column=1,sticky="ew",pady=3)
    for idx in range(4): trivia_asr_frame.columnconfigure(idx,weight=1)
    ttk.Entry(trivia_asr_frame,textvariable=trivia_model,width=12).grid(row=0,column=0,sticky="ew",padx=(0,3))
    ttk.Combobox(trivia_asr_frame,textvariable=trivia_device,values=("auto","cpu","cuda"),state="readonly",width=10).grid(row=0,column=1,sticky="ew",padx=3)
    ttk.Entry(trivia_asr_frame,textvariable=trivia_compute,width=10).grid(row=0,column=2,sticky="ew",padx=3)
    ttk.Entry(trivia_asr_frame,textvariable=trivia_language,width=8).grid(row=0,column=3,sticky="ew",padx=(3,0))
    ttk.Label(trivia_asr_frame,text="model / device / compute / language",anchor="center").grid(row=1,column=0,columnspan=4,sticky="ew")
    ttk.Checkbutton(trivia_tab,text="Allow local FasterWhisper model download (network)",variable=trivia_allow_download).grid(row=17,column=1,sticky="w",pady=3)

    def mine_trivia_video() -> None:
        video=trivia_video.get().strip()
        if not video:
            messagebox.showerror("Video trivia learning","Select a video first."); return
        def done(report) -> None:
            refresh_trivia(); status.set(f"Video trivia: mined={report.mined_candidates}")
            messagebox.showinfo("Video trivia learning",f"Mined CANDIDATE trivia: {report.mined_candidates}\nTranscript: {report.transcript_path}\nSRT: {report.subtitle_path}\n\nCandidates still require Human review before automatic reuse.")
        run_background(
            "Video trivia learning",
            lambda: workspace.mine_trivia_from_video(
                video_path=video,model=trivia_model.get().strip() or "small",
                device=trivia_device.get().strip() or "auto",compute_type=trivia_compute.get().strip() or "int8",
                language=trivia_language.get().strip() or None,allow_model_download=trivia_allow_download.get(),
            ),
            done,
        )

    def mine_trivia_transcript() -> None:
        chosen=filedialog.askopenfilename(title="Select BVP TranscriptManifest JSON",filetypes=[("JSON","*.json"),("All files","*.*")])
        if not chosen: return
        run_background(
            "Transcript trivia learning",
            lambda: workspace.mine_trivia_from_transcript(chosen),
            lambda count: (refresh_trivia(),status.set(f"Transcript trivia: mined={count}"),messagebox.showinfo("Transcript trivia learning",f"Mined CANDIDATE trivia: {count}")),
        )

    trivia_learning_buttons=ttk.Frame(trivia_tab); trivia_learning_buttons.grid(row=18,column=1,sticky="w",pady=6)
    ttk.Button(trivia_learning_buttons,text="Transcribe video + mine candidates",command=mine_trivia_video).pack(side="left",padx=(0,6))
    ttk.Button(trivia_learning_buttons,text="Mine from existing Transcript JSON",command=mine_trivia_transcript).pack(side="left")
    refresh_trivia()

    # ---- HUD Calibration tab --------------------------------------------------
    calibration_tab = ttk.Frame(notebook, padding=12)
    notebook.add(calibration_tab, text="HUD Calibration")
    calibration_tab.columnconfigure(1, weight=1)
    calibration_tab.rowconfigure(8, weight=1)

    calibration_registry = HudProfileRegistry(workspace.root / "hud_profiles")
    calibration_inspector = FFmpegFrameInspector()
    calibration_vars = {
        "source": tk.StringVar(),
        "frame": tk.StringVar(value="0"),
        "profile_id": tk.StringVar(value="dbd-calibrated-16x9-v1"),
        "profile_version": tk.StringVar(value="1"),
        "ui_scale": tk.StringVar(value="100"),
        "game_from": tk.StringVar(),
        "game_to": tk.StringVar(),
        "target": tk.StringVar(value="bottom_right_perks"),
        "loaded_profile": tk.StringVar(),
    }
    calibration_state: dict[str, object] = {
        "preview_path": None,
        "source_geometry": None,
        "preview_geometry": None,
        "photo": None,
        "rois": {},
        "drag_start": None,
    }

    target_ids = [
        "lower_left_survivor_hud", "lower_left_loadout_hud", "upper_right_notifications", "bottom_right_perks",
        *[f"survivor_slot_{i}" for i in range(4)],
        "item_slot", *[f"addon_slot_{i}" for i in range(2)],
        *[f"perk_slot_{i}" for i in range(4)],
        "killer_power_hud",
    ]

    def rois_from_profile(profile: DBDHudRoiProfile) -> dict[str, NormalizedROI]:
        rows = {
            profile.lower_left_survivor_hud.roi_id: profile.lower_left_survivor_hud,
            profile.upper_right_notifications.roi_id: profile.upper_right_notifications,
            profile.bottom_right_perks.roi_id: profile.bottom_right_perks,
        }
        if profile.lower_left_loadout_hud is not None:
            rows[profile.lower_left_loadout_hud.roi_id] = profile.lower_left_loadout_hud
        if profile.item_slot is not None:
            rows[profile.item_slot.roi_id] = profile.item_slot
        rows.update({item.roi_id: item for item in profile.addon_slots})
        rows.update({item.roi_id: item for item in profile.survivor_slots})
        rows.update({item.roi_id: item for item in profile.perk_slots})
        if profile.killer_power_hud is not None:
            rows[profile.killer_power_hud.roi_id] = profile.killer_power_hud
        return rows

    calibration_state["rois"] = rois_from_profile(DBDHudRoiProfile())

    ttk.Label(calibration_tab, text="Video / still image").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(calibration_tab, textvariable=calibration_vars["source"]).grid(row=0, column=1, sticky="ew", pady=3)
    def choose_calibration_source() -> None:
        chosen = filedialog.askopenfilename(
            title="Select DbD video or still frame",
            filetypes=[("Media", "*.mp4 *.mkv *.mov *.avi *.webm *.png *.jpg *.jpeg *.bmp *.pgm"), ("All files", "*.*")],
        )
        if chosen:
            calibration_vars["source"].set(chosen)
    ttk.Button(calibration_tab, text="Browse", command=choose_calibration_source).grid(row=0, column=2, padx=(8, 0))

    ttk.Label(calibration_tab, text="Frame index (still image = 0)").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(calibration_tab, textvariable=calibration_vars["frame"]).grid(row=1, column=1, sticky="ew", pady=3)

    profile_meta = ttk.Frame(calibration_tab); profile_meta.grid(row=2, column=0, columnspan=3, sticky="ew", pady=3)
    for idx in range(6): profile_meta.columnconfigure(idx, weight=1)
    for idx, (label, key) in enumerate((("Profile ID", "profile_id"), ("Version", "profile_version"), ("UI Scale %", "ui_scale"), ("Game from", "game_from"), ("Game to", "game_to"))):
        ttk.Label(profile_meta, text=label).grid(row=0, column=idx, sticky="w", padx=(0, 4))
        ttk.Entry(profile_meta, textvariable=calibration_vars[key], width=18).grid(row=1, column=idx, sticky="ew", padx=(0, 6))

    target_row = ttk.Frame(calibration_tab); target_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)
    ttk.Label(target_row, text="ROI target").pack(side="left")
    ttk.Combobox(target_row, textvariable=calibration_vars["target"], values=target_ids, state="readonly", width=34).pack(side="left", padx=8)
    ttk.Label(target_row, text="Drag a rectangle on the preview. Normalized coordinates are saved.").pack(side="left", padx=8)

    calibration_canvas = tk.Canvas(calibration_tab, width=960, height=540, background="black", highlightthickness=1)
    calibration_canvas.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(8, 6))

    def redraw_calibration_overlay() -> None:
        calibration_canvas.delete("roi")
        geom = calibration_state.get("preview_geometry")
        if geom is None:
            return
        width, height = geom.width, geom.height
        rois = calibration_state["rois"]
        for roi_id, roi in sorted(rois.items()):
            x1, y1 = roi.x * width, roi.y * height
            x2, y2 = (roi.x + roi.width) * width, (roi.y + roi.height) * height
            calibration_canvas.create_rectangle(x1, y1, x2, y2, outline="white", width=1, tags="roi")
            calibration_canvas.create_text(x1 + 3, y1 + 3, text=roi_id, anchor="nw", fill="white", tags="roi")

    def load_calibration_preview() -> None:
        source = calibration_vars["source"].get().strip()
        if not source:
            messagebox.showerror("HUD Calibration", "Select a video or still image first."); return
        try:
            frame_index = int(calibration_vars["frame"].get())
            preview_dir = workspace.root / "hud_profiles" / "_preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_path, source_geometry, preview_geometry = calibration_inspector.extract_preview_pgm(
                source_path=source, frame_index=frame_index, output_path=preview_dir / "current-preview.pgm",
            )
            photo = tk.PhotoImage(file=str(preview_path))
        except Exception as exc:
            messagebox.showerror("HUD Calibration", str(exc)); return
        calibration_state.update({
            "preview_path": preview_path,
            "source_geometry": source_geometry,
            "preview_geometry": preview_geometry,
            "photo": photo,
        })
        calibration_canvas.config(width=preview_geometry.width, height=preview_geometry.height, scrollregion=(0, 0, preview_geometry.width, preview_geometry.height))
        calibration_canvas.delete("all")
        calibration_canvas.create_image(0, 0, image=photo, anchor="nw", tags="preview")
        redraw_calibration_overlay()
        status.set(f"HUD Calibration preview: {source_geometry.width}x{source_geometry.height} frame={frame_index}")

    def calibration_press(event) -> None:
        calibration_state["drag_start"] = (event.x, event.y)

    def calibration_release(event) -> None:
        start = calibration_state.get("drag_start")
        geom = calibration_state.get("preview_geometry")
        if start is None or geom is None:
            return
        x1, y1 = start; x2, y2 = event.x, event.y
        left, top = max(0, min(x1, x2)), max(0, min(y1, y2))
        right, bottom = min(geom.width, max(x1, x2)), min(geom.height, max(y1, y2))
        if right - left < 4 or bottom - top < 4:
            messagebox.showwarning("HUD Calibration", "ROI must be at least 4 preview pixels wide/high."); return
        roi_id = calibration_vars["target"].get()
        try:
            roi = NormalizedROI(roi_id, left / geom.width, top / geom.height, (right-left) / geom.width, (bottom-top) / geom.height)
        except Exception as exc:
            messagebox.showerror("HUD Calibration", str(exc)); return
        calibration_state["rois"][roi_id] = roi
        calibration_state["drag_start"] = None
        redraw_calibration_overlay()
        status.set(f"HUD Calibration ROI updated: {roi_id}")

    calibration_canvas.bind("<ButtonPress-1>", calibration_press)
    calibration_canvas.bind("<ButtonRelease-1>", calibration_release)

    def build_calibrated_profile(*, with_anchors: bool) -> DBDHudRoiProfile:
        geometry = calibration_state.get("source_geometry")
        if geometry is None:
            raise ValueError("Load a calibration preview first")
        rois: dict[str, NormalizedROI] = calibration_state["rois"]
        profile_id = calibration_vars["profile_id"].get().strip()
        ui_text = calibration_vars["ui_scale"].get().strip()
        profile = DBDHudRoiProfile(
            profile_id=profile_id,
            profile_version=int(calibration_vars["profile_version"].get()),
            calibrated_frame_width=geometry.width,
            calibrated_frame_height=geometry.height,
            ui_scale_percent=None if not ui_text else int(ui_text),
            game_version_from=calibration_vars["game_from"].get().strip() or None,
            game_version_to=calibration_vars["game_to"].get().strip() or None,
            calibration_source_ref=calibration_vars["source"].get().strip(),
            anchors=(),
            lower_left_survivor_hud=rois["lower_left_survivor_hud"],
            upper_right_notifications=rois["upper_right_notifications"],
            bottom_right_perks=rois["bottom_right_perks"],
            lower_left_loadout_hud=rois.get("lower_left_loadout_hud"),
            item_slot=rois.get("item_slot"),
            addon_slots=tuple(rois[f"addon_slot_{i}"] for i in range(2)) if all(f"addon_slot_{i}" in rois for i in range(2)) else (),
            survivor_slots=tuple(rois[f"survivor_slot_{i}"] for i in range(4)),
            perk_slots=tuple(rois[f"perk_slot_{i}"] for i in range(4)),
            killer_power_hud=rois.get("killer_power_hud"),
        )
        if not with_anchors:
            return profile
        preview_path = calibration_state.get("preview_path")
        if preview_path is None:
            raise ValueError("Calibration preview is missing")
        image = GrayImage.read_pgm(preview_path)
        anchors = []
        for roi_id in ("lower_left_survivor_hud", "lower_left_loadout_hud", "upper_right_notifications", "bottom_right_perks", "killer_power_hud"):
            roi = rois.get(roi_id)
            if roi is not None:
                anchors.append(calibration_registry.store_anchor(profile_id=profile.profile_id, roi=roi, image=image, source_ref=profile.calibration_source_ref or "manual://hud-calibration"))
        return DBDHudRoiProfile.from_dict({**profile.to_dict(), "anchors": [anchor.to_dict() for anchor in anchors]})

    def refresh_calibration_profiles() -> None:
        profile_ids = [item.profile_id for item in calibration_registry.list_profiles()]
        calibration_profile_combo["values"] = profile_ids
        if profile_ids and not calibration_vars["loaded_profile"].get():
            calibration_vars["loaded_profile"].set(profile_ids[0])

    def save_calibration_profile() -> None:
        try:
            profile = build_calibrated_profile(with_anchors=True)
            path = calibration_registry.save(profile)
        except Exception as exc:
            messagebox.showerror("HUD Calibration", str(exc)); return
        refresh_calibration_profiles()
        calibration_vars["loaded_profile"].set(profile.profile_id)
        status.set(f"HUD profile saved: {profile.profile_id}")
        messagebox.showinfo("HUD Calibration", f"Saved profile:\n{path}\n\nAnchors: {len(profile.anchors)}")

    def load_calibration_profile() -> None:
        profile_id = calibration_vars["loaded_profile"].get().strip()
        if not profile_id:
            return
        try:
            profile = calibration_registry.load(profile_id)
        except Exception as exc:
            messagebox.showerror("HUD Calibration", str(exc)); return
        calibration_vars["profile_id"].set(profile.profile_id)
        calibration_vars["profile_version"].set(str(profile.profile_version))
        calibration_vars["ui_scale"].set("" if profile.ui_scale_percent is None else str(profile.ui_scale_percent))
        calibration_vars["game_from"].set(profile.game_version_from or "")
        calibration_vars["game_to"].set(profile.game_version_to or "")
        calibration_state["rois"] = rois_from_profile(profile)
        redraw_calibration_overlay()
        status.set(f"HUD profile loaded: {profile.profile_id}")

    def test_profile_resolution_and_anchor() -> None:
        source = calibration_vars["source"].get().strip()
        if not source:
            messagebox.showerror("HUD Calibration", "Select a video first."); return
        try:
            frame_index = int(calibration_vars["frame"].get())
            ui_text = calibration_vars["ui_scale"].get().strip()
            resolver = DBDHudVideoProfileResolver(calibration_registry)
            resolution = resolver.resolve_video(
                video_path=source, frame_index=frame_index,
                ui_scale_percent=None if not ui_text else int(ui_text),
                game_version=calibration_vars["game_from"].get().strip() or None,
            )
            geometry = calibration_inspector.probe_geometry(source)
            alignment = HudAnchorAligner().align(
                video_path=source, frame_index=frame_index, profile=resolution.profile,
                frame_width=geometry.width, frame_height=geometry.height,
                working_directory=workspace.root / "hud_profiles" / "_alignment-test",
            )
        except Exception as exc:
            messagebox.showerror("HUD Calibration fail-closed", str(exc)); return
        details = "\n".join(f"{item.roi_id}: dx={item.dx_normalized:.6f} dy={item.dy_normalized:.6f} confidence={item.confidence_milli}" for item in alignment.corrections) or "No anchors/correction required"
        messagebox.showinfo(
            "HUD Profile resolution",
            f"Profile: {resolution.profile.profile_id}\nResolve score: {resolution.score_milli}\nAnchor score: {alignment.confidence_milli}\n\n{details}",
        )

    control_row = ttk.Frame(calibration_tab); control_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=4)
    ttk.Button(control_row, text="Load preview", command=load_calibration_preview).pack(side="left", padx=(0, 6))
    ttk.Button(control_row, text="Save versioned profile + anchors", command=save_calibration_profile).pack(side="left", padx=6)
    ttk.Button(control_row, text="Test auto profile + anchor correction", command=test_profile_resolution_and_anchor).pack(side="left", padx=6)

    profile_row = ttk.Frame(calibration_tab); profile_row.grid(row=5, column=0, columnspan=3, sticky="ew", pady=4)
    ttk.Label(profile_row, text="Registered profiles").pack(side="left")
    calibration_profile_combo = ttk.Combobox(profile_row, textvariable=calibration_vars["loaded_profile"], state="readonly", width=42)
    calibration_profile_combo.pack(side="left", padx=8)
    ttk.Button(profile_row, text="Load profile", command=load_calibration_profile).pack(side="left")
    refresh_calibration_profiles()

    ttk.Label(
        calibration_tab,
        text="Runtime behavior: profile resolution and anchor alignment are fail-closed. If no profile is compatible or anchor confidence is insufficient, recognition must stop and request calibration rather than guess coordinates.",
        wraplength=920,
    ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(6, 0))

    # ---- Knowledge Source Import tab -----------------------------------------
    knowledge_import_tab = ttk.Frame(notebook, padding=12)
    notebook.add(knowledge_import_tab, text="Knowledge Import")
    knowledge_import_tab.columnconfigure(1, weight=1)

    ttk.Label(knowledge_import_tab, text="Kamigame DbD knowledge candidate collector", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
    ttk.Label(knowledge_import_tab, text="Collects Survivor perks, Killer perks, Killer list and optional Killer detail pages. Results remain COMMUNITY_REFERENCE / CANDIDATE and are never auto-VERIFIED.", wraplength=900).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

    kamigame_output = tk.StringVar(value=str(workspace.root / "knowledge-imports" / "kamigame"))
    kamigame_details = tk.BooleanVar(value=True)
    kamigame_max_pages = tk.StringVar(value="20")
    kamigame_max_details = tk.StringVar(value="128")
    kamigame_result = tk.StringVar(value="No collection run yet.")

    ttk.Label(knowledge_import_tab, text="Output directory").grid(row=2, column=0, sticky="w", pady=3)
    ttk.Entry(knowledge_import_tab, textvariable=kamigame_output).grid(row=2, column=1, sticky="ew", pady=3)
    def choose_kamigame_output() -> None:
        chosen = filedialog.askdirectory(title="Choose Kamigame candidate output directory")
        if chosen: kamigame_output.set(chosen)
    ttk.Button(knowledge_import_tab, text="Browse", command=choose_kamigame_output).grid(row=2, column=2, padx=(8,0))

    ttk.Checkbutton(knowledge_import_tab, text="Follow Killer detail pages", variable=kamigame_details).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)
    limits = ttk.Frame(knowledge_import_tab); limits.grid(row=4, column=1, sticky="ew", pady=3)
    limits.columnconfigure(0, weight=1); limits.columnconfigure(1, weight=1)
    ttk.Entry(limits, textvariable=kamigame_max_pages, width=12).grid(row=0, column=0, sticky="ew", padx=(0,4))
    ttk.Entry(limits, textvariable=kamigame_max_details, width=12).grid(row=0, column=1, sticky="ew", padx=(4,0))
    ttk.Label(knowledge_import_tab, text="Limits").grid(row=4, column=0, sticky="w", pady=3)
    ttk.Label(limits, text="max list pages / max killer details").grid(row=1, column=0, columnspan=2, sticky="w")

    ttk.Label(knowledge_import_tab, textvariable=kamigame_result, wraplength=900).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10,6))

    def collect_kamigame() -> None:
        try:
            out = Path(kamigame_output.get().strip())
            max_pages = int(kamigame_max_pages.get())
            max_details = int(kamigame_max_details.get())
            if max_pages < 1 or max_details < 0: raise ValueError("limits must be positive")
        except Exception as exc:
            messagebox.showerror("Kamigame Knowledge Import", str(exc)); return
        def done(manifest) -> None:
            counts = manifest.get("counts", {})
            text = (f"Survivor perks={counts.get('survivor_perks',0)} / Killer perks={counts.get('killer_perks',0)} / "
                    f"Killers={counts.get('killers',0)} / Killer details={counts.get('killer_details',0)}\n"
                    f"Saved to: {out}")
            kamigame_result.set(text); status.set("Kamigame knowledge candidate collection complete")
            messagebox.showinfo("Kamigame Knowledge Import", text + "\n\nAll records remain CANDIDATE. Review before canonical import.")
        run_background(
            "Kamigame knowledge import",
            lambda: KamigameDbDKnowledgeCollector(out).collect(
                follow_killer_details=kamigame_details.get(), max_pages=max_pages, max_killer_details=max_details
            ),
            done,
        )

    ttk.Button(knowledge_import_tab, text="Collect Survivor / Killer / Killer details", command=collect_kamigame).grid(row=6, column=0, columnspan=2, sticky="w", pady=(6,3))
    ttk.Label(knowledge_import_tab, text="Network access occurs only when you press Collect. The collector rate-limits requests, keeps raw HTML snapshots + hashes, and does not write Canonical Knowledge automatically.", wraplength=900).grid(row=7, column=0, columnspan=3, sticky="w", pady=(8,0))

    # ---- Backup / Restore tab ------------------------------------------------
    migration_tab = ttk.Frame(notebook, padding=12)
    notebook.add(migration_tab, text="Backup / Restore")
    migration_tab.columnconfigure(1, weight=1)
    ttk.Label(
        migration_tab,
        text="別PCへの移行用。Project Game Intelligence / Training data / Triviaをchecksum付きZIPに保存します。",
        wraplength=900,
    ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
    ttk.Label(
        migration_tab,
        text="Restore前はBAI Video Production / Trivia Editorを閉じてください。API Key / Credential / private keyは対象外です。",
        wraplength=900,
    ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

    migration_project = tk.StringVar()
    include_project = tk.BooleanVar(value=False)
    include_training = tk.BooleanVar(value=True)
    include_trivia = tk.BooleanVar(value=True)
    ttk.Checkbutton(migration_tab, text="Project Game Intelligence", variable=include_project).grid(row=2, column=0, sticky="w", pady=3)
    ttk.Entry(migration_tab, textvariable=migration_project).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=3)
    def choose_migration_project() -> None:
        chosen = filedialog.askdirectory(title="Select BAI Video Production project root")
        if chosen:
            migration_project.set(chosen)
            include_project.set(True)
    ttk.Button(migration_tab, text="Project folder...", command=choose_migration_project).grid(row=2, column=2, sticky="e", pady=3)

    ttk.Checkbutton(migration_tab, text="Training Studio workspace (slice / CSV / index / OCR / transcript / training trivia)", variable=include_training).grid(row=3, column=0, columnspan=3, sticky="w", pady=3)
    ttk.Checkbutton(migration_tab, text="Global Trivia Editor knowledge DB", variable=include_trivia).grid(row=4, column=0, columnspan=3, sticky="w", pady=3)

    migration_last_bundle = tk.StringVar()
    ttk.Label(migration_tab, text="Backup / Restore ZIP").grid(row=5, column=0, sticky="w", pady=(12, 3))
    ttk.Entry(migration_tab, textvariable=migration_last_bundle, state="readonly").grid(row=5, column=1, sticky="ew", padx=(8, 8), pady=(12, 3))

    def migration_service() -> DbDDataMigrationService:
        return DbDDataMigrationService(training_root=workspace.root)

    def selected_project_or_none() -> str | None:
        value = migration_project.get().strip()
        return value or None

    def create_migration_backup() -> None:
        if not any((include_project.get(), include_training.get(), include_trivia.get())):
            messagebox.showerror("Backup", "Select at least one data scope.")
            return
        if include_project.get() and not selected_project_or_none():
            messagebox.showerror("Backup", "Select the BAI Video Production project folder or turn off Project Game Intelligence.")
            return
        chosen = filedialog.asksaveasfilename(
            title="Save DbD migration backup",
            defaultextension=".zip",
            filetypes=[("Migration ZIP", "*.zip")],
            initialfile="bvp-dbd-data-migration.zip",
        )
        if not chosen:
            return
        def done(receipt) -> None:
            migration_last_bundle.set(str(receipt.path))
            status.set(f"Migration backup: {receipt.entry_count} files")
            messagebox.showinfo(
                "Backup complete",
                f"Backup: {receipt.path}\nFiles: {receipt.entry_count}\nBytes: {receipt.total_bytes}\nManifest: {receipt.manifest_sha256}\n\nCredentials are not included.",
            )
        run_background(
            "DbD data backup",
            lambda: migration_service().create_backup(
                chosen,
                project_root=selected_project_or_none(),
                include_project=include_project.get(),
                include_training=include_training.get(),
                include_trivia=include_trivia.get(),
            ),
            done,
        )

    def choose_restore_bundle() -> str | None:
        chosen = filedialog.askopenfilename(title="Select DbD migration backup", filetypes=[("Migration ZIP", "*.zip"), ("All files", "*.*")])
        if chosen:
            migration_last_bundle.set(chosen)
        return chosen or None

    def preview_migration_restore() -> None:
        chosen = choose_restore_bundle()
        if not chosen:
            return
        try:
            preview = migration_service().preview_restore(chosen, project_root=selected_project_or_none())
        except Exception as exc:
            messagebox.showerror("Restore preview failed", str(exc))
            return
        if preview.requires_project_root:
            messagebox.showwarning("Restore preview", "This backup contains Project Game Intelligence data. Select the destination BVP project folder and preview again.")
            return
        conflict_text = "\n".join(preview.conflicts[:12]) if preview.conflicts else "None"
        if len(preview.conflicts) > 12:
            conflict_text += f"\n... and {len(preview.conflicts)-12} more"
        messagebox.showinfo(
            "Restore preview",
            f"Bundle: {preview.bundle_id}\nFiles: {preview.entry_count}\nBytes: {preview.total_bytes}\nScopes: {', '.join(preview.scopes)}\nConflicts: {len(preview.conflicts)}\n{conflict_text}\n\nNo files were changed.",
        )

    def restore_migration_bundle() -> None:
        chosen = migration_last_bundle.get().strip()
        if not chosen:
            chosen = choose_restore_bundle() or ""
        if not chosen:
            return
        try:
            preview = migration_service().preview_restore(chosen, project_root=selected_project_or_none())
        except Exception as exc:
            messagebox.showerror("Restore failed", str(exc))
            return
        if preview.requires_project_root:
            messagebox.showerror("Restore", "Select the destination BAI Video Production project folder first.")
            return
        replace = bool(preview.conflicts)
        details = (
            f"Restore {preview.entry_count} files from backup?\n\n"
            f"Conflicting existing files: {len(preview.conflicts)}\n"
            "If conflicts exist, a pre-restore safety backup is created automatically.\n"
            "Close BAI Video Production / Trivia Editor before continuing."
        )
        if not messagebox.askyesno("Confirm restore", details):
            return
        def done(receipt) -> None:
            try:
                refresh_visual(); refresh_ocr(); refresh_trivia()
            except Exception:
                pass
            status.set(f"Restore complete: {receipt.restored_files} files")
            safety = str(receipt.safety_backup_path) if receipt.safety_backup_path else "Not required"
            messagebox.showinfo(
                "Restore complete",
                f"Restored: {receipt.restored_files}\nReplaced: {receipt.replaced_files}\nNew: {receipt.new_files}\nSafety backup: {safety}\n\nRestart Training Studio before continuing normal work.",
            )
        run_background(
            "DbD data restore",
            lambda: migration_service().restore(
                chosen,
                project_root=selected_project_or_none(),
                allow_replace=replace,
                create_safety_backup=True,
            ),
            done,
        )

    migration_buttons = ttk.Frame(migration_tab)
    migration_buttons.grid(row=6, column=0, columnspan=3, sticky="w", pady=(12, 6))
    ttk.Button(migration_buttons, text="Create backup ZIP", command=create_migration_backup).pack(side="left", padx=(0, 6))
    ttk.Button(migration_buttons, text="Preview restore", command=preview_migration_restore).pack(side="left", padx=6)
    ttk.Button(migration_buttons, text="Restore", command=restore_migration_bundle).pack(side="left", padx=6)

    ttk.Label(
        migration_tab,
        text=f"Training data: {workspace.root}\nGlobal Trivia: {migration_service().trivia_database_path}\nRestore safety backups: {migration_service().safety_backup_root}",
        wraplength=900,
    ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))

    root.mainloop()
    return 0


def main() -> int:
    return launch_training_studio()


if __name__ == "__main__":
    raise SystemExit(main())
