"""TASK-035 durable owner history and current read for audio round trips.

The store persists metadata-only ``AudioRoundTripManifest`` records at one
fixed Product Project coordinate. It never reads audio, launches REAPER,
renders media, promotes Assets, mutates Resolve, or publishes output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .reaper_audio_finishing import AudioRoundTripManifest
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


FORMAT_ID = "bai-video-production.audio-round-trip-history"
FORMAT_VERSION = "1.0.0"
RELATIVE_PATH = "state/audio-round-trip-history.json"
MAX_ENTRIES = 10_000
MAX_BYTES = 16 * 1024 * 1024

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_ROOT_FIELDS = {
    "snapshot_version", "task_owner", "project_id", "store_revision", "entries",
    "audio_body_embedded", "external_execution_authority",
    "asset_promotion_authority", "resolve_mutation_authority",
    "publication_authority", "snapshot_sha256",
}
_OWNER_READ_SEAL = object()


def _require_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:/", value)
        or ".." in value.split("/")
        or any(term in folded for term in (
            "credential", "password", "secret", "license-key", "serial-number",
        ))
    ):
        raise ValueError(f"{field_name} violates the private boundary")
    return value


def _require_sha(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a SHA-256 digest")
    return validate_sha256(value, field_name=field_name)


class AudioRoundTripCurrentState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    NOT_FOUND = "NOT_FOUND"
    STORE_NOT_FOUND = "STORE_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class AudioRoundTripCurrentRead:
    state: AudioRoundTripCurrentState
    project_id: str
    manifest_id: str
    store_revision: int | None
    snapshot_sha256: str | None
    manifest: AudioRoundTripManifest | None
    reason_codes: tuple[str, ...]
    owner_store_read: bool
    owner_origin_authenticated: bool
    currentness_verified: bool
    _issuer_seal: object = field(repr=False, compare=False)
    audio_read_started: bool = False
    external_execution_started: bool = False
    reaper_launch_started: bool = False
    audio_render_started: bool = False
    asset_promotion_started: bool = False
    resolve_mutation_started: bool = False
    publication_started: bool = False

    def __post_init__(self) -> None:
        if self._issuer_seal is not _OWNER_READ_SEAL:
            raise ValueError("current round-trip read must be issued by the TASK-035 owner store")
        if any((
            self.audio_read_started,
            self.external_execution_started,
            self.reaper_launch_started,
            self.audio_render_started,
            self.asset_promotion_started,
            self.resolve_mutation_started,
            self.publication_started,
        )):
            raise ValueError("current round-trip read cannot carry effect authority")

    def to_dict(self) -> dict[str, Any]:
        manifest = None if self.manifest is None else self.manifest.to_dict()
        return {
            "state": self.state.value,
            "project_id": self.project_id,
            "manifest_id": self.manifest_id,
            "store_revision": self.store_revision,
            "snapshot_sha256": self.snapshot_sha256,
            "manifest_sha256": None if self.manifest is None else self.manifest.record_sha256,
            "manifest_revision": None if manifest is None else manifest["revision"],
            "round_trip_state": None if manifest is None else manifest["round_trip_state"],
            "reason_codes": list(self.reason_codes),
            "owner_store_read": self.owner_store_read,
            "owner_origin_authenticated": self.owner_origin_authenticated,
            "currentness_verified": self.currentness_verified,
            "audio_read_started": False,
            "external_execution_started": False,
            "reaper_launch_started": False,
            "audio_render_started": False,
            "asset_promotion_started": False,
            "resolve_mutation_started": False,
            "publication_started": False,
        }


class AudioRoundTripHistory:
    def __init__(self, project_id: str) -> None:
        self.project_id = _require_id(project_id, "project_id")
        self.store_revision = 0
        self.entries: list[AudioRoundTripManifest] = []

    def current(self, manifest_id: str) -> AudioRoundTripManifest | None:
        for entry in reversed(self.entries):
            if entry.to_dict()["manifest_id"] == manifest_id:
                return entry
        return None

    def append(self, manifest: AudioRoundTripManifest) -> bool:
        value = manifest.to_dict()
        if value["project_id"] != self.project_id:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_PROJECT_MISMATCH",
                "Round-trip manifest belongs to another Project",
                ProductErrorCategory.SECURITY,
            )
        if any(entry.record_sha256 == manifest.record_sha256 for entry in self.entries):
            return False
        if len(self.entries) >= MAX_ENTRIES:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_LIMIT",
                "Round-trip history reached its entry bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        manifest_id = value["manifest_id"]
        current = self.current(manifest_id)
        if current is None:
            if value["revision"] != 1 or value["parent_record_sha256"] is not None:
                raise ProductError(
                    "ERR_AUDIO_ROUND_TRIP_REVISION_CONFLICT",
                    "First round-trip manifest must start at revision 1",
                    ProductErrorCategory.STATE,
                )
        else:
            head = current.to_dict()
            if value["revision"] != head["revision"] + 1:
                raise ProductError(
                    "ERR_AUDIO_ROUND_TRIP_REVISION_CONFLICT",
                    "Round-trip manifest revision does not follow the owner head",
                    ProductErrorCategory.STATE,
                )
            if value["parent_record_sha256"] != current.record_sha256:
                raise ProductError(
                    "ERR_AUDIO_ROUND_TRIP_PARENT_CONFLICT",
                    "Round-trip manifest parent does not match the owner head",
                    ProductErrorCategory.STATE,
                )
        self.entries.append(manifest)
        self.store_revision += 1
        return True


class AudioRoundTripHistoryStore:
    @staticmethod
    def snapshot(history: AudioRoundTripHistory) -> dict[str, Any]:
        body = {
            "snapshot_version": FORMAT_VERSION,
            "task_owner": "TASK-035",
            "project_id": history.project_id,
            "store_revision": history.store_revision,
            "entries": [entry.to_dict() for entry in history.entries],
            "audio_body_embedded": False,
            "external_execution_authority": False,
            "asset_promotion_authority": False,
            "resolve_mutation_authority": False,
            "publication_authority": False,
        }
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def serialize(cls, history: AudioRoundTripHistory) -> bytes:
        value = canonical_json_bytes(cls.snapshot(history))
        if len(value) > MAX_BYTES:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_SIZE",
                "Round-trip history exceeds the allowed byte bound",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        return value

    @classmethod
    def parse(
        cls, document: Mapping[str, Any], *, expected_project_id: str | None = None,
    ) -> AudioRoundTripHistory:
        if set(document) != _ROOT_FIELDS:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_FIELDS",
                "Round-trip history fields are not exact",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
        if document.get("snapshot_sha256") != sha256_bytes(canonical_json_bytes(body)):
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_CHECKSUM",
                "Round-trip history checksum mismatch",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if document.get("snapshot_version") != FORMAT_VERSION or document.get("task_owner") != "TASK-035":
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_VERSION",
                "Round-trip history version or owner is unsupported",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        if any(document.get(field) is not False for field in (
            "audio_body_embedded", "external_execution_authority",
            "asset_promotion_authority", "resolve_mutation_authority",
            "publication_authority",
        )):
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_BOUNDARY",
                "Round-trip history violates effect or privacy boundaries",
                ProductErrorCategory.SECURITY,
            )
        rows = document.get("entries")
        revision = document.get("store_revision")
        if (
            isinstance(revision, bool) or not isinstance(revision, int) or revision < 0
            or not isinstance(rows, list) or len(rows) > MAX_ENTRIES
        ):
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_SHAPE",
                "Round-trip history revision or entries are invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            history = AudioRoundTripHistory(document["project_id"])
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("round-trip history row must be an object")
                if not history.append(AudioRoundTripManifest.from_dict(row)):
                    raise ValueError("duplicate round-trip manifest")
            if history.store_revision != revision:
                raise ValueError("store_revision does not equal accepted entry count")
            if expected_project_id is not None and history.project_id != expected_project_id:
                raise ProductError(
                    "ERR_AUDIO_ROUND_TRIP_PROJECT_MISMATCH",
                    "Round-trip history belongs to another Project",
                    ProductErrorCategory.SECURITY,
                )
            return history
        except ProductError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_INVALID",
                "Round-trip history contains invalid records",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    @classmethod
    def parse_bytes(
        cls, value: bytes, *, expected_project_id: str | None = None,
    ) -> AudioRoundTripHistory:
        if not isinstance(value, bytes) or not 0 < len(value) <= MAX_BYTES:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_SIZE",
                "Round-trip history size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
            )
        try:
            document = json.loads(value.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_READ",
                "Round-trip history is not UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_INVALID",
                "Round-trip history root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return cls.parse(document, expected_project_id=expected_project_id)

    @staticmethod
    def project_path(project_root: str | Path) -> Path:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_PROJECT_ROOT",
                "Project root must be an existing regular non-symlink directory",
                ProductErrorCategory.SECURITY,
            )
        state = root / "state"
        if state.is_symlink() or (state.exists() and not state.is_dir()):
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_STATE_DIRECTORY",
                "Project state coordinate must be a regular non-symlink directory",
                ProductErrorCategory.SECURITY,
            )
        return root / RELATIVE_PATH

    @classmethod
    def load_project(
        cls, project_root: str | Path, *, expected_project_id: str,
    ) -> AudioRoundTripHistory:
        target = cls.project_path(project_root)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_FILE",
                "Round-trip history must be a regular non-symlink file",
                ProductErrorCategory.SECURITY,
            )
        try:
            value = target.read_bytes()
        except OSError as exc:
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_READ",
                "Round-trip history could not be read",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return cls.parse_bytes(value, expected_project_id=expected_project_id)

    @classmethod
    def save_project(
        cls,
        project_root: str | Path,
        history: AudioRoundTripHistory,
        *,
        expected_previous_snapshot_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = cls.project_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink() or not target.parent.is_dir() or target.is_symlink():
            raise ProductError(
                "ERR_AUDIO_ROUND_TRIP_HISTORY_FILE",
                "Refusing a symlink or non-directory round-trip history coordinate",
                ProductErrorCategory.SECURITY,
            )
        with exclusive_file_update_lock(target):
            if target.exists():
                if not target.is_file():
                    raise ProductError(
                        "ERR_AUDIO_ROUND_TRIP_HISTORY_FILE",
                        "Round-trip history target must be a regular file",
                        ProductErrorCategory.SECURITY,
                    )
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError(
                        "ERR_AUDIO_ROUND_TRIP_CAS_REQUIRED",
                        "Replacing round-trip history requires its exact previous checksum",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                current = cls.snapshot(cls.load_project(
                    project_root, expected_project_id=history.project_id,
                ))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError(
                        "ERR_AUDIO_ROUND_TRIP_REVISION_CONFLICT",
                        "Round-trip history changed before save; reload before retry",
                        ProductErrorCategory.STATE,
                        details={"current_snapshot_sha256": current},
                    )
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError(
                    "ERR_AUDIO_ROUND_TRIP_PREVIOUS_MISSING",
                    "Expected previous round-trip history does not exist",
                    ProductErrorCategory.STATE,
                )
            document = cls.snapshot(history)
            return AtomicJsonWriter.write(
                target,
                document,
                validator=lambda value: cls.parse(
                    value, expected_project_id=history.project_id,
                ),
            )

    @classmethod
    def read_current(
        cls,
        project_root: str | Path,
        *,
        project_id: str,
        manifest_id: str,
        expected_session_plan_sha256: str,
        expected_manifest_sha256: str | None = None,
    ) -> AudioRoundTripCurrentRead:
        _require_id(project_id, "project_id")
        _require_id(manifest_id, "manifest_id")
        _require_sha(expected_session_plan_sha256, "expected_session_plan_sha256")
        if expected_manifest_sha256 is not None:
            _require_sha(expected_manifest_sha256, "expected_manifest_sha256")
        target = cls.project_path(project_root)
        if not target.exists() and not target.is_symlink():
            return AudioRoundTripCurrentRead(
                AudioRoundTripCurrentState.STORE_NOT_FOUND,
                project_id, manifest_id, None, None, None,
                ("OWNER_STORE_NOT_FOUND",), False, False, False, _OWNER_READ_SEAL,
            )
        history = cls.load_project(project_root, expected_project_id=project_id)
        snapshot_sha = str(cls.snapshot(history)["snapshot_sha256"])
        manifest = history.current(manifest_id)
        if manifest is None:
            return AudioRoundTripCurrentRead(
                AudioRoundTripCurrentState.NOT_FOUND,
                project_id, manifest_id, history.store_revision, snapshot_sha, None,
                ("MANIFEST_NOT_FOUND",), True, True, False, _OWNER_READ_SEAL,
            )
        value = manifest.to_dict()
        reasons: list[str] = []
        if value["session_plan_sha256"] != expected_session_plan_sha256:
            reasons.append("SESSION_PLAN_CHANGED")
        if expected_manifest_sha256 is not None and manifest.record_sha256 != expected_manifest_sha256:
            reasons.append("MANIFEST_HEAD_CHANGED")
        state = AudioRoundTripCurrentState.CURRENT if not reasons else AudioRoundTripCurrentState.STALE
        return AudioRoundTripCurrentRead(
            state,
            project_id,
            manifest_id,
            history.store_revision,
            snapshot_sha,
            manifest,
            tuple(sorted(reasons)),
            True,
            True,
            not reasons,
            _OWNER_READ_SEAL,
        )


__all__ = [
    "AudioRoundTripCurrentRead", "AudioRoundTripCurrentState",
    "AudioRoundTripHistory", "AudioRoundTripHistoryStore",
    "FORMAT_ID", "FORMAT_VERSION", "MAX_BYTES", "MAX_ENTRIES", "RELATIVE_PATH",
]
