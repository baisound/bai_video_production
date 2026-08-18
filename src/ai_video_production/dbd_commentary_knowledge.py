"""TASK-049 DbD commentary trivia / practical-knowledge store.

Trivia is intentionally separate from canonical game facts such as Perk or
Killer revisions.  Manual entries and mined commentary become CANDIDATE until
Human review promotes them to VERIFIED.  Only VERIFIED, patch-compatible trivia
is eligible for automatic commentary reuse.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable, Mapping, Sequence

from .canonical_game_event import GameEventType
from .dbd_perk_knowledge import DBDPatchVersion, PerkEnvironment
from .game_commentary import CommentaryClaimKind, CommentaryDisposition, CommentaryFact, CommentaryPlan
from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


class TriviaStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class TriviaSourceKind(str, Enum):
    MANUAL = "MANUAL"
    COMMENTARY_EXTRACTED = "COMMENTARY_EXTRACTED"
    TRANSCRIPT_EXTRACTED = "TRANSCRIPT_EXTRACTED"
    OFFICIAL = "OFFICIAL"
    COMMUNITY_REFERENCE = "COMMUNITY_REFERENCE"


@dataclass(frozen=True, slots=True)
class DBDTriviaEntry:
    title: str
    text: str
    source_kind: TriviaSourceKind
    source_ref: str
    status: TriviaStatus = TriviaStatus.CANDIDATE
    category: str = "GENERAL"
    tags: tuple[str, ...] = ()
    event_types: tuple[GameEventType, ...] = ()
    entity_refs: tuple[str, ...] = ()
    environment: PerkEnvironment = PerkEnvironment.LIVE
    game_version_from: str | None = None
    game_version_to: str | None = None
    trivia_id: str = field(default_factory=lambda: generate_id(IdKind.TRIVIA))
    revision: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    verified_at: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.trivia_id, IdKind.TRIVIA)
        if not self.title.strip() or len(self.title) > 300 or not self.text.strip() or len(self.text) > 8000:
            raise ValueError("trivia title/text are invalid")
        if not self.source_ref.strip() or len(self.source_ref) > 2000:
            raise ValueError("source_ref is required")
        if self.revision < 1:
            raise ValueError("revision must be positive")
        if self.tags != tuple(sorted(set(self.tags))):
            raise ValueError("tags must be unique and sorted")
        if self.event_types != tuple(sorted(set(self.event_types), key=lambda x: x.value)):
            raise ValueError("event_types must be unique and sorted")
        if self.entity_refs != tuple(sorted(set(self.entity_refs))):
            raise ValueError("entity_refs must be unique and sorted")
        if self.game_version_from is not None:
            DBDPatchVersion.parse(self.game_version_from)
        if self.game_version_to is not None:
            DBDPatchVersion.parse(self.game_version_to)

    def compatible(self, game_version: str, environment: PerkEnvironment) -> bool:
        if self.environment is not environment:
            return False
        version = DBDPatchVersion.parse(game_version)
        if self.game_version_from and version < DBDPatchVersion.parse(self.game_version_from):
            return False
        if self.game_version_to and version > DBDPatchVersion.parse(self.game_version_to):
            return False
        return True

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": "1.0.0", "trivia_id": self.trivia_id, "revision": self.revision,
            "title": self.title, "text": self.text, "source_kind": self.source_kind.value,
            "source_ref": self.source_ref, "status": self.status.value, "category": self.category,
            "tags": list(self.tags), "event_types": [x.value for x in self.event_types],
            "entity_refs": list(self.entity_refs), "environment": self.environment.value,
            "game_version_from": self.game_version_from, "game_version_to": self.game_version_to,
            "created_at": self.created_at, "verified_at": self.verified_at,
        }
        return {**body, "trivia_sha256": sha256_bytes(canonical_json_bytes(body))}


class DbDTriviaStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS trivia_revision(
              trivia_id TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL,
              payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
              PRIMARY KEY(trivia_id, revision)
            );
            CREATE TABLE IF NOT EXISTS trivia_usage(
              trivia_id TEXT NOT NULL, event_id TEXT NOT NULL, commentary_candidate_id TEXT,
              used_at TEXT NOT NULL, PRIMARY KEY(trivia_id,event_id,used_at)
            );
            """)

    def put(self, entry: DBDTriviaEntry) -> DBDTriviaEntry:
        payload = entry.to_dict(); digest = str(payload["trivia_sha256"])
        with self._connect() as conn:
            current = conn.execute("SELECT MAX(revision) FROM trivia_revision WHERE trivia_id=?", (entry.trivia_id,)).fetchone()[0]
            if current is not None and entry.revision <= current:
                raise ValueError("trivia revision must be append-only")
            conn.execute("INSERT INTO trivia_revision(trivia_id,revision,status,payload_json,payload_sha256) VALUES(?,?,?,?,?)",
                         (entry.trivia_id, entry.revision, entry.status.value, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), digest))
        return entry

    def create_manual(self, *, title: str, text: str, source_ref: str = "manual://owner", category: str = "GENERAL",
                      tags: Iterable[str] = (), event_types: Iterable[GameEventType] = (), entity_refs: Iterable[str] = (),
                      environment: PerkEnvironment = PerkEnvironment.LIVE, game_version_from: str | None = None,
                      game_version_to: str | None = None, verify: bool = False) -> DBDTriviaEntry:
        entry = DBDTriviaEntry(title=title.strip(), text=text.strip(), source_kind=TriviaSourceKind.MANUAL, source_ref=source_ref,
                               status=TriviaStatus.VERIFIED if verify else TriviaStatus.CANDIDATE, category=category.strip().upper() or "GENERAL",
                               tags=tuple(sorted(set(x.strip().upper() for x in tags if x.strip()))),
                               event_types=tuple(sorted(set(event_types), key=lambda x: x.value)), entity_refs=tuple(sorted(set(entity_refs))),
                               environment=environment, game_version_from=game_version_from, game_version_to=game_version_to,
                               verified_at=utc_now_iso() if verify else None)
        return self.put(entry)

    def latest(self, trivia_id: str) -> DBDTriviaEntry:
        validate_id(trivia_id, IdKind.TRIVIA)
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json,payload_sha256 FROM trivia_revision WHERE trivia_id=? ORDER BY revision DESC LIMIT 1", (trivia_id,)).fetchone()
        if row is None:
            raise KeyError(trivia_id)
        return self._decode(row[0], row[1])

    def verify(self, trivia_id: str) -> DBDTriviaEntry:
        current = self.latest(trivia_id)
        revised = replace(current, revision=current.revision + 1, status=TriviaStatus.VERIFIED, verified_at=utc_now_iso())
        return self.put(revised)

    def reject(self, trivia_id: str) -> DBDTriviaEntry:
        current = self.latest(trivia_id)
        return self.put(replace(current, revision=current.revision + 1, status=TriviaStatus.REJECTED))

    def list_latest(self, *, status: TriviaStatus | None = None) -> tuple[DBDTriviaEntry, ...]:
        with self._connect() as conn:
            rows = conn.execute("""SELECT r.payload_json,r.payload_sha256 FROM trivia_revision r
                JOIN (SELECT trivia_id,MAX(revision) rev FROM trivia_revision GROUP BY trivia_id) x
                ON r.trivia_id=x.trivia_id AND r.revision=x.rev ORDER BY r.trivia_id""").fetchall()
        values = tuple(self._decode(row[0], row[1]) for row in rows)
        return tuple(x for x in values if status is None or x.status is status)

    def query_verified(self, *, game_version: str, environment: PerkEnvironment, event_type: GameEventType | None = None,
                       entity_refs: Iterable[str] = (), tags: Iterable[str] = (), limit: int = 5) -> tuple[DBDTriviaEntry, ...]:
        wanted_entities, wanted_tags = set(entity_refs), {x.upper() for x in tags}
        rows: list[tuple[int, DBDTriviaEntry]] = []
        for item in self.list_latest(status=TriviaStatus.VERIFIED):
            if not item.compatible(game_version, environment):
                continue
            score = 0
            if event_type is not None and event_type in item.event_types:
                score += 50
            score += 30 * len(wanted_entities & set(item.entity_refs))
            score += 10 * len(wanted_tags & set(item.tags))
            if not item.event_types and not item.entity_refs and not item.tags:
                score += 1
            if score:
                rows.append((score, item))
        rows.sort(key=lambda x: (-x[0], x[1].trivia_id))
        return tuple(item for _, item in rows[:limit])

    def record_usage(self, trivia_id: str, *, event_id: str, commentary_candidate_id: str | None = None) -> None:
        validate_id(trivia_id, IdKind.TRIVIA)
        with self._connect() as conn:
            conn.execute("INSERT INTO trivia_usage(trivia_id,event_id,commentary_candidate_id,used_at) VALUES(?,?,?,?)",
                         (trivia_id, event_id, commentary_candidate_id, utc_now_iso()))

    def list_usage(self, trivia_id: str | None = None) -> tuple[dict[str, str | None], ...]:
        if trivia_id is not None:
            validate_id(trivia_id, IdKind.TRIVIA)
        with self._connect() as conn:
            if trivia_id is None:
                rows = conn.execute(
                    "SELECT trivia_id,event_id,commentary_candidate_id,used_at FROM trivia_usage ORDER BY used_at,trivia_id,event_id"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT trivia_id,event_id,commentary_candidate_id,used_at FROM trivia_usage WHERE trivia_id=? ORDER BY used_at,event_id",
                    (trivia_id,),
                ).fetchall()
        return tuple({
            "trivia_id": row["trivia_id"],
            "event_id": row["event_id"],
            "commentary_candidate_id": row["commentary_candidate_id"],
            "used_at": row["used_at"],
        } for row in rows)

    @staticmethod
    def _decode(payload_json: str, expected_digest: str) -> DBDTriviaEntry:
        payload = json.loads(payload_json)
        if payload.get("trivia_sha256") != expected_digest:
            raise ValueError("trivia checksum mismatch")
        body = dict(payload); body.pop("trivia_sha256", None); body.pop("schema_version", None)
        body["source_kind"] = TriviaSourceKind(body["source_kind"]); body["status"] = TriviaStatus(body["status"])
        body["environment"] = PerkEnvironment(body["environment"])
        body["tags"] = tuple(body["tags"]); body["entity_refs"] = tuple(body["entity_refs"])
        body["event_types"] = tuple(GameEventType(x) for x in body["event_types"])
        entry = DBDTriviaEntry(**body)
        if entry.to_dict() != payload:
            raise ValueError("trivia payload is not canonical")
        return entry


class TriviaCandidateMiner:
    """Conservative heuristic miner; all mined rows remain CANDIDATE.

    Strong discourse cues are sufficient by themselves.  Domain words are
    weaker signals and therefore need either a mechanic-style connective or
    more than one DbD-specific term.  This keeps ordinary play-by-play from
    flooding the review queue while still surfacing useful explanatory lines.
    """
    STRONG_CUES = ("実は", "ちなみに", "豆知識", "覚えておく", "知っておく", "意外と", "仕様", "ポイントは", "補足すると")
    DOMAIN_TERMS = ("パーク", "キラー", "発電機", "チェイス", "フック", "窓", "板", "トーテム", "オファリング", "アドオン")
    MECHANIC_CUES = ("すると", "場合", "条件", "秒", "%", "効果", "発動", "仕様", "できる", "ならない", "扱い")

    @classmethod
    def _interesting(cls, sentence: str) -> bool:
        if any(cue in sentence for cue in cls.STRONG_CUES):
            return True
        domain_count = sum(1 for term in cls.DOMAIN_TERMS if term in sentence)
        return domain_count >= 2 or (domain_count >= 1 and any(cue in sentence for cue in cls.MECHANIC_CUES))

    def mine(self, text: str) -> tuple[str, ...]:
        parts = [x.strip() for x in re.split(r"(?<=[。！？!?])\s*|\n+", text) if x.strip()]
        return tuple(x for x in parts if 8 <= len(x) <= 500 and self._interesting(x))

    def capture(self, store: DbDTriviaStore, *, text: str, source_ref: str, event_type: GameEventType | None = None,
                entity_refs: Sequence[str] = (), source_kind: TriviaSourceKind = TriviaSourceKind.COMMENTARY_EXTRACTED) -> tuple[DBDTriviaEntry, ...]:
        rows = []
        for sentence in self.mine(text):
            if source_kind not in {TriviaSourceKind.COMMENTARY_EXTRACTED, TriviaSourceKind.TRANSCRIPT_EXTRACTED}:
                raise ValueError("mined trivia source_kind must be commentary/transcript extracted")
            entry = DBDTriviaEntry(title=sentence[:60], text=sentence, source_kind=source_kind,
                                   source_ref=source_ref, status=TriviaStatus.CANDIDATE,
                                   event_types=() if event_type is None else (event_type,), entity_refs=tuple(sorted(set(entity_refs))))
            store.put(entry); rows.append(entry)
        return tuple(rows)

    def capture_transcript_manifest(self, store: DbDTriviaStore, manifest: object) -> tuple[DBDTriviaEntry, ...]:
        """Mine ASR transcript segments without coupling the Store to ASR.

        ``manifest`` must expose ``source_asset_id`` and ``segments`` whose
        items expose ``segment_id`` and ``text``.  Each admitted sentence is
        persisted as TRANSCRIPT_EXTRACTED/CANDIDATE with a segment-level source
        reference so Human review can trace the original utterance.
        """
        source_asset_id = getattr(manifest, "source_asset_id", None)
        segments = getattr(manifest, "segments", None)
        if not isinstance(source_asset_id, str) or segments is None:
            raise TypeError("manifest must expose source_asset_id and segments")
        rows: list[DBDTriviaEntry] = []
        for segment in segments:
            segment_id = getattr(segment, "segment_id", None)
            text = getattr(segment, "text", None)
            if not isinstance(segment_id, str) or not isinstance(text, str):
                raise TypeError("transcript segments must expose segment_id and text")
            rows.extend(self.capture(
                store,
                text=text,
                source_ref=f"transcript://{source_asset_id}/{segment_id}",
                source_kind=TriviaSourceKind.TRANSCRIPT_EXTRACTED,
            ))
        return tuple(rows)


class TriviaCommentaryAugmentor:
    def augment(self, plan: CommentaryPlan, trivia: Sequence[DBDTriviaEntry], *, maximum: int = 2) -> CommentaryPlan:
        if plan.disposition is not CommentaryDisposition.PROPOSE or maximum < 1:
            return plan
        admitted = [x for x in trivia if x.status is TriviaStatus.VERIFIED][:maximum]
        extra = [CommentaryFact(CommentaryClaimKind.TRIVIA, f"trivia.{x.trivia_id}", x.text) for x in admitted]
        facts = tuple(sorted(set(plan.facts + tuple(extra)), key=lambda x: (x.kind.value, x.key, x.value)))
        hashes = tuple(sorted(set(plan.knowledge_ref_sha256s + tuple(x.to_dict()["trivia_sha256"] for x in admitted))))
        return replace(plan, facts=facts, knowledge_ref_sha256s=hashes)


__all__ = ["DBDTriviaEntry", "DbDTriviaStore", "TriviaCandidateMiner", "TriviaCommentaryAugmentor", "TriviaSourceKind", "TriviaStatus"]
