from __future__ import annotations

from pathlib import Path

import pytest

from ai_video_production.audio_workspace import AudioWorkspaceRegistry
from ai_video_production.audio_workspace_store import AudioWorkspaceSnapshotStore
from ai_video_production.candidate_audit import CandidateAuditRegistry
from ai_video_production.candidate_audit_store import CandidateAuditSnapshotStore
from ai_video_production.continuity_registry import ContinuityRegistry
from ai_video_production.continuity_registry_store import ContinuityRegistryStore
from ai_video_production.errors import ProductError
from ai_video_production.production_bundle_store import ProductionBundleManifestStore
from ai_video_production.production_control import ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.prompt_registry import PromptGenerationRegistry
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore


def registries():
    return (
        ProductionControlRegistry(), CandidateAuditRegistry(), PromptGenerationRegistry(),
        ContinuityRegistry(), AudioWorkspaceRegistry(),
    )


def save_stores(root: Path, production, audits, prompts, continuity, audio):
    ProductionControlSnapshotStore.save(root / "production-control.json", production)
    CandidateAuditSnapshotStore.save(root / "candidate-audit.json", audits)
    PromptRegistrySnapshotStore.save(root / "prompt-registry.json", prompts)
    ContinuityRegistryStore.save(root / "continuity-registry.json", continuity)
    AudioWorkspaceSnapshotStore.save(root / "audio-workspace.json", audio)


def test_validated_manifest_pins_exact_cross_store_snapshot_set(tmp_path: Path):
    production, audits, prompts, continuity, audio = registries()
    save_stores(tmp_path, production, audits, prompts, continuity, audio)
    manifest = ProductionBundleManifestStore.build(
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio
    )
    ProductionBundleManifestStore.save(tmp_path / "production-bundle.json", manifest)
    recovered = ProductionBundleManifestStore.recover(tmp_path)
    assert recovered.validation.to_dict()["status"] == "PASS"
    assert recovered.manifest_sha256 == manifest["manifest_sha256"]


def test_recovery_fails_closed_when_one_valid_store_changes_after_manifest(tmp_path: Path):
    production, audits, prompts, continuity, audio = registries()
    save_stores(tmp_path, production, audits, prompts, continuity, audio)
    manifest = ProductionBundleManifestStore.build(
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio
    )
    ProductionBundleManifestStore.save(tmp_path / "production-bundle.json", manifest)

    previous = ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"]
    production.add_slot(SceneAssetSlot("slot-new", "project-1", "scene-1", SlotKind.START_FRAME, True))
    ProductionControlSnapshotStore.save(
        tmp_path / "production-control.json", production, expected_previous_snapshot_sha256=previous
    )
    with pytest.raises(ProductError) as exc:
        ProductionBundleManifestStore.recover(tmp_path)
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_SNAPSHOT_SET_CHANGED"
    assert exc.value.details["changed_stores"] == ["production"]
    assert exc.value.details["automatic_repair_performed"] is False


def test_manifest_rejects_relative_path_substitution(tmp_path: Path):
    production, audits, prompts, continuity, audio = registries()
    manifest = ProductionBundleManifestStore.build(
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio
    )
    manifest["stores"]["production"]["relative_path"] = "../outside.json"
    with pytest.raises(ProductError) as exc:
        ProductionBundleManifestStore.save(tmp_path / "production-bundle.json", manifest)
    # The body changed without updating the manifest hash, so integrity fails before path use.
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_MANIFEST_CHECKSUM"


def test_manifest_requires_cas_on_replace(tmp_path: Path):
    production, audits, prompts, continuity, audio = registries()
    manifest = ProductionBundleManifestStore.build(
        production=production, audits=audits, prompts=prompts, continuity=continuity, audio=audio
    )
    path = tmp_path / "production-bundle.json"
    ProductionBundleManifestStore.save(path, manifest)
    with pytest.raises(ProductError) as exc:
        ProductionBundleManifestStore.save(path, manifest)
    assert exc.value.code == "ERR_PRODUCTION_BUNDLE_MANIFEST_CAS_REQUIRED"
