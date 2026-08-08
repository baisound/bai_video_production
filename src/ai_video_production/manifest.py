from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
import re

from .ids import IdKind, generate_id, validate_id, validate_schema_id
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256

_SECRET_KEY = re.compile(r"(?:secret|password|token|api[_-]?key|credential)", re.I)
_RAW_PATH_KEYS = {"path", "file_path", "absolute_path", "windows_path", "wsl_path", "local_path"}
_RAW_PATH_VALUE = re.compile(r"^(?:[A-Za-z]:[\\/]|/mnt/|/home/|/Users/|\\\\)")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _assert_safe(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            skey = str(key)
            if _SECRET_KEY.search(skey):
                raise ValueError(f"secret-like key is forbidden in canonical manifest: {path}.{skey}")
            if skey.lower() in _RAW_PATH_KEYS:
                raise ValueError(f"raw environment path field is forbidden: {path}.{skey}")
            if isinstance(child, str) and _RAW_PATH_VALUE.match(child):
                raise ValueError(f"raw environment path value is forbidden: {path}.{skey}")
            _assert_safe(child, f"{path}.{skey}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _assert_safe(child, f"{path}[{i}]")

@dataclass(frozen=True, slots=True)
class Producer:
    component: str
    version: str

    def __post_init__(self) -> None:
        if not self.component.strip() or not self.version.strip():
            raise ValueError("producer component/version must be non-empty")

    def to_dict(self) -> dict[str, str]:
        return {"component": self.component, "version": self.version}

@dataclass(frozen=True, slots=True)
class ManifestEnvelope:
    schema_id: str
    schema_version: str
    manifest_id: str
    production_job_id: str
    revision: int
    created_at: str
    producer: Producer
    profile_snapshot_id: str
    source_refs: tuple[str, ...]
    input_checksums: tuple[str, ...]
    content_checksum: str
    operation_id: str | None
    idempotency_key: str | None
    _payload_json: str
    _extensions_json: str

    @classmethod
    def create(
        cls,
        *,
        schema_id: str,
        schema_version: str,
        production_job_id: str,
        revision: int,
        producer: Producer,
        profile_snapshot_id: str,
        payload: dict[str, Any],
        source_refs: tuple[str, ...] = (),
        input_checksums: tuple[str, ...] = (),
        operation_id: str | None = None,
        idempotency_key: str | None = None,
        created_at: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> "ManifestEnvelope":
        validate_schema_id(schema_id)
        if not _SEMVER.fullmatch(schema_version):
            raise ValueError("schema_version must be semantic version x.y.z")
        validate_id(production_job_id, IdKind.JOB)
        validate_id(profile_snapshot_id, IdKind.PROFILE_SNAPSHOT)
        if operation_id is not None:
            validate_id(operation_id, IdKind.OPERATION)
        if revision < 1:
            raise ValueError("revision must be >= 1")
        if idempotency_key is not None and not (1 <= len(idempotency_key) <= 200):
            raise ValueError("idempotency_key must be 1-200 characters")
        for source_ref in source_refs:
            if not source_ref or _RAW_PATH_VALUE.match(source_ref):
                raise ValueError("source_refs must not contain empty or environment-dependent raw paths")
        for checksum in input_checksums:
            validate_sha256(checksum, field_name="manifest input checksum")
        _assert_safe(payload)
        ext = dict(extensions or {})
        _assert_safe(ext, "extensions")
        payload_bytes = canonical_json_bytes(payload)
        extension_bytes = canonical_json_bytes(ext)
        return cls(
            schema_id=schema_id,
            schema_version=schema_version,
            manifest_id=generate_id(IdKind.MANIFEST),
            production_job_id=production_job_id,
            revision=revision,
            created_at=created_at or utc_now_iso(),
            producer=producer,
            profile_snapshot_id=profile_snapshot_id,
            source_refs=tuple(source_refs),
            input_checksums=tuple(input_checksums),
            content_checksum=sha256_bytes(payload_bytes),
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            _payload_json=payload_bytes.decode("utf-8"),
            _extensions_json=extension_bytes.decode("utf-8"),
        )

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)

    @property
    def extensions(self) -> dict[str, Any]:
        return json.loads(self._extensions_json)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "production_job_id": self.production_job_id,
            "revision": self.revision,
            "created_at": self.created_at,
            "producer": self.producer.to_dict(),
            "profile_snapshot_id": self.profile_snapshot_id,
            "source_refs": list(self.source_refs),
            "input_checksums": list(self.input_checksums),
            "content_checksum": self.content_checksum,
            "payload": self.payload,
            "extensions": self.extensions,
        }
        if self.operation_id is not None:
            result["operation_id"] = self.operation_id
        if self.idempotency_key is not None:
            result["idempotency_key"] = self.idempotency_key
        return result
