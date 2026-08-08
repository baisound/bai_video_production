from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import json
import os
import re
from typing import Any, Iterator

from .ids import IdKind, generate_id, validate_id
from .serialization import canonical_json_bytes, utc_now_iso, validate_sha256

_SECRET_KEY = re.compile(r"(?:secret|password|token|api[_-]?key|credential)", re.I)

def _mask(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if _SECRET_KEY.search(str(k)) else _mask(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v) for v in value]
    return value

@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    production_job_id: str
    category: str
    producer: str
    details: dict[str, Any]
    operation_id: str | None = None
    input_checksums: tuple[str, ...] = ()
    output_checksums: tuple[str, ...] = ()
    evidence_id: str = field(default_factory=lambda: generate_id(IdKind.EVIDENCE))
    created_at: str = field(default_factory=utc_now_iso)
    supersedes_evidence_id: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.production_job_id, IdKind.JOB)
        validate_id(self.evidence_id, IdKind.EVIDENCE)
        if self.operation_id:
            validate_id(self.operation_id, IdKind.OPERATION)
        if self.supersedes_evidence_id:
            validate_id(self.supersedes_evidence_id, IdKind.EVIDENCE)
        for checksum in self.input_checksums:
            validate_sha256(checksum, field_name="evidence input checksum")
        for checksum in self.output_checksums:
            validate_sha256(checksum, field_name="evidence output checksum")

    def to_dict(self) -> dict[str, Any]:
        result = {
            "evidence_id": self.evidence_id,
            "production_job_id": self.production_job_id,
            "category": self.category,
            "producer": self.producer,
            "created_at": self.created_at,
            "input_checksums": list(self.input_checksums),
            "output_checksums": list(self.output_checksums),
            "details": _mask(self.details),
        }
        if self.operation_id:
            result["operation_id"] = self.operation_id
        if self.supersedes_evidence_id:
            result["supersedes_evidence_id"] = self.supersedes_evidence_id
        return result

class EvidenceWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: EvidenceRecord) -> None:
        data = canonical_json_bytes(record.to_dict()) + b"\n"
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            written = os.write(fd, data)
            if written != len(data):
                raise OSError("short evidence write")
            os.fsync(fd)
        finally:
            os.close(fd)

    def append_superseding(self, prior: EvidenceRecord, replacement: EvidenceRecord) -> EvidenceRecord:
        linked = replace(replacement, supersedes_evidence_id=prior.evidence_id)
        self.append(linked)
        return linked

    def iter_records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
