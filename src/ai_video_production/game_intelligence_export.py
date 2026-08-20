"""TASK-049 R9A independent Game Intelligence analysis export backend.

The exporter reads already-canonical local analysis state and writes portable
analysis artifacts.  It is intentionally independent from BVP Production UI,
Production Timeline, Resolve, provider execution, and publishing.
"""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Any, Sequence

from .canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
)
from .game_commentary import CommentaryCandidateStore
from .game_event_store import GameIntelligenceStore
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso
from .dbd_observation_envelope import (
    DbDObservationEnvelope,
    serialize_observations_csv,
    serialize_observations_jsonl,
)


_EXPORT_FORMAT = "task049.game-intelligence-export"
_EXPORT_VERSION = "1.0.0"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError(f"export target must not be a symlink: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def _srt_timestamp(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValueError("SRT milliseconds must be non-negative")
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _event_commentary_payload(
    commentary_store: CommentaryCandidateStore | None,
    event: CanonicalGameEvent,
) -> dict[str, Any] | None:
    if commentary_store is None:
        return None
    candidates = tuple(
        payload
        for payload in commentary_store.list_for_event(event.event_id, validated_only=True)
        if payload.get("event_revision") == event.revision
    )
    if len(candidates) > 1:
        raise ValueError(
            f"event {event.event_id}@{event.revision} has multiple VALIDATED Commentary candidates; Human selection is required"
        )
    return candidates[0] if candidates else None


def _is_srt_eligible(event: CanonicalGameEvent, commentary: dict[str, Any] | None) -> bool:
    return bool(
        commentary is not None
        and event.confirmation_state is EventConfirmationState.CONFIRMED
        and event.review_status
        in {
            EventReviewStatus.AUTO_ACCEPTED,
            EventReviewStatus.HUMAN_APPROVED,
            EventReviewStatus.HUMAN_CORRECTED,
        }
    )


class GameIntelligenceAnalysisExporter:
    """Write analysis-only artifacts from the local TASK-049 canonical stores."""

    @classmethod
    def export(
        cls,
        *,
        store: GameIntelligenceStore,
        match_id: str,
        destination: str | Path,
        commentary_store: CommentaryCandidateStore | None = None,
        observations: Sequence[DbDObservationEnvelope] = (),
    ) -> dict[str, Path]:
        if not isinstance(store, GameIntelligenceStore):
            raise ValueError("store must be a GameIntelligenceStore")
        if commentary_store is not None and not isinstance(commentary_store, CommentaryCandidateStore):
            raise ValueError("commentary_store must be a CommentaryCandidateStore or None")
        if any(not isinstance(item, DbDObservationEnvelope) for item in observations):
            raise ValueError("observations must contain DbDObservationEnvelope records")
        validate_id(match_id, IdKind.GAME_MATCH)

        root = Path(destination)
        if root.exists() and root.is_symlink():
            raise ValueError("export destination must not be a symlink")
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ValueError("export destination must be a directory")

        match = store.get_match(match_id)
        events = store.list_events(match_id, latest_only=True)
        commentary_by_event: dict[tuple[str, int], dict[str, Any]] = {}
        for event in events:
            payload = _event_commentary_payload(commentary_store, event)
            if payload is not None:
                commentary_by_event[(event.event_id, event.revision)] = payload

        event_payloads = [event.to_dict() for event in events]
        selected_commentary = [
            commentary_by_event[key]
            for key in sorted(commentary_by_event)
        ]
        observation_rows = tuple(sorted(
            observations,
            key=lambda item: (item.frame_start, item.observation_type.value, item.observation_id),
        ))
        observation_payloads = [item.to_dict() for item in observation_rows]

        analysis_body = {
            "schema_version": _EXPORT_VERSION,
            "export_format": _EXPORT_FORMAT,
            "match": match.to_dict(),
            "events": event_payloads,
            "validated_commentary": selected_commentary,
            "observations": observation_payloads,
            "analysis_only": True,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "external_publish_performed": False,
        }
        analysis_payload = {
            **analysis_body,
            "analysis_export_sha256": sha256_bytes(canonical_json_bytes(analysis_body)),
        }

        files: dict[str, Path] = {
            "json": root / "analysis.json",
            "jsonl": root / "events.jsonl",
            "csv": root / "events.csv",
            "markdown": root / "report.md",
            "srt": root / "commentary.srt",
            "manifest": root / "manifest.json",
        }

        _atomic_write_bytes(files["json"], canonical_json_bytes(analysis_payload) + b"\n")
        _atomic_write_text(
            files["jsonl"],
            "".join(canonical_json_bytes(payload).decode("utf-8") + "\n" for payload in event_payloads),
        )
        observations_jsonl_path: Path | None = None
        observations_csv_path: Path | None = None
        if observation_rows:
            observations_jsonl_path = root / "observations.jsonl"
            observations_csv_path = root / "observations.csv"
            _atomic_write_bytes(
                observations_jsonl_path,
                serialize_observations_jsonl(observation_rows),
            )
            _atomic_write_text(
                observations_csv_path,
                serialize_observations_csv(observation_rows),
            )

        csv_buffer = io.StringIO(newline="")
        writer = csv.writer(csv_buffer, lineterminator="\n")
        writer.writerow(
            (
                "event_id",
                "revision",
                "event_type",
                "start_frame",
                "end_frame_exclusive",
                "confidence_milli",
                "confirmation_state",
                "review_status",
                "evidence_count",
                "knowledge_ref_count",
                "commentary_candidate_id",
            )
        )
        for event in events:
            commentary = commentary_by_event.get((event.event_id, event.revision))
            writer.writerow(
                (
                    event.event_id,
                    event.revision,
                    event.event_type.value,
                    event.source_range.start_frame,
                    event.source_range.end_frame_exclusive,
                    event.confidence_milli,
                    event.confirmation_state.value,
                    event.review_status.value,
                    len(event.evidence_refs),
                    len(event.knowledge_refs),
                    "" if commentary is None else commentary["candidate_id"],
                )
            )
        _atomic_write_text(files["csv"], csv_buffer.getvalue())

        md: list[str] = [
            "# Game Intelligence Analysis Report",
            "",
            f"- Match: `{match.match_id}`",
            f"- Game profile: `{match.game_profile_id}`",
            f"- Game version: `{match.game_version}`",
            f"- Environment: `{match.environment.value}`",
            f"- Perspective: `{match.perspective.value}`",
            f"- Source asset: `{match.source_asset_id}`",
            f"- Source rate: `{match.source_rate.numerator}/{match.source_rate.denominator}`",
            f"- Latest events: `{len(events)}`",
            "- Mode: `ANALYSIS_ONLY`",
            "",
            "## Events",
            "",
        ]
        if not events:
            md.append("No canonical events are currently stored for this match.")
        for event in events:
            commentary = commentary_by_event.get((event.event_id, event.revision))
            md.extend(
                [
                    f"### {event.event_type.value} — `{event.event_id}@{event.revision}`",
                    "",
                    f"- Frames: `{event.source_range.start_frame}..{event.source_range.end_frame_exclusive}` (end-exclusive)",
                    f"- Confidence: `{event.confidence_milli}/1000`",
                    f"- Confirmation: `{event.confirmation_state.value}`",
                    f"- Review: `{event.review_status.value}`",
                    f"- Evidence: `{len(event.evidence_refs)}`",
                    f"- Knowledge refs: `{len(event.knowledge_refs)}`",
                ]
            )
            if commentary is not None:
                md.extend(["- Validated commentary:", "", f"> {commentary['draft']['text']}"])
            md.append("")
        _atomic_write_text(files["markdown"], "\n".join(md).rstrip() + "\n")

        srt_blocks: list[str] = []
        cue_index = 1
        for event in events:
            commentary = commentary_by_event.get((event.event_id, event.revision))
            if not _is_srt_eligible(event, commentary):
                continue
            assert commentary is not None
            micros = event.source_range.to_microsecond_range(match.source_rate)
            start_ms = micros["start"] // 1000
            end_ms = (micros["end_exclusive"] + 999) // 1000
            if end_ms <= start_ms:
                end_ms = start_ms + 1
            text = commentary["draft"]["text"].replace("\r\n", "\n").replace("\r", "\n").strip()
            srt_blocks.append(
                f"{cue_index}\n{_srt_timestamp(start_ms)} --> {_srt_timestamp(end_ms)}\n{text}\n"
            )
            cue_index += 1
        _atomic_write_text(files["srt"], "\n".join(srt_blocks))

        artifact_entries = []
        manifest_artifacts = [
            ("json", files["json"]),
            ("jsonl", files["jsonl"]),
            ("csv", files["csv"]),
            ("markdown", files["markdown"]),
            ("srt", files["srt"]),
        ]
        if observations_jsonl_path is not None:
            manifest_artifacts.append(
                ("observations_jsonl", observations_jsonl_path)
            )
        if observations_csv_path is not None:
            manifest_artifacts.append(
                ("observations_csv", observations_csv_path)
            )
        for key, path in manifest_artifacts:
            data = path.read_bytes()
            artifact_entries.append(
                {
                    "kind": key.upper(),
                    "filename": path.name,
                    "size_bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        manifest_body = {
            "schema_version": _EXPORT_VERSION,
            "export_format": _EXPORT_FORMAT,
            "match_id": match.match_id,
            "analysis_export_sha256": analysis_payload["analysis_export_sha256"],
            "artifacts": artifact_entries,
            "analysis_only": True,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "external_publish_performed": False,
            "created_at": utc_now_iso(),
        }
        manifest_payload = {
            **manifest_body,
            "manifest_sha256": sha256_bytes(canonical_json_bytes(manifest_body)),
        }
        _atomic_write_bytes(files["manifest"], canonical_json_bytes(manifest_payload) + b"\n")
        return files


__all__ = ["GameIntelligenceAnalysisExporter"]
