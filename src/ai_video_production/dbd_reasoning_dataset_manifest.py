from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
RECORD_KIND = "DBD_REASONING_DATASET_RIGHTS_MANIFEST"
MANIFEST_STATE = "CANDIDATE_ONLY_NO_ADOPTION"
MAX_MANIFEST_ENTRIES = 2_048
MAX_MANIFEST_CANONICAL_BYTES = 2 * 1024 * 1024
_CANDIDATE_RE = re.compile(r"^CAND-R2D[0-9A-HJKMNP-TV-Z]{23}$")
_GROUP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_HASH_REF_RE = re.compile(
    r"^(?:media|rights|consent|provenance|human-review)://sha256/[0-9a-f]{64}$"
)


class DatasetSplit(str, Enum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


class RightsDecision(str, Enum):
    ADMITTED_FOR_TRAINING = "ADMITTED_FOR_TRAINING"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class ConsentDecision(str, Enum):
    EXPLICIT_TRAINING = "EXPLICIT_TRAINING"
    NOT_REQUIRED_NON_PERSONAL = "NOT_REQUIRED_NON_PERSONAL"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class DatasetRowDisposition(str, Enum):
    ELIGIBLE_CANDIDATE = "ELIGIBLE_CANDIDATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


def _hash_ref(value: str, *, scheme: str, name: str) -> None:
    if not isinstance(value, str) or not _HASH_REF_RE.fullmatch(value) or not value.startswith(f"{scheme}://"):
        raise ValueError(f"{name} must be a body-free {scheme} sha256 reference")


def _expected_disposition(rights: RightsDecision, consent: ConsentDecision) -> DatasetRowDisposition:
    if rights in {RightsDecision.REJECTED, RightsDecision.REVOKED} or consent in {
        ConsentDecision.REJECTED, ConsentDecision.REVOKED,
    }:
        return DatasetRowDisposition.REJECTED
    if rights is RightsDecision.ADMITTED_FOR_TRAINING and consent in {
        ConsentDecision.EXPLICIT_TRAINING, ConsentDecision.NOT_REQUIRED_NON_PERSONAL,
    }:
        return DatasetRowDisposition.ELIGIBLE_CANDIDATE
    return DatasetRowDisposition.NEEDS_REVIEW


@dataclass(frozen=True, slots=True)
class DbDReasoningDatasetRightsEntry:
    candidate_id: str
    candidate_sha256: str
    lineage_sha256: str
    human_review_sha256: str
    human_review_ref: str
    match_id: str
    source_group_id: str
    source_ref: str
    split: DatasetSplit
    patch_version: str
    locale: str
    rights_decision: RightsDecision
    rights_ref: str
    consent_decision: ConsentDecision
    consent_ref: str
    provenance_ref: str
    disposition: DatasetRowDisposition
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_RE.fullmatch(self.candidate_id):
            raise ValueError("candidate_id must use the CAND-R2D namespace")
        validate_id(self.match_id, IdKind.GAME_MATCH)
        for name in ("candidate_sha256", "lineage_sha256", "human_review_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if not isinstance(self.source_group_id, str) or not _GROUP_RE.fullmatch(self.source_group_id):
            raise ValueError("source_group_id is invalid")
        if not isinstance(self.split, DatasetSplit):
            raise ValueError("split must be DatasetSplit")
        if not isinstance(self.patch_version, str) or not _VERSION_RE.fullmatch(self.patch_version):
            raise ValueError("patch_version is invalid")
        if not isinstance(self.locale, str) or not _LOCALE_RE.fullmatch(self.locale):
            raise ValueError("locale is invalid")
        for value, expected in (
            (self.rights_decision, RightsDecision), (self.consent_decision, ConsentDecision),
            (self.disposition, DatasetRowDisposition),
        ):
            if not isinstance(value, expected):
                raise ValueError(f"{expected.__name__} value is invalid")
        for value, scheme, name in (
            (self.source_ref, "media", "source_ref"), (self.rights_ref, "rights", "rights_ref"),
            (self.consent_ref, "consent", "consent_ref"),
            (self.provenance_ref, "provenance", "provenance_ref"),
            (self.human_review_ref, "human-review", "human_review_ref"),
        ):
            _hash_ref(value, scheme=scheme, name=name)
        if self.disposition is not _expected_disposition(self.rights_decision, self.consent_decision):
            raise ValueError("disposition does not match rights and consent decisions")
        if not isinstance(self.reason_codes, tuple) or self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("reason_codes must be a sorted unique tuple")
        if len(self.reason_codes) > 32:
            raise ValueError("reason_codes exceed the manifest ceiling")
        if any(not _VERSION_RE.fullmatch(code) or code.upper() != code for code in self.reason_codes):
            raise ValueError("reason_codes contain an invalid stable code")
        if self.disposition is DatasetRowDisposition.ELIGIBLE_CANDIDATE and self.reason_codes:
            raise ValueError("eligible candidates cannot carry rejection reasons")
        if self.disposition is not DatasetRowDisposition.ELIGIBLE_CANDIDATE and not self.reason_codes:
            raise ValueError("non-eligible candidates require reason codes")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id, "candidate_sha256": self.candidate_sha256,
            "lineage_sha256": self.lineage_sha256, "human_review_sha256": self.human_review_sha256,
            "human_review_ref": self.human_review_ref, "match_id": self.match_id,
            "source_group_id": self.source_group_id, "source_ref": self.source_ref,
            "split": self.split.value, "patch_version": self.patch_version, "locale": self.locale,
            "rights_decision": self.rights_decision.value, "rights_ref": self.rights_ref,
            "consent_decision": self.consent_decision.value, "consent_ref": self.consent_ref,
            "provenance_ref": self.provenance_ref, "disposition": self.disposition.value,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class DbDReasoningDatasetRightsManifest:
    manifest_id: str
    revision: int
    entries: tuple[DbDReasoningDatasetRightsEntry, ...]
    manifest_state: str = MANIFEST_STATE

    def __post_init__(self) -> None:
        validate_id(self.manifest_id, IdKind.MANIFEST)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be a positive integer")
        if self.manifest_state != MANIFEST_STATE:
            raise ValueError("R4A cannot grant Dataset adoption")
        if not self.entries or any(not isinstance(item, DbDReasoningDatasetRightsEntry) for item in self.entries):
            raise ValueError("entries must contain Dataset rights entries")
        if len(self.entries) > MAX_MANIFEST_ENTRIES:
            raise ValueError("entries exceed the manifest ceiling")
        ids = tuple(item.candidate_id for item in self.entries)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("entries must be unique and sorted by candidate_id")
        groups: dict[str, DatasetSplit] = {}
        for entry in self.entries:
            prior = groups.setdefault(entry.source_group_id, entry.split)
            if prior is not entry.split:
                raise ValueError("source group leakage across Dataset splits")
        if len(canonical_json_bytes(self._body())) > MAX_MANIFEST_CANONICAL_BYTES:
            raise ValueError("manifest exceeds the canonical byte ceiling")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION, "record_kind": RECORD_KIND,
            "manifest_id": self.manifest_id, "revision": self.revision,
            "manifest_state": self.manifest_state,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "rights_manifest_sha256": sha256_bytes(canonical_json_bytes(body))}


def admit_dbd_reasoning_dataset_rights_manifest(record: Mapping[str, Any]) -> DbDReasoningDatasetRightsManifest:
    if not isinstance(record, Mapping):
        raise ValueError("manifest record must be a mapping")
    expected = {"schema_version", "record_kind", "manifest_id", "revision", "manifest_state", "entries", "rights_manifest_sha256"}
    if set(record) != expected or record.get("schema_version") != SCHEMA_VERSION or record.get("record_kind") != RECORD_KIND:
        raise ValueError("manifest record shape or version is invalid")
    raw_entries = record.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("entries must be a list")
    entry_keys = set(DbDReasoningDatasetRightsEntry.__dataclass_fields__)
    entries: list[DbDReasoningDatasetRightsEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, Mapping) or set(raw) != entry_keys:
            raise ValueError("entry record shape is invalid")
        values = dict(raw)
        values["split"] = DatasetSplit(values["split"])
        values["rights_decision"] = RightsDecision(values["rights_decision"])
        values["consent_decision"] = ConsentDecision(values["consent_decision"])
        values["disposition"] = DatasetRowDisposition(values["disposition"])
        if not isinstance(values["reason_codes"], list):
            raise ValueError("reason_codes must be a list")
        values["reason_codes"] = tuple(values["reason_codes"])
        entries.append(DbDReasoningDatasetRightsEntry(**values))
    manifest = DbDReasoningDatasetRightsManifest(
        manifest_id=record["manifest_id"], revision=record["revision"],
        entries=tuple(entries), manifest_state=record["manifest_state"],
    )
    if manifest.to_dict() != dict(record):
        raise ValueError("manifest checksum or canonical representation is invalid")
    return manifest


__all__ = [
    "ConsentDecision", "DatasetRowDisposition", "DatasetSplit",
    "DbDReasoningDatasetRightsEntry", "DbDReasoningDatasetRightsManifest",
    "MANIFEST_STATE", "MAX_MANIFEST_CANONICAL_BYTES", "MAX_MANIFEST_ENTRIES",
    "RightsDecision", "admit_dbd_reasoning_dataset_rights_manifest",
]
