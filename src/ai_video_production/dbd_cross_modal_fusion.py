"""TASK-049 cross-modal evidence fusion for bounded DbD event signals."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .canonical_game_event import GameEventType
from .game_event_evidence import SourceFrameRange


class FusionModality(str, Enum):
    VISION = "VISION"
    HUD = "HUD"
    OCR = "OCR"
    ASR = "ASR"
    AUDIO = "AUDIO"
    KNOWLEDGE = "KNOWLEDGE"
    STATE = "STATE"


@dataclass(frozen=True, slots=True)
class FusionObservation:
    event_type: GameEventType
    modality: FusionModality
    confidence_milli: int
    source_range: SourceFrameRange
    evidence_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, GameEventType) or not isinstance(self.modality, FusionModality):
            raise ValueError("invalid fusion observation enum")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if not self.evidence_ref:
            raise ValueError("evidence_ref is required")


@dataclass(frozen=True, slots=True)
class FusionDecision:
    event_type: GameEventType | None
    confidence_milli: int
    evidence_refs: tuple[str, ...]
    modalities: tuple[FusionModality, ...]
    source_range: SourceFrameRange | None
    reason_codes: tuple[str, ...]


class DBDCrossModalFusion:
    DEFAULT_WEIGHTS = {
        FusionModality.VISION: 1000,
        FusionModality.HUD: 1000,
        FusionModality.OCR: 800,
        FusionModality.ASR: 550,
        FusionModality.AUDIO: 600,
        FusionModality.KNOWLEDGE: 450,
        FusionModality.STATE: 900,
    }

    def __init__(self, *, minimum_confidence_milli: int = 650, auto_confirm_milli: int = 900, weights: dict[FusionModality, int] | None = None) -> None:
        if not 0 <= minimum_confidence_milli < auto_confirm_milli <= 1000:
            raise ValueError("invalid fusion thresholds")
        self.minimum_confidence_milli = minimum_confidence_milli
        self.auto_confirm_milli = auto_confirm_milli
        self.weights = dict(weights or self.DEFAULT_WEIGHTS)

    @staticmethod
    def _overlap(a: SourceFrameRange, b: SourceFrameRange) -> bool:
        return a.start_frame < b.end_frame_exclusive and b.start_frame < a.end_frame_exclusive

    def fuse(self, observations: Iterable[FusionObservation]) -> FusionDecision:
        rows = tuple(observations)
        if not rows:
            return FusionDecision(None, 0, (), (), None, ("NO_EVIDENCE",))
        groups: dict[GameEventType, list[FusionObservation]] = {}
        for row in rows:
            groups.setdefault(row.event_type, []).append(row)
        scored: list[tuple[int, GameEventType, list[FusionObservation]]] = []
        for event_type, items in groups.items():
            admitted: list[FusionObservation] = []
            for item in sorted(items, key=lambda x: (-x.confidence_milli, x.modality.value, x.evidence_ref)):
                if not admitted or any(self._overlap(item.source_range, other.source_range) for other in admitted):
                    admitted.append(item)
            best_by_modality: dict[FusionModality, FusionObservation] = {}
            for item in admitted:
                existing = best_by_modality.get(item.modality)
                if existing is None or item.confidence_milli > existing.confidence_milli:
                    best_by_modality[item.modality] = item
            numerator = sum(item.confidence_milli * self.weights.get(modality, 500) for modality, item in best_by_modality.items())
            denominator = sum(self.weights.get(modality, 500) for modality in best_by_modality)
            score = round(numerator / denominator) if denominator else 0
            # Independent modalities increase confidence, but never above strongest evidence + bounded bonus.
            independent_bonus = min(120, max(0, len(best_by_modality) - 1) * 45)
            score = min(1000, score + independent_bonus)
            scored.append((score, event_type, list(best_by_modality.values())))
        scored.sort(key=lambda row: (-row[0], row[1].value))
        top_score, top_type, top_items = scored[0]
        if len(scored) > 1 and top_score - scored[1][0] < 80:
            return FusionDecision(None, top_score, tuple(sorted(x.evidence_ref for x in top_items)), tuple(sorted({x.modality for x in top_items}, key=lambda x: x.value)), None, ("AMBIGUOUS_EVENT_TYPES",))
        start = min(x.source_range.start_frame for x in top_items)
        end = max(x.source_range.end_frame_exclusive for x in top_items)
        source_range = SourceFrameRange(start, end)
        reasons: list[str] = []
        if top_score < self.minimum_confidence_milli:
            reasons.append("CONFIDENCE_BELOW_REVIEW_FLOOR")
            return FusionDecision(None, top_score, tuple(sorted(x.evidence_ref for x in top_items)), tuple(sorted({x.modality for x in top_items}, key=lambda x: x.value)), source_range, tuple(reasons))
        if len({x.modality for x in top_items}) == 1 and top_items[0].modality in {FusionModality.ASR, FusionModality.OCR, FusionModality.KNOWLEDGE}:
            reasons.append("SINGLE_WEAK_MODALITY_REQUIRES_REVIEW")
        if top_score < self.auto_confirm_milli:
            reasons.append("NEEDS_REVIEW")
        return FusionDecision(top_type, top_score, tuple(sorted(x.evidence_ref for x in top_items)), tuple(sorted({x.modality for x in top_items}, key=lambda x: x.value)), source_range, tuple(sorted(set(reasons))))


__all__ = ["DBDCrossModalFusion", "FusionDecision", "FusionModality", "FusionObservation"]
