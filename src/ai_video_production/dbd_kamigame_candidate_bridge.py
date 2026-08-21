"""Bridge normalized Kamigame CANDIDATE records into searchable review state.

Community-reference material remains CANDIDATE until explicit Human verification.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .canonical_game_event import GameKnowledgeKind
from .dbd_game_information_classification import classify_game_information
from .dbd_entity_aliases import (
    EntityAliasCatalog,
    EntityAliasRecord,
    EntityAliasReviewStatus,
    EntityAliasType,
)
from .dbd_game_knowledge_catalog import (
    GameKnowledgeCandidate,
    GameKnowledgeReviewCatalog,
    candidate_from_normalized,
)


@dataclass(frozen=True, slots=True)
class KamigameCandidateSummary:
    candidate_id: str
    knowledge_kind: GameKnowledgeKind
    name_ja: str
    aliases_ja: tuple[str, ...]
    review_status: str
    source_page_url: str
    image_urls: tuple[str, ...] = ()
    details: dict[str, object] | None = None

    @property
    def kind_ja(self) -> str:
        return {
            GameKnowledgeKind.PERK: "パーク",
            GameKnowledgeKind.KILLER: "キラー",
            GameKnowledgeKind.ITEM: "アイテム",
            GameKnowledgeKind.ADDON: "アドオン",
            GameKnowledgeKind.MAP: "マップ",
            GameKnowledgeKind.REALM: "領域",
            GameKnowledgeKind.OFFERING: "オファリング",
            GameKnowledgeKind.UNKNOWN: "未分類・要確認",
            GameKnowledgeKind.SURVIVOR: "サバイバー",
            GameKnowledgeKind.KNOWLEDGE: "ナレッジ系",
        }.get(
            self.knowledge_kind,
            "未分類・要確認" if self.knowledge_kind is GameKnowledgeKind.CHARACTER else self.knowledge_kind.value,
        )


@dataclass(frozen=True, slots=True)
class KamigameAliasIndexReport:
    candidates: int
    alias_records: int


_COMMON_VARIANTS_JA: dict[str, tuple[str, ...]] = {"鋼の意思": ("鋼の意志",)}
_FILE_KINDS: tuple[tuple[str, GameKnowledgeKind], ...] = (
    ("survivor-perks.jsonl", GameKnowledgeKind.PERK),
    ("killer-perks.jsonl", GameKnowledgeKind.PERK),
    ("killers.jsonl", GameKnowledgeKind.KILLER),
    ("items.jsonl", GameKnowledgeKind.ITEM),
    ("addons.jsonl", GameKnowledgeKind.ADDON),
    ("maps.jsonl", GameKnowledgeKind.MAP),
)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_no}: invalid JSONL") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path.name}:{line_no}: record must be an object")
            rows.append(payload)
    return rows


def _derived_candidate_id(prefix: str, name: str) -> str:
    return f"{prefix}_kamigame_{hashlib.sha256(name.encode('utf-8')).hexdigest()[:16]}"


def load_kamigame_candidates(output_root: str | Path) -> tuple[GameKnowledgeCandidate, ...]:
    root = Path(output_root)
    normalized = root / "normalized"
    rows: list[GameKnowledgeCandidate] = []
    derived: dict[str, GameKnowledgeCandidate] = {}
    for filename, kind in _FILE_KINDS:
        for payload in _read_jsonl(normalized / filename):
            if not (payload.get("candidate_id") and (payload.get("name_ja") or payload.get("map_name_ja"))):
                continue
            normalized_payload = dict(payload)
            classified_kind, classification_source, classification_confidence = classify_game_information(
                normalized_payload, source_kind=kind
            )
            normalized_payload["classification_source"] = classification_source
            normalized_payload["classification_confidence"] = classification_confidence
            candidate = candidate_from_normalized(normalized_payload, classified_kind)
            local = str(candidate.details.get("local_image_path") or "").strip()
            if local and not Path(local).is_absolute():
                candidate = replace(candidate, details={**candidate.details, "local_image_path": str((root / local).resolve())})
            rows.append(candidate)
            if kind is GameKnowledgeKind.MAP:
                for field, derived_kind, prefix in (
                    ("realm_name_ja", GameKnowledgeKind.REALM, "realm"),
                    ("offering_name_ja", GameKnowledgeKind.OFFERING, "offering"),
                ):
                    name = str(payload.get(field) or "").strip()
                    if not name:
                        continue
                    did = _derived_candidate_id(prefix, name)
                    source_payload = {
                        "candidate_id": did, "name_ja": name, "aliases_ja": [],
                        "source_page_url": str(payload.get("detail_url") or payload.get("source_page_url") or ""),
                        "review_status": "CANDIDATE", "source_authority": "COMMUNITY_REFERENCE",
                        "derived_from_map_id": str(payload.get("candidate_id")),
                    }
                    derived[did] = candidate_from_normalized(source_payload, derived_kind)
    rows.extend(derived.values())
    killer_by_name = {row.effective_name_ja: row.candidate_id for row in rows if row.knowledge_kind is GameKnowledgeKind.KILLER}
    realm_by_name = {row.effective_name_ja: row.candidate_id for row in rows if row.knowledge_kind is GameKnowledgeKind.REALM}
    offering_by_name = {row.effective_name_ja: row.candidate_id for row in rows if row.knowledge_kind is GameKnowledgeKind.OFFERING}
    related: list[GameKnowledgeCandidate] = []
    for row in rows:
        details = dict(row.details)
        if row.knowledge_kind is GameKnowledgeKind.ADDON:
            owner_name = str(details.get("owner_killer_name_ja") or "").strip()
            if owner_name in killer_by_name:
                details["owner_killer_candidate_id"] = killer_by_name[owner_name]
        elif row.knowledge_kind is GameKnowledgeKind.MAP:
            realm_name = str(details.get("realm_name_ja") or "").strip()
            offering_name = str(details.get("offering_name_ja") or "").strip()
            if realm_name in realm_by_name: details["realm_candidate_id"] = realm_by_name[realm_name]
            if offering_name in offering_by_name: details["offering_candidate_id"] = offering_by_name[offering_name]
        related.append(replace(row, details=details))
    return tuple(sorted(related, key=lambda x: (x.knowledge_kind.value, x.effective_name_ja, x.candidate_id)))


def load_kamigame_candidate_summaries(output_root: str | Path) -> tuple[KamigameCandidateSummary, ...]:
    return tuple(
        KamigameCandidateSummary(
            candidate_id=row.candidate_id,
            knowledge_kind=row.knowledge_kind,
            name_ja=row.effective_name_ja,
            aliases_ja=row.effective_aliases_ja,
            review_status=row.review_status,
            source_page_url=row.source_page_url,
            image_urls=row.image_urls,
            details=row.details,
        )
        for row in load_kamigame_candidates(output_root)
    )


def _alias_records(summary: KamigameCandidateSummary) -> Iterable[EntityAliasRecord]:
    yield EntityAliasRecord(
        entity_id=summary.candidate_id,
        knowledge_kind=summary.knowledge_kind,
        alias_text=summary.name_ja,
        alias_type=EntityAliasType.OFFICIAL_NAME,
        priority=100,
        review_status=EntityAliasReviewStatus.CANDIDATE,
        source_ref=summary.source_page_url,
    )
    for alias in summary.aliases_ja:
        yield EntityAliasRecord(
            entity_id=summary.candidate_id,
            knowledge_kind=summary.knowledge_kind,
            alias_text=alias,
            alias_type=EntityAliasType.COMMUNITY_SHORT_NAME,
            priority=80,
            review_status=EntityAliasReviewStatus.CANDIDATE,
            source_ref=summary.source_page_url,
        )
    for variant in _COMMON_VARIANTS_JA.get(summary.name_ja, ()):
        yield EntityAliasRecord(
            entity_id=summary.candidate_id,
            knowledge_kind=summary.knowledge_kind,
            alias_text=variant,
            alias_type=EntityAliasType.COMMON_MISSPELLING,
            priority=60,
            review_status=EntityAliasReviewStatus.CANDIDATE,
            source_ref=summary.source_page_url,
        )


def index_kamigame_candidates_for_search(catalog: EntityAliasCatalog, output_root: str | Path) -> KamigameAliasIndexReport:
    summaries = load_kamigame_candidate_summaries(output_root)
    records: list[EntityAliasRecord] = []
    for summary in summaries:
        records.extend(_alias_records(summary))
    catalog.put_many(records)
    return KamigameAliasIndexReport(candidates=len(summaries), alias_records=len(records))


def sync_kamigame_review_catalog(catalog: GameKnowledgeReviewCatalog, output_root: str | Path) -> int:
    return catalog.upsert_external(load_kamigame_candidates(output_root))


__all__ = [
    "KamigameCandidateSummary", "KamigameAliasIndexReport", "load_kamigame_candidates",
    "load_kamigame_candidate_summaries", "index_kamigame_candidates_for_search",
    "sync_kamigame_review_catalog",
]
