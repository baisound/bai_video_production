"""Durable TASK-098 runtime-transcription control coordination.

SQLite operation rows are the sole state authority.  Files written here are
immutable, digest-addressed Evidence for the exact row reference or validated
predecessor chain.  This module has no Provider, model, network, UI, Shell, or
private-media entrypoint.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Iterator, Mapping, TypeVar

from .errors import ProductError, ProductErrorCategory
from .faster_whisper_runtime_contract import (
    FasterWhisperRuntimeDecisionV1,
    FasterWhisperRuntimeRequestV1,
    validate_runtime_pair,
)
from .ids import IdKind, validate_id, validate_project_id
from .local_comfy_image_generation_port import _PinnedDirectory
from .serialization import canonical_json_bytes, validate_sha256
from .store import OperationRecord, SQLiteProductStore
from .task098_runtime_transcription_control import (
    RuntimeTranscriptionAdjudicationDecisionV1,
    RuntimeTranscriptionCancelOutcomeV1,
    RuntimeTranscriptionCancelRequestV1,
    RuntimeTranscriptionCommitBarrierV1,
    RuntimeTranscriptionGenerationAbsenceObservationV1,
    RuntimeTranscriptionTerminalClosureCommitV1,
)


_OPERATION_DOMAIN = b"bvp.task098.task036-runtime-operation.v2\0"
_GUARD_DOMAIN = b"bvp.task098.task036-cross-version-guard.v1\0"
_CONTROL_DOMAIN = b"bvp.task098.runtime-transcription-control-operation.v1\0"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SECOND_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_MAX_RECORD_BYTES = 256 * 1024

CONTROL_COMMAND = "task098.runtime_transcription.control.v1"
MAIN_COMMAND = "task036.local_transcription.v2"
LEASE_COMMAND = "task036.local_transcription.cross_version_guard.v1"
SLOT_COMMAND = "task036.local_transcription_output_slot"
_CONTROL_REF_PREFIXES = {
    "cancel-request": "task098-runtime-cancel-request:v1:",
    "cancel-outcome": "task098-runtime-cancel-outcome:v1:",
    "commit-barrier": "task098-runtime-commit-barrier:v1:",
    "terminal-commit": "task098-runtime-terminal-commit:v1:",
}


def _typed_control_ref(kind: str, digest: str) -> str:
    prefix = _CONTROL_REF_PREFIXES.get(kind)
    if prefix is None:
        raise ValueError("control ref kind is invalid")
    return prefix + _digest(digest, "record_sha256").removeprefix("sha256:")


def _typed_control_digest(kind: str, value: Any) -> str:
    prefix = _CONTROL_REF_PREFIXES.get(kind)
    if prefix is None or not isinstance(value, str):
        raise ValueError("control ref kind or value is invalid")
    match = re.fullmatch(re.escape(prefix) + r"([0-9a-f]{64})", value)
    if match is None:
        raise ValueError("control ref is not the exact typed durable form")
    return "sha256:" + match.group(1)


@contextmanager
def _exclusive_pinned_file_lock(
    directory: _PinnedDirectory, name: str,
) -> Iterator[None]:
    """Lock one pinned-directory child without a check-to-open path race."""

    name = directory._name(name)
    directory.assert_current()
    descriptor: int | None = None
    locked = False
    try:
        if directory.fd is not None:
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory.fd,
            )
        else:
            if os.name != "nt":
                raise ProductError(
                    "ERR_TASK098_CONTROL_LOCK_INVALID",
                    "Pinned runtime control lock has no safe directory descriptor",
                    ProductErrorCategory.SECURITY,
                )
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateFileW.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
            )
            kernel32.CreateFileW.restype = wintypes.HANDLE
            handle = kernel32.CreateFileW(
                str(directory.path / name),
                0x80000000 | 0x40000000,
                0x1 | 0x2,
                None,
                4,
                0x00200000 | 0x80000000,
                None,
            )
            if handle == wintypes.HANDLE(-1).value:
                raise ProductError(
                    "ERR_TASK098_CONTROL_LOCK_INVALID",
                    "Runtime control lock could not be opened safely",
                    ProductErrorCategory.SECURITY,
                )
            try:
                identity = _PinnedDirectory._windows_handle_identity(handle)
                descriptor = msvcrt.open_osfhandle(
                    handle, os.O_RDWR | getattr(os, "O_BINARY", 0),
                )
            except BaseException:
                kernel32.CloseHandle(handle)
                raise
            observed = os.lstat(directory.path / name)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if (
                not stat.S_ISREG(observed.st_mode)
                or getattr(observed, "st_file_attributes", 0) & reparse_flag
                or (observed.st_ino not in {0, identity[1]})
            ):
                raise ProductError(
                    "ERR_TASK098_CONTROL_LOCK_INVALID",
                    "Runtime control lock is not a regular non-reparse file",
                    ProductErrorCategory.SECURITY,
                )
        assert descriptor is not None
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ProductError(
                "ERR_TASK098_CONTROL_LOCK_INVALID",
                "Runtime control lock is not a regular file",
                ProductErrorCategory.SECURITY,
            )
        if opened.st_size == 0:
            os.write(descriptor, b"0")
            os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = True
        current = (
            os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
            if directory.fd is not None
            else os.lstat(directory.path / name)
        )
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ProductError(
                "ERR_TASK098_CONTROL_LOCK_INVALID",
                "Runtime control lock identity changed before acquisition",
                ProductErrorCategory.SECURITY,
            )
        directory.assert_current()
        yield
        directory.assert_current()
        current = (
            os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
            if directory.fd is not None
            else os.lstat(directory.path / name)
        )
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise ProductError(
                "ERR_TASK098_CONTROL_LOCK_INVALID",
                "Runtime control lock identity changed while held",
                ProductErrorCategory.SECURITY,
            )
    except ProductError:
        raise
    except OSError as exc:
        raise ProductError(
            "ERR_TASK098_CONTROL_LOCK_INVALID",
            "Runtime control lock failed closed",
            ProductErrorCategory.SECURITY,
        ) from exc
    finally:
        if descriptor is not None:
            if locked:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{name} must be non-empty text")
    value.encode("utf-8")
    return value


def _second_utc(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SECOND_UTC.fullmatch(value) is None:
        raise ValueError(f"{name} must be a second-precision UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid UTC timestamp") from exc
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return validate_sha256(value, field_name=name)


def derive_runtime_operation_key_v2(
    *,
    project_id: str,
    source_asset_id: str,
    source_asset_sha256: str,
    provider_id: str,
    model_id: str,
    execution_config_sha256: str,
    runtime_request: FasterWhisperRuntimeRequestV1,
) -> str:
    """Derive the one provenance-bound TASK-036 v2 operation identity."""

    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id and source_asset_id must be non-empty")
    if not isinstance(source_asset_id, str) or not source_asset_id.strip():
        raise ValueError("project_id and source_asset_id must be non-empty")
    source_sha = _digest(source_asset_sha256, "source_asset_sha256")
    execution_sha = _digest(execution_config_sha256, "execution_config_sha256")
    request = FasterWhisperRuntimeRequestV1.from_dict(runtime_request.to_dict())
    body = {
        "contract": "task036-local-transcription/2.0.0",
        "project_id": project_id,
        "source_asset_id": source_asset_id,
        "source_asset_sha256": source_sha,
        "provider_id": _text(provider_id, "provider_id"),
        "model_id": _text(model_id, "model_id"),
        "execution_config_sha256": execution_sha,
        "runtime_request_sha256": request.record_sha256,
        "model_download_authorized": False,
    }
    return "task036-transcription-" + hashlib.sha256(
        _OPERATION_DOMAIN + canonical_json_bytes(body),
    ).hexdigest()


def derive_cross_version_guard_key(
    *, project_id: str, source_asset_id: str, source_asset_sha256: str,
) -> str:
    body = {
        "coordination_version": "1.0.0",
        "project_id": project_id,
        "source_asset_id": source_asset_id,
        "source_asset_sha256": source_asset_sha256,
    }
    return "task036-transcription-cross-version-" + hashlib.sha256(
        _GUARD_DOMAIN + canonical_json_bytes(body),
    ).hexdigest()


def derive_output_slot_key(*, production_job_id: str, project_id: str) -> str:
    body = {
        "contract": "task036-local-transcription-fixed-output-slot/1.0.0",
        "project_id": project_id,
        "production_job_id": production_job_id,
    }
    return "task036-transcription-slot-" + hashlib.sha256(
        canonical_json_bytes(body),
    ).hexdigest()


def derive_control_key(
    *, production_job_id: str, project_id: str, source_asset_id: str,
    source_asset_sha256: str, runtime_operation_id: str,
) -> str:
    body = {
        "contract_version": "1.0.0",
        "production_job_id": production_job_id,
        "project_id": project_id,
        "source_asset_id": source_asset_id,
        "source_asset_sha256": source_asset_sha256,
        "runtime_operation_id": runtime_operation_id,
    }
    return "task098-runtime-control-" + hashlib.sha256(
        _CONTROL_DOMAIN + canonical_json_bytes(body),
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class RuntimeTranscriptionCoordinatesV1:
    production_job_id: str
    project_id: str
    source_asset_id: str
    source_asset_sha256: str
    runtime_operation_id: str
    expected_attempt: int
    runtime_admission_ref: str
    runtime_request: FasterWhisperRuntimeRequestV1
    runtime_decision: FasterWhisperRuntimeDecisionV1
    provider_id: str
    model_id: str
    execution_config_sha256: str
    slot_operation_id: str
    recovery_state: str = "ACTIVE_UNKNOWN"

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_project_id(self.project_id)
        validate_id(self.source_asset_id, IdKind.ASSET)
        source_sha = _digest(self.source_asset_sha256, "source_asset_sha256")
        validate_id(self.runtime_operation_id, IdKind.OPERATION)
        validate_id(self.slot_operation_id, IdKind.OPERATION)
        if type(self.expected_attempt) is not int or self.expected_attempt < 1:
            raise ValueError("expected_attempt must be an integer of at least one")
        request, decision = validate_runtime_pair(self.runtime_request, self.runtime_decision)
        admission = (
            "task098-runtime-admission:v2:"
            + source_sha.removeprefix("sha256:")
            + ":"
            + decision.record_sha256.removeprefix("sha256:")
        )
        if self.runtime_admission_ref != admission:
            raise ValueError("runtime_admission_ref does not bind source and decision")
        _text(self.provider_id, "provider_id")
        _text(self.model_id, "model_id")
        _digest(self.execution_config_sha256, "execution_config_sha256")
        if self.recovery_state not in {
            "ACTIVE_UNKNOWN", "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        }:
            raise ValueError("recovery_state is outside the R2b1 closure states")
        object.__setattr__(self, "runtime_request", request)
        object.__setattr__(self, "runtime_decision", decision)

    @property
    def operation_key(self) -> str:
        return derive_runtime_operation_key_v2(
            project_id=self.project_id,
            source_asset_id=self.source_asset_id,
            source_asset_sha256=self.source_asset_sha256,
            provider_id=self.provider_id,
            model_id=self.model_id,
            execution_config_sha256=self.execution_config_sha256,
            runtime_request=self.runtime_request,
        )

    @property
    def control_key(self) -> str:
        return derive_control_key(
            production_job_id=self.production_job_id,
            project_id=self.project_id,
            source_asset_id=self.source_asset_id,
            source_asset_sha256=self.source_asset_sha256,
            runtime_operation_id=self.runtime_operation_id,
        )


@dataclass(frozen=True, slots=True)
class RuntimeTranscriptionDurableControlCoordinatesV1:
    """Detached R2c control coordinates; never a Provider execution admission."""

    production_job_id: str
    project_id: str
    source_asset_id: str
    source_asset_sha256: str
    runtime_operation_id: str
    expected_attempt: int
    runtime_admission_ref: str
    runtime_request: FasterWhisperRuntimeRequestV1
    runtime_decision_sha256: str
    provider_id: str
    model_id: str
    execution_config_sha256: str
    slot_operation_id: str
    recovery_state: str = "ACTIVE_UNKNOWN"

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_project_id(self.project_id)
        validate_id(self.source_asset_id, IdKind.ASSET)
        source_sha = _digest(self.source_asset_sha256, "source_asset_sha256")
        validate_id(self.runtime_operation_id, IdKind.OPERATION)
        validate_id(self.slot_operation_id, IdKind.OPERATION)
        if type(self.expected_attempt) is not int or self.expected_attempt < 1:
            raise ValueError("expected_attempt must be an integer of at least one")
        request = FasterWhisperRuntimeRequestV1.from_dict(self.runtime_request.to_dict())
        decision_sha256 = _digest(
            self.runtime_decision_sha256, "runtime_decision_sha256",
        )
        admission = (
            "task098-runtime-admission:v2:"
            + source_sha.removeprefix("sha256:")
            + ":"
            + decision_sha256.removeprefix("sha256:")
        )
        if self.runtime_admission_ref != admission:
            raise ValueError("runtime_admission_ref does not bind source and decision")
        _text(self.provider_id, "provider_id")
        _text(self.model_id, "model_id")
        _digest(self.execution_config_sha256, "execution_config_sha256")
        if self.recovery_state not in {
            "ACTIVE_UNKNOWN", "ADJUDICATION_REQUIRED_NO_PUBLICATION",
        }:
            raise ValueError("recovery_state is outside the R2c closure states")
        object.__setattr__(self, "runtime_request", request)
        object.__setattr__(self, "runtime_decision_sha256", decision_sha256)

    @property
    def operation_key(self) -> str:
        return derive_runtime_operation_key_v2(
            project_id=self.project_id,
            source_asset_id=self.source_asset_id,
            source_asset_sha256=self.source_asset_sha256,
            provider_id=self.provider_id,
            model_id=self.model_id,
            execution_config_sha256=self.execution_config_sha256,
            runtime_request=self.runtime_request,
        )

    @property
    def control_key(self) -> str:
        return derive_control_key(
            production_job_id=self.production_job_id,
            project_id=self.project_id,
            source_asset_id=self.source_asset_id,
            source_asset_sha256=self.source_asset_sha256,
            runtime_operation_id=self.runtime_operation_id,
        )


_ControlCoordinates = (
    RuntimeTranscriptionCoordinatesV1
    | RuntimeTranscriptionDurableControlCoordinatesV1
)


def _runtime_decision_sha256(coordinates: _ControlCoordinates) -> str:
    if type(coordinates) is RuntimeTranscriptionCoordinatesV1:
        return coordinates.runtime_decision.record_sha256
    if type(coordinates) is RuntimeTranscriptionDurableControlCoordinatesV1:
        return coordinates.runtime_decision_sha256
    raise TypeError("runtime control coordinates have an invalid type")


RecordT = TypeVar("RecordT")


@dataclass(frozen=True, slots=True)
class RuntimeTranscriptionControlChainSnapshotV1:
    """Validated private control chain returned without mutating durable state."""

    control: OperationRecord | None = field(compare=False)
    cancel_request: RuntimeTranscriptionCancelRequestV1 | None = field(default=None, compare=False)
    cancel_outcome: RuntimeTranscriptionCancelOutcomeV1 | None = field(default=None, compare=False)
    adjudication: RuntimeTranscriptionAdjudicationDecisionV1 | None = field(default=None, compare=False)
    barrier: RuntimeTranscriptionCommitBarrierV1 | None = field(default=None, compare=False)
    generation_observation: RuntimeTranscriptionGenerationAbsenceObservationV1 | None = field(default=None, compare=False)
    terminal_commit: RuntimeTranscriptionTerminalClosureCommitV1 | None = field(default=None, compare=False)
    runtime_admission_ref: str | None = None
    runtime_decision_sha256: str | None = None
    identity: tuple[Any, ...] = ()


class _ControlEvidenceStore:
    _KINDS: dict[str, type[Any]] = {
        "cancel-request": RuntimeTranscriptionCancelRequestV1,
        "cancel-outcome": RuntimeTranscriptionCancelOutcomeV1,
        "adjudication": RuntimeTranscriptionAdjudicationDecisionV1,
        "commit-barrier": RuntimeTranscriptionCommitBarrierV1,
        "generation-absence": RuntimeTranscriptionGenerationAbsenceObservationV1,
        "terminal-commit": RuntimeTranscriptionTerminalClosureCommitV1,
    }

    def __init__(self, output_root: Path, runtime_operation_id: str, *, create: bool = True) -> None:
        supplied_root = Path(output_root)
        self.output_root = supplied_root.resolve(strict=True)
        if not supplied_root.is_absolute() or supplied_root != self.output_root:
            raise ProductError(
                "ERR_TASK098_CONTROL_ROOT_INVALID",
                "Runtime control output root must be canonical and non-reparse",
                ProductErrorCategory.SECURITY,
            )
        validate_id(runtime_operation_id, IdKind.OPERATION)
        self.runtime_operation_id = runtime_operation_id
        self.control_root = self.output_root / ".task036-runtime-control"
        self.operation_root = self.control_root / runtime_operation_id
        if create:
            self._ensure_roots()

    def _ensure_roots(self) -> None:
        with _PinnedDirectory(self.output_root) as output:
            output.mkdir(".task036-runtime-control", exist_ok=True)
            with output.pin_child(".task036-runtime-control") as control:
                control.mkdir(self.runtime_operation_id, exist_ok=True)
                with control.pin_child(self.runtime_operation_id) as operation:
                    operation.assert_current()

    @staticmethod
    def operation_artifacts_exist(output_root: Path, runtime_operation_id: str) -> bool:
        validate_id(runtime_operation_id, IdKind.OPERATION)
        with _PinnedDirectory(Path(output_root).resolve(strict=True)) as output:
            if not output.child_exists(".task036-runtime-control"):
                return False
            with output.pin_child(".task036-runtime-control") as control:
                if not control.child_exists(runtime_operation_id):
                    return False
                with control.pin_child(runtime_operation_id) as operation:
                    count = 0
                    for entry in os.scandir(operation.path):
                        count += 1
                        if count > 64:
                            return True
                        if entry.name != "generation-exclusion.lock":
                            return True
                    operation.assert_current()
                    control.assert_current()
                    output.assert_current()
                    return False

    @contextmanager
    def pinned_operation(self) -> Iterator[_PinnedDirectory]:
        with _PinnedDirectory(self.output_root) as output:
            with output.pin_child(".task036-runtime-control") as control:
                with control.pin_child(self.runtime_operation_id) as operation:
                    yield operation
                    operation.assert_current()

    @staticmethod
    def _record_bytes(record: Any) -> bytes:
        return canonical_json_bytes(record.to_dict())

    @staticmethod
    def _filename(kind: str, digest: str) -> str:
        if kind not in _ControlEvidenceStore._KINDS:
            raise ValueError("record kind is invalid")
        return f"{kind}-{_digest(digest, 'record_sha256').removeprefix('sha256:')}.json"

    @staticmethod
    def _create_only(directory: _PinnedDirectory, name: str, data: bytes) -> None:
        name = directory._name(name)
        directory.assert_current()
        if directory.child_exists(name):
            if directory.read(name, max_bytes=_MAX_RECORD_BYTES) != data:
                raise ProductError(
                    "ERR_TASK098_CONTROL_EVIDENCE_CONFLICT",
                    "Immutable runtime control Evidence differs from authorized bytes",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            return
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        if directory.fd is not None:
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(name, flags, 0o600, dir_fd=directory.fd)
            except FileExistsError:
                if directory.read(name, max_bytes=_MAX_RECORD_BYTES) != data:
                    raise ProductError(
                        "ERR_TASK098_CONTROL_EVIDENCE_CONFLICT",
                        "Immutable runtime control Evidence differs from authorized bytes",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
                return
            try:
                with os.fdopen(descriptor, "wb", closefd=False) as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(descriptor)
                observed = os.fstat(descriptor)
                if not stat.S_ISREG(observed.st_mode) or observed.st_size != len(data):
                    raise ProductError(
                        "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                        "Runtime control Evidence identity is invalid",
                        ProductErrorCategory.SECURITY,
                    )
                os.fsync(directory.fd)
            finally:
                os.close(descriptor)
        else:
            target = directory.path / name
            try:
                with target.open("xb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                if directory.read(name, max_bytes=_MAX_RECORD_BYTES) != data:
                    raise ProductError(
                        "ERR_TASK098_CONTROL_EVIDENCE_CONFLICT",
                        "Immutable runtime control Evidence differs from authorized bytes",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
        directory.assert_current()
        if directory.read(name, max_bytes=_MAX_RECORD_BYTES) != data:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence read-back failed",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    def write(self, kind: str, record: Any, *, anchor: str | None = None) -> None:
        expected = self._KINDS.get(kind)
        if expected is None or type(record) is not expected:
            raise TypeError("record does not match its Evidence kind")
        checked = expected.from_dict(record.to_dict())
        raw = self._record_bytes(checked)
        if not 0 < len(raw) <= _MAX_RECORD_BYTES:
            raise ValueError("runtime control Evidence size is invalid")
        with self.pinned_operation() as operation:
            self._create_only(operation, self._filename(kind, checked.record_sha256), raw)
            if anchor is not None:
                self._create_only(operation, anchor, raw)

    def load(self, kind: str, digest: str) -> Any:
        expected = self._KINDS.get(kind)
        if expected is None:
            raise ValueError("record kind is invalid")
        try:
            with self.pinned_operation() as operation:
                raw = operation.read(self._filename(kind, digest), max_bytes=_MAX_RECORD_BYTES)
        except ProductError:
            raise
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Authoritative runtime control Evidence is unavailable",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return self._parse(expected, raw, expected_digest=digest)

    def load_anchor(self, kind: str, anchor: str) -> Any | None:
        expected = self._KINDS.get(kind)
        if expected is None:
            raise ValueError("record kind is invalid")
        try:
            with self.pinned_operation() as operation:
                if not operation.child_exists(anchor):
                    return None
                raw = operation.read(anchor, max_bytes=_MAX_RECORD_BYTES)
        except ProductError:
            raise
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence anchor is unavailable",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return self._parse(expected, raw)

    def has(self, kind: str, digest: str) -> bool:
        if kind not in self._KINDS:
            raise ValueError("record kind is invalid")
        try:
            with self.pinned_operation() as operation:
                return operation.child_exists(self._filename(kind, digest))
        except ProductError:
            raise
        except (OSError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence presence cannot be established",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    @staticmethod
    def _parse(expected: type[RecordT], raw: bytes, *, expected_digest: str | None = None) -> RecordT:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence is malformed",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(value, Mapping):
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence is not an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            record = expected.from_dict(value)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence failed validation",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if expected_digest is not None and record.record_sha256 != expected_digest:
            raise ProductError(
                "ERR_TASK098_CONTROL_EVIDENCE_INVALID",
                "Runtime control Evidence digest is not authoritative",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return record


def runtime_control_artifacts_exist(
    output_root: Path, runtime_operation_id: str,
) -> bool:
    """Read-only bounded presence check for a closed durable-state capture."""

    return _ControlEvidenceStore.operation_artifacts_exist(
        output_root, runtime_operation_id,
    )


class RuntimeTranscriptionCoordinatorV1:
    """Internal R2b1 state coordinator; deliberately not connected to Product UI."""

    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        output_directory: Path,
        clock: Callable[[], datetime | str],
    ) -> None:
        if not isinstance(store, SQLiteProductStore):
            raise TypeError("store must be SQLiteProductStore")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self.store = store
        self.output_directory = Path(output_directory)
        self.clock = clock

    def _now(self) -> str:
        value = self.clock()
        if isinstance(value, str):
            return _second_utc(value, "clock")
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("clock must return aware UTC datetime or canonical text")
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("clock must return UTC")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _request_time(created_at: str) -> str:
        if not isinstance(created_at, str) or not created_at.endswith("Z"):
            raise ProductError(
                "ERR_TASK098_CONTROL_TIME_INVALID",
                "Control creation time is not canonical UTC",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            value = datetime.fromisoformat(created_at[:-1] + "+00:00")
        except ValueError as exc:
            raise ProductError(
                "ERR_TASK098_CONTROL_TIME_INVALID",
                "Control creation time is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ProductError(
                "ERR_TASK098_CONTROL_TIME_INVALID",
                "Control creation time is not UTC",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _conflict(message: str) -> ProductError:
        return ProductError(
            "ERR_TASK098_CONTROL_CONFLICT", message,
            ProductErrorCategory.DATA_INTEGRITY,
        )

    def _evidence(self, coordinates: _ControlCoordinates) -> _ControlEvidenceStore:
        return _ControlEvidenceStore(self.output_directory, coordinates.runtime_operation_id)

    def _require_lease(self, c: _ControlCoordinates) -> OperationRecord:
        key = derive_cross_version_guard_key(
            project_id=c.project_id,
            source_asset_id=c.source_asset_id,
            source_asset_sha256=c.source_asset_sha256,
        )
        lease = self.store.find_operation(c.production_job_id, key)
        expected_ref = "task098-runtime-owner:v2:" + key.rsplit("-", 1)[-1]
        if (
            lease is None
            or lease.job_id != c.production_job_id
            or lease.command_type != LEASE_COMMAND
            or lease.idempotency_key != key
            or lease.status != "IN_PROGRESS"
            or lease.attempt != 0
            or lease.result_ref != expected_ref
        ):
            raise self._conflict("Runtime source lease is missing or changed")
        return lease

    def _require_main(
        self,
        c: _ControlCoordinates,
        *,
        statuses: tuple[str, ...],
        result_refs: tuple[str, ...],
    ) -> OperationRecord:
        operation = self.store.get_operation(c.runtime_operation_id)
        if (
            operation.job_id != c.production_job_id
            or operation.command_type != MAIN_COMMAND
            or operation.idempotency_key != c.operation_key
            or operation.status not in statuses
            or operation.attempt != c.expected_attempt
            or operation.result_ref not in result_refs
        ):
            raise self._conflict("Runtime operation is outside the exact closure coordinate")
        return operation

    def _require_slot(
        self, c: _ControlCoordinates, *, statuses: tuple[str, ...],
    ) -> OperationRecord:
        slot = self.store.get_operation(c.slot_operation_id)
        if (
            slot.job_id != c.production_job_id
            or slot.command_type != SLOT_COMMAND
            or slot.idempotency_key != derive_output_slot_key(
                production_job_id=c.production_job_id, project_id=c.project_id,
            )
            or slot.status not in statuses
            or slot.result_ref != c.runtime_operation_id
        ):
            raise self._conflict("Runtime output slot is missing or changed")
        return slot

    def _reserve_control(self, c: _ControlCoordinates) -> OperationRecord:
        control, _created = self.store.reserve_operation(
            c.production_job_id, CONTROL_COMMAND, c.control_key,
        )
        if (
            control.job_id != c.production_job_id
            or control.command_type != CONTROL_COMMAND
            or control.idempotency_key != c.control_key
            or control.attempt != 0
        ):
            raise self._conflict("Runtime control row identity is invalid")
        return control

    def _require_control(
        self,
        c: _ControlCoordinates,
        operation_id: str,
        *,
        status: str,
        result_ref: str,
    ) -> OperationRecord:
        control = self.store.get_operation(operation_id)
        if (
            control.job_id != c.production_job_id
            or control.command_type != CONTROL_COMMAND
            or control.idempotency_key != c.control_key
            or control.status != status
            or control.attempt != 0
            or control.result_ref != result_ref
        ):
            raise self._conflict("Runtime control row changed outside the exact transition")
        return control

    @staticmethod
    def _record_binds(record: Any, c: _ControlCoordinates) -> bool:
        return (
            record.runtime_operation_id == c.runtime_operation_id
            and record.slot_operation_id == c.slot_operation_id
            and record.source_asset_sha256 == c.source_asset_sha256
            and record.expected_attempt == c.expected_attempt
            and getattr(record, "runtime_admission_ref", c.runtime_admission_ref)
                == c.runtime_admission_ref
            and getattr(record, "prior_runtime_admission_ref", c.runtime_admission_ref)
                == c.runtime_admission_ref
            and getattr(record, "runtime_request_sha256", c.runtime_request.record_sha256)
                == c.runtime_request.record_sha256
            and getattr(record, "runtime_decision_sha256", _runtime_decision_sha256(c))
                == _runtime_decision_sha256(c)
        )

    def _require_active(self, c: _ControlCoordinates, *, status: str) -> None:
        self._require_lease(c)
        self._require_main(c, statuses=(status,), result_refs=(c.runtime_admission_ref,))
        self._require_slot(c, statuses=("IN_PROGRESS",))

    @contextmanager
    def generation_exclusion_lock(
        self, coordinates: RuntimeTranscriptionCoordinatesV1,
    ) -> Iterator[None]:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        with self._generation_exclusion_lock(coordinates):
            yield

    @contextmanager
    def _generation_exclusion_lock(
        self, coordinates: _ControlCoordinates,
    ) -> Iterator[None]:
        evidence = self._evidence(coordinates)
        with evidence.pinned_operation() as operation:
            with _exclusive_pinned_file_lock(operation, "generation-exclusion.lock"):
                operation.assert_current()
                yield
                operation.assert_current()

    def request_cancel(
        self, coordinates: RuntimeTranscriptionCoordinatesV1,
        *, fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCancelRequestV1:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        return self._request_cancel(coordinates, fault_hook=fault_hook)

    def request_cancel_from_durable_coordinates(
        self, coordinates: RuntimeTranscriptionDurableControlCoordinatesV1,
        *, fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCancelRequestV1:
        if type(coordinates) is not RuntimeTranscriptionDurableControlCoordinatesV1:
            raise TypeError(
                "coordinates must be RuntimeTranscriptionDurableControlCoordinatesV1",
            )
        return self._request_cancel(coordinates, fault_hook=fault_hook)

    def _request_cancel(
        self, coordinates: _ControlCoordinates,
        *, fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCancelRequestV1:
        c = coordinates
        self._require_active(c, status="IN_PROGRESS")
        control = self._reserve_control(c)
        evidence = self._evidence(c)
        if control.status == "IN_PROGRESS" and control.result_ref is not None:
            try:
                request_digest = _typed_control_digest("cancel-request", control.result_ref)
            except ValueError as exc:
                raise self._conflict("Control row does not contain a typed cancel request") from exc
            existing = evidence.load("cancel-request", request_digest)
            if self._record_binds(existing, c) and existing.cancel_request_id == control.operation_id:
                return existing
            raise self._conflict("Control row does not contain the expected cancel request")
        if control.status != "PENDING" or control.result_ref is not None:
            raise self._conflict("A publication or terminal barrier already owns control")
        request = RuntimeTranscriptionCancelRequestV1.create(
            cancel_request_id=control.operation_id,
            runtime_operation_id=c.runtime_operation_id,
            slot_operation_id=c.slot_operation_id,
            source_asset_sha256=c.source_asset_sha256,
            runtime_admission_ref=c.runtime_admission_ref,
            runtime_request_sha256=c.runtime_request.record_sha256,
            runtime_decision_sha256=_runtime_decision_sha256(c),
            expected_attempt=c.expected_attempt,
            requested_at=self._request_time(control.created_at),
        )
        evidence.write("cancel-request", request)
        request_ref = _typed_control_ref("cancel-request", request.record_sha256)
        if fault_hook is not None:
            fault_hook("after_cancel_request_write")
        self._require_active(c, status="IN_PROGRESS")
        updated, changed = self.store.compare_and_set_operation_status(
            control.operation_id,
            expected_statuses=("PENDING",),
            expected_result_refs=(None,),
            expected_attempt=0,
            status="IN_PROGRESS",
            result_ref=request_ref,
            replace_result_ref=True,
        )
        if not changed and not (
            updated.status == "IN_PROGRESS"
            and updated.attempt == 0
            and updated.result_ref == request_ref
        ):
            raise self._conflict("Cancel request lost the control-row CAS")
        return request

    def observe_cancel_request(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
    ) -> RuntimeTranscriptionCancelRequestV1 | None:
        """Read one exact worker-visible request without reserving control."""

        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        c = coordinates
        self._require_active(c, status="IN_PROGRESS")
        control = self.store.find_operation(c.production_job_id, c.control_key)
        if control is None:
            return None
        if (
            control.job_id != c.production_job_id
            or control.command_type != CONTROL_COMMAND
            or control.idempotency_key != c.control_key
            or control.attempt != 0
        ):
            raise self._conflict("Runtime control row identity is invalid")
        if control.status == "PENDING" and control.result_ref is None:
            return None
        if control.status != "IN_PROGRESS" or control.result_ref is None:
            raise self._conflict("Control row is not an observable cancel request")
        try:
            request_digest = _typed_control_digest("cancel-request", control.result_ref)
        except ValueError as exc:
            raise self._conflict("Control row is not an exact cancel request") from exc
        request = self._evidence(c).load("cancel-request", request_digest)
        if not self._record_binds(request, c) or request.cancel_request_id != control.operation_id:
            raise self._conflict("Cancel request does not bind the exact worker coordinate")
        return request

    def validate_active_control_state(
        self,
        *,
        production_job_id: str,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        runtime_operation_id: str,
        expected_attempt: int,
        runtime_admission_ref: str,
        runtime_request_sha256: str,
        runtime_decision_sha256: str,
        slot_operation_id: str,
    ) -> bool:
        """Validate a pre-publication control chain without reserving or mutating it."""

        try:
            validate_id(production_job_id, IdKind.JOB)
            validate_project_id(project_id)
            validate_id(source_asset_id, IdKind.ASSET)
            _digest(source_asset_sha256, "source_asset_sha256")
            validate_id(runtime_operation_id, IdKind.OPERATION)
            validate_id(slot_operation_id, IdKind.OPERATION)
            _digest(runtime_request_sha256, "runtime_request_sha256")
            _digest(runtime_decision_sha256, "runtime_decision_sha256")
            if type(expected_attempt) is not int or expected_attempt < 1:
                return False
            expected_control_key = derive_control_key(
                production_job_id=production_job_id,
                project_id=project_id,
                source_asset_id=source_asset_id,
                source_asset_sha256=source_asset_sha256,
                runtime_operation_id=runtime_operation_id,
            )
            control = self.store.find_operation(production_job_id, expected_control_key)
            if control is None:
                return True
            if (
                control.job_id != production_job_id
                or control.command_type != CONTROL_COMMAND
                or control.idempotency_key != expected_control_key
                or control.attempt != 0
            ):
                return False
            if control.status == "PENDING" and control.result_ref is None:
                return True
            if control.status != "IN_PROGRESS" or control.result_ref is None:
                return False
            evidence = _ControlEvidenceStore(self.output_directory, runtime_operation_id)
            kind: str
            try:
                record_digest = _typed_control_digest("cancel-request", control.result_ref)
                kind = "cancel-request"
            except ValueError:
                record_digest = _typed_control_digest("cancel-outcome", control.result_ref)
                kind = "cancel-outcome"
            record = evidence.load(kind, record_digest)

            def binds(value: Any) -> bool:
                return (
                    value.runtime_operation_id == runtime_operation_id
                    and value.slot_operation_id == slot_operation_id
                    and value.source_asset_sha256 == source_asset_sha256
                    and value.runtime_admission_ref == runtime_admission_ref
                    and value.runtime_request_sha256 == runtime_request_sha256
                    and value.runtime_decision_sha256 == runtime_decision_sha256
                    and value.expected_attempt == expected_attempt
                )

            if not binds(record):
                return False
            if kind == "cancel-request":
                return record.cancel_request_id == control.operation_id
            request = evidence.load("cancel-request", record.cancel_request_sha256)
            return (
                binds(request)
                and request.cancel_request_id == control.operation_id
                and record.cancel_request_sha256 == request.record_sha256
            )
        except (OSError, ProductError, TypeError, ValueError):
            return False

    def read_control_chain(
        self,
        *,
        production_job_id: str,
        project_id: str,
        source_asset_id: str,
        source_asset_sha256: str,
        runtime_operation_id: str,
        expected_attempt: int,
        runtime_request_sha256: str,
        slot_operation_id: str,
        runtime_admission_ref: str | None = None,
        runtime_decision_sha256: str | None = None,
    ) -> RuntimeTranscriptionControlChainSnapshotV1:
        """Read and validate the exact R2 durable chain without creating state."""

        try:
            validate_id(production_job_id, IdKind.JOB)
            validate_project_id(project_id)
            validate_id(source_asset_id, IdKind.ASSET)
            source_sha = _digest(source_asset_sha256, "source_asset_sha256")
            validate_id(runtime_operation_id, IdKind.OPERATION)
            validate_id(slot_operation_id, IdKind.OPERATION)
            request_sha = _digest(runtime_request_sha256, "runtime_request_sha256")
            if type(expected_attempt) is not int or expected_attempt < 1:
                raise ValueError("expected_attempt must be at least one")
            if runtime_decision_sha256 is not None:
                runtime_decision_sha256 = _digest(
                    runtime_decision_sha256, "runtime_decision_sha256",
                )
            if runtime_admission_ref is not None:
                admission_match = re.fullmatch(
                    r"task098-runtime-admission:v2:([0-9a-f]{64}):([0-9a-f]{64})",
                    runtime_admission_ref,
                )
                if (
                    admission_match is None
                    or admission_match.group(1) != source_sha.removeprefix("sha256:")
                    or (
                        runtime_decision_sha256 is not None
                        and admission_match.group(2)
                        != runtime_decision_sha256.removeprefix("sha256:")
                    )
                ):
                    raise ValueError("runtime admission coordinate is invalid")
                runtime_decision_sha256 = "sha256:" + admission_match.group(2)
            control_key = derive_control_key(
                production_job_id=production_job_id,
                project_id=project_id,
                source_asset_id=source_asset_id,
                source_asset_sha256=source_sha,
                runtime_operation_id=runtime_operation_id,
            )
            control = self.store.find_operation(production_job_id, control_key)
            if control is None:
                if _ControlEvidenceStore.operation_artifacts_exist(
                    self.output_directory, runtime_operation_id,
                ):
                    raise self._conflict(
                        "Runtime control Evidence exists without its control row",
                    )
                return RuntimeTranscriptionControlChainSnapshotV1(
                    control=None,
                    runtime_admission_ref=runtime_admission_ref,
                    runtime_decision_sha256=runtime_decision_sha256,
                    identity=("ABSENT", control_key),
                )
            if (
                control.job_id != production_job_id
                or control.command_type != CONTROL_COMMAND
                or control.idempotency_key != control_key
                or control.attempt != 0
            ):
                raise self._conflict("Runtime control row identity is invalid")
            control_identity = (
                control.operation_id, control.job_id, control.command_type,
                control.idempotency_key, control.status, control.attempt,
                control.created_at, control.updated_at, control.last_error_code,
                control.result_ref,
            )
            if control.status == "PENDING" and control.result_ref is None:
                if _ControlEvidenceStore.operation_artifacts_exist(
                    self.output_directory, runtime_operation_id,
                ):
                    raise self._conflict(
                        "Pending runtime control has unexpected Evidence",
                    )
                return RuntimeTranscriptionControlChainSnapshotV1(
                    control=control,
                    runtime_admission_ref=runtime_admission_ref,
                    runtime_decision_sha256=runtime_decision_sha256,
                    identity=("PENDING", control_identity),
                )
            if control.result_ref is None:
                raise self._conflict("Runtime control row lacks its typed reference")

            evidence = _ControlEvidenceStore(
                self.output_directory, runtime_operation_id, create=False,
            )
            request: RuntimeTranscriptionCancelRequestV1 | None = None
            outcome: RuntimeTranscriptionCancelOutcomeV1 | None = None
            adjudication: RuntimeTranscriptionAdjudicationDecisionV1 | None = None
            barrier: RuntimeTranscriptionCommitBarrierV1 | None = None
            observation: RuntimeTranscriptionGenerationAbsenceObservationV1 | None = None
            commit: RuntimeTranscriptionTerminalClosureCommitV1 | None = None

            if control.status == "IN_PROGRESS":
                for kind in ("cancel-request", "cancel-outcome", "commit-barrier"):
                    try:
                        digest = _typed_control_digest(kind, control.result_ref)
                    except ValueError:
                        continue
                    if kind == "cancel-request":
                        request = evidence.load(kind, digest)
                    elif kind == "cancel-outcome":
                        outcome = evidence.load(kind, digest)
                        request = evidence.load("cancel-request", outcome.cancel_request_sha256)
                    else:
                        barrier = evidence.load(kind, digest)
                        if barrier.barrier_owner != "PUBLICATION":
                            raise self._conflict("In-progress barrier is not publication-owned")
                    break
                else:
                    raise self._conflict("Runtime control ref is not an accepted in-progress type")
            elif control.status == "PARTIAL":
                digest = _typed_control_digest("commit-barrier", control.result_ref)
                barrier = evidence.load("commit-barrier", digest)
                if barrier.barrier_owner != "TERMINAL_CLOSURE" or barrier.closure_record_sha256 is None:
                    raise self._conflict("Partial control lacks a terminal closure barrier")
                closure_sha = barrier.closure_record_sha256
                has_outcome = evidence.has("cancel-outcome", closure_sha)
                has_adjudication = evidence.has("adjudication", closure_sha)
                if has_outcome == has_adjudication:
                    raise self._conflict("Terminal closure kind is missing or ambiguous")
                if has_outcome:
                    outcome = evidence.load("cancel-outcome", closure_sha)
                    request = evidence.load("cancel-request", outcome.cancel_request_sha256)
                else:
                    adjudication = evidence.load("adjudication", closure_sha)
                observation = evidence.load_anchor(
                    "generation-absence", "generation-absence.json",
                )
                commit = evidence.load_anchor("terminal-commit", "terminal-commit.json")
            elif control.status == "COMPLETED":
                try:
                    digest = _typed_control_digest("commit-barrier", control.result_ref)
                except ValueError:
                    digest = _typed_control_digest("terminal-commit", control.result_ref)
                    commit = evidence.load("terminal-commit", digest)
                    barrier = evidence.load("commit-barrier", commit.commit_barrier_sha256)
                    observation = evidence.load(
                        "generation-absence",
                        commit.generation_absence_observation_sha256,
                    )
                    if commit.closure_kind == "CONFIRMED_CANCEL":
                        outcome = evidence.load("cancel-outcome", commit.closure_record_sha256)
                        request = evidence.load("cancel-request", outcome.cancel_request_sha256)
                    else:
                        adjudication = evidence.load("adjudication", commit.closure_record_sha256)
                else:
                    barrier = evidence.load("commit-barrier", digest)
                    if barrier.barrier_owner != "PUBLICATION":
                        raise self._conflict("Completed barrier is not publication-owned")
            else:
                raise self._conflict("Runtime control status is outside the closed matrix")

            records = tuple(
                value for value in (
                    request, outcome, adjudication, barrier, observation, commit,
                ) if value is not None
            )
            admissions: set[str] = set()
            decision_digests: set[str] = set()
            for record in records:
                if (
                    record.runtime_operation_id != runtime_operation_id
                    or record.slot_operation_id != slot_operation_id
                    or record.source_asset_sha256 != source_sha
                    or record.expected_attempt != expected_attempt
                ):
                    raise self._conflict("Runtime control Evidence binds a foreign coordinate")
                admission = getattr(
                    record, "runtime_admission_ref",
                    getattr(record, "prior_runtime_admission_ref", None),
                )
                if admission is not None:
                    admissions.add(admission)
                decision_sha = getattr(record, "runtime_decision_sha256", None)
                if decision_sha is not None:
                    decision_digests.add(decision_sha)
                record_request_sha = getattr(record, "runtime_request_sha256", None)
                if record_request_sha is not None and record_request_sha != request_sha:
                    raise self._conflict("Runtime control Evidence binds a foreign request")
            if request is not None and request.cancel_request_id != control.operation_id:
                raise self._conflict("Cancel request does not bind its control operation")
            if outcome is not None and (
                request is None or outcome.cancel_request_sha256 != request.record_sha256
            ):
                raise self._conflict("Cancel outcome predecessor is invalid")
            if barrier is not None and barrier.barrier_owner == "TERMINAL_CLOSURE":
                closure = outcome or adjudication
                if closure is None or barrier.closure_record_sha256 != closure.record_sha256:
                    raise self._conflict("Terminal barrier predecessor is invalid")
            if observation is not None and (
                barrier is None or observation.commit_barrier_sha256 != barrier.record_sha256
            ):
                raise self._conflict("Generation observation predecessor is invalid")
            if commit is not None and (
                barrier is None
                or observation is None
                or commit.commit_barrier_sha256 != barrier.record_sha256
                or commit.generation_absence_observation_sha256 != observation.record_sha256
                or commit.closure_record_sha256
                != (outcome or adjudication).record_sha256
            ):
                raise self._conflict("Terminal commit predecessor chain is invalid")
            if runtime_admission_ref is not None:
                admissions.add(runtime_admission_ref)
            if runtime_decision_sha256 is not None:
                decision_digests.add(runtime_decision_sha256)
            if len(admissions) > 1 or len(decision_digests) > 1:
                raise self._conflict("Runtime control admission identity is mixed")
            resolved_admission = next(iter(admissions), None)
            resolved_decision = next(iter(decision_digests), None)
            if resolved_admission is not None:
                match = re.fullmatch(
                    r"task098-runtime-admission:v2:([0-9a-f]{64}):([0-9a-f]{64})",
                    resolved_admission,
                )
                if match is None or match.group(1) != source_sha.removeprefix("sha256:"):
                    raise self._conflict("Runtime control admission is invalid")
                admitted_decision = "sha256:" + match.group(2)
                if resolved_decision not in {None, admitted_decision}:
                    raise self._conflict("Runtime control decision digest is mixed")
                resolved_decision = admitted_decision
            identities = tuple(
                None if value is None else value.record_sha256
                for value in (request, outcome, adjudication, barrier, observation, commit)
            )
            return RuntimeTranscriptionControlChainSnapshotV1(
                control=control,
                cancel_request=request,
                cancel_outcome=outcome,
                adjudication=adjudication,
                barrier=barrier,
                generation_observation=observation,
                terminal_commit=commit,
                runtime_admission_ref=resolved_admission,
                runtime_decision_sha256=resolved_decision,
                identity=("CHAIN", control_identity, *identities),
            )
        except ProductError:
            raise
        except (OSError, TypeError, ValueError, AttributeError) as exc:
            raise self._conflict("Runtime control chain could not be validated") from exc

    def acknowledge_worker_cancel(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        *,
        provider_execution_started: bool,
        provider_stop_confirmed: bool,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCancelOutcomeV1:
        """Bind a closed worker outcome and terminal-close only a proven stop."""

        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        if type(provider_execution_started) is not bool or type(provider_stop_confirmed) is not bool:
            raise TypeError("worker cancellation facts must be booleans")
        if not provider_execution_started and not provider_stop_confirmed:
            raise ValueError("pre-Provider cancellation must be synchronously confirmed")
        if provider_stop_confirmed:
            outcome_name = (
                "CANCELLED_AFTER_COOPERATIVE_BOUNDARY"
                if provider_execution_started
                else "CANCELLED_BEFORE_PROVIDER_EFFECT"
            )
            evidence_name = "COOPERATIVE_CHECKPOINT" if provider_execution_started else "PRE_PROVIDER"
        else:
            outcome_name = "STOP_NOT_CONFIRMED"
            evidence_name = "NONE"
        c = coordinates
        control = self.store.find_operation(c.production_job_id, c.control_key)
        if control is None:
            raise self._conflict("No exact cancel request is available to acknowledge")
        if (
            control.job_id != c.production_job_id
            or control.command_type != CONTROL_COMMAND
            or control.idempotency_key != c.control_key
            or control.attempt != 0
            or control.result_ref is None
        ):
            raise self._conflict("Runtime control row is not an exact cancellation chain")
        evidence = self._evidence(c)
        existing: RuntimeTranscriptionCancelOutcomeV1 | None = None
        try:
            if control.status == "IN_PROGRESS":
                try:
                    request_digest = _typed_control_digest("cancel-request", control.result_ref)
                    request = evidence.load("cancel-request", request_digest)
                except ValueError:
                    outcome_digest = _typed_control_digest("cancel-outcome", control.result_ref)
                    existing = evidence.load("cancel-outcome", outcome_digest)
                    request = evidence.load("cancel-request", existing.cancel_request_sha256)
            elif control.status == "PARTIAL":
                barrier_digest = _typed_control_digest("commit-barrier", control.result_ref)
                barrier = evidence.load("commit-barrier", barrier_digest)
                if barrier.barrier_owner != "TERMINAL_CLOSURE" or barrier.closure_record_sha256 is None:
                    raise ValueError("control is not a cancellation terminal barrier")
                existing = evidence.load("cancel-outcome", barrier.closure_record_sha256)
                request = evidence.load("cancel-request", existing.cancel_request_sha256)
            elif control.status == "COMPLETED":
                commit_digest = _typed_control_digest("terminal-commit", control.result_ref)
                commit = evidence.load("terminal-commit", commit_digest)
                if commit.closure_kind != "CONFIRMED_CANCEL":
                    raise ValueError("completed control is not a cancellation commit")
                existing = evidence.load("cancel-outcome", commit.closure_record_sha256)
                request = evidence.load("cancel-request", existing.cancel_request_sha256)
            else:
                raise ValueError("control status is not a cancellation state")
        except (OSError, ProductError, ValueError) as exc:
            if isinstance(exc, ProductError) and exc.code == "ERR_TASK098_CONTROL_CONFLICT":
                raise
            raise self._conflict("Runtime control row is not an exact cancellation chain") from exc
        if (
            not self._record_binds(request, c)
            or request.cancel_request_id != control.operation_id
        ):
            raise self._conflict("Cancellation chain does not bind the exact request")
        if existing is not None:
            if (
                not self._record_binds(existing, c)
                or existing.cancel_request_sha256 != request.record_sha256
                or existing.outcome != outcome_name
                or existing.provider_execution_started is not provider_execution_started
                or existing.provider_stop_confirmed is not provider_stop_confirmed
                or existing.stop_evidence != evidence_name
            ):
                raise self._conflict("A different worker cancellation outcome is authoritative")
            if provider_stop_confirmed:
                self.close_confirmed_cancel(c, fault_hook=fault_hook)
            return existing
        outcome = RuntimeTranscriptionCancelOutcomeV1.create(
            cancel_request_sha256=request.record_sha256,
            runtime_operation_id=c.runtime_operation_id,
            slot_operation_id=c.slot_operation_id,
            source_asset_sha256=c.source_asset_sha256,
            runtime_admission_ref=c.runtime_admission_ref,
            runtime_request_sha256=c.runtime_request.record_sha256,
            runtime_decision_sha256=_runtime_decision_sha256(c),
            expected_attempt=c.expected_attempt,
            outcome=outcome_name,
            provider_execution_started=provider_execution_started,
            provider_stop_confirmed=provider_stop_confirmed,
            stop_evidence=evidence_name,
            acknowledged_at=self._now(),
        )
        bound = self.bind_cancel_outcome(c, outcome, fault_hook=fault_hook)
        if provider_stop_confirmed:
            self.close_confirmed_cancel(c, fault_hook=fault_hook)
        return bound

    def bind_cancel_outcome(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        outcome: RuntimeTranscriptionCancelOutcomeV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCancelOutcomeV1:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        c = coordinates
        checked = RuntimeTranscriptionCancelOutcomeV1.from_dict(outcome.to_dict())
        if not self._record_binds(checked, c):
            raise ValueError("cancel outcome does not bind the exact runtime coordinate")
        self._require_active(c, status="IN_PROGRESS")
        control = self._reserve_control(c)
        evidence = self._evidence(c)
        outcome_ref = _typed_control_ref("cancel-outcome", checked.record_sha256)
        if control.status == "IN_PROGRESS" and control.result_ref == outcome_ref:
            return evidence.load("cancel-outcome", checked.record_sha256)
        if control.status != "IN_PROGRESS" or control.result_ref is None:
            raise self._conflict("Cancel outcome has no authoritative request")
        try:
            request_digest = _typed_control_digest("cancel-request", control.result_ref)
        except ValueError as exc:
            raise self._conflict("Cancel outcome has no typed authoritative request") from exc
        request = evidence.load("cancel-request", request_digest)
        if checked.cancel_request_sha256 != request.record_sha256:
            raise ValueError("cancel outcome does not bind the authoritative request")
        evidence.write("cancel-outcome", checked)
        if fault_hook is not None:
            fault_hook("after_cancel_outcome_write")
        self._require_active(c, status="IN_PROGRESS")
        updated, changed = self.store.compare_and_set_operation_status(
            control.operation_id,
            expected_statuses=("IN_PROGRESS",),
            expected_result_refs=(control.result_ref,),
            expected_attempt=0,
            status="IN_PROGRESS",
            result_ref=outcome_ref,
            replace_result_ref=True,
        )
        if not changed and not (
            updated.status == "IN_PROGRESS"
            and updated.attempt == 0
            and updated.result_ref == outcome_ref
        ):
            raise self._conflict("Cancel outcome lost the control-row CAS")
        return checked

    def acquire_publication_barrier(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        first_generation_writer: Callable[[RuntimeTranscriptionCommitBarrierV1], Any],
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCommitBarrierV1:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        if not callable(first_generation_writer):
            raise TypeError("first_generation_writer must be callable")
        c = coordinates
        with self._generation_exclusion_lock(c):
            self._require_active(c, status="IN_PROGRESS")
            control = self._reserve_control(c)
            evidence = self._evidence(c)
            if control.status == "IN_PROGRESS" and control.result_ref is not None:
                try:
                    barrier_digest = _typed_control_digest("commit-barrier", control.result_ref)
                    barrier = evidence.load("commit-barrier", barrier_digest)
                except (OSError, ProductError, ValueError):
                    raise self._conflict("Control is owned by a cancel request or invalid barrier")
                if barrier.barrier_owner != "PUBLICATION" or not self._record_binds(barrier, c):
                    raise self._conflict("Control is not owned by the exact publication barrier")
            else:
                if control.status != "PENDING" or control.result_ref is not None:
                    raise self._conflict("Cancellation or terminal closure already owns control")
                barrier = RuntimeTranscriptionCommitBarrierV1.create(
                    runtime_operation_id=c.runtime_operation_id,
                    slot_operation_id=c.slot_operation_id,
                    source_asset_sha256=c.source_asset_sha256,
                    runtime_admission_ref=c.runtime_admission_ref,
                    expected_attempt=c.expected_attempt,
                    barrier_owner="PUBLICATION",
                    closure_record_sha256=None,
                    acquired_at=self._now(),
                )
                evidence.write("commit-barrier", barrier)
                barrier_ref = _typed_control_ref("commit-barrier", barrier.record_sha256)
                if fault_hook is not None:
                    fault_hook("after_publication_barrier_write")
                self._require_active(c, status="IN_PROGRESS")
                updated, changed = self.store.compare_and_set_operation_status(
                    control.operation_id,
                    expected_statuses=("PENDING",),
                    expected_result_refs=(None,),
                    expected_attempt=0,
                    status="IN_PROGRESS",
                    result_ref=barrier_ref,
                    replace_result_ref=True,
                )
                if not changed and not (
                    updated.status == "IN_PROGRESS"
                    and updated.attempt == 0
                    and updated.result_ref == barrier_ref
                ):
                    raise self._conflict("Publication barrier lost the control-row CAS")
            if fault_hook is not None:
                fault_hook("after_publication_barrier")
            first_generation_writer(barrier)
            if fault_hook is not None:
                fault_hook("after_first_generation_write")
            return barrier

    def complete_publication(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        publication_set_sha256: str,
        barrier: RuntimeTranscriptionCommitBarrierV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCommitBarrierV1:
        """Close only the exact publication barrier after main binds its digest."""

        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        c = coordinates
        digest = _digest(publication_set_sha256, "publication_set_sha256")
        checked = RuntimeTranscriptionCommitBarrierV1.from_dict(barrier.to_dict())
        if (
            checked.barrier_owner != "PUBLICATION"
            or checked.closure_record_sha256 is not None
            or not self._record_binds(checked, c)
        ):
            raise self._conflict("Publication barrier does not bind the exact coordinate")
        self._require_lease(c)
        main = self._require_main(
            c, statuses=("PARTIAL", "COMPLETED"), result_refs=(digest,),
        )
        self._require_slot(c, statuses=("IN_PROGRESS",))
        evidence = self._evidence(c)
        stored = evidence.load("commit-barrier", checked.record_sha256)
        if stored.to_dict() != checked.to_dict():
            raise self._conflict("Publication barrier Evidence differs from the caller")
        barrier_ref = _typed_control_ref("commit-barrier", checked.record_sha256)
        control = self.store.find_operation(c.production_job_id, c.control_key)
        if control is None:
            raise self._conflict("Publication control row is missing")
        if main.status == "COMPLETED":
            self._require_control(
                c, control.operation_id, status="COMPLETED", result_ref=barrier_ref,
            )
            return checked
        if control.status == "COMPLETED" and control.attempt == 0 and control.result_ref == barrier_ref:
            self._require_control(
                c, control.operation_id, status="COMPLETED", result_ref=barrier_ref,
            )
            return checked
        self._require_control(
            c, control.operation_id, status="IN_PROGRESS", result_ref=barrier_ref,
        )
        updated, changed = self.store.compare_and_set_operation_status(
            control.operation_id,
            expected_statuses=("IN_PROGRESS",),
            expected_result_refs=(barrier_ref,),
            expected_attempt=0,
            status="COMPLETED",
            result_ref=barrier_ref,
            replace_result_ref=True,
        )
        if not changed and not (
            updated.status == "COMPLETED"
            and updated.attempt == 0
            and updated.result_ref == barrier_ref
        ):
            raise self._conflict("Publication completion lost the control-row CAS")
        if fault_hook is not None:
            fault_hook("after_publication_control_completion")
        return checked

    def reconcile_publication(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        publication_set_sha256: str,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionCommitBarrierV1:
        """Recover an exact already-bound publication without reserving control."""

        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        c = coordinates
        control = self.store.find_operation(c.production_job_id, c.control_key)
        if control is None or control.result_ref is None:
            raise self._conflict("Publication recovery control row is missing")
        if (
            control.job_id != c.production_job_id
            or control.command_type != CONTROL_COMMAND
            or control.idempotency_key != c.control_key
            or control.attempt != 0
            or control.status not in {"IN_PROGRESS", "COMPLETED"}
        ):
            raise self._conflict("Publication recovery control row is invalid")
        try:
            barrier_digest = _typed_control_digest("commit-barrier", control.result_ref)
        except ValueError as exc:
            raise self._conflict("Publication recovery lacks its typed barrier") from exc
        barrier = self._evidence(c).load("commit-barrier", barrier_digest)
        if barrier.barrier_owner != "PUBLICATION" or not self._record_binds(barrier, c):
            raise self._conflict("Publication recovery barrier is foreign")
        return self.complete_publication(
            c, publication_set_sha256, barrier, fault_hook=fault_hook,
        )

    def close_confirmed_cancel(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        c = coordinates
        with self._generation_exclusion_lock(c):
            self._require_lease(c)
            control = self._reserve_control(c)
            evidence = self._evidence(c)
            if control.status == "COMPLETED":
                return self._resume_completed(
                    c, control, evidence, expected_closure_kind="CONFIRMED_CANCEL",
                )
            if control.status == "PARTIAL":
                try:
                    barrier_digest = _typed_control_digest("commit-barrier", control.result_ref)
                except ValueError as exc:
                    raise self._conflict("Terminal control lacks its typed barrier") from exc
                barrier = evidence.load("commit-barrier", barrier_digest)
                outcome = evidence.load("cancel-outcome", barrier.closure_record_sha256)
                if outcome.outcome == "STOP_NOT_CONFIRMED" or not outcome.provider_stop_confirmed:
                    raise self._conflict("Provider stop is not confirmed")
            else:
                self._require_active(c, status="IN_PROGRESS")
                if control.status != "IN_PROGRESS" or control.result_ref is None:
                    raise self._conflict("Confirmed cancel has no authoritative outcome")
                try:
                    outcome_digest = _typed_control_digest("cancel-outcome", control.result_ref)
                except ValueError as exc:
                    raise self._conflict("Confirmed cancel lacks its typed outcome") from exc
                outcome = evidence.load("cancel-outcome", outcome_digest)
                if outcome.outcome == "STOP_NOT_CONFIRMED" or not outcome.provider_stop_confirmed:
                    raise self._conflict("Provider stop is not confirmed")
                barrier = RuntimeTranscriptionCommitBarrierV1.create(
                    runtime_operation_id=c.runtime_operation_id,
                    slot_operation_id=c.slot_operation_id,
                    source_asset_sha256=c.source_asset_sha256,
                    runtime_admission_ref=c.runtime_admission_ref,
                    expected_attempt=c.expected_attempt,
                    barrier_owner="TERMINAL_CLOSURE",
                    closure_record_sha256=outcome.record_sha256,
                    acquired_at=self._now(),
                )
                evidence.write("commit-barrier", barrier)
                barrier_ref = _typed_control_ref("commit-barrier", barrier.record_sha256)
                updated, changed = self.store.compare_and_set_operation_status(
                    control.operation_id,
                    expected_statuses=("IN_PROGRESS",),
                    expected_result_refs=(control.result_ref,),
                    expected_attempt=0,
                    status="PARTIAL",
                    result_ref=barrier_ref,
                    replace_result_ref=True,
                )
                if not changed and not (
                    updated.status == "PARTIAL" and updated.result_ref == barrier_ref
                ):
                    raise self._conflict("Terminal cancel barrier lost the control-row CAS")
            return self._finish_terminal(
                c, control_operation_id=control.operation_id, evidence=evidence,
                barrier=barrier, closure=outcome, closure_kind="CONFIRMED_CANCEL",
                pre_status="IN_PROGRESS", fault_hook=fault_hook,
            )

    def close_human_adjudication(
        self,
        coordinates: RuntimeTranscriptionCoordinatesV1,
        decision: RuntimeTranscriptionAdjudicationDecisionV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        if type(coordinates) is not RuntimeTranscriptionCoordinatesV1:
            raise TypeError("coordinates must be RuntimeTranscriptionCoordinatesV1")
        return self._close_human_adjudication(
            coordinates, decision, fault_hook=fault_hook,
        )

    def close_human_adjudication_from_durable_coordinates(
        self,
        coordinates: RuntimeTranscriptionDurableControlCoordinatesV1,
        decision: RuntimeTranscriptionAdjudicationDecisionV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        if type(coordinates) is not RuntimeTranscriptionDurableControlCoordinatesV1:
            raise TypeError(
                "coordinates must be RuntimeTranscriptionDurableControlCoordinatesV1",
            )
        return self._close_human_adjudication(
            coordinates, decision, fault_hook=fault_hook,
        )

    def _close_human_adjudication(
        self,
        coordinates: _ControlCoordinates,
        decision: RuntimeTranscriptionAdjudicationDecisionV1,
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        c = coordinates
        if c.recovery_state != "ADJUDICATION_REQUIRED_NO_PUBLICATION":
            raise ValueError("Human closure requires the exact adjudication recovery state")
        checked = RuntimeTranscriptionAdjudicationDecisionV1.from_dict(decision.to_dict())
        if not self._record_binds(checked, c):
            raise ValueError("Human decision does not bind the exact runtime coordinate")
        with self._generation_exclusion_lock(c):
            self._require_lease(c)
            control = self._reserve_control(c)
            evidence = self._evidence(c)
            if control.status == "COMPLETED":
                return self._resume_completed(
                    c, control, evidence,
                    expected_closure_kind="HUMAN_ADJUDICATED_FAILED",
                    expected_closure_digest=checked.record_sha256,
                )
            if control.status == "PARTIAL":
                try:
                    barrier_digest = _typed_control_digest("commit-barrier", control.result_ref)
                except ValueError as exc:
                    raise self._conflict("Human control lacks its typed barrier") from exc
                barrier = evidence.load("commit-barrier", barrier_digest)
                stored = evidence.load("adjudication", barrier.closure_record_sha256)
                if stored.record_sha256 != checked.record_sha256:
                    raise self._conflict("A different Human decision owns the terminal barrier")
            else:
                self._require_active(c, status="PARTIAL")
                if control.status != "PENDING" or control.result_ref is not None:
                    raise self._conflict("Another path already owns control")
                evidence.write("adjudication", checked)
                barrier = RuntimeTranscriptionCommitBarrierV1.create(
                    runtime_operation_id=c.runtime_operation_id,
                    slot_operation_id=c.slot_operation_id,
                    source_asset_sha256=c.source_asset_sha256,
                    runtime_admission_ref=c.runtime_admission_ref,
                    expected_attempt=c.expected_attempt,
                    barrier_owner="TERMINAL_CLOSURE",
                    closure_record_sha256=checked.record_sha256,
                    acquired_at=self._now(),
                )
                evidence.write("commit-barrier", barrier)
                barrier_ref = _typed_control_ref("commit-barrier", barrier.record_sha256)
                updated, changed = self.store.compare_and_set_operation_status(
                    control.operation_id,
                    expected_statuses=("PENDING",),
                    expected_result_refs=(None,),
                    expected_attempt=0,
                    status="PARTIAL",
                    result_ref=barrier_ref,
                    replace_result_ref=True,
                )
                if not changed and not (
                    updated.status == "PARTIAL" and updated.result_ref == barrier_ref
                ):
                    raise self._conflict("Human terminal barrier lost the control-row CAS")
            return self._finish_terminal(
                c, control_operation_id=control.operation_id, evidence=evidence,
                barrier=barrier, closure=checked,
                closure_kind="HUMAN_ADJUDICATED_FAILED", pre_status="PARTIAL",
                fault_hook=fault_hook,
            )

    def _observe_generation(self, c: _ControlCoordinates) -> str:
        try:
            with _PinnedDirectory(self.output_directory.resolve(strict=True)) as output:
                if not output.child_exists(".task036-publications"):
                    output.assert_current()
                    return "EXACT_GENERATION_ABSENT"
                with output.pin_child(".task036-publications") as publications:
                    result = (
                        "PRESENT_PARTIAL_OR_UNKNOWN"
                        if publications.child_exists(c.runtime_operation_id)
                        else "EXACT_GENERATION_ABSENT"
                    )
                    publications.assert_current()
                    output.assert_current()
                    return result
        except (OSError, ProductError, ValueError):
            return "PRESENT_PARTIAL_OR_UNKNOWN"

    def _finish_terminal(
        self,
        c: _ControlCoordinates,
        *,
        control_operation_id: str,
        evidence: _ControlEvidenceStore,
        barrier: RuntimeTranscriptionCommitBarrierV1,
        closure: RuntimeTranscriptionCancelOutcomeV1 | RuntimeTranscriptionAdjudicationDecisionV1,
        closure_kind: str,
        pre_status: str,
        fault_hook: Callable[[str], None] | None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        if (
            not self._record_binds(barrier, c)
            or not self._record_binds(closure, c)
            or barrier.barrier_owner != "TERMINAL_CLOSURE"
            or barrier.closure_record_sha256 != closure.record_sha256
        ):
            raise self._conflict("Terminal barrier chain is invalid")
        if fault_hook is not None:
            fault_hook("after_terminal_barrier")

        observed = self._observe_generation(c)
        if fault_hook is not None:
            fault_hook("after_first_generation_observation")
        observed_again = self._observe_generation(c)
        final_observation = (
            "EXACT_GENERATION_ABSENT"
            if observed == observed_again == "EXACT_GENERATION_ABSENT"
            else "PRESENT_PARTIAL_OR_UNKNOWN"
        )
        existing_observation = evidence.load_anchor(
            "generation-absence", "generation-absence.json",
        )
        if existing_observation is None:
            observation = RuntimeTranscriptionGenerationAbsenceObservationV1.create(
                runtime_operation_id=c.runtime_operation_id,
                slot_operation_id=c.slot_operation_id,
                source_asset_sha256=c.source_asset_sha256,
                runtime_admission_ref=c.runtime_admission_ref,
                expected_attempt=c.expected_attempt,
                commit_barrier_sha256=barrier.record_sha256,
                observation=final_observation,
                observed_at=self._now(),
            )
            evidence.write(
                "generation-absence", observation, anchor="generation-absence.json",
            )
        else:
            observation = existing_observation
        if (
            not self._record_binds(observation, c)
            or observation.commit_barrier_sha256 != barrier.record_sha256
            or observation.observation != "EXACT_GENERATION_ABSENT"
            or final_observation != "EXACT_GENERATION_ABSENT"
        ):
            raise self._conflict("Exact generation absence was not proven")
        if fault_hook is not None:
            fault_hook("after_generation_observation")

        barrier_ref = _typed_control_ref("commit-barrier", barrier.record_sha256)
        self._require_control(
            c, control_operation_id, status="PARTIAL", result_ref=barrier_ref,
        )

        terminal_ref = (
            "task098-runtime-cancelled:v1:"
            if closure_kind == "CONFIRMED_CANCEL"
            else "task098-runtime-adjudicated-failed:v1:"
        ) + closure.record_sha256.removeprefix("sha256:")
        self._require_lease(c)
        self._require_slot(c, statuses=("IN_PROGRESS",))
        main = self.store.get_operation(c.runtime_operation_id)
        if main.status == pre_status and main.result_ref == c.runtime_admission_ref:
            self._require_main(
                c, statuses=(pre_status,), result_refs=(c.runtime_admission_ref,),
            )
            main, changed = self.store.compare_and_set_operation_status(
                c.runtime_operation_id,
                expected_statuses=(pre_status,),
                expected_result_refs=(c.runtime_admission_ref,),
                expected_attempt=c.expected_attempt,
                status="FAILED",
                last_error_code="ERR_TASK098_RUNTIME_CANCELLED" if closure_kind == "CONFIRMED_CANCEL" else "ERR_TASK098_RUNTIME_ADJUDICATED_FAILED",
                result_ref=terminal_ref,
                replace_result_ref=True,
            )
            if not changed:
                raise self._conflict("Main terminal CAS lost or attempt changed")
        elif not (
            main.status == "FAILED"
            and main.attempt == c.expected_attempt
            and main.result_ref == terminal_ref
        ):
            raise self._conflict("Main operation is not at the exact resumable state")
        if fault_hook is not None:
            fault_hook("after_main_cas")

        self._require_lease(c)
        self._require_main(c, statuses=("FAILED",), result_refs=(terminal_ref,))
        self._require_slot(c, statuses=("IN_PROGRESS",))
        self._require_control(
            c, control_operation_id, status="PARTIAL", result_ref=barrier_ref,
        )

        existing_commit = evidence.load_anchor("terminal-commit", "terminal-commit.json")
        if existing_commit is None:
            commit = RuntimeTranscriptionTerminalClosureCommitV1.create(
                runtime_operation_id=c.runtime_operation_id,
                slot_operation_id=c.slot_operation_id,
                source_asset_sha256=c.source_asset_sha256,
                prior_runtime_admission_ref=c.runtime_admission_ref,
                expected_attempt=c.expected_attempt,
                closure_kind=closure_kind,
                closure_record_sha256=closure.record_sha256,
                commit_barrier_sha256=barrier.record_sha256,
                generation_absence_observation_sha256=observation.record_sha256,
                terminal_result_ref=terminal_ref,
                committed_at=self._now(),
            )
            evidence.write("terminal-commit", commit, anchor="terminal-commit.json")
        else:
            commit = existing_commit
        if (
            not self._record_binds(commit, c)
            or commit.closure_kind != closure_kind
            or commit.closure_record_sha256 != closure.record_sha256
            or commit.commit_barrier_sha256 != barrier.record_sha256
            or commit.generation_absence_observation_sha256 != observation.record_sha256
            or commit.terminal_result_ref != terminal_ref
        ):
            raise self._conflict("Terminal commit chain is invalid")
        if fault_hook is not None:
            fault_hook("after_terminal_commit_write")

        self._require_lease(c)
        self._require_main(c, statuses=("FAILED",), result_refs=(terminal_ref,))
        self._require_slot(c, statuses=("IN_PROGRESS",))
        self._require_control(
            c, control_operation_id, status="PARTIAL", result_ref=barrier_ref,
        )

        commit_ref = _typed_control_ref("terminal-commit", commit.record_sha256)
        control = self.store.get_operation(control_operation_id)
        if control.status == "PARTIAL" and control.result_ref == barrier_ref:
            control, changed = self.store.compare_and_set_operation_status(
                control_operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(barrier_ref,),
                expected_attempt=0,
                status="COMPLETED",
                result_ref=commit_ref,
                replace_result_ref=True,
            )
            if not changed:
                raise self._conflict("Terminal commit lost the control-row CAS")
        elif not (
            control.status == "COMPLETED"
            and control.attempt == 0
            and control.result_ref == commit_ref
        ):
            raise self._conflict("Control row is not at the exact resumable state")
        if fault_hook is not None:
            fault_hook("after_control_commit")

        self._require_lease(c)
        self._require_main(c, statuses=("FAILED",), result_refs=(terminal_ref,))
        self._require_control(
            c, control_operation_id, status="COMPLETED", result_ref=commit_ref,
        )
        slot = self._require_slot(c, statuses=("IN_PROGRESS", "PENDING"))
        if slot.status == "IN_PROGRESS":
            released, changed = self.store.compare_and_set_operation_status(
                slot.operation_id,
                expected_statuses=("IN_PROGRESS",),
                expected_result_refs=(c.runtime_operation_id,),
                expected_attempt=slot.attempt,
                status="PENDING",
                result_ref=c.runtime_operation_id,
                replace_result_ref=True,
            )
            if not changed or released.status != "PENDING":
                raise self._conflict("Output-slot release lost its exact CAS")
        if fault_hook is not None:
            fault_hook("after_slot_release")
        return commit

    def _resume_completed(
        self,
        c: _ControlCoordinates,
        control: OperationRecord,
        evidence: _ControlEvidenceStore,
        *,
        expected_closure_kind: str,
        expected_closure_digest: str | None = None,
    ) -> RuntimeTranscriptionTerminalClosureCommitV1:
        if control.result_ref is None:
            raise self._conflict("Completed control row has no terminal commit")
        try:
            commit_digest = _typed_control_digest("terminal-commit", control.result_ref)
        except ValueError as exc:
            raise self._conflict("Completed control row has an invalid terminal commit ref") from exc
        commit = evidence.load("terminal-commit", commit_digest)
        anchor = evidence.load_anchor("terminal-commit", "terminal-commit.json")
        if (
            anchor is None
            or anchor.record_sha256 != commit.record_sha256
            or not self._record_binds(commit, c)
            or commit.closure_kind != expected_closure_kind
        ):
            raise self._conflict("Completed control row lacks its exact commit anchor")
        barrier = evidence.load("commit-barrier", commit.commit_barrier_sha256)
        observation = evidence.load_anchor("generation-absence", "generation-absence.json")
        closure_kind = (
            "cancel-outcome"
            if commit.closure_kind == "CONFIRMED_CANCEL"
            else "adjudication"
        )
        closure = evidence.load(closure_kind, commit.closure_record_sha256)
        if (
            observation is None
            or not self._record_binds(barrier, c)
            or not self._record_binds(observation, c)
            or not self._record_binds(closure, c)
            or barrier.barrier_owner != "TERMINAL_CLOSURE"
            or barrier.closure_record_sha256 != closure.record_sha256
            or observation.commit_barrier_sha256 != barrier.record_sha256
            or observation.record_sha256 != commit.generation_absence_observation_sha256
            or observation.observation != "EXACT_GENERATION_ABSENT"
            or commit.closure_record_sha256 != closure.record_sha256
            or (
                expected_closure_digest is not None
                and closure.record_sha256 != expected_closure_digest
            )
        ):
            raise self._conflict("Completed terminal Evidence chain is invalid")
        self._require_lease(c)
        self._require_main(c, statuses=("FAILED",), result_refs=(commit.terminal_result_ref,))
        self._require_control(
            c,
            control.operation_id,
            status="COMPLETED",
            result_ref=_typed_control_ref("terminal-commit", commit.record_sha256),
        )
        slot = self._require_slot(c, statuses=("IN_PROGRESS", "PENDING"))
        if slot.status == "IN_PROGRESS":
            released, changed = self.store.compare_and_set_operation_status(
                slot.operation_id,
                expected_statuses=("IN_PROGRESS",),
                expected_result_refs=(c.runtime_operation_id,),
                expected_attempt=slot.attempt,
                status="PENDING",
                result_ref=c.runtime_operation_id,
                replace_result_ref=True,
            )
            if not changed or released.status != "PENDING":
                raise self._conflict("Completed closure could not resume exact slot release")
        return commit


__all__ = [
    "RuntimeTranscriptionCoordinatesV1",
    "RuntimeTranscriptionDurableControlCoordinatesV1",
    "RuntimeTranscriptionCoordinatorV1",
    "derive_control_key",
    "derive_cross_version_guard_key",
    "derive_output_slot_key",
    "derive_runtime_operation_key_v2",
]
