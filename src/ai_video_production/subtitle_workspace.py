"""Versioned subtitle workspace for planning, SRT import, and human editing."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .atomic import AtomicJsonWriter
from .ids import IdKind, generate_id
from .subtitles import TranscriptManifest


class SubtitleOrigin(str, Enum):
    PLANNED_NARRATION = "PLANNED_NARRATION"
    ASR = "ASR"
    SRT_IMPORT = "SRT_IMPORT"
    HUMAN = "HUMAN"


class SubtitleReviewState(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"


@dataclass(frozen=True, slots=True)
class WorkspaceCue:
    cue_id: str
    start_ms: int
    end_ms: int
    text: str
    raw_text: str
    origin: SubtitleOrigin
    review_state: SubtitleReviewState = SubtitleReviewState.UNREVIEWED

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.cue_id):
            raise ValueError("cue_id is invalid")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("cue timing must be positive and ordered")
        for name, value in (("text", self.text), ("raw_text", self.raw_text)):
            normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
            if not normalized or len(normalized) > 10_000 or "\x00" in normalized:
                raise ValueError(f"{name} is invalid")
            object.__setattr__(self, name, normalized)

    def to_dict(self) -> dict[str, Any]:
        return {"cue_id": self.cue_id, "start_ms": self.start_ms, "end_ms": self.end_ms,
                "text": self.text, "raw_text": self.raw_text, "origin": self.origin.value,
                "review_state": self.review_state.value}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkspaceCue":
        return cls(str(value["cue_id"]), int(value["start_ms"]), int(value["end_ms"]),
                   str(value["text"]), str(value["raw_text"]), SubtitleOrigin(value["origin"]),
                   SubtitleReviewState(value.get("review_state", "UNREVIEWED")))


@dataclass(frozen=True, slots=True)
class NarrationCue:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class SubtitleWorkspace:
    workspace_id: str
    revision: int
    cues: tuple[WorkspaceCue, ...] = ()
    ai_typo_check_enabled: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.workspace_id):
            raise ValueError("workspace_id is invalid")
        if self.revision < 0:
            raise ValueError("revision must be non-negative")
        ids: set[str] = set()
        previous_end = 0
        for cue in self.cues:
            if cue.cue_id in ids:
                raise ValueError("duplicate cue_id")
            if cue.start_ms < previous_end:
                raise ValueError("subtitle cues overlap or are out of order")
            ids.add(cue.cue_id)
            previous_end = cue.end_ms

    @classmethod
    def empty(cls) -> "SubtitleWorkspace":
        return cls(generate_id(IdKind.OPERATION), 0)

    @classmethod
    def from_narration(cls, items: Iterable[NarrationCue]) -> "SubtitleWorkspace":
        cues = tuple(WorkspaceCue(f"cue-{i:06d}", x.start_ms, x.end_ms, x.text, x.text,
                                  SubtitleOrigin.PLANNED_NARRATION)
                     for i, x in enumerate(items, 1))
        return cls(generate_id(IdKind.OPERATION), 0, cues)

    @classmethod
    def from_transcript(cls, transcript: TranscriptManifest) -> "SubtitleWorkspace":
        """Create an editable workspace without losing the ASR source wording."""
        cues: list[WorkspaceCue] = []
        previous_end = 0
        for segment in transcript.segments:
            start_ms = max(previous_end, segment.start_us // 1000)
            end_ms = max(start_ms + 1, (segment.end_us + 999) // 1000)
            cues.append(WorkspaceCue(
                segment.segment_id,
                start_ms,
                end_ms,
                segment.text,
                segment.text,
                SubtitleOrigin.ASR,
            ))
            previous_end = end_ms
        return cls(generate_id(IdKind.OPERATION), 0, tuple(cues))

    def _next(self, cues: Iterable[WorkspaceCue] | None = None, **changes: Any) -> "SubtitleWorkspace":
        return replace(self, revision=self.revision + 1,
                       cues=tuple(cues) if cues is not None else self.cues, **changes)

    def set_ai_typo_check(self, enabled: bool) -> "SubtitleWorkspace":
        return self._next(ai_typo_check_enabled=bool(enabled))

    def insert(self, index: int, start_ms: int, end_ms: int, text: str) -> "SubtitleWorkspace":
        if not 0 <= index <= len(self.cues):
            raise ValueError("insert index is out of range")
        cue = WorkspaceCue(generate_id(IdKind.OPERATION), start_ms, end_ms, text, text, SubtitleOrigin.HUMAN)
        values = list(self.cues); values.insert(index, cue)
        return self._next(values)

    def insert_relative(self, cue_id: str | None, position: str, text: str = "新しい字幕") -> "SubtitleWorkspace":
        """Insert a cue strictly inside the requested visible gap.

        UI insertion deliberately keeps a one-millisecond margin from both
        neighboring subtitle boundaries.  For example, a gap bounded by
        ``...300`` and ``...600`` becomes ``...301`` through ``...599``.
        This makes the meaning of "before" and "after" visible and avoids
        reusing a neighboring cue's timestamp in hand-authored SRT.
        """
        if position == "append":
            if cue_id is not None:
                raise ValueError("append does not accept cue_id")
            if not self.cues:
                return self.insert(0, 0, 1000, text)
            start_ms = self.cues[-1].end_ms + 1
            return self.insert(len(self.cues), start_ms, start_ms + 1000, text)

        if position not in {"before", "after"}:
            raise ValueError("insert position is invalid")
        if not cue_id:
            raise ValueError("cue_id is required")

        try:
            cue_index = next(i for i, cue in enumerate(self.cues) if cue.cue_id == cue_id)
        except StopIteration as exc:
            raise ValueError("cue_id was not found") from exc

        index = cue_index if position == "before" else cue_index + 1
        left_boundary = self.cues[index - 1].end_ms if index else -1
        right_boundary = self.cues[index].start_ms if index < len(self.cues) else None

        if right_boundary is None:
            start_ms = left_boundary + 1
            return self.insert(index, start_ms, start_ms + 1000, text)

        start_ms = max(0, left_boundary + 1)
        end_ms = right_boundary - 1
        if end_ms <= start_ms:
            raise ValueError(
                "挿入できる空き時間がありません。前後字幕の間に2msを超える空きを作ってください。"
            )
        return self.insert(index, start_ms, end_ms, text)

    def update(self, cue_id: str, *, start_ms: int, end_ms: int, text: str,
               approved: bool = False) -> "SubtitleWorkspace":
        values = list(self.cues)
        for index, cue in enumerate(values):
            if cue.cue_id == cue_id:
                values[index] = replace(cue, start_ms=start_ms, end_ms=end_ms, text=text,
                                        review_state=SubtitleReviewState.APPROVED if approved else SubtitleReviewState.NEEDS_REVIEW)
                return self._next(values)
        raise ValueError("cue_id was not found")

    def delete(self, cue_id: str) -> "SubtitleWorkspace":
        values = tuple(x for x in self.cues if x.cue_id != cue_id)
        if len(values) == len(self.cues):
            raise ValueError("cue_id was not found")
        return self._next(values)

    def to_dict(self) -> dict[str, Any]:
        return {"workspace_version": "1.0.0", "workspace_id": self.workspace_id,
                "revision": self.revision, "ai_typo_check_enabled": self.ai_typo_check_enabled,
                "cues": [x.to_dict() for x in self.cues]}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SubtitleWorkspace":
        if value.get("workspace_version") != "1.0.0":
            raise ValueError("unsupported workspace version")
        return cls(str(value["workspace_id"]), int(value["revision"]),
                   tuple(WorkspaceCue.from_dict(x) for x in value["cues"]),
                   bool(value.get("ai_typo_check_enabled", False)))


_TIME = re.compile(r"^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$")


def _parse_time(value: str) -> int:
    match = _TIME.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value}")
    hours, minutes, seconds, millis = map(int, match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"invalid SRT timestamp: {value}")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def _format_time(value: int) -> str:
    hours, rem = divmod(value, 3_600_000); minutes, rem = divmod(rem, 60_000); seconds, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


class SrtWorkspaceCodec:
    @staticmethod
    def import_path(path: str | Path, *, max_bytes: int = 64 * 1024 * 1024,
                    max_cues: int = 200_000) -> SubtitleWorkspace:
        source = Path(path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size <= 0 or source.stat().st_size > max_bytes:
            raise ValueError("SRT must be a non-empty regular file within the configured size limit")
        cues: list[WorkspaceCue] = []
        with source.open("r", encoding="utf-8-sig", newline=None) as handle:
            block: list[str] = []
            for line in handle:
                stripped = line.rstrip("\r\n")
                if stripped:
                    block.append(stripped)
                    continue
                if block:
                    SrtWorkspaceCodec._append_block(block, cues, max_cues); block = []
            if block:
                SrtWorkspaceCodec._append_block(block, cues, max_cues)
        return SubtitleWorkspace(generate_id(IdKind.OPERATION), 0, tuple(cues))

    @staticmethod
    def _append_block(block: list[str], cues: list[WorkspaceCue], max_cues: int) -> None:
        if len(cues) >= max_cues:
            raise ValueError("SRT cue count exceeds the configured limit")
        timing_index = 1 if len(block) >= 2 and re.fullmatch(r"\d+", block[0].strip()) else 0
        if timing_index >= len(block) or "-->" not in block[timing_index]:
            raise ValueError(f"SRT cue {len(cues) + 1} has no timing line")
        left, right = [x.strip() for x in block[timing_index].split("-->", 1)]
        text = "\n".join(block[timing_index + 1:]).strip()
        cue = WorkspaceCue(f"cue-{len(cues) + 1:06d}", _parse_time(left), _parse_time(right),
                           text, text, SubtitleOrigin.SRT_IMPORT)
        cues.append(cue)

    @staticmethod
    def render(workspace: SubtitleWorkspace) -> str:
        blocks = [f"{i}\n{_format_time(c.start_ms)} --> {_format_time(c.end_ms)}\n{c.text}"
                  for i, c in enumerate(workspace.cues, 1)]
        return "\n\n".join(blocks) + ("\n" if blocks else "")


class SubtitleWorkspaceStore:
    @staticmethod
    def load(path: str | Path) -> SubtitleWorkspace:
        return SubtitleWorkspace.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def save(path: str | Path, workspace: SubtitleWorkspace, *, expected_revision: int | None = None) -> None:
        target = Path(path)
        if target.exists() and expected_revision is not None:
            current = SubtitleWorkspaceStore.load(target)
            if current.revision != expected_revision:
                raise ValueError("workspace revision conflict")
        AtomicJsonWriter.write(target, workspace.to_dict())
