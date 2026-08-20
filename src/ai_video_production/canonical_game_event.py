"""TASK-049 canonical game-analysis contracts.

These records describe what was observed in a game.  They do not authorize or
perform BVP Production Timeline edits, Resolve writes, provider calls, or any
other external effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Mapping

from .game_event_evidence import SourceFrameRange, parse_source_frame_range
from .ids import IdKind, generate_id, validate_id
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso
from .timebase import FrameRate


_GAME_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_ENTITY_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,127}$")
_REVISION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class GameEnvironment(str, Enum):
    LIVE = "LIVE"
    PTB = "PTB"
    UNKNOWN = "UNKNOWN"


class GamePerspective(str, Enum):
    SURVIVOR = "SURVIVOR"
    KILLER = "KILLER"
    SPECTATOR = "SPECTATOR"
    UNKNOWN = "UNKNOWN"


class GameMatchStatus(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REVIEWED = "REVIEWED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class GameEventType(str, Enum):
    MATCH_START = "MATCH_START"
    CHASE_START = "CHASE_START"
    CHASE_END = "CHASE_END"
    INJURY = "INJURY"
    DOWN = "DOWN"
    HOOK = "HOOK"
    UNHOOK = "UNHOOK"
    WINDOW_VAULT = "WINDOW_VAULT"
    PALLET_DROP = "PALLET_DROP"
    KILL = "KILL"
    ESCAPE = "ESCAPE"
    UNKNOWN_EVENT = "UNKNOWN_EVENT"


class EventConfirmationState(str, Enum):
    DETECTED = "DETECTED"
    POSSIBLE = "POSSIBLE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class EventReviewStatus(str, Enum):
    PENDING = "PENDING"
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class GameReviewAction(str, Enum):
    APPROVE = "APPROVE"
    CORRECT = "CORRECT"
    REJECT = "REJECT"
    MARK_UNKNOWN = "MARK_UNKNOWN"


class GameKnowledgeKind(str, Enum):
    PERK = "PERK"
    KILLER = "KILLER"
    POWER = "POWER"
    MAP = "MAP"
    REALM = "REALM"
    TILE = "TILE"
    ADDON = "ADDON"
    ITEM = "ITEM"
    OFFERING = "OFFERING"
    CHARACTER = "CHARACTER"
    SURVIVOR = "SURVIVOR"
    KNOWLEDGE = "KNOWLEDGE"
    STATUS = "STATUS"
    MECHANIC = "MECHANIC"


def _require_enum(value: Any, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise ValueError(f"{field_name} must be a {enum_type.__name__}")


def _require_game_version(value: str, *, field_name: str = "game_version") -> str:
    if not isinstance(value, str) or not _GAME_VERSION_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a bounded game-version identifier")
    return value


def _require_text(value: str, *, field_name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be a non-empty string up to {maximum} characters")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value


def _require_confidence(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
        raise ValueError("confidence_milli must be an integer in 0..1000")
    return value


def _require_json_object(value: Mapping[str, Any], *, field_name: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    # Canonical JSON encoding also rejects non-serializable values early.
    try:
        canonical_json_bytes(dict(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be canonical-JSON serializable") from exc


@dataclass(frozen=True, slots=True)
class GameMatch:
    production_job_id: str
    source_asset_id: str
    game_profile_id: str
    game_profile_version: str
    game_version: str
    environment: GameEnvironment
    perspective: GamePerspective
    source_rate: FrameRate
    analysis_revision: int = 1
    status: GameMatchStatus = GameMatchStatus.CREATED
    match_id: str = field(default_factory=lambda: generate_id(IdKind.GAME_MATCH))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.source_asset_id, IdKind.ASSET)
        validate_id(self.match_id, IdKind.GAME_MATCH)
        if not isinstance(self.game_profile_id, str) or not _ENTITY_ID_RE.fullmatch(self.game_profile_id):
            raise ValueError("game_profile_id must be a stable lowercase identifier")
        SemVer.parse(self.game_profile_version)
        _require_game_version(self.game_version)
        _require_enum(self.environment, GameEnvironment, "environment")
        _require_enum(self.perspective, GamePerspective, "perspective")
        if not isinstance(self.source_rate, FrameRate):
            raise ValueError("source_rate must be an exact FrameRate")
        if isinstance(self.analysis_revision, bool) or not isinstance(self.analysis_revision, int) or self.analysis_revision < 1:
            raise ValueError("analysis_revision must be a positive integer")
        _require_enum(self.status, GameMatchStatus, "status")
        _require_text(self.created_at, field_name="created_at", maximum=64)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "match_id": self.match_id,
            "production_job_id": self.production_job_id,
            "source_asset_id": self.source_asset_id,
            "game_profile_id": self.game_profile_id,
            "game_profile_version": self.game_profile_version,
            "game_version": self.game_version,
            "environment": self.environment.value,
            "perspective": self.perspective.value,
            "source_rate": {
                "numerator": self.source_rate.numerator,
                "denominator": self.source_rate.denominator,
            },
            "analysis_revision": self.analysis_revision,
            "status": self.status.value,
            "created_at": self.created_at,
        }
        return {**body, "match_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class GameKnowledgeRef:
    knowledge_kind: GameKnowledgeKind
    entity_id: str
    revision_id: str
    environment: GameEnvironment
    game_version_from: str
    source_provenance_ref: str
    game_version_to: str | None = None

    def __post_init__(self) -> None:
        _require_enum(self.knowledge_kind, GameKnowledgeKind, "knowledge_kind")
        if not isinstance(self.entity_id, str) or not _ENTITY_ID_RE.fullmatch(self.entity_id):
            raise ValueError("entity_id must be a stable lowercase identifier")
        if not isinstance(self.revision_id, str) or not _REVISION_ID_RE.fullmatch(self.revision_id):
            raise ValueError("revision_id must be a bounded stable identifier")
        _require_enum(self.environment, GameEnvironment, "environment")
        _require_game_version(self.game_version_from, field_name="game_version_from")
        if self.game_version_to is not None:
            _require_game_version(self.game_version_to, field_name="game_version_to")
        _require_text(self.source_provenance_ref, field_name="source_provenance_ref", maximum=512)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "knowledge_kind": self.knowledge_kind.value,
            "entity_id": self.entity_id,
            "revision_id": self.revision_id,
            "environment": self.environment.value,
            "game_version_from": self.game_version_from,
            "game_version_to": self.game_version_to,
            "source_provenance_ref": self.source_provenance_ref,
        }
        return {
            **body,
            "knowledge_ref_sha256": sha256_bytes(canonical_json_bytes(body)),
        }


@dataclass(frozen=True, slots=True)
class CanonicalGameEvent:
    match_id: str
    revision: int
    event_type: GameEventType
    source_range: SourceFrameRange
    game_version: str
    environment: GameEnvironment
    perspective: GamePerspective
    state: Mapping[str, Any]
    confidence_milli: int
    confirmation_state: EventConfirmationState
    evidence_refs: tuple[str, ...]
    knowledge_refs: tuple[GameKnowledgeRef, ...] = ()
    review_status: EventReviewStatus = EventReviewStatus.PENDING
    event_id: str = field(default_factory=lambda: generate_id(IdKind.GAME_EVENT))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be a positive integer")
        _require_enum(self.event_type, GameEventType, "event_type")
        if not isinstance(self.source_range, SourceFrameRange):
            raise ValueError("source_range must be a SourceFrameRange")
        _require_game_version(self.game_version)
        _require_enum(self.environment, GameEnvironment, "environment")
        _require_enum(self.perspective, GamePerspective, "perspective")
        _require_json_object(self.state, field_name="state")
        _require_confidence(self.confidence_milli)
        _require_enum(self.confirmation_state, EventConfirmationState, "confirmation_state")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise ValueError("event must reference at least one admitted game Evidence")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")
        for ref in self.evidence_refs:
            validate_id(ref, IdKind.GAME_EVIDENCE)
        if not isinstance(self.knowledge_refs, tuple) or any(
            not isinstance(ref, GameKnowledgeRef) for ref in self.knowledge_refs
        ):
            raise ValueError("knowledge_refs must contain GameKnowledgeRef values")
        if len({ref.to_dict()["knowledge_ref_sha256"] for ref in self.knowledge_refs}) != len(self.knowledge_refs):
            raise ValueError("knowledge_refs must be unique")
        _require_enum(self.review_status, EventReviewStatus, "review_status")
        _require_text(self.created_at, field_name="created_at", maximum=64)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "event_id": self.event_id,
            "match_id": self.match_id,
            "revision": self.revision,
            "event_type": self.event_type.value,
            "source_range": self.source_range.to_dict(),
            "game_version": self.game_version,
            "environment": self.environment.value,
            "perspective": self.perspective.value,
            "state": dict(self.state),
            "confidence_milli": self.confidence_milli,
            "confirmation_state": self.confirmation_state.value,
            "evidence_refs": list(self.evidence_refs),
            "knowledge_refs": [ref.to_dict() for ref in self.knowledge_refs],
            "review_status": self.review_status.value,
            "created_at": self.created_at,
        }
        return {**body, "event_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class GameEventReview:
    event_id: str
    event_revision: int
    action: GameReviewAction
    reviewer_kind: str
    original_confirmation_state: EventConfirmationState
    corrected_confirmation_state: EventConfirmationState
    original_event_type: GameEventType
    corrected_event_type: GameEventType
    reason_code: str
    notes: str = ""
    review_id: str = field(default_factory=lambda: generate_id(IdKind.GAME_REVIEW))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.event_id, IdKind.GAME_EVENT)
        validate_id(self.review_id, IdKind.GAME_REVIEW)
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be a positive integer")
        _require_enum(self.action, GameReviewAction, "action")
        if self.reviewer_kind not in {"HUMAN", "SYSTEM"}:
            raise ValueError("reviewer_kind must be HUMAN or SYSTEM")
        _require_enum(self.original_confirmation_state, EventConfirmationState, "original_confirmation_state")
        _require_enum(self.corrected_confirmation_state, EventConfirmationState, "corrected_confirmation_state")
        _require_enum(self.original_event_type, GameEventType, "original_event_type")
        _require_enum(self.corrected_event_type, GameEventType, "corrected_event_type")
        if not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code):
            raise ValueError("reason_code must be an uppercase stable reason code")
        if not isinstance(self.notes, str) or len(self.notes) > 2000:
            raise ValueError("notes must be a string up to 2000 characters")
        _require_text(self.created_at, field_name="created_at", maximum=64)
        if self.action is GameReviewAction.APPROVE:
            if (
                self.corrected_confirmation_state is not self.original_confirmation_state
                or self.corrected_event_type is not self.original_event_type
            ):
                raise ValueError("APPROVE cannot change event type or confirmation state")
        if self.action is GameReviewAction.REJECT and self.corrected_confirmation_state is not EventConfirmationState.REJECTED:
            raise ValueError("REJECT must set corrected confirmation state to REJECTED")
        if self.action is GameReviewAction.MARK_UNKNOWN and self.corrected_confirmation_state is not EventConfirmationState.UNKNOWN:
            raise ValueError("MARK_UNKNOWN must set corrected confirmation state to UNKNOWN")
        if self.action is GameReviewAction.CORRECT and (
            self.corrected_confirmation_state is self.original_confirmation_state
            and self.corrected_event_type is self.original_event_type
        ):
            raise ValueError("CORRECT must change event type or confirmation state")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "review_id": self.review_id,
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "action": self.action.value,
            "reviewer_kind": self.reviewer_kind,
            "original_confirmation_state": self.original_confirmation_state.value,
            "corrected_confirmation_state": self.corrected_confirmation_state.value,
            "original_event_type": self.original_event_type.value,
            "corrected_event_type": self.corrected_event_type.value,
            "reason_code": self.reason_code,
            "notes": self.notes,
            "created_at": self.created_at,
        }
        return {**body, "review_sha256": sha256_bytes(canonical_json_bytes(body))}


def parse_game_match(payload: Any) -> GameMatch:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid game match payload")
    try:
        rate = payload["source_rate"]
        if not isinstance(rate, dict) or set(rate) != {"numerator", "denominator"}:
            raise ValueError("invalid source_rate")
        item = GameMatch(
            production_job_id=payload["production_job_id"],
            source_asset_id=payload["source_asset_id"],
            game_profile_id=payload["game_profile_id"],
            game_profile_version=payload["game_profile_version"],
            game_version=payload["game_version"],
            environment=GameEnvironment(payload["environment"]),
            perspective=GamePerspective(payload["perspective"]),
            source_rate=FrameRate(rate["numerator"], rate["denominator"]),
            analysis_revision=payload["analysis_revision"],
            status=GameMatchStatus(payload["status"]),
            match_id=payload["match_id"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid game match payload") from exc
    if item.to_dict() != payload:
        raise ValueError("game match payload/hash is not canonical")
    return item


def parse_game_knowledge_ref(payload: Any) -> GameKnowledgeRef:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid game knowledge reference payload")
    try:
        item = GameKnowledgeRef(
            knowledge_kind=GameKnowledgeKind(payload["knowledge_kind"]),
            entity_id=payload["entity_id"],
            revision_id=payload["revision_id"],
            environment=GameEnvironment(payload["environment"]),
            game_version_from=payload["game_version_from"],
            source_provenance_ref=payload["source_provenance_ref"],
            game_version_to=payload["game_version_to"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid game knowledge reference payload") from exc
    if item.to_dict() != payload:
        raise ValueError("game knowledge reference payload/hash is not canonical")
    return item


def parse_canonical_game_event(payload: Any) -> CanonicalGameEvent:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid canonical game event payload")
    try:
        knowledge = tuple(parse_game_knowledge_ref(value) for value in payload["knowledge_refs"])
        item = CanonicalGameEvent(
            match_id=payload["match_id"],
            revision=payload["revision"],
            event_type=GameEventType(payload["event_type"]),
            source_range=parse_source_frame_range(payload["source_range"]),
            game_version=payload["game_version"],
            environment=GameEnvironment(payload["environment"]),
            perspective=GamePerspective(payload["perspective"]),
            state=payload["state"],
            confidence_milli=payload["confidence_milli"],
            confirmation_state=EventConfirmationState(payload["confirmation_state"]),
            evidence_refs=tuple(payload["evidence_refs"]),
            knowledge_refs=knowledge,
            review_status=EventReviewStatus(payload["review_status"]),
            event_id=payload["event_id"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid canonical game event payload") from exc
    if item.to_dict() != payload:
        raise ValueError("canonical game event payload/hash is not canonical")
    return item


def parse_game_event_review(payload: Any) -> GameEventReview:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or invalid game event review payload")
    try:
        item = GameEventReview(
            event_id=payload["event_id"],
            event_revision=payload["event_revision"],
            action=GameReviewAction(payload["action"]),
            reviewer_kind=payload["reviewer_kind"],
            original_confirmation_state=EventConfirmationState(payload["original_confirmation_state"]),
            corrected_confirmation_state=EventConfirmationState(payload["corrected_confirmation_state"]),
            original_event_type=GameEventType(payload["original_event_type"]),
            corrected_event_type=GameEventType(payload["corrected_event_type"]),
            reason_code=payload["reason_code"],
            notes=payload["notes"],
            review_id=payload["review_id"],
            created_at=payload["created_at"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid game event review payload") from exc
    if item.to_dict() != payload:
        raise ValueError("game event review payload/hash is not canonical")
    return item


__all__ = [
    "CanonicalGameEvent",
    "EventConfirmationState",
    "EventReviewStatus",
    "GameEnvironment",
    "GameEventReview",
    "GameEventType",
    "GameKnowledgeKind",
    "GameKnowledgeRef",
    "GameMatch",
    "GameMatchStatus",
    "GamePerspective",
    "GameReviewAction",
    "parse_canonical_game_event",
    "parse_game_event_review",
    "parse_game_knowledge_ref",
    "parse_game_match",
]
