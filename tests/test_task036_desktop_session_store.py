from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_session_store import DesktopSessionCheckpointStore
from ai_video_production.desktop_shell import JobSnapshot, JobState, WorkspaceId
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


H = lambda ch: "sha256:" + ch * 64


def coordinator() -> DesktopEditingCoordinator:
    value = DesktopEditingCoordinator.create(
        product_version="0.19.0",
        project_id="project-1",
        display_name="DbD 朝活",
        token_factory=lambda: "token-not-persisted",
    )
    value.bind_source(asset_id="asset-1", asset_sha256=H("1"))
    value.bind_transcript(H("2"))
    value.bind_subtitle_workspace(H("3"))
    value.bind_cut_candidates(H("4"))
    value.shell.set_workspace(WorkspaceId.EDIT)
    return value


def test_checkpoint_round_trip_restores_stage_workspace_and_command_policy(tmp_path: Path):
    path = tmp_path / "desktop-session.json"
    original = coordinator()
    DesktopSessionCheckpointStore.save(path, original)
    recovered = DesktopSessionCheckpointStore.recover(path)
    assert recovered.state.to_dict() == original.state.to_dict()
    assert recovered.shell.current_workspace is WorkspaceId.EDIT
    assert recovered.shell.project.selected_asset_id == "asset-1"
    assert "edit_plan.approve" in recovered.snapshot().available_commands
    assert "resolve.assembly.apply" not in recovered.snapshot().available_commands


def test_checkpoint_never_persists_confirmation_tokens_or_host_paths(tmp_path: Path):
    value = coordinator()
    review_token = value.shell.prepare_confirmation(
        command_type="edit_plan.approve",
        expected_upstream_hashes={"draft": H("a")},
        target_application="BAI Video Production",
        target_project="project-1",
    )
    document = DesktopSessionCheckpointStore.snapshot(value)
    text = json.dumps(document, ensure_ascii=False)
    assert review_token["confirmation_id"] not in text
    assert document["confirmation_tokens_persisted"] is False
    assert document["host_paths_persisted"] is False


def test_checkpoint_refuses_active_jobs(tmp_path: Path):
    value = coordinator()
    value.shell.jobs.register(JobSnapshot("job-1", "cmd-1", "ASR", JobState.RUNNING, True))
    with pytest.raises(ProductError) as exc:
        DesktopSessionCheckpointStore.save(tmp_path / "desktop-session.json", value)
    assert exc.value.code == "ERR_SHELL_CHECKPOINT_ACTIVE_JOBS"


def test_existing_checkpoint_requires_compare_and_swap(tmp_path: Path):
    path = tmp_path / "desktop-session.json"
    value = coordinator()
    DesktopSessionCheckpointStore.save(path, value)
    with pytest.raises(ProductError) as exc:
        DesktopSessionCheckpointStore.save(path, value)
    assert exc.value.code == "ERR_SHELL_CHECKPOINT_CAS_REQUIRED"


def test_exact_checksum_allows_replacement_and_stale_writer_is_rejected(tmp_path: Path):
    path = tmp_path / "desktop-session.json"
    value = coordinator()
    DesktopSessionCheckpointStore.save(path, value)
    previous = DesktopSessionCheckpointStore.load_document(path)["checkpoint_sha256"]
    value.bind_edit_plan(plan_sha256=H("5"), approved=True)
    DesktopSessionCheckpointStore.save(path, value, expected_previous_checkpoint_sha256=previous)
    with pytest.raises(ProductError) as exc:
        DesktopSessionCheckpointStore.save(path, value, expected_previous_checkpoint_sha256=previous)
    assert exc.value.code == "ERR_SHELL_CHECKPOINT_REVISION_CONFLICT"


def test_checksum_tamper_is_detected(tmp_path: Path):
    path = tmp_path / "desktop-session.json"
    DesktopSessionCheckpointStore.save(path, coordinator())
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["workspace"] = "REVIEW"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        DesktopSessionCheckpointStore.load_document(path)
    assert exc.value.code == "ERR_SHELL_CHECKPOINT_CHECKSUM"


def test_shell_and_editing_asset_identity_mismatch_is_rejected_even_with_new_checksum(tmp_path: Path):
    path = tmp_path / "desktop-session.json"
    doc = DesktopSessionCheckpointStore.snapshot(coordinator())
    doc["project"]["selected_asset_id"] = "asset-other"
    body = {key: value for key, value in doc.items() if key != "checkpoint_sha256"}
    doc["checkpoint_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        DesktopSessionCheckpointStore.load_document(path)
    assert exc.value.code == "ERR_SHELL_CHECKPOINT_ASSET_MISMATCH"
