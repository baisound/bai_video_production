from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.montage_learning_bridge_contracts import (
    EXACT_LINEAGE_VERIFIED,
    OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE,
    OWNER_SCOPE_UNBOUND,
    REVIEW_REQUIRED,
    MontageLearningBridgeContractError,
    canonical_learning_sha256,
    validate_exact_evidence_delivery,
    validate_generic_learning_delivery,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
OWNER_SCOPE_HASH = "sha256:" + "a" * 64
BODY_FREE_RESULT_FIELDS = {
    "lane",
    "record_id",
    "source_sha256",
    "validation_state",
    "owner_scope_state",
    "review_state",
    "runtime_observation_state",
    "canonical_timeline",
    "canonical_admission_authorized",
    "canonical_store_write_authorized",
    "automatic_learning_promotion_authorized",
    "runtime_authority_created",
    "receipt_minted",
}


def _sign(body: dict[str, object], field: str) -> dict[str, object]:
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _proposal() -> dict[str, object]:
    return _sign(
        {
            "schema_version": "1.0.0",
            "record_kind": "MONTAGE_PROPOSAL_BUNDLE",
            "project_id": "proj-test",
            "production_job_id": "JOB-01J00000000000000000000000",
            "timeline_rate": {"numerator": 60, "denominator": 1},
            "music_asset_id": "ASSET-01J00000000000000000000002",
            "style_profile_id": "dbd-aggressive",
            "preset_manifest_sha256": "sha256:" + "1" * 64,
            "external_generator": {
                "generator_id": "davinci-beat-sync-montage-director",
                "version": "0.6.0",
                "sha256": "sha256:" + "3" * 64,
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


def _approved_plan(proposal: dict[str, object]) -> dict[str, object]:
    placements = proposal["placements"]
    assert isinstance(placements, list)
    return _sign(
        {
            "plan_version": "1.0.0",
            "task_owner": "TASK-055",
            "source_proposal_sha256": proposal["proposal_sha256"],
            "approved_by": "owner-local",
            "placements": [
                {
                    "placement": deepcopy(placements[0]),
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


def _human_edit_evidence(
    proposal: dict[str, object], approved_plan: dict[str, object]
) -> dict[str, object]:
    return _sign(
        {
            "evidence_version": "1.0.0",
            "task_owner": "TASK-055",
            "source_proposal_sha256": proposal["proposal_sha256"],
            "source_approved_plan_sha256": approved_plan["plan_sha256"],
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


def _exact_delivery() -> dict[str, object]:
    proposal = _proposal()
    approved_plan = _approved_plan(proposal)
    evidence = _human_edit_evidence(proposal, approved_plan)
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageExactEvidenceDelivery",
        "contract_profile": "bvp-task058-montage-exact-evidence-v1",
        "record_id": "exact-delivery-001",
        "proposal_sha256": proposal["proposal_sha256"],
        "approved_plan_sha256": approved_plan["plan_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
        "owner_scope_hash": OWNER_SCOPE_HASH,
        "canonical_timeline": False,
        "auto_admit_authorized": False,
        "proposal": proposal,
        "approved_plan": approved_plan,
        "human_edit_evidence": evidence,
        "authority_flags": {
            "exact_lineage_is_canonical_admission": False,
            "canonical_store_write_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "receipt_mint_authorized": False,
        },
        "effect_flags": {
            "filesystem_written": False,
            "network_accessed": False,
            "database_accessed": False,
            "native_application_started": False,
            "canonical_store_written": False,
            "receipt_minted": False,
        },
    }


def _generic_payload(style_profile: object = "dbd-aggressive") -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "message_type": "MontageLearningExport",
        "record_id": "learning-record-001",
        "source_feedback_id": "feedback-001",
        "proposal_id": "proposal-001",
        "timeline_fps": {"numerator": 60, "denominator": 1},
        "style_profile": style_profile,
        "music_context": {"anchor_kind": "DROP"},
        "video_context": {"event_type": "PALLET_DROP"},
        "proposal": {"timeline_frame": 600},
        "human_final": {
            "timeline_frame": 604,
            "status": "moved",
            "provenance": {
                "actor_role": "owner-editor",
                "player_name": "[REDACTED]",
            },
        },
        "delta_frames": 4,
        "result": "moved",
        "privacy": {
            "safe_export": True,
            "raw_actor_exported": False,
            "redacted_field_paths": ["$.human_final.provenance.player_name"],
        },
        "validation_status": {
            "planning": "PASS",
            "static": "PASS",
            "package": "PASS",
            "runtime": "NOT_RUN",
        },
        "adapter_metadata": {
            "canonical_timeline": False,
            "absolute_host_path_included": False,
        },
    }


def _generic_delivery(style_profile: object = "dbd-aggressive") -> dict[str, object]:
    payload = _generic_payload(style_profile)
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "record_id": payload["record_id"],
        "learning_sha256": canonical_learning_sha256(payload),
        "canonical_timeline": False,
        "auto_admit_authorized": False,
        "payload": payload,
    }


def _resign(document: dict[str, object], field: str) -> dict[str, object]:
    body = deepcopy(document)
    body.pop(field)
    return _sign(body, field)


def _rehash_generic(delivery: dict[str, object]) -> None:
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    delivery["learning_sha256"] = canonical_learning_sha256(payload)


def test_public_schemas_are_valid_byte_exact_mirrors_and_admit_positive_values():
    cases = (
        ("montage-exact-evidence-delivery.schema.json", _exact_delivery()),
        ("montage-learning-file-bridge.schema.json", _generic_delivery()),
        (
            "montage-learning-file-bridge.schema.json",
            _generic_delivery({"profile_id": "dbd-aggressive", "weight": 1}),
        ),
    )
    for name, value in cases:
        public_bytes = (ROOT / "schemas" / name).read_bytes()
        packaged_bytes = (
            ROOT / "src" / "ai_video_production" / "schema_resources" / name
        ).read_bytes()
        assert public_bytes == packaged_bytes
        schema = json.loads(public_bytes)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)


def test_exact_delivery_verifies_embedded_lineage_but_returns_body_free_review_only_candidate():
    delivery = _exact_delivery()
    result = validate_exact_evidence_delivery(
        delivery, expected_owner_scope_hash=OWNER_SCOPE_HASH
    ).to_dict()

    assert result == {
        "lane": "EXACT_BVP_NATIVE",
        "record_id": "exact-delivery-001",
        "source_sha256": delivery["evidence_sha256"],
        "validation_state": EXACT_LINEAGE_VERIFIED,
        "owner_scope_state": OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE,
        "review_state": REVIEW_REQUIRED,
        "runtime_observation_state": "NOT_APPLICABLE",
        "canonical_timeline": False,
        "canonical_admission_authorized": False,
        "canonical_store_write_authorized": False,
        "automatic_learning_promotion_authorized": False,
        "runtime_authority_created": False,
        "receipt_minted": False,
    }
    assert set(result) == BODY_FREE_RESULT_FIELDS
    assert not ({"proposal", "approved_plan", "human_edit_evidence"} & set(result))


@pytest.mark.parametrize(
    "expected_owner_scope_hash",
    ["sha256:" + "b" * 64, "A" * 64, 0],
)
def test_exact_delivery_rejects_wrong_or_invalid_expected_owner_scope(
    expected_owner_scope_hash: object,
):
    with pytest.raises(MontageLearningBridgeContractError):
        validate_exact_evidence_delivery(
            _exact_delivery(), expected_owner_scope_hash=expected_owner_scope_hash
        )


def test_exact_delivery_rejects_top_level_hash_tamper():
    delivery = _exact_delivery()
    delivery["proposal_sha256"] = "sha256:" + "b" * 64
    with pytest.raises(MontageLearningBridgeContractError, match="proposal_sha256"):
        validate_exact_evidence_delivery(
            delivery, expected_owner_scope_hash=OWNER_SCOPE_HASH
        )


def test_exact_delivery_rejects_resigned_but_inconsistent_task055_lineage():
    delivery = _exact_delivery()
    evidence = deepcopy(delivery["human_edit_evidence"])
    assert isinstance(evidence, dict)
    evidence["source_approved_plan_sha256"] = "sha256:" + "9" * 64
    evidence = _resign(evidence, "evidence_sha256")
    delivery["human_edit_evidence"] = evidence
    delivery["evidence_sha256"] = evidence["evidence_sha256"]

    with pytest.raises(MontageLearningBridgeContractError, match="TASK-055 lineage"):
        validate_exact_evidence_delivery(
            delivery, expected_owner_scope_hash=OWNER_SCOPE_HASH
        )


@pytest.mark.parametrize(
    ("group", "field", "bad_value"),
    [
        (None, "canonical_timeline", True),
        (None, "auto_admit_authorized", 0),
        ("authority_flags", "canonical_store_write_authorized", True),
        ("authority_flags", "receipt_mint_authorized", 0),
        ("effect_flags", "filesystem_written", True),
        ("effect_flags", "receipt_minted", 0),
    ],
)
def test_exact_delivery_rejects_true_and_integer_zero_authority_or_effect_flags(
    group: str | None, field: str, bad_value: object
):
    delivery = _exact_delivery()
    target = delivery if group is None else delivery[group]
    assert isinstance(target, dict)
    target[field] = bad_value
    with pytest.raises(MontageLearningBridgeContractError):
        validate_exact_evidence_delivery(
            delivery, expected_owner_scope_hash=OWNER_SCOPE_HASH
        )


@pytest.mark.parametrize(
    "style_profile",
    ["", "   ", "dbd-aggressive", {"profile_id": "dbd-aggressive", "weight": 1}, {}],
)
def test_generic_delivery_accepts_string_or_object_style_as_unbound_review_candidate(
    style_profile: object,
):
    delivery = _generic_delivery(style_profile)
    result = validate_generic_learning_delivery(delivery).to_dict()

    assert result["lane"] == "GENERIC_SKILL_OBSERVATION"
    assert result["record_id"] == delivery["record_id"]
    assert result["source_sha256"] == delivery["learning_sha256"]
    assert result["validation_state"] == REVIEW_REQUIRED
    assert result["owner_scope_state"] == OWNER_SCOPE_UNBOUND
    assert result["review_state"] == REVIEW_REQUIRED
    assert result["runtime_observation_state"] == "SOURCE_NOT_RUN_NONAUTHORITATIVE"
    assert set(result) == BODY_FREE_RESULT_FIELDS
    for field in (
        "canonical_timeline",
        "canonical_admission_authorized",
        "canonical_store_write_authorized",
        "automatic_learning_promotion_authorized",
        "runtime_authority_created",
        "receipt_minted",
    ):
        assert result[field] is False


@pytest.mark.parametrize("style_profile", [[], 1, False])
def test_generic_delivery_rejects_invalid_style_profile(style_profile: object):
    delivery = _generic_delivery(style_profile)
    with pytest.raises(MontageLearningBridgeContractError, match="style_profile"):
        validate_generic_learning_delivery(delivery)


def test_generic_delivery_rejects_learning_hash_and_record_id_mismatches():
    hash_tamper = _generic_delivery()
    hash_tamper["learning_sha256"] = "sha256:" + "b" * 64
    with pytest.raises(MontageLearningBridgeContractError, match="learning_sha256"):
        validate_generic_learning_delivery(hash_tamper)

    record_tamper = _generic_delivery()
    record_tamper["record_id"] = "different-record"
    with pytest.raises(MontageLearningBridgeContractError, match="record_id"):
        validate_generic_learning_delivery(record_tamper)

def test_generic_delivery_preserves_v1_ids_empty_style_and_negative_frames():
    delivery = _generic_delivery("")
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    payload["source_feedback_id"] = "feedback/legacy value"
    payload["proposal_id"] = "proposal:legacy value"
    proposal = payload["proposal"]
    human_final = payload["human_final"]
    assert isinstance(proposal, dict)
    assert isinstance(human_final, dict)
    proposal["timeline_frame"] = -10
    human_final["timeline_frame"] = -6
    payload["delta_frames"] = 4
    _rehash_generic(delivery)
    schema = json.loads(
        (ROOT / "schemas" / "montage-learning-file-bridge.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(delivery)
    result = validate_generic_learning_delivery(delivery).to_dict()
    assert result["owner_scope_state"] == OWNER_SCOPE_UNBOUND
    assert result["review_state"] == REVIEW_REQUIRED


@pytest.mark.parametrize("field", ["source_feedback_id", "proposal_id"])
@pytest.mark.parametrize("bad_value", ["", "   "])
def test_generic_delivery_rejects_empty_source_identifiers(
    field: str, bad_value: str
):
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    payload[field] = bad_value
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError, match=field):
        validate_generic_learning_delivery(delivery)



def test_generic_delivery_rejects_unreduced_fps():
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    payload["timeline_fps"] = {"numerator": 120, "denominator": 2}
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError, match="reduced"):
        validate_generic_learning_delivery(delivery)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("delta_frames", 3, "delta_frames"),
        ("result", "deleted", "status mismatch"),
        ("validation_status", {"planning": "PASS"}, "fields mismatch"),
    ],
)
def test_generic_delivery_rejects_delta_result_status_and_validation_status_mismatch(
    field: str, bad_value: object, message: str
):
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    payload[field] = bad_value
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError, match=message):
        validate_generic_learning_delivery(delivery)


def test_generic_delivery_rejects_missing_human_provenance():
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    human_final = payload["human_final"]
    assert isinstance(human_final, dict)
    human_final.pop("provenance")
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError, match="provenance"):
        validate_generic_learning_delivery(delivery)


def test_generic_privacy_accepts_redaction_and_rejects_raw_sensitive_values():
    redacted = _generic_delivery()
    validate_generic_learning_delivery(redacted)

    raw = _generic_delivery()
    payload = raw["payload"]
    assert isinstance(payload, dict)
    human_final = payload["human_final"]
    assert isinstance(human_final, dict)
    provenance = human_final["provenance"]
    assert isinstance(provenance, dict)
    provenance["player_name"] = "private-player"
    _rehash_generic(raw)
    with pytest.raises(MontageLearningBridgeContractError, match="sensitive field"):
        validate_generic_learning_delivery(raw)


@pytest.mark.parametrize(
    ("container", "field", "bad_value"),
    [
        ("adapter_metadata", "absolute_host_path_included", True),
        ("adapter_metadata", "absolute_host_path_included", 0),
        ("privacy", "redacted_field_paths", "not-an-array"),
        ("privacy", "redacted_field_paths", [""]),
    ],
)
def test_generic_privacy_rejects_invalid_typed_safe_markers(
    container: str, field: str, bad_value: object
):
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    target = payload[container]
    assert isinstance(target, dict)
    target[field] = bad_value
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError):
        validate_generic_learning_delivery(delivery)


@pytest.mark.parametrize(
    "runtime_evidence",
    [None, {}, {"executed": False, "evidence_id": "runtime-001"}, {"executed": True}],
)
def test_generic_runtime_pass_requires_executed_evidence_reference(
    runtime_evidence: object,
):
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    statuses = payload["validation_status"]
    assert isinstance(statuses, dict)
    statuses["runtime"] = "PASS"
    if runtime_evidence is not None:
        payload["runtime_evidence"] = runtime_evidence
    _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError, match="runtime"):
        validate_generic_learning_delivery(delivery)


def test_generic_runtime_pass_with_reference_remains_nonauthoritative():
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    statuses = payload["validation_status"]
    assert isinstance(statuses, dict)
    statuses["runtime"] = "PASS"
    payload["runtime_evidence"] = {"executed": True, "report_ref": "report-001"}
    _rehash_generic(delivery)

    result = validate_generic_learning_delivery(delivery).to_dict()
    assert (
        result["runtime_observation_state"]
        == "SOURCE_PASS_CLAIM_STRUCTURALLY_VALID_NONAUTHORITATIVE"
    )
    assert result["runtime_authority_created"] is False
    assert result["receipt_minted"] is False


@pytest.mark.parametrize(
    ("target_name", "field"),
    [
        ("delivery", "canonical_timeline"),
        ("delivery", "auto_admit_authorized"),
        ("adapter_metadata", "canonical_timeline"),
    ],
)
def test_generic_delivery_rejects_integer_zero_for_boolean_false_contracts(
    target_name: str, field: str
):
    delivery = _generic_delivery()
    payload = delivery["payload"]
    assert isinstance(payload, dict)
    if target_name == "delivery":
        delivery[field] = 0
    else:
        target = payload[target_name]
        assert isinstance(target, dict)
        target[field] = 0
        _rehash_generic(delivery)
    with pytest.raises(MontageLearningBridgeContractError):
        validate_generic_learning_delivery(delivery)


def test_validation_is_deterministic_and_does_not_mutate_inputs():
    exact = _exact_delivery()
    exact_before = deepcopy(exact)
    exact_first = validate_exact_evidence_delivery(
        exact, expected_owner_scope_hash=OWNER_SCOPE_HASH
    ).to_dict()
    exact_second = validate_exact_evidence_delivery(
        exact, expected_owner_scope_hash=OWNER_SCOPE_HASH
    ).to_dict()
    assert exact == exact_before
    assert exact_first == exact_second

    generic = _generic_delivery()
    generic_before = deepcopy(generic)
    generic_first = validate_generic_learning_delivery(generic).to_dict()
    generic_second = validate_generic_learning_delivery(generic).to_dict()
    assert generic == generic_before
    assert generic_first == generic_second


def test_contract_results_create_no_receipt_store_or_canonical_authority():
    results = (
        validate_exact_evidence_delivery(
            _exact_delivery(), expected_owner_scope_hash=OWNER_SCOPE_HASH
        ).to_dict(),
        validate_generic_learning_delivery(_generic_delivery()).to_dict(),
    )
    for result in results:
        assert set(result) == BODY_FREE_RESULT_FIELDS
        assert result["canonical_timeline"] is False
        assert result["canonical_admission_authorized"] is False
        assert result["canonical_store_write_authorized"] is False
        assert result["automatic_learning_promotion_authorized"] is False
        assert result["runtime_authority_created"] is False
        assert result["receipt_minted"] is False
