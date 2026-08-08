from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .assets import AssetType
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .store import SQLiteProductStore
from .paths import LogicalPathResolver
from .derived_assets import sha256_file
from pathlib import Path

_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,2}$")


def _clean_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value or "\x00" in value:
        raise ValueError(f"{field_name} must be non-empty and contain no NUL")
    return value


@dataclass(frozen=True, slots=True)
class CharacterIdentityProfile:
    identity_key: str
    version: str
    display_name: str
    visual_prompt: str
    negative_prompt: str = ""
    style_prompt: str = ""
    voice_prompt: str = ""
    aliases: tuple[str, ...] = ()
    immutable_traits: dict[str, str] = field(default_factory=dict)
    allowed_variations: tuple[str, ...] = ()
    forbidden_drift: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _KEY_RE.fullmatch(self.identity_key):
            raise ValueError("identity_key must be a stable lowercase slug")
        if not _VERSION_RE.fullmatch(self.version):
            raise ValueError("version must be numeric dotted version")
        object.__setattr__(self, "display_name", _clean_text(self.display_name, "display_name"))
        object.__setattr__(self, "visual_prompt", _clean_text(self.visual_prompt, "visual_prompt"))
        object.__setattr__(self, "negative_prompt", self.negative_prompt.strip())
        object.__setattr__(self, "style_prompt", self.style_prompt.strip())
        object.__setattr__(self, "voice_prompt", self.voice_prompt.strip())
        for name in (*self.aliases, *self.allowed_variations, *self.forbidden_drift):
            _clean_text(name, "character list item")
        for key, value in self.immutable_traits.items():
            _clean_text(str(key), "immutable trait key")
            _clean_text(str(value), "immutable trait value")

    def identity_prompt(self) -> str:
        parts = [self.visual_prompt]
        if self.immutable_traits:
            traits = ", ".join(f"{k}: {self.immutable_traits[k]}" for k in sorted(self.immutable_traits))
            parts.append("Identity locks: " + traits)
        if self.forbidden_drift:
            parts.append("Do not change: " + ", ".join(self.forbidden_drift))
        if self.style_prompt:
            parts.append("Style: " + self.style_prompt)
        return ". ".join(parts)

    def character_sheet_prompt(self) -> str:
        return (
            self.identity_prompt()
            + ". Create one 16:9 character reference sheet. Left region: consistent face and upper-body anchor. "
              "Upper-right: coordinated full-body front, side, and back turnaround with the same face and body proportions. "
              "Lower-right: close-up studies of signature clothing, accessories, materials, and identity details. "
              "Keep facial identity, hair, proportions, costume palette, and signature details consistent across every view."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_key": self.identity_key,
            "version": self.version,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "visual_prompt": self.visual_prompt,
            "negative_prompt": self.negative_prompt,
            "style_prompt": self.style_prompt,
            "voice_prompt": self.voice_prompt,
            "immutable_traits": dict(self.immutable_traits),
            "allowed_variations": list(self.allowed_variations),
            "forbidden_drift": list(self.forbidden_drift),
        }


@dataclass(frozen=True, slots=True)
class CharacterReferenceBundle:
    production_job_id: str
    identity_key: str
    identity_version: str
    face_anchor_asset_id: str
    front_asset_id: str | None = None
    side_asset_id: str | None = None
    back_asset_id: str | None = None
    detail_asset_ids: tuple[str, ...] = ()
    locked_for_production: bool = False
    approval_ref: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        if not _KEY_RE.fullmatch(self.identity_key):
            raise ValueError("identity_key must be a stable lowercase slug")
        if not _VERSION_RE.fullmatch(self.identity_version):
            raise ValueError("identity_version is invalid")
        ids = [self.face_anchor_asset_id, self.front_asset_id, self.side_asset_id, self.back_asset_id, *self.detail_asset_ids]
        for asset_id in ids:
            if asset_id is not None:
                validate_id(asset_id, IdKind.ASSET)
        non_null = [x for x in ids if x is not None]
        if len(non_null) != len(set(non_null)):
            raise ValueError("reference bundle cannot contain duplicate asset IDs")
        if self.locked_for_production and not self.approval_ref:
            raise ValueError("locked production bundle requires approval_ref")

    def asset_ids(self) -> tuple[str, ...]:
        return tuple(x for x in (
            self.face_anchor_asset_id,
            self.front_asset_id,
            self.side_asset_id,
            self.back_asset_id,
            *self.detail_asset_ids,
        ) if x is not None)


class CharacterIdentityService:
    def __init__(self, store: SQLiteProductStore, resolver: LogicalPathResolver) -> None:
        self.store = store
        self.resolver = resolver

    def validate_bundle(self, profile: CharacterIdentityProfile, bundle: CharacterReferenceBundle) -> tuple[dict[str, str], ...]:
        if profile.identity_key != bundle.identity_key or profile.version != bundle.identity_version:
            raise ProductError(
                "ERR_INTEGRITY_CHARACTER_PROFILE_BINDING_MISMATCH",
                "character reference bundle does not match the identity profile version",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        refs: list[dict[str, str]] = []
        for asset_id in bundle.asset_ids():
            asset = self.store.get_asset(asset_id)
            if asset.production_job_id != bundle.production_job_id:
                raise ProductError(
                    "ERR_SECURITY_CROSS_JOB_REFERENCE_DENIED",
                    "character reference belongs to a different Job",
                    ProductErrorCategory.SECURITY,
                )
            if asset.asset_type is not AssetType.IMAGE:
                raise ProductError(
                    "ERR_INPUT_CHARACTER_REFERENCE_TYPE",
                    "character reference assets must be IMAGE",
                    ProductErrorCategory.VALIDATION,
                )
            if not asset.derivative_use_allowed:
                raise ProductError(
                    "ERR_POLICY_CHARACTER_REFERENCE_RIGHTS",
                    "character reference is not authorized for derivative generation",
                    ProductErrorCategory.AUTHORIZATION,
                )
            path = self.resolver.resolve(asset.logical_uri)
            if not isinstance(path, Path) or not path.exists() or path.is_symlink() or not path.is_file():
                raise ProductError(
                    "ERR_INTEGRITY_CHARACTER_REFERENCE_MISSING",
                    "character reference canonical bytes are missing, symlinked, or invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"asset_id": asset.asset_id},
                )
            if sha256_file(path) != asset.checksum:
                raise ProductError(
                    "ERR_INTEGRITY_CHARACTER_REFERENCE_CHECKSUM",
                    "character reference canonical checksum no longer matches the Registry",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"asset_id": asset.asset_id},
                )
            refs.append({"asset_id": asset.asset_id, "checksum": asset.checksum, "logical_uri": asset.logical_uri})
        return tuple(refs)
