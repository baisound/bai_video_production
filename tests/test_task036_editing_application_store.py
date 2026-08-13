from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.desktop_editing_application import Task036EditingApplication
from ai_video_production.desktop_editing_application_store import DesktopEditingApplicationCheckpointStore
from ai_video_production.errors import ProductError


H = lambda ch: "sha256:" + ch * 64


def manifest(ch: str = "1") -> CutCandidateManifest:
    return CutCandidateManifest(
        source_asset_id="ASSET-00000000000000000000000000",
        analysis_audio_sha256=H(ch),
        analysis_sample_rate=48_000,
        source_duration_us=10_000_000,
        config_sha256=H("2"),
        transcript_manifest_sha256=H("3"),
        candidates=(
            CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 2_000_000, 90, ("SILENCE",)),
            CutCandidate("cut-000002", CutCandidateKind.FILLER, 4_000_000, 4_500_000, 75, ("FILLER",)),
        ),
        keep_blocks=(),
    )


def application(tokens=("r1", "r2", "approve")) -> Task036EditingApplication:
    values = iter(tokens)
    return Task036EditingApplication.create(
        product_version="0.19.0",
        project_id="project-1",
        display_name="DbD 朝活",
        source_asset_sha256=H("4"),
        cut_manifest=manifest(),
        token_factory=lambda: next(values),
    )


def test_checkpoint_restores_partial_human_review_without_confirmation_tokens(tmp_path: Path):
    path = tmp_path / "editing-app.json"
    app = application()
    app.select_candidate("cut-000002")
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    DesktopEditingApplicationCheckpointStore.save(path, app)
    text = path.read_text(encoding="utf-8")
    assert "r1" not in text
    recovered = DesktopEditingApplicationCheckpointStore.recover(path, cut_manifest=manifest(), token_factory=lambda: "fresh")
    review = recovered.review.snapshot()
    assert review["reviewed_count"] == 1
    assert review["unresolved_count"] == 1
    assert review["selected_candidate_id"] == "cut-000001"
    assert "edit_plan.approve" in recovered.shell.snapshot().available_commands


def test_checkpoint_restores_approved_plan_and_resolve_prepare_stage(tmp_path: Path):
    path = tmp_path / "editing-app.json"
    app = application()
    app.review_candidate(candidate_id="cut-000001", decision="CUT")
    app.review_candidate(candidate_id="cut-000002", decision="KEEP")
    prepared = app.prepare_edit_plan_approval()
    app.approve_edit_plan(
        confirmation_id=prepared["confirmation_id"],
        draft_plan_sha256=prepared["draft_plan_sha256"],
        approved_by="owner",
    )
    DesktopEditingApplicationCheckpointStore.save(path, app)
    recovered = DesktopEditingApplicationCheckpointStore.recover(path, cut_manifest=manifest(), token_factory=lambda: "fresh")
    assert recovered.review.approved_plan is not None
    assert recovered.coordinator.state.edit_plan_approved is True
    assert "resolve.assembly.prepare" in recovered.shell.snapshot().available_commands


def test_recovery_rejects_different_candidate_manifest(tmp_path: Path):
    path = tmp_path / "editing-app.json"
    DesktopEditingApplicationCheckpointStore.save(path, application())
    with pytest.raises(ProductError) as exc:
        DesktopEditingApplicationCheckpointStore.recover(path, cut_manifest=manifest("9"))
    assert exc.value.code == "ERR_SHELL_APPLICATION_CHECKPOINT_MANIFEST_MISMATCH"


def test_application_checkpoint_detects_outer_tamper(tmp_path: Path):
    path = tmp_path / "editing-app.json"
    DesktopEditingApplicationCheckpointStore.save(path, application())
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["review_checkpoint"]["playhead_us"] = 999
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        DesktopEditingApplicationCheckpointStore.load_document(path)
    assert exc.value.code == "ERR_SHELL_APPLICATION_CHECKPOINT_CHECKSUM"


def test_existing_application_checkpoint_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "editing-app.json"
    app = application()
    DesktopEditingApplicationCheckpointStore.save(path, app)
    with pytest.raises(ProductError) as exc:
        DesktopEditingApplicationCheckpointStore.save(path, app)
    assert exc.value.code == "ERR_SHELL_APPLICATION_CHECKPOINT_CAS_REQUIRED"
