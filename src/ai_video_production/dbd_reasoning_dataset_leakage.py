from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping
import unicodedata

from .dbd_reasoning_dataset_manifest import (
    DatasetSplit,
    DbDReasoningDatasetRightsManifest,
    admit_dbd_reasoning_dataset_rights_manifest,
)
from .dbd_reasoning_narration_intake import (
    DbDReasoningNarrationIntakeCandidate,
    admit_dbd_reasoning_narration_intake,
    validate_narration_intake_rights,
)
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


AUDIT_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_DATASET_LEAKAGE_REPORT"
AUDIT_STATE = "EVIDENCE_ONLY_NO_ADOPTION"
MIN_PHRASE_CHARS = 32
MAX_AUDIT_SEGMENTS = 2_048
MAX_TOTAL_NORMALIZED_CHARS = 250_000
MAX_REPORT_CANONICAL_BYTES = 2 * 1024 * 1024
_SPACE_RE = re.compile(r"\s+")


class LeakageAuditStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class LeakageKind(str, Enum):
    SOURCE_GROUP_SPLIT = "SOURCE_GROUP_SPLIT"
    MATCH_SPLIT = "MATCH_SPLIT"
    EXACT_TRANSCRIPT_DUPLICATE = "EXACT_TRANSCRIPT_DUPLICATE"
    PHRASE_OVERLAP = "PHRASE_OVERLAP"


@dataclass(frozen=True, slots=True)
class LeakageFinding:
    kind: LeakageKind
    left_segment_id: str
    right_segment_id: str
    left_split: DatasetSplit
    right_split: DatasetSplit
    fingerprint_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, LeakageKind):
            raise ValueError("finding kind is invalid")
        if not isinstance(self.left_split, DatasetSplit) or not isinstance(self.right_split, DatasetSplit):
            raise ValueError("finding split is invalid")
        validate_id(self.left_segment_id, IdKind.SEGMENT)
        validate_id(self.right_segment_id, IdKind.SEGMENT)
        if self.left_segment_id >= self.right_segment_id:
            raise ValueError("finding segment IDs must be canonical and distinct")
        if self.left_split is self.right_split:
            raise ValueError("finding must cross Dataset splits")
        validate_sha256(self.fingerprint_sha256, field_name="fingerprint_sha256")

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "left_segment_id": self.left_segment_id,
            "right_segment_id": self.right_segment_id,
            "left_split": self.left_split.value,
            "right_split": self.right_split.value,
            "fingerprint_sha256": self.fingerprint_sha256,
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningDatasetLeakageReport:
    rights_manifest_sha256: str
    audited_segments_sha256: str
    segment_count: int
    split_count: int
    findings: tuple[LeakageFinding, ...]
    status: LeakageAuditStatus
    audit_state: str = AUDIT_STATE

    def __post_init__(self) -> None:
        validate_sha256(self.rights_manifest_sha256, field_name="rights_manifest_sha256")
        validate_sha256(self.audited_segments_sha256, field_name="audited_segments_sha256")
        if (
            isinstance(self.segment_count, bool)
            or not isinstance(self.segment_count, int)
            or not 1 <= self.segment_count <= MAX_AUDIT_SEGMENTS
        ):
            raise ValueError("segment_count is invalid")
        if (
            isinstance(self.split_count, bool)
            or not isinstance(self.split_count, int)
            or not 1 <= self.split_count <= 3
        ):
            raise ValueError("split_count is invalid")
        if not isinstance(self.findings, tuple) or any(
            not isinstance(item, LeakageFinding) for item in self.findings
        ):
            raise ValueError("findings are invalid")
        keys = tuple(
            (item.kind.value, item.left_segment_id, item.right_segment_id, item.fingerprint_sha256)
            for item in self.findings
        )
        if keys != tuple(sorted(set(keys))):
            raise ValueError("findings must be sorted and unique")
        if not isinstance(self.status, LeakageAuditStatus):
            raise ValueError("status is invalid")
        expected = (
            LeakageAuditStatus.FAIL
            if self.findings
            else LeakageAuditStatus.PASS
            if self.split_count >= 2
            else LeakageAuditStatus.NOT_CONFIRMED
        )
        if self.status is not expected:
            raise ValueError("status does not match findings/split coverage")
        if self.audit_state != AUDIT_STATE:
            raise ValueError("R4C cannot grant Dataset adoption")
        if len(canonical_json_bytes(self.to_dict())) > MAX_REPORT_CANONICAL_BYTES:
            raise ValueError("report exceeds the canonical byte ceiling")

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": AUDIT_VERSION,
            "record_kind": RECORD_KIND,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "audited_segments_sha256": self.audited_segments_sha256,
            "segment_count": self.segment_count,
            "split_count": self.split_count,
            "findings": [item.to_dict() for item in self.findings],
            "status": self.status.value,
            "audit_state": self.audit_state,
        }
        return {**body, "report_sha256": sha256_bytes(canonical_json_bytes(body))}


def admit_dbd_reasoning_dataset_leakage_report(
    record: Mapping[str, Any],
) -> DbDReasoningDatasetLeakageReport:
    if not isinstance(record, Mapping):
        raise ValueError("leakage report must be a mapping")
    expected = {
        "schema_version",
        "record_kind",
        "rights_manifest_sha256",
        "audited_segments_sha256",
        "segment_count",
        "split_count",
        "findings",
        "status",
        "audit_state",
        "report_sha256",
    }
    if (
        set(record) != expected
        or record.get("schema_version") != AUDIT_VERSION
        or record.get("record_kind") != RECORD_KIND
    ):
        raise ValueError("leakage report shape or version is invalid")
    raw_findings = record.get("findings")
    if not isinstance(raw_findings, list):
        raise ValueError("findings must be a list")
    finding_keys = {
        "kind",
        "left_segment_id",
        "right_segment_id",
        "left_split",
        "right_split",
        "fingerprint_sha256",
    }
    findings: list[LeakageFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, Mapping) or set(raw) != finding_keys:
            raise ValueError("finding shape is invalid")
        values = dict(raw)
        values["kind"] = LeakageKind(values["kind"])
        values["left_split"] = DatasetSplit(values["left_split"])
        values["right_split"] = DatasetSplit(values["right_split"])
        findings.append(LeakageFinding(**values))
    report = DbDReasoningDatasetLeakageReport(
        rights_manifest_sha256=record["rights_manifest_sha256"],
        audited_segments_sha256=record["audited_segments_sha256"],
        segment_count=record["segment_count"],
        split_count=record["split_count"],
        findings=tuple(findings),
        status=LeakageAuditStatus(record["status"]),
        audit_state=record["audit_state"],
    )
    if report.to_dict() != dict(record):
        raise ValueError("leakage report checksum or canonical representation is invalid")
    return report


def _normalized(value: str) -> str:
    return _SPACE_RE.sub("", unicodedata.normalize("NFKC", value).casefold())


def _phrase_digests(normalized: str) -> frozenset[str]:
    if len(normalized) < MIN_PHRASE_CHARS:
        return frozenset()
    return frozenset(
        sha256_bytes(normalized[index : index + MIN_PHRASE_CHARS].encode())
        for index in range(len(normalized) - MIN_PHRASE_CHARS + 1)
    )


class DbDReasoningDatasetLeakageAuditor:
    @staticmethod
    def audit(
        manifest: DbDReasoningDatasetRightsManifest,
        segments: tuple[DbDReasoningNarrationIntakeCandidate, ...],
    ) -> DbDReasoningDatasetLeakageReport:
        manifest = admit_dbd_reasoning_dataset_rights_manifest(manifest.to_dict())
        if (
            not isinstance(segments, tuple)
            or not segments
            or len(segments) > MAX_AUDIT_SEGMENTS
        ):
            raise ValueError("segments are invalid or exceed the audit ceiling")
        admitted = tuple(
            validate_narration_intake_rights(
                admit_dbd_reasoning_narration_intake(segment.to_dict()), manifest
            )
            for segment in segments
        )
        segment_ids = tuple(segment.segment_id for segment in admitted)
        if segment_ids != tuple(sorted(set(segment_ids))):
            raise ValueError("segments must be sorted and unique")
        entries = {entry.candidate_id: entry for entry in manifest.entries}
        splits = {
            segment.segment_id: entries[segment.rights_candidate_id].split
            for segment in admitted
        }
        findings: list[LeakageFinding] = []
        groups: dict[str, tuple[str, DatasetSplit]] = {}
        matches: dict[str, tuple[str, DatasetSplit]] = {}
        for item in admitted:
            entry = entries[item.rights_candidate_id]
            for owners, key, kind in (
                (groups, entry.source_group_id, LeakageKind.SOURCE_GROUP_SPLIT),
                (matches, item.match_id, LeakageKind.MATCH_SPLIT),
            ):
                prior = owners.setdefault(key, (item.segment_id, entry.split))
                if prior[1] is not entry.split:
                    left, right = sorted((prior[0], item.segment_id))
                    findings.append(
                        LeakageFinding(
                            kind,
                            left,
                            right,
                            splits[left],
                            splits[right],
                            sha256_bytes(key.encode()),
                        )
                    )
        normalized = {
            segment.segment_id: _normalized(segment.redacted_transcript)
            for segment in admitted
        }
        if sum(len(value) for value in normalized.values()) > MAX_TOTAL_NORMALIZED_CHARS:
            raise ValueError("transcripts exceed the aggregate audit ceiling")
        exact_owners: dict[str, dict[DatasetSplit, str]] = {}
        phrase_owners: dict[str, dict[DatasetSplit, str]] = {}
        for item in admitted:
            item_split = splits[item.segment_id]
            owners = exact_owners.setdefault(item.corrected_transcript_sha256, {})
            other = next(
                (
                    (split_value, segment_id)
                    for split_value, segment_id in owners.items()
                    if split_value is not item_split
                ),
                None,
            )
            if other is not None:
                left, right = sorted((other[1], item.segment_id))
                findings.append(
                    LeakageFinding(
                        LeakageKind.EXACT_TRANSCRIPT_DUPLICATE,
                        left,
                        right,
                        splits[left],
                        splits[right],
                        item.corrected_transcript_sha256,
                    )
                )
            owners.setdefault(item_split, item.segment_id)
            phrase_digests = _phrase_digests(normalized[item.segment_id])
            crossing: tuple[str, str] | None = None
            for digest in sorted(phrase_digests):
                old = next(
                    (
                        (split_value, segment_id)
                        for split_value, segment_id in phrase_owners.get(digest, {}).items()
                        if split_value is not item_split
                    ),
                    None,
                )
                if old is not None:
                    crossing = (digest, old[1])
                    break
            if crossing is not None and other is None:
                left, right = sorted((crossing[1], item.segment_id))
                findings.append(
                    LeakageFinding(
                        LeakageKind.PHRASE_OVERLAP,
                        left,
                        right,
                        splits[left],
                        splits[right],
                        crossing[0],
                    )
                )
            for digest in phrase_digests:
                phrase_owners.setdefault(digest, {}).setdefault(item_split, item.segment_id)
        canonical_findings = tuple(
            sorted(
                set(findings),
                key=lambda item: (
                    item.kind.value,
                    item.left_segment_id,
                    item.right_segment_id,
                    item.fingerprint_sha256,
                ),
            )
        )
        split_count = len(set(splits.values()))
        status = (
            LeakageAuditStatus.FAIL
            if canonical_findings
            else LeakageAuditStatus.PASS
            if split_count >= 2
            else LeakageAuditStatus.NOT_CONFIRMED
        )
        return DbDReasoningDatasetLeakageReport(
            manifest.to_dict()["rights_manifest_sha256"],
            sha256_bytes(canonical_json_bytes([segment.to_dict() for segment in admitted])),
            len(admitted),
            split_count,
            canonical_findings,
            status,
        )


__all__ = [
    "AUDIT_STATE",
    "DbDReasoningDatasetLeakageAuditor",
    "DbDReasoningDatasetLeakageReport",
    "LeakageAuditStatus",
    "LeakageFinding",
    "LeakageKind",
    "MAX_AUDIT_SEGMENTS",
    "MAX_REPORT_CANONICAL_BYTES",
    "MAX_TOTAL_NORMALIZED_CHARS",
    "admit_dbd_reasoning_dataset_leakage_report",
]
