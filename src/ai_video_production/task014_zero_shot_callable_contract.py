"""Body-free TASK-014 zero-shot callable binding contract.

This module binds already-canonical narration admission, preflight, profile and
plan coordinates for a future external-dispatch gate.  It never issues the
subject/plan authority receipts that it consumes and never loads a model,
reads or writes audio, dispatches work, records a result, or creates QA/Asset
truth.  Hash linkage proves record consistency, not authenticity; callers must
load authority receipts from their canonical owners.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import re

from .owner_narration import NarrationGenerationMode, NarrationGenerationPlan
from .owner_narration_local_primary import (
    ContractState,
    LocalNarrationRouteMode,
    LocalPrimaryNarrationPreflight,
    NarrationIntendedUsage,
    PreflightDecision,
    parse_local_primary_preflight,
)
from .owner_narration_local_render_admission import (
    DurableJobState,
    LocalPrimaryNarrationRenderAdmission,
    RenderAdmissionDecision,
    render_operation_identity_sha256,
    parse_render_admission,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_revision import (
    ArtifactAdmissionState,
    CapabilityProbeState,
    ConsentState,
    VoiceProfileRevision,
)


SCHEMA_ID = "bai.task014.zero-shot-callable-envelope.v1"
SUBJECT_RECEIPT_SCHEMA_ID = "bai.task014.zero-shot-subject-binding-receipt.v1"
PLAN_RECEIPT_SCHEMA_ID = "bai.task014.canonical-narration-plan-derivation-receipt.v1"

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}$")
_RFC3339_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "private-key")

_REQUIRED_ARTIFACT_CLASS = "STAGED_NARRATION_PCM_WAV_48000_MONO"
_REQUIRED_SAMPLE_RATE_HZ = 48_000
_REQUIRED_CHANNELS = 1
_REQUIRED_SAMPLE_FORMAT = "PCM_S24LE"


class SubjectBindingAuthorityKind(str, Enum):
    CANONICAL_OWNER_CAPTURE_CHAIN = "CANONICAL_OWNER_CAPTURE_CHAIN"
    OWNER_HUMAN_GATE = "OWNER_HUMAN_GATE"


class SubjectMatchDecision(str, Enum):
    VERIFIED_SAME_SUBJECT = "VERIFIED_SAME_SUBJECT"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class PlanDerivationAuthorityKind(str, Enum):
    CANONICAL_NARRATION_PLAN_STORE = "CANONICAL_NARRATION_PLAN_STORE"


class PlanDerivationDecision(str, Enum):
    VERIFIED_FROM_APPROVED_BODY = "VERIFIED_FROM_APPROVED_BODY"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class CallableEnvelopeDecision(str, Enum):
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_ENVELOPE_BODY_FIELDS = (
    "compiled_at", "project_id", "admission_id", "admission_revision",
    "admission_sha256", "preflight_id", "preflight_sha256", "plan_id",
    "plan_sha256", "subject_binding_receipt_sha256",
    "plan_derivation_receipt_sha256", "script_text_revision_sha256",
    "voice_profile_id", "voice_profile_revision_sha256", "route_mode",
    "intended_usage", "registered_job_id", "registered_job_revision_sha256",
    "render_operation_identity_sha256", "authorization_id",
    "authorization_revision", "authorization_sha256", "engine_id",
    "engine_revision_sha256", "model_artifact_id", "model_artifact_sha256",
    "runtime_id", "runtime_sha256", "code_revision_sha256",
    "reference_asset_id", "reference_asset_checksum_sha256",
    "asset_revision_binding_ref", "asset_revision_binding_sha256",
    "reference_profile_ref", "reference_profile_sha256", "destination_id",
    "destination_policy_sha256", "required_artifact_class",
    "required_sample_rate_hz", "required_channels", "required_sample_format",
    "decision", "reason_codes",
)

_ENVELOPE_FALSE_FLAGS = (
    "script_body_persisted", "audio_body_persisted",
    "private_voice_id_persisted", "credential_value_persisted",
    "host_path_persisted", "execution_started", "dispatch_started",
    "model_loaded", "gpu_reserved", "audio_rendered", "asset_published",
)


def _envelope_content_body(values: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "record_type": "ZeroShotCallableEnvelope",
        "task_owner": "TASK-014",
    }
    for field in _ENVELOPE_BODY_FIELDS:
        value = values[field]
        if isinstance(value, Enum):
            value = value.value
        elif field == "reason_codes":
            value = list(value)
        body[field] = value
    body.update({flag: False for flag in _ENVELOPE_FALSE_FLAGS})
    return body


_BLOCKER_REASONS = frozenset(
    {
        "ADMISSION_NOT_READY",
        "PREFLIGHT_BINDING_MISMATCH",
        "PREFLIGHT_NOT_READY",
        "ZERO_SHOT_ROUTE_REQUIRED",
        "VOICE_PROFILE_REVISION_MISMATCH",
        "VOICE_PROFILE_NOT_ADMITTED",
        "SUBJECT_BINDING_MISMATCH",
        "SUBJECT_BINDING_EXPIRED",
        "ZERO_SHOT_REFERENCE_MISMATCH",
        "PLAN_DERIVATION_MISMATCH",
        "PLAN_DERIVATION_EXPIRED",
        "PLAN_COORDINATE_MISMATCH",
        "PLAN_CHUNK_INTEGRITY_MISMATCH",
        "ENGINE_BINDING_MISMATCH",
        "JOB_BINDING_MISMATCH",
        "RESOURCE_OR_DESTINATION_MISMATCH",
        "AUTHORIZATION_SCOPE_MISMATCH",
        "AUTHORIZATION_EXPIRED",
        "OPERATION_IDENTITY_MISMATCH",
        "CALLABLE_TIME_ORDER_MISMATCH",
    }
)
_UNKNOWN_REASONS = frozenset(
    {
        "SUBJECT_BINDING_NOT_PROVIDED",
        "SUBJECT_BINDING_UNKNOWN",
        "PLAN_DERIVATION_NOT_PROVIDED",
        "PLAN_DERIVATION_UNKNOWN",
        "CANONICAL_BINDING_UNRESOLVED",
        "CANONICAL_AUTHORITY_NOT_CONFIRMED",
        "TRUSTED_EVALUATION_TIME_NOT_CONFIRMED",
    }
)
_ALL_REASONS = _BLOCKER_REASONS | _UNKNOWN_REASONS


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or "//" in value
        or ":" in value
        or "?" in value
        or "#" in value
        or "@" in value
        or any(part == ".." for part in value.split("/"))
        or any(term in folded for term in _PRIVATE_TERMS)
    ):
        raise ValueError(f"{name} violates the body-free identity boundary")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=name)


def _nullable_id(value: Any, name: str) -> str | None:
    return None if value is None else _id(value, name)


def _nullable_digest(value: Any, name: str) -> str | None:
    return None if value is None else _digest(value, name)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer >= 1")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339_UTC_RE.fullmatch(value):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{name} must be UTC")
    return parsed


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _hash(body: Mapping[str, Any] | list[Mapping[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(body))


def _content_address(prefix: str, body: Mapping[str, Any]) -> tuple[str, str]:
    digest = _hash(body)
    return prefix + digest.removeprefix("sha256:"), digest


def _subject_ref_sha256(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _false(value: Any, name: str) -> None:
    if value is not False:
        raise ValueError(f"{name} must remain false")


@dataclass(frozen=True, slots=True)
class ZeroShotReferenceSubjectBindingReceipt:
    receipt_id: str
    receipt_sha256: str
    project_id: str
    voice_profile_id: str
    voice_profile_revision_sha256: str
    consent_sha256: str
    consent_subject_ref_sha256: str
    reference_asset_id: str
    reference_asset_checksum_sha256: str
    asset_revision_binding_ref: str
    asset_revision_binding_sha256: str
    reference_profile_ref: str
    reference_profile_sha256: str
    capture_lineage_ref: str
    capture_lineage_sha256: str
    consent_current_evaluation_sha256: str
    rights_current_evaluation_sha256: str
    authority_kind: SubjectBindingAuthorityKind
    subject_match_decision: SubjectMatchDecision
    subject_match_evidence_ref: str
    subject_match_evidence_sha256: str
    evaluated_at: str
    expires_at: str
    usage_scope: str
    audio_body_persisted: bool
    speaker_embedding_persisted: bool
    private_subject_ref_persisted: bool
    host_path_persisted: bool

    def __post_init__(self) -> None:
        for name in (
            "receipt_id",
            "project_id",
            "voice_profile_id",
            "reference_asset_id",
            "asset_revision_binding_ref",
            "reference_profile_ref",
            "capture_lineage_ref",
            "subject_match_evidence_ref",
        ):
            _id(getattr(self, name), name)
        for name in (
            "receipt_sha256",
            "voice_profile_revision_sha256",
            "consent_sha256",
            "consent_subject_ref_sha256",
            "reference_asset_checksum_sha256",
            "asset_revision_binding_sha256",
            "reference_profile_sha256",
            "capture_lineage_sha256",
            "consent_current_evaluation_sha256",
            "rights_current_evaluation_sha256",
            "subject_match_evidence_sha256",
        ):
            _digest(getattr(self, name), name)
        object.__setattr__(self, "authority_kind", _enum(SubjectBindingAuthorityKind, self.authority_kind, "authority_kind"))
        object.__setattr__(self, "subject_match_decision", _enum(SubjectMatchDecision, self.subject_match_decision, "subject_match_decision"))
        _timestamp(self.evaluated_at, "evaluated_at")
        if _timestamp(self.expires_at, "expires_at") <= _timestamp(self.evaluated_at, "evaluated_at"):
            raise ValueError("subject receipt must expire after evaluation")
        if self.usage_scope != "ZERO_SHOT_OWNER_NARRATION":
            raise ValueError("subject receipt usage_scope is invalid")
        for name in (
            "audio_body_persisted",
            "speaker_embedding_persisted",
            "private_subject_ref_persisted",
            "host_path_persisted",
        ):
            _false(getattr(self, name), name)
        expected_id, expected_sha = _content_address("zero-shot-subject-receipt-", self._content_body())
        if self.receipt_id != expected_id or self.receipt_sha256 != expected_sha:
            raise ValueError("subject receipt content address mismatch")

    def _content_body(self) -> dict[str, Any]:
        return {
            "schema": SUBJECT_RECEIPT_SCHEMA_ID,
            "record_type": "ZeroShotReferenceSubjectBindingReceipt",
            "task_owner": "TASK-014",
            "project_id": self.project_id,
            "voice_profile_id": self.voice_profile_id,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "consent_sha256": self.consent_sha256,
            "consent_subject_ref_sha256": self.consent_subject_ref_sha256,
            "reference_asset_id": self.reference_asset_id,
            "reference_asset_checksum_sha256": self.reference_asset_checksum_sha256,
            "asset_revision_binding_ref": self.asset_revision_binding_ref,
            "asset_revision_binding_sha256": self.asset_revision_binding_sha256,
            "reference_profile_ref": self.reference_profile_ref,
            "reference_profile_sha256": self.reference_profile_sha256,
            "capture_lineage_ref": self.capture_lineage_ref,
            "capture_lineage_sha256": self.capture_lineage_sha256,
            "consent_current_evaluation_sha256": self.consent_current_evaluation_sha256,
            "rights_current_evaluation_sha256": self.rights_current_evaluation_sha256,
            "authority_kind": self.authority_kind.value,
            "subject_match_decision": self.subject_match_decision.value,
            "subject_match_evidence_ref": self.subject_match_evidence_ref,
            "subject_match_evidence_sha256": self.subject_match_evidence_sha256,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
            "usage_scope": self.usage_scope,
            "audio_body_persisted": False,
            "speaker_embedding_persisted": False,
            "private_subject_ref_persisted": False,
            "host_path_persisted": False,
        }

    def to_private_dict(self) -> dict[str, Any]:
        return {**self._content_body(), "receipt_id": self.receipt_id, "receipt_sha256": self.receipt_sha256}

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "schema": SUBJECT_RECEIPT_SCHEMA_ID,
            "record_type": "ZeroShotReferenceSubjectBindingReceiptPublicProjection",
            "task_owner": "TASK-014",
            "authority_kind": self.authority_kind.value,
            "subject_match_decision": self.subject_match_decision.value,
            "usage_scope": self.usage_scope,
            "private_binding_persisted": False,
            "audio_body_persisted": False,
            "speaker_embedding_persisted": False,
            "private_subject_ref_persisted": False,
            "host_path_persisted": False,
        }
        body["public_projection_sha256"] = _hash(body)
        return body


@dataclass(frozen=True, slots=True)
class CanonicalNarrationPlanRevisionReceipt:
    receipt_id: str
    receipt_sha256: str
    project_id: str
    plan_id: str
    plan_revision: int
    parent_plan_revision_sha256: str | None
    plan_sha256: str
    approved_text_revision_ref: str
    approved_text_revision_sha256: str
    approved_script_body_sha256: str
    source_text_binding_sha256: str
    voice_profile_id: str
    voice_profile_revision_sha256: str
    route_mode: LocalNarrationRouteMode
    mode: NarrationGenerationMode
    model_id: str
    language_code: str
    normalization_policy_id: str
    normalization_policy_revision: int
    normalization_policy_sha256: str
    chunking_policy_id: str
    chunking_policy_revision: int
    chunking_policy_sha256: str
    compiler_code_revision_sha256: str
    ordered_chunk_manifest_sha256: str
    chunk_count: int
    plan_store_ref: str
    plan_store_revision: int
    plan_store_record_sha256: str
    authority_kind: PlanDerivationAuthorityKind
    derivation_decision: PlanDerivationDecision
    derivation_evidence_ref: str
    derivation_evidence_sha256: str
    evaluated_at: str
    expires_at: str | None
    script_body_persisted: bool
    chunk_body_persisted: bool
    host_path_persisted: bool
    execution_authorized: bool

    def __post_init__(self) -> None:
        for name in (
            "receipt_id",
            "project_id",
            "plan_id",
            "approved_text_revision_ref",
            "voice_profile_id",
            "model_id",
            "language_code",
            "normalization_policy_id",
            "chunking_policy_id",
            "plan_store_ref",
            "derivation_evidence_ref",
        ):
            _id(getattr(self, name), name)
        for name in (
            "receipt_sha256",
            "plan_sha256",
            "approved_text_revision_sha256",
            "approved_script_body_sha256",
            "source_text_binding_sha256",
            "voice_profile_revision_sha256",
            "normalization_policy_sha256",
            "chunking_policy_sha256",
            "compiler_code_revision_sha256",
            "ordered_chunk_manifest_sha256",
            "plan_store_record_sha256",
            "derivation_evidence_sha256",
        ):
            _digest(getattr(self, name), name)
        _positive_int(self.plan_revision, "plan_revision")
        if self.plan_revision == 1 and self.parent_plan_revision_sha256 is not None:
            raise ValueError("first plan revision must not have a parent")
        if self.plan_revision > 1 and self.parent_plan_revision_sha256 is None:
            raise ValueError("later plan revision requires a parent")
        _nullable_digest(self.parent_plan_revision_sha256, "parent_plan_revision_sha256")
        for name in (
            "normalization_policy_revision",
            "chunking_policy_revision",
            "chunk_count",
            "plan_store_revision",
        ):
            _positive_int(getattr(self, name), name)
        object.__setattr__(self, "route_mode", _enum(LocalNarrationRouteMode, self.route_mode, "route_mode"))
        object.__setattr__(self, "mode", _enum(NarrationGenerationMode, self.mode, "mode"))
        object.__setattr__(self, "authority_kind", _enum(PlanDerivationAuthorityKind, self.authority_kind, "authority_kind"))
        object.__setattr__(self, "derivation_decision", _enum(PlanDerivationDecision, self.derivation_decision, "derivation_decision"))
        evaluated = _timestamp(self.evaluated_at, "evaluated_at")
        if self.expires_at is not None and _timestamp(self.expires_at, "expires_at") <= evaluated:
            raise ValueError("plan receipt expiry must follow evaluation")
        for name in (
            "script_body_persisted",
            "chunk_body_persisted",
            "host_path_persisted",
            "execution_authorized",
        ):
            _false(getattr(self, name), name)
        expected_id, expected_sha = _content_address("narration-plan-derivation-receipt-", self._content_body())
        if self.receipt_id != expected_id or self.receipt_sha256 != expected_sha:
            raise ValueError("plan derivation receipt content address mismatch")

    def _content_body(self) -> dict[str, Any]:
        return {
            "schema": PLAN_RECEIPT_SCHEMA_ID,
            "record_type": "CanonicalNarrationPlanRevisionReceipt",
            "task_owner": "TASK-014",
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "plan_revision": self.plan_revision,
            "parent_plan_revision_sha256": self.parent_plan_revision_sha256,
            "plan_sha256": self.plan_sha256,
            "approved_text_revision_ref": self.approved_text_revision_ref,
            "approved_text_revision_sha256": self.approved_text_revision_sha256,
            "approved_script_body_sha256": self.approved_script_body_sha256,
            "source_text_binding_sha256": self.source_text_binding_sha256,
            "voice_profile_id": self.voice_profile_id,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "route_mode": self.route_mode.value,
            "mode": self.mode.value,
            "model_id": self.model_id,
            "language_code": self.language_code,
            "normalization_policy_id": self.normalization_policy_id,
            "normalization_policy_revision": self.normalization_policy_revision,
            "normalization_policy_sha256": self.normalization_policy_sha256,
            "chunking_policy_id": self.chunking_policy_id,
            "chunking_policy_revision": self.chunking_policy_revision,
            "chunking_policy_sha256": self.chunking_policy_sha256,
            "compiler_code_revision_sha256": self.compiler_code_revision_sha256,
            "ordered_chunk_manifest_sha256": self.ordered_chunk_manifest_sha256,
            "chunk_count": self.chunk_count,
            "plan_store_ref": self.plan_store_ref,
            "plan_store_revision": self.plan_store_revision,
            "plan_store_record_sha256": self.plan_store_record_sha256,
            "authority_kind": self.authority_kind.value,
            "derivation_decision": self.derivation_decision.value,
            "derivation_evidence_ref": self.derivation_evidence_ref,
            "derivation_evidence_sha256": self.derivation_evidence_sha256,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
            "script_body_persisted": False,
            "chunk_body_persisted": False,
            "host_path_persisted": False,
            "execution_authorized": False,
        }

    def to_private_dict(self) -> dict[str, Any]:
        return {**self._content_body(), "receipt_id": self.receipt_id, "receipt_sha256": self.receipt_sha256}

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "schema": PLAN_RECEIPT_SCHEMA_ID,
            "record_type": "CanonicalNarrationPlanRevisionReceiptPublicProjection",
            "task_owner": "TASK-014",
            "authority_kind": self.authority_kind.value,
            "derivation_decision": self.derivation_decision.value,
            "route_mode": self.route_mode.value,
            "mode": self.mode.value,
            "chunk_count": self.chunk_count,
            "private_binding_persisted": False,
            "script_body_persisted": False,
            "chunk_body_persisted": False,
            "host_path_persisted": False,
            "execution_authorized": False,
        }
        body["public_projection_sha256"] = _hash(body)
        return body


@dataclass(frozen=True, slots=True)
class ZeroShotCallableEnvelope:
    envelope_id: str
    envelope_sha256: str
    compiled_at: str
    project_id: str
    admission_id: str
    admission_revision: int
    admission_sha256: str
    preflight_id: str | None
    preflight_sha256: str | None
    plan_id: str
    plan_sha256: str
    subject_binding_receipt_sha256: str | None
    plan_derivation_receipt_sha256: str | None
    script_text_revision_sha256: str
    voice_profile_id: str
    voice_profile_revision_sha256: str
    route_mode: LocalNarrationRouteMode
    intended_usage: NarrationIntendedUsage
    registered_job_id: str | None
    registered_job_revision_sha256: str | None
    render_operation_identity_sha256: str | None
    authorization_id: str | None
    authorization_revision: int | None
    authorization_sha256: str | None
    engine_id: str | None
    engine_revision_sha256: str | None
    model_artifact_id: str | None
    model_artifact_sha256: str | None
    runtime_id: str | None
    runtime_sha256: str | None
    code_revision_sha256: str | None
    reference_asset_id: str | None
    reference_asset_checksum_sha256: str | None
    asset_revision_binding_ref: str | None
    asset_revision_binding_sha256: str | None
    reference_profile_ref: str | None
    reference_profile_sha256: str | None
    destination_id: str | None
    destination_policy_sha256: str | None
    required_artifact_class: str
    required_sample_rate_hz: int
    required_channels: int
    required_sample_format: str
    decision: CallableEnvelopeDecision
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("envelope_id", "project_id", "admission_id", "plan_id", "voice_profile_id"):
            _id(getattr(self, name), name)
        for name in (
            "preflight_id",
            "registered_job_id",
            "authorization_id",
            "engine_id",
            "model_artifact_id",
            "runtime_id",
            "reference_asset_id",
            "asset_revision_binding_ref",
            "reference_profile_ref",
            "destination_id",
        ):
            _nullable_id(getattr(self, name), name)
        for name in (
            "envelope_sha256",
            "admission_sha256",
            "plan_sha256",
            "script_text_revision_sha256",
            "voice_profile_revision_sha256",
        ):
            _digest(getattr(self, name), name)
        for name in (
            "preflight_sha256",
            "subject_binding_receipt_sha256",
            "plan_derivation_receipt_sha256",
            "registered_job_revision_sha256",
            "render_operation_identity_sha256",
            "authorization_sha256",
            "engine_revision_sha256",
            "model_artifact_sha256",
            "runtime_sha256",
            "code_revision_sha256",
            "reference_asset_checksum_sha256",
            "asset_revision_binding_sha256",
            "reference_profile_sha256",
            "destination_policy_sha256",
        ):
            _nullable_digest(getattr(self, name), name)
        _positive_int(self.admission_revision, "admission_revision")
        if self.authorization_revision is not None:
            _positive_int(self.authorization_revision, "authorization_revision")
        object.__setattr__(self, "route_mode", _enum(LocalNarrationRouteMode, self.route_mode, "route_mode"))
        object.__setattr__(self, "intended_usage", _enum(NarrationIntendedUsage, self.intended_usage, "intended_usage"))
        object.__setattr__(self, "decision", _enum(CallableEnvelopeDecision, self.decision, "decision"))
        _timestamp(self.compiled_at, "compiled_at")
        if (
            self.required_artifact_class != _REQUIRED_ARTIFACT_CLASS
            or self.required_sample_rate_hz != _REQUIRED_SAMPLE_RATE_HZ
            or self.required_channels != _REQUIRED_CHANNELS
            or self.required_sample_format != _REQUIRED_SAMPLE_FORMAT
        ):
            raise ValueError("callable media constraints are invalid")
        if (
            len(self.reason_codes) > 64
            or tuple(sorted(set(self.reason_codes))) != self.reason_codes
            or any(not isinstance(reason, str) or not _REASON_RE.fullmatch(reason) or reason not in _ALL_REASONS for reason in self.reason_codes)
        ):
            raise ValueError("reason_codes are invalid")
        has_blocker = bool(set(self.reason_codes) & _BLOCKER_REASONS)
        has_unknown = bool(set(self.reason_codes) & _UNKNOWN_REASONS)
        if (
            (self.decision is CallableEnvelopeDecision.BLOCKED and not has_blocker)
            or (self.decision is CallableEnvelopeDecision.UNKNOWN and (not has_unknown or has_blocker))
        ):
            raise ValueError("callable decision and reasons are inconsistent")
        expected_id, expected_sha = _content_address("zero-shot-callable-", self._content_body())
        if self.envelope_id != expected_id or self.envelope_sha256 != expected_sha:
            raise ValueError("callable envelope content address mismatch")

    def _content_body(self) -> dict[str, Any]:
        return _envelope_content_body(
            {field: getattr(self, field) for field in _ENVELOPE_BODY_FIELDS}
        )

    def to_private_dict(self) -> dict[str, Any]:
        return {**self._content_body(), "envelope_id": self.envelope_id, "envelope_sha256": self.envelope_sha256}

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "schema": SCHEMA_ID,
            "record_type": "ZeroShotCallableEnvelopePublicProjection",
            "task_owner": "TASK-014",
            "route_mode": self.route_mode.value,
            "intended_usage": self.intended_usage.value,
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "required_artifact_class": self.required_artifact_class,
            "required_sample_rate_hz": self.required_sample_rate_hz,
            "required_channels": self.required_channels,
            "required_sample_format": self.required_sample_format,
            "private_binding_persisted": False,
            "script_body_persisted": False,
            "audio_body_persisted": False,
            "private_voice_id_persisted": False,
            "credential_value_persisted": False,
            "host_path_persisted": False,
            "execution_started": False,
            "dispatch_started": False,
            "model_loaded": False,
            "gpu_reserved": False,
            "audio_rendered": False,
            "asset_published": False,
        }
        body["public_projection_sha256"] = _hash(body)
        return body


def _plan_sha256(plan: NarrationGenerationPlan) -> str:
    value = plan.to_dict().get("plan_sha256")
    return _digest(value, "plan_sha256")


def _ordered_chunk_manifest_sha256(plan: NarrationGenerationPlan) -> str:
    return _hash(
        [
            {"chunk_id": chunk.chunk_id, "order": chunk.order, "text_sha256": chunk.text_sha256}
            for chunk in plan.chunks
        ]
    )


def _plan_structure_reasons(plan: NarrationGenerationPlan) -> list[str]:
    reasons: list[str] = []
    try:
        _id(plan.plan_id, "plan_id")
        _id(plan.script_id, "script_id")
        _digest(plan.script_sha256, "script_sha256")
        _id(plan.voice_profile_id, "voice_profile_id")
        _digest(plan.voice_profile_digest, "voice_profile_digest")
        _id(plan.model_id, "model_id")
        _id(plan.language_code, "language_code")
    except ValueError:
        return ["PLAN_CHUNK_INTEGRITY_MISMATCH"]
    if not isinstance(plan.mode, NarrationGenerationMode):
        reasons.append("PLAN_COORDINATE_MISMATCH")
    if (
        not plan.chunks
        or tuple(chunk.order for chunk in plan.chunks) != tuple(range(1, len(plan.chunks) + 1))
        or len({chunk.chunk_id for chunk in plan.chunks}) != len(plan.chunks)
    ):
        reasons.append("PLAN_CHUNK_INTEGRITY_MISMATCH")
    for chunk in plan.chunks:
        try:
            _id(chunk.chunk_id, "chunk_id")
            _digest(chunk.text_sha256, "chunk.text_sha256")
        except ValueError:
            reasons.append("PLAN_CHUNK_INTEGRITY_MISMATCH")
            break
        if not isinstance(chunk.text, str) or not chunk.text.strip() or chunk.text_sha256 != sha256_bytes(chunk.text.encode("utf-8")):
            reasons.append("PLAN_CHUNK_INTEGRITY_MISMATCH")
            break
    if not reasons:
        seed = canonical_json_bytes(
            {
                "script": plan.script_sha256,
                "voice": plan.voice_profile_digest,
                "mode": plan.mode.value,
                "model": plan.model_id,
                "language": plan.language_code,
                "chunks": [chunk.text_sha256 for chunk in plan.chunks],
            }
        )
        expected_id = "narration-plan-" + sha256_bytes(seed).split(":", 1)[1][:16]
        if plan.plan_id != expected_id:
            reasons.append("PLAN_CHUNK_INTEGRITY_MISMATCH")
    return reasons


def _copy_optional_fields(source: Mapping[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any]:
    if source is None:
        return {field: None for field in fields}
    return {field: source.get(field) for field in fields}


def compile_zero_shot_callable_envelope(
    *,
    admission: LocalPrimaryNarrationRenderAdmission,
    preflight: LocalPrimaryNarrationPreflight,
    profile_revision: VoiceProfileRevision,
    plan: NarrationGenerationPlan,
    subject_binding_receipt: ZeroShotReferenceSubjectBindingReceipt | None,
    plan_derivation_receipt: CanonicalNarrationPlanRevisionReceipt | None,
    compiled_at: str,
) -> ZeroShotCallableEnvelope:
    """Compile a no-effect zero-shot binding that cannot authorize dispatch."""

    admission = parse_render_admission(admission.to_private_dict())
    preflight = parse_local_primary_preflight(preflight.to_private_dict())
    profile_revision = VoiceProfileRevision.from_private_dict(profile_revision.to_private_dict())
    if subject_binding_receipt is not None:
        subject_binding_receipt = parse_zero_shot_reference_subject_binding_receipt(subject_binding_receipt.to_private_dict())
    if plan_derivation_receipt is not None:
        plan_derivation_receipt = parse_canonical_narration_plan_revision_receipt(plan_derivation_receipt.to_private_dict())
    compiled_instant = _timestamp(compiled_at, "compiled_at")
    plan_sha256 = _plan_sha256(plan)

    blocked: list[str] = []
    unknown: list[str] = []
    if admission.decision is not RenderAdmissionDecision.READY_FOR_EXTERNAL_DISPATCH_GATE:
        blocked.append("ADMISSION_NOT_READY")
    if admission.route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL or preflight.route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL:
        blocked.append("ZERO_SHOT_ROUTE_REQUIRED")
    preflight_binding = admission.preflight_binding
    if (
        preflight.project_id != admission.project_id
        or preflight.preflight_id != preflight_binding.preflight_id
        or preflight.preflight_sha256 != preflight_binding.preflight_sha256
        or preflight.route_mode is not admission.route_mode
        or preflight.intended_usage is not admission.intended_usage
        or preflight.script_text_binding["approved_text_revision_sha256"] != admission.script_text_revision_sha256
        or preflight.voice_profile_revision_binding["voice_profile_revision_sha256"] != admission.voice_profile_revision_sha256
    ):
        blocked.append("PREFLIGHT_BINDING_MISMATCH")
    if preflight.decision is not PreflightDecision.READY_FOR_OWNER_HUMAN_GATE:
        blocked.append("PREFLIGHT_NOT_READY")
    if (
        profile_revision.voice_profile_id != admission.voice_profile_revision_id
        or profile_revision.voice_profile_revision_sha256 != admission.voice_profile_revision_sha256
    ):
        blocked.append("VOICE_PROFILE_REVISION_MISMATCH")
    if (
        profile_revision.consent.state is not ConsentState.ACTIVE
        or not profile_revision.consent.subject_verified
        or "OWNER_NARRATION_LOCAL" not in profile_revision.consent.allowed_usage_classes
        or profile_revision.license.artifact_state is not ArtifactAdmissionState.APPROVED
        or not profile_revision.license.commercial_use_allowed
        or profile_revision.capability.probe_state is not CapabilityProbeState.VERIFIED
        or not profile_revision.capability.offline_only
    ):
        blocked.append("VOICE_PROFILE_NOT_ADMITTED")

    zero = preflight.zero_shot_reference_binding
    engine = preflight.engine_admission_binding
    if zero is None:
        blocked.append("ZERO_SHOT_REFERENCE_MISMATCH")
    elif zero["contract_state"] in {ContractState.CANONICAL_REF_NOT_PROVIDED.value, ContractState.UNKNOWN.value}:
        unknown.append("CANONICAL_BINDING_UNRESOLVED")
    elif zero["contract_state"] != ContractState.BOUND_VERIFIED.value:
        blocked.append("ZERO_SHOT_REFERENCE_MISMATCH")
    if engine["contract_state"] in {ContractState.CANONICAL_REF_NOT_PROVIDED.value, ContractState.UNKNOWN.value}:
        unknown.append("CANONICAL_BINDING_UNRESOLVED")
    elif engine["contract_state"] != ContractState.BOUND_VERIFIED.value:
        blocked.append("ENGINE_BINDING_MISMATCH")

    if subject_binding_receipt is None:
        unknown.append("SUBJECT_BINDING_NOT_PROVIDED")
    else:
        consent = profile_revision.consent.to_dict()
        expected_subject = {
            "project_id": admission.project_id,
            "voice_profile_id": profile_revision.voice_profile_id,
            "voice_profile_revision_sha256": profile_revision.voice_profile_revision_sha256,
            "consent_sha256": consent["consent_sha256"],
            "consent_subject_ref_sha256": _subject_ref_sha256(profile_revision.consent.consent_subject_ref),
        }
        if any(getattr(subject_binding_receipt, field) != value for field, value in expected_subject.items()):
            blocked.append("SUBJECT_BINDING_MISMATCH")
        if zero is not None:
            expected_reference = {
                "reference_asset_id": zero["asset_id"],
                "reference_asset_checksum_sha256": zero["asset_checksum_sha256"],
                "asset_revision_binding_ref": zero["asset_revision_binding_ref"],
                "asset_revision_binding_sha256": zero["asset_revision_binding_sha256"],
                "reference_profile_ref": zero["reference_profile_ref"],
                "reference_profile_sha256": zero["reference_profile_sha256"],
                "consent_current_evaluation_sha256": zero["consent_current_evaluation_sha256"],
                "rights_current_evaluation_sha256": zero["rights_current_evaluation_sha256"],
            }
            if any(getattr(subject_binding_receipt, field) != value for field, value in expected_reference.items()):
                blocked.append("ZERO_SHOT_REFERENCE_MISMATCH")
        if subject_binding_receipt.consent_current_evaluation_sha256 != preflight.voice_profile_revision_binding["current_consent_evaluation_sha256"]:
            blocked.append("SUBJECT_BINDING_MISMATCH")
        if subject_binding_receipt.rights_current_evaluation_sha256 != preflight.rights_evaluation_binding["evidence_sha256"]:
            blocked.append("SUBJECT_BINDING_MISMATCH")
        if subject_binding_receipt.subject_match_decision is SubjectMatchDecision.UNKNOWN:
            unknown.append("SUBJECT_BINDING_UNKNOWN")
        elif subject_binding_receipt.subject_match_decision is not SubjectMatchDecision.VERIFIED_SAME_SUBJECT:
            blocked.append("SUBJECT_BINDING_MISMATCH")
        if compiled_instant >= _timestamp(subject_binding_receipt.expires_at, "subject expires_at"):
            blocked.append("SUBJECT_BINDING_EXPIRED")

    blocked.extend(_plan_structure_reasons(plan))
    expected_mode = NarrationGenerationMode.PREVIEW if admission.intended_usage is NarrationIntendedUsage.PREVIEW else NarrationGenerationMode.FULL_RENDER
    if (
        plan.script_id != admission.script_text_revision_id
        or plan.script_sha256 != admission.script_text_revision_sha256
        or plan.voice_profile_id != profile_revision.voice_profile_id
        or plan.voice_profile_digest != profile_revision.canonical_narration_profile_sha256
        or plan.mode is not expected_mode
    ):
        blocked.append("PLAN_COORDINATE_MISMATCH")
    if (
        engine.get("engine_id") is None
        or plan.model_id != engine.get("engine_id")
        or plan.model_id != profile_revision.license.exact_model_id
        or plan.model_id != profile_revision.capability.engine_id
        or plan.language_code not in profile_revision.capability.supported_languages
        or engine.get("model_artifact_id") != profile_revision.license.model_artifact_id
        or engine.get("model_artifact_sha256") != profile_revision.license.checkpoint_sha256
        or engine.get("runtime_id") != profile_revision.license.runtime_id
    ):
        blocked.append("ENGINE_BINDING_MISMATCH")

    if plan_derivation_receipt is None:
        unknown.append("PLAN_DERIVATION_NOT_PROVIDED")
    else:
        script_binding = preflight.script_text_binding
        expected_plan = {
            "project_id": admission.project_id,
            "plan_id": plan.plan_id,
            "plan_sha256": plan_sha256,
            "approved_text_revision_ref": script_binding["approved_text_revision_ref"],
            "approved_text_revision_sha256": script_binding["approved_text_revision_sha256"],
            "approved_script_body_sha256": plan.script_sha256,
            "source_text_binding_sha256": script_binding["source_text_binding_sha256"],
            "voice_profile_id": profile_revision.voice_profile_id,
            "voice_profile_revision_sha256": profile_revision.voice_profile_revision_sha256,
            "route_mode": LocalNarrationRouteMode.ZERO_SHOT_LOCAL,
            "mode": plan.mode,
            "model_id": plan.model_id,
            "language_code": plan.language_code,
            "ordered_chunk_manifest_sha256": _ordered_chunk_manifest_sha256(plan),
            "chunk_count": len(plan.chunks),
        }
        if any(getattr(plan_derivation_receipt, field) != value for field, value in expected_plan.items()):
            blocked.append("PLAN_DERIVATION_MISMATCH")
        if plan_derivation_receipt.derivation_decision is PlanDerivationDecision.UNKNOWN:
            unknown.append("PLAN_DERIVATION_UNKNOWN")
        elif plan_derivation_receipt.derivation_decision is not PlanDerivationDecision.VERIFIED_FROM_APPROVED_BODY:
            blocked.append("PLAN_DERIVATION_MISMATCH")
        if plan_derivation_receipt.expires_at is not None and compiled_instant >= _timestamp(plan_derivation_receipt.expires_at, "plan expires_at"):
            blocked.append("PLAN_DERIVATION_EXPIRED")

    operation_identity: str | None = None
    try:
        operation_identity = render_operation_identity_sha256(
            project_id=admission.project_id,
            admission_id=admission.admission_id,
            admission_revision=admission.revision,
            route_mode=admission.route_mode,
            intended_usage=admission.intended_usage,
            script_text_revision_sha256=admission.script_text_revision_sha256,
            voice_profile_revision_sha256=admission.voice_profile_revision_sha256,
            preflight_sha256=admission.preflight_binding.preflight_sha256,
            destination_policy_sha256=admission.output_destination_binding.storage_policy_sha256,
        )
    except ValueError:
        blocked.append("OPERATION_IDENTITY_MISMATCH")
    if operation_identity != admission.durable_job_binding.operation_identity_sha256:
        blocked.append("OPERATION_IDENTITY_MISMATCH")
    if (
        admission.durable_job_binding.contract_state.value != ContractState.BOUND_VERIFIED.value
        or admission.durable_job_binding.job_state is not DurableJobState.REGISTERED
    ):
        blocked.append("JOB_BINDING_MISMATCH")
    destination = admission.output_destination_binding
    if (
        destination.contract_state.value != ContractState.BOUND_VERIFIED.value
        or destination.allowed_artifact_class != _REQUIRED_ARTIFACT_CLASS
        or destination.public_exposure is not False
        or admission.resource_admission_binding.contract_state.value != ContractState.BOUND_VERIFIED.value
    ):
        blocked.append("RESOURCE_OR_DESTINATION_MISMATCH")
    authorization = admission.execution_authorization_binding
    if authorization.contract_state.value != ContractState.BOUND_VERIFIED.value or authorization.one_shot is not True:
        blocked.append("AUTHORIZATION_SCOPE_MISMATCH")
    evidence_times = (
        preflight.created_at,
        admission.created_at,
        admission.preflight_binding.evaluated_at,
        admission.resource_admission_binding.evaluated_at,
        authorization.issued_at,
        None if subject_binding_receipt is None else subject_binding_receipt.evaluated_at,
        None if plan_derivation_receipt is None else plan_derivation_receipt.evaluated_at,
    )
    if any(
        evidence_time is not None
        and compiled_instant < _timestamp(evidence_time, "evidence time")
        for evidence_time in evidence_times
    ):
        blocked.append("CALLABLE_TIME_ORDER_MISMATCH")
    for expiry, reason in (
        (admission.preflight_binding.expires_at, "AUTHORIZATION_EXPIRED"),
        (admission.resource_admission_binding.expires_at, "AUTHORIZATION_EXPIRED"),
        (authorization.expires_at, "AUTHORIZATION_EXPIRED"),
    ):
        if expiry is not None and compiled_instant >= _timestamp(expiry, "gate expires_at"):
            blocked.append(reason)
            break

    if not blocked and not unknown:
        unknown.extend(
            (
                "CANONICAL_AUTHORITY_NOT_CONFIRMED",
                "TRUSTED_EVALUATION_TIME_NOT_CONFIRMED",
            )
        )
    reasons = tuple(sorted(set(blocked + unknown)))
    decision = (
        CallableEnvelopeDecision.BLOCKED
        if blocked
        else CallableEnvelopeDecision.UNKNOWN
    )
    zero_values = _copy_optional_fields(
        zero,
        (
            "asset_id",
            "asset_checksum_sha256",
            "asset_revision_binding_ref",
            "asset_revision_binding_sha256",
            "reference_profile_ref",
            "reference_profile_sha256",
        ),
    )
    engine_values = _copy_optional_fields(
        engine,
        (
            "engine_id",
            "engine_revision_sha256",
            "model_artifact_id",
            "model_artifact_sha256",
            "runtime_id",
            "runtime_sha256",
            "code_revision_sha256",
        ),
    )
    body_values = dict(
        envelope_id="zero-shot-callable-" + "0" * 64,
        envelope_sha256="sha256:" + "0" * 64,
        compiled_at=compiled_at,
        project_id=admission.project_id,
        admission_id=admission.admission_id,
        admission_revision=admission.revision,
        admission_sha256=admission.admission_sha256,
        preflight_id=preflight.preflight_id,
        preflight_sha256=preflight.preflight_sha256,
        plan_id=plan.plan_id,
        plan_sha256=plan_sha256,
        subject_binding_receipt_sha256=None if subject_binding_receipt is None else subject_binding_receipt.receipt_sha256,
        plan_derivation_receipt_sha256=None if plan_derivation_receipt is None else plan_derivation_receipt.receipt_sha256,
        script_text_revision_sha256=admission.script_text_revision_sha256,
        voice_profile_id=profile_revision.voice_profile_id,
        voice_profile_revision_sha256=profile_revision.voice_profile_revision_sha256,
        route_mode=admission.route_mode,
        intended_usage=admission.intended_usage,
        registered_job_id=admission.durable_job_binding.job_id,
        registered_job_revision_sha256=admission.durable_job_binding.job_revision_sha256,
        render_operation_identity_sha256=operation_identity,
        authorization_id=authorization.authorization_id,
        authorization_revision=authorization.authorization_revision,
        authorization_sha256=authorization.authorization_sha256,
        engine_id=engine_values["engine_id"],
        engine_revision_sha256=engine_values["engine_revision_sha256"],
        model_artifact_id=engine_values["model_artifact_id"],
        model_artifact_sha256=engine_values["model_artifact_sha256"],
        runtime_id=engine_values["runtime_id"],
        runtime_sha256=engine_values["runtime_sha256"],
        code_revision_sha256=engine_values["code_revision_sha256"],
        reference_asset_id=zero_values["asset_id"],
        reference_asset_checksum_sha256=zero_values["asset_checksum_sha256"],
        asset_revision_binding_ref=zero_values["asset_revision_binding_ref"],
        asset_revision_binding_sha256=zero_values["asset_revision_binding_sha256"],
        reference_profile_ref=zero_values["reference_profile_ref"],
        reference_profile_sha256=zero_values["reference_profile_sha256"],
        destination_id=destination.destination_id,
        destination_policy_sha256=destination.storage_policy_sha256,
        required_artifact_class=_REQUIRED_ARTIFACT_CLASS,
        required_sample_rate_hz=_REQUIRED_SAMPLE_RATE_HZ,
        required_channels=_REQUIRED_CHANNELS,
        required_sample_format=_REQUIRED_SAMPLE_FORMAT,
        decision=decision,
        reason_codes=reasons,
    )
    envelope_id, envelope_sha256 = _content_address(
        "zero-shot-callable-", _envelope_content_body(body_values)
    )
    body_values.update(envelope_id=envelope_id, envelope_sha256=envelope_sha256)
    return ZeroShotCallableEnvelope(**body_values)


def parse_zero_shot_reference_subject_binding_receipt(
    value: Mapping[str, Any],
) -> ZeroShotReferenceSubjectBindingReceipt:
    body_fields = {
        "schema",
        "record_type",
        "task_owner",
        "project_id",
        "voice_profile_id",
        "voice_profile_revision_sha256",
        "consent_sha256",
        "consent_subject_ref_sha256",
        "reference_asset_id",
        "reference_asset_checksum_sha256",
        "asset_revision_binding_ref",
        "asset_revision_binding_sha256",
        "reference_profile_ref",
        "reference_profile_sha256",
        "capture_lineage_ref",
        "capture_lineage_sha256",
        "consent_current_evaluation_sha256",
        "rights_current_evaluation_sha256",
        "authority_kind",
        "subject_match_decision",
        "subject_match_evidence_ref",
        "subject_match_evidence_sha256",
        "evaluated_at",
        "expires_at",
        "usage_scope",
        "audio_body_persisted",
        "speaker_embedding_persisted",
        "private_subject_ref_persisted",
        "host_path_persisted",
    }
    _expect_keys(value, body_fields | {"receipt_id", "receipt_sha256"}, "ZeroShotReferenceSubjectBindingReceipt")
    if value["schema"] != SUBJECT_RECEIPT_SCHEMA_ID or value["record_type"] != "ZeroShotReferenceSubjectBindingReceipt" or value["task_owner"] != "TASK-014":
        raise ValueError("subject receipt identity is invalid")
    kwargs = {key: value[key] for key in body_fields - {"schema", "record_type", "task_owner"}}
    return ZeroShotReferenceSubjectBindingReceipt(
        receipt_id=value["receipt_id"],
        receipt_sha256=value["receipt_sha256"],
        **kwargs,
    )


def parse_canonical_narration_plan_revision_receipt(
    value: Mapping[str, Any],
) -> CanonicalNarrationPlanRevisionReceipt:
    body_fields = {
        "schema",
        "record_type",
        "task_owner",
        "project_id",
        "plan_id",
        "plan_revision",
        "parent_plan_revision_sha256",
        "plan_sha256",
        "approved_text_revision_ref",
        "approved_text_revision_sha256",
        "approved_script_body_sha256",
        "source_text_binding_sha256",
        "voice_profile_id",
        "voice_profile_revision_sha256",
        "route_mode",
        "mode",
        "model_id",
        "language_code",
        "normalization_policy_id",
        "normalization_policy_revision",
        "normalization_policy_sha256",
        "chunking_policy_id",
        "chunking_policy_revision",
        "chunking_policy_sha256",
        "compiler_code_revision_sha256",
        "ordered_chunk_manifest_sha256",
        "chunk_count",
        "plan_store_ref",
        "plan_store_revision",
        "plan_store_record_sha256",
        "authority_kind",
        "derivation_decision",
        "derivation_evidence_ref",
        "derivation_evidence_sha256",
        "evaluated_at",
        "expires_at",
        "script_body_persisted",
        "chunk_body_persisted",
        "host_path_persisted",
        "execution_authorized",
    }
    _expect_keys(value, body_fields | {"receipt_id", "receipt_sha256"}, "CanonicalNarrationPlanRevisionReceipt")
    if value["schema"] != PLAN_RECEIPT_SCHEMA_ID or value["record_type"] != "CanonicalNarrationPlanRevisionReceipt" or value["task_owner"] != "TASK-014":
        raise ValueError("plan receipt identity is invalid")
    kwargs = {key: value[key] for key in body_fields - {"schema", "record_type", "task_owner"}}
    return CanonicalNarrationPlanRevisionReceipt(
        receipt_id=value["receipt_id"],
        receipt_sha256=value["receipt_sha256"],
        **kwargs,
    )


def parse_zero_shot_callable_envelope(value: Mapping[str, Any]) -> ZeroShotCallableEnvelope:
    flags = set(_ENVELOPE_FALSE_FLAGS)
    fields = {
        "schema",
        "record_type",
        "task_owner",
        "envelope_id",
        "envelope_sha256",
        *_ENVELOPE_BODY_FIELDS,
    }
    _expect_keys(value, fields | flags, "ZeroShotCallableEnvelope")
    if value["schema"] != SCHEMA_ID or value["record_type"] != "ZeroShotCallableEnvelope" or value["task_owner"] != "TASK-014" or any(value[flag] is not False for flag in flags):
        raise ValueError("callable envelope identity or no-effect boundary is invalid")
    reasons = value["reason_codes"]
    if not isinstance(reasons, list):
        raise ValueError("reason_codes must be a list")
    kwargs = {key: value[key] for key in fields - {"schema", "record_type", "task_owner", "reason_codes"}}
    return ZeroShotCallableEnvelope(
        **kwargs,
        reason_codes=tuple(reasons),
    )


__all__ = [
    "SCHEMA_ID",
    "SUBJECT_RECEIPT_SCHEMA_ID",
    "PLAN_RECEIPT_SCHEMA_ID",
    "SubjectBindingAuthorityKind",
    "SubjectMatchDecision",
    "PlanDerivationAuthorityKind",
    "PlanDerivationDecision",
    "CallableEnvelopeDecision",
    "ZeroShotReferenceSubjectBindingReceipt",
    "CanonicalNarrationPlanRevisionReceipt",
    "ZeroShotCallableEnvelope",
    "parse_zero_shot_reference_subject_binding_receipt",
    "parse_canonical_narration_plan_revision_receipt",
    "compile_zero_shot_callable_envelope",
    "parse_zero_shot_callable_envelope",
]
