"""Guarded TASK-098 coordination for the existing private TASK-036 ASR settings."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import stat
import threading
import time
from typing import Any, Callable

from .atomic import AtomicJsonWriter, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .serialization import sha256_bytes, validate_sha256
from .task036_native_dialog import Task036NativeDialogService
from .task098_faster_whisper_model_directory_inspector import (
    inspect_faster_whisper_model_directory,
)


SETTINGS_UPDATE_VERSION = "1.0.0"
_PENDING_LIMIT = 16
_PENDING_TTL_SECONDS = 300.0
_REPARSE_POINT = 0x00000400


def _error(code: str, message: str, category: ProductErrorCategory) -> ProductError:
    return ProductError(code, message, category)


def _task036_contract() -> tuple[int, Callable[[Any], Any]]:
    # Lazy import avoids the existing trusted-launcher -> Shell import cycle.
    from .task036_trusted_launcher import (
        TASK036_LAUNCH_CONFIG_MAX_BYTES,
        Task036LaunchConfiguration,
    )

    return TASK036_LAUNCH_CONFIG_MAX_BYTES, Task036LaunchConfiguration.from_dict


def _identity(value: os.stat_result) -> tuple[int, ...]:
    identity = (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )
    # Windows path-stat and descriptor-stat do not expose a comparable ctime
    # projection for the same unchanged file.  Prefer the stable birth time
    # when available and keep the stronger ctime signal on POSIX.
    if os.name == "nt":
        birthtime = getattr(value, "st_birthtime_ns", None)
        return identity if birthtime is None else (*identity, birthtime)
    return (*identity, value.st_ctime_ns)


def _is_alias(value: os.stat_result) -> bool:
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _require_safe_ancestry(path: Path) -> None:
    for candidate in [*reversed(path.parents), path]:
        try:
            metadata = candidate.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_PATH_UNSAFE",
                "Model settings path ancestry is unavailable",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if _is_alias(metadata):
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_PATH_UNSAFE",
                "Model settings path ancestry is unsafe",
                ProductErrorCategory.DATA_INTEGRITY,
            )


def _read_config(path: Path) -> tuple[bytes, dict[str, Any]]:
    maximum, validator = _task036_contract()
    _require_safe_ancestry(path)
    try:
        before = path.stat(follow_symlinks=False)
        if (
            _is_alias(before)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 1 <= before.st_size <= maximum
        ):
            raise OSError("unsafe config identity")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            body = bytearray()
            while len(body) <= maximum:
                chunk = os.read(descriptor, min(64 * 1024, maximum + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            after_open = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = path.stat(follow_symlinks=False)
        if (
            _is_alias(opened)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not 1 <= len(body) <= maximum
            or len(body) != opened.st_size
            or not (_identity(before) == _identity(opened) == _identity(after_open) == _identity(after))
        ):
            raise OSError("config changed during read")
        document = json.loads(bytes(body).decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError("config must be an object")
        validator(document)
        project_root = Path(document["project"]["project_root"]).resolve(strict=True)
        path.resolve(strict=True).relative_to(project_root)
        return bytes(body), document
    except ProductError:
        raise
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        RecursionError,
        TypeError,
        ValueError,
    ) as exc:
        raise _error(
            "ERR_TASK098_MODEL_SETTINGS_CONFIG_INVALID",
            "TASK-036 launch configuration is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc


def _validate_config_document(document: Any) -> None:
    _maximum, validator = _task036_contract()
    validator(document)


def _cache_directory_is_safe(document: dict[str, Any]) -> bool:
    try:
        project_root = Path(document["project"]["project_root"])
        cache = Path(document["paths"]["asr_cache_directory"])
        _require_safe_ancestry(cache)
        metadata = cache.stat(follow_symlinks=False)
        if _is_alias(metadata) or not stat.S_ISDIR(metadata.st_mode):
            return False
        cache.resolve(strict=True).relative_to(project_root.resolve(strict=True))
        return True
    except (KeyError, OSError, ProductError, TypeError, ValueError):
        return False


def _base_projection(status: str) -> dict[str, Any]:
    return {
        "settings_update_version": SETTINGS_UPDATE_VERSION,
        "status": status,
        "model_download_authorized": False,
        "model_load_started": False,
        "inference_started": False,
        "network_used": False,
        "provider_execution_started": False,
        "private_path_exposed": False,
    }


@dataclass(frozen=True, slots=True, repr=False)
class _PendingModelSettingsUpdate:
    confirmation_id: str
    expires_at: float
    expected_config_sha256: str
    expected_cache_locator_sha256: str
    model_path: str
    model_id: str
    inspection_record_sha256: str


class Task098FasterWhisperModelSettingsService:
    """Prepare and atomically apply one path-free local model setting update."""

    def __init__(
        self,
        *,
        launch_config_path: str | Path,
        native_dialog: Task036NativeDialogService,
        token_factory: Callable[[], str] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        pending_ttl_seconds: float = _PENDING_TTL_SECONDS,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        raw_path = os.fspath(launch_config_path)
        if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
            raise ValueError("launch_config_path is invalid")
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError("launch_config_path must be absolute")
        if not isinstance(native_dialog, Task036NativeDialogService):
            raise TypeError("native_dialog must be a TASK-036 dialog service")
        if not callable(token_factory or secrets.token_urlsafe) or not callable(monotonic_clock):
            raise TypeError("token factory and monotonic clock must be callable")
        if not isinstance(pending_ttl_seconds, (int, float)) or not 1 <= pending_ttl_seconds <= 900:
            raise ValueError("pending_ttl_seconds must be in 1..900")
        self._path = Path(os.path.abspath(path))
        self._native_dialog = native_dialog
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._clock = monotonic_clock
        self._pending_ttl = float(pending_ttl_seconds)
        self._failure_injector = failure_injector
        self._pending: dict[str, _PendingModelSettingsUpdate] = {}
        self._pending_lock = threading.Lock()

    def _prune(self, now: float) -> None:
        for key in tuple(self._pending):
            if self._pending[key].expires_at < now:
                del self._pending[key]

    def snapshot(self, *, expected_launch_config_sha256: str) -> dict[str, Any]:
        try:
            expected = validate_sha256(
                expected_launch_config_sha256,
                field_name="expected_launch_config_sha256",
            )
        except ValueError as exc:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_EXPECTED_SHA_INVALID",
                "Expected launch configuration identity is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        raw, document = _read_config(self._path)
        current_sha = sha256_bytes(raw)
        if current_sha != expected:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_STALE",
                "TASK-036 launch configuration differs from the reviewed identity",
                ProductErrorCategory.AUTHORIZATION,
            )
        base = {
            **_base_projection("BLOCKED"),
            "launch_config_sha256": current_sha,
            "model_id": None,
            "reason_codes": [],
            "settings_updated": False,
            "cache_directory_configured": True,
            "cache_reuse_available": False,
            "cache_hit_observed": False,
            "restart_readback": True,
            "model_manifest_continuity_confirmed": False,
            "runtime_compatibility_confirmed": False,
        }
        if not _cache_directory_is_safe(document):
            return {**base, "reason_codes": ["CACHE_DIRECTORY_UNSAFE"]}
        model = document["asr"]["model"]
        if not Path(model).is_absolute():
            return {
                **base,
                "status": "LOCAL_MODEL_NOT_CONFIGURED",
                "reason_codes": ["LOCAL_MODEL_NOT_CONFIGURED"],
                "cache_reuse_available": True,
            }
        inspection = inspect_faster_whisper_model_directory(model)
        if inspection.outcome != "READY":
            return {
                **base,
                "reason_codes": list(inspection.reason_codes),
                "inspection": inspection.to_public_dict(),
                "cache_reuse_available": True,
            }
        return {
            **base,
            "status": "READY",
            "model_id": inspection.model_id,
            "reason_codes": list(inspection.reason_codes),
            "inspection": inspection.to_public_dict(),
            "cache_reuse_available": True,
        }

    def prepare(self, *, expected_launch_config_sha256: str) -> dict[str, Any]:
        try:
            expected = validate_sha256(
                expected_launch_config_sha256,
                field_name="expected_launch_config_sha256",
            )
        except ValueError as exc:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_EXPECTED_SHA_INVALID",
                "Expected launch configuration identity is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        raw, document = _read_config(self._path)
        if sha256_bytes(raw) != expected:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_STALE",
                "TASK-036 launch configuration differs from the reviewed identity",
                ProductErrorCategory.AUTHORIZATION,
            )

        selection = self._native_dialog.choose_faster_whisper_model_folder()
        if not selection.selected:
            return {
                **_base_projection("CANCELLED"),
                "confirmation_id": None,
                "model_id": None,
                "reason_codes": [],
                "settings_updated": False,
                "cache_directory_preserved": True,
            }
        assert selection.host_path is not None
        inspection = inspect_faster_whisper_model_directory(selection.host_path)
        if inspection.outcome != "READY":
            return {
                **_base_projection("BLOCKED"),
                "confirmation_id": None,
                "model_id": None,
                "reason_codes": list(inspection.reason_codes),
                "inspection": inspection.to_public_dict(),
                "settings_updated": False,
                "cache_directory_preserved": True,
            }

        model_path = str(Path(selection.host_path).resolve(strict=True))
        if sha256_bytes(model_path.encode("utf-8")) != inspection.private_locator_sha256:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_MODEL_DRIFT",
                "Selected model directory identity changed",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        cache_value = document["paths"]["asr_cache_directory"]
        cache_sha = sha256_bytes(cache_value.encode("utf-8"))
        now = self._clock()
        token = self._token_factory()
        if not isinstance(token, str) or not token or len(token) > 256 or "\x00" in token:
            raise ValueError("token factory returned an invalid confirmation ID")
        with self._pending_lock:
            self._prune(now)
            if len(self._pending) >= _PENDING_LIMIT or token in self._pending:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_PENDING_LIMIT",
                    "Model settings confirmation capacity is unavailable",
                    ProductErrorCategory.STATE,
                )
            self._pending[token] = _PendingModelSettingsUpdate(
                confirmation_id=token,
                expires_at=now + self._pending_ttl,
                expected_config_sha256=expected,
                expected_cache_locator_sha256=cache_sha,
                model_path=model_path,
                model_id=inspection.model_id or "",
                inspection_record_sha256=inspection.record_sha256,
            )
        return {
            **_base_projection("READY_FOR_CONFIRMATION"),
            "confirmation_id": token,
            "model_id": inspection.model_id,
            "reason_codes": list(inspection.reason_codes),
            "inspection": inspection.to_public_dict(),
            "expected_launch_config_sha256": expected,
            "settings_updated": False,
            "cache_directory_preserved": True,
            "human_confirmation_required": True,
        }

    def apply(self, *, confirmation_id: str) -> dict[str, Any]:
        if not isinstance(confirmation_id, str) or not confirmation_id or len(confirmation_id) > 256:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_CONFIRMATION_INVALID",
                "Model settings confirmation is invalid",
                ProductErrorCategory.VALIDATION,
            )
        now = self._clock()
        with self._pending_lock:
            self._prune(now)
            pending = self._pending.pop(confirmation_id, None)
        if pending is None or pending.expires_at < now:
            raise _error(
                "ERR_TASK098_MODEL_SETTINGS_CONFIRMATION_INVALID",
                "Model settings confirmation is unavailable or expired",
                ProductErrorCategory.AUTHORIZATION,
            )

        with exclusive_file_update_lock(self._path):
            raw, document = _read_config(self._path)
            current_sha = sha256_bytes(raw)
            if current_sha != pending.expected_config_sha256:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_STALE",
                    "TASK-036 launch configuration changed before apply",
                    ProductErrorCategory.AUTHORIZATION,
                )
            cache_value = document["paths"]["asr_cache_directory"]
            if sha256_bytes(cache_value.encode("utf-8")) != pending.expected_cache_locator_sha256:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_CACHE_DRIFT",
                    "TASK-036 ASR cache identity changed before apply",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            inspection = inspect_faster_whisper_model_directory(pending.model_path)
            if (
                inspection.outcome != "READY"
                or inspection.record_sha256 != pending.inspection_record_sha256
                or inspection.model_id != pending.model_id
            ):
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_MODEL_DRIFT",
                    "Selected model directory changed before apply",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

            updated = deepcopy(document)
            updated["asr"]["model"] = pending.model_path
            semantic_check = deepcopy(updated)
            semantic_check["asr"]["model"] = document["asr"]["model"]
            if semantic_check != document:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_SCOPE_INVALID",
                    "Model settings update exceeded its one-field scope",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if updated["asr"]["allow_model_download"] is not False:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_DOWNLOAD_AUTHORITY",
                    "Model settings cannot authorize downloads",
                    ProductErrorCategory.AUTHORIZATION,
                )
            if updated["paths"]["asr_cache_directory"] != cache_value:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_CACHE_DRIFT",
                    "Model settings cannot replace the existing cache",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            _validate_config_document(updated)

            def guarded_failure(stage: str, temporary: Path) -> None:
                if stage == "before_replace":
                    latest, _latest_document = _read_config(self._path)
                    if sha256_bytes(latest) != pending.expected_config_sha256:
                        raise _error(
                            "ERR_TASK098_MODEL_SETTINGS_STALE",
                            "TASK-036 launch configuration changed during apply",
                            ProductErrorCategory.AUTHORIZATION,
                        )
                if self._failure_injector is not None:
                    self._failure_injector(stage, temporary)

            AtomicJsonWriter.write(
                self._path,
                updated,
                validator=_validate_config_document,
                failure_injector=guarded_failure,
            )
            written, readback = _read_config(self._path)
            if readback["asr"]["model"] != pending.model_path:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_READBACK_INVALID",
                    "Model settings read-back is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if readback["paths"]["asr_cache_directory"] != cache_value:
                raise _error(
                    "ERR_TASK098_MODEL_SETTINGS_READBACK_INVALID",
                    "ASR cache changed during model settings update",
                    ProductErrorCategory.DATA_INTEGRITY,
                )

        return {
            **_base_projection("UPDATED"),
            "model_id": pending.model_id,
            "reason_codes": ["MODEL_DIRECTORY_VALID"],
            "previous_launch_config_sha256": pending.expected_config_sha256,
            "launch_config_sha256": sha256_bytes(written),
            "settings_updated": True,
            "cache_directory_preserved": True,
            "restart_required": True,
        }
