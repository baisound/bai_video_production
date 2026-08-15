from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path

import pytest

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
from ai_video_production.production_control import ProductionControlRegistry, SceneAssetSlot, SlotKind
from ai_video_production.production_control_application import Task037ProductionControlApplication
from ai_video_production.production_control_store import ProductionControlSnapshotStore
from ai_video_production.profile import ProfileSnapshot
from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
from ai_video_production.prompt_registry import PromptEntity, PromptGenerationRegistry
from ai_video_production.prompt_registry_store import PromptRegistrySnapshotStore
from ai_video_production.store import SQLiteProductStore


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

    def snapshot(self):
        attempts = [] if self.attempt is None else [dict(self.attempt)]
        return {
            "prompt_snapshot_sha256": self.sha,
            "production_snapshot_sha256": self.production.sha,
            "recovery": dict(self.recovery),
            "prompts": [{"prompt_id": "prompt-1", "prompt_version": 1, "attempts": attempts}],
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
