from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

import ai_video_production.desktop_compute_diagnostics as diagnostics
from ai_video_production.desktop_compute_diagnostics import (
    BoundedDesktopDiagnostics,
    DiagnosticEvent,
    DiagnosticSeverity,
    DiagnosticWriteStatus,
    DiagnosticsError,
    MAX_ACTIVE_FILE_BYTES,
    MAX_QUEUE_BYTES,
    MAX_QUEUE_RECORDS,
    RETAINED_GENERATIONS,
    SHARED_DIRECTORY_CAP_BYTES,
)
from ai_video_production.desktop_install_layout import DesktopInstallLayout


INSTANCE = "bvp-install-" + "2" * 32


def _layout(tmp_path: Path) -> DesktopInstallLayout:
    data = tmp_path / "data"
    for leaf in ("settings", "logs", "runtime-cache", "settings/installation"):
        (data / leaf).mkdir(parents=True, exist_ok=True)
    return DesktopInstallLayout(
        install_instance_id=INSTANCE,
        install_scope="PER_USER",
        binary_root=tmp_path,
        data_root=data,
        task063_descriptor_sha256="sha256:" + "a" * 64,
        layout_sha256="sha256:" + "b" * 64,
        acl_principal_sids=("S-1-5-21-1000",),
    )


def _event(index: int = 0, severity: DiagnosticSeverity = DiagnosticSeverity.INFO) -> DiagnosticEvent:
    return DiagnosticEvent(
        application="BAI_VIDEO_PRODUCTION",
        application_version="1.0.0",
        session_id="sha256:" + f"{index:064x}",
        event_category="COMPUTE_PREFLIGHT",
        severity=severity,
        selected_preference="AUTO_GPU_FIRST",
        detected_adapter="NVIDIA_ADAPTER",
        effective_backend="CUDA",
        compatibility_result="NOT_CONFIRMED",
        failure_stage="RUNTIME_READBACK",
        reason_code="RUNTIME_NOT_CONFIRMED",
        next_action="OPEN_AI_MODEL_SETTINGS",
        exception_category="NONE",
        correlation_id="sha256:" + f"{index + 1:064x}",
    )


def test_structured_public_record_is_written_and_fsynced(tmp_path: Path) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    result = writer.emit(_event())
    records = [json.loads(line) for line in writer.active_path.read_text(encoding="utf-8").splitlines()]
    assert result.status is DiagnosticWriteStatus.WRITTEN
    assert records[0]["reason_code"] == "RUNTIME_NOT_CONFIRMED"
    assert "details" not in records[0]
    assert records[0]["message_type"] == "BvpDesktopDiagnosticEvent"


@pytest.mark.parametrize(
    "replacement",
    [
        "C:\\Users\\owner\\private.mp4",
        "raw prompt body",
        "transcript from private media",
        '{"provider_body":"secret"}',
        "sk-abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_free_text_private_or_provider_content_is_structurally_rejected(
    tmp_path: Path, replacement: str
) -> None:
    with pytest.raises(DiagnosticsError, match="public code"):
        replace(_event(), next_action=replacement)


def test_secret_like_value_cannot_hide_in_opaque_identity() -> None:
    with pytest.raises(DiagnosticsError, match="correlation_id"):
        replace(_event(), correlation_id="sk-abcdefghijklmnopqrstuvwxyz")


def test_warn_duplicates_are_aggregated_not_written_repeatedly(tmp_path: Path) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    first = writer.emit(_event(severity=DiagnosticSeverity.WARN))
    second = writer.emit(_event(severity=DiagnosticSeverity.WARN))
    assert first.status is DiagnosticWriteStatus.WRITTEN
    assert second.status is DiagnosticWriteStatus.AGGREGATED
    assert len(writer.active_path.read_text(encoding="utf-8").splitlines()) == 1


def test_rotation_retention_and_foreign_files_are_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    record = writer._record_bytes(_event())
    monkeypatch.setattr(diagnostics, "MAX_ACTIVE_FILE_BYTES", len(record))
    writer.active_path.write_bytes(record)
    foreign = writer.root / "owner-notes.txt"
    foreign.write_text("preserve", encoding="utf-8")
    assert writer.emit(_event()).status is DiagnosticWriteStatus.WRITTEN
    assert len(list(writer.root.glob("main.*.closed.jsonl"))) == 1
    for sequence in range(10):
        path = writer.root / f"main.{sequence:020d}.closed.jsonl"
        path.write_bytes(record)
        os.utime(path, (1_800_000_000 + sequence, 1_800_000_000 + sequence))
    writer.cleanup()
    assert len(list(writer.root.glob("main.*.closed.jsonl"))) == RETAINED_GENERATIONS
    assert foreign.read_text(encoding="utf-8") == "preserve"


def test_active_only_shared_cap_suspends_without_deleting_active_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    active_bytes = writer._record_bytes(_event())
    for index in range(8):
        family_writer = BoundedDesktopDiagnostics(writer.layout, application_family=f"family{index}")
        family_writer.active_path.write_bytes(
            family_writer._record_bytes(_event(index))
        )
    before = {path.name: path.stat().st_size for path in writer.root.glob("*.active.jsonl")}
    monkeypatch.setattr(diagnostics, "SHARED_DIRECTORY_CAP_BYTES", sum(before.values()))
    result = writer.emit(_event())
    after = {path.name: path.stat().st_size for path in writer.root.glob("*.active.jsonl")}
    assert len(active_bytes) > 0
    assert result.status is DiagnosticWriteStatus.SUSPENDED_ACTIVE_CAP
    assert after == before


def test_queue_is_bounded_when_coordinator_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")

    class TimeoutLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise TimeoutError

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(diagnostics, "_CoordinatorLock", TimeoutLock)
    statuses = [writer.emit(_event(index)) for index in range(MAX_QUEUE_RECORDS + 20)]
    assert writer.queued_records <= MAX_QUEUE_RECORDS
    assert writer.queued_bytes <= MAX_QUEUE_BYTES
    assert any(item.status in {DiagnosticWriteStatus.QUEUED, DiagnosticWriteStatus.DROPPED_QUEUE_FULL} for item in statuses)


def test_queued_records_cannot_bypass_process_rate_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    real_lock = diagnostics._CoordinatorLock

    class TimeoutLock:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise TimeoutError

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(diagnostics, "_CoordinatorLock", TimeoutLock)
    for index in range(30):
        assert writer.emit(_event(index, DiagnosticSeverity.ERROR)).status is DiagnosticWriteStatus.QUEUED
    monkeypatch.setattr(diagnostics, "_CoordinatorLock", real_lock)

    writer.emit(_event(999))

    assert writer.queued_records == 11
    assert len(writer.active_path.read_text(encoding="utf-8").splitlines()) == 20


def test_corrupt_global_rate_state_fails_closed_and_is_preserved(tmp_path: Path) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    assert writer.emit(_event()).status is DiagnosticWriteStatus.WRITTEN
    rate_state = writer._rate_state_path()
    rate_state.write_text('{"tampered":true}', encoding="utf-8")
    original = rate_state.read_bytes()

    result = writer.emit(_event(2))

    assert result.status is DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR
    assert rate_state.read_bytes() == original
    assert len(writer.active_path.read_text(encoding="utf-8").splitlines()) == 1


def test_concurrent_writers_leave_complete_json_lines(tmp_path: Path) -> None:
    layout = _layout(tmp_path)

    def write(index: int) -> DiagnosticWriteStatus:
        writer = BoundedDesktopDiagnostics(layout, application_family="shared")
        return writer.emit(_event(index)).status

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(write, range(8)))
    lines = (layout.logs_root / "shared.active.jsonl").read_text(encoding="utf-8").splitlines()
    assert all(json.loads(line)["message_type"] == "BvpDesktopDiagnosticEvent" for line in lines)
    assert len(lines) == statuses.count(DiagnosticWriteStatus.WRITTEN)


def test_cleanup_preserves_unverifiable_temporary_files(tmp_path: Path) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    owned = writer.root / ".task066-crash.tmp"
    foreign = writer.root / "foreign.tmp"
    owned.write_bytes(b"partial")
    foreign.write_bytes(b"preserve")
    writer.cleanup()
    assert owned.read_bytes() == b"partial"
    assert foreign.read_bytes() == b"preserve"


def test_foreign_closed_shape_is_never_deleted_or_counted(tmp_path: Path) -> None:
    writer = BoundedDesktopDiagnostics(_layout(tmp_path), application_family="main")
    foreign = writer.root / "main.00000000000000000001.closed.jsonl"
    foreign.write_bytes(b"owner data")
    writer.cleanup()
    assert foreign.read_bytes() == b"owner data"
    assert writer.emit(_event()).status is DiagnosticWriteStatus.WRITTEN


def test_terminal_guard_is_durable_across_writers_and_retries_after_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _layout(tmp_path)
    first = BoundedDesktopDiagnostics(layout, application_family="main")
    original = first._write_record_locked
    monkeypatch.setattr(first, "_write_record_locked", lambda event: (_ for _ in ()).throw(OSError("disk")))
    failed = first.emit_terminal_guard(_event(severity=DiagnosticSeverity.ERROR))
    assert failed.status is DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR
    monkeypatch.setattr(first, "_write_record_locked", original)
    assert first.emit_terminal_guard(_event(severity=DiagnosticSeverity.ERROR)).status is DiagnosticWriteStatus.WRITTEN

    second = BoundedDesktopDiagnostics(layout, application_family="main")
    duplicate = second.emit_terminal_guard(_event(severity=DiagnosticSeverity.ERROR))
    assert duplicate.status is DiagnosticWriteStatus.AGGREGATED
    assert len(second.active_path.read_text(encoding="utf-8").splitlines()) == 1


def test_terminal_guard_recovers_log_after_state_save_crash_without_duplicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _layout(tmp_path)
    first = BoundedDesktopDiagnostics(layout, application_family="main")
    monkeypatch.setattr(
        first,
        "_save_terminal_state",
        lambda keys: (_ for _ in ()).throw(OSError("state crash")),
    )
    failed = first.emit_terminal_guard(_event(severity=DiagnosticSeverity.ERROR))
    assert failed.status is DiagnosticWriteStatus.SUSPENDED_INTERNAL_ERROR
    assert len(first.active_path.read_text(encoding="utf-8").splitlines()) == 1

    second = BoundedDesktopDiagnostics(layout, application_family="main")
    recovered = second.emit_terminal_guard(_event(severity=DiagnosticSeverity.ERROR))
    assert recovered.status is DiagnosticWriteStatus.AGGREGATED
    assert recovered.reason_code == "TERMINAL_GUARD_RECOVERED"
    assert len(second.active_path.read_text(encoding="utf-8").splitlines()) == 1
