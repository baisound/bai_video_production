"""TASK-036 desktop shell state, command authorization and one-shot confirmation core.

This module contains no GUI toolkit dependency and performs no external mutation by
itself.  It is the transport-neutral boundary between the future desktop shell and
existing Product application services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import secrets
from typing import Any, Callable, Mapping

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


class WorkspaceId(str, Enum):
    PROJECT = "PROJECT"
    MEDIA = "MEDIA"
    EDIT = "EDIT"
    SUBTITLE = "SUBTITLE"
    REVIEW = "REVIEW"
    EXPORT = "EXPORT"
    PRODUCTION_CONTROL = "PRODUCTION_CONTROL"
    PLANNING = "PLANNING"
    GENERATION_SAFETY = "GENERATION_SAFETY"
    CONTINUITY = "CONTINUITY"
    PROMPT_EVIDENCE = "PROMPT_EVIDENCE"
    GENERATION_QUEUE = "GENERATION_QUEUE"


class CommandCategory(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOCAL_REVERSIBLE = "LOCAL_REVERSIBLE"
    LOCAL_DURABLE = "LOCAL_DURABLE"
    EXTERNAL_MUTATION = "EXTERNAL_MUTATION"
    HUMAN_FINAL_AUTHORITY = "HUMAN_FINAL_AUTHORITY"


@dataclass(frozen=True, slots=True)
class ShellCommandSpec:
    command_type: str
    category: CommandCategory
    requires_project: bool = True


_COMMAND_SPECS: dict[str, ShellCommandSpec] = {
    "project.open": ShellCommandSpec("project.open", CommandCategory.LOCAL_REVERSIBLE, False),
    "project.create": ShellCommandSpec("project.create", CommandCategory.LOCAL_DURABLE, False),
    "project.select_asset": ShellCommandSpec("project.select_asset", CommandCategory.LOCAL_REVERSIBLE),
    "media.choose_and_ingest": ShellCommandSpec("media.choose_and_ingest", CommandCategory.LOCAL_DURABLE),
    "media.normalize": ShellCommandSpec("media.normalize", CommandCategory.LOCAL_DURABLE),
    "transcription.start": ShellCommandSpec("transcription.start", CommandCategory.LOCAL_DURABLE),
    "transcription.cancel": ShellCommandSpec("transcription.cancel", CommandCategory.LOCAL_REVERSIBLE),
    "subtitle.import": ShellCommandSpec("subtitle.import", CommandCategory.LOCAL_DURABLE),
    "subtitle.save": ShellCommandSpec("subtitle.save", CommandCategory.LOCAL_DURABLE),
    "subtitle.update_cue": ShellCommandSpec("subtitle.update_cue", CommandCategory.LOCAL_DURABLE),
    "cut_candidates.generate": ShellCommandSpec("cut_candidates.generate", CommandCategory.LOCAL_DURABLE),
    "edit_candidate.review": ShellCommandSpec("edit_candidate.review", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "edit_plan.approve": ShellCommandSpec("edit_plan.approve", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "resolve.connection_check": ShellCommandSpec("resolve.connection_check", CommandCategory.READ_ONLY),
    "resolve.assembly.prepare": ShellCommandSpec("resolve.assembly.prepare", CommandCategory.READ_ONLY),
    "resolve.assembly.apply": ShellCommandSpec("resolve.assembly.apply", CommandCategory.EXTERNAL_MUTATION),
    "render.prepare": ShellCommandSpec("render.prepare", CommandCategory.READ_ONLY),
    "render.start": ShellCommandSpec("render.start", CommandCategory.EXTERNAL_MUTATION),
    "render.qa.inspect": ShellCommandSpec("render.qa.inspect", CommandCategory.READ_ONLY),
    "handoff.choose_destination": ShellCommandSpec("handoff.choose_destination", CommandCategory.LOCAL_REVERSIBLE),
    "handoff.create": ShellCommandSpec("handoff.create", CommandCategory.LOCAL_DURABLE),
    "handoff.open_folder": ShellCommandSpec("handoff.open_folder", CommandCategory.READ_ONLY),
    "settings.read": ShellCommandSpec("settings.read", CommandCategory.READ_ONLY, False),
    "settings.update": ShellCommandSpec("settings.update", CommandCategory.LOCAL_DURABLE, False),
    "production.snapshot": ShellCommandSpec("production.snapshot", CommandCategory.READ_ONLY),
    "production.candidate.register": ShellCommandSpec("production.candidate.register", CommandCategory.LOCAL_DURABLE),
    "production.candidate.ready_for_audit": ShellCommandSpec("production.candidate.ready_for_audit", CommandCategory.LOCAL_DURABLE),
    "production.lock.prepare": ShellCommandSpec("production.lock.prepare", CommandCategory.READ_ONLY),
    "production.lock.apply": ShellCommandSpec("production.lock.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "audit.snapshot": ShellCommandSpec("audit.snapshot", CommandCategory.READ_ONLY),
    "audit.decision.prepare": ShellCommandSpec("audit.decision.prepare", CommandCategory.READ_ONLY),
    "audit.decision.apply": ShellCommandSpec("audit.decision.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "audit.recovery.apply": ShellCommandSpec("audit.recovery.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "planning.snapshot": ShellCommandSpec("planning.snapshot", CommandCategory.READ_ONLY),
    "planning.go.prepare": ShellCommandSpec("planning.go.prepare", CommandCategory.READ_ONLY),
    "planning.go.apply": ShellCommandSpec("planning.go.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "planning.install.prepare": ShellCommandSpec("planning.install.prepare", CommandCategory.READ_ONLY),
    "planning.install.apply": ShellCommandSpec("planning.install.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "generation_safety.snapshot": ShellCommandSpec("generation_safety.snapshot", CommandCategory.READ_ONLY),
    "generation_safety.review.prepare": ShellCommandSpec("generation_safety.review.prepare", CommandCategory.READ_ONLY),
    "generation_safety.review.apply": ShellCommandSpec("generation_safety.review.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "continuity.snapshot": ShellCommandSpec("continuity.snapshot", CommandCategory.READ_ONLY),
    "continuity.edge.prepare": ShellCommandSpec("continuity.edge.prepare", CommandCategory.READ_ONLY),
    "continuity.edge.apply": ShellCommandSpec("continuity.edge.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "continuity.inspect": ShellCommandSpec("continuity.inspect", CommandCategory.LOCAL_DURABLE),
    "continuity.soft.prepare": ShellCommandSpec("continuity.soft.prepare", CommandCategory.READ_ONLY),
    "continuity.soft.apply": ShellCommandSpec("continuity.soft.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "continuity.stale.propagate": ShellCommandSpec("continuity.stale.propagate", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "continuity.recovery.apply": ShellCommandSpec("continuity.recovery.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "prompt_evidence.snapshot": ShellCommandSpec("prompt_evidence.snapshot", CommandCategory.READ_ONLY),
    "prompt_evidence.prompt.prepare": ShellCommandSpec("prompt_evidence.prompt.prepare", CommandCategory.READ_ONLY),
    "prompt_evidence.prompt.apply": ShellCommandSpec("prompt_evidence.prompt.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "prompt_evidence.attempt.prepare": ShellCommandSpec("prompt_evidence.attempt.prepare", CommandCategory.READ_ONLY),
    "prompt_evidence.attempt.apply": ShellCommandSpec("prompt_evidence.attempt.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "prompt_evidence.regeneration.prepare": ShellCommandSpec("prompt_evidence.regeneration.prepare", CommandCategory.READ_ONLY),
    "prompt_evidence.regeneration.apply": ShellCommandSpec("prompt_evidence.regeneration.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "prompt_evidence.recovery.apply": ShellCommandSpec("prompt_evidence.recovery.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "generation_queue.snapshot": ShellCommandSpec("generation_queue.snapshot", CommandCategory.READ_ONLY),
    "generation_queue.prepare": ShellCommandSpec("generation_queue.prepare", CommandCategory.READ_ONLY),
    "generation_queue.apply": ShellCommandSpec("generation_queue.apply", CommandCategory.HUMAN_FINAL_AUTHORITY),
    "generation_execution.snapshot": ShellCommandSpec("generation_execution.snapshot", CommandCategory.READ_ONLY),
    "generation_execution.prepare": ShellCommandSpec("generation_execution.prepare", CommandCategory.READ_ONLY),
    "generation_execution.apply": ShellCommandSpec("generation_execution.apply", CommandCategory.EXTERNAL_MUTATION),
}


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_HUMAN = "WAITING_HUMAN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ShellProjectContext:
    project_id: str
    display_name: str
    context_revision: int
    selected_asset_id: str | None = None
    resolve_project_name: str | None = None
    resolve_timeline_name: str | None = None

    def __post_init__(self) -> None:
        if not self.project_id.strip() or not self.display_name.strip():
            raise ValueError("project identity must be non-empty")
        if self.context_revision < 1:
            raise ValueError("context_revision must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "display_name": self.display_name,
            "context_revision": self.context_revision,
            "selected_asset_id": self.selected_asset_id,
            "resolve_project_name": self.resolve_project_name,
            "resolve_timeline_name": self.resolve_timeline_name,
        }


@dataclass(frozen=True, slots=True)
class JobSnapshot:
    job_id: str
    command_id: str
    stage: str
    state: JobState
    safe_cancel: bool
    progress_kind: str = "INDETERMINATE"
    progress_value: float | None = None
    error_code: str | None = None
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.command_id.strip() or not self.stage.strip():
            raise ValueError("job identity fields must be non-empty")
        if self.progress_value is not None and not 0.0 <= self.progress_value <= 1.0:
            raise ValueError("progress_value must be 0..1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "command_id": self.command_id,
            "stage": self.stage,
            "state": self.state.value,
            "safe_cancel": self.safe_cancel,
            "progress_kind": self.progress_kind,
            "progress_value": self.progress_value,
            "error_code": self.error_code,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class ShellSnapshot:
    product_version: str
    current_workspace: WorkspaceId
    project: ShellProjectContext | None
    active_jobs: tuple[JobSnapshot, ...]
    available_commands: tuple[str, ...]
    next_recommended_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "snapshot_version": "1.0.0",
            "task_owner": "TASK-036",
            "product_version": self.product_version,
            "current_workspace": self.current_workspace.value,
            "project": None if self.project is None else self.project.to_dict(),
            "active_jobs": [job.to_dict() for job in self.active_jobs],
            "available_commands": list(self.available_commands),
            "next_recommended_action": self.next_recommended_action,
        }
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class ShellCommand:
    command_id: str
    command_type: str
    project_id: str | None
    expected_context_revision: int | None
    expected_upstream_hashes: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    confirmation_id: str | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ShellCommand":
        allowed = {
            "command_id",
            "command_type",
            "project_id",
            "expected_context_revision",
            "expected_upstream_hashes",
            "payload",
            "confirmation_id",
        }
        if not isinstance(raw, Mapping) or set(raw) - allowed:
            raise ProductError(
                "ERR_SHELL_COMMAND_INVALID",
                "Shell command contains unsupported fields",
                ProductErrorCategory.VALIDATION,
            )
        command_id = raw.get("command_id")
        command_type = raw.get("command_type")
        if not isinstance(command_id, str) or not command_id.strip():
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "command_id must be non-empty text", ProductErrorCategory.VALIDATION)
        if not isinstance(command_type, str) or not command_type.strip():
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "command_type must be non-empty text", ProductErrorCategory.VALIDATION)
        project_id = raw.get("project_id")
        if project_id is not None and not isinstance(project_id, str):
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "project_id must be text or null", ProductErrorCategory.VALIDATION)
        revision = raw.get("expected_context_revision")
        if revision is not None and (not isinstance(revision, int) or isinstance(revision, bool) or revision < 1):
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "expected_context_revision must be a positive integer or null", ProductErrorCategory.VALIDATION)
        hashes = raw.get("expected_upstream_hashes", {})
        payload = raw.get("payload", {})
        if not isinstance(hashes, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in hashes.items()):
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "expected_upstream_hashes must be a text map", ProductErrorCategory.VALIDATION)
        if not isinstance(payload, Mapping):
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "payload must be an object", ProductErrorCategory.VALIDATION)
        confirmation_id = raw.get("confirmation_id")
        if confirmation_id is not None and not isinstance(confirmation_id, str):
            raise ProductError("ERR_SHELL_COMMAND_INVALID", "confirmation_id must be text or null", ProductErrorCategory.VALIDATION)
        return cls(
            command_id=command_id,
            command_type=command_type,
            project_id=project_id,
            expected_context_revision=revision,
            expected_upstream_hashes=dict(hashes),
            payload=dict(payload),
            confirmation_id=confirmation_id,
        )


@dataclass(slots=True)
class _PendingConfirmation:
    confirmation_id: str
    command_type: str
    project_id: str
    context_revision: int
    upstream_hashes_sha256: str
    target_application: str
    target_project: str | None
    target_timeline: str | None
    destination: str | None
    consumed: bool = False

    def public_dict(self) -> dict[str, Any]:
        return {
            "confirmation_id": self.confirmation_id,
            "command_type": self.command_type,
            "target_application": self.target_application,
            "target_project": self.target_project,
            "target_timeline": self.target_timeline,
            "destination": self.destination,
            "upstream_hashes_sha256": self.upstream_hashes_sha256,
            "expires_when_context_revision_changes": True,
        }


Executor = Callable[[ShellCommand], Mapping[str, Any]]
TokenFactory = Callable[[], str]
CommandPolicyProvider = Callable[[], tuple[str, ...]]


class BackgroundJobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobSnapshot] = {}

    def register(self, job: JobSnapshot) -> None:
        if job.job_id in self._jobs:
            raise ProductError("ERR_SHELL_JOB_CONFLICT", "job_id already exists", ProductErrorCategory.STATE)
        self._jobs[job.job_id] = job

    def replace(self, job: JobSnapshot) -> None:
        if job.job_id not in self._jobs:
            raise ProductError("ERR_SHELL_JOB_NOT_FOUND", "job_id does not exist", ProductErrorCategory.STATE)
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> JobSnapshot:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise ProductError("ERR_SHELL_JOB_NOT_FOUND", "job_id does not exist", ProductErrorCategory.STATE) from exc

    def active(self) -> tuple[JobSnapshot, ...]:
        terminal = {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}
        return tuple(job for job in self._jobs.values() if job.state not in terminal)

    def unsafe_active(self) -> tuple[JobSnapshot, ...]:
        return tuple(job for job in self.active() if not job.safe_cancel)


class ShellApplicationService:
    """Transport-neutral TASK-036 shell authority boundary.

    The service validates shell commands and confirmation tokens but delegates the
    actual Product operation to an explicitly supplied executor.
    """

    def __init__(
        self,
        *,
        product_version: str,
        token_factory: TokenFactory | None = None,
    ) -> None:
        if not product_version.strip():
            raise ValueError("product_version must be non-empty")
        self.product_version = product_version
        self.current_workspace = WorkspaceId.PROJECT
        self.project: ShellProjectContext | None = None
        self.jobs = BackgroundJobRegistry()
        self._context_revision = 0
        self._confirmations: dict[str, _PendingConfirmation] = {}
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._command_policy_provider: CommandPolicyProvider | None = None
        self.next_recommended_action: str | None = "project.open"

    @staticmethod
    def command_spec(command_type: str) -> ShellCommandSpec:
        try:
            return _COMMAND_SPECS[command_type]
        except KeyError as exc:
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_ALLOWED",
                "Unknown or non-allowlisted Shell command",
                ProductErrorCategory.AUTHORIZATION,
                details={"command_type": command_type},
            ) from exc

    def open_project_context(
        self,
        *,
        project_id: str,
        display_name: str,
        selected_asset_id: str | None = None,
        resolve_project_name: str | None = None,
        resolve_timeline_name: str | None = None,
    ) -> ShellProjectContext:
        self._context_revision += 1
        self._confirmations.clear()
        self.project = ShellProjectContext(
            project_id=project_id,
            display_name=display_name,
            context_revision=self._context_revision,
            selected_asset_id=selected_asset_id,
            resolve_project_name=resolve_project_name,
            resolve_timeline_name=resolve_timeline_name,
        )
        self.current_workspace = WorkspaceId.MEDIA
        self.next_recommended_action = "media.choose_and_ingest" if selected_asset_id is None else "transcription.start"
        return self.project

    def update_project_selection(self, *, selected_asset_id: str | None) -> ShellProjectContext:
        if self.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        self._context_revision += 1
        self._confirmations.clear()
        self.project = ShellProjectContext(
            project_id=self.project.project_id,
            display_name=self.project.display_name,
            context_revision=self._context_revision,
            selected_asset_id=selected_asset_id,
            resolve_project_name=self.project.resolve_project_name,
            resolve_timeline_name=self.project.resolve_timeline_name,
        )
        return self.project

    def bind_resolve_target(self, *, resolve_project_name: str, resolve_timeline_name: str) -> ShellProjectContext:
        """Bind the exact external Resolve target and invalidate stale confirmations."""
        if self.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        if not resolve_project_name.strip() or not resolve_timeline_name.strip():
            raise ProductError(
                "ERR_SHELL_RESOLVE_TARGET_INVALID",
                "Resolve Project and Timeline names must be non-empty",
                ProductErrorCategory.VALIDATION,
            )
        self._context_revision += 1
        self._confirmations.clear()
        self.project = ShellProjectContext(
            project_id=self.project.project_id,
            display_name=self.project.display_name,
            context_revision=self._context_revision,
            selected_asset_id=self.project.selected_asset_id,
            resolve_project_name=resolve_project_name.strip(),
            resolve_timeline_name=resolve_timeline_name.strip(),
        )
        return self.project

    def set_workspace(self, workspace: WorkspaceId | str) -> None:
        try:
            self.current_workspace = workspace if isinstance(workspace, WorkspaceId) else WorkspaceId(str(workspace))
        except ValueError as exc:
            raise ProductError("ERR_SHELL_WORKSPACE_INVALID", "Unknown desktop workspace", ProductErrorCategory.VALIDATION) from exc

    def bind_command_policy(self, provider: CommandPolicyProvider | None) -> None:
        """Bind an optional stage-aware allowlist provider.

        The provider narrows the static command registry; it can never make an
        unknown command executable.  TASK-036 uses this to turn EditingSession
        state into a real execution gate instead of a visual-only menu filter.
        """
        self._command_policy_provider = provider

    def advance_context_revision(self) -> ShellProjectContext:
        """Invalidate one-shot confirmations after an upstream state change."""
        if self.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        self._context_revision += 1
        self._confirmations.clear()
        self.project = ShellProjectContext(
            project_id=self.project.project_id,
            display_name=self.project.display_name,
            context_revision=self._context_revision,
            selected_asset_id=self.project.selected_asset_id,
            resolve_project_name=self.project.resolve_project_name,
            resolve_timeline_name=self.project.resolve_timeline_name,
        )
        return self.project

    def available_commands(self) -> tuple[str, ...]:
        base = []
        for command_type, spec in _COMMAND_SPECS.items():
            if spec.requires_project and self.project is None:
                continue
            base.append(command_type)
        if self._command_policy_provider is None:
            return tuple(base)
        try:
            policy = tuple(dict.fromkeys(self._command_policy_provider()))
        except ProductError:
            raise
        except Exception as exc:
            raise ProductError(
                "ERR_SHELL_COMMAND_POLICY_FAILED",
                "Shell command policy provider failed",
                ProductErrorCategory.INTERNAL,
                details={"exception_type": type(exc).__name__},
            ) from exc
        unknown = sorted(set(policy) - set(_COMMAND_SPECS))
        if unknown:
            raise ProductError(
                "ERR_SHELL_COMMAND_POLICY_INVALID",
                "Shell command policy returned unknown commands",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"unknown_commands": unknown},
            )
        allowed = set(policy)
        return tuple(command for command in base if command in allowed)

    def snapshot(self) -> ShellSnapshot:
        return ShellSnapshot(
            product_version=self.product_version,
            current_workspace=self.current_workspace,
            project=self.project,
            active_jobs=self.jobs.active(),
            available_commands=self.available_commands(),
            next_recommended_action=self.next_recommended_action,
        )

    @staticmethod
    def _hash_upstream(hashes: Mapping[str, str]) -> str:
        return sha256_bytes(canonical_json_bytes(dict(sorted(hashes.items()))))

    def prepare_confirmation(
        self,
        *,
        command_type: str,
        expected_upstream_hashes: Mapping[str, str],
        target_application: str,
        target_project: str | None = None,
        target_timeline: str | None = None,
        destination: str | None = None,
    ) -> dict[str, Any]:
        spec = self.command_spec(command_type)
        if spec.category not in {CommandCategory.EXTERNAL_MUTATION, CommandCategory.HUMAN_FINAL_AUTHORITY}:
            raise ProductError(
                "ERR_SHELL_CONFIRMATION_NOT_REQUIRED",
                "This Shell command does not use a mutation/final-authority confirmation",
                ProductErrorCategory.VALIDATION,
            )
        if self.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_SHELL_CONFIRMATION_TOKEN_INVALID", "Confirmation token factory returned an invalid token", ProductErrorCategory.INTERNAL)
        pending = _PendingConfirmation(
            confirmation_id=token,
            command_type=command_type,
            project_id=self.project.project_id,
            context_revision=self.project.context_revision,
            upstream_hashes_sha256=self._hash_upstream(expected_upstream_hashes),
            target_application=target_application,
            target_project=target_project,
            target_timeline=target_timeline,
            destination=destination,
        )
        self._confirmations[token] = pending
        return pending.public_dict()

    def _validate_context(self, command: ShellCommand, spec: ShellCommandSpec) -> None:
        if spec.requires_project:
            if self.project is None:
                raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
            if command.project_id != self.project.project_id:
                raise ProductError(
                    "ERR_SHELL_PROJECT_CONTEXT_STALE",
                    "Shell command targets a different Project than the current context",
                    ProductErrorCategory.STATE,
                )
            if command.expected_context_revision != self.project.context_revision:
                raise ProductError(
                    "ERR_SHELL_CONTEXT_STALE",
                    "Shell command was created against an older Project context",
                    ProductErrorCategory.STATE,
                    details={"current_context_revision": self.project.context_revision},
                )
        elif command.project_id is not None and self.project is not None and command.project_id != self.project.project_id:
            raise ProductError("ERR_SHELL_PROJECT_CONTEXT_STALE", "Shell command Project identity is stale", ProductErrorCategory.STATE)

    def _consume_confirmation(self, command: ShellCommand, spec: ShellCommandSpec) -> None:
        if spec.category not in {CommandCategory.EXTERNAL_MUTATION, CommandCategory.HUMAN_FINAL_AUTHORITY}:
            return
        if self.project is None:
            raise ProductError("ERR_SHELL_PROJECT_REQUIRED", "No Project is open", ProductErrorCategory.STATE)
        if not command.confirmation_id:
            raise ProductError(
                "ERR_SHELL_CONFIRMATION_REQUIRED",
                "This Shell command requires an exact one-shot confirmation",
                ProductErrorCategory.AUTHORIZATION,
            )
        pending = self._confirmations.get(command.confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError(
                "ERR_SHELL_CONFIRMATION_INVALID",
                "Shell confirmation is missing, expired, or already used",
                ProductErrorCategory.AUTHORIZATION,
            )
        if (
            pending.command_type != command.command_type
            or pending.project_id != self.project.project_id
            or pending.context_revision != self.project.context_revision
            or pending.upstream_hashes_sha256 != self._hash_upstream(command.expected_upstream_hashes)
        ):
            raise ProductError(
                "ERR_SHELL_CONFIRMATION_STALE",
                "Shell confirmation no longer matches the exact Product context",
                ProductErrorCategory.AUTHORIZATION,
            )
        # One-shot even when the downstream executor later fails. Ambiguous external
        # state must be inspected before a new authorization is issued.
        pending.consumed = True

    def authorize(self, command: ShellCommand) -> ShellCommandSpec:
        spec = self.command_spec(command.command_type)
        self._validate_context(command, spec)
        if self._command_policy_provider is not None and command.command_type not in self.available_commands():
            raise ProductError(
                "ERR_SHELL_COMMAND_NOT_AVAILABLE_IN_STAGE",
                "Shell command is not available in the current editing stage",
                ProductErrorCategory.AUTHORIZATION,
                details={"command_type": command.command_type},
            )
        self._consume_confirmation(command, spec)
        return spec

    def dispatch(self, command: ShellCommand, *, executor: Executor) -> dict[str, Any]:
        spec = self.authorize(command)
        try:
            result = executor(command)
        except ProductError:
            raise
        except Exception as exc:
            raise ProductError(
                "ERR_SHELL_COMMAND_EXECUTION_FAILED",
                "Shell Application Service command execution failed",
                ProductErrorCategory.INTERNAL,
                details={"exception_type": type(exc).__name__, "command_type": command.command_type},
            ) from exc
        if not isinstance(result, Mapping):
            raise ProductError(
                "ERR_SHELL_COMMAND_RESULT_INVALID",
                "Shell command executor must return an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return {
            "receipt_version": "1.0.0",
            "command_id": command.command_id,
            "command_type": command.command_type,
            "category": spec.category.value,
            "result": dict(result),
        }

    def close_guard(self) -> dict[str, Any]:
        unsafe = self.jobs.unsafe_active()
        if unsafe:
            return {
                "can_close_immediately": False,
                "unsafe_job_ids": [job.job_id for job in unsafe],
                "message": "An external or non-cancellable job is still active; inspect before closing.",
            }
        return {"can_close_immediately": True, "unsafe_job_ids": [], "message": None}
