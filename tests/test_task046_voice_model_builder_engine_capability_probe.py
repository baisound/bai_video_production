from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.voice_model_builder_engine_capability_probe import (
    EngineAdmissionEvidenceProjection,
    EngineCapabilityProbePlan,
    EngineCapabilityProbeReceipt,
    add_record_digest,
    assert_no_effect_surface,
    compile_evidence_projection,
    compile_probe_plan,
    public_projection,
    validate_receipt_against_plan,
    validate_record,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-engine-capability-probe.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-engine-capability-probe.schema.json"
NOW = "2026-08-17T00:00:00Z"
H = ["sha256:" + str(index) * 64 for index in range(1, 9)]
PHASES = [
    "PACKAGE_VERIFY", "MODEL_LOAD", "REPRESENTATIVE_STEP",
    "CHECKPOINT_ROUNDTRIP", "OOM_SAFE_FAILURE_RECOVERY", "THERMAL_DURATION",
]


def plan(*, mode: str = "ADAPTER_OR_LORA", phases: list[str] | None = None) -> dict:
    return compile_probe_plan(
        plan_id="probe-plan:synthetic:1", revision=1, parent_plan_sha256=None,
        engine_id="engine:synthetic", engine_revision="engine-revision:1", package_sha256=H[0],
        model_id="model:synthetic", model_revision="model-revision:1", weight_manifest_sha256=H[1],
        runtime_sha256=H[2], recipe_revision="recipe:1", recipe_sha256=H[3], training_mode=mode,
        probe_profile_revision="probe-profile:1", probe_profile_sha256=H[4],
        target_resource_profile_sha256=H[5], requested_phases=phases or PHASES, created_at=NOW,
    ).to_dict()


def receipt(*, states: dict[str, str] | None = None, phases: list[str] | None = None) -> dict:
    phases = phases or PHASES
    states = states or {}
    phase_results = [
        {"order_index": index, "phase": phase, "state": states.get(phase, "PASS"), "evidence_sha256": H[(index + 1) % len(H)]}
        for index, phase in enumerate(phases)
    ]
    values = [item["state"] for item in phase_results]
    probe_state = "UNKNOWN" if "UNKNOWN" in values else ("FAILED_KNOWN" if any(value in {"FAIL", "NOT_SUPPORTED"} for value in values) else "COMPLETED")
    body = {
        "record_type": "EngineCapabilityProbeReceipt", "receipt_id": "probe-receipt:1",
        "plan_sha256": plan(phases=phases)["plan_sha256"], "training_mode": "ADAPTER_OR_LORA",
        "requested_phases": phases, "phase_results": phase_results, "probe_state": probe_state,
        "peak_vram_bytes": 8_000_000_000, "peak_ram_bytes": 16_000_000_000,
        "optimizer_state_bytes": 2_000_000_000, "checkpoint_bytes": 3_000_000_000,
        "free_disk_floor_bytes": 250_000_000_000, "duration_milliseconds": 120_000,
        "max_temperature_millidegrees_c": 72_000, "measurement_profile_sha256": H[7],
        "process_reconciliation_state": "PASS", "synthetic_input_only": True,
        "owner_audio_used": False, "probe_execution_performed_by_module": False,
        "training_run_dispatched": False, "model_candidate_registered": False,
        "observed_at": NOW,
    }
    return add_record_digest(body, "receipt_sha256")


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


@pytest.mark.parametrize("mode", ["FULL_FINE_TUNE", "PARAMETER_EFFICIENT_FINE_TUNE", "ADAPTER_OR_LORA"])
def test_plan_is_mode_specific_canonical_and_effect_free(mode: str) -> None:
    record = plan(mode=mode)
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(record)
    assert EngineCapabilityProbePlan(record).to_dict() == record
    assert record["model_load_started"] is False
    assert record["training_step_started"] is False


def test_plan_rejects_bad_order_duplicates_lineage_and_owner_audio() -> None:
    with pytest.raises(ValueError, match="canonical order"):
        plan(phases=["MODEL_LOAD", "PACKAGE_VERIFY"])
    with pytest.raises(ValueError, match="unique"):
        plan(phases=["PACKAGE_VERIFY", "PACKAGE_VERIFY"])
    forged = plan()
    forged["revision"] = 2
    forged = add_record_digest(forged, "plan_sha256")
    with pytest.raises(ValueError, match="lineage"):
        validate_record(forged)
    forged = plan()
    forged["owner_audio_used"] = True
    forged = add_record_digest(forged, "plan_sha256")
    with pytest.raises(ValueError, match="owner_audio_used"):
        validate_record(forged)


def test_complete_receipt_is_schema_valid_and_preserves_integer_measurements() -> None:
    record = receipt()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(record)
    assert EngineCapabilityProbeReceipt(record).to_dict() == record
    assert record["probe_state"] == "COMPLETED"
    assert record["peak_vram_bytes"] == 8_000_000_000
    assert record["training_run_dispatched"] is False
    assert validate_receipt_against_plan(plan(), record) == record


def test_receipt_must_match_exact_plan_mode_and_phase_set() -> None:
    record = receipt()
    wrong = plan(mode="FULL_FINE_TUNE")
    with pytest.raises(ValueError, match="plan_sha256"):
        validate_receipt_against_plan(wrong, record)
    forged = copy.deepcopy(record)
    forged["training_mode"] = "FULL_FINE_TUNE"
    forged = add_record_digest(forged, "receipt_sha256")
    with pytest.raises(ValueError, match="training_mode"):
        validate_receipt_against_plan(plan(), forged)


def test_unknown_and_known_failure_are_not_converted_to_pass() -> None:
    unknown = receipt(states={"REPRESENTATIVE_STEP": "UNKNOWN"})
    assert EngineCapabilityProbeReceipt(unknown).to_dict()["probe_state"] == "UNKNOWN"
    failed = receipt(states={"REPRESENTATIVE_STEP": "FAIL"})
    assert EngineCapabilityProbeReceipt(failed).to_dict()["probe_state"] == "FAILED_KNOWN"
    forged = copy.deepcopy(unknown)
    forged["probe_state"] = "COMPLETED"
    forged = add_record_digest(forged, "receipt_sha256")
    with pytest.raises(ValueError, match="probe_state"):
        validate_record(forged)


def test_unknown_process_reconciliation_blocks_probe_and_projection() -> None:
    record = receipt()
    record["process_reconciliation_state"] = "UNKNOWN"
    record["probe_state"] = "UNKNOWN"
    record = add_record_digest(record, "receipt_sha256")
    assert EngineCapabilityProbeReceipt(record).to_dict()["probe_state"] == "UNKNOWN"
    projection = compile_evidence_projection(
        projection_id="projection:orphan", receipt=record, target_resource_state="PASS", created_at=NOW,
    ).to_dict()
    assert projection["process_reconciliation_state"] == "UNKNOWN"
    assert projection["evidence_state"] == "UNKNOWN"


def test_representative_step_checkpoint_and_thermal_pass_require_measurements() -> None:
    for field, match in (
        ("peak_vram_bytes", "representative step"),
        ("checkpoint_bytes", "checkpoint PASS"),
        ("max_temperature_millidegrees_c", "thermal duration"),
    ):
        record = receipt()
        record[field] = None
        record = add_record_digest(record, "receipt_sha256")
        with pytest.raises(ValueError, match=match):
            validate_record(record)


def test_projection_requires_every_training_phase_and_target_resource_pass() -> None:
    projection = compile_evidence_projection(
        projection_id="projection:1", receipt=receipt(), target_resource_state="PASS", created_at=NOW,
    ).to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(projection)
    assert EngineAdmissionEvidenceProjection(projection).to_dict() == projection
    assert projection["evidence_state"] == "PASS"
    assert projection["load_only_proves_training"] is False
    assert projection["engine_admission_issued"] is False


def test_load_only_qwen_like_receipt_remains_unknown_for_training() -> None:
    phases = ["PACKAGE_VERIFY", "MODEL_LOAD"]
    projection = compile_evidence_projection(
        projection_id="projection:qwen-load-only", receipt=receipt(phases=phases),
        target_resource_state="UNKNOWN", created_at=NOW,
    ).to_dict()
    assert projection["model_load_state"] == "PASS"
    assert projection["representative_step_state"] == "NOT_APPLICABLE"
    assert projection["evidence_state"] == "UNKNOWN"


@pytest.mark.parametrize("field", ["target_resource_state", "checkpoint_compatibility_state", "recovery_state", "thermal_duration_state"])
def test_projection_unknown_fact_cannot_be_forged_to_pass(field: str) -> None:
    projection = compile_evidence_projection(
        projection_id="projection:unknown", receipt=receipt(states={"OOM_SAFE_FAILURE_RECOVERY": "UNKNOWN"}),
        target_resource_state="PASS", created_at=NOW,
    ).to_dict()
    projection[field] = "UNKNOWN"
    projection["evidence_state"] = "PASS"
    projection = add_record_digest(projection, "projection_sha256")
    with pytest.raises(ValueError, match="evidence_state"):
        validate_record(projection)


def test_tamper_unknown_fields_and_effect_flags_fail_closed() -> None:
    record = receipt()
    record["training_run_dispatched"] = True
    record = add_record_digest(record, "receipt_sha256")
    with pytest.raises(ValueError, match="training_run_dispatched"):
        validate_record(record)
    extra = plan()
    extra["runtime_path"] = "private/path"
    with pytest.raises(ValueError, match="fields"):
        validate_record(extra)
    tampered = receipt()
    tampered["peak_vram_bytes"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        validate_record(tampered)


def test_public_projection_hides_engine_model_hashes_and_measurements() -> None:
    records = [
        plan(), receipt(), compile_evidence_projection(
            projection_id="projection:1", receipt=receipt(), target_resource_state="PASS", created_at=NOW,
        ).to_dict(),
    ]
    for record in records:
        encoded = json.dumps(public_projection(record), sort_keys=True)
        assert "sha256" not in encoded
        assert "engine_id" not in encoded
        assert "model_id" not in encoded
        assert "peak_vram" not in encoded


def test_no_effect_surface() -> None:
    assert_no_effect_surface()
