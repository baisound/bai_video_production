"""TASK-054 R6B-C body-free Dataset adoption authority admission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Mapping, Protocol

from .dbd_reasoning_dataset_preflight import (
    DatasetEvidencePreflightMode,
    DatasetEvidencePreflightStatus,
    admit_dataset_evidence_preflight,
)
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_VERSION = "1.0.0"
AUTHORITY_RECORD_KIND = "DBD_REASONING_DATASET_ADOPTION_AUTHORITY"
REQUEST_RECORD_KIND = "DBD_REASONING_DATASET_ADOPTION_REQUEST"
AUTHORITY_SCOPE = "DATASET_ADOPTION_REQUEST_ONLY"
AUTHORITY_STATE = "ALLOWED_SINGLE_DATASET_ADOPTION_REQUEST"
REQUEST_STATE = "AUTHORIZED_PROPOSAL_NO_DATASET_ADOPTION_OR_TRAINING_EFFECT"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


def _utc(value: str, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ValueError(f"{field_name} must be an RFC3339 UTC timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_id(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")


def _load_schema() -> Mapping[str, object]:
    from importlib.resources import files

    return json.loads(
        files("ai_video_production.schema_resources")
        .joinpath("dbd-reasoning-dataset-adoption-authority.schema.json")
        .read_text(encoding="utf-8")
    )


def _validate_schema(record: Mapping[str, object]) -> None:
    from jsonschema import Draft202012Validator

    if list(Draft202012Validator(_load_schema()).iter_errors(dict(record))):
        raise ValueError("Dataset adoption authority record does not satisfy JSON Schema")


@dataclass(frozen=True, slots=True)
class DatasetAdoptionAuthority:
    authorization_id: str
    authority_evidence_sha256: str
    preflight_sha256: str
    manifest_id: str
    revision: int
    rights_manifest_sha256: str
    logical_path_sha256: str
    observation_sha256: str
    not_before: str
    expires_at: str
    max_adoption_requests: int = 1
    authorization_scope: str = AUTHORITY_SCOPE
    authorization_state: str = AUTHORITY_STATE

    def __post_init__(self) -> None:
        _safe_id(self.authorization_id, field_name="authorization_id")
        validate_id(self.manifest_id, IdKind.MANIFEST)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        for name in (
            "authority_evidence_sha256",
            "preflight_sha256",
            "rights_manifest_sha256",
            "logical_path_sha256",
            "observation_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if _utc(self.not_before, field_name="not_before") >= _utc(
            self.expires_at, field_name="expires_at"
        ):
            raise ValueError("authorization validity interval is invalid")
        if self.max_adoption_requests != 1:
            raise ValueError("R6B-C authorizes one Dataset adoption request")
        if self.authorization_scope != AUTHORITY_SCOPE or self.authorization_state != AUTHORITY_STATE:
            raise ValueError("Dataset adoption authorization boundary is invalid")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": AUTHORITY_RECORD_KIND,
            "authorization_id": self.authorization_id,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "preflight_sha256": self.preflight_sha256,
            "manifest_id": self.manifest_id,
            "revision": self.revision,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "logical_path_sha256": self.logical_path_sha256,
            "observation_sha256": self.observation_sha256,
            "not_before": self.not_before,
            "expires_at": self.expires_at,
            "max_adoption_requests": self.max_adoption_requests,
            "authorization_scope": self.authorization_scope,
            "authorization_state": self.authorization_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "authorization_sha256": sha256_bytes(canonical_json_bytes(body))}


@dataclass(frozen=True, slots=True)
class DatasetAdoptionRequest:
    request_id: str
    authorization_sha256: str
    authority_evidence_sha256: str
    preflight_sha256: str
    manifest_id: str
    revision: int
    rights_manifest_sha256: str
    logical_path_sha256: str
    observation_sha256: str
    created_at: str
    dataset_adoption_requested: bool = True
    dataset_adoption_started: bool = False
    training_authorized: bool = False
    training_started: bool = False
    request_state: str = REQUEST_STATE

    def __post_init__(self) -> None:
        _safe_id(self.request_id, field_name="request_id")
        validate_id(self.manifest_id, IdKind.MANIFEST)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be positive")
        for name in (
            "authorization_sha256",
            "authority_evidence_sha256",
            "preflight_sha256",
            "rights_manifest_sha256",
            "logical_path_sha256",
            "observation_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        _utc(self.created_at, field_name="created_at")
        if self.dataset_adoption_requested is not True:
            raise ValueError("Dataset adoption request must be explicit")
        if (
            self.dataset_adoption_started is not False
            or self.training_authorized is not False
            or self.training_started is not False
            or self.request_state != REQUEST_STATE
        ):
            raise ValueError("R6B-C request cannot start Dataset adoption or training")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": REQUEST_RECORD_KIND,
            "request_id": self.request_id,
            "authorization_sha256": self.authorization_sha256,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "preflight_sha256": self.preflight_sha256,
            "manifest_id": self.manifest_id,
            "revision": self.revision,
            "rights_manifest_sha256": self.rights_manifest_sha256,
            "logical_path_sha256": self.logical_path_sha256,
            "observation_sha256": self.observation_sha256,
            "created_at": self.created_at,
            "dataset_adoption_requested": self.dataset_adoption_requested,
            "dataset_adoption_started": self.dataset_adoption_started,
            "training_authorized": self.training_authorized,
            "training_started": self.training_started,
            "request_state": self.request_state,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "request_sha256": sha256_bytes(canonical_json_bytes(body))}


class DatasetAdoptionAuthorityVerifier(Protocol):
    def verify(self, authority_evidence_sha256: str) -> bool: ...


class DatasetAdoptionAuthorityUseStore(Protocol):
    def claim_once(self, authorization_sha256: str) -> bool: ...


def admit_dataset_adoption_authority(record: Mapping[str, object]) -> DatasetAdoptionAuthority:
    if not isinstance(record, Mapping):
        raise ValueError("Dataset adoption authority must be a mapping")
    _validate_schema(record)
    expected = {
        "schema_version",
        "record_kind",
        *DatasetAdoptionAuthority.__dataclass_fields__,
        "authorization_sha256",
    }
    if set(record) != expected or record.get("record_kind") != AUTHORITY_RECORD_KIND:
        raise ValueError("Dataset adoption authority shape is invalid")
    values = {name: record[name] for name in DatasetAdoptionAuthority.__dataclass_fields__}
    authority = DatasetAdoptionAuthority(**values)
    if authority.to_dict() != dict(record):
        raise ValueError("Dataset adoption authority is not exact canonical form")
    return authority


def admit_dataset_adoption_request(record: Mapping[str, object]) -> DatasetAdoptionRequest:
    if not isinstance(record, Mapping):
        raise ValueError("Dataset adoption request must be a mapping")
    _validate_schema(record)
    expected = {
        "schema_version",
        "record_kind",
        *DatasetAdoptionRequest.__dataclass_fields__,
        "request_sha256",
    }
    if set(record) != expected or record.get("record_kind") != REQUEST_RECORD_KIND:
        raise ValueError("Dataset adoption request shape is invalid")
    values = {name: record[name] for name in DatasetAdoptionRequest.__dataclass_fields__}
    request = DatasetAdoptionRequest(**values)
    if request.to_dict() != dict(record):
        raise ValueError("Dataset adoption request is not exact canonical form")
    return request


def build_dataset_adoption_request(
    preflight_record: Mapping[str, object],
    authority_record: Mapping[str, object],
    *,
    request_id: str,
    now: str,
    authority_verifier: DatasetAdoptionAuthorityVerifier,
    authority_use_store: DatasetAdoptionAuthorityUseStore,
) -> DatasetAdoptionRequest:
    if authority_verifier is None or not callable(getattr(authority_verifier, "verify", None)):
        raise ValueError("authority_verifier must implement verify")
    if authority_use_store is None or not callable(getattr(authority_use_store, "claim_once", None)):
        raise ValueError("authority_use_store must implement claim_once")
    _safe_id(request_id, field_name="request_id")
    observed = _utc(now, field_name="now")
    preflight = admit_dataset_evidence_preflight(preflight_record)
    authority = admit_dataset_adoption_authority(authority_record)

    if (
        preflight.mode is not DatasetEvidencePreflightMode.LEARNING_PREPARATION
        or preflight.status is not DatasetEvidencePreflightStatus.DATASET_ADOPTION_REVIEW_REQUIRED
        or not preflight.requires_dataset_adoption_gate
        or preflight.eligible_candidate_count < 1
        or preflight.dataset_adoption_authorized
        or preflight.training_authorized
    ):
        raise ProductError(
            "ERR_DBD_R6BC_PREFLIGHT_INELIGIBLE",
            "Dataset Evidence preflight is not eligible for adoption authority admission",
            ProductErrorCategory.AUTHORIZATION,
        )
    expected = (
        preflight.to_dict()["preflight_sha256"],
        preflight.selected_manifest_id,
        preflight.selected_revision,
        preflight.selected_rights_manifest_sha256,
        preflight.selected_logical_path_sha256,
        preflight.selected_observation_sha256,
    )
    actual = (
        authority.preflight_sha256,
        authority.manifest_id,
        authority.revision,
        authority.rights_manifest_sha256,
        authority.logical_path_sha256,
        authority.observation_sha256,
    )
    if actual != expected:
        raise ProductError(
            "ERR_DBD_R6BC_AUTHORITY_CROSSED",
            "Dataset adoption authority does not match the selected Dataset Evidence",
            ProductErrorCategory.AUTHORIZATION,
        )
    if not _utc(authority.not_before, field_name="not_before") <= observed < _utc(
        authority.expires_at, field_name="expires_at"
    ):
        raise ProductError(
            "ERR_DBD_R6BC_AUTHORITY_INACTIVE",
            "Dataset adoption authority is not active",
            ProductErrorCategory.AUTHORIZATION,
        )
    if authority_verifier.verify(authority.authority_evidence_sha256) is not True:
        raise ProductError(
            "ERR_DBD_R6BC_AUTHORITY_UNTRUSTED",
            "Dataset adoption authority Evidence is not trusted",
            ProductErrorCategory.AUTHORIZATION,
        )

    authorization_sha256 = authority.to_dict()["authorization_sha256"]
    request = DatasetAdoptionRequest(
        request_id=request_id,
        authorization_sha256=authorization_sha256,
        authority_evidence_sha256=authority.authority_evidence_sha256,
        preflight_sha256=authority.preflight_sha256,
        manifest_id=authority.manifest_id,
        revision=authority.revision,
        rights_manifest_sha256=authority.rights_manifest_sha256,
        logical_path_sha256=authority.logical_path_sha256,
        observation_sha256=authority.observation_sha256,
        created_at=now,
    )
    if authority_use_store.claim_once(authorization_sha256) is not True:
        raise ProductError(
            "ERR_DBD_R6BC_AUTHORITY_REUSED",
            "Dataset adoption authority was already consumed",
            ProductErrorCategory.AUTHORIZATION,
        )
    return request


__all__ = [
    "AUTHORITY_SCOPE",
    "AUTHORITY_STATE",
    "REQUEST_STATE",
    "DatasetAdoptionAuthority",
    "DatasetAdoptionAuthorityUseStore",
    "DatasetAdoptionAuthorityVerifier",
    "DatasetAdoptionRequest",
    "admit_dataset_adoption_authority",
    "admit_dataset_adoption_request",
    "build_dataset_adoption_request",
]
