from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

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
from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def registry() -> ProductionProposalRegistry:
    result = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-DEMO", 1, "Product intro", "Viewers", "YouTube", "16:9", Decimal("10"),
        "Calm", "Explain the product", "ja-JP", budget_ceiling=Decimal("20"),
    )
    result.add_intent(intent)
    refs = (
        BlueprintReference("PERSON-A", ReferenceKind.PERSON, ReferenceStatus.LOCKED, "person.png"),
        BlueprintReference("SPACE-A", ReferenceKind.SPACE, ReferenceStatus.AVAILABLE, "space.png"),
    )
    scene = BlueprintScene(
        "SC01", 0, 300, "Opening", AssetSourceStrategy.REUSE_EXISTING,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("PERSON-A", "SPACE-A"),
    )
    blueprint = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, refs, (scene,))
    proposal = ProductionProposalRevision(
        "PROPOSAL-DEMO", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "A concise opening."),),
        ProviderPolicyBinding("policy", "1", SHA_C), Decimal("2"), Decimal("10"), "USD",
    )
    result.add_proposal(proposal)
    service = ProductionGoApprovalService(result, token_factory=lambda: "go")
    service.prepare_go(
        proposal_id="PROPOSAL-DEMO",
        proposal_revision=1,
        reference_bindings=(
            ReferenceAssetBinding("PERSON-A", "asset-person", SHA_A),
            ReferenceAssetBinding("SPACE-A", "asset-space", SHA_B),
        ),
        cost_ceiling="12",
        rights_warnings_acknowledged=False,
    )
    service.approve_go(confirmation_id="go", approved_by="owner")
    return result


def test_proposal_snapshot_roundtrip_and_cas(tmp_path: Path) -> None:
    source = registry()
    path = tmp_path / "proposal.json"
    first = ProductionProposalSnapshotStore.save(path, source)
    loaded = ProductionProposalSnapshotStore.load(path)
    assert loaded.to_dict() == source.to_dict()
    snap = ProductionProposalSnapshotStore.snapshot(loaded)
    assert snap["credential_values_embedded"] is False
    assert snap["provider_execution_authorized"] is False
    second = ProductionProposalSnapshotStore.save(path, loaded, expected_previous_snapshot_sha256=snap["snapshot_sha256"])
    assert second.bytes_written == first.bytes_written


def test_project_scoped_proposal_snapshot_roundtrip_and_foreign_scope_rejection(tmp_path: Path) -> None:
    source = registry()
    path = tmp_path / "proposal.json"
    ProductionProposalSnapshotStore.save(path, source, project_id="project-a")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["snapshot_version"] == "1.1.0"
    assert document["project_id"] == "project-a"
    assert ProductionProposalSnapshotStore.load(
        path,
        expected_project_id="project-a",
    ).to_dict() == source.to_dict()
    scoped_sha = document["snapshot_sha256"]
    ProductionProposalSnapshotStore.save(
        path,
        source,
        project_id="project-a",
        expected_previous_snapshot_sha256=scoped_sha,
    )
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.load(path, expected_project_id="project-b")
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_PROJECT_SCOPE_MISMATCH"


def test_generic_legacy_projection_cannot_downgrade_scoped_snapshot(tmp_path: Path) -> None:
    source = registry()
    path = tmp_path / "proposal.json"
    ProductionProposalSnapshotStore.save(path, source, project_id="project-a")
    before = path.read_bytes()
    generic = ProductionProposalSnapshotStore.load(path)
    legacy_sha = ProductionProposalSnapshotStore.snapshot(generic)["snapshot_sha256"]
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.save(
            path,
            generic,
            expected_previous_snapshot_sha256=legacy_sha,
        )
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_SCOPE_CHANGE_FORBIDDEN"
    assert path.read_bytes() == before


def test_existing_oversize_snapshot_save_fails_before_read_and_preserves_bytes(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    payload = b" " * (16 * 1024 * 1024 + 1)
    path.write_bytes(payload)
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.save(
            path,
            registry(),
            expected_previous_snapshot_sha256="sha256:" + "0" * 64,
        )
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_SIZE"
    assert path.read_bytes() == payload


def test_product_runtime_rejects_legacy_unscoped_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    ProductionProposalSnapshotStore.save(path, registry())
    assert ProductionProposalSnapshotStore.load(path).to_dict() == registry().to_dict()
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.load(path, expected_project_id="project-a")
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_PROJECT_SCOPE_REQUIRED"


def test_proposal_snapshot_requires_cas_for_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    source = registry()
    ProductionProposalSnapshotStore.save(path, source)
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.save(path, source)
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_CAS_REQUIRED"


def test_proposal_snapshot_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    ProductionProposalSnapshotStore.save(path, registry())
    data = json.loads(path.read_text(encoding="utf-8"))
    data["registry"]["proposals"][0]["sections"][0]["body"] = "tampered"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.load(path)
    assert exc.value.code in {"ERR_PROPOSAL_SNAPSHOT_CHECKSUM", "ERR_PROPOSAL_SNAPSHOT_REGISTRY_CHECKSUM"}


def test_proposal_snapshot_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real.json"
    ProductionProposalSnapshotStore.save(target, registry())
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ProductError) as exc:
        ProductionProposalSnapshotStore.load(link)
    assert exc.value.code == "ERR_PROPOSAL_SNAPSHOT_FILE_INVALID"
