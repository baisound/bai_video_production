from dataclasses import dataclass
from ai_video_production.dbd_commentary_knowledge import DbDTriviaStore, TriviaCandidateMiner
from ai_video_production.dbd_trivia_operational import (
    TriviaOperationalMetadataStore,
    format_time_range,
    index_transcript_candidates,
)

@dataclass
class Segment:
    segment_id:str
    text:str
    start_seconds:float
    end_seconds:float

@dataclass
class Manifest:
    source_asset_id:str
    segments:tuple

def test_transcript_candidate_time_provenance(tmp_path):
    trivia=DbDTriviaStore(tmp_path/"trivia.sqlite3")
    manifest=Manifest(
        "asset-1",
        (Segment("seg-1","ちなみにパークの効果は条件で発動します。",12.5,15.0),),
    )
    entries=TriviaCandidateMiner().capture_transcript_manifest(trivia,manifest)
    assert entries
    meta=TriviaOperationalMetadataStore(tmp_path/"meta.json")
    assert index_transcript_candidates(
        meta,
        entries=entries,
        transcript=manifest,
        source_video="match.mp4",
        transcript_path="transcript.json",
    )==len(entries)
    row=meta.get(entries[0].trivia_id)
    assert row.source_video=="match.mp4"
    assert format_time_range(row)=="12.50–15.00秒"
