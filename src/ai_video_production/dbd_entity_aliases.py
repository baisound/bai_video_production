"""TASK-050 R4 generalized DbD entity aliases/readings.

This is an auxiliary resolution index. Canonical game facts remain in their
existing Knowledge stores. Every alias points to a stable canonical entity_id
and GameKnowledgeKind; this module does not create competing entity truth.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from enum import Enum
import sqlite3
from pathlib import Path
import unicodedata
from typing import Iterable

from .canonical_game_event import GameKnowledgeKind


class EntityAliasType(str, Enum):
    OFFICIAL_NAME = "OFFICIAL_NAME"
    OFFICIAL_ENGLISH = "OFFICIAL_ENGLISH"
    READING = "READING"
    COMMUNITY_SHORT_NAME = "COMMUNITY_SHORT_NAME"
    COMMUNITY_NICKNAME = "COMMUNITY_NICKNAME"
    ASR_VARIANT = "ASR_VARIANT"
    COMMON_MISSPELLING = "COMMON_MISSPELLING"


class EntityAliasReviewStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


def normalize_entity_alias(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("alias must be text")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(normalized.split())
    if not normalized or len(normalized) > 256:
        raise ValueError("alias must normalize to 1..256 characters")
    return normalized


@dataclass(frozen=True, slots=True)
class EntityAliasRecord:
    entity_id: str
    knowledge_kind: GameKnowledgeKind
    alias_text: str
    alias_type: EntityAliasType
    locale: str = "ja-JP"
    reading: str | None = None
    priority: int = 50
    review_status: EntityAliasReviewStatus = EntityAliasReviewStatus.CANDIDATE
    source_ref: str = "manual://owner"

    def __post_init__(self) -> None:
        if not self.entity_id.strip() or len(self.entity_id) > 128:
            raise ValueError("entity_id is required")
        normalize_entity_alias(self.alias_text)
        if self.reading is not None:
            normalize_entity_alias(self.reading)
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be 0..100")
        if not self.locale.strip() or len(self.locale) > 32:
            raise ValueError("locale is required")
        if not self.source_ref.strip():
            raise ValueError("source_ref is required")

    @property
    def normalized_alias(self) -> str:
        return normalize_entity_alias(self.alias_text)


@dataclass(frozen=True, slots=True)
class EntityAliasResolution:
    entity_id: str
    knowledge_kind: GameKnowledgeKind
    matched_text: str
    alias_type: EntityAliasType
    priority: int


class EntityAliasCatalog:
    """Small SQLite index used by UI, ASR and search/RAG front doors."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn:
            with conn:
                conn.executescript("""
            CREATE TABLE IF NOT EXISTS entity_alias(
              entity_id TEXT NOT NULL,
              knowledge_kind TEXT NOT NULL,
              alias_text TEXT NOT NULL,
              normalized_alias TEXT NOT NULL,
              alias_type TEXT NOT NULL,
              locale TEXT NOT NULL,
              reading TEXT,
              priority INTEGER NOT NULL,
              review_status TEXT NOT NULL,
              source_ref TEXT NOT NULL,
              PRIMARY KEY(entity_id, knowledge_kind, normalized_alias, alias_type)
            );
                CREATE INDEX IF NOT EXISTS entity_alias_lookup
                  ON entity_alias(normalized_alias, locale, review_status, priority DESC);
                """)

    def put(self, record: EntityAliasRecord) -> None:
        with closing(sqlite3.connect(self.path)) as conn:
            with conn:
                conn.execute(
                    """INSERT INTO entity_alias(
                       entity_id,knowledge_kind,alias_text,normalized_alias,alias_type,
                       locale,reading,priority,review_status,source_ref)
                       VALUES(?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(entity_id,knowledge_kind,normalized_alias,alias_type)
                       DO UPDATE SET alias_text=excluded.alias_text, locale=excluded.locale,
                         reading=excluded.reading, priority=excluded.priority,
                         review_status=excluded.review_status, source_ref=excluded.source_ref""",
                    (
                        record.entity_id, record.knowledge_kind.value, record.alias_text,
                        record.normalized_alias, record.alias_type.value, record.locale,
                        record.reading, record.priority, record.review_status.value,
                        record.source_ref,
                    ),
                )

    def put_many(self, records: Iterable[EntityAliasRecord]) -> None:
        for record in records:
            self.put(record)

    def replace_entity_aliases(self, entity_id: str, knowledge_kind: GameKnowledgeKind, records: Iterable[EntityAliasRecord]) -> None:
        """Replace the searchable aliases for one entity as one bounded catalog operation."""
        rows = tuple(records)
        if any(row.entity_id != entity_id or row.knowledge_kind is not knowledge_kind for row in rows):
            raise ValueError("replacement aliases must belong to the same entity and knowledge kind")
        with closing(sqlite3.connect(self.path)) as conn:
            with conn:
                conn.execute(
                    "DELETE FROM entity_alias WHERE entity_id=? AND knowledge_kind=?",
                    (entity_id, knowledge_kind.value),
                )
                for record in rows:
                    conn.execute(
                        """INSERT INTO entity_alias(
                           entity_id,knowledge_kind,alias_text,normalized_alias,alias_type,
                           locale,reading,priority,review_status,source_ref)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (
                            record.entity_id, record.knowledge_kind.value, record.alias_text,
                            record.normalized_alias, record.alias_type.value, record.locale,
                            record.reading, record.priority, record.review_status.value,
                            record.source_ref,
                        ),
                    )

    def count(self) -> int:
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM entity_alias").fetchone()
        return 0 if row is None else int(row[0])

    def search(
        self,
        query: str,
        *,
        knowledge_kind: GameKnowledgeKind | None = None,
        locale: str = "ja-JP",
        verified_only: bool = False,
        limit: int = 50,
    ) -> tuple[EntityAliasResolution, ...]:
        if not isinstance(query, str):
            raise ValueError("query must be text")

        raw_query = query.strip()

        sql = """SELECT entity_id,knowledge_kind,alias_text,alias_type,priority
                 FROM entity_alias
                 WHERE locale=?"""
        params: list[object] = [locale]

        normalized: str | None = None

        if raw_query:
            normalized = normalize_entity_alias(query)
            sql += " AND normalized_alias LIKE ?"
            params.append(f"%{normalized}%")

        if knowledge_kind is not None:
            sql += " AND knowledge_kind=?"
            params.append(knowledge_kind.value)

        if verified_only:
            sql += " AND review_status='VERIFIED'"

        if normalized is not None:
            sql += (
                " ORDER BY CASE WHEN normalized_alias=? THEN 0 ELSE 1 END,"
                " priority DESC, entity_id LIMIT ?"
            )
            params.extend([normalized, limit])
        else:
            sql += " ORDER BY priority DESC, normalized_alias, entity_id LIMIT ?"
            params.append(limit)

        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(sql, params).fetchall()

        return tuple(
            EntityAliasResolution(
                entity_id=row[0],
                knowledge_kind=GameKnowledgeKind(row[1]),
                matched_text=row[2],
                alias_type=EntityAliasType(row[3]),
                priority=int(row[4]),
            )
            for row in rows
        )

    def resolve_unique(
        self,
        text: str,
        *,
        locale: str = "ja-JP",
        verified_only: bool = True,
    ) -> EntityAliasResolution | None:
        normalized = normalize_entity_alias(text)
        sql = """SELECT entity_id,knowledge_kind,alias_text,alias_type,priority
                 FROM entity_alias
                 WHERE locale=? AND normalized_alias=?"""
        params: list[object] = [locale, normalized]
        if verified_only:
            sql += " AND review_status='VERIFIED'"
        sql += " ORDER BY priority DESC, entity_id"
        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(sql, params).fetchall()
        if not rows:
            return None
        identities = {(row[0], row[1]) for row in rows}
        if len(identities) != 1:
            raise ValueError("同じ呼び方が複数のゲーム要素に一致しました。選択確認が必要です。")
        row = rows[0]
        return EntityAliasResolution(
            entity_id=row[0],
            knowledge_kind=GameKnowledgeKind(row[1]),
            matched_text=row[2],
            alias_type=EntityAliasType(row[3]),
            priority=int(row[4]),
        )


def perk_alias_type_to_entity(alias_type: str) -> EntityAliasType:
    """Bridge existing TASK-049 PerkAliasType without changing its contract."""
    mapping = {
        "COMMUNITY": EntityAliasType.COMMUNITY_NICKNAME,
        "ABBREVIATION": EntityAliasType.COMMUNITY_SHORT_NAME,
        "OLD_NAME": EntityAliasType.COMMUNITY_NICKNAME,
        "SEARCH_SYNONYM": EntityAliasType.COMMUNITY_NICKNAME,
        "ASR_VARIANT": EntityAliasType.ASR_VARIANT,
        "MANUAL": EntityAliasType.COMMUNITY_NICKNAME,
    }
    return mapping.get(alias_type, EntityAliasType.COMMUNITY_NICKNAME)
