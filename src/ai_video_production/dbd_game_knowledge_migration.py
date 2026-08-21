"""Read-only migration planning for DbD Game Knowledge taxonomy repair."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .canonical_game_event import GameKnowledgeKind
from .dbd_game_information_classification import classify_game_information
from .dbd_game_knowledge_catalog import GameKnowledgeCandidate


_HUMAN_REVIEW_STATUSES = {
    "VERIFIED",
    "NEEDS_REVIEW",
    "UPDATE_AVAILABLE",
    "REJECTED",
    "DISABLED",
}


@dataclass(frozen=True, slots=True)
class KnowledgeKindCount:
    kind: GameKnowledgeKind
    count: int


@dataclass(frozen=True, slots=True)
class KnowledgeMigrationChange:
    candidate_id: str
    old_kind: GameKnowledgeKind
    proposed_kind: GameKnowledgeKind
    reason: str
    protected_human_decision: bool
    requires_human_review: bool


@dataclass(frozen=True, slots=True)
class KnowledgeMigrationDryRunReport:
    input_count: int
    old_counts: tuple[KnowledgeKindCount, ...]
    proposed_counts: tuple[KnowledgeKindCount, ...]
    changes: tuple[KnowledgeMigrationChange, ...]
    unchanged_count: int
    human_protected_count: int
    conflict_count: int
    apply_performed: bool = False


def _kind_counts(values: Iterable[GameKnowledgeKind]) -> tuple[KnowledgeKindCount, ...]:
    counts = Counter(values)
    return tuple(
        KnowledgeKindCount(kind=kind, count=counts[kind])
        for kind in sorted(counts, key=lambda value: value.value)
    )


def _is_human_touched(row: GameKnowledgeCandidate) -> bool:
    return bool(
        row.review_status in _HUMAN_REVIEW_STATUSES
        or row.manual_name_ja.strip()
        or row.manual_name_en.strip()
        or row.manual_aliases_ja
        or row.manual_image_path.strip()
    )


def _classify_for_migration(
    row: GameKnowledgeCandidate,
) -> tuple[GameKnowledgeKind, str, bool]:
    evidence = dict(row.details)
    evidence.pop("forced_type", None)
    evidence.pop("knowledge_kind", None)
    evidence["name_ja"] = row.effective_name_ja
    if row.knowledge_kind is GameKnowledgeKind.CHARACTER:
        proposed, source, _ = classify_game_information(evidence, source_kind=None)
        if proposed is GameKnowledgeKind.SURVIVOR and source == "KNOWN_ENTITY_MASTER":
            return proposed, "LEGACY_CHARACTER_KNOWN_SURVIVOR", False
        return GameKnowledgeKind.UNKNOWN, "LEGACY_CHARACTER_UNRESOLVED", True
    proposed, source, _ = classify_game_information(
        evidence, source_kind=row.knowledge_kind
    )
    return proposed, source, proposed is GameKnowledgeKind.UNKNOWN


def plan_game_knowledge_migration(
    rows: Iterable[GameKnowledgeCandidate],
) -> KnowledgeMigrationDryRunReport:
    """Build an immutable proposal without writing catalog or Workspace state."""
    source_rows = tuple(rows)
    proposed_kinds: list[GameKnowledgeKind] = []
    changes: list[KnowledgeMigrationChange] = []
    protected_count = 0
    conflict_count = 0
    for row in source_rows:
        proposed, reason, needs_review = _classify_for_migration(row)
        proposed_kinds.append(proposed)
        if proposed is row.knowledge_kind:
            continue
        protected = _is_human_touched(row)
        if protected:
            protected_count += 1
            conflict_count += 1
        changes.append(
            KnowledgeMigrationChange(
                candidate_id=row.candidate_id,
                old_kind=row.knowledge_kind,
                proposed_kind=proposed,
                reason=reason,
                protected_human_decision=protected,
                requires_human_review=needs_review or protected,
            )
        )
    return KnowledgeMigrationDryRunReport(
        input_count=len(source_rows),
        old_counts=_kind_counts(row.knowledge_kind for row in source_rows),
        proposed_counts=_kind_counts(proposed_kinds),
        changes=tuple(changes),
        unchanged_count=len(source_rows) - len(changes),
        human_protected_count=protected_count,
        conflict_count=conflict_count,
    )


__all__ = [
    "KnowledgeKindCount",
    "KnowledgeMigrationChange",
    "KnowledgeMigrationDryRunReport",
    "plan_game_knowledge_migration",
]
