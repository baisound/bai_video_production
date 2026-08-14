from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_video_production.approved_plan_orchestration import (
    ApprovedPlanProductionControlInstaller,
    ApprovedPlanVerifier,
)
from ai_video_production.errors import ProductError
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    CameraMotion,
    GenerationRisk,
)
from ai_video_production.production_blueprint_v2 import (
    AssetLockBinding,
    BlueprintSceneV2,
    CharacterLockBinding,
    CharacterRole,
    FrameIntent,
    FrameKind,
    FrameReferenceBinding,
    ProductionBlueprintV2,
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
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
SHA_F = "sha256:" + "f" * 64
POLICY_SHA = "sha256:" + "1" * 64


def _frame(kind: FrameKind, suffix: str, checksums: tuple[str, str, str]) -> FrameIntent:
    character_sha, space_sha, composition_sha = checksums
    return FrameIntent(
        kind,
        f"{kind.value} visual",
        "show exact approved state",
        ("subject", "display"),
        ("crew",),
        ("subject", "display", "background"),
        "locked eye-level camera",
        FrameReferenceBinding(
            (
                CharacterLockBinding(
                    CharacterRole.PRIMARY,
                    f"ASSET-CHAR-{suffix}",
                    character_sha,
                    f"SLOT-CHAR-{suffix}",
                    f"CAND-CHAR-{suffix}",
                ),
            ),
            AssetLockBinding(
                f"ASSET-SPACE-{suffix}",
                space_sha,
                f"SLOT-SPACE-{suffix}",
                f"CAND-SPACE-{suffix}",
            ),
            AssetLockBinding(
                f"ASSET-COMP-{suffix}",
                composition_sha,
                f"SLOT-COMP-{suffix}",
                f"CAND-COMP-{suffix}",
            ),
        ),
        "medium wide",
    )


def _blueprint() -> ProductionBlueprintV2:
    scene = BlueprintSceneV2(
        "SC01",
        0,
        300,
        "Opening",
        AssetSourceStrategy.COMPOSITE,
        GenerationRisk.B_HEADLINE,
        CameraMotion.STATIC,
        _frame(FrameKind.START, "START", (SHA_A, SHA_B, SHA_C)),
        _frame(FrameKind.END, "END", (SHA_D, SHA_E, SHA_F)),
        post_composite_text=True,
    )
    return ProductionBlueprintV2("BP-V6-PROPOSAL", "V6 Proposal", FrameRate(30, 1), 300, (scene,))


def _bindings() -> tuple[ReferenceAssetBinding, ...]:
    return (
        ReferenceAssetBinding("SC01:START:CHARACTER:0", "ASSET-CHAR-START", SHA_A),
        ReferenceAssetBinding("SC01:START:SPACE", "ASSET-SPACE-START", SHA_B),
        ReferenceAssetBinding("SC01:START:COMPOSITION", "ASSET-COMP-START", SHA_C),
        ReferenceAssetBinding("SC01:END:CHARACTER:0", "ASSET-CHAR-END", SHA_D),
        ReferenceAssetBinding("SC01:END:SPACE", "ASSET-SPACE-END", SHA_E),
        ReferenceAssetBinding("SC01:END:COMPOSITION", "ASSET-COMP-END", SHA_F),
    )


def _registry() -> tuple[ProductionProposalRegistry, ProductionBlueprintV2]:
    registry = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-V6",
        1,
        "Product introduction",
        "Viewers",
        "YouTube",
        "16:9",
        Decimal("10"),
        "Clear",
        "Explain the approved product state",
        "ja-JP",
        budget_ceiling=Decimal("20"),
    )
    registry.add_intent(intent)
    blueprint = _blueprint()
    registry.add_proposal(
        ProductionProposalRevision(
            "PROPOSAL-V6",
            1,
            intent.to_dict()["intent_sha256"],
            blueprint,
            (ProposalSection("concept", "CONCEPT", "Concept", "Exact frame-bound proposal."),),
            ProviderPolicyBinding("policy-v6", "1", POLICY_SHA),
            Decimal("1"),
            Decimal("10"),
            "USD",
        )
    )
    return registry, blueprint


def _approve() -> tuple[ProductionProposalRegistry, ProductionBlueprintV2, str]:
    registry, blueprint = _registry()
    go = ProductionGoApprovalService(registry, token_factory=lambda: "go-v6")
    prepared = go.prepare_go(
        proposal_id="PROPOSAL-V6",
        proposal_revision=1,
        reference_bindings=_bindings(),
        cost_ceiling="12",
        rights_warnings_acknowledged=False,
    )
    assert prepared["provider_execution_started"] is False
    plan = go.approve_go(confirmation_id="go-v6", approved_by="owner")
    return registry, blueprint, plan.plan_id


def test_v2_go_requires_every_deterministic_frame_path_and_exact_asset_identity() -> None:
    registry, _ = _registry()
    service = ProductionGoApprovalService(registry, token_factory=lambda: "go-v6")

    with pytest.raises(ProductError) as missing:
        service.prepare_go(
            proposal_id="PROPOSAL-V6",
            proposal_revision=1,
            reference_bindings=_bindings()[:-1],
            cost_ceiling="12",
            rights_warnings_acknowledged=False,
        )
    assert missing.value.code == "ERR_PRODUCTION_GO_REFERENCE_BINDING_MISMATCH"

    changed = list(_bindings())
    changed[0] = ReferenceAssetBinding("SC01:START:CHARACTER:0", "ASSET-WRONG", SHA_A)
    with pytest.raises(ProductError) as identity:
        service.prepare_go(
            proposal_id="PROPOSAL-V6",
            proposal_revision=1,
            reference_bindings=changed,
            cost_ceiling="12",
            rights_warnings_acknowledged=False,
        )
    assert identity.value.code == "ERR_PRODUCTION_GO_FRAME_BINDING_IDENTITY_MISMATCH"
    assert identity.value.details == {"mismatched": ["SC01:START:CHARACTER:0"]}


def test_v2_human_go_verifies_identity_but_production_control_requires_current_world_lock() -> None:
    registry, blueprint, plan_id = _approve()
    plan = ApprovedPlanVerifier.require_current(
        proposal_registry=registry,
        plan_id=plan_id,
        blueprint=blueprint,
    )
    assert plan.blueprint_sha256 == blueprint.to_dict()["blueprint_sha256"]
    assert plan.to_dict()["publish_authorized"] is False

    with pytest.raises(ProductError) as blocked:
        ApprovedPlanProductionControlInstaller.compile(
            proposal_registry=registry,
            plan_id=plan_id,
            blueprint=blueprint,
            project_id="project-v6",
        )
    assert blocked.value.code == "ERR_BLUEPRINT_V2_WORLD_LOCK_REGISTRY_REQUIRED"


def test_v2_proposal_and_approved_plan_snapshot_round_trip_with_cas(tmp_path: Path) -> None:
    registry, blueprint, _ = _approve()
    path = tmp_path / "proposal-v2.json"
    ProductionProposalSnapshotStore.save(path, registry)
    loaded = ProductionProposalSnapshotStore.load(path)
    assert loaded.to_dict() == registry.to_dict()
    loaded_blueprint = loaded.latest_proposal("PROPOSAL-V6").blueprint
    assert isinstance(loaded_blueprint, ProductionBlueprintV2)
    assert loaded_blueprint.to_dict() == blueprint.to_dict()

    previous = ProductionProposalSnapshotStore.snapshot(loaded)["snapshot_sha256"]
    ProductionProposalSnapshotStore.save(
        path,
        loaded,
        expected_previous_snapshot_sha256=previous,
    )
