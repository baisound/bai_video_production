from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
from threading import Lock
import shutil

import pytest

from ai_video_production.ai_connections import AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass, ModelRoute, ProviderFamily, SelectionMode
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.approved_creative_generation import ApprovedCreativeGenerationPlanner
from ai_video_production.approved_plan_orchestration import ApprovedPlanProductionControlInstaller
from ai_video_production.creative_generation import CreativeGenerationMode, CreativeGenerationRequest
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.connection_settings_web import ConnectionSettingsWebService
from ai_video_production.local_ollama_planning import parse_local_planning_candidate
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.production_proposal import ProductionProposalRevision, ProposalSection, ProviderPolicyBinding
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.production_control import ProductionControlRegistry
from ai_video_production.prompt_registry import PromptEntity
from ai_video_production.shot_feasibility import CheckState, ShotFeasibilityAssessment
from ai_video_production.task036_planning_generation_application import Task036PlanningGenerationApplication
from ai_video_production.task036_shell_ui import Task036ShellBridge


def candidate(title: str = "Local plan"):
    return parse_local_planning_candidate({
        "intent": {
            "purpose": "Product intro", "audience": "Creators", "platform": "YouTube",
            "aspect_ratio": "16:9", "target_duration_seconds": 2, "style_tone": "Clear",
            "story_message": "Explain the workflow", "language": "ja-JP", "free_text": "",
            "rights_constraints": [],
        },
        "proposal_title": title, "timeline_fps": 30,
        "sections": [{"section_id": "concept", "kind": "CONCEPT", "title": "Concept", "body": "A clear introduction"}],
        "scenes": [
            {"scene_id": "SC01", "start_frame": 0, "end_frame": 30, "narrative_role": "Opening", "source_strategy": "AI_GENERATED", "generation_risk": "A_LOW_TEXT", "camera_motion": "SUBTLE", "audio": {"narration": True, "dialogue": False, "sound_effects": [], "bgm": True, "sound_logo": False}, "locked_reference": False, "post_composite_text": False, "final_hold_frames": 0},
            {"scene_id": "SC02", "start_frame": 30, "end_frame": 60, "narrative_role": "Close", "source_strategy": "COMPOSITE", "generation_risk": "B_HEADLINE", "camera_motion": "STATIC", "audio": {"narration": True, "dialogue": False, "sound_effects": [], "bgm": True, "sound_logo": False}, "locked_reference": False, "post_composite_text": True, "final_hold_frames": 3},
        ],
        "rights_warnings": [],
    })


def route(model: str = "qwen3:8b") -> ModelRoute:
    return ModelRoute(
        "planning-local", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE,
        "ollama", model, CostClass.LOCAL_FREE_AI, priority=0,
        capabilities=("TEXT_GENERATION",),
    )


def connection(model: str = "qwen3:8b"):
    selected = route(model)
    video = ModelRoute(
        "video-local", AiWorkload.VIDEO, ProviderFamily.COMFYUI, "comfyui",
        "local-video", CostClass.LOCAL_FREE_AI, priority=0,
        capabilities=("IMAGE_TO_VIDEO",),
    )
    return AiConnectionProfile(
        "creator-local", "1.0.0", SelectionMode.OFFLINE_ONLY, (selected, video),
    ), ConnectionAvailability(frozenset({selected.route_id, video.route_id}))


class Adapter:
    def __init__(self, result=None, failure: BaseException | None = None):
        self.result, self.failure = result or candidate(), failure
        self.ready_calls = 0
        self.generate_calls = 0
        self.prompts: list[str] = []
        self._lock = Lock()

    def ready(self):
        with self._lock:
            self.ready_calls += 1
        return True

    def generate(self, prompt):
        with self._lock:
            self.generate_calls += 1
            self.prompts.append(prompt)
        if self.failure:
            raise self.failure
        return self.result


def application(root: Path, adapter: Adapter, *, token: str = "confirm", connection_provider=None, project_id: str = "project-1"):
    if not ProductProjectManifestStore.path(root).exists():
        ProductProjectManifestStore.save(
            root,
            ProductProjectManifest.create(
                project_id=project_id, project_revision=1, product_version="0.22.0",
                timebase=ProjectTimebase(30, 1), child_bindings=(),
            ),
        )
    planning = Task027PlanningApplication(project_root=root, project_id=project_id)
    return Task036PlanningGenerationApplication(
        planning_application=planning,
        connection_provider=connection_provider or connection,
        adapter_factory=lambda _route: adapter,
        token_factory=lambda: token,
    )


def test_prepare_apply_persists_typed_zero_cost_proposal_after_one_local_call(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    empty = app.planning.snapshot()
    prepared = app.prepare(vague_request="2秒の紹介動画", expected_planning_snapshot_sha256=empty["snapshot_sha256"])
    assert prepared["cost_class"] == "LOCAL_FREE_AI"
    assert prepared["request_text_exposed"] is False and prepared["host_paths_exposed"] is False
    assert prepared["provider_execution_started"] is False and adapter.ready_calls == 1
    result = app.apply(confirmation_id=prepared["confirmation_id"])
    assert result["provider_execution_started"] is True and result["paid_execution_authorized"] is False
    assert adapter.generate_calls == 1 and "2秒の紹介動画" in adapter.prompts[0]
    workspace = result["application"]["workspace"]
    assert workspace["estimated_cost_range"] == {"min": "0", "max": "0", "currency": "JPY"}
    assert workspace["go_status"] == "GO_REQUIRED"
    assert workspace["creation_intent"]["intent_id"].startswith("INTENT-AI-")
    assert [item["scene_id"] for item in workspace["blueprint"]["scenes"]] == ["SC01", "SC02"]
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_CONFIRMATION_INVALID"


def test_restart_same_request_is_idempotent_without_readiness_or_generation(tmp_path: Path):
    first_adapter = Adapter()
    first = application(tmp_path, first_adapter, token="first")
    prepared = first.prepare(vague_request="same request", expected_planning_snapshot_sha256=first.planning.snapshot()["snapshot_sha256"])
    created = first.apply(confirmation_id=prepared["confirmation_id"])
    second_adapter = Adapter()
    second = application(tmp_path, second_adapter, token="second")
    prepared_again = second.prepare(vague_request="same request", expected_planning_snapshot_sha256=second.planning.snapshot()["snapshot_sha256"])
    assert prepared_again["already_generated"] is True and second_adapter.ready_calls == 0
    again = second.apply(confirmation_id=prepared_again["confirmation_id"])
    assert again["idempotent"] is True and again["proposal_id"] == created["proposal_id"]
    assert second_adapter.generate_calls == 0


def test_two_applications_concurrently_publish_exact_one_and_generate_once(tmp_path: Path):
    adapter = Adapter()
    first = application(tmp_path, adapter, token="first")
    second = application(tmp_path, adapter, token="second")
    snapshot = first.planning.snapshot()["snapshot_sha256"]
    one = first.prepare(vague_request="parallel request", expected_planning_snapshot_sha256=snapshot)
    two = second.prepare(vague_request="parallel request", expected_planning_snapshot_sha256=snapshot)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: item[0].apply(confirmation_id=item[1]), ((first, one["confirmation_id"]), (second, two["confirmation_id"]))))
    assert sorted(item["idempotent"] for item in results) == [False, True]
    assert adapter.generate_calls == 1
    reopened = Task027PlanningApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert len(reopened["proposal_ids"]) == 1


def test_connection_drift_consumes_confirmation_without_provider_or_store(tmp_path: Path):
    state = {"model": "qwen3:8b"}
    adapter = Adapter()
    app = application(tmp_path, adapter, connection_provider=lambda: connection(state["model"]))
    prepared = app.prepare(vague_request="drift", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    state["model"] = "qwen3:14b"
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_CONNECTION_STALE"
    assert adapter.generate_calls == 0 and not (tmp_path / "production-proposal.json").exists()
    with pytest.raises(ProductError):
        app.apply(confirmation_id=prepared["confirmation_id"])


def test_removed_canonical_connection_after_prepare_blocks_provider_and_publication(tmp_path: Path):
    raw = tmp_path / "initial-profile.json"
    current_profile, _ = connection()
    raw.write_text(json.dumps(current_profile.to_dict()), encoding="utf-8")
    settings = tmp_path / "ai-connection-settings.json"
    ConnectionSettingsStore.save(settings, current_profile)
    service = ConnectionSettingsWebService.from_paths(settings, raw)
    adapter = Adapter()
    app = application(tmp_path, adapter, connection_provider=service.current_connection)
    prepared = app.prepare(
        vague_request="revoked settings",
        expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"],
    )
    settings.unlink()
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_CONNECTION_SETTINGS_INTEGRITY"
    assert adapter.generate_calls == 0
    assert not (tmp_path / "production-proposal.json").exists()


def test_provider_failure_leaves_canonical_store_absent(tmp_path: Path):
    failure = ProductError("ERR_FAKE_OLLAMA", "failed", ProductErrorCategory.EXTERNAL_DEPENDENCY)
    adapter = Adapter(failure=failure)
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="failure", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_FAKE_OLLAMA"
    assert adapter.generate_calls == 1 and not (tmp_path / "production-proposal.json").exists()


def test_unrelated_proposal_change_makes_confirmation_stale_before_provider(tmp_path: Path):
    adapter = Adapter()
    first = application(tmp_path, adapter, token="pending")
    prepared = first.prepare(vague_request="will be stale", expected_planning_snapshot_sha256=first.planning.snapshot()["snapshot_sha256"])
    other = application(tmp_path, Adapter(candidate("Other")), token="other")
    other_prepared = other.prepare(vague_request="other request", expected_planning_snapshot_sha256=other.planning.snapshot()["snapshot_sha256"])
    other.apply(confirmation_id=other_prepared["confirmation_id"])
    with pytest.raises(ProductError) as exc:
        first.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_SNAPSHOT_STALE"
    assert adapter.generate_calls == 0


def test_prepare_rejects_paid_or_non_ollama_routes_without_adapter_call(tmp_path: Path):
    paid = ModelRoute("paid", AiWorkload.PLANNING, ProviderFamily.OPENAI, "openai", "gpt", CostClass.CLOUD_PAID_AI, capabilities=("TEXT_GENERATION",))
    profile = AiConnectionProfile("paid-only", "1", SelectionMode.AI, (paid,))
    adapter = Adapter()
    app = application(tmp_path, adapter, connection_provider=lambda: (profile, ConnectionAvailability(frozenset({"paid"}))))
    with pytest.raises(ProductError) as exc:
        app.prepare(vague_request="never paid", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    assert exc.value.code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"
    assert adapter.ready_calls == adapter.generate_calls == 0


def test_cancel_is_single_use_and_never_calls_provider(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="cancel me", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    result = app.cancel(confirmation_id=prepared["confirmation_id"])
    assert result["cancelled"] is True and result["provider_execution_started"] is False
    assert adapter.generate_calls == 0 and not (tmp_path / "production-proposal.json").exists()
    with pytest.raises(ProductError) as exc:
        app.cancel(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_CONFIRMATION_INVALID"


def test_cross_project_application_is_rejected_by_canonical_manifest(tmp_path: Path):
    application(tmp_path, Adapter())
    wrong = Task027PlanningApplication(project_root=tmp_path, project_id="other-project")
    with pytest.raises(ProductError) as exc:
        Task036PlanningGenerationApplication(
            planning_application=wrong, connection_provider=connection,
            adapter_factory=lambda _route: Adapter(),
        )
    assert exc.value.code == "ERR_TASK036_PLANNING_PROJECT_SCOPE_MISMATCH"


def test_checksum_valid_foreign_proposal_store_swap_fails_before_readiness(tmp_path: Path):
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    root_a.mkdir()
    root_b.mkdir()
    source = application(root_a, Adapter(), project_id="project-a")
    prepared = source.prepare(
        vague_request="same request",
        expected_planning_snapshot_sha256=source.planning.snapshot()["snapshot_sha256"],
    )
    source.apply(confirmation_id=prepared["confirmation_id"])
    target_adapter = Adapter()
    target = application(root_b, target_adapter, project_id="project-b")
    expected_empty = target.planning.snapshot()["snapshot_sha256"]
    shutil.copyfile(
        root_a / "production-proposal.json",
        root_b / "production-proposal.json",
    )
    with pytest.raises(ProductError) as exc:
        target.prepare(
            vague_request="same request",
            expected_planning_snapshot_sha256=expected_empty,
        )
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_PROJECT_SCOPE_MISMATCH"
    assert target_adapter.ready_calls == target_adapter.generate_calls == 0


def test_foreign_record_rewrapped_for_target_project_is_not_idempotent(tmp_path: Path):
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    root_a.mkdir()
    root_b.mkdir()
    source = application(root_a, Adapter(), project_id="project-a")
    prepared = source.prepare(
        vague_request="same request",
        expected_planning_snapshot_sha256=source.planning.snapshot()["snapshot_sha256"],
    )
    source.apply(confirmation_id=prepared["confirmation_id"])
    foreign_registry = ProductionProposalSnapshotStore.load(
        root_a / "production-proposal.json",
        expected_project_id="project-a",
    )
    target_adapter = Adapter()
    target = application(root_b, target_adapter, project_id="project-b")
    ProductionProposalSnapshotStore.save(
        root_b / "production-proposal.json",
        foreign_registry,
        project_id="project-b",
    )
    with pytest.raises(ProductError) as exc:
        target.prepare(
            vague_request="same request",
            expected_planning_snapshot_sha256=target.planning.snapshot()["snapshot_sha256"],
        )
    assert exc.value.code == "ERR_TASK036_PLANNING_REQUEST_ID_CONFLICT"
    assert target_adapter.ready_calls == target_adapter.generate_calls == 0


def test_manifest_revision_drift_blocks_before_provider(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="manifest drift", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    current = ProductProjectManifestStore.load(tmp_path)
    changed = ProductProjectManifest.create(
        project_id=current.project_id, project_revision=2, product_version=current.product_version,
        timebase=current.timebase, child_bindings=current.child_bindings,
        created_at=current.created_at,
    )
    ProductProjectManifestStore.save(tmp_path, changed, expected_previous_manifest_sha256=current.project_manifest_sha256)
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_PROJECT_STALE"
    assert adapter.generate_calls == 0 and not (tmp_path / "production-proposal.json").exists()


def test_existing_id_policy_with_wrong_request_binding_is_conflict_not_idempotent(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    _, request_sha = app._request("same request")
    profile, _, selected_route, _, policy = app._connection()
    manifest_sha = ProductProjectManifestStore.load(tmp_path).project_manifest_sha256
    provenance = app._provenance(
        profile, selected_route, request_sha,
        project_id=app.project_id,
        project_manifest_sha256=manifest_sha,
    )
    intent, proposal = app._records(candidate(), request_sha256=request_sha, policy=policy, provenance_body=provenance)
    altered_sections = tuple(
        ProposalSection(item.section_id, item.kind, item.title, "sha256:" + "0" * 64)
        if item.section_id == "task036_request_binding" else item
        for item in proposal.sections
    )
    altered = ProductionProposalRevision(
        proposal.proposal_id, proposal.revision, proposal.intent_sha256, proposal.blueprint,
        altered_sections, proposal.provider_policy, proposal.estimated_cost_min,
        proposal.estimated_cost_max, proposal.currency, proposal.rights_warnings,
    )
    empty = app.planning.snapshot()
    app.planning.append_initial_proposal(
        intent=intent, proposal=altered,
        expected_snapshot_sha256=empty["snapshot_sha256"],
        expected_project_manifest_sha256=ProductProjectManifestStore.load(tmp_path).project_manifest_sha256,
    )
    reopened = application(tmp_path, Adapter(), token="reopened")
    with pytest.raises(ProductError) as exc:
        reopened.prepare(vague_request="same request", expected_planning_snapshot_sha256=reopened.planning.snapshot()["snapshot_sha256"])
    assert exc.value.code == "ERR_TASK036_PLANNING_REQUEST_ID_CONFLICT"


def test_task027_initial_append_rejects_orphan_intent_pair(tmp_path: Path):
    app = application(tmp_path, Adapter())
    _, request_sha = app._request("pair")
    profile, _, selected_route, _, policy = app._connection()
    manifest_sha = ProductProjectManifestStore.load(tmp_path).project_manifest_sha256
    provenance = app._provenance(
        profile, selected_route, request_sha,
        project_id=app.project_id,
        project_manifest_sha256=manifest_sha,
    )
    intent, proposal = app._records(candidate(), request_sha256=request_sha, policy=policy, provenance_body=provenance)
    other_intent = replace(intent, intent_id="INTENT-AI-" + "F" * 32)
    with pytest.raises(ProductError) as exc:
        app.planning.append_initial_proposal(
            intent=other_intent, proposal=proposal,
            expected_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"],
            expected_project_manifest_sha256=ProductProjectManifestStore.load(tmp_path).project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PLANNING_APPLICATION_INITIAL_PROPOSAL_INTENT_MISMATCH"
    assert not (tmp_path / "production-proposal.json").exists()


def test_concurrent_duplicate_confirmation_token_admission_is_exact(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter, token="same-token")
    snapshot = app.planning.snapshot()["snapshot_sha256"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(app.prepare, vague_request=f"request {index}", expected_planning_snapshot_sha256=snapshot) for index in range(2)]
    successes, errors = [], []
    for future in futures:
        try:
            successes.append(future.result())
        except ProductError as exc:
            errors.append(exc.code)
    assert len(successes) == 1 and errors == ["ERR_TASK036_PLANNING_CONFIRMATION_INVALID"]


def test_operation_lock_symlink_rejects_before_provider(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="lock attack", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    target = tmp_path / "lock-target"
    target.write_text("sentinel", encoding="utf-8")
    (tmp_path / ".task036-planning-generation.json.lock").symlink_to(target)
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_PRODUCTION_SNAPSHOT_LOCK_INVALID"
    assert adapter.generate_calls == 0 and target.read_text(encoding="utf-8") == "sentinel"


def test_generated_proposal_go_compiles_existing_approved_generation_with_exact_profile(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="vertical policy", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    created = app.apply(confirmation_id=prepared["confirmation_id"])
    state = created["application"]
    profile, availability = connection()
    assert state["workspace"]["provider_policy"] == {
        "policy_id": profile.profile_id,
        "policy_version": profile.profile_version,
        "policy_sha256": profile.to_dict()["profile_sha256"],
    }
    go = app.planning.prepare_go(
        proposal_id=created["proposal_id"], proposal_revision=1, reference_bindings=(),
        cost_ceiling="0", rights_warnings_acknowledged=False,
        expected_snapshot_sha256=state["snapshot_sha256"],
    )
    approved = app.planning.approve_go(confirmation_id=go["confirmation_id"], approved_by="owner")
    registry = ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json")
    proposal = registry.latest_proposal(created["proposal_id"])
    production = ProductionControlRegistry()
    plan_id = approved["approved_plan"]["plan_id"]
    ApprovedPlanProductionControlInstaller.install(
        proposal_registry=registry, plan_id=plan_id, blueprint=proposal.blueprint,
        project_id="project-1", production_registry=production,
    )
    prompt = PromptEntity(
        "prompt-1", 1, "scene", "sha256:" + "a" * 64,
        profile.profile_id, profile.profile_version, ("keep",),
        scene_id="SC01", slot_id="slot:SC01:VIDEO",
    )
    request = CreativeGenerationRequest(
        "request-1", "SC01", "slot:SC01:VIDEO", CreativeGenerationMode.IMAGE_TO_VIDEO,
        prompt, "rights://project-1/sc01", explicit_paid_execution_authorization=False,
    )
    checks = {
        name: CheckState.PASS for name in (
            "subject_position_exists", "orientation_camera_compatible", "required_visible_coexists",
            "prohibited_change_not_required", "shot_reference_matches_final_camera", "reference_roles_valid",
            "continuity_contract_valid", "task_axis_valid", "depth_order_valid", "occlusion_valid",
            "furniture_integrity_valid", "room_anchor_integrity_valid", "production_gear_absent",
            "character_identity_valid",
        )
    }
    compiled = ApprovedCreativeGenerationPlanner.compile(
        request, profile=profile, availability=availability,
        proposal_registry=registry, approved_plan_id=plan_id, blueprint=proposal.blueprint,
        feasibility=ShotFeasibilityAssessment("SC01", checks, "TEST"),
        production_registry=production,
    )
    assert compiled.ready_for_provider_execution is True and compiled.paid_execution_required is False


def test_full_request_sha_identity_does_not_collide_on_shared_hex_prefix():
    first = "sha256:" + "a" * 32 + "b" * 32
    second = "sha256:" + "a" * 32 + "c" * 32
    first_ids = Task036PlanningGenerationApplication._ids(first)
    second_ids = Task036PlanningGenerationApplication._ids(second)
    assert first_ids != second_ids
    assert all(len(value) <= 64 for value in first_ids + second_ids)


def test_confirmation_capacity_is_exact_and_cancel_releases_one_slot(tmp_path: Path):
    adapter = Adapter()
    counter = iter(f"token-{index}" for index in range(257))
    app = Task036PlanningGenerationApplication(
        planning_application=application(tmp_path, adapter).planning,
        connection_provider=connection, adapter_factory=lambda _route: adapter,
        token_factory=lambda: next(counter),
    )
    snapshot = app.planning.snapshot()["snapshot_sha256"]
    confirmations = [app.prepare(vague_request=f"request {index}", expected_planning_snapshot_sha256=snapshot) for index in range(256)]
    with pytest.raises(ProductError) as exc:
        app.prepare(vague_request="over capacity", expected_planning_snapshot_sha256=snapshot)
    assert exc.value.code == "ERR_TASK036_PLANNING_CONFIRMATION_CAPACITY"
    app.cancel(confirmation_id=confirmations[0]["confirmation_id"])
    app._token_factory = lambda: "replacement"
    assert app.prepare(vague_request="replacement", expected_planning_snapshot_sha256=snapshot)["confirmation_id"] == "replacement"


def test_parallel_same_confirmation_apply_admits_exactly_one(tmp_path: Path):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="one token", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(app.apply, confirmation_id=prepared["confirmation_id"]) for _ in range(2)]
    results, errors = [], []
    for future in futures:
        try:
            results.append(future.result())
        except ProductError as exc:
            errors.append(exc.code)
    assert len(results) == 1 and errors == ["ERR_TASK036_PLANNING_CONFIRMATION_INVALID"]
    assert adapter.generate_calls == 1


def test_connection_drift_during_provider_drops_output_before_store(tmp_path: Path):
    state = {"model": "qwen3:8b"}

    class DriftingAdapter(Adapter):
        def generate(self, prompt):
            value = super().generate(prompt)
            state["model"] = "qwen3:14b"
            return value

    adapter = DriftingAdapter()
    app = application(tmp_path, adapter, connection_provider=lambda: connection(state["model"]))
    prepared = app.prepare(vague_request="mid-flight drift", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_CONNECTION_STALE"
    assert adapter.generate_calls == 1 and not (tmp_path / "production-proposal.json").exists()


def test_project_manifest_drift_during_provider_drops_output_before_store(tmp_path: Path):
    class DriftingManifestAdapter(Adapter):
        def generate(self, prompt):
            value = super().generate(prompt)
            current = ProductProjectManifestStore.load(tmp_path)
            changed = ProductProjectManifest.create(
                project_id=current.project_id,
                project_revision=current.project_revision + 1,
                product_version=current.product_version,
                timebase=current.timebase,
                child_bindings=current.child_bindings,
                created_at=current.created_at,
            )
            ProductProjectManifestStore.save(
                tmp_path,
                changed,
                expected_previous_manifest_sha256=current.project_manifest_sha256,
            )
            return value

    adapter = DriftingManifestAdapter()
    app = application(tmp_path, adapter)
    prepared = app.prepare(
        vague_request="mid-flight project drift",
        expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"],
    )
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_PROJECT_STALE"
    assert adapter.generate_calls == 1 and not (tmp_path / "production-proposal.json").exists()


@pytest.mark.parametrize("variant", ("policy_id", "policy_version", "cost", "intent_budget"))
def test_existing_record_requires_all_product_fixed_invariants(tmp_path: Path, variant: str):
    adapter = Adapter()
    app = application(tmp_path, adapter)
    _, request_sha = app._request("fixed invariants")
    profile, _, selected_route, _, policy = app._connection()
    manifest_sha = ProductProjectManifestStore.load(tmp_path).project_manifest_sha256
    provenance = app._provenance(
        profile, selected_route, request_sha,
        project_id=app.project_id,
        project_manifest_sha256=manifest_sha,
    )
    intent, proposal = app._records(
        candidate(), request_sha256=request_sha, policy=policy,
        provenance_body=provenance,
    )
    if variant == "policy_id":
        proposal = replace(
            proposal,
            provider_policy=ProviderPolicyBinding(
                "different-profile", policy.policy_version, policy.policy_sha256,
            ),
        )
    elif variant == "policy_version":
        proposal = replace(
            proposal,
            provider_policy=ProviderPolicyBinding(
                policy.policy_id, "different-version", policy.policy_sha256,
            ),
        )
    elif variant == "cost":
        proposal = replace(
            proposal,
            estimated_cost_min=Decimal("1"),
            estimated_cost_max=Decimal("2"),
            currency="USD",
        )
    else:
        intent = replace(intent, budget_ceiling=Decimal("1"), currency="USD")
        proposal = replace(proposal, intent_sha256=intent.to_dict()["intent_sha256"])
    empty = app.planning.snapshot()
    app.planning.append_initial_proposal(
        intent=intent,
        proposal=proposal,
        expected_snapshot_sha256=empty["snapshot_sha256"],
        expected_project_manifest_sha256=manifest_sha,
    )
    reopened = application(tmp_path, Adapter(), token="reopened")
    with pytest.raises(ProductError) as exc:
        reopened.prepare(
            vague_request="fixed invariants",
            expected_planning_snapshot_sha256=reopened.planning.snapshot()["snapshot_sha256"],
        )
    assert exc.value.code == "ERR_TASK036_PLANNING_REQUEST_ID_CONFLICT"


def test_proposal_symlink_and_checksum_tamper_fail_before_readiness(tmp_path: Path):
    symlink_root = tmp_path / "symlink"
    symlink_root.mkdir()
    adapter = Adapter()
    app = application(symlink_root, adapter)
    target = symlink_root / "outside.json"
    target.write_text("{}", encoding="utf-8")
    (symlink_root / "production-proposal.json").symlink_to(target)
    with pytest.raises(ProductError):
        app.prepare(vague_request="symlink", expected_planning_snapshot_sha256="sha256:" + "0" * 64)
    assert adapter.ready_calls == 0

    tamper_root = tmp_path / "tamper"
    tamper_root.mkdir()
    generated = application(tamper_root, Adapter())
    prepared = generated.prepare(vague_request="seed", expected_planning_snapshot_sha256=generated.planning.snapshot()["snapshot_sha256"])
    generated.apply(confirmation_id=prepared["confirmation_id"])
    path = tamper_root / "production-proposal.json"
    path.write_text(path.read_text(encoding="utf-8").replace("Local plan", "Tampered plan"), encoding="utf-8")
    reopened_adapter = Adapter()
    reopened = application(tamper_root, reopened_adapter, token="reopen")
    with pytest.raises(ProductError):
        reopened.prepare(vague_request="new", expected_planning_snapshot_sha256="sha256:" + "0" * 64)
    assert reopened_adapter.ready_calls == 0


def test_model_cannot_use_reserved_provenance_sections(tmp_path: Path):
    value = candidate()
    bad = replace(value, sections=value.sections + (replace(value.sections[0], section_id="task036_request_binding"),))
    adapter = Adapter(result=bad)
    app = application(tmp_path, adapter)
    prepared = app.prepare(vague_request="reserved", expected_planning_snapshot_sha256=app.planning.snapshot()["snapshot_sha256"])
    with pytest.raises(ProductError) as exc:
        app.apply(confirmation_id=prepared["confirmation_id"])
    assert exc.value.code == "ERR_TASK036_PLANNING_RESERVED_SECTION"
    assert not (tmp_path / "production-proposal.json").exists()


def test_shell_bridge_runs_local_planning_only_after_exact_human_confirmation(tmp_path: Path):
    adapter = Adapter()
    planning_generation = application(tmp_path, adapter)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        planning_application=planning_generation.planning,
        planning_generation_application=planning_generation,
    )
    status = bridge.planning_generation_status({})
    assert status["available"] is True
    assert status["route_id"] == "planning-local"
    assert status["model_id"] == "qwen3:8b"
    assert status["cost_class"] == "LOCAL_FREE_AI"
    assert status["provider_execution_started"] is False
    assert status["paid_execution_authorized"] is False
    assert status["human_confirmation_required"] is True
    current = bridge.planning_snapshot({})
    prepared = bridge.planning_generation_prepare({
        "vague_request": "2秒の紹介動画",
        "expected_planning_snapshot_sha256": current["snapshot_sha256"],
    })
    assert prepared["human_confirmation_required"] is True
    assert adapter.ready_calls == 1 and adapter.generate_calls == 0
    result = bridge.planning_generation_apply({
        "confirmation_id": prepared["confirmation_id"],
    })
    assert result["paid_execution_authorized"] is False
    assert adapter.generate_calls == 1
    projected = bridge.planning_snapshot({"proposal_id": result["proposal_id"]})
    assert projected["workspace"]["go_status"] == "GO_REQUIRED"


def test_shell_bridge_unbound_cancel_and_broad_requests_fail_closed(tmp_path: Path):
    unbound = Task036ShellBridge(ShellApplicationService(product_version="0.22.0"))
    assert unbound.planning_generation_status({})["available"] is False
    with pytest.raises(ProductError) as missing:
        unbound.planning_generation_prepare({
            "vague_request": "never",
            "expected_planning_snapshot_sha256": "sha256:" + "0" * 64,
        })
    assert missing.value.code == "ERR_TASK036_PLANNING_GENERATION_NOT_BOUND"

    adapter = Adapter()
    planning_generation = application(tmp_path, adapter)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        planning_application=planning_generation.planning,
        planning_generation_application=planning_generation,
    )
    with pytest.raises(ProductError) as broad:
        bridge.planning_generation_prepare({
            "vague_request": "blocked",
            "expected_planning_snapshot_sha256": planning_generation.planning.snapshot()["snapshot_sha256"],
            "paid": True,
        })
    assert broad.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    prepared = bridge.planning_generation_prepare({
        "vague_request": "cancel",
        "expected_planning_snapshot_sha256": planning_generation.planning.snapshot()["snapshot_sha256"],
    })
    cancelled = bridge.planning_generation_cancel({
        "confirmation_id": prepared["confirmation_id"],
    })
    assert cancelled["cancelled"] is True
    assert adapter.generate_calls == 0


def test_shell_bridge_rejects_non_string_or_empty_planning_confirmation_ids(tmp_path: Path):
    adapter = Adapter()
    planning_generation = application(tmp_path, adapter)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        planning_application=planning_generation.planning,
        planning_generation_application=planning_generation,
    )
    for operation in (bridge.planning_generation_apply, bridge.planning_generation_cancel):
        for invalid in (None, 1, True, ""):
            with pytest.raises(ProductError) as exc:
                operation({"confirmation_id": invalid})
            assert exc.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"
    assert adapter.generate_calls == 0
