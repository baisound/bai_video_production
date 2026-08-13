from __future__ import annotations

import pytest

from ai_video_production.desktop_editing_coordinator import DesktopEditingCoordinator
from ai_video_production.desktop_shell import ShellCommand
from ai_video_production.errors import ProductError


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
SHA_F = "sha256:" + "f" * 64
SHA_1 = "sha256:" + "1" * 64
SHA_2 = "sha256:" + "2" * 64


def coordinator():
    return DesktopEditingCoordinator.create(
        product_version="0.19.0", project_id="project-1", display_name="DbD 朝活",
        token_factory=lambda: "confirm-1",
    )


def command(c, command_type, *, confirmation_id=None, hashes=None):
    project = c.shell.project
    assert project is not None
    return ShellCommand(
        command_id="cmd-1", command_type=command_type, project_id=project.project_id,
        expected_context_revision=project.context_revision,
        expected_upstream_hashes=hashes or {}, payload={}, confirmation_id=confirmation_id,
    )


def test_stage_policy_hides_and_blocks_future_mutations_not_just_ui_buttons():
    c = coordinator()
    assert "media.choose_and_ingest" in c.snapshot().available_commands
    assert "render.start" not in c.snapshot().available_commands
    with pytest.raises(ProductError) as exc:
        c.shell.dispatch(command(c, "render.start"), executor=lambda _cmd: {"ok": True})
    assert exc.value.code == "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE"


def test_workflow_state_advances_command_surface_to_render_and_handoff():
    c = coordinator()
    c.bind_source(asset_id="asset-1", asset_sha256=SHA_A)
    c.bind_transcript(SHA_B)
    c.bind_subtitle_workspace(SHA_C)
    c.bind_cut_candidates(SHA_D)
    c.bind_edit_plan(plan_sha256=SHA_E, approved=True)
    assert "resolve.assembly.prepare" in c.snapshot().available_commands
    assert "render.start" not in c.snapshot().available_commands

    c.bind_resolve_assembly(SHA_F)
    assert "resolve.assembly.apply" in c.snapshot().available_commands
    c.mark_resolve_applied()
    assert "render.start" in c.snapshot().available_commands
    c.bind_render_qa(report_sha256=SHA_1, status="PASS")
    assert "handoff.create" in c.snapshot().available_commands
    c.bind_handoff(SHA_2)
    assert c.state.current_stage.value == "HANDOFF"
    assert c.state.next_recommended_action == "NONE"


def test_upstream_state_change_invalidates_prepared_mutation_confirmation():
    c = coordinator()
    c.bind_source(asset_id="asset-1", asset_sha256=SHA_A)
    c.bind_transcript(SHA_B)
    c.bind_cut_candidates(SHA_C)
    c.bind_edit_plan(plan_sha256=SHA_D, approved=True)
    c.bind_resolve_assembly(SHA_E)
    hashes = {"assembly": SHA_E}
    confirmation = c.shell.prepare_confirmation(
        command_type="resolve.assembly.apply", expected_upstream_hashes=hashes,
        target_application="DaVinci Resolve", target_project="sandbox", target_timeline="BAI_AUTO_TEST",
    )
    old_token = confirmation["confirmation_id"]
    c.bind_resolve_assembly(SHA_F)
    with pytest.raises(ProductError) as exc:
        c.shell.dispatch(
            command(c, "resolve.assembly.apply", confirmation_id=old_token, hashes=hashes),
            executor=lambda _cmd: {"ok": True},
        )
    assert exc.value.code in {"ERR_SHELL_CONFIRMATION_INVALID", "ERR_SHELL_CONFIRMATION_STALE"}


def test_source_change_resets_downstream_command_surface_and_context():
    c = coordinator()
    c.bind_source(asset_id="asset-1", asset_sha256=SHA_A)
    c.bind_transcript(SHA_B)
    c.bind_cut_candidates(SHA_C)
    c.bind_edit_plan(plan_sha256=SHA_D, approved=True)
    assert "resolve.assembly.prepare" in c.snapshot().available_commands
    prior_revision = c.shell.project.context_revision
    c.bind_source(asset_id="asset-2", asset_sha256=SHA_E)
    assert c.shell.project.context_revision > prior_revision
    assert "resolve.assembly.prepare" not in c.snapshot().available_commands
    assert c.state.transcript_sha256 is None
    assert c.state.edit_plan_sha256 is None
