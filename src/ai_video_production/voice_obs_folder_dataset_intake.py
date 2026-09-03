"""Effect-zero TASK-046 OBS-folder Dataset intake proposal contract.

Only body-free facts are accepted.  Private path/audio/transcript custody,
Asset writes, ASR, quality measurement, Dataset mutation and training belong to
their existing effect owners and are never performed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import inspect
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
CONTRACT_VERSION = "TASK046_OBS_FOLDER_INTAKE_R1"
AUTHORITY_KIND = "SYNTHETIC_CONTRACT_TEST"
SAMPLE_RATE_HZ = 48_000
TRAINING_COPY_FORMAT = "PCM_S24LE_48000_MONO"
MINIMUM_COVERAGE_SAMPLES = SAMPLE_RATE_HZ * 60 * 30
TARGET_COVERAGE_SAMPLES = SAMPLE_RATE_HZ * 60 * 60
MAX_ITEMS = 4096
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_LANGUAGE_RE = re.compile(r"[a-z]{2,8}(?:-[A-Za-z0-9]{2,8})*")
MAX_INTEGER = 2**63 - 1
MAX_SEGMENT_US = 60 * 60 * 1_000_000
MAX_SEGMENT_SAMPLES = SAMPLE_RATE_HZ * 60 * 60


class ContractState(str, Enum):
    BOUND_VERIFIED = "BOUND_VERIFIED"
    NOT_BOUND = "NOT_BOUND"
    MISMATCH = "MISMATCH"
    STALE = "STALE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class FactState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    STALE = "STALE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class FolderCurrentness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class AvailabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class StabilityState(str, Enum):
    STABLE = "STABLE"
    WRITE_IN_PROGRESS = "WRITE_IN_PROGRESS"
    LOCKED = "LOCKED"
    PARTIAL_OR_TEMP = "PARTIAL_OR_TEMP"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class TrackClass(str, Enum):
    MIC_ISOLATED = "MIC_ISOLATED"
    MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"
    NON_MIC_ONLY = "NON_MIC_ONLY"
    UNKNOWN = "UNKNOWN"


class OwnerDecision(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class CandidateDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    EXCLUDED = "EXCLUDED"


class CoverageState(str, Enum):
    COVERAGE_LT_30 = "COVERAGE_LT_30"
    REVIEW_BLOCKED = "REVIEW_BLOCKED"
    MINIMUM_COVERAGE_MET = "MINIMUM_COVERAGE_MET"
    TARGET_COVERAGE_MET = "TARGET_COVERAGE_MET"


_QUALITY_REASONS = {
    "SILENCE", "CLIPPING", "LOW_SNR", "OTHER_SPEAKER",
    "MUSIC_OR_GAME_AUDIO", "LOW_TRANSCRIPT_CONFIDENCE",
}
_ALL_REASONS = _QUALITY_REASONS | {
    "FOLDER_NOT_SELECTED", "FOLDER_MISSING", "FOLDER_UNREADABLE", "FOLDER_STALE",
    "FOLDER_UNKNOWN", "FOLDER_NOT_CURRENT", "FOLDER_UNAVAILABLE",
    "SOURCE_FINALIZATION_MISMATCH", "SOURCE_FINALIZATION_NOT_BOUND",
    "CAPTURE_FORMAT_MISMATCH", "CAPTURE_FORMAT_NOT_BOUND",
    "TRACK_MISMATCH", "TRACK_NOT_BOUND", "SOURCE_ASSET_MISMATCH", "SOURCE_ASSET_NOT_BOUND",
    "PRIVATE_MEDIA_CUSTODY_MISMATCH", "PRIVATE_MEDIA_CUSTODY_NOT_BOUND",
    "TRANSCRIPT_MISMATCH", "TRANSCRIPT_NOT_BOUND",
    "TRANSCRIPT_PRIVATE_CUSTODY_MISMATCH", "TRANSCRIPT_PRIVATE_CUSTODY_NOT_BOUND",
    "VOICE_PROFILE_MISMATCH", "VOICE_PROFILE_NOT_BOUND", "LABEL_MISMATCH", "LABEL_NOT_BOUND",
    "TRAINING_ASSET_MISMATCH", "TRAINING_ASSET_NOT_BOUND",
    "TRAINING_PRIVATE_CUSTODY_MISMATCH", "TRAINING_PRIVATE_CUSTODY_NOT_BOUND",
    "NORMALIZATION_MISMATCH", "NORMALIZATION_NOT_BOUND", "SOURCE_LOCKED", "SOURCE_PARTIAL",
    "MEDIA_UNSUPPORTED", "SOURCE_NOT_STABLE", "MEDIA_INVALID", "MEDIA_UNKNOWN",
    "MIC_ISOLATED_REQUIRED", "TRANSCRIPT_SOURCE_ASSET_MISMATCH",
    "VOICE_PROFILE_DIGEST_MISMATCH", "CONSENT_BLOCKED", "CONSENT_NOT_CURRENT", "CONSENT_UNKNOWN",
    "RIGHTS_BLOCKED", "RIGHTS_NOT_CURRENT", "RIGHTS_UNKNOWN", "QUALITY_BLOCKED",
    "QUALITY_NOT_CURRENT", "QUALITY_UNKNOWN", "QUALITY_SUBJECT_MISMATCH",
    "PRIVATE_OR_SECRET_CONTENT", "PRIVACY_REVIEW_REQUIRED", "PRIVACY_NOT_CURRENT",
    "OWNER_EXCLUDED", "DUPLICATE", "OVERLAP", "FINGERPRINT_INDEX_MISMATCH",
    "FINGERPRINT_INDEX_NOT_BOUND", "NORMALIZATION_SUBJECT_MISMATCH",
    "TRAINING_ASSET_SOURCE_COLLISION", "TRAINING_ASSET_DUPLICATE", "MEDIA_NOT_CURRENT",
}


def _expect(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _id(value: Any, name: str, *, prefix: str) -> str:
    if isinstance(value, str) and (
        "\\" in value or value.startswith("/") or _DRIVE_PATH_RE.match(value)
        or "//" in value or any(part == ".." for part in value.split("/"))
    ):
        raise ValueError(f"{name} must be a logical identifier, not a host path")
    if not isinstance(value, str) or not _ID_RE.fullmatch(value) or not value.startswith(prefix):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _int(value: Any, name: str, *, minimum: int = 0, maximum: int = MAX_INTEGER) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is invalid")
    return value


def _bool(value: Any, name: str, *, exact: bool | None = None) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be boolean")
    if exact is not None and value is not exact:
        raise ValueError(f"{name} must remain {str(exact).lower()}")
    return value


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


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


def _reasons(value: Any, name: str, *, allowed: set[str] | None = None) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 64 or value != sorted(set(value)):
        raise ValueError(f"{name} must be a sorted unique bounded list")
    for reason in value:
        if not isinstance(reason, str) or not _REASON_RE.fullmatch(reason):
            raise ValueError(f"{name} contains an invalid reason")
        if reason not in (allowed or _ALL_REASONS):
            raise ValueError(f"{name} contains an unsupported reason")
    return tuple(value)


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


def _validate_synthetic_authority(value: Mapping[str, Any]) -> None:
    # Deliberately compare with a literal.  The public compatibility constant is
    # not an authority switch and monkeypatching it must never widen this unit.
    if value["authority_kind"] != "SYNTHETIC_CONTRACT_TEST":
        raise ValueError("Unit A accepts synthetic contract-test authority only")
    _bool(value["synthetic_input_only"], "synthetic_input_only", exact=True)
    _bool(value["owner_audio_used"], "owner_audio_used", exact=False)


def transcript_range_identity_sha256(
    *, source_asset_id: str, transcript_manifest_sha256: str,
    source_start_us: int, source_end_us: int,
) -> str:
    _id(source_asset_id, "source_asset_id", prefix="asset:")
    _sha(transcript_manifest_sha256, "transcript_manifest_sha256")
    start = _int(source_start_us, "source_start_us", maximum=MAX_SEGMENT_US)
    end = _int(source_end_us, "source_end_us", minimum=1, maximum=MAX_SEGMENT_US)
    if end <= start:
        raise ValueError("source range must be non-empty")
    return sha256_bytes(canonical_json_bytes({
        "source_asset_id": source_asset_id,
        "source_end_us": end,
        "source_start_us": start,
        "transcript_manifest_sha256": transcript_manifest_sha256,
    }))


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


def _version(value: Mapping[str, Any]) -> None:
    if value.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("contract_version is invalid")


def _validate_folder(value: Mapping[str, Any]) -> None:
    _expect(value, {
        "contract_version", "record_type", "authority_kind", "synthetic_input_only",
        "owner_audio_used", "folder_binding_id", "preference_revision",
        "currentness", "configured", "availability_state", "reason_codes",
        "source_path_body_present", "binding_sha256",
    }, "ObsFolderBinding")
    _version(value)
    _validate_synthetic_authority(value)
    _id(value["folder_binding_id"], "folder_binding_id", prefix="folder-binding:")
    _int(value["preference_revision"], "preference_revision", minimum=1)
    configured = _bool(value["configured"], "configured")
    current = _enum(FolderCurrentness, value["currentness"], "currentness")
    available = _enum(AvailabilityState, value["availability_state"], "availability_state")
    if current is FolderCurrentness.CURRENT and (not configured or available is not AvailabilityState.AVAILABLE):
        raise ValueError("CURRENT folder must be configured and available")
    if not configured and available is not AvailabilityState.UNAVAILABLE:
        raise ValueError("unconfigured folder must be unavailable")
    reasons = _reasons(value["reason_codes"], "reason_codes")
    expected_reasons: set[str] = set()
    if not configured:
        expected_reasons.add("FOLDER_NOT_SELECTED")
    if current is FolderCurrentness.STALE:
        expected_reasons.add("FOLDER_STALE")
    elif current is FolderCurrentness.UNKNOWN:
        expected_reasons.add("FOLDER_UNKNOWN")
    if available is AvailabilityState.UNAVAILABLE:
        expected_reasons.add("FOLDER_UNAVAILABLE")
    elif available is AvailabilityState.UNKNOWN:
        expected_reasons.add("FOLDER_UNKNOWN")
    if set(reasons) != expected_reasons:
        raise ValueError("folder reason_codes do not match folder state")
    _bool(value["source_path_body_present"], "source_path_body_present", exact=False)
    _verify_digest(value, "binding_sha256")


def _validate_observation(value: Mapping[str, Any]) -> None:
    _expect(value, {
        "contract_version", "record_type", "authority_kind", "synthetic_input_only",
        "owner_audio_used", "scan_operation_id", "recording_id",
        "source_identity_sha256", "finalization_state", "finalization_receipt_sha256",
        "capture_format_binding_state", "capture_format_receipt_sha256", "capture_format",
        "stability_state",
        "media_validation_state", "track_binding_state", "track_class",
        "track_index", "track_classification_receipt_sha256", "asset_binding_state",
        "source_asset_id", "source_asset_revision_ref", "source_asset_revision_sha256",
        "source_asset_checksum_sha256", "private_media_custody_state",
        "private_media_custody_receipt_sha256", "source_path_body_present",
        "observed_recording_sha256",
    }, "ObservedRecording")
    _version(value)
    _validate_synthetic_authority(value)
    _id(value["scan_operation_id"], "scan_operation_id", prefix="operation:")
    _id(value["recording_id"], "recording_id", prefix="recording:")
    _sha(value["source_identity_sha256"], "source_identity_sha256")
    finalization = _enum(ContractState, value["finalization_state"], "finalization_state")
    if finalization is ContractState.BOUND_VERIFIED:
        _sha(value["finalization_receipt_sha256"], "finalization_receipt_sha256")
    elif value["finalization_receipt_sha256"] is not None:
        raise ValueError("unbound finalization must not invent a receipt")
    capture_format = _enum(ContractState, value["capture_format_binding_state"], "capture_format_binding_state")
    if capture_format is ContractState.BOUND_VERIFIED:
        _sha(value["capture_format_receipt_sha256"], "capture_format_receipt_sha256")
        if value["capture_format"] != TRAINING_COPY_FORMAT:
            raise ValueError("verified capture format must be PCM_S24LE_48000_MONO")
    elif value["capture_format_receipt_sha256"] is not None or value["capture_format"] is not None:
        raise ValueError("unbound capture format must not invent format truth")
    _enum(StabilityState, value["stability_state"], "stability_state")
    _enum(FactState, value["media_validation_state"], "media_validation_state")
    track_state = _enum(ContractState, value["track_binding_state"], "track_binding_state")
    track_class = _enum(TrackClass, value["track_class"], "track_class")
    track_index = value["track_index"]
    track_receipt = value["track_classification_receipt_sha256"]
    if track_state is ContractState.BOUND_VERIFIED:
        _int(track_index, "track_index", minimum=1, maximum=64)
        _sha(track_receipt, "track_classification_receipt_sha256")
    elif track_index is not None or track_receipt is not None or track_class is not TrackClass.UNKNOWN:
        raise ValueError("unbound track classification must not invent track truth")
    asset_state = _enum(ContractState, value["asset_binding_state"], "asset_binding_state")
    asset_fields = (
        "source_asset_id", "source_asset_revision_ref", "source_asset_revision_sha256",
        "source_asset_checksum_sha256",
    )
    if asset_state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in asset_fields):
            raise ValueError("BOUND_VERIFIED source Asset is incomplete")
        _id(value["source_asset_id"], "source_asset_id", prefix="asset:")
        _id(value["source_asset_revision_ref"], "source_asset_revision_ref", prefix="asset:")
        _sha(value["source_asset_revision_sha256"], "source_asset_revision_sha256")
        _sha(value["source_asset_checksum_sha256"], "source_asset_checksum_sha256")
    elif any(value[field] is not None for field in asset_fields):
        raise ValueError("unbound source Asset must not invent Asset truth")
    custody = _enum(ContractState, value["private_media_custody_state"], "private_media_custody_state")
    if custody is ContractState.BOUND_VERIFIED:
        _sha(value["private_media_custody_receipt_sha256"], "private_media_custody_receipt_sha256")
    elif value["private_media_custody_receipt_sha256"] is not None:
        raise ValueError("unbound private-media custody must not invent a receipt")
    _bool(value["source_path_body_present"], "source_path_body_present", exact=False)
    _verify_digest(value, "observed_recording_sha256")


def _validate_candidate(value: Mapping[str, Any]) -> None:
    _expect(value, {
        "contract_version", "record_type", "authority_kind", "synthetic_input_only",
        "owner_audio_used", "scan_operation_id", "candidate_id",
        "recording_id", "observed_recording_sha256", "candidate_revision_ref",
        "candidate_revision_sha256", "source_start_us", "source_end_us",
        "transcript_binding_state", "transcript_source_asset_id",
        "transcript_manifest_sha256", "transcript_provider_id", "transcript_model_id",
        "transcript_language", "transcript_range_sha256",
        "transcript_private_custody_state", "transcript_private_custody_receipt_sha256",
        "voice_profile_binding_state",
        "voice_profile_revision_sha256", "consent_state", "consent_evaluation_sha256",
        "rights_state", "rights_evaluation_sha256", "quality_state",
        "quality_evaluation_sha256", "quality_subject_asset_checksum_sha256",
        "quality_subject_start_us", "quality_subject_end_us", "quality_reason_codes",
        "label_binding_state",
        "approved_label_binding_sha256", "privacy_review_state", "owner_decision",
        "training_asset_binding_state", "training_asset_id", "training_asset_revision_ref",
        "training_asset_revision_sha256", "training_asset_checksum_sha256",
        "training_copy_format", "training_sample_rate_hz", "training_channel_count",
        "training_bit_depth", "training_asset_sample_count", "training_private_custody_state",
        "training_private_custody_receipt_sha256", "normalization_binding_state",
        "normalization_receipt_sha256", "normalization_source_asset_checksum_sha256",
        "normalization_source_start_us", "normalization_source_end_us",
        "normalization_output_asset_id", "normalization_output_asset_revision_ref",
        "normalization_output_asset_revision_sha256",
        "normalization_output_asset_checksum_sha256", "normalization_output_sample_count",
        "audio_fingerprint_sha256",
        "audio_body_persisted", "transcript_text_persisted", "candidate_sha256",
    }, "SpeechRangeCandidate")
    _version(value)
    _validate_synthetic_authority(value)
    _id(value["scan_operation_id"], "scan_operation_id", prefix="operation:")
    _id(value["candidate_id"], "candidate_id", prefix="candidate:")
    _id(value["recording_id"], "recording_id", prefix="recording:")
    _id(value["candidate_revision_ref"], "candidate_revision_ref", prefix="candidate:")
    for field in ("observed_recording_sha256", "candidate_revision_sha256", "audio_fingerprint_sha256"):
        _sha(value[field], field)
    start = _int(value["source_start_us"], "source_start_us", maximum=MAX_SEGMENT_US)
    end = _int(value["source_end_us"], "source_end_us", minimum=1, maximum=MAX_SEGMENT_US)
    if end <= start:
        raise ValueError("source range must be non-empty")
    transcript_state = _enum(ContractState, value["transcript_binding_state"], "transcript_binding_state")
    transcript_fields = (
        "transcript_source_asset_id", "transcript_manifest_sha256", "transcript_provider_id",
        "transcript_model_id", "transcript_language", "transcript_range_sha256",
    )
    if transcript_state is ContractState.BOUND_VERIFIED:
        _id(value["transcript_source_asset_id"], "transcript_source_asset_id", prefix="asset:")
        _id(value["transcript_provider_id"], "transcript_provider_id", prefix="provider:")
        _id(value["transcript_model_id"], "transcript_model_id", prefix="model:")
        if not isinstance(value["transcript_language"], str) or not _LANGUAGE_RE.fullmatch(value["transcript_language"]):
            raise ValueError("transcript_language is invalid")
        for field in ("transcript_manifest_sha256", "transcript_range_sha256"):
            _sha(value[field], field)
        expected_range_sha256 = transcript_range_identity_sha256(
            source_asset_id=value["transcript_source_asset_id"],
            transcript_manifest_sha256=value["transcript_manifest_sha256"],
            source_start_us=start,
            source_end_us=end,
        )
        if value["transcript_range_sha256"] != expected_range_sha256:
            raise ValueError("transcript range binding mismatch")
    elif any(value[field] is not None for field in transcript_fields):
        raise ValueError("unbound Transcript must not invent Transcript truth")
    transcript_custody = _enum(ContractState, value["transcript_private_custody_state"], "transcript_private_custody_state")
    if transcript_custody is ContractState.BOUND_VERIFIED:
        _sha(value["transcript_private_custody_receipt_sha256"], "transcript_private_custody_receipt_sha256")
    elif value["transcript_private_custody_receipt_sha256"] is not None:
        raise ValueError("unbound Transcript custody must not invent a receipt")
    for state_field, digest_field in (
        ("voice_profile_binding_state", "voice_profile_revision_sha256"),
        ("label_binding_state", "approved_label_binding_sha256"),
    ):
        state = _enum(ContractState, value[state_field], state_field)
        if state is ContractState.BOUND_VERIFIED:
            _sha(value[digest_field], digest_field)
        elif value[digest_field] is not None:
            raise ValueError(f"unbound {state_field} must not invent a digest")
    for state_field, digest_field in (
        ("consent_state", "consent_evaluation_sha256"),
        ("rights_state", "rights_evaluation_sha256"),
        ("quality_state", "quality_evaluation_sha256"),
    ):
        state = _enum(FactState, value[state_field], state_field)
        if state in {FactState.PASS, FactState.FAIL}:
            _sha(value[digest_field], digest_field)
        elif value[digest_field] is not None:
            raise ValueError(f"non-current {state_field} must not invent a digest")
    _enum(FactState, value["privacy_review_state"], "privacy_review_state")
    _enum(OwnerDecision, value["owner_decision"], "owner_decision")
    quality_reasons = _reasons(value["quality_reason_codes"], "quality_reason_codes", allowed=_QUALITY_REASONS)
    if value["quality_state"] == FactState.PASS.value and value["quality_reason_codes"]:
        raise ValueError("quality PASS cannot carry failure reasons")
    if value["quality_state"] == FactState.FAIL.value and not quality_reasons:
        raise ValueError("quality FAIL must carry a closed failure reason")
    quality_subject_fields = (
        "quality_subject_asset_checksum_sha256", "quality_subject_start_us", "quality_subject_end_us",
    )
    if value["quality_state"] in {FactState.PASS.value, FactState.FAIL.value}:
        _sha(value["quality_subject_asset_checksum_sha256"], "quality_subject_asset_checksum_sha256")
        if _int(value["quality_subject_start_us"], "quality_subject_start_us", maximum=MAX_SEGMENT_US) != start:
            raise ValueError("quality subject start mismatch")
        if _int(value["quality_subject_end_us"], "quality_subject_end_us", minimum=1, maximum=MAX_SEGMENT_US) != end:
            raise ValueError("quality subject end mismatch")
    elif any(value[field] is not None for field in quality_subject_fields):
        raise ValueError("unknown quality fact must not invent a subject")
    training_state = _enum(ContractState, value["training_asset_binding_state"], "training_asset_binding_state")
    training_fields = (
        "training_asset_id", "training_asset_revision_ref", "training_asset_revision_sha256",
        "training_asset_checksum_sha256", "training_asset_sample_count",
    )
    if training_state is ContractState.BOUND_VERIFIED:
        _id(value["training_asset_id"], "training_asset_id", prefix="asset:")
        _id(value["training_asset_revision_ref"], "training_asset_revision_ref", prefix="asset:")
        _sha(value["training_asset_revision_sha256"], "training_asset_revision_sha256")
        _sha(value["training_asset_checksum_sha256"], "training_asset_checksum_sha256")
        training_samples = _int(value["training_asset_sample_count"], "training_asset_sample_count", minimum=1, maximum=MAX_SEGMENT_SAMPLES)
        max_source_samples = ((end - start) * SAMPLE_RATE_HZ + 999_999) // 1_000_000
        if training_samples > max_source_samples:
            raise ValueError("training Asset cannot contain more samples than its source range")
    elif any(value[field] is not None for field in training_fields):
        raise ValueError("unbound training Asset must not invent Asset truth")
    if value["training_copy_format"] != TRAINING_COPY_FORMAT:
        raise ValueError("training_copy_format is invalid")
    if _int(value["training_sample_rate_hz"], "training_sample_rate_hz", minimum=1) != SAMPLE_RATE_HZ:
        raise ValueError("training sample rate must be 48000")
    if _int(value["training_channel_count"], "training_channel_count", minimum=1) != 1:
        raise ValueError("training channel count must be mono")
    if _int(value["training_bit_depth"], "training_bit_depth", minimum=1) != 24:
        raise ValueError("training bit depth must be 24")
    training_custody = _enum(ContractState, value["training_private_custody_state"], "training_private_custody_state")
    if training_custody is ContractState.BOUND_VERIFIED:
        _sha(value["training_private_custody_receipt_sha256"], "training_private_custody_receipt_sha256")
    elif value["training_private_custody_receipt_sha256"] is not None:
        raise ValueError("unbound training custody must not invent a receipt")
    normalization = _enum(ContractState, value["normalization_binding_state"], "normalization_binding_state")
    normalization_fields = (
        "normalization_receipt_sha256", "normalization_source_asset_checksum_sha256",
        "normalization_source_start_us", "normalization_source_end_us",
        "normalization_output_asset_id", "normalization_output_asset_revision_ref",
        "normalization_output_asset_revision_sha256",
        "normalization_output_asset_checksum_sha256", "normalization_output_sample_count",
    )
    if normalization is ContractState.BOUND_VERIFIED:
        for field in (
            "normalization_receipt_sha256", "normalization_source_asset_checksum_sha256",
            "normalization_output_asset_revision_sha256",
            "normalization_output_asset_checksum_sha256",
        ):
            _sha(value[field], field)
        _id(value["normalization_output_asset_id"], "normalization_output_asset_id", prefix="asset:")
        _id(value["normalization_output_asset_revision_ref"], "normalization_output_asset_revision_ref", prefix="asset:")
        if value["normalization_source_start_us"] != start or value["normalization_source_end_us"] != end:
            raise ValueError("normalization source range mismatch")
        if (
            value["normalization_output_asset_id"] != value["training_asset_id"]
            or value["normalization_output_asset_revision_ref"] != value["training_asset_revision_ref"]
            or value["normalization_output_asset_revision_sha256"] != value["training_asset_revision_sha256"]
            or value["normalization_output_asset_checksum_sha256"] != value["training_asset_checksum_sha256"]
        ):
            raise ValueError("normalization output Asset mismatch")
        if value["normalization_output_sample_count"] != value["training_asset_sample_count"]:
            raise ValueError("normalization output sample count mismatch")
    elif any(value[field] is not None for field in normalization_fields):
        raise ValueError("unbound normalization must not invent sample-map truth")
    _bool(value["audio_body_persisted"], "audio_body_persisted", exact=False)
    _bool(value["transcript_text_persisted"], "transcript_text_persisted", exact=False)
    _verify_digest(value, "candidate_sha256")


def _validate_fingerprint_index(value: Mapping[str, Any]) -> None:
    _expect(value, {
        "contract_version", "record_type", "authority_kind", "synthetic_input_only",
        "owner_audio_used", "contract_state", "dataset_id", "dataset_head_sha256",
        "ordered_fingerprint_sha256s", "entry_count", "binding_sha256",
    }, "ExistingFingerprintIndexBinding")
    _version(value)
    _validate_synthetic_authority(value)
    state = _enum(ContractState, value["contract_state"], "contract_state")
    _id(value["dataset_id"], "dataset_id", prefix="dataset:")
    _sha(value["dataset_head_sha256"], "dataset_head_sha256", nullable=True)
    rows = value["ordered_fingerprint_sha256s"]
    if not isinstance(rows, list) or len(rows) > MAX_ITEMS or rows != sorted(set(rows)):
        raise ValueError("ordered_fingerprint_sha256s must be sorted, unique and bounded")
    for item in rows:
        _sha(item, "fingerprint_sha256")
    if state is not ContractState.BOUND_VERIFIED and rows:
        raise ValueError("unbound fingerprint index must not invent entries")
    if _int(value["entry_count"], "entry_count", maximum=MAX_ITEMS) != len(rows):
        raise ValueError("fingerprint entry_count mismatch")
    _verify_digest(value, "binding_sha256")


def _validate_proposal(value: Mapping[str, Any]) -> None:
    _expect(value, {
        "contract_version", "record_type", "authority_kind", "synthetic_input_only",
        "owner_audio_used", "proposal_id", "operation_id",
        "idempotency_key", "project_id", "dataset_id", "expected_dataset_head_sha256",
        "folder_binding_sha256", "voice_profile_revision_sha256", "policy_revision_sha256",
        "existing_fingerprint_index_sha256", "candidate_results", "proposal_reason_codes", "reason_counts",
        "accepted_unique_samples", "accepted_duration_ms", "coverage_state",
        "canonical_training_readiness", "owner_dataset_gate_required",
        "canonical_membership_issued", "training_input_snapshot_issued",
        "source_path_body_present", "audio_body_persisted", "transcript_text_persisted",
        "dataset_mutation_authorized", "training_authorized", "model_load_started",
        "provider_execution_started", "created_at", "proposal_sha256",
    }, "ObsFolderDatasetIntakeProposal")
    _version(value)
    _validate_synthetic_authority(value)
    _id(value["proposal_id"], "proposal_id", prefix="proposal:")
    _id(value["operation_id"], "operation_id", prefix="operation:")
    _id(value["idempotency_key"], "idempotency_key", prefix="idempotency:")
    _id(value["project_id"], "project_id", prefix="project:")
    _id(value["dataset_id"], "dataset_id", prefix="dataset:")
    _sha(value["expected_dataset_head_sha256"], "expected_dataset_head_sha256", nullable=True)
    for field in (
        "folder_binding_sha256", "voice_profile_revision_sha256", "policy_revision_sha256",
        "existing_fingerprint_index_sha256",
    ):
        _sha(value[field], field)
    rows = value["candidate_results"]
    if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
        raise ValueError("candidate_results must be bounded")
    ids: list[str] = []
    accepted = 0
    expected_counts: dict[str, int] = {}
    for row in rows:
        _expect(row, {"candidate_id", "candidate_sha256", "disposition", "reason_codes", "unique_samples"}, "CandidateResult")
        ids.append(_id(row["candidate_id"], "candidate_id", prefix="candidate:"))
        _sha(row["candidate_sha256"], "candidate_sha256")
        disposition = _enum(CandidateDisposition, row["disposition"], "disposition")
        reasons = _reasons(row["reason_codes"], "reason_codes")
        samples = _int(row["unique_samples"], "unique_samples")
        if disposition is CandidateDisposition.ACCEPTED:
            if reasons or samples < 1:
                raise ValueError("accepted candidate result is invalid")
            accepted += samples
        elif not reasons or samples != 0:
            raise ValueError("non-accepted candidate result is invalid")
        for reason in reasons:
            expected_counts[reason] = expected_counts.get(reason, 0) + 1
    if ids != sorted(set(ids)):
        raise ValueError("candidate_results must be sorted and unique")
    counts = value["reason_counts"]
    if not isinstance(counts, Mapping) or list(counts) != sorted(counts):
        raise ValueError("reason_counts must be a sorted object")
    for reason, count in counts.items():
        if not _REASON_RE.fullmatch(reason):
            raise ValueError("reason_counts contains an invalid reason")
        _int(count, f"reason_counts.{reason}", minimum=1)
    if dict(counts) != {key: expected_counts[key] for key in sorted(expected_counts)}:
        raise ValueError("reason_counts mismatch")
    proposal_reasons = _reasons(value["proposal_reason_codes"], "proposal_reason_codes")
    if _int(value["accepted_unique_samples"], "accepted_unique_samples") != accepted:
        raise ValueError("accepted_unique_samples mismatch")
    if _int(value["accepted_duration_ms"], "accepted_duration_ms") != accepted * 1000 // SAMPLE_RATE_HZ:
        raise ValueError("accepted_duration_ms mismatch")
    coverage = _enum(CoverageState, value["coverage_state"], "coverage_state")
    has_review = any(row["disposition"] == CandidateDisposition.REVIEW_REQUIRED.value for row in rows)
    expected_coverage = (
        CoverageState.REVIEW_BLOCKED if proposal_reasons or has_review
        else CoverageState.COVERAGE_LT_30 if accepted < MINIMUM_COVERAGE_SAMPLES
        else CoverageState.MINIMUM_COVERAGE_MET if accepted < TARGET_COVERAGE_SAMPLES
        else CoverageState.TARGET_COVERAGE_MET
    )
    if coverage is not expected_coverage:
        raise ValueError("coverage_state mismatch")
    if value["canonical_training_readiness"] != "NOT_CONFIRMED":
        raise ValueError("Unit A cannot claim canonical training readiness")
    _bool(value["owner_dataset_gate_required"], "owner_dataset_gate_required", exact=True)
    for field in (
        "canonical_membership_issued", "training_input_snapshot_issued",
        "source_path_body_present", "audio_body_persisted", "transcript_text_persisted",
        "dataset_mutation_authorized", "training_authorized", "model_load_started",
        "provider_execution_started",
    ):
        _bool(value[field], field, exact=False)
    _timestamp(value["created_at"], "created_at")
    _verify_digest(value, "proposal_sha256")


_VALIDATORS = {
    "ObsFolderBinding": _validate_folder,
    "ObservedRecording": _validate_observation,
    "SpeechRangeCandidate": _validate_candidate,
    "ExistingFingerprintIndexBinding": _validate_fingerprint_index,
    "ObsFolderDatasetIntakeProposal": _validate_proposal,
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if record_type not in _VALIDATORS or (expected_type is not None and record_type != expected_type):
        raise ValueError("record_type is invalid")
    result = _thaw(value)
    _VALIDATORS[record_type](result)
    return result


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(validate_record(self.data, expected_type=self.RECORD_TYPE)))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_Record":
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


class ObsFolderBinding(_Record): RECORD_TYPE = "ObsFolderBinding"
class ObservedRecording(_Record): RECORD_TYPE = "ObservedRecording"
class SpeechRangeCandidate(_Record): RECORD_TYPE = "SpeechRangeCandidate"
class ExistingFingerprintIndexBinding(_Record): RECORD_TYPE = "ExistingFingerprintIndexBinding"
class ObsFolderDatasetIntakeProposal(_Record): RECORD_TYPE = "ObsFolderDatasetIntakeProposal"


def compile_folder_binding(
    *, folder_binding_id: str, preference_revision: int,
    currentness: FolderCurrentness, configured: bool,
    availability_state: AvailabilityState, reason_codes: Sequence[str] = (),
) -> ObsFolderBinding:
    body = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "ObsFolderBinding",
        "authority_kind": "SYNTHETIC_CONTRACT_TEST",
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "folder_binding_id": folder_binding_id,
        "preference_revision": preference_revision,
        "currentness": currentness.value,
        "configured": configured,
        "availability_state": availability_state.value,
        "reason_codes": sorted(set(reason_codes)),
        "source_path_body_present": False,
    }
    return ObsFolderBinding(add_record_digest(body, "binding_sha256"))


def compile_fingerprint_index_binding(
    *, dataset_id: str, dataset_head_sha256: str | None,
    ordered_fingerprint_sha256s: Sequence[str],
    contract_state: ContractState = ContractState.BOUND_VERIFIED,
) -> ExistingFingerprintIndexBinding:
    rows = sorted(set(ordered_fingerprint_sha256s))
    body = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "ExistingFingerprintIndexBinding",
        "authority_kind": "SYNTHETIC_CONTRACT_TEST",
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "contract_state": contract_state.value,
        "dataset_id": dataset_id,
        "dataset_head_sha256": dataset_head_sha256,
        "ordered_fingerprint_sha256s": rows,
        "entry_count": len(rows),
    }
    return ExistingFingerprintIndexBinding(add_record_digest(body, "binding_sha256"))


def _contract_reason(prefix: str, state: str) -> tuple[str, bool]:
    parsed = ContractState(state)
    if parsed is ContractState.BOUND_VERIFIED:
        return "", False
    if parsed in {ContractState.MISMATCH, ContractState.STALE, ContractState.REVOKED}:
        return f"{prefix}_MISMATCH", True
    return f"{prefix}_NOT_BOUND", False


def _fact_reason(prefix: str, state: str) -> tuple[str, bool]:
    parsed = FactState(state)
    if parsed is FactState.PASS:
        return "", False
    if parsed is FactState.FAIL:
        return f"{prefix}_BLOCKED", True
    if parsed in {FactState.STALE, FactState.REVOKED}:
        return f"{prefix}_NOT_CURRENT", True
    return f"{prefix}_UNKNOWN", False


def compile_intake_proposal(
    *, proposal_id: str, operation_id: str, idempotency_key: str,
    project_id: str, dataset_id: str, expected_dataset_head_sha256: str | None,
    folder_binding: Mapping[str, Any], voice_profile_revision_sha256: str,
    policy_revision_sha256: str, observations: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]], fingerprint_index_binding: Mapping[str, Any],
    created_at: str,
) -> ObsFolderDatasetIntakeProposal:
    operation_id = _id(operation_id, "operation_id", prefix="operation:")
    folder = ObsFolderBinding.from_dict(folder_binding).to_dict()
    fingerprint_index = ExistingFingerprintIndexBinding.from_dict(fingerprint_index_binding).to_dict()
    _id(dataset_id, "dataset_id", prefix="dataset:")
    _sha(expected_dataset_head_sha256, "expected_dataset_head_sha256", nullable=True)
    if fingerprint_index["dataset_id"] != dataset_id or fingerprint_index["dataset_head_sha256"] != expected_dataset_head_sha256:
        raise ValueError("fingerprint index Dataset/head mismatch")
    observed = [ObservedRecording.from_dict(item).to_dict() for item in observations]
    candidate_rows = [SpeechRangeCandidate.from_dict(item).to_dict() for item in candidates]
    if len(observed) > MAX_ITEMS or len(candidate_rows) > MAX_ITEMS:
        raise ValueError("intake inputs exceed the bounded item limit")
    by_id: dict[str, dict[str, Any]] = {}
    for item in observed:
        if item["scan_operation_id"] != operation_id:
            raise ValueError("observation operation mismatch")
        if item["recording_id"] in by_id:
            raise ValueError("recording_id must be unique")
        by_id[item["recording_id"]] = item
    if len({row["candidate_id"] for row in candidate_rows}) != len(candidate_rows):
        raise ValueError("candidate_id must be unique")
    existing = list(fingerprint_index["ordered_fingerprint_sha256s"])
    global_reasons: list[str] = []
    global_hard = False
    if folder["currentness"] != FolderCurrentness.CURRENT.value:
        global_reasons.append("FOLDER_NOT_CURRENT")
        global_hard = folder["currentness"] == FolderCurrentness.STALE.value
    if not folder["configured"] or folder["availability_state"] != AvailabilityState.AVAILABLE.value:
        global_reasons.append("FOLDER_UNAVAILABLE")
        global_hard = global_hard or folder["availability_state"] == AvailabilityState.UNAVAILABLE.value
    reason, fingerprint_index_hard = _contract_reason("FINGERPRINT_INDEX", fingerprint_index["contract_state"])
    global_hard = global_hard or fingerprint_index_hard
    if reason:
        global_reasons.append(reason)
    ordered: list[tuple[tuple[str, int, int, str], dict[str, Any], dict[str, Any]]] = []
    for row in candidate_rows:
        if row["scan_operation_id"] != operation_id:
            raise ValueError("candidate operation mismatch")
        observation = by_id.get(row["recording_id"])
        if observation is None:
            raise ValueError("candidate references an unknown recording")
        if row["observed_recording_sha256"] != observation["observed_recording_sha256"]:
            raise ValueError("candidate observation binding mismatch")
        checksum = observation["source_asset_checksum_sha256"] or "sha256:" + "f" * 64
        ordered.append(((checksum, row["source_start_us"], row["source_end_us"], row["candidate_id"]), row, observation))
    ordered.sort(key=lambda item: item[0])

    seen = set(existing)
    accepted_ranges: dict[str, list[tuple[int, int]]] = {}
    accepted_training_asset_ids: set[str] = set()
    accepted_training_asset_revisions: set[str] = set()
    accepted_training_asset_revision_sha256s: set[str] = set()
    accepted_training_asset_checksums: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    accepted_samples = 0
    for _sort, row, observation in ordered:
        reasons = list(global_reasons)
        hard = global_hard
        for prefix, state in (
            ("SOURCE_FINALIZATION", observation["finalization_state"]),
            ("CAPTURE_FORMAT", observation["capture_format_binding_state"]),
            ("TRACK", observation["track_binding_state"]),
            ("SOURCE_ASSET", observation["asset_binding_state"]),
            ("PRIVATE_MEDIA_CUSTODY", observation["private_media_custody_state"]),
            ("TRANSCRIPT", row["transcript_binding_state"]),
            ("TRANSCRIPT_PRIVATE_CUSTODY", row["transcript_private_custody_state"]),
            ("VOICE_PROFILE", row["voice_profile_binding_state"]),
            ("LABEL", row["label_binding_state"]),
            ("TRAINING_ASSET", row["training_asset_binding_state"]),
            ("TRAINING_PRIVATE_CUSTODY", row["training_private_custody_state"]),
            ("NORMALIZATION", row["normalization_binding_state"]),
        ):
            reason, terminal = _contract_reason(prefix, state)
            if reason:
                reasons.append(reason)
                hard = hard or terminal
        stability = StabilityState(observation["stability_state"])
        if stability is not StabilityState.STABLE:
            reasons.append({
                StabilityState.LOCKED: "SOURCE_LOCKED",
                StabilityState.PARTIAL_OR_TEMP: "SOURCE_PARTIAL",
                StabilityState.UNSUPPORTED: "MEDIA_UNSUPPORTED",
            }.get(stability, "SOURCE_NOT_STABLE"))
            hard = hard or stability is StabilityState.UNSUPPORTED
        media = FactState(observation["media_validation_state"])
        if media is FactState.FAIL:
            reasons.append("MEDIA_INVALID")
            hard = True
        elif media in {FactState.STALE, FactState.REVOKED}:
            reasons.append("MEDIA_NOT_CURRENT")
            hard = True
        elif media is not FactState.PASS:
            reasons.append("MEDIA_UNKNOWN")
        if observation["track_class"] != TrackClass.MIC_ISOLATED.value:
            reasons.append("MIC_ISOLATED_REQUIRED")
            hard = hard or observation["track_class"] != TrackClass.UNKNOWN.value
        if row["transcript_binding_state"] == ContractState.BOUND_VERIFIED.value:
            if row["transcript_source_asset_id"] != observation["source_asset_id"]:
                reasons.append("TRANSCRIPT_SOURCE_ASSET_MISMATCH")
                hard = True
        if row["voice_profile_binding_state"] == ContractState.BOUND_VERIFIED.value:
            if row["voice_profile_revision_sha256"] != voice_profile_revision_sha256:
                reasons.append("VOICE_PROFILE_DIGEST_MISMATCH")
                hard = True
        if row["quality_state"] in {FactState.PASS.value, FactState.FAIL.value}:
            if row["quality_subject_asset_checksum_sha256"] != observation["source_asset_checksum_sha256"]:
                reasons.append("QUALITY_SUBJECT_MISMATCH")
                hard = True
        if row["normalization_binding_state"] == ContractState.BOUND_VERIFIED.value:
            if row["normalization_source_asset_checksum_sha256"] != observation["source_asset_checksum_sha256"]:
                reasons.append("NORMALIZATION_SUBJECT_MISMATCH")
                hard = True
        if row["training_asset_binding_state"] == ContractState.BOUND_VERIFIED.value:
            if (
                row["training_asset_id"] == observation["source_asset_id"]
                or row["training_asset_revision_ref"] == observation["source_asset_revision_ref"]
                or row["training_asset_revision_sha256"] == observation["source_asset_revision_sha256"]
                or row["training_asset_checksum_sha256"] == observation["source_asset_checksum_sha256"]
            ):
                reasons.append("TRAINING_ASSET_SOURCE_COLLISION")
                hard = True
        for prefix, state in (
            ("CONSENT", row["consent_state"]),
            ("RIGHTS", row["rights_state"]),
            ("QUALITY", row["quality_state"]),
        ):
            reason, terminal = _fact_reason(prefix, state)
            if reason:
                reasons.append(reason)
                hard = hard or terminal
        if row["quality_state"] == FactState.FAIL.value:
            reasons.extend(row["quality_reason_codes"])
        privacy = FactState(row["privacy_review_state"])
        if privacy is FactState.FAIL:
            reasons.append("PRIVATE_OR_SECRET_CONTENT")
            hard = True
        elif privacy in {FactState.STALE, FactState.REVOKED}:
            reasons.append("PRIVACY_NOT_CURRENT")
            hard = True
        elif privacy is not FactState.PASS:
            reasons.append("PRIVACY_REVIEW_REQUIRED")
        if row["owner_decision"] == OwnerDecision.EXCLUDE.value:
            reasons.append("OWNER_EXCLUDED")
            hard = True
        fingerprint = row["audio_fingerprint_sha256"]
        if fingerprint in seen:
            reasons.append("DUPLICATE")
            hard = True
        reasons = sorted(set(reasons))
        if not reasons:
            source_key = observation["source_asset_checksum_sha256"]
            assert source_key is not None
            ranges = accepted_ranges.setdefault(source_key, [])
            if any(row["source_start_us"] < end and start < row["source_end_us"] for start, end in ranges):
                reasons = ["OVERLAP"]
                hard = True
        if reasons:
            disposition = CandidateDisposition.EXCLUDED if hard else CandidateDisposition.REVIEW_REQUIRED
            samples = 0
        else:
            if (
                row["training_asset_id"] in accepted_training_asset_ids
                or row["training_asset_revision_ref"] in accepted_training_asset_revisions
                or row["training_asset_revision_sha256"] in accepted_training_asset_revision_sha256s
                or row["training_asset_checksum_sha256"] in accepted_training_asset_checksums
            ):
                reasons = ["TRAINING_ASSET_DUPLICATE"]
                disposition = CandidateDisposition.EXCLUDED
                samples = 0
            else:
                disposition = CandidateDisposition.ACCEPTED
                samples = row["training_asset_sample_count"]
                assert isinstance(samples, int)
                accepted_samples += samples
                accepted_ranges[observation["source_asset_checksum_sha256"]].append((row["source_start_us"], row["source_end_us"]))
                accepted_training_asset_ids.add(row["training_asset_id"])
                accepted_training_asset_revisions.add(row["training_asset_revision_ref"])
                accepted_training_asset_revision_sha256s.add(row["training_asset_revision_sha256"])
                accepted_training_asset_checksums.add(row["training_asset_checksum_sha256"])
                seen.add(fingerprint)
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
        results[row["candidate_id"]] = {
            "candidate_id": row["candidate_id"],
            "candidate_sha256": row["candidate_sha256"],
            "disposition": disposition.value,
            "reason_codes": reasons,
            "unique_samples": samples,
        }

    candidate_results = [results[key] for key in sorted(results)]
    if global_reasons or any(row["disposition"] == CandidateDisposition.REVIEW_REQUIRED.value for row in candidate_results):
        coverage = CoverageState.REVIEW_BLOCKED
    elif accepted_samples < MINIMUM_COVERAGE_SAMPLES:
        coverage = CoverageState.COVERAGE_LT_30
    elif accepted_samples < TARGET_COVERAGE_SAMPLES:
        coverage = CoverageState.MINIMUM_COVERAGE_MET
    else:
        coverage = CoverageState.TARGET_COVERAGE_MET
    body = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "ObsFolderDatasetIntakeProposal",
        "authority_kind": "SYNTHETIC_CONTRACT_TEST",
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "proposal_id": proposal_id,
        "operation_id": operation_id,
        "idempotency_key": idempotency_key,
        "project_id": project_id,
        "dataset_id": dataset_id,
        "expected_dataset_head_sha256": expected_dataset_head_sha256,
        "folder_binding_sha256": folder["binding_sha256"],
        "voice_profile_revision_sha256": voice_profile_revision_sha256,
        "policy_revision_sha256": policy_revision_sha256,
        "existing_fingerprint_index_sha256": fingerprint_index["binding_sha256"],
        "candidate_results": candidate_results,
        "proposal_reason_codes": sorted(set(global_reasons)),
        "reason_counts": {key: counts[key] for key in sorted(counts)},
        "accepted_unique_samples": accepted_samples,
        "accepted_duration_ms": accepted_samples * 1000 // SAMPLE_RATE_HZ,
        "coverage_state": coverage.value,
        "canonical_training_readiness": "NOT_CONFIRMED",
        "owner_dataset_gate_required": True,
        "canonical_membership_issued": False,
        "training_input_snapshot_issued": False,
        "source_path_body_present": False,
        "audio_body_persisted": False,
        "transcript_text_persisted": False,
        "dataset_mutation_authorized": False,
        "training_authorized": False,
        "model_load_started": False,
        "provider_execution_started": False,
        "created_at": created_at,
    }
    return ObsFolderDatasetIntakeProposal(add_record_digest(body, "proposal_sha256"))


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    record = validate_record(value)
    if record["record_type"] == "ObsFolderBinding":
        return {
            "record_type": record["record_type"],
            "synthetic_input_only": True,
            "owner_audio_used": False,
            "configured": record["configured"],
            "currentness": record["currentness"],
            "availability_state": record["availability_state"],
            "reason_codes": list(record["reason_codes"]),
            "source_path_body_present": False,
        }
    if record["record_type"] == "ObsFolderDatasetIntakeProposal":
        counts = {state.value: 0 for state in CandidateDisposition}
        for row in record["candidate_results"]:
            counts[row["disposition"]] += 1
        return {
            "record_type": record["record_type"],
            "synthetic_input_only": True,
            "owner_audio_used": False,
            "candidate_counts": counts,
            "proposal_reason_codes": list(record["proposal_reason_codes"]),
            "reason_counts": dict(record["reason_counts"]),
            "accepted_duration_ms": record["accepted_duration_ms"],
            "coverage_state": record["coverage_state"],
            "canonical_training_readiness": "NOT_CONFIRMED",
            "canonical_membership_issued": False,
            "training_input_snapshot_issued": False,
            "owner_dataset_gate_required": True,
            "dataset_mutation_authorized": False,
            "training_authorized": False,
            "model_load_started": False,
            "provider_execution_started": False,
            "source_path_body_present": False,
        }
    return {
        "record_type": record["record_type"],
        "synthetic_input_only": True,
        "owner_audio_used": False,
        "body_free": True,
        "source_path_body_present": False,
    }


def assert_no_effect_surface() -> None:
    module = inspect.getmodule(assert_no_effect_surface)
    forbidden = {"pathlib", "os", "subprocess", "socket", "requests", "urllib", "torch", "soundfile", "wave"}
    if module is None or forbidden.intersection(module.__dict__):
        raise AssertionError("effect-capable import detected")
