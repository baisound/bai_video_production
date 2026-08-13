"""Top-level crash-safe production-session manifest.

Pins the upstream TASK-027/TASK-037 planning bundle together with the downstream
TASK-037..041 production bundle and proves they share the same Production
Control snapshot.  It never repairs a partially advanced store set.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .planning_production_bundle import PlanningProductionBundleState, PlanningProductionBundleStore
from .production_bundle_store import ProductionBundleManifestStore, ProductionBundleState
from .production_control_store import ProductionControlSnapshotStore
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ProductionSessionState:
    planning: PlanningProductionBundleState
    production: ProductionBundleState
    manifest_sha256: str


def _production_hash(document: dict[str, Any], *, source: str) -> str:
    try:
        value = document["stores"]["production"]["snapshot_sha256"]
    except (KeyError, TypeError) as exc:
        raise ProductError(
            "ERR_PRODUCTION_SESSION_CHILD_MANIFEST_INVALID",
            "Child bundle manifest does not expose Production Control snapshot identity",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"source": source},
        ) from exc
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ProductError(
            "ERR_PRODUCTION_SESSION_CHILD_MANIFEST_INVALID",
            "Child bundle Production Control checksum is invalid",
            ProductErrorCategory.DATA_INTEGRITY,
            details={"source": source},
        )
    return value


def _manifest(planning: dict[str, Any], production: dict[str, Any]) -> dict[str, Any]:
    planning_hash = planning.get("manifest_sha256")
    production_hash = production.get("manifest_sha256")
    if not isinstance(planning_hash, str) or not isinstance(production_hash, str):
        raise ProductError("ERR_PRODUCTION_SESSION_CHILD_MANIFEST_INVALID", "Child bundle manifest identity is missing", ProductErrorCategory.DATA_INTEGRITY)
    upstream_production = _production_hash(planning, source="planning")
    downstream_production = _production_hash(production, source="production")
    if upstream_production != downstream_production:
        raise ProductError(
            "ERR_PRODUCTION_SESSION_PRODUCTION_SNAPSHOT_MISMATCH",
            "Planning and downstream Production bundles were not validated against the same Production Control snapshot",
            ProductErrorCategory.STATE,
            details={"automatic_repair_performed": False},
        )
    body: dict[str, Any] = {
        "session_bundle_version": "1.0.0",
        "task_owner": "TASK-027/TASK-037..041",
        "planning_manifest": {
            "relative_path": "planning-production-bundle.json",
            "manifest_sha256": planning_hash,
        },
        "production_manifest": {
            "relative_path": "production-bundle.json",
            "manifest_sha256": production_hash,
        },
        "shared_production_snapshot_sha256": upstream_production,
        "automatic_repair_authorized": False,
        "automatic_regeneration_authorized": False,
        "provider_execution_authorized": False,
    }
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> tuple[str, str, str]:
    if document.get("session_bundle_version") != "1.0.0" or document.get("task_owner") != "TASK-027/TASK-037..041":
        raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_VERSION", "Unsupported Production Session manifest", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("manifest_sha256")
    body = {key: value for key, value in document.items() if key != "manifest_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_CHECKSUM", "Production Session manifest checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if any(document.get(key) is not False for key in (
        "automatic_repair_authorized", "automatic_regeneration_authorized", "provider_execution_authorized"
    )):
        raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_BOUNDARY", "Production Session manifest cannot grant repair/generation/provider authority", ProductErrorCategory.SECURITY)
    planning = document.get("planning_manifest")
    production = document.get("production_manifest")
    if not isinstance(planning, dict) or planning.get("relative_path") != "planning-production-bundle.json":
        raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_PATH", "Planning manifest path must use the canonical relative name", ProductErrorCategory.SECURITY)
    if not isinstance(production, dict) or production.get("relative_path") != "production-bundle.json":
        raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_PATH", "Production manifest path must use the canonical relative name", ProductErrorCategory.SECURITY)
    planning_hash = planning.get("manifest_sha256")
    production_hash = production.get("manifest_sha256")
    shared = document.get("shared_production_snapshot_sha256")
    for value in (planning_hash, production_hash, shared):
        if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_HASH", "Production Session manifest contains an invalid checksum", ProductErrorCategory.DATA_INTEGRITY)
    return planning_hash, production_hash, shared


class ProductionSessionBundleStore:
    @staticmethod
    def build(*, planning_manifest: dict[str, Any], production_manifest: dict[str, Any]) -> dict[str, Any]:
        # Child public loaders/parsers are responsible for their own self-checks;
        # this composition layer verifies the shared Production snapshot identity.
        return _manifest(planning_manifest, production_manifest)

    @staticmethod
    def save(path: str | Path, document: dict[str, Any], *, expected_previous_manifest_sha256: str | None = None) -> AtomicWriteResult:
        _parse(document)
        target = Path(path)
        if target.is_symlink():
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_FILE_INVALID", "Refusing to replace a symlink Production Session manifest", ProductErrorCategory.SECURITY)
        if target.exists():
            if not target.is_file():
                raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_FILE_INVALID", "Production Session manifest target must be a regular file", ProductErrorCategory.VALIDATION)
            if expected_previous_manifest_sha256 is None:
                raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_CAS_REQUIRED", "Replacing Production Session manifest requires exact previous checksum", ProductErrorCategory.AUTHORIZATION)
            current = ProductionSessionBundleStore.load_document(target)
            if current["manifest_sha256"] != expected_previous_manifest_sha256:
                raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_REVISION_CONFLICT", "Production Session manifest changed before save", ProductErrorCategory.STATE)
        elif expected_previous_manifest_sha256 is not None:
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_PREVIOUS_MISSING", "Expected previous Production Session manifest does not exist", ProductErrorCategory.STATE)
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_FILE_INVALID", "Production Session manifest must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_SIZE", "Production Session manifest size is outside the allowed bound", ProductErrorCategory.VALIDATION)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_READ", "Production Session manifest could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(document, dict):
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_INVALID", "Production Session manifest root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        _parse(document)
        return document

    @staticmethod
    def recover(root: str | Path, *, manifest_name: str = "production-session.json") -> ProductionSessionState:
        directory = Path(root)
        if directory.is_symlink() or not directory.is_dir():
            raise ProductError("ERR_PRODUCTION_SESSION_ROOT_INVALID", "Production Session root must be an existing regular non-symlink directory", ProductErrorCategory.VALIDATION)
        if manifest_name != "production-session.json":
            raise ProductError("ERR_PRODUCTION_SESSION_MANIFEST_NAME", "Production Session recovery uses the fixed canonical manifest name", ProductErrorCategory.SECURITY)
        document = ProductionSessionBundleStore.load_document(directory / manifest_name)
        planning_expected, production_expected, shared_expected = _parse(document)
        planning_doc = PlanningProductionBundleStore.load_document(directory / "planning-production-bundle.json")
        production_doc = ProductionBundleManifestStore.load_document(directory / "production-bundle.json")
        if planning_doc["manifest_sha256"] != planning_expected or production_doc["manifest_sha256"] != production_expected:
            raise ProductError(
                "ERR_PRODUCTION_SESSION_CHILD_MANIFEST_CHANGED",
                "A child bundle manifest changed after Production Session checkpoint",
                ProductErrorCategory.STATE,
                details={"automatic_repair_performed": False},
            )
        if _production_hash(planning_doc, source="planning") != shared_expected or _production_hash(production_doc, source="production") != shared_expected:
            raise ProductError("ERR_PRODUCTION_SESSION_PRODUCTION_SNAPSHOT_MISMATCH", "Child bundles no longer pin the same Production Control snapshot", ProductErrorCategory.STATE)
        planning = PlanningProductionBundleStore.recover(directory)
        production = ProductionBundleManifestStore.recover(directory)
        planning_snapshot = ProductionControlSnapshotStore.snapshot(planning.production)["snapshot_sha256"]
        production_snapshot = ProductionControlSnapshotStore.snapshot(production.production)["snapshot_sha256"]
        if planning_snapshot != shared_expected or production_snapshot != shared_expected:
            raise ProductError("ERR_PRODUCTION_SESSION_RECOVERED_PRODUCTION_MISMATCH", "Recovered child bundles do not share the checkpointed Production Control snapshot", ProductErrorCategory.DATA_INTEGRITY)
        return ProductionSessionState(planning, production, document["manifest_sha256"])
