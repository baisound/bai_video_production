from __future__ import annotations

import copy
import json
from pathlib import Path
import wave

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.voice_model_builder_runtime import (
    SyntheticMasterAssemblyReceipt,
    WavInspectionReceipt,
    add_record_digest,
    assert_no_forbidden_effect_surface,
    compile_synthetic_master_request,
    execute_synthetic_master_assembly,
    inspect_synthetic_wav,
    public_projection,
    validate_record,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "voice-model-builder-runtime.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "voice-model-builder-runtime.schema.json"
NOW = "2026-08-17T00:00:00Z"
H = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64
H4 = "sha256:" + "4" * 64


def write_wav(path: Path, *, frames: int, rate: int = 48_000, channels: int = 1, width: int = 3, byte: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(bytes([byte]) * frames * channels * width)


def inspected(root: Path, logical_ref: str, receipt_id: str) -> dict:
    return inspect_synthetic_wav(
        root=root,
        source_logical_ref=logical_ref,
        receipt_id=receipt_id,
        inspected_at=NOW,
    ).to_dict()


def request(receipts: list[dict], *, output: str = "master/test.wav", pauses: list[int] | None = None, frame_cap: int = 20_000) -> dict:
    pauses = pauses or [480, 0]
    ordered = [
        {
            "order_index": index,
            "cue_sha256": "sha256:" + str(index + 5) * 64,
            "source_logical_ref": receipt["source_logical_ref"],
            "inspection_receipt_sha256": receipt["receipt_sha256"],
            "pause_after_samples": pauses[index],
        }
        for index, receipt in enumerate(receipts)
    ]
    return compile_synthetic_master_request(
        request_id="request:synthetic-master:1",
        workflow_sha256=H,
        model_candidate_sha256=H2,
        voice_profile_revision_sha256=H3,
        assembly_policy_sha256=H4,
        authority_evidence_sha256="sha256:" + "a" * 64,
        ordered_inputs=ordered,
        output_logical_ref=output,
        max_total_frames=frame_cap,
        created_at=NOW,
    ).to_dict()


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


def test_inspection_receipt_matches_schema_and_is_body_free(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_wav(source / "cue" / "one.wav", frames=960)
    result = inspected(source, "cue/one.wav", "inspection:one")
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(result)
    assert WavInspectionReceipt(result).to_dict() == result
    assert result["duration_numerator"] == 960
    assert result["duration_denominator"] == 48_000
    assert result["owner_audio_used"] is False
    assert "absolute" not in json.dumps(result).lower()


@pytest.mark.parametrize(
    ("rate", "channels", "width"),
    [(44_100, 1, 3), (48_000, 2, 3), (48_000, 1, 2)],
)
def test_inspection_rejects_noncanonical_wav(tmp_path: Path, rate: int, channels: int, width: int) -> None:
    source = tmp_path / "source"
    write_wav(source / "bad.wav", frames=100, rate=rate, channels=channels, width=width)
    with pytest.raises(ValueError, match="48 kHz"):
        inspected(source, "bad.wav", "inspection:bad")


def test_request_is_synthetic_proposal_only_and_ordered(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_wav(source / "one.wav", frames=100, byte=1)
    write_wav(source / "two.wav", frames=100, byte=2)
    receipts = [inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")]
    result = request(receipts)
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(result)
    assert result["authority_kind"] == "APPROVED_SYNTHETIC_TEST_AUTHORITY"
    assert result["execution_started"] is False
    bad = copy.deepcopy(result)
    bad["ordered_inputs"][1]["order_index"] = 4
    bad = add_record_digest(bad, "request_sha256")
    with pytest.raises(ValueError, match="contiguous"):
        validate_record(bad)


def test_request_rejects_owner_or_effect_flags(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_wav(source / "one.wav", frames=100)
    write_wav(source / "two.wav", frames=100)
    record = request([inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")])
    for field in ("owner_audio_used", "training_started", "model_inference_started", "publication_started"):
        forged = copy.deepcopy(record)
        forged[field] = True
        forged = add_record_digest(forged, "request_sha256")
        with pytest.raises(ValueError, match="must remain false"):
            validate_record(forged)


def test_assembly_is_deterministic_exact_format_and_inserts_pause(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    (output / "master").mkdir(parents=True)
    write_wav(source / "cue" / "one.wav", frames=1000, byte=1)
    write_wav(source / "cue" / "two.wav", frames=2000, byte=2)
    receipts = [inspected(source, "cue/one.wav", "inspection:one"), inspected(source, "cue/two.wav", "inspection:two")]
    compiled = request(receipts, pauses=[480, 0])
    result = execute_synthetic_master_assembly(
        request=compiled,
        inspection_receipts=receipts,
        source_root=source,
        output_root=output,
        receipt_id="assembly:synthetic:1",
        completed_at=NOW,
    ).to_dict()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(result)
    assert SyntheticMasterAssemblyReceipt(result).to_dict() == result
    assert result["frame_count"] == 3480
    assert result["inserted_silence_samples"] == 480
    assert result["boundary_analysis_state"] == "UNKNOWN"
    with wave.open(str(output / "master" / "test.wav"), "rb") as handle:
        assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth(), handle.getnframes()) == (48_000, 1, 3, 3480)


def test_assembly_rejects_wav_changed_after_inspection(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    output.mkdir()
    write_wav(source / "one.wav", frames=100, byte=1)
    write_wav(source / "two.wav", frames=100, byte=2)
    receipts = [inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")]
    compiled = request(receipts)
    write_wav(source / "one.wav", frames=100, byte=3)
    with pytest.raises(ValueError, match="changed after inspection"):
        execute_synthetic_master_assembly(
            request=compiled, inspection_receipts=receipts, source_root=source, output_root=output,
            receipt_id="assembly:changed", completed_at=NOW,
        )


def test_assembly_rejects_receipt_swap_and_frame_cap(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    output.mkdir()
    write_wav(source / "one.wav", frames=100)
    write_wav(source / "two.wav", frames=100)
    receipts = [inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")]
    swapped = request(receipts)
    swapped["ordered_inputs"][0]["inspection_receipt_sha256"] = receipts[1]["receipt_sha256"]
    swapped = add_record_digest(swapped, "request_sha256")
    with pytest.raises(ValueError, match="binding mismatch"):
        execute_synthetic_master_assembly(
            request=swapped, inspection_receipts=receipts, source_root=source, output_root=output,
            receipt_id="assembly:swap", completed_at=NOW,
        )
    capped = request(receipts, frame_cap=100)
    with pytest.raises(ValueError, match="frame cap"):
        execute_synthetic_master_assembly(
            request=capped, inspection_receipts=receipts, source_root=source, output_root=output,
            receipt_id="assembly:cap", completed_at=NOW,
        )


def test_existing_output_is_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    (output / "master").mkdir(parents=True)
    (output / "master" / "test.wav").write_bytes(b"occupied")
    write_wav(source / "one.wav", frames=100)
    write_wav(source / "two.wav", frames=100)
    receipts = [inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")]
    with pytest.raises(ValueError, match="existing output"):
        execute_synthetic_master_assembly(
            request=request(receipts), inspection_receipts=receipts, source_root=source, output_root=output,
            receipt_id="assembly:occupied", completed_at=NOW,
        )


def test_containment_rejects_absolute_parent_and_missing_parent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for logical in ("../escape.wav", "C:/owner.wav", "/owner.wav"):
        with pytest.raises(ValueError):
            inspect_synthetic_wav(root=source, source_logical_ref=logical, receipt_id="inspection:bad", inspected_at=NOW)
    output = tmp_path / "output"
    output.mkdir()
    write_wav(source / "one.wav", frames=100)
    write_wav(source / "two.wav", frames=100)
    receipts = [inspected(source, "one.wav", "inspection:one"), inspected(source, "two.wav", "inspection:two")]
    with pytest.raises((FileNotFoundError, ValueError)):
        execute_synthetic_master_assembly(
            request=request(receipts, output="missing/parent/master.wav"), inspection_receipts=receipts,
            source_root=source, output_root=output, receipt_id="assembly:missing-parent", completed_at=NOW,
        )


def test_symlink_source_is_rejected_when_supported(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outside = tmp_path / "outside.wav"
    source.mkdir()
    write_wav(outside, frames=100)
    link = source / "link.wav"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="symlink"):
        inspect_synthetic_wav(root=source, source_logical_ref="link.wav", receipt_id="inspection:link", inspected_at=NOW)


def test_public_projection_hides_coordinates_and_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_wav(source / "one.wav", frames=100)
    projected = public_projection(inspected(source, "one.wav", "inspection:one"))
    encoded = json.dumps(projected, sort_keys=True)
    assert "source_logical_ref" not in encoded
    assert "sha256" not in encoded
    assert projected["owner_audio_used"] is False


def test_digest_tamper_unknown_field_and_unsafe_surface_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_wav(source / "one.wav", frames=100)
    record = inspected(source, "one.wav", "inspection:one")
    record["frame_count"] += 1
    with pytest.raises(ValueError, match="duration|mismatch"):
        validate_record(record)
    extra = inspected(source, "one.wav", "inspection:two")
    extra["raw_audio"] = "forbidden"
    with pytest.raises(ValueError, match="fields"):
        validate_record(extra)
    assert_no_forbidden_effect_surface()
