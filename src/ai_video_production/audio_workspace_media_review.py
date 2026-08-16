"""TASK-041 body-free audio review, audition and DAW handoff contracts.

This pure module validates immutable metadata and classifies review readiness.
It never reads audio, renders a waveform, launches a player/DAW, strips media,
registers an Asset, mutates a placement plan, or grants execution authority.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task041.audio-workspace-media-review.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_MAX_OPERATIONS = 8
_MAX_REASONS = 64


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class RightsState(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class CapabilityState(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    PROBE_REQUIRED = "PROBE_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class MediaKind(str, Enum):
    AUDIO_ASSET = "AUDIO_ASSET"
    VIDEO_WITH_EMBEDDED_AUDIO = "VIDEO_WITH_EMBEDDED_AUDIO"
    AUDIO_WORKSPACE_CANDIDATE = "AUDIO_WORKSPACE_CANDIDATE"
    DAW_ROUND_TRIP_CANDIDATE = "DAW_ROUND_TRIP_CANDIDATE"


class ReviewOperation(str, Enum):
    AUDITION = "AUDITION"
    WAVEFORM_VIEW = "WAVEFORM_VIEW"
    STRIP_EMBEDDED_AUDIO = "STRIP_EMBEDDED_AUDIO"
    RETAIN_AUDIO_ALTERNATE = "RETAIN_AUDIO_ALTERNATE"
    DAW_HANDOFF = "DAW_HANDOFF"


class ExternalReviewState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED_SAFE = "CANCELLED_SAFE"
    UNKNOWN = "UNKNOWN"


class AudioReviewDecisionKind(str, Enum):
    ACCEPT_AUDIO = "ACCEPT_AUDIO"
    REJECT_AUDIO = "REJECT_AUDIO"
    RETAIN_ALTERNATE = "RETAIN_ALTERNATE"
    STRIP_AUDIO = "STRIP_AUDIO"
    RETEST = "RETEST"


class VisualDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DerivationKind(str, Enum):
    AUDIO_STRIPPED_VIDEO = "AUDIO_STRIPPED_VIDEO"
    AUDIO_ONLY_ALTERNATE = "AUDIO_ONLY_ALTERNATE"


class DawHandoffState(str, Enum):
    PROPOSED = "PROPOSED"
    EXTERNAL_PENDING = "EXTERNAL_PENDING"
    RETURN_RECEIVED = "RETURN_RECEIVED"
    UNKNOWN = "UNKNOWN"


def _id(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value)
        or ".." in value.split("/")
        or any(term in folded for term in ("credential", "password", "secret", "license-key", "serial-number"))
    ):
        raise ValueError(f"{name} violates the body-free/private boundary")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _time(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be UTC RFC3339") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC RFC3339")
    return value


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside its cap")
    return value


def _keys(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _revision(value: Mapping[str, Any], name: str) -> None:
    revision = _integer(value["revision"], f"{name}.revision", 1, 2_147_483_647)
    parent = _digest(value["parent_record_sha256"], "parent_record_sha256", nullable=True)
    if (revision == 1) != (parent is None):
        raise ValueError(f"{name} parent/revision mismatch")


def _ordered_operations(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("requested_operations must be an ordered array")
    result = tuple(value)
    if not result or len(result) > _MAX_OPERATIONS or len(result) != len(set(result)):
        raise ValueError("requested_operations must be unique and bounded")
    if result != tuple(sorted(result)):
        raise ValueError("requested_operations must use canonical sorted order")
    for item in result:
        _enum(ReviewOperation, item, "requested_operations")
    return result


def _reasons(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("reason_codes must be an ordered array")
    result = tuple(value)
    if len(result) > _MAX_REASONS or len(result) != len(set(result)):
        raise ValueError("reason_codes must be unique and bounded")
    if result != tuple(sorted(result)):
        raise ValueError("reason_codes must use canonical sorted order")
    if any(not isinstance(item, str) or not _REASON_RE.fullmatch(item) for item in result):
        raise ValueError("reason_codes contains an invalid reason")
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _hashed(body: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(body))
    result["record_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _check_hash(value: Mapping[str, Any]) -> None:
    supplied = _digest(value["record_sha256"], "record_sha256")
    body = {key: copy.deepcopy(item) for key, item in value.items() if key != "record_sha256"}
    if supplied != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("record_sha256 mismatch")


def _policy(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "policy_id", "revision", "parent_record_sha256",
        "required_sample_rate_hz", "max_review_duration_samples", "max_observation_age_seconds",
        "official_policy_ref", "official_policy_sha256", "effective_at", "expires_at",
        "audio_read_started", "media_mutation_started", "record_sha256",
    }
    _keys(value, fields, "AudioMediaReviewPolicyRevision")
    _id(value["policy_id"], "policy_id")
    _revision(value, "policy")
    if value["required_sample_rate_hz"] != 48_000:
        raise ValueError("R0 review sample rate must be 48000 Hz")
    _integer(value["max_review_duration_samples"], "max_review_duration_samples", 1, 48_000 * 60 * 60 * 4)
    _integer(value["max_observation_age_seconds"], "max_observation_age_seconds", 1, 86_400)
    _id(value["official_policy_ref"], "official_policy_ref")
    _digest(value["official_policy_sha256"], "official_policy_sha256")
    effective = _time(value["effective_at"], "effective_at")
    expires = _time(value["expires_at"], "expires_at", nullable=True)
    if expires is not None and _dt(expires) <= _dt(effective):
        raise ValueError("expires_at must follow effective_at")
    if value["audio_read_started"] is not False or value["media_mutation_started"] is not False:
        raise ValueError("review policy cannot start effects")


def _source(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "source_id", "media_kind", "contract_state", "canonical_ref",
        "canonical_sha256", "canonical_revision", "candidate_id", "asset_id", "rights_state",
        "sample_rate_hz", "channel_count", "duration_samples", "observed_at", "body_included",
        "absolute_path_included", "record_sha256",
    }
    _keys(value, fields, "AudioMediaSourceBinding")
    _id(value["source_id"], "source_id")
    _enum(MediaKind, value["media_kind"], "media_kind")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    rights = _enum(RightsState, value["rights_state"], "rights_state")
    if value["body_included"] is not False or value["absolute_path_included"] is not False:
        raise ValueError("source binding must remain body/path free")
    nullable = (
        "canonical_ref", "canonical_sha256", "canonical_revision", "candidate_id", "asset_id",
        "sample_rate_hz", "channel_count", "duration_samples", "observed_at",
    )
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable) or rights is not RightsState.UNKNOWN:
            raise ValueError("unresolved source invents canonical truth")
        return
    for field in ("canonical_ref", "candidate_id", "asset_id"):
        _id(value[field], field, nullable=True)
    _digest(value["canonical_sha256"], "canonical_sha256", nullable=True)
    for field, maximum in (("canonical_revision", 2_147_483_647), ("sample_rate_hz", 768_000), ("channel_count", 64), ("duration_samples", 48_000 * 60 * 60 * 24)):
        if value[field] is not None:
            _integer(value[field], field, 1, maximum)
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED source is incomplete")


def _capability(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "capability_id", "contract_state", "player_state", "waveform_state",
        "decode_state", "sample_accurate_range_state", "capability_profile_ref",
        "capability_profile_sha256", "app_identity_sha256", "observed_at", "body_included",
        "absolute_path_included", "record_sha256",
    }
    _keys(value, fields, "PlaybackWaveformCapabilityBinding")
    _id(value["capability_id"], "capability_id")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    for field in ("player_state", "waveform_state", "decode_state", "sample_accurate_range_state"):
        _enum(CapabilityState, value[field], field)
    if value["body_included"] is not False or value["absolute_path_included"] is not False:
        raise ValueError("capability binding must remain body/path free")
    nullable = ("capability_profile_ref", "capability_profile_sha256", "app_identity_sha256", "observed_at")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved capability invents canonical fields")
        if any(value[field] != CapabilityState.UNKNOWN.value for field in ("player_state", "waveform_state", "decode_state", "sample_accurate_range_state")):
            raise ValueError("unresolved capability states must remain UNKNOWN")
        return
    _id(value["capability_profile_ref"], "capability_profile_ref", nullable=True)
    _digest(value["capability_profile_sha256"], "capability_profile_sha256", nullable=True)
    _digest(value["app_identity_sha256"], "app_identity_sha256", nullable=True)
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED capability is incomplete")


def _intent(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "intent_id", "revision", "parent_record_sha256", "project_id",
        "policy_sha256", "source_binding_sha256", "capability_binding_sha256",
        "audio_workspace_snapshot_sha256", "requested_operations", "range_start_sample",
        "range_end_sample", "requested_at", "body_included", "absolute_path_included",
        "playback_started", "waveform_render_started", "media_mutation_started", "record_sha256",
    }
    _keys(value, fields, "AudioMediaReviewIntent")
    _id(value["intent_id"], "intent_id")
    _revision(value, "intent")
    _id(value["project_id"], "project_id")
    for field in ("policy_sha256", "source_binding_sha256", "capability_binding_sha256", "audio_workspace_snapshot_sha256"):
        _digest(value[field], field)
    _ordered_operations(value["requested_operations"])
    start = _integer(value["range_start_sample"], "range_start_sample", 0, 48_000 * 60 * 60 * 24)
    end = _integer(value["range_end_sample"], "range_end_sample", 1, 48_000 * 60 * 60 * 24)
    if end <= start:
        raise ValueError("review range must be non-empty half-open samples")
    _time(value["requested_at"], "requested_at")
    effect_flags = ("body_included", "absolute_path_included", "playback_started", "waveform_render_started", "media_mutation_started")
    if any(value[field] is not False for field in effect_flags):
        raise ValueError("review intent must remain body/path free and unexecuted")


def _external_review(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "receipt_ref", "receipt_sha256", "intent_sha256",
        "source_binding_sha256", "capability_binding_sha256", "range_start_sample",
        "range_end_sample", "external_state", "audition_completed", "waveform_available",
        "observed_at", "canonical_persistence_verified", "effect_started_by_module", "record_sha256",
    }
    _keys(value, fields, "ExternalAudioReviewReceiptBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if value["effect_started_by_module"] is not False:
        raise ValueError("pure TASK-041 module cannot play or analyze audio")
    nullable = fields - {"record_type", "contract_state", "effect_started_by_module", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved external receipt invents fields")
        return
    for field in ("receipt_ref",):
        _id(value[field], field, nullable=True)
    for field in ("receipt_sha256", "intent_sha256", "source_binding_sha256", "capability_binding_sha256"):
        _digest(value[field], field, nullable=True)
    for field in ("range_start_sample", "range_end_sample"):
        if value[field] is not None:
            _integer(value[field], field, 0 if field.endswith("start_sample") else 1, 48_000 * 60 * 60 * 24)
    if value["range_start_sample"] is not None and value["range_end_sample"] is not None and value["range_end_sample"] <= value["range_start_sample"]:
        raise ValueError("external review range must be non-empty")
    if value["external_state"] is not None:
        _enum(ExternalReviewState, value["external_state"], "external_state")
    if value["audition_completed"] not in {True, False, None} or value["waveform_available"] not in {True, False, None}:
        raise ValueError("external observation flags must be boolean or null")
    _time(value["observed_at"], "observed_at", nullable=True)
    if value["canonical_persistence_verified"] not in {True, False, None}:
        raise ValueError("canonical_persistence_verified must be boolean or null")
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in nullable):
            raise ValueError("BOUND_VERIFIED external review receipt is incomplete")
        if value["external_state"] == ExternalReviewState.COMPLETED.value and value["canonical_persistence_verified"] is not True:
            raise ValueError("completed external review requires canonical persistence")


def _derived_proposal(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "proposal_id", "revision", "parent_record_sha256", "source_binding_sha256",
        "review_intent_sha256", "derivation_kind", "proposed_asset_identity", "lineage_sha256",
        "source_bytes_preserved", "derived_bytes_present", "asset_registration_started",
        "media_mutation_started", "record_sha256",
    }
    _keys(value, fields, "DerivedAudioAssetProposal")
    _id(value["proposal_id"], "proposal_id")
    _revision(value, "derived proposal")
    _digest(value["source_binding_sha256"], "source_binding_sha256")
    _digest(value["review_intent_sha256"], "review_intent_sha256")
    _enum(DerivationKind, value["derivation_kind"], "derivation_kind")
    _id(value["proposed_asset_identity"], "proposed_asset_identity")
    _digest(value["lineage_sha256"], "lineage_sha256")
    if value["source_bytes_preserved"] is not True:
        raise ValueError("derived proposal must preserve source bytes")
    if any(value[field] is not False for field in ("derived_bytes_present", "asset_registration_started", "media_mutation_started")):
        raise ValueError("proposal cannot claim derived bytes or effects")


def _decision(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "decision_id", "revision", "parent_record_sha256", "intent_sha256",
        "source_binding_sha256", "external_review_receipt_sha256", "audio_decision",
        "visual_decision", "derived_proposal_sha256", "reviewer_kind", "decided_at",
        "evidence_ref", "evidence_sha256", "reason_codes", "asset_mutation_started",
        "placement_mutation_started", "record_sha256",
    }
    _keys(value, fields, "AudioMediaReviewDecision")
    _id(value["decision_id"], "decision_id")
    _revision(value, "review decision")
    for field in ("intent_sha256", "source_binding_sha256"):
        _digest(value[field], field)
    _digest(value["external_review_receipt_sha256"], "external_review_receipt_sha256", nullable=True)
    audio = _enum(AudioReviewDecisionKind, value["audio_decision"], "audio_decision")
    _enum(VisualDecision, value["visual_decision"], "visual_decision")
    _digest(value["derived_proposal_sha256"], "derived_proposal_sha256", nullable=True)
    if value["reviewer_kind"] != "OWNER_HUMAN":
        raise ValueError("reviewer_kind must be OWNER_HUMAN")
    _time(value["decided_at"], "decided_at")
    _id(value["evidence_ref"], "evidence_ref")
    _digest(value["evidence_sha256"], "evidence_sha256")
    _reasons(value["reason_codes"])
    if audio in {AudioReviewDecisionKind.STRIP_AUDIO, AudioReviewDecisionKind.RETAIN_ALTERNATE}:
        if value["derived_proposal_sha256"] is None:
            raise ValueError("derived review decision requires an exact proposal")
    elif value["derived_proposal_sha256"] is not None:
        raise ValueError("non-derived review decision cannot attach a derived proposal")
    if any(value[field] is not False for field in ("asset_mutation_started", "placement_mutation_started")):
        raise ValueError("review decision cannot mutate Asset or placement")


def _daw_handoff(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "handoff_ref", "handoff_sha256",
        "review_decision_sha256", "task035_manifest_sha256", "returned_candidate_binding_sha256",
        "handoff_state", "observed_at", "reaper_launch_started", "audio_render_started",
        "asset_promotion_started", "record_sha256",
    }
    _keys(value, fields, "DawRoundTripStatusBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if any(value[field] is not False for field in ("reaper_launch_started", "audio_render_started", "asset_promotion_started")):
        raise ValueError("TASK-041 cannot start DAW or Asset effects")
    nullable = (
        "handoff_ref", "handoff_sha256", "review_decision_sha256", "task035_manifest_sha256",
        "returned_candidate_binding_sha256", "handoff_state", "observed_at",
    )
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved DAW handoff invents fields")
        return
    _id(value["handoff_ref"], "handoff_ref", nullable=True)
    for field in ("handoff_sha256", "review_decision_sha256", "task035_manifest_sha256", "returned_candidate_binding_sha256"):
        _digest(value[field], field, nullable=True)
    if value["handoff_state"] is not None:
        handoff_state = _enum(DawHandoffState, value["handoff_state"], "handoff_state")
        if handoff_state is DawHandoffState.RETURN_RECEIVED and value["returned_candidate_binding_sha256"] is None:
            raise ValueError("RETURN_RECEIVED requires returned candidate binding")
        if handoff_state is not DawHandoffState.RETURN_RECEIVED and value["returned_candidate_binding_sha256"] is not None:
            raise ValueError("returned candidate only belongs to RETURN_RECEIVED")
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable if field != "returned_candidate_binding_sha256"):
        raise ValueError("BOUND_VERIFIED DAW handoff is incomplete")


_VALIDATORS = {
    "AudioMediaReviewPolicyRevision": _policy,
    "AudioMediaSourceBinding": _source,
    "PlaybackWaveformCapabilityBinding": _capability,
    "AudioMediaReviewIntent": _intent,
    "ExternalAudioReviewReceiptBinding": _external_review,
    "DerivedAudioAssetProposal": _derived_proposal,
    "AudioMediaReviewDecision": _decision,
    "DawRoundTripStatusBinding": _daw_handoff,
}


@dataclass(frozen=True, slots=True)
class _Record:
    _data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    @classmethod
    def create(cls, **fields: Any) -> "_Record":
        body = {"record_type": cls.RECORD_TYPE, **copy.deepcopy(fields)}
        return validate_record(_hashed(body), expected_type=cls.RECORD_TYPE)

    @property
    def record_sha256(self) -> str:
        return self._data["record_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


class AudioMediaReviewPolicyRevision(_Record): RECORD_TYPE = "AudioMediaReviewPolicyRevision"
class AudioMediaSourceBinding(_Record): RECORD_TYPE = "AudioMediaSourceBinding"
class PlaybackWaveformCapabilityBinding(_Record): RECORD_TYPE = "PlaybackWaveformCapabilityBinding"
class AudioMediaReviewIntent(_Record): RECORD_TYPE = "AudioMediaReviewIntent"
class ExternalAudioReviewReceiptBinding(_Record): RECORD_TYPE = "ExternalAudioReviewReceiptBinding"
class DerivedAudioAssetProposal(_Record): RECORD_TYPE = "DerivedAudioAssetProposal"
class AudioMediaReviewDecision(_Record): RECORD_TYPE = "AudioMediaReviewDecision"
class DawRoundTripStatusBinding(_Record): RECORD_TYPE = "DawRoundTripStatusBinding"


_CLASSES = {
    cls.RECORD_TYPE: cls for cls in (
        AudioMediaReviewPolicyRevision, AudioMediaSourceBinding,
        PlaybackWaveformCapabilityBinding, AudioMediaReviewIntent,
        ExternalAudioReviewReceiptBinding, DerivedAudioAssetProposal,
        AudioMediaReviewDecision, DawRoundTripStatusBinding,
    )
}


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> _Record:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    record_type = value.get("record_type")
    if record_type not in _VALIDATORS or (expected_type is not None and record_type != expected_type):
        raise ValueError("record_type is unknown or mismatched")
    _VALIDATORS[record_type](value)
    _check_hash(value)
    return _CLASSES[record_type](_freeze(copy.deepcopy(dict(value))))


def classify_review_admission(
    *, policy: AudioMediaReviewPolicyRevision, source: AudioMediaSourceBinding,
    capability: PlaybackWaveformCapabilityBinding, intent: AudioMediaReviewIntent,
    evaluated_at: str,
) -> dict[str, Any]:
    """Classify metadata readiness; never starts playback, waveform or mutation."""
    evaluated = _time(evaluated_at, "evaluated_at")
    assert evaluated is not None
    reasons: set[str] = set()
    unknown = False
    if intent.to_dict()["policy_sha256"] != policy.record_sha256:
        reasons.add("POLICY_HASH_MISMATCH")
    if intent.to_dict()["source_binding_sha256"] != source.record_sha256:
        reasons.add("SOURCE_HASH_MISMATCH")
    if intent.to_dict()["capability_binding_sha256"] != capability.record_sha256:
        reasons.add("CAPABILITY_HASH_MISMATCH")
    policy_data, source_data, capability_data, intent_data = (
        policy.to_dict(), source.to_dict(), capability.to_dict(), intent.to_dict()
    )
    expires = policy_data["expires_at"]
    if expires is not None and _dt(evaluated) >= _dt(expires):
        reasons.add("POLICY_EXPIRED")
    if source_data["contract_state"] != ContractState.BOUND_VERIFIED.value:
        reasons.add("SOURCE_NOT_BOUND")
        unknown |= source_data["contract_state"] in {ContractState.CANONICAL_REF_NOT_PROVIDED.value, ContractState.UNKNOWN.value}
    if source_data["rights_state"] != RightsState.PASS.value:
        reasons.add("SOURCE_RIGHTS_NOT_PASS")
        unknown |= source_data["rights_state"] == RightsState.UNKNOWN.value
    if capability_data["contract_state"] != ContractState.BOUND_VERIFIED.value:
        reasons.add("CAPABILITY_NOT_BOUND")
        unknown |= capability_data["contract_state"] in {ContractState.CANONICAL_REF_NOT_PROVIDED.value, ContractState.UNKNOWN.value}
    requested = set(intent_data["requested_operations"])
    required_states = {"AUDITION": "player_state", "WAVEFORM_VIEW": "waveform_state"}
    for operation, field in required_states.items():
        if operation in requested and capability_data[field] != CapabilityState.SUPPORTED.value:
            reasons.add(f"{operation}_NOT_SUPPORTED")
            unknown |= capability_data[field] in {CapabilityState.PROBE_REQUIRED.value, CapabilityState.UNKNOWN.value}
    if capability_data["decode_state"] != CapabilityState.SUPPORTED.value:
        reasons.add("SOURCE_DECODE_NOT_SUPPORTED")
        unknown |= capability_data["decode_state"] in {CapabilityState.PROBE_REQUIRED.value, CapabilityState.UNKNOWN.value}
    if source_data["sample_rate_hz"] is not None and source_data["sample_rate_hz"] != policy_data["required_sample_rate_hz"]:
        reasons.add("SAMPLE_RATE_MISMATCH")
    if source_data["duration_samples"] is not None and intent_data["range_end_sample"] > source_data["duration_samples"]:
        reasons.add("RANGE_OUTSIDE_SOURCE")
    if intent_data["range_end_sample"] - intent_data["range_start_sample"] > policy_data["max_review_duration_samples"]:
        reasons.add("REVIEW_RANGE_EXCEEDS_POLICY")
    for observed_field, code in (("observed_at", "SOURCE_OBSERVATION_STALE"),):
        observed = source_data[observed_field]
        if observed is not None and (_dt(evaluated) - _dt(observed)).total_seconds() > policy_data["max_observation_age_seconds"]:
            reasons.add(code)
    cap_observed = capability_data["observed_at"]
    if cap_observed is not None and (_dt(evaluated) - _dt(cap_observed)).total_seconds() > policy_data["max_observation_age_seconds"]:
        reasons.add("CAPABILITY_OBSERVATION_STALE")
    blocking = bool(reasons)
    decision = "READY_FOR_HUMAN_REVIEW" if not blocking else ("UNKNOWN" if unknown else "BLOCKED")
    return {
        "decision": decision,
        "reason_codes": sorted(reasons),
        "policy_sha256": policy.record_sha256,
        "source_binding_sha256": source.record_sha256,
        "capability_binding_sha256": capability.record_sha256,
        "intent_sha256": intent.record_sha256,
        "evaluated_at": evaluated,
        "playback_started": False,
        "waveform_render_started": False,
        "media_mutation_started": False,
        "daw_launch_started": False,
        "asset_registration_started": False,
        "placement_mutation_started": False,
    }


def validate_external_review_inclusion(
    *, receipt: ExternalAudioReviewReceiptBinding, intent: AudioMediaReviewIntent,
    source: AudioMediaSourceBinding, capability: PlaybackWaveformCapabilityBinding,
) -> dict[str, Any]:
    """Prove an externally issued receipt exactly includes the reviewed inputs."""
    body = receipt.to_dict()
    reasons: list[str] = []
    if body["contract_state"] != ContractState.BOUND_VERIFIED.value:
        reasons.append("RECEIPT_NOT_BOUND")
    if body["intent_sha256"] != intent.record_sha256:
        reasons.append("INTENT_MISMATCH")
    if body["source_binding_sha256"] != source.record_sha256:
        reasons.append("SOURCE_MISMATCH")
    if body["capability_binding_sha256"] != capability.record_sha256:
        reasons.append("CAPABILITY_MISMATCH")
    intent_data = intent.to_dict()
    if (body["range_start_sample"], body["range_end_sample"]) != (
        intent_data["range_start_sample"], intent_data["range_end_sample"]
    ):
        reasons.append("RANGE_MISMATCH")
    return {
        "classification": "ACCEPT_PROVEN_EXTERNAL_REVIEW" if not reasons else "REJECT_OR_UNKNOWN",
        "reason_codes": sorted(reasons),
        "receipt_sha256": receipt.record_sha256,
        "effect_started_by_module": False,
    }


def private_projection(record: _Record) -> dict[str, Any]:
    return record.to_dict()


def public_projection(record: _Record) -> dict[str, Any]:
    data = record.to_dict()
    public = {
        "schema_id": SCHEMA_ID,
        "record_type": data["record_type"],
        "record_sha256": data["record_sha256"],
        "contract_state": data.get("contract_state"),
        "media_kind": data.get("media_kind"),
        "rights_state": data.get("rights_state"),
        "audio_decision": data.get("audio_decision"),
        "visual_decision": data.get("visual_decision"),
        "handoff_state": data.get("handoff_state"),
        "reason_codes": list(data.get("reason_codes", [])),
        "body_included": False,
        "absolute_path_included": False,
        "private_reference_included": False,
        "audio_body_included": False,
    }
    return {key: value for key, value in public.items() if value is not None}


EFFECT_SURFACE = MappingProxyType({
    "audio_read": False,
    "playback": False,
    "waveform_render": False,
    "media_strip_or_write": False,
    "asset_registration": False,
    "placement_mutation": False,
    "daw_launch_or_operation": False,
    "provider_or_paid_call": False,
    "release_or_deploy": False,
})


__all__ = [
    "AudioMediaReviewDecision", "AudioMediaReviewIntent", "AudioMediaReviewPolicyRevision",
    "AudioMediaSourceBinding", "DawRoundTripStatusBinding", "DerivedAudioAssetProposal",
    "ExternalAudioReviewReceiptBinding", "PlaybackWaveformCapabilityBinding", "EFFECT_SURFACE",
    "SCHEMA_ID", "classify_review_admission", "private_projection", "public_projection",
    "validate_external_review_inclusion", "validate_record",
]
