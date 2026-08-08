from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .ids import IdKind, generate_id, validate_id
from .serialization import validate_sha256

class AssetType(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    SUBTITLE = "SUBTITLE"
    BGM = "BGM"
    SFX = "SFX"
    GENERATED_VIDEO = "GENERATED_VIDEO"
    VOICE_MODEL = "VOICE_MODEL"
    OTHER = "OTHER"

class RightsStatus(str, Enum):
    OWNED = "OWNED"
    LICENSED = "LICENSED"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PLATFORM_RESTRICTED = "PLATFORM_RESTRICTED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"

class RetentionClass(str, Enum):
    STANDARD = "STANDARD"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    LEGAL_HOLD = "LEGAL_HOLD"

@dataclass(frozen=True, slots=True)
class AssetRecord:
    production_job_id: str
    asset_type: AssetType
    logical_uri: str
    checksum: str
    rights_status: RightsStatus
    owner: str
    asset_id: str = field(default_factory=lambda: generate_id(IdKind.ASSET))
    retention_class: RetentionClass = RetentionClass.STANDARD
    human_lock: bool = False
    generation_provenance: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.asset_id, IdKind.ASSET)
        prefix = "asset://" if self.logical_uri.startswith("asset://") else "job://" if self.logical_uri.startswith("job://") else None
        if prefix is None:
            raise ValueError("asset logical_uri must use asset:// or job://")
        relative = self.logical_uri[len(prefix):]
        if "\x00" in relative or "\\" in relative:
            raise ValueError("asset logical_uri contains forbidden path syntax")
        parts = relative.split("/")
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("asset logical_uri contains invalid path segments")
        validate_id(parts[0], IdKind.JOB)
        if parts[0] != self.production_job_id:
            raise ValueError("asset logical_uri must be scoped to production_job_id")
        validate_sha256(self.checksum, field_name="asset checksum")

    @property
    def auto_use_allowed(self) -> bool:
        return self.rights_status in {
            RightsStatus.OWNED,
            RightsStatus.LICENSED,
            RightsStatus.PERMISSION_GRANTED,
        } and not self.human_lock

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "production_job_id": self.production_job_id,
            "asset_type": self.asset_type.value,
            "logical_uri": self.logical_uri,
            "checksum": self.checksum,
            "rights_status": self.rights_status.value,
            "owner": self.owner,
            "retention_class": self.retention_class.value,
            "human_lock": self.human_lock,
            "generation_provenance": self.generation_provenance,
            "evidence_refs": list(self.evidence_refs),
        }
