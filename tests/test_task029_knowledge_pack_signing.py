from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import inspect
from pathlib import Path

import pytest

from ai_video_production.knowledge_pack_candidate import compile_knowledge_pack_promotion_candidate
from ai_video_production.knowledge_pack_signing import (
    CriticKnowledgePackDecision,
    HumanKnowledgePackDecision,
    HumanKnowledgePackReview,
    IndependentKnowledgePackCriticReview,
    KnowledgePackSigningCandidate,
    KnowledgePackSigningState,
    compile_knowledge_pack_signing_candidate,
    confirm_human_knowledge_pack_review,
    confirm_independent_knowledge_pack_critic_review,
    verify_knowledge_pack_signing_candidate,
)
from ai_video_production.schema_contracts import validate_instance
from test_task029_knowledge_pack_candidate import digest, policy, source


ROOT = Path(__file__).resolve().parents[1]


def bundle(tmp_path: Path, *, human_reject: bool = False, critic_reject: bool = False):
    sources = (source(tmp_path, "a"), source(tmp_path, "b"))
    source_candidate = compile_knowledge_pack_promotion_candidate(
        "knowledge-pack.audio-energy.001", "audio.energy", sources, policy()
    )
    human = confirm_human_knowledge_pack_review(
        review_id="knowledge-pack.human-review.001",
        candidate=source_candidate,
        reviewer_coordinate_sha256=digest("reviewer:human"),
        decision=(
            HumanKnowledgePackDecision.REJECT
            if human_reject
            else HumanKnowledgePackDecision.APPROVE_FOR_INDEPENDENT_CRITIC
        ),
        reason_codes=("human.explicit-review",),
        reviewed_at_epoch_ms=1_800_000_400_000,
    )
    critic = confirm_independent_knowledge_pack_critic_review(
        review_id="knowledge-pack.critic-review.001",
        candidate=source_candidate,
        reviewer_coordinate_sha256=digest("reviewer:critic"),
        critic_report_sha256=digest("critic-report:001"),
        decision=(
            CriticKnowledgePackDecision.REJECT
            if critic_reject
            else CriticKnowledgePackDecision.ACCEPT_FOR_EXTERNAL_SIGNATURE
        ),
        unresolved_critical_count=0,
        unresolved_high_count=0,
        reason_codes=("critic.independent-review",),
        reviewed_at_epoch_ms=1_800_000_500_000,
    )
    kwargs = {
        "signing_candidate_id": "knowledge-pack.signing-candidate.001",
        "pack_id": "knowledge-pack.audio-energy",
        "pack_version": "1.0.0",
        "source_candidate_payload": source_candidate.to_dict(),
        "source_candidate_id": source_candidate.candidate_id,
        "feature_key": "audio.energy",
        "sources": sources,
        "policy": policy(),
        "human_review": human,
        "critic_review": critic,
        "predecessor_pack_sha256": None,
    }
    return source_candidate, human, critic, kwargs


def test_ready_candidate_is_exact_private_unsigned_and_no_effect(tmp_path: Path) -> None:
    source_candidate, human, critic, kwargs = bundle(tmp_path)
    result = compile_knowledge_pack_signing_candidate(**kwargs)
    payload = result.to_dict()
    assert result.state is KnowledgePackSigningState.READY_FOR_EXTERNAL_SIGNATURE
    assert payload["source_candidate_sha256"] == source_candidate.to_dict()["candidate_sha256"]
    assert payload["human_review_sha256"] == human.to_dict()["review_sha256"]
    assert payload["critic_review_sha256"] == critic.to_dict()["review_sha256"]
    assert payload["external_signature_required"] is True
    for field in (
        "owner_scope_coordinates_included", "project_scope_coordinates_included",
        "reviewer_coordinates_included", "raw_media_included", "text_body_included",
        "absolute_host_path_included", "credential_included", "signing_key_material_included",
        "signature_present", "signature_verified", "knowledge_pack_write_authorized",
        "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
        "runtime_profile_apply_authorized", "rollback_execution_authorized",
        "release_authorized", "external_effect_authorized",
    ):
        assert payload[field] is False
    assert human.reviewer_coordinate_sha256 not in str(payload)
    assert critic.reviewer_coordinate_sha256 not in str(payload)
    validate_instance("knowledge-pack-signing-candidate.schema.json", payload)


def test_round_trip_determinism_exact_revalidation_and_tamper_rejection(tmp_path: Path) -> None:
    _, human, critic, kwargs = bundle(tmp_path)
    first = compile_knowledge_pack_signing_candidate(**kwargs)
    second = compile_knowledge_pack_signing_candidate(**kwargs)
    assert first.to_dict() == second.to_dict()
    assert KnowledgePackSigningCandidate.from_dict(first.to_dict()).to_dict() == first.to_dict()
    assert HumanKnowledgePackReview.from_dict(human.to_dict()).to_dict() == human.to_dict()
    assert IndependentKnowledgePackCriticReview.from_dict(critic.to_dict()).to_dict() == critic.to_dict()
    verify_knowledge_pack_signing_candidate(first.to_dict(), **kwargs)
    tampered = deepcopy(first.to_dict())
    tampered["pack_version"] = "1.0.1"
    with pytest.raises(ValueError, match="exact current sources and reviews"):
        verify_knowledge_pack_signing_candidate(tampered, **kwargs)
    source_tampered = deepcopy(kwargs["source_candidate_payload"])
    source_tampered["source_owner_count"] = 3
    with pytest.raises(ValueError, match="exact current sources"):
        compile_knowledge_pack_signing_candidate(**(kwargs | {"source_candidate_payload": source_tampered}))


def test_human_and_critic_rejection_states_remain_distinct(tmp_path: Path) -> None:
    assert compile_knowledge_pack_signing_candidate(
        **bundle(tmp_path / "human", human_reject=True)[3]
    ).state is KnowledgePackSigningState.HUMAN_REJECTED
    assert compile_knowledge_pack_signing_candidate(
        **bundle(tmp_path / "critic", critic_reject=True)[3]
    ).state is KnowledgePackSigningState.CRITIC_REJECTED
    source_candidate, _, _, _ = bundle(tmp_path / "finding")
    with pytest.raises(ValueError, match="zero unresolved Critical/High"):
        confirm_independent_knowledge_pack_critic_review(
            review_id="knowledge-pack.critic-review.finding",
            candidate=source_candidate,
            reviewer_coordinate_sha256=digest("reviewer:critic:finding"),
            critic_report_sha256=digest("critic-report:finding"),
            decision=CriticKnowledgePackDecision.ACCEPT_FOR_EXTERNAL_SIGNATURE,
            unresolved_critical_count=0,
            unresolved_high_count=1,
            reason_codes=("critic.high-open",),
            reviewed_at_epoch_ms=1_800_000_500_001,
        )


def test_review_independence_and_exact_binding_fail_closed(tmp_path: Path) -> None:
    _, human, critic, kwargs = bundle(tmp_path)
    same_reviewer = replace(critic, reviewer_coordinate_sha256=human.reviewer_coordinate_sha256)
    with pytest.raises(ValueError, match="reviewers must be independent"):
        compile_knowledge_pack_signing_candidate(**(kwargs | {"critic_review": same_reviewer}))
    wrong_binding = replace(critic, source_candidate_sha256=digest("wrong-candidate"))
    with pytest.raises(ValueError, match="does not bind the exact current candidate"):
        compile_knowledge_pack_signing_candidate(**(kwargs | {"critic_review": wrong_binding}))
    with pytest.raises(ValueError, match="review IDs must be distinct"):
        compile_knowledge_pack_signing_candidate(
            **(kwargs | {"critic_review": replace(critic, review_id=human.review_id)})
        )


def test_candidate_is_immutable_schema_mirror_exact_and_module_is_pure(tmp_path: Path) -> None:
    candidate = compile_knowledge_pack_signing_candidate(**bundle(tmp_path)[3])
    with pytest.raises(FrozenInstanceError):
        candidate.state = KnowledgePackSigningState.CRITIC_REJECTED  # type: ignore[misc]
    with pytest.raises(ValueError, match="must remain false"):
        tampered = candidate.to_dict()
        tampered["signature_present"] = True
        KnowledgePackSigningCandidate.from_dict(tampered)
    assert (ROOT / "schemas/knowledge-pack-signing-candidate.schema.json").read_bytes() == (
        ROOT / "src/ai_video_production/schema_resources/knowledge-pack-signing-candidate.schema.json"
    ).read_bytes()
    import ai_video_production.knowledge_pack_signing as module
    tree = ast.parse(inspect.getsource(module))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported_roots.intersection(
        {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "sqlite3", "cryptography"}
    )
