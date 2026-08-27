from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production import (
    montage_learning_external_monotonic_anchor_contract as module,
)
from ai_video_production.montage_learning_canonical_promotion_ledger_contract import (
    MontageLearningCanonicalLedgerCandidate,
)
from ai_video_production.montage_learning_external_monotonic_anchor_contract import (
    ANCHOR_STATE,
    CONTRACT_STATE,
    AnchorDecision,
    MontageLearningExternalMonotonicAnchorCandidate,
    MontageLearningExternalMonotonicAnchorEvaluation,
    MontageLearningExternalMonotonicAnchorExpectation,
    evaluate_montage_learning_external_monotonic_anchor,
)
from test_task058_montage_learning_bridge_contracts import _exact_delivery
from test_task058_montage_learning_canonical_promotion_ledger_contract import (
    _append,
    _deleted_delivery,
    _empty,
    _stage,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / (
    "montage-learning-external-monotonic-anchor-candidate.schema.json"
)
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
SOURCE = ROOT / "src" / "ai_video_production" / (
    "montage_learning_external_monotonic_anchor_contract.py"
)


class _DictSubclass(dict):
    pass


class _StringSubclass(str):
    pass


class _EvilInt(int):
    def __lt__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return True


def _ledgers(tmp_path: Path):
    first_readback = _stage(tmp_path / "first", _exact_delivery())
    second_readback = _stage(tmp_path / "second", _deleted_delivery())
    empty = _empty(first_readback.project_id)
    first = _append(empty, first_readback)
    second = _append(first, second_readback)
    fork_first = _append(empty, second_readback)
    fork_second = _append(fork_first, first_readback)
    return empty, first, second, fork_first, fork_second


def _bootstrap(ledger: MontageLearningCanonicalLedgerCandidate):
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(
        ledger
    )
    evaluation = evaluate_montage_learning_external_monotonic_anchor(
        None, expectation, None, ledger
    )
    body = evaluation.to_dict()
    assert body["decision"] == AnchorDecision.BOOTSTRAP_CANDIDATE.value
    return (
        MontageLearningExternalMonotonicAnchorCandidate.from_dict(
            body["proposed_anchor"]
        ),
        evaluation,
    )


def _resign_anchor(body: dict[str, object]) -> dict[str, object]:
    unsigned = dict(body)
    unsigned.pop("anchor_sha256")
    body["anchor_sha256"] = module._domain_hash(module._ANCHOR_DOMAIN, unsigned)
    return body


def _resign_expectation(body: dict[str, object]) -> dict[str, object]:
    unsigned = dict(body)
    unsigned.pop("expectation_sha256")
    body["expectation_sha256"] = module._domain_hash(
        module._EXPECTATION_DOMAIN, unsigned
    )
    return body


def _resign_evaluation(body: dict[str, object]) -> dict[str, object]:
    unsigned = dict(body)
    unsigned.pop("evaluation_sha256")
    body["evaluation_sha256"] = module._domain_hash(
        module._EVALUATION_DOMAIN, unsigned
    )
    return body


def test_exact_snapshot_budget_covers_two_max_revision_chain_proofs() -> None:
    digest = "sha256:" + "0" * 64
    snapshot = module._snapshot_exact_json(
        {"observed": [digest] * 4096, "proposed": [digest] * 4096},
        "max_chain_proofs",
    )
    assert len(snapshot["observed"]) == 4096
    assert len(snapshot["proposed"]) == 4096


def test_schema_mirror_meta_schema_and_all_record_shapes(tmp_path: Path) -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, bootstrap = _bootstrap(first)
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
    advance = evaluate_montage_learning_external_monotonic_anchor(
        anchor, expectation, first, second
    )
    for body in (
        anchor.to_dict(), expectation.to_dict(), bootstrap.to_dict(), advance.to_dict(),
        advance.to_dict()["proposed_anchor"],
    ):
        validator.validate(body)


def test_bootstrap_is_deterministic_body_free_and_non_authoritative(
    tmp_path: Path,
) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, evaluation = _bootstrap(first)
    anchor_body = anchor.to_dict()
    second_anchor, second_evaluation = _bootstrap(first)
    assert anchor_body == second_anchor.to_dict()
    assert evaluation.to_dict() == second_evaluation.to_dict()
    assert anchor_body["anchor_revision"] == 1
    assert anchor_body["anchored_ledger_revision"] == 1
    assert anchor_body["previous_anchor_sha256"] is None
    assert anchor_body["contract_state"] == CONTRACT_STATE
    assert anchor_body["anchor_state"] == ANCHOR_STATE
    assert anchor_body["consumer_revalidation_required"] is True
    assert not any(anchor_body["authority_flags"].values())
    assert not any(anchor_body["effect_flags"].values())
    serialized = json.dumps(anchor_body, sort_keys=True)
    for forbidden in (
        "proposal_body", "approved_plan_body", "human_edit_body", "media_path",
        "actor_id", "account_id", "receipt_body", "secret", "private_key",
    ):
        assert forbidden not in serialized


def test_advance_requires_exact_prefix_and_chains_anchor(tmp_path: Path) -> None:
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
    result = evaluate_montage_learning_external_monotonic_anchor(
        anchor, expectation, first, second
    ).to_dict()
    assert result["decision"] == AnchorDecision.ADVANCE_CANDIDATE.value
    proposed = MontageLearningExternalMonotonicAnchorCandidate.from_dict(
        result["proposed_anchor"]
    ).to_dict()
    assert proposed["anchor_revision"] == 2
    assert proposed["previous_anchor_sha256"] == anchor.to_dict()["anchor_sha256"]
    assert proposed["anchored_ledger_revision"] == 2
    assert proposed["anchored_ledger_sha256"] == second.to_dict()["ledger_sha256"]


def test_unchanged_candidate_does_not_propose_anchor(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    result = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        first,
    ).to_dict()
    assert result["decision"] == AnchorDecision.UNCHANGED_CANDIDATE.value
    assert result["proposed_anchor"] is None


def test_rollback_is_rejected(tmp_path: Path) -> None:
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(second)
    result = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        second,
        first,
    ).to_dict()
    assert result["decision"] == AnchorDecision.ROLLBACK_REJECTED.value
    assert result["proposed_anchor"] is None


@pytest.mark.parametrize("use_higher_fork", [False, True])
def test_same_revision_and_higher_revision_forks_are_rejected(
    tmp_path: Path, use_higher_fork: bool,
) -> None:
    _, first, _, fork_first, fork_second = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    proposed = fork_second if use_higher_fork else fork_first
    result = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        proposed,
    ).to_dict()
    assert result["decision"] == AnchorDecision.FORK_REJECTED.value
    assert result["proposed_anchor"] is None


def test_scope_mismatch_is_rejected_before_bootstrap(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    foreign = MontageLearningCanonicalLedgerCandidate.empty(
        project_id="project-foreign",
        canonical_store_id="task058-canonical-learning",
        owner_scope_hash=first.to_dict()["owner_scope_hash"],
    )
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(
        foreign
    )
    result = evaluate_montage_learning_external_monotonic_anchor(
        None, expectation, None, first
    ).to_dict()
    assert result["decision"] == AnchorDecision.SCOPE_MISMATCH_REJECTED.value
    assert result["proposed_anchor"] is None


def test_stale_expectation_is_rejected(tmp_path: Path) -> None:
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    stale = MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(first)
    result = evaluate_montage_learning_external_monotonic_anchor(
        anchor, stale, first, second
    ).to_dict()
    assert result["decision"] == AnchorDecision.STALE_ANCHOR_REJECTED.value
    assert result["proposed_anchor"] is None


def test_anchor_must_bind_exact_current_ledger(tmp_path: Path) -> None:
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    with pytest.raises(ValueError, match="does not bind"):
        evaluate_montage_learning_external_monotonic_anchor(
            anchor,
            MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
            second,
            second,
        )


def test_current_anchor_and_ledger_are_an_atomic_pair(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
    with pytest.raises(ValueError, match="supplied together"):
        evaluate_montage_learning_external_monotonic_anchor(
            anchor, expectation, None, first
        )
    with pytest.raises(ValueError, match="supplied together"):
        evaluate_montage_learning_external_monotonic_anchor(
            None, expectation, first, first
        )


def test_empty_ledger_cannot_be_anchored() -> None:
    empty = _empty()
    with pytest.raises(ValueError, match="non-empty"):
        evaluate_montage_learning_external_monotonic_anchor(
            None,
            MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(empty),
            None,
            empty,
        )


def test_expectation_absent_sentinel_requires_all_nullable_coordinates(
    tmp_path: Path,
) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    body = MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(
        first
    ).to_dict()
    body["expected_anchored_chain_sha256"] = first.to_dict()["chain_sha256"]
    _resign_expectation(body)
    with pytest.raises(ValueError, match="ledger sentinel"):
        MontageLearningExternalMonotonicAnchorExpectation.from_dict(body)


def test_existing_expectation_and_evaluation_reject_partial_null_coordinates(
    tmp_path: Path,
) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, evaluation = _bootstrap(first)
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(
        anchor
    ).to_dict()
    expectation["expected_anchored_chain_sha256"] = None
    _resign_expectation(expectation)
    with pytest.raises(ValueError, match="ledger sentinel"):
        MontageLearningExternalMonotonicAnchorExpectation.from_dict(expectation)
    evaluation_body = evaluation.to_dict()
    evaluation_body["observed_anchor_revision"] = 1
    evaluation_body["observed_anchor_sha256"] = anchor.to_dict()["anchor_sha256"]
    evaluation_body["observed_ledger_revision"] = 1
    evaluation_body["observed_latest_entry_sha256"] = None
    evaluation_body["observed_chain_sha256"] = first.to_dict()["chain_sha256"]
    evaluation_body["observed_ledger_sha256"] = first.to_dict()["ledger_sha256"]
    evaluation_body["existing_anchor_sha256"] = anchor.to_dict()["anchor_sha256"]
    _resign_evaluation(evaluation_body)
    with pytest.raises(ValueError, match="ledger sentinel"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(evaluation_body)


def test_evaluation_decision_revision_semantics_fail_closed(tmp_path: Path) -> None:
    _, first, second, _, fork_second = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    advance = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        second,
    ).to_dict()
    advance["decision"] = AnchorDecision.ROLLBACK_REJECTED.value
    advance["reason_codes"] = [AnchorDecision.ROLLBACK_REJECTED.value]
    advance["proposed_anchor"] = None
    _resign_evaluation(advance)
    with pytest.raises(ValueError, match="not canonical"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(advance)

    advance_as_fork = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        second,
    ).to_dict()
    advance_as_fork["decision"] = AnchorDecision.FORK_REJECTED.value
    advance_as_fork["reason_codes"] = [AnchorDecision.FORK_REJECTED.value]
    advance_as_fork["proposed_anchor"] = None
    _resign_evaluation(advance_as_fork)
    with pytest.raises(ValueError, match="not canonical"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(advance_as_fork)

    fork_as_advance = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        fork_second,
    ).to_dict()
    fork_as_advance["decision"] = AnchorDecision.ADVANCE_CANDIDATE.value
    fork_as_advance["reason_codes"] = [AnchorDecision.ADVANCE_CANDIDATE.value]
    fork_as_advance["proposed_anchor"] = module._anchor_for_ledger(
        fork_second.to_dict(),
        anchor_revision=2,
        previous_anchor_sha256=anchor.to_dict()["anchor_sha256"],
    )
    _resign_evaluation(fork_as_advance)
    with pytest.raises(ValueError, match="not canonical"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(fork_as_advance)

    unchanged = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        first,
    ).to_dict()
    unchanged["decision"] = AnchorDecision.FORK_REJECTED.value
    unchanged["reason_codes"] = [AnchorDecision.FORK_REJECTED.value]
    unchanged["proposed_ledger_sha256"] = "sha256:" + "f" * 64
    _resign_evaluation(unchanged)
    with pytest.raises(ValueError, match="digest/entry proof"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(unchanged)

    same_revision_fork = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        _ledgers(tmp_path / "same-revision-fork")[3],
    ).to_dict()
    same_revision_fork["decision"] = AnchorDecision.UNCHANGED_CANDIDATE.value
    same_revision_fork["reason_codes"] = [AnchorDecision.UNCHANGED_CANDIDATE.value]
    same_revision_fork["proposed_ledger_sha256"] = (
        same_revision_fork["observed_ledger_sha256"]
    )
    _resign_evaluation(same_revision_fork)
    with pytest.raises(ValueError, match="digest/entry proof"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(
            same_revision_fork
        )


def test_serialized_stale_and_scope_decisions_cannot_be_relabelled(
    tmp_path: Path,
) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    matching = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
    unchanged = evaluate_montage_learning_external_monotonic_anchor(
        anchor, matching, first, first
    ).to_dict()
    for replacement in (
        AnchorDecision.STALE_ANCHOR_REJECTED,
        AnchorDecision.SCOPE_MISMATCH_REJECTED,
    ):
        changed = deepcopy(unchanged)
        changed["decision"] = replacement.value
        changed["reason_codes"] = [replacement.value]
        _resign_evaluation(changed)
        with pytest.raises(ValueError):
            MontageLearningExternalMonotonicAnchorEvaluation.from_dict(changed)

    stale = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(first),
        first,
        first,
    ).to_dict()
    stale["decision"] = AnchorDecision.UNCHANGED_CANDIDATE.value
    stale["reason_codes"] = [AnchorDecision.UNCHANGED_CANDIDATE.value]
    _resign_evaluation(stale)
    with pytest.raises(ValueError, match="not canonical"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(stale)

    foreign = MontageLearningCanonicalLedgerCandidate.empty(
        project_id="project-foreign",
        canonical_store_id="task058-canonical-learning",
        owner_scope_hash=first.to_dict()["owner_scope_hash"],
    )
    scope = evaluate_montage_learning_external_monotonic_anchor(
        None,
        MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(foreign),
        None,
        first,
    ).to_dict()
    scope["decision"] = AnchorDecision.STALE_ANCHOR_REJECTED.value
    scope["reason_codes"] = [AnchorDecision.STALE_ANCHOR_REJECTED.value]
    _resign_evaluation(scope)
    with pytest.raises(ValueError, match="not canonical"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(scope)

    scope_tamper = evaluate_montage_learning_external_monotonic_anchor(
        anchor, matching, first, first
    ).to_dict()
    scope_tamper["proposed_scope"]["project_id"] = "project-tampered"
    _resign_evaluation(scope_tamper)
    with pytest.raises(ValueError, match="scope digest"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(scope_tamper)


def test_anchor_revision_predecessor_and_bounds_fail_closed(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    for field, value in (
        ("anchor_revision", 4097),
        ("anchor_revision", _EvilInt(1)),
        ("anchored_ledger_revision", 0),
        ("previous_anchor_sha256", "sha256:" + "1" * 64),
    ):
        body = anchor.to_dict()
        body[field] = value
        _resign_anchor(body)
        with pytest.raises(ValueError):
            MontageLearningExternalMonotonicAnchorCandidate.from_dict(body)


def test_exact_types_and_custom_mapping_hooks_are_rejected(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, evaluation = _bootstrap(first)
    expectation = MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
    for factory, body in (
        (MontageLearningExternalMonotonicAnchorCandidate.from_dict, anchor.to_dict()),
        (MontageLearningExternalMonotonicAnchorExpectation.from_dict, expectation.to_dict()),
        (MontageLearningExternalMonotonicAnchorEvaluation.from_dict, evaluation.to_dict()),
    ):
        with pytest.raises(ValueError, match="exact built-in dict"):
            factory(_DictSubclass(body))
    with pytest.raises(TypeError, match="exact validated"):
        evaluate_montage_learning_external_monotonic_anchor(
            anchor.to_dict(), expectation, first, first  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="exact validated"):
        evaluate_montage_learning_external_monotonic_anchor(
            anchor, expectation, first.to_dict(), first  # type: ignore[arg-type]
        )


def test_scalar_subclasses_and_authority_tamper_fail_closed(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, evaluation = _bootstrap(first)
    anchor_body = anchor.to_dict()
    anchor_body["project_id"] = _StringSubclass(anchor_body["project_id"])
    _resign_anchor(anchor_body)
    with pytest.raises(ValueError, match="project_id"):
        MontageLearningExternalMonotonicAnchorCandidate.from_dict(anchor_body)
    evaluation_body = evaluation.to_dict()
    evaluation_body["authority_flags"]["external_monotonic_anchor_verified"] = True
    _resign_evaluation(evaluation_body)
    with pytest.raises(ValueError, match="authority boundary"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(evaluation_body)


def test_evaluation_parser_cross_binds_proposed_anchor(tmp_path: Path) -> None:
    _, first, second, _, _ = _ledgers(tmp_path)
    anchor, _ = _bootstrap(first)
    evaluation = evaluate_montage_learning_external_monotonic_anchor(
        anchor,
        MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor),
        first,
        second,
    ).to_dict()
    evaluation["proposed_anchor"]["anchored_chain_sha256"] = first.to_dict()[
        "chain_sha256"
    ]
    _resign_anchor(evaluation["proposed_anchor"])
    _resign_evaluation(evaluation)
    with pytest.raises(ValueError, match="bind evaluation coordinates"):
        MontageLearningExternalMonotonicAnchorEvaluation.from_dict(evaluation)


def test_records_are_immutable_and_return_detached_dicts(tmp_path: Path) -> None:
    _, first, _, _, _ = _ledgers(tmp_path)
    anchor, evaluation = _bootstrap(first)
    with pytest.raises(AttributeError, match="immutable"):
        anchor.anchor_revision = 2  # type: ignore[attr-defined]
    detached = evaluation.to_dict()
    detached["authority_flags"]["external_monotonic_anchor_verified"] = True
    assert not any(evaluation.to_dict()["authority_flags"].values())


def test_source_surface_is_pure_no_io_and_has_no_writer_or_receipt_api() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint({
        "os", "pathlib", "sqlite3", "subprocess", "socket", "requests", "urllib"
    })
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_names.isdisjoint({
        "open", "write", "replace", "rename", "unlink", "remove", "mkdir",
        "mint_receipt", "get_latest",
    })
    public = set(module.__all__)
    assert not any(
        token in name.lower()
        for name in public
        for token in ("write", "save", "persist", "recover", "mint", "receipt")
    )
