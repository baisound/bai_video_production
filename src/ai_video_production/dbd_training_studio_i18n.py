"""Japanese-first presentation contracts for TASK-050 Training Studio."""
from __future__ import annotations

from dataclasses import dataclass


STAGE_ORDER = (
    "INTRODUCTION",
    "RUNTIME_ENVIRONMENT",
    "KNOWLEDGE_IMPORT",
    "HUD_CALIBRATION",
    "VIDEO_LEARNING",
    "IMAGE_REGISTRATION",
    "UPPER_RIGHT_OCR",
    "COMMENTARY_TRIVIA",
    "TRAINING_DATA_REVIEW",
    "BACKUP_RESTORE",
)

STAGE_JA = {
    "INTRODUCTION": "はじめに",
    "RUNTIME_ENVIRONMENT": "実行環境を設定",
    "KNOWLEDGE_IMPORT": "ゲーム情報を取得",
    "HUD_CALIBRATION": "HUD位置を設定",
    "VIDEO_LEARNING": "動画から学習",
    "IMAGE_REGISTRATION": "画像を追加登録",
    "UPPER_RIGHT_OCR": "右上通知を学習",
    "COMMENTARY_TRIVIA": "実況・豆知識を登録",
    "TRAINING_DATA_REVIEW": "学習データを確認",
    "BACKUP_RESTORE": "バックアップ・復元",
}

PERK_SLOT_JA = {
    0: "パーク1（上向き）",
    1: "パーク2（右向き）",
    2: "パーク3（下向き）",
    3: "パーク4（左向き）",
}

HELP_JA = {
    "category": {
        "title": "カテゴリ",
        "description": "豆知識が何についての情報かを分類します。",
        "example": "例: パーク、キラー、ゲーム仕様、立ち回り・戦術",
    },
    "tags": {
        "title": "タグ",
        "description": "検索や実況候補の絞り込みに使う複数の補助キーワードです。",
        "example": "例: 初心者向け、チェイス、発電機、救助",
    },
    "event_types": {
        "title": "使用する場面",
        "description": "この情報を利用できるCGELイベントを複数選択します。",
        "example": "例: チェイス開始、窓越え、救助",
    },
    "entity_refs": {
        "title": "関連するゲーム要素",
        "description": "パーク、キラー、能力、アイテムなどのCanonical Knowledgeを関連付けます。",
        "example": "例: 鋼の意志 / Iron Will",
    },
    "environment": {
        "title": "対象環境",
        "description": "通常版・PTBなど、この情報が有効なゲーム環境を指定します。",
        "example": "通常版 (LIVE)",
    },
}


@dataclass(frozen=True, slots=True)
class UserFacingError:
    error_code: str
    title_ja: str
    summary_ja: str
    next_action_ja: str
    technical_details: str | None = None

    def __post_init__(self) -> None:
        forbidden = {"", "none", "error", "failed", "exception"}
        for value in (self.title_ja, self.summary_ja, self.next_action_ja):
            if value.strip().lower() in forbidden:
                raise ValueError("利用者向けエラーには日本語の説明と次の操作が必要です。")

    def message(self) -> str:
        return (
            f"{self.summary_ja}\n\n"
            f"次にすること:\n{self.next_action_ja}\n\n"
            f"エラーコード: {self.error_code}"
        )


def error_from_exception(
    *,
    error_code: str,
    title_ja: str,
    summary_ja: str,
    next_action_ja: str,
    exc: Exception,
) -> UserFacingError:
    return UserFacingError(
        error_code=error_code,
        title_ja=title_ja,
        summary_ja=summary_ja,
        next_action_ja=next_action_ja,
        technical_details=f"{type(exc).__name__}: {exc}",
    )
