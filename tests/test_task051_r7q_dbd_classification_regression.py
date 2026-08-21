from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_game_information_classification import classify_game_information
from ai_video_production.dbd_kamigame_candidate_bridge import load_kamigame_candidates


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("トーリー", GameKnowledgeKind.SURVIVOR),
        ("ドワイト", GameKnowledgeKind.SURVIVOR),
        ("ナンシー", GameKnowledgeKind.SURVIVOR),
        ("ネア", GameKnowledgeKind.SURVIVOR),
        ("ハグ", GameKnowledgeKind.KILLER),
        ("ヒルビリー", GameKnowledgeKind.KILLER),
        ("ピッグ", GameKnowledgeKind.KILLER),
        ("ハグ対策", GameKnowledgeKind.KNOWLEDGE),
        ("ヒルビリー対策", GameKnowledgeKind.KNOWLEDGE),
        ("ピッグ対策", GameKnowledgeKind.KNOWLEDGE),
        ("ハディ", GameKnowledgeKind.SURVIVOR),
    ],
)
def test_owner_verified_classification_regression(title: str, expected: GameKnowledgeKind) -> None:
    kind, source, confidence = classify_game_information(
        {"name_ja": title}, source_kind=GameKnowledgeKind.MAP
    )
    assert kind is expected
    assert source in {"KNOWN_ENTITY_MASTER", "ARTICLE_SUFFIX"}
    assert confidence == 1000


def test_article_semantics_win_over_base_killer_name() -> None:
    kind, source, _ = classify_game_information(
        {"name_ja": "ハグ対策"}, source_kind=GameKnowledgeKind.KILLER
    )
    assert kind is GameKnowledgeKind.KNOWLEDGE
    assert source == "ARTICLE_SUFFIX"


def test_known_entity_is_not_overwritten_by_map_source_kind() -> None:
    kind, source, _ = classify_game_information(
        {"name_ja": "ドワイト", "source_section_heading": "各マップ一覧"},
        source_kind=GameKnowledgeKind.MAP,
    )
    assert kind is GameKnowledgeKind.SURVIVOR
    assert source == "KNOWN_ENTITY_MASTER"


def test_bridge_reclassifies_polluted_map_rows_before_review_catalog(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    normalized.mkdir(parents=True)
    rows = [
        {"candidate_id": "legacy-map-dwight", "name_ja": "ドワイト", "source_page_url": "https://kamigame.jp/dbd/page/maps.html"},
        {"candidate_id": "legacy-map-hag-guide", "name_ja": "ハグ対策", "source_page_url": "https://kamigame.jp/dbd/page/maps.html"},
        {"candidate_id": "real-map", "name_ja": "サファケーション・ピット", "source_page_url": "https://kamigame.jp/dbd/page/maps.html"},
    ]
    (normalized / "maps.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    found = {row.candidate_id: row for row in load_kamigame_candidates(tmp_path)}
    assert found["legacy-map-dwight"].knowledge_kind is GameKnowledgeKind.SURVIVOR
    assert found["legacy-map-hag-guide"].knowledge_kind is GameKnowledgeKind.KNOWLEDGE
    assert found["real-map"].knowledge_kind is GameKnowledgeKind.MAP
    assert found["legacy-map-dwight"].details["classification_source"] == "KNOWN_ENTITY_MASTER"
