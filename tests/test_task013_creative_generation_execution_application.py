from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from ai_video_production.ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass,
    ModelRoute, ProviderFamily, SelectionMode,
)
from ai_video_production.connection_settings_store import ConnectionSettingsStore
from ai_video_production.creative_generation_execution_application import (
    LocalGenerationExecutionResult,
    LocalGenerationRuntimeReadiness,
    Task013CreativeGenerationExecutionApplication,
)
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


class SnapshotStub:
    def __init__(self, value: dict):
        self.value = value

    def snapshot(self) -> dict:
        return self.value

class QueueStub:
    def __init__(self, root: Path, entry: dict, prompt: dict):
        self.project_root = root
        self.project_id = "project-1"
        self.value = {
            "queue_snapshot_sha256": "sha256:" + "1" * 64,
            "entries": [entry],
        }
        self.prompt_evidence_application = SnapshotStub({"prompts": [prompt]})
        self.production_control = SnapshotStub({
            "slots": [{"slot_id": entry["slot_id"], "scene_id": entry["scene_id"], "slot_kind": "VIDEO"}],
        })

    def snapshot(self) -> dict:
        return self.value

    def require_current_entry(self, *, queue_entry_id: str) -> dict:
        entry = next((item for item in self.value["entries"] if item["queue_entry_id"] == queue_entry_id), None)
        if entry is None:
            raise ProductError("ERR_QUEUE_ENTRY_NOT_FOUND", "missing", ProductErrorCategory.STATE)
        return {"queue_snapshot_sha256": self.value["queue_snapshot_sha256"], "entry": entry}


class FakePort:
    def __init__(self, *, failure: BaseException | None = None):
        self.calls = []
        self.failure = failure

    def preflight(self):
        return LocalGenerationRuntimeReadiness(
            "local-video", "comfy", "model-v1", "sha256:" + "8" * 64,
            13, "DEFAULT_DYNAMIC_VRAM_INCIDENT_HARDENED_V1",
        )

    def execute(self, route, request):
        self.calls.append((route, request))
        if self.failure is not None:
            raise self.failure
        return LocalGenerationExecutionResult(
            route.route_id, route.provider_family, route.provider_id, route.model_id,
            request.capability, "operation-1", "project-output://generated/result.mp4",
            "sha256:" + "9" * 64, "VIDEO", 125,
        )


class ImagePort(FakePort):
    def preflight(self):
        return LocalGenerationRuntimeReadiness(
            "local-image", "comfy-image", "flux-schnell", "sha256:" + "7" * 64,
            6, "FIXED_LOOPBACK_FLUX_SCHNELL_V1",
        )

def fixture(root: Path, *, cost_class: CostClass = CostClass.LOCAL_FREE_AI, failure: BaseException | None = None):
    prompt_bytes = b"quiet cinematic opening"
    prompt_sha = sha256_bytes(prompt_bytes)
    prompt_dir = root / "private" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "opening.txt").write_bytes(prompt_bytes)
    prompt = {
        "prompt_id": "prompt-1", "prompt_version": 1, "scene_id": "scene-1", "slot_id": "slot-video",
        "body_ref": "project-private://prompts/opening.txt", "body_sha256": prompt_sha,
        "provider_profile_id": "profile-1", "provider_profile_version": "v1",
    }
    entry = {
        "project_id": "project-1", "queue_entry_id": "QUEUE-1234567890ABCDEF12345678",
        "queue_status": "ADMISSION_READY", "execution_status": "EXECUTION_NOT_AUTHORIZED",
        "scene_id": "scene-1", "slot_id": "slot-video", "prompt_id": "prompt-1", "prompt_version": 1,
        "prompt_sha256": prompt_sha, "provider_profile_id": "profile-1", "provider_profile_version": "v1",
        "input_bindings": [],
    }
    route = ModelRoute(
        "local-video", AiWorkload.VIDEO, ProviderFamily.COMFYUI, "comfy", "model-v1", cost_class,
        credential_ref="credential://provider/key" if cost_class is CostClass.CLOUD_PAID_AI else None,
        capabilities=("TEXT_TO_VIDEO",),
    )
    profile = AiConnectionProfile("profile-1", "v1", SelectionMode.AUTO, (route,))
    ConnectionSettingsStore.save(root / "ai-connection-settings.json", profile)
    queue = QueueStub(root, entry, prompt)
    port = FakePort(failure=failure)
    app = Task013CreativeGenerationExecutionApplication(
        project_root=root, project_id="project-1", generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"}), frozenset({"credential://provider/key"})),
        token_factory=lambda: "execution-confirm",
    )
    return app, queue, port


def prepare(app: Task013CreativeGenerationExecutionApplication, queue: QueueStub):
    state = app.snapshot()
    return app.prepare_execution(
        queue_entry_id=queue.value["entries"][0]["queue_entry_id"],
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_execution_snapshot_sha256=state["execution_snapshot_sha256"],
    )


def test_runtime_preflight_is_explicit_read_only_and_creates_no_project_state(tmp_path: Path):
    app, _queue, port = fixture(tmp_path)
    result = app.runtime_preflight()
    assert result["result"] == "SAFE_RUNTIME_PREFLIGHT_PASS_EXECUTION_PARKED"
    assert result["execution_authorized"] is False
    assert result["dispatch_performed"] is False
    assert result["journal_created"] is False
    assert result["native_gate_satisfied"] is False
    assert port.calls == []
    assert not app.snapshot_path.exists()


def test_route_capability_selector_requires_queue_scope_and_selects_exact_image_port(tmp_path: Path):
    app, queue, _video_port = fixture(tmp_path)
    queue.production_control.value["slots"][0]["slot_kind"] = "START_FRAME"
    image_route = ModelRoute(
        "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
        "comfy-image", "flux-schnell", CostClass.LOCAL_FREE_AI,
        capabilities=("TEXT_TO_IMAGE",),
    )
    ConnectionSettingsStore.save(
        tmp_path / "ai-connection-settings.json",
        AiConnectionProfile("profile-1", "v1", SelectionMode.AUTO, (image_route,)),
        expected_revision=ConnectionSettingsStore.load(
            tmp_path / "ai-connection-settings.json"
        ).record.revision,
    )
    calls = []
    image_port = ImagePort()

    def selector(route, capability):
        calls.append((route.route_id, capability))
        if (route.route_id, capability) != ("local-image", "TEXT_TO_IMAGE"):
            raise ProductError("ERR_UNSUPPORTED", "unsupported", ProductErrorCategory.NOT_SUPPORTED)
        return image_port

    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=None, execution_port_selector=selector,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-image"})),
    )
    with pytest.raises(ProductError) as unscoped:
        selected.runtime_preflight()
    assert unscoped.value.code == "ERR_GENERATION_EXECUTION_PREFLIGHT_SCOPE_REQUIRED"
    readiness = selected.runtime_preflight(queue_entry_id=queue.value["entries"][0]["queue_entry_id"])
    assert readiness["route_id"] == "local-image"
    assert readiness["model_id"] == "flux-schnell"
    assert calls == [("local-image", "TEXT_TO_IMAGE")]
    assert image_port.calls == []
    assert not selected.snapshot_path.exists()


def test_selector_is_rechecked_at_apply_and_confirmation_is_single_use(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    selector_calls = []

    def selector(route, capability):
        selector_calls.append((route.route_id, capability))
        return port

    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=None, execution_port_selector=selector,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "selector-confirm",
    )
    prepare(selected, queue)
    selected.apply_execution(confirmation_id="selector-confirm")
    with pytest.raises(ProductError) as replay:
        selected.apply_execution(confirmation_id="selector-confirm")
    assert replay.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION"
    assert selector_calls == [
        ("local-video", "TEXT_TO_VIDEO"),
        ("local-video", "TEXT_TO_VIDEO"),
    ]
    assert len(port.calls) == 1


def test_selector_rejection_prevents_confirmation_and_dispatch(tmp_path: Path):
    _app, queue, port = fixture(tmp_path)

    def reject(_route, _capability):
        raise ProductError("ERR_IMAGE_PORT_NOT_BOUND", "not bound", ProductErrorCategory.NOT_SUPPORTED)

    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=None, execution_port_selector=reject,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "unused-confirm",
    )
    with pytest.raises(ProductError) as exc:
        prepare(selected, queue)
    assert exc.value.code == "ERR_IMAGE_PORT_NOT_BOUND"
    assert port.calls == []
    assert not selected.snapshot_path.exists()


def test_wrong_selected_runtime_identity_fails_before_confirmation_or_history(tmp_path: Path):
    _app, queue, _port = fixture(tmp_path)
    wrong_port = ImagePort()
    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=None, execution_port_selector=lambda _route, _capability: wrong_port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "wrong-runtime-confirm",
    )
    with pytest.raises(ProductError) as exc:
        prepare(selected, queue)
    assert exc.value.code == "ERR_GENERATION_PREFLIGHT_ROUTE_MISMATCH"
    assert wrong_port.calls == []
    assert not selected.snapshot_path.exists()


def test_runtime_identity_drift_after_confirmation_fails_before_dispatching(tmp_path: Path):
    _app, queue, port = fixture(tmp_path)
    preflight_count = 0

    def drifting_preflight():
        nonlocal preflight_count
        preflight_count += 1
        return LocalGenerationRuntimeReadiness(
            "local-video", "comfy", "model-v1",
            "sha256:" + ("8" if preflight_count == 1 else "7") * 64,
            13, "DEFAULT_DYNAMIC_VRAM_INCIDENT_HARDENED_V1",
        )

    port.preflight = drifting_preflight
    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=None, execution_port_selector=lambda _route, _capability: port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "drift-confirm",
    )
    prepare(selected, queue)
    with pytest.raises(ProductError) as exc:
        selected.apply_execution(confirmation_id="drift-confirm")
    assert exc.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION_STALE"
    assert port.calls == []
    assert not selected.snapshot_path.exists()
    with pytest.raises(ProductError) as replay:
        selected.apply_execution(confirmation_id="drift-confirm")
    assert replay.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION"


def test_profile_drift_during_apply_preflight_fails_before_dispatching(tmp_path: Path):
    _app, queue, port = fixture(tmp_path)
    preflight_entered = Event()
    release_preflight = Event()
    preflight_count = 0
    original_preflight = port.preflight

    def blocking_preflight():
        nonlocal preflight_count
        preflight_count += 1
        if preflight_count == 2:
            preflight_entered.set()
            assert release_preflight.wait(timeout=5)
        return original_preflight()

    port.preflight = blocking_preflight
    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "midflight-profile-confirm",
    )
    prepare(selected, queue)

    with ThreadPoolExecutor(max_workers=1) as pool:
        applied = pool.submit(
            selected.apply_execution,
            confirmation_id="midflight-profile-confirm",
        )
        assert preflight_entered.wait(timeout=5)
        current = ConnectionSettingsStore.load(
            tmp_path / "ai-connection-settings.json"
        ).record
        changed_route = ModelRoute(
            "local-video", AiWorkload.VIDEO, ProviderFamily.COMFYUI,
            "comfy", "model-v1", CostClass.LOCAL_FREE_AI,
            capabilities=("TEXT_TO_VIDEO",),
        )
        ConnectionSettingsStore.save(
            tmp_path / "ai-connection-settings.json",
            AiConnectionProfile("profile-1", "v2", SelectionMode.AUTO, (changed_route,)),
            expected_revision=current.revision,
        )
        release_preflight.set()
        with pytest.raises(ProductError) as exc:
            applied.result(timeout=5)
    assert exc.value.code == "ERR_GENERATION_EXECUTION_PROFILE_DRIFT"
    assert port.calls == []
    assert not selected.snapshot_path.exists()


def test_parallel_same_confirmation_admits_exactly_one_dispatch(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    prepare(app, queue)

    def apply_once():
        try:
            return app.apply_execution(confirmation_id="execution-confirm")
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: apply_once(), range(2)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count("ERR_GENERATION_EXECUTION_CONFIRMATION") == 1
    assert len(port.calls) == 1
    assert [event["state"] for event in app.snapshot()["events"]] == ["DISPATCHING", "COMPLETED"]


def test_cancel_is_single_use_and_releases_confirmation_capacity(tmp_path: Path):
    _app, queue, port = fixture(tmp_path)
    issued = iter(f"confirm-{index}" for index in range(258))
    selected = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: next(issued),
    )
    state = selected.snapshot()
    for _index in range(256):
        selected.prepare_execution(
            queue_entry_id=queue.value["entries"][0]["queue_entry_id"],
            expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
            expected_execution_snapshot_sha256=state["execution_snapshot_sha256"],
        )
    with pytest.raises(ProductError) as capacity:
        selected.prepare_execution(
            queue_entry_id=queue.value["entries"][0]["queue_entry_id"],
            expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
            expected_execution_snapshot_sha256=state["execution_snapshot_sha256"],
        )
    assert capacity.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION_CAPACITY"
    assert capacity.value.category is ProductErrorCategory.STATE
    cancelled = selected.cancel_execution(confirmation_id="confirm-0")
    assert cancelled["cancelled"] is True
    assert cancelled["provider_execution_started"] is False
    assert not selected.snapshot_path.exists()
    replacement = selected.prepare_execution(
        queue_entry_id=queue.value["entries"][0]["queue_entry_id"],
        expected_queue_snapshot_sha256=state["queue_snapshot_sha256"],
        expected_execution_snapshot_sha256=state["execution_snapshot_sha256"],
    )
    assert replacement["confirmation_id"] == "confirm-257"
    with pytest.raises(ProductError) as duplicate:
        selected.cancel_execution(confirmation_id="confirm-0")
    assert duplicate.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION"
    assert port.calls == []


def test_parallel_cancel_and_apply_admit_only_one_confirmation_action(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    prepare(app, queue)

    def apply_once():
        try:
            app.apply_execution(confirmation_id="execution-confirm")
            return "APPLIED"
        except ProductError as exc:
            return exc.code

    def cancel_once():
        try:
            app.cancel_execution(confirmation_id="execution-confirm")
            return "CANCELLED"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        apply_future = pool.submit(apply_once)
        cancel_future = pool.submit(cancel_once)
        outcomes = [apply_future.result(), cancel_future.result()]
    assert outcomes.count("ERR_GENERATION_EXECUTION_CONFIRMATION") == 1
    assert sum(value in {"APPLIED", "CANCELLED"} for value in outcomes) == 1
    if "APPLIED" in outcomes:
        assert len(port.calls) == 1
        assert [event["state"] for event in app.snapshot()["events"]] == ["DISPATCHING", "COMPLETED"]
    else:
        assert port.calls == []
        assert not app.snapshot_path.exists()


def test_two_application_instances_cannot_dispatch_same_queue_entry_twice(tmp_path: Path):
    _app, queue, port = fixture(tmp_path)
    first = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "first-confirm",
    )
    second = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=port,
        availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
        token_factory=lambda: "second-confirm",
    )
    prepare(first, queue)
    prepare(second, queue)

    def apply(app, token):
        try:
            app.apply_execution(confirmation_id=token)
            return "APPLIED"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda item: apply(*item), ((first, "first-confirm"), (second, "second-confirm"))))
    assert outcomes.count("APPLIED") == 1
    assert outcomes.count("ERR_GENERATION_EXECUTION_CONFLICT") == 1
    assert len(port.calls) == 1


def test_local_execution_is_confirmed_body_private_and_restart_durable(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    prepared = prepare(app, queue)
    assert prepared["cost_class"] == "LOCAL_FREE_AI"
    assert prepared["prompt_body_exposed"] is False
    state = app.apply_execution(confirmation_id="execution-confirm")
    assert [event["state"] for event in state["events"]] == ["DISPATCHING", "COMPLETED"]
    assert state["paid_execution_authorized"] is False
    assert state["candidate_creation_authorized"] is False
    assert port.calls[0][1].prompt_text == "quiet cinematic opening"
    assert "quiet cinematic opening" not in app.snapshot_path.read_text(encoding="utf-8")
    reopened = Task013CreativeGenerationExecutionApplication(
        project_root=tmp_path, project_id="project-1", generation_queue=queue,
        execution_port=FakePort(), availability_factory=lambda: ConnectionAvailability(frozenset({"local-video"})),
    ).snapshot()
    assert reopened["recovery"]["required"] is False
    assert reopened["available_queue_entries"] == []


def test_paid_or_credential_route_is_blocked_before_port_call(tmp_path: Path):
    app, queue, port = fixture(tmp_path, cost_class=CostClass.CLOUD_PAID_AI)
    with pytest.raises(ProductError) as exc:
        prepare(app, queue)
    assert exc.value.code == "ERR_GENERATION_EXECUTION_LOCAL_ONLY"
    assert port.calls == []


def test_private_prompt_checksum_mismatch_blocks_before_dispatch(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    (tmp_path / "private" / "prompts" / "opening.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        prepare(app, queue)
    assert exc.value.code == "ERR_GENERATION_EXECUTION_PROMPT_CHECKSUM"
    assert not app.snapshot_path.exists()
    assert port.calls == []


def test_known_provider_failure_is_terminal_and_not_replayed(tmp_path: Path):
    app, queue, port = fixture(
        tmp_path,
        failure=ProductError("ERR_FAKE_PROVIDER", "fake", ProductErrorCategory.EXTERNAL_DEPENDENCY),
    )
    prepare(app, queue)
    with pytest.raises(ProductError) as exc:
        app.apply_execution(confirmation_id="execution-confirm")
    assert exc.value.code == "ERR_FAKE_PROVIDER"
    assert [event["state"] for event in app.snapshot()["events"]] == ["DISPATCHING", "FAILED"]
    with pytest.raises(ProductError) as second:
        app.prepare_execution(
            queue_entry_id=queue.value["entries"][0]["queue_entry_id"],
            expected_queue_snapshot_sha256=queue.value["queue_snapshot_sha256"],
            expected_execution_snapshot_sha256=app.snapshot()["execution_snapshot_sha256"],
        )
    assert second.value.code == "ERR_GENERATION_EXECUTION_ALREADY_DISPATCHED"


def test_uncertain_interruption_remains_recovery_required_without_auto_retry(tmp_path: Path):
    app, queue, _port = fixture(tmp_path, failure=KeyboardInterrupt())
    prepare(app, queue)
    with pytest.raises(KeyboardInterrupt):
        app.apply_execution(confirmation_id="execution-confirm")
    state = app.snapshot()
    assert [event["state"] for event in state["events"]] == ["DISPATCHING"]
    assert state["recovery"]["required"] is True
    assert state["recovery"]["automatic_retry_allowed"] is False
    assert state["available_queue_entries"] == []


def test_structured_uncertain_port_error_remains_recovery_required(tmp_path: Path):
    uncertain = ProductError(
        "ERR_GENERATION_COMFY_TIMEOUT_UNCERTAIN", "uncertain", ProductErrorCategory.STATE,
        details={"execution_state_uncertain": True, "automatic_retry_allowed": False},
    )
    app, queue, port = fixture(tmp_path, failure=uncertain)
    prepare(app, queue)
    with pytest.raises(ProductError) as exc:
        app.apply_execution(confirmation_id="execution-confirm")
    assert exc.value is uncertain
    assert [event["state"] for event in app.snapshot()["events"]] == ["DISPATCHING"]
    assert app.snapshot()["recovery"]["required"] is True
    assert port.calls and len(port.calls) == 1


def test_confirmation_is_consumed_before_stale_queue_revalidation(tmp_path: Path):
    app, queue, port = fixture(tmp_path)
    prepare(app, queue)
    queue.value["queue_snapshot_sha256"] = "sha256:" + "2" * 64
    with pytest.raises(ProductError) as exc:
        app.apply_execution(confirmation_id="execution-confirm")
    assert exc.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION_STALE"
    queue.value["queue_snapshot_sha256"] = "sha256:" + "1" * 64
    with pytest.raises(ProductError) as replay:
        app.apply_execution(confirmation_id="execution-confirm")
    assert replay.value.code == "ERR_GENERATION_EXECUTION_CONFIRMATION"
    assert port.calls == []


def test_checksum_valid_unknown_event_field_is_rejected(tmp_path: Path):
    app, queue, _port = fixture(tmp_path)
    prepare(app, queue)
    app.apply_execution(confirmation_id="execution-confirm")
    document = json.loads(app.snapshot_path.read_text(encoding="utf-8"))
    document["events"][0]["dispatch_replay_allowed"] = True
    body = {key: value for key, value in document.items() if key != "execution_snapshot_sha256"}
    document["execution_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    app.snapshot_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        app.snapshot()
    assert exc.value.code == "ERR_GENERATION_EXECUTION_EVENT"


def test_checksum_valid_terminal_identity_drift_is_rejected(tmp_path: Path):
    app, queue, _port = fixture(tmp_path)
    prepare(app, queue)
    app.apply_execution(confirmation_id="execution-confirm")
    document = json.loads(app.snapshot_path.read_text(encoding="utf-8"))
    document["events"][1]["model_id"] = "other-model"
    body = {key: value for key, value in document.items() if key != "execution_snapshot_sha256"}
    document["execution_snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    app.snapshot_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        app.snapshot()
    assert exc.value.code == "ERR_GENERATION_EXECUTION_IDENTITY_DRIFT"


def test_result_output_reference_rejects_parent_traversal():
    with pytest.raises(ValueError, match="unsafe path"):
        LocalGenerationExecutionResult(
            "route", ProviderFamily.COMFYUI, "provider", "model", "TEXT_TO_VIDEO",
            "operation", "project-output://generated/../escaped.mp4", "sha256:" + "9" * 64, "VIDEO",
        )
