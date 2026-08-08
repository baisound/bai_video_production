from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import ProductError, ProductErrorCategory


class H3SingleFrameMode(str, Enum):
    SINGLE_FRAME_EDIT = "SINGLE_FRAME_EDIT"
    START_END_INTERPOLATE = "START_END_INTERPOLATE"


@dataclass(frozen=True, slots=True)
class H3SingleFrameContract:
    mode: H3SingleFrameMode
    requested_frame_count: int = 5
    selected_frame_index: int = 0
    temporal_rope_strength: float = 0.0

    def __post_init__(self) -> None:
        if self.requested_frame_count < 1 or self.requested_frame_count > 3600:
            raise ValueError("requested_frame_count must be in 1..3600")
        if self.selected_frame_index < 0:
            raise ValueError("selected_frame_index must be non-negative")
        if not 0.0 <= self.temporal_rope_strength <= 1.0:
            raise ValueError("temporal_rope_strength must be between 0 and 1")

    @property
    def actual_frame_count(self) -> int:
        # The reviewed external ComfyUI node requires frame_count % 17 == 5,
        # with a minimum of 5. BAI normalizes the request before workflow
        # materialization so Evidence can record requested vs actual values.
        count = max(5, self.requested_frame_count)
        remainder = count % 17
        if remainder == 5:
            return count
        return count + ((5 - remainder) % 17)

    @property
    def required_reference_count(self) -> int:
        return 1 if self.mode is H3SingleFrameMode.SINGLE_FRAME_EDIT else 2

    @property
    def required_node_classes(self) -> tuple[str, ...]:
        if self.mode is H3SingleFrameMode.SINGLE_FRAME_EDIT:
            return ("MiniMaxH3SingleFrameEdit", "MiniMaxH3SelectFrame")
        return ("MiniMaxH3StartEndFrameInterpolate", "MiniMaxH3SelectFrame")

    def validate_reference_count(self, count: int) -> None:
        if count != self.required_reference_count:
            raise ProductError(
                "ERR_INPUT_H3_SINGLE_FRAME_REFERENCE_COUNT",
                "H3 single-frame mode received an invalid canonical reference count",
                ProductErrorCategory.VALIDATION,
                details={"mode": self.mode.value, "required": self.required_reference_count, "actual": count},
            )

    def validate_selected_frame(self) -> None:
        if self.selected_frame_index >= self.actual_frame_count:
            raise ProductError(
                "ERR_INPUT_H3_SINGLE_FRAME_INDEX",
                "selected H3 frame index is outside the normalized frame sequence",
                ProductErrorCategory.VALIDATION,
                details={"selected_frame_index": self.selected_frame_index, "actual_frame_count": self.actual_frame_count},
            )

    def validate_workflow_classes(self, classes: tuple[str, ...]) -> None:
        available = set(classes)
        missing = [name for name in self.required_node_classes if name not in available]
        if missing:
            raise ProductError(
                "ERR_PROVIDER_H3_SINGLE_FRAME_WORKFLOW_MISMATCH",
                "H3 single-frame workflow is missing required custom-node classes",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                retryable=False,
                details={"missing_node_classes": missing, "mode": self.mode.value},
            )

    def evidence_fields(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "requested_frame_count": self.requested_frame_count,
            "actual_frame_count": self.actual_frame_count,
            "selected_frame_index": self.selected_frame_index,
            "temporal_rope_strength": self.temporal_rope_strength,
        }
