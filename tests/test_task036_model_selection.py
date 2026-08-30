from __future__ import annotations

import copy

import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task036_model_selection import Task036ModelSelectionProjection


def _form():
    def workload(name, route_id, family, model, cost, *, credential=False, configured=True):
        return {
            "workload": name,
            "selection_mode": "AUTO",
            "status": "READY",
            "error_code": None,
            "preferred_route_id": route_id,
            "routes": [{
                "route_id": route_id, "provider_family": family,
                "provider_id": family.casefold(), "model_id": model,
                "cost_class": cost, "capabilities": [f"{name}_GENERATION"],
                "credential_required": credential, "credential_configured": configured,
                "enabled": True, "implementation_status": "LOCAL_RUNTIME" if cost.startswith("LOCAL") else "IMPLEMENTED",
            }],
        }
    return {
        "profile_id": "project-profile", "profile_version": "3", "revision": 7,
        "workloads": [
            workload("PLANNING", "planning-route", "OPENAI", "plan-model", "CLOUD_PAID_AI", credential=True),
            workload("IMAGE", "image-route", "COMFYUI", "image-workflow", "LOCAL_FREE_AI"),
            workload("VIDEO", "video-route", "COMFYUI", "video-workflow", "LOCAL_FREE_AI"),
            workload("AUDIO", "audio-route", "ELEVENLABS", "voice-model", "CLOUD_PAID_AI", credential=True),
            workload("MUSIC", "music-route", "SUNO_API", "music-model", "CLOUD_PAID_AI", credential=True),
        ],
    }


def test_projects_project_scene_and_quick_coordinates_without_effects():
    projected = Task036ModelSelectionProjection.project(
        _form(),
        prompt_snapshot={"prompts": [{
            "prompt_id": "prompt-1", "prompt_version": 2, "scene_id": "scene-1", "slot_id": "slot-1",
            "compilation_binding": {"selected_route_id": "image-route"},
        }]},
        quick_snapshot={"intents": [
            {"intent_id": "quick-1", "intent_version": 1, "mode": "VIDEO", "scene_id": "scene-1", "selected_route_id": "video-route", "selected_capability": "VIDEO_GENERATION"},
            {"intent_id": "quick-audio", "intent_version": 1, "mode": "AUDIO", "scene_id": "scene-1", "selected_route_id": "audio-route", "selected_capability": "AUDIO_GENERATION"},
        ]},
    )
    assert [row["page_id"] for row in projected["selectors"]] == ["PLANNING", "IMAGE", "VIDEO", "QUICK_IMAGE", "QUICK_VIDEO", "AUDIO", "MUSIC"]
    assert projected["scene_bindings"][0]["coordinate_state"] == "CURRENT_CONFIGURED"
    assert projected["quick_bindings"][0]["selected_route_id"] == "video-route"
    assert projected["delegated_audio_owner"] == "DEVELOPER2"
    assert projected["delegated_audio_intent_count"] == 1
    assert projected["provider_execution_started"] is False
    assert projected["paid_execution_authorized"] is False
    assert projected["generation_started"] is False
    assert "credential://" not in str(projected)
    digest = projected.pop("projection_sha256")
    assert digest == sha256_bytes(canonical_json_bytes(projected))


def test_projection_is_deterministic_and_reports_license_resource_unknown():
    first = Task036ModelSelectionProjection.project(_form())
    second = Task036ModelSelectionProjection.project(copy.deepcopy(_form()))
    assert first == second
    planning = next(row for row in first["selectors"] if row["page_id"] == "PLANNING")
    candidate = planning["candidates"][0]
    assert candidate["paid"] is True
    assert candidate["rights_license_state"] == "UNKNOWN_NOT_EVIDENCED"
    assert candidate["resource_state"] == "UNKNOWN_NOT_EVIDENCED"
    assert candidate["runtime_admission_state"] == "NOT_AUTHORIZED"


def test_local_audio_routes_are_visible_but_not_selectable_without_public_inventory():
    form = _form()
    for workload in form["workloads"]:
        if workload["workload"] not in {"AUDIO", "MUSIC"}:
            continue
        route = workload["routes"][0]
        route["provider_family"] = "LOCAL_OPEN_SOURCE"
        route["provider_id"] = "local-audio"
        route["cost_class"] = "LOCAL_FREE_AI"
        route["credential_required"] = False
        route["credential_configured"] = False
        route["implementation_status"] = "LOCAL_RUNTIME"

    projected = Task036ModelSelectionProjection.project(form)
    for workload in ("AUDIO", "MUSIC"):
        selector = next(item for item in projected["selectors"] if item["workload"] == workload)
        candidate = selector["candidates"][0]
        assert selector["available"] is False
        assert selector["unavailable_reason"] == "NO_SELECTABLE_LOCAL_AUDIO_MODEL"
        assert candidate["configuration_selectable"] is False
        assert "LOCAL_AUDIO_INVENTORY_NOT_BOUND" in candidate["configuration_blockers"]
@pytest.mark.parametrize("field", ["api_key", "secret", "credential_ref", "path", "runner", "callback", "raw_bytes"])


def test_forbidden_secret_or_effect_surfaces_fail_closed(field):
    form = _form()
    form[field] = "forbidden"
    with pytest.raises(ValueError, match="forbidden"):
        Task036ModelSelectionProjection.project(form)


def test_mismatch_and_caps_fail_closed():
    form = _form()
    form["workloads"][1]["preferred_route_id"] = "other-route"
    with pytest.raises(ValueError, match="preferred route"):
        Task036ModelSelectionProjection.project(form)
    form = _form()
    form["workloads"][1]["routes"] *= 65
    with pytest.raises(ValueError, match="bounded"):
        Task036ModelSelectionProjection.project(form)
    form = _form()
    form["workloads"][1]["routes"][0]["capabilities"] = ["IMAGE_GENERATION", "IMAGE_GENERATION"]
    with pytest.raises(ValueError, match="unique"):
        Task036ModelSelectionProjection.project(form)


def test_quick_cross_workload_binding_is_visible_but_not_repaired():
    projected = Task036ModelSelectionProjection.project(
        _form(),
        quick_snapshot={"intents": [{
            "intent_id": "quick-1", "intent_version": 1, "mode": "VIDEO", "scene_id": "scene-1",
            "selected_route_id": "image-route", "selected_capability": "VIDEO_GENERATION",
        }]},
    )
    assert projected["quick_bindings"][0]["coordinate_state"] == "WORKLOAD_MISMATCH"
