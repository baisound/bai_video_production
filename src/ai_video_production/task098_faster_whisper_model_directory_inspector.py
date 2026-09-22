"""Contained read-only TASK-098 FasterWhisper model-directory inspector.

The inspector creates the body-free A3-R0 contract from one explicit local
directory.  It never writes settings or files and never loads a model, performs
inference, accesses the network, downloads content, or reads audio.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterable

from .serialization import sha256_bytes
from .task098_faster_whisper_model_directory import (
    ALLOWED_MODEL_FILE_NAMES,
    JSON_MODEL_FILE_NAMES,
    MODEL_FILE_SIZE_LIMITS,
    REQUIRED_FIXED_MODEL_FILE_NAMES,
    VOCABULARY_MODEL_FILE_NAMES,
    FasterWhisperModelDirectoryInspectionV1,
    FasterWhisperModelFileObservationV1,
)


MAX_MODEL_DIRECTORY_ENTRIES = 64
_READ_CHUNK_BYTES = 4 * 1024 * 1024
_REPARSE_POINT = 0x00000400


def _blocked(*reasons: str) -> FasterWhisperModelDirectoryInspectionV1:
    return FasterWhisperModelDirectoryInspectionV1.blocked(*sorted(set(reasons)))


def _physical_identity(metadata: os.stat_result) -> tuple[int, ...]:
    identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )
    # Windows path-stat and descriptor-stat expose different st_ctime_ns
    # projections for the same unchanged file on supported Python versions.
    # Prefer the stable birth time when Python exposes it; older Windows
    # versions still retain identity, type, size and modification-time checks.
    if os.name == "nt":
        birthtime = getattr(metadata, "st_birthtime_ns", None)
        return identity if birthtime is None else (*identity, birthtime)
    return (*identity, metadata.st_ctime_ns)


def _is_alias(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _alias_ancestry_reason(path: Path) -> str | None:
    candidates = [*reversed(path.parents), path]
    for candidate in candidates:
        try:
            metadata = candidate.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            return "DIRECTORY_SCAN_FAILED"
        if _is_alias(metadata):
            return "PATH_ALIAS_UNSAFE"
    return None


def _scan_entries(root: Path) -> tuple[Path, ...]:
    return tuple(root.iterdir())


def _read_stable_file(
    path: Path,
    *,
    name: str,
) -> tuple[FasterWhisperModelFileObservationV1 | None, str | None]:
    maximum = MODEL_FILE_SIZE_LIMITS[name]
    try:
        before = path.stat(follow_symlinks=False)
    except OSError:
        return None, "FILE_HASH_INVALID"
    if _is_alias(before):
        return None, "FILE_ALIAS_UNSAFE"
    if not stat.S_ISREG(before.st_mode):
        return None, "FILE_NOT_REGULAR"
    if before.st_nlink != 1:
        return None, "FILE_ALIAS_UNSAFE"
    if not 1 <= before.st_size <= maximum:
        return None, "FILE_SIZE_INVALID"

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, "FILE_HASH_INVALID"

    opened: os.stat_result | None = None
    after_open: os.stat_result | None = None
    digest = hashlib.sha256()
    counted = 0
    json_bytes = bytearray() if name in JSON_MODEL_FILE_NAMES else None
    failure: str | None = None
    try:
        opened = os.fstat(descriptor)
        if _is_alias(opened):
            failure = "FILE_ALIAS_UNSAFE"
        elif not stat.S_ISREG(opened.st_mode):
            failure = "FILE_NOT_REGULAR"
        elif opened.st_nlink != 1:
            failure = "FILE_ALIAS_UNSAFE"
        elif not 1 <= opened.st_size <= maximum:
            failure = "FILE_SIZE_INVALID"
        else:
            while True:
                chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, maximum + 1 - counted))
                if not chunk:
                    break
                counted += len(chunk)
                digest.update(chunk)
                if json_bytes is not None:
                    json_bytes.extend(chunk)
                if counted > maximum:
                    failure = "FILE_SIZE_INVALID"
                    break
            after_open = os.fstat(descriptor)
    except OSError:
        failure = "FILE_HASH_INVALID"
    finally:
        os.close(descriptor)

    try:
        after = path.stat(follow_symlinks=False)
    except OSError:
        return None, "FILE_HASH_INVALID"
    if failure is not None:
        return None, failure
    if opened is None or after_open is None:
        return None, "FILE_HASH_INVALID"
    if not (
        _physical_identity(before)
        == _physical_identity(opened)
        == _physical_identity(after_open)
        == _physical_identity(after)
    ):
        return None, "FILE_HASH_INVALID"
    if counted != opened.st_size:
        return None, "FILE_HASH_INVALID"
    if json_bytes is not None:
        try:
            json.loads(bytes(json_bytes).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            return None, "REQUIRED_JSON_INVALID"
    return (
        FasterWhisperModelFileObservationV1(
            name=name,
            size_bytes=counted,
            sha256="sha256:" + digest.hexdigest(),
        ),
        None,
    )


def _directory_identity_reason(root: Path, before: os.stat_result) -> str | None:
    try:
        after = root.stat(follow_symlinks=False)
    except OSError:
        return "DIRECTORY_SCAN_FAILED"
    if _is_alias(after):
        return "PATH_ALIAS_UNSAFE"
    if not stat.S_ISDIR(after.st_mode) or _physical_identity(before) != _physical_identity(after):
        return "DIRECTORY_SCAN_FAILED"
    return None


def _shape_reasons(names: Iterable[str]) -> set[str]:
    available = set(names)
    reasons: set[str] = set()
    if not REQUIRED_FIXED_MODEL_FILE_NAMES.issubset(available):
        reasons.add("REQUIRED_FILE_MISSING")
    if len(available & VOCABULARY_MODEL_FILE_NAMES) != 1:
        reasons.add("VOCABULARY_SET_INVALID")
    return reasons


def inspect_faster_whisper_model_directory(
    locator: str | os.PathLike[str],
) -> FasterWhisperModelDirectoryInspectionV1:
    """Inspect one explicit local directory without returning its private path."""

    if not isinstance(locator, (str, os.PathLike)):
        raise TypeError("locator must be a local path")
    try:
        raw_locator = os.fspath(locator)
        if not isinstance(raw_locator, str) or not raw_locator or "\x00" in raw_locator:
            return _blocked("PATH_NOT_DIRECTORY")
        supplied = Path(raw_locator)
    except (TypeError, ValueError):
        return _blocked("PATH_NOT_DIRECTORY")
    if not supplied.is_absolute():
        return _blocked("PATH_ALIAS_UNSAFE")
    absolute = Path(os.path.abspath(supplied))
    ancestry_reason = _alias_ancestry_reason(absolute)
    if ancestry_reason is not None:
        return _blocked(ancestry_reason)
    try:
        before = absolute.stat(follow_symlinks=False)
    except FileNotFoundError:
        return _blocked("PATH_NOT_DIRECTORY")
    except OSError:
        return _blocked("DIRECTORY_SCAN_FAILED")
    if _is_alias(before):
        return _blocked("PATH_ALIAS_UNSAFE")
    if not stat.S_ISDIR(before.st_mode):
        return _blocked("PATH_NOT_DIRECTORY")
    try:
        root = absolute.resolve(strict=True)
        entries = _scan_entries(root)
    except (OSError, RuntimeError):
        return _blocked("DIRECTORY_SCAN_FAILED")
    if len(entries) > MAX_MODEL_DIRECTORY_ENTRIES:
        return _blocked("DIRECTORY_ENTRY_LIMIT_EXCEEDED")

    allowed_entries = {
        entry.name: entry for entry in entries if entry.name in ALLOWED_MODEL_FILE_NAMES
    }
    reasons = _shape_reasons(allowed_entries)
    observations: list[FasterWhisperModelFileObservationV1] = []
    if not reasons:
        for name in sorted(allowed_entries):
            observation, reason = _read_stable_file(allowed_entries[name], name=name)
            if reason is not None:
                reasons.add(reason)
            elif observation is not None:
                observations.append(observation)

    identity_reason = _directory_identity_reason(root, before)
    if identity_reason is not None:
        reasons.add(identity_reason)
    if reasons:
        return _blocked(*reasons)

    return FasterWhisperModelDirectoryInspectionV1.ready(
        private_locator_sha256=sha256_bytes(str(root).encode("utf-8")),
        files=observations,
    )
