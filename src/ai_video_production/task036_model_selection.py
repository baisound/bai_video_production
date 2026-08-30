"""TASK-036 P-UX-2A1 secret-free Provider/Model selection projection.

The projection composes existing TASK-028, TASK-040 and TASK-042 receipts.  It
does not create another settings or intent store and never grants execution
authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes


_PAGE_WORKLOADS = (
    ("PLANNING", "PLANNING"),
    ("IMAGE", "IMAGE"),
    ("VIDEO", "VIDEO"),
    ("QUICK_IMAGE", "IMAGE"),
    ("QUICK_VIDEO", "VIDEO"),
    ("AUDIO", "AUDIO"),
    ("MUSIC", "MUSIC"),
)
_QUICK_WORKLOAD = {"IMAGE": "IMAGE", "START_END": "IMAGE", "VIDEO": "VIDEO"}
_FORBIDDEN_KEYS = {
    "api_key", "apikey", "access_token", "token", "secret", "password",
    "credential_ref", "endpoint_ref", "raw_bytes", "path", "runner", "callback",
}
_MAX_ROUTES = 64
_MAX_PROMPTS = 256
_MAX_QUICK_INTENTS = 256


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _sequence(value: object, name: str, maximum: int) -> Sequence[object]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ValueError(f"{name} must be a bounded sequence")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be non-empty bounded text")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _reject_secret_surface(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in _FORBIDDEN_KEYS:
                raise ValueError(f"forbidden secret/effect field: {key}")
            _reject_secret_surface(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secret_surface(child)


def _candidate(route: Mapping[str, object]) -> dict[str, object]:
    route_id = _text(route.get("route_id"), "route_id")
    provider = _text(route.get("provider_family"), "provider_family")
    model = _text(route.get("model_id"), "model_id")
    cost = _text(route.get("cost_class"), "cost_class")
    enabled = route.get("enabled")
    credential_required = route.get("credential_required")
    credential_configured = route.get("credential_configured")
    if not all(isinstance(item, bool) for item in (enabled, credential_required, credential_configured)):
        raise ValueError("route booleans are invalid")
    capabilities = _sequence(route.get("capabilities", []), "capabilities", 64)
    if any(not isinstance(item, str) or not item for item in capabilities):
        raise ValueError("capabilities are invalid")
    if len(capabilities) != len(set(capabilities)):
        raise ValueError("capabilities must be unique")
    blockers: list[str] = []
    if not enabled:
        blockers.append("ROUTE_DISABLED")
    if credential_required and not credential_configured:
        blockers.append("CREDENTIAL_MISSING")
    implementation = _text(route.get("implementation_status"), "implementation_status")
    if implementation not in {"IMPLEMENTED", "LOCAL_RUNTIME"}:
        blockers.append("ADAPTER_NOT_CURRENTLY_IMPLEMENTED")
    return {
        "route_id": route_id,
        "provider_family": provider,
        "provider_id": _text(route.get("provider_id"), "provider_id"),
        "model_id": model,
        "cost_class": cost,
        "local": cost.startswith("LOCAL_") or cost == "NON_AI_FREE",
        "paid": cost == "CLOUD_PAID_AI",
        "capabilities": sorted(set(capabilities)),
        "implementation_status": implementation,
        "credential_required": credential_required,
        "credential_configured": credential_configured,
        "configuration_selectable": enabled,
        "configuration_blockers": blockers,
        "rights_license_state": "UNKNOWN_NOT_EVIDENCED",
        "resource_state": "UNKNOWN_NOT_EVIDENCED",
        "runtime_admission_state": "NOT_AUTHORIZED",
    }


class Task036ModelSelectionProjection:
    """Compose canonical selection receipts without executing or persisting work."""

    @classmethod
    def project(
        cls,
        connection_form: Mapping[str, object],
        *,
        prompt_snapshot: Mapping[str, object] | None = None,
        quick_snapshot: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        form = _mapping(connection_form, "connection_form")
        _reject_secret_surface(form)
        revision = _nonnegative_int(form.get("revision"), "revision")
        workloads = _sequence(form.get("workloads"), "workloads", 5)
        by_workload: dict[str, dict[str, object]] = {}
        all_routes: dict[str, tuple[str, dict[str, object]]] = {}
        for raw_workload in workloads:
            row = _mapping(raw_workload, "workload")
            workload = _text(row.get("workload"), "workload")
            if workload in by_workload:
                raise ValueError("duplicate workload")
            routes = [_candidate(_mapping(item, "route")) for item in _sequence(row.get("routes"), "routes", _MAX_ROUTES)]
            route_ids = [str(item["route_id"]) for item in routes]
            if len(route_ids) != len(set(route_ids)):
                raise ValueError("duplicate route")
            preferred = row.get("preferred_route_id")
            if preferred is not None and (not isinstance(preferred, str) or preferred not in route_ids):
                raise ValueError("preferred route is not in its workload")
            for candidate in routes:
                route_id = str(candidate["route_id"])
                if route_id in all_routes:
                    raise ValueError("route_id is not globally unique")
                all_routes[route_id] = (workload, candidate)
            by_workload[workload] = {
                "selection_mode": _text(row.get("selection_mode"), "selection_mode"),
                "preferred_route_id": preferred,
                "status": _text(row.get("status"), "status"),
                "error_code": row.get("error_code"),
                "candidates": routes,
            }

        selectors: list[dict[str, object]] = []
        for page_id, workload in _PAGE_WORKLOADS:
            source = by_workload.get(workload)
            if source is None:
                selectors.append({
                    "page_id": page_id, "workload": workload, "available": False,
                    "unavailable_reason": "WORKLOAD_NOT_CONFIGURED", "candidates": [],
                })
                continue
            selectors.append({
                "page_id": page_id,
                "workload": workload,
                "scope": "PROJECT_DEFAULT",
                "available": True,
                **source,
            })

        scene_bindings: list[dict[str, object]] = []
        if prompt_snapshot is not None:
            prompts = _sequence(_mapping(prompt_snapshot, "prompt_snapshot").get("prompts", []), "prompts", _MAX_PROMPTS)
            for raw_prompt in prompts:
                prompt = _mapping(raw_prompt, "prompt")
                binding = prompt.get("compilation_binding")
                if binding is None:
                    continue
                bound = _mapping(binding, "compilation_binding")
                route_id = _text(bound.get("selected_route_id"), "selected_route_id")
                route = all_routes.get(route_id)
                scene_bindings.append({
                    "prompt_id": _text(prompt.get("prompt_id"), "prompt_id"),
                    "prompt_version": _nonnegative_int(prompt.get("prompt_version"), "prompt_version"),
                    "scene_id": prompt.get("scene_id"),
                    "slot_id": prompt.get("slot_id"),
                    "selected_route_id": route_id,
                    "coordinate_state": "CURRENT_CONFIGURED" if route else "UNKNOWN_ROUTE",
                    "provider_execution_started": False,
                })

        quick_bindings: list[dict[str, object]] = []
        delegated_audio_intent_count = 0
        if quick_snapshot is not None:
            intents = _sequence(_mapping(quick_snapshot, "quick_snapshot").get("intents", []), "intents", _MAX_QUICK_INTENTS)
            for raw_intent in intents:
                intent = _mapping(raw_intent, "quick_intent")
                mode = _text(intent.get("mode"), "quick mode")
                if mode == "AUDIO":
                    delegated_audio_intent_count += 1
                    continue
                workload = _QUICK_WORKLOAD.get(mode)
                route_id = _text(intent.get("selected_route_id"), "selected_route_id")
                route = all_routes.get(route_id)
                if workload is None:
                    state = "UNSUPPORTED_MODE"
                elif route is None:
                    state = "UNKNOWN_ROUTE"
                elif route[0] != workload:
                    state = "WORKLOAD_MISMATCH"
                else:
                    state = "CURRENT_CONFIGURED"
                quick_bindings.append({
                    "intent_id": _text(intent.get("intent_id"), "intent_id"),
                    "intent_version": _nonnegative_int(intent.get("intent_version"), "intent_version"),
                    "mode": mode,
                    "workload": workload,
                    "scene_id": intent.get("scene_id"),
                    "selected_route_id": route_id,
                    "selected_capability": intent.get("selected_capability"),
                    "coordinate_state": state,
                    "provider_execution_started": False,
                })

        body: dict[str, object] = {
            "projection_version": "1.0.0",
            "profile_id": _text(form.get("profile_id"), "profile_id"),
            "profile_version": _text(form.get("profile_version"), "profile_version"),
            "settings_revision": revision,
            "selectors": selectors,
            "scene_bindings": scene_bindings,
            "quick_bindings": quick_bindings,
            "delegated_audio_owner": "DEVELOPER2",
            "delegated_audio_intent_count": delegated_audio_intent_count,
            "credential_values_redisplayed": False,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "generation_started": False,
        }
        body["projection_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


__all__ = ["Task036ModelSelectionProjection"]
