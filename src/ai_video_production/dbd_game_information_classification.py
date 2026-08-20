"""Deterministic DbD game-information classification for imported review data.

Strong/explicit signals must win over weak source-page heuristics so a known entity
is never turned into a map merely because it was discovered on a map/index page.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .canonical_game_event import GameKnowledgeKind


# Owner-verified regression master. Keep this small and explicit; source/page rules
# handle general cases while these identities protect known historical failures.
_KNOWN_ENTITY_KIND: dict[str, GameKnowledgeKind] = {
    "トーリー": GameKnowledgeKind.CHARACTER,
    "ドワイト": GameKnowledgeKind.CHARACTER,
    "ナンシー": GameKnowledgeKind.CHARACTER,
    "ネア": GameKnowledgeKind.CHARACTER,
    "ハディ": GameKnowledgeKind.SURVIVOR,
    "ハグ": GameKnowledgeKind.KILLER,
    "ヒルビリー": GameKnowledgeKind.KILLER,
    "ピッグ": GameKnowledgeKind.KILLER,
}


def normalize_game_information_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = re.sub(r"\s+", "", value)
    return value.strip("-–—|｜:：・")


def _title(row: dict[str, Any]) -> str:
    for key in ("name_ja", "map_name_ja", "realm_name_ja", "title", "page_title"):
        value = normalize_game_information_title(str(row.get(key) or ""))
        if value:
            return value
    return ""


def classify_game_information(
    row: dict[str, Any],
    *,
    source_kind: GameKnowledgeKind | None = None,
) -> tuple[GameKnowledgeKind, str, int]:
    """Return (kind, classification_source, confidence_milli).

    Priority follows the approved design: explicit/manual -> known entity master ->
    article semantics -> source metadata -> source-kind fallback.
    """
    explicit = str(row.get("forced_type") or row.get("knowledge_kind") or "").strip().upper()
    if explicit in GameKnowledgeKind.__members__:
        return GameKnowledgeKind[explicit], "EXPLICIT_SOURCE", 1000

    title = _title(row)
    # Knowledge-article semantics intentionally precede base-name lookup: "ハグ対策"
    # is an article, while "ハグ" is the killer entity.
    if title.endswith("対策") or title.endswith("攻略"):
        return GameKnowledgeKind.KNOWLEDGE, "ARTICLE_SUFFIX", 1000

    known = _KNOWN_ENTITY_KIND.get(title)
    if known is not None:
        return known, "KNOWN_ENTITY_MASTER", 1000

    heading = normalize_game_information_title(str(row.get("source_section_heading") or row.get("section_heading") or ""))
    if "対策" in heading or "攻略" in heading or "豆知識" in heading:
        return GameKnowledgeKind.KNOWLEDGE, "SOURCE_SECTION", 900
    if "サバイバー" in heading:
        return GameKnowledgeKind.SURVIVOR, "SOURCE_SECTION", 900
    if "キャラクター" in heading or "登場人物" in heading:
        return GameKnowledgeKind.CHARACTER, "SOURCE_SECTION", 900
    if "キラー" in heading and source_kind in {None, GameKnowledgeKind.MAP, GameKnowledgeKind.MECHANIC}:
        return GameKnowledgeKind.KILLER, "SOURCE_SECTION", 850

    return (source_kind or GameKnowledgeKind.MECHANIC), "SOURCE_KIND_FALLBACK", 500


__all__ = ["classify_game_information", "normalize_game_information_title"]
