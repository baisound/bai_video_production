"""TASK-050 R4 Japanese form metadata for Training Studio."""
from __future__ import annotations

from .canonical_game_event import GameEventType, GameKnowledgeKind
from .dbd_perk_knowledge import PerkEnvironment


TRIVIA_CATEGORIES = {
    "GENERAL": "一般",
    "PERK": "パーク",
    "KILLER": "キラー",
    "POWER": "キラー能力",
    "ITEM": "アイテム",
    "ADDON": "アドオン",
    "MAP": "マップ",
    "MECHANIC": "ゲーム仕様",
    "STRATEGY": "立ち回り・戦術",
    "HISTORY": "過去仕様・変更履歴",
}

EVENT_TYPE_JA = {
    GameEventType.MATCH_START: "試合開始",
    GameEventType.CHASE_START: "チェイス開始",
    GameEventType.CHASE_END: "チェイス終了",
    GameEventType.INJURY: "負傷",
    GameEventType.DOWN: "ダウン",
    GameEventType.HOOK: "フック",
    GameEventType.UNHOOK: "救助",
    GameEventType.WINDOW_VAULT: "窓越え",
    GameEventType.PALLET_DROP: "板倒し",
    GameEventType.KILL: "処刑・死亡",
    GameEventType.ESCAPE: "脱出",
    GameEventType.UNKNOWN_EVENT: "不明イベント",
}

ENVIRONMENT_JA = {
    PerkEnvironment.LIVE: "通常版 (LIVE)",
    PerkEnvironment.PTB: "PTB",
    PerkEnvironment.ARCHIVE: "過去版・資料 (ARCHIVE)",
    PerkEnvironment.UNKNOWN: "不明",
}

KNOWLEDGE_KIND_JA = {
    GameKnowledgeKind.PERK: "パーク",
    GameKnowledgeKind.KILLER: "キラー",
    GameKnowledgeKind.POWER: "キラー能力",
    GameKnowledgeKind.MAP: "マップ",
    GameKnowledgeKind.REALM: "レルム",
    GameKnowledgeKind.TILE: "地形・タイル",
    GameKnowledgeKind.ADDON: "アドオン",
    GameKnowledgeKind.ITEM: "アイテム",
    GameKnowledgeKind.OFFERING: "オファリング",
    GameKnowledgeKind.STATUS: "状態",
    GameKnowledgeKind.MECHANIC: "ゲーム仕様",
}

FIELD_HELP_JA = {
    "category": ("カテゴリ", "何についての豆知識かを選びます。", "例: パーク / キラー / ゲーム仕様"),
    "tags": ("タグ", "検索や実況候補の絞り込みに使う複数キーワードです。", "例: 初心者向け, チェイス, 発電機"),
    "event_types": ("使用する場面", "この情報を利用できるCGELイベントを複数選びます。", "例: チェイス開始 / 窓越え"),
    "entity_refs": ("関連するゲーム要素", "Knowledgeからパーク・キラー等を検索して関連付けます。内部IDは自動保存します。", "例: 鋼の意志 / Iron Will / アイウィル"),
    "environment": ("対象環境", "この情報が有効なDbD環境を指定します。", "例: 通常版 (LIVE)"),
}


def parse_event_display(values: tuple[str, ...]) -> tuple[GameEventType, ...]:
    reverse = {label: event for event, label in EVENT_TYPE_JA.items()}
    return tuple(sorted({reverse[value] for value in values}, key=lambda x: x.value))
