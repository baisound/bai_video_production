from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import ProductError, ProductErrorCategory


class H3AccelerationMode(str, Enum):
    NATIVE = "NATIVE"
    SPECTRUM_QUALITY = "SPECTRUM_QUALITY"
    SPECTRUM_FAST = "SPECTRUM_FAST"


SPECTRUM_CLASS_TYPE = "SpectrumApplyMiniMaxH3"
_COMPETING_CLASS_TOKENS = ("easycache", "lazycache")


def _workflow_nodes(workflow: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(node for node in workflow.values() if isinstance(node, dict))


def _active_spectrum_nodes(workflow: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for node in _workflow_nodes(workflow):
        if node.get("class_type") != SPECTRUM_CLASS_TYPE:
            continue
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        if inputs.get("enabled") is False:
            continue
        result.append(node)
    return tuple(result)


def competing_acceleration_class_types(workflow: dict[str, Any]) -> tuple[str, ...]:
    found: set[str] = set()
    for node in _workflow_nodes(workflow):
        class_type = node.get("class_type")
        if not isinstance(class_type, str):
            continue
        lowered = class_type.lower()
        if any(token in lowered for token in _COMPETING_CLASS_TOKENS):
            found.add(class_type)
    return tuple(sorted(found))


@dataclass(frozen=True, slots=True)
class H3AccelerationContract:
    mode: H3AccelerationMode = H3AccelerationMode.NATIVE

    @property
    def approximate(self) -> bool:
        return self.mode is not H3AccelerationMode.NATIVE

    def validate_workflow(self, workflow: dict[str, Any], *, configured_vram_floor_bytes: int = 0) -> dict[str, Any]:
        spectrum_nodes = _active_spectrum_nodes(workflow)
        competing = competing_acceleration_class_types(workflow)
        if spectrum_nodes and competing:
            raise ProductError(
                "ERR_INPUT_H3_ACCELERATOR_CONFLICT",
                "Spectrum must not be combined with EasyCache/LazyCache acceleration in one H3 workflow",
                ProductErrorCategory.VALIDATION,
                details={"competing_class_types": list(competing)},
            )
        if self.mode is H3AccelerationMode.NATIVE:
            if spectrum_nodes:
                raise ProductError(
                    "ERR_INPUT_H3_NATIVE_WORKFLOW_ACCELERATED",
                    "NATIVE H3 acceleration mode requires Spectrum to be disabled or absent",
                    ProductErrorCategory.VALIDATION,
                )
        elif not spectrum_nodes:
            raise ProductError(
                "ERR_PROVIDER_H3_SPECTRUM_NODE_REQUIRED",
                "selected Spectrum acceleration mode requires an active SpectrumApplyMiniMaxH3 workflow node",
                ProductErrorCategory.NOT_SUPPORTED,
            )

        history_storage: set[str] = set()
        for node in spectrum_nodes:
            inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
            value = inputs.get("history_storage", "system_ram")
            if isinstance(value, str):
                history_storage.add(value)
        if "vram" in history_storage and configured_vram_floor_bytes <= 0:
            raise ProductError(
                "ERR_RESOURCE_H3_SPECTRUM_VRAM_FLOOR_REQUIRED",
                "Spectrum VRAM history storage requires an explicit positive free-VRAM admission floor",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        return {
            "mode": self.mode.value,
            "approximate": self.approximate,
            "spectrum_node_count": len(spectrum_nodes),
            "history_storage": sorted(history_storage),
            "competing_class_types": list(competing),
            "external_node_class": SPECTRUM_CLASS_TYPE if spectrum_nodes else None,
            "external_node_license": "GPL-3.0",
            "external_node_code_incorporated": False,
        }
