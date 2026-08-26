from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.montage_learning_admission_store import (
    MontageLearningAdmissionEntry,
)
from ai_video_production import montage_learning_canonical_preflight as preflight_module
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    validate_exact_evidence_delivery,
)
from ai_video_production.montage_learning_canonical_preflight import (
    HUMAN_BINDING_DOMAIN,
    PREFLIGHT_DOMAIN,
    MontageLearningCanonicalPreflight,
    MontageLearningCanonicalPreflightError,
    compile_montage_learning_canonical_preflight,
    derive_canonical_evidence_id,
    derive_human_binding_sha256,
)
from ai_video_production.montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task058_montage_learning_bridge_contracts import (
    OWNER_SCOPE_HASH,
    _exact_delivery,
    _generic_delivery,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "montage-learning-canonical-preflight.schema.json"
MIRROR = (
    ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
)


def _resign(body: dict[str, object], field: str) -> dict[str, object]:
    unsigned = dict(body)
    unsigned.pop(field, None)
    return {**unsigned, field: sha256_bytes(canonical_json_bytes(unsigned))}


def _entry(delivery: dict[str, object]) -> MontageLearningAdmissionEntry:
    source_record_id = str(delivery["record_id"])
    source_sha = str(delivery["evidence_sha256"])
    evidence_id = derive_canonical_evidence_id(source_sha)
    return MontageLearningAdmissionEntry(
        sequence=1,
        canonical_evidence_id=evidence_id,
        source_record_id=source_record_id,
        source_sha256=source_sha,
        owner_scope_hash=OWNER_SCOPE_HASH,
        idempotency_key_sha256=derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id=source_record_id,
            source_sha256=source_sha,
            owner_scope_hash=OWNER_SCOPE_HASH,
        ),
        canonical_evidence_sha256=source_sha,
        human_binding_sha256=derive_human_binding_sha256(
            project_id=str(delivery["proposal"]["project_id"]),
            source_record_id=source_record_id,
            owner_scope_hash=OWNER_SCOPE_HASH,
            proposal_sha256=str(delivery["proposal_sha256"]),
            approved_plan_sha256=str(delivery["approved_plan_sha256"]),
            evidence_sha256=source_sha,
        ),
        committed_at="2026-08-26T00:00:01Z",
        previous_entry_sha256=None,
    )


def _compile(
    delivery: dict[str, object] | None = None,
    entry: MontageLearningAdmissionEntry | None = None,
) -> MontageLearningCanonicalPreflight:
    source = _exact_delivery() if delivery is None else delivery
    staging = _entry(source) if entry is None else entry
    return compile_montage_learning_canonical_preflight(
        source,
        staging.to_dict(),
        expected_owner_scope_hash=OWNER_SCOPE_HASH,
    )


def test_exact_source_and_human_binding_preflight_is_body_free_and_strict() -> None:
    delivery = _exact_delivery()
    entry = _entry(delivery)
    result = _compile(delivery, entry)
    body = result.to_dict()

    assert body["admission_state"] == "NONAUTHORITATIVE_SOURCE_HUMAN_PREFLIGHT_PROJECTION"
    assert body["project_id"] == "proj-test"
    assert body["source_record_id"] == delivery["record_id"]
    assert body["source_sha256"] == delivery["evidence_sha256"]
    assert body["staging_entry_sha256"] == entry.to_dict()["entry_sha256"]
    assert body["proposal_sha256"] == delivery["proposal_sha256"]
    assert body["approved_plan_sha256"] == delivery["approved_plan_sha256"]
    assert body["projection_structure_valid"] is True
    assert body["negative_feedback_preserved"] is False
    for field in (
        "compiler_execution_verified",
        "source_lineage_origin_verified",
        "human_binding_origin_verified",
        "staging_entry_origin_verified",
        "staging_membership_verified",
        "staging_store_origin_verified",
        "monotonic_project_anchor_verified",
        "rollback_detection_authority_created",
        "canonical_store_written",
        "receipt_minted",
        "canonical_admission_authority_created",
        "automatic_learning_promotion_authorized",
        "timeline_mutation_authorized",
        "resolve_write_authorized",
        "external_effect_authorized",
    ):
        assert body[field] is False
    assert body["canonical_store_commit_sha256"] is None
    raw = canonical_json_bytes(body)
    for forbidden in (
        b"proposal\"", b"approved_plan\"", b"human_edit_evidence\"",
        b"placements\"", b"transcript", b"absolute_host_path",
    ):
        assert forbidden not in raw
    assert MontageLearningCanonicalPreflight.from_dict(body) == result


def test_public_constructor_cannot_mint_compiler_or_origin_authority() -> None:
    delivery = _exact_delivery()
    evidence_sha = str(delivery["evidence_sha256"])
    source_record_id = str(delivery["record_id"])
    project_id = str(delivery["proposal"]["project_id"])
    manual = MontageLearningCanonicalPreflight(
        project_id=project_id,
        source_record_id=source_record_id,
        source_sha256=evidence_sha,
        owner_scope_hash=OWNER_SCOPE_HASH,
        proposal_sha256=str(delivery["proposal_sha256"]),
        approved_plan_sha256=str(delivery["approved_plan_sha256"]),
        idempotency_key_sha256=derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id=source_record_id,
            source_sha256=evidence_sha,
            owner_scope_hash=OWNER_SCOPE_HASH,
        ),
        staging_entry_sha256="sha256:" + "9" * 64,
        canonical_evidence_id=derive_canonical_evidence_id(evidence_sha),
        canonical_evidence_sha256=evidence_sha,
        human_binding_sha256=derive_human_binding_sha256(
            project_id=project_id,
            source_record_id=source_record_id,
            owner_scope_hash=OWNER_SCOPE_HASH,
            proposal_sha256=str(delivery["proposal_sha256"]),
            approved_plan_sha256=str(delivery["approved_plan_sha256"]),
            evidence_sha256=evidence_sha,
        ),
        negative_feedback_preserved=False,
    )
    body = manual.to_dict()
    assert body["admission_state"] == "NONAUTHORITATIVE_SOURCE_HUMAN_PREFLIGHT_PROJECTION"
    for field in (
        "compiler_execution_verified", "source_lineage_origin_verified",
        "human_binding_origin_verified", "staging_entry_origin_verified",
        "staging_membership_verified", "staging_store_origin_verified",
    ):
        assert body[field] is False
    assert MontageLearningCanonicalPreflight.from_dict(body) == manual


def test_schema_mirror_meta_schema_and_runtime_parity() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    body = _compile().to_dict()
    Draft202012Validator(schema).validate(body)

    tampered = dict(body)
    tampered["canonical_store_written"] = True
    with pytest.raises(ValueError):
        MontageLearningCanonicalPreflight.from_dict(tampered)
    tampered = dict(body)
    tampered["unknown"] = False
    with pytest.raises(ValueError):
        MontageLearningCanonicalPreflight.from_dict(tampered)


def test_fixed_domain_derivations_match_manual_vectors() -> None:
    delivery = _exact_delivery()
    binding_body = {
        "approved_plan_sha256": delivery["approved_plan_sha256"],
        "evidence_sha256": delivery["evidence_sha256"],
        "owner_scope_hash": OWNER_SCOPE_HASH,
        "project_id": delivery["proposal"]["project_id"],
        "proposal_sha256": delivery["proposal_sha256"],
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": delivery["record_id"],
    }
    expected = sha256_bytes(HUMAN_BINDING_DOMAIN + canonical_json_bytes(binding_body))
    assert _entry(delivery).human_binding_sha256 == expected
    result_body = _compile(delivery).to_dict()
    unsigned = dict(result_body)
    supplied = unsigned.pop("preflight_sha256")
    assert supplied == sha256_bytes(PREFLIGHT_DOMAIN + canonical_json_bytes(unsigned))


@pytest.mark.parametrize(
    "field",
    [
        "source_record_id",
        "source_sha256",
        "owner_scope_hash",
        "canonical_evidence_id",
        "canonical_evidence_sha256",
        "human_binding_sha256",
    ],
)
def test_every_staging_coordinate_mismatch_fails_closed(field: str) -> None:
    delivery = _exact_delivery()
    original = _entry(delivery)
    changes: dict[str, object]
    if field == "source_record_id":
        changes = {"source_record_id": "other-record"}
    elif field == "source_sha256":
        changes = {"source_sha256": "sha256:" + "1" * 64}
    elif field == "owner_scope_hash":
        changes = {"owner_scope_hash": "sha256:" + "2" * 64}
    elif field == "canonical_evidence_id":
        changes = {"canonical_evidence_id": "other-evidence"}
    elif field == "canonical_evidence_sha256":
        changes = {"canonical_evidence_sha256": "sha256:" + "3" * 64}
    else:
        changes = {"human_binding_sha256": "sha256:" + "4" * 64}
    source_record_id = str(changes.get("source_record_id", original.source_record_id))
    source_sha = str(changes.get("source_sha256", original.source_sha256))
    owner_scope = str(changes.get("owner_scope_hash", original.owner_scope_hash))
    changes["idempotency_key_sha256"] = (
        derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id=source_record_id,
            source_sha256=source_sha,
            owner_scope_hash=owner_scope,
        )
    )
    changed = replace(original, **changes)
    with pytest.raises(MontageLearningCanonicalPreflightError):
        _compile(delivery, changed)


def test_tampered_staging_hash_and_generic_source_fail_closed() -> None:
    delivery = _exact_delivery()
    staged = _entry(delivery).to_dict()
    staged["committed_at"] = "2026-08-26T00:00:02Z"
    with pytest.raises(MontageLearningCanonicalPreflightError):
        compile_montage_learning_canonical_preflight(
            delivery, staged, expected_owner_scope_hash=OWNER_SCOPE_HASH
        )

    with pytest.raises(MontageLearningCanonicalPreflightError):
        compile_montage_learning_canonical_preflight(
            _generic_delivery(),
            _entry(delivery).to_dict(),
            expected_owner_scope_hash=OWNER_SCOPE_HASH,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lane", "GENERIC_SKILL_OBSERVATION"),
        ("validation_state", "REVIEW_REQUIRED"),
        ("owner_scope_state", "OWNER_SCOPE_UNBOUND"),
        ("review_state", "APPROVED"),
        ("runtime_observation_state", "SOURCE_PASS_CLAIM_STRUCTURALLY_VALID_NONAUTHORITATIVE"),
    ],
)
def test_dependency_candidate_state_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch, field: str, value: str,
) -> None:
    delivery = _exact_delivery()
    candidate = validate_exact_evidence_delivery(
        delivery, expected_owner_scope_hash=OWNER_SCOPE_HASH
    )

    def drifted_validator(*args: object, **kwargs: object):
        del args, kwargs
        return replace(candidate, **{field: value})

    monkeypatch.setattr(
        preflight_module, "validate_exact_evidence_delivery", drifted_validator
    )
    with pytest.raises(
        MontageLearningCanonicalPreflightError, match="candidate state drifted"
    ):
        _compile(delivery)


def test_do_not_learn_is_rejected_after_exact_lineage_revalidation() -> None:
    delivery = _exact_delivery()
    evidence = deepcopy(delivery["human_edit_evidence"])
    assert isinstance(evidence, dict)
    evidence["do_not_learn"] = True
    evidence = _resign(evidence, "evidence_sha256")
    delivery["human_edit_evidence"] = evidence
    delivery["evidence_sha256"] = evidence["evidence_sha256"]
    with pytest.raises(MontageLearningCanonicalPreflightError, match="do_not_learn"):
        _compile(delivery)


def test_deleted_human_edit_is_preserved_as_negative_feedback() -> None:
    delivery = _exact_delivery()
    evidence = deepcopy(delivery["human_edit_evidence"])
    assert isinstance(evidence, dict)
    evidence.update(
        {
            "disposition": "DELETED",
            "final_target_timeline_frame": None,
            "delta_from_proposal_frames": None,
            "delta_from_review_frames": None,
            "do_not_learn": False,
        }
    )
    evidence = _resign(evidence, "evidence_sha256")
    delivery["human_edit_evidence"] = evidence
    delivery["evidence_sha256"] = evidence["evidence_sha256"]
    result = _compile(delivery)
    assert result.negative_feedback_preserved is True
    assert result.to_dict()["automatic_learning_promotion_authorized"] is False


def test_custom_json_types_fail_without_invoking_hooks() -> None:
    hooks: list[str] = []

    class ChameleonDict(dict[str, object]):
        def items(self):  # type: ignore[no-untyped-def]
            hooks.append("items")
            return super().items()

        def __deepcopy__(self, memo: object) -> dict[str, object]:
            del memo
            hooks.append("deepcopy")
            return {}

    delivery = _exact_delivery()
    staging = _entry(delivery).to_dict()
    with pytest.raises(MontageLearningCanonicalPreflightError):
        compile_montage_learning_canonical_preflight(
            ChameleonDict(delivery), staging,
            expected_owner_scope_hash=OWNER_SCOPE_HASH,
        )
    with pytest.raises(MontageLearningCanonicalPreflightError):
        compile_montage_learning_canonical_preflight(
            delivery, ChameleonDict(staging),
            expected_owner_scope_hash=OWNER_SCOPE_HASH,
        )
    nested = deepcopy(delivery)
    nested["proposal"] = ChameleonDict(nested["proposal"])
    with pytest.raises(MontageLearningCanonicalPreflightError):
        compile_montage_learning_canonical_preflight(
            nested, staging,
            expected_owner_scope_hash=OWNER_SCOPE_HASH,
        )
    assert hooks == []


def test_inputs_are_snapshotted_and_result_is_immutable() -> None:
    delivery = _exact_delivery()
    staged = _entry(delivery).to_dict()
    result = compile_montage_learning_canonical_preflight(
        delivery, staged, expected_owner_scope_hash=OWNER_SCOPE_HASH
    )
    delivery["record_id"] = "mutated-after-call"
    staged["source_record_id"] = "mutated-after-call"
    assert result.source_record_id == "exact-delivery-001"
    assert result.project_id == "proj-test"
    with pytest.raises(Exception):
        result.source_record_id = "forbidden"  # type: ignore[misc]


def test_module_has_no_direct_mutable_io_network_native_or_store_write_surface() -> None:
    source_path = (
        ROOT / "src" / "ai_video_production"
        / "montage_learning_canonical_preflight.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert not imported.intersection(
        {"os", "pathlib", "socket", "subprocess", "sqlite3", "urllib", "requests"}
    )
    public = set(ast.literal_eval(next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )))
    assert "MontageLearningAdmissionStore" not in public
    assert all("write" not in name.lower() and "receipt" not in name.lower() for name in public)
