"""TASK-049 R10B reusable DbD ROI/slice-image recognition primitives.

The first production baseline intentionally avoids a heavyweight ML runtime.
It provides deterministic ROI extraction, grayscale perceptual fingerprints,
reference-index training, top-k matching, and temporal consensus.  A future
CNN/embedding recognizer can implement the same ports without changing CGEL.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


@dataclass(frozen=True, slots=True)
class NormalizedROI:
    roi_id: str
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if not self.roi_id or len(self.roi_id) > 128:
            raise ValueError("roi_id must be bounded non-empty text")
        for name in ("x", "y", "width", "height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
        if not (0 <= self.x < 1 and 0 <= self.y < 1):
            raise ValueError("ROI origin must be normalized into 0..1")
        if not (0 < self.width <= 1 and 0 < self.height <= 1):
            raise ValueError("ROI size must be normalized into 0..1")
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("ROI must stay inside frame bounds")

    def to_dict(self) -> dict[str, object]:
        return {"roi_id": self.roi_id, "x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class HudAnchorReference:
    """Portable visual anchor used for HUD-profile resolution/alignment."""

    roi_id: str
    feature_hex: str
    source_sha256: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.roi_id or len(self.roi_id) > 128:
            raise ValueError("anchor roi_id must be bounded non-empty text")
        if len(self.feature_hex) != 16:
            raise ValueError("anchor feature_hex must encode a 64-bit dHash")
        int(self.feature_hex, 16)
        if not self.source_sha256.startswith("sha256:") or len(self.source_sha256) != 71:
            raise ValueError("anchor source_sha256 must use canonical sha256:<hex>")
        if not self.source_ref or len(self.source_ref) > 1024:
            raise ValueError("anchor source_ref must be bounded non-empty text")

    @property
    def feature(self) -> int:
        return int(self.feature_hex, 16)

    def to_dict(self) -> dict[str, str]:
        return {
            "roi_id": self.roi_id,
            "feature_hex": self.feature_hex,
            "source_sha256": self.source_sha256,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True, slots=True)
class DBDHudRoiProfile:
    """Versioned, calibratable HUD geometry contract.

    Pixel positions are never canonical.  ROIs are normalized to the source
    frame and calibration metadata records the frame/UI/game conditions that
    produced them.  Optional dHash anchors support profile inference and small
    drift correction without embedding image binaries in the JSON contract.

    The broad ``dbd-16x9-discovery-v1`` defaults remain for backward
    compatibility and discovery/testing only.  Production recognition should
    use a saved calibrated profile and fail closed when it cannot be resolved.
    """

    profile_id: str = "dbd-16x9-discovery-v1"
    profile_version: int = 1
    calibrated_frame_width: int | None = None
    calibrated_frame_height: int | None = None
    ui_scale_percent: int | None = None
    game_version_from: str | None = None
    game_version_to: str | None = None
    calibration_source_ref: str | None = None
    anchors: tuple[HudAnchorReference, ...] = ()
    lower_left_survivor_hud: NormalizedROI = field(default_factory=lambda: NormalizedROI("lower_left_survivor_hud", 0.0, 0.60, 0.30, 0.40))
    upper_right_notifications: NormalizedROI = field(default_factory=lambda: NormalizedROI("upper_right_notifications", 0.55, 0.0, 0.45, 0.38))
    bottom_right_perks: NormalizedROI = field(default_factory=lambda: NormalizedROI("bottom_right_perks", 0.72, 0.64, 0.28, 0.36))
    lower_left_loadout_hud: NormalizedROI | None = None
    item_slot: NormalizedROI | None = None
    addon_slots: tuple[NormalizedROI, ...] = ()
    survivor_slots: tuple[NormalizedROI, ...] = field(default_factory=lambda: (
        NormalizedROI("survivor_slot_0", 0.010, 0.625, 0.120, 0.080),
        NormalizedROI("survivor_slot_1", 0.010, 0.715, 0.120, 0.080),
        NormalizedROI("survivor_slot_2", 0.010, 0.805, 0.120, 0.080),
        NormalizedROI("survivor_slot_3", 0.010, 0.895, 0.120, 0.080),
    ))
    perk_slots: tuple[NormalizedROI, ...] = field(default_factory=lambda: (
        NormalizedROI("perk_slot_0", 0.820, 0.735, 0.075, 0.095),
        NormalizedROI("perk_slot_1", 0.900, 0.735, 0.075, 0.095),
        NormalizedROI("perk_slot_2", 0.820, 0.840, 0.075, 0.095),
        NormalizedROI("perk_slot_3", 0.900, 0.840, 0.075, 0.095),
    ))
    killer_power_hud: NormalizedROI | None = None
    heartbeat_hud: NormalizedROI | None = None

    def __post_init__(self) -> None:
        if not self.profile_id or len(self.profile_id) > 128:
            raise ValueError("profile_id must be bounded non-empty text")
        if self.profile_version < 1:
            raise ValueError("profile_version must be positive")
        if (self.calibrated_frame_width is None) != (self.calibrated_frame_height is None):
            raise ValueError("calibrated frame width/height must be provided together")
        if self.calibrated_frame_width is not None and (self.calibrated_frame_width < 64 or self.calibrated_frame_height < 64):
            raise ValueError("calibrated frame dimensions are invalid")
        if self.ui_scale_percent is not None and not 25 <= self.ui_scale_percent <= 200:
            raise ValueError("ui_scale_percent must be 25..200 when supplied")
        if len(self.survivor_slots) != 4 or len(self.perk_slots) != 4:
            raise ValueError("DbD HUD profile requires exactly four survivor and four perk slot ROIs")
        if len(self.addon_slots) not in {0, 2}:
            raise ValueError("addon_slots must be empty or contain exactly two add-on ROIs")
        slot_rows = self.survivor_slots + self.perk_slots + self.addon_slots
        if self.item_slot is not None:
            slot_rows += (self.item_slot,)
        slot_ids = [item.roi_id for item in slot_rows]
        if len(set(slot_ids)) != len(slot_ids):
            raise ValueError("slot ROI identifiers must be unique")
        anchor_ids = [item.roi_id for item in self.anchors]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("anchor ROI identifiers must be unique")

    @property
    def aspect_ratio(self) -> float | None:
        if self.calibrated_frame_width is None or self.calibrated_frame_height is None:
            return None
        return self.calibrated_frame_width / self.calibrated_frame_height

    def anchor_for(self, roi_id: str) -> HudAnchorReference | None:
        return next((item for item in self.anchors if item.roi_id == roi_id), None)

    @classmethod
    def from_dict(cls, payload: object) -> "DBDHudRoiProfile":
        if not isinstance(payload, dict):
            raise ValueError("ROI profile must be an object")
        schema_version = str(payload.get("schema_version", "1.1.0"))
        if schema_version not in {"1.1.0", "2.0.0", "2.1.0", "2.2.0"}:
            raise ValueError("unsupported HUD ROI profile schema")
        def roi(name: str, value: object) -> NormalizedROI:
            if not isinstance(value, dict):
                raise ValueError(f"{name} must be an ROI object")
            return NormalizedROI(
                str(value.get("roi_id", name)),
                float(value["x"]), float(value["y"]), float(value["width"]), float(value["height"]),
            )
        defaults = cls()
        survivor_values = payload.get("survivor_slots")
        perk_values = payload.get("perk_slots")
        raw_anchors = payload.get("anchors", [])
        anchors = tuple(HudAnchorReference(**item) for item in raw_anchors) if isinstance(raw_anchors, list) else ()
        return cls(
            profile_id=str(payload.get("profile_id", defaults.profile_id)),
            profile_version=int(payload.get("profile_version", 1)),
            calibrated_frame_width=None if payload.get("calibrated_frame_width") is None else int(payload["calibrated_frame_width"]),
            calibrated_frame_height=None if payload.get("calibrated_frame_height") is None else int(payload["calibrated_frame_height"]),
            ui_scale_percent=None if payload.get("ui_scale_percent") is None else int(payload["ui_scale_percent"]),
            game_version_from=None if payload.get("game_version_from") is None else str(payload["game_version_from"]),
            game_version_to=None if payload.get("game_version_to") is None else str(payload["game_version_to"]),
            calibration_source_ref=None if payload.get("calibration_source_ref") is None else str(payload["calibration_source_ref"]),
            anchors=anchors,
            lower_left_survivor_hud=roi("lower_left_survivor_hud", payload.get("lower_left_survivor_hud", defaults.lower_left_survivor_hud.to_dict())),
            upper_right_notifications=roi("upper_right_notifications", payload.get("upper_right_notifications", defaults.upper_right_notifications.to_dict())),
            bottom_right_perks=roi("bottom_right_perks", payload.get("bottom_right_perks", defaults.bottom_right_perks.to_dict())),
            lower_left_loadout_hud=None if payload.get("lower_left_loadout_hud") is None else roi("lower_left_loadout_hud", payload["lower_left_loadout_hud"]),
            item_slot=None if payload.get("item_slot") is None else roi("item_slot", payload["item_slot"]),
            addon_slots=tuple(roi(f"addon_slot_{index}", value) for index, value in enumerate(payload.get("addon_slots", []))) if isinstance(payload.get("addon_slots", []), list) else (),
            survivor_slots=tuple(roi(f"survivor_slot_{index}", value) for index, value in enumerate(survivor_values)) if isinstance(survivor_values, list) else defaults.survivor_slots,
            perk_slots=tuple(roi(f"perk_slot_{index}", value) for index, value in enumerate(perk_values)) if isinstance(perk_values, list) else defaults.perk_slots,
            killer_power_hud=None if payload.get("killer_power_hud") is None else roi("killer_power_hud", payload["killer_power_hud"]),
            heartbeat_hud=None if payload.get("heartbeat_hud") is None else roi("heartbeat_hud", payload["heartbeat_hud"]),
        )

    def survivor_slot_roi(self, slot: int) -> NormalizedROI:
        if not 0 <= slot < 4:
            raise ValueError("survivor slot must be 0..3")
        return self.survivor_slots[slot]

    def perk_slot_roi(self, slot: int) -> NormalizedROI:
        if not 0 <= slot < 4:
            raise ValueError("perk slot must be 0..3")
        return self.perk_slots[slot]

    def item_slot_roi(self) -> NormalizedROI:
        if self.item_slot is None:
            raise ValueError("item_slot is not calibrated for this HUD profile")
        return self.item_slot

    def addon_slot_roi(self, slot: int) -> NormalizedROI:
        if not 0 <= slot < 2:
            raise ValueError("add-on slot must be 0..1")
        if len(self.addon_slots) != 2:
            raise ValueError("add-on slots are not calibrated for this HUD profile")
        return self.addon_slots[slot]

    def roi_by_id(self, roi_id: str) -> NormalizedROI:
        direct = {
            self.lower_left_survivor_hud.roi_id: self.lower_left_survivor_hud,
            self.upper_right_notifications.roi_id: self.upper_right_notifications,
            self.bottom_right_perks.roi_id: self.bottom_right_perks,
        }
        if self.lower_left_loadout_hud is not None:
            direct[self.lower_left_loadout_hud.roi_id] = self.lower_left_loadout_hud
        if self.item_slot is not None:
            direct[self.item_slot.roi_id] = self.item_slot
        if self.killer_power_hud is not None:
            direct[self.killer_power_hud.roi_id] = self.killer_power_hud
        if self.heartbeat_hud is not None:
            direct[self.heartbeat_hud.roi_id] = self.heartbeat_hud
        direct.update({item.roi_id: item for item in self.survivor_slots + self.perk_slots + self.addon_slots})
        if roi_id not in direct:
            raise KeyError(roi_id)
        return direct[roi_id]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "2.2.0",
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "calibrated_frame_width": self.calibrated_frame_width,
            "calibrated_frame_height": self.calibrated_frame_height,
            "ui_scale_percent": self.ui_scale_percent,
            "game_version_from": self.game_version_from,
            "game_version_to": self.game_version_to,
            "calibration_source_ref": self.calibration_source_ref,
            "anchors": [item.to_dict() for item in self.anchors],
            "lower_left_survivor_hud": self.lower_left_survivor_hud.to_dict(),
            "upper_right_notifications": self.upper_right_notifications.to_dict(),
            "bottom_right_perks": self.bottom_right_perks.to_dict(),
            "lower_left_loadout_hud": None if self.lower_left_loadout_hud is None else self.lower_left_loadout_hud.to_dict(),
            "item_slot": None if self.item_slot is None else self.item_slot.to_dict(),
            "addon_slots": [item.to_dict() for item in self.addon_slots],
            "survivor_slots": [item.to_dict() for item in self.survivor_slots],
            "perk_slots": [item.to_dict() for item in self.perk_slots],
            "killer_power_hud": None if self.killer_power_hud is None else self.killer_power_hud.to_dict(),
            "heartbeat_hud": None if self.heartbeat_hud is None else self.heartbeat_hud.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GrayImage:
    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1 or len(self.pixels) != self.width * self.height:
            raise ValueError("invalid grayscale image dimensions/pixels")

    @classmethod
    def read_pgm(cls, path: str | Path) -> "GrayImage":
        raw = Path(path).read_bytes()
        if not raw.startswith(b"P5"):
            raise ValueError("only binary PGM (P5) slices are supported")
        index = 2
        tokens: list[bytes] = []
        while len(tokens) < 3:
            while index < len(raw) and raw[index] in b" \t\r\n":
                index += 1
            if index < len(raw) and raw[index] == 35:  # '#'
                while index < len(raw) and raw[index] not in b"\r\n":
                    index += 1
                continue
            start = index
            while index < len(raw) and raw[index] not in b" \t\r\n":
                index += 1
            tokens.append(raw[start:index])
        width, height, maximum = (int(value) for value in tokens)
        if maximum != 255:
            raise ValueError("PGM max value must be 255")
        while index < len(raw) and raw[index] in b" \t\r\n":
            index += 1
        pixels = raw[index:]
        return cls(width, height, pixels)

    def write_pgm(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"P5\n{self.width} {self.height}\n255\n".encode("ascii") + self.pixels)
        return target

    def crop_normalized(self, roi: NormalizedROI) -> "GrayImage":
        left = max(0, min(self.width - 1, round(roi.x * self.width)))
        top = max(0, min(self.height - 1, round(roi.y * self.height)))
        right = max(left + 1, min(self.width, round((roi.x + roi.width) * self.width)))
        bottom = max(top + 1, min(self.height, round((roi.y + roi.height) * self.height)))
        width, height = right - left, bottom - top
        out = bytearray(width * height)
        for y in range(height):
            source = (top + y) * self.width + left
            out[y * width:(y + 1) * width] = self.pixels[source:source + width]
        return GrayImage(width, height, bytes(out))

    def resized(self, width: int, height: int) -> "GrayImage":
        if width < 1 or height < 1:
            raise ValueError("resize dimensions must be positive")
        target = bytearray(width * height)
        for y in range(height):
            src_y = min(self.height - 1, int((y + 0.5) * self.height / height))
            for x in range(width):
                src_x = min(self.width - 1, int((x + 0.5) * self.width / width))
                target[y * width + x] = self.pixels[src_y * self.width + src_x]
        return GrayImage(width, height, bytes(target))

    def dhash64(self) -> int:
        small = self.resized(9, 8)
        value = 0
        bit = 0
        for y in range(8):
            row = y * 9
            for x in range(8):
                if small.pixels[row + x] > small.pixels[row + x + 1]:
                    value |= 1 << bit
                bit += 1
        return value


@dataclass(frozen=True, slots=True)
class SliceReference:
    label: str
    feature_hex: str
    source_sha256: str
    source_ref: str
    group: str = "default"
    match_id: str = ""
    survivor_slot: int | None = None
    signal_kind: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip() or len(self.label) > 256:
            raise ValueError("label must be bounded non-empty text")
        if len(self.feature_hex) != 16:
            raise ValueError("feature_hex must encode a 64-bit dHash")
        int(self.feature_hex, 16)
        if not self.source_sha256.startswith("sha256:") or len(self.source_sha256) != 71:
            raise ValueError("source_sha256 must use canonical sha256:<hex>")
        if not self.source_ref or len(self.source_ref) > 1024:
            raise ValueError("source_ref must be bounded non-empty text")
        has_subject = bool(self.match_id or self.survivor_slot is not None or self.signal_kind)
        if has_subject:
            if not self.match_id.strip() or len(self.match_id) > 256:
                raise ValueError("subject reference requires bounded match_id")
            if self.survivor_slot is None or not 0 <= self.survivor_slot <= 3:
                raise ValueError("subject reference requires survivor_slot 0..3")
            if self.signal_kind not in {"HOOK_COUNT", "CHASE_STATE", "SURVIVOR_STATE"}:
                raise ValueError("subject reference requires supported signal_kind")

    @property
    def feature(self) -> int:
        return int(self.feature_hex, 16)

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label, "feature_hex": self.feature_hex,
            "source_sha256": self.source_sha256, "source_ref": self.source_ref,
            "group": self.group, "match_id": self.match_id,
            "survivor_slot": self.survivor_slot, "signal_kind": self.signal_kind,
        }


@dataclass(frozen=True, slots=True)
class SliceMatch:
    label: str
    confidence_milli: int
    distance_bits: int
    source_ref: str
    match_id: str = ""
    survivor_slot: int | None = None
    signal_kind: str = ""


class ReferenceSliceIndex:
    schema_version = "1.1.0"

    def __init__(self, *, index_id: str, references: Sequence[SliceReference], created_at: str | None = None) -> None:
        if not index_id or len(index_id) > 128:
            raise ValueError("index_id must be bounded non-empty text")
        if not references:
            raise ValueError("reference index requires at least one reference")
        self.index_id = index_id
        self.references = tuple(references)
        self.created_at = created_at or utc_now_iso()

    @classmethod
    def train_from_pgm(
        cls,
        *,
        index_id: str,
        samples: Iterable[
            tuple[str, str | Path]
            | tuple[str, str | Path, str]
            | tuple[str, str | Path, str, str, int | None, str]
        ],
        group: str = "default",
    ) -> "ReferenceSliceIndex":
        """Build the deterministic reference baseline from labeled PGM slices.

        A sample may be ``(label, path)`` or ``(label, path, group)``.  The
        optional group records visual-state provenance such as ``normal``,
        ``active``, ``greyed`` or ``hard-negative`` without changing the
        classifier's canonical label.
        """
        refs: list[SliceReference] = []
        for sample in samples:
            if len(sample) == 2:
                label, path_value = sample
                sample_group = group
                match_id, survivor_slot, signal_kind = "", None, ""
            elif len(sample) == 3:
                label, path_value, sample_group = sample
                match_id, survivor_slot, signal_kind = "", None, ""
            elif len(sample) == 6:
                label, path_value, sample_group, match_id, survivor_slot, signal_kind = sample
            else:
                raise ValueError("reference sample must contain 2, 3 or 6 fields")
            if not str(sample_group).strip() or len(str(sample_group)) > 128:
                raise ValueError("reference sample group must be bounded non-empty text")
            path = Path(path_value)
            raw = path.read_bytes()
            image = GrayImage.read_pgm(path)
            refs.append(SliceReference(
                label, f"{image.dhash64():016x}", sha256_bytes(raw), str(path),
                str(sample_group).strip(), str(match_id).strip(), survivor_slot,
                str(signal_kind).strip().upper(),
            ))
        if not refs:
            raise ValueError("samples must not be empty")
        return cls(index_id=index_id, references=refs)

    def match(self, image: GrayImage, *, top_k: int = 3) -> tuple[SliceMatch, ...]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        feature = image.dhash64()
        rows: list[SliceMatch] = []
        for ref in self.references:
            distance = (feature ^ ref.feature).bit_count()
            confidence = max(0, 1000 - round(distance * 1000 / 64))
            rows.append(SliceMatch(
                ref.label, confidence, distance, ref.source_ref,
                ref.match_id, ref.survivor_slot, ref.signal_kind,
            ))
        rows.sort(key=lambda item: (-item.confidence_milli, item.distance_bits, item.label, item.source_ref))
        return tuple(rows[:top_k])

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": self.schema_version,
            "index_id": self.index_id,
            "created_at": self.created_at,
            "references": [item.to_dict() for item in sorted(
                self.references,
                key=lambda x: (
                    x.label, x.group, x.match_id,
                    -1 if x.survivor_slot is None else x.survivor_slot,
                    x.signal_kind, x.source_ref,
                ),
            )],
        }
        return {**body, "index_sha256": sha256_bytes(canonical_json_bytes(body))}

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "ReferenceSliceIndex":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        body = dict(document)
        digest = body.pop("index_sha256", None)
        if digest != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("reference index checksum mismatch")
        if body.get("schema_version") not in {"1.0.0", cls.schema_version}:
            raise ValueError("unsupported reference index schema")
        refs = tuple(SliceReference(**item) for item in body["references"])
        return cls(index_id=body["index_id"], references=refs, created_at=body["created_at"])


class FFmpegSliceExtractor:
    def __init__(self, ffmpeg_executable: str = "ffmpeg") -> None:
        self.ffmpeg_executable = ffmpeg_executable

    def extract_frame_roi(self, *, video_path: str | Path, frame_index: int, roi: NormalizedROI,
                          output_path: str | Path, width: int = 64, height: int = 64) -> Path:
        if frame_index < 0 or width < 8 or height < 8:
            raise ValueError("frame_index/dimensions are invalid")
        source = Path(video_path)
        if not source.is_file():
            raise ProductError("ERR_DBD_SLICE_SOURCE_MISSING", "DbD slice source video is missing", ProductErrorCategory.VALIDATION)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        crop = f"crop=iw*{roi.width}:ih*{roi.height}:iw*{roi.x}:ih*{roi.y}"
        vf = f"select=eq(n\\,{frame_index}),{crop},scale={width}:{height}:flags=area,format=gray"
        cmd = [self.ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", vf, "-frames:v", "1", "-f", "image2", "-vcodec", "pgm", "-y", str(target)]
        try:
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductError("ERR_DBD_SLICE_FFMPEG_UNAVAILABLE", "FFmpeg ROI extraction failed to start", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True) from exc
        if completed.returncode != 0 or not target.is_file():
            raise ProductError("ERR_DBD_SLICE_FFMPEG_FAILED", "FFmpeg failed to extract the requested DbD ROI", ProductErrorCategory.EXTERNAL_DEPENDENCY, retryable=True, details={"returncode": completed.returncode})
        return target

    def normalize_still_to_pgm(self, *, image_path: str | Path, output_path: str | Path, width: int = 64, height: int = 64) -> Path:
        source, target = Path(image_path), Path(output_path)
        if not source.is_file():
            raise ValueError("reference image does not exist")
        target.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", f"scale={width}:{height}:flags=area,format=gray", "-frames:v", "1", "-f", "image2", "-vcodec", "pgm", "-y", str(target)]
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
        if completed.returncode != 0 or not target.is_file():
            raise ProductError("ERR_DBD_REFERENCE_NORMALIZE_FAILED", "FFmpeg failed to normalize a reference slice", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        return target


class TemporalConsensus:
    @staticmethod
    def vote(labels: Sequence[tuple[str, int]], *, minimum_frames: int = 2, minimum_confidence_milli: int = 650) -> tuple[str, int] | None:
        admitted = [(label, confidence) for label, confidence in labels if confidence >= minimum_confidence_milli]
        if len(admitted) < minimum_frames:
            return None
        buckets: dict[str, list[int]] = {}
        for label, confidence in admitted:
            buckets.setdefault(label, []).append(confidence)
        label, values = max(buckets.items(), key=lambda item: (len(item[1]), sum(item[1]), item[0]))
        if len(values) < minimum_frames:
            return None
        return label, round(sum(values) / len(values))


__all__ = [
    "DBDHudRoiProfile", "FFmpegSliceExtractor", "GrayImage", "HudAnchorReference", "NormalizedROI",
    "ReferenceSliceIndex", "SliceMatch", "SliceReference", "TemporalConsensus",
]
