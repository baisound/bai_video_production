"""TASK-013 Scene-Compatible Reference / Shot Feasibility Gate foundation.

The first implementation is intentionally fail-closed.  It validates deterministic
reference/continuity contracts and accepts explicit Human-reviewed feasibility
checks; it does not pretend to prove room geometry automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


class ContinuityType(str, Enum):
    CUT = "CUT"
    DIRECT_CONTINUATION = "DIRECT_CONTINUATION"
    MATCH_CUT = "MATCH_CUT"
    GRAPHIC_TRANSITION = "GRAPHIC_TRANSITION"


class StartFrameSource(str, Enum):
    NEW = "NEW"
    PREV_END = "PREV_END"


class CheckState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"


class AssessmentStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


_REQUIRED_CHECKS = (
    "subject_position_exists",
    "orientation_camera_compatible",
    "required_visible_coexists",
    "prohibited_change_not_required",
    "shot_reference_matches_final_camera",
    "reference_roles_valid",
    "continuity_contract_valid",
    "task_axis_valid",
    "depth_order_valid",
    "occlusion_valid",
    "furniture_integrity_valid",
    "room_anchor_integrity_valid",
    "production_gear_absent",
    "character_identity_valid",
)


@dataclass(frozen=True, slots=True)
class SceneGenerationReferenceSpec:
    scene_id: str
    continuity_type: ContinuityType
    character_required: bool
    character_identity_profile_id: str | None
    character_reference_asset_ids: tuple[str, ...]
    room_master_asset_id: str | None
    room_shot_reference_asset_id: str | None
    style_reference_asset_id: str | None
    required_visible: tuple[str, ...]
    subject_orientation: str
    camera_semantic: str
    start_frame_source: StartFrameSource
    previous_end_asset_id: str | None = None
    previous_end_sha256: str | None = None
    start_asset_id: str | None = None
    start_asset_sha256: str | None = None
    prohibited_changes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.scene_id, "scene_id")
        for name, value in (
            ("character_identity_profile_id", self.character_identity_profile_id),
            ("room_master_asset_id", self.room_master_asset_id),
            ("room_shot_reference_asset_id", self.room_shot_reference_asset_id),
            ("style_reference_asset_id", self.style_reference_asset_id),
            ("previous_end_asset_id", self.previous_end_asset_id),
            ("start_asset_id", self.start_asset_id),
        ):
            if value is not None:
                _id(value, name)
        for value in self.character_reference_asset_ids:
            _id(value, "character_reference_asset_id")
        for name, value in (("previous_end_sha256", self.previous_end_sha256), ("start_asset_sha256", self.start_asset_sha256)):
            if value is not None:
                _sha(value, name)
        if not self.subject_orientation.strip() or not self.camera_semantic.strip():
            raise ValueError("subject_orientation and camera_semantic must be non-empty")
        if not self.required_visible:
            raise ValueError("required_visible must not be empty")
        for value in self.required_visible + self.prohibited_changes:
            _id(value, "contract code")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "spec_version": "1.0.0",
            "task_owner": "TASK-013",
            "scene_id": self.scene_id,
            "continuity_type": self.continuity_type.value,
            "character_required": self.character_required,
            "character_identity_profile_id": self.character_identity_profile_id,
            "character_reference_asset_ids": list(self.character_reference_asset_ids),
            "room_master_asset_id": self.room_master_asset_id,
            "room_shot_reference_asset_id": self.room_shot_reference_asset_id,
            "style_reference_asset_id": self.style_reference_asset_id,
            "required_visible": list(self.required_visible),
            "subject_orientation": self.subject_orientation,
            "camera_position": {"semantic": self.camera_semantic},
            "start_frame_source": self.start_frame_source.value,
            "previous_end_asset_id": self.previous_end_asset_id,
            "previous_end_sha256": self.previous_end_sha256,
            "start_asset_id": self.start_asset_id,
            "start_asset_sha256": self.start_asset_sha256,
            "prohibited_changes": list(self.prohibited_changes),
        }
        body["reference_spec_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class ShotFeasibilityAssessment:
    scene_id: str
    checks: Mapping[str, CheckState]
    decision_source: str
    blocking_reasons: tuple[str, ...] = ()
    reference_spec_sha256: str | None = None

    def __post_init__(self) -> None:
        _id(self.scene_id, "scene_id")
        if set(self.checks) != set(_REQUIRED_CHECKS):
            raise ValueError("assessment must contain exactly the required checks")
        if not self.decision_source.strip():
            raise ValueError("decision_source must be non-empty")
        for value in self.blocking_reasons:
            _id(value, "blocking_reason")
        if self.reference_spec_sha256 is not None:
            _sha(self.reference_spec_sha256, "reference_spec_sha256")

    @property
    def status(self) -> AssessmentStatus:
        values = tuple(self.checks.values())
        if CheckState.FAIL in values:
            return AssessmentStatus.FAIL
        if CheckState.UNVERIFIED in values:
            return AssessmentStatus.REVIEW_REQUIRED
        return AssessmentStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "assessment_version": "1.0.0",
            "task_owner": "TASK-013",
            "scene_id": self.scene_id,
            "status": self.status.value,
            "checks": {key: self.checks[key].value for key in _REQUIRED_CHECKS},
            "decision_source": self.decision_source,
            "blocking_reasons": list(self.blocking_reasons),
            "reference_spec_sha256": self.reference_spec_sha256,
            "automatic_geometry_proof_claimed": False,
        }
        body["assessment_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


class ShotFeasibilityGate:
    @staticmethod
    def deterministic_checks(spec: SceneGenerationReferenceSpec) -> dict[str, CheckState]:
        checks = {name: CheckState.UNVERIFIED for name in _REQUIRED_CHECKS}

        reference_roles_ok = True
        if spec.character_required:
            reference_roles_ok = bool(spec.character_identity_profile_id and spec.character_reference_asset_ids)
        if spec.character_required and spec.room_master_asset_id is not None and spec.room_shot_reference_asset_id is None:
            reference_roles_ok = False
        checks["reference_roles_valid"] = CheckState.PASS if reference_roles_ok else CheckState.FAIL

        continuity_ok = True
        if spec.continuity_type is ContinuityType.DIRECT_CONTINUATION:
            continuity_ok = (
                spec.start_frame_source is StartFrameSource.PREV_END
                and spec.previous_end_asset_id is not None
                and spec.previous_end_sha256 is not None
                and spec.start_asset_id == spec.previous_end_asset_id
                and spec.start_asset_sha256 == spec.previous_end_sha256
            )
        elif spec.start_frame_source is StartFrameSource.PREV_END:
            continuity_ok = spec.previous_end_asset_id is not None and spec.previous_end_sha256 is not None
        checks["continuity_contract_valid"] = CheckState.PASS if continuity_ok else CheckState.FAIL

        return checks

    @classmethod
    def assess(
        cls,
        spec: SceneGenerationReferenceSpec,
        *,
        human_reviewed_checks: Mapping[str, CheckState] | None = None,
        blocking_reasons: tuple[str, ...] = (),
    ) -> ShotFeasibilityAssessment:
        checks = cls.deterministic_checks(spec)
        if human_reviewed_checks is not None:
            unknown = set(human_reviewed_checks) - set(_REQUIRED_CHECKS)
            if unknown:
                raise ValueError("human_reviewed_checks contains unknown checks")
            for key, value in human_reviewed_checks.items():
                if key in {"reference_roles_valid", "continuity_contract_valid"}:
                    # Human review cannot turn a deterministic contract FAIL into PASS.
                    if checks[key] is CheckState.FAIL and value is CheckState.PASS:
                        continue
                checks[key] = value
        reasons = list(blocking_reasons)
        if checks["reference_roles_valid"] is CheckState.FAIL:
            reasons.append("REFERENCE_ROLE_CONFLICT")
        if checks["continuity_contract_valid"] is CheckState.FAIL:
            reasons.append("DIRECT_CONTINUATION_ASSET_MISMATCH")
        return ShotFeasibilityAssessment(
            spec.scene_id,
            checks,
            "HUMAN_REVIEWED_STRUCTURED_ASSERTION" if human_reviewed_checks is not None else "DETERMINISTIC_CONTRACT_ONLY",
            tuple(dict.fromkeys(reasons)),
            spec.to_dict()["reference_spec_sha256"],
        )

    @staticmethod
    def require_generation_ready(assessment: ShotFeasibilityAssessment) -> None:
        if assessment.status is AssessmentStatus.PASS:
            return
        raise ProductError(
            "ERR_SHOT_FEASIBILITY_NOT_READY",
            "Scene references are not ready for provider generation",
            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            details={"status": assessment.status.value, "blocking_reasons": list(assessment.blocking_reasons)},
        )
