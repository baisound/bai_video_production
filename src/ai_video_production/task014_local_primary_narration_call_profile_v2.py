"""Pure TASK-014 D4/R1 local narration call-profile evidence.

The profile is a strict, body-free projection over an already compiled V1
zero-shot callable envelope plus the current TASK-014 preflight and render
admission.  It does not mint the live call capability or output sink and has
no file, model, provider, process, audio, GPU, or native side effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import re

from .owner_narration import NarrationGenerationPlan
from .owner_narration_local_primary import (
    LocalNarrationRouteMode,
    LocalPrimaryNarrationPreflight,
    NarrationIntendedUsage,
    PreflightDecision,
    parse_local_primary_preflight,
)
from .owner_narration_local_render_admission import (
    LocalPrimaryNarrationRenderAdmission,
    RenderAdmissionDecision,
    parse_render_admission,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .task014_zero_shot_callable_contract import (
    CALLABLE_BLOCKER_REASON_CODES,
    CALLABLE_REASON_CODES,
    CALLABLE_UNKNOWN_REASON_CODES,
    V1_CURRENTNESS_CLOSURE_REASONS,
    CanonicalNarrationPlanRevisionReceipt,
    CallableEnvelopeDecision,
    PlanDerivationDecision,
    ReferenceTranscriptDecision,
    SubjectMatchDecision,
    ZeroShotCallableEnvelope,
    ZeroShotReferenceSubjectBindingReceipt,
    ZeroShotReferenceTranscriptBindingReceipt,
    callable_plan_currentness_facts,
    callable_surface_sha256,
    parse_canonical_narration_plan_revision_receipt,
    parse_zero_shot_callable_envelope,
    parse_zero_shot_reference_subject_binding_receipt,
    parse_zero_shot_reference_transcript_binding_receipt,
)


SCHEMA_ID = "bai.task014.local-primary-narration-call-profile.v2"
RECORD_TYPE = "LocalPrimaryNarrationCallProfileV2"
TASK_OWNER = "TASK-014"
RECEIPT_TYPE = "LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2"
SCHEMA_VERSION = 2

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")
_RFC3339_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "private-key")
_REQUIRED_ARTIFACT_CLASS = "STAGED_NARRATION_PCM_WAV_48000_MONO"
_REQUIRED_SAMPLE_RATE_HZ = 48_000
_REQUIRED_CHANNELS = 1
_REQUIRED_SAMPLE_FORMAT = "PCM_S24LE"

_PROFILE_SPECIFIC_BLOCKERS = frozenset(
    {
        "CALLABLE_ENVELOPE_BINDING_MISMATCH",
        "CALLABLE_EVIDENCE_EXPIRED",
        "CALL_PROFILE_TIME_ORDER_MISMATCH",
    }
)
REASON_CODES = frozenset(CALLABLE_REASON_CODES | _PROFILE_SPECIFIC_BLOCKERS)

# D4 field order with the R1 route_mode/intended_usage insertion.  Keeping this
# tuple explicit makes missing, extra, or reordered mappings fail closed.
PROFILE_FIELDS = (
    "schema",
    "record_type",
    "task_owner",
    "profile_id",
    "profile_revision",
    "route_mode",
    "intended_usage",
    "parent_profile_sha256",
    "compiled_at",
    "expires_at",
    "project_id",
    "project_manifest_revision",
    "project_manifest_sha256",
    "installed_session_sha256",
    "operation_plan_id",
    "operation_plan_sha256",
    "callable_envelope_id",
    "callable_envelope_sha256",
    "render_admission_sha256",
    "preflight_sha256",
    "canonical_plan_sha256",
    "subject_binding_receipt_sha256",
    "plan_derivation_receipt_sha256",
    "reference_transcript_receipt_sha256",
    "reference_transcript_revision_sha256",
    "reference_transcript_body_sha256",
    "script_text_revision_sha256",
    "preview_call_text_body_sha256",
    "voice_profile_revision_sha256",
    "route_selection_revision_sha256",
    "registered_job_revision_sha256",
    "render_operation_identity_sha256",
    "authorization_sha256",
    "engine_revision_sha256",
    "model_artifact_sha256",
    "runtime_sha256",
    "code_revision_sha256",
    "reference_asset_checksum_sha256",
    "reference_profile_sha256",
    "destination_policy_sha256",
    "call_surface_sha256",
    "required_artifact_class",
    "required_sample_rate_hz",
    "required_channels",
    "required_sample_format",
    "max_attempts",
    "automatic_retry_allowed",
    "fixture_lineage_sha256",
    "decision",
    "reason_codes",
    "profile_sha256",
)


class CallProfileDecision(str, Enum):
    READY_FOR_TASK075_DISPATCH = "READY_FOR_TASK075_DISPATCH"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


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


def _nullable_digest(value: Any, name: str) -> str | None:
    return None if value is None else _digest(value, name)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 2_147_483_647:
        raise ValueError(f"{name} must be a bounded positive integer")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339_UTC_RE.fullmatch(value):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        instant = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if instant.tzinfo != timezone.utc:
        raise ValueError(f"{name} must be RFC3339 UTC")
    return instant


def _enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _profile_preimage(values: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for field in PROFILE_FIELDS[:-1]:
        value = values[field]
        if isinstance(value, Enum):
            value = value.value
        elif field == "reason_codes":
            value = list(value)
        body[field] = value
    return body


@dataclass(frozen=True, slots=True)
class LocalPrimaryNarrationCallProfileV2:
    profile_id: str
    profile_revision: int
    route_mode: LocalNarrationRouteMode
    intended_usage: NarrationIntendedUsage
    parent_profile_sha256: str | None
    compiled_at: str
    expires_at: str
    project_id: str
    project_manifest_revision: int
    project_manifest_sha256: str
    installed_session_sha256: str
    operation_plan_id: str
    operation_plan_sha256: str
    callable_envelope_id: str
    callable_envelope_sha256: str
    render_admission_sha256: str
    preflight_sha256: str
    canonical_plan_sha256: str
    subject_binding_receipt_sha256: str
    plan_derivation_receipt_sha256: str
    reference_transcript_receipt_sha256: str
    reference_transcript_revision_sha256: str
    reference_transcript_body_sha256: str
    script_text_revision_sha256: str
    preview_call_text_body_sha256: str
    voice_profile_revision_sha256: str
    route_selection_revision_sha256: str
    registered_job_revision_sha256: str
    render_operation_identity_sha256: str
    authorization_sha256: str
    engine_revision_sha256: str
    model_artifact_sha256: str
    runtime_sha256: str
    code_revision_sha256: str
    reference_asset_checksum_sha256: str
    reference_profile_sha256: str
    destination_policy_sha256: str
    call_surface_sha256: str
    required_artifact_class: str
    required_sample_rate_hz: int
    required_channels: int
    required_sample_format: str
    max_attempts: int
    automatic_retry_allowed: bool
    fixture_lineage_sha256: str
    decision: CallProfileDecision
    reason_codes: tuple[str, ...]
    profile_sha256: str

    def __post_init__(self) -> None:
        for name in ("profile_id", "project_id", "operation_plan_id", "callable_envelope_id"):
            _id(getattr(self, name), name)
        _positive_int(self.profile_revision, "profile_revision")
        _positive_int(self.project_manifest_revision, "project_manifest_revision")
        if (self.profile_revision == 1) != (self.parent_profile_sha256 is None):
            raise ValueError("parent_profile_sha256 must be null only for revision 1")
        _nullable_digest(self.parent_profile_sha256, "parent_profile_sha256")
        compiled = _timestamp(self.compiled_at, "compiled_at")
        expires = _timestamp(self.expires_at, "expires_at")
        if expires <= compiled:
            raise ValueError("expires_at must be later than compiled_at")
        for name in (
            "project_manifest_sha256",
            "installed_session_sha256",
            "operation_plan_sha256",
            "callable_envelope_sha256",
            "render_admission_sha256",
            "preflight_sha256",
            "canonical_plan_sha256",
            "subject_binding_receipt_sha256",
            "plan_derivation_receipt_sha256",
            "reference_transcript_receipt_sha256",
            "reference_transcript_revision_sha256",
            "reference_transcript_body_sha256",
            "script_text_revision_sha256",
            "preview_call_text_body_sha256",
            "voice_profile_revision_sha256",
            "route_selection_revision_sha256",
            "registered_job_revision_sha256",
            "render_operation_identity_sha256",
            "authorization_sha256",
            "engine_revision_sha256",
            "model_artifact_sha256",
            "runtime_sha256",
            "code_revision_sha256",
            "reference_asset_checksum_sha256",
            "reference_profile_sha256",
            "destination_policy_sha256",
            "call_surface_sha256",
            "fixture_lineage_sha256",
            "profile_sha256",
        ):
            _digest(getattr(self, name), name)
        object.__setattr__(self, "route_mode", _enum(LocalNarrationRouteMode, self.route_mode, "route_mode"))
        object.__setattr__(self, "intended_usage", _enum(NarrationIntendedUsage, self.intended_usage, "intended_usage"))
        object.__setattr__(self, "decision", _enum(CallProfileDecision, self.decision, "decision"))
        if self.route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL:
            raise ValueError("route_mode must be ZERO_SHOT_LOCAL")
        if self.intended_usage is not NarrationIntendedUsage.PREVIEW:
            raise ValueError("intended_usage must be PREVIEW")
        if (
            self.required_artifact_class != _REQUIRED_ARTIFACT_CLASS
            or self.required_sample_rate_hz != _REQUIRED_SAMPLE_RATE_HZ
            or self.required_channels != _REQUIRED_CHANNELS
            or self.required_sample_format != _REQUIRED_SAMPLE_FORMAT
            or self.max_attempts != 1
            or self.automatic_retry_allowed is not False
        ):
            raise ValueError("call-profile execution bounds are invalid")
        if (
            len(self.reason_codes) > 64
            or tuple(sorted(set(self.reason_codes))) != self.reason_codes
            or any(reason not in REASON_CODES for reason in self.reason_codes)
        ):
            raise ValueError("reason_codes are invalid")
        blockers = set(self.reason_codes) & (CALLABLE_BLOCKER_REASON_CODES | _PROFILE_SPECIFIC_BLOCKERS)
        unknowns = set(self.reason_codes) & CALLABLE_UNKNOWN_REASON_CODES
        if self.decision is CallProfileDecision.READY_FOR_TASK075_DISPATCH:
            if self.reason_codes:
                raise ValueError("READY profile cannot carry reason_codes")
        elif self.decision is CallProfileDecision.BLOCKED:
            if not blockers:
                raise ValueError("BLOCKED profile requires a blocker reason")
        elif not unknowns or blockers:
            raise ValueError("UNKNOWN profile requires only unknown reasons")
        expected = sha256_bytes(canonical_json_bytes(_profile_preimage(self._values())))
        if self.profile_sha256 != expected:
            raise ValueError("profile_sha256 does not match the exact V2 preimage")

    def _values(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "record_type": RECORD_TYPE,
            "task_owner": TASK_OWNER,
            **{
                field: getattr(self, field)
                for field in PROFILE_FIELDS[3:]
            },
        }

    def to_dict(self) -> dict[str, Any]:
        values = self._values()
        return {
            field: (
                values[field].value
                if isinstance(values[field], Enum)
                else list(values[field])
                if field == "reason_codes"
                else values[field]
            )
            for field in PROFILE_FIELDS
        }

    def to_task073_receipt_ref(
        self,
        *,
        producer_build_sha256: str,
        quick_clone_flow_sha256: str,
    ) -> dict[str, Any]:
        """Project the Evidence into TASK-073's closed receipt slot.

        The serializable profile remains non-capability Evidence, so this
        projection never claims authority or production eligibility.
        """

        return {
            "owner_task": TASK_OWNER,
            "receipt_type": RECEIPT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "opaque_ref": self.profile_id,
            "receipt_sha256": self.profile_sha256,
            "producer_build_sha256": _digest(producer_build_sha256, "producer_build_sha256"),
            "producer_state": self.decision.value,
            "candidate_id": None,
            "candidate_sha256": None,
            "project_id": self.project_id,
            "project_manifest_sha256": self.project_manifest_sha256,
            "installed_session_sha256": self.installed_session_sha256,
            "operation_plan_sha256": self.operation_plan_sha256,
            "quick_clone_flow_sha256": _digest(quick_clone_flow_sha256, "quick_clone_flow_sha256"),
            "revision": self.profile_revision,
            "head_sha256": self.profile_sha256,
            "observed_at": self.compiled_at,
            "expires_at": self.expires_at,
            "current": True,
            "fixture_only": False,
            "authority_created": False,
            "production_eligible": False,
        }


def _require_bound_envelope(envelope: ZeroShotCallableEnvelope) -> None:
    required = (
        "preflight_id",
        "preflight_sha256",
        "subject_binding_receipt_sha256",
        "plan_derivation_receipt_sha256",
        "reference_transcript_receipt_sha256",
        "reference_transcript_revision_sha256",
        "reference_transcript_body_sha256",
        "preview_call_text_body_sha256",
        "registered_job_id",
        "registered_job_revision_sha256",
        "render_operation_identity_sha256",
        "authorization_id",
        "authorization_revision",
        "authorization_sha256",
        "engine_id",
        "engine_revision_sha256",
        "model_artifact_id",
        "model_artifact_sha256",
        "runtime_id",
        "runtime_sha256",
        "code_revision_sha256",
        "reference_asset_id",
        "reference_asset_checksum_sha256",
        "asset_revision_binding_ref",
        "asset_revision_binding_sha256",
        "reference_profile_ref",
        "reference_profile_sha256",
        "destination_id",
        "destination_policy_sha256",
    )
    if any(getattr(envelope, field) is None for field in required):
        raise ValueError("callable envelope is not fully bound for the V2 profile")


def _binding_reasons(
    envelope: ZeroShotCallableEnvelope,
    admission: LocalPrimaryNarrationRenderAdmission,
    preflight: LocalPrimaryNarrationPreflight,
    compiled: datetime,
    profile_expires: datetime,
) -> set[str]:
    reasons: set[str] = set()
    job = admission.durable_job_binding
    authorization = admission.execution_authorization_binding
    destination = admission.output_destination_binding
    if (
        envelope.project_id != admission.project_id
        or envelope.project_id != preflight.project_id
        or envelope.admission_id != admission.admission_id
        or envelope.admission_revision != admission.revision
        or envelope.admission_sha256 != admission.admission_sha256
        or envelope.preflight_id != preflight.preflight_id
        or envelope.preflight_sha256 != preflight.preflight_sha256
        or envelope.preflight_sha256 != admission.preflight_binding.preflight_sha256
        or envelope.route_mode is not admission.route_mode
        or envelope.route_mode is not preflight.route_mode
        or envelope.intended_usage is not admission.intended_usage
        or envelope.intended_usage is not preflight.intended_usage
        or envelope.script_text_revision_sha256 != admission.script_text_revision_sha256
        or envelope.voice_profile_revision_sha256 != admission.voice_profile_revision_sha256
        or envelope.registered_job_id != job.job_id
        or envelope.registered_job_revision_sha256 != job.job_revision_sha256
        or envelope.render_operation_identity_sha256 != job.operation_identity_sha256
        or envelope.authorization_id != authorization.authorization_id
        or envelope.authorization_revision != authorization.authorization_revision
        or envelope.authorization_sha256 != authorization.authorization_sha256
        or envelope.destination_id != destination.destination_id
        or envelope.destination_policy_sha256 != destination.storage_policy_sha256
    ):
        reasons.add("CALLABLE_ENVELOPE_BINDING_MISMATCH")
    engine = preflight.engine_admission_binding
    zero = preflight.zero_shot_reference_binding
    if (
        envelope.engine_id != engine.get("engine_id")
        or envelope.engine_revision_sha256 != engine.get("engine_revision_sha256")
        or envelope.model_artifact_id != engine.get("model_artifact_id")
        or envelope.model_artifact_sha256 != engine.get("model_artifact_sha256")
        or envelope.runtime_id != engine.get("runtime_id")
        or envelope.runtime_sha256 != engine.get("runtime_sha256")
        or envelope.code_revision_sha256 != engine.get("code_revision_sha256")
        or zero is None
        or envelope.reference_asset_id != zero.get("asset_id")
        or envelope.reference_asset_checksum_sha256 != zero.get("asset_checksum_sha256")
        or envelope.asset_revision_binding_ref != zero.get("asset_revision_binding_ref")
        or envelope.asset_revision_binding_sha256 != zero.get("asset_revision_binding_sha256")
        or envelope.reference_profile_ref != zero.get("reference_profile_ref")
        or envelope.reference_profile_sha256 != zero.get("reference_profile_sha256")
    ):
        reasons.add("CALLABLE_ENVELOPE_BINDING_MISMATCH")
    if (
        admission.decision is not RenderAdmissionDecision.READY_FOR_EXTERNAL_DISPATCH_GATE
        or preflight.decision is not PreflightDecision.READY_FOR_OWNER_HUMAN_GATE
    ):
        reasons.add("ADMISSION_NOT_READY")
    if compiled < _timestamp(envelope.compiled_at, "callable_envelope.compiled_at"):
        reasons.add("CALL_PROFILE_TIME_ORDER_MISMATCH")
    evidence_times = (
        preflight.created_at,
        admission.created_at,
        admission.preflight_binding.evaluated_at,
        admission.resource_admission_binding.evaluated_at,
        authorization.issued_at,
    )
    if any(
        value is not None and compiled < _timestamp(value, "evidence evaluated_at")
        for value in evidence_times
    ):
        reasons.add("CALL_PROFILE_TIME_ORDER_MISMATCH")
    for expiry_value in (
        admission.preflight_binding.expires_at,
        admission.resource_admission_binding.expires_at,
        authorization.expires_at,
    ):
        if expiry_value is None:
            continue
        evidence_expiry = _timestamp(expiry_value, "evidence expires_at")
        if compiled >= evidence_expiry or profile_expires > evidence_expiry:
            reasons.add("CALLABLE_EVIDENCE_EXPIRED")
    return reasons


def _current_receipt_reasons(
    envelope: ZeroShotCallableEnvelope,
    subject: ZeroShotReferenceSubjectBindingReceipt,
    plan: CanonicalNarrationPlanRevisionReceipt,
    transcript: ZeroShotReferenceTranscriptBindingReceipt,
    plan_facts: Mapping[str, Any],
    preflight: LocalPrimaryNarrationPreflight,
    compiled: datetime,
    profile_expires: datetime,
) -> tuple[set[str], set[str]]:
    blockers: set[str] = set()
    unknowns: set[str] = set()
    voice = preflight.voice_profile_revision_binding
    rights = preflight.rights_evaluation_binding
    script = preflight.script_text_binding
    if (
        subject.receipt_sha256 != envelope.subject_binding_receipt_sha256
        or subject.project_id != envelope.project_id
        or subject.voice_profile_id != envelope.voice_profile_id
        or subject.voice_profile_revision_sha256 != envelope.voice_profile_revision_sha256
        or subject.reference_asset_id != envelope.reference_asset_id
        or subject.reference_asset_checksum_sha256 != envelope.reference_asset_checksum_sha256
        or subject.asset_revision_binding_ref != envelope.asset_revision_binding_ref
        or subject.asset_revision_binding_sha256 != envelope.asset_revision_binding_sha256
        or subject.reference_profile_ref != envelope.reference_profile_ref
        or subject.reference_profile_sha256 != envelope.reference_profile_sha256
        or subject.consent_sha256 != voice.get("consent", {}).get("consent_sha256")
        or subject.consent_current_evaluation_sha256 != voice.get("current_consent_evaluation_sha256")
        or subject.rights_current_evaluation_sha256 != rights.get("evidence_sha256")
    ):
        blockers.add("SUBJECT_BINDING_MISMATCH")
    if subject.subject_match_decision is SubjectMatchDecision.UNKNOWN:
        unknowns.add("SUBJECT_BINDING_UNKNOWN")
    elif subject.subject_match_decision is not SubjectMatchDecision.VERIFIED_SAME_SUBJECT:
        blockers.add("SUBJECT_BINDING_MISMATCH")

    if (
        plan.receipt_sha256 != envelope.plan_derivation_receipt_sha256
        or plan.project_id != envelope.project_id
        or plan.plan_id != envelope.plan_id
        or plan.plan_sha256 != envelope.plan_sha256
        or plan.plan_id != plan_facts["plan_id"]
        or plan.plan_sha256 != plan_facts["plan_sha256"]
        or plan.approved_text_revision_ref != script.get("approved_text_revision_ref")
        or plan.approved_text_revision_sha256 != script.get("approved_text_revision_sha256")
        or plan.source_text_binding_sha256 != script.get("source_text_binding_sha256")
        or plan.approved_script_body_sha256 != plan_facts["script_text_revision_sha256"]
        or plan.approved_script_body_sha256 != envelope.script_text_revision_sha256
        or plan.approved_text_code_point_count != plan_facts["preview_text_code_point_count"]
        or plan.ordered_chunk_manifest_sha256 != plan_facts["ordered_chunk_manifest_sha256"]
        or plan.chunk_count != plan_facts["chunk_count"]
        or plan.voice_profile_id != envelope.voice_profile_id
        or plan.voice_profile_revision_sha256 != envelope.voice_profile_revision_sha256
        or plan.route_mode is not envelope.route_mode
        or plan.model_id != plan_facts["model_id"]
        or plan.model_id != envelope.engine_id
        or plan.language_code != plan_facts["language_code"]
        or plan.language_code != envelope.product_language_code
        or plan_facts["preview_call_text_body_sha256"] != envelope.preview_call_text_body_sha256
        or plan_facts["preview_text_code_point_count"] != envelope.preview_text_code_point_count
    ):
        blockers.add("PLAN_DERIVATION_MISMATCH")
    if plan.derivation_decision is PlanDerivationDecision.UNKNOWN:
        unknowns.add("PLAN_DERIVATION_UNKNOWN")
    elif plan.derivation_decision is not PlanDerivationDecision.VERIFIED_FROM_APPROVED_BODY:
        blockers.add("PLAN_DERIVATION_MISMATCH")

    if (
        transcript.receipt_sha256 != envelope.reference_transcript_receipt_sha256
        or transcript.project_id != envelope.project_id
        or transcript.voice_profile_id != envelope.voice_profile_id
        or transcript.voice_profile_revision_sha256 != envelope.voice_profile_revision_sha256
        or transcript.reference_asset_id != envelope.reference_asset_id
        or transcript.reference_asset_checksum_sha256 != envelope.reference_asset_checksum_sha256
        or transcript.asset_revision_binding_ref != envelope.asset_revision_binding_ref
        or transcript.asset_revision_binding_sha256 != envelope.asset_revision_binding_sha256
        or transcript.reference_profile_ref != envelope.reference_profile_ref
        or transcript.reference_profile_sha256 != envelope.reference_profile_sha256
        or transcript.transcript_revision_sha256 != envelope.reference_transcript_revision_sha256
        or transcript.transcript_body_sha256 != envelope.reference_transcript_body_sha256
        or transcript.transcript_language_code != envelope.product_language_code
        or transcript.consent_current_evaluation_sha256 != voice.get("current_consent_evaluation_sha256")
        or transcript.rights_current_evaluation_sha256 != rights.get("evidence_sha256")
    ):
        blockers.add("REFERENCE_TRANSCRIPT_BINDING_MISMATCH")
    if transcript.transcript_decision is ReferenceTranscriptDecision.UNKNOWN:
        unknowns.add("REFERENCE_TRANSCRIPT_UNKNOWN")
    elif transcript.transcript_decision is not ReferenceTranscriptDecision.VERIFIED_EXACT_TRANSCRIPT:
        blockers.add("REFERENCE_TRANSCRIPT_MISMATCH")

    evidence_times = (subject.evaluated_at, plan.evaluated_at, transcript.evaluated_at)
    if any(compiled < _timestamp(value, "receipt evaluated_at") for value in evidence_times):
        blockers.add("CALL_PROFILE_TIME_ORDER_MISMATCH")
    expiries = tuple(
        _timestamp(value, "receipt expires_at")
        for value in (subject.expires_at, plan.expires_at, transcript.expires_at)
        if value is not None
    )
    if any(compiled >= expiry or profile_expires > expiry for expiry in expiries):
        blockers.add("CALLABLE_EVIDENCE_EXPIRED")
    return blockers, unknowns


def compile_local_primary_narration_call_profile_v2(
    *,
    profile_id: str,
    profile_revision: int,
    parent_profile_sha256: str | None,
    compiled_at: str,
    expires_at: str,
    project_manifest_revision: int,
    project_manifest_sha256: str,
    installed_session_sha256: str,
    operation_plan_id: str,
    operation_plan_sha256: str,
    route_selection_revision_sha256: str,
    fixture_lineage_sha256: str,
    callable_envelope: ZeroShotCallableEnvelope,
    render_admission: LocalPrimaryNarrationRenderAdmission,
    preflight: LocalPrimaryNarrationPreflight,
    subject_binding_receipt: ZeroShotReferenceSubjectBindingReceipt,
    plan_derivation_receipt: CanonicalNarrationPlanRevisionReceipt,
    reference_transcript_receipt: ZeroShotReferenceTranscriptBindingReceipt,
    narration_plan: NarrationGenerationPlan,
) -> LocalPrimaryNarrationCallProfileV2:
    """Compile one immutable V2 Evidence profile with no effect authority."""

    if type(callable_envelope) is not ZeroShotCallableEnvelope:
        raise TypeError("callable_envelope must be an exact ZeroShotCallableEnvelope")
    if type(render_admission) is not LocalPrimaryNarrationRenderAdmission:
        raise TypeError("render_admission must be an exact LocalPrimaryNarrationRenderAdmission")
    if type(preflight) is not LocalPrimaryNarrationPreflight:
        raise TypeError("preflight must be an exact LocalPrimaryNarrationPreflight")
    if type(subject_binding_receipt) is not ZeroShotReferenceSubjectBindingReceipt:
        raise TypeError("subject_binding_receipt must be an exact typed receipt")
    if type(plan_derivation_receipt) is not CanonicalNarrationPlanRevisionReceipt:
        raise TypeError("plan_derivation_receipt must be an exact typed receipt")
    if type(reference_transcript_receipt) is not ZeroShotReferenceTranscriptBindingReceipt:
        raise TypeError("reference_transcript_receipt must be an exact typed receipt")
    if type(narration_plan) is not NarrationGenerationPlan:
        raise TypeError("narration_plan must be an exact NarrationGenerationPlan")
    envelope = parse_zero_shot_callable_envelope(callable_envelope.to_private_dict())
    admission = parse_render_admission(render_admission.to_private_dict())
    current_preflight = parse_local_primary_preflight(preflight.to_private_dict())
    subject = parse_zero_shot_reference_subject_binding_receipt(subject_binding_receipt.to_private_dict())
    plan = parse_canonical_narration_plan_revision_receipt(plan_derivation_receipt.to_private_dict())
    transcript = parse_zero_shot_reference_transcript_binding_receipt(reference_transcript_receipt.to_private_dict())
    plan_facts = callable_plan_currentness_facts(narration_plan)
    _require_bound_envelope(envelope)
    compiled = _timestamp(compiled_at, "compiled_at")
    expiry = _timestamp(expires_at, "expires_at")
    if expiry <= compiled:
        raise ValueError("expires_at must be later than compiled_at")
    if envelope.route_mode is not LocalNarrationRouteMode.ZERO_SHOT_LOCAL:
        raise ValueError("V2 cannot relabel a non-zero-shot V1 envelope")
    if envelope.intended_usage is not NarrationIntendedUsage.PREVIEW:
        raise ValueError("V2 cannot relabel a non-preview V1 envelope")

    blocked = _binding_reasons(
        envelope,
        admission,
        current_preflight,
        compiled,
        expiry,
    )
    receipt_blockers, receipt_unknowns = _current_receipt_reasons(
        envelope,
        subject,
        plan,
        transcript,
        plan_facts,
        current_preflight,
        compiled,
        expiry,
    )
    blocked.update(receipt_blockers)
    if envelope.decision is CallableEnvelopeDecision.BLOCKED:
        blocked.update(envelope.reason_codes)
    unknown = (set(envelope.reason_codes) - V1_CURRENTNESS_CLOSURE_REASONS) | receipt_unknowns
    if blocked:
        decision = CallProfileDecision.BLOCKED
        reasons = tuple(sorted(blocked | unknown))
    elif unknown:
        decision = CallProfileDecision.UNKNOWN
        reasons = tuple(sorted(unknown))
    elif set(envelope.reason_codes) == V1_CURRENTNESS_CLOSURE_REASONS:
        decision = CallProfileDecision.READY_FOR_TASK075_DISPATCH
        reasons = ()
    else:
        decision = CallProfileDecision.UNKNOWN
        reasons = ("CANONICAL_AUTHORITY_NOT_CONFIRMED",)

    values: dict[str, Any] = {
        "profile_id": profile_id,
        "profile_revision": profile_revision,
        "route_mode": envelope.route_mode,
        "intended_usage": envelope.intended_usage,
        "parent_profile_sha256": parent_profile_sha256,
        "compiled_at": compiled_at,
        "expires_at": expires_at,
        "project_id": envelope.project_id,
        "project_manifest_revision": project_manifest_revision,
        "project_manifest_sha256": project_manifest_sha256,
        "installed_session_sha256": installed_session_sha256,
        "operation_plan_id": operation_plan_id,
        "operation_plan_sha256": operation_plan_sha256,
        "callable_envelope_id": envelope.envelope_id,
        "callable_envelope_sha256": envelope.envelope_sha256,
        "render_admission_sha256": admission.admission_sha256,
        "preflight_sha256": current_preflight.preflight_sha256,
        "canonical_plan_sha256": envelope.plan_sha256,
        "subject_binding_receipt_sha256": envelope.subject_binding_receipt_sha256,
        "plan_derivation_receipt_sha256": envelope.plan_derivation_receipt_sha256,
        "reference_transcript_receipt_sha256": envelope.reference_transcript_receipt_sha256,
        "reference_transcript_revision_sha256": envelope.reference_transcript_revision_sha256,
        "reference_transcript_body_sha256": envelope.reference_transcript_body_sha256,
        "script_text_revision_sha256": envelope.script_text_revision_sha256,
        "preview_call_text_body_sha256": envelope.preview_call_text_body_sha256,
        "voice_profile_revision_sha256": envelope.voice_profile_revision_sha256,
        "route_selection_revision_sha256": route_selection_revision_sha256,
        "registered_job_revision_sha256": envelope.registered_job_revision_sha256,
        "render_operation_identity_sha256": envelope.render_operation_identity_sha256,
        "authorization_sha256": envelope.authorization_sha256,
        "engine_revision_sha256": envelope.engine_revision_sha256,
        "model_artifact_sha256": envelope.model_artifact_sha256,
        "runtime_sha256": envelope.runtime_sha256,
        "code_revision_sha256": envelope.code_revision_sha256,
        "reference_asset_checksum_sha256": envelope.reference_asset_checksum_sha256,
        "reference_profile_sha256": envelope.reference_profile_sha256,
        "destination_policy_sha256": envelope.destination_policy_sha256,
        "call_surface_sha256": callable_surface_sha256(envelope),
        "required_artifact_class": _REQUIRED_ARTIFACT_CLASS,
        "required_sample_rate_hz": _REQUIRED_SAMPLE_RATE_HZ,
        "required_channels": _REQUIRED_CHANNELS,
        "required_sample_format": _REQUIRED_SAMPLE_FORMAT,
        "max_attempts": 1,
        "automatic_retry_allowed": False,
        "fixture_lineage_sha256": fixture_lineage_sha256,
        "decision": decision,
        "reason_codes": reasons,
        "profile_sha256": "sha256:" + "0" * 64,
    }
    preimage = {
        "schema": SCHEMA_ID,
        "record_type": RECORD_TYPE,
        "task_owner": TASK_OWNER,
        **values,
    }
    values["profile_sha256"] = sha256_bytes(
        canonical_json_bytes(_profile_preimage(preimage))
    )
    return LocalPrimaryNarrationCallProfileV2(**values)


def parse_local_primary_narration_call_profile_v2(
    value: Mapping[str, Any],
) -> LocalPrimaryNarrationCallProfileV2:
    if not isinstance(value, Mapping) or tuple(value) != PROFILE_FIELDS:
        raise ValueError("call profile fields are incomplete, unknown, or reordered")
    if (
        value["schema"] != SCHEMA_ID
        or value["record_type"] != RECORD_TYPE
        or value["task_owner"] != TASK_OWNER
    ):
        raise ValueError("call profile identity is invalid")
    if not isinstance(value["reason_codes"], list):
        raise ValueError("reason_codes must be a list")
    return LocalPrimaryNarrationCallProfileV2(
        **{
            field: tuple(value[field]) if field == "reason_codes" else value[field]
            for field in PROFILE_FIELDS[3:]
        }
    )


__all__ = [
    "SCHEMA_ID",
    "RECORD_TYPE",
    "TASK_OWNER",
    "RECEIPT_TYPE",
    "SCHEMA_VERSION",
    "PROFILE_FIELDS",
    "REASON_CODES",
    "CallProfileDecision",
    "LocalPrimaryNarrationCallProfileV2",
    "compile_local_primary_narration_call_profile_v2",
    "parse_local_primary_narration_call_profile_v2",
]
