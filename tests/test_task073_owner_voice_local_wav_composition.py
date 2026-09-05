from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
import ai_video_production.task073_owner_voice_local_wav_composition as task073
from ai_video_production.task073_owner_voice_local_wav_composition import (
    DESIGN_BUNDLE_SHA256, OwnerVoiceLocalWavCompositionV4, RECEIPT_ALLOWLIST,
    RECEIPT_SLOTS,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "task073-owner-voice-local-wav-composition.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / SCHEMA.name
NOW = "2026-09-05T01:00:00Z"

def digest(label: str) -> str: return sha256_bytes(label.encode())
def state(slot: str) -> str:
    return {"installed_session":"READY","quick_clone":"ACCEPTED","selection":"SELECTED","reference":"PREPARED_VERIFIED","call_profile":"READY_FOR_TASK075_DISPATCH","compute_admission":"ADMITTED","human_plan":"CONFIRMED","operation_ticket":"ISSUED","durable_job":"SUCCEEDED","inference":"SUCCESS","wav":"PUBLISHED_READBACK_VERIFIED","qa":"PASS","playback":"COMPLETED","listening_join":"ACCEPTED"}[slot]
def receipt(slot: str, *, pair: tuple[str, str] | None = None, fixture: bool = False) -> dict[str, object]:
    owner, kind, version = RECEIPT_ALLOWLIST[slot]
    candidate = pair if slot in {"quick_clone","wav","qa","playback","listening_join"} else (None, None)
    operation = None if slot in {"installed_session","quick_clone","selection","reference"} else digest("operation")
    quick = None if slot == "installed_session" else digest("quick-head")
    expiry = "2026-09-05T02:00:00Z" if slot in {"reference","call_profile","compute_admission","human_plan","operation_ticket","durable_job"} else None
    return {"owner_task":owner,"receipt_type":kind,"schema_version":version,"opaque_ref":f"receipt.{slot}.1","receipt_sha256":digest("receipt-"+slot),"producer_build_sha256":digest("build-"+slot),"producer_state":state(slot),"candidate_id":candidate[0],"candidate_sha256":candidate[1],"project_id":"project.alpha","project_manifest_sha256":digest("manifest"),"installed_session_sha256":digest("install"),"operation_plan_sha256":operation,"quick_clone_flow_sha256":quick,"revision":1,"head_sha256":digest("quick-head") if slot=="quick_clone" else digest("head-"+slot),"observed_at":"2026-09-05T00:30:00Z","expires_at":expiry,"current":True,"fixture_only":fixture,"authority_created":not fixture,"production_eligible":not fixture}
def slots(count: int = 14) -> dict[str, dict[str, object] | None]:
    pair = ("candidate.alpha", digest("wav"))
    return {slot: receipt(slot, pair=pair) if i < count else None for i, slot in enumerate(RECEIPT_SLOTS)}
def make(values=None, *, derived="WAV_ACCEPTED", reasons=(), installed_session_sha256=digest("install"), operation_plan_sha256=digest("operation")):
    return OwnerVoiceLocalWavCompositionV4.create(composition_id="task073.composition.1",composition_revision=1,parent_composition_sha256=None,observed_at=NOW,project_id="project.alpha",project_manifest_revision=4,project_manifest_sha256=digest("manifest"),installed_session_sha256=installed_session_sha256,operation_plan_sha256=operation_plan_sha256,receipts=slots() if values is None else values,derived_state=derived,reason_codes=reasons)

def progression_slots(through_group: int, *, job_state: str | None = None) -> dict[str, dict[str, object] | None]:
    pair = ("candidate.alpha", digest("wav"))
    groups = (
        ("installed_session",),
        ("quick_clone",),
        ("reference",),
        ("selection",),
        ("call_profile", "compute_admission"),
        ("human_plan",),
        ("operation_ticket",),
        ("durable_job",),
        ("inference",),
        ("wav",),
        ("qa",),
        ("playback",),
        ("listening_join",),
    )
    result: dict[str, dict[str, object] | None] = {slot: None for slot in RECEIPT_SLOTS}
    for group in groups[: through_group + 1]:
        for slot in group:
            result[slot] = receipt(slot, pair=pair)
    if job_state is not None:
        assert result["durable_job"] is not None
        result["durable_job"]["producer_state"] = job_state
    return result

def test_receipt_v2_schema_mirror_round_trip_and_hash() -> None:
    result = make().to_dict()
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(result)
    assert result["design_bundle_sha256"] == DESIGN_BUNDLE_SHA256
    assert OwnerVoiceLocalWavCompositionV4.from_dict(result).to_dict() == result

@pytest.mark.parametrize("slot", ["wav","qa","playback","listening_join"])
def test_late_receipts_require_complete_candidate_pair(slot: str) -> None:
    values = slots(); values[slot]["candidate_id"] = None
    with pytest.raises(ValueError, match="both null|required"): make(values)

def test_active_quick_clone_cannot_claim_candidate_pair() -> None:
    values = slots(); values["quick_clone"]["producer_state"] = "ACTIVE"
    with pytest.raises(ValueError, match="active quick clone"): make(values)

@pytest.mark.parametrize("quick_state", ["BLOCKED", "UNKNOWN"])
def test_candidate_bearing_late_receipt_requires_a_quick_clone_anchor(quick_state: str) -> None:
    values = slots()
    values["quick_clone"]["producer_state"] = quick_state
    values["quick_clone"]["candidate_id"] = None
    values["quick_clone"]["candidate_sha256"] = None
    reasons = ("CANDIDATE_MISMATCH", "PRODUCER_BLOCKED") if quick_state == "BLOCKED" else ("CANDIDATE_MISMATCH",)
    blocked = make(values, derived="BLOCKED", reasons=reasons).to_dict()
    assert blocked["reason_codes"] == sorted(reasons)

def test_terminal_candidate_pair_must_match_across_all_late_receipts() -> None:
    values = slots(); values["qa"]["candidate_id"] = "candidate.other"
    blocked = make(values, derived="BLOCKED", reasons=("CANDIDATE_MISMATCH",)).to_dict()
    assert blocked["reason_codes"] == ["CANDIDATE_MISMATCH"]
    with pytest.raises(ValueError, match="fail closed"): make(values)

@pytest.mark.parametrize("quick,listening", [("ACCEPTED", "REJECTED"), ("REJECTED", "ACCEPTED"), ("ACTIVE", "ACCEPTED")])
def test_terminal_state_crosswalk_rejects_asymmetric_or_active_pairs(quick: str, listening: str) -> None:
    values = slots(); values["quick_clone"]["producer_state"] = quick; values["listening_join"]["producer_state"] = listening
    with pytest.raises(ValueError, match="derived_state|active quick clone"):
        make(values)

def test_current_conflict_and_same_hash_different_body_are_closed() -> None:
    values = slots(); observations = {s: ([] if x is None else [deepcopy(x)]) for s,x in values.items()}
    competitor = deepcopy(observations["qa"][0]); competitor["receipt_sha256"] = digest("competing")
    observations["qa"].append(competitor)
    blocked = OwnerVoiceLocalWavCompositionV4.create_from_observations(observations=observations,composition_id="task073.composition.1",composition_revision=1,parent_composition_sha256=None,observed_at=NOW,project_id="project.alpha",project_manifest_revision=4,project_manifest_sha256=digest("manifest"),installed_session_sha256=digest("install"),operation_plan_sha256=digest("operation"),derived_state="WAV_ACCEPTED").to_dict()
    assert blocked["derived_state"] == "BLOCKED"
    assert blocked["reason_codes"] == ["MISSING_REQUIRED_RECEIPT", "MULTIPLE_CURRENT_RECEIPTS"]
    observations["qa"] = [deepcopy(values["qa"]), deepcopy(values["qa"])]
    observations["qa"][1]["head_sha256"] = digest("forged")
    with pytest.raises(ValueError, match="different content"):
        OwnerVoiceLocalWavCompositionV4.create_from_observations(observations=observations,composition_id="task073.composition.1",composition_revision=1,parent_composition_sha256=None,observed_at=NOW,project_id="project.alpha",project_manifest_revision=4,project_manifest_sha256=digest("manifest"),installed_session_sha256=digest("install"),operation_plan_sha256=digest("operation"),derived_state="WAV_ACCEPTED")

def test_coordinate_stale_expiry_and_fixture_lineage_fail_closed_or_taint() -> None:
    values = slots(); values["reference"]["expires_at"] = NOW
    with pytest.raises(ValueError, match="fail closed"): make(values)
    values = slots(4); values["selection"] = receipt("selection", fixture=True)
    result = make(values, derived="READY_TO_RENDER", operation_plan_sha256=None).to_dict()
    assert result["fixture_lineage"]["fixture_only"] is True
    assert result["fixture_lineage"]["authority_created"] is False
    assert result["fixture_lineage"]["production_eligible"] is False
    assert result["fixture_lineage"]["producer_fixture_count"] >= 1

def test_non_authoritative_or_nonproduction_receipt_taints_fixture_lineage() -> None:
    values = slots(4)
    values["selection"]["authority_created"] = False
    result = make(values, derived="READY_TO_RENDER", operation_plan_sha256=None).to_dict()
    assert result["fixture_lineage"] == {
        "fixture_only": False,
        "authority_created": False,
        "production_eligible": False,
        "fixture_set_sha256": sha256_bytes(canonical_json_bytes([["selection", values["selection"]["receipt_sha256"]]])),
        "producer_fixture_count": 1,
    }

def test_unknown_field_hash_tamper_and_deepcopy_are_rejected_or_isolated() -> None:
    value = make().to_dict(); value["receipts"]["qa"]["private_path"] = "C:/private.wav"
    with pytest.raises(ValueError, match="incomplete, unknown, or reordered"): OwnerVoiceLocalWavCompositionV4.from_dict(value)
    value = make().to_dict(); value["composition_id"] = "task073.other"
    with pytest.raises(ValueError, match="composition_sha256"): OwnerVoiceLocalWavCompositionV4.from_dict(value)
    model = make(); first, second = model.to_dict(), model.to_dict(); first["receipts"]["qa"]["opaque_ref"] = "receipt.changed.1"
    assert second["receipts"]["qa"]["opaque_ref"] == "receipt.qa.1"

def test_state_is_not_caller_claim_and_direct_constructor_cannot_keep_mutable_input() -> None:
    values = slots(); values["qa"]["producer_state"] = "FAIL"
    with pytest.raises(ValueError, match="derived_state"):
        make(values, derived="WAV_ACCEPTED")
    result = make().to_dict()
    model = OwnerVoiceLocalWavCompositionV4(result)
    result["receipts"]["qa"]["opaque_ref"] = "receipt.forged.1"
    assert model.to_dict()["receipts"]["qa"]["opaque_ref"] == "receipt.qa.1"

def test_caller_cannot_add_or_omit_automatic_reason_codes() -> None:
    values = slots(); values["qa"]["candidate_id"] = "candidate.other"
    with pytest.raises(ValueError, match="exactly match"):
        make(values, derived="BLOCKED", reasons=("CANDIDATE_MISMATCH", "STALE_RECEIPT"))
    with pytest.raises(ValueError, match="derived_state|exactly match"):
        make(values, derived="BLOCKED", reasons=())

@pytest.mark.parametrize(
    "through_group,job_state,derived,installed,operation",
    [
        (-1, None, "SETUP_REQUIRED", None, None),
        (0, None, "REFERENCE_REQUIRED", digest("install"), None),
        (1, None, "REFERENCE_REQUIRED", digest("install"), None),
        (2, None, "MODEL_SELECTION_REQUIRED", digest("install"), None),
        (3, None, "READY_TO_RENDER", digest("install"), None),
        (4, None, "CONFIRMATION_REQUIRED", digest("install"), digest("operation")),
        (5, None, "CONFIRMATION_REQUIRED", digest("install"), digest("operation")),
        (6, None, "QUEUED", digest("install"), digest("operation")),
        (7, "QUEUED", "QUEUED", digest("install"), digest("operation")),
        (7, "RUNNING", "RUNNING", digest("install"), digest("operation")),
        (7, "RECOVERY_REQUIRED", "RECOVERY_REQUIRED", digest("install"), digest("operation")),
        (7, "UNKNOWN", "UNKNOWN", digest("install"), digest("operation")),
        (8, None, "RUNNING", digest("install"), digest("operation")),
        (9, None, "QA_REQUIRED", digest("install"), digest("operation")),
        (10, None, "LISTENING_REQUIRED", digest("install"), digest("operation")),
        (11, None, "LISTENING_REQUIRED", digest("install"), digest("operation")),
        (12, None, "WAV_ACCEPTED", digest("install"), digest("operation")),
    ],
)
def test_each_deterministic_progression_state(
    through_group: int,
    job_state: str | None,
    derived: str,
    installed: str | None,
    operation: str | None,
) -> None:
    values = progression_slots(through_group, job_state=job_state)
    result = make(
        values,
        derived=derived,
        installed_session_sha256=installed,
        operation_plan_sha256=operation,
    ).to_dict()
    assert result["derived_state"] == derived
    _schema().validate(result)

@pytest.mark.parametrize(
    "mutate",
    [
        lambda values: values["operation_ticket"].__setitem__("producer_state", "CONSUMED"),
        lambda values: values["compute_admission"].__setitem__("operation_plan_sha256", digest("other-operation")),
    ],
)
def test_contradictory_progression_is_blocked_with_exact_reason(mutate) -> None:
    values = progression_slots(6)
    mutate(values)
    expected = "MISSING_REQUIRED_RECEIPT" if values["operation_ticket"]["producer_state"] == "CONSUMED" else "OPERATION_MISMATCH"
    blocked = make(values, derived="BLOCKED", reasons=(expected,), operation_plan_sha256=digest("operation")).to_dict()
    assert blocked["reason_codes"] == [expected]

def test_receipt_top_and_lineage_field_reordering_is_rejected() -> None:
    for target_path in (("composition",), ("receipts", "qa"), ("fixture_lineage",)):
        document = make().to_dict()
        if target_path == ("composition",):
            reordered = {"record_type": document["record_type"], "schema": document["schema"], **{key: value for key, value in document.items() if key not in {"schema", "record_type"}}}
        else:
            target = document[target_path[0]] if len(target_path) == 1 else document[target_path[0]][target_path[1]]
            keys = list(target)
            target = {keys[1]: target[keys[1]], keys[0]: target[keys[0]], **{key: target[key] for key in keys[2:]}}
            document[target_path[0]] = target if len(target_path) == 1 else {**document[target_path[0]], target_path[1]: target}
            reordered = document
        with pytest.raises(ValueError, match="reordered"):
            OwnerVoiceLocalWavCompositionV4.from_dict(reordered)

def test_direct_create_and_observation_aggregation_reject_reordered_slot_maps() -> None:
    values = slots()
    reordered = {"quick_clone": values["quick_clone"], "installed_session": values["installed_session"], **{slot: values[slot] for slot in RECEIPT_SLOTS[2:]}}
    with pytest.raises(ValueError, match="fixed slots in order"):
        make(reordered)
    observations = {slot: ([] if item is None else [item]) for slot, item in reordered.items()}
    with pytest.raises(ValueError, match="slots in order"):
        OwnerVoiceLocalWavCompositionV4.create_from_observations(
            observations=observations,
            composition_id="task073.composition.1",
            composition_revision=1,
            parent_composition_sha256=None,
            observed_at=NOW,
            project_id="project.alpha",
            project_manifest_revision=4,
            project_manifest_sha256=digest("manifest"),
            installed_session_sha256=digest("install"),
            operation_plan_sha256=digest("operation"),
            derived_state="WAV_ACCEPTED",
        )

def test_reason_code_inventory_matches_the_canonical_sixteen_values() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert len(task073.REASON_CODES) == 16
    assert set(schema["properties"]["reason_codes"]["items"]["enum"]) == task073.REASON_CODES
    assert schema["properties"]["reason_codes"]["maxItems"] == 16

@pytest.mark.parametrize("slot,bad", [("operation_ticket", "BURNED"), ("inference", "FAILED_KNOWN"), ("qa", "FAIL")])
def test_terminal_failure_states_cannot_be_projected_as_success(slot: str, bad: str) -> None:
    values = slots(); values[slot]["producer_state"] = bad
    with pytest.raises(ValueError, match="derived_state"):
        make(values, derived="WAV_ACCEPTED")

def test_matching_rejected_terminal_is_not_production_eligible_and_asymmetric_is_blocked() -> None:
    values = slots(); values["quick_clone"]["producer_state"] = "REJECTED"; values["listening_join"]["producer_state"] = "REJECTED"
    assert make(values, derived="WAV_REJECTED").to_dict()["fixture_lineage"]["production_eligible"] is False
    values["listening_join"]["producer_state"] = "ACCEPTED"
    with pytest.raises(ValueError, match="derived_state"):
        make(values, derived="WAV_REJECTED")

@pytest.mark.parametrize("slot", ["quick_clone", "listening_join"])
def test_one_sided_retest_with_the_same_candidate_pair_is_legal(slot: str) -> None:
    values = slots(); values[slot]["producer_state"] = "RETEST_REQUIRED"
    assert make(values, derived="WAV_RETEST_REQUIRED").to_dict()["derived_state"] == "WAV_RETEST_REQUIRED"

def _schema() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

@pytest.mark.parametrize(
    "slot,field,value",
    [
        ("qa", "owner_task", "TASK-999"),
        ("qa", "receipt_type", "UNKNOWN_RECEIPT"),
        ("qa", "schema_version", 2),
        ("qa", "producer_state", "READY"),
        ("durable_job", "producer_state", "ACCEPTED"),
        ("selection", "producer_state", "READY"),
    ],
)
def test_schema_rejects_slot_specific_allowlist_and_state_mismatch(slot: str, field: str, value: object) -> None:
    document = make().to_dict()
    document["receipts"][slot][field] = value
    assert not _schema().is_valid(document)

@pytest.mark.parametrize("slot", ["installed_session", "selection", "reference", "call_profile", "compute_admission", "human_plan", "operation_ticket", "durable_job", "inference"])
def test_schema_rejects_candidate_pair_on_non_candidate_slots(slot: str) -> None:
    document = make().to_dict()
    document["receipts"][slot]["candidate_id"] = "candidate.forged"
    document["receipts"][slot]["candidate_sha256"] = digest("forged-wav")
    assert not _schema().is_valid(document)

@pytest.mark.parametrize("slot", ["wav", "qa", "playback", "listening_join"])
def test_schema_requires_candidate_pair_on_late_slots(slot: str) -> None:
    document = make().to_dict()
    document["receipts"][slot]["candidate_id"] = None
    document["receipts"][slot]["candidate_sha256"] = None
    assert not _schema().is_valid(document)

def test_schema_enforces_quick_clone_state_candidate_applicability() -> None:
    document = make(slots(4), derived="READY_TO_RENDER", operation_plan_sha256=None).to_dict()
    document["receipts"]["quick_clone"]["producer_state"] = "ACTIVE"
    assert not _schema().is_valid(document)
    document["receipts"]["quick_clone"]["candidate_id"] = None
    document["receipts"]["quick_clone"]["candidate_sha256"] = None
    assert _schema().is_valid(document)

@pytest.mark.parametrize(
    "slot,field,value",
    [
        ("installed_session", "operation_plan_sha256", digest("forged-operation")),
        ("installed_session", "quick_clone_flow_sha256", digest("forged-quick")),
        ("reference", "expires_at", None),
        ("call_profile", "operation_plan_sha256", None),
        ("inference", "expires_at", "2026-09-05T02:00:00Z"),
    ],
)
def test_schema_rejects_slot_coordinate_or_expiry_applicability(slot: str, field: str, value: object) -> None:
    document = make().to_dict()
    document["receipts"][slot][field] = value
    assert not _schema().is_valid(document)

def test_schema_enforces_top_operation_timing_and_terminal_crosswalk() -> None:
    ready = make(slots(4), derived="READY_TO_RENDER", operation_plan_sha256=None).to_dict()
    assert _schema().is_valid(ready)
    ready["operation_plan_sha256"] = digest("too-early")
    assert not _schema().is_valid(ready)
    accepted = make().to_dict()
    accepted["operation_plan_sha256"] = None
    assert not _schema().is_valid(accepted)
    accepted = make().to_dict()
    accepted["receipts"]["listening_join"]["producer_state"] = "REJECTED"
    assert not _schema().is_valid(accepted)

@pytest.mark.parametrize("derived", ["WAV_ACCEPTED", "WAV_REJECTED", "WAV_RETEST_REQUIRED"])
@pytest.mark.parametrize("slot", ["quick_clone", "listening_join"])
def test_schema_terminal_states_require_nonnull_terminal_receipts(derived: str, slot: str) -> None:
    values = slots()
    if derived == "WAV_REJECTED":
        values["quick_clone"]["producer_state"] = "REJECTED"
        values["listening_join"]["producer_state"] = "REJECTED"
    elif derived == "WAV_RETEST_REQUIRED":
        values["quick_clone"]["producer_state"] = "RETEST_REQUIRED"
    document = make(values, derived=derived).to_dict()
    document["receipts"][slot] = None
    assert not _schema().is_valid(document)

@pytest.mark.parametrize(
    "later,earlier",
    [
        ("quick_clone", "installed_session"),
        ("reference", "quick_clone"),
        ("selection", "reference"),
        ("call_profile", "compute_admission"),
        ("compute_admission", "call_profile"),
        ("human_plan", "call_profile"),
        ("operation_ticket", "human_plan"),
        ("durable_job", "operation_ticket"),
        ("inference", "durable_job"),
        ("wav", "inference"),
        ("qa", "wav"),
        ("playback", "qa"),
        ("listening_join", "playback"),
    ],
)
def test_schema_rejects_every_immediate_prefix_gap(later: str, earlier: str) -> None:
    document = _blocked_schema_document()
    assert document["receipts"][later] is not None
    document["receipts"][earlier] = None
    assert not _schema().is_valid(document), (later, earlier)

@pytest.mark.parametrize(
    "path,value",
    [
        (("composition_id",), "C:/private/project"),
        (("composition_id",), "x" * 201),
        (("observed_at",), "2026-09-05 01:00:00"),
        (("composition_revision",), 2147483648),
        (("receipts", "qa", "opaque_ref"), "https://private.example/voice"),
        (("receipts", "qa", "revision"), 0),
    ],
)
def test_schema_rejects_identifier_timestamp_and_size_bounds(path: tuple[str, ...], value: object) -> None:
    document = make().to_dict()
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    assert not _schema().is_valid(document)

def test_schema_rejects_unknown_top_receipt_and_lineage_fields() -> None:
    validator = _schema()
    for path in (("private_path",), ("receipts", "unknown"), ("fixture_lineage", "private_count")):
        document = make().to_dict()
        target = document
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = "private"
        assert not validator.is_valid(document)

def _blocked_schema_document() -> dict[str, object]:
    document = make().to_dict()
    document["derived_state"] = "BLOCKED"
    document["reason_codes"] = ["PRODUCER_BLOCKED"]
    document["fixture_lineage"]["production_eligible"] = False
    return document

@pytest.mark.parametrize("slot", RECEIPT_SLOTS)
def test_schema_accepts_every_runtime_slot_allowlist_and_state_vocabulary(slot: str) -> None:
    validator = _schema()
    owner, kind, version = RECEIPT_ALLOWLIST[slot]
    for producer_state in task073._STATES[slot]:
        document = _blocked_schema_document()
        item = document["receipts"][slot]
        item["owner_task"], item["receipt_type"], item["schema_version"] = owner, kind, version
        item["producer_state"] = producer_state
        if slot == "quick_clone":
            pair_required = producer_state in {"RETEST_REQUIRED", "ACCEPTED", "REJECTED"}
            item["candidate_id"] = "candidate.alpha" if pair_required else None
            item["candidate_sha256"] = digest("wav") if pair_required else None
        assert validator.is_valid(document), (slot, producer_state)

@pytest.mark.parametrize("slot", RECEIPT_SLOTS)
@pytest.mark.parametrize("field", ["owner_task", "receipt_type", "schema_version", "producer_state"])
def test_schema_rejects_every_slot_allowlist_or_state_escape(slot: str, field: str) -> None:
    document = _blocked_schema_document()
    document["receipts"][slot][field] = 99 if field == "schema_version" else "INVALID"
    assert not _schema().is_valid(document), (slot, field)

@pytest.mark.parametrize("slot", RECEIPT_SLOTS)
def test_schema_enforces_every_slot_operation_quick_and_expiry_coordinate(slot: str) -> None:
    validator = _schema()
    operation_required, quick_required, expiry_required = task073._COORDS[slot][3:]
    mutations = {
        "operation_plan_sha256": None if operation_required else digest("forged-operation"),
        "quick_clone_flow_sha256": None if quick_required else digest("forged-quick"),
        "expires_at": None if expiry_required else "2026-09-05T02:00:00Z",
    }
    for field, value in mutations.items():
        document = _blocked_schema_document()
        document["receipts"][slot][field] = value
        assert not validator.is_valid(document), (slot, field)
