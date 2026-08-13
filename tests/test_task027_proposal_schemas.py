from __future__ import annotations

from decimal import Decimal
from importlib import resources
import json
from pathlib import Path

from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint,
)
from ai_video_production.production_proposal import (
    CreationIntent, ProductionGoApprovalService, ProductionProposalRegistry,
    ProductionProposalRevision, ProposalSection, ProviderPolicyBinding,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.timebase import FrameRate

POLICY_SHA = "sha256:" + "c" * 64


def documents():
    intent = CreationIntent(
        "INTENT-SCHEMA", 1, "Intro", "Viewers", "YouTube", "16:9", Decimal("2"),
        "Calm", "Opening", "ja-JP", budget_ceiling=Decimal("4"),
    )
    scene = BlueprintScene(
        "SC01", 0, 60, "opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-SCHEMA1", "Schema", FrameRate(30), 60, (), (scene,))
    proposal = ProductionProposalRevision(
        "PROPOSAL-SCHEMA", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "Opening"),),
        ProviderPolicyBinding("policy", "1", POLICY_SHA), Decimal("1"), Decimal("2"), "USD",
    )
    registry = ProductionProposalRegistry(); registry.add_intent(intent); registry.add_proposal(proposal)
    go = ProductionGoApprovalService(registry, token_factory=lambda: "go")
    go.prepare_go(
        proposal_id="PROPOSAL-SCHEMA", proposal_revision=1, reference_bindings=(),
        cost_ceiling="3", rights_warnings_acknowledged=False,
    )
    plan = go.approve_go(confirmation_id="go", approved_by="owner")
    return intent.to_dict(), proposal.to_dict(), plan.to_dict()


def test_task027_proposal_contract_schemas_validate_and_package_match() -> None:
    root = Path(__file__).parents[1]
    names = (
        "creation-intent.schema.json",
        "production-proposal-revision.schema.json",
        "approved-production-plan.schema.json",
    )
    for name, document in zip(names, documents(), strict=True):
        canonical = root / "schemas" / name
        validate_instance(document, canonical)
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name)
        assert json.loads(canonical.read_text(encoding="utf-8")) == json.loads(packaged.read_text(encoding="utf-8"))
