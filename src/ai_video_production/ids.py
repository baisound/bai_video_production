from __future__ import annotations

from enum import Enum
import re
import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_RE = r"[0-9A-HJKMNP-TV-Z]"

class IdKind(str, Enum):
    JOB = "JOB"
    ASSET = "ASSET"
    SEGMENT = "SEG"
    CANDIDATE = "CAND"
    MANIFEST = "MAN"
    OPERATION = "OP"
    EVIDENCE = "EVD"
    CHECKPOINT = "CHK"
    PROFILE_SNAPSHOT = "PSN"
    ASSET_VERSION = "AV"
    APPROVAL = "APR"

_PATTERNS = {k: re.compile(rf"^{k.value}-{_CROCKFORD_RE}{{26}}$") for k in IdKind}
_PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9][a-z0-9-]*)+$")


def _encode_ulid(value: int) -> str:
    chars = ["0"] * 26
    for i in range(25, -1, -1):
        chars[i] = _CROCKFORD[value & 31]
        value >>= 5
    return "".join(chars)


def generate_id(kind: IdKind | str, *, timestamp_ms: int | None = None) -> str:
    kind = IdKind(kind)
    ts = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    if not 0 <= ts < (1 << 48):
        raise ValueError("timestamp_ms must fit 48 bits")
    value = (ts << 80) | int.from_bytes(secrets.token_bytes(10), "big")
    return f"{kind.value}-{_encode_ulid(value)}"


def validate_id(value: str, kind: IdKind | str | None = None) -> str:
    if kind is not None:
        kind = IdKind(kind)
        if not _PATTERNS[kind].fullmatch(value):
            raise ValueError(f"invalid {kind.value} identifier")
        return value
    for pattern in _PATTERNS.values():
        if pattern.fullmatch(value):
            return value
    raise ValueError("invalid product identifier")


def validate_project_id(value: str) -> str:
    if not _PROJECT_RE.fullmatch(value):
        raise ValueError("project_id must be 3-64 lowercase alphanumeric/hyphen characters")
    return value


def validate_schema_id(value: str) -> str:
    if not _SCHEMA_RE.fullmatch(value):
        raise ValueError("schema_id must be a stable dotted/hyphenated lowercase identifier")
    return value
