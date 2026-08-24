from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.human_edit_learning import (
    HardGateState, HumanActionEvidence, HumanDisposition, MetricEvaluation,
    OwnerLearningPolicy, compile_owner_decision_candidate,
)
from ai_video_production.multimodal_scoring import EvidenceValidity
from ai_video_production.owner_decision_store import (
    HumanDecision, OwnerDecisionHistory, OwnerDecisionStore,
    WindowsDpapiOwnerDecisionCipher,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
METRIC_IDS = ("human_acceptance", "qa_compliance", "quality_improvement", "rework_reduction", "sample_confidence", "time_reduction")


class TestCipher:
    __test__ = False
    cipher_suite = "TEST_AEAD_V1"
    def __init__(self, key: bytes = b"task029-test-key") -> None: self.key = key
    def encrypt(self, plaintext: bytes) -> bytes:
        stream = hashlib.shake_256(self.key + b"stream").digest(len(plaintext))
        body = bytes(a ^ b for a, b in zip(plaintext, stream, strict=True))
        return hmac.digest(self.key, body, "sha256") + body
    def decrypt(self, ciphertext: bytes) -> bytes:
        tag, body = ciphertext[:32], ciphertext[32:]
        if len(tag) != 32 or not hmac.compare_digest(tag, hmac.digest(self.key, body, "sha256")):
            raise ValueError("authentication failed")
        stream = hashlib.shake_256(self.key + b"stream").digest(len(body))
        return bytes(a ^ b for a, b in zip(body, stream, strict=True))


def evidence(number: int) -> HumanActionEvidence:
    return HumanActionEvidence(
        f"human-action.{number:03d}", SHA_A, SHA_B, "TASK-055",
        "sha256:" + f"{number:064x}", "montage.timing",
        ("event:PALLET_DROP", "style:dbd-aggressive"), SHA_B, SHA_C, SHA_A,
        HumanDisposition.MODIFIED, EvidenceValidity.CURRENT_VALID, False, False, False,
        HardGateState.PASS, HardGateState.PASS, 1_700_000_000_000 + number, 10_000,
    )


def candidate(candidate_id: str = "owner-decision.001", observed: int = 520) -> dict:
    metrics = tuple(MetricEvaluation(name, 500, observed, 10, EvidenceValidity.CURRENT_VALID) for name in METRIC_IDS)
    policy = OwnerLearningPolicy("owner-learning.conservative", "1.0.0", 2, 10, 10, 0)
    return compile_owner_decision_candidate(candidate_id, SHA_A, "hypothesis.montage-quality", (evidence(1), evidence(2)), metrics, policy).to_dict()


def append(store: OwnerDecisionStore, *, revision: int = 0, decision_id: str = "decision.001", value: dict | None = None, decision: HumanDecision = HumanDecision.ADOPTED):
    return store.append(
        store_id="owner-decisions.default", owner_scope_sha256=SHA_A,
        decision_id=decision_id, candidate=value or candidate(), decision=decision,
        reason_codes=("human.explicit-review",), decided_at_epoch_ms=1_700_000_100_000 + revision,
        expected_revision=revision,
    )


def test_encrypted_round_trip_contains_no_plaintext(tmp_path: Path) -> None:
    path = tmp_path / "owner-decisions.json"
    first = append(OwnerDecisionStore(path, TestCipher()))
    raw = path.read_bytes()
    assert b"owner-decision.001" not in raw and SHA_A.encode() not in raw and b"human.explicit-review" not in raw
    assert OwnerDecisionStore(path, TestCipher()).load().to_dict() == first.history.to_dict()
    validate_instance("owner-decision-store.schema.json", json.loads(raw))


def test_append_chain_and_no_profile_authority(tmp_path: Path) -> None:
    store = OwnerDecisionStore(tmp_path / "store.json", TestCipher())
    first = append(store)
    second = append(store, revision=1, decision_id="decision.002", value=candidate("owner-decision.002"), decision=HumanDecision.REJECTED)
    assert second.history.entries[1].previous_entry_sha256 == first.history.entries[0].to_dict()["entry_sha256"]
    document = second.history.to_dict()
    for name in ("owner_profile_write_authorized", "knowledge_pack_promotion_authorized", "plaintext_export_authorized", "physical_delete_authorized"):
        assert document[name] is False


def test_stale_revision_scope_replay_and_nonready_fail_closed(tmp_path: Path) -> None:
    store = OwnerDecisionStore(tmp_path / "store.json", TestCipher())
    original = candidate()
    append(store, value=original)
    with pytest.raises(ProductError) as stale: append(store, revision=0, decision_id="decision.002", value=candidate("owner-decision.002"))
    assert stale.value.code == "ERR_OWNER_DECISION_STORE_CONFLICT"
    with pytest.raises(ProductError) as scope:
        store.append(store_id="owner-decisions.other", owner_scope_sha256=SHA_A, decision_id="decision.002", candidate=candidate("owner-decision.002"), decision=HumanDecision.ADOPTED, reason_codes=("human.explicit-review",), decided_at_epoch_ms=1_700_000_200_000, expected_revision=1)
    assert scope.value.code == "ERR_OWNER_DECISION_STORE_SCOPE"
    with pytest.raises(ValueError, match="replay"): append(store, revision=1, decision_id="decision.003", value=original)
    blocked = candidate("owner-decision.blocked", observed=500)
    with pytest.raises(ValueError, match="READY_FOR_HUMAN_REVIEW"): append(store, revision=1, decision_id="decision.004", value=blocked)


@pytest.mark.parametrize("field", ["ciphertext_b64", "ciphertext_sha256", "document_sha256", "plaintext_fields_present"])
def test_envelope_tamper_fails_closed(tmp_path: Path, field: str) -> None:
    path = tmp_path / "store.json"; append(OwnerDecisionStore(path, TestCipher()))
    document = json.loads(path.read_text(encoding="utf-8")); document[field] = "tampered" if field != "plaintext_fields_present" else True
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc: OwnerDecisionStore(path, TestCipher()).load()
    assert exc.value.code == "ERR_OWNER_DECISION_STORE_INTEGRITY"


def test_authenticated_inner_tamper_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "store.json"; cipher = TestCipher(); append(OwnerDecisionStore(path, cipher))
    envelope = json.loads(path.read_text(encoding="utf-8"))
    plaintext = json.loads(cipher.decrypt(base64.b64decode(envelope["ciphertext_b64"])))
    plaintext["entries"][0]["reason_codes"] = ["attacker.rehashed"]
    encrypted = cipher.encrypt(canonical_json_bytes(plaintext))
    body = {**envelope, "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"), "ciphertext_sha256": sha256_bytes(encrypted)}
    body.pop("document_sha256"); body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ProductError): OwnerDecisionStore(path, cipher).load()


def test_atomic_failure_preserves_previous_store(tmp_path: Path) -> None:
    path = tmp_path / "store.json"; store = OwnerDecisionStore(path, TestCipher()); append(store); before = path.read_bytes()
    def fail(stage: str, _path: Path) -> None:
        if stage == "before_replace": raise RuntimeError("simulated power loss")
    with pytest.raises(RuntimeError):
        store.append(store_id="owner-decisions.default", owner_scope_sha256=SHA_A, decision_id="decision.002", candidate=candidate("owner-decision.002"), decision=HumanDecision.REJECTED, reason_codes=("human.explicit-review",), decided_at_epoch_ms=1_700_000_200_000, expected_revision=1, failure_injector=fail)
    assert path.read_bytes() == before and store.load().revision == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI runtime only")
def test_windows_dpapi_real_synthetic_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "owner-decisions-dpapi.json"
    saved = append(OwnerDecisionStore(path))
    loaded = OwnerDecisionStore(path).load()
    assert loaded.to_dict() == saved.history.to_dict()
    assert b"owner-decision.001" not in path.read_bytes()

def test_wrong_key_symlink_plaintext_and_schema_mirror(tmp_path: Path) -> None:
    path = tmp_path / "store.json"; append(OwnerDecisionStore(path, TestCipher()))
    with pytest.raises(ProductError): OwnerDecisionStore(path, TestCipher(b"wrong")).load()
    plain = tmp_path / "plain.json"; plain.write_text(json.dumps(OwnerDecisionHistory("owner-decisions.default", SHA_A, 0, ()).to_dict()), encoding="utf-8")
    with pytest.raises(ProductError): OwnerDecisionStore(plain, TestCipher()).load()
    link = tmp_path / "link.json"
    try: link.symlink_to(path)
    except OSError: pass
    else:
        with pytest.raises(ProductError): OwnerDecisionStore(link, TestCipher()).load()
    root = Path(__file__).resolve().parents[1]
    assert (root / "schemas/owner-decision-store.schema.json").read_bytes() == (root / "src/ai_video_production/schema_resources/owner-decision-store.schema.json").read_bytes()
    if os.name != "nt":
        with pytest.raises(ProductError) as exc: WindowsDpapiOwnerDecisionCipher()
        assert exc.value.code == "ERR_OWNER_DECISION_ENCRYPTION_UNAVAILABLE"
