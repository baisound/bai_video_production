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
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


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

    def __post_init__(self) -> None:
        validate_id(self.candidate_id, IdKind.CANDIDATE)
        if not isinstance(self.plan, CommentaryPlan) or not isinstance(self.draft, CommentaryDraft) or not isinstance(self.validation, FactValidationResult):
            raise ValueError("candidate requires canonical plan/draft/validation")
        _stable_text(self.created_at, field_name="created_at", maximum=64)

    @property
    def status(self) -> CommentaryCandidateStatus:
        return CommentaryCandidateStatus.VALIDATED if self.validation.passed else CommentaryCandidateStatus.REJECTED

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "1.0.0",
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
        return {**body, "commentary_candidate_sha256": sha256_bytes(canonical_json_bytes(body))}


def _verify_commentary_candidate_payload(payload: Any) -> None:
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("invalid Commentary candidate payload")
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


class CommentaryCandidateStore:
    """Append-only local store/export for provider-neutral Commentary candidates."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ProductError("ERR_COMMENTARY_STORE_PATH_SYMLINK", "Commentary store path must not be a symlink", ProductErrorCategory.SECURITY)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        try:
            with closing(self._connect()) as conn:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if version > 1:
                    raise ProductError("ERR_COMMENTARY_STORE_NEWER_VERSION", "Commentary store uses a newer schema", ProductErrorCategory.DATA_INTEGRITY)
                if version == 0 and tables:
                    raise ProductError("ERR_COMMENTARY_STORE_FOREIGN_SCHEMA", "Existing SQLite is not an admitted Commentary store", ProductErrorCategory.DATA_INTEGRITY)
                if version == 0:
                    conn.executescript(
                        """
                        CREATE TABLE store_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                        CREATE TABLE commentary_candidates(candidate_id TEXT PRIMARY KEY,match_id TEXT NOT NULL,event_id TEXT NOT NULL,event_revision INTEGER NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
                        CREATE INDEX commentary_event_lookup ON commentary_candidates(event_id,event_revision,created_at,candidate_id);
                        """
                    )
                    conn.execute("INSERT INTO store_metadata VALUES('store_format','task049.game-commentary.sqlite')")
                    conn.execute("PRAGMA user_version=1")
                    conn.commit()
                else:
                    metadata = dict(conn.execute("SELECT key,value FROM store_metadata"))
                    if metadata.get("store_format") != "task049.game-commentary.sqlite" or "commentary_candidates" not in tables:
                        raise ProductError("ERR_COMMENTARY_STORE_FORMAT", "Commentary store format is not recognized", ProductErrorCategory.DATA_INTEGRITY)
        except sqlite3.DatabaseError as exc:
            raise ProductError("ERR_COMMENTARY_STORE_CORRUPT", "Commentary SQLite is corrupt or unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc

    def append(self, candidate: CommentaryCandidate) -> None:
        if not isinstance(candidate, CommentaryCandidate):
            raise TypeError("candidate must be CommentaryCandidate")
        payload = candidate.to_dict()
        text = canonical_json_bytes(payload).decode("utf-8")
        with closing(self._connect()) as conn:
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

    def list_for_event(self, event_id: str, *, validated_only: bool = False) -> tuple[dict[str, Any], ...]:
        validate_id(event_id, IdKind.GAME_EVENT)
        with closing(self._connect()) as conn:
            if validated_only:
                rows = conn.execute("SELECT payload_json FROM commentary_candidates WHERE event_id=? AND status='VALIDATED' ORDER BY event_revision,created_at,candidate_id", (event_id,)).fetchall()
            else:
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
            if validated_only:
                rows = conn.execute("SELECT payload_json FROM commentary_candidates WHERE match_id=? AND status='VALIDATED' ORDER BY event_id,event_revision,created_at,candidate_id", (match_id,)).fetchall()
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
