"""TASK-043 versioned Product Project contract.

The manifest aggregates child-store identities, versions and checksums. It never
duplicates domain payloads and grants no Provider, native or external authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import PurePosixPath, PureWindowsPath
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .errors import ProductError, ProductErrorCategory
from .ids import validate_project_id
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256


PROJECT_FORMAT_ID = "bai-video-production.project"
PROJECT_FORMAT_VERSION = "1.0.0"
_FORMAT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9][a-z0-9-]*)+$")
_DOMAIN_OWNER_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:[-./][A-Z0-9]+)*$")
_MAX_BINDINGS = 256


def _parse_timestamp(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be a UTC ISO-8601 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")
    return parsed


def validate_project_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError("relative_path must contain 1-512 characters")
    if "\\" in value or "\x00" in value:
        raise ValueError("relative_path must use canonical forward slashes")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise ValueError("relative_path must not be absolute or drive-qualified")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError("relative_path must not contain empty, dot or parent segments")
    if posix.parts[0].casefold() == ".bai-project":
        raise ValueError("relative_path must not bind the reserved Project control directory")
    canonical = posix.as_posix()
    if canonical != value:
        raise ValueError("relative_path must already be canonical")
    return value


def sha256_file_exact(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectTimebase:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int) or self.numerator <= 0:
            raise ValueError("timebase numerator must be a positive integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int) or self.denominator <= 0:
            raise ValueError("timebase denominator must be a positive integer")

    def to_dict(self) -> dict[str, int]:
        return {"numerator": self.numerator, "denominator": self.denominator}


@dataclass(frozen=True, slots=True)
class ProjectChildBinding:
    domain_owner: str
    relative_path: str
    format_id: str
    format_version: str
    content_sha256: str
    required: bool
    dependency_hashes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.domain_owner, str) or not _DOMAIN_OWNER_RE.fullmatch(self.domain_owner):
            raise ValueError("domain_owner must be a stable uppercase Task/domain identity")
        validate_project_relative_path(self.relative_path)
        if not isinstance(self.format_id, str) or not _FORMAT_ID_RE.fullmatch(self.format_id):
            raise ValueError("format_id must be a stable dotted/hyphenated lowercase identity")
        SemVer.parse(self.format_version)
        validate_sha256(self.content_sha256, field_name="content_sha256")
        if not isinstance(self.required, bool):
            raise ValueError("required must be boolean")
        if len(self.dependency_hashes) > 128:
            raise ValueError("dependency_hashes exceeds the bounded maximum")
        if tuple(sorted(set(self.dependency_hashes))) != self.dependency_hashes:
            raise ValueError("dependency_hashes must be unique and sorted")
        for value in self.dependency_hashes:
            validate_sha256(value, field_name="dependency_hash")

    @property
    def identity(self) -> tuple[str, str]:
        return self.domain_owner, self.relative_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_owner": self.domain_owner,
            "relative_path": self.relative_path,
            "format_id": self.format_id,
            "format_version": self.format_version,
            "content_sha256": self.content_sha256,
            "required": self.required,
            "dependency_hashes": list(self.dependency_hashes),
        }


@dataclass(frozen=True, slots=True)
class ProductProjectManifest:
    project_id: str
    project_revision: int
    created_at: str
    updated_at: str
    product_version: str
    timebase: ProjectTimebase
    child_bindings: tuple[ProjectChildBinding, ...]
    project_manifest_sha256: str
    project_format_version: str = PROJECT_FORMAT_VERSION
    project_format_id: str = PROJECT_FORMAT_ID

    def __post_init__(self) -> None:
        validate_project_id(self.project_id)
        if isinstance(self.project_revision, bool) or not isinstance(self.project_revision, int) or self.project_revision < 1:
            raise ValueError("project_revision must be a positive integer")
        created = _parse_timestamp(self.created_at, "created_at")
        updated = _parse_timestamp(self.updated_at, "updated_at")
        if updated < created:
            raise ValueError("updated_at must not precede created_at")
        SemVer.parse(self.product_version)
        if self.project_format_id != PROJECT_FORMAT_ID:
            raise ValueError("unsupported project_format_id")
        if self.project_format_version != PROJECT_FORMAT_VERSION:
            raise ValueError("unsupported project_format_version")
        if len(self.child_bindings) > _MAX_BINDINGS:
            raise ValueError("child_bindings exceeds the bounded maximum")
        identities = [item.identity for item in self.child_bindings]
        paths = [item.relative_path.casefold() for item in self.child_bindings]
        if len(identities) != len(set(identities)) or len(paths) != len(set(paths)):
            raise ValueError("child bindings contain duplicate identity or case-colliding path")
        if tuple(sorted(self.child_bindings, key=lambda item: item.identity)) != self.child_bindings:
            raise ValueError("child_bindings must be sorted by domain_owner and relative_path")
        validate_sha256(self.project_manifest_sha256, field_name="project_manifest_sha256")
        if sha256_bytes(canonical_json_bytes(self._body())) != self.project_manifest_sha256:
            raise ValueError("project_manifest_sha256 does not match the manifest body")

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        project_revision: int,
        product_version: str,
        timebase: ProjectTimebase,
        child_bindings: Iterable[ProjectChildBinding],
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> "ProductProjectManifest":
        now = utc_now_iso()
        created = created_at or now
        updated = updated_at or now
        bindings = tuple(sorted(child_bindings, key=lambda item: item.identity))
        body = _manifest_body(
            project_id=project_id,
            project_revision=project_revision,
            created_at=created,
            updated_at=updated,
            product_version=product_version,
            timebase=timebase,
            child_bindings=bindings,
        )
        return cls(
            project_id=project_id,
            project_revision=project_revision,
            created_at=created,
            updated_at=updated,
            product_version=product_version,
            timebase=timebase,
            child_bindings=bindings,
            project_manifest_sha256=sha256_bytes(canonical_json_bytes(body)),
        )

    def _body(self) -> dict[str, Any]:
        return _manifest_body(
            project_id=self.project_id,
            project_revision=self.project_revision,
            created_at=self.created_at,
            updated_at=self.updated_at,
            product_version=self.product_version,
            timebase=self.timebase,
            child_bindings=self.child_bindings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "project_manifest_sha256": self.project_manifest_sha256}


def _manifest_body(
    *,
    project_id: str,
    project_revision: int,
    created_at: str,
    updated_at: str,
    product_version: str,
    timebase: ProjectTimebase,
    child_bindings: tuple[ProjectChildBinding, ...],
) -> dict[str, Any]:
    return {
        "project_format_id": PROJECT_FORMAT_ID,
        "project_format_version": PROJECT_FORMAT_VERSION,
        "project_id": project_id,
        "project_revision": project_revision,
        "created_at": created_at,
        "updated_at": updated_at,
        "product_version": product_version,
        "timebase": timebase.to_dict(),
        "child_bindings": [item.to_dict() for item in child_bindings],
        "authority": {
            "provider_execution_authorized": False,
            "paid_execution_authorized": False,
            "native_execution_authorized": False,
            "external_mutation_authorized": False,
        },
        "secrets_embedded": False,
        "media_bytes_embedded": False,
    }


def parse_product_project_manifest(document: Mapping[str, Any]) -> ProductProjectManifest:
    if not isinstance(document, Mapping):
        raise ProductError("ERR_PROJECT_FORMAT_INVALID", "Project manifest root must be an object", ProductErrorCategory.DATA_INTEGRITY)
    expected_fields = {
        "project_format_id", "project_format_version", "project_id", "project_revision",
        "created_at", "updated_at", "product_version", "timebase", "child_bindings",
        "authority", "secrets_embedded", "media_bytes_embedded", "project_manifest_sha256",
    }
    if set(document) != expected_fields:
        raise ProductError("ERR_PROJECT_FORMAT_FIELDS", "Project manifest fields are not exact", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("project_format_id") != PROJECT_FORMAT_ID:
        raise ProductError("ERR_PROJECT_FORMAT_ID_UNSUPPORTED", "Project format identity is unsupported", ProductErrorCategory.NOT_SUPPORTED)
    try:
        document_version = SemVer.parse(document.get("project_format_version"))
        supported_version = SemVer.parse(PROJECT_FORMAT_VERSION)
    except (TypeError, ValueError) as exc:
        raise ProductError("ERR_PROJECT_FORMAT_VERSION_INVALID", "Project format version is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc
    if document_version > supported_version:
        raise ProductError("ERR_PROJECT_FORMAT_NEWER_UNSUPPORTED", "Project was created by a newer unsupported format", ProductErrorCategory.NOT_SUPPORTED)
    if document_version < supported_version:
        raise ProductError("ERR_PROJECT_FORMAT_MIGRATION_REQUIRED", "Project format requires an explicit migration plan", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)
    authority = document.get("authority")
    if authority != {
        "provider_execution_authorized": False,
        "paid_execution_authorized": False,
        "native_execution_authorized": False,
        "external_mutation_authorized": False,
    } or document.get("secrets_embedded") is not False or document.get("media_bytes_embedded") is not False:
        raise ProductError("ERR_PROJECT_FORMAT_AUTHORITY", "Project manifest violates authority or storage boundaries", ProductErrorCategory.SECURITY)
    try:
        timebase_raw = document["timebase"]
        if not isinstance(timebase_raw, Mapping) or set(timebase_raw) != {"numerator", "denominator"}:
            raise ValueError("timebase fields are invalid")
        binding_rows = document["child_bindings"]
        if not isinstance(binding_rows, list):
            raise ValueError("child_bindings must be an array")
        bindings = []
        for row in binding_rows:
            if not isinstance(row, Mapping) or set(row) != {
                "domain_owner", "relative_path", "format_id", "format_version",
                "content_sha256", "required", "dependency_hashes",
            }:
                raise ValueError("child binding fields are invalid")
            hashes = row["dependency_hashes"]
            if not isinstance(hashes, list) or not all(isinstance(value, str) for value in hashes):
                raise ValueError("dependency_hashes must be a string array")
            bindings.append(ProjectChildBinding(
                domain_owner=row["domain_owner"], relative_path=row["relative_path"],
                format_id=row["format_id"], format_version=row["format_version"],
                content_sha256=row["content_sha256"], required=row["required"],
                dependency_hashes=tuple(hashes),
            ))
        return ProductProjectManifest(
            project_id=document["project_id"], project_revision=document["project_revision"],
            created_at=document["created_at"], updated_at=document["updated_at"],
            product_version=document["product_version"],
            timebase=ProjectTimebase(timebase_raw["numerator"], timebase_raw["denominator"]),
            child_bindings=tuple(bindings), project_manifest_sha256=document["project_manifest_sha256"],
            project_format_id=document["project_format_id"],
            project_format_version=document["project_format_version"],
        )
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PROJECT_FORMAT_INVALID", "Project manifest contains invalid values", ProductErrorCategory.DATA_INTEGRITY) from exc
