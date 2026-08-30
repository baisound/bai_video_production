"""TASK-060 PP-B encrypted montage Preference promotion history.

Only an exact PP-A candidate and a separate explicit Human confirmation can
append a promotion.  Rollback is another append-only revision which points to
an exact earlier payload; it never deletes or rewrites history.  This module
does not publish, transport, load into a runtime, or mutate a Timeline.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .montage_preference_projection import (
    PreferenceProjectionCandidate,
    PreferenceProjectionCandidateState,
    PreferenceProjectionPolicy,
    PreferenceProjectionSources,
    verify_preference_projection_candidate,
)
from .serialization import canonical_json_bytes, sha256_bytes


STORE_SCHEMA_VERSION = "1.0.0"
STORE_RECORD_VERSION = "1.0.0"
PROMOTION_DPAPI_CIPHER_SUITE = "WINDOWS_DPAPI_CURRENT_USER_MONTAGE_PREFERENCE_PROMOTION_V1"
_DPAPI_ENTROPY = b"BAI_VIDEO_PRODUCTION\0TASK060_MONTAGE_PREFERENCE_PROMOTION\0V1"
_MAX_CIPHERTEXT_BYTES = 16 * 1024 * 1024
_STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_PROFILE_ID = re.compile(r"profile-[0-9a-f]{64}")
_PREFERENCE_ID = re.compile(r"pref-[0-9a-f]{64}")
_SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_TOKEN = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def _fail(
    code: str,
    message: str,
    category: ProductErrorCategory,
    **details: object,
) -> ProductError:
    return ProductError(code, message, category, details=dict(details))


def _stable_id(value: object, field: str) -> str:
    if type(value) is not str or _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha256(value: object, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _revision(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 1_000_000_000:
        raise ValueError(f"{field} must be an integer from {minimum} to 1000000000")
    return value


def _epoch_ms(value: object, field: str) -> int:
    if type(value) is not int or value < 1 or value > 9_999_999_999_999:
        raise ValueError(f"{field} must be a positive epoch-millisecond integer")
    return value


def _verify_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version", "message_type", "contract_profile", "profile_contract",
        "profile_id", "profile_version", "owner_scope_hash", "source_record_count",
        "profile_sha256", "advisory_only", "canonical_timeline",
        "auto_apply_authorized", "payload",
    }
    if type(value) is not dict or set(value) != expected:
        raise ValueError("promoted envelope fields are incomplete or unknown")
    if (
        value["schema_version"] != "1.0.0"
        or value["message_type"] != "BvpMontagePreferenceProfileDelivery"
        or value["contract_profile"] != "bvp-task029-file-bridge-v1"
        or value["profile_contract"] != "bvp-task029-montage-preference-projection-v1"
    ):
        raise ValueError("promoted envelope identity mismatch")
    if type(value["profile_id"]) is not str or _PROFILE_ID.fullmatch(value["profile_id"]) is None:
        raise ValueError("profile_id is invalid")
    _revision(value["profile_version"], "profile_version", minimum=1)
    _sha256(value["owner_scope_hash"], "owner_scope_hash")
    _revision(value["source_record_count"], "source_record_count", minimum=1)
    _sha256(value["profile_sha256"], "profile_sha256")
    if (
        value["advisory_only"] is not True
        or value["canonical_timeline"] is not False
        or value["auto_apply_authorized"] is not False
    ):
        raise ValueError("promoted envelope exceeds advisory-only authority")
    payload = value["payload"]
    if type(payload) is not dict or set(payload) != {"projection_version", "preferences"}:
        raise ValueError("promoted payload fields are incomplete or unknown")
    if payload["projection_version"] != "1.0.0" or type(payload["preferences"]) is not list or not payload["preferences"]:
        raise ValueError("promoted payload is invalid")
    if len(payload["preferences"]) > 1000:
        raise ValueError("promoted payload has too many preferences")
    preference_ids: list[str] = []
    for index, row in enumerate(payload["preferences"]):
        fields = {
            "preference_id", "decision", "target", "contexts", "confidence",
            "confirmation_count", "reason_codes", "ranking_bias",
        }
        if type(row) is not dict or set(row) != fields:
            raise ValueError(f"promoted preference {index} fields are incomplete or unknown")
        preference_id = row["preference_id"]
        if type(preference_id) is not str or _PREFERENCE_ID.fullmatch(preference_id) is None:
            raise ValueError("preference_id is invalid")
        preference_ids.append(preference_id)
        if row["decision"] not in {"PREFER", "AVOID", "PROTECT", "DEPRIORITIZE"}:
            raise ValueError("preference decision is invalid")
        if type(row["target"]) is not str or _TOKEN.fullmatch(row["target"]) is None:
            raise ValueError("preference target is invalid")
        for field in ("contexts", "reason_codes"):
            items = row[field]
            if (
                type(items) is not list
                or not 1 <= len(items) <= 16
                or items != sorted(set(items))
                or any(type(item) is not str or _TOKEN.fullmatch(item) is None for item in items)
            ):
                raise ValueError(f"preference {field} must contain canonical Product tokens")
        if type(row["confirmation_count"]) is not int or not 1 <= row["confirmation_count"] <= 32:
            raise ValueError("preference confirmation_count is invalid")
        for field in ("confidence", "ranking_bias"):
            number = row[field]
            if type(number) not in {int, float} or not math.isfinite(number):
                raise ValueError(f"preference {field} is invalid")
        if not 0 <= row["confidence"] <= 1 or not -1 <= row["ranking_bias"] <= 1 or row["ranking_bias"] == 0:
            raise ValueError("preference numeric bounds are invalid")
        positive = row["decision"] in {"PREFER", "PROTECT"}
        if (row["ranking_bias"] > 0) is not positive:
            raise ValueError("preference ranking bias sign does not match decision")
    if preference_ids != sorted(set(preference_ids)):
        raise ValueError("preferences must be unique and canonically sorted")
    if value["profile_sha256"] != sha256_bytes(canonical_json_bytes(payload)):
        raise ValueError("promoted payload hash mismatch")
    # Return a built-in tree detached from caller-owned containers.
    return json.loads(canonical_json_bytes(value))


def _verify_candidate_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version", "record_type", "task_owner", "state", "reason_codes",
        "owner_scope_sha256", "registry_id", "registry_revision",
        "registry_history_sha256", "current_profile_sha256", "current_profile_version",
        "policy_id", "policy_version", "policy_sha256",
        "previous_active_promotion_revision", "previous_active_promotion_sha256",
        "next_profile_version", "source_proposal_sha256s", "source_binding_sha256s",
        "source_decision_history_sha256s", "active_preference_map_sha256",
        "proposed_envelope", "human_review_required", "automatic_learning_authorized",
        "automatic_promotion_authorized", "canonical_timeline",
        "timeline_mutation_authorized", "resolve_write_authorized",
        "external_effect_authorized", "candidate_sha256",
    }
    if type(value) is not dict or set(value) != expected:
        raise ValueError("projection candidate fields are incomplete or unknown")
    if (
        value["schema_version"] != "1.0.0"
        or value["record_type"] != "BVP_MONTAGE_PREFERENCE_PROJECTION_CANDIDATE"
        or value["task_owner"] != "TASK-060"
        or value["state"] != PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW.value
        or value["reason_codes"] != []
    ):
        raise ValueError("only an exact ready PP-A candidate may be promoted")
    if value["human_review_required"] is not True:
        raise ValueError("Human review requirement must remain true")
    for field in (
        "automatic_learning_authorized", "automatic_promotion_authorized",
        "canonical_timeline", "timeline_mutation_authorized",
        "resolve_write_authorized", "external_effect_authorized",
    ):
        if value[field] is not False:
            raise ValueError(f"{field} must remain false")
    body = dict(value)
    candidate_sha256 = body.pop("candidate_sha256", None)
    _sha256(candidate_sha256, "candidate_sha256")
    if candidate_sha256 != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("projection candidate hash mismatch")
    _sha256(value["owner_scope_sha256"], "owner_scope_sha256")
    _stable_id(value["registry_id"], "registry_id")
    _revision(value["registry_revision"], "registry_revision")
    _sha256(value["registry_history_sha256"], "registry_history_sha256")
    if (value["current_profile_sha256"] is None) != (value["current_profile_version"] is None):
        raise ValueError("current profile coordinates must be present together")
    if value["current_profile_sha256"] is not None:
        _sha256(value["current_profile_sha256"], "current_profile_sha256")
        if type(value["current_profile_version"]) is not str or _SEMVER.fullmatch(value["current_profile_version"]) is None:
            raise ValueError("current_profile_version is invalid")
    _stable_id(value["policy_id"], "policy_id")
    if type(value["policy_version"]) is not str or _SEMVER.fullmatch(value["policy_version"]) is None:
        raise ValueError("policy_version is invalid")
    _sha256(value["policy_sha256"], "policy_sha256")
    previous_revision = _revision(
        value["previous_active_promotion_revision"],
        "previous_active_promotion_revision",
    )
    next_version = _revision(value["next_profile_version"], "next_profile_version", minimum=1)
    if next_version != previous_revision + 1:
        raise ValueError("candidate next version does not follow its predecessor")
    if previous_revision == 0:
        if value["previous_active_promotion_sha256"] is not None:
            raise ValueError("first candidate cannot bind a predecessor hash")
    else:
        _sha256(value["previous_active_promotion_sha256"], "previous_active_promotion_sha256")
    for field in (
        "source_proposal_sha256s", "source_binding_sha256s",
        "source_decision_history_sha256s",
    ):
        coordinates = value[field]
        if (
            type(coordinates) is not list
            or not coordinates
            or coordinates != sorted(set(coordinates))
        ):
            raise ValueError(f"{field} must be non-empty, unique, and sorted")
        for coordinate in coordinates:
            _sha256(coordinate, field)
    envelope = _verify_envelope(value["proposed_envelope"])
    if envelope["owner_scope_hash"] != value["owner_scope_sha256"]:
        raise ValueError("candidate envelope Owner scope mismatch")
    if envelope["profile_version"] != value["next_profile_version"]:
        raise ValueError("candidate envelope version mismatch")
    # The private map digest and public payload digest intentionally differ.
    _sha256(value["active_preference_map_sha256"], "active_preference_map_sha256")
    return json.loads(canonical_json_bytes(value))


@runtime_checkable
class PreferencePromotionCipher(Protocol):
    cipher_suite: str

    def encrypt(self, plaintext: bytes) -> bytes: ...

    def decrypt(self, ciphertext: bytes) -> bytes: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(value: bytes) -> tuple[_DataBlob, object]:
    if value:
        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer
    return _DataBlob(0, ctypes.POINTER(ctypes.c_ubyte)()), None


class WindowsDpapiPreferencePromotionCipher:
    """Windows Current User DPAPI with a PP-B-specific entropy domain."""

    cipher_suite = PROMOTION_DPAPI_CIPHER_SUITE
    _UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if os.name != "nt":
            raise _fail(
                "ERR_MONTAGE_PREFERENCE_PROMOTION_ENCRYPTION_UNAVAILABLE",
                "Windows DPAPI is unavailable on this platform",
                ProductErrorCategory.NOT_SUPPORTED,
            )

    @staticmethod
    def _crypt(value: bytes, *, protect: bool) -> bytes:
        input_blob, input_buffer = _blob(value)
        entropy_blob, entropy_buffer = _blob(_DPAPI_ENTROPY)
        output_blob = _DataBlob()
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        function.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.POINTER(_DataBlob),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        function.restype = wintypes.BOOL
        if not function(
            ctypes.byref(input_blob), None, ctypes.byref(entropy_blob), None, None,
            WindowsDpapiPreferencePromotionCipher._UI_FORBIDDEN,
            ctypes.byref(output_blob),
        ):
            raise OSError(ctypes.get_last_error(), "DPAPI operation failed")
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            if output_blob.pbData:
                kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._crypt(plaintext, protect=True)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._crypt(ciphertext, protect=False)


class PreferencePromotionAction(str, Enum):
    PROMOTE = "PROMOTE"
    ROLLBACK = "ROLLBACK"


@dataclass(frozen=True, slots=True)
class PreferencePromotionConfirmation:
    confirmation_id: str
    action: PreferencePromotionAction
    owner_scope_sha256: str
    candidate_sha256: str | None
    expected_revision: int
    expected_previous_revision_sha256: str | None
    active_payload_sha256: str
    rollback_target_revision: int | None
    rollback_target_revision_sha256: str | None
    confirmed_at_epoch_ms: int

    def __post_init__(self) -> None:
        _stable_id(self.confirmation_id, "confirmation_id")
        if type(self.action) is not PreferencePromotionAction:
            raise ValueError("action must be a PreferencePromotionAction")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _revision(self.expected_revision, "expected_revision")
        _sha256(self.active_payload_sha256, "active_payload_sha256")
        _epoch_ms(self.confirmed_at_epoch_ms, "confirmed_at_epoch_ms")
        if self.expected_revision == 0:
            if self.expected_previous_revision_sha256 is not None:
                raise ValueError("first confirmation cannot bind a previous revision")
        else:
            _sha256(self.expected_previous_revision_sha256, "expected_previous_revision_sha256")
        if self.action is PreferencePromotionAction.PROMOTE:
            _sha256(self.candidate_sha256, "candidate_sha256")
            if self.rollback_target_revision is not None or self.rollback_target_revision_sha256 is not None:
                raise ValueError("promotion confirmation cannot bind a rollback target")
        else:
            if self.candidate_sha256 is not None:
                raise ValueError("rollback confirmation cannot bind a candidate")
            _revision(self.rollback_target_revision, "rollback_target_revision", minimum=1)
            _sha256(self.rollback_target_revision_sha256, "rollback_target_revision_sha256")
            if self.rollback_target_revision > self.expected_revision:
                raise ValueError("rollback target must already exist")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "MONTAGE_PREFERENCE_PROMOTION_CONFIRMATION",
            "task_owner": "TASK-060",
            "confirmation_id": self.confirmation_id,
            "action": self.action.value,
            "owner_scope_sha256": self.owner_scope_sha256,
            "candidate_sha256": self.candidate_sha256,
            "expected_revision": self.expected_revision,
            "expected_previous_revision_sha256": self.expected_previous_revision_sha256,
            "active_payload_sha256": self.active_payload_sha256,
            "rollback_target_revision": self.rollback_target_revision,
            "rollback_target_revision_sha256": self.rollback_target_revision_sha256,
            "confirmed_at_epoch_ms": self.confirmed_at_epoch_ms,
            "explicit_human_confirmation_received": True,
            "automatic_promotion_authorized": False,
            "automatic_rollback_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["confirmation_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PreferencePromotionConfirmation":
        expected = {
            "record_version", "record_type", "task_owner", "confirmation_id", "action",
            "owner_scope_sha256", "candidate_sha256", "expected_revision",
            "expected_previous_revision_sha256", "active_payload_sha256",
            "rollback_target_revision", "rollback_target_revision_sha256",
            "confirmed_at_epoch_ms", "explicit_human_confirmation_received",
            "automatic_promotion_authorized", "automatic_rollback_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized", "confirmation_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("confirmation fields are incomplete or unknown")
        if (
            value["record_version"] != STORE_RECORD_VERSION
            or value["record_type"] != "MONTAGE_PREFERENCE_PROMOTION_CONFIRMATION"
            or value["task_owner"] != "TASK-060"
            or value["explicit_human_confirmation_received"] is not True
        ):
            raise ValueError("confirmation identity mismatch")
        for field in (
            "automatic_promotion_authorized", "automatic_rollback_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["confirmation_id"], PreferencePromotionAction(value["action"]),
            value["owner_scope_sha256"], value["candidate_sha256"],
            value["expected_revision"], value["expected_previous_revision_sha256"],
            value["active_payload_sha256"], value["rollback_target_revision"],
            value["rollback_target_revision_sha256"], value["confirmed_at_epoch_ms"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("confirmation hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PreferencePromotionRevision:
    sequence: int
    action: PreferencePromotionAction
    candidate: Mapping[str, Any] | None
    confirmation: PreferencePromotionConfirmation
    active_envelope: Mapping[str, Any]
    rollback_target_revision: int | None
    rollback_target_revision_sha256: str | None
    previous_revision_sha256: str | None

    def __post_init__(self) -> None:
        _revision(self.sequence, "sequence", minimum=1)
        if type(self.action) is not PreferencePromotionAction or self.confirmation.action is not self.action:
            raise ValueError("revision action mismatch")
        envelope = _verify_envelope(self.active_envelope)
        if envelope["owner_scope_hash"] != self.confirmation.owner_scope_sha256:
            raise ValueError("revision Owner scope mismatch")
        if envelope["profile_sha256"] != self.confirmation.active_payload_sha256:
            raise ValueError("confirmation does not bind the active payload")
        if self.confirmation.expected_revision != self.sequence - 1:
            raise ValueError("confirmation does not bind the previous revision")
        if self.confirmation.expected_previous_revision_sha256 != self.previous_revision_sha256:
            raise ValueError("confirmation previous hash mismatch")
        if self.sequence == 1:
            if self.previous_revision_sha256 is not None:
                raise ValueError("first revision cannot have a predecessor")
        else:
            _sha256(self.previous_revision_sha256, "previous_revision_sha256")
        if self.action is PreferencePromotionAction.PROMOTE:
            if self.candidate is None:
                raise ValueError("promotion revision requires the exact candidate")
            candidate = _verify_candidate_payload(self.candidate)
            if candidate["candidate_sha256"] != self.confirmation.candidate_sha256:
                raise ValueError("confirmation does not bind the candidate")
            if candidate["previous_active_promotion_revision"] != self.sequence - 1:
                raise ValueError("candidate does not bind the current promotion revision")
            if candidate["previous_active_promotion_sha256"] != self.previous_revision_sha256:
                raise ValueError("candidate does not bind the current promotion hash")
            if candidate["next_profile_version"] != self.sequence:
                raise ValueError("candidate profile version must equal promotion revision")
            if candidate["proposed_envelope"] != envelope:
                raise ValueError("active envelope does not equal the candidate envelope")
            if self.rollback_target_revision is not None or self.rollback_target_revision_sha256 is not None:
                raise ValueError("promotion revision cannot bind a rollback target")
        else:
            if self.candidate is not None:
                raise ValueError("rollback revision cannot contain a candidate")
            if (
                self.rollback_target_revision != self.confirmation.rollback_target_revision
                or self.rollback_target_revision_sha256
                != self.confirmation.rollback_target_revision_sha256
            ):
                raise ValueError("rollback target does not match confirmation")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "MONTAGE_PREFERENCE_PROMOTION_REVISION",
            "task_owner": "TASK-060",
            "sequence": self.sequence,
            "action": self.action.value,
            "candidate": None if self.candidate is None else dict(self.candidate),
            "confirmation": self.confirmation.to_dict(),
            "active_envelope": dict(self.active_envelope),
            "active_payload_sha256": self.active_envelope["profile_sha256"],
            "rollback_target_revision": self.rollback_target_revision,
            "rollback_target_revision_sha256": self.rollback_target_revision_sha256,
            "previous_revision_sha256": self.previous_revision_sha256,
            "append_only_revision": True,
            "advisory_profile_only": True,
            "automatic_promotion_authorized": False,
            "automatic_rollback_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["promotion_revision_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PreferencePromotionRevision":
        expected = {
            "record_version", "record_type", "task_owner", "sequence", "action",
            "candidate", "confirmation", "active_envelope", "active_payload_sha256",
            "rollback_target_revision", "rollback_target_revision_sha256",
            "previous_revision_sha256", "append_only_revision", "advisory_profile_only",
            "automatic_promotion_authorized", "automatic_rollback_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized", "promotion_revision_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("promotion revision fields are incomplete or unknown")
        if (
            value["record_version"] != STORE_RECORD_VERSION
            or value["record_type"] != "MONTAGE_PREFERENCE_PROMOTION_REVISION"
            or value["task_owner"] != "TASK-060"
            or value["append_only_revision"] is not True
            or value["advisory_profile_only"] is not True
        ):
            raise ValueError("promotion revision identity mismatch")
        for field in (
            "automatic_promotion_authorized", "automatic_rollback_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        if value["active_payload_sha256"] != value["active_envelope"].get("profile_sha256"):
            raise ValueError("active payload coordinate mismatch")
        result = cls(
            value["sequence"], PreferencePromotionAction(value["action"]),
            value["candidate"], PreferencePromotionConfirmation.from_dict(value["confirmation"]),
            value["active_envelope"], value["rollback_target_revision"],
            value["rollback_target_revision_sha256"], value["previous_revision_sha256"],
        )
        if result.to_dict() != dict(value):
            raise ValueError("promotion revision hash or derived fields mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PreferencePromotionHistory:
    store_id: str
    owner_scope_sha256: str
    revision: int
    revisions: tuple[PreferencePromotionRevision, ...]

    def __post_init__(self) -> None:
        _stable_id(self.store_id, "store_id")
        _sha256(self.owner_scope_sha256, "owner_scope_sha256")
        _revision(self.revision, "revision")
        if type(self.revisions) is not tuple or self.revision != len(self.revisions):
            raise ValueError("revision must equal the immutable revision count")
        previous: str | None = None
        confirmation_ids: dict[str, str] = {}
        candidate_hashes: dict[str, str] = {}
        for sequence, item in enumerate(self.revisions, 1):
            if type(item) is not PreferencePromotionRevision:
                raise ValueError("revisions must be exact PreferencePromotionRevision records")
            payload = item.to_dict()
            revision_sha256 = payload["promotion_revision_sha256"]
            if item.sequence != sequence or item.previous_revision_sha256 != previous:
                raise ValueError("promotion history chain is not contiguous")
            if item.confirmation.owner_scope_sha256 != self.owner_scope_sha256:
                raise ValueError("promotion history Owner scope mismatch")
            confirmation_sha256 = item.confirmation.to_dict()["confirmation_sha256"]
            existing = confirmation_ids.setdefault(item.confirmation.confirmation_id, confirmation_sha256)
            if existing != confirmation_sha256 or sum(
                revision.confirmation.confirmation_id == item.confirmation.confirmation_id
                for revision in self.revisions
            ) > 1:
                raise ValueError("confirmation replay or collision is forbidden")
            if item.action is PreferencePromotionAction.PROMOTE:
                candidate_sha256 = item.confirmation.candidate_sha256
                existing_candidate = candidate_hashes.setdefault(candidate_sha256, revision_sha256)
                if existing_candidate != revision_sha256:
                    raise ValueError("candidate replay is forbidden")
            else:
                target = self.revisions[item.rollback_target_revision - 1]
                if target.sequence >= item.sequence:
                    raise ValueError("rollback target must precede the rollback revision")
                if target.to_dict()["promotion_revision_sha256"] != item.rollback_target_revision_sha256:
                    raise ValueError("rollback target hash mismatch")
                if dict(target.active_envelope) != dict(item.active_envelope):
                    raise ValueError("rollback must preserve the exact target envelope and payload hash")
            previous = revision_sha256

    @property
    def current_revision_sha256(self) -> str | None:
        if not self.revisions:
            return None
        return self.revisions[-1].to_dict()["promotion_revision_sha256"]

    @property
    def active_envelope(self) -> dict[str, Any] | None:
        if not self.revisions:
            return None
        return json.loads(canonical_json_bytes(self.revisions[-1].active_envelope))

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_version": STORE_RECORD_VERSION,
            "record_type": "MONTAGE_PREFERENCE_PROMOTION_HISTORY",
            "task_owner": "TASK-060",
            "store_id": self.store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "revision": self.revision,
            "revisions": [item.to_dict() for item in self.revisions],
            "append_only_revisions": True,
            "encrypted_at_rest_required": True,
            "explicit_human_confirmation_required": True,
            "advisory_profile_only": True,
            "plaintext_export_authorized": False,
            "physical_delete_authorized": False,
            "automatic_promotion_authorized": False,
            "automatic_rollback_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        body["history_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PreferencePromotionHistory":
        expected = {
            "record_version", "record_type", "task_owner", "store_id",
            "owner_scope_sha256", "revision", "revisions", "append_only_revisions",
            "encrypted_at_rest_required", "explicit_human_confirmation_required",
            "advisory_profile_only", "plaintext_export_authorized",
            "physical_delete_authorized", "automatic_promotion_authorized",
            "automatic_rollback_authorized", "timeline_mutation_authorized",
            "resolve_write_authorized", "external_effect_authorized", "history_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("promotion history fields are incomplete or unknown")
        if (
            value["record_version"] != STORE_RECORD_VERSION
            or value["record_type"] != "MONTAGE_PREFERENCE_PROMOTION_HISTORY"
            or value["task_owner"] != "TASK-060"
        ):
            raise ValueError("promotion history identity mismatch")
        for field in (
            "append_only_revisions", "encrypted_at_rest_required",
            "explicit_human_confirmation_required", "advisory_profile_only",
        ):
            if value[field] is not True:
                raise ValueError(f"{field} must remain true")
        for field in (
            "plaintext_export_authorized", "physical_delete_authorized",
            "automatic_promotion_authorized", "automatic_rollback_authorized",
            "timeline_mutation_authorized", "resolve_write_authorized",
            "external_effect_authorized",
        ):
            if value[field] is not False:
                raise ValueError(f"{field} must remain false")
        result = cls(
            value["store_id"], value["owner_scope_sha256"], value["revision"],
            tuple(PreferencePromotionRevision.from_dict(row) for row in value["revisions"]),
        )
        if result.to_dict() != dict(value):
            raise ValueError("promotion history hash or derived fields mismatch")
        return result


def confirm_preference_promotion(
    *,
    confirmation_id: str,
    candidate: PreferenceProjectionCandidate,
    confirmed_at_epoch_ms: int,
    human_confirmed: bool,
) -> PreferencePromotionConfirmation:
    if human_confirmed is not True:
        raise ValueError("explicit Human promotion confirmation is required")
    if type(candidate) is not PreferenceProjectionCandidate or candidate.state is not PreferenceProjectionCandidateState.READY_FOR_HUMAN_REVIEW:
        raise ValueError("only READY_FOR_HUMAN_REVIEW candidates may be confirmed")
    payload = candidate.to_dict()
    envelope = _verify_envelope(payload["proposed_envelope"])
    return PreferencePromotionConfirmation(
        confirmation_id, PreferencePromotionAction.PROMOTE, candidate.owner_scope_sha256,
        payload["candidate_sha256"], candidate.previous_active_promotion_revision,
        candidate.previous_active_promotion_sha256, envelope["profile_sha256"],
        None, None, confirmed_at_epoch_ms,
    )


def confirm_preference_rollback(
    *,
    confirmation_id: str,
    history: PreferencePromotionHistory,
    target_revision: int,
    confirmed_at_epoch_ms: int,
    human_confirmed: bool,
) -> PreferencePromotionConfirmation:
    if human_confirmed is not True:
        raise ValueError("explicit Human rollback confirmation is required")
    if type(history) is not PreferencePromotionHistory or history.revision == 0:
        raise ValueError("rollback requires a non-empty verified promotion history")
    _revision(target_revision, "target_revision", minimum=1)
    if target_revision > history.revision:
        raise ValueError("rollback target does not exist")
    target = history.revisions[target_revision - 1]
    return PreferencePromotionConfirmation(
        confirmation_id, PreferencePromotionAction.ROLLBACK, history.owner_scope_sha256,
        None, history.revision, history.current_revision_sha256,
        target.active_envelope["profile_sha256"], target_revision,
        target.to_dict()["promotion_revision_sha256"], confirmed_at_epoch_ms,
    )


@dataclass(frozen=True, slots=True)
class PreferencePromotionSaveResult:
    history: PreferencePromotionHistory
    write: AtomicWriteResult | None
    duplicate_noop: bool


class PreferencePromotionStore:
    """CAS append/read of explicit promotions and append-only rollbacks."""

    def __init__(self, path: str | Path, cipher: PreferencePromotionCipher | None = None) -> None:
        self.path = Path(path)
        self.cipher = cipher if cipher is not None else WindowsDpapiPreferencePromotionCipher()
        if not isinstance(self.cipher, PreferencePromotionCipher):
            raise ValueError("cipher does not implement PreferencePromotionCipher")
        _stable_id(self.cipher.cipher_suite, "cipher_suite")

    def _envelope(self, history: PreferencePromotionHistory) -> dict[str, object]:
        ciphertext = self.cipher.encrypt(canonical_json_bytes(history.to_dict()))
        if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT_BYTES:
            raise ValueError("ciphertext size is invalid")
        body: dict[str, object] = {
            "schema_version": STORE_SCHEMA_VERSION,
            "record_type": "MONTAGE_PREFERENCE_PROMOTION_STORE_ENCRYPTED",
            "task_owner": "TASK-060",
            "cipher_suite": self.cipher.cipher_suite,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "plaintext_fields_present": False,
        }
        body["document_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    def _parse_envelope(self, value: Mapping[str, Any]) -> PreferencePromotionHistory:
        expected = {
            "schema_version", "record_type", "task_owner", "cipher_suite",
            "ciphertext_b64", "ciphertext_sha256", "plaintext_fields_present",
            "document_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("encrypted promotion store fields are incomplete or unknown")
        if (
            value["schema_version"] != STORE_SCHEMA_VERSION
            or value["record_type"] != "MONTAGE_PREFERENCE_PROMOTION_STORE_ENCRYPTED"
            or value["task_owner"] != "TASK-060"
            or value["cipher_suite"] != self.cipher.cipher_suite
            or value["plaintext_fields_present"] is not False
        ):
            raise ValueError("encrypted promotion store identity mismatch")
        body = {key: item for key, item in value.items() if key != "document_sha256"}
        if value["document_sha256"] != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("encrypted promotion store document checksum mismatch")
        ciphertext = base64.b64decode(value["ciphertext_b64"], validate=True)
        if (
            not ciphertext
            or len(ciphertext) > _MAX_CIPHERTEXT_BYTES
            or value["ciphertext_sha256"] != sha256_bytes(ciphertext)
        ):
            raise ValueError("encrypted promotion store ciphertext checksum mismatch")
        document = json.loads(self.cipher.decrypt(ciphertext).decode("utf-8"))
        if type(document) is not dict:
            raise ValueError("decrypted promotion history must be an object")
        return PreferencePromotionHistory.from_dict(document)

    def load(self) -> PreferencePromotionHistory:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError("promotion store must be a regular non-symlink file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if type(document) is not dict:
                raise ValueError("encrypted promotion store must be an object")
            return self._parse_envelope(document)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _fail(
                "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_INTEGRITY",
                "Montage Preference promotion store could not be decrypted and verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                reason=type(exc).__name__,
            ) from exc

    def _current(self, store_id: str, owner_scope_sha256: str) -> PreferencePromotionHistory:
        if self.path.exists():
            current = self.load()
            if current.store_id != store_id or current.owner_scope_sha256 != owner_scope_sha256:
                raise _fail(
                    "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_SCOPE",
                    "Montage Preference promotion store scope mismatch",
                    ProductErrorCategory.AUTHORIZATION,
                )
            return current
        if self.path.is_symlink():
            raise _fail(
                "ERR_MONTAGE_PREFERENCE_PROMOTION_STORE_INTEGRITY",
                "Montage Preference promotion store path is a symlink",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return PreferencePromotionHistory(store_id, owner_scope_sha256, 0, ())

    @staticmethod
    def _duplicate(
        current: PreferencePromotionHistory,
        confirmation: PreferencePromotionConfirmation,
        candidate_sha256: str | None,
    ) -> bool:
        confirmation_payload = confirmation.to_dict()
        for revision in current.revisions:
            existing = revision.confirmation
            if existing.confirmation_id == confirmation.confirmation_id:
                if existing.to_dict() == confirmation_payload and existing.candidate_sha256 == candidate_sha256:
                    return True
                raise _fail(
                    "ERR_MONTAGE_PREFERENCE_PROMOTION_COLLISION",
                    "confirmation identity collision",
                    ProductErrorCategory.DATA_INTEGRITY,
                    confirmation_id=confirmation.confirmation_id,
                )
            if candidate_sha256 is not None and existing.candidate_sha256 == candidate_sha256:
                raise _fail(
                    "ERR_MONTAGE_PREFERENCE_PROMOTION_COLLISION",
                    "candidate replay with a different confirmation",
                    ProductErrorCategory.DATA_INTEGRITY,
                    candidate_sha256=candidate_sha256,
                )
        return False

    @staticmethod
    def _check_cas(current: PreferencePromotionHistory, expected_revision: int) -> None:
        if current.revision != expected_revision:
            raise _fail(
                "ERR_MONTAGE_PREFERENCE_PROMOTION_CONFLICT",
                "Montage Preference promotion store changed since it was read",
                ProductErrorCategory.STATE,
                expected_revision=expected_revision,
                current_revision=current.revision,
            )

    def _write(
        self,
        history: PreferencePromotionHistory,
        failure_injector: FailureInjector | None,
    ) -> PreferencePromotionSaveResult:
        write = AtomicJsonWriter.write(
            self.path,
            self._envelope(history),
            validator=lambda value: self._parse_envelope(value),
            failure_injector=failure_injector,
        )
        if failure_injector:
            failure_injector("after_replace", self.path)
            failure_injector("before_durable_readback", self.path)
        durable = self.load()
        if durable.to_dict() != history.to_dict():
            raise _fail(
                "ERR_MONTAGE_PREFERENCE_PROMOTION_DURABLE_READBACK",
                "durable promotion read-back did not match the appended history",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return PreferencePromotionSaveResult(durable, write, False)

    def promote(
        self,
        *,
        store_id: str,
        owner_scope_sha256: str,
        candidate: PreferenceProjectionCandidate,
        sources: PreferenceProjectionSources,
        policy: PreferenceProjectionPolicy,
        confirmation: PreferencePromotionConfirmation,
        expected_revision: int,
        failure_injector: FailureInjector | None = None,
    ) -> PreferencePromotionSaveResult:
        _stable_id(store_id, "store_id")
        _sha256(owner_scope_sha256, "owner_scope_sha256")
        _revision(expected_revision, "expected_revision")
        if type(candidate) is not PreferenceProjectionCandidate:
            raise ValueError("candidate must be an exact PreferenceProjectionCandidate")
        candidate_payload = _verify_candidate_payload(candidate.to_dict())
        if (
            type(confirmation) is not PreferencePromotionConfirmation
            or confirmation.action is not PreferencePromotionAction.PROMOTE
            or confirmation.to_dict()["candidate_sha256"] != candidate_payload["candidate_sha256"]
        ):
            raise ValueError("exact explicit Human confirmation does not match the candidate")
        with exclusive_file_update_lock(self.path):
            current = self._current(store_id, owner_scope_sha256)
            if self._duplicate(current, confirmation, candidate_payload["candidate_sha256"]):
                return PreferencePromotionSaveResult(current, None, True)
            self._check_cas(current, expected_revision)
            if (
                confirmation.expected_revision != current.revision
                or confirmation.expected_previous_revision_sha256 != current.current_revision_sha256
            ):
                raise ValueError("confirmation does not bind the exact current store revision")
            verify_preference_projection_candidate(
                candidate,
                sources,
                policy,
                expected_owner_scope_sha256=owner_scope_sha256,
                expected_registry_revision=candidate.registry_revision,
                requested_scope_mode="OWNER_GLOBAL",
                previous_active_promotion_revision=current.revision,
                previous_active_promotion_sha256=current.current_revision_sha256,
                next_profile_version=current.revision + 1,
            )
            revision = PreferencePromotionRevision(
                current.revision + 1, PreferencePromotionAction.PROMOTE,
                candidate_payload, confirmation, candidate_payload["proposed_envelope"],
                None, None, current.current_revision_sha256,
            )
            history = PreferencePromotionHistory(
                store_id, owner_scope_sha256, current.revision + 1,
                current.revisions + (revision,),
            )
            return self._write(history, failure_injector)

    def rollback(
        self,
        *,
        store_id: str,
        owner_scope_sha256: str,
        confirmation: PreferencePromotionConfirmation,
        expected_revision: int,
        failure_injector: FailureInjector | None = None,
    ) -> PreferencePromotionSaveResult:
        _stable_id(store_id, "store_id")
        _sha256(owner_scope_sha256, "owner_scope_sha256")
        _revision(expected_revision, "expected_revision", minimum=1)
        if type(confirmation) is not PreferencePromotionConfirmation or confirmation.action is not PreferencePromotionAction.ROLLBACK:
            raise ValueError("rollback requires exact explicit Human rollback confirmation")
        with exclusive_file_update_lock(self.path):
            current = self._current(store_id, owner_scope_sha256)
            if self._duplicate(current, confirmation, None):
                return PreferencePromotionSaveResult(current, None, True)
            self._check_cas(current, expected_revision)
            if (
                confirmation.expected_revision != current.revision
                or confirmation.expected_previous_revision_sha256 != current.current_revision_sha256
            ):
                raise ValueError("rollback confirmation does not bind the exact current store revision")
            target_revision = confirmation.rollback_target_revision
            if target_revision is None or target_revision > current.revision:
                raise ValueError("rollback target does not exist")
            target = current.revisions[target_revision - 1]
            if (
                target.to_dict()["promotion_revision_sha256"]
                != confirmation.rollback_target_revision_sha256
                or target.active_envelope["profile_sha256"] != confirmation.active_payload_sha256
            ):
                raise ValueError("rollback confirmation does not bind the exact target payload")
            revision = PreferencePromotionRevision(
                current.revision + 1, PreferencePromotionAction.ROLLBACK, None,
                confirmation, target.active_envelope, target_revision,
                confirmation.rollback_target_revision_sha256,
                current.current_revision_sha256,
            )
            history = PreferencePromotionHistory(
                store_id, owner_scope_sha256, current.revision + 1,
                current.revisions + (revision,),
            )
            return self._write(history, failure_injector)


__all__ = [
    "PROMOTION_DPAPI_CIPHER_SUITE", "PreferencePromotionAction",
    "PreferencePromotionCipher", "PreferencePromotionConfirmation",
    "PreferencePromotionHistory", "PreferencePromotionRevision",
    "PreferencePromotionSaveResult", "PreferencePromotionStore",
    "WindowsDpapiPreferencePromotionCipher", "confirm_preference_promotion",
    "confirm_preference_rollback",
]
