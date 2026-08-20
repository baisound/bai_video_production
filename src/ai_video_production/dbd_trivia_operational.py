"""TASK-051 R5 operational provenance for trivia candidates.

Canonical trivia truth remains in DbDTriviaStore. This sidecar only records
operator-facing provenance such as source video and transcript segment time.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Iterable

from .dbd_commentary_knowledge import DBDTriviaEntry


@dataclass(frozen=True, slots=True)
class TriviaOperationalMetadata:
    trivia_id: str
    source_video: str = ""
    transcript_path: str = ""
    segment_id: str = ""
    start_seconds: float | None = None
    end_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.trivia_id.strip():
            raise ValueError("trivia_id is required")
        if self.start_seconds is not None and self.start_seconds < 0:
            raise ValueError("start_seconds must be non-negative")
        if self.end_seconds is not None and self.end_seconds < 0:
            raise ValueError("end_seconds must be non-negative")
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError("end_seconds must be >= start_seconds")


class TriviaOperationalMetadataStore:
    schema_version = "1.0.0"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.exists():
            self._write(())

    def list(self) -> tuple[TriviaOperationalMetadata, ...]:
        with self._lock:
            body = json.loads(self.path.read_text(encoding="utf-8"))
            if body.get("schema_version") != self.schema_version:
                raise ValueError("unsupported trivia operational metadata schema")
            return tuple(
                TriviaOperationalMetadata(**row)
                for row in body.get("records", [])
            )

    def get(self, trivia_id: str) -> TriviaOperationalMetadata | None:
        return next((row for row in self.list() if row.trivia_id == trivia_id), None)

    def _write(self, rows: Iterable[TriviaOperationalMetadata]) -> None:
        values = tuple(sorted(rows, key=lambda x: x.trivia_id))
        fd, raw = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        os.close(fd)
        temp = Path(raw)
        try:
            temp.write_text(
                json.dumps(
                    {
                        "schema_version": self.schema_version,
                        "records": [asdict(row) for row in values],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()

    def upsert(self, row: TriviaOperationalMetadata) -> None:
        with self._lock:
            values = list(self.list())
            for index, existing in enumerate(values):
                if existing.trivia_id == row.trivia_id:
                    values[index] = row
                    self._write(values)
                    return
            values.append(row)
            self._write(values)

    def copy(self, source_trivia_id: str, target_trivia_id: str) -> None:
        source = self.get(source_trivia_id)
        if source is None:
            return
        self.upsert(
            TriviaOperationalMetadata(
                trivia_id=target_trivia_id,
                source_video=source.source_video,
                transcript_path=source.transcript_path,
                segment_id=source.segment_id,
                start_seconds=source.start_seconds,
                end_seconds=source.end_seconds,
            )
        )


def _segment_time(segment: object, prefix: str) -> float | None:
    for name in (
        f"{prefix}_seconds",
        f"{prefix}_time_seconds",
        prefix,
        f"{prefix}_s",
    ):
        value = getattr(segment, name, None)
        if isinstance(value, (int, float)):
            return float(value)
    milliseconds = getattr(segment, f"{prefix}_ms", None)
    if isinstance(milliseconds, (int, float)):
        return float(milliseconds) / 1000.0
    return None


def index_transcript_candidates(
    store: TriviaOperationalMetadataStore,
    *,
    entries: Iterable[DBDTriviaEntry],
    transcript: object,
    source_video: str = "",
    transcript_path: str = "",
) -> int:
    segments = getattr(transcript, "segments", None)
    if segments is None:
        return 0
    by_id = {}
    for segment in segments:
        segment_id = getattr(segment, "segment_id", None)
        if isinstance(segment_id, str):
            by_id[segment_id] = segment

    indexed = 0
    for entry in entries:
        marker = entry.source_ref.rsplit("/", 1)[-1]
        segment = by_id.get(marker)
        if segment is None:
            continue
        store.upsert(
            TriviaOperationalMetadata(
                trivia_id=entry.trivia_id,
                source_video=source_video,
                transcript_path=transcript_path,
                segment_id=marker,
                start_seconds=_segment_time(segment, "start"),
                end_seconds=_segment_time(segment, "end"),
            )
        )
        indexed += 1
    return indexed


def format_time_range(row: TriviaOperationalMetadata | None) -> str:
    if row is None or row.start_seconds is None:
        return ""
    if row.end_seconds is None:
        return f"{row.start_seconds:.2f}秒"
    return f"{row.start_seconds:.2f}–{row.end_seconds:.2f}秒"
