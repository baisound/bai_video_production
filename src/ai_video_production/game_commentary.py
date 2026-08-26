"""TASK-049 R7 provider-neutral Commentary Planner / Fact Validator.

The planner compiles only facts already supported by a CONFIRMED CGEL Event
and patch-compatible canonical Perk Knowledge.  It performs no LLM/provider
call.  A later provider may draft prose from the plan, but the resulting draft
must pass the deterministic Fact Validator before it is eligible for a later
Production Bridge.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEventType,
    GameKnowledgeKind,
)
from .dbd_perk_knowledge import DbDPerkKnowledgeStore, PerkEnvironment, PerkLookupResult
from .dbd_killer_knowledge import DbDKillerKnowledgeStore, KillerKnowledgeKind
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256


class CommentaryDisposition(str, Enum):
    PROPOSE = "PROPOSE"
    ABSTAIN = "ABSTAIN"


class CommentaryClaimKind(str, Enum):
    EVENT_OCCURRED = "EVENT_OCCURRED"
    PERK_NAME = "PERK_NAME"
    PERK_EFFECT = "PERK_EFFECT"
    PERK_ACTIVATION = "PERK_ACTIVATION"
    KILLER_NAME = "KILLER_NAME"
    KILLER_DESCRIPTION = "KILLER_DESCRIPTION"
    POWER_NAME = "POWER_NAME"
    POWER_DESCRIPTION = "POWER_DESCRIPTION"
    TRIVIA = "TRIVIA"


class CommentaryCandidateStatus(str, Enum):
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


def _stable_text(value: str, *, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be a non-empty string up to {maximum} characters")
    return value


def _reason(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", value):
        raise ValueError("reason code must be an uppercase stable identifier")
    return value


def _locale(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", value):
        raise ValueError("language must be a language or language-region tag")
    return value


@dataclass(frozen=True, slots=True)
class CommentaryFact:
    kind: CommentaryClaimKind
    key: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CommentaryClaimKind):
            raise ValueError("kind must be a CommentaryClaimKind")
        _stable_text(self.key, field_name="key", maximum=256)
        _stable_text(self.value, field_name="value", maximum=16000)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "key": self.key, "value": self.value}


@dataclass(frozen=True, slots=True)
class CommentaryPlan:
    match_id: str
    event_id: str
    event_revision: int
    language: str
    disposition: CommentaryDisposition
    priority_milli: int
    reason_codes: tuple[str, ...]
    facts: tuple[CommentaryFact, ...]
    evidence_refs: tuple[str, ...]
    knowledge_ref_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_id(self.match_id, IdKind.GAME_MATCH)
        validate_id(self.event_id, IdKind.GAME_EVENT)
        if isinstance(self.event_revision, bool) or not isinstance(self.event_revision, int) or self.event_revision < 1:
            raise ValueError("event_revision must be positive")
        _locale(self.language)
        if not isinstance(self.disposition, CommentaryDisposition):
            raise ValueError("disposition must be a CommentaryDisposition")
        if isinstance(self.priority_milli, bool) or not isinstance(self.priority_milli, int) or not 0 <= self.priority_milli <= 1000:
            raise ValueError("priority_milli must be 0..1000")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("reason_codes must be unique and canonically sorted")
        for value in self.reason_codes:
            _reason(value)
        if not isinstance(self.facts, tuple) or any(not isinstance(item, CommentaryFact) for item in self.facts):
            raise ValueError("facts must contain CommentaryFact values")
        fact_keys = [(item.kind.value, item.key, item.value) for item in self.facts]
        if fact_keys != sorted(set(fact_keys)):
            raise ValueError("facts must be unique and canonically sorted")
        if self.evidence_refs != tuple(sorted(set(self.evidence_refs))):
            raise ValueError("evidence_refs must be unique and canonically sorted")
        for ref in self.evidence_refs:
            validate_id(ref, IdKind.GAME_EVIDENCE)
        if self.knowledge_ref_sha256s != tuple(sorted(set(self.knowledge_ref_sha256s))):
            raise ValueError("knowledge_ref_sha256s must be unique and canonically sorted")
        if self.disposition is CommentaryDisposition.ABSTAIN and self.facts:
            raise ValueError("ABSTAIN plan must not expose speakable facts")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "match_id": self.match_id,
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "language": self.language,
            "disposition": self.disposition.value,
            "priority_milli": self.priority_milli,
            "reason_codes": list(self.reason_codes),
            "facts": [item.to_dict() for item in self.facts],
            "evidence_refs": list(self.evidence_refs),
            "knowledge_ref_sha256s": list(self.knowledge_ref_sha256s),
        }
        return {**body, "commentary_plan_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class CommentaryClaim:
    kind: CommentaryClaimKind
    key: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CommentaryClaimKind):
            raise ValueError("kind must be a CommentaryClaimKind")
        _stable_text(self.key, field_name="key", maximum=256)
        _stable_text(self.value, field_name="value", maximum=16000)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "key": self.key, "value": self.value}


@dataclass(frozen=True, slots=True)
class CommentaryDraft:
    text: str
    claims: tuple[CommentaryClaim, ...]
    provider_ref: str | None = None

    def __post_init__(self) -> None:
        _stable_text(self.text, field_name="text", maximum=16000)
        if not isinstance(self.claims, tuple) or any(not isinstance(item, CommentaryClaim) for item in self.claims):
            raise ValueError("claims must contain CommentaryClaim values")
        keys = [(item.kind.value, item.key, item.value) for item in self.claims]
        if keys != sorted(set(keys)):
            raise ValueError("claims must be unique and canonically sorted")
        if self.provider_ref is not None:
            _stable_text(self.provider_ref, field_name="provider_ref", maximum=512)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
            "text": self.text,
            "claims": [item.to_dict() for item in self.claims],
            "provider_ref": self.provider_ref,
        }
        return {**body, "commentary_draft_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class FactValidationResult:
    passed: bool
    errors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be bool")
        if self.errors != tuple(sorted(set(self.errors))):
            raise ValueError("errors must be unique and canonically sorted")
        if self.passed == bool(self.errors):
            raise ValueError("passed must be true exactly when errors are empty")


class CommentaryPlanner:
    _PRIORITY = {
        GameEventType.MATCH_START: 200,
        GameEventType.CHASE_START: 650,
        GameEventType.CHASE_END: 650,
        GameEventType.GENERATOR_COMPLETE: 760,
        GameEventType.INJURY: 750,
        GameEventType.DOWN: 820,
        GameEventType.HOOK: 850,
        GameEventType.UNHOOK: 700,
        GameEventType.WINDOW_VAULT: 720,
        GameEventType.PALLET_DROP: 720,
        GameEventType.KILL: 900,
        GameEventType.ESCAPE: 900,
        GameEventType.UNKNOWN_EVENT: 0,
    }

    def __init__(self, *, minimum_priority_milli: int = 600) -> None:
        if isinstance(minimum_priority_milli, bool) or not isinstance(minimum_priority_milli, int) or not 0 <= minimum_priority_milli <= 1000:
            raise ValueError("minimum_priority_milli must be 0..1000")
        self.minimum_priority_milli = minimum_priority_milli

    def plan(
        self,
        event: CanonicalGameEvent,
        *,
        perk_store: DbDPerkKnowledgeStore | None = None,
        killer_store: DbDKillerKnowledgeStore | None = None,
        trivia_store: Any | None = None,
        language: str = "ja-JP",
    ) -> CommentaryPlan:
        if not isinstance(event, CanonicalGameEvent):
            raise TypeError("event must be CanonicalGameEvent")
        _locale(language)
        priority = self._PRIORITY[event.event_type]
        reasons: list[str] = []

        if event.confirmation_state is not EventConfirmationState.CONFIRMED:
            reasons.append("EVENT_NOT_CONFIRMED")
        if event.review_status in {EventReviewStatus.PENDING, EventReviewStatus.HUMAN_REJECTED}:
            reasons.append("EVENT_REVIEW_NOT_ADMITTED")
        if event.event_type is GameEventType.UNKNOWN_EVENT:
            reasons.append("UNKNOWN_EVENT")
        if priority < self.minimum_priority_milli:
            reasons.append("LOW_COMMENTARY_PRIORITY")

        perk_results: list[PerkLookupResult] = []
        killer_results: list[Any] = []
        knowledge_hashes: list[str] = []
        for ref in event.knowledge_refs:
            ref_hash = ref.to_dict()["knowledge_ref_sha256"]
            knowledge_hashes.append(ref_hash)
            if ref.knowledge_kind is GameKnowledgeKind.PERK:
                if perk_store is None:
                    reasons.append("PERK_KNOWLEDGE_STORE_REQUIRED")
                    continue
                try:
                    result = perk_store.lookup(
                        ref.entity_id, game_version=event.game_version, environment=event.environment, locale=language,
                    )
                except ProductError:
                    reasons.append("PERK_KNOWLEDGE_LOOKUP_FAILED")
                    continue
                if result.to_knowledge_ref().to_dict()["knowledge_ref_sha256"] != ref_hash:
                    reasons.append("KNOWLEDGE_REVISION_MISMATCH")
                    continue
                perk_results.append(result)
            elif ref.knowledge_kind in {GameKnowledgeKind.KILLER, GameKnowledgeKind.POWER}:
                if killer_store is None:
                    reasons.append("KILLER_KNOWLEDGE_STORE_REQUIRED")
                    continue
                try:
                    result = killer_store.lookup(
                        ref.entity_id, game_version=event.game_version, environment=PerkEnvironment(event.environment.value),
                    )
                except ProductError:
                    reasons.append("KILLER_KNOWLEDGE_LOOKUP_FAILED")
                    continue
                if result.to_knowledge_ref().to_dict()["knowledge_ref_sha256"] != ref_hash:
                    reasons.append("KNOWLEDGE_REVISION_MISMATCH")
                    continue
                killer_results.append(result)

        if reasons:
            return CommentaryPlan(
                match_id=event.match_id,
                event_id=event.event_id,
                event_revision=event.revision,
                language=language,
                disposition=CommentaryDisposition.ABSTAIN,
                priority_milli=priority,
                reason_codes=tuple(sorted(set(reasons))),
                facts=(),
                evidence_refs=tuple(sorted(event.evidence_refs)),
                knowledge_ref_sha256s=tuple(sorted(set(knowledge_hashes))),
            )

        facts: list[CommentaryFact] = [
            CommentaryFact(CommentaryClaimKind.EVENT_OCCURRED, "event.type", event.event_type.value)
        ]
        if trivia_store is not None:
            try:
                trivia_rows = trivia_store.query_verified(
                    game_version=event.game_version, environment=PerkEnvironment(event.environment.value),
                    event_type=event.event_type,
                    entity_refs=tuple(ref.entity_id for ref in event.knowledge_refs),
                    tags=(event.event_type.value,), limit=2,
                )
            except Exception:
                trivia_rows = ()
            for trivia in trivia_rows:
                facts.append(CommentaryFact(CommentaryClaimKind.TRIVIA, f"trivia.{trivia.trivia_id}", trivia.text))
                knowledge_hashes.append(str(trivia.to_dict()["trivia_sha256"]))
        for result in perk_results:
            localization = _select_localization(result, language)
            if localization is not None:
                facts.append(CommentaryFact(CommentaryClaimKind.PERK_NAME, f"perk.name.{result.identity.perk_id}", localization.name))
            effect = result.revision.official_effect_ja if language == "ja-JP" else result.revision.official_effect_en
            if not effect:
                effect = result.revision.official_effect_en or result.revision.official_effect_ja
            if effect:
                facts.append(CommentaryFact(CommentaryClaimKind.PERK_EFFECT, f"perk.effect.{result.identity.perk_id}", effect))

        for result in killer_results:
            if result.kind is KillerKnowledgeKind.KILLER:
                facts.append(CommentaryFact(CommentaryClaimKind.KILLER_NAME, f"killer.name.{result.entity_id}", result.name_ja if language == "ja-JP" and result.name_ja else result.name_en))
                description = result.description_ja if language == "ja-JP" and result.description_ja else result.description_en
                if description:
                    facts.append(CommentaryFact(CommentaryClaimKind.KILLER_DESCRIPTION, f"killer.description.{result.entity_id}", description))
            else:
                facts.append(CommentaryFact(CommentaryClaimKind.POWER_NAME, f"power.name.{result.entity_id}", result.name_ja if language == "ja-JP" and result.name_ja else result.name_en))
                description = result.description_ja if language == "ja-JP" and result.description_ja else result.description_en
                if description:
                    facts.append(CommentaryFact(CommentaryClaimKind.POWER_DESCRIPTION, f"power.description.{result.entity_id}", description))

        activations = event.state.get("perk_activations") if isinstance(event.state, Mapping) else None
        if isinstance(activations, list):
            for row in activations:
                if not isinstance(row, Mapping) or row.get("state") != "CONFIRMED":
                    continue
                perk_id = row.get("perk_id")
                if isinstance(perk_id, str) and any(result.identity.perk_id == perk_id for result in perk_results):
                    facts.append(CommentaryFact(CommentaryClaimKind.PERK_ACTIVATION, f"perk.activation.{perk_id}", "CONFIRMED"))

        facts_tuple = tuple(sorted(facts, key=lambda item: (item.kind.value, item.key, item.value)))
        return CommentaryPlan(
            match_id=event.match_id,
            event_id=event.event_id,
            event_revision=event.revision,
            language=language,
            disposition=CommentaryDisposition.PROPOSE,
            priority_milli=priority,
            reason_codes=(),
            facts=facts_tuple,
            evidence_refs=tuple(sorted(event.evidence_refs)),
            knowledge_ref_sha256s=tuple(sorted(set(knowledge_hashes))),
        )


def _select_localization(result: PerkLookupResult, language: str):
    exact = next((item for item in result.localizations if item.locale == language), None)
    if exact is not None:
        return exact
    return next((item for item in result.localizations if item.locale == "en-US"), None)


class CommentaryFactValidator:
    _NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:\.\d+)?%?")
    _STATUS_TERMS = {
        "HASTE", "HINDERED", "EXHAUSTED", "ENDURANCE", "BROKEN", "EXPOSED",
        "OBLIVIOUS", "UNDETECTABLE",
    }

    def validate(self, plan: CommentaryPlan, draft: CommentaryDraft) -> FactValidationResult:
        if not isinstance(plan, CommentaryPlan) or not isinstance(draft, CommentaryDraft):
            raise TypeError("plan and draft must be canonical commentary contracts")
        errors: list[str] = []
        if plan.disposition is not CommentaryDisposition.PROPOSE:
            errors.append("PLAN_ABSTAINS")

        allowed = {(fact.kind, fact.key, fact.value) for fact in plan.facts}
        if not draft.claims:
            errors.append("CLAIMS_REQUIRED")
        for claim in draft.claims:
            if (claim.kind, claim.key, claim.value) not in allowed:
                if claim.kind is CommentaryClaimKind.PERK_ACTIVATION:
                    errors.append("UNSUPPORTED_PERK_ACTIVATION_CLAIM")
                elif claim.kind is CommentaryClaimKind.PERK_EFFECT:
                    errors.append("UNSUPPORTED_PERK_EFFECT_CLAIM")
                else:
                    errors.append("UNSUPPORTED_FACT_CLAIM")

        allowed_numbers: set[str] = set()
        for fact in plan.facts:
            allowed_numbers.update(self._NUMBER_RE.findall(fact.value))
        draft_numbers = set(self._NUMBER_RE.findall(draft.text))
        for token in draft_numbers - allowed_numbers:
            errors.append(f"UNSUPPORTED_NUMBER:{token}")

        allowed_statuses = {status for status in self._STATUS_TERMS if any(status in fact.value.upper() for fact in plan.facts)}
        mentioned_statuses = {status for status in self._STATUS_TERMS if status in draft.text.upper()}
        for status in mentioned_statuses - allowed_statuses:
            errors.append(f"UNSUPPORTED_STATUS:{status}")

        activation_claimed = any(claim.kind is CommentaryClaimKind.PERK_ACTIVATION for claim in draft.claims)
        activation_language = "発動" in draft.text or "ACTIVAT" in draft.text.upper()
        if activation_language and not activation_claimed:
            errors.append("ACTIVATION_LANGUAGE_REQUIRES_CLAIM")

        return FactValidationResult(not errors, tuple(sorted(set(errors))))


@dataclass(frozen=True, slots=True)
class CommentaryCandidate:
    plan: CommentaryPlan
    draft: CommentaryDraft
    validation: FactValidationResult
    candidate_id: str = field(default_factory=lambda: generate_id(IdKind.CANDIDATE))
    created_at: str = field(default_factory=utc_now_iso)
    reasoning_lineage_required: bool = field(default=False, repr=False, compare=False)
    reasoning_origin: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_id(self.candidate_id, IdKind.CANDIDATE)
        if not isinstance(self.plan, CommentaryPlan) or not isinstance(self.draft, CommentaryDraft) or not isinstance(self.validation, FactValidationResult):
            raise ValueError("candidate requires canonical plan/draft/validation")
        _stable_text(self.created_at, field_name="created_at", maximum=64)
        if not isinstance(self.reasoning_lineage_required, bool):
            raise ValueError("reasoning_lineage_required must be bool")
        reserved = self.candidate_id.startswith("CAND-R2D")
        if self.reasoning_lineage_required != reserved:
            raise ValueError("reserved R2D Candidate identity must match lineage requirement")
        if reserved:
            if self.reasoning_origin not in {None, "TUNED_REASONING", "TUNED_REASONING_CORRECTION"}:
                raise ValueError("reasoning_origin is invalid")
            object.__setattr__(self, "reasoning_origin", self.reasoning_origin or "TUNED_REASONING")
        elif self.reasoning_origin is not None:
            raise ValueError("legacy Candidate cannot carry reasoning_origin")

    @property
    def status(self) -> CommentaryCandidateStatus:
        return CommentaryCandidateStatus.VALIDATED if self.validation.passed else CommentaryCandidateStatus.REJECTED

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": (
                "1.2.0" if self.reasoning_origin == "TUNED_REASONING_CORRECTION"
                else "1.1.0" if self.reasoning_lineage_required else "1.0.0"
            ),
            "candidate_id": self.candidate_id,
            "match_id": self.plan.match_id,
            "event_id": self.plan.event_id,
            "event_revision": self.plan.event_revision,
            "status": self.status.value,
            "plan": self.plan.to_dict(),
            "draft": self.draft.to_dict(),
            "validation": {"passed": self.validation.passed, "errors": list(self.validation.errors)},
            "created_at": self.created_at,
        }
        if self.reasoning_lineage_required:
            body["reasoning_origin"] = self.reasoning_origin
        return {**body, "commentary_candidate_sha256": sha256_bytes(canonical_json_bytes(body))}


def _verify_commentary_candidate_payload(payload: Any) -> None:
    if not isinstance(payload, dict) or payload.get("schema_version") not in {"1.0.0", "1.1.0", "1.2.0"}:
        raise ValueError("invalid Commentary candidate payload")
    legacy_keys = {"schema_version", "candidate_id", "match_id", "event_id", "event_revision", "status", "plan", "draft", "validation", "created_at", "commentary_candidate_sha256"}
    reasoning_keys = legacy_keys | {"reasoning_origin"}
    expected_keys = reasoning_keys if payload.get("schema_version") in {"1.1.0", "1.2.0"} else legacy_keys
    if set(payload) != expected_keys:
        raise ValueError("invalid Commentary candidate payload fields")
    body = dict(payload)
    candidate_hash = body.pop("commentary_candidate_sha256", None)
    if candidate_hash != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("commentary_candidate_sha256 is invalid")
    plan = payload.get("plan")
    draft = payload.get("draft")
    validation = payload.get("validation")
    if not isinstance(plan, dict) or not isinstance(draft, dict) or not isinstance(validation, dict):
        raise ValueError("Commentary candidate nested payloads are invalid")
    plan_body = dict(plan)
    plan_hash = plan_body.pop("commentary_plan_sha256", None)
    if plan_hash != sha256_bytes(canonical_json_bytes(plan_body)):
        raise ValueError("commentary_plan_sha256 is invalid")
    draft_body = dict(draft)
    draft_hash = draft_body.pop("commentary_draft_sha256", None)
    if draft_hash != sha256_bytes(canonical_json_bytes(draft_body)):
        raise ValueError("commentary_draft_sha256 is invalid")
    errors = validation.get("errors")
    passed = validation.get("passed")
    if not isinstance(passed, bool) or not isinstance(errors, list) or any(not isinstance(item, str) for item in errors):
        raise ValueError("Commentary validation payload is invalid")
    expected_status = CommentaryCandidateStatus.VALIDATED.value if passed and not errors else CommentaryCandidateStatus.REJECTED.value
    if payload.get("status") != expected_status:
        raise ValueError("Commentary candidate status does not match validation")
    reserved = isinstance(payload.get("candidate_id"), str) and payload["candidate_id"].startswith("CAND-R2D")
    expected_origin = {"1.1.0": "TUNED_REASONING", "1.2.0": "TUNED_REASONING_CORRECTION"}.get(payload.get("schema_version"))
    if (expected_origin is not None) != reserved or (reserved and payload.get("reasoning_origin") != expected_origin):
        raise ValueError("Commentary candidate reasoning_origin is invalid")


def verify_commentary_candidate_payload(payload: Any) -> None:
    """Public read-only admission boundary for canonical Candidate payloads."""

    _verify_commentary_candidate_payload(payload)


class CommentaryCandidateStore:
    """Append-only local store/export for provider-neutral Commentary candidates."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._reasoning_review_current_resolver: Any | None = None
        if self.path.exists() and self.path.is_symlink():
            raise ProductError("ERR_COMMENTARY_STORE_PATH_SYMLINK", "Commentary store path must not be a symlink", ProductErrorCategory.SECURITY)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self) -> None:
        try:
            with closing(self._connect()) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if version > 3:
                    raise ProductError("ERR_COMMENTARY_STORE_NEWER_VERSION", "Commentary store uses a newer schema", ProductErrorCategory.DATA_INTEGRITY)
                if version == 0 and tables:
                    raise ProductError("ERR_COMMENTARY_STORE_FOREIGN_SCHEMA", "Existing SQLite is not an admitted Commentary store", ProductErrorCategory.DATA_INTEGRITY)
                if version == 0:
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        conn.execute("CREATE TABLE store_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
                        conn.execute("CREATE TABLE commentary_candidates(candidate_id TEXT PRIMARY KEY,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL)")
                        conn.execute("CREATE INDEX commentary_event_lookup ON commentary_candidates(event_id,event_revision,created_at,candidate_id)")
                        self._create_v2_lineage_schema(conn)
                        self._create_v3_review_schema(conn)
                        conn.execute("INSERT INTO store_metadata VALUES('store_format','task049.game-commentary.sqlite')")
                        self._validate_v3_schema(conn)
                        conn.execute("PRAGMA user_version=3")
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
                else:
                    metadata = dict(conn.execute("SELECT key,value FROM store_metadata"))
                    if metadata.get("store_format") != "task049.game-commentary.sqlite" or "commentary_candidates" not in tables:
                        raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary store format is not recognized", ProductErrorCategory.DATA_INTEGRITY)
                    self._validate_candidate_schema(conn)
                    if version in {1, 2}:
                        try:
                            conn.execute("BEGIN IMMEDIATE")
                            if version == 1:
                                self._create_v2_lineage_schema(conn)
                            else:
                                self._validate_v2_schema(conn)
                            self._create_v3_review_schema(conn)
                            self._validate_v3_schema(conn)
                            conn.execute("PRAGMA user_version=3")
                            conn.commit()
                        except Exception:
                            conn.rollback()
                            raise
                    elif "dbd_reasoning_candidate_lineage" not in tables or "dbd_reasoning_human_reviews" not in tables:
                        raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 reasoning tables are missing", ProductErrorCategory.DATA_INTEGRITY)
                self._validate_v3_schema(conn)
        except sqlite3.DatabaseError as exc:
            raise ProductError("ERR_COMMENTARY_STORE_CORRUPT", "Commentary SQLite is corrupt or unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def _create_v2_lineage_schema(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE dbd_reasoning_candidate_lineage(candidate_id TEXT PRIMARY KEY REFERENCES commentary_candidates(candidate_id),parent_candidate_id TEXT UNIQUE REFERENCES commentary_candidates(candidate_id),match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,context_sha256 TEXT NOT NULL,commentary_plan_sha256 TEXT NOT NULL,structural_body_sha256 TEXT NOT NULL,proposal_sha256 TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL)")
        conn.execute("CREATE INDEX dbd_reasoning_lineage_event_lookup ON dbd_reasoning_candidate_lineage(event_id,event_revision,candidate_id)")

    @staticmethod
    def _create_v3_review_schema(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE dbd_reasoning_human_reviews(review_sha256 TEXT PRIMARY KEY,root_candidate_id TEXT NOT NULL REFERENCES dbd_reasoning_candidate_lineage(candidate_id),leaf_candidate_id TEXT NOT NULL REFERENCES dbd_reasoning_candidate_lineage(candidate_id),leaf_candidate_sha256 TEXT NOT NULL,leaf_lineage_sha256 TEXT NOT NULL,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,context_sha256 TEXT NOT NULL,commentary_plan_sha256 TEXT NOT NULL,proposal_sha256 TEXT NOT NULL,review_revision INTEGER NOT NULL,previous_review_sha256 TEXT,decision TEXT NOT NULL,authority_binding_sha256 TEXT NOT NULL,confirmation_sha256 TEXT NOT NULL UNIQUE,reviewed_at TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,UNIQUE(root_candidate_id,review_revision),UNIQUE(root_candidate_id,previous_review_sha256),UNIQUE(root_candidate_id,review_sha256),FOREIGN KEY(root_candidate_id,previous_review_sha256) REFERENCES dbd_reasoning_human_reviews(root_candidate_id,review_sha256))")
        conn.execute("CREATE INDEX dbd_reasoning_review_root_lookup ON dbd_reasoning_human_reviews(root_candidate_id,review_revision DESC,review_sha256)")
        conn.execute("CREATE INDEX dbd_reasoning_review_event_lookup ON dbd_reasoning_human_reviews(event_id,event_revision,root_candidate_id)")

    @staticmethod
    def _validate_v2_schema(conn: sqlite3.Connection) -> None:
        CommentaryCandidateStore._validate_candidate_schema(conn)
        expected = (
            ("candidate_id", "TEXT", 0, 1), ("parent_candidate_id", "TEXT", 0, 0),
            ("match_id", "TEXT", 1, 0), ("event_id", "TEXT", 1, 0), ("event_revision", "INTEGER", 1, 0),
            ("context_sha256", "TEXT", 1, 0), ("commentary_plan_sha256", "TEXT", 1, 0),
            ("structural_body_sha256", "TEXT", 1, 0), ("proposal_sha256", "TEXT", 1, 0),
            ("payload_json", "TEXT", 1, 0), ("payload_sha256", "TEXT", 1, 0),
        )
        info = tuple(conn.execute("PRAGMA table_info(dbd_reasoning_candidate_lineage)"))
        if tuple((row[1], row[2].upper(), row[3], row[5]) for row in info) != expected:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v2 lineage table shape is invalid", ProductErrorCategory.DATA_INTEGRITY)
        foreign = {(row[3], row[2], row[4], row[5], row[6]) for row in conn.execute("PRAGMA foreign_key_list(dbd_reasoning_candidate_lineage)")}
        if foreign != {
            ("candidate_id", "commentary_candidates", "candidate_id", "NO ACTION", "NO ACTION"),
            ("parent_candidate_id", "commentary_candidates", "candidate_id", "NO ACTION", "NO ACTION"),
        }:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v2 lineage foreign key is invalid", ProductErrorCategory.DATA_INTEGRITY)
        indexes = tuple(conn.execute("PRAGMA index_list(dbd_reasoning_candidate_lineage)"))
        index_by_name = {row[1]: row for row in indexes}
        event_index = tuple(row[2] for row in conn.execute("PRAGMA index_info(dbd_reasoning_lineage_event_lookup)"))
        unique_shapes = {
            tuple(item[0] for item in conn.execute("SELECT name FROM pragma_index_info(?) ORDER BY seqno", (row[1],)))
            for row in indexes if row[2] == 1
        }
        if "dbd_reasoning_lineage_event_lookup" not in index_by_name or event_index != ("event_id", "event_revision", "candidate_id") or ("parent_candidate_id",) not in unique_shapes:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v2 lineage index is missing", ProductErrorCategory.DATA_INTEGRITY)

    @staticmethod
    def _validate_v3_schema(conn: sqlite3.Connection) -> None:
        CommentaryCandidateStore._validate_v2_schema(conn)
        expected = (
            ("review_sha256", "TEXT", 0, 1), ("root_candidate_id", "TEXT", 1, 0),
            ("leaf_candidate_id", "TEXT", 1, 0), ("leaf_candidate_sha256", "TEXT", 1, 0),
            ("leaf_lineage_sha256", "TEXT", 1, 0), ("match_id", "TEXT", 1, 0),
            ("event_id", "TEXT", 1, 0), ("event_revision", "INTEGER", 1, 0),
            ("context_sha256", "TEXT", 1, 0), ("commentary_plan_sha256", "TEXT", 1, 0),
            ("proposal_sha256", "TEXT", 1, 0), ("review_revision", "INTEGER", 1, 0),
            ("previous_review_sha256", "TEXT", 0, 0), ("decision", "TEXT", 1, 0),
            ("authority_binding_sha256", "TEXT", 1, 0), ("confirmation_sha256", "TEXT", 1, 0),
            ("reviewed_at", "TEXT", 1, 0), ("payload_json", "TEXT", 1, 0),
            ("payload_sha256", "TEXT", 1, 0),
        )
        info = tuple(conn.execute("PRAGMA table_info(dbd_reasoning_human_reviews)"))
        if tuple((row[1], row[2].upper(), row[3], row[5]) for row in info) != expected:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 review table shape is invalid", ProductErrorCategory.DATA_INTEGRITY)
        foreign_rows = tuple(conn.execute("PRAGMA foreign_key_list(dbd_reasoning_human_reviews)"))
        grouped: dict[int, list[sqlite3.Row]] = {}
        for row in foreign_rows:
            grouped.setdefault(row[0], []).append(row)
        foreign = {
            (
                rows[0][2], tuple((row[3], row[4]) for row in sorted(rows, key=lambda item: item[1])),
                rows[0][5], rows[0][6], rows[0][7],
            )
            for rows in grouped.values()
        }
        required_foreign = {
            ("dbd_reasoning_candidate_lineage", (("root_candidate_id", "candidate_id"),), "NO ACTION", "NO ACTION", "NONE"),
            ("dbd_reasoning_candidate_lineage", (("leaf_candidate_id", "candidate_id"),), "NO ACTION", "NO ACTION", "NONE"),
            ("dbd_reasoning_human_reviews", (("root_candidate_id", "root_candidate_id"), ("previous_review_sha256", "review_sha256")), "NO ACTION", "NO ACTION", "NONE"),
        }
        if foreign != required_foreign:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 review foreign keys are invalid", ProductErrorCategory.DATA_INTEGRITY)
        indexes = tuple(conn.execute("PRAGMA index_list(dbd_reasoning_human_reviews)"))
        shapes = {
            (row[1], bool(row[2]), CommentaryCandidateStore._index_columns(conn, row[1]))
            for row in indexes
        }
        named = {name: columns for name, unique, columns in shapes if not unique}
        if named != {
            "dbd_reasoning_review_root_lookup": ("root_candidate_id", "review_revision", "review_sha256"),
            "dbd_reasoning_review_event_lookup": ("event_id", "event_revision", "root_candidate_id"),
        } or any(row[4] != 0 for row in indexes):
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 review indexes are invalid", ProductErrorCategory.DATA_INTEGRITY)
        unique_columns = {columns for _, unique, columns in shapes if unique}
        if unique_columns != {
            ("review_sha256",), ("confirmation_sha256",),
            ("root_candidate_id", "review_revision"),
            ("root_candidate_id", "previous_review_sha256"),
            ("root_candidate_id", "review_sha256"),
        }:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 review uniqueness is invalid", ProductErrorCategory.DATA_INTEGRITY)
        root_signature = CommentaryCandidateStore._index_signature(conn, "dbd_reasoning_review_root_lookup")
        event_signature = CommentaryCandidateStore._index_signature(conn, "dbd_reasoning_review_event_lookup")
        if root_signature != (("root_candidate_id", False), ("review_revision", True), ("review_sha256", False)) or event_signature != (("event_id", False), ("event_revision", False), ("root_candidate_id", False)):
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary v3 review index ordering is invalid", ProductErrorCategory.DATA_INTEGRITY)

    @staticmethod
    def _index_columns(conn: sqlite3.Connection, name: str) -> tuple[str, ...]:
        if not isinstance(name, str) or "'" in name:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary index name is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return tuple(row[2] for row in conn.execute(f"PRAGMA index_xinfo('{name}')") if row[1] >= 0)

    @staticmethod
    def _index_signature(conn: sqlite3.Connection, name: str) -> tuple[tuple[str, bool], ...]:
        if not isinstance(name, str) or "'" in name:
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary index name is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return tuple((row[2], bool(row[3])) for row in conn.execute(f"PRAGMA index_xinfo('{name}')") if row[1] >= 0)

    @staticmethod
    def _validate_candidate_schema(conn: sqlite3.Connection) -> None:
        expected = (
            ("candidate_id", "TEXT", 0, 1), ("match_id", "TEXT", 1, 0), ("event_id", "TEXT", 1, 0),
            ("event_revision", "INTEGER", 1, 0), ("status", "TEXT", 1, 0), ("payload_json", "TEXT", 1, 0),
            ("payload_sha256", "TEXT", 1, 0), ("created_at", "TEXT", 1, 0),
        )
        info = tuple(conn.execute("PRAGMA table_info(commentary_candidates)"))
        event_index = tuple(row[2] for row in conn.execute("PRAGMA index_info(commentary_event_lookup)"))
        if tuple((row[1], row[2].upper(), row[3], row[5]) for row in info) != expected or event_index != ("event_id", "event_revision", "created_at", "candidate_id"):
            raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary candidate table shape is invalid", ProductErrorCategory.DATA_INTEGRITY)

    @staticmethod
    def _audit_candidate_rows(conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT payload_json,payload_sha256,match_id,event_id,event_revision,status,created_at,candidate_id FROM commentary_candidates").fetchall()
        for row in rows:
            try:
                payload = json.loads(row[0])
                _verify_commentary_candidate_payload(payload)
                if (
                    row[1] != payload.get("commentary_candidate_sha256")
                    or (row[2], row[3], row[4], row[5], row[6], row[7])
                    != (payload.get("match_id"), payload.get("event_id"), payload.get("event_revision"), payload.get("status"), payload.get("created_at"), payload.get("candidate_id"))
                ):
                    raise ValueError("candidate columns do not match payload")
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ProductError("ERR_COMMENTARY_STORE_RECORD_INVALID", "Stored Commentary candidate canonical payload/hash is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def _audit_reasoning_lineage_rows(conn: sqlite3.Connection) -> None:
        from .dbd_reasoning_candidate_lineage import admit_reasoning_candidate_lineage_record
        from .dbd_reasoning_human_review import HumanReviewDecision, admit_reasoning_human_review_record
        if tuple(conn.execute("PRAGMA foreign_key_check")):
            raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Stored reasoning Candidate lineage foreign key is invalid", ProductErrorCategory.DATA_INTEGRITY)
        rows = conn.execute(
            "SELECT l.candidate_id,l.parent_candidate_id,l.match_id,l.event_id,l.event_revision,l.context_sha256,l.commentary_plan_sha256,l.structural_body_sha256,l.proposal_sha256,l.payload_json,l.payload_sha256,c.payload_json FROM dbd_reasoning_candidate_lineage l JOIN commentary_candidates c ON c.candidate_id=l.candidate_id"
        ).fetchall()
        admitted: dict[str, Any] = {}
        candidates: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            try:
                lineage = json.loads(row[9])
                candidate = json.loads(row[11])
                proposal = lineage.get("proposal") if isinstance(lineage, Mapping) else None
                proposal_sha256 = proposal.get("proposal_sha256") if isinstance(proposal, Mapping) else None
                if (
                    (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[10])
                    != (
                        lineage.get("candidate_id"), lineage.get("parent_candidate_id"), lineage.get("match_id"),
                        lineage.get("event_id"), lineage.get("event_revision"), lineage.get("context_sha256"),
                        lineage.get("commentary_plan_sha256"), lineage.get("structural_body_sha256"),
                        proposal_sha256, lineage.get("lineage_sha256"),
                    )
                ):
                    raise ValueError("lineage columns do not match payload")
                admitted_lineage = admit_reasoning_candidate_lineage_record(lineage, candidate_payload=candidate)
                admitted[admitted_lineage.candidate_id] = admitted_lineage
                candidates[admitted_lineage.candidate_id] = candidate
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Stored reasoning Candidate lineage is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        correction_submission_refs: set[str] = set()
        correction_submission_bindings: set[str] = set()
        for candidate_id, lineage in admitted.items():
            if lineage.parent_candidate_id is None:
                continue
            parent = admitted.get(lineage.parent_candidate_id)
            if parent is None or candidates[lineage.parent_candidate_id].get("commentary_candidate_sha256") != lineage.parent_candidate_sha256:
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage parent is invalid", ProductErrorCategory.DATA_INTEGRITY)
            if (parent.match_id, parent.event_id, parent.event_revision, parent.context_sha256, parent.commentary_plan_sha256) != (
                lineage.match_id, lineage.event_id, lineage.event_revision, lineage.context_sha256, lineage.commentary_plan_sha256,
            ):
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage coordinates cross parent", ProductErrorCategory.DATA_INTEGRITY)
            review_row = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE review_sha256=?", (lineage.correction_request_review_sha256,)).fetchone()
            try:
                review = None if review_row is None else admit_reasoning_human_review_record(json.loads(review_row[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage review is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
            if (
                review is None or review.decision is not HumanReviewDecision.REVISE
                or review.root_candidate_id != lineage.parent_candidate_id
                or review.leaf_candidate_id != lineage.parent_candidate_id
                or review.correction_request_sha256 is None
                or review.review_sha256 != lineage.correction_request_review_sha256
            ):
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage does not bind a REVISE review", ProductErrorCategory.DATA_INTEGRITY)
            if (
                lineage.correction_submission_ref in correction_submission_refs
                or lineage.correction_submission_binding_sha256 in correction_submission_bindings
            ):
                raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction submission is reused by multiple lineages", ProductErrorCategory.DATA_INTEGRITY)
            correction_submission_refs.add(lineage.correction_submission_ref)
            correction_submission_bindings.add(lineage.correction_submission_binding_sha256)
        for candidate_id in admitted:
            seen: set[str] = set()
            cursor = candidate_id
            depth = 0
            while admitted[cursor].parent_candidate_id is not None:
                if cursor in seen or depth >= 16:
                    raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage graph is cyclic or too deep", ProductErrorCategory.DATA_INTEGRITY)
                seen.add(cursor)
                parent_id = admitted[cursor].parent_candidate_id
                assert parent_id is not None
                if parent_id not in admitted:
                    raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Correction lineage parent is missing", ProductErrorCategory.DATA_INTEGRITY)
                cursor = parent_id
                depth += 1

    @staticmethod
    def _audit_human_review_rows(conn: sqlite3.Connection) -> None:
        from .dbd_reasoning_human_review import admit_reasoning_human_review_record
        if tuple(conn.execute("PRAGMA foreign_key_check")):
            raise ProductError("ERR_COMMENTARY_REASONING_REVIEW_INVALID", "Stored reasoning Human review foreign key is invalid", ProductErrorCategory.DATA_INTEGRITY)
        rows = conn.execute("SELECT review_sha256,root_candidate_id,leaf_candidate_id,leaf_candidate_sha256,leaf_lineage_sha256,match_id,event_id,event_revision,context_sha256,commentary_plan_sha256,proposal_sha256,review_revision,previous_review_sha256,decision,authority_binding_sha256,confirmation_sha256,reviewed_at,payload_json,payload_sha256 FROM dbd_reasoning_human_reviews ORDER BY root_candidate_id,review_revision").fetchall()
        heads: dict[str, tuple[int, str]] = {}
        for row in rows:
            try:
                payload = json.loads(row[17])
                review = admit_reasoning_human_review_record(payload)
                expected = (
                    review.review_sha256, review.root_candidate_id, review.leaf_candidate_id,
                    review.leaf_candidate_sha256, review.leaf_lineage_sha256, review.match_id,
                    review.event_id, review.event_revision, review.context_sha256,
                    review.commentary_plan_sha256, review.proposal_sha256, review.review_revision,
                    review.previous_review_sha256, review.decision.value,
                    review.authority_binding_sha256, review.confirmation_sha256,
                    review.reviewed_at, review.review_sha256,
                )
                if tuple(row[:17]) + (row[18],) != expected:
                    raise ValueError("review columns do not match payload")
                owner = conn.execute("SELECT c.payload_sha256,l.payload_sha256,l.match_id,l.event_id,l.event_revision,l.context_sha256,l.commentary_plan_sha256,l.proposal_sha256 FROM commentary_candidates c JOIN dbd_reasoning_candidate_lineage l ON l.candidate_id=c.candidate_id WHERE c.candidate_id=?", (review.leaf_candidate_id,)).fetchone()
                if owner is None or (
                    review.leaf_candidate_sha256, review.leaf_lineage_sha256,
                    review.match_id, review.event_id, review.event_revision,
                    review.context_sha256, review.commentary_plan_sha256, review.proposal_sha256,
                ) != tuple(owner):
                    raise ValueError("review coordinates cross Candidate/lineage owner")
                previous = heads.get(review.root_candidate_id)
                if review.review_revision == 1:
                    if previous is not None or review.previous_review_sha256 is not None:
                        raise ValueError("review chain root is invalid")
                elif previous != (review.review_revision - 1, review.previous_review_sha256):
                    raise ValueError("review chain is not contiguous")
                heads[review.root_candidate_id] = (review.review_revision, review.review_sha256)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ProductError("ERR_COMMENTARY_REASONING_REVIEW_INVALID", "Stored reasoning Human review is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc

    def _configure_reasoning_review_current_resolver(self, registration: Any, resolver: Any) -> None:
        from .dbd_reasoning_human_review_application import _valid_registration
        if not _valid_registration(registration, self):
            raise ProductError("ERR_DBD_REVIEW_INTERNAL_AUTHORITY", "Human review Application registration is invalid", ProductErrorCategory.AUTHORIZATION)
        if not callable(getattr(resolver, "resolve", None)):
            raise TypeError("reasoning review current resolver is invalid")
        if self._reasoning_review_current_resolver is not None and self._reasoning_review_current_resolver is not resolver:
            raise ProductError("ERR_DBD_REVIEW_RESOLVER_CONFLICT", "Reasoning review current resolver is already configured", ProductErrorCategory.STATE)
        self._reasoning_review_current_resolver = resolver

    def _append_resolved_human_review(self, *, token: Any, authority: Any, current: Any, expected_head: Any, evaluated_at: str) -> Any:
        from .dbd_reasoning_human_review import (
            CurrentHumanReviewSnapshot, DbDReasoningHumanReviewAuthorityBinding,
            admit_human_review, admit_reasoning_human_review_record,
        )
        from .dbd_reasoning_human_review_application import HumanReviewAppendResult, HumanReviewHeadExpectation, _valid_admission_token
        if not isinstance(authority, DbDReasoningHumanReviewAuthorityBinding) or not isinstance(current, CurrentHumanReviewSnapshot) or not isinstance(expected_head, HumanReviewHeadExpectation):
            raise TypeError("resolved Human review inputs are invalid")
        if not _valid_admission_token(token, self, authority, current, evaluated_at):
            raise ProductError("ERR_DBD_REVIEW_INTERNAL_AUTHORITY", "Human review Application admission token is invalid", ProductErrorCategory.AUTHORIZATION)
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._audit_candidate_rows(conn)
                self._audit_reasoning_lineage_rows(conn)
                self._audit_human_review_rows(conn)
                row = conn.execute("SELECT c.payload_json,l.payload_json FROM commentary_candidates c JOIN dbd_reasoning_candidate_lineage l ON l.candidate_id=c.candidate_id WHERE c.candidate_id=?", (current.root_candidate_id,)).fetchone()
                if row is None or canonical_json_bytes(current.leaf_candidate.to_dict()).decode("utf-8") != row[0] or canonical_json_bytes(current.leaf_lineage.to_dict()).decode("utf-8") != row[1]:
                    raise ProductError("ERR_DBD_REVIEW_CURRENT_CROSSING", "Resolved current Candidate/lineage does not match Store", ProductErrorCategory.DATA_INTEGRITY)
                head_row = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE root_candidate_id=? ORDER BY review_revision DESC LIMIT 1", (current.root_candidate_id,)).fetchone()
                previous = None if head_row is None else admit_reasoning_human_review_record(json.loads(head_row[0]))
                actual_revision = 0 if previous is None else previous.review_revision
                actual_sha = None if previous is None else previous.review_sha256
                existing_confirmation = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE confirmation_sha256=?", (authority.confirmation_sha256,)).fetchone()
                if existing_confirmation is not None:
                    stored = admit_reasoning_human_review_record(json.loads(existing_confirmation[0]))
                    retry_previous_row = None if authority.expected_previous_review_sha256 is None else conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE review_sha256=?", (authority.expected_previous_review_sha256,)).fetchone()
                    retry_previous = None if retry_previous_row is None else admit_reasoning_human_review_record(json.loads(retry_previous_row[0]))
                    retry_current = CurrentHumanReviewSnapshot(
                        current.root_candidate_id, current.leaf_candidate, current.leaf_lineage,
                        current.context, current.plan, authority.expected_previous_review_revision,
                        authority.expected_previous_review_sha256,
                    )
                    retry_admitted = admit_human_review(
                        authority_record=authority.to_dict(), current=retry_current,
                        previous_review=retry_previous, evaluated_at=authority.decided_at,
                    )
                    if retry_admitted.passed and retry_admitted.review_record == stored:
                        conn.commit()
                        return HumanReviewAppendResult("IDEMPOTENT_EXISTING", stored)
                    raise ProductError("ERR_DBD_REVIEW_CONFIRMATION_REPLAY", "Human confirmation was already consumed by different review content", ProductErrorCategory.AUTHORIZATION)
                if (expected_head.revision, expected_head.review_sha256) != (actual_revision, actual_sha):
                    raise ProductError("ERR_DBD_REVIEW_HEAD_CONFLICT", "Reasoning review head changed", ProductErrorCategory.STATE)
                trusted = CurrentHumanReviewSnapshot(
                    current.root_candidate_id, current.leaf_candidate, current.leaf_lineage,
                    current.context, current.plan, actual_revision, actual_sha,
                )
                admitted = admit_human_review(
                    authority_record=authority.to_dict(), current=trusted,
                    previous_review=previous, evaluated_at=evaluated_at,
                )
                if not admitted.passed or admitted.review_record is None:
                    raise ProductError("ERR_DBD_REVIEW_ADMISSION_REJECTED", ",".join(admitted.error_codes), ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
                review = admitted.review_record
                text = canonical_json_bytes(review.to_dict()).decode("utf-8")
                conn.execute("INSERT INTO dbd_reasoning_human_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    review.review_sha256, review.root_candidate_id, review.leaf_candidate_id,
                    review.leaf_candidate_sha256, review.leaf_lineage_sha256, review.match_id,
                    review.event_id, review.event_revision, review.context_sha256,
                    review.commentary_plan_sha256, review.proposal_sha256, review.review_revision,
                    review.previous_review_sha256, review.decision.value, review.authority_binding_sha256,
                    review.confirmation_sha256, review.reviewed_at, text, review.review_sha256,
                ))
                self._audit_human_review_rows(conn)
                conn.commit()
                return HumanReviewAppendResult("APPENDED", review)
            except Exception:
                conn.rollback()
                raise

    def _append_resolved_human_correction(
        self, *, token: Any, submission: Any, current: Any, child_candidate: Any,
        child_lineage: Any, expected_review_head: Any, evaluated_at: str,
    ) -> Any:
        """Private C3 capability route; public bundle append deliberately rejects children."""
        from .dbd_reasoning_candidate_lineage import DbDReasoningCandidateLineage, admit_reasoning_candidate_lineage_record
        from .dbd_reasoning_human_correction_application import (
            DbDReasoningHumanCorrectionSubmission, HumanCorrectionAppendResult,
            _utc, _valid_correction_token, admit_reasoning_human_correction_submission,
        )
        from .dbd_reasoning_human_review import CurrentHumanReviewSnapshot, HumanReviewDecision, admit_reasoning_human_review_record
        from .dbd_reasoning_human_review_application import HumanReviewHeadExpectation
        if (
            not isinstance(submission, DbDReasoningHumanCorrectionSubmission)
            or not isinstance(current, CurrentHumanReviewSnapshot)
            or not isinstance(child_candidate, CommentaryCandidate)
            or not isinstance(child_lineage, DbDReasoningCandidateLineage)
            or not isinstance(expected_review_head, HumanReviewHeadExpectation)
        ):
            raise TypeError("resolved Human correction inputs are invalid")
        try:
            admitted_submission = admit_reasoning_human_correction_submission(submission.to_dict())
            trusted_current = CurrentHumanReviewSnapshot(
                current.root_candidate_id, current.leaf_candidate, current.leaf_lineage,
                current.context, current.plan, current.review_head_revision, current.review_head_sha256,
            )
            if submission.to_dict() != admitted_submission.to_dict() or _utc(evaluated_at, "evaluated_at") < _utc(admitted_submission.submitted_at, "submitted_at") or _utc(admitted_submission.expires_at, "expires_at") <= _utc(evaluated_at, "evaluated_at"):
                raise ValueError("correction submission is stale or noncanonical")
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_DBD_CORRECTION_SUBMISSION_INVALID", "Resolved Human correction submission is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not _valid_correction_token(token, self, admitted_submission, trusted_current, evaluated_at):
            raise ProductError("ERR_DBD_CORRECTION_INTERNAL_AUTHORITY", "Human correction Application admission token is invalid", ProductErrorCategory.AUTHORIZATION)
        submission, current = admitted_submission, trusted_current
        if (
            child_lineage.origin != "TUNED_REASONING_CORRECTION"
            or child_lineage.parent_candidate_id != current.root_candidate_id
            or child_lineage.parent_candidate_sha256 != submission.parent_candidate_sha256
            or child_lineage.correction_request_review_sha256 != submission.correction_review_sha256
            or child_lineage.correction_submission_ref != submission.correction_ref
            or child_lineage.correction_submission_binding_sha256 != submission.binding_sha256
            or child_lineage.raw_output_sha256 != submission.edited_output_sha256
            or child_candidate.candidate_id != submission.child_candidate_id
            or child_candidate.created_at != submission.child_created_at
        ):
            raise ProductError("ERR_DBD_CORRECTION_CROSSING", "Human correction child crosses its trusted binding", ProductErrorCategory.DATA_INTEGRITY)
        child_payload, lineage_payload = child_candidate.to_dict(), child_lineage.to_dict()
        admit_reasoning_candidate_lineage_record(lineage_payload, candidate_payload=child_payload)
        child_text, lineage_text = canonical_json_bytes(child_payload).decode("utf-8"), canonical_json_bytes(lineage_payload).decode("utf-8")
        parent_text, parent_lineage_text = canonical_json_bytes(current.leaf_candidate.to_dict()).decode("utf-8"), canonical_json_bytes(current.leaf_lineage.to_dict()).decode("utf-8")
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._audit_candidate_rows(conn)
                self._audit_reasoning_lineage_rows(conn)
                self._audit_human_review_rows(conn)
                parent = conn.execute(
                    "SELECT c.payload_json,l.payload_json FROM commentary_candidates c JOIN dbd_reasoning_candidate_lineage l ON l.candidate_id=c.candidate_id WHERE c.candidate_id=?",
                    (current.root_candidate_id,),
                ).fetchone()
                if parent is None or tuple(parent) != (parent_text, parent_lineage_text):
                    raise ProductError("ERR_DBD_CORRECTION_CURRENT_CROSSING", "Resolved correction parent does not match Store", ProductErrorCategory.DATA_INTEGRITY)
                head_row = conn.execute(
                    "SELECT payload_json FROM dbd_reasoning_human_reviews WHERE root_candidate_id=? ORDER BY review_revision DESC LIMIT 1",
                    (current.root_candidate_id,),
                ).fetchone()
                actual = None if head_row is None else admit_reasoning_human_review_record(json.loads(head_row[0]))
                actual_head = (0, None) if actual is None else (actual.review_revision, actual.review_sha256)
                if (expected_review_head.revision, expected_review_head.review_sha256) != actual_head:
                    raise ProductError("ERR_DBD_CORRECTION_HEAD_CONFLICT", "Reasoning correction review head changed", ProductErrorCategory.STATE)
                if (
                    actual is None or actual.decision is not HumanReviewDecision.REVISE
                    or actual.review_sha256 != submission.correction_review_sha256
                    or actual.correction_request_sha256 != submission.correction_request_sha256
                    or actual.root_candidate_id != current.root_candidate_id
                    or actual.leaf_candidate_id != current.root_candidate_id
                    or _utc(submission.submitted_at, "submitted_at") < _utc(actual.reviewed_at, "reviewed_at")
                    or (actual.context_sha256, actual.commentary_plan_sha256, actual.proposal_sha256)
                    != (submission.context_sha256, submission.commentary_plan_sha256, submission.proposal_sha256)
                ):
                    raise ProductError("ERR_DBD_CORRECTION_REVISE_REQUIRED", "Current Human review is not the bound REVISE request", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
                if (current.review_head_revision, current.review_head_sha256) != actual_head:
                    raise ProductError("ERR_DBD_CORRECTION_CURRENT_CROSSING", "Resolved correction review head crosses Store", ProductErrorCategory.DATA_INTEGRITY)
                existing_child = conn.execute(
                    "SELECT c.payload_json,l.payload_json FROM dbd_reasoning_candidate_lineage l JOIN commentary_candidates c ON c.candidate_id=l.candidate_id WHERE l.parent_candidate_id=?",
                    (current.root_candidate_id,),
                ).fetchone()
                if existing_child is not None:
                    if tuple(existing_child) == (child_text, lineage_text):
                        conn.commit()
                        return HumanCorrectionAppendResult("IDEMPOTENT_EXISTING", child_candidate, child_lineage, submission)
                    raise ProductError("ERR_DBD_CORRECTION_BRANCH_CONFLICT", "Correction parent already has a different child", ProductErrorCategory.DATA_INTEGRITY)
                conflict = conn.execute("SELECT 1 FROM commentary_candidates WHERE candidate_id=?", (child_candidate.candidate_id,)).fetchone()
                if conflict is not None:
                    raise ProductError("ERR_DBD_CORRECTION_CHILD_CONFLICT", "Correction child Candidate identity already exists", ProductErrorCategory.DATA_INTEGRITY)
                conn.execute(
                    "INSERT INTO commentary_candidates VALUES(?,?,?,?,?,?,?,?)",
                    (child_candidate.candidate_id, child_candidate.plan.match_id, child_candidate.plan.event_id,
                     child_candidate.plan.event_revision, child_candidate.status.value, child_text,
                     child_payload["commentary_candidate_sha256"], child_candidate.created_at),
                )
                conn.execute(
                    "INSERT INTO dbd_reasoning_candidate_lineage VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (child_candidate.candidate_id, child_lineage.parent_candidate_id, child_lineage.match_id,
                     child_lineage.event_id, child_lineage.event_revision, child_lineage.context_sha256,
                     child_lineage.commentary_plan_sha256, child_lineage.structural_body_sha256,
                     child_lineage.proposal.to_dict()["proposal_sha256"], lineage_text, child_lineage.lineage_sha256),
                )
                self._audit_candidate_rows(conn)
                self._audit_reasoning_lineage_rows(conn)
                conn.commit()
                return HumanCorrectionAppendResult("APPENDED", child_candidate, child_lineage, submission)
            except Exception:
                conn.rollback()
                raise

    def get_reasoning_human_review_head(self, root_candidate_id: str) -> dict[str, Any] | None:
        validate_id(root_candidate_id, IdKind.CANDIDATE)
        with closing(self._connect()) as conn:
            self._audit_human_review_rows(conn)
            row = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE root_candidate_id=? ORDER BY review_revision DESC LIMIT 1", (root_candidate_id,)).fetchone()
        return None if row is None else json.loads(row[0])

    def get_reasoning_human_review(self, review_sha256: str) -> dict[str, Any]:
        validate_sha256(review_sha256, field_name="review_sha256")
        with closing(self._connect()) as conn:
            self._audit_human_review_rows(conn)
            row = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE review_sha256=?", (review_sha256,)).fetchone()
        if row is None:
            raise ProductError("ERR_DBD_REVIEW_NOT_FOUND", "Reasoning Human review was not found", ProductErrorCategory.STATE)
        return json.loads(row[0])

    def list_reasoning_human_reviews(self, root_candidate_id: str) -> tuple[dict[str, Any], ...]:
        validate_id(root_candidate_id, IdKind.CANDIDATE)
        with closing(self._connect()) as conn:
            self._audit_human_review_rows(conn)
            rows = conn.execute("SELECT payload_json FROM dbd_reasoning_human_reviews WHERE root_candidate_id=? ORDER BY review_revision", (root_candidate_id,)).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def _approved_reasoning_payloads(self, conn: sqlite3.Connection, *, column: str, identity: str) -> tuple[str, ...]:
        from .dbd_reasoning_human_review import CurrentHumanReviewSnapshot, admit_reasoning_human_review_record
        resolver = self._reasoning_review_current_resolver
        if resolver is None:
            return ()
        if column not in {"event_id", "match_id"}:
            raise ValueError("unsupported reasoning review selection column")
        rows = conn.execute(
            f"SELECT c.payload_json,l.payload_json,r.payload_json FROM commentary_candidates c JOIN dbd_reasoning_candidate_lineage l ON l.candidate_id=c.candidate_id JOIN dbd_reasoning_human_reviews r ON r.root_candidate_id=c.candidate_id WHERE c.{column}=? AND c.status='VALIDATED' AND r.review_revision=(SELECT MAX(r2.review_revision) FROM dbd_reasoning_human_reviews r2 WHERE r2.root_candidate_id=c.candidate_id) AND r.decision='APPROVE' AND NOT EXISTS(SELECT 1 FROM dbd_reasoning_candidate_lineage child WHERE child.parent_candidate_id=c.candidate_id)",
            (identity,),
        ).fetchall()
        admitted: list[str] = []
        for candidate_text, lineage_text, review_text in rows:
            candidate = json.loads(candidate_text)
            lineage = json.loads(lineage_text)
            review = admit_reasoning_human_review_record(json.loads(review_text))
            try:
                current = resolver.resolve(candidate["candidate_id"])
            except Exception:
                continue
            if not isinstance(current, CurrentHumanReviewSnapshot):
                continue
            try:
                CurrentHumanReviewSnapshot(
                    current.root_candidate_id, current.leaf_candidate, current.leaf_lineage,
                    current.context, current.plan, review.review_revision, review.review_sha256,
                )
            except (TypeError, ValueError):
                continue
            if (
                current.root_candidate_id == candidate["candidate_id"]
                and current.leaf_candidate.to_dict() == candidate
                and current.leaf_lineage.to_dict() == lineage
                and review.leaf_candidate_sha256 == candidate["commentary_candidate_sha256"]
                and review.leaf_lineage_sha256 == lineage["lineage_sha256"]
                and review.context_sha256 == current.context.to_dict()["context_sha256"]
                and review.commentary_plan_sha256 == current.plan.to_dict()["commentary_plan_sha256"]
                and (review.match_id, review.event_id, review.event_revision)
                == (lineage["match_id"], lineage["event_id"], lineage["event_revision"])
                and review.proposal_sha256 == lineage["proposal"]["proposal_sha256"]
            ):
                admitted.append(candidate_text)
        return tuple(admitted)

    def append(self, candidate: CommentaryCandidate) -> None:
        if not isinstance(candidate, CommentaryCandidate):
            raise TypeError("candidate must be CommentaryCandidate")
        if candidate.reasoning_lineage_required or candidate.candidate_id.startswith("CAND-R2D"):
            raise ProductError("ERR_COMMENTARY_REASONING_BUNDLE_REQUIRED", "Reasoning Candidate must be appended with its lineage bundle", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        payload = candidate.to_dict()
        text = canonical_json_bytes(payload).decode("utf-8")
        with closing(self._connect()) as conn:
            self._audit_candidate_rows(conn)
            row = conn.execute("SELECT payload_json FROM commentary_candidates WHERE candidate_id=?", (candidate.candidate_id,)).fetchone()
            if row is not None:
                if row[0] == text:
                    return
                raise ProductError("ERR_COMMENTARY_CANDIDATE_CONFLICT", "Commentary candidate ID has different canonical content", ProductErrorCategory.DATA_INTEGRITY)
            conn.execute(
                "INSERT INTO commentary_candidates VALUES(?,?,?,?,?,?,?,?)",
                (candidate.candidate_id, candidate.plan.match_id, candidate.plan.event_id, candidate.plan.event_revision, candidate.status.value, text, payload["commentary_candidate_sha256"], candidate.created_at),
            )
            conn.commit()

    def append_reasoning_bundle(self, candidate: CommentaryCandidate, lineage: Any) -> None:
        """Atomically append the existing Candidate and its admitted R2D lineage."""

        from .dbd_reasoning_candidate_lineage import (
            DbDReasoningCandidateLineage, admit_reasoning_candidate_lineage_record,
        )
        if not isinstance(candidate, CommentaryCandidate) or not isinstance(lineage, DbDReasoningCandidateLineage):
            raise TypeError("reasoning bundle requires CommentaryCandidate and DbDReasoningCandidateLineage")
        if not candidate.reasoning_lineage_required:
            raise ValueError("reasoning bundle candidate must carry the lineage-required marker")
        if lineage.parent_candidate_id is not None or lineage.origin != "TUNED_REASONING":
            raise ProductError("ERR_DBD_CORRECTION_APPLICATION_REQUIRED", "Human correction Candidate must be appended through its Application", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        candidate_payload = candidate.to_dict()
        lineage_payload = lineage.to_dict()
        admit_reasoning_candidate_lineage_record(lineage_payload, candidate_payload=candidate_payload)
        candidate_text = canonical_json_bytes(candidate_payload).decode("utf-8")
        lineage_text = canonical_json_bytes(lineage_payload).decode("utf-8")
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._audit_candidate_rows(conn)
                self._audit_reasoning_lineage_rows(conn)
                candidate_row = conn.execute("SELECT payload_json,payload_sha256 FROM commentary_candidates WHERE candidate_id=?", (candidate.candidate_id,)).fetchone()
                lineage_row = conn.execute("SELECT payload_json,payload_sha256 FROM dbd_reasoning_candidate_lineage WHERE candidate_id=?", (candidate.candidate_id,)).fetchone()
                if candidate_row is not None or lineage_row is not None:
                    if (
                        candidate_row is not None and lineage_row is not None
                        and candidate_row[0] == candidate_text and candidate_row[1] == candidate_payload["commentary_candidate_sha256"]
                        and lineage_row[0] == lineage_text and lineage_row[1] == lineage.lineage_sha256
                    ):
                        conn.commit()
                        return
                    raise ProductError("ERR_COMMENTARY_REASONING_BUNDLE_CONFLICT", "Reasoning Candidate/lineage bundle is partial or conflicting", ProductErrorCategory.DATA_INTEGRITY)
                conn.execute(
                    "INSERT INTO commentary_candidates VALUES(?,?,?,?,?,?,?,?)",
                    (candidate.candidate_id, candidate.plan.match_id, candidate.plan.event_id, candidate.plan.event_revision, candidate.status.value, candidate_text, candidate_payload["commentary_candidate_sha256"], candidate.created_at),
                )
                conn.execute(
                    "INSERT INTO dbd_reasoning_candidate_lineage VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (candidate.candidate_id, lineage.parent_candidate_id, lineage.match_id, lineage.event_id, lineage.event_revision, lineage.context_sha256, lineage.commentary_plan_sha256, lineage.structural_body_sha256, lineage.proposal.to_dict()["proposal_sha256"], lineage_text, lineage.lineage_sha256),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_reasoning_lineage(self, candidate_id: str) -> dict[str, Any]:
        from .dbd_reasoning_candidate_lineage import admit_reasoning_candidate_lineage_record
        validate_id(candidate_id, IdKind.CANDIDATE)
        with closing(self._connect()) as conn:
            self._audit_candidate_rows(conn)
            self._audit_reasoning_lineage_rows(conn)
            row = conn.execute(
                "SELECT c.payload_json,c.payload_sha256,l.payload_json,l.payload_sha256,l.match_id,l.event_id,l.event_revision,l.context_sha256,l.commentary_plan_sha256,l.structural_body_sha256,l.proposal_sha256 FROM commentary_candidates c JOIN dbd_reasoning_candidate_lineage l ON l.candidate_id=c.candidate_id WHERE c.candidate_id=?",
                (candidate_id,),
            ).fetchone()
        if row is None:
            raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_NOT_FOUND", "Reasoning Candidate lineage was not found", ProductErrorCategory.STATE)
        try:
            candidate_payload = json.loads(row[0])
            lineage_payload = json.loads(row[2])
            proposal = lineage_payload.get("proposal") if isinstance(lineage_payload, Mapping) else None
            proposal_sha256 = proposal.get("proposal_sha256") if isinstance(proposal, Mapping) else None
            if (
                row[1] != candidate_payload.get("commentary_candidate_sha256")
                or row[3] != lineage_payload.get("lineage_sha256")
                or (row[4], row[5], row[6], row[7], row[8], row[9], row[10])
                != (
                    lineage_payload.get("match_id"), lineage_payload.get("event_id"), lineage_payload.get("event_revision"),
                    lineage_payload.get("context_sha256"), lineage_payload.get("commentary_plan_sha256"),
                    lineage_payload.get("structural_body_sha256"), proposal_sha256,
                )
            ):
                raise ValueError("stored reasoning lineage columns do not match canonical payload")
            admitted = admit_reasoning_candidate_lineage_record(lineage_payload, candidate_payload=candidate_payload)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_COMMENTARY_REASONING_LINEAGE_INVALID", "Stored reasoning Candidate lineage is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
        return admitted.to_dict()

    def list_for_event(self, event_id: str, *, validated_only: bool = False) -> tuple[dict[str, Any], ...]:
        validate_id(event_id, IdKind.GAME_EVENT)
        with closing(self._connect()) as conn:
            self._audit_reasoning_lineage_rows(conn)
            self._audit_human_review_rows(conn)
            if validated_only:
                self._audit_candidate_rows(conn)
                legacy = [row[0] for row in conn.execute("SELECT c.payload_json FROM commentary_candidates c WHERE c.event_id=? AND c.status='VALIDATED' AND c.candidate_id NOT LIKE 'CAND-R2D%' AND NOT EXISTS(SELECT 1 FROM dbd_reasoning_candidate_lineage l WHERE l.candidate_id=c.candidate_id)", (event_id,)).fetchall()]
                reasoning = list(self._approved_reasoning_payloads(conn, column="event_id", identity=event_id))
                rows = [(text,) for text in sorted(legacy + reasoning, key=lambda text: (json.loads(text)["event_revision"], json.loads(text)["created_at"], json.loads(text)["candidate_id"]))]
            else:
                self._audit_candidate_rows(conn)
                rows = conn.execute("SELECT payload_json FROM commentary_candidates WHERE event_id=? ORDER BY event_revision,created_at,candidate_id", (event_id,)).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row[0])
            try:
                _verify_commentary_candidate_payload(payload)
            except ValueError as exc:
                raise ProductError("ERR_COMMENTARY_STORE_RECORD_INVALID", "Stored Commentary candidate canonical payload/hash is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
            results.append(payload)
        return tuple(results)

    def export_jsonl(self, destination: str | Path, *, match_id: str, validated_only: bool = True) -> Path:
        validate_id(match_id, IdKind.GAME_MATCH)
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            self._audit_candidate_rows(conn)
            self._audit_reasoning_lineage_rows(conn)
            self._audit_human_review_rows(conn)
            if validated_only:
                legacy = [row[0] for row in conn.execute("SELECT c.payload_json FROM commentary_candidates c WHERE c.match_id=? AND c.status='VALIDATED' AND c.candidate_id NOT LIKE 'CAND-R2D%' AND NOT EXISTS(SELECT 1 FROM dbd_reasoning_candidate_lineage l WHERE l.candidate_id=c.candidate_id)", (match_id,)).fetchall()]
                reasoning = list(self._approved_reasoning_payloads(conn, column="match_id", identity=match_id))
                rows = [(text,) for text in sorted(legacy + reasoning, key=lambda text: (json.loads(text)["event_id"], json.loads(text)["event_revision"], json.loads(text)["created_at"], json.loads(text)["candidate_id"]))]
            else:
                rows = conn.execute("SELECT payload_json FROM commentary_candidates WHERE match_id=? ORDER BY event_id,event_revision,created_at,candidate_id", (match_id,)).fetchall()
        lines: list[str] = []
        for row in rows:
            payload = json.loads(row[0])
            try:
                _verify_commentary_candidate_payload(payload)
            except ValueError as exc:
                raise ProductError("ERR_COMMENTARY_STORE_RECORD_INVALID", "Stored Commentary candidate canonical payload/hash is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
            lines.append(canonical_json_bytes(payload).decode("utf-8"))
        content = "".join(line + "\n" for line in lines)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target


__all__ = [
    "CommentaryCandidate",
    "CommentaryCandidateStatus",
    "CommentaryCandidateStore",
    "verify_commentary_candidate_payload",
    "CommentaryClaim",
    "CommentaryClaimKind",
    "CommentaryDisposition",
    "CommentaryDraft",
    "CommentaryFact",
    "CommentaryFactValidator",
    "CommentaryPlan",
    "CommentaryPlanner",
    "FactValidationResult",
]
