from __future__ import annotations

import pytest

from ai_video_production.desktop_shell import (
    CommandCategory,
    JobSnapshot,
    JobState,
    ShellApplicationService,
    ShellCommand,
    WorkspaceId,
)
from ai_video_production.errors import ProductError


def service() -> ShellApplicationService:
    tokens = iter(["confirm-1", "confirm-2", "confirm-3"])
    return ShellApplicationService(product_version="0.19.0", token_factory=lambda: next(tokens))


def test_snapshot_without_project_exposes_only_project_independent_commands():
    shell = service()
    snapshot = shell.snapshot().to_dict()
    assert snapshot["project"] is None
    assert "settings.read" in snapshot["available_commands"]
    assert "project.open" in snapshot["available_commands"]
    assert "render.start" not in snapshot["available_commands"]
    assert snapshot["snapshot_sha256"].startswith("sha256:")


def test_open_project_sets_media_workspace_and_context_revision():
    shell = service()
    context = shell.open_project_context(project_id="p1", display_name="Project 1")
    assert context.context_revision == 1
    assert shell.snapshot().current_workspace == WorkspaceId.MEDIA
    assert "render.start" in shell.available_commands()


def test_production_control_workspace_and_commands_are_explicitly_allowlisted():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1")
    shell.set_workspace(WorkspaceId.PRODUCTION_CONTROL)
    snapshot = shell.snapshot().to_dict()
    assert snapshot["current_workspace"] == "PRODUCTION_CONTROL"
    assert "production.snapshot" in snapshot["available_commands"]
    assert "production.candidate.register" in snapshot["available_commands"]
    assert "production.candidate.ready_for_audit" in snapshot["available_commands"]
    assert "production.lock.prepare" in snapshot["available_commands"]
    assert "production.lock.apply" in snapshot["available_commands"]
    assert "audit.snapshot" in snapshot["available_commands"]
    assert "audit.decision.prepare" in snapshot["available_commands"]
    assert "audit.decision.apply" in snapshot["available_commands"]
    assert "audit.recovery.apply" in snapshot["available_commands"]


def test_unknown_command_fails_closed():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1")
    command = ShellCommand("c1", "shell.exec_arbitrary", "p1", 1)
    with pytest.raises(ProductError) as exc:
        shell.authorize(command)
    assert exc.value.code == "ERR_SHELL_COMMAND_NOT_ALLOWED"


def test_stale_context_is_rejected_after_asset_switch():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1", selected_asset_id="a1")
    old = ShellCommand("c1", "render.qa.inspect", "p1", 1)
    shell.update_project_selection(selected_asset_id="a2")
    with pytest.raises(ProductError) as exc:
        shell.authorize(old)
    assert exc.value.code == "ERR_SHELL_CONTEXT_STALE"


def test_external_mutation_requires_exact_one_shot_confirmation():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1")
    hashes = {"assembly": "sha256:abc"}
    confirmation = shell.prepare_confirmation(
        command_type="render.start",
        expected_upstream_hashes=hashes,
        target_application="DaVinci Resolve",
        target_project="Sandbox",
        target_timeline="BAI_AUTO_X",
    )
    command = ShellCommand("c1", "render.start", "p1", 1, hashes, {}, confirmation["confirmation_id"])
    assert shell.authorize(command).category == CommandCategory.EXTERNAL_MUTATION
    with pytest.raises(ProductError) as exc:
        shell.authorize(command)
    assert exc.value.code == "ERR_SHELL_CONFIRMATION_INVALID"


def test_confirmation_expires_when_context_revision_changes():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1", selected_asset_id="a1")
    hashes = {"assembly": "sha256:abc"}
    confirmation = shell.prepare_confirmation(
        command_type="resolve.assembly.apply",
        expected_upstream_hashes=hashes,
        target_application="DaVinci Resolve",
    )
    shell.update_project_selection(selected_asset_id="a2")
    command = ShellCommand("c1", "resolve.assembly.apply", "p1", 2, hashes, {}, confirmation["confirmation_id"])
    with pytest.raises(ProductError) as exc:
        shell.authorize(command)
    assert exc.value.code == "ERR_SHELL_CONFIRMATION_INVALID"


def test_confirmation_rejects_changed_upstream_hash():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1")
    confirmation = shell.prepare_confirmation(
        command_type="render.start",
        expected_upstream_hashes={"assembly": "sha256:abc"},
        target_application="DaVinci Resolve",
    )
    command = ShellCommand(
        "c1", "render.start", "p1", 1,
        {"assembly": "sha256:def"}, {}, confirmation["confirmation_id"],
    )
    with pytest.raises(ProductError) as exc:
        shell.authorize(command)
    assert exc.value.code == "ERR_SHELL_CONFIRMATION_STALE"


def test_dispatch_wraps_executor_result_and_consumes_confirmation_before_failure():
    shell = service()
    shell.open_project_context(project_id="p1", display_name="Project 1")
    hashes = {"assembly": "sha256:abc"}
    confirmation = shell.prepare_confirmation(
        command_type="render.start",
        expected_upstream_hashes=hashes,
        target_application="DaVinci Resolve",
    )
    command = ShellCommand("c1", "render.start", "p1", 1, hashes, {}, confirmation["confirmation_id"])

    def failure(_command):
        raise ProductError("ERR_NATIVE_UNKNOWN", "unknown state", retryable=False)

    with pytest.raises(ProductError):
        shell.dispatch(command, executor=failure)
    with pytest.raises(ProductError) as exc:
        shell.authorize(command)
    assert exc.value.code == "ERR_SHELL_CONFIRMATION_INVALID"


def test_shell_command_parser_rejects_unknown_top_level_field():
    with pytest.raises(ProductError) as exc:
        ShellCommand.from_dict({
            "command_id": "c1",
            "command_type": "settings.read",
            "project_id": None,
            "expected_context_revision": None,
            "payload": {},
            "expected_upstream_hashes": {},
            "confirmation_id": None,
            "shell": "calc.exe",
        })
    assert exc.value.code == "ERR_SHELL_COMMAND_INVALID"


def test_close_guard_blocks_non_cancellable_active_job():
    shell = service()
    shell.jobs.register(JobSnapshot("j1", "c1", "RENDER", JobState.RUNNING, safe_cancel=False))
    result = shell.close_guard()
    assert result["can_close_immediately"] is False
    assert result["unsafe_job_ids"] == ["j1"]
