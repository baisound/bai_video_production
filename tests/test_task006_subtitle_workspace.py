from pathlib import Path
import json
import re
from urllib import error, request

import pytest

from ai_video_production.subtitle_workspace import (
    NarrationCue, SrtWorkspaceCodec, SubtitleOrigin, SubtitleWorkspace, SubtitleWorkspaceStore,
)
from ai_video_production.subtitle_workspace_web import SubtitleWorkspaceWebService, launch_server
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.ids import IdKind, generate_id


def _open_rejected_loopback(
    req: request.Request,
    *,
    opener=request.urlopen,
):
    for attempt in range(3):
        try:
            return opener(req, timeout=3)
        except ConnectionAbortedError as exc:
            # The rejected request has no mutation, so this exact Windows
            # transient is safe to retry before asserting the HTTP 400.
            if getattr(exc, "winerror", None) != 10053 or attempt == 2:
                raise
    raise AssertionError("bounded rejected-request retry exhausted")


def test_rejected_loopback_retries_only_windows_abort_10053() -> None:
    class WindowsAbort10053(ConnectionAbortedError):
        winerror = 10053

    calls: list[int] = []

    def opener(req: request.Request, timeout: int):
        del req, timeout
        calls.append(1)
        if len(calls) == 1:
            raise WindowsAbort10053()
        raise error.HTTPError("http://127.0.0.1/", 400, "bad", {}, None)

    with pytest.raises(error.HTTPError) as exc_info:
        _open_rejected_loopback(request.Request("http://127.0.0.1/"), opener=opener)
    assert exc_info.value.code == 400
    assert len(calls) == 2


def test_rejected_loopback_retry_exhaustion_and_other_errors_fail_closed() -> None:
    class WindowsAbort10053(ConnectionAbortedError):
        winerror = 10053

    exact_calls: list[int] = []

    def exact_opener(req: request.Request, timeout: int):
        del req, timeout
        exact_calls.append(1)
        raise WindowsAbort10053()

    with pytest.raises(WindowsAbort10053):
        _open_rejected_loopback(
            request.Request("http://127.0.0.1/"),
            opener=exact_opener,
        )
    assert len(exact_calls) == 3

    class OtherAbort(ConnectionAbortedError):
        winerror = 10054

    other_calls: list[int] = []

    def other_opener(req: request.Request, timeout: int):
        del req, timeout
        other_calls.append(1)
        raise OtherAbort()

    with pytest.raises(OtherAbort):
        _open_rejected_loopback(
            request.Request("http://127.0.0.1/"),
            opener=other_opener,
        )
    assert len(other_calls) == 1


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


class _FakeDialog:
    def __init__(self, open_path: str | None, save_path: str | None) -> None:
        self.open_path = open_path
        self.save_path = save_path
        self.calls: list[str] = []

    def choose_open_srt(self) -> str | None:
        self.calls.append("open")
        return self.open_path

    def choose_save_srt(self) -> str | None:
        self.calls.append("save")
        return self.save_path


def test_web_service_native_dialog_contract_is_explicit_and_non_mutating(tmp_path: Path) -> None:
    fake = _FakeDialog(r"C:\字幕\input.srt", r"D:\出力\edited.srt")
    service = SubtitleWorkspaceWebService(tmp_path / "workspace.json", file_dialog=fake)
    before = service.form()

    opened = service.choose_path("open_srt")
    saved = service.choose_path("save_srt")

    assert opened == {"path": r"C:\字幕\input.srt", "cancelled": False}
    assert saved == {"path": r"D:\出力\edited.srt", "cancelled": False}
    assert fake.calls == ["open", "save"]
    assert service.form() == before


def test_web_service_native_dialog_cancel_and_unknown_kind(tmp_path: Path) -> None:
    service = SubtitleWorkspaceWebService(
        tmp_path / "workspace.json",
        file_dialog=_FakeDialog(None, None),
    )
    assert service.choose_path("open_srt") == {"path": None, "cancelled": True}
    assert service.choose_path("save_srt") == {"path": None, "cancelled": True}
    with pytest.raises(ValueError, match="unsupported dialog kind"):
        service.choose_path("folder")


def test_loopback_dialog_endpoint_requires_csrf_and_returns_selected_path(tmp_path: Path) -> None:
    fake = _FakeDialog(r"C:\字幕\input.srt", None)
    service = SubtitleWorkspaceWebService(tmp_path / "workspace.json", file_dialog=fake)
    server, thread, url = launch_server(service, port=0)
    try:
        html = request.urlopen(url, timeout=3).read().decode("utf-8")
        token_match = re.search(r"const CSRF=(\"[^\"]+\")", html)
        assert token_match is not None
        csrf = json.loads(token_match.group(1))

        body = json.dumps({"kind": "open_srt"}).encode("utf-8")
        bad = request.Request(
            url + "api/dialog",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "X-BAI-CSRF": "wrong"},
        )
        with pytest.raises(error.HTTPError) as exc_info:
            _open_rejected_loopback(bad)
        assert exc_info.value.code == 400

        good = request.Request(
            url + "api/dialog",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "X-BAI-CSRF": csrf},
        )
        result = json.loads(request.urlopen(good, timeout=3).read().decode("utf-8"))
        assert result == {"path": r"C:\字幕\input.srt", "cancelled": False}
        assert service.form()["revision"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_relative_insert_uses_strict_millisecond_gap_between_neighbors() -> None:
    workspace = SubtitleWorkspace.from_narration((
        NarrationCue(0, 300, "前"),
        NarrationCue(600, 900, "後"),
    ))

    inserted = workspace.insert_relative(workspace.cues[0].cue_id, "after")

    assert len(inserted.cues) == 3
    assert (inserted.cues[1].start_ms, inserted.cues[1].end_ms) == (301, 599)
    assert inserted.cues[1].text == "新しい字幕"
    assert inserted.cues[2].text == "後"


def test_relative_insert_before_and_append_are_visibly_ordered() -> None:
    workspace = SubtitleWorkspace.from_narration((
        NarrationCue(300, 600, "基準"),
    ))

    before = workspace.insert_relative(workspace.cues[0].cue_id, "before", "前追加")
    assert [(cue.start_ms, cue.end_ms, cue.text) for cue in before.cues] == [
        (0, 299, "前追加"),
        (300, 600, "基準"),
    ]

    appended = before.insert_relative(None, "append", "末尾追加")
    assert (appended.cues[-1].start_ms, appended.cues[-1].end_ms) == (601, 1601)
    assert appended.cues[-1].text == "末尾追加"


def test_relative_insert_rejects_gap_without_strict_room() -> None:
    workspace = SubtitleWorkspace.from_narration((
        NarrationCue(0, 300, "前"),
        NarrationCue(302, 600, "後"),
    ))
    with pytest.raises(ValueError, match="挿入できる空き時間"):
        workspace.insert_relative(workspace.cues[0].cue_id, "after")


def test_web_service_relative_insert_contract_and_export_evidence(tmp_path: Path) -> None:
    target = tmp_path / "exported.srt"
    service = SubtitleWorkspaceWebService(tmp_path / "workspace.json")
    result = service.apply({"revision": 0, "operation": "insert", "index": 0,
                            "start_ms": 0, "end_ms": 300, "text": "前"})
    result = service.apply({"revision": result["revision"], "operation": "insert", "index": 1,
                            "start_ms": 600, "end_ms": 900, "text": "後"})
    result = service.apply({"revision": result["revision"], "operation": "insert_relative",
                            "cue_id": result["cues"][0]["cue_id"], "position": "after",
                            "text": "間"})
    assert (result["cues"][1]["start_ms"], result["cues"][1]["end_ms"]) == (301, 599)

    exported = service.apply({"revision": result["revision"], "operation": "export_srt",
                              "path": str(target)})
    assert exported["exported_path"] == str(target.resolve())
    assert exported["exported_bytes"] == target.stat().st_size
    assert exported["exported_bytes"] > 0


def test_workspace_html_exposes_prominent_status_and_server_disconnect_guidance(tmp_path: Path) -> None:
    service = SubtitleWorkspaceWebService(tmp_path / "workspace.json", file_dialog=_FakeDialog(None, None))
    server, thread, url = launch_server(service, port=0)
    try:
        html = request.urlopen(url, timeout=3).read().decode("utf-8")
        assert 'id="msg" class="notice" role="status" aria-live="polite"' in html
        assert "SRT書き出し成功" in html
        assert "exported_path" in html and "exported_bytes" in html
        assert "ローカルサーバーに接続できません" in html
        assert "insert_relative" in html
        assert "insertionRange" not in html
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
