from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import inspect
from pathlib import Path

import pytest

from ai_video_production.owner_profile_registry import (
    OwnerProfileRegistryCandidateState,
    SCORING_PROFILE_COMPATIBILITY_CONTRACT,
    compile_owner_profile_registry_candidate,
    verify_owner_profile_registry_candidate,
)
from ai_video_production.owner_profile_store import OwnerProfileHistory, OwnerProfileStore
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task029_owner_decision_store import TestCipher
from test_task029_owner_profile_store import append


ROOT = Path(__file__).resolve().parents[1]


def materialized_history(tmp_path: Path) -> OwnerProfileHistory:
    saved, _, _ = append(OwnerProfileStore(tmp_path / "owner-profiles.json", TestCipher()))
    return saved.history


def test_latest_materialized_profile_compiles_exact_no_effect_candidate(tmp_path: Path) -> None:
    history = materialized_history(tmp_path)
    candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001",
        history,
        expected_history_revision=1,
    )
    payload = candidate.to_dict()
    latest = history.revisions[-1].to_dict()

    assert candidate.state is OwnerProfileRegistryCandidateState.READY_FOR_HUMAN_REGISTRY_REVIEW
    assert payload["source_history_sha256"] == history.to_dict()["history_sha256"]
    assert payload["source_profile_revision_sha256"] == latest["revision_sha256"]
    assert payload["source_materialization_sha256"] == latest["candidate"]["materialization_sha256"]
    assert payload["source_confirmation_sha256"] == latest["confirmation"]["confirmation_sha256"]
    assert payload["profile_snapshot"] == latest["candidate"]["profile_snapshot"]
    assert payload["compatibility_contract"] == SCORING_PROFILE_COMPATIBILITY_CONTRACT
    assert payload["owner_local_profile_only"] is True
    for field in (
        "model_profile_registry_write_authorized",
        "runtime_profile_apply_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "rollback_execution_authorized",
        "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        assert payload[field] is False
    validate_instance("owner-profile-registry-candidate.schema.json", payload)


def test_candidate_is_deterministic_and_exactly_revalidated(tmp_path: Path) -> None:
    history = materialized_history(tmp_path)
    first = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001", history, expected_history_revision=1
    )
    second = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001",
        OwnerProfileHistory.from_dict(history.to_dict()),
        expected_history_revision=1,
    )
    assert first.to_dict() == second.to_dict()
    verify_owner_profile_registry_candidate(
        first.to_dict(),
        first.registry_candidate_id,
        history,
        expected_history_revision=1,
    )


def test_empty_stale_and_wrong_history_fail_closed(tmp_path: Path) -> None:
    history = materialized_history(tmp_path)
    empty = OwnerProfileHistory(history.store_id, history.owner_scope_sha256, 0, ())
    with pytest.raises(ValueError, match="materialized Owner Profile"):
        compile_owner_profile_registry_candidate(
            "owner-profile.registry-candidate.empty", empty, expected_history_revision=1
        )
    with pytest.raises(ValueError, match="changed since"):
        compile_owner_profile_registry_candidate(
            "owner-profile.registry-candidate.stale", history, expected_history_revision=2
        )
    with pytest.raises(ValueError, match="OwnerProfileHistory"):
        compile_owner_profile_registry_candidate(
            "owner-profile.registry-candidate.wrong", object(), expected_history_revision=1  # type: ignore[arg-type]
        )


def test_payload_or_history_drift_fails_exact_verification(tmp_path: Path) -> None:
    history = materialized_history(tmp_path)
    candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001", history, expected_history_revision=1
    )
    tampered = deepcopy(candidate.to_dict())
    tampered["source_history_revision"] = 2
    with pytest.raises(ValueError, match="exact latest"):
        verify_owner_profile_registry_candidate(
            tampered,
            candidate.registry_candidate_id,
            history,
            expected_history_revision=1,
        )


def test_hash_consistent_but_semantically_invalid_profile_fails_closed(tmp_path: Path) -> None:
    document = deepcopy(materialized_history(tmp_path).to_dict())
    revision = document["revisions"][-1]
    candidate = revision["candidate"]
    confirmation = revision["confirmation"]
    profile = candidate["profile_snapshot"]
    profile["rules"][0]["raw_range"]["maximum"] = profile["rules"][0]["raw_range"]["minimum"]
    profile_body = {key: value for key, value in profile.items() if key != "profile_sha256"}
    profile["profile_sha256"] = sha256_bytes(canonical_json_bytes(profile_body))
    candidate["proposed_profile_sha256"] = profile["profile_sha256"]
    candidate_body = {key: value for key, value in candidate.items() if key != "materialization_sha256"}
    candidate["materialization_sha256"] = sha256_bytes(canonical_json_bytes(candidate_body))
    confirmation["profile_sha256"] = profile["profile_sha256"]
    confirmation["candidate_sha256"] = candidate["materialization_sha256"]
    confirmation_body = {key: value for key, value in confirmation.items() if key != "confirmation_sha256"}
    confirmation["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(confirmation_body))
    revision_body = {key: value for key, value in revision.items() if key != "revision_sha256"}
    revision["revision_sha256"] = sha256_bytes(canonical_json_bytes(revision_body))
    history_body = {key: value for key, value in document.items() if key != "history_sha256"}
    document["history_sha256"] = sha256_bytes(canonical_json_bytes(history_body))
    reconstructed = OwnerProfileHistory.from_dict(document)

    with pytest.raises(ValueError, match="raw_maximum"):
        compile_owner_profile_registry_candidate(
            "owner-profile.registry-candidate.invalid",
            reconstructed,
            expected_history_revision=1,
        )


def test_candidate_is_immutable_and_schema_mirror_is_exact(tmp_path: Path) -> None:
    candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001",
        materialized_history(tmp_path),
        expected_history_revision=1,
    )
    profile_sha256 = candidate.profile_snapshot.to_dict()["profile_sha256"]
    with pytest.raises(ValueError, match="differ from its baseline"):
        replace(
            candidate,
            baseline_profile_sha256=profile_sha256,
            rollback_profile_sha256=profile_sha256,
        )
    with pytest.raises(FrozenInstanceError):
        candidate.state = OwnerProfileRegistryCandidateState.READY_FOR_HUMAN_REGISTRY_REVIEW  # type: ignore[misc]
    assert (ROOT / "schemas/owner-profile-registry-candidate.schema.json").read_bytes() == (
        ROOT
        / "src/ai_video_production/schema_resources"
        / "owner-profile-registry-candidate.schema.json"
    ).read_bytes()


def test_public_surface_is_pure_and_contains_no_private_body_fields() -> None:
    import ai_video_production.owner_profile_registry as module

    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported_roots.intersection(
        {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "sqlite3"}
    )
    forbidden = {"raw_media", "transcript_text", "prompt_body", "host_path", "credential"}
    for field in forbidden:
        assert f'"{field}"' not in source
    assert "OwnerProfileStore(" not in source
