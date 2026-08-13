"""Cross-registry consistency validation for Production Control snapshots.

Each TASK store can be internally valid while references between TASK-037/038/
039/040/041 are stale or mismatched. This read-only validator detects those
cross-store problems before generation, locking, or autonomous session resume.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audio_workspace import AudioWorkspaceRegistry, PlacementDecision
from .candidate_audit import CandidateAuditRegistry
from .continuity_registry import ContinuityRegistry
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotStatus
from .prompt_registry import GenerationResult, PromptGenerationRegistry
from .serialization import canonical_json_bytes, sha256_bytes


@dataclass(frozen=True, slots=True)
class ProductionBundleValidationReport:
    production_candidate_count: int
    audit_count: int
    generation_attempt_count: int
    continuity_edge_count: int
    audio_placement_count: int

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "report_version": "1.0.0",
            "task_owner": "TASK-037..041",
            "status": "PASS",
            "production_candidate_count": self.production_candidate_count,
            "audit_count": self.audit_count,
            "generation_attempt_count": self.generation_attempt_count,
            "continuity_edge_count": self.continuity_edge_count,
            "audio_placement_count": self.audio_placement_count,
            "automatic_repair_performed": False,
            "automatic_regeneration_started": False,
        }
        body["report_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ProductionBundleValidator:
    @staticmethod
    def validate(
        *,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        prompts: PromptGenerationRegistry,
        continuity: ContinuityRegistry,
        audio: AudioWorkspaceRegistry,
        require_bound_pass_outputs: bool = True,
    ) -> ProductionBundleValidationReport:
        # TASK-038 -> TASK-037 exact Candidate/Asset binding.
        for record in audits.audit_records.values():
            candidate = production.candidates.get(record.candidate_id)
            if candidate is None:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_AUDIT_CANDIDATE_MISSING",
                    "Audit snapshot references a Candidate missing from Production Control",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"audit_id": record.audit_id},
                )
            if candidate.asset_sha256 != record.asset_sha256:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_AUDIT_HASH_MISMATCH",
                    "Audit snapshot Asset checksum differs from Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"audit_id": record.audit_id, "candidate_id": candidate.candidate_id},
                )
        for decision in audits.decisions.values():
            if decision.candidate_id not in production.candidates:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_DECISION_CANDIDATE_MISSING",
                    "Human audit decision references a missing Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"decision_id": decision.decision_id},
                )

        # TASK-040 PASS output lineage. Failed/cancelled attempts do not require a
        # Candidate. A PASS with declared output must be production-bound when the
        # strict resume/admission mode is requested.
        for attempt in prompts.attempts.values():
            if attempt.result is not GenerationResult.PASS or attempt.output_candidate_id is None:
                continue
            candidate = production.candidates.get(attempt.output_candidate_id)
            if candidate is None:
                if require_bound_pass_outputs:
                    raise ProductError(
                        "ERR_PRODUCTION_BUNDLE_GENERATION_OUTPUT_MISSING",
                        "PASS Generation Attempt output Candidate is missing from Production Control",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"generation_job_id": attempt.generation_job_id},
                    )
                continue
            if candidate.slot_id != attempt.slot_id or candidate.generation_job_id != attempt.generation_job_id:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_GENERATION_OUTPUT_MISMATCH",
                    "Generation Attempt output lineage differs from Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"generation_job_id": attempt.generation_job_id, "candidate_id": candidate.candidate_id},
                )

        # TASK-039 continuity source/target must remain connected to the exact
        # production Slots/Candidate bytes used when the edge/resolution was made.
        for edge in continuity.edges.values():
            from_slot = production.slots.get(edge.from_slot_id)
            to_slot = production.slots.get(edge.to_slot_id)
            source = production.candidates.get(edge.from_candidate_id)
            if from_slot is None or to_slot is None or source is None:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_CONTINUITY_REFERENCE_MISSING",
                    "Continuity edge references missing Production state",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"edge_id": edge.edge_id},
                )
            if from_slot.scene_id != edge.from_scene_id or to_slot.scene_id != edge.to_scene_id:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_CONTINUITY_SCENE_MISMATCH",
                    "Continuity edge Scene/Slot identity no longer matches Production Control",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"edge_id": edge.edge_id},
                )
            if source.slot_id != edge.from_slot_id or source.asset_id != edge.from_asset_id or source.asset_sha256 != edge.from_asset_sha256:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_CONTINUITY_SOURCE_MISMATCH",
                    "Continuity source Candidate/Asset identity no longer matches Production Control",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"edge_id": edge.edge_id},
                )
            resolution = continuity.resolutions.get(edge.edge_id)
            if resolution is not None and resolution.status in {"PASS", "HUMAN_APPROVED"}:
                if to_slot.status is not SlotStatus.LOCKED or to_slot.locked_candidate_id is None:
                    raise ProductError(
                        "ERR_PRODUCTION_BUNDLE_CONTINUITY_TARGET_NOT_LOCKED",
                        "Resolved continuity target Slot is no longer locked",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"edge_id": edge.edge_id},
                    )
                target = production.candidates.get(to_slot.locked_candidate_id)
                if target is None or target.lifecycle_state is not CandidateLifecycle.LOCKED:
                    raise ProductError(
                        "ERR_PRODUCTION_BUNDLE_CONTINUITY_TARGET_NOT_LOCKED",
                        "Resolved continuity target Candidate is no longer locked",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"edge_id": edge.edge_id},
                    )
                if target.asset_id != resolution.target_asset_id or target.asset_sha256 != resolution.target_asset_sha256:
                    raise ProductError(
                        "ERR_PRODUCTION_BUNDLE_CONTINUITY_TARGET_MISMATCH",
                        "Resolved continuity target Asset differs from the current locked Candidate",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"edge_id": edge.edge_id},
                    )

        # TASK-041 references Production Candidates. Accepted placements are only
        # production-safe while their Candidate remains locked.
        for decision in audio.decisions.values():
            if decision.candidate_id not in production.candidates:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_AUDIO_CANDIDATE_MISSING",
                    "Audio decision references a missing Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"decision_id": decision.decision_id},
                )
        for placement in audio.placements.values():
            candidate = production.candidates.get(placement.candidate_id)
            if candidate is None:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_AUDIO_CANDIDATE_MISSING",
                    "Audio placement references a missing Production Candidate",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"review_id": placement.review_id},
                )
            if placement.decision is PlacementDecision.ACCEPT and candidate.lifecycle_state is not CandidateLifecycle.LOCKED:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_AUDIO_ACCEPT_NOT_LOCKED",
                    "Accepted Audio placement references a Candidate that is no longer locked",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"review_id": placement.review_id, "candidate_id": candidate.candidate_id},
                )

        return ProductionBundleValidationReport(
            production_candidate_count=len(production.candidates),
            audit_count=len(audits.audit_records),
            generation_attempt_count=len(prompts.attempts),
            continuity_edge_count=len(continuity.edges),
            audio_placement_count=len(audio.placements),
        )
