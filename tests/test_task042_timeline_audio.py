from pathlib import Path
from importlib import resources
import json

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.production_control import AssetCandidate, CandidateLifecycle, ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.serialization import sha256_bytes
from ai_video_production.timebase import FrameRate
from ai_video_production.timeline_audio import (AudioFitPolicy, AudioRange, AudioSourceBinding,
    AudioSourceIntent, ImportedSrtCue, MusicPlan, SrtProposalService, SrtProposalState,
    TimelineAudioPlan, TimelineAudioRole)
from ai_video_production.timeline_audio_application import Task042TimelineAudioApplication
from ai_video_production.timeline_audio_store import TimelineAudioHistory, TimelineAudioSnapshotStore
from ai_video_production.audio_workspace import AudioWorkspaceRegistry, PlacementDecision, PlacementReview
from ai_video_production.audio_workspace_placement_binding import AudioWorkspacePlacementBinding

SHA = "sha256:" + "1" * 64
ASSET_SHA = "sha256:" + "2" * 64
CREATED = "2026-08-15T00:00:00.000Z"


def source(slot: str = "slot-bgm") -> AudioSourceBinding:
    return AudioSourceBinding(slot, AudioSourceIntent.EXISTING_ASSET, "candidate-1", "asset-1", ASSET_SHA, 300)


def plan(*items, revision: int = 1, previous: str | None = None) -> TimelineAudioPlan:
    return TimelineAudioPlan("project-1", "timeline-1", revision, "blueprint-1", SHA,
                             FrameRate(30), 300, tuple(items), previous)


def music(**overrides) -> MusicPlan:
    values = dict(item_id="music-1", lane_id="bgm-1", start_frame=0, end_frame=300,
                  source=source(), whole_timeline=True)
    values.update(overrides)
    return MusicPlan(**values)


def locked_production() -> ProductionControlRegistry:
    value = ProductionControlRegistry()
    value.add_slot(SceneAssetSlot("slot-bgm", "project-1", "scene-1", SlotKind.BGM, True))
    value.add_candidate(AssetCandidate("candidate-1", "slot-bgm", "asset-1", ASSET_SHA, 1))
    value.transition_candidate("candidate-1", CandidateLifecycle.READY_FOR_AUDIT)
    value.transition_candidate("candidate-1", CandidateLifecycle.ACCEPTED)
    value.lock_candidate(slot_id="slot-bgm", candidate_id="candidate-1", expected_revision=value.slots["slot-bgm"].revision)
    return value


def setup_project(root: Path) -> ProductProjectManifest:
    blueprint = b'{"blueprint":true}'
    child = root / "state/blueprint.json"
    child.parent.mkdir(); child.write_bytes(blueprint)
    binding = ProjectChildBinding("TASK-042", "state/blueprint.json", "bai.test-blueprint", "1.0.0", SHA, True)
    # The fixture intentionally binds the declared Blueprint proof. The child
    # bytes are patched to that proof only at the manifest boundary below.
    binding = ProjectChildBinding("TASK-042", "state/blueprint.json", "bai.test-blueprint", "1.0.0", sha256_bytes(blueprint), True)
    manifest = ProductProjectManifest.create(project_id="project-1", project_revision=1, product_version="0.20.1",
        timebase=ProjectTimebase(30, 1), child_bindings=(binding,), created_at=CREATED, updated_at=CREATED)
    ProductProjectManifestStore.save(root, manifest)
    return manifest


def test_frame_plan_is_canonical_and_whole_timeline_is_exact() -> None:
    value = plan(music())
    assert value.to_dict()["timeline_frames_authoritative"] is True
    assert value.placement_binding("music-1").plan_sha256 == value.plan_sha256
    with pytest.raises(ValueError, match="whole-timeline"):
        plan(music(end_frame=299))


def test_same_lane_overlap_is_rejected_and_bgm_transition_is_explicit() -> None:
    first = music(end_frame=180, whole_timeline=False, transition_group_id="crossfade-1")
    second = music(item_id="music-2", start_frame=150, source=source(), whole_timeline=False, transition_group_id="crossfade-1")
    assert len(plan(first, second).items) == 2
    with pytest.raises(ValueError, match="overlap"):
        plan(first, MusicPlan("music-2", "bgm-1", 150, 300, source()))


def test_srt_is_proposal_only_and_detects_global_narration_overlap() -> None:
    cues = (ImportedSrtCue(1, 0, 1000, "bai-text://cue/1", SHA, "scene-1"),
            ImportedSrtCue(2, 900, 1500, "bai-text://cue/2", SHA, "scene-2"))
    result = SrtProposalService.import_cues(cues, source_srt_sha256=SHA, blueprint_sha256=SHA,
        timeline_rate=FrameRate(30), target_duration_frames=100,
        scene_ranges={"scene-1": (0, 50), "scene-2": (0, 100)})
    assert result.state is SrtProposalState.CONFLICT
    assert "NARRATION_OVERLAP" in result.cues[1].conflict_codes
    assert result.to_dict()["scene_timing_mutation_authorized"] is False


def test_history_round_trip_rejects_forks() -> None:
    history = TimelineAudioHistory("project-1"); first = plan(music()); history.add_plan(first)
    loaded = TimelineAudioSnapshotStore.parse_bytes(TimelineAudioSnapshotStore.serialize(history), expected_project_id="project-1")
    assert loaded.current_plan == first
    with pytest.raises(ProductError, match="append"):
        loaded.add_plan(plan(music(), revision=2, previous=SHA))


def test_application_commits_timeline_as_product_project_child(tmp_path: Path) -> None:
    initial = setup_project(tmp_path)
    blueprint_hash = initial.child_bindings[0].content_sha256
    value = TimelineAudioPlan("project-1", "timeline-1", 1, "blueprint-1", blueprint_hash,
        FrameRate(30), 300, (music(),))
    app = Task042TimelineAudioApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm-1")
    prepared = app.prepare_plan(plan=value, production=locked_production(), expected_project_manifest_sha256=initial.project_manifest_sha256)
    result = app.apply_plan(confirmation_id=prepared["confirmation_id"])
    assert result["timeline_snapshot"]["current_revision"] == 1
    manifest = ProductProjectManifestStore.load(tmp_path)
    assert manifest.project_revision == 2
    assert any(binding.relative_path == "state/timeline-audio.json" for binding in manifest.child_bindings)


def test_application_rejects_slot_role_and_stale_project(tmp_path: Path) -> None:
    initial = setup_project(tmp_path); blueprint_hash = initial.child_bindings[0].content_sha256
    ambience = AudioRange("amb-1", "amb-1", TimelineAudioRole.AMBIENCE, 0, 300,
                          AudioSourceBinding("slot-bgm", AudioSourceIntent.EXISTING_ASSET, "candidate-1", "asset-1", ASSET_SHA, 300))
    value = TimelineAudioPlan("project-1", "timeline-1", 1, "blueprint-1", blueprint_hash, FrameRate(30), 300, (ambience,))
    app = Task042TimelineAudioApplication(project_root=tmp_path, project_id="project-1")
    with pytest.raises(ProductError, match="role"):
        app.prepare_plan(plan=value, production=locked_production(), expected_project_manifest_sha256=initial.project_manifest_sha256)
    with pytest.raises(ProductError, match="changed"):
        app.prepare_plan(plan=plan(music()), production=locked_production(), expected_project_manifest_sha256=SHA)


def test_stretch_is_preserved_as_visible_execution_gap(tmp_path: Path) -> None:
    initial = setup_project(tmp_path); blueprint_hash = initial.child_bindings[0].content_sha256
    stretched = music(fit_policy=AudioFitPolicy.STRETCH)
    value = TimelineAudioPlan("project-1", "timeline-1", 1, "blueprint-1", blueprint_hash, FrameRate(30), 300, (stretched,))
    app = Task042TimelineAudioApplication(project_root=tmp_path, project_id="project-1", token_factory=lambda: "confirm-gap")
    prepared = app.prepare_plan(plan=value, production=locked_production(), expected_project_manifest_sha256=initial.project_manifest_sha256)
    assert prepared["execution_gaps"] == [{"item_id": "music-1", "code": "TASK026_STRETCH_NOT_SUPPORTED"}]


def test_schema_is_valid_and_packaged_copy_is_equivalent() -> None:
    public = Path(__file__).parents[1] / "schemas/timeline-audio.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    public_document = json.loads(public.read_text(encoding="utf-8"))
    assert public_document == json.loads(packaged.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(public_document)


def test_current_timeline_proof_compiles_to_task026_and_stale_proof_fails() -> None:
    production = locked_production(); value = plan(music()); history = TimelineAudioHistory("project-1"); history.add_plan(value)
    workspace = AudioWorkspaceRegistry()
    workspace.add_placement(PlacementReview("review-1", "candidate-1", 0, 300, "BGM",
        PlacementDecision.ACCEPT, timeline_binding=value.placement_binding("music-1")))
    compiled = AudioWorkspacePlacementBinding.compile_current_timeline_placement(
        review_id="review-1", workspace=workspace, production=production, timeline=history, track_index=1)
    assert compiled.asset_id == "asset-1"
    assert compiled.task010_compatible is True

    second = plan(music(gain_db=-3), revision=2, previous=value.plan_sha256); history.add_plan(second)
    with pytest.raises(ProductError, match="current revision"):
        AudioWorkspacePlacementBinding.compile_current_timeline_placement(
            review_id="review-1", workspace=workspace, production=production, timeline=history, track_index=1)
