"""TASK-025 deterministic Premiere-compatible FCP7 XML adapter.

The adapter renders in-memory TASK-022 TimelineMappingPlan values.  It never
opens media, writes a file, launches Premiere, imports a sequence, or mutates a
Timeline.  Media URIs are private inputs; public receipts contain their digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate, FrameRounding
from .timeline_mapping import TimelineMappingPlan


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")
_PLACEMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FILE_URI_RE = re.compile(r"^file://localhost/[A-Za-z0-9%._~!$&'()+,;=:@/-]{1,1024}$")
_MAX_BINDINGS = 10_000
_MAX_PLACEMENTS = 100_000
_MAX_FRAMES = (1 << 53) - 1


def _sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _positive_int(value: int, field_name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in 1..{maximum}")
    return value


def _rate_fields(rate: FrameRate) -> tuple[int, bool]:
    mapping = {
        (24, 1): (24, False),
        (24000, 1001): (24, True),
        (25, 1): (25, False),
        (30, 1): (30, False),
        (30000, 1001): (30, True),
        (50, 1): (50, False),
        (60, 1): (60, False),
        (60000, 1001): (60, True),
    }
    try:
        return mapping[(rate.numerator, rate.denominator)]
    except KeyError as exc:
        raise ValueError("frame rate is not in the closed FCP7 compatibility matrix") from exc


def _validate_media_uri(value: str) -> str:
    if not isinstance(value, str) or not _FILE_URI_RE.fullmatch(value):
        raise ValueError("media_uri must be a contained file://localhost URI")
    suffix = value.removeprefix("file://localhost/")
    if "\\" in value or "?" in value or "#" in value:
        raise ValueError("media_uri cannot contain backslash, query, or fragment")
    if any(segment in {"", ".", ".."} for segment in suffix.split("/")):
        raise ValueError("media_uri cannot contain empty, current, or parent path segments")
    if "%2e" in suffix.casefold() or "%5c" in suffix.casefold() or "%2f" in suffix.casefold():
        raise ValueError("media_uri cannot hide separators or parent segments with percent encoding")
    return value


@dataclass(frozen=True, slots=True)
class FCP7SequenceProfile:
    sequence_name: str
    width: int
    height: int
    frame_rate: FrameRate
    pixel_aspect_ratio: str = "square"

    def __post_init__(self) -> None:
        if not isinstance(self.sequence_name, str) or not _NAME_RE.fullmatch(self.sequence_name):
            raise ValueError("sequence_name is invalid")
        _positive_int(self.width, "width", 16_384)
        _positive_int(self.height, "height", 16_384)
        if not isinstance(self.frame_rate, FrameRate):
            raise ValueError("frame_rate must be the canonical FrameRate type")
        _rate_fields(self.frame_rate)
        if self.pixel_aspect_ratio not in {"square", "PAL-CCIR-601", "NTSC-CCIR-601"}:
            raise ValueError("pixel_aspect_ratio is not supported")

    def to_dict(self) -> dict[str, Any]:
        timebase, ntsc = _rate_fields(self.frame_rate)
        return {
            "sequence_name": self.sequence_name,
            "width": self.width,
            "height": self.height,
            "frame_rate": {
                "numerator": self.frame_rate.numerator,
                "denominator": self.frame_rate.denominator,
                "fcp_timebase": timebase,
                "ntsc": ntsc,
            },
            "pixel_aspect_ratio": self.pixel_aspect_ratio,
        }


@dataclass(frozen=True, slots=True)
class FCP7MediaBinding:
    asset_id: str
    asset_sha256: str
    logical_name: str
    media_uri: str
    frame_rate: FrameRate
    duration_frames: int

    def __post_init__(self) -> None:
        validate_id(self.asset_id, IdKind.ASSET)
        _sha256(self.asset_sha256, "asset_sha256")
        if not isinstance(self.logical_name, str) or not _NAME_RE.fullmatch(self.logical_name):
            raise ValueError("logical_name is invalid")
        _validate_media_uri(self.media_uri)
        if not isinstance(self.frame_rate, FrameRate):
            raise ValueError("frame_rate must be the canonical FrameRate type")
        _rate_fields(self.frame_rate)
        _positive_int(self.duration_frames, "duration_frames", _MAX_FRAMES)

    def public_receipt(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_sha256": self.asset_sha256,
            "logical_name": self.logical_name,
            "media_uri_sha256": sha256_bytes(self.media_uri.encode("utf-8")),
            "frame_rate": {
                "numerator": self.frame_rate.numerator,
                "denominator": self.frame_rate.denominator,
            },
            "duration_frames": self.duration_frames,
            "media_uri_public": False,
        }


@dataclass(frozen=True, slots=True)
class PremiereFCP7XMLPackage:
    profile: FCP7SequenceProfile
    timeline_plan: TimelineMappingPlan
    media_bindings: tuple[FCP7MediaBinding, ...]
    xml_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.profile, FCP7SequenceProfile):
            raise ValueError("profile must be an FCP7SequenceProfile")
        if not isinstance(self.timeline_plan, TimelineMappingPlan):
            raise ValueError("timeline_plan must be a TimelineMappingPlan")
        if any(not isinstance(item, FCP7MediaBinding) for item in self.media_bindings):
            raise ValueError("media_bindings must contain FCP7MediaBinding values")
        if self.media_bindings != tuple(sorted(self.media_bindings, key=lambda item: item.asset_id)):
            raise ValueError("media_bindings must be canonically sorted")
        expected = _render_xml(self.profile, self.timeline_plan, self.media_bindings)
        if self.xml_bytes != expected:
            raise ValueError("xml_bytes do not match the canonical FCP7 rendering")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "package_version": "1.0.0",
            "task_owner": "TASK-025",
            "format": "FCP7_XMEML_V5",
            "sequence_profile": self.profile.to_dict(),
            "timeline_plan_sha256": self.timeline_plan.to_dict()["plan_sha256"],
            "media_binding_receipts": [item.public_receipt() for item in self.media_bindings],
            "xml_byte_length": len(self.xml_bytes),
            "xml_sha256": sha256_bytes(self.xml_bytes),
            "media_uri_values_private": True,
            "media_read_performed": False,
            "filesystem_write_performed": False,
            "premiere_import_performed": False,
            "external_mutation_authorized": False,
            "human_import_review_required": True,
        }
        body["package_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_premiere_fcp7_xml(
    profile: FCP7SequenceProfile,
    timeline_plan: TimelineMappingPlan,
    media_bindings: Iterable[FCP7MediaBinding],
) -> PremiereFCP7XMLPackage:
    """Render an in-memory, deterministic xmeml v5 package with no external effect."""

    if not isinstance(profile, FCP7SequenceProfile):
        raise ValueError("profile must be an FCP7SequenceProfile")
    if not isinstance(timeline_plan, TimelineMappingPlan):
        raise ValueError("timeline_plan must be a TimelineMappingPlan")
    rows = tuple(media_bindings)
    if not 1 <= len(rows) <= _MAX_BINDINGS:
        raise ValueError("media_bindings must contain 1-10000 rows")
    if any(not isinstance(item, FCP7MediaBinding) for item in rows):
        raise ValueError("media_bindings must contain FCP7MediaBinding values")
    canonical_rows = tuple(sorted(rows, key=lambda item: item.asset_id))
    xml_bytes = _render_xml(profile, timeline_plan, canonical_rows)
    return PremiereFCP7XMLPackage(profile, timeline_plan, canonical_rows, xml_bytes)


def _render_xml(
    profile: FCP7SequenceProfile,
    plan: TimelineMappingPlan,
    bindings: tuple[FCP7MediaBinding, ...],
) -> bytes:
    if plan.timeline_origin_frame != 0:
        raise ValueError("R0 FCP7 export requires timeline_origin_frame=0")
    if not 1 <= len(plan.placements) <= _MAX_PLACEMENTS:
        raise ValueError("timeline placements must contain 1-100000 rows")
    if plan.timeline_rate != profile.frame_rate:
        raise ValueError("Timeline and FCP7 sequence frame rates must match exactly")
    binding_by_asset: dict[str, FCP7MediaBinding] = {}
    for binding in bindings:
        if binding.asset_id in binding_by_asset:
            raise ValueError("media binding asset IDs must be unique")
        if binding.frame_rate != plan.timeline_rate:
            raise ValueError("media and Timeline frame rates must match exactly in R0")
        binding_by_asset[binding.asset_id] = binding
    expected_assets = {item.mapped_asset_id for item in plan.placements}
    if set(binding_by_asset) != expected_assets:
        raise ValueError("media binding asset set must exactly equal mapped Timeline assets")

    root = ET.Element("xmeml", {"version": "5"})
    sequence = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    _text(sequence, "name", profile.sequence_name)
    _text(sequence, "duration", str(plan.duration_frames))
    _append_rate(sequence, profile.frame_rate)
    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    characteristics = ET.SubElement(fmt, "samplecharacteristics")
    _append_rate(characteristics, profile.frame_rate)
    _text(characteristics, "width", str(profile.width))
    _text(characteristics, "height", str(profile.height))
    _text(characteristics, "anamorphic", "FALSE")
    _text(characteristics, "pixelaspectratio", profile.pixel_aspect_ratio)
    _text(characteristics, "fielddominance", "none")
    track = ET.SubElement(video, "track")

    seen_placements: set[str] = set()
    for ordinal, placement in enumerate(plan.placements, start=1):
        if not _PLACEMENT_RE.fullmatch(placement.placement_id):
            raise ValueError("placement_id is not safe for FCP7 XML identity")
        if placement.placement_id in seen_placements:
            raise ValueError("placement IDs must be unique")
        seen_placements.add(placement.placement_id)
        if (placement.playback_rate_numerator, placement.playback_rate_denominator) != (1, 1):
            raise ValueError("R0 FCP7 export does not admit retimed placements")
        binding = binding_by_asset[placement.mapped_asset_id]
        source_in = binding.frame_rate.us_to_frame(
            placement.mapped_start_us, rounding=FrameRounding.FLOOR
        )
        source_out = binding.frame_rate.us_to_frame(
            placement.mapped_end_us, rounding=FrameRounding.CEIL
        )
        if not 0 <= source_in < source_out <= binding.duration_frames:
            raise ValueError("mapped source range is outside bound media duration")
        if placement.timeline_end_frame - placement.timeline_start_frame != source_out - source_in:
            raise ValueError("R0 FCP7 placement duration must match the exact source frame range")

        clip = ET.SubElement(track, "clipitem", {"id": f"clipitem-{ordinal:06d}"})
        _text(clip, "name", binding.logical_name)
        _text(clip, "duration", str(binding.duration_frames))
        _append_rate(clip, binding.frame_rate)
        _text(clip, "start", str(placement.timeline_start_frame))
        _text(clip, "end", str(placement.timeline_end_frame))
        _text(clip, "in", str(source_in))
        _text(clip, "out", str(source_out))
        file_node = ET.SubElement(clip, "file", {"id": f"file-{ordinal:06d}"})
        _text(file_node, "name", binding.logical_name)
        _text(file_node, "pathurl", binding.media_uri)
        _append_rate(file_node, binding.frame_rate)
        _text(file_node, "duration", str(binding.duration_frames))

    _text(track, "enabled", "TRUE")
    _text(track, "locked", "FALSE")
    body = ET.tostring(root, encoding="utf-8", xml_declaration=False, short_empty_elements=True)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + body + b"\n"


def _text(parent: ET.Element, tag: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = value
    return child


def _append_rate(parent: ET.Element, rate: FrameRate) -> ET.Element:
    timebase, ntsc = _rate_fields(rate)
    node = ET.SubElement(parent, "rate")
    _text(node, "timebase", str(timebase))
    _text(node, "ntsc", "TRUE" if ntsc else "FALSE")
    return node


def verify_premiere_fcp7_package_hash(payload: dict[str, Any]) -> None:
    """Verify the public no-self package digest."""

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    body = dict(payload)
    claimed = body.pop("package_sha256", None)
    _sha256(claimed, "package_sha256")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("package_sha256 does not match the canonical package body")
