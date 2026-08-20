from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import GameKnowledgeKind
from ai_video_production.dbd_entity_aliases import (
    EntityAliasCatalog,
    EntityAliasRecord,
    EntityAliasType,
)
from ai_video_production.dbd_game_knowledge_catalog import (
    GameKnowledgeCandidate,
    GameKnowledgeReviewCatalog,
    KnowledgeDependencyReference,
)
from ai_video_production.dbd_game_knowledge_presentation import (
    diagnostic_knowledge_values,
    human_knowledge_fields,
)
from ai_video_production.dbd_map_intelligence import MapIntelligenceStore, MapRecord


def _candidate(
    candidate_id: str,
    *,
    kind: GameKnowledgeKind = GameKnowledgeKind.PERK,
    status: str = "CANDIDATE",
    source_hash: str = "sha256:v1",
    details: dict | None = None,
) -> GameKnowledgeCandidate:
    return GameKnowledgeCandidate(
        candidate_id=candidate_id,
        knowledge_kind=kind,
        name_ja="テスト情報",
        review_status=status,
        source_revision_sha256=source_hash,
        details=details or {},
    )


def test_human_detail_allowlist_separates_diagnostics() -> None:
    row = _candidate(
        "map-1",
        kind=GameKnowledgeKind.MAP,
        details={
            "realm_name_ja": "マクミラン・エステート",
            "offering_name_ja": "マクミランの指骨",
            "area_m2": 10240,
            "features": "上下に発電機が固まりやすい",
            "classification_source": "SOURCE_SECTION",
            "classification_confidence": 900,
            "local_image_path": "private/map.img",
            "canonical_map_id": None,
        },
    )
    human = {field.label_ja: field.value for field in human_knowledge_fields(row)}
    diagnostics = diagnostic_knowledge_values(row)
    assert human["領域名"] == "マクミラン・エステート"
    assert human["面積㎡"] == 10240
    assert "classification_source" not in human
    assert diagnostics["classification_source"] == "SOURCE_SECTION"
    assert diagnostics["local_image_path"] == "private/map.img"
    assert diagnostics["candidate_id"] == "map-1"


def test_unverified_unreferenced_candidate_is_removed_and_exact_revision_suppressed(tmp_path: Path) -> None:
    catalog = GameKnowledgeReviewCatalog(tmp_path / "knowledge.json")
    row = _candidate("candidate-1")
    catalog.upsert_external((row,))
    derived = KnowledgeDependencyReference(
        "REFERENCE_INDEX", "candidate-1", "alias index", protected=False
    )
    impact = catalog.preview_delete("candidate-1", external_dependencies=(derived,))
    assert impact.action == "REMOVE_CANDIDATE"
    result = catalog.delete_safely(
        "candidate-1",
        expected_fingerprint=impact.fingerprint,
        external_dependencies=(derived,),
    )
    assert result.retained_catalog_row is False
    assert catalog.list() == ()
    assert catalog.upsert_external((row,)) == 0
    assert catalog.list() == ()

    newer = _candidate("candidate-1", source_hash="sha256:v2")
    assert catalog.upsert_external((newer,)) == 1
    restored = catalog.get("candidate-1")
    assert restored.review_status == "CANDIDATE"
    assert restored.details["_previous_tombstone"]["action"] == "REMOVE_CANDIDATE"


def test_verified_or_referenced_candidate_tombstones_and_stays_disabled(tmp_path: Path) -> None:
    catalog = GameKnowledgeReviewCatalog(tmp_path / "knowledge.json")
    catalog.upsert_external((_candidate("verified", status="VERIFIED"),))
    dependency = KnowledgeDependencyReference(
        "TRIVIA_ENTITY_REF", "trivia-1", "verified trivia reference"
    )
    impact = catalog.preview_delete("verified", external_dependencies=(dependency,))
    assert impact.action == "TOMBSTONE"
    assert impact.protected_count == 2
    assert any(item.kind == "HUMAN_REVIEW_STATE" for item in impact.dependencies)
    result = catalog.delete_safely(
        "verified",
        expected_fingerprint=impact.fingerprint,
        external_dependencies=(dependency,),
    )
    assert result.retained_catalog_row is True
    disabled = catalog.get("verified")
    assert disabled.review_status == "DISABLED"
    assert disabled.enabled is False
    assert disabled.details["_tombstone"]["action"] == "TOMBSTONE"

    newer = _candidate("verified", status="CANDIDATE", source_hash="sha256:v2")
    assert catalog.upsert_external((newer,)) == 1
    still_disabled = catalog.get("verified")
    assert still_disabled.review_status == "DISABLED"
    assert still_disabled.details["_pending_external_update"]["source_revision_sha256"] == "sha256:v2"
    resurrected = catalog.set_status("verified", "VERIFIED")
    assert resurrected.source_revision_sha256 == "sha256:v2"
    payload = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    assert payload["tombstones"] == []


def test_catalog_relation_protects_target_and_stale_preview_fails(tmp_path: Path) -> None:
    catalog = GameKnowledgeReviewCatalog(tmp_path / "knowledge.json")
    target = _candidate("target")
    relation = _candidate("relation", details={"realm_candidate_id": "target"})
    catalog.upsert_external((target, relation))
    impact = catalog.preview_delete("target")
    assert impact.action == "TOMBSTONE"
    assert any(item.kind == "CATALOG_RELATION" for item in impact.dependencies)
    changed_dependencies = (
        KnowledgeDependencyReference("MAP_RELATION", "target", "map relation"),
    )
    with pytest.raises(ValueError, match="preview again"):
        catalog.delete_safely(
            "target",
            expected_fingerprint=impact.fingerprint,
            external_dependencies=changed_dependencies,
        )


def test_explicit_reenable_clears_tombstone_state(tmp_path: Path) -> None:
    catalog = GameKnowledgeReviewCatalog(tmp_path / "knowledge.json")
    catalog.upsert_external((_candidate("target"),))
    dependency = KnowledgeDependencyReference("MAP_RELATION", "target", "map relation")
    impact = catalog.preview_delete("target", external_dependencies=(dependency,))
    catalog.delete_safely(
        "target",
        expected_fingerprint=impact.fingerprint,
        external_dependencies=(dependency,),
    )
    reenabled = catalog.edit("target", enabled=True)
    assert reenabled.review_status == "NEEDS_REVIEW"
    assert reenabled.enabled is True
    assert "_tombstone" not in reenabled.details
    payload = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    assert payload["tombstones"] == []


def test_alias_invalidation_and_map_disable_are_bounded(tmp_path: Path) -> None:
    aliases = EntityAliasCatalog(tmp_path / "aliases.sqlite")
    aliases.put(EntityAliasRecord(
        entity_id="map-1",
        knowledge_kind=GameKnowledgeKind.MAP,
        alias_text="テストマップ",
        alias_type=EntityAliasType.OFFICIAL_NAME,
        source_ref="manual://test",
    ))
    assert aliases.count_for_entity("map-1") == 1
    assert aliases.remove_entity("map-1") == 1
    assert aliases.count_for_entity("map-1") == 0

    maps = MapIntelligenceStore(tmp_path / "maps.json")
    maps.upsert(MapRecord(map_id="map-1", map_name="テストマップ"))
    assert maps.disable("map-1").enabled is False


def test_training_studio_uses_collapsed_diagnostics_and_safe_delete() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'text="内部・診断情報を表示"' in text
    assert "diagnostics_frame.grid_remove()" in text
    assert "human_knowledge_fields(row)" in text
    assert "preview_delete(row.candidate_id" in text
    assert "delete_safely(" in text
    assert 'text="削除"' in text
