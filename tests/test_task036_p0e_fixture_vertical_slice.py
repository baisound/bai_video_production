from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from pathlib import Path

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.audit_application import Task038AuditApplication
from ai_video_production.candidate_audit import AuditRecord, AuditorKind
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.connection_settings_web import ConnectionSettingsWebService
from ai_video_production.continuity_application import Task039ContinuityApplication
from ai_video_production.creative_generation_execution_application import (
    LocalGenerationExecutionResult,
    LocalGenerationRuntimeReadiness,
    Task013CreativeGenerationExecutionApplication,
)
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.durable_product_job import (
    DurableProductJobState,
    DurableProductJobStore,
    durable_job_shell_projection,
)
from ai_video_production.errors import ProductError
from ai_video_production.export_queue import (
    ExportAuthorityClass,
    ExportOutputContract,
    ExportPreparation,
    ExportPreset,
)
from ai_video_production.export_queue_application import ExportQueueApplication
from ai_video_production.final_review_application import FinalReviewApprovalApplication
from ai_video_production.final_review_gate import (
    FinalReviewExternalGateReceipt,
    FinalReviewGateId,
    FinalReviewGateState,
)
from ai_video_production.generation_output_adoption_application import (
    AdoptedAssetIdentity,
    Task027GenerationOutputAdoptionApplication,
)
from ai_video_production.generation_queue_application import Task027GenerationQueueApplication
from ai_video_production.generation_safety_application import Task013GenerationSafetyApplication
from ai_video_production.local_ollama_planning import parse_local_planning_candidate
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task036_planning_generation_application import (
    Task036PlanningGenerationApplication,
)
from ai_video_production.task036_shell_ui import Task036ShellBridge


PROJECT_ID = "project-p0e-fixture"
FIXTURE_CONTRACT_VERSION = "task036-p0e-fixture/v1"


def _local_profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "profile-p0e-local",
        "1.0.0",
        SelectionMode.OFFLINE_ONLY,
        (
            ModelRoute(
                "planning-local",
                AiWorkload.PLANNING,
                ProviderFamily.LOCAL_OPEN_SOURCE,
                "ollama",
                "qwen3:8b",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_GENERATION",),
            ),
            ModelRoute(
                "image-local",
                AiWorkload.IMAGE,
                ProviderFamily.COMFYUI,
                "comfy-image",
                "flux-schnell-fixture",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_TO_IMAGE",),
            ),
            ModelRoute(
                "video-local",
                AiWorkload.VIDEO,
                ProviderFamily.COMFYUI,
                "comfy-video",
                "wan-fixture",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_TO_VIDEO",),
            ),
            ModelRoute(
                "audio-local-unavailable",
                AiWorkload.AUDIO,
                ProviderFamily.LOCAL_OPEN_SOURCE,
                "local-audio",
                "voice-fixture-not-installed",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_TO_SPEECH",),
            ),
            ModelRoute(
                "music-local-unavailable",
                AiWorkload.MUSIC,
                ProviderFamily.LOCAL_OPEN_SOURCE,
                "local-audio",
                "music-fixture-not-installed",
                CostClass.LOCAL_FREE_AI,
                capabilities=("TEXT_TO_MUSIC",),
            ),
        ),
    )


def _planning_candidate():
    return parse_local_planning_candidate(
        {
            "intent": {
                "purpose": "Product introduction",
                "audience": "Creators",
                "platform": "YouTube",
                "aspect_ratio": "16:9",
                "target_duration_seconds": 2,
                "style_tone": "Clear",
                "story_message": "Show the safe local workflow",
                "language": "ja-JP",
                "free_text": "",
                "rights_constraints": [],
            },
            "proposal_title": "P0-E fixture vertical",
            "timeline_fps": 30,
            "sections": [
                {
                    "section_id": "concept",
                    "kind": "CONCEPT",
                    "title": "Concept",
                    "body": "One fixture-backed local video scene",
                }
            ],
            "scenes": [
                {
                    "scene_id": "SC01",
                    "start_frame": 0,
                    "end_frame": 60,
                    "narrative_role": "Opening",
                    "source_strategy": "COMPOSITE",
                    "generation_risk": "A_LOW_TEXT",
                    "camera_motion": "STATIC",
                    "audio": {
                        "narration": False,
                        "dialogue": False,
                        "sound_effects": [],
                        "bgm": False,
                        "sound_logo": False,
                    },
                    "locked_reference": False,
                    "post_composite_text": False,
                    "final_hold_frames": 0,
                }
            ],
            "rights_warnings": [],
        }
    )


class _FixturePlanningAdapter:
    def __init__(self) -> None:
        self.ready_calls = 0
        self.generate_calls = 0

    def ready(self) -> bool:
        self.ready_calls += 1
        return True

    def generate(self, _prompt: str):
        self.generate_calls += 1
        return _planning_candidate()


class _FixtureVideoPort:
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.preflight_calls = 0
        self.execute_calls = 0

    def preflight(self) -> LocalGenerationRuntimeReadiness:
        self.preflight_calls += 1
        return LocalGenerationRuntimeReadiness(
            "video-local",
            "comfy-video",
            "wan-fixture",
            "sha256:" + "7" * 64,
            6,
            "P0E_PUBLIC_SAFE_FIXTURE_V1",
        )

    def execute(self, route, request) -> LocalGenerationExecutionResult:
        self.execute_calls += 1
        payload = canonical_json_bytes(
            {
                "fixture_version": "1.0.0",
                "execution_id": request.execution_id,
                "scene_id": request.scene_id,
                "slot_id": request.slot_id,
                "prompt_sha256": request.prompt_sha256,
            }
        )
        target = self.output_root / request.execution_id / "fixture-video.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return LocalGenerationExecutionResult(
            route.route_id,
            route.provider_family,
            route.provider_id,
            route.model_id,
            request.capability,
            "fixture-operation-1",
            f"project-output://{request.execution_id}/fixture-video.json",
            sha256_bytes(payload),
            "VIDEO",
            1,
        )

    def recover(self, _route, _request):
        raise AssertionError("the success vertical must not enter provider recovery")


class _FixtureAssetPort:
    def __init__(self) -> None:
        self.adopt_calls = 0

    def adopt(self, event) -> AdoptedAssetIdentity:
        self.adopt_calls += 1
        return AdoptedAssetIdentity(
            "ASSET-P0E0000000000000000000000",
            event["output_sha256"],
        )

    def verify(self, event, asset_id: str) -> AdoptedAssetIdentity:
        return AdoptedAssetIdentity(asset_id, event["output_sha256"])


@dataclass
class _NleReadback:
    export_application: ExportQueueApplication
    timeline_sha256: str
    project_manifest_sha256: str

    def snapshot(self, args=None):
        assert args in (None, {})
        return {
            "available": True,
            "projected_timeline_sha256": self.timeline_sha256,
            "project_manifest_sha256": self.project_manifest_sha256,
            "visual_asset_placement_count": 0,
        }

    def export_snapshot(self, args=None):
        assert args in (None, {})
        path = DurableProductJobStore.path(self.export_application.project_root)
        rows = []
        if path.exists():
            for job in DurableProductJobStore.load(self.export_application.project_root).jobs:
                shell = durable_job_shell_projection(job).to_dict()
                rows.append(
                    {
                        **shell,
                        "operation_identity": job.operation_identity,
                        "state_version": job.state_version,
                        "recovery_actions": list(job.recovery_actions),
                        "individual_confirmation_required": (
                            job.state is DurableProductJobState.READY
                        ),
                    }
                )
        return {
            "available": True,
            "rows": rows,
            "blanket_execute_all_authorized": False,
            "host_output_path_persisted": False,
        }

    def visual_asset_placement_snapshot(self, args=None):
        assert args in (None, {})
        return {"available": False}


_GATE_OWNERS = {
    FinalReviewGateId.AUDIO_COMPLETION: "DEVELOPER2",
    FinalReviewGateId.EDIT_PERSISTENCE: "TASK-044",
    FinalReviewGateId.PRIVACY: "TASK-016",
    FinalReviewGateId.RESOURCE: "TASK-020",
    FinalReviewGateId.RIGHTS_LICENSE: "TASK-003/027",
}


def _external_gates(timeline_sha256: str) -> tuple[FinalReviewExternalGateReceipt, ...]:
    return tuple(
        FinalReviewExternalGateReceipt(
            gate_id=gate_id,
            source_authority_owner=owner,
            project_id=PROJECT_ID,
            timeline_sha256=timeline_sha256,
            source_receipt_id=f"fixture-{gate_id.value.casefold()}",
            source_receipt_sha256=sha256_bytes(f"fixture:{gate_id.value}".encode()),
            state=FinalReviewGateState.PASS,
            evaluated_at="2026-09-01T00:00:00.000Z",
            current_valid=True,
            invalidation_epoch=0,
        )
        for gate_id, owner in _GATE_OWNERS.items()
    )


def test_central_models_to_planning_generation_and_export_is_one_fixture_vertical(
    tmp_path: Path,
) -> None:
    manifest = ProductProjectManifest.create(
        project_id=PROJECT_ID,
        project_revision=1,
        product_version="0.22.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
    )
    ProductProjectManifestStore.save(tmp_path, manifest)

    settings_path = tmp_path / "ai-connection-settings.json"
    initial_save = ConnectionSettingsStore.save(settings_path, _local_profile())
    available_routes = frozenset({"planning-local", "image-local", "video-local"})
    settings = ConnectionSettingsWebService(
        settings_path,
        initial_save.record.profile,
        initial_save.record.revision,
        ConnectionAvailability(available_routes),
    )

    planning = Task027PlanningApplication(project_root=tmp_path, project_id=PROJECT_ID)
    planning_adapter = _FixturePlanningAdapter()
    planning_generation = Task036PlanningGenerationApplication(
        planning_application=planning,
        connection_provider=settings.current_connection,
        adapter_factory=lambda _route: planning_adapter,
        token_factory=lambda: "planning-fixture-confirmation",
    )
    production = planning.production_control
    safety = Task013GenerationSafetyApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        planning_application=planning,
        token_factory=lambda: "safety-fixture-confirmation",
    )
    continuity = Task039ContinuityApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        production_control=production,
    )
    prompt_confirmation_ids = count(1)
    prompt = Task040PromptEvidenceApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        production_control=production,
        token_factory=lambda: f"prompt-fixture-confirmation-{next(prompt_confirmation_ids)}",
    )
    queue = Task027GenerationQueueApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        production_control=production,
        planning_application=planning,
        generation_safety_application=safety,
        continuity_application=continuity,
        prompt_evidence_application=prompt,
        token_factory=lambda: "queue-fixture-confirmation",
    )
    video_port = _FixtureVideoPort(tmp_path / "fixture-generation-output")
    execution = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        generation_queue=queue,
        execution_port=video_port,
        availability_factory=lambda: settings.current_connection()[1],
        token_factory=lambda: "execution-fixture-confirmation",
    )
    asset_port = _FixtureAssetPort()
    adoption = Task027GenerationOutputAdoptionApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        generation_execution=execution,
        generation_queue=queue,
        production_control=production,
        prompt_evidence=prompt,
        asset_port=asset_port,
        token_factory=lambda: "adoption-fixture-confirmation",
    )
    audit = Task038AuditApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        token_factory=lambda: "audit-fixture-confirmation",
    )
    final_review = FinalReviewApprovalApplication(
        project_root=tmp_path,
        project_id=PROJECT_ID,
        token_factory=lambda: "final-review-fixture-confirmation",
    )
    export_queue = ExportQueueApplication(project_root=tmp_path, project_id=PROJECT_ID)
    timeline_sha256 = sha256_bytes(
        canonical_json_bytes({"project_id": PROJECT_ID, "timeline": "p0e-fixture-v1"})
    )
    nle = _NleReadback(export_queue, timeline_sha256, manifest.project_manifest_sha256)

    def export_preparation(receipt) -> ExportPreparation:
        return ExportPreparation(
            project_id=PROJECT_ID,
            project_manifest_sha256=manifest.project_manifest_sha256,
            product_version=manifest.product_version,
            timeline_plan_id="timeline-p0e-fixture",
            timeline_revision=1,
            timeline_sha256=timeline_sha256,
            edit_plan_sha256=sha256_bytes(b"fixture-edit-plan"),
            assembly_plan_sha256=sha256_bytes(b"fixture-assembly-plan"),
            final_approval=receipt,
            preset=ExportPreset(
                "preset-fixture-1080p",
                "1.0.0",
                ExportOutputContract(1920, 1080, 30, 1, 48000, 2, "mp4", "h264", "pcm"),
            ),
            output_target_identity="export:p0e-fixture-master",
            authority_class=ExportAuthorityClass.LOCAL_PACKAGE,
        )

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        production_control=production,
        audit_application=audit,
        planning_application=planning,
        planning_generation_application=planning_generation,
        generation_safety_application=safety,
        continuity_application=continuity,
        prompt_evidence_application=prompt,
        generation_queue_application=queue,
        generation_execution_application=execution,
        generation_output_adoption_application=adoption,
        connection_settings=settings,
        final_review_application=final_review,
        final_review_external_gate_provider=lambda: _external_gates(timeline_sha256),
        final_review_export_preparation_provider=export_preparation,
        nle_controller=nle,
    )

    connection = bridge.connection_settings_snapshot({})
    modes = {row["workload"]: "OFFLINE_ONLY" for row in connection["workloads"]}
    preferred = {row["workload"]: None for row in connection["workloads"]}
    preferred.update(
        {"PLANNING": "planning-local", "IMAGE": "image-local", "VIDEO": "video-local"}
    )
    saved = bridge.connection_settings_update(
        {
            "revision": connection["revision"],
            "workload_modes": modes,
            "preferred_route_ids": preferred,
        }
    )
    assert saved["provider_execution_started"] is False
    assert saved["paid_execution_authorized"] is False
    model_inventory = bridge.model_selection_snapshot({})
    planning_model = next(
        row for row in model_inventory["selectors"] if row["workload"] == "PLANNING"
    )
    video_model = next(
        row for row in model_inventory["selectors"] if row["workload"] == "VIDEO"
    )
    audio_model = next(
        row for row in model_inventory["selectors"] if row["workload"] == "AUDIO"
    )
    assert planning_model["preferred_route_id"] == "planning-local"
    assert video_model["preferred_route_id"] == "video-local"
    assert planning_model["candidates"][0]["configuration_selectable"] is True
    assert video_model["candidates"][0]["configuration_selectable"] is True
    assert audio_model["available"] is False
    assert audio_model["unavailable_reason"] == "NO_SELECTABLE_LOCAL_AUDIO_MODEL"

    reopened_settings = ConnectionSettingsWebService.from_paths(settings_path, None)
    reopened = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        connection_settings=reopened_settings,
    ).connection_settings_snapshot({})
    reopened_preferred = {
        row["workload"]: row["preferred_route_id"] for row in reopened["workloads"]
    }
    assert reopened_preferred["PLANNING"] == "planning-local"
    assert reopened_preferred["VIDEO"] == "video-local"

    planning_state = bridge.planning_snapshot({})
    prepared_plan = bridge.planning_generation_prepare(
        {
            "vague_request": "無料ローカルAIで2秒の紹介動画を作る",
            "expected_planning_snapshot_sha256": planning_state["snapshot_sha256"],
        }
    )
    assert planning_adapter.ready_calls == 1
    assert planning_adapter.generate_calls == 0
    generated = bridge.planning_generation_apply(
        {"confirmation_id": prepared_plan["confirmation_id"]}
    )
    assert planning_adapter.generate_calls == 1
    assert generated["paid_execution_authorized"] is False
    with pytest.raises(ProductError) as planning_replay:
        bridge.planning_generation_apply({"confirmation_id": prepared_plan["confirmation_id"]})
    assert planning_replay.value.code == "ERR_TASK036_PLANNING_CONFIRMATION_INVALID"

    proposal_id = generated["proposal_id"]
    planning_state = bridge.planning_snapshot({"proposal_id": proposal_id})
    prepared_go = bridge.planning_prepare_go(
        {
            "proposal_id": proposal_id,
            "proposal_revision": 1,
            "reference_bindings": [],
            "cost_ceiling": "0",
            "rights_warnings_acknowledged": False,
            "expected_snapshot_sha256": planning_state["snapshot_sha256"],
        }
    )
    approved = bridge.planning_approve_go(
        {"confirmation_id": prepared_go["confirmation_id"], "approved_by": "fixture-owner"}
    )
    planning_state = bridge.planning_snapshot({"proposal_id": proposal_id})
    prepared_install = bridge.planning_prepare_install_plan(
        {
            "plan_id": approved["approved_plan"]["plan_id"],
            "expected_proposal_snapshot_sha256": planning_state["snapshot_sha256"],
            "expected_production_snapshot_sha256": planning_state["installation"]["production"]["snapshot_sha256"],
        }
    )
    bridge.planning_apply_install_plan(
        {"confirmation_id": prepared_install["confirmation_id"]}
    )
    production_state = bridge.production_snapshot({})
    assert [(row["scene_id"], row["slot_kind"]) for row in production_state["slots"]] == [
        ("SC01", "VIDEO")
    ]
    slot_id = production_state["slots"][0]["slot_id"]

    safety_state = bridge.generation_safety_snapshot({})
    checks = {
        name: "PASS"
        for name in (
            "subject_position_exists",
            "orientation_camera_compatible",
            "required_visible_coexists",
            "prohibited_change_not_required",
            "shot_reference_matches_final_camera",
            "task_axis_valid",
            "depth_order_valid",
            "occlusion_valid",
            "furniture_integrity_valid",
            "room_anchor_integrity_valid",
            "production_gear_absent",
            "character_identity_valid",
        )
    }
    prepared_safety = bridge.generation_safety_prepare_review(
        {
            "spec": {
                "scene_id": "SC01",
                "continuity_type": "CUT",
                "character_required": True,
                "character_identity_profile_id": "CHAR-FIXTURE",
                "character_reference_asset_ids": ["ASSET-CHAR-FIXTURE"],
                "room_master_asset_id": "ASSET-ROOM-FIXTURE",
                "room_shot_reference_asset_id": "ASSET-SHOT-FIXTURE",
                "style_reference_asset_id": None,
                "required_visible": ["FACE"],
                "subject_orientation": "THREE_QUARTER",
                "camera_semantic": "DESK_FRONT",
                "start_frame_source": "NEW",
                "previous_end_asset_id": None,
                "previous_end_sha256": None,
                "start_asset_id": None,
                "start_asset_sha256": None,
                "prohibited_changes": ["MOVE_FURNITURE"],
            },
            "human_reviewed_checks": checks,
            "blocking_reasons": [],
            "expected_planning_snapshot_sha256": safety_state["planning_snapshot_sha256"],
            "expected_safety_snapshot_sha256": safety_state["safety_snapshot_sha256"],
        }
    )
    bridge.generation_safety_apply_review(
        {
            "confirmation_id": prepared_safety["confirmation_id"],
            "reviewed_by": "fixture-owner",
        }
    )

    prompt_body = b"one safe local fixture video scene"
    prompt_sha256 = sha256_bytes(prompt_body)
    prompt_path = tmp_path / "private" / "prompts" / "p0e-video" / "v1"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_bytes(prompt_body)
    prompt_state = bridge.prompt_evidence_snapshot({})
    prepared_prompt = bridge.prompt_evidence_prepare_prompt(
        {
            "prompt_id": "p0e-video",
            "prompt_version": 1,
            "purpose": "fixture video",
            "scene_id": "SC01",
            "slot_id": slot_id,
            "body_ref": "project-private://prompts/p0e-video/v1",
            "body_sha256": prompt_sha256,
            "provider_profile_id": "profile-p0e-local",
            "provider_profile_version": "1.0.0",
            "input_asset_hashes": [],
            "keep_conditions": ["keep composition"],
            "expected_prompt_snapshot_sha256": prompt_state["prompt_snapshot_sha256"],
            "expected_production_snapshot_sha256": prompt_state["production_snapshot_sha256"],
        }
    )
    bridge.prompt_evidence_apply_prompt(
        {"confirmation_id": prepared_prompt["confirmation_id"]}
    )

    queue_state = bridge.generation_queue_snapshot({})
    prepared_queue = bridge.generation_queue_prepare(
        {
            "prompt_id": "p0e-video",
            "prompt_version": 1,
            "expected_queue_snapshot_sha256": queue_state["queue_snapshot_sha256"],
            "expected_upstream_snapshots": queue_state["upstream_snapshots"],
        }
    )
    bridge.generation_queue_apply({"confirmation_id": prepared_queue["confirmation_id"]})
    queue_state = bridge.generation_queue_snapshot({})
    queue_entry_id = queue_state["entries"][0]["queue_entry_id"]

    runtime = bridge.generation_execution_preflight({"queue_entry_id": queue_entry_id})
    assert runtime["dispatch_performed"] is False
    prepared_execution = bridge.generation_execution_prepare(
        {
            "queue_entry_id": queue_entry_id,
            "expected_queue_snapshot_sha256": queue_state["queue_snapshot_sha256"],
            "expected_execution_snapshot_sha256": queue_state["execution_control"]["execution_snapshot_sha256"],
        }
    )
    completed = bridge.generation_execution_apply(
        {"confirmation_id": prepared_execution["confirmation_id"]}
    )["latest_executions"][0]
    assert completed["state"] == "COMPLETED"
    assert video_port.preflight_calls >= 2
    assert video_port.execute_calls == 1
    output_path = (
        tmp_path
        / "fixture-generation-output"
        / completed["execution_id"]
        / "fixture-video.json"
    )
    assert output_path.is_file()
    assert sha256_bytes(output_path.read_bytes()) == completed["output_sha256"]
    with pytest.raises(ProductError) as execution_replay:
        bridge.generation_execution_apply(
            {"confirmation_id": prepared_execution["confirmation_id"]}
        )
    assert execution_replay.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION"
    assert video_port.execute_calls == 1

    queue_state = bridge.generation_queue_snapshot({})
    production_state = bridge.production_snapshot({})
    prompt_state = bridge.prompt_evidence_snapshot({})
    prepared_adoption = bridge.generation_output_adoption_prepare(
        {
            "execution_id": completed["execution_id"],
            "expected_execution_snapshot_sha256": queue_state["execution_control"]["execution_snapshot_sha256"],
            "expected_queue_snapshot_sha256": queue_state["queue_snapshot_sha256"],
            "expected_production_snapshot_sha256": production_state["snapshot_sha256"],
            "expected_prompt_snapshot_sha256": prompt_state["prompt_snapshot_sha256"],
            "expected_adoption_snapshot_sha256": queue_state["output_adoption_control"]["adoption_snapshot_sha256"],
        }
    )
    adopted = bridge.generation_output_adoption_apply(
        {"confirmation_id": prepared_adoption["confirmation_id"]}
    )
    assert adopted["records"][-1]["state"] == "READY_FOR_AUDIT"
    assert asset_port.adopt_calls == 1

    production_state = bridge.production_snapshot({})
    candidate = production_state["slots"][0]["candidates"][0]
    audit_state = bridge.audit_snapshot({})
    audit.record_audit(
        record=AuditRecord(
            "audit-p0e-fixture",
            candidate["candidate_id"],
            candidate["asset_sha256"],
            ("P0E_FIXTURE_CONTRACT",),
            AuditorKind.AI,
            "fixture-auditor",
            "1.0.0",
            {"CONTRACT": 100.0},
            (),
            (),
            (),
        ),
        expected_production_snapshot_sha256=audit_state["production_snapshot_sha256"],
        expected_audit_snapshot_sha256=audit_state["audit_snapshot_sha256"],
    )
    audit_state = bridge.audit_snapshot({})
    prepared_decision = bridge.audit_prepare_human_decision(
        {
            "candidate_id": candidate["candidate_id"],
            "decision": "ACCEPT",
            "expected_production_snapshot_sha256": audit_state["production_snapshot_sha256"],
            "expected_audit_snapshot_sha256": audit_state["audit_snapshot_sha256"],
        }
    )
    bridge.audit_apply_human_decision(
        {
            "confirmation_id": prepared_decision["confirmation_id"],
            "actor_id": "fixture-owner",
            "notes": "fixture output reviewed",
        }
    )
    production_state = bridge.production_snapshot({})
    prepared_lock = bridge.production_prepare_lock(
        {
            "slot_id": slot_id,
            "candidate_id": candidate["candidate_id"],
            "expected_snapshot_sha256": production_state["snapshot_sha256"],
        }
    )
    bridge.production_apply_lock({"confirmation_id": prepared_lock["confirmation_id"]})
    visual = bridge.visual_generation_handoff_snapshot({})
    assert visual["all_required_visual_slots_adopted"] is True
    assert visual["required_blocker_count"] == 0

    review = bridge.final_review_snapshot({})
    assert review["readiness"]["state"] == "READY_FOR_TYPED_FINAL_REVIEW"
    prepared_review = bridge.final_review_prepare(
        {
            "expected_readiness_projection_sha256": review["readiness"]["projection_sha256"],
            "expected_approval_snapshot_sha256": review["approval"]["snapshot_sha256"],
        }
    )
    bridge.final_review_apply(
        {
            "confirmation_id": prepared_review["confirmation_id"],
            "approved_by": "fixture-owner",
        }
    )
    export_state = bridge.final_review_export_snapshot({})
    prepared_export = bridge.final_review_export_prepare(
        {
            "expected_readiness_projection_sha256": export_state["readiness_projection_sha256"],
            "expected_approval_snapshot_sha256": export_state["approval_snapshot_sha256"],
            "expected_preparation_sha256": export_state["preparation_sha256"],
        }
    )
    queued_export = bridge.final_review_export_apply(
        {"confirmation_id": prepared_export["confirmation_id"]}
    )
    assert queued_export["state"] == "QUEUED"
    assert queued_export["export_job_created"] is True
    assert queued_export["side_effect_started_by_this_call"] is False
    assert queued_export["host_output_path_persisted"] is False
    export_readback = bridge.export_queue_snapshot({})
    assert len(export_readback["rows"]) == 1
    assert export_readback["rows"][0]["job_id"] == queued_export["job_id"]
    assert export_readback["rows"][0]["state"] == "QUEUED"
    with pytest.raises(ProductError) as export_replay:
        bridge.final_review_export_apply(
            {"confirmation_id": prepared_export["confirmation_id"]}
        )
    assert export_replay.value.code == "ERR_FINAL_REVIEW_EXPORT_CONFIRMATION_INVALID"
    jobs = DurableProductJobStore.load(tmp_path).jobs
    assert len(jobs) == 1
    assert jobs[0].job_id == queued_export["job_id"]
    assert jobs[0].target_identity == "export:p0e-fixture-master"
