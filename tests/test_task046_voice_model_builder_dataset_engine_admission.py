from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.voice_model_builder_dataset_engine_admission import (
    EngineRecipeAdmissionBinding,
    SyntheticDatasetPreparationManifest,
    TrainingExecutionProposal,
    add_record_digest,
    assert_no_effect_surface,
    compile_dataset_manifest,
    compile_training_proposal,
    public_projection,
    validate_record,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-dataset-engine-admission.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-dataset-engine-admission.schema.json"
NOW = "2026-08-17T00:00:00Z"
H = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64


def item(index: int, *, source: str = H2, start: int | None = None, end: int | None = None) -> dict:
    start = index * 1000 if start is None else start
    end = start + 1000 if end is None else end
    return {
        "order_index": index,
        "item_id": f"item:{index}",
        "wav_inspection_receipt_sha256": "sha256:" + str(index + 5) * 64,
        "source_sha256": source,
        "start_frame": start,
        "end_frame": end,
        "approved_label_sha256": H3,
    }


def manifest(items: list[dict] | None = None) -> dict:
    return compile_dataset_manifest(
        manifest_id="manifest:synthetic:1", revision=1, parent_manifest_sha256=None,
        workflow_sha256=H, ordered_items=items or [item(0), item(1)], created_at=NOW,
    ).to_dict()


def engine(*, bound: bool = True, legal: bool = False, mode: str = "ADAPTER_OR_LORA") -> dict:
    state = "BOUND_VERIFIED" if bound else "CANONICAL_REF_NOT_PROVIDED"
    fact = "PASS" if bound else "UNKNOWN"
    values = {
        "engine_id": "engine:synthetic" if bound else None,
        "engine_revision": "revision:1" if bound else None,
        "package_sha256": H if bound else None,
        "model_id": "model:synthetic" if bound else None,
        "model_revision": "revision:1" if bound else None,
        "weight_sha256": H2 if bound else None,
        "runtime_sha256": H3 if bound else None,
        "recipe_revision": "recipe:1" if bound else None,
        "recipe_sha256": H4 if bound else None,
        "license_evidence_sha256": H if bound else None,
        "evaluated_at": NOW if bound else None,
    }
    body = {
        "record_type": "EngineRecipeAdmissionBinding",
        "binding_id": "engine-binding:1",
        "contract_state": state,
        **values,
        "training_mode": mode,
        "official_recipe_state": fact,
        "representative_step_state": fact,
        "target_resource_state": fact,
        "checkpoint_compatibility_state": fact,
        "license_state": "LEGAL_REVIEW_REQUIRED" if legal else ("APPROVED_FOR_SYNTHETIC_TECHNICAL_TEST" if bound else "UNKNOWN"),
    }
    return add_record_digest(body, "binding_sha256")


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_manifest_is_canonical_schema_valid_and_body_free() -> None:
    record = manifest()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(record)
    assert SyntheticDatasetPreparationManifest(record).to_dict() == record
    assert record["selected_unique_frames"] == 2000
    assert record["dataset_adoption_started"] is False
    assert record["training_input_snapshot_issued"] is False


def test_manifest_rejects_overlap_duplicate_and_noncontiguous_order() -> None:
    with pytest.raises(ValueError, match="overlapping"):
        manifest([item(0, start=0, end=1000), item(1, start=500, end=1200)])
    duplicate = [item(0), item(1, source=H3)]
    duplicate[1]["item_id"] = duplicate[0]["item_id"]
    with pytest.raises(ValueError, match="item_id"):
        manifest(duplicate)
    unordered = [item(0), item(1)]
    unordered[1]["order_index"] = 3
    with pytest.raises(ValueError, match="contiguous"):
        manifest(unordered)


def test_manifest_revision_lineage_and_effect_flags_fail_closed() -> None:
    record = manifest()
    record["revision"] = 2
    record = add_record_digest(record, "manifest_sha256")
    with pytest.raises(ValueError, match="lineage"):
        validate_record(record)
    for field in ("owner_audio_used", "dataset_adoption_started", "training_input_snapshot_issued"):
        forged = manifest()
        forged[field] = True
        forged = add_record_digest(forged, "manifest_sha256")
        with pytest.raises(ValueError):
            validate_record(forged)


@pytest.mark.parametrize("mode", ["FULL_FINE_TUNE", "PARAMETER_EFFICIENT_FINE_TUNE", "ADAPTER_OR_LORA"])
def test_engine_admission_is_mode_specific_and_schema_valid(mode: str) -> None:
    record = engine(mode=mode)
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(record)
    assert EngineRecipeAdmissionBinding(record).to_dict() == record
    assert record["training_mode"] == mode


def test_qwen_like_legal_review_or_short_probe_cannot_be_bound() -> None:
    with pytest.raises(ValueError, match="approved synthetic license"):
        EngineRecipeAdmissionBinding(engine(legal=True))
    record = engine()
    record["representative_step_state"] = "UNKNOWN"
    record = add_record_digest(record, "binding_sha256")
    with pytest.raises(ValueError, match="all exact PASS"):
        EngineRecipeAdmissionBinding(record)


def test_unresolved_engine_cannot_invent_identifiers_or_hashes() -> None:
    assert EngineRecipeAdmissionBinding(engine(bound=False))
    record = engine(bound=False)
    record["engine_id"] = "engine:guessed"
    record = add_record_digest(record, "binding_sha256")
    with pytest.raises(ValueError, match="must not invent"):
        validate_record(record)


def test_training_proposal_ready_still_requires_owner_gate_and_never_dispatches() -> None:
    proposal = compile_training_proposal(
        proposal_id="proposal:1", dataset_manifest=manifest(), engine_admission=engine(),
        output_destination_binding_sha256=H4, durable_job_binding_state="BOUND_VERIFIED",
        rights_consent_state="PASS", created_at=NOW,
    ).to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(proposal)
    assert TrainingExecutionProposal(proposal).to_dict() == proposal
    assert proposal["proposal_state"] == "READY_FOR_OWNER_HUMAN_GATE"
    assert proposal["owner_human_gate_required"] is True
    assert proposal["dispatch_started"] is False


@pytest.mark.parametrize(
    ("engine_record", "job", "rights", "reason"),
    [
        (engine(bound=False), "BOUND_VERIFIED", "PASS", "ENGINE_RECIPE_NOT_BOUND"),
        (engine(), "UNKNOWN", "PASS", "DURABLE_JOB_NOT_BOUND"),
        (engine(), "BOUND_VERIFIED", "UNKNOWN", "RIGHTS_CONSENT_NOT_PASS"),
    ],
)
def test_training_proposal_blocks_each_missing_prerequisite(engine_record: dict, job: str, rights: str, reason: str) -> None:
    proposal = compile_training_proposal(
        proposal_id="proposal:blocked", dataset_manifest=manifest(), engine_admission=engine_record,
        output_destination_binding_sha256=H4, durable_job_binding_state=job,
        rights_consent_state=rights, created_at=NOW,
    ).to_dict()
    assert proposal["proposal_state"] == "BLOCKED"
    assert reason in proposal["reason_codes"]
    assert proposal["training_started"] is False


def test_tamper_unknown_fields_and_forged_dispatch_fail_closed() -> None:
    proposal = compile_training_proposal(
        proposal_id="proposal:1", dataset_manifest=manifest(), engine_admission=engine(),
        output_destination_binding_sha256=H4, durable_job_binding_state="BOUND_VERIFIED",
        rights_consent_state="PASS", created_at=NOW,
    ).to_dict()
    proposal["dispatch_started"] = True
    proposal = add_record_digest(proposal, "proposal_sha256")
    with pytest.raises(ValueError, match="must remain false"):
        validate_record(proposal)
    extra = manifest()
    extra["raw_audio_path"] = "forbidden.wav"
    with pytest.raises(ValueError, match="fields"):
        validate_record(extra)
    tampered = manifest()
    tampered["selected_unique_frames"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        validate_record(tampered)


def test_public_projection_hides_hashes_items_and_engine_identity() -> None:
    for record in (manifest(), engine(), compile_training_proposal(
        proposal_id="proposal:1", dataset_manifest=manifest(), engine_admission=engine(),
        output_destination_binding_sha256=H4, durable_job_binding_state="BOUND_VERIFIED",
        rights_consent_state="PASS", created_at=NOW,
    ).to_dict()):
        encoded = json.dumps(public_projection(record), sort_keys=True)
        assert "sha256" not in encoded
        assert "engine_id" not in encoded
        assert "ordered_items" not in encoded


def test_no_effect_surface() -> None:
    assert_no_effect_surface()

