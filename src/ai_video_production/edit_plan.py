"""TASK-007 deterministic Candidate Clip Graph and human-approved Edit Plan."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .cut_candidates import CutCandidate, CutCandidateManifest
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


class EditDecision(str, Enum):
    REVIEW = "REVIEW"
    CUT = "CUT"
    KEEP = "KEEP"


@dataclass(frozen=True, slots=True)
class CandidateReviewDecision:
    candidate_id: str
    decision: EditDecision
    override_start_us: int | None = None
    override_end_us: int | None = None

    def __post_init__(self) -> None:
        if self.decision is EditDecision.REVIEW:
            raise ValueError("human review decision cannot remain REVIEW")
        supplied = self.override_start_us is not None or self.override_end_us is not None
        if supplied:
            if self.decision is not EditDecision.CUT:
                raise ValueError("only CUT decisions may override the cut range")
            if self.override_start_us is None or self.override_end_us is None:
                raise ValueError("override range requires both start and end")
            if self.override_start_us < 0 or self.override_end_us <= self.override_start_us:
                raise ValueError("override range must be positive and end-exclusive")


@dataclass(frozen=True, slots=True)
class PlannedRange:
    range_id: str
    start_us: int
    end_us: int
    source_candidate_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("planned range must be positive and end-exclusive")

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "range_id": self.range_id,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "duration_us": self.duration_us,
            "source_candidate_ids": list(self.source_candidate_ids),
        }


@dataclass(frozen=True, slots=True)
class CandidateGraphNode:
    candidate_id: str
    kind: str
    start_us: int
    end_us: int
    strength_score: int
    evidence_codes: tuple[str, ...]
    proposed_decision: EditDecision
    final_decision: EditDecision
    effective_start_us: int
    effective_end_us: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "range_us": {"start": self.start_us, "end_exclusive": self.end_us},
            "strength_score": self.strength_score,
            "evidence_codes": list(self.evidence_codes),
            "proposed_decision": self.proposed_decision.value,
            "final_decision": self.final_decision.value,
            "effective_range_us": {
                "start": self.effective_start_us,
                "end_exclusive": self.effective_end_us,
            },
        }


@dataclass(frozen=True, slots=True)
class CandidateGraphEdge:
    from_node: str
    to_node: str

    def to_dict(self) -> dict[str, str]:
        return {"from": self.from_node, "to": self.to_node}


@dataclass(frozen=True, slots=True)
class EditPlan:
    source_asset_id: str
    source_duration_us: int
    source_candidate_manifest_sha256: str
    target_duration_us: int | None
    graph_nodes: tuple[CandidateGraphNode, ...]
    graph_edges: tuple[CandidateGraphEdge, ...]
    keep_ranges: tuple[PlannedRange, ...]
    cut_ranges: tuple[PlannedRange, ...]
    approval_state: str
    approved_by: str | None

    @property
    def unresolved_candidate_ids(self) -> tuple[str, ...]:
        return tuple(node.candidate_id for node in self.graph_nodes if node.final_decision is EditDecision.REVIEW)

    @property
    def projected_duration_us(self) -> int:
        return sum(item.duration_us for item in self.keep_ranges)

    @property
    def target_met(self) -> bool | None:
        if self.target_duration_us is None:
            return None
        return self.projected_duration_us <= self.target_duration_us

    @property
    def ready_for_assembly(self) -> bool:
        return self.approval_state == "APPROVED" and not self.unresolved_candidate_ids and bool(self.keep_ranges)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-007",
            "downstream_execution_owner": "TASK-010",
            "source_asset_id": self.source_asset_id,
            "source_duration_us": self.source_duration_us,
            "source_candidate_manifest_sha256": self.source_candidate_manifest_sha256,
            "target_duration_us": self.target_duration_us,
            "candidate_graph": {
                "nodes": [item.to_dict() for item in self.graph_nodes],
                "edges": [item.to_dict() for item in self.graph_edges],
            },
            "keep_ranges": [item.to_dict() for item in self.keep_ranges],
            "cut_ranges": [item.to_dict() for item in self.cut_ranges],
            "unresolved_candidate_ids": list(self.unresolved_candidate_ids),
            "projected_duration_us": self.projected_duration_us,
            "target_met": self.target_met,
            "approval_state": self.approval_state,
            "approved_by": self.approved_by,
            "ready_for_assembly": self.ready_for_assembly,
            "automatic_external_write_authorized": False,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class EditPlanService:
    """Compile review-only TASK-024 candidates into a deterministic TASK-007 plan.

    Candidate scores may order *proposals*, but no candidate becomes an executable
    cut until a caller supplies an explicit human review decision. Plan-level
    approval is a second gate and cannot be asserted while any candidate remains
    unresolved.
    """

    @staticmethod
    def build(
        manifest: CutCandidateManifest,
        *,
        reviews: Iterable[CandidateReviewDecision] = (),
        target_duration_us: int | None = None,
        approve: bool = False,
        approved_by: str | None = None,
    ) -> EditPlan:
        manifest_dict = manifest.to_dict()
        if manifest_dict.get("auto_apply_authorized") is not False:
            raise ProductError(
                "ERR_EDIT_PLAN_UPSTREAM_AUTO_APPLY_UNSAFE",
                "TASK-007 requires a review-only TASK-024 manifest",
                ProductErrorCategory.AUTHORIZATION,
            )
        source_duration_us = manifest.source_duration_us
        if target_duration_us is not None and not 1 <= target_duration_us <= source_duration_us:
            raise ValueError("target_duration_us must be within the source duration")

        review_map: dict[str, CandidateReviewDecision] = {}
        valid_ids = {item.candidate_id for item in manifest.candidates}
        for review in reviews:
            if review.candidate_id not in valid_ids:
                raise ValueError(f"unknown candidate_id: {review.candidate_id}")
            if review.candidate_id in review_map:
                raise ValueError(f"duplicate review decision: {review.candidate_id}")
            review_map[review.candidate_id] = review

        proposed_cut_ids = EditPlanService._proposal_ids(
            manifest.candidates,
            source_duration_us=source_duration_us,
            target_duration_us=target_duration_us,
        )
        keep_blocks = tuple((item.start_us, item.end_us) for item in manifest.keep_blocks)
        nodes: list[CandidateGraphNode] = []
        cut_sources: list[tuple[int, int, str]] = []
        for candidate in manifest.candidates:
            proposed = EditDecision.CUT if candidate.candidate_id in proposed_cut_ids else EditDecision.KEEP
            review = review_map.get(candidate.candidate_id)
            final = EditDecision.REVIEW if review is None else review.decision
            effective_start = candidate.start_us
            effective_end = candidate.end_us
            if review is not None and review.override_start_us is not None:
                assert review.override_end_us is not None
                if review.override_start_us < candidate.start_us or review.override_end_us > candidate.end_us:
                    raise ProductError(
                        "ERR_EDIT_PLAN_OVERRIDE_OUTSIDE_CANDIDATE",
                        "review override must stay within the source candidate range",
                        ProductErrorCategory.VALIDATION,
                        details={"candidate_id": candidate.candidate_id},
                    )
                effective_start = review.override_start_us
                effective_end = review.override_end_us
            if final is EditDecision.CUT:
                EditPlanService._assert_not_protected(effective_start, effective_end, keep_blocks, candidate.candidate_id)
                cut_sources.append((effective_start, effective_end, candidate.candidate_id))
            nodes.append(
                CandidateGraphNode(
                    candidate_id=candidate.candidate_id,
                    kind=candidate.kind.value,
                    start_us=candidate.start_us,
                    end_us=candidate.end_us,
                    strength_score=candidate.strength_score,
                    evidence_codes=candidate.evidence_codes,
                    proposed_decision=proposed,
                    final_decision=final,
                    effective_start_us=effective_start,
                    effective_end_us=effective_end,
                )
            )

        nodes.sort(key=lambda item: (item.start_us, item.end_us, item.candidate_id))
        edges = EditPlanService._graph_edges(nodes)
        cut_ranges = EditPlanService._merge_cut_ranges(cut_sources)
        keep_ranges = EditPlanService._complement_ranges(source_duration_us, cut_ranges)

        unresolved = [item.candidate_id for item in nodes if item.final_decision is EditDecision.REVIEW]
        if approve:
            if unresolved:
                raise ProductError(
                    "ERR_EDIT_PLAN_HUMAN_REVIEW_REQUIRED",
                    "all TASK-024 candidates require a human CUT/KEEP decision before approval",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    details={"unresolved_count": len(unresolved)},
                )
            if not approved_by or not approved_by.strip():
                raise ProductError(
                    "ERR_EDIT_PLAN_APPROVER_REQUIRED",
                    "approved Edit Plan requires a non-empty approver identity",
                    ProductErrorCategory.AUTHORIZATION,
                )
            approval_state = "APPROVED"
            approver = approved_by.strip()
        else:
            approval_state = "DRAFT"
            approver = None

        return EditPlan(
            source_asset_id=manifest.source_asset_id,
            source_duration_us=source_duration_us,
            source_candidate_manifest_sha256=manifest_dict["manifest_sha256"],
            target_duration_us=target_duration_us,
            graph_nodes=tuple(nodes),
            graph_edges=edges,
            keep_ranges=keep_ranges,
            cut_ranges=cut_ranges,
            approval_state=approval_state,
            approved_by=approver,
        )

    @staticmethod
    def _proposal_ids(
        candidates: tuple[CutCandidate, ...],
        *,
        source_duration_us: int,
        target_duration_us: int | None,
    ) -> set[str]:
        if target_duration_us is None:
            return {item.candidate_id for item in candidates}
        reduction_needed = max(0, source_duration_us - target_duration_us)
        if reduction_needed == 0:
            return set()
        ordered = sorted(
            candidates,
            key=lambda item: (-item.strength_score, item.start_us, item.end_us, item.candidate_id),
        )
        selected: set[str] = set()
        covered: list[tuple[int, int]] = []
        reduced = 0
        for item in ordered:
            if reduced >= reduction_needed:
                break
            before = EditPlanService._union_duration(covered)
            covered.append((item.start_us, item.end_us))
            after = EditPlanService._union_duration(covered)
            if after > before:
                selected.add(item.candidate_id)
                reduced = after
        return selected

    @staticmethod
    def _union_duration(ranges: Iterable[tuple[int, int]]) -> int:
        ordered = sorted(ranges)
        total = 0
        start: int | None = None
        end: int | None = None
        for current_start, current_end in ordered:
            if start is None:
                start, end = current_start, current_end
                continue
            assert end is not None
            if current_start <= end:
                end = max(end, current_end)
            else:
                total += end - start
                start, end = current_start, current_end
        if start is not None and end is not None:
            total += end - start
        return total

    @staticmethod
    def _assert_not_protected(
        start_us: int,
        end_us: int,
        keep_blocks: tuple[tuple[int, int], ...],
        candidate_id: str,
    ) -> None:
        for keep_start, keep_end in keep_blocks:
            if start_us < keep_end and keep_start < end_us:
                raise ProductError(
                    "ERR_EDIT_PLAN_PROTECTED_KEEP_COLLISION",
                    "approved cut overlaps an upstream protected Keep Block",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"candidate_id": candidate_id},
                )

    @staticmethod
    def _graph_edges(nodes: list[CandidateGraphNode]) -> tuple[CandidateGraphEdge, ...]:
        if not nodes:
            return (CandidateGraphEdge("START", "END"),)
        edges = [CandidateGraphEdge("START", nodes[0].candidate_id)]
        for left, right in zip(nodes, nodes[1:]):
            edges.append(CandidateGraphEdge(left.candidate_id, right.candidate_id))
        edges.append(CandidateGraphEdge(nodes[-1].candidate_id, "END"))
        return tuple(edges)

    @staticmethod
    def _merge_cut_ranges(sources: Iterable[tuple[int, int, str]]) -> tuple[PlannedRange, ...]:
        ordered = sorted(sources, key=lambda item: (item[0], item[1], item[2]))
        merged: list[tuple[int, int, list[str]]] = []
        for start, end, candidate_id in ordered:
            if not merged or start > merged[-1][1]:
                merged.append((start, end, [candidate_id]))
                continue
            old_start, old_end, ids = merged[-1]
            merged[-1] = (old_start, max(old_end, end), ids + [candidate_id])
        return tuple(
            PlannedRange(f"remove-{index:06d}", start, end, tuple(sorted(set(ids))))
            for index, (start, end, ids) in enumerate(merged, start=1)
        )

    @staticmethod
    def _complement_ranges(source_duration_us: int, cuts: tuple[PlannedRange, ...]) -> tuple[PlannedRange, ...]:
        keep: list[PlannedRange] = []
        cursor = 0
        index = 1
        for cut in cuts:
            if cursor < cut.start_us:
                keep.append(PlannedRange(f"keep-{index:06d}", cursor, cut.start_us))
                index += 1
            cursor = max(cursor, cut.end_us)
        if cursor < source_duration_us:
            keep.append(PlannedRange(f"keep-{index:06d}", cursor, source_duration_us))
        return tuple(keep)
