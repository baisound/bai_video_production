from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.dbd_reasoning_contracts import TunedModelBinding, TunedModelBindingStatus
from ai_video_production.dbd_reasoning_evaluated_binding import propose_evaluated_binding
from ai_video_production.dbd_reasoning_quarantined_artifact import (
    ArtifactFileEvidence, ArtifactFileRole, QuarantinedArtifactManifest,
    artifact_role_set_sha256,
)
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition, DbDTunedModelRegistry, DbDTunedModelRegistryRecord,
)
from ai_video_production.errors import ProductError


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
QUARANTINE = "model-quarantine://task054/01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _manifest(**changes: object) -> QuarantinedArtifactManifest:
    files = (ArtifactFileEvidence("adapter/model.bin", ArtifactFileRole.ADAPTER, 100, SHA_B),)
    values: dict[str, object] = {
        "artifact_manifest_id": "ART-01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "quarantine_ref": QUARANTINE,
        "base_model_ref": "model://registry/qwen-base",
        "base_model_sha256": SHA_A,
        "adapter_ref": "model-adapter://registry/task054/dbd-ja",
        "adapter_sha256": artifact_role_set_sha256(files, ArtifactFileRole.ADAPTER),
        "files": files,
        "total_bytes": 100,
        "training_dataset_sha256": SHA_B,
        "training_recipe_sha256": SHA_C,
        "evaluation_report_sha256": SHA_D,
        "rights_manifest_sha256": SHA_A,
        "test_sample_set_sha256": SHA_B,
        "tuned_binding_sha256": SHA_C,
        "sealed_at": "2026-08-25T03:00:00Z",
    }
    values.update(changes)
    return QuarantinedArtifactManifest(**values)


def _draft(manifest: QuarantinedArtifactManifest, **changes: object) -> DbDTunedModelRegistryRecord:
    values: dict[str, object] = {
        "binding_id": "dbd-ja-r6d",
        "revision": 1,
        "status": TunedModelBindingStatus.DRAFT,
        "base_model_ref": manifest.base_model_ref,
        "base_model_sha256": manifest.base_model_sha256,
        "adapter_ref": manifest.adapter_ref,
        "adapter_sha256": manifest.adapter_sha256,
        "training_dataset_sha256": None,
        "training_recipe_sha256": None,
        "evaluation_report_sha256": None,
        "rights_manifest_sha256": None,
        "supported_locales": ("ja-JP",),
        "approved_at": None,
        "approved_by_ref": None,
    }
    values.update(changes)
    binding = TunedModelBinding(**values)
    return DbDTunedModelRegistryRecord(
        binding=binding, transition=BindingLifecycleTransition.REGISTER,
        previous_record_sha256=None,
        decision_evidence_ref="registry-intake://sha256/" + "e" * 64,
        decision_evidence_sha256="sha256:" + "e" * 64,
        recorded_at="2026-08-25T03:01:00Z",
    )


def test_sealed_manifest_proposes_evaluated_only() -> None:
    manifest = _manifest()
    draft = _draft(manifest)
    evaluated = propose_evaluated_binding(
        draft_record=draft, artifact_manifest=manifest,
        recorded_at="2026-08-25T03:02:00Z",
    )
    assert evaluated.binding.status is TunedModelBindingStatus.EVALUATED
    assert evaluated.transition is BindingLifecycleTransition.EVALUATE
    assert evaluated.binding.approved_at is None
    assert evaluated.binding.approved_by_ref is None
    assert evaluated.binding.evaluation_report_sha256 == manifest.evaluation_report_sha256
    registry = DbDTunedModelRegistry((draft, evaluated))
    with pytest.raises(ProductError):
        registry.resolve(locale="ja-JP")


def test_artifact_crossing_draft_coordinates_fails_closed() -> None:
    manifest = _manifest()
    draft = _draft(manifest, base_model_sha256=SHA_C)
    with pytest.raises(ValueError, match="crosses DRAFT"):
        propose_evaluated_binding(
            draft_record=draft, artifact_manifest=manifest,
            recorded_at="2026-08-25T03:02:00Z",
        )


def test_non_draft_input_is_rejected() -> None:
    manifest = _manifest()
    draft = _draft(manifest)
    evaluated = propose_evaluated_binding(
        draft_record=draft, artifact_manifest=manifest,
        recorded_at="2026-08-25T03:02:00Z",
    )
    with pytest.raises(ValueError, match="DRAFT"):
        propose_evaluated_binding(
            draft_record=evaluated, artifact_manifest=manifest,
            recorded_at="2026-08-25T03:03:00Z",
        )


def test_manifest_approval_forge_is_rejected_before_bridge() -> None:
    with pytest.raises(ValueError, match="cannot approve"):
        replace(_manifest(), state="APPROVED")
