from __future__ import annotations

import base64
from pathlib import Path

import pytest

from ai_video_production.dbd_image_assets import (
    ImageAssetDecodeError,
    content_image_extension,
    decode_image_for_preview,
    inspect_image_asset,
    inspect_image_bytes,
    validate_rotation,
)
from ai_video_production.dbd_kamigame_collector import _image_extension
from ai_video_production.dbd_map_intelligence import MapIntelligenceStore, MapRecord


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_png_bytes_under_opaque_suffix_are_content_sniffed(tmp_path: Path) -> None:
    path = tmp_path / "map-cache.img"
    path.write_bytes(PNG_1X1)
    report = inspect_image_asset(path)
    assert report.detected_format == "PNG"
    assert report.mime_type == "image/png"
    assert (report.width, report.height) == (1, 1)
    assert report.diagnostic_code == "OK"
    assert content_image_extension(PNG_1X1) == ".png"
    assert _image_extension("application/octet-stream", PNG_1X1) == ".png"


def test_svg_bytes_under_opaque_suffix_are_identified_and_unsafe_svg_fails_closed(tmp_path: Path) -> None:
    safe = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 330 90"><path d="M0 0h1v1z"/></svg>'
    path = tmp_path / "map-cache.img"
    path.write_bytes(safe)
    report = inspect_image_asset(path)
    assert report.detected_format == "SVG"
    assert report.mime_type == "image/svg+xml"
    assert (report.width, report.height) == (330, 90)
    assert content_image_extension(safe) == ".svg"

    unsafe = b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///secret">]><svg xmlns="http://www.w3.org/2000/svg"/>'
    rejected = inspect_image_bytes(unsafe)
    assert rejected.detected_format == "SVG"
    assert rejected.diagnostic_code == "UNSAFE_OR_INVALID_SVG"
    assert content_image_extension(unsafe) == ".img"

    late_declaration = b'<svg xmlns="http://www.w3.org/2000/svg">' + (b" " * 9000) + b'<! ENTITY xxe "unsafe"></svg>'
    assert inspect_image_bytes(late_declaration).diagnostic_code == "UNSAFE_OR_INVALID_SVG"

    external = b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/map.png"/></svg>'
    assert inspect_image_bytes(external).diagnostic_code == "UNSAFE_OR_INVALID_SVG"


def test_oversized_declared_dimensions_fail_before_pixel_decode() -> None:
    oversized = PNG_1X1[:16] + (20000).to_bytes(4, "big") + (20000).to_bytes(4, "big") + PNG_1X1[24:]
    report = inspect_image_bytes(oversized)
    assert report.detected_format == "PNG"
    assert report.diagnostic_code == "IMAGE_DIMENSIONS_EXCEED_LIMIT"
    assert content_image_extension(oversized) == ".img"


def test_preview_decode_is_suffix_independent_or_fail_visible_without_pillow(tmp_path: Path) -> None:
    path = tmp_path / "valid-raster.img"
    path.write_bytes(PNG_1X1)
    try:
        image, report = decode_image_for_preview(path, max_size=(64, 64), rotation_deg=90)
    except ImageAssetDecodeError as exc:
        assert exc.report.detected_format == "PNG"
        assert exc.report.diagnostic_code == "PIL_UNAVAILABLE"
    else:
        assert image.size == (1, 1)
        assert report.decode_path == "PIL_BYTES"


def test_rotation_contract_and_store_persistence(tmp_path: Path) -> None:
    for value in (0, 90, 180, 270):
        assert validate_rotation(value) == value
    with pytest.raises(ValueError, match="0/90/180/270"):
        validate_rotation(45)
    path = tmp_path / "maps.json"
    store = MapIntelligenceStore(path)
    store.upsert(MapRecord(map_id="map-1", map_name="テストマップ", image_path="cache.img"))
    store.set_orientation("map-1", 90, note="右回転をCanonical Upとして保存")
    reopened = MapIntelligenceStore(path).get("map-1")
    assert reopened.rotation_deg == 90
    assert reopened.orientation_locked is True


def test_training_studio_keeps_strong_reference_and_fail_visible_diagnostic() -> None:
    text = Path("src/ai_video_production/dbd_training_studio.py").read_text(encoding="utf-8")
    assert "decode_image_for_preview(" in text
    assert 'image_ref={"photo":None}' in text
    assert 'image_ref["photo"]=photo' in text
    assert "前回表示を保持" in text
    assert "diagnostic_code" in text
    assert "表示回転 {rotation.get()}°" in text
