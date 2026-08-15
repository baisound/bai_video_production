"""Append-only, project-local TASK-046 VoiceProfileRevision metadata store."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_profile_revision import VoiceProfileRevision


_CONTROL_DIR = ".bai-project"
_STORE_NAME = "voice-profile-revisions.json"
_MAX_STORE_BYTES = 4 * 1024 * 1024
_BOUNDARY_FLAGS = {
    "audio_body_persisted",
    "dataset_body_persisted",
    "speaker_embedding_persisted",
    "transcript_body_persisted",
    "credential_value_persisted",
    "private_provider_voice_id_persisted",
    "host_path_persisted",
    "execution_authorized",
}


def _project_root(value: str | Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.is_dir():
        raise ProductError(
            "ERR_VOICE_PROFILE_ROOT_INVALID",
            "Voice Profile project root must be an existing regular directory",
            ProductErrorCategory.SECURITY,
        )
    return root.resolve(strict=True)


def _store_path(value: str | Path, *, create_control_dir: bool = False) -> Path:
    root = _project_root(value)
    control = root / _CONTROL_DIR
    if create_control_dir and not control.exists():
        control.mkdir(mode=0o700)
    if control.is_symlink() or (control.exists() and not control.is_dir()):
        raise ProductError(
            "ERR_VOICE_PROFILE_CONTROL_DIR_INVALID",
            "Voice Profile control directory must be a regular non-symlink directory",
            ProductErrorCategory.SECURITY,
        )
    return control / _STORE_NAME


@dataclass(frozen=True, slots=True)
class VoiceProfileRevisionHistory:
    voice_profile_id: str
    revisions: tuple[VoiceProfileRevision, ...]

    def __post_init__(self) -> None:
        if not self.revisions:
            raise ValueError("Voice Profile history must not be empty")
        for index, revision in enumerate(self.revisions, 1):
            if revision.voice_profile_id != self.voice_profile_id:
                raise ValueError("Voice Profile identity changed within history")
            if revision.revision != index:
                raise ValueError("Voice Profile revisions must be contiguous from 1")
            expected_parent = None if index == 1 else self.revisions[index - 2].voice_profile_revision_sha256
            if revision.parent_revision_sha256 != expected_parent:
                raise ValueError("Voice Profile parent revision chain is invalid")

    @property
    def latest(self) -> VoiceProfileRevision:
        return self.revisions[-1]

    def _body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "store_version": "1.0.0",
            "task_owner": "TASK-046",
            "voice_profile_id": self.voice_profile_id,
            "latest_revision": self.latest.revision,
            "latest_revision_sha256": self.latest.voice_profile_revision_sha256,
            "revisions": [revision.to_private_dict() for revision in self.revisions],
        }
        body.update({name: False for name in sorted(_BOUNDARY_FLAGS)})
        return body

    @property
    def store_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self._body()))

    def to_private_dict(self) -> dict[str, Any]:
        body = self._body()
        body["store_sha256"] = self.store_sha256
        return body

    def to_public_dict(self) -> dict[str, Any]:
        body = {
            "store_version": "1.0.0",
            "task_owner": "TASK-046",
            "voice_profile_id": self.voice_profile_id,
            "latest_revision": self.latest.revision,
            "latest_revision_sha256": self.latest.voice_profile_revision_sha256,
            "store_sha256": self.store_sha256,
            "revisions": [revision.to_public_dict() for revision in self.revisions],
        }
        body.update({name: False for name in sorted(_BOUNDARY_FLAGS)})
        return body


def _parse_store(value: Any) -> VoiceProfileRevisionHistory:
    if not isinstance(value, dict):
        raise ValueError("Voice Profile store root must be an object")
    expected = {
        "store_version", "task_owner", "voice_profile_id", "latest_revision",
        "latest_revision_sha256", "revisions", "store_sha256", *_BOUNDARY_FLAGS,
    }
    if set(value) != expected:
        raise ValueError("Voice Profile store fields are incomplete or unknown")
    if value["store_version"] != "1.0.0" or value["task_owner"] != "TASK-046":
        raise ValueError("unsupported Voice Profile store identity")
    if any(value[name] is not False for name in _BOUNDARY_FLAGS):
        raise ValueError("Voice Profile store violates body-free/non-executing boundaries")
    supplied_sha = value["store_sha256"]
    validate_sha256(supplied_sha, field_name="store_sha256")
    body = {key: item for key, item in value.items() if key != "store_sha256"}
    if supplied_sha != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("Voice Profile store checksum mismatch")
    rows = value["revisions"]
    if not isinstance(rows, list) or not rows or any(not isinstance(item, Mapping) for item in rows):
        raise ValueError("Voice Profile revisions must be a non-empty object list")
    history = VoiceProfileRevisionHistory(
        voice_profile_id=value["voice_profile_id"],
        revisions=tuple(VoiceProfileRevision.from_private_dict(item) for item in rows),
    )
    if value["latest_revision"] != history.latest.revision:
        raise ValueError("Voice Profile latest revision is invalid")
    if value["latest_revision_sha256"] != history.latest.voice_profile_revision_sha256:
        raise ValueError("Voice Profile latest revision digest is invalid")
    if history.store_sha256 != supplied_sha:
        raise ValueError("Voice Profile store did not round-trip")
    return history


def _load_path(target: Path) -> VoiceProfileRevisionHistory:
    if target.is_symlink() or not target.is_file():
        raise ProductError(
            "ERR_VOICE_PROFILE_STORE_FILE_INVALID",
            "Voice Profile store must be a regular non-symlink file",
            ProductErrorCategory.VALIDATION,
        )
    size = target.stat().st_size
    if size <= 0 or size > _MAX_STORE_BYTES:
        raise ProductError(
            "ERR_VOICE_PROFILE_STORE_SIZE",
            "Voice Profile store size is outside the allowed bound",
            ProductErrorCategory.VALIDATION,
            details={"size_bytes": size},
        )
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        return _parse_store(value)
    except ProductError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_VOICE_PROFILE_STORE_INTEGRITY",
            "Voice Profile store failed integrity validation",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc


class VoiceProfileRevisionStore:
    @staticmethod
    def path(project_root: str | Path) -> Path:
        return _store_path(project_root)

    @staticmethod
    def load(project_root: str | Path) -> VoiceProfileRevisionHistory:
        return _load_path(_store_path(project_root))

    @staticmethod
    def create(
        project_root: str | Path,
        revision: VoiceProfileRevision,
        *,
        failure_injector: FailureInjector | None = None,
    ) -> AtomicWriteResult:
        if revision.revision != 1 or revision.parent_revision_sha256 is not None:
            raise ProductError(
                "ERR_VOICE_PROFILE_FIRST_REVISION_INVALID",
                "First Voice Profile revision must be revision 1 with no parent",
                ProductErrorCategory.STATE,
            )
        target = _store_path(project_root, create_control_dir=True)
        try:
            with exclusive_file_update_lock(target):
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise ProductError(
                        "ERR_VOICE_PROFILE_STORE_FILE_INVALID",
                        "Refusing an invalid Voice Profile store target",
                        ProductErrorCategory.SECURITY,
                    )
                if target.exists():
                    raise ProductError(
                        "ERR_VOICE_PROFILE_STORE_ALREADY_EXISTS",
                        "Voice Profile store already exists",
                        ProductErrorCategory.STATE,
                    )
                history = VoiceProfileRevisionHistory(revision.voice_profile_id, (revision,))
                return AtomicJsonWriter.write(
                    target,
                    history.to_private_dict(),
                    validator=_parse_store,
                    failure_injector=failure_injector,
                )
        except ValueError as exc:
            raise ProductError(
                "ERR_VOICE_PROFILE_STORE_LOCK_INVALID",
                "Voice Profile store lock is invalid",
                ProductErrorCategory.SECURITY,
            ) from exc

    @staticmethod
    def append(
        project_root: str | Path,
        revision: VoiceProfileRevision,
        *,
        expected_previous_store_sha256: str | None,
        failure_injector: FailureInjector | None = None,
    ) -> AtomicWriteResult:
        target = _store_path(project_root, create_control_dir=True)
        try:
            with exclusive_file_update_lock(target):
                if expected_previous_store_sha256 is None:
                    raise ProductError(
                        "ERR_VOICE_PROFILE_STORE_CAS_REQUIRED",
                        "Appending a Voice Profile revision requires the exact previous store checksum",
                        ProductErrorCategory.AUTHORIZATION,
                    )
                validate_sha256(expected_previous_store_sha256, field_name="expected_previous_store_sha256")
                if not target.exists():
                    raise ProductError(
                        "ERR_VOICE_PROFILE_STORE_PREVIOUS_MISSING",
                        "Expected previous Voice Profile store does not exist",
                        ProductErrorCategory.STATE,
                    )
                current = _load_path(target)
                if current.store_sha256 != expected_previous_store_sha256:
                    raise ProductError(
                        "ERR_VOICE_PROFILE_STORE_REVISION_CONFLICT",
                        "Voice Profile store changed before append; reload before retry",
                        ProductErrorCategory.STATE,
                        details={"current_store_sha256": current.store_sha256},
                    )
                if revision.voice_profile_id != current.voice_profile_id:
                    raise ProductError(
                        "ERR_VOICE_PROFILE_IDENTITY_CONFLICT",
                        "Voice Profile identity cannot change within a store",
                        ProductErrorCategory.STATE,
                    )
                if revision.revision != current.latest.revision + 1:
                    raise ProductError(
                        "ERR_VOICE_PROFILE_REVISION_INVALID",
                        "Voice Profile revision must advance exactly once",
                        ProductErrorCategory.STATE,
                    )
                if revision.parent_revision_sha256 != current.latest.voice_profile_revision_sha256:
                    raise ProductError(
                        "ERR_VOICE_PROFILE_PARENT_CONFLICT",
                        "Voice Profile parent must be the exact latest revision digest",
                        ProductErrorCategory.STATE,
                    )
                updated = VoiceProfileRevisionHistory(current.voice_profile_id, current.revisions + (revision,))
                return AtomicJsonWriter.write(
                    target,
                    updated.to_private_dict(),
                    validator=_parse_store,
                    failure_injector=failure_injector,
                )
        except ProductError:
            raise
        except ValueError as exc:
            raise ProductError(
                "ERR_VOICE_PROFILE_STORE_UPDATE_INVALID",
                "Voice Profile store update failed validation",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
