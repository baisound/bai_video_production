"""Shared Japanese runtime-selector options for DbD local analysis workflows."""
from __future__ import annotations

from collections.abc import Mapping

WHISPER_MODEL_OPTIONS_JA: dict[str, str] = {
    "小（small・推奨）": "small",
    "中（medium）": "medium",
    "大（large-v3）": "large-v3",
}
DEVICE_OPTIONS_JA: dict[str, str] = {
    "自動": "auto",
    "CPU": "cpu",
    "GPU（CUDA）": "cuda",
}
COMPUTE_OPTIONS_JA: dict[str, str] = {
    "省メモリ（int8）": "int8",
    "半精度（float16）": "float16",
    "自動": "default",
}


def display_for_value(options: Mapping[str, str], value: str, fallback: str) -> str:
    return next((label for label, raw in options.items() if raw == value), fallback)


__all__ = [
    "WHISPER_MODEL_OPTIONS_JA",
    "DEVICE_OPTIONS_JA",
    "COMPUTE_OPTIONS_JA",
    "display_for_value",
]
