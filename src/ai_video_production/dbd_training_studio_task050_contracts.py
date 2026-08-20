"""TASK-050 design contracts for DbD Training Studio operational foundation.

These types are intentionally side-effect free. They bind implementation to the
reviewed design before GUI or migration code is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StudioStage(str, Enum):
    INTRO = "INTRO"
    RUNTIME = "RUNTIME"
    KNOWLEDGE = "KNOWLEDGE"
    HUD = "HUD"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    OCR = "OCR"
    TRIVIA = "TRIVIA"
    REVIEW = "REVIEW"
    BACKUP = "BACKUP"


STAGE_ORDER = (
    StudioStage.INTRO,
    StudioStage.RUNTIME,
    StudioStage.KNOWLEDGE,
    StudioStage.HUD,
    StudioStage.VIDEO,
    StudioStage.IMAGE,
    StudioStage.OCR,
    StudioStage.TRIVIA,
    StudioStage.REVIEW,
    StudioStage.BACKUP,
)

STAGE_JA = {
    StudioStage.INTRO: "はじめに",
    StudioStage.RUNTIME: "実行環境を設定",
    StudioStage.KNOWLEDGE: "ゲーム情報を取得",
    StudioStage.HUD: "HUD位置を設定",
    StudioStage.VIDEO: "動画から学習",
    StudioStage.IMAGE: "画像を追加登録",
    StudioStage.OCR: "右上通知を学習",
    StudioStage.TRIVIA: "実況・豆知識を登録",
    StudioStage.REVIEW: "学習データを確認",
    StudioStage.BACKUP: "バックアップ・復元",
}


class LocationSource(str, Enum):
    AUTO_DETECTED = "AUTO_DETECTED"
    USER_OVERRIDE = "USER_OVERRIDE"
    PROFILE_SAVED = "PROFILE_SAVED"


class ToolHealth(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ExternalTool:
    tool_id: str
    effective_path: str | None
    source: LocationSource
    health: ToolHealth
    version: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceDescriptor:
    workspace_id: str
    display_name: str
    root_path: str


class HudVisibility(str, Enum):
    VISIBLE = "VISIBLE"
    PARTIALLY_OCCLUDED = "PARTIALLY_OCCLUDED"
    HIDDEN = "HIDDEN"
    UNREADABLE = "UNREADABLE"
    UNKNOWN = "UNKNOWN"


class HeartbeatTrend(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class UserFacingError:
    error_code: str
    title_ja: str
    summary_ja: str
    next_action_ja: str

    def __post_init__(self) -> None:
        forbidden = {"", "none", "error", "failed"}
        values = (self.title_ja, self.summary_ja, self.next_action_ja)
        if any(v.strip().lower() in forbidden for v in values):
            raise ValueError("user-visible error text must be actionable")


PERK_SLOT_JA = {
    0: "パーク1（上向き）",
    1: "パーク2（右向き）",
    2: "パーク3（下向き）",
    3: "パーク4（左向き）",
}
