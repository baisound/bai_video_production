from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

import pytest

from ai_video_production.montage_preference_projection import (
    ChangeDirection,
    PreferenceDecision,
    PreferenceProjectionCandidateState,
    PreferenceProjectionPolicy,
    PreferenceProjectionSources,
    ProjectionAction,
    ProjectionPolicyRow,
    compile_preference_projection_candidate,
    verify_preference_projection_candidate,
)
from ai_video_production.owner_decision_store import HumanDecision, OwnerDecisionEntry, OwnerDecisionHistory
from ai_video_production.owner_profile_materialization import compile_owner_profile_materialization_candidate
from ai_video_production.owner_profile_registry import compile_owner_profile_registry_candidate
from ai_video_production.owner_profile_registry_store import (
    OwnerProfileRegistryHistory,
    OwnerProfileRegistryRevision,
    confirm_owner_profile_registry_registration,
)
from ai_video_production.owner_profile_store import (
    OwnerProfileHistory,
    OwnerProfileRevision,
    confirm_owner_profile_materialization,
)
from ai_video_production.profile_tuning import AdjustmentReason, ProfileTuningProposal, WeightAdjustment
from ai_video_production.profile_tuning_owner_decision import AdjustmentDecisionSelection, compile_profile_tuning_owner_decision_binding
from ai_video_production.schema_contracts import validate_instance
from test_task019_owner_decision_bridge import _candidate, _history, _profile_proposal, _selections


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64


def policy(*, minimum: int = 1, ceiling: int = 500) -> PreferenceProjectionPolicy:
    return PreferenceProjectionPolicy(
        "montage.owner.preference",
        "1.0.0",
        (
            ProjectionPolicyRow(
                "audio.energy", ChangeDirection.INCREASE, ProjectionAction.UPSERT,
                PreferenceDecision.PREFER, "ENERGETIC_AUDIO", ("MONTAGE",),
                ("OWNER_CONFIRMED",), minimum, ceiling,
            ),
            ProjectionPolicyRow(
                "visual.motion", ChangeDirection.DECREASE, ProjectionAction.UPSERT,
                PreferenceDecision.DEPRIORITIZE, "LOW_MOTION", ("MONTAGE",),
                ("OWNER_CONFIRMED",), minimum, ceiling,
            ),
        ),
    )


def sources(*, second_decision: HumanDecision = HumanDecision.ADOPTED) -> PreferenceProjectionSources:
    proposal = _profile_proposal()
    decisions = _history(second_decision=second_decision)
    selections = _selections()
    binding = compile_profile_tuning_owner_decision_binding(proposal, decisions, selections)
    materialization = compile_owner_profile_materialization_candidate(
        "owner-profile.materialization.001", proposal, binding, decisions, selections
    )
    materialization_confirmation = confirm_owner_profile_materialization(
        confirmation_id="owner-profile.confirmation.001",
        candidate=materialization,
        confirmed_at_epoch_ms=1_700_000_300_000,
        human_confirmed=True,
    )
    profile_revision = OwnerProfileRevision(
        1, materialization.to_dict(), materialization_confirmation, None
    )
    profile_history = OwnerProfileHistory(
        "owner-profiles.default", materialization.owner_scope_sha256, 1,
        (profile_revision,),
    )
    registry_candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001", profile_history,
        expected_history_revision=1,
    )
    registry_confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.001",
        candidate=registry_candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    registry_revision = OwnerProfileRegistryRevision(
        1, registry_candidate, registry_confirmation, None
    )
    registry = OwnerProfileRegistryHistory(
        "owner-profile-registry.default", materialization.owner_scope_sha256,
        profile_history.store_id, 1, (registry_revision,),
    )
    return PreferenceProjectionSources(
        registry, (profile_history,), (proposal,), (binding,), (decisions,)
    )


def multi_revision_sources() -> PreferenceProjectionSources:
    first = sources()
    first_registry_revision = first.registry_history.revisions[0]
    first_profile_history = first.owner_profile_histories[0]
    first_proposal = first.proposals[0]
    first_decisions = first.decision_histories[0]

    third = OwnerDecisionEntry(
        3, "decision.003", _candidate(3), HumanDecision.ADOPTED,
        ("human.explicit-review",), 1_700_000_100_003,
        first_decisions.entries[-1].to_dict()["entry_sha256"],
    )
    fourth = OwnerDecisionEntry(
        4, "decision.004", _candidate(4), HumanDecision.ADOPTED,
        ("human.explicit-review",), 1_700_000_100_004,
        third.to_dict()["entry_sha256"],
    )
    decisions = OwnerDecisionHistory(
        first_decisions.store_id, SHA_A, 4,
        (*first_decisions.entries, third, fourth),
    )
    adjustments = (
        WeightAdjustment("audio.energy", 600, AdjustmentReason.RETENTION_SIGNAL),
        WeightAdjustment("visual.motion", 400, AdjustmentReason.ENGAGEMENT_SIGNAL),
    )
    rules = tuple(
        replace(rule, weight_milli=600 if rule.feature_key == "audio.energy" else 400)
        for rule in first_proposal.proposed_profile.rules
    )
    proposal = ProfileTuningProposal(
        first_proposal.proposed_profile,
        replace(first_proposal.proposed_profile, profile_version="1.2.0", rules=rules),
        first_proposal.feedback_snapshot_sha256,
        first_proposal.feedback_state,
        first_proposal.policy,
        adjustments,
        first_proposal.evaluations,
        first_proposal.state,
        first_proposal.total_holdout_samples,
        first_proposal.weighted_improvement_milli,
        first_proposal.regressed_evaluation_ids,
    )
    selections = (
        AdjustmentDecisionSelection("audio.energy", ("decision.003",)),
        AdjustmentDecisionSelection("visual.motion", ("decision.004",)),
    )
    binding = compile_profile_tuning_owner_decision_binding(proposal, decisions, selections)
    materialization = compile_owner_profile_materialization_candidate(
        "owner-profile.materialization.002", proposal, binding, decisions, selections
    )
    confirmation = confirm_owner_profile_materialization(
        confirmation_id="owner-profile.confirmation.002", candidate=materialization,
        confirmed_at_epoch_ms=1_700_000_300_001, human_confirmed=True,
    )
    first_profile_revision = first_profile_history.revisions[0]
    second_profile_revision = OwnerProfileRevision(
        2, materialization.to_dict(), confirmation,
        first_profile_revision.to_dict()["revision_sha256"],
    )
    second_profile_history = OwnerProfileHistory(
        first_profile_history.store_id, SHA_A, 2,
        (first_profile_revision, second_profile_revision),
    )
    registry_candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.002", second_profile_history,
        expected_history_revision=2,
    )
    registry_confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.002",
        candidate=registry_candidate, confirmed_at_epoch_ms=1_800_000_000_001,
        human_confirmed=True,
    )
    second_registry_revision = OwnerProfileRegistryRevision(
        2, registry_candidate, registry_confirmation,
        first_registry_revision.to_dict()["revision_sha256"],
    )
    registry = OwnerProfileRegistryHistory(
        first.registry_history.registry_id, SHA_A, first_profile_history.store_id,
        2, (first_registry_revision, second_registry_revision),
    )
    return PreferenceProjectionSources(
        registry, (first_profile_history, second_profile_history),
        (first_proposal, proposal), (first.bindings[0], binding),
        (first_decisions, decisions),
    )


def compile_ready(*, source: PreferenceProjectionSources | None = None, projection_policy: PreferenceProjectionPolicy | None = None, **overrides):
    value = sources() if source is None else source
    arguments = {
        "expected_owner_scope_sha256": SHA_A,
        "expected_registry_revision": 1,
        "requested_scope_mode": "OWNER_GLOBAL",
        "previous_active_promotion_revision": 0,
        "previous_active_promotion_sha256": None,
        "next_profile_version": 1,
    }
    arguments.update(overrides)
    return compile_preference_projection_candidate(value, policy() if projection_policy is None else projection_policy, **arguments)


def test_policy_round_trip_schema_mirror_closed_fields_and_immutability() -> None:
    original = policy()
    payload = original.to_dict()
    assert PreferenceProjectionPolicy.from_dict(payload).to_dict() == payload
    validate_instance("montage-preference-projection-policy.schema.json", payload)
    assert (
        ROOT.joinpath("schemas/montage-preference-projection-policy.schema.json").read_bytes()
        == ROOT.joinpath("src/ai_video_production/schema_resources/montage-preference-projection-policy.schema.json").read_bytes()
    )
    with pytest.raises(FrozenInstanceError):
        original.policy_id = "changed"  # type: ignore[misc]
    unknown = deepcopy(payload); unknown["unknown"] = False
    with pytest.raises(ValueError, match="incomplete or unknown"):
        PreferenceProjectionPolicy.from_dict(unknown)
    wrong_version = deepcopy(payload); wrong_version["schema_version"] = "2.0.0"
    with pytest.raises(ValueError, match="unsupported"):
        PreferenceProjectionPolicy.from_dict(wrong_version)


@pytest.mark.parametrize(
    "row,match",
    (
        (ProjectionPolicyRow("audio.energy", ChangeDirection.INCREASE, ProjectionAction.RETIRE, None, None, (), (), 1, 0), None),
        (("bad",), "Product tokens"),
    ),
)
def test_policy_retire_and_token_contract(row, match) -> None:
    if match is None:
        assert row.projection_action is ProjectionAction.RETIRE
    else:
        with pytest.raises(ValueError, match=match):
            ProjectionPolicyRow("audio.energy", ChangeDirection.INCREASE, ProjectionAction.UPSERT, PreferenceDecision.PREFER, "TARGET", row, ("OK",), 1, 1)
    with pytest.raises(ValueError, match="RETIRE"):
        ProjectionPolicyRow("audio.energy", ChangeDirection.INCREASE, ProjectionAction.RETIRE, PreferenceDecision.PREFER, None, (), (), 1, 0)
    with pytest.raises(ValueError, match="unique"):
        PreferenceProjectionPolicy("p", "1.0.0", (policy().rows[0], policy().rows[0]))


def test_ready_candidate_is_deterministic_advisory_only_and_self_verified() -> None:
    source = sources()
    first = compile_ready(source=source)
    second = compile_ready(source=source)
    assert first.to_dict() == second.to_dict()
    assert first.state is PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW
    document = first.to_dict()
    envelope = document["proposed_envelope"]
    assert envelope["profile_contract"] == "bvp-task029-montage-preference-projection-v1"
    assert envelope["profile_version"] == 1
    assert envelope["source_record_count"] == 2
    assert envelope["advisory_only"] is True
    assert envelope["canonical_timeline"] is False
    assert envelope["auto_apply_authorized"] is False
    assert [row["decision"] for row in envelope["payload"]["preferences"]] == [
        row["decision"] for row in sorted(envelope["payload"]["preferences"], key=lambda value: value["preference_id"])
    ]
    assert all(row["ranking_bias"] != -0.0 for row in envelope["payload"]["preferences"])
    for field in ("automatic_learning_authorized", "automatic_promotion_authorized", "timeline_mutation_authorized", "resolve_write_authorized", "external_effect_authorized"):
        assert document[field] is False
    verify_preference_projection_candidate(
        first, source, policy(), expected_owner_scope_sha256=SHA_A,
        expected_registry_revision=1, requested_scope_mode="OWNER_GLOBAL",
        previous_active_promotion_revision=0, previous_active_promotion_sha256=None,
        next_profile_version=1,
    )


def test_integer_formula_golden_threshold_half_and_cap() -> None:
    candidate = compile_ready()
    rows = {row.target: row for row in candidate.preferences or ()}
    # TASK-019 fixture: samples=100/min=100 -> 500; improvement=20/min=10 -> cap 1000.
    assert {row.confidence_milli for row in rows.values()} == {500}
    # delta=50/max=100 -> 500; effective=500; ceiling=500 -> half-up 250.
    assert rows["ENERGETIC_AUDIO"].ranking_bias_milli == 250
    assert rows["LOW_MOTION"].ranking_bias_milli == -250
    capped = compile_ready(projection_policy=policy(ceiling=1000))
    assert {abs(row.ranking_bias_milli) for row in capped.preferences or ()} == {500}


def test_multi_revision_reconstructs_only_latest_change_and_current_hashes() -> None:
    source = multi_revision_sources()
    candidate = compile_preference_projection_candidate(
        source, policy(), expected_owner_scope_sha256=SHA_A,
        expected_registry_revision=2, requested_scope_mode="OWNER_GLOBAL",
        previous_active_promotion_revision=1,
        previous_active_promotion_sha256="sha256:" + "f" * 64,
        next_profile_version=2,
    )
    assert candidate.state is PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW
    assert candidate.current_profile_version == "1.2.0"
    assert candidate.current_profile_sha256 == source.registry_history.revisions[-1].candidate.profile_snapshot.to_dict()["profile_sha256"]
    assert {decision for row in candidate.preferences or () for decision in row.source_decision_ids} == {"decision.003", "decision.004"}
    assert candidate.to_dict()["proposed_envelope"]["profile_version"] == 2


def test_project_scope_stale_owner_and_unbound_are_body_free() -> None:
    project = compile_ready(requested_scope_mode="PROJECT_ONLY")
    stale = compile_ready(expected_registry_revision=2)
    mixed = compile_ready(expected_owner_scope_sha256="sha256:" + "b" * 64)
    source = sources()
    unbound_source = PreferenceProjectionSources(source.registry_history, (), (), (), ())
    unbound = compile_ready(source=unbound_source)
    assert [value.state for value in (project, stale, mixed, unbound)] == [
        PreferenceProjectionCandidateState.PROJECT_SCOPED_PROFILE_UNSUPPORTED_V1,
        PreferenceProjectionCandidateState.SOURCE_STALE,
        PreferenceProjectionCandidateState.SOURCE_INTEGRITY_FAILURE,
        PreferenceProjectionCandidateState.SOURCE_NOT_BOUND,
    ]
    assert all(value.to_dict()["proposed_envelope"] is None for value in (project, stale, mixed, unbound))


def test_missing_mapping_confirmation_threshold_and_retire_are_closed_states() -> None:
    missing = PreferenceProjectionPolicy("p", "1.0.0", (policy().rows[0],))
    assert compile_ready(projection_policy=missing).state is PreferenceProjectionCandidateState.UNMAPPED_SOURCE_RULE
    assert compile_ready(projection_policy=policy(minimum=2)).state is PreferenceProjectionCandidateState.INSUFFICIENT_CONFIRMATIONS
    retired = PreferenceProjectionPolicy(
        "p", "1.0.0",
        tuple(ProjectionPolicyRow(row.feature_key, row.change_direction, ProjectionAction.RETIRE, None, None, (), (), 1, 0) for row in policy().rows),
    )
    assert compile_ready(projection_policy=retired).state is PreferenceProjectionCandidateState.NO_ACTIVE_PREFERENCES


def test_source_tamper_rejected_decision_and_replay_fail_closed() -> None:
    source = sources()
    source.registry_history.revisions[0].candidate.profile_snapshot.rules[0]  # immutable read
    malformed = deepcopy(source.registry_history.to_dict())
    malformed["revision"] = 2
    with pytest.raises(ValueError):
        OwnerProfileRegistryHistory.from_dict(malformed)
    # A rejected decision cannot form the ready materialization/registry chain.
    with pytest.raises(ValueError):
        sources(second_decision=HumanDecision.REJECTED)
    with pytest.raises(ValueError):
        replace(
            source.bindings[0],
            supports=(source.bindings[0].supports[0], source.bindings[0].supports[0]),
        )


def test_custom_mapping_and_scalar_hooks_are_never_executed() -> None:
    calls = 0

    class Hook(dict):
        def __iter__(self):
            nonlocal calls
            calls += 1
            return super().__iter__()

    source = sources()
    object.__setattr__(
        source.decision_histories[0].entries[0],
        "candidate",
        Hook(source.decision_histories[0].entries[0].candidate),
    )
    with pytest.raises(ValueError, match="custom containers"):
        PreferenceProjectionSources(source.registry_history, source.owner_profile_histories, source.proposals, source.bindings, source.decision_histories)
    assert calls == 0
    with pytest.raises(ValueError):
        ProjectionPolicyRow("audio.energy", ChangeDirection.INCREASE, ProjectionAction.UPSERT, PreferenceDecision.PREFER, "TARGET", (str.__new__(type("Token", (str,), {}), "TOKEN"),), ("OK",), 1, 1)


def test_no_io_timing_profile_or_runtime_authority_imports() -> None:
    source = ROOT.joinpath("src/ai_video_production/montage_preference_projection.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {"pathlib", "subprocess", "socket", "requests", "montage_preference_profile"}
    assert imports.isdisjoint(forbidden)
