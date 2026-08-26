from __future__ import annotations

import ast
import base64
from collections.abc import Mapping
from dataclasses import replace
import inspect
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from jsonschema import Draft202012Validator
import pytest

import ai_video_production.knowledge_pack_signature_artifact_custody_store as module
from ai_video_production.errors import ProductError
from ai_video_production.knowledge_pack_signature_artifact_custody_candidate import (
    SignatureArtifactCustodyCandidate,
    compile_signature_artifact_custody_candidate,
)
from ai_video_production.knowledge_pack_signature_artifact_custody_store import (
    SignatureArtifactCustodyConfirmation,
    SignatureArtifactCustodyReceipt,
    SignatureArtifactCustodyStore,
    WindowsDpapiSignatureArtifactCustodyCipher,
    confirm_signature_artifact_custody,
)
from ai_video_production.serialization import sha256_bytes
from test_task029_knowledge_pack_signature_artifact_custody_candidate import (
    custody_case,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/knowledge-pack-signature-artifact-custody-receipt.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name


class SyntheticCipher:
    cipher_suite = "SYNTHETIC_SIGNATURE_ARTIFACT_CUSTODY_TEST_V1"

    def __init__(self, key: int = 0x5A) -> None:
        self.key = key

    def encrypt(self, plaintext: bytes) -> bytes:
        return bytes(item ^ self.key for item in plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return bytes(item ^ self.key for item in ciphertext)


class HookMapping(Mapping[str, object]):
    def __init__(self, value: dict[str, object]) -> None:
        self.value = value
        self.read_count = 0

    def __getitem__(self, key: str) -> object:
        self.read_count += 1
        return self.value[key]

    def __iter__(self):
        self.read_count += 1
        return iter(self.value)

    def __len__(self) -> int:
        self.read_count += 1
        return len(self.value)


class DerivedStr(str):
    pass


class DerivedInt(int):
    pass


def store_case(tmp_path: Path, *, path: Path | None = None, cipher=None):
    values, admission_arguments, result, admission, candidate_arguments = custody_case(
        tmp_path / "sources"
    )
    candidate = compile_signature_artifact_custody_candidate(**candidate_arguments)
    confirmation = confirm_signature_artifact_custody(
        confirmation_id="signature-artifact-custody-confirmation.r10d",
        candidate_payload=candidate.to_dict(),
        confirmed_at_epoch_ms=700,
        explicit_human_confirmation=True,
    )
    target = path if path is not None else tmp_path / "signature-artifact.json"
    store = SignatureArtifactCustodyStore(
        target, cipher if cipher is not None else SyntheticCipher()
    )
    arguments = {
        "receipt_id": "signature-artifact-custody-receipt.r10d",
        "candidate_payload": candidate.to_dict(),
        "key_custody_receipt_payload": candidate_arguments[
            "key_custody_receipt_payload"
        ],
        "trusted_signature_admission_compile_kwargs": admission_arguments,
        "confirmation": confirmation,
        "stored_at_epoch_ms": 800,
    }
    return values, result, admission, candidate, confirmation, store, arguments


def provision(tmp_path: Path, *, path: Path | None = None, cipher=None):
    case = store_case(tmp_path, path=path, cipher=cipher)
    result = case[5].provision(**case[6])
    return (*case, result)


def test_exact_r10b_r10c_recompile_encrypts_and_reads_body_free_receipt(
    tmp_path: Path,
) -> None:
    values, _, admission, candidate, confirmation, store, arguments, saved = provision(
        tmp_path
    )
    receipt = saved.receipt
    payload = receipt.to_dict()

    assert store.read_receipt() == receipt
    assert SignatureArtifactCustodyReceipt.from_dict(payload) == receipt
    assert payload["candidate_sha256"] == candidate.to_dict()[
        "custody_candidate_sha256"
    ]
    assert payload["source_trusted_signature_admission_sha256"] == admission.to_dict()[
        "trusted_signature_admission_sha256"
    ]
    assert payload["confirmation_sha256"] == confirmation.to_dict()[
        "confirmation_sha256"
    ]
    assert payload["r10b_direct_recompiled_at_write"] is True
    assert payload[
        "cryptographic_signature_verified_against_supplied_policy_at_write"
    ] is True
    assert payload["r10c_candidate_recompiled_at_write"] is True
    assert payload["signature_artifact_custody_confirmed"] is True

    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert set(document) == {
        "schema_version",
        "record_type",
        "task_owner",
        "cipher_suite",
        "ciphertext_b64",
        "ciphertext_sha256",
        "plaintext_fields_present",
        "document_sha256",
    }
    raw = store.path.read_bytes()
    assert values[7] not in raw
    assert values[8] not in raw
    assert base64.b64encode(values[8]) not in raw
    assert base64.b64encode(
        arguments["trusted_signature_admission_compile_kwargs"][
            "detached_signature_bytes"
        ]
    ) not in raw
    assert b"signature-artifact-custody-candidate.r10c" not in raw


def test_public_receipt_schema_and_package_mirror_are_exact(tmp_path: Path) -> None:
    receipt = provision(tmp_path)[-1].receipt.to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(receipt)
    changed = dict(receipt)
    changed["knowledge_pack_promotion_authorized"] = True
    assert list(Draft202012Validator(schema).iter_errors(changed))


def test_receipt_flags_bound_confirmed_custody_without_promotion_authority(
    tmp_path: Path,
) -> None:
    payload = provision(tmp_path)[-1].receipt.to_dict()
    for field in (
        "r10b_direct_recompiled_at_write",
        "caller_supplied_source_graph_recompiled_at_write",
        "cryptographic_signature_verified_against_supplied_policy_at_write",
        "r10c_candidate_recompiled_at_write",
        "explicit_human_custody_confirmation_received",
        "owner_local_encrypted_store_implemented",
        "one_shot_write_completed",
        "post_write_readback_verified",
        "signature_artifact_custody_confirmed",
        "symlink_rejection_present",
        "encrypted_at_rest",
        "body_free_receipt",
    ):
        assert payload[field] is True
    for field in (
        "signature_artifact_body_included",
        "public_key_material_included",
        "private_key_material_included",
        "absolute_host_path_included",
        "credential_included",
        "directory_durability_confirmed",
        "power_loss_replay_prevention_confirmed",
        "hostile_path_race_protection_confirmed",
        "deletion_replay_prevention_confirmed",
        "alternate_path_replay_prevention_confirmed",
        "owner_local_path_verified",
        "canonical_store_path_binding_confirmed",
        "project_scope_coordinates_included",
        "canonical_project_binding_confirmed",
        "canonical_latest_source_revalidated",
        "canonical_trusted_signer_policy_revalidated",
        "owner_scope_origin_authenticated",
        "canonical_trust_root_confirmed",
        "owner_signer_binding_confirmed",
        "canonical_knowledge_pack_receipt_minted",
        "knowledge_pack_write_authorized",
        "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized",
        "runtime_profile_apply_authorized",
        "rollback_execution_authorized",
        "timeline_mutation_authorized",
        "resolve_mutation_authorized",
        "release_authorized",
        "deploy_authorized",
        "production_authorized",
        "external_effect_authorized",
    ):
        assert payload[field] is False


def test_explicit_human_confirmation_is_required_and_exactly_bound(
    tmp_path: Path,
) -> None:
    _, _, _, candidate, _, _, _ = store_case(tmp_path)
    with pytest.raises(ProductError) as error:
        confirm_signature_artifact_custody(
            confirmation_id="confirmation",
            candidate_payload=candidate.to_dict(),
            confirmed_at_epoch_ms=700,
            explicit_human_confirmation=False,
        )
    assert error.value.code == "ERR_SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUIRED"

    _, _, _, _, confirmation, store, arguments = store_case(tmp_path / "drift")
    arguments["confirmation"] = replace(
        confirmation, detached_signature_sha256="sha256:" + "9" * 64
    )
    with pytest.raises(ValueError, match="confirmation does not match"):
        store.provision(**arguments)


def test_r10b_and_r10c_are_recompiled_with_exact_transient_artifacts(
    tmp_path: Path,
) -> None:
    _, _, _, _, _, store, arguments = store_case(tmp_path)
    compile_kwargs = dict(arguments["trusted_signature_admission_compile_kwargs"])
    signature = compile_kwargs["detached_signature_bytes"]
    compile_kwargs["detached_signature_bytes"] = bytes([signature[0] ^ 1]) + signature[1:]
    arguments["trusted_signature_admission_compile_kwargs"] = compile_kwargs
    with pytest.raises((ValueError, InvalidSignature)):
        store.provision(**arguments)

    _, _, _, candidate, _, store, arguments = store_case(tmp_path / "candidate")
    changed = dict(candidate.to_dict())
    changed["custody_candidate_sha256"] = "sha256:" + "0" * 64
    arguments["candidate_payload"] = changed
    with pytest.raises(ValueError):
        store.provision(**arguments)


def test_one_shot_store_rejects_overwrite_without_changing_receipt(
    tmp_path: Path,
) -> None:
    *_, store, arguments, first = provision(tmp_path)
    with pytest.raises(ProductError) as error:
        store.provision(**arguments)
    assert error.value.code == "ERR_SIGNATURE_ARTIFACT_CUSTODY_ALREADY_EXISTS"
    assert store.read_receipt() == first.receipt


def test_tamper_wrong_cipher_plaintext_and_symlink_fail_closed(
    tmp_path: Path,
) -> None:
    *_, store, _, _ = provision(tmp_path)
    document = json.loads(store.path.read_text(encoding="utf-8"))
    document["ciphertext_b64"] = document["ciphertext_b64"][:-4] + "AAAA"
    store.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as error:
        store.read_receipt()
    assert error.value.code == "ERR_SIGNATURE_ARTIFACT_CUSTODY_INTEGRITY"

    *_, other_store, _, _ = provision(
        tmp_path / "wrong", cipher=SyntheticCipher(0x33)
    )
    with pytest.raises(ProductError):
        SignatureArtifactCustodyStore(
            other_store.path, SyntheticCipher(0x44)
        ).read_receipt()

    plain = tmp_path / "plain.json"
    plain.write_text('{"public_key_b64":"secret"}', encoding="utf-8")
    with pytest.raises(ProductError):
        SignatureArtifactCustodyStore(plain, SyntheticCipher()).read_receipt()

    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pass
    else:
        _, _, _, _, _, link_store, link_arguments = store_case(
            tmp_path / "link-case", path=link
        )
        with pytest.raises(ProductError):
            link_store.provision(**link_arguments)


def test_atomic_failure_leaves_no_target_and_retry_can_succeed(tmp_path: Path) -> None:
    _, _, _, _, _, store, arguments = store_case(tmp_path)

    def stop(stage: str, _: Path) -> None:
        if stage == "before_replace":
            raise RuntimeError("injected")

    arguments["failure_injector"] = stop
    with pytest.raises(RuntimeError, match="injected"):
        store.provision(**arguments)
    assert not store.path.exists()
    arguments.pop("failure_injector")
    assert store.provision(**arguments).receipt == store.read_receipt()


def test_causality_and_exact_security_scalars_fail_before_write(tmp_path: Path) -> None:
    _, _, _, _, confirmation, store, arguments = store_case(tmp_path)
    arguments["stored_at_epoch_ms"] = confirmation.confirmed_at_epoch_ms - 1
    with pytest.raises(ValueError, match="storage precedes"):
        store.provision(**arguments)
    assert not store.path.exists()

    _, _, _, _, _, store, arguments = store_case(tmp_path / "derived")
    arguments["receipt_id"] = DerivedStr(arguments["receipt_id"])
    with pytest.raises(ValueError, match="receipt_id"):
        store.provision(**arguments)
    arguments["receipt_id"] = "receipt"
    arguments["stored_at_epoch_ms"] = DerivedInt(800)
    with pytest.raises(ValueError, match="exact positive"):
        store.provision(**arguments)


def test_custom_public_mappings_are_rejected_without_hook_reads(tmp_path: Path) -> None:
    _, _, _, candidate, confirmation, store, arguments = store_case(tmp_path)
    wrapped_candidate = HookMapping(candidate.to_dict())
    arguments["candidate_payload"] = wrapped_candidate
    with pytest.raises(ValueError, match="exact built-in object"):
        store.provision(**arguments)
    assert wrapped_candidate.read_count == 0

    wrapped_confirmation = HookMapping(confirmation.to_dict())
    with pytest.raises(ValueError, match="exact built-in object"):
        SignatureArtifactCustodyConfirmation.from_dict(wrapped_confirmation)
    assert wrapped_confirmation.read_count == 0

    arguments["candidate_payload"] = candidate.to_dict()
    wrapped_kwargs = HookMapping(arguments["trusted_signature_admission_compile_kwargs"])
    arguments["trusted_signature_admission_compile_kwargs"] = wrapped_kwargs
    with pytest.raises(ValueError, match="exact object"):
        store.provision(**arguments)
    assert wrapped_kwargs.read_count == 0


def test_receipt_tamper_unknown_field_and_hash_fail_closed(tmp_path: Path) -> None:
    payload = provision(tmp_path)[-1].receipt.to_dict()
    for field, value in (
        ("production_authorized", True),
        ("signature_artifact_custody_confirmed", False),
        ("custody_receipt_sha256", "sha256:" + "0" * 64),
    ):
        changed = dict(payload)
        changed[field] = value
        with pytest.raises(ValueError):
            SignatureArtifactCustodyReceipt.from_dict(changed)
    changed = dict(payload)
    changed["unknown"] = False
    with pytest.raises(ValueError):
        SignatureArtifactCustodyReceipt.from_dict(changed)


def test_module_has_no_network_process_or_private_key_capability() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports.isdisjoint({"requests", "httpx", "socket", "subprocess"})
    assert "Ed25519PrivateKey" not in source
    assert "private_key_seed" not in source
    provision_parameters = inspect.signature(
        SignatureArtifactCustodyStore.provision
    ).parameters
    assert "private_key" not in provision_parameters
    assert "private_key_seed" not in provision_parameters


@pytest.mark.skipif(os.name != "nt", reason="Windows Current User DPAPI only")
def test_windows_dpapi_round_trip_uses_synthetic_artifacts_only(tmp_path: Path) -> None:
    cipher = WindowsDpapiSignatureArtifactCustodyCipher()
    *_, store, _, saved = provision(tmp_path, cipher=cipher)
    assert store.read_receipt() == saved.receipt
