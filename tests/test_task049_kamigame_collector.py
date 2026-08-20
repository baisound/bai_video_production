from __future__ import annotations

from pathlib import Path
import hashlib

from ai_video_production.dbd_kamigame_collector import (
    FetchReceipt,
    KILLER_PERKS_URL,
    KILLERS_URL,
    SURVIVOR_PERKS_URL,
    ITEMS_URL, ADDONS_URL, MAPS_URL,
    KamigameDbDKnowledgeCollector,
    discover_next_pages,
    parse_killer_detail_page,
    parse_killer_list_page,
    parse_perk_page,
    parse_map_detail_page,
)


SURVIVOR_HTML = """
<html><body><table><tr><th>パーク</th><th>詳細</th></tr>
<tr><td><a href='/dbd/page/111.html'>デッド・ハード</a><a href='/dbd/page/111.html'>(デッハ)</a></td>
<td>〖所有者〗 <a href='/dbd/page/owner.html'>デイビッド</a> 〖優先度〗★★★★☆〖効果〗
フックから外されたあと0.5秒我慢を得る。〖一致するカテゴリ〗 <a href='/dbd/cat/chase'>チェイス補助</a></td></tr>
</table><a href='?page=2'>次へ</a></body></html>
"""

KILLER_PERK_HTML = """
<html><body><table><tr><td><a href='/dbd/page/222.html'>野蛮な力</a><a href='/dbd/page/222.html'>(板壊し)</a></td>
<td>〖所有者〗 <a href='/dbd/page/trapper.html'>トラッパー</a> 〖優先度〗★★★★☆〖効果〗破壊速度が20%上昇。〖一致するカテゴリ〗 <a href='/dbd/cat/chase'>チェイス補助</a></td></tr></table></body></html>
"""

KILLER_HTML = """
<html><body><table><tr><th>キラー</th><th>ステータス</th><th>固有パーク</th></tr>
<tr><td><a href='/dbd/page/trapper-detail.html'>トラッパー</a></td>
<td>移動速度：4.6m/s 脅威範囲：32m 背の高さ：高い</td>
<td><a href='/dbd/page/a.html'>不安の元凶</a> <a href='/dbd/page/b.html'>野蛮な力</a> <a href='/dbd/page/c.html'>興奮</a></td></tr>
</table></body></html>
"""


ITEM_HTML = """<html><body><h2>医療キット系アイテム一覧</h2><table><tr><td>救急箱</td><td>Uncommon 〖基礎チャージ量〗24 〖効果〗自己治療</td></tr></table></body></html>"""
ADDON_HTML = """<html><body><h2>ヒルビリーのアドオン一覧</h2><table><tr><td><img src='/boot.png'>親父のブーツ</td><td>Rare 〖効果〗旋回性能上昇</td></tr></table></body></html>"""
MAP_HTML = """<html><body><h2>各マップ個別一覧</h2><table><tr><td><a href='/dbd/page/map1.html'>サファケーション・ピット</a> <a href='/dbd/page/realm1.html'>マクミラン・エステート</a></td><td>室外面積大板最大19枚</td></tr></table></body></html>"""

MAP_DETAIL_HTML = """<html><body><h2>サファケーション・ピットの見取り図</h2><img src="https://lh3.googleusercontent.com/map.png"><h2>サファケーション・ピットの特徴</h2><table><tr><th>領域名</th><th>オファリング</th></tr><tr><td><a href="/dbd/page/realm1.html">マクミラン・エステート</a></td><td><a href="/dbd/page/offering.html">マクミランの指骨</a></td></tr><tr><td>19~19枚</td><td>10240㎡</td><td>大</td></tr></table><p>特徴・固有オブジェクト 発電機が上下に固まりやすい 有利度 サバ微有利 板 面積 広さ</p></body></html>"""

DETAIL_HTML = """
<html><body><h1>トラッパー</h1><h2>特殊能力</h2><p>罠を設置する。</p><h2>アドオン一覧</h2><p>罠を強化する。</p></body></html>
"""


def test_parse_survivor_perk_candidate() -> None:
    rows = parse_perk_page(SURVIVOR_HTML, page_url=SURVIVOR_PERKS_URL, role="SURVIVOR")
    assert len(rows) == 1
    row = rows[0]
    assert row["name_ja"] == "デッド・ハード"
    assert row["aliases_ja"] == ["デッハ"]
    assert row["owner_name_ja"] == "デイビッド"
    assert row["priority"] == 4
    assert row["review_status"] == "CANDIDATE"
    assert row["source_authority"] == "COMMUNITY_REFERENCE"
    assert "0.5秒" in row["source_effect_ja"]


def test_parse_killer_perk_candidate() -> None:
    rows = parse_perk_page(KILLER_PERK_HTML, page_url=KILLER_PERKS_URL, role="KILLER")
    assert len(rows) == 1
    assert rows[0]["name_ja"] == "野蛮な力"
    assert rows[0]["owner_name_ja"] == "トラッパー"


def test_parse_killer_list_and_detail() -> None:
    rows = parse_killer_list_page(KILLER_HTML, page_url=KILLERS_URL)
    assert len(rows) == 1
    row = rows[0]
    assert row["name_ja"] == "トラッパー"
    assert row["movement_speed_text"] == "4.6m/s"
    assert row["terror_radius_text"] == "32m"
    assert row["height_text"] == "高い"
    assert row["unique_perks_ja"] == ["不安の元凶", "野蛮な力", "興奮"]
    detail = parse_killer_detail_page(DETAIL_HTML, page_url=row["detail_url"])
    assert detail["contains_power_section"] is True
    assert detail["contains_addon_section"] is True


def test_parse_map_detail_extracts_training_metadata() -> None:
    detail = parse_map_detail_page(MAP_DETAIL_HTML, page_url="https://kamigame.jp/dbd/page/map1.html")
    assert detail["realm_name_ja"] == "マクミラン・エステート"
    assert detail["offering_name_ja"] == "マクミランの指骨"
    assert detail["area_m2"] == 10240
    assert detail["pallet_text"] == "19~19"
    assert detail["map_image_urls"] == ["https://lh3.googleusercontent.com/map.png"]


def test_pagination_discovery_is_bounded_to_same_page() -> None:
    pages = discover_next_pages(SURVIVOR_HTML, page_url=SURVIVOR_PERKS_URL)
    assert pages == [SURVIVOR_PERKS_URL + "?page=2"]


class FakeClient:
    def __init__(self) -> None:
        self.pages = {
            SURVIVOR_PERKS_URL: SURVIVOR_HTML.replace("<a href='?page=2'>次へ</a>", ""),
            KILLER_PERKS_URL: KILLER_PERK_HTML,
            KILLERS_URL: KILLER_HTML,
            "https://kamigame.jp/dbd/page/trapper-detail.html": DETAIL_HTML,
            ITEMS_URL: ITEM_HTML, ADDONS_URL: ADDON_HTML, MAPS_URL: MAP_HTML,
            "https://kamigame.jp/dbd/page/map1.html": MAP_DETAIL_HTML,
        }

    def fetch_html(self, url: str, *, output_path: Path) -> FetchReceipt:
        body = self.pages[url].encode("utf-8")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(body)
        return FetchReceipt(url, output_path, hashlib.sha256(body).hexdigest(), "2026-08-18T00:00:00Z", "text/html")


def test_collector_writes_reviewable_bundle_without_canonical_promotion(tmp_path: Path) -> None:
    manifest = KamigameDbDKnowledgeCollector(tmp_path, client=FakeClient()).collect()
    assert manifest["automatic_verification"] is False
    assert manifest["canonical_write_performed"] is False
    assert manifest["counts"] == {
        "survivor_perks": 1,
        "killer_perks": 1,
        "killers": 1,
        "items": 1,
        "addons": 1,
        "maps": 1,
        "killer_details": 1,
        "map_details": 1,
        "cached_images": 0,
        "source_snapshots": 8,
    }
    assert (tmp_path / "normalized" / "survivor-perks.jsonl").exists()
    assert (tmp_path / "normalized" / "killer-perks.jsonl").exists()
    assert (tmp_path / "normalized" / "killers.jsonl").exists()
    assert (tmp_path / "normalized" / "items.jsonl").exists()
    assert (tmp_path / "normalized" / "addons.jsonl").exists()
    assert (tmp_path / "normalized" / "maps.jsonl").exists()
    assert (tmp_path / "normalized" / "aliases.csv").exists()
    assert (tmp_path / "manifest.json").exists()
    assert "CANDIDATE" in (tmp_path / "normalized" / "survivor-perks.jsonl").read_text(encoding="utf-8")


def test_training_studio_exposes_kamigame_knowledge_import_tab() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'notebook.add(knowledge_import_tab, text="ゲーム情報を取得")' in text
    assert "KamigameDbDKnowledgeCollector" in text
    assert 'text="ゲーム情報を取得"' in text
    assert 'text="検索用インデックスへ反映"' in text
    assert "CANDIDATE" in text


def test_readme_links_kamigame_import_guide() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "DBD-KAMIGAME-KNOWLEDGE-IMPORT.md" in text
    assert Path("docs/game-intelligence/DBD-KAMIGAME-KNOWLEDGE-IMPORT.md").exists()


def test_pyproject_exposes_kamigame_cli() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'ai-video-dbd-kamigame-collect = "ai_video_production.dbd_kamigame_cli:main"' in text
