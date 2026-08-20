from __future__ import annotations

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_game_knowledge_catalog import candidate_from_normalized
from ai_video_production.dbd_kamigame_collector import ITEMS_URL, parse_item_page


def test_unknown_source_columns_are_preserved_as_source_sections() -> None:
    html = """
    <html><body><h2>医療キット系アイテム一覧</h2><table>
      <tr><td>救急箱</td><td>Uncommon 〖基礎チャージ量〗24 〖効果〗自己治療</td><td>将来追加された攻略メモ</td></tr>
    </table></body></html>
    """
    rows = parse_item_page(html, page_url=ITEMS_URL)
    assert len(rows) == 1
    row = rows[0]
    assert row["source_effect_ja"] == "自己治療"
    sections = row["source_sections"]
    assert any(section["value"] == "将来追加された攻略メモ" for section in sections)
    assert all({"heading", "label", "value", "order"} <= set(section) for section in sections)


def test_source_sections_survive_review_candidate_normalization() -> None:
    payload = {
        "candidate_id": "item-completeness",
        "name_ja": "救急箱",
        "source_page_url": ITEMS_URL,
        "source_effect_ja": "自己治療",
        "source_sections": [
            {"heading": "医療キット", "label": "追加情報", "value": "未知フィールド", "order": 3}
        ],
    }
    candidate = candidate_from_normalized(payload, GameKnowledgeKind.ITEM)
    assert candidate.details["source_effect_ja"] == "自己治療"
    assert candidate.details["source_sections"][0]["value"] == "未知フィールド"
