"""TASK-051 R3 HUD-profile binding and multi-slot training support."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .canonical_game_event import GameKnowledgeKind
from .dbd_entity_aliases import EntityAliasCatalog
from .dbd_hud_calibration import (
    DBDHudProfileResolver,
    DBDHudVideoProfileResolver,
    FFmpegFrameInspector,
    HudProfileRegistry,
)
from .dbd_hud_calibration_editor import PixelRect, RoiPixelEditor
from .dbd_training_workspace import VisualTrainingDomain
from .dbd_vision_slices import DBDHudRoiProfile, NormalizedROI


@dataclass(frozen=True, slots=True)
class TrainingHudProfileBinding:
    profile: DBDHudRoiProfile
    profile_path: str
    score_milli: int
    evidence: tuple[str, ...]
    source_width: int
    source_height: int
    mode: str  # AUTO or MANUAL_OVERRIDE


@dataclass(frozen=True, slots=True)
class AliasChoice:
    entity_id: str
    display_text: str
    matched_text: str
    knowledge_kind: GameKnowledgeKind
    priority: int


PERK_SLOT_LABELS = (
    "パーク1（上向き）",
    "パーク2（右向き）",
    "パーク3（下向き）",
    "パーク4（左向き）",
)
ADDON_SLOT_LABELS = ("アドオン1", "アドオン2")


def _load_profile(path: str | Path) -> DBDHudRoiProfile:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("指定したHUDプロファイルJSONが見つかりません。")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("HUDプロファイルJSONを読み取れませんでした。") from exc
    return DBDHudRoiProfile.from_dict(payload)


def resolve_training_hud_profile(
    *,
    video_path: str | Path,
    registry_root: str | Path,
    manual_profile_path: str | Path | None = None,
    frame_index: int = 0,
    ui_scale_percent: int | None = None,
    game_version: str | None = None,
    inspector: FFmpegFrameInspector | None = None,
) -> TrainingHudProfileBinding:
    """Resolve the exact profile used by video learning.

    A manual path is an advanced override, but it is still compatibility checked.
    Without an override, the workspace registry is resolved conservatively and
    ambiguity fails closed.
    """
    source = Path(video_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("学習元動画が見つかりません。")

    active_inspector = inspector or FFmpegFrameInspector()
    geometry = active_inspector.probe_geometry(source)

    manual = str(manual_profile_path or "").strip()
    if manual:
        profile = _load_profile(manual)
        resolution = DBDHudProfileResolver((profile,)).resolve(
            frame_width=geometry.width,
            frame_height=geometry.height,
            ui_scale_percent=ui_scale_percent,
            game_version=game_version,
        )
        return TrainingHudProfileBinding(
            profile=profile,
            profile_path=str(Path(manual).expanduser().resolve()),
            score_milli=resolution.score_milli,
            evidence=resolution.evidence,
            source_width=geometry.width,
            source_height=geometry.height,
            mode="MANUAL_OVERRIDE",
        )

    registry = HudProfileRegistry(registry_root)
    resolver = DBDHudVideoProfileResolver(
        registry,
        inspector=active_inspector,
    )
    resolution = resolver.resolve_video(
        video_path=source,
        frame_index=frame_index,
        ui_scale_percent=ui_scale_percent,
        game_version=game_version,
    )
    profile_path = registry.profile_directory(resolution.profile.profile_id) / "profile.json"
    if not profile_path.is_file():
        raise ValueError("自動判定したHUDプロファイルの保存ファイルが見つかりません。")
    return TrainingHudProfileBinding(
        profile=resolution.profile,
        profile_path=str(profile_path.resolve()),
        score_milli=resolution.score_milli,
        evidence=resolution.evidence,
        source_width=geometry.width,
        source_height=geometry.height,
        mode="AUTO",
    )


def training_roi(
    profile: DBDHudRoiProfile,
    domain: VisualTrainingDomain,
    slot: int | None,
) -> NormalizedROI:
    if domain is VisualTrainingDomain.PERK_ICON:
        if slot is None:
            raise ValueError("パーク学習にはスロットが必要です。")
        return profile.perk_slot_roi(slot)
    if domain is VisualTrainingDomain.ADDON_ICON:
        if slot is None:
            raise ValueError("アドオン学習にはスロットが必要です。")
        return profile.addon_slot_roi(slot)
    if domain is VisualTrainingDomain.ITEM_ICON:
        return profile.item_slot_roi()
    if domain is VisualTrainingDomain.SURVIVOR_HUD:
        if slot is None:
            raise ValueError("サバイバーHUD学習にはスロットが必要です。")
        return profile.survivor_slot_roi(slot)
    if domain is VisualTrainingDomain.KILLER_SPECIFIC_HUD:
        if slot is None:
            raise ValueError("キラー固有HUD学習にはサバイバースロットが必要です。")
        return profile.survivor_slot_roi(slot)
    if domain is VisualTrainingDomain.KILLER_POWER:
        if profile.killer_power_hud is None:
            raise ValueError("キラー能力HUDがこのHUDプロファイルで未設定です。")
        return profile.killer_power_hud
    if domain is VisualTrainingDomain.STATUS_EFFECT_POSITIVE:
        if profile.bottom_right_positive_effects is None:
            raise ValueError("ポジティブ状態効果HUDがこのHUDプロファイルで未設定です。")
        return profile.bottom_right_positive_effects
    if domain is VisualTrainingDomain.STATUS_EFFECT_NEGATIVE:
        if profile.bottom_right_negative_effects is None:
            raise ValueError("ネガティブ状態効果HUDがこのHUDプロファイルで未設定です。")
        return profile.bottom_right_negative_effects
    raise ValueError(f"未対応の学習対象です: {domain.value}")


def roi_pixel_rect(
    profile: DBDHudRoiProfile,
    *,
    domain: VisualTrainingDomain,
    slot: int | None,
    source_width: int,
    source_height: int,
) -> PixelRect:
    """Return the same pixel rectangle used by the calibration editor."""
    roi = training_roi(profile, domain, slot)
    editor = RoiPixelEditor(
        source_width=source_width,
        source_height=source_height,
        rois={roi.roi_id: roi},
    )
    return editor.pixel_rect(roi.roi_id)


def alias_choices(
    catalog: EntityAliasCatalog,
    *,
    knowledge_kind: GameKnowledgeKind,
    limit: int = 500,
) -> tuple[AliasChoice, ...]:
    """Pre-populate user choices from Knowledge/Alias without promoting status."""
    rows = catalog.search(
        "",
        knowledge_kind=knowledge_kind,
        verified_only=False,
        limit=limit,
    )
    selected: dict[str, AliasChoice] = {}
    for row in rows:
        choice = AliasChoice(
            entity_id=row.entity_id,
            display_text=f"{row.matched_text}  [{row.entity_id}]",
            matched_text=row.matched_text,
            knowledge_kind=row.knowledge_kind,
            priority=row.priority,
        )
        existing = selected.get(row.entity_id)
        if existing is None or choice.priority > existing.priority:
            selected[row.entity_id] = choice
    return tuple(
        sorted(
            selected.values(),
            key=lambda item: (-item.priority, item.matched_text, item.entity_id),
        )
    )


def slot_specifications(
    domain: VisualTrainingDomain,
) -> tuple[tuple[int | None, str], ...]:
    if domain is VisualTrainingDomain.PERK_ICON:
        return tuple((index, label) for index, label in enumerate(PERK_SLOT_LABELS))
    if domain is VisualTrainingDomain.ADDON_ICON:
        return tuple((index, label) for index, label in enumerate(ADDON_SLOT_LABELS))
    if domain is VisualTrainingDomain.SURVIVOR_HUD:
        return ((0, "サバイバー1"), (1, "サバイバー2"), (2, "サバイバー3"), (3, "サバイバー4"))
    if domain is VisualTrainingDomain.KILLER_SPECIFIC_HUD:
        return ((0, "サバイバー1"), (1, "サバイバー2"), (2, "サバイバー3"), (3, "サバイバー4"))
    if domain is VisualTrainingDomain.ITEM_ICON:
        return ((None, "アイテム"),)
    if domain is VisualTrainingDomain.KILLER_POWER:
        return ((None, "キラー能力"),)
    if domain is VisualTrainingDomain.STATUS_EFFECT_POSITIVE:
        return ((None, "ポジティブ状態効果"),)
    if domain is VisualTrainingDomain.STATUS_EFFECT_NEGATIVE:
        return ((None, "ネガティブ状態効果"),)
    return ()
