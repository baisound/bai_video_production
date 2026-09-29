"""TASK-041 durable owner history and current read for audio media review.

The store persists metadata-only review bundles under one fixed Product Project
coordinate.  It never reads audio bodies, starts playback, renders waveforms,
mutates media, or grants downstream execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult, exclusive_file_update_lock
from .audio_workspace_media_review import (
    AudioMediaReviewDecision,
    AudioMediaReviewIntent,
    AudioMediaSourceBinding,
    DerivedAudioAssetProposal,
    ExternalAudioReviewReceiptBinding,
    PlaybackWaveformCapabilityBinding,
    validate_external_review_inclusion,
    validate_record,
)
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


FORMAT_ID = "bai-video-production.audio-media-review-history"
FORMAT_VERSION = "1.0.0"
RELATIVE_PATH = "state/audio-media-review-history.json"
MAX_ENTRIES = 10_000
MAX_BYTES = 16 * 1024 * 1024

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_ROOT_FIELDS = {
    "snapshot_version", "task_owner", "project_id", "store_revision", "entries",
    "audio_body_embedded", "playback_authority", "media_mutation_authority",
    "external_execution_authority", "snapshot_sha256",
}
_ENTRY_FIELDS = {
    "source_binding", "capability_binding", "review_intent",
    "external_review_receipt", "derived_asset_proposal", "review_decision",
    "entry_sha256",
}
_OWNER_READ_SEAL = object()


def _require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    folded = value.casefold()
    if (
        "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value)
        or ".." in value.split("/")
        or any(term in folded for term in ("credential", "password", "secret", "license-key", "serial-number"))
    ):
        raise ValueError(f"{field} violates the private boundary")
    return value


def _require_sha(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return validate_sha256(value, field_name=field)


def _entry_body(
    source: AudioMediaSourceBinding,
    capability: PlaybackWaveformCapabilityBinding,
    intent: AudioMediaReviewIntent,
    receipt: ExternalAudioReviewReceiptBinding | None,
    proposal: DerivedAudioAssetProposal | None,
    decision: AudioMediaReviewDecision,
) -> dict[str, Any]:
    return {
        "source_binding": source.to_dict(),
        "capability_binding": capability.to_dict(),
        "review_intent": intent.to_dict(),
        "external_review_receipt": None if receipt is None else receipt.to_dict(),
        "derived_asset_proposal": None if proposal is None else proposal.to_dict(),
        "review_decision": decision.to_dict(),
    }


@dataclass(frozen=True, slots=True)
class AudioMediaReviewHistoryEntry:
    source: AudioMediaSourceBinding
    capability: PlaybackWaveformCapabilityBinding
    intent: AudioMediaReviewIntent
    receipt: ExternalAudioReviewReceiptBinding | None
    proposal: DerivedAudioAssetProposal | None
    decision: AudioMediaReviewDecision
    entry_sha256: str

    @classmethod
    def create(
        cls,
        *,
        source: AudioMediaSourceBinding,
        capability: PlaybackWaveformCapabilityBinding,
        intent: AudioMediaReviewIntent,
        decision: AudioMediaReviewDecision,
        receipt: ExternalAudioReviewReceiptBinding | None = None,
        proposal: DerivedAudioAssetProposal | None = None,
    ) -> "AudioMediaReviewHistoryEntry":
        body = _entry_body(source, capability, intent, receipt, proposal, decision)
        return cls(source, capability, intent, receipt, proposal, decision, sha256_bytes(canonical_json_bytes(body))).validated()

    @property
    def project_id(self) -> str:
        return str(self.intent.to_dict()["project_id"])

    @property
    def decision_id(self) -> str:
        return str(self.decision.to_dict()["decision_id"])

    @property
    def revision(self) -> int:
        return int(self.decision.to_dict()["revision"])

    def validated(self) -> "AudioMediaReviewHistoryEntry":
        intent = self.intent.to_dict()
        decision = self.decision.to_dict()
        if intent["source_binding_sha256"] != self.source.record_sha256:
            raise ValueError("review intent source binding mismatch")
        if intent["capability_binding_sha256"] != self.capability.record_sha256:
            raise ValueError("review intent capability binding mismatch")
        if decision["intent_sha256"] != self.intent.record_sha256:
            raise ValueError("review decision intent mismatch")
        if decision["source_binding_sha256"] != self.source.record_sha256:
            raise ValueError("review decision source mismatch")

        receipt_sha = decision["external_review_receipt_sha256"]
        if self.receipt is None:
            if receipt_sha is not None:
                raise ValueError("review decision receipt is missing")
        else:
            if receipt_sha != self.receipt.record_sha256:
                raise ValueError("review decision receipt mismatch")
            inclusion = validate_external_review_inclusion(
                receipt=self.receipt,
                intent=self.intent,
                source=self.source,
                capability=self.capability,
            )
            if inclusion["classification"] != "ACCEPT_PROVEN_EXTERNAL_REVIEW":
                raise ValueError("external review receipt does not prove the reviewed inputs")

        proposal_sha = decision["derived_proposal_sha256"]
        if self.proposal is None:
            if proposal_sha is not None:
                raise ValueError("review decision proposal is missing")
        else:
            proposal = self.proposal.to_dict()
            if proposal_sha != self.proposal.record_sha256:
                raise ValueError("review decision proposal mismatch")
            if proposal["source_binding_sha256"] != self.source.record_sha256:
                raise ValueError("derived proposal source mismatch")
            if proposal["review_intent_sha256"] != self.intent.record_sha256:
                raise ValueError("derived proposal intent mismatch")

        body = _entry_body(
            self.source, self.capability, self.intent, self.receipt, self.proposal, self.decision
        )
        _require_sha(self.entry_sha256, "entry_sha256")
        if self.entry_sha256 != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("entry_sha256 mismatch")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {**_entry_body(
            self.source, self.capability, self.intent, self.receipt, self.proposal, self.decision
        ), "entry_sha256": self.entry_sha256}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AudioMediaReviewHistoryEntry":
        if set(value) != _ENTRY_FIELDS:
            raise ValueError("review history entry fields are not exact")
        for field in ("source_binding", "capability_binding", "review_intent", "review_decision"):
            if not isinstance(value[field], Mapping):
                raise ValueError(f"{field} must be an object")
        receipt_value = value["external_review_receipt"]
        proposal_value = value["derived_asset_proposal"]
        if receipt_value is not None and not isinstance(receipt_value, Mapping):
            raise ValueError("external_review_receipt must be an object or null")
        if proposal_value is not None and not isinstance(proposal_value, Mapping):
            raise ValueError("derived_asset_proposal must be an object or null")
        source = validate_record(value["source_binding"], expected_type="AudioMediaSourceBinding")
        capability = validate_record(value["capability_binding"], expected_type="PlaybackWaveformCapabilityBinding")
        intent = validate_record(value["review_intent"], expected_type="AudioMediaReviewIntent")
        decision = validate_record(value["review_decision"], expected_type="AudioMediaReviewDecision")
        receipt = None if receipt_value is None else validate_record(
            receipt_value, expected_type="ExternalAudioReviewReceiptBinding"
        )
        proposal = None if proposal_value is None else validate_record(
            proposal_value, expected_type="DerivedAudioAssetProposal"
        )
        assert isinstance(source, AudioMediaSourceBinding)
        assert isinstance(capability, PlaybackWaveformCapabilityBinding)
        assert isinstance(intent, AudioMediaReviewIntent)
        assert isinstance(decision, AudioMediaReviewDecision)
        assert receipt is None or isinstance(receipt, ExternalAudioReviewReceiptBinding)
        assert proposal is None or isinstance(proposal, DerivedAudioAssetProposal)
        return cls(source, capability, intent, receipt, proposal, decision, value["entry_sha256"]).validated()


class AudioMediaReviewHistory:
    def __init__(self, project_id: str) -> None:
        self.project_id = _require_id(project_id, "project_id")
        self.store_revision = 0
        self.entries: list[AudioMediaReviewHistoryEntry] = []

    def append(self, entry: AudioMediaReviewHistoryEntry) -> bool:
        entry.validated()
        if entry.project_id != self.project_id:
            raise ProductError(
                "ERR_AUDIO_REVIEW_PROJECT_MISMATCH",
                "Review entry belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        matching = [item for item in self.entries if item.decision_id == entry.decision_id]
        if matching:
            current = matching[-1]
            if current.entry_sha256 == entry.entry_sha256:
                return False
            if entry.revision != current.revision + 1:
                raise ProductError(
                    "ERR_AUDIO_REVIEW_REVISION_CONFLICT",
                    "Review decision revision does not follow the current owner head",
                    ProductErrorCategory.STATE,
                )
            if entry.decision.to_dict()["parent_record_sha256"] != current.decision.record_sha256:
                raise ProductError(
                    "ERR_AUDIO_REVIEW_PARENT_CONFLICT",
                    "Review decision parent does not match the current owner head",
                    ProductErrorCategory.STATE,
                )
        elif entry.revision != 1 or entry.decision.to_dict()["parent_record_sha256"] is not None:
            raise ProductError(
                "ERR_AUDIO_REVIEW_FIRST_REVISION",
                "A new review decision history must begin at revision one",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if len(self.entries) >= MAX_ENTRIES:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_LIMIT",
                "Review history reached its bounded maximum",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        self.entries.append(entry)
        self.store_revision += 1
        return True

    def current(self, decision_id: str) -> AudioMediaReviewHistoryEntry | None:
        _require_id(decision_id, "decision_id")
        for entry in reversed(self.entries):
            if entry.decision_id == decision_id:
                return entry
        return None


class AudioMediaReviewCurrentState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    NOT_FOUND = "NOT_FOUND"
    STORE_NOT_FOUND = "STORE_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class AudioMediaReviewCurrentRead:
    state: AudioMediaReviewCurrentState
    project_id: str
    decision_id: str
    store_revision: int | None
    snapshot_sha256: str | None
    entry: AudioMediaReviewHistoryEntry | None
    reason_codes: tuple[str, ...]
    owner_store_read: bool
    owner_origin_authenticated: bool
    currentness_verified: bool
    _issuer_seal: object = field(repr=False, compare=False)
    audio_read_started: bool = False
    playback_started: bool = False
    waveform_render_started: bool = False
    media_mutation_started: bool = False
    external_execution_started: bool = False

    def __post_init__(self) -> None:
        if self._issuer_seal is not _OWNER_READ_SEAL:
            raise ValueError("current review read must be issued by the TASK-041 owner store")
        if any((
            self.audio_read_started, self.playback_started,
            self.waveform_render_started, self.media_mutation_started,
            self.external_execution_started,
        )):
            raise ValueError("current review read cannot carry effect authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "project_id": self.project_id,
            "decision_id": self.decision_id,
            "store_revision": self.store_revision,
            "snapshot_sha256": self.snapshot_sha256,
            "entry_sha256": None if self.entry is None else self.entry.entry_sha256,
            "decision_sha256": None if self.entry is None else self.entry.decision.record_sha256,
            "audio_workspace_snapshot_sha256": None if self.entry is None else self.entry.intent.to_dict()["audio_workspace_snapshot_sha256"],
            "reason_codes": list(self.reason_codes),
            "owner_store_read": self.owner_store_read,
            "owner_origin_authenticated": self.owner_origin_authenticated,
            "currentness_verified": self.currentness_verified,
            "audio_read_started": False,
            "playback_started": False,
            "waveform_render_started": False,
            "media_mutation_started": False,
            "external_execution_started": False,
        }


class AudioMediaReviewHistoryStore:
    @staticmethod
    def snapshot(history: AudioMediaReviewHistory) -> dict[str, Any]:
        body = {
            "snapshot_version": FORMAT_VERSION,
            "task_owner": "TASK-041",
            "project_id": history.project_id,
            "store_revision": history.store_revision,
            "entries": [entry.to_dict() for entry in history.entries],
            "audio_body_embedded": False,
            "playback_authority": False,
            "media_mutation_authority": False,
            "external_execution_authority": False,
        }
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def serialize(cls, history: AudioMediaReviewHistory) -> bytes:
        value = canonical_json_bytes(cls.snapshot(history))
        if len(value) > MAX_BYTES:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_SIZE",
                "Review history exceeds the allowed byte bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        return value

    @classmethod
    def parse(
        cls, document: Mapping[str, Any], *, expected_project_id: str | None = None
    ) -> AudioMediaReviewHistory:
        if set(document) != _ROOT_FIELDS:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_FIELDS",
                "Review history fields are not exact",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
        if document.get("snapshot_sha256") != sha256_bytes(canonical_json_bytes(body)):
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_CHECKSUM",
                "Review history checksum mismatch",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if document.get("snapshot_version") != FORMAT_VERSION or document.get("task_owner") != "TASK-041":
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_VERSION",
                "Review history version or owner is unsupported",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        if any(document.get(field) is not False for field in (
            "audio_body_embedded", "playback_authority", "media_mutation_authority",
            "external_execution_authority",
        )):
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_BOUNDARY",
                "Review history violates effect or privacy boundaries",
                ProductErrorCategory.SECURITY,
            )
        rows = document.get("entries")
        revision = document.get("store_revision")
        if (
            isinstance(revision, bool) or not isinstance(revision, int) or revision < 0
            or not isinstance(rows, list) or len(rows) > MAX_ENTRIES
        ):
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_SHAPE",
                "Review history revision or entries are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            history = AudioMediaReviewHistory(document["project_id"])
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("review history row must be an object")
                if not history.append(AudioMediaReviewHistoryEntry.from_dict(row)):
                    raise ValueError("duplicate review history entry")
            if history.store_revision != revision:
                raise ValueError("store_revision does not equal accepted entry count")
            if expected_project_id is not None and history.project_id != expected_project_id:
                raise ProductError(
                    "ERR_AUDIO_REVIEW_PROJECT_MISMATCH",
                    "Review history belongs to another Project",
                    ProductErrorCategory.SECURITY,
                )
            return history
        except ProductError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_INVALID",
                "Review history contains invalid records",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    @classmethod
    def parse_bytes(
        cls, value: bytes, *, expected_project_id: str | None = None
    ) -> AudioMediaReviewHistory:
        if not isinstance(value, bytes) or not 0 < len(value) <= MAX_BYTES:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_SIZE",
                "Review history size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
            )
        try:
            document = json.loads(value.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_READ",
                "Review history is not UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_INVALID",
                "Review history root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return cls.parse(document, expected_project_id=expected_project_id)

    @staticmethod
    def project_path(project_root: str | Path) -> Path:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_AUDIO_REVIEW_PROJECT_ROOT",
                "Project root must be an existing regular non-symlink directory",
                ProductErrorCategory.SECURITY,
            )
        state = root / "state"
        if state.is_symlink() or (state.exists() and not state.is_dir()):
            raise ProductError(
                "ERR_AUDIO_REVIEW_STATE_DIRECTORY",
                "Project state coordinate must be a regular non-symlink directory",
                ProductErrorCategory.SECURITY,
            )
        return root / RELATIVE_PATH

    @classmethod
    def load_project(
        cls, project_root: str | Path, *, expected_project_id: str
    ) -> AudioMediaReviewHistory:
        target = cls.project_path(project_root)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_FILE",
                "Review history must be a regular non-symlink file",
                ProductErrorCategory.SECURITY,
            )
        try:
            value = target.read_bytes()
        except OSError as exc:
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_READ",
                "Review history could not be read",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return cls.parse_bytes(value, expected_project_id=expected_project_id)

    @classmethod
    def save_project(
        cls,
        project_root: str | Path,
        history: AudioMediaReviewHistory,
        *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = cls.project_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink() or not target.parent.is_dir() or target.is_symlink():
            raise ProductError(
                "ERR_AUDIO_REVIEW_HISTORY_FILE",
                "Refusing a symlink or non-directory review history coordinate",
                ProductErrorCategory.SECURITY,
            )
        with exclusive_file_update_lock(target):
            if target.exists():
                if not target.is_file():
                    raise ProductError(
                        "ERR_AUDIO_REVIEW_HISTORY_FILE",
                        "Review history target must be a regular file",
                        ProductErrorCategory.SECURITY,
                    )
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError(
                        "ERR_AUDIO_REVIEW_CAS_REQUIRED",
                        "Replacing review history requires its exact previous checksum",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                current = cls.snapshot(cls.load_project(
                    project_root, expected_project_id=history.project_id
                ))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError(
                        "ERR_AUDIO_REVIEW_REVISION_CONFLICT",
                        "Review history changed before save; reload before retry",
                        ProductErrorCategory.STATE,
                        details={"current_snapshot_sha256": current},
                    )
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError(
                    "ERR_AUDIO_REVIEW_PREVIOUS_MISSING",
                    "Expected previous review history does not exist",
                    ProductErrorCategory.STATE,
                )
            document = cls.snapshot(history)
            return AtomicJsonWriter.write(
                target,
                document,
                validator=lambda value: cls.parse(value, expected_project_id=history.project_id),
            )

    @classmethod
    def read_current(
        cls,
        project_root: str | Path,
        *,
        project_id: str,
        decision_id: str,
        expected_audio_workspace_snapshot_sha256: str,
        expected_decision_sha256: str | None = None,
    ) -> AudioMediaReviewCurrentRead:
        _require_id(project_id, "project_id")
        _require_id(decision_id, "decision_id")
        _require_sha(expected_audio_workspace_snapshot_sha256, "expected_audio_workspace_snapshot_sha256")
        if expected_decision_sha256 is not None:
            _require_sha(expected_decision_sha256, "expected_decision_sha256")
        target = cls.project_path(project_root)
        if not target.exists() and not target.is_symlink():
            return AudioMediaReviewCurrentRead(
                AudioMediaReviewCurrentState.STORE_NOT_FOUND,
                project_id, decision_id, None, None, None,
                ("OWNER_STORE_NOT_FOUND",), False, False, False, _OWNER_READ_SEAL,
            )
        history = cls.load_project(project_root, expected_project_id=project_id)
        snapshot_sha = str(cls.snapshot(history)["snapshot_sha256"])
        entry = history.current(decision_id)
        if entry is None:
            return AudioMediaReviewCurrentRead(
                AudioMediaReviewCurrentState.NOT_FOUND,
                project_id, decision_id, history.store_revision, snapshot_sha, None,
                ("DECISION_NOT_FOUND",), True, True, False, _OWNER_READ_SEAL,
            )
        reasons: list[str] = []
        if entry.intent.to_dict()["audio_workspace_snapshot_sha256"] != expected_audio_workspace_snapshot_sha256:
            reasons.append("AUDIO_WORKSPACE_SNAPSHOT_CHANGED")
        if expected_decision_sha256 is not None and entry.decision.record_sha256 != expected_decision_sha256:
            reasons.append("DECISION_HEAD_CHANGED")
        state = AudioMediaReviewCurrentState.CURRENT if not reasons else AudioMediaReviewCurrentState.STALE
        return AudioMediaReviewCurrentRead(
            state,
            project_id,
            decision_id,
            history.store_revision,
            snapshot_sha,
            entry,
            tuple(sorted(reasons)),
            True,
            True,
            not reasons,
            _OWNER_READ_SEAL,
        )


__all__ = [
    "AudioMediaReviewCurrentRead", "AudioMediaReviewCurrentState",
    "AudioMediaReviewHistory", "AudioMediaReviewHistoryEntry",
    "AudioMediaReviewHistoryStore", "FORMAT_ID", "FORMAT_VERSION",
    "MAX_BYTES", "MAX_ENTRIES", "RELATIVE_PATH",
]
