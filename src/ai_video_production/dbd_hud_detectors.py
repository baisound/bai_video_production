"""TASK-049 R10B HUD recognition baselines for DbD recorded video.

These detectors are deterministic baselines built on labeled ROI slice
references and optional Tesseract OCR.  They deliberately return UNKNOWN when
confidence is insufficient.  They do not claim production accuracy before a
Human Gold benchmark is executed on real video.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from enum import Enum
from pathlib import Path
import re
import subprocess
import unicodedata
from typing import Iterable, Protocol, Sequence

from .dbd_hud_visibility import HudVisibility, visibility_training_label
from .dbd_vision_slices import GrayImage, ReferenceSliceIndex, SliceMatch, TemporalConsensus
from .errors import ProductError, ProductErrorCategory


class SurvivorHudState(str, Enum):
    HEALTHY = "HEALTHY"
    INJURED = "INJURED"
    DOWNED = "DOWNED"
    HOOKED = "HOOKED"
    DEAD = "DEAD"
    ESCAPED = "ESCAPED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RecognitionCandidate:
    label: str
    confidence_milli: int
    source_ref: str


@dataclass(frozen=True, slots=True)
class ClassifiedSlice:
    selected_label: str
    confidence_milli: int
    candidates: tuple[RecognitionCandidate, ...]
    unknown: bool


class ReferenceSliceClassifier:
    def __init__(self, index: ReferenceSliceIndex, *, acceptance_milli: int = 780, ambiguity_margin_milli: int = 60) -> None:
        if not 0 <= acceptance_milli <= 1000 or not 0 <= ambiguity_margin_milli <= 1000:
            raise ValueError("recognition thresholds must be 0..1000")
        self.index, self.acceptance_milli, self.ambiguity_margin_milli = index, acceptance_milli, ambiguity_margin_milli

    def classify(self, image: GrayImage, *, top_k: int = 3) -> ClassifiedSlice:
        # Compare *labels*, not merely reference images.  Multiple normal/active
        # references for one perk/state must not hide a close competing label.
        matches = self.index.match(image, top_k=max(top_k, len(self.index.references)))
        best_by_label: dict[str, SliceMatch] = {}
        for match in matches:
            current = best_by_label.get(match.label)
            if current is None or (match.confidence_milli, -match.distance_bits, match.source_ref) > (current.confidence_milli, -current.distance_bits, current.source_ref):
                best_by_label[match.label] = match
        unique = sorted(best_by_label.values(), key=lambda item: (-item.confidence_milli, item.distance_bits, item.label, item.source_ref))[:top_k]
        candidates = tuple(RecognitionCandidate(x.label, x.confidence_milli, x.source_ref) for x in unique)
        if not candidates:
            return ClassifiedSlice("UNKNOWN", 0, (), True)
        first = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        ambiguous = second is not None and first.confidence_milli - second.confidence_milli < self.ambiguity_margin_milli
        if first.confidence_milli < self.acceptance_milli or ambiguous:
            return ClassifiedSlice("UNKNOWN", first.confidence_milli, candidates, True)
        return ClassifiedSlice(first.label, first.confidence_milli, candidates, False)


@dataclass(frozen=True, slots=True)
class SurvivorSlotObservation:
    slot: int
    state: SurvivorHudState
    confidence_milli: int
    candidates: tuple[RecognitionCandidate, ...]


class SurvivorHudStateDetector:
    def __init__(self, index: ReferenceSliceIndex, *, acceptance_milli: int = 780) -> None:
        self.classifier = ReferenceSliceClassifier(index, acceptance_milli=acceptance_milli)

    def detect_slot(self, image: GrayImage, *, slot: int) -> SurvivorSlotObservation:
        if not 0 <= slot <= 3:
            raise ValueError("survivor HUD slot must be 0..3")
        result = self.classifier.classify(image)
        try:
            state = SurvivorHudState(result.selected_label)
        except ValueError:
            state = SurvivorHudState.UNKNOWN
        return SurvivorSlotObservation(slot, state, result.confidence_milli, result.candidates)

    @staticmethod
    def detect_transition(before: Sequence[SurvivorSlotObservation], after: Sequence[SurvivorSlotObservation]) -> tuple[tuple[int, SurvivorHudState, SurvivorHudState, int], ...]:
        left = {item.slot: item for item in before}
        right = {item.slot: item for item in after}
        rows = []
        for slot in sorted(set(left) & set(right)):
            old, new = left[slot], right[slot]
            if old.state is SurvivorHudState.UNKNOWN or new.state is SurvivorHudState.UNKNOWN or old.state is new.state:
                continue
            rows.append((slot, old.state, new.state, min(old.confidence_milli, new.confidence_milli)))
        return tuple(rows)


@dataclass(frozen=True, slots=True)
class PerkSlotObservation:
    slot: int
    perk_id: str | None
    confidence_milli: int
    candidates: tuple[RecognitionCandidate, ...]
    visibility: HudVisibility = HudVisibility.UNKNOWN


class PerkIconDetector:
    """Recognize one of four bottom-right perk slots from trained icon slices."""

    def __init__(self, index: ReferenceSliceIndex, *, acceptance_milli: int = 800, temporal_minimum_frames: int = 2) -> None:
        self.classifier = ReferenceSliceClassifier(index, acceptance_milli=acceptance_milli, ambiguity_margin_milli=75)
        self.temporal_minimum_frames = temporal_minimum_frames

    def detect_slot(self, image: GrayImage, *, slot: int) -> PerkSlotObservation:
        if not 0 <= slot <= 3:
            raise ValueError("perk slot must be 0..3")
        result = self.classifier.classify(image, top_k=3)
        visibility = visibility_training_label("PERK", result.selected_label)
        if visibility is not None and not result.unknown:
            return PerkSlotObservation(slot, None, result.confidence_milli, result.candidates, visibility)

        perk_id = None if result.unknown or not result.selected_label.startswith("perk_") else result.selected_label
        visibility = HudVisibility.VISIBLE if perk_id is not None else HudVisibility.UNKNOWN
        return PerkSlotObservation(slot, perk_id, result.confidence_milli, result.candidates, visibility)

    def temporal_vote(self, observations: Sequence[PerkSlotObservation]) -> PerkSlotObservation:
        if not observations:
            raise ValueError("observations must not be empty")
        slots = {item.slot for item in observations}
        if len(slots) != 1:
            raise ValueError("temporal observations must belong to one perk slot")
        slot = next(iter(slots))
        visibility_vote = TemporalConsensus.vote(
            [(item.visibility.value, item.confidence_milli) for item in observations],
            minimum_frames=self.temporal_minimum_frames,
            minimum_confidence_milli=650,
        )
        if visibility_vote is not None:
            visibility = HudVisibility(visibility_vote[0])
            if visibility in {
                HudVisibility.HIDDEN,
                HudVisibility.PARTIALLY_OCCLUDED,
                HudVisibility.UNREADABLE,
            }:
                return PerkSlotObservation(slot, None, visibility_vote[1], (), visibility)

        vote = TemporalConsensus.vote([(item.perk_id or "UNKNOWN", item.confidence_milli) for item in observations], minimum_frames=self.temporal_minimum_frames, minimum_confidence_milli=650)
        if vote is None or vote[0] == "UNKNOWN":
            confidence = max((item.confidence_milli for item in observations), default=0)
            visible_seen = any(item.visibility is HudVisibility.VISIBLE for item in observations)
            visibility = HudVisibility.VISIBLE if visible_seen else HudVisibility.UNKNOWN
            return PerkSlotObservation(slot, None, confidence, (), visibility)
        return PerkSlotObservation(slot, vote[0], vote[1], (), HudVisibility.VISIBLE)


class OcrEngine(Protocol):
    def read(self, image_path: str | Path, *, language: str = "jpn+eng") -> str: ...


class TesseractCliOcrEngine:
    """Optional OCR adapter with short-HUD multi-pass recognition.

    Upper-right DbD text is often a single sparse line over a noisy game frame.
    A single ``--psm 6`` pass is brittle, so the adapter evaluates several page
    segmentation modes and returns unique alternatives in deterministic order.
    """

    def __init__(self, executable: str = "tesseract") -> None:
        self.executable = executable

    def _read_psm(self, source: Path, *, language: str, psm: int) -> str:
        cmd = [
            self.executable, str(source), "stdout", "-l", language,
            "--psm", str(psm), "-c", "preserve_interword_spaces=1",
        ]
        try:
            completed = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductError(
                "ERR_DBD_OCR_RUNTIME_UNAVAILABLE", "Tesseract OCR is unavailable",
                ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True,
            ) from exc
        if completed.returncode != 0:
            raise ProductError(
                "ERR_DBD_OCR_FAILED", "Tesseract OCR failed",
                ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True,
                details={"returncode": completed.returncode, "psm": psm},
            )
        return completed.stdout.decode("utf-8", errors="replace").strip()

    def read_candidates(
        self, image_path: str | Path, *, language: str = "jpn+eng",
    ) -> tuple[str, ...]:
        source = Path(image_path)
        if not source.is_file():
            raise ValueError("OCR image does not exist")
        rows: list[str] = []
        seen: set[str] = set()
        # PSM 7 is strongest for one-line HUD labels, PSM 6 for compact blocks,
        # and PSM 11 for sparse text.  Showing unique alternatives lets the
        # human reviewer select/correct the strongest candidate without hiding
        # uncertainty.
        for psm in (7, 6, 11):
            text = self._read_psm(source, language=language, psm=psm)
            normalized = normalize_hud_text(text)
            if normalized and normalized not in seen:
                seen.add(normalized)
                rows.append(text)
        return tuple(rows)

    def read(self, image_path: str | Path, *, language: str = "jpn+eng") -> str:
        candidates = self.read_candidates(image_path, language=language)
        return candidates[0] if candidates else ""


def normalize_hud_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠ー ]+", " ", normalized)
    return " ".join(normalized.split())


@dataclass(frozen=True, slots=True)
class NotificationVocabularyEntry:
    signal_id: str
    phrases: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.signal_id or not self.phrases:
            raise ValueError("notification vocabulary entry requires signal_id and phrases")

    def to_dict(self) -> dict[str, object]:
        return {"signal_id": self.signal_id, "phrases": list(self.phrases)}


@dataclass(frozen=True, slots=True)
class NotificationVocabularyIndex:
    vocabulary_id: str
    entries: tuple[NotificationVocabularyEntry, ...]
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.vocabulary_id.strip() or len(self.vocabulary_id) > 128:
            raise ValueError("vocabulary_id must be bounded non-empty text")
        if not self.entries:
            raise ValueError("notification vocabulary requires at least one entry")
        signal_ids = [entry.signal_id for entry in self.entries]
        if len(set(signal_ids)) != len(signal_ids):
            raise ValueError("notification vocabulary signal_id values must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "vocabulary_id": self.vocabulary_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "NotificationVocabularyIndex":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if document.get("schema_version") != "1.0.0":
            raise ValueError("unsupported notification vocabulary schema")
        entries = tuple(
            NotificationVocabularyEntry(str(item["signal_id"]), tuple(str(x) for x in item["phrases"]))
            for item in document.get("entries", [])
        )
        return cls(vocabulary_id=str(document["vocabulary_id"]), entries=entries)


@dataclass(frozen=True, slots=True)
class NotificationTextObservation:
    text: str
    normalized_text: str
    signal_id: str | None
    confidence_milli: int


class DBDNotificationTextDetector:
    """Resolve OCR output from the upper-right notification area to bounded signals."""

    DEFAULT_VOCABULARY = (
        NotificationVocabularyEntry("CHASE", ("chase", "追跡", "チェイス")),
        NotificationVocabularyEntry("WINDOW_VAULT", ("vault", "乗り越え", "窓越え", "窓枠")),
        NotificationVocabularyEntry("PALLET", ("pallet", "パレット", "板")),
        NotificationVocabularyEntry("GENERATOR", ("generator", "発電機")),
        NotificationVocabularyEntry("HEAL", ("heal", "治療")),
        NotificationVocabularyEntry("HOOK", ("hook", "フック")),
        NotificationVocabularyEntry("UNHOOK", ("rescue", "救助", "フック救助")),
    )

    def __init__(self, engine: OcrEngine, vocabulary: Iterable[NotificationVocabularyEntry] | None = None) -> None:
        self.engine = engine
        self.vocabulary = tuple(vocabulary or self.DEFAULT_VOCABULARY)

    @classmethod
    def from_vocabulary_file(cls, engine: OcrEngine, path: str | Path) -> "DBDNotificationTextDetector":
        return cls(engine, NotificationVocabularyIndex.load(path).entries)

    def detect(self, image_path: str | Path, *, language: str = "jpn+eng") -> NotificationTextObservation:
        text = self.engine.read(image_path, language=language)
        normalized = normalize_hud_text(text)
        hits: list[tuple[int, str]] = []
        for entry in self.vocabulary:
            for phrase in entry.phrases:
                token = normalize_hud_text(phrase)
                if token and token in normalized:
                    hits.append((len(token), entry.signal_id))
        if not hits:
            return NotificationTextObservation(text, normalized, None, 0)
        hits.sort(reverse=True)
        best_length, best = hits[0]
        same = {signal for length, signal in hits if length == best_length}
        if len(same) > 1:
            return NotificationTextObservation(text, normalized, None, 400)
        confidence = min(950, 650 + best_length * 20)
        return NotificationTextObservation(text, normalized, best, confidence)


def to_resolver_health_state(state: SurvivorHudState):
    from .dbd_event_resolver import DBDHealthState
    mapping = {
        SurvivorHudState.HEALTHY: DBDHealthState.HEALTHY,
        SurvivorHudState.INJURED: DBDHealthState.INJURED,
        SurvivorHudState.DOWNED: DBDHealthState.DOWNED,
        SurvivorHudState.HOOKED: DBDHealthState.HOOKED,
        SurvivorHudState.DEAD: DBDHealthState.DEAD,
        SurvivorHudState.ESCAPED: DBDHealthState.ESCAPED,
    }
    return mapping.get(state)


__all__ = [
    "ClassifiedSlice", "DBDNotificationTextDetector", "NotificationTextObservation",
    "NotificationVocabularyEntry", "NotificationVocabularyIndex", "OcrEngine", "PerkIconDetector", "PerkSlotObservation",
    "HudVisibility",
    "RecognitionCandidate", "ReferenceSliceClassifier", "SurvivorHudState",
    "SurvivorHudStateDetector", "SurvivorSlotObservation", "TesseractCliOcrEngine",
    "normalize_hud_text", "to_resolver_health_state",
]
