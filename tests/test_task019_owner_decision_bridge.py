from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path

import pytest

from ai_video_production.human_edit_learning import (
    HardGateState, HumanActionEvidence, HumanDisposition, MetricEvaluation,
    OwnerLearningPolicy, compile_owner_decision_candidate,
)
from ai_video_production.multimodal_scoring import (
    EvidenceValidity, FeatureModality, FeaturePolarity, FeatureRule,
    FeatureSourceSelector, ScoringProfile,
)
from ai_video_production.owner_decision_store import (
    HumanDecision, OwnerDecisionEntry, OwnerDecisionHistory,
)
from ai_video_production.profile_tuning import (
    AdjustmentReason, HoldoutEvaluation, TuningPolicy, WeightAdjustment,
    compile_profile_tuning_proposal,
)
from ai_video_production.profile_tuning_owner_decision import (
    AdjustmentDecisionSelection, OwnerDecisionBindingState,
    compile_profile_tuning_owner_decision_binding,
    verify_profile_tuning_owner_decision_binding,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.youtube_feedback import (
    AnalyticsMetric, AnalyticsObservation, AnalyticsWindow, FeedbackProfile,
    MetricUnit, YouTubePublicationBinding, compile_youtube_feedback_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
METRIC_IDS = (
    "human_acceptance", "qa_compliance", "quality_improvement",
    "rework_reduction", "sample_confidence", "time_reduction",
)


def _rule(key: str, modality: FeatureModality, weight: int, task: str) -> FeatureRule:
    return FeatureRule(
        key, modality, weight, 0, 1000, FeaturePolarity.DIRECT, True, None,
        (FeatureSourceSelector(task, f"{key}.v1"),),
    )


def _profile_proposal(*, complete: bool = True, improvement: int = 520):
    baseline = ScoringProfile(
        "generic.multimodal", "1.0.0",
        (
            _rule("audio.energy", FeatureModality.AUDIO, 500, "TASK-006"),
            _rule("visual.motion", FeatureModality.VISUAL, 500, "TASK-005"),
        ),
    )
    publication = YouTubePublicationBinding(
        "abcDEF_123", SHA_A, "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAV", SHA_B,
        SHA_C, 1_700_000_000,
    )
    profile = FeedbackProfile(
        "youtube.aggregate-feedback", "1.0.0",
        (AnalyticsMetric.IMPRESSIONS_COUNT, AnalyticsMetric.VIEWS_COUNT), (),
    )
    rows = [
        AnalyticsObservation(
            AnalyticsMetric.VIEWS_COUNT, MetricUnit.COUNT, 100, SHA_A,
            "row.views", SHA_B, EvidenceValidity.CURRENT_VALID,
        )
    ]
    if complete:
        rows.append(
            AnalyticsObservation(
                AnalyticsMetric.IMPRESSIONS_COUNT, MetricUnit.COUNT, 1000,
                SHA_A, "row.impressions", SHA_C, EvidenceValidity.CURRENT_VALID,
            )
        )
    feedback = compile_youtube_feedback_snapshot(
        publication, SHA_D, AnalyticsWindow(1_700_000_000, 1_700_086_400),
        profile, rows,
    )
    policy = TuningPolicy(
        "profile-tuning.conservative", "1.0.0", 4, 100, 100, 10, 5
    )
    adjustments = (
        WeightAdjustment("audio.energy", 550, AdjustmentReason.RETENTION_SIGNAL),
        WeightAdjustment("visual.motion", 450, AdjustmentReason.ENGAGEMENT_SIGNAL),
    )
    evaluation = HoldoutEvaluation(
        "holdout.a", SHA_A, 100, 500, improvement, EvidenceValidity.CURRENT_VALID
    )
    return compile_profile_tuning_proposal(
        baseline, "1.1.0", feedback, policy, adjustments, (evaluation,)
    )


def _evidence(number: int) -> HumanActionEvidence:
    return HumanActionEvidence(
        f"human-action.{number:03d}", SHA_A, SHA_B, "TASK-055",
        "sha256:" + f"{number:064x}", "montage.timing",
        ("event:PALLET_DROP", "style:dbd-aggressive"), SHA_B, SHA_C, SHA_A,
        HumanDisposition.MODIFIED, EvidenceValidity.CURRENT_VALID,
        False, False, False, HardGateState.PASS, HardGateState.PASS,
        1_700_000_000_000 + number, 10_000,
    )


def _candidate(number: int) -> dict:
    metrics = tuple(
        MetricEvaluation(name, 500, 520, 10, EvidenceValidity.CURRENT_VALID)
        for name in METRIC_IDS
    )
    policy = OwnerLearningPolicy(
        "owner-learning.conservative", "1.0.0", 2, 10, 10, 0
    )
    return compile_owner_decision_candidate(
        f"owner-decision.{number:03d}", SHA_A,
        f"hypothesis.montage-quality.{number:03d}",
        (_evidence(number * 2 - 1), _evidence(number * 2)), metrics, policy,
    ).to_dict()


def _history(*, second_decision: HumanDecision = HumanDecision.ADOPTED) -> OwnerDecisionHistory:
    first = OwnerDecisionEntry(
        1, "decision.001", _candidate(1), HumanDecision.ADOPTED,
        ("human.explicit-review",), 1_700_000_100_001, None,
    )
    second = OwnerDecisionEntry(
        2, "decision.002", _candidate(2), second_decision,
        ("human.explicit-review",), 1_700_000_100_002,
        first.to_dict()["entry_sha256"],
    )
    return OwnerDecisionHistory("owner-decisions.default", SHA_A, 2, (first, second))


def _selections() -> tuple[AdjustmentDecisionSelection, ...]:
    return (
        AdjustmentDecisionSelection("audio.energy", ("decision.001",)),
        AdjustmentDecisionSelection("visual.motion", ("decision.002",)),
    )


def test_ready_binding_is_deterministic_schema_valid_and_no_effect() -> None:
    proposal = _profile_proposal()
    history = _history()
    first = compile_profile_tuning_owner_decision_binding(
        proposal, history, _selections()
    ).to_dict()
    second = compile_profile_tuning_owner_decision_binding(
        proposal, history, reversed(_selections())
    ).to_dict()
    assert first == second
    assert first["state"] == "READY_FOR_HUMAN_REVIEW"
    assert first["decision_history_revision"] == 2
    assert first["latest_history_revalidation_required"] is True
    for field in (
        "profile_materialization_authorized", "automatic_profile_write_authorized",
        "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
        "rollback_execution_authorized", "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        assert first[field] is False
    validate_instance("profile-tuning-owner-decision-binding.schema.json", first)


def test_rejected_decision_and_nonready_proposal_remain_distinct() -> None:
    rejected = compile_profile_tuning_owner_decision_binding(
        _profile_proposal(), _history(second_decision=HumanDecision.REJECTED),
        _selections(),
    )
    assert rejected.state is OwnerDecisionBindingState.REJECTED_OWNER_DECISION_PRESENT
    not_ready = compile_profile_tuning_owner_decision_binding(
        _profile_proposal(complete=False), _history(), _selections()
    )
    assert not_ready.state is OwnerDecisionBindingState.PROFILE_PROPOSAL_NOT_READY


def test_every_adjustment_requires_one_distinct_existing_decision() -> None:
    proposal = _profile_proposal()
    history = _history()
    with pytest.raises(ValueError, match="every adjusted feature"):
        compile_profile_tuning_owner_decision_binding(
            proposal, history, (_selections()[0],)
        )
    with pytest.raises(ValueError, match="selected only once"):
        compile_profile_tuning_owner_decision_binding(
            proposal, history,
            (
                AdjustmentDecisionSelection("audio.energy", ("decision.001",)),
                AdjustmentDecisionSelection("visual.motion", ("decision.001",)),
            ),
        )
    with pytest.raises(ValueError, match="missing from history"):
        compile_profile_tuning_owner_decision_binding(
            proposal, history,
            (
                AdjustmentDecisionSelection("audio.energy", ("decision.001",)),
                AdjustmentDecisionSelection("visual.motion", ("decision.999",)),
            ),
        )


def test_selection_requires_canonical_ids_and_order() -> None:
    with pytest.raises(ValueError, match="canonically sorted"):
        AdjustmentDecisionSelection("audio.energy", ("decision.002", "decision.001"))
    with pytest.raises(ValueError, match="1..32"):
        AdjustmentDecisionSelection("audio.energy", ())
    with pytest.raises(ValueError, match="invalid"):
        AdjustmentDecisionSelection("bad key", ("decision.001",))


def test_verifier_rejects_binding_or_source_drift() -> None:
    proposal = _profile_proposal()
    history = _history()
    payload = compile_profile_tuning_owner_decision_binding(
        proposal, history, _selections()
    ).to_dict()
    verify_profile_tuning_owner_decision_binding(
        payload, proposal, history, _selections()
    )
    tampered = deepcopy(payload)
    tampered["decision_history_revision"] = 3
    with pytest.raises(ValueError, match="exact proposal"):
        verify_profile_tuning_owner_decision_binding(
            tampered, proposal, history, _selections()
        )
    with pytest.raises(ValueError, match="exact proposal"):
        verify_profile_tuning_owner_decision_binding(
            payload, _profile_proposal(improvement=530), history, _selections()
        )


def test_mutated_candidate_mapping_is_revalidated_before_binding() -> None:
    history = _history()
    history.entries[0].candidate["hypothesis_id"] = "hypothesis.attacker"  # type: ignore[index]
    with pytest.raises(ValueError, match="candidate_sha256"):
        compile_profile_tuning_owner_decision_binding(
            _profile_proposal(), history, _selections()
        )


def test_binding_and_selection_are_immutable() -> None:
    binding = compile_profile_tuning_owner_decision_binding(
        _profile_proposal(), _history(), _selections()
    )
    with pytest.raises(FrozenInstanceError):
        binding.state = OwnerDecisionBindingState.PROFILE_PROPOSAL_NOT_READY  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        _selections()[0].feature_key = "other"  # type: ignore[misc]


def test_schema_mirror_is_byte_identical() -> None:
    assert (
        ROOT / "schemas/profile-tuning-owner-decision-binding.schema.json"
    ).read_bytes() == (
        ROOT / "src/ai_video_production/schema_resources/profile-tuning-owner-decision-binding.schema.json"
    ).read_bytes()


def test_bridge_public_surface_has_no_io_or_mutation_capability() -> None:
    import ai_video_production.profile_tuning_owner_decision as module

    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported_roots.intersection(
        {"pathlib", "os", "subprocess", "socket", "requests", "urllib"}
    )
    assert "OwnerDecisionStore" not in source
    assert "automatic_profile_write_authorized\": True" not in source
