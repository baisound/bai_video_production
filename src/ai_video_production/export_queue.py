"""TASK-044 P-NLE-3 closed Export preparation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from pathlib import PureWindowsPath
from typing import Any, Mapping

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .final_review import FinalReviewApprovalReceipt

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    if ("\\" in value or value.startswith("/") or PureWindowsPath(value).drive
            or ".." in value.split("/")
            or any(term in value.casefold() for term in ("credential", "password", "secret", "token"))):
        raise ValueError(f"{name} must be a logical identity, not a host path")
    return value


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


class ExportAuthorityClass(str, Enum):
    LOCAL_PACKAGE = "LOCAL_PACKAGE"
    RESOLVE_RENDER = "RESOLVE_RENDER"


@dataclass(frozen=True, slots=True)
class ExportOutputContract:
    width: int
    height: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    audio_sample_rate_hz: int
    audio_channels: int
    container: str
    video_codec: str
    audio_codec: str

    def __post_init__(self) -> None:
        for name in ("width", "height", "frame_rate_numerator", "frame_rate_denominator",
                     "audio_sample_rate_hz", "audio_channels"):
            _positive_int(getattr(self, name), name)
        for name in ("container", "video_codec", "audio_codec"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SAFE_TOKEN.fullmatch(value):
                raise ValueError(f"{name} is invalid")

    def to_dict(self) -> dict[str, object]:
        return {"width": self.width, "height": self.height,
                "frame_rate": {"numerator": self.frame_rate_numerator,
                               "denominator": self.frame_rate_denominator},
                "audio_sample_rate_hz": self.audio_sample_rate_hz,
                "audio_channels": self.audio_channels, "container": self.container,
                "video_codec": self.video_codec, "audio_codec": self.audio_codec}


@dataclass(frozen=True, slots=True)
class ExportPreset:
    preset_id: str
    preset_version: str
    output: ExportOutputContract

    def __post_init__(self) -> None:
        _identity(self.preset_id, "preset_id")
        if not isinstance(self.preset_version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.preset_version):
            raise ValueError("preset_version is invalid")
        if not isinstance(self.output, ExportOutputContract):
            raise ValueError("output contract is invalid")

    def to_dict(self) -> dict[str, object]:
        body = {"preset_id": self.preset_id, "preset_version": self.preset_version,
                "output": self.output.to_dict()}
        return {**body, "preset_sha256": sha256_bytes(canonical_json_bytes(body))}

    @property
    def preset_sha256(self) -> str:
        return self.to_dict()["preset_sha256"]


@dataclass(frozen=True, slots=True)
class ExportPreparation:
    project_id: str
    project_manifest_sha256: str
    product_version: str
    timeline_plan_id: str
    timeline_revision: int
    timeline_sha256: str
    edit_plan_sha256: str
    assembly_plan_sha256: str
    final_approval: FinalReviewApprovalReceipt
    preset: ExportPreset
    output_target_identity: str
    authority_class: ExportAuthorityClass
    resolve_project_identity: str | None = None
    resolve_timeline_identity: str | None = None
    estimated_cost: float | None = None
    currency: str | None = None
    estimate_source: str | None = None

    def __post_init__(self) -> None:
        for value, name in ((self.project_id, "project_id"),
                            (self.timeline_plan_id, "timeline_plan_id"),
                            (self.output_target_identity, "output_target_identity")):
            _identity(value, name)
        validate_sha256(self.project_manifest_sha256, field_name="project_manifest_sha256")
        validate_sha256(self.timeline_sha256, field_name="timeline_sha256")
        validate_sha256(self.edit_plan_sha256, field_name="edit_plan_sha256")
        validate_sha256(self.assembly_plan_sha256, field_name="assembly_plan_sha256")
        if not isinstance(self.final_approval, FinalReviewApprovalReceipt):
            raise ValueError("final_approval must be a typed receipt")
        if self.final_approval.project_id != self.project_id:
            raise ValueError("Export preparation crosses Final Review Project")
        if self.final_approval.project_manifest_sha256 != self.project_manifest_sha256:
            raise ValueError("Export preparation crosses Final Review Project Manifest")
        if self.final_approval.timeline_sha256 != self.timeline_sha256:
            raise ValueError("Export preparation crosses Final Review Timeline")
        _positive_int(self.timeline_revision, "timeline_revision")
        if not isinstance(self.product_version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.product_version):
            raise ValueError("product_version is invalid")
        if not isinstance(self.preset, ExportPreset) or not isinstance(self.authority_class, ExportAuthorityClass):
            raise ValueError("preset or authority class is invalid")
        identities = (self.resolve_project_identity, self.resolve_timeline_identity)
        if self.authority_class is ExportAuthorityClass.RESOLVE_RENDER:
            if any(value is None for value in identities):
                raise ValueError("Resolve render requires exact Project and Timeline identities")
        elif any(value is not None for value in identities):
            raise ValueError("local export cannot carry Resolve identities")
        for value, name in zip(identities, ("resolve_project_identity", "resolve_timeline_identity")):
            if value is not None:
                _identity(value, name)
        if self.estimated_cost is not None and (isinstance(self.estimated_cost, bool) or not isinstance(self.estimated_cost, (int, float)) or self.estimated_cost < 0):
            raise ValueError("estimated_cost is invalid")
        if (self.currency is None) != (self.estimated_cost is None):
            raise ValueError("currency must exist exactly when cost is known")
        if self.currency is not None and not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("currency is invalid")
        if (self.estimate_source is None) != (self.estimated_cost is None):
            raise ValueError("estimate_source must exist exactly when cost is known")
        if self.estimate_source is not None:
            _identity(self.estimate_source, "estimate_source")

    @property
    def export_profile_sha256(self) -> str:
        """Digest every logical field that can change Export execution.

        Host destinations and one-shot authority tokens are deliberately absent;
        those remain launcher-private.  The digest is persisted as a Job input so
        a changed preset, output contract, logical target or Resolve target cannot
        reuse an older durable Job after restart.
        """
        body = {
            "preset": self.preset.to_dict(),
            "output_target_identity": self.output_target_identity,
            "authority_class": self.authority_class.value,
            "resolve_project_identity": self.resolve_project_identity,
            "resolve_timeline_identity": self.resolve_timeline_identity,
        }
        return sha256_bytes(canonical_json_bytes(body))

    @property
    def input_hashes(self) -> Mapping[str, str]:
        return {"project_manifest": self.project_manifest_sha256,
                "timeline": self.timeline_sha256, "edit_plan": self.edit_plan_sha256,
                "assembly_plan": self.assembly_plan_sha256,
                "final_approval": self.final_approval.final_approval_receipt_sha256,
                "preset": self.preset.preset_sha256,
                "export_profile": self.export_profile_sha256}

    def to_dict(self) -> dict[str, Any]:
        body = {"preparation_version": "1.0.0", "task_owner": "TASK-044/P-NLE-3",
                "project_id": self.project_id,
                "project_manifest_sha256": self.project_manifest_sha256,
                "product_version": self.product_version,
                "timeline_plan_id": self.timeline_plan_id,
                "timeline_revision": self.timeline_revision,
                "timeline_sha256": self.timeline_sha256,
                "edit_plan_sha256": self.edit_plan_sha256,
                "assembly_plan_sha256": self.assembly_plan_sha256,
                "final_approval_receipt_sha256": self.final_approval.final_approval_receipt_sha256,
                "preset": self.preset.to_dict(),
                "export_profile_sha256": self.export_profile_sha256,
                "output_target_identity": self.output_target_identity,
                "authority_class": self.authority_class.value,
                "resolve_project_identity": self.resolve_project_identity,
                "resolve_timeline_identity": self.resolve_timeline_identity,
                "estimated_cost": self.estimated_cost, "currency": self.currency,
                "estimate_source": self.estimate_source,
                "host_output_path_persisted": False,
                "external_mutation_authorized": False}
        return {**body, "preparation_sha256": sha256_bytes(canonical_json_bytes(body))}

    @property
    def preparation_sha256(self) -> str:
        return self.to_dict()["preparation_sha256"]


@dataclass(frozen=True, slots=True)
class ExportDispatchResult:
    state: str
    result_identity: str | None = None
    render_qa_sha256: str | None = None
    render_qa_passed: bool | None = None
    actual_cost: float | None = None

    def __post_init__(self) -> None:
        if self.state not in {"RUNNING", "SUCCEEDED"}:
            raise ValueError("dispatch result state is invalid")
        if self.state == "RUNNING":
            if any(value is not None for value in (self.result_identity, self.render_qa_sha256,
                                                    self.render_qa_passed, self.actual_cost)):
                raise ValueError("RUNNING cannot claim result or QA")
            return
        _identity(self.result_identity, "result_identity")
        validate_sha256(self.render_qa_sha256, field_name="render_qa_sha256")
        if self.render_qa_passed is not True:
            raise ValueError("SUCCEEDED requires passing Render QA Evidence")
        if self.actual_cost is not None and (isinstance(self.actual_cost, bool)
                or not isinstance(self.actual_cost, (int, float)) or self.actual_cost < 0):
            raise ValueError("actual_cost is invalid")

    @property
    def durable_result_ref(self) -> str | None:
        if self.state != "SUCCEEDED":
            return None
        body = {"result_identity": self.result_identity,
                "render_qa_sha256": self.render_qa_sha256,
                "render_qa_passed": True}
        return "export-result:" + sha256_bytes(canonical_json_bytes(body)).split(":", 1)[1]


__all__ = ["ExportAuthorityClass", "ExportDispatchResult", "ExportOutputContract",
           "ExportPreparation", "ExportPreset"]
