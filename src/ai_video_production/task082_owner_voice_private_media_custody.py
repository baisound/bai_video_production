"""TASK-082 pure, body-free owner-voice custody contracts.

This module deliberately has no filesystem, audio, process, key, cipher, OBS,
model, provider, or native integration.  It validates public-safe metadata and
produces fixture-only decisions that cannot grant access to a private body.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from itertools import islice
import json
import re
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task082.owner-voice-private-media-custody.v2"
SCHEMA_VERSION = 2
TASK_OWNER = "TASK-082"

RECEIPT_RECORD_TYPE = "Task082PrivateMediaCustodyReceiptV2"
RECEIPT_ROLE = "PRIVATE_MEDIA_CUSTODY"
EVENT_RECORD_TYPE = "Task082PrivateMediaGenerationEventV2"
EVENT_ROLE = "PRIVATE_MEDIA_GENERATION_EVENT"
DECISION_RECORD_TYPE = "Task082PrivateMediaLeaseDecisionV2"
DECISION_ROLE = "PRIVATE_MEDIA_LEASE_DECISION"
COMPLETION_RECORD_TYPE = "Task082PrivateMediaLeaseCompletionReadbackV2"
COMPLETION_ROLE = "PRIVATE_MEDIA_LEASE_COMPLETION_READBACK"

EVENT_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0"
RECEIPT_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_CUSTODY_RECEIPT_V2\0"
CUSTODY_BINDING_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_STAGED_CUSTODY_BINDING_V2\0"
DECISION_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_LEASE_DECISION_V2\0"
CURRENTNESS_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_CURRENTNESS_V2\0"
COMPLETION_DIGEST_DOMAIN = b"TASK082_PRIVATE_MEDIA_LEASE_COMPLETION_READBACK_V2\0"

MAX_JSON_BYTES = 65_536
MAX_JSON_DEPTH = 16
MAX_EVENTS = 1_024

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_PRIVATE_MARKERS = (
    "private-path",
    "host-path",
    "credential",
    "password",
    "secret",
    "token",
    "speaker-fingerprint",
)


class Task082Reason(str, Enum):
    READY = "READY"
    CURRENT = "CURRENT"
    NO_CURRENT_GENERATION = "NO_CURRENT_GENERATION"
    JSON_INVALID = "JSON_INVALID"
    JSON_DUPLICATE_KEY = "JSON_DUPLICATE_KEY"
    JSON_NONFINITE = "JSON_NONFINITE"
    JSON_OVERSIZE = "JSON_OVERSIZE"
    JSON_DEPTH_EXCEEDED = "JSON_DEPTH_EXCEEDED"
    RECORD_FIELDS_INVALID = "RECORD_FIELDS_INVALID"
    RECORD_DISCRIMINATOR_INVALID = "RECORD_DISCRIMINATOR_INVALID"
    IDENTIFIER_INVALID = "IDENTIFIER_INVALID"
    DIGEST_INVALID = "DIGEST_INVALID"
    TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
    INTEGER_INVALID = "INTEGER_INVALID"
    RECEIPT_DIGEST_MISMATCH = "RECEIPT_DIGEST_MISMATCH"
    CUSTODY_BINDING_MISMATCH = "CUSTODY_BINDING_MISMATCH"
    EVENT_DIGEST_MISMATCH = "EVENT_DIGEST_MISMATCH"
    EVENT_REVISION_GAP = "EVENT_REVISION_GAP"
    EVENT_PREDECESSOR_MISMATCH = "EVENT_PREDECESSOR_MISMATCH"
    EVENT_LINEAGE_MISMATCH = "EVENT_LINEAGE_MISMATCH"
    EVENT_VARIANT_FIELDS_INVALID = "EVENT_VARIANT_FIELDS_INVALID"
    PUBLISH_GENERATION_GAP = "PUBLISH_GENERATION_GAP"
    TOMBSTONE_TARGET_MISMATCH = "TOMBSTONE_TARGET_MISMATCH"
    CURRENTNESS_NOT_CONFIRMED = "CURRENTNESS_NOT_CONFIRMED"
    REQUEST_INVALID = "REQUEST_INVALID"
    WRONG_SUBJECT = "WRONG_SUBJECT"
    WRONG_PURPOSE = "WRONG_PURPOSE"
    WRONG_CONSENT = "WRONG_CONSENT"
    WRONG_ARTIFACT_CLASS = "WRONG_ARTIFACT_CLASS"
    WRONG_PRODUCER = "WRONG_PRODUCER"
    WRONG_OUTPUT_ROLE = "WRONG_OUTPUT_ROLE"
    WRONG_CONSUMER = "WRONG_CONSUMER"
    WRONG_OPERATION = "WRONG_OPERATION"
    WRONG_GENERATION = "WRONG_GENERATION"
    WRONG_ASSET_ADOPTION = "WRONG_ASSET_ADOPTION"
    REQUIRED_BINDING_MISSING = "REQUIRED_BINDING_MISSING"
    STALE_BINDING = "STALE_BINDING"
    REVOKED = "REVOKED"
    RECEIPT_AS_CAPABILITY = "RECEIPT_AS_CAPABILITY"
    STATE_TRANSITION_INVALID = "STATE_TRANSITION_INVALID"
    REPLAY = "REPLAY"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"


class Task082ContractError(ValueError):
    """A public-safe failure carrying only a stable reason code."""

    def __init__(self, reason: Task082Reason):
        self.reason = reason
        super().__init__(reason.value)


class ArtifactClass(str, Enum):
    RAW_CAPTURE = "RAW_CAPTURE"
    CANONICAL_PCM = "CANONICAL_PCM"
    PROCESSED_SPEECH_CONTINUOUS = "PROCESSED_SPEECH_CONTINUOUS"
    REVIEW_TRANSCRIPT = "REVIEW_TRANSCRIPT"
    TRAINING_COPY = "TRAINING_COPY"


class GenerationEventKind(str, Enum):
    GENERATION_PUBLISHED = "GENERATION_PUBLISHED"
    GENERATION_REVOKED = "GENERATION_REVOKED"
    GENERATION_QUARANTINED = "GENERATION_QUARANTINED"
    GENERATION_EXPIRED = "GENERATION_EXPIRED"


class CurrentnessState(str, Enum):
    CURRENT = "CURRENT"
    NO_CURRENT_GENERATION = "NO_CURRENT_GENERATION"
    CURRENTNESS_NOT_CONFIRMED = "CURRENTNESS_NOT_CONFIRMED"


class LeaseKind(str, Enum):
    WRITE = "WRITE"
    READ = "READ"


class LeaseState(str, Enum):
    PREPARED = "PREPARED"
    ISSUED = "ISSUED"
    OPEN_STARTED = "OPEN_STARTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"
    FAILED_CLOSED = "FAILED_CLOSED"


class LeaseDecisionKind(str, Enum):
    READY_FIXTURE_ONLY = "READY_FIXTURE_ONLY"
    BLOCKED = "BLOCKED"
    COMPLETION_UNKNOWN = "COMPLETION_UNKNOWN"


class CompletionKind(str, Enum):
    WRITE_PUBLISH_PINNED_READBACK = "WRITE_PUBLISH_PINNED_READBACK"
    READ_CLOSE_IDENTITY_COMPLETION_READBACK = "READ_CLOSE_IDENTITY_COMPLETION_READBACK"


class WritePurpose(str, Enum):
    CAPTURE_RAW_PUBLISH = "CAPTURE_RAW_PUBLISH"
    CAPTURE_CANONICAL_PUBLISH = "CAPTURE_CANONICAL_PUBLISH"
    QUALITY_SPEECH_CONTINUOUS_PUBLISH = "QUALITY_SPEECH_CONTINUOUS_PUBLISH"
    QUALITY_TRAINING_COPY_PUBLISH = "QUALITY_TRAINING_COPY_PUBLISH"
    DATASET_REVIEW_TRANSCRIPT_PUBLISH = "DATASET_REVIEW_TRANSCRIPT_PUBLISH"


class ReadPurpose(str, Enum):
    QUALITY_PROCESSING = "QUALITY_PROCESSING"
    DATASET_INTAKE = "DATASET_INTAKE"
    DATASET_REVIEW = "DATASET_REVIEW"
    VOICE_MODEL_TRAINING = "VOICE_MODEL_TRAINING"


WRITE_PURPOSE_MATRIX: Mapping[WritePurpose, tuple[str, ArtifactClass, str, str, str]] = {
    WritePurpose.CAPTURE_RAW_PUBLISH: (
        "TASK-047",
        ArtifactClass.RAW_CAPTURE,
        "OWNER_VOICE_CAPTURE",
        "TASK047_RAW_CAPTURE_OUTPUT",
        "Task047RawCaptureOutputV1",
    ),
    WritePurpose.CAPTURE_CANONICAL_PUBLISH: (
        "TASK-047",
        ArtifactClass.CANONICAL_PCM,
        "OWNER_VOICE_CAPTURE",
        "TASK047_CANONICAL_PCM_OUTPUT",
        "Task047CanonicalPcmOutputV1",
    ),
    WritePurpose.QUALITY_SPEECH_CONTINUOUS_PUBLISH: (
        "TASK-048",
        ArtifactClass.PROCESSED_SPEECH_CONTINUOUS,
        "OWNER_VOICE_DATA_PREPARATION",
        "TASK048_SPEECH_CONTINUOUS_OUTPUT",
        "Task048SpeechContinuousOutputV1",
    ),
    WritePurpose.QUALITY_TRAINING_COPY_PUBLISH: (
        "TASK-048",
        ArtifactClass.TRAINING_COPY,
        "OWNER_VOICE_DATA_PREPARATION",
        "TASK048_TRAINING_COPY_OUTPUT",
        "Task048TrainingCopyOutputV1",
    ),
    WritePurpose.DATASET_REVIEW_TRANSCRIPT_PUBLISH: (
        "TASK-046",
        ArtifactClass.REVIEW_TRANSCRIPT,
        "OWNER_VOICE_DATA_PREPARATION",
        "TASK046_REVIEW_TRANSCRIPT_OUTPUT",
        "Task046ReviewTranscriptOutputV1",
    ),
}

READ_PURPOSE_MATRIX: Mapping[ReadPurpose, tuple[str, frozenset[ArtifactClass], bool]] = {
    ReadPurpose.QUALITY_PROCESSING: (
        "TASK-048",
        frozenset({ArtifactClass.RAW_CAPTURE, ArtifactClass.CANONICAL_PCM}),
        True,
    ),
    ReadPurpose.DATASET_INTAKE: (
        "TASK-046",
        frozenset({ArtifactClass.PROCESSED_SPEECH_CONTINUOUS, ArtifactClass.TRAINING_COPY}),
        True,
    ),
    ReadPurpose.DATASET_REVIEW: (
        "TASK-046",
        frozenset({ArtifactClass.REVIEW_TRANSCRIPT}),
        False,
    ),
    ReadPurpose.VOICE_MODEL_TRAINING: (
        "TASK-046",
        frozenset({ArtifactClass.TRAINING_COPY}),
        True,
    ),
}


RECEIPT_FIELDS = (
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "receipt_role",
    "opaque_artifact_id",
    "logical_slot_ref",
    "generation_revision",
    "predecessor_receipt_sha256",
    "custody_binding_sha256",
    "owner_subject_revision_sha256",
    "purpose",
    "artifact_class",
    "content_sha256",
    "media_metadata_sha256",
    "opened_physical_identity_sha256",
    "cipher_backend_identity_sha256",
    "consent_rights_revision_sha256",
    "generation_event_sha256",
    "event_head_sha256",
    "observed_at",
    "fresh_until",
    "receipt_sha256",
)

EVENT_FIELDS = (
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "receipt_role",
    "event_kind",
    "logical_slot_ref",
    "artifact_class",
    "event_revision",
    "predecessor_event_sha256",
    "owner_subject_revision_sha256",
    "purpose",
    "consent_rights_revision_sha256",
    "created_at",
    "observed_at",
    "fresh_until",
    "trusted_time_binding_sha256",
    "published_generation_revision",
    "opaque_artifact_id",
    "custody_binding_sha256",
    "content_sha256",
    "media_metadata_sha256",
    "opened_physical_identity_sha256",
    "cipher_backend_identity_sha256",
    "target_generation_revision",
    "target_publish_event_sha256",
    "tombstone_decision_sha256",
    "event_sha256",
)

DECISION_FIELDS = (
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "receipt_role",
    "lease_kind",
    "purpose",
    "operation_id",
    "logical_slot_ref",
    "artifact_class",
    "generation_revision",
    "event_head_sha256",
    "state",
    "decision",
    "reason_code",
    "fixture_only",
    "authority_created",
    "body_access_granted",
    "production_backend_invoked",
    "private_media_effect_count",
    "decision_sha256",
)

COMPLETION_FIELDS = (
    "record_type",
    "schema_version",
    "canonical_owner_task",
    "receipt_role",
    "lease_kind",
    "operation_id",
    "completion_kind",
    "write_publish_pinned_readback_sha256",
    "read_close_handle_identity_sha256",
    "read_completion_readback_sha256",
    "fixture_only",
    "authority_created",
    "body_access_granted",
    "production_backend_invoked",
    "private_media_effect_count",
    "completion_sha256",
)


def _fail(reason: Task082Reason) -> None:
    raise Task082ContractError(reason)


def _exact(value: Mapping[str, Any], fields: Sequence[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != set(fields):
        _fail(Task082Reason.RECORD_FIELDS_INVALID)


def _snapshot_mapping(value: Any) -> dict[str, Any]:
    """Read an untrusted scalar mapping exactly once without echoing failures."""

    if not isinstance(value, Mapping):
        _fail(Task082Reason.REQUEST_INVALID)
    try:
        items = list(value.items())
    except Exception:
        _fail(Task082Reason.REQUEST_INVALID)
    result: dict[str, Any] = {}
    for key, item in items:
        if type(key) is not str or key in result:
            _fail(Task082Reason.RECORD_FIELDS_INVALID)
        if item is not None and type(item) not in {str, int, bool}:
            _fail(Task082Reason.RECORD_FIELDS_INVALID)
        result[key] = item
    return result


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        _fail(Task082Reason.IDENTIFIER_INVALID)
    folded = value.casefold()
    if (
        any(character in value for character in ("/", "\\", ":", "?", "#", "@"))
        or value in {".", ".."}
        or ".." in value
        or any(marker in folded for marker in _PRIVATE_MARKERS)
    ):
        _fail(Task082Reason.IDENTIFIER_INVALID)
    return value


def _digest(value: Any, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        _fail(Task082Reason.DIGEST_INVALID)
    try:
        return validate_sha256(value)
    except ValueError:
        _fail(Task082Reason.DIGEST_INVALID)


def _positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
        _fail(Task082Reason.INTEGER_INVALID)
    return value


def _is_digest(value: Any) -> bool:
    try:
        _digest(value)
    except Task082ContractError:
        return False
    return True


def _matching_digest_pair(actual: Any, expected: Any) -> bool:
    return _is_digest(actual) and _is_digest(expected) and actual == expected


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        _fail(Task082Reason.TIMESTAMP_INVALID)
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail(Task082Reason.TIMESTAMP_INVALID)
    if result.tzinfo != timezone.utc:
        _fail(Task082Reason.TIMESTAMP_INVALID)
    return result


def _enum(kind: type[Enum], value: Any) -> Enum:
    raw = value.value if isinstance(value, kind) else value
    try:
        return kind(raw)
    except (TypeError, ValueError):
        _fail(Task082Reason.RECORD_FIELDS_INVALID)


def _without(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def _record_digest(domain: bytes, value: Mapping[str, Any], field: str) -> str:
    return sha256_bytes(domain + canonical_json_bytes(_without(value, field)))


_CUSTODY_BINDING_FIELDS = (
    "opaque_artifact_id",
    "logical_slot_ref",
    "generation_revision",
    "owner_subject_revision_sha256",
    "purpose",
    "artifact_class",
    "content_sha256",
    "media_metadata_sha256",
    "opened_physical_identity_sha256",
    "cipher_backend_identity_sha256",
    "consent_rights_revision_sha256",
    "observed_at",
    "fresh_until",
)


def _custody_binding_digest(value: Mapping[str, Any]) -> str:
    try:
        preimage = {
            field: (
                value["generation_revision"]
                if field == "generation_revision" and "generation_revision" in value
                else value["published_generation_revision"]
                if field == "generation_revision"
                else value[field]
            )
            for field in _CUSTODY_BINDING_FIELDS
        }
    except (KeyError, TypeError):
        _fail(Task082Reason.RECORD_FIELDS_INVALID)
    if isinstance(preimage["artifact_class"], ArtifactClass):
        preimage["artifact_class"] = preimage["artifact_class"].value
    return sha256_bytes(CUSTODY_BINDING_DIGEST_DOMAIN + canonical_json_bytes(preimage))


def custody_staged_binding_sha256(**values: Any) -> str:
    """Compute the explicit pre-event binding; this is never a receipt digest."""

    normalized = dict(values)
    if isinstance(normalized.get("artifact_class"), ArtifactClass):
        normalized["artifact_class"] = normalized["artifact_class"].value
    snapshot = _snapshot_mapping(normalized)
    _exact(snapshot, _CUSTODY_BINDING_FIELDS)
    return _custody_binding_digest(snapshot)


def _json_depth(value: Any) -> int:
    maximum = 1
    pending: list[tuple[Any, int]] = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        maximum = max(maximum, depth)
        if maximum > MAX_JSON_DEPTH:
            return maximum
        if isinstance(current, Mapping):
            pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            pending.extend((item, depth + 1) for item in current)
    return maximum


def parse_strict_json(payload: bytes | str) -> Mapping[str, Any]:
    """Parse bounded UTF-8 JSON while rejecting ambiguous encodings and values."""

    if isinstance(payload, bytes):
        if len(payload) > MAX_JSON_BYTES:
            _fail(Task082Reason.JSON_OVERSIZE)
        if payload.startswith(b"\xef\xbb\xbf"):
            _fail(Task082Reason.JSON_INVALID)
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail(Task082Reason.JSON_INVALID)
    elif isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            _fail(Task082Reason.JSON_INVALID)
        if len(encoded) > MAX_JSON_BYTES or payload.startswith("\ufeff"):
            _fail(Task082Reason.JSON_OVERSIZE if len(encoded) > MAX_JSON_BYTES else Task082Reason.JSON_INVALID)
        text = payload
    else:
        _fail(Task082Reason.JSON_INVALID)

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(Task082Reason.JSON_DUPLICATE_KEY)
            result[key] = value
        return result

    def reject_constant(_: str) -> None:
        _fail(Task082Reason.JSON_NONFINITE)

    try:
        value = json.loads(text, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    except Task082ContractError:
        raise
    except RecursionError:
        _fail(Task082Reason.JSON_DEPTH_EXCEEDED)
    except (TypeError, ValueError, json.JSONDecodeError):
        _fail(Task082Reason.JSON_INVALID)
    if not isinstance(value, Mapping):
        _fail(Task082Reason.JSON_INVALID)
    if _json_depth(value) > MAX_JSON_DEPTH:
        _fail(Task082Reason.JSON_DEPTH_EXCEEDED)
    return value


@dataclass(frozen=True, slots=True)
class PrivateMediaCustodyReceipt:
    opaque_artifact_id: str
    logical_slot_ref: str
    generation_revision: int
    predecessor_receipt_sha256: str | None
    custody_binding_sha256: str
    owner_subject_revision_sha256: str
    purpose: str
    artifact_class: ArtifactClass
    content_sha256: str
    media_metadata_sha256: str
    opened_physical_identity_sha256: str
    cipher_backend_identity_sha256: str
    consent_rights_revision_sha256: str
    generation_event_sha256: str
    event_head_sha256: str
    observed_at: str
    fresh_until: str
    receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_class, ArtifactClass):
            _fail(Task082Reason.RECORD_FIELDS_INVALID)
        self._validate(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": RECEIPT_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": RECEIPT_ROLE,
            "opaque_artifact_id": self.opaque_artifact_id,
            "logical_slot_ref": self.logical_slot_ref,
            "generation_revision": self.generation_revision,
            "predecessor_receipt_sha256": self.predecessor_receipt_sha256,
            "custody_binding_sha256": self.custody_binding_sha256,
            "owner_subject_revision_sha256": self.owner_subject_revision_sha256,
            "purpose": self.purpose,
            "artifact_class": self.artifact_class.value,
            "content_sha256": self.content_sha256,
            "media_metadata_sha256": self.media_metadata_sha256,
            "opened_physical_identity_sha256": self.opened_physical_identity_sha256,
            "cipher_backend_identity_sha256": self.cipher_backend_identity_sha256,
            "consent_rights_revision_sha256": self.consent_rights_revision_sha256,
            "generation_event_sha256": self.generation_event_sha256,
            "event_head_sha256": self.event_head_sha256,
            "observed_at": self.observed_at,
            "fresh_until": self.fresh_until,
            "receipt_sha256": self.receipt_sha256,
        }

    @classmethod
    def create(cls, **values: Any) -> "PrivateMediaCustodyReceipt":
        body = {
            "record_type": RECEIPT_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": RECEIPT_ROLE,
            **values,
            "receipt_sha256": None,
        }
        if isinstance(body.get("artifact_class"), ArtifactClass):
            body["artifact_class"] = body["artifact_class"].value
        if "custody_binding_sha256" not in body:
            body["custody_binding_sha256"] = _custody_binding_digest(body)
        body["receipt_sha256"] = _record_digest(RECEIPT_DIGEST_DOMAIN, body, "receipt_sha256")
        return cls.from_mapping(body)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PrivateMediaCustodyReceipt":
        value = _snapshot_mapping(value)
        cls._validate(value)
        return cls(
            opaque_artifact_id=value["opaque_artifact_id"],
            logical_slot_ref=value["logical_slot_ref"],
            generation_revision=value["generation_revision"],
            predecessor_receipt_sha256=value["predecessor_receipt_sha256"],
            custody_binding_sha256=value["custody_binding_sha256"],
            owner_subject_revision_sha256=value["owner_subject_revision_sha256"],
            purpose=value["purpose"],
            artifact_class=ArtifactClass(value["artifact_class"]),
            content_sha256=value["content_sha256"],
            media_metadata_sha256=value["media_metadata_sha256"],
            opened_physical_identity_sha256=value["opened_physical_identity_sha256"],
            cipher_backend_identity_sha256=value["cipher_backend_identity_sha256"],
            consent_rights_revision_sha256=value["consent_rights_revision_sha256"],
            generation_event_sha256=value["generation_event_sha256"],
            event_head_sha256=value["event_head_sha256"],
            observed_at=value["observed_at"],
            fresh_until=value["fresh_until"],
            receipt_sha256=value["receipt_sha256"],
        )

    @staticmethod
    def _validate(value: Mapping[str, Any]) -> None:
        _exact(value, RECEIPT_FIELDS)
        if (
            value["record_type"] != RECEIPT_RECORD_TYPE
            or type(value["schema_version"]) is not int
            or value["schema_version"] != SCHEMA_VERSION
            or value["canonical_owner_task"] != TASK_OWNER
            or value["receipt_role"] != RECEIPT_ROLE
        ):
            _fail(Task082Reason.RECORD_DISCRIMINATOR_INVALID)
        _identifier(value["opaque_artifact_id"])
        _identifier(value["logical_slot_ref"])
        generation = _positive_int(value["generation_revision"])
        predecessor = _digest(value["predecessor_receipt_sha256"], nullable=True)
        if (generation == 1) != (predecessor is None):
            _fail(Task082Reason.EVENT_LINEAGE_MISMATCH)
        _digest(value["custody_binding_sha256"])
        for name in (
            "owner_subject_revision_sha256",
            "content_sha256",
            "media_metadata_sha256",
            "opened_physical_identity_sha256",
            "cipher_backend_identity_sha256",
            "consent_rights_revision_sha256",
            "generation_event_sha256",
            "event_head_sha256",
            "receipt_sha256",
        ):
            _digest(value[name])
        purpose = _enum(WritePurpose, value["purpose"])
        artifact_class = _enum(ArtifactClass, value["artifact_class"])
        if WRITE_PURPOSE_MATRIX[purpose][1] is not artifact_class:
            _fail(Task082Reason.WRONG_ARTIFACT_CLASS)
        observed = _timestamp(value["observed_at"])
        fresh = _timestamp(value["fresh_until"])
        if fresh <= observed:
            _fail(Task082Reason.STALE_BINDING)
        if value["custody_binding_sha256"] != _custody_binding_digest(value):
            _fail(Task082Reason.CUSTODY_BINDING_MISMATCH)
        if value["receipt_sha256"] != _record_digest(RECEIPT_DIGEST_DOMAIN, value, "receipt_sha256"):
            _fail(Task082Reason.RECEIPT_DIGEST_MISMATCH)


@dataclass(frozen=True, slots=True)
class PrivateMediaGenerationEvent:
    event_kind: GenerationEventKind
    logical_slot_ref: str
    artifact_class: ArtifactClass
    event_revision: int
    predecessor_event_sha256: str | None
    owner_subject_revision_sha256: str
    purpose: str
    consent_rights_revision_sha256: str
    created_at: str
    observed_at: str
    fresh_until: str
    trusted_time_binding_sha256: str
    published_generation_revision: int | None
    opaque_artifact_id: str | None
    custody_binding_sha256: str | None
    content_sha256: str | None
    media_metadata_sha256: str | None
    opened_physical_identity_sha256: str | None
    cipher_backend_identity_sha256: str | None
    target_generation_revision: int | None
    target_publish_event_sha256: str | None
    tombstone_decision_sha256: str | None
    event_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.event_kind, GenerationEventKind) or not isinstance(
            self.artifact_class, ArtifactClass
        ):
            _fail(Task082Reason.RECORD_FIELDS_INVALID)
        self._validate(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": EVENT_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": EVENT_ROLE,
            "event_kind": self.event_kind.value,
            "logical_slot_ref": self.logical_slot_ref,
            "artifact_class": self.artifact_class.value,
            "event_revision": self.event_revision,
            "predecessor_event_sha256": self.predecessor_event_sha256,
            "owner_subject_revision_sha256": self.owner_subject_revision_sha256,
            "purpose": self.purpose,
            "consent_rights_revision_sha256": self.consent_rights_revision_sha256,
            "created_at": self.created_at,
            "observed_at": self.observed_at,
            "fresh_until": self.fresh_until,
            "trusted_time_binding_sha256": self.trusted_time_binding_sha256,
            "published_generation_revision": self.published_generation_revision,
            "opaque_artifact_id": self.opaque_artifact_id,
            "custody_binding_sha256": self.custody_binding_sha256,
            "content_sha256": self.content_sha256,
            "media_metadata_sha256": self.media_metadata_sha256,
            "opened_physical_identity_sha256": self.opened_physical_identity_sha256,
            "cipher_backend_identity_sha256": self.cipher_backend_identity_sha256,
            "target_generation_revision": self.target_generation_revision,
            "target_publish_event_sha256": self.target_publish_event_sha256,
            "tombstone_decision_sha256": self.tombstone_decision_sha256,
            "event_sha256": self.event_sha256,
        }

    @classmethod
    def create(cls, **values: Any) -> "PrivateMediaGenerationEvent":
        body = {
            "record_type": EVENT_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": EVENT_ROLE,
            **values,
            "event_sha256": None,
        }
        for field in ("event_kind", "artifact_class"):
            if isinstance(body.get(field), Enum):
                body[field] = body[field].value
        body["event_sha256"] = _record_digest(EVENT_DIGEST_DOMAIN, body, "event_sha256")
        return cls.from_mapping(body)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PrivateMediaGenerationEvent":
        value = _snapshot_mapping(value)
        cls._validate(value)
        return cls(
            event_kind=GenerationEventKind(value["event_kind"]),
            logical_slot_ref=value["logical_slot_ref"],
            artifact_class=ArtifactClass(value["artifact_class"]),
            event_revision=value["event_revision"],
            predecessor_event_sha256=value["predecessor_event_sha256"],
            owner_subject_revision_sha256=value["owner_subject_revision_sha256"],
            purpose=value["purpose"],
            consent_rights_revision_sha256=value["consent_rights_revision_sha256"],
            created_at=value["created_at"],
            observed_at=value["observed_at"],
            fresh_until=value["fresh_until"],
            trusted_time_binding_sha256=value["trusted_time_binding_sha256"],
            published_generation_revision=value["published_generation_revision"],
            opaque_artifact_id=value["opaque_artifact_id"],
            custody_binding_sha256=value["custody_binding_sha256"],
            content_sha256=value["content_sha256"],
            media_metadata_sha256=value["media_metadata_sha256"],
            opened_physical_identity_sha256=value["opened_physical_identity_sha256"],
            cipher_backend_identity_sha256=value["cipher_backend_identity_sha256"],
            target_generation_revision=value["target_generation_revision"],
            target_publish_event_sha256=value["target_publish_event_sha256"],
            tombstone_decision_sha256=value["tombstone_decision_sha256"],
            event_sha256=value["event_sha256"],
        )

    @staticmethod
    def _validate(value: Mapping[str, Any]) -> None:
        _exact(value, EVENT_FIELDS)
        if (
            value["record_type"] != EVENT_RECORD_TYPE
            or type(value["schema_version"]) is not int
            or value["schema_version"] != SCHEMA_VERSION
            or value["canonical_owner_task"] != TASK_OWNER
            or value["receipt_role"] != EVENT_ROLE
        ):
            _fail(Task082Reason.RECORD_DISCRIMINATOR_INVALID)
        kind = _enum(GenerationEventKind, value["event_kind"])
        _identifier(value["logical_slot_ref"])
        artifact_class = _enum(ArtifactClass, value["artifact_class"])
        revision = _positive_int(value["event_revision"])
        predecessor = _digest(value["predecessor_event_sha256"], nullable=True)
        if (revision == 1) != (predecessor is None):
            _fail(Task082Reason.EVENT_PREDECESSOR_MISMATCH)
        _digest(value["owner_subject_revision_sha256"])
        purpose = _enum(WritePurpose, value["purpose"])
        if WRITE_PURPOSE_MATRIX[purpose][1] is not artifact_class:
            _fail(Task082Reason.WRONG_ARTIFACT_CLASS)
        _digest(value["consent_rights_revision_sha256"])
        created = _timestamp(value["created_at"])
        observed = _timestamp(value["observed_at"])
        fresh = _timestamp(value["fresh_until"])
        if not created <= observed < fresh:
            _fail(Task082Reason.TIMESTAMP_INVALID)
        _digest(value["trusted_time_binding_sha256"])

        publish_fields = (
            "published_generation_revision",
            "opaque_artifact_id",
            "custody_binding_sha256",
            "content_sha256",
            "media_metadata_sha256",
            "opened_physical_identity_sha256",
            "cipher_backend_identity_sha256",
        )
        tombstone_fields = (
            "target_generation_revision",
            "target_publish_event_sha256",
            "tombstone_decision_sha256",
        )
        if kind is GenerationEventKind.GENERATION_PUBLISHED:
            if any(value[field] is None for field in publish_fields) or any(
                value[field] is not None for field in tombstone_fields
            ):
                _fail(Task082Reason.EVENT_VARIANT_FIELDS_INVALID)
            _positive_int(value["published_generation_revision"])
            _identifier(value["opaque_artifact_id"])
            for field in publish_fields[2:]:
                _digest(value[field])
            if value["custody_binding_sha256"] != _custody_binding_digest(value):
                _fail(Task082Reason.CUSTODY_BINDING_MISMATCH)
        else:
            if any(value[field] is not None for field in publish_fields) or any(
                value[field] is None for field in tombstone_fields
            ):
                _fail(Task082Reason.EVENT_VARIANT_FIELDS_INVALID)
            _positive_int(value["target_generation_revision"])
            for field in tombstone_fields[1:]:
                _digest(value[field])
        _digest(value["event_sha256"])
        if value["event_sha256"] != _record_digest(EVENT_DIGEST_DOMAIN, value, "event_sha256"):
            _fail(Task082Reason.EVENT_DIGEST_MISMATCH)


_CURRENTNESS_TOKEN = object()


@dataclass(frozen=True, slots=True, init=False)
class GenerationCurrentness:
    state: CurrentnessState
    reason_code: Task082Reason
    logical_slot_ref: str | None
    artifact_class: ArtifactClass | None
    current_generation_revision: int | None
    current_publish_event_sha256: str | None
    current_custody_binding_sha256: str | None
    event_head_sha256: str | None
    source_event_count: int
    expected_event_head_sha256: str
    currentness_sha256: str
    fixture_only: bool
    authority_created: bool
    body_access_granted: bool
    production_backend_invoked: bool
    private_media_effect_count: int

    @classmethod
    def _create(
        cls,
        token: object,
        *,
        state: CurrentnessState,
        reason_code: Task082Reason,
        logical_slot_ref: str | None,
        artifact_class: ArtifactClass | None,
        current_generation_revision: int | None,
        current_publish_event_sha256: str | None,
        current_custody_binding_sha256: str | None,
        event_head_sha256: str | None,
        source_event_count: int,
        expected_event_head_sha256: str,
    ) -> "GenerationCurrentness":
        if token is not _CURRENTNESS_TOKEN:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        body = {
            "state": state.value,
            "reason_code": reason_code.value,
            "logical_slot_ref": logical_slot_ref,
            "artifact_class": artifact_class.value if artifact_class else None,
            "current_generation_revision": current_generation_revision,
            "current_publish_event_sha256": current_publish_event_sha256,
            "current_custody_binding_sha256": current_custody_binding_sha256,
            "event_head_sha256": event_head_sha256,
            "source_event_count": source_event_count,
            "expected_event_head_sha256": expected_event_head_sha256,
            "fixture_only": True,
            "authority_created": False,
            "body_access_granted": False,
            "production_backend_invoked": False,
            "private_media_effect_count": 0,
            "currentness_sha256": None,
        }
        body["currentness_sha256"] = _record_digest(
            CURRENTNESS_DIGEST_DOMAIN, body, "currentness_sha256"
        )
        if cls is not GenerationCurrentness:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        result = object.__new__(cls)
        for field, item in body.items():
            if field == "state":
                item = state
            elif field == "reason_code":
                item = reason_code
            elif field == "artifact_class":
                item = artifact_class
            object.__setattr__(result, field, item)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "reason_code": self.reason_code.value,
            "logical_slot_ref": self.logical_slot_ref,
            "artifact_class": self.artifact_class.value if self.artifact_class else None,
            "current_generation_revision": self.current_generation_revision,
            "current_publish_event_sha256": self.current_publish_event_sha256,
            "current_custody_binding_sha256": self.current_custody_binding_sha256,
            "event_head_sha256": self.event_head_sha256,
            "source_event_count": self.source_event_count,
            "expected_event_head_sha256": self.expected_event_head_sha256,
            "fixture_only": self.fixture_only,
            "authority_created": self.authority_created,
            "body_access_granted": self.body_access_granted,
            "production_backend_invoked": self.production_backend_invoked,
            "private_media_effect_count": self.private_media_effect_count,
            "currentness_sha256": self.currentness_sha256,
        }

    def __reduce__(self) -> Any:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)


def _not_confirmed(
    reason: Task082Reason, *, expected_event_head_sha256: str, source_event_count: int
) -> GenerationCurrentness:
    return GenerationCurrentness._create(
        _CURRENTNESS_TOKEN,
        state=CurrentnessState.CURRENTNESS_NOT_CONFIRMED,
        reason_code=reason,
        logical_slot_ref=None,
        artifact_class=None,
        current_generation_revision=None,
        current_publish_event_sha256=None,
        current_custody_binding_sha256=None,
        event_head_sha256=None,
        source_event_count=source_event_count,
        expected_event_head_sha256=expected_event_head_sha256,
    )


def derive_generation_currentness(
    events: Sequence[PrivateMediaGenerationEvent | Mapping[str, Any]],
    *,
    observed_at: str,
    expected_event_head_sha256: str,
    expected_event_count: int,
    expected_current_custody_binding_sha256: str | None,
) -> GenerationCurrentness:
    """Derive current generation solely from one closed immutable event chain."""

    safe_expected_head = sha256_bytes(b"TASK082_INVALID_EXPECTED_EVENT_HEAD")
    source_count = 0
    try:
        observed = _timestamp(observed_at)
        expected_head = _digest(expected_event_head_sha256)
        assert expected_head is not None
        safe_expected_head = expected_head
        _positive_int(expected_event_count)
        expected_custody = _digest(expected_current_custody_binding_sha256, nullable=True)
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            return _not_confirmed(
                Task082Reason.CURRENTNESS_NOT_CONFIRMED,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        try:
            event_snapshot = tuple(islice(iter(events), MAX_EVENTS + 1))
        except Exception:
            return _not_confirmed(
                Task082Reason.CURRENTNESS_NOT_CONFIRMED,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        source_count = len(event_snapshot)
        if not 1 <= source_count <= MAX_EVENTS:
            return _not_confirmed(
                Task082Reason.CURRENTNESS_NOT_CONFIRMED,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        if source_count != expected_event_count:
            return _not_confirmed(
                Task082Reason.EVENT_REVISION_GAP,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        parsed = [
            PrivateMediaGenerationEvent.from_mapping(event.as_dict())
            if type(event) is PrivateMediaGenerationEvent
            else PrivateMediaGenerationEvent.from_mapping(event)
            for event in event_snapshot
        ]
        if parsed[-1].event_sha256 != expected_head:
            return _not_confirmed(
                Task082Reason.EVENT_PREDECESSOR_MISMATCH,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        first = parsed[0]
        lineage = (
            first.logical_slot_ref,
            first.artifact_class,
            first.owner_subject_revision_sha256,
            first.purpose,
            first.consent_rights_revision_sha256,
        )
        previous: PrivateMediaGenerationEvent | None = None
        previous_observed: datetime | None = None
        last_publish_generation = 0
        current_generation: int | None = None
        current_publish: str | None = None
        current_custody: str | None = None
        for expected_revision, event in enumerate(parsed, 1):
            if event.event_revision != expected_revision:
                return _not_confirmed(Task082Reason.EVENT_REVISION_GAP, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
            expected_predecessor = None if previous is None else previous.event_sha256
            if event.predecessor_event_sha256 != expected_predecessor:
                return _not_confirmed(Task082Reason.EVENT_PREDECESSOR_MISMATCH, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
            if (
                event.logical_slot_ref,
                event.artifact_class,
                event.owner_subject_revision_sha256,
                event.purpose,
                event.consent_rights_revision_sha256,
            ) != lineage:
                return _not_confirmed(Task082Reason.EVENT_LINEAGE_MISMATCH, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
            event_observed = _timestamp(event.observed_at)
            if observed < event_observed or (previous_observed is not None and event_observed < previous_observed):
                return _not_confirmed(Task082Reason.TIMESTAMP_INVALID, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
            if observed >= _timestamp(event.fresh_until):
                return _not_confirmed(Task082Reason.STALE_BINDING, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
            if event.event_kind is GenerationEventKind.GENERATION_PUBLISHED:
                assert event.published_generation_revision is not None
                if event.published_generation_revision != last_publish_generation + 1:
                    return _not_confirmed(Task082Reason.PUBLISH_GENERATION_GAP, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
                last_publish_generation = event.published_generation_revision
                current_generation = event.published_generation_revision
                current_publish = event.event_sha256
                current_custody = event.custody_binding_sha256
            else:
                if (
                    current_generation is None
                    or event.target_generation_revision != current_generation
                    or event.target_publish_event_sha256 != current_publish
                ):
                    return _not_confirmed(Task082Reason.TOMBSTONE_TARGET_MISMATCH, expected_event_head_sha256=safe_expected_head, source_event_count=source_count)
                current_generation = None
                current_publish = None
                current_custody = None
            previous = event
            previous_observed = event_observed
        assert previous is not None
        if current_custody != expected_custody:
            return _not_confirmed(
                Task082Reason.EVENT_LINEAGE_MISMATCH,
                expected_event_head_sha256=safe_expected_head,
                source_event_count=source_count,
            )
        if current_generation is None:
            return GenerationCurrentness._create(
                _CURRENTNESS_TOKEN,
                state=CurrentnessState.NO_CURRENT_GENERATION,
                reason_code=Task082Reason.NO_CURRENT_GENERATION,
                logical_slot_ref=first.logical_slot_ref,
                artifact_class=first.artifact_class,
                current_generation_revision=None,
                current_publish_event_sha256=None,
                current_custody_binding_sha256=None,
                event_head_sha256=previous.event_sha256,
                source_event_count=source_count,
                expected_event_head_sha256=safe_expected_head,
            )
        return GenerationCurrentness._create(
            _CURRENTNESS_TOKEN,
            state=CurrentnessState.CURRENT,
            reason_code=Task082Reason.CURRENT,
            logical_slot_ref=first.logical_slot_ref,
            artifact_class=first.artifact_class,
            current_generation_revision=current_generation,
            current_publish_event_sha256=current_publish,
            current_custody_binding_sha256=current_custody,
            event_head_sha256=previous.event_sha256,
            source_event_count=source_count,
            expected_event_head_sha256=safe_expected_head,
        )
    except Task082ContractError as exc:
        return _not_confirmed(
            exc.reason,
            expected_event_head_sha256=safe_expected_head,
            source_event_count=source_count,
        )


_DECISION_TOKEN = object()


@dataclass(frozen=True, slots=True, init=False)
class LeaseDecision:
    lease_kind: LeaseKind
    purpose: str
    operation_id: str
    logical_slot_ref: str
    artifact_class: ArtifactClass
    generation_revision: int
    event_head_sha256: str | None
    state: LeaseState
    decision: LeaseDecisionKind
    reason_code: Task082Reason
    decision_sha256: str

    @classmethod
    def _create(
        cls,
        token: object,
        *,
        lease_kind: LeaseKind,
        purpose: str,
        operation_id: str,
        logical_slot_ref: str,
        artifact_class: ArtifactClass,
        generation_revision: int,
        event_head_sha256: str | None,
        state: LeaseState,
        decision: LeaseDecisionKind,
        reason_code: Task082Reason,
        decision_sha256: str,
    ) -> "LeaseDecision":
        if token is not _DECISION_TOKEN or cls is not LeaseDecision:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        result = object.__new__(cls)
        for field, item in (
            ("lease_kind", lease_kind),
            ("purpose", purpose),
            ("operation_id", operation_id),
            ("logical_slot_ref", logical_slot_ref),
            ("artifact_class", artifact_class),
            ("generation_revision", generation_revision),
            ("event_head_sha256", event_head_sha256),
            ("state", state),
            ("decision", decision),
            ("reason_code", reason_code),
            ("decision_sha256", decision_sha256),
        ):
            object.__setattr__(result, field, item)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": DECISION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": DECISION_ROLE,
            "lease_kind": self.lease_kind.value,
            "purpose": self.purpose,
            "operation_id": self.operation_id,
            "logical_slot_ref": self.logical_slot_ref,
            "artifact_class": self.artifact_class.value,
            "generation_revision": self.generation_revision,
            "event_head_sha256": self.event_head_sha256,
            "state": self.state.value,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "fixture_only": True,
            "authority_created": False,
            "body_access_granted": False,
            "production_backend_invoked": False,
            "private_media_effect_count": 0,
            "decision_sha256": self.decision_sha256,
        }

    def __reduce__(self) -> Any:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)


def _decision(
    *,
    lease_kind: LeaseKind,
    purpose: str,
    operation_id: str,
    logical_slot_ref: str,
    artifact_class: ArtifactClass,
    generation_revision: int,
    event_head_sha256: str | None,
    state: LeaseState,
    reason: Task082Reason,
) -> LeaseDecision:
    decision = (
        LeaseDecisionKind.READY_FIXTURE_ONLY
        if reason is Task082Reason.READY
        else LeaseDecisionKind.COMPLETION_UNKNOWN
        if reason is Task082Reason.COMPLETION_UNKNOWN
        else LeaseDecisionKind.BLOCKED
    )
    body = {
        "record_type": DECISION_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "canonical_owner_task": TASK_OWNER,
        "receipt_role": DECISION_ROLE,
        "lease_kind": lease_kind.value,
        "purpose": purpose,
        "operation_id": operation_id,
        "logical_slot_ref": logical_slot_ref,
        "artifact_class": artifact_class.value,
        "generation_revision": generation_revision,
        "event_head_sha256": event_head_sha256,
        "state": state.value,
        "decision": decision.value,
        "reason_code": reason.value,
        "fixture_only": True,
        "authority_created": False,
        "body_access_granted": False,
        "production_backend_invoked": False,
        "private_media_effect_count": 0,
        "decision_sha256": None,
    }
    body["decision_sha256"] = _record_digest(DECISION_DIGEST_DOMAIN, body, "decision_sha256")
    return LeaseDecision._create(
        _DECISION_TOKEN,
        lease_kind=lease_kind,
        purpose=purpose,
        operation_id=operation_id,
        logical_slot_ref=logical_slot_ref,
        artifact_class=artifact_class,
        generation_revision=generation_revision,
        event_head_sha256=event_head_sha256,
        state=state,
        decision=decision,
        reason_code=reason,
        decision_sha256=body["decision_sha256"],
    )


def _safe_decision_identity(
    *,
    lease_kind: LeaseKind,
    purpose: Any,
    operation_id: Any,
    logical_slot_ref: Any,
    artifact_class: Any,
    generation_revision: Any,
    event_head_sha256: Any,
) -> dict[str, Any]:
    try:
        normalized_purpose = _identifier(purpose)
    except Task082ContractError:
        normalized_purpose = "INVALID"
    try:
        normalized_operation = _identifier(operation_id)
    except Task082ContractError:
        normalized_operation = "INVALID"
    try:
        normalized_slot = _identifier(logical_slot_ref)
    except Task082ContractError:
        normalized_slot = "INVALID"
    try:
        normalized_class = _enum(ArtifactClass, artifact_class)
    except Task082ContractError:
        normalized_class = ArtifactClass.RAW_CAPTURE
    try:
        normalized_generation = _positive_int(generation_revision)
    except Task082ContractError:
        normalized_generation = 1
    try:
        normalized_head = _digest(event_head_sha256, nullable=True)
    except Task082ContractError:
        normalized_head = None
    return {
        "lease_kind": lease_kind,
        "purpose": normalized_purpose,
        "operation_id": normalized_operation,
        "logical_slot_ref": normalized_slot,
        "artifact_class": normalized_class,
        "generation_revision": normalized_generation,
        "event_head_sha256": normalized_head,
    }


def compile_fixture_write_lease_admission(
    *,
    purpose: WritePurpose | str,
    expected_purpose: WritePurpose | str,
    producer_task: str,
    producer_output_role: str,
    artifact_class: ArtifactClass | str,
    operation_id: str,
    expected_operation_id: str,
    logical_slot_ref: str,
    generation_revision: int,
    expected_generation_revision: int,
    owner_subject_revision_sha256: str,
    expected_owner_subject_revision_sha256: str,
    consent_scope: str,
    consent_rights_revision_sha256: str,
    expected_consent_rights_revision_sha256: str,
    current_event_head_sha256: str | None,
    expected_event_head_sha256: str | None,
    producer_output_record_type: str,
    expected_producer_output_record_type: str,
    producer_output_receipt_sha256: str,
    expected_producer_output_receipt_sha256: str,
    producer_output_currentness_sha256: str,
    expected_producer_output_currentness_sha256: str,
    producer_output_current: bool,
    issued_at: str,
    expires_at: str,
    observed_at: str,
    revoked: bool = False,
    receipt_as_capability: bool = False,
) -> LeaseDecision:
    identity = _safe_decision_identity(
        lease_kind=LeaseKind.WRITE,
        purpose=purpose.value if isinstance(purpose, WritePurpose) else purpose,
        operation_id=operation_id,
        logical_slot_ref=logical_slot_ref,
        artifact_class=artifact_class,
        generation_revision=generation_revision,
        event_head_sha256=current_event_head_sha256,
    )
    reason = Task082Reason.READY
    try:
        normalized_purpose = _enum(WritePurpose, purpose)
        normalized_expected_purpose = _enum(WritePurpose, expected_purpose)
        normalized_class = _enum(ArtifactClass, artifact_class)
        _identifier(producer_task)
        _identifier(producer_output_role)
        _identifier(operation_id)
        _identifier(expected_operation_id)
        _identifier(logical_slot_ref)
        _identifier(consent_scope)
        _identifier(producer_output_record_type)
        _identifier(expected_producer_output_record_type)
        _positive_int(generation_revision)
        _positive_int(expected_generation_revision)
        for digest in (
            owner_subject_revision_sha256,
            expected_owner_subject_revision_sha256,
            consent_rights_revision_sha256,
            expected_consent_rights_revision_sha256,
            producer_output_receipt_sha256,
            expected_producer_output_receipt_sha256,
            producer_output_currentness_sha256,
            expected_producer_output_currentness_sha256,
        ):
            _digest(digest)
        _digest(current_event_head_sha256, nullable=True)
        _digest(expected_event_head_sha256, nullable=True)
        issued, expires, observed = _timestamp(issued_at), _timestamp(expires_at), _timestamp(observed_at)
        if normalized_purpose is not normalized_expected_purpose:
            reason = Task082Reason.WRONG_PURPOSE
        elif generation_revision != expected_generation_revision:
            reason = Task082Reason.WRONG_GENERATION
        elif (generation_revision == 1) != (current_event_head_sha256 is None):
            reason = Task082Reason.STALE_BINDING
        elif not issued <= observed < expires:
            reason = Task082Reason.STALE_BINDING
        elif not isinstance(revoked, bool) or not isinstance(receipt_as_capability, bool):
            reason = Task082Reason.REQUEST_INVALID
        elif producer_output_current is not True:
            reason = Task082Reason.STALE_BINDING
        elif revoked:
            reason = Task082Reason.REVOKED
        elif receipt_as_capability:
            reason = Task082Reason.RECEIPT_AS_CAPABILITY
        else:
            (
                expected_producer,
                expected_class,
                expected_consent_scope,
                expected_role,
                expected_record_type,
            ) = WRITE_PURPOSE_MATRIX[normalized_purpose]
            if producer_task != expected_producer:
                reason = Task082Reason.WRONG_PRODUCER
            elif normalized_class is not expected_class:
                reason = Task082Reason.WRONG_ARTIFACT_CLASS
            elif producer_output_role != expected_role:
                reason = Task082Reason.WRONG_OUTPUT_ROLE
            elif (
                producer_output_record_type != expected_record_type
                or expected_producer_output_record_type != expected_record_type
            ):
                reason = Task082Reason.WRONG_OUTPUT_ROLE
            elif producer_output_receipt_sha256 != expected_producer_output_receipt_sha256:
                reason = Task082Reason.STALE_BINDING
            elif producer_output_currentness_sha256 != expected_producer_output_currentness_sha256:
                reason = Task082Reason.STALE_BINDING
            elif consent_scope != expected_consent_scope:
                reason = Task082Reason.WRONG_CONSENT
            elif consent_rights_revision_sha256 != expected_consent_rights_revision_sha256:
                reason = Task082Reason.WRONG_CONSENT
            elif owner_subject_revision_sha256 != expected_owner_subject_revision_sha256:
                reason = Task082Reason.WRONG_SUBJECT
            elif operation_id != expected_operation_id:
                reason = Task082Reason.WRONG_OPERATION
            elif current_event_head_sha256 != expected_event_head_sha256:
                reason = Task082Reason.STALE_BINDING
    except (Task082ContractError, KeyError):
        reason = Task082Reason.REQUEST_INVALID
    return _decision(**identity, state=LeaseState.PREPARED, reason=reason)


def compile_fixture_read_lease_admission(
    *,
    receipt: PrivateMediaCustodyReceipt | Mapping[str, Any],
    currentness: GenerationCurrentness,
    purpose: ReadPurpose | str,
    expected_purpose: ReadPurpose | str,
    consumer_task: str,
    operation_id: str,
    expected_operation_id: str,
    expected_owner_subject_revision_sha256: str,
    expected_consent_rights_revision_sha256: str,
    issued_at: str,
    expires_at: str,
    observed_at: str,
    asset_adoption_readback_sha256: str | None = None,
    expected_asset_adoption_readback_sha256: str | None = None,
    producer_output_receipt_sha256: str | None = None,
    expected_producer_output_receipt_sha256: str | None = None,
    dataset_review_binding_sha256: str | None = None,
    expected_dataset_review_binding_sha256: str | None = None,
    dataset_snapshot_sha256: str | None = None,
    expected_dataset_snapshot_sha256: str | None = None,
    durable_job_head_sha256: str | None = None,
    expected_durable_job_head_sha256: str | None = None,
    run_recipe_binding_sha256: str | None = None,
    expected_run_recipe_binding_sha256: str | None = None,
    h3_authorization_sha256: str | None = None,
    expected_h3_authorization_sha256: str | None = None,
    training_compound_operation_sha256: str | None = None,
    expected_training_compound_operation_sha256: str | None = None,
    revoked: bool = False,
    receipt_as_capability: bool = False,
) -> LeaseDecision:
    receipt_snapshot_error = False
    if type(receipt) is PrivateMediaCustodyReceipt:
        receipt_mapping: Mapping[str, Any] = receipt.as_dict()
    else:
        try:
            receipt_mapping = _snapshot_mapping(receipt)
        except Task082ContractError:
            receipt_mapping = {}
            receipt_snapshot_error = True
    fallback_class = receipt_mapping.get("artifact_class", ArtifactClass.RAW_CAPTURE.value)
    fallback_generation = receipt_mapping.get("generation_revision", 1)
    fallback_slot = receipt_mapping.get("logical_slot_ref", "INVALID")
    fallback_head = receipt_mapping.get("event_head_sha256")
    identity = _safe_decision_identity(
        lease_kind=LeaseKind.READ,
        purpose=purpose.value if isinstance(purpose, ReadPurpose) else purpose,
        operation_id=operation_id,
        logical_slot_ref=fallback_slot,
        artifact_class=fallback_class,
        generation_revision=fallback_generation,
        event_head_sha256=fallback_head,
    )
    reason = Task082Reason.READY
    try:
        if receipt_snapshot_error:
            _fail(Task082Reason.REQUEST_INVALID)
        parsed_receipt = PrivateMediaCustodyReceipt.from_mapping(receipt_mapping)
        normalized_purpose = _enum(ReadPurpose, purpose)
        normalized_expected_purpose = _enum(ReadPurpose, expected_purpose)
        _identifier(consumer_task)
        _identifier(operation_id)
        _identifier(expected_operation_id)
        _digest(expected_owner_subject_revision_sha256)
        _digest(expected_consent_rights_revision_sha256)
        issued, expires, observed = _timestamp(issued_at), _timestamp(expires_at), _timestamp(observed_at)
        if normalized_purpose is not normalized_expected_purpose:
            reason = Task082Reason.WRONG_PURPOSE
        elif not issued <= observed < expires or observed >= _timestamp(parsed_receipt.fresh_until):
            reason = Task082Reason.STALE_BINDING
        elif not isinstance(revoked, bool) or not isinstance(receipt_as_capability, bool):
            reason = Task082Reason.REQUEST_INVALID
        elif revoked:
            reason = Task082Reason.REVOKED
        elif receipt_as_capability:
            reason = Task082Reason.RECEIPT_AS_CAPABILITY
        elif (
            type(currentness) is not GenerationCurrentness
            or currentness.state is not CurrentnessState.CURRENT
            or currentness.reason_code is not Task082Reason.CURRENT
            or currentness.fixture_only is not True
            or currentness.authority_created is not False
            or currentness.body_access_granted is not False
            or currentness.production_backend_invoked is not False
            or currentness.private_media_effect_count != 0
            or currentness.event_head_sha256 != currentness.expected_event_head_sha256
            or currentness.currentness_sha256
            != _record_digest(CURRENTNESS_DIGEST_DOMAIN, currentness.as_dict(), "currentness_sha256")
        ):
            reason = Task082Reason.CURRENTNESS_NOT_CONFIRMED
        elif parsed_receipt.owner_subject_revision_sha256 != expected_owner_subject_revision_sha256:
            reason = Task082Reason.WRONG_SUBJECT
        elif parsed_receipt.consent_rights_revision_sha256 != expected_consent_rights_revision_sha256:
            reason = Task082Reason.WRONG_CONSENT
        elif operation_id != expected_operation_id:
            reason = Task082Reason.WRONG_OPERATION
        elif (
            parsed_receipt.logical_slot_ref != currentness.logical_slot_ref
            or parsed_receipt.artifact_class is not currentness.artifact_class
            or parsed_receipt.generation_revision != currentness.current_generation_revision
            or parsed_receipt.generation_event_sha256 != currentness.current_publish_event_sha256
            or parsed_receipt.custody_binding_sha256
            != currentness.current_custody_binding_sha256
            or parsed_receipt.event_head_sha256 != currentness.event_head_sha256
        ):
            reason = Task082Reason.WRONG_GENERATION
        else:
            expected_consumer, allowed_classes, requires_asset = READ_PURPOSE_MATRIX[normalized_purpose]
            if consumer_task != expected_consumer:
                reason = Task082Reason.WRONG_CONSUMER
            elif parsed_receipt.artifact_class not in allowed_classes:
                reason = Task082Reason.WRONG_ARTIFACT_CLASS
            elif requires_asset and (
                asset_adoption_readback_sha256 is None
                or expected_asset_adoption_readback_sha256 is None
                or asset_adoption_readback_sha256 != expected_asset_adoption_readback_sha256
                or not _is_digest(asset_adoption_readback_sha256)
                or not _is_digest(expected_asset_adoption_readback_sha256)
            ):
                reason = Task082Reason.WRONG_ASSET_ADOPTION
            elif normalized_purpose is ReadPurpose.DATASET_REVIEW and (
                asset_adoption_readback_sha256 is not None or expected_asset_adoption_readback_sha256 is not None
            ):
                reason = Task082Reason.WRONG_ASSET_ADOPTION
            else:
                producer_pair = (
                    producer_output_receipt_sha256,
                    expected_producer_output_receipt_sha256,
                )
                review_pair = (
                    dataset_review_binding_sha256,
                    expected_dataset_review_binding_sha256,
                )
                training_pairs = (
                    (dataset_snapshot_sha256, expected_dataset_snapshot_sha256),
                    (durable_job_head_sha256, expected_durable_job_head_sha256),
                    (run_recipe_binding_sha256, expected_run_recipe_binding_sha256),
                    (h3_authorization_sha256, expected_h3_authorization_sha256),
                    (
                        training_compound_operation_sha256,
                        expected_training_compound_operation_sha256,
                    ),
                )
                if normalized_purpose in {ReadPurpose.QUALITY_PROCESSING, ReadPurpose.DATASET_INTAKE}:
                    if not _matching_digest_pair(*producer_pair):
                        reason = Task082Reason.REQUIRED_BINDING_MISSING
                    elif any(item is not None for item in review_pair) or any(
                        item is not None for pair in training_pairs for item in pair
                    ):
                        reason = Task082Reason.WRONG_PURPOSE
                elif normalized_purpose is ReadPurpose.DATASET_REVIEW:
                    if not _matching_digest_pair(*review_pair):
                        reason = Task082Reason.REQUIRED_BINDING_MISSING
                    elif any(item is not None for item in producer_pair) or any(
                        item is not None for pair in training_pairs for item in pair
                    ):
                        reason = Task082Reason.WRONG_PURPOSE
                elif normalized_purpose is ReadPurpose.VOICE_MODEL_TRAINING:
                    if not all(_matching_digest_pair(*pair) for pair in training_pairs):
                        reason = Task082Reason.REQUIRED_BINDING_MISSING
                    elif any(item is not None for item in producer_pair + review_pair):
                        reason = Task082Reason.WRONG_PURPOSE
                else:
                    reason = Task082Reason.WRONG_PURPOSE
    except (Task082ContractError, KeyError, AttributeError):
        reason = Task082Reason.REQUEST_INVALID
    return _decision(**identity, state=LeaseState.PREPARED, reason=reason)


@dataclass(frozen=True, slots=True, init=False)
class LeaseCompletionReadback:
    lease_kind: LeaseKind
    operation_id: str
    completion_kind: CompletionKind
    write_publish_pinned_readback_sha256: str | None
    read_close_handle_identity_sha256: str | None
    read_completion_readback_sha256: str | None
    completion_sha256: str

    @classmethod
    def create(
        cls,
        *,
        lease_kind: LeaseKind | str,
        operation_id: str,
        completion_kind: CompletionKind | str,
        write_publish_pinned_readback_sha256: str | None,
        read_close_handle_identity_sha256: str | None,
        read_completion_readback_sha256: str | None,
    ) -> "LeaseCompletionReadback":
        if cls is not LeaseCompletionReadback:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        body = {
            "record_type": COMPLETION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": COMPLETION_ROLE,
            "lease_kind": lease_kind.value if isinstance(lease_kind, LeaseKind) else lease_kind,
            "operation_id": operation_id,
            "completion_kind": (
                completion_kind.value if isinstance(completion_kind, CompletionKind) else completion_kind
            ),
            "write_publish_pinned_readback_sha256": write_publish_pinned_readback_sha256,
            "read_close_handle_identity_sha256": read_close_handle_identity_sha256,
            "read_completion_readback_sha256": read_completion_readback_sha256,
            "fixture_only": True,
            "authority_created": False,
            "body_access_granted": False,
            "production_backend_invoked": False,
            "private_media_effect_count": 0,
            "completion_sha256": None,
        }
        body["completion_sha256"] = _record_digest(
            COMPLETION_DIGEST_DOMAIN, body, "completion_sha256"
        )
        return cls.from_mapping(body)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LeaseCompletionReadback":
        if cls is not LeaseCompletionReadback:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        snapshot = _snapshot_mapping(value)
        _exact(snapshot, COMPLETION_FIELDS)
        if (
            snapshot["record_type"] != COMPLETION_RECORD_TYPE
            or type(snapshot["schema_version"]) is not int
            or snapshot["schema_version"] != SCHEMA_VERSION
            or snapshot["canonical_owner_task"] != TASK_OWNER
            or snapshot["receipt_role"] != COMPLETION_ROLE
        ):
            _fail(Task082Reason.RECORD_DISCRIMINATOR_INVALID)
        lease_kind = _enum(LeaseKind, snapshot["lease_kind"])
        completion_kind = _enum(CompletionKind, snapshot["completion_kind"])
        _identifier(snapshot["operation_id"])
        write_digest = _digest(snapshot["write_publish_pinned_readback_sha256"], nullable=True)
        close_digest = _digest(snapshot["read_close_handle_identity_sha256"], nullable=True)
        readback_digest = _digest(snapshot["read_completion_readback_sha256"], nullable=True)
        if lease_kind is LeaseKind.WRITE:
            if (
                completion_kind is not CompletionKind.WRITE_PUBLISH_PINNED_READBACK
                or write_digest is None
                or close_digest is not None
                or readback_digest is not None
            ):
                _fail(Task082Reason.WRONG_PURPOSE)
        elif (
            completion_kind is not CompletionKind.READ_CLOSE_IDENTITY_COMPLETION_READBACK
            or write_digest is not None
            or close_digest is None
            or readback_digest is None
        ):
            _fail(Task082Reason.WRONG_PURPOSE)
        if (
            snapshot["fixture_only"] is not True
            or snapshot["authority_created"] is not False
            or snapshot["body_access_granted"] is not False
            or snapshot["production_backend_invoked"] is not False
            or type(snapshot["private_media_effect_count"]) is not int
            or snapshot["private_media_effect_count"] != 0
        ):
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        _digest(snapshot["completion_sha256"])
        if snapshot["completion_sha256"] != _record_digest(
            COMPLETION_DIGEST_DOMAIN, snapshot, "completion_sha256"
        ):
            _fail(Task082Reason.DIGEST_INVALID)
        result = object.__new__(cls)
        for field, item in (
            ("lease_kind", lease_kind),
            ("operation_id", snapshot["operation_id"]),
            ("completion_kind", completion_kind),
            ("write_publish_pinned_readback_sha256", write_digest),
            ("read_close_handle_identity_sha256", close_digest),
            ("read_completion_readback_sha256", readback_digest),
            ("completion_sha256", snapshot["completion_sha256"]),
        ):
            object.__setattr__(result, field, item)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": COMPLETION_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "canonical_owner_task": TASK_OWNER,
            "receipt_role": COMPLETION_ROLE,
            "lease_kind": self.lease_kind.value,
            "operation_id": self.operation_id,
            "completion_kind": self.completion_kind.value,
            "write_publish_pinned_readback_sha256": self.write_publish_pinned_readback_sha256,
            "read_close_handle_identity_sha256": self.read_close_handle_identity_sha256,
            "read_completion_readback_sha256": self.read_completion_readback_sha256,
            "fixture_only": True,
            "authority_created": False,
            "body_access_granted": False,
            "production_backend_invoked": False,
            "private_media_effect_count": 0,
            "completion_sha256": self.completion_sha256,
        }

    def __reduce__(self) -> Any:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)


_SENTINEL_TOKEN = object()


class Task082FixtureLeaseSentinel:
    """Non-serializable in-memory fixture state; never a production lease."""

    __slots__ = ("_decision", "_state")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)

    def __init__(self, token: object, decision: LeaseDecision):
        if (
            token is not _SENTINEL_TOKEN
            or type(self) is not Task082FixtureLeaseSentinel
            or type(decision) is not LeaseDecision
            or decision.reason_code is not Task082Reason.READY
            or decision.decision is not LeaseDecisionKind.READY_FIXTURE_ONLY
            or decision.state is not LeaseState.PREPARED
            or decision.decision_sha256
            != _record_digest(DECISION_DIGEST_DOMAIN, decision.as_dict(), "decision_sha256")
        ):
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        object.__setattr__(self, "_decision", decision)
        object.__setattr__(self, "_state", LeaseState.PREPARED)

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)

    def _transition(self, token: object, target: LeaseState) -> None:
        if token is not _SENTINEL_TOKEN or type(self) is not Task082FixtureLeaseSentinel:
            _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
        object.__setattr__(self, "_state", target)

    @property
    def state(self) -> LeaseState:
        return self._state

    def __reduce__(self) -> Any:
        raise TypeError(Task082Reason.RECEIPT_AS_CAPABILITY.value)


def mint_fixture_lease_sentinel(decision: LeaseDecision) -> Task082FixtureLeaseSentinel:
    return Task082FixtureLeaseSentinel(_SENTINEL_TOKEN, decision)


_LEASE_TRANSITIONS: Mapping[LeaseState, frozenset[LeaseState]] = {
    LeaseState.PREPARED: frozenset({LeaseState.ISSUED, LeaseState.EXPIRED, LeaseState.FAILED_CLOSED}),
    LeaseState.ISSUED: frozenset({LeaseState.OPEN_STARTED, LeaseState.EXPIRED, LeaseState.FAILED_CLOSED}),
    LeaseState.OPEN_STARTED: frozenset(
        {LeaseState.CONSUMED, LeaseState.COMPLETION_UNKNOWN, LeaseState.FAILED_CLOSED}
    ),
    LeaseState.CONSUMED: frozenset(),
    LeaseState.EXPIRED: frozenset(),
    LeaseState.COMPLETION_UNKNOWN: frozenset(),
    LeaseState.FAILED_CLOSED: frozenset(),
}


def transition_fixture_lease(
    sentinel: Task082FixtureLeaseSentinel,
    target: LeaseState | str,
    *,
    completion_readback: LeaseCompletionReadback | Mapping[str, Any] | None = None,
    expected_completion_readback_sha256: str | None = None,
    lost_reply: bool = False,
) -> LeaseDecision:
    if type(sentinel) is not Task082FixtureLeaseSentinel:
        _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
    normalized_target = _enum(LeaseState, target)
    current = sentinel._state
    if type(lost_reply) is not bool:
        _fail(Task082Reason.REQUEST_INVALID)
    if lost_reply:
        if current is not LeaseState.OPEN_STARTED or normalized_target is not LeaseState.CONSUMED:
            _fail(Task082Reason.STATE_TRANSITION_INVALID)
        normalized_target = LeaseState.COMPLETION_UNKNOWN
    elif normalized_target is LeaseState.CONSUMED:
        try:
            parsed_completion = LeaseCompletionReadback.from_mapping(
                completion_readback.as_dict()
                if type(completion_readback) is LeaseCompletionReadback
                else completion_readback  # type: ignore[arg-type]
            )
            expected_completion = _digest(expected_completion_readback_sha256)
            original = sentinel._decision
            if (
                parsed_completion.lease_kind is not original.lease_kind
                or parsed_completion.operation_id != original.operation_id
                or parsed_completion.completion_sha256 != expected_completion
            ):
                normalized_target = LeaseState.COMPLETION_UNKNOWN
        except (Task082ContractError, TypeError, AttributeError):
            normalized_target = LeaseState.COMPLETION_UNKNOWN
    elif completion_readback is not None or expected_completion_readback_sha256 is not None:
        _fail(Task082Reason.STATE_TRANSITION_INVALID)
    if normalized_target not in _LEASE_TRANSITIONS[current]:
        _fail(Task082Reason.REPLAY if current in {
            LeaseState.CONSUMED,
            LeaseState.EXPIRED,
            LeaseState.COMPLETION_UNKNOWN,
            LeaseState.FAILED_CLOSED,
        } else Task082Reason.STATE_TRANSITION_INVALID)
    sentinel._transition(_SENTINEL_TOKEN, normalized_target)
    reason = (
        Task082Reason.COMPLETION_UNKNOWN
        if normalized_target is LeaseState.COMPLETION_UNKNOWN
        else Task082Reason.STALE_BINDING
        if normalized_target is LeaseState.EXPIRED
        else Task082Reason.STATE_TRANSITION_INVALID
        if normalized_target is LeaseState.FAILED_CLOSED
        else Task082Reason.READY
    )
    original = sentinel._decision
    return _decision(
        lease_kind=original.lease_kind,
        purpose=original.purpose,
        operation_id=original.operation_id,
        logical_slot_ref=original.logical_slot_ref,
        artifact_class=original.artifact_class,
        generation_revision=original.generation_revision,
        event_head_sha256=original.event_head_sha256,
        state=normalized_target,
        reason=reason,
    )


def read_fixture_lease_state(sentinel: Task082FixtureLeaseSentinel) -> LeaseDecision:
    """Return body-free state only; duplicate callers never receive a capability."""

    if type(sentinel) is not Task082FixtureLeaseSentinel:
        _fail(Task082Reason.RECEIPT_AS_CAPABILITY)
    original = sentinel._decision
    reason = (
        Task082Reason.COMPLETION_UNKNOWN
        if sentinel.state is LeaseState.COMPLETION_UNKNOWN
        else Task082Reason.STALE_BINDING
        if sentinel.state is LeaseState.EXPIRED
        else Task082Reason.STATE_TRANSITION_INVALID
        if sentinel.state is LeaseState.FAILED_CLOSED
        else Task082Reason.READY
    )
    return _decision(
        lease_kind=original.lease_kind,
        purpose=original.purpose,
        operation_id=original.operation_id,
        logical_slot_ref=original.logical_slot_ref,
        artifact_class=original.artifact_class,
        generation_revision=original.generation_revision,
        event_head_sha256=original.event_head_sha256,
        state=sentinel.state,
        reason=reason,
    )


def parse_custody_receipt(payload: bytes | str) -> PrivateMediaCustodyReceipt:
    return PrivateMediaCustodyReceipt.from_mapping(parse_strict_json(payload))


def parse_generation_event(payload: bytes | str) -> PrivateMediaGenerationEvent:
    return PrivateMediaGenerationEvent.from_mapping(parse_strict_json(payload))


__all__ = [
    "ArtifactClass",
    "CompletionKind",
    "CurrentnessState",
    "GenerationCurrentness",
    "GenerationEventKind",
    "LeaseDecision",
    "LeaseDecisionKind",
    "LeaseCompletionReadback",
    "LeaseKind",
    "LeaseState",
    "PrivateMediaCustodyReceipt",
    "PrivateMediaGenerationEvent",
    "ReadPurpose",
    "Task082ContractError",
    "Task082FixtureLeaseSentinel",
    "Task082Reason",
    "WritePurpose",
    "compile_fixture_read_lease_admission",
    "compile_fixture_write_lease_admission",
    "custody_staged_binding_sha256",
    "derive_generation_currentness",
    "mint_fixture_lease_sentinel",
    "parse_custody_receipt",
    "parse_generation_event",
    "parse_strict_json",
    "read_fixture_lease_state",
    "transition_fixture_lease",
]
