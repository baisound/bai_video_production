"""TASK-042 one-shot Quick intent application with Prompt/Production/Quick CAS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any, Callable

from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotKind, SlotStatus, StaleState
from .production_control_store import ProductionControlSnapshotStore
from .prompt_registry import PromptGenerationRegistry
from .prompt_registry_store import PromptRegistrySnapshotStore
from .quick_generation import (
    QuickGenerationIntent, QuickGenerationMode, QuickGenerationRegistry,
    QuickReferenceInput, QuickReferenceRole, QuickReferenceSource,
)
from .quick_generation_store import QuickGenerationSnapshotStore


TokenFactory = Callable[[], str]


@dataclass(slots=True)
class _PendingIntent:
    confirmation_id: str
    intent: QuickGenerationIntent
    consumed: bool = False


class Task042QuickGenerationApplication:
    def __init__(
        self, *, project_root: str | Path, project_id: str,
        token_factory: TokenFactory | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError("ERR_QUICK_PROJECT_ROOT_INVALID", "Quick project root must be a regular directory", ProductErrorCategory.VALIDATION)
        self.project_root = root
        self.project_id = project_id
        self.prompt_path = root / "prompt-registry.json"
        self.production_path = root / "production-control.json"
        self.quick_path = root / "quick-generation-intents.json"
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._confirmations: dict[str, _PendingIntent] = {}
        try:
            QuickGenerationRegistry(project_id)
        except ValueError as exc:
            raise ProductError("ERR_QUICK_PROJECT_ID_INVALID", "Quick project_id is invalid", ProductErrorCategory.VALIDATION) from exc

    def _load_prompts(self) -> tuple[PromptGenerationRegistry, str]:
        if not self.prompt_path.exists():
            raise ProductError("ERR_QUICK_PROMPT_SNAPSHOT_REQUIRED", "Quick intent requires a persisted Prompt snapshot", ProductErrorCategory.STATE)
        value = PromptRegistrySnapshotStore.load(self.prompt_path)
        return value, PromptRegistrySnapshotStore.snapshot(value)["snapshot_sha256"]

    def _load_production(self) -> tuple[ProductionControlRegistry, str]:
        if not self.production_path.exists():
            raise ProductError("ERR_QUICK_PRODUCTION_SNAPSHOT_REQUIRED", "Quick intent requires a persisted Production snapshot", ProductErrorCategory.STATE)
        value = ProductionControlSnapshotStore.load(self.production_path)
        foreign = [slot.slot_id for slot in value.slots.values() if slot.project_id != self.project_id]
        if foreign:
            raise ProductError("ERR_QUICK_PROJECT_MISMATCH", "Production contains a foreign project Slot", ProductErrorCategory.DATA_INTEGRITY, details={"foreign_slot_ids": sorted(foreign)})
        return value, ProductionControlSnapshotStore.snapshot(value)["snapshot_sha256"]

    def _load_quick(self) -> tuple[QuickGenerationRegistry, str, bool]:
        if self.quick_path.exists():
            value = QuickGenerationSnapshotStore.load(self.quick_path, project_id=self.project_id)
            return value, QuickGenerationSnapshotStore.snapshot(value)["snapshot_sha256"], True
        value = QuickGenerationRegistry(self.project_id)
        return value, QuickGenerationSnapshotStore.snapshot(value)["snapshot_sha256"], False

    @staticmethod
    def _require_expected(actual: str, expected: str, name: str) -> None:
        if not isinstance(expected, str) or expected != actual:
            raise ProductError("ERR_QUICK_SNAPSHOT_CONFLICT", f"{name} snapshot changed; reload and prepare again", ProductErrorCategory.STATE, details={"snapshot_kind": name, "current_snapshot_sha256": actual})

    @staticmethod
    def _target_kinds(mode: QuickGenerationMode) -> frozenset[SlotKind]:
        if mode is QuickGenerationMode.IMAGE:
            return frozenset({SlotKind.START_FRAME, SlotKind.END_FRAME, SlotKind.OTHER})
        if mode in {QuickGenerationMode.START_END, QuickGenerationMode.VIDEO}:
            return frozenset({SlotKind.VIDEO})
        return frozenset({SlotKind.SE, SlotKind.BGM, SlotKind.NARRATION, SlotKind.OTHER})

    @classmethod
    def _validate_authority(
        cls, intent: QuickGenerationIntent, prompts: PromptGenerationRegistry,
        production: ProductionControlRegistry,
    ) -> None:
        prompt = prompts.prompts.get((intent.prompt_id, intent.prompt_version))
        if prompt is None or prompt.compilation_binding is None:
            raise ProductError("ERR_QUICK_COMPILED_PROMPT_REQUIRED", "Quick intent requires an exact compiled Prompt version", ProductErrorCategory.AUTHORIZATION)
        binding = prompt.compilation_binding
        if (
            prompt.body_sha256 != intent.prompt_sha256
            or binding.compilation_sha256 != intent.compilation_sha256
            or prompt.provider_profile_id != intent.provider_profile_id
            or prompt.provider_profile_version != intent.provider_profile_version
            or binding.provider_profile_sha256 != intent.provider_profile_sha256
            or binding.selected_route_id != intent.selected_route_id
            or binding.required_capabilities != intent.route_capabilities
            or binding.scene_id != intent.scene_id
            or binding.slot_id != intent.target_slot_id
        ):
            raise ProductError("ERR_QUICK_PROMPT_IDENTITY_MISMATCH", "Quick intent differs from immutable Prompt compilation", ProductErrorCategory.DATA_INTEGRITY)
        if tuple(reference.asset_sha256 for reference in intent.references) != binding.input_asset_hashes:
            raise ProductError("ERR_QUICK_REFERENCE_PROMPT_MISMATCH", "Quick references differ from exact compiled Prompt inputs", ProductErrorCategory.DATA_INTEGRITY)
        slot = production.slots.get(intent.target_slot_id)
        if slot is None or slot.project_id != intent.project_id or slot.scene_id != intent.scene_id:
            raise ProductError("ERR_QUICK_TARGET_SLOT_MISMATCH", "Quick target Slot does not match project/Scene", ProductErrorCategory.DATA_INTEGRITY)
        if slot.slot_kind not in cls._target_kinds(intent.mode):
            raise ProductError("ERR_QUICK_TARGET_SLOT_KIND", "Quick target Slot kind is incompatible with mode", ProductErrorCategory.VALIDATION)
        if slot.stale_state is not StaleState.CURRENT or slot.status in {SlotStatus.LOCKED, SlotStatus.STALE} or slot.locked_candidate_id is not None:
            raise ProductError("ERR_QUICK_TARGET_SLOT_NOT_MUTABLE", "Quick target Slot must be mutable, CURRENT and unlocked", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
        lock_kinds = {
            QuickReferenceRole.CHARACTER_LOCK: SlotKind.CHARACTER_REFERENCE,
            QuickReferenceRole.SPACE_LOCK: SlotKind.SPACE_REFERENCE,
            QuickReferenceRole.COMPOSITION_LOCK: SlotKind.COMPOSITION_REFERENCE,
        }
        for reference in intent.references:
            if reference.source_kind is QuickReferenceSource.FILE:
                raise ProductError("ERR_QUICK_FILE_INGEST_REQUIRED", "FILE input must be securely ingested and referenced as an internal Asset before Quick authority", ProductErrorCategory.AUTHORIZATION)
            if reference.slot_id is None:
                continue
            ref_slot = production.slots.get(reference.slot_id)
            candidate = production.candidates.get(reference.candidate_id or "")
            if ref_slot is None or candidate is None or candidate.slot_id != ref_slot.slot_id or candidate.asset_id != reference.asset_id or candidate.asset_sha256 != reference.asset_sha256:
                raise ProductError("ERR_QUICK_REFERENCE_IDENTITY_MISMATCH", "Quick reference does not match exact Production Candidate", ProductErrorCategory.DATA_INTEGRITY)
            expected_kind = lock_kinds.get(reference.role)
            if expected_kind is not None and (
                ref_slot.slot_kind is not expected_kind
                or ref_slot.status is not SlotStatus.LOCKED
                or ref_slot.stale_state is not StaleState.CURRENT
                or ref_slot.locked_candidate_id != candidate.candidate_id
                or candidate.lifecycle_state is not CandidateLifecycle.LOCKED
            ):
                raise ProductError("ERR_QUICK_REFERENCE_LOCK_NOT_CURRENT", "Quick Lock reference is not exact LOCKED/CURRENT truth", ProductErrorCategory.AUTHORIZATION)

    def snapshot(self) -> dict[str, Any]:
        prompts, prompt_sha = self._load_prompts()
        production, production_sha = self._load_production()
        quick, quick_sha, persisted = self._load_quick()
        rows = []
        for intent in quick.intents:
            if intent.expected_prompt_snapshot_sha256 != prompt_sha or intent.expected_production_snapshot_sha256 != production_sha:
                status = "STALE_REPREPARE_REQUIRED"
            else:
                try:
                    self._validate_authority(intent, prompts, production)
                except ProductError:
                    status = "RECOVERY_REQUIRED"
                else:
                    status = "CURRENT"
            rows.append({
                **intent.to_dict(), "status": status,
                "compiled_plan": {
                    "authority_kind": "QUICK_INTENT", "approved_plan_used": False,
                    "human_go_used": False, "provider_execution_started": False,
                    "candidate_created": False,
                },
            })
        return {
            "application_version": "1.0.0", "task_owner": "TASK-042",
            "project_id": self.project_id, "quick_snapshot_sha256": quick_sha,
            "prompt_snapshot_sha256": prompt_sha, "production_snapshot_sha256": production_sha,
            "persisted": persisted, "intent_count": len(rows), "intents": rows,
            "provider_execution_started": False, "paid_execution_authorized": False,
            "candidate_creation_started": False, "media_write_started": False,
        }

    def prepare_intent(
        self, *, intent_id: str, intent_version: int, scene_id: str,
        mode: QuickGenerationMode, target_slot_id: str, prompt_id: str,
        prompt_version: int, provider_profile_sha256: str, selected_capability: str,
        route_capabilities: tuple[str, ...], references: tuple[QuickReferenceInput, ...],
        rights_authorization_ref: str, currency: str, cost_ceiling: str,
        execution_decision_id: str, execution_decision_sha256: str,
        expected_prompt_snapshot_sha256: str,
        expected_production_snapshot_sha256: str,
        expected_quick_snapshot_sha256: str,
    ) -> dict[str, Any]:
        prompts, prompt_sha = self._load_prompts()
        production, production_sha = self._load_production()
        _, quick_sha, _ = self._load_quick()
        self._require_expected(prompt_sha, expected_prompt_snapshot_sha256, "Prompt")
        self._require_expected(production_sha, expected_production_snapshot_sha256, "Production")
        self._require_expected(quick_sha, expected_quick_snapshot_sha256, "Quick")
        prompt = prompts.prompts.get((prompt_id, prompt_version))
        if prompt is None or prompt.compilation_binding is None:
            raise ProductError("ERR_QUICK_COMPILED_PROMPT_REQUIRED", "Quick intent requires a compiled Prompt", ProductErrorCategory.AUTHORIZATION)
        binding = prompt.compilation_binding
        try:
            intent = QuickGenerationIntent(
                intent_id=intent_id, intent_version=intent_version, project_id=self.project_id,
                scene_id=scene_id, mode=mode, target_slot_id=target_slot_id,
                prompt_id=prompt_id, prompt_version=prompt_version, prompt_sha256=prompt.body_sha256,
                compilation_sha256=binding.compilation_sha256,
                provider_profile_id=prompt.provider_profile_id,
                provider_profile_version=prompt.provider_profile_version,
                provider_profile_sha256=provider_profile_sha256,
                selected_route_id=binding.selected_route_id,
                selected_capability=selected_capability,
                route_capabilities=route_capabilities, references=references,
                rights_authorization_ref=rights_authorization_ref, currency=currency,
                cost_ceiling=cost_ceiling, execution_decision_id=execution_decision_id,
                execution_decision_sha256=execution_decision_sha256,
                expected_prompt_snapshot_sha256=prompt_sha,
                expected_production_snapshot_sha256=production_sha,
                expected_quick_snapshot_sha256=quick_sha,
            )
        except (TypeError, ValueError) as exc:
            raise ProductError("ERR_QUICK_INTENT_INVALID", "Quick intent is invalid", ProductErrorCategory.VALIDATION) from exc
        self._validate_authority(intent, prompts, production)
        token = self._token_factory()
        if not isinstance(token, str) or not token.strip() or token in self._confirmations:
            raise ProductError("ERR_QUICK_CONFIRMATION_TOKEN_INVALID", "Quick confirmation token is invalid", ProductErrorCategory.INTERNAL)
        self._confirmations[token] = _PendingIntent(token, intent)
        return {
            "confirmation_id": token, "intent": intent.to_dict(),
            "human_final_authority_required": True, "provider_execution_started": False,
            "paid_execution_authorized": False, "candidate_created": False,
        }

    def apply_intent(self, *, confirmation_id: str) -> dict[str, Any]:
        pending = self._confirmations.get(confirmation_id)
        if pending is None or pending.consumed:
            raise ProductError("ERR_QUICK_CONFIRMATION_INVALID", "Quick confirmation is missing or already used", ProductErrorCategory.AUTHORIZATION)
        pending.consumed = True
        prompts, prompt_sha = self._load_prompts()
        production, production_sha = self._load_production()
        quick, quick_sha, persisted = self._load_quick()
        intent = pending.intent
        self._require_expected(prompt_sha, intent.expected_prompt_snapshot_sha256, "Prompt")
        self._require_expected(production_sha, intent.expected_production_snapshot_sha256, "Production")
        self._require_expected(quick_sha, intent.expected_quick_snapshot_sha256, "Quick")
        self._validate_authority(intent, prompts, production)
        quick.add_intent(intent)
        QuickGenerationSnapshotStore.save(
            self.quick_path, quick,
            expected_previous_snapshot_sha256=quick_sha if persisted else None,
        )
        return self.snapshot()


__all__ = ["Task042QuickGenerationApplication"]
