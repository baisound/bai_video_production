from __future__ import annotations

import copy

import pytest

from ai_video_production.final_review import FinalReviewApprovalReceipt
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def h(char: str) -> str:
    return "sha256:" + char * 64


def readiness() -> dict[str, object]:
    value = {
        "available": True,
        "state": "READY_FOR_TYPED_FINAL_REVIEW",
        "project_id": "project-1",
        "source_snapshots": {
            "production": h("2"), "audit": h("3"), "visual_handoff": h("4"),
            "timeline": h("5"), "project_manifest": h("6"),
        },
        "product_blockers": [],
        "external_blockers": [],
        "external_gates": [{
            "gate_id": gate, "state": "PASS", "receipt_sha256": h(char),
        } for gate, char in zip(
            ("AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE"),
            "789ab", strict=True,
        )],
        "final_approval_created": False,
        "export_job_created": False,
        "render_or_publish_started": False,
        "human_decision_authorized": False,
    }
    value["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: item for key, item in value.items() if key != "available"
    }))
    return value


def rehash(value: dict[str, object]) -> dict[str, object]:
    value["projection_sha256"] = sha256_bytes(canonical_json_bytes({
        key: item for key, item in value.items() if key not in {"available", "projection_sha256"}
    }))
    return value


def approval(source: dict[str, object] | None = None) -> FinalReviewApprovalReceipt:
    return FinalReviewApprovalReceipt.from_readiness(
        readiness() if source is None else source,
        receipt_id="final-review-1",
        approved_by="owner-1",
        approved_at="2026-08-17T02:00:00.000Z",
    )


def test_explicit_approval_is_deterministic_and_keeps_effects_separate() -> None:
    first = approval()
    second = approval(copy.deepcopy(readiness()))
    assert first == second
    document = first.to_dict()
    assert document["decision"] == "APPROVE"
    assert document["source_snapshot_sha256s"]["timeline"] == h("5")
    assert set(document["external_gate_receipt_sha256s"]) == {
        "AUDIO_COMPLETION", "EDIT_PERSISTENCE", "PRIVACY", "RESOURCE", "RIGHTS_LICENSE",
    }
    assert document["export_job_created"] is False
    assert document["render_or_publish_started"] is False
    assert first.final_approval_receipt_sha256 == document["final_approval_receipt_sha256"]


@pytest.mark.parametrize("state", ["BLOCKED_PRODUCT_GATES", "BLOCKED_EXTERNAL_GATES", "SOURCE_UNAVAILABLE"])
def test_non_ready_state_cannot_create_approval(state: str) -> None:
    source = readiness()
    source["state"] = state
    rehash(source)
    with pytest.raises(ValueError, match="exact ready state"):
        approval(source)


def test_missing_unknown_duplicate_and_authority_inflation_reject() -> None:
    source = readiness()
    source["external_gates"] = source["external_gates"][:-1]
    rehash(source)
    with pytest.raises(ValueError, match="incomplete"):
        approval(source)
    source = readiness()
    source["external_gates"][0]["state"] = "UNKNOWN"
    rehash(source)
    with pytest.raises(ValueError, match="must PASS"):
        approval(source)
    source = readiness()
    source["external_gates"][1]["gate_id"] = "AUDIO_COMPLETION"
    rehash(source)
    with pytest.raises(ValueError, match="not exact"):
        approval(source)
    source = readiness()
    source["human_decision_authorized"] = True
    rehash(source)
    with pytest.raises(ValueError, match="forbidden authority"):
        approval(source)


def test_source_keys_hashes_timeline_and_timestamp_are_exact() -> None:
    source = readiness()
    del source["source_snapshots"]["audit"]
    rehash(source)
    with pytest.raises(ValueError, match="key set"):
        approval(source)
    source = readiness()
    source["source_snapshots"]["timeline"] = "invented"
    rehash(source)
    with pytest.raises(ValueError, match="sha256"):
        approval(source)
    with pytest.raises(ValueError, match="canonical UTC"):
        FinalReviewApprovalReceipt.from_readiness(
            readiness(), receipt_id="final-review-1", approved_by="owner-1",
            approved_at="tomorrow",
        )


def test_projection_checksum_and_stored_receipt_roundtrip_are_exact() -> None:
    source = readiness()
    source["source_snapshots"]["audit"] = h("f")
    with pytest.raises(ValueError, match="projection checksum mismatch"):
        approval(source)

    document = approval().to_dict()
    assert FinalReviewApprovalReceipt.from_dict(copy.deepcopy(document)) == approval()
    document["approved_by"] = "other-owner"
    with pytest.raises(ValueError, match="checksum or canonical body mismatch"):
        FinalReviewApprovalReceipt.from_dict(document)
