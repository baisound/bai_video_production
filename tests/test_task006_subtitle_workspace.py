from pathlib import Path

import pytest

from ai_video_production.subtitle_workspace import (
    NarrationCue, SrtWorkspaceCodec, SubtitleOrigin, SubtitleWorkspace, SubtitleWorkspaceStore,
)
from ai_video_production.subtitle_workspace_web import SubtitleWorkspaceWebService
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.ids import IdKind, generate_id


def test_planned_narration_creates_editable_draft_without_claiming_measured_timing() -> None:
    workspace = SubtitleWorkspace.from_narration((
        NarrationCue(0, 4000, "企画から作る字幕"), NarrationCue(4000, 9000, "次の字幕"),
    ))
    assert [x.origin for x in workspace.cues] == [SubtitleOrigin.PLANNED_NARRATION] * 2
    assert workspace.revision == 0 and workspace.ai_typo_check_enabled is False


def test_asr_transcript_becomes_workspace_with_outward_millisecond_rounding() -> None:
    transcript = TranscriptManifest(
        generate_id(IdKind.ASSET), "ja", "faster-whisper", "small",
        (TranscriptSegment("seg-1", 1, 1_001, "私たちはその間にある「と」をつなぐ"),),
    )
    workspace = SubtitleWorkspace.from_transcript(transcript)
    assert (workspace.cues[0].start_ms, workspace.cues[0].end_ms) == (0, 2)
    assert workspace.cues[0].origin is SubtitleOrigin.ASR


def test_adjacent_asr_segments_remain_non_overlapping_after_ms_conversion() -> None:
    transcript = TranscriptManifest(
        generate_id(IdKind.ASSET), "ja", "faster-whisper", "small",
        (TranscriptSegment("seg-1", 0, 1_001, "前"),
         TranscriptSegment("seg-2", 1_001, 2_000, "後")),
    )
    workspace = SubtitleWorkspace.from_transcript(transcript)
    assert workspace.cues[0].end_ms == workspace.cues[1].start_ms


def test_insert_update_delete_preserve_raw_text_and_increment_revision() -> None:
    workspace = SubtitleWorkspace.from_narration((NarrationCue(0, 1000, "原文"),))
    workspace = workspace.insert(1, 1000, 2000, "追加")
    inserted = workspace.cues[1]
    workspace = workspace.update(inserted.cue_id, start_ms=1000, end_ms=2500, text="人間修正", approved=True)
    assert workspace.cues[1].raw_text == "追加"
    assert workspace.cues[1].text == "人間修正"
    workspace = workspace.delete(workspace.cues[0].cue_id)
    assert workspace.revision == 3 and len(workspace.cues) == 1


def test_srt_import_handles_bom_multiline_missing_sequence_and_exports(tmp_path: Path) -> None:
    source = tmp_path / "input.srt"
    # Write exact bytes: text-mode newline translation would turn embedded CRLF
    # into CRCRLF on Windows and create a different, malformed fixture.
    source.write_bytes(
        b"\xef\xbb\xbf" +
        "1\r\n00:00:00,000 --> 00:00:01,000\r\n一行目\r\n二行目\r\n\r\n"
        "00:00:01.001 --> 00:00:02,000\r\n後\r\n".encode("utf-8")
    )
    workspace = SrtWorkspaceCodec.import_path(source)
    assert [x.text for x in workspace.cues] == ["一行目\n二行目", "後"]
    assert all(x.origin is SubtitleOrigin.SRT_IMPORT for x in workspace.cues)
    assert SrtWorkspaceCodec.render(workspace).startswith("1\n00:00:00,000 --> 00:00:01,000")


def test_srt_import_rejects_overlap_and_oversize(tmp_path: Path) -> None:
    source = tmp_path / "bad.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:02,000\na\n\n2\n00:00:01,000 --> 00:00:03,000\nb\n", encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        SrtWorkspaceCodec.import_path(source)
    with pytest.raises(ValueError, match="size limit"):
        SrtWorkspaceCodec.import_path(source, max_bytes=3)


def test_workspace_store_detects_revision_conflict(tmp_path: Path) -> None:
    path = tmp_path / "workspace.json"
    original = SubtitleWorkspace.empty()
    SubtitleWorkspaceStore.save(path, original)
    changed = original.set_ai_typo_check(True)
    SubtitleWorkspaceStore.save(path, changed, expected_revision=0)
    with pytest.raises(ValueError, match="revision conflict"):
        SubtitleWorkspaceStore.save(path, changed.set_ai_typo_check(False), expected_revision=0)


def test_web_service_operations_persist_and_ai_toggle_never_executes_provider(tmp_path: Path) -> None:
    path = tmp_path / "workspace.json"
    service = SubtitleWorkspaceWebService(path)
    result = service.apply({"revision": 0, "operation": "insert", "index": 0,
                            "start_ms": 0, "end_ms": 1000, "text": "字幕"})
    result = service.apply({"revision": result["revision"], "operation": "set_ai", "enabled": True})
    assert result["ai_typo_check_enabled"] is True
    assert SubtitleWorkspaceStore.load(path).cues[0].text == "字幕"


def test_web_service_import_and_export_srt(tmp_path: Path) -> None:
    source, target = tmp_path / "in.srt", tmp_path / "out.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")
    service = SubtitleWorkspaceWebService(tmp_path / "workspace.json")
    result = service.apply({"revision": 0, "operation": "import_srt", "path": str(source)})
    result = service.apply({"revision": result["revision"], "operation": "export_srt", "path": str(target)})
    assert target.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:01,000\n字幕\n"
