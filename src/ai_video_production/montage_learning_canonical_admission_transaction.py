"""TASK-058 FAST-BATCH-1A canonical admission transaction.

Only a raw exact TASK-055 delivery enters this writer.  P1C-B/C/D are rerun
inside the Product Project lock and a separately rooted anchor guard.  Public
v2 receipts are published only after ProjectSave, canonical child, manifest,
anchor and receipt-registry read-back all agree.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
from typing import Any, Callable, Iterator, Mapping

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
    validate_generic_learning_delivery,
)
from .montage_learning_canonical_promotion_ledger_contract import (
    AppendDecision,
    MontageLearningCanonicalLedgerCandidate,
    MontageLearningCanonicalLedgerCasExpectation,
    evaluate_montage_learning_canonical_append,
)
from .montage_learning_durable_staging_readback import (
    verify_montage_learning_durable_staging_readback,
)
from .montage_learning_external_monotonic_anchor_contract import (
    AnchorDecision,
    MontageLearningExternalMonotonicAnchorCandidate,
    MontageLearningExternalMonotonicAnchorExpectation,
    evaluate_montage_learning_external_monotonic_anchor,
)
from .montage_learning_receipt_contracts import (
    ACCEPTED, DUPLICATE, EXACT_EVIDENCE,
    CONTRACT_PROFILE as RECEIPT_CONTRACT_PROFILE,
    MESSAGE_TYPE as RECEIPT_MESSAGE_TYPE,
    SCHEMA_VERSION as RECEIPT_SCHEMA_VERSION,
    MontageLearningAdmissionReceipt,
    compute_montage_learning_receipt_sha256,
    parse_montage_learning_admission_receipt,
)
from .product_project import (
    ProductProjectManifest, ProjectChildBinding, parse_product_project_manifest,
)
from .product_project_store import ProductProjectManifestStore, _exclusive_project_lock
from .project_save import (
    ProductProjectSaveCoordinator,
    ProjectSaveParticipantOutcome,
    ProjectSaveParticipantPlan,
    ProjectSaveParticipantResult,
)
from .serialization import canonical_json_bytes, sha256_bytes


SCHEMA_VERSION = "1.0.0"
TASK_OWNER = "TASK-058"
CANONICAL_RELATIVE_PATH = Path("state/montage-learning-canonical-admission.json")
RECEIPT_RELATIVE_PATH = Path("state/montage-learning-admission-receipts-v2.json")
JOURNAL_RELATIVE_PATH = Path("state/montage-learning-canonical-admission-transaction.json")
ANCHOR_FILE_NAME = "montage-learning-external-monotonic-anchor.json"
ANCHOR_RECOVERY_FILE_NAME = ".montage-learning-external-monotonic-anchor.recovery.json"
CANONICAL_FORMAT_ID = "bai.montage-learning-canonical-admission"
CANONICAL_FORMAT_VERSION = "1.0.0"
GENERIC_OBSERVATION_RELATIVE_PATH = Path("state/montage-learning-generic-review-observations.json")
GENERIC_OBSERVATION_FORMAT_ID = "bai.montage-learning-generic-review-observations"
GENERIC_OBSERVATION_FORMAT_VERSION = "1.0.0"
_PARTICIPANT_ID = "TASK058/MONTAGE-ANCHOR"
_PARTICIPANT_VERSION = "1.0.0"

_CANONICAL_DOMAIN = b"TASK058_CANONICAL_ADMISSION_STORE_V1\0"
_ANCHOR_DOMAIN = b"TASK058_EXTERNAL_MONOTONIC_ANCHOR_STORE_V1\0"
_REGISTRY_DOMAIN = b"TASK058_ADMISSION_RECEIPT_REGISTRY_V1\0"
_JOURNAL_DOMAIN = b"TASK058_CANONICAL_ADMISSION_TRANSACTION_JOURNAL_V1\0"
_RECEIPT_ID_DOMAIN = b"TASK058_CANONICAL_ADMISSION_RECEIPT_ID_V1\0"
_GENERIC_LEDGER_DOMAIN = b"TASK058_GENERIC_REVIEW_OBSERVATION_LEDGER_V1\0"
_GENERIC_RECEIPT_DOMAIN = b"TASK058_GENERIC_REVIEW_OBSERVATION_RECEIPT_V1\0"
_MAX_BYTES = 64 * 1024 * 1024
_MAX_RECEIPTS = 8192
_REPARSE_POINT = 0x400
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
FailureHook = Callable[[str, Path], None]


class MontageLearningCanonicalAdmissionError(ValueError):
    """Fail-closed canonical admission error."""


def _exact(value: object, name: str, *, max_nodes: int = 400_000) -> Any:
    count = 0
    active: set[int] = set()

    def copy(item: object, path: str, depth: int) -> Any:
        nonlocal count
        count += 1
        if count > max_nodes or depth > 40:
            raise MontageLearningCanonicalAdmissionError(f"{name} exceeds bounds")
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) not in {dict, list}:
            raise MontageLearningCanonicalAdmissionError(f"{path} is not exact JSON")
        marker = id(item)
        if marker in active:
            raise MontageLearningCanonicalAdmissionError(f"{path} contains a cycle")
        active.add(marker)
        try:
            if type(item) is list:
                return [copy(child, f"{path}[]", depth + 1) for child in item]
            output: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise MontageLearningCanonicalAdmissionError(f"{path} has a non-string key")
                output[key] = copy(child, f"{path}.{key}", depth + 1)
            return output
        finally:
            active.remove(marker)

    return copy(value, name, 0)


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _sha(value: object, name: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _integer(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise MontageLearningCanonicalAdmissionError(f"{name} is invalid")
    return value


def _hash(domain: bytes, body: Mapping[str, Any]) -> str:
    return sha256_bytes(domain + canonical_json_bytes(body))


def _without(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: value for key, value in body.items() if key != field}


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _root(value: str | Path, name: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir() or _is_reparse(path):
        raise MontageLearningCanonicalAdmissionError(f"{name} must be an existing safe root")
    return path.resolve(strict=True)


def _target(path: Path) -> None:
    if not path.parent.is_dir() or _is_reparse(path.parent):
        raise MontageLearningCanonicalAdmissionError("target parent is unsafe")
    if _is_reparse(path) or (path.exists() and not path.is_file()):
        raise MontageLearningCanonicalAdmissionError("target is unsafe")


def _read(path: Path, parser: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    _target(path)
    try:
        raw = path.read_bytes()
        if not 1 <= len(raw) <= _MAX_BYTES:
            raise ValueError("size")
        value = json.loads(raw.decode("utf-8"))
        if type(value) is not dict or raw != canonical_json_bytes(value) + b"\n":
            raise ValueError("canonical")
        return parser(value)
    except MontageLearningCanonicalAdmissionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise MontageLearningCanonicalAdmissionError(f"invalid document: {path.name}") from exc


def _parse_canonical(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "canonical")
    expected = {
        "schema_version", "record_type", "task_owner", "project_id",
        "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
        "source_project_manifest_sha256", "ledger", "external_anchor_sha256",
        "canonical_state", "canonical_store_written", "durable_readback_required",
        "directory_durability_confirmed", "hostile_path_race_protection_verified",
        "automatic_learning_promotion_authorized", "profile_generation_authorized",
        "timeline_mutation_authorized", "resolve_write_authorized",
        "release_authorized", "deploy_authorized", "production_authorized",
        "canonical_store_commit_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("canonical fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_CANONICAL_ADMISSION_STORE" or
        body["task_owner"] != TASK_OWNER or body["canonical_state"] != "COMMITTED" or
        body["canonical_store_written"] is not True or
        body["durable_readback_required"] is not True):
        raise MontageLearningCanonicalAdmissionError("canonical identity mismatch")
    for name in ("project_id", "canonical_store_id"):
        _identifier(body[name], name)
    for name in ("owner_scope_hash", "ledger_key_sha256", "source_project_manifest_sha256",
                 "external_anchor_sha256", "canonical_store_commit_sha256"):
        _sha(body[name], name)
    if body["directory_durability_confirmed"] is not False:
        raise MontageLearningCanonicalAdmissionError("directory durability is not claimed")
    for name in ("hostile_path_race_protection_verified", "automatic_learning_promotion_authorized",
                 "profile_generation_authorized", "timeline_mutation_authorized",
                 "resolve_write_authorized", "release_authorized", "deploy_authorized",
                 "production_authorized"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    ledger = MontageLearningCanonicalLedgerCandidate.from_dict(body["ledger"]).to_dict()
    if ledger["ledger_revision"] <= 0:
        raise MontageLearningCanonicalAdmissionError("canonical ledger is empty")
    for name in ("project_id", "canonical_store_id", "owner_scope_hash", "ledger_key_sha256"):
        if body[name] != ledger[name]:
            raise MontageLearningCanonicalAdmissionError("canonical ledger scope mismatch")
    if body["canonical_store_commit_sha256"] != _hash(
        _CANONICAL_DOMAIN, _without(body, "canonical_store_commit_sha256")
    ):
        raise MontageLearningCanonicalAdmissionError("canonical digest mismatch")
    body["ledger"] = ledger
    return body


def _parse_anchor(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "anchor")
    expected = {
        "schema_version", "record_type", "task_owner", "project_id",
        "canonical_store_id", "owner_scope_hash", "ledger_key_sha256",
        "canonical_store_commit_sha256", "target_project_manifest_sha256",
        "target_project_manifest_revision", "anchor",
        "anchor_state", "external_anchor_written", "external_snapshot_coordinate_only",
        "origin_authenticated_by_store", "rollback_detection_authority_created",
        "directory_durability_confirmed", "hostile_path_race_protection_verified",
        "external_anchor_document_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("anchor fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_STORE" or
        body["task_owner"] != TASK_OWNER or body["anchor_state"] != "ESTABLISHED" or
        body["external_anchor_written"] is not True or
        body["external_snapshot_coordinate_only"] is not True):
        raise MontageLearningCanonicalAdmissionError("anchor identity mismatch")
    for name in ("origin_authenticated_by_store", "rollback_detection_authority_created",
                 "directory_durability_confirmed", "hostile_path_race_protection_verified"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    for name in ("project_id", "canonical_store_id"):
        _identifier(body[name], name)
    for name in ("owner_scope_hash", "ledger_key_sha256", "canonical_store_commit_sha256",
                 "target_project_manifest_sha256", "external_anchor_document_sha256"):
        _sha(body[name], name)
    _integer(body["target_project_manifest_revision"], "target_project_manifest_revision", 1, 2**63 - 1)
    anchor = MontageLearningExternalMonotonicAnchorCandidate.from_dict(body["anchor"]).to_dict()
    for name in ("project_id", "canonical_store_id", "owner_scope_hash", "ledger_key_sha256"):
        if body[name] != anchor[name]:
            raise MontageLearningCanonicalAdmissionError("anchor scope mismatch")
    if body["external_anchor_document_sha256"] != _hash(
        _ANCHOR_DOMAIN, _without(body, "external_anchor_document_sha256")
    ):
        raise MontageLearningCanonicalAdmissionError("anchor digest mismatch")
    body["anchor"] = anchor
    return body


def _parse_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "receipt registry")
    expected = {"schema_version", "record_type", "task_owner", "project_id",
                "canonical_store_id", "owner_scope_hash", "revision", "receipts",
                "registry_sha256"}
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("registry fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_ADMISSION_RECEIPT_REGISTRY_V2" or
        body["task_owner"] != TASK_OWNER):
        raise MontageLearningCanonicalAdmissionError("registry identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["canonical_store_id"], "canonical_store_id")
    _sha(body["owner_scope_hash"], "owner_scope_hash")
    revision = _integer(body["revision"], "revision", 0, _MAX_RECEIPTS)
    if type(body["receipts"]) is not list or len(body["receipts"]) != revision:
        raise MontageLearningCanonicalAdmissionError("registry count mismatch")
    accepted: dict[str, str] = {}
    ids: set[str] = set()
    hashes: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for raw in body["receipts"]:
        receipt = parse_montage_learning_admission_receipt(raw).to_dict()
        if receipt["owner_scope_hash"] != body["owner_scope_hash"]:
            raise MontageLearningCanonicalAdmissionError("registry scope mismatch")
        if receipt["receipt_id"] in ids or receipt["receipt_sha256"] in hashes:
            raise MontageLearningCanonicalAdmissionError("registry replay")
        key = receipt["idempotency_key_sha256"]
        if receipt["status"] == ACCEPTED:
            if key in accepted:
                raise MontageLearningCanonicalAdmissionError("multiple ACCEPTED lineage roots")
            accepted[key] = receipt["receipt_sha256"]
        elif accepted.get(key) != receipt["duplicate_of_receipt_sha256"]:
            raise MontageLearningCanonicalAdmissionError("DUPLICATE lineage mismatch")
        ids.add(receipt["receipt_id"])
        hashes.add(receipt["receipt_sha256"])
        parsed.append(receipt)
    if body["registry_sha256"] != _hash(_REGISTRY_DOMAIN, _without(body, "registry_sha256")):
        raise MontageLearningCanonicalAdmissionError("registry digest mismatch")
    body["receipts"] = parsed
    return body


def _empty_registry(project_id: str, store_id: str, scope: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_ADMISSION_RECEIPT_REGISTRY_V2",
        "task_owner": TASK_OWNER,
        "project_id": project_id,
        "canonical_store_id": store_id,
        "owner_scope_hash": scope,
        "revision": 0,
        "receipts": [],
    }
    body["registry_sha256"] = _hash(_REGISTRY_DOMAIN, body)
    return _parse_registry(body)


def _append_registry(registry: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    body = _without(registry, "registry_sha256")
    body["receipts"] = [*registry["receipts"], dict(receipt)]
    body["revision"] = len(body["receipts"])
    if body["revision"] > _MAX_RECEIPTS:
        raise MontageLearningCanonicalAdmissionError("registry is full")
    body["registry_sha256"] = _hash(_REGISTRY_DOMAIN, body)
    return _parse_registry(body)


def _build_canonical(source_manifest_sha256: str, ledger: Mapping[str, Any],
                     anchor: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_CANONICAL_ADMISSION_STORE",
        "task_owner": TASK_OWNER,
        "project_id": ledger["project_id"],
        "canonical_store_id": ledger["canonical_store_id"],
        "owner_scope_hash": ledger["owner_scope_hash"],
        "ledger_key_sha256": ledger["ledger_key_sha256"],
        "source_project_manifest_sha256": source_manifest_sha256,
        "ledger": dict(ledger),
        "external_anchor_sha256": anchor["anchor_sha256"],
        "canonical_state": "COMMITTED",
        "canonical_store_written": True,
        "durable_readback_required": True,
        "directory_durability_confirmed": False,
        "hostile_path_race_protection_verified": False,
        "automatic_learning_promotion_authorized": False,
        "profile_generation_authorized": False,
        "timeline_mutation_authorized": False,
        "resolve_write_authorized": False,
        "release_authorized": False,
        "deploy_authorized": False,
        "production_authorized": False,
    }
    body["canonical_store_commit_sha256"] = _hash(_CANONICAL_DOMAIN, body)
    return _parse_canonical(body)


def _build_anchor(canonical: Mapping[str, Any], anchor: Mapping[str, Any],
                  target_manifest_sha256: str, target_manifest_revision: int) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "MONTAGE_LEARNING_EXTERNAL_MONOTONIC_ANCHOR_STORE",
        "task_owner": TASK_OWNER,
        "project_id": canonical["project_id"],
        "canonical_store_id": canonical["canonical_store_id"],
        "owner_scope_hash": canonical["owner_scope_hash"],
        "ledger_key_sha256": canonical["ledger_key_sha256"],
        "canonical_store_commit_sha256": canonical["canonical_store_commit_sha256"],
        "target_project_manifest_sha256": target_manifest_sha256,
        "target_project_manifest_revision": target_manifest_revision,
        "anchor": dict(anchor),
        "anchor_state": "ESTABLISHED",
        "external_anchor_written": True,
        "external_snapshot_coordinate_only": True,
        "origin_authenticated_by_store": False,
        "rollback_detection_authority_created": False,
        "directory_durability_confirmed": False,
        "hostile_path_race_protection_verified": False,
    }
    body["external_anchor_document_sha256"] = _hash(_ANCHOR_DOMAIN, body)
    return _parse_anchor(body)


def _receipt_id(commit: str, key: str, attempt: int) -> str:
    digest = _hash(_RECEIPT_ID_DOMAIN, {
        "canonical_store_commit_sha256": commit,
        "idempotency_key_sha256": key,
        "attempt": attempt,
    }).removeprefix("sha256:")
    return f"task058-{digest[:40]}-{attempt}"


def _mint_receipt(*, readback: Mapping[str, Any], commit: str, status: str,
                  duplicate_of: str | None, attempt: int, bridge_instance_id: str,
                  processed_at: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "message_type": RECEIPT_MESSAGE_TYPE,
        "contract_profile": RECEIPT_CONTRACT_PROFILE,
        "receipt_id": _receipt_id(commit, readback["idempotency_key_sha256"], attempt),
        "admission_class": EXACT_EVIDENCE,
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": readback["source_record_id"],
        "source_sha256": readback["source_sha256"],
        "owner_scope_hash": readback["owner_scope_hash"],
        "idempotency_key_sha256": readback["idempotency_key_sha256"],
        "status": status,
        "canonical_store_written": True,
        "canonical_evidence_id": readback["canonical_evidence_id"],
        "canonical_evidence_sha256": readback["canonical_evidence_sha256"],
        "canonical_store_commit_sha256": commit,
        "duplicate_of_receipt_sha256": duplicate_of,
        "reason_codes": [] if status == ACCEPTED else ["DUPLICATE_IDEMPOTENCY_KEY"],
        "attempt": attempt,
        "processed_at": processed_at,
        "bridge_instance_id": bridge_instance_id,
    }
    body["receipt_sha256"] = compute_montage_learning_receipt_sha256(body)
    return parse_montage_learning_admission_receipt(body).to_dict()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _AnchorParticipant:
    participant_id = _PARTICIPANT_ID
    participant_version = _PARTICIPANT_VERSION

    def __init__(self, *, project_id: str, anchor_path: Path, recovery_path: Path,
                 expected_sha256: str | None, target_anchor: Mapping[str, Any],
                 source_manifest_sha256: str, target_manifest_sha256: str,
                 failure_hook: FailureHook | None = None) -> None:
        self.project_id = project_id
        self.anchor_path = anchor_path
        self.recovery_path = recovery_path
        self.expected_sha256 = expected_sha256
        self.target_anchor = _parse_anchor(target_anchor)
        self.source_manifest_sha256 = source_manifest_sha256
        self.target_manifest_sha256 = target_manifest_sha256
        self.failure_hook = failure_hook

    def _current_sha(self) -> str | None:
        if not self.anchor_path.exists():
            return None
        return str(_read(self.anchor_path, _parse_anchor)["external_anchor_document_sha256"])

    def plan_locked(self, project_root: Path, source_manifest: ProductProjectManifest,
                    target_manifest: ProductProjectManifest) -> ProjectSaveParticipantPlan:
        del project_root
        if (source_manifest.project_id != self.project_id or
            source_manifest.project_manifest_sha256 != self.source_manifest_sha256 or
            target_manifest.project_manifest_sha256 != self.target_manifest_sha256 or
            self._current_sha() != self.expected_sha256):
            raise MontageLearningCanonicalAdmissionError("anchor participant CAS conflict")
        return ProjectSaveParticipantPlan.create(
            participant_id=self.participant_id,
            participant_version=self.participant_version,
            project_id=self.project_id,
            source_manifest_sha256=self.source_manifest_sha256,
            target_manifest_sha256=self.target_manifest_sha256,
            source_content_sha256=self.expected_sha256,
            target_content_sha256=self.target_anchor["external_anchor_document_sha256"],
        )

    def _recovery(self, transaction_id: str, plan: ProjectSaveParticipantPlan) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "MONTAGE_LEARNING_ANCHOR_PARTICIPANT_RECOVERY",
            "participant_id": self.participant_id,
            "participant_version": self.participant_version,
            "project_id": self.project_id,
            "transaction_id": transaction_id,
            "binding_sha256": plan.binding_sha256,
            "source_manifest_sha256": plan.source_manifest_sha256,
            "target_manifest_sha256": plan.target_manifest_sha256,
            "expected_anchor_document_sha256": self.expected_sha256,
            "target_anchor": self.target_anchor,
        }
        body["recovery_sha256"] = _hash(_JOURNAL_DOMAIN, body)
        return body

    def _load_recovery(self) -> dict[str, Any]:
        value = _read(self.recovery_path, lambda item: _exact(item, "anchor recovery"))
        if type(value) is not dict or value.get("recovery_sha256") != _hash(
            _JOURNAL_DOMAIN, _without(value, "recovery_sha256")
        ):
            raise MontageLearningCanonicalAdmissionError("anchor recovery digest mismatch")
        return value

    def prepare_locked(self, project_root: Path, transaction_id: str,
                       plan: ProjectSaveParticipantPlan) -> str:
        del project_root
        body = self._recovery(transaction_id, plan)
        if self.recovery_path.exists():
            if self._load_recovery() != body:
                raise MontageLearningCanonicalAdmissionError("anchor recovery conflicts")
        else:
            AtomicJsonWriter.write(self.recovery_path, body)
        return str(body["recovery_sha256"])

    def _scope(self, transaction_id: str, plan: ProjectSaveParticipantPlan,
               receipt: str) -> dict[str, Any]:
        body = self._load_recovery()
        expected = self._recovery(transaction_id, plan)
        if body != expected or body["recovery_sha256"] != receipt:
            raise MontageLearningCanonicalAdmissionError("anchor recovery scope mismatch")
        return body

    def reconcile_locked(self, project_root: Path, transaction_id: str,
                         plan: ProjectSaveParticipantPlan, prepared_receipt_sha256: str,
                         outcome: ProjectSaveParticipantOutcome) -> ProjectSaveParticipantResult:
        del project_root
        current = self._current_sha()
        if self.recovery_path.exists():
            self._scope(transaction_id, plan, prepared_receipt_sha256)
        else:
            expected_without_recovery = (
                plan.target_content_sha256
                if outcome is ProjectSaveParticipantOutcome.COMPLETE
                else plan.source_content_sha256
            )
            if current != expected_without_recovery:
                raise MontageLearningCanonicalAdmissionError("anchor recovery is missing")
            return ProjectSaveParticipantResult.create(
                participant_id=self.participant_id,
                binding_sha256=plan.binding_sha256,
                transaction_id=transaction_id,
                outcome=outcome,
                result_content_sha256=current,
            )
        if outcome is ProjectSaveParticipantOutcome.COMPLETE:
            if current == plan.source_content_sha256:
                AtomicJsonWriter.write(self.anchor_path, self.target_anchor, validator=_parse_anchor)
                current = self._current_sha()
            if current != plan.target_content_sha256:
                raise MontageLearningCanonicalAdmissionError("anchor commit/read-back failed")
            if self.failure_hook is not None:
                self.failure_hook("after_anchor_write_before_participant_result", self.anchor_path)
        elif current != plan.source_content_sha256:
            raise MontageLearningCanonicalAdmissionError("anchor rollback conflict")
        self.recovery_path.unlink()
        return ProjectSaveParticipantResult.create(
            participant_id=self.participant_id,
            binding_sha256=plan.binding_sha256,
            transaction_id=transaction_id,
            outcome=outcome,
            result_content_sha256=current,
        )

    def abort_prejournal_locked(self, project_root: Path, transaction_id: str,
                                plan: ProjectSaveParticipantPlan,
                                prepared_receipt_sha256: str) -> None:
        del project_root
        self._scope(transaction_id, plan, prepared_receipt_sha256)
        if self._current_sha() != plan.source_content_sha256:
            raise MontageLearningCanonicalAdmissionError("anchor changed before abort")
        self.recovery_path.unlink()

    def reconcile_orphan_locked(self, project_root: Path,
                                current_manifest: ProductProjectManifest) -> str | None:
        del project_root
        if not self.recovery_path.exists():
            return None
        body = self._load_recovery()
        if (body["source_manifest_sha256"] != current_manifest.project_manifest_sha256 or
            self._current_sha() != body["expected_anchor_document_sha256"]):
            raise MontageLearningCanonicalAdmissionError("unsafe anchor orphan")
        receipt = str(body["recovery_sha256"])
        self.recovery_path.unlink()
        return receipt


def _parse_journal(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "transaction journal")
    expected = {
        "schema_version", "record_type", "task_owner", "operation", "project_id",
        "canonical_store_id", "owner_scope_hash", "staging_readback_sha256",
        "expected_previous_commit_sha256", "expected_previous_anchor_document_sha256",
        "expected_previous_registry_sha256", "proposed_canonical", "proposed_anchor",
        "proposed_registry", "target_manifest", "receipt_sha256", "journal_sha256",
    }
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("journal fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "MONTAGE_LEARNING_CANONICAL_ADMISSION_TRANSACTION" or
        body["task_owner"] != TASK_OWNER or body["operation"] not in {ACCEPTED, DUPLICATE}):
        raise MontageLearningCanonicalAdmissionError("journal identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["canonical_store_id"], "canonical_store_id")
    for name in ("owner_scope_hash", "staging_readback_sha256", "receipt_sha256"):
        _sha(body[name], name)
    for name in ("expected_previous_commit_sha256",
                 "expected_previous_anchor_document_sha256",
                 "expected_previous_registry_sha256"):
        _sha(body[name], name, nullable=True)
    canonical = _parse_canonical(body["proposed_canonical"])
    anchor = _parse_anchor(body["proposed_anchor"])
    registry = _parse_registry(body["proposed_registry"])
    manifest = parse_product_project_manifest(body["target_manifest"])
    if (body["project_id"] != canonical["project_id"] or
        body["canonical_store_id"] != canonical["canonical_store_id"] or
        body["owner_scope_hash"] != canonical["owner_scope_hash"] or
        anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
        anchor["target_project_manifest_sha256"] != manifest.project_manifest_sha256 or
        anchor["target_project_manifest_revision"] != manifest.project_revision or
        registry["receipts"][-1]["receipt_sha256"] != body["receipt_sha256"] or
        registry["receipts"][-1]["status"] != body["operation"]):
        raise MontageLearningCanonicalAdmissionError("journal cross-binding mismatch")
    if body["journal_sha256"] != _hash(_JOURNAL_DOMAIN, _without(body, "journal_sha256")):
        raise MontageLearningCanonicalAdmissionError("journal digest mismatch")
    body["proposed_canonical"] = canonical
    body["proposed_anchor"] = anchor
    body["proposed_registry"] = registry
    body["target_manifest"] = manifest.to_dict()
    return body


@dataclass(frozen=True, slots=True)
class MontageLearningCanonicalAdmissionResult:
    receipt: MontageLearningAdmissionReceipt
    canonical_store_commit_sha256: str
    external_anchor_document_sha256: str
    recovered: bool

    @property
    def status(self) -> str:
        return str(self.receipt.to_dict()["status"])


_VERIFIED_TOKEN = object()


class MontageLearningVerifiedAdmissionReceipt:
    __slots__ = ("_receipt", "_manifest", "_anchor")

    def __init__(self, receipt: MontageLearningAdmissionReceipt, manifest: str,
                 anchor: str, *, _token: object | None = None) -> None:
        if _token is not _VERIFIED_TOKEN:
            raise TypeError("use the trusted canonical reader")
        object.__setattr__(self, "_receipt", receipt)
        object.__setattr__(self, "_manifest", manifest)
        object.__setattr__(self, "_anchor", anchor)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("verified receipt is immutable")

    @property
    def receipt(self) -> MontageLearningAdmissionReceipt:
        return self._receipt

    def to_public_projection(self) -> dict[str, object]:
        receipt = self._receipt.to_dict()
        return {
            "receipt_id": receipt["receipt_id"],
            "receipt_sha256": receipt["receipt_sha256"],
            "status": receipt["status"],
            "canonical_store_commit_sha256": receipt["canonical_store_commit_sha256"],
            "project_manifest_sha256": self._manifest,
            "external_anchor_document_sha256": self._anchor,
            "canonical_currentness_verified": True,
            "manifest_child_binding_verified": True,
            "external_anchor_currentness_verified": True,
            "receipt_origin_verified_by_trusted_reader": True,
            "rollback_detection_authority_created": False,
            "automatic_learning_promotion_authorized": False,
            "profile_generation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "release_authorized": False,
            "deploy_authorized": False,
            "production_authorized": False,
        }


class GenericReviewObservationReceipt:
    __slots__ = ("record_id", "learning_sha256", "status", "receipt_id", "timestamp",
                 "ledger_revision", "previous_ledger_sha256", "duplicate_of_receipt_sha256",
                 "receipt_sha256")

    def __init__(self, *, record_id: str, learning_sha256: str, status: str,
                 receipt_id: str, timestamp: str, ledger_revision: int,
                 previous_ledger_sha256: str, duplicate_of_receipt_sha256: str | None,
                 receipt_sha256: str, _token: object | None = None) -> None:
        if _token is not _VERIFIED_TOKEN:
            raise TypeError("generic receipts are returned only after durable read-back")
        for name, value in locals().copy().items():
            if name not in {"self", "_token"}:
                object.__setattr__(self, name, value)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("generic receipt is immutable")

    @classmethod
    def _from_dict(cls, value: Mapping[str, Any]) -> "GenericReviewObservationReceipt":
        body = _exact(value, "generic receipt")
        expected = {"schema_version", "record_type", "task_owner", "namespace",
                    "source_contract_profile", "record_id", "learning_sha256", "status",
                    "receipt_id", "timestamp", "ledger_revision", "previous_ledger_sha256",
                    "duplicate_of_receipt_sha256", "canonical_store_written",
                    "serialized_receipt_authoritative",
                    "learning_adoption_authorized", "automatic_learning_promotion_authorized",
                    "profile_generation_authorized", "timeline_mutation_authorized",
                    "resolve_write_authorized", "release_authorized", "deploy_authorized",
                    "production_authorized", "receipt_sha256"}
        if type(body) is not dict or set(body) != expected:
            raise MontageLearningCanonicalAdmissionError("generic receipt fields mismatch")
        if (body["schema_version"] != SCHEMA_VERSION or
            body["record_type"] != "GENERIC_REVIEW_OBSERVATION_RECEIPT" or
            body["task_owner"] != TASK_OWNER or
            body["namespace"] != "GENERIC_REVIEW_OBSERVATION_ONLY" or
            body["source_contract_profile"] != GENERIC_CONTRACT_PROFILE or
            body["status"] not in {ACCEPTED, DUPLICATE} or
            body["canonical_store_written"] is not True):
            raise MontageLearningCanonicalAdmissionError("generic receipt identity mismatch")
        _identifier(body["record_id"], "record_id")
        _identifier(body["receipt_id"], "receipt_id")
        _sha(body["learning_sha256"], "learning_sha256")
        _sha(body["previous_ledger_sha256"], "previous_ledger_sha256")
        _sha(body["duplicate_of_receipt_sha256"], "duplicate_of_receipt_sha256", nullable=True)
        revision = _integer(body["ledger_revision"], "ledger_revision", 1, _MAX_RECEIPTS)
        if type(body["timestamp"]) is not str or not body["timestamp"].endswith("Z"):
            raise MontageLearningCanonicalAdmissionError("generic timestamp invalid")
        for name in ("learning_adoption_authorized", "automatic_learning_promotion_authorized",
                     "profile_generation_authorized", "timeline_mutation_authorized",
                     "resolve_write_authorized", "release_authorized", "deploy_authorized",
                     "production_authorized"):
            if body[name] is not False:
                raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
        if body["serialized_receipt_authoritative"] is not False:
            raise MontageLearningCanonicalAdmissionError("serialized generic receipt is non-authoritative")
        if (body["status"] == ACCEPTED) != (body["duplicate_of_receipt_sha256"] is None):
            raise MontageLearningCanonicalAdmissionError("generic receipt lineage mismatch")
        if body["receipt_sha256"] != _hash(
            _GENERIC_RECEIPT_DOMAIN, _without(body, "receipt_sha256")
        ):
            raise MontageLearningCanonicalAdmissionError("generic receipt digest mismatch")
        return cls(
            record_id=body["record_id"], learning_sha256=body["learning_sha256"],
            status=body["status"], receipt_id=body["receipt_id"], timestamp=body["timestamp"],
            ledger_revision=revision, previous_ledger_sha256=body["previous_ledger_sha256"],
            duplicate_of_receipt_sha256=body["duplicate_of_receipt_sha256"],
            receipt_sha256=body["receipt_sha256"],
            _token=_VERIFIED_TOKEN,
        )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "GENERIC_REVIEW_OBSERVATION_RECEIPT",
            "task_owner": TASK_OWNER,
            "namespace": "GENERIC_REVIEW_OBSERVATION_ONLY",
            "source_contract_profile": GENERIC_CONTRACT_PROFILE,
            "record_id": self.record_id,
            "learning_sha256": self.learning_sha256,
            "status": self.status,
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "ledger_revision": self.ledger_revision,
            "previous_ledger_sha256": self.previous_ledger_sha256,
            "duplicate_of_receipt_sha256": self.duplicate_of_receipt_sha256,
            "canonical_store_written": True,
            "serialized_receipt_authoritative": False,
            "learning_adoption_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "profile_generation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "release_authorized": False,
            "deploy_authorized": False,
            "production_authorized": False,
            "receipt_sha256": self.receipt_sha256,
        }
        return body

    def to_skill_v1_receipt(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "message_type": "BvpMontageLearningAdmissionReceipt",
            "record_id": self.record_id,
            "learning_sha256": self.learning_sha256,
            "status": self.status,
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
        }


def _parse_generic_ledger(value: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact(value, "generic observation ledger")
    expected = {"schema_version", "record_type", "task_owner", "namespace", "project_id",
                "store_id", "revision", "entries", "canonical_store_written",
                "learning_adoption_authorized", "automatic_learning_promotion_authorized",
                "profile_generation_authorized", "timeline_mutation_authorized",
                "resolve_write_authorized", "ledger_sha256"}
    if type(body) is not dict or set(body) != expected:
        raise MontageLearningCanonicalAdmissionError("generic ledger fields mismatch")
    if (body["schema_version"] != SCHEMA_VERSION or
        body["record_type"] != "GENERIC_REVIEW_OBSERVATION_LEDGER" or
        body["task_owner"] != TASK_OWNER or
        body["namespace"] != "GENERIC_REVIEW_OBSERVATION_ONLY" or
        body["canonical_store_written"] is not True):
        raise MontageLearningCanonicalAdmissionError("generic ledger identity mismatch")
    _identifier(body["project_id"], "project_id")
    _identifier(body["store_id"], "store_id")
    revision = _integer(body["revision"], "revision", 1, _MAX_RECEIPTS)
    if type(body["entries"]) is not list or len(body["entries"]) != revision:
        raise MontageLearningCanonicalAdmissionError("generic ledger count mismatch")
    for name in ("learning_adoption_authorized", "automatic_learning_promotion_authorized",
                 "profile_generation_authorized", "timeline_mutation_authorized",
                 "resolve_write_authorized"):
        if body[name] is not False:
            raise MontageLearningCanonicalAdmissionError(f"{name} must remain false")
    seen: dict[str, str] = {}
    accepted_receipts: dict[str, str] = {}
    for index, entry in enumerate(body["entries"], start=1):
        if type(entry) is not dict or set(entry) != {
            "revision", "record_id", "learning_sha256", "source_delivery",
            "source_delivery_sha256", "receipt",
        }:
            raise MontageLearningCanonicalAdmissionError("generic entry fields mismatch")
        if entry["revision"] != index:
            raise MontageLearningCanonicalAdmissionError("generic revision gap")
        _identifier(entry["record_id"], "record_id")
        _sha(entry["learning_sha256"], "learning_sha256")
        _sha(entry["source_delivery_sha256"], "source_delivery_sha256")
        if entry["source_delivery_sha256"] != sha256_bytes(canonical_json_bytes(entry["source_delivery"])):
            raise MontageLearningCanonicalAdmissionError("generic delivery digest mismatch")
        candidate = validate_generic_learning_delivery(entry["source_delivery"])
        if candidate.record_id != entry["record_id"] or candidate.source_sha256 != entry["learning_sha256"]:
            raise MontageLearningCanonicalAdmissionError("generic source cross-binding mismatch")
        receipt = GenericReviewObservationReceipt._from_dict(entry["receipt"])
        if receipt.record_id != entry["record_id"] or receipt.learning_sha256 != entry["learning_sha256"] or receipt.ledger_revision != index:
            raise MontageLearningCanonicalAdmissionError("generic receipt cross-binding mismatch")
        prior = seen.get(entry["record_id"])
        if prior is not None and prior != entry["learning_sha256"]:
            raise MontageLearningCanonicalAdmissionError("generic record collision")
        if receipt.status == ACCEPTED:
            if prior is not None:
                raise MontageLearningCanonicalAdmissionError("generic ACCEPTED replay")
            accepted_receipts[entry["record_id"]] = receipt.receipt_sha256
        elif receipt.duplicate_of_receipt_sha256 != accepted_receipts.get(entry["record_id"]):
            raise MontageLearningCanonicalAdmissionError("generic DUPLICATE lineage mismatch")
        seen[entry["record_id"]] = entry["learning_sha256"]
    if body["ledger_sha256"] != _hash(_GENERIC_LEDGER_DOMAIN, _without(body, "ledger_sha256")):
        raise MontageLearningCanonicalAdmissionError("generic ledger digest mismatch")
    return body


class MontageLearningCanonicalAdmissionTransactionStore:
    """Canonical exact-admission writer and trusted latest-reader."""

    def __init__(self, project_root: str | Path, external_anchor_root: str | Path,
                 *, canonical_store_id: str, bridge_instance_id: str) -> None:
        self.project_root = _root(project_root, "project_root")
        self.external_anchor_root = _root(external_anchor_root, "external_anchor_root")
        try:
            self.external_anchor_root.relative_to(self.project_root)
        except ValueError:
            pass
        else:
            raise MontageLearningCanonicalAdmissionError("anchor root must be external")
        try:
            self.project_root.relative_to(self.external_anchor_root)
        except ValueError:
            pass
        else:
            raise MontageLearningCanonicalAdmissionError("Project root must be external to anchor")
        self.canonical_store_id = _identifier(canonical_store_id, "canonical_store_id")
        self.bridge_instance_id = _identifier(bridge_instance_id, "bridge_instance_id")
        state = self.project_root / "state"
        if not state.exists():
            state.mkdir()
        if _is_reparse(state) or not state.is_dir():
            raise MontageLearningCanonicalAdmissionError("state root is unsafe")
        self.canonical_path = self.project_root / CANONICAL_RELATIVE_PATH
        self.receipt_path = self.project_root / RECEIPT_RELATIVE_PATH
        self.journal_path = self.project_root / JOURNAL_RELATIVE_PATH
        self.generic_observation_path = self.project_root / GENERIC_OBSERVATION_RELATIVE_PATH
        self.anchor_path = self.external_anchor_root / ANCHOR_FILE_NAME
        self.anchor_recovery_path = self.external_anchor_root / ANCHOR_RECOVERY_FILE_NAME
        self._validate_paths()

    def _validate_paths(self) -> None:
        for path in (self.canonical_path, self.receipt_path, self.journal_path,
                     self.generic_observation_path, self.anchor_path,
                     self.anchor_recovery_path):
            _target(path)

    @contextmanager
    def _locks(self) -> Iterator[None]:
        with _exclusive_project_lock(ProductProjectManifestStore.path(self.project_root)):
            with exclusive_file_update_lock(self.anchor_path):
                self._validate_paths()
                yield

    @staticmethod
    def _optional(path: Path, parser: Callable[[Mapping[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        return None if not path.exists() else _read(path, parser)

    def _readback(self, raw: Mapping[str, Any], *, staging_store_id: str,
                  owner_scope_hash: str, staging_revision: int,
                  staging_entry_sha256: str):
        return verify_montage_learning_durable_staging_readback(
            raw,
            project_root=self.project_root,
            store_id=staging_store_id,
            expected_owner_scope_hash=owner_scope_hash,
            expected_revision=staging_revision,
            expected_staging_entry_sha256=staging_entry_sha256,
        )

    def _current(self, manifest: ProductProjectManifest, scope: str) -> tuple[
        dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]
    ]:
        canonical = self._optional(self.canonical_path, _parse_canonical)
        anchor = self._optional(self.anchor_path, _parse_anchor)
        if (canonical is None) != (anchor is None):
            raise MontageLearningCanonicalAdmissionError("canonical/anchor split brain")
        registry = (_empty_registry(manifest.project_id, self.canonical_store_id, scope)
                    if not self.receipt_path.exists() else _read(self.receipt_path, _parse_registry))
        if registry["project_id"] != manifest.project_id or registry["canonical_store_id"] != self.canonical_store_id or registry["owner_scope_hash"] != scope:
            raise MontageLearningCanonicalAdmissionError("registry scope mismatch")
        if canonical is not None:
            if (canonical["project_id"] != manifest.project_id or
                canonical["canonical_store_id"] != self.canonical_store_id or
                canonical["owner_scope_hash"] != scope or anchor is None or
                anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
                anchor["anchor"]["anchor_sha256"] != canonical["external_anchor_sha256"]):
                raise MontageLearningCanonicalAdmissionError("canonical/anchor binding mismatch")
        return canonical, anchor, registry

    def _target_manifest(self, source: ProductProjectManifest,
                         canonical_bytes: bytes, updated_at: str) -> ProductProjectManifest:
        binding = ProjectChildBinding(
            domain_owner=TASK_OWNER,
            relative_path=CANONICAL_RELATIVE_PATH.as_posix(),
            format_id=CANONICAL_FORMAT_ID,
            format_version=CANONICAL_FORMAT_VERSION,
            content_sha256=sha256_bytes(canonical_bytes),
            required=True,
        )
        bindings = [item for item in source.child_bindings if item.identity != binding.identity]
        bindings.append(binding)
        return ProductProjectManifest.create(
            project_id=source.project_id,
            project_revision=source.project_revision + 1,
            product_version=source.product_version,
            timebase=source.timebase,
            child_bindings=bindings,
            created_at=source.created_at,
            updated_at=updated_at,
        )

    def _make_proposal(self, raw: Mapping[str, Any], *, staging_store_id: str,
                       owner_scope_hash: str, staging_revision: int,
                       staging_entry_sha256: str, expected_commit: str | None,
                       expected_anchor: str | None, processed_at: str) -> dict[str, Any]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        readback_result = self._readback(
            raw, staging_store_id=staging_store_id, owner_scope_hash=owner_scope_hash,
            staging_revision=staging_revision,
            staging_entry_sha256=staging_entry_sha256,
        )
        readback = readback_result.to_dict()
        if readback["project_id"] != manifest.project_id:
            raise MontageLearningCanonicalAdmissionError("staging Project mismatch")
        canonical, anchor_doc, registry = self._current(manifest, owner_scope_hash)
        current_commit = None if canonical is None else canonical["canonical_store_commit_sha256"]
        current_anchor = None if anchor_doc is None else anchor_doc["external_anchor_document_sha256"]
        if current_commit != expected_commit or current_anchor != expected_anchor:
            raise MontageLearningCanonicalAdmissionError("canonical CAS is stale")
        ledger = (MontageLearningCanonicalLedgerCandidate.empty(
            project_id=manifest.project_id,
            canonical_store_id=self.canonical_store_id,
            owner_scope_hash=owner_scope_hash,
        ) if canonical is None else MontageLearningCanonicalLedgerCandidate.from_dict(canonical["ledger"]))
        append = evaluate_montage_learning_canonical_append(
            ledger, MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger),
            readback_result,
        ).to_dict()
        if append["decision"] == AppendDecision.ID_COLLISION_REJECTED.value:
            raise MontageLearningCanonicalAdmissionError("canonical identity collision")
        if append["decision"] == AppendDecision.STALE_CAS_REJECTED.value:
            raise MontageLearningCanonicalAdmissionError("canonical append CAS rejected")
        attempt = 1 + sum(
            item["idempotency_key_sha256"] == readback["idempotency_key_sha256"]
            for item in registry["receipts"]
        )
        if append["decision"] == AppendDecision.DUPLICATE_CANDIDATE.value:
            if canonical is None or anchor_doc is None:
                raise MontageLearningCanonicalAdmissionError("duplicate lacks committed state")
            roots = [item for item in registry["receipts"]
                     if item["status"] == ACCEPTED and
                     item["idempotency_key_sha256"] == readback["idempotency_key_sha256"] and
                     item["canonical_store_commit_sha256"] == current_commit]
            if len(roots) != 1:
                raise MontageLearningCanonicalAdmissionError("duplicate lineage is not exact")
            target_manifest = manifest
            proposed_canonical = canonical
            proposed_anchor = anchor_doc
            status = DUPLICATE
            duplicate_of = roots[0]["receipt_sha256"]
        elif append["decision"] == AppendDecision.APPEND_CANDIDATE.value:
            proposed_ledger = MontageLearningCanonicalLedgerCandidate.from_dict(
                append["proposed_ledger"]
            )
            current_anchor_candidate = (None if anchor_doc is None else
                MontageLearningExternalMonotonicAnchorCandidate.from_dict(anchor_doc["anchor"]))
            expectation = (
                MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(proposed_ledger)
                if current_anchor_candidate is None else
                MontageLearningExternalMonotonicAnchorExpectation.for_anchor(current_anchor_candidate)
            )
            anchor_evaluation = evaluate_montage_learning_external_monotonic_anchor(
                current_anchor_candidate, expectation,
                None if canonical is None else ledger, proposed_ledger,
            ).to_dict()
            if anchor_evaluation["decision"] not in {
                AnchorDecision.BOOTSTRAP_CANDIDATE.value,
                AnchorDecision.ADVANCE_CANDIDATE.value,
            }:
                raise MontageLearningCanonicalAdmissionError("external anchor transition rejected")
            anchor_candidate = anchor_evaluation["proposed_anchor"]
            proposed_canonical = _build_canonical(
                manifest.project_manifest_sha256, proposed_ledger.to_dict(), anchor_candidate
            )
            canonical_bytes = canonical_json_bytes(proposed_canonical) + b"\n"
            target_manifest = self._target_manifest(manifest, canonical_bytes, processed_at)
            proposed_anchor = _build_anchor(
                proposed_canonical, anchor_candidate, target_manifest.project_manifest_sha256,
                target_manifest.project_revision,
            )
            status = ACCEPTED
            duplicate_of = None
        else:
            raise MontageLearningCanonicalAdmissionError("append decision is unsupported")
        receipt = _mint_receipt(
            readback=readback,
            commit=proposed_canonical["canonical_store_commit_sha256"],
            status=status,
            duplicate_of=duplicate_of,
            attempt=attempt,
            bridge_instance_id=self.bridge_instance_id,
            processed_at=processed_at,
        )
        proposed_registry = _append_registry(registry, receipt)
        journal: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "MONTAGE_LEARNING_CANONICAL_ADMISSION_TRANSACTION",
            "task_owner": TASK_OWNER,
            "operation": status,
            "project_id": manifest.project_id,
            "canonical_store_id": self.canonical_store_id,
            "owner_scope_hash": owner_scope_hash,
            "staging_readback_sha256": readback["readback_sha256"],
            "expected_previous_commit_sha256": current_commit,
            "expected_previous_anchor_document_sha256": current_anchor,
            "expected_previous_registry_sha256": registry["registry_sha256"] if self.receipt_path.exists() else None,
            "proposed_canonical": proposed_canonical,
            "proposed_anchor": proposed_anchor,
            "proposed_registry": proposed_registry,
            "target_manifest": target_manifest.to_dict(),
            "receipt_sha256": receipt["receipt_sha256"],
        }
        journal["journal_sha256"] = _hash(_JOURNAL_DOMAIN, journal)
        return _parse_journal(journal)

    def _participant(self, journal: Mapping[str, Any],
                     failure_hook: FailureHook | None = None) -> _AnchorParticipant:
        source_manifest_sha256 = str(journal["proposed_canonical"]["source_project_manifest_sha256"])
        return _AnchorParticipant(
            project_id=str(journal["project_id"]),
            anchor_path=self.anchor_path,
            recovery_path=self.anchor_recovery_path,
            expected_sha256=journal["expected_previous_anchor_document_sha256"],
            target_anchor=journal["proposed_anchor"],
            source_manifest_sha256=source_manifest_sha256,
            target_manifest_sha256=str(journal["target_manifest"]["project_manifest_sha256"]),
            failure_hook=failure_hook,
        )

    @contextmanager
    def _commit_guard(self, journal: Mapping[str, Any], raw: Mapping[str, Any], *,
                      staging_store_id: str, owner_scope_hash: str,
                      staging_revision: int, staging_entry_sha256: str) -> Iterator[None]:
        with exclusive_file_update_lock(self.anchor_path):
            self._validate_paths()
            readback = self._readback(
                raw, staging_store_id=staging_store_id,
                owner_scope_hash=owner_scope_hash,
                staging_revision=staging_revision,
                staging_entry_sha256=staging_entry_sha256,
            )
            if readback.to_dict()["readback_sha256"] != journal["staging_readback_sha256"]:
                raise MontageLearningCanonicalAdmissionError("staging changed before commit")
            live = ProductProjectManifestStore.load(self.project_root)
            source_sha = journal["proposed_canonical"]["source_project_manifest_sha256"]
            target_sha = journal["target_manifest"]["project_manifest_sha256"]
            if live.project_manifest_sha256 not in {source_sha, target_sha}:
                raise MontageLearningCanonicalAdmissionError("Project moved outside transaction")
            current_canonical = self._optional(self.canonical_path, _parse_canonical)
            current_anchor = self._optional(self.anchor_path, _parse_anchor)
            current_anchor_sha = None if current_anchor is None else current_anchor["external_anchor_document_sha256"]
            if current_anchor_sha not in {
                journal["expected_previous_anchor_document_sha256"],
                journal["proposed_anchor"]["external_anchor_document_sha256"],
            }:
                raise MontageLearningCanonicalAdmissionError("anchor changed outside transaction")
            current_commit = (None if current_canonical is None else
                              current_canonical["canonical_store_commit_sha256"])
            if (live.project_manifest_sha256 == source_sha and
                current_commit == journal["expected_previous_commit_sha256"] and
                current_anchor_sha == journal["expected_previous_anchor_document_sha256"]):
                recompiled = self._make_proposal(
                    raw,
                    staging_store_id=staging_store_id,
                    owner_scope_hash=owner_scope_hash,
                    staging_revision=staging_revision,
                    staging_entry_sha256=staging_entry_sha256,
                    expected_commit=journal["expected_previous_commit_sha256"],
                    expected_anchor=journal["expected_previous_anchor_document_sha256"],
                    processed_at=journal["proposed_registry"]["receipts"][-1]["processed_at"],
                )
                if recompiled != journal:
                    raise MontageLearningCanonicalAdmissionError("P1C-B/C/D recompile drifted")
            elif current_commit not in {
                journal["expected_previous_commit_sha256"],
                journal["proposed_canonical"]["canonical_store_commit_sha256"],
            }:
                raise MontageLearningCanonicalAdmissionError("canonical changed outside transaction")
            if not self.journal_path.exists():
                AtomicJsonWriter.write(self.journal_path, journal, validator=_parse_journal)
            elif _read(self.journal_path, _parse_journal) != journal:
                raise MontageLearningCanonicalAdmissionError("pending transaction conflicts")
            yield

    def _finish(self, journal: Mapping[str, Any], *, recovered: bool,
                failure_hook: FailureHook | None) -> MontageLearningCanonicalAdmissionResult:
        coordinator = ProductProjectSaveCoordinator()
        with self._locks():
            manifest = ProductProjectManifestStore.load(self.project_root)
            target_manifest = parse_product_project_manifest(journal["target_manifest"])
            if manifest.project_manifest_sha256 != target_manifest.project_manifest_sha256:
                raise MontageLearningCanonicalAdmissionError("target manifest is not committed")
            coordinator.require_current_integrity(self.project_root, target_manifest)
            canonical = _read(self.canonical_path, _parse_canonical)
            anchor = _read(self.anchor_path, _parse_anchor)
            if canonical != journal["proposed_canonical"] or anchor != journal["proposed_anchor"]:
                raise MontageLearningCanonicalAdmissionError("canonical/anchor read-back mismatch")
            registry = (None if not self.receipt_path.exists() else
                        _read(self.receipt_path, _parse_registry))
            expected_registry_sha = journal["expected_previous_registry_sha256"]
            proposed = journal["proposed_registry"]
            if registry is None:
                if expected_registry_sha is not None:
                    raise MontageLearningCanonicalAdmissionError("receipt registry disappeared")
            elif registry["registry_sha256"] not in {expected_registry_sha, proposed["registry_sha256"]}:
                raise MontageLearningCanonicalAdmissionError("receipt registry split brain")
            if registry != proposed:
                AtomicJsonWriter.write(self.receipt_path, proposed, validator=_parse_registry)
                if failure_hook is not None:
                    failure_hook("after_receipt_write", self.receipt_path)
            registry = _read(self.receipt_path, _parse_registry)
            if registry != proposed:
                raise MontageLearningCanonicalAdmissionError("receipt durable read-back failed")
            receipt_body = registry["receipts"][-1]
            if receipt_body["receipt_sha256"] != journal["receipt_sha256"]:
                raise MontageLearningCanonicalAdmissionError("receipt lineage changed")
            self.journal_path.unlink(missing_ok=True)
            return MontageLearningCanonicalAdmissionResult(
                receipt=parse_montage_learning_admission_receipt(receipt_body),
                canonical_store_commit_sha256=canonical["canonical_store_commit_sha256"],
                external_anchor_document_sha256=anchor["external_anchor_document_sha256"],
                recovered=recovered,
            )

    def _run_accepted(self, journal: Mapping[str, Any], raw: Mapping[str, Any], *,
                      staging_store_id: str, owner_scope_hash: str,
                      staging_revision: int, staging_entry_sha256: str,
                      failure_hook: FailureHook | None, recovered: bool) -> None:
        coordinator = ProductProjectSaveCoordinator()
        participant = self._participant(journal, failure_hook)
        target_manifest = parse_product_project_manifest(journal["target_manifest"])
        canonical_bytes = canonical_json_bytes(journal["proposed_canonical"]) + b"\n"

        def guard() -> Iterator[None]:
            return self._commit_guard(
                journal, raw,
                staging_store_id=staging_store_id,
                owner_scope_hash=owner_scope_hash,
                staging_revision=staging_revision,
                staging_entry_sha256=staging_entry_sha256,
            )

        status = coordinator.recovery_status(self.project_root)
        if status["required"]:
            coordinator.recover_complete(
                self.project_root,
                transaction_id=str(status["transaction_id"]),
                participant=participant,
                commit_guard=guard,
            )
        else:
            live = ProductProjectManifestStore.load(self.project_root)
            if live.project_manifest_sha256 != target_manifest.project_manifest_sha256:
                coordinator.save(
                    self.project_root,
                    target_manifest,
                    {CANONICAL_RELATIVE_PATH.as_posix(): canonical_bytes},
                    expected_previous_manifest_sha256=str(
                        journal["proposed_canonical"]["source_project_manifest_sha256"]
                    ),
                    participant=participant,
                    commit_guard=guard,
                )
        if failure_hook is not None:
            failure_hook(
                "after_project_save_committed" if not recovered else "after_project_save_recovered",
                self.canonical_path,
            )

    def admit_exact(
        self,
        delivery: Mapping[str, Any],
        *,
        staging_store_id: str,
        expected_owner_scope_hash: str,
        expected_staging_revision: int,
        expected_staging_entry_sha256: str,
        expected_canonical_store_commit_sha256: str | None,
        expected_external_anchor_document_sha256: str | None,
        failure_hook: FailureHook | None = None,
    ) -> MontageLearningCanonicalAdmissionResult:
        """Commit one exact delivery or emit an exact idempotent DUPLICATE."""
        if failure_hook is not None and not callable(failure_hook):
            raise TypeError("failure_hook must be callable")
        raw = _exact(delivery, "delivery", max_nodes=200_000)
        store_id = _identifier(staging_store_id, "staging_store_id")
        scope = _sha(expected_owner_scope_hash, "expected_owner_scope_hash")
        revision = _integer(expected_staging_revision, "expected_staging_revision", 1, 4096)
        entry_sha = _sha(expected_staging_entry_sha256, "expected_staging_entry_sha256")
        expected_commit = _sha(
            expected_canonical_store_commit_sha256,
            "expected_canonical_store_commit_sha256", nullable=True,
        )
        expected_anchor = _sha(
            expected_external_anchor_document_sha256,
            "expected_external_anchor_document_sha256", nullable=True,
        )
        recovered = False
        with self._locks():
            if self.journal_path.exists():
                journal = _read(self.journal_path, _parse_journal)
                recovered = True
                readback = self._readback(
                    raw, staging_store_id=store_id, owner_scope_hash=scope,
                    staging_revision=revision, staging_entry_sha256=entry_sha,
                )
                if (journal["staging_readback_sha256"] != readback.to_dict()["readback_sha256"] or
                    journal["owner_scope_hash"] != scope or
                    journal["expected_previous_commit_sha256"] != expected_commit or
                    journal["expected_previous_anchor_document_sha256"] != expected_anchor):
                    raise MontageLearningCanonicalAdmissionError("retry does not match pending transaction")
            else:
                journal = self._make_proposal(
                    raw,
                    staging_store_id=store_id,
                    owner_scope_hash=scope,
                    staging_revision=revision,
                    staging_entry_sha256=entry_sha,
                    expected_commit=expected_commit,
                    expected_anchor=expected_anchor,
                    processed_at=_now(),
                )
                if journal["operation"] == DUPLICATE:
                    AtomicJsonWriter.write(self.journal_path, journal, validator=_parse_journal)
                    if failure_hook is not None:
                        failure_hook("after_journal_write", self.journal_path)
        if journal["operation"] == ACCEPTED:
            self._run_accepted(
                journal, raw,
                staging_store_id=store_id,
                owner_scope_hash=scope,
                staging_revision=revision,
                staging_entry_sha256=entry_sha,
                failure_hook=failure_hook,
                recovered=recovered,
            )
        return self._finish(journal, recovered=recovered, failure_hook=failure_hook)

    def get_verified_receipt(
        self, *, receipt_sha256: str | None = None,
    ) -> MontageLearningVerifiedAdmissionReceipt:
        """Return a sealed receipt only after canonical currentness revalidation."""
        wanted = _sha(receipt_sha256, "receipt_sha256", nullable=True)
        coordinator = ProductProjectSaveCoordinator()
        with self._locks():
            if self.journal_path.exists() or coordinator.recovery_status(self.project_root)["required"]:
                raise MontageLearningCanonicalAdmissionError("canonical recovery is pending")
            manifest = ProductProjectManifestStore.load(self.project_root)
            coordinator.require_current_integrity(self.project_root, manifest)
            canonical = _read(self.canonical_path, _parse_canonical)
            anchor = _read(self.anchor_path, _parse_anchor)
            registry = _read(self.receipt_path, _parse_registry)
            binding = next((item for item in manifest.child_bindings
                            if item.identity == (TASK_OWNER, CANONICAL_RELATIVE_PATH.as_posix())), None)
            canonical_bytes = canonical_json_bytes(canonical) + b"\n"
            if (binding is None or binding.format_id != CANONICAL_FORMAT_ID or
                binding.format_version != CANONICAL_FORMAT_VERSION or
                binding.content_sha256 != sha256_bytes(canonical_bytes) or
                manifest.project_revision < anchor["target_project_manifest_revision"] or
                anchor["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"] or
                anchor["anchor"]["anchor_sha256"] != canonical["external_anchor_sha256"]):
                raise MontageLearningCanonicalAdmissionError("canonical currentness mismatch")
            matches = [item for item in registry["receipts"]
                       if wanted is None or item["receipt_sha256"] == wanted]
            if len(matches) != 1 and wanted is not None:
                raise MontageLearningCanonicalAdmissionError("receipt is not uniquely present")
            if wanted is None:
                if not registry["receipts"]:
                    raise MontageLearningCanonicalAdmissionError("receipt registry is empty")
                matches = [registry["receipts"][-1]]
            selected = matches[0]
            if selected["canonical_store_commit_sha256"] != canonical["canonical_store_commit_sha256"]:
                raise MontageLearningCanonicalAdmissionError("receipt is not current")
            return MontageLearningVerifiedAdmissionReceipt(
                parse_montage_learning_admission_receipt(selected),
                manifest.project_manifest_sha256,
                anchor["external_anchor_document_sha256"],
                _token=_VERIFIED_TOKEN,
            )

    def record_exact_generic_observation(
        self,
        delivery: Mapping[str, Any],
        *,
        expected_revision: int,
        generic_store_id: str = "task058-generic-review-observations",
    ) -> GenericReviewObservationReceipt:
        """Durably record one generic review observation in a separate namespace.

        ACCEPTED/DUPLICATE here only mean immutable observation storage.  They
        never mean exact learning admission, adoption, Profile generation or
        Timeline mutation.
        """
        raw = _exact(delivery, "generic delivery", max_nodes=200_000)
        candidate = validate_generic_learning_delivery(raw)
        store_id = _identifier(generic_store_id, "generic_store_id")
        expected = _integer(expected_revision, "expected_revision", 0, _MAX_RECEIPTS - 1)
        coordinator = ProductProjectSaveCoordinator()
        manifest = ProductProjectManifestStore.load(self.project_root)
        current = (None if not self.generic_observation_path.exists() else
                   _read(self.generic_observation_path, _parse_generic_ledger))
        if current is None:
            if expected != 0:
                raise MontageLearningCanonicalAdmissionError("generic CAS is stale")
            entries: list[dict[str, Any]] = []
            previous_ledger_sha256 = _hash(_GENERIC_LEDGER_DOMAIN, {
                "project_id": manifest.project_id, "store_id": store_id, "revision": 0,
            })
        else:
            if (current["project_id"] != manifest.project_id or
                current["store_id"] != store_id or current["revision"] != expected):
                raise MontageLearningCanonicalAdmissionError("generic CAS/scope is stale")
            entries = list(current["entries"])
            previous_ledger_sha256 = current["ledger_sha256"]
        same_record = [entry for entry in entries if entry["record_id"] == candidate.record_id]
        if same_record and any(entry["learning_sha256"] != candidate.source_sha256
                               for entry in same_record):
            raise MontageLearningCanonicalAdmissionError("generic record identity collision")
        status = DUPLICATE if same_record else ACCEPTED
        duplicate_of = (None if not same_record else
                        next(entry["receipt"]["receipt_sha256"] for entry in same_record
                             if entry["receipt"]["status"] == ACCEPTED))
        revision = len(entries) + 1
        timestamp = _now()
        receipt_id_hash = _hash(_GENERIC_RECEIPT_DOMAIN, {
            "record_id": candidate.record_id,
            "learning_sha256": candidate.source_sha256,
            "revision": revision,
            "status": status,
        }).removeprefix("sha256:")
        receipt_body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "GENERIC_REVIEW_OBSERVATION_RECEIPT",
            "task_owner": TASK_OWNER,
            "namespace": "GENERIC_REVIEW_OBSERVATION_ONLY",
            "source_contract_profile": GENERIC_CONTRACT_PROFILE,
            "record_id": candidate.record_id,
            "learning_sha256": candidate.source_sha256,
            "status": status,
            "receipt_id": f"generic-{receipt_id_hash[:40]}-{revision}",
            "timestamp": timestamp,
            "ledger_revision": revision,
            "previous_ledger_sha256": previous_ledger_sha256,
            "duplicate_of_receipt_sha256": duplicate_of,
            "canonical_store_written": True,
            "serialized_receipt_authoritative": False,
            "learning_adoption_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "profile_generation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
            "release_authorized": False,
            "deploy_authorized": False,
            "production_authorized": False,
        }
        receipt_body["receipt_sha256"] = _hash(_GENERIC_RECEIPT_DOMAIN, receipt_body)
        receipt = GenericReviewObservationReceipt._from_dict(receipt_body)
        entry = {
            "revision": revision,
            "record_id": candidate.record_id,
            "learning_sha256": candidate.source_sha256,
            "source_delivery": raw,
            "source_delivery_sha256": sha256_bytes(canonical_json_bytes(raw)),
            "receipt": receipt.to_dict(),
        }
        ledger: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "GENERIC_REVIEW_OBSERVATION_LEDGER",
            "task_owner": TASK_OWNER,
            "namespace": "GENERIC_REVIEW_OBSERVATION_ONLY",
            "project_id": manifest.project_id,
            "store_id": store_id,
            "revision": revision,
            "entries": [*entries, entry],
            "canonical_store_written": True,
            "learning_adoption_authorized": False,
            "automatic_learning_promotion_authorized": False,
            "profile_generation_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }
        ledger["ledger_sha256"] = _hash(_GENERIC_LEDGER_DOMAIN, ledger)
        ledger = _parse_generic_ledger(ledger)
        document = canonical_json_bytes(ledger) + b"\n"
        binding = ProjectChildBinding(
            TASK_OWNER,
            GENERIC_OBSERVATION_RELATIVE_PATH.as_posix(),
            GENERIC_OBSERVATION_FORMAT_ID,
            GENERIC_OBSERVATION_FORMAT_VERSION,
            sha256_bytes(document),
            True,
        )
        bindings = [item for item in manifest.child_bindings if item.identity != binding.identity]
        bindings.append(binding)
        target_manifest = ProductProjectManifest.create(
            project_id=manifest.project_id,
            project_revision=manifest.project_revision + 1,
            product_version=manifest.product_version,
            timebase=manifest.timebase,
            child_bindings=bindings,
            created_at=manifest.created_at,
            updated_at=timestamp,
        )
        coordinator.save(
            self.project_root,
            target_manifest,
            {GENERIC_OBSERVATION_RELATIVE_PATH.as_posix(): document},
            expected_previous_manifest_sha256=manifest.project_manifest_sha256,
        )
        coordinator.require_current_integrity(self.project_root, target_manifest)
        readback = _read(self.generic_observation_path, _parse_generic_ledger)
        if readback != ledger or readback["entries"][-1]["receipt"] != receipt.to_dict():
            raise MontageLearningCanonicalAdmissionError("generic durable read-back mismatch")
        return receipt


__all__ = [
    "ANCHOR_FILE_NAME", "CANONICAL_RELATIVE_PATH", "JOURNAL_RELATIVE_PATH",
    "RECEIPT_RELATIVE_PATH", "SCHEMA_VERSION",
    "MontageLearningCanonicalAdmissionError",
    "MontageLearningCanonicalAdmissionResult",
    "MontageLearningCanonicalAdmissionTransactionStore",
    "MontageLearningVerifiedAdmissionReceipt",
    "GENERIC_OBSERVATION_RELATIVE_PATH", "GenericReviewObservationReceipt",
]
