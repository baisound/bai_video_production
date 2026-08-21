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
    GameEventType.GENERATOR_COMPLETE: "発電機修理完了",
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
    GameKnowledgeKind.UNKNOWN: "未分類・要確認",
    GameKnowledgeKind.SURVIVOR: "サバイバー",
    GameKnowledgeKind.KNOWLEDGE: "ナレッジ系",
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


VISUAL_TRAINING_DOMAIN_JA = {
    "SURVIVOR_HUD": "サバイバーHUD",
    "PERK_ICON": "パークアイコン",
    "ITEM_ICON": "アイテムアイコン",
    "ADDON_ICON": "アドオンアイコン",
    "KILLER_POWER": "キラー能力アイコン",
}

HUD_VISIBILITY_JA = {
    "VISIBLE": "表示されている",
    "PARTIALLY_OCCLUDED": "一部が隠れている",
    "HIDDEN": "非表示・隠されている",
    "UNREADABLE": "表示されているが判読できない",
    "UNKNOWN": "不明",
}

SOURCE_MODE_MANUAL_JA = "手入力"
SOURCE_MODE_URL_JA = "URL参照"
SOURCE_MODE_VALUES_JA = (SOURCE_MODE_MANUAL_JA, SOURCE_MODE_URL_JA)

LANGUAGE_JA = {
    "ja-JP": "日本語",
    "en-US": "英語",
}

_GAME_VERSION_RE = __import__("re").compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")


class TrainingFieldValidationError(ValueError):
    """Actionable field-level input error intended for Training Studio UI."""

    def __init__(self, *, field_ja: str, value: str, guidance_ja: str) -> None:
        self.field_ja = field_ja
        self.value = value
        self.guidance_ja = guidance_ja
        super().__init__(f"{field_ja}: {guidance_ja}")


def validate_game_version_text(value: str, *, field_ja: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    if not _GAME_VERSION_RE.fullmatch(normalized):
        raise TrainingFieldValidationError(
            field_ja=field_ja,
            value=normalized,
            guidance_ja=(
                "形式が正しくありません。例: 8.7.0 / 9.0.0 / 9.0.0.1。"
                "数字を「.」で区切った x.y.z または x.y.z.h 形式で入力してください。"
            ),
        )
    return normalized


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def validate_game_version_range(
    start_value: str,
    end_value: str,
) -> tuple[str | None, str | None]:
    start = validate_game_version_text(
        start_value,
        field_ja="対象ゲームバージョン（開始）",
    )
    end = validate_game_version_text(
        end_value,
        field_ja="対象ゲームバージョン（終了）",
    )
    if start is not None and end is not None:
        left = _version_tuple(start)
        right = _version_tuple(end)
        width = max(len(left), len(right))
        left += (0,) * (width - len(left))
        right += (0,) * (width - len(right))
        if left > right:
            raise TrainingFieldValidationError(
                field_ja="対象ゲームバージョン",
                value=f"{start} -> {end}",
                guidance_ja=(
                    "範囲が逆です。開始バージョンは終了バージョン以下にしてください。"
                ),
            )
    return start, end


def compose_source_ref(mode_ja: str, url_value: str) -> str:
    if mode_ja == SOURCE_MODE_MANUAL_JA:
        return "manual://owner"
    if mode_ja != SOURCE_MODE_URL_JA:
        raise TrainingFieldValidationError(
            field_ja="情報源",
            value=mode_ja,
            guidance_ja="「手入力」または「URL参照」を選択してください。",
        )
    url = url_value.strip()
    if not url:
        raise TrainingFieldValidationError(
            field_ja="参照URL",
            value="",
            guidance_ja="URL参照を選んだ場合は参照URLを入力してください。",
        )
    if not (url.startswith("https://") or url.startswith("http://")):
        raise TrainingFieldValidationError(
            field_ja="参照URL",
            value=url,
            guidance_ja="http:// または https:// で始まるURLを入力してください。",
        )
    return url


def visual_domain_display(internal_value: str) -> str:
    return VISUAL_TRAINING_DOMAIN_JA.get(internal_value, internal_value)


def hud_visibility_display(internal_value: str) -> str:
    return HUD_VISIBILITY_JA.get(internal_value, internal_value)
