from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.montage_learning_admission_store import (
    MontageLearningAdmissionStore,
)
from ai_video_production.montage_learning_canonical_preflight import (
    derive_canonical_evidence_id,
    derive_human_binding_sha256,
)
from ai_video_production import (
    montage_learning_canonical_promotion_ledger_contract as module,
)
from ai_video_production.montage_learning_canonical_promotion_ledger_contract import (
    AppendDecision,
    CANONICAL_STATE,
    CONTRACT_STATE,
    EMPTY_CHAIN_SHA256,
    MontageLearningCanonicalAppendEvaluation,
    MontageLearningCanonicalLedgerCandidate,
    MontageLearningCanonicalLedgerCasExpectation,
    MontageLearningCanonicalLedgerEntryCandidate,
    evaluate_montage_learning_canonical_append,
)
from ai_video_production.montage_learning_durable_staging_readback import (
    READBACK_DOMAIN,
    MontageLearningDurableStagingReadback,
    verify_montage_learning_durable_staging_readback,
)
from ai_video_production.montage_learning_receipt_contracts import (
    derive_montage_learning_idempotency_key_sha256,
)
from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_task058_montage_learning_bridge_contracts import (
    OWNER_SCOPE_HASH,
    _exact_delivery,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / (
    "montage-learning-canonical-promotion-ledger-candidate.schema.json"
)
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
SOURCE = ROOT / "src" / "ai_video_production" / (
    "montage_learning_canonical_promotion_ledger_contract.py"
)
STAGING_STORE_ID = "task058-p1cc-staging"
CANONICAL_STORE_ID = "task058-canonical-learning"


class _LyingDict(dict):
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _StringSubclass(str):
    pass


class _EvilString(str):
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


class _ListSubclass(list):
    pass


def _stage(project_root: Path, delivery: dict[str, object]):
    source_sha = str(delivery["evidence_sha256"])
    project_root.mkdir(parents=True, exist_ok=True)
    source_record_id = str(delivery["record_id"])
    evidence_id = derive_canonical_evidence_id(source_sha)
    binding = derive_human_binding_sha256(
        project_id=str(delivery["proposal"]["project_id"]),
        source_record_id=source_record_id,
        owner_scope_hash=OWNER_SCOPE_HASH,
        proposal_sha256=str(delivery["proposal_sha256"]),
        approved_plan_sha256=str(delivery["approved_plan_sha256"]),
        evidence_sha256=source_sha,
    )
    key = derive_montage_learning_idempotency_key_sha256(
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_record_id,
        source_sha256=source_sha,
        owner_scope_hash=OWNER_SCOPE_HASH,
    )
    result = MontageLearningAdmissionStore(project_root).append(
        store_id=STAGING_STORE_ID,
        owner_scope_hash=OWNER_SCOPE_HASH,
        source_contract_profile=EXACT_CONTRACT_PROFILE,
        source_record_id=source_record_id,
        source_sha256=source_sha,
        idempotency_key_sha256=key,
        canonical_evidence_id=evidence_id,
        canonical_evidence_sha256=source_sha,
        human_binding_sha256=binding,
        committed_at="2026-08-26T00:00:01Z",
        expected_revision=0,
    )
    return verify_montage_learning_durable_staging_readback(
        delivery,
        project_root=project_root,
        store_id=STAGING_STORE_ID,
        expected_owner_scope_hash=OWNER_SCOPE_HASH,
        expected_revision=result.ledger.revision,
        expected_staging_entry_sha256=result.entry.to_dict()["entry_sha256"],
    )


def _deleted_delivery() -> dict[str, object]:
    delivery = _exact_delivery()
    delivery["record_id"] = "montage-feedback-deleted-001"
    evidence = deepcopy(delivery["human_edit_evidence"])
    assert isinstance(evidence, dict)
    evidence.update({
        "disposition": "DELETED",
        "final_target_timeline_frame": None,
        "delta_from_proposal_frames": None,
        "delta_from_review_frames": None,
        "do_not_learn": False,
    })
    unsigned = dict(evidence)
    unsigned.pop("evidence_sha256")
    evidence["evidence_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    delivery["human_edit_evidence"] = evidence
    delivery["evidence_sha256"] = evidence["evidence_sha256"]
    return delivery


def _empty(project_id: str = "project-alpha"):
    return MontageLearningCanonicalLedgerCandidate.empty(
        project_id=project_id,
        canonical_store_id=CANONICAL_STORE_ID,
        owner_scope_hash=OWNER_SCOPE_HASH,
    )


def _append(ledger, readback):
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        readback,
    )
    assert result.to_dict()["decision"] == AppendDecision.APPEND_CANDIDATE.value
    return MontageLearningCanonicalLedgerCandidate.from_dict(
        result.to_dict()["proposed_ledger"]
    )


def _resign_expectation(body: dict[str, object]) -> dict[str, object]:
    unsigned = dict(body)
    unsigned.pop("expectation_sha256")
    body["expectation_sha256"] = module._domain_hash(module._CAS_DOMAIN, unsigned)
    return body


def _forged_exact_readback(
    source: MontageLearningDurableStagingReadback, **changes: object,
) -> MontageLearningDurableStagingReadback:
    values = {
        name: getattr(source, name)
        for name in source.__annotations__
    }
    values.update(changes)
    result = object.__new__(MontageLearningDurableStagingReadback)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def test_schema_mirror_meta_schema_and_all_record_shapes(tmp_path: Path) -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty(readback.project_id)
    expectation = MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger)
    evaluation = evaluate_montage_learning_canonical_append(
        ledger, expectation, readback
    )
    proposed = evaluation.to_dict()["proposed_ledger"]
    assert isinstance(proposed, dict)
    for body in (
        expectation.to_dict(), evaluation.to_dict(), proposed, proposed["entries"][0],
    ):
        validator.validate(body)


def test_empty_and_append_candidate_are_deterministic_body_free_and_false_authority(
    tmp_path: Path,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    empty = _empty(readback.project_id)
    assert empty.to_dict() == _empty(readback.project_id).to_dict()
    assert empty.to_dict()["chain_sha256"] == EMPTY_CHAIN_SHA256
    evaluation = evaluate_montage_learning_canonical_append(
        empty,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(empty),
        readback,
    )
    assert evaluation.to_dict() == evaluate_montage_learning_canonical_append(
        empty,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(empty),
        readback,
    ).to_dict()
    body = evaluation.to_dict()
    proposed = body["proposed_ledger"]
    assert body["decision"] == "APPEND_CANDIDATE"
    assert proposed["ledger_revision"] == proposed["entry_count"] == 1
    assert proposed["entries"][0]["staging_readback_sha256"] == readback.to_dict()["readback_sha256"]
    assert proposed["entries"][0]["candidate_state"] == CONTRACT_STATE
    assert proposed["contract_state"] == CONTRACT_STATE
    assert proposed["canonical_state"] == CANONICAL_STATE
    assert proposed["consumer_revalidation_required"] is True
    assert all(value is False for value in proposed["authority_flags"].values())
    assert all(value is False for value in proposed["effect_flags"].values())
    raw = canonical_json_bytes(body)
    for forbidden in (
        b'"proposal"', b'"approved_plan"', b'"human_edit_evidence"',
        b'"placements"', b"transcript", str(tmp_path).encode(),
    ):
        assert forbidden not in raw


def test_multi_entry_chain_parses_and_preserves_negative_feedback(tmp_path: Path) -> None:
    first = _stage(tmp_path / "first", _exact_delivery())
    second = _stage(tmp_path / "second", _deleted_delivery())
    ledger = _append(_empty(first.project_id), first)
    ledger = _append(ledger, second)
    body = ledger.to_dict()
    assert body["ledger_revision"] == 2
    assert body["entries"][1]["parent_entry_sha256"] == body["entries"][0]["entry_sha256"]
    assert body["entries"][1]["prior_chain_sha256"] == body["entries"][0]["chain_sha256"]
    assert body["entries"][1]["negative_feedback_preserved"] is True
    assert MontageLearningCanonicalLedgerCandidate.from_dict(body).to_dict() == body


def test_exact_duplicate_is_not_appended(tmp_path: Path) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _append(_empty(readback.project_id), readback)
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        readback,
    ).to_dict()
    assert result["decision"] == "DUPLICATE_CANDIDATE"
    assert result["proposed_ledger"] is None
    assert result["existing_entry_sha256"] == ledger.to_dict()["latest_entry_sha256"]


@pytest.mark.parametrize(
    "field",
    [
        "ledger_key_sha256",
        "expected_ledger_revision",
        "expected_latest_entry_sha256",
        "expected_chain_sha256",
        "expected_ledger_sha256",
    ],
)
def test_every_cas_coordinate_mismatch_is_stale(
    tmp_path: Path, field: str,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _append(_empty(readback.project_id), readback)
    body = MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger).to_dict()
    if field == "expected_ledger_revision":
        body[field] = 0
        body["expected_latest_entry_sha256"] = None
    elif field == "expected_latest_entry_sha256":
        body[field] = "sha256:" + "1" * 64
    else:
        body[field] = "sha256:" + "2" * 64
    expectation = MontageLearningCanonicalLedgerCasExpectation.from_dict(
        _resign_expectation(body)
    )
    result = evaluate_montage_learning_canonical_append(
        ledger, expectation, readback
    ).to_dict()
    assert result["decision"] == "STALE_CAS_REJECTED"
    assert result["proposed_ledger"] is None


def test_scope_mismatch_is_stale_not_cross_project_append(tmp_path: Path) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty("another-project")
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        readback,
    ).to_dict()
    assert result["decision"] == "STALE_CAS_REJECTED"


@pytest.mark.parametrize(
    "changed_field",
    [
        "staging_file_identity_sha256",
        "ledger_sha256",
    ],
)
def test_same_identity_with_changed_coordinate_is_collision(
    tmp_path: Path, changed_field: str,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _append(_empty(readback.project_id), readback)
    changed = _forged_exact_readback(
        readback, **{changed_field: "sha256:" + "3" * 64}
    )
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        changed,
    ).to_dict()
    assert result["decision"] == "ID_COLLISION_REJECTED"
    assert result["proposed_ledger"] is None
    assert all(value is False for value in result["authority_flags"].values())


def test_mapping_and_nonexact_readback_are_rejected(tmp_path: Path) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty(readback.project_id)
    expectation = MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger)
    with pytest.raises(TypeError):
        evaluate_montage_learning_canonical_append(
            ledger, expectation, readback.to_dict()  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        MontageLearningDurableStagingReadback()


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("ledger", "ledger_revision", True),
        ("ledger", "entry_count", 4097),
        ("ledger", "canonical_state", "MINTED"),
        ("ledger", "consumer_revalidation_required", False),
        ("entry", "entry_revision", 2),
        ("entry", "prior_chain_sha256", "sha256:" + "4" * 64),
        ("entry", "canonical_state", "MINTED"),
        ("entry", "entry_sha256", "sha256:" + "5" * 64),
    ],
)
def test_tamper_gap_bounds_and_authority_claims_fail_closed(
    tmp_path: Path, target: str, field: str, value: object,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _append(_empty(readback.project_id), readback).to_dict()
    body = deepcopy(ledger if target == "ledger" else ledger["entries"][0])
    body[field] = value
    parser = (
        MontageLearningCanonicalLedgerCandidate.from_dict
        if target == "ledger"
        else MontageLearningCanonicalLedgerEntryCandidate.from_dict
    )
    with pytest.raises(ValueError):
        parser(body)


def test_records_are_immutable_and_roundtrip_only_as_validated_dict(tmp_path: Path) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty(readback.project_id)
    expectation = MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger)
    evaluation = evaluate_montage_learning_canonical_append(
        ledger, expectation, readback
    )
    with pytest.raises(AttributeError):
        ledger.extra = True  # type: ignore[attr-defined]
    assert MontageLearningCanonicalLedgerCasExpectation.from_dict(
        expectation.to_dict()
    ).to_dict() == expectation.to_dict()
    assert MontageLearningCanonicalAppendEvaluation.from_dict(
        evaluation.to_dict()
    ).to_dict() == evaluation.to_dict()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "9.0.0"),
        ("idempotency_key_sha256", "sha256:" + "6" * 64),
        ("canonical_evidence_id", "other-evidence-id"),
        ("human_binding_sha256", "sha256:" + "7" * 64),
    ],
)
def test_readback_identity_and_derived_coordinate_tamper_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    tampered = readback.to_dict()
    tampered[field] = value
    unsigned = dict(tampered)
    unsigned.pop("readback_sha256")
    tampered["readback_sha256"] = sha256_bytes(
        READBACK_DOMAIN + canonical_json_bytes(unsigned)
    )
    monkeypatch.setattr(
        MontageLearningDurableStagingReadback,
        "to_dict",
        lambda self: deepcopy(tampered),
    )
    ledger = _empty(readback.project_id)
    with pytest.raises(ValueError):
        evaluate_montage_learning_canonical_append(
            ledger,
            MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
            readback,
        )


def test_staging_revision_is_not_limited_by_candidate_chain_bound(tmp_path: Path) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    high_revision = _forged_exact_readback(readback, store_revision=5000)
    ledger = _empty(readback.project_id)
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        high_revision,
    ).to_dict()
    proposed = result["proposed_ledger"]
    assert proposed["entries"][0]["staging_store_revision"] == 5000
    Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(proposed)


def test_evaluation_parser_cross_binds_proposed_ledger_to_incoming_coordinates(
    tmp_path: Path,
) -> None:
    first = _stage(tmp_path / "first", _exact_delivery())
    second = _stage(tmp_path / "second", _deleted_delivery())
    ledger = _empty(first.project_id)
    expectation = MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger)
    first_body = evaluate_montage_learning_canonical_append(
        ledger, expectation, first
    ).to_dict()
    second_body = evaluate_montage_learning_canonical_append(
        ledger, expectation, second
    ).to_dict()
    first_body["proposed_ledger"] = second_body["proposed_ledger"]
    unsigned = dict(first_body)
    unsigned.pop("evaluation_sha256")
    first_body["evaluation_sha256"] = module._domain_hash(
        module._EVALUATION_DOMAIN, unsigned
    )
    with pytest.raises(ValueError, match="bind evaluation coordinates"):
        MontageLearningCanonicalAppendEvaluation.from_dict(first_body)


def test_evaluation_parser_reconstructs_exact_observed_prior_ledger(
    tmp_path: Path,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty(readback.project_id)
    body = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        readback,
    ).to_dict()
    body["observed_ledger_sha256"] = "sha256:" + "8" * 64
    unsigned = dict(body)
    unsigned.pop("evaluation_sha256")
    body["evaluation_sha256"] = module._domain_hash(
        module._EVALUATION_DOMAIN, unsigned
    )
    with pytest.raises(ValueError, match="prior state"):
        MontageLearningCanonicalAppendEvaluation.from_dict(body)


@pytest.mark.parametrize("record_name", ["entry", "ledger", "evaluation"])
@pytest.mark.parametrize("map_field", ["authority_flags", "effect_flags"])
def test_malicious_dict_subclass_cannot_bypass_false_authority_boundary(
    tmp_path: Path, record_name: str, map_field: str,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    empty = _empty(readback.project_id)
    evaluation = evaluate_montage_learning_canonical_append(
        empty,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(empty),
        readback,
    ).to_dict()
    ledger = deepcopy(evaluation["proposed_ledger"])
    assert isinstance(ledger, dict)
    parsers = {
        "entry": MontageLearningCanonicalLedgerEntryCandidate.from_dict,
        "ledger": MontageLearningCanonicalLedgerCandidate.from_dict,
        "evaluation": MontageLearningCanonicalAppendEvaluation.from_dict,
    }
    documents = {
        "entry": deepcopy(ledger["entries"][0]),
        "ledger": ledger,
        "evaluation": evaluation,
    }
    body = documents[record_name]
    flags = dict(body[map_field])
    escalated_field = (
        "canonical_store_commit_verified"
        if map_field == "authority_flags"
        else "filesystem_written"
    )
    flags[escalated_field] = True
    body[map_field] = _LyingDict(flags)
    if record_name == "entry":
        unsigned = {
            key: value for key, value in body.items()
            if key not in {"entry_sha256", "chain_sha256"}
        }
        body["entry_sha256"] = module._domain_hash(module._ENTRY_DOMAIN, unsigned)
        body["chain_sha256"] = module._domain_hash(module._CHAIN_DOMAIN, {
            "prior_chain_sha256": body["prior_chain_sha256"],
            "entry_sha256": body["entry_sha256"],
        })
    elif record_name == "ledger":
        unsigned = dict(body)
        unsigned.pop("ledger_sha256")
        body["ledger_sha256"] = module._domain_hash(module._LEDGER_DOMAIN, unsigned)
    else:
        unsigned = dict(body)
        unsigned.pop("evaluation_sha256")
        body["evaluation_sha256"] = module._domain_hash(
            module._EVALUATION_DOMAIN, unsigned
        )
    with pytest.raises(ValueError, match="exact built-in dict|boundary"):
        parsers[record_name](body)


@pytest.mark.parametrize("record_name", ["entry", "ledger", "evaluation"])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", _EvilString("9.0.0")),
        ("canonical_state", _EvilString("MINTED")),
    ],
)
def test_evil_string_cannot_spoof_identity_or_state_constants(
    tmp_path: Path, record_name: str, field: str, value: str,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    empty = _empty(readback.project_id)
    evaluation = evaluate_montage_learning_canonical_append(
        empty,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(empty),
        readback,
    ).to_dict()
    ledger = deepcopy(evaluation["proposed_ledger"])
    assert isinstance(ledger, dict)
    parsers = {
        "entry": MontageLearningCanonicalLedgerEntryCandidate.from_dict,
        "ledger": MontageLearningCanonicalLedgerCandidate.from_dict,
        "evaluation": MontageLearningCanonicalAppendEvaluation.from_dict,
    }
    body = {
        "entry": deepcopy(ledger["entries"][0]),
        "ledger": ledger,
        "evaluation": evaluation,
    }[record_name]
    body[field] = value
    if record_name == "entry":
        unsigned = {
            key: item for key, item in body.items()
            if key not in {"entry_sha256", "chain_sha256"}
        }
        body["entry_sha256"] = module._domain_hash(module._ENTRY_DOMAIN, unsigned)
        body["chain_sha256"] = module._domain_hash(module._CHAIN_DOMAIN, {
            "prior_chain_sha256": body["prior_chain_sha256"],
            "entry_sha256": body["entry_sha256"],
        })
    elif record_name == "ledger":
        unsigned = dict(body)
        unsigned.pop("ledger_sha256")
        body["ledger_sha256"] = module._domain_hash(module._LEDGER_DOMAIN, unsigned)
    else:
        unsigned = dict(body)
        unsigned.pop("evaluation_sha256")
        body["evaluation_sha256"] = module._domain_hash(
            module._EVALUATION_DOMAIN, unsigned
        )
    with pytest.raises(ValueError, match="unsupported JSON value type"):
        parsers[record_name](body)


def test_recursive_snapshot_rejects_custom_keys_and_list_subclasses(
    tmp_path: Path,
) -> None:
    ledger_body = _empty().to_dict()
    state = ledger_body.pop("canonical_state")
    ledger_body[_EvilString("canonical_state")] = state
    with pytest.raises(ValueError, match="non-string key"):
        MontageLearningCanonicalLedgerCandidate.from_dict(ledger_body)

    readback = _stage(tmp_path, _exact_delivery())
    ledger = _empty(readback.project_id)
    evaluation = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        readback,
    ).to_dict()
    evaluation["reason_codes"] = _ListSubclass(evaluation["reason_codes"])
    with pytest.raises(ValueError, match="exact built-in list"):
        MontageLearningCanonicalAppendEvaluation.from_dict(evaluation)

def test_identifier_subclasses_are_rejected() -> None:
    with pytest.raises(ValueError):
        MontageLearningCanonicalLedgerCandidate.empty(
            project_id=_StringSubclass("project-alpha"),
            canonical_store_id=CANONICAL_STORE_ID,
            owner_scope_hash=OWNER_SCOPE_HASH,
        )


def test_identifier_boundary_matches_p1cb_192_character_contract(
    tmp_path: Path,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    accepted = "a" * 192
    binding = derive_human_binding_sha256(
        project_id=accepted,
        source_record_id=readback.source_record_id,
        owner_scope_hash=readback.owner_scope_hash,
        proposal_sha256=readback.proposal_sha256,
        approved_plan_sha256=readback.approved_plan_sha256,
        evidence_sha256=readback.source_sha256,
    )
    accepted_readback = _forged_exact_readback(
        readback, project_id=accepted, human_binding_sha256=binding
    )
    ledger = _empty(accepted)
    result = evaluate_montage_learning_canonical_append(
        ledger,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
        accepted_readback,
    ).to_dict()
    assert result["decision"] == AppendDecision.APPEND_CANDIDATE.value
    Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(result["proposed_ledger"])
    with pytest.raises(ValueError):
        _empty("a" * 193)

def test_exact_4096_entry_ledger_is_accepted_and_4097_is_rejected(
    tmp_path: Path,
) -> None:
    readback = _stage(tmp_path, _exact_delivery())
    empty = _empty(readback.project_id)
    first_evaluation = evaluate_montage_learning_canonical_append(
        empty,
        MontageLearningCanonicalLedgerCasExpectation.for_ledger(empty),
        readback,
    ).to_dict()
    proposed = first_evaluation["proposed_ledger"]
    assert isinstance(proposed, dict)
    template = proposed["entries"][0]
    entries: list[dict[str, object]] = []
    parent: str | None = None
    prior_chain = EMPTY_CHAIN_SHA256
    for revision in range(1, 4097):
        entry = deepcopy(template)
        suffix = str(revision)
        entry["entry_revision"] = revision
        entry["parent_entry_sha256"] = parent
        entry["prior_chain_sha256"] = prior_chain
        entry["source_record_id"] = f"max-record-{suffix}"
        entry["source_sha256"] = sha256_bytes(f"source-{suffix}".encode())
        entry["idempotency_key_sha256"] = sha256_bytes(f"key-{suffix}".encode())
        entry["staging_entry_sha256"] = sha256_bytes(f"stage-entry-{suffix}".encode())
        entry["staging_ledger_sha256"] = sha256_bytes(f"stage-ledger-{suffix}".encode())
        entry["staging_file_identity_sha256"] = sha256_bytes(f"file-{suffix}".encode())
        entry["staging_readback_sha256"] = sha256_bytes(f"readback-{suffix}".encode())
        entry["canonical_evidence_id"] = f"max-evidence-{suffix}"
        entry["canonical_evidence_sha256"] = sha256_bytes(f"evidence-{suffix}".encode())
        entry["human_binding_sha256"] = sha256_bytes(f"human-{suffix}".encode())
        unsigned = {
            key: value for key, value in entry.items()
            if key not in {"entry_sha256", "chain_sha256"}
        }
        entry["entry_sha256"] = module._domain_hash(module._ENTRY_DOMAIN, unsigned)
        entry["chain_sha256"] = module._domain_hash(module._CHAIN_DOMAIN, {
            "prior_chain_sha256": prior_chain,
            "entry_sha256": entry["entry_sha256"],
        })
        entries.append(entry)
        parent = str(entry["entry_sha256"])
        prior_chain = str(entry["chain_sha256"])

    maximum = empty.to_dict()
    maximum["ledger_revision"] = maximum["entry_count"] = 4096
    maximum["latest_entry_sha256"] = parent
    maximum["chain_sha256"] = prior_chain
    maximum["entries"] = entries
    unsigned_ledger = dict(maximum)
    unsigned_ledger.pop("ledger_sha256")
    maximum["ledger_sha256"] = module._domain_hash(
        module._LEDGER_DOMAIN, unsigned_ledger
    )
    parsed = MontageLearningCanonicalLedgerCandidate.from_dict(maximum)
    assert parsed.to_dict()["entry_count"] == 4096

    overflow_entry = deepcopy(entries[-1])
    overflow_entry["entry_revision"] = 4097
    overflow_entry["parent_entry_sha256"] = parent
    overflow_entry["prior_chain_sha256"] = prior_chain
    overflow_entry["source_record_id"] = "max-record-4097"
    overflow_entry["idempotency_key_sha256"] = sha256_bytes(b"key-4097")
    overflow_entry["canonical_evidence_id"] = "max-evidence-4097"
    overflow_unsigned = {
        key: value for key, value in overflow_entry.items()
        if key not in {"entry_sha256", "chain_sha256"}
    }
    overflow_entry["entry_sha256"] = module._domain_hash(
        module._ENTRY_DOMAIN, overflow_unsigned
    )
    overflow_entry["chain_sha256"] = module._domain_hash(module._CHAIN_DOMAIN, {
        "prior_chain_sha256": prior_chain,
        "entry_sha256": overflow_entry["entry_sha256"],
    })
    overflow = deepcopy(maximum)
    overflow["entries"].append(overflow_entry)
    overflow["ledger_revision"] = overflow["entry_count"] = 4097
    overflow["latest_entry_sha256"] = overflow_entry["entry_sha256"]
    overflow["chain_sha256"] = overflow_entry["chain_sha256"]
    overflow_unsigned_ledger = dict(overflow)
    overflow_unsigned_ledger.pop("ledger_sha256")
    overflow["ledger_sha256"] = module._domain_hash(
        module._LEDGER_DOMAIN, overflow_unsigned_ledger
    )
    with pytest.raises(ValueError, match="outside the bounded range"):
        MontageLearningCanonicalLedgerCandidate.from_dict(overflow)

def test_source_surface_is_pure_no_io_and_has_no_writer_or_receipt_api() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots.isdisjoint({"os", "pathlib", "json", "subprocess", "socket"})
    assert imported_from.isdisjoint({"os", "pathlib", "subprocess", "socket"})
    public = set(module.__all__)
    assert not any(
        token in name.lower()
        for name in public
        for token in ("open", "load", "save", "write", "replace", "recover", "latest", "mint", "receipt")
    )
