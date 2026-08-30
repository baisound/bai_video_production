"""Pure TASK-054 R3A tuned-model binding registry.

The registry admits immutable lifecycle Evidence and resolves only the latest
APPROVED binding.  It never grants route/provider execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import re
from typing import Any, Mapping

from .dbd_reasoning_contracts import (
    CONTEXT_SCHEMA_VERSION,
    PROPOSAL_SCHEMA_VERSION,
    TunedModelBinding,
    TunedModelBindingStatus,
    admit_reasoning_contract_record,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


REGISTRY_SCHEMA_VERSION = "1.0.0"
REGISTRY_RECORD_KIND = "DBD_TUNED_MODEL_REGISTRY_RECORD"
EXECUTION_AUTHORITY_STATE = "NOT_AUTHORIZED_R3B_REQUIRED"
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
_DIGEST_REF_RE = re.compile(r"(?:registry-intake|evaluation)://sha256/[0-9a-f]{64}")
_HUMAN_REF_RE = re.compile(r"human-confirmation://[0-9A-HJKMNP-TV-Z]{26}")


class BindingLifecycleTransition(str, Enum):
    REGISTER = "REGISTER"
    EVALUATE = "EVALUATE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SUSPEND = "SUSPEND"
    REINSTATE = "REINSTATE"
    REVOKE = "REVOKE"


_TRANSITIONS: dict[tuple[TunedModelBindingStatus, TunedModelBindingStatus], BindingLifecycleTransition] = {
    (TunedModelBindingStatus.DRAFT, TunedModelBindingStatus.EVALUATED): BindingLifecycleTransition.EVALUATE,
    (TunedModelBindingStatus.EVALUATED, TunedModelBindingStatus.APPROVED): BindingLifecycleTransition.APPROVE,
    (TunedModelBindingStatus.EVALUATED, TunedModelBindingStatus.REJECTED): BindingLifecycleTransition.REJECT,
    (TunedModelBindingStatus.APPROVED, TunedModelBindingStatus.SUSPENDED): BindingLifecycleTransition.SUSPEND,
    (TunedModelBindingStatus.SUSPENDED, TunedModelBindingStatus.APPROVED): BindingLifecycleTransition.REINSTATE,
    (TunedModelBindingStatus.SUSPENDED, TunedModelBindingStatus.REVOKED): BindingLifecycleTransition.REVOKE,
}
_HUMAN_TRANSITIONS = frozenset({
    BindingLifecycleTransition.APPROVE,
    BindingLifecycleTransition.REJECT,
    BindingLifecycleTransition.SUSPEND,
    BindingLifecycleTransition.REINSTATE,
    BindingLifecycleTransition.REVOKE,
})


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise ValueError("recorded_at must be an RFC3339 UTC timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _binding_from_record(value: Mapping[str, Any]) -> TunedModelBinding:
    admitted = admit_reasoning_contract_record(value)
    binding = TunedModelBinding(
        binding_id=admitted["binding_id"],
        revision=admitted["revision"],
        status=TunedModelBindingStatus(admitted["status"]),
        base_model_ref=admitted["base_model_ref"],
        base_model_sha256=admitted["base_model_sha256"],
        adapter_ref=admitted["adapter_ref"],
        adapter_sha256=admitted["adapter_sha256"],
        training_dataset_sha256=admitted["training_dataset_sha256"],
        training_recipe_sha256=admitted["training_recipe_sha256"],
        evaluation_report_sha256=admitted["evaluation_report_sha256"],
        rights_manifest_sha256=admitted["rights_manifest_sha256"],
        supported_locales=tuple(admitted["supported_locales"]),
        approved_at=admitted["approved_at"],
        approved_by_ref=admitted["approved_by_ref"],
    )
    if binding.to_dict() != dict(value):
        raise ValueError("binding record is not exact canonical TunedModelBinding data")
    return binding


@dataclass(frozen=True, slots=True)
class DbDTunedModelRegistryRecord:
    binding: TunedModelBinding
    transition: BindingLifecycleTransition
    previous_record_sha256: str | None
    decision_evidence_ref: str
    decision_evidence_sha256: str
    recorded_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.binding, TunedModelBinding):
            raise ValueError("binding must be TunedModelBinding")
        if not isinstance(self.transition, BindingLifecycleTransition):
            raise ValueError("transition must be BindingLifecycleTransition")
        if self.previous_record_sha256 is not None:
            validate_sha256(self.previous_record_sha256, field_name="previous_record_sha256")
        validate_sha256(self.decision_evidence_sha256, field_name="decision_evidence_sha256")
        _utc(self.recorded_at)
        if self.transition in _HUMAN_TRANSITIONS:
            if not isinstance(self.decision_evidence_ref, str) or not _HUMAN_REF_RE.fullmatch(self.decision_evidence_ref):
                raise ValueError("Human lifecycle transition requires an opaque Human confirmation reference")
        else:
            if not isinstance(self.decision_evidence_ref, str) or not _DIGEST_REF_RE.fullmatch(self.decision_evidence_ref):
                raise ValueError("technical lifecycle transition requires a digest-only Evidence reference")
            expected_scheme = "registry-intake" if self.transition is BindingLifecycleTransition.REGISTER else "evaluation"
            if not self.decision_evidence_ref.startswith(expected_scheme + "://"):
                raise ValueError("technical Evidence namespace does not match the lifecycle transition")
            if self.decision_evidence_ref.rsplit("/", 1)[1] != self.decision_evidence_sha256.removeprefix("sha256:"):
                raise ValueError("technical Evidence reference and digest must match")
        if self.binding.status is TunedModelBindingStatus.APPROVED:
            approved_at = datetime.fromisoformat((self.binding.approved_at or "").replace("Z", "+00:00"))
            if approved_at > _utc(self.recorded_at):
                raise ValueError("binding approval cannot postdate its registry record")
        target_status = {
            BindingLifecycleTransition.REGISTER: TunedModelBindingStatus.DRAFT,
            BindingLifecycleTransition.EVALUATE: TunedModelBindingStatus.EVALUATED,
            BindingLifecycleTransition.APPROVE: TunedModelBindingStatus.APPROVED,
            BindingLifecycleTransition.REJECT: TunedModelBindingStatus.REJECTED,
            BindingLifecycleTransition.SUSPEND: TunedModelBindingStatus.SUSPENDED,
            BindingLifecycleTransition.REINSTATE: TunedModelBindingStatus.APPROVED,
            BindingLifecycleTransition.REVOKE: TunedModelBindingStatus.REVOKED,
        }[self.transition]
        if self.binding.status is not target_status:
            raise ValueError("transition target does not match binding status")
        if self.transition is BindingLifecycleTransition.REGISTER:
            if self.binding.revision != 1 or self.previous_record_sha256 is not None:
                raise ValueError("REGISTER must be the revision 1 root record")
            if any(value is not None for value in _lineage_values(self.binding)):
                raise ValueError("DRAFT root must not carry evaluated artifact lineage")
        elif self.binding.revision < 2 or self.previous_record_sha256 is None:
            raise ValueError("non-root transition requires a previous record and later revision")
        if self.transition is BindingLifecycleTransition.EVALUATE:
            lineage = _lineage_values(self.binding)
            if any(value is None for value in lineage):
                raise ValueError("EVALUATE requires complete artifact lineage")
            if self.decision_evidence_sha256 != self.binding.evaluation_report_sha256:
                raise ValueError("EVALUATE Evidence must match evaluation_report_sha256")

    def _body(self) -> dict[str, Any]:
        binding = self.binding.to_dict()
        return {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "record_kind": REGISTRY_RECORD_KIND,
            "binding": binding,
            "binding_id": self.binding.binding_id,
            "binding_revision": self.binding.revision,
            "binding_sha256": binding["binding_sha256"],
            "transition": self.transition.value,
            "previous_record_sha256": self.previous_record_sha256,
            "decision_evidence_ref": self.decision_evidence_ref,
            "decision_evidence_sha256": self.decision_evidence_sha256,
            "recorded_at": self.recorded_at,
            "execution_authority_state": EXECUTION_AUTHORITY_STATE,
        }

    @property
    def registry_record_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "registry_record_sha256": self.registry_record_sha256}


def admit_tuned_model_registry_record(record: Mapping[str, Any]) -> DbDTunedModelRegistryRecord:
    if not isinstance(record, Mapping):
        raise ValueError("registry record must be a mapping")
    expected = {
        "schema_version", "record_kind", "binding", "binding_id", "binding_revision", "binding_sha256",
        "transition", "previous_record_sha256", "decision_evidence_ref", "decision_evidence_sha256",
        "recorded_at", "execution_authority_state", "registry_record_sha256",
    }
    if set(record) != expected:
        raise ValueError("registry record has unknown or missing fields")
    if record.get("schema_version") != REGISTRY_SCHEMA_VERSION or record.get("record_kind") != REGISTRY_RECORD_KIND:
        raise ValueError("unsupported tuned-model registry record")
    from importlib.resources import files
    from jsonschema import Draft202012Validator

    schema = json.loads(files("ai_video_production.schema_resources").joinpath("dbd-tuned-model-registry.schema.json").read_text(encoding="utf-8"))
    if list(Draft202012Validator(schema).iter_errors(dict(record))):
        raise ValueError("registry record does not satisfy JSON Schema")
    supplied = record["registry_record_sha256"]
    validate_sha256(supplied, field_name="registry_record_sha256")
    body = {key: value for key, value in record.items() if key != "registry_record_sha256"}
    if sha256_bytes(canonical_json_bytes(body)) != supplied:
        raise ValueError("registry_record_sha256 does not match canonical content")
    if not isinstance(record["binding"], Mapping):
        raise ValueError("binding must be an object")
    binding = _binding_from_record(record["binding"])
    result = DbDTunedModelRegistryRecord(
        binding=binding,
        transition=BindingLifecycleTransition(record["transition"]),
        previous_record_sha256=record["previous_record_sha256"],
        decision_evidence_ref=record["decision_evidence_ref"],
        decision_evidence_sha256=record["decision_evidence_sha256"],
        recorded_at=record["recorded_at"],
    )
    if result.to_dict() != dict(record):
        raise ValueError("registry record is not exact canonical data")
    return result


def _lineage_values(binding: TunedModelBinding) -> tuple[str | None, ...]:
    return (
        binding.training_dataset_sha256,
        binding.training_recipe_sha256,
        binding.evaluation_report_sha256,
        binding.rights_manifest_sha256,
    )


@dataclass(frozen=True, slots=True)
class DbDTunedModelResolution:
    binding: TunedModelBinding
    registry_record_sha256: str
    execution_authority_state: str = EXECUTION_AUTHORITY_STATE

    def __post_init__(self) -> None:
        if not isinstance(self.binding, TunedModelBinding) or not self.binding.resolvable:
            raise ValueError("resolution requires an APPROVED TunedModelBinding")
        validate_sha256(self.registry_record_sha256, field_name="registry_record_sha256")
        if self.execution_authority_state != EXECUTION_AUTHORITY_STATE:
            raise ValueError("R3A resolution cannot grant execution authority")


@dataclass(frozen=True, slots=True)
class DbDTunedModelRegistry:
    records: tuple[DbDTunedModelRegistryRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple) or any(not isinstance(item, DbDTunedModelRegistryRecord) for item in self.records):
            raise ValueError("records must be a tuple of registry records")
        canonical_order = tuple(sorted(self.records, key=lambda item: (item.binding.binding_id, item.binding.revision)))
        if self.records != canonical_order:
            raise ValueError("registry records must be canonically ordered")
        seen_hashes: set[str] = set()
        seen_human_refs: set[str] = set()
        seen_human_digests: set[str] = set()
        artifact_owner: dict[tuple[str, str, str, str], str] = {}
        chains: dict[str, list[DbDTunedModelRegistryRecord]] = {}
        for record in self.records:
            admitted = admit_tuned_model_registry_record(record.to_dict())
            if admitted != record or record.registry_record_sha256 in seen_hashes:
                raise ValueError("registry contains a duplicate or non-canonical record")
            seen_hashes.add(record.registry_record_sha256)
            if record.transition in _HUMAN_TRANSITIONS:
                if record.decision_evidence_ref in seen_human_refs or record.decision_evidence_sha256 in seen_human_digests:
                    raise ValueError("Human confirmation Evidence must be one-shot across the registry")
                seen_human_refs.add(record.decision_evidence_ref)
                seen_human_digests.add(record.decision_evidence_sha256)
            chains.setdefault(record.binding.binding_id, []).append(record)
            identity = (
                record.binding.base_model_ref, record.binding.base_model_sha256,
                record.binding.adapter_ref, record.binding.adapter_sha256,
            )
            owner = artifact_owner.setdefault(identity, record.binding.binding_id)
            if owner != record.binding.binding_id:
                raise ValueError("one model/adapter identity cannot belong to multiple binding chains")
        for chain in chains.values():
            self._validate_chain(chain)

    @staticmethod
    def _validate_chain(chain: list[DbDTunedModelRegistryRecord]) -> None:
        first = chain[0]
        if first.binding.revision != 1 or first.binding.status is not TunedModelBindingStatus.DRAFT:
            raise ValueError("binding chain must start at revision 1 DRAFT")
        if first.transition is not BindingLifecycleTransition.REGISTER or first.previous_record_sha256 is not None:
            raise ValueError("first binding record must be a root REGISTER transition")
        stable = (
            first.binding.base_model_ref, first.binding.base_model_sha256,
            first.binding.adapter_ref, first.binding.adapter_sha256,
            first.binding.supported_locales,
        )
        previous = first
        evaluated_lineage: tuple[str | None, ...] | None = None
        for expected_revision, current in enumerate(chain[1:], start=2):
            binding = current.binding
            if binding.revision != expected_revision or current.previous_record_sha256 != previous.registry_record_sha256:
                raise ValueError("binding chain revision or previous checksum is not gap-free")
            if _utc(current.recorded_at) <= _utc(previous.recorded_at):
                raise ValueError("binding registry record times must increase strictly")
            if binding.binding_id != previous.binding.binding_id:
                raise ValueError("binding chain crosses binding identity")
            current_stable = (
                binding.base_model_ref, binding.base_model_sha256,
                binding.adapter_ref, binding.adapter_sha256,
                binding.supported_locales,
            )
            if current_stable != stable:
                raise ValueError("binding model, adapter or locale coordinates changed in-place")
            expected_transition = _TRANSITIONS.get((previous.binding.status, binding.status))
            if current.transition is not expected_transition:
                raise ValueError("binding lifecycle transition is not allowed")
            if binding.status is TunedModelBindingStatus.APPROVED:
                approved_at = datetime.fromisoformat((binding.approved_at or "").replace("Z", "+00:00"))
                if approved_at < _utc(previous.recorded_at):
                    raise ValueError("binding approval time cannot precede the previous lifecycle record")
            lineage = _lineage_values(binding)
            if binding.status is TunedModelBindingStatus.EVALUATED:
                if any(value is None for value in lineage):
                    raise ValueError("EVALUATED binding requires complete artifact lineage")
                evaluated_lineage = lineage
            elif previous.binding.status is not TunedModelBindingStatus.DRAFT:
                if evaluated_lineage is None:
                    evaluated_lineage = _lineage_values(previous.binding)
                if lineage != evaluated_lineage:
                    raise ValueError("evaluated artifact lineage cannot change during lifecycle transitions")
            previous = current

    def latest(self, binding_id: str) -> DbDTunedModelRegistryRecord:
        rows = tuple(record for record in self.records if record.binding.binding_id == binding_id)
        if not rows:
            raise ProductError("ERR_DBD_TUNED_BINDING_NOT_FOUND", "DbD tuned binding is not registered", ProductErrorCategory.VALIDATION)
        return rows[-1]

    def resolve(self, *, locale: str, binding_id: str | None = None,
                context_schema: str = CONTEXT_SCHEMA_VERSION,
                output_schema: str = PROPOSAL_SCHEMA_VERSION) -> DbDTunedModelResolution:
        if context_schema != CONTEXT_SCHEMA_VERSION or output_schema != PROPOSAL_SCHEMA_VERSION:
            raise ProductError("ERR_DBD_TUNED_BINDING_SCHEMA_MISMATCH", "DbD tuned binding schema is incompatible", ProductErrorCategory.VALIDATION)
        latest = {record.binding.binding_id: record for record in self.records}
        candidates = tuple(
            record for key, record in sorted(latest.items())
            if record.binding.status is TunedModelBindingStatus.APPROVED
            and locale in record.binding.supported_locales
            and (binding_id is None or key == binding_id)
        )
        if not candidates:
            raise ProductError("ERR_DBD_TUNED_BINDING_UNAVAILABLE", "No current approved DbD tuned binding is available", ProductErrorCategory.EXTERNAL_DEPENDENCY)
        if len(candidates) != 1:
            raise ProductError("ERR_DBD_TUNED_BINDING_AMBIGUOUS", "Multiple approved DbD tuned bindings require explicit selection", ProductErrorCategory.VALIDATION)
        selected = candidates[0]
        return DbDTunedModelResolution(selected.binding, selected.registry_record_sha256)


__all__ = [
    "BindingLifecycleTransition", "DbDTunedModelRegistry", "DbDTunedModelRegistryRecord",
    "DbDTunedModelResolution", "EXECUTION_AUTHORITY_STATE", "REGISTRY_RECORD_KIND",
    "REGISTRY_SCHEMA_VERSION", "admit_tuned_model_registry_record",
]
