"""TASK-054 R6C body-free quarantined artifact sealing contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping

from .dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationReport,
    OfflineEvaluationArm,
    OfflineGateStatus,
    admit_dbd_reasoning_offline_evaluation_report,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


_MANIFEST_RE = re.compile(r"ART-[0-9A-HJKMNP-TV-Z]{26}")
_QUARANTINE_RE = re.compile(r"model-quarantine://task054/[0-9A-HJKMNP-TV-Z]{26}")
_MODEL_REF_RE = re.compile(r"model-cache://task054/[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
_ADAPTER_REF_RE = re.compile(r"model-quarantine://task054/[0-9A-HJKMNP-TV-Z]{26}/adapter")
_PATH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,239}")
_STATE = "QUARANTINED_EVALUATED_NO_APPROVAL_OR_ACTIVATION"
_MAX_FILES = 4096
_MAX_TOTAL_BYTES = 1024 * 1024 * 1024


class ArtifactFileRole(str, Enum):
    ADAPTER = "ADAPTER"
    CONFIG = "CONFIG"
    TOKENIZER = "TOKENIZER"
    METADATA = "METADATA"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class ArtifactFileEvidence:
    logical_path: str
    role: ArtifactFileRole
    size_bytes: int
    content_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.logical_path, str)
            or not _PATH_RE.fullmatch(self.logical_path)
            or self.logical_path.startswith("/")
            or "//" in self.logical_path
            or any(part in {"", ".", ".."} for part in self.logical_path.split("/"))
        ):
            raise ValueError("artifact logical_path is invalid")
        if not isinstance(self.role, ArtifactFileRole):
            raise ValueError("artifact role is invalid")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 1:
            raise ValueError("artifact size_bytes must be positive")
        validate_sha256(self.content_sha256, field_name="content_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_path": self.logical_path,
            "role": self.role.value,
            "size_bytes": self.size_bytes,
            "content_sha256": self.content_sha256,
        }


def artifact_role_set_sha256(
    files: tuple[ArtifactFileEvidence, ...], role: ArtifactFileRole,
) -> str:
    selected = [item.to_dict() for item in files if item.role is role]
    if not selected:
        raise ValueError("artifact role set cannot be empty")
    return sha256_bytes(canonical_json_bytes(selected))


@dataclass(frozen=True, slots=True)
class QuarantinedArtifactManifest:
    artifact_manifest_id: str
    quarantine_ref: str
    base_model_ref: str
    base_model_sha256: str
    adapter_ref: str
    adapter_sha256: str
    files: tuple[ArtifactFileEvidence, ...]
    total_bytes: int
    training_dataset_sha256: str
    training_recipe_sha256: str
    evaluation_report_sha256: str
    rights_manifest_sha256: str
    test_sample_set_sha256: str
    tuned_binding_sha256: str
    sealed_at: str
    state: str = _STATE

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_manifest_id, str) or not _MANIFEST_RE.fullmatch(self.artifact_manifest_id):
            raise ValueError("artifact_manifest_id is invalid")
        if not isinstance(self.quarantine_ref, str) or not _QUARANTINE_RE.fullmatch(self.quarantine_ref):
            raise ValueError("quarantine_ref is invalid")
        if not isinstance(self.base_model_ref, str) or not _MODEL_REF_RE.fullmatch(self.base_model_ref):
            raise ValueError("base_model_ref is invalid")
        if not isinstance(self.adapter_ref, str) or not _ADAPTER_REF_RE.fullmatch(self.adapter_ref):
            raise ValueError("adapter_ref is invalid")
        if not self.adapter_ref.startswith(self.quarantine_ref + "/"):
            raise ValueError("adapter_ref crosses quarantine identity")
        for name in (
            "base_model_sha256", "adapter_sha256", "training_dataset_sha256",
            "training_recipe_sha256", "evaluation_report_sha256",
            "rights_manifest_sha256", "test_sample_set_sha256", "tuned_binding_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if (
            not isinstance(self.files, tuple) or not 1 <= len(self.files) <= _MAX_FILES
            or any(not isinstance(item, ArtifactFileEvidence) for item in self.files)
        ):
            raise ValueError("artifact files are invalid or outside bounds")
        if tuple(item.logical_path for item in self.files) != tuple(sorted(set(item.logical_path for item in self.files))):
            raise ValueError("artifact files must be sorted and path-unique")
        adapters = tuple(item for item in self.files if item.role is ArtifactFileRole.ADAPTER)
        if not adapters or artifact_role_set_sha256(self.files, ArtifactFileRole.ADAPTER) != self.adapter_sha256:
            raise ValueError("manifest requires an exact non-empty adapter role set")
        if self.total_bytes != sum(item.size_bytes for item in self.files) or self.total_bytes > _MAX_TOTAL_BYTES:
            raise ValueError("artifact total_bytes is invalid or outside bounds")
        if not isinstance(self.sealed_at, str) or not self.sealed_at.endswith("Z"):
            raise ValueError("sealed_at must be UTC")
        parsed = datetime.fromisoformat(self.sealed_at[:-1] + "+00:00")
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError("sealed_at must be UTC")
        if self.state != _STATE:
            raise ValueError("R6C cannot approve, promote or activate an artifact")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0", "record_kind": "DBD_REASONING_QUARANTINED_ARTIFACT_MANIFEST",
            "artifact_manifest_id": self.artifact_manifest_id, "quarantine_ref": self.quarantine_ref,
            "base_model_ref": self.base_model_ref, "base_model_sha256": self.base_model_sha256,
            "adapter_ref": self.adapter_ref, "adapter_sha256": self.adapter_sha256,
            "files": [item.to_dict() for item in self.files], "total_bytes": self.total_bytes,
            "training_dataset_sha256": self.training_dataset_sha256,
            "training_recipe_sha256": self.training_recipe_sha256,
            "evaluation_report_sha256": self.evaluation_report_sha256,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "test_sample_set_sha256": self.test_sample_set_sha256,
            "tuned_binding_sha256": self.tuned_binding_sha256,
            "sealed_at": self.sealed_at, "state": self.state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "artifact_manifest_sha256": sha256_bytes(canonical_json_bytes(body))}


def seal_quarantined_artifact(
    *, artifact_manifest_id: str, quarantine_ref: str,
    base_model_ref: str, base_model_sha256: str,
    adapter_ref: str, adapter_sha256: str,
    files: tuple[ArtifactFileEvidence, ...],
    training_dataset_sha256: str, training_recipe_sha256: str,
    offline_report: DbDReasoningOfflineEvaluationReport,
    sealed_at: str,
) -> QuarantinedArtifactManifest:
    report = admit_dbd_reasoning_offline_evaluation_report(offline_report.to_dict())
    tuned = report.evaluations[-1]
    if tuned.arm is not OfflineEvaluationArm.TUNED or tuned.status is not OfflineGateStatus.PASS:
        raise ValueError("R6C requires a PASS TUNED offline evaluation")
    return QuarantinedArtifactManifest(
        artifact_manifest_id=artifact_manifest_id, quarantine_ref=quarantine_ref,
        base_model_ref=base_model_ref, base_model_sha256=base_model_sha256,
        adapter_ref=adapter_ref, adapter_sha256=adapter_sha256,
        files=files, total_bytes=sum(item.size_bytes for item in files),
        training_dataset_sha256=training_dataset_sha256,
        training_recipe_sha256=training_recipe_sha256,
        evaluation_report_sha256=report.to_dict()["evaluation_report_sha256"],
        rights_manifest_sha256=report.rights_manifest_sha256,
        test_sample_set_sha256=report.test_sample_set_sha256,
        tuned_binding_sha256=tuned.binding_sha256, sealed_at=sealed_at,
    )


def admit_quarantined_artifact_manifest(record: Mapping[str, Any]) -> QuarantinedArtifactManifest:
    if not isinstance(record, Mapping):
        raise ValueError("artifact manifest must be a mapping")
    expected = set(QuarantinedArtifactManifest.__dataclass_fields__) | {
        "schema_version", "record_kind", "artifact_manifest_sha256",
    }
    if set(record) != expected or record.get("schema_version") != "1.0.0" or record.get("record_kind") != "DBD_REASONING_QUARANTINED_ARTIFACT_MANIFEST":
        raise ValueError("artifact manifest shape is invalid")
    raw_files = record.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("artifact files must be a list")
    files = tuple(ArtifactFileEvidence(
        logical_path=item["logical_path"], role=ArtifactFileRole(item["role"]),
        size_bytes=item["size_bytes"], content_sha256=item["content_sha256"],
    ) for item in raw_files if isinstance(item, dict) and set(item) == {
        "logical_path", "role", "size_bytes", "content_sha256",
    })
    if len(files) != len(raw_files):
        raise ValueError("artifact file shape is invalid")
    values = {name: record[name] for name in QuarantinedArtifactManifest.__dataclass_fields__ if name != "files"}
    manifest = QuarantinedArtifactManifest(files=files, **values)
    if manifest.to_dict() != dict(record):
        raise ValueError("artifact manifest is not canonical")
    return manifest


__all__ = [
    "ArtifactFileEvidence", "ArtifactFileRole", "QuarantinedArtifactManifest",
    "admit_quarantined_artifact_manifest", "artifact_role_set_sha256",
    "seal_quarantined_artifact",
]
