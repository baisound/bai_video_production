from __future__ import annotations

import ast
import builtins
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.montage_learning_receipt_contracts as receipt_module
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
)
from ai_video_production.montage_learning_receipt_contracts import (
    ACCEPTED,
    CONTRACT_PROFILE,
    DUPLICATE,
    EXACT_EVIDENCE,
    GENERIC_OBSERVATION,
    IDEMPOTENCY_DOMAIN,
    MESSAGE_TYPE,
    RECEIPT_DOMAIN,
    REJECTED,
    REVIEW_REQUIRED,
    SCHEMA_VERSION,
    MontageLearningAdmissionReceipt,
    MontageLearningReceiptContractError,
    compute_montage_learning_receipt_sha256,
    derive_montage_learning_idempotency_key_sha256,
    parse_montage_learning_admission_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
SCOPE = "sha256:" + "a" * 64
SOURCE = "sha256:" + "b" * 64
OTHER_DIGEST = "sha256:" + "c" * 64
IDEMPOTENCY_VECTOR = (
    "sha256:9dc68f81fe5961526acea445b27f58b58db733e2a5f679f6099952108661d686"
)
RECEIPT_VECTOR = (
    "sha256:f31513b7318ba49a51348dc4c858391988eec2ef2feaf0c0c2b04eb17fb1468e"
)
PUBLIC_FIELDS = {
    "receipt_id",
    "admission_class",
    "source_record_id",
    "source_sha256",
    "status",
    "reason_codes",
    "receipt_sha256",
    "canonical_store_commit_claimed",
    "receipt_structure_valid",
    "origin_authority_verified",
    "duplicate_lineage_verified",
    "canonical_store_commit_verified",
    "canonical_admission_authority_created",
    "receipt_minted",
}


def _receipt(
    *,
    admission_class: str = EXACT_EVIDENCE,
    status: str = ACCEPTED,
    store_written: bool = False,
) -> dict[str, object]:
    source_profile = (
        EXACT_CONTRACT_PROFILE
        if admission_class == EXACT_EVIDENCE
        else GENERIC_CONTRACT_PROFILE
    )
    reasons: list[str]
    duplicate_ref: str | None = None
    if status == ACCEPTED:
        reasons = []
    elif status == DUPLICATE:
        reasons = ["DUPLICATE_IDEMPOTENCY_KEY"]
        duplicate_ref = OTHER_DIGEST
    elif status == REVIEW_REQUIRED:
        reasons = ["REVIEW_BINDING_REQUIRED"]
    else:
        reasons = ["HASH_MISMATCH"]
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "message_type": MESSAGE_TYPE,
        "contract_profile": CONTRACT_PROFILE,
        "receipt_id": "receipt-001",
        "admission_class": admission_class,
        "source_contract_profile": source_profile,
        "source_record_id": "record-001",
        "source_sha256": SOURCE,
        "owner_scope_hash": SCOPE,
        "idempotency_key_sha256": (
            derive_montage_learning_idempotency_key_sha256(
                source_contract_profile=source_profile,
                source_record_id="record-001",
                source_sha256=SOURCE,
                owner_scope_hash=SCOPE,
            )
        ),
        "status": status,
        "canonical_store_written": store_written,
        "canonical_evidence_id": "evidence-001" if store_written else None,
        "canonical_evidence_sha256": OTHER_DIGEST if store_written else None,
        "canonical_store_commit_sha256": OTHER_DIGEST if store_written else None,
        "duplicate_of_receipt_sha256": duplicate_ref,
        "reason_codes": reasons,
        "attempt": 1,
        "processed_at": "2026-08-26T00:00:00Z",
        "bridge_instance_id": "bridge-001",
    }
    return _resign(body)


def _resign(value: dict[str, object]) -> dict[str, object]:
    value.pop("receipt_sha256", None)
    value["receipt_sha256"] = compute_montage_learning_receipt_sha256(value)
    return value


def _assert_rejected(value: object) -> None:
    with pytest.raises(MontageLearningReceiptContractError):
        parse_montage_learning_admission_receipt(value)  # type: ignore[arg-type]


def test_schema_is_valid_and_public_package_mirrors_are_byte_exact() -> None:
    public_path = ROOT / "schemas" / "montage-learning-admission-receipt.schema.json"
    package_path = (
        ROOT
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / "montage-learning-admission-receipt.schema.json"
    )
    assert public_path.read_bytes() == package_path.read_bytes()
    schema = json.loads(public_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for value in (
        _receipt(),
        _receipt(store_written=True),
        _receipt(status=DUPLICATE),
        _receipt(admission_class=GENERIC_OBSERVATION, status=REVIEW_REQUIRED),
        _receipt(admission_class=GENERIC_OBSERVATION, status=REJECTED),
    ):
        assert validator.is_valid(value)


def test_fixed_domain_and_digest_vectors_match_design() -> None:
    assert IDEMPOTENCY_DOMAIN == (
        b"TASK058_MONTAGE_LEARNING_IDEMPOTENCY_V1" + bytes([0])
    )
    assert RECEIPT_DOMAIN == (
        b"TASK058_MONTAGE_LEARNING_ADMISSION_RECEIPT_V2" + bytes([0])
    )
    assert (
        derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=EXACT_CONTRACT_PROFILE,
            source_record_id="record-001",
            source_sha256=SOURCE,
            owner_scope_hash=SCOPE,
        )
        == IDEMPOTENCY_VECTOR
    )
    assert _receipt()["receipt_sha256"] == RECEIPT_VECTOR


def test_exact_accepted_false_is_structural_not_canonical_authority() -> None:
    parsed = parse_montage_learning_admission_receipt(_receipt())
    assert isinstance(parsed, MontageLearningAdmissionReceipt)
    assert parsed.to_dict()["canonical_store_written"] is False
    projection = parsed.to_public_projection()
    assert set(projection) == PUBLIC_FIELDS
    assert projection == {
        "receipt_id": "receipt-001",
        "admission_class": EXACT_EVIDENCE,
        "source_record_id": "record-001",
        "source_sha256": SOURCE,
        "status": ACCEPTED,
        "reason_codes": [],
        "receipt_sha256": RECEIPT_VECTOR,
        "canonical_store_commit_claimed": False,
        "receipt_structure_valid": True,
        "origin_authority_verified": False,
        "duplicate_lineage_verified": False,
        "canonical_store_commit_verified": False,
        "canonical_admission_authority_created": False,
        "receipt_minted": False,
    }


def test_exact_store_commit_claim_remains_unverified_and_body_free() -> None:
    parsed = parse_montage_learning_admission_receipt(
        _receipt(store_written=True)
    )
    projection = parsed.to_public_projection()
    assert projection["canonical_store_commit_claimed"] is True
    assert projection["canonical_store_commit_verified"] is False
    assert projection["origin_authority_verified"] is False
    forbidden = {
        "owner_scope_hash",
        "idempotency_key_sha256",
        "canonical_evidence_id",
        "canonical_evidence_sha256",
        "canonical_store_commit_sha256",
        "duplicate_of_receipt_sha256",
        "bridge_instance_id",
    }
    assert forbidden.isdisjoint(projection)


def test_exact_duplicate_is_only_structurally_referenced() -> None:
    parsed = parse_montage_learning_admission_receipt(
        _receipt(status=DUPLICATE, store_written=True)
    )
    body = parsed.to_dict()
    assert body["duplicate_of_receipt_sha256"] == OTHER_DIGEST
    projection = parsed.to_public_projection()
    assert projection["status"] == DUPLICATE
    assert projection["canonical_store_commit_claimed"] is True
    assert projection["duplicate_lineage_verified"] is False


@pytest.mark.parametrize(
    ("admission_class", "status"),
    [
        (GENERIC_OBSERVATION, ACCEPTED),
        (GENERIC_OBSERVATION, DUPLICATE),
        (EXACT_EVIDENCE, REVIEW_REQUIRED),
    ],
)
def test_lane_status_matrix_fails_closed(
    admission_class: str,
    status: str,
) -> None:
    value = _receipt(
        admission_class=admission_class,
        status=status,
    )
    _assert_rejected(value)


def test_generic_review_and_rejection_are_noncanonical() -> None:
    review = parse_montage_learning_admission_receipt(
        _receipt(
            admission_class=GENERIC_OBSERVATION,
            status=REVIEW_REQUIRED,
        )
    )
    rejected = parse_montage_learning_admission_receipt(
        _receipt(
            admission_class=GENERIC_OBSERVATION,
            status=REJECTED,
        )
    )
    assert review.to_public_projection()["reason_codes"] == [
        "REVIEW_BINDING_REQUIRED"
    ]
    assert rejected.to_public_projection()["reason_codes"] == ["HASH_MISMATCH"]
    assert review.to_public_projection()["canonical_store_commit_claimed"] is False
    assert rejected.to_public_projection()["canonical_store_commit_claimed"] is False


@pytest.mark.parametrize(
    ("status", "bad_reasons"),
    [
        (ACCEPTED, ["HASH_MISMATCH"]),
        (DUPLICATE, ["OWNER_SCOPE_MISMATCH"]),
        (REVIEW_REQUIRED, ["HASH_MISMATCH"]),
        (REJECTED, ["DUPLICATE_IDEMPOTENCY_KEY"]),
        (REJECTED, ["REVIEW_BINDING_REQUIRED"]),
    ],
)
def test_status_reason_matrix_fails_closed(
    status: str,
    bad_reasons: list[str],
) -> None:
    admission_class = (
        GENERIC_OBSERVATION if status == REVIEW_REQUIRED else EXACT_EVIDENCE
    )
    value = _receipt(admission_class=admission_class, status=status)
    value["reason_codes"] = bad_reasons
    _resign(value)
    _assert_rejected(value)


def test_rejection_reasons_must_be_sorted_unique_terminal_codes() -> None:
    valid = _receipt(status=REJECTED)
    valid["reason_codes"] = ["HASH_MISMATCH", "ID_COLLISION"]
    _resign(valid)
    assert parse_montage_learning_admission_receipt(valid).to_dict()[
        "reason_codes"
    ] == ["HASH_MISMATCH", "ID_COLLISION"]

    for bad in (
        ["ID_COLLISION", "HASH_MISMATCH"],
        ["HASH_MISMATCH", "HASH_MISMATCH"],
        ["UNKNOWN_REASON"],
    ):
        value = _receipt(status=REJECTED)
        value["reason_codes"] = bad
        _resign(value)
        _assert_rejected(value)


def test_duplicate_reference_shape_fails_closed() -> None:
    missing = _receipt(status=DUPLICATE)
    missing["duplicate_of_receipt_sha256"] = None
    _resign(missing)
    _assert_rejected(missing)

    unexpected = _receipt()
    unexpected["duplicate_of_receipt_sha256"] = OTHER_DIGEST
    _resign(unexpected)
    _assert_rejected(unexpected)


def test_canonical_store_claim_matrix_fails_closed() -> None:
    false_with_ref = _receipt()
    false_with_ref["canonical_evidence_id"] = "evidence-001"
    _resign(false_with_ref)
    _assert_rejected(false_with_ref)

    true_missing_ref = _receipt(store_written=True)
    true_missing_ref["canonical_store_commit_sha256"] = None
    _resign(true_missing_ref)
    _assert_rejected(true_missing_ref)

    generic_true = _receipt(
        admission_class=GENERIC_OBSERVATION,
        status=REVIEW_REQUIRED,
    )
    generic_true["canonical_store_written"] = True
    generic_true["canonical_evidence_id"] = "evidence-001"
    generic_true["canonical_evidence_sha256"] = OTHER_DIGEST
    generic_true["canonical_store_commit_sha256"] = OTHER_DIGEST
    _resign(generic_true)
    _assert_rejected(generic_true)


def test_lane_profile_idempotency_and_self_hash_tamper_fail_closed() -> None:
    wrong_profile = _receipt()
    wrong_profile["source_contract_profile"] = GENERIC_CONTRACT_PROFILE
    _resign(wrong_profile)
    _assert_rejected(wrong_profile)

    wrong_key = _receipt()
    wrong_key["idempotency_key_sha256"] = OTHER_DIGEST
    _resign(wrong_key)
    _assert_rejected(wrong_key)

    wrong_hash = _receipt()
    wrong_hash["receipt_sha256"] = OTHER_DIGEST
    _assert_rejected(wrong_hash)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("canonical_store_written", 0),
        ("attempt", True),
        ("attempt", 0),
        ("processed_at", "2026-08-26T00:00:00+00:00"),
        ("processed_at", "2026-02-30T00:00:00Z"),
        ("receipt_id", "../escape"),
        ("source_sha256", "sha256:" + "A" * 64),
        ("owner_scope_hash", None),
        ("admission_class", []),
        ("status", []),
    ],
)
def test_scalar_types_ids_digests_and_time_fail_closed(
    field: str,
    bad_value: object,
) -> None:
    value = _receipt()
    value[field] = bad_value
    _resign(value)
    _assert_rejected(value)


def test_missing_extra_non_json_and_unknown_values_fail_closed() -> None:
    missing = _receipt()
    missing.pop("attempt")
    _assert_rejected(missing)

    extra = _receipt()
    extra["unexpected"] = False
    _resign(extra)
    _assert_rejected(extra)

    unknown_status = _receipt()
    unknown_status["status"] = "PENDING"
    _resign(unknown_status)
    _assert_rejected(unknown_status)

    non_json = _receipt()
    non_json["reason_codes"] = {"HASH_MISMATCH"}
    _assert_rejected(non_json)


def test_custom_json_like_types_fail_without_invoking_hooks() -> None:
    hooks: list[str] = []

    class ChameleonStr(str):
        def __deepcopy__(self, memo: object) -> str:
            del memo
            hooks.append("str")
            return "changed"

    class ChameleonDict(dict[str, object]):
        def __deepcopy__(self, memo: object) -> dict[str, object]:
            del memo
            hooks.append("dict")
            return {}

    class ChameleonList(list[str]):
        def __deepcopy__(self, memo: object) -> list[str]:
            del memo
            hooks.append("list")
            return ["changed"]

    class ChameleonInt(int):
        def __deepcopy__(self, memo: object) -> int:
            del memo
            hooks.append("int")
            return 2

    custom_string = _receipt()
    custom_string["receipt_id"] = ChameleonStr("receipt-001")
    _assert_rejected(custom_string)
    with pytest.raises(MontageLearningReceiptContractError):
        compute_montage_learning_receipt_sha256(custom_string)

    custom_root = ChameleonDict(_receipt())
    _assert_rejected(custom_root)
    with pytest.raises(MontageLearningReceiptContractError):
        compute_montage_learning_receipt_sha256(custom_root)

    custom_list = _receipt(status=REJECTED)
    custom_list["reason_codes"] = ChameleonList(["HASH_MISMATCH"])
    _assert_rejected(custom_list)

    custom_integer = _receipt()
    custom_integer["attempt"] = ChameleonInt(1)
    _assert_rejected(custom_integer)

    with pytest.raises(MontageLearningReceiptContractError):
        derive_montage_learning_idempotency_key_sha256(
            source_contract_profile=ChameleonStr(EXACT_CONTRACT_PROFILE),
            source_record_id="record-001",
            source_sha256=SOURCE,
            owner_scope_hash=SCOPE,
        )
    assert hooks == []


def test_parser_is_deterministic_immutable_and_returns_fresh_copies() -> None:
    original = _receipt(status=REJECTED)
    snapshot = deepcopy(original)
    first = parse_montage_learning_admission_receipt(original)
    second = parse_montage_learning_admission_receipt(original)
    assert original == snapshot
    assert first.to_dict() == second.to_dict()
    assert first.to_public_projection() == second.to_public_projection()

    body = first.to_dict()
    body["reason_codes"].append("ID_COLLISION")
    projection = first.to_public_projection()
    projection["reason_codes"].append("ID_COLLISION")
    assert first.to_dict()["reason_codes"] == ["HASH_MISMATCH"]
    assert first.to_public_projection()["reason_codes"] == ["HASH_MISMATCH"]
    with pytest.raises(AttributeError):
        first.status = ACCEPTED  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        MontageLearningAdmissionReceipt({})


def test_p1a_has_no_io_writer_minter_or_authority_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = (
        ROOT
        / "src"
        / "ai_video_production"
        / "montage_learning_receipt_contracts.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert imports.isdisjoint(
        {"os", "pathlib", "socket", "sqlite3", "subprocess", "urllib", "requests"}
    )
    public_names = set(receipt_module.__all__)
    assert all(
        not any(part in name for part in ("build", "mint", "write", "save", "get_latest"))
        for name in public_names
    )

    def forbidden_open(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("P1A parser attempted filesystem I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    parsed = parse_montage_learning_admission_receipt(_receipt())
    assert parsed.to_public_projection()["receipt_minted"] is False
    assert (
        parsed.to_public_projection()["canonical_admission_authority_created"]
        is False
    )
