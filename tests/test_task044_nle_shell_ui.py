from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.interactive_timeline import (
    InteractiveTimeline, InteractiveTimelineClip, TimelineMediaKind, TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task036_shell_ui import HTML, Task036ShellBridge
from ai_video_production.task044_nle_shell import Task044NleShellController
from ai_video_production.timebase import FrameRate


def timeline(count: int = 3) -> InteractiveTimeline:
    tracks = (
        TimelineTrack("V1", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video", True),
        TimelineTrack("A1", 1, TimelineTrackRole.AUDIO, TimelineMediaKind.AUDIO, "Audio", True),
    )
    clips = tuple(InteractiveTimelineClip(
        f"clip-{index:05d}", "V1" if index % 2 == 0 else "A1", index, index + 1,
        "TASK-007", f"source-{index}", sha256_bytes(str(index).encode()),
        f"Clip {index}", "CURRENT", "candidate-1" if index == 0 else None,
    ) for index in range(count))
    return InteractiveTimeline("project-1", "timeline-1", FrameRate(30), count + 1, tracks, clips)


def bridge(value: InteractiveTimeline):
    service = ShellApplicationService(product_version="0.20.1")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    controller = Task044NleShellController(timeline=value)
    return Task036ShellBridge(service, nle_controller=controller), controller


def test_controller_returns_bounded_dynamic_projection_for_ten_thousand_clips() -> None:
    value = timeline(10_000)
    _bridge, controller = bridge(value)
    snapshot = controller.snapshot({"clip_offset": 0, "max_clips": 500})
    projection = snapshot["projection"]
    assert len(projection["clips"]) == 500
    assert projection["total_intersecting_clips"] == 10_000
    assert projection["next_clip_offset"] == 500
    assert {item["media_kind"] for item in projection["clips"]} == {"VIDEO", "AUDIO"}
    assert snapshot["durable_state_in_javascript"] is False


def test_selection_seek_fit_and_in_out_remain_python_owned_and_distinct() -> None:
    value = timeline()
    shell, _controller = bridge(value)
    selected = shell.interactive_timeline_select({
        "clip_id": "clip-00000", "extend": False,
        "expected_timeline_sha256": value.timeline_sha256,
    })
    assert selected["interaction"]["selected_clip_ids"] == ["clip-00000"]
    assert selected["interaction"]["playhead_frame"] == 0
    sought = shell.interactive_timeline_seek({
        "frame": 2, "expected_timeline_sha256": value.timeline_sha256,
    })
    assert sought["interaction"]["playhead_frame"] == 2
    assert sought["interaction"]["selected_clip_ids"] == ["clip-00000"]
    fitted = shell.interactive_timeline_fit({"mode": "SELECTION", "viewport_width_px": 800})
    assert fitted["projection"]["viewport"]["fit_mode"] == "SELECTION"
    marked = shell.interactive_timeline_set_in_out({"in_frame": 1, "out_frame": 3})
    assert (marked["interaction"]["in_frame"], marked["interaction"]["out_frame"]) == (1, 3)


def test_bridge_fails_closed_for_stale_or_extra_timeline_requests() -> None:
    value = timeline()
    shell, _controller = bridge(value)
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_select({
            "clip_id": "clip-00000", "extend": False,
            "expected_timeline_sha256": "sha256:" + "0" * 64,
        })
    assert exc.value.code == "ERR_NLE_SHELL_TIMELINE_STALE"
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_snapshot({"clip_offset": 0, "max_clips": 500, "exec": "whoami"})
    assert exc.value.code == "ERR_NLE_SHELL_REQUEST_INVALID"


def test_track_controls_are_python_owned_and_media_aware() -> None:
    value = timeline()
    shell, _controller = bridge(value)
    initial = shell.interactive_timeline_snapshot({})
    tracks = {item["track_id"]: item for item in initial["projection"]["tracks"]}
    assert tracks["V1"]["category"] == "VIDEO"
    assert tracks["A1"]["category"] == "AUDIO"
    assert tracks["V1"]["visible"] is True
    assert tracks["A1"]["muted"] is False
    changed = shell.interactive_timeline_update_track_state({
        "track_id": "A1", "state": "MUTED", "value": True,
        "expected_timeline_sha256": value.timeline_sha256,
    })
    changed_audio = next(item for item in changed["projection"]["tracks"] if item["track_id"] == "A1")
    assert changed_audio["muted"] is True
    assert changed["durable_state_in_javascript"] is False
    hidden = shell.interactive_timeline_update_track_state({
        "track_id": "V1", "state": "VISIBLE", "value": False,
        "expected_timeline_sha256": value.timeline_sha256,
    })
    assert next(item for item in hidden["projection"]["tracks"] if item["track_id"] == "V1")["visible"] is False
    soloed = shell.interactive_timeline_update_track_state({
        "track_id": "A1", "state": "SOLO", "value": True,
        "expected_timeline_sha256": value.timeline_sha256,
    })
    assert next(item for item in soloed["projection"]["tracks"] if item["track_id"] == "A1")["solo"] is True
    resized = shell.interactive_timeline_update_track_height({
        "height": 72, "expected_timeline_sha256": value.timeline_sha256,
    })
    assert {item["height"] for item in resized["projection"]["tracks"]} == {72}
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_update_track_height({
            "height": 93, "expected_timeline_sha256": value.timeline_sha256,
        })
    assert exc.value.code == "ERR_NLE_SHELL_REQUEST_INVALID"
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_update_track_state({
            "track_id": "V1", "state": "MUTED", "value": True,
            "expected_timeline_sha256": value.timeline_sha256,
        })
    assert exc.value.code == "ERR_NLE_SHELL_TRACK_STATE_NOT_APPLICABLE"
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_snapshot({"clip_offset": 0, "max_clips": 501})
    assert exc.value.code == "ERR_NLE_SHELL_REQUEST_INVALID"


def test_viewport_zoom_scroll_and_track_page_are_bounded_and_normalized() -> None:
    value = timeline()
    shell, _controller = bridge(value)
    model = shell.interactive_timeline_update_viewport({
        "start_frame": 1, "end_frame": 3,
        "scale_numerator": 2400, "scale_denominator": 60,
        "first_track_index": 1, "visible_track_count": 1,
    })
    viewport = model["projection"]["viewport"]
    assert viewport["visible_start_frame"] == 1
    assert viewport["visible_end_frame"] == 3
    assert viewport["pixels_per_second"] == {"numerator": 40, "denominator": 1}
    assert viewport["first_track_index"] == 1
    with pytest.raises(ProductError) as exc:
        shell.interactive_timeline_update_viewport({
            "start_frame": 0, "end_frame": value.duration_frames + 1,
            "scale_numerator": 1, "scale_denominator": 1,
            "first_track_index": 0, "visible_track_count": 1,
        })
    assert exc.value.code == "ERR_NLE_SHELL_REQUEST_INVALID"


def test_track_window_pages_a_large_topology_without_unbounded_dom() -> None:
    tracks = tuple(TimelineTrack(
        f"V{index}", index, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO,
        f"Video {index}", index == 0,
    ) for index in range(10))
    clips = tuple(InteractiveTimelineClip(
        f"clip-{index}", f"V{index}", 0, 10, "TASK-007", f"source-{index}",
        sha256_bytes(str(index).encode()), f"Clip {index}", "CURRENT",
    ) for index in range(10))
    value = InteractiveTimeline("project-1", "timeline-1", FrameRate(30), 30, tracks, clips)
    shell, _controller = bridge(value)
    first = shell.interactive_timeline_snapshot({})
    assert len(first["projection"]["tracks"]) == 8
    second = shell.interactive_timeline_update_viewport({
        "start_frame": 0, "end_frame": 30,
        "scale_numerator": 40, "scale_denominator": 1,
        "first_track_index": 8, "visible_track_count": 8,
    })
    assert [item["track_id"] for item in second["projection"]["tracks"]] == ["V8", "V9"]
    assert len(second["projection"]["clips"]) == 2


def test_unbound_nle_and_export_are_explicitly_unavailable() -> None:
    service = ShellApplicationService(product_version="0.20.1")
    shell = Task036ShellBridge(service)
    assert shell.interactive_timeline_snapshot({}) == {"available": False}
    assert shell.export_queue_snapshot({}) == {"available": False, "rows": []}


def test_bridge_lazily_binds_nle_after_editing_application_exists() -> None:
    service = ShellApplicationService(product_version="0.20.1")
    service.open_project_context(project_id="project-1", display_name="Project 1")
    application = SimpleNamespace(shell=service)
    expected = Task044NleShellController(timeline=timeline())
    calls = []
    shell = Task036ShellBridge(
        service, application=application,
        nle_controller_factory=lambda supplied: calls.append(supplied) or expected,
    )
    for internal_name in (
        "service", "projection", "review", "application", "native_dialog",
        "pre_edit_runtime", "workflow_runtime", "workflow_runtime_factory",
        "production_control", "audit_application", "planning_application",
        "generation_safety_application", "continuity_application",
        "prompt_evidence_application", "generation_queue_application",
        "generation_execution_application", "audio_workspace_application",
        "nle_controller", "nle_controller_factory",
    ):
        assert not hasattr(shell, internal_name)
    assert shell.interactive_timeline_snapshot({})["available"] is True
    assert calls == [application]
    shell.interactive_timeline_snapshot({})
    assert calls == [application]


def test_html_wires_dynamic_nle_without_javascript_durable_store() -> None:
    required = (
        'id="interactiveTimeline"', 'id="fitEntireButton"', 'id="fitSelectionButton"',
        'id="zoomInButton"', 'id="zoomOutButton"', 'id="scrollLeftButton"',
        'id="scrollRightButton"', 'id="trackUpButton"', 'id="trackDownButton"',
        'id="setInButton"', 'id="setOutButton"', "interactive_timeline_snapshot",
        "interactive_timeline_select", "interactive_timeline_seek",
        "interactive_timeline_prepare_trim", "interactive_timeline_apply_edit",
        "interactive_timeline_update_track_state",
        "interactive_timeline_update_track_height",
        "interactive_timeline_prepare_add_track",
        "interactive_timeline_prepare_remove_track",
        'data-add-track="VIDEO"', 'data-add-track="SUBTITLE"',
        'data-add-track="AUDIO"', 'data-add-track="SE"', 'data-add-track="BGM"',
        "installTrackHeightControl", "document.querySelector('.zoomrow')",
        "aria-label','Track高さ'", "trackControl('M'",
        "trackControl('S'", "track.remove_available",
        "max_clips:500", "replaceChildren", "role','button'", "clipButtons.indexOf",
    )
    for marker in required:
        assert marker in HTML
    assert "localStorage" not in HTML
    assert "sessionStorage" not in HTML
    assert "innerHTML" not in HTML
    assert "durable_state_in_javascript" in HTML


def test_html_wires_export_rows_and_accessibility_responsive_contracts() -> None:
    for marker in ('id="exportWorkspace"', "export_queue_snapshot",
                   "export_queue_prepare_dispatch", "export_queue_cancel",
                   "export_queue_reconcile", "ACCEPT_PROVEN_SUCCESS",
                   "individual_confirmation_required", "UNKNOWNは自動再実行しません",
                   'aria-live="polite"', "@media(max-width:900px)",
                   "@media(min-resolution:1.5dppx)", "button:focus-visible"):
        assert marker in HTML
    assert "blanket Execute All: NO" in HTML
    assert "host path persisted: NO" in HTML
