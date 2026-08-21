"""TASK-054 R1 pure assembly for DbD tuned-reasoning context.

The assembler is deliberately a boundary adapter.  It neither loads a model nor
consults a store: callers must provide already-admitted CGEL, Knowledge and RAG
records.  Invalid or incompatible inputs fail closed before a context can be
constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameKnowledgeKind,
    GameKnowledgeRef,
    GameMatch,
)
from .dbd_commentary_knowledge import DBDTriviaEntry, TriviaStatus
from .dbd_perk_knowledge import DBDPatchVersion
from .dbd_perk_knowledge import PerkEnvironment
from .dbd_reasoning_contracts import (
    ContextFreshness,
    DbDReasoningContextEnvelope,
    RagChunk,
    ReasoningFact,
    ReasoningSessionMode,
)
from .game_commentary import CommentaryClaimKind, CommentaryDisposition, CommentaryPlan
from .game_event_evidence import GameEvidence
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_ADMITTED_REVIEW_STATUSES = frozenset((
    EventReviewStatus.AUTO_ACCEPTED,
    EventReviewStatus.HUMAN_APPROVED,
    EventReviewStatus.HUMAN_CORRECTED,
))
_MAX_ENVELOPE_EVIDENCE_REFS = 128
_MAX_ENVELOPE_KNOWLEDGE_REFS = 128
_MAX_ENVELOPE_RAG_CHUNKS = 16


@dataclass(frozen=True, slots=True)
class DbDReasoningContextPolicy:
    """Bounded, immutable admission policy for one reasoning-context route."""

    locale: str
    max_evidence_refs: int = 16
    max_knowledge_refs: int = 16
    max_rag_chunks: int = 8
    max_speech_budget_ms: int = 15_000
    allowed_session_modes: tuple[ReasoningSessionMode, ...] = (
        ReasoningSessionMode.PREVIEW_NO_LEARNING,
        ReasoningSessionMode.LEARNING,
    )
    require_human_or_auto_admitted_review: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.locale, str) or not self.locale or len(self.locale) > 16:
            raise ValueError("locale must be a bounded non-empty locale")
        # The envelope remains the final locale validator; this makes the
        # policy reject obviously non-canonical values before assembly.
        parts = self.locale.split("-", 1)
        if not (2 <= len(parts[0]) <= 3 and parts[0].islower() and parts[0].isalpha()):
            raise ValueError("locale must be a canonical locale")
        if len(parts) == 2 and not (len(parts[1]) == 2 and parts[1].isupper() and parts[1].isalpha()):
            raise ValueError("locale must be a canonical locale")
        for name, maximum in (
            ("max_evidence_refs", _MAX_ENVELOPE_EVIDENCE_REFS),
            ("max_knowledge_refs", _MAX_ENVELOPE_KNOWLEDGE_REFS),
            ("max_rag_chunks", _MAX_ENVELOPE_RAG_CHUNKS),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
                raise ValueError(f"{name} must be 0..{maximum}")
        if (
            isinstance(self.max_speech_budget_ms, bool)
            or not isinstance(self.max_speech_budget_ms, int)
            or not 0 <= self.max_speech_budget_ms <= 30_000
        ):
            raise ValueError("max_speech_budget_ms must be 0..30000")
        if not isinstance(self.allowed_session_modes, tuple) or not self.allowed_session_modes:
            raise ValueError("allowed_session_modes must be a non-empty tuple")
        if any(not isinstance(mode, ReasoningSessionMode) for mode in self.allowed_session_modes):
            raise ValueError("allowed_session_modes must contain ReasoningSessionMode values")
        if len(set(self.allowed_session_modes)) != len(self.allowed_session_modes):
            raise ValueError("allowed_session_modes must be unique")
        if self.require_human_or_auto_admitted_review is not True:
            raise ValueError("require_human_or_auto_admitted_review must be true")

    def to_dict(self) -> dict[str, object]:
        return {
            "locale": self.locale,
            "max_evidence_refs": self.max_evidence_refs,
            "max_knowledge_refs": self.max_knowledge_refs,
            "max_rag_chunks": self.max_rag_chunks,
            "max_speech_budget_ms": self.max_speech_budget_ms,
            "allowed_session_modes": sorted(mode.value for mode in self.allowed_session_modes),
            "require_human_or_auto_admitted_review": self.require_human_or_auto_admitted_review,
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningRagResult:
    """An admitted RAG result with retrieval coordinates and auxiliary lineage.

    ``RagChunk`` deliberately carries only untrusted display data.  This wrapper
    supplies the environment, retrieval snapshot and auxiliary-knowledge digest
    required to admit that data into a DbD reasoning request.
    """

    chunk: RagChunk
    environment: GameEnvironment
    source_revision: str
    retrieval_snapshot_sha256: str
    auxiliary_knowledge_sha256s: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.chunk, RagChunk):
            raise ValueError("chunk must be RagChunk")
        if self.environment not in {GameEnvironment.LIVE, GameEnvironment.PTB}:
            raise ValueError("RAG environment must be LIVE or PTB")
        if not isinstance(self.source_revision, str) or not self.source_revision.strip() or len(self.source_revision) > 128:
            raise ValueError("source_revision must be a bounded non-empty string")
        validate_sha256(self.retrieval_snapshot_sha256, field_name="retrieval_snapshot_sha256")
        if self.auxiliary_knowledge_sha256s != tuple(sorted(set(self.auxiliary_knowledge_sha256s))):
            raise ValueError("auxiliary_knowledge_sha256s must be unique and canonically sorted")
        for value in self.auxiliary_knowledge_sha256s:
            validate_sha256(value, field_name="auxiliary_knowledge_sha256")

    def to_context_coordinates(self) -> dict[str, object]:
        return {
            "source_ref": self.chunk.source_ref,
            "content_sha256": self.chunk.content_sha256,
            "environment": self.environment.value,
            "source_revision": self.source_revision,
            "retrieval_snapshot_sha256": self.retrieval_snapshot_sha256,
            "auxiliary_knowledge_sha256s": list(self.auxiliary_knowledge_sha256s),
        }


class DbDReasoningContextAssembler:
    """Build a fresh, replayable envelope from exact already-admitted inputs."""

    def assemble(
        self,
        *,
        event: CanonicalGameEvent,
        match: GameMatch,
        commentary_plan: CommentaryPlan,
        evidence_by_id: Mapping[str, GameEvidence],
        evidence_sha256_by_id: Mapping[str, str],
        current_evidence_sha256_by_id: Mapping[str, str],
        knowledge_refs: Sequence[GameKnowledgeRef],
        trivia_entries: Sequence[DBDTriviaEntry],
        rag_results: Sequence[DbDReasoningRagResult],
        policy: DbDReasoningContextPolicy,
        current_event_revision: int,
        current_event_sha256: str,
        timeline_sha256: str,
        current_timeline_sha256: str,
        session_mode: ReasoningSessionMode,
        speech_budget_ms: int,
        style_profile_ref: str,
    ) -> DbDReasoningContextEnvelope:
        if not isinstance(event, CanonicalGameEvent):
            raise TypeError("event must be CanonicalGameEvent")
        if not isinstance(match, GameMatch):
            raise TypeError("match must be GameMatch")
        if not isinstance(commentary_plan, CommentaryPlan):
            raise TypeError("commentary_plan must be CommentaryPlan")
        if not isinstance(policy, DbDReasoningContextPolicy):
            raise TypeError("policy must be DbDReasoningContextPolicy")
        if not isinstance(evidence_by_id, Mapping):
            raise TypeError("evidence_by_id must be a Mapping")
        if not isinstance(session_mode, ReasoningSessionMode):
            raise ValueError("session_mode must be ReasoningSessionMode")
        validate_sha256(current_event_sha256, field_name="current_event_sha256")
        validate_sha256(timeline_sha256, field_name="timeline_sha256")
        validate_sha256(current_timeline_sha256, field_name="current_timeline_sha256")
        if isinstance(current_event_revision, bool) or not isinstance(current_event_revision, int) or current_event_revision < 1:
            raise ValueError("current_event_revision must be positive")
        event_sha256 = event.to_dict()["event_sha256"]
        if (event.revision, event_sha256) != (current_event_revision, current_event_sha256):
            raise ValueError("event is stale against current event coordinates")
        if timeline_sha256 != current_timeline_sha256:
            raise ValueError("timeline is stale against current timeline coordinates")

        self._validate_event_and_plan(event, match, commentary_plan, policy)
        if session_mode not in policy.allowed_session_modes:
            raise ValueError("session_mode is not allowed by policy")
        if isinstance(speech_budget_ms, bool) or not isinstance(speech_budget_ms, int) or not 0 <= speech_budget_ms <= policy.max_speech_budget_ms:
            raise ValueError("speech_budget_ms exceeds the policy bound")

        evidence_refs, evidence_sha256s = self._validate_evidence(
            event, match, evidence_by_id, evidence_sha256_by_id, current_evidence_sha256_by_id, policy,
        )
        evidence_snapshot_sha256 = self._evidence_snapshot_sha256(evidence_refs, evidence_sha256s)
        rag_rows = self._validate_rag(event, rag_results, policy)
        chunks = tuple(row.chunk for row in rag_rows)
        rag_snapshot_sha256 = self._rag_snapshot_sha256(rag_rows)
        knowledge_sha256s = self._validate_knowledge(
            event, commentary_plan, knowledge_refs, trivia_entries, rag_rows, policy,
        )
        observed_facts, canonical_facts = self._bridge_facts(event, commentary_plan)

        context_id = self._context_id(
            event_sha256=event_sha256,
            timeline_sha256=timeline_sha256,
            commentary_plan_sha256=commentary_plan.to_dict()["commentary_plan_sha256"],
            evidence_sha256s=evidence_sha256s,
            evidence_snapshot_sha256=evidence_snapshot_sha256,
            knowledge_ref_sha256s=knowledge_sha256s,
            game_environment=event.environment.value,
            rag_snapshot_sha256=rag_snapshot_sha256,
            session_mode=session_mode,
            speech_budget_ms=speech_budget_ms,
            style_profile_ref=style_profile_ref,
            policy=policy.to_dict(),
        )
        envelope = DbDReasoningContextEnvelope(
            context_id=context_id,
            match_id=event.match_id,
            event_id=event.event_id,
            event_revision=event.revision,
            event_sha256=event_sha256,
            timeline_sha256=timeline_sha256,
            game_version=event.game_version,
            game_environment=event.environment,
            rag_snapshot_sha256=rag_snapshot_sha256,
            evidence_snapshot_sha256=evidence_snapshot_sha256,
            session_mode=session_mode,
            freshness=ContextFreshness.CURRENT,
            observed_facts=observed_facts,
            canonical_facts=canonical_facts,
            evidence_refs=evidence_refs,
            knowledge_ref_sha256s=knowledge_sha256s,
            rag_chunks=chunks,
            uncertainties=(),
            forbidden_claims=(),
            speech_budget_ms=speech_budget_ms,
            language=policy.locale,
            style_profile_ref=style_profile_ref,
        )
        # Enforce the canonical 128 KiB envelope limit inside this boundary;
        # callers never receive a non-dispatchable oversized record.
        envelope.to_dict()
        return envelope

    @staticmethod
    def _validate_event_and_plan(
        event: CanonicalGameEvent,
        match: GameMatch,
        plan: CommentaryPlan,
        policy: DbDReasoningContextPolicy,
    ) -> None:
        if event.confirmation_state is not EventConfirmationState.CONFIRMED:
            raise ValueError("event must be CONFIRMED")
        if (
            match.match_id != event.match_id
            or match.game_version != event.game_version
            or match.environment is not event.environment
            or match.perspective is not event.perspective
        ):
            raise ValueError("match coordinates do not exactly match event")
        if event.environment.value == "UNKNOWN":
            raise ValueError("event environment must not be UNKNOWN")
        if event.review_status not in _ADMITTED_REVIEW_STATUSES:
            raise ValueError("event review is not admitted")
        if plan.disposition is not CommentaryDisposition.PROPOSE:
            raise ValueError("commentary_plan must PROPOSE")
        if (plan.match_id, plan.event_id, plan.event_revision, plan.language) != (
            event.match_id, event.event_id, event.revision, policy.locale,
        ):
            raise ValueError("commentary_plan does not exactly match event coordinates or policy locale")
        expected_evidence = tuple(sorted(event.evidence_refs))
        if plan.evidence_refs != expected_evidence:
            raise ValueError("commentary_plan evidence refs do not exactly match event")
        if len(event.evidence_refs) > policy.max_evidence_refs:
            raise ValueError("event evidence refs exceed policy bound")
        if len(event.knowledge_refs) > policy.max_knowledge_refs:
            raise ValueError("event knowledge refs exceed policy bound")

    @staticmethod
    def _validate_evidence(
        event: CanonicalGameEvent,
        match: GameMatch,
        evidence_by_id: Mapping[str, GameEvidence],
        evidence_sha256_by_id: Mapping[str, str],
        current_evidence_sha256_by_id: Mapping[str, str],
        policy: DbDReasoningContextPolicy,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        expected_ids = set(event.evidence_refs)
        if set(evidence_by_id) != expected_ids or len(evidence_by_id) != len(expected_ids):
            raise ValueError("evidence_by_id keys must exactly match event evidence refs")
        if not isinstance(evidence_sha256_by_id, Mapping) or set(evidence_sha256_by_id) != expected_ids or len(evidence_sha256_by_id) != len(expected_ids):
            raise ValueError("evidence_sha256_by_id keys must exactly match event evidence refs")
        if (
            not isinstance(current_evidence_sha256_by_id, Mapping)
            or set(current_evidence_sha256_by_id) != expected_ids
            or len(current_evidence_sha256_by_id) != len(expected_ids)
            or dict(current_evidence_sha256_by_id) != dict(evidence_sha256_by_id)
        ):
            raise ValueError("evidence bindings are stale against the canonical current snapshot")
        for evidence_id in event.evidence_refs:
            evidence = evidence_by_id[evidence_id]
            if not isinstance(evidence, GameEvidence) or evidence.game_evidence_id != evidence_id:
                raise ValueError("evidence_by_id must contain exact GameEvidence values")
            if evidence.match_id != event.match_id:
                raise ValueError("evidence match_id does not match event")
            if (
                evidence.production_job_id != match.production_job_id
                or evidence.source_asset_id != match.source_asset_id
            ):
                raise ValueError("evidence owner coordinates do not match GameMatch")
            if (
                evidence.source_range.end_frame_exclusive <= event.source_range.start_frame
                or evidence.source_range.start_frame >= event.source_range.end_frame_exclusive
            ):
                raise ValueError("evidence range must positively overlap the event source range")
            supplied_sha256 = evidence_sha256_by_id[evidence_id]
            validate_sha256(supplied_sha256, field_name="evidence_sha256_by_id value")
            if evidence.to_dict()["game_evidence_sha256"] != supplied_sha256:
                raise ValueError("evidence digest does not exactly match GameEvidence")
        refs = tuple(sorted(expected_ids))
        if len(refs) > policy.max_evidence_refs:
            raise ValueError("evidence refs exceed policy bound")
        return refs, tuple(evidence_sha256_by_id[reference] for reference in refs)

    @staticmethod
    def _validate_knowledge(
        event: CanonicalGameEvent,
        plan: CommentaryPlan,
        knowledge_refs: Sequence[GameKnowledgeRef],
        trivia_entries: Sequence[DBDTriviaEntry],
        rag_rows: Sequence[DbDReasoningRagResult],
        policy: DbDReasoningContextPolicy,
    ) -> tuple[str, ...]:
        if isinstance(knowledge_refs, (str, bytes)):
            raise TypeError("knowledge_refs must be a sequence of GameKnowledgeRef")
        supplied = tuple(knowledge_refs)
        if any(not isinstance(reference, GameKnowledgeRef) for reference in supplied):
            raise ValueError("knowledge_refs must contain GameKnowledgeRef values")
        supplied_hashes = tuple(sorted(reference.to_dict()["knowledge_ref_sha256"] for reference in supplied))
        expected_hashes = tuple(sorted(reference.to_dict()["knowledge_ref_sha256"] for reference in event.knowledge_refs))
        if len(supplied_hashes) != len(set(supplied_hashes)) or supplied_hashes != expected_hashes:
            raise ValueError("knowledge refs must exactly match event knowledge hashes")
        auxiliary_hashes = tuple(hash_value for row in rag_rows for hash_value in row.auxiliary_knowledge_sha256s)
        if len(auxiliary_hashes) != len(set(auxiliary_hashes)):
            raise ValueError("RAG auxiliary knowledge hashes must be globally unique")
        DbDReasoningContextAssembler._validate_trivia(event, plan, trivia_entries, rag_rows)
        if plan.knowledge_ref_sha256s != tuple(sorted((*expected_hashes, *auxiliary_hashes))):
            raise ValueError("knowledge and trivia hashes must exactly match commentary plan hashes")
        if len(supplied) > policy.max_knowledge_refs:
            raise ValueError("knowledge refs exceed policy bound")
        event_version = _patch_version(event.game_version, field_name="event game version")
        for reference in supplied:
            if reference.environment is not event.environment:
                raise ValueError("knowledge environment does not match event")
            lower = _patch_version(reference.game_version_from, field_name="knowledge game_version_from")
            upper = (
                None
                if reference.game_version_to is None
                else _patch_version(reference.game_version_to, field_name="knowledge game_version_to")
            )
            if upper is not None and upper <= lower:
                raise ValueError("knowledge patch interval is invalid")
            if event_version < lower:
                raise ValueError("knowledge patch interval does not include event game version")
            if upper is not None:
                if reference.knowledge_kind is GameKnowledgeKind.PERK and event_version >= upper:
                    raise ValueError("PERK knowledge patch interval does not include event game version")
                if reference.knowledge_kind in {GameKnowledgeKind.KILLER, GameKnowledgeKind.POWER} and event_version > upper:
                    raise ValueError("KILLER/POWER knowledge patch interval does not include event game version")
                if reference.knowledge_kind not in {GameKnowledgeKind.PERK, GameKnowledgeKind.KILLER, GameKnowledgeKind.POWER}:
                    raise ValueError("knowledge kind with an upper patch bound is not mapped")
        return tuple(sorted((*supplied_hashes, *auxiliary_hashes)))

    @staticmethod
    def _validate_trivia(
        event: CanonicalGameEvent,
        plan: CommentaryPlan,
        trivia_entries: Sequence[DBDTriviaEntry],
        rag_rows: Sequence[DbDReasoningRagResult],
    ) -> None:
        if isinstance(trivia_entries, (str, bytes)):
            raise TypeError("trivia_entries must be a sequence of DBDTriviaEntry")
        entries = tuple(trivia_entries)
        if any(not isinstance(entry, DBDTriviaEntry) for entry in entries):
            raise ValueError("trivia_entries must contain DBDTriviaEntry values")
        hashes = tuple(sorted(str(entry.to_dict()["trivia_sha256"]) for entry in entries))
        if len(hashes) != len(set(hashes)):
            raise ValueError("trivia entries must be unique")
        environment = PerkEnvironment(event.environment.value)
        for entry in entries:
            if entry.status is not TriviaStatus.VERIFIED or not entry.compatible(event.game_version, environment):
                raise ValueError("trivia entry must be VERIFIED and compatible with event")
        expected_facts = tuple(sorted(
            (f"trivia.{entry.trivia_id}", entry.text) for entry in entries
        ))
        actual_facts = tuple(sorted(
            (fact.key, fact.value) for fact in plan.facts if fact.kind is CommentaryClaimKind.TRIVIA
        ))
        if actual_facts != expected_facts:
            raise ValueError("TRIVIA facts must exactly match admitted trivia entries")
        entries_by_digest = {str(entry.to_dict()["trivia_sha256"]): entry for entry in entries}
        auxiliary_hashes = tuple(hash_value for row in rag_rows for hash_value in row.auxiliary_knowledge_sha256s)
        if tuple(sorted(auxiliary_hashes)) != hashes:
            raise ValueError("RAG auxiliary hashes must exactly match verified trivia entries")
        for row in rag_rows:
            if not row.auxiliary_knowledge_sha256s:
                continue
            if row.chunk.source_type != "TRIVIA" or len(row.auxiliary_knowledge_sha256s) != 1:
                raise ValueError("auxiliary hashes require exactly one TRIVIA RAG result")
            entry = entries_by_digest[row.auxiliary_knowledge_sha256s[0]]
            if (
                row.chunk.source_ref != f"trivia://{entry.trivia_id}/r{entry.revision}"
                or row.chunk.text != entry.text
                or row.source_revision != str(entry.revision)
            ):
                raise ValueError("TRIVIA RAG provenance does not exactly match verified entry")

    @staticmethod
    def _validate_rag(
        event: CanonicalGameEvent,
        rag_results: Sequence[DbDReasoningRagResult],
        policy: DbDReasoningContextPolicy,
    ) -> tuple[DbDReasoningRagResult, ...]:
        if isinstance(rag_results, (str, bytes)):
            raise TypeError("rag_results must be a sequence of DbDReasoningRagResult")
        rows = tuple(rag_results)
        if len(rows) > policy.max_rag_chunks:
            raise ValueError("RAG chunks exceed policy bound")
        if any(not isinstance(row, DbDReasoningRagResult) for row in rows):
            raise ValueError("rag_results must contain DbDReasoningRagResult values")
        if any(row.auxiliary_knowledge_sha256s and row.chunk.source_type != "TRIVIA" for row in rows):
            raise ValueError("only TRIVIA RAG results may carry auxiliary knowledge hashes")
        if any(row.environment is not event.environment for row in rows):
            raise ValueError("RAG environment must exactly match event")
        chunks = tuple(row.chunk for row in rows)
        if any(chunk.rights_status != "ADMITTED" or chunk.verification_state != "VERIFIED" or chunk.content_role != "UNTRUSTED_DATA" for chunk in chunks):
            raise ValueError("RAG chunks must be ADMITTED, VERIFIED and UNTRUSTED_DATA")
        if len({chunk.source_ref for chunk in chunks}) != len(chunks):
            raise ValueError("RAG source_ref values must be unique")
        version = _patch_version(event.game_version, field_name="event game version")
        for chunk in chunks:
            if not _rag_interval_includes(chunk.patch_interval, version):
                raise ValueError("RAG patch interval does not include event game version")
        return tuple(sorted(rows, key=lambda row: row.chunk.source_ref))

    @staticmethod
    def _bridge_facts(
        event: CanonicalGameEvent,
        plan: CommentaryPlan,
    ) -> tuple[tuple[ReasoningFact, ...], tuple[ReasoningFact, ...]]:
        values = tuple(ReasoningFact(fact.kind, fact.key, fact.value) for fact in plan.facts)
        seen_values: dict[tuple[CommentaryClaimKind, str], str] = {}
        for fact in values:
            key = (fact.kind, fact.key)
            previous = seen_values.setdefault(key, fact.value)
            if previous != fact.value:
                raise ValueError("contradictory commentary facts share kind and key")
        event_facts = tuple(fact for fact in values if fact.kind is CommentaryClaimKind.EVENT_OCCURRED)
        if event_facts != (ReasoningFact(CommentaryClaimKind.EVENT_OCCURRED, "event.type", event.event_type.value),):
            raise ValueError("EVENT_OCCURRED must exactly describe the canonical event type")
        activations = event.state.get("perk_activations") if isinstance(event.state, Mapping) else None
        expected_activations = () if not isinstance(activations, list) else tuple(sorted(
            (
                ReasoningFact(CommentaryClaimKind.PERK_ACTIVATION, f"perk.activation.{row['perk_id']}", "CONFIRMED")
                for row in activations
                if isinstance(row, Mapping) and row.get("state") == "CONFIRMED" and isinstance(row.get("perk_id"), str)
            ),
            key=lambda fact: (fact.kind.value, fact.key, fact.value),
        ))
        actual_activations = tuple(fact for fact in values if fact.kind is CommentaryClaimKind.PERK_ACTIVATION)
        if actual_activations != expected_activations:
            raise ValueError("PERK_ACTIVATION must exactly match confirmed event state")
        observed_kinds = {CommentaryClaimKind.EVENT_OCCURRED, CommentaryClaimKind.PERK_ACTIVATION}
        observed = tuple(fact for fact in values if fact.kind in observed_kinds)
        canonical = tuple(
            fact for fact in values
            if fact.kind not in observed_kinds and fact.kind is not CommentaryClaimKind.TRIVIA
        )
        return observed, canonical

    @staticmethod
    def _context_id(**coordinates: object) -> str:
        digest = sha256_bytes(canonical_json_bytes(coordinates))
        return "dbd-context-" + digest.removeprefix("sha256:")

    @staticmethod
    def _rag_snapshot_sha256(rows: Sequence[DbDReasoningRagResult]) -> str:
        """Seal the trusted retrieval coordinates independently of untrusted text.

        The public Context only stores ``RagChunk`` display data; its wrapper
        revision/environment coordinates cannot be reconstructed from that list.
        This deterministic digest makes the exact admitted retrieval snapshot a
        first-class Context dependency, including the empty-RAG case.
        """

        payload = {
            "kind": "DBD_REASONING_RAG_SNAPSHOT",
            "rows": [row.to_context_coordinates() for row in rows],
        }
        return sha256_bytes(canonical_json_bytes(payload))

    @staticmethod
    def _evidence_snapshot_sha256(
        evidence_refs: tuple[str, ...], evidence_sha256s: tuple[str, ...],
    ) -> str:
        return sha256_bytes(canonical_json_bytes({
            "kind": "DBD_REASONING_EVIDENCE_SNAPSHOT",
            "evidence": [
                {"game_evidence_id": reference, "game_evidence_sha256": digest}
                for reference, digest in zip(evidence_refs, evidence_sha256s, strict=True)
            ],
        }))


def _patch_version(value: str, *, field_name: str) -> DBDPatchVersion:
    try:
        return DBDPatchVersion.parse(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a numeric DbD patch version") from exc


def _rag_interval_includes(interval: str, version: DBDPatchVersion) -> bool:
    """Accept only an exact patch or explicit inclusive/exclusive ``[from,to)``."""

    if not isinstance(interval, str) or not interval:
        raise ValueError("RAG patch_interval must be a non-empty string")
    if interval.startswith("[") and interval.endswith(")") and "," in interval:
        lower_raw, upper_raw = interval[1:-1].split(",", 1)
        lower = _patch_version(lower_raw, field_name="RAG patch interval lower bound")
        upper = _patch_version(upper_raw, field_name="RAG patch interval upper bound")
        if upper <= lower:
            raise ValueError("RAG patch interval must be non-empty")
        return lower <= version < upper
    return _patch_version(interval, field_name="RAG patch interval") == version


__all__ = ["DbDReasoningContextAssembler", "DbDReasoningContextPolicy", "DbDReasoningRagResult"]
