from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from importlib import resources
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Protocol

from .assets import (
    ApprovedSegment,
    AssetRecord,
    AssetType,
    AudioRightsStatus,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .evidence import EvidenceRecord, EvidenceWriter
from .manifest import ManifestEnvelope, Producer
from .media_probe import FFprobeMediaProbe, MediaProbeResult
from .paths import LogicalPathResolver, SourcePathPolicy
from .schema_contracts import validate_instance
from .serialization import canonical_json_bytes, sha256_bytes, sha256_json
from .state import JobStateService, ProductionJobState
from .store import ManifestRecord, OperationRecord, SQLiteProductStore

_INGEST_VERSION = "0.3.1"
_SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,10}$")
_PROBE_TYPES = {
    AssetType.VIDEO,
    AssetType.AUDIO,
    AssetType.IMAGE,
    AssetType.BGM,
    AssetType.SFX,
    AssetType.GENERATED_VIDEO,
}
FailureInjector = Callable[[str, Path], None]


class MediaProbe(Protocol):
    def probe(self, path: str | Path) -> MediaProbeResult: ...
    def assert_compatible(self, asset_type: AssetType, result: MediaProbeResult) -> None: ...


@dataclass(frozen=True, slots=True)
class AssetIngestRequest:
    production_job_id: str
    source_path: Path
    asset_type: AssetType
    rights_status: RightsStatus
    owner: str
    idempotency_key: str
    retention_class: RetentionClass = RetentionClass.STANDARD
    human_lock: bool = False
    commercial_use: PermissionState = PermissionState.UNKNOWN
    derivative_allowed: PermissionState = PermissionState.UNKNOWN
    reuse_allowed: PermissionState = PermissionState.ALLOWED
    audio_rights_status: AudioRightsStatus = AudioRightsStatus.NOT_APPLICABLE
    source_ref: str | None = None
    source_project: str | None = None
    attribution: str | None = None
    territory: tuple[str, ...] = ()
    rights_valid_until: str | None = None
    publication_restrictions: tuple[str, ...] = ()
    approved_segments: tuple[ApprovedSegment, ...] = ()
    generation_provenance: dict[str, Any] = field(default_factory=dict)
    perceptual_hash: str | None = None
    audio_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.idempotency_key or len(self.idempotency_key) > 200:
            raise ValueError("idempotency_key must be 1-200 characters")
        if not self.owner.strip():
            raise ValueError("owner must be non-empty")


@dataclass(frozen=True, slots=True)
class AssetIngestResult:
    asset: AssetRecord
    operation: OperationRecord
    source_manifest_uri: str
    source_manifest_checksum: str
    evidence_uri: str
    deduplicated: bool
    repaired_existing_file: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset.to_dict(),
            "operation_id": self.operation.operation_id,
            "operation_status": self.operation.status,
            "source_manifest_uri": self.source_manifest_uri,
            "source_manifest_checksum": self.source_manifest_checksum,
            "evidence_uri": self.evidence_uri,
            "deduplicated": self.deduplicated,
            "repaired_existing_file": self.repaired_existing_file,
        }


class AssetIngestService:
    """Secure, idempotent source-asset ingest boundary.

    The raw source path exists only at this boundary. Canonical state stores a
    Logical URI and checksums, never a machine-specific source path.
    """

    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        source_policy: SourcePathPolicy,
        media_probe: MediaProbe | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.source_policy = source_policy
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.failure_injector = failure_injector

    def _inject(self, stage: str, path: Path) -> None:
        if self.failure_injector:
            self.failure_injector(stage, path)

    @staticmethod
    def _suffix(path: Path) -> str:
        suffix = path.suffix.lower()
        return suffix if _SAFE_SUFFIX.fullmatch(suffix) else ".bin"

    @staticmethod
    def _directory_fsync(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    @staticmethod
    def _make_read_only(path: Path) -> None:
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

    @staticmethod
    def _make_owner_writable(path: Path) -> None:
        try:
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
        except OSError:
            pass

    @staticmethod
    def _hash_open_source_fd(source_fd: int) -> tuple[str, int]:
        """Re-hash an already opened regular file without reopening its path."""
        os.lseek(source_fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        counted = 0
        while True:
            chunk = os.read(source_fd, 4 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            counted += len(chunk)
        return "sha256:" + digest.hexdigest(), counted

    def _copy_to_target_local_stage(self, source: Path, operation_id: str, job_id: str) -> tuple[Path, str, int]:
        staging_uri = f"asset://{job_id}/.staging/{operation_id}.part"
        staging = self.resolver.resolve(staging_uri)
        assert isinstance(staging, Path)
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.unlink(missing_ok=True)

        # Windows CRT file descriptors default to translated text mode unless
        # O_BINARY is requested. Binary media commonly contains 0x1A (CTRL+Z),
        # which text mode interprets as EOF; always opt into untranslated mode.
        binary_flag = getattr(os, "O_BINARY", 0)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | binary_flag
        source_fd = os.open(source, flags)
        try:
            before = os.fstat(source_fd)
            if not stat.S_ISREG(before.st_mode):
                raise ProductError("ERR_INPUT_SOURCE_NOT_FILE", "ingest source must be a regular file", ProductErrorCategory.VALIDATION)
            out_fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | binary_flag, 0o600)
            digest = hashlib.sha256()
            copied = 0
            try:
                while True:
                    chunk = os.read(source_fd, 4 * 1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    view = memoryview(chunk)
                    while view:
                        written = os.write(out_fd, view)
                        if written <= 0:
                            raise OSError("short staged asset write")
                        view = view[written:]
                    copied += len(chunk)
                os.fsync(out_fd)
            finally:
                os.close(out_fd)

            after = os.fstat(source_fd)
            checksum = "sha256:" + digest.hexdigest()

            # Size drift is always a hard integrity failure.  A last-write-time
            # drift alone is not sufficient proof of content mutation on all
            # filesystems (notably Windows immediately after a producer closes
            # a file), so revalidate the bytes through the *same opened handle*.
            if before.st_size != after.st_size or copied != after.st_size:
                raise ProductError(
                    "ERR_INPUT_SOURCE_CHANGED_DURING_INGEST",
                    "source file changed while it was being ingested",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={
                        "reason": "SIZE_CHANGED",
                        "before_size": before.st_size,
                        "after_size": after.st_size,
                        "copied_size": copied,
                    },
                )

            if before.st_mtime_ns != after.st_mtime_ns:
                verify_before = os.fstat(source_fd)
                verification_checksum, verification_size = self._hash_open_source_fd(source_fd)
                verify_after = os.fstat(source_fd)
                if (
                    verify_before.st_size != verify_after.st_size
                    or verification_size != copied
                    or verify_after.st_size != copied
                    or verification_checksum != checksum
                ):
                    raise ProductError(
                        "ERR_INPUT_SOURCE_CHANGED_DURING_INGEST",
                        "source file changed while it was being ingested",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={
                            "reason": "CONTENT_REVALIDATION_MISMATCH",
                            "before_size": before.st_size,
                            "after_size": after.st_size,
                            "copied_size": copied,
                            "verification_size": verification_size,
                            "before_mtime_ns": before.st_mtime_ns,
                            "after_mtime_ns": after.st_mtime_ns,
                        },
                    )
        except Exception:
            staging.unlink(missing_ok=True)
            raise
        finally:
            os.close(source_fd)

        if copied == 0:
            staging.unlink(missing_ok=True)
            raise ProductError(
                "ERR_INPUT_EMPTY_ASSET",
                "empty files are not accepted as source assets",
                ProductErrorCategory.VALIDATION,
            )
        self._inject("after_stage_copy", staging)
        return staging, checksum, copied

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        return "sha256:" + digest.hexdigest()

    @staticmethod
    def _duplicate_metadata_conflicts(existing: AssetRecord, request: AssetIngestRequest) -> list[str]:
        requested = {
            "asset_type": request.asset_type.value,
            "rights_status": request.rights_status.value,
            "owner": request.owner,
            "retention_class": request.retention_class.value,
            "human_lock": request.human_lock,
            "commercial_use": request.commercial_use.value,
            "derivative_allowed": request.derivative_allowed.value,
            "reuse_allowed": request.reuse_allowed.value,
            "audio_rights_status": request.audio_rights_status.value,
        }
        current = {
            "asset_type": existing.asset_type.value,
            "rights_status": existing.rights_status.value,
            "owner": existing.owner,
            "retention_class": existing.retention_class.value,
            "human_lock": existing.human_lock,
            "commercial_use": existing.commercial_use.value,
            "derivative_allowed": existing.derivative_allowed.value,
            "reuse_allowed": existing.reuse_allowed.value,
            "audio_rights_status": existing.audio_rights_status.value,
        }
        return [key for key, value in requested.items() if current[key] != value]

    def _assert_ingest_state(self, job_id: str):
        snapshot = self.store.get_job_state(job_id)
        if snapshot.state not in {ProductionJobState.CREATED, ProductionJobState.INGESTING}:
            raise ProductError(
                "ERR_STATE_INGEST_NOT_ALLOWED",
                f"source ingest is not allowed while job state is {snapshot.state.value}",
                ProductErrorCategory.STATE,
            )
        return snapshot

    def _schema(self, name: str) -> dict[str, Any]:
        return json.loads(resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8"))

    def _validate_source_manifest(self, value: dict[str, Any]) -> None:
        validate_instance(value, self._schema("canonical-manifest-envelope.schema.json"))
        validate_instance(value["payload"], self._schema("source-manifest-payload.schema.json"))

    def _write_source_manifest(self, job_id: str, operation_id: str) -> tuple[str, str]:
        snapshot = self.store.get_job_state(job_id)
        # Reserve the monotonically increasing revision before taking the Asset
        # snapshot. This prevents a higher revision from being built from an
        # older pre-reservation snapshot during concurrent Ingest operations.
        reservation = self.store.reserve_manifest(
            job_id=job_id,
            manifest_type="source-manifest",
            schema_version="1.0.0",
            operation_id=operation_id,
            uri_pattern=f"job://{job_id}/manifests/source-manifest/v{{version:06d}}.json",
        )
        assets = tuple(
            asset for asset in self.store.list_assets(job_id)
            if asset.logical_uri.startswith(f"asset://{job_id}/source/")
        )
        payload = {
            "asset_count": len(assets),
            "assets": [asset.to_dict() for asset in assets],
            "rights_review_asset_ids": [asset.asset_id for asset in assets if asset.rights_review_required],
        }
        envelope = ManifestEnvelope.create(
            schema_id="ai-video.source-manifest",
            schema_version="1.0.0",
            production_job_id=job_id,
            revision=reservation.version,
            producer=Producer("asset-ingest-service", _INGEST_VERSION),
            profile_snapshot_id=snapshot.profile_snapshot_id,
            payload=payload,
            source_refs=tuple(asset.logical_uri for asset in assets),
            input_checksums=tuple(asset.checksum for asset in assets),
            operation_id=operation_id,
            idempotency_key=self.store.get_operation(operation_id).idempotency_key,
            manifest_id=reservation.manifest_id,
        )
        latest_uri = f"job://{job_id}/manifests/source-manifest.json"
        versioned_path = self.resolver.resolve(reservation.uri)
        latest_path = self.resolver.resolve(latest_uri)
        assert isinstance(versioned_path, Path) and isinstance(latest_path, Path)
        try:
            self._inject("before_manifest_write", versioned_path)
            versioned = AtomicJsonWriter.write(versioned_path, envelope.to_dict(), validator=self._validate_source_manifest)
            self._inject("after_manifest_write", versioned_path)
            committed = self.store.finalize_manifest(reservation.manifest_id, versioned.checksum)
        except Exception:
            self.store.fail_manifest(reservation.manifest_id)
            raise

        # source-manifest.json is a derived convenience pointer. Only the
        # highest committed revision may update it, so concurrent older writers
        # cannot roll the pointer backwards.
        with exclusive_file_update_lock(latest_path):
            latest = self.store.latest_manifest(job_id, "source-manifest")
            if latest is not None and latest.manifest_id == committed.manifest_id:
                AtomicJsonWriter.write(latest_path, envelope.to_dict(), validator=self._validate_source_manifest)
        return reservation.uri, versioned.checksum

    def _write_evidence(
        self,
        *,
        job_id: str,
        operation_id: str,
        asset: AssetRecord,
        manifest_checksum: str,
        deduplicated: bool,
        repaired_existing_file: bool,
    ) -> str:
        evidence_uri = f"job://{job_id}/evidence/ingest.jsonl"
        evidence_path = self.resolver.resolve(evidence_uri)
        assert isinstance(evidence_path, Path)
        record = EvidenceRecord(
            production_job_id=job_id,
            category="ASSET_INGEST",
            producer=f"asset-ingest-service/{_INGEST_VERSION}",
            operation_id=operation_id,
            input_checksums=(asset.checksum,),
            output_checksums=(asset.checksum, manifest_checksum),
            details={
                "asset_id": asset.asset_id,
                "logical_uri": asset.logical_uri,
                "asset_type": asset.asset_type.value,
                "original_name": asset.original_name,
                "rights_status": asset.rights_status.value,
                "rights_review_required": asset.rights_review_required,
                "deduplicated": deduplicated,
                "repaired_existing_file": repaired_existing_file,
                "media_metadata": asset.media_metadata,
            },
        )
        EvidenceWriter(evidence_path).append(record)
        self.store.register_evidence_index(
            evidence_id=record.evidence_id,
            job_id=job_id,
            category=record.category,
            uri=evidence_uri,
            checksum=sha256_json(record.to_dict()),
            operation_id=operation_id,
            created_at=record.created_at,
        )
        return evidence_uri

    def _repair_manifest_only(self, operation: OperationRecord, asset: AssetRecord) -> AssetIngestResult:
        try:
            target = self.resolver.resolve(asset.logical_uri)
            if not isinstance(target, Path) or not target.exists():
                raise ProductError(
                    "ERR_INTEGRITY_REGISTERED_ASSET_MISSING",
                    "cannot repair ingest metadata because the registered asset file is missing",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"asset_id": asset.asset_id},
                )
            if self._hash_file(target) != asset.checksum:
                raise ProductError(
                    "ERR_INTEGRITY_REGISTERED_ASSET_CHECKSUM_MISMATCH",
                    "cannot repair ingest metadata because the registered asset checksum no longer matches",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"asset_id": asset.asset_id},
                )
            manifest_uri, manifest_checksum = self._write_source_manifest(asset.production_job_id, operation.operation_id)
            evidence_uri = self._write_evidence(
                job_id=asset.production_job_id,
                operation_id=operation.operation_id,
                asset=asset,
                manifest_checksum=manifest_checksum,
                deduplicated=True,
                repaired_existing_file=False,
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=asset.asset_id)
            return AssetIngestResult(asset, operation, manifest_uri, manifest_checksum, evidence_uri, True, False)
        except Exception as exc:
            code = exc.code if isinstance(exc, ProductError) else "ERR_INTERNAL_ASSET_INGEST_REPAIR_FAILED"
            self.store.update_operation_status(
                operation.operation_id,
                "PARTIAL",
                last_error_code=code,
                result_ref=asset.asset_id,
            )
            if isinstance(exc, ProductError):
                raise
            raise ProductError(
                "ERR_INTERNAL_ASSET_INGEST_REPAIR_FAILED",
                "asset ingest metadata repair failed unexpectedly",
                ProductErrorCategory.INTERNAL,
                retryable=True,
                operation_id=operation.operation_id,
            ) from exc

    def ingest(self, request: AssetIngestRequest) -> AssetIngestResult:
        operation, _created = self.store.reserve_operation(request.production_job_id, "ASSET_INGEST", request.idempotency_key)
        # Idempotent replay and repair are valid even after the Job has advanced
        # beyond INGESTING; they do not ingest a new source or mutate the source
        # Asset bytes.
        if operation.status == "COMPLETED" and operation.result_ref:
            asset = self.store.get_asset(operation.result_ref)
            latest = self.store.latest_manifest(request.production_job_id, "source-manifest")
            if latest is None:
                return self._repair_manifest_only(operation, asset)
            return AssetIngestResult(
                asset,
                operation,
                latest.uri,
                latest.checksum,
                f"job://{request.production_job_id}/evidence/ingest.jsonl",
                True,
                False,
            )
        if operation.status == "PARTIAL" and operation.result_ref:
            return self._repair_manifest_only(operation, self.store.get_asset(operation.result_ref))
        # Hard-process failure may occur after Asset Registry commit but before
        # operation.result_ref/status is updated. asset_versions retains the
        # producer operation binding, allowing source-free manifest/evidence
        # repair on the next idempotent replay.
        bound_asset = self.store.find_asset_by_operation(operation.operation_id)
        if bound_asset is not None:
            return self._repair_manifest_only(operation, bound_asset)

        staging: Path | None = None
        target: Path | None = None
        target_created = False
        asset_registered = False
        asset: AssetRecord | None = None
        deduplicated = False
        repaired_existing_file = False

        try:
            snapshot = self._assert_ingest_state(request.production_job_id)
            # Authorization of the raw source path happens before changing the
            # Product Job state, so a denied path has zero Job-state side effect.
            source = self.source_policy.authorize_file(request.source_path)
            if snapshot.state is ProductionJobState.CREATED:
                JobStateService(self.store).transition(
                    request.production_job_id,
                    ProductionJobState.INGESTING,
                    expected_version=snapshot.state_version,
                )
            operation = self.store.update_operation_status(operation.operation_id, "IN_PROGRESS", increment_attempt=True)
            original_name = source.name
            staging, checksum, copied = self._copy_to_target_local_stage(
                source,
                operation.operation_id,
                request.production_job_id,
            )
            probe_result: MediaProbeResult | None = None
            if request.asset_type in _PROBE_TYPES:
                probe_result = self.media_probe.probe(staging)
                self.media_probe.assert_compatible(request.asset_type, probe_result)
            self._inject("after_probe", staging)

            existing = self.store.find_asset_by_checksum(request.production_job_id, checksum)
            if existing is not None:
                conflicts = self._duplicate_metadata_conflicts(existing, request)
                if conflicts:
                    raise ProductError(
                        "ERR_POLICY_DUPLICATE_RIGHTS_CONFLICT",
                        "duplicate bytes already exist with different rights/classification metadata",
                        ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                        details={"asset_id": existing.asset_id, "conflicting_fields": conflicts},
                    )
                target = self.resolver.resolve(existing.logical_uri)
                assert isinstance(target, Path)
                if target.exists():
                    if self._hash_file(target) != checksum:
                        raise ProductError(
                            "ERR_INTEGRITY_REGISTERED_ASSET_CHECKSUM_MISMATCH",
                            "registered asset file does not match its canonical checksum",
                            ProductErrorCategory.DATA_INTEGRITY,
                        )
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staging, target)
                    staging = None
                    self._make_read_only(target)
                    self._directory_fsync(target.parent)
                    repaired_existing_file = True
                asset = existing
                deduplicated = True
            else:
                suffix = self._suffix(source)
                hash_hex = checksum.removeprefix("sha256:")
                logical_uri = f"asset://{request.production_job_id}/source/{hash_hex}{suffix}"
                self.resolver.assert_job_scope(logical_uri, request.production_job_id)
                target = self.resolver.resolve(logical_uri)
                assert isinstance(target, Path)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if self._hash_file(target) != checksum:
                        raise ProductError(
                            "ERR_INTEGRITY_INGEST_TARGET_COLLISION",
                            "deterministic ingest target exists with a different checksum",
                            ProductErrorCategory.DATA_INTEGRITY,
                        )
                    staging.unlink(missing_ok=True)
                    staging = None
                    repaired_existing_file = True
                else:
                    os.replace(staging, target)
                    staging = None
                    target_created = True
                    self._directory_fsync(target.parent)
                self._make_read_only(target)
                self._inject("after_promote_before_registry", target)

                metadata = probe_result.to_dict() if probe_result else {"size_bytes": copied, "probe": "NOT_REQUIRED"}
                asset = AssetRecord(
                    production_job_id=request.production_job_id,
                    asset_type=request.asset_type,
                    logical_uri=logical_uri,
                    checksum=checksum,
                    rights_status=request.rights_status,
                    owner=request.owner,
                    retention_class=request.retention_class,
                    human_lock=request.human_lock,
                    generation_provenance=dict(request.generation_provenance),
                    original_name=original_name,
                    commercial_use=request.commercial_use,
                    derivative_allowed=request.derivative_allowed,
                    reuse_allowed=request.reuse_allowed,
                    audio_rights_status=request.audio_rights_status,
                    source_ref=request.source_ref,
                    source_project=request.source_project,
                    attribution=request.attribution,
                    territory=request.territory,
                    rights_valid_until=request.rights_valid_until,
                    publication_restrictions=request.publication_restrictions,
                    approved_segments=request.approved_segments,
                    media_metadata=metadata,
                    perceptual_hash=request.perceptual_hash,
                    audio_fingerprint=request.audio_fingerprint,
                )
                try:
                    self.store.register_asset(asset, producer_operation_id=operation.operation_id)
                    asset_registered = True
                except ProductError as exc:
                    if exc.code != "ERR_INTEGRITY_ASSET_REGISTRY_CONFLICT":
                        raise
                    concurrent = self.store.find_asset_by_checksum(request.production_job_id, checksum)
                    if concurrent is None:
                        raise
                    conflicts = self._duplicate_metadata_conflicts(concurrent, request)
                    if conflicts:
                        raise ProductError(
                            "ERR_POLICY_DUPLICATE_RIGHTS_CONFLICT",
                            "concurrent duplicate ingest produced a rights/classification conflict",
                            ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                            details={"asset_id": concurrent.asset_id, "conflicting_fields": conflicts},
                        ) from exc
                    asset = concurrent
                    deduplicated = True
                    asset_registered = True

            assert asset is not None
            manifest_uri, manifest_checksum = self._write_source_manifest(request.production_job_id, operation.operation_id)
            evidence_uri = self._write_evidence(
                job_id=request.production_job_id,
                operation_id=operation.operation_id,
                asset=asset,
                manifest_checksum=manifest_checksum,
                deduplicated=deduplicated,
                repaired_existing_file=repaired_existing_file,
            )
            operation = self.store.update_operation_status(
                operation.operation_id,
                "COMPLETED",
                result_ref=asset.asset_id,
            )
            return AssetIngestResult(
                asset,
                operation,
                manifest_uri,
                manifest_checksum,
                evidence_uri,
                deduplicated,
                repaired_existing_file,
            )
        except Exception as exc:
            if staging is not None:
                staging.unlink(missing_ok=True)
            if target_created and not asset_registered and target is not None and target.exists():
                self._make_owner_writable(target)
                target.unlink(missing_ok=True)
                self._directory_fsync(target.parent)
            result_ref = asset.asset_id if asset_registered and asset is not None else None
            code = exc.code if isinstance(exc, ProductError) else "ERR_INTERNAL_ASSET_INGEST_FAILED"
            status = "PARTIAL" if result_ref else "FAILED"
            self.store.update_operation_status(operation.operation_id, status, last_error_code=code, result_ref=result_ref)
            if isinstance(exc, ProductError):
                raise
            raise ProductError(
                "ERR_INTERNAL_ASSET_INGEST_FAILED",
                "asset ingest failed unexpectedly",
                ProductErrorCategory.INTERNAL,
                retryable=bool(result_ref),
                operation_id=operation.operation_id,
            ) from exc
