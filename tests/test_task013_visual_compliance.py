from __future__ import annotations

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.prompt_registry import RegenerationStrategy
from ai_video_production.visual_compliance import (
    AdaptiveVisualRegenerationPlanner,
    CoordinateConvention,
    VisualCheckState,
    VisualComplianceContract,
    VisualComplianceGate,
    VisualContractCheck,
    VisualDecision,
    VisualScoreSet,
)


SHA = "sha256:" + "a" * 64


def contract():
    return VisualComplianceContract(
        "VC-SC01", 1, "SC01",
        (
            VisualContractCheck("monitor.foreground", "Monitor is foreground", True),
            VisualContractCheck("person.orientation", "Person is not back-facing", True),
            VisualContractCheck("character.identity", "Character identity matches", False),
        ),
        CoordinateConvention.EXPLICIT_MIXED,
        character_contract_ref="CHAR-1",
    )


def scores(aesthetic=0.9):
    return VisualScoreSet(0.95, 0.9, 0.9, aesthetic)


def all_pass():
    return {
        "monitor.foreground": VisualCheckState.PASS,
        "person.orientation": VisualCheckState.PASS,
        "character.identity": VisualCheckState.PASS,
    }


def test_all_contract_checks_pass_only_makes_candidate_eligible_for_human_approval():
    result = VisualComplianceGate.evaluate(
        contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
        observed_checks=all_pass(), scores=scores(), inspector_kind="VISION_JUDGE",
        inspector_model_ref="model://vision/judge",
    )
    assert result.decision is VisualDecision.ELIGIBLE_FOR_HUMAN_APPROVAL
    assert result.eligible_for_human_approval is True
    assert result.to_dict()["automatic_asset_approval"] is False
    assert result.inspection.to_dict()["candidate_path_persisted"] is False
    assert result.inspection.to_dict() == result.inspection.to_dict()


def test_critical_spatial_failure_rejects_even_with_perfect_aesthetic_score():
    observed = all_pass(); observed["monitor.foreground"] = VisualCheckState.FAIL
    result = VisualComplianceGate.evaluate(
        contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
        observed_checks=observed, scores=scores(aesthetic=1.0),
        failure_codes=("SPATIAL_RELATION_FAILURE",), inspector_kind="VISION_JUDGE",
    )
    assert result.decision is VisualDecision.REJECT
    assert result.critical_pass is False
    assert result.inspection.scores.aesthetic == 1.0
    with pytest.raises(ProductError) as exc:
        VisualComplianceGate.require_human_approval_eligible(result)
    assert exc.value.code == "ERR_VISUAL_COMPLIANCE_NOT_ELIGIBLE"


def test_unverified_required_check_requires_human_review_not_automatic_pass():
    observed = all_pass(); observed["character.identity"] = VisualCheckState.UNVERIFIED
    result = VisualComplianceGate.evaluate(
        contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
        observed_checks=observed, scores=scores(), inspector_kind="AUXILIARY_DETECTORS",
    )
    assert result.decision is VisualDecision.HUMAN_REVIEW_REQUIRED
    assert result.critical_pass is True


def test_inspection_must_report_exact_contract_check_set():
    observed = all_pass(); observed.pop("character.identity")
    with pytest.raises(ProductError) as exc:
        VisualComplianceGate.evaluate(
            contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
            observed_checks=observed, scores=scores(), inspector_kind="VISION_JUDGE",
        )
    assert exc.value.code == "ERR_VISUAL_COMPLIANCE_CHECK_SET_MISMATCH"


def test_repeated_same_structural_failure_escalates_generation_control_strategy():
    observed = all_pass(); observed["monitor.foreground"] = VisualCheckState.FAIL
    reports = []
    for candidate in ("candidate-1", "candidate-2"):
        reports.append(VisualComplianceGate.evaluate(
            contract(), candidate_id=candidate, candidate_asset_sha256=SHA,
            observed_checks=observed, scores=scores(),
            failure_codes=("SPATIAL_RELATION_FAILURE",), inspector_kind="VISION_JUDGE",
        ).inspection)
    assert AdaptiveVisualRegenerationPlanner.next_strategy(
        reports, current_strategy=RegenerationStrategy.TEXT_PROMPT,
    ) is RegenerationStrategy.PROMPT_RESTRUCTURE


def test_single_failure_does_not_overreactively_escalate_strategy():
    observed = all_pass(); observed["person.orientation"] = VisualCheckState.FAIL
    report = VisualComplianceGate.evaluate(
        contract(), candidate_id="candidate-1", candidate_asset_sha256=SHA,
        observed_checks=observed, scores=scores(),
        failure_codes=("ORIENTATION_FAILURE",), inspector_kind="VISION_JUDGE",
    ).inspection
    assert AdaptiveVisualRegenerationPlanner.next_strategy(
        (report,), current_strategy=RegenerationStrategy.LAYOUT_REFERENCE,
    ) is RegenerationStrategy.LAYOUT_REFERENCE
