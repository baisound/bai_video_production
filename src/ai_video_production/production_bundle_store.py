"""Crash-safe cross-store manifest for TASK-037..041 production state.

Individual stores are already atomic and self-checksummed.  This module adds a
small *bundle manifest* that pins the exact Production/Audit/Prompt/Continuity/
Audio snapshot identities that were validated together.  It never attempts
silent repair: a partially updated set fails closed until an operator/session
rebuilds a new validated manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .audio_workspace import AudioWorkspaceRegistry
from .audio_workspace_store import AudioWorkspaceSnapshotStore
from .candidate_audit import CandidateAuditRegistry
from .candidate_audit_store import CandidateAuditSnapshotStore
from .continuity_registry import ContinuityRegistry
from .continuity_registry_store import ContinuityRegistryStore
from .errors import ProductError, ProductErrorCategory
from .production_bundle_validation import ProductionBundleValidationReport, ProductionBundleValidator
from .production_control import ProductionControlRegistry
from .production_control_store import ProductionControlSnapshotStore
from .prompt_registry import PromptGenerationRegistry
from .prompt_registry_store import PromptRegistrySnapshotStore
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_MANIFEST_BYTES = 1024 * 1024
_FILES = {
    "production": "production-control.json",
    "audits": "candidate-audit.json",
    "prompts": "prompt-registry.json",
    "continuity": "continuity-registry.json",
    "audio": "audio-workspace.json",
}


@dataclass(frozen=True, slots=True)
class ProductionBundleState:
    production: ProductionControlRegistry
    audits: CandidateAuditRegistry
    prompts: PromptGenerationRegistry
    continuity: ContinuityRegistry
    audio: AudioWorkspaceRegistry
    validation: ProductionBundleValidationReport
    manifest_sha256: str


def _snapshot_hashes(
    *,
    production: ProductionControlRegistry,
    audits: CandidateAuditRegistry,
    prompts: PromptGenerationRegistry,
    continuity: ContinuityRegistry,
    audio: AudioWorkspaceRegistry,
) -> dict[str, str]:
    return {
        "production": ProductionControlSnapshotStore.snapshot(production)["snapshot_sha256"],
        "audits": CandidateAuditSnapshotStore.snapshot(audits)["snapshot_sha256"],
        "prompts": PromptRegistrySnapshotStore.snapshot(prompts)["snapshot_sha256"],
        "continuity": ContinuityRegistryStore.snapshot(continuity)["registry_sha256"],
        "audio": AudioWorkspaceSnapshotStore.snapshot(audio)["snapshot_sha256"],
    }


def _manifest(hashes: dict[str, str]) -> dict[str, Any]:
    if set(hashes) != set(_FILES):
        raise ValueError("bundle hashes must contain every canonical store")
    body: dict[str, Any] = {
        "bundle_version": "1.0.0",
        "task_owner": "TASK-037..041",
        "stores": {
            key: {"relative_path": _FILES[key], "snapshot_sha256": hashes[key]}
            for key in sorted(_FILES)
        },
        "automatic_repair_authorized": False,
        "automatic_regeneration_authorized": False,
    }
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse_manifest(document: dict[str, Any]) -> dict[str, str]:
    if document.get("bundle_version") != "1.0.0" or document.get("task_owner") != "TASK-037..041":
        raise ProductError(
            "ERR_PRODUCTION_BUNDLE_MANIFEST_VERSION",
            "Unsupported Production bundle manifest",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    expected = document.get("manifest_sha256")
    body = {key: value for key, value in document.items() if key != "manifest_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError(
            "ERR_PRODUCTION_BUNDLE_MANIFEST_CHECKSUM",
            "Production bundle manifest checksum mismatch",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if document.get("automatic_repair_authorized") is not False or document.get("automatic_regeneration_authorized") is not False:
        raise ProductError(
            "ERR_PRODUCTION_BUNDLE_MANIFEST_BOUNDARY",
            "Production bundle manifest cannot grant repair/regeneration authority",
            ProductErrorCategory.SECURITY,
        )
    stores = document.get("stores")
    if not isinstance(stores, dict) or set(stores) != set(_FILES):
        raise ProductError(
            "ERR_PRODUCTION_BUNDLE_MANIFEST_STORES",
            "Production bundle manifest must pin every canonical store exactly once",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    hashes: dict[str, str] = {}
    for key, filename in _FILES.items():
        row = stores.get(key)
        if not isinstance(row, dict) or set(row) != {"relative_path", "snapshot_sha256"}:
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_STORES",
                "Production bundle store reference is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"store": key},
            )
        if row["relative_path"] != filename:
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_PATH",
                "Production bundle manifest may reference only fixed relative store names",
                ProductErrorCategory.SECURITY,
                details={"store": key},
            )
        value = row["snapshot_sha256"]
        if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_HASH",
                "Production bundle store checksum is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"store": key},
            )
        hashes[key] = value
    return hashes


class ProductionBundleManifestStore:
    @staticmethod
    def build(
        *,
        production: ProductionControlRegistry,
        audits: CandidateAuditRegistry,
        prompts: PromptGenerationRegistry,
        continuity: ContinuityRegistry,
        audio: AudioWorkspaceRegistry,
    ) -> dict[str, Any]:
        # A manifest may only be produced for a cross-store consistent set.
        ProductionBundleValidator.validate(
            production=production,
            audits=audits,
            prompts=prompts,
            continuity=continuity,
            audio=audio,
        )
        return _manifest(_snapshot_hashes(
            production=production,
            audits=audits,
            prompts=prompts,
            continuity=continuity,
            audio=audio,
        ))

    @staticmethod
    def save(
        path: str | Path,
        document: dict[str, Any],
        *,
        expected_previous_manifest_sha256: str | None = None,
    ) -> AtomicWriteResult:
        _parse_manifest(document)
        target = Path(path)
        if target.is_symlink():
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_FILE_INVALID",
                "Refusing to replace a symlink Production bundle manifest",
                ProductErrorCategory.SECURITY,
            )
        if target.exists():
            if not target.is_file():
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_MANIFEST_FILE_INVALID",
                    "Production bundle manifest target must be a regular file",
                    ProductErrorCategory.VALIDATION,
                )
            if expected_previous_manifest_sha256 is None:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_MANIFEST_CAS_REQUIRED",
                    "Replacing a Production bundle manifest requires its exact previous checksum",
                    ProductErrorCategory.AUTHORIZATION,
                )
            current = ProductionBundleManifestStore.load_document(target)
            if current["manifest_sha256"] != expected_previous_manifest_sha256:
                raise ProductError(
                    "ERR_PRODUCTION_BUNDLE_MANIFEST_REVISION_CONFLICT",
                    "Production bundle manifest changed before save; reload before retry",
                    ProductErrorCategory.STATE,
                )
        elif expected_previous_manifest_sha256 is not None:
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_PREVIOUS_MISSING",
                "Expected previous Production bundle manifest does not exist",
                ProductErrorCategory.STATE,
            )
        return AtomicJsonWriter.write(target, document, validator=lambda value: _parse_manifest(value))

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_FILE_INVALID",
                "Production bundle manifest must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        size = target.stat().st_size
        if size <= 0 or size > _MAX_MANIFEST_BYTES:
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_SIZE",
                "Production bundle manifest size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
                details={"size_bytes": size},
            )
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_READ",
                "Production bundle manifest could not be read as UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_INVALID",
                "Production bundle manifest root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        _parse_manifest(document)
        return document

    @staticmethod
    def recover(root: str | Path, *, manifest_name: str = "production-bundle.json") -> ProductionBundleState:
        directory = Path(root)
        if directory.is_symlink() or not directory.is_dir():
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_ROOT_INVALID",
                "Production bundle root must be an existing regular non-symlink directory",
                ProductErrorCategory.VALIDATION,
            )
        if manifest_name != "production-bundle.json":
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_MANIFEST_NAME",
                "Production bundle recovery uses the fixed canonical manifest name",
                ProductErrorCategory.SECURITY,
            )
        document = ProductionBundleManifestStore.load_document(directory / manifest_name)
        expected_hashes = _parse_manifest(document)
        production = ProductionControlSnapshotStore.load(directory / _FILES["production"])
        audits = CandidateAuditSnapshotStore.load(directory / _FILES["audits"])
        prompts = PromptRegistrySnapshotStore.load(directory / _FILES["prompts"])
        continuity = ContinuityRegistryStore.recover(directory / _FILES["continuity"])
        audio = AudioWorkspaceSnapshotStore.load(directory / _FILES["audio"])
        observed = _snapshot_hashes(
            production=production,
            audits=audits,
            prompts=prompts,
            continuity=continuity,
            audio=audio,
        )
        if observed != expected_hashes:
            changed = sorted(key for key in _FILES if observed[key] != expected_hashes[key])
            raise ProductError(
                "ERR_PRODUCTION_BUNDLE_SNAPSHOT_SET_CHANGED",
                "Production snapshot set no longer matches the last validated bundle manifest",
                ProductErrorCategory.STATE,
                details={"changed_stores": changed, "automatic_repair_performed": False},
            )
        validation = ProductionBundleValidator.validate(
            production=production,
            audits=audits,
            prompts=prompts,
            continuity=continuity,
            audio=audio,
        )
        return ProductionBundleState(
            production, audits, prompts, continuity, audio, validation, document["manifest_sha256"]
        )
