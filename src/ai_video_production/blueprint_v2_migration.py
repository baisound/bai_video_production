"""Read-only v1 to v2 migration preview; this module never writes or grants GO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .production_blueprint import ProductionBlueprint, ReferenceKind
from .production_blueprint_v2 import parse_production_blueprint_document
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


@dataclass(frozen=True, slots=True)
class ProposedReferenceRole:
    reference_id: str
    registry_kind: ReferenceKind
    proposed_role: str

    def __post_init__(self) -> None:
        if not self.reference_id:
            raise ValueError("reference_id is required")
        if not isinstance(self.registry_kind, ReferenceKind):
            raise ValueError("registry_kind is invalid")
        if self.proposed_role not in {"CHARACTER", "SPACE", "UNRESOLVED"}:
            raise ValueError("proposed_role is invalid")

    def to_dict(self) -> dict[str, str]:
        return {
            "reference_id": self.reference_id,
            "registry_kind": self.registry_kind.value,
            "proposed_role": self.proposed_role,
        }


@dataclass(frozen=True, slots=True)
class SceneMigrationPreview:
    scene_id: str
    preserved_legacy_reference_ids: tuple[str, ...]
    proposed_reference_roles: tuple[ProposedReferenceRole, ...]
    unresolved_decisions: tuple[str, ...]
    target_scene_candidate_sha256: str

    def __post_init__(self) -> None:
        if not self.scene_id:
            raise ValueError("scene_id is required")
        if len(self.preserved_legacy_reference_ids) != len(set(self.preserved_legacy_reference_ids)):
            raise ValueError("legacy reference IDs must be unique")
        validate_sha256(self.target_scene_candidate_sha256, field_name="target_scene_candidate_sha256")

    @property
    def status(self) -> str:
        return "NEEDS_FRAME_BINDING_REVIEW"

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "status": self.status,
            "preserved_legacy_reference_ids": list(self.preserved_legacy_reference_ids),
            "proposed_reference_roles": [item.to_dict() for item in self.proposed_reference_roles],
            "unresolved_decisions": list(self.unresolved_decisions),
            "target_scene_candidate_sha256": self.target_scene_candidate_sha256,
        }


@dataclass(frozen=True, slots=True)
class BlueprintV2MigrationPreview:
    source_blueprint_id: str
    source_blueprint_sha256: str
    scenes: tuple[SceneMigrationPreview, ...]
    target_v2_candidate_sha256: str
    preview_sha256: str

    def __post_init__(self) -> None:
        validate_sha256(self.source_blueprint_sha256, field_name="source_blueprint_sha256")
        validate_sha256(self.target_v2_candidate_sha256, field_name="target_v2_candidate_sha256")
        validate_sha256(self.preview_sha256, field_name="preview_sha256")
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if expected != self.preview_sha256:
            raise ValueError("preview_sha256 does not match the migration preview")

    def to_dict(self) -> dict[str, object]:
        return {
            **self._body(),
            "preview_sha256": self.preview_sha256,
        }

    def _body(self) -> dict[str, object]:
        return _preview_body(
            self.source_blueprint_id,
            self.source_blueprint_sha256,
            self.scenes,
            self.target_v2_candidate_sha256,
        )


class BlueprintV1MigrationService:
    """Produces deterministic Evidence only; apply is intentionally absent."""

    def preview(self, source_document: Mapping[str, Any]) -> BlueprintV2MigrationPreview:
        source = parse_production_blueprint_document(source_document)
        if not isinstance(source, ProductionBlueprint):
            raise ValueError("migration preview requires an exact v1 blueprint")
        source_sha256 = source_document["blueprint_sha256"]
        kind_by_reference = {item.reference_id: item.kind for item in source.references}
        scene_previews: list[SceneMigrationPreview] = []
        for scene in source.scenes:
            proposed_roles = tuple(
                ProposedReferenceRole(reference_id, kind_by_reference[reference_id], _proposed_role(kind_by_reference[reference_id]))
                for reference_id in scene.reference_ids
            )
            unresolved = tuple(
                f"{scene.scene_id}:{frame}:{binding}"
                for frame in ("START", "END")
                for binding in ("CHARACTER_BINDINGS", "SPACE_BINDING", "COMPOSITION_BINDING")
            )
            scene_candidate = {
                "scene_id": scene.scene_id,
                "legacy_reference_ids": list(scene.reference_ids),
                "proposed_reference_roles": [item.to_dict() for item in proposed_roles],
                "unresolved_decisions": list(unresolved),
            }
            scene_previews.append(
                SceneMigrationPreview(
                    scene.scene_id,
                    scene.reference_ids,
                    proposed_roles,
                    unresolved,
                    sha256_bytes(canonical_json_bytes(scene_candidate)),
                )
            )
        target_candidate = {
            "blueprint_version": "2.0.0",
            "source_blueprint_id": source.blueprint_id,
            "source_blueprint_sha256": source_sha256,
            "scene_candidates": [item.to_dict() for item in scene_previews],
            "status": "UNRESOLVED_PREVIEW_ONLY",
        }
        target_sha256 = sha256_bytes(canonical_json_bytes(target_candidate))
        body = _preview_body(source.blueprint_id, source_sha256, tuple(scene_previews), target_sha256)
        preview_sha256 = sha256_bytes(canonical_json_bytes(body))
        return BlueprintV2MigrationPreview(
            source.blueprint_id,
            source_sha256,
            tuple(scene_previews),
            target_sha256,
            preview_sha256,
        )

    def assert_source_current(
        self,
        preview: BlueprintV2MigrationPreview,
        current_source_document: Mapping[str, Any],
    ) -> None:
        current = parse_production_blueprint_document(current_source_document)
        if not isinstance(current, ProductionBlueprint):
            raise ValueError("current migration source must remain an exact v1 blueprint")
        if current_source_document["blueprint_sha256"] != preview.source_blueprint_sha256:
            raise ValueError("migration preview is stale because the source checksum changed")


def _proposed_role(kind: ReferenceKind) -> str:
    if kind is ReferenceKind.PERSON:
        return "CHARACTER"
    if kind is ReferenceKind.SPACE:
        return "SPACE"
    return "UNRESOLVED"


def _preview_body(
    source_blueprint_id: str,
    source_blueprint_sha256: str,
    scenes: tuple[SceneMigrationPreview, ...],
    target_v2_candidate_sha256: str,
) -> dict[str, object]:
    return {
        "migration_preview_version": "1.0.0",
        "source_blueprint_version": "1.0.0",
        "source_blueprint_id": source_blueprint_id,
        "source_blueprint_sha256": source_blueprint_sha256,
        "target_blueprint_version": "2.0.0",
        "status": "NEEDS_FRAME_BINDING_REVIEW",
        "scenes": [item.to_dict() for item in scenes],
        "target_v2_candidate_sha256": target_v2_candidate_sha256,
        "authority": {
            "store_write_authorized": False,
            "human_go_granted": False,
            "provider_execution_authorized": False,
            "native_execution_authorized": False,
        },
    }
