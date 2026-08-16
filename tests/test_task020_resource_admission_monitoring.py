from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from ai_video_production.resource_admission_monitoring import (
    AdmissionDecision,
    ContractState,
    MetricValueState,
    OperationGateDecision,
    OperationScope,
    ResourceAdmissionDecisionReceipt,
    ResourceAdmissionPolicyRevision,
    ResourceIncidentReceipt,
    ResourceMetricFact,
    ResourceMetricKind,
    ResourceOperationGateBinding,
    ResourcePreflightObservationReceipt,
    RuntimeResourceWatermarkReceipt,
    SCHEMA_ID,
    canonical_record_digest,
    classify_runtime_watermark,
    classify_operation_gate,
    derive_incident,
    evaluate_admission,
    module_effect_surface,
    parse_resource_record,
    private_projection,
    public_projection,
    validate_policy_successor,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
ZERO = "sha256:" + "0" * 64
ONE = "sha256:" + "1" * 64
NOW = "2026-08-17T01:00:00Z"


def _with_hash(body: dict[str, object], field: str) -> dict[str, object]:
    value = copy.deepcopy(body)
    value[field] = sha256_bytes(canonical_json_bytes(body))
    return value


def _fact(
    kind: ResourceMetricKind,
    value: int | None,
    *,
    state: MetricValueState = MetricValueState.MEASURED,
    observed_at: str = NOW,
    profile_sha: str = ZERO,
) -> dict[str, object]:
    return ResourceMetricFact.create(
        metric_kind=kind,
        value_state=state,
        value_int=value,
        observed_at=observed_at,
        source_profile_ref="probe-profile:host-a:v1",
        source_profile_sha256=profile_sha,
    ).to_dict()


def _threshold(kind: ResourceMetricKind, value: int, comparison: str = "GREATER_THAN_OR_EQUAL") -> dict[str, object]:
    unit = {
        ResourceMetricKind.CPU_AVAILABLE_MILLICORES: "millicores",
        ResourceMetricKind.RAM_AVAILABLE_BYTES: "bytes",
        ResourceMetricKind.VRAM_AVAILABLE_BYTES: "bytes",
        ResourceMetricKind.DISK_AVAILABLE_BYTES: "bytes",
        ResourceMetricKind.NETWORK_REACHABLE: "boolean-int",
        ResourceMetricKind.PROCESS_INSTANCE_COUNT: "count",
        ResourceMetricKind.APP_INSTANCE_COUNT: "count",
    }[kind]
    return {
        "metric_kind": kind.value,
        "comparison": comparison,
        "threshold_value_int": value,
        "unit": unit,
        "required": True,
    }


def _policy(*thresholds: dict[str, object]) -> dict[str, object]:
    ordered = sorted(thresholds, key=lambda item: str(item["metric_kind"]))
    body: dict[str, object] = {
        "schema": SCHEMA_ID,
        "record_type": "ResourceAdmissionPolicyRevision",
        "task_owner": "TASK-020",
        "project_id": "project:demo",
        "policy_id": "resource-policy:local-generation",
        "revision": 1,
        "parent_revision_sha256": None,
        "created_at": "2026-08-17T00:00:00Z",
        "max_fact_age_seconds": 3600,
        "thresholds": ordered,
        "collector_body_persisted": False,
        "effect_authorized": False,
    }
    return _with_hash(body, "policy_revision_sha256")


def _observation(policy: dict[str, object], *facts: dict[str, object]) -> dict[str, object]:
    ordered = sorted(facts, key=lambda item: str(item["metric_kind"]))
    body: dict[str, object] = {
        "schema": SCHEMA_ID,
        "record_type": "ResourcePreflightObservationReceipt",
        "task_owner": "TASK-020",
        "project_id": "project:demo",
        "observation_receipt_id": "observation:001",
        "operation_identity": "operation:local-generation:001",
        "operation_input_sha256": ZERO,
        "target_kind": "TASK-004/COMFYUI",
        "target_ref": "runtime:comfyui:local",
        "target_revision_sha256": ONE,
        "policy_id": policy["policy_id"],
        "policy_revision_sha256": policy["policy_revision_sha256"],
        "observed_at": NOW,
        "facts": ordered,
        "collector_executed_by_module": False,
        "operation_started": False,
    }
    return _with_hash(body, "observation_receipt_sha256")


def test_schema_and_mirror_are_byte_exact_and_accept_canonical_records() -> None:
    public = ROOT / "schemas" / "resource-admission-monitoring.schema.json"
    mirror = ROOT / "src" / "ai_video_production" / "schema_resources" / "resource-admission-monitoring.schema.json"
    assert public.read_bytes() == mirror.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    policy = _policy(_threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1024))
    jsonschema.validate(policy, schema)


def test_metric_fact_distinguishes_genuine_zero_from_unknown() -> None:
    measured_zero = _fact(ResourceMetricKind.PROCESS_INSTANCE_COUNT, 0)
    assert ResourceMetricFact.from_dict(measured_zero).value_int == 0
    unknown = _fact(ResourceMetricKind.VRAM_AVAILABLE_BYTES, None, state=MetricValueState.UNKNOWN)
    assert ResourceMetricFact.from_dict(unknown).value_int is None
    forged = copy.deepcopy(unknown)
    forged["value_int"] = 0
    forged = _with_hash({key: value for key, value in forged.items() if key != "metric_fact_sha256"}, "metric_fact_sha256")
    with pytest.raises(ValueError, match="only MEASURED"):
        ResourceMetricFact.from_dict(forged)


def test_metric_fact_rejects_wrong_unit_network_non_boolean_and_tamper() -> None:
    fact = _fact(ResourceMetricKind.NETWORK_REACHABLE, 1)
    wrong_unit = copy.deepcopy(fact)
    wrong_unit["unit"] = "count"
    wrong_unit = _with_hash({key: value for key, value in wrong_unit.items() if key != "metric_fact_sha256"}, "metric_fact_sha256")
    with pytest.raises(ValueError, match="unit"):
        ResourceMetricFact.from_dict(wrong_unit)
    invalid_boolean = copy.deepcopy(fact)
    invalid_boolean["value_int"] = 2
    invalid_boolean = _with_hash(
        {key: value for key, value in invalid_boolean.items() if key != "metric_fact_sha256"},
        "metric_fact_sha256",
    )
    with pytest.raises(ValueError, match="0 or 1"):
        ResourceMetricFact.from_dict(invalid_boolean)
    tampered = copy.deepcopy(fact)
    tampered["value_int"] = 0
    with pytest.raises(ValueError, match="canonical record body"):
        ResourceMetricFact.from_dict(tampered)


def test_policy_revision_parent_and_sorted_threshold_invariants() -> None:
    policy = _policy(
        _threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1024),
        _threshold(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 1000),
    )
    ResourceAdmissionPolicyRevision.from_dict(policy)
    unsorted = copy.deepcopy(policy)
    unsorted["thresholds"] = list(reversed(unsorted["thresholds"]))
    unsorted = _with_hash({key: value for key, value in unsorted.items() if key != "policy_revision_sha256"}, "policy_revision_sha256")
    with pytest.raises(ValueError, match="sorted"):
        ResourceAdmissionPolicyRevision.from_dict(unsorted)
    later = copy.deepcopy(policy)
    later["revision"] = 2
    later["parent_revision_sha256"] = None
    later = _with_hash({key: value for key, value in later.items() if key != "policy_revision_sha256"}, "policy_revision_sha256")
    with pytest.raises(ValueError, match="SHA-256"):
        ResourceAdmissionPolicyRevision.from_dict(later)


def test_policy_successor_requires_exact_parent_revision_and_monotonic_time() -> None:
    parent = _policy(_threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1024))
    candidate = copy.deepcopy(parent)
    candidate["revision"] = 2
    candidate["parent_revision_sha256"] = parent["policy_revision_sha256"]
    candidate["created_at"] = "2026-08-17T00:01:00Z"
    candidate = _with_hash(
        {key: value for key, value in candidate.items() if key != "policy_revision_sha256"},
        "policy_revision_sha256",
    )
    assert validate_policy_successor(parent, candidate).to_dict() == candidate
    fork = copy.deepcopy(candidate)
    fork["parent_revision_sha256"] = ONE
    fork = _with_hash({key: value for key, value in fork.items() if key != "policy_revision_sha256"}, "policy_revision_sha256")
    with pytest.raises(ValueError, match="parent hash mismatch"):
        validate_policy_successor(parent, fork)


def test_admission_admitted_is_pure_and_deterministic() -> None:
    policy = _policy(
        _threshold(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 2000),
        _threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 8_000_000_000),
    )
    observation = _observation(
        policy,
        _fact(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 4000),
        _fact(ResourceMetricKind.RAM_AVAILABLE_BYTES, 16_000_000_000),
    )
    first = evaluate_admission(policy, observation, decision_id="decision:001", evaluated_at="2026-08-17T01:10:00Z")
    second = evaluate_admission(policy, observation, decision_id="decision:001", evaluated_at="2026-08-17T01:10:00Z")
    assert first.to_dict() == second.to_dict()
    assert first.to_dict()["decision"] == "ADMITTED"
    assert first.to_dict()["reason_codes"] == []
    assert first.to_dict()["reservation_started"] is False
    assert first.to_dict()["dispatch_started"] is False
    assert first.to_dict()["execution_authorized"] is False


def test_threshold_failure_denies_and_unknown_never_becomes_zero_or_pass() -> None:
    policy = _policy(_threshold(ResourceMetricKind.VRAM_AVAILABLE_BYTES, 12_000_000_000))
    denied_observation = _observation(policy, _fact(ResourceMetricKind.VRAM_AVAILABLE_BYTES, 8_000_000_000))
    denied = evaluate_admission(policy, denied_observation, decision_id="decision:denied", evaluated_at="2026-08-17T01:10:00Z")
    assert denied.to_dict()["decision"] == "DENIED"
    assert denied.to_dict()["reason_codes"] == ["VRAM_AVAILABLE_BYTES_THRESHOLD_NOT_MET"]
    unknown_observation = _observation(
        policy,
        _fact(ResourceMetricKind.VRAM_AVAILABLE_BYTES, None, state=MetricValueState.NOT_SUPPORTED),
    )
    unknown = evaluate_admission(policy, unknown_observation, decision_id="decision:unknown", evaluated_at="2026-08-17T01:10:00Z")
    assert unknown.to_dict()["decision"] == "UNKNOWN"
    assert unknown.to_dict()["reason_codes"] == ["VRAM_AVAILABLE_BYTES_NOT_SUPPORTED"]


def test_missing_stale_mixed_profile_and_mismatched_bindings_fail_closed() -> None:
    policy = _policy(
        _threshold(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 1),
        _threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1),
    )
    missing = _observation(policy, _fact(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 100))
    result = evaluate_admission(policy, missing, decision_id="decision:missing", evaluated_at="2026-08-17T01:10:00Z")
    assert result.to_dict()["decision"] == "UNKNOWN"
    assert "RAM_AVAILABLE_BYTES_MISSING" in result.to_dict()["reason_codes"]
    stale = evaluate_admission(policy, missing, decision_id="decision:stale", evaluated_at="2026-08-17T03:00:01Z")
    assert stale.to_dict()["decision"] == "UNKNOWN"
    assert "CPU_AVAILABLE_MILLICORES_STALE_OR_FUTURE" in stale.to_dict()["reason_codes"]
    mixed = _observation(
        policy,
        _fact(ResourceMetricKind.CPU_AVAILABLE_MILLICORES, 100),
        _fact(ResourceMetricKind.RAM_AVAILABLE_BYTES, 100, profile_sha=ONE),
    )
    mixed_result = evaluate_admission(policy, mixed, decision_id="decision:mixed", evaluated_at="2026-08-17T01:10:00Z")
    assert mixed_result.to_dict()["decision"] == "UNKNOWN"
    assert "MIXED_SOURCE_PROFILE" in mixed_result.to_dict()["reason_codes"]
    wrong_project = copy.deepcopy(missing)
    wrong_project["project_id"] = "project:other"
    wrong_project = _with_hash(
        {key: value for key, value in wrong_project.items() if key != "observation_receipt_sha256"},
        "observation_receipt_sha256",
    )
    with pytest.raises(ValueError, match="project mismatch"):
        evaluate_admission(policy, wrong_project, decision_id="decision:bad", evaluated_at="2026-08-17T01:10:00Z")


def test_operation_gate_requires_verified_admitted_binding_and_never_authorizes() -> None:
    unbound = classify_operation_gate(
        project_id="project:demo",
        binding_id="gate:unbound",
        operation_identity="operation:001",
        operation_scope=OperationScope.LOCAL_GENERATION,
        contract_state=ContractState.CANONICAL_REF_NOT_PROVIDED,
        decision_ref=None,
        admission_decision_sha256=None,
        admission_decision=None,
    )
    assert unbound.to_dict()["gate_decision"] == "UNKNOWN"
    ready = classify_operation_gate(
        project_id="project:demo",
        binding_id="gate:ready",
        operation_identity="operation:001",
        operation_scope=OperationScope.LOCAL_GENERATION,
        contract_state=ContractState.BOUND_VERIFIED,
        decision_ref="decision:001",
        admission_decision_sha256=ZERO,
        admission_decision=AdmissionDecision.ADMITTED,
    )
    assert ready.to_dict()["gate_decision"] == "READY_FOR_EXTERNAL_HUMAN_GATE"
    assert ready.to_dict()["execution_authorized"] is False
    forged = ready.to_dict()
    forged["execution_authorized"] = True
    forged = _with_hash(
        {key: value for key, value in forged.items() if key != "operation_gate_binding_sha256"},
        "operation_gate_binding_sha256",
    )
    with pytest.raises(ValueError, match="must remain false"):
        ResourceOperationGateBinding.from_dict(forged)


def test_watermark_and_incident_are_evidence_not_process_control() -> None:
    fact = _fact(ResourceMetricKind.APP_INSTANCE_COUNT, 2)
    watermark_body: dict[str, object] = {
        "schema": SCHEMA_ID,
        "record_type": "RuntimeResourceWatermarkReceipt",
        "task_owner": "TASK-020",
        "project_id": "project:demo",
        "watermark_receipt_id": "watermark:001",
        "operation_identity": "operation:001",
        "policy_revision_sha256": ZERO,
        "admission_decision_sha256": ONE,
        "sequence": 1,
        "window_started_at": "2026-08-17T01:00:00Z",
        "window_ended_at": "2026-08-17T01:01:00Z",
        "facts": [fact],
        "state": "BREACH",
        "reason_codes": ["APP_INSTANCE_COUNT_THRESHOLD_NOT_MET"],
        "collector_executed_by_module": False,
        "process_control_started": False,
        "app_operation_started": False,
    }
    watermark = RuntimeResourceWatermarkReceipt.from_dict(_with_hash(watermark_body, "watermark_receipt_sha256"))
    incident_body: dict[str, object] = {
        "schema": SCHEMA_ID,
        "record_type": "ResourceIncidentReceipt",
        "task_owner": "TASK-020",
        "project_id": "project:demo",
        "incident_receipt_id": "incident:001",
        "operation_identity": "operation:001",
        "watermark_receipt_sha256": watermark.to_dict()["watermark_receipt_sha256"],
        "detected_at": "2026-08-17T01:01:01Z",
        "state": "CONFIRMED",
        "incident_kind": "APP_CARDINALITY",
        "affected_metrics": ["APP_INSTANCE_COUNT"],
        "reason_codes": ["APP_INSTANCE_COUNT_THRESHOLD_NOT_MET"],
        "termination_requested": False,
        "process_kill_started": False,
        "app_stop_started": False,
    }
    incident = ResourceIncidentReceipt.from_dict(_with_hash(incident_body, "incident_receipt_sha256"))
    assert incident.to_dict()["process_kill_started"] is False
    forged = incident.to_dict()
    forged["process_kill_started"] = True
    forged = _with_hash(
        {key: value for key, value in forged.items() if key != "incident_receipt_sha256"},
        "incident_receipt_sha256",
    )
    with pytest.raises(ValueError, match="must remain false"):
        ResourceIncidentReceipt.from_dict(forged)


def test_runtime_classifier_and_incident_derivation_remain_non_effecting() -> None:
    policy = _policy(_threshold(ResourceMetricKind.APP_INSTANCE_COUNT, 1, "LESS_THAN_OR_EQUAL"))
    observation = _observation(policy, _fact(ResourceMetricKind.APP_INSTANCE_COUNT, 1))
    admission = evaluate_admission(
        policy,
        observation,
        decision_id="decision:runtime",
        evaluated_at="2026-08-17T01:10:00Z",
    ).to_dict()
    runtime_fact = _fact(
        ResourceMetricKind.APP_INSTANCE_COUNT,
        2,
        observed_at="2026-08-17T01:20:00Z",
    )
    watermark = classify_runtime_watermark(
        policy,
        admission,
        [runtime_fact],
        watermark_receipt_id="watermark:derived",
        sequence=1,
        window_started_at="2026-08-17T01:19:00Z",
        window_ended_at="2026-08-17T01:20:01Z",
    )
    assert watermark.to_dict()["state"] == "BREACH"
    assert watermark.to_dict()["process_control_started"] is False
    incident = derive_incident(
        watermark.to_dict(),
        incident_receipt_id="incident:derived",
        detected_at="2026-08-17T01:20:02Z",
    )
    assert incident.to_dict()["incident_kind"] == "APP_CARDINALITY"
    assert incident.to_dict()["state"] == "CONFIRMED"
    assert incident.to_dict()["termination_requested"] is False


def test_parse_digest_and_projection_are_body_free() -> None:
    policy = _policy(_threshold(ResourceMetricKind.DISK_AVAILABLE_BYTES, 1000))
    observation = _observation(policy, _fact(ResourceMetricKind.DISK_AVAILABLE_BYTES, 2000))
    parsed = parse_resource_record(observation)
    assert isinstance(parsed, ResourcePreflightObservationReceipt)
    assert canonical_record_digest(observation) == observation["observation_receipt_sha256"]
    assert private_projection(observation)["target_ref"] == "runtime:comfyui:local"
    public = public_projection(observation)
    assert public["projection"] == "PUBLIC_BODY_FREE"
    assert "target_ref" not in public
    assert "source_profile_ref" not in public["facts"][0]
    assert "source_profile_sha256" not in public["facts"][0]
    assert "value_int" not in public["facts"][0]
    assert "operation_input_sha256" not in public
    assert "credential" not in json.dumps(public).casefold()


def test_unknown_type_extra_property_and_absolute_path_are_rejected() -> None:
    with pytest.raises(ValueError, match="record_type"):
        parse_resource_record({"record_type": "FilesystemResourceCollector"})
    policy = _policy(_threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1))
    extra = copy.deepcopy(policy)
    extra["raw_probe_body"] = "forbidden"
    with pytest.raises(ValueError, match="incomplete or unknown"):
        ResourceAdmissionPolicyRevision.from_dict(extra)
    observation = _observation(policy, _fact(ResourceMetricKind.RAM_AVAILABLE_BYTES, 2))
    path = copy.deepcopy(observation)
    path["target_ref"] = "C:\\private\\host"
    path = _with_hash(
        {key: value for key, value in path.items() if key != "observation_receipt_sha256"},
        "observation_receipt_sha256",
    )
    with pytest.raises(ValueError, match="invalid|body-free"):
        ResourcePreflightObservationReceipt.from_dict(path)


def test_schema_rejects_effect_flags_and_module_has_no_effect_surface() -> None:
    schema = json.loads((ROOT / "schemas" / "resource-admission-monitoring.schema.json").read_text(encoding="utf-8"))
    policy = _policy(_threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1))
    policy["effect_authorized"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(policy, schema)
    assert set(module_effect_surface().values()) == {False}
    source = (ROOT / "src" / "ai_video_production" / "resource_admission_monitoring.py").read_text(encoding="utf-8")
    for forbidden in ("import os", "import subprocess", "import socket", "import requests", "Path(", "urlopen("):
        assert forbidden not in source


def test_decision_receipt_rejects_admitted_reasons_and_manual_hash_tamper() -> None:
    policy = _policy(_threshold(ResourceMetricKind.RAM_AVAILABLE_BYTES, 1))
    observation = _observation(policy, _fact(ResourceMetricKind.RAM_AVAILABLE_BYTES, 2))
    decision = evaluate_admission(policy, observation, decision_id="decision:001", evaluated_at="2026-08-17T01:10:00Z").to_dict()
    reasoned = copy.deepcopy(decision)
    reasoned["reason_codes"] = ["FORGED_REASON"]
    reasoned = _with_hash(
        {key: value for key, value in reasoned.items() if key != "admission_decision_sha256"},
        "admission_decision_sha256",
    )
    with pytest.raises(ValueError, match="ADMITTED"):
        ResourceAdmissionDecisionReceipt.from_dict(reasoned)
    tampered = copy.deepcopy(decision)
    tampered["operation_identity"] = "operation:other"
    with pytest.raises(ValueError, match="canonical record body"):
        ResourceAdmissionDecisionReceipt.from_dict(tampered)
