"""Content-sniffed image inspection and non-destructive preview transforms."""
from __future__ import annotations

from dataclasses import dataclass, replace
from io import BytesIO
import hashlib
import os
from pathlib import Path
import re
import struct
import tempfile
from typing import Any
import xml.etree.ElementTree as ET


_MAX_IMAGE_BYTES = 16 * 1024 * 1024
_MAX_DIMENSION = 16384
_MAX_PIXELS = 64 * 1024 * 1024
_MIME = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "GIF": "image/gif",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
    "SVG": "image/svg+xml",
    "UNKNOWN": "application/octet-stream",
}
_EXTENSION = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "GIF": ".gif",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tiff",
    "SVG": ".svg",
    "UNKNOWN": ".img",
}


@dataclass(frozen=True, slots=True)
class ImageAssetReport:
    detected_format: str
    mime_type: str
    byte_length: int
    source_sha256: str
    width: int | None = None
    height: int | None = None
    decode_path: str = "CONTENT_SNIFF"
    diagnostic_code: str = "OK"
    diagnostic_reason: str = ""


class ImageAssetDecodeError(ValueError):
    def __init__(self, report: ImageAssetReport) -> None:
        self.report = report
        super().__init__(f"{report.diagnostic_code}: {report.diagnostic_reason}")


def validate_rotation(rotation_deg: int) -> int:
    value = int(rotation_deg)
    if value not in {0, 90, 180, 270}:
        raise ValueError("rotation_deg must be 0/90/180/270")
    return value


def _svg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if re.search(br"<!\s*(?:doctype|entity)\b", data, flags=re.IGNORECASE):
        raise ValueError("SVG_DTD_OR_ENTITY_NOT_ALLOWED")
    root = ET.fromstring(data)
    if root.tag.rsplit("}", 1)[-1].casefold() != "svg":
        raise ValueError("SVG_ROOT_MISSING")

    def safe_reference(value: str) -> bool:
        reference = value.strip().strip("'\"")
        return not reference or reference.startswith("#") or reference.casefold().startswith("data:image/")

    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].casefold() in {"script", "foreignobject"}:
            raise ValueError("SVG_ACTIVE_CONTENT_NOT_ALLOWED")
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].casefold()
            if local_name.startswith("on"):
                raise ValueError("SVG_EVENT_HANDLER_NOT_ALLOWED")
            if local_name == "href" and not safe_reference(value):
                raise ValueError("SVG_EXTERNAL_REFERENCE_NOT_ALLOWED")
            for match in re.finditer(r"url\(\s*([^)]*?)\s*\)", value, flags=re.IGNORECASE):
                if not safe_reference(match.group(1)):
                    raise ValueError("SVG_EXTERNAL_REFERENCE_NOT_ALLOWED")
        if element.tag.rsplit("}", 1)[-1].casefold() == "style" and element.text:
            if re.search(r"@import\b", element.text, flags=re.IGNORECASE):
                raise ValueError("SVG_EXTERNAL_REFERENCE_NOT_ALLOWED")
            for match in re.finditer(r"url\(\s*([^)]*?)\s*\)", element.text, flags=re.IGNORECASE):
                if not safe_reference(match.group(1)):
                    raise ValueError("SVG_EXTERNAL_REFERENCE_NOT_ALLOWED")

    def numeric(value: str | None) -> int | None:
        if not value:
            return None
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*", value)
        return None if match is None else max(1, int(round(float(match.group(1)))))

    width, height = numeric(root.get("width")), numeric(root.get("height"))
    if width is not None and height is not None:
        return width, height
    view_box = re.split(r"[\s,]+", (root.get("viewBox") or "").strip())
    if len(view_box) == 4:
        try:
            return max(1, int(round(float(view_box[2])))), max(1, int(round(float(view_box[3]))))
        except ValueError:
            pass
    return width, height


def _jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        length = int.from_bytes(data[index:index + 2], "big")
        if length < 2 or index + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            return int.from_bytes(data[index + 5:index + 7], "big"), int.from_bytes(data[index + 3:index + 5], "big")
        index += length
    return None, None


def inspect_image_bytes(data: bytes) -> ImageAssetReport:
    if not isinstance(data, bytes) or not data:
        raise ValueError("image content must be non-empty bytes")
    if len(data) > _MAX_IMAGE_BYTES:
        raise ValueError("image content exceeds 16 MiB inspection limit")
    fmt = "UNKNOWN"
    width: int | None = None
    height: int | None = None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        fmt = "PNG"; width, height = struct.unpack(">II", data[16:24])
    elif data.startswith((b"\xff\xd8\xff",)):
        fmt = "JPEG"; width, height = _jpeg_dimensions(data)
    elif data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        fmt = "GIF"; width, height = struct.unpack("<HH", data[6:10])
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        fmt = "WEBP"
    elif data.startswith(b"BM") and len(data) >= 26:
        fmt = "BMP"; width, height = abs(struct.unpack("<ii", data[18:26])[0]), abs(struct.unpack("<ii", data[18:26])[1])
    elif data.startswith((b"II*\x00", b"MM\x00*")):
        fmt = "TIFF"
    else:
        probe = data.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")[:8192].lower()
        if b"<svg" in probe and (
            probe.startswith(b"<svg")
            or probe.startswith(b"<?xml")
            or probe.startswith(b"<!doctype")
        ):
            fmt = "SVG"
            try:
                width, height = _svg_dimensions(data)
            except (ET.ParseError, ValueError) as exc:
                return ImageAssetReport(
                    detected_format="SVG", mime_type=_MIME["SVG"], byte_length=len(data),
                    source_sha256=hashlib.sha256(data).hexdigest(), decode_path="SVG_XML_INSPECTION",
                    diagnostic_code="UNSAFE_OR_INVALID_SVG", diagnostic_reason=str(exc)[:256],
                )
    code = "OK" if fmt != "UNKNOWN" else "UNKNOWN_IMAGE_FORMAT"
    reason = "" if code == "OK" else "content magic does not match a supported image format"
    if width is not None and height is not None and (
        width > _MAX_DIMENSION or height > _MAX_DIMENSION or width * height > _MAX_PIXELS
    ):
        code = "IMAGE_DIMENSIONS_EXCEED_LIMIT"
        reason = f"decoded dimensions {width}x{height} exceed the bounded preview limit"
    return ImageAssetReport(
        detected_format=fmt,
        mime_type=_MIME[fmt],
        byte_length=len(data),
        source_sha256=hashlib.sha256(data).hexdigest(),
        width=width,
        height=height,
        diagnostic_code=code,
        diagnostic_reason=reason,
    )


def inspect_image_asset(path: str | Path) -> ImageAssetReport:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    data = source.read_bytes()
    return inspect_image_bytes(data)


def content_image_extension(data: bytes) -> str:
    report = inspect_image_bytes(data)
    return _EXTENSION[report.detected_format] if report.diagnostic_code == "OK" else ".img"


def decode_image_for_preview(
    path: str | Path,
    *,
    max_size: tuple[int, int],
    rotation_deg: int = 0,
) -> tuple[Any, ImageAssetReport]:
    rotation = validate_rotation(rotation_deg)
    source = Path(path)
    data = source.read_bytes()
    report = inspect_image_bytes(data)
    if report.diagnostic_code != "OK":
        raise ImageAssetDecodeError(report)
    payload = data
    decode_path = "PIL_BYTES"
    if report.detected_format == "SVG":
        try:
            import cairosvg
        except ImportError as exc:
            raise ImageAssetDecodeError(replace(
                report, decode_path="SVG_BYTES", diagnostic_code="SVG_RASTERIZER_UNAVAILABLE",
                diagnostic_reason="a safe SVG rasterizer is not installed",
            )) from exc
        options = {}
        if report.width is not None:
            options["output_width"] = report.width
        if report.height is not None:
            options["output_height"] = report.height
        payload = cairosvg.svg2png(bytestring=data, **options)
        decode_path = "CAIROSVG_BYTES_TO_PNG"
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImageAssetDecodeError(replace(
            report, decode_path=decode_path, diagnostic_code="PIL_UNAVAILABLE",
            diagnostic_reason="Pillow is required for raster preview",
        )) from exc
    try:
        with Image.open(BytesIO(payload)) as opened:
            if (
                opened.width > _MAX_DIMENSION
                or opened.height > _MAX_DIMENSION
                or opened.width * opened.height > _MAX_PIXELS
            ):
                raise ValueError(
                    f"decoded dimensions {opened.width}x{opened.height} exceed limit"
                )
            opened.load()
            image = opened.convert("RGBA")
    except Exception as exc:
        raise ImageAssetDecodeError(replace(
            report, decode_path=decode_path, diagnostic_code="PIXEL_DECODE_FAILED",
            diagnostic_reason=f"{type(exc).__name__}: {exc}"[:256],
        )) from exc
    if rotation:
        image = image.rotate(-rotation, expand=True)
    image.thumbnail(max_size)
    return image.copy(), replace(
        report, width=image.width, height=image.height, decode_path=decode_path,
    )


def normalize_image_to_png(source_path: str | Path, output_path: str | Path) -> ImageAssetReport:
    image, report = decode_image_for_preview(
        source_path, max_size=(16384, 16384), rotation_deg=0,
    )
    target = Path(output_path)
    if target.suffix.casefold() != ".png":
        raise ValueError("normalized image target must use .png")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(fd)
    temp = Path(raw)
    try:
        image.save(temp, format="PNG")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return replace(report, decode_path=f"{report.decode_path}_NORMALIZED_PNG")


__all__ = [
    "ImageAssetDecodeError",
    "ImageAssetReport",
    "content_image_extension",
    "decode_image_for_preview",
    "inspect_image_asset",
    "inspect_image_bytes",
    "normalize_image_to_png",
    "validate_rotation",
]
