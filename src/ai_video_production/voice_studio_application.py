"""Pure, non-executing TASK-046 Voice Studio metadata preflight."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes
from .voice_profile_revision import (
    ArtifactAdmissionState,
    CapabilityProbeState,
    ConsentState,
    ModelLicenseClass,
    VoiceProfileRevision,
    _id,
)


class VoiceStudioPreflightStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class VoiceStudioPreflightReport:
    voice_profile_id: str
    canonical_narration_profile_sha256: str
    revision: int
    voice_profile_revision_sha256: str
    requested_language: str
    requested_usage_class: str
    requested_capability: str
    commercial_use_required: bool
    status: VoiceStudioPreflightStatus
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        body = {
            "preflight_version": "1.0.0",
            "task_owner": "TASK-046",
            "voice_profile_id": self.voice_profile_id,
            "canonical_narration_profile_sha256": self.canonical_narration_profile_sha256,
            "revision": self.revision,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "requested_language": self.requested_language,
            "requested_usage_class": self.requested_usage_class,
            "requested_capability": self.requested_capability,
            "commercial_use_required": self.commercial_use_required,
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "metadata_ready": self.status is VoiceStudioPreflightStatus.READY,
            "execution_authorized": False,
            "runtime_probe_started": False,
            "model_load_started": False,
            "network_egress_started": False,
        }
        body["preflight_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class VoiceStudioPreflightService:
    """Evaluate already-recorded metadata without probing or invoking anything."""

    @staticmethod
    def evaluate(
        revision: VoiceProfileRevision,
        *,
        requested_language: str,
        requested_usage_class: str,
        requested_capability: str,
        commercial_use_required: bool,
    ) -> VoiceStudioPreflightReport:
        _id(requested_language, "requested_language")
        _id(requested_usage_class, "requested_usage_class")
        _id(requested_capability, "requested_capability")
        if not isinstance(commercial_use_required, bool):
            raise ValueError("commercial_use_required must be boolean")

        reasons: list[str] = []
        consent = revision.consent
        license_ref = revision.license
        capability = revision.capability

        if consent.state is not ConsentState.ACTIVE:
            reasons.append("CONSENT_NOT_ACTIVE")
        if not consent.subject_verified:
            reasons.append("CONSENT_SUBJECT_NOT_VERIFIED")
        if consent.evidence_sha256 is None:
            reasons.append("CONSENT_EVIDENCE_MISSING")
        if requested_usage_class not in consent.allowed_usage_classes:
            reasons.append("CONSENT_USAGE_NOT_ALLOWED")

        if license_ref.artifact_state is not ArtifactAdmissionState.APPROVED:
            reasons.append("MODEL_ARTIFACT_NOT_APPROVED")
        if license_ref.license_class is ModelLicenseClass.UNKNOWN:
            reasons.append("MODEL_LICENSE_UNKNOWN")
        if license_ref.license_class is ModelLicenseClass.RESTRICTED:
            reasons.append("MODEL_LICENSE_RESTRICTED")
        if license_ref.evidence_sha256 is None:
            reasons.append("MODEL_LICENSE_EVIDENCE_MISSING")
        if commercial_use_required and not license_ref.commercial_use_allowed:
            reasons.append("COMMERCIAL_USE_NOT_ALLOWED")

        if capability.probe_state is not CapabilityProbeState.VERIFIED:
            reasons.append("CAPABILITY_PROBE_NOT_VERIFIED")
        if capability.probe_report_sha256 is None:
            reasons.append("CAPABILITY_PROBE_EVIDENCE_MISSING")
        if not capability.offline_only:
            reasons.append("OFFLINE_ONLY_NOT_DECLARED")
        if requested_language not in capability.supported_languages:
            reasons.append("LANGUAGE_NOT_SUPPORTED")
        if requested_capability not in capability.capabilities:
            reasons.append("CAPABILITY_NOT_SUPPORTED")

        status = VoiceStudioPreflightStatus.READY if not reasons else VoiceStudioPreflightStatus.BLOCKED
        return VoiceStudioPreflightReport(
            voice_profile_id=revision.voice_profile_id,
            canonical_narration_profile_sha256=revision.canonical_narration_profile_sha256,
            revision=revision.revision,
            voice_profile_revision_sha256=revision.voice_profile_revision_sha256,
            requested_language=requested_language,
            requested_usage_class=requested_usage_class,
            requested_capability=requested_capability,
            commercial_use_required=commercial_use_required,
            status=status,
            reason_codes=tuple(reasons),
        )
