"""TASK-060 PP-C pinned read-only source for one promoted Preference envelope.

The port reads an already-encrypted PP-B history through one pinned file handle
and returns only the exact current advisory envelope.  It never promotes,
rolls back, publishes, applies, or mutates a Timeline or Resolve state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable

from .errors import ProductError
from .montage_preference_promotion_store import (
    PreferencePromotionCipher,
    PreferencePromotionHistory,
    PreferencePromotionStore,
)
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_SOURCE_BYTES = 24 * 1024 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,191}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
SourceReadHook = Callable[[str, Path], None]
_SOURCE_READ_TOKEN = object()


class PreferencePromotionSourceError(ValueError):
    """Raised when an exact promoted source cannot be pinned and verified."""


def _is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & marker)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_size),
        int(info.st_mtime_ns),
    )


def _verify_ancestors(path: Path) -> None:
    current = path.parent
    while True:
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise PreferencePromotionSourceError("source ancestor cannot be inspected") from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise PreferencePromotionSourceError("source ancestor must be a non-reparse directory")
        if current.parent == current:
            return
        current = current.parent


def _open_pinned(path: Path, hook: SourceReadHook | None) -> tuple[bytes, str]:
    if not path.is_absolute():
        raise PreferencePromotionSourceError("source path must be absolute")
    if any(part in {".", ".."} for part in path.parts):
        raise PreferencePromotionSourceError("source path must be lexically normalized")
    _verify_ancestors(path)
    try:
        before_path = os.lstat(path)
    except OSError as exc:
        raise PreferencePromotionSourceError("source file is missing or unreadable") from exc
    if (
        stat.S_ISLNK(before_path.st_mode)
        or _is_reparse(before_path)
        or not stat.S_ISREG(before_path.st_mode)
        or before_path.st_nlink != 1
    ):
        raise PreferencePromotionSourceError(
            "source must be one regular non-reparse, non-hardlinked file"
        )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PreferencePromotionSourceError("source file could not be opened safely") from exc
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before_path) or opened.st_nlink != 1:
            raise PreferencePromotionSourceError("source identity changed while opening")
        if hook:
            hook("after_open", path)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, _MAX_SOURCE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_SOURCE_BYTES:
                raise PreferencePromotionSourceError("source exceeds the maximum byte ceiling")
        after_read = os.fstat(descriptor)
        if _identity(after_read) != _identity(opened) or after_read.st_nlink != 1:
            raise PreferencePromotionSourceError("source changed during pinned read")
        if hook:
            hook("after_read", path)
        _verify_ancestors(path)
        after_path = os.lstat(path)
        if _identity(after_path) != _identity(opened) or after_path.st_nlink != 1:
            raise PreferencePromotionSourceError("source path was substituted during read")
        data = b"".join(chunks)
        if not data:
            raise PreferencePromotionSourceError("source file is empty")
        identity_sha256 = sha256_bytes(
            canonical_json_bytes(
                {
                    "domain": "TASK060_PINNED_PREFERENCE_SOURCE_FILE_V1",
                    "device": opened.st_dev,
                    "inode": opened.st_ino,
                    "mode": opened.st_mode,
                    "size": opened.st_size,
                    "mtime_ns": opened.st_mtime_ns,
                    "content_sha256": sha256_bytes(data),
                }
            )
        )
        return data, identity_sha256
    except OSError as exc:
        raise PreferencePromotionSourceError("source file read failed closed") from exc
    finally:
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class PromotedPreferenceSourceCoordinates:
    source_id: str
    store_id: str
    owner_scope_sha256: str
    promotion_revision: int
    promotion_revision_sha256: str
    history_sha256: str
    active_payload_sha256: str

    def __post_init__(self) -> None:
        if type(self.source_id) is not str or _ID.fullmatch(self.source_id) is None:
            raise ValueError("source_id is required")
        if type(self.store_id) is not str or not self.store_id:
            raise ValueError("store_id is required")
        for field in (
            "owner_scope_sha256", "promotion_revision_sha256", "history_sha256",
            "active_payload_sha256",
        ):
            value = getattr(self, field)
            if type(value) is not str or _SHA256.fullmatch(value) is None:
                raise ValueError(f"{field} must be a sha256 coordinate")
        if type(self.promotion_revision) is not int or self.promotion_revision < 1:
            raise ValueError("promotion_revision must be an integer >= 1")


@dataclass(frozen=True, slots=True)
class PromotedPreferenceSourceRead:
    source_id: str
    source_file_identity_sha256: str
    store_id: str
    owner_scope_sha256: str
    promotion_revision: int
    promotion_revision_sha256: str
    history_sha256: str
    profile_id: str
    profile_version: int
    active_payload_sha256: str
    envelope: dict[str, Any]
    envelope_sha256: str
    readback_sha256: str
    _token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _SOURCE_READ_TOKEN:
            raise TypeError("PromotedPreferenceSourceRead must be minted by the pinned source port")
        PromotedPreferenceSourceCoordinates(
            self.source_id, self.store_id, self.owner_scope_sha256,
            self.promotion_revision, self.promotion_revision_sha256,
            self.history_sha256, self.active_payload_sha256,
        )
        if type(self.source_file_identity_sha256) is not str or _SHA256.fullmatch(self.source_file_identity_sha256) is None:
            raise ValueError("source_file_identity_sha256 is invalid")
        if type(self.profile_id) is not str or not self.profile_id.startswith("profile-"):
            raise ValueError("profile_id is invalid")
        if type(self.profile_version) is not int or self.profile_version < 1:
            raise ValueError("profile_version is invalid")
        if type(self.envelope) is not dict:
            raise ValueError("envelope must be a detached built-in dict")
        if (
            type(self.envelope_sha256) is not str
            or self.envelope_sha256 != sha256_bytes(canonical_json_bytes(self.envelope))
        ):
            raise ValueError("envelope_sha256 does not bind the exact envelope")
        if (
            self.envelope.get("profile_id") != self.profile_id
            or self.envelope.get("profile_version") != self.profile_version
            or self.envelope.get("profile_sha256") != self.active_payload_sha256
            or self.envelope.get("owner_scope_hash") != self.owner_scope_sha256
        ):
            raise ValueError("read-back envelope coordinates mismatch")
        if (
            self.envelope.get("advisory_only") is not True
            or self.envelope.get("canonical_timeline") is not False
            or self.envelope.get("auto_apply_authorized") is not False
        ):
            raise ValueError("read-back envelope exceeds advisory-only authority")
        expected = self._body()
        if self.readback_sha256 != sha256_bytes(canonical_json_bytes(expected)):
            raise ValueError("read-back hash mismatch")

    @property
    def production_source_bound(self) -> bool:
        return True

    def verify_current(self) -> None:
        """Fail if caller-owned mutable data changed after the pinned read."""

        self.__post_init__()

    def _body(self) -> dict[str, Any]:
        return {
            "record_version": "1.0.0",
            "record_type": "MONTAGE_PREFERENCE_PROMOTED_SOURCE_READBACK",
            "task_owner": "TASK-060",
            "source_id": self.source_id,
            "source_file_identity_sha256": self.source_file_identity_sha256,
            "store_id": self.store_id,
            "owner_scope_sha256": self.owner_scope_sha256,
            "promotion_revision": self.promotion_revision,
            "promotion_revision_sha256": self.promotion_revision_sha256,
            "history_sha256": self.history_sha256,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "active_payload_sha256": self.active_payload_sha256,
            "envelope": json.loads(canonical_json_bytes(self.envelope)),
            "envelope_sha256": self.envelope_sha256,
            "exact_current_source_verified": True,
            "production_profile_source_bound": True,
            "advisory_profile_only": True,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "readback_sha256": self.readback_sha256}


class PromotedPreferenceSource:
    """Read exactly one current PP-B envelope from a pinned encrypted source."""

    def __init__(
        self,
        path: str | Path,
        cipher: PreferencePromotionCipher,
        coordinates: PromotedPreferenceSourceCoordinates,
    ) -> None:
        self.path = Path(path)
        self.cipher = cipher
        if type(coordinates) is not PromotedPreferenceSourceCoordinates:
            raise ValueError("coordinates must be exact PromotedPreferenceSourceCoordinates")
        self.coordinates = coordinates

    def read_current(self, *, hook: SourceReadHook | None = None) -> PromotedPreferenceSourceRead:
        data, file_identity = _open_pinned(self.path, hook)
        try:
            document = json.loads(data.decode("utf-8"))
            if type(document) is not dict:
                raise ValueError("encrypted source must be an object")
            store = PreferencePromotionStore(self.path, self.cipher)
            history = store.parse_encrypted_document(document)
        except (ProductError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise PreferencePromotionSourceError(
                "encrypted promotion source failed exact admission"
            ) from exc
        self._verify_history(history)
        envelope = history.active_envelope
        if envelope is None:
            raise PreferencePromotionSourceError("promotion source has no active envelope")
        revision = history.revisions[-1]
        body = {
            "record_version": "1.0.0",
            "record_type": "MONTAGE_PREFERENCE_PROMOTED_SOURCE_READBACK",
            "task_owner": "TASK-060",
            "source_id": self.coordinates.source_id,
            "source_file_identity_sha256": file_identity,
            "store_id": history.store_id,
            "owner_scope_sha256": history.owner_scope_sha256,
            "promotion_revision": history.revision,
            "promotion_revision_sha256": revision.to_dict()["promotion_revision_sha256"],
            "history_sha256": history.to_dict()["history_sha256"],
            "profile_id": envelope["profile_id"],
            "profile_version": envelope["profile_version"],
            "active_payload_sha256": envelope["profile_sha256"],
            "envelope": envelope,
            "envelope_sha256": sha256_bytes(canonical_json_bytes(envelope)),
            "exact_current_source_verified": True,
            "production_profile_source_bound": True,
            "advisory_profile_only": True,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "external_effect_authorized": False,
        }
        return PromotedPreferenceSourceRead(
            self.coordinates.source_id, file_identity, history.store_id,
            history.owner_scope_sha256, history.revision,
            revision.to_dict()["promotion_revision_sha256"],
            history.to_dict()["history_sha256"], envelope["profile_id"],
            envelope["profile_version"], envelope["profile_sha256"], envelope,
            sha256_bytes(canonical_json_bytes(envelope)),
            sha256_bytes(canonical_json_bytes(body)),
            _SOURCE_READ_TOKEN,
        )

    def _verify_history(self, history: PreferencePromotionHistory) -> None:
        current = history.revisions[-1] if history.revisions else None
        actual_revision_sha256 = (
            None if current is None else current.to_dict()["promotion_revision_sha256"]
        )
        actual_history_sha256 = history.to_dict()["history_sha256"]
        envelope = history.active_envelope
        actual_payload_sha256 = None if envelope is None else envelope["profile_sha256"]
        expected = self.coordinates
        if (
            history.store_id != expected.store_id
            or history.owner_scope_sha256 != expected.owner_scope_sha256
            or history.revision != expected.promotion_revision
            or actual_revision_sha256 != expected.promotion_revision_sha256
            or actual_history_sha256 != expected.history_sha256
            or actual_payload_sha256 != expected.active_payload_sha256
        ):
            raise PreferencePromotionSourceError(
                "promotion source is missing, stale, substituted, or out of scope"
            )


def coordinates_from_verified_history(
    *, source_id: str, history: PreferencePromotionHistory,
) -> PromotedPreferenceSourceCoordinates:
    """Capture expected coordinates from an already verified PP-B read."""

    if type(history) is not PreferencePromotionHistory or not history.revisions:
        raise ValueError("a non-empty exact PreferencePromotionHistory is required")
    envelope = history.active_envelope
    if envelope is None:
        raise ValueError("history has no active envelope")
    return PromotedPreferenceSourceCoordinates(
        source_id, history.store_id, history.owner_scope_sha256, history.revision,
        history.current_revision_sha256, history.to_dict()["history_sha256"],
        envelope["profile_sha256"],
    )


__all__ = [
    "PreferencePromotionSourceError", "PromotedPreferenceSource",
    "PromotedPreferenceSourceCoordinates", "PromotedPreferenceSourceRead",
    "coordinates_from_verified_history",
]
