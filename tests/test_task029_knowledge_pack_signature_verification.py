from __future__ import annotations

from dataclasses import FrozenInstanceError
import ast
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ai_video_production.knowledge_pack_signature_request import (
    KnowledgePackSignatureAlgorithm,
    compile_knowledge_pack_signature_verification_request,
)
from ai_video_production.knowledge_pack_signature_verification import (
    KnowledgePackSignatureVerificationReceipt,
    TrustedSignerPolicy,
    TrustedSignerPolicyState,
    verify_detached_knowledge_pack_signature,
)
from ai_video_production.knowledge_pack_signing import (
    compile_knowledge_pack_signing_candidate,
)
from ai_video_production.serialization import sha256_bytes
from test_task029_knowledge_pack_signing import bundle

ROOT = Path(__file__).resolve().parents[1]
POLICY_SCHEMA = ROOT / "schemas" / "trusted-knowledge-pack-signer-policy.schema.json"
POLICY_MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / POLICY_SCHEMA.name
RECEIPT_SCHEMA = ROOT / "schemas" / "knowledge-pack-signature-verification-receipt.schema.json"
RECEIPT_MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / RECEIPT_SCHEMA.name
MODULE = ROOT / "src" / "ai_video_production" / "knowledge_pack_signature_verification.py"


def _case(tmp_path: Path, *, revoked: bool = False):
    _, _, _, signing_kwargs = bundle(tmp_path)
    candidate = compile_knowledge_pack_signing_candidate(**signing_kwargs)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_id = sha256_bytes(public_key)
    policy = TrustedSignerPolicy(
        "knowledge-pack.owner-signers.v1",
        (key_id,),
        TrustedSignerPolicyState.REVOKED if revoked else TrustedSignerPolicyState.ACTIVE,
    )
    request_kwargs = {
        "request_id": "knowledge-pack.signature-request.001",
        "source_signing_candidate_payload": candidate.to_dict(),
        "signing_candidate_compile_kwargs": signing_kwargs,
        "trusted_signer_policy_sha256": policy.to_dict()["trusted_signer_policy_sha256"],
        "signer_key_id_sha256": key_id,
        "signature_algorithm": KnowledgePackSignatureAlgorithm.ED25519,
    }
    request = compile_knowledge_pack_signature_verification_request(**request_kwargs)
    signature = private_key.sign(
        request.to_dict()["signature_message_sha256"].encode("ascii")
    )
    return request, request_kwargs, policy, public_key, signature


def test_valid_signature_returns_body_free_no_effect_receipt(tmp_path: Path) -> None:
    request, request_kwargs, policy, public_key, signature = _case(tmp_path)
    receipt = verify_detached_knowledge_pack_signature(
        receipt_id="knowledge-pack.signature-receipt.001",
        signature_request_payload=request.to_dict(),
        signature_request_compile_kwargs=request_kwargs,
        trusted_signer_policy_payload=policy.to_dict(),
        public_key_bytes=public_key,
        detached_signature_bytes=signature,
    )
    payload = receipt.to_dict()
    policy_payload = policy.to_dict()
    Draft202012Validator(json.loads(POLICY_SCHEMA.read_text(encoding="utf-8"))).validate(policy_payload)
    Draft202012Validator(json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))).validate(payload)
    assert TrustedSignerPolicy.from_dict(policy_payload) == policy
    assert POLICY_SCHEMA.read_bytes() == POLICY_MIRROR.read_bytes()
    assert RECEIPT_SCHEMA.read_bytes() == RECEIPT_MIRROR.read_bytes()
    assert payload["state"] == "VERIFIED"
    assert payload["signature_present"] is True
    assert payload["signature_verified"] is True
    assert payload["latest_source_revalidated"] is True
    assert payload["external_effect_authorized"] is False
    assert payload["detached_signature_sha256"] == sha256_bytes(signature)
    assert payload["signer_key_id_sha256"] == sha256_bytes(public_key)
    for field in (
        "signature_bytes_included", "public_key_material_included",
        "private_key_material_included", "knowledge_pack_write_authorized",
        "knowledge_pack_promotion_authorized", "automatic_promotion_authorized",
        "runtime_profile_apply_authorized", "rollback_execution_authorized",
        "release_authorized",
    ):
        assert payload[field] is False
    assert KnowledgePackSignatureVerificationReceipt.from_dict(payload) == receipt
    with pytest.raises(FrozenInstanceError):
        receipt.pack_version = "9.9.9"  # type: ignore[misc]


@pytest.mark.parametrize("target", ["signature", "public_key", "policy", "request"])
def test_tamper_fails_closed(tmp_path: Path, target: str) -> None:
    request, request_kwargs, policy, public_key, signature = _case(tmp_path)
    request_payload = request.to_dict()
    policy_payload = policy.to_dict()
    if target == "signature":
        signature = bytes([signature[0] ^ 1]) + signature[1:]
    elif target == "public_key":
        public_key = bytes([public_key[0] ^ 1]) + public_key[1:]
    elif target == "policy":
        policy_payload["policy_id"] = "knowledge-pack.other-policy"
    else:
        request_payload["pack_version"] = "9.9.9"
    with pytest.raises(ValueError):
        verify_detached_knowledge_pack_signature(
            receipt_id="knowledge-pack.signature-receipt.001",
            signature_request_payload=request_payload,
            signature_request_compile_kwargs=request_kwargs,
            trusted_signer_policy_payload=policy_payload,
            public_key_bytes=public_key,
            detached_signature_bytes=signature,
        )


def test_revoked_policy_and_wrong_lengths_fail_closed(tmp_path: Path) -> None:
    request, request_kwargs, policy, public_key, signature = _case(tmp_path, revoked=True)
    common = {
        "receipt_id": "knowledge-pack.signature-receipt.001",
        "signature_request_payload": request.to_dict(),
        "signature_request_compile_kwargs": request_kwargs,
        "trusted_signer_policy_payload": policy.to_dict(),
    }
    with pytest.raises(ValueError, match="not active"):
        verify_detached_knowledge_pack_signature(
            **common, public_key_bytes=public_key, detached_signature_bytes=signature
        )
    active_request, active_kwargs, active_policy, _, active_signature = _case(tmp_path / "active")
    with pytest.raises(ValueError, match="32 bytes"):
        verify_detached_knowledge_pack_signature(
            receipt_id="knowledge-pack.signature-receipt.002",
            signature_request_payload=active_request.to_dict(),
            signature_request_compile_kwargs=active_kwargs,
            trusted_signer_policy_payload=active_policy.to_dict(),
            public_key_bytes=b"x",
            detached_signature_bytes=active_signature,
        )


def test_policy_order_receipt_tamper_and_signature_length_fail_closed(tmp_path: Path) -> None:
    request, request_kwargs, policy, public_key, signature = _case(tmp_path)
    key_id = sha256_bytes(public_key)
    with pytest.raises(ValueError, match="unique and sorted"):
        TrustedSignerPolicy("policy.invalid", (key_id, key_id))
    receipt = verify_detached_knowledge_pack_signature(
        receipt_id="knowledge-pack.signature-receipt.001",
        signature_request_payload=request.to_dict(),
        signature_request_compile_kwargs=request_kwargs,
        trusted_signer_policy_payload=policy.to_dict(),
        public_key_bytes=public_key,
        detached_signature_bytes=signature,
    )
    tampered = receipt.to_dict()
    tampered["pack_version"] = "9.9.9"
    with pytest.raises(ValueError):
        KnowledgePackSignatureVerificationReceipt.from_dict(tampered)
    with pytest.raises(ValueError, match="64 bytes"):
        verify_detached_knowledge_pack_signature(
            receipt_id="knowledge-pack.signature-receipt.002",
            signature_request_payload=request.to_dict(),
            signature_request_compile_kwargs=request_kwargs,
            trusted_signer_policy_payload=policy.to_dict(),
            public_key_bytes=public_key,
            detached_signature_bytes=b"x",
        )


def test_production_module_has_no_private_key_generation_or_io_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint({"os", "pathlib", "requests", "socket", "sqlite3", "subprocess", "urllib"})
    assert "Ed25519PrivateKey" not in source
    assert "private_bytes" not in source
    assert "generate(" not in source
