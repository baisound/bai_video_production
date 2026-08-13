"""TASK-036 minimum editing workflow stage reducer.

The reducer tracks artifact identities only. It does not own the underlying media,
transcript, edit plan, Resolve timeline, render, or handoff bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory


_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")


def _sha_or_none(value: str | None, name: str) -> None:
    if value is not None and not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} must be sha256:... or null")


def _id_or_none(value: str | None, name: str) -> None:
    if value is not None and not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")


class EditingStage(str, Enum):
    PROJECT = "PROJECT"
    MEDIA = "MEDIA"
    TRANSCRIPT = "TRANSCRIPT"
    SUBTITLE = "SUBTITLE"
    CUT_REVIEW = "CUT_REVIEW"
    EDIT_PLAN = "EDIT_PLAN"
    RESOLVE = "RESOLVE"
    RENDER_QA = "RENDER_QA"
    HANDOFF = "HANDOFF"


@dataclass(frozen=True, slots=True)
class EditingSessionState:
    project_id: str
    revision: int = 1
    source_asset_id: str | None = None
    source_asset_sha256: str | None = None
    transcript_sha256: str | None = None
    subtitle_workspace_sha256: str | None = None
    cut_candidate_manifest_sha256: str | None = None
    edit_plan_sha256: str | None = None
    edit_plan_approved: bool = False
    resolve_assembly_sha256: str | None = None
    resolve_applied: bool = False
    render_qa_sha256: str | None = None
    render_qa_status: str | None = None
    handoff_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.project_id):
            raise ValueError("project_id is invalid")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        _id_or_none(self.source_asset_id, "source_asset_id")
        for name, value in (
            ("source_asset_sha256", self.source_asset_sha256),
            ("transcript_sha256", self.transcript_sha256),
            ("subtitle_workspace_sha256", self.subtitle_workspace_sha256),
            ("cut_candidate_manifest_sha256", self.cut_candidate_manifest_sha256),
            ("edit_plan_sha256", self.edit_plan_sha256),
            ("resolve_assembly_sha256", self.resolve_assembly_sha256),
            ("render_qa_sha256", self.render_qa_sha256),
            ("handoff_manifest_sha256", self.handoff_manifest_sha256),
        ):
            _sha_or_none(value, name)
        if self.source_asset_id is None and self.source_asset_sha256 is not None:
            raise ValueError("source hash requires source_asset_id")
        if self.edit_plan_approved and self.edit_plan_sha256 is None:
            raise ValueError("approved edit plan requires edit_plan_sha256")
        if self.resolve_applied and self.resolve_assembly_sha256 is None:
            raise ValueError("resolve_applied requires resolve_assembly_sha256")
        if self.render_qa_status not in {None, "PASS", "FAIL"}:
            raise ValueError("render_qa_status must be PASS/FAIL/null")
        if self.render_qa_status is not None and self.render_qa_sha256 is None:
            raise ValueError("render QA status requires report hash")
        if self.handoff_manifest_sha256 is not None and self.render_qa_status != "PASS":
            raise ValueError("handoff requires passing render QA")

    @property
    def current_stage(self) -> EditingStage:
        if self.handoff_manifest_sha256 is not None:
            return EditingStage.HANDOFF
        if self.render_qa_sha256 is not None:
            return EditingStage.RENDER_QA
        if self.resolve_assembly_sha256 is not None:
            return EditingStage.RESOLVE
        if self.edit_plan_sha256 is not None:
            return EditingStage.EDIT_PLAN
        if self.cut_candidate_manifest_sha256 is not None:
            return EditingStage.CUT_REVIEW
        if self.subtitle_workspace_sha256 is not None:
            return EditingStage.SUBTITLE
        if self.transcript_sha256 is not None:
            return EditingStage.TRANSCRIPT
        if self.source_asset_id is not None:
            return EditingStage.MEDIA
        return EditingStage.PROJECT

    @property
    def next_recommended_action(self) -> str:
        if self.source_asset_id is None:
            return "media.choose_and_ingest"
        if self.transcript_sha256 is None:
            return "transcription.start"
        # Subtitle is part of the preferred minimum-editing flow, but once a cut
        # review artifact already exists it must not pull the workflow backwards.
        # TASK-010 permits subtitle to be absent, so an approved Edit Plan may
        # continue toward Resolve while Subtitle remains optional/unfinished.
        if self.subtitle_workspace_sha256 is None and self.cut_candidate_manifest_sha256 is None:
            return "subtitle.save"
        if self.cut_candidate_manifest_sha256 is None:
            return "cut_candidates.generate"
        if self.edit_plan_sha256 is None or not self.edit_plan_approved:
            return "edit_plan.approve"
        if self.resolve_assembly_sha256 is None:
            return "resolve.assembly.prepare"
        if not self.resolve_applied:
            return "resolve.assembly.apply"
        if self.render_qa_sha256 is None:
            return "render.start"
        if self.render_qa_status != "PASS":
            return "render.qa.inspect"
        if self.handoff_manifest_sha256 is None:
            return "handoff.create"
        return "NONE"

    def available_commands(self) -> tuple[str, ...]:
        commands = ["settings.read", "resolve.connection_check"]
        if self.source_asset_id is None:
            commands += ["media.choose_and_ingest"]
        else:
            commands += ["project.select_asset", "transcription.start"]
        if self.transcript_sha256 is not None:
            commands += ["subtitle.import", "subtitle.save", "subtitle.update_cue", "cut_candidates.generate"]
        if self.cut_candidate_manifest_sha256 is not None:
            commands += ["edit_candidate.review", "edit_plan.approve"]
        if self.edit_plan_sha256 is not None and self.edit_plan_approved:
            commands += ["resolve.assembly.prepare"]
        if self.resolve_assembly_sha256 is not None:
            commands += ["resolve.assembly.apply"]
        if self.resolve_applied:
            commands += ["render.prepare", "render.start"]
        if self.render_qa_sha256 is not None:
            commands += ["render.qa.inspect"]
        if self.render_qa_status == "PASS":
            commands += ["handoff.choose_destination", "handoff.create"]
        if self.handoff_manifest_sha256 is not None:
            commands += ["handoff.open_folder"]
        return tuple(dict.fromkeys(commands))

    def _next(self, **changes: Any) -> "EditingSessionState":
        return replace(self, revision=self.revision + 1, **changes)

    def bind_source(self, *, asset_id: str, asset_sha256: str) -> "EditingSessionState":
        if not _ID_RE.fullmatch(asset_id) or not _SHA_RE.fullmatch(asset_sha256):
            raise ValueError("source identity is invalid")
        # A source change invalidates every downstream artifact rather than silently
        # carrying stale plans/render evidence into the new context.
        return self._next(
            source_asset_id=asset_id,
            source_asset_sha256=asset_sha256,
            transcript_sha256=None,
            subtitle_workspace_sha256=None,
            cut_candidate_manifest_sha256=None,
            edit_plan_sha256=None,
            edit_plan_approved=False,
            resolve_assembly_sha256=None,
            resolve_applied=False,
            render_qa_sha256=None,
            render_qa_status=None,
            handoff_manifest_sha256=None,
        )

    def bind_transcript(self, transcript_sha256: str) -> "EditingSessionState":
        if self.source_asset_id is None:
            raise ProductError("ERR_SHELL_SOURCE_REQUIRED", "Transcript requires a selected source Asset", ProductErrorCategory.STATE)
        return self._next(
            transcript_sha256=transcript_sha256,
            subtitle_workspace_sha256=None,
            cut_candidate_manifest_sha256=None,
            edit_plan_sha256=None,
            edit_plan_approved=False,
            resolve_assembly_sha256=None,
            resolve_applied=False,
            render_qa_sha256=None,
            render_qa_status=None,
            handoff_manifest_sha256=None,
        )

    def bind_subtitle_workspace(self, workspace_sha256: str) -> "EditingSessionState":
        if self.transcript_sha256 is None:
            raise ProductError("ERR_SHELL_TRANSCRIPT_REQUIRED", "Subtitle Workspace requires transcript context", ProductErrorCategory.STATE)
        return self._next(subtitle_workspace_sha256=workspace_sha256)

    def bind_cut_candidates(self, manifest_sha256: str) -> "EditingSessionState":
        if self.transcript_sha256 is None:
            raise ProductError("ERR_SHELL_TRANSCRIPT_REQUIRED", "Cut candidates require transcript/source analysis context", ProductErrorCategory.STATE)
        return self._next(
            cut_candidate_manifest_sha256=manifest_sha256,
            edit_plan_sha256=None,
            edit_plan_approved=False,
            resolve_assembly_sha256=None,
            resolve_applied=False,
            render_qa_sha256=None,
            render_qa_status=None,
            handoff_manifest_sha256=None,
        )

    def bind_edit_plan(self, *, plan_sha256: str, approved: bool) -> "EditingSessionState":
        if self.cut_candidate_manifest_sha256 is None:
            raise ProductError("ERR_SHELL_CUT_CANDIDATES_REQUIRED", "Edit Plan requires Cut Candidate context", ProductErrorCategory.STATE)
        return self._next(
            edit_plan_sha256=plan_sha256,
            edit_plan_approved=approved,
            resolve_assembly_sha256=None,
            resolve_applied=False,
            render_qa_sha256=None,
            render_qa_status=None,
            handoff_manifest_sha256=None,
        )

    def bind_resolve_assembly(self, assembly_sha256: str) -> "EditingSessionState":
        if not self.edit_plan_approved or self.edit_plan_sha256 is None:
            raise ProductError("ERR_SHELL_APPROVED_EDIT_PLAN_REQUIRED", "Resolve assembly requires approved Edit Plan", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        return self._next(
            resolve_assembly_sha256=assembly_sha256,
            resolve_applied=False,
            render_qa_sha256=None,
            render_qa_status=None,
            handoff_manifest_sha256=None,
        )

    def mark_resolve_applied(self) -> "EditingSessionState":
        if self.resolve_assembly_sha256 is None:
            raise ProductError("ERR_SHELL_RESOLVE_ASSEMBLY_REQUIRED", "Resolve apply requires compiled assembly", ProductErrorCategory.STATE)
        return self._next(resolve_applied=True, render_qa_sha256=None, render_qa_status=None, handoff_manifest_sha256=None)

    def bind_render_qa(self, *, report_sha256: str, status: str) -> "EditingSessionState":
        if not self.resolve_applied:
            raise ProductError("ERR_SHELL_RESOLVE_APPLY_REQUIRED", "Render QA requires applied Resolve assembly", ProductErrorCategory.STATE)
        if status not in {"PASS", "FAIL"}:
            raise ValueError("render QA status must be PASS or FAIL")
        return self._next(render_qa_sha256=report_sha256, render_qa_status=status, handoff_manifest_sha256=None)

    def bind_handoff(self, manifest_sha256: str) -> "EditingSessionState":
        if self.render_qa_status != "PASS":
            raise ProductError("ERR_SHELL_RENDER_QA_PASS_REQUIRED", "EDITOR_WORK handoff requires PASS Render QA", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        return self._next(handoff_manifest_sha256=manifest_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_version": "1.0.0",
            "task_owner": "TASK-036",
            "project_id": self.project_id,
            "revision": self.revision,
            "current_stage": self.current_stage.value,
            "source_asset_id": self.source_asset_id,
            "source_asset_sha256": self.source_asset_sha256,
            "transcript_sha256": self.transcript_sha256,
            "subtitle_workspace_sha256": self.subtitle_workspace_sha256,
            "cut_candidate_manifest_sha256": self.cut_candidate_manifest_sha256,
            "edit_plan_sha256": self.edit_plan_sha256,
            "edit_plan_approved": self.edit_plan_approved,
            "resolve_assembly_sha256": self.resolve_assembly_sha256,
            "resolve_applied": self.resolve_applied,
            "render_qa_sha256": self.render_qa_sha256,
            "render_qa_status": self.render_qa_status,
            "handoff_manifest_sha256": self.handoff_manifest_sha256,
            "available_commands": list(self.available_commands()),
            "next_recommended_action": self.next_recommended_action,
        }
