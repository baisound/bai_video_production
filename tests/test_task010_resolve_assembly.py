from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError
from ai_video_production.resolve_assembly import (
    ResolveAssemblyResult,
    ResolveAssemblyService,
    ResolveAssetBindings,
)
from ai_video_production.timebase import FrameRate

ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def approved_plan():
    upstream = CutCandidateManifest(
        ASSET_ID, SHA_A, 48000, 4_000_000, SHA_B, None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    return EditPlanService.build(
        upstream,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.CUT),),
        approve=True,
        approved_by="owner",
    )


class FakeAdapter:
    def __init__(self, observed=None):
        self.observed = observed
        self.calls = 0
    def applied_hash(self, timeline_name):
        return self.observed
    def assemble(self, plan, bindings):
        self.calls += 1
        return ResolveAssemblyResult(
            plan.to_dict()["assembly_sha256"], plan.timeline_name, "APPLIED", False, "NOT_REQUESTED", "NOT_REQUESTED"
        )


def test_compile_uses_task022_mapping_and_automation_owned_timeline():
    plan = ResolveAssemblyService.compile(approved_plan(), timeline_rate=FrameRate(30))
    assert plan.timeline_name.startswith("BAI_AUTO_")
    assert len(plan.timeline_mapping.placements) == 2
    assert plan.expected_duration_frames == 90
    assert plan.to_dict()["timeline_ownership"] == "AUTOMATION_OWNED"
    assert plan.to_dict()["assembly_plan_version"] == "1.1.0"
    assert plan.to_dict()["source_media_mode"] == "LINKED_AV"
    assert plan.to_dict()["external_write_requires_explicit_authorization"] is True


def test_execute_requires_explicit_write_authorization(tmp_path: Path):
    plan = ResolveAssemblyService.compile(approved_plan(), timeline_rate=FrameRate(30))
    source = tmp_path / "source.mp4"
    source.write_bytes(b"not-used-by-fake")
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.execute(
            plan,
            adapter=FakeAdapter(),
            bindings=ResolveAssetBindings(source),
            explicit_external_write_authorization=False,
        )
    assert exc.value.code == "ERR_RESOLVE_WRITE_NOT_AUTHORIZED"


def test_idempotent_replay_returns_already_applied_without_mutation(tmp_path: Path):
    plan = ResolveAssemblyService.compile(approved_plan(), timeline_rate=FrameRate(30))
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake")
    assembly_hash = plan.to_dict()["assembly_sha256"]
    adapter = FakeAdapter(assembly_hash)
    result = ResolveAssemblyService.execute(
        plan,
        adapter=adapter,
        bindings=ResolveAssetBindings(source),
        explicit_external_write_authorization=True,
    )
    assert result.status == "ALREADY_APPLIED"
    assert result.reused_existing is True
    assert adapter.calls == 0


def test_hash_conflict_fails_closed(tmp_path: Path):
    plan = ResolveAssemblyService.compile(approved_plan(), timeline_rate=FrameRate(30))
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake")
    with pytest.raises(ProductError) as exc:
        ResolveAssemblyService.execute(
            plan,
            adapter=FakeAdapter("sha256:" + "c" * 64),
            bindings=ResolveAssetBindings(source),
            explicit_external_write_authorization=True,
        )
    assert exc.value.code == "ERR_RESOLVE_AUTOMATION_TIMELINE_HASH_CONFLICT"
