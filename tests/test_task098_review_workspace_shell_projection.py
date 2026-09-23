from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task098_review_workspace_contract import (
    ReviewViewport,
    project_microseconds_to_samples,
    project_milliseconds_to_samples,
)
from ai_video_production.task098_review_workspace_coordinator import (
    ReviewWorkspaceViewModel,
    SubtitleTimingRow,
    TranscriptTimingRow,
)
from ai_video_production.task098_review_workspace_shell_projection import (
    ReviewWorkspaceShellProjection,
    ShellReviewViewport,
    ShellSubtitleTimingRow,
    ShellTranscriptTimingRow,
    project_review_workspace,
)


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64


def private_view() -> ReviewWorkspaceViewModel:
    transcript_rows = (
        TranscriptTimingRow(
            "segment-1", 1_000_000, 2_000_000,
            project_microseconds_to_samples(1_000_000, 2_000_000),
        ),
        TranscriptTimingRow(
            "segment-2", 2_000_000, 3_000_000,
            project_microseconds_to_samples(2_000_000, 3_000_000),
        ),
    )
    subtitle_rows = (
        SubtitleTimingRow(
            "cue-1", 1_000, 2_000,
            project_milliseconds_to_samples(1_000, 2_000),
        ),
    )
    return ReviewWorkspaceViewModel(
        source_binding_sha256=H1,
        source_asset_id="ASSET-00000000000000000000000001",
        source_candidate_id="candidate:private:1",
        intent_sha256=H2,
        intent_id="intent:private:1",
        transcript_manifest_sha256=H3,
        workspace_id="workspace.private.1",
        workspace_revision=7,
        workspace_snapshot_sha256=H4,
        transcript_rows=transcript_rows,
        subtitle_rows=subtitle_rows,
        viewport=ReviewViewport(
            source_duration_samples=480_000,
            waveform_start_sample=48_000,
            waveform_span_samples=192_000,
            segment_count=2,
            segment_scroll_index=0,
            visible_segment_count=1,
        ),
    )


def test_projection_is_exact_allowlisted_body_free_and_effect_disabled() -> None:
    body = project_review_workspace(private_view()).to_dict()
    assert set(body) == {
        "projection_version", "task_owner", "available", "sample_rate_hz",
        "source_duration_samples", "workspace_revision",
        "workspace_transcript_lineage_confirmed", "transcript_timing_rows",
        "subtitle_timing_rows", "viewport", "capabilities",
    }
    assert body["task_owner"] == "TASK-098"
    assert body["workspace_transcript_lineage_confirmed"] is False
    assert body["viewport"]["segment_count"] == 2
    assert body["transcript_timing_rows"][0]["sample_range"] == {
        "start": 48_000,
        "end_exclusive": 96_000,
    }
    assert body["capabilities"]["local_viewport_scroll"] is True
    assert set(
        value
        for key, value in body["capabilities"].items()
        if key != "local_viewport_scroll"
    ) == {False}
    serialized = repr(body)
    for private_value in (
        H1, H2, H3, H4, "ASSET-00000000000000000000000001",
        "candidate:private:1", "intent:private:1", "workspace.private.1",
    ):
        assert private_value not in serialized
    for forbidden in ("text", "raw_text", "path", "digest", "sha256", "receipt"):
        assert forbidden not in serialized.lower()


def test_projection_constructor_rejects_forged_contract_state() -> None:
    projection = project_review_workspace(private_view())
    with pytest.raises(ValueError, match="48000"):
        replace(projection, sample_rate_hz=44_100)
    with pytest.raises(ValueError, match="lineage"):
        replace(projection, workspace_transcript_lineage_confirmed=True)
    with pytest.raises(ValueError, match="transcript_rows"):
        replace(projection, transcript_rows=({"text": "private"},))
    with pytest.raises(ValueError, match="segment_count"):
        replace(
            projection,
            viewport=ShellReviewViewport(48_000, 192_000, 1, 0, 1),
        )
    with pytest.raises(ValueError, match="source duration"):
        replace(projection, source_duration_samples=95_999)
    with pytest.raises(ValueError, match="projection"):
        ShellTranscriptTimingRow("segment-1", 1_000_000, 2_000_000, 1, 2)
    with pytest.raises(ValueError, match="projection"):
        ShellSubtitleTimingRow("cue-1", 1_000, 2_000, 1, 2)
    with pytest.raises(ValueError, match="segment_id"):
        ShellTranscriptTimingRow(
            "private text is not an id", 1_000_000, 2_000_000, 48_000, 96_000
        )
    with pytest.raises(ValueError, match="duplicated or out of order"):
        replace(
            projection,
            transcript_rows=(projection.transcript_rows[0], projection.transcript_rows[0]),
        )


def test_shell_without_provider_preserves_exact_legacy_view_model_shape() -> None:
    shell = ShellApplicationService(product_version="0.24.3")
    shell.open_project_context(project_id="p1", display_name="Project")
    expected = Task036ShellBridge(shell).view_model()
    actual = Task036ShellBridge(shell, review_workspace_provider=None).view_model()
    assert actual == expected
    assert "universal_wav_review" not in actual


def test_shell_provider_is_called_once_and_adds_projection_on_plain_path() -> None:
    shell = ShellApplicationService(product_version="0.24.3")
    shell.open_project_context(project_id="p1", display_name="Project")
    calls = 0

    def provider() -> ReviewWorkspaceViewModel:
        nonlocal calls
        calls += 1
        return private_view()

    body = Task036ShellBridge(shell, review_workspace_provider=provider).view_model()
    assert calls == 1
    assert body["universal_wav_review"]["available"] is True


def test_shell_adds_projection_after_integrated_application_path() -> None:
    shell = ShellApplicationService(product_version="0.24.3")
    shell.open_project_context(project_id="p1", display_name="Project")

    class FakeApplication:
        def __init__(self) -> None:
            self.shell = shell

        def view_model(self) -> dict[str, object]:
            return {"base": "integrated"}

    body = Task036ShellBridge(
        shell,
        application=FakeApplication(),  # type: ignore[arg-type]
        review_workspace_provider=private_view,
    ).view_model()
    assert body["base"] == "integrated"
    assert body["universal_wav_review"]["task_owner"] == "TASK-098"


@pytest.mark.parametrize(
    "provider",
    [
        lambda: {"private": "body"},
        lambda: (_ for _ in ()).throw(RuntimeError("private exception detail")),
    ],
)
def test_provider_failure_is_one_closed_product_error_without_partial_body(provider) -> None:
    shell = ShellApplicationService(product_version="0.24.3")
    bridge = Task036ShellBridge(
        shell,
        review_workspace_provider=provider,  # type: ignore[arg-type]
    )
    with pytest.raises(ProductError) as caught:
        bridge.view_model()
    error = caught.value
    assert error.code == "ERR_TASK098_REVIEW_WORKSPACE_PROJECTION_INVALID"
    assert error.category is ProductErrorCategory.DATA_INTEGRITY
    assert error.details == {}
    assert "private" not in str(error).lower()
    assert "universal_wav_review" not in error.to_envelope()


def test_projection_requires_exact_private_view_model_type() -> None:
    with pytest.raises(ValueError, match="ViewModel"):
        project_review_workspace({})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="48000"):
        ReviewWorkspaceShellProjection(
            sample_rate_hz=1,
            source_duration_samples=1,
            workspace_revision=0,
            transcript_rows=(),
            subtitle_rows=(),
            viewport=ShellReviewViewport(0, 1, 0, 0, 1),
        )


def test_projection_enables_only_audition_and_waveform_for_bound_a6_runtime() -> None:
    body = project_review_workspace(
        private_view(), review_runtime_enabled=True
    ).to_dict()
    assert body["capabilities"] == {
        "local_viewport_scroll": True,
        "audition": True,
        "waveform_render": True,
        "subtitle_mutation": False,
        "review_completion": False,
        "review_state_persistence": False,
        "human_decision_authorized": False,
    }
