from __future__ import annotations

import ast
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import inspect
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.knowledge_pack_local_signing_ceremony import (
    LocalSigningCeremonyReceipt,
)
from ai_video_production.knowledge_pack_signature_artifact_custody_candidate import (
    SignatureArtifactCustodyCandidate,
    SignatureArtifactCustodyCandidateState,
    compile_signature_artifact_custody_candidate,
    verify_signature_artifact_custody_candidate,
)
from ai_video_production.knowledge_pack_trusted_signature_admission import (
    compile_knowledge_pack_trusted_signature_admission,
)
from ai_video_production.owner_signing_key_custody import OwnerSigningKeyCustodyReceipt
from test_task029_knowledge_pack_trusted_signature_admission import signed_case


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/knowledge-pack-signature-artifact-custody-candidate.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name


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


def custody_case(tmp_path: Path):
    values, ceremony_arguments, _, result, _, admission_arguments = signed_case(tmp_path)
    admission = compile_knowledge_pack_trusted_signature_admission(**admission_arguments)
    arguments = {
        "candidate_id": "signature-artifact-custody-candidate.r10c",
        "artifact_store_id": "signature-artifact-store.owner-local.001",
        "key_custody_receipt_payload": ceremony_arguments["custody_receipt_payload"],
        "signing_ceremony_receipt_payload": result.receipt.to_dict(),
        "trusted_signature_admission_payload": admission.to_dict(),
        "created_at_epoch_ms": 600,
    }
    return values, admission_arguments, result, admission, arguments


def test_exact_r9b_r9c_r10b_coordinates_compile_body_free_candidate(tmp_path: Path) -> None:
    values, admission_arguments, result, admission, arguments = custody_case(tmp_path)
    candidate = compile_signature_artifact_custody_candidate(**arguments)
    payload = candidate.to_dict()
    custody = OwnerSigningKeyCustodyReceipt.from_dict(arguments["key_custody_receipt_payload"])

    assert candidate.state is (
        SignatureArtifactCustodyCandidateState.READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION
    )
    assert payload["owner_scope_sha256"] == custody.owner_scope_sha256
    assert payload["source_signing_ceremony_receipt_sha256"] == result.receipt.to_dict()[
        "ceremony_receipt_sha256"
    ]
    assert payload["source_trusted_signature_admission_sha256"] == admission.to_dict()[
        "trusted_signature_admission_sha256"
    ]
    assert payload["detached_signature_sha256"] == admission.detached_signature_sha256
    assert SignatureArtifactCustodyCandidate.from_dict(payload) == candidate
    verify_signature_artifact_custody_candidate(payload, **arguments)

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    assert values[7] not in raw
    assert values[8] not in raw
    assert admission_arguments["detached_signature_bytes"] not in raw


def test_schema_and_package_mirror_are_exact(tmp_path: Path) -> None:
    payload = compile_signature_artifact_custody_candidate(**custody_case(tmp_path)[4]).to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_remaining_gates_and_effects_are_machine_readable(tmp_path: Path) -> None:
    payload = compile_signature_artifact_custody_candidate(**custody_case(tmp_path)[4]).to_dict()
    for field in (
        "r10b_direct_recompile_required_at_write",
        "transient_public_key_required_at_write",
        "r9b_r9c_r10b_receipts_self_validated",
        "owner_scope_sourced_from_r9b_receipt",
        "transient_detached_signature_required_at_write",
        "cryptographic_reverification_required_at_write",
        "owner_local_encrypted_store_required",
        "one_shot_artifact_write_required",
        "explicit_human_custody_confirmation_required",
        "in_memory_candidate_only",
        "owner_scope_coordinates_included",
    ):
        assert payload[field] is True
    for field in (
        "project_scope_coordinates_included", "reviewer_coordinates_included",
        "source_graph_currentness_confirmed", "owner_scope_origin_authenticated",
        "signature_artifact_body_included", "public_key_material_included",
        "private_key_material_included", "absolute_host_path_included",
        "credential_included", "artifact_custody_write_authorized",
        "signature_artifact_custody_confirmed", "canonical_receipt_minted",
        "canonical_trust_root_confirmed", "owner_signer_binding_confirmed",
        "knowledge_pack_write_authorized", "knowledge_pack_promotion_authorized",
        "automatic_promotion_authorized", "runtime_profile_apply_authorized",
        "rollback_execution_authorized", "release_authorized", "external_effect_authorized",
    ):
        assert payload[field] is False


def test_custody_ceremony_and_admission_cross_binding_fail_closed(tmp_path: Path) -> None:
    _, _, _, _, arguments = custody_case(tmp_path)
    custody = OwnerSigningKeyCustodyReceipt.from_dict(arguments["key_custody_receipt_payload"])
    arguments["key_custody_receipt_payload"] = replace(
        custody, signer_key_id_sha256="sha256:" + "9" * 64
    ).to_dict()
    with pytest.raises(ValueError, match="exact key custody receipt"):
        compile_signature_artifact_custody_candidate(**arguments)

    _, _, _, _, arguments = custody_case(tmp_path / "ceremony-drift")
    ceremony = LocalSigningCeremonyReceipt.from_dict(
        arguments["signing_ceremony_receipt_payload"]
    )
    arguments["signing_ceremony_receipt_payload"] = replace(
        ceremony, detached_signature_sha256="sha256:" + "8" * 64
    ).to_dict()
    with pytest.raises(ValueError, match="does not match the exact R10B"):
        compile_signature_artifact_custody_candidate(**arguments)


@pytest.mark.parametrize("created_at", [1, 499])
def test_candidate_time_cannot_precede_source_evidence(
    tmp_path: Path, created_at: int,
) -> None:
    _, _, _, _, arguments = custody_case(tmp_path)
    arguments["created_at_epoch_ms"] = created_at
    with pytest.raises(ValueError, match="precedes"):
        compile_signature_artifact_custody_candidate(**arguments)


def test_exact_scalar_subclasses_are_rejected(tmp_path: Path) -> None:
    _, _, _, _, arguments = custody_case(tmp_path)
    arguments["candidate_id"] = DerivedStr(arguments["candidate_id"])
    with pytest.raises(ValueError, match="candidate_id"):
        compile_signature_artifact_custody_candidate(**arguments)

    _, _, _, _, arguments = custody_case(tmp_path / "derived-time")
    arguments["created_at_epoch_ms"] = DerivedInt(600)
    with pytest.raises(ValueError, match="exact positive"):
        compile_signature_artifact_custody_candidate(**arguments)

    _, _, _, _, arguments = custody_case(tmp_path / "derived-nested")
    changed = deepcopy(arguments["trusted_signature_admission_payload"])
    changed["pack_id"] = DerivedStr(changed["pack_id"])
    arguments["trusted_signature_admission_payload"] = changed
    with pytest.raises(ValueError, match="derived value"):
        compile_signature_artifact_custody_candidate(**arguments)


@pytest.mark.parametrize(
    "field",
    ["key_custody_receipt_payload", "signing_ceremony_receipt_payload", "trusted_signature_admission_payload"],
)
def test_custom_mapping_is_rejected_without_hook_reads(tmp_path: Path, field: str) -> None:
    _, _, _, _, arguments = custody_case(tmp_path)
    wrapped = HookMapping(arguments[field])
    arguments[field] = wrapped
    with pytest.raises(ValueError, match="exact built-in object"):
        compile_signature_artifact_custody_candidate(**arguments)
    assert wrapped.read_count == 0


def test_output_tamper_unknown_field_and_custom_mapping_fail_closed(tmp_path: Path) -> None:
    _, _, _, _, arguments = custody_case(tmp_path)
    payload = compile_signature_artifact_custody_candidate(**arguments).to_dict()
    for field, value in (
        ("artifact_custody_write_authorized", True),
        ("custody_candidate_sha256", "sha256:" + "0" * 64),
    ):
        changed = dict(payload)
        changed[field] = value
        with pytest.raises(ValueError):
            SignatureArtifactCustodyCandidate.from_dict(changed)
    changed = dict(payload)
    changed["unknown"] = False
    with pytest.raises(ValueError, match="incomplete or unknown"):
        SignatureArtifactCustodyCandidate.from_dict(changed)
    wrapped = HookMapping(payload)
    with pytest.raises(ValueError, match="exact built-in object"):
        SignatureArtifactCustodyCandidate.from_dict(wrapped)
    assert wrapped.read_count == 0


def test_candidate_is_immutable_and_module_has_no_io_capability(tmp_path: Path) -> None:
    candidate = compile_signature_artifact_custody_candidate(**custody_case(tmp_path)[4])
    with pytest.raises(FrozenInstanceError):
        candidate.state = SignatureArtifactCustodyCandidateState.READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION  # type: ignore[misc]

    import ai_video_production.knowledge_pack_signature_artifact_custody_candidate as module

    tree = ast.parse(inspect.getsource(module))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported.intersection(
        {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "sqlite3"}
    )
