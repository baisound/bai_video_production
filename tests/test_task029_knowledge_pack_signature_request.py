from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.knowledge_pack_signature_request import (
    KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT,
    KnowledgePackSignatureAlgorithm,
    KnowledgePackSignatureRequestState,
    KnowledgePackSignatureVerificationRequest,
    compile_knowledge_pack_signature_verification_request,
    verify_knowledge_pack_signature_verification_request,
)
from ai_video_production.knowledge_pack_signing import (
    compile_knowledge_pack_signing_candidate,
)
from test_task029_knowledge_pack_candidate import digest
from test_task029_knowledge_pack_signing import bundle


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack-signature-verification-request.schema.json"
MIRROR = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "knowledge-pack-signature-verification-request.schema.json"
)
MODULE = (
    ROOT
    / "src"
    / "ai_video_production"
    / "knowledge_pack_signature_request.py"
)


def _compile(tmp_path: Path, **overrides: object):
    _, _, _, signing_kwargs = bundle(tmp_path)
    source = compile_knowledge_pack_signing_candidate(**signing_kwargs)
    kwargs = {
        "request_id": "knowledge-pack.signature-request.001",
        "source_signing_candidate_payload": source.to_dict(),
        "signing_candidate_compile_kwargs": signing_kwargs,
        "trusted_signer_policy_sha256": digest("trusted-signer-policy-v1"),
        "signer_key_id_sha256": digest("offline-ed25519-key-id"),
        "signature_algorithm": KnowledgePackSignatureAlgorithm.ED25519,
    }
    kwargs.update(overrides)
    return source, signing_kwargs, compile_knowledge_pack_signature_verification_request(**kwargs)


def test_ready_request_is_deterministic_schema_valid_and_body_free(tmp_path: Path) -> None:
    source, signing_kwargs, request = _compile(tmp_path / "first")
    again = _compile(tmp_path / "again")[2]
    payload = request.to_dict()

    assert request == again
    assert request.state is KnowledgePackSignatureRequestState.READY_FOR_EXTERNAL_CRYPTOGRAPHIC_VERIFICATION
    assert payload["signing_candidate_sha256"] == source.to_dict()["signing_candidate_sha256"]
    assert payload["signature_algorithm"] == "ED25519"
    assert payload["signature_input_contract"] == KNOWLEDGE_PACK_SIGNATURE_INPUT_CONTRACT
    assert payload["latest_source_revalidation_required"] is True
    assert payload["external_cryptographic_verification_required"] is True
    assert payload["in_memory_request_only"] is True
    for key, value in payload.items():
        if key.endswith("_present") or key.endswith("_verified") or key.endswith("_performed"):
            assert value is False, key
    assert "signature" not in payload
    assert "public_key" not in payload
    assert "private_key" not in payload

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    assert KnowledgePackSignatureVerificationRequest.from_dict(payload) == request
    assert verify_knowledge_pack_signature_verification_request(
        payload,
        request_id="knowledge-pack.signature-request.001",
        source_signing_candidate_payload=source.to_dict(),
        signing_candidate_compile_kwargs=signing_kwargs,
        trusted_signer_policy_sha256=digest("trusted-signer-policy-v1"),
        signer_key_id_sha256=digest("offline-ed25519-key-id"),
        signature_algorithm=KnowledgePackSignatureAlgorithm.ED25519,
    ) is None


def test_tamper_and_source_drift_fail_closed(tmp_path: Path) -> None:
    source, signing_kwargs, request = _compile(tmp_path)
    tampered = request.to_dict()
    tampered["pack_version"] = "9.9.9"
    with pytest.raises(ValueError):
        KnowledgePackSignatureVerificationRequest.from_dict(tampered)

    drifted = source.to_dict()
    drifted["pack_version"] = "9.9.9"
    with pytest.raises(ValueError):
        compile_knowledge_pack_signature_verification_request(
            request_id="knowledge-pack.signature-request.001",
            source_signing_candidate_payload=drifted,
            signing_candidate_compile_kwargs=signing_kwargs,
            trusted_signer_policy_sha256=digest("trusted-signer-policy-v1"),
            signer_key_id_sha256=digest("offline-ed25519-key-id"),
            signature_algorithm=KnowledgePackSignatureAlgorithm.ED25519,
        )


def test_invalid_algorithm_and_non_ready_source_are_rejected(tmp_path: Path) -> None:
    source, signing_kwargs, _ = _compile(tmp_path)
    with pytest.raises((TypeError, ValueError)):
        compile_knowledge_pack_signature_verification_request(
            request_id="knowledge-pack.signature-request.001",
            source_signing_candidate_payload=source.to_dict(),
            signing_candidate_compile_kwargs=signing_kwargs,
            trusted_signer_policy_sha256=digest("trusted-signer-policy-v1"),
            signer_key_id_sha256=digest("offline-ed25519-key-id"),
            signature_algorithm="RSA",  # type: ignore[arg-type]
        )

    _, _, _, rejected_kwargs = bundle(tmp_path / "rejected", human_reject=True)
    rejected = compile_knowledge_pack_signing_candidate(**rejected_kwargs)
    with pytest.raises(ValueError, match="ready"):
        compile_knowledge_pack_signature_verification_request(
            request_id="knowledge-pack.signature-request.001",
            source_signing_candidate_payload=rejected.to_dict(),
            signing_candidate_compile_kwargs=rejected_kwargs,
            trusted_signer_policy_sha256=digest("trusted-signer-policy-v1"),
            signer_key_id_sha256=digest("offline-ed25519-key-id"),
            signature_algorithm=KnowledgePackSignatureAlgorithm.ED25519,
        )


def test_record_is_immutable_and_schema_mirror_is_exact(tmp_path: Path) -> None:
    request = _compile(tmp_path)[2]
    with pytest.raises(FrozenInstanceError):
        request.pack_version = "9.9.9"  # type: ignore[misc]
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_module_has_no_io_crypto_or_network_imports() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    prohibited = {
        "cryptography",
        "nacl",
        "os",
        "pathlib",
        "requests",
        "socket",
        "sqlite3",
        "subprocess",
        "urllib",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(prohibited)
