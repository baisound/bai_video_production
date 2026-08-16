from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import inspect
import json
from pathlib import Path

import pytest

from ai_video_production.multimodal_scoring import (
    EvidenceValidity,
    FeatureModality,
    FeaturePolarity,
    FeatureRule,
    FeatureSourceSelector,
    ScoringProfile,
)
from ai_video_production.profile_tuning import (
    AdjustmentReason,
    HoldoutEvaluation,
    ProfileTuningProposal,
    TuningPolicy,
    TuningProposalState,
    WeightAdjustment,
    compile_profile_tuning_proposal,
    verify_profile_tuning_proposal_hash,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.youtube_feedback import (
    AnalyticsMetric,
    AnalyticsObservation,
    AnalyticsWindow,
    FeedbackProfile,
    MetricUnit,
    YouTubePublicationBinding,
    compile_youtube_feedback_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


def rule(key: str, modality: FeatureModality, weight: int, task: str) -> FeatureRule:
    return FeatureRule(
        key, modality, weight, 0, 1000, FeaturePolarity.DIRECT, True, None,
        (FeatureSourceSelector(task, f"{key}.v1"),),
    )


def baseline() -> ScoringProfile:
    return ScoringProfile(
        "generic.multimodal",
        "1.0.0",
        (
            rule("audio.energy", FeatureModality.AUDIO, 500, "TASK-006"),
            rule("visual.motion", FeatureModality.VISUAL, 500, "TASK-005"),
        ),
    )


def feedback(*, complete: bool = True):
    publication = YouTubePublicationBinding(
        "abcDEF_123", SHA_A, "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAV", SHA_B, SHA_C, 1_700_000_000
    )
    profile = FeedbackProfile(
        "youtube.aggregate-feedback", "1.0.0",
        (AnalyticsMetric.IMPRESSIONS_COUNT, AnalyticsMetric.VIEWS_COUNT), (),
    )
    rows = [
        AnalyticsObservation(
            AnalyticsMetric.VIEWS_COUNT, MetricUnit.COUNT, 100, SHA_A, "row.views", SHA_B,
            EvidenceValidity.CURRENT_VALID,
        )
    ]
    if complete:
        rows.append(
            AnalyticsObservation(
                AnalyticsMetric.IMPRESSIONS_COUNT, MetricUnit.COUNT, 1000, SHA_A,
                "row.impressions", SHA_C, EvidenceValidity.CURRENT_VALID,
            )
        )
    return compile_youtube_feedback_snapshot(
        publication, SHA_D, AnalyticsWindow(1_700_000_000, 1_700_086_400), profile, rows
    )


def policy(**changes) -> TuningPolicy:
    values = {
        "policy_id": "profile-tuning.conservative",
        "policy_version": "1.0.0",
        "max_changed_rules": 4,
        "max_abs_weight_delta_milli": 100,
        "minimum_holdout_samples": 100,
        "minimum_improvement_milli": 10,
        "max_single_holdout_regression_milli": 5,
    }
    values.update(changes)
    return TuningPolicy(**values)


def adjustments() -> tuple[WeightAdjustment, ...]:
    return (
        WeightAdjustment("audio.energy", 550, AdjustmentReason.RETENTION_SIGNAL),
        WeightAdjustment("visual.motion", 450, AdjustmentReason.ENGAGEMENT_SIGNAL),
    )


def evaluation(
    evaluation_id: str = "holdout.a",
    baseline_quality: int = 500,
    proposed_quality: int = 520,
    sample_count: int = 100,
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
    manifest: str = SHA_A,
) -> HoldoutEvaluation:
    return HoldoutEvaluation(
        evaluation_id, manifest, sample_count, baseline_quality, proposed_quality, validity
    )


def proposal(*rows: HoldoutEvaluation, feedback_complete: bool = True) -> ProfileTuningProposal:
    return compile_profile_tuning_proposal(
        baseline(), "1.1.0", feedback(complete=feedback_complete), policy(), adjustments(),
        rows or (evaluation(),),
    )


def test_proposal_is_deterministic_schema_valid_and_no_effect():
    first = proposal().to_dict()
    second = proposal().to_dict()
    assert first == second
    assert first["task_owner"] == "TASK-019"
    assert first["state"] == "READY_FOR_HUMAN_REVIEW"
    assert first["weighted_improvement_milli"] == 20
    assert first["rollback_profile_sha256"] == first["baseline_profile"]["profile_sha256"]
    assert first["human_review_required"] is True
    for name in (
        "automatic_profile_write_authorized",
        "automatic_promotion_authorized",
        "automatic_rollback_execution_authorized",
        "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        assert first[name] is False
    verify_profile_tuning_proposal_hash(first)
    validate_instance(first, ROOT / "schemas" / "profile-tuning-proposal.schema.json")


def test_schema_mirror_is_byte_identical():
    public = (ROOT / "schemas" / "profile-tuning-proposal.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "profile-tuning-proposal.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(proposal().to_dict(), json.loads(public))


def test_proposed_profile_changes_only_declared_weights_and_version():
    compiled = proposal()
    assert compiled.proposed_profile.profile_id == compiled.baseline_profile.profile_id
    assert compiled.proposed_profile.profile_version == "1.1.0"
    before = {item.feature_key: item for item in compiled.baseline_profile.rules}
    after = {item.feature_key: item for item in compiled.proposed_profile.rules}
    assert {key: item.weight_milli for key, item in after.items()} == {
        "audio.energy": 550, "visual.motion": 450
    }
    for key in before:
        assert replace(after[key], weight_milli=before[key].weight_milli) == before[key]


def test_feedback_and_holdout_states_are_distinct_and_fail_closed():
    assert proposal(feedback_complete=False).state is TuningProposalState.FEEDBACK_INCOMPLETE
    insufficient = compile_profile_tuning_proposal(
        baseline(), "1.1.0", feedback(), policy(minimum_holdout_samples=101), adjustments(),
        (evaluation(),),
    )
    assert insufficient.state is TuningProposalState.INSUFFICIENT_HOLDOUT
    no_gain = proposal(evaluation(proposed_quality=505))
    assert no_gain.state is TuningProposalState.NO_MEASURED_IMPROVEMENT
    regression = proposal(
        evaluation("holdout.a", baseline_quality=500, proposed_quality=520, sample_count=100, manifest=SHA_A),
        evaluation("holdout.b", baseline_quality=500, proposed_quality=494, sample_count=100, manifest=SHA_B),
    )
    assert regression.state is TuningProposalState.HOLDOUT_REGRESSION
    assert regression.regressed_evaluation_ids == ("holdout.b",)
    unknown = proposal(evaluation(validity=EvidenceValidity.UNKNOWN))
    assert unknown.state is TuningProposalState.UNKNOWN_EVIDENCE
    stale = proposal(evaluation(validity=EvidenceValidity.STALE))
    assert stale.state is TuningProposalState.STALE_OR_REVOKED_EVIDENCE


def test_adjustment_bounds_projection_and_versions_fail_closed():
    with pytest.raises(ValueError, match="must differ"):
        compile_profile_tuning_proposal(
            baseline(), "1.0.0", feedback(), policy(), adjustments(), (evaluation(),)
        )
    with pytest.raises(ValueError, match="delta exceeds"):
        compile_profile_tuning_proposal(
            baseline(), "1.1.0", feedback(), policy(),
            (
                WeightAdjustment("audio.energy", 601, AdjustmentReason.RETENTION_SIGNAL),
                WeightAdjustment("visual.motion", 399, AdjustmentReason.FEATURE_BALANCE),
            ),
            (evaluation(),),
        )
    with pytest.raises(ValueError, match="sum"):
        compile_profile_tuning_proposal(
            baseline(), "1.1.0", feedback(), policy(),
            (
                WeightAdjustment("audio.energy", 550, AdjustmentReason.RETENTION_SIGNAL),
                WeightAdjustment("visual.motion", 451, AdjustmentReason.FEATURE_BALANCE),
            ),
            (evaluation(),),
        )
    with pytest.raises(ValueError, match="not present"):
        compile_profile_tuning_proposal(
            baseline(), "1.1.0", feedback(), policy(),
            (
                WeightAdjustment("audio.energy", 550, AdjustmentReason.RETENTION_SIGNAL),
                WeightAdjustment("unknown.feature", 450, AdjustmentReason.FEATURE_BALANCE),
            ),
            (evaluation(),),
        )


def test_holdout_identity_caps_and_duplicates_fail_closed():
    with pytest.raises(ValueError, match="unique"):
        proposal(evaluation(), evaluation())
    with pytest.raises(ValueError, match="manifests must be unique"):
        proposal(evaluation("holdout.a"), evaluation("holdout.b"))
    huge = evaluation(sample_count=1_000_000_000)
    with pytest.raises(ValueError, match="total holdout samples"):
        proposal(huge, evaluation("holdout.b", sample_count=1, manifest=SHA_B))
    with pytest.raises(ValueError, match="1-32"):
        compile_profile_tuning_proposal(
            baseline(), "1.1.0", feedback(), policy(), adjustments(), ()
        )


def test_manual_proposal_cannot_launder_state_or_profile_projection():
    compiled = proposal()
    with pytest.raises(ValueError, match="state and evaluation summary"):
        replace(compiled, state=TuningProposalState.NO_MEASURED_IMPROVEMENT)
    altered = ScoringProfile(
        compiled.proposed_profile.profile_id,
        compiled.proposed_profile.profile_version,
        (
            replace(compiled.proposed_profile.rules[0], weight_milli=540),
            replace(compiled.proposed_profile.rules[1], weight_milli=460),
        ),
    )
    with pytest.raises(ValueError, match="exactly project"):
        replace(compiled, proposed_profile=altered)


def test_hash_verifier_rejects_nested_outer_and_rollback_tamper():
    payload = proposal().to_dict()
    payload["holdout_evaluations"][0]["proposed_quality_milli"] += 1
    with pytest.raises(ValueError, match="proposal_sha256"):
        verify_profile_tuning_proposal_hash(payload)
    payload = proposal().to_dict()
    payload["tuning_policy"]["minimum_improvement_milli"] += 1
    body = dict(payload)
    body.pop("proposal_sha256")
    payload["proposal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="tuning_policy.policy_sha256"):
        verify_profile_tuning_proposal_hash(payload)
    payload = proposal().to_dict()
    payload["rollback_profile_sha256"] = SHA_D
    body = dict(payload)
    body.pop("proposal_sha256")
    payload["proposal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="rollback_profile_sha256"):
        verify_profile_tuning_proposal_hash(payload)


def test_contract_is_immutable_and_public_surface_has_no_effect_capability():
    compiled = proposal()
    with pytest.raises(FrozenInstanceError):
        compiled.state = TuningProposalState.UNKNOWN_EVIDENCE  # type: ignore[misc]
    assert set(inspect.signature(compile_profile_tuning_proposal).parameters) == {
        "baseline_profile", "proposed_profile_version", "feedback_snapshot", "policy",
        "adjustments", "evaluations",
    }
    tree = ast.parse((ROOT / "src" / "ai_video_production" / "profile_tuning.py").read_text("utf-8"))
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {"subprocess", "requests", "urllib", "httpx", "pathlib", "googleapiclient", "socket"}
    )
    calls = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})
