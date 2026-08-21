from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from importlib import resources
import json
from pathlib import Path
import struct
import zlib

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile,
    AiWorkload,
    ConnectionAvailability,
    CostClass,
    ModelRoute,
    ProviderFamily,
    SelectionMode,
)
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.creative_generation_execution_application import (
    LocalGenerationExecutionResult,
    LocalGenerationRuntimeReadiness,
    Task013CreativeGenerationExecutionApplication,
)
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.generation_output_adoption_application import (
    AdoptedAssetIdentity,
    Task027GeneratedOutputAssetPort,
    Task027GenerationOutputAdoptionApplication,
)
from ai_video_production.serialization import sha256_bytes
from ai_video_production.ingest import AssetIngestService
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.paths import LogicalPathResolver, PathMapping, SourcePathPolicy
from ai_video_production.production_control import AssetCandidate, ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.profile import ProfileSnapshot
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import ProductProjectSaveCoordinator
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.prompt_registry import (
    GenerationAttempt,
    GenerationResult,
    PromptEntity,
    PromptGenerationRegistry,
    PromptRegenerationBinding,
    RegenerationStrategy,
)
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.store import SQLiteProductStore
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.desktop_shell import ShellApplicationService


SHA_1 = "sha256:" + "1" * 64
SHA_2 = "sha256:" + "2" * 64
SHA_3 = "sha256:" + "3" * 64
SHA_4 = "sha256:" + "4" * 64


class ExecutionStub:
    def __init__(self) -> None:
        self.event = {
            "project_id": "project-1",
            "execution_id": "execution-1",
            "queue_entry_id": "QUEUE-123",
            "slot_id": "slot-video",
            "prompt_id": "prompt-1",
            "prompt_version": 1,
            "prompt_sha256": SHA_1,
            "provider_id": "comfy",
            "model_id": "minimax-h3",
            "provider_operation_id": "operation-1",
            "state": "COMPLETED",
            "output_ref": "project-output://generated/result.mp4",
            "output_sha256": SHA_2,
            "media_kind": "VIDEO",
            "latency_ms": 125,
        }
        self.sha = SHA_3

    def snapshot(self):
        return {
            "execution_snapshot_sha256": self.sha,
            "latest_executions": [dict(self.event)],
            "recovery": {"required": False},
        }


class QueueStub:
    def __init__(self) -> None:
        self.sha = SHA_4
        self.entry = {
            "queue_entry_id": "QUEUE-123",
            "slot_id": "slot-video",
            "prompt_id": "prompt-1",
            "prompt_version": 1,
            "prompt_sha256": SHA_1,
        }

    def snapshot(self):
        return {"queue_snapshot_sha256": self.sha, "entries": [dict(self.entry)]}


class ProductionStub:
    def __init__(self) -> None:
        self.sha = "sha256:" + "5" * 64
        self.candidate = None

    def snapshot(self):
        candidates = [] if self.candidate is None else [dict(self.candidate)]
        return {
            "snapshot_sha256": self.sha,
            "slots": [{"slot_id": "slot-video", "candidates": candidates}],
        }

    def register_candidate(self, **values):
        assert values["expected_snapshot_sha256"] == self.sha
        self.candidate = {
            "candidate_id": values["candidate_id"],
            "slot_id": values["slot_id"],
            "asset_id": values["asset_id"],
            "asset_sha256": values["asset_sha256"],
            "candidate_version": 1,
            "lifecycle_state": "CREATED",
            "generation_job_id": values["generation_job_id"],
            "parent_candidate_id": values["parent_candidate_id"],
            "supersedes": values["supersedes"],
        }
        self.sha = "sha256:" + "6" * 64
        return {"candidate": dict(self.candidate), "workspace": self.snapshot()}

    def mark_ready_for_audit(self, **values):
        assert values["candidate_id"] == self.candidate["candidate_id"]
        assert values["expected_snapshot_sha256"] == self.sha
        self.candidate["lifecycle_state"] = "READY_FOR_AUDIT"
        self.sha = "sha256:" + "7" * 64
        return {"candidate": dict(self.candidate), "workspace": self.snapshot()}


class PromptStub:
    def __init__(self, production: ProductionStub) -> None:
        self.production = production
        self.sha = "sha256:" + "8" * 64
        self.attempt = None
        self.pending = None
        self.recovery = {"required": False, "available_actions": []}
        self.prompt_version = 1
        self.regeneration_binding = None

    def snapshot(self):
        attempts = [] if self.attempt is None else [dict(self.attempt)]
        return {
            "prompt_snapshot_sha256": self.sha,
            "production_snapshot_sha256": self.production.sha,
            "recovery": dict(self.recovery),
            "prompts": [{
                "prompt_id": "prompt-1", "prompt_version": self.prompt_version,
                "regeneration_binding": self.regeneration_binding, "attempts": attempts,
            }],
        }

    def prepare_attempt(self, **values):
        assert values["expected_prompt_snapshot_sha256"] == self.sha
        assert values["expected_production_snapshot_sha256"] == self.production.sha
        self.pending = values
        return {"confirmation_id": "prompt-confirm"}

    def apply_attempt(self, *, confirmation_id):
        assert confirmation_id == "prompt-confirm"
        values = self.pending
        self.attempt = {
            "generation_job_id": values["generation_job_id"],
            "slot_id": values["slot_id"],
            "prompt_id": values["prompt_id"],
            "prompt_version": values["prompt_version"],
            "prompt_sha256": SHA_1,
            "provider_id": values["provider_id"],
            "model_id": values["model_id"],
            "strategy_level": values["strategy_level"],
            "result": values["result"],
            "failure_codes": list(values["failure_codes"]),
            "output_candidate_id": values["output_candidate_id"],
            "parent_attempt_id": values["parent_attempt_id"],
            "cost": values["cost"],
            "latency_ms": values["latency_ms"],
        }
        self.sha = "sha256:" + "9" * 64
        return self.snapshot()

    def apply_recovery(self, *, action):
        assert action in {"COMPLETE", "FINALIZE"}
        self.recovery = {"required": False, "available_actions": []}
        return self.snapshot()


class AssetPortStub:
    def __init__(self, failure: ProductError | None = None) -> None:
        self.calls = 0
        self.verify_calls = 0
        self.failure = failure

    def adopt(self, event):
        self.calls += 1
        if self.failure:
            raise self.failure
        return AdoptedAssetIdentity("ASSET-01K00000000000000000000000", event["output_sha256"])

    def verify(self, event, asset_id):
        self.verify_calls += 1
        return AdoptedAssetIdentity(asset_id, event["output_sha256"])


def fixture(root: Path, *, asset_port=None):
    execution = ExecutionStub()
    queue = QueueStub()
    production = ProductionStub()
    prompt = PromptStub(production)
    port = asset_port or AssetPortStub()
    app = Task027GenerationOutputAdoptionApplication(
        project_root=root,
        project_id="project-1",
        generation_execution=execution,
        generation_queue=queue,
        production_control=production,
        prompt_evidence=prompt,
        asset_port=port,
        token_factory=lambda: "adoption-confirm",
    )
    return app, execution, queue, production, prompt, port


def prepare(app, execution, queue, production, prompt):
    state = app.snapshot()
    production_sha = production.sha if hasattr(production, "sha") else production.snapshot()["snapshot_sha256"]
    prompt_sha = prompt.sha if hasattr(prompt, "sha") else prompt.snapshot()["prompt_snapshot_sha256"]
    return app.prepare_adoption(
        execution_id="execution-1",
        expected_execution_snapshot_sha256=execution.sha,
        expected_queue_snapshot_sha256=queue.sha,
        expected_production_snapshot_sha256=production_sha,
        expected_prompt_snapshot_sha256=prompt_sha,
        expected_adoption_snapshot_sha256=state["adoption_snapshot_sha256"],
    )


def test_manifest_drift_after_confirmation_blocks_asset_adoption(tmp_path: Path):
    app, execution, queue, production, prompt, port = fixture(tmp_path)
    initial = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.22.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
    )
    ProductProjectManifestStore.save(tmp_path, initial)
    state = app.snapshot()
    prepared = app.prepare_adoption(
        execution_id="execution-1",
        expected_execution_snapshot_sha256=execution.sha,
        expected_queue_snapshot_sha256=queue.sha,
        expected_production_snapshot_sha256=production.sha,
        expected_prompt_snapshot_sha256=prompt.sha,
        expected_adoption_snapshot_sha256=state["adoption_snapshot_sha256"],
        expected_project_manifest_sha256=initial.project_manifest_sha256,
    )
    changed = ProductProjectManifest.create(
        project_id="project-1", project_revision=2, product_version="0.22.0",
        timebase=initial.timebase, child_bindings=(), created_at=initial.created_at,
        updated_at=initial.updated_at,
    )
    ProductProjectManifestStore.save(
        tmp_path, changed,
        expected_previous_manifest_sha256=initial.project_manifest_sha256,
    )
    with pytest.raises(ProductError) as blocked:
        app.apply_adoption(confirmation_id=prepared["confirmation_id"])
    assert blocked.value.code == "ERR_OUTPUT_ADOPTION_MANIFEST_CONFLICT"
    assert port.calls == 0
    assert app.snapshot()["records"] == []


def test_project_recovery_gate_blocks_adoption_before_asset(tmp_path: Path, monkeypatch):
    app, execution, queue, production, prompt, port = fixture(tmp_path)
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.22.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
    )
    ProductProjectManifestStore.save(tmp_path, manifest)
    state = app.snapshot()
    prepared = app.prepare_adoption(
        execution_id="execution-1",
        expected_execution_snapshot_sha256=execution.sha,
        expected_queue_snapshot_sha256=queue.sha,
        expected_production_snapshot_sha256=production.sha,
        expected_prompt_snapshot_sha256=prompt.sha,
        expected_adoption_snapshot_sha256=state["adoption_snapshot_sha256"],
        expected_project_manifest_sha256=manifest.project_manifest_sha256,
    )

    def blocked(_self, _root, _manifest):
        raise ProductError("ERR_PROJECT_SAVE_RECOVERY_REQUIRED", "blocked", ProductErrorCategory.HUMAN_REVIEW_REQUIRED)

    monkeypatch.setattr(ProductProjectSaveCoordinator, "require_current_integrity", blocked)
    with pytest.raises(ProductError) as rejected:
        app.apply_adoption(confirmation_id=prepared["confirmation_id"])
    assert rejected.value.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED"
    assert port.calls == 0
    assert app.snapshot()["records"] == []


def test_completed_output_becomes_ready_for_human_audit_without_wider_authority(tmp_path: Path):
    app, execution, queue, production, prompt, port = fixture(tmp_path)
    confirmation = prepare(app, execution, queue, production, prompt)
    assert confirmation["action_label"] == "検証して監査候補へ登録"
    assert confirmation["provider_execution_replayed"] is False
    result = app.apply_adoption(confirmation_id="adoption-confirm")

    assert port.calls == 1
    assert port.verify_calls == 0
    assert [item["state"] for item in result["records"]] == [
        "PREPARED", "ASSET_REGISTERED", "CANDIDATE_REGISTERED",
        "ATTEMPT_BOUND", "READY_FOR_AUDIT",
    ]
    assert production.candidate["lifecycle_state"] == "READY_FOR_AUDIT"
    assert prompt.attempt["result"] == "PASS"
    assert result["provider_execution_started"] is False
    assert result["paid_execution_authorized"] is False
    assert result["human_audit_decision_created"] is False
    assert result["candidate_accepted"] is False
    assert result["candidate_locked"] is False
    assert result["publication_authorized"] is False
    assert result["nle_mutation_started"] is False
    assert result["eligible_completed_outputs"] == []


def test_confirmation_is_one_shot_and_snapshot_bound(tmp_path: Path):
    app, execution, queue, production, prompt, _port = fixture(tmp_path)
    prepare(app, execution, queue, production, prompt)
    queue.sha = "sha256:" + "a" * 64
    with pytest.raises(ProductError) as stale:
        app.apply_adoption(confirmation_id="adoption-confirm")
    assert stale.value.code == "ERR_OUTPUT_ADOPTION_QUEUE_CONFLICT"
    with pytest.raises(ProductError) as reused:
        app.apply_adoption(confirmation_id="adoption-confirm")
    assert reused.value.code == "ERR_OUTPUT_ADOPTION_CONFIRMATION_INVALID"
    assert not app.snapshot_path.exists()


def test_known_asset_validation_failure_is_terminal_without_candidate(tmp_path: Path):
    failure = ProductError(
        "ERR_OUTPUT_ADOPTION_CHECKSUM_MISMATCH",
        "mismatch",
        ProductErrorCategory.DATA_INTEGRITY,
    )
    app, execution, queue, production, prompt, _port = fixture(tmp_path, asset_port=AssetPortStub(failure))
    prepare(app, execution, queue, production, prompt)
    with pytest.raises(ProductError) as exc:
        app.apply_adoption(confirmation_id="adoption-confirm")
    assert exc.value.code == "ERR_OUTPUT_ADOPTION_CHECKSUM_MISMATCH"
    assert [item["state"] for item in app.snapshot()["records"]] == ["PREPARED", "FAILED_KNOWN"]
    assert production.candidate is None
    assert prompt.attempt is None


def test_regenerated_prompt_output_is_parked_until_strategy_parent_binding_is_exact(tmp_path: Path):
    app, execution, queue, production, prompt, _port = fixture(tmp_path)
    execution.event["prompt_version"] = 2
    queue.entry["prompt_version"] = 2
    state = app.snapshot()
    assert state["eligible_completed_outputs"][0]["adoption_status"] == "PARKED_STRATEGY_BINDING_REQUIRED"
    with pytest.raises(ProductError) as exc:
        prepare(app, execution, queue, production, prompt)
    assert exc.value.code == "ERR_OUTPUT_ADOPTION_REGENERATION_STRATEGY_UNBOUND"
    assert not app.snapshot_path.exists()


def test_regenerated_prompt_output_uses_exact_queue_strategy_and_parent(tmp_path: Path):
    app, execution, queue, production, prompt, _port = fixture(tmp_path)
    execution.event["prompt_version"] = 2
    queue.entry["prompt_version"] = 2
    queue.entry["execution_lineage"] = {
        "lineage_version": "1.0.0", "kind": "REGENERATION", "strategy_level": 2,
        "parent_attempt_id": "job-parent", "regeneration_plan_sha256": SHA_3,
    }
    prompt.prompt_version = 2
    prompt.regeneration_binding = {
        "binding_version": "1.0.0", "parent_prompt_id": "prompt-1",
        "parent_prompt_version": 1, "parent_prompt_sha256": SHA_4,
        "parent_attempt_id": "job-parent", "strategy_level": 2,
        "reason_codes": ["DEPTH_ORDER"], "regeneration_plan_sha256": SHA_3,
    }
    assert app.snapshot()["eligible_completed_outputs"][0]["adoption_status"] == "READY"
    prepared = prepare(app, execution, queue, production, prompt)
    assert prepared["execution_lineage"]["parent_attempt_id"] == "job-parent"
    result = app.apply_adoption(confirmation_id=prepared["confirmation_id"])
    assert result["records"][-1]["state"] == "READY_FOR_AUDIT"
    assert prompt.attempt["strategy_level"] == 2
    assert prompt.attempt["parent_attempt_id"] == "job-parent"


def test_regenerated_output_blocks_when_queue_and_prompt_binding_differ(tmp_path: Path):
    app, execution, queue, production, prompt, _port = fixture(tmp_path)
    execution.event["prompt_version"] = 2
    queue.entry["prompt_version"] = 2
    queue.entry["execution_lineage"] = {
        "lineage_version": "1.0.0", "kind": "REGENERATION", "strategy_level": 1,
        "parent_attempt_id": "job-parent", "regeneration_plan_sha256": SHA_3,
    }
    prompt.prompt_version = 2
    prompt.regeneration_binding = {
        "binding_version": "1.0.0", "parent_prompt_id": "prompt-1",
        "parent_prompt_version": 1, "parent_prompt_sha256": SHA_4,
        "parent_attempt_id": "job-parent", "strategy_level": 2,
        "reason_codes": ["DEPTH_ORDER"], "regeneration_plan_sha256": SHA_3,
    }
    with pytest.raises(ProductError) as exc:
        prepare(app, execution, queue, production, prompt)
    assert exc.value.code == "ERR_OUTPUT_ADOPTION_REGENERATION_BINDING_DRIFT"
    assert production.candidate is None


def test_recovery_continues_exact_suffix_without_reingesting_asset(tmp_path: Path):
    app, execution, queue, production, prompt, port = fixture(tmp_path)
    prepare(app, execution, queue, production, prompt)
    original = app._continue

    def interrupt_after_asset(store, latest, event):
        asset = app.asset_port.adopt(event)
        app._append(store, app._base(event, latest["candidate_id"]), "ASSET_REGISTERED", asset_id=asset.asset_id)
        raise KeyboardInterrupt()

    app._continue = interrupt_after_asset
    with pytest.raises(KeyboardInterrupt):
        app.apply_adoption(confirmation_id="adoption-confirm")
    app._continue = original
    active = app.snapshot()["recovery"]["active"][0]
    result = app.apply_recovery(adoption_id=active["adoption_id"])
    assert port.calls == 1
    assert port.verify_calls == 1
    assert result["recovery"]["required"] is False
    assert result["records"][-1]["state"] == "READY_FOR_AUDIT"


def test_recovery_rejects_completed_execution_event_identity_drift(tmp_path: Path):
    app, execution, queue, production, prompt, _port = fixture(tmp_path)
    prepare(app, execution, queue, production, prompt)

    def interrupt_after_asset(store, latest, event):
        asset = app.asset_port.adopt(event)
        app._append(store, app._base(event, latest["candidate_id"]), "ASSET_REGISTERED", asset_id=asset.asset_id)
        raise KeyboardInterrupt()

    original = app._continue
    app._continue = interrupt_after_asset
    with pytest.raises(KeyboardInterrupt):
        app.apply_adoption(confirmation_id="adoption-confirm")
    app._continue = original
    active = app.snapshot()["recovery"]["active"][0]
    execution.event["provider_id"] = "different-provider"
    with pytest.raises(ProductError) as exc:
        app.apply_recovery(adoption_id=active["adoption_id"])
    assert exc.value.code == "ERR_OUTPUT_ADOPTION_RECOVERY_IDENTITY_DRIFT"
    assert production.candidate is None
    assert prompt.attempt is None


@dataclass
class IngestServiceSpy:
    calls: int = 0

    def ingest(self, request):
        self.calls += 1

        class Asset:
            asset_id = "ASSET-01K00000000000000000000000"
            checksum = request.generation_provenance["output_sha256"]

        class Result:
            asset = Asset()

        return Result()


def test_asset_port_rejects_checksum_drift_and_symlink_before_ingest(tmp_path: Path):
    output = tmp_path / "output"
    generated = output / "generated"
    generated.mkdir(parents=True)
    media = generated / "result.mp4"
    media.write_bytes(b"safe-output")
    service = IngestServiceSpy()
    port = Task027GeneratedOutputAssetPort(service, output, "JOB-01K00000000000000000000000", "owner")
    event = ExecutionStub().event
    event["output_sha256"] = sha256_bytes(media.read_bytes())
    identity = port.adopt(event)
    assert identity.asset_sha256 == event["output_sha256"]
    assert service.calls == 1

    event["output_sha256"] = SHA_2
    with pytest.raises(ProductError) as mismatch:
        port.adopt(event)
    assert mismatch.value.code == "ERR_OUTPUT_ADOPTION_CHECKSUM_MISMATCH"
    assert service.calls == 1

    link = generated / "linked.mp4"
    try:
        link.symlink_to(media)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    event["output_ref"] = "project-output://generated/linked.mp4"
    event["output_sha256"] = sha256_bytes(media.read_bytes())
    with pytest.raises(ProductError) as symlink:
        port.adopt(event)
    assert symlink.value.code == "ERR_OUTPUT_ADOPTION_SYMLINK"
    assert service.calls == 1


def test_adoption_schema_is_valid_and_packaged_copy_matches():
    root = Path(__file__).parents[1]
    canonical = root / "schemas" / "generation-output-adoption.schema.json"
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "generation-output-adoption.schema.json"
    )
    assert json.loads(canonical.read_text(encoding="utf-8"))["title"].startswith("TASK-027")
    assert canonical.read_text(encoding="utf-8") == packaged.read_text(encoding="utf-8")


def test_real_task003_037_040_stores_close_lineage_end_to_end(tmp_path: Path):
    output_root = tmp_path / "generation-output"
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    for root in (output_root / "generated", asset_root, job_root):
        root.mkdir(parents=True)
    output = output_root / "generated" / "result.mp4"
    output.write_bytes(b"bounded synthetic video output")

    class VideoProbe:
        def probe(self, path):
            return MediaProbeResult("mp4", 1_000_000, Path(path).stat().st_size, None, ({"codec_type": "video"},))

        def assert_compatible(self, asset_type, result):
            assert result.has_video

    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile = ProfileSnapshot.create("task027-test", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    service = AssetIngestService(
        store=store,
        resolver=LogicalPathResolver((PathMapping("asset://", asset_root), PathMapping("job://", job_root))),
        source_policy=SourcePathPolicy((output_root,)),
        media_probe=VideoProbe(),
    )
    production_registry = ProductionControlRegistry()
    production_registry.add_slot(SceneAssetSlot("slot-video", "project-1", "scene-1", SlotKind.VIDEO, True))
    ProductionControlSnapshotStore.save(tmp_path / "production-control.json", production_registry)
    prompt_registry = PromptGenerationRegistry()
    prompt_registry.add_prompt(PromptEntity(
        "prompt-1", 1, "scene video", SHA_1, "profile-1", "v1", ("keep identity",),
        scene_id="scene-1", slot_id="slot-video", body_ref="project-private://prompts/prompt-1/v1",
    ))
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompt_registry)

    execution = ExecutionStub()
    execution.event["output_sha256"] = sha256_bytes(output.read_bytes())
    queue = QueueStub()
    production = Task037ProductionControlApplication(project_root=tmp_path, project_id="project-1")
    prompt = Task040PromptEvidenceApplication(
        project_root=tmp_path,
        project_id="project-1",
        production_control=production,
        token_factory=lambda: "prompt-attempt-confirm",
    )
    app = Task027GenerationOutputAdoptionApplication(
        project_root=tmp_path,
        project_id="project-1",
        generation_execution=execution,
        generation_queue=queue,
        production_control=production,
        prompt_evidence=prompt,
        asset_port=Task027GeneratedOutputAssetPort(service, output_root, job.job_id, "owner"),
        token_factory=lambda: "adoption-confirm",
    )
    prepared = prepare(app, execution, queue, production, prompt)
    result = app.apply_adoption(confirmation_id=prepared["confirmation_id"])

    assert result["records"][-1]["state"] == "READY_FOR_AUDIT"
    candidate = production.snapshot()["slots"][0]["candidates"][0]
    assert candidate["lifecycle_state"] == "READY_FOR_AUDIT"
    asset = store.get_asset(candidate["asset_id"])
    assert asset.checksum == execution.event["output_sha256"]
    assert asset.rights_status.value == "UNKNOWN"
    assert "PUBLICATION_NOT_AUTHORIZED" in asset.publication_restrictions
    prompt_state = prompt.snapshot()
    assert prompt_state["attempt_count"] == 1
    assert prompt_state["prompts"][0]["attempts"][0]["output_candidate_id"] == candidate["candidate_id"]
    persisted = ProductionControlSnapshotStore.load(tmp_path / "production-control.json")
    assert any(edge.to_ref.entity_id == candidate["candidate_id"] for edge in persisted.edges.values())


def test_real_image_output_becomes_canonical_asset_and_audit_candidate(tmp_path: Path):
    output_root = tmp_path / "generation-output"
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    output = output_root / "generated" / "EXEC-IMAGE-1" / "result.png"
    for root in (output.parent, asset_root, job_root):
        root.mkdir(parents=True)
    output.write_bytes(b"structurally-verified-image-bytes")

    class ImageProbe:
        def probe(self, path):
            return MediaProbeResult(
                "png", None, Path(path).stat().st_size, None,
                ({"codec_type": "video", "codec_name": "png", "width": 64, "height": 64},),
            )

        def assert_compatible(self, asset_type, result):
            assert result.has_video

    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile = ProfileSnapshot.create("task027-image-test", "1.0.0", {})
    job = store.create_job(profile.profile_snapshot_id)
    service = AssetIngestService(
        store=store,
        resolver=LogicalPathResolver((
            PathMapping("asset://", asset_root), PathMapping("job://", job_root),
        )),
        source_policy=SourcePathPolicy((output_root,)),
        media_probe=ImageProbe(),
    )
    production_registry = ProductionControlRegistry()
    production_registry.add_slot(SceneAssetSlot(
        "slot-start", "project-1", "scene-1", SlotKind.START_FRAME, True,
    ))
    ProductionControlSnapshotStore.save(tmp_path / "production-control.json", production_registry)
    prompt_registry = PromptGenerationRegistry()
    prompt_registry.add_prompt(PromptEntity(
        "prompt-1", 1, "scene start image", SHA_1, "profile-1", "v1",
        ("keep composition",), scene_id="scene-1", slot_id="slot-start",
        body_ref="project-private://prompts/prompt-1/v1",
    ))
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompt_registry)

    execution = ExecutionStub()
    execution.event.update({
        "slot_id": "slot-start",
        "provider_id": "comfy-image",
        "model_id": "flux-schnell-fp8",
        "output_ref": "project-output://generated/EXEC-IMAGE-1/result.png",
        "output_sha256": sha256_bytes(output.read_bytes()),
        "media_kind": "IMAGE",
    })
    queue = QueueStub()
    queue.entry["slot_id"] = "slot-start"
    production = Task037ProductionControlApplication(
        project_root=tmp_path, project_id="project-1",
    )
    prompt = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1",
        production_control=production,
        token_factory=lambda: "prompt-image-attempt-confirm",
    )
    app = Task027GenerationOutputAdoptionApplication(
        project_root=tmp_path,
        project_id="project-1",
        generation_execution=execution,
        generation_queue=queue,
        production_control=production,
        prompt_evidence=prompt,
        asset_port=Task027GeneratedOutputAssetPort(
            service, output_root, job.job_id, "owner",
        ),
        token_factory=lambda: "adoption-image-confirm",
    )
    prepared = prepare(app, execution, queue, production, prompt)
    result = app.apply_adoption(confirmation_id=prepared["confirmation_id"])

    assert result["records"][-1]["state"] == "READY_FOR_AUDIT"
    candidate = production.snapshot()["slots"][0]["candidates"][0]
    assert candidate["lifecycle_state"] == "READY_FOR_AUDIT"
    asset = store.get_asset(candidate["asset_id"])
    assert asset.asset_type.value == "IMAGE"
    assert asset.checksum == execution.event["output_sha256"]
    assert "PUBLICATION_NOT_AUTHORIZED" in asset.publication_restrictions
    assert prompt.snapshot()["prompts"][0]["attempts"][0]["output_candidate_id"] == candidate["candidate_id"]


def test_bound_shell_executes_one_fake_local_image_and_adopts_exact_bytes(tmp_path: Path):
    from ai_video_production.local_comfy_image_generation_port import _probe_png

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
        )

    rows = b"".join(b"\x00" + (b"\x20\x40\x60" * 64) for _ in range(64))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )
    _probe_png(raw=png, width=64, height=64, max_bytes=1024 * 1024)

    output_root = tmp_path / "generation-output"
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    prompt_file = tmp_path / "private" / "prompts" / "prompt-1" / "v1"
    for root in (output_root, asset_root, job_root, prompt_file.parent):
        root.mkdir(parents=True, exist_ok=True)
    prompt_body = b"calm blue opening composition"
    prompt_file.write_bytes(prompt_body)
    prompt_sha = sha256_bytes(prompt_body)

    class StrictImageProbe:
        def probe(self, path):
            raw = Path(path).read_bytes()
            _probe_png(raw=raw, width=64, height=64, max_bytes=1024 * 1024)
            return MediaProbeResult(
                "png", None, len(raw), None,
                ({"codec_type": "video", "codec_name": "png", "width": 64, "height": 64},),
            )

        def assert_compatible(self, asset_type, result):
            assert result.has_video

    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile_snapshot = ProfileSnapshot.create("task027-shell-image", "1.0.0", {})
    job = store.create_job(profile_snapshot.profile_snapshot_id)
    ingest = AssetIngestService(
        store=store,
        resolver=LogicalPathResolver((
            PathMapping("asset://", asset_root), PathMapping("job://", job_root),
        )),
        source_policy=SourcePathPolicy((output_root,)),
        media_probe=StrictImageProbe(),
    )
    production_registry = ProductionControlRegistry()
    production_registry.add_slot(SceneAssetSlot(
        "slot-start", "project-1", "scene-1", SlotKind.START_FRAME, True,
    ))
    ProductionControlSnapshotStore.save(
        tmp_path / "production-control.json", production_registry,
    )
    prompt_registry = PromptGenerationRegistry()
    prompt_registry.add_prompt(PromptEntity(
        "prompt-1", 1, prompt_body.decode("utf-8"), prompt_sha,
        "profile-1", "v1", ("keep composition",),
        scene_id="scene-1", slot_id="slot-start",
        body_ref="project-private://prompts/prompt-1/v1",
    ))
    PromptRegistrySnapshotStore.save(
        tmp_path / "prompt-registry.json", prompt_registry,
    )
    production = Task037ProductionControlApplication(
        project_root=tmp_path, project_id="project-1",
    )
    prompt = Task040PromptEvidenceApplication(
        project_root=tmp_path,
        project_id="project-1",
        production_control=production,
        token_factory=lambda: "prompt-shell-attempt-confirm",
    )

    entry = {
        "project_id": "project-1",
        "queue_entry_id": "QUEUE-1234567890ABCDEF12345678",
        "queue_status": "ADMISSION_READY",
        "execution_status": "EXECUTION_NOT_AUTHORIZED",
        "scene_id": "scene-1",
        "slot_id": "slot-start",
        "prompt_id": "prompt-1",
        "prompt_version": 1,
        "prompt_sha256": prompt_sha,
        "provider_profile_id": "profile-1",
        "provider_profile_version": "v1",
        "input_bindings": [],
    }

    class ExecutableQueue:
        project_root = tmp_path
        project_id = "project-1"
        production_control = production
        prompt_evidence_application = prompt

        def snapshot(self):
            return {
                "project_id": self.project_id,
                "queue_snapshot_sha256": SHA_4,
                "entries": [dict(entry)],
                "available_prompts": [],
                "entry_count": 1,
            }

        def require_current_entry(self, *, queue_entry_id):
            assert queue_entry_id == entry["queue_entry_id"]
            return {"queue_snapshot_sha256": SHA_4, "entry": dict(entry)}

    queue = ExecutableQueue()
    route = ModelRoute(
        "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
        "comfy-image", "flux-schnell-fp8", CostClass.LOCAL_FREE_AI,
        capabilities=("TEXT_TO_IMAGE",),
    )
    ConnectionSettingsStore.save(
        tmp_path / "ai-connection-settings.json",
        AiConnectionProfile("profile-1", "v1", SelectionMode.AUTO, (route,)),
    )

    class FakeLocalImagePort:
        def __init__(self):
            self.execute_calls = 0

        def preflight(self):
            return LocalGenerationRuntimeReadiness(
                "local-image", "comfy-image", "flux-schnell-fp8",
                "sha256:" + "7" * 64, 6, "FIXED_LOOPBACK_FLUX_SCHNELL_V1",
            )

        def execute(self, selected_route, request):
            self.execute_calls += 1
            target = output_root / "generated" / request.execution_id / "result.png"
            target.parent.mkdir(parents=True)
            target.write_bytes(png)
            return LocalGenerationExecutionResult(
                selected_route.route_id,
                selected_route.provider_family,
                selected_route.provider_id,
                selected_route.model_id,
                request.capability,
                "fake-operation-1",
                f"project-output://generated/{request.execution_id}/result.png",
                sha256_bytes(png),
                "IMAGE",
                1,
            )

        def recover(self, selected_route, request):
            raise AssertionError("recovery is not used by the success vertical")

    port = FakeLocalImagePort()
    execution = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path,
        project_id="project-1",
        generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-image"})),
        token_factory=lambda: "execution-shell-confirm",
    )
    adoption = Task027GenerationOutputAdoptionApplication(
        project_root=tmp_path,
        project_id="project-1",
        generation_execution=execution,
        generation_queue=queue,
        production_control=production,
        prompt_evidence=prompt,
        asset_port=Task027GeneratedOutputAssetPort(
            ingest, output_root, job.job_id, "owner", max_output_bytes=1024 * 1024,
        ),
        token_factory=lambda: "adoption-shell-confirm",
    )

    @contextmanager
    def active_lease():
        yield

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.22.0"),
        production_control=production,
        prompt_evidence_application=prompt,
        generation_queue_application=queue,
        generation_execution_application=execution,
        generation_output_adoption_application=adoption,
        nle_runtime_guard=active_lease,
    )
    model = bridge.generation_queue_snapshot({})
    readiness = bridge.generation_execution_preflight({
        "queue_entry_id": entry["queue_entry_id"],
    })
    assert readiness["dispatch_performed"] is False
    prepared = bridge.generation_execution_prepare({
        "queue_entry_id": entry["queue_entry_id"],
        "expected_queue_snapshot_sha256": model["queue_snapshot_sha256"],
        "expected_execution_snapshot_sha256": model["execution_control"]["execution_snapshot_sha256"],
    })
    executed = bridge.generation_execution_apply({
        "confirmation_id": prepared["confirmation_id"],
    })
    completed = executed["latest_executions"][0]
    output = output_root / completed["output_ref"].removeprefix("project-output://")
    assert port.execute_calls == 1
    assert output.read_bytes() == png
    assert completed["output_sha256"] == sha256_bytes(png)

    model = bridge.generation_queue_snapshot({})
    production_state = production.snapshot()
    prompt_state = prompt.snapshot()
    prepared_adoption = bridge.generation_output_adoption_prepare({
        "execution_id": completed["execution_id"],
        "expected_execution_snapshot_sha256": model["execution_control"]["execution_snapshot_sha256"],
        "expected_queue_snapshot_sha256": model["queue_snapshot_sha256"],
        "expected_production_snapshot_sha256": production_state["snapshot_sha256"],
        "expected_prompt_snapshot_sha256": prompt_state["prompt_snapshot_sha256"],
        "expected_adoption_snapshot_sha256": model["output_adoption_control"]["adoption_snapshot_sha256"],
    })
    adopted = bridge.generation_output_adoption_apply({
        "confirmation_id": prepared_adoption["confirmation_id"],
    })
    assert adopted["records"][-1]["state"] == "READY_FOR_AUDIT"
    candidate = production.snapshot()["slots"][0]["candidates"][0]
    assert candidate["lifecycle_state"] == "READY_FOR_AUDIT"
    asset = store.get_asset(candidate["asset_id"])
    assert asset.asset_type.value == "IMAGE"
    assert asset.checksum == sha256_bytes(png)
    assert "PUBLICATION_NOT_AUTHORIZED" in asset.publication_restrictions
    assert adopted["publication_authorized"] is False
    assert adopted["candidate_accepted"] is False
    assert adopted["candidate_locked"] is False


def test_real_task037_040_stores_adopt_regenerated_output_with_exact_lineage(tmp_path: Path):
    production_registry = ProductionControlRegistry()
    production_registry.add_slot(SceneAssetSlot("slot-video", "project-1", "scene-1", SlotKind.VIDEO, True))
    production_registry.add_candidate(AssetCandidate(
        "candidate-old", "slot-video", "asset-old", SHA_4, 1,
        generation_job_id="job-parent",
    ))
    ProductionControlSnapshotStore.save(tmp_path / "production-control.json", production_registry)

    prompt_registry = PromptGenerationRegistry()
    prompt_registry.add_prompt(PromptEntity(
        "prompt-1", 1, "scene video", SHA_1, "profile-1", "v1", ("keep identity",),
        scene_id="scene-1", slot_id="slot-video", body_ref="project-private://prompts/prompt-1/v1",
    ))
    prompt_registry.add_attempt(GenerationAttempt(
        "job-parent", "slot-video", "prompt-1", 1, SHA_1, "comfy", "minimax-h3",
        RegenerationStrategy.TEXT_PROMPT, GenerationResult.PASS, (), "candidate-old",
        provider_profile_version="v1",
    ))
    prompt_registry.add_prompt(PromptEntity(
        "prompt-1", 2, "scene video", SHA_1, "profile-1", "v1", ("keep identity",),
        scene_id="scene-1", slot_id="slot-video", body_ref="project-private://prompts/prompt-1/v2",
        regeneration_binding=PromptRegenerationBinding(
            "1.0.0", "prompt-1", 1, SHA_1, "job-parent",
            RegenerationStrategy.LAYOUT_REFERENCE, ("DEPTH_ORDER",), SHA_3,
        ),
    ))
    PromptRegistrySnapshotStore.save(tmp_path / "prompt-registry.json", prompt_registry)

    execution = ExecutionStub()
    execution.event["prompt_version"] = 2
    queue = QueueStub()
    queue.entry["prompt_version"] = 2
    queue.entry["execution_lineage"] = {
        "lineage_version": "1.0.0", "kind": "REGENERATION", "strategy_level": 2,
        "parent_attempt_id": "job-parent", "regeneration_plan_sha256": SHA_3,
    }
    production = Task037ProductionControlApplication(project_root=tmp_path, project_id="project-1")
    prompt = Task040PromptEvidenceApplication(
        project_root=tmp_path, project_id="project-1", production_control=production,
        token_factory=lambda: "prompt-confirm",
    )
    app = Task027GenerationOutputAdoptionApplication(
        project_root=tmp_path, project_id="project-1", generation_execution=execution,
        generation_queue=queue, production_control=production, prompt_evidence=prompt,
        asset_port=AssetPortStub(), token_factory=lambda: "adoption-confirm",
    )
    prepared = prepare(app, execution, queue, production, prompt)
    result = app.apply_adoption(confirmation_id=prepared["confirmation_id"])

    assert result["records"][-1]["state"] == "READY_FOR_AUDIT"
    state = prompt.snapshot()
    attempt = next(
        item for row in state["prompts"] for item in row["attempts"]
        if item["generation_job_id"] == "execution-1"
    )
    assert attempt["strategy_level"] == 2
    assert attempt["parent_attempt_id"] == "job-parent"
