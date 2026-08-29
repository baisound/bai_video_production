from __future__ import annotations

from copy import deepcopy

import pytest

from ai_video_production.editing_skill_handoff import (
    KNOWLEDGE_COMMENTARY,
    LEGACY_NOT_AVAILABLE,
    MONTAGE,
    REVIEW_REQUIRED,
    SOURCE_READY,
    EditingSkillHandoffError,
    project_optional_editing_skill_handoff,
)
from ai_video_production.resolve_subtitle_handoff import ResolveSubtitleHandoffService
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.subtitle_workspace import (
    SubtitleOrigin,
    SubtitleReviewState,
    SubtitleWorkspace,
    WorkspaceCue,
)
from ai_video_production.timebase import FrameRate
from test_task055_montage_contract_recovery import _handoff, _plan, _proposal


def _knowledge_handoff(*, approved: bool = True) -> dict[str, object]:
    review_state = (
        SubtitleReviewState.APPROVED
        if approved
        else SubtitleReviewState.NEEDS_REVIEW
    )
    workspace = SubtitleWorkspace(
        "workspace-common-handoff",
        1,
        (
            WorkspaceCue(
                "cue-1",
                0,
                1_000,
                "private subtitle text",
                "private subtitle text",
                SubtitleOrigin.HUMAN,
                review_state,
            ),
        ),
    )
    return ResolveSubtitleHandoffService.build(
        workspace,
        timeline_rate=FrameRate(30),
    ).to_dict()


def _montage_handoff() -> dict[str, object]:
    proposal = _proposal()
    plan = _plan(proposal)
    return _handoff(proposal, plan)


def test_common_projection_redacts_private_knowledge_payload_and_keeps_authority_false() -> None:
    evidence = project_optional_editing_skill_handoff(
        editing_mode=KNOWLEDGE_COMMENTARY,
        value=_knowledge_handoff(),
    )
    assert evidence["editing_mode"] == KNOWLEDGE_COMMENTARY
    assert evidence["source_readiness"] == SOURCE_READY
    assert evidence["privacy_class"] == "PRIVATE_SOURCE_BODY_REDACTED"
    assert evidence["source_payload_included"] is False
    assert evidence["canonical_timeline"] is False
    assert evidence["resolve_write_authorized"] is False
    assert evidence["runtime_authority_created"] is False
    assert "private subtitle text" not in repr(evidence)
    assert evidence == project_optional_editing_skill_handoff(
        editing_mode=KNOWLEDGE_COMMENTARY,
        value=_knowledge_handoff(),
    )


def test_common_projection_keeps_montage_pending_until_runtime_qa() -> None:
    evidence = project_optional_editing_skill_handoff(
        editing_mode=MONTAGE,
        value=_montage_handoff(),
    )
    assert evidence["editing_mode"] == MONTAGE
    assert evidence["source_readiness"] == REVIEW_REQUIRED
    assert evidence["source_owner"] == "TASK-055"
    assert evidence["execution_owner"] == "TASK-022"
    assert evidence["resolve_write_authorized"] is False
    assert evidence["runtime_authority_created"] is False


def test_missing_optional_handoff_is_legacy_safe_and_non_authoritative() -> None:
    evidence = project_optional_editing_skill_handoff(
        editing_mode=None,
        value=None,
    )
    assert evidence["source_readiness"] == LEGACY_NOT_AVAILABLE
    assert evidence["source_payload_included"] is False
    assert evidence["canonical_timeline"] is False
    assert evidence["resolve_write_authorized"] is False
    assert evidence["runtime_authority_created"] is False


@pytest.mark.parametrize(
    ("editing_mode", "value"),
    [
        (KNOWLEDGE_COMMENTARY, None),
        (None, _knowledge_handoff()),
        ("UNKNOWN", _knowledge_handoff()),
    ],
)
def test_partial_or_unknown_optional_handoff_fails_closed(
    editing_mode: str | None,
    value: dict[str, object] | None,
) -> None:
    with pytest.raises(EditingSkillHandoffError):
        project_optional_editing_skill_handoff(
            editing_mode=editing_mode,
            value=value,
        )


def test_tampered_source_handoffs_fail_closed() -> None:
    knowledge = _knowledge_handoff()
    knowledge["ready_for_resolve_write"] = False
    with pytest.raises(EditingSkillHandoffError, match="plan_sha256 mismatch"):
        project_optional_editing_skill_handoff(
            editing_mode=KNOWLEDGE_COMMENTARY,
            value=knowledge,
        )

    montage = deepcopy(_montage_handoff())
    montage["runtime_qa_status"] = "PASS"
    with pytest.raises(EditingSkillHandoffError, match="montage handoff is invalid"):
        project_optional_editing_skill_handoff(
            editing_mode=MONTAGE,
            value=montage,
        )


def test_self_hashed_knowledge_readiness_cannot_bypass_human_review() -> None:
    knowledge = _knowledge_handoff(approved=False)
    knowledge["ready_for_resolve_write"] = True
    unsigned = {
        key: value for key, value in knowledge.items() if key != "plan_sha256"
    }
    knowledge["plan_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))

    with pytest.raises(
        EditingSkillHandoffError,
        match="ready_for_resolve_write conflicts with placement review state",
    ):
        project_optional_editing_skill_handoff(
            editing_mode=KNOWLEDGE_COMMENTARY,
            value=knowledge,
        )
