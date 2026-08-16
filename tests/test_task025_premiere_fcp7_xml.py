from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import inspect
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from ai_video_production.premiere_fcp7_xml import (
    FCP7MediaBinding,
    FCP7SequenceProfile,
    PremiereFCP7XMLPackage,
    compile_premiere_fcp7_xml,
    verify_premiere_fcp7_package_hash,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.timebase import FrameRate
from ai_video_production.timeline_mapping import EditSegment, TimelineMappingService


ROOT = Path(__file__).resolve().parents[1]
ASSET_A = "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAV"
ASSET_B = "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAW"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def simple_plan(rate: FrameRate = FrameRate(30)):
    return TimelineMappingService.build(
        [EditSegment("clip-1", ASSET_A, 0, 1_000_000)], timeline_rate=rate
    )


def binding(
    asset_id: str = ASSET_A,
    rate: FrameRate = FrameRate(30),
    duration_frames: int = 300,
    uri: str = "file://localhost/C:/BAI/media/clip01.mov",
) -> FCP7MediaBinding:
    return FCP7MediaBinding(asset_id, SHA_A, "clip01.mov", uri, rate, duration_frames)


def package(rate: FrameRate = FrameRate(30)) -> PremiereFCP7XMLPackage:
    return compile_premiere_fcp7_xml(
        FCP7SequenceProfile("Sequence 01", 1920, 1080, rate),
        simple_plan(rate),
        (binding(rate=rate),),
    )


EXPECTED_XML_30 = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n'
    '<xmeml version="5"><sequence id="sequence-1"><name>Sequence 01</name><duration>30</duration>'
    '<rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate><media><video><format>'
    '<samplecharacteristics><rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate>'
    '<width>1920</width><height>1080</height><anamorphic>FALSE</anamorphic>'
    '<pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance>'
    '</samplecharacteristics></format><track><clipitem id="clipitem-000001"><name>clip01.mov</name>'
    '<duration>300</duration><rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate>'
    '<start>0</start><end>30</end><in>0</in><out>30</out><file id="file-000001">'
    '<name>clip01.mov</name><pathurl>file://localhost/C:/BAI/media/clip01.mov</pathurl>'
    '<rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate><duration>300</duration></file>'
    '</clipitem><enabled>TRUE</enabled><locked>FALSE</locked></track></video></media></sequence></xmeml>\n'
).encode("utf-8")


def test_golden_xml_is_deterministic_well_formed_and_schema_valid():
    compiled = package()
    assert compiled.xml_bytes == EXPECTED_XML_30
    assert package().xml_bytes == compiled.xml_bytes
    root = ET.fromstring(compiled.xml_bytes)
    assert root.tag == "xmeml"
    assert root.attrib == {"version": "5"}
    receipt = compiled.to_dict()
    assert receipt["format"] == "FCP7_XMEML_V5"
    assert receipt["xml_sha256"] == sha256_bytes(EXPECTED_XML_30)
    assert receipt["premiere_import_performed"] is False
    assert receipt["external_mutation_authorized"] is False
    assert receipt["human_import_review_required"] is True
    verify_premiere_fcp7_package_hash(receipt)
    validate_instance(receipt, ROOT / "schemas" / "premiere-fcp7-xml-package.schema.json")


def test_schema_mirror_is_byte_identical():
    public = (ROOT / "schemas" / "premiere-fcp7-xml-package.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "premiere-fcp7-xml-package.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(package().to_dict(), json.loads(public))


@pytest.mark.parametrize(
    ("rate", "timebase", "ntsc"),
    [
        (FrameRate(24), "24", "FALSE"),
        (FrameRate(24000, 1001), "24", "TRUE"),
        (FrameRate(25), "25", "FALSE"),
        (FrameRate(30), "30", "FALSE"),
        (FrameRate(30000, 1001), "30", "TRUE"),
        (FrameRate(50), "50", "FALSE"),
        (FrameRate(60), "60", "FALSE"),
        (FrameRate(60000, 1001), "60", "TRUE"),
    ],
)
def test_closed_frame_rate_matrix(rate, timebase, ntsc):
    compiled = package(rate)
    root = ET.fromstring(compiled.xml_bytes)
    first_rate = root.find("./sequence/rate")
    assert first_rate is not None
    assert first_rate.findtext("timebase") == timebase
    assert first_rate.findtext("ntsc") == ntsc


def test_unsupported_rate_and_cross_rate_binding_fail_closed():
    with pytest.raises(ValueError, match="compatibility matrix"):
        FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(23))
    with pytest.raises(ValueError, match="media and Timeline"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
            simple_plan(FrameRate(30)),
            (binding(rate=FrameRate(25)),),
        )


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/clip.mov",
        "file://localhost/C:/BAI/../secret.mov",
        "file://localhost/C:/BAI/%2e%2e/secret.mov",
        "file://localhost/C:/BAI/%2Fsecret.mov",
        "file://localhost/C:\\BAI\\clip.mov",
        "file://localhost/C:/BAI/clip.mov?token=x",
        "file://localhost/C:/BAI/clip.mov#fragment",
    ],
)
def test_media_uri_is_strict_and_non_laundering(uri):
    with pytest.raises(ValueError, match="media_uri"):
        binding(uri=uri)


def test_public_receipt_hides_private_media_uri_but_binds_digest():
    compiled = package()
    receipt = compiled.to_dict()
    encoded = json.dumps(receipt, sort_keys=True)
    assert "file://" not in encoded
    assert "C:/BAI" not in encoded
    media = receipt["media_binding_receipts"][0]
    assert media["media_uri_public"] is False
    assert media["media_uri_sha256"] == sha256_bytes(binding().media_uri.encode("utf-8"))


def test_binding_set_must_equal_mapped_assets_without_extra_or_missing_rows():
    with pytest.raises(ValueError, match="exactly equal"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
            simple_plan(),
            (binding(), binding(ASSET_B, uri="file://localhost/C:/BAI/media/clip02.mov")),
        )
    with pytest.raises(ValueError, match="1-10000"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)), simple_plan(), ()
        )


def test_source_duration_origin_retime_and_placement_identity_fail_closed():
    with pytest.raises(ValueError, match="outside bound media duration"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
            simple_plan(),
            (binding(duration_frames=29),),
        )
    origin_plan = TimelineMappingService.build(
        [EditSegment("clip-1", ASSET_A, 0, 1_000_000)],
        timeline_rate=FrameRate(30), timeline_origin_frame=1,
    )
    with pytest.raises(ValueError, match="timeline_origin_frame=0"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
            origin_plan, (binding(),),
        )
    retimed = TimelineMappingService.build(
        [EditSegment("clip-1", ASSET_A, 0, 2_000_000, playback_rate_numerator=2)],
        timeline_rate=FrameRate(30),
    )
    with pytest.raises(ValueError, match="retimed"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
            retimed, (binding(duration_frames=60),),
        )
    unsafe = TimelineMappingService.build(
        [EditSegment("../clip", ASSET_A, 0, 1_000_000)], timeline_rate=FrameRate(30)
    )
    with pytest.raises(ValueError, match="placement_id"):
        compile_premiere_fcp7_xml(
            FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)), unsafe, (binding(),)
        )


def test_gaps_and_multiple_assets_preserve_exact_timeline_ranges():
    plan = TimelineMappingService.build(
        (
            EditSegment("clip-a", ASSET_A, 0, 1_000_000),
            EditSegment("clip-b", ASSET_B, 0, 1_000_000, gap_before_frames=10),
        ),
        timeline_rate=FrameRate(30),
    )
    compiled = compile_premiere_fcp7_xml(
        FCP7SequenceProfile("Sequence 01", 1920, 1080, FrameRate(30)),
        plan,
        (
            binding(ASSET_B, uri="file://localhost/C:/BAI/media/clip02.mov"),
            binding(),
        ),
    )
    root = ET.fromstring(compiled.xml_bytes)
    clips = root.findall("./sequence/media/video/track/clipitem")
    assert [(item.findtext("start"), item.findtext("end")) for item in clips] == [
        ("0", "30"), ("40", "70")
    ]
    assert [row["asset_id"] for row in compiled.to_dict()["media_binding_receipts"]] == [
        ASSET_A, ASSET_B
    ]


def test_manual_package_xml_and_receipt_tamper_fail_closed():
    compiled = package()
    with pytest.raises(ValueError, match="canonical FCP7"):
        replace(compiled, xml_bytes=compiled.xml_bytes + b" ")
    with pytest.raises(FrozenInstanceError):
        compiled.xml_bytes = b""  # type: ignore[misc]
    receipt = compiled.to_dict()
    receipt["xml_byte_length"] += 1
    with pytest.raises(ValueError, match="package_sha256"):
        verify_premiere_fcp7_package_hash(receipt)


def test_public_api_and_import_surface_have_no_external_effect_capability():
    assert set(inspect.signature(compile_premiere_fcp7_xml).parameters) == {
        "profile", "timeline_plan", "media_bindings"
    }
    tree = ast.parse(
        (ROOT / "src" / "ai_video_production" / "premiere_fcp7_xml.py").read_text("utf-8")
    )
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"subprocess", "requests", "urllib", "httpx", "pathlib", "socket"})
    calls = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})

