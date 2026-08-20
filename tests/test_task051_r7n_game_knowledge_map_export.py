from __future__ import annotations

import json
from pathlib import Path

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_editing_intelligence import DbDEditingIntelligenceBuilder, EditCandidateKind
from ai_video_production.dbd_game_knowledge_catalog import GameKnowledgeCandidate, GameKnowledgeReviewCatalog
from ai_video_production.dbd_kamigame_collector import parse_addon_page, parse_item_page, parse_map_page
from ai_video_production.dbd_map_intelligence import (MapFloor, MapIntelligenceStore, MapLandmark, MapRecord, MapTrainingCapture, MapTrainingDatasetStore, MapLocalizationResult, MapLocationCandidate)
from ai_video_production.dbd_video_analysis_export import DbDVideoEditingExportService
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.timebase import FrameRate
from ai_video_production.canonical_game_event import GameKnowledgeKind


def test_kamigame_item_addon_map_parsers_cover_requested_domains() -> None:
    item_html = """
    <h2>医療キット系アイテム一覧</h2>
    <table><tr><td><img src='/img/med.png'>救急箱</td><td>Uncommon 〖基礎チャージ量〗24 〖効果〗自己治療ができる</td></tr></table>
    """
    items = parse_item_page(item_html, page_url="https://kamigame.jp/dbd/page/94107608092246023.html")
    assert items and items[0]["name_ja"] == "救急箱"
    assert items[0]["category_ja"] == "医療キット"
    assert items[0]["base_charges_text"] == "24"

    addon_html = """
    <h2>ヒルビリーのアドオン一覧</h2>
    <table><tr><td><img src='/img/boot.png'>親父のブーツ</td><td>Rare 〖効果〗チェーンソー旋回性能が上昇</td></tr></table>
    """
    addons = parse_addon_page(addon_html, page_url="https://kamigame.jp/dbd/page/93674768519135239.html")
    assert addons and addons[0]["owner_killer_name_ja"] == "ヒルビリー"
    assert addons[0]["name_ja"] == "親父のブーツ"

    map_html = """
    <h2>各マップ個別一覧</h2>
    <table><tr><td><a href='/dbd/page/map1.html'>サファケーション・ピット</a> <a href='/dbd/page/realm1.html'>マクミラン・エステート</a></td><td>室外 面積大 板最大19枚</td></tr></table>
    <h2>各マップの広さと板枚数比較表</h2>
    <table><tr><td><a href='/dbd/page/map1.html'>サファケーション・ピット</a> <a href='/dbd/page/realm1.html'>マクミラン・エステート</a></td><td>10240</td><td>19~19</td></tr></table>
    """
    maps = parse_map_page(map_html, page_url="https://kamigame.jp/dbd/page/94254357779841031.html")
    assert maps and maps[0]["name_ja"] == "サファケーション・ピット"
    assert maps[0]["realm_name_ja"] == "マクミラン・エステート"


def test_game_knowledge_catalog_preserves_manual_override_and_marks_external_update(tmp_path: Path) -> None:
    store = GameKnowledgeReviewCatalog(tmp_path / "knowledge.json")
    first = GameKnowledgeCandidate(
        candidate_id="item_test",
        knowledge_kind=GameKnowledgeKind.ITEM,
        name_ja="救急箱",
        aliases_ja=("メディキット",),
        source_revision_sha256="sha256:" + "1" * 64,
    )
    store.upsert_external((first,))
    store.set_status("item_test", "VERIFIED")
    edited = store.edit("item_test", aliases_ja=("救急", "メディキット"), image_path=str(tmp_path / "custom.png"))
    assert edited.review_status == "NEEDS_REVIEW"
    store.set_status("item_test", "VERIFIED")

    second = GameKnowledgeCandidate(
        candidate_id="item_test",
        knowledge_kind=GameKnowledgeKind.ITEM,
        name_ja="救急箱（更新）",
        source_revision_sha256="sha256:" + "2" * 64,
    )
    store.upsert_external((second,))
    after = store.get("item_test")
    assert after.review_status == "UPDATE_AVAILABLE"
    assert after.name_ja == "救急箱"  # last Human-verified source stays active
    assert after.effective_aliases_ja == ("救急", "メディキット")
    assert after.manual_image_path.endswith("custom.png")
    accepted = store.set_status("item_test", "VERIFIED")
    assert accepted.name_ja == "救急箱（更新）"
    assert accepted.review_status == "VERIFIED"


def test_map_intelligence_locks_orientation_and_accepts_cross_view_training_contract(tmp_path: Path) -> None:
    store = MapIntelligenceStore(tmp_path / "maps.json")
    store.upsert(MapRecord(
        map_id="map_test",
        map_name="テストマップ",
        realm_name="テスト領域",
        floors=(MapFloor("f1", "1F", 1),),
        landmarks=(MapLandmark("shack", "小屋", "f1", 0.75, 0.25, "KILLER_SHACK"),),
    ))
    locked = store.set_orientation("map_test", 90, note="小屋側を下として固定")
    assert locked.orientation_locked is True
    assert locked.rotation_deg == 90
    loaded = MapIntelligenceStore(tmp_path / "maps.json").get("map_test")
    assert loaded.orientation_note == "小屋側を下として固定"

    capture = MapTrainingCapture(
        capture_id="cap-1", session_id="session-1", map_id="map_test", floor_id="f1",
        view_role="SURVIVOR_3", source_frame=1200, frame_image="frame.pgm", u=0.5, v=0.4,
        heading_deg=315.0, region_id="south", landmark_ids=("shack",),
    )
    assert capture.view_role == "SURVIVOR_3"
    killer = MapTrainingCapture(
        capture_id="cap-2", session_id="session-1", map_id="map_test", floor_id="f1",
        view_role="KILLER", source_frame=1220, frame_image="frame2.pgm", u=0.5, v=0.4,
    )
    assert killer.view_role == "KILLER"
    dataset = MapTrainingDatasetStore(tmp_path / "map-training.json")
    assert dataset.append(capture) is True and dataset.append(killer) is True
    assert {row.view_role for row in dataset.list()} == {"SURVIVOR_3", "KILLER"}
    result = MapLocalizationResult(
        map_id="map_test", floor_id="f1", u=0.51, v=0.39, view_role="KILLER",
        confidence_milli=910, heading_deg=315.0, region_id="south", nearest_landmark_id="shack",
        candidates=(MapLocationCandidate("f1", 0.51, 0.39, 910),),
    )
    assert result.confidence_milli == 910


def _game_fixture(tmp_path: Path):
    store = GameIntelligenceStore(tmp_path / "analysis.sqlite3")
    match = GameMatch(
        production_job_id=generate_id(IdKind.JOB), source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight", game_profile_version="1.0.0", game_version="9.1.0",
        environment=GameEnvironment.LIVE, perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30, 1), status=GameMatchStatus.ANALYZING,
    )
    store.put_match(match)
    rows = []
    for idx, (kind, start, confidence) in enumerate(((GameEventType.CHASE_START, 300, 920), (GameEventType.DOWN, 600, 950))):
        evidence = GameEvidence(
            production_job_id=match.production_job_id, match_id=match.match_id,
            source_asset_id=match.source_asset_id, producer="r7n.fixture", producer_version="1.0.0",
            evidence_type=GameEvidenceType.VISION, source_range=SourceFrameRange(start, start + 30),
            confidence_milli=confidence,
        )
        event = CanonicalGameEvent(
            match_id=match.match_id, revision=1, event_type=kind, source_range=evidence.source_range,
            game_version=match.game_version, environment=match.environment, perspective=match.perspective,
            state={"fixture": True}, confidence_milli=confidence,
            confirmation_state=EventConfirmationState.CONFIRMED, evidence_refs=(evidence.game_evidence_id,),
            review_status=EventReviewStatus.HUMAN_APPROVED,
        )
        store.append_evidence(evidence); store.append_event(event); rows.append(event)
    return store, match, tuple(rows)


def test_editing_intelligence_and_export_package_are_editing_oriented(tmp_path: Path) -> None:
    store, match, events = _game_fixture(tmp_path)
    plan = DbDEditingIntelligenceBuilder(highlight_threshold=60).build(match, events)
    assert len(plan.candidates) == 2
    assert all(row.kind is EditCandidateKind.HIGHLIGHT for row in plan.candidates)
    assert plan.candidates[1].highlight_score > plan.candidates[0].highlight_score

    files = DbDVideoEditingExportService().export(
        store=store, match_id=match.match_id, destination=tmp_path / "export",
    )
    assert set(files) == {"analysis", "edit_plan", "markers_csv", "events_csv", "bai_handoff", "manifest"}
    manifest = json.loads(files["manifest"].read_text("utf-8"))
    assert manifest["package_type"] == "BAI_DBD_EDITING_INTELLIGENCE"
    assert "BAI_VIDEO_PRODUCTION" in manifest["recommended_consumers"]
    assert "highlight_score" in files["markers_csv"].read_text("utf-8-sig")
    handoff = json.loads(files["bai_handoff"].read_text("utf-8"))
    assert handoff["handoff_type"] == "BAI_VIDEO_PRODUCTION_EDITING_INTELLIGENCE"
    assert handoff["production_timeline_mutated"] is False


def test_review_and_training_studio_ui_source_contains_owner_requested_ux() -> None:
    review = Path("src/ai_video_production/dbd_training_review_ui_v2.py").read_text("utf-8")
    assert 'text="学習対象"' in review
    assert 'text="キーワード"' in review
    assert 'text="正解ラベルを選び直す"' in review
    assert 'text="画像を大きく表示"' in review
    assert 'text="全タブを再読み込み"' in review
    assert "simpledialog.askstring" not in review

    studio = Path("src/ai_video_production/dbd_training_studio.py").read_text("utf-8")
    assert 'text="動画を解析・編集情報を出力"' in studio
    assert 'text="編集"' in studio
    assert 'text="確認済みにする"' in studio
    assert 'text="マップ詳細"' in studio
    assert "アイテム=" in studio and "アドオン=" in studio and "マップ=" in studio
    assert "外部参考情報" in studio and "取込候補" in studio and "確認済み" in studio
