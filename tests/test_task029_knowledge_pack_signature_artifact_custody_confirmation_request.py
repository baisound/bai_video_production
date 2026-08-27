from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.knowledge_pack_signature_artifact_custody_confirmation_request import (
    MAX_CONFIRMATION_REQUEST_TTL_MS,
    SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_STATE,
    compile_signature_artifact_custody_confirmation_request,
    verify_signature_artifact_custody_confirmation_request,
)
from ai_video_production.knowledge_pack_signature_artifact_custody_store import (
    SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE,
    SignatureArtifactCustodyReceipt,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack-signature-artifact-custody-confirmation-request.schema.json"
MIRROR = (
    ROOT
    / "src"
    / "ai_video_production"
    / "schema_resources"
    / "knowledge-pack-signature-artifact-custody-confirmation-request.schema.json"
)


def _hash(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def _receipt(
    *, production: bool = True, pack_id: str = "knowledge-pack:owner-editing"
) -> SignatureArtifactCustodyReceipt:
    return SignatureArtifactCustodyReceipt(
        receipt_id="receipt-r10d-001",
        candidate_sha256=_hash("candidate"),
        artifact_store_id="owner-signature-artifacts",
        owner_scope_sha256=_hash("owner-scope"),
        source_key_custody_receipt_sha256=_hash("key-custody"),
        source_signing_ceremony_receipt_sha256=_hash("ceremony"),
        source_trusted_signature_admission_sha256=_hash("admission"),
        pack_id=pack_id,
        pack_version="1.2.3",
        predecessor_pack_sha256=_hash("predecessor"),
        signature_request_sha256=_hash("request"),
        signature_message_sha256=_hash("message"),
        trusted_signer_policy_sha256=_hash("policy"),
        signer_key_id_sha256=_hash("signer"),
        detached_signature_sha256=_hash("signature"),
        verification_receipt_sha256=_hash("verification"),
        intent_attestation_sha256=_hash("intent"),
        stored_at_epoch_ms=1_000,
        cipher_suite=(
            SIGNATURE_ARTIFACT_DPAPI_CIPHER_SUITE if production else "TEST_ONLY_PREFIX_CIPHER"
        ),
        production_dpapi_cipher_verified=production,
    )


def _compile(payload: dict | None = None):
    return compile_signature_artifact_custody_confirmation_request(
        request_id="confirmation-request-001",
        custody_receipt_payload=_receipt().to_dict() if payload is None else payload,
        requested_at_epoch_ms=1_100,
        expires_at_epoch_ms=1_100 + MAX_CONFIRMATION_REQUEST_TTL_MS,
    )


def _rehash(payload: dict) -> None:
    payload.pop("confirmation_request_sha256", None)
    payload["confirmation_request_sha256"] = sha256_bytes(canonical_json_bytes(payload))


class _HookMapping(Mapping):
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.read_count = 0

    def __getitem__(self, key):
        self.read_count += 1
        return self.payload[key]

    def __iter__(self):
        self.read_count += 1
        return iter(self.payload)

    def __len__(self):
        self.read_count += 1
        return len(self.payload)


class _DerivedStr(str):
    pass


class _DerivedInt(int):
    pass


def test_compile_is_body_free_short_lived_and_non_authoritative() -> None:
    request = _compile()
    payload = request.to_dict()

    assert payload["state"] == SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST_STATE
    assert payload["custody_receipt_sha256"] == _receipt().to_dict()["custody_receipt_sha256"]
    assert payload["body_free_request"] is True
    assert payload["source_receipt_self_hash_required_by_compiler"] is True
    assert payload["source_receipt_self_hash_revalidated"] is False
    assert payload["source_receipt_publicly_constructible"] is True
    assert payload["trusted_human_confirmation_required"] is True
    assert payload["trusted_human_confirmation_received"] is False
    assert payload["human_confirmation_origin_authenticated"] is False
    assert payload["custody_promotion_authorized"] is False
    assert payload["canonical_custody_write_authorized"] is False
    assert payload["canonical_custody_receipt_minted"] is False
    assert payload["knowledge_pack_promotion_authorized"] is False
    assert payload["runtime_profile_apply_authorized"] is False
    assert payload["release_authorized"] is False
    assert payload["deploy_authorized"] is False
    assert payload["production_authorized"] is False
    assert payload["signature_artifact_body_included"] is False
    assert payload["public_key_material_included"] is False
    assert payload["private_key_material_included"] is False
    assert payload["absolute_host_path_included"] is False
    assert payload["credential_included"] is False
    assert "C:/" not in json.dumps(payload)
    assert verify_signature_artifact_custody_confirmation_request(payload) == request


def test_public_schema_and_package_mirror_are_exact_and_validate() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_compile().to_dict())


def test_compiler_rejects_test_cipher_and_tampered_receipt() -> None:
    with pytest.raises(ValueError, match="production DPAPI"):
        _compile(_receipt(production=False).to_dict())

    tampered = _receipt().to_dict()
    tampered["candidate_sha256"] = _hash("other-candidate")
    with pytest.raises(ValueError, match="identity mismatch"):
        _compile(tampered)


@pytest.mark.parametrize(
    ("requested", "expires"),
    [
        (999, 1_100),
        (1_100, 1_100),
        (1_100, 1_100 + MAX_CONFIRMATION_REQUEST_TTL_MS + 1),
    ],
)
def test_request_causality_and_ttl_are_hard_gates(requested: int, expires: int) -> None:
    with pytest.raises(ValueError):
        compile_signature_artifact_custody_confirmation_request(
            request_id="confirmation-request-001",
            custody_receipt_payload=_receipt().to_dict(),
            requested_at_epoch_ms=requested,
            expires_at_epoch_ms=expires,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trusted_human_confirmation_received", True),
        ("human_confirmation_origin_authenticated", True),
        ("custody_promotion_authorized", True),
        ("canonical_custody_write_authorized", True),
        ("production_authorized", True),
        ("state", "HUMAN_CONFIRMED"),
    ],
)
def test_relabel_and_authority_tamper_fail_even_after_rehash(field: str, value: object) -> None:
    payload = _compile().to_dict()
    payload[field] = value
    _rehash(payload)
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_signature_artifact_custody_confirmation_request(payload)


def test_custom_mapping_is_rejected_without_executing_hooks() -> None:
    receipt_mapping = _HookMapping(_receipt().to_dict())
    with pytest.raises(ValueError, match="exact built-in dictionary"):
        _compile(receipt_mapping)  # type: ignore[arg-type]
    assert receipt_mapping.read_count == 0

    request_mapping = _HookMapping(_compile().to_dict())
    with pytest.raises(ValueError, match="exact built-in dictionary"):
        verify_signature_artifact_custody_confirmation_request(request_mapping)
    assert request_mapping.read_count == 0


def test_exact_scalar_types_reject_subclasses_at_public_boundaries() -> None:
    with pytest.raises(ValueError, match="exact logical identifier"):
        compile_signature_artifact_custody_confirmation_request(
            request_id=_DerivedStr("confirmation-request-001"),
            custody_receipt_payload=_receipt().to_dict(),
            requested_at_epoch_ms=1_100,
            expires_at_epoch_ms=1_200,
        )
    with pytest.raises(ValueError, match="exact positive integer"):
        compile_signature_artifact_custody_confirmation_request(
            request_id="confirmation-request-001",
            custody_receipt_payload=_receipt().to_dict(),
            requested_at_epoch_ms=_DerivedInt(1_100),
            expires_at_epoch_ms=1_200,
        )

    request_payload = _compile().to_dict()
    request_payload["request_id"] = _DerivedStr(request_payload["request_id"])
    _rehash(request_payload)
    with pytest.raises(ValueError):
        verify_signature_artifact_custody_confirmation_request(request_payload)

    receipt_payload = _receipt().to_dict()
    receipt_payload["stored_at_epoch_ms"] = _DerivedInt(1_000)
    with pytest.raises(ValueError):
        _compile(receipt_payload)


def test_reconstructed_coordinates_remain_non_authoritative_and_unknown_fields_fail() -> None:
    payload = _compile().to_dict()
    payload["signer_key_id_sha256"] = _hash("other-signer")
    _rehash(payload)
    reconstructed = verify_signature_artifact_custody_confirmation_request(payload)
    assert reconstructed.signer_key_id_sha256 == _hash("other-signer")
    assert reconstructed.to_dict()["standalone_request_authoritative"] is False
    assert reconstructed.to_dict()["source_store_origin_authenticated"] is False

    unknown = copy.deepcopy(_compile().to_dict())
    unknown["human_confirmation"] = True
    _rehash(unknown)
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_signature_artifact_custody_confirmation_request(unknown)


@pytest.mark.parametrize(
    "path_like_pack_id",
    ["C:/Users/user/private/signature.ppk", "file://owner/private/signature.ppk"],
)
def test_path_like_pack_id_cannot_contradict_path_free_projection(
    path_like_pack_id: str,
) -> None:
    forged_receipt = _receipt(pack_id=path_like_pack_id).to_dict()
    with pytest.raises(ValueError, match="absolute host path or URI"):
        _compile(forged_receipt)

    serialized = _compile().to_dict()
    serialized["pack_id"] = path_like_pack_id
    _rehash(serialized)
    with pytest.raises(ValueError, match="absolute host path or URI"):
        verify_signature_artifact_custody_confirmation_request(serialized)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    mirror_schema = json.loads(MIRROR.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(serialized))
    assert list(Draft202012Validator(mirror_schema).iter_errors(serialized))
