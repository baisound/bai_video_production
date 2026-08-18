"""TASK-049 canonical DbD Item / Add-on knowledge and visual-reference binding."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .canonical_game_event import GameEnvironment, GameKnowledgeKind, GameKnowledgeRef
from .dbd_perk_knowledge import DBDPatchVersion, PerkEnvironment
from .dbd_vision_slices import GrayImage, ReferenceSliceIndex
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso

_ID_RE = re.compile(r"^(item|addon)_[a-z0-9][a-z0-9_]{1,123}$")


class LoadoutKnowledgeKind(str, Enum):
    ITEM = "ITEM"
    ADDON = "ADDON"


class LoadoutKnowledgeStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class LoadoutKnowledgeSource:
    source_id: str
    authority: str
    source_ref: str
    content_sha256: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.authority or not self.source_ref or len(self.content_sha256) != 64:
            raise ValueError("invalid Item/Add-on knowledge source")


@dataclass(frozen=True, slots=True)
class LoadoutKnowledgeRevision:
    entity_id: str
    revision_id: str
    kind: LoadoutKnowledgeKind
    name_ja: str
    name_en: str
    environment: PerkEnvironment
    game_version_from: str
    game_version_to: str | None
    status: LoadoutKnowledgeStatus
    source_id: str
    description_ja: str = ""
    description_en: str = ""
    parent_item_id: str | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.entity_id):
            raise ValueError("entity_id must use item_* or addon_*")
        if not self.revision_id or not self.name_en or not self.source_id:
            raise ValueError("revision_id/name/source are required")
        if not isinstance(self.kind, LoadoutKnowledgeKind) or not isinstance(self.environment, PerkEnvironment) or not isinstance(self.status, LoadoutKnowledgeStatus):
            raise ValueError("invalid Item/Add-on knowledge enum")
        DBDPatchVersion.parse(self.game_version_from)
        if self.game_version_to is not None:
            DBDPatchVersion.parse(self.game_version_to)
        if self.parent_item_id is not None and not self.parent_item_id.startswith("item_"):
            raise ValueError("parent_item_id must use item_* when supplied")
        if self.created_at and len(self.created_at) > 64:
            raise ValueError("created_at too long")

    def compatible(self, game_version: str) -> bool:
        version = DBDPatchVersion.parse(game_version)
        if version < DBDPatchVersion.parse(self.game_version_from):
            return False
        return self.game_version_to is None or version <= DBDPatchVersion.parse(self.game_version_to)

    def to_knowledge_ref(self) -> GameKnowledgeRef:
        if self.environment not in {PerkEnvironment.LIVE, PerkEnvironment.PTB}:
            raise ProductError(
                "ERR_LOADOUT_ENVIRONMENT_NOT_BINDABLE",
                "Only LIVE/PTB Item/Add-on revisions may bind automatically to an Event",
                ProductErrorCategory.VALIDATION,
            )
        return GameKnowledgeRef(
            knowledge_kind=GameKnowledgeKind.ITEM if self.kind is LoadoutKnowledgeKind.ITEM else GameKnowledgeKind.ADDON,
            entity_id=self.entity_id,
            revision_id=self.revision_id,
            environment=GameEnvironment(self.environment.value),
            game_version_from=self.game_version_from,
            game_version_to=self.game_version_to,
            source_provenance_ref=f"loadout-knowledge-revision://{self.revision_id}",
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "entity_id": self.entity_id,
            "revision_id": self.revision_id,
            "kind": self.kind.value,
            "name_ja": self.name_ja,
            "name_en": self.name_en,
            "environment": self.environment.value,
            "game_version_from": self.game_version_from,
            "game_version_to": self.game_version_to,
            "status": self.status.value,
            "source_id": self.source_id,
            "description_ja": self.description_ja,
            "description_en": self.description_en,
            "parent_item_id": self.parent_item_id,
            "created_at": self.created_at,
        }
        return {**body, "revision_sha256": sha256_bytes(canonical_json_bytes(body))}


class DbDLoadoutKnowledgeStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS source(
              source_id TEXT PRIMARY KEY, authority TEXT NOT NULL, source_ref TEXT NOT NULL, content_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revision(
              entity_id TEXT NOT NULL, revision_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
              name_ja TEXT NOT NULL, name_en TEXT NOT NULL, environment TEXT NOT NULL,
              game_version_from TEXT NOT NULL, game_version_to TEXT, status TEXT NOT NULL,
              source_id TEXT NOT NULL REFERENCES source(source_id), description_ja TEXT NOT NULL,
              description_en TEXT NOT NULL, parent_item_id TEXT, created_at TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alias(
              normalized_alias TEXT NOT NULL, entity_id TEXT NOT NULL, locale TEXT NOT NULL,
              PRIMARY KEY(normalized_alias, entity_id, locale)
            );
            """)

    def put_source(self, source: LoadoutKnowledgeSource) -> None:
        with self._connect() as conn:
            existing = conn.execute("SELECT authority,source_ref,content_sha256 FROM source WHERE source_id=?", (source.source_id,)).fetchone()
            values = (source.authority, source.source_ref, source.content_sha256)
            if existing is not None:
                if tuple(existing) != values:
                    raise ProductError("ERR_LOADOUT_KNOWLEDGE_SOURCE_IMMUTABLE", "Item/Add-on source identifiers are immutable", ProductErrorCategory.STATE)
                return
            conn.execute("INSERT INTO source(source_id,authority,source_ref,content_sha256) VALUES(?,?,?,?)", (source.source_id, *values))

    def put_revision(self, revision: LoadoutKnowledgeRevision) -> None:
        if revision.status is LoadoutKnowledgeStatus.VERIFIED:
            with self._connect() as conn:
                if conn.execute("SELECT 1 FROM source WHERE source_id=?", (revision.source_id,)).fetchone() is None:
                    raise ProductError("ERR_LOADOUT_KNOWLEDGE_SOURCE_REQUIRED", "VERIFIED Item/Add-on revision requires provenance", ProductErrorCategory.VALIDATION)
        created = revision.created_at or utc_now_iso()
        stored = LoadoutKnowledgeRevision(**{**{k: getattr(revision, k) for k in revision.__dataclass_fields__}, "created_at": created})
        payload = json.dumps(stored.to_dict(), ensure_ascii=False, separators=(",", ":"))
        with self._connect() as conn:
            existing = conn.execute("SELECT payload_json FROM revision WHERE revision_id=?", (stored.revision_id,)).fetchone()
            if existing is not None:
                if existing[0] != payload:
                    raise ProductError("ERR_LOADOUT_KNOWLEDGE_REVISION_IMMUTABLE", "Item/Add-on revision identifiers are immutable", ProductErrorCategory.STATE)
                return
            conn.execute(
                """INSERT INTO revision(entity_id,revision_id,kind,name_ja,name_en,environment,game_version_from,game_version_to,status,source_id,description_ja,description_en,parent_item_id,created_at,payload_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (stored.entity_id, stored.revision_id, stored.kind.value, stored.name_ja, stored.name_en, stored.environment.value,
                 stored.game_version_from, stored.game_version_to, stored.status.value, stored.source_id, stored.description_ja,
                 stored.description_en, stored.parent_item_id, stored.created_at, payload),
            )

    def add_alias(self, entity_id: str, alias: str, *, locale: str = "ja-JP") -> None:
        normalized = " ".join(alias.casefold().split())
        if not normalized:
            raise ValueError("alias must not be empty")
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO alias(normalized_alias,entity_id,locale) VALUES(?,?,?)", (normalized, entity_id, locale))

    def lookup(self, entity_id: str, *, game_version: str, environment: PerkEnvironment = PerkEnvironment.LIVE) -> LoadoutKnowledgeRevision:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM revision WHERE entity_id=? AND environment=? AND status='VERIFIED'", (entity_id, environment.value)).fetchall()
        candidates: list[LoadoutKnowledgeRevision] = []
        for row in rows:
            document = json.loads(row[0])
            expected = document.pop("revision_sha256", None)
            if expected != sha256_bytes(canonical_json_bytes(document)):
                raise ProductError("ERR_LOADOUT_KNOWLEDGE_INTEGRITY", "Item/Add-on revision checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
            item = LoadoutKnowledgeRevision(
                entity_id=document["entity_id"], revision_id=document["revision_id"], kind=LoadoutKnowledgeKind(document["kind"]),
                name_ja=document["name_ja"], name_en=document["name_en"], environment=PerkEnvironment(document["environment"]),
                game_version_from=document["game_version_from"], game_version_to=document["game_version_to"], status=LoadoutKnowledgeStatus(document["status"]),
                source_id=document["source_id"], description_ja=document["description_ja"], description_en=document["description_en"],
                parent_item_id=document["parent_item_id"], created_at=document["created_at"],
            )
            if item.to_dict()["revision_sha256"] != expected:
                raise ProductError("ERR_LOADOUT_KNOWLEDGE_NONCANONICAL", "Item/Add-on revision payload is not canonical", ProductErrorCategory.DATA_INTEGRITY)
            if item.compatible(game_version):
                candidates.append(item)
        if len(candidates) != 1:
            code = "ERR_LOADOUT_KNOWLEDGE_NOT_FOUND" if not candidates else "ERR_LOADOUT_KNOWLEDGE_AMBIGUOUS"
            raise ProductError(code, "No unique patch-compatible VERIFIED Item/Add-on revision", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        return candidates[0]


@dataclass(frozen=True, slots=True)
class LoadoutVisualObservation:
    entity_id: str | None
    confidence_milli: int
    kind: LoadoutKnowledgeKind
    slot: int | None = None


class LoadoutVisualRecognizer:
    def __init__(self, index: ReferenceSliceIndex, *, kind: LoadoutKnowledgeKind, acceptance_milli: int = 800) -> None:
        self.index = index
        self.kind = kind
        self.acceptance_milli = acceptance_milli

    def recognize(self, image: GrayImage, *, slot: int | None = None) -> LoadoutVisualObservation:
        rows = self.index.match(image, top_k=max(2, len(self.index.references)))
        best_by_label = {}
        for row in rows:
            best_by_label.setdefault(row.label, row)
        unique = sorted(best_by_label.values(), key=lambda item: (-item.confidence_milli, item.distance_bits, item.label, item.source_ref))
        if not unique or unique[0].confidence_milli < self.acceptance_milli:
            return LoadoutVisualObservation(None, unique[0].confidence_milli if unique else 0, self.kind, slot)
        if len(unique) > 1 and unique[0].confidence_milli - unique[1].confidence_milli < 70:
            return LoadoutVisualObservation(None, unique[0].confidence_milli, self.kind, slot)
        prefix = "item_" if self.kind is LoadoutKnowledgeKind.ITEM else "addon_"
        label = unique[0].label
        if not label.startswith(prefix):
            return LoadoutVisualObservation(None, unique[0].confidence_milli, self.kind, slot)
        return LoadoutVisualObservation(label, unique[0].confidence_milli, self.kind, slot)


__all__ = [
    "DbDLoadoutKnowledgeStore", "LoadoutKnowledgeKind", "LoadoutKnowledgeRevision", "LoadoutKnowledgeSource",
    "LoadoutKnowledgeStatus", "LoadoutVisualObservation", "LoadoutVisualRecognizer",
]
