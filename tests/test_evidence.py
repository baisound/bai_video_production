from ai_video_production.evidence import EvidenceRecord, EvidenceWriter
from ai_video_production.ids import IdKind, generate_id

def test_evidence_is_append_only_and_masks_secrets(tmp_path):
    job=generate_id(IdKind.JOB); op=generate_id(IdKind.OPERATION)
    writer=EvidenceWriter(tmp_path/"evidence.jsonl")
    first=EvidenceRecord(job,"TEST","pytest",{"api_key":"nope","safe":"ok"},operation_id=op)
    writer.append(first)
    second=EvidenceRecord(job,"TEST","pytest",{"safe":"new"})
    linked=writer.append_superseding(first,second)
    rows=list(writer.iter_records())
    assert len(rows)==2
    assert rows[0]["details"]["api_key"]=="[REDACTED]"
    assert rows[1]["supersedes_evidence_id"]==first.evidence_id==linked.supersedes_evidence_id
