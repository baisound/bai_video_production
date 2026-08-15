"""TASK-046 body-free metadata revisions bound to TASK-014 VoiceProfile identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


VOICE_PROFILE_REVISION_VERSION = "1.0.0"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_LANGUAGE_RE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _text(value: str, name: str, *, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"{name} is invalid")
    return value.strip()


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("created_at must be a UTC RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("created_at must be a UTC RFC3339 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("created_at must be UTC")
    return value


def _unique_ids(values: tuple[str, ...], name: str, *, language: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{name} must not be empty")
    pattern = _LANGUAGE_RE if language else _ID_RE
    if any(not isinstance(value, str) or not pattern.fullmatch(value) for value in values):
        raise ValueError(f"{name} contains an invalid value")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must contain unique values")
    return values


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


class ConsentState(str, Enum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ModelLicenseClass(str, Enum):
    UNKNOWN = "UNKNOWN"
    COMMERCIAL_ALLOWED = "COMMERCIAL_ALLOWED"
    NONCOMMERCIAL_ONLY = "NONCOMMERCIAL_ONLY"
    RESTRICTED = "RESTRICTED"


class ArtifactAdmissionState(str, Enum):
    CATALOG_ONLY = "CATALOG_ONLY"
    EVALUATION_CANDIDATE = "EVALUATION_CANDIDATE"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    DEPRECATED = "DEPRECATED"


class CapabilityProbeState(str, Enum):
    NOT_RUN = "NOT_RUN"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ConsentReference:
    consent_subject_ref: str
    consent_scope: str
    allowed_usage_classes: tuple[str, ...]
    state: ConsentState
    subject_verified: bool
    evidence_id: str | None = None
    evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ConsentState):
            raise ValueError("state must be a ConsentState")
        _id(self.consent_subject_ref, "consent_subject_ref")
        _text(self.consent_scope, "consent_scope")
        _unique_ids(self.allowed_usage_classes, "allowed_usage_classes")
        if not isinstance(self.subject_verified, bool):
            raise ValueError("subject_verified must be boolean")
        if (self.evidence_id is None) != (self.evidence_sha256 is None):
            raise ValueError("Consent evidence id and digest must be supplied together")
        if self.evidence_id is not None:
            _id(self.evidence_id, "consent evidence_id")
            validate_sha256(self.evidence_sha256 or "", field_name="consent evidence_sha256")
        if self.state is ConsentState.ACTIVE and (
            not self.subject_verified or self.evidence_id is None
        ):
            raise ValueError("ACTIVE Consent requires verified subject and exact evidence")
        if self.state is ConsentState.UNKNOWN and self.subject_verified:
            raise ValueError("UNKNOWN Consent cannot claim a verified subject")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "consent_subject_ref": self.consent_subject_ref,
            "consent_scope": self.consent_scope,
            "allowed_usage_classes": list(self.allowed_usage_classes),
            "state": self.state.value,
            "subject_verified": self.subject_verified,
            "evidence_id": self.evidence_id,
            "evidence_sha256": self.evidence_sha256,
        }
        body["consent_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConsentReference":
        expected = {
            "consent_subject_ref", "consent_scope", "allowed_usage_classes", "state",
            "subject_verified", "evidence_id", "evidence_sha256", "consent_sha256",
        }
        _expect_keys(value, expected, "ConsentReference")
        body = {key: item for key, item in value.items() if key != "consent_sha256"}
        if value["consent_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("ConsentReference checksum mismatch")
        usage = value["allowed_usage_classes"]
        if not isinstance(usage, list) or any(not isinstance(item, str) for item in usage):
            raise ValueError("allowed_usage_classes must be a string list")
        return cls(
            consent_subject_ref=value["consent_subject_ref"],
            consent_scope=value["consent_scope"],
            allowed_usage_classes=tuple(usage),
            state=ConsentState(value["state"]),
            subject_verified=value["subject_verified"],
            evidence_id=value["evidence_id"],
            evidence_sha256=value["evidence_sha256"],
        )


@dataclass(frozen=True, slots=True)
class LicenseReference:
    model_artifact_id: str
    exact_model_id: str
    checkpoint_sha256: str
    runtime_id: str
    license_class: ModelLicenseClass
    artifact_state: ArtifactAdmissionState
    commercial_use_allowed: bool
    evidence_id: str | None = None
    evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.license_class, ModelLicenseClass):
            raise ValueError("license_class must be a ModelLicenseClass")
        if not isinstance(self.artifact_state, ArtifactAdmissionState):
            raise ValueError("artifact_state must be an ArtifactAdmissionState")
        for name in ("model_artifact_id", "exact_model_id", "runtime_id"):
            _id(getattr(self, name), name)
        validate_sha256(self.checkpoint_sha256, field_name="checkpoint_sha256")
        if not isinstance(self.commercial_use_allowed, bool):
            raise ValueError("commercial_use_allowed must be boolean")
        if (self.evidence_id is None) != (self.evidence_sha256 is None):
            raise ValueError("License evidence id and digest must be supplied together")
        if self.evidence_id is not None:
            _id(self.evidence_id, "license evidence_id")
            validate_sha256(self.evidence_sha256 or "", field_name="license evidence_sha256")
        if self.artifact_state is ArtifactAdmissionState.APPROVED and (
            self.license_class is ModelLicenseClass.UNKNOWN or self.evidence_id is None
        ):
            raise ValueError("APPROVED artifact requires known exact License evidence")
        if self.commercial_use_allowed and (
            self.license_class is not ModelLicenseClass.COMMERCIAL_ALLOWED
            or self.artifact_state is not ArtifactAdmissionState.APPROVED
            or self.evidence_id is None
        ):
            raise ValueError("commercial use requires an approved COMMERCIAL_ALLOWED artifact with evidence")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "model_artifact_id": self.model_artifact_id,
            "exact_model_id": self.exact_model_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "runtime_id": self.runtime_id,
            "license_class": self.license_class.value,
            "artifact_state": self.artifact_state.value,
            "commercial_use_allowed": self.commercial_use_allowed,
            "evidence_id": self.evidence_id,
            "evidence_sha256": self.evidence_sha256,
        }
        body["license_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LicenseReference":
        expected = {
            "model_artifact_id", "exact_model_id", "checkpoint_sha256", "runtime_id",
            "license_class", "artifact_state", "commercial_use_allowed", "evidence_id",
            "evidence_sha256", "license_sha256",
        }
        _expect_keys(value, expected, "LicenseReference")
        body = {key: item for key, item in value.items() if key != "license_sha256"}
        if value["license_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("LicenseReference checksum mismatch")
        return cls(
            model_artifact_id=value["model_artifact_id"],
            exact_model_id=value["exact_model_id"],
            checkpoint_sha256=value["checkpoint_sha256"],
            runtime_id=value["runtime_id"],
            license_class=ModelLicenseClass(value["license_class"]),
            artifact_state=ArtifactAdmissionState(value["artifact_state"]),
            commercial_use_allowed=value["commercial_use_allowed"],
            evidence_id=value["evidence_id"],
            evidence_sha256=value["evidence_sha256"],
        )


@dataclass(frozen=True, slots=True)
class LocalVoiceCapabilityDescription:
    engine_family: str
    engine_id: str
    supported_languages: tuple[str, ...]
    capabilities: tuple[str, ...]
    offline_only: bool
    probe_state: CapabilityProbeState = CapabilityProbeState.NOT_RUN
    probe_report_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.probe_state, CapabilityProbeState):
            raise ValueError("probe_state must be a CapabilityProbeState")
        _id(self.engine_family, "engine_family")
        _id(self.engine_id, "engine_id")
        _unique_ids(self.supported_languages, "supported_languages", language=True)
        _unique_ids(self.capabilities, "capabilities")
        if not isinstance(self.offline_only, bool):
            raise ValueError("offline_only must be boolean")
        if self.probe_report_sha256 is not None:
            validate_sha256(self.probe_report_sha256, field_name="probe_report_sha256")
        if self.probe_state is CapabilityProbeState.VERIFIED and self.probe_report_sha256 is None:
            raise ValueError("VERIFIED capability requires an exact probe report digest")
        if self.probe_state is CapabilityProbeState.NOT_RUN and self.probe_report_sha256 is not None:
            raise ValueError("NOT_RUN capability cannot reference a probe report")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "engine_family": self.engine_family,
            "engine_id": self.engine_id,
            "supported_languages": list(self.supported_languages),
            "capabilities": list(self.capabilities),
            "offline_only": self.offline_only,
            "probe_state": self.probe_state.value,
            "probe_report_sha256": self.probe_report_sha256,
        }
        body["capability_description_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalVoiceCapabilityDescription":
        expected = {
            "engine_family", "engine_id", "supported_languages", "capabilities",
            "offline_only", "probe_state", "probe_report_sha256",
            "capability_description_sha256",
        }
        _expect_keys(value, expected, "LocalVoiceCapabilityDescription")
        body = {key: item for key, item in value.items() if key != "capability_description_sha256"}
        if value["capability_description_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("LocalVoiceCapabilityDescription checksum mismatch")
        languages = value["supported_languages"]
        capabilities = value["capabilities"]
        if not isinstance(languages, list) or any(not isinstance(item, str) for item in languages):
            raise ValueError("supported_languages must be a string list")
        if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
            raise ValueError("capabilities must be a string list")
        return cls(
            engine_family=value["engine_family"],
            engine_id=value["engine_id"],
            supported_languages=tuple(languages),
            capabilities=tuple(capabilities),
            offline_only=value["offline_only"],
            probe_state=CapabilityProbeState(value["probe_state"]),
            probe_report_sha256=value["probe_report_sha256"],
        )


@dataclass(frozen=True, slots=True)
class VoiceProfileRevision:
    voice_profile_id: str
    canonical_narration_profile_sha256: str
    revision: int
    parent_revision_sha256: str | None
    created_at: str
    consent: ConsentReference
    license: LicenseReference
    capability: LocalVoiceCapabilityDescription

    def __post_init__(self) -> None:
        if not isinstance(self.consent, ConsentReference):
            raise ValueError("consent must be a ConsentReference")
        if not isinstance(self.license, LicenseReference):
            raise ValueError("license must be a LicenseReference")
        if not isinstance(self.capability, LocalVoiceCapabilityDescription):
            raise ValueError("capability must be a LocalVoiceCapabilityDescription")
        _id(self.voice_profile_id, "voice_profile_id")
        validate_sha256(
            self.canonical_narration_profile_sha256,
            field_name="canonical_narration_profile_sha256",
        )
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            raise ValueError("revision must be an integer >= 1")
        if self.revision == 1 and self.parent_revision_sha256 is not None:
            raise ValueError("first revision cannot have a parent")
        if self.revision > 1:
            validate_sha256(self.parent_revision_sha256 or "", field_name="parent_revision_sha256")
        _timestamp(self.created_at)

    def _body(self) -> dict[str, Any]:
        return {
            "profile_revision_version": VOICE_PROFILE_REVISION_VERSION,
            "task_owner": "TASK-046",
            "voice_profile_id": self.voice_profile_id,
            "canonical_narration_profile_sha256": self.canonical_narration_profile_sha256,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "consent": self.consent.to_dict(),
            "license": self.license.to_dict(),
            "capability": self.capability.to_dict(),
            "audio_body_persisted": False,
            "dataset_body_persisted": False,
            "speaker_embedding_persisted": False,
            "transcript_body_persisted": False,
            "credential_value_persisted": False,
            "private_provider_voice_id_persisted": False,
            "host_path_persisted": False,
            "execution_authorized": False,
        }

    @property
    def voice_profile_revision_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    def to_private_dict(self) -> dict[str, Any]:
        body = self._body()
        body["voice_profile_revision_sha256"] = self.voice_profile_revision_sha256
        return body

    def to_public_dict(self) -> dict[str, Any]:
        consent = self.consent.to_dict()
        license_row = self.license.to_dict()
        capability = self.capability.to_dict()
        return {
            "profile_revision_version": VOICE_PROFILE_REVISION_VERSION,
            "task_owner": "TASK-046",
            "voice_profile_id": self.voice_profile_id,
            "canonical_narration_profile_sha256": self.canonical_narration_profile_sha256,
            "revision": self.revision,
            "parent_revision_sha256": self.parent_revision_sha256,
            "created_at": self.created_at,
            "voice_profile_revision_sha256": self.voice_profile_revision_sha256,
            "consent_state": self.consent.state.value,
            "consent_subject_verified": self.consent.subject_verified,
            "consent_sha256": consent["consent_sha256"],
            "license_class": self.license.license_class.value,
            "artifact_state": self.license.artifact_state.value,
            "commercial_use_allowed": self.license.commercial_use_allowed,
            "license_sha256": license_row["license_sha256"],
            "model_artifact_id": self.license.model_artifact_id,
            "exact_model_id": self.license.exact_model_id,
            "checkpoint_sha256": self.license.checkpoint_sha256,
            "runtime_id": self.license.runtime_id,
            "engine_family": self.capability.engine_family,
            "engine_id": self.capability.engine_id,
            "supported_languages": list(self.capability.supported_languages),
            "capabilities": list(self.capability.capabilities),
            "offline_only": self.capability.offline_only,
            "probe_state": self.capability.probe_state.value,
            "probe_report_sha256": self.capability.probe_report_sha256,
            "capability_description_sha256": capability["capability_description_sha256"],
            "consent_subject_ref_persisted": False,
            "consent_scope_persisted": False,
            "evidence_id_persisted": False,
            "audio_body_persisted": False,
            "dataset_body_persisted": False,
            "speaker_embedding_persisted": False,
            "transcript_body_persisted": False,
            "credential_value_persisted": False,
            "private_provider_voice_id_persisted": False,
            "host_path_persisted": False,
            "execution_authorized": False,
        }

    @classmethod
    def from_private_dict(cls, value: Mapping[str, Any]) -> "VoiceProfileRevision":
        boundary = {
            "audio_body_persisted", "dataset_body_persisted", "speaker_embedding_persisted",
            "transcript_body_persisted", "credential_value_persisted",
            "private_provider_voice_id_persisted", "host_path_persisted", "execution_authorized",
        }
        expected = {
            "profile_revision_version", "task_owner", "voice_profile_id",
            "canonical_narration_profile_sha256", "revision",
            "parent_revision_sha256", "created_at", "consent", "license", "capability",
            "voice_profile_revision_sha256", *boundary,
        }
        _expect_keys(value, expected, "VoiceProfileRevision")
        if value["profile_revision_version"] != VOICE_PROFILE_REVISION_VERSION or value["task_owner"] != "TASK-046":
            raise ValueError("unsupported VoiceProfileRevision identity")
        if any(value[name] is not False for name in boundary):
            raise ValueError("VoiceProfileRevision violates body-free/non-executing boundaries")
        revision = cls(
            voice_profile_id=value["voice_profile_id"],
            canonical_narration_profile_sha256=value["canonical_narration_profile_sha256"],
            revision=value["revision"],
            parent_revision_sha256=value["parent_revision_sha256"],
            created_at=value["created_at"],
            consent=ConsentReference.from_dict(value["consent"]),
            license=LicenseReference.from_dict(value["license"]),
            capability=LocalVoiceCapabilityDescription.from_dict(value["capability"]),
        )
        if value["voice_profile_revision_sha256"] != revision.voice_profile_revision_sha256:
            raise ValueError("VoiceProfileRevision checksum mismatch")
        return revision
