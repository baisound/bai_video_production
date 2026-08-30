from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.human_edit_learning import (
    EvidenceAdmissionState,
    HardGateState,
    HumanActionEvidence,
    HumanDisposition,
    MetricEvaluation,
    OwnerDecisionState,
    OwnerLearningPolicy,
    compile_montage_human_action_evidence,
    compile_owner_decision_candidate,
    verify_human_action_evidence_hash,
    verify_owner_decision_candidate_hash,
)
from ai_video_production.multimodal_scoring import EvidenceValidity
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
METRIC_IDS = (
    "human_acceptance",
    "qa_compliance",
    "quality_improvement",
    "rework_reduction",
    "sample_confidence",
    "time_reduction",
)


def evidence(
    evidence_id: str = "human-action.001",
    *,
    condition: str = "style:dbd-aggressive",
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
    disposition: HumanDisposition = HumanDisposition.MODIFIED,
    do_not_learn: bool = False,
    safety: HardGateState = HardGateState.PASS,
    rights: HardGateState = HardGateState.PASS,
) -> HumanActionEvidence:
    return HumanActionEvidence(
        evidence_id=evidence_id,
        owner_scope_sha256=SHA_A,
        project_scope_sha256=SHA_B,
        producer_task_id="TASK-055",
        source_record_sha256=(
            "sha256:" + f"{int(evidence_id[-1]):064x}"
            if evidence_id[-1].isdigit()
            else SHA_C
        ),
        action_type="montage.timing",
        condition_keys=("event:PALLET_DROP", condition),
        before_snapshot_sha256=SHA_C,
        proposed_snapshot_sha256=SHA_D,
        final_snapshot_sha256=None if disposition is HumanDisposition.REJECTED else SHA_A,
        disposition=disposition,
        validity=validity,
        do_not_learn=do_not_learn,
        immediate_undo=disposition is HumanDisposition.UNDONE,
        later_revision=disposition is HumanDisposition.REVISED_AFTER_ACCEPTANCE,
        safety_state=safety,
        rights_state=rights,
        observed_at_epoch_ms=1_700_000_000_000,
        work_duration_ms=15_000,
    )


def metrics(
    *,
    observed: int = 520,
    sample_count: int = 10,
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
    overrides: dict[str, int] | None = None,
) -> tuple[MetricEvaluation, ...]:
    overrides = overrides or {}
    return tuple(
        MetricEvaluation(metric_id, 500, overrides.get(metric_id, observed), sample_count, validity)
        for metric_id in METRIC_IDS
    )


def policy(**changes) -> OwnerLearningPolicy:
    values = {
        "policy_id": "owner-learning.conservative",
        "policy_version": "1.0.0",
        "minimum_evidence_records": 2,
        "minimum_samples_per_axis": 10,
        "minimum_weighted_benefit_milli": 10,
        "maximum_axis_regression_milli": 0,
    }
    values.update(changes)
    return OwnerLearningPolicy(**values)


def candidate(
    rows: tuple[HumanActionEvidence, ...] | None = None,
    metric_rows: tuple[MetricEvaluation, ...] | None = None,
    chosen_policy: OwnerLearningPolicy | None = None,
):
    return compile_owner_decision_candidate(
        "owner-decision.001",
        SHA_A,
        "hypothesis.montage-timing-improves-quality",
        rows or (evidence("human-action.001"), evidence("human-action.002")),
        metric_rows or metrics(),
        chosen_policy or policy(),
    )


def _sign(body: dict, field: str) -> dict:
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _resign(value: dict, field: str) -> dict:
    body = deepcopy(value)
    body.pop(field)
    return _sign(body, field)


def montage_documents() -> tuple[dict, dict, dict]:
    proposal = _sign(
        {
            "schema_version": "1.0.0",
            "record_kind": "MONTAGE_PROPOSAL_BUNDLE",
            "project_id": "proj-test",
            "production_job_id": "JOB-01J00000000000000000000000",
            "timeline_rate": {"numerator": 60, "denominator": 1},
            "music_asset_id": "ASSET-01J00000000000000000000002",
            "style_profile_id": "dbd-aggressive",
            "preset_manifest_sha256": SHA_A,
            "external_generator": {
                "generator_id": "davinci-beat-sync-montage-director",
                "version": "0.6.0",
                "sha256": SHA_B,
            },
            "generated_at": "2026-08-24T00:00:00Z",
            "music_anchors": [
                {
                    "anchor_id": "anchor-001",
                    "timeline_frame": 600,
                    "bar_index": 4,
                    "beat_index": 1,
                    "kind": "DROP",
                    "strength_milli": 980,
                }
            ],
            "placements": [
                {
                    "placement_id": "placement-001",
                    "source_asset_id": "ASSET-01J00000000000000000000001",
                    "source_rate": {"numerator": 60, "denominator": 1},
                    "source_start_frame": 120,
                    "source_end_frame_exclusive": 180,
                    "source_anchor_frame": 149,
                    "event_ref": "event-001",
                    "event_type": "PALLET_DROP",
                    "target_music_anchor_id": "anchor-001",
                    "target_timeline_frame": 600,
                    "highlight_score_milli": 900,
                    "confidence_milli": 920,
                    "reason_codes": ["BEAT_EVENT_ALIGNMENT", "PALLET_DROP"],
                }
            ],
            "compositions": [
                {
                    "composition_id": "composition-001",
                    "placement_id": "placement-001",
                    "operations": [
                        {
                            "operation_id": "operation-001",
                            "preset_id": "preset.zoom.punch",
                            "family": "zoom",
                            "offset_frames": 0,
                            "intensity_milli": 800,
                        }
                    ],
                    "complexity_score": 300,
                    "visibility_score": 850,
                }
            ],
            "external_input_untrusted": True,
            "human_review_required": True,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "automatic_learning_promotion_authorized": False,
        },
        "proposal_sha256",
    )
    plan = _sign(
        {
            "plan_version": "1.0.0",
            "task_owner": "TASK-055",
            "source_proposal_sha256": proposal["proposal_sha256"],
            "approved_by": "owner-local",
            "placements": [
                {
                    "placement": deepcopy(proposal["placements"][0]),
                    "proposed_target_timeline_frame": 600,
                    "final_target_timeline_frame": 602,
                    "delta_frames": 2,
                    "accepted_composition_ids": ["composition-001"],
                }
            ],
            "rejected": [],
            "review_do_not_learn_placement_ids": [],
            "approval_state": "APPROVED",
            "ready_for_timeline_projection": True,
            "automatic_timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        },
        "plan_sha256",
    )
    human = _sign(
        {
            "evidence_version": "1.0.0",
            "task_owner": "TASK-055",
            "source_proposal_sha256": proposal["proposal_sha256"],
            "source_approved_plan_sha256": plan["plan_sha256"],
            "placement_id": "placement-001",
            "style_profile_id": "dbd-aggressive",
            "event_type": "PALLET_DROP",
            "music_anchor_kind": "DROP",
            "proposed_target_timeline_frame": 600,
            "human_review_target_timeline_frame": 602,
            "final_target_timeline_frame": 604,
            "disposition": "MOVED",
            "delta_from_proposal_frames": 4,
            "delta_from_review_frames": 2,
            "preset_families": ["zoom"],
            "do_not_learn": False,
            "raw_media_included": False,
            "absolute_host_path_included": False,
            "automatic_learning_promotion_authorized": False,
            "automatic_edit_plan_mutation_authorized": False,
        },
        "evidence_sha256",
    )
    return proposal, plan, human


def test_human_action_evidence_is_deterministic_schema_valid_and_no_effect():
    row = evidence()
    first = row.to_dict()
    assert first == row.to_dict()
    assert first["admission_state"] == "ELIGIBLE_FOR_EVALUATION"
    assert first["raw_media_included"] is False
    assert first["text_body_included"] is False
    assert first["absolute_host_path_included"] is False
    assert first["credential_included"] is False
    assert first["automatic_learning_promotion_authorized"] is False
    assert first["external_effect_authorized"] is False
    verify_human_action_evidence_hash(first)
    validate_instance(first, ROOT / "schemas" / "human-edit-learning.schema.json")
    with pytest.raises(FrozenInstanceError):
        row.evidence_id = "changed"


def test_task055_bridge_admits_exact_lineage_without_body_or_path():
    proposal, plan, human = montage_documents()
    row = compile_montage_human_action_evidence(
        evidence_id="human-action.montage.001",
        owner_scope_sha256=SHA_A,
        project_scope_sha256=SHA_B,
        proposal=proposal,
        approved_plan=plan,
        montage_evidence=human,
        observed_at_epoch_ms=1_700_000_000_000,
    )
    value = row.to_dict()
    assert row.producer_task_id == "TASK-055"
    assert row.source_record_sha256 == human["evidence_sha256"]
    assert row.disposition is HumanDisposition.MODIFIED
    assert value["condition_keys"] == [
        "anchor:drop",
        "event:PALLET_DROP",
        "preset:zoom",
        "style:dbd-aggressive",
    ]
    serialized = json.dumps(value, ensure_ascii=False).lower()
    assert "c:\\" not in serialized
    assert "/home/" not in serialized
    assert value["text_body_included"] is False
    assert value["credential_included"] is False


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (evidence(validity=EvidenceValidity.UNKNOWN), EvidenceAdmissionState.UNKNOWN_EVIDENCE),
        (evidence(validity=EvidenceValidity.STALE), EvidenceAdmissionState.STALE_OR_REVOKED_EVIDENCE),
        (evidence(do_not_learn=True), EvidenceAdmissionState.DO_NOT_LEARN),
        (evidence(disposition=HumanDisposition.UNDONE), EvidenceAdmissionState.IMMEDIATE_UNDO),
        (
            evidence(disposition=HumanDisposition.REVISED_AFTER_ACCEPTANCE),
            EvidenceAdmissionState.LATER_REVISION,
        ),
        (evidence(safety=HardGateState.FAIL), EvidenceAdmissionState.SAFETY_BLOCKED),
        (evidence(rights=HardGateState.UNKNOWN), EvidenceAdmissionState.RIGHTS_BLOCKED),
    ],
)
def test_exclusion_and_hard_gate_states_fail_closed(row, expected):
    assert row.admission_state is expected


def test_disposition_and_exclusion_flags_must_match_exactly():
    with pytest.raises(ValueError, match="immediate_undo"):
        replace(evidence(), immediate_undo=True)
    with pytest.raises(ValueError, match="final snapshot"):
        replace(evidence(), disposition=HumanDisposition.REJECTED)


def test_owner_decision_candidate_preserves_six_axes_and_is_advisory_only():
    compiled = candidate()
    value = compiled.to_dict()
    assert compiled.state is OwnerDecisionState.READY_FOR_HUMAN_REVIEW
    assert compiled.weighted_benefit_milli == 20
    assert [row["metric_id"] for row in value["metric_evaluations"]] == list(METRIC_IDS)
    assert value["human_review_required"] is True
    for key in (
        "owner_profile_write_authorized",
        "knowledge_pack_promotion_authorized",
        "cloud_telemetry_authorized",
        "automatic_rollback_authorized",
        "edit_plan_mutation_authorized",
        "external_effect_authorized",
    ):
        assert value[key] is False
    verify_owner_decision_candidate_hash(value)
    validate_instance(value, ROOT / "schemas" / "human-edit-learning.schema.json")


def test_candidate_negative_matrix_is_distinct_and_fail_closed():
    assert candidate((evidence("human-action.001"),)).state is OwnerDecisionState.INSUFFICIENT_EVIDENCE
    assert candidate(
        (
            evidence("human-action.001"),
            evidence("human-action.002", condition="style:other"),
        )
    ).state is OwnerDecisionState.CONFLICTING_CONTEXT
    assert candidate(
        (
            evidence("human-action.001"),
            evidence("human-action.002", do_not_learn=True),
        )
    ).state is OwnerDecisionState.EXCLUDED_EVIDENCE_PRESENT
    assert candidate(
        (
            evidence("human-action.001"),
            evidence("human-action.002", safety=HardGateState.FAIL),
        )
    ).state is OwnerDecisionState.SAFETY_OR_RIGHTS_BLOCKED
    assert candidate(
        (
            evidence("human-action.001"),
            evidence("human-action.002", validity=EvidenceValidity.UNKNOWN),
        )
    ).state is OwnerDecisionState.UNKNOWN_EVIDENCE
    assert candidate(
        metric_rows=metrics(overrides={"quality_improvement": 499})
    ).state is OwnerDecisionState.AXIS_REGRESSION
    assert candidate(metric_rows=metrics(observed=500)).state is OwnerDecisionState.NO_MEASURED_BENEFIT


def test_missing_or_duplicate_metric_axis_is_rejected():
    with pytest.raises(ValueError, match="all six"):
        candidate(metric_rows=metrics()[:-1])
    duplicated = metrics()[:-1] + (metrics()[0],)
    with pytest.raises(ValueError, match="all six"):
        candidate(metric_rows=duplicated)


def test_hash_tamper_is_rejected():
    human = evidence().to_dict()
    human["work_duration_ms"] = 16_000
    with pytest.raises(ValueError, match="evidence_sha256 mismatch"):
        verify_human_action_evidence_hash(human)
    human = evidence().to_dict()
    human["condition_fingerprint_sha256"] = SHA_D
    human = _resign(human, "evidence_sha256")
    with pytest.raises(ValueError, match="derived fields or authority flags mismatch"):
        verify_human_action_evidence_hash(human)

    decision = candidate().to_dict()
    decision["state"] = "NO_MEASURED_BENEFIT"
    with pytest.raises(ValueError, match="candidate_sha256 mismatch"):
        verify_owner_decision_candidate_hash(decision)
    decision = candidate().to_dict()
    decision["learning_policy"]["minimum_evidence_records"] = 3
    decision = _resign(decision, "candidate_sha256")
    with pytest.raises(ValueError, match="policy_sha256 mismatch"):
        verify_owner_decision_candidate_hash(decision)
    decision = candidate().to_dict()
    decision["metric_evaluations"][0]["delta_milli"] = 999
    decision = _resign(decision, "candidate_sha256")
    with pytest.raises(ValueError, match="metric delta mismatch"):
        verify_owner_decision_candidate_hash(decision)
    decision = candidate().to_dict()
    decision["owner_profile_write_authorized"] = True
    decision = _resign(decision, "candidate_sha256")
    with pytest.raises(ValueError, match="owner_profile_write_authorized must remain false"):
        verify_owner_decision_candidate_hash(decision)


def test_schema_mirror_is_byte_identical_and_accepts_both_records():
    public = (ROOT / "schemas" / "human-edit-learning.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "human-edit-learning.schema.json"
    ).read_bytes()
    assert public == packaged
    schema = json.loads(public)
    validate_instance(evidence().to_dict(), schema)
    validate_instance(candidate().to_dict(), schema)


def test_module_has_no_io_provider_or_effect_surface():
    source_path = ROOT / "src" / "ai_video_production" / "human_edit_learning.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and not node.module.startswith(".")
    )
    assert imports.isdisjoint(
        {"pathlib", "os", "socket", "subprocess", "requests", "urllib", "http", "sqlite3"}
    )
    source = source_path.read_text(encoding="utf-8")
    assert "open(" not in source
    assert "automatic_learning_promotion_authorized\": False" in source
    assert "knowledge_pack_promotion_authorized\": False" in source
