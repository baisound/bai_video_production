from __future__ import annotations
import ast, json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator
from ai_video_production.errors import ProductError
from ai_video_production.knowledge_pack_local_signing_ceremony import LocalSigningCeremonyConfirmation, LocalSigningCeremonyReceipt, confirm_local_signing_ceremony, execute_local_signing_ceremony
from ai_video_production.knowledge_pack_signature_request import KnowledgePackSignatureAlgorithm, compile_knowledge_pack_signature_verification_request
from ai_video_production.knowledge_pack_signature_verification import TrustedSignerPolicy, TrustedSignerPolicyState
from ai_video_production.knowledge_pack_signing import compile_knowledge_pack_signing_candidate
from ai_video_production.owner_signing_key_custody import OwnerSigningKeyCustodyStore, confirm_owner_signing_key_custody
from ai_video_production.serialization import sha256_bytes
from test_task029_knowledge_pack_signing import bundle

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/knowledge-pack-local-signing-ceremony-receipt.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name
SCOPE = "sha256:" + "7" * 64

class SyntheticCipher:
    cipher_suite = "TEST_R9C_CUSTODY_V1"
    def __init__(self) -> None: self.decrypt_count = 0
    def encrypt(self, plaintext: bytes) -> bytes: return b"R9C" + bytes(x ^ 0x5A for x in plaintext)
    def decrypt(self, ciphertext: bytes) -> bytes:
        self.decrypt_count += 1
        if not ciphertext.startswith(b"R9C"): raise ValueError("wrong ciphertext")
        return bytes(x ^ 0x5A for x in ciphertext[3:])

def case(tmp_path: Path, *, revoked: bool = False):
    _, _, _, signing_kwargs = bundle(tmp_path / "bundle")
    candidate = compile_knowledge_pack_signing_candidate(**signing_kwargs)
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = sha256_bytes(public)
    policy = TrustedSignerPolicy("policy.r9c", (key_id,), TrustedSignerPolicyState.REVOKED if revoked else TrustedSignerPolicyState.ACTIVE)
    request_kwargs = {"request_id":"request.r9c", "source_signing_candidate_payload":candidate.to_dict(), "signing_candidate_compile_kwargs":signing_kwargs, "trusted_signer_policy_sha256":policy.to_dict()["trusted_signer_policy_sha256"], "signer_key_id_sha256":key_id, "signature_algorithm":KnowledgePackSignatureAlgorithm.ED25519}
    request = compile_knowledge_pack_signature_verification_request(**request_kwargs)
    cipher = SyntheticCipher(); store = OwnerSigningKeyCustodyStore(tmp_path / "custody.json", cipher)
    custody_confirmation = confirm_owner_signing_key_custody(confirmation_id="custody-confirmation.r9c", custody_id="custody.r9c", owner_scope_sha256=SCOPE, signer_public_key=public, confirmed_at_epoch_ms=100, explicit_human_confirmation=True)
    custody = store.provision(receipt_id="custody-receipt.r9c", custody_id="custody.r9c", owner_scope_sha256=SCOPE, private_key_seed=seed, confirmation=custody_confirmation, custodied_at_epoch_ms=101).receipt
    confirmation = confirm_local_signing_ceremony(confirmation_id="sign-confirmation.r9c", ceremony_id="ceremony.r9c", custody_receipt_payload=custody.to_dict(), signature_request_payload=request.to_dict(), confirmed_at_epoch_ms=200, explicit_human_confirmation=True)
    return store, cipher, custody, request, request_kwargs, policy, confirmation, seed, public

def execute(values, **overrides):
    store, _, custody, request, request_kwargs, policy, confirmation, _, _ = values
    kwargs = {"receipt_id":"ceremony-receipt.r9c", "verification_receipt_id":"verification-receipt.r9c", "custody_store":store, "custody_receipt_payload":custody.to_dict(), "signature_request_payload":request.to_dict(), "signature_request_compile_kwargs":request_kwargs, "trusted_signer_policy_payload":policy.to_dict(), "confirmation":confirmation, "completed_at_epoch_ms":201}
    kwargs.update(overrides); return execute_local_signing_ceremony(**kwargs)

def test_exact_custody_signs_verifies_and_returns_body_free_receipts(tmp_path: Path) -> None:
    values = case(tmp_path); result = execute(values); payload = result.receipt.to_dict()
    assert payload["state"] == "SIGNED_AND_VERIFIED"
    assert payload["detached_signature_sha256"] == result.verification_receipt.detached_signature_sha256
    assert payload["verification_receipt_sha256"] == result.verification_receipt.to_dict()["verification_receipt_sha256"]
    for field in ("persistent_replay_prevention_present", "signature_bytes_included", "public_key_material_included", "private_key_material_included", "private_key_export_authorized", "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized", "automatic_promotion_authorized", "runtime_profile_apply_authorized", "rollback_execution_authorized", "release_authorized", "external_effect_authorized"):
        assert payload[field] is False
    assert LocalSigningCeremonyReceipt.from_dict(payload) == result.receipt
    assert LocalSigningCeremonyConfirmation.from_dict(values[6].to_dict()) == values[6]
    raw = json.dumps(payload).encode(); assert values[7] not in raw and values[8] not in raw

def test_schema_mirror_and_receipt_validate(tmp_path: Path) -> None:
    payload = execute(case(tmp_path)).receipt.to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")); Draft202012Validator.check_schema(schema); Draft202012Validator(schema).validate(payload)

def test_explicit_human_confirmation_is_required(tmp_path: Path) -> None:
    values = case(tmp_path)
    with pytest.raises(ProductError) as error:
        confirm_local_signing_ceremony(confirmation_id="x", ceremony_id="x", custody_receipt_payload=values[2].to_dict(), signature_request_payload=values[3].to_dict(), confirmed_at_epoch_ms=1, explicit_human_confirmation=False)
    assert error.value.code == "ERR_KNOWLEDGE_PACK_LOCAL_SIGNING_CONFIRMATION_REQUIRED"

def test_request_tamper_and_revoked_policy_fail_before_signing(tmp_path: Path) -> None:
    values = case(tmp_path); before = values[1].decrypt_count; tampered = values[3].to_dict(); tampered["pack_version"] = "9.9.9"
    with pytest.raises(ValueError): execute(values, signature_request_payload=tampered)
    assert values[1].decrypt_count == before
    revoked = case(tmp_path / "revoked", revoked=True); before = revoked[1].decrypt_count
    with pytest.raises(ValueError, match="not active"): execute(revoked)
    assert revoked[1].decrypt_count == before

def test_custody_confirmation_and_time_drift_fail_closed(tmp_path: Path) -> None:
    values = case(tmp_path); confirmation = values[6]
    wrong = LocalSigningCeremonyConfirmation(confirmation.confirmation_id, confirmation.ceremony_id, "sha256:" + "0" * 64, confirmation.signature_request_sha256, confirmation.confirmed_at_epoch_ms)
    with pytest.raises(ValueError, match="does not match"): execute(values, confirmation=wrong)
    with pytest.raises(ValueError, match="precedes"): execute(values, completed_at_epoch_ms=199)
    other = case(tmp_path / "other")
    with pytest.raises(ValueError): execute(values, custody_receipt_payload=other[2].to_dict())

def test_receipt_tamper_and_unknown_fields_fail_closed(tmp_path: Path) -> None:
    payload = execute(case(tmp_path)).receipt.to_dict(); payload["state"] = "SIGNED"
    with pytest.raises(ValueError): LocalSigningCeremonyReceipt.from_dict(payload)
    payload = execute(case(tmp_path / "other")).receipt.to_dict(); payload["secret"] = "x"
    with pytest.raises(ValueError): LocalSigningCeremonyReceipt.from_dict(payload)

def test_module_has_no_external_io_export_or_signature_body_return() -> None:
    module = ROOT / "src/ai_video_production/knowledge_pack_local_signing_ceremony.py"; source = module.read_text(encoding="utf-8"); tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports.isdisjoint({"os", "pathlib", "requests", "socket", "sqlite3", "subprocess", "urllib"})
    assert "private_key_seed" not in source and "private_bytes" not in source and "generate(" not in source
    assert "detached_signature_bytes" not in LocalSigningCeremonyReceipt.__dataclass_fields__