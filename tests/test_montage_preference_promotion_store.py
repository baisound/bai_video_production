from __future__ import annotations

import base64
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.montage_preference_projection import (
    PreferenceProjectionCandidateState,
    compile_preference_projection_candidate,
)
from ai_video_production.montage_preference_promotion_store import (
    PreferencePromotionAction,
    PreferencePromotionConfirmation,
    PreferencePromotionHistory,
    PreferencePromotionStore,
    WindowsDpapiPreferencePromotionCipher,
    confirm_preference_promotion,
    confirm_preference_rollback,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_montage_preference_projection import (
    SHA_A,
    compile_ready,
    multi_revision_sources,
    policy,
    sources,
)


ROOT = Path(__file__).resolve().parents[1]
STORE_ID = "montage-preference-promotions.default"


class SyntheticCipher:
    cipher_suite = "TEST_ONLY_XOR_MONTAGE_PREFERENCE_PROMOTION_V1"

    def __init__(self, key: int = 0x5A) -> None:
        self.key = key

    def encrypt(self, plaintext: bytes) -> bytes:
        return b"PPB1" + bytes(value ^ self.key for value in plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        if not ciphertext.startswith(b"PPB1"):
            raise ValueError("wrong test cipher prefix")
        return bytes(value ^ self.key for value in ciphertext[4:])


def _first(path: Path):
    source = sources()
    candidate = compile_ready(source=source)
    confirmation = confirm_preference_promotion(
        confirmation_id="preference-promotion.confirmation.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_100_000,
        human_confirmed=True,
    )
    store = PreferencePromotionStore(path, SyntheticCipher())
    result = store.promote(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        candidate=candidate,
        sources=source,
        policy=policy(),
        confirmation=confirmation,
        expected_revision=0,
    )
    return store, result, candidate, confirmation


def _second(store: PreferencePromotionStore, history: PreferencePromotionHistory):
    source = multi_revision_sources()
    candidate = compile_preference_projection_candidate(
        source,
        policy(),
        expected_owner_scope_sha256=SHA_A,
        expected_registry_revision=2,
        requested_scope_mode="OWNER_GLOBAL",
        previous_active_promotion_revision=history.revision,
        previous_active_promotion_sha256=history.current_revision_sha256,
        next_profile_version=history.revision + 1,
    )
    assert candidate.state is PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW
    confirmation = confirm_preference_promotion(
        confirmation_id="preference-promotion.confirmation.002",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_100_001,
        human_confirmed=True,
    )
    return store.promote(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        candidate=candidate,
        sources=source,
        policy=policy(),
        confirmation=confirmation,
        expected_revision=history.revision,
    )


def _concurrent_worker(path: str, queue) -> None:
    try:
        source = sources()
        candidate = compile_ready(source=source)
        confirmation = confirm_preference_promotion(
            confirmation_id="preference-promotion.concurrent.001",
            candidate=candidate,
            confirmed_at_epoch_ms=1_800_000_100_100,
            human_confirmed=True,
        )
        result = PreferencePromotionStore(Path(path), SyntheticCipher()).promote(
            store_id=STORE_ID,
            owner_scope_sha256=SHA_A,
            candidate=candidate,
            sources=source,
            policy=policy(),
            confirmation=confirmation,
            expected_revision=0,
        )
        queue.put(("ok", result.history.revision, result.duplicate_noop))
    except Exception as exc:  # pragma: no cover - child failure is asserted by parent
        queue.put(("error", type(exc).__name__, str(exc)))


def test_explicit_confirmation_encrypted_round_trip_schema_and_no_effect(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    store, saved, candidate, confirmation = _first(path)
    raw = path.read_bytes()
    assert candidate.to_dict()["candidate_sha256"].encode() not in raw
    assert candidate.to_dict()["proposed_envelope"]["profile_id"].encode() not in raw
    assert confirmation.confirmation_id.encode() not in raw
    assert SHA_A.encode() not in raw
    loaded = store.load()
    assert loaded.to_dict() == saved.history.to_dict()
    assert loaded.active_envelope == candidate.to_dict()["proposed_envelope"]
    assert loaded.revisions[0].action is PreferencePromotionAction.PROMOTE
    for field in (
        "automatic_promotion_authorized", "automatic_rollback_authorized",
        "timeline_mutation_authorized", "resolve_write_authorized",
        "external_effect_authorized",
    ):
        assert loaded.to_dict()[field] is False
    validate_instance(
        "montage-preference-projection-promotion.schema.json",
        json.loads(raw),
    )


def test_confirmation_is_separate_ready_only_and_exact() -> None:
    candidate = compile_ready()
    with pytest.raises(ValueError, match="explicit Human"):
        confirm_preference_promotion(
            confirmation_id="preference-promotion.denied",
            candidate=candidate,
            confirmed_at_epoch_ms=1_800_000_100_000,
            human_confirmed=False,
        )
    blocked = compile_ready(expected_registry_revision=2)
    with pytest.raises(ValueError, match="READY_FOR_HUMAN_REVIEW"):
        confirm_preference_promotion(
            confirmation_id="preference-promotion.blocked",
            candidate=blocked,
            confirmed_at_epoch_ms=1_800_000_100_000,
            human_confirmed=True,
        )


def test_duplicate_noop_collision_and_stale_cas(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    store, first, candidate, confirmation = _first(path)
    before = path.read_bytes()
    duplicate = store.promote(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        candidate=candidate,
        sources=sources(),
        policy=policy(),
        confirmation=confirmation,
        expected_revision=0,
    )
    assert duplicate.duplicate_noop is True
    assert duplicate.write is None
    assert path.read_bytes() == before

    different = PreferencePromotionConfirmation(
        confirmation.confirmation_id,
        confirmation.action,
        confirmation.owner_scope_sha256,
        confirmation.candidate_sha256,
        confirmation.expected_revision,
        confirmation.expected_previous_revision_sha256,
        confirmation.active_payload_sha256,
        None,
        None,
        confirmation.confirmed_at_epoch_ms + 1,
    )
    with pytest.raises(ProductError) as collision:
        store.promote(
            store_id=STORE_ID,
            owner_scope_sha256=SHA_A,
            candidate=candidate,
            sources=sources(),
            policy=policy(),
            confirmation=different,
            expected_revision=1,
        )
    assert collision.value.code == "ERR_MONTAGE_PREFERENCE_PROMOTION_COLLISION"

    next_source = multi_revision_sources()
    stale_candidate = compile_preference_projection_candidate(
        next_source,
        policy(),
        expected_owner_scope_sha256=SHA_A,
        expected_registry_revision=2,
        requested_scope_mode="OWNER_GLOBAL",
        previous_active_promotion_revision=1,
        previous_active_promotion_sha256=first.history.current_revision_sha256,
        next_profile_version=2,
    )
    stale_confirmation = confirm_preference_promotion(
        confirmation_id="preference-promotion.stale.002",
        candidate=stale_candidate,
        confirmed_at_epoch_ms=1_800_000_100_002,
        human_confirmed=True,
    )
    with pytest.raises(ProductError) as conflict:
        store.promote(
            store_id=STORE_ID,
            owner_scope_sha256=SHA_A,
            candidate=stale_candidate,
            sources=next_source,
            policy=policy(),
            confirmation=stale_confirmation,
            expected_revision=0,
        )
    assert conflict.value.code == "ERR_MONTAGE_PREFERENCE_PROMOTION_CONFLICT"


def test_source_policy_and_confirmation_drift_fail_before_write(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    source = sources()
    candidate = compile_ready(source=source)
    confirmation = confirm_preference_promotion(
        confirmation_id="preference-promotion.confirmation.drift",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_100_000,
        human_confirmed=True,
    )
    with pytest.raises(ValueError, match="exact source snapshots"):
        PreferencePromotionStore(path, SyntheticCipher()).promote(
            store_id=STORE_ID,
            owner_scope_sha256=SHA_A,
            candidate=candidate,
            sources=source,
            policy=policy(ceiling=1000),
            confirmation=confirmation,
            expected_revision=0,
        )
    assert not path.exists()


def test_rollback_appends_higher_revision_and_preserves_target_payload(tmp_path: Path) -> None:
    store, first, _, _ = _first(tmp_path / "preference-promotions.json")
    second = _second(store, first.history)
    confirmation = confirm_preference_rollback(
        confirmation_id="preference-promotion.rollback.003",
        history=second.history,
        target_revision=1,
        confirmed_at_epoch_ms=1_800_000_100_003,
        human_confirmed=True,
    )
    rolled_back = store.rollback(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        confirmation=confirmation,
        expected_revision=2,
    )
    assert rolled_back.history.revision == 3
    revision = rolled_back.history.revisions[-1]
    assert revision.action is PreferencePromotionAction.ROLLBACK
    assert revision.rollback_target_revision == 1
    assert revision.active_envelope == first.history.revisions[0].active_envelope
    assert (
        revision.to_dict()["active_payload_sha256"]
        == first.history.revisions[0].to_dict()["active_payload_sha256"]
    )
    assert rolled_back.history.revisions[1].to_dict() == second.history.revisions[1].to_dict()


@pytest.mark.parametrize("stage", ("before_replace", "after_replace", "before_durable_readback"))
def test_crash_recovery_is_no_clobber_or_exact_duplicate_noop(tmp_path: Path, stage: str) -> None:
    path = tmp_path / f"failure-{stage}.json"
    source = sources()
    candidate = compile_ready(source=source)
    confirmation = confirm_preference_promotion(
        confirmation_id=f"preference-promotion.failure.{stage}",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_100_000,
        human_confirmed=True,
    )
    store = PreferencePromotionStore(path, SyntheticCipher())

    def fail(current_stage: str, _path: Path) -> None:
        if current_stage == stage:
            raise RuntimeError(f"simulated crash {stage}")

    with pytest.raises(RuntimeError, match="simulated crash"):
        store.promote(
            store_id=STORE_ID,
            owner_scope_sha256=SHA_A,
            candidate=candidate,
            sources=source,
            policy=policy(),
            confirmation=confirmation,
            expected_revision=0,
            failure_injector=fail,
        )
    if stage == "before_replace":
        assert not path.exists()
    else:
        assert store.load().revision == 1
    recovered = store.promote(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        candidate=candidate,
        sources=source,
        policy=policy(),
        confirmation=confirmation,
        expected_revision=0,
    )
    assert recovered.history.revision == 1
    assert recovered.duplicate_noop is (stage != "before_replace")


def test_inner_outer_tamper_wrong_cipher_plaintext_and_schema_mirror(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    store, _, _, _ = _first(path)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    plaintext = json.loads(SyntheticCipher().decrypt(base64.b64decode(envelope["ciphertext_b64"])))
    plaintext["revisions"][0]["active_envelope"]["payload"]["preferences"][0]["target"] = "TAMPERED"
    encrypted = SyntheticCipher().encrypt(canonical_json_bytes(plaintext))
    tampered = {
        **envelope,
        "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"),
        "ciphertext_sha256": sha256_bytes(encrypted),
    }
    tampered.pop("document_sha256")
    tampered["document_sha256"] = sha256_bytes(canonical_json_bytes(tampered))
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ProductError) as integrity:
        store.load()
    assert integrity.value.code == "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_INTEGRITY"
    with pytest.raises(ProductError):
        PreferencePromotionStore(path, SyntheticCipher(0x31)).load()
    assert ROOT.joinpath("schemas/montage-preference-projection-promotion.schema.json").read_bytes() == ROOT.joinpath(
        "src/ai_video_production/schema_resources/montage-preference-projection-promotion.schema.json"
    ).read_bytes()


def test_rehashed_noncanonical_preference_is_still_rejected(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    _first(path)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    plaintext = json.loads(SyntheticCipher().decrypt(base64.b64decode(envelope["ciphertext_b64"])))
    revision = plaintext["revisions"][0]
    candidate = revision["candidate"]
    candidate["proposed_envelope"]["payload"]["preferences"][0]["ranking_bias"] *= -1
    candidate["proposed_envelope"]["profile_sha256"] = sha256_bytes(
        canonical_json_bytes(candidate["proposed_envelope"]["payload"])
    )
    candidate_body = dict(candidate)
    candidate_body.pop("candidate_sha256")
    candidate["candidate_sha256"] = sha256_bytes(canonical_json_bytes(candidate_body))
    encrypted = SyntheticCipher().encrypt(canonical_json_bytes(plaintext))
    outer = {
        **envelope,
        "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"),
        "ciphertext_sha256": sha256_bytes(encrypted),
    }
    outer.pop("document_sha256")
    outer["document_sha256"] = sha256_bytes(canonical_json_bytes(outer))
    path.write_text(json.dumps(outer), encoding="utf-8")
    with pytest.raises(ProductError) as integrity:
        PreferencePromotionStore(path, SyntheticCipher()).load()
    assert integrity.value.code == "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_INTEGRITY"


def test_cross_process_exact_duplicate_serializes_to_one_revision(tmp_path: Path) -> None:
    path = tmp_path / "concurrent-promotions.json"
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(target=_concurrent_worker, args=(str(path), queue)) for _ in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0
    results = [queue.get(timeout=5) for _ in processes]
    assert all(result[0] == "ok" for result in results), results
    assert sorted(result[2] for result in results) == [False, True]
    assert PreferencePromotionStore(path, SyntheticCipher()).load().revision == 1


def test_symlink_scope_and_rollback_confirmation_negatives(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    store, first, _, _ = _first(path)
    with pytest.raises(ValueError, match="explicit Human"):
        confirm_preference_rollback(
            confirmation_id="preference-promotion.rollback.denied",
            history=first.history,
            target_revision=1,
            confirmed_at_epoch_ms=1_800_000_100_003,
            human_confirmed=False,
        )
    with pytest.raises(ProductError) as scope:
        PreferencePromotionStore(path, SyntheticCipher()).rollback(
            store_id="montage-preference-promotions.other",
            owner_scope_sha256=SHA_A,
            confirmation=confirm_preference_rollback(
                confirmation_id="preference-promotion.rollback.scope",
                history=first.history,
                target_revision=1,
                confirmed_at_epoch_ms=1_800_000_100_004,
                human_confirmed=True,
            ),
            expected_revision=1,
        )
    assert scope.value.code == "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_SCOPE"
    link = tmp_path / "link.json"
    try:
        link.symlink_to(path)
    except OSError:
        pass
    else:
        with pytest.raises(ProductError):
            PreferencePromotionStore(link, SyntheticCipher()).load()


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI runtime only")
def test_windows_dpapi_real_synthetic_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions-dpapi.json"
    source = sources()
    candidate = compile_ready(source=source)
    confirmation = confirm_preference_promotion(
        confirmation_id="preference-promotion.dpapi.001",
        candidate=candidate,
        confirmed_at_epoch_ms=1_800_000_100_000,
        human_confirmed=True,
    )
    store = PreferencePromotionStore(path, WindowsDpapiPreferencePromotionCipher())
    saved = store.promote(
        store_id=STORE_ID,
        owner_scope_sha256=SHA_A,
        candidate=candidate,
        sources=source,
        policy=policy(),
        confirmation=confirmation,
        expected_revision=0,
    )
    assert PreferencePromotionStore(path).load().to_dict() == saved.history.to_dict()
    assert candidate.to_dict()["candidate_sha256"].encode() not in path.read_bytes()
