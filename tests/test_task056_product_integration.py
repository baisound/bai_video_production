from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.schema_contracts import validate_instance
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


def _application(project: Path, **kwargs) -> Task056SpeechCueProductApplication:
    return Task056SpeechCueProductApplication(
        project_root=project,
        project_id="project-task056",
        output_directory=project / "private" / "transcription" / "semantic-cues",
        source_frame_rate=FrameRate(30, 1),
        **kwargs,
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
        "human_accepted_count": 0,
        "human_rejected_count": 0,
        "pending_review_count": 0,
        "review_revision": 0,
        "human_decisions": {},
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


def test_human_decision_requires_confirmation_and_survives_application_restart(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    application = _application(
        project,
        token_factory=lambda: "confirm-task056-1",
        clock=lambda: "2026-08-24T12:34:56.789Z",
    )
    transcript = _transcript()
    generated = application.generate(
        project_id="project-task056",
        transcript=transcript,
    )
    cue_id = generated["review_items"][0]["cue_id"]

    prepared = application.prepare_human_decision(
        transcript=transcript,
        cue_id=cue_id,
        decision="ACCEPT",
    )
    assert prepared["human_final_authority_required"] is True
    assert prepared["canonical_timeline"] is False
    assert prepared["auto_apply_authorized"] is False
    assert prepared["transcript_text_exposed"] is False
    assert prepared["host_path_exposed"] is False

    applied = application.apply_human_decision(
        transcript=transcript,
        confirmation_id=prepared["confirmation_id"],
    )
    assert applied["status"] == "HUMAN_DECISION_RECORDED"
    assert applied["decision"] == "ACCEPT"
    assert applied["confirmation_token_persisted"] is False
    assert applied["canonical_timeline"] is False
    assert applied["auto_apply_authorized"] is False
    with pytest.raises(ProductError) as reused:
        application.apply_human_decision(
            transcript=transcript,
            confirmation_id=prepared["confirmation_id"],
        )
    assert reused.value.code == "ERR_TASK056_CONFIRMATION_INVALID"

    restarted = _application(project)
    snapshot = restarted.snapshot(transcript)
    assert snapshot["pending_review_count"] == 0
    assert snapshot["human_accepted_count"] == 1
    assert snapshot["human_rejected_count"] == 0
    assert snapshot["review_revision"] == 1
    assert snapshot["review_items"] == []
    assert snapshot["human_decisions"][cue_id]["decision"] == "ACCEPT"
    regenerated = restarted.generate(
        project_id="project-task056",
        transcript=transcript,
    )
    assert regenerated["human_accepted_count"] == 1
    assert regenerated["pending_review_count"] == 0
    assert regenerated["human_decisions"][cue_id]["decision"] == "ACCEPT"

    review_files = list(
        (project / "private" / "transcription" / "semantic-cues" / "human-review").glob("*.json")
    )
    assert len(review_files) == 1
    stored = review_files[0].read_text(encoding="utf-8")
    schema = Path("schemas/speech-cue-human-review-store.schema.json")
    mirror = Path(
        "src/ai_video_production/schema_resources/speech-cue-human-review-store.schema.json"
    )
    assert schema.read_bytes() == mirror.read_bytes()
    validate_instance(json.loads(stored), schema)
    assert "チェイス" not in stored
    assert str(tmp_path) not in stored
    assert "confirm-task056-1" not in stored
    assert '"confirmation_tokens_persisted":false' in stored
    assert '"canonical_timeline":false' in stored
    assert '"auto_apply_authorized":false' in stored


def test_cancelled_human_decision_consumes_token_without_persistence(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    application = _application(
        project,
        token_factory=lambda: "confirm-task056-cancel",
        clock=lambda: "2026-08-24T12:36:00.000Z",
    )
    transcript = _transcript()
    generated = application.generate(project_id="project-task056", transcript=transcript)
    prepared = application.prepare_human_decision(
        transcript=transcript,
        cue_id=generated["review_items"][0]["cue_id"],
        decision="ACCEPT",
    )
    cancelled = application.cancel_human_decision(
        confirmation_id=prepared["confirmation_id"]
    )
    assert cancelled["status"] == "HUMAN_DECISION_CANCELLED"
    assert cancelled["decision_persisted"] is False
    assert cancelled["confirmation_token_persisted"] is False
    with pytest.raises(ProductError) as consumed:
        application.apply_human_decision(
            transcript=transcript,
            confirmation_id=prepared["confirmation_id"],
        )
    assert consumed.value.code == "ERR_TASK056_CONFIRMATION_INVALID"
    review_root = project / "private" / "transcription" / "semantic-cues" / "human-review"
    assert not list(review_root.glob("*.json"))

def test_human_review_store_tamper_and_duplicate_decision_fail_closed(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    application = _application(
        project,
        token_factory=lambda: "confirm-task056-2",
        clock=lambda: "2026-08-24T12:35:00.000Z",
    )
    transcript = _transcript()
    generated = application.generate(project_id="project-task056", transcript=transcript)
    cue_id = generated["review_items"][0]["cue_id"]
    prepared = application.prepare_human_decision(
        transcript=transcript,
        cue_id=cue_id,
        decision="REJECT",
    )
    application.apply_human_decision(
        transcript=transcript,
        confirmation_id=prepared["confirmation_id"],
    )
    with pytest.raises(ProductError) as duplicate:
        application.prepare_human_decision(
            transcript=transcript,
            cue_id=cue_id,
            decision="ACCEPT",
        )
    assert duplicate.value.code == "ERR_TASK056_HUMAN_DECISION_ALREADY_RECORDED"

    review_file = next(
        (project / "private" / "transcription" / "semantic-cues" / "human-review").glob("*.json")
    )
    document = json.loads(review_file.read_text(encoding="utf-8"))
    document["decisions"][0]["decision"] = "ACCEPT"
    review_file.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as tampered:
        application.snapshot(transcript)
    assert tampered.value.code == "ERR_TASK056_HUMAN_REVIEW_INVALID"

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
    assert "call('prepare_speech_cue_decision'" in shell
    assert "call('cancel_speech_cue_decision'" in shell
    assert "call('apply_speech_cue_decision'" in shell
    assert "文字起こし本文とPC内の保存場所は表示しません" in shell
    assert "TimelineやResolveへ自動反映しません" in shell
    assert 'self._empty_args(args, "speech cue generation")' in bridge
    assert "def prepare_speech_cue_decision" in bridge
    assert "def cancel_speech_cue_decision" in bridge
    assert "def apply_speech_cue_decision" in bridge
    assert "include_word_timestamps=True" in port