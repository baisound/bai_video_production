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


class PermissionState(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class AudioRightsStatus(str, Enum):
    SAFE = "SAFE"
    REPLACE = "REPLACE"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class ApprovedSegment:
    in_us: int
    out_us: int

    def __post_init__(self) -> None:
        if self.in_us < 0 or self.out_us <= self.in_us:
            raise ValueError("approved segment must satisfy 0 <= in_us < out_us")

    def to_dict(self) -> dict[str, int]:
        return {"in_us": self.in_us, "out_us": self.out_us}


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
    original_name: str | None = None
    commercial_use: PermissionState = PermissionState.UNKNOWN
    derivative_allowed: PermissionState = PermissionState.UNKNOWN
    reuse_allowed: PermissionState = PermissionState.ALLOWED
    audio_rights_status: AudioRightsStatus = AudioRightsStatus.NOT_APPLICABLE
    source_ref: str | None = None
    source_project: str | None = None
    attribution: str | None = None
    territory: tuple[str, ...] = ()
    rights_valid_until: str | None = None
    publication_restrictions: tuple[str, ...] = ()
    approved_segments: tuple[ApprovedSegment, ...] = ()
    media_metadata: dict[str, Any] = field(default_factory=dict)
    perceptual_hash: str | None = None
    audio_fingerprint: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.asset_id, IdKind.ASSET)
        if not self.owner.strip():
            raise ValueError("asset owner must be non-empty")
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
        if self.original_name is not None:
            if not self.original_name or any(x in self.original_name for x in ("/", "\\", "\x00")):
                raise ValueError("original_name must be a basename, not a path")
        for ref in self.evidence_refs:
            if ref.startswith("EVD-"):
                validate_id(ref, IdKind.EVIDENCE)
        for value, field_name in (
            (self.source_ref, "source_ref"),
            (self.source_project, "source_project"),
            (self.attribution, "attribution"),
            (self.rights_valid_until, "rights_valid_until"),
            (self.perceptual_hash, "perceptual_hash"),
            (self.audio_fingerprint, "audio_fingerprint"),
        ):
            if value is not None and "\x00" in value:
                raise ValueError(f"{field_name} contains NUL")
        if any(not item.strip() for item in self.territory):
            raise ValueError("territory values must be non-empty")
        if any(not item.strip() for item in self.publication_restrictions):
            raise ValueError("publication restrictions must be non-empty")

    @property
    def auto_use_allowed(self) -> bool:
        """Whether the asset can be reused automatically for ordinary editing.

        Commercial publication and derivative-work permission remain separate
        gates. Audio REVIEW/REPLACE states also require an explicit downstream
        treatment instead of silently reusing the complete source audio.
        """
        return (
            self.rights_status in {
                RightsStatus.OWNED,
                RightsStatus.LICENSED,
                RightsStatus.PERMISSION_GRANTED,
            }
            and not self.human_lock
            and self.reuse_allowed is not PermissionState.DENIED
            and self.audio_rights_status not in {AudioRightsStatus.REVIEW, AudioRightsStatus.REPLACE}
        )

    @property
    def commercial_use_allowed(self) -> bool:
        return self.auto_use_allowed and self.commercial_use is PermissionState.ALLOWED

    @property
    def derivative_use_allowed(self) -> bool:
        return self.auto_use_allowed and self.derivative_allowed is PermissionState.ALLOWED

    @property
    def rights_review_required(self) -> bool:
        return (
            self.rights_status in {RightsStatus.UNKNOWN, RightsStatus.PLATFORM_RESTRICTED}
            or self.commercial_use is PermissionState.UNKNOWN
            or self.derivative_allowed is PermissionState.UNKNOWN
            or self.reuse_allowed is PermissionState.UNKNOWN
            or self.audio_rights_status is AudioRightsStatus.REVIEW
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
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
            "commercial_use": self.commercial_use.value,
            "derivative_allowed": self.derivative_allowed.value,
            "reuse_allowed": self.reuse_allowed.value,
            "audio_rights_status": self.audio_rights_status.value,
            "territory": list(self.territory),
            "publication_restrictions": list(self.publication_restrictions),
            "approved_segments": [segment.to_dict() for segment in self.approved_segments],
            "media_metadata": self.media_metadata,
        }
        optional = {
            "original_name": self.original_name,
            "source_ref": self.source_ref,
            "source_project": self.source_project,
            "attribution": self.attribution,
            "rights_valid_until": self.rights_valid_until,
            "perceptual_hash": self.perceptual_hash,
            "audio_fingerprint": self.audio_fingerprint,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AssetRecord":
        return cls(
            production_job_id=value["production_job_id"],
            asset_type=AssetType(value["asset_type"]),
            logical_uri=value["logical_uri"],
            checksum=value["checksum"],
            rights_status=RightsStatus(value["rights_status"]),
            owner=value["owner"],
            asset_id=value["asset_id"],
            retention_class=RetentionClass(value.get("retention_class", RetentionClass.STANDARD.value)),
            human_lock=bool(value.get("human_lock", False)),
            generation_provenance=dict(value.get("generation_provenance", {})),
            evidence_refs=tuple(value.get("evidence_refs", ())),
            original_name=value.get("original_name"),
            commercial_use=PermissionState(value.get("commercial_use", PermissionState.UNKNOWN.value)),
            derivative_allowed=PermissionState(value.get("derivative_allowed", PermissionState.UNKNOWN.value)),
            reuse_allowed=PermissionState(value.get("reuse_allowed", PermissionState.ALLOWED.value)),
            audio_rights_status=AudioRightsStatus(value.get("audio_rights_status", AudioRightsStatus.NOT_APPLICABLE.value)),
            source_ref=value.get("source_ref"),
            source_project=value.get("source_project"),
            attribution=value.get("attribution"),
            territory=tuple(value.get("territory", ())),
            rights_valid_until=value.get("rights_valid_until"),
            publication_restrictions=tuple(value.get("publication_restrictions", ())),
            approved_segments=tuple(ApprovedSegment(int(x["in_us"]), int(x["out_us"])) for x in value.get("approved_segments", ())),
            media_metadata=dict(value.get("media_metadata", {})),
            perceptual_hash=value.get("perceptual_hash"),
            audio_fingerprint=value.get("audio_fingerprint"),
        )
