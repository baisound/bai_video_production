from __future__ import annotations

from dataclasses import replace
import json

import pytest

from ai_video_production.prompt_registry import PromptCompilationBinding, PromptEntity, PromptGenerationRegistry
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.production_control import ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.production_control_store import ProductionControlSnapshotStore

from ai_video_production.visual_prompt_compilation import (
    ManualEnglishOverrideState,
    PromptCompilationService,
    ProofreadingState,
    VisualPromptCompilationRequest,
)


H = lambda ch: "sha256:" + ch * 64


def request() -> VisualPromptCompilationRequest:
    return VisualPromptCompilationRequest(
        project_id="project-1", scene_id="scene-1", slot_id="slot-image",
        blueprint_world_lock_sha256=H("a"), provider_profile_id="profile-1",
        provider_profile_version="v1", provider_profile_sha256=H("b"),
        selected_route_id="route-1", required_capabilities=("image.generate",),
        input_asset_hashes=(H("c"),), source_ja_ref="project-private://prompt/source-ja",
        source_ja="秘密の日本語原文", normalized_ja_ref="project-private://prompt/normalized-ja",
        normalized_ja="正規化した秘密の日本語", runtime_en_ref="project-private://prompt/runtime-en",
        runtime_en="private runtime English prompt", proofreading_state=ProofreadingState.AI_PROOFREAD,
        manual_english_override_state=ManualEnglishOverrideState.NONE,
        world=("same world",), before=("door closed",), now=("door opens",),
        trace=("dust trace",), physics=("real gravity",), place=("studio",),
        owner_constraints=("no logo change",), subject=("main subject",),
        space=("wide room",), off_screen=("crew absent",), camera=("eye level",),
        light=("soft key",), frame=("16:9",), after=("door open",),
        narration_intent="quiet narration", music_direction="minimal music",
        se_intent="door sound", ambience_intent="room tone", generate_bgm=True,
        generate_se=True, generate_ambience=False,
        negative_prompt_ref="project-private://prompt/negative", negative_prompt="private negative body",
    )


def test_compilation_is_deterministic_and_public_manifest_contains_no_bodies() -> None:
    first = PromptCompilationService.compile(request())
    second = PromptCompilationService.compile(request())
    assert first.to_manifest() == second.to_manifest()
    public = json.dumps(first.to_manifest(), ensure_ascii=False)
    for secret in (first.source_ja, first.normalized_ja, first.runtime_en, first.negative_prompt):
        assert secret not in public
    assert first.to_manifest()["prompt_bodies_embedded"] is False
    assert first.to_manifest()["provider_execution_started"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("runtime_en", "changed private English"),
        ("narration_intent", "changed narration"),
        ("generate_bgm", False),
        ("blueprint_world_lock_sha256", H("d")),
        ("input_asset_hashes", (H("e"),)),
        ("required_capabilities", ("image.edit",)),
    ],
)
def test_each_compiler_input_changes_immutable_identity(field: str, value: object) -> None:
    baseline = PromptCompilationService.compile(request()).to_manifest()["compilation_sha256"]
    changed = PromptCompilationService.compile(replace(request(), **{field: value})).to_manifest()
    assert changed["compilation_sha256"] != baseline


def test_capabilities_must_be_unique_and_sorted() -> None:
    with pytest.raises(ValueError):
        replace(request(), required_capabilities=("video.generate", "image.generate"))
    with pytest.raises(ValueError):
        replace(request(), required_capabilities=("image.generate", "image.generate"))


def test_negative_prompt_ref_and_body_are_atomic() -> None:
    with pytest.raises(ValueError):
        replace(request(), negative_prompt=None)


def test_compiled_prompt_binding_round_trips_without_changing_legacy_shape(tmp_path) -> None:
    compilation = PromptCompilationService.compile(request()).to_manifest()
    binding = PromptCompilationBinding.from_manifest(
        manifest_ref="project-private://prompt/compilation.json",
        manifest=compilation,
    )
    compiled = PromptEntity(
        "prompt-compiled", 1, "image", compilation["runtime_en_sha256"],
        "profile-1", "v1", ("keep identity",), scene_id="scene-1",
        slot_id="slot-image", body_ref="project-private://prompt/runtime-en",
        input_asset_hashes=(H("c"),), compilation_binding=binding,
    )
    registry = PromptGenerationRegistry(); registry.add_prompt(compiled)
    path = tmp_path / "prompt.json"
    PromptRegistrySnapshotStore.save(path, registry)
    loaded = PromptRegistrySnapshotStore.load(path).prompts[("prompt-compiled", 1)]
    assert loaded == compiled
    assert loaded.to_dict()["compilation_binding"]["prompt_bodies_embedded"] is False

    legacy = PromptEntity(
        "prompt-legacy", 1, "legacy", H("d"), "profile-1", "v1", ("keep",),
    ).to_dict()
    assert "compilation_binding" not in legacy


def test_compiled_prompt_rejects_runtime_or_input_identity_drift() -> None:
    manifest = PromptCompilationService.compile(request()).to_manifest()
    binding = PromptCompilationBinding.from_manifest(
        manifest_ref="project-private://prompt/compilation.json", manifest=manifest,
    )
    with pytest.raises(ValueError):
        PromptEntity(
            "prompt-compiled", 1, "image", H("f"), "profile-1", "v1", ("keep",),
            scene_id="scene-1", slot_id="slot-image", body_ref="project-private://prompt/runtime-en",
            input_asset_hashes=(H("c"),), compilation_binding=binding,
        )


def test_compilation_binding_rejects_tampered_manifest_even_when_shape_is_valid() -> None:
    manifest = PromptCompilationService.compile(request()).to_manifest()
    manifest["generate_bgm"] = False
    with pytest.raises(ValueError):
        PromptCompilationBinding.from_manifest(
            manifest_ref="project-private://prompt/compilation.json", manifest=manifest,
        )


def test_compiled_prompt_uses_existing_task040_prepare_apply_and_restart(tmp_path) -> None:
    production = ProductionControlRegistry()
    production.add_slot(SceneAssetSlot("slot-image", "project-1", "scene-1", SlotKind.START_FRAME, False))
    ProductionControlSnapshotStore.save(tmp_path / "production-control.json", production)
    compiled = PromptCompilationService.compile(request()).to_manifest()
    binding = PromptCompilationBinding.from_manifest(
        manifest_ref="project-private://prompt/compilation.json", manifest=compiled,
    )
    app = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm",
    )
    state = app.snapshot()
    prepared = app.prepare_prompt(
        prompt_id="prompt-compiled", prompt_version=1, purpose="quick image",
        scene_id="scene-1", slot_id="slot-image", body_ref=compiled["runtime_en_ref"],
        body_sha256=compiled["runtime_en_sha256"], provider_profile_id="profile-1",
        provider_profile_version="v1", input_asset_hashes=(H("c"),),
        keep_conditions=("keep identity",),
        expected_prompt_snapshot_sha256=state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=state["production_snapshot_sha256"],
        compilation_binding=binding,
    )
    saved = app.apply_prompt(confirmation_id=prepared["confirmation_id"])
    assert saved["prompts"][0]["compilation_binding"]["compilation_sha256"] == compiled["compilation_sha256"]
    reopened = Task040PromptEvidenceApplication(project_root=tmp_path, project_id="project-1").snapshot()
    assert reopened["prompts"][0]["compilation_binding"] == saved["prompts"][0]["compilation_binding"]
