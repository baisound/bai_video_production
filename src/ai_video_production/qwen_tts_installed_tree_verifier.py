"""Bounded, non-atomic read observation for the pinned Qwen-TTS 0.1.1 wheel.

This module deliberately has no install, import, subprocess, extraction, network,
or target-Python execution surface.  It observes a mutable installed tree using
lstat/open/fstat guarded streaming reads; it does not create an immutable
snapshot, verifier-origin proof, runtime authenticity, or reuse authority.
"""

from __future__ import annotations

import base64
import binascii
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping
import zipfile
from urllib.parse import urlsplit

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


SCHEMA_ID = "bai.task014.qwen-tts-payload-read-observation.v1"
SCOPE = "BOUNDED_NONATOMIC_WHEEL_PAYLOAD_OBSERVATION_ONLY"
WHEEL_FILENAME = "qwen_tts-0.1.1-py3-none-any.whl"
WHEEL_BYTES = 113_529
WHEEL_SHA256 = "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d"
TRUSTED_PAYLOAD_INVENTORY_SHA256 = "sha256:0a0568dfbbf716135c911322c22dc44df1e279dfd52ab25de9a4edb6a8a11dd6"
DIST_INFO = "qwen_tts-0.1.1.dist-info"
PACKAGE = "qwen_tts"
MAX_MEMBERS = 128
MAX_EXPANDED_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 128 * 1024
MAX_RECORD_FIELD_BYTES = 4096
DRIVE_FIXED = 3
_SHA_B64 = re.compile(r"^sha256=([A-Za-z0-9_-]+)$")
_DRIVE = re.compile(r"^[A-Za-z]:$")
_RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")
_UNKNOWN_REASONS = frozenset({"IO_UNAVAILABLE"})
_BLOCKER_REASONS = frozenset({
    "UNSAFE_RUNTIME_ROOT", "REPARSE_OR_NONREGULAR_FILE", "REPARSE_OR_NON_DIRECTORY",
    "MISSING_INSTALLED_TREE", "FILE_RACE_DETECTED", "UNSAFE_ARCHIVE_PATH",
    "MALFORMED_RECORD", "DUPLICATE_RECORD_PATH", "WHEEL_PIN_MISMATCH",
    "ARCHIVE_BOUNDS_EXCEEDED", "UNSAFE_ARCHIVE_MEMBER", "ARCHIVE_MEMBER_SIZE_MISMATCH",
    "WHEEL_RECORD_MISSING", "INVALID_WHEEL_ARCHIVE", "WHEEL_RECORD_MEMBER_SET_MISMATCH",
    "WHEEL_RECORD_HASH_MISMATCH", "WHEEL_LAYOUT_MISMATCH", "INSTALLED_INVENTORY_BOUNDS_EXCEEDED",
    "INSTALLED_TREE_EXTRA_MISSING_OR_CASE_MISMATCH", "INSTALLED_TREE_TYPE_MISMATCH",
    "INSTALLED_RECORD_MEMBER_SET_MISMATCH", "INSTALLED_RECORD_SELF_ROW_INVALID",
    "INSTALLED_RECORD_TRUSTED_ROW_MISMATCH", "INSTALLED_RECORD_GENERATED_ROW_INVALID",
    "WHEEL_OBSERVED_COUNT_MISMATCH", "WHEEL_ENTRY_POINT_MISSING", "WHEEL_ENTRY_POINT_MISMATCH",
    "INSTALLED_TRUSTED_BODY_MISMATCH", "INSTALLED_GENERATED_BODY_MISMATCH",
    "DIRECT_URL_JSON_INVALID", "CONTROL_FILE_BOUNDS_EXCEEDED",
    "TRUSTED_PAYLOAD_INVENTORY_MISMATCH", "UNSUPPORTED_VERIFIER_PLATFORM",
    "UNSUPPORTED_FILE_IDENTITY",
})


class _Blocked(Exception):
    pass


class _Unknown(Exception):
    pass


def _sha(data: bytes) -> str:
    return sha256_bytes(data)


def _digest(value: Mapping[str, Any], field: str) -> str:
    return _sha(canonical_json_bytes({key: item for key, item in value.items() if key != field}))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping): return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list): return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping): return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple): return [_thaw(item) for item in value]
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _RFC3339_UTC.fullmatch(value):
        raise ValueError("evaluated_at must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("evaluated_at must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluated_at must be UTC")
    return value


def _path_is_reparse(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _same(a: os.stat_result, b: os.stat_result) -> bool:
    return (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns) == (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns)


def _stable_directory_identity(st: os.stat_result) -> tuple[int, int, int, int]:
    dev, ino = int(st.st_dev), int(st.st_ino)
    if dev <= 0 or ino <= 0:
        raise _Blocked("UNSUPPORTED_FILE_IDENTITY")
    # Attributes other than the reparse marker are not identity facts and may
    # legitimately change (for example archive/indexing bits on Windows).
    return (dev, ino, stat.S_IFMT(st.st_mode), int(_path_is_reparse(st)))


def _lstat_file(path: Path) -> os.stat_result:
    try:
        result = path.lstat()
    except FileNotFoundError as exc:
        raise _Blocked("MISSING_INSTALLED_TREE") from exc
    except OSError as exc:
        raise _Unknown("IO_UNAVAILABLE") from exc
    if _path_is_reparse(result) or not stat.S_ISREG(result.st_mode):
        raise _Blocked("REPARSE_OR_NONREGULAR_FILE")
    return result


def _lstat_dir(path: Path) -> os.stat_result:
    try:
        result = path.lstat()
    except FileNotFoundError as exc:
        raise _Blocked("MISSING_INSTALLED_TREE") from exc
    except OSError as exc:
        raise _Unknown("IO_UNAVAILABLE") from exc
    if _path_is_reparse(result) or not stat.S_ISDIR(result.st_mode):
        raise _Blocked("REPARSE_OR_NON_DIRECTORY")
    return result


def _ancestor_guard(path: Path) -> None:
    # This checks every existing ancestor, pre and post every sensitive access.
    anchor = path.anchor
    parts = path.parts
    current = Path(anchor) if anchor else Path(parts[0])
    start = 1 if anchor else 1
    for part in parts[start:]:
        current = current / part
        _lstat_dir(current)


def _ancestor_identities(path: Path) -> tuple[tuple[int, int, int, int], ...]:
    anchor = path.anchor
    parts = path.parts
    current = Path(anchor) if anchor else Path(parts[0])
    values: list[tuple[int, int, int, int]] = []
    for part in parts[1:]:
        current = current / part
        st = _lstat_dir(current)
        values.append(_stable_directory_identity(st))
    return tuple(values)


def _default_get_drive_type(path: Path) -> int:
    if os.name != "nt":
        return DRIVE_FIXED
    import ctypes
    return int(ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor + "\\")))


def _safe_root(path: Path) -> None:
    raw = str(path)
    if not path.is_absolute() or raw.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\")):
        raise _Blocked("UNSAFE_RUNTIME_ROOT")
    raw_parts = [part for part in raw.replace("\\", "/").split("/") if part and not _DRIVE.fullmatch(part)]
    if any(part in {".", ".."} or part.endswith((".", " ")) for part in raw_parts):
        raise _Blocked("UNSAFE_RUNTIME_ROOT")
    if os.name != "nt":
        raise _Blocked("UNSUPPORTED_VERIFIER_PLATFORM")
    if not _DRIVE.fullmatch(path.drive) or _default_get_drive_type(path) != DRIVE_FIXED:
        raise _Blocked("UNSAFE_RUNTIME_ROOT")
    _ancestor_guard(path)


def _safe_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise _Blocked("UNSAFE_ARCHIVE_PATH")
    try:
        name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise _Blocked("UNSAFE_ARCHIVE_PATH") from exc
    if any(ord(char) < 33 or ord(char) > 126 for char in name):
        raise _Blocked("UNSAFE_ARCHIVE_PATH")
    p = PurePosixPath(name)
    if p.is_absolute() or p.name in {"", ".", ".."} or any(part in {"", ".", ".."} for part in p.parts):
        raise _Blocked("UNSAFE_ARCHIVE_PATH")
    return name


def _stream_file(path: Path, *, maximum: int = MAX_EXPANDED_BYTES) -> tuple[str, int]:
    parents = _ancestor_identities(path.parent)
    before = _lstat_file(path)
    if before.st_size > maximum:
        raise _Blocked("CONTROL_FILE_BOUNDS_EXCEEDED")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not _same(before, opened) or parents != _ancestor_identities(path.parent):
                raise _Blocked("FILE_RACE_DETECTED")
            digest = hashlib.sha256()
            length = 0
            while chunk := handle.read(64 * 1024):
                digest.update(chunk)
                length += len(chunk)
                if length > maximum:
                    raise _Blocked("CONTROL_FILE_BOUNDS_EXCEEDED")
    except _Blocked:
        raise
    except OSError as exc:
        raise _Unknown("IO_UNAVAILABLE") from exc
    after = _lstat_file(path)
    if not _same(before, after) or parents != _ancestor_identities(path.parent):
        raise _Blocked("FILE_RACE_DETECTED")
    return "sha256:" + digest.hexdigest(), length


def _read_guarded(path: Path, maximum: int) -> bytes:
    """Read a small control file with the same anti-TOCTOU discipline."""
    parents = _ancestor_identities(path.parent)
    before = _lstat_file(path)
    if before.st_size > maximum:
        raise _Blocked("CONTROL_FILE_BOUNDS_EXCEEDED")
    try:
        with path.open("rb") as handle:
            if not _same(before, os.fstat(handle.fileno())) or parents != _ancestor_identities(path.parent):
                raise _Blocked("FILE_RACE_DETECTED")
            value = handle.read(maximum + 1)
    except _Blocked:
        raise
    except OSError as exc:
        raise _Unknown("IO_UNAVAILABLE") from exc
    if len(value) > maximum or not _same(before, _lstat_file(path)) or parents != _ancestor_identities(path.parent):
        raise _Blocked("FILE_RACE_DETECTED")
    return value


def _read_pinned_wheel(path: Path) -> bytes:
    """Bind validation and ZIP parsing to one immutable in-memory byte sequence."""
    parents = _ancestor_identities(path.parent)
    before = _lstat_file(path)
    if before.st_size != WHEEL_BYTES:
        raise _Blocked("WHEEL_PIN_MISMATCH")
    try:
        with path.open("rb") as handle:
            if not _same(before, os.fstat(handle.fileno())) or parents != _ancestor_identities(path.parent):
                raise _Blocked("FILE_RACE_DETECTED")
            raw = handle.read(WHEEL_BYTES + 1)
            if len(raw) != WHEEL_BYTES or not _same(before, os.fstat(handle.fileno())):
                raise _Blocked("FILE_RACE_DETECTED")
    except _Blocked:
        raise
    except OSError as exc:
        raise _Unknown("IO_UNAVAILABLE") from exc
    if not _same(before, _lstat_file(path)) or parents != _ancestor_identities(path.parent):
        raise _Blocked("FILE_RACE_DETECTED")
    if path.name != WHEEL_FILENAME or "sha256:" + hashlib.sha256(raw).hexdigest() != WHEEL_SHA256:
        raise _Blocked("WHEEL_PIN_MISMATCH")
    return raw


def _parse_record(raw: bytes, *, wheel: bool) -> dict[str, tuple[str | None, int | None]]:
    if len(raw) > MAX_RECORD_BYTES:
        raise _Blocked("MALFORMED_RECORD")
    try:
        text = raw.decode("utf-8", "strict")
        rows = csv.reader(io.StringIO(text, newline=""))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise _Blocked("MALFORMED_RECORD") from exc
    values: dict[str, tuple[str | None, int | None]] = {}
    seen_casefold: set[str] = set()
    for row_count, row in enumerate(rows, start=1):
        if row_count > MAX_MEMBERS or len(row) != 3 or any(len(field.encode("utf-8")) > MAX_RECORD_FIELD_BYTES for field in row):
            raise _Blocked("MALFORMED_RECORD")
        # pip records its generated console executable relative to site-packages.
        # It is normalized later, but no other traversal spelling is ever accepted.
        if not wheel and row[0] == "../../Scripts/qwen-tts-demo.exe":
            name = row[0]
        else:
            name = _safe_member(row[0])
        if name in values or name.casefold() in seen_casefold:
            raise _Blocked("DUPLICATE_RECORD_PATH")
        seen_casefold.add(name.casefold())
        hashed, size = row[1], row[2]
        if not hashed and not size:
            values[name] = (None, None)
            continue
        if not hashed or not size or not _SHA_B64.fullmatch(hashed) or not size.isascii() or not size.isdecimal():
            raise _Blocked("MALFORMED_RECORD")
        encoded = hashed.split("=", 1)[1]
        try:
            decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        except (ValueError, binascii.Error) as exc:
            raise _Blocked("MALFORMED_RECORD") from exc
        if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
            raise _Blocked("MALFORMED_RECORD")
        if (len(size) > 1 and size.startswith("0")) or int(size) > MAX_EXPANDED_BYTES:
            raise _Blocked("MALFORMED_RECORD")
        values[name] = ("sha256:" + decoded.hex(), int(size))
    if not values:
        raise _Blocked("MALFORMED_RECORD")
    return values


def _zip_inventory(path: Path) -> tuple[dict[str, tuple[str, int]], dict[str, tuple[str | None, int | None]]]:
    try:
        raw = _read_pinned_wheel(path)
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
                infos = archive.infolist()
                if not 1 <= len(infos) <= MAX_MEMBERS or sum(item.file_size for item in infos) > MAX_EXPANDED_BYTES:
                    raise _Blocked("ARCHIVE_BOUNDS_EXCEEDED")
                names: set[str] = set()
                casefolded: set[str] = set()
                inventory: dict[str, tuple[str, int]] = {}
                record_raw: bytes | None = None
                entry_raw: bytes | None = None
                for info in infos:
                    name = _safe_member(info.filename)
                    kind = (info.external_attr >> 16) & 0o170000
                    if name in names or name.casefold() in casefolded or info.is_dir() or kind in {stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK}:
                        raise _Blocked("UNSAFE_ARCHIVE_MEMBER")
                    names.add(name); casefolded.add(name.casefold())
                    with archive.open(info, "r") as member:
                        h = hashlib.sha256(); size = 0
                        while chunk := member.read(64 * 1024):
                            h.update(chunk); size += len(chunk)
                    if size != info.file_size:
                        raise _Blocked("ARCHIVE_MEMBER_SIZE_MISMATCH")
                    inventory[name] = ("sha256:" + h.hexdigest(), size)
                    if name == f"{DIST_INFO}/RECORD":
                        with archive.open(info, "r") as member:
                            record_raw = member.read(MAX_RECORD_BYTES + 1)
                        if len(record_raw) > MAX_RECORD_BYTES:
                            raise _Blocked("ARCHIVE_BOUNDS_EXCEEDED")
                    if name == f"{DIST_INFO}/entry_points.txt":
                        with archive.open(info, "r") as member:
                            entry_raw = member.read(4097)
                        if len(entry_raw) > 4096:
                            raise _Blocked("ARCHIVE_BOUNDS_EXCEEDED")
                record_name = f"{DIST_INFO}/RECORD"
                if record_raw is None or sum(name == record_name for name in names) != 1:
                    raise _Blocked("WHEEL_RECORD_MISSING")
    except _Blocked:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise _Blocked("INVALID_WHEEL_ARCHIVE") from exc
    record = _parse_record(record_raw, wheel=True)
    if set(record) != set(inventory) or record.get(f"{DIST_INFO}/RECORD") != (None, None):
        raise _Blocked("WHEEL_RECORD_MEMBER_SET_MISMATCH")
    for name, (expected_hash, expected_size) in record.items():
        if name == f"{DIST_INFO}/RECORD":
            continue
        if inventory[name] != (expected_hash, expected_size):
            raise _Blocked("WHEEL_RECORD_HASH_MISMATCH")
    trusted = {name: value for name, value in record.items() if name != f"{DIST_INFO}/RECORD"}
    if len(inventory) != 24 or len(trusted) != 23 or sum(name.endswith(".py") for name in trusted) != 17:
        raise _Blocked("WHEEL_OBSERVED_COUNT_MISMATCH")
    entry = f"{DIST_INFO}/entry_points.txt"
    if entry not in inventory or entry_raw is None:
        raise _Blocked("WHEEL_ENTRY_POINT_MISSING")
    # This is read from pinned in-memory wheel bytes before runtime-root I/O.
    if entry_raw != b"[console_scripts]\nqwen-tts-demo = qwen_tts.cli.demo:main\n":
        raise _Blocked("WHEEL_ENTRY_POINT_MISMATCH")
    return inventory, record


def _cache_path(source: str) -> str:
    p = PurePosixPath(source)
    return str(p.parent / "__pycache__" / f"{p.stem}.cpython-312.pyc")


def _expected_dirs(paths: set[str]) -> set[str]:
    result: set[str] = set()
    for name in paths:
        parent = PurePosixPath(name).parent
        while str(parent) not in {"", "."}:
            result.add(str(parent)); parent = parent.parent
    return result


def _runtime_inventory(root: Path, wheel_rows: Mapping[str, tuple[str | None, int | None]]) -> tuple[dict[str, tuple[str, int]], str]:
    site = root / "Lib" / "site-packages"
    _ancestor_guard(site)
    record_name = f"{DIST_INFO}/RECORD"
    trusted = {name: row for name, row in wheel_rows.items() if name != record_name}
    expected = set(wheel_rows)
    expected_cache = {_cache_path(name) for name, (h, _) in trusted.items() if h is not None and name.endswith(".py")}
    generated_installation = {
        "../../Scripts/qwen-tts-demo.exe",
        f"{DIST_INFO}/INSTALLER", f"{DIST_INFO}/REQUESTED", f"{DIST_INFO}/direct_url.json",
    }
    tree_expected = expected | expected_cache | (generated_installation - {"../../Scripts/qwen-tts-demo.exe"})
    dirs = _expected_dirs(tree_expected)
    # Only the two distribution-owned trees are enumerated.  We never scan site-packages.
    for top in (PACKAGE, DIST_INFO):
        if top not in dirs:
            raise _Blocked("WHEEL_LAYOUT_MISMATCH")
    seen: set[str] = set(); count = 0
    def visit(logical: str) -> None:
        nonlocal count
        directory = site.joinpath(*PurePosixPath(logical).parts)
        before = _lstat_dir(directory)
        try:
            entries: dict[str, os.DirEntry[str]] = {}
            with os.scandir(directory) as scan:
                for entry in scan:
                    count += 1
                    if count > MAX_MEMBERS:
                        raise _Blocked("INSTALLED_INVENTORY_BOUNDS_EXCEEDED")
                    entries[entry.name] = entry
        except OSError as exc:
            raise _Unknown("IO_UNAVAILABLE") from exc
        actual_names = set(entries)
        allowed = {PurePosixPath(item).name for item in tree_expected | dirs if str(PurePosixPath(item).parent) == logical}
        if actual_names != allowed or {name.casefold() for name in actual_names} != {name.casefold() for name in allowed}:
            raise _Blocked("INSTALLED_TREE_EXTRA_MISSING_OR_CASE_MISMATCH")
        for entry in entries.values():
            child = f"{logical}/{entry.name}"
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise _Unknown("IO_UNAVAILABLE") from exc
            if _path_is_reparse(st):
                raise _Blocked("REPARSE_OR_NONREGULAR_FILE")
            if child in dirs:
                if not stat.S_ISDIR(st.st_mode): raise _Blocked("INSTALLED_TREE_TYPE_MISMATCH")
                visit(child)
            else:
                if child not in tree_expected or not stat.S_ISREG(st.st_mode): raise _Blocked("INSTALLED_TREE_TYPE_MISMATCH")
                seen.add(child)
        if _stable_directory_identity(before) != _stable_directory_identity(_lstat_dir(directory)):
            raise _Blocked("FILE_RACE_DETECTED")
    visit(PACKAGE); visit(DIST_INFO)
    if seen != tree_expected:
        raise _Blocked("INSTALLED_TREE_EXTRA_MISSING_OR_CASE_MISMATCH")
    record_path = site.joinpath(DIST_INFO, "RECORD")
    record_raw = _read_guarded(record_path, MAX_RECORD_BYTES)
    installed = _parse_record(record_raw, wheel=False)
    # Read-bytes is only for the bounded, already lstat/open/fstat checked RECORD.
    if len(wheel_rows) != 24 or len(trusted) != 23 or len(expected_cache) != 17:
        raise _Blocked("WHEEL_OBSERVED_COUNT_MISMATCH")
    allowed = expected | generated_installation | expected_cache
    if set(installed) != allowed or len(installed) != 45:
        raise _Blocked("INSTALLED_RECORD_MEMBER_SET_MISMATCH")
    if installed.get(record_name) != (None, None):
        raise _Blocked("INSTALLED_RECORD_SELF_ROW_INVALID")
    for name in trusted:
        if installed[name] != trusted[name]:
            raise _Blocked("INSTALLED_RECORD_TRUSTED_ROW_MISMATCH")
    for name in expected_cache:
        if installed[name] != (None, None):
            raise _Blocked("INSTALLED_RECORD_GENERATED_ROW_INVALID")
    for name in generated_installation:
        item_hash, item_size = installed[name]
        if item_hash is None or item_size is None:
            raise _Blocked("INSTALLED_RECORD_GENERATED_ROW_INVALID")
    entry_point = f"{DIST_INFO}/entry_points.txt"
    if entry_point not in trusted:
        raise _Blocked("WHEEL_ENTRY_POINT_MISSING")
    entry_raw = _read_guarded(site.joinpath(*PurePosixPath(entry_point).parts), 4096)
    if entry_raw != b"[console_scripts]\nqwen-tts-demo = qwen_tts.cli.demo:main\n":
        raise _Blocked("WHEEL_ENTRY_POINT_MISMATCH")
    values: dict[str, tuple[str, int]] = {}
    observed: dict[str, str] = {}
    observed_bytes = 0
    for name in sorted(trusted):
        file_hash, size = _stream_file(site.joinpath(*PurePosixPath(name).parts))
        observed_bytes += size
        if observed_bytes > MAX_EXPANDED_BYTES:
            raise _Blocked("INSTALLED_INVENTORY_BOUNDS_EXCEEDED")
        if (file_hash, size) != trusted[name]:
            raise _Blocked("INSTALLED_TRUSTED_BODY_MISMATCH")
        values[name] = (file_hash, size)
    for name in sorted(expected_cache):
        file_hash, size = _stream_file(site.joinpath(*PurePosixPath(name).parts))
        observed_bytes += size
        if observed_bytes > MAX_EXPANDED_BYTES:
            raise _Blocked("INSTALLED_INVENTORY_BOUNDS_EXCEEDED")
        observed[name] = file_hash
    # This is the sole normalized parent traversal admitted by the contract.  It
    # resolves to runtime_root/Scripts, never outside runtime_root.
    script = root / "Scripts" / "qwen-tts-demo.exe"
    _ancestor_guard(script.parent)
    script_hash, script_size = _stream_file(script)
    observed_bytes += script_size
    if observed_bytes > MAX_EXPANDED_BYTES:
        raise _Blocked("INSTALLED_INVENTORY_BOUNDS_EXCEEDED")
    if (script_hash, script_size) != installed["../../Scripts/qwen-tts-demo.exe"]:
        raise _Blocked("INSTALLED_GENERATED_BODY_MISMATCH")
    observed["Scripts/qwen-tts-demo.exe"] = script_hash
    for name in sorted(generated_installation - {"../../Scripts/qwen-tts-demo.exe"}):
        file_hash, size = _stream_file(site.joinpath(*PurePosixPath(name).parts))
        observed_bytes += size
        if observed_bytes > MAX_EXPANDED_BYTES:
            raise _Blocked("INSTALLED_INVENTORY_BOUNDS_EXCEEDED")
        if (file_hash, size) != installed[name]:
            raise _Blocked("INSTALLED_GENERATED_BODY_MISMATCH")
        observed[name] = file_hash
    direct_url = _read_guarded(site.joinpath(DIST_INFO, "direct_url.json"), 16 * 1024)
    try:
        import json
        def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result: raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        parsed_direct_url = json.loads(direct_url.decode("utf-8", "strict"), object_pairs_hook=no_duplicates, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON")))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise _Blocked("DIRECT_URL_JSON_INVALID") from exc
    bare = WHEEL_SHA256.removeprefix("sha256:")
    if not isinstance(parsed_direct_url, dict) or set(parsed_direct_url) != {"archive_info", "url"} or not isinstance(parsed_direct_url["archive_info"], dict) or set(parsed_direct_url["archive_info"]) != {"hash", "hashes"} or parsed_direct_url["archive_info"].get("hash") != "sha256=" + bare or parsed_direct_url["archive_info"].get("hashes") != {"sha256": bare} or not isinstance(parsed_direct_url["url"], str):
        raise _Blocked("DIRECT_URL_JSON_INVALID")
    try:
        split = urlsplit(parsed_direct_url["url"])
    except ValueError as exc:
        raise _Blocked("DIRECT_URL_JSON_INVALID") from exc
    if split.scheme != "file" or split.netloc or split.query or split.fragment or not split.path.replace("\\", "/").endswith("/" + WHEEL_FILENAME):
        raise _Blocked("DIRECT_URL_JSON_INVALID")
    # A second exact enumeration closes the window between a per-file hash and
    # receipt issuance: late files, type changes, and trusted-body swaps fail.
    seen.clear(); count = 0
    visit(PACKAGE); visit(DIST_INFO)
    if seen != tree_expected:
        raise _Blocked("FILE_RACE_DETECTED")
    for name, expected_value in values.items():
        if _stream_file(site.joinpath(*PurePosixPath(name).parts)) != expected_value:
            raise _Blocked("FILE_RACE_DETECTED")
    for name, expected_hash in observed.items():
        path = script if name == "Scripts/qwen-tts-demo.exe" else site.joinpath(*PurePosixPath(name).parts)
        if _stream_file(path)[0] != expected_hash:
            raise _Blocked("FILE_RACE_DETECTED")
    if _read_guarded(record_path, MAX_RECORD_BYTES) != record_raw:
        raise _Blocked("FILE_RACE_DETECTED")
    # Re-enumerate *after* the terminal body reads so a final late file/type
    # change cannot slip between the previous reconciliation and receipt issue.
    seen.clear(); count = 0
    visit(PACKAGE); visit(DIST_INFO)
    if seen != tree_expected:
        raise _Blocked("FILE_RACE_DETECTED")
    _ancestor_guard(site)
    if _sha(canonical_json_bytes(values)) != TRUSTED_PAYLOAD_INVENTORY_SHA256:
        raise _Blocked("TRUSTED_PAYLOAD_INVENTORY_MISMATCH")
    return values, _sha(canonical_json_bytes(observed))


def _private_body(*, evaluated_at: str, decision: str, reasons: tuple[str, ...], wheel_path: Path, runtime_root: Path, inventory: Mapping[str, tuple[str, int]] | None = None, generated_digest: str | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA_ID, "scope": SCOPE, "package_name": "qwen-tts", "package_version": "0.1.1",
        "wheel_filename": WHEEL_FILENAME, "wheel_bytes": WHEEL_BYTES, "wheel_sha256": WHEEL_SHA256,
        "wheel_member_count": 24 if inventory is not None else 0, "wheel_record_row_count": 24 if inventory is not None else 0,
        "trusted_wheel_row_count": 23 if inventory is not None else 0, "installed_record_row_count": 45 if inventory is not None else 0,
        "installed_unhashed_row_count": 18 if inventory is not None else 0, "generated_cache_rows": 17 if inventory is not None else 0,
        "generated_installation_rows": 4 if inventory is not None else 0, "untrusted_generated_rows": 21 if inventory is not None else 0,
        "wheel_record_rows": 24 if inventory is not None else 0, "trusted_payload_files": 23 if inventory is not None else 0,
        "installed_record_rows": 45 if inventory is not None else 0, "pip_generated_files": 4 if inventory is not None else 0,
        "pip_generated_trusted_files": 0, "pip_generated_self_consistent_files": 4 if inventory is not None else 0,
        "generated_cache_files": 17 if inventory is not None else 0, "generated_cache_trusted_files": 0,
        "installed_record_trusted": False, "direct_url_redacted": True, "unknown_rows": 0,
        "trusted_inventory_digest": _sha(canonical_json_bytes(inventory)) if inventory is not None else None,
        "untrusted_generated_observation_digest": generated_digest,
        "wheel_path_fingerprint": _sha(str(wheel_path).encode("utf-8")), "runtime_root_fingerprint": _sha(str(runtime_root).encode("utf-8")),
        "evaluated_at": evaluated_at, "decision": decision, "reason_codes": list(reasons),
        "archive_enumerated": inventory is not None, "inventory_enumerated": inventory is not None,
        "trusted_bodies_hashed": inventory is not None, "installed_tree_modified": False,
        "untrusted_generated_cache_present": inventory is not None, "tree_mutability": "MUTABLE_UNLOCKED",
        "post_return_state_guaranteed": False, "authoritative_runtime_gate": False,
        "immutable_snapshot_verified": False, "locked_handles_held_through_consumer": False,
        "runtime_reuse_authorized": False, "consumer_revalidation_required": True,
        "dependency_resolved_or_installed": False, "target_python_executed": False, "target_package_imported": False,
        "model_loaded": False, "owner_audio_read": False, "inference_executed": False, "network_accessed": False,
        "subprocess_started": False, "archive_extracted": False, "absolute_path_persisted": False,
    }


def _validate(value: Mapping[str, Any]) -> dict[str, Any]:
    required = set(_private_body(evaluated_at="2026-08-21T00:00:00Z", decision="UNKNOWN", reasons=(), wheel_path=Path("/wheel"), runtime_root=Path("/runtime")).keys()) | {"receipt_sha256"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError("receipt fields are incomplete or unknown")
    copy = dict(value)
    if copy["schema"] != SCHEMA_ID or copy["scope"] != SCOPE or copy["package_name"] != "qwen-tts" or copy["package_version"] != "0.1.1": raise ValueError("receipt identity mismatch")
    if (copy["wheel_filename"], copy["wheel_bytes"], copy["wheel_sha256"]) != (WHEEL_FILENAME, WHEEL_BYTES, WHEEL_SHA256): raise ValueError("wheel pin mismatch")
    _timestamp(copy["evaluated_at"])
    counts = ("wheel_member_count", "wheel_record_row_count", "trusted_wheel_row_count", "installed_record_row_count", "installed_unhashed_row_count", "generated_cache_rows", "generated_installation_rows", "untrusted_generated_rows", "wheel_record_rows", "trusted_payload_files", "installed_record_rows", "pip_generated_files", "pip_generated_trusted_files", "pip_generated_self_consistent_files", "generated_cache_files", "generated_cache_trusted_files", "unknown_rows")
    if any(not isinstance(copy[field], int) or isinstance(copy[field], bool) or not 0 <= copy[field] <= MAX_MEMBERS for field in counts): raise ValueError("receipt count is invalid")
    if copy["decision"] not in {"QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE", "BLOCKED", "UNKNOWN"} or not isinstance(copy["reason_codes"], list) or len(copy["reason_codes"]) != len(set(copy["reason_codes"])) or any(not isinstance(item, str) or item not in (_BLOCKER_REASONS | _UNKNOWN_REASONS) for item in copy["reason_codes"]): raise ValueError("decision or reasons invalid")
    if copy["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE" and copy["reason_codes"]: raise ValueError("complete observation must have no reasons")
    if copy["decision"] != "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE" and len(copy["reason_codes"]) != 1: raise ValueError("non-success requires exactly one reason")
    if copy["decision"] == "BLOCKED" and not any(item in _BLOCKER_REASONS for item in copy["reason_codes"]): raise ValueError("BLOCKED requires a blocker reason")
    if copy["decision"] == "UNKNOWN" and any(item not in _UNKNOWN_REASONS for item in copy["reason_codes"]): raise ValueError("UNKNOWN may contain only unknown reasons")
    for field in ("wheel_sha256", "wheel_path_fingerprint", "runtime_root_fingerprint", "receipt_sha256"):
        validate_sha256(copy[field], field_name=field)
    for field in ("trusted_inventory_digest", "untrusted_generated_observation_digest"):
        if copy[field] is not None: validate_sha256(copy[field], field_name=field)
    for field in ("dependency_resolved_or_installed", "target_python_executed", "target_package_imported", "model_loaded", "owner_audio_read", "inference_executed", "network_accessed", "subprocess_started", "archive_extracted", "absolute_path_persisted", "post_return_state_guaranteed", "authoritative_runtime_gate", "immutable_snapshot_verified", "locked_handles_held_through_consumer", "runtime_reuse_authorized"):
        if copy[field] is not False: raise ValueError(f"{field} must remain false")
    for field in ("archive_enumerated", "inventory_enumerated", "trusted_bodies_hashed", "installed_tree_modified", "untrusted_generated_cache_present", "installed_record_trusted", "direct_url_redacted"):
        if not isinstance(copy[field], bool): raise ValueError(f"{field} must be boolean")
    if copy["installed_tree_modified"] is not False or copy["installed_record_trusted"] is not False or copy["direct_url_redacted"] is not True or copy["tree_mutability"] != "MUTABLE_UNLOCKED" or copy["consumer_revalidation_required"] is not True: raise ValueError("receipt safety invariant failed")
    if copy["decision"] == "QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE":
        if [copy[field] for field in ("wheel_member_count", "wheel_record_row_count", "trusted_wheel_row_count", "installed_record_row_count", "installed_unhashed_row_count", "generated_cache_rows", "generated_installation_rows", "untrusted_generated_rows", "wheel_record_rows", "trusted_payload_files", "installed_record_rows", "pip_generated_files", "pip_generated_trusted_files", "pip_generated_self_consistent_files", "generated_cache_files", "generated_cache_trusted_files", "unknown_rows")] != [24, 24, 23, 45, 18, 17, 4, 21, 24, 23, 45, 4, 0, 4, 17, 0, 0] or not copy["untrusted_generated_cache_present"] or not copy["direct_url_redacted"] or not all(copy[field] for field in ("archive_enumerated", "inventory_enumerated", "trusted_bodies_hashed")):
            raise ValueError("success observation invariants failed")
        if copy["trusted_inventory_digest"] != TRUSTED_PAYLOAD_INVENTORY_SHA256 or copy["untrusted_generated_observation_digest"] is None:
            raise ValueError("success digests are required")
    else:
        if any(copy[field] for field in ("archive_enumerated", "inventory_enumerated", "trusted_bodies_hashed", "untrusted_generated_cache_present")) or any(copy[field] for field in counts) or copy["trusted_inventory_digest"] is not None or copy["untrusted_generated_observation_digest"] is not None:
            raise ValueError("non-success must not claim an observation")
    if copy["receipt_sha256"] != _digest(copy, "receipt_sha256"): raise ValueError("receipt_sha256 mismatch")
    return copy


@dataclass(frozen=True, slots=True)
class QwenTtsInstalledTreeVerification:
    _value: Mapping[str, Any]
    def __post_init__(self) -> None: object.__setattr__(self, "_value", _freeze(_validate(self._value)))
    def to_private_dict(self) -> dict[str, Any]: return _thaw(self._value)
    def to_public_dict(self) -> dict[str, Any]:
        value = self.to_private_dict()
        return {key: item for key, item in value.items() if key not in {"wheel_path_fingerprint", "runtime_root_fingerprint", "trusted_inventory_digest", "untrusted_generated_observation_digest", "receipt_sha256"}}


def parse_qwen_tts_011_installed_tree_verification(mapping: Mapping[str, Any]) -> QwenTtsInstalledTreeVerification:
    return QwenTtsInstalledTreeVerification(dict(mapping))


def verify_qwen_tts_011_installed_tree(wheel_path: Path, runtime_root: Path, evaluated_at: str) -> QwenTtsInstalledTreeVerification:
    """Return a private receipt; all failures are fail-closed BLOCKED or UNKNOWN."""
    _timestamp(evaluated_at)
    wheel_path, runtime_root = Path(wheel_path), Path(runtime_root)
    try:
        _safe_root(wheel_path.parent)
        inventory, wheel_record = _zip_inventory(wheel_path)
        # The pinned wheel is the first trust boundary.  Do not touch an
        # installed runtime for a wrong or malformed wheel.
        _safe_root(runtime_root)
        values, generated = _runtime_inventory(runtime_root, wheel_record)
        body = _private_body(evaluated_at=evaluated_at, decision="QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE", reasons=(), wheel_path=wheel_path, runtime_root=runtime_root, inventory=values, generated_digest=generated)
    except _Blocked as exc:
        body = _private_body(evaluated_at=evaluated_at, decision="BLOCKED", reasons=(str(exc),), wheel_path=wheel_path, runtime_root=runtime_root)
    except _Unknown as exc:
        body = _private_body(evaluated_at=evaluated_at, decision="UNKNOWN", reasons=(str(exc),), wheel_path=wheel_path, runtime_root=runtime_root)
    body["receipt_sha256"] = _digest(body, "receipt_sha256")
    return QwenTtsInstalledTreeVerification(body)
