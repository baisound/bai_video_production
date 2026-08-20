from __future__ import annotations

import copy

import pytest

from ai_video_production.final_review_gate import (
    FinalReviewExternalGateReceipt,
    FinalReviewGateId,
    FinalReviewGateState,
    validate_external_gate_receipts,
)


def h(char: str) -> str:
    return "sha256:" + char * 64


def receipt(
    gate_id: FinalReviewGateId = FinalReviewGateId.AUDIO_COMPLETION,
    *,
    state: FinalReviewGateState = FinalReviewGateState.PASS,
) -> FinalReviewExternalGateReceipt:
    owners = {
        FinalReviewGateId.AUDIO_COMPLETION: "DEVELOPER2",
        FinalReviewGateId.EDIT_PERSISTENCE: "TASK-044",
        FinalReviewGateId.PRIVACY: "TASK-016",
        FinalReviewGateId.RESOURCE: "TASK-020",
        FinalReviewGateId.RIGHTS_LICENSE: "TASK-003/027",
    }
    invalidated = state in {FinalReviewGateState.STALE, FinalReviewGateState.REVOKED}
    return FinalReviewExternalGateReceipt(
        gate_id=gate_id,
        source_authority_owner=owners[gate_id],
        project_id="project-1",
        timeline_sha256=h("1"),
        source_receipt_id=f"source-{gate_id.value.lower()}",
        source_receipt_sha256=h("2"),
        state=state,
        evaluated_at="2026-08-17T06:00:00.000Z",
        current_valid=state is FinalReviewGateState.PASS,
        invalidation_epoch=1 if invalidated else 0,
    )


def test_external_gate_receipt_roundtrips_and_projects_only_bounded_fields() -> None:
    item = receipt()
    assert FinalReviewExternalGateReceipt.from_dict(copy.deepcopy(item.to_dict())) == item
    assert item.to_readiness_dict() == {
        "gate_id": "AUDIO_COMPLETION",
        "project_id": "project-1",
        "timeline_sha256": h("1"),
        "state": "PASS",
        "receipt_sha256": item.to_dict()["receipt_sha256"],
    }
    assert item.to_dict()["authority_effect_created"] is False


def test_tamper_owner_state_and_invalidation_mismatch_fail_closed() -> None:
    document = receipt().to_dict()
    document["source_receipt_sha256"] = h("3")
    with pytest.raises(ValueError, match="checksum or canonical body mismatch"):
        FinalReviewExternalGateReceipt.from_dict(document)
    with pytest.raises(ValueError, match="closed registry"):
        FinalReviewExternalGateReceipt(
            gate_id=FinalReviewGateId.AUDIO_COMPLETION,
            source_authority_owner="TASK-036",
            project_id="project-1", timeline_sha256=h("1"),
            source_receipt_id="source-1", source_receipt_sha256=h("2"),
            state=FinalReviewGateState.PASS,
            evaluated_at="2026-08-17T06:00:00.000Z", current_valid=True,
            invalidation_epoch=0,
        )
    with pytest.raises(ValueError, match="current-valid PASS"):
        FinalReviewExternalGateReceipt(
            gate_id=FinalReviewGateId.AUDIO_COMPLETION,
            source_authority_owner="DEVELOPER2",
            project_id="project-1", timeline_sha256=h("1"),
            source_receipt_id="source-1", source_receipt_sha256=h("2"),
            state=FinalReviewGateState.UNKNOWN,
            evaluated_at="2026-08-17T06:00:00.000Z", current_valid=True,
            invalidation_epoch=0,
        )


def test_collection_is_typed_bounded_sorted_and_duplicate_free() -> None:
    rows = validate_external_gate_receipts((
        receipt(FinalReviewGateId.RESOURCE),
        receipt(FinalReviewGateId.AUDIO_COMPLETION),
    ))
    assert [row.gate_id.value for row in rows] == ["AUDIO_COMPLETION", "RESOURCE"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_external_gate_receipts((receipt(), receipt()))
    with pytest.raises(ValueError, match="typed contract"):
        validate_external_gate_receipts((receipt().to_dict(),))  # type: ignore[arg-type]
