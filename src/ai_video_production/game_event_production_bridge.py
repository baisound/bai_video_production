"""TASK-049 R8A proposal-only Game Event -> BVP Production bridge.

This module crosses the CGEL / Production responsibility boundary without
crossing the Production *authority* boundary.  It compiles immutable proposal
records from a reviewed canonical game Event and a VALIDATED commentary
candidate.  It does not mutate Production Control, Subtitle Workspace,
Timeline, Resolve, assets, or external providers.

A later R8B adoption adapter may translate an accepted proposal bundle into
existing BVP application-service requests after the relevant Human/ownership
Gate is satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameMatch,
)
from .game_commentary import (
    CommentaryCandidate,
    CommentaryCandidateStatus,
    CommentaryDisposition,
)
from .game_event_evidence import SourceFrameRange
from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso
from .timebase import FrameRate


class GameProductionProposalKind(str, Enum):
    HIGHLIGHT = "HIGHLIGHT"
    NARRATION = "NARRATION"
    SUBTITLE = "SUBTITLE"


def _stable_text(value: str, *, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{field_name} must be a non-empty bounded string")
    return value


def _sha(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field_name} must be a canonical sha256 identity")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a canonical sha256 identity") from exc
    return value


@dataclass(frozen=True, slots=True)
class GameProductionProposalItem:
    kind: GameProductionProposalKind
    source_range: SourceFrameRange
    text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, GameProductionProposalKind):
            raise ValueError("kind must be a GameProductionProposalKind")
        if not isinstance(self.source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        if self.kind is GameProductionProposalKind.HIGHLIGHT:
            if self.text is not None:
                raise ValueError("HIGHLIGHT proposal must not carry narration text")
        else:
            if self.text is None:
                raise ValueError(f"{self.kind.value} proposal requires text")
            _stable_text(self.text, field_name="proposal text", maximum=16000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "source_range": self.source_range.to_dict(),
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class GameProductionProposalBundle:
    match_id: str
    event_id: str
    event_revision: int
    source_asset_id: str
    source_rate: FrameRate
    event_sha256: str
    commentary_candidate_id: str
    commentary_candidate_sha256: str
    evidence_refs: tuple[str, ...]
    knowledge_ref_sha256s: tuple[str, ...]
    items: tuple[GameProductionProposalItem, ...]
    bundle_id: str = field(default_factory=lambda: generate_id(IdKind.CANDIDATE))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.bundle_id, IdKind.CANDIDATE)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        validate_id(self.source_asset_id, IdKind.ASSET)
        validate_id(self.commentary_candidate_id, IdKind.CANDIDATE)
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be positive")
        if not isinstance(self.source_rate, FrameRate):
            raise ValueError("source_rate must be an exact FrameRate")
        _sha(self.event_sha256, field_name="event_sha256")
        _sha(self.commentary_candidate_sha256, field_name="commentary_candidate_sha256")
        if self.evidence_refs != tuple(sorted(set(self.evidence_refs))):
            raise ValueError("evidence_refs must be unique and canonically sorted")
        for ref in self.evidence_refs:
            validate_id(ref, IdKind.GAME_EVIDENCE)
        if self.knowledge_ref_sha256s != tuple(sorted(set(self.knowledge_ref_sha256s))):
            raise ValueError("knowledge_ref_sha256s must be unique and canonically sorted")
        for ref_hash in self.knowledge_ref_sha256s:
            _sha(ref_hash, field_name="knowledge_ref_sha256")
        if not self.items:
            raise ValueError("proposal bundle must contain at least one item")
        if any(not isinstance(item, GameProductionProposalItem) for item in self.items):
            raise ValueError("items must contain GameProductionProposalItem values")
        kinds = tuple(item.kind.value for item in self.items)
        if kinds != tuple(sorted(set(kinds))):
            raise ValueError("proposal kinds must be unique and canonically sorted")
        _stable_text(self.created_at, field_name="created_at", maximum=64)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "task_owner": "TASK-049",
            "authority_state": "PROPOSAL_ONLY",
            "bundle_id": self.bundle_id,
            "match_id": self.match_id,
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "source_asset_id": self.source_asset_id,
            "source_rate": {
                "numerator": self.source_rate.numerator,
                "denominator": self.source_rate.denominator,
            },
            "event_sha256": self.event_sha256,
            "commentary_candidate_id": self.commentary_candidate_id,
            "commentary_candidate_sha256": self.commentary_candidate_sha256,
            "evidence_refs": list(self.evidence_refs),
            "knowledge_ref_sha256s": list(self.knowledge_ref_sha256s),
            "items": [item.to_dict() for item in self.items],
            "requires_human_adoption": True,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "external_write_authorized": False,
            "created_at": self.created_at,
        }
        return {**body, "bridge_bundle_sha256": sha256_bytes(canonical_json_bytes(body))}


class GameEventToProductionBridge:
    """Compile immutable, side-effect-free production proposals."""

    @staticmethod
    def compile(
        *,
        match: GameMatch,
        event: CanonicalGameEvent,
        commentary: CommentaryCandidate,
    ) -> GameProductionProposalBundle:
        if not isinstance(match, GameMatch):
            raise ValueError("match must be a GameMatch")
        if not isinstance(event, CanonicalGameEvent):
            raise ValueError("event must be a CanonicalGameEvent")
        if not isinstance(commentary, CommentaryCandidate):
            raise ValueError("commentary must be a CommentaryCandidate")

        if event.match_id != match.match_id or commentary.plan.match_id != match.match_id:
            raise ValueError("match lineage mismatch")
        if commentary.plan.event_id != event.event_id or commentary.plan.event_revision != event.revision:
            raise ValueError("event/commentary lineage mismatch")
        if event.game_version != match.game_version or event.environment is not match.environment:
            raise ValueError("event/match game-version or environment mismatch")

        if event.confirmation_state is not EventConfirmationState.CONFIRMED:
            raise ValueError("only CONFIRMED Events are bridgeable")
        if event.review_status not in {
            EventReviewStatus.AUTO_ACCEPTED,
            EventReviewStatus.HUMAN_APPROVED,
            EventReviewStatus.HUMAN_CORRECTED,
        }:
            raise ValueError("Event review status is not bridgeable")
        if commentary.status is not CommentaryCandidateStatus.VALIDATED:
            raise ValueError("only VALIDATED Commentary candidates are bridgeable")
        if commentary.plan.disposition is not CommentaryDisposition.PROPOSE:
            raise ValueError("ABSTAIN Commentary cannot cross the Production bridge")

        event_payload = event.to_dict()
        commentary_payload = commentary.to_dict()
        event_evidence = tuple(sorted(event.evidence_refs))
        if commentary.plan.evidence_refs != event_evidence:
            raise ValueError("Commentary Evidence lineage does not exactly match Event Evidence")
        event_knowledge = tuple(
            sorted(ref.to_dict()["knowledge_ref_sha256"] for ref in event.knowledge_refs)
        )
        if commentary.plan.knowledge_ref_sha256s != event_knowledge:
            raise ValueError("Commentary Knowledge lineage does not exactly match Event Knowledge")

        # R8A intentionally keeps ranges in the admitted analysis/source clock.
        # Production-timeline mapping remains an adoption-time responsibility.
        items = tuple(
            sorted(
                (
                    GameProductionProposalItem(
                        GameProductionProposalKind.HIGHLIGHT,
                        event.source_range,
                    ),
                    GameProductionProposalItem(
                        GameProductionProposalKind.NARRATION,
                        event.source_range,
                        commentary.draft.text,
                    ),
                    GameProductionProposalItem(
                        GameProductionProposalKind.SUBTITLE,
                        event.source_range,
                        commentary.draft.text,
                    ),
                ),
                key=lambda item: item.kind.value,
            )
        )

        return GameProductionProposalBundle(
            match_id=match.match_id,
            event_id=event.event_id,
            event_revision=event.revision,
            source_asset_id=match.source_asset_id,
            source_rate=match.source_rate,
            event_sha256=event_payload["event_sha256"],
            commentary_candidate_id=commentary.candidate_id,
            commentary_candidate_sha256=commentary_payload["commentary_candidate_sha256"],
            evidence_refs=event_evidence,
            knowledge_ref_sha256s=event_knowledge,
            items=items,
        )


__all__ = [
    "GameEventToProductionBridge",
    "GameProductionProposalBundle",
    "GameProductionProposalItem",
    "GameProductionProposalKind",
]
