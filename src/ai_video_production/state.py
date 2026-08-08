from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .errors import ProductError, ProductErrorCategory
from .checkpoint import CheckpointRecord, ResumeContext, assert_resume_compatible

class ProductionJobState(str, Enum):
    CREATED = "CREATED"
    INGESTING = "INGESTING"
    NORMALIZING = "NORMALIZING"
    ANALYZING = "ANALYZING"
    CANDIDATES_READY = "CANDIDATES_READY"
    PLAN_REVIEW = "PLAN_REVIEW"
    PLAN_APPROVED = "PLAN_APPROVED"
    ASSET_PREPARING = "ASSET_PREPARING"
    RESOLVE_ASSEMBLING = "RESOLVE_ASSEMBLING"
    AUTO_QA = "AUTO_QA"
    READY_FOR_MANUAL_EDIT = "READY_FOR_MANUAL_EDIT"
    MANUAL_EDITING = "MANUAL_EDITING"
    READY_FOR_RENDER = "READY_FOR_RENDER"
    RENDERING = "RENDERING"
    RENDER_QA = "RENDER_QA"
    COMPLETED = "COMPLETED"
    WAITING_RESOURCE = "WAITING_RESOURCE"
    WAITING_HUMAN = "WAITING_HUMAN"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

TERMINAL_STATES = {ProductionJobState.COMPLETED, ProductionJobState.CANCELLED}

_FORWARD: dict[ProductionJobState, set[ProductionJobState]] = {
    ProductionJobState.CREATED: {ProductionJobState.INGESTING},
    ProductionJobState.INGESTING: {ProductionJobState.NORMALIZING},
    ProductionJobState.NORMALIZING: {ProductionJobState.ANALYZING},
    ProductionJobState.ANALYZING: {ProductionJobState.CANDIDATES_READY},
    ProductionJobState.CANDIDATES_READY: {ProductionJobState.PLAN_REVIEW},
    ProductionJobState.PLAN_REVIEW: {ProductionJobState.PLAN_APPROVED},
    ProductionJobState.PLAN_APPROVED: {ProductionJobState.ASSET_PREPARING},
    ProductionJobState.ASSET_PREPARING: {ProductionJobState.RESOLVE_ASSEMBLING},
    ProductionJobState.RESOLVE_ASSEMBLING: {ProductionJobState.AUTO_QA},
    ProductionJobState.AUTO_QA: {ProductionJobState.READY_FOR_MANUAL_EDIT},
    ProductionJobState.READY_FOR_MANUAL_EDIT: {ProductionJobState.MANUAL_EDITING},
    ProductionJobState.MANUAL_EDITING: {ProductionJobState.READY_FOR_RENDER},
    ProductionJobState.READY_FOR_RENDER: {ProductionJobState.RENDERING},
    ProductionJobState.RENDERING: {ProductionJobState.RENDER_QA},
    ProductionJobState.RENDER_QA: {ProductionJobState.COMPLETED},
}

_RESOURCE_WAIT_ALLOWED = {
    ProductionJobState.INGESTING, ProductionJobState.NORMALIZING,
    ProductionJobState.ANALYZING, ProductionJobState.ASSET_PREPARING,
    ProductionJobState.RESOLVE_ASSEMBLING, ProductionJobState.RENDERING,
}
_HUMAN_WAIT_ALLOWED = {
    ProductionJobState.INGESTING, ProductionJobState.PLAN_REVIEW,
    ProductionJobState.AUTO_QA, ProductionJobState.READY_FOR_MANUAL_EDIT,
    ProductionJobState.READY_FOR_RENDER, ProductionJobState.RENDER_QA,
}
_RESUME_SOURCES = {
    ProductionJobState.WAITING_RESOURCE, ProductionJobState.WAITING_HUMAN,
    ProductionJobState.PAUSED, ProductionJobState.FAILED,
}

@dataclass(frozen=True, slots=True)
class JobStateSnapshot:
    job_id: str
    state: ProductionJobState
    state_version: int
    profile_snapshot_id: str
    resume_to_state: ProductionJobState | None = None
    last_error_code: str | None = None

class JobStateRepository(Protocol):
    def get_job_state(self, job_id: str) -> JobStateSnapshot: ...
    def _transition_job_state(self, job_id: str, *, from_state: ProductionJobState, to_state: ProductionJobState,
                              expected_version: int, resume_to_state: ProductionJobState | None,
                              last_error_code: str | None) -> JobStateSnapshot: ...
    def _resume_job_state(self, job_id: str, *, from_state: ProductionJobState, target_state: ProductionJobState,
                          expected_version: int) -> JobStateSnapshot: ...

class JobStateService:
    def __init__(self, repository: JobStateRepository) -> None:
        self._repository = repository

    @staticmethod
    def legal_targets(snapshot: JobStateSnapshot) -> set[ProductionJobState]:
        state = snapshot.state
        if state in TERMINAL_STATES:
            return set()
        if state is ProductionJobState.RESUMING:
            return {snapshot.resume_to_state} if snapshot.resume_to_state else set()
        if state in _RESUME_SOURCES:
            return {ProductionJobState.RESUMING, ProductionJobState.CANCELLED}
        targets = set(_FORWARD.get(state, set()))
        targets.update({ProductionJobState.PAUSED, ProductionJobState.FAILED, ProductionJobState.CANCELLED})
        if state in _RESOURCE_WAIT_ALLOWED:
            targets.add(ProductionJobState.WAITING_RESOURCE)
        if state in _HUMAN_WAIT_ALLOWED:
            targets.add(ProductionJobState.WAITING_HUMAN)
        return targets

    def transition(self, job_id: str, to_state: ProductionJobState | str, *, expected_version: int,
                   resume_to_state: ProductionJobState | str | None = None,
                   error_code: str | None = None) -> JobStateSnapshot:
        to_state = ProductionJobState(to_state)
        snapshot = self._repository.get_job_state(job_id)
        if to_state is ProductionJobState.RESUMING or snapshot.state is ProductionJobState.RESUMING:
            raise ProductError(
                "ERR_STATE_RESUME_API_REQUIRED",
                "checkpoint-gated resume_from_checkpoint() is required for RESUMING transitions",
                ProductErrorCategory.STATE,
            )
        if snapshot.state_version != expected_version:
            raise ProductError(
                "ERR_STATE_STALE_REVISION", "job state revision conflict", ProductErrorCategory.STATE,
                details={"expected": expected_version, "actual": snapshot.state_version},
            )
        allowed = self.legal_targets(snapshot)
        if to_state not in allowed:
            raise ProductError(
                "ERR_STATE_INVALID_TRANSITION", f"illegal transition {snapshot.state.value}->{to_state.value}",
                ProductErrorCategory.STATE, details={"allowed": sorted(s.value for s in allowed)},
            )

        next_resume: ProductionJobState | None = None
        if to_state in {ProductionJobState.PAUSED, ProductionJobState.WAITING_HUMAN, ProductionJobState.WAITING_RESOURCE, ProductionJobState.FAILED}:
            if resume_to_state is None:
                # Default to the interrupted state. A later checkpoint gate decides
                # whether actual resume is permitted.
                next_resume = snapshot.state
            else:
                next_resume = ProductionJobState(resume_to_state)
                if next_resume in TERMINAL_STATES or next_resume in _RESUME_SOURCES or next_resume is ProductionJobState.RESUMING:
                    raise ProductError("ERR_STATE_INVALID_RESUME_TARGET", "invalid resume target", ProductErrorCategory.STATE)
        elif snapshot.state in _RESUME_SOURCES and to_state is ProductionJobState.RESUMING:
            next_resume = snapshot.resume_to_state
            if next_resume is None:
                raise ProductError("ERR_STATE_RESUME_TARGET_MISSING", "resume target is missing", ProductErrorCategory.STATE)
        elif snapshot.state is ProductionJobState.RESUMING:
            next_resume = None

        if to_state is ProductionJobState.FAILED and not error_code:
            raise ProductError("ERR_STATE_FAILURE_CODE_REQUIRED", "FAILED transition requires error_code", ProductErrorCategory.VALIDATION)

        return self._repository._transition_job_state(
            job_id, from_state=snapshot.state, to_state=to_state, expected_version=expected_version,
            resume_to_state=next_resume, last_error_code=error_code if to_state is ProductionJobState.FAILED else None,
        )

    def resume_from_checkpoint(
        self,
        job_id: str,
        *,
        expected_version: int,
        checkpoint: CheckpointRecord,
        current: ResumeContext,
    ) -> JobStateSnapshot:
        snapshot = self._repository.get_job_state(job_id)
        if snapshot.state_version != expected_version:
            raise ProductError(
                "ERR_STATE_STALE_REVISION", "job state revision conflict", ProductErrorCategory.STATE,
                details={"expected": expected_version, "actual": snapshot.state_version},
            )
        if snapshot.state not in _RESUME_SOURCES or snapshot.resume_to_state is None:
            raise ProductError("ERR_STATE_RESUME_NOT_AVAILABLE", "job is not in a resumable side state", ProductErrorCategory.STATE)
        if checkpoint.production_job_id != job_id:
            raise ProductError("ERR_INTEGRITY_CHECKPOINT_JOB_MISMATCH", "checkpoint belongs to another job", ProductErrorCategory.DATA_INTEGRITY)
        if checkpoint.profile_snapshot_id != snapshot.profile_snapshot_id or current.profile_snapshot_id != snapshot.profile_snapshot_id:
            raise ProductError(
                "ERR_INTEGRITY_CHECKPOINT_PROFILE_MISMATCH",
                "checkpoint/current profile snapshot is not the immutable profile bound to the job",
                ProductErrorCategory.DATA_INTEGRITY,
                details={
                    "job_profile_snapshot_id": snapshot.profile_snapshot_id,
                    "checkpoint_profile_snapshot_id": checkpoint.profile_snapshot_id,
                    "current_profile_snapshot_id": current.profile_snapshot_id,
                },
            )
        if checkpoint.resume_state != snapshot.resume_to_state.value:
            raise ProductError(
                "ERR_INTEGRITY_CHECKPOINT_STATE_MISMATCH", "checkpoint resume state does not match job resume target",
                ProductErrorCategory.DATA_INTEGRITY, details={"checkpoint": checkpoint.resume_state, "job": snapshot.resume_to_state.value},
            )
        assert_resume_compatible(checkpoint, current)
        # RESUMING is a logical bridge, but persistence must not expose a crash
        # window where the job can become stranded in RESUMING. The repository
        # therefore commits side-state -> target atomically while consuming two
        # state revisions (side -> RESUMING -> target).
        return self._repository._resume_job_state(
            job_id, from_state=snapshot.state, target_state=snapshot.resume_to_state,
            expected_version=expected_version,
        )
