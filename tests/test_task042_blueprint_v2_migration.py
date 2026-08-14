import copy
from dataclasses import replace

import pytest

from ai_video_production.blueprint_v2_migration import BlueprintV1MigrationService
from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    BlueprintReference,
    BlueprintScene,
    CameraMotion,
    GenerationRisk,
    ProductionBlueprint,
    ReferenceKind,
    ReferenceStatus,
)
from ai_video_production.production_blueprint_v2 import parse_production_blueprint_document
from ai_video_production.timebase import FrameRate


def v1_document(title: str = "Legacy") -> dict[str, object]:
    references = (
        BlueprintReference("PERSON-A", ReferenceKind.PERSON, ReferenceStatus.LOCKED, "person.png"),
        BlueprintReference("SPACE-A", ReferenceKind.SPACE, ReferenceStatus.LOCKED, "space.png"),
        BlueprintReference("PROMPT-A", ReferenceKind.PROMPT, ReferenceStatus.AVAILABLE),
    )
    scene = BlueprintScene(
        "SC01", 0, 300, "Legacy scene", AssetSourceStrategy.REUSE_EXISTING,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC,
        ("PERSON-A", "SPACE-A", "PROMPT-A"),
    )
    return ProductionBlueprint("BP-LEGACY-01", title, FrameRate(30, 1), 300, references, (scene,)).to_dict()


def test_preview_is_deterministic_unresolved_and_never_grants_authority() -> None:
    service = BlueprintV1MigrationService()
    first = service.preview(v1_document())
    second = service.preview(v1_document())
    assert first == second
    result = first.to_dict()
    assert result["status"] == "NEEDS_FRAME_BINDING_REVIEW"
    assert all(value is False for value in result["authority"].values())
    scene = result["scenes"][0]
    assert scene["preserved_legacy_reference_ids"] == ["PERSON-A", "SPACE-A", "PROMPT-A"]
    assert [item["proposed_role"] for item in scene["proposed_reference_roles"]] == [
        "CHARACTER", "SPACE", "UNRESOLVED"
    ]
    assert scene["unresolved_decisions"] == [
        "SC01:START:CHARACTER_BINDINGS", "SC01:START:SPACE_BINDING", "SC01:START:COMPOSITION_BINDING",
        "SC01:END:CHARACTER_BINDINGS", "SC01:END:SPACE_BINDING", "SC01:END:COMPOSITION_BINDING",
    ]
    assert not hasattr(service, "apply")


def test_preview_verifies_v1_checksum_and_detects_stale_source() -> None:
    service = BlueprintV1MigrationService()
    source = v1_document()
    preview = service.preview(source)
    service.assert_source_current(preview, source)
    changed = v1_document("Changed")
    with pytest.raises(ValueError, match="stale"):
        service.assert_source_current(preview, changed)
    tampered = copy.deepcopy(source)
    tampered["title"] = "Tampered without checksum"
    with pytest.raises(ValueError, match="does not match"):
        service.preview(tampered)
    with pytest.raises(ValueError, match="preview_sha256 does not match"):
        replace(preview, preview_sha256="sha256:" + "f" * 64)


def test_public_parser_keeps_exact_v1_read_compatibility() -> None:
    source = v1_document()
    parsed = parse_production_blueprint_document(source)
    assert isinstance(parsed, ProductionBlueprint)
    assert parsed.to_dict() == source


def test_preview_refuses_v2_input() -> None:
    source = v1_document()
    source["blueprint_version"] = "2.0.0"
    with pytest.raises(ValueError):
        BlueprintV1MigrationService().preview(source)
