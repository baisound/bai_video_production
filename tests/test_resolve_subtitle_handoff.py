from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.resolve_subtitle_handoff import ResolveSubtitleHandoffService
from ai_video_production.subtitle_workspace import (
    SubtitleOrigin,
    SubtitleReviewState,
    SubtitleWorkspace,
    WorkspaceCue,
)
from ai_video_production.timebase import FrameRate


def workspace(*, approved: bool = True) -> SubtitleWorkspace:
    state = SubtitleReviewState.APPROVED if approved else SubtitleReviewState.NEEDS_REVIEW
    return SubtitleWorkspace(
        "workspace-1",
        7,
        (
            WorkspaceCue("cue-1", 0, 1000, "one", "one", SubtitleOrigin.HUMAN, state),
            WorkspaceCue("cue-2", 1500, 2500, "two", "two", SubtitleOrigin.HUMAN, state),
        ),
    )


def test_handoff_is_deterministic_and_task010_owns_execution() -> None:
    first = ResolveSubtitleHandoffService.build(
        workspace(),
        timeline_rate=FrameRate(30000, 1001),
        timeline_origin_frame=100,
        track_index=2,
    )
    second = ResolveSubtitleHandoffService.build(
        workspace(),
        timeline_rate=FrameRate(30000, 1001),
        timeline_origin_frame=100,
        track_index=2,
    )
    assert first.to_dict() == second.to_dict()
    payload = first.to_dict()
    assert payload["handoff_owner"] == "TASK-006"
    assert payload["execution_owner"] == "TASK-010"
    assert payload["timeline_origin_frame"] == 100
    assert payload["placements"][0]["record_range_frames"]["start"] == 100
    assert payload["contains_private_subtitle_text"] is True
    assert payload["ready_for_resolve_write"] is True
    assert payload["plan_sha256"].startswith("sha256:")


def test_handoff_requires_all_cues_approved_for_ready_signal() -> None:
    plan = ResolveSubtitleHandoffService.build(
        workspace(approved=False), timeline_rate=FrameRate(30)
    )
    assert plan.ready_for_resolve_write is False


def test_handoff_fails_closed_when_ms_cues_collapse_into_same_frame() -> None:
    collision = SubtitleWorkspace(
        "workspace-2",
        1,
        (
            WorkspaceCue("cue-1", 0, 1, "a", "a", SubtitleOrigin.HUMAN, SubtitleReviewState.APPROVED),
            WorkspaceCue("cue-2", 1, 2, "b", "b", SubtitleOrigin.HUMAN, SubtitleReviewState.APPROVED),
        ),
    )
    with pytest.raises(ValueError, match="non-overlapping timeline frames"):
        ResolveSubtitleHandoffService.build(collision, timeline_rate=FrameRate(30))


def test_handoff_write_is_atomic_and_contains_canonical_hash(tmp_path: Path) -> None:
    target = tmp_path / "resolve-subtitle-placement.json"
    plan, write = ResolveSubtitleHandoffService.write(
        target, workspace(), timeline_rate=FrameRate(24)
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert write.path == target
    assert payload["plan_sha256"] == plan.to_dict()["plan_sha256"]
    assert payload["workspace_revision"] == 7
    assert len(payload["placements"]) == 2


def test_workspace_change_changes_source_and_plan_hash() -> None:
    original = workspace()
    changed = original.update("cue-1", start_ms=0, end_ms=1000, text="changed", approved=True)
    first = ResolveSubtitleHandoffService.build(original, timeline_rate=FrameRate(24))
    second = ResolveSubtitleHandoffService.build(changed, timeline_rate=FrameRate(24))
    assert first.source_workspace_sha256 != second.source_workspace_sha256
    assert first.to_dict()["plan_sha256"] != second.to_dict()["plan_sha256"]
