"""TASK-054 R6B-B body-free Dataset Evidence selection preflight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Mapping

from .dbd_reasoning_dataset_discovery import (
    DatasetDiscoveryItem,
    DatasetDiscoveryItemStatus,
    DatasetDiscoveryStatus,
    admit_dataset_discovery_report,
)
from .dbd_reasoning_dataset_manifest import MAX_MANIFEST_ENTRIES
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_DATASET_EVIDENCE_PREFLIGHT"
PREFLIGHT_STATE = "PREFLIGHT_ONLY_NO_DATASET_ADOPTION_OR_TRAINING_AUTHORITY"
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class DatasetEvidencePreflightMode(str, Enum):
    CONFIRMATION_ONLY = "CONFIRMATION_ONLY"
    LEARNING_PREPARATION = "LEARNING_PREPARATION"


class DatasetEvidencePreflightStatus(str, Enum):
    BLOCKED_DISCOVERY = "BLOCKED_DISCOVERY"
    SELECTION_REQUIRED = "SELECTION_REQUIRED"
    EVIDENCE_REVIEW_READY = "EVIDENCE_REVIEW_READY"
    BLOCKED_NO_ELIGIBLE_CANDIDATE = "BLOCKED_NO_ELIGIBLE_CANDIDATE"
    DATASET_ADOPTION_REVIEW_REQUIRED = "DATASET_ADOPTION_REVIEW_REQUIRED"


def _utc(value: str, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be UTC")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")
    return parsed


def _count(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_MANIFEST_ENTRIES:
        raise ValueError(f"{name} is outside the manifest ceiling")


@dataclass(frozen=True, slots=True)
class DatasetEvidencePreflight:
    created_at: str
    discovery_observed_at: str
    discovery_report_sha256: str
    mode: DatasetEvidencePreflightMode
    status: DatasetEvidencePreflightStatus
    detail_code: str
    selected_logical_path_sha256: str | None
    selected_observation_sha256: str | None
    selected_manifest_id: str | None
    selected_revision: int | None
    selected_rights_manifest_sha256: str | None
    entry_count: int
    eligible_candidate_count: int
    needs_review_count: int
    rejected_count: int
    train_count: int
    validation_count: int
    test_count: int
    requires_dataset_adoption_gate: bool
    dataset_adoption_authorized: bool = False
    training_authorized: bool = False
    state: str = PREFLIGHT_STATE

    def __post_init__(self) -> None:
        created_at = _utc(self.created_at, field_name="created_at")
        discovery_observed_at = _utc(
            self.discovery_observed_at, field_name="discovery_observed_at"
        )
        if created_at < discovery_observed_at:
            raise ValueError("created_at cannot be before discovery_observed_at")
        validate_sha256(self.discovery_report_sha256, field_name="discovery_report_sha256")
        if not isinstance(self.mode, DatasetEvidencePreflightMode):
            raise ValueError("preflight mode is invalid")
        if not isinstance(self.status, DatasetEvidencePreflightStatus):
            raise ValueError("preflight status is invalid")
        if not isinstance(self.detail_code, str) or not _CODE_RE.fullmatch(self.detail_code):
            raise ValueError("detail_code is invalid")
        for name in (
            "entry_count",
            "eligible_candidate_count",
            "needs_review_count",
            "rejected_count",
            "train_count",
            "validation_count",
            "test_count",
        ):
            _count(getattr(self, name), name)
        if not isinstance(self.requires_dataset_adoption_gate, bool):
            raise ValueError("requires_dataset_adoption_gate must be boolean")
        if self.dataset_adoption_authorized is not False or self.training_authorized is not False:
            raise ValueError("preflight cannot grant Dataset adoption or training authority")
        if self.state != PREFLIGHT_STATE:
            raise ValueError("preflight state cannot grant Dataset adoption or training authority")

        selection = (
            self.selected_logical_path_sha256,
            self.selected_observation_sha256,
            self.selected_manifest_id,
            self.selected_revision,
            self.selected_rights_manifest_sha256,
        )
        has_selection = all(value is not None for value in selection)
        if any(value is not None for value in selection) and not has_selection:
            raise ValueError("selected Dataset identity must be complete")
        if has_selection:
            validate_sha256(self.selected_logical_path_sha256, field_name="selected_logical_path_sha256")
            validate_sha256(self.selected_observation_sha256, field_name="selected_observation_sha256")
            validate_id(self.selected_manifest_id, IdKind.MANIFEST)
            if (
                isinstance(self.selected_revision, bool)
                or not isinstance(self.selected_revision, int)
                or self.selected_revision < 1
            ):
                raise ValueError("selected_revision must be positive")
            validate_sha256(
                self.selected_rights_manifest_sha256,
                field_name="selected_rights_manifest_sha256",
            )
            disposition_total = (
                self.eligible_candidate_count + self.needs_review_count + self.rejected_count
            )
            split_total = self.train_count + self.validation_count + self.test_count
            if self.entry_count < 1 or disposition_total != self.entry_count or split_total != self.entry_count:
                raise ValueError("selected Dataset aggregate counts do not match")
        elif any(
            getattr(self, name) != 0
            for name in (
                "entry_count",
                "eligible_candidate_count",
                "needs_review_count",
                "rejected_count",
                "train_count",
                "validation_count",
                "test_count",
            )
        ):
            raise ValueError("preflight without selection cannot expose Dataset counts")

        if self.status is DatasetEvidencePreflightStatus.BLOCKED_DISCOVERY:
            if has_selection or self.detail_code not in {"NO_DATASET_EVIDENCE", "INVALID_DATASET_EVIDENCE"}:
                raise ValueError("blocked discovery preflight is inconsistent")
            if self.requires_dataset_adoption_gate:
                raise ValueError("blocked discovery cannot require an adoption Gate")
        elif self.status is DatasetEvidencePreflightStatus.SELECTION_REQUIRED:
            if has_selection or self.detail_code != "SELECT_DATASET_REVISION":
                raise ValueError("selection-required preflight is inconsistent")
            if self.requires_dataset_adoption_gate:
                raise ValueError("missing selection cannot require an adoption Gate")
        elif self.status is DatasetEvidencePreflightStatus.EVIDENCE_REVIEW_READY:
            if not has_selection or self.mode is not DatasetEvidencePreflightMode.CONFIRMATION_ONLY:
                raise ValueError("evidence review preflight is inconsistent")
            if self.detail_code != "PASS_EVIDENCE_REVIEW" or self.requires_dataset_adoption_gate:
                raise ValueError("evidence review cannot require an adoption Gate")
        elif self.status is DatasetEvidencePreflightStatus.BLOCKED_NO_ELIGIBLE_CANDIDATE:
            if not has_selection or self.mode is not DatasetEvidencePreflightMode.LEARNING_PREPARATION:
                raise ValueError("blocked learning preflight is inconsistent")
            if (
                self.detail_code != "NO_ELIGIBLE_CANDIDATE"
                or self.eligible_candidate_count != 0
                or self.requires_dataset_adoption_gate
            ):
                raise ValueError("blocked learning preflight cannot request adoption")
        else:
            if not has_selection or self.mode is not DatasetEvidencePreflightMode.LEARNING_PREPARATION:
                raise ValueError("Dataset adoption review preflight is inconsistent")
            if (
                self.detail_code != "HUMAN_DATASET_ADOPTION_REQUIRED"
                or self.eligible_candidate_count < 1
                or not self.requires_dataset_adoption_gate
            ):
                raise ValueError("Dataset adoption review must remain Human-Gated")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": RECORD_KIND,
            "created_at": self.created_at,
            "discovery_observed_at": self.discovery_observed_at,
            "discovery_report_sha256": self.discovery_report_sha256,
            "mode": self.mode.value,
            "status": self.status.value,
            "detail_code": self.detail_code,
            "selected_logical_path_sha256": self.selected_logical_path_sha256,
            "selected_observation_sha256": self.selected_observation_sha256,
            "selected_manifest_id": self.selected_manifest_id,
            "selected_revision": self.selected_revision,
            "selected_rights_manifest_sha256": self.selected_rights_manifest_sha256,
            "entry_count": self.entry_count,
            "eligible_candidate_count": self.eligible_candidate_count,
            "needs_review_count": self.needs_review_count,
            "rejected_count": self.rejected_count,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "requires_dataset_adoption_gate": self.requires_dataset_adoption_gate,
            "dataset_adoption_authorized": self.dataset_adoption_authorized,
            "training_authorized": self.training_authorized,
            "state": self.state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "preflight_sha256": sha256_bytes(canonical_json_bytes(body))}


def _empty_preflight(
    *,
    created_at: str,
    discovery_observed_at: str,
    discovery_report_sha256: str,
    mode: DatasetEvidencePreflightMode,
    status: DatasetEvidencePreflightStatus,
    detail_code: str,
) -> DatasetEvidencePreflight:
    return DatasetEvidencePreflight(
        created_at=created_at,
        discovery_observed_at=discovery_observed_at,
        discovery_report_sha256=discovery_report_sha256,
        mode=mode,
        status=status,
        detail_code=detail_code,
        selected_logical_path_sha256=None,
        selected_observation_sha256=None,
        selected_manifest_id=None,
        selected_revision=None,
        selected_rights_manifest_sha256=None,
        entry_count=0,
        eligible_candidate_count=0,
        needs_review_count=0,
        rejected_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
        requires_dataset_adoption_gate=False,
    )


def _selected_preflight(
    *,
    created_at: str,
    discovery_observed_at: str,
    discovery_report_sha256: str,
    mode: DatasetEvidencePreflightMode,
    status: DatasetEvidencePreflightStatus,
    detail_code: str,
    item: DatasetDiscoveryItem,
    requires_dataset_adoption_gate: bool,
) -> DatasetEvidencePreflight:
    return DatasetEvidencePreflight(
        created_at=created_at,
        discovery_observed_at=discovery_observed_at,
        discovery_report_sha256=discovery_report_sha256,
        mode=mode,
        status=status,
        detail_code=detail_code,
        selected_logical_path_sha256=item.logical_path_sha256,
        selected_observation_sha256=item.observation_sha256,
        selected_manifest_id=item.manifest_id,
        selected_revision=item.revision,
        selected_rights_manifest_sha256=item.rights_manifest_sha256,
        entry_count=item.entry_count,
        eligible_candidate_count=item.eligible_candidate_count,
        needs_review_count=item.needs_review_count,
        rejected_count=item.rejected_count,
        train_count=item.train_count,
        validation_count=item.validation_count,
        test_count=item.test_count,
        requires_dataset_adoption_gate=requires_dataset_adoption_gate,
    )


def build_dataset_evidence_preflight(
    discovery_record: Mapping[str, object],
    *,
    created_at: str,
    mode: DatasetEvidencePreflightMode,
    selected_manifest_id: str | None = None,
    selected_revision: int | None = None,
    selected_rights_manifest_sha256: str | None = None,
) -> DatasetEvidencePreflight:
    _utc(created_at, field_name="created_at")
    if not isinstance(mode, DatasetEvidencePreflightMode):
        raise ValueError("mode must be DatasetEvidencePreflightMode")
    report = admit_dataset_discovery_report(discovery_record)
    report_sha256 = report.to_dict()["report_sha256"]
    requested = (selected_manifest_id, selected_revision, selected_rights_manifest_sha256)
    any_selected = any(value is not None for value in requested)
    all_selected = all(value is not None for value in requested)
    if any_selected and not all_selected:
        raise ValueError("selected Dataset identity must be complete")

    if report.status is not DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY:
        if any_selected:
            raise ValueError("selection is not allowed for a blocked discovery report")
        detail_code = (
            "NO_DATASET_EVIDENCE"
            if report.status is DatasetDiscoveryStatus.NO_MANIFEST_FOUND
            else "INVALID_DATASET_EVIDENCE"
        )
        return _empty_preflight(
            created_at=created_at,
            discovery_observed_at=report.observed_at,
            discovery_report_sha256=report_sha256,
            mode=mode,
            status=DatasetEvidencePreflightStatus.BLOCKED_DISCOVERY,
            detail_code=detail_code,
        )
    if not any_selected:
        return _empty_preflight(
            created_at=created_at,
            discovery_observed_at=report.observed_at,
            discovery_report_sha256=report_sha256,
            mode=mode,
            status=DatasetEvidencePreflightStatus.SELECTION_REQUIRED,
            detail_code="SELECT_DATASET_REVISION",
        )

    matches = tuple(
        item
        for item in report.items
        if item.status is DatasetDiscoveryItemStatus.ADMITTED
        and item.manifest_id == selected_manifest_id
        and item.revision == selected_revision
        and item.rights_manifest_sha256 == selected_rights_manifest_sha256
    )
    if len(matches) != 1:
        raise ValueError("selected Dataset identity is stale, crossed, or absent")
    item = matches[0]
    if mode is DatasetEvidencePreflightMode.CONFIRMATION_ONLY:
        return _selected_preflight(
            created_at=created_at,
            discovery_observed_at=report.observed_at,
            discovery_report_sha256=report_sha256,
            mode=mode,
            status=DatasetEvidencePreflightStatus.EVIDENCE_REVIEW_READY,
            detail_code="PASS_EVIDENCE_REVIEW",
            item=item,
            requires_dataset_adoption_gate=False,
        )
    if item.eligible_candidate_count == 0:
        return _selected_preflight(
            created_at=created_at,
            discovery_observed_at=report.observed_at,
            discovery_report_sha256=report_sha256,
            mode=mode,
            status=DatasetEvidencePreflightStatus.BLOCKED_NO_ELIGIBLE_CANDIDATE,
            detail_code="NO_ELIGIBLE_CANDIDATE",
            item=item,
            requires_dataset_adoption_gate=False,
        )
    return _selected_preflight(
        created_at=created_at,
        discovery_observed_at=report.observed_at,
        discovery_report_sha256=report_sha256,
        mode=mode,
        status=DatasetEvidencePreflightStatus.DATASET_ADOPTION_REVIEW_REQUIRED,
        detail_code="HUMAN_DATASET_ADOPTION_REQUIRED",
        item=item,
        requires_dataset_adoption_gate=True,
    )


def admit_dataset_evidence_preflight(record: Mapping[str, object]) -> DatasetEvidencePreflight:
    if not isinstance(record, Mapping):
        raise ValueError("Dataset Evidence preflight must be a mapping")
    expected = {
        "schema_version",
        "record_kind",
        *DatasetEvidencePreflight.__dataclass_fields__,
        "preflight_sha256",
    }
    if (
        set(record) != expected
        or record.get("schema_version") != SCHEMA_VERSION
        or record.get("record_kind") != RECORD_KIND
    ):
        raise ValueError("Dataset Evidence preflight shape is invalid")
    values = {name: record[name] for name in DatasetEvidencePreflight.__dataclass_fields__}
    values["mode"] = DatasetEvidencePreflightMode(values["mode"])
    values["status"] = DatasetEvidencePreflightStatus(values["status"])
    preflight = DatasetEvidencePreflight(**values)
    if preflight.to_dict() != dict(record):
        raise ValueError("Dataset Evidence preflight is not canonical")
    return preflight


__all__ = [
    "PREFLIGHT_STATE",
    "DatasetEvidencePreflight",
    "DatasetEvidencePreflightMode",
    "DatasetEvidencePreflightStatus",
    "admit_dataset_evidence_preflight",
    "build_dataset_evidence_preflight",
]
