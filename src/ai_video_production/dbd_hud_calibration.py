"""TASK-049 DbD HUD calibration, profile resolution, and anchor alignment.

The calibration contract keeps HUD geometry normalized and versioned.  Runtime
profile selection is fail-closed when a calibrated profile cannot be resolved
unambiguously.  Anchor alignment only permits a small bounded translation;
it never silently rescales or invents new geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Iterable, Sequence

from .dbd_vision_slices import (
    DBDHudRoiProfile,
    FFmpegSliceExtractor,
    GrayImage,
    HudAnchorReference,
    NormalizedROI,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import sha256_bytes


_PARENT_ROI_BY_PREFIX = {
    "survivor_slot_": "lower_left_survivor_hud",
    "perk_slot_": "bottom_right_perks",
    "addon_slot_": "lower_left_loadout_hud",
    "item_slot": "lower_left_loadout_hud",
    "bottom_right_positive_effects": "bottom_right_perks",
    "bottom_right_negative_effects": "bottom_right_perks",
}


def _version_tuple(value: str | None) -> tuple[int, ...] | None:
    if value is None or not value.strip():
        return None
    parts = [int(part) for part in re.findall(r"\d+", value)]
    return tuple(parts) if parts else None


def _version_compatible(profile: DBDHudRoiProfile, game_version: str | None) -> bool:
    current = _version_tuple(game_version)
    if current is None:
        return True
    lower, upper = _version_tuple(profile.game_version_from), _version_tuple(profile.game_version_to)
    if lower is not None and current < lower:
        return False
    if upper is not None and current > upper:
        return False
    return True


@dataclass(frozen=True, slots=True)
class FrameGeometry:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 64 or self.height < 64:
            raise ValueError("invalid frame geometry")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


class FFmpegFrameInspector:
    """Bounded FFmpeg/ffprobe helper for calibration previews.

    Probe results are cached per source identity and video previews use timestamp
    seeking instead of decoding from frame zero for every transport update.
    """

    def __init__(self, *, ffmpeg_executable: str = "ffmpeg", ffprobe_executable: str = "ffprobe") -> None:
        self.ffmpeg_executable = ffmpeg_executable
        self.ffprobe_executable = ffprobe_executable
        self._probe_cache: dict[tuple[str, int, int], tuple[FrameGeometry, float]] = {}

    @staticmethod
    def _parse_rate(value: str | None) -> float:
        raw = (value or "").strip()
        if not raw or raw == "0/0":
            raise ValueError("video FPS is unavailable")
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            fps = int(numerator) / int(denominator)
        else:
            fps = float(raw)
        if fps <= 0:
            raise ValueError("video FPS must be positive")
        return fps

    def _probe_video(self, source_path: str | Path) -> tuple[FrameGeometry, float]:
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("calibration source does not exist")
        stat = source.stat()
        cache_key = (str(source.resolve()), stat.st_size, stat.st_mtime_ns)
        cached = self._probe_cache.get(cache_key)
        if cached is not None:
            return cached
        cmd = [
            self.ffprobe_executable, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate",
            "-of", "json", str(source),
        ]
        try:
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductError("ERR_DBD_HUD_FFPROBE_UNAVAILABLE", "ffprobe is unavailable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if completed.returncode != 0:
            raise ProductError("ERR_DBD_HUD_FFPROBE_FAILED", "ffprobe failed to inspect calibration source", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True)
        try:
            stream = json.loads(completed.stdout.decode("utf-8"))["streams"][0]
            geometry = FrameGeometry(int(stream["width"]), int(stream["height"]))
            fps = self._parse_rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        except Exception as exc:
            raise ProductError("ERR_DBD_HUD_FRAME_GEOMETRY", "video frame geometry/fps could not be resolved", ProductErrorCategory.DATA_INTEGRITY) from exc
        self._probe_cache.clear()
        self._probe_cache[cache_key] = (geometry, fps)
        return geometry, fps

    def probe_geometry(self, source_path: str | Path) -> FrameGeometry:
        geometry, _fps = self._probe_video(source_path)
        return geometry

    def extract_preview_pgm(
        self, *, source_path: str | Path, output_path: str | Path, frame_index: int = 0,
        maximum_width: int = 960, maximum_height: int = 540,
    ) -> tuple[Path, FrameGeometry, FrameGeometry]:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        source = Path(source_path)
        original, fps = self._probe_video(source)
        scale = min(maximum_width / original.width, maximum_height / original.height, 1.0)
        preview = FrameGeometry(max(64, round(original.width * scale)), max(64, round(original.height * scale)))
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        seek_seconds = frame_index / fps
        vf = f"scale={preview.width}:{preview.height}:flags=area,format=gray"
        cmd = [
            self.ffmpeg_executable, "-hide_banner", "-loglevel", "error",
            "-ss", f"{seek_seconds:.6f}", "-i", str(source),
            "-vf", vf, "-frames:v", "1", "-f", "image2",
            "-vcodec", "pgm", "-y", str(target),
        ]
        try:
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductError("ERR_DBD_HUD_FFMPEG_UNAVAILABLE", "FFmpeg is unavailable", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if completed.returncode != 0 or not target.is_file():
            raise ProductError("ERR_DBD_HUD_PREVIEW_FAILED", "FFmpeg failed to extract calibration preview", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True)
        return target, original, preview


class HudProfileRegistry:
    """Portable on-disk registry for calibrated HUD profiles."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def profile_directory(self, profile_id: str) -> Path:
        if not profile_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in profile_id):
            raise ValueError("profile_id must be filesystem-safe")
        return self.root / profile_id

    def save(self, profile: DBDHudRoiProfile) -> Path:
        directory = self.profile_directory(profile.profile_id)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "profile.json"
        target.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def load(self, profile_id: str) -> DBDHudRoiProfile:
        path = self.profile_directory(profile_id) / "profile.json"
        return DBDHudRoiProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_profiles(self) -> tuple[DBDHudRoiProfile, ...]:
        rows: list[DBDHudRoiProfile] = []
        for path in sorted(self.root.glob("*/profile.json")):
            try:
                rows.append(DBDHudRoiProfile.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return tuple(rows)

    def store_anchor(self, *, profile_id: str, roi: NormalizedROI, image: GrayImage, source_ref: str) -> HudAnchorReference:
        directory = self.profile_directory(profile_id) / "anchors"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{roi.roi_id}.pgm"
        normalized = image.crop_normalized(roi).resized(96, 96)
        normalized.write_pgm(target)
        raw = target.read_bytes()
        return HudAnchorReference(
            roi_id=roi.roi_id,
            feature_hex=f"{normalized.dhash64():016x}",
            source_sha256=sha256_bytes(raw),
            source_ref=str(target.relative_to(self.root)),
        )


@dataclass(frozen=True, slots=True)
class ProfileResolution:
    profile: DBDHudRoiProfile
    score_milli: int
    evidence: tuple[str, ...]


class DBDHudProfileResolver:
    """Resolve a calibrated profile from frame/UI/version metadata.

    Resolution is intentionally conservative.  If two profiles remain within
    ``ambiguity_margin_milli`` the resolver fails closed rather than guessing.
    """

    def __init__(self, profiles: Sequence[DBDHudRoiProfile], *, acceptance_milli: int = 650, ambiguity_margin_milli: int = 75) -> None:
        self.profiles = tuple(profiles)
        self.acceptance_milli = acceptance_milli
        self.ambiguity_margin_milli = ambiguity_margin_milli

    def resolve(
        self, *, frame_width: int, frame_height: int, ui_scale_percent: int | None = None,
        game_version: str | None = None, anchor_scores: dict[str, int] | None = None,
    ) -> ProfileResolution:
        geometry = FrameGeometry(frame_width, frame_height)
        rows: list[ProfileResolution] = []
        for profile in self.profiles:
            if profile.calibrated_frame_width is None or profile.calibrated_frame_height is None:
                continue
            if not _version_compatible(profile, game_version):
                continue
            aspect_error = abs(profile.aspect_ratio - geometry.aspect_ratio) / max(profile.aspect_ratio, geometry.aspect_ratio)
            if aspect_error > 0.035:
                continue
            score = max(0, 700 - round(aspect_error * 8000))
            evidence = [f"aspect_error={aspect_error:.5f}"]
            if profile.calibrated_frame_width == frame_width and profile.calibrated_frame_height == frame_height:
                score += 150; evidence.append("exact_resolution")
            if ui_scale_percent is not None and profile.ui_scale_percent is not None:
                delta = abs(ui_scale_percent - profile.ui_scale_percent)
                if delta > 10:
                    continue
                score += max(0, 100 - delta * 10); evidence.append(f"ui_scale_delta={delta}")
            if anchor_scores and profile.profile_id in anchor_scores:
                anchor = anchor_scores[profile.profile_id]
                score = round(score * 0.55 + anchor * 0.45)
                evidence.append(f"anchor={anchor}")
            rows.append(ProfileResolution(profile, min(1000, score), tuple(evidence)))
        rows.sort(key=lambda row: (-row.score_milli, -row.profile.profile_version, row.profile.profile_id))
        if not rows or rows[0].score_milli < self.acceptance_milli:
            raise ProductError("ERR_DBD_HUD_PROFILE_UNKNOWN", "No compatible calibrated DbD HUD profile could be resolved", ProductErrorCategory.VALIDATION, details={"frame": f"{frame_width}x{frame_height}"})
        if len(rows) > 1 and rows[0].score_milli - rows[1].score_milli < self.ambiguity_margin_milli:
            raise ProductError("ERR_DBD_HUD_PROFILE_AMBIGUOUS", "Multiple DbD HUD profiles match; calibration selection is required", ProductErrorCategory.VALIDATION, details={"candidates": [rows[0].profile.profile_id, rows[1].profile.profile_id]})
        return rows[0]


@dataclass(frozen=True, slots=True)
class RoiCorrection:
    roi_id: str
    dx_normalized: float
    dy_normalized: float
    confidence_milli: int


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    profile: DBDHudRoiProfile
    corrections: tuple[RoiCorrection, ...]
    confidence_milli: int


def _shift_roi(roi: NormalizedROI, dx: float, dy: float) -> NormalizedROI:
    x = min(max(0.0, roi.x + dx), 1.0 - roi.width)
    y = min(max(0.0, roi.y + dy), 1.0 - roi.height)
    return NormalizedROI(roi.roi_id, x, y, roi.width, roi.height)


class HudAnchorAligner:
    """Search a bounded translation around registered anchor ROIs."""

    anchor_roi_ids = ("lower_left_survivor_hud", "lower_left_loadout_hud", "upper_right_notifications", "bottom_right_perks", "killer_power_hud")

    def __init__(self, *, extractor: FFmpegSliceExtractor | None = None, search_radius_pixels: int = 8, search_step_pixels: int = 4, acceptance_milli: int = 700) -> None:
        if search_radius_pixels < 0 or search_step_pixels < 1:
            raise ValueError("invalid anchor search window")
        self.extractor = extractor or FFmpegSliceExtractor()
        self.search_radius_pixels = search_radius_pixels
        self.search_step_pixels = search_step_pixels
        self.acceptance_milli = acceptance_milli

    def align(
        self, *, video_path: str | Path, frame_index: int, profile: DBDHudRoiProfile,
        frame_width: int, frame_height: int, working_directory: str | Path | None = None,
    ) -> AlignmentResult:
        if not profile.anchors:
            return AlignmentResult(profile, (), 1000)
        temporary = None
        if working_directory is None:
            temporary = tempfile.TemporaryDirectory(prefix="bvp-dbd-anchor-")
            root = Path(temporary.name)
        else:
            root = Path(working_directory); root.mkdir(parents=True, exist_ok=True)
        corrections: list[RoiCorrection] = []
        try:
            for anchor in profile.anchors:
                try:
                    base_roi = profile.roi_by_id(anchor.roi_id)
                except KeyError:
                    continue
                best: tuple[int, float, float] | None = None
                for dy_px in range(-self.search_radius_pixels, self.search_radius_pixels + 1, self.search_step_pixels):
                    for dx_px in range(-self.search_radius_pixels, self.search_radius_pixels + 1, self.search_step_pixels):
                        dx, dy = dx_px / frame_width, dy_px / frame_height
                        candidate = _shift_roi(base_roi, dx, dy)
                        out = root / f"{anchor.roi_id}-{dx_px:+d}-{dy_px:+d}.pgm"
                        path = self.extractor.extract_frame_roi(video_path=video_path, frame_index=frame_index, roi=candidate, output_path=out, width=96, height=96)
                        feature = GrayImage.read_pgm(path).dhash64()
                        distance = (feature ^ anchor.feature).bit_count()
                        confidence = max(0, 1000 - round(distance * 1000 / 64))
                        row = (confidence, dx, dy)
                        if best is None or row[0] > best[0] or (row[0] == best[0] and abs(row[1]) + abs(row[2]) < abs(best[1]) + abs(best[2])):
                            best = row
                if best is None or best[0] < self.acceptance_milli:
                    raise ProductError("ERR_DBD_HUD_ANCHOR_UNRESOLVED", "Registered HUD anchor could not be aligned confidently", ProductErrorCategory.VALIDATION, details={"profile_id": profile.profile_id, "roi_id": anchor.roi_id, "confidence_milli": 0 if best is None else best[0]})
                corrections.append(RoiCorrection(anchor.roi_id, best[1], best[2], best[0]))
            if not corrections:
                return AlignmentResult(profile, (), 1000)
            by_id = {item.roi_id: item for item in corrections}
            def correction_for(roi_id: str) -> RoiCorrection | None:
                if roi_id in by_id:
                    return by_id[roi_id]
                for prefix, parent in _PARENT_ROI_BY_PREFIX.items():
                    if roi_id.startswith(prefix):
                        return by_id.get(parent)
                return None
            def adjusted(roi: NormalizedROI) -> NormalizedROI:
                correction = correction_for(roi.roi_id)
                return roi if correction is None else _shift_roi(roi, correction.dx_normalized, correction.dy_normalized)
            updated = replace(
                profile,
                lower_left_survivor_hud=adjusted(profile.lower_left_survivor_hud),
                upper_right_notifications=adjusted(profile.upper_right_notifications),
                bottom_right_perks=adjusted(profile.bottom_right_perks),
                bottom_right_positive_effects=(
                    None if profile.bottom_right_positive_effects is None
                    else adjusted(profile.bottom_right_positive_effects)
                ),
                bottom_right_negative_effects=(
                    None if profile.bottom_right_negative_effects is None
                    else adjusted(profile.bottom_right_negative_effects)
                ),
                lower_left_loadout_hud=None if profile.lower_left_loadout_hud is None else adjusted(profile.lower_left_loadout_hud),
                item_slot=None if profile.item_slot is None else adjusted(profile.item_slot),
                addon_slots=tuple(adjusted(item) for item in profile.addon_slots),
                survivor_slots=tuple(adjusted(item) for item in profile.survivor_slots),
                perk_slots=tuple(adjusted(item) for item in profile.perk_slots),
                killer_power_hud=None if profile.killer_power_hud is None else adjusted(profile.killer_power_hud),
            )
            return AlignmentResult(updated, tuple(corrections), round(sum(item.confidence_milli for item in corrections) / len(corrections)))
        finally:
            if temporary is not None:
                temporary.cleanup()


class DBDHudVideoProfileResolver:
    """Resolve a registry profile for a video and optionally score anchors."""

    def __init__(self, registry: HudProfileRegistry, *, inspector: FFmpegFrameInspector | None = None, extractor: FFmpegSliceExtractor | None = None, acceptance_milli: int = 650) -> None:
        self.registry = registry
        self.inspector = inspector or FFmpegFrameInspector()
        self.extractor = extractor or FFmpegSliceExtractor()
        self.acceptance_milli = acceptance_milli

    def resolve_video(self, *, video_path: str | Path, frame_index: int = 0, ui_scale_percent: int | None = None, game_version: str | None = None) -> ProfileResolution:
        geometry = self.inspector.probe_geometry(video_path)
        profiles = self.registry.list_profiles()
        if not profiles:
            raise ProductError("ERR_DBD_HUD_PROFILE_REGISTRY_EMPTY", "No calibrated DbD HUD profiles are registered", ProductErrorCategory.VALIDATION)
        anchor_scores: dict[str, int] = {}
        with tempfile.TemporaryDirectory(prefix="bvp-dbd-profile-score-") as tmp:
            root = Path(tmp)
            for profile in profiles:
                scores: list[int] = []
                for anchor in profile.anchors:
                    try:
                        roi = profile.roi_by_id(anchor.roi_id)
                    except KeyError:
                        continue
                    target = root / f"{profile.profile_id}-{anchor.roi_id}.pgm"
                    try:
                        path = self.extractor.extract_frame_roi(video_path=video_path, frame_index=frame_index, roi=roi, output_path=target, width=96, height=96)
                    except Exception:
                        continue
                    feature = GrayImage.read_pgm(path).dhash64()
                    distance = (feature ^ anchor.feature).bit_count()
                    scores.append(max(0, 1000 - round(distance * 1000 / 64)))
                if scores:
                    anchor_scores[profile.profile_id] = round(sum(scores) / len(scores))
        return DBDHudProfileResolver(profiles, acceptance_milli=self.acceptance_milli).resolve(
            frame_width=geometry.width, frame_height=geometry.height,
            ui_scale_percent=ui_scale_percent, game_version=game_version,
            anchor_scores=anchor_scores,
        )


__all__ = [
    "AlignmentResult", "DBDHudProfileResolver", "DBDHudVideoProfileResolver",
    "FFmpegFrameInspector", "FrameGeometry", "HudAnchorAligner", "HudProfileRegistry",
    "ProfileResolution", "RoiCorrection",
]
