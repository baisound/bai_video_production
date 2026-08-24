from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.owner_profile_registry import (
    OwnerProfileRegistryCandidate,
    compile_owner_profile_registry_candidate,
)
from ai_video_production.owner_profile_registry_store import (
    OwnerProfileRegistryHistory,
    OwnerProfileRegistryStore,
    WindowsDpapiOwnerProfileRegistryCipher,
    confirm_owner_profile_registry_registration,
)
from ai_video_production.owner_profile_store import OwnerProfileStore
from ai_video_production.schema_contracts import validate_instance
from test_task029_owner_decision_store import TestCipher
from test_task029_owner_profile_store import append as append_owner_profile


ROOT = Path(__file__).resolve().parents[1]
SHA_B = "sha256:" + "b" * 64


def source_and_candidate(tmp_path: Path) -> tuple[OwnerProfileStore, OwnerProfileRegistryCandidate]:
    source = OwnerProfileStore(tmp_path / "owner-profiles.json", TestCipher())
    saved, _, _ = append_owner_profile(source)
    candidate = compile_owner_profile_registry_candidate(
        "owner-profile.registry-candidate.001",
        saved.history,
        expected_history_revision=1,
    )
    return source, candidate


def register(tmp_path: Path, *, cipher: TestCipher | None = None):
    source, candidate = source_and_candidate(tmp_path)
    confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    registry = OwnerProfileRegistryStore(
        tmp_path / "owner-profile-registry.json",
        TestCipher() if cipher is None else cipher,
    )
    saved = registry.append(
        registry_id="owner-profile-registry.default",
        registry_candidate_id=candidate.registry_candidate_id,
        source_profile_store=source,
        expected_source_history_revision=1,
        confirmation=confirmation,
        expected_registry_revision=0,
    )
    return registry, source, candidate, confirmation, saved


def test_explicit_confirmation_encrypted_round_trip_and_no_effect_authority(tmp_path: Path) -> None:
    registry, _, candidate, confirmation, saved = register(tmp_path)
    raw = registry.path.read_bytes()
    assert candidate.registry_candidate_id.encode() not in raw
    assert confirmation.confirmation_id.encode() not in raw
    loaded = OwnerProfileRegistryStore(registry.path, TestCipher()).load()
    assert loaded.to_dict() == saved.history.to_dict()
    with pytest.raises(FrozenInstanceError):
        loaded.revisions[0].candidate.registry_candidate_id = "mutated"  # type: ignore[misc]

    document = loaded.to_dict()
    revision = document["revisions"][0]
    assert document["owner_local_profile_registry"] is True
    assert document["explicit_human_registry_confirmation_required"] is True
    assert revision["registered_in_model_profile_registry"] is True
    assert revision["registration_authority_consumed"] is True
    for field in (
        "runtime_profile_apply_authorized", "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized", "rollback_execution_authorized",
        "external_effect_authorized",
    ):
        assert document[field] is False
    validate_instance(
        "owner-profile-registry-store.schema.json",
        json.loads(registry.path.read_text(encoding="utf-8")),
    )


def test_confirmation_is_separate_exact_and_candidate_round_trip(tmp_path: Path) -> None:
    source, candidate = source_and_candidate(tmp_path)
    with pytest.raises(ValueError, match="explicit Human registry confirmation"):
        confirm_owner_profile_registry_registration(
            confirmation_id="owner-profile.registry-confirmation.denied",
            candidate=candidate,
            confirmed_at_epoch_ms=1_800_000_000_000,
            human_confirmed=False,
        )
    confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    assert OwnerProfileRegistryCandidate.from_dict(candidate.to_dict()).to_dict() == candidate.to_dict()
    wrong = replace(confirmation, registry_candidate_sha256=SHA_B)
    with pytest.raises(ValueError, match="does not match"):
        OwnerProfileRegistryStore(tmp_path / "registry.json", TestCipher()).append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=wrong,
            expected_registry_revision=0,
        )


def test_candidate_unknown_tamper_and_confirmation_tamper_fail_closed(tmp_path: Path) -> None:
    _, candidate = source_and_candidate(tmp_path)
    unknown = deepcopy(candidate.to_dict())
    unknown["unexpected"] = False
    with pytest.raises(ValueError, match="incomplete or unknown"):
        OwnerProfileRegistryCandidate.from_dict(unknown)
    tampered = deepcopy(candidate.to_dict())
    tampered["runtime_profile_apply_authorized"] = True
    with pytest.raises(ValueError, match="must remain false"):
        OwnerProfileRegistryCandidate.from_dict(tampered)
    confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    confirmation_payload = confirmation.to_dict()
    confirmation_payload["automatic_registry_write_authorized"] = True
    from ai_video_production.owner_profile_registry_store import OwnerProfileRegistryConfirmation
    with pytest.raises(ValueError, match="must remain false"):
        OwnerProfileRegistryConfirmation.from_dict(confirmation_payload)


def test_source_revalidation_registry_cas_scope_and_replay_fail_closed(tmp_path: Path) -> None:
    registry, source, candidate, confirmation, saved = register(tmp_path)
    with pytest.raises(ValueError, match="changed since"):
        registry.append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=2,
            confirmation=confirmation,
            expected_registry_revision=1,
        )
    with pytest.raises(ProductError) as conflict:
        registry.append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=confirmation,
            expected_registry_revision=0,
        )
    assert conflict.value.code == "ERR_OWNER_PROFILE_REGISTRY_STORE_CONFLICT"
    with pytest.raises(ProductError) as scope:
        registry.append(
            registry_id="owner-profile-registry.other",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=confirmation,
            expected_registry_revision=1,
        )
    assert scope.value.code == "ERR_OWNER_PROFILE_REGISTRY_STORE_SCOPE"
    with pytest.raises(ValueError, match="source Owner Profile revision must advance"):
        registry.append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=confirmation,
            expected_registry_revision=1,
        )
    assert saved.history.revision == 1


def test_authenticated_tamper_wrong_key_plaintext_and_atomic_failure(tmp_path: Path) -> None:
    registry, source, candidate, confirmation, saved = register(tmp_path)
    original = registry.path.read_bytes()
    envelope = json.loads(original.decode("utf-8"))
    envelope["ciphertext_sha256"] = SHA_B
    registry.path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ProductError) as tamper:
        registry.load()
    assert tamper.value.code == "ERR_OWNER_PROFILE_REGISTRY_STORE_INTEGRITY"
    registry.path.write_bytes(original)
    with pytest.raises(ProductError):
        OwnerProfileRegistryStore(registry.path, TestCipher(b"wrong")).load()
    plain = tmp_path / "plain-registry.json"
    plain.write_text(
        json.dumps(OwnerProfileRegistryHistory(
            "owner-profile-registry.default", candidate.owner_scope_sha256,
            candidate.source_store_id, 0, (),
        ).to_dict()),
        encoding="utf-8",
    )
    with pytest.raises(ProductError):
        OwnerProfileRegistryStore(plain, TestCipher()).load()

    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("simulated power loss")

    failed_path = tmp_path / "failed-registry.json"
    with pytest.raises(RuntimeError, match="simulated power loss"):
        OwnerProfileRegistryStore(failed_path, TestCipher()).append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=confirmation,
            expected_registry_revision=0,
            failure_injector=fail,
        )
    assert not failed_path.exists()
    assert saved.history.revision == 1


def test_separate_path_symlink_schema_mirror_and_platform_boundary(tmp_path: Path) -> None:
    source, candidate = source_and_candidate(tmp_path)
    confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    with pytest.raises(ValueError, match="separate files"):
        OwnerProfileRegistryStore(source.path, TestCipher()).append(
            registry_id="owner-profile-registry.default",
            registry_candidate_id=candidate.registry_candidate_id,
            source_profile_store=source,
            expected_source_history_revision=1,
            confirmation=confirmation,
            expected_registry_revision=0,
        )
    link = tmp_path / "registry-link.json"
    try:
        link.symlink_to(source.path)
    except OSError:
        pass
    else:
        with pytest.raises(ProductError):
            OwnerProfileRegistryStore(link, TestCipher()).load()
    assert (ROOT / "schemas/owner-profile-registry-store.schema.json").read_bytes() == (
        ROOT / "src/ai_video_production/schema_resources" / "owner-profile-registry-store.schema.json"
    ).read_bytes()
    if os.name != "nt":
        with pytest.raises(ProductError) as unavailable:
            WindowsDpapiOwnerProfileRegistryCipher()
        assert unavailable.value.code == "ERR_OWNER_PROFILE_REGISTRY_ENCRYPTION_UNAVAILABLE"


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI runtime only")
def test_windows_dpapi_real_synthetic_registry_round_trip(tmp_path: Path) -> None:
    source, candidate = source_and_candidate(tmp_path)
    confirmation = confirm_owner_profile_registry_registration(
        confirmation_id="owner-profile.registry-confirmation.dpapi",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_000_000,
        human_confirmed=True,
    )
    path = tmp_path / "owner-profile-registry-dpapi.json"
    saved = OwnerProfileRegistryStore(path).append(
        registry_id="owner-profile-registry.default",
        registry_candidate_id=candidate.registry_candidate_id,
        source_profile_store=source,
        expected_source_history_revision=1,
        confirmation=confirmation,
        expected_registry_revision=0,
    )
    assert OwnerProfileRegistryStore(path).load().to_dict() == saved.history.to_dict()
    assert candidate.registry_candidate_id.encode() not in path.read_bytes()
