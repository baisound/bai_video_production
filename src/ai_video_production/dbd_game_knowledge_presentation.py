"""Human-first Game Knowledge detail projection with isolated diagnostics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical_game_event import GameKnowledgeKind
from .dbd_game_knowledge_catalog import GameKnowledgeCandidate


@dataclass(frozen=True, slots=True)
class HumanKnowledgeField:
    key: str
    label_ja: str
    value: object


@dataclass(frozen=True, slots=True)
class _FieldSpec:
    key: str
    label_ja: str
    source_keys: tuple[str, ...]


_COMMON = (
    _FieldSpec("description", "効果・説明", ("source_effect_ja", "effect", "description", "summary")),
)

_BY_KIND: dict[GameKnowledgeKind, tuple[_FieldSpec, ...]] = {
    GameKnowledgeKind.PERK: (
        _FieldSpec("owner", "所有者", ("owner_name_ja", "owner")),
    ),
    GameKnowledgeKind.KILLER: (
        _FieldSpec("movement_speed", "移動速度", ("movement_speed_text",)),
        _FieldSpec("terror_radius", "脅威範囲", ("terror_radius_text",)),
        _FieldSpec("height", "背の高さ", ("height_text",)),
        _FieldSpec("power", "固有能力", ("power_name_ja", "power", "ability")),
        _FieldSpec("unique_perks", "固有パーク", ("unique_perks_ja",)),
        _FieldSpec("evaluation", "評価・攻略", ("evaluation", "tactical_text", "detail_sections")),
        _FieldSpec("addons", "アドオン関連", ("addons", "addon_evaluation")),
    ),
    GameKnowledgeKind.ITEM: (
        _FieldSpec("category", "種類", ("category_ja", "category")),
        _FieldSpec("rarity", "レア度", ("rarity",)),
        _FieldSpec("charges", "チャージ", ("base_charges_text", "charges")),
        _FieldSpec("conditions", "使用条件", ("use_conditions", "conditions")),
    ),
    GameKnowledgeKind.ADDON: (
        _FieldSpec("owner", "所有・対象", ("owner_killer_name_ja", "owner_name_ja", "owner")),
        _FieldSpec("rarity", "レア度", ("rarity",)),
        _FieldSpec("conditions", "使用条件", ("use_conditions", "conditions")),
    ),
    GameKnowledgeKind.MAP: (
        _FieldSpec("realm", "領域名", ("realm_name_ja",)),
        _FieldSpec("offering", "オファリング", ("offering_name_ja",)),
        _FieldSpec("area", "面積㎡", ("area_m2",)),
        _FieldSpec("size", "広さ", ("size_class",)),
        _FieldSpec("pallets", "板", ("pallet_text",)),
        _FieldSpec("features", "特徴", ("features",)),
        _FieldSpec("objects", "固有オブジェクト", ("unique_objects",)),
        _FieldSpec("favorability", "有利度", ("favorability",)),
    ),
}

_KIND_LABELS = {
    GameKnowledgeKind.PERK: "パーク",
    GameKnowledgeKind.KILLER: "キラー",
    GameKnowledgeKind.POWER: "能力",
    GameKnowledgeKind.MAP: "マップ",
    GameKnowledgeKind.REALM: "領域",
    GameKnowledgeKind.TILE: "地形",
    GameKnowledgeKind.ADDON: "アドオン",
    GameKnowledgeKind.ITEM: "アイテム",
    GameKnowledgeKind.OFFERING: "オファリング",
    GameKnowledgeKind.SURVIVOR: "サバイバー",
    GameKnowledgeKind.KNOWLEDGE: "ナレッジ系",
    GameKnowledgeKind.STATUS: "状態",
    GameKnowledgeKind.MECHANIC: "ゲーム仕様",
    GameKnowledgeKind.UNKNOWN: "未分類・要確認",
}


def knowledge_kind_label_ja(kind: GameKnowledgeKind) -> str:
    if kind is GameKnowledgeKind.CHARACTER:
        return "未分類・要確認"
    return _KIND_LABELS.get(kind, kind.value)


def _present(value: object) -> bool:
    return value not in (None, "", (), [], {})


def human_knowledge_fields(candidate: GameKnowledgeCandidate) -> tuple[HumanKnowledgeField, ...]:
    fields = [
        HumanKnowledgeField("kind", "種別", knowledge_kind_label_ja(candidate.knowledge_kind)),
        HumanKnowledgeField("review_status", "確認状態", candidate.review_status),
    ]
    if candidate.source_page_url:
        fields.append(HumanKnowledgeField("source", "取得元", candidate.source_page_url))
    for spec in (*_COMMON, *_BY_KIND.get(candidate.knowledge_kind, ())):
        for source_key in spec.source_keys:
            value = candidate.details.get(source_key)
            if _present(value):
                fields.append(HumanKnowledgeField(spec.key, spec.label_ja, value))
                break
    return tuple(fields)


def diagnostic_knowledge_values(candidate: GameKnowledgeCandidate) -> dict[str, Any]:
    human_source_keys = {
        source_key
        for spec in (*_COMMON, *_BY_KIND.get(candidate.knowledge_kind, ()))
        for source_key in spec.source_keys
    }
    diagnostics = {
        key: value
        for key, value in candidate.details.items()
        if key not in human_source_keys
    }
    diagnostics.update({
        "candidate_id": candidate.candidate_id,
        "knowledge_kind": candidate.knowledge_kind.value,
        "manual_image_path": candidate.manual_image_path,
        "image_urls": list(candidate.image_urls),
        "source_revision_sha256": candidate.source_revision_sha256,
        "updated_at": candidate.updated_at,
    })
    return dict(sorted(diagnostics.items()))


__all__ = [
    "HumanKnowledgeField",
    "diagnostic_knowledge_values",
    "human_knowledge_fields",
    "knowledge_kind_label_ja",
]
