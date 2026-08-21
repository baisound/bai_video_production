"""Convert DbD canonical game events into video-editing oriented candidates.

This layer never mutates the production timeline.  It produces a reviewable,
portable edit-intelligence plan that BAI VIDEO PRODUCTION/NLE adapters can consume.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical_game_event import CanonicalGameEvent, EventConfirmationState, EventReviewStatus, GameEventType, GameMatch
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


class EditCandidateKind(str, Enum):
    HIGHLIGHT = "HIGHLIGHT"
    MARKER = "MARKER"
    REVIEW = "REVIEW"


_EVENT_LABEL_JA = {
    GameEventType.MATCH_START: "試合開始",
    GameEventType.CHASE_START: "チェイス開始",
    GameEventType.CHASE_END: "チェイス終了",
    GameEventType.GENERATOR_COMPLETE: "発電機修理完了",
    GameEventType.INJURY: "負傷",
    GameEventType.DOWN: "ダウン",
    GameEventType.HOOK: "フック",
    GameEventType.UNHOOK: "救助",
    GameEventType.WINDOW_VAULT: "窓越え",
    GameEventType.PALLET_DROP: "板倒し",
    GameEventType.KILL: "死亡",
    GameEventType.ESCAPE: "脱出",
    GameEventType.UNKNOWN_EVENT: "要確認イベント",
}

_BASE_SCORE = {
    GameEventType.MATCH_START: 20,
    GameEventType.CHASE_START: 65,
    GameEventType.CHASE_END: 60,
    GameEventType.GENERATOR_COMPLETE: 76,
    GameEventType.INJURY: 65,
    GameEventType.DOWN: 82,
    GameEventType.HOOK: 78,
    GameEventType.UNHOOK: 72,
    GameEventType.WINDOW_VAULT: 58,
    GameEventType.PALLET_DROP: 64,
    GameEventType.KILL: 94,
    GameEventType.ESCAPE: 94,
    GameEventType.UNKNOWN_EVENT: 25,
}

_MARKER_COLORS = {
    GameEventType.CHASE_START: "Blue",
    GameEventType.CHASE_END: "Blue",
    GameEventType.GENERATOR_COMPLETE: "Yellow",
    GameEventType.DOWN: "Red",
    GameEventType.HOOK: "Red",
    GameEventType.UNHOOK: "Green",
    GameEventType.INJURY: "Orange",
    GameEventType.PALLET_DROP: "Yellow",
    GameEventType.WINDOW_VAULT: "Cyan",
    GameEventType.KILL: "Red",
    GameEventType.ESCAPE: "Green",
}


@dataclass(frozen=True, slots=True)
class EditingCandidate:
    candidate_id: str
    kind: EditCandidateKind
    event_ids: tuple[str, ...]
    source_start_frame: int
    source_end_frame_exclusive: int
    label_ja: str
    reason_codes: tuple[str, ...]
    confidence_milli: int
    highlight_score: int
    marker_color: str = "Blue"
    pre_roll_frames: int = 0
    post_roll_frames: int = 0
    human_review_required: bool = False

    def __post_init__(self) -> None:
        if self.source_start_frame < 0 or self.source_end_frame_exclusive <= self.source_start_frame:
            raise ValueError("editing candidate source range is invalid")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if not 0 <= self.highlight_score <= 100:
            raise ValueError("highlight_score must be 0..100")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind.value,
            "event_ids": list(self.event_ids),
            "source_start_frame": self.source_start_frame,
            "source_end_frame_exclusive": self.source_end_frame_exclusive,
            "label_ja": self.label_ja,
            "reason_codes": list(self.reason_codes),
            "confidence_milli": self.confidence_milli,
            "highlight_score": self.highlight_score,
            "marker_color": self.marker_color,
            "pre_roll_frames": self.pre_roll_frames,
            "post_roll_frames": self.post_roll_frames,
            "human_review_required": self.human_review_required,
        }


@dataclass(frozen=True, slots=True)
class EditingIntelligencePlan:
    match_id: str
    analysis_revision: int
    source_rate_num: int
    source_rate_den: int
    candidates: tuple[EditingCandidate, ...]
    generated_at: str = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "match_id": self.match_id,
            "analysis_revision": self.analysis_revision,
            "source_rate": {"numerator": self.source_rate_num, "denominator": self.source_rate_den},
            "generated_at": self.generated_at,
            "candidates": [x.to_dict() for x in self.candidates],
        }
        return {**body, "plan_sha256": sha256_bytes(canonical_json_bytes(body))}


class DbDEditingIntelligenceBuilder:
    """Create reviewable markers/highlights from canonical events."""

    def __init__(self, *, highlight_threshold: int = 60) -> None:
        if not 0 <= int(highlight_threshold) <= 100:
            raise ValueError("highlight_threshold must be 0..100")
        self.highlight_threshold = int(highlight_threshold)

    @staticmethod
    def _score(event: CanonicalGameEvent) -> int:
        base = _BASE_SCORE.get(event.event_type, 30)
        confidence_bonus = round((event.confidence_milli - 500) / 50)
        review_bonus = 5 if event.review_status in {EventReviewStatus.HUMAN_APPROVED, EventReviewStatus.HUMAN_CORRECTED} else 0
        if event.confirmation_state in {EventConfirmationState.NEEDS_REVIEW, EventConfirmationState.UNKNOWN, EventConfirmationState.POSSIBLE}:
            review_bonus -= 15
        return max(0, min(100, base + confidence_bonus + review_bonus))

    def build(self, match: GameMatch, events: Iterable[CanonicalGameEvent]) -> EditingIntelligencePlan:
        ordered = tuple(sorted(events, key=lambda e: (e.source_range.start_frame, e.source_range.end_frame_exclusive, e.event_id)))
        rows: list[EditingCandidate] = []
        fps = max(1, round(match.source_rate.numerator / match.source_rate.denominator))
        for index, event in enumerate(ordered):
            score = self._score(event)
            review = event.review_status is EventReviewStatus.PENDING or event.confirmation_state in {
                EventConfirmationState.DETECTED, EventConfirmationState.POSSIBLE,
                EventConfirmationState.UNKNOWN, EventConfirmationState.NEEDS_REVIEW,
            }
            kind = EditCandidateKind.HIGHLIGHT if score >= self.highlight_threshold else (EditCandidateKind.REVIEW if review else EditCandidateKind.MARKER)
            rows.append(EditingCandidate(
                candidate_id=f"edit-{event.event_id}-r{event.revision}",
                kind=kind,
                event_ids=(event.event_id,),
                source_start_frame=event.source_range.start_frame,
                source_end_frame_exclusive=event.source_range.end_frame_exclusive,
                label_ja=_EVENT_LABEL_JA.get(event.event_type, event.event_type.value),
                reason_codes=(event.event_type.value, "LOW_CONFIDENCE" if review else "CANONICAL_EVENT"),
                confidence_milli=event.confidence_milli,
                highlight_score=score,
                marker_color=_MARKER_COLORS.get(event.event_type, "Blue"),
                pre_roll_frames=2 * fps if kind is EditCandidateKind.HIGHLIGHT else 0,
                post_roll_frames=3 * fps if kind is EditCandidateKind.HIGHLIGHT else 0,
                human_review_required=review,
            ))
        return EditingIntelligencePlan(
            match_id=match.match_id,
            analysis_revision=match.analysis_revision,
            source_rate_num=match.source_rate.numerator,
            source_rate_den=match.source_rate.denominator,
            candidates=tuple(rows),
        )


__all__ = ["EditCandidateKind", "EditingCandidate", "EditingIntelligencePlan", "DbDEditingIntelligenceBuilder"]
