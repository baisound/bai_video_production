"""Pure immutable-bytes parser for the exact TASK-014 Qwen-TTS wheel.

The module owns no path, filesystem, process, import, install, extraction, or
network operation. Its parser accepts immutable bytes and validates the one
production pin plus the complete ZIP/RECORD contract.
"""

from __future__ import annotations

import base64
import binascii
import csv
from dataclasses import dataclass
import io
from pathlib import PurePosixPath
import stat
from types import MappingProxyType
from typing import Mapping
import zipfile

from .serialization import canonical_json_bytes, sha256_bytes


_WHEEL_BYTES = 113_529
_WHEEL_SHA256 = "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d"
_TRUSTED_PAYLOAD_INVENTORY_SHA256 = "sha256:0a0568dfbbf716135c911322c22dc44df1e279dfd52ab25de9a4edb6a8a11dd6"
_DIST_INFO = "qwen_tts-0.1.1.dist-info"
_MAX_MEMBERS = 128
_MAX_EXPANDED_BYTES = 4 * 1024 * 1024
_MAX_RECORD_BYTES = 128 * 1024
_MAX_RECORD_FIELD_BYTES = 4096
_SHA_B64_PREFIX = "sha256="
_EXPECTED_ENTRY_POINTS = b"[console_scripts]\nqwen-tts-demo = qwen_tts.cli.demo:main\n"


class PinnedWheelError(Exception):
    """A closed, body-free reason suitable for a caller's receipt."""


@dataclass(frozen=True, slots=True)
class PinnedQwenTtsWheel:
    """Verified wheel records and immutable copies of the trusted payload."""

    payload: Mapping[str, bytes]
    record: Mapping[str, tuple[str | None, int | None]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "record", MappingProxyType(dict(self.record)))

    @property
    def trusted_inventory(self) -> Mapping[str, tuple[str, int]]:
        return MappingProxyType({name: (sha256_bytes(body), len(body)) for name, body in self.payload.items()})


def _fail(reason: str) -> None:
    raise PinnedWheelError(reason)


def _safe_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        _fail("UNSAFE_ARCHIVE_PATH")
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        _fail("UNSAFE_ARCHIVE_PATH")
    if any(ord(char) < 33 or ord(char) > 126 for char in name):
        _fail("UNSAFE_ARCHIVE_PATH")
    path = PurePosixPath(name)
    if path.is_absolute() or path.name in {"", ".", ".."} or any(part in {"", ".", ".."} for part in path.parts):
        _fail("UNSAFE_ARCHIVE_PATH")
    # Windows aliases must not be admitted even though this parser has POSIX
    # archive notation.  A materialized tree is Windows-only.
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(part.rstrip(". ").upper() in reserved or part.endswith((".", " ")) for part in path.parts):
        _fail("UNSAFE_ARCHIVE_PATH")
    return name


def _parse_record(raw: bytes) -> dict[str, tuple[str | None, int | None]]:
    """Parse a bounded RECORD without accepting alternate traversal spellings."""
    if len(raw) > _MAX_RECORD_BYTES:
        _fail("MALFORMED_RECORD")
    try:
        rows = csv.reader(io.StringIO(raw.decode("utf-8", "strict"), newline=""))
        result: dict[str, tuple[str | None, int | None]] = {}
        casefolded: set[str] = set()
        for count, row in enumerate(rows, start=1):
            if count > _MAX_MEMBERS or len(row) != 3 or any(len(field.encode("utf-8")) > _MAX_RECORD_FIELD_BYTES for field in row):
                _fail("MALFORMED_RECORD")
            name = _safe_member(row[0])
            if name in result or name.casefold() in casefolded:
                _fail("DUPLICATE_RECORD_PATH")
            casefolded.add(name.casefold())
            encoded_hash, raw_size = row[1], row[2]
            if not encoded_hash and not raw_size:
                result[name] = (None, None)
                continue
            if not encoded_hash.startswith(_SHA_B64_PREFIX) or not raw_size or not raw_size.isascii() or not raw_size.isdecimal():
                _fail("MALFORMED_RECORD")
            encoded = encoded_hash.removeprefix(_SHA_B64_PREFIX)
            try:
                decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            except (ValueError, binascii.Error):
                _fail("MALFORMED_RECORD")
            if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
                _fail("MALFORMED_RECORD")
            if (len(raw_size) > 1 and raw_size.startswith("0")) or int(raw_size) > _MAX_EXPANDED_BYTES:
                _fail("MALFORMED_RECORD")
            result[name] = ("sha256:" + decoded.hex(), int(raw_size))
    except (UnicodeDecodeError, csv.Error, OverflowError):
        _fail("MALFORMED_RECORD")
    if not result:
        _fail("MALFORMED_RECORD")
    return result


def parse_pinned_qwen_tts_011_wheel(raw: bytes) -> PinnedQwenTtsWheel:
    """Parse only the production-pinned immutable wheel byte sequence."""
    if type(raw) is not bytes or len(raw) != _WHEEL_BYTES or sha256_bytes(raw) != _WHEEL_SHA256:
        _fail("WHEEL_PIN_MISMATCH")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= _MAX_MEMBERS or any(item.file_size < 0 or item.compress_size < 0 for item in infos) or sum(item.file_size for item in infos) > _MAX_EXPANDED_BYTES:
                _fail("ARCHIVE_BOUNDS_EXCEEDED")
            names: set[str] = set()
            casefolded: set[str] = set()
            bodies: dict[str, bytes] = {}
            for info in infos:
                name = _safe_member(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if (info.flag_bits & 0x1) or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED} or info.is_dir() or mode in {stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK}:
                    _fail("UNSAFE_ARCHIVE_MEMBER")
                if name in names or name.casefold() in casefolded:
                    _fail("DUPLICATE_ARCHIVE_MEMBER")
                names.add(name); casefolded.add(name.casefold())
                with archive.open(info, "r") as member:
                    chunks: list[bytes] = []
                    total = 0
                    while chunk := member.read(64 * 1024):
                        total += len(chunk)
                        if total > info.file_size or total > _MAX_EXPANDED_BYTES:
                            _fail("ARCHIVE_BOUNDS_EXCEEDED")
                        chunks.append(chunk)
                body = b"".join(chunks)
                if len(body) != info.file_size:
                    _fail("ARCHIVE_MEMBER_SIZE_MISMATCH")
                bodies[name] = body
    except PinnedWheelError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise PinnedWheelError("INVALID_WHEEL_ARCHIVE") from exc
    record_name = f"{_DIST_INFO}/RECORD"
    if record_name not in bodies:
        _fail("WHEEL_RECORD_MISSING")
    record = _parse_record(bodies[record_name])
    if set(record) != set(bodies) or record.get(record_name) != (None, None):
        _fail("WHEEL_RECORD_MEMBER_SET_MISMATCH")
    for name, expected in record.items():
        if name == record_name:
            continue
        actual = (sha256_bytes(bodies[name]), len(bodies[name]))
        if actual != expected:
            _fail("WHEEL_RECORD_HASH_MISMATCH")
    payload = {name: body for name, body in bodies.items() if name != record_name}
    if len(bodies) != 24 or len(payload) != 23 or sum(name.endswith(".py") for name in payload) != 17:
        _fail("WHEEL_OBSERVED_COUNT_MISMATCH")
    if bodies.get(f"{_DIST_INFO}/entry_points.txt") != _EXPECTED_ENTRY_POINTS:
        _fail("WHEEL_ENTRY_POINT_MISMATCH")
    inventory = {name: (sha256_bytes(body), len(body)) for name, body in payload.items()}
    if sha256_bytes(canonical_json_bytes(inventory)) != _TRUSTED_PAYLOAD_INVENTORY_SHA256:
        _fail("TRUSTED_PAYLOAD_INVENTORY_MISMATCH")
    return PinnedQwenTtsWheel(payload=payload, record=record)
