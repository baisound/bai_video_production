"""TASK-040 generation-attempt -> TASK-037 Candidate lineage binding.

Provider execution and media ingest are outside this module. It binds an already
registered PASS GenerationAttempt to an already registered Production Candidate
using exact job/slot/Candidate identities, then records a GENERATED_FROM Prompt
edge for stale/trace analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .production_control import (
    DependencyEdge,
    DependencyKind,
    EntityRef,
    EntityType,
    ProductionControlRegistry,
)
from .prompt_registry import GenerationResult, PromptGenerationRegistry
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class GenerationOutputBindingResult:
    generation_job_id: str
    prompt_id: str
    prompt_version: int
    candidate_id: str
    slot_id: str
    edge_id: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-040/TASK-037",
            "generation_job_id": self.generation_job_id,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "candidate_id": self.candidate_id,
            "slot_id": self.slot_id,
            "edge_id": self.edge_id,
            "status": self.status,
            "provider_execution_started": False,
            "media_bytes_embedded": False,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class GenerationOutputProductionBinding:
    @staticmethod
    def _prompt_ref(prompt_id: str, prompt_version: int) -> EntityRef:
        try:
            return EntityRef(EntityType.PROMPT, f"{prompt_id}:v{prompt_version}")
        except ValueError as exc:
            raise ProductError(
                "ERR_GENERATION_PROMPT_ID_PRODUCTION_INCOMPATIBLE",
                "Prompt identity cannot be represented in the Production Control graph",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    @classmethod
    def bind(
        cls,
        *,
        generation_job_id: str,
        prompts: PromptGenerationRegistry,
        production: ProductionControlRegistry,
    ) -> GenerationOutputBindingResult:
        attempt = prompts.attempts.get(generation_job_id)
        if attempt is None:
            raise ProductError(
                "ERR_GENERATION_OUTPUT_ATTEMPT_NOT_FOUND",
                "Generation output binding requires a registered Attempt",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if attempt.result is not GenerationResult.PASS or attempt.output_candidate_id is None:
            raise ProductError(
                "ERR_GENERATION_OUTPUT_NOT_PASS",
                "Only a PASS Attempt with an output Candidate may be bound",
                ProductErrorCategory.STATE,
            )
        prompt = prompts.prompts.get((attempt.prompt_id, attempt.prompt_version))
        if prompt is None:
            raise ProductError(
                "ERR_GENERATION_PROMPT_NOT_FOUND",
                "Generation Attempt references an unavailable Prompt version",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        candidate = production.candidates.get(attempt.output_candidate_id)
        if candidate is None:
            raise ProductError(
                "ERR_GENERATION_OUTPUT_CANDIDATE_NOT_FOUND",
                "Generation Attempt output Candidate is not registered in Production Control",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.slot_id != attempt.slot_id:
            raise ProductError(
                "ERR_GENERATION_OUTPUT_SLOT_MISMATCH",
                "Generation Attempt and output Candidate belong to different Slots",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if candidate.generation_job_id != generation_job_id:
            raise ProductError(
                "ERR_GENERATION_OUTPUT_JOB_MISMATCH",
                "Production Candidate generation_job_id does not match the Generation Attempt",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        from_ref = cls._prompt_ref(prompt.prompt_id, prompt.prompt_version)
        to_ref = EntityRef(EntityType.CANDIDATE, candidate.candidate_id)
        seed = sha256_bytes(canonical_json_bytes({
            "generation_job_id": generation_job_id,
            "prompt_id": prompt.prompt_id,
            "prompt_version": prompt.prompt_version,
            "candidate_id": candidate.candidate_id,
        })).split(":", 1)[1][:20]
        edge = DependencyEdge(
            edge_id=f"dep:prompt-candidate:{seed}",
            from_ref=from_ref,
            to_ref=to_ref,
            dependency_kind=DependencyKind.GENERATED_FROM,
            from_hash=prompt.body_sha256,
        )
        existing = production.edges.get(edge.edge_id)
        if existing is not None:
            if existing == edge:
                return GenerationOutputBindingResult(
                    generation_job_id, prompt.prompt_id, prompt.prompt_version,
                    candidate.candidate_id, candidate.slot_id, edge.edge_id, "ALREADY_BOUND",
                )
            raise ProductError(
                "ERR_GENERATION_OUTPUT_DEPENDENCY_CONFLICT",
                "Generation output dependency identity conflicts with existing graph state",
                ProductErrorCategory.STATE,
            )
        production.add_dependency(edge)
        return GenerationOutputBindingResult(
            generation_job_id, prompt.prompt_id, prompt.prompt_version,
            candidate.candidate_id, candidate.slot_id, edge.edge_id, "BOUND",
        )
