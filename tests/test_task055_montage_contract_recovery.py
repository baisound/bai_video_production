from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from ai_video_production.montage_contracts import (
    MontageContractError,
    admit_montage_approved_plan,
    admit_montage_human_edit_evidence,
    admit_montage_proposal_bundle,
    admit_montage_resolve_handoff,
    parse_bvp_montage_skill_input,
    parse_montage_approved_plan,
    parse_montage_human_edit_evidence,
    parse_montage_preference_profile,
    parse_montage_proposal_bundle,
    parse_montage_resolve_handoff,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT=Path(__file__).resolve().parents[1]
SCHEMA_SHA256S={
    "bvp-montage-skill-input.schema.json":"511945f24cffaf37b6b0b158e16c9af8fbbfeb2b1f3d4cb48bb4ec49a064ef76",
    "montage-proposal.schema.json":"1b7f33b1af464c7c6f6fb9ecee35c3674d6f5b81e4ec16b1488f6eb3d6a48137",
    "montage-approved-plan.schema.json":"4bce10cf3a29578bde6e0d1708a7c07179ca2da7626220da72fa85cdf0684fa3",
    "montage-human-edit-evidence.schema.json":"112d557f0a5e377a9049bfd3625f636165b47c888fcdd8a21f6255f463f09307",
    "montage-preference-profile.schema.json":"7d89b0973ca69fef66aadb49f913332dc6df7928c95709c7fb05725364bbb412",
    "montage-resolve-handoff.schema.json":"c06d6506bf8618c813ac2f8114b790d275205cf89def5103459f4d5814d00910",
}


def _sign(body, field):
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _input():
    return _sign({
        "schema_version":"1.0.0",
        "record_kind":"BVP_MONTAGE_SKILL_INPUT",
        "project_id":"proj-test",
        "production_job_id":"JOB-01J00000000000000000000000",
        "match_id":"match-001",
        "source_asset_id":"ASSET-01J00000000000000000000001",
        "source_rate":{"numerator":60,"denominator":1},
        "timeline_rate":{"numerator":60,"denominator":1},
        "music_asset_id":"ASSET-01J00000000000000000000002",
        "style_profile_id":"dbd-aggressive",
        "preset_manifest_sha256":"sha256:"+"1"*64,
        "editing_plan_sha256":"sha256:"+"2"*64,
        "candidates":[{
            "candidate_id":"candidate-001",
            "source_start_frame":120,
            "source_end_frame_exclusive":180,
            "event_refs":["event-001"],
            "reason_codes":["CANONICAL_EVENT","PALLET_DROP"],
            "highlight_score_milli":900,
            "confidence_milli":920,
            "human_review_required":False,
        }],
        "media_bytes_included":False,
        "absolute_host_paths_included":False,
        "external_skill_output_untrusted":True,
        "timeline_mutation_authorized":False,
        "resolve_write_authorized":False,
    },"input_sha256")


def _proposal():
    return _sign({
        "schema_version":"1.0.0",
        "record_kind":"MONTAGE_PROPOSAL_BUNDLE",
        "project_id":"proj-test",
        "production_job_id":"JOB-01J00000000000000000000000",
        "timeline_rate":{"numerator":60,"denominator":1},
        "music_asset_id":"ASSET-01J00000000000000000000002",
        "style_profile_id":"dbd-aggressive",
        "preset_manifest_sha256":"sha256:"+"1"*64,
        "external_generator":{
            "generator_id":"davinci-beat-sync-montage-director",
            "version":"0.6.0",
            "sha256":"sha256:"+"3"*64,
        },
        "generated_at":"2026-08-24T00:00:00Z",
        "music_anchors":[{
            "anchor_id":"anchor-001",
            "timeline_frame":600,
            "bar_index":4,
            "beat_index":1,
            "kind":"DROP",
            "strength_milli":980,
        }],
        "placements":[{
            "placement_id":"placement-001",
            "source_asset_id":"ASSET-01J00000000000000000000001",
            "source_rate":{"numerator":60,"denominator":1},
            "source_start_frame":120,
            "source_end_frame_exclusive":180,
            "source_anchor_frame":149,
            "event_ref":"event-001",
            "event_type":"PALLET_DROP",
            "target_music_anchor_id":"anchor-001",
            "target_timeline_frame":600,
            "highlight_score_milli":900,
            "confidence_milli":920,
            "reason_codes":["BEAT_EVENT_ALIGNMENT","PALLET_DROP"],
        }],
        "compositions":[{
            "composition_id":"composition-001",
            "placement_id":"placement-001",
            "operations":[{
                "operation_id":"operation-001",
                "preset_id":"preset.zoom.punch",
                "family":"zoom",
                "offset_frames":0,
                "intensity_milli":800,
            }],
            "complexity_score":300,
            "visibility_score":850,
        }],
        "external_input_untrusted":True,
        "human_review_required":True,
        "timeline_mutation_authorized":False,
        "resolve_write_authorized":False,
        "automatic_learning_promotion_authorized":False,
    },"proposal_sha256")


def _plan(proposal):
    placement=deepcopy(proposal["placements"][0])
    return _sign({
        "plan_version":"1.0.0",
        "task_owner":"TASK-055",
        "source_proposal_sha256":proposal["proposal_sha256"],
        "approved_by":"owner-local",
        "placements":[{
            "placement":placement,
            "proposed_target_timeline_frame":600,
            "final_target_timeline_frame":602,
            "delta_frames":2,
            "accepted_composition_ids":["composition-001"],
        }],
        "rejected":[],
        "review_do_not_learn_placement_ids":[],
        "approval_state":"APPROVED",
        "ready_for_timeline_projection":True,
        "automatic_timeline_mutation_authorized":False,
        "resolve_write_authorized":False,
    },"plan_sha256")


def _evidence(proposal, plan):
    return _sign({
        "evidence_version":"1.0.0",
        "task_owner":"TASK-055",
        "source_proposal_sha256":proposal["proposal_sha256"],
        "source_approved_plan_sha256":plan["plan_sha256"],
        "placement_id":"placement-001",
        "style_profile_id":"dbd-aggressive",
        "event_type":"PALLET_DROP",
        "music_anchor_kind":"DROP",
        "proposed_target_timeline_frame":600,
        "human_review_target_timeline_frame":602,
        "final_target_timeline_frame":604,
        "disposition":"MOVED",
        "delta_from_proposal_frames":4,
        "delta_from_review_frames":2,
        "preset_families":["zoom"],
        "do_not_learn":False,
        "raw_media_included":False,
        "absolute_host_path_included":False,
        "automatic_learning_promotion_authorized":False,
        "automatic_edit_plan_mutation_authorized":False,
    },"evidence_sha256")


def _preference(evidence):
    return _sign({
        "profile_version_contract":"1.0.0",
        "task_owner":"TASK-055",
        "future_generic_learning_owner":"TASK-029",
        "future_holdout_promotion_owner":"TASK-019",
        "profile_id":"montage-owner-local",
        "profile_version":"1.0.0",
        "source_evidence_sha256s":[evidence["evidence_sha256"]],
        "minimum_samples":3,
        "timing_preferences":[{
            "style_profile_id":"dbd-aggressive",
            "event_type":"PALLET_DROP",
            "music_anchor_kind":"DROP",
            "sample_count":10,
            "retained_count":8,
            "moved_count":3,
            "deleted_count":2,
            "accepted_rate_milli":800,
            "median_delta_frames":2,
            "mean_delta_milli_frames":2200,
            "state":"ADVISORY_READY_FOR_HUMAN_REVIEW",
        }],
        "advisory_only":True,
        "human_review_required_before_use":True,
        "automatic_profile_write_authorized":False,
        "automatic_edit_plan_mutation_authorized":False,
        "automatic_promotion_authorized":False,
    },"profile_sha256")


def _handoff(proposal, plan):
    return _sign({
        "handoff_version":"1.0.0",
        "task_owner":"TASK-055",
        "existing_resolve_assembly_owner":"TASK-010",
        "canonical_timeline_mapping_owner":"TASK-022",
        "source_proposal_sha256":proposal["proposal_sha256"],
        "source_approved_plan_sha256":plan["plan_sha256"],
        "source_projection_sha256":"sha256:"+"4"*64,
        "timeline_mapping_sha256":"sha256:"+"5"*64,
        "preset_manifest_sha256":"sha256:"+"1"*64,
        "compositions":deepcopy(proposal["compositions"]),
        "required_native_capability":"RESOLVE_FUSION_TEMPLATE_APPLICATION",
        "native_runtime_capability_status":"NOT_CONFIRMED",
        "runtime_qa_status":"NOT_RUN",
        "external_write_authorization_required":True,
        "resolve_write_authorized":False,
        "preset_installation_authorized":False,
    },"handoff_sha256")


def _resign(document, field):
    body=deepcopy(document)
    body.pop(field)
    return _sign(body,field)


def test_recovered_source_main_schemas_keep_exact_hash_and_package_mirror():
    for name, expected_sha256 in SCHEMA_SHA256S.items():
        canonical=(ROOT/"schemas"/name).read_bytes()
        packaged=(ROOT/"src/ai_video_production/schema_resources"/name).read_bytes()
        assert canonical == packaged
        committed_bytes=canonical.replace(b"\r\n",b"\n")
        assert hashlib.sha256(committed_bytes).hexdigest() == expected_sha256


def test_all_recovered_contracts_parse_and_round_trip():
    incoming=_input()
    proposal=_proposal()
    plan=_plan(proposal)
    evidence=_evidence(proposal,plan)
    preference=_preference(evidence)
    handoff=_handoff(proposal,plan)
    assert parse_bvp_montage_skill_input(incoming).to_dict()==incoming
    assert parse_montage_proposal_bundle(proposal).to_dict()==proposal
    assert parse_montage_approved_plan(plan).to_dict()==plan
    assert parse_montage_human_edit_evidence(evidence).to_dict()==evidence
    assert parse_montage_preference_profile(preference).to_dict()==preference
    assert parse_montage_resolve_handoff(handoff).to_dict()==handoff


def test_proposal_admission_binds_input_and_active_preset_manifest():
    incoming=_input()
    proposal=_proposal()
    assert admit_montage_proposal_bundle(
        incoming,proposal,allowed_preset_ids={"preset.zoom.punch"}
    ).to_dict()==proposal
    with pytest.raises(MontageContractError,match="preset absent"):
        admit_montage_proposal_bundle(incoming,proposal,allowed_preset_ids=set())
    changed=deepcopy(proposal)
    changed["music_asset_id"]="ASSET-01J00000000000000000000003"
    changed=_resign(changed,"proposal_sha256")
    with pytest.raises(MontageContractError,match="music_asset_id differs"):
        admit_montage_proposal_bundle(
            incoming,changed,allowed_preset_ids={"preset.zoom.punch"}
        )
    changed=deepcopy(proposal)
    changed["placements"][0]["source_rate"]={"numerator":30,"denominator":1}
    changed=_resign(changed,"proposal_sha256")
    with pytest.raises(MontageContractError,match="source rate differs"):
        admit_montage_proposal_bundle(
            incoming,changed,allowed_preset_ids={"preset.zoom.punch"}
        )


def test_resolve_handoff_is_limited_to_exact_approved_compositions():
    proposal=_proposal()
    plan=_plan(proposal)
    handoff=_handoff(proposal,plan)
    assert admit_montage_resolve_handoff(proposal,plan,handoff).to_dict()==handoff
    wrong=deepcopy(handoff)
    wrong["compositions"][0]["operations"][0]["intensity_milli"]=700
    wrong=_resign(wrong,"handoff_sha256")
    with pytest.raises(MontageContractError,match="composition differs"):
        admit_montage_resolve_handoff(proposal,plan,wrong)


def test_plan_and_human_evidence_are_exactly_cross_bound():
    proposal=_proposal()
    plan=_plan(proposal)
    evidence=_evidence(proposal,plan)
    assert admit_montage_approved_plan(proposal,plan).to_dict()==plan
    assert admit_montage_human_edit_evidence(proposal,plan,evidence).to_dict()==evidence
    wrong=deepcopy(evidence)
    wrong["human_review_target_timeline_frame"]=603
    wrong["delta_from_review_frames"]=1
    wrong=_resign(wrong,"evidence_sha256")
    with pytest.raises(MontageContractError,match="review frame binding"):
        admit_montage_human_edit_evidence(proposal,plan,wrong)


@pytest.mark.parametrize(
    ("builder","field","mutate","message"),
    [
        (_input,"input_sha256",lambda row: row.update(input_sha256="sha256:"+"0"*64),"hash mismatch"),
        (_input,"input_sha256",lambda row: row["source_rate"].update(numerator=120,denominator=2),"reduced rational"),
        (_proposal,"proposal_sha256",lambda row: row["placements"][0].update(source_anchor_frame=999),"outside its source range"),
    ],
)
def test_malformed_or_ambiguous_contracts_fail_closed(builder,field,mutate,message):
    document=builder()
    mutate(document)
    if "hash mismatch" not in message:
        document=_resign(document,field)
    parser=parse_bvp_montage_skill_input if field=="input_sha256" else parse_montage_proposal_bundle
    with pytest.raises(MontageContractError,match=message):
        parser(document)


def test_learning_profile_is_advisory_and_count_consistent():
    proposal=_proposal()
    plan=_plan(proposal)
    evidence=_evidence(proposal,plan)
    profile=_preference(evidence)
    assert parse_montage_preference_profile(profile).to_dict()==profile
    invalid=deepcopy(profile)
    invalid["timing_preferences"][0]["accepted_rate_milli"]=900
    invalid=_resign(invalid,"profile_sha256")
    with pytest.raises(MontageContractError,match="accepted_rate"):
        parse_montage_preference_profile(invalid)


def test_authority_flags_remain_false_across_every_output():
    proposal=_proposal()
    plan=_plan(proposal)
    evidence=_evidence(proposal,plan)
    preference=_preference(evidence)
    handoff=_handoff(proposal,plan)
    assert proposal["timeline_mutation_authorized"] is False
    assert proposal["resolve_write_authorized"] is False
    assert proposal["automatic_learning_promotion_authorized"] is False
    assert plan["automatic_timeline_mutation_authorized"] is False
    assert plan["resolve_write_authorized"] is False
    assert evidence["automatic_learning_promotion_authorized"] is False
    assert preference["automatic_promotion_authorized"] is False
    assert handoff["resolve_write_authorized"] is False
    assert handoff["runtime_qa_status"]=="NOT_RUN"
