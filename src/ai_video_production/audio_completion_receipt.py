"""Pure TASK-041 Audio Completion admission-candidate contract R0.

Body-free coordinates only. No I/O, canonical minting, store/latest selection,
Final Review Gate issuance, or source-authority reissuance is performed.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256

SCHEMA_VERSION = "bai.task041.audio-completion-admission-candidate.v1"
SCHEMA_ID = "https://baisound.dev/schemas/audio-completion-receipt.schema.json"
_SCOPE_DOMAIN = b"TASK041_AUDIO_COMPLETION_SCOPE_BINDING_V1\0"
_EVIDENCE_DOMAIN = b"TASK041_AUDIO_COMPLETION_EVIDENCE_BINDING_V1\0"
_PRIVATE_DOMAIN = b"TASK041_AUDIO_COMPLETION_ADMISSION_CANDIDATE_PRIVATE_V1\0"
_PUBLIC_DOMAIN = b"TASK041_AUDIO_COMPLETION_ADMISSION_CANDIDATE_PUBLIC_V1\0"
_CANDIDATE_CONSTRUCTION_TOKEN = object()
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
_MAX_ITEMS = 1024


class AudioCompletionRole(str, Enum):
    SOURCE = "SOURCE"
    SE = "SE"
    BGM = "BGM"
    AMBIENCE = "AMBIENCE"
    NARRATION = "NARRATION"
    MIX_STEM = "MIX_STEM"


class RoleRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class RolePresence(str, Enum):
    PRESENT = "PRESENT"
    ABSENT_CONFIRMED = "ABSENT_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class FinishingRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    REVOKED = "REVOKED"


class CandidateState(str, Enum):
    SOURCE_REVALIDATION_REQUIRED = "SOURCE_REVALIDATION_REQUIRED"


class CanonicalState(str, Enum):
    NOT_MINTED = "NOT_MINTED"


_ROLE_ORDER = tuple(role.value for role in AudioCompletionRole)
_REF_MATRIX = MappingProxyType({
    "review_receipt": ("TASK-041", "AudioMediaReviewDecision"),
    "external_review_receipt": ("TASK-041", "ExternalAudioReviewReceiptBinding"),
    "placement_receipt": ("TASK-026", "AudioPlacementCompilationRecord"),
    "narration_publication_receipt": ("TASK-014", "NarrationPublicationReceipt"),
    "finishing_receipt": ("TASK-035", "AudioRoundTripManifest"),
})
_AUTHORITY_FLAGS = MappingProxyType({
    "canonical_admission_authorized": False,
    "canonical_receipt_minted": False,
    "source_authority_reissued": False,
    "store_write_authorized": False,
    "latest_state_authorized": False,
    "final_review_gate_issued": False,
})
_EFFECT_FLAGS = MappingProxyType({
    "filesystem_read": False, "filesystem_written": False,
    "network_accessed": False, "provider_called": False,
    "paid_call_started": False, "audio_read": False, "audio_written": False,
    "asset_published": False, "placement_mutated": False,
    "daw_operation_started": False, "release_started": False,
    "deployment_started": False,
})


def _exact(value: Mapping[str, Any], fields: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identity(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} is invalid")
    return validate_sha256(value, field_name=name)


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a positive bounded integer")
    return value


def _epoch(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be a bounded non-negative integer")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError(f"{name} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be canonical UTC") from exc
    return parsed


def _enum(kind: type[Enum], value: Any, name: str) -> Enum:
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is invalid") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != field}


@dataclass(frozen=True, slots=True)
class ScopeBinding:
    _data: Mapping[str, Any]

    @classmethod
    def create(cls, *, project_id: str, project_revision: int, project_manifest_sha256: str,
               timeline_id: str, timeline_revision: int, timeline_sha256: str,
               workspace_snapshot_sha256: str, source_truth_receipt_id: str,
               source_truth_receipt_sha256: str,
               role_policy_receipt_id: str, role_policy_receipt_sha256: str,
               source_truth_owner: str = "TASK-041",
               source_truth_record_type: str = "AudioCompletionSourceTruthReceipt",
               role_policy_owner: str = "TASK-041",
               role_policy_record_type: str = "AudioCompletionRolePolicy") -> "ScopeBinding":
        body = {
            "project_id": project_id, "project_revision": project_revision,
            "project_manifest_sha256": project_manifest_sha256,
            "timeline_id": timeline_id, "timeline_revision": timeline_revision,
            "timeline_sha256": timeline_sha256,
            "workspace_snapshot_sha256": workspace_snapshot_sha256,
            "source_truth_receipt_id": source_truth_receipt_id,
            "source_truth_receipt_sha256": source_truth_receipt_sha256,
            "source_truth_owner": source_truth_owner,
            "source_truth_record_type": source_truth_record_type,
            "role_policy_receipt_id": role_policy_receipt_id,
            "role_policy_receipt_sha256": role_policy_receipt_sha256,
            "role_policy_owner": role_policy_owner,
            "role_policy_record_type": role_policy_record_type,
            "requirements_authority_verified": False,
            "source_origin_authenticated": False,
        }
        body["scope_binding_sha256"] = sha256_bytes(_SCOPE_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScopeBinding":
        _exact(value, {"project_id", "project_revision", "project_manifest_sha256",
            "timeline_id", "timeline_revision", "timeline_sha256", "workspace_snapshot_sha256",
            "source_truth_receipt_id", "source_truth_receipt_sha256", "source_truth_owner",
            "source_truth_record_type", "role_policy_receipt_id", "role_policy_receipt_sha256",
            "role_policy_owner", "role_policy_record_type", "requirements_authority_verified",
            "source_origin_authenticated",
            "scope_binding_sha256"}, "ScopeBinding")
        _identity(value["project_id"], "project_id"); _positive(value["project_revision"], "project_revision")
        _digest(value["project_manifest_sha256"], "project_manifest_sha256")
        _identity(value["timeline_id"], "timeline_id"); _positive(value["timeline_revision"], "timeline_revision")
        _digest(value["timeline_sha256"], "timeline_sha256")
        _digest(value["workspace_snapshot_sha256"], "workspace_snapshot_sha256")
        _identity(value["source_truth_receipt_id"], "source_truth_receipt_id")
        _digest(value["source_truth_receipt_sha256"], "source_truth_receipt_sha256")
        if value["source_truth_owner"] != "TASK-041":
            raise ValueError("source truth owner is outside the closed boundary")
        if value["source_truth_record_type"] != "AudioCompletionSourceTruthReceipt":
            raise ValueError("source truth record type is outside the closed boundary")
        _identity(value["role_policy_receipt_id"], "role_policy_receipt_id")
        _digest(value["role_policy_receipt_sha256"], "role_policy_receipt_sha256")
        if value["role_policy_owner"] != "TASK-041" or value["role_policy_record_type"] != "AudioCompletionRolePolicy":
            raise ValueError("role policy coordinate is outside the closed boundary")
        if value["requirements_authority_verified"] is not False or value["source_origin_authenticated"] is not False:
            raise ValueError("R0 cannot verify requirements authority or source origin")
        expected = sha256_bytes(_SCOPE_DOMAIN + canonical_json_bytes(_without(value, "scope_binding_sha256")))
        if value["scope_binding_sha256"] != expected:
            raise ValueError("scope binding digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True)
class ClosedReceiptRef:
    authority_owner: str
    record_type: str
    record_id: str
    record_sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], field_name: str) -> "ClosedReceiptRef":
        _exact(value, {"authority_owner", "record_type", "record_id", "record_sha256"}, field_name)
        if field_name not in _REF_MATRIX or (value["authority_owner"], value["record_type"]) != _REF_MATRIX[field_name]:
            raise ValueError(f"{field_name} owner/type binding is invalid")
        _identity(value["record_id"], f"{field_name}.record_id")
        _digest(value["record_sha256"], f"{field_name}.record_sha256")
        return cls(**copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        return {"authority_owner": self.authority_owner, "record_type": self.record_type,
                "record_id": self.record_id, "record_sha256": self.record_sha256}


def make_closed_receipt_ref(field_name: str, *, record_id: str, record_sha256: str) -> ClosedReceiptRef:
    if field_name not in _REF_MATRIX:
        raise ValueError("receipt reference kind is outside the closed matrix")
    owner, record_type = _REF_MATRIX[field_name]
    return ClosedReceiptRef.from_dict({"authority_owner": owner, "record_type": record_type,
        "record_id": record_id, "record_sha256": record_sha256}, field_name)


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    _data: Mapping[str, Any]

    @classmethod
    def create(cls, *, item_id: str, role: AudioCompletionRole, item_source_sha256: str,
               review_receipt: ClosedReceiptRef, external_review_receipt: ClosedReceiptRef,
               placement_receipt: ClosedReceiptRef, narration_publication_receipt: ClosedReceiptRef | None,
               finishing_receipt: ClosedReceiptRef | None, evidence_state: EvidenceState,
               evidence_current_at_evaluation: bool, evidence_invalidation_epoch: int) -> "EvidenceBinding":
        if not isinstance(role, AudioCompletionRole) or not isinstance(evidence_state, EvidenceState):
            raise ValueError("role/state must use the closed enum")
        required_refs = (review_receipt, external_review_receipt, placement_receipt)
        optional_refs = (narration_publication_receipt, finishing_receipt)
        if any(not isinstance(item, ClosedReceiptRef) for item in required_refs):
            raise ValueError("required receipt coordinates must use ClosedReceiptRef")
        if any(item is not None and not isinstance(item, ClosedReceiptRef) for item in optional_refs):
            raise ValueError("optional receipt coordinates must use ClosedReceiptRef or None")
        body = {
            "record_type": "AudioCompletionEvidenceBinding", "item_id": item_id,
            "role": role.value, "item_source_sha256": item_source_sha256,
            "review_receipt": review_receipt.to_dict(),
            "external_review_receipt": external_review_receipt.to_dict(),
            "placement_receipt": placement_receipt.to_dict(),
            "narration_publication_receipt": None if narration_publication_receipt is None else narration_publication_receipt.to_dict(),
            "finishing_receipt": None if finishing_receipt is None else finishing_receipt.to_dict(),
            "evidence_state": evidence_state.value,
            "evidence_current_at_evaluation": evidence_current_at_evaluation,
            "evidence_invalidation_epoch": evidence_invalidation_epoch,
            "source_authority_reissued": False,
        }
        body["evidence_binding_sha256"] = sha256_bytes(_EVIDENCE_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceBinding":
        _exact(value, {"record_type", "item_id", "role", "item_source_sha256",
            "review_receipt", "external_review_receipt", "placement_receipt",
            "narration_publication_receipt", "finishing_receipt", "evidence_state",
            "evidence_current_at_evaluation", "evidence_invalidation_epoch",
            "source_authority_reissued", "evidence_binding_sha256"}, "EvidenceBinding")
        if value["record_type"] != "AudioCompletionEvidenceBinding":
            raise ValueError("evidence record_type is invalid")
        _identity(value["item_id"], "item_id"); _digest(value["item_source_sha256"], "item_source_sha256")
        role = _enum(AudioCompletionRole, value["role"], "role")
        state = _enum(EvidenceState, value["evidence_state"], "evidence_state")
        assert isinstance(role, AudioCompletionRole) and isinstance(state, EvidenceState)
        ClosedReceiptRef.from_dict(value["review_receipt"], "review_receipt")
        ClosedReceiptRef.from_dict(value["external_review_receipt"], "external_review_receipt")
        ClosedReceiptRef.from_dict(value["placement_receipt"], "placement_receipt")
        narration = value["narration_publication_receipt"]
        if (role is AudioCompletionRole.NARRATION) != (narration is not None):
            raise ValueError("only NARRATION requires a publication receipt")
        if narration is not None:
            ClosedReceiptRef.from_dict(narration, "narration_publication_receipt")
        if value["finishing_receipt"] is not None:
            ClosedReceiptRef.from_dict(value["finishing_receipt"], "finishing_receipt")
        current = value["evidence_current_at_evaluation"]
        if not isinstance(current, bool):
            raise ValueError("evidence currentness must be boolean")
        epoch = _epoch(value["evidence_invalidation_epoch"], "evidence_invalidation_epoch")
        if state in {EvidenceState.PASS, EvidenceState.FAIL, EvidenceState.UNKNOWN}:
            if not current or epoch != 0:
                raise ValueError("active evidence requires current=true and epoch zero")
        elif current or epoch < 1:
            raise ValueError("stale/revoked evidence requires current=false and an epoch")
        if value["source_authority_reissued"] is not False:
            raise ValueError("evidence wrapper cannot reissue source authority")
        expected = sha256_bytes(_EVIDENCE_DOMAIN + canonical_json_bytes(_without(value, "evidence_binding_sha256")))
        if value["evidence_binding_sha256"] != expected:
            raise ValueError("evidence binding digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)


@dataclass(frozen=True, slots=True)
class RoleDeclaration:
    role: AudioCompletionRole
    requirement: RoleRequirement
    presence: RolePresence
    finishing_requirement: FinishingRequirement
    expected_item_ids: tuple[str, ...]
    expected_item_binding_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        if not all(isinstance(value, kind) for value, kind in (
            (self.role, AudioCompletionRole), (self.requirement, RoleRequirement),
            (self.presence, RolePresence), (self.finishing_requirement, FinishingRequirement))):
            raise ValueError("role declaration enums are invalid")
        ids, hashes = self.expected_item_ids, self.expected_item_binding_sha256s
        if not isinstance(ids, tuple) or not isinstance(hashes, tuple) or len(ids) != len(hashes) or len(ids) > _MAX_ITEMS:
            raise ValueError("expected item coordinates are inconsistent or unbounded")
        for item_id in ids: _identity(item_id, "expected_item_id")
        for digest in hashes: _digest(digest, "expected_item_binding_sha256")
        if len(set(hashes)) != len(hashes):
            raise ValueError("expected item binding hashes must be unique within a role")
        if list(ids) != sorted(ids, key=str.casefold) or len({item.casefold() for item in ids}) != len(ids):
            raise ValueError("expected item ids must be casefold-unique canonical order")
        if self.requirement is RoleRequirement.REQUIRED and not ids:
            raise ValueError("required roles cannot be empty")
        if self.requirement is RoleRequirement.REQUIRED and self.presence is RolePresence.ABSENT_CONFIRMED:
            raise ValueError("required roles cannot be absent")
        if self.requirement is RoleRequirement.OPTIONAL and not ids and self.presence is not RolePresence.ABSENT_CONFIRMED:
            raise ValueError("optional omission must be absent-confirmed")
        if ids and self.presence is RolePresence.ABSENT_CONFIRMED:
            raise ValueError("absent-confirmed roles cannot retain expected items")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RoleDeclaration":
        _exact(value, {"role", "requirement", "presence", "finishing_requirement",
            "expected_item_ids", "expected_item_binding_sha256s"}, "RoleDeclaration")
        ids, hashes = value["expected_item_ids"], value["expected_item_binding_sha256s"]
        if not isinstance(ids, list) or not isinstance(hashes, list):
            raise ValueError("expected item coordinates must be arrays")
        return cls(_enum(AudioCompletionRole, value["role"], "role"),
            _enum(RoleRequirement, value["requirement"], "requirement"),
            _enum(RolePresence, value["presence"], "presence"),
            _enum(FinishingRequirement, value["finishing_requirement"], "finishing_requirement"),
            tuple(ids), tuple(hashes))  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role.value, "requirement": self.requirement.value,
            "presence": self.presence.value, "finishing_requirement": self.finishing_requirement.value,
            "expected_item_ids": list(self.expected_item_ids),
            "expected_item_binding_sha256s": list(self.expected_item_binding_sha256s)}


def _classify(roles: Sequence[RoleDeclaration], evidence: Sequence[EvidenceBinding]) -> tuple[CandidateState, tuple[str, ...]]:
    del roles, evidence
    return (
        CandidateState.SOURCE_REVALIDATION_REQUIRED,
        ("SOURCE_RECORDS_REQUIRE_OWNER_API_REVALIDATION",),
    )


@dataclass(frozen=True, slots=True, init=False)
class AudioCompletionAdmissionCandidate:
    _data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str] = "AudioCompletionAdmissionCandidate"

    def __init__(self, data: Mapping[str, Any], *, _token: object | None = None) -> None:
        if _token is not _CANDIDATE_CONSTRUCTION_TOKEN:
            raise TypeError("AudioCompletionAdmissionCandidate must use a validated factory")
        object.__setattr__(self, "_data", data)

    def __reduce__(self) -> object:
        raise TypeError("serialize the validated receipt dictionary, not the typed object")

    @classmethod
    def create(cls, *, receipt_id: str, scope: ScopeBinding,
               role_declarations: Sequence[RoleDeclaration],
               evidence_bindings: Sequence[EvidenceBinding], evaluated_at: str,
               previous: "AudioCompletionAdmissionCandidate | None" = None) -> "AudioCompletionAdmissionCandidate":
        roles, evidence = tuple(role_declarations), tuple(evidence_bindings)
        if previous is None:
            revision, parent = 1, None
        else:
            if not isinstance(previous, cls):
                raise TypeError("previous must be an exact AudioCompletionAdmissionCandidate")
            prior = cls.from_dict(previous.to_dict()).to_dict()
            if prior["canonical_state"] != CanonicalState.NOT_MINTED.value:
                raise ValueError("R0 create cannot append to or invalidate canonical diagnostics")
            if prior["receipt_id"] != receipt_id or prior["scope_binding_sha256"] != scope.to_dict()["scope_binding_sha256"]:
                raise ValueError("append identity/scope mismatch")
            if _timestamp(evaluated_at, "evaluated_at") <= _timestamp(prior["evaluated_at"], "previous.evaluated_at"):
                raise ValueError("append time must advance")
            revision, parent = prior["revision"] + 1, prior["receipt_sha256"]
        state, reasons = _classify(roles, evidence)
        body = {
            "schema_version": SCHEMA_VERSION, "record_type": cls.RECORD_TYPE,
            "task_owner": "TASK-041", "receipt_id": receipt_id, "revision": revision,
            "parent_receipt_sha256": parent, "scope_binding": scope.to_dict(),
            "scope_binding_sha256": scope.to_dict()["scope_binding_sha256"],
            "role_declarations": [role.to_dict() for role in roles],
            "evidence_bindings": [item.to_dict() for item in evidence],
            "candidate_state": state.value, "canonical_state": CanonicalState.NOT_MINTED.value,
            "reason_codes": list(reasons), "evaluated_at": evaluated_at,
            "current_valid": False, "invalidation_epoch": 0,
            "inputs_origin_authenticated": False,
            "source_records_semantically_revalidated": False,
            "chain_diagnostic": {"parent_link_checked_in_memory": False, "parent_link_matches": False,
                "revision_gap_absence_verified": False, "fork_absence_verified": False,
                "latest_state_verified": False, "persistence_verified": False},
            "authority_flags": dict(_AUTHORITY_FLAGS), "effect_flags": dict(_EFFECT_FLAGS),
        }
        body["receipt_sha256"] = sha256_bytes(_PRIVATE_DOMAIN + canonical_json_bytes(body))
        return cls.from_dict(body)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioCompletionAdmissionCandidate":
        _exact(value, {"schema_version", "record_type", "task_owner", "receipt_id", "revision",
            "parent_receipt_sha256", "scope_binding", "scope_binding_sha256", "role_declarations",
            "evidence_bindings", "candidate_state", "canonical_state", "reason_codes",
            "evaluated_at", "current_valid", "invalidation_epoch", "inputs_origin_authenticated",
            "source_records_semantically_revalidated", "chain_diagnostic",
            "authority_flags", "effect_flags", "receipt_sha256"}, cls.RECORD_TYPE)
        if value["schema_version"] != SCHEMA_VERSION or value["record_type"] != cls.RECORD_TYPE or value["task_owner"] != "TASK-041":
            raise ValueError("candidate identity/version is invalid")
        _identity(value["receipt_id"], "receipt_id")
        revision = _positive(value["revision"], "revision")
        parent = _digest(value["parent_receipt_sha256"], "parent_receipt_sha256", nullable=True)
        if (revision == 1) != (parent is None):
            raise ValueError("genesis/append parent invariant is invalid")
        scope = ScopeBinding.from_dict(value["scope_binding"])
        if value["scope_binding_sha256"] != scope.to_dict()["scope_binding_sha256"]:
            raise ValueError("root scope hash does not match embedded scope")
        raw_roles, raw_evidence = value["role_declarations"], value["evidence_bindings"]
        if not isinstance(raw_roles, list) or not isinstance(raw_evidence, list) or len(raw_evidence) > _MAX_ITEMS:
            raise ValueError("role/evidence collections are invalid or unbounded")
        roles = tuple(RoleDeclaration.from_dict(item) for item in raw_roles)
        evidence = tuple(EvidenceBinding.from_dict(item) for item in raw_evidence)
        if tuple(role.role.value for role in roles) != _ROLE_ORDER:
            raise ValueError("roles must contain the exact closed canonical order")
        order = [(item.to_dict()["role"], item.to_dict()["item_id"].casefold()) for item in evidence]
        if order != sorted(order, key=lambda item: (_ROLE_ORDER.index(item[0]), item[1])):
            raise ValueError("evidence bindings are not in canonical role/item order")
        hashes = [item.to_dict()["evidence_binding_sha256"] for item in evidence]
        item_ids = [item.to_dict()["item_id"] for item in evidence]
        expected_hashes = [digest for role in roles for digest in role.expected_item_binding_sha256s]
        expected_ids = [item_id for role in roles for item_id in role.expected_item_ids]
        if (
            len(set(hashes)) != len(hashes)
            or len(set(expected_hashes)) != len(expected_hashes)
            or len({item.casefold() for item in item_ids}) != len(item_ids)
            or len({item.casefold() for item in expected_ids}) != len(expected_ids)
            or set(hashes) - set(expected_hashes)
        ):
            raise ValueError("evidence bindings are duplicated or undeclared")
        by_hash = {item.to_dict()["evidence_binding_sha256"]: item.to_dict() for item in evidence}
        for declaration in roles:
            if declaration.presence is RolePresence.UNKNOWN:
                if any(item_hash in by_hash for item_hash in declaration.expected_item_binding_sha256s):
                    raise ValueError("unknown role cannot carry resolved item evidence")
                continue
            if declaration.presence is not RolePresence.PRESENT:
                continue
            for item_id, item_hash in zip(
                declaration.expected_item_ids,
                declaration.expected_item_binding_sha256s,
            ):
                bound = by_hash.get(item_hash)
                if bound is None or bound["item_id"] != item_id or bound["role"] != declaration.role.value:
                    raise ValueError("present role does not have exact item evidence closure")
                if declaration.finishing_requirement is FinishingRequirement.REQUIRED and bound["finishing_receipt"] is None:
                    raise ValueError("required finishing evidence is absent")
                if declaration.finishing_requirement is FinishingRequirement.NOT_APPLICABLE and bound["finishing_receipt"] is not None:
                    raise ValueError("finishing evidence is present for a not-applicable role")
        state, reasons = _classify(roles, evidence)
        if value["candidate_state"] != state.value or value["reason_codes"] != list(reasons):
            raise ValueError("candidate state/reasons do not match source facts")
        canonical = _enum(CanonicalState, value["canonical_state"], "canonical_state")
        current, epoch = value["current_valid"], _epoch(value["invalidation_epoch"], "invalidation_epoch")
        if not isinstance(current, bool):
            raise ValueError("current_valid must be boolean")
        if canonical is not CanonicalState.NOT_MINTED or current or epoch != 0:
            raise ValueError("R0 canonical state is fixed to NOT_MINTED/non-current/epoch-zero")
        if value["inputs_origin_authenticated"] is not False or value["source_records_semantically_revalidated"] is not False:
            raise ValueError("R0 cannot claim source origin authentication or semantic revalidation")
        _timestamp(value["evaluated_at"], "evaluated_at")
        if value["chain_diagnostic"] != {"parent_link_checked_in_memory": False, "parent_link_matches": False,
                "revision_gap_absence_verified": False, "fork_absence_verified": False,
                "latest_state_verified": False, "persistence_verified": False}:
            raise ValueError("R0 cannot claim store/latest/fork/gap truth")
        if value["authority_flags"] != dict(_AUTHORITY_FLAGS) or value["effect_flags"] != dict(_EFFECT_FLAGS):
            raise ValueError("candidate authority/effect boundary is invalid")
        expected = sha256_bytes(_PRIVATE_DOMAIN + canonical_json_bytes(_without(value, "receipt_sha256")))
        if value["receipt_sha256"] != expected:
            raise ValueError("candidate private digest mismatch")
        return cls(_freeze(copy.deepcopy(dict(value))), _token=_CANDIDATE_CONSTRUCTION_TOKEN)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    def to_public_dict(self) -> dict[str, Any]:
        private = type(self).from_dict(self.to_dict()).to_dict()
        roles = private["role_declarations"]
        public = {"schema_version": SCHEMA_VERSION,
            "record_type": "AudioCompletionAdmissionCandidatePublicProjection",
            "candidate_state": private["candidate_state"], "canonical_state": private["canonical_state"],
            "reason_codes": list(private["reason_codes"]), "role_count": len(roles),
            "required_role_count": sum(role["requirement"] == "REQUIRED" for role in roles),
            "present_role_count": sum(role["presence"] == "PRESENT" for role in roles),
            "item_count": len(private["evidence_bindings"]),
            "inputs_origin_authenticated": False,
            "source_records_semantically_revalidated": False,
            "canonical_admission_authorized": False}
        public["public_projection_sha256"] = sha256_bytes(_PUBLIC_DOMAIN + canonical_json_bytes(public))
        return public


def parse_audio_completion_admission_candidate(value: Mapping[str, Any]) -> AudioCompletionAdmissionCandidate:
    return AudioCompletionAdmissionCandidate.from_dict(value)


def validate_audio_completion_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> tuple[AudioCompletionAdmissionCandidate, AudioCompletionAdmissionCandidate]:
    """Validate an observed pair without minting, persisting, or choosing latest."""
    before, after = AudioCompletionAdmissionCandidate.from_dict(previous), AudioCompletionAdmissionCandidate.from_dict(current)
    left, right = before.to_dict(), after.to_dict()
    if right["receipt_id"] != left["receipt_id"] or right["scope_binding_sha256"] != left["scope_binding_sha256"]:
        raise ValueError("transition identity/scope mismatch")
    if right["revision"] != left["revision"] + 1 or right["parent_receipt_sha256"] != left["receipt_sha256"]:
        raise ValueError("transition revision/parent link mismatch")
    if _timestamp(right["evaluated_at"], "current.evaluated_at") <= _timestamp(left["evaluated_at"], "previous.evaluated_at"):
        raise ValueError("transition time must advance")
    return before, after


__all__ = ["AudioCompletionAdmissionCandidate", "AudioCompletionRole", "CandidateState",
    "CanonicalState", "ClosedReceiptRef", "EvidenceBinding", "EvidenceState",
    "FinishingRequirement", "RoleDeclaration", "RolePresence", "RoleRequirement",
    "SCHEMA_ID", "SCHEMA_VERSION", "ScopeBinding", "make_closed_receipt_ref",
    "parse_audio_completion_admission_candidate", "validate_audio_completion_transition"]
