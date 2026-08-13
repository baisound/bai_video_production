from __future__ import annotations

from decimal import Decimal

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintReference,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
    ReferenceKind,
    ReferenceStatus,
)
from ai_video_production.production_proposal import (
    CreationIntent,
    ProductionGoApprovalService,
    ProductionProposalRegistry,
    ProductionProposalRevision,
    ProposalSection,
    ProviderPolicyBinding,
    ReferenceAssetBinding,
)
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def blueprint() -> ProductionBlueprint:
    refs = (
        BlueprintReference("PERSON-A", ReferenceKind.PERSON, ReferenceStatus.LOCKED, "person.png"),
        BlueprintReference("SPACE-A", ReferenceKind.SPACE, ReferenceStatus.AVAILABLE, "space.png"),
        BlueprintReference("FUTURE-ASSET", ReferenceKind.ASSET, ReferenceStatus.PLANNED),
    )
    scene = BlueprintScene(
        "SC01",
        0,
        300,
        "Opening",
        AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT,
        CameraMotion.SUBTLE,
        ("PERSON-A", "SPACE-A", "FUTURE-ASSET"),
    )
    return ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, refs, (scene,))


def intent(revision: int = 1) -> CreationIntent:
    return CreationIntent(
        intent_id="INTENT-DEMO",
        revision=revision,
        purpose="YouTube introduction",
        audience="Existing viewers",
        platform="YouTube",
        aspect_ratio="16:9",
        target_duration_seconds=Decimal("10"),
        style_tone="Professional but warm",
        story_message="Explain the product clearly",
        language="ja-JP",
        budget_ceiling=Decimal("25"),
        currency="USD",
        rights_constraints=("Use only owned references",),
    )


def proposal(registry: ProductionProposalRegistry, *, revision: int = 1, parent: str | None = None, warning: bool = True) -> ProductionProposalRevision:
    current_intent = registry.intents["INTENT-DEMO@1"]
    return ProductionProposalRevision(
        proposal_id="PROPOSAL-DEMO",
        revision=revision,
        parent_proposal_sha256=parent,
        intent_sha256=current_intent.to_dict()["intent_sha256"],
        blueprint=blueprint(),
        sections=(
            ProposalSection("concept", "CONCEPT", "Concept", "A concise creator-studio introduction."),
            ProposalSection("script", "SCRIPT", "Script", "Opening, explanation, close."),
        ),
        provider_policy=ProviderPolicyBinding("policy-demo", "1", SHA_C),
        estimated_cost_min=Decimal("5"),
        estimated_cost_max=Decimal("12"),
        currency="USD",
        rights_warnings=("Confirm PERSON-A usage scope",) if warning else (),
    )


def refs() -> tuple[ReferenceAssetBinding, ...]:
    return (
        ReferenceAssetBinding("PERSON-A", "asset-person", SHA_A),
        ReferenceAssetBinding("SPACE-A", "asset-space", SHA_B),
    )


def registry_with_proposal(*, warning: bool = True) -> ProductionProposalRegistry:
    registry = ProductionProposalRegistry()
    registry.add_intent(intent())
    registry.add_proposal(proposal(registry, warning=warning))
    return registry


def test_intent_and_proposal_revision_chain_are_deterministic() -> None:
    registry = registry_with_proposal()
    first = registry.latest_proposal("PROPOSAL-DEMO")
    first_sha = first.to_dict()["proposal_sha256"]
    second = proposal(registry, revision=2, parent=first_sha)
    registry.add_proposal(second)
    assert registry.latest_proposal("PROPOSAL-DEMO").revision == 2
    assert registry.to_dict() == registry.to_dict()
    assert registry.to_dict()["provider_execution_started"] is False


def test_proposal_rejects_unknown_intent_and_broken_parent_chain() -> None:
    registry = ProductionProposalRegistry()
    registry.add_intent(intent())
    bad = ProductionProposalRevision(
        proposal_id="PROPOSAL-OTHER",
        revision=1,
        intent_sha256=SHA_A,
        blueprint=blueprint(),
        sections=(ProposalSection("concept", "CONCEPT", "Concept", "Body"),),
        provider_policy=ProviderPolicyBinding("policy", "1", SHA_C),
    )
    with pytest.raises(ProductError) as exc:
        registry.add_proposal(bad)
    assert exc.value.code == "ERR_PRODUCTION_PROPOSAL_INTENT_UNKNOWN"

    registry.add_proposal(proposal(registry))
    with pytest.raises(ProductError) as exc:
        registry.add_proposal(proposal(registry, revision=2, parent=SHA_A))
    assert exc.value.code == "ERR_PRODUCTION_PROPOSAL_PARENT_MISMATCH"


def test_go_requires_exact_existing_reference_bindings_cost_and_rights_ack() -> None:
    registry = registry_with_proposal()
    service = ProductionGoApprovalService(registry, token_factory=lambda: "go-1")
    with pytest.raises(ProductError) as exc:
        service.prepare_go(
            proposal_id="PROPOSAL-DEMO",
            proposal_revision=1,
            reference_bindings=(refs()[0],),
            cost_ceiling="20",
            rights_warnings_acknowledged=True,
        )
    assert exc.value.code == "ERR_PRODUCTION_GO_REFERENCE_BINDING_MISMATCH"

    with pytest.raises(ProductError) as exc:
        service.prepare_go(
            proposal_id="PROPOSAL-DEMO",
            proposal_revision=1,
            reference_bindings=refs(),
            cost_ceiling="11.99",
            rights_warnings_acknowledged=True,
        )
    assert exc.value.code == "ERR_PRODUCTION_GO_COST_CEILING_TOO_LOW"

    with pytest.raises(ProductError) as exc:
        service.prepare_go(
            proposal_id="PROPOSAL-DEMO",
            proposal_revision=1,
            reference_bindings=refs(),
            cost_ceiling="20",
            rights_warnings_acknowledged=False,
        )
    assert exc.value.code == "ERR_PRODUCTION_GO_RIGHTS_ACKNOWLEDGEMENT_REQUIRED"


def test_go_creates_immutable_plan_without_starting_provider_or_resolve() -> None:
    registry = registry_with_proposal()
    service = ProductionGoApprovalService(registry, token_factory=lambda: "go-1")
    prepared = service.prepare_go(
        proposal_id="PROPOSAL-DEMO",
        proposal_revision=1,
        reference_bindings=refs(),
        cost_ceiling="20",
        rights_warnings_acknowledged=True,
    )
    assert prepared["provider_execution_started"] is False
    assert prepared["resolve_mutation_started"] is False
    plan = service.approve_go(confirmation_id="go-1", approved_by="owner")
    body = plan.to_dict()
    assert body["human_go_approved"] is True
    assert body["provider_execution_started"] is False
    assert body["resolve_mutation_started"] is False
    assert body["publish_authorized"] is False
    assert {row["reference_id"] for row in body["reference_bindings"]} == {"PERSON-A", "SPACE-A"}
    assert "FUTURE-ASSET" not in {row["reference_id"] for row in body["reference_bindings"]}
    with pytest.raises(ProductError) as exc:
        service.approve_go(confirmation_id="go-1", approved_by="owner")
    assert exc.value.code == "ERR_PRODUCTION_GO_CONFIRMATION_INVALID"


def test_go_confirmation_becomes_stale_when_a_new_proposal_revision_is_added() -> None:
    registry = registry_with_proposal(warning=False)
    service = ProductionGoApprovalService(registry, token_factory=lambda: "go-1")
    service.prepare_go(
        proposal_id="PROPOSAL-DEMO",
        proposal_revision=1,
        reference_bindings=refs(),
        cost_ceiling="20",
        rights_warnings_acknowledged=False,
    )
    first_sha = registry.latest_proposal("PROPOSAL-DEMO").to_dict()["proposal_sha256"]
    registry.add_proposal(proposal(registry, revision=2, parent=first_sha, warning=False))
    with pytest.raises(ProductError) as exc:
        service.approve_go(confirmation_id="go-1", approved_by="owner")
    assert exc.value.code == "ERR_PRODUCTION_GO_CONFIRMATION_STALE"


def test_go_can_only_be_prepared_for_latest_revision() -> None:
    registry = registry_with_proposal(warning=False)
    first_sha = registry.latest_proposal("PROPOSAL-DEMO").to_dict()["proposal_sha256"]
    registry.add_proposal(proposal(registry, revision=2, parent=first_sha, warning=False))
    service = ProductionGoApprovalService(registry)
    with pytest.raises(ProductError) as exc:
        service.prepare_go(
            proposal_id="PROPOSAL-DEMO",
            proposal_revision=1,
            reference_bindings=refs(),
            cost_ceiling="20",
            rights_warnings_acknowledged=False,
        )
    assert exc.value.code == "ERR_PRODUCTION_GO_PROPOSAL_NOT_LATEST"
