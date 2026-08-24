from __future__ import annotations

import base64
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.owner_decision_store import HumanDecision
from ai_video_production.owner_profile_materialization import (
    compile_owner_profile_materialization_candidate,
)
from ai_video_production.owner_profile_store import (
    OwnerProfileHistory,
    OwnerProfileMaterializationConfirmation,
    OwnerProfileStore,
    WindowsDpapiOwnerProfileCipher,
    confirm_owner_profile_materialization,
)
from ai_video_production.profile_tuning_owner_decision import (
    compile_profile_tuning_owner_decision_binding,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task019_owner_decision_bridge import _history, _profile_proposal, _selections
from test_task029_owner_decision_store import TestCipher


ROOT = Path(__file__).resolve().parents[1]
SHA_B = "sha256:" + "b" * 64


def sources(*, complete: bool = True, rejected: bool = False):
    proposal = _profile_proposal(complete=complete)
    history = _history(
        second_decision=HumanDecision.REJECTED if rejected else HumanDecision.ADOPTED
    )
    selections = _selections()
    binding = compile_profile_tuning_owner_decision_binding(proposal, history, selections)
    candidate = compile_owner_profile_materialization_candidate(
        "owner-profile.materialization.001", proposal, binding, history, selections
    )
    return proposal, history, selections, binding, candidate


def append(store: OwnerProfileStore, *, expected_revision: int = 0):
    proposal, history, selections, binding, candidate = sources()
    confirmation = confirm_owner_profile_materialization(
        confirmation_id="owner-profile.confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_700_000_300_000,
        human_confirmed=True,
    )
    result = store.append(
        store_id="owner-profiles.default",
        owner_scope_sha256=candidate.owner_scope_sha256,
        candidate_id=candidate.candidate_id,
        proposal=proposal,
        binding=binding,
        decision_history=history,
        selections=selections,
        confirmation=confirmation,
        expected_revision=expected_revision,
    )
    return result, candidate, confirmation


def test_explicit_confirmation_encrypted_round_trip_and_no_effect_authority(tmp_path: Path) -> None:
    path = tmp_path / "owner-profiles.json"
    saved, candidate, confirmation = append(OwnerProfileStore(path, TestCipher()))
    raw = path.read_bytes()
    assert candidate.candidate_id.encode() not in raw
    assert confirmation.confirmation_id.encode() not in raw
    assert candidate.owner_scope_sha256.encode() not in raw
    loaded = OwnerProfileStore(path, TestCipher()).load()
    assert loaded.to_dict() == saved.history.to_dict()
    document = loaded.to_dict()
    assert document["explicit_human_confirmation_required"] is True
    for field in (
        "model_profile_registry_write_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "rollback_execution_authorized",
        "external_effect_authorized",
    ):
        assert document[field] is False
    validate_instance("owner-profile-store.schema.json", json.loads(raw))


def test_confirmation_is_separate_exact_and_fail_closed() -> None:
    proposal, history, selections, binding, candidate = sources()
    with pytest.raises(ValueError, match="explicit Human"):
        confirm_owner_profile_materialization(
            confirmation_id="owner-profile.confirmation.denied",
            candidate=candidate,
            confirmed_at_epoch_ms=1_700_000_300_000,
            human_confirmed=False,
        )
    confirmation = confirm_owner_profile_materialization(
        confirmation_id="owner-profile.confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_700_000_300_000,
        human_confirmed=True,
    )
    wrong = OwnerProfileMaterializationConfirmation(
        "owner-profile.confirmation.wrong", SHA_B,
        candidate.owner_scope_sha256, candidate.proposed_profile_sha256,
        1_700_000_300_001,
    )
    store = OwnerProfileStore(Path("unused.json"), TestCipher())
    with pytest.raises(ValueError, match="does not match"):
        store.append(
            store_id="owner-profiles.default", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=history, selections=selections, confirmation=wrong,
            expected_revision=0,
        )
    assert confirmation.to_dict()["explicit_human_confirmation_received"] is True


@pytest.mark.parametrize("complete,rejected", ((False, False), (True, True)))
def test_nonready_candidate_cannot_be_confirmed_or_stored(complete: bool, rejected: bool) -> None:
    proposal, history, selections, binding, candidate = sources(
        complete=complete, rejected=rejected
    )
    with pytest.raises(ValueError, match="READY_FOR_HUMAN_MATERIALIZATION"):
        confirm_owner_profile_materialization(
            confirmation_id="owner-profile.confirmation.blocked",
            candidate=candidate,
            confirmed_at_epoch_ms=1_700_000_300_000,
            human_confirmed=True,
        )


def test_exact_source_revalidation_stale_revision_scope_and_replay_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "owner-profiles.json"
    store = OwnerProfileStore(path, TestCipher())
    saved, candidate, confirmation = append(store)
    assert saved.history.revision == 1
    proposal, history, selections, binding, _ = sources()
    with pytest.raises(ProductError) as conflict:
        store.append(
            store_id="owner-profiles.default", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=history, selections=selections, confirmation=confirmation,
            expected_revision=0,
        )
    assert conflict.value.code == "ERR_OWNER_PROFILE_STORE_CONFLICT"
    with pytest.raises(ProductError) as scope:
        store.append(
            store_id="owner-profiles.other", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=history, selections=selections, confirmation=confirmation,
            expected_revision=1,
        )
    assert scope.value.code == "ERR_OWNER_PROFILE_STORE_SCOPE"
    with pytest.raises(ValueError, match="baseline|replay"):
        store.append(
            store_id="owner-profiles.default", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=history, selections=selections, confirmation=confirmation,
            expected_revision=1,
        )
    with pytest.raises(ValueError):
        store.append(
            store_id="owner-profiles.default", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=_history(second_decision=HumanDecision.REJECTED),
            selections=selections, confirmation=confirmation, expected_revision=1,
        )


def test_authenticated_inner_and_envelope_tamper_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "owner-profiles.json"
    cipher = TestCipher()
    append(OwnerProfileStore(path, cipher))
    envelope = json.loads(path.read_text(encoding="utf-8"))
    plaintext = json.loads(cipher.decrypt(base64.b64decode(envelope["ciphertext_b64"])))
    plaintext["revisions"][0]["candidate"]["profile_snapshot"]["profile_version"] = "9.9.9"
    encrypted = cipher.encrypt(canonical_json_bytes(plaintext))
    body = {
        **envelope,
        "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"),
        "ciphertext_sha256": sha256_bytes(encrypted),
    }
    body.pop("document_sha256")
    body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        OwnerProfileStore(path, cipher).load()
    assert exc.value.code == "ERR_OWNER_PROFILE_STORE_INTEGRITY"


def test_atomic_failure_wrong_key_plaintext_symlink_and_schema_mirror(tmp_path: Path) -> None:
    path = tmp_path / "owner-profiles.json"
    store = OwnerProfileStore(path, TestCipher())
    saved, candidate, confirmation = append(store)
    before = path.read_bytes()
    proposal, history, selections, binding, _ = sources()

    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("simulated power loss")

    failed_path = tmp_path / "failed-first-write.json"
    with pytest.raises(RuntimeError, match="simulated power loss"):
        OwnerProfileStore(failed_path, TestCipher()).append(
            store_id="owner-profiles.default", owner_scope_sha256=candidate.owner_scope_sha256,
            candidate_id=candidate.candidate_id, proposal=proposal, binding=binding,
            decision_history=history, selections=selections, confirmation=confirmation,
            expected_revision=0, failure_injector=fail,
        )
    assert not failed_path.exists()
    assert path.read_bytes() == before and saved.history.revision == 1
    with pytest.raises(ProductError):
        OwnerProfileStore(path, TestCipher(b"wrong")).load()
    plain = tmp_path / "plain.json"
    plain.write_text(json.dumps(OwnerProfileHistory("owner-profiles.default", candidate.owner_scope_sha256, 0, ()).to_dict()), encoding="utf-8")
    with pytest.raises(ProductError):
        OwnerProfileStore(plain, TestCipher()).load()
    link = tmp_path / "link.json"
    try:
        link.symlink_to(path)
    except OSError:
        pass
    else:
        with pytest.raises(ProductError):
            OwnerProfileStore(link, TestCipher()).load()
    assert (ROOT / "schemas/owner-profile-store.schema.json").read_bytes() == (
        ROOT / "src/ai_video_production/schema_resources/owner-profile-store.schema.json"
    ).read_bytes()
    if os.name != "nt":
        with pytest.raises(ProductError) as exc:
            WindowsDpapiOwnerProfileCipher()
        assert exc.value.code == "ERR_OWNER_PROFILE_ENCRYPTION_UNAVAILABLE"


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI runtime only")
def test_windows_dpapi_real_synthetic_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "owner-profiles-dpapi.json"
    saved, candidate, _ = append(OwnerProfileStore(path))
    assert OwnerProfileStore(path).load().to_dict() == saved.history.to_dict()
    assert candidate.candidate_id.encode() not in path.read_bytes()
