from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

@dataclass(frozen=True, order=True, slots=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = _SEMVER.fullmatch(value)
        if not match:
            raise ValueError("schema version must be semantic version x.y.z")
        return cls(*(int(x) for x in match.groups()))


def reader_compatible(reader_version: str, document_version: str) -> bool:
    """Same-major documents are readable.

    Optional MINOR evolution belongs in payload/extension contracts so old
    readers can ignore fields they do not understand. MAJOR changes require a
    migration or adapter.
    """
    reader = SemVer.parse(reader_version)
    document = SemVer.parse(document_version)
    return reader.major == document.major


def requires_migration(from_version: str, to_version: str) -> bool:
    return SemVer.parse(from_version).major != SemVer.parse(to_version).major


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_instance(instance: Any, schema: dict[str, Any] | str | Path) -> None:
    if not isinstance(schema, dict):
        schema = load_schema(schema)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        messages = "; ".join(e.message for e in errors[:5])
        raise ValueError(f"schema validation failed: {messages}")
