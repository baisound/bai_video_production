"""TASK-059 P1C-H Python-local native PPK Operator adapter.

Selected paths and file bodies stay outside WebView. The secret backend writes
UTF-8 directly into a caller-owned mutable buffer; passphrases are never API
strings or immutable bytes. P0 still owns preflight, P1C-E owns the helper
session, and TASK-029 R9B owns custody.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import time
from typing import Callable, Protocol

from .owner_signing_key_ppk_custody_import import PpkCustodyImportResult
from .owner_signing_key_ppk_operator_session import (
    PpkImportOperatorError,
    PpkImportOperatorSession,
)
from .owner_signing_key_ppk_preflight import (
    MAX_PPK_BYTES,
    MAX_PUBLIC_KEY_FILE_BYTES,
    inspect_ppk_import_preflight,
)
from .owner_signing_key_ppk_process_controller import packaged_ppk_helper_launch_spec


MAX_PASSPHRASE_UTF8_BYTES = 1024
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_READ_CHUNK_BYTES = 16 * 1024


class PpkNativeOperatorError(RuntimeError):
    """Body-free native adapter failure carrying only a fixed code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"PpkNativeOperatorError(code={self.code!r})"


class PpkNativeDialogBackend(Protocol):
    """Toolkit boundary implemented by the Windows-native unit."""

    def choose_encrypted_ppk(self) -> str | None: ...

    def choose_rfc4716_public_key(self) -> str | None: ...

    def read_passphrase_utf8(
        self, destination: bytearray, *, maximum_bytes: int
    ) -> int | None:
        """Write into destination and return byte count, or None on Cancel."""


@dataclass(frozen=True, slots=True, repr=False)
class PpkNativeCandidateView:
    candidate_id: str
    preflight_sha256: str
    ppk_file_sha256: str
    public_key_file_sha256: str
    signer_key_id_sha256: str
    openssh_sha256_fingerprint: str
    ppk_format_version: int
    algorithm: str
    encryption: str
    key_derivation: str
    state: str = "FILES_SELECTED_PUBLIC_CANDIDATE"

    def to_ui_dict(self) -> dict[str, object]:
        return {
            "adapter_version": "1.0.0",
            "task_owner": "TASK-059",
            **{name: getattr(self, name) for name in self.__dataclass_fields__},
            "selected_paths_exposed": False,
            "file_bodies_exposed": False,
            "passphrase_received": False,
            "custody_import_started": False,
            "signing_started": False,
        }

    def __repr__(self) -> str:
        return (
            "PpkNativeCandidateView("
            f"candidate_id={self.candidate_id!r}, state={self.state!r}, "
            f"fingerprint={self.openssh_sha256_fingerprint!r})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class PpkNativeReadyView:
    attempt_id: str
    openssh_sha256_fingerprint: str
    expires_at_epoch_ms: int
    state: str = "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT"

    def to_ui_dict(self) -> dict[str, object]:
        return {
            "adapter_version": "1.0.0",
            "task_owner": "TASK-059",
            **{name: getattr(self, name) for name in self.__dataclass_fields__},
            "selected_paths_exposed": False,
            "file_bodies_exposed": False,
            "passphrase_exposed": False,
            "custody_import_started": False,
            "signing_started": False,
        }

    def __repr__(self) -> str:
        return (
            "PpkNativeReadyView("
            f"attempt_id={self.attempt_id!r}, state={self.state!r}, "
            f"fingerprint={self.openssh_sha256_fingerprint!r})"
        )


@dataclass(slots=True, repr=False)
class _Candidate:
    view: PpkNativeCandidateView
    ppk_path: str
    public_key_path: str
    preflight_payload: dict[str, object]
    public_identity_confirmed: bool = False


@dataclass(slots=True, repr=False)
class _ActiveAttempt:
    attempt_id: str
    session: PpkImportOperatorSession


def _clear(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


def _valid_utf8(value: bytearray, length: int) -> bool:
    """Strict UTF-8 validation without making an immutable secret copy."""

    index = 0
    while index < length:
        first = value[index]
        if first <= 0x7F:
            index += 1
            continue
        if 0xC2 <= first <= 0xDF:
            required, lower, upper = 1, None, None
        elif 0xE0 <= first <= 0xEF:
            required = 2
            lower = 0xA0 if first == 0xE0 else None
            upper = 0x9F if first == 0xED else None
        elif 0xF0 <= first <= 0xF4:
            required = 3
            lower = 0x90 if first == 0xF0 else None
            upper = 0x8F if first == 0xF4 else None
        else:
            return False
        if index + required >= length:
            return False
        second = value[index + 1]
        if not 0x80 <= second <= 0xBF:
            return False
        if lower is not None and second < lower:
            return False
        if upper is not None and second > upper:
            return False
        if any(
            not 0x80 <= value[index + offset] <= 0xBF
            for offset in range(2, required + 1)
        ):
            return False
        index += required + 1
    return True


def _read_bounded_regular_file(
    path_text: str, *, maximum_bytes: int, required_suffix: str
) -> bytearray:
    if (
        not isinstance(path_text, str)
        or not path_text
        or any(character in path_text for character in ("\x00", "\r", "\n"))
    ):
        raise PpkNativeOperatorError("ERR_PPK_NATIVE_FILE_SELECTION_INVALID")
    path = Path(path_text)
    if not path.is_absolute() or path.suffix.casefold() != required_suffix:
        raise PpkNativeOperatorError("ERR_PPK_NATIVE_FILE_SELECTION_INVALID")

    stream = None
    result = bytearray()
    try:
        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISREG(path_stat.st_mode):
            raise OSError
        stream = path.open("rb", buffering=0)
        before = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size < 1
            or before.st_size > maximum_bytes
        ):
            raise OSError
        coordinates = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(
            getattr(path_stat, name) != getattr(before, name)
            for name in coordinates
        ):
            raise OSError

        result = bytearray(before.st_size)
        view = memoryview(result)
        offset = 0
        try:
            while offset < len(result):
                count = stream.readinto(view[offset : offset + _READ_CHUNK_BYTES])
                if count is None or count <= 0:
                    break
                offset += count
        finally:
            view.release()
        after = os.fstat(stream.fileno())
        if offset != len(result) or any(
            getattr(before, name) != getattr(after, name) for name in coordinates
        ):
            raise OSError
        return result
    except (OSError, ValueError):
        _clear(result)
        raise PpkNativeOperatorError(
            "ERR_PPK_NATIVE_FILE_SELECTION_INVALID"
        ) from None
    finally:
        if stream is not None:
            stream.close()


def _default_session_factory() -> PpkImportOperatorSession:
    return PpkImportOperatorSession(helper_spec=packaged_ppk_helper_launch_spec())

def _default_helper_availability_probe() -> None:
    packaged_ppk_helper_launch_spec().verify_identity()



class PpkNativeOperatorAdapter:
    """One-candidate/one-attempt adapter with no secret WebView route."""

    def __init__(
        self,
        *,
        dialog_backend: PpkNativeDialogBackend,
        identity: Callable[[str], str],
        session_factory: Callable[[], PpkImportOperatorSession] = (
            _default_session_factory
        ),
        helper_availability_probe: Callable[[], None] = (
            _default_helper_availability_probe
        ),
        epoch_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
    ) -> None:
        self._dialog_backend = dialog_backend
        self._session_factory = session_factory
        self._helper_availability_probe = helper_availability_probe
        self._epoch_ms = epoch_ms
        self._identity = identity
        self._candidate: _Candidate | None = None
        self._active: _ActiveAttempt | None = None

    def __repr__(self) -> str:
        candidate_state = self._candidate.view.state if self._candidate else None
        attempt_state = (
            "READY_FOR_EXPLICIT_HUMAN_CUSTODY_IMPORT" if self._active else None
        )
        return (
            "PpkNativeOperatorAdapter("
            f"candidate_state={candidate_state!r}, attempt_state={attempt_state!r})"
        )

    def choose_files(
        self, *, expected_openssh_sha256_fingerprint: str
    ) -> PpkNativeCandidateView | None:
        if self._active is not None:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ATTEMPT_ALREADY_ACTIVE")
        self._require_helper_available()
        self._candidate = None
        try:
            ppk_path = self._dialog_backend.choose_encrypted_ppk()
            if ppk_path is None:
                return None
            public_key_path = self._dialog_backend.choose_rfc4716_public_key()
            if public_key_path is None:
                return None
        except Exception:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_DIALOG_UNAVAILABLE") from None

        ppk, public_key = bytearray(), bytearray()
        try:
            ppk = _read_bounded_regular_file(
                ppk_path, maximum_bytes=MAX_PPK_BYTES, required_suffix=".ppk"
            )
            public_key = _read_bounded_regular_file(
                public_key_path,
                maximum_bytes=MAX_PUBLIC_KEY_FILE_BYTES,
                required_suffix=".pub",
            )
            preflight = inspect_ppk_import_preflight(
                bytes(ppk),
                bytes(public_key),
                expected_openssh_sha256_fingerprint=(
                    expected_openssh_sha256_fingerprint
                ),
                observed_at_epoch_ms=self._safe_epoch_ms(),
            )
            payload = preflight.to_dict()
            view = PpkNativeCandidateView(
                candidate_id=self._safe_identity("candidate"),
                preflight_sha256=str(payload["preflight_sha256"]),
                ppk_file_sha256=preflight.ppk_file_sha256,
                public_key_file_sha256=preflight.public_key_file_sha256,
                signer_key_id_sha256=preflight.signer_key_id_sha256,
                openssh_sha256_fingerprint=preflight.openssh_sha256_fingerprint,
                ppk_format_version=preflight.ppk_format_version,
                algorithm=preflight.algorithm,
                encryption=preflight.encryption,
                key_derivation=preflight.key_derivation,
            )
            self._candidate = _Candidate(
                view=view,
                ppk_path=ppk_path,
                public_key_path=public_key_path,
                preflight_payload=payload,
            )
            return view
        except PpkNativeOperatorError:
            raise
        except Exception:
            raise PpkNativeOperatorError(
                "ERR_PPK_NATIVE_PUBLIC_PREFLIGHT_FAILED"
            ) from None
        finally:
            _clear(ppk)
            _clear(public_key)

    def confirm_public_identity(
        self, *, candidate_id: str, explicit_human_confirmation: bool
    ) -> PpkNativeCandidateView:
        candidate = self._require_candidate(candidate_id)
        if explicit_human_confirmation is not True:
            raise PpkNativeOperatorError(
                "ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED"
            )
        candidate.public_identity_confirmed = True
        return candidate.view

    def open_secret_dialog(
        self,
        *,
        candidate_id: str,
        owner_scope_sha256: str,
        destination_path: str,
    ) -> PpkNativeReadyView | None:
        if self._active is not None:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ATTEMPT_ALREADY_ACTIVE")
        candidate = self._require_candidate(candidate_id)
        if not candidate.public_identity_confirmed:
            raise PpkNativeOperatorError(
                "ERR_PPK_NATIVE_PUBLIC_CONFIRMATION_REQUIRED"
            )
        self._require_helper_available()

        passphrase = bytearray(MAX_PASSPHRASE_UTF8_BYTES)
        ppk, public_key = bytearray(), bytearray()
        session: PpkImportOperatorSession | None = None
        succeeded = False
        try:
            try:
                length = self._dialog_backend.read_passphrase_utf8(
                    passphrase, maximum_bytes=MAX_PASSPHRASE_UTF8_BYTES
                )
            except Exception:
                raise PpkNativeOperatorError(
                    "ERR_PPK_NATIVE_SECRET_DIALOG_UNAVAILABLE"
                ) from None
            if length is None:
                self._candidate = None
                return None
            if (
                isinstance(length, bool)
                or not isinstance(length, int)
                or not 1 <= length <= MAX_PASSPHRASE_UTF8_BYTES
                or any(
                    passphrase[index] == 0 for index in range(length)
                )
                or any(
                    passphrase[index] != 0
                    for index in range(length, len(passphrase))
                )
                or not _valid_utf8(passphrase, length)
            ):
                raise PpkNativeOperatorError("ERR_PPK_NATIVE_SECRET_INPUT_INVALID")
            del passphrase[length:]

            ppk = _read_bounded_regular_file(
                candidate.ppk_path,
                maximum_bytes=MAX_PPK_BYTES,
                required_suffix=".ppk",
            )
            public_key = _read_bounded_regular_file(
                candidate.public_key_path,
                maximum_bytes=MAX_PUBLIC_KEY_FILE_BYTES,
                required_suffix=".pub",
            )
            expected = candidate.preflight_payload
            current = inspect_ppk_import_preflight(
                bytes(ppk),
                bytes(public_key),
                expected_openssh_sha256_fingerprint=(
                    candidate.view.openssh_sha256_fingerprint
                ),
                observed_at_epoch_ms=int(expected["observed_at_epoch_ms"]),
            ).to_dict()
            if current != expected:
                raise PpkNativeOperatorError("ERR_PPK_NATIVE_FILE_IDENTITY_CHANGED")

            attempt_id = self._safe_identity("attempt")
            try:
                session = self._session_factory()
            except Exception:
                raise PpkNativeOperatorError(
                    "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
                ) from None
            ready = session.begin(
                preflight_payload=expected,
                ppk_document=ppk,
                rfc4716_public_key=public_key,
                passphrase_utf8=passphrase,
                owner_scope_sha256=owner_scope_sha256,
                destination_path=destination_path,
            )
            self._active = _ActiveAttempt(attempt_id, session)
            self._candidate = None
            succeeded = True
            return PpkNativeReadyView(
                attempt_id=attempt_id,
                openssh_sha256_fingerprint=ready.openssh_sha256_fingerprint,
                expires_at_epoch_ms=ready.expires_at_epoch_ms,
            )
        except PpkNativeOperatorError:
            raise
        except PpkImportOperatorError as exc:
            raise PpkNativeOperatorError(exc.code) from None
        except Exception:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ADAPTER_FAILED") from None
        finally:
            _clear(passphrase)
            _clear(ppk)
            _clear(public_key)
            if not succeeded:
                self._candidate = None
                if session is not None:
                    session.close()

    def confirm_ready(
        self, *, attempt_id: str, explicit_human_confirmation: bool
    ) -> PpkCustodyImportResult:
        active = self._require_active(attempt_id)
        if explicit_human_confirmation is not True:
            raise PpkNativeOperatorError(
                "ERR_PPK_CUSTODY_IMPORT_CONFIRMATION_REQUIRED"
            )
        try:
            result = active.session.confirm(explicit_human_confirmation=True)
            self._active = None
            return result
        except PpkImportOperatorError as exc:
            self._active = None
            raise PpkNativeOperatorError(exc.code) from None
        except Exception:
            self._active = None
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ADAPTER_FAILED") from None

    def cancel_candidate(self, *, candidate_id: str) -> None:
        self._require_candidate(candidate_id)
        self._candidate = None

    def cancel_ready(self, *, attempt_id: str) -> None:
        active = self._require_active(attempt_id)
        try:
            active.session.cancel()
        except PpkImportOperatorError as exc:
            raise PpkNativeOperatorError(exc.code) from None
        except Exception:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ADAPTER_FAILED") from None
        finally:
            self._active = None

    def close(self) -> None:
        self._candidate = None
        active, self._active = self._active, None
        if active is not None:
            active.session.close()

    def _require_helper_available(self) -> None:
        try:
            self._helper_availability_probe()
        except Exception:
            raise PpkNativeOperatorError(
                "ERR_PPK_PACKAGED_HELPER_UNAVAILABLE"
            ) from None

    def _require_candidate(self, candidate_id: str) -> _Candidate:
        candidate = self._candidate
        if (
            candidate is None
            or not isinstance(candidate_id, str)
            or candidate.view.candidate_id != candidate_id
        ):
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_CANDIDATE_NOT_FOUND")
        return candidate

    def _require_active(self, attempt_id: str) -> _ActiveAttempt:
        active = self._active
        if (
            active is None
            or not isinstance(attempt_id, str)
            or active.attempt_id != attempt_id
        ):
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ATTEMPT_NOT_READY")
        return active

    def _safe_epoch_ms(self) -> int:
        value = self._epoch_ms()
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ADAPTER_FAILED")
        return value

    def _safe_identity(self, kind: str) -> str:
        value = self._identity(kind)
        if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
            raise PpkNativeOperatorError("ERR_PPK_NATIVE_ADAPTER_FAILED")
        return value


__all__ = [
    "MAX_PASSPHRASE_UTF8_BYTES",
    "PpkNativeCandidateView",
    "PpkNativeDialogBackend",
    "PpkNativeOperatorAdapter",
    "PpkNativeOperatorError",
    "PpkNativeReadyView",
]
