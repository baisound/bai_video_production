"""Bounded synthetic WAV runtime for TASK-046/P-VS-4B Gate 4 R0.

Only explicitly synthetic, non-Owner PCM WAVs may be inspected or assembled.
The adapter performs no Dataset, training, model inference, publication, or
Asset effect.  Runtime paths are caller-supplied contained roots and are never
serialized into receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import inspect
import os
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping
import wave

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task046.voice-model-builder-runtime.v1"
MAX_CUES = 256
MAX_TOTAL_FRAMES = 48_000 * 60 * 10
MAX_PAUSE_SAMPLES = 48_000 * 10
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class AuthorityKind(str, Enum):
    APPROVED_SYNTHETIC_TEST_AUTHORITY = "APPROVED_SYNTHETIC_TEST_AUTHORITY"


class FormatState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ExecutionState(str, Enum):
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    COMPLETED_SYNTHETIC = "COMPLETED_SYNTHETIC"


def _expect(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    if (
        "\\" in value
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:/", value) is not None
        or any(part == ".." for part in value.split("/"))
    ):
        raise ValueError(f"{name} must be a contained logical identifier")
    return value


def _logical_file(value: Any, name: str) -> str:
    result = _id(value, name)
    path = PurePosixPath(result)
    if path.is_absolute() or not path.name or path.name in {".", ".."}:
        raise ValueError(f"{name} must identify a contained file")
    return result


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _digest_body(value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(canonical_json_bytes({key: item for key, item in value.items() if key != field}))


def add_record_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result[field] = _digest_body(result, field)
    return result


def _verify_digest(value: Mapping[str, Any], field: str) -> None:
    _sha(value[field], field)
    if value[field] != _digest_body(value, field):
        raise ValueError(f"{field} mismatch")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _validate_inspection(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "receipt_id", "source_logical_ref", "source_sha256", "source_bytes",
        "sample_rate_hz", "channels", "sample_width_bytes", "frame_count",
        "duration_numerator", "duration_denominator", "format_state", "synthetic_input",
        "owner_audio_used", "inspected_at", "receipt_sha256",
    }
    _expect(value, fields, "WavInspectionReceipt")
    _id(value["receipt_id"], "receipt_id")
    _logical_file(value["source_logical_ref"], "source_logical_ref")
    _sha(value["source_sha256"], "source_sha256")
    for name in ("source_bytes", "frame_count", "duration_numerator"):
        if not isinstance(value[name], int) or value[name] < 0:
            raise ValueError(f"{name} is invalid")
    if value["duration_denominator"] != 48_000:
        raise ValueError("duration denominator must be the canonical sample rate")
    exact = value["sample_rate_hz"] == 48_000 and value["channels"] == 1 and value["sample_width_bytes"] == 3
    state = _enum(FormatState, value["format_state"], "format_state")
    if (state is FormatState.PASS) != exact:
        raise ValueError("format_state must reflect exact 48 kHz / mono / PCM 24-bit facts")
    if value["duration_numerator"] != value["frame_count"]:
        raise ValueError("duration must retain exact integer-sample truth")
    if value["synthetic_input"] is not True or value["owner_audio_used"] is not False:
        raise ValueError("R0 inspection is synthetic and non-Owner only")
    _timestamp(value["inspected_at"], "inspected_at")
    _verify_digest(value, "receipt_sha256")


def _validate_request(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "request_id", "workflow_sha256", "model_candidate_sha256",
        "voice_profile_revision_sha256", "assembly_policy_sha256", "authority_kind",
        "authority_evidence_sha256", "ordered_inputs", "output_logical_ref",
        "max_total_frames", "execution_state", "execution_started", "owner_audio_used",
        "dataset_effect_started", "training_started", "model_inference_started",
        "publication_started", "created_at", "request_sha256",
    }
    _expect(value, fields, "SyntheticMasterAssemblyRequest")
    _id(value["request_id"], "request_id")
    for name in (
        "workflow_sha256", "model_candidate_sha256", "voice_profile_revision_sha256",
        "assembly_policy_sha256", "authority_evidence_sha256",
    ):
        _sha(value[name], name)
    _enum(AuthorityKind, value["authority_kind"], "authority_kind")
    inputs = value["ordered_inputs"]
    if not isinstance(inputs, list) or not 2 <= len(inputs) <= MAX_CUES:
        raise ValueError("ordered_inputs must contain 2..256 Cues")
    seen_cues: set[str] = set()
    seen_refs: set[str] = set()
    for index, item in enumerate(inputs):
        _expect(item, {"order_index", "cue_sha256", "source_logical_ref", "inspection_receipt_sha256", "pause_after_samples"}, "ordered input")
        if item["order_index"] != index:
            raise ValueError("Cue order must be contiguous and deterministic")
        _sha(item["cue_sha256"], "cue_sha256")
        _sha(item["inspection_receipt_sha256"], "inspection_receipt_sha256")
        _logical_file(item["source_logical_ref"], "source_logical_ref")
        pause = item["pause_after_samples"]
        if not isinstance(pause, int) or not 0 <= pause <= MAX_PAUSE_SAMPLES:
            raise ValueError("pause_after_samples is out of bounds")
        if item["cue_sha256"] in seen_cues or item["source_logical_ref"] in seen_refs:
            raise ValueError("Cue and source references must be unique")
        seen_cues.add(item["cue_sha256"])
        seen_refs.add(item["source_logical_ref"])
    if inputs[-1]["pause_after_samples"] != 0:
        raise ValueError("the final Cue cannot append trailing silence")
    _logical_file(value["output_logical_ref"], "output_logical_ref")
    if not isinstance(value["max_total_frames"], int) or not 1 <= value["max_total_frames"] <= MAX_TOTAL_FRAMES:
        raise ValueError("max_total_frames is invalid")
    if _enum(ExecutionState, value["execution_state"], "execution_state") is not ExecutionState.PROPOSAL_ONLY:
        raise ValueError("request must remain a proposal")
    for name in (
        "execution_started", "owner_audio_used", "dataset_effect_started", "training_started",
        "model_inference_started", "publication_started",
    ):
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "request_sha256")


def _validate_execution(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "receipt_id", "request_sha256", "ordered_cue_sha256",
        "output_logical_ref", "output_sha256", "output_bytes", "sample_rate_hz",
        "channels", "sample_width_bytes", "frame_count", "duration_numerator",
        "duration_denominator", "inserted_silence_samples", "format_state",
        "boundary_analysis_state", "loudness_analysis_state", "style_analysis_state",
        "execution_state", "owner_audio_used", "dataset_effect_started", "training_started",
        "model_inference_started", "asset_adoption_started", "publication_started",
        "completed_at", "receipt_sha256",
    }
    _expect(value, fields, "SyntheticMasterAssemblyReceipt")
    _id(value["receipt_id"], "receipt_id")
    _sha(value["request_sha256"], "request_sha256")
    cues = value["ordered_cue_sha256"]
    if not isinstance(cues, list) or not 2 <= len(cues) <= MAX_CUES or len(cues) != len(set(cues)):
        raise ValueError("ordered_cue_sha256 is invalid")
    for cue in cues:
        _sha(cue, "ordered_cue_sha256")
    _logical_file(value["output_logical_ref"], "output_logical_ref")
    _sha(value["output_sha256"], "output_sha256")
    for name in ("output_bytes", "frame_count", "duration_numerator", "inserted_silence_samples"):
        if not isinstance(value[name], int) or value[name] < 0:
            raise ValueError(f"{name} is invalid")
    if (value["sample_rate_hz"], value["channels"], value["sample_width_bytes"]) != (48_000, 1, 3):
        raise ValueError("output must be exact 48 kHz / mono / PCM 24-bit")
    if value["duration_numerator"] != value["frame_count"] or value["duration_denominator"] != 48_000:
        raise ValueError("duration must retain exact integer-sample truth")
    if _enum(FormatState, value["format_state"], "format_state") is not FormatState.PASS:
        raise ValueError("completed output format must PASS")
    for name in ("boundary_analysis_state", "loudness_analysis_state", "style_analysis_state"):
        if _enum(FormatState, value[name], name) is not FormatState.UNKNOWN:
            raise ValueError("R0 does not synthesize analyzer PASS")
    if _enum(ExecutionState, value["execution_state"], "execution_state") is not ExecutionState.COMPLETED_SYNTHETIC:
        raise ValueError("execution_state is invalid")
    for name in (
        "owner_audio_used", "dataset_effect_started", "training_started", "model_inference_started",
        "asset_adoption_started", "publication_started",
    ):
        if value[name] is not False:
            raise ValueError(f"{name} must remain false")
    _timestamp(value["completed_at"], "completed_at")
    _verify_digest(value, "receipt_sha256")


_VALIDATORS = {
    "WavInspectionReceipt": _validate_inspection,
    "SyntheticMasterAssemblyRequest": _validate_request,
    "SyntheticMasterAssemblyReceipt": _validate_execution,
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if expected_type is not None and record_type != expected_type:
        raise ValueError("record_type mismatch")
    validator = _VALIDATORS.get(record_type)
    if validator is None:
        raise ValueError("record_type is unknown")
    copy = _thaw(value)
    validator(copy)
    return copy


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(validate_record(self.data, expected_type=self.RECORD_TYPE)))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class WavInspectionReceipt(_Record):
    RECORD_TYPE = "WavInspectionReceipt"


class SyntheticMasterAssemblyRequest(_Record):
    RECORD_TYPE = "SyntheticMasterAssemblyRequest"


class SyntheticMasterAssemblyReceipt(_Record):
    RECORD_TYPE = "SyntheticMasterAssemblyReceipt"


def _contained_file(root: Path, logical_ref: str, *, must_exist: bool) -> Path:
    _logical_file(logical_ref, "logical_ref")
    root = Path(root)
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ValueError("runtime root must be an existing non-symlink directory")
    root_resolved = root.resolve(strict=True)
    current = root
    parts = PurePosixPath(logical_ref).parts
    for part in parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError("symlink/reparse traversal is forbidden")
    candidate = root.joinpath(*parts)
    resolved_parent = candidate.parent.resolve(strict=True)
    if root_resolved != resolved_parent and root_resolved not in resolved_parent.parents:
        raise ValueError("runtime path escapes the contained root")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise ValueError("runtime source file is missing")
    if not must_exist and candidate.exists():
        raise ValueError("existing output disposition is not authorized")
    return candidate


def _read_exact_wav(path: Path) -> tuple[bytes, int]:
    try:
        with wave.open(str(path), "rb") as handle:
            params = handle.getparams()
            if params.comptype != "NONE":
                raise ValueError("compressed WAV is not supported")
            if (params.framerate, params.nchannels, params.sampwidth) != (48_000, 1, 3):
                raise ValueError("WAV must be exact 48 kHz / mono / PCM 24-bit")
            if params.nframes > MAX_TOTAL_FRAMES:
                raise ValueError("WAV exceeds the bounded frame cap")
            frames = handle.readframes(params.nframes)
            if len(frames) != params.nframes * 3:
                raise ValueError("WAV frame payload is incomplete")
            return frames, params.nframes
    except (EOFError, wave.Error) as exc:
        raise ValueError("WAV container is invalid") from exc


def inspect_synthetic_wav(*, root: Path, source_logical_ref: str, receipt_id: str, inspected_at: str) -> WavInspectionReceipt:
    path = _contained_file(root, source_logical_ref, must_exist=True)
    _, frame_count = _read_exact_wav(path)
    raw = path.read_bytes()
    body = {
        "record_type": "WavInspectionReceipt",
        "receipt_id": receipt_id,
        "source_logical_ref": source_logical_ref,
        "source_sha256": sha256_bytes(raw),
        "source_bytes": len(raw),
        "sample_rate_hz": 48_000,
        "channels": 1,
        "sample_width_bytes": 3,
        "frame_count": frame_count,
        "duration_numerator": frame_count,
        "duration_denominator": 48_000,
        "format_state": "PASS",
        "synthetic_input": True,
        "owner_audio_used": False,
        "inspected_at": inspected_at,
    }
    return WavInspectionReceipt(add_record_digest(body, "receipt_sha256"))


def compile_synthetic_master_request(
    *, request_id: str, workflow_sha256: str, model_candidate_sha256: str,
    voice_profile_revision_sha256: str, assembly_policy_sha256: str,
    authority_evidence_sha256: str, ordered_inputs: list[Mapping[str, Any]],
    output_logical_ref: str, max_total_frames: int, created_at: str,
) -> SyntheticMasterAssemblyRequest:
    body = {
        "record_type": "SyntheticMasterAssemblyRequest",
        "request_id": request_id,
        "workflow_sha256": workflow_sha256,
        "model_candidate_sha256": model_candidate_sha256,
        "voice_profile_revision_sha256": voice_profile_revision_sha256,
        "assembly_policy_sha256": assembly_policy_sha256,
        "authority_kind": "APPROVED_SYNTHETIC_TEST_AUTHORITY",
        "authority_evidence_sha256": authority_evidence_sha256,
        "ordered_inputs": [dict(item) for item in ordered_inputs],
        "output_logical_ref": output_logical_ref,
        "max_total_frames": max_total_frames,
        "execution_state": "PROPOSAL_ONLY",
        "execution_started": False,
        "owner_audio_used": False,
        "dataset_effect_started": False,
        "training_started": False,
        "model_inference_started": False,
        "publication_started": False,
        "created_at": created_at,
    }
    return SyntheticMasterAssemblyRequest(add_record_digest(body, "request_sha256"))


def execute_synthetic_master_assembly(
    *, request: Mapping[str, Any], inspection_receipts: list[Mapping[str, Any]],
    source_root: Path, output_root: Path, receipt_id: str, completed_at: str,
) -> SyntheticMasterAssemblyReceipt:
    validated = validate_record(request, expected_type="SyntheticMasterAssemblyRequest")
    receipts = {
        item["receipt_sha256"]: validate_record(item, expected_type="WavInspectionReceipt")
        for item in inspection_receipts
    }
    if len(receipts) != len(inspection_receipts):
        raise ValueError("inspection receipts must be unique")
    chunks: list[bytes] = []
    total_frames = 0
    silence = 0
    cues: list[str] = []
    for item in validated["ordered_inputs"]:
        receipt = receipts.get(item["inspection_receipt_sha256"])
        if receipt is None or receipt["source_logical_ref"] != item["source_logical_ref"]:
            raise ValueError("Cue inspection receipt binding mismatch")
        path = _contained_file(source_root, item["source_logical_ref"], must_exist=True)
        raw = path.read_bytes()
        if sha256_bytes(raw) != receipt["source_sha256"] or len(raw) != receipt["source_bytes"]:
            raise ValueError("Cue WAV changed after inspection")
        frames, frame_count = _read_exact_wav(path)
        if frame_count != receipt["frame_count"]:
            raise ValueError("Cue frame count changed after inspection")
        pause = item["pause_after_samples"]
        chunks.append(frames)
        if pause:
            chunks.append(b"\x00" * (pause * 3))
        total_frames += frame_count + pause
        silence += pause
        cues.append(item["cue_sha256"])
    if total_frames > validated["max_total_frames"]:
        raise ValueError("assembled Master exceeds request frame cap")
    output = _contained_file(output_root, validated["output_logical_ref"], must_exist=False)
    digest_suffix = validated["request_sha256"].removeprefix("sha256:")[:16]
    temp = output.with_name(f".{output.name}.{digest_suffix}.tmp")
    if temp.exists() or temp.is_symlink():
        raise ValueError("atomic output temp target is not clean")
    with wave.open(str(temp), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(3)
        handle.setframerate(48_000)
        handle.writeframes(b"".join(chunks))
    os.replace(temp, output)
    raw_output = output.read_bytes()
    _, readback_frames = _read_exact_wav(output)
    if readback_frames != total_frames:
        raise ValueError("Master read-back frame count mismatch")
    body = {
        "record_type": "SyntheticMasterAssemblyReceipt",
        "receipt_id": receipt_id,
        "request_sha256": validated["request_sha256"],
        "ordered_cue_sha256": cues,
        "output_logical_ref": validated["output_logical_ref"],
        "output_sha256": sha256_bytes(raw_output),
        "output_bytes": len(raw_output),
        "sample_rate_hz": 48_000,
        "channels": 1,
        "sample_width_bytes": 3,
        "frame_count": total_frames,
        "duration_numerator": total_frames,
        "duration_denominator": 48_000,
        "inserted_silence_samples": silence,
        "format_state": "PASS",
        "boundary_analysis_state": "UNKNOWN",
        "loudness_analysis_state": "UNKNOWN",
        "style_analysis_state": "UNKNOWN",
        "execution_state": "COMPLETED_SYNTHETIC",
        "owner_audio_used": False,
        "dataset_effect_started": False,
        "training_started": False,
        "model_inference_started": False,
        "asset_adoption_started": False,
        "publication_started": False,
        "completed_at": completed_at,
    }
    return SyntheticMasterAssemblyReceipt(add_record_digest(body, "receipt_sha256"))


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    record = validate_record(value)
    if record["record_type"] == "WavInspectionReceipt":
        return {
            "record_type": record["record_type"],
            "format_state": record["format_state"],
            "sample_rate_hz": record["sample_rate_hz"],
            "channels": record["channels"],
            "sample_width_bytes": record["sample_width_bytes"],
            "owner_audio_used": False,
        }
    if record["record_type"] == "SyntheticMasterAssemblyRequest":
        return {
            "record_type": record["record_type"],
            "cue_count": len(record["ordered_inputs"]),
            "execution_state": record["execution_state"],
            "effect_authorized": False,
        }
    return {
        "record_type": record["record_type"],
        "cue_count": len(record["ordered_cue_sha256"]),
        "format_state": record["format_state"],
        "boundary_analysis_state": record["boundary_analysis_state"],
        "loudness_analysis_state": record["loudness_analysis_state"],
        "style_analysis_state": record["style_analysis_state"],
        "owner_audio_used": False,
        "publication_started": False,
    }


def assert_no_forbidden_effect_surface() -> None:
    module = inspect.getmodule(assert_no_forbidden_effect_surface)
    forbidden_imports = {"subprocess", "socket", "requests", "urllib", "torch"}
    if module is None or forbidden_imports.intersection(module.__dict__):
        raise AssertionError("forbidden runtime effect surface detected")
