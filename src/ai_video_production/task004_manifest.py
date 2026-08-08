from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter
from .evidence import EvidenceRecord, EvidenceWriter
from .errors import ProductError, ProductErrorCategory
from .manifest import ManifestEnvelope, Producer
from .paths import LogicalPathResolver
from .schema_contracts import validate_instance
from .serialization import sha256_bytes, sha256_json
from .store import ManifestRecord, SQLiteProductStore

_TASK004_VERSION = "0.4.0"


@dataclass(frozen=True, slots=True)
class Task004ManifestResult:
    manifest: ManifestRecord
    evidence_uri: str


class Task004ManifestWriter:
    def __init__(self, *, store: SQLiteProductStore, resolver: LogicalPathResolver) -> None:
        self.store = store
        self.resolver = resolver

    @staticmethod
    def _schema(name: str) -> dict[str, Any]:
        return json.loads(resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8"))

    def _validate(self, value: dict[str, Any]) -> None:
        validate_instance(value, self._schema("canonical-manifest-envelope.schema.json"))
        validate_instance(value["payload"], self._schema("task004-operation-manifest-payload.schema.json"))

    def load_verified(self, manifest: ManifestRecord) -> dict[str, Any]:
        path = self.resolver.resolve(manifest.uri)
        if not isinstance(path, Path) or not path.exists() or path.is_symlink():
            raise ProductError("ERR_INTEGRITY_TASK004_MANIFEST_MISSING", "TASK-004 committed manifest file is missing or symlinked", ProductErrorCategory.DATA_INTEGRITY)
        raw = path.read_bytes()
        checksum = sha256_bytes(raw.rstrip(b"\n"))
        if checksum != manifest.checksum:
            raise ProductError("ERR_INTEGRITY_TASK004_MANIFEST_CHECKSUM", "TASK-004 committed manifest checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ProductError("ERR_INTEGRITY_TASK004_MANIFEST_FORMAT", "TASK-004 committed manifest must be an object", ProductErrorCategory.DATA_INTEGRITY)
        self._validate(value)
        return value

    def _ensure_evidence(
        self, *, job_id: str, operation_id: str, evidence_category: str, producer_component: str,
        input_checksums: tuple[str, ...], output_assets: tuple[Any, ...], details: dict[str, Any],
        committed: ManifestRecord, operation_kind: str, lane: str,
    ) -> str:
        evidence_uri = f"job://{job_id}/evidence/task004.jsonl"
        evidence_path = self.resolver.resolve(evidence_uri)
        assert isinstance(evidence_path, Path)
        if self.store.has_evidence_for_operation(operation_id, evidence_category):
            return evidence_uri
        writer = EvidenceWriter(evidence_path)
        for existing in writer.iter_records():
            if existing.get("operation_id") == operation_id and existing.get("category") == evidence_category:
                try:
                    self.store.register_evidence_index(
                        evidence_id=existing["evidence_id"], job_id=job_id, category=evidence_category, uri=evidence_uri,
                        checksum=sha256_json(existing), operation_id=operation_id, created_at=existing["created_at"],
                    )
                except Exception:
                    if not self.store.has_evidence_for_operation(operation_id, evidence_category):
                        raise
                return evidence_uri
        record = EvidenceRecord(
            production_job_id=job_id, category=evidence_category, producer=f"{producer_component}/{_TASK004_VERSION}",
            operation_id=operation_id, input_checksums=input_checksums,
            output_checksums=tuple(a.checksum for a in output_assets) + (committed.checksum,),
            details={
                "lane": lane, "operation_kind": operation_kind, "manifest_id": committed.manifest_id,
                "manifest_uri": committed.uri, "output_asset_ids": [a.asset_id for a in output_assets], **details,
            },
        )
        writer.append(record)
        try:
            self.store.register_evidence_index(
                evidence_id=record.evidence_id, job_id=job_id, category=record.category, uri=evidence_uri,
                checksum=sha256_json(record.to_dict()), operation_id=operation_id, created_at=record.created_at,
            )
        except Exception:
            if not self.store.has_evidence_for_operation(operation_id, evidence_category):
                raise
        return evidence_uri

    def write(
        self,
        *,
        job_id: str,
        operation_id: str,
        manifest_type: str,
        schema_id: str,
        lane: str,
        operation_kind: str,
        source_refs: tuple[str, ...],
        input_checksums: tuple[str, ...],
        output_assets: tuple[Any, ...],
        details: dict[str, Any],
        evidence_category: str,
        producer_component: str,
    ) -> Task004ManifestResult:
        prior = self.store.find_manifest_by_operation(operation_id, manifest_type)
        if prior is not None:
            self.load_verified(prior)
            evidence_uri = self._ensure_evidence(
                job_id=job_id, operation_id=operation_id, evidence_category=evidence_category, producer_component=producer_component,
                input_checksums=input_checksums, output_assets=output_assets, details=details, committed=prior,
                operation_kind=operation_kind, lane=lane,
            )
            return Task004ManifestResult(prior, evidence_uri)
        snapshot = self.store.get_job_state(job_id)
        reservation = self.store.reserve_manifest(
            job_id=job_id,
            manifest_type=manifest_type,
            schema_version="1.0.0",
            operation_id=operation_id,
            uri_pattern=f"job://{job_id}/manifests/{manifest_type}/v{{version:06d}}.json",
        )
        payload = {
            "lane": lane,
            "operation_kind": operation_kind,
            "output_assets": [a.to_dict() for a in output_assets],
            "details": details,
        }
        envelope = ManifestEnvelope.create(
            schema_id=schema_id,
            schema_version="1.0.0",
            production_job_id=job_id,
            revision=reservation.version,
            producer=Producer(producer_component, _TASK004_VERSION),
            profile_snapshot_id=snapshot.profile_snapshot_id,
            payload=payload,
            source_refs=source_refs,
            input_checksums=input_checksums,
            operation_id=operation_id,
            idempotency_key=self.store.get_operation(operation_id).idempotency_key,
            manifest_id=reservation.manifest_id,
        )
        path = self.resolver.resolve(reservation.uri)
        assert isinstance(path, Path)
        try:
            written = AtomicJsonWriter.write(path, envelope.to_dict(), validator=self._validate)
            committed = self.store.finalize_manifest(reservation.manifest_id, written.checksum)
        except Exception:
            self.store.fail_manifest(reservation.manifest_id)
            raise

        evidence_uri = self._ensure_evidence(
            job_id=job_id, operation_id=operation_id, evidence_category=evidence_category, producer_component=producer_component,
            input_checksums=input_checksums, output_assets=output_assets, details=details, committed=committed,
            operation_kind=operation_kind, lane=lane,
        )
        return Task004ManifestResult(committed, evidence_uri)
