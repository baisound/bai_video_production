"""TASK-013 provider-neutral, non-executing SFX routing-plan compiler.

The compiler consumes immutable Creative Generation, Asset, rights,
provider-profile and admission Evidence coordinates.  It never calls a
provider, reads media, resolves credentials, invokes Foley generation or
publishes an Asset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable

from .ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from .creative_generation import CreativeGenerationMode
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
_RIGHTS_REF_RE = re.compile(r"^rights://[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_EVIDENCE_REF_RE = re.compile(r"^evidence://[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")


def _safe_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")
    return value


class SfxBindingState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class SfxRoutingState(str, Enum):
    ROUTE_SELECTED = "ROUTE_SELECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class SfxRouteDisposition(str, Enum):
    SELECTED = "SELECTED"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True, slots=True)
class SfxEvidenceBinding:
    state: SfxBindingState
    evidence_ref: str | None = None
    evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.state is SfxBindingState.BOUND_VERIFIED:
            if self.evidence_ref is None or self.evidence_sha256 is None:
                raise ValueError("BOUND_VERIFIED requires exact Evidence reference and digest")
        if self.state is SfxBindingState.CANONICAL_REF_NOT_PROVIDED:
            if self.evidence_ref is not None or self.evidence_sha256 is not None:
                raise ValueError("CANONICAL_REF_NOT_PROVIDED must not contain invented Evidence")
        if self.evidence_ref is not None and not _EVIDENCE_REF_RE.fullmatch(self.evidence_ref):
            raise ValueError("evidence_ref must use evidence:// and contain no secret")
        if self.evidence_sha256 is not None:
            validate_sha256(self.evidence_sha256, field_name="evidence_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "evidence_ref": self.evidence_ref,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class SfxCreativeGenerationIntentReference:
    request_id: str
    project_id: str
    scene_id: str
    slot_id: str
    prompt_id: str
    prompt_version: int
    prompt_body_sha256: str
    creative_plan_sha256: str
    provider_profile_id: str
    provider_profile_version: str
    provider_profile_sha256: str
    binding: SfxEvidenceBinding
    mode: CreativeGenerationMode = CreativeGenerationMode.SFX

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "project_id",
            "scene_id",
            "slot_id",
            "prompt_id",
            "provider_profile_id",
        ):
            _safe_id(getattr(self, name), name)
        if self.prompt_version < 1:
            raise ValueError("prompt_version must be positive")
        if not self.provider_profile_version or len(self.provider_profile_version) > 64:
            raise ValueError("provider_profile_version is invalid")
        for name in (
            "prompt_body_sha256",
            "creative_plan_sha256",
            "provider_profile_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if self.mode is not CreativeGenerationMode.SFX:
            raise ValueError("SFX routing accepts only SFX intent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "scene_id": self.scene_id,
            "slot_id": self.slot_id,
            "mode": self.mode.value,
            "prompt": {
                "prompt_id": self.prompt_id,
                "prompt_version": self.prompt_version,
                "body_sha256": self.prompt_body_sha256,
                "body_embedded": False,
            },
            "creative_plan_sha256": self.creative_plan_sha256,
            "provider_profile": {
                "profile_id": self.provider_profile_id,
                "profile_version": self.provider_profile_version,
                "profile_sha256": self.provider_profile_sha256,
            },
            "binding": self.binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SfxAssetReference:
    asset_id: str
    asset_revision_sha256: str
    asset_checksum: str
    binding: SfxEvidenceBinding

    def __post_init__(self) -> None:
        _safe_id(self.asset_id, "asset_id")
        validate_sha256(self.asset_revision_sha256, field_name="asset_revision_sha256")
        validate_sha256(self.asset_checksum, field_name="asset_checksum")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_revision_sha256": self.asset_revision_sha256,
            "asset_checksum": self.asset_checksum,
            "body_embedded": False,
            "binding": self.binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SfxRightsEvidenceReference:
    rights_authorization_ref: str
    binding: SfxEvidenceBinding

    def __post_init__(self) -> None:
        if not _RIGHTS_REF_RE.fullmatch(self.rights_authorization_ref):
            raise ValueError("rights_authorization_ref must use rights:// and contain no secret")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rights_authorization_ref": self.rights_authorization_ref,
            "binding": self.binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SfxRouteAdmissionEvidence:
    route_id: str
    capability: SfxEvidenceBinding
    license: SfxEvidenceBinding
    resource: SfxEvidenceBinding

    def __post_init__(self) -> None:
        _safe_id(self.route_id, "route_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "capability": self.capability.to_dict(),
            "license": self.license.to_dict(),
            "resource": self.resource.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SfxRoutingRequest:
    compilation_id: str
    intent: SfxCreativeGenerationIntentReference
    rights: SfxRightsEvidenceReference
    route_admission_evidence: tuple[SfxRouteAdmissionEvidence, ...]
    input_assets: tuple[SfxAssetReference, ...] = ()

    def __post_init__(self) -> None:
        _safe_id(self.compilation_id, "compilation_id")
        asset_ids = [item.asset_id for item in self.input_assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("input asset IDs must be unique")
        route_ids = [item.route_id for item in self.route_admission_evidence]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("route admission Evidence IDs must be unique")


@dataclass(frozen=True, slots=True)
class SfxRouteDecision:
    route_id: str
    provider_family: str
    provider_id: str
    model_id: str
    cost_class: str
    priority: int
    disposition: SfxRouteDisposition
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "provider_family": self.provider_family,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "cost_class": self.cost_class,
            "priority": self.priority,
            "disposition": self.disposition.value,
            "reason_codes": list(self.reason_codes),
            "credential_ref_persisted": False,
            "route_settings_persisted": False,
        }


@dataclass(frozen=True, slots=True)
class SfxRoutingPlan:
    compilation_id: str
    intent: SfxCreativeGenerationIntentReference
    rights: SfxRightsEvidenceReference
    input_assets: tuple[SfxAssetReference, ...]
    routing_state: SfxRoutingState
    global_reason_codes: tuple[str, ...]
    route_decisions: tuple[SfxRouteDecision, ...]
    selected_route_id: str | None

    @property
    def provider_execution_admitted(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": "1.0.0",
            "task_owner": "TASK-013",
            "plan_kind": "SFX_PROVIDER_NEUTRAL_ROUTING",
            "compilation_id": self.compilation_id,
            "intent": self.intent.to_dict(),
            "rights": self.rights.to_dict(),
            "input_assets": [
                item.to_dict()
                for item in sorted(self.input_assets, key=lambda item: item.asset_id)
            ],
            "routing_state": self.routing_state.value,
            "global_reason_codes": list(self.global_reason_codes),
            "route_decisions": [item.to_dict() for item in self.route_decisions],
            "selected_route_id": self.selected_route_id,
            "provider_execution_admitted": False,
            "provider_execution_started": False,
            "sfx_generation_started": False,
            "h3_foley_started": False,
            "asset_publication_started": False,
            "placement_started": False,
        }
        body["plan_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def _selection_mode_allows(mode: SelectionMode, route: ModelRoute) -> bool:
    if mode is SelectionMode.AI:
        return route.provider_family is not ProviderFamily.NON_AI_LIBRARY
    if mode is SelectionMode.FREE:
        return route.is_free
    if mode is SelectionMode.OFFLINE_ONLY:
        return route.is_offline
    return mode is SelectionMode.AUTO


def _global_binding_state(
    request: SfxRoutingRequest,
) -> tuple[SfxRoutingState | None, tuple[str, ...]]:
    bindings: list[tuple[str, SfxEvidenceBinding]] = [
        ("CREATIVE_INTENT", request.intent.binding),
        ("RIGHTS", request.rights.binding),
    ]
    bindings.extend(
        (f"ASSET:{item.asset_id}", item.binding)
        for item in sorted(request.input_assets, key=lambda item: item.asset_id)
    )
    mismatch = tuple(
        f"{name}_MISMATCH"
        for name, binding in bindings
        if binding.state is SfxBindingState.MISMATCH
    )
    if mismatch:
        return SfxRoutingState.BLOCKED, mismatch
    unresolved = tuple(
        f"{name}_{binding.state.value}"
        for name, binding in bindings
        if binding.state
        in {SfxBindingState.UNKNOWN, SfxBindingState.CANONICAL_REF_NOT_PROVIDED}
    )
    if unresolved:
        return SfxRoutingState.UNKNOWN, unresolved
    return None, ()


class SfxRoutingCompiler:
    """Compile a deterministic SFX route selection without executing it."""

    @classmethod
    def compile(
        cls,
        request: SfxRoutingRequest,
        *,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        required_capabilities: Iterable[str] = ("SFX",),
    ) -> SfxRoutingPlan:
        profile_body = profile.to_dict()
        if (
            request.intent.provider_profile_id != profile.profile_id
            or request.intent.provider_profile_version != profile.profile_version
            or request.intent.provider_profile_sha256 != profile_body["profile_sha256"]
        ):
            raise ValueError(
                "Creative Generation intent provider profile does not match exact active profile"
            )

        required = tuple(dict.fromkeys(required_capabilities))
        if not required or any(not _ID_RE.fullmatch(value) for value in required):
            raise ValueError("required_capabilities must be non-empty unique safe identifiers")
        evidence_by_route = {
            item.route_id: item for item in request.route_admission_evidence
        }
        mode = profile.mode_for(AiWorkload.AUDIO)
        global_state, global_reasons = _global_binding_state(request)
        if mode is SelectionMode.DISABLED:
            global_state = SfxRoutingState.BLOCKED
            global_reasons = (*global_reasons, "AUDIO_WORKLOAD_DISABLED")

        decisions: list[SfxRouteDecision] = []
        selected_route_id: str | None = None
        saw_unknown = global_state is SfxRoutingState.UNKNOWN
        routes = sorted(
            (route for route in profile.routes if route.workload is AiWorkload.AUDIO),
            key=lambda route: (route.priority, route.route_id),
        )
        for route in routes:
            reasons: list[str] = []
            evidence = evidence_by_route.get(route.route_id)
            if global_state is not None:
                reasons.append("GLOBAL_BINDING_NOT_ADMITTED")
            if not route.enabled:
                reasons.append("ROUTE_DISABLED")
            if route.route_id not in availability.available_route_ids:
                reasons.append("ROUTE_UNAVAILABLE")
            if (
                route.credential_ref
                and route.credential_ref not in availability.available_credential_refs
            ):
                reasons.append("CREDENTIAL_UNAVAILABLE")
            if not set(required).issubset(route.capabilities):
                reasons.append("CAPABILITY_NOT_CONFIGURED")
            if not _selection_mode_allows(mode, route):
                reasons.append("SELECTION_MODE_EXCLUDED")
            if evidence is None:
                reasons.append("ROUTE_ADMISSION_EVIDENCE_NOT_PROVIDED")
                saw_unknown = True
            else:
                for label, binding in (
                    ("CAPABILITY", evidence.capability),
                    ("LICENSE", evidence.license),
                    ("RESOURCE", evidence.resource),
                ):
                    if binding.state is SfxBindingState.MISMATCH:
                        reasons.append(f"{label}_MISMATCH")
                    elif binding.state is not SfxBindingState.BOUND_VERIFIED:
                        reasons.append(f"{label}_{binding.state.value}")
                        saw_unknown = True
            eligible = not reasons and selected_route_id is None
            if eligible:
                selected_route_id = route.route_id
                disposition = SfxRouteDisposition.SELECTED
                reasons.append("SELECTED_HIGHEST_PRIORITY_ELIGIBLE_ROUTE")
            else:
                disposition = SfxRouteDisposition.EXCLUDED
                if not reasons:
                    reasons.append("NOT_SELECTED_LOWER_PRIORITY")
            decisions.append(
                SfxRouteDecision(
                    route.route_id,
                    route.provider_family.value,
                    route.provider_id,
                    route.model_id,
                    route.cost_class.value,
                    route.priority,
                    disposition,
                    tuple(reasons),
                )
            )

        if selected_route_id is not None:
            routing_state = SfxRoutingState.ROUTE_SELECTED
        elif global_state is not None:
            routing_state = global_state
        elif saw_unknown:
            routing_state = SfxRoutingState.UNKNOWN
        else:
            routing_state = SfxRoutingState.BLOCKED
        if not routes:
            global_reasons = (*global_reasons, "NO_AUDIO_SFX_ROUTES_CONFIGURED")

        return SfxRoutingPlan(
            request.compilation_id,
            request.intent,
            request.rights,
            request.input_assets,
            routing_state,
            tuple(global_reasons),
            tuple(decisions),
            selected_route_id,
        )
