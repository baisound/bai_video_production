"""TASK-039 crash-safe local persistence for continuity registry state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .continuity_map import ContinuityBoundaryType, ContinuityEdge
from .continuity_registry import ContinuityRegistry, ContinuityResolution
from .errors import ProductError, ProductErrorCategory
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_BYTES = 4 * 1024 * 1024


def _parse(document: dict[str, Any]) -> ContinuityRegistry:
    if document.get("registry_version") != "1.0.0" or document.get("task_owner") != "TASK-039":
        raise ProductError(
            "ERR_CONTINUITY_STORE_VERSION",
            "Unsupported continuity registry document",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    expected = document.get("registry_sha256")
    body = {k: v for k, v in document.items() if k != "registry_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError(
            "ERR_CONTINUITY_STORE_CHECKSUM",
            "Continuity registry checksum mismatch",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    if document.get("automatic_regeneration_started") is not False:
        raise ProductError(
            "ERR_CONTINUITY_STORE_BOUNDARY",
            "Continuity registry must not persist automatic regeneration state",
            ProductErrorCategory.SECURITY,
        )
    value = ContinuityRegistry()
    try:
        for raw in document.get("edges", []):
            value.add_edge(ContinuityEdge(
                edge_id=str(raw["edge_id"]),
                from_scene_id=str(raw["from_scene_id"]),
                from_slot_id=str(raw["from_slot_id"]),
                from_candidate_id=str(raw["from_candidate_id"]),
                from_asset_id=str(raw["from_asset_id"]),
                from_asset_sha256=str(raw["from_asset_sha256"]),
                to_scene_id=str(raw["to_scene_id"]),
                to_slot_id=str(raw["to_slot_id"]),
                boundary_type=ContinuityBoundaryType(str(raw["boundary_type"])),
                character_contract_refs=tuple(raw.get("character_contract_refs", [])),
                space_contract_refs=tuple(raw.get("space_contract_refs", [])),
            ))
        for raw in document.get("resolutions", []):
            resolution = ContinuityResolution(
                edge_id=str(raw["edge_id"]),
                target_asset_id=str(raw["target_asset_id"]),
                target_asset_sha256=str(raw["target_asset_sha256"]),
                status=str(raw["status"]),
                validation_status=str(raw["validation_status"]),
                human_approved_by=raw.get("human_approved_by"),
                reason_code=raw.get("reason_code"),
            )
            if resolution.edge_id not in value.edges:
                raise ValueError("resolution references unknown edge")
            value.resolutions[resolution.edge_id] = resolution
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(
            "ERR_CONTINUITY_STORE_INVALID",
            "Continuity registry document contains invalid domain state",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    # Recomputed domain hash catches any parser normalization drift.
    if value.to_dict()["registry_sha256"] != expected:
        raise ProductError(
            "ERR_CONTINUITY_STORE_DOMAIN_HASH",
            "Continuity registry domain identity changed during recovery",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return value


class ContinuityRegistryStore:
    @staticmethod
    def snapshot(registry: ContinuityRegistry) -> dict[str, Any]:
        return registry.to_dict()

    @staticmethod
    def load_document(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError(
                "ERR_CONTINUITY_STORE_FILE_INVALID",
                "Continuity registry must be a regular non-symlink file",
                ProductErrorCategory.VALIDATION,
            )
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError(
                "ERR_CONTINUITY_STORE_SIZE",
                "Continuity registry size is outside the allowed bound",
                ProductErrorCategory.VALIDATION,
                details={"size_bytes": size},
            )
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError(
                "ERR_CONTINUITY_STORE_READ",
                "Continuity registry could not be read as UTF-8 JSON",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if not isinstance(document, dict):
            raise ProductError(
                "ERR_CONTINUITY_STORE_INVALID",
                "Continuity registry root must be an object",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        _parse(document)
        return document

    @staticmethod
    def save(
        path: str | Path,
        registry: ContinuityRegistry,
        *,
        expected_previous_registry_sha256: str | None = None,
    ) -> AtomicWriteResult:
        target = Path(path)
        if target.is_symlink():
            raise ProductError(
                "ERR_CONTINUITY_STORE_FILE_INVALID",
                "Refusing to replace a symlink continuity registry",
                ProductErrorCategory.SECURITY,
            )
        if target.exists():
            if not target.is_file():
                raise ProductError(
                    "ERR_CONTINUITY_STORE_FILE_INVALID",
                    "Continuity registry target must be a regular file",
                    ProductErrorCategory.VALIDATION,
                )
            if expected_previous_registry_sha256 is None:
                raise ProductError(
                    "ERR_CONTINUITY_STORE_CAS_REQUIRED",
                    "Replacing an existing continuity registry requires its exact previous checksum",
                    ProductErrorCategory.AUTHORIZATION,
                )
            current = ContinuityRegistryStore.load_document(target)["registry_sha256"]
            if current != expected_previous_registry_sha256:
                raise ProductError(
                    "ERR_CONTINUITY_STORE_REVISION_CONFLICT",
                    "Continuity registry changed before save; reload before retry",
                    ProductErrorCategory.STATE,
                )
        elif expected_previous_registry_sha256 is not None:
            raise ProductError(
                "ERR_CONTINUITY_STORE_PREVIOUS_MISSING",
                "Expected previous continuity registry does not exist",
                ProductErrorCategory.STATE,
            )
        return AtomicJsonWriter.write(target, registry.to_dict(), validator=lambda value: _parse(value))

    @staticmethod
    def recover(path: str | Path) -> ContinuityRegistry:
        return _parse(ContinuityRegistryStore.load_document(path))
