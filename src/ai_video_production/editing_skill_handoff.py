"""Body-free common evidence for knowledge/commentary and montage handoffs.

The projection is deliberately non-authoritative.  It describes whether the
source handoff is ready for its separately owned execution gate; it never
performs or authorizes a Resolve write.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .montage_contracts import parse_montage_resolve_handoff
from .resolve_subtitle_handoff import (
    ResolveSubtitlePlacement,
    ResolveSubtitlePlacementPlan,
)
from .serialization import canonical_json_bytes, sha256_bytes
from .subtitle_workspace import SubtitleReviewState
from .timebase import FrameRate


KNOWLEDGE_COMMENTARY = "KNOWLEDGE_COMMENTARY"
MONTAGE = "MONTAGE"
SOURCE_READY = "SOURCE_READY_FOR_EXECUTION_GATE"
REVIEW_REQUIRED = "REVIEW_OR_RUNTIME_QA_REQUIRED"
LEGACY_NOT_AVAILABLE = "NOT_AVAILABLE_LEGACY_SAFE"

_KNOWLEDGE_FIELDS = {
    "plan_version",
    "workspace_id",
    "workspace_revision",
    "source_workspace_sha256",
    "timeline_rate",
    "timeline_origin_frame",
    "track_index",
    "placements",
    "ready_for_resolve_write",
    "handoff_owner",
    "execution_owner",
    "contains_private_subtitle_text",
    "plan_sha256",
}


class EditingSkillHandoffError(ValueError):
    """Raised when a source handoff cannot be projected safely."""


@dataclass(frozen=True, slots=True)
class EditingSkillHandoffEvidence:
    editing_mode: str
    source_sha256: str
    source_owner: str
    execution_owner: str
    source_ready: bool
    privacy_class: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "evidence_version": "1.0.0",
            "editing_mode": self.editing_mode,
            "source_sha256": self.source_sha256,
            "source_owner": self.source_owner,
            "execution_owner": self.execution_owner,
            "source_readiness": SOURCE_READY if self.source_ready else REVIEW_REQUIRED,
            "privacy_class": self.privacy_class,
            "source_payload_included": False,
            "canonical_timeline": False,
            "resolve_write_authorized": False,
            "runtime_authority_created": False,
        }
        body["evidence_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _mapping(value: Mapping[str, Any], *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EditingSkillHandoffError(f"{name} must be an object")
    return dict(value)


def _require_bool(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise EditingSkillHandoffError(f"{name} must be boolean")
    return value


def _require_integer(value: object, *, name: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise EditingSkillHandoffError(f"{name} must be an integer >= {minimum}")
    return value


def _require_string(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise EditingSkillHandoffError(f"{name} must be a non-empty string")
    return value


def _verify_self_hash(document: dict[str, Any], *, field: str) -> str:
    digest = document.get(field)
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise EditingSkillHandoffError(f"{field} is invalid")
    body = {key: value for key, value in document.items() if key != field}
    if sha256_bytes(canonical_json_bytes(body)) != digest:
        raise EditingSkillHandoffError(f"{field} mismatch")
    return digest


def project_knowledge_commentary_handoff(
    value: Mapping[str, Any],
) -> EditingSkillHandoffEvidence:
    """Project a private subtitle placement plan without copying its payload."""

    document = _mapping(value, name="knowledge/commentary handoff")
    if set(document) != _KNOWLEDGE_FIELDS:
        raise EditingSkillHandoffError("knowledge/commentary handoff fields differ")
    if document["plan_version"] != "1.0.0":
        raise EditingSkillHandoffError("knowledge/commentary plan_version differs")
    if document["handoff_owner"] != "TASK-006":
        raise EditingSkillHandoffError("knowledge/commentary handoff_owner differs")
    if document["execution_owner"] != "TASK-010":
        raise EditingSkillHandoffError("knowledge/commentary execution_owner differs")
    if _require_bool(
        document["contains_private_subtitle_text"],
        name="contains_private_subtitle_text",
    ) is not True:
        raise EditingSkillHandoffError("knowledge/commentary privacy marker differs")
    source_ready = _require_bool(
        document["ready_for_resolve_write"],
        name="ready_for_resolve_write",
    )
    digest = _verify_self_hash(document, field="plan_sha256")
    try:
        timeline_rate = _mapping(document["timeline_rate"], name="timeline_rate")
        if set(timeline_rate) != {"numerator", "denominator"}:
            raise EditingSkillHandoffError("timeline_rate fields differ")
        frame_rate = FrameRate(
            _require_integer(timeline_rate["numerator"], name="numerator", minimum=1),
            _require_integer(timeline_rate["denominator"], name="denominator", minimum=1),
        )
        raw_placements = document["placements"]
        if not isinstance(raw_placements, list):
            raise EditingSkillHandoffError("placements must be an array")
        placements: list[ResolveSubtitlePlacement] = []
        for raw in raw_placements:
            placement = _mapping(raw, name="placement")
            if set(placement) != {
                "cue_id",
                "record_range_frames",
                "text",
                "review_state",
            }:
                raise EditingSkillHandoffError("placement fields differ")
            frame_range = _mapping(
                placement["record_range_frames"],
                name="record_range_frames",
            )
            if set(frame_range) != {"start", "end_exclusive"}:
                raise EditingSkillHandoffError("record_range_frames fields differ")
            placements.append(
                ResolveSubtitlePlacement(
                    cue_id=_require_string(placement["cue_id"], name="cue_id"),
                    record_start_frame=_require_integer(
                        frame_range["start"], name="start", minimum=0
                    ),
                    record_end_frame=_require_integer(
                        frame_range["end_exclusive"],
                        name="end_exclusive",
                        minimum=1,
                    ),
                    text=_require_string(placement["text"], name="text"),
                    review_state=SubtitleReviewState(placement["review_state"]),
                )
            )
        reconstructed = ResolveSubtitlePlacementPlan(
            workspace_id=_require_string(document["workspace_id"], name="workspace_id"),
            workspace_revision=_require_integer(
                document["workspace_revision"],
                name="workspace_revision",
                minimum=0,
            ),
            source_workspace_sha256=_require_string(
                document["source_workspace_sha256"],
                name="source_workspace_sha256",
            ),
            timeline_rate=frame_rate,
            timeline_origin_frame=_require_integer(
                document["timeline_origin_frame"],
                name="timeline_origin_frame",
                minimum=0,
            ),
            track_index=_require_integer(
                document["track_index"], name="track_index", minimum=1
            ),
            placements=tuple(placements),
            ready_for_resolve_write=source_ready,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, EditingSkillHandoffError):
            raise
        raise EditingSkillHandoffError(
            "knowledge/commentary handoff semantics are invalid"
        ) from exc
    expected_ready = bool(placements) and all(
        item.review_state is SubtitleReviewState.APPROVED for item in placements
    )
    if source_ready is not expected_ready:
        raise EditingSkillHandoffError(
            "ready_for_resolve_write conflicts with placement review state"
        )
    if reconstructed.to_dict() != document:
        raise EditingSkillHandoffError("knowledge/commentary handoff differs")
    return EditingSkillHandoffEvidence(
        editing_mode=KNOWLEDGE_COMMENTARY,
        source_sha256=digest,
        source_owner="TASK-006",
        execution_owner="TASK-010",
        source_ready=source_ready,
        privacy_class="PRIVATE_SOURCE_BODY_REDACTED",
    )


def project_montage_handoff(
    value: Mapping[str, Any],
) -> EditingSkillHandoffEvidence:
    """Project a validated TASK-055 handoff without granting runtime authority."""

    try:
        document = parse_montage_resolve_handoff(value).to_dict()
    except (TypeError, ValueError) as exc:
        raise EditingSkillHandoffError("montage handoff is invalid") from exc
    if document["task_owner"] != "TASK-055":
        raise EditingSkillHandoffError("montage task_owner differs")
    if document["canonical_timeline_mapping_owner"] != "TASK-022":
        raise EditingSkillHandoffError("montage execution owner differs")
    if _require_bool(
        document["resolve_write_authorized"],
        name="resolve_write_authorized",
    ) is not False:
        raise EditingSkillHandoffError("montage handoff authorizes Resolve write")
    runtime_status = document["runtime_qa_status"]
    if not isinstance(runtime_status, str):
        raise EditingSkillHandoffError("runtime_qa_status must be a string")
    return EditingSkillHandoffEvidence(
        editing_mode=MONTAGE,
        source_sha256=document["handoff_sha256"],
        source_owner="TASK-055",
        execution_owner="TASK-022",
        source_ready=runtime_status == "PASS",
        privacy_class="PUBLIC_SAFE_METADATA_ONLY",
    )


def project_optional_editing_skill_handoff(
    *,
    editing_mode: str | None,
    value: Mapping[str, Any] | None,
) -> dict[str, object]:
    """Keep legacy callers safe when no optional skill handoff is supplied."""

    if editing_mode is None and value is None:
        body: dict[str, object] = {
            "evidence_version": "1.0.0",
            "editing_mode": None,
            "source_readiness": LEGACY_NOT_AVAILABLE,
            "source_payload_included": False,
            "canonical_timeline": False,
            "resolve_write_authorized": False,
            "runtime_authority_created": False,
        }
        body["evidence_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body
    if editing_mode is None or value is None:
        raise EditingSkillHandoffError("editing_mode and value must be supplied together")
    if editing_mode == KNOWLEDGE_COMMENTARY:
        return project_knowledge_commentary_handoff(value).to_dict()
    if editing_mode == MONTAGE:
        return project_montage_handoff(value).to_dict()
    raise EditingSkillHandoffError("editing_mode is unsupported")
