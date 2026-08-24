"""Recovered TASK-055 montage contracts and fail-closed admission."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from math import gcd
from typing import Any, Iterable, Mapping
import json

from jsonschema import ValidationError
from jsonschema.validators import validator_for

from .serialization import canonical_json_bytes, sha256_bytes


class MontageContractError(ValueError):
    """A TASK-055 document failed schema, hash, semantic, or binding admission."""


@dataclass(frozen=True, slots=True)
class MontageContractDocument:
    _value: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._value)


_SCHEMAS = {
    "input": ("bvp-montage-skill-input.schema.json", "input_sha256"),
    "proposal": ("montage-proposal.schema.json", "proposal_sha256"),
    "plan": ("montage-approved-plan.schema.json", "plan_sha256"),
    "evidence": ("montage-human-edit-evidence.schema.json", "evidence_sha256"),
    "preference": ("montage-preference-profile.schema.json", "profile_sha256"),
    "handoff": ("montage-resolve-handoff.schema.json", "handoff_sha256"),
}


@lru_cache(maxsize=None)
def _validator(schema_name: str):
    schema = json.loads(
        files("ai_video_production.schema_resources")
        .joinpath(schema_name)
        .read_text(encoding="utf-8")
    )
    validator_type = validator_for(schema)
    validator_type.check_schema(schema)
    return validator_type(schema)


def _parse(value: Mapping[str, Any], kind: str, semantic) -> MontageContractDocument:
    if not isinstance(value, Mapping):
        raise MontageContractError("montage contract must be an object")
    document = deepcopy(dict(value))
    schema_name, hash_field = _SCHEMAS[kind]
    try:
        _validator(schema_name).validate(document)
    except ValidationError as exc:
        coordinate = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise MontageContractError(
            f"montage contract schema validation failed at {coordinate}: {exc.message}"
        ) from exc
    body = dict(document)
    body.pop(hash_field)
    if document[hash_field] != sha256_bytes(canonical_json_bytes(body)):
        raise MontageContractError(f"{hash_field} hash mismatch")
    semantic(document)
    return MontageContractDocument(document)


def _rate(value: Mapping[str, Any], name: str) -> None:
    if gcd(int(value["numerator"]), int(value["denominator"])) != 1:
        raise MontageContractError(f"{name} must be a reduced rational frame rate")


def _ids(values: Iterable[str], name: str) -> set[str]:
    rows = list(values)
    result = set(rows)
    if len(result) != len(rows):
        raise MontageContractError(f"{name} contains duplicate identities")
    return result


def _input(document: dict[str, Any]) -> None:
    _rate(document["source_rate"], "source_rate")
    _rate(document["timeline_rate"], "timeline_rate")
    _ids((row["candidate_id"] for row in document["candidates"]), "candidates")
    for row in document["candidates"]:
        if row["source_end_frame_exclusive"] <= row["source_start_frame"]:
            raise MontageContractError("candidate source range must be non-empty")


def _proposal(document: dict[str, Any]) -> None:
    _rate(document["timeline_rate"], "timeline_rate")
    anchors = {row["anchor_id"]: row for row in document["music_anchors"]}
    _ids((row["anchor_id"] for row in document["music_anchors"]), "music_anchors")
    placement_ids = _ids((row["placement_id"] for row in document["placements"]), "placements")
    for row in document["placements"]:
        _rate(row["source_rate"], "placement.source_rate")
        if row["source_end_frame_exclusive"] <= row["source_start_frame"]:
            raise MontageContractError("placement source range must be non-empty")
        if not row["source_start_frame"] <= row["source_anchor_frame"] < row["source_end_frame_exclusive"]:
            raise MontageContractError("placement source anchor is outside its source range")
        anchor = anchors.get(row["target_music_anchor_id"])
        if anchor is None or anchor["timeline_frame"] != row["target_timeline_frame"]:
            raise MontageContractError("placement music anchor binding mismatch")
    _ids((row["composition_id"] for row in document["compositions"]), "compositions")
    operation_ids: list[str] = []
    for row in document["compositions"]:
        if row["placement_id"] not in placement_ids:
            raise MontageContractError("composition references an unknown placement")
        _ids((op["preset_id"] for op in row["operations"]), "composition preset operations")
        operation_ids.extend(op["operation_id"] for op in row["operations"])
    _ids(operation_ids, "composition operations")


def _plan(document: dict[str, Any]) -> None:
    approved = _ids(
        (row["placement"]["placement_id"] for row in document["placements"]),
        "approved placements",
    )
    rejected = _ids((row["placement_id"] for row in document["rejected"]), "rejected placements")
    if approved & rejected:
        raise MontageContractError("placement cannot be approved and rejected")
    if not set(document["review_do_not_learn_placement_ids"]).issubset(approved | rejected):
        raise MontageContractError("do-not-learn references an unknown placement")
    for row in document["placements"]:
        placement = row["placement"]
        _rate(placement["source_rate"], "approved placement.source_rate")
        if row["proposed_target_timeline_frame"] != placement["target_timeline_frame"]:
            raise MontageContractError("approved proposed frame differs from placement")
        if row["delta_frames"] != row["final_target_timeline_frame"] - row["proposed_target_timeline_frame"]:
            raise MontageContractError("approved delta_frames is inconsistent")


def _evidence(document: dict[str, Any]) -> None:
    proposed = document["proposed_target_timeline_frame"]
    reviewed = document["human_review_target_timeline_frame"]
    final = document["final_target_timeline_frame"]
    disposition = document["disposition"]
    if disposition == "DELETED":
        if final is not None or document["delta_from_proposal_frames"] is not None or document["delta_from_review_frames"] is not None:
            raise MontageContractError("deleted evidence cannot claim a final frame or delta")
        return
    if final is None:
        raise MontageContractError("retained evidence requires a final frame")
    if document["delta_from_proposal_frames"] != final - proposed:
        raise MontageContractError("proposal delta is inconsistent")
    if document["delta_from_review_frames"] != final - reviewed:
        raise MontageContractError("review delta is inconsistent")
    if disposition == "UNCHANGED" and final != reviewed:
        raise MontageContractError("UNCHANGED evidence must retain the review frame")
    if disposition == "MOVED" and final == reviewed:
        raise MontageContractError("MOVED evidence must change the review frame")


def _preference(document: dict[str, Any]) -> None:
    _ids(document["source_evidence_sha256s"], "source evidence")
    keys = []
    minimum = document["minimum_samples"]
    for row in document["timing_preferences"]:
        keys.append((row["style_profile_id"], row["event_type"], row["music_anchor_kind"]))
        if row["retained_count"] + row["deleted_count"] != row["sample_count"]:
            raise MontageContractError("preference counts disagree with sample_count")
        if row["moved_count"] > row["retained_count"]:
            raise MontageContractError("moved_count exceeds retained_count")
        if row["accepted_rate_milli"] != row["retained_count"] * 1000 // row["sample_count"]:
            raise MontageContractError("accepted_rate_milli is inconsistent")
        ready = row["state"] == "ADVISORY_READY_FOR_HUMAN_REVIEW"
        if ready != (row["sample_count"] >= minimum):
            raise MontageContractError("preference state disagrees with minimum_samples")
        if not ready and (row["median_delta_frames"] is not None or row["mean_delta_milli_frames"] is not None):
            raise MontageContractError("insufficient preference cannot claim timing deltas")
    if len(keys) != len(set(keys)):
        raise MontageContractError("duplicate preference dimension")


def _handoff(document: dict[str, Any]) -> None:
    _ids((row["composition_id"] for row in document["compositions"]), "handoff compositions")
    operations = []
    for row in document["compositions"]:
        _ids((op["preset_id"] for op in row["operations"]), "handoff preset operations")
        operations.extend(op["operation_id"] for op in row["operations"])
    _ids(operations, "handoff operations")


def parse_bvp_montage_skill_input(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "input", _input)


def parse_montage_proposal_bundle(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "proposal", _proposal)


def parse_montage_approved_plan(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "plan", _plan)


def parse_montage_human_edit_evidence(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "evidence", _evidence)


def parse_montage_preference_profile(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "preference", _preference)


def parse_montage_resolve_handoff(value: Mapping[str, Any]) -> MontageContractDocument:
    return _parse(value, "handoff", _handoff)


def admit_montage_proposal_bundle(
    bvp_input: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    allowed_preset_ids: Iterable[str],
) -> MontageContractDocument:
    incoming = parse_bvp_montage_skill_input(bvp_input).to_dict()
    candidate = parse_montage_proposal_bundle(proposal).to_dict()
    for field in (
        "project_id", "production_job_id", "timeline_rate", "music_asset_id",
        "style_profile_id", "preset_manifest_sha256",
    ):
        if candidate[field] != incoming[field]:
            raise MontageContractError(f"proposal {field} differs from BVP input")
    coordinates = {
        (row["source_start_frame"], row["source_end_frame_exclusive"], event)
        for row in incoming["candidates"]
        for event in row["event_refs"]
    }
    for row in candidate["placements"]:
        if row["source_asset_id"] != incoming["source_asset_id"]:
            raise MontageContractError("proposal source asset differs from BVP input")
        if row["source_rate"] != incoming["source_rate"]:
            raise MontageContractError("proposal source rate differs from BVP input")
        if (row["source_start_frame"], row["source_end_frame_exclusive"], row["event_ref"]) not in coordinates:
            raise MontageContractError("proposal placement is not bound to an input candidate")
    used = {
        operation["preset_id"]
        for composition in candidate["compositions"]
        for operation in composition["operations"]
    }
    if not used.issubset(set(allowed_preset_ids)):
        raise MontageContractError("proposal references a preset absent from the active manifest")
    return MontageContractDocument(candidate)


def admit_montage_approved_plan(
    proposal: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> MontageContractDocument:
    proposal_doc = parse_montage_proposal_bundle(proposal).to_dict()
    plan_doc = parse_montage_approved_plan(plan).to_dict()
    if plan_doc["source_proposal_sha256"] != proposal_doc["proposal_sha256"]:
        raise MontageContractError("approved plan proposal binding mismatch")
    proposal_placements = {row["placement_id"]: row for row in proposal_doc["placements"]}
    compositions = {row["composition_id"]: row for row in proposal_doc["compositions"]}
    handled = set()
    for row in plan_doc["placements"]:
        placement = row["placement"]
        placement_id = placement["placement_id"]
        if proposal_placements.get(placement_id) != placement:
            raise MontageContractError("approved placement differs from proposal")
        handled.add(placement_id)
        for composition_id in row["accepted_composition_ids"]:
            composition = compositions.get(composition_id)
            if composition is None or composition["placement_id"] != placement_id:
                raise MontageContractError("approved plan accepts an unrelated composition")
    for row in plan_doc["rejected"]:
        placement = proposal_placements.get(row["placement_id"])
        if placement is None:
            raise MontageContractError("approved plan rejects an unknown placement")
        if row["proposed_target_timeline_frame"] != placement["target_timeline_frame"]:
            raise MontageContractError("rejected frame differs from proposal")
        handled.add(row["placement_id"])
    if handled != set(proposal_placements):
        raise MontageContractError("approved plan must decide every proposal placement")
    return MontageContractDocument(plan_doc)


def admit_montage_human_edit_evidence(
    proposal: Mapping[str, Any],
    plan: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> MontageContractDocument:
    proposal_doc = parse_montage_proposal_bundle(proposal).to_dict()
    plan_doc = admit_montage_approved_plan(proposal_doc, plan).to_dict()
    evidence_doc = parse_montage_human_edit_evidence(evidence).to_dict()
    if evidence_doc["source_proposal_sha256"] != proposal_doc["proposal_sha256"]:
        raise MontageContractError("evidence proposal binding mismatch")
    if evidence_doc["source_approved_plan_sha256"] != plan_doc["plan_sha256"]:
        raise MontageContractError("evidence plan binding mismatch")
    placements = {row["placement_id"]: row for row in proposal_doc["placements"]}
    placement = placements.get(evidence_doc["placement_id"])
    if placement is None:
        raise MontageContractError("evidence references an unknown placement")
    if evidence_doc["style_profile_id"] != proposal_doc["style_profile_id"]:
        raise MontageContractError("evidence style profile binding mismatch")
    if evidence_doc["event_type"] != placement["event_type"]:
        raise MontageContractError("evidence event type binding mismatch")
    anchors = {row["anchor_id"]: row for row in proposal_doc["music_anchors"]}
    if evidence_doc["music_anchor_kind"] != anchors[placement["target_music_anchor_id"]]["kind"]:
        raise MontageContractError("evidence music anchor binding mismatch")
    if evidence_doc["proposed_target_timeline_frame"] != placement["target_timeline_frame"]:
        raise MontageContractError("evidence proposed frame binding mismatch")
    approved = {
        row["placement"]["placement_id"]: row for row in plan_doc["placements"]
    }.get(evidence_doc["placement_id"])
    expected_review = (
        approved["final_target_timeline_frame"]
        if approved is not None
        else placement["target_timeline_frame"]
    )
    if evidence_doc["human_review_target_timeline_frame"] != expected_review:
        raise MontageContractError("evidence review frame binding mismatch")
    return MontageContractDocument(evidence_doc)

def admit_montage_resolve_handoff(
    proposal: Mapping[str, Any],
    plan: Mapping[str, Any],
    handoff: Mapping[str, Any],
) -> MontageContractDocument:
    proposal_doc = parse_montage_proposal_bundle(proposal).to_dict()
    plan_doc = admit_montage_approved_plan(proposal_doc, plan).to_dict()
    handoff_doc = parse_montage_resolve_handoff(handoff).to_dict()
    if handoff_doc["source_proposal_sha256"] != proposal_doc["proposal_sha256"]:
        raise MontageContractError("handoff proposal binding mismatch")
    if handoff_doc["source_approved_plan_sha256"] != plan_doc["plan_sha256"]:
        raise MontageContractError("handoff plan binding mismatch")
    if handoff_doc["preset_manifest_sha256"] != proposal_doc["preset_manifest_sha256"]:
        raise MontageContractError("handoff preset manifest binding mismatch")
    proposal_compositions = {
        row["composition_id"]: row for row in proposal_doc["compositions"]
    }
    accepted_ids = {
        composition_id
        for row in plan_doc["placements"]
        for composition_id in row["accepted_composition_ids"]
    }
    expected = [proposal_compositions[composition_id] for composition_id in accepted_ids]
    actual = handoff_doc["compositions"]
    if {row["composition_id"] for row in actual} != accepted_ids:
        raise MontageContractError("handoff composition set differs from approved plan")
    if any(row != proposal_compositions[row["composition_id"]] for row in actual):
        raise MontageContractError("handoff composition differs from proposal")
    return MontageContractDocument(handoff_doc)
