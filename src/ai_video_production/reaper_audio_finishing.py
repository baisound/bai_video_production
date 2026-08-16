"""TASK-035 body-free REAPER audio finishing and round-trip contracts.

The module only validates immutable metadata and classifies preflight state. It
does not launch REAPER, read or write projects/audio, host plug-ins, render,
promote Assets, mutate Resolve, or grant an execution authority.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task035.reaper-audio-finishing.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_MAX_BINDINGS = 512
_MAX_TRACKS = 256
_MAX_ROUTES = 1024
_MAX_RENDERS = 64
_MAX_REASONS = 64


class ContractState(str, Enum):
    CANONICAL_REF_NOT_PROVIDED = "CANONICAL_REF_NOT_PROVIDED"
    BOUND_VERIFIED = "BOUND_VERIFIED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class CapabilityState(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    PROBE_REQUIRED = "PROBE_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class LicenseState(str, Enum):
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class RightsState(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class DawSourceKind(str, Enum):
    ASSET_REVISION = "ASSET_REVISION"
    TIMELINE_AUDIO = "TIMELINE_AUDIO"
    AUDIO_WORKSPACE = "AUDIO_WORKSPACE"
    PLACEMENT_PLAN = "PLACEMENT_PLAN"
    RESOURCE_ADMISSION = "RESOURCE_ADMISSION"
    QUALITY_POLICY = "QUALITY_POLICY"


class DawOwnership(str, Enum):
    AUTOMATION_OWNED = "AUTOMATION_OWNED"
    HUMAN_OWNED = "HUMAN_OWNED"
    SHARED_REVIEW = "SHARED_REVIEW"


class DawPlanState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT_READY = "PREFLIGHT_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class DawOperation(str, Enum):
    CREATE_PROJECT = "CREATE_PROJECT"
    SYNC_PROJECT = "SYNC_PROJECT"
    APPLY_TRACK_PLAN = "APPLY_TRACK_PLAN"
    RENDER_MIX = "RENDER_MIX"
    RENDER_STEMS = "RENDER_STEMS"


class ExternalExecutionState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED_SAFE = "CANCELLED_SAFE"
    UNKNOWN = "UNKNOWN"


class QaDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class HumanMixDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETEST = "RETEST"


class RoundTripState(str, Enum):
    RENDER_CANDIDATE = "RENDER_CANDIDATE"
    QA_VERIFIED = "QA_VERIFIED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    ASSET_BOUND = "ASSET_BOUND"
    PLACEMENT_BOUND = "PLACEMENT_BOUND"
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


def _ordered(
    value: Any, name: str, maximum: int, *, digest: bool = False,
    enum: type[Enum] | None = None, required: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an ordered array")
    result = tuple(value)
    if (required and not result) or len(result) > maximum or len(result) != len(set(result)):
        raise ValueError(f"{name} must be unique and bounded")
    if result != tuple(sorted(result)):
        raise ValueError(f"{name} must use canonical sorted order")
    for item in result:
        if digest:
            _digest(item, name)
        elif enum is not None:
            _enum(enum, item, name)
        else:
            _id(item, name)
    return result


def _reasons(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("reason_codes must be an ordered array")
    result = tuple(value)
    if len(result) > _MAX_REASONS or len(result) != len(set(result)):
        raise ValueError("reason_codes must be unique and bounded")
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


def _revision(value: Mapping[str, Any], name: str) -> None:
    revision = _integer(value["revision"], f"{name}.revision", 1, 2_147_483_647)
    parent = _digest(value["parent_record_sha256"], "parent_record_sha256", nullable=True)
    if (revision == 1) != (parent is None):
        raise ValueError(f"{name} parent/revision mismatch")


def _policy(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "policy_id", "revision", "parent_record_sha256",
        "required_sample_rate_hz", "max_tracks", "max_routes", "max_render_targets",
        "allow_human_owned_mutation", "official_policy_ref", "official_policy_sha256",
        "effective_at", "expires_at", "record_sha256",
    }
    _keys(value, fields, "DawFinishingPolicyRevision")
    _id(value["policy_id"], "policy_id")
    _revision(value, "policy")
    if value["required_sample_rate_hz"] != 48_000:
        raise ValueError("R0 canonical render sample rate must be 48000 Hz")
    _integer(value["max_tracks"], "max_tracks", 1, _MAX_TRACKS)
    _integer(value["max_routes"], "max_routes", 1, _MAX_ROUTES)
    _integer(value["max_render_targets"], "max_render_targets", 1, _MAX_RENDERS)
    if value["allow_human_owned_mutation"] is not False:
        raise ValueError("Human-owned DAW objects are immutable")
    _id(value["official_policy_ref"], "official_policy_ref")
    _digest(value["official_policy_sha256"], "official_policy_sha256")
    effective = _time(value["effective_at"], "effective_at")
    expires = _time(value["expires_at"], "expires_at", nullable=True)
    if expires is not None and _dt(expires) <= _dt(effective):
        raise ValueError("expires_at must follow effective_at")


def _source(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "source_id", "source_kind", "contract_state", "canonical_ref",
        "canonical_sha256", "canonical_revision", "rights_state", "observed_at",
        "body_included", "absolute_path_included", "record_sha256",
    }
    _keys(value, fields, "DawSourceBinding")
    _id(value["source_id"], "source_id")
    _enum(DawSourceKind, value["source_kind"], "source_kind")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    rights = _enum(RightsState, value["rights_state"], "rights_state")
    if value["body_included"] is not False or value["absolute_path_included"] is not False:
        raise ValueError("DAW source binding must remain body/path free")
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in ("canonical_ref", "canonical_sha256", "canonical_revision", "observed_at")):
            raise ValueError("unresolved source invents canonical fields")
        if rights is not RightsState.UNKNOWN:
            raise ValueError("unresolved source rights must remain UNKNOWN")
        return
    _id(value["canonical_ref"], "canonical_ref", nullable=True)
    _digest(value["canonical_sha256"], "canonical_sha256", nullable=True)
    if value["canonical_revision"] is not None:
        _integer(value["canonical_revision"], "canonical_revision", 1, 2_147_483_647)
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(
        value[field] is None for field in ("canonical_ref", "canonical_sha256", "canonical_revision", "observed_at")
    ):
        raise ValueError("BOUND_VERIFIED source is incomplete")


def _capability(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "report_id", "reaper_version", "platform", "executable_sha256",
        "reascript_api_state", "project_read_state", "project_write_state", "undo_state",
        "render_mix_state", "render_stems_state", "plugin_inventory_state",
        "plugin_inventory_sha256", "license_state", "probed_at", "probe_profile_sha256",
        "private_path_included", "license_data_included", "record_sha256",
    }
    _keys(value, fields, "DawCapabilityReport")
    _id(value["report_id"], "report_id")
    _id(value["reaper_version"], "reaper_version")
    if value["platform"] != "WINDOWS_X64":
        raise ValueError("R0 supports only the probed WINDOWS_X64 target")
    _digest(value["executable_sha256"], "executable_sha256")
    states = (
        "reascript_api_state", "project_read_state", "project_write_state", "undo_state",
        "render_mix_state", "render_stems_state", "plugin_inventory_state",
    )
    for field in states:
        _enum(CapabilityState, value[field], field)
    _digest(value["plugin_inventory_sha256"], "plugin_inventory_sha256", nullable=True)
    if (value["plugin_inventory_state"] == CapabilityState.SUPPORTED.value) != (value["plugin_inventory_sha256"] is not None):
        raise ValueError("supported plugin inventory requires an exact digest")
    _enum(LicenseState, value["license_state"], "license_state")
    _time(value["probed_at"], "probed_at")
    _digest(value["probe_profile_sha256"], "probe_profile_sha256")
    if value["private_path_included"] is not False or value["license_data_included"] is not False:
        raise ValueError("Capability report cannot expose path/license data")


def _plan(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "session_plan_id", "production_job_id", "revision",
        "parent_record_sha256", "project_id", "source_binding_hashes",
        "timeline_binding_sha256", "audio_workspace_sha256", "resource_admission_sha256",
        "capability_report_sha256", "sample_rate_hz", "frame_rate_numerator",
        "frame_rate_denominator", "channel_layout", "track_spec_hashes", "route_spec_hashes",
        "render_target_hashes", "ownership", "plan_state", "reason_codes",
        "body_included", "absolute_path_included", "execution_started", "record_sha256",
    }
    _keys(value, fields, "DawSessionPlan")
    _id(value["session_plan_id"], "session_plan_id")
    _id(value["production_job_id"], "production_job_id")
    _revision(value, "session plan")
    _id(value["project_id"], "project_id")
    _ordered(value["source_binding_hashes"], "source_binding_hashes", _MAX_BINDINGS, digest=True, required=True)
    for field in ("timeline_binding_sha256", "audio_workspace_sha256", "resource_admission_sha256", "capability_report_sha256"):
        _digest(value[field], field)
    if value["sample_rate_hz"] != 48_000:
        raise ValueError("session plan sample rate must be 48000 Hz")
    _integer(value["frame_rate_numerator"], "frame_rate_numerator", 1, 1_000_000)
    _integer(value["frame_rate_denominator"], "frame_rate_denominator", 1, 1_000_000)
    if value["channel_layout"] not in {"MONO", "STEREO", "MULTICHANNEL"}:
        raise ValueError("channel_layout is invalid")
    _ordered(value["track_spec_hashes"], "track_spec_hashes", _MAX_TRACKS, digest=True, required=True)
    _ordered(value["route_spec_hashes"], "route_spec_hashes", _MAX_ROUTES, digest=True)
    _ordered(value["render_target_hashes"], "render_target_hashes", _MAX_RENDERS, digest=True, required=True)
    ownership = _enum(DawOwnership, value["ownership"], "ownership")
    state = _enum(DawPlanState, value["plan_state"], "plan_state")
    _reasons(value["reason_codes"])
    if ownership is DawOwnership.HUMAN_OWNED and state is DawPlanState.PREFLIGHT_READY:
        raise ValueError("Human-owned project cannot be automation preflight ready")
    if any(value[field] is not False for field in ("body_included", "absolute_path_included", "execution_started")):
        raise ValueError("Session Plan must remain body/path free and unexecuted")


def _authorization(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "authorization_id", "authorization_revision",
        "authorization_sha256", "session_plan_sha256", "capability_report_sha256",
        "resource_gate_sha256", "operation", "authority_kind", "issued_at", "expires_at",
        "one_shot", "consumed", "evidence_ref", "evidence_sha256", "record_sha256",
    }
    _keys(value, fields, "DawExecutionAuthorizationBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    nullable = fields - {"record_type", "contract_state", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved execution authorization invents fields")
        return
    for field in ("authorization_id", "evidence_ref"):
        _id(value[field], field, nullable=True)
    for field in ("authorization_sha256", "session_plan_sha256", "capability_report_sha256", "resource_gate_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if value["authorization_revision"] is not None:
        _integer(value["authorization_revision"], "authorization_revision", 1, 2_147_483_647)
    if value["operation"] is not None:
        _enum(DawOperation, value["operation"], "operation")
    if value["authority_kind"] not in {"OWNER_HUMAN_GATE", None}:
        raise ValueError("authority_kind must be OWNER_HUMAN_GATE")
    _time(value["issued_at"], "issued_at", nullable=True)
    _time(value["expires_at"], "expires_at", nullable=True)
    if value["one_shot"] not in {True, False, None} or value["consumed"] not in {True, False, None}:
        raise ValueError("one_shot/consumed must be boolean or null")
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in nullable):
            raise ValueError("BOUND_VERIFIED execution authorization is incomplete")
        if value["one_shot"] is not True or value["consumed"] is not False:
            raise ValueError("execution authorization must be unused and one-shot")
        if _dt(value["expires_at"]) <= _dt(value["issued_at"]):
            raise ValueError("authorization expires_at must follow issued_at")


def _snapshot(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "snapshot_ref", "snapshot_sha256",
        "session_plan_sha256", "project_state_sha256", "reaper_version", "ownership",
        "observed_at", "retained_as_evidence", "absolute_path_included", "record_sha256",
    }
    _keys(value, fields, "DawProjectSnapshotBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if value["absolute_path_included"] is not False:
        raise ValueError("Project snapshot binding cannot expose an absolute path")
    nullable = fields - {"record_type", "contract_state", "absolute_path_included", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved project snapshot invents fields")
        return
    for field in ("snapshot_ref", "reaper_version"):
        _id(value[field], field, nullable=True)
    for field in ("snapshot_sha256", "session_plan_sha256", "project_state_sha256"):
        _digest(value[field], field, nullable=True)
    if value["ownership"] is not None:
        _enum(DawOwnership, value["ownership"], "ownership")
    _time(value["observed_at"], "observed_at", nullable=True)
    if value["retained_as_evidence"] not in {True, False, None}:
        raise ValueError("retained_as_evidence must be boolean or null")
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED project snapshot is incomplete")


def _execution(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "receipt_ref", "receipt_sha256",
        "operation_identity", "operation", "session_plan_sha256", "authorization_sha256",
        "before_snapshot_sha256", "after_snapshot_sha256", "external_state", "started_at",
        "completed_at", "canonical_persistence_verified", "effect_started_by_module",
        "record_sha256",
    }
    _keys(value, fields, "DawExecutionReceiptBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if value["effect_started_by_module"] is not False:
        raise ValueError("pure TASK-035 module cannot execute REAPER")
    nullable = fields - {"record_type", "contract_state", "effect_started_by_module", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved execution receipt invents fields")
        return
    for field in ("receipt_ref", "operation_identity"):
        _id(value[field], field, nullable=True)
    for field in ("receipt_sha256", "session_plan_sha256", "authorization_sha256", "before_snapshot_sha256", "after_snapshot_sha256"):
        _digest(value[field], field, nullable=True)
    if value["operation"] is not None:
        _enum(DawOperation, value["operation"], "operation")
    if value["external_state"] is not None:
        external = _enum(ExternalExecutionState, value["external_state"], "external_state")
    else:
        external = None
    started = _time(value["started_at"], "started_at", nullable=True)
    completed = _time(value["completed_at"], "completed_at", nullable=True)
    if started is not None and completed is not None and _dt(completed) < _dt(started):
        raise ValueError("execution completion precedes start")
    if value["canonical_persistence_verified"] not in {True, False, None}:
        raise ValueError("canonical_persistence_verified must be boolean or null")
    if state is ContractState.BOUND_VERIFIED:
        required = nullable - {"after_snapshot_sha256", "completed_at"}
        if any(value[field] is None for field in required):
            raise ValueError("BOUND_VERIFIED execution receipt is incomplete")
        if external is ExternalExecutionState.COMPLETED:
            if value["after_snapshot_sha256"] is None or completed is None:
                raise ValueError("COMPLETED requires after snapshot and completion time")
            if value["canonical_persistence_verified"] is not True:
                raise ValueError("COMPLETED requires canonical persistence proof")
        elif external in {ExternalExecutionState.FAILED, ExternalExecutionState.CANCELLED_SAFE} and completed is None:
            raise ValueError("terminal execution state requires completion time")


def _qa(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "qa_receipt_ref", "qa_receipt_sha256",
        "rendered_candidate_sha256", "quality_policy_sha256", "analyzer_profile_sha256",
        "sample_rate_hz", "channel_layout", "duration_samples", "qa_decision",
        "observed_at", "audio_analyzed_by_module", "record_sha256",
    }
    _keys(value, fields, "AudioQaReceiptBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    if value["audio_analyzed_by_module"] is not False:
        raise ValueError("pure TASK-035 module cannot analyze audio")
    nullable = fields - {"record_type", "contract_state", "audio_analyzed_by_module", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved QA binding invents fields")
        return
    _id(value["qa_receipt_ref"], "qa_receipt_ref", nullable=True)
    for field in ("qa_receipt_sha256", "rendered_candidate_sha256", "quality_policy_sha256", "analyzer_profile_sha256"):
        _digest(value[field], field, nullable=True)
    if value["sample_rate_hz"] is not None:
        _integer(value["sample_rate_hz"], "sample_rate_hz", 1, 768_000)
    if value["channel_layout"] not in {"MONO", "STEREO", "MULTICHANNEL", None}:
        raise ValueError("channel_layout is invalid")
    if value["duration_samples"] is not None:
        _integer(value["duration_samples"], "duration_samples", 1, 9_223_372_036_854_775_807)
    if value["qa_decision"] is not None:
        _enum(QaDecision, value["qa_decision"], "qa_decision")
    _time(value["observed_at"], "observed_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED:
        if any(value[field] is None for field in nullable):
            raise ValueError("BOUND_VERIFIED QA receipt is incomplete")
        if value["qa_decision"] == QaDecision.PASS.value and value["sample_rate_hz"] != 48_000:
            raise ValueError("QA PASS requires canonical 48000 Hz output")


def _approval(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "contract_state", "approval_id", "approval_sha256",
        "candidate_manifest_sha256", "qa_receipt_sha256", "decision", "reviewer_kind",
        "decided_at", "evidence_ref", "evidence_sha256", "record_sha256",
    }
    _keys(value, fields, "HumanMixApprovalBinding")
    state = _enum(ContractState, value["contract_state"], "contract_state")
    nullable = fields - {"record_type", "contract_state", "record_sha256"}
    if state is ContractState.CANONICAL_REF_NOT_PROVIDED:
        if any(value[field] is not None for field in nullable):
            raise ValueError("unresolved Human approval invents fields")
        return
    for field in ("approval_id", "evidence_ref"):
        _id(value[field], field, nullable=True)
    for field in ("approval_sha256", "candidate_manifest_sha256", "qa_receipt_sha256", "evidence_sha256"):
        _digest(value[field], field, nullable=True)
    if value["decision"] is not None:
        _enum(HumanMixDecision, value["decision"], "decision")
    if value["reviewer_kind"] not in {"OWNER", None}:
        raise ValueError("reviewer_kind must be OWNER")
    _time(value["decided_at"], "decided_at", nullable=True)
    if state is ContractState.BOUND_VERIFIED and any(value[field] is None for field in nullable):
        raise ValueError("BOUND_VERIFIED Human approval is incomplete")


def _manifest(value: Mapping[str, Any]) -> None:
    fields = {
        "record_type", "manifest_id", "revision", "parent_record_sha256", "project_id",
        "session_plan_sha256", "project_snapshot_sha256", "execution_receipt_sha256",
        "rendered_asset_binding_hashes", "qa_receipt_hashes", "human_approval_sha256",
        "resolve_placement_plan_sha256", "round_trip_state", "reason_codes",
        "untreated_source_preserved", "asset_promotion_started", "resolve_mutation_started",
        "publication_started", "record_sha256",
    }
    _keys(value, fields, "AudioRoundTripManifest")
    _id(value["manifest_id"], "manifest_id")
    _revision(value, "round-trip manifest")
    _id(value["project_id"], "project_id")
    for field in ("session_plan_sha256", "project_snapshot_sha256", "execution_receipt_sha256"):
        _digest(value[field], field)
    _ordered(value["rendered_asset_binding_hashes"], "rendered_asset_binding_hashes", _MAX_RENDERS, digest=True, required=True)
    qa = _ordered(value["qa_receipt_hashes"], "qa_receipt_hashes", _MAX_RENDERS, digest=True)
    approval = _digest(value["human_approval_sha256"], "human_approval_sha256", nullable=True)
    placement = _digest(value["resolve_placement_plan_sha256"], "resolve_placement_plan_sha256", nullable=True)
    state = _enum(RoundTripState, value["round_trip_state"], "round_trip_state")
    _reasons(value["reason_codes"])
    if state in {RoundTripState.QA_VERIFIED, RoundTripState.HUMAN_APPROVED, RoundTripState.ASSET_BOUND, RoundTripState.PLACEMENT_BOUND} and not qa:
        raise ValueError("advanced round-trip state requires QA receipts")
    if state in {RoundTripState.RENDER_CANDIDATE, RoundTripState.QA_VERIFIED} and approval is not None:
        raise ValueError("pre-approval state cannot reference Human approval")
    if state in {RoundTripState.HUMAN_APPROVED, RoundTripState.ASSET_BOUND, RoundTripState.PLACEMENT_BOUND} and approval is None:
        raise ValueError("advanced round-trip state requires Human approval")
    if state is not RoundTripState.PLACEMENT_BOUND and placement is not None:
        raise ValueError("only PLACEMENT_BOUND may reference Resolve placement")
    if state is RoundTripState.PLACEMENT_BOUND and placement is None:
        raise ValueError("PLACEMENT_BOUND requires exact Resolve placement plan")
    if value["untreated_source_preserved"] is not True:
        raise ValueError("untreated source must remain preserved")
    if any(value[field] is not False for field in ("asset_promotion_started", "resolve_mutation_started", "publication_started")):
        raise ValueError("metadata manifest cannot perform downstream effects")


_VALIDATORS = {
    "DawFinishingPolicyRevision": _policy,
    "DawSourceBinding": _source,
    "DawCapabilityReport": _capability,
    "DawSessionPlan": _plan,
    "DawExecutionAuthorizationBinding": _authorization,
    "DawProjectSnapshotBinding": _snapshot,
    "DawExecutionReceiptBinding": _execution,
    "AudioQaReceiptBinding": _qa,
    "HumanMixApprovalBinding": _approval,
    "AudioRoundTripManifest": _manifest,
}


@dataclass(frozen=True, slots=True)
class _Record:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    @classmethod
    def create(cls, **fields: Any) -> "_Record":
        return cls.from_dict(_hashed({"record_type": cls.RECORD_TYPE, **copy.deepcopy(fields)}))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_Record":
        if value.get("record_type") != cls.RECORD_TYPE:
            raise ValueError(f"record_type must be {cls.RECORD_TYPE}")
        _VALIDATORS[cls.RECORD_TYPE](value)
        _check_hash(value)
        return cls(_freeze(value))

    @property
    def record_sha256(self) -> str:
        return self.data["record_sha256"]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)


class DawFinishingPolicyRevision(_Record): RECORD_TYPE = "DawFinishingPolicyRevision"
class DawSourceBinding(_Record): RECORD_TYPE = "DawSourceBinding"
class DawCapabilityReport(_Record): RECORD_TYPE = "DawCapabilityReport"
class DawSessionPlan(_Record): RECORD_TYPE = "DawSessionPlan"
class DawExecutionAuthorizationBinding(_Record): RECORD_TYPE = "DawExecutionAuthorizationBinding"
class DawProjectSnapshotBinding(_Record): RECORD_TYPE = "DawProjectSnapshotBinding"
class DawExecutionReceiptBinding(_Record): RECORD_TYPE = "DawExecutionReceiptBinding"
class AudioQaReceiptBinding(_Record): RECORD_TYPE = "AudioQaReceiptBinding"
class HumanMixApprovalBinding(_Record): RECORD_TYPE = "HumanMixApprovalBinding"
class AudioRoundTripManifest(_Record): RECORD_TYPE = "AudioRoundTripManifest"


_CLASSES = {cls.RECORD_TYPE: cls for cls in (
    DawFinishingPolicyRevision, DawSourceBinding, DawCapabilityReport, DawSessionPlan,
    DawExecutionAuthorizationBinding, DawProjectSnapshotBinding, DawExecutionReceiptBinding,
    AudioQaReceiptBinding, HumanMixApprovalBinding, AudioRoundTripManifest,
)}


def validate_record(value: Mapping[str, Any]) -> _Record:
    try:
        return _CLASSES[value.get("record_type")].from_dict(value)
    except (KeyError, TypeError) as exc:
        raise ValueError("unknown TASK-035 record_type") from exc


def classify_preflight(
    *, policy: DawFinishingPolicyRevision, capability: DawCapabilityReport,
    plan: DawSessionPlan, sources: tuple[DawSourceBinding, ...], evaluated_at: str,
) -> dict[str, Any]:
    """Classify plan readiness without issuing authority or touching REAPER."""
    now = _time(evaluated_at, "evaluated_at")
    p = policy.to_dict()
    c = capability.to_dict()
    session = plan.to_dict()
    reasons: list[str] = []
    decision = "READY_FOR_OWNER_HUMAN_GATE"
    severity = {"READY_FOR_OWNER_HUMAN_GATE": 0, "UNKNOWN": 1, "BLOCKED": 2}

    def classify(candidate: str) -> None:
        nonlocal decision
        if severity[candidate] > severity[decision]:
            decision = candidate
    if _dt(now) < _dt(p["effective_at"]) or (p["expires_at"] is not None and _dt(now) >= _dt(p["expires_at"])):
        classify("BLOCKED")
        reasons.append("POLICY_NOT_CURRENT")
    if session["sample_rate_hz"] != p["required_sample_rate_hz"]:
        classify("BLOCKED")
        reasons.append("SAMPLE_RATE_POLICY_MISMATCH")
    if session["capability_report_sha256"] != capability.record_sha256:
        classify("BLOCKED")
        reasons.append("CAPABILITY_BINDING_MISMATCH")
    expected_sources = sorted(item.record_sha256 for item in sources)
    if session["source_binding_hashes"] != expected_sources:
        classify("BLOCKED")
        reasons.append("SOURCE_SET_MISMATCH")
    if not sources or any(item.to_dict()["contract_state"] != ContractState.BOUND_VERIFIED.value for item in sources):
        classify("UNKNOWN")
        reasons.append("SOURCE_BINDING_UNRESOLVED")
    if any(item.to_dict()["rights_state"] != RightsState.PASS.value for item in sources):
        classify("BLOCKED" if any(
            item.to_dict()["rights_state"] in {RightsState.BLOCKED.value, RightsState.REVOKED.value}
            for item in sources
        ) else "UNKNOWN")
        reasons.append("SOURCE_RIGHTS_NOT_PASS")
    required_capabilities = (
        "reascript_api_state", "project_read_state", "project_write_state", "undo_state",
        "render_mix_state",
    )
    if any(c[field] in {CapabilityState.UNSUPPORTED.value} for field in required_capabilities):
        classify("BLOCKED")
        reasons.append("REQUIRED_CAPABILITY_UNSUPPORTED")
    elif any(c[field] != CapabilityState.SUPPORTED.value for field in required_capabilities):
        classify("UNKNOWN")
        reasons.append("REQUIRED_CAPABILITY_NOT_PROVEN")
    if c["license_state"] != LicenseState.VERIFIED.value:
        classify("BLOCKED" if c["license_state"] == LicenseState.REVOKED.value else "UNKNOWN")
        reasons.append("LICENSE_STATE_NOT_VERIFIED")
    if session["plan_state"] != DawPlanState.PREFLIGHT_READY.value:
        classify("BLOCKED" if session["plan_state"] == DawPlanState.BLOCKED.value else "UNKNOWN")
        reasons.append("SESSION_PLAN_NOT_PREFLIGHT_READY")
    return {
        "policy_sha256": policy.record_sha256,
        "capability_report_sha256": capability.record_sha256,
        "session_plan_sha256": plan.record_sha256,
        "decision": decision,
        "reason_codes": list(dict.fromkeys(reasons)),
        "execution_authority_issued": False,
        "reaper_launched": False,
        "project_mutation_started": False,
        "audio_render_started": False,
        "asset_promotion_started": False,
        "resolve_mutation_started": False,
        "publication_started": False,
    }


def private_projection(record: _Record) -> dict[str, Any]:
    return record.to_dict()


def public_projection(record: _Record) -> dict[str, Any]:
    data = record.to_dict()
    result: dict[str, Any] = {
        "record_type": data["record_type"], "record_sha256": data["record_sha256"],
        "body_included": False, "absolute_path_included": False,
        "license_data_included": False, "private_plugin_inventory_included": False,
    }
    for field in (
        "contract_state", "plan_state", "round_trip_state", "qa_decision", "decision",
        "external_state", "rights_state", "ownership",
    ):
        if field in data:
            result[field] = data[field]
    if "reason_codes" in data:
        result["reason_codes"] = list(data["reason_codes"])
    return result


EFFECT_SURFACE = MappingProxyType({
    "reaper_launch_or_operation": False,
    "project_or_audio_filesystem_io": False,
    "plugin_scan_insert_parameter_or_preset": False,
    "audio_render_or_analysis": False,
    "asset_promotion": False,
    "resolve_mutation": False,
    "release_deploy_production": False,
})


__all__ = [
    "AudioQaReceiptBinding", "AudioRoundTripManifest", "CapabilityState", "ContractState",
    "DawCapabilityReport", "DawExecutionAuthorizationBinding", "DawExecutionReceiptBinding",
    "DawFinishingPolicyRevision", "DawOperation", "DawOwnership", "DawPlanState",
    "DawProjectSnapshotBinding", "DawSessionPlan", "DawSourceBinding", "DawSourceKind",
    "EFFECT_SURFACE", "ExternalExecutionState", "HumanMixApprovalBinding", "HumanMixDecision",
    "LicenseState", "QaDecision", "RightsState", "RoundTripState", "classify_preflight",
    "private_projection", "public_projection", "validate_record",
]
