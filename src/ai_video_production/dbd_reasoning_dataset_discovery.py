"""TASK-054 R6B-A bounded, body-free Dataset Evidence discovery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import re
from typing import Mapping

from .dbd_reasoning_dataset_manifest import (
    DatasetRowDisposition,
    DatasetSplit,
    MAX_MANIFEST_CANONICAL_BYTES,
    DbDReasoningDatasetRightsManifest,
    admit_dbd_reasoning_dataset_rights_manifest,
)
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_DATASET_DISCOVERY_REPORT"
DISCOVERY_STATE = "EVIDENCE_ONLY_NO_DATASET_ADOPTION_OR_TRAINING_AUTHORITY"
MAX_DISCOVERY_MANIFESTS = 256
MAX_DISCOVERY_DIRECTORIES = 4096
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")

_DISCOVERY_POLICY = {
    "layout": "<manifest-id>/<positive-revision>/manifest.json",
    "max_manifests": MAX_DISCOVERY_MANIFESTS,
    "max_directories": MAX_DISCOVERY_DIRECTORIES,
    "max_manifest_bytes": MAX_MANIFEST_CANONICAL_BYTES,
    "symlinks": "DENIED",
    "writes": "DENIED",
}
DISCOVERY_POLICY_SHA256 = sha256_bytes(canonical_json_bytes(_DISCOVERY_POLICY))


class DatasetDiscoveryItemStatus(str, Enum):
    ADMITTED = "ADMITTED"
    INVALID = "INVALID"


class DatasetDiscoveryStatus(str, Enum):
    NO_MANIFEST_FOUND = "NO_MANIFEST_FOUND"
    DISCOVERED_CANDIDATE_ONLY = "DISCOVERED_CANDIDATE_ONLY"
    BLOCKED_INVALID_EVIDENCE = "BLOCKED_INVALID_EVIDENCE"


def _utc(value: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("observed_at must be UTC")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("observed_at must be UTC")


def _count(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class DatasetDiscoveryItem:
    logical_path_sha256: str
    observation_sha256: str
    status: DatasetDiscoveryItemStatus
    detail_code: str
    manifest_id: str | None
    revision: int | None
    rights_manifest_sha256: str | None
    entry_count: int
    eligible_candidate_count: int
    needs_review_count: int
    rejected_count: int
    train_count: int
    validation_count: int
    test_count: int

    def __post_init__(self) -> None:
        validate_sha256(self.logical_path_sha256, field_name="logical_path_sha256")
        validate_sha256(self.observation_sha256, field_name="observation_sha256")
        if not isinstance(self.status, DatasetDiscoveryItemStatus):
            raise ValueError("discovery item status is invalid")
        if not isinstance(self.detail_code, str) or not _CODE_RE.fullmatch(self.detail_code):
            raise ValueError("detail_code is invalid")
        for name in (
            "entry_count", "eligible_candidate_count", "needs_review_count",
            "rejected_count", "train_count", "validation_count", "test_count",
        ):
            _count(getattr(self, name), name)
        disposition_total = self.eligible_candidate_count + self.needs_review_count + self.rejected_count
        split_total = self.train_count + self.validation_count + self.test_count
        if self.status is DatasetDiscoveryItemStatus.ADMITTED:
            if self.manifest_id is None or self.revision is None or self.rights_manifest_sha256 is None:
                raise ValueError("admitted discovery item requires manifest identity")
            validate_id(self.manifest_id, IdKind.MANIFEST)
            if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
                raise ValueError("admitted revision is invalid")
            validate_sha256(self.rights_manifest_sha256, field_name="rights_manifest_sha256")
            if self.detail_code != "PASS":
                raise ValueError("admitted discovery item must use PASS")
            if self.entry_count < 1 or disposition_total != self.entry_count or split_total != self.entry_count:
                raise ValueError("admitted discovery counts do not match")
        else:
            if self.detail_code == "PASS":
                raise ValueError("invalid discovery item cannot use PASS")
            if self.manifest_id is not None or self.revision is not None or self.rights_manifest_sha256 is not None:
                raise ValueError("invalid discovery item must not expose parsed identity")
            if self.entry_count != 0 or disposition_total != 0 or split_total != 0:
                raise ValueError("invalid discovery item counts must be zero")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_path_sha256": self.logical_path_sha256,
            "observation_sha256": self.observation_sha256,
            "status": self.status.value,
            "detail_code": self.detail_code,
            "manifest_id": self.manifest_id,
            "revision": self.revision,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "entry_count": self.entry_count,
            "eligible_candidate_count": self.eligible_candidate_count,
            "needs_review_count": self.needs_review_count,
            "rejected_count": self.rejected_count,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
        }


@dataclass(frozen=True, slots=True)
class DatasetDiscoveryReport:
    observed_at: str
    root_observation_sha256: str
    discovery_policy_sha256: str
    status: DatasetDiscoveryStatus
    detail_code: str
    items: tuple[DatasetDiscoveryItem, ...]
    state: str = DISCOVERY_STATE

    def __post_init__(self) -> None:
        _utc(self.observed_at)
        validate_sha256(self.root_observation_sha256, field_name="root_observation_sha256")
        if self.discovery_policy_sha256 != DISCOVERY_POLICY_SHA256:
            raise ValueError("discovery policy digest is invalid")
        if not isinstance(self.status, DatasetDiscoveryStatus):
            raise ValueError("discovery status is invalid")
        if not isinstance(self.detail_code, str) or not _CODE_RE.fullmatch(self.detail_code):
            raise ValueError("discovery detail_code is invalid")
        if not isinstance(self.items, tuple) or len(self.items) > MAX_DISCOVERY_MANIFESTS:
            raise ValueError("discovery items are invalid or outside bounds")
        if any(not isinstance(item, DatasetDiscoveryItem) for item in self.items):
            raise ValueError("discovery items contain an invalid record")
        keys = tuple(item.logical_path_sha256 for item in self.items)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("discovery items must be unique and digest-sorted")
        has_invalid = any(item.status is DatasetDiscoveryItemStatus.INVALID for item in self.items)
        if self.status is DatasetDiscoveryStatus.NO_MANIFEST_FOUND:
            if self.items or self.detail_code not in {"ROOT_NOT_FOUND", "NO_MANIFEST_FOUND"}:
                raise ValueError("no-manifest report is inconsistent")
        elif self.status is DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY:
            if not self.items or has_invalid or self.detail_code != "PASS":
                raise ValueError("discovered report is inconsistent")
        elif not self.items or not has_invalid or self.detail_code != "INVALID_EVIDENCE":
            raise ValueError("blocked discovery report is inconsistent")
        if self.state != DISCOVERY_STATE:
            raise ValueError("discovery cannot grant Dataset adoption or training authority")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": RECORD_KIND,
            "observed_at": self.observed_at,
            "root_observation_sha256": self.root_observation_sha256,
            "discovery_policy_sha256": self.discovery_policy_sha256,
            "status": self.status.value,
            "detail_code": self.detail_code,
            "items": [item.to_dict() for item in self.items],
            "state": self.state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "report_sha256": sha256_bytes(canonical_json_bytes(body))}


def _path_digest(relative_path: str) -> str:
    return sha256_bytes(relative_path.encode("utf-8"))


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _invalid_item(relative_path: str, detail_code: str, observation: bytes) -> DatasetDiscoveryItem:
    return DatasetDiscoveryItem(
        logical_path_sha256=_path_digest(relative_path),
        observation_sha256=sha256_bytes(observation),
        status=DatasetDiscoveryItemStatus.INVALID,
        detail_code=detail_code,
        manifest_id=None,
        revision=None,
        rights_manifest_sha256=None,
        entry_count=0,
        eligible_candidate_count=0,
        needs_review_count=0,
        rejected_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
    )


def _admitted_item(
    relative_path: str,
    raw: bytes,
    manifest: DbDReasoningDatasetRightsManifest,
) -> DatasetDiscoveryItem:
    dispositions = {value: 0 for value in DatasetRowDisposition}
    splits = {value: 0 for value in DatasetSplit}
    for entry in manifest.entries:
        dispositions[entry.disposition] += 1
        splits[entry.split] += 1
    return DatasetDiscoveryItem(
        logical_path_sha256=_path_digest(relative_path),
        observation_sha256=sha256_bytes(raw),
        status=DatasetDiscoveryItemStatus.ADMITTED,
        detail_code="PASS",
        manifest_id=manifest.manifest_id,
        revision=manifest.revision,
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],
        entry_count=len(manifest.entries),
        eligible_candidate_count=dispositions[DatasetRowDisposition.ELIGIBLE_CANDIDATE],
        needs_review_count=dispositions[DatasetRowDisposition.NEEDS_REVIEW],
        rejected_count=dispositions[DatasetRowDisposition.REJECTED],
        train_count=splits[DatasetSplit.TRAIN],
        validation_count=splits[DatasetSplit.VALIDATION],
        test_count=splits[DatasetSplit.TEST],
    )


def discover_task054_dataset_evidence(
    root: Path,
    *,
    observed_at: str,
) -> DatasetDiscoveryReport:
    if not isinstance(root, Path):
        raise ValueError("root must be pathlib.Path")
    _utc(observed_at)
    root_observation_sha256 = sha256_bytes(os.fsencode(str(root.absolute())))
    if not root.exists():
        return DatasetDiscoveryReport(
            observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
            DatasetDiscoveryStatus.NO_MANIFEST_FOUND, "ROOT_NOT_FOUND", (),
        )
    if _is_linklike(root) or not root.is_dir():
        item = _invalid_item(".", "UNSAFE_DATASET_ROOT", b"UNSAFE_DATASET_ROOT")
        return DatasetDiscoveryReport(
            observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
            DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE, "INVALID_EVIDENCE", (item,),
        )

    candidates: list[tuple[str, Path]] = []
    findings: list[DatasetDiscoveryItem] = []
    walk_error_seen = False

    def onerror(error: OSError) -> None:
        nonlocal walk_error_seen
        walk_error_seen = True

    visited_directories = 0
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        visited_directories += 1
        if visited_directories > MAX_DISCOVERY_DIRECTORIES:
            item = _invalid_item(".", "DIRECTORY_SCAN_LIMIT", b"DIRECTORY_SCAN_LIMIT")
            return DatasetDiscoveryReport(
                observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
                DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE, "INVALID_EVIDENCE", (item,),
            )
        current_path = Path(current)
        safe_directories: list[str] = []
        for name in sorted(directory_names):
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if _is_linklike(child):
                findings.append(_invalid_item(relative, "SYMLINK_DENIED", b"SYMLINK_DENIED" + relative.encode("utf-8")))
            else:
                safe_directories.append(name)
        directory_names[:] = safe_directories
        if "manifest.json" in file_names:
            path = current_path / "manifest.json"
            relative = path.relative_to(root).as_posix()
            candidates.append((relative, path))
        if len(candidates) + len(findings) > MAX_DISCOVERY_MANIFESTS:
            item = _invalid_item(".", "DISCOVERY_LIMIT", b"DISCOVERY_LIMIT")
            return DatasetDiscoveryReport(
                observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
                DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE, "INVALID_EVIDENCE", (item,),
            )

    if walk_error_seen and len(candidates) + len(findings) >= MAX_DISCOVERY_MANIFESTS:
        item = _invalid_item(".", "DISCOVERY_LIMIT", b"DISCOVERY_LIMIT")
        return DatasetDiscoveryReport(
            observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
            DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE, "INVALID_EVIDENCE", (item,),
        )
    if walk_error_seen:
        findings.append(_invalid_item(".", "ROOT_READ_ERROR", b"ROOT_READ_ERROR"))

    for relative, path in sorted(candidates):
        parts = Path(relative).parts
        if (
            len(parts) != 3
            or parts[-1] != "manifest.json"
            or not parts[1].isdigit()
            or int(parts[1]) < 1
            or str(int(parts[1])) != parts[1]
        ):
            findings.append(_invalid_item(relative, "UNEXPECTED_MANIFEST_LAYOUT", relative.encode("utf-8")))
            continue
        if _is_linklike(path):
            findings.append(_invalid_item(relative, "SYMLINK_DENIED", b"SYMLINK_DENIED" + relative.encode("utf-8")))
            continue
        try:
            size = path.stat().st_size
            if size > MAX_MANIFEST_CANONICAL_BYTES:
                findings.append(_invalid_item(relative, "MANIFEST_SIZE_LIMIT", str(size).encode("ascii")))
                continue
            with path.open("rb") as stream:
                raw = stream.read(MAX_MANIFEST_CANONICAL_BYTES + 1)
            if len(raw) > MAX_MANIFEST_CANONICAL_BYTES:
                findings.append(_invalid_item(relative, "MANIFEST_SIZE_LIMIT", str(len(raw)).encode("ascii")))
                continue
        except OSError:
            findings.append(_invalid_item(relative, "MANIFEST_READ_ERROR", b"MANIFEST_READ_ERROR"))
            continue
        try:
            record = json.loads(raw.decode("utf-8"))
            manifest = admit_dbd_reasoning_dataset_rights_manifest(record)
            if parts[0] != manifest.manifest_id or int(parts[1]) != manifest.revision:
                raise ValueError("manifest identity does not match logical path")
            findings.append(_admitted_item(relative, raw, manifest))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            findings.append(_invalid_item(relative, "MANIFEST_ADMISSION_FAILED", raw))

    if not findings:
        return DatasetDiscoveryReport(
            observed_at, root_observation_sha256, DISCOVERY_POLICY_SHA256,
            DatasetDiscoveryStatus.NO_MANIFEST_FOUND, "NO_MANIFEST_FOUND", (),
        )

    identity_counts: dict[tuple[str, int], int] = {}
    for item in findings:
        if item.status is DatasetDiscoveryItemStatus.ADMITTED:
            key = (item.manifest_id, item.revision)
            identity_counts[key] = identity_counts.get(key, 0) + 1
    duplicates = {key for key, count in identity_counts.items() if count > 1}
    normalized: list[DatasetDiscoveryItem] = []
    for item in findings:
        if item.status is DatasetDiscoveryItemStatus.ADMITTED and (item.manifest_id, item.revision) in duplicates:
            normalized.append(replace(
                item,
                status=DatasetDiscoveryItemStatus.INVALID,
                detail_code="DUPLICATE_MANIFEST_IDENTITY",
                manifest_id=None,
                revision=None,
                rights_manifest_sha256=None,
                entry_count=0,
                eligible_candidate_count=0,
                needs_review_count=0,
                rejected_count=0,
                train_count=0,
                validation_count=0,
                test_count=0,
            ))
        else:
            normalized.append(item)
    items = tuple(sorted(normalized, key=lambda item: item.logical_path_sha256))
    has_invalid = any(item.status is DatasetDiscoveryItemStatus.INVALID for item in items)
    return DatasetDiscoveryReport(
        observed_at,
        root_observation_sha256,
        DISCOVERY_POLICY_SHA256,
        DatasetDiscoveryStatus.BLOCKED_INVALID_EVIDENCE if has_invalid else DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY,
        "INVALID_EVIDENCE" if has_invalid else "PASS",
        items,
    )


def admit_dataset_discovery_report(record: Mapping[str, object]) -> DatasetDiscoveryReport:
    if not isinstance(record, Mapping):
        raise ValueError("discovery report must be a mapping")
    expected = {
        "schema_version", "record_kind", "observed_at", "root_observation_sha256",
        "discovery_policy_sha256", "status", "detail_code", "items", "state", "report_sha256",
    }
    if set(record) != expected or record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != RECORD_KIND:
        raise ValueError("discovery report shape is invalid")
    raw_items = record.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("discovery items must be a list")
    item_keys = set(DatasetDiscoveryItem.__dataclass_fields__)
    items: list[DatasetDiscoveryItem] = []
    for raw in raw_items:
        if not isinstance(raw, Mapping) or set(raw) != item_keys:
            raise ValueError("discovery item shape is invalid")
        values = dict(raw)
        values["status"] = DatasetDiscoveryItemStatus(values["status"])
        items.append(DatasetDiscoveryItem(**values))
    report = DatasetDiscoveryReport(
        observed_at=record["observed_at"],
        root_observation_sha256=record["root_observation_sha256"],
        discovery_policy_sha256=record["discovery_policy_sha256"],
        status=DatasetDiscoveryStatus(record["status"]),
        detail_code=record["detail_code"],
        items=tuple(items),
        state=record["state"],
    )
    if report.to_dict() != dict(record):
        raise ValueError("discovery report is not canonical")
    return report


__all__ = [
    "DISCOVERY_POLICY_SHA256", "DISCOVERY_STATE", "DatasetDiscoveryItem",
    "DatasetDiscoveryItemStatus", "DatasetDiscoveryReport", "DatasetDiscoveryStatus",
    "MAX_DISCOVERY_DIRECTORIES", "MAX_DISCOVERY_MANIFESTS", "admit_dataset_discovery_report",
    "discover_task054_dataset_evidence",
]
