"""Deterministic multi-icon segmentation for bottom-right status-effect regions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import median

from .dbd_killer_status_temporal import EffectPolarity
from .dbd_vision_slices import GrayImage, NormalizedROI
from .serialization import sha256_bytes


_REGION_BY_POLARITY = {
    EffectPolarity.POSITIVE: "bottom_right_positive_effects",
    EffectPolarity.NEGATIVE: "bottom_right_negative_effects",
}


class StatusIconSegmentationStatus(str, Enum):
    SEGMENTED = "SEGMENTED"
    EMPTY = "EMPTY"
    REGION_UNAVAILABLE = "REGION_UNAVAILABLE"
    OVERFLOW = "OVERFLOW"


@dataclass(frozen=True, slots=True)
class StatusIconSegmentationProfile:
    contrast_threshold: int = 48
    bridge_pixels: int = 1
    minimum_width: int = 4
    minimum_height: int = 4
    minimum_foreground_pixels: int = 12
    maximum_icons: int = 8
    crop_padding_pixels: int = 1

    def __post_init__(self) -> None:
        values = (
            self.contrast_threshold, self.bridge_pixels, self.minimum_width,
            self.minimum_height, self.minimum_foreground_pixels,
            self.maximum_icons, self.crop_padding_pixels,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise ValueError("status segmentation profile values must be integers")
        if not 1 <= self.contrast_threshold <= 255:
            raise ValueError("contrast_threshold must be 1..255")
        if not 0 <= self.bridge_pixels <= 8 or not 0 <= self.crop_padding_pixels <= 32:
            raise ValueError("status segmentation pixel padding is out of range")
        if min(self.minimum_width, self.minimum_height, self.minimum_foreground_pixels, self.maximum_icons) < 1:
            raise ValueError("status segmentation minima and maximum_icons must be positive")
        if self.maximum_icons > 64:
            raise ValueError("maximum_icons must not exceed 64")


@dataclass(frozen=True, slots=True)
class StatusIconSegmentCandidate:
    ordinal: int
    polarity: EffectPolarity
    region_roi_id: str
    crop_roi: NormalizedROI
    foreground_pixels: int
    segmentation_score_milli: int
    crop_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ValueError("status segment ordinal must be non-negative")
        if not isinstance(self.polarity, EffectPolarity):
            raise ValueError("invalid status segment polarity")
        if not self.region_roi_id or len(self.region_roi_id) > 128:
            raise ValueError("status segment region_roi_id must be bounded text")
        if self.region_roi_id != _REGION_BY_POLARITY[self.polarity]:
            raise ValueError("status segment polarity and region namespace must agree")
        if self.crop_roi.roi_id != f"{self.region_roi_id}/segment_{self.ordinal}":
            raise ValueError("status segment ROI id must match region and ordinal")
        if self.foreground_pixels < 1:
            raise ValueError("status segment must contain foreground pixels")
        if not 0 <= self.segmentation_score_milli <= 1000:
            raise ValueError("segmentation_score_milli must be 0..1000")
        if not self.crop_sha256.startswith("sha256:") or len(self.crop_sha256) != 71:
            raise ValueError("status segment crop_sha256 must be canonical")


@dataclass(frozen=True, slots=True)
class StatusIconSegmentationResult:
    polarity: EffectPolarity
    region_roi_id: str
    status: StatusIconSegmentationStatus
    candidates: tuple[StatusIconSegmentCandidate, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.polarity, EffectPolarity):
            raise ValueError("invalid status segmentation polarity")
        if not self.region_roi_id or len(self.region_roi_id) > 128:
            raise ValueError("status segmentation region_roi_id must be bounded text")
        if self.region_roi_id != _REGION_BY_POLARITY[self.polarity]:
            raise ValueError("status segmentation polarity and region namespace must agree")
        if not isinstance(self.status, StatusIconSegmentationStatus):
            raise ValueError("invalid status segmentation status")
        if self.status is StatusIconSegmentationStatus.SEGMENTED and not self.candidates:
            raise ValueError("SEGMENTED result requires candidates")
        if self.status is not StatusIconSegmentationStatus.SEGMENTED and self.candidates:
            raise ValueError("non-SEGMENTED result cannot expose partial candidates")
        if any(item.polarity is not self.polarity or item.region_roi_id != self.region_roi_id for item in self.candidates):
            raise ValueError("status segment candidate scope mismatch")
        if tuple(item.ordinal for item in self.candidates) != tuple(range(len(self.candidates))):
            raise ValueError("status segment ordinals must be contiguous")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise ValueError("status segmentation reason_codes must be unique and sorted")

    @classmethod
    def unavailable(cls, polarity: EffectPolarity, region_roi_id: str) -> "StatusIconSegmentationResult":
        return cls(
            polarity, region_roi_id, StatusIconSegmentationStatus.REGION_UNAVAILABLE,
            reason_codes=("STATUS_EFFECT_REGION_NOT_CALIBRATED",),
        )


class StatusIconSegmenter:
    """Segment high-contrast components without claiming effect identity."""

    def __init__(self, profile: StatusIconSegmentationProfile = StatusIconSegmentationProfile()) -> None:
        if not isinstance(profile, StatusIconSegmentationProfile):
            raise ValueError("profile must be a StatusIconSegmentationProfile")
        self.profile = profile

    @staticmethod
    def _border_values(image: GrayImage) -> tuple[int, ...]:
        values = []
        values.extend(image.pixels[:image.width])
        if image.height > 1:
            values.extend(image.pixels[(image.height - 1) * image.width:])
        for y in range(1, max(1, image.height - 1)):
            values.append(image.pixels[y * image.width])
            if image.width > 1:
                values.append(image.pixels[y * image.width + image.width - 1])
        return tuple(values)

    def _foreground(self, image: GrayImage) -> bytearray:
        background = int(median(self._border_values(image)))
        base = bytearray(
            1 if abs(value - background) >= self.profile.contrast_threshold else 0
            for value in image.pixels
        )
        radius = self.profile.bridge_pixels
        if radius == 0:
            return base
        expanded = bytearray(len(base))
        for y in range(image.height):
            for x in range(image.width):
                if not base[y * image.width + x]:
                    continue
                for dy in range(-radius, radius + 1):
                    target_y = y + dy
                    if not 0 <= target_y < image.height:
                        continue
                    for dx in range(-radius, radius + 1):
                        target_x = x + dx
                        if 0 <= target_x < image.width:
                            expanded[target_y * image.width + target_x] = 1
        return expanded

    @staticmethod
    def _components(mask: bytearray, width: int, height: int) -> tuple[tuple[int, int, int, int], ...]:
        seen = bytearray(len(mask))
        boxes = []
        for start in range(len(mask)):
            if not mask[start] or seen[start]:
                continue
            stack = [start]
            seen[start] = 1
            left = right = start % width
            top = bottom = start // width
            while stack:
                current = stack.pop()
                x, y = current % width, current // width
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        index = ny * width + nx
                        if mask[index] and not seen[index]:
                            seen[index] = 1
                            stack.append(index)
            boxes.append((left, top, right + 1, bottom + 1))
        return tuple(boxes)

    @staticmethod
    def _crop(image: GrayImage, box: tuple[int, int, int, int]) -> GrayImage:
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        pixels = bytearray(width * height)
        for y in range(height):
            source = (top + y) * image.width + left
            pixels[y * width:(y + 1) * width] = image.pixels[source:source + width]
        return GrayImage(width, height, bytes(pixels))

    def segment(
        self, image: GrayImage, *, polarity: EffectPolarity, region_roi_id: str,
    ) -> StatusIconSegmentationResult:
        if not isinstance(image, GrayImage):
            raise ValueError("image must be a GrayImage")
        if image.width > 2048 or image.height > 2048 or image.width * image.height > 4_194_304:
            raise ValueError("status segmentation image exceeds bounded dimensions")
        if not isinstance(polarity, EffectPolarity):
            raise ValueError("polarity must be an EffectPolarity")
        if not region_roi_id or len(region_roi_id) > 128:
            raise ValueError("region_roi_id must be bounded text")
        original = self._foreground(image)
        boxes = []
        padding = self.profile.crop_padding_pixels
        for left, top, right, bottom in self._components(original, image.width, image.height):
            left, top = max(0, left - padding), max(0, top - padding)
            right, bottom = min(image.width, right + padding), min(image.height, bottom + padding)
            width, height = right - left, bottom - top
            foreground = sum(
                original[y * image.width + x]
                for y in range(top, bottom) for x in range(left, right)
            )
            if (
                width < self.profile.minimum_width
                or height < self.profile.minimum_height
                or foreground < self.profile.minimum_foreground_pixels
            ):
                continue
            boxes.append((left, top, right, bottom, foreground))
        boxes.sort(key=lambda item: (item[1], item[0], item[3], item[2]))
        if not boxes:
            return StatusIconSegmentationResult(
                polarity, region_roi_id, StatusIconSegmentationStatus.EMPTY,
                reason_codes=("NO_STATUS_ICON_COMPONENTS",),
            )
        if len(boxes) > self.profile.maximum_icons:
            return StatusIconSegmentationResult(
                polarity, region_roi_id, StatusIconSegmentationStatus.OVERFLOW,
                reason_codes=("STATUS_ICON_COMPONENT_LIMIT_EXCEEDED",),
            )
        candidates = []
        for ordinal, (left, top, right, bottom, foreground) in enumerate(boxes):
            crop = self._crop(image, (left, top, right, bottom))
            roi = NormalizedROI(
                f"{region_roi_id}/segment_{ordinal}",
                left / image.width, top / image.height,
                (right - left) / image.width, (bottom - top) / image.height,
            )
            score = min(1000, 600 + (400 * foreground // self.profile.minimum_foreground_pixels))
            digest_input = f"{crop.width}x{crop.height}\0".encode("ascii") + crop.pixels
            candidates.append(StatusIconSegmentCandidate(
                ordinal, polarity, region_roi_id, roi, foreground, score,
                sha256_bytes(digest_input),
            ))
        return StatusIconSegmentationResult(
            polarity, region_roi_id, StatusIconSegmentationStatus.SEGMENTED,
            tuple(candidates), ("STATUS_ICON_COMPONENTS_SEGMENTED",),
        )


__all__ = [
    "StatusIconSegmentCandidate", "StatusIconSegmentationProfile",
    "StatusIconSegmentationResult", "StatusIconSegmentationStatus", "StatusIconSegmenter",
]
