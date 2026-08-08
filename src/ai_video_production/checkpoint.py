from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id
from .serialization import utc_now_iso, validate_sha256

@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    production_job_id: str
    stage: str
    input_hash: str
    output_hash: str
    resume_state: str
    profile_snapshot_id: str
    manifest_hashes: Mapping[str, str] = field(default_factory=dict)
    checkpoint_id: str = field(default_factory=lambda: generate_id(IdKind.CHECKPOINT))
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.checkpoint_id, IdKind.CHECKPOINT)
        validate_id(self.profile_snapshot_id, IdKind.PROFILE_SNAPSHOT)
        validate_sha256(self.input_hash, field_name="checkpoint input_hash")
        validate_sha256(self.output_hash, field_name="checkpoint output_hash")
        for name, checksum in self.manifest_hashes.items():
            validate_sha256(checksum, field_name=f"checkpoint manifest_hashes[{name!r}]")
        object.__setattr__(self, "manifest_hashes", MappingProxyType(dict(self.manifest_hashes)))

    def to_dict(self) -> dict[str, object]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "production_job_id": self.production_job_id,
            "stage": self.stage,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "resume_state": self.resume_state,
            "profile_snapshot_id": self.profile_snapshot_id,
            "manifest_hashes": dict(self.manifest_hashes),
            "created_at": self.created_at,
        }

@dataclass(frozen=True, slots=True)
class ResumeContext:
    input_hash: str
    profile_snapshot_id: str
    manifest_hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        validate_id(self.profile_snapshot_id, IdKind.PROFILE_SNAPSHOT)
        validate_sha256(self.input_hash, field_name="resume input_hash")
        for name, checksum in self.manifest_hashes.items():
            validate_sha256(checksum, field_name=f"resume manifest_hashes[{name!r}]")
        object.__setattr__(self, "manifest_hashes", MappingProxyType(dict(self.manifest_hashes)))


def assert_resume_compatible(checkpoint: CheckpointRecord, current: ResumeContext) -> None:
    mismatches: dict[str, object] = {}
    if checkpoint.input_hash != current.input_hash:
        mismatches["input_hash"] = {"checkpoint": checkpoint.input_hash, "current": current.input_hash}
    if checkpoint.profile_snapshot_id != current.profile_snapshot_id:
        mismatches["profile_snapshot_id"] = {"checkpoint": checkpoint.profile_snapshot_id, "current": current.profile_snapshot_id}
    if checkpoint.manifest_hashes != current.manifest_hashes:
        mismatches["manifest_hashes"] = {"checkpoint": checkpoint.manifest_hashes, "current": current.manifest_hashes}
    if mismatches:
        raise ProductError(
            "ERR_INTEGRITY_CHECKPOINT_MISMATCH",
            "checkpoint cannot be resumed because canonical inputs changed",
            ProductErrorCategory.DATA_INTEGRITY,
            False,
            details=mismatches,
        )
