"""TASK-049 LLM drafting adapter for validated Game Intelligence plans.

This is the only layer that invokes configured text-generation providers.  It
requires explicit execution authorization, uses the existing BVP provider
routing/credential boundary, parses a strict JSON response, then runs the
existing deterministic Fact Validator before a candidate can be persisted.
"""
from __future__ import annotations

import json
from typing import Any

from .ai_connections import AiConnectionProfile, ConnectionAvailability
from .dbd_commentary_knowledge import DbDTriviaStore, TriviaCandidateMiner
from .game_commentary import (
    CommentaryCandidate, CommentaryCandidateStore, CommentaryClaim, CommentaryClaimKind,
    CommentaryDisposition, CommentaryDraft, CommentaryFactValidator, CommentaryPlan,
)
from .provider_execution import AiProviderExecutionService, TextGenerationRequest


_SYSTEM = """You draft concise Dead by Daylight commentary using ONLY supplied canonical facts.
Return JSON only with this shape:
{"text":"...","claims":[{"kind":"EVENT_OCCURRED|PERK_NAME|PERK_EFFECT|PERK_ACTIVATION|KILLER_NAME|KILLER_DESCRIPTION|POWER_NAME|POWER_DESCRIPTION|TRIVIA","key":"...","value":"..."}]}
Every factual statement in text must correspond to an exact supplied claim. Do not invent numbers, perk effects, activations, killer powers, game state, or trivia. If facts are insufficient, return a minimal factual sentence using only the event fact."""


class CommentaryLlmService:
    def __init__(self, provider_service: AiProviderExecutionService) -> None:
        self.provider_service = provider_service
        self.validator = CommentaryFactValidator()

    @staticmethod
    def _prompt(plan: CommentaryPlan) -> str:
        allowed = [fact.to_dict() for fact in plan.facts]
        return json.dumps({
            "language": plan.language,
            "event_id": plan.event_id,
            "event_revision": plan.event_revision,
            "priority_milli": plan.priority_milli,
            "allowed_facts": allowed,
            "instruction": "Write one or two natural commentary sentences. Claims must copy kind/key/value exactly from allowed_facts.",
        }, ensure_ascii=False, indent=2)

    def draft(self, *, plan: CommentaryPlan, profile: AiConnectionProfile, availability: ConnectionAvailability,
              execution_authorized: bool, max_output_tokens: int = 600, temperature: float = 0.2) -> CommentaryCandidate:
        if plan.disposition is not CommentaryDisposition.PROPOSE:
            raise ValueError("LLM draft requires a PROPOSE commentary plan")
        if not execution_authorized:
            raise PermissionError("LLM provider execution requires explicit authorization")
        result = self.provider_service.generate_planning_text(
            profile, availability,
            TextGenerationRequest(prompt=self._prompt(plan), system_instruction=_SYSTEM,
                                  max_output_tokens=max_output_tokens, temperature=temperature),
        )
        try:
            payload: Any = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM commentary response must be strict JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str) or not isinstance(payload.get("claims"), list):
            raise ValueError("LLM commentary response has invalid shape")
        claims = []
        for item in payload["claims"]:
            if not isinstance(item, dict):
                raise ValueError("LLM commentary claims must be objects")
            claims.append(CommentaryClaim(CommentaryClaimKind(item["kind"]), str(item["key"]), str(item["value"])))
        claims_tuple = tuple(sorted(set(claims), key=lambda x: (x.kind.value, x.key, x.value)))
        draft = CommentaryDraft(payload["text"], claims_tuple, provider_ref=f"provider://{result.provider_id}/{result.model_id}/{result.provider_request_id or result.route_id}")
        validation = self.validator.validate(plan, draft)
        return CommentaryCandidate(plan, draft, validation)

    def draft_persist_and_capture_trivia(self, *, plan: CommentaryPlan, profile: AiConnectionProfile,
                                         availability: ConnectionAvailability, execution_authorized: bool,
                                         candidate_store: CommentaryCandidateStore,
                                         trivia_store: DbDTriviaStore | None = None) -> CommentaryCandidate:
        candidate = self.draft(plan=plan, profile=profile, availability=availability, execution_authorized=execution_authorized)
        candidate_store.append(candidate)
        if candidate.validation.passed and trivia_store is not None:
            for claim in candidate.draft.claims:
                if claim.kind is CommentaryClaimKind.TRIVIA and claim.key.startswith("trivia."):
                    trivia_store.record_usage(
                        claim.key.removeprefix("trivia."),
                        event_id=plan.event_id,
                        commentary_candidate_id=candidate.candidate_id,
                    )
            TriviaCandidateMiner().capture(
                trivia_store, text=candidate.draft.text,
                source_ref=f"commentary://{candidate.candidate_id}",
                event_type=None,
                entity_refs=tuple(fact.key.split(".")[-1] for fact in plan.facts if fact.kind in {CommentaryClaimKind.PERK_NAME, CommentaryClaimKind.PERK_EFFECT}),
            )
        return candidate


__all__ = ["CommentaryLlmService"]
