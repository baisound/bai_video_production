from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
)
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
)
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate


POLICY_SHA = "sha256:" + "c" * 64


def seed_proposal(root: Path) -> None:
    registry = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DEMO", 1, "Product intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Explain the product", "ja-JP", budget_ceiling=Decimal("5"),
    )
    registry.add_intent(intent)
    scenes = (
        BlueprintScene(
            "SC01", 0, 30, "Opening", AssetSourceStrategy.REAL_CAPTURE,
            GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
        ),
        BlueprintScene(
            "SC02", 30, 60, "Promise", AssetSourceStrategy.COMPOSITE,
            GenerationRisk.B_HEADLINE, CameraMotion.SUBTLE, (),
        ),
    )
    blueprint = ProductionBlueprint("BP-DEMO-027", "Demo", FrameRate(30), 60, (), scenes)
    registry.add_proposal(ProductionProposalRevision(
        "PROPOSAL-DEMO", 1, intent.to_dict()["intent_sha256"], blueprint,
        (
            ProposalSection("concept", "CONCEPT", "Concept", "A clear introduction"),
            ProposalSection("script", "SCRIPT", "Script", "Opening then promise"),
        ),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    ))
    ProductionProposalSnapshotStore.save(root / "production-proposal.json", registry)


def app(root: Path) -> Task027PlanningApplication:
    tokens = iter(("go-confirm", "install-confirm"))
    return Task027PlanningApplication(project_root=root, project_id="project-1", token_factory=lambda: next(tokens))


def approve(service: Task027PlanningApplication) -> dict:
    state = service.snapshot()
    prepared = service.prepare_go(
        proposal_id="PROPOSAL-DEMO",
        proposal_revision=1,
        reference_bindings=(),
        cost_ceiling="3",
        rights_warnings_acknowledged=False,
        expected_snapshot_sha256=state["snapshot_sha256"],
    )
    return service.approve_go(confirmation_id=prepared["confirmation_id"], approved_by="owner")


def test_snapshot_projects_persisted_scene_contract_without_execution(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    state = app(tmp_path).snapshot()
    assert state["proposal_ids"] == ["PROPOSAL-DEMO"]
    assert state["workspace"]["go_status"] == "GO_REQUIRED"
    assert [scene["scene_id"] for scene in state["workspace"]["blueprint"]["scenes"]] == ["SC01", "SC02"]
    assert state["installation"]["status"] == "GO_REQUIRED"
    assert state["provider_execution_started"] is False
    assert state["paid_execution_authorized"] is False
    assert state["budget_reservation_created"] is False
    assert state["resolve_mutation_started"] is False


def test_go_is_one_shot_persisted_and_does_not_install_or_execute(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    service = app(tmp_path)
    result = approve(service)
    assert result["approved_plan"]["approved_by"] == "owner"
    reopened = Task027PlanningApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["workspace"]["go_status"] == "APPROVED"
    assert reopened["installation"]["status"] == "NOT_INSTALLED"
    assert reopened["provider_execution_started"] is False
    with pytest.raises(ProductError) as exc:
        service.approve_go(confirmation_id="go-confirm", approved_by="owner")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_CONFIRMATION_INVALID"


def test_approved_plan_install_is_separate_exact_and_restart_detectable(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    service = app(tmp_path)
    approved = approve(service)
    state = service.snapshot()
    prepared = service.prepare_install_plan(
        plan_id=approved["approved_plan"]["plan_id"],
        expected_proposal_snapshot_sha256=state["snapshot_sha256"],
        expected_production_snapshot_sha256=state["installation"]["production"]["snapshot_sha256"],
    )
    assert prepared["scene_count"] == 2
    installed = service.apply_install_plan(confirmation_id=prepared["confirmation_id"])
    assert installed["application"]["installation"]["status"] == "INSTALLED"
    assert installed["application"]["installation"]["trace"]["plan_id"] == approved["approved_plan"]["plan_id"]
    # Each Scene produces its required VIDEO plus the default BGM Slot.
    assert installed["application"]["installation"]["production"]["slot_count"] == 4
    reopened = Task027PlanningApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["installation"]["status"] == "INSTALLED"
    with pytest.raises(ProductError) as exc:
        service.apply_install_plan(confirmation_id="install-confirm")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_INSTALL_CONFIRMATION_INVALID"


def test_new_proposal_revision_after_prepare_consumes_stale_go(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    service = app(tmp_path)
    state = service.snapshot()
    prepared = service.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1, reference_bindings=(), cost_ceiling="3",
        rights_warnings_acknowledged=False, expected_snapshot_sha256=state["snapshot_sha256"],
    )
    registry = ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json")
    previous_sha = ProductionProposalSnapshotStore.snapshot(registry)["snapshot_sha256"]
    first = registry.latest_proposal("PROPOSAL-DEMO")
    registry.add_proposal(ProductionProposalRevision(
        "PROPOSAL-DEMO", 2, first.intent_sha256, first.blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Revised"),),
        first.provider_policy, first.estimated_cost_min, first.estimated_cost_max, first.currency,
        parent_proposal_sha256=first.to_dict()["proposal_sha256"],
    ))
    ProductionProposalSnapshotStore.save(
        tmp_path / "production-proposal.json", registry,
        expected_previous_snapshot_sha256=previous_sha,
    )
    with pytest.raises(ProductError) as exc:
        service.approve_go(confirmation_id=prepared["confirmation_id"], approved_by="owner")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_SNAPSHOT_CONFLICT"
    with pytest.raises(ProductError) as exc:
        service.approve_go(confirmation_id=prepared["confirmation_id"], approved_by="owner")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_CONFIRMATION_INVALID"


def test_planning_and_production_project_scope_must_match(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    production = Task037ProductionControlApplication(project_root=tmp_path, project_id="other-project")
    with pytest.raises(ProductError) as exc:
        Task027PlanningApplication(
            project_root=tmp_path,
            project_id="project-1",
            production_control=production,
        )
    assert exc.value.code == "ERR_PLANNING_APPLICATION_PRODUCTION_SCOPE_MISMATCH"


def test_concurrent_go_publication_allows_exactly_one_writer(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    first = Task027PlanningApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "go-first")
    second = Task027PlanningApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "go-second")
    snapshot = first.snapshot()["snapshot_sha256"]
    first.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1, reference_bindings=(), cost_ceiling="3",
        rights_warnings_acknowledged=False, expected_snapshot_sha256=snapshot,
    )
    second.prepare_go(
        proposal_id="PROPOSAL-DEMO", proposal_revision=1, reference_bindings=(), cost_ceiling="3",
        rights_warnings_acknowledged=False, expected_snapshot_sha256=snapshot,
    )

    def publish(service: Task027PlanningApplication, token: str):
        try:
            service.approve_go(confirmation_id=token, approved_by="owner")
            return "PASS"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda value: publish(*value), ((first, "go-first"), (second, "go-second"))))
    assert results.count("PASS") == 1
    assert len(ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json").approved_plans) == 1


def revision_sections(*, concept_title: str = "Concept", concept_body: str = "A clearer introduction") -> list[dict[str, str]]:
    return [
        {"section_id": "concept", "kind": "CONCEPT", "title": concept_title, "body": concept_body},
        {"section_id": "script", "kind": "SCRIPT", "title": "Script", "body": "Opening then promise"},
    ]


def test_human_revision_is_append_only_persisted_and_no_effect(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    service = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-1",
        token_factory=lambda: "revision-confirm",
    )
    before = service.snapshot()
    prepared = service.prepare_revision(
        proposal_id="PROPOSAL-DEMO",
        sections=revision_sections(),
        expected_snapshot_sha256=before["snapshot_sha256"],
    )
    assert prepared["proposal"]["revision"] == 2
    assert prepared["proposal"]["parent_proposal_sha256"] == before["workspace"]["latest_proposal_sha256"]
    assert prepared["provider_execution_started"] is False
    assert prepared["paid_execution_authorized"] is False
    assert prepared["publish_started"] is False

    result = service.apply_revision(confirmation_id=prepared["confirmation_id"])
    workspace = result["application"]["workspace"]
    assert workspace["latest_revision"] == 2
    assert workspace["go_status"] == "GO_REQUIRED"
    assert workspace["changed_section_ids_from_previous"] == ["concept"]
    assert result["provider_execution_started"] is False
    assert result["resolve_mutation_started"] is False
    assert result["publish_started"] is False

    registry = ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json")
    first, second = registry.proposals["PROPOSAL-DEMO"]
    assert second.intent_sha256 == first.intent_sha256
    assert second.blueprint.to_dict() == first.blueprint.to_dict()
    assert second.provider_policy == first.provider_policy
    assert (second.estimated_cost_min, second.estimated_cost_max, second.currency) == (
        first.estimated_cost_min,
        first.estimated_cost_max,
        first.currency,
    )
    reopened = Task027PlanningApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["workspace"]["latest_revision"] == 2
    with pytest.raises(ProductError) as exc:
        service.apply_revision(confirmation_id="revision-confirm")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_REVISION_CONFIRMATION_INVALID"


def test_human_revision_after_go_requires_fresh_go_without_removing_prior_plan(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    service = Task027PlanningApplication(
        project_root=tmp_path,
        project_id="project-1",
        token_factory=iter(("go-confirm", "revision-confirm")).__next__,
    )
    approved = approve(service)
    state = service.snapshot()
    prepared = service.prepare_revision(
        proposal_id="PROPOSAL-DEMO",
        sections=revision_sections(concept_title="Revised concept"),
        expected_snapshot_sha256=state["snapshot_sha256"],
    )
    applied = service.apply_revision(confirmation_id=prepared["confirmation_id"])
    workspace = applied["application"]["workspace"]
    assert workspace["go_status"] == "GO_REQUIRED"
    assert workspace["new_go_required_after_revision"] is True
    assert workspace["prior_approved_plan_ids"] == [approved["approved_plan"]["plan_id"]]
    assert workspace["approved_plan"] is None


@pytest.mark.parametrize(
    ("sections", "code"),
    (
        (revision_sections(concept_body="A clear introduction"), "ERR_PLANNING_APPLICATION_REVISION_NO_CHANGE"),
        (list(reversed(revision_sections())), "ERR_PLANNING_APPLICATION_REVISION_SECTION_IDENTITY"),
        ([{**revision_sections()[0], "kind": "SCRIPT"}, revision_sections()[1]], "ERR_PLANNING_APPLICATION_REVISION_SECTION_IDENTITY"),
        ([{**revision_sections()[0], "extra": "forbidden"}, revision_sections()[1]], "ERR_PLANNING_APPLICATION_REVISION_SECTIONS_INVALID"),
        (revision_sections() * 33, "ERR_PLANNING_APPLICATION_REVISION_SECTIONS_INVALID"),
    ),
)
def test_human_revision_rejects_noop_identity_drift_broad_fields_and_cap_plus_one(
    tmp_path: Path,
    sections: list[dict[str, str]],
    code: str,
) -> None:
    seed_proposal(tmp_path)
    service = Task027PlanningApplication(project_root=tmp_path, project_id="project-1")
    with pytest.raises(ProductError) as exc:
        service.prepare_revision(
            proposal_id="PROPOSAL-DEMO",
            sections=sections,
            expected_snapshot_sha256=service.snapshot()["snapshot_sha256"],
        )
    assert exc.value.code == code


def test_concurrent_revision_publication_allows_exactly_one_writer(tmp_path: Path) -> None:
    seed_proposal(tmp_path)
    first = Task027PlanningApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "revision-first")
    second = Task027PlanningApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "revision-second")
    snapshot = first.snapshot()["snapshot_sha256"]
    first.prepare_revision(proposal_id="PROPOSAL-DEMO", sections=revision_sections(), expected_snapshot_sha256=snapshot)
    second.prepare_revision(
        proposal_id="PROPOSAL-DEMO",
        sections=revision_sections(concept_title="Other title"),
        expected_snapshot_sha256=snapshot,
    )
    first.apply_revision(confirmation_id="revision-first")
    with pytest.raises(ProductError) as exc:
        second.apply_revision(confirmation_id="revision-second")
    assert exc.value.code == "ERR_PLANNING_APPLICATION_SNAPSHOT_CONFLICT"
    assert len(ProductionProposalSnapshotStore.load(tmp_path / "production-proposal.json").proposals["PROPOSAL-DEMO"]) == 2
