"""TASK-058 P0 montage-learning bridge admission contracts.

This module is deterministic for the same admitted inputs and performs no
external or mutable I/O. It may invoke the existing TASK-055 admission
contract, which lazily reads packaged immutable JSON Schemas through
``importlib.resources``. It never writes a filesystem/store, reads external
mutable files, accesses a network/database/media source, starts a native
application, mints a receipt, or creates runtime/canonical authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
from math import gcd
import re

from .montage_contracts import (
    MontageContractError,
    admit_montage_human_edit_evidence,
)


EXACT_SCHEMA_VERSION = "1.0.0"
EXACT_MESSAGE_TYPE = "BvpMontageExactEvidenceDelivery"
EXACT_CONTRACT_PROFILE = "bvp-task058-montage-exact-evidence-v1"

GENERIC_SCHEMA_VERSION = "1.0.0"
GENERIC_MESSAGE_TYPE = "BvpMontageLearningDelivery"
GENERIC_CONTRACT_PROFILE = "bvp-task029-file-bridge-v1"
GENERIC_PAYLOAD_MESSAGE_TYPE = "MontageLearningExport"

EXACT_LINEAGE_VERIFIED = "EXACT_LINEAGE_VERIFIED"
OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE = (
    "OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE"
)
OWNER_SCOPE_UNBOUND = "OWNER_SCOPE_UNBOUND"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_REDACTED = "[REDACTED]"
_FORBIDDEN_KEY_SUBSTRINGS = (
    "path",
    "filename",
    "account",
    "player",
    "email",
    "transcript",
    "token",
    "secret",
    "password",
    "credential",
    "username",
    "display_name",
    "real_name",
)
_VALIDATION_KEYS = frozenset({"planning", "static", "package", "runtime"})
_VALIDATION_VALUES = frozenset(
    {"NOT_RUN", "NOT_TESTED", "PARTIAL", "PASS", "FAIL", "REVIEW"}
)
_RESULT_VALUES = frozenset(
    {
        "accepted",
        "accepted_with_adjustment",
        "rejected",
        "moved",
        "deleted",
        "replaced",
    }
)

_EXACT_FIELDS = frozenset(
    {
        "schema_version",
        "message_type",
        "contract_profile",
        "record_id",
        "proposal_sha256",
        "approved_plan_sha256",
        "evidence_sha256",
        "owner_scope_hash",
        "canonical_timeline",
        "auto_admit_authorized",
        "proposal",
        "approved_plan",
        "human_edit_evidence",
        "authority_flags",
        "effect_flags",
    }
)
_GENERIC_FIELDS = frozenset(
    {
        "schema_version",
        "message_type",
        "contract_profile",
        "record_id",
        "learning_sha256",
        "canonical_timeline",
        "auto_admit_authorized",
        "payload",
    }
)
_AUTHORITY_FIELDS = frozenset(
    {
        "exact_lineage_is_canonical_admission",
        "canonical_store_write_authorized",
        "automatic_learning_promotion_authorized",
        "timeline_mutation_authorized",
        "resolve_write_authorized",
        "receipt_mint_authorized",
    }
)
_EFFECT_FIELDS = frozenset(
    {
        "filesystem_written",
        "network_accessed",
        "database_accessed",
        "native_application_started",
        "canonical_store_written",
        "receipt_minted",
    }
)


class MontageLearningBridgeContractError(ValueError):
    """Raised when an untrusted bridge envelope is not exactly admissible."""


@dataclass(frozen=True, slots=True)
class MontageLearningBridgeCandidate:
    """Body-free, non-authoritative result of P0 validation."""

    lane: str
    record_id: str
    source_sha256: str
    validation_state: str
    owner_scope_state: str
    review_state: str
    runtime_observation_state: str

    def to_dict(self) -> dict[str, object]:
        """Return a fresh JSON-serializable body-free projection."""

        return {
            "lane": self.lane,
            "record_id": self.record_id,
            "source_sha256": self.source_sha256,
            "validation_state": self.validation_state,
            "owner_scope_state": self.owner_scope_state,
            "review_state": self.review_state,
            "runtime_observation_state": self.runtime_observation_state,
            "canonical_timeline": False,
            "canonical_admission_authorized": False,
            "canonical_store_write_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "runtime_authority_created": False,
            "receipt_minted": False,
        }


def canonical_learning_sha256(payload: Mapping[str, object]) -> str:
    """Return the SKILL-compatible canonical SHA-256 for a learning payload."""

    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MontageLearningBridgeContractError(
            "payload must be canonical JSON data"
        ) from exc
    return f"sha256:{sha256(encoded).hexdigest()}"


def validate_exact_evidence_delivery(
    value: Mapping[str, object],
    *,
    expected_owner_scope_hash: str,
) -> MontageLearningBridgeCandidate:
    """Validate embedded TASK-055 lineage without admitting it canonically."""

    envelope = _require_mapping(value, name="exact delivery")
    _require_exact_fields(envelope, _EXACT_FIELDS, name="exact delivery")
    _require_equal(envelope, "schema_version", EXACT_SCHEMA_VERSION)
    _require_equal(envelope, "message_type", EXACT_MESSAGE_TYPE)
    _require_equal(envelope, "contract_profile", EXACT_CONTRACT_PROFILE)
    record_id = _require_record_id(envelope, "record_id")
    _require_false(envelope, "canonical_timeline")
    _require_false(envelope, "auto_admit_authorized")

    expected_scope = _require_sha256_value(
        expected_owner_scope_hash, name="expected_owner_scope_hash"
    )
    actual_scope = _require_sha256(envelope, "owner_scope_hash")
    if actual_scope != expected_scope:
        raise MontageLearningBridgeContractError("owner_scope_hash mismatch")

    proposal = _require_mapping(envelope["proposal"], name="proposal")
    approved_plan = _require_mapping(
        envelope["approved_plan"], name="approved_plan"
    )
    evidence = _require_mapping(
        envelope["human_edit_evidence"], name="human_edit_evidence"
    )
    proposal_sha = _require_sha256(envelope, "proposal_sha256")
    plan_sha = _require_sha256(envelope, "approved_plan_sha256")
    evidence_sha = _require_sha256(envelope, "evidence_sha256")
    if proposal.get("proposal_sha256") != proposal_sha:
        raise MontageLearningBridgeContractError("proposal_sha256 mismatch")
    if approved_plan.get("plan_sha256") != plan_sha:
        raise MontageLearningBridgeContractError("approved_plan_sha256 mismatch")
    if evidence.get("evidence_sha256") != evidence_sha:
        raise MontageLearningBridgeContractError("evidence_sha256 mismatch")

    _require_all_false(
        envelope["authority_flags"], _AUTHORITY_FIELDS, name="authority_flags"
    )
    _require_all_false(
        envelope["effect_flags"], _EFFECT_FIELDS, name="effect_flags"
    )
    _reject_unredacted_sensitive_values(envelope)

    try:
        admitted = admit_montage_human_edit_evidence(
            proposal,
            approved_plan,
            evidence,
        )
    except MontageContractError as exc:
        raise MontageLearningBridgeContractError(
            "embedded TASK-055 lineage is invalid"
        ) from exc
    admitted_body = admitted.to_dict()
    if admitted_body.get("evidence_sha256") != evidence_sha:
        raise MontageLearningBridgeContractError(
            "admitted evidence_sha256 mismatch"
        )

    return MontageLearningBridgeCandidate(
        lane="EXACT_BVP_NATIVE",
        record_id=record_id,
        source_sha256=evidence_sha,
        validation_state=EXACT_LINEAGE_VERIFIED,
        owner_scope_state=OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE,
        review_state=REVIEW_REQUIRED,
        runtime_observation_state="NOT_APPLICABLE",
    )


def validate_generic_learning_delivery(
    value: Mapping[str, object],
) -> MontageLearningBridgeCandidate:
    """Revalidate a generic SKILL delivery as an unbound review candidate."""

    envelope = _require_mapping(value, name="generic delivery")
    _require_exact_fields(envelope, _GENERIC_FIELDS, name="generic delivery")
    _require_equal(envelope, "schema_version", GENERIC_SCHEMA_VERSION)
    _require_equal(envelope, "message_type", GENERIC_MESSAGE_TYPE)
    _require_equal(envelope, "contract_profile", GENERIC_CONTRACT_PROFILE)
    record_id = _require_record_id(envelope, "record_id")
    _require_false(envelope, "canonical_timeline")
    _require_false(envelope, "auto_admit_authorized")

    payload = _require_mapping(envelope["payload"], name="payload")
    learning_sha = _require_sha256(envelope, "learning_sha256")
    if canonical_learning_sha256(payload) != learning_sha:
        raise MontageLearningBridgeContractError("learning_sha256 mismatch")
    if payload.get("record_id") != record_id:
        raise MontageLearningBridgeContractError("record_id mismatch")
    _validate_generic_payload(payload)
    _reject_unredacted_sensitive_values(payload)

    runtime_status = _require_mapping(
        payload["validation_status"], name="validation_status"
    )["runtime"]
    runtime_observation_state = (
        "SOURCE_PASS_CLAIM_STRUCTURALLY_VALID_NONAUTHORITATIVE"
        if runtime_status == "PASS"
        else f"SOURCE_{runtime_status}_NONAUTHORITATIVE"
    )
    return MontageLearningBridgeCandidate(
        lane="GENERIC_SKILL_OBSERVATION",
        record_id=record_id,
        source_sha256=learning_sha,
        validation_state=REVIEW_REQUIRED,
        owner_scope_state=OWNER_SCOPE_UNBOUND,
        review_state=REVIEW_REQUIRED,
        runtime_observation_state=runtime_observation_state,
    )


admit_montage_exact_evidence_delivery = validate_exact_evidence_delivery
admit_montage_learning_delivery = validate_generic_learning_delivery


def _validate_generic_payload(payload: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "message_type",
        "record_id",
        "source_feedback_id",
        "proposal_id",
        "timeline_fps",
        "style_profile",
        "music_context",
        "video_context",
        "proposal",
        "human_final",
        "delta_frames",
        "result",
        "privacy",
        "validation_status",
        "adapter_metadata",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise MontageLearningBridgeContractError(
            f"payload missing required fields: {', '.join(missing)}"
        )
    _require_equal(payload, "schema_version", GENERIC_SCHEMA_VERSION)
    _require_equal(payload, "message_type", GENERIC_PAYLOAD_MESSAGE_TYPE)
    _require_record_id(payload, "record_id")
    for field in ("source_feedback_id", "proposal_id"):
        if not _nonempty_string(payload.get(field)):
            raise MontageLearningBridgeContractError(
                f"{field} must be a non-empty string"
            )

    fps = _require_mapping(payload["timeline_fps"], name="timeline_fps")
    _require_exact_fields(
        fps, frozenset({"numerator", "denominator"}), name="timeline_fps"
    )
    numerator = _require_positive_int(fps, "numerator")
    denominator = _require_positive_int(fps, "denominator")
    if gcd(numerator, denominator) != 1:
        raise MontageLearningBridgeContractError("timeline_fps must be reduced")

    style_profile = payload["style_profile"]
    if not isinstance(style_profile, (str, Mapping)):
        raise MontageLearningBridgeContractError(
            "style_profile must be a string or object"
        )
    _require_mapping(payload["music_context"], name="music_context")
    _require_mapping(payload["video_context"], name="video_context")
    proposal = _require_mapping(payload["proposal"], name="proposal")
    human_final = _require_mapping(payload["human_final"], name="human_final")
    proposal_frame = _require_int(proposal, "timeline_frame")
    final_frame = _require_int(human_final, "timeline_frame")
    result = payload["result"]
    if not isinstance(result, str) or result not in _RESULT_VALUES:
        raise MontageLearningBridgeContractError("result is invalid")
    if human_final.get("status") != result:
        raise MontageLearningBridgeContractError("human_final.status mismatch")
    _require_mapping(human_final.get("provenance"), name="human_final.provenance")
    delta = payload["delta_frames"]
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise MontageLearningBridgeContractError("delta_frames must be an integer")
    if delta != final_frame - proposal_frame:
        raise MontageLearningBridgeContractError("delta_frames mismatch")

    privacy = _require_mapping(payload["privacy"], name="privacy")
    if privacy.get("safe_export") is not True:
        raise MontageLearningBridgeContractError("privacy.safe_export must be true")
    if privacy.get("raw_actor_exported") is not False:
        raise MontageLearningBridgeContractError(
            "privacy.raw_actor_exported must be false"
        )

    statuses = _require_mapping(
        payload["validation_status"], name="validation_status"
    )
    _require_exact_fields(statuses, _VALIDATION_KEYS, name="validation_status")
    for key, status in statuses.items():
        if not isinstance(status, str) or status not in _VALIDATION_VALUES:
            raise MontageLearningBridgeContractError(
                f"validation_status.{key} is invalid"
            )

    metadata = _require_mapping(payload["adapter_metadata"], name="adapter_metadata")
    if metadata.get("canonical_timeline") is not False:
        raise MontageLearningBridgeContractError(
            "adapter_metadata.canonical_timeline must be false"
        )

    if statuses["runtime"] == "PASS":
        runtime = _require_mapping(
            payload.get("runtime_evidence"), name="runtime_evidence"
        )
        if runtime.get("executed") is not True:
            raise MontageLearningBridgeContractError(
                "runtime PASS requires executed true"
            )
        evidence_id = runtime.get("evidence_id")
        report_ref = runtime.get("report_ref")
        if not (_nonempty_string(evidence_id) or _nonempty_string(report_ref)):
            raise MontageLearningBridgeContractError(
                "runtime PASS requires evidence_id or report_ref"
            )


def _require_mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MontageLearningBridgeContractError(f"{name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise MontageLearningBridgeContractError(f"{name} keys must be strings")
    return value


def _require_exact_fields(
    value: Mapping[str, object], expected: frozenset[str], *, name: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise MontageLearningBridgeContractError(
            f"{name} fields mismatch; missing={missing}; extra={extra}"
        )


def _require_equal(
    value: Mapping[str, object], field: str, expected: object
) -> None:
    if value.get(field) != expected or type(value.get(field)) is not type(expected):
        raise MontageLearningBridgeContractError(
            f"{field} must equal {expected!r}"
        )


def _require_false(value: Mapping[str, object], field: str) -> None:
    if value.get(field) is not False:
        raise MontageLearningBridgeContractError(f"{field} must be false")


def _require_all_false(
    value: object, expected_fields: frozenset[str], *, name: str
) -> None:
    flags = _require_mapping(value, name=name)
    _require_exact_fields(flags, expected_fields, name=name)
    for field in expected_fields:
        _require_false(flags, field)


def _require_record_id(value: Mapping[str, object], field: str) -> str:
    candidate = value.get(field)
    if not isinstance(candidate, str) or _RECORD_ID_RE.fullmatch(candidate) is None:
        raise MontageLearningBridgeContractError(f"{field} is invalid")
    return candidate


def _require_sha256(value: Mapping[str, object], field: str) -> str:
    return _require_sha256_value(value.get(field), name=field)


def _require_sha256_value(value: object, *, name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise MontageLearningBridgeContractError(
            f"{name} must be a lowercase sha256: digest"
        )
    return value


def _require_positive_int(value: Mapping[str, object], field: str) -> int:
    candidate = value.get(field)
    if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate <= 0:
        raise MontageLearningBridgeContractError(f"{field} must be a positive integer")
    return candidate


def _require_int(value: Mapping[str, object], field: str) -> int:
    candidate = value.get(field)
    if isinstance(candidate, bool) or not isinstance(candidate, int):
        raise MontageLearningBridgeContractError(f"{field} must be an integer")
    return candidate


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _reject_unredacted_sensitive_values(value: object, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if lowered == "absolute_host_path_included":
                if child is not False:
                    raise MontageLearningBridgeContractError(
                        f"{child_path} must be false"
                    )
                continue
            if lowered == "redacted_field_paths":
                if not isinstance(child, Sequence) or isinstance(
                    child, (str, bytes, bytearray)
                ):
                    raise MontageLearningBridgeContractError(
                        f"{child_path} must be an array of field references"
                    )
                if any(not _nonempty_string(item) for item in child):
                    raise MontageLearningBridgeContractError(
                        f"{child_path} contains an invalid field reference"
                    )
                continue
            if any(part in lowered for part in _FORBIDDEN_KEY_SUBSTRINGS):
                if child != _REDACTED:
                    raise MontageLearningBridgeContractError(
                        f"sensitive field must be {_REDACTED}: {child_path}"
                    )
                continue
            _reject_unredacted_sensitive_values(child, path=child_path)
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for index, child in enumerate(value):
            _reject_unredacted_sensitive_values(child, path=f"{path}[{index}]")


__all__ = [
    "EXACT_CONTRACT_PROFILE",
    "EXACT_LINEAGE_VERIFIED",
    "EXACT_MESSAGE_TYPE",
    "GENERIC_CONTRACT_PROFILE",
    "GENERIC_MESSAGE_TYPE",
    "MontageLearningBridgeCandidate",
    "MontageLearningBridgeContractError",
    "OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE",
    "OWNER_SCOPE_UNBOUND",
    "REVIEW_REQUIRED",
    "admit_montage_exact_evidence_delivery",
    "admit_montage_learning_delivery",
    "canonical_learning_sha256",
    "validate_exact_evidence_delivery",
    "validate_generic_learning_delivery",
]
