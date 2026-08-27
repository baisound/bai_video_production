"""TASK-054 R6B-D read-only Dataset adoption execution preflight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Mapping, Protocol

from .dbd_reasoning_dataset_adoption_authority import admit_dataset_adoption_request
from .dbd_reasoning_dataset_manifest import (
    DatasetRowDisposition,
    DbDReasoningDatasetRightsEntry,
    admit_dbd_reasoning_dataset_rights_manifest,
)
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
AUTHORITY_RECORD_KIND = "DBD_REASONING_DATASET_ADOPTION_PREFLIGHT_AUTHORITY"
PLAN_RECORD_KIND = "DBD_REASONING_DATASET_ADOPTION_COMMIT_PLAN"
AUTHORITY_SCOPE = "DATASET_ADOPTION_READ_ONLY_PREFLIGHT"
AUTHORITY_STATE = "ALLOWED_READ_ONLY_DATASET_ADOPTION_PREFLIGHT"
PLAN_STATE = "READY_FOR_SEPARATE_DATASET_ADOPTION_COMMIT_AUTHORITY"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_CANDIDATE_ID = re.compile(r"^CAND-R2D[0-9A-HJKMNP-TV-Z]{23}$")


def _utc(value: str, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ValueError(f"{field_name} must be an RFC3339 UTC timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_id(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")


def _optional_sha256(value: str | None, *, field_name: str) -> None:
    if value is not None:
        validate_sha256(value, field_name=field_name)


def _load_schema() -> Mapping[str, object]:
    from importlib.resources import files

    return json.loads(
        files("ai_video_production.schema_resources")
        .joinpath("dbd-reasoning-dataset-adoption-preflight.schema.json")
        .read_text(encoding="utf-8")
    )


def _validate_schema(record: Mapping[str, object]) -> None:
    from jsonschema import Draft202012Validator

    if list(Draft202012Validator(_load_schema()).iter_errors(dict(record))):
        raise ValueError("Dataset adoption preflight record does not satisfy JSON Schema")


@dataclass(frozen=True, slots=True)
class DatasetAdoptionPreflightAuthority:
    authorization_id: str
    authority_evidence_sha256: str
    request_sha256: str
    manifest_id: str
    revision: int
    rights_manifest_sha256: str
    logical_path_sha256: str
    observation_sha256: str
    dataset_store_id: str
    expected_store_sha256: str | None
    not_before: str
    expires_at: str
    authorization_scope: str = AUTHORITY_SCOPE
    authorization_state: str = AUTHORITY_STATE

    def __post_init__(self) -> None:
        _safe_id(self.authorization_id, field_name="authorization_id")
        _safe_id(self.dataset_store_id, field_name="dataset_store_id")
        validate_id(self.manifest_id, IdKind.MANIFEST)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        for name in (
            "authority_evidence_sha256",
            "request_sha256",
            "rights_manifest_sha256",
            "logical_path_sha256",
            "observation_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _optional_sha256(self.expected_store_sha256, field_name="expected_store_sha256")
        if _utc(self.not_before, field_name="not_before") >= _utc(
            self.expires_at, field_name="expires_at"
        ):
            raise ValueError("authorization validity interval is invalid")
        if self.authorization_scope != AUTHORITY_SCOPE or self.authorization_state != AUTHORITY_STATE:
            raise ValueError("Dataset adoption preflight authority boundary is invalid")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": AUTHORITY_RECORD_KIND,
            **{name: getattr(self, name) for name in self.__dataclass_fields__},
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "authorization_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class DatasetAdoptionPlannedMembership:
    candidate_id: str
    candidate_sha256: str
    lineage_sha256: str
    human_review_sha256: str
    match_id: str
    source_group_id: str
    split: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_ID.fullmatch(self.candidate_id):
            raise ValueError("candidate_id is invalid")
        validate_id(self.match_id, IdKind.GAME_MATCH)
        for name in ("candidate_sha256", "lineage_sha256", "human_review_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        _safe_id(self.source_group_id, field_name="source_group_id")
        if self.split not in {"TRAIN", "VALIDATION", "TEST"}:
            raise ValueError("split is invalid")

    @classmethod
    def from_rights_entry(
        cls,
        entry: DbDReasoningDatasetRightsEntry,
    ) -> "DatasetAdoptionPlannedMembership":
        return cls(
            candidate_id=entry.candidate_id,
            candidate_sha256=entry.candidate_sha256,
            lineage_sha256=entry.lineage_sha256,
            human_review_sha256=entry.human_review_sha256,
            match_id=entry.match_id,
            source_group_id=entry.source_group_id,
            split=entry.split.value,
        )

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class DatasetAdoptionCommitPlan:
    plan_id: str
    adoption_request_sha256: str
    preflight_authorization_sha256: str
    authority_evidence_sha256: str
    manifest_id: str
    source_manifest_revision: int
    rights_manifest_sha256: str
    logical_path_sha256: str
    observation_sha256: str
    dataset_store_id: str
    expected_store_sha256: str | None
    memberships: tuple[DatasetAdoptionPlannedMembership, ...]
    member_count: int
    train_count: int
    validation_count: int
    test_count: int
    created_at: str
    dataset_adoption_requested: bool = True
    dataset_adoption_started: bool = False
    dataset_store_mutated: bool = False
    training_authorized: bool = False
    training_started: bool = False
    plan_state: str = PLAN_STATE

    def __post_init__(self) -> None:
        _safe_id(self.plan_id, field_name="plan_id")
        _safe_id(self.dataset_store_id, field_name="dataset_store_id")
        validate_id(self.manifest_id, IdKind.MANIFEST)
        if (
            isinstance(self.source_manifest_revision, bool)
            or not isinstance(self.source_manifest_revision, int)
            or self.source_manifest_revision < 1
        ):
            raise ValueError("source_manifest_revision must be positive")
        for name in (
            "adoption_request_sha256",
            "preflight_authorization_sha256",
            "authority_evidence_sha256",
            "rights_manifest_sha256",
            "logical_path_sha256",
            "observation_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _optional_sha256(self.expected_store_sha256, field_name="expected_store_sha256")
        if not self.memberships or any(
            not isinstance(item, DatasetAdoptionPlannedMembership) for item in self.memberships
        ):
            raise ValueError("memberships must contain at least one planned membership")
        ids = tuple(item.candidate_id for item in self.memberships)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("memberships must be unique and sorted")
        groups: dict[str, str] = {}
        for item in self.memberships:
            prior = groups.setdefault(item.source_group_id, item.split)
            if prior != item.split:
                raise ValueError("source group crosses Dataset splits")
        counts = {
            "TRAIN": sum(item.split == "TRAIN" for item in self.memberships),
            "VALIDATION": sum(item.split == "VALIDATION" for item in self.memberships),
            "TEST": sum(item.split == "TEST" for item in self.memberships),
        }
        if (
            isinstance(self.member_count, bool)
            or self.member_count != len(self.memberships)
            or self.train_count != counts["TRAIN"]
            or self.validation_count != counts["VALIDATION"]
            or self.test_count != counts["TEST"]
            or self.member_count != self.train_count + self.validation_count + self.test_count
        ):
            raise ValueError("planned membership counts are inconsistent")
        _utc(self.created_at, field_name="created_at")
        if (
            self.dataset_adoption_requested is not True
            or self.dataset_adoption_started is not False
            or self.dataset_store_mutated is not False
            or self.training_authorized is not False
            or self.training_started is not False
            or self.plan_state != PLAN_STATE
        ):
            raise ValueError("Dataset adoption preflight plan effect boundary is invalid")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": PLAN_RECORD_KIND,
            "plan_id": self.plan_id,
            "adoption_request_sha256": self.adoption_request_sha256,
            "preflight_authorization_sha256": self.preflight_authorization_sha256,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "manifest_id": self.manifest_id,
            "source_manifest_revision": self.source_manifest_revision,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "logical_path_sha256": self.logical_path_sha256,
            "observation_sha256": self.observation_sha256,
            "dataset_store_id": self.dataset_store_id,
            "expected_store_sha256": self.expected_store_sha256,
            "memberships": [item.to_dict() for item in self.memberships],
            "member_count": self.member_count,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "created_at": self.created_at,
            "dataset_adoption_requested": self.dataset_adoption_requested,
            "dataset_adoption_started": self.dataset_adoption_started,
            "dataset_store_mutated": self.dataset_store_mutated,
            "training_authorized": self.training_authorized,
            "training_started": self.training_started,
            "plan_state": self.plan_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "plan_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class DatasetManifestRead:
    logical_path_sha256: str
    observation_sha256: str
    manifest_record: Mapping[str, object]

    def __post_init__(self) -> None:
        validate_sha256(self.logical_path_sha256, field_name="logical_path_sha256")
        validate_sha256(self.observation_sha256, field_name="observation_sha256")
        if not isinstance(self.manifest_record, Mapping):
            raise ValueError("manifest_record must be a mapping")


@dataclass(frozen=True, slots=True)
class DatasetStoreCapability:
    dataset_store_id: str
    current_store_sha256: str | None
    encrypted_at_rest: bool
    atomic_compare_and_swap: bool
    authoritative_read_back: bool
    append_only_revisions: bool
    one_shot_authority_evidence: bool

    def __post_init__(self) -> None:
        _safe_id(self.dataset_store_id, field_name="dataset_store_id")
        _optional_sha256(self.current_store_sha256, field_name="current_store_sha256")
        for name in (
            "encrypted_at_rest",
            "atomic_compare_and_swap",
            "authoritative_read_back",
            "append_only_revisions",
            "one_shot_authority_evidence",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")


class DatasetAdoptionPreflightAuthorityVerifier(Protocol):
    def verify(
        self,
        authority_evidence_sha256: str,
        authorization_sha256: str,
    ) -> bool: ...


class DatasetManifestReader(Protocol):
    def read_current_manifest(self, manifest_id: str, revision: int) -> DatasetManifestRead: ...


class DatasetStoreCapabilityReader(Protocol):
    def read_capability(self) -> DatasetStoreCapability: ...


def admit_dataset_adoption_preflight_authority(
    record: Mapping[str, object],
) -> DatasetAdoptionPreflightAuthority:
    if not isinstance(record, Mapping):
        raise ValueError("Dataset adoption preflight authority must be a mapping")
    _validate_schema(record)
    expected = {
        "schema_version",
        "record_kind",
        *DatasetAdoptionPreflightAuthority.__dataclass_fields__,
        "authorization_sha256",
    }
    if set(record) != expected or record.get("record_kind") != AUTHORITY_RECORD_KIND:
        raise ValueError("Dataset adoption preflight authority shape is invalid")
    values = {name: record[name] for name in DatasetAdoptionPreflightAuthority.__dataclass_fields__}
    authority = DatasetAdoptionPreflightAuthority(**values)
    if authority.to_dict() != dict(record):
        raise ValueError("Dataset adoption preflight authority is not exact canonical form")
    return authority


def admit_dataset_adoption_commit_plan(
    record: Mapping[str, object],
) -> DatasetAdoptionCommitPlan:
    if not isinstance(record, Mapping):
        raise ValueError("Dataset adoption commit plan must be a mapping")
    _validate_schema(record)
    expected = {
        "schema_version",
        "record_kind",
        *DatasetAdoptionCommitPlan.__dataclass_fields__,
        "plan_sha256",
    }
    if set(record) != expected or record.get("record_kind") != PLAN_RECORD_KIND:
        raise ValueError("Dataset adoption commit plan shape is invalid")
    raw_memberships = record.get("memberships")
    if not isinstance(raw_memberships, list):
        raise ValueError("memberships must be a list")
    member_keys = set(DatasetAdoptionPlannedMembership.__dataclass_fields__)
    memberships = []
    for raw in raw_memberships:
        if not isinstance(raw, Mapping) or set(raw) != member_keys:
            raise ValueError("planned Dataset membership shape is invalid")
        memberships.append(DatasetAdoptionPlannedMembership(**dict(raw)))
    values = {name: record[name] for name in DatasetAdoptionCommitPlan.__dataclass_fields__}
    values["memberships"] = tuple(memberships)
    plan = DatasetAdoptionCommitPlan(**values)
    if plan.to_dict() != dict(record):
        raise ValueError("Dataset adoption commit plan is not exact canonical form")
    return plan


def build_dataset_adoption_execution_preflight(
    request_record: Mapping[str, object],
    preflight_authority_record: Mapping[str, object],
    *,
    plan_id: str,
    now: str,
    authority_verifier: DatasetAdoptionPreflightAuthorityVerifier,
    manifest_reader: DatasetManifestReader,
    store_capability_reader: DatasetStoreCapabilityReader,
) -> DatasetAdoptionCommitPlan:
    """Compile a read-only plan; no collaborator exposes a mutation operation."""

    if authority_verifier is None or not callable(getattr(authority_verifier, "verify", None)):
        raise ValueError("authority_verifier must implement verify")
    if manifest_reader is None or not callable(getattr(manifest_reader, "read_current_manifest", None)):
        raise ValueError("manifest_reader must implement read_current_manifest")
    if store_capability_reader is None or not callable(
        getattr(store_capability_reader, "read_capability", None)
    ):
        raise ValueError("store_capability_reader must implement read_capability")
    _safe_id(plan_id, field_name="plan_id")
    observed_at = _utc(now, field_name="now")
    request = admit_dataset_adoption_request(request_record)
    authority = admit_dataset_adoption_preflight_authority(preflight_authority_record)
    request_sha256 = request.to_dict()["request_sha256"]
    if (
        authority.request_sha256,
        authority.manifest_id,
        authority.revision,
        authority.rights_manifest_sha256,
        authority.logical_path_sha256,
        authority.observation_sha256,
    ) != (
        request_sha256,
        request.manifest_id,
        request.revision,
        request.rights_manifest_sha256,
        request.logical_path_sha256,
        request.observation_sha256,
    ):
        raise ProductError(
            "ERR_DBD_R6BD_AUTHORITY_CROSSED",
            "Dataset adoption preflight Authority does not match the exact request",
            ProductErrorCategory.AUTHORIZATION,
        )
    if not _utc(authority.not_before, field_name="not_before") <= observed_at < _utc(
        authority.expires_at, field_name="expires_at"
    ):
        raise ProductError(
            "ERR_DBD_R6BD_AUTHORITY_INACTIVE",
            "Dataset adoption preflight Authority is not active",
            ProductErrorCategory.AUTHORIZATION,
        )
    authorization_sha256 = authority.to_dict()["authorization_sha256"]
    if authority_verifier.verify(authority.authority_evidence_sha256, authorization_sha256) is not True:
        raise ProductError(
            "ERR_DBD_R6BD_AUTHORITY_UNTRUSTED",
            "Dataset adoption preflight Authority Evidence is not trusted",
            ProductErrorCategory.AUTHORIZATION,
        )

    capability = store_capability_reader.read_capability()
    if not isinstance(capability, DatasetStoreCapability):
        raise ProductError(
            "ERR_DBD_R6BD_STORE_CAPABILITY_INVALID",
            "Dataset Store capability is invalid",
            ProductErrorCategory.SECURITY,
        )
    if capability.dataset_store_id != authority.dataset_store_id or not all(
        (
            capability.encrypted_at_rest,
            capability.atomic_compare_and_swap,
            capability.authoritative_read_back,
            capability.append_only_revisions,
            capability.one_shot_authority_evidence,
        )
    ):
        raise ProductError(
            "ERR_DBD_R6BD_STORE_CAPABILITY_INSUFFICIENT",
            "Dataset Store does not satisfy the adoption persistence floor",
            ProductErrorCategory.SECURITY,
        )
    if capability.current_store_sha256 != authority.expected_store_sha256:
        raise ProductError(
            "ERR_DBD_R6BD_STORE_HEAD_DRIFT",
            "Current Dataset Store head does not match the authorized expected digest",
            ProductErrorCategory.STATE,
        )

    manifest_read = manifest_reader.read_current_manifest(request.manifest_id, request.revision)
    if not isinstance(manifest_read, DatasetManifestRead):
        raise ProductError(
            "ERR_DBD_R6BD_MANIFEST_READ_INVALID",
            "Current Dataset manifest read is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if (
        manifest_read.logical_path_sha256 != request.logical_path_sha256
        or manifest_read.observation_sha256 != request.observation_sha256
    ):
        raise ProductError(
            "ERR_DBD_R6BD_MANIFEST_LOCATION_DRIFT",
            "Current Dataset manifest observation no longer matches the request",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    try:
        manifest = admit_dbd_reasoning_dataset_rights_manifest(manifest_read.manifest_record)
    except (TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_DBD_R6BD_MANIFEST_INVALID",
            "Current Dataset rights manifest failed exact admission",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    if (
        manifest.manifest_id != request.manifest_id
        or manifest.revision != request.revision
        or manifest.to_dict()["rights_manifest_sha256"] != request.rights_manifest_sha256
    ):
        raise ProductError(
            "ERR_DBD_R6BD_MANIFEST_CROSSED",
            "Current Dataset rights manifest no longer matches the request",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    memberships = tuple(
        DatasetAdoptionPlannedMembership.from_rights_entry(entry)
        for entry in manifest.entries
        if entry.disposition is DatasetRowDisposition.ELIGIBLE_CANDIDATE
    )
    if not memberships:
        raise ProductError(
            "ERR_DBD_R6BD_NO_ELIGIBLE_MEMBERS",
            "Current Dataset rights manifest has no eligible Dataset members",
            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
        )
    return DatasetAdoptionCommitPlan(
        plan_id=plan_id,
        adoption_request_sha256=request_sha256,
        preflight_authorization_sha256=authorization_sha256,
        authority_evidence_sha256=authority.authority_evidence_sha256,
        manifest_id=manifest.manifest_id,
        source_manifest_revision=manifest.revision,
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],
        logical_path_sha256=request.logical_path_sha256,
        observation_sha256=request.observation_sha256,
        dataset_store_id=authority.dataset_store_id,
        expected_store_sha256=authority.expected_store_sha256,
        memberships=memberships,
        member_count=len(memberships),
        train_count=sum(item.split == "TRAIN" for item in memberships),
        validation_count=sum(item.split == "VALIDATION" for item in memberships),
        test_count=sum(item.split == "TEST" for item in memberships),
        created_at=now,
    )


__all__ = [
    "AUTHORITY_SCOPE",
    "AUTHORITY_STATE",
    "PLAN_STATE",
    "DatasetAdoptionCommitPlan",
    "DatasetAdoptionPlannedMembership",
    "DatasetAdoptionPreflightAuthority",
    "DatasetAdoptionPreflightAuthorityVerifier",
    "DatasetManifestRead",
    "DatasetManifestReader",
    "DatasetStoreCapability",
    "DatasetStoreCapabilityReader",
    "admit_dataset_adoption_commit_plan",
    "admit_dataset_adoption_preflight_authority",
    "build_dataset_adoption_execution_preflight",
]
