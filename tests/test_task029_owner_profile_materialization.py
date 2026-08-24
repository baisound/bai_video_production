from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path

import pytest

from ai_video_production.owner_decision_store import HumanDecision
from ai_video_production.owner_profile_materialization import (
    OwnerProfileMaterializationState,
    compile_owner_profile_materialization_candidate,
    verify_owner_profile_materialization_candidate,
)
from ai_video_production.profile_tuning_owner_decision import (
    compile_profile_tuning_owner_decision_binding,
)
from ai_video_production.schema_contracts import validate_instance
from test_task019_owner_decision_bridge import (
    _history,
    _profile_proposal,
    _selections,
)


ROOT = Path(__file__).resolve().parents[1]


def _materialization(*, complete: bool = True, rejected: bool = False):
    proposal = _profile_proposal(complete=complete)
    history = _history(
        second_decision=HumanDecision.REJECTED
        if rejected
        else HumanDecision.ADOPTED
    )
    selections = _selections()
    binding = compile_profile_tuning_owner_decision_binding(
        proposal, history, selections
    )
    candidate = compile_owner_profile_materialization_candidate(
        "owner-profile.materialization.001",
        proposal,
        binding,
        history,
        selections,
    )
    return proposal, history, selections, binding, candidate


def test_ready_candidate_exposes_exact_proposed_profile_without_authority() -> None:
    proposal, history, _, binding, candidate = _materialization()
    payload = candidate.to_dict()

    assert candidate.state is OwnerProfileMaterializationState.READY_FOR_HUMAN_MATERIALIZATION
    assert payload["profile_snapshot"] == proposal.proposed_profile.to_dict()
    assert payload["decision_history_sha256"] == history.to_dict()["history_sha256"]
    assert payload["binding_sha256"] == binding.to_dict()["binding_sha256"]
    assert payload["source_decision_ids"] == ["decision.001", "decision.002"]
    for field in (
        "owner_profile_store_write_authorized",
        "model_profile_registry_write_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "rollback_execution_authorized",
        "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        assert payload[field] is False
    validate_instance("owner-profile-materialization-candidate.schema.json", payload)


def test_candidate_is_deterministic_and_exactly_verifiable() -> None:
    proposal, history, selections, binding, first = _materialization()
    second = compile_owner_profile_materialization_candidate(
        first.candidate_id,
        proposal,
        binding,
        history,
        reversed(selections),
    )
    assert first.to_dict() == second.to_dict()
    verify_owner_profile_materialization_candidate(
        first.to_dict(),
        first.candidate_id,
        proposal,
        binding,
        history,
        selections,
    )


@pytest.mark.parametrize(
    ("complete", "rejected", "state"),
    (
        (False, False, "PROFILE_PROPOSAL_NOT_READY"),
        (True, True, "REJECTED_OWNER_DECISION_PRESENT"),
    ),
)
def test_nonready_sources_never_expose_profile_snapshot(
    complete: bool, rejected: bool, state: str
) -> None:
    *_, candidate = _materialization(complete=complete, rejected=rejected)
    payload = candidate.to_dict()
    assert payload["state"] == state
    assert payload["profile_snapshot"] is None
    validate_instance("owner-profile-materialization-candidate.schema.json", payload)


def test_payload_and_latest_history_drift_fail_closed() -> None:
    proposal, history, selections, binding, candidate = _materialization()
    payload = candidate.to_dict()
    tampered = deepcopy(payload)
    tampered["decision_history_revision"] = 3
    with pytest.raises(ValueError, match="exact sources"):
        verify_owner_profile_materialization_candidate(
            tampered, candidate.candidate_id, proposal, binding, history, selections
        )
    with pytest.raises(ValueError):
        compile_owner_profile_materialization_candidate(
            candidate.candidate_id,
            proposal,
            binding,
            _history(second_decision=HumanDecision.REJECTED),
            selections,
        )


def test_candidate_is_immutable() -> None:
    *_, candidate = _materialization()
    with pytest.raises(FrozenInstanceError):
        candidate.state = OwnerProfileMaterializationState.PROFILE_PROPOSAL_NOT_READY  # type: ignore[misc]


def test_schema_mirror_is_byte_identical() -> None:
    assert (
        ROOT / "schemas/owner-profile-materialization-candidate.schema.json"
    ).read_bytes() == (
        ROOT
        / "src/ai_video_production/schema_resources"
        / "owner-profile-materialization-candidate.schema.json"
    ).read_bytes()


def test_public_surface_has_no_io_store_or_mutation_capability() -> None:
    import ai_video_production.owner_profile_materialization as module

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
