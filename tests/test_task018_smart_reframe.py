from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import inspect
import json
from pathlib import Path

import pytest

from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.smart_reframe import (
    CropWindow,
    EvidenceValidity,
    FrameRange,
    ReframeEvidenceRef,
    ReframeEvidenceSource,
    ReframePlanState,
    ReframeSegmentProposal,
    ReframeTargetProfile,
    SourceVideoBinding,
    compile_smart_reframe_plan,
    verify_smart_reframe_plan_hash,
)
from ai_video_production.timebase import FrameRate


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "ASSET-01J00000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def source(**changes: object) -> SourceVideoBinding:
    values: dict[str, object] = {
        "asset_id": ASSET_ID,
        "asset_sha256": SHA_A,
        "width": 1920,
        "height": 1080,
        "frame_rate": FrameRate(30000, 1001),
        "total_frames": 300,
    }
    values.update(changes)
    return SourceVideoBinding(**values)  # type: ignore[arg-type]


def target(**changes: object) -> ReframeTargetProfile:
    values: dict[str, object] = {
        "profile_id": "vertical.1080x1920",
        "profile_version": "1.0.0",
        "width": 1080,
        "height": 1920,
        "frame_rate": FrameRate(30000, 1001),
    }
    values.update(changes)
    return ReframeTargetProfile(**values)  # type: ignore[arg-type]


def evidence(
    source_kind: ReframeEvidenceSource = ReframeEvidenceSource.TASK008_MULTIMODAL_SCORING,
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
    row_id: str = "candidate-000001",
) -> ReframeEvidenceRef:
    return ReframeEvidenceRef(source_kind, "1.0.0", SHA_B, row_id, SHA_C, validity)


def proposal(start: int, end: int, *refs: ReframeEvidenceRef) -> ReframeSegmentProposal:
    rows = refs or (evidence(),)
    return ReframeSegmentProposal(FrameRange(start, end), CropWindow(600, 60, 540, 960), tuple(rows))


def plan(*, refs: tuple[ReframeEvidenceRef, ...] | None = None):
    rows = refs or (evidence(),)
    return compile_smart_reframe_plan(
        source(),
        SHA_B,
        (FrameRange(0, 100), FrameRange(150, 300)),
        target(),
        (proposal(0, 50, *rows), proposal(50, 100, *rows), proposal(150, 300, *rows)),
    )


def test_plan_is_deterministic_schema_valid_review_only_and_provider_neutral():
    first = plan()
    second = plan()
    payload = first.to_dict()

    assert payload == second.to_dict()
    assert payload["state"] == "READY_FOR_HUMAN_REVIEW"
    assert payload["target"]["adapter_family"] == "PROVIDER_NEUTRAL"
    assert payload["target"]["remotion_compatibility"] == "CONTRACT_ONLY_UNPROVEN"
    assert [row["output_range_frames"] for row in payload["segments"]] == [
        {"start": 0, "end_exclusive": 50},
        {"start": 50, "end_exclusive": 100},
        {"start": 100, "end_exclusive": 250},
    ]
    assert payload["human_review_required"] is True
    for key in (
        "media_read_performed",
        "remotion_execution_performed",
        "render_authorized",
        "timeline_mutation_authorized",
        "external_write_authorized",
    ):
        assert payload[key] is False
    verify_smart_reframe_plan_hash(payload)
    validate_instance(payload, ROOT / "schemas" / "smart-reframe-plan.schema.json")


def test_public_and_packaged_schema_are_byte_identical_and_meta_valid():
    public = (ROOT / "schemas" / "smart-reframe-plan.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "smart-reframe-plan.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(plan().to_dict(), json.loads(public))


def test_source_and_profile_bind_exact_geometry_rate_asset_and_digest():
    payload = plan().to_dict()
    assert payload["source"]["asset_id"] == ASSET_ID
    assert payload["source"]["asset_sha256"] == SHA_A
    assert payload["source"]["pixel_aspect_ratio"] == {"numerator": 1, "denominator": 1}
    assert payload["source"]["frame_rate"] == {"numerator": 30000, "denominator": 1001}
    assert payload["source_edit_plan_sha256"] == SHA_B
    assert payload["target"]["profile_sha256"].startswith("sha256:")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"asset_id": "asset.mov"}, "invalid ASSET"),
        ({"asset_sha256": "a" * 64}, "asset_sha256"),
        ({"width": True}, "width"),
        ({"height": 32769}, "height"),
        ({"frame_rate": "30000/1001"}, "FrameRate"),
        ({"total_frames": 0}, "total_frames"),
    ],
)
def test_source_binding_rejects_weak_or_unbounded_values(changes, message):
    with pytest.raises(ValueError, match=message):
        source(**changes)


def test_target_requires_portrait_semver_and_exact_source_rate():
    with pytest.raises(ValueError, match="portrait"):
        target(width=1920, height=1080)
    with pytest.raises(ValueError, match="semantic"):
        target(profile_version="latest")
    with pytest.raises(ValueError, match="exactly equal"):
        compile_smart_reframe_plan(
            source(), SHA_B, (FrameRange(0, 300),), target(frame_rate=FrameRate(24, 1)), (proposal(0, 300),)
        )


def test_crop_must_be_contained_and_exact_target_aspect():
    bad_bounds = ReframeSegmentProposal(FrameRange(0, 300), CropWindow(1500, 60, 540, 960), (evidence(),))
    with pytest.raises(ValueError, match="contained"):
        compile_smart_reframe_plan(source(), SHA_B, (FrameRange(0, 300),), target(), (bad_bounds,))

    bad_aspect = ReframeSegmentProposal(FrameRange(0, 300), CropWindow(0, 0, 541, 960), (evidence(),))
    with pytest.raises(ValueError, match="aspect ratio"):
        compile_smart_reframe_plan(source(), SHA_B, (FrameRange(0, 300),), target(), (bad_aspect,))


@pytest.mark.parametrize(
    "keep_ranges",
    [
        (FrameRange(0, 200), FrameRange(100, 300)),
        (FrameRange(0, 301),),
    ],
)
def test_keep_ranges_must_be_ordered_nonoverlapping_and_source_bounded(keep_ranges):
    with pytest.raises(ValueError):
        compile_smart_reframe_plan(source(), SHA_B, keep_ranges, target(), (proposal(0, 300),))


@pytest.mark.parametrize(
    "proposals",
    [
        (proposal(0, 99), proposal(150, 300)),
        (proposal(0, 100), proposal(99, 100), proposal(150, 300)),
        (proposal(0, 100), proposal(100, 150), proposal(150, 300)),
        (proposal(0, 100), proposal(150, 299)),
    ],
)
def test_proposals_must_exactly_partition_keep_ranges(proposals):
    with pytest.raises(ValueError, match="partition|cover|outside"):
        compile_smart_reframe_plan(
            source(), SHA_B, (FrameRange(0, 100), FrameRange(150, 300)), target(), proposals
        )


def test_unknown_and_stale_evidence_are_distinct_and_cannot_be_ready():
    unknown = plan(refs=(evidence(validity=EvidenceValidity.UNKNOWN),))
    stale = plan(refs=(evidence(validity=EvidenceValidity.STALE),))
    revoked = plan(refs=(evidence(validity=EvidenceValidity.REVOKED),))
    assert unknown.state is ReframePlanState.UNKNOWN_EVIDENCE
    assert stale.state is ReframePlanState.STALE_OR_REVOKED_EVIDENCE
    assert revoked.state is ReframePlanState.STALE_OR_REVOKED_EVIDENCE
    assert unknown.to_dict()["render_authorized"] is False


def test_evidence_requires_closed_enums_exact_receipts_and_canonical_order():
    with pytest.raises(ValueError, match="ReframeEvidenceSource"):
        replace(evidence(), source="TASK008_MULTIMODAL_SCORING")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="EvidenceValidity"):
        replace(evidence(), validity="CURRENT_VALID")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="manifest_sha256"):
        replace(evidence(), manifest_sha256="digest-only")
    first = evidence(ReframeEvidenceSource.HUMAN_REVIEW, row_id="review-2")
    second = evidence(ReframeEvidenceSource.TASK005_SCENE_BOUNDARY, row_id="scene-1")
    with pytest.raises(ValueError, match="canonically sorted"):
        ReframeSegmentProposal(FrameRange(0, 1), CropWindow(0, 0, 540, 960), (second, first))
    with pytest.raises(ValueError, match="unique"):
        ReframeSegmentProposal(FrameRange(0, 1), CropWindow(0, 0, 540, 960), (second, second))


def test_rows_and_contracts_are_immutable():
    compiled = plan()
    with pytest.raises(FrozenInstanceError):
        compiled.state = ReframePlanState.UNKNOWN_EVIDENCE  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        compiled.segments[0].crop.x = 1  # type: ignore[misc]


def test_manifest_hash_rejects_tampering_and_digest_only_substitution():
    payload = plan().to_dict()
    payload["segments"][0]["crop"]["x"] = 601
    with pytest.raises(ValueError, match="does not match"):
        verify_smart_reframe_plan_hash(payload)
    with pytest.raises(ValueError, match="target"):
        verify_smart_reframe_plan_hash({"plan_sha256": SHA_A})


def test_outer_rehash_cannot_hide_tampered_target_profile_digest():
    payload = plan().to_dict()
    payload["target"]["profile_sha256"] = SHA_A
    body = dict(payload)
    body.pop("plan_sha256")
    payload["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="target.profile_sha256"):
        verify_smart_reframe_plan_hash(payload)


def test_caps_reject_max_plus_one_before_constituent_laundering():
    one = FrameRange(0, 1)
    with pytest.raises(ValueError, match="1-100000"):
        compile_smart_reframe_plan(source(), SHA_B, (one,) * 100_001, target(), (proposal(0, 1),))
    with pytest.raises(ValueError, match="1-100000"):
        compile_smart_reframe_plan(source(), SHA_B, (one,), target(), (proposal(0, 1),) * 100_001)
    with pytest.raises(ValueError, match="1-32"):
        ReframeSegmentProposal(one, CropWindow(0, 0, 540, 960), (evidence(),) * 33)


def test_public_compile_surface_accepts_no_effect_capability():
    assert set(inspect.signature(compile_smart_reframe_plan).parameters) == {
        "source",
        "source_edit_plan_sha256",
        "source_keep_ranges",
        "target",
        "proposals",
    }
    source_text = (ROOT / "src" / "ai_video_production" / "smart_reframe.py").read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"subprocess", "requests", "urllib", "httpx", "ffmpeg", "cv2", "pathlib"})
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"open", "exec", "eval", "compile"})
