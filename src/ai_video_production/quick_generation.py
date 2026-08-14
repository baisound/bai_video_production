"""TASK-042 P-V6-3 Quick Generation intent authority and read-only adoption."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any

from .candidate_audit import CandidateAuditRegistry, HumanCandidateDecision
from .errors import ProductError, ProductErrorCategory
from .production_control import CandidateLifecycle, ProductionControlRegistry, SlotStatus, StaleState
from .prompt_registry import GenerationResult, PromptGenerationRegistry
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_CURRENCY_RE = re.compile(r"[A-Z]{3}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class QuickGenerationMode(str, Enum):
    IMAGE = "IMAGE"
    START_END = "START_END"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class QuickReferenceSource(str, Enum):
    FILE = "FILE"
    ASSET_LIBRARY = "ASSET_LIBRARY"
    GENERATION_RESULT = "GENERATION_RESULT"


class QuickReferenceRole(str, Enum):
    GENERAL = "GENERAL"
    CHARACTER_LOCK = "CHARACTER_LOCK"
    SPACE_LOCK = "SPACE_LOCK"
    COMPOSITION_LOCK = "COMPOSITION_LOCK"
    START = "START"
    END = "END"
    AUDIO_REFERENCE = "AUDIO_REFERENCE"


@dataclass(frozen=True, slots=True)
class QuickReferenceInput:
    reference_id: str
    source_kind: QuickReferenceSource
    role: QuickReferenceRole
    asset_id: str
    asset_sha256: str
    slot_id: str | None = None
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        _id(self.reference_id, "reference_id")
        _id(self.asset_id, "asset_id")
        _sha(self.asset_sha256, "asset_sha256")
        if not isinstance(self.source_kind, QuickReferenceSource) or not isinstance(self.role, QuickReferenceRole):
            raise ValueError("Quick reference enum is invalid")
        for name in ("slot_id", "candidate_id"):
            value = getattr(self, name)
            if value is not None:
                _id(value, name)
        if (self.slot_id is None) != (self.candidate_id is None):
            raise ValueError("Quick reference Slot/Candidate identity is incomplete")
        if self.source_kind is QuickReferenceSource.FILE and self.slot_id is not None:
            raise ValueError("FILE references must be ingested before Candidate binding")
        if self.source_kind is QuickReferenceSource.GENERATION_RESULT and self.slot_id is None:
            raise ValueError("GENERATION_RESULT requires exact Slot/Candidate identity")
        if self.role in {
            QuickReferenceRole.CHARACTER_LOCK,
            QuickReferenceRole.SPACE_LOCK,
            QuickReferenceRole.COMPOSITION_LOCK,
        } and self.slot_id is None:
            raise ValueError("Lock role requires exact Slot/Candidate identity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "source_kind": self.source_kind.value,
            "role": self.role.value,
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "slot_id": self.slot_id,
            "candidate_id": self.candidate_id,
            "host_path_embedded": False,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QuickReferenceInput":
        fields = {"reference_id", "source_kind", "role", "asset_id", "asset_sha256", "slot_id", "candidate_id", "host_path_embedded"}
        if not isinstance(value, dict) or set(value) != fields or value["host_path_embedded"] is not False:
            raise ValueError("Quick reference fields are invalid")
        return cls(
            reference_id=value["reference_id"], source_kind=QuickReferenceSource(value["source_kind"]),
            role=QuickReferenceRole(value["role"]), asset_id=value["asset_id"],
            asset_sha256=value["asset_sha256"], slot_id=value["slot_id"], candidate_id=value["candidate_id"],
        )


@dataclass(frozen=True, slots=True)
class QuickGenerationIntent:
    intent_id: str
    intent_version: int
    project_id: str
    scene_id: str
    mode: QuickGenerationMode
    target_slot_id: str
    prompt_id: str
    prompt_version: int
    prompt_sha256: str
    compilation_sha256: str
    provider_profile_id: str
    provider_profile_version: str
    provider_profile_sha256: str
    selected_route_id: str
    selected_capability: str
    route_capabilities: tuple[str, ...]
    references: tuple[QuickReferenceInput, ...]
    rights_authorization_ref: str
    currency: str
    cost_ceiling: str
    execution_decision_id: str
    execution_decision_sha256: str
    expected_prompt_snapshot_sha256: str
    expected_production_snapshot_sha256: str
    expected_quick_snapshot_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "intent_id", "project_id", "scene_id", "target_slot_id", "prompt_id",
            "provider_profile_id", "selected_route_id", "selected_capability", "execution_decision_id",
        ):
            _id(getattr(self, name), name)
        for name in (
            "prompt_sha256", "compilation_sha256", "provider_profile_sha256",
            "execution_decision_sha256", "expected_prompt_snapshot_sha256",
            "expected_production_snapshot_sha256", "expected_quick_snapshot_sha256",
        ):
            _sha(getattr(self, name), name)
        if not isinstance(self.intent_version, int) or isinstance(self.intent_version, bool) or self.intent_version < 1:
            raise ValueError("intent_version must be >= 1")
        if not isinstance(self.prompt_version, int) or isinstance(self.prompt_version, bool) or self.prompt_version < 1:
            raise ValueError("prompt_version must be >= 1")
        if not isinstance(self.mode, QuickGenerationMode):
            raise ValueError("mode is invalid")
        if not isinstance(self.provider_profile_version, str) or not self.provider_profile_version.strip():
            raise ValueError("provider_profile_version is invalid")
        if not isinstance(self.route_capabilities, tuple) or not self.route_capabilities or tuple(sorted(self.route_capabilities)) != self.route_capabilities or len(set(self.route_capabilities)) != len(self.route_capabilities):
            raise ValueError("route_capabilities must be non-empty, unique and sorted")
        for capability in self.route_capabilities:
            _id(capability, "route_capability")
        if self.selected_capability not in self.route_capabilities:
            raise ValueError("selected_capability is not declared by the route")
        if not isinstance(self.references, tuple) or len({row.reference_id for row in self.references}) != len(self.references):
            raise ValueError("references must be a tuple with unique identities")
        if not isinstance(self.rights_authorization_ref, str) or not self.rights_authorization_ref.startswith("rights://"):
            raise ValueError("rights_authorization_ref is invalid")
        if not _CURRENCY_RE.fullmatch(self.currency):
            raise ValueError("currency is invalid")
        try:
            ceiling = Decimal(self.cost_ceiling)
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("cost_ceiling is invalid") from exc
        if not ceiling.is_finite() or ceiling < 0 or str(ceiling) != self.cost_ceiling:
            raise ValueError("cost_ceiling must be canonical non-negative decimal text")
        self._validate_mode()

    def _validate_mode(self) -> None:
        roles = [row.role for row in self.references]
        if self.mode is QuickGenerationMode.IMAGE:
            allowed = {QuickReferenceRole.GENERAL, QuickReferenceRole.CHARACTER_LOCK, QuickReferenceRole.SPACE_LOCK, QuickReferenceRole.COMPOSITION_LOCK}
            if any(role not in allowed for role in roles):
                raise ValueError("IMAGE reference role is invalid")
        elif self.mode is QuickGenerationMode.START_END:
            allowed = {QuickReferenceRole.START, QuickReferenceRole.END, QuickReferenceRole.CHARACTER_LOCK, QuickReferenceRole.SPACE_LOCK, QuickReferenceRole.COMPOSITION_LOCK}
            if (
                len(roles) < 2
                or roles.count(QuickReferenceRole.START) > 1
                or roles.count(QuickReferenceRole.END) > 1
                or any(role not in allowed for role in roles)
            ):
                raise ValueError("START_END requires multiple typed references")
        elif self.mode is QuickGenerationMode.VIDEO:
            allowed = {QuickReferenceRole.START, QuickReferenceRole.END, QuickReferenceRole.CHARACTER_LOCK, QuickReferenceRole.SPACE_LOCK, QuickReferenceRole.COMPOSITION_LOCK}
            if roles.count(QuickReferenceRole.START) != 1 or roles.count(QuickReferenceRole.END) > 1 or any(role not in allowed for role in roles):
                raise ValueError("VIDEO requires exactly one START and at most one END")
        elif self.mode is QuickGenerationMode.AUDIO:
            if len(roles) > 1 or any(role is not QuickReferenceRole.AUDIO_REFERENCE for role in roles):
                raise ValueError("AUDIO permits at most one audio reference")
            if roles and "AUDIO_REFERENCE" not in self.route_capabilities:
                raise ValueError("AUDIO reference capability is not declared")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "intent_version_schema": "1.0.0", "authority_kind": "QUICK_INTENT",
            "intent_id": self.intent_id, "intent_version": self.intent_version,
            "project_id": self.project_id, "scene_id": self.scene_id, "mode": self.mode.value,
            "target_slot_id": self.target_slot_id, "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version, "prompt_sha256": self.prompt_sha256,
            "compilation_sha256": self.compilation_sha256,
            "provider_profile_id": self.provider_profile_id,
            "provider_profile_version": self.provider_profile_version,
            "provider_profile_sha256": self.provider_profile_sha256,
            "selected_route_id": self.selected_route_id,
            "selected_capability": self.selected_capability,
            "route_capabilities": list(self.route_capabilities),
            "references": [row.to_dict() for row in self.references],
            "rights_authorization_ref": self.rights_authorization_ref,
            "currency": self.currency, "cost_ceiling": self.cost_ceiling,
            "execution_decision_id": self.execution_decision_id,
            "execution_decision_sha256": self.execution_decision_sha256,
            "expected_prompt_snapshot_sha256": self.expected_prompt_snapshot_sha256,
            "expected_production_snapshot_sha256": self.expected_production_snapshot_sha256,
            "expected_quick_snapshot_sha256": self.expected_quick_snapshot_sha256,
            "approved_plan_used": False, "human_go_used": False,
            "provider_execution_started": False, "candidate_created": False,
            "media_write_started": False,
        }
        body["intent_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QuickGenerationIntent":
        expected = set(cls(
            "x", 1, "x", "x", QuickGenerationMode.IMAGE, "x", "x", 1,
            "sha256:" + "0" * 64, "sha256:" + "0" * 64, "x", "1",
            "sha256:" + "0" * 64, "x", "X", ("X",), (), "rights://x", "USD", "0",
            "x", "sha256:" + "0" * 64, "sha256:" + "0" * 64,
            "sha256:" + "0" * 64, "sha256:" + "0" * 64,
        ).to_dict())
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("Quick intent fields are invalid")
        for name in ("approved_plan_used", "human_go_used", "provider_execution_started", "candidate_created", "media_write_started"):
            if value[name] is not False:
                raise ValueError("Quick intent authority boundary is invalid")
        body = {key: item for key, item in value.items() if key != "intent_sha256"}
        if value["intent_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("Quick intent checksum is invalid")
        return cls(
            intent_id=value["intent_id"], intent_version=value["intent_version"], project_id=value["project_id"],
            scene_id=value["scene_id"], mode=QuickGenerationMode(value["mode"]), target_slot_id=value["target_slot_id"],
            prompt_id=value["prompt_id"], prompt_version=value["prompt_version"], prompt_sha256=value["prompt_sha256"],
            compilation_sha256=value["compilation_sha256"], provider_profile_id=value["provider_profile_id"],
            provider_profile_version=value["provider_profile_version"], provider_profile_sha256=value["provider_profile_sha256"],
            selected_route_id=value["selected_route_id"], selected_capability=value["selected_capability"],
            route_capabilities=tuple(value["route_capabilities"]), references=tuple(QuickReferenceInput.from_dict(row) for row in value["references"]),
            rights_authorization_ref=value["rights_authorization_ref"], currency=value["currency"], cost_ceiling=value["cost_ceiling"],
            execution_decision_id=value["execution_decision_id"], execution_decision_sha256=value["execution_decision_sha256"],
            expected_prompt_snapshot_sha256=value["expected_prompt_snapshot_sha256"],
            expected_production_snapshot_sha256=value["expected_production_snapshot_sha256"],
            expected_quick_snapshot_sha256=value["expected_quick_snapshot_sha256"],
        )


class QuickGenerationRegistry:
    def __init__(self, project_id: str) -> None:
        _id(project_id, "project_id")
        self.project_id = project_id
        self.intents: list[QuickGenerationIntent] = []

    def add_intent(self, intent: QuickGenerationIntent) -> None:
        if intent.project_id != self.project_id:
            raise ProductError("ERR_QUICK_PROJECT_MISMATCH", "Quick intent belongs to another project", ProductErrorCategory.DATA_INTEGRITY)
        versions = [row.intent_version for row in self.intents if row.intent_id == intent.intent_id]
        expected = max(versions) + 1 if versions else 1
        if intent.intent_version != expected:
            raise ProductError("ERR_QUICK_INTENT_VERSION", "Quick intent versions must append without gaps", ProductErrorCategory.DATA_INTEGRITY, details={"expected_version": expected})
        if any(row.intent_id == intent.intent_id and row.intent_version == intent.intent_version for row in self.intents):
            raise ProductError("ERR_QUICK_INTENT_CONFLICT", "Quick intent version already exists", ProductErrorCategory.STATE)
        self.intents.append(intent)


class QuickGenerationAdoptionProjection:
    @staticmethod
    def project(
        *, intent: QuickGenerationIntent, generation_job_id: str,
        prompts: PromptGenerationRegistry, production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
    ) -> dict[str, Any]:
        attempt = prompts.attempts.get(generation_job_id)
        if attempt is None or attempt.output_candidate_id is None:
            status = "OUTPUT_NOT_REGISTERED"
            candidate = None
        else:
            if attempt.result is not GenerationResult.PASS or attempt.prompt_id != intent.prompt_id or attempt.prompt_version != intent.prompt_version or attempt.prompt_sha256 != intent.prompt_sha256 or attempt.slot_id != intent.target_slot_id:
                raise ProductError("ERR_QUICK_ADOPTION_ATTEMPT_MISMATCH", "Attempt does not match exact Quick intent", ProductErrorCategory.DATA_INTEGRITY)
            candidate = production.candidates.get(attempt.output_candidate_id)
            if candidate is None:
                status = "OUTPUT_NOT_REGISTERED"
            elif candidate.generation_job_id != generation_job_id or candidate.slot_id != intent.target_slot_id:
                raise ProductError("ERR_QUICK_ADOPTION_CANDIDATE_MISMATCH", "Candidate does not match Quick output identity", ProductErrorCategory.DATA_INTEGRITY)
            else:
                history = audits.candidate_history(candidate.candidate_id)
                if not history["audits"]:
                    status = "AUDIT_REQUIRED"
                elif not any(row["decision"] == HumanCandidateDecision.ACCEPT.value for row in history["human_decisions"]):
                    status = "ACCEPT_REQUIRED"
                else:
                    slot = production.slots.get(intent.target_slot_id)
                    if candidate.lifecycle_state is not CandidateLifecycle.LOCKED or slot is None or slot.status is not SlotStatus.LOCKED or slot.stale_state is not StaleState.CURRENT or slot.locked_candidate_id != candidate.candidate_id:
                        status = "LOCK_REQUIRED"
                    else:
                        status = "PRODUCTION_ADOPTED"
        body: dict[str, Any] = {
            "projection_version": "1.0.0", "intent_id": intent.intent_id,
            "intent_version": intent.intent_version, "generation_job_id": generation_job_id,
            "target_slot_id": intent.target_slot_id,
            "candidate_id": None if candidate is None else candidate.candidate_id,
            "asset_id": None if candidate is None else candidate.asset_id,
            "asset_sha256": None if candidate is None else candidate.asset_sha256,
            "status": status, "read_only": True, "candidate_created": False,
            "audit_written": False, "human_decision_written": False,
            "lock_written": False, "physical_delete_performed": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = [
    "QuickGenerationAdoptionProjection", "QuickGenerationIntent", "QuickGenerationMode",
    "QuickGenerationRegistry", "QuickReferenceInput", "QuickReferenceRole", "QuickReferenceSource",
]
