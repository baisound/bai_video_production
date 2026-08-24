from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.subtitles import (
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)
from ai_video_production.task056_product_integration import (
    Task056SpeechCueProductApplication,
)
from ai_video_production.timebase import FrameRate


ASSET_ID = "ASSET-00000000000000000000000000"


def _transcript(*, second_confidence: float = 0.40) -> TranscriptManifest:
    return TranscriptManifest(
        ASSET_ID,
        "ja",
        "faster-whisper",
        "small",
        (
            TranscriptSegment(
                "seg-1",
                0,
                2_000_000,
                "チェイス、チェイス",
                words=(
                    TranscriptWord(100_000, 400_000, "チェイス", 0.93),
                    TranscriptWord(1_100_000, 1_400_000, "チェイス", second_confidence),
                ),
            ),
        ),
        True,
    )


def _application(project: Path) -> Task056SpeechCueProductApplication:
    return Task056SpeechCueProductApplication(
        project_root=project,
        project_id="project-task056",
        output_directory=project / "private" / "transcription" / "semantic-cues",
        source_frame_rate=FrameRate(30, 1),
    )


def test_product_application_reuses_bound_transcript_and_returns_text_free_review_queue(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    application = _application(project)

    before = application.snapshot(_transcript())
    assert before == {
        "available": True,
        "task_owner": "TASK-056",
        "generated": False,
        "can_generate": True,
        "keyword_profile_id": "dbd-chase-call-ja-v1",
        "confirmed_count": 0,
        "review_count": 0,
        "rejected_count": 0,
        "review_items": [],
        "transcript_text_exposed": False,
        "host_path_exposed": False,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
    }

    result = application.generate(
        project_id="project-task056",
        transcript=_transcript(),
    )

    assert result["generated"] is True
    assert result["confirmed_count"] == 1
    assert result["review_count"] == 1
    assert result["rejected_count"] == 0
    assert len(result["review_items"]) == 1
    assert result["review_items"][0]["review_state"] == "REVIEW"
    assert result["review_items"][0]["timing_granularity"] == "WORD"
    assert result["transcript_text_exposed"] is False
    assert result["host_path_exposed"] is False
    assert result["canonical_timeline"] is False
    assert result["auto_apply_authorized"] is False

    serialized = json.dumps(result, ensure_ascii=False)
    assert "チェイス" not in serialized
    assert str(tmp_path) not in serialized

    output = project / "private" / "transcription" / "semantic-cues"
    projection = json.loads(
        (output / "montage-semantic-audio-cues.json").read_text(encoding="utf-8")
    )
    assert len(projection["cues"]) == 1
    assert projection["cues"][0]["review_state"] == "CONFIRMED"


def test_product_application_fails_closed_for_project_or_transcript_mismatch(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    application = _application(project)
    transcript = _transcript()

    with pytest.raises(ProductError) as project_error:
        application.generate(project_id="different-project", transcript=transcript)
    assert project_error.value.code == "ERR_TASK056_PROJECT_SCOPE_MISMATCH"

    application.generate(project_id="project-task056", transcript=transcript)
    changed = _transcript(second_confidence=0.41)
    with pytest.raises(ProductError) as transcript_error:
        application.snapshot(changed)
    assert transcript_error.value.code == "ERR_TASK056_PUBLICATION_BINDING_INVALID"


def test_product_shell_exposes_only_fixed_no_argument_cue_operations() -> None:
    shell = Path("src/ai_video_production/task036_shell_v611.py").read_text(
        encoding="utf-8"
    )
    bridge = Path("src/ai_video_production/task036_shell_ui.py").read_text(
        encoding="utf-8"
    )
    port = Path("src/ai_video_production/task036_product_ports.py").read_text(
        encoding="utf-8"
    )

    assert 'id="generateSpeechCuesButton"' in shell
    assert 'id="speechCueSummary"' in shell
    assert 'id="speechCueReviewList"' in shell
    assert "call('generate_speech_cues')" in shell
    assert "文字起こし本文とPC内の保存場所は表示しません" in shell
    assert 'self._empty_args(args, "speech cue generation")' in bridge
    assert "include_word_timestamps=True" in port