"""TASK-049 R5 Dead by Daylight Perk Knowledge baseline.

This module owns revisioned, source-provenanced Perk facts for Game
Intelligence.  It does not replace BVP Asset truth, CGEL Event Evidence, RAG,
or Production Timeline authority.  LIVE/PTB separation and patch-compatible
VERIFIED lookup fail closed.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field, replace
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from typing import Any, Mapping

from .canonical_game_event import (
    CanonicalGameEvent,
    GameEnvironment,
    GameKnowledgeKind,
    GameKnowledgeRef,
)
from .errors import ProductError, ProductErrorCategory
from .game_event_evidence import GameEvidence
from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256, utc_now_iso


_STORE_FORMAT = "task049.dbd-perk-knowledge.sqlite"
_STORE_USER_VERSION = 1
_PERK_ID_RE = re.compile(r"^perk_[a-z0-9][a-z0-9_]{1,123}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,126}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")
_LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
_PATCH_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")


class PerkRole(str, Enum):
    SURVIVOR = "SURVIVOR"
    KILLER = "KILLER"


class PerkEnvironment(str, Enum):
    LIVE = "LIVE"
    PTB = "PTB"
    ARCHIVE = "ARCHIVE"
    UNKNOWN = "UNKNOWN"


class PerkRevisionStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    PARSED = "PARSED"
    STRUCTURED = "STRUCTURED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class PerkAliasType(str, Enum):
    COMMUNITY = "COMMUNITY"
    ABBREVIATION = "ABBREVIATION"
    OLD_NAME = "OLD_NAME"
    SEARCH_SYNONYM = "SEARCH_SYNONYM"
    ASR_VARIANT = "ASR_VARIANT"
    MANUAL = "MANUAL"


class PerkSourceAuthority(str, Enum):
    GAME_CLIENT = "GAME_CLIENT"
    BHVR_OFFICIAL = "BHVR_OFFICIAL"
    OFFICIAL_CHARACTER_PAGE = "OFFICIAL_CHARACTER_PAGE"
    OFFICIAL_PATCH_NOTE = "OFFICIAL_PATCH_NOTE"
    OFFICIAL_WIKI = "OFFICIAL_WIKI"
    MANUAL_VERIFIED = "MANUAL_VERIFIED"
    COMMUNITY_REFERENCE = "COMMUNITY_REFERENCE"
    UNKNOWN = "UNKNOWN"


class PerkObservationState(str, Enum):
    UNKNOWN = "UNKNOWN"
    CANDIDATE = "CANDIDATE"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, order=True, slots=True)
class DBDPatchVersion:
    major: int
    minor: int
    patch: int
    hotfix: int = 0

    def __post_init__(self) -> None:
        for name in ("major", "minor", "patch", "hotfix"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    @classmethod
    def parse(cls, value: str) -> "DBDPatchVersion":
        if not isinstance(value, str):
            raise ValueError("game version must be a string")
        match = _PATCH_RE.fullmatch(value)
        if match is None:
            raise ValueError("game version must be numeric x.y.z or x.y.z.h")
        parts = [int(group) if group is not None else 0 for group in match.groups()]
        return cls(*parts)

    def __str__(self) -> str:
        if self.hotfix:
            return f"{self.major}.{self.minor}.{self.patch}.{self.hotfix}"
        return f"{self.major}.{self.minor}.{self.patch}"


def normalize_perk_alias(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("alias must be a string")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = " ".join(normalized.split()).strip()
    if not normalized or len(normalized) > 256:
        raise ValueError("alias must normalize to 1..256 characters")
    return normalized


def _require_perk_id(value: str) -> str:
    if not isinstance(value, str) or not _PERK_ID_RE.fullmatch(value):
        raise ValueError("perk_id must be a stable lowercase perk_* identifier")
    return value


def _require_stable_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a bounded stable identifier")
    return value


def _require_locale(value: str) -> str:
    if not isinstance(value, str) or not _LOCALE_RE.fullmatch(value):
        raise ValueError("locale must be a language or language-region tag")
    return value


def _require_text(value: str, *, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be a non-empty string up to {maximum} characters")
    if any(ord(ch) < 32 and ch not in "\n\t\r" for ch in value):
        raise ValueError(f"{field_name} contains invalid control characters")
    return value


def _json_object(value: Mapping[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    result = dict(value)
    try:
        canonical_json_bytes(result)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be canonical-JSON serializable") from exc
    return result


def _knowledge_error(code: str, message: str, *, category: ProductErrorCategory = ProductErrorCategory.VALIDATION, **details: Any) -> ProductError:
    return ProductError(code, message, category, False, details=details)


@dataclass(frozen=True, slots=True)
class PerkIdentity:
    perk_id: str
    slug: str
    role: PerkRole
    owner_character_id: str | None = None
    introduced_version: str | None = None
    retired_version: str | None = None
    active: bool = True
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_perk_id(self.perk_id)
        if not isinstance(self.slug, str) or not _SLUG_RE.fullmatch(self.slug):
            raise ValueError("slug must be a stable lowercase slug")
        if not isinstance(self.role, PerkRole):
            raise ValueError("role must be a PerkRole")
        if self.owner_character_id is not None:
            _require_stable_id(self.owner_character_id, field_name="owner_character_id")
        if self.introduced_version is not None:
            DBDPatchVersion.parse(self.introduced_version)
        if self.retired_version is not None:
            DBDPatchVersion.parse(self.retired_version)
        if not isinstance(self.active, bool):
            raise ValueError("active must be bool")
        _require_text(self.created_at, field_name="created_at", maximum=64)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "perk_id": self.perk_id,
            "slug": self.slug,
            "role": self.role.value,
            "owner_character_id": self.owner_character_id,
            "introduced_version": self.introduced_version,
            "retired_version": self.retired_version,
            "active": self.active,
            "created_at": self.created_at,
        }
        return {**body, "perk_identity_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkLocalization:
    perk_id: str
    locale: str
    name: str
    simple_text: str | None = None
    beginner_text: str | None = None
    short_text: str | None = None

    def __post_init__(self) -> None:
        _require_perk_id(self.perk_id)
        _require_locale(self.locale)
        _require_text(self.name, field_name="name", maximum=256)
        for name in ("simple_text", "beginner_text", "short_text"):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, field_name=name, maximum=4000)

    @property
    def normalized_name(self) -> str:
        return normalize_perk_alias(self.name)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "perk_id": self.perk_id,
            "locale": self.locale,
            "name": self.name,
            "simple_text": self.simple_text,
            "beginner_text": self.beginner_text,
            "short_text": self.short_text,
        }
        return {**body, "perk_localization_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkAlias:
    alias_id: str
    perk_id: str
    locale: str
    alias: str
    alias_type: PerkAliasType
    verified: bool = False

    def __post_init__(self) -> None:
        _require_stable_id(self.alias_id, field_name="alias_id")
        _require_perk_id(self.perk_id)
        _require_locale(self.locale)
        normalize_perk_alias(self.alias)
        if not isinstance(self.alias_type, PerkAliasType):
            raise ValueError("alias_type must be a PerkAliasType")
        if not isinstance(self.verified, bool):
            raise ValueError("verified must be bool")

    @property
    def normalized_alias(self) -> str:
        return normalize_perk_alias(self.alias)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "alias_id": self.alias_id,
            "perk_id": self.perk_id,
            "locale": self.locale,
            "alias": self.alias,
            "alias_type": self.alias_type.value,
            "verified": self.verified,
        }
        return {**body, "perk_alias_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkKnowledgeSource:
    source_id: str
    source_type: str
    authority: PerkSourceAuthority
    retrieved_at: str
    content_sha256: str
    environment: PerkEnvironment | None = None
    uri: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        _require_stable_id(self.source_id, field_name="source_id")
        _require_stable_id(self.source_type, field_name="source_type")
        if not isinstance(self.authority, PerkSourceAuthority):
            raise ValueError("authority must be a PerkSourceAuthority")
        if self.environment is not None and not isinstance(self.environment, PerkEnvironment):
            raise ValueError("environment must be a PerkEnvironment or None")
        if self.uri is not None:
            _require_text(self.uri, field_name="uri", maximum=1024)
        _require_text(self.retrieved_at, field_name="retrieved_at", maximum=64)
        validate_sha256(self.content_sha256, field_name="content_sha256")
        if self.locale is not None:
            _require_locale(self.locale)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "source_id": self.source_id,
            "source_type": self.source_type,
            "authority": self.authority.value,
            "environment": None if self.environment is None else self.environment.value,
            "uri": self.uri,
            "retrieved_at": self.retrieved_at,
            "locale": self.locale,
            "content_sha256": self.content_sha256,
        }
        return {**body, "perk_source_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkRevision:
    revision_id: str
    perk_id: str
    game_version_from: str
    environment: PerkEnvironment
    status: PerkRevisionStatus
    source_ids: tuple[str, ...]
    official_effect_ja: str | None = None
    official_effect_en: str | None = None
    structured_effect: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    game_version_to_exclusive: str | None = None
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_stable_id(self.revision_id, field_name="revision_id")
        _require_perk_id(self.perk_id)
        DBDPatchVersion.parse(self.game_version_from)
        if self.game_version_to_exclusive is not None:
            if DBDPatchVersion.parse(self.game_version_to_exclusive) <= DBDPatchVersion.parse(self.game_version_from):
                raise ValueError("game_version_to_exclusive must be later than game_version_from")
        if not isinstance(self.environment, PerkEnvironment):
            raise ValueError("environment must be a PerkEnvironment")
        if not isinstance(self.status, PerkRevisionStatus):
            raise ValueError("status must be a PerkRevisionStatus")
        if not isinstance(self.source_ids, tuple) or not self.source_ids:
            raise ValueError("source_ids must be a non-empty tuple")
        for source_id in self.source_ids:
            _require_stable_id(source_id, field_name="source_id")
        if self.source_ids != tuple(sorted(set(self.source_ids))):
            raise ValueError("source_ids must be unique and canonically sorted")
        for field_name in ("official_effect_ja", "official_effect_en"):
            value = getattr(self, field_name)
            if value is not None:
                _require_text(value, field_name=field_name, maximum=12000)
        object.__setattr__(self, "structured_effect", _json_object(self.structured_effect, field_name="structured_effect"))
        if not isinstance(self.tags, tuple) or any(not isinstance(tag, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", tag) for tag in self.tags):
            raise ValueError("tags must be uppercase stable taxonomy strings")
        if self.tags != tuple(sorted(set(self.tags))):
            raise ValueError("tags must be unique and canonically sorted")
        if self.status is PerkRevisionStatus.VERIFIED and not (self.official_effect_ja or self.official_effect_en):
            raise ValueError("VERIFIED revision requires an official effect text")
        _require_text(self.created_at, field_name="created_at", maximum=64)

    def is_compatible(self, game_version: str) -> bool:
        target = DBDPatchVersion.parse(game_version)
        if target < DBDPatchVersion.parse(self.game_version_from):
            return False
        if self.game_version_to_exclusive is not None and target >= DBDPatchVersion.parse(self.game_version_to_exclusive):
            return False
        return True

    def fact_payload(self) -> dict[str, Any]:
        return {
            "official_effect_ja": self.official_effect_ja,
            "official_effect_en": self.official_effect_en,
            "structured_effect": dict(self.structured_effect),
            "tags": list(self.tags),
        }

    @property
    def content_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.fact_payload()))

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "revision_id": self.revision_id,
            "perk_id": self.perk_id,
            "game_version_from": self.game_version_from,
            "game_version_to_exclusive": self.game_version_to_exclusive,
            "environment": self.environment.value,
            "status": self.status.value,
            "source_ids": list(self.source_ids),
            "official_effect_ja": self.official_effect_ja,
            "official_effect_en": self.official_effect_en,
            "structured_effect": dict(self.structured_effect),
            "tags": list(self.tags),
            "content_sha256": self.content_sha256,
            "created_at": self.created_at,
        }
        return {**body, "perk_revision_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkObservation:
    match_id: str
    slot: int
    evidence_ref: str
    confidence_milli: int
    state: PerkObservationState
    perk_id: str | None = None
    resolved_revision_id: str | None = None
    observation_id: str = field(default_factory=lambda: generate_id(IdKind.CANDIDATE))

    def __post_init__(self) -> None:
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.evidence_ref, IdKind.GAME_EVIDENCE)
        validate_id(self.observation_id, IdKind.CANDIDATE)
        if isinstance(self.slot, bool) or not isinstance(self.slot, int) or not 1 <= self.slot <= 4:
            raise ValueError("slot must be 1..4")
        if isinstance(self.confidence_milli, bool) or not isinstance(self.confidence_milli, int) or not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be an integer in 0..1000")
        if not isinstance(self.state, PerkObservationState):
            raise ValueError("state must be a PerkObservationState")
        if self.perk_id is not None:
            _require_perk_id(self.perk_id)
        if self.resolved_revision_id is not None:
            _require_stable_id(self.resolved_revision_id, field_name="resolved_revision_id")
        if self.state is PerkObservationState.UNKNOWN and (self.perk_id is not None or self.resolved_revision_id is not None):
            raise ValueError("UNKNOWN observation cannot claim perk/revision identity")
        if self.state is PerkObservationState.CANDIDATE and (self.perk_id is None or self.resolved_revision_id is not None):
            raise ValueError("CANDIDATE observation requires perk_id and no resolved revision")
        if self.state is PerkObservationState.RESOLVED and (self.perk_id is None or self.resolved_revision_id is None):
            raise ValueError("RESOLVED observation requires perk_id and revision")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "observation_id": self.observation_id,
            "match_id": self.match_id,
            "slot": self.slot,
            "evidence_ref": self.evidence_ref,
            "confidence_milli": self.confidence_milli,
            "state": self.state.value,
            "perk_id": self.perk_id,
            "resolved_revision_id": self.resolved_revision_id,
        }
        return {**body, "perk_observation_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class PerkLookupResult:
    identity: PerkIdentity
    revision: PerkRevision
    localizations: tuple[PerkLocalization, ...]

    def to_knowledge_ref(self) -> GameKnowledgeRef:
        if self.revision.environment not in {PerkEnvironment.LIVE, PerkEnvironment.PTB}:
            raise _knowledge_error(
                "ERR_PERK_ENVIRONMENT_NOT_BINDABLE",
                "Only LIVE/PTB Perk revisions may bind automatically to a live analysis Event",
            )
        return GameKnowledgeRef(
            knowledge_kind=GameKnowledgeKind.PERK,
            entity_id=self.identity.perk_id,
            revision_id=self.revision.revision_id,
            environment=GameEnvironment(self.revision.environment.value),
            game_version_from=self.revision.game_version_from,
            game_version_to=self.revision.game_version_to_exclusive,
            source_provenance_ref=f"perk-revision://{self.revision.revision_id}",
        )


class DbDPerkKnowledgeStore:
    """Revisioned canonical fact store for TASK-049 DbD Perk knowledge."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ProductError("ERR_PERK_STORE_PATH_SYMLINK", "Perk Knowledge store path must not be a symlink", ProductErrorCategory.SECURITY)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        try:
            with closing(self._connect()) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if version > _STORE_USER_VERSION:
                    raise _knowledge_error("ERR_PERK_STORE_NEWER_VERSION", "Perk Knowledge store uses a newer schema version", category=ProductErrorCategory.DATA_INTEGRITY)
                if version == 0 and tables:
                    raise _knowledge_error("ERR_PERK_STORE_FOREIGN_SCHEMA", "Existing unversioned SQLite file is not an admitted Perk Knowledge store", category=ProductErrorCategory.DATA_INTEGRITY)
                if version == 0:
                    connection.executescript(
                        """
                        CREATE TABLE store_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                        CREATE TABLE perk_identities(perk_id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL);
                        CREATE TABLE perk_sources(source_id TEXT PRIMARY KEY, environment TEXT, authority TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL);
                        CREATE TABLE perk_revisions(revision_id TEXT PRIMARY KEY, perk_id TEXT NOT NULL, environment TEXT NOT NULL, status TEXT NOT NULL, version_from TEXT NOT NULL, version_to_exclusive TEXT, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, FOREIGN KEY(perk_id) REFERENCES perk_identities(perk_id));
                        CREATE INDEX perk_revision_lookup ON perk_revisions(perk_id, environment, status);
                        CREATE TABLE perk_localizations(perk_id TEXT NOT NULL, locale TEXT NOT NULL, normalized_name TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, PRIMARY KEY(perk_id, locale), FOREIGN KEY(perk_id) REFERENCES perk_identities(perk_id));
                        CREATE INDEX perk_localization_name ON perk_localizations(normalized_name, locale);
                        CREATE TABLE perk_aliases(alias_id TEXT PRIMARY KEY, perk_id TEXT NOT NULL, locale TEXT NOT NULL, normalized_alias TEXT NOT NULL, verified INTEGER NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, FOREIGN KEY(perk_id) REFERENCES perk_identities(perk_id));
                        CREATE INDEX perk_alias_lookup ON perk_aliases(normalized_alias, locale, verified);
                        """
                    )
                    connection.execute("INSERT INTO store_metadata(key,value) VALUES('store_format',?)", (_STORE_FORMAT,))
                    connection.execute("PRAGMA user_version = 1")
                    connection.commit()
                else:
                    metadata = dict(connection.execute("SELECT key,value FROM store_metadata"))
                    if metadata.get("store_format") != _STORE_FORMAT:
                        raise _knowledge_error("ERR_PERK_STORE_FORMAT", "Perk Knowledge store format is not recognized", category=ProductErrorCategory.DATA_INTEGRITY)
                    required = {"store_metadata", "perk_identities", "perk_sources", "perk_revisions", "perk_localizations", "perk_aliases"}
                    if not required.issubset(tables):
                        raise _knowledge_error("ERR_PERK_STORE_SCHEMA_INCOMPLETE", "Perk Knowledge store is missing required tables", category=ProductErrorCategory.DATA_INTEGRITY)
        except sqlite3.DatabaseError as exc:
            raise _knowledge_error("ERR_PERK_STORE_CORRUPT", "Perk Knowledge SQLite file is corrupt or unreadable", category=ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def _payload_text(payload: Mapping[str, Any]) -> str:
        return canonical_json_bytes(dict(payload)).decode("utf-8")

    @staticmethod
    def _assert_idempotent(row: sqlite3.Row | None, payload: Mapping[str, Any], *, kind: str) -> bool:
        if row is None:
            return False
        if row["payload_json"] != DbDPerkKnowledgeStore._payload_text(payload):
            raise _knowledge_error(f"ERR_PERK_{kind}_CONFLICT", f"Existing {kind.lower()} identifier has different canonical content", category=ProductErrorCategory.DATA_INTEGRITY)
        return True

    def put_identity(self, item: PerkIdentity) -> None:
        if not isinstance(item, PerkIdentity):
            raise ValueError("item must be PerkIdentity")
        payload = item.to_dict()
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT payload_json FROM perk_identities WHERE perk_id=?", (item.perk_id,)).fetchone()
            if self._assert_idempotent(row, payload, kind="IDENTITY"):
                return
            try:
                connection.execute("INSERT INTO perk_identities(perk_id,slug,payload_json,payload_sha256) VALUES(?,?,?,?)", (item.perk_id, item.slug, self._payload_text(payload), payload["perk_identity_sha256"]))
                connection.commit()
            except sqlite3.IntegrityError as exc:
                raise _knowledge_error("ERR_PERK_IDENTITY_UNIQUE", "Perk identity/slug conflicts with existing canonical identity", category=ProductErrorCategory.DATA_INTEGRITY) from exc

    def put_source(self, item: PerkKnowledgeSource) -> None:
        if not isinstance(item, PerkKnowledgeSource):
            raise ValueError("item must be PerkKnowledgeSource")
        payload = item.to_dict()
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT payload_json FROM perk_sources WHERE source_id=?", (item.source_id,)).fetchone()
            if self._assert_idempotent(row, payload, kind="SOURCE"):
                return
            connection.execute("INSERT INTO perk_sources(source_id,environment,authority,payload_json,payload_sha256) VALUES(?,?,?,?,?)", (item.source_id, None if item.environment is None else item.environment.value, item.authority.value, self._payload_text(payload), payload["perk_source_sha256"]))
            connection.commit()

    def put_localization(self, item: PerkLocalization) -> None:
        if not isinstance(item, PerkLocalization):
            raise ValueError("item must be PerkLocalization")
        payload = item.to_dict()
        with closing(self._connect()) as connection:
            if connection.execute("SELECT 1 FROM perk_identities WHERE perk_id=?", (item.perk_id,)).fetchone() is None:
                raise _knowledge_error("ERR_PERK_IDENTITY_MISSING", "Localization references unknown perk_id")
            row = connection.execute("SELECT payload_json FROM perk_localizations WHERE perk_id=? AND locale=?", (item.perk_id, item.locale)).fetchone()
            if self._assert_idempotent(row, payload, kind="LOCALIZATION"):
                return
            connection.execute("INSERT INTO perk_localizations(perk_id,locale,normalized_name,payload_json,payload_sha256) VALUES(?,?,?,?,?)", (item.perk_id, item.locale, item.normalized_name, self._payload_text(payload), payload["perk_localization_sha256"]))
            connection.commit()

    def put_alias(self, item: PerkAlias) -> None:
        if not isinstance(item, PerkAlias):
            raise ValueError("item must be PerkAlias")
        payload = item.to_dict()
        with closing(self._connect()) as connection:
            if connection.execute("SELECT 1 FROM perk_identities WHERE perk_id=?", (item.perk_id,)).fetchone() is None:
                raise _knowledge_error("ERR_PERK_IDENTITY_MISSING", "Alias references unknown perk_id")
            row = connection.execute("SELECT payload_json FROM perk_aliases WHERE alias_id=?", (item.alias_id,)).fetchone()
            if self._assert_idempotent(row, payload, kind="ALIAS"):
                return
            connection.execute("INSERT INTO perk_aliases(alias_id,perk_id,locale,normalized_alias,verified,payload_json,payload_sha256) VALUES(?,?,?,?,?,?,?)", (item.alias_id, item.perk_id, item.locale, item.normalized_alias, int(item.verified), self._payload_text(payload), payload["perk_alias_sha256"]))
            connection.commit()

    def put_revision(self, item: PerkRevision) -> None:
        if not isinstance(item, PerkRevision):
            raise ValueError("item must be PerkRevision")
        payload = item.to_dict()
        with closing(self._connect()) as connection:
            if connection.execute("SELECT 1 FROM perk_identities WHERE perk_id=?", (item.perk_id,)).fetchone() is None:
                raise _knowledge_error("ERR_PERK_IDENTITY_MISSING", "Revision references unknown perk_id")
            existing_id = connection.execute("SELECT payload_json FROM perk_revisions WHERE revision_id=?", (item.revision_id,)).fetchone()
            if self._assert_idempotent(existing_id, payload, kind="REVISION"):
                return
            sources = []
            for source_id in item.source_ids:
                row = connection.execute("SELECT environment,authority FROM perk_sources WHERE source_id=?", (source_id,)).fetchone()
                if row is None:
                    raise _knowledge_error("ERR_PERK_SOURCE_MISSING", "Revision references unknown Source Provenance", source_id=source_id)
                sources.append(row)
            if item.status is PerkRevisionStatus.VERIFIED:
                if item.environment in {PerkEnvironment.UNKNOWN, PerkEnvironment.ARCHIVE}:
                    raise _knowledge_error("ERR_PERK_VERIFIED_ENVIRONMENT", "VERIFIED revision must be explicitly LIVE or PTB")
                if not any(row["authority"] != PerkSourceAuthority.UNKNOWN.value and row["environment"] in {None, item.environment.value} for row in sources):
                    raise _knowledge_error("ERR_PERK_VERIFIED_PROVENANCE", "VERIFIED revision requires compatible non-UNKNOWN Source Provenance")
                existing = connection.execute("SELECT payload_json FROM perk_revisions WHERE perk_id=? AND environment=? AND status=?", (item.perk_id, item.environment.value, PerkRevisionStatus.VERIFIED.value)).fetchall()
                for row in existing:
                    other = _parse_revision(json.loads(row["payload_json"]))
                    if _ranges_overlap_version(item, other):
                        raise _knowledge_error("ERR_PERK_VERIFIED_RANGE_OVERLAP", "VERIFIED Perk revisions must not have overlapping patch ranges", category=ProductErrorCategory.DATA_INTEGRITY)
            connection.execute("INSERT INTO perk_revisions(revision_id,perk_id,environment,status,version_from,version_to_exclusive,payload_json,payload_sha256) VALUES(?,?,?,?,?,?,?,?)", (item.revision_id, item.perk_id, item.environment.value, item.status.value, item.game_version_from, item.game_version_to_exclusive, self._payload_text(payload), payload["perk_revision_sha256"]))
            connection.commit()

    def resolve_alias(self, value: str, *, locale: str | None = None) -> str | None:
        normalized = normalize_perk_alias(value)
        if locale is not None:
            _require_locale(locale)
        with closing(self._connect()) as connection:
            params: list[Any] = [normalized]
            locale_clause = ""
            if locale is not None:
                locale_clause = " AND locale=?"
                params.append(locale)
            localization_rows = connection.execute(
                f"SELECT perk_id,normalized_name,payload_json FROM perk_localizations WHERE normalized_name=?{locale_clause}",
                tuple(params),
            ).fetchall()
            alias_params: list[Any] = [normalized]
            alias_locale_clause = ""
            if locale is not None:
                alias_locale_clause = " AND locale=?"
                alias_params.append(locale)
            alias_rows = connection.execute(
                f"SELECT perk_id,normalized_alias,payload_json FROM perk_aliases WHERE normalized_alias=? AND verified=1{alias_locale_clause}",
                tuple(alias_params),
            ).fetchall()

        matches: set[str] = set()
        try:
            for row in localization_rows:
                item = _parse_localization(json.loads(row["payload_json"]))
                if item.perk_id != row["perk_id"] or item.normalized_name != row["normalized_name"] or item.normalized_name != normalized:
                    raise ValueError("localization lookup index does not match canonical payload")
                matches.add(item.perk_id)
            for row in alias_rows:
                item = _parse_alias(json.loads(row["payload_json"]))
                if not item.verified or item.perk_id != row["perk_id"] or item.normalized_alias != row["normalized_alias"] or item.normalized_alias != normalized:
                    raise ValueError("alias lookup index does not match canonical payload")
                matches.add(item.perk_id)
        except (ValueError, json.JSONDecodeError) as exc:
            raise _knowledge_error(
                "ERR_PERK_LOOKUP_INDEX_CORRUPT",
                "Perk alias/name lookup index does not match canonical payload",
                category=ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if len(matches) > 1:
            raise _knowledge_error("ERR_PERK_ALIAS_AMBIGUOUS", "Alias/name resolves to multiple perk IDs", matches=sorted(matches))
        return next(iter(matches), None)

    def resolve_verified_revision(self, perk_id: str, *, game_version: str, environment: GameEnvironment) -> PerkRevision:
        _require_perk_id(perk_id)
        if environment not in {GameEnvironment.LIVE, GameEnvironment.PTB}:
            raise _knowledge_error("ERR_PERK_LOOKUP_ENVIRONMENT", "Patch-aware VERIFIED lookup requires LIVE or PTB environment")
        try:
            DBDPatchVersion.parse(game_version)
        except ValueError as exc:
            raise _knowledge_error("ERR_PERK_PATCH_UNKNOWN", "Game patch cannot be resolved to a numeric DbD version", game_version=game_version) from exc
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT payload_json FROM perk_revisions WHERE perk_id=? AND environment=? AND status=?", (perk_id, environment.value, PerkRevisionStatus.VERIFIED.value)).fetchall()
            try:
                revisions = [_parse_revision(json.loads(row["payload_json"])) for row in rows]
            except (ValueError, json.JSONDecodeError) as exc:
                raise _knowledge_error("ERR_PERK_REVISION_CORRUPT", "Stored Perk revision payload/hash is corrupt", category=ProductErrorCategory.DATA_INTEGRITY) from exc
            matches = [revision for revision in revisions if revision.is_compatible(game_version)]
            if not matches:
                raise _knowledge_error("ERR_PERK_VERIFIED_REVISION_NOT_FOUND", "No patch-compatible VERIFIED Perk revision exists", perk_id=perk_id, game_version=game_version, environment=environment.value)
            if len(matches) != 1:
                raise _knowledge_error("ERR_PERK_VERIFIED_REVISION_AMBIGUOUS", "Multiple patch-compatible VERIFIED Perk revisions exist", category=ProductErrorCategory.DATA_INTEGRITY, perk_id=perk_id)
            revision = matches[0]
            compatible_source = False
            for source_id in revision.source_ids:
                row = connection.execute("SELECT environment,authority,payload_json FROM perk_sources WHERE source_id=?", (source_id,)).fetchone()
                if row is None:
                    raise _knowledge_error("ERR_PERK_SOURCE_MISSING", "VERIFIED revision Source Provenance is missing", category=ProductErrorCategory.DATA_INTEGRITY, source_id=source_id)
                try:
                    item = _parse_source(json.loads(row["payload_json"]))
                except (ValueError, json.JSONDecodeError) as exc:
                    raise _knowledge_error("ERR_PERK_SOURCE_CORRUPT", "Stored Perk Source Provenance payload/hash is corrupt", category=ProductErrorCategory.DATA_INTEGRITY, source_id=source_id) from exc
                if (None if item.environment is None else item.environment.value) != row["environment"] or item.authority.value != row["authority"]:
                    raise _knowledge_error("ERR_PERK_SOURCE_INDEX_CORRUPT", "Perk Source Provenance index does not match canonical payload", category=ProductErrorCategory.DATA_INTEGRITY, source_id=source_id)
                if item.authority is not PerkSourceAuthority.UNKNOWN and item.environment in {None, revision.environment}:
                    compatible_source = True
            if not compatible_source:
                raise _knowledge_error("ERR_PERK_VERIFIED_PROVENANCE", "VERIFIED revision no longer has compatible non-UNKNOWN Source Provenance", category=ProductErrorCategory.DATA_INTEGRITY)
            return revision

    def lookup(self, value: str, *, game_version: str, environment: GameEnvironment, locale: str | None = None) -> PerkLookupResult:
        perk_id = value if isinstance(value, str) and _PERK_ID_RE.fullmatch(value) else self.resolve_alias(value, locale=locale)
        if perk_id is None:
            raise _knowledge_error("ERR_PERK_NOT_FOUND", "Perk ID/name/alias was not found")
        with closing(self._connect()) as connection:
            identity_row = connection.execute("SELECT payload_json FROM perk_identities WHERE perk_id=?", (perk_id,)).fetchone()
            if identity_row is None:
                raise _knowledge_error("ERR_PERK_NOT_FOUND", "Perk identity was not found")
            loc_rows = connection.execute("SELECT payload_json FROM perk_localizations WHERE perk_id=? ORDER BY locale", (perk_id,)).fetchall()
        identity = _parse_identity(json.loads(identity_row["payload_json"]))
        revision = self.resolve_verified_revision(perk_id, game_version=game_version, environment=environment)
        localizations = tuple(_parse_localization(json.loads(row["payload_json"])) for row in loc_rows)
        return PerkLookupResult(identity, revision, localizations)

    def resolve_observation(self, observation: PerkObservation, match_environment: GameEnvironment, game_version: str) -> PerkObservation:
        if not isinstance(observation, PerkObservation):
            raise ValueError("observation must be PerkObservation")
        if observation.state is PerkObservationState.UNKNOWN:
            return observation
        assert observation.perk_id is not None
        revision = self.resolve_verified_revision(observation.perk_id, game_version=game_version, environment=match_environment)
        return replace(observation, state=PerkObservationState.RESOLVED, resolved_revision_id=revision.revision_id)

    def bind_event(self, event: CanonicalGameEvent, perk_id: str) -> CanonicalGameEvent:
        if not isinstance(event, CanonicalGameEvent):
            raise ValueError("event must be CanonicalGameEvent")
        lookup = self.lookup(perk_id, game_version=event.game_version, environment=event.environment)
        ref = lookup.to_knowledge_ref()
        if any(existing.to_dict()["knowledge_ref_sha256"] == ref.to_dict()["knowledge_ref_sha256"] for existing in event.knowledge_refs):
            return event
        refs = tuple(sorted((*event.knowledge_refs, ref), key=lambda item: item.to_dict()["knowledge_ref_sha256"]))
        return replace(event, revision=event.revision + 1, knowledge_refs=refs)


def _ranges_overlap_version(left: PerkRevision, right: PerkRevision) -> bool:
    left_start = DBDPatchVersion.parse(left.game_version_from)
    right_start = DBDPatchVersion.parse(right.game_version_from)
    left_end = None if left.game_version_to_exclusive is None else DBDPatchVersion.parse(left.game_version_to_exclusive)
    right_end = None if right.game_version_to_exclusive is None else DBDPatchVersion.parse(right.game_version_to_exclusive)
    return (right_end is None or left_start < right_end) and (left_end is None or right_start < left_end)


def _verify_hash(payload: dict[str, Any], hash_field: str) -> None:
    body = dict(payload)
    claimed = body.pop(hash_field, None)
    validate_sha256(claimed, field_name=hash_field)
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError(f"{hash_field} does not match canonical body")


def _parse_identity(payload: Any) -> PerkIdentity:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Perk identity payload")
    _verify_hash(payload, "perk_identity_sha256")
    return PerkIdentity(payload["perk_id"], payload["slug"], PerkRole(payload["role"]), payload["owner_character_id"], payload["introduced_version"], payload["retired_version"], payload["active"], payload["created_at"])


def _parse_localization(payload: Any) -> PerkLocalization:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Perk localization payload")
    _verify_hash(payload, "perk_localization_sha256")
    return PerkLocalization(payload["perk_id"], payload["locale"], payload["name"], payload["simple_text"], payload["beginner_text"], payload["short_text"])


def _parse_alias(payload: Any) -> PerkAlias:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Perk alias payload")
    _verify_hash(payload, "perk_alias_sha256")
    return PerkAlias(
        payload["alias_id"], payload["perk_id"], payload["locale"], payload["alias"],
        PerkAliasType(payload["alias_type"]), payload["verified"],
    )


def _parse_source(payload: Any) -> PerkKnowledgeSource:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Perk source payload")
    _verify_hash(payload, "perk_source_sha256")
    return PerkKnowledgeSource(
        source_id=payload["source_id"], source_type=payload["source_type"],
        authority=PerkSourceAuthority(payload["authority"]),
        environment=None if payload["environment"] is None else PerkEnvironment(payload["environment"]),
        uri=payload["uri"], retrieved_at=payload["retrieved_at"], locale=payload["locale"],
        content_sha256=payload["content_sha256"],
    )


def _parse_revision(payload: Any) -> PerkRevision:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Perk revision payload")
    _verify_hash(payload, "perk_revision_sha256")
    item = PerkRevision(
        revision_id=payload["revision_id"], perk_id=payload["perk_id"], game_version_from=payload["game_version_from"],
        game_version_to_exclusive=payload["game_version_to_exclusive"], environment=PerkEnvironment(payload["environment"]),
        status=PerkRevisionStatus(payload["status"]), source_ids=tuple(payload["source_ids"]), official_effect_ja=payload["official_effect_ja"],
        official_effect_en=payload["official_effect_en"], structured_effect=payload["structured_effect"], tags=tuple(payload["tags"]), created_at=payload["created_at"],
    )
    if item.content_sha256 != payload["content_sha256"]:
        raise ValueError("Perk revision content_sha256 does not match fact payload")
    return item


__all__ = [
    "DBDPatchVersion",
    "DbDPerkKnowledgeStore",
    "PerkAlias",
    "PerkAliasType",
    "PerkEnvironment",
    "PerkIdentity",
    "PerkKnowledgeSource",
    "PerkLocalization",
    "PerkLookupResult",
    "PerkObservation",
    "PerkObservationState",
    "PerkRevision",
    "PerkRevisionStatus",
    "PerkRole",
    "PerkSourceAuthority",
    "normalize_perk_alias",
]
