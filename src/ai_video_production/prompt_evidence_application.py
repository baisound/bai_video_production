"""TASK-040 durable Prompt / Generation Evidence Product application.

This application records body-free Prompt metadata and already-produced
Generation Evidence. It never calls a Provider, creates media/Candidates, or
grants paid execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
from typing import Any, Callable

from .atomic import AtomicJsonWriter
from .audit_application import Task038AuditApplication
from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision
from .candidate_audit_store import CandidateAuditSnapshotStore
from .errors import ProductError, ProductErrorCategory
from .generation_output_binding import GenerationOutputProductionBinding
from .production_control import ProductionControlRegistry
from .production_control_application import Task037ProductionControlApplication
from .production_control_store import ProductionControlSnapshotStore, _exclusive_snapshot_lock
from .prompt_registry import (
    GenerationAttempt,
    GenerationResult,
    PromptEntity,
    PromptGenerationRegistry,
    RegenerationStrategy,
)
from .prompt_registry_store import PromptRegistrySnapshotStore
from .regeneration_planning import HumanRegenerationPlanner
from .regeneration_prompt_draft import RegenerationPromptDraft, RegenerationPromptDraftService
from .serialization import canonical_json_bytes, sha256_bytes


TokenFactory = Callable[[], str]
FailureInjector = Callable[[str], None]
_PROMPT_NAME = "prompt-registry.json"
_AUDIT_NAME = "candidate-audit.json"
_TRANSACTION_NAME = "task040-attempt-transaction.json"
_MAX_TRANSACTION_BYTES = 256 * 1024
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_ATTEMPT_FIELDS = {
    "generation_job_id", "slot_id", "prompt_id", "prompt_version", "prompt_sha256",
    "provider_id", "model_id", "provider_profile_version", "strategy_level", "result",
    "failure_codes", "output_candidate_id", "parent_attempt_id", "input_asset_hashes",
    "cost", "latency_ms",
}
_TRANSACTION_FIELDS = {
    "transaction_version", "task_owner", "transaction_id", "project_id", "state",
    "confirmation_id_sha256", "attempt", "old_prompt_sha256", "new_prompt_sha256",
    "old_production_sha256", "new_production_sha256", "transaction_sha256",
}


@dataclass(slots=True)
class _PendingPrompt:
    confirmation_id: str
    prompt: PromptEntity
    prompt_sha256: str
    production_sha256: str
    consumed: bool = False


@dataclass(slots=True)
class _PendingAttempt:
    confirmation_id: str
    attempt: GenerationAttempt
    old_prompt_sha256: str
    new_prompt_sha256: str
    old_production_sha256: str
    new_production_sha256: str
    production_binding_required: bool
    consumed: bool = False


@dataclass(slots=True)
class _PendingRegeneration:
    confirmation_id: str
    candidate_id: str
    draft: RegenerationPromptDraft
    plan_sha256: str
    repeated_failure_threshold: int
    prompt_sha256: str
    production_sha256: str
    audit_sha256: str
    consumed: bool = False


class Task040PromptEvidenceApplication:
    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        production_control: Task037ProductionControlApplication | None = None,
        audit_application: Task038AuditApplication | None = None,
        token_factory: TokenFactory | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError("ERR_PROMPT_APPLICATION_PROJECT_ROOT_INVALID", "Prompt Evidence project root must be an existing regular directory", ProductErrorCategory.VALIDATION)
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProductError("ERR_PROMPT_APPLICATION_PROJECT_ID_INVALID", "Prompt Evidence project_id must be non-empty text", ProductErrorCategory.VALIDATION)
        if production_control is not None and (production_control.project_root != root or production_control.project_id != project_id):
            raise ProductError("ERR_PROMPT_APPLICATION_PRODUCTION_SCOPE_MISMATCH", "Prompt Evidence and Production Control scope must match", ProductErrorCategory.SECURITY)
        if audit_application is not None and (audit_application.project_root != root or audit_application.project_id != project_id):
            raise ProductError("ERR_PROMPT_APPLICATION_AUDIT_SCOPE_MISMATCH", "Prompt Evidence and Audit scope must match", ProductErrorCategory.SECURITY)
        self.project_root = root
        self.project_id = project_id
        self.production_control = production_control or Task037ProductionControlApplication(project_root=root, project_id=project_id)
        self.audit_application = audit_application or Task038AuditApplication(project_root=root, project_id=project_id)
        self.prompt_path = root / _PROMPT_NAME
        self.audit_path = root / _AUDIT_NAME
        self.transaction_path = root / _TRANSACTION_NAME
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._failure_injector = failure_injector
        self._prompt_confirmations: dict[str, _PendingPrompt] = {}
        self._attempt_confirmations: dict[str, _PendingAttempt] = {}
        self._regeneration_confirmations: dict[str, _PendingRegeneration] = {}

    @staticmethod
    def _prompt_hash(registry: PromptGenerationRegistry) -> str:
        return str(PromptRegistrySnapshotStore.snapshot(registry)["snapshot_sha256"])

    @staticmethod
    def _production_hash(registry: ProductionControlRegistry) -> str:
        return str(ProductionControlSnapshotStore.snapshot(registry)["snapshot_sha256"])

    @staticmethod
    def _audit_hash(registry: CandidateAuditRegistry) -> str:
        return str(CandidateAuditSnapshotStore.snapshot(registry)["snapshot_sha256"])

    def _load_prompts(self) -> tuple[PromptGenerationRegistry, str, bool]:
        if self.prompt_path.exists():
            value = PromptRegistrySnapshotStore.load(self.prompt_path)
            return value, self._prompt_hash(value), True
        value = PromptGenerationRegistry()
        return value, self._prompt_hash(value), False

    def _load_production(self) -> tuple[ProductionControlRegistry, str, bool]:
        target = self.production_control.snapshot_path
        if target.exists():
            value = ProductionControlSnapshotStore.load(target)
            foreign = sorted(slot.slot_id for slot in value.slots.values() if slot.project_id != self.project_id)
            if foreign:
                raise ProductError("ERR_PROMPT_APPLICATION_PROJECT_MISMATCH", "Production contains foreign project Slots", ProductErrorCategory.DATA_INTEGRITY, details={"foreign_slot_ids": foreign})
            return value, self._production_hash(value), True
        value = ProductionControlRegistry()
        return value, self._production_hash(value), False

    def _load_audits(self) -> tuple[CandidateAuditRegistry, str]:
        if self.audit_path.exists():
            value = CandidateAuditSnapshotStore.load(self.audit_path)
            return value, self._audit_hash(value)
        value = CandidateAuditRegistry()
        return value, self._audit_hash(value)

    def _require_audit_stable(self, production_sha: str, audit_sha: str) -> None:
        state = self.audit_application.snapshot()
        if state["recovery"]["required"]:
            raise ProductError("ERR_PROMPT_APPLICATION_AUDIT_RECOVERY_REQUIRED", "Complete Audit recovery before regeneration planning", ProductErrorCategory.STATE)
        self._require_expected(state["production_snapshot_sha256"], production_sha, "Production")
        self._require_expected(state["audit_snapshot_sha256"], audit_sha, "Audit")

    def _require_registry_scope(self, prompts: PromptGenerationRegistry, production: ProductionControlRegistry) -> None:
        for prompt in prompts.prompts.values():
            if prompt.slot_id is None:
                raise ProductError("ERR_PROMPT_APPLICATION_SLOT_REQUIRED", "Product Prompt must bind an exact Production Slot", ProductErrorCategory.DATA_INTEGRITY)
            slot = production.slots.get(prompt.slot_id)
            if slot is None or slot.project_id != self.project_id or (prompt.scene_id is not None and prompt.scene_id != slot.scene_id):
                raise ProductError("ERR_PROMPT_APPLICATION_SCOPE_INVALID", "Prompt Scene/Slot does not match this project Production state", ProductErrorCategory.DATA_INTEGRITY)
        for attempt in prompts.attempts.values():
            slot = production.slots.get(attempt.slot_id)
            if slot is None or slot.project_id != self.project_id:
                raise ProductError("ERR_PROMPT_APPLICATION_ATTEMPT_SCOPE_INVALID", "Generation Attempt Slot does not match this project", ProductErrorCategory.DATA_INTEGRITY)

    @staticmethod
    def _require_expected(actual: str, expected: str, kind: str) -> None:
        if not isinstance(expected, str) or expected != actual:
            raise ProductError("ERR_PROMPT_APPLICATION_SNAPSHOT_CONFLICT", f"{kind} snapshot changed; reload before applying the command", ProductErrorCategory.STATE, details={"snapshot_kind": kind, "current_snapshot_sha256": actual})

    def _new_token(self) -> str:
        token = self._token_factory()
        existing = set(self._prompt_confirmations) | set(self._attempt_confirmations) | set(self._regeneration_confirmations)
        if not isinstance(token, str) or not token.strip() or token in existing:
            raise ProductError("ERR_PROMPT_APPLICATION_CONFIRMATION_TOKEN_INVALID", "Prompt Evidence confirmation token is invalid", ProductErrorCategory.INTERNAL)
        return token

    @staticmethod
    def _transaction_body(value: dict[str, Any]) -> dict[str, Any]:
        body = {key: item for key, item in value.items() if key != "transaction_sha256"}
        body["transaction_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @staticmethod
    def _attempt_from_dict(raw: Any) -> GenerationAttempt:
        try:
            if (
                not isinstance(raw, dict)
                or set(raw) != _ATTEMPT_FIELDS
                or isinstance(raw["prompt_version"], bool)
                or not isinstance(raw["prompt_version"], int)
                or isinstance(raw["strategy_level"], bool)
                or not isinstance(raw["strategy_level"], int)
                or not isinstance(raw["failure_codes"], list)
                or not isinstance(raw["input_asset_hashes"], list)
            ):
                raise ValueError("Attempt fields are invalid")
            return GenerationAttempt(
                generation_job_id=raw["generation_job_id"], slot_id=raw["slot_id"],
                prompt_id=raw["prompt_id"], prompt_version=raw["prompt_version"],
                prompt_sha256=raw["prompt_sha256"], provider_id=raw["provider_id"],
                model_id=raw["model_id"], provider_profile_version=raw["provider_profile_version"],
                strategy_level=RegenerationStrategy(raw["strategy_level"]), result=GenerationResult(raw["result"]),
                failure_codes=tuple(raw["failure_codes"]), output_candidate_id=raw["output_candidate_id"],
                parent_attempt_id=raw["parent_attempt_id"], input_asset_hashes=tuple(raw["input_asset_hashes"]),
                cost=raw["cost"], latency_ms=raw["latency_ms"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError("ERR_PROMPT_TRANSACTION_ATTEMPT_INVALID", "Prompt transaction Attempt is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc

    @classmethod
    def _validate_transaction(cls, value: Any) -> None:
        if (
            not isinstance(value, dict)
            or set(value) != _TRANSACTION_FIELDS
            or value.get("transaction_version") != "1.0.0"
            or value.get("task_owner") != "TASK-040"
            or value.get("state") not in {"PREPARED", "COMMITTED", "ABANDONED"}
            or not isinstance(value.get("transaction_id"), str) or not value["transaction_id"].strip()
            or not isinstance(value.get("project_id"), str) or not value["project_id"].strip()
        ):
            raise ProductError("ERR_PROMPT_TRANSACTION_INVALID", "Prompt transaction is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value["transaction_sha256"] != cls._transaction_body(value)["transaction_sha256"]:
            raise ProductError("ERR_PROMPT_TRANSACTION_CHECKSUM", "Prompt transaction checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        hashes = (
            value["confirmation_id_sha256"], value["old_prompt_sha256"], value["new_prompt_sha256"],
            value["old_production_sha256"], value["new_production_sha256"],
        )
        if not all(isinstance(item, str) and _SHA_RE.fullmatch(item) for item in hashes):
            raise ProductError("ERR_PROMPT_TRANSACTION_INVALID", "Prompt transaction hashes are invalid", ProductErrorCategory.DATA_INTEGRITY)
        cls._attempt_from_dict(value["attempt"])

    def _write_transaction(self, value: dict[str, Any]) -> dict[str, Any]:
        document = self._transaction_body(value)
        AtomicJsonWriter.write(self.transaction_path, document, validator=self._validate_transaction)
        return document

    def _load_transaction(self) -> dict[str, Any] | None:
        target = self.transaction_path
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ProductError("ERR_PROMPT_TRANSACTION_FILE_INVALID", "Prompt transaction must be a regular non-symlink file", ProductErrorCategory.SECURITY)
        if not target.exists():
            return None
        size = target.stat().st_size
        if size <= 0 or size > _MAX_TRANSACTION_BYTES:
            raise ProductError("ERR_PROMPT_TRANSACTION_SIZE", "Prompt transaction size is outside the allowed bound", ProductErrorCategory.DATA_INTEGRITY)
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROMPT_TRANSACTION_READ", "Prompt transaction could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._validate_transaction(value)
        if value["project_id"] != self.project_id:
            raise ProductError("ERR_PROMPT_TRANSACTION_PROJECT_MISMATCH", "Prompt transaction belongs to another project", ProductErrorCategory.DATA_INTEGRITY)
        return value

    @staticmethod
    def _recovery_state(transaction: dict[str, Any] | None, prompt_sha: str, production_sha: str) -> dict[str, Any]:
        if transaction is None or transaction["state"] != "PREPARED":
            return {"required": False, "state": None, "available_actions": []}
        old_r, new_r = transaction["old_prompt_sha256"], transaction["new_prompt_sha256"]
        old_p, new_p = transaction["old_production_sha256"], transaction["new_production_sha256"]
        if prompt_sha == old_r and production_sha == old_p:
            state, actions = "OLD_OLD", ["COMPLETE", "ABANDON"]
        elif prompt_sha == new_r and production_sha == old_p:
            state, actions = "PROMPT_NEW_PRODUCTION_OLD", ["COMPLETE"]
        elif prompt_sha == old_r and production_sha == new_p:
            state, actions = "PROMPT_OLD_PRODUCTION_NEW", ["COMPLETE"]
        elif prompt_sha == new_r and production_sha == new_p:
            state, actions = "NEW_NEW", ["FINALIZE"]
        else:
            state, actions = "UNKNOWN_MIXTURE", []
        return {"required": True, "state": state, "generation_job_id": transaction["attempt"]["generation_job_id"], "available_actions": actions}

    def snapshot(self) -> dict[str, Any]:
        prompts, prompt_sha, prompt_persisted = self._load_prompts()
        production, production_sha, production_persisted = self._load_production()
        self._require_registry_scope(prompts, production)
        audits, audit_sha = self._load_audits()
        regeneration_candidates = {
            item.candidate_id
            for item in audits.decisions.values()
            if item.decision is HumanCandidateDecision.NEEDS_REGENERATION
        }
        recovery = self._recovery_state(self._load_transaction(), prompt_sha, production_sha)
        prompt_rows = []
        for key in sorted(prompts.prompts):
            prompt = prompts.prompts[key]
            attempts = [
                {**item.to_dict(), "human_regeneration_available": item.output_candidate_id in regeneration_candidates}
                for item in prompts.attempts.values()
                if item.prompt_id == prompt.prompt_id and item.prompt_version == prompt.prompt_version
            ]
            prompt_rows.append({**prompt.to_dict(), "attempts": sorted(attempts, key=lambda item: item["generation_job_id"])})
        return {
            "application_version": "1.0.0", "task_owner": "TASK-040", "project_id": self.project_id,
            "prompt_snapshot_sha256": prompt_sha, "production_snapshot_sha256": production_sha,
            "audit_snapshot_sha256": audit_sha, "prompt_persisted": prompt_persisted,
            "production_persisted": production_persisted, "recovery": recovery,
            "prompts": prompt_rows, "prompt_count": len(prompts.prompts), "attempt_count": len(prompts.attempts),
            "actions_allowed": not recovery["required"], "prompt_body_embedded": False,
            "provider_execution_started": False, "paid_execution_authorized": False,
            "candidate_creation_started": False, "resolve_mutation_started": False,
        }

    def prepare_prompt(
        self, *, prompt_id: str, prompt_version: int, purpose: str, scene_id: str,
        slot_id: str, body_ref: str, body_sha256: str, provider_profile_id: str,
        provider_profile_version: str, input_asset_hashes: tuple[str, ...],
        keep_conditions: tuple[str, ...], expected_prompt_snapshot_sha256: str,
        expected_production_snapshot_sha256: str,
    ) -> dict[str, Any]:
        prompts, prompt_sha, _ = self._load_prompts()
        production, production_sha, _ = self._load_production()
        self._require_expected(prompt_sha, expected_prompt_snapshot_sha256, "Prompt")
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
            raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before registering a Prompt", ProductErrorCategory.STATE)
        if not isinstance(body_ref, str) or not body_ref.startswith("project-private://"):
            raise ProductError("ERR_PROMPT_APPLICATION_BODY_REF_INVALID", "Prompt body reference must use project-private:// storage", ProductErrorCategory.SECURITY)
        try:
            prompt = PromptEntity(
                prompt_id, prompt_version, purpose, body_sha256, provider_profile_id,
                provider_profile_version, keep_conditions, scene_id=scene_id, slot_id=slot_id,
                body_ref=body_ref, input_asset_hashes=input_asset_hashes,
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_PROMPT_APPLICATION_PROMPT_INVALID", "Prompt metadata is invalid", ProductErrorCategory.VALIDATION) from exc
        prompts.add_prompt(prompt)
        self._require_registry_scope(prompts, production)
        token = self._new_token()
        self._prompt_confirmations[token] = _PendingPrompt(token, prompt, prompt_sha, production_sha)
        return {"confirmation_id": token, "prompt": prompt.to_dict(), "human_final_authority_required": True, "provider_execution_started": False}

    def apply_prompt(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._prompt_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PROMPT_APPLICATION_CONFIRMATION_INVALID", "Prompt confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            prompts, prompt_sha, persisted = self._load_prompts()
            production, production_sha, _ = self._load_production()
            self._require_expected(prompt_sha, pending.prompt_sha256, "Prompt")
            self._require_expected(production_sha, pending.production_sha256, "Production")
            if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
                raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before registering a Prompt", ProductErrorCategory.STATE)
            prompts.add_prompt(pending.prompt)
            self._require_registry_scope(prompts, production)
            PromptRegistrySnapshotStore.save(self.prompt_path, prompts, expected_previous_snapshot_sha256=prompt_sha if persisted else None)
        return self.snapshot()

    def prepare_attempt(
        self, *, generation_job_id: str, slot_id: str, prompt_id: str, prompt_version: int,
        provider_id: str, model_id: str, strategy_level: int, result: str,
        failure_codes: tuple[str, ...], output_candidate_id: str | None,
        parent_attempt_id: str | None, cost: float | None, latency_ms: int | None,
        expected_prompt_snapshot_sha256: str, expected_production_snapshot_sha256: str,
    ) -> dict[str, Any]:
        prompts, prompt_sha, _ = self._load_prompts()
        production, production_sha, _ = self._load_production()
        self._require_expected(prompt_sha, expected_prompt_snapshot_sha256, "Prompt")
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
            raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before importing Generation Evidence", ProductErrorCategory.STATE)
        prompt = prompts.prompts.get((prompt_id, prompt_version))
        if prompt is None:
            raise ProductError("ERR_GENERATION_PROMPT_NOT_FOUND", "Generation Evidence references unknown Prompt", ProductErrorCategory.DATA_INTEGRITY)
        try:
            attempt = GenerationAttempt(
                generation_job_id, slot_id, prompt_id, prompt_version, prompt.body_sha256,
                provider_id, model_id, RegenerationStrategy(strategy_level), GenerationResult(result),
                failure_codes, output_candidate_id=output_candidate_id, parent_attempt_id=parent_attempt_id,
                provider_profile_version=prompt.provider_profile_version,
                input_asset_hashes=prompt.input_asset_hashes, cost=cost, latency_ms=latency_ms,
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_PROMPT_APPLICATION_ATTEMPT_INVALID", "Generation Evidence metadata is invalid", ProductErrorCategory.VALIDATION) from exc
        prompts.add_attempt(attempt)
        self._require_registry_scope(prompts, production)
        production_binding = output_candidate_id is not None
        if production_binding:
            binding = GenerationOutputProductionBinding.bind(generation_job_id=generation_job_id, prompts=prompts, production=production)
            if binding.status != "BOUND":
                raise ProductError("ERR_PROMPT_APPLICATION_PREBOUND_OUTPUT", "Production lineage exists without matching persisted Prompt Evidence", ProductErrorCategory.DATA_INTEGRITY)
        token = self._new_token()
        pending = _PendingAttempt(
            token, attempt, prompt_sha, self._prompt_hash(prompts), production_sha,
            self._production_hash(production), production_binding,
        )
        self._attempt_confirmations[token] = pending
        return {"confirmation_id": token, "attempt": attempt.to_dict(), "production_binding_required": production_binding, "human_final_authority_required": True, "provider_execution_started": False, "candidate_creation_started": False}

    def _inject(self, stage: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def apply_attempt(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._attempt_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PROMPT_APPLICATION_ATTEMPT_CONFIRMATION_INVALID", "Generation Evidence confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            prompts, prompt_sha, prompt_persisted = self._load_prompts()
            production, production_sha, production_persisted = self._load_production()
            self._require_expected(prompt_sha, pending.old_prompt_sha256, "Prompt")
            self._require_expected(production_sha, pending.old_production_sha256, "Production")
            if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
                raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before importing Generation Evidence", ProductErrorCategory.STATE)
            prompts.add_attempt(pending.attempt)
            if pending.production_binding_required:
                GenerationOutputProductionBinding.bind(generation_job_id=pending.attempt.generation_job_id, prompts=prompts, production=production)
            if self._prompt_hash(prompts) != pending.new_prompt_sha256 or self._production_hash(production) != pending.new_production_sha256:
                raise ProductError("ERR_PROMPT_APPLICATION_CONFIRMATION_STALE", "Generation Evidence result changed after preparation", ProductErrorCategory.AUTHORIZATION)
            if not pending.production_binding_required:
                PromptRegistrySnapshotStore.save(self.prompt_path, prompts, expected_previous_snapshot_sha256=prompt_sha if prompt_persisted else None)
                return self.snapshot()
            transaction = self._write_transaction({
                "transaction_version": "1.0.0", "task_owner": "TASK-040",
                "transaction_id": "txn-" + sha256_bytes(confirmation_id.encode("utf-8"))[7:31],
                "project_id": self.project_id, "state": "PREPARED",
                "confirmation_id_sha256": sha256_bytes(confirmation_id.encode("utf-8")),
                "attempt": pending.attempt.to_dict(), "old_prompt_sha256": prompt_sha,
                "new_prompt_sha256": pending.new_prompt_sha256, "old_production_sha256": production_sha,
                "new_production_sha256": pending.new_production_sha256,
            })
            self._inject("after_transaction_prepare")
            PromptRegistrySnapshotStore.save(self.prompt_path, prompts, expected_previous_snapshot_sha256=prompt_sha if prompt_persisted else None)
            self._inject("after_prompt_save")
            ProductionControlSnapshotStore.save(self.production_control.snapshot_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            self._inject("after_production_save")
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return self.snapshot()

    def prepare_regeneration(
        self, *, candidate_id: str, new_body_sha256: str, new_body_ref: str,
        provider_profile_id: str | None, provider_profile_version: str | None,
        input_asset_hashes: tuple[str, ...] | None, keep_conditions: tuple[str, ...] | None,
        repeated_failure_threshold: int, expected_prompt_snapshot_sha256: str,
        expected_production_snapshot_sha256: str, expected_audit_snapshot_sha256: str,
    ) -> dict[str, Any]:
        prompts, prompt_sha, _ = self._load_prompts()
        production, production_sha, _ = self._load_production()
        audits, audit_sha = self._load_audits()
        self._require_expected(prompt_sha, expected_prompt_snapshot_sha256, "Prompt")
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(audit_sha, expected_audit_snapshot_sha256, "Audit")
        self._require_registry_scope(prompts, production)
        self._require_audit_stable(production_sha, audit_sha)
        if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
            raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before regeneration planning", ProductErrorCategory.STATE)
        if not isinstance(new_body_ref, str) or not new_body_ref.startswith("project-private://"):
            raise ProductError("ERR_PROMPT_APPLICATION_BODY_REF_INVALID", "Regeneration Prompt body reference must use project-private:// storage", ProductErrorCategory.SECURITY)
        try:
            plan = HumanRegenerationPlanner.compile(
                candidate_id=candidate_id, production=production, audits=audits, prompts=prompts,
                repeated_failure_threshold=repeated_failure_threshold,
            )
            draft = RegenerationPromptDraftService.compile(
                plan, registry=prompts, new_body_sha256=new_body_sha256, new_body_ref=new_body_ref,
                provider_profile_id=provider_profile_id, provider_profile_version=provider_profile_version,
                input_asset_hashes=input_asset_hashes, keep_conditions=keep_conditions,
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_PROMPT_APPLICATION_REGENERATION_INVALID", "Regeneration Prompt metadata is invalid", ProductErrorCategory.VALIDATION) from exc
        token = self._new_token()
        self._regeneration_confirmations[token] = _PendingRegeneration(
            token, candidate_id, draft, plan.to_dict()["plan_sha256"], repeated_failure_threshold,
            prompt_sha, production_sha, audit_sha,
        )
        return {"confirmation_id": token, "plan": plan.to_dict(), "draft": draft.to_dict(), "human_final_authority_required": True, "provider_execution_started": False}

    def apply_regeneration(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._regeneration_confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_PROMPT_APPLICATION_REGENERATION_CONFIRMATION_INVALID", "Regeneration confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        with _exclusive_snapshot_lock(self.transaction_path):
            prompts, prompt_sha, prompt_persisted = self._load_prompts()
            production, production_sha, _ = self._load_production()
            audits, audit_sha = self._load_audits()
            self._require_expected(prompt_sha, pending.prompt_sha256, "Prompt")
            self._require_expected(production_sha, pending.production_sha256, "Production")
            self._require_expected(audit_sha, pending.audit_sha256, "Audit")
            self._require_registry_scope(prompts, production)
            self._require_audit_stable(production_sha, audit_sha)
            if self._recovery_state(self._load_transaction(), prompt_sha, production_sha)["required"]:
                raise ProductError("ERR_PROMPT_APPLICATION_RECOVERY_REQUIRED", "Complete Prompt recovery before regeneration registration", ProductErrorCategory.STATE)
            plan = HumanRegenerationPlanner.compile(
                candidate_id=pending.candidate_id, production=production, audits=audits,
                prompts=prompts, repeated_failure_threshold=pending.repeated_failure_threshold,
            )
            if plan.to_dict()["plan_sha256"] != pending.plan_sha256:
                raise ProductError("ERR_PROMPT_APPLICATION_REGENERATION_STALE", "Regeneration plan changed after confirmation", ProductErrorCategory.AUTHORIZATION)
            RegenerationPromptDraftService.register(pending.draft, registry=prompts)
            PromptRegistrySnapshotStore.save(self.prompt_path, prompts, expected_previous_snapshot_sha256=prompt_sha if prompt_persisted else None)
        return self.snapshot()

    def apply_recovery(self, *, action: str) -> dict[str, Any]:
        with _exclusive_snapshot_lock(self.transaction_path):
            transaction = self._load_transaction()
            if transaction is None or transaction["state"] != "PREPARED":
                raise ProductError("ERR_PROMPT_RECOVERY_NOT_REQUIRED", "No prepared Prompt transaction requires recovery", ProductErrorCategory.STATE)
            prompts, prompt_sha, prompt_persisted = self._load_prompts()
            production, production_sha, production_persisted = self._load_production()
            recovery = self._recovery_state(transaction, prompt_sha, production_sha)
            if action not in recovery["available_actions"]:
                raise ProductError("ERR_PROMPT_RECOVERY_ACTION_INVALID", "Recovery action is not allowed for the exact persisted state", ProductErrorCategory.AUTHORIZATION, details={"recovery_state": recovery["state"]})
            if action == "ABANDON":
                transaction["state"] = "ABANDONED"; self._write_transaction(transaction); return self.snapshot()
            if action == "FINALIZE":
                transaction["state"] = "COMMITTED"; self._write_transaction(transaction); return self.snapshot()
            attempt = self._attempt_from_dict(transaction["attempt"])
            if prompt_sha == transaction["old_prompt_sha256"]:
                prompts.add_attempt(attempt)
            if production_sha == transaction["old_production_sha256"]:
                GenerationOutputProductionBinding.bind(generation_job_id=attempt.generation_job_id, prompts=prompts, production=production)
            if self._prompt_hash(prompts) != transaction["new_prompt_sha256"] or self._production_hash(production) != transaction["new_production_sha256"]:
                raise ProductError("ERR_PROMPT_RECOVERY_RESULT_MISMATCH", "Recovered Prompt state does not match prepared result", ProductErrorCategory.DATA_INTEGRITY)
            if prompt_sha == transaction["old_prompt_sha256"]:
                PromptRegistrySnapshotStore.save(self.prompt_path, prompts, expected_previous_snapshot_sha256=prompt_sha if prompt_persisted else None)
            if production_sha == transaction["old_production_sha256"]:
                ProductionControlSnapshotStore.save(self.production_control.snapshot_path, production, expected_previous_snapshot_sha256=production_sha if production_persisted else None)
            transaction["state"] = "COMMITTED"
            self._write_transaction(transaction)
        return self.snapshot()


__all__ = ["Task040PromptEvidenceApplication"]
