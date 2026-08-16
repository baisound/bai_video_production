"""Pure TASK-005 real-detector admission contract.

This module classifies typed Evidence receipts for detector candidates.  It has
no executable path, media body, runner, callback, filesystem, subprocess,
network, provider, model, or native-runtime surface.  Even an ``ADMITTED``
decision is contract-only and never grants runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from .scene_boundary import DetectorProfile
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


class DetectorCandidateFamily(str, Enum):
    BOUNDED_SYNTHETIC = "BOUNDED_SYNTHETIC"
    FFMPEG_SCENE_FILTER_PROFILE_FAMILY = "FFMPEG_SCENE_FILTER_PROFILE_FAMILY"
    FFPROBE_METADATA_ONLY = "FFPROBE_METADATA_ONLY"
    PYSCENEDETECT_CONTENT_PROFILE_FAMILY = "PYSCENEDETECT_CONTENT_PROFILE_FAMILY"
    OPENCV_CUSTOM_PROFILE_FAMILY = "OPENCV_CUSTOM_PROFILE_FAMILY"
    FFMPEG_SILENCE_AUDIO_ONLY = "FFMPEG_SILENCE_AUDIO_ONLY"
    UNKNOWN = "UNKNOWN"


class DetectorAdmissionState(str, Enum):
    CONTRACT_READY_NO_RUNTIME = "CONTRACT_READY_NO_RUNTIME"
    ACQUISITION_GATE_REQUIRED = "ACQUISITION_GATE_REQUIRED"
    LICENSE_REVIEW_REQUIRED = "LICENSE_REVIEW_REQUIRED"
    CAPABILITY_EVIDENCE_REQUIRED = "CAPABILITY_EVIDENCE_REQUIRED"
    NOT_ADMISSIBLE = "NOT_ADMISSIBLE"
    UNKNOWN = "UNKNOWN"
    ADMITTED = "ADMITTED"


class DetectorEvidenceKind(str, Enum):
    ARTIFACT_IDENTITY = "ARTIFACT_IDENTITY"
    VERSION_PIN = "VERSION_PIN"
    ARTIFACT_SHA256 = "ARTIFACT_SHA256"
    PROVENANCE = "PROVENANCE"
    LICENSE = "LICENSE"
    DISTRIBUTION_POLICY = "DISTRIBUTION_POLICY"
    DEPENDENCY_GRAPH = "DEPENDENCY_GRAPH"
    PLATFORM_ARCH = "PLATFORM_ARCH"
    OFFLINE_MATERIALIZATION = "OFFLINE_MATERIALIZATION"
    RUNTIME_CAPABILITY = "RUNTIME_CAPABILITY"
    RESOURCE_BOUNDS = "RESOURCE_BOUNDS"
    OUTPUT_NORMALIZATION = "OUTPUT_NORMALIZATION"


class DetectorEvidenceValidity(str, Enum):
    CURRENT_VALID_JUDGED = "CURRENT_VALID_JUDGED"
    STALE = "STALE"
    REVOKED = "REVOKED"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


_REAL_CANDIDATES = frozenset(
    {
        DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY,
        DetectorCandidateFamily.PYSCENEDETECT_CONTENT_PROFILE_FAMILY,
        DetectorCandidateFamily.OPENCV_CUSTOM_PROFILE_FAMILY,
    }
)
_NOT_DETECTORS = frozenset(
    {
        DetectorCandidateFamily.FFPROBE_METADATA_ONLY,
        DetectorCandidateFamily.FFMPEG_SILENCE_AUDIO_ONLY,
    }
)
_REQUIRED_EVIDENCE = tuple(DetectorEvidenceKind)
_LICENSE_EVIDENCE = frozenset(
    {DetectorEvidenceKind.LICENSE, DetectorEvidenceKind.DISTRIBUTION_POLICY}
)
_ACQUISITION_EVIDENCE = frozenset(
    {
        DetectorEvidenceKind.ARTIFACT_IDENTITY,
        DetectorEvidenceKind.VERSION_PIN,
        DetectorEvidenceKind.ARTIFACT_SHA256,
        DetectorEvidenceKind.PROVENANCE,
        DetectorEvidenceKind.DEPENDENCY_GRAPH,
        DetectorEvidenceKind.PLATFORM_ARCH,
        DetectorEvidenceKind.OFFLINE_MATERIALIZATION,
    }
)
_CAPABILITY_EVIDENCE = frozenset(
    {
        DetectorEvidenceKind.RUNTIME_CAPABILITY,
        DetectorEvidenceKind.RESOURCE_BOUNDS,
        DetectorEvidenceKind.OUTPUT_NORMALIZATION,
    }
)
_MAX_EVIDENCE_CLAIMS = len(_REQUIRED_EVIDENCE)
_DECISION_CONSTRUCTION_TOKEN = object()


@dataclass(frozen=True, slots=True)
class DetectorEvidenceClaim:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    evidence_kind: DetectorEvidenceKind
    receipt_sha256: str
    authority_scope_sha256: str
    validity: DetectorEvidenceValidity

    def __post_init__(self) -> None:
        if type(self.candidate_family) is not DetectorCandidateFamily:
            raise TypeError("candidate_family must be an exact DetectorCandidateFamily")
        if self.candidate_family not in _REAL_CANDIDATES:
            raise ValueError("Evidence claims are accepted only for real detector families")
        if type(self.detector_profile) is not DetectorProfile:
            raise TypeError("detector_profile must be an exact DetectorProfile")
        if type(self.evidence_kind) is not DetectorEvidenceKind:
            raise TypeError("evidence_kind must be an exact DetectorEvidenceKind")
        if type(self.validity) is not DetectorEvidenceValidity:
            raise TypeError("validity must be an exact DetectorEvidenceValidity")
        validate_sha256(self.receipt_sha256, field_name="receipt_sha256")
        validate_sha256(self.authority_scope_sha256, field_name="authority_scope_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_family": self.candidate_family.value,
            "detector_profile": self.detector_profile.to_dict(),
            "evidence_kind": self.evidence_kind.value,
            "receipt_sha256": self.receipt_sha256,
            "authority_scope_sha256": self.authority_scope_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True, init=False)
class DetectorAdmissionDecision:
    candidate_family: DetectorCandidateFamily
    detector_profile: DetectorProfile
    evidence_claims: tuple[DetectorEvidenceClaim, ...]
    missing_evidence: tuple[DetectorEvidenceKind, ...]
    admission_state: DetectorAdmissionState

    contract_version: ClassVar[str] = "1.0.0"
    selected_contract_candidate: ClassVar[DetectorCandidateFamily] = (
        DetectorCandidateFamily.FFMPEG_SCENE_FILTER_PROFILE_FAMILY
    )
    selected_runtime_candidate: ClassVar[None] = None
    runtime_authorized: ClassVar[bool] = False
    media_read_performed: ClassVar[bool] = False
    external_effect_performed: ClassVar[bool] = False

    def __init__(
        self,
        candidate_family: DetectorCandidateFamily,
        detector_profile: DetectorProfile,
        evidence_claims: tuple[DetectorEvidenceClaim, ...],
        missing_evidence: tuple[DetectorEvidenceKind, ...],
        admission_state: DetectorAdmissionState,
        *,
        _construction_token: object,
    ) -> None:
        if _construction_token is not _DECISION_CONSTRUCTION_TOKEN:
            raise ValueError("admission decisions must be created by the evaluator")
        object.__setattr__(self, "candidate_family", candidate_family)
        object.__setattr__(self, "detector_profile", detector_profile)
        object.__setattr__(self, "evidence_claims", evidence_claims)
        object.__setattr__(self, "missing_evidence", missing_evidence)
        object.__setattr__(self, "admission_state", admission_state)
        self.__post_init__()

    def __post_init__(self) -> None:
        if type(self.candidate_family) is not DetectorCandidateFamily:
            raise TypeError("candidate_family must be an exact DetectorCandidateFamily")
        if type(self.detector_profile) is not DetectorProfile:
            raise TypeError("detector_profile must be an exact DetectorProfile")
        if type(self.evidence_claims) is not tuple:
            raise TypeError("evidence_claims must be an exact tuple")
        if any(type(claim) is not DetectorEvidenceClaim for claim in self.evidence_claims):
            raise TypeError("every Evidence claim must be exact")
        if type(self.missing_evidence) is not tuple:
            raise TypeError("missing_evidence must be an exact tuple")
        if any(type(kind) is not DetectorEvidenceKind for kind in self.missing_evidence):
            raise TypeError("every missing Evidence kind must be exact")
        if type(self.admission_state) is not DetectorAdmissionState:
            raise TypeError("admission_state must be exact")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contract_version": self.contract_version,
            "candidate_family": self.candidate_family.value,
            "detector_profile": self.detector_profile.to_dict(),
            "evidence_claims": [claim.to_dict() for claim in self.evidence_claims],
            "missing_evidence": [kind.value for kind in self.missing_evidence],
            "admission_state": self.admission_state.value,
            "selected_contract_candidate": self.selected_contract_candidate.value,
            "candidate_is_selected_contract": (
                self.candidate_family is self.selected_contract_candidate
            ),
            "selected_runtime_candidate": self.selected_runtime_candidate,
            "runtime_authorized": self.runtime_authorized,
            "media_read_performed": self.media_read_performed,
            "external_effect_performed": self.external_effect_performed,
        }
        body["decision_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def evaluate_detector_admission(
    candidate_family: DetectorCandidateFamily,
    detector_profile: DetectorProfile,
    evidence_claims: tuple[DetectorEvidenceClaim, ...],
) -> DetectorAdmissionDecision:
    """Classify a candidate without authorizing or executing a runtime."""

    if type(candidate_family) is not DetectorCandidateFamily:
        raise TypeError("candidate_family must be an exact DetectorCandidateFamily")
    if type(detector_profile) is not DetectorProfile:
        raise TypeError("detector_profile must be an exact DetectorProfile")
    if type(evidence_claims) is not tuple:
        raise TypeError("evidence_claims must be an exact tuple")
    if len(evidence_claims) > _MAX_EVIDENCE_CLAIMS:
        raise ValueError("evidence_claims exceeds the exact maximum of 12")
    if any(type(claim) is not DetectorEvidenceClaim for claim in evidence_claims):
        raise TypeError("every Evidence claim must be exact")

    if candidate_family is DetectorCandidateFamily.BOUNDED_SYNTHETIC:
        if evidence_claims:
            raise ValueError("synthetic contract accepts no runtime Evidence claims")
        return DetectorAdmissionDecision(
            candidate_family,
            detector_profile,
            evidence_claims,
            (),
            DetectorAdmissionState.CONTRACT_READY_NO_RUNTIME,
            _construction_token=_DECISION_CONSTRUCTION_TOKEN,
        )
    if candidate_family in _NOT_DETECTORS:
        if evidence_claims:
            raise ValueError("non-detector candidates accept no detector Evidence claims")
        return DetectorAdmissionDecision(
            candidate_family,
            detector_profile,
            evidence_claims,
            (),
            DetectorAdmissionState.NOT_ADMISSIBLE,
            _construction_token=_DECISION_CONSTRUCTION_TOKEN,
        )
    if candidate_family is DetectorCandidateFamily.UNKNOWN:
        if evidence_claims:
            raise ValueError("UNKNOWN candidate accepts no Evidence claims")
        return DetectorAdmissionDecision(
            candidate_family,
            detector_profile,
            evidence_claims,
            _REQUIRED_EVIDENCE,
            DetectorAdmissionState.UNKNOWN,
            _construction_token=_DECISION_CONSTRUCTION_TOKEN,
        )

    if candidate_family not in _REAL_CANDIDATES:
        raise ValueError("candidate family is not closed")
    kinds = tuple(claim.evidence_kind for claim in evidence_claims)
    if len(set(kinds)) != len(kinds):
        raise ValueError("Evidence kinds must be unique")
    order = {kind: index for index, kind in enumerate(_REQUIRED_EVIDENCE)}
    if kinds != tuple(sorted(kinds, key=order.__getitem__)):
        raise ValueError("Evidence claims must be in canonical kind order")
    for claim in evidence_claims:
        if claim.candidate_family is not candidate_family:
            raise ValueError("Evidence claim candidate mismatch")
        if claim.detector_profile != detector_profile:
            raise ValueError("Evidence claim profile mismatch")

    present = frozenset(kinds)
    missing = tuple(kind for kind in _REQUIRED_EVIDENCE if kind not in present)
    if any(
        claim.validity is not DetectorEvidenceValidity.CURRENT_VALID_JUDGED
        for claim in evidence_claims
    ):
        state = DetectorAdmissionState.UNKNOWN
    elif _LICENSE_EVIDENCE.intersection(missing):
        state = DetectorAdmissionState.LICENSE_REVIEW_REQUIRED
    elif _ACQUISITION_EVIDENCE.intersection(missing):
        state = DetectorAdmissionState.ACQUISITION_GATE_REQUIRED
    elif _CAPABILITY_EVIDENCE.intersection(missing):
        state = DetectorAdmissionState.CAPABILITY_EVIDENCE_REQUIRED
    elif missing:
        state = DetectorAdmissionState.UNKNOWN
    else:
        state = DetectorAdmissionState.ADMITTED

    return DetectorAdmissionDecision(
        candidate_family,
        detector_profile,
        evidence_claims,
        missing,
        state,
        _construction_token=_DECISION_CONSTRUCTION_TOKEN,
    )
