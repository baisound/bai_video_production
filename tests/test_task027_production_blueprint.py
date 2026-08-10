from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.production_blueprint import (
    AssetSourceStrategy, BlueprintReference, BlueprintScene, CameraMotion,
    GenerationRisk, ProductionBlueprint, ReferenceKind, ReferenceStatus,
    SceneAudioPlan,
)
from ai_video_production.timebase import FrameRate
from ai_video_production.schema_contracts import validate_instance


def references():
    return (
        BlueprintReference("PERSON-A", ReferenceKind.PERSON, ReferenceStatus.LOCKED, "PERSON-A.png"),
        BlueprintReference("SPACE-A_CONCEPT", ReferenceKind.SPACE, ReferenceStatus.AVAILABLE, "SPACE-A_CONCEPT.png"),
        BlueprintReference("SPACE-F_CLIENT", ReferenceKind.SPACE, ReferenceStatus.PLANNED),
    )


def scenes():
    return (
        BlueprintScene(
            "SC01", 0, 150, "Brand opening", AssetSourceStrategy.REUSE_EXISTING,
            GenerationRisk.A_LOW_TEXT, CameraMotion.SUBTLE,
            ("PERSON-A", "SPACE-A_CONCEPT"),
            SceneAudioPlan(sound_effects=("click", "chime"), sound_logo=True),
            final_hold_frames=30,
        ),
        BlueprintScene(
            "SC02", 150, 300, "Dense product UI", AssetSourceStrategy.COMPOSITE,
            GenerationRisk.C_DENSE_UI, CameraMotion.STATIC,
            ("SPACE-A_CONCEPT",), locked_reference=True, post_composite_text=True,
        ),
    )


def test_blueprint_is_deterministic_and_records_real_first_priority() -> None:
    blueprint = ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, references(), scenes())
    document = blueprint.to_dict()
    assert document["asset_source_priority"] == [
        "REAL_CAPTURE", "REUSE_EXISTING", "COMPOSITE", "AI_GENERATED"
    ]
    assert document == blueprint.to_dict()
    assert document["scenes"][1]["post_composite_text"] is True
    canonical = Path(__file__).parents[1] / "schemas" / "production-blueprint.schema.json"
    validate_instance(document, canonical)
    packaged = resources.files("ai_video_production").joinpath("schema_resources", canonical.name)
    assert json.loads(canonical.read_text(encoding="utf-8")) == json.loads(packaged.read_text(encoding="utf-8"))


def test_dense_ui_fails_closed_without_locked_static_post_composite_design() -> None:
    with pytest.raises(ValueError, match="locked reference and static"):
        BlueprintScene(
            "SC01", 0, 30, "UI", AssetSourceStrategy.AI_GENERATED,
            GenerationRisk.C_DENSE_UI, CameraMotion.DYNAMIC, (), post_composite_text=True,
        )
    with pytest.raises(ValueError, match="composed after"):
        BlueprintScene(
            "SC01", 0, 30, "UI", AssetSourceStrategy.COMPOSITE,
            GenerationRisk.C_DENSE_UI, CameraMotion.STATIC, (), locked_reference=True,
        )


def test_scene_ledger_rejects_gaps_unknown_references_and_wrong_target() -> None:
    broken = BlueprintScene(
        "SC01", 1, 30, "Gap", AssetSourceStrategy.REAL_CAPTURE,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("UNKNOWN-ID",),
    )
    with pytest.raises(ValueError, match="without gaps"):
        ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 30, references(), (broken,))
    first = scenes()[0]
    unknown = BlueprintScene(
        "SC02", 150, 300, "Unknown", AssetSourceStrategy.REAL_CAPTURE,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, ("UNKNOWN-ID",),
    )
    with pytest.raises(ValueError, match="undeclared"):
        ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 300, references(), (first, unknown))
    with pytest.raises(ValueError, match="target_duration"):
        ProductionBlueprint("BP-DEMO-001", "Demo", FrameRate(30, 1), 301, references(), scenes())


def test_planned_reference_cannot_claim_existing_file() -> None:
    with pytest.raises(ValueError, match="planned references"):
        BlueprintReference("SPACE-F_CLIENT", ReferenceKind.SPACE, ReferenceStatus.PLANNED, "not-created.png")
