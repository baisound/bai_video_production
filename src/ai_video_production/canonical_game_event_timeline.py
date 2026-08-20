"""TASK-049 immutable Canonical Game Event Timeline snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .canonical_game_event import (CanonicalGameEvent, GameMatch, parse_canonical_game_event, parse_game_match)
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


@dataclass(frozen=True, slots=True)
class CanonicalGameEventTimeline:
    match: GameMatch
    events: tuple[CanonicalGameEvent, ...]
    timeline_revision: int = 1
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not isinstance(self.match, GameMatch):
            raise ValueError("match must be a GameMatch")
        if not isinstance(self.events, tuple) or any(
            not isinstance(event, CanonicalGameEvent) for event in self.events
        ):
            raise ValueError("events must contain CanonicalGameEvent values")
        if isinstance(self.timeline_revision, bool) or not isinstance(self.timeline_revision, int) or self.timeline_revision < 1:
            raise ValueError("timeline_revision must be a positive integer")
        event_ids = [event.event_id for event in self.events]
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("timeline must contain at most one revision per event_id")
        for event in self.events:
            if event.match_id != self.match.match_id:
                raise ValueError("timeline event match_id does not match timeline match")
            if event.game_version != self.match.game_version:
                raise ValueError("timeline event game_version does not match timeline match")
            if event.environment is not self.match.environment:
                raise ValueError("timeline event environment does not match timeline match")
            if event.perspective is not self.match.perspective:
                raise ValueError("timeline event perspective does not match timeline match")
        ordered = tuple(
            sorted(
                self.events,
                key=lambda event: (
                    event.source_range.start_frame,
                    event.source_range.end_frame_exclusive,
                    event.event_id,
                ),
            )
        )
        object.__setattr__(self, "events", ordered)

    @classmethod
    def create(
        cls,
        match: GameMatch,
        events: Iterable[CanonicalGameEvent],
        *,
        timeline_revision: int = 1,
    ) -> "CanonicalGameEventTimeline":
        return cls(match, tuple(events), timeline_revision)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "timeline_revision": self.timeline_revision,
            "match": self.match.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "created_at": self.created_at,
        }
        return {
            **body,
            "timeline_sha256": sha256_bytes(canonical_json_bytes(body)),
        }


def parse_canonical_game_event_timeline(payload: Any) -> CanonicalGameEventTimeline:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid canonical game event timeline payload")
    try:
        item = CanonicalGameEventTimeline(
            match=parse_game_match(payload["match"]),
            events=tuple(parse_canonical_game_event(value) for value in payload["events"]),
            timeline_revision=payload["timeline_revision"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid canonical game event timeline payload") from exc
    if item.to_dict() != payload:
        raise ValueError("canonical game event timeline payload/hash is not canonical")
    return item


__all__ = ["CanonicalGameEventTimeline", "parse_canonical_game_event_timeline"]
