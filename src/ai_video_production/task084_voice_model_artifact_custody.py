"""TASK-084 encrypted voice-model artifact custody pure contracts.

This module is deliberately body-free and effect-free.  It validates public
metadata, compiles fail-closed admissions, and provides sealed in-memory
fixtures for state/fault tests.  It never opens a file, encrypts model bytes,
creates an OS handle, invokes the TASK-068 backend, loads a model, or grants
training/evaluation/inference authority.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import PureWindowsPath
import re
from threading import RLock
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_dataset_revision import TrainingInputSnapshot
from .voice_training_run import (
    TrainingComputeTerminalReceipt,
    TrainingDurableJobBinding,
    TrainingRunIntent,
    TrainingRunRevision,
    TrainingRunState,
)


SCHEMA_ID = "bai.task084.voice-model-artifact-custody.v1"
SCHEMA_VERSION = 1
CANONICAL_OWNER_TASK = "TASK-084"
MAX_SECURITY_JSON_BYTES = 131_072
MAX_SECURITY_JSON_DEPTH = 20
MAX_EXPECTED_ENTRIES = 128
MAX_TOTAL_PLAIN_BYTES = 512 * 1024 * 1024 * 1024
MAX_TOTAL_CIPHER_BYTES = 520 * 1024 * 1024 * 1024
MAX_RELATIVE_FILE_DEPTH = 8
MAX_CHECKPOINT_INDEX = 2_147_483_647
MAX_CHECKPOINT_BASE_RELATIVE_FILE_DEPTH = MAX_RELATIVE_FILE_DEPTH - 3
MAX_CHECKPOINT_BASE_RELATIVE_FILE_LENGTH = 424
CHECKPOINT_MANIFEST_RELATIVE_FILE = "manifest.json.enc"
MINIMUM_CHECKPOINTS_BEFORE_TERMINAL = 1
APPROVED_AEAD_SUITES = frozenset({"AES_256_GCM", "XCHACHA20_POLY1305"})

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_RELATIVE_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_TIMESTAMP_RE = re.compile(
    r"^(?:(?:(?!0000)[0-9]{4})-"
    r"(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])|"
    r"(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)|"
    r"02-(?:0[1-9]|1[0-9]|2[0-8]))|"
    r"(?:(?!0000)(?:[0-9]{2}(?:0[48]|[2468][048]|[13579][26])|"
    r"(?:0[48]|[2468][048]|[13579][26])00))-02-29)"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?Z$"
)
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}

_PLAN_DOMAIN = b"BAI:TASK-084:DESTINATION-PLAN:V1\x00"
_INVENTORY_DOMAIN = b"BAI:TASK-084:FIXTURE-INVENTORY:V1\x00"
_CHECKPOINT_NAMESPACE_POLICY_DOMAIN = (
    b"BAI:TASK-084:CHECKPOINT-NAMESPACE-POLICY:V1\x00"
)
_CHECKPOINT_NAMESPACE_DOMAIN = b"BAI:TASK-084:CHECKPOINT-NAMESPACE:V1\x00"
_EVENT_DOMAIN = b"BAI:TASK-084:FIXTURE-CUSTODY-EVENT:V1\x00"
_FIXTURE_CHECKPOINT_RECEIPT_DOMAIN = b"BAI:TASK-084:FIXTURE-CHECKPOINT-RECEIPT:V1\x00"
_FIXTURE_TERMINAL_RECEIPT_DOMAIN = b"BAI:TASK-084:FIXTURE-TERMINAL-RECEIPT:V1\x00"
_PRODUCTION_CHECKPOINT_RECEIPT_DOMAIN = b"BAI:TASK-084:PRODUCTION-CHECKPOINT-RECEIPT:V1\x00"
_PRODUCTION_TERMINAL_RECEIPT_DOMAIN = b"BAI:TASK-084:PRODUCTION-TERMINAL-RECEIPT:V1\x00"
_FIXTURE_READBACK_DOMAIN = b"BAI:TASK-084:FIXTURE-CUSTODY-READBACK:V1\x00"
_PRODUCTION_READBACK_DOMAIN = b"BAI:TASK-084:PRODUCTION-CUSTODY-READBACK:V1\x00"
_PRODUCTION_ADMISSION_DOMAIN = b"BAI:TASK-084:PRODUCTION-CUSTODY-ADMISSION:V1\x00"
_LOAD_ADMISSION_DOMAIN = b"BAI:TASK-084:MODEL-LOAD-ADMISSION:V1\x00"
_FIXTURE_LOAD_READBACK_DOMAIN = b"BAI:TASK-084:FIXTURE-MODEL-LOAD-READBACK:V1\x00"
_FIXTURE_LOAD_HANDLE_DOMAIN = b"BAI:TASK-084:FIXTURE-MODEL-LOAD-HANDLE:V1\x00"
_FIXTURE_LOAD_COMPLETION_DOMAIN = b"BAI:TASK-084:FIXTURE-MODEL-LOAD-COMPLETION:V1\x00"
_NEGATIVE_ACK_DOMAIN = b"BAI:TASK-084:FIXTURE-DURABLE-NEGATIVE-ACK:V1\x00"
_FACTORY_KEY = object()


class ArtifactVariant(str, Enum):
    CHECKPOINT = "CHECKPOINT"
    TERMINAL = "TERMINAL"


class CustodyPhase(str, Enum):
    PREPARED = "PREPARED"
    DESTINATION_ACTIVE = "DESTINATION_ACTIVE"
    PUBLISH_STARTED = "PUBLISH_STARTED"
    CHECKPOINT_PUBLISHED = "CHECKPOINT_PUBLISHED"
    TERMINAL_SEALED = "TERMINAL_SEALED"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"
    FAILED_CLOSED = "FAILED_CLOSED"


class LeaseState(str, Enum):
    PREPARED = "PREPARED"
    ISSUED = "ISSUED"
    OPEN_STARTED = "OPEN_STARTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"
    FAILED_CLOSED = "FAILED_CLOSED"


class LoadPurpose(str, Enum):
    TRAINING_RESUME = "TRAINING_RESUME"
    HELD_OUT_EVALUATION = "HELD_OUT_EVALUATION"
    LOCAL_NARRATION_INFERENCE = "LOCAL_NARRATION_INFERENCE"


_PRODUCTION_BLOCKERS = tuple(
    sorted(
        {
            "TASK043_VOICE_MODEL_TRAINING_SOURCE_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK046_H3_V2_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK046_COMPOUND_OPERATION_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK046_OUTPUT_PRODUCER_EVENT_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK046_CUSTODY_AWARE_CONSUMER_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK083_RESERVATION_CONTRACT_NOT_AVAILABLE_CURRENT_SOURCE",
            "TASK084_WINDOWS_BACKEND_NOT_AVAILABLE",
        }
    )
)

_LOAD_BINDING_FIELDS: dict[LoadPurpose, frozenset[str]] = {
    LoadPurpose.TRAINING_RESUME: frozenset(
        {
            "checkpoint_custody_receipt_sha256",
            "job_head_sha256",
            "recovery_readback_sha256",
            "task083_reservation_receipt_sha256",
            "h3_v2_authorization_sha256",
            "resume_compound_operation_sha256",
        }
    ),
    LoadPurpose.HELD_OUT_EVALUATION: frozenset(
        {
            "terminal_custody_receipt_sha256",
            "model_artifact_binding_sha256",
            "pending_candidate_sha256",
            "evaluation_authorization_sha256",
            "evaluation_operation_sha256",
        }
    ),
    LoadPurpose.LOCAL_NARRATION_INFERENCE: frozenset(
        {
            "terminal_custody_receipt_sha256",
            "model_artifact_binding_sha256",
            "h4_v2_approval_sha256",
            "fine_tuned_model_binding_sha256",
            "task075_admission_sha256",
            "current_consent_rights_sha256",
        }
    ),
}


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return copy.deepcopy(dict(value))


def _expect_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} fields are incomplete or unknown")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    folded = value.casefold()
    if (
        folded.startswith(("file:", "http:", "https:"))
        or value.startswith(("/", "\\"))
        or "\\" in value
        or PureWindowsPath(value).drive
        or any(part == ".." for part in value.split("/"))
    ):
        raise ValueError(f"{name} must be a body-free logical identifier")
    return value


def _relative_file(value: Any, name: str = "relative_file") -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError(f"{name} is invalid")
    if value.startswith(("/", "\\")) or "\\" in value or ":" in value:
        raise ValueError(f"{name} must be a relative body-free file identity")
    parts = value.split("/")
    if len(parts) > MAX_RELATIVE_FILE_DEPTH or any(
        not part
        or part in {".", ".."}
        or part.endswith((".", " "))
        or not _RELATIVE_COMPONENT_RE.fullmatch(part)
        or part.split(".", 1)[0].upper() in _WINDOWS_RESERVED
        for part in parts
    ):
        raise ValueError(f"{name} violates the closed relative-file policy")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _nullable_sha(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _sha(value, name)


def _integer(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} exceeds {maximum}")
    return value


def _boolean(value: Any, name: str, *, exact: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    if exact is not None and value is not exact:
        raise ValueError(f"{name} must be {str(exact).lower()}")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{name} must be strict RFC3339 UTC")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be strict RFC3339 UTC") from exc
    return value


def _timestamp_value(value: str) -> datetime:
    _timestamp(value, "timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sorted_reason_codes(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("reason_codes must be a bounded list")
    for reason in value:
        _identifier(reason, "reason_code")
    if value != sorted(set(value)):
        raise ValueError("reason_codes must be sorted and unique")
    return value


def _digest(value: Mapping[str, Any], field: str, domain: bytes) -> str:
    body = copy.deepcopy(dict(value))
    body.pop(field, None)
    return sha256_bytes(domain + canonical_json_bytes(body))


def _with_digest(value: Mapping[str, Any], field: str, domain: bytes) -> dict[str, Any]:
    body = copy.deepcopy(dict(value))
    body[field] = _digest(body, field, domain)
    return body


def _verify_digest(value: Mapping[str, Any], field: str, domain: bytes) -> None:
    if _sha(value[field], field) != _digest(value, field, domain):
        raise ValueError(f"{field} mismatch")


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


def _max_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, Mapping):
        return max([depth, *(_max_depth(item, depth + 1) for item in value.values())])
    if isinstance(value, list):
        return max([depth, *(_max_depth(item, depth + 1) for item in value)])
    return depth


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _pairs_no_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class _CanonicalRecord:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str]

    def __post_init__(self) -> None:
        body = _mapping(self.data, self.RECORD_TYPE)
        validate_record(body, expected_type=self.RECORD_TYPE)
        object.__setattr__(self, "data", _freeze(body))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "_CanonicalRecord":
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class Task084OutputArtifactDestinationPlanV1(_CanonicalRecord):
    RECORD_TYPE = "Task084OutputArtifactDestinationPlanV1"


class Task084FixtureArtifactInventoryV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureArtifactInventoryV1"


class Task084FixtureCustodyEventV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureCustodyEventV1"


class Task084FixtureModelCheckpointCustodyReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureModelCheckpointCustodyReceiptV1"


class Task084FixtureModelArtifactCustodyReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureModelArtifactCustodyReceiptV1"


class Task084ModelCheckpointCustodyReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task084ModelCheckpointCustodyReceiptV1"


class Task084ModelArtifactCustodyReceiptV1(_CanonicalRecord):
    RECORD_TYPE = "Task084ModelArtifactCustodyReceiptV1"


class Task084FixtureCustodyReadbackV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureCustodyReadbackV1"


class Task084CustodyReadbackV1(_CanonicalRecord):
    RECORD_TYPE = "Task084CustodyReadbackV1"


class Task084ProductionCustodyAdmissionV1(_CanonicalRecord):
    RECORD_TYPE = "Task084ProductionCustodyAdmissionV1"


class Task084ModelLoadAdmissionV1(_CanonicalRecord):
    RECORD_TYPE = "Task084ModelLoadAdmissionV1"


class Task084FixtureModelLoadReadbackV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureModelLoadReadbackV1"


class Task084FixtureDurableNegativeAcknowledgementV1(_CanonicalRecord):
    RECORD_TYPE = "Task084FixtureDurableNegativeAcknowledgementV1"


_RECORD_CLASSES: dict[str, type[_CanonicalRecord]] = {
    cls.RECORD_TYPE: cls
    for cls in (
        Task084OutputArtifactDestinationPlanV1,
        Task084FixtureArtifactInventoryV1,
        Task084FixtureCustodyEventV1,
        Task084FixtureModelCheckpointCustodyReceiptV1,
        Task084FixtureModelArtifactCustodyReceiptV1,
        Task084ModelCheckpointCustodyReceiptV1,
        Task084ModelArtifactCustodyReceiptV1,
        Task084FixtureCustodyReadbackV1,
        Task084CustodyReadbackV1,
        Task084ProductionCustodyAdmissionV1,
        Task084ModelLoadAdmissionV1,
        Task084FixtureModelLoadReadbackV1,
        Task084FixtureDurableNegativeAcknowledgementV1,
    )
}


_PLAN_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "plan_id",
    "project_id",
    "run_intent_sha256",
    "run_revision",
    "training_run_revision_sha256",
    "training_run_revision_number",
    "training_run_state",
    "training_run_head_sha256",
    "training_input_snapshot_sha256",
    "dataset_id",
    "voice_dataset_revision_sha256",
    "job_binding_sha256",
    "job_contract_state",
    "job_id",
    "job_revision",
    "job_revision_sha256",
    "task043_job_readback_sha256",
    "task043_job_head_sha256",
    "task083_reservation_plan_sha256",
    "training_mode",
    "recipe_revision_sha256",
    "engine_admission_sha256",
    "engine_id",
    "engine_commit_sha256",
    "base_model_id",
    "base_model_revision",
    "base_model_sha256",
    "runtime_revision",
    "runtime_sha256",
    "code_revision",
    "code_sha256",
    "config_sha256",
    "current_consent_rights_license_sha256",
    "output_destination_binding_sha256",
    "destination_coordinate",
    "destination_coordinate_sha256",
    "custody_policy_sha256",
    "encryption_policy_sha256",
    "aead_suite",
    "cipher_backend_revision_sha256",
    "principal_scope_sha256",
    "key_scope_sha256",
    "dacl_policy_sha256",
    "checkpoint_expected_entries",
    "checkpoint_entry_allowlist_sha256",
    "checkpoint_namespace_policy_sha256",
    "terminal_expected_entries",
    "terminal_entry_allowlist_sha256",
    "max_file_count",
    "max_total_plain_bytes",
    "max_total_cipher_bytes",
    "max_relative_file_depth",
    "compiled_at",
    "task043_job_source_state",
    "task083_contract_state",
    "h3_v2_state",
    "compound_operation_state",
    "producer_event_state",
    "windows_backend_state",
    "fixture_only",
    "authority_created",
    "destination_activated",
    "write_lease_created",
    "load_lease_created",
    "model_artifact_binding_created",
    "candidate_registered",
    "resource_effect_count",
    "production_eligible",
    "plan_sha256",
}


def _validate_discriminator(value: Mapping[str, Any], record_type: str) -> None:
    if (
        value.get("record_type") != record_type
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("canonical_owner_task") != CANONICAL_OWNER_TASK
    ):
        raise ValueError(f"{record_type} discriminator mismatch")


def _checkpoint_base_relative_file(value: Any) -> str:
    parsed = _relative_file(value)
    if (
        len(parsed) > MAX_CHECKPOINT_BASE_RELATIVE_FILE_LENGTH
        or len(parsed.split("/")) > MAX_CHECKPOINT_BASE_RELATIVE_FILE_DEPTH
    ):
        raise ValueError(
            "checkpoint relative_file exceeds its closed namespace path budget"
        )
    if parsed.casefold() == CHECKPOINT_MANIFEST_RELATIVE_FILE.casefold():
        raise ValueError("checkpoint relative_file collides with reserved manifest")
    return parsed


def _validate_expected_entries(
    value: Any, *, checkpoint_base: bool = False
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_EXPECTED_ENTRIES:
        raise ValueError("expected_entries must be a bounded non-empty list")
    result: list[dict[str, Any]] = []
    for item in value:
        _expect_keys(
            item,
            {"entry_id", "role", "index", "relative_file"},
            "expected_entry",
        )
        _identifier(item["entry_id"], "entry_id")
        if item["role"] not in {
            "MODEL_WEIGHT",
            "OPTIMIZER_STATE",
            "TRAINING_STATE",
            "CONFIG",
            "TOKENIZER",
            "CODEC",
            "VOCODER",
        }:
            raise ValueError("expected entry role is invalid")
        _integer(item["index"], "index", minimum=0)
        if checkpoint_base:
            _checkpoint_base_relative_file(item["relative_file"])
        else:
            _relative_file(item["relative_file"])
        result.append(copy.deepcopy(dict(item)))
    if result != sorted(result, key=lambda item: (item["index"], item["entry_id"])):
        raise ValueError("expected_entries must be ordered by index and entry_id")
    if len({item["entry_id"] for item in result}) != len(result):
        raise ValueError("expected entry ids must be unique")
    if len({item["relative_file"].casefold() for item in result}) != len(result):
        raise ValueError("expected entry relative files must be case-insensitively unique")
    if [item["index"] for item in result] != list(range(len(result))):
        raise ValueError("expected entry indices must be contiguous")
    return result


def _entry_allowlist_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(
        b"BAI:TASK-084:EXPECTED-ENTRY-ALLOWLIST:V1\x00"
        + canonical_json_bytes(list(entries))
    )


def _checkpoint_namespace_policy_sha256() -> str:
    return sha256_bytes(
        _CHECKPOINT_NAMESPACE_POLICY_DOMAIN
        + canonical_json_bytes(
            {
                "layout": (
                    "checkpoints/{checkpoint_index}/"
                    "{producer_event_sha256_hex}/{expected_relative_file}"
                ),
                "manifest_layout": (
                    "checkpoints/{checkpoint_index}/"
                    "{producer_event_sha256_hex}/manifest.json.enc"
                ),
                "index_base": 1,
                "max_checkpoint_index": MAX_CHECKPOINT_INDEX,
                "max_checkpoint_base_relative_file_depth": (
                    MAX_CHECKPOINT_BASE_RELATIVE_FILE_DEPTH
                ),
                "max_checkpoint_base_relative_file_length": (
                    MAX_CHECKPOINT_BASE_RELATIVE_FILE_LENGTH
                ),
                "reserved_manifest_relative_file": CHECKPOINT_MANIFEST_RELATIVE_FILE,
                "case_insensitive_no_reuse": True,
            }
        )
    )


def _checkpoint_namespace_sha256(
    plan_sha256: str, checkpoint_index: int, producer_event_sha256: str
) -> str:
    parsed_checkpoint_index = _integer(
        checkpoint_index,
        "checkpoint_index",
        minimum=1,
        maximum=MAX_CHECKPOINT_INDEX,
    )
    return sha256_bytes(
        _CHECKPOINT_NAMESPACE_DOMAIN
        + canonical_json_bytes(
            {
                "plan_sha256": plan_sha256,
                "checkpoint_namespace_policy_sha256": (
                    _checkpoint_namespace_policy_sha256()
                ),
                "checkpoint_index": parsed_checkpoint_index,
                "producer_event_sha256": _sha(
                    producer_event_sha256, "producer_event_sha256"
                ),
            }
        )
    )


def _checkpoint_scoped_entries(
    expected_entries: Sequence[Mapping[str, Any]],
    *,
    checkpoint_index: int,
    producer_event_sha256: str,
) -> list[dict[str, Any]]:
    parsed_checkpoint_index = _integer(
        checkpoint_index,
        "checkpoint_index",
        minimum=1,
        maximum=MAX_CHECKPOINT_INDEX,
    )
    producer_event_sha256_hex = _sha(
        producer_event_sha256, "producer_event_sha256"
    ).removeprefix("sha256:")
    prefix = f"checkpoints/{parsed_checkpoint_index}/{producer_event_sha256_hex}"
    return [
        {
            **copy.deepcopy(dict(item)),
            "relative_file": f"{prefix}/{item['relative_file']}",
        }
        for item in expected_entries
    ]


def _validate_plan(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _PLAN_FIELDS, "Task084OutputArtifactDestinationPlanV1")
    _validate_discriminator(value, "Task084OutputArtifactDestinationPlanV1")
    for field in (
        "plan_id",
        "project_id",
        "dataset_id",
        "training_mode",
        "engine_id",
        "base_model_id",
        "base_model_revision",
        "runtime_revision",
        "code_revision",
        "destination_coordinate",
        "aead_suite",
    ):
        _identifier(value[field], field)
    for field in (
        "run_intent_sha256",
        "training_run_revision_sha256",
        "training_run_head_sha256",
        "training_input_snapshot_sha256",
        "voice_dataset_revision_sha256",
        "job_binding_sha256",
        "task043_job_readback_sha256",
        "task043_job_head_sha256",
        "task083_reservation_plan_sha256",
        "recipe_revision_sha256",
        "engine_admission_sha256",
        "engine_commit_sha256",
        "base_model_sha256",
        "runtime_sha256",
        "code_sha256",
        "config_sha256",
        "current_consent_rights_license_sha256",
        "output_destination_binding_sha256",
        "destination_coordinate_sha256",
        "custody_policy_sha256",
        "encryption_policy_sha256",
        "cipher_backend_revision_sha256",
        "principal_scope_sha256",
        "key_scope_sha256",
        "dacl_policy_sha256",
        "checkpoint_entry_allowlist_sha256",
        "checkpoint_namespace_policy_sha256",
        "terminal_entry_allowlist_sha256",
    ):
        _sha(value[field], field)
    _integer(value["run_revision"], "run_revision", minimum=1)
    _integer(value["training_run_revision_number"], "training_run_revision_number", minimum=1)
    TrainingRunState(value["training_run_state"])
    if value["training_run_head_sha256"] != value["training_run_revision_sha256"]:
        raise ValueError("training run head must equal the bound revision")
    if value["job_contract_state"] not in {
        "BOUND_VERIFIED",
        "CANONICAL_REF_NOT_PROVIDED",
    }:
        raise ValueError("job_contract_state is invalid")
    if value["job_contract_state"] == "BOUND_VERIFIED":
        _identifier(value["job_id"], "job_id")
        _integer(value["job_revision"], "job_revision", minimum=1)
        _sha(value["job_revision_sha256"], "job_revision_sha256")
    elif any(
        value[field] is not None
        for field in ("job_id", "job_revision", "job_revision_sha256")
    ):
        raise ValueError("unresolved Job source must not invent Job identity")
    checkpoint_entries = _validate_expected_entries(
        value["checkpoint_expected_entries"], checkpoint_base=True
    )
    terminal_entries = _validate_expected_entries(value["terminal_expected_entries"])
    if value["checkpoint_entry_allowlist_sha256"] != _entry_allowlist_sha256(
        checkpoint_entries
    ):
        raise ValueError("checkpoint_entry_allowlist_sha256 mismatch")
    if value["checkpoint_namespace_policy_sha256"] != (
        _checkpoint_namespace_policy_sha256()
    ):
        raise ValueError("checkpoint_namespace_policy_sha256 mismatch")
    if value["terminal_entry_allowlist_sha256"] != _entry_allowlist_sha256(
        terminal_entries
    ):
        raise ValueError("terminal_entry_allowlist_sha256 mismatch")
    file_count = _integer(
        value["max_file_count"], "max_file_count", minimum=1, maximum=MAX_EXPECTED_ENTRIES
    )
    if file_count < max(len(checkpoint_entries), len(terminal_entries)):
        raise ValueError("max_file_count is below the expected allowlist")
    _integer(
        value["max_total_plain_bytes"],
        "max_total_plain_bytes",
        minimum=1,
        maximum=MAX_TOTAL_PLAIN_BYTES,
    )
    _integer(
        value["max_total_cipher_bytes"],
        "max_total_cipher_bytes",
        minimum=value["max_total_plain_bytes"],
        maximum=MAX_TOTAL_CIPHER_BYTES,
    )
    if (
        _integer(
            value["max_relative_file_depth"],
            "max_relative_file_depth",
            minimum=1,
            maximum=MAX_RELATIVE_FILE_DEPTH,
        )
        != MAX_RELATIVE_FILE_DEPTH
    ):
        raise ValueError("max_relative_file_depth must use the closed v1 limit")
    _timestamp(value["compiled_at"], "compiled_at")
    if value["aead_suite"] not in APPROVED_AEAD_SUITES:
        raise ValueError("aead_suite is outside the closed v1 allowlist")
    fixed_states = {
        "task043_job_source_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "task083_contract_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "h3_v2_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "compound_operation_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "producer_event_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "windows_backend_state": "NOT_AVAILABLE_CURRENT_SOURCE",
    }
    for field, expected in fixed_states.items():
        if value[field] != expected:
            raise ValueError(f"{field} must remain {expected}")
    for field in (
        "fixture_only",
        "authority_created",
        "destination_activated",
        "write_lease_created",
        "load_lease_created",
        "model_artifact_binding_created",
        "candidate_registered",
        "production_eligible",
    ):
        _boolean(value[field], field, exact=field == "fixture_only")
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("pure destination plan must remain effect-0")
    _verify_digest(value, "plan_sha256", _PLAN_DOMAIN)


_FILE_OBSERVATION_FIELDS = {
    "entry_id",
    "role",
    "index",
    "relative_file",
    "plain_byte_count",
    "plain_sha256",
    "cipher_byte_count",
    "cipher_sha256",
    "nonce_sha256",
    "aead_authentication_evidence_sha256",
    "envelope_evidence_sha256",
    "opened_physical_identity_sha256",
    "ancestor_identity_sha256",
    "regular_file",
    "nlink",
    "reparse_point",
    "opened_identity_pinned",
    "file_flush_evidence_sha256",
    "directory_flush_evidence_sha256",
    "pinned_readback_sha256",
}


def _validate_file_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    _expect_keys(value, _FILE_OBSERVATION_FIELDS, "fixture artifact file observation")
    _identifier(value["entry_id"], "entry_id")
    if value["role"] not in {
        "MODEL_WEIGHT",
        "OPTIMIZER_STATE",
        "TRAINING_STATE",
        "CONFIG",
        "TOKENIZER",
        "CODEC",
        "VOCODER",
    }:
        raise ValueError("artifact file role is invalid")
    _integer(value["index"], "index", minimum=0)
    _relative_file(value["relative_file"])
    plain = _integer(value["plain_byte_count"], "plain_byte_count", minimum=1)
    cipher = _integer(value["cipher_byte_count"], "cipher_byte_count", minimum=1)
    if cipher < plain:
        raise ValueError("cipher_byte_count cannot be below plain_byte_count")
    for field in (
        "plain_sha256",
        "cipher_sha256",
        "nonce_sha256",
        "aead_authentication_evidence_sha256",
        "envelope_evidence_sha256",
        "opened_physical_identity_sha256",
        "ancestor_identity_sha256",
        "file_flush_evidence_sha256",
        "directory_flush_evidence_sha256",
        "pinned_readback_sha256",
    ):
        _sha(value[field], field)
    _boolean(value["regular_file"], "regular_file", exact=True)
    if _integer(value["nlink"], "nlink", minimum=0) != 1:
        raise ValueError("artifact files require nlink=1")
    _boolean(value["reparse_point"], "reparse_point", exact=False)
    _boolean(value["opened_identity_pinned"], "opened_identity_pinned", exact=True)
    return copy.deepcopy(dict(value))


_INVENTORY_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "inventory_id",
    "plan_sha256",
    "producer_event_sha256",
    "artifact_variant",
    "checkpoint_index",
    "checkpoint_namespace_sha256",
    "destination_root_identity_sha256",
    "destination_ancestor_identity_sha256",
    "destination_target_identity_sha256",
    "destination_pinned_readback_sha256",
    "entries",
    "entry_count",
    "total_plain_bytes",
    "total_cipher_bytes",
    "manifest_relative_file",
    "manifest_sha256",
    "manifest_nonce_sha256",
    "manifest_authentication_evidence_sha256",
    "manifest_envelope_evidence_sha256",
    "manifest_confidentiality",
    "manifest_opened_physical_identity_sha256",
    "manifest_ancestor_identity_sha256",
    "manifest_regular_file",
    "manifest_nlink",
    "manifest_reparse_point",
    "manifest_opened_identity_pinned",
    "manifest_file_flush_evidence_sha256",
    "manifest_directory_flush_evidence_sha256",
    "manifest_pinned_readback_sha256",
    "opened_physical_identity_set_sha256",
    "unexpected_files_present",
    "fixture_only",
    "authority_created",
    "resource_effect_count",
    "inventory_sha256",
}


def _physical_identity_set_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    projection = [
        {
            "entry_id": item["entry_id"],
            "relative_file": item["relative_file"],
            "opened_physical_identity_sha256": item["opened_physical_identity_sha256"],
            "ancestor_identity_sha256": item["ancestor_identity_sha256"],
        }
        for item in entries
    ]
    return sha256_bytes(
        b"BAI:TASK-084:OPENED-PHYSICAL-IDENTITY-SET:V1\x00"
        + canonical_json_bytes(projection)
    )


def _validate_inventory(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _INVENTORY_FIELDS, "Task084FixtureArtifactInventoryV1")
    _validate_discriminator(value, "Task084FixtureArtifactInventoryV1")
    _identifier(value["inventory_id"], "inventory_id")
    _sha(value["plan_sha256"], "plan_sha256")
    _sha(value["producer_event_sha256"], "producer_event_sha256")
    variant = ArtifactVariant(value["artifact_variant"])
    if variant is ArtifactVariant.CHECKPOINT:
        _integer(
            value["checkpoint_index"],
            "checkpoint_index",
            minimum=1,
            maximum=MAX_CHECKPOINT_INDEX,
        )
        _sha(value["checkpoint_namespace_sha256"], "checkpoint_namespace_sha256")
    elif (
        value["checkpoint_index"] is not None
        or value["checkpoint_namespace_sha256"] is not None
    ):
        raise ValueError("terminal inventory forbids checkpoint namespace")
    for field in (
        "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256",
        "destination_pinned_readback_sha256",
    ):
        _sha(value[field], field)
    if not isinstance(value["entries"], list) or not value["entries"]:
        raise ValueError("inventory entries must be non-empty")
    entries = [_validate_file_observation(item) for item in value["entries"]]
    if entries != sorted(entries, key=lambda item: (item["index"], item["entry_id"])):
        raise ValueError("inventory entries must be ordered")
    if len(entries) != _integer(value["entry_count"], "entry_count", minimum=1):
        raise ValueError("inventory entry_count mismatch")
    if len({item["entry_id"] for item in entries}) != len(entries):
        raise ValueError("inventory entry_id collision")
    relative_keys = [item["relative_file"].casefold() for item in entries]
    if len(set(relative_keys)) != len(relative_keys):
        raise ValueError("inventory relative-file case collision")
    physical_ids = [item["opened_physical_identity_sha256"] for item in entries]
    if len(set(physical_ids)) != len(physical_ids):
        raise ValueError("two entries cannot share one physical identity")
    if any(
        item["ancestor_identity_sha256"] != value["destination_target_identity_sha256"]
        for item in entries
    ):
        raise ValueError("artifact entry ancestor is outside the pinned destination target")
    if sum(item["plain_byte_count"] for item in entries) != _integer(
        value["total_plain_bytes"], "total_plain_bytes", minimum=1
    ):
        raise ValueError("inventory total_plain_bytes mismatch")
    if sum(item["cipher_byte_count"] for item in entries) != _integer(
        value["total_cipher_bytes"], "total_cipher_bytes", minimum=1
    ):
        raise ValueError("inventory total_cipher_bytes mismatch")
    manifest = _relative_file(value["manifest_relative_file"], "manifest_relative_file")
    if manifest.casefold() in relative_keys:
        raise ValueError("manifest path must be distinct from artifact entries")
    for field in (
        "manifest_sha256",
        "manifest_nonce_sha256",
        "manifest_authentication_evidence_sha256",
        "manifest_envelope_evidence_sha256",
        "manifest_opened_physical_identity_sha256",
        "manifest_ancestor_identity_sha256",
        "manifest_file_flush_evidence_sha256",
        "manifest_directory_flush_evidence_sha256",
        "manifest_pinned_readback_sha256",
    ):
        _sha(value[field], field)
    nonce_digests = [item["nonce_sha256"] for item in entries]
    nonce_digests.append(value["manifest_nonce_sha256"])
    if len(set(nonce_digests)) != len(nonce_digests):
        raise ValueError("artifact and manifest AEAD nonces must be unique")
    if value["manifest_opened_physical_identity_sha256"] in physical_ids:
        raise ValueError("manifest must have a distinct physical identity")
    if value["manifest_ancestor_identity_sha256"] != value["destination_target_identity_sha256"]:
        raise ValueError("manifest ancestor is outside the pinned destination target")
    _boolean(value["manifest_regular_file"], "manifest_regular_file", exact=True)
    if _integer(value["manifest_nlink"], "manifest_nlink", minimum=0) != 1:
        raise ValueError("manifest requires nlink=1")
    _boolean(value["manifest_reparse_point"], "manifest_reparse_point", exact=False)
    _boolean(
        value["manifest_opened_identity_pinned"],
        "manifest_opened_identity_pinned",
        exact=True,
    )
    if value["manifest_confidentiality"] not in {
        "ENCRYPTED_AUTHENTICATED",
        "PUBLIC_SAFE_BODY_FREE_AUTHENTICATED",
    }:
        raise ValueError("manifest_confidentiality is invalid")
    if value["opened_physical_identity_set_sha256"] != _physical_identity_set_sha256(entries):
        raise ValueError("opened physical identity set mismatch")
    _boolean(value["unexpected_files_present"], "unexpected_files_present", exact=False)
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    _boolean(value["authority_created"], "authority_created", exact=False)
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("fixture inventory must remain effect-0")
    _verify_digest(value, "inventory_sha256", _INVENTORY_DOMAIN)


_EVENT_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "event_id",
    "plan_sha256",
    "destination_root_identity_sha256",
    "destination_ancestor_identity_sha256",
    "destination_target_identity_sha256",
    "destination_pinned_readback_sha256",
    "event_revision",
    "predecessor_event_sha256",
    "event_kind",
    "phase",
    "request_sha256",
    "producer_event_sha256",
    "artifact_variant",
    "checkpoint_index",
    "failed_lease_id",
    "negative_acknowledgement_sha256",
    "event_at",
    "fixture_only",
    "authority_created",
    "private_handle_returned",
    "resource_effect_count",
    "event_sha256",
}


_EVENT_KIND_PHASE = {
    "DESTINATION_ACTIVATED": CustodyPhase.DESTINATION_ACTIVE,
    "CHECKPOINT_PUBLISH_STARTED": CustodyPhase.PUBLISH_STARTED,
    "TERMINAL_PUBLISH_STARTED": CustodyPhase.PUBLISH_STARTED,
    "CHECKPOINT_PUBLISHED": CustodyPhase.CHECKPOINT_PUBLISHED,
    "TERMINAL_SEALED": CustodyPhase.TERMINAL_SEALED,
    "PUBLISH_COMPLETION_UNKNOWN": CustodyPhase.COMPLETION_UNKNOWN,
    "FAILED_CLOSED": CustodyPhase.FAILED_CLOSED,
}


def _validate_event(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _EVENT_FIELDS, "Task084FixtureCustodyEventV1")
    _validate_discriminator(value, "Task084FixtureCustodyEventV1")
    _identifier(value["event_id"], "event_id")
    for field in (
        "plan_sha256",
        "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256",
        "destination_pinned_readback_sha256",
        "predecessor_event_sha256",
        "request_sha256",
    ):
        _sha(value[field], field)
    revision = _integer(value["event_revision"], "event_revision", minimum=1)
    if value["event_kind"] not in _EVENT_KIND_PHASE:
        raise ValueError("event_kind is invalid")
    phase = CustodyPhase(value["phase"])
    if _EVENT_KIND_PHASE[value["event_kind"]] is not phase:
        raise ValueError("event_kind/phase mismatch")
    publish_event = value["event_kind"] != "DESTINATION_ACTIVATED"
    if publish_event:
        _sha(value["producer_event_sha256"], "producer_event_sha256")
        variant = ArtifactVariant(value["artifact_variant"])
        if variant is ArtifactVariant.CHECKPOINT:
            _integer(
                value["checkpoint_index"],
                "checkpoint_index",
                minimum=1,
                maximum=MAX_CHECKPOINT_INDEX,
            )
        elif value["checkpoint_index"] is not None:
            raise ValueError("terminal event forbids checkpoint_index")
    elif any(
        value[field] is not None
        for field in ("producer_event_sha256", "artifact_variant", "checkpoint_index")
    ):
        raise ValueError("non-publish event has publish-only fields")
    if value["event_kind"] == "FAILED_CLOSED":
        _identifier(value["failed_lease_id"], "failed_lease_id")
        _sha(value["negative_acknowledgement_sha256"], "negative_acknowledgement_sha256")
    elif any(
        value[field] is not None
        for field in ("failed_lease_id", "negative_acknowledgement_sha256")
    ):
        raise ValueError("non-failure event has failure-only fields")
    _timestamp(value["event_at"], "event_at")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    _boolean(value["authority_created"], "authority_created", exact=False)
    _boolean(value["private_handle_returned"], "private_handle_returned", exact=False)
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("fixture event must remain effect-0")
    if revision == 1 and value["event_kind"] != "DESTINATION_ACTIVATED":
        raise ValueError("first event must activate the destination")
    _verify_digest(value, "event_sha256", _EVENT_DOMAIN)


_RECEIPT_COMMON_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "receipt_role",
    "receipt_id",
    "plan_sha256",
    "project_id",
    "run_intent_sha256",
    "training_run_revision_sha256",
    "training_run_head_sha256",
    "job_binding_sha256",
    "task043_job_readback_sha256",
    "task043_job_head_sha256",
    "training_input_snapshot_sha256",
    "recipe_revision_sha256",
    "engine_admission_sha256",
    "base_model_sha256",
    "runtime_sha256",
    "code_sha256",
    "config_sha256",
    "current_consent_rights_license_sha256",
    "task083_reservation_plan_sha256",
    "task083_reservation_receipt_sha256",
    "destination_coordinate_sha256",
    "destination_root_identity_sha256",
    "destination_ancestor_identity_sha256",
    "destination_target_identity_sha256",
    "destination_pinned_readback_sha256",
    "custody_policy_sha256",
    "encryption_policy_sha256",
    "cipher_backend_revision_sha256",
    "principal_scope_sha256",
    "key_scope_sha256",
    "dacl_policy_sha256",
    "checkpoint_namespace_policy_sha256",
    "checkpoint_namespace_sha256",
    "producer_event_sha256",
    "event_revision",
    "predecessor_event_sha256",
    "event_sha256",
    "inventory_sha256",
    "manifest_sha256",
    "manifest_nonce_sha256",
    "manifest_authentication_evidence_sha256",
    "manifest_envelope_evidence_sha256",
    "manifest_opened_physical_identity_sha256",
    "manifest_ancestor_identity_sha256",
    "manifest_file_flush_evidence_sha256",
    "manifest_directory_flush_evidence_sha256",
    "manifest_pinned_readback_sha256",
    "opened_physical_identity_set_sha256",
    "artifact_variant",
    "checkpoint_index",
    "training_step",
    "progress_ppm",
    "checkpoint_event_predecessor_sha256",
    "task046_checkpoint_binding_sha256",
    "task046_terminal_receipt_sha256",
    "last_checkpoint_receipt_sha256",
    "checkpoint_count",
    "sealed_at",
    "fixture_only",
    "authority_created",
    "native_backend_invoked",
    "artifact_body_persisted",
    "private_handle_returned",
    "model_artifact_binding_created",
    "candidate_registered",
    "model_use_authorized",
    "production_use_authorized",
    "resource_effect_count",
    "receipt_sha256",
}


def _receipt_domain(record_type: str) -> bytes:
    return {
        "Task084FixtureModelCheckpointCustodyReceiptV1": _FIXTURE_CHECKPOINT_RECEIPT_DOMAIN,
        "Task084FixtureModelArtifactCustodyReceiptV1": _FIXTURE_TERMINAL_RECEIPT_DOMAIN,
        "Task084ModelCheckpointCustodyReceiptV1": _PRODUCTION_CHECKPOINT_RECEIPT_DOMAIN,
        "Task084ModelArtifactCustodyReceiptV1": _PRODUCTION_TERMINAL_RECEIPT_DOMAIN,
    }[record_type]


def _validate_receipt(value: Mapping[str, Any], record_type: str) -> None:
    _expect_keys(value, _RECEIPT_COMMON_FIELDS, record_type)
    _validate_discriminator(value, record_type)
    fixture = record_type.startswith("Task084Fixture")
    checkpoint = "Checkpoint" in record_type
    role = "MODEL_CHECKPOINT_CUSTODY" if checkpoint else "MODEL_ARTIFACT_CUSTODY"
    variant = ArtifactVariant.CHECKPOINT if checkpoint else ArtifactVariant.TERMINAL
    if value["receipt_role"] != role or value["artifact_variant"] != variant.value:
        raise ValueError("receipt discriminator/variant mismatch")
    for field in ("receipt_id", "project_id"):
        _identifier(value[field], field)
    for field in (
        "plan_sha256",
        "run_intent_sha256",
        "training_run_revision_sha256",
        "training_run_head_sha256",
        "job_binding_sha256",
        "task043_job_readback_sha256",
        "task043_job_head_sha256",
        "training_input_snapshot_sha256",
        "recipe_revision_sha256",
        "engine_admission_sha256",
        "base_model_sha256",
        "runtime_sha256",
        "code_sha256",
        "config_sha256",
        "current_consent_rights_license_sha256",
        "task083_reservation_plan_sha256",
        "task083_reservation_receipt_sha256",
        "destination_coordinate_sha256",
        "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256",
        "destination_pinned_readback_sha256",
        "custody_policy_sha256",
        "encryption_policy_sha256",
        "cipher_backend_revision_sha256",
        "principal_scope_sha256",
        "key_scope_sha256",
        "dacl_policy_sha256",
        "checkpoint_namespace_policy_sha256",
        "producer_event_sha256",
        "predecessor_event_sha256",
        "event_sha256",
        "inventory_sha256",
        "manifest_sha256",
        "manifest_nonce_sha256",
        "manifest_authentication_evidence_sha256",
        "manifest_envelope_evidence_sha256",
        "manifest_opened_physical_identity_sha256",
        "manifest_ancestor_identity_sha256",
        "manifest_file_flush_evidence_sha256",
        "manifest_directory_flush_evidence_sha256",
        "manifest_pinned_readback_sha256",
        "opened_physical_identity_set_sha256",
        "task046_checkpoint_binding_sha256",
    ):
        _sha(value[field], field)
    _integer(value["event_revision"], "event_revision", minimum=1)
    checkpoint_count = _integer(value["checkpoint_count"], "checkpoint_count", minimum=0)
    if value["checkpoint_namespace_policy_sha256"] != (
        _checkpoint_namespace_policy_sha256()
    ):
        raise ValueError("receipt checkpoint namespace policy mismatch")
    if checkpoint:
        checkpoint_index = _integer(
            value["checkpoint_index"],
            "checkpoint_index",
            minimum=1,
            maximum=MAX_CHECKPOINT_INDEX,
        )
        _sha(value["checkpoint_namespace_sha256"], "checkpoint_namespace_sha256")
        if value["checkpoint_namespace_sha256"] != _checkpoint_namespace_sha256(
            value["plan_sha256"], checkpoint_index, value["producer_event_sha256"]
        ):
            raise ValueError("checkpoint receipt namespace mismatch")
        if checkpoint_index != checkpoint_count:
            raise ValueError("checkpoint index/count mismatch")
        _integer(value["training_step"], "training_step", minimum=1)
        _integer(value["progress_ppm"], "progress_ppm", minimum=0, maximum=1_000_000)
        _sha(value["checkpoint_event_predecessor_sha256"], "checkpoint_event_predecessor_sha256")
        if value["task046_terminal_receipt_sha256"] is not None:
            raise ValueError("checkpoint receipt forbids terminal receipt")
        _nullable_sha(value["last_checkpoint_receipt_sha256"], "last_checkpoint_receipt_sha256")
    else:
        if checkpoint_count < MINIMUM_CHECKPOINTS_BEFORE_TERMINAL:
            raise ValueError("terminal custody requires at least one checkpoint")
        if any(
            value[field] is not None
            for field in (
                "checkpoint_index",
                "training_step",
                "progress_ppm",
                "checkpoint_event_predecessor_sha256",
            )
        ):
            raise ValueError("terminal receipt forbids checkpoint-only fields")
        _sha(value["task046_terminal_receipt_sha256"], "task046_terminal_receipt_sha256")
        _sha(value["last_checkpoint_receipt_sha256"], "last_checkpoint_receipt_sha256")
        if value["checkpoint_namespace_sha256"] is not None:
            raise ValueError("terminal receipt forbids checkpoint namespace")
    _timestamp(value["sealed_at"], "sealed_at")
    _boolean(value["fixture_only"], "fixture_only", exact=fixture)
    _boolean(value["authority_created"], "authority_created", exact=False)
    _boolean(value["native_backend_invoked"], "native_backend_invoked", exact=not fixture)
    _boolean(value["artifact_body_persisted"], "artifact_body_persisted", exact=not fixture)
    _boolean(value["private_handle_returned"], "private_handle_returned", exact=False)
    for field in (
        "model_artifact_binding_created",
        "candidate_registered",
        "model_use_authorized",
        "production_use_authorized",
    ):
        _boolean(value[field], field, exact=False)
    effects = _integer(value["resource_effect_count"], "resource_effect_count")
    if fixture and effects != 0:
        raise ValueError("fixture receipt must remain effect-0")
    if not fixture and effects < 1:
        raise ValueError("production receipt must attest an observed backend effect")
    _verify_digest(value, "receipt_sha256", _receipt_domain(record_type))


_READBACK_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "plan_sha256",
    "destination_root_identity_sha256",
    "destination_ancestor_identity_sha256",
    "destination_target_identity_sha256",
    "destination_pinned_readback_sha256",
    "phase",
    "event_count",
    "head_revision",
    "head_event_sha256",
    "checkpoint_count",
    "last_checkpoint_receipt_sha256",
    "terminal_receipt_sha256",
    "current_inventory_sha256",
    "current_manifest_sha256",
    "current_manifest_opened_physical_identity_sha256",
    "current_manifest_ancestor_identity_sha256",
    "current_manifest_file_flush_evidence_sha256",
    "current_manifest_directory_flush_evidence_sha256",
    "current_manifest_pinned_readback_sha256",
    "current_opened_physical_identity_set_sha256",
    "current_inventory_observed_at",
    "active_lease_state",
    "read_back_at",
    "fixture_only",
    "authority_created",
    "native_backend_observed",
    "private_handle_returned",
    "model_artifact_binding_created",
    "candidate_registered",
    "resource_effect_count",
    "readback_sha256",
}

_CURRENT_INVENTORY_READBACK_SHA_FIELDS = (
    "current_inventory_sha256",
    "current_manifest_sha256",
    "current_manifest_opened_physical_identity_sha256",
    "current_manifest_ancestor_identity_sha256",
    "current_manifest_file_flush_evidence_sha256",
    "current_manifest_directory_flush_evidence_sha256",
    "current_manifest_pinned_readback_sha256",
    "current_opened_physical_identity_set_sha256",
)

_CURRENT_INVENTORY_TO_RECEIPT = {
    "current_inventory_sha256": "inventory_sha256",
    "current_manifest_sha256": "manifest_sha256",
    "current_manifest_opened_physical_identity_sha256": (
        "manifest_opened_physical_identity_sha256"
    ),
    "current_manifest_ancestor_identity_sha256": "manifest_ancestor_identity_sha256",
    "current_manifest_file_flush_evidence_sha256": (
        "manifest_file_flush_evidence_sha256"
    ),
    "current_manifest_directory_flush_evidence_sha256": (
        "manifest_directory_flush_evidence_sha256"
    ),
    "current_manifest_pinned_readback_sha256": "manifest_pinned_readback_sha256",
    "current_opened_physical_identity_set_sha256": (
        "opened_physical_identity_set_sha256"
    ),
}


def _empty_current_inventory_readback() -> dict[str, Any]:
    return {
        **{field: None for field in _CURRENT_INVENTORY_READBACK_SHA_FIELDS},
        "current_inventory_observed_at": None,
    }


def _current_inventory_readback(
    inventory: Mapping[str, Any], *, observed_at: str
) -> dict[str, Any]:
    return {
        field: inventory[receipt_field]
        for field, receipt_field in _CURRENT_INVENTORY_TO_RECEIPT.items()
    } | {"current_inventory_observed_at": _timestamp(observed_at, "observed_at")}


def _validate_readback(value: Mapping[str, Any], record_type: str) -> None:
    _expect_keys(value, _READBACK_FIELDS, record_type)
    _validate_discriminator(value, record_type)
    fixture = record_type.startswith("Task084Fixture")
    _sha(value["plan_sha256"], "plan_sha256")
    phase = CustodyPhase(value["phase"])
    destination_fields = (
        "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256",
        "destination_pinned_readback_sha256",
    )
    if phase is CustodyPhase.PREPARED:
        if any(value[field] is not None for field in destination_fields):
            raise ValueError("PREPARED readback forbids destination identities")
    else:
        for field in destination_fields:
            _sha(value[field], field)
    event_count = _integer(value["event_count"], "event_count", minimum=0)
    head_revision = _integer(value["head_revision"], "head_revision", minimum=0)
    if event_count != head_revision:
        raise ValueError("readback event_count/head_revision mismatch")
    if event_count == 0:
        if value["head_event_sha256"] is not None or phase is not CustodyPhase.PREPARED:
            raise ValueError("empty readback must be PREPARED without a head")
    else:
        _sha(value["head_event_sha256"], "head_event_sha256")
    checkpoint_count = _integer(value["checkpoint_count"], "checkpoint_count", minimum=0)
    last_checkpoint = _nullable_sha(
        value["last_checkpoint_receipt_sha256"], "last_checkpoint_receipt_sha256"
    )
    if (checkpoint_count == 0) != (last_checkpoint is None):
        raise ValueError("checkpoint count/readback head mismatch")
    terminal = _nullable_sha(value["terminal_receipt_sha256"], "terminal_receipt_sha256")
    if (phase is CustodyPhase.TERMINAL_SEALED) != (terminal is not None):
        raise ValueError("terminal receipt/phase mismatch")
    if value["active_lease_state"] is not None:
        LeaseState(value["active_lease_state"])
    read_back_at = _timestamp(value["read_back_at"], "read_back_at")
    current_values = [value[field] for field in _CURRENT_INVENTORY_READBACK_SHA_FIELDS]
    current_observed_at = value["current_inventory_observed_at"]
    if any(item is not None for item in (*current_values, current_observed_at)):
        if any(item is None for item in (*current_values, current_observed_at)):
            raise ValueError("current terminal inventory readback must be complete")
        if phase is not CustodyPhase.TERMINAL_SEALED:
            raise ValueError("current terminal inventory requires TERMINAL_SEALED phase")
        for field in _CURRENT_INVENTORY_READBACK_SHA_FIELDS:
            _sha(value[field], field)
        if _timestamp(current_observed_at, "current_inventory_observed_at") != read_back_at:
            raise ValueError("current terminal inventory observation must match read_back_at")
    _boolean(value["fixture_only"], "fixture_only", exact=fixture)
    _boolean(value["authority_created"], "authority_created", exact=False)
    _boolean(value["native_backend_observed"], "native_backend_observed", exact=not fixture)
    _boolean(value["private_handle_returned"], "private_handle_returned", exact=False)
    _boolean(value["model_artifact_binding_created"], "model_artifact_binding_created", exact=False)
    _boolean(value["candidate_registered"], "candidate_registered", exact=False)
    effects = _integer(value["resource_effect_count"], "resource_effect_count")
    if fixture and effects != 0:
        raise ValueError("fixture readback must remain effect-0")
    if not fixture and effects < 1:
        raise ValueError("production readback must attest an observed backend effect")
    domain = _FIXTURE_READBACK_DOMAIN if fixture else _PRODUCTION_READBACK_DOMAIN
    _verify_digest(value, "readback_sha256", domain)


_ADMISSION_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "plan_sha256",
    "decision",
    "reason_codes",
    "evaluated_at",
    "fixture_only",
    "authority_created",
    "destination_activated",
    "write_lease_created",
    "load_lease_created",
    "native_backend_invoked",
    "model_artifact_binding_created",
    "candidate_registered",
    "training_started",
    "model_loaded",
    "resource_effect_count",
    "admission_sha256",
}


def _validate_production_admission(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _ADMISSION_FIELDS, "Task084ProductionCustodyAdmissionV1")
    _validate_discriminator(value, "Task084ProductionCustodyAdmissionV1")
    _sha(value["plan_sha256"], "plan_sha256")
    if value["decision"] != "BLOCKED" or value["reason_codes"] != list(_PRODUCTION_BLOCKERS):
        raise ValueError("current-source production admission must remain exact BLOCKED")
    _sorted_reason_codes(value["reason_codes"])
    _timestamp(value["evaluated_at"], "evaluated_at")
    for field in (
        "fixture_only",
        "authority_created",
        "destination_activated",
        "write_lease_created",
        "load_lease_created",
        "native_backend_invoked",
        "model_artifact_binding_created",
        "candidate_registered",
        "training_started",
        "model_loaded",
    ):
        _boolean(value[field], field, exact=False)
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("production admission compilation must remain effect-0")
    _verify_digest(value, "admission_sha256", _PRODUCTION_ADMISSION_DOMAIN)


_LOAD_ADMISSION_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "plan_sha256",
    "purpose",
    "bindings",
    "decision",
    "reason_codes",
    "evaluated_at",
    "fixture_only",
    "authority_created",
    "load_lease_created",
    "private_handle_returned",
    "model_loaded",
    "resource_effect_count",
    "admission_sha256",
}


def _validate_load_bindings(purpose: LoadPurpose, bindings: Any) -> dict[str, str]:
    if not isinstance(bindings, Mapping) or set(bindings) != _LOAD_BINDING_FIELDS[purpose]:
        raise ValueError("load bindings are incomplete or contain cross-purpose fields")
    result = dict(bindings)
    for field, digest in result.items():
        _sha(digest, field)
    return result


def _validate_load_admission(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _LOAD_ADMISSION_FIELDS, "Task084ModelLoadAdmissionV1")
    _validate_discriminator(value, "Task084ModelLoadAdmissionV1")
    _sha(value["plan_sha256"], "plan_sha256")
    purpose = LoadPurpose(value["purpose"])
    _validate_load_bindings(purpose, value["bindings"])
    if value["decision"] != "BLOCKED":
        raise ValueError("current-source load admission must remain BLOCKED")
    expected_reasons = sorted(
        {
            *_PRODUCTION_BLOCKERS,
            {
                LoadPurpose.TRAINING_RESUME: "TASK046_RESUME_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
                LoadPurpose.HELD_OUT_EVALUATION: "TASK046_EVALUATION_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
                LoadPurpose.LOCAL_NARRATION_INFERENCE: "H4_AND_INFERENCE_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
            }[purpose],
        }
    )
    if value["reason_codes"] != expected_reasons:
        raise ValueError("load admission reason set mismatch")
    _sorted_reason_codes(value["reason_codes"])
    _timestamp(value["evaluated_at"], "evaluated_at")
    for field in (
        "fixture_only",
        "authority_created",
        "load_lease_created",
        "private_handle_returned",
        "model_loaded",
    ):
        _boolean(value[field], field, exact=False)
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("load admission compilation must remain effect-0")
    _verify_digest(value, "admission_sha256", _LOAD_ADMISSION_DOMAIN)


_LOAD_READBACK_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "plan_sha256",
    "lease_id",
    "purpose",
    "bindings_sha256",
    "state",
    "expected_head_revision",
    "expected_head_sha256",
    "load_handle_identity_sha256",
    "completion_verification_sha256",
    "issued_at",
    "expires_at",
    "read_back_at",
    "fixture_only",
    "authority_created",
    "private_handle_returned",
    "model_loaded",
    "resource_effect_count",
    "readback_sha256",
}


def _validate_load_readback(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _LOAD_READBACK_FIELDS, "Task084FixtureModelLoadReadbackV1")
    _validate_discriminator(value, "Task084FixtureModelLoadReadbackV1")
    for field in ("plan_sha256", "bindings_sha256", "expected_head_sha256"):
        _sha(value[field], field)
    _identifier(value["lease_id"], "lease_id")
    LoadPurpose(value["purpose"])
    state = LeaseState(value["state"])
    if state not in {
        LeaseState.ISSUED,
        LeaseState.OPEN_STARTED,
        LeaseState.CONSUMED,
        LeaseState.EXPIRED,
        LeaseState.COMPLETION_UNKNOWN,
    }:
        raise ValueError("fixture load readback state is invalid")
    _integer(value["expected_head_revision"], "expected_head_revision", minimum=1)
    handle_identity = _nullable_sha(
        value["load_handle_identity_sha256"], "load_handle_identity_sha256"
    )
    completion_verification = _nullable_sha(
        value["completion_verification_sha256"],
        "completion_verification_sha256",
    )
    if state in {LeaseState.ISSUED, LeaseState.EXPIRED}:
        if handle_identity is not None or completion_verification is not None:
            raise ValueError("unopened load readback forbids handle/completion identity")
    elif state is LeaseState.OPEN_STARTED:
        if handle_identity is None or completion_verification is not None:
            raise ValueError("open load readback requires only handle identity")
    elif state is LeaseState.CONSUMED:
        if handle_identity is None or completion_verification is None:
            raise ValueError("consumed load readback requires completion verification")
    elif state is LeaseState.COMPLETION_UNKNOWN and handle_identity is None:
        raise ValueError("unknown load completion requires opened handle identity")
    issued = _timestamp_value(_timestamp(value["issued_at"], "issued_at"))
    expires = _timestamp_value(_timestamp(value["expires_at"], "expires_at"))
    read_back = _timestamp_value(_timestamp(value["read_back_at"], "read_back_at"))
    if expires <= issued or read_back < issued:
        raise ValueError("fixture load readback lifetime/currentness mismatch")
    for field in (
        "fixture_only",
        "authority_created",
        "private_handle_returned",
        "model_loaded",
    ):
        _boolean(value[field], field, exact=field == "fixture_only")
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("fixture load readback must remain effect-0")
    _verify_digest(value, "readback_sha256", _FIXTURE_LOAD_READBACK_DOMAIN)


_NEGATIVE_ACK_FIELDS = {
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "acknowledgement_id",
    "plan_sha256",
    "lease_id",
    "publish_started_event_sha256",
    "producer_event_sha256",
    "verified_no_visible_manifest",
    "verified_no_current_artifact_set",
    "observed_at",
    "fixture_only",
    "authority_created",
    "resource_effect_count",
    "acknowledgement_sha256",
}


def _validate_negative_ack(value: Mapping[str, Any]) -> None:
    _expect_keys(value, _NEGATIVE_ACK_FIELDS, "Task084FixtureDurableNegativeAcknowledgementV1")
    _validate_discriminator(value, "Task084FixtureDurableNegativeAcknowledgementV1")
    for field in ("acknowledgement_id", "lease_id"):
        _identifier(value[field], field)
    for field in ("plan_sha256", "publish_started_event_sha256", "producer_event_sha256"):
        _sha(value[field], field)
    _boolean(value["verified_no_visible_manifest"], "verified_no_visible_manifest", exact=True)
    _boolean(value["verified_no_current_artifact_set"], "verified_no_current_artifact_set", exact=True)
    _timestamp(value["observed_at"], "observed_at")
    _boolean(value["fixture_only"], "fixture_only", exact=True)
    _boolean(value["authority_created"], "authority_created", exact=False)
    if _integer(value["resource_effect_count"], "resource_effect_count") != 0:
        raise ValueError("fixture acknowledgement must remain effect-0")
    _verify_digest(value, "acknowledgement_sha256", _NEGATIVE_ACK_DOMAIN)


def validate_record(value: Mapping[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record must be an object")
    body = copy.deepcopy(dict(value))
    record_type = body.get("record_type")
    if expected_type is not None and record_type != expected_type:
        raise ValueError(f"expected {expected_type}")
    if record_type == "Task084OutputArtifactDestinationPlanV1":
        _validate_plan(body)
    elif record_type == "Task084FixtureArtifactInventoryV1":
        _validate_inventory(body)
    elif record_type == "Task084FixtureCustodyEventV1":
        _validate_event(body)
    elif record_type in {
        "Task084FixtureModelCheckpointCustodyReceiptV1",
        "Task084FixtureModelArtifactCustodyReceiptV1",
        "Task084ModelCheckpointCustodyReceiptV1",
        "Task084ModelArtifactCustodyReceiptV1",
    }:
        _validate_receipt(body, record_type)
    elif record_type in {"Task084FixtureCustodyReadbackV1", "Task084CustodyReadbackV1"}:
        _validate_readback(body, record_type)
    elif record_type == "Task084ProductionCustodyAdmissionV1":
        _validate_production_admission(body)
    elif record_type == "Task084ModelLoadAdmissionV1":
        _validate_load_admission(body)
    elif record_type == "Task084FixtureModelLoadReadbackV1":
        _validate_load_readback(body)
    elif record_type == "Task084FixtureDurableNegativeAcknowledgementV1":
        _validate_negative_ack(body)
    else:
        raise ValueError("record_type is unknown")
    return body


def parse_security_json(payload: bytes, *, expected_type: str | None = None) -> _CanonicalRecord:
    if not isinstance(payload, bytes):
        raise ValueError("security JSON must be bytes")
    if not payload or len(payload) > MAX_SECURITY_JSON_BYTES or payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("security JSON is empty, oversized, or contains BOM")
    try:
        text = payload.decode("utf-8", errors="strict")
        decoder = json.JSONDecoder(
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
        value, end = decoder.raw_decode(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("security JSON is invalid") from exc
    if end != len(text) or _max_depth(value) > MAX_SECURITY_JSON_DEPTH:
        raise ValueError("security JSON has trailing bytes or excessive depth")
    body = validate_record(value, expected_type=expected_type)
    cls = _RECORD_CLASSES[body["record_type"]]
    return cls.from_dict(body)


def compile_output_artifact_destination_plan(
    training_intent: Mapping[str, Any] | TrainingRunIntent,
    training_run_revision: Mapping[str, Any] | TrainingRunRevision,
    training_input_snapshot: Mapping[str, Any] | TrainingInputSnapshot,
    durable_job_binding: Mapping[str, Any] | TrainingDurableJobBinding,
    *,
    plan_id: str,
    training_run_head_sha256: str,
    task043_job_readback_sha256: str,
    task043_job_head_sha256: str,
    task083_reservation_plan_sha256: str,
    destination_coordinate: str,
    custody_policy_sha256: str,
    encryption_policy_sha256: str,
    aead_suite: str,
    cipher_backend_revision_sha256: str,
    principal_scope_sha256: str,
    key_scope_sha256: str,
    dacl_policy_sha256: str,
    checkpoint_expected_entries: Sequence[Mapping[str, Any]],
    terminal_expected_entries: Sequence[Mapping[str, Any]],
    max_file_count: int,
    max_total_plain_bytes: int,
    max_total_cipher_bytes: int,
    compiled_at: str,
) -> Task084OutputArtifactDestinationPlanV1:
    intent = TrainingRunIntent.from_dict(_mapping(training_intent, "training_intent")).to_dict()
    run = TrainingRunRevision.from_dict(
        _mapping(training_run_revision, "training_run_revision")
    ).to_dict()
    snapshot = TrainingInputSnapshot.from_dict(
        _mapping(training_input_snapshot, "training_input_snapshot")
    ).to_dict()
    job = TrainingDurableJobBinding.from_dict(
        _mapping(durable_job_binding, "durable_job_binding")
    ).to_dict()
    if intent["project_id"] != snapshot["project_id"]:
        raise ValueError("training intent/snapshot project mismatch")
    if run["run_intent_sha256"] != intent["intent_sha256"]:
        raise ValueError("training run revision/intent mismatch")
    if run["durable_job_binding"]["binding_sha256"] != job["binding_sha256"]:
        raise ValueError("training run revision/Job binding mismatch")
    if intent["training_input_snapshot_sha256"] != snapshot["snapshot_sha256"]:
        raise ValueError("training input snapshot digest mismatch")
    engine = intent["engine_admission_binding"]
    destination = intent["output_artifact_destination_binding"]
    feasibility = intent["target_resource_feasibility_binding"]
    if engine["contract_state"] != "BOUND_VERIFIED":
        raise ValueError("destination plan requires a bound engine identity")
    if destination["contract_state"] != "BOUND_VERIFIED":
        raise ValueError("destination plan requires a bound logical destination")
    if destination["public_exposure"] is not False:
        raise ValueError("voice model destination must remain private")
    if not {"CHECKPOINT", "MODEL_OUTPUT"}.issubset(destination["allowed_artifact_classes"]):
        raise ValueError("destination does not allow checkpoint and model output")
    if feasibility["contract_state"] != "BOUND_VERIFIED":
        raise ValueError("destination plan requires a bound recipe identity")
    checkpoint_entries = _validate_expected_entries(
        [dict(item) for item in checkpoint_expected_entries], checkpoint_base=True
    )
    terminal_entries = _validate_expected_entries(
        [dict(item) for item in terminal_expected_entries]
    )
    coordinate = _identifier(destination_coordinate, "destination_coordinate")
    if coordinate != destination["logical_uri"]:
        raise ValueError("destination coordinate does not match TrainingRunIntent")
    body: dict[str, Any] = {
        "record_type": "Task084OutputArtifactDestinationPlanV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_id": _identifier(plan_id, "plan_id"),
        "project_id": intent["project_id"],
        "run_intent_sha256": intent["intent_sha256"],
        "run_revision": intent["revision"],
        "training_run_revision_sha256": run["revision_sha256"],
        "training_run_revision_number": run["revision"],
        "training_run_state": run["state"],
        "training_run_head_sha256": _sha(
            training_run_head_sha256, "training_run_head_sha256"
        ),
        "training_input_snapshot_sha256": snapshot["snapshot_sha256"],
        "dataset_id": snapshot["dataset_id"],
        "voice_dataset_revision_sha256": snapshot["voice_dataset_revision_sha256"],
        "job_binding_sha256": job["binding_sha256"],
        "job_contract_state": job["contract_state"],
        "job_id": job["job_id"],
        "job_revision": job["job_revision"],
        "job_revision_sha256": job["job_revision_sha256"],
        "task043_job_readback_sha256": _sha(
            task043_job_readback_sha256, "task043_job_readback_sha256"
        ),
        "task043_job_head_sha256": _sha(
            task043_job_head_sha256, "task043_job_head_sha256"
        ),
        "task083_reservation_plan_sha256": _sha(
            task083_reservation_plan_sha256, "task083_reservation_plan_sha256"
        ),
        "training_mode": intent["training_mode"],
        "recipe_revision_sha256": feasibility["recipe_revision_sha256"],
        "engine_admission_sha256": engine["binding_sha256"],
        "engine_id": engine["engine_id"],
        "engine_commit_sha256": engine["engine_commit_sha256"],
        "base_model_id": engine["base_model_id"],
        "base_model_revision": engine["base_model_revision"],
        "base_model_sha256": engine["base_model_sha256"],
        "runtime_revision": engine["runtime_revision"],
        "runtime_sha256": engine["runtime_sha256"],
        "code_revision": engine["code_revision"],
        "code_sha256": engine["code_sha256"],
        "config_sha256": intent["config_sha256"],
        "current_consent_rights_license_sha256": intent[
            "current_consent_rights_license_sha256"
        ],
        "output_destination_binding_sha256": destination["binding_sha256"],
        "destination_coordinate": coordinate,
        "destination_coordinate_sha256": sha256_bytes(
            b"BAI:TASK-084:DESTINATION-COORDINATE:V1\x00" + coordinate.encode("ascii")
        ),
        "custody_policy_sha256": _sha(custody_policy_sha256, "custody_policy_sha256"),
        "encryption_policy_sha256": _sha(
            encryption_policy_sha256, "encryption_policy_sha256"
        ),
        "aead_suite": _identifier(aead_suite, "aead_suite"),
        "cipher_backend_revision_sha256": _sha(
            cipher_backend_revision_sha256, "cipher_backend_revision_sha256"
        ),
        "principal_scope_sha256": _sha(principal_scope_sha256, "principal_scope_sha256"),
        "key_scope_sha256": _sha(key_scope_sha256, "key_scope_sha256"),
        "dacl_policy_sha256": _sha(dacl_policy_sha256, "dacl_policy_sha256"),
        "checkpoint_expected_entries": checkpoint_entries,
        "checkpoint_entry_allowlist_sha256": _entry_allowlist_sha256(checkpoint_entries),
        "checkpoint_namespace_policy_sha256": _checkpoint_namespace_policy_sha256(),
        "terminal_expected_entries": terminal_entries,
        "terminal_entry_allowlist_sha256": _entry_allowlist_sha256(terminal_entries),
        "max_file_count": max_file_count,
        "max_total_plain_bytes": max_total_plain_bytes,
        "max_total_cipher_bytes": max_total_cipher_bytes,
        "max_relative_file_depth": MAX_RELATIVE_FILE_DEPTH,
        "compiled_at": _timestamp(compiled_at, "compiled_at"),
        "task043_job_source_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "task083_contract_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "h3_v2_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "compound_operation_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "producer_event_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "windows_backend_state": "NOT_AVAILABLE_CURRENT_SOURCE",
        "fixture_only": True,
        "authority_created": False,
        "destination_activated": False,
        "write_lease_created": False,
        "load_lease_created": False,
        "model_artifact_binding_created": False,
        "candidate_registered": False,
        "resource_effect_count": 0,
        "production_eligible": False,
    }
    if body["training_run_head_sha256"] != run["revision_sha256"]:
        raise ValueError("training run head does not match the supplied revision")
    return Task084OutputArtifactDestinationPlanV1.from_dict(
        _with_digest(body, "plan_sha256", _PLAN_DOMAIN)
    )


def compile_production_custody_admission(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
    *,
    evaluated_at: str,
) -> Task084ProductionCustodyAdmissionV1:
    parsed = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    ).to_dict()
    body = {
        "record_type": "Task084ProductionCustodyAdmissionV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed["plan_sha256"],
        "decision": "BLOCKED",
        "reason_codes": list(_PRODUCTION_BLOCKERS),
        "evaluated_at": _timestamp(evaluated_at, "evaluated_at"),
        "fixture_only": False,
        "authority_created": False,
        "destination_activated": False,
        "write_lease_created": False,
        "load_lease_created": False,
        "native_backend_invoked": False,
        "model_artifact_binding_created": False,
        "candidate_registered": False,
        "training_started": False,
        "model_loaded": False,
        "resource_effect_count": 0,
    }
    return Task084ProductionCustodyAdmissionV1.from_dict(
        _with_digest(body, "admission_sha256", _PRODUCTION_ADMISSION_DOMAIN)
    )


def compile_model_load_admission(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
    *,
    purpose: str | LoadPurpose,
    bindings: Mapping[str, str],
    evaluated_at: str,
) -> Task084ModelLoadAdmissionV1:
    parsed = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    ).to_dict()
    selected = LoadPurpose(purpose)
    parsed_bindings = _validate_load_bindings(selected, bindings)
    purpose_reason = {
        LoadPurpose.TRAINING_RESUME: "TASK046_RESUME_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
        LoadPurpose.HELD_OUT_EVALUATION: "TASK046_EVALUATION_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
        LoadPurpose.LOCAL_NARRATION_INFERENCE: "H4_AND_INFERENCE_AUTHORITY_NOT_AVAILABLE_CURRENT_SOURCE",
    }[selected]
    body = {
        "record_type": "Task084ModelLoadAdmissionV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed["plan_sha256"],
        "purpose": selected.value,
        "bindings": parsed_bindings,
        "decision": "BLOCKED",
        "reason_codes": sorted({*_PRODUCTION_BLOCKERS, purpose_reason}),
        "evaluated_at": _timestamp(evaluated_at, "evaluated_at"),
        "fixture_only": False,
        "authority_created": False,
        "load_lease_created": False,
        "private_handle_returned": False,
        "model_loaded": False,
        "resource_effect_count": 0,
    }
    return Task084ModelLoadAdmissionV1.from_dict(
        _with_digest(body, "admission_sha256", _LOAD_ADMISSION_DOMAIN)
    )


def compile_fixture_inventory(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
    *,
    inventory_id: str,
    producer_event_sha256: str,
    artifact_variant: str | ArtifactVariant,
    destination_root_identity_sha256: str,
    destination_ancestor_identity_sha256: str,
    destination_target_identity_sha256: str,
    destination_pinned_readback_sha256: str,
    entries: Sequence[Mapping[str, Any]],
    manifest_relative_file: str,
    manifest_sha256: str,
    manifest_nonce_sha256: str,
    manifest_authentication_evidence_sha256: str,
    manifest_envelope_evidence_sha256: str,
    manifest_confidentiality: str,
    manifest_opened_physical_identity_sha256: str,
    manifest_ancestor_identity_sha256: str,
    manifest_regular_file: bool,
    manifest_nlink: int,
    manifest_reparse_point: bool,
    manifest_opened_identity_pinned: bool,
    manifest_file_flush_evidence_sha256: str,
    manifest_directory_flush_evidence_sha256: str,
    manifest_pinned_readback_sha256: str,
    checkpoint_index: int | None = None,
) -> Task084FixtureArtifactInventoryV1:
    parsed_plan = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    ).to_dict()
    variant = ArtifactVariant(artifact_variant)
    producer_digest = _sha(producer_event_sha256, "producer_event_sha256")
    parsed_entries = [_validate_file_observation(item) for item in entries]
    parsed_entries.sort(key=lambda item: (item["index"], item["entry_id"]))
    allowlist = [
        {
            "entry_id": item["entry_id"],
            "role": item["role"],
            "index": item["index"],
            "relative_file": item["relative_file"],
        }
        for item in parsed_entries
    ]
    if variant is ArtifactVariant.CHECKPOINT:
        parsed_checkpoint_index = _integer(
            checkpoint_index,
            "checkpoint_index",
            minimum=1,
            maximum=MAX_CHECKPOINT_INDEX,
        )
        expected_entries = _checkpoint_scoped_entries(
            parsed_plan["checkpoint_expected_entries"],
            checkpoint_index=parsed_checkpoint_index,
            producer_event_sha256=producer_digest,
        )
        checkpoint_namespace = _checkpoint_namespace_sha256(
            parsed_plan["plan_sha256"],
            parsed_checkpoint_index,
            producer_digest,
        )
    else:
        if checkpoint_index is not None:
            raise ValueError("terminal inventory forbids checkpoint_index")
        parsed_checkpoint_index = None
        checkpoint_namespace = None
        expected_entries = parsed_plan["terminal_expected_entries"]
    if allowlist != expected_entries:
        raise ValueError("inventory does not match the closed expected-entry allowlist")
    parsed_manifest_relative_file = _relative_file(
        manifest_relative_file, "manifest_relative_file"
    )
    if variant is ArtifactVariant.CHECKPOINT:
        producer_event_sha256_hex = producer_digest.removeprefix("sha256:")
        expected_manifest = (
            f"checkpoints/{parsed_checkpoint_index}/"
            f"{producer_event_sha256_hex}/manifest.json.enc"
        )
        if parsed_manifest_relative_file != expected_manifest:
            raise ValueError("checkpoint manifest is outside its immutable namespace")
    if len(parsed_entries) > parsed_plan["max_file_count"]:
        raise ValueError("inventory exceeds max_file_count")
    if sum(item["plain_byte_count"] for item in parsed_entries) > parsed_plan[
        "max_total_plain_bytes"
    ]:
        raise ValueError("inventory exceeds max_total_plain_bytes")
    if sum(item["cipher_byte_count"] for item in parsed_entries) > parsed_plan[
        "max_total_cipher_bytes"
    ]:
        raise ValueError("inventory exceeds max_total_cipher_bytes")
    body = {
        "record_type": "Task084FixtureArtifactInventoryV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "inventory_id": _identifier(inventory_id, "inventory_id"),
        "plan_sha256": parsed_plan["plan_sha256"],
        "producer_event_sha256": producer_digest,
        "artifact_variant": variant.value,
        "checkpoint_index": parsed_checkpoint_index,
        "checkpoint_namespace_sha256": checkpoint_namespace,
        "destination_root_identity_sha256": _sha(
            destination_root_identity_sha256, "destination_root_identity_sha256"
        ),
        "destination_ancestor_identity_sha256": _sha(
            destination_ancestor_identity_sha256,
            "destination_ancestor_identity_sha256",
        ),
        "destination_target_identity_sha256": _sha(
            destination_target_identity_sha256, "destination_target_identity_sha256"
        ),
        "destination_pinned_readback_sha256": _sha(
            destination_pinned_readback_sha256,
            "destination_pinned_readback_sha256",
        ),
        "entries": parsed_entries,
        "entry_count": len(parsed_entries),
        "total_plain_bytes": sum(item["plain_byte_count"] for item in parsed_entries),
        "total_cipher_bytes": sum(item["cipher_byte_count"] for item in parsed_entries),
        "manifest_relative_file": parsed_manifest_relative_file,
        "manifest_sha256": _sha(manifest_sha256, "manifest_sha256"),
        "manifest_nonce_sha256": _sha(manifest_nonce_sha256, "manifest_nonce_sha256"),
        "manifest_authentication_evidence_sha256": _sha(
            manifest_authentication_evidence_sha256,
            "manifest_authentication_evidence_sha256",
        ),
        "manifest_envelope_evidence_sha256": _sha(
            manifest_envelope_evidence_sha256,
            "manifest_envelope_evidence_sha256",
        ),
        "manifest_confidentiality": manifest_confidentiality,
        "manifest_opened_physical_identity_sha256": _sha(
            manifest_opened_physical_identity_sha256,
            "manifest_opened_physical_identity_sha256",
        ),
        "manifest_ancestor_identity_sha256": _sha(
            manifest_ancestor_identity_sha256, "manifest_ancestor_identity_sha256"
        ),
        "manifest_regular_file": _boolean(
            manifest_regular_file, "manifest_regular_file", exact=True
        ),
        "manifest_nlink": manifest_nlink,
        "manifest_reparse_point": _boolean(
            manifest_reparse_point, "manifest_reparse_point", exact=False
        ),
        "manifest_opened_identity_pinned": _boolean(
            manifest_opened_identity_pinned,
            "manifest_opened_identity_pinned",
            exact=True,
        ),
        "manifest_file_flush_evidence_sha256": _sha(
            manifest_file_flush_evidence_sha256,
            "manifest_file_flush_evidence_sha256",
        ),
        "manifest_directory_flush_evidence_sha256": _sha(
            manifest_directory_flush_evidence_sha256,
            "manifest_directory_flush_evidence_sha256",
        ),
        "manifest_pinned_readback_sha256": _sha(
            manifest_pinned_readback_sha256, "manifest_pinned_readback_sha256"
        ),
        "opened_physical_identity_set_sha256": _physical_identity_set_sha256(
            parsed_entries
        ),
        "unexpected_files_present": False,
        "fixture_only": True,
        "authority_created": False,
        "resource_effect_count": 0,
    }
    return Task084FixtureArtifactInventoryV1.from_dict(
        _with_digest(body, "inventory_sha256", _INVENTORY_DOMAIN)
    )


class _EphemeralFixtureObject:
    __slots__ = ()

    def __copy__(self):
        raise TypeError("fixture lease objects are non-copyable")

    def __deepcopy__(self, memo):
        raise TypeError("fixture lease objects are non-copyable")

    def __reduce__(self):
        raise TypeError("fixture lease objects are non-serializable")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} redacted fixture-only effect-0>"


class Task084FixtureEntryHandle(_EphemeralFixtureObject):
    __slots__ = ("_lease_id", "_entry_id", "_nonce", "_closed")

    def __init__(self, *, lease_id: str, entry_id: str, nonce: object, key: object) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture entry handles are factory-only")
        self._lease_id = lease_id
        self._entry_id = entry_id
        self._nonce = nonce
        self._closed = False

    @property
    def entry_id(self) -> str:
        return self._entry_id

    @property
    def private_handle_returned(self) -> bool:
        return False

    @property
    def resource_effect_count(self) -> int:
        return 0


class Task084FixtureModelArtifactWriteLeaseV1(_EphemeralFixtureObject):
    __slots__ = (
        "_ledger_nonce",
        "_lease_id",
        "_request_sha256",
        "_producer_event_sha256",
        "_variant",
        "_checkpoint_index",
        "_training_step",
        "_progress_ppm",
        "_task046_checkpoint_binding_sha256",
        "_task046_terminal_receipt_sha256",
        "_producer_observed_at",
        "_issued_at",
        "_expires_at",
        "_expected_revision",
        "_expected_head_sha256",
        "_state",
        "_entry_handles",
        "_entry_observations",
        "_publish_started_event_sha256",
    )

    def __init__(
        self,
        *,
        ledger_nonce: object,
        lease_id: str,
        request_sha256: str,
        producer_event_sha256: str,
        variant: ArtifactVariant,
        checkpoint_index: int | None,
        training_step: int | None,
        progress_ppm: int | None,
        task046_checkpoint_binding_sha256: str,
        task046_terminal_receipt_sha256: str | None,
        producer_observed_at: datetime,
        issued_at: str,
        expires_at: str,
        expected_revision: int,
        expected_head_sha256: str,
        key: object,
    ) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture write leases are factory-only")
        self._ledger_nonce = ledger_nonce
        self._lease_id = lease_id
        self._request_sha256 = request_sha256
        self._producer_event_sha256 = producer_event_sha256
        self._variant = variant
        self._checkpoint_index = checkpoint_index
        self._training_step = training_step
        self._progress_ppm = progress_ppm
        self._task046_checkpoint_binding_sha256 = task046_checkpoint_binding_sha256
        self._task046_terminal_receipt_sha256 = task046_terminal_receipt_sha256
        self._producer_observed_at = producer_observed_at
        self._issued_at = issued_at
        self._expires_at = expires_at
        self._expected_revision = expected_revision
        self._expected_head_sha256 = expected_head_sha256
        self._state = LeaseState.ISSUED
        self._entry_handles: dict[str, Task084FixtureEntryHandle] = {}
        self._entry_observations: dict[str, dict[str, Any]] = {}
        self._publish_started_event_sha256: str | None = None

    @property
    def lease_id(self) -> str:
        return self._lease_id

    @property
    def state(self) -> LeaseState:
        return self._state

    @property
    def artifact_variant(self) -> ArtifactVariant:
        return self._variant

    @property
    def checkpoint_index(self) -> int | None:
        return self._checkpoint_index

    @property
    def private_handle_returned(self) -> bool:
        return False

    @property
    def resource_effect_count(self) -> int:
        return 0


class Task084FixtureManifestVerification(_EphemeralFixtureObject):
    __slots__ = ("_ledger_nonce", "_lease_id", "_inventory_sha256", "_token_nonce", "_used")

    def __init__(
        self,
        *,
        ledger_nonce: object,
        lease_id: str,
        inventory_sha256: str,
        key: object,
    ) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture manifest verification is factory-only")
        self._ledger_nonce = ledger_nonce
        self._lease_id = lease_id
        self._inventory_sha256 = inventory_sha256
        self._token_nonce = object()
        self._used = False


class Task084FixtureModelLoadOpenHandle(_EphemeralFixtureObject):
    __slots__ = (
        "_ledger_nonce",
        "_lease_id",
        "_handle_identity_sha256",
        "_opened_at",
        "_used",
    )

    def __init__(
        self,
        *,
        ledger_nonce: object,
        lease_id: str,
        handle_identity_sha256: str,
        opened_at: datetime,
        key: object,
    ) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture model-load handles are factory-only")
        self._ledger_nonce = ledger_nonce
        self._lease_id = lease_id
        self._handle_identity_sha256 = handle_identity_sha256
        self._opened_at = opened_at
        self._used = False

    @property
    def handle_identity_sha256(self) -> str:
        return self._handle_identity_sha256

    @property
    def private_handle_returned(self) -> bool:
        return False

    @property
    def resource_effect_count(self) -> int:
        return 0


class Task084FixtureModelLoadCompletionVerification(_EphemeralFixtureObject):
    __slots__ = (
        "_ledger_nonce",
        "_lease_id",
        "_handle_identity_sha256",
        "_close_identity_sha256",
        "_completion_readback_sha256",
        "_zeroization_evidence_sha256",
        "_observed_at",
        "_verification_sha256",
        "_used",
    )

    def __init__(
        self,
        *,
        ledger_nonce: object,
        lease_id: str,
        handle_identity_sha256: str,
        close_identity_sha256: str,
        completion_readback_sha256: str,
        zeroization_evidence_sha256: str,
        observed_at: datetime,
        verification_sha256: str,
        key: object,
    ) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture model-load completion verification is factory-only")
        self._ledger_nonce = ledger_nonce
        self._lease_id = lease_id
        self._handle_identity_sha256 = handle_identity_sha256
        self._close_identity_sha256 = close_identity_sha256
        self._completion_readback_sha256 = completion_readback_sha256
        self._zeroization_evidence_sha256 = zeroization_evidence_sha256
        self._observed_at = observed_at
        self._verification_sha256 = verification_sha256
        self._used = False

    @property
    def verification_sha256(self) -> str:
        return self._verification_sha256

    @property
    def private_handle_returned(self) -> bool:
        return False

    @property
    def resource_effect_count(self) -> int:
        return 0


class Task084FixtureModelLoadLeaseV1(_EphemeralFixtureObject):
    __slots__ = (
        "_ledger_nonce",
        "_lease_id",
        "_purpose",
        "_bindings_sha256",
        "_issued_at",
        "_expires_at",
        "_expected_revision",
        "_expected_head_sha256",
        "_opened_at",
        "_open_handle",
        "_completion_verification_sha256",
        "_state",
    )

    def __init__(
        self,
        *,
        ledger_nonce: object,
        lease_id: str,
        purpose: LoadPurpose,
        bindings_sha256: str,
        issued_at: str,
        expires_at: str,
        expected_revision: int,
        expected_head_sha256: str,
        key: object,
    ) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("fixture load leases are factory-only")
        self._ledger_nonce = ledger_nonce
        self._lease_id = lease_id
        self._purpose = purpose
        self._bindings_sha256 = bindings_sha256
        self._issued_at = issued_at
        self._expires_at = expires_at
        self._expected_revision = expected_revision
        self._expected_head_sha256 = expected_head_sha256
        self._opened_at: datetime | None = None
        self._open_handle: Task084FixtureModelLoadOpenHandle | None = None
        self._completion_verification_sha256: str | None = None
        self._state = LeaseState.ISSUED

    @property
    def lease_id(self) -> str:
        return self._lease_id

    @property
    def purpose(self) -> LoadPurpose:
        return self._purpose

    @property
    def state(self) -> LeaseState:
        return self._state

    @property
    def private_handle_returned(self) -> bool:
        return False

    @property
    def resource_effect_count(self) -> int:
        return 0


def _request_sha256(operation: str, body: Mapping[str, Any]) -> str:
    return sha256_bytes(
        b"BAI:TASK-084:FIXTURE-REQUEST:V1\x00"
        + operation.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(body)
    )


def _event_transition(previous: CustodyPhase, event_kind: str, variant: str | None) -> CustodyPhase:
    allowed: dict[CustodyPhase, set[str]] = {
        CustodyPhase.PREPARED: {"DESTINATION_ACTIVATED"},
        CustodyPhase.DESTINATION_ACTIVE: {"CHECKPOINT_PUBLISH_STARTED"},
        CustodyPhase.CHECKPOINT_PUBLISHED: {
            "CHECKPOINT_PUBLISH_STARTED",
            "TERMINAL_PUBLISH_STARTED",
        },
        CustodyPhase.PUBLISH_STARTED: {
            "CHECKPOINT_PUBLISHED",
            "TERMINAL_SEALED",
            "PUBLISH_COMPLETION_UNKNOWN",
            "FAILED_CLOSED",
        },
        CustodyPhase.TERMINAL_SEALED: set(),
        CustodyPhase.COMPLETION_UNKNOWN: set(),
        CustodyPhase.FAILED_CLOSED: set(),
    }
    if event_kind not in allowed[previous]:
        raise ValueError("custody event transition is invalid")
    target = _EVENT_KIND_PHASE[event_kind]
    if previous is CustodyPhase.PUBLISH_STARTED:
        expected_completion = {
            ArtifactVariant.CHECKPOINT.value: "CHECKPOINT_PUBLISHED",
            ArtifactVariant.TERMINAL.value: "TERMINAL_SEALED",
        }
        if event_kind in {"CHECKPOINT_PUBLISHED", "TERMINAL_SEALED"} and (
            variant is None or expected_completion[variant] != event_kind
        ):
            raise ValueError("publish completion variant mismatch")
    return target


def replay_fixture_event_chain(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
    events: Sequence[Mapping[str, Any] | Task084FixtureCustodyEventV1],
    *,
    read_back_at: str,
) -> Task084FixtureCustodyReadbackV1:
    parsed_plan = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    ).to_dict()
    phase = CustodyPhase.PREPARED
    predecessor = parsed_plan["plan_sha256"]
    checkpoint_count = 0
    publish_variant: str | None = None
    publish_producer: str | None = None
    publish_checkpoint_index: int | None = None
    destination_identities: dict[str, str] | None = None
    last_event_at: datetime | None = None
    for expected_revision, item in enumerate(events, start=1):
        event = Task084FixtureCustodyEventV1.from_dict(_mapping(item, "event")).to_dict()
        if event["plan_sha256"] != parsed_plan["plan_sha256"]:
            raise ValueError("event chain plan mismatch")
        identities = {
            field: event[field]
            for field in (
                "destination_root_identity_sha256",
                "destination_ancestor_identity_sha256",
                "destination_target_identity_sha256",
                "destination_pinned_readback_sha256",
            )
        }
        if destination_identities is None:
            destination_identities = identities
        elif identities != destination_identities:
            raise ValueError("event chain destination identity fork")
        if event["event_revision"] != expected_revision:
            raise ValueError("event chain gap/rollback/duplicate revision")
        if event["predecessor_event_sha256"] != predecessor:
            raise ValueError("event chain fork/predecessor mismatch")
        event_time = _timestamp_value(event["event_at"])
        if last_event_at is not None and event_time < last_event_at:
            raise ValueError("event time rollback")
        next_phase = _event_transition(phase, event["event_kind"], publish_variant)
        if event["event_kind"].endswith("PUBLISH_STARTED"):
            publish_variant = event["artifact_variant"]
            publish_producer = event["producer_event_sha256"]
            publish_checkpoint_index = event["checkpoint_index"]
            if publish_variant == ArtifactVariant.CHECKPOINT.value:
                if event["checkpoint_index"] != checkpoint_count + 1:
                    raise ValueError("checkpoint event index gap/duplicate")
        elif event["event_kind"] == "CHECKPOINT_PUBLISHED":
            if (
                event["artifact_variant"] != publish_variant
                or event["producer_event_sha256"] != publish_producer
                or event["checkpoint_index"] != publish_checkpoint_index
            ):
                raise ValueError("publish start/completion context mismatch")
            checkpoint_count += 1
            publish_variant = None
            publish_producer = None
            publish_checkpoint_index = None
        elif event["event_kind"] in {
            "TERMINAL_SEALED",
            "PUBLISH_COMPLETION_UNKNOWN",
            "FAILED_CLOSED",
        }:
            if (
                event["artifact_variant"] != publish_variant
                or event["producer_event_sha256"] != publish_producer
                or event["checkpoint_index"] != publish_checkpoint_index
            ):
                raise ValueError("publish start/terminal context mismatch")
            publish_variant = None
            publish_producer = None
            publish_checkpoint_index = None
        phase = next_phase
        predecessor = event["event_sha256"]
        last_event_at = event_time
    if phase is CustodyPhase.PUBLISH_STARTED or publish_variant is not None:
        raise ValueError(
            "post-burn restart requires a durable terminal resolution event"
        )
    readback_time = _timestamp_value(_timestamp(read_back_at, "read_back_at"))
    if last_event_at is not None and readback_time < last_event_at:
        raise ValueError("replay readback predates the event chain head")
    body = {
        "record_type": "Task084FixtureCustodyReadbackV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed_plan["plan_sha256"],
        "destination_root_identity_sha256": (
            destination_identities["destination_root_identity_sha256"]
            if destination_identities is not None
            else None
        ),
        "destination_ancestor_identity_sha256": (
            destination_identities["destination_ancestor_identity_sha256"]
            if destination_identities is not None
            else None
        ),
        "destination_target_identity_sha256": (
            destination_identities["destination_target_identity_sha256"]
            if destination_identities is not None
            else None
        ),
        "destination_pinned_readback_sha256": (
            destination_identities["destination_pinned_readback_sha256"]
            if destination_identities is not None
            else None
        ),
        "phase": phase.value,
        "event_count": len(events),
        "head_revision": len(events),
        "head_event_sha256": predecessor if events else None,
        "checkpoint_count": checkpoint_count,
        "last_checkpoint_receipt_sha256": None,
        "terminal_receipt_sha256": None,
        **_empty_current_inventory_readback(),
        "active_lease_state": None,
        "read_back_at": _timestamp_text(readback_time),
        "fixture_only": True,
        "authority_created": False,
        "native_backend_observed": False,
        "private_handle_returned": False,
        "model_artifact_binding_created": False,
        "candidate_registered": False,
        "resource_effect_count": 0,
    }
    # Replay does not invent missing receipt identities.  A receipt-aware ledger
    # fills these fields; bare events are suitable only through pre-seal phases.
    if checkpoint_count or phase in {
        CustodyPhase.TERMINAL_SEALED,
        CustodyPhase.FAILED_CLOSED,
    }:
        raise ValueError("sealed event replay requires receipt-aware ledger readback")
    return Task084FixtureCustodyReadbackV1.from_dict(
        _with_digest(body, "readback_sha256", _FIXTURE_READBACK_DOMAIN)
    )


def _validate_receipt_plan_binding(
    plan: Mapping[str, Any],
    receipt: Mapping[str, Any],
    destination_identities: Mapping[str, str],
) -> None:
    bindings = {
        "plan_sha256": "plan_sha256",
        "project_id": "project_id",
        "run_intent_sha256": "run_intent_sha256",
        "training_run_revision_sha256": "training_run_revision_sha256",
        "training_run_head_sha256": "training_run_head_sha256",
        "job_binding_sha256": "job_binding_sha256",
        "task043_job_readback_sha256": "task043_job_readback_sha256",
        "task043_job_head_sha256": "task043_job_head_sha256",
        "training_input_snapshot_sha256": "training_input_snapshot_sha256",
        "recipe_revision_sha256": "recipe_revision_sha256",
        "engine_admission_sha256": "engine_admission_sha256",
        "base_model_sha256": "base_model_sha256",
        "runtime_sha256": "runtime_sha256",
        "code_sha256": "code_sha256",
        "config_sha256": "config_sha256",
        "current_consent_rights_license_sha256": "current_consent_rights_license_sha256",
        "task083_reservation_plan_sha256": "task083_reservation_plan_sha256",
        "destination_coordinate_sha256": "destination_coordinate_sha256",
        "custody_policy_sha256": "custody_policy_sha256",
        "encryption_policy_sha256": "encryption_policy_sha256",
        "cipher_backend_revision_sha256": "cipher_backend_revision_sha256",
        "principal_scope_sha256": "principal_scope_sha256",
        "key_scope_sha256": "key_scope_sha256",
        "dacl_policy_sha256": "dacl_policy_sha256",
        "checkpoint_namespace_policy_sha256": "checkpoint_namespace_policy_sha256",
    }
    if any(receipt[field] != plan[source] for field, source in bindings.items()):
        raise ValueError("custody receipt/plan binding mismatch")
    if any(receipt[field] != digest for field, digest in destination_identities.items()):
        raise ValueError("custody receipt/destination identity mismatch")


def _validate_current_inventory_against_receipt(
    inventory: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    bindings = {
        "plan_sha256": "plan_sha256",
        "producer_event_sha256": "producer_event_sha256",
        "inventory_sha256": "inventory_sha256",
        "manifest_sha256": "manifest_sha256",
        "manifest_nonce_sha256": "manifest_nonce_sha256",
        "manifest_authentication_evidence_sha256": (
            "manifest_authentication_evidence_sha256"
        ),
        "manifest_envelope_evidence_sha256": "manifest_envelope_evidence_sha256",
        "manifest_opened_physical_identity_sha256": (
            "manifest_opened_physical_identity_sha256"
        ),
        "manifest_ancestor_identity_sha256": "manifest_ancestor_identity_sha256",
        "manifest_file_flush_evidence_sha256": (
            "manifest_file_flush_evidence_sha256"
        ),
        "manifest_directory_flush_evidence_sha256": (
            "manifest_directory_flush_evidence_sha256"
        ),
        "manifest_pinned_readback_sha256": "manifest_pinned_readback_sha256",
        "opened_physical_identity_set_sha256": "opened_physical_identity_set_sha256",
        "destination_root_identity_sha256": "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256": "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256": "destination_target_identity_sha256",
        "destination_pinned_readback_sha256": "destination_pinned_readback_sha256",
        "checkpoint_namespace_sha256": "checkpoint_namespace_sha256",
    }
    if inventory["artifact_variant"] != ArtifactVariant.TERMINAL.value:
        raise ValueError("current terminal inventory must be TERMINAL")
    if any(inventory[field] != receipt[target] for field, target in bindings.items()):
        raise ValueError("current terminal inventory/receipt commitment mismatch")


def replay_fixture_custody(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
    events: Sequence[Mapping[str, Any] | Task084FixtureCustodyEventV1],
    checkpoint_receipts: Sequence[
        Mapping[str, Any] | Task084FixtureModelCheckpointCustodyReceiptV1
    ],
    *,
    terminal_receipt: (
        Mapping[str, Any] | Task084FixtureModelArtifactCustodyReceiptV1 | None
    ) = None,
    current_terminal_inventory: (
        Mapping[str, Any] | Task084FixtureArtifactInventoryV1 | None
    ) = None,
    negative_acknowledgements: Sequence[
        Mapping[str, Any] | Task084FixtureDurableNegativeAcknowledgementV1
    ] = (),
    read_back_at: str,
) -> Task084FixtureCustodyReadbackV1:
    """Rebuild body-free custody state from events plus durable receipts."""
    parsed_plan = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    ).to_dict()
    parsed_events = [
        Task084FixtureCustodyEventV1.from_dict(_mapping(item, "event")).to_dict()
        for item in events
    ]
    phase = CustodyPhase.PREPARED
    predecessor = parsed_plan["plan_sha256"]
    last_event_at: datetime | None = None
    destination_identities: dict[str, str] | None = None
    publish_context: tuple[str, str, int | None] | None = None
    checkpoint_events: list[dict[str, Any]] = []
    terminal_event: dict[str, Any] | None = None
    failure_event: dict[str, Any] | None = None
    for revision, event in enumerate(parsed_events, start=1):
        if event["plan_sha256"] != parsed_plan["plan_sha256"]:
            raise ValueError("event chain plan mismatch")
        if event["event_revision"] != revision:
            raise ValueError("event chain gap/rollback/duplicate revision")
        if event["predecessor_event_sha256"] != predecessor:
            raise ValueError("event chain fork/predecessor mismatch")
        event_at = _timestamp_value(event["event_at"])
        if last_event_at is not None and event_at < last_event_at:
            raise ValueError("event time rollback")
        identities = {
            field: event[field]
            for field in (
                "destination_root_identity_sha256",
                "destination_ancestor_identity_sha256",
                "destination_target_identity_sha256",
                "destination_pinned_readback_sha256",
            )
        }
        if destination_identities is None:
            destination_identities = identities
        elif identities != destination_identities:
            raise ValueError("event chain destination identity fork")
        next_phase = _event_transition(
            phase,
            event["event_kind"],
            publish_context[0] if publish_context is not None else None,
        )
        if event["event_kind"].endswith("PUBLISH_STARTED"):
            publish_context = (
                event["artifact_variant"],
                event["producer_event_sha256"],
                event["checkpoint_index"],
            )
        elif event["event_kind"] != "DESTINATION_ACTIVATED":
            current = (
                event["artifact_variant"],
                event["producer_event_sha256"],
                event["checkpoint_index"],
            )
            if current != publish_context:
                raise ValueError("publish start/completion context mismatch")
            if event["event_kind"] == "CHECKPOINT_PUBLISHED":
                checkpoint_events.append(event)
            elif event["event_kind"] == "TERMINAL_SEALED":
                terminal_event = event
            elif event["event_kind"] == "FAILED_CLOSED":
                failure_event = event
            publish_context = None
        phase = next_phase
        predecessor = event["event_sha256"]
        last_event_at = event_at
    parsed_checkpoints = [
        Task084FixtureModelCheckpointCustodyReceiptV1.from_dict(
            _mapping(item, "checkpoint_receipt")
        ).to_dict()
        for item in checkpoint_receipts
    ]
    if len(parsed_checkpoints) != len(checkpoint_events):
        raise ValueError("checkpoint event/receipt count mismatch")
    previous_receipt_sha256: str | None = None
    for index, (event, receipt) in enumerate(
        zip(checkpoint_events, parsed_checkpoints), start=1
    ):
        if destination_identities is None:
            raise ValueError("checkpoint receipt lacks destination activation")
        _validate_receipt_plan_binding(parsed_plan, receipt, destination_identities)
        if (
            receipt["checkpoint_index"] != index
            or receipt["checkpoint_count"] != index
            or receipt["last_checkpoint_receipt_sha256"] != previous_receipt_sha256
            or receipt["event_sha256"] != event["event_sha256"]
            or receipt["event_revision"] != event["event_revision"]
            or receipt["predecessor_event_sha256"]
            != event["predecessor_event_sha256"]
            or receipt["producer_event_sha256"] != event["producer_event_sha256"]
            or receipt["sealed_at"] != event["event_at"]
        ):
            raise ValueError("checkpoint receipt/event lineage mismatch")
        previous_receipt_sha256 = receipt["receipt_sha256"]
    parsed_terminal = (
        Task084FixtureModelArtifactCustodyReceiptV1.from_dict(
            _mapping(terminal_receipt, "terminal_receipt")
        ).to_dict()
        if terminal_receipt is not None
        else None
    )
    if (terminal_event is None) != (parsed_terminal is None):
        raise ValueError("terminal event/receipt presence mismatch")
    if parsed_terminal is not None and terminal_event is not None:
        if destination_identities is None:
            raise ValueError("terminal receipt lacks destination activation")
        _validate_receipt_plan_binding(
            parsed_plan, parsed_terminal, destination_identities
        )
        if (
            parsed_terminal["event_sha256"] != terminal_event["event_sha256"]
            or parsed_terminal["event_revision"] != terminal_event["event_revision"]
            or parsed_terminal["predecessor_event_sha256"]
            != terminal_event["predecessor_event_sha256"]
            or parsed_terminal["producer_event_sha256"]
            != terminal_event["producer_event_sha256"]
            or parsed_terminal["sealed_at"] != terminal_event["event_at"]
            or parsed_terminal["checkpoint_count"] != len(parsed_checkpoints)
            or parsed_terminal["last_checkpoint_receipt_sha256"]
            != previous_receipt_sha256
            or parsed_terminal["task046_checkpoint_binding_sha256"]
            != parsed_checkpoints[-1]["task046_checkpoint_binding_sha256"]
        ):
            raise ValueError("terminal receipt/event lineage mismatch")
    parsed_acks = [
        Task084FixtureDurableNegativeAcknowledgementV1.from_dict(
            _mapping(item, "negative_acknowledgement")
        ).to_dict()
        for item in negative_acknowledgements
    ]
    if failure_event is None:
        if parsed_acks:
            raise ValueError("unused durable negative acknowledgement")
    else:
        matches = [
            ack
            for ack in parsed_acks
            if ack["acknowledgement_sha256"]
            == failure_event["negative_acknowledgement_sha256"]
        ]
        if len(matches) != 1:
            raise ValueError("FAILED_CLOSED requires one exact durable negative acknowledgement")
        if len(parsed_acks) != 1:
            raise ValueError("FAILED_CLOSED forbids unrelated negative acknowledgements")
        ack = matches[0]
        if (
            ack["plan_sha256"] != parsed_plan["plan_sha256"]
            or ack["lease_id"] != failure_event["failed_lease_id"]
            or ack["producer_event_sha256"] != failure_event["producer_event_sha256"]
            or ack["publish_started_event_sha256"]
            != failure_event["predecessor_event_sha256"]
            or _timestamp_value(ack["observed_at"])
            > _timestamp_value(failure_event["event_at"])
        ):
            raise ValueError("FAILED_CLOSED acknowledgement lineage mismatch")
    if phase is CustodyPhase.PUBLISH_STARTED or publish_context is not None:
        raise ValueError(
            "post-burn restart requires a durable terminal resolution event"
        )
    if destination_identities is None and parsed_events:
        raise ValueError("event chain destination identities unavailable")
    readback_time = _timestamp_value(_timestamp(read_back_at, "read_back_at"))
    temporal_floor = last_event_at
    for receipt in (*parsed_checkpoints, *([parsed_terminal] if parsed_terminal else [])):
        receipt_time = _timestamp_value(receipt["sealed_at"])
        temporal_floor = (
            receipt_time
            if temporal_floor is None
            else max(temporal_floor, receipt_time)
        )
    for acknowledgement in parsed_acks:
        acknowledgement_time = _timestamp_value(acknowledgement["observed_at"])
        temporal_floor = (
            acknowledgement_time
            if temporal_floor is None
            else max(temporal_floor, acknowledgement_time)
        )
    if temporal_floor is not None and readback_time < temporal_floor:
        raise ValueError("replay readback predates durable custody evidence")
    current_inventory_fields = _empty_current_inventory_readback()
    if current_terminal_inventory is not None:
        if parsed_terminal is None:
            raise ValueError("current terminal inventory requires terminal receipt")
        parsed_current_inventory = Task084FixtureArtifactInventoryV1.from_dict(
            _mapping(current_terminal_inventory, "current_terminal_inventory")
        ).to_dict()
        _validate_current_inventory_against_receipt(
            parsed_current_inventory, parsed_terminal
        )
        current_inventory_fields = _current_inventory_readback(
            parsed_current_inventory, observed_at=read_back_at
        )
    body = {
        "record_type": "Task084FixtureCustodyReadbackV1",
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": CANONICAL_OWNER_TASK,
        "plan_sha256": parsed_plan["plan_sha256"],
        **(
            destination_identities
            if destination_identities is not None
            else {
                "destination_root_identity_sha256": None,
                "destination_ancestor_identity_sha256": None,
                "destination_target_identity_sha256": None,
                "destination_pinned_readback_sha256": None,
            }
        ),
        "phase": phase.value,
        "event_count": len(parsed_events),
        "head_revision": len(parsed_events),
        "head_event_sha256": predecessor if parsed_events else None,
        "checkpoint_count": len(parsed_checkpoints),
        "last_checkpoint_receipt_sha256": previous_receipt_sha256,
        "terminal_receipt_sha256": (
            parsed_terminal["receipt_sha256"] if parsed_terminal is not None else None
        ),
        **current_inventory_fields,
        "active_lease_state": None,
        "read_back_at": _timestamp_text(readback_time),
        "fixture_only": True,
        "authority_created": False,
        "native_backend_observed": False,
        "private_handle_returned": False,
        "model_artifact_binding_created": False,
        "candidate_registered": False,
        "resource_effect_count": 0,
    }
    return Task084FixtureCustodyReadbackV1.from_dict(
        _with_digest(body, "readback_sha256", _FIXTURE_READBACK_DOMAIN)
    )


class Task084FixtureCustodyLedger:
    """Sealed in-memory fault fixture; never a production custody backend."""

    def __init__(self, plan: Task084OutputArtifactDestinationPlanV1) -> None:
        self._plan = plan
        self._lock = RLock()
        self._nonce = object()
        self._events: list[Task084FixtureCustodyEventV1] = []
        self._phase = CustodyPhase.PREPARED
        self._checkpoint_receipts: list[Task084FixtureModelCheckpointCustodyReceiptV1] = []
        self._terminal_receipt: Task084FixtureModelArtifactCustodyReceiptV1 | None = None
        self._active_write_lease: Task084FixtureModelArtifactWriteLeaseV1 | None = None
        self._write_leases_by_producer: dict[str, Task084FixtureModelArtifactWriteLeaseV1] = {}
        self._producer_prerequisites: dict[str, dict[str, Any]] = {}
        self._load_leases: dict[str, Task084FixtureModelLoadLeaseV1] = {}
        self._load_prerequisites: dict[tuple[LoadPurpose, str], dict[str, Any]] = {}
        self._load_request_index: dict[
            str, tuple[str, Task084FixtureModelLoadLeaseV1]
        ] = {}
        self._request_index: dict[str, str] = {}
        self._last_event_at = _timestamp_value(plan.to_dict()["compiled_at"])
        self._last_training_step = 0
        self._last_progress_ppm = 0
        self._negative_acknowledgements: dict[
            str, Task084FixtureDurableNegativeAcknowledgementV1
        ] = {}
        self._destination_identities: dict[str, str] | None = None
        self._last_task046_checkpoint_binding_sha256: str | None = None
        self._published_relative_files: set[str] = set()

    @property
    def phase(self) -> CustodyPhase:
        return self._phase

    @property
    def resource_effect_count(self) -> int:
        return 0

    @property
    def fixture_only(self) -> bool:
        return True

    def event_chain(self) -> tuple[Task084FixtureCustodyEventV1, ...]:
        with self._lock:
            return tuple(
                Task084FixtureCustodyEventV1.from_dict(event.to_dict())
                for event in self._events
            )

    def _request_duplicate(
        self, request_id: str, request_sha256: str, *, read_back_at: str
    ) -> Task084FixtureCustodyReadbackV1 | None:
        _identifier(request_id, "request_id")
        existing = self._request_index.get(request_id)
        if existing is None:
            return None
        if existing != request_sha256:
            raise ValueError("request replay payload mismatch")
        return self.readback(read_back_at=read_back_at)

    def _append_event(
        self,
        *,
        request_sha256: str,
        event_kind: str,
        event_at: str,
        producer_event_sha256: str | None = None,
        artifact_variant: ArtifactVariant | None = None,
        checkpoint_index: int | None = None,
        failed_lease_id: str | None = None,
        negative_acknowledgement_sha256: str | None = None,
        activation_identities: Mapping[str, str] | None = None,
    ) -> Task084FixtureCustodyEventV1:
        observed_at = _timestamp_value(event_at)
        if observed_at < self._last_event_at:
            raise ValueError("event time rollback")
        previous_variant = (
            self._active_write_lease._variant
            if self._active_write_lease is not None
            else None
        )
        target = _event_transition(
            self._phase,
            event_kind,
            previous_variant.value if previous_variant is not None else None,
        )
        revision = len(self._events) + 1
        predecessor = (
            self._events[-1].to_dict()["event_sha256"]
            if self._events
            else self._plan.to_dict()["plan_sha256"]
        )
        identities = (
            dict(activation_identities)
            if activation_identities is not None
            else copy.deepcopy(self._destination_identities)
        )
        if identities is None:
            raise ValueError("destination identity commitments are unavailable")
        body = {
            "record_type": "Task084FixtureCustodyEventV1",
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": CANONICAL_OWNER_TASK,
            "event_id": f"task084-event:{revision}",
            "plan_sha256": self._plan.to_dict()["plan_sha256"],
            **identities,
            "event_revision": revision,
            "predecessor_event_sha256": predecessor,
            "event_kind": event_kind,
            "phase": target.value,
            "request_sha256": request_sha256,
            "producer_event_sha256": producer_event_sha256,
            "artifact_variant": artifact_variant.value if artifact_variant else None,
            "checkpoint_index": checkpoint_index,
            "failed_lease_id": failed_lease_id,
            "negative_acknowledgement_sha256": negative_acknowledgement_sha256,
            "event_at": event_at,
            "fixture_only": True,
            "authority_created": False,
            "private_handle_returned": False,
            "resource_effect_count": 0,
        }
        event = Task084FixtureCustodyEventV1.from_dict(
            _with_digest(body, "event_sha256", _EVENT_DOMAIN)
        )
        self._events.append(event)
        self._phase = target
        self._last_event_at = observed_at
        return event

    def activate_destination(
        self,
        *,
        request_id: str,
        destination_root_identity_sha256: str,
        destination_ancestor_identity_sha256: str,
        destination_target_identity_sha256: str,
        destination_pinned_readback_sha256: str,
        observed_at: str,
    ) -> Task084FixtureCustodyEventV1 | Task084FixtureCustodyReadbackV1:
        with self._lock:
            request_body = {
                "destination_root_identity_sha256": _sha(
                    destination_root_identity_sha256, "destination_root_identity_sha256"
                ),
                "destination_ancestor_identity_sha256": _sha(
                    destination_ancestor_identity_sha256,
                    "destination_ancestor_identity_sha256",
                ),
                "destination_target_identity_sha256": _sha(
                    destination_target_identity_sha256, "destination_target_identity_sha256"
                ),
                "destination_pinned_readback_sha256": _sha(
                    destination_pinned_readback_sha256,
                    "destination_pinned_readback_sha256",
                ),
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("ACTIVATE_DESTINATION", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            event = self._append_event(
                request_sha256=request_digest,
                event_kind="DESTINATION_ACTIVATED",
                event_at=observed_at,
                activation_identities={
                    key: value for key, value in request_body.items() if key != "observed_at"
                },
            )
            self._destination_identities = {
                key: value for key, value in request_body.items() if key != "observed_at"
            }
            self._request_index[request_id] = request_digest
            return event

    def register_fixture_producer_event(
        self,
        *,
        producer_event_sha256: str,
        artifact_variant: str | ArtifactVariant,
        training_run_head_sha256: str,
        task043_job_readback_sha256: str,
        task043_job_head_sha256: str,
        observed_at: str,
        checkpoint_index: int | None = None,
        task046_checkpoint_binding_sha256: str | None = None,
        task046_terminal_receipt_sha256: str | None = None,
    ) -> None:
        """Register synthetic parent-event evidence without granting authority."""
        with self._lock:
            producer_digest = _sha(producer_event_sha256, "producer_event_sha256")
            variant = ArtifactVariant(artifact_variant)
            plan = self._plan.to_dict()
            current_bindings = {
                "training_run_head_sha256": _sha(
                    training_run_head_sha256, "training_run_head_sha256"
                ),
                "task043_job_readback_sha256": _sha(
                    task043_job_readback_sha256, "task043_job_readback_sha256"
                ),
                "task043_job_head_sha256": _sha(
                    task043_job_head_sha256, "task043_job_head_sha256"
                ),
            }
            if any(plan[field] != digest for field, digest in current_bindings.items()):
                raise ValueError("producer event current run/Job binding mismatch")
            observed = _timestamp_value(_timestamp(observed_at, "observed_at"))
            if observed < self._last_event_at:
                raise ValueError("producer event observation time rollback")
            if variant is ArtifactVariant.CHECKPOINT:
                expected_index = len(self._checkpoint_receipts) + 1
                if checkpoint_index != expected_index:
                    raise ValueError("producer checkpoint index must be current")
                if task046_terminal_receipt_sha256 is not None:
                    raise ValueError("checkpoint producer event forbids terminal receipt")
                checkpoint_binding = _sha(
                    task046_checkpoint_binding_sha256,
                    "task046_checkpoint_binding_sha256",
                )
            else:
                if self._phase is not CustodyPhase.CHECKPOINT_PUBLISHED:
                    raise ValueError("terminal producer event requires sealed checkpoint custody")
                if checkpoint_index is not None:
                    raise ValueError("terminal producer event forbids checkpoint_index")
                _sha(
                    task046_terminal_receipt_sha256,
                    "task046_terminal_receipt_sha256",
                )
                if task046_checkpoint_binding_sha256 is not None:
                    raise ValueError("terminal producer event derives the last checkpoint")
                checkpoint_binding = self._last_task046_checkpoint_binding_sha256
                if checkpoint_binding is None:
                    raise ValueError("terminal producer event requires TASK-046 checkpoint binding")
            if self._phase not in {
                CustodyPhase.DESTINATION_ACTIVE,
                CustodyPhase.CHECKPOINT_PUBLISHED,
            }:
                raise ValueError("custody phase cannot observe a producer event")
            if (
                producer_digest in self._producer_prerequisites
                or producer_digest in self._write_leases_by_producer
            ):
                raise ValueError("producer event prerequisite already registered")
            self._producer_prerequisites[producer_digest] = {
                "artifact_variant": variant,
                "checkpoint_index": checkpoint_index,
                "task046_checkpoint_binding_sha256": checkpoint_binding,
                "task046_terminal_receipt_sha256": task046_terminal_receipt_sha256,
                **current_bindings,
                "observed_at": observed,
                "expected_revision": len(self._events),
                "expected_head_sha256": self._events[-1].to_dict()["event_sha256"],
                "used": False,
            }

    def issue_write_lease(
        self,
        *,
        request_id: str,
        lease_id: str,
        producer_event_sha256: str,
        artifact_variant: str | ArtifactVariant,
        issued_at: str,
        expires_at: str,
        checkpoint_index: int | None = None,
        training_step: int | None = None,
        progress_ppm: int | None = None,
        task046_terminal_receipt: Mapping[str, Any] | TrainingComputeTerminalReceipt | None = None,
    ) -> Task084FixtureModelArtifactWriteLeaseV1 | Task084FixtureCustodyReadbackV1:
        with self._lock:
            variant = ArtifactVariant(artifact_variant)
            producer_digest = _sha(producer_event_sha256, "producer_event_sha256")
            issued = _timestamp_value(_timestamp(issued_at, "issued_at"))
            expires = _timestamp_value(_timestamp(expires_at, "expires_at"))
            terminal_digest: str | None = None
            terminal: dict[str, Any] | None = None
            if variant is ArtifactVariant.CHECKPOINT:
                if task046_terminal_receipt is not None:
                    raise ValueError("checkpoint lease forbids terminal receipt")
                _integer(
                    checkpoint_index,
                    "checkpoint_index",
                    minimum=1,
                    maximum=MAX_CHECKPOINT_INDEX,
                )
                _integer(training_step, "training_step", minimum=1)
                _integer(progress_ppm, "progress_ppm", minimum=0, maximum=1_000_000)
            else:
                if any(value is not None for value in (checkpoint_index, training_step, progress_ppm)):
                    raise ValueError("terminal lease forbids checkpoint-only fields")
                if task046_terminal_receipt is None:
                    raise ValueError("terminal lease requires TASK-046 terminal receipt")
                terminal = TrainingComputeTerminalReceipt.from_dict(
                    _mapping(task046_terminal_receipt, "task046_terminal_receipt")
                ).to_dict()
                terminal_digest = terminal["receipt_sha256"]
            request_body = {
                "lease_id": _identifier(lease_id, "lease_id"),
                "producer_event_sha256": producer_digest,
                "artifact_variant": variant.value,
                "checkpoint_index": checkpoint_index,
                "training_step": training_step,
                "progress_ppm": progress_ppm,
                "task046_terminal_receipt_sha256": terminal_digest,
                "issued_at": issued_at,
                "expires_at": expires_at,
            }
            request_digest = _request_sha256("ISSUE_WRITE_LEASE", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=issued_at
            )
            if duplicate is not None:
                return duplicate
            if expires <= issued or issued < self._last_event_at:
                raise ValueError("write lease lifetime/currentness mismatch")
            if variant is ArtifactVariant.CHECKPOINT:
                expected_index = len(self._checkpoint_receipts) + 1
                if checkpoint_index != expected_index:
                    raise ValueError("checkpoint index must be strictly monotonic")
                if training_step <= self._last_training_step:
                    raise ValueError("training step must be strictly monotonic")
                if progress_ppm < self._last_progress_ppm:
                    raise ValueError("checkpoint progress cannot roll back")
            else:
                if self._phase is not CustodyPhase.CHECKPOINT_PUBLISHED:
                    raise ValueError("terminal lease requires at least one sealed checkpoint")
                assert terminal is not None
                if terminal["compute_state"] != "COMPLETED" or terminal["artifact_registered"] is not False:
                    raise ValueError("terminal custody requires unregistered COMPLETED training result")
                if terminal["run_intent_sha256"] != self._plan.to_dict()["run_intent_sha256"]:
                    raise ValueError("terminal training run intent mismatch")
                if terminal["run_revision_sha256"] != self._plan.to_dict()[
                    "training_run_revision_sha256"
                ]:
                    raise ValueError("terminal training run revision/head mismatch")
                if terminal["job_binding_sha256"] != self._plan.to_dict()["job_binding_sha256"]:
                    raise ValueError("terminal training Job binding mismatch")
                if terminal["last_checkpoint_binding_sha256"] != (
                    self._last_task046_checkpoint_binding_sha256
                ):
                    raise ValueError("terminal last TASK-046 checkpoint binding mismatch")
                if _timestamp_value(terminal["started_at"]) > _timestamp_value(
                    terminal["terminal_at"]
                ):
                    raise ValueError("terminal training timestamps are reversed")
                if _timestamp_value(terminal["terminal_at"]) > issued:
                    raise ValueError("terminal receipt is from the future")
            if self._phase not in {
                CustodyPhase.DESTINATION_ACTIVE,
                CustodyPhase.CHECKPOINT_PUBLISHED,
            }:
                raise ValueError("custody phase cannot issue a write lease")
            prerequisite = self._producer_prerequisites.get(producer_digest)
            if prerequisite is None:
                raise ValueError("fixture producer event prerequisite was not observed")
            if prerequisite["used"]:
                raise ValueError("producer event prerequisite already has a child lease")
            if (
                prerequisite["artifact_variant"] is not variant
                or prerequisite["checkpoint_index"] != checkpoint_index
                or prerequisite["task046_terminal_receipt_sha256"] != terminal_digest
            ):
                raise ValueError("producer event prerequisite binding mismatch")
            if prerequisite["observed_at"] > issued:
                raise ValueError("write lease predates its producer event")
            if prerequisite["expected_revision"] != len(self._events) or (
                prerequisite["expected_head_sha256"]
                != self._events[-1].to_dict()["event_sha256"]
            ):
                raise ValueError("producer event prerequisite is stale")
            if self._active_write_lease is not None:
                raise ValueError("another write lease is active")
            if producer_digest in self._write_leases_by_producer:
                raise ValueError("producer event already has a child write lease")
            lease = Task084FixtureModelArtifactWriteLeaseV1(
                ledger_nonce=self._nonce,
                lease_id=lease_id,
                request_sha256=request_digest,
                producer_event_sha256=producer_digest,
                variant=variant,
                checkpoint_index=checkpoint_index,
                training_step=training_step,
                progress_ppm=progress_ppm,
                task046_checkpoint_binding_sha256=prerequisite[
                    "task046_checkpoint_binding_sha256"
                ],
                task046_terminal_receipt_sha256=terminal_digest,
                producer_observed_at=prerequisite["observed_at"],
                issued_at=issued_at,
                expires_at=expires_at,
                expected_revision=len(self._events),
                expected_head_sha256=self._events[-1].to_dict()["event_sha256"],
                key=_FACTORY_KEY,
            )
            self._write_leases_by_producer[producer_digest] = lease
            prerequisite["used"] = True
            self._active_write_lease = lease
            self._request_index[request_id] = request_digest
            return lease

    def begin_publish(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        *,
        request_id: str,
        observed_at: str,
    ) -> Task084FixtureCustodyEventV1 | Task084FixtureCustodyReadbackV1:
        with self._lock:
            self._require_write_lease(lease)
            request_body = {
                "lease_id": lease._lease_id,
                "expected_revision": lease._expected_revision,
                "expected_head_sha256": lease._expected_head_sha256,
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("BEGIN_PUBLISH", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if lease._state is not LeaseState.ISSUED:
                raise ValueError("write lease cannot be opened twice")
            observed = _timestamp_value(observed_at)
            if observed < _timestamp_value(lease._issued_at):
                raise ValueError("write lease cannot open before issuance")
            if observed >= _timestamp_value(lease._expires_at):
                lease._state = LeaseState.EXPIRED
                self._active_write_lease = None
                self._request_index[request_id] = request_digest
                return self.readback(read_back_at=observed_at)
            if len(self._events) != lease._expected_revision or (
                self._events[-1].to_dict()["event_sha256"] != lease._expected_head_sha256
            ):
                raise ValueError("write lease head/revision is stale")
            event = self._append_event(
                request_sha256=request_digest,
                event_kind=(
                    "CHECKPOINT_PUBLISH_STARTED"
                    if lease._variant is ArtifactVariant.CHECKPOINT
                    else "TERMINAL_PUBLISH_STARTED"
                ),
                event_at=observed_at,
                producer_event_sha256=lease._producer_event_sha256,
                artifact_variant=lease._variant,
                checkpoint_index=lease._checkpoint_index,
            )
            lease._state = LeaseState.OPEN_STARTED
            lease._publish_started_event_sha256 = event.to_dict()["event_sha256"]
            self._request_index[request_id] = request_digest
            return event

    def open_entry(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        *,
        entry_id: str,
    ) -> Task084FixtureEntryHandle:
        with self._lock:
            self._require_write_lease(lease)
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("entry open requires burned OPEN_STARTED lease")
            expected_field = (
                "checkpoint_expected_entries"
                if lease._variant is ArtifactVariant.CHECKPOINT
                else "terminal_expected_entries"
            )
            expected_ids = {item["entry_id"] for item in self._plan.to_dict()[expected_field]}
            _identifier(entry_id, "entry_id")
            if entry_id not in expected_ids:
                raise ValueError("entry is outside the closed allowlist")
            if entry_id in lease._entry_handles:
                raise ValueError("entry handle cannot be issued twice")
            handle = Task084FixtureEntryHandle(
                lease_id=lease._lease_id,
                entry_id=entry_id,
                nonce=object(),
                key=_FACTORY_KEY,
            )
            lease._entry_handles[entry_id] = handle
            return handle

    def complete_entry(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        handle: Task084FixtureEntryHandle,
        observation: Mapping[str, Any],
    ) -> None:
        with self._lock:
            self._require_write_lease(lease)
            if not isinstance(handle, Task084FixtureEntryHandle):
                raise ValueError("fixture entry handle is required")
            if handle._lease_id != lease._lease_id or lease._entry_handles.get(handle._entry_id) is not handle:
                raise ValueError("entry handle does not belong to this lease")
            if handle._closed:
                raise ValueError("entry handle cannot complete twice")
            parsed = _validate_file_observation(observation)
            if parsed["entry_id"] != handle._entry_id:
                raise ValueError("entry observation identity mismatch")
            expected_field = (
                "checkpoint_expected_entries"
                if lease._variant is ArtifactVariant.CHECKPOINT
                else "terminal_expected_entries"
            )
            expected = {
                item["entry_id"]: item for item in self._plan.to_dict()[expected_field]
            }[handle._entry_id]
            if (parsed["role"], parsed["index"]) != (expected["role"], expected["index"]):
                raise ValueError("entry observation role/index mismatch")
            handle._closed = True
            lease._entry_observations[handle._entry_id] = parsed

    def verify_manifest_last(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        inventory: Mapping[str, Any] | Task084FixtureArtifactInventoryV1,
    ) -> Task084FixtureManifestVerification:
        with self._lock:
            self._require_write_lease(lease)
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("manifest verification requires OPEN_STARTED lease")
            parsed = Task084FixtureArtifactInventoryV1.from_dict(
                _mapping(inventory, "inventory")
            ).to_dict()
            if parsed["plan_sha256"] != self._plan.to_dict()["plan_sha256"]:
                raise ValueError("inventory plan mismatch")
            if parsed["producer_event_sha256"] != lease._producer_event_sha256:
                raise ValueError("inventory producer event mismatch")
            if parsed["artifact_variant"] != lease._variant.value:
                raise ValueError("inventory artifact variant mismatch")
            if lease._variant is ArtifactVariant.CHECKPOINT:
                expected_namespace = _checkpoint_namespace_sha256(
                    self._plan.to_dict()["plan_sha256"],
                    lease._checkpoint_index,
                    lease._producer_event_sha256,
                )
                if (
                    parsed["checkpoint_index"] != lease._checkpoint_index
                    or parsed["checkpoint_namespace_sha256"] != expected_namespace
                ):
                    raise ValueError("checkpoint inventory namespace mismatch")
            elif (
                parsed["checkpoint_index"] is not None
                or parsed["checkpoint_namespace_sha256"] is not None
            ):
                raise ValueError("terminal inventory forbids checkpoint namespace")
            if self._destination_identities is None or any(
                parsed[field] != digest
                for field, digest in self._destination_identities.items()
            ):
                raise ValueError("inventory destination identity/readback binding mismatch")
            actual = sorted(
                lease._entry_observations.values(),
                key=lambda item: (item["index"], item["entry_id"]),
            )
            if parsed["entries"] != actual:
                raise ValueError("manifest inventory does not match completed entry handles")
            relative_files = {
                item["relative_file"].casefold() for item in parsed["entries"]
            }
            relative_files.add(parsed["manifest_relative_file"].casefold())
            if relative_files & self._published_relative_files:
                raise ValueError("published artifact relative path cannot be reused")
            expected_field = (
                "checkpoint_expected_entries"
                if lease._variant is ArtifactVariant.CHECKPOINT
                else "terminal_expected_entries"
            )
            if len(actual) != len(self._plan.to_dict()[expected_field]):
                raise ValueError("manifest cannot seal a partial entry set")
            return Task084FixtureManifestVerification(
                ledger_nonce=self._nonce,
                lease_id=lease._lease_id,
                inventory_sha256=parsed["inventory_sha256"],
                key=_FACTORY_KEY,
            )

    def complete_publish(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        inventory: Mapping[str, Any] | Task084FixtureArtifactInventoryV1,
        verification: Task084FixtureManifestVerification,
        *,
        request_id: str,
        task083_reservation_receipt_sha256: str,
        sealed_at: str,
    ) -> (
        Task084FixtureModelCheckpointCustodyReceiptV1
        | Task084FixtureModelArtifactCustodyReceiptV1
        | Task084FixtureCustodyReadbackV1
    ):
        with self._lock:
            self._require_write_lease(lease)
            parsed_inventory = Task084FixtureArtifactInventoryV1.from_dict(
                _mapping(inventory, "inventory")
            ).to_dict()
            request_body = {
                "lease_id": lease._lease_id,
                "inventory_sha256": parsed_inventory["inventory_sha256"],
                "task083_reservation_receipt_sha256": _sha(
                    task083_reservation_receipt_sha256,
                    "task083_reservation_receipt_sha256",
                ),
                "sealed_at": _timestamp(sealed_at, "sealed_at"),
            }
            request_digest = _request_sha256("COMPLETE_PUBLISH", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=sealed_at
            )
            if duplicate is not None:
                return duplicate
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("publish completion requires burned lease")
            sealed = _timestamp_value(sealed_at)
            if sealed < lease._producer_observed_at:
                raise ValueError("publish completion predates producer event")
            if sealed >= _timestamp_value(lease._expires_at):
                event = self._append_event(
                    request_sha256=request_digest,
                    event_kind="PUBLISH_COMPLETION_UNKNOWN",
                    event_at=sealed_at,
                    producer_event_sha256=lease._producer_event_sha256,
                    artifact_variant=lease._variant,
                    checkpoint_index=lease._checkpoint_index,
                )
                lease._state = LeaseState.COMPLETION_UNKNOWN
                self._active_write_lease = None
                self._request_index[request_id] = request_digest
                return self.readback(read_back_at=sealed_at)
            if (
                not isinstance(verification, Task084FixtureManifestVerification)
                or verification._ledger_nonce is not self._nonce
                or verification._lease_id != lease._lease_id
                or verification._inventory_sha256 != parsed_inventory["inventory_sha256"]
                or verification._used
            ):
                raise ValueError("ledger-issued manifest-last verification is required")
            if self._events[-1].to_dict()["event_sha256"] != lease._publish_started_event_sha256:
                raise ValueError("publish-start head changed")
            event = self._append_event(
                request_sha256=request_digest,
                event_kind=(
                    "CHECKPOINT_PUBLISHED"
                    if lease._variant is ArtifactVariant.CHECKPOINT
                    else "TERMINAL_SEALED"
                ),
                event_at=sealed_at,
                producer_event_sha256=lease._producer_event_sha256,
                artifact_variant=lease._variant,
                checkpoint_index=lease._checkpoint_index,
            )
            plan = self._plan.to_dict()
            previous_checkpoint = (
                self._checkpoint_receipts[-1].to_dict()["receipt_sha256"]
                if self._checkpoint_receipts
                else None
            )
            checkpoint_count = len(self._checkpoint_receipts) + (
                1 if lease._variant is ArtifactVariant.CHECKPOINT else 0
            )
            record_type = (
                "Task084FixtureModelCheckpointCustodyReceiptV1"
                if lease._variant is ArtifactVariant.CHECKPOINT
                else "Task084FixtureModelArtifactCustodyReceiptV1"
            )
            receipt_body = {
                "record_type": record_type,
                "schema_version": SCHEMA_VERSION,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "receipt_role": (
                    "MODEL_CHECKPOINT_CUSTODY"
                    if lease._variant is ArtifactVariant.CHECKPOINT
                    else "MODEL_ARTIFACT_CUSTODY"
                ),
                "receipt_id": f"task084-receipt:{len(self._events)}",
                "plan_sha256": plan["plan_sha256"],
                "project_id": plan["project_id"],
                "run_intent_sha256": plan["run_intent_sha256"],
                "training_run_revision_sha256": plan["training_run_revision_sha256"],
                "training_run_head_sha256": plan["training_run_head_sha256"],
                "job_binding_sha256": plan["job_binding_sha256"],
                "task043_job_readback_sha256": plan["task043_job_readback_sha256"],
                "task043_job_head_sha256": plan["task043_job_head_sha256"],
                "training_input_snapshot_sha256": plan["training_input_snapshot_sha256"],
                "recipe_revision_sha256": plan["recipe_revision_sha256"],
                "engine_admission_sha256": plan["engine_admission_sha256"],
                "base_model_sha256": plan["base_model_sha256"],
                "runtime_sha256": plan["runtime_sha256"],
                "code_sha256": plan["code_sha256"],
                "config_sha256": plan["config_sha256"],
                "current_consent_rights_license_sha256": plan[
                    "current_consent_rights_license_sha256"
                ],
                "task083_reservation_plan_sha256": plan[
                    "task083_reservation_plan_sha256"
                ],
                "task083_reservation_receipt_sha256": request_body[
                    "task083_reservation_receipt_sha256"
                ],
                "destination_coordinate_sha256": plan["destination_coordinate_sha256"],
                "destination_root_identity_sha256": parsed_inventory[
                    "destination_root_identity_sha256"
                ],
                "destination_ancestor_identity_sha256": parsed_inventory[
                    "destination_ancestor_identity_sha256"
                ],
                "destination_target_identity_sha256": parsed_inventory[
                    "destination_target_identity_sha256"
                ],
                "destination_pinned_readback_sha256": parsed_inventory[
                    "destination_pinned_readback_sha256"
                ],
                "custody_policy_sha256": plan["custody_policy_sha256"],
                "encryption_policy_sha256": plan["encryption_policy_sha256"],
                "cipher_backend_revision_sha256": plan[
                    "cipher_backend_revision_sha256"
                ],
                "principal_scope_sha256": plan["principal_scope_sha256"],
                "key_scope_sha256": plan["key_scope_sha256"],
                "dacl_policy_sha256": plan["dacl_policy_sha256"],
                "checkpoint_namespace_policy_sha256": plan[
                    "checkpoint_namespace_policy_sha256"
                ],
                "checkpoint_namespace_sha256": parsed_inventory[
                    "checkpoint_namespace_sha256"
                ],
                "producer_event_sha256": lease._producer_event_sha256,
                "event_revision": event.to_dict()["event_revision"],
                "predecessor_event_sha256": event.to_dict()[
                    "predecessor_event_sha256"
                ],
                "event_sha256": event.to_dict()["event_sha256"],
                "inventory_sha256": parsed_inventory["inventory_sha256"],
                "manifest_sha256": parsed_inventory["manifest_sha256"],
                "manifest_nonce_sha256": parsed_inventory["manifest_nonce_sha256"],
                "manifest_authentication_evidence_sha256": parsed_inventory[
                    "manifest_authentication_evidence_sha256"
                ],
                "manifest_envelope_evidence_sha256": parsed_inventory[
                    "manifest_envelope_evidence_sha256"
                ],
                "manifest_opened_physical_identity_sha256": parsed_inventory[
                    "manifest_opened_physical_identity_sha256"
                ],
                "manifest_ancestor_identity_sha256": parsed_inventory[
                    "manifest_ancestor_identity_sha256"
                ],
                "manifest_file_flush_evidence_sha256": parsed_inventory[
                    "manifest_file_flush_evidence_sha256"
                ],
                "manifest_directory_flush_evidence_sha256": parsed_inventory[
                    "manifest_directory_flush_evidence_sha256"
                ],
                "manifest_pinned_readback_sha256": parsed_inventory[
                    "manifest_pinned_readback_sha256"
                ],
                "opened_physical_identity_set_sha256": parsed_inventory[
                    "opened_physical_identity_set_sha256"
                ],
                "artifact_variant": lease._variant.value,
                "checkpoint_index": lease._checkpoint_index,
                "training_step": lease._training_step,
                "progress_ppm": lease._progress_ppm,
                "checkpoint_event_predecessor_sha256": (
                    lease._expected_head_sha256
                    if lease._variant is ArtifactVariant.CHECKPOINT
                    else None
                ),
                "task046_checkpoint_binding_sha256": lease._task046_checkpoint_binding_sha256,
                "task046_terminal_receipt_sha256": lease._task046_terminal_receipt_sha256,
                "last_checkpoint_receipt_sha256": (
                    previous_checkpoint
                    if lease._variant is ArtifactVariant.CHECKPOINT
                    else self._checkpoint_receipts[-1].to_dict()["receipt_sha256"]
                ),
                "checkpoint_count": checkpoint_count,
                "sealed_at": sealed_at,
                "fixture_only": True,
                "authority_created": False,
                "native_backend_invoked": False,
                "artifact_body_persisted": False,
                "private_handle_returned": False,
                "model_artifact_binding_created": False,
                "candidate_registered": False,
                "model_use_authorized": False,
                "production_use_authorized": False,
                "resource_effect_count": 0,
            }
            receipt_dict = _with_digest(
                receipt_body, "receipt_sha256", _receipt_domain(record_type)
            )
            if lease._variant is ArtifactVariant.CHECKPOINT:
                receipt = Task084FixtureModelCheckpointCustodyReceiptV1.from_dict(
                    receipt_dict
                )
                self._checkpoint_receipts.append(receipt)
                self._last_training_step = lease._training_step or 0
                self._last_progress_ppm = lease._progress_ppm or 0
                self._last_task046_checkpoint_binding_sha256 = (
                    lease._task046_checkpoint_binding_sha256
                )
            else:
                receipt = Task084FixtureModelArtifactCustodyReceiptV1.from_dict(
                    receipt_dict
                )
                self._terminal_receipt = receipt
            verification._used = True
            self._published_relative_files.update(
                item["relative_file"].casefold()
                for item in parsed_inventory["entries"]
            )
            self._published_relative_files.add(
                parsed_inventory["manifest_relative_file"].casefold()
            )
            lease._state = LeaseState.CONSUMED
            self._active_write_lease = None
            self._request_index[request_id] = request_digest
            return receipt

    def issue_durable_negative_acknowledgement(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        *,
        acknowledgement_id: str,
        observed_at: str,
    ) -> Task084FixtureDurableNegativeAcknowledgementV1:
        with self._lock:
            self._require_write_lease(lease)
            if lease._state is not LeaseState.OPEN_STARTED or lease._publish_started_event_sha256 is None:
                raise ValueError("negative acknowledgement requires burned publish lease")
            observed = _timestamp_value(_timestamp(observed_at, "observed_at"))
            if observed < self._last_event_at:
                raise ValueError("negative acknowledgement predates publish burn")
            body = {
                "record_type": "Task084FixtureDurableNegativeAcknowledgementV1",
                "schema_version": SCHEMA_VERSION,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "acknowledgement_id": _identifier(
                    acknowledgement_id, "acknowledgement_id"
                ),
                "plan_sha256": self._plan.to_dict()["plan_sha256"],
                "lease_id": lease._lease_id,
                "publish_started_event_sha256": lease._publish_started_event_sha256,
                "producer_event_sha256": lease._producer_event_sha256,
                "verified_no_visible_manifest": True,
                "verified_no_current_artifact_set": True,
                "observed_at": _timestamp_text(observed),
                "fixture_only": True,
                "authority_created": False,
                "resource_effect_count": 0,
            }
            acknowledgement = Task084FixtureDurableNegativeAcknowledgementV1.from_dict(
                _with_digest(body, "acknowledgement_sha256", _NEGATIVE_ACK_DOMAIN)
            )
            self._negative_acknowledgements[
                acknowledgement.to_dict()["acknowledgement_sha256"]
            ] = acknowledgement
            return acknowledgement

    def fail_closed_after_burn(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        acknowledgement: Mapping[str, Any] | Task084FixtureDurableNegativeAcknowledgementV1,
        *,
        request_id: str,
        observed_at: str,
    ) -> Task084FixtureCustodyEventV1 | Task084FixtureCustodyReadbackV1:
        with self._lock:
            self._require_write_lease(lease)
            ack = Task084FixtureDurableNegativeAcknowledgementV1.from_dict(
                _mapping(acknowledgement, "acknowledgement")
            ).to_dict()
            if self._negative_acknowledgements.get(ack["acknowledgement_sha256"]) is None:
                raise ValueError("ledger-issued durable negative acknowledgement required")
            if (
                ack["lease_id"] != lease._lease_id
                or ack["publish_started_event_sha256"] != lease._publish_started_event_sha256
                or ack["producer_event_sha256"] != lease._producer_event_sha256
            ):
                raise ValueError("negative acknowledgement binding mismatch")
            if _timestamp_value(ack["observed_at"]) > _timestamp_value(observed_at):
                raise ValueError("failure cannot predate durable negative acknowledgement")
            request_body = {
                "lease_id": lease._lease_id,
                "acknowledgement_sha256": ack["acknowledgement_sha256"],
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("FAIL_CLOSED_AFTER_BURN", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            event = self._append_event(
                request_sha256=request_digest,
                event_kind="FAILED_CLOSED",
                event_at=observed_at,
                producer_event_sha256=lease._producer_event_sha256,
                artifact_variant=lease._variant,
                checkpoint_index=lease._checkpoint_index,
                failed_lease_id=lease._lease_id,
                negative_acknowledgement_sha256=ack["acknowledgement_sha256"],
            )
            lease._state = LeaseState.FAILED_CLOSED
            self._active_write_lease = None
            self._request_index[request_id] = request_digest
            return event

    def mark_publish_completion_unknown(
        self,
        lease: Task084FixtureModelArtifactWriteLeaseV1,
        *,
        request_id: str,
        observed_at: str,
    ) -> Task084FixtureCustodyEventV1 | Task084FixtureCustodyReadbackV1:
        with self._lock:
            self._require_write_lease(lease)
            request_body = {
                "lease_id": lease._lease_id,
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("PUBLISH_COMPLETION_UNKNOWN", request_body)
            duplicate = self._request_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("completion unknown requires burned publish lease")
            event = self._append_event(
                request_sha256=request_digest,
                event_kind="PUBLISH_COMPLETION_UNKNOWN",
                event_at=observed_at,
                producer_event_sha256=lease._producer_event_sha256,
                artifact_variant=lease._variant,
                checkpoint_index=lease._checkpoint_index,
            )
            lease._state = LeaseState.COMPLETION_UNKNOWN
            self._active_write_lease = None
            self._request_index[request_id] = request_digest
            return event

    def register_fixture_current_load_bindings(
        self,
        *,
        purpose: str | LoadPurpose,
        bindings: Mapping[str, str],
        observed_at: str,
    ) -> None:
        """Pin one synthetic current-lineage snapshot for a future fixture load."""
        with self._lock:
            selected = LoadPurpose(purpose)
            parsed_bindings = _validate_load_bindings(selected, bindings)
            if selected is LoadPurpose.TRAINING_RESUME:
                if not self._checkpoint_receipts:
                    raise ValueError("TRAINING_RESUME requires checkpoint custody")
                expected = self._checkpoint_receipts[-1].to_dict()["receipt_sha256"]
                if parsed_bindings["checkpoint_custody_receipt_sha256"] != expected:
                    raise ValueError("resume checkpoint custody mismatch")
            else:
                if self._terminal_receipt is None:
                    raise ValueError("terminal load purpose requires sealed terminal custody")
                expected = self._terminal_receipt.to_dict()["receipt_sha256"]
                if parsed_bindings["terminal_custody_receipt_sha256"] != expected:
                    raise ValueError("terminal custody receipt mismatch")
            observed = _timestamp_value(_timestamp(observed_at, "observed_at"))
            if observed < self._last_event_at:
                raise ValueError("load prerequisite observation time rollback")
            binding_digest = sha256_bytes(
                b"BAI:TASK-084:FIXTURE-LOAD-BINDINGS:V1\x00"
                + canonical_json_bytes(parsed_bindings)
            )
            key = (selected, binding_digest)
            if key in self._load_prerequisites:
                raise ValueError("fixture current load bindings already registered")
            self._load_prerequisites[key] = {
                "observed_at": observed,
                "expected_revision": len(self._events),
                "expected_head_sha256": self._events[-1].to_dict()["event_sha256"],
                "used": False,
            }

    def _load_duplicate(
        self,
        request_id: str,
        request_sha256: str,
        *,
        read_back_at: str,
    ) -> Task084FixtureModelLoadReadbackV1 | None:
        _identifier(request_id, "request_id")
        existing = self._load_request_index.get(request_id)
        if existing is None:
            return None
        existing_sha256, lease = existing
        if existing_sha256 != request_sha256:
            raise ValueError("load request replay payload mismatch")
        return self.fixture_load_readback(lease, read_back_at=read_back_at)

    def fixture_load_readback(
        self,
        lease: Task084FixtureModelLoadLeaseV1,
        *,
        read_back_at: str,
    ) -> Task084FixtureModelLoadReadbackV1:
        with self._lock:
            self._require_load_lease(lease)
            candidate = _timestamp_value(_timestamp(read_back_at, "read_back_at"))
            floor = max(
                self._last_event_at,
                _timestamp_value(lease._issued_at),
                lease._opened_at or _timestamp_value(lease._issued_at),
            )
            body = {
                "record_type": "Task084FixtureModelLoadReadbackV1",
                "schema_version": SCHEMA_VERSION,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "plan_sha256": self._plan.to_dict()["plan_sha256"],
                "lease_id": lease._lease_id,
                "purpose": lease._purpose.value,
                "bindings_sha256": lease._bindings_sha256,
                "state": lease._state.value,
                "expected_head_revision": lease._expected_revision,
                "expected_head_sha256": lease._expected_head_sha256,
                "load_handle_identity_sha256": (
                    lease._open_handle._handle_identity_sha256
                    if lease._open_handle is not None
                    else None
                ),
                "completion_verification_sha256": (
                    lease._completion_verification_sha256
                ),
                "issued_at": lease._issued_at,
                "expires_at": lease._expires_at,
                "read_back_at": _timestamp_text(max(candidate, floor)),
                "fixture_only": True,
                "authority_created": False,
                "private_handle_returned": False,
                "model_loaded": False,
                "resource_effect_count": 0,
            }
            return Task084FixtureModelLoadReadbackV1.from_dict(
                _with_digest(body, "readback_sha256", _FIXTURE_LOAD_READBACK_DOMAIN)
            )

    def issue_fixture_load_lease(
        self,
        *,
        request_id: str,
        lease_id: str,
        purpose: str | LoadPurpose,
        bindings: Mapping[str, str],
        issued_at: str,
        expires_at: str,
    ) -> Task084FixtureModelLoadLeaseV1 | Task084FixtureModelLoadReadbackV1:
        with self._lock:
            selected = LoadPurpose(purpose)
            parsed_bindings = _validate_load_bindings(selected, bindings)
            issued = _timestamp_value(_timestamp(issued_at, "issued_at"))
            expires = _timestamp_value(_timestamp(expires_at, "expires_at"))
            binding_digest = sha256_bytes(
                b"BAI:TASK-084:FIXTURE-LOAD-BINDINGS:V1\x00"
                + canonical_json_bytes(parsed_bindings)
            )
            request_body = {
                "lease_id": _identifier(lease_id, "lease_id"),
                "purpose": selected.value,
                "bindings_sha256": binding_digest,
                "issued_at": issued_at,
                "expires_at": expires_at,
            }
            request_digest = _request_sha256("ISSUE_FIXTURE_LOAD_LEASE", request_body)
            duplicate = self._load_duplicate(
                request_id, request_digest, read_back_at=issued_at
            )
            if duplicate is not None:
                return duplicate
            if selected is LoadPurpose.TRAINING_RESUME:
                if not self._checkpoint_receipts:
                    raise ValueError("TRAINING_RESUME requires checkpoint custody")
                expected = self._checkpoint_receipts[-1].to_dict()["receipt_sha256"]
                if parsed_bindings["checkpoint_custody_receipt_sha256"] != expected:
                    raise ValueError("resume checkpoint custody mismatch")
            else:
                if self._terminal_receipt is None:
                    raise ValueError("terminal load purpose requires sealed terminal custody")
                expected = self._terminal_receipt.to_dict()["receipt_sha256"]
                if parsed_bindings["terminal_custody_receipt_sha256"] != expected:
                    raise ValueError("terminal custody receipt mismatch")
            if expires <= issued or issued < self._last_event_at:
                raise ValueError("load lease lifetime/currentness mismatch")
            prerequisite = self._load_prerequisites.get((selected, binding_digest))
            if prerequisite is None:
                raise ValueError("fixture current load bindings were not registered")
            if prerequisite["used"]:
                raise ValueError("fixture current load bindings were already consumed")
            if prerequisite["observed_at"] > issued:
                raise ValueError("load lease predates its current-lineage snapshot")
            if prerequisite["expected_revision"] != len(self._events) or (
                prerequisite["expected_head_sha256"]
                != self._events[-1].to_dict()["event_sha256"]
            ):
                raise ValueError("fixture current load bindings are stale")
            if lease_id in self._load_leases:
                raise ValueError("load lease id already exists")
            lease = Task084FixtureModelLoadLeaseV1(
                ledger_nonce=self._nonce,
                lease_id=lease_id,
                purpose=selected,
                bindings_sha256=binding_digest,
                issued_at=issued_at,
                expires_at=expires_at,
                expected_revision=len(self._events),
                expected_head_sha256=self._events[-1].to_dict()["event_sha256"],
                key=_FACTORY_KEY,
            )
            self._load_leases[lease_id] = lease
            prerequisite["used"] = True
            self._load_request_index[request_id] = (request_digest, lease)
            return lease

    def begin_fixture_load(
        self,
        lease: Task084FixtureModelLoadLeaseV1,
        *,
        request_id: str,
        observed_at: str,
    ) -> Task084FixtureModelLoadOpenHandle | Task084FixtureModelLoadReadbackV1:
        with self._lock:
            self._require_load_lease(lease)
            request_body = {
                "lease_id": lease._lease_id,
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("BEGIN_FIXTURE_LOAD", request_body)
            duplicate = self._load_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if lease._state is not LeaseState.ISSUED:
                raise ValueError("load lease cannot be opened twice")
            observed = _timestamp_value(_timestamp(observed_at, "observed_at"))
            if observed < _timestamp_value(lease._issued_at):
                raise ValueError("load lease cannot open before issuance")
            if observed >= _timestamp_value(lease._expires_at):
                lease._state = LeaseState.EXPIRED
                self._load_request_index[request_id] = (request_digest, lease)
                return self.fixture_load_readback(lease, read_back_at=observed_at)
            if len(self._events) != lease._expected_revision or (
                self._events[-1].to_dict()["event_sha256"]
                != lease._expected_head_sha256
            ):
                raise ValueError("load lease custody head is stale")
            lease._state = LeaseState.OPEN_STARTED
            lease._opened_at = observed
            handle_identity_sha256 = sha256_bytes(
                _FIXTURE_LOAD_HANDLE_DOMAIN
                + canonical_json_bytes(
                    {
                        "plan_sha256": self._plan.to_dict()["plan_sha256"],
                        "lease_id": lease._lease_id,
                        "bindings_sha256": lease._bindings_sha256,
                        "begin_request_sha256": request_digest,
                    }
                )
            )
            handle = Task084FixtureModelLoadOpenHandle(
                ledger_nonce=self._nonce,
                lease_id=lease._lease_id,
                handle_identity_sha256=handle_identity_sha256,
                opened_at=observed,
                key=_FACTORY_KEY,
            )
            lease._open_handle = handle
            self._load_request_index[request_id] = (request_digest, lease)
            return handle

    def observe_fixture_load_completion(
        self,
        lease: Task084FixtureModelLoadLeaseV1,
        handle: Task084FixtureModelLoadOpenHandle,
        *,
        close_identity_sha256: str,
        completion_readback_sha256: str,
        zeroization_evidence_sha256: str,
        observed_at: str,
    ) -> Task084FixtureModelLoadCompletionVerification:
        """Mint one fixture-only close proof bound to the exact opened handle."""
        with self._lock:
            self._require_load_lease(lease)
            if (
                not isinstance(handle, Task084FixtureModelLoadOpenHandle)
                or handle._ledger_nonce is not self._nonce
                or lease._open_handle is not handle
                or handle._lease_id != lease._lease_id
            ):
                raise ValueError("fixture load handle does not belong to this lease")
            if lease._state is not LeaseState.OPEN_STARTED or handle._used:
                raise ValueError("fixture load handle is not open and unused")
            close_identity = _sha(close_identity_sha256, "close_identity_sha256")
            if close_identity != handle._handle_identity_sha256:
                raise ValueError("load close identity does not match opened handle")
            completion_readback = _sha(
                completion_readback_sha256, "completion_readback_sha256"
            )
            zeroization = _sha(
                zeroization_evidence_sha256, "zeroization_evidence_sha256"
            )
            observed = _timestamp_value(_timestamp(observed_at, "observed_at"))
            if observed < handle._opened_at:
                raise ValueError("load completion observation predates load open")
            if len(self._events) != lease._expected_revision or (
                self._events[-1].to_dict()["event_sha256"]
                != lease._expected_head_sha256
            ):
                raise ValueError("load completion observation custody head is stale")
            verification_body = {
                "plan_sha256": self._plan.to_dict()["plan_sha256"],
                "lease_id": lease._lease_id,
                "bindings_sha256": lease._bindings_sha256,
                "handle_identity_sha256": handle._handle_identity_sha256,
                "close_identity_sha256": close_identity,
                "completion_readback_sha256": completion_readback,
                "zeroization_evidence_sha256": zeroization,
                "observed_at": _timestamp_text(observed),
            }
            verification_sha256 = sha256_bytes(
                _FIXTURE_LOAD_COMPLETION_DOMAIN
                + canonical_json_bytes(verification_body)
            )
            verification = Task084FixtureModelLoadCompletionVerification(
                ledger_nonce=self._nonce,
                lease_id=lease._lease_id,
                handle_identity_sha256=handle._handle_identity_sha256,
                close_identity_sha256=close_identity,
                completion_readback_sha256=completion_readback,
                zeroization_evidence_sha256=zeroization,
                observed_at=observed,
                verification_sha256=verification_sha256,
                key=_FACTORY_KEY,
            )
            handle._used = True
            lease._completion_verification_sha256 = verification_sha256
            return verification

    def complete_fixture_load(
        self,
        lease: Task084FixtureModelLoadLeaseV1,
        verification: Task084FixtureModelLoadCompletionVerification,
        *,
        request_id: str,
        completed_at: str,
    ) -> Task084FixtureModelLoadReadbackV1:
        with self._lock:
            self._require_load_lease(lease)
            request_body = {
                "lease_id": lease._lease_id,
                "completion_verification_sha256": (
                    verification._verification_sha256
                    if isinstance(
                        verification, Task084FixtureModelLoadCompletionVerification
                    )
                    else None
                ),
                "completed_at": _timestamp(completed_at, "completed_at"),
            }
            request_digest = _request_sha256("COMPLETE_FIXTURE_LOAD", request_body)
            duplicate = self._load_duplicate(
                request_id, request_digest, read_back_at=completed_at
            )
            if duplicate is not None:
                return duplicate
            if (
                not isinstance(
                    verification, Task084FixtureModelLoadCompletionVerification
                )
                or verification._ledger_nonce is not self._nonce
                or verification._lease_id != lease._lease_id
                or lease._completion_verification_sha256
                != verification._verification_sha256
                or lease._open_handle is None
                or verification._handle_identity_sha256
                != lease._open_handle._handle_identity_sha256
                or verification._close_identity_sha256
                != lease._open_handle._handle_identity_sha256
                or verification._used
            ):
                raise ValueError("ledger-issued exact load completion verification is required")
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("load completion requires OPEN_STARTED lease")
            completed = _timestamp_value(completed_at)
            if completed < verification._observed_at:
                raise ValueError("load completion predates completion verification")
            if len(self._events) != lease._expected_revision or (
                self._events[-1].to_dict()["event_sha256"]
                != lease._expected_head_sha256
            ):
                raise ValueError("load completion custody head is stale")
            if completed >= _timestamp_value(lease._expires_at):
                lease._state = LeaseState.COMPLETION_UNKNOWN
                verification._used = True
                self._load_request_index[request_id] = (request_digest, lease)
                return self.fixture_load_readback(lease, read_back_at=completed_at)
            lease._state = LeaseState.CONSUMED
            verification._used = True
            self._load_request_index[request_id] = (request_digest, lease)
            return self.fixture_load_readback(lease, read_back_at=completed_at)

    def mark_fixture_load_completion_unknown(
        self,
        lease: Task084FixtureModelLoadLeaseV1,
        *,
        request_id: str,
        observed_at: str,
    ) -> Task084FixtureModelLoadReadbackV1:
        with self._lock:
            self._require_load_lease(lease)
            request_body = {
                "lease_id": lease._lease_id,
                "observed_at": _timestamp(observed_at, "observed_at"),
            }
            request_digest = _request_sha256("FIXTURE_LOAD_COMPLETION_UNKNOWN", request_body)
            duplicate = self._load_duplicate(
                request_id, request_digest, read_back_at=observed_at
            )
            if duplicate is not None:
                return duplicate
            if lease._state is not LeaseState.OPEN_STARTED:
                raise ValueError("load ambiguity requires OPEN_STARTED lease")
            observed = _timestamp_value(observed_at)
            if lease._opened_at is None or observed < lease._opened_at:
                raise ValueError("load ambiguity predates load open")
            lease._state = LeaseState.COMPLETION_UNKNOWN
            self._load_request_index[request_id] = (request_digest, lease)
            return self.fixture_load_readback(lease, read_back_at=observed_at)

    def readback(
        self,
        *,
        read_back_at: str,
        current_terminal_inventory: (
            Mapping[str, Any] | Task084FixtureArtifactInventoryV1 | None
        ) = None,
    ) -> Task084FixtureCustodyReadbackV1:
        with self._lock:
            candidate = _timestamp_value(_timestamp(read_back_at, "read_back_at"))
            monotonic = max(candidate, self._last_event_at)
            current_inventory_fields = _empty_current_inventory_readback()
            if current_terminal_inventory is not None:
                if self._terminal_receipt is None:
                    raise ValueError("current terminal inventory requires sealed custody")
                parsed_current_inventory = Task084FixtureArtifactInventoryV1.from_dict(
                    _mapping(current_terminal_inventory, "current_terminal_inventory")
                ).to_dict()
                _validate_current_inventory_against_receipt(
                    parsed_current_inventory, self._terminal_receipt.to_dict()
                )
                current_inventory_fields = _current_inventory_readback(
                    parsed_current_inventory, observed_at=_timestamp_text(monotonic)
                )
            active_state = (
                self._active_write_lease._state.value
                if self._active_write_lease is not None
                else None
            )
            body = {
                "record_type": "Task084FixtureCustodyReadbackV1",
                "schema_version": SCHEMA_VERSION,
                "canonical_owner_task": CANONICAL_OWNER_TASK,
                "plan_sha256": self._plan.to_dict()["plan_sha256"],
                "destination_root_identity_sha256": (
                    self._destination_identities["destination_root_identity_sha256"]
                    if self._destination_identities is not None
                    else None
                ),
                "destination_ancestor_identity_sha256": (
                    self._destination_identities["destination_ancestor_identity_sha256"]
                    if self._destination_identities is not None
                    else None
                ),
                "destination_target_identity_sha256": (
                    self._destination_identities["destination_target_identity_sha256"]
                    if self._destination_identities is not None
                    else None
                ),
                "destination_pinned_readback_sha256": (
                    self._destination_identities["destination_pinned_readback_sha256"]
                    if self._destination_identities is not None
                    else None
                ),
                "phase": self._phase.value,
                "event_count": len(self._events),
                "head_revision": len(self._events),
                "head_event_sha256": (
                    self._events[-1].to_dict()["event_sha256"]
                    if self._events
                    else None
                ),
                "checkpoint_count": len(self._checkpoint_receipts),
                "last_checkpoint_receipt_sha256": (
                    self._checkpoint_receipts[-1].to_dict()["receipt_sha256"]
                    if self._checkpoint_receipts
                    else None
                ),
                "terminal_receipt_sha256": (
                    self._terminal_receipt.to_dict()["receipt_sha256"]
                    if self._terminal_receipt is not None
                    else None
                ),
                **current_inventory_fields,
                "active_lease_state": active_state,
                "read_back_at": _timestamp_text(monotonic),
                "fixture_only": True,
                "authority_created": False,
                "native_backend_observed": False,
                "private_handle_returned": False,
                "model_artifact_binding_created": False,
                "candidate_registered": False,
                "resource_effect_count": 0,
            }
            return Task084FixtureCustodyReadbackV1.from_dict(
                _with_digest(body, "readback_sha256", _FIXTURE_READBACK_DOMAIN)
            )

    def _require_write_lease(self, lease: Task084FixtureModelArtifactWriteLeaseV1) -> None:
        if (
            not isinstance(lease, Task084FixtureModelArtifactWriteLeaseV1)
            or lease._ledger_nonce is not self._nonce
            or self._write_leases_by_producer.get(lease._producer_event_sha256) is not lease
        ):
            raise ValueError("write lease does not belong to this fixture ledger")

    def _require_load_lease(self, lease: Task084FixtureModelLoadLeaseV1) -> None:
        if (
            not isinstance(lease, Task084FixtureModelLoadLeaseV1)
            or lease._ledger_nonce is not self._nonce
            or self._load_leases.get(lease._lease_id) is not lease
        ):
            raise ValueError("load lease does not belong to this fixture ledger")


def open_fixture_custody(
    plan: Mapping[str, Any] | Task084OutputArtifactDestinationPlanV1,
) -> Task084FixtureCustodyLedger:
    parsed = Task084OutputArtifactDestinationPlanV1.from_dict(
        _mapping(plan, "plan")
    )
    return Task084FixtureCustodyLedger(parsed)


def validate_terminal_custody_for_model_artifact_binding(
    receipt: Mapping[str, Any] | Task084ModelArtifactCustodyReceiptV1,
    readback: Mapping[str, Any] | Task084CustodyReadbackV1,
) -> None:
    parsed_receipt = Task084ModelArtifactCustodyReceiptV1.from_dict(
        _mapping(receipt, "terminal custody receipt")
    ).to_dict()
    parsed_readback = Task084CustodyReadbackV1.from_dict(
        _mapping(readback, "terminal custody readback")
    ).to_dict()
    direct_bindings = {
        "plan_sha256": "plan_sha256",
        "destination_root_identity_sha256": "destination_root_identity_sha256",
        "destination_ancestor_identity_sha256": "destination_ancestor_identity_sha256",
        "destination_target_identity_sha256": "destination_target_identity_sha256",
        "destination_pinned_readback_sha256": "destination_pinned_readback_sha256",
        "terminal_receipt_sha256": "receipt_sha256",
    }
    current_bindings = _CURRENT_INVENTORY_TO_RECEIPT
    if any(
        parsed_readback[readback_field] != parsed_receipt[receipt_field]
        for readback_field, receipt_field in {
            **direct_bindings,
            **current_bindings,
        }.items()
    ):
        raise ValueError("terminal receipt/readback mismatch")
    if parsed_readback["current_inventory_observed_at"] is None:
        raise ValueError("terminal custody readback lacks current physical observation")
    raise RuntimeError("TASK046_CUSTODY_AWARE_CONSUMER_NOT_AVAILABLE_CURRENT_SOURCE")


def assert_effect_zero_surface(value: Any) -> None:
    if isinstance(value, _EphemeralFixtureObject):
        if value.resource_effect_count != 0 or value.private_handle_returned is not False:
            raise ValueError("fixture ephemeral surface exceeded effect-0")
        return
    body = _mapping(value, "effect surface")
    if body.get("resource_effect_count") != 0:
        raise ValueError("surface is not effect-0")
    for field in (
        "authority_created",
        "destination_activated",
        "write_lease_created",
        "load_lease_created",
        "native_backend_invoked",
        "private_handle_returned",
        "model_artifact_binding_created",
        "candidate_registered",
        "training_started",
        "model_loaded",
        "model_use_authorized",
        "production_use_authorized",
    ):
        if field in body and body[field] is not False:
            raise ValueError(f"{field} exceeded effect-0")


__all__ = [
    "ArtifactVariant",
    "APPROVED_AEAD_SUITES",
    "CANONICAL_OWNER_TASK",
    "CustodyPhase",
    "LeaseState",
    "LoadPurpose",
    "MINIMUM_CHECKPOINTS_BEFORE_TERMINAL",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "Task084CustodyReadbackV1",
    "Task084FixtureArtifactInventoryV1",
    "Task084FixtureCustodyEventV1",
    "Task084FixtureCustodyLedger",
    "Task084FixtureCustodyReadbackV1",
    "Task084FixtureDurableNegativeAcknowledgementV1",
    "Task084FixtureEntryHandle",
    "Task084FixtureModelArtifactCustodyReceiptV1",
    "Task084FixtureModelArtifactWriteLeaseV1",
    "Task084FixtureModelCheckpointCustodyReceiptV1",
    "Task084FixtureModelLoadCompletionVerification",
    "Task084FixtureModelLoadLeaseV1",
    "Task084FixtureModelLoadOpenHandle",
    "Task084FixtureModelLoadReadbackV1",
    "Task084ModelArtifactCustodyReceiptV1",
    "Task084ModelCheckpointCustodyReceiptV1",
    "Task084ModelLoadAdmissionV1",
    "Task084OutputArtifactDestinationPlanV1",
    "Task084ProductionCustodyAdmissionV1",
    "assert_effect_zero_surface",
    "compile_fixture_inventory",
    "compile_model_load_admission",
    "compile_output_artifact_destination_plan",
    "compile_production_custody_admission",
    "open_fixture_custody",
    "parse_security_json",
    "replay_fixture_event_chain",
    "replay_fixture_custody",
    "validate_record",
    "validate_terminal_custody_for_model_artifact_binding",
]
