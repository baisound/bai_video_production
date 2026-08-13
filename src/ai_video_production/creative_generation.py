"""TASK-013 provider-neutral creative-generation routing foundation.

The module selects an already configured provider route and compiles a durable
execution plan.  It intentionally does *not* call any provider.  Paid cloud
execution remains a separate, explicit authorization boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable

from .ai_connections import (
    AiConnectionProfile,
    AiConnectionResolver,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
)
from .errors import ProductError, ProductErrorCategory
from .production_control import ProductionControlRegistry
from .production_orchestrator import GenerationQueueAdmissionResult, GenerationQueueAdmissionService
from .prompt_registry import PromptEntity, RegenerationStrategy
from .serialization import canonical_json_bytes, sha256_bytes
from .shot_feasibility import ShotFeasibilityAssessment


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_RIGHTS_REF_RE = re.compile(r"rights://[A-Za-z0-9][A-Za-z0-9._/-]{0,199}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class CreativeGenerationMode(str, Enum):
    TEXT_TO_IMAGE = "TEXT_TO_IMAGE"
    IMAGE_TO_IMAGE = "IMAGE_TO_IMAGE"
    TEXT_TO_VIDEO = "TEXT_TO_VIDEO"
    IMAGE_TO_VIDEO = "IMAGE_TO_VIDEO"
    SFX = "SFX"
    MUSIC_GENERATION = "MUSIC_GENERATION"

    @property
    def workload(self) -> AiWorkload:
        if self in {self.TEXT_TO_IMAGE, self.IMAGE_TO_IMAGE}:
            return AiWorkload.IMAGE
        if self in {self.TEXT_TO_VIDEO, self.IMAGE_TO_VIDEO}:
            return AiWorkload.VIDEO
        if self is self.SFX:
            return AiWorkload.AUDIO
        assert self is self.MUSIC_GENERATION
        return AiWorkload.MUSIC

    @property
    def required_capability(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CreativeGenerationRequest:
    request_id: str
    scene_id: str
    slot_id: str
    mode: CreativeGenerationMode
    prompt: PromptEntity
    rights_authorization_ref: str
    required_input_slot_ids: tuple[str, ...] = ()
    strategy: RegenerationStrategy = RegenerationStrategy.TEXT_PROMPT
    explicit_paid_execution_authorization: bool = False

    def __post_init__(self) -> None:
        _id(self.request_id, "request_id")
        _id(self.scene_id, "scene_id")
        _id(self.slot_id, "slot_id")
        if self.prompt.scene_id is not None and self.prompt.scene_id != self.scene_id:
            raise ValueError("prompt scene_id does not match generation request")
        if self.prompt.slot_id is not None and self.prompt.slot_id != self.slot_id:
            raise ValueError("prompt slot_id does not match generation request")
        if not _RIGHTS_REF_RE.fullmatch(self.rights_authorization_ref):
            raise ValueError("rights_authorization_ref must use rights:// and contain no secret")
        for value in self.required_input_slot_ids:
            _id(value, "required_input_slot_id")
        if len(set(self.required_input_slot_ids)) != len(self.required_input_slot_ids):
            raise ValueError("required_input_slot_ids must be unique")


@dataclass(frozen=True, slots=True)
class CreativeGenerationPlan:
    request_id: str
    scene_id: str
    slot_id: str
    mode: CreativeGenerationMode
    workload: AiWorkload
    capability: str
    prompt_id: str
    prompt_version: int
    prompt_sha256: str
    input_asset_hashes: tuple[str, ...]
    strategy: RegenerationStrategy
    provider_profile_id: str
    provider_profile_version: str
    provider_profile_sha256: str
    route_id: str
    provider_family: str
    provider_id: str
    model_id: str
    cost_class: CostClass
    route_requires_credential: bool
    rights_authorization_ref: str
    admission: GenerationQueueAdmissionResult
    paid_execution_authorized: bool

    @property
    def paid_execution_required(self) -> bool:
        return self.cost_class is CostClass.CLOUD_PAID_AI

    @property
    def ready_for_provider_execution(self) -> bool:
        return self.admission.ready and (not self.paid_execution_required or self.paid_execution_authorized)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "plan_version": "1.0.0",
            "task_owner": "TASK-013",
            "request_id": self.request_id,
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "mode": self.mode.value,
            "workload": self.workload.value,
            "capability": self.capability,
            "prompt": {
                "prompt_id": self.prompt_id,
                "prompt_version": self.prompt_version,
                "body_sha256": self.prompt_sha256,
                "input_asset_hashes": list(self.input_asset_hashes),
                "body_embedded": False,
            },
            "strategy_level": int(self.strategy),
            "provider_profile": {
                "profile_id": self.provider_profile_id,
                "profile_version": self.provider_profile_version,
                "profile_sha256": self.provider_profile_sha256,
            },
            "selected_route": {
                "route_id": self.route_id,
                "provider_family": self.provider_family,
                "provider_id": self.provider_id,
                "model_id": self.model_id,
                "cost_class": self.cost_class.value,
                "credential_required": self.route_requires_credential,
                "credential_ref_persisted": False,
                "route_settings_persisted": False,
            },
            "rights_authorization_ref": self.rights_authorization_ref,
            "admission": self.admission.to_dict(),
            "paid_execution_required": self.paid_execution_required,
            "paid_execution_authorized": self.paid_execution_authorized,
            "ready_for_provider_execution": self.ready_for_provider_execution,
            "provider_execution_started": False,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class CreativeGenerationPlanner:
    """Select a provider route and compile a non-executing generation plan."""

    @staticmethod
    def _select_route(
        request: CreativeGenerationRequest,
        *,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        extra_required_capabilities: Iterable[str],
    ) -> ModelRoute:
        capabilities = tuple(dict.fromkeys((request.mode.required_capability, *extra_required_capabilities)))
        return AiConnectionResolver.resolve(
            profile,
            request.mode.workload,
            availability,
            required_capabilities=capabilities,
        )

    @classmethod
    def compile(
        cls,
        request: CreativeGenerationRequest,
        *,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        plan_approved: bool,
        feasibility: ShotFeasibilityAssessment,
        registry: ProductionControlRegistry,
        extra_required_capabilities: Iterable[str] = (),
    ) -> CreativeGenerationPlan:
        if request.prompt.provider_profile_id != profile.profile_id:
            raise ProductError(
                "ERR_GENERATION_PROFILE_ID_MISMATCH",
                "Prompt provider profile identity does not match the active AI Connection Profile",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if request.prompt.provider_profile_version != profile.profile_version:
            raise ProductError(
                "ERR_GENERATION_PROFILE_VERSION_MISMATCH",
                "Prompt provider profile version does not match the active AI Connection Profile",
                ProductErrorCategory.DATA_INTEGRITY,
            )

        route = cls._select_route(
            request,
            profile=profile,
            availability=availability,
            extra_required_capabilities=extra_required_capabilities,
        )
        paid_required = route.cost_class is CostClass.CLOUD_PAID_AI
        admission = GenerationQueueAdmissionService.evaluate(
            scene_id=request.scene_id,
            slot_id=request.slot_id,
            plan_approved=plan_approved,
            feasibility=feasibility,
            required_input_slot_ids=request.required_input_slot_ids,
            registry=registry,
            cost_authorized=request.explicit_paid_execution_authorization,
            cost_required=paid_required,
        )
        return CreativeGenerationPlan(
            request_id=request.request_id,
            scene_id=request.scene_id,
            slot_id=request.slot_id,
            mode=request.mode,
            workload=request.mode.workload,
            capability=request.mode.required_capability,
            prompt_id=request.prompt.prompt_id,
            prompt_version=request.prompt.prompt_version,
            prompt_sha256=request.prompt.body_sha256,
            input_asset_hashes=request.prompt.input_asset_hashes,
            strategy=request.strategy,
            provider_profile_id=profile.profile_id,
            provider_profile_version=profile.profile_version,
            provider_profile_sha256=profile.to_dict()["profile_sha256"],
            route_id=route.route_id,
            provider_family=route.provider_family.value,
            provider_id=route.provider_id,
            model_id=route.model_id,
            cost_class=route.cost_class,
            route_requires_credential=route.credential_ref is not None,
            rights_authorization_ref=request.rights_authorization_ref,
            admission=admission,
            paid_execution_authorized=request.explicit_paid_execution_authorization,
        )

    @staticmethod
    def require_provider_execution_authorized(plan: CreativeGenerationPlan) -> None:
        if plan.ready_for_provider_execution:
            return
        if plan.paid_execution_required and not plan.paid_execution_authorized:
            raise ProductError(
                "ERR_GENERATION_PAID_EXECUTION_NOT_AUTHORIZED",
                "The selected cloud-paid provider route requires explicit execution authorization",
                ProductErrorCategory.AUTHORIZATION,
                details={"route_id": plan.route_id, "cost_class": plan.cost_class.value},
            )
        raise ProductError(
            "ERR_GENERATION_PLAN_NOT_READY",
            "Creative generation plan is not ready for provider execution",
            ProductErrorCategory.STATE,
        )
