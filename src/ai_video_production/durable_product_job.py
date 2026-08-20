"""TASK-043 durable Product-local background and Export Queue job truth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path, PureWindowsPath
import re
from typing import Any, Mapping

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .desktop_shell import JobSnapshot, JobState as ShellJobState
from .errors import ProductError, ProductErrorCategory
from .product_project_store import ProductProjectManifestStore, _exclusive_project_lock, _manifest_path, _project_root
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso, validate_sha256


_STORE_VERSION = "1.0.0"
_MAX_STORE_BYTES = 16 * 1024 * 1024
_MAX_JOBS = 4096
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_KIND_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_LOCAL_JOB_KINDS = {"EXPORT", "LOCAL_ANALYSIS", "LOCAL_TRANSCODE", "MEDIA_INDEX", "PROJECT_MAINTENANCE"}
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_ERROR_RE = re.compile(r"^ERR_PRODUCT_JOB_[A-Z0-9_]+$")
_PRIVATE_TERMS = ("credential", "password", "secret", "token", "prompt-body", "private-key")


def _timestamp(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be a UTC ISO-8601 timestamp")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")
    return parsed


def _safe_public_identity(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or PureWindowsPath(value).drive
        or any(part == ".." for part in value.split("/"))
        or any(term in folded for term in _PRIVATE_TERMS)
    ):
        raise ValueError(f"{field_name} violates the public identity boundary")
    return value


class DurableProductJobState(str, Enum):
    QUEUED = "QUEUED"
    PREFLIGHT = "PREFLIGHT"
    READY = "READY"
    DISPATCHING = "DISPATCHING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


_TERMINAL = {
    DurableProductJobState.SUCCEEDED,
    DurableProductJobState.FAILED,
    DurableProductJobState.CANCELLED,
}


def _recovery_actions(state: DurableProductJobState) -> tuple[str, ...]:
    if state is DurableProductJobState.UNKNOWN:
        return ("ACCEPT_PROVEN_SUCCESS", "MARK_FAILED", "REQUIRE_HUMAN")
    if state is DurableProductJobState.HUMAN_REQUIRED:
        return ("CANCEL", "MARK_FAILED", "RESUME_PREFLIGHT")
    return ()


@dataclass(frozen=True, slots=True)
class DurableProductJob:
    job_id: str
    operation_identity: str
    kind: str
    target_identity: str
    input_hashes: tuple[tuple[str, str], ...]
    state: DurableProductJobState
    state_version: int
    attempt: int
    created_at: str
    updated_at: str
    unknown_since: str | None
    recovery_actions: tuple[str, ...]
    result_ref: str | None
    error_code: str | None
    estimated_cost: float | None
    currency: str | None
    estimate_source: str | None
    actual_cost: float | None
    job_sha256: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"product-job-[0-9a-f]{64}", self.job_id):
            raise ValueError("job_id is invalid")
        if not re.fullmatch(r"operation-[0-9a-f]{64}", self.operation_identity):
            raise ValueError("operation_identity is invalid")
        if not _KIND_RE.fullmatch(self.kind) or self.kind not in _LOCAL_JOB_KINDS:
            raise ValueError("kind is not an allowlisted Product-local job")
        _safe_public_identity(self.target_identity, "target_identity")
        if len(self.input_hashes) > 128 or tuple(sorted(set(self.input_hashes))) != self.input_hashes:
            raise ValueError("input_hashes must be unique, sorted and bounded")
        for name, checksum in self.input_hashes:
            _safe_public_identity(name, "input_hash name")
            validate_sha256(checksum, field_name="input_hash")
        if isinstance(self.state_version, bool) or not isinstance(self.state_version, int) or self.state_version < 1:
            raise ValueError("state_version must be positive")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 0:
            raise ValueError("attempt must be non-negative")
        created = _timestamp(self.created_at, "created_at")
        updated = _timestamp(self.updated_at, "updated_at")
        if updated < created:
            raise ValueError("updated_at precedes created_at")
        if self.unknown_since is not None:
            unknown = _timestamp(self.unknown_since, "unknown_since")
            if unknown < created or unknown > updated:
                raise ValueError("unknown_since is outside the job lifetime")
        if (self.state is DurableProductJobState.UNKNOWN) != (self.unknown_since is not None):
            raise ValueError("unknown_since must exist only for UNKNOWN")
        if self.recovery_actions != _recovery_actions(self.state):
            raise ValueError("recovery_actions do not match job state")
        if self.result_ref is not None:
            _safe_public_identity(self.result_ref, "result_ref")
        if self.state is DurableProductJobState.SUCCEEDED and self.result_ref is None:
            raise ValueError("SUCCEEDED requires result_ref")
        if self.state is not DurableProductJobState.SUCCEEDED and self.result_ref is not None:
            raise ValueError("result_ref is valid only for SUCCEEDED")
        if self.error_code is not None and not _ERROR_RE.fullmatch(self.error_code):
            raise ValueError("error_code is invalid")
        if self.state in {DurableProductJobState.FAILED, DurableProductJobState.UNKNOWN, DurableProductJobState.HUMAN_REQUIRED}:
            if self.error_code is None:
                raise ValueError("failure/unknown/human state requires error_code")
        elif self.error_code is not None:
            raise ValueError("error_code is invalid for this state")
        for value, name in ((self.estimated_cost, "estimated_cost"), (self.actual_cost, "actual_cost")):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise ValueError(f"{name} must be null or non-negative")
        if (self.currency is None) != (self.estimated_cost is None and self.actual_cost is None):
            raise ValueError("currency is required exactly when a cost is known")
        if self.currency is not None and not _CURRENCY_RE.fullmatch(self.currency):
            raise ValueError("currency is invalid")
        if self.estimate_source is not None:
            _safe_public_identity(self.estimate_source, "estimate_source")
        if self.estimated_cost is not None and self.estimate_source is None:
            raise ValueError("known estimated_cost requires estimate_source")
        expected_operation = _operation_identity(self.kind, self.target_identity, self.input_hashes)
        if self.operation_identity != expected_operation:
            raise ValueError("operation_identity does not match exact inputs")
        if self.job_id != "product-job-" + expected_operation.removeprefix("operation-"):
            raise ValueError("job_id does not match operation identity")
        validate_sha256(self.job_sha256, field_name="job_sha256")
        if self.job_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("job_sha256 does not match job body")

    @classmethod
    def create(
        cls, *, kind: str, target_identity: str, input_hashes: Mapping[str, str],
        estimated_cost: float | None = None, currency: str | None = None,
        estimate_source: str | None = None, created_at: str | None = None,
    ) -> "DurableProductJob":
        inputs = tuple(sorted(input_hashes.items()))
        operation = _operation_identity(kind, target_identity, inputs)
        now = created_at or utc_now_iso()
        values: dict[str, Any] = {
            "job_id": "product-job-" + operation.removeprefix("operation-"),
            "operation_identity": operation, "kind": kind, "target_identity": target_identity,
            "input_hashes": inputs, "state": DurableProductJobState.QUEUED,
            "state_version": 1, "attempt": 0, "created_at": now, "updated_at": now,
            "unknown_since": None, "recovery_actions": (), "result_ref": None,
            "error_code": None, "estimated_cost": estimated_cost, "currency": currency,
            "estimate_source": estimate_source, "actual_cost": None,
        }
        return _job(**values)

    def transition(
        self, state: DurableProductJobState, *, result_ref: str | None = None,
        error_code: str | None = None, actual_cost: float | None = None,
        recovery_action: str | None = None, updated_at: str | None = None,
    ) -> "DurableProductJob":
        allowed = {
            DurableProductJobState.QUEUED: {DurableProductJobState.PREFLIGHT, DurableProductJobState.CANCELLED},
            DurableProductJobState.PREFLIGHT: {DurableProductJobState.READY, DurableProductJobState.FAILED, DurableProductJobState.HUMAN_REQUIRED, DurableProductJobState.CANCELLED},
            DurableProductJobState.READY: {DurableProductJobState.DISPATCHING, DurableProductJobState.CANCELLED},
            DurableProductJobState.DISPATCHING: {DurableProductJobState.RUNNING, DurableProductJobState.SUCCEEDED, DurableProductJobState.FAILED, DurableProductJobState.UNKNOWN, DurableProductJobState.HUMAN_REQUIRED},
            DurableProductJobState.RUNNING: {DurableProductJobState.SUCCEEDED, DurableProductJobState.FAILED, DurableProductJobState.UNKNOWN, DurableProductJobState.HUMAN_REQUIRED},
            DurableProductJobState.UNKNOWN: {DurableProductJobState.SUCCEEDED, DurableProductJobState.FAILED, DurableProductJobState.HUMAN_REQUIRED},
            DurableProductJobState.HUMAN_REQUIRED: {DurableProductJobState.PREFLIGHT, DurableProductJobState.FAILED, DurableProductJobState.CANCELLED},
            DurableProductJobState.SUCCEEDED: set(), DurableProductJobState.FAILED: set(), DurableProductJobState.CANCELLED: set(),
        }
        if state not in allowed[self.state]:
            raise ProductError("ERR_PRODUCT_JOB_TRANSITION", "Durable Product job transition is invalid", ProductErrorCategory.STATE)
        required_action: str | None = None
        if self.state is DurableProductJobState.UNKNOWN:
            required_action = {
                DurableProductJobState.SUCCEEDED: "ACCEPT_PROVEN_SUCCESS",
                DurableProductJobState.FAILED: "MARK_FAILED",
                DurableProductJobState.HUMAN_REQUIRED: "REQUIRE_HUMAN",
            }[state]
        elif self.state is DurableProductJobState.HUMAN_REQUIRED:
            required_action = {
                DurableProductJobState.PREFLIGHT: "RESUME_PREFLIGHT",
                DurableProductJobState.FAILED: "MARK_FAILED",
                DurableProductJobState.CANCELLED: "CANCEL",
            }[state]
        if recovery_action != required_action:
            code = "ERR_PRODUCT_JOB_RECOVERY_ACTION_REQUIRED" if required_action else "ERR_PRODUCT_JOB_RECOVERY_ACTION_INVALID"
            raise ProductError(code, "Durable Product job recovery action does not match the transition", ProductErrorCategory.AUTHORIZATION)
        now = updated_at or utc_now_iso()
        values = {
            "job_id": self.job_id, "operation_identity": self.operation_identity,
            "kind": self.kind, "target_identity": self.target_identity, "input_hashes": self.input_hashes,
            "state": state, "state_version": self.state_version + 1,
            "attempt": self.attempt + (1 if state is DurableProductJobState.DISPATCHING else 0),
            "created_at": self.created_at, "updated_at": now,
            "unknown_since": now if state is DurableProductJobState.UNKNOWN else None,
            "recovery_actions": _recovery_actions(state), "result_ref": result_ref,
            "error_code": error_code, "estimated_cost": self.estimated_cost,
            "currency": self.currency, "estimate_source": self.estimate_source,
            "actual_cost": actual_cost if state in _TERMINAL else None,
        }
        return _job(**values)

    def _body(self) -> dict[str, object]:
        return _job_body(
            job_id=self.job_id, operation_identity=self.operation_identity, kind=self.kind,
            target_identity=self.target_identity, input_hashes=self.input_hashes, state=self.state,
            state_version=self.state_version, attempt=self.attempt, created_at=self.created_at,
            updated_at=self.updated_at, unknown_since=self.unknown_since,
            recovery_actions=self.recovery_actions, result_ref=self.result_ref,
            error_code=self.error_code, estimated_cost=self.estimated_cost,
            currency=self.currency, estimate_source=self.estimate_source, actual_cost=self.actual_cost,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "job_sha256": self.job_sha256}


def _operation_identity(kind: str, target_identity: str, input_hashes: tuple[tuple[str, str], ...]) -> str:
    body = {"kind": kind, "target_identity": target_identity, "input_hashes": dict(input_hashes)}
    return "operation-" + sha256_bytes(canonical_json_bytes(body)).split(":", 1)[1]


def _job(**values: Any) -> DurableProductJob:
    body = _job_body(**values)
    return DurableProductJob(**values, job_sha256=sha256_bytes(canonical_json_bytes(body)))


def _job_body(**values: Any) -> dict[str, object]:
    return {
        "job_id": values["job_id"], "operation_identity": values["operation_identity"],
        "kind": values["kind"], "target_identity": values["target_identity"],
        "input_hashes": dict(values["input_hashes"]),
        "state": values["state"].value if isinstance(values["state"], DurableProductJobState) else values["state"],
        "state_version": values["state_version"], "attempt": values["attempt"],
        "created_at": values["created_at"], "updated_at": values["updated_at"],
        "unknown_since": values["unknown_since"], "recovery_actions": list(values["recovery_actions"]),
        "result_ref": values["result_ref"], "error_code": values["error_code"],
        "estimated_cost": values["estimated_cost"], "currency": values["currency"],
        "estimate_source": values["estimate_source"], "actual_cost": values["actual_cost"],
        "authority": {"provider_execution_authorized": False, "paid_execution_authorized": False, "external_replay_authorized": False},
    }


@dataclass(frozen=True, slots=True)
class DurableProductJobCollection:
    project_id: str
    store_revision: int
    jobs: tuple[DurableProductJob, ...]
    jobs_sha256: str

    def __post_init__(self) -> None:
        _safe_public_identity(self.project_id, "project_id")
        if isinstance(self.store_revision, bool) or not isinstance(self.store_revision, int) or self.store_revision < 1:
            raise ValueError("store_revision must be positive")
        if len(self.jobs) > _MAX_JOBS or tuple(sorted(self.jobs, key=lambda job: job.job_id)) != self.jobs:
            raise ValueError("jobs must be sorted and bounded")
        if len({job.job_id for job in self.jobs}) != len(self.jobs):
            raise ValueError("jobs contain duplicate identity")
        validate_sha256(self.jobs_sha256, field_name="jobs_sha256")
        if self.jobs_sha256 != sha256_bytes(canonical_json_bytes(self._body())):
            raise ValueError("jobs_sha256 does not match store body")

    @classmethod
    def create(cls, project_id: str) -> "DurableProductJobCollection":
        body = _collection_body(project_id, 1, ())
        return cls(project_id, 1, (), sha256_bytes(canonical_json_bytes(body)))

    def replace(self, job: DurableProductJob) -> "DurableProductJobCollection":
        by_id = {item.job_id: item for item in self.jobs}
        by_id[job.job_id] = job
        jobs = tuple(sorted(by_id.values(), key=lambda item: item.job_id))
        revision = self.store_revision + 1
        body = _collection_body(self.project_id, revision, jobs)
        return DurableProductJobCollection(self.project_id, revision, jobs, sha256_bytes(canonical_json_bytes(body)))

    def get(self, job_id: str) -> DurableProductJob:
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        raise ProductError("ERR_PRODUCT_JOB_NOT_FOUND", "Durable Product job was not found", ProductErrorCategory.STATE)

    def _body(self) -> dict[str, object]:
        return _collection_body(self.project_id, self.store_revision, self.jobs)

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "jobs_sha256": self.jobs_sha256}


def _collection_body(project_id: str, revision: int, jobs: tuple[DurableProductJob, ...]) -> dict[str, object]:
    return {
        "store_version": _STORE_VERSION, "project_id": project_id, "store_revision": revision,
        "jobs": [job.to_dict() for job in jobs],
        "authority": {"generation_queue_replaced": False, "provider_execution_authorized": False, "external_replay_authorized": False},
    }


def parse_durable_product_job(document: Mapping[str, Any]) -> DurableProductJob:
    expected = {
        "job_id", "operation_identity", "kind", "target_identity", "input_hashes",
        "state", "state_version", "attempt", "created_at", "updated_at", "unknown_since",
        "recovery_actions", "result_ref", "error_code", "estimated_cost", "currency",
        "estimate_source", "actual_cost", "authority", "job_sha256",
    }
    authority = {"provider_execution_authorized": False, "paid_execution_authorized": False, "external_replay_authorized": False}
    if not isinstance(document, Mapping) or set(document) != expected or document.get("authority") != authority:
        raise ProductError("ERR_PRODUCT_JOB_INVALID", "Durable Product job fields or authority are invalid", ProductErrorCategory.DATA_INTEGRITY)
    try:
        hashes = document["input_hashes"]
        if not isinstance(hashes, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in hashes.items()):
            raise ValueError("input_hashes must be an object")
        return DurableProductJob(
            job_id=document["job_id"], operation_identity=document["operation_identity"],
            kind=document["kind"], target_identity=document["target_identity"],
            input_hashes=tuple(sorted(hashes.items())), state=DurableProductJobState(document["state"]),
            state_version=document["state_version"], attempt=document["attempt"],
            created_at=document["created_at"], updated_at=document["updated_at"],
            unknown_since=document["unknown_since"], recovery_actions=tuple(document["recovery_actions"]),
            result_ref=document["result_ref"], error_code=document["error_code"],
            estimated_cost=document["estimated_cost"], currency=document["currency"],
            estimate_source=document["estimate_source"], actual_cost=document["actual_cost"],
            job_sha256=document["job_sha256"],
        )
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PRODUCT_JOB_INVALID", "Durable Product job contains invalid values", ProductErrorCategory.DATA_INTEGRITY) from exc


def parse_durable_product_job_collection(document: Mapping[str, Any]) -> DurableProductJobCollection:
    fields = {"store_version", "project_id", "store_revision", "jobs", "authority", "jobs_sha256"}
    authority = {"generation_queue_replaced": False, "provider_execution_authorized": False, "external_replay_authorized": False}
    if not isinstance(document, Mapping) or set(document) != fields or document.get("store_version") != _STORE_VERSION or document.get("authority") != authority:
        raise ProductError("ERR_PRODUCT_JOB_STORE_INVALID", "Durable Product job store fields or authority are invalid", ProductErrorCategory.DATA_INTEGRITY)
    try:
        rows = document["jobs"]
        if not isinstance(rows, list):
            raise ValueError("jobs must be an array")
        return DurableProductJobCollection(
            project_id=document["project_id"], store_revision=document["store_revision"],
            jobs=tuple(parse_durable_product_job(row) for row in rows), jobs_sha256=document["jobs_sha256"],
        )
    except ProductError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PRODUCT_JOB_STORE_INVALID", "Durable Product job store contains invalid values", ProductErrorCategory.DATA_INTEGRITY) from exc


class DurableProductJobStore:
    @staticmethod
    def path(project_root: str | Path, *, create: bool = False) -> Path:
        return _manifest_path(project_root, create_control_dir=create).with_name("jobs.json")

    @staticmethod
    def load(project_root: str | Path) -> DurableProductJobCollection:
        target = DurableProductJobStore.path(project_root)
        if target.is_symlink() or not target.is_file() or not 0 < target.stat().st_size <= _MAX_STORE_BYTES:
            raise ProductError("ERR_PRODUCT_JOB_STORE_FILE", "Durable Product job store file is invalid", ProductErrorCategory.DATA_INTEGRITY)
        try:
            return parse_durable_product_job_collection(json.loads(target.read_text(encoding="utf-8")))
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PRODUCT_JOB_STORE_READ", "Durable Product job store could not be read", ProductErrorCategory.DATA_INTEGRITY) from exc

    @staticmethod
    def _save_unlocked(project_root: str | Path, collection: DurableProductJobCollection) -> AtomicWriteResult:
        return AtomicJsonWriter.write(
            DurableProductJobStore.path(project_root, create=True), collection.to_dict(),
            validator=parse_durable_product_job_collection,
        )


class DurableProductJobService:
    def enqueue(
        self, project_root: str | Path, *, kind: str, target_identity: str,
        input_hashes: Mapping[str, str], estimated_cost: float | None = None,
        currency: str | None = None, estimate_source: str | None = None,
        exclusive_input_name: str | None = None,
        expected_project_id: str | None = None,
    ) -> DurableProductJob:
        root = _project_root(project_root)
        with _exclusive_project_lock(_manifest_path(root, create_control_dir=True)):
            manifest = ProductProjectManifestStore.load(root)
            self._assert_expected_project_id(manifest.project_id, expected_project_id)
            collection = self._load_or_create(root, manifest.project_id)
            self._assert_expected_project_id(collection.project_id, expected_project_id)
            candidate = DurableProductJob.create(
                kind=kind, target_identity=target_identity, input_hashes=input_hashes,
                estimated_cost=estimated_cost, currency=currency, estimate_source=estimate_source,
            )
            exclusive_digest: str | None = None
            if exclusive_input_name is not None:
                self._validate_exclusive_input(candidate, exclusive_input_name)
                exclusive_digest = dict(candidate.input_hashes)[exclusive_input_name]
            if exclusive_input_name is not None:
                matches = tuple(
                    existing for existing in collection.jobs
                    if (
                        existing.kind == candidate.kind
                        and dict(existing.input_hashes).get(exclusive_input_name) == exclusive_digest
                    )
                )
                if len(matches) == 1 and matches[0].operation_identity == candidate.operation_identity:
                    return matches[0]
                if matches:
                    raise ProductError(
                        "ERR_PRODUCT_JOB_EXCLUSIVE_INPUT_CONFLICT",
                        "Durable Product job already owns this exclusive input binding",
                        ProductErrorCategory.DATA_INTEGRITY,
                    )
            else:
                for existing in collection.jobs:
                    if existing.operation_identity == candidate.operation_identity:
                        return existing
            DurableProductJobStore._save_unlocked(root, collection.replace(candidate))
            return candidate

    def query_by_input_binding(
        self, project_root: str | Path, *, kind: str, input_name: str,
        input_sha256: str, expected_project_id: str | None = None,
    ) -> tuple[DurableProductJob, ...]:
        """Return durable jobs for one exact public input coordinate.

        An absent store is an empty, read-only result.  Existing stores are
        always parsed and Project-scoped before their jobs are returned.
        """

        if not isinstance(kind, str) or not _KIND_RE.fullmatch(kind) or kind not in _LOCAL_JOB_KINDS:
            raise ProductError(
                "ERR_PRODUCT_JOB_QUERY_INVALID",
                "Durable Product job kind is invalid",
                ProductErrorCategory.VALIDATION,
            )
        try:
            _safe_public_identity(input_name, "input_name")
            validate_sha256(input_sha256, field_name="input_sha256")
        except ValueError as exc:
            raise ProductError(
                "ERR_PRODUCT_JOB_QUERY_INVALID",
                "Durable Product job input binding is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        root = _project_root(project_root)
        with _exclusive_project_lock(_manifest_path(root, create_control_dir=True)):
            manifest = ProductProjectManifestStore.load(root)
            self._assert_expected_project_id(manifest.project_id, expected_project_id)
            path = DurableProductJobStore.path(root)
            if path.is_symlink():
                raise ProductError(
                    "ERR_PRODUCT_JOB_STORE_FILE",
                    "Durable Product job store file is invalid",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if not path.exists():
                return ()
            collection = DurableProductJobStore.load(root)
            if collection.project_id != manifest.project_id:
                raise ProductError(
                    "ERR_PRODUCT_JOB_PROJECT_CONFLICT",
                    "Durable Product jobs belong to another Project",
                    ProductErrorCategory.SECURITY,
                )
            self._assert_expected_project_id(collection.project_id, expected_project_id)
            return tuple(
                job for job in collection.jobs
                if job.kind == kind and dict(job.input_hashes).get(input_name) == input_sha256
            )

    def transition(
        self, project_root: str | Path, job_id: str, state: DurableProductJobState,
        *, expected_state_version: int, result_ref: str | None = None,
        error_code: str | None = None, actual_cost: float | None = None,
        recovery_action: str | None = None,
    ) -> DurableProductJob:
        root = _project_root(project_root)
        with _exclusive_project_lock(_manifest_path(root, create_control_dir=True)):
            collection = self._load_verified_collection(root)
            current = collection.get(job_id)
            if current.state_version != expected_state_version:
                raise ProductError("ERR_PRODUCT_JOB_CAS_CONFLICT", "Durable Product job changed before transition", ProductErrorCategory.STATE)
            changed = current.transition(
                state, result_ref=result_ref, error_code=error_code, actual_cost=actual_cost,
                recovery_action=recovery_action,
            )
            DurableProductJobStore._save_unlocked(root, collection.replace(changed))
            return changed

    def recover_interrupted(
        self, project_root: str | Path, *, kind: str | None = None,
        expected_project_id: str | None = None,
    ) -> tuple[DurableProductJob, ...]:
        """Mark interrupted durable Jobs unknown, optionally for one validated kind."""

        if kind is not None and (
            not isinstance(kind, str)
            or not _KIND_RE.fullmatch(kind)
            or kind not in _LOCAL_JOB_KINDS
        ):
            raise ProductError(
                "ERR_PRODUCT_JOB_RECOVERY_KIND_INVALID",
                "Durable Product recovery kind is invalid",
                ProductErrorCategory.VALIDATION,
            )
        root = _project_root(project_root)
        with _exclusive_project_lock(_manifest_path(root, create_control_dir=True)):
            manifest = ProductProjectManifestStore.load(root)
            self._assert_expected_project_id(manifest.project_id, expected_project_id)
            collection = self._load_verified_collection(root)
            self._assert_expected_project_id(collection.project_id, expected_project_id)
            changed: list[DurableProductJob] = []
            current_collection = collection
            for job in collection.jobs:
                if kind is not None and job.kind != kind:
                    continue
                if job.state not in {DurableProductJobState.DISPATCHING, DurableProductJobState.RUNNING}:
                    continue
                recovered = job.transition(
                    DurableProductJobState.UNKNOWN,
                    error_code="ERR_PRODUCT_JOB_RESTART_UNKNOWN",
                )
                current_collection = current_collection.replace(recovered)
                changed.append(recovered)
            if changed:
                DurableProductJobStore._save_unlocked(root, current_collection)
            return tuple(changed)

    @staticmethod
    def _load_or_create(root: Path, project_id: str) -> DurableProductJobCollection:
        path = DurableProductJobStore.path(root)
        if path.is_symlink():
            raise ProductError(
                "ERR_PRODUCT_JOB_STORE_FILE",
                "Durable Product job store file is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        if not path.exists():
            return DurableProductJobCollection.create(project_id)
        collection = DurableProductJobStore.load(root)
        if collection.project_id != project_id:
            raise ProductError("ERR_PRODUCT_JOB_PROJECT_CONFLICT", "Durable Product jobs belong to another Project", ProductErrorCategory.SECURITY)
        return collection

    @staticmethod
    def _validate_exclusive_input(candidate: DurableProductJob, input_name: str) -> None:
        try:
            _safe_public_identity(input_name, "exclusive_input_name")
        except ValueError as exc:
            raise ProductError(
                "ERR_PRODUCT_JOB_EXCLUSIVE_INPUT_INVALID",
                "Durable Product exclusive input name is invalid",
                ProductErrorCategory.VALIDATION,
            ) from exc
        if input_name not in dict(candidate.input_hashes):
            raise ProductError(
                "ERR_PRODUCT_JOB_EXCLUSIVE_INPUT_INVALID",
                "Durable Product exclusive input is absent from the candidate",
                ProductErrorCategory.DATA_INTEGRITY,
            )

    @staticmethod
    def _assert_expected_project_id(actual_project_id: str, expected_project_id: str | None) -> None:
        if expected_project_id is not None and actual_project_id != expected_project_id:
            raise ProductError(
                "ERR_PRODUCT_JOB_PROJECT_CONFLICT",
                "Durable Product jobs belong to another Project",
                ProductErrorCategory.SECURITY,
            )

    @staticmethod
    def _load_verified_collection(root: Path) -> DurableProductJobCollection:
        manifest = ProductProjectManifestStore.load(root)
        collection = DurableProductJobStore.load(root)
        if collection.project_id != manifest.project_id:
            raise ProductError("ERR_PRODUCT_JOB_PROJECT_CONFLICT", "Durable Product jobs belong to another Project", ProductErrorCategory.SECURITY)
        return collection


def durable_job_shell_projection(job: DurableProductJob) -> JobSnapshot:
    states = {
        DurableProductJobState.QUEUED: ShellJobState.QUEUED,
        DurableProductJobState.PREFLIGHT: ShellJobState.QUEUED,
        DurableProductJobState.READY: ShellJobState.QUEUED,
        DurableProductJobState.DISPATCHING: ShellJobState.RUNNING,
        DurableProductJobState.RUNNING: ShellJobState.RUNNING,
        DurableProductJobState.SUCCEEDED: ShellJobState.COMPLETED,
        DurableProductJobState.FAILED: ShellJobState.FAILED,
        DurableProductJobState.CANCELLED: ShellJobState.CANCELLED,
        DurableProductJobState.UNKNOWN: ShellJobState.WAITING_HUMAN,
        DurableProductJobState.HUMAN_REQUIRED: ShellJobState.WAITING_HUMAN,
    }
    return JobSnapshot(
        job_id=job.job_id, command_id=job.operation_identity, stage=job.state.value,
        state=states[job.state], safe_cancel=job.state in {
            DurableProductJobState.QUEUED, DurableProductJobState.PREFLIGHT, DurableProductJobState.READY,
        }, error_code=job.error_code, evidence_ref=job.result_ref,
    )
