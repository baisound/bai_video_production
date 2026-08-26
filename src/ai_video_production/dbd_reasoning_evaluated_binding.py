"""TASK-054 R6D bridge from sealed quarantine Evidence to EVALUATED only."""

from __future__ import annotations

from .dbd_reasoning_contracts import TunedModelBinding, TunedModelBindingStatus
from .dbd_reasoning_quarantined_artifact import (
    QuarantinedArtifactManifest, admit_quarantined_artifact_manifest,
)
from .dbd_tuned_model_registry import (
    BindingLifecycleTransition, DbDTunedModelRegistry, DbDTunedModelRegistryRecord,
    admit_tuned_model_registry_record,
)


def propose_evaluated_binding(
    *, draft_record: DbDTunedModelRegistryRecord,
    artifact_manifest: QuarantinedArtifactManifest,
    recorded_at: str,
) -> DbDTunedModelRegistryRecord:
    draft = admit_tuned_model_registry_record(draft_record.to_dict())
    manifest = admit_quarantined_artifact_manifest(artifact_manifest.to_dict())
    if draft.binding.status is not TunedModelBindingStatus.DRAFT:
        raise ValueError("R6D requires the exact DRAFT registry root")
    expected_coordinates = (
        manifest.base_model_ref, manifest.base_model_sha256,
        manifest.adapter_ref, manifest.adapter_sha256,
    )
    actual_coordinates = (
        draft.binding.base_model_ref, draft.binding.base_model_sha256,
        draft.binding.adapter_ref, draft.binding.adapter_sha256,
    )
    if actual_coordinates != expected_coordinates:
        raise ValueError("sealed artifact crosses DRAFT model coordinates")
    binding = TunedModelBinding(
        binding_id=draft.binding.binding_id,
        revision=draft.binding.revision + 1,
        status=TunedModelBindingStatus.EVALUATED,
        base_model_ref=manifest.base_model_ref,
        base_model_sha256=manifest.base_model_sha256,
        adapter_ref=manifest.adapter_ref,
        adapter_sha256=manifest.adapter_sha256,
        training_dataset_sha256=manifest.training_dataset_sha256,
        training_recipe_sha256=manifest.training_recipe_sha256,
        evaluation_report_sha256=manifest.evaluation_report_sha256,
        rights_manifest_sha256=manifest.rights_manifest_sha256,
        supported_locales=draft.binding.supported_locales,
        approved_at=None,
        approved_by_ref=None,
    )
    evaluated = DbDTunedModelRegistryRecord(
        binding=binding,
        transition=BindingLifecycleTransition.EVALUATE,
        previous_record_sha256=draft.registry_record_sha256,
        decision_evidence_ref=(
            "evaluation://sha256/"
            + manifest.evaluation_report_sha256.removeprefix("sha256:")
        ),
        decision_evidence_sha256=manifest.evaluation_report_sha256,
        recorded_at=recorded_at,
    )
    DbDTunedModelRegistry((draft, evaluated))
    return evaluated


__all__ = ["propose_evaluated_binding"]
