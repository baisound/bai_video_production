from __future__ import annotations

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.desktop_shell_projection import EditingProjection, TimelineBlock, TranscriptRow
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task036_view_model import Task036DesktopViewModel


def projection():
    return EditingProjection(
        10_000_000,
        (TranscriptRow("cue-1", 1_000_000, 3_000_000, "こんにちは", "APPROVED", "ASR"),),
        (TimelineBlock("subtitle:cue-1", "S1", "SUBTITLE", 1_000_000, 3_000_000, "こんにちは", "APPROVED", ("cue-1",)),),
    )


def test_view_model_projects_clock_labels_and_timeline_geometry():
    shell = ShellApplicationService(product_version="0.19.0")
    shell.open_project_context(project_id="p1", display_name="DbD")
    body = Task036DesktopViewModel(shell.snapshot(), projection()).to_dict()
    assert body["source_duration_label"] == "00:00:10.000"
    assert body["transcript_rows"][0]["start_label"] == "00:00:01.000"
    block = body["timeline_tracks"]["S1"][0]
    assert block["left_percent"] == 10.0
    assert block["width_percent"] == 20.0
    assert body["ai_chat_is_primary_canvas"] is False


def test_bridge_can_expose_projection_without_file_or_process_capability():
    shell = ShellApplicationService(product_version="0.19.0")
    shell.open_project_context(project_id="p1", display_name="DbD")
    bridge = Task036ShellBridge(shell, projection=projection())
    body = bridge.view_model()
    assert body["transcript_rows"][0]["text"] == "こんにちは"
    assert not hasattr(bridge, "exec")
    assert not hasattr(bridge, "open_file")
