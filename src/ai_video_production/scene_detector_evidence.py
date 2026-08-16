"""Pure TASK-005 detector Evidence receipt contracts.

The records in this module describe future artifact, license, materialization,
probe, and normalized-output Evidence.  They never acquire an artifact, touch a
path, execute a process, read media, or grant runtime authority.  A finalized
receipt can be projected into the existing R1B1 admission claim only when its
typed state is exact, current-valid, and independently judged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, ClassVar

from .scene_boundary import DetectorProfile, SceneSourceBinding
from .scene_detector_admission import (
    DetectorCandidateFamily,
    DetectorEvidenceClaim,
    DetectorEvidenceKind,
    DetectorEvidenceValidity,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,254}$")
_SPDX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,127}$")
_INCIDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_MAX_ARTIFACT_BYTES = (1 << 63) - 1
_MAX_PROBE_STEPS = 5
_MAX_EVENTS = 512
_MAX_TIMEOUT_MS = 300_000
_MAX_OUTPUT_BYTES = 16_777_216
_MAX_MEMORY_BYTES = 1_073_741_824
_REAL_CANDIDATES = frozenset(
    {
        DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY,
        DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY,
        DetectorCandidateFamily.OPENCV_CUSTOM_PROFILE_FAMILY,
    }
)


def _require_exact_real_binding(
    candidate_family: DetectorCandidateFamily,
    detector_profile: DetectorProfile,
) -> None:
    if type(candidate_family) is not DetectorCandidateFamily:
        raise TypeError("candidate_family must be an exact DetectorCandidateFamily")
    if candidate_family not in _REAL_CANDIDATES:
        raise ValueError("Evidence receipts are accepted only for real detector families")
    if type(detector_profile) is not DetectorProfile:
        raise TypeError("detector_profile must be an exact DetectorProfile")


def _require_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")
    return value


def _require_filename(value: str) -> str:
    if type(value) is not str or not _FILENAME_RE.fullmatch(value):
        raise ValueError("artifact_filename must be a basename without path syntax")
    return value


def _require_bounded_int(value: int, low: int, high: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{field_name} must be {low}-{high}")
    return value


def _record_payload(record_type: str, body: dict[str, Any]) -> dict[str, Any]:
    payload = {"record_type": record_type, "contract_version": "1.0.0", **body}
    payload["receipt_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


class DetectorArtifactKind(str, Enum):
    ACQUISITION_ARCHIVE = "ACQUISITION_ARCHIVE"
    EXECUTABLE = "EXECUTABLE"
    COMPANION_EXECUTABLE = "COMPANION_EXECUTABLE"
    SHARED_LIBRARY = "SHARED_LIBRARY"
    UNKNOWN = "UNKNOWN"


class DetectorArtifactPlatform(str, Enum):
    WINDOWS = "WINDOWS"
    LINUX = "LINUX"
    MACOS = "MACOS"
    UNKNOWN = "UNKNOWN"


class DetectorArtifactArchitecture(str, Enum):
    X86_64 = "X86_64"
    ARM64 = "ARM64"
    X86 = "X86"
    UNIVERSAL = "UNIVERSAL"
    UNKNOWN = "UNKNOWN"


class DetectorSignatureRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class DetectorArtifactComparisonState(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_OBSERVED = "NOT_OBSERVED"
    OBSERVED_ONLY_UNBOUND = "OBSERVED_ONLY_UNBOUND"
    UNKNOWN = "UNKNOWN"


class DetectorArtifactComparisonReason(str, Enum):
    EXACT_IDENTITY_MATCH = "EXACT_IDENTITY_MATCH"
    IDENTITY_FIELD_MISMATCH = "IDENTITY_FIELD_MISMATCH"
    OBSERVATION_ABSENT = "OBSERVATION_ABSENT"
    EXPECTED_IDENTITY_ABSENT = "EXPECTED_IDENTITY_ABSENT"
    EXPECTED_IDENTITY_INCOMPLETE = "EXPECTED_IDENTITY_INCOMPLETE"
    UNDERLYING_EVIDENCE_NOT_CURRENT = "UNDERLYING_EVIDENCE_NOT_CURRENT"


class DetectorLicenseState(str, Enum):
    CLEARED = "CLEARED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"


class DetectorMaterializationState(str, Enum):
    VERIFIED_CONTAINED = "VERIFIED_CONTAINED"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class DetectorProbeKind(str, Enum):
    VERSION = "VERSION"
    SCENE_FILTER_CAPABILITY = "SCENE_FILTER_CAPABILITY"
    PLATFORM_ARCH = "PLATFORM_ARCH"
    RESOURCE_BOUNDS = "RESOURCE_BOUNDS"
    OUTPUT_NORMALIZATION = "OUTPUT_NORMALIZATION"


class DetectorProbeInputMode(str, Enum):
    NO_MEDIA = "NO_MEDIA"
    SYNTHETIC_MEDIA = "SYNTHETIC_MEDIA"
    REAL_MEDIA = "REAL_MEDIA"


class DetectorProbeDisposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNSUPPORTED = "UNSUPPORTED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class DetectorEventKind(str, Enum):
    SCENE_CANDIDATE = "SCENE_CANDIDATE"
    INCIDENT = "INCIDENT"
    END = "END"


@dataclass(frozen=True, slots=True)
class ExpectedDetectorArtifact:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    artifact_coordinate_id: str
    artifact_kind: DetectorArtifactKind
    artifact_filename: str
    version: str
    platform: DetectorArtifactPlatform
    architecture: DetectorArtifactArchitecture
    byte_count: int | None
    artifact_sha256: str | None
    signature_requirement: DetectorSignatureRequirement
    signature_sha256: str | None
    publisher_identity_sha256: str
    provenance_receipt_sha256: str
    validity: DetectorEvidenceValidity

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        _require_identifier(self.artifact_coordinate_id, "artifact_coordinate_id")
        if type(self.artifact_kind) is not DetectorArtifactKind:
            raise TypeError("artifact_kind must be exact")
        _require_filename(self.artifact_filename)
        _require_identifier(self.version, "version")
        if type(self.platform) is not DetectorArtifactPlatform:
            raise TypeError("platform must be exact")
        if type(self.architecture) is not DetectorArtifactArchitecture:
            raise TypeError("architecture must be exact")
        if self.byte_count is not None:
            _require_bounded_int(self.byte_count, 1, _MAX_ARTIFACT_BYTES, "byte_count")
        if self.artifact_sha256 is not None:
            validate_sha256(self.artifact_sha256, field_name="artifact_sha256")
        if type(self.signature_requirement) is not DetectorSignatureRequirement:
            raise TypeError("signature_requirement must be exact")
        if self.signature_sha256 is not None:
            validate_sha256(self.signature_sha256, field_name="signature_sha256")
        if (
            self.signature_requirement is DetectorSignatureRequirement.REQUIRED
            and self.signature_sha256 is None
        ):
            raise ValueError("REQUIRED signature requires signature_sha256")
        if (
            self.signature_requirement is DetectorSignatureRequirement.NOT_APPLICABLE
            and self.signature_sha256 is not None
        ):
            raise ValueError("NOT_APPLICABLE signature requires null signature_sha256")
        validate_sha256(self.publisher_identity_sha256, field_name="publisher_identity_sha256")
        validate_sha256(self.provenance_receipt_sha256, field_name="provenance_receipt_sha256")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")

    @property
    def identity_complete(self) -> bool:
        return (
            self.byte_count is not None
            and self.artifact_sha256 is not None
            and self.artifact_kind is not DetectorArtifactKind.UNKNOWN
            and self.platform is not DetectorArtifactPlatform.UNKNOWN
            and self.architecture is not DetectorArtifactArchitecture.UNKNOWN
            and self.signature_requirement is not DetectorSignatureRequirement.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_family": self.candidate_family.value,
            "detector_profile": self.detector_profile.to_dict(),
            "artifact_coordinate_id": self.artifact_coordinate_id,
            "artifact_kind": self.artifact_kind.value,
            "artifact_filename": self.artifact_filename,
            "version": self.version,
            "platform": self.platform.value,
            "architecture": self.architecture.value,
            "byte_count": self.byte_count,
            "artifact_sha256": self.artifact_sha256,
            "signature_requirement": self.signature_requirement.value,
            "signature_sha256": self.signature_sha256,
            "publisher_identity_sha256": self.publisher_identity_sha256,
            "provenance_receipt_sha256": self.provenance_receipt_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class ObservedDetectorArtifact:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    artifact_coordinate_id: str
    artifact_kind: DetectorArtifactKind
    artifact_filename: str
    version: str
    platform: DetectorArtifactPlatform
    architecture: DetectorArtifactArchitecture
    byte_count: int
    artifact_sha256: str
    signature_sha256: str | None
    observation_receipt_sha256: str
    validity: DetectorEvidenceValidity

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        _require_identifier(self.artifact_coordinate_id, "artifact_coordinate_id")
        if type(self.artifact_kind) is not DetectorArtifactKind:
            raise TypeError("artifact_kind must be exact")
        _require_filename(self.artifact_filename)
        _require_identifier(self.version, "version")
        if type(self.platform) is not DetectorArtifactPlatform:
            raise TypeError("platform must be exact")
        if type(self.architecture) is not DetectorArtifactArchitecture:
            raise TypeError("architecture must be exact")
        _require_bounded_int(self.byte_count, 1, _MAX_ARTIFACT_BYTES, "byte_count")
        validate_sha256(self.artifact_sha256, field_name="artifact_sha256")
        if self.signature_sha256 is not None:
            validate_sha256(self.signature_sha256, field_name="signature_sha256")
        validate_sha256(self.observation_receipt_sha256, field_name="observation_receipt_sha256")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_family": self.candidate_family.value,
            "detector_profile": self.detector_profile.to_dict(),
            "artifact_coordinate_id": self.artifact_coordinate_id,
            "artifact_kind": self.artifact_kind.value,
            "artifact_filename": self.artifact_filename,
            "version": self.version,
            "platform": self.platform.value,
            "architecture": self.architecture.value,
            "byte_count": self.byte_count,
            "artifact_sha256": self.artifact_sha256,
            "signature_sha256": self.signature_sha256,
            "observation_receipt_sha256": self.observation_receipt_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True, init=False)
class DetectorArtifactComparisonReceipt:
    expected: ExpectedDetectorArtifact | None
    observed: ObservedDetectorArtifact | None
    comparison_state: DetectorArtifactComparisonState
    comparison_reason: DetectorArtifactComparisonReason
    validity: DetectorEvidenceValidity

    runtime_authorized: ClassVar[bool] = False
    external_effect_performed: ClassVar[bool] = False

    def __init__(
        self,
        expected: ExpectedDetectorArtifact | None,
        observed: ObservedDetectorArtifact | None,
        comparison_state: DetectorArtifactComparisonState,
        comparison_reason: DetectorArtifactComparisonReason,
        validity: DetectorEvidenceValidity,
        *,
        _token: object,
    ) -> None:
        if _token is not _COMPARISON_TOKEN:
            raise ValueError("comparison receipts must be created by compare_detector_artifacts")
        object.__setattr__(self, "expected", expected)
        object.__setattr__(self, "observed", observed)
        object.__setattr__(self, "comparison_state", comparison_state)
        object.__setattr__(self, "comparison_reason", comparison_reason)
        object.__setattr__(self, "validity", validity)
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.expected is None and self.observed is None:
            raise ValueError("expected and observed cannot both be null")
        if self.expected is not None and type(self.expected) is not ExpectedDetectorArtifact:
            raise TypeError("expected must be exact")
        if self.observed is not None and type(self.observed) is not ObservedDetectorArtifact:
            raise TypeError("observed must be exact")
        if type(self.comparison_state) is not DetectorArtifactComparisonState:
            raise TypeError("comparison_state must be exact")
        if type(self.comparison_reason) is not DetectorArtifactComparisonReason:
            raise TypeError("comparison_reason must be exact")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")

    @property
    def candidate_family(self) -> DetectorCandidateFamily:
        return (self.expected or self.observed).candidate_family  # type: ignore[union-attr]

    @property
    def detector_profile(self) -> DetectorProfile:
        return (self.expected or self.observed).detector_profile  # type: ignore[union-attr]

    @property
    def artifact_coordinate_id(self) -> str:
        return (self.expected or self.observed).artifact_coordinate_id  # type: ignore[union-attr]

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorArtifactComparisonReceipt",
            {
                "expected": None if self.expected is None else self.expected.to_dict(),
                "observed": None if self.observed is None else self.observed.to_dict(),
                "comparison_state": self.comparison_state.value,
                "comparison_reason": self.comparison_reason.value,
                "validity": self.validity.value,
                "runtime_authorized": self.runtime_authorized,
                "external_effect_performed": self.external_effect_performed,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


_COMPARISON_TOKEN = object()


def compare_detector_artifacts(
    expected: ExpectedDetectorArtifact | None,
    observed: ObservedDetectorArtifact | None,
) -> DetectorArtifactComparisonReceipt:
    """Compare immutable coordinates; absence never becomes identity Evidence."""

    if expected is None and observed is None:
        raise ValueError("expected and observed cannot both be null")
    if expected is not None and type(expected) is not ExpectedDetectorArtifact:
        raise TypeError("expected must be exact")
    if observed is not None and type(observed) is not ObservedDetectorArtifact:
        raise TypeError("observed must be exact")
    if expected is None:
        state = DetectorArtifactComparisonState.OBSERVED_ONLY_UNBOUND
        reason = DetectorArtifactComparisonReason.EXPECTED_IDENTITY_ABSENT
        validity = DetectorEvidenceValidity.UNKNOWN
    elif observed is None:
        state = DetectorArtifactComparisonState.NOT_OBSERVED
        reason = DetectorArtifactComparisonReason.OBSERVATION_ABSENT
        validity = DetectorEvidenceValidity.UNKNOWN
    else:
        if expected.candidate_family is not observed.candidate_family:
            raise ValueError("artifact candidate binding mismatch")
        if expected.detector_profile != observed.detector_profile:
            raise ValueError("artifact detector profile binding mismatch")
        if expected.artifact_coordinate_id != observed.artifact_coordinate_id:
            raise ValueError("artifact coordinate borrowing is prohibited")
        if (
            expected.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
            or observed.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            state = DetectorArtifactComparisonState.UNKNOWN
            reason = DetectorArtifactComparisonReason.UNDERLYING_EVIDENCE_NOT_CURRENT
            validity = DetectorEvidenceValidity.UNKNOWN
        elif not expected.identity_complete:
            state = DetectorArtifactComparisonState.UNKNOWN
            reason = DetectorArtifactComparisonReason.EXPECTED_IDENTITY_INCOMPLETE
            validity = DetectorEvidenceValidity.UNKNOWN
        else:
            expected_fields = (
                expected.artifact_kind,
                expected.artifact_filename,
                expected.version,
                expected.platform,
                expected.architecture,
                expected.byte_count,
                expected.artifact_sha256,
                expected.signature_sha256,
            )
            observed_fields = (
                observed.artifact_kind,
                observed.artifact_filename,
                observed.version,
                observed.platform,
                observed.architecture,
                observed.byte_count,
                observed.artifact_sha256,
                observed.signature_sha256,
            )
            if expected_fields == observed_fields:
                state = DetectorArtifactComparisonState.MATCH
                reason = DetectorArtifactComparisonReason.EXACT_IDENTITY_MATCH
            else:
                state = DetectorArtifactComparisonState.MISMATCH
                reason = DetectorArtifactComparisonReason.IDENTITY_FIELD_MISMATCH
            validity = DetectorEvidenceValidity.CURRENT_VALID_JUDGED
    return DetectorArtifactComparisonReceipt(
        expected,
        observed,
        state,
        reason,
        validity,
        _token=_COMPARISON_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class DetectorLicenseProvenanceReceipt:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    artifact_comparison: DetectorArtifactComparisonReceipt
    spdx_identifier: str
    license_text_sha256: str
    provenance_receipt_sha256: str
    distribution_policy_receipt_sha256: str
    license_state: DetectorLicenseState
    validity: DetectorEvidenceValidity

    runtime_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        if type(self.artifact_comparison) is not DetectorArtifactComparisonReceipt:
            raise TypeError("artifact_comparison must be exact")
        if self.artifact_comparison.candidate_family is not self.candidate_family:
            raise ValueError("license receipt candidate borrowing is prohibited")
        if self.artifact_comparison.detector_profile != self.detector_profile:
            raise ValueError("license receipt profile borrowing is prohibited")
        if type(self.spdx_identifier) is not str or not _SPDX_RE.fullmatch(self.spdx_identifier):
            raise ValueError("spdx_identifier is invalid")
        validate_sha256(self.license_text_sha256, field_name="license_text_sha256")
        validate_sha256(self.provenance_receipt_sha256, field_name="provenance_receipt_sha256")
        validate_sha256(
            self.distribution_policy_receipt_sha256,
            field_name="distribution_policy_receipt_sha256",
        )
        if type(self.license_state) is not DetectorLicenseState:
            raise TypeError("license_state must be exact")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")
        if (
            self.license_state is DetectorLicenseState.CLEARED
            and self.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("CLEARED requires current-valid judged Evidence")
        if self.license_state is DetectorLicenseState.CLEARED and (
            self.artifact_comparison.comparison_state
            is not DetectorArtifactComparisonState.MATCH
            or self.artifact_comparison.validity
            is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("CLEARED requires an exact current-valid artifact MATCH")
        if self.license_state is DetectorLicenseState.CLEARED and self.spdx_identifier in {
            "NONE",
            "NOASSERTION",
        }:
            raise ValueError("CLEARED requires a resolved SPDX identifier")

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorLicenseProvenanceReceipt",
            {
                "candidate_family": self.candidate_family.value,
                "detector_profile": self.detector_profile.to_dict(),
                "artifact_comparison": self.artifact_comparison.to_dict(),
                "spdx_identifier": self.spdx_identifier,
                "license_text_sha256": self.license_text_sha256,
                "provenance_receipt_sha256": self.provenance_receipt_sha256,
                "distribution_policy_receipt_sha256": self.distribution_policy_receipt_sha256,
                "license_state": self.license_state.value,
                "validity": self.validity.value,
                "runtime_authorized": self.runtime_authorized,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]


@dataclass(frozen=True, slots=True)
class DetectorMaterializationReceipt:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    artifact_comparison: DetectorArtifactComparisonReceipt
    dependency_graph_sha256: str
    platform_arch_receipt_sha256: str
    materialization_receipt_sha256: str
    materialization_state: DetectorMaterializationState
    validity: DetectorEvidenceValidity

    runtime_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        if type(self.artifact_comparison) is not DetectorArtifactComparisonReceipt:
            raise TypeError("artifact_comparison must be exact")
        if self.artifact_comparison.candidate_family is not self.candidate_family:
            raise ValueError("materialization receipt candidate borrowing is prohibited")
        if self.artifact_comparison.detector_profile != self.detector_profile:
            raise ValueError("materialization receipt profile borrowing is prohibited")
        for field_name in (
            "dependency_graph_sha256",
            "platform_arch_receipt_sha256",
            "materialization_receipt_sha256",
        ):
            validate_sha256(getattr(self, field_name), field_name=field_name)
        if type(self.materialization_state) is not DetectorMaterializationState:
            raise TypeError("materialization_state must be exact")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")
        if (
            self.materialization_state is DetectorMaterializationState.VERIFIED_CONTAINED
            and self.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("VERIFIED_CONTAINED requires current-valid judged Evidence")
        if self.materialization_state is DetectorMaterializationState.VERIFIED_CONTAINED and (
            self.artifact_comparison.comparison_state
            is not DetectorArtifactComparisonState.MATCH
            or self.artifact_comparison.validity
            is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("VERIFIED_CONTAINED requires an exact current-valid artifact MATCH")

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorMaterializationReceipt",
            {
                "candidate_family": self.candidate_family.value,
                "detector_profile": self.detector_profile.to_dict(),
                "artifact_comparison": self.artifact_comparison.to_dict(),
                "dependency_graph_sha256": self.dependency_graph_sha256,
                "platform_arch_receipt_sha256": self.platform_arch_receipt_sha256,
                "materialization_receipt_sha256": self.materialization_receipt_sha256,
                "materialization_state": self.materialization_state.value,
                "validity": self.validity.value,
                "runtime_authorized": self.runtime_authorized,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]


@dataclass(frozen=True, slots=True)
class DetectorProbePlan:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    artifact_comparison: DetectorArtifactComparisonReceipt
    input_mode: DetectorProbeInputMode
    source_binding: SceneSourceBinding | None
    probe_kinds: tuple[DetectorProbeKind, ...]
    timeout_ms: int
    stdout_cap_bytes: int
    stderr_cap_bytes: int
    memory_cap_bytes: int
    event_cap: int

    execution_authorized: ClassVar[bool] = False
    media_input_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        if type(self.artifact_comparison) is not DetectorArtifactComparisonReceipt:
            raise TypeError("artifact_comparison must be exact")
        if self.artifact_comparison.candidate_family is not self.candidate_family:
            raise ValueError("probe plan candidate borrowing is prohibited")
        if self.artifact_comparison.detector_profile != self.detector_profile:
            raise ValueError("probe plan profile borrowing is prohibited")
        if type(self.probe_kinds) is not tuple:
            raise TypeError("probe_kinds must be an exact tuple")
        if not 1 <= len(self.probe_kinds) <= _MAX_PROBE_STEPS:
            raise ValueError("probe_kinds must contain 1-5 values")
        if any(type(kind) is not DetectorProbeKind for kind in self.probe_kinds):
            raise TypeError("every probe kind must be exact")
        order = {kind: index for index, kind in enumerate(DetectorProbeKind)}
        if self.probe_kinds != tuple(sorted(set(self.probe_kinds), key=order.__getitem__)):
            raise ValueError("probe_kinds must be unique and canonically ordered")
        if type(self.input_mode) is not DetectorProbeInputMode:
            raise TypeError("input_mode must be exact")
        if self.input_mode is DetectorProbeInputMode.NO_MEDIA:
            if self.source_binding is not None:
                raise ValueError("NO_MEDIA requires a null source_binding")
            if DetectorProbeKind.OUTPUT_NORMALIZATION in self.probe_kinds:
                raise ValueError("NO_MEDIA cannot plan OUTPUT_NORMALIZATION")
        elif type(self.source_binding) is not SceneSourceBinding:
            raise TypeError("media probe modes require an exact R0 SceneSourceBinding")
        _require_bounded_int(self.timeout_ms, 1, _MAX_TIMEOUT_MS, "timeout_ms")
        _require_bounded_int(self.stdout_cap_bytes, 0, _MAX_OUTPUT_BYTES, "stdout_cap_bytes")
        _require_bounded_int(self.stderr_cap_bytes, 0, _MAX_OUTPUT_BYTES, "stderr_cap_bytes")
        _require_bounded_int(self.memory_cap_bytes, 1, _MAX_MEMORY_BYTES, "memory_cap_bytes")
        _require_bounded_int(self.event_cap, 1, _MAX_EVENTS, "event_cap")

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorProbePlan",
            {
                "candidate_family": self.candidate_family.value,
                "detector_profile": self.detector_profile.to_dict(),
                "artifact_comparison": self.artifact_comparison.to_dict(),
                "input_mode": self.input_mode.value,
                "source_binding": (
                    None if self.source_binding is None else self.source_binding.to_dict()
                ),
                "probe_kinds": [kind.value for kind in self.probe_kinds],
                "timeout_ms": self.timeout_ms,
                "stdout_cap_bytes": self.stdout_cap_bytes,
                "stderr_cap_bytes": self.stderr_cap_bytes,
                "memory_cap_bytes": self.memory_cap_bytes,
                "event_cap": self.event_cap,
                "execution_authorized": self.execution_authorized,
                "media_input_authorized": self.media_input_authorized,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]


@dataclass(frozen=True, slots=True)
class DetectorProbeOutcome:
    probe_kind: DetectorProbeKind
    disposition: DetectorProbeDisposition
    evidence_receipt_sha256: str
    output_sha256: str
    incident_code: str | None

    def __post_init__(self) -> None:
        if type(self.probe_kind) is not DetectorProbeKind:
            raise TypeError("probe_kind must be exact")
        if type(self.disposition) is not DetectorProbeDisposition:
            raise TypeError("disposition must be exact")
        validate_sha256(self.evidence_receipt_sha256, field_name="evidence_receipt_sha256")
        validate_sha256(self.output_sha256, field_name="output_sha256")
        if self.disposition is DetectorProbeDisposition.PASS:
            if self.incident_code is not None:
                raise ValueError("PASS cannot carry an incident_code")
        elif type(self.incident_code) is not str or not _INCIDENT_RE.fullmatch(self.incident_code):
            raise ValueError("non-PASS probe outcomes require an incident_code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_kind": self.probe_kind.value,
            "disposition": self.disposition.value,
            "evidence_receipt_sha256": self.evidence_receipt_sha256,
            "output_sha256": self.output_sha256,
            "incident_code": self.incident_code,
        }


@dataclass(frozen=True, slots=True)
class DetectorProbeReceipt:
    plan: DetectorProbePlan
    outcomes: tuple[DetectorProbeOutcome, ...]
    validity: DetectorEvidenceValidity

    runtime_authorized: ClassVar[bool] = False
    next_stage_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self.plan) is not DetectorProbePlan:
            raise TypeError("plan must be exact")
        if type(self.outcomes) is not tuple:
            raise TypeError("outcomes must be an exact tuple")
        if any(type(outcome) is not DetectorProbeOutcome for outcome in self.outcomes):
            raise TypeError("every outcome must be exact")
        if tuple(outcome.probe_kind for outcome in self.outcomes) != self.plan.probe_kinds:
            raise ValueError("outcomes must exactly equal the planned probe-kind set and order")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")
        if self.validity is DetectorEvidenceValidity.CURRENT_VALID_JUDGED and any(
            outcome.disposition is not DetectorProbeDisposition.PASS for outcome in self.outcomes
        ):
            raise ValueError("current-valid probe receipt requires every planned outcome PASS")

    @property
    def candidate_family(self) -> DetectorCandidateFamily:
        return self.plan.candidate_family

    @property
    def detector_profile(self) -> DetectorProfile:
        return self.plan.detector_profile

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorProbeReceipt",
            {
                "plan": self.plan.to_dict(),
                "outcomes": [outcome.to_dict() for outcome in self.outcomes],
                "validity": self.validity.value,
                "runtime_authorized": self.runtime_authorized,
                "next_stage_authorized": self.next_stage_authorized,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]


@dataclass(frozen=True, slots=True)
class NormalizedDetectorEvent:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    probe_receipt_sha256: str
    ordinal: int
    event_kind: DetectorEventKind
    frame_index: int | None
    confidence_milli: int | None
    incident_code: str | None
    source_event_sha256: str

    def __post_init__(self) -> None:
        _require_exact_real_binding(self.candidate_family, self.detector_profile)
        validate_sha256(self.probe_receipt_sha256, field_name="probe_receipt_sha256")
        _require_bounded_int(self.ordinal, 0, _MAX_EVENTS - 1, "ordinal")
        if type(self.event_kind) is not DetectorEventKind:
            raise TypeError("event_kind must be exact")
        validate_sha256(self.source_event_sha256, field_name="source_event_sha256")
        if self.event_kind is DetectorEventKind.SCENE_CANDIDATE:
            if self.frame_index is None:
                raise ValueError("SCENE_CANDIDATE requires frame_index")
            _require_bounded_int(self.frame_index, 0, (1 << 63) - 1, "frame_index")
            if self.confidence_milli is None:
                raise ValueError("SCENE_CANDIDATE requires confidence_milli")
            _require_bounded_int(self.confidence_milli, 0, 1000, "confidence_milli")
            if self.incident_code is not None:
                raise ValueError("SCENE_CANDIDATE cannot carry incident_code")
        elif self.event_kind is DetectorEventKind.INCIDENT:
            if self.confidence_milli is not None:
                raise ValueError("INCIDENT cannot carry confidence_milli")
            if type(self.incident_code) is not str or not _INCIDENT_RE.fullmatch(self.incident_code):
                raise ValueError("INCIDENT requires incident_code")
            if self.frame_index is not None:
                _require_bounded_int(self.frame_index, 0, (1 << 63) - 1, "frame_index")
        else:
            if self.frame_index is not None or self.confidence_milli is not None or self.incident_code is not None:
                raise ValueError("END carries no frame, confidence, or incident")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_family": self.candidate_family.value,
            "detector_profile": self.detector_profile.to_dict(),
            "probe_receipt_sha256": self.probe_receipt_sha256,
            "ordinal": self.ordinal,
            "event_kind": self.event_kind.value,
            "frame_index": self.frame_index,
            "confidence_milli": self.confidence_milli,
            "incident_code": self.incident_code,
            "source_event_sha256": self.source_event_sha256,
        }


@dataclass(frozen=True, slots=True)
class DetectorOutputNormalizationReceipt:
    probe_receipt: DetectorProbeReceipt
    events: tuple[NormalizedDetectorEvent, ...]
    validity: DetectorEvidenceValidity

    manifest_compiled: ClassVar[bool] = False
    media_read_performed: ClassVar[bool] = False
    runtime_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self.probe_receipt) is not DetectorProbeReceipt:
            raise TypeError("probe_receipt must be exact")
        if type(self.events) is not tuple:
            raise TypeError("events must be an exact tuple")
        if not 1 <= len(self.events) <= self.probe_receipt.plan.event_cap:
            raise ValueError("events must fit the exact plan event cap")
        if any(type(event) is not NormalizedDetectorEvent for event in self.events):
            raise TypeError("every event must be exact")
        if tuple(event.ordinal for event in self.events) != tuple(range(len(self.events))):
            raise ValueError("event ordinals must be contiguous from zero")
        if self.events[-1].event_kind is not DetectorEventKind.END:
            raise ValueError("the final normalized event must be END")
        if any(event.event_kind is DetectorEventKind.END for event in self.events[:-1]):
            raise ValueError("END may occur only once at the terminal ordinal")
        previous_frame = -1
        source_binding = self.probe_receipt.plan.source_binding
        if source_binding is None:
            raise ValueError("normalized output requires an exact R0 source_binding")
        if DetectorProbeKind.OUTPUT_NORMALIZATION not in self.probe_receipt.plan.probe_kinds:
            raise ValueError("normalized output requires an OUTPUT_NORMALIZATION probe")
        for event in self.events:
            if event.candidate_family is not self.probe_receipt.candidate_family:
                raise ValueError("event candidate borrowing is prohibited")
            if event.detector_profile != self.probe_receipt.detector_profile:
                raise ValueError("event detector profile borrowing is prohibited")
            if event.probe_receipt_sha256 != self.probe_receipt.receipt_sha256:
                raise ValueError("event probe receipt borrowing is prohibited")
            if event.event_kind is DetectorEventKind.SCENE_CANDIDATE:
                if event.frame_index >= source_binding.total_frames:  # type: ignore[operator]
                    raise ValueError("scene candidate frame exceeds the R0 source binding")
                if event.frame_index <= previous_frame:  # type: ignore[operator]
                    raise ValueError("scene candidate frames must be strictly increasing")
                previous_frame = event.frame_index  # type: ignore[assignment]
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be exact")
        if (
            self.validity is DetectorEvidenceValidity.CURRENT_VALID_JUDGED
            and self.probe_receipt.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("current-valid normalization requires a current-valid probe receipt")

    @property
    def candidate_family(self) -> DetectorCandidateFamily:
        return self.probe_receipt.candidate_family

    @property
    def detector_profile(self) -> DetectorProfile:
        return self.probe_receipt.detector_profile

    def to_dict(self) -> dict[str, Any]:
        return _record_payload(
            "DetectorOutputNormalizationReceipt",
            {
                "probe_receipt": self.probe_receipt.to_dict(),
                "events": [event.to_dict() for event in self.events],
                "validity": self.validity.value,
                "manifest_compiled": self.manifest_compiled,
                "media_read_performed": self.media_read_performed,
                "runtime_authorized": self.runtime_authorized,
            },
        )

    @property
    def receipt_sha256(self) -> str:
        return self.to_dict()["receipt_sha256"]


_SUPPORT_KINDS: dict[type[Any], frozenset[DetectorEvidenceKind]] = {
    DetectorArtifactComparisonReceipt: frozenset(
        {
            DetectorEvidenceKind.ARTIFACT_IDENTITY,
            DetectorEvidenceKind.VERSION_PIN,
            DetectorEvidenceKind.ARTIFACT_SHA256,
            DetectorEvidenceKind.PLATFORM_ARCH,
        }
    ),
    DetectorLicenseProvenanceReceipt: frozenset(
        {
            DetectorEvidenceKind.PROVENANCE,
            DetectorEvidenceKind.LICENSE,
            DetectorEvidenceKind.DISTRIBUTION_POLICY,
        }
    ),
    DetectorMaterializationReceipt: frozenset(
        {DetectorEvidenceKind.DEPENDENCY_GRAPH, DetectorEvidenceKind.OFFLINE_MATERIALIZATION}
    ),
    DetectorProbeReceipt: frozenset(
        {DetectorEvidenceKind.RUNTIME_CAPABILITY, DetectorEvidenceKind.RESOURCE_BOUNDS}
    ),
    DetectorOutputNormalizationReceipt: frozenset(
        {DetectorEvidenceKind.OUTPUT_NORMALIZATION}
    ),
}


def project_detector_evidence_claim(
    evidence_kind: DetectorEvidenceKind,
    support_receipt: (
        DetectorArtifactComparisonReceipt
        | DetectorLicenseProvenanceReceipt
        | DetectorMaterializationReceipt
        | DetectorProbeReceipt
        | DetectorOutputNormalizationReceipt
    ),
    authority_scope_sha256: str,
) -> DetectorEvidenceClaim:
    """Project exact current-valid support into one existing R1B1 claim."""

    if type(evidence_kind) is not DetectorEvidenceKind:
        raise TypeError("evidence_kind must be exact")
    support_type = type(support_receipt)
    if support_type not in _SUPPORT_KINDS:
        raise TypeError("support_receipt type is not closed")
    if evidence_kind not in _SUPPORT_KINDS[support_type]:
        raise ValueError("support receipt cannot strengthen into this Evidence kind")
    validate_sha256(authority_scope_sha256, field_name="authority_scope_sha256")
    if support_receipt.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED:
        raise ValueError("support receipt is not current-valid judged")
    if isinstance(support_receipt, DetectorArtifactComparisonReceipt):
        if support_receipt.comparison_state is not DetectorArtifactComparisonState.MATCH:
            raise ValueError("artifact Evidence requires an exact expected/observed MATCH")
    elif isinstance(support_receipt, DetectorLicenseProvenanceReceipt):
        if support_receipt.license_state is not DetectorLicenseState.CLEARED:
            raise ValueError("license Evidence requires CLEARED state")
    elif isinstance(support_receipt, DetectorMaterializationReceipt):
        if support_receipt.materialization_state is not DetectorMaterializationState.VERIFIED_CONTAINED:
            raise ValueError("materialization Evidence requires VERIFIED_CONTAINED state")
    elif isinstance(support_receipt, DetectorProbeReceipt):
        if (
            support_receipt.plan.artifact_comparison.comparison_state
            is not DetectorArtifactComparisonState.MATCH
            or support_receipt.plan.artifact_comparison.validity
            is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        ):
            raise ValueError("probe Evidence requires an exact current-valid artifact MATCH")
        if any(outcome.disposition is not DetectorProbeDisposition.PASS for outcome in support_receipt.outcomes):
            raise ValueError("probe Evidence requires every planned outcome PASS")
        required_probe = {
            DetectorEvidenceKind.RUNTIME_CAPABILITY: DetectorProbeKind.SCENE_FILTER_CAPABILITY,
            DetectorEvidenceKind.RESOURCE_BOUNDS: DetectorProbeKind.RESOURCE_BOUNDS,
        }[evidence_kind]
        if required_probe not in support_receipt.plan.probe_kinds:
            raise ValueError("probe receipt lacks the exact required probe kind")
    else:
        if support_receipt.probe_receipt.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED:
            raise ValueError("normalization Evidence requires a current-valid probe receipt")
        if DetectorProbeKind.OUTPUT_NORMALIZATION not in support_receipt.probe_receipt.plan.probe_kinds:
            raise ValueError("normalization receipt lacks OUTPUT_NORMALIZATION probe binding")
        if any(event.event_kind is DetectorEventKind.INCIDENT for event in support_receipt.events):
            raise ValueError("normalization Evidence cannot contain an INCIDENT event")

    return DetectorEvidenceClaim(
        support_receipt.candidate_family,
        support_receipt.detector_profile,
        evidence_kind,
        support_receipt.receipt_sha256,
        authority_scope_sha256,
        DetectorEvidenceValidity.CURRENT_VALID_JUDGED,
    )
