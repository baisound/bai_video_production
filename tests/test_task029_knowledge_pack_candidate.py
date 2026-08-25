from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import inspect
from pathlib import Path

import pytest

from ai_video_production.human_edit_learning import (
    HardGateState,
    HumanActionEvidence,
    HumanDisposition,
    MetricEvaluation,
    OwnerLearningPolicy,
    compile_owner_decision_candidate,
)
from ai_video_production.knowledge_pack_candidate import (
    KnowledgePackCandidatePolicy,
    KnowledgePackCandidateState,
    KnowledgePackPromotionCandidate,
    KnowledgePackSource,
    compile_knowledge_pack_promotion_candidate,
    verify_knowledge_pack_promotion_candidate,
)
from ai_video_production.multimodal_scoring import EvidenceValidity
from ai_video_production.owner_decision_store import (
    HumanDecision,
    OwnerDecisionEntry,
    OwnerDecisionHistory,
)
from ai_video_production.owner_profile_materialization import (
    compile_owner_profile_materialization_candidate,
)
from ai_video_production.owner_profile_registry import compile_owner_profile_registry_candidate
from ai_video_production.owner_profile_registry_store import (
    OwnerProfileRegistryStore,
    confirm_owner_profile_registry_registration,
)
from ai_video_production.owner_profile_store import (
    OwnerProfileStore,
    confirm_owner_profile_materialization,
)
from ai_video_production.profile_tuning_owner_decision import (
    compile_profile_tuning_owner_decision_binding,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import sha256_bytes
from test_task019_owner_decision_bridge import _profile_proposal, _selections
from test_task029_owner_decision_store import TestCipher


ROOT = Path(__file__).resolve().parents[1]
METRIC_IDS = (
    "human_acceptance", "qa_compliance", "quality_improvement",
    "rework_reduction", "sample_confidence", "time_reduction",
)


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def evidence(owner: str, project: str, prefix: str, number: int) -> HumanActionEvidence:
    return HumanActionEvidence(
        f"human-action.{prefix}.{number}", owner, project, "TASK-055",
        digest(f"source:{prefix}:{number}"), "montage.timing",
        ("event:PALLET_DROP", "style:dbd-aggressive"), digest("before"),
        digest("proposed"), digest("final"), HumanDisposition.MODIFIED,
        EvidenceValidity.CURRENT_VALID, False, False, False,
        HardGateState.PASS, HardGateState.PASS, 1_800_000_000_000 + number, 10_000,
    )


def decision_candidate(
    owner: str, project: str, prefix: str, number: int,
    *, regression: bool = False,
):
    rows = (evidence(owner, project, prefix, number * 2 - 1), evidence(owner, project, prefix, number * 2))
    observed = [490 if regression and name == "qa_compliance" else 530 for name in METRIC_IDS]
    metrics = tuple(
        MetricEvaluation(name, 500, value, 10, EvidenceValidity.CURRENT_VALID)
        for name, value in zip(METRIC_IDS, observed, strict=True)
    )
    policy = OwnerLearningPolicy("owner-learning.pack-source", "1.0.0", 2, 10, 10, 50)
    candidate = compile_owner_decision_candidate(
        f"owner-decision.{number:03d}", owner,
        "hypothesis.shared.audio" if number == 1 else "hypothesis.shared.visual",
        rows, metrics, policy,
    )
    return candidate, rows


def source(tmp_path: Path, prefix: str, *, project: str | None = None, regression: bool = False):
    owner = digest(f"owner:{prefix}")
    project_scope = digest(f"project:{prefix}") if project is None else project
    first, first_evidence = decision_candidate(owner, project_scope, prefix, 1, regression=regression)
    second, _ = decision_candidate(owner, project_scope, prefix, 2)
    first_entry = OwnerDecisionEntry(
        1, "decision.001", first.to_dict(), HumanDecision.ADOPTED,
        ("human.explicit-review",), 1_800_000_100_001, None,
    )
    second_entry = OwnerDecisionEntry(
        2, "decision.002", second.to_dict(), HumanDecision.ADOPTED,
        ("human.explicit-review",), 1_800_000_100_002,
        first_entry.to_dict()["entry_sha256"],
    )
    decisions = OwnerDecisionHistory(
        f"owner-decisions.{prefix}", owner, 2, (first_entry, second_entry)
    )
    proposal = _profile_proposal()
    selections = _selections()
    binding = compile_profile_tuning_owner_decision_binding(proposal, decisions, selections)
    materialization = compile_owner_profile_materialization_candidate(
        f"owner-profile.materialization.{prefix}", proposal, binding, decisions, selections
    )
    confirmation = confirm_owner_profile_materialization(
        confirmation_id=f"owner-profile.confirmation.{prefix}",
        candidate=materialization, confirmed_at_epoch_ms=1_800_000_200_000,
        human_confirmed=True,
    )
    profile_store = OwnerProfileStore(tmp_path / f"profiles-{prefix}.json", TestCipher())
    saved_profile = profile_store.append(
        store_id=f"owner-profiles.{prefix}", owner_scope_sha256=owner,
        candidate_id=materialization.candidate_id, proposal=proposal, binding=binding,
        decision_history=decisions, selections=selections, confirmation=confirmation,
        expected_revision=0,
    )
    registry_candidate = compile_owner_profile_registry_candidate(
        f"owner-profile.registry-candidate.{prefix}", saved_profile.history,
        expected_history_revision=1,
    )
    registry_confirmation = confirm_owner_profile_registry_registration(
        confirmation_id=f"owner-profile.registry-confirmation.{prefix}",
        candidate=registry_candidate, confirmed_at_epoch_ms=1_800_000_300_000,
        human_confirmed=True,
    )
    registry_store = OwnerProfileRegistryStore(
        tmp_path / f"registry-{prefix}.json", TestCipher()
    )
    saved_registry = registry_store.append(
        registry_id=f"owner-profile-registry.{prefix}",
        registry_candidate_id=registry_candidate.registry_candidate_id,
        source_profile_store=profile_store, expected_source_history_revision=1,
        confirmation=registry_confirmation, expected_registry_revision=0,
    )
    sorted_evidence = tuple(sorted(first_evidence, key=lambda row: row.to_dict()["evidence_sha256"]))
    return KnowledgePackSource(saved_registry.history, decisions, "decision.001", sorted_evidence)


def policy(**overrides: int) -> KnowledgePackCandidatePolicy:
    values = {
        "minimum_owner_count": 2,
        "minimum_project_count": 2,
        "minimum_samples_per_axis": 20,
        "minimum_owner_weighted_benefit_milli": 10,
        "maximum_axis_regression_milli": 0,
    }
    values.update(overrides)
    return KnowledgePackCandidatePolicy("knowledge-pack.conservative", "1.0.0", **values)


def test_cross_owner_project_candidate_is_exact_private_and_no_effect(tmp_path: Path) -> None:
    sources = (source(tmp_path, "a"), source(tmp_path, "b"))
    candidate = compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.audio-energy.001", "audio.energy", sources, policy()
    )
    payload = candidate.to_dict()
    assert candidate.state is KnowledgePackCandidateState.READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW
    assert payload["source_owner_count"] == 2
    assert payload["source_project_count"] == 2
    assert payload["source_evidence_count"] == 4
    assert len(payload["source_coordinate_sha256s"]) == 2
    assert payload["owner_scope_coordinates_included"] is False
    assert payload["project_scope_coordinates_included"] is False
    for item in sources:
        assert item.registry_history.owner_scope_sha256 not in str(payload)
        for row in item.evidence:
            assert row.project_scope_sha256 not in str(payload)
    for field in (
        "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized", "runtime_profile_apply_authorized",
        "rollback_execution_authorized", "release_authorized", "external_effect_authorized",
    ):
        assert payload[field] is False
    validate_instance("knowledge-pack-promotion-candidate.schema.json", payload)


def test_deterministic_round_trip_and_exact_source_revalidation(tmp_path: Path) -> None:
    sources = (source(tmp_path, "a"), source(tmp_path, "b"))
    first = compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.audio-energy.001", "audio.energy", sources, policy()
    )
    second = compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.audio-energy.001", "audio.energy", reversed(sources), policy()
    )
    assert first.to_dict() == second.to_dict()
    assert KnowledgePackPromotionCandidate.from_dict(first.to_dict()).to_dict() == first.to_dict()
    verify_knowledge_pack_promotion_candidate(
        first.to_dict(), first.candidate_id, "audio.energy", sources, policy()
    )
    tampered = deepcopy(first.to_dict())
    tampered["source_owner_count"] = 3
    with pytest.raises(ValueError, match="exact current sources"):
        verify_knowledge_pack_promotion_candidate(
            tampered, first.candidate_id, "audio.energy", sources, policy()
        )


def test_diversity_sample_benefit_and_axis_states_remain_distinct(tmp_path: Path) -> None:
    only = (source(tmp_path, "a"),)
    assert compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.owner-gap", "audio.energy", only, policy()
    ).state is KnowledgePackCandidateState.INSUFFICIENT_OWNER_DIVERSITY

    shared_project = digest("project:shared")
    same_project = (
        source(tmp_path, "b", project=shared_project),
        source(tmp_path, "c", project=shared_project),
    )
    assert compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.project-gap", "audio.energy", same_project, policy()
    ).state is KnowledgePackCandidateState.INSUFFICIENT_PROJECT_DIVERSITY

    good = (source(tmp_path, "d"), source(tmp_path, "e"))
    assert compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.sample-gap", "audio.energy", good,
        policy(minimum_samples_per_axis=21),
    ).state is KnowledgePackCandidateState.INSUFFICIENT_SAMPLES
    assert compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.benefit-gap", "audio.energy", good,
        policy(minimum_owner_weighted_benefit_milli=31),
    ).state is KnowledgePackCandidateState.NO_REPRODUCIBLE_BENEFIT

    regression = (source(tmp_path, "f", regression=True), source(tmp_path, "g"))
    assert compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.axis-regression", "audio.energy", regression, policy()
    ).state is KnowledgePackCandidateState.AXIS_REGRESSION


def test_lineage_scope_evidence_and_feature_mismatch_fail_closed(tmp_path: Path) -> None:
    first = source(tmp_path, "a")
    second = source(tmp_path, "b")
    with pytest.raises(ValueError, match="one source per Owner"):
        compile_knowledge_pack_promotion_candidate(
            "knowledge-pack.duplicate-owner", "audio.energy", (first, first), policy()
        )
    wrong_evidence = replace(second, evidence=first.evidence)
    with pytest.raises(ValueError, match="does not match the decision|owner scope mismatch"):
        compile_knowledge_pack_promotion_candidate(
            "knowledge-pack.wrong-evidence", "audio.energy", (first, wrong_evidence), policy()
        )
    with pytest.raises(ValueError, match="absent"):
        compile_knowledge_pack_promotion_candidate(
            "knowledge-pack.missing-feature", "subtitle.nonexistent", (first, second), policy()
        )


def test_candidate_is_immutable_schema_mirror_exact_and_module_is_pure(tmp_path: Path) -> None:
    candidate = compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.audio-energy.001", "audio.energy",
        (source(tmp_path, "a"), source(tmp_path, "b")), policy(),
    )
    with pytest.raises(FrozenInstanceError):
        candidate.state = KnowledgePackCandidateState.AXIS_REGRESSION  # type: ignore[misc]
    with pytest.raises(ValueError, match="state does not match"):
        replace(candidate, state=KnowledgePackCandidateState.AXIS_REGRESSION)
    with pytest.raises(ValueError, match="source_owner_count"):
        replace(candidate, source_owner_count=3)
    with pytest.raises(ValueError, match="must remain false"):
        tampered = candidate.to_dict()
        tampered["release_authorized"] = True
        KnowledgePackPromotionCandidate.from_dict(tampered)
    assert (ROOT / "schemas/knowledge-pack-promotion-candidate.schema.json").read_bytes() == (
        ROOT / "src/ai_video_production/schema_resources/knowledge-pack-promotion-candidate.schema.json"
    ).read_bytes()

    import ai_video_production.knowledge_pack_candidate as module
    source_text = inspect.getsource(module)
    tree = ast.parse(source_text)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported_roots.intersection(
        {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "sqlite3"}
    )
    for field in ("raw_media", "transcript_text", "prompt_body", "host_path", "credential"):
        assert f'"{field}"' not in source_text
