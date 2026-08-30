"""TASK-054 R5B time-aligned, read-only Commentary Preview projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .dbd_reasoning_contracts import ReasoningSessionMode, verify_canonical_record_sha256
from .game_commentary import verify_commentary_candidate_payload
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


PREVIEW_SCHEMA_VERSION = "1.0.0"
_ANALYSIS_FIELDS = {
    "schema_version", "export_format", "match", "events", "validated_commentary",
    "observations", "analysis_only", "production_timeline_mutated",
    "resolve_write_performed", "external_publish_performed", "analysis_export_sha256",
}
_MATCH_FIELDS = {
    "schema_version", "match_id", "production_job_id", "source_asset_id",
    "game_profile_id", "game_profile_version", "game_version", "environment",
    "perspective", "source_rate", "analysis_revision", "status", "created_at", "match_sha256",
}
_EVENT_FIELDS = {
    "schema_version", "event_id", "match_id", "revision", "event_type", "source_range",
    "game_version", "environment", "perspective", "state", "confidence_milli",
    "confirmation_state", "evidence_refs", "knowledge_refs", "review_status", "created_at", "event_sha256",
}
_ADMITTED_REVIEW = {"AUTO_ACCEPTED", "HUMAN_APPROVED", "HUMAN_CORRECTED"}


class CommentaryPreviewKind(str, Enum):
    PLAY_BY_PLAY = "PLAY_BY_PLAY"
    EXPLANATION = "EXPLANATION"
    TACTICAL = "TACTICAL"
    REACTION = "REACTION"


class PreviewMediaBindingStatus(str, Enum):
    CANONICAL_ASSET_BOUND = "CANONICAL_ASSET_BOUND"
    OPERATOR_SELECTED_UNVERIFIED = "OPERATOR_SELECTED_UNVERIFIED"


class CommentaryPreviewStatus(str, Enum):
    READY = "READY"
    NO_VALIDATED_COMMENTARY = "NO_VALIDATED_COMMENTARY"
    NOT_CONFIRMED_MEDIA_IDENTITY = "NOT_CONFIRMED_MEDIA_IDENTITY"


def _integer(value: Any, *, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _text(value: Any, *, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string up to {maximum} characters")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ValueError(f"{name} contains a control character")
    return value


def _block_kind(candidate: Mapping[str, Any]) -> CommentaryPreviewKind:
    knowledge_kinds = {
        "PERK_EFFECT", "KILLER_DESCRIPTION", "POWER_DESCRIPTION", "TRIVIA",
    }
    facts = candidate["plan"].get("facts") or []
    if any(isinstance(item, Mapping) and item.get("kind") in knowledge_kinds for item in facts):
        return CommentaryPreviewKind.EXPLANATION
    return CommentaryPreviewKind.PLAY_BY_PLAY


@dataclass(frozen=True, slots=True)
class CommentaryPreviewBlock:
    event_id: str
    event_revision: int
    event_sha256: str
    candidate_id: str
    commentary_candidate_sha256: str
    start_ms: int
    end_ms: int
    kind: CommentaryPreviewKind
    text: str
    confidence_milli: int
    validation_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        _text(self.event_id, name="event_id", maximum=128)
        _integer(self.event_revision, name="event_revision", minimum=1)
        validate_sha256(self.event_sha256, field_name="event_sha256")
        _text(self.candidate_id, name="candidate_id", maximum=128)
        validate_sha256(self.commentary_candidate_sha256, field_name="commentary_candidate_sha256")
        _integer(self.start_ms, name="start_ms")
        _integer(self.end_ms, name="end_ms", minimum=1)
        if self.end_ms <= self.start_ms:
            raise ValueError("preview block must have a positive duration")
        if not isinstance(self.kind, CommentaryPreviewKind):
            raise ValueError("kind must be CommentaryPreviewKind")
        _text(self.text, name="text", maximum=8000)
        if not 0 <= _integer(self.confidence_milli, name="confidence_milli") <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.validation_status != "VALIDATED":
            raise ValueError("only VALIDATED commentary is previewable")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_revision": self.event_revision,
            "event_sha256": self.event_sha256,
            "candidate_id": self.candidate_id,
            "commentary_candidate_sha256": self.commentary_candidate_sha256,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "kind": self.kind.value,
            "text": self.text,
            "confidence_milli": self.confidence_milli,
            "validation_status": self.validation_status,
        }


@dataclass(frozen=True, slots=True)
class CommentaryPreview:
    preview_id: str
    source_analysis_export_sha256: str
    match_id: str
    source_asset_id: str
    analysis_revision: int
    video_duration_ms: int
    media_binding_status: PreviewMediaBindingStatus
    status: CommentaryPreviewStatus
    blocks: tuple[CommentaryPreviewBlock, ...]

    def __post_init__(self) -> None:
        _text(self.preview_id, name="preview_id", maximum=128)
        validate_sha256(self.source_analysis_export_sha256, field_name="source_analysis_export_sha256")
        _text(self.match_id, name="match_id", maximum=128)
        _text(self.source_asset_id, name="source_asset_id", maximum=128)
        _integer(self.analysis_revision, name="analysis_revision", minimum=1)
        _integer(self.video_duration_ms, name="video_duration_ms", minimum=1)
        if not isinstance(self.media_binding_status, PreviewMediaBindingStatus):
            raise ValueError("media_binding_status must be PreviewMediaBindingStatus")
        if not isinstance(self.status, CommentaryPreviewStatus):
            raise ValueError("status must be CommentaryPreviewStatus")
        if not isinstance(self.blocks, tuple) or any(not isinstance(item, CommentaryPreviewBlock) for item in self.blocks):
            raise ValueError("blocks must contain CommentaryPreviewBlock values")
        if len(self.blocks) > 10_000:
            raise ValueError("preview blocks exceed maximum")
        keys = tuple((item.start_ms, item.end_ms, item.event_id, item.candidate_id) for item in self.blocks)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("preview blocks must be unique and canonically ordered")
        if any(item.end_ms > self.video_duration_ms for item in self.blocks):
            raise ValueError("preview block exceeds video duration")
        expected = (
            CommentaryPreviewStatus.NO_VALIDATED_COMMENTARY
            if not self.blocks
            else CommentaryPreviewStatus.NOT_CONFIRMED_MEDIA_IDENTITY
            if self.media_binding_status is PreviewMediaBindingStatus.OPERATOR_SELECTED_UNVERIFIED
            else CommentaryPreviewStatus.READY
        )
        if self.status is not expected:
            raise ValueError("preview status does not match blocks/media binding")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": PREVIEW_SCHEMA_VERSION,
            "preview_id": self.preview_id,
            "source_analysis_export_sha256": self.source_analysis_export_sha256,
            "match_id": self.match_id,
            "source_asset_id": self.source_asset_id,
            "analysis_revision": self.analysis_revision,
            "video_duration_ms": self.video_duration_ms,
            "session_mode": ReasoningSessionMode.PREVIEW_NO_LEARNING.value,
            "training_eligible": False,
            "media_binding_status": self.media_binding_status.value,
            "status": self.status.value,
            "blocks": [item.to_dict() for item in self.blocks],
            "dataset_mutated": False,
            "binding_mutated": False,
            "training_started": False,
            "provider_execution_performed": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "state": "PRESENTATION_ONLY_NO_EXECUTION",
        }
        return {**body, "preview_sha256": sha256_bytes(canonical_json_bytes(body))}


def compile_commentary_preview(
    analysis: Mapping[str, Any],
    *,
    preview_id: str,
    video_duration_ms: int,
    media_binding_status: PreviewMediaBindingStatus,
) -> CommentaryPreview:
    """Compile an admitted TASK-049 analysis export into a read-only preview."""

    if not isinstance(analysis, Mapping) or set(analysis) != _ANALYSIS_FIELDS:
        raise ValueError("analysis export fields are not exact")
    if analysis.get("schema_version") != "1.0.0" or analysis.get("export_format") != "task049.game-intelligence-export":
        raise ValueError("unsupported analysis export")
    if any((
        analysis.get("analysis_only") is not True,
        analysis.get("production_timeline_mutated") is not False,
        analysis.get("resolve_write_performed") is not False,
        analysis.get("external_publish_performed") is not False,
    )):
        raise ValueError("analysis export side-effect flags are invalid")
    verify_canonical_record_sha256(analysis, checksum_field="analysis_export_sha256")
    match = analysis.get("match")
    if not isinstance(match, Mapping):
        raise ValueError("analysis match is required")
    if set(match) != _MATCH_FIELDS or match.get("schema_version") != "1.0.0":
        raise ValueError("analysis match fields are not exact")
    verify_canonical_record_sha256(match, checksum_field="match_sha256")
    rate = match.get("source_rate")
    if not isinstance(rate, Mapping) or set(rate) != {"numerator", "denominator"}:
        raise ValueError("exact source_rate is required")
    numerator = _integer(rate.get("numerator"), name="source_rate.numerator", minimum=1)
    denominator = _integer(rate.get("denominator"), name="source_rate.denominator", minimum=1)

    events = analysis.get("events")
    candidates = analysis.get("validated_commentary")
    if not isinstance(events, list) or not isinstance(candidates, list):
        raise ValueError("events and validated_commentary must be arrays")
    if len(events) > 10_000 or len(candidates) > 10_000:
        raise ValueError("analysis preview inputs exceed maximum")
    event_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    for event in events:
        if not isinstance(event, Mapping):
            raise ValueError("event must be an object")
        if set(event) != _EVENT_FIELDS or event.get("schema_version") != "1.0.0":
            raise ValueError("event fields are not exact")
        verify_canonical_record_sha256(event, checksum_field="event_sha256")
        if event.get("match_id") != match.get("match_id"):
            raise ValueError("event crosses match boundary")
        key = (event.get("event_id"), event.get("revision"))
        if key in event_by_key:
            raise ValueError("duplicate event revision")
        event_by_key[key] = event

    candidate_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    for candidate in candidates:
        verify_commentary_candidate_payload(candidate)
        if candidate.get("match_id") != match.get("match_id"):
            raise ValueError("commentary crosses match boundary")
        key = (candidate.get("event_id"), candidate.get("event_revision"))
        if key in candidate_by_key:
            raise ValueError("multiple validated Commentary candidates require Human selection")
        candidate_by_key[key] = candidate
    if not set(candidate_by_key).issubset(event_by_key):
        raise ValueError("commentary references an absent event revision")

    blocks: list[CommentaryPreviewBlock] = []
    for key, event in event_by_key.items():
        candidate = candidate_by_key.get(key)
        if candidate is None:
            continue
        if event.get("confirmation_state") != "CONFIRMED" or event.get("review_status") not in _ADMITTED_REVIEW:
            continue
        source_range = event.get("source_range")
        if not isinstance(source_range, Mapping) or set(source_range) != {"start_frame", "end_frame_exclusive"}:
            raise ValueError("event source_range is invalid")
        start_frame = _integer(source_range.get("start_frame"), name="start_frame")
        end_frame = _integer(source_range.get("end_frame_exclusive"), name="end_frame_exclusive", minimum=1)
        if end_frame <= start_frame:
            raise ValueError("event source_range must be positive")
        start_ms = start_frame * denominator * 1000 // numerator
        end_ms = (end_frame * denominator * 1000 + numerator - 1) // numerator
        blocks.append(CommentaryPreviewBlock(
            event_id=event["event_id"],
            event_revision=event["revision"],
            event_sha256=event["event_sha256"],
            candidate_id=candidate["candidate_id"],
            commentary_candidate_sha256=candidate["commentary_candidate_sha256"],
            start_ms=start_ms,
            end_ms=end_ms,
            kind=_block_kind(candidate),
            text=candidate["draft"]["text"],
            confidence_milli=event["confidence_milli"],
        ))
    ordered = tuple(sorted(blocks, key=lambda item: (item.start_ms, item.end_ms, item.event_id, item.candidate_id)))
    duration = _integer(video_duration_ms, name="video_duration_ms", minimum=1)
    status = (
        CommentaryPreviewStatus.NO_VALIDATED_COMMENTARY
        if not ordered
        else CommentaryPreviewStatus.NOT_CONFIRMED_MEDIA_IDENTITY
        if media_binding_status is PreviewMediaBindingStatus.OPERATOR_SELECTED_UNVERIFIED
        else CommentaryPreviewStatus.READY
    )
    return CommentaryPreview(
        preview_id=preview_id,
        source_analysis_export_sha256=analysis["analysis_export_sha256"],
        match_id=match["match_id"],
        source_asset_id=match["source_asset_id"],
        analysis_revision=match["analysis_revision"],
        video_duration_ms=duration,
        media_binding_status=media_binding_status,
        status=status,
        blocks=ordered,
    )


__all__ = [
    "CommentaryPreview", "CommentaryPreviewBlock", "CommentaryPreviewKind",
    "CommentaryPreviewStatus", "PreviewMediaBindingStatus", "compile_commentary_preview",
]
