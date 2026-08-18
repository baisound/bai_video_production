"""DbD Training Studio data contracts and import/build services.

This module keeps GUI concerns out of dataset persistence so the same contracts
can be exercised from tests, CLI tools, or a future richer desktop shell.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Iterable, Sequence

from .canonical_game_event import GameEventType
from .dbd_commentary_knowledge import DbDTriviaStore, TriviaCandidateMiner
from .dbd_hud_detectors import (
    NotificationVocabularyEntry,
    NotificationVocabularyIndex,
    TesseractCliOcrEngine,
    normalize_hud_text,
)
from .dbd_perk_knowledge import PerkEnvironment
from .dbd_vision_slices import DBDHudRoiProfile, FFmpegSliceExtractor, NormalizedROI, ReferenceSliceIndex
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider, LocalTranscriptionService
from .cut_candidates import load_transcript_manifest


class VisualTrainingDomain(str, Enum):
    SURVIVOR_HUD = "SURVIVOR_HUD"
    PERK_ICON = "PERK_ICON"
    ITEM_ICON = "ITEM_ICON"
    ADDON_ICON = "ADDON_ICON"
    KILLER_POWER = "KILLER_POWER"


_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_component(value: str, *, fallback: str) -> str:
    normalized = _SAFE_COMPONENT.sub("-", value.strip()).strip("-._")
    return (normalized or fallback)[:96]


def load_roi_profile(path: str | Path | None) -> DBDHudRoiProfile:
    if path is None or not str(path).strip():
        return DBDHudRoiProfile()
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"ROI profile does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("ROI profile must be valid UTF-8 JSON") from exc
    return DBDHudRoiProfile.from_dict(payload)


@dataclass(frozen=True, slots=True)
class ImportReport:
    accepted: int
    rejected: int
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.rejected == 0


@dataclass(frozen=True, slots=True)
class VisualVideoTrainingRequest:
    domain: VisualTrainingDomain
    label: str
    video_path: str
    start_frame: int
    end_frame_exclusive: int
    frame_step: int = 30
    slot: int | None = None
    group: str = "normal"
    source_ref: str = ""
    notes: str = ""
    roi_profile_path: str | None = None
    max_samples: int = 500

    def __post_init__(self) -> None:
        if not self.label.strip() or len(self.label) > 256:
            raise ValueError("video training label must be bounded non-empty text")
        if not self.video_path.strip() or len(self.video_path) > 2048:
            raise ValueError("video_path must be bounded non-empty text")
        if self.start_frame < 0 or self.end_frame_exclusive <= self.start_frame:
            raise ValueError("video training frame range is invalid")
        if self.frame_step < 1 or self.frame_step > 1_000_000:
            raise ValueError("frame_step must be 1..1000000")
        if self.slot is not None and not 0 <= self.slot <= 3:
            raise ValueError("slot must be 0..3 when specified")
        if not 1 <= self.max_samples <= 10_000:
            raise ValueError("max_samples must be 1..10000")
        sample_count = ((self.end_frame_exclusive - self.start_frame - 1) // self.frame_step) + 1
        if sample_count > self.max_samples:
            raise ValueError(
                f"requested video slice count {sample_count} exceeds max_samples={self.max_samples}; "
                "increase frame_step or split the range"
            )


@dataclass(frozen=True, slots=True)
class VideoLearningReport:
    domain: VisualTrainingDomain
    label: str
    roi_id: str
    requested_frames: int
    extracted: int
    registered: int
    duplicates: int
    rejected: int
    output_directory: str
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.rejected == 0


@dataclass(frozen=True, slots=True)
class OcrVideoCandidate:
    frame_index: int
    image_path: str
    text: str
    normalized_text: str


@dataclass(frozen=True, slots=True)
class OcrVideoScanReport:
    requested_frames: int
    scanned: int
    candidates: tuple[OcrVideoCandidate, ...]
    rejected: int
    output_directory: str
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.rejected == 0


@dataclass(frozen=True, slots=True)
class TriviaVideoLearningReport:
    transcript_path: str
    subtitle_path: str
    mined_candidates: int
    source_asset_id: str


@dataclass(frozen=True, slots=True)
class VisualTrainingSample:
    domain: VisualTrainingDomain
    label: str
    image_path: str
    group: str = "default"
    source_ref: str = "manual://owner"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip() or len(self.label) > 256:
            raise ValueError("visual training label must be bounded non-empty text")
        if not self.image_path.strip() or len(self.image_path) > 2048:
            raise ValueError("visual training image_path must be bounded non-empty text")
        if not self.group.strip() or len(self.group) > 128:
            raise ValueError("visual training group must be bounded non-empty text")
        if not self.source_ref.strip() or len(self.source_ref) > 2048:
            raise ValueError("visual training source_ref must be bounded non-empty text")
        if len(self.notes) > 4000:
            raise ValueError("visual training notes are too long")

    def to_row(self) -> dict[str, str]:
        return {
            "domain": self.domain.value,
            "label": self.label.strip(),
            "image_path": self.image_path.strip(),
            "group": self.group.strip(),
            "source_ref": self.source_ref.strip(),
            "notes": self.notes.strip(),
        }


class VisualTrainingManifest:
    fieldnames = ("domain", "label", "image_path", "group", "source_ref", "notes")

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(())

    def _write(self, values: Sequence[VisualTrainingSample]) -> None:
        with self._lock:
            fd, raw_temp = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
            os.close(fd)
            temp = Path(raw_temp)
            try:
                with temp.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                    writer.writeheader()
                    for item in values:
                        writer.writerow(item.to_row())
                os.replace(temp, self.path)
            finally:
                if temp.exists():
                    temp.unlink()

    def list(self, *, domain: VisualTrainingDomain | None = None) -> tuple[VisualTrainingSample, ...]:
        with self._lock:
            rows: list[VisualTrainingSample] = []
            with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
                for number, row in enumerate(csv.DictReader(handle), start=2):
                    if not row:
                        continue
                    try:
                        item = VisualTrainingSample(
                            domain=VisualTrainingDomain((row.get("domain") or "").strip().upper()),
                            label=(row.get("label") or "").strip(),
                            image_path=(row.get("image_path") or "").strip(),
                            group=(row.get("group") or "default").strip() or "default",
                            source_ref=(row.get("source_ref") or "manual://owner").strip() or "manual://owner",
                            notes=(row.get("notes") or "").strip(),
                        )
                    except Exception as exc:
                        raise ValueError(f"invalid visual manifest row {number}: {exc}") from exc
                    if domain is None or item.domain is domain:
                        rows.append(item)
            return tuple(rows)

    @staticmethod
    def _identity(item: VisualTrainingSample) -> tuple[str, ...]:
        return (item.domain.value, item.label.casefold(), str(Path(item.image_path)).casefold(), item.group.casefold(), item.source_ref.casefold())

    def append(self, item: VisualTrainingSample) -> bool:
        with self._lock:
            values = list(self.list())
            identities = {self._identity(existing) for existing in values}
            if self._identity(item) in identities:
                return False
            values.append(item)
            self._write(values)
            return True

    def import_csv(self, path: str | Path, *, default_domain: VisualTrainingDomain | None = None) -> ImportReport:
        accepted, rejected = 0, 0
        errors: list[str] = []
        source = Path(path)
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "label" not in reader.fieldnames or "image_path" not in reader.fieldnames:
                return ImportReport(0, 1, ("CSV requires label and image_path columns",))
            for number, row in enumerate(reader, start=2):
                try:
                    raw_domain = (row.get("domain") or "").strip().upper()
                    domain = VisualTrainingDomain(raw_domain) if raw_domain else default_domain
                    if domain is None:
                        raise ValueError("domain is required when no default domain is selected")
                    item = VisualTrainingSample(
                        domain=domain,
                        label=(row.get("label") or "").strip(),
                        image_path=(row.get("image_path") or "").strip(),
                        group=(row.get("group") or "default").strip() or "default",
                        source_ref=(row.get("source_ref") or source.resolve().as_uri()).strip(),
                        notes=(row.get("notes") or "").strip(),
                    )
                    if not Path(item.image_path).is_file():
                        raise ValueError(f"image does not exist: {item.image_path}")
                    if self.append(item):
                        accepted += 1
                except Exception as exc:
                    rejected += 1
                    errors.append(f"row {number}: {exc}")
        return ImportReport(accepted, rejected, tuple(errors))

    def build_reference_index(
        self,
        *,
        domain: VisualTrainingDomain,
        output_path: str | Path,
        index_id: str,
        ffmpeg_executable: str = "ffmpeg",
    ) -> Path:
        samples = self.list(domain=domain)
        if not samples:
            raise ValueError(f"no visual samples registered for {domain.value}")
        extractor = FFmpegSliceExtractor(ffmpeg_executable)
        with tempfile.TemporaryDirectory(prefix="bvp-dbd-training-") as td:
            normalized: list[tuple[str, Path, str]] = []
            for index, sample in enumerate(samples):
                source = Path(sample.image_path)
                if not source.is_file():
                    raise ValueError(f"registered training image is missing: {source}")
                if source.suffix.casefold() == ".pgm":
                    pgm = source
                else:
                    pgm = Path(td) / f"{index:06d}.pgm"
                    extractor.normalize_still_to_pgm(image_path=source, output_path=pgm)
                normalized.append((sample.label, pgm, sample.group))
            reference = ReferenceSliceIndex.train_from_pgm(index_id=index_id, samples=normalized)
            return reference.save(output_path)


def _visual_training_roi(request: VisualVideoTrainingRequest, profile: DBDHudRoiProfile) -> NormalizedROI:
    if request.domain is VisualTrainingDomain.SURVIVOR_HUD:
        if request.slot is None:
            raise ValueError("SURVIVOR_HUD video learning requires slot 0..3")
        return profile.survivor_slot_roi(request.slot)
    if request.domain is VisualTrainingDomain.PERK_ICON:
        if request.slot is None:
            raise ValueError("PERK_ICON video learning requires slot 0..3")
        return profile.perk_slot_roi(request.slot)
    if request.domain is VisualTrainingDomain.ITEM_ICON:
        return profile.item_slot_roi()
    if request.domain is VisualTrainingDomain.ADDON_ICON:
        if request.slot is None or not 0 <= request.slot < 2:
            raise ValueError("ADDON_ICON video learning requires slot 0..1")
        return profile.addon_slot_roi(request.slot)
    if request.domain is VisualTrainingDomain.KILLER_POWER:
        if profile.killer_power_hud is None:
            raise ValueError(
                "KILLER_POWER video learning requires an ROI profile with killer_power_hud configured"
            )
        return profile.killer_power_hud
    raise ValueError(f"unsupported visual training domain: {request.domain.value}")


@dataclass(frozen=True, slots=True)
class OcrVocabularySample:
    signal_id: str
    phrase: str
    locale: str = "ja-JP"
    source_ref: str = "manual://owner"

    def __post_init__(self) -> None:
        if not self.signal_id.strip() or len(self.signal_id) > 128:
            raise ValueError("signal_id must be bounded non-empty text")
        if not self.phrase.strip() or len(self.phrase) > 512:
            raise ValueError("phrase must be bounded non-empty text")
        if not self.locale.strip() or len(self.locale) > 32:
            raise ValueError("locale must be bounded non-empty text")
        if not self.source_ref.strip() or len(self.source_ref) > 2048:
            raise ValueError("source_ref must be bounded non-empty text")


class OcrVocabularyManifest:
    fieldnames = ("signal_id", "phrase", "locale", "source_ref")

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(())

    def _write(self, values: Sequence[OcrVocabularySample]) -> None:
        with self._lock:
            fd, raw_temp = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
            os.close(fd)
            temp = Path(raw_temp)
            try:
                with temp.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                    writer.writeheader()
                    for item in values:
                        writer.writerow({"signal_id": item.signal_id, "phrase": item.phrase, "locale": item.locale, "source_ref": item.source_ref})
                os.replace(temp, self.path)
            finally:
                if temp.exists():
                    temp.unlink()

    def list(self) -> tuple[OcrVocabularySample, ...]:
        with self._lock:
            values: list[OcrVocabularySample] = []
            with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
                for number, row in enumerate(csv.DictReader(handle), start=2):
                    try:
                        values.append(OcrVocabularySample(
                            signal_id=(row.get("signal_id") or "").strip().upper(),
                            phrase=(row.get("phrase") or "").strip(),
                            locale=(row.get("locale") or "ja-JP").strip() or "ja-JP",
                            source_ref=(row.get("source_ref") or "manual://owner").strip() or "manual://owner",
                        ))
                    except Exception as exc:
                        raise ValueError(f"invalid OCR vocabulary row {number}: {exc}") from exc
            return tuple(values)

    @staticmethod
    def _identity(item: OcrVocabularySample) -> tuple[str, str, str]:
        return (item.signal_id.casefold(), item.phrase.casefold(), item.locale.casefold())

    def append(self, item: OcrVocabularySample) -> bool:
        with self._lock:
            values = list(self.list())
            if self._identity(item) in {self._identity(existing) for existing in values}:
                return False
            values.append(item)
            self._write(values)
            return True

    def import_csv(self, path: str | Path) -> ImportReport:
        accepted, rejected = 0, 0
        errors: list[str] = []
        source = Path(path)
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "signal_id" not in reader.fieldnames or "phrase" not in reader.fieldnames:
                return ImportReport(0, 1, ("CSV requires signal_id and phrase columns",))
            for number, row in enumerate(reader, start=2):
                try:
                    item = OcrVocabularySample(
                        signal_id=(row.get("signal_id") or "").strip().upper(),
                        phrase=(row.get("phrase") or "").strip(),
                        locale=(row.get("locale") or "ja-JP").strip() or "ja-JP",
                        source_ref=(row.get("source_ref") or source.resolve().as_uri()).strip(),
                    )
                    if self.append(item):
                        accepted += 1
                except Exception as exc:
                    rejected += 1
                    errors.append(f"row {number}: {exc}")
        return ImportReport(accepted, rejected, tuple(errors))

    def build_vocabulary(self, *, output_path: str | Path, vocabulary_id: str) -> Path:
        grouped: dict[str, set[str]] = {}
        for item in self.list():
            grouped.setdefault(item.signal_id, set()).add(item.phrase)
        if not grouped:
            raise ValueError("OCR vocabulary has no registered phrases")
        entries = tuple(NotificationVocabularyEntry(signal_id, tuple(sorted(phrases))) for signal_id, phrases in sorted(grouped.items()))
        return NotificationVocabularyIndex(vocabulary_id=vocabulary_id, entries=entries).save(output_path)


def default_training_workspace_root() -> Path:
    override = os.environ.get("BVP_DBD_TRAINING_ROOT")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) if local else Path.home() / ".local" / "share"
    return root / "BAI Video Production" / "training" / "dbd"


class DbDTrainingWorkspace:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_training_workspace_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.visual = VisualTrainingManifest(self.root / "visual-training.csv")
        self.ocr = OcrVocabularyManifest(self.root / "upper-right-ocr-vocabulary.csv")
        self.trivia = DbDTriviaStore(self.root / "dbd-commentary-knowledge.sqlite3")
        (self.root / "indexes").mkdir(parents=True, exist_ok=True)
        (self.root / "video-slices").mkdir(parents=True, exist_ok=True)
        (self.root / "video-ocr").mkdir(parents=True, exist_ok=True)
        (self.root / "video-transcripts").mkdir(parents=True, exist_ok=True)

    def extract_visual_from_video(
        self,
        request: VisualVideoTrainingRequest,
        *,
        ffmpeg_executable: str = "ffmpeg",
    ) -> VideoLearningReport:
        video = Path(request.video_path).expanduser().resolve()
        if not video.is_file():
            raise ValueError(f"training video does not exist: {video}")
        profile = load_roi_profile(request.roi_profile_path)
        roi = _visual_training_roi(request, profile)
        frames = tuple(range(request.start_frame, request.end_frame_exclusive, request.frame_step))
        token = hashlib.sha256(
            (
                f"{video}|{request.domain.value}|{request.label}|{request.start_frame}|"
                f"{request.end_frame_exclusive}|{request.frame_step}|{roi.roi_id}|{profile.profile_id}"
            ).encode("utf-8")
        ).hexdigest()[:12]
        output = (
            self.root
            / "video-slices"
            / request.domain.value.lower()
            / _safe_component(request.label, fallback="label")
            / f"{_safe_component(video.stem, fallback='video')}-{token}"
        )
        output.mkdir(parents=True, exist_ok=True)
        extractor = FFmpegSliceExtractor(ffmpeg_executable)
        registered = duplicates = rejected = extracted = 0
        errors: list[str] = []
        base_ref = request.source_ref.strip() or video.as_uri()
        for frame_index in frames:
            try:
                target = output / f"frame-{frame_index:09d}-{roi.roi_id}.pgm"
                extractor.extract_frame_roi(
                    video_path=video,
                    frame_index=frame_index,
                    roi=roi,
                    output_path=target,
                    width=96,
                    height=96,
                )
                extracted += 1
                item = VisualTrainingSample(
                    domain=request.domain,
                    label=request.label,
                    image_path=str(target),
                    group=request.group,
                    source_ref=f"{base_ref}#frame={frame_index}&roi={roi.roi_id}",
                    notes=(request.notes.strip() + f" | video_profile={profile.profile_id}").strip(" |"),
                )
                if self.visual.append(item):
                    registered += 1
                else:
                    duplicates += 1
            except Exception as exc:
                rejected += 1
                errors.append(f"frame {frame_index}: {exc}")
        report = VideoLearningReport(
            domain=request.domain,
            label=request.label,
            roi_id=roi.roi_id,
            requested_frames=len(frames),
            extracted=extracted,
            registered=registered,
            duplicates=duplicates,
            rejected=rejected,
            output_directory=str(output),
            errors=tuple(errors),
        )
        receipt = {
            "schema_version": "1.0.0",
            "domain": report.domain.value,
            "label": report.label,
            "video_path": str(video),
            "roi_profile_id": profile.profile_id,
            "roi_id": report.roi_id,
            "range": {
                "start_frame": request.start_frame,
                "end_frame_exclusive": request.end_frame_exclusive,
                "frame_step": request.frame_step,
            },
            "requested_frames": report.requested_frames,
            "extracted": report.extracted,
            "registered": report.registered,
            "duplicates": report.duplicates,
            "rejected": report.rejected,
            "errors": list(report.errors),
        }
        (output / "video-learning-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return report

    def import_video_training_csv(
        self,
        path: str | Path,
        *,
        default_domain: VisualTrainingDomain | None = None,
        ffmpeg_executable: str = "ffmpeg",
    ) -> ImportReport:
        accepted = rejected = 0
        errors: list[str] = []
        source = Path(path).expanduser().resolve()
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"label", "video_path", "start_frame", "end_frame_exclusive"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                return ImportReport(0, 1, (f"CSV requires columns: {', '.join(sorted(required))}",))
            for number, row in enumerate(reader, start=2):
                try:
                    raw_domain = (row.get("domain") or "").strip().upper()
                    domain = VisualTrainingDomain(raw_domain) if raw_domain else default_domain
                    if domain is None:
                        raise ValueError("domain is required when no default domain is selected")
                    raw_slot = (row.get("slot") or "").strip()
                    request = VisualVideoTrainingRequest(
                        domain=domain,
                        label=(row.get("label") or "").strip(),
                        video_path=(row.get("video_path") or "").strip(),
                        start_frame=int((row.get("start_frame") or "0").strip()),
                        end_frame_exclusive=int((row.get("end_frame_exclusive") or "0").strip()),
                        frame_step=int((row.get("frame_step") or "30").strip()),
                        slot=None if not raw_slot else int(raw_slot),
                        group=(row.get("group") or "normal").strip() or "normal",
                        source_ref=(row.get("source_ref") or source.as_uri()).strip(),
                        notes=(row.get("notes") or "").strip(),
                        roi_profile_path=(row.get("roi_profile_path") or "").strip() or None,
                        max_samples=int((row.get("max_samples") or "500").strip()),
                    )
                    report = self.extract_visual_from_video(request, ffmpeg_executable=ffmpeg_executable)
                    accepted += report.registered
                    rejected += report.rejected
                    errors.extend(f"row {number}: {message}" for message in report.errors)
                except Exception as exc:
                    rejected += 1
                    errors.append(f"row {number}: {exc}")
        return ImportReport(accepted, rejected, tuple(errors))

    def scan_upper_right_ocr_from_video(
        self,
        *,
        video_path: str | Path,
        start_frame: int,
        end_frame_exclusive: int,
        frame_step: int = 30,
        roi_profile_path: str | Path | None = None,
        ffmpeg_executable: str = "ffmpeg",
        tesseract_executable: str = "tesseract",
        language: str = "jpn+eng",
        max_samples: int = 300,
    ) -> OcrVideoScanReport:
        video = Path(video_path).expanduser().resolve()
        if not video.is_file():
            raise ValueError(f"OCR source video does not exist: {video}")
        if start_frame < 0 or end_frame_exclusive <= start_frame or frame_step < 1:
            raise ValueError("OCR video frame range is invalid")
        frames = tuple(range(start_frame, end_frame_exclusive, frame_step))
        if len(frames) > max_samples:
            raise ValueError(
                f"requested OCR frame count {len(frames)} exceeds max_samples={max_samples}; increase frame_step"
            )
        profile = load_roi_profile(roi_profile_path)
        roi = profile.upper_right_notifications
        token = hashlib.sha256(
            f"{video}|{start_frame}|{end_frame_exclusive}|{frame_step}|{profile.profile_id}".encode("utf-8")
        ).hexdigest()[:12]
        output = self.root / "video-ocr" / f"{_safe_component(video.stem, fallback='video')}-{token}"
        output.mkdir(parents=True, exist_ok=True)
        extractor = FFmpegSliceExtractor(ffmpeg_executable)
        engine = TesseractCliOcrEngine(tesseract_executable)
        candidates: list[OcrVideoCandidate] = []
        errors: list[str] = []
        scanned = rejected = 0
        seen: set[str] = set()
        for frame_index in frames:
            try:
                target = output / f"frame-{frame_index:09d}-upper-right.pgm"
                extractor.extract_frame_roi(
                    video_path=video,
                    frame_index=frame_index,
                    roi=roi,
                    output_path=target,
                    width=512,
                    height=256,
                )
                scanned += 1
                text = engine.read(target, language=language).strip()
                normalized = normalize_hud_text(text)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    candidates.append(OcrVideoCandidate(frame_index, str(target), text, normalized))
            except Exception as exc:
                rejected += 1
                errors.append(f"frame {frame_index}: {exc}")
        return OcrVideoScanReport(
            requested_frames=len(frames),
            scanned=scanned,
            candidates=tuple(candidates),
            rejected=rejected,
            output_directory=str(output),
            errors=tuple(errors),
        )

    def mine_trivia_from_video(
        self,
        *,
        video_path: str | Path,
        model: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
        language: str | None = "ja",
        allow_model_download: bool = False,
    ) -> TriviaVideoLearningReport:
        video = Path(video_path).expanduser().resolve()
        if not video.is_file():
            raise ValueError(f"trivia source video does not exist: {video}")
        token = hashlib.sha256(str(video).encode("utf-8")).hexdigest()[:12]
        output = self.root / "video-transcripts" / f"{_safe_component(video.stem, fallback='video')}-{token}"
        provider = FasterWhisperProvider(
            FasterWhisperConfig(
                model=model,
                device=device,
                compute_type=compute_type,
                allow_model_download=allow_model_download,
            )
        )
        publication = LocalTranscriptionService.run(
            video,
            output,
            provider=provider,
            language=language or None,
        )
        mined = TriviaCandidateMiner().capture_transcript_manifest(self.trivia, publication.transcript)
        return TriviaVideoLearningReport(
            transcript_path=str(publication.transcript_path),
            subtitle_path=str(publication.subtitle_path),
            mined_candidates=len(mined),
            source_asset_id=publication.transcript.source_asset_id,
        )

    def mine_trivia_from_transcript(self, path: str | Path) -> int:
        manifest = load_transcript_manifest(path)
        return len(TriviaCandidateMiner().capture_transcript_manifest(self.trivia, manifest))

    def import_trivia_csv(self, path: str | Path) -> ImportReport:
        accepted, rejected = 0, 0
        errors: list[str] = []
        source = Path(path)
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "title" not in reader.fieldnames or "text" not in reader.fieldnames:
                return ImportReport(0, 1, ("CSV requires title and text columns",))
            for number, row in enumerate(reader, start=2):
                try:
                    tags = tuple(x.strip() for x in (row.get("tags") or "").split(",") if x.strip())
                    events = tuple(GameEventType(x.strip().upper()) for x in (row.get("event_types") or "").split(",") if x.strip())
                    entities = tuple(x.strip() for x in (row.get("entity_refs") or "").split(",") if x.strip())
                    verify = (row.get("verify") or "").strip().casefold() in {"1", "true", "yes", "y"}
                    self.trivia.create_manual(
                        title=(row.get("title") or "").strip(),
                        text=(row.get("text") or "").strip(),
                        source_ref=(row.get("source_ref") or source.resolve().as_uri()).strip(),
                        category=(row.get("category") or "GENERAL").strip() or "GENERAL",
                        tags=tags,
                        event_types=events,
                        entity_refs=entities,
                        environment=PerkEnvironment((row.get("environment") or "LIVE").strip().upper()),
                        game_version_from=(row.get("game_version_from") or "").strip() or None,
                        game_version_to=(row.get("game_version_to") or "").strip() or None,
                        verify=verify,
                    )
                    accepted += 1
                except Exception as exc:
                    rejected += 1
                    errors.append(f"row {number}: {exc}")
        return ImportReport(accepted, rejected, tuple(errors))


__all__ = [
    "DbDTrainingWorkspace", "ImportReport", "OcrVideoCandidate", "OcrVideoScanReport",
    "OcrVocabularyManifest", "OcrVocabularySample", "TriviaVideoLearningReport",
    "VideoLearningReport", "VisualTrainingDomain", "VisualTrainingManifest", "VisualTrainingSample",
    "VisualVideoTrainingRequest", "default_training_workspace_root", "load_roi_profile",
]
