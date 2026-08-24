from __future__ import annotations

from dataclasses import replace
import pytest

from ai_video_production.dbd_reasoning_dataset_leakage import DbDReasoningDatasetLeakageAuditor,LeakageAuditStatus,LeakageKind
from ai_video_production.dbd_reasoning_dataset_manifest import ConsentDecision,DatasetRowDisposition,DatasetSplit,DbDReasoningDatasetRightsEntry,DbDReasoningDatasetRightsManifest,RightsDecision
from ai_video_production.dbd_reasoning_narration_intake import DbDReasoningNarrationIntakeCandidate,NarrationDisposition,NarrationRole
from ai_video_production.serialization import canonical_json_bytes,sha256_bytes

SHA="sha256:"+"a"*64; HEX="a"*64

def _entry(index:int,split:DatasetSplit,**changes):
    digit=str(index)
    values=dict(candidate_id="CAND-R2D"+digit*23,candidate_sha256=SHA,lineage_sha256=SHA,human_review_sha256=SHA,
        human_review_ref=f"human-review://sha256/{HEX}",match_id="MATCH-"+digit*26,source_group_id=f"group-{index}",
        source_ref=f"media://sha256/{digit*64}",split=split,patch_version="9.1.0",locale="ja-JP",
        rights_decision=RightsDecision.ADMITTED_FOR_TRAINING,rights_ref=f"rights://sha256/{digit*64}",
        consent_decision=ConsentDecision.EXPLICIT_TRAINING,consent_ref=f"consent://sha256/{digit*64}",
        provenance_ref=f"provenance://sha256/{digit*64}",disposition=DatasetRowDisposition.ELIGIBLE_CANDIDATE,reason_codes=())
    values.update(changes); return DbDReasoningDatasetRightsEntry(**values)

def _manifest(*entries): return DbDReasoningDatasetRightsManifest("MAN-"+"0"*26,1,entries)

def _segment(index:int,entry,manifest,text:str):
    digest=sha256_bytes(text.encode()); digit=str(index)
    return DbDReasoningNarrationIntakeCandidate(segment_id="SEG-"+digit*26,rights_candidate_id=entry.candidate_id,
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],match_id=entry.match_id,event_ids=("GEVT-"+digit*26,),
        context_sha256=SHA,source_video_ref=entry.source_ref,source_audio_ref=entry.source_ref,source_start_us=index*1000,
        source_end_us_exclusive=index*1000+500,speaker_ref=f"speaker://sha256/{digit*64}",asr_revision=1,asr_sha256=SHA,
        diarization_revision=1,diarization_sha256=SHA,original_transcript_sha256=SHA,corrected_transcript_sha256=digest,
        redacted_transcript=text,role=NarrationRole.PLAY_BY_PLAY,patch_version="9.1.0",human_review_ref=entry.human_review_ref,
        human_review_sha256=entry.human_review_sha256,issue_codes=(),disposition=NarrationDisposition.ELIGIBLE_CANDIDATE)

def test_clean_two_split_audit_passes_without_adoption_authority():
    a=_entry(1,DatasetSplit.TRAIN); b=_entry(2,DatasetSplit.TEST); manifest=_manifest(a,b)
    report=DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(1,a,manifest,"発電機を修理しています"),_segment(2,b,manifest,"キラーが窓を越えました")))
    assert report.status is LeakageAuditStatus.PASS and report.findings==()
    assert report.audit_state=="EVIDENCE_ONLY_NO_ADOPTION" and not hasattr(report,"adopt")

def test_one_split_is_not_confirmed():
    a=_entry(1,DatasetSplit.TRAIN); manifest=_manifest(a)
    assert DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(1,a,manifest,"チェイスを開始します"),)).status is LeakageAuditStatus.NOT_CONFIRMED

def test_exact_and_long_phrase_cross_split_leakage_fail():
    a=_entry(1,DatasetSplit.TRAIN); b=_entry(2,DatasetSplit.TEST); manifest=_manifest(a,b)
    exact="これは十分に長い同一実況テキストでクロススプリット漏洩を検出します"
    report=DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(1,a,manifest,exact),_segment(2,b,manifest,exact)))
    assert report.status is LeakageAuditStatus.FAIL and report.findings[0].kind is LeakageKind.EXACT_TRANSCRIPT_DUPLICATE
    left="開始"+"非常に長い共通実況フレーズをここへ配置して漏洩を確実に検出します"+"終了"
    right="別"+"非常に長い共通実況フレーズをここへ配置して漏洩を確実に検出します"+"末尾"
    report=DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(1,a,manifest,left),_segment(2,b,manifest,right)))
    assert any(x.kind is LeakageKind.PHRASE_OVERLAP for x in report.findings)

def test_match_crossing_and_input_forges_fail_closed():
    a=_entry(1,DatasetSplit.TRAIN); b=_entry(2,DatasetSplit.TEST,match_id=a.match_id); manifest=_manifest(a,b)
    report=DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(1,a,manifest,"短い実況A"),_segment(2,b,manifest,"短い実況B")))
    assert any(x.kind is LeakageKind.MATCH_SPLIT for x in report.findings)
    with pytest.raises(ValueError,match="sorted"):
        DbDReasoningDatasetLeakageAuditor.audit(manifest,(_segment(2,b,manifest,"短い実況B"),_segment(1,a,manifest,"短い実況A")))
    forged=_segment(1,a,manifest,"短い実況A"); object.__setattr__(forged,"rights_manifest_sha256",SHA)
    with pytest.raises(ValueError): DbDReasoningDatasetLeakageAuditor.audit(manifest,(forged,))

def test_report_is_body_free_and_deterministic():
    a=_entry(1,DatasetSplit.TRAIN); b=_entry(2,DatasetSplit.TEST); manifest=_manifest(a,b); text="同じ実況"
    segments=(_segment(1,a,manifest,text),_segment(2,b,manifest,text)); first=DbDReasoningDatasetLeakageAuditor.audit(manifest,segments)
    assert first.audited_segments_sha256==sha256_bytes(canonical_json_bytes([item.to_dict() for item in segments]))
    assert first.to_dict()==DbDReasoningDatasetLeakageAuditor.audit(manifest,segments).to_dict()
    assert text not in str(first.to_dict())
