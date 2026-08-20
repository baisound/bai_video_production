from pathlib import Path
from types import SimpleNamespace
import sqlite3

from ai_video_production.dbd_training_review_ui_v2 import (
    _alias_counts,
    _count_rows_in_file,
)

def test_alias_counts(tmp_path):
    db=tmp_path/"knowledge"/"entity-aliases.sqlite"
    db.parent.mkdir()
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE entity_alias(
            entity_id TEXT, knowledge_kind TEXT, alias_text TEXT, alias_type TEXT,
            review_status TEXT, source_ref TEXT)""")
        conn.executemany(
            "INSERT INTO entity_alias VALUES(?,?,?,?,?,?)",
            [
                ("a","PERK","A","OFFICIAL_NAME","CANDIDATE","x"),
                ("b","PERK","B","OFFICIAL_NAME","VERIFIED","x"),
                ("c","KILLER","C","OFFICIAL_NAME","REJECTED","x"),
            ],
        )
    assert _alias_counts(tmp_path)==(3,1,1)

def test_count_rows_in_jsonl_and_csv(tmp_path):
    jsonl=tmp_path/"gold.jsonl"
    jsonl.write_text('{"a":1}\n\n{"a":2}\n',encoding="utf-8")
    csv_path=tmp_path/"gold.csv"
    csv_path.write_text("id,label\n1,a\n2,b\n",encoding="utf-8")
    assert _count_rows_in_file(jsonl)==2
    assert _count_rows_in_file(csv_path)==2
