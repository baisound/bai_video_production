"""TASK-049 R2 project-local Game Intelligence SQLite store.

The store is canonical only for game-analysis records.  It does not replace the
BVP Asset Registry, Product Project store, Production Timeline, or any external
application authority.
"""

from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator, Mapping

from .canonical_game_event import (
    CanonicalGameEvent,
    GameEventReview,
    GameMatch,
    parse_canonical_game_event,
    parse_game_event_review,
    parse_game_match,
)
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence, parse_game_evidence
from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, sha256_json, utc_now_iso


_STORE_FORMAT = "task049.game-intelligence.sqlite"
_STORE_SCHEMA_VERSION = 1
_STORE_SCHEMA_SEMVER = "1.0.0"
_STAGE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_REQUIRED_TABLES = {
    "store_metadata",
    "match_revisions",
    "game_evidence",
    "event_revisions",
    "event_reviews",
    "checkpoints",
}


def _integrity(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.DATA_INTEGRITY, False, details=details)


def _state_error(code: str, message: str, **details: Any) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.STATE, False, details=details)


def _canonical_text(payload: Mapping[str, Any]) -> str:
    return canonical_json_bytes(dict(payload)).decode("utf-8")


def _json_object(value: Mapping[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    result = dict(value)
    try:
        canonical_json_bytes(result)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be canonical-JSON serializable") from exc
    return result


@dataclass(frozen=True, slots=True)
class GameIntelligenceCheckpoint:
    match_id: str
    checkpoint_revision: int
    stage: str
    match_sha256: str
    evidence_head_sha256: str
    event_head_sha256: str
    review_head_sha256: str
    state: Mapping[str, Any]
    store_schema_version: str = _STORE_SCHEMA_SEMVER
    checkpoint_id: str = field(default_factory=lambda: generate_id(IdKind.CHECKPOINT))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.checkpoint_id, IdKind.CHECKPOINT)
        if isinstance(self.checkpoint_revision, bool) or not isinstance(self.checkpoint_revision, int) or self.checkpoint_revision < 1:
            raise ValueError("checkpoint_revision must be a positive integer")
        if not isinstance(self.stage, str) or not _STAGE_RE.fullmatch(self.stage):
            raise ValueError("stage must be an uppercase stable stage identifier")
        if self.store_schema_version != _STORE_SCHEMA_SEMVER:
            raise ValueError("unsupported checkpoint store_schema_version")
        for name in (
            "match_sha256",
            "evidence_head_sha256",
            "event_head_sha256",
            "review_head_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                raise ValueError(f"{name} must be a canonical sha256")
        object.__setattr__(self, "state", _json_object(self.state, field_name="state"))
        if not isinstance(self.created_at, str) or not self.created_at:
            raise ValueError("created_at must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "checkpoint_id": self.checkpoint_id,
            "match_id": self.match_id,
            "checkpoint_revision": self.checkpoint_revision,
            "stage": self.stage,
            "store_schema_version": self.store_schema_version,
            "match_sha256": self.match_sha256,
            "evidence_head_sha256": self.evidence_head_sha256,
            "event_head_sha256": self.event_head_sha256,
            "review_head_sha256": self.review_head_sha256,
            "state": dict(self.state),
            "created_at": self.created_at,
        }
        return {
            **body,
            "checkpoint_sha256": sha256_bytes(canonical_json_bytes(body)),
        }


def parse_game_intelligence_checkpoint(payload: Any) -> GameIntelligenceCheckpoint:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid game intelligence checkpoint payload")
    try:
        item = GameIntelligenceCheckpoint(
            checkpoint_id=payload["checkpoint_id"],
            match_id=payload["match_id"],
            checkpoint_revision=payload["checkpoint_revision"],
            stage=payload["stage"],
            store_schema_version=payload["store_schema_version"],
            match_sha256=payload["match_sha256"],
            evidence_head_sha256=payload["evidence_head_sha256"],
            event_head_sha256=payload["event_head_sha256"],
            review_head_sha256=payload["review_head_sha256"],
            state=payload["state"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid game intelligence checkpoint payload") from exc
    if item.to_dict() != payload:
        raise ValueError("game intelligence checkpoint payload/hash is not canonical")
    return item


class GameIntelligenceStore:
    """Append-only SQLite persistence for TASK-049 game-analysis state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ProductError(
                "ERR_GAME_STORE_PATH_SYMLINK",
                "Game Intelligence store path must not be a symlink",
                ProductErrorCategory.SECURITY,
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            return conn
        except sqlite3.DatabaseError as exc:
            raise _integrity(
                "ERR_GAME_STORE_OPEN",
                "Game Intelligence store could not be opened as SQLite",
            ) from exc

    @staticmethod
    @contextmanager
    def _transaction(conn: sqlite3.Connection) -> Iterator[None]:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")

    def _initialize(self) -> None:
        try:
            with closing(self._connect()) as conn:
                check = conn.execute("PRAGMA quick_check").fetchone()
                if not check or check[0] != "ok":
                    raise _integrity(
                        "ERR_GAME_STORE_CORRUPT",
                        "Game Intelligence store failed SQLite quick_check",
                        result=check[0] if check else None,
                    )
                version = int(conn.execute("PRAGMA user_version").fetchone()[0])
                user_tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                if version > _STORE_SCHEMA_VERSION:
                    raise ProductError(
                        "ERR_GAME_STORE_VERSION_UNSUPPORTED",
                        "Game Intelligence store schema is newer than this reader",
                        ProductErrorCategory.NOT_SUPPORTED,
                        details={"store_version": version, "reader_version": _STORE_SCHEMA_VERSION},
                    )
                if version == 0:
                    if user_tables:
                        raise _integrity(
                            "ERR_GAME_STORE_VERSION_UNKNOWN",
                            "Existing SQLite database has tables but no recognized Game Intelligence version",
                            tables=sorted(user_tables),
                        )
                    self._create_v1(conn)
                    conn.execute(f"PRAGMA user_version={_STORE_SCHEMA_VERSION}")
                elif version == 1:
                    missing = _REQUIRED_TABLES - user_tables
                    if missing:
                        raise _integrity(
                            "ERR_GAME_STORE_SCHEMA_INCOMPLETE",
                            "Game Intelligence store is missing required tables",
                            missing=sorted(missing),
                        )
                    meta = dict(conn.execute("SELECT key, value FROM store_metadata").fetchall())
                    if meta.get("store_format") != _STORE_FORMAT or meta.get("schema_semver") != _STORE_SCHEMA_SEMVER:
                        raise _integrity(
                            "ERR_GAME_STORE_METADATA_INVALID",
                            "Game Intelligence store metadata does not match the supported format",
                        )
        except ProductError:
            raise
        except sqlite3.DatabaseError as exc:
            raise _integrity(
                "ERR_GAME_STORE_CORRUPT",
                "Game Intelligence store is corrupt or unreadable",
            ) from exc

    @staticmethod
    def _create_v1(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE store_metadata (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE match_revisions (
              match_id TEXT NOT NULL,
              analysis_revision INTEGER NOT NULL,
              production_job_id TEXT NOT NULL,
              source_asset_id TEXT NOT NULL,
              match_sha256 TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(match_id, analysis_revision)
            );
            CREATE TABLE game_evidence (
              game_evidence_id TEXT PRIMARY KEY,
              match_id TEXT NOT NULL,
              source_asset_id TEXT NOT NULL,
              game_evidence_sha256 TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX game_evidence_match_idx ON game_evidence(match_id, game_evidence_id);
            CREATE TABLE event_revisions (
              event_id TEXT NOT NULL,
              revision INTEGER NOT NULL,
              match_id TEXT NOT NULL,
              start_frame INTEGER NOT NULL,
              end_frame_exclusive INTEGER NOT NULL,
              event_sha256 TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(event_id, revision)
            );
            CREATE INDEX event_revisions_match_idx
              ON event_revisions(match_id, start_frame, end_frame_exclusive, event_id, revision);
            CREATE TABLE event_reviews (
              review_id TEXT PRIMARY KEY,
              event_id TEXT NOT NULL,
              event_revision INTEGER NOT NULL,
              review_sha256 TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX event_reviews_event_idx ON event_reviews(event_id, event_revision, review_id);
            CREATE TABLE checkpoints (
              checkpoint_id TEXT PRIMARY KEY,
              match_id TEXT NOT NULL,
              checkpoint_revision INTEGER NOT NULL,
              stage TEXT NOT NULL,
              checkpoint_sha256 TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(match_id, checkpoint_revision)
            );
            CREATE INDEX checkpoints_match_idx ON checkpoints(match_id, checkpoint_revision);
            """
        )
        conn.executemany(
            "INSERT INTO store_metadata(key, value) VALUES (?, ?)",
            (
                ("store_format", _STORE_FORMAT),
                ("schema_semver", _STORE_SCHEMA_SEMVER),
                ("created_at", utc_now_iso()),
            ),
        )

    @property
    def schema_version(self) -> str:
        return _STORE_SCHEMA_SEMVER

    def _latest_match_row(self, conn: sqlite3.Connection, match_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM match_revisions WHERE match_id=? ORDER BY analysis_revision DESC LIMIT 1",
            (match_id,),
        ).fetchone()

    def list_matches(self) -> tuple[GameMatch, ...]:
        """Return the latest canonical revision for every known match.

        This is a read-only UI/reporting projection.  Each payload is parsed
        through the canonical contract so stored-hash tampering still fails
        closed instead of leaking partially trusted state into the Shell.
        """
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT mr.*
                FROM match_revisions AS mr
                JOIN (
                  SELECT match_id, MAX(analysis_revision) AS latest_revision
                  FROM match_revisions
                  GROUP BY match_id
                ) AS latest
                  ON latest.match_id = mr.match_id
                 AND latest.latest_revision = mr.analysis_revision
                ORDER BY mr.created_at DESC, mr.match_id
                """
            ).fetchall()
        values: list[GameMatch] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            match = parse_game_match(payload)
            if match.to_dict()["match_sha256"] != row["match_sha256"]:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_HASH_MISMATCH",
                    "Stored Match payload hash does not match canonical content",
                    match_id=match.match_id,
                    revision=match.analysis_revision,
                )
            values.append(match)
        return tuple(values)

    def put_match(self, match: GameMatch) -> None:
        if not isinstance(match, GameMatch):
            raise TypeError("match must be a GameMatch")
        payload = match.to_dict()
        with closing(self._connect()) as conn, self._transaction(conn):
            existing = conn.execute(
                "SELECT match_sha256 FROM match_revisions WHERE match_id=? AND analysis_revision=?",
                (match.match_id, match.analysis_revision),
            ).fetchone()
            if existing:
                if existing[0] == payload["match_sha256"]:
                    return
                raise _state_error(
                    "ERR_GAME_STORE_REVISION_CONFLICT",
                    "Match revision already exists with different canonical content",
                    match_id=match.match_id,
                    revision=match.analysis_revision,
                )
            previous = self._latest_match_row(conn, match.match_id)
            if previous is None:
                if match.analysis_revision != 1:
                    raise _state_error(
                        "ERR_GAME_STORE_REVISION_GAP",
                        "First Match revision must be 1",
                    )
            else:
                prior = parse_game_match(json.loads(previous["payload_json"]))
                if match.analysis_revision != prior.analysis_revision + 1:
                    raise _state_error(
                        "ERR_GAME_STORE_REVISION_GAP",
                        "Match revisions must advance exactly once",
                        current=prior.analysis_revision,
                        incoming=match.analysis_revision,
                    )
                if (
                    match.production_job_id != prior.production_job_id
                    or match.source_asset_id != prior.source_asset_id
                    or match.game_profile_id != prior.game_profile_id
                    or match.source_rate != prior.source_rate
                ):
                    raise _state_error(
                        "ERR_GAME_STORE_MATCH_IDENTITY_CONFLICT",
                        "Match identity/source/timebase cannot change across revisions",
                    )
            conn.execute(
                "INSERT INTO match_revisions VALUES (?,?,?,?,?,?,?)",
                (
                    match.match_id,
                    match.analysis_revision,
                    match.production_job_id,
                    match.source_asset_id,
                    payload["match_sha256"],
                    _canonical_text(payload),
                    match.created_at,
                ),
            )

    def get_match(self, match_id: str, *, analysis_revision: int | None = None) -> GameMatch:
        validate_id(match_id, IdKind.GAME_MATCH)
        with closing(self._connect()) as conn:
            if analysis_revision is None:
                row = self._latest_match_row(conn, match_id)
            else:
                row = conn.execute(
                    "SELECT * FROM match_revisions WHERE match_id=? AND analysis_revision=?",
                    (match_id, analysis_revision),
                ).fetchone()
            if row is None:
                raise _state_error("ERR_GAME_MATCH_NOT_FOUND", "Game Match was not found", match_id=match_id)
            try:
                return parse_game_match(json.loads(row["payload_json"]))
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Match payload failed canonical validation",
                    match_id=match_id,
                ) from exc

    def append_evidence(self, evidence: GameEvidence) -> None:
        if not isinstance(evidence, GameEvidence):
            raise TypeError("evidence must be GameEvidence")
        payload = evidence.to_dict()
        with closing(self._connect()) as conn, self._transaction(conn):
            current_match = self._latest_match_row(conn, evidence.match_id)
            if current_match is None:
                raise _state_error("ERR_GAME_MATCH_NOT_FOUND", "Evidence Match was not found")
            game_match = parse_game_match(json.loads(current_match["payload_json"]))
            if (
                evidence.production_job_id != game_match.production_job_id
                or evidence.source_asset_id != game_match.source_asset_id
            ):
                raise _state_error(
                    "ERR_GAME_EVIDENCE_SOURCE_MISMATCH",
                    "Evidence job/source Asset does not match its Match",
                )
            existing = conn.execute(
                "SELECT game_evidence_sha256 FROM game_evidence WHERE game_evidence_id=?",
                (evidence.game_evidence_id,),
            ).fetchone()
            if existing:
                if existing[0] == payload["game_evidence_sha256"]:
                    return
                raise _state_error(
                    "ERR_GAME_EVIDENCE_ID_CONFLICT",
                    "Game Evidence ID already exists with different content",
                )
            conn.execute(
                "INSERT INTO game_evidence VALUES (?,?,?,?,?,?)",
                (
                    evidence.game_evidence_id,
                    evidence.match_id,
                    evidence.source_asset_id,
                    payload["game_evidence_sha256"],
                    _canonical_text(payload),
                    evidence.created_at,
                ),
            )

    def get_evidence(self, game_evidence_id: str) -> GameEvidence:
        validate_id(game_evidence_id, IdKind.GAME_EVIDENCE)
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT payload_json FROM game_evidence WHERE game_evidence_id=?",
                (game_evidence_id,),
            ).fetchone()
            if row is None:
                raise _state_error("ERR_GAME_EVIDENCE_NOT_FOUND", "Game Evidence was not found")
            try:
                return parse_game_evidence(json.loads(row[0]))
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Game Evidence failed canonical validation",
                ) from exc

    def _validate_event_for_insert(self, conn: sqlite3.Connection, event: CanonicalGameEvent) -> None:
        match_row = self._latest_match_row(conn, event.match_id)
        if match_row is None:
            raise _state_error("ERR_GAME_MATCH_NOT_FOUND", "Event Match was not found")
        game_match = parse_game_match(json.loads(match_row["payload_json"]))
        if (
            event.game_version != game_match.game_version
            or event.environment is not game_match.environment
            or event.perspective is not game_match.perspective
        ):
            raise _state_error(
                "ERR_GAME_EVENT_MATCH_CONTEXT_MISMATCH",
                "Event patch/environment/perspective does not match current Match revision",
            )
        placeholders = ",".join("?" for _ in event.evidence_refs)
        rows = conn.execute(
            f"SELECT game_evidence_id, match_id FROM game_evidence WHERE game_evidence_id IN ({placeholders})",
            event.evidence_refs,
        ).fetchall()
        found = {row["game_evidence_id"]: row["match_id"] for row in rows}
        if set(found) != set(event.evidence_refs):
            raise _state_error(
                "ERR_GAME_EVENT_EVIDENCE_MISSING",
                "Event references Evidence that is not present in the store",
            )
        if any(match_id != event.match_id for match_id in found.values()):
            raise _state_error(
                "ERR_GAME_EVENT_EVIDENCE_CROSS_MATCH",
                "Event cannot consume Evidence from another Match",
            )

    def _insert_event_conn(self, conn: sqlite3.Connection, event: CanonicalGameEvent) -> None:
        self._validate_event_for_insert(conn, event)
        payload = event.to_dict()
        existing = conn.execute(
            "SELECT event_sha256 FROM event_revisions WHERE event_id=? AND revision=?",
            (event.event_id, event.revision),
        ).fetchone()
        if existing:
            if existing[0] == payload["event_sha256"]:
                return
            raise _state_error(
                "ERR_GAME_EVENT_REVISION_CONFLICT",
                "Event revision already exists with different canonical content",
            )
        prior = conn.execute(
            "SELECT revision, match_id FROM event_revisions WHERE event_id=? ORDER BY revision DESC LIMIT 1",
            (event.event_id,),
        ).fetchone()
        if prior is None:
            if event.revision != 1:
                raise _state_error("ERR_GAME_EVENT_REVISION_GAP", "First Event revision must be 1")
        else:
            if prior["match_id"] != event.match_id:
                raise _state_error("ERR_GAME_EVENT_IDENTITY_CONFLICT", "Event cannot change Match identity")
            if event.revision != int(prior["revision"]) + 1:
                raise _state_error(
                    "ERR_GAME_EVENT_REVISION_GAP",
                    "Event revisions must advance exactly once",
                    current=int(prior["revision"]),
                    incoming=event.revision,
                )
        conn.execute(
            "INSERT INTO event_revisions VALUES (?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.revision,
                event.match_id,
                event.source_range.start_frame,
                event.source_range.end_frame_exclusive,
                payload["event_sha256"],
                _canonical_text(payload),
                event.created_at,
            ),
        )

    def append_event(self, event: CanonicalGameEvent) -> None:
        if not isinstance(event, CanonicalGameEvent):
            raise TypeError("event must be CanonicalGameEvent")
        with closing(self._connect()) as conn, self._transaction(conn):
            self._insert_event_conn(conn, event)

    def get_event(self, event_id: str, *, revision: int | None = None) -> CanonicalGameEvent:
        validate_id(event_id, IdKind.GAME_EVENT)
        with closing(self._connect()) as conn:
            if revision is None:
                row = conn.execute(
                    "SELECT payload_json FROM event_revisions WHERE event_id=? ORDER BY revision DESC LIMIT 1",
                    (event_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT payload_json FROM event_revisions WHERE event_id=? AND revision=?",
                    (event_id, revision),
                ).fetchone()
            if row is None:
                raise _state_error("ERR_GAME_EVENT_NOT_FOUND", "Canonical Game Event was not found")
            try:
                return parse_canonical_game_event(json.loads(row[0]))
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Canonical Game Event failed canonical validation",
                ) from exc

    def list_events(self, match_id: str, *, latest_only: bool = True) -> tuple[CanonicalGameEvent, ...]:
        validate_id(match_id, IdKind.GAME_MATCH)
        with closing(self._connect()) as conn:
            if latest_only:
                rows = conn.execute(
                    """
                    SELECT e.payload_json
                    FROM event_revisions e
                    JOIN (
                      SELECT event_id, MAX(revision) AS revision
                      FROM event_revisions WHERE match_id=? GROUP BY event_id
                    ) latest ON latest.event_id=e.event_id AND latest.revision=e.revision
                    WHERE e.match_id=?
                    ORDER BY e.start_frame, e.end_frame_exclusive, e.event_id
                    """,
                    (match_id, match_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM event_revisions WHERE match_id=? ORDER BY start_frame, end_frame_exclusive, event_id, revision",
                    (match_id,),
                ).fetchall()
            try:
                return tuple(parse_canonical_game_event(json.loads(row[0])) for row in rows)
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Event list contains invalid canonical content",
                ) from exc

    def _insert_review_conn(self, conn: sqlite3.Connection, review: GameEventReview) -> None:
        event = conn.execute(
            "SELECT 1 FROM event_revisions WHERE event_id=? AND revision=?",
            (review.event_id, review.event_revision),
        ).fetchone()
        if event is None:
            raise _state_error(
                "ERR_GAME_REVIEW_EVENT_NOT_FOUND",
                "Review target Event revision does not exist",
            )
        payload = review.to_dict()
        existing = conn.execute(
            "SELECT review_sha256 FROM event_reviews WHERE review_id=?",
            (review.review_id,),
        ).fetchone()
        if existing:
            if existing[0] == payload["review_sha256"]:
                return
            raise _state_error(
                "ERR_GAME_REVIEW_ID_CONFLICT",
                "Review ID already exists with different canonical content",
            )
        conn.execute(
            "INSERT INTO event_reviews VALUES (?,?,?,?,?,?)",
            (
                review.review_id,
                review.event_id,
                review.event_revision,
                payload["review_sha256"],
                _canonical_text(payload),
                review.created_at,
            ),
        )

    def append_review(self, review: GameEventReview) -> None:
        if not isinstance(review, GameEventReview):
            raise TypeError("review must be GameEventReview")
        with closing(self._connect()) as conn, self._transaction(conn):
            self._insert_review_conn(conn, review)

    def append_event_and_review(self, event: CanonicalGameEvent, review: GameEventReview) -> None:
        """Atomically append an Event revision and the Review that produced it."""
        if review.event_id != event.event_id or review.event_revision != event.revision:
            raise ValueError("review must target the exact Event revision in the atomic bundle")
        with closing(self._connect()) as conn, self._transaction(conn):
            self._insert_event_conn(conn, event)
            self._insert_review_conn(conn, review)

    def list_reviews(self, event_id: str) -> tuple[GameEventReview, ...]:
        validate_id(event_id, IdKind.GAME_EVENT)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT payload_json FROM event_reviews WHERE event_id=? ORDER BY event_revision, created_at, review_id",
                (event_id,),
            ).fetchall()
            try:
                return tuple(parse_game_event_review(json.loads(row[0])) for row in rows)
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Review list contains invalid canonical content",
                ) from exc

    def _head_hashes(self, conn: sqlite3.Connection, match_id: str) -> dict[str, str]:
        match_row = self._latest_match_row(conn, match_id)
        if match_row is None:
            raise _state_error("ERR_GAME_MATCH_NOT_FOUND", "Checkpoint Match was not found")
        evidence_rows = conn.execute(
            "SELECT game_evidence_id, game_evidence_sha256 FROM game_evidence WHERE match_id=? ORDER BY game_evidence_id",
            (match_id,),
        ).fetchall()
        event_rows = conn.execute(
            """
            SELECT e.event_id, e.revision, e.event_sha256
            FROM event_revisions e
            JOIN (
              SELECT event_id, MAX(revision) AS revision
              FROM event_revisions WHERE match_id=? GROUP BY event_id
            ) latest ON latest.event_id=e.event_id AND latest.revision=e.revision
            WHERE e.match_id=? ORDER BY e.event_id
            """,
            (match_id, match_id),
        ).fetchall()
        review_rows = conn.execute(
            """
            SELECT r.review_id, r.review_sha256
            FROM event_reviews r
            JOIN event_revisions e ON e.event_id=r.event_id AND e.revision=r.event_revision
            WHERE e.match_id=? ORDER BY r.review_id
            """,
            (match_id,),
        ).fetchall()
        return {
            "match_sha256": match_row["match_sha256"],
            "evidence_head_sha256": sha256_json([[row[0], row[1]] for row in evidence_rows]),
            "event_head_sha256": sha256_json([[row[0], row[1], row[2]] for row in event_rows]),
            "review_head_sha256": sha256_json([[row[0], row[1]] for row in review_rows]),
        }

    def create_checkpoint(
        self,
        match_id: str,
        *,
        stage: str,
        state: Mapping[str, Any] | None = None,
    ) -> GameIntelligenceCheckpoint:
        validate_id(match_id, IdKind.GAME_MATCH)
        if not isinstance(stage, str) or not _STAGE_RE.fullmatch(stage):
            raise ValueError("stage must be an uppercase stable stage identifier")
        with closing(self._connect()) as conn, self._transaction(conn):
            heads = self._head_hashes(conn, match_id)
            current = conn.execute(
                "SELECT MAX(checkpoint_revision) FROM checkpoints WHERE match_id=?",
                (match_id,),
            ).fetchone()[0]
            checkpoint = GameIntelligenceCheckpoint(
                match_id=match_id,
                checkpoint_revision=(int(current) + 1) if current is not None else 1,
                stage=stage,
                match_sha256=heads["match_sha256"],
                evidence_head_sha256=heads["evidence_head_sha256"],
                event_head_sha256=heads["event_head_sha256"],
                review_head_sha256=heads["review_head_sha256"],
                state={} if state is None else state,
            )
            payload = checkpoint.to_dict()
            conn.execute(
                "INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?)",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.match_id,
                    checkpoint.checkpoint_revision,
                    checkpoint.stage,
                    payload["checkpoint_sha256"],
                    _canonical_text(payload),
                    checkpoint.created_at,
                ),
            )
            return checkpoint

    def latest_checkpoint(self, match_id: str) -> GameIntelligenceCheckpoint:
        validate_id(match_id, IdKind.GAME_MATCH)
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT payload_json FROM checkpoints WHERE match_id=? ORDER BY checkpoint_revision DESC LIMIT 1",
                (match_id,),
            ).fetchone()
            if row is None:
                raise _state_error("ERR_GAME_CHECKPOINT_NOT_FOUND", "Game Intelligence checkpoint was not found")
            try:
                return parse_game_intelligence_checkpoint(json.loads(row[0]))
            except (json.JSONDecodeError, ValueError) as exc:
                raise _integrity(
                    "ERR_GAME_STORE_RECORD_INVALID",
                    "Stored Game Intelligence checkpoint failed canonical validation",
                ) from exc

    def assert_resume_compatible(self, checkpoint: GameIntelligenceCheckpoint) -> None:
        if not isinstance(checkpoint, GameIntelligenceCheckpoint):
            raise TypeError("checkpoint must be GameIntelligenceCheckpoint")
        with closing(self._connect()) as conn:
            current = self._head_hashes(conn, checkpoint.match_id)
        mismatches = {
            key: {"checkpoint": getattr(checkpoint, key), "current": value}
            for key, value in current.items()
            if getattr(checkpoint, key) != value
        }
        if mismatches:
            raise _integrity(
                "ERR_GAME_RESUME_CONTEXT_CHANGED",
                "Game Intelligence state changed after the checkpoint",
                mismatches=mismatches,
            )


__all__ = [
    "GameIntelligenceCheckpoint",
    "GameIntelligenceStore",
    "parse_game_intelligence_checkpoint",
]
