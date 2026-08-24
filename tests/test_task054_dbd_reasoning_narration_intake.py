from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision, DatasetRowDisposition, DatasetSplit, DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest, RightsDecision,
)
from ai_video_production.dbd_reasoning_narration_intake import (
    DbDReasoningNarrationIntakeCandidate, INTAKE_STATE, NarrationDisposition,
    NarrationRole, admit_dbd_reasoning_narration_intake, validate_narration_intake_rights,
)
from ai_video_production.serialization import sha256_bytes

SHA="sha256:"+"a"*64; HEX="a"*64


def _candidate(**changes):
    text="チェイス開始、板へ向かいます"
    values=dict(segment_id="SEG-"+"0"*26,rights_candidate_id="CAND-R2D"+"0"*23,
        rights_manifest_sha256=SHA,match_id="MATCH-"+"0"*26,event_ids=("GEVT-"+"0"*26,),
        context_sha256=SHA,source_video_ref=f"media://sha256/{HEX}",source_audio_ref=f"media://sha256/{HEX}",
        source_start_us=1_000_000,source_end_us_exclusive=2_000_000,speaker_ref=f"speaker://sha256/{HEX}",
        asr_revision=1,asr_sha256=SHA,diarization_revision=1,diarization_sha256=SHA,
        original_transcript_sha256=SHA,corrected_transcript_sha256=sha256_bytes(text.encode()),redacted_transcript=text,
        role=NarrationRole.PLAY_BY_PLAY,patch_version="9.1.0",human_review_ref=f"human-review://sha256/{HEX}",
        human_review_sha256=SHA,issue_codes=(),disposition=NarrationDisposition.ELIGIBLE_CANDIDATE)
    values.update(changes); return DbDReasoningNarrationIntakeCandidate(**values)


def test_play_by_play_candidate_is_exact_but_never_adopted():
    item=_candidate(); assert admit_dbd_reasoning_narration_intake(item.to_dict())==item
    assert item.intake_state==INTAKE_STATE and not hasattr(item,"adopt")
    assert "original_transcript" not in item.to_dict()


@pytest.mark.parametrize(("role","issues","disposition"),[
    (NarrationRole.UNCERTAIN,(),NarrationDisposition.NEEDS_REVIEW),
    (NarrationRole.ANALYSIS,("MUSIC_BLEED",),NarrationDisposition.NEEDS_REVIEW),
    (NarrationRole.TACTICAL,("UNSUPPORTED_TACTICAL_CLAIM",),NarrationDisposition.REJECTED),
    (NarrationRole.PLAY_BY_PLAY,("PII_OR_SECRET",),NarrationDisposition.REJECTED)])
def test_quality_and_privacy_issues_fail_closed(role,issues,disposition):
    assert _candidate(role=role,issue_codes=issues,disposition=disposition)
    with pytest.raises(ValueError,match="disposition"): _candidate(role=role,issue_codes=issues)


def test_ranges_revisions_event_order_refs_and_digest_are_strict():
    with pytest.raises(ValueError,match="source range"): _candidate(source_end_us_exclusive=1_000_000)
    with pytest.raises(ValueError,match="positive"): _candidate(asr_revision=0)
    with pytest.raises(ValueError,match="event_ids"): _candidate(event_ids=("GEVT-"+"1"*26,"GEVT-"+"0"*26))
    with pytest.raises(ValueError,match="body-free"): _candidate(speaker_ref="speaker://John-Doe")
    with pytest.raises(ValueError,match="digest"): _candidate(redacted_transcript="different")
    leaked="api_key=sk-live-secret"
    with pytest.raises(ValueError,match="DLP"):
        _candidate(redacted_transcript=leaked,corrected_transcript_sha256=sha256_bytes(leaked.encode()))


def test_rehashed_semantic_and_shape_forges_are_rejected():
    for field,value in (("schema_version","9.9.9"),("disposition","REJECTED"),("extra",True)):
        record=json.loads(json.dumps(_candidate().to_dict())); record[field]=value
        body={k:v for k,v in record.items() if k!="intake_sha256"}
        record["intake_sha256"]=sha256_bytes(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
        with pytest.raises((ValueError,TypeError)): admit_dbd_reasoning_narration_intake(record)


def test_schema_mirror_and_runtime_conformance():
    root=Path(__file__).parents[1]; canonical=root/"schemas/dbd-reasoning-narration-intake.schema.json"
    mirror=root/"src/ai_video_production/schema_resources/dbd-reasoning-narration-intake.schema.json"
    assert canonical.read_bytes()==mirror.read_bytes()
    assert not list(Draft202012Validator(json.loads(canonical.read_text())).iter_errors(_candidate().to_dict()))
    numeric=_candidate().to_dict()
    numeric["segment_id"]=42
    assert list(Draft202012Validator(json.loads(canonical.read_text())).iter_errors(numeric))


def _rights_manifest(**changes):
    values=dict(candidate_id="CAND-R2D"+"0"*23,candidate_sha256=SHA,lineage_sha256=SHA,
        human_review_sha256=SHA,human_review_ref=f"human-review://sha256/{HEX}",match_id="MATCH-"+"0"*26,
        source_group_id="source-group-1",source_ref=f"media://sha256/{HEX}",split=DatasetSplit.TRAIN,
        patch_version="9.1.0",locale="ja-JP",rights_decision=RightsDecision.ADMITTED_FOR_TRAINING,
        rights_ref=f"rights://sha256/{HEX}",consent_decision=ConsentDecision.EXPLICIT_TRAINING,
        consent_ref=f"consent://sha256/{HEX}",provenance_ref=f"provenance://sha256/{HEX}",
        disposition=DatasetRowDisposition.ELIGIBLE_CANDIDATE,reason_codes=())
    values.update(changes)
    return DbDReasoningDatasetRightsManifest("MAN-"+"0"*26,1,(DbDReasoningDatasetRightsEntry(**values),))


def test_rights_manifest_membership_and_coordinates_are_revalidated():
    manifest=_rights_manifest(); digest=manifest.to_dict()["rights_manifest_sha256"]
    candidate=_candidate(rights_manifest_sha256=digest)
    assert validate_narration_intake_rights(candidate,manifest)==candidate
    with pytest.raises(ValueError,match="digest crossing"):
        validate_narration_intake_rights(_candidate(),manifest)
    other=f"media://sha256/{'b'*64}"
    with pytest.raises(ValueError,match="coordinate crossing"):
        validate_narration_intake_rights(_candidate(rights_manifest_sha256=digest,source_video_ref=other),manifest)
    blocked=_rights_manifest(rights_decision=RightsDecision.UNKNOWN,
        disposition=DatasetRowDisposition.NEEDS_REVIEW,reason_codes=("RIGHTS_UNKNOWN",))
    with pytest.raises(ValueError,match="not eligible"):
        validate_narration_intake_rights(_candidate(rights_manifest_sha256=blocked.to_dict()["rights_manifest_sha256"]),blocked)
