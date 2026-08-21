from __future__ import annotations

from pathlib import Path

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_game_information_classification import classify_game_information
from ai_video_production.dbd_game_knowledge_catalog import GameKnowledgeCandidate
from ai_video_production.dbd_game_knowledge_migration import plan_game_knowledge_migration
from ai_video_production.dbd_kamigame_candidate_bridge import KamigameCandidateSummary


def _candidate(
    candidate_id: str,
    kind: GameKnowledgeKind,
    name: str,
    *,
    review_status: str = "CANDIDATE",
    manual_name_ja: str = "",
) -> GameKnowledgeCandidate:
    return GameKnowledgeCandidate(
        candidate_id=candidate_id,
        knowledge_kind=kind,
        name_ja=name,
        review_status=review_status,
        manual_name_ja=manual_name_ja,
    )


def test_legacy_character_remains_readable_but_new_decisions_fail_closed() -> None:
    assert GameKnowledgeKind("CHARACTER") is GameKnowledgeKind.CHARACTER
    known, known_source, _ = classify_game_information(
        {"knowledge_kind": "CHARACTER", "name_ja": "ドワイト"}
    )
    unresolved, unresolved_source, _ = classify_game_information(
        {"knowledge_kind": "CHARACTER", "name_ja": "未登録の登場人物"}
    )
    heading, heading_source, _ = classify_game_information(
        {"name_ja": "未登録", "source_section_heading": "登場人物"}
    )
    assert (known, known_source) == (GameKnowledgeKind.SURVIVOR, "KNOWN_ENTITY_MASTER")
    assert (unresolved, unresolved_source) == (GameKnowledgeKind.UNKNOWN, "LEGACY_CHARACTER")
    assert (heading, heading_source) == (GameKnowledgeKind.UNKNOWN, "AMBIGUOUS_CHARACTER_SECTION")


def test_missing_source_kind_is_unknown_not_mechanic() -> None:
    kind, source, confidence = classify_game_information({"name_ja": "未分類情報"})
    assert (kind, source, confidence) == (
        GameKnowledgeKind.UNKNOWN,
        "SOURCE_KIND_FALLBACK",
        500,
    )


def test_operator_label_sources_do_not_expose_legacy_character_category() -> None:
    source_paths = (
        "src/ai_video_production/dbd_training_studio.py",
        "src/ai_video_production/dbd_training_form_support.py",
        "src/ai_video_production/dbd_game_element_selector_ui.py",
    )
    for source_path in source_paths:
        text = Path(source_path).read_text(encoding="utf-8")
        assert 'GameKnowledgeKind.CHARACTER:"キャラクター"' not in text
        assert 'GameKnowledgeKind.CHARACTER: "キャラクター"' not in text
    summary = KamigameCandidateSummary(
        candidate_id="legacy",
        knowledge_kind=GameKnowledgeKind.CHARACTER,
        name_ja="legacy",
        aliases_ja=(),
        review_status="CANDIDATE",
        source_page_url="",
    )
    assert summary.kind_ja == "未分類・要確認"
    selector_text = Path(
        "src/ai_video_production/dbd_game_element_selector_ui.py"
    ).read_text(encoding="utf-8")
    assert "if kind in {GameKnowledgeKind.CHARACTER, GameKnowledgeKind.UNKNOWN}" in selector_text


def test_migration_dry_run_reports_known_unknown_and_human_protection() -> None:
    rows = (
        _candidate("known", GameKnowledgeKind.CHARACTER, "ドワイト"),
        _candidate("unresolved", GameKnowledgeKind.CHARACTER, "未登録の登場人物"),
        _candidate(
            "protected",
            GameKnowledgeKind.CHARACTER,
            "ナンシー",
            review_status="VERIFIED",
            manual_name_ja="ナンシー・ウィーラー",
        ),
        _candidate("map", GameKnowledgeKind.MAP, "サファケーション・ピット"),
    )
    before = tuple(row.to_dict() for row in rows)
    report = plan_game_knowledge_migration(rows)
    changes = {change.candidate_id: change for change in report.changes}
    assert report.apply_performed is False
    assert report.input_count == 4
    assert report.unchanged_count == 1
    assert changes["known"].proposed_kind is GameKnowledgeKind.SURVIVOR
    assert changes["known"].reason == "LEGACY_CHARACTER_KNOWN_SURVIVOR"
    assert changes["unresolved"].proposed_kind is GameKnowledgeKind.UNKNOWN
    assert changes["unresolved"].requires_human_review is True
    assert changes["protected"].protected_human_decision is True
    assert report.human_protected_count == 1
    assert report.conflict_count == 1
    assert tuple(row.to_dict() for row in rows) == before
