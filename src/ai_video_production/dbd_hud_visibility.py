"""Shared visibility semantics for DbD HUD identity regions."""

from __future__ import annotations

from enum import Enum


class HudVisibility(str, Enum):
    VISIBLE = "VISIBLE"
    PARTIALLY_OCCLUDED = "PARTIALLY_OCCLUDED"
    HIDDEN = "HIDDEN"
    UNREADABLE = "UNREADABLE"
    UNKNOWN = "UNKNOWN"


def visibility_training_label(prefix: str, label: str) -> HudVisibility | None:
    prefix = prefix.strip().upper()
    mapping = {
        f"{prefix}_VISIBLE": HudVisibility.VISIBLE,
        f"{prefix}_PARTIALLY_OCCLUDED": HudVisibility.PARTIALLY_OCCLUDED,
        f"{prefix}_HIDDEN": HudVisibility.HIDDEN,
        f"{prefix}_UNREADABLE": HudVisibility.UNREADABLE,
    }
    return mapping.get(label)


__all__ = ["HudVisibility", "visibility_training_label"]
