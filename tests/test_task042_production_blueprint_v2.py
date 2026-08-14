from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.production_blueprint import (
    AssetSourceStrategy,
    CameraMotion,
    GenerationRisk,
    SceneAudioPlan,
)
from ai_video_production.production_blueprint_v2 import (
    AssetLockBinding,
    BlueprintSceneV2,
    CharacterLockBinding,
    CharacterRole,
    FrameIntent,
    FrameKind,
    FrameReferenceBinding,
    ProductionBlueprintV2,
    parse_production_blueprint_document,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.timebase import FrameRate


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def character(role: CharacterRole, suffix: str, checksum: str = SHA_A) -> CharacterLockBinding:
    return CharacterLockBinding(role, f"ASSET-{suffix}", checksum, f"SLOT-{suffix}", f"CAND-{suffix}")


def intent(kind: FrameKind, suffix: str) -> FrameIntent:
    return FrameIntent(
        kind,
        f"{kind.value} visual {suffix}",
        "Explain the product state",
        ("subject", "display"),
        ("extra furniture",),
        ("subject", "display", "background"),
        "eye-level locked camera",
        FrameReferenceBinding(
            (character(CharacterRole.PRIMARY, suffix),),
            AssetLockBinding(f"SPACE-{suffix}", SHA_B, f"SPACE-SLOT-{suffix}", f"SPACE-CAND-{suffix}"),
            AssetLockBinding(f"COMP-{suffix}", SHA_C, f"COMP-SLOT-{suffix}", f"COMP-CAND-{suffix}"),
        ),
        "medium wide",
    )


def blueprint(duration: int = 216_000) -> ProductionBlueprintV2:
    scene = BlueprintSceneV2(
        "SC01",
        0,
        duration,
        "Two-hour deterministic scene",
        AssetSourceStrategy.COMPOSITE,
        GenerationRisk.B_HEADLINE,
        CameraMotion.STATIC,
        intent(FrameKind.START, "START"),
        intent(FrameKind.END, "END"),
        SceneAudioPlan(narration=True, sound_effects=("transition",)),
        post_composite_text=True,
        final_hold_frames=30,
    )
    return ProductionBlueprintV2("BP-V6-DEMO", "V6 Demo", FrameRate(30, 1), duration, (scene,))


def test_v2_is_deterministic_closed_and_packaged_schema_is_identical() -> None:
    document = blueprint().to_dict()
    assert document == blueprint().to_dict()
    assert document["blueprint_version"] == "2.0.0"
    assert document["target_duration_frames"] == 216_000
    assert document["scenes"][0]["start_frame_intent"] != document["scenes"][0]["end_frame_intent"]
    canonical = Path(__file__).parents[1] / "schemas" / "production-blueprint-v2.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", canonical.name)
    assert canonical.read_bytes() == packaged.read_bytes()
    validate_instance(document, canonical)
    parsed = parse_production_blueprint_document(document)
    assert isinstance(parsed, ProductionBlueprintV2)
    assert parsed.to_dict() == document


def test_frame_binding_preserves_character_order_and_rejects_identity_collisions() -> None:
    first = character(CharacterRole.SUPPORTING, "A")
    second = character(CharacterRole.BACKGROUND, "B", SHA_B)
    binding = FrameReferenceBinding((first, second))
    assert [item["asset_id"] for item in binding.to_dict()["character_locks"]] == ["ASSET-A", "ASSET-B"]
    with pytest.raises(ValueError, match="one PRIMARY"):
        FrameReferenceBinding((character(CharacterRole.PRIMARY, "A"), character(CharacterRole.PRIMARY, "B", SHA_B)))
    with pytest.raises(ValueError, match="duplicate asset_id"):
        FrameReferenceBinding((first, CharacterLockBinding(CharacterRole.BACKGROUND, "ASSET-A", SHA_B, "SLOT-B", "CAND-B")))
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        FrameReferenceBinding((first,), AssetLockBinding("SPACE-A", SHA_B, "SPACE-SLOT", "CAND-A"))
    with pytest.raises(ValueError, match="CharacterRole"):
        CharacterLockBinding("PRIMARY", "ASSET-X", SHA_A, "SLOT-X", "CAND-X")  # type: ignore[arg-type]


def test_frame_intents_fail_closed_for_visibility_conflicts_and_wrong_scene_kind() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        FrameIntent(
            FrameKind.START, "visual", "axis", ("same",), ("same",), (), "static", FrameReferenceBinding()
        )
    with pytest.raises(ValueError, match="START frame_kind"):
        BlueprintSceneV2(
            "SC01", 0, 30, "bad", AssetSourceStrategy.REAL_CAPTURE,
            GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC,
            intent(FrameKind.END, "A"), intent(FrameKind.END, "B"),
        )


def test_parser_rejects_tampering_unknown_version_and_unknown_field() -> None:
    document = blueprint(300).to_dict()
    tampered = json.loads(json.dumps(document))
    tampered["title"] = "tampered"
    with pytest.raises(ValueError, match="does not match"):
        parse_production_blueprint_document(tampered)
    unknown = dict(document)
    unknown["blueprint_version"] = "2.1.0"
    with pytest.raises(ValueError, match="exactly 1.0.0 or 2.0.0"):
        parse_production_blueprint_document(unknown)
    extra = dict(document)
    extra["unexpected"] = True
    with pytest.raises(ValueError, match="Additional properties"):
        parse_production_blueprint_document(extra)
