from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import multiprocessing
import shutil
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production import ProfileSnapshot, SQLiteProductStore
from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from ai_video_production.faster_whisper_runtime_contract import FasterWhisperRuntimeRequestV1
from ai_video_production.faster_whisper_runtime_preflight import evaluate_runtime_preflight
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.task036_product_ports import (
    FasterWhisperProviderSettingsV2,
    RuntimeManagedLocalTranscriptionOutcomeV2,
    Task036RuntimeManagedLocalTranscriptionPortV2,
    Task036LocalTranscriptionPort,
    _Task036LocalTranscriptionOperationEngine,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task098_runtime_transcription_coordination import (
    RuntimeTranscriptionCoordinatesV1,
    RuntimeTranscriptionCoordinatorV1,
    derive_control_key,
    derive_cross_version_guard_key,
    derive_output_slot_key,
    derive_runtime_operation_key_v2,
)
from ai_video_production.task098_runtime_transcription_control import (
    RuntimeTranscriptionAdjudicationDecisionV1,
)


PROJECT_ID = "task098-project"
ASSET_ID = "ASSET-00000000000000000000000000"
T0 = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


class Probe:
    def __init__(self, value: object = True) -> None:
        self.value = value
        self.calls: list[tuple[str, str]] = []

    def supports(self, device: str, compute_type: str) -> bool:
        self.calls.append((device, compute_type))
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value  # type: ignore[return-value]


class FakeModel:
    def transcribe(self, source: str, **kwargs):
        assert Path(source).is_file()
        assert kwargs["language"] == "ja"
        return ([SimpleNamespace(start=0.0, end=1.0, text="hello", words=[])], SimpleNamespace(language="ja"))


def source_file(tmp_path: Path, payload: bytes = b"synthetic source bytes") -> tuple[Path, str]:
    path = tmp_path / "canonical-source.media"
    path.write_bytes(payload)
    return path, "sha256:" + hashlib.sha256(payload).hexdigest()


def make_port(
    tmp_path: Path,
    *,
    settings: FasterWhisperProviderSettingsV2 | None = None,
    requested_device: str = "cpu",
    probe: Probe | None = None,
    provider_factory=None,
    port_clock: datetime | str = T0,
    store_clock: datetime | None = None,
    phase_observer=None,
    lifecycle_observer=None,
) -> tuple[Task036RuntimeManagedLocalTranscriptionPortV2, SQLiteProductStore, Probe, list[FasterWhisperConfig]]:
    db = tmp_path / "product.sqlite3"
    effective_store_clock = store_clock if store_clock is not None else T0
    store = SQLiteProductStore(db, clock=lambda: effective_store_clock)
    job = store.create_job(ProfileSnapshot.create("task098", "1.0.0", {}).profile_snapshot_id)
    observed_probe = probe or Probe(True)
    configs: list[FasterWhisperConfig] = []

    def factory(config: FasterWhisperConfig):
        configs.append(config)
        if provider_factory is not None:
            return provider_factory(config)
        return FasterWhisperProvider(config, model_factory=lambda *_args, **_kwargs: FakeModel())

    port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=settings or FasterWhisperProviderSettingsV2(model="small"),
        runtime_request=FasterWhisperRuntimeRequestV1.create(requested_device),
        capability_probe=observed_probe,
        provider_factory=factory,
        clock=lambda: port_clock,
        output_directory=tmp_path / "transcription",
        store=store,
        production_job_id=job.job_id,
        language="ja",
        phase_observer=phase_observer,
        lifecycle_observer=lifecycle_observer,
    )
    port.output_directory.mkdir()
    return port, store, observed_probe, configs


def execute(port: Task036RuntimeManagedLocalTranscriptionPortV2, source: Path, digest: str):
    return port.transcribe_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )


def test_r2c_capture_has_exact_not_started_projection_and_zero_durable_effect(
    tmp_path: Path,
) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    before = store.list_operations_by_command_prefix(
        port.production_job_id, command_type_prefix="task", limit=32,
    )
    capture = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256="sha256:" + "a" * 64,
    )
    assert capture.public_projection() == {
        "control_mode": "PHASE_ONLY_V1",
        "phase": "NOT_STARTED",
        "cancel_state": "NOT_REQUESTED",
        "adjudication_state": "NOT_REQUIRED",
        "available_action": "NONE",
        "status_label": "音声認識は開始されていません",
        "provider_execution_started": False,
        "provider_execution_known": True,
        "provider_stop_confirmed": False,
        "stop_evidence": "NONE",
        "slot_release_allowed": False,
        "no_replay": True,
    }
    assert store.list_operations_by_command_prefix(
        port.production_job_id, command_type_prefix="task", limit=32,
    ) == before
    assert not (port.output_directory / ".task036-runtime-control").exists()


def test_r2c_pending_main_rejects_orphan_control_evidence(tmp_path: Path) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    digest = "sha256:" + "b" * 64
    engine = port._engine()
    engine._acquire_cross_version_lease(
        PROJECT_ID, ASSET_ID, digest, version="v2",
    )
    operation, created = store.reserve_operation(
        port.production_job_id,
        "task036.local_transcription.v2",
        port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert created is True and operation.status == "PENDING"
    clean = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert clean.public_projection()["status_label"] == "開始待ちです"
    orphan = (
        port.output_directory / ".task036-runtime-control"
        / operation.operation_id
    )
    orphan.mkdir(parents=True)
    (orphan / "orphan.json").write_text("{}", encoding="utf-8")
    blocked = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert blocked.recovery_state == "CORRUPT_BLOCKED"
    assert blocked.public_projection()["status_label"] == "状態が不正なため操作できません"


def test_r2c_process_local_phase_is_bound_to_epoch_and_cleared(tmp_path: Path) -> None:
    port, _store, _probe, _configs = make_port(tmp_path)
    _observation, decision = evaluate_runtime_preflight(
        port.runtime_request, Probe(True), observed_at=port._clock_text(), ttl_seconds=300,
    )
    source_sha = "sha256:" + "b" * 64
    provider_id, model_id, execution_sha = port._execution_identity()
    coordinates = RuntimeTranscriptionCoordinatesV1(
        production_job_id=port.production_job_id,
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=source_sha,
        runtime_operation_id=generate_id(IdKind.OPERATION),
        expected_attempt=1,
        runtime_admission_ref=port._admission_ref(source_sha, decision),
        runtime_request=port.runtime_request,
        runtime_decision=decision,
        provider_id=provider_id,
        model_id=model_id,
        execution_config_sha256=execution_sha,
        slot_operation_id=generate_id(IdKind.OPERATION),
    )
    epoch = port._begin_runtime_invocation(coordinates)
    port._observe_runtime_phase(epoch, "PROVIDER_RUNNING")
    assert port._runtime_active_worker_coordinate == epoch
    assert port._runtime_phase_coordinate == epoch + ("PROVIDER_RUNNING",)
    with pytest.raises(ProductError) as reversed_phase:
        port._observe_runtime_phase(epoch, "PROVIDER_STARTING")
    assert reversed_phase.value.code == "ERR_TASK098_RUNTIME_PHASE_STALE"
    assert port._runtime_phase_coordinate == epoch + ("PROVIDER_RUNNING",)
    port._end_runtime_invocation(epoch)
    assert port._runtime_active_worker_coordinate is None
    assert port._runtime_phase_coordinate is None
    with pytest.raises(ProductError) as stale:
        port._observe_runtime_phase(epoch, "PUBLICATION_VALIDATING")
    assert stale.value.code == "ERR_TASK098_RUNTIME_PHASE_STALE"


def request_runtime_cancel(
    port: Task036RuntimeManagedLocalTranscriptionPortV2,
    store: SQLiteProductStore,
    source_digest: str,
) -> RuntimeTranscriptionCoordinatesV1:
    _observation, decision = evaluate_runtime_preflight(
        port.runtime_request, Probe(True), observed_at=port._clock_text(), ttl_seconds=300,
    )
    operation = store.find_operation(
        port.production_job_id,
        port._operation_key(PROJECT_ID, ASSET_ID, source_digest),
    )
    slot = store.find_operation(
        port.production_job_id,
        derive_output_slot_key(
            production_job_id=port.production_job_id, project_id=PROJECT_ID,
        ),
    )
    assert operation is not None and slot is not None
    provider_id, model_id, execution_sha = port._execution_identity()
    coordinates = RuntimeTranscriptionCoordinatesV1(
        production_job_id=port.production_job_id,
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=source_digest,
        runtime_operation_id=operation.operation_id,
        expected_attempt=operation.attempt,
        runtime_admission_ref=port._admission_ref(source_digest, decision),
        runtime_request=port.runtime_request,
        runtime_decision=decision,
        provider_id=provider_id,
        model_id=model_id,
        execution_config_sha256=execution_sha,
        slot_operation_id=slot.operation_id,
    )
    RuntimeTranscriptionCoordinatorV1(
        store=store, output_directory=port.output_directory.resolve(strict=True),
        clock=port.clock,
    ).request_cancel(coordinates)
    return coordinates


def _v2_process_worker(db: str, output: str, job_id: str, source: str, digest: str, marker: str, barrier, queue) -> None:
    store = SQLiteProductStore(
        db,
        require_existing=True,
        required_job_id=job_id,
        clock=lambda: T0,
    )

    def factory(config: FasterWhisperConfig):
        with Path(marker).open("a", encoding="utf-8") as handle:
            handle.write("provider-entry\n")
        return FasterWhisperProvider(config, model_factory=lambda *_args, **_kwargs: FakeModel())

    Path(output).mkdir(parents=True, exist_ok=True)
    port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=FasterWhisperProviderSettingsV2(model="small"),
        runtime_request=FasterWhisperRuntimeRequestV1.create("cpu"),
        capability_probe=Probe(True),
        provider_factory=factory,
        clock=lambda: T0,
        output_directory=Path(output),
        store=store,
        production_job_id=job_id,
        language="ja",
    )
    try:
        barrier.wait(10)
        execute(port, Path(source), digest)
        queue.put("COMPLETED")
    except ProductError as exc:
        queue.put(exc.code)
    finally:
        store.close()


def _v1_process_worker(db: str, output: str, job_id: str, source: str, digest: str, marker: str, barrier, queue) -> None:
    store = SQLiteProductStore(db, require_existing=True, required_job_id=job_id)

    def model_factory(*_args, **_kwargs):
        with Path(marker).open("a", encoding="utf-8") as handle:
            handle.write("provider-entry\n")
        return FakeModel()

    Path(output).mkdir(parents=True, exist_ok=True)
    port = Task036LocalTranscriptionPort(
        FasterWhisperProvider(
            FasterWhisperConfig(model="small", device="cpu", compute_type="int8", allow_model_download=False),
            model_factory=model_factory,
        ),
        Path(output), store, job_id, language="ja",
    )
    try:
        barrier.wait(10)
        port.transcribe_local_media(
            project_id=PROJECT_ID, source_path=Path(source), source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
        )
        queue.put("COMPLETED")
    except ProductError as exc:
        queue.put(exc.code)
    finally:
        store.close()


def test_v2_success_is_fake_only_and_public_projection_excludes_private_paths(tmp_path: Path) -> None:
    private_model = tmp_path / "private-model-name"
    private_cache = tmp_path / "private-cache-name"
    settings = FasterWhisperProviderSettingsV2(model=str(private_model), cache_directory=private_cache)
    port, _store, probe, configs = make_port(tmp_path, settings=settings)
    source, digest = source_file(tmp_path)

    outcome = execute(port, source, digest)

    assert isinstance(outcome, RuntimeManagedLocalTranscriptionOutcomeV2)
    assert outcome.provider_execution_started is True
    assert outcome.recovered_from_durable_result is False
    assert probe.calls == [("cpu", "int8")]
    assert configs[0].allow_model_download is False
    assert configs[0].device == "cpu"
    assert configs[0].compute_type == "int8"
    public = json.dumps(outcome.runtime_request_public, ensure_ascii=False)
    assert str(private_model) not in public
    assert str(private_cache) not in public

    publication = port.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    body = publication.read_text(encoding="utf-8")
    assert str(private_model) not in body
    assert str(private_cache) not in body
    assert '"model_download_authorized": false' in body

    capture = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert capture.recovery_state == "VERIFICATION_ONLY"
    assert capture.public_projection()["phase"] == "COMPLETED"
    assert capture.public_projection()["available_action"] == "NONE"


def test_v2_success_observes_closed_phases_and_barrier_before_first_generation(tmp_path: Path) -> None:
    phases: list[str] = []
    lifecycle: list[str] = []
    generation_absence: list[bool] = []
    holder: dict[str, object] = {}

    def observe_lifecycle(value: str) -> None:
        lifecycle.append(value)
        if value == "AFTER_PUBLICATION_BARRIER":
            port = holder["port"]
            assert isinstance(port, Task036RuntimeManagedLocalTranscriptionPortV2)
            generation_absence.append(not (port.output_directory / ".task036-publications").exists())

    port, store, _probe, _configs = make_port(
        tmp_path, phase_observer=phases.append, lifecycle_observer=observe_lifecycle,
    )
    holder["port"] = port
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)

    assert phases == [
        "ADMISSION", "PROVIDER_STARTING", "PROVIDER_RUNNING",
        "PUBLICATION_VALIDATING", "PUBLICATION_COMMITTING", "COMPLETED",
    ]
    assert lifecycle == [
        "AFTER_PUBLICATION_BARRIER", "AFTER_IMMUTABLE_WRITE",
        "AFTER_MAIN_PUBLICATION_CAS", "AFTER_CONTROL_PUBLICATION_COMPLETION",
        "AFTER_FIXED_PROMOTION", "AFTER_MAIN_COMPLETION",
    ]
    assert generation_absence == [True]
    control = store.find_operation(
        port.production_job_id,
        derive_control_key(
            production_job_id=port.production_job_id,
            project_id=PROJECT_ID,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
            runtime_operation_id=outcome.operation_id,
        ),
    )
    assert control is not None and control.status == "COMPLETED"
    assert control.result_ref.startswith("task098-runtime-commit-barrier:v1:")
    assert outcome.publication_set_sha256.startswith("sha256:")


def test_v2_cancel_at_admission_closes_before_provider_factory_and_writes_no_generation(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {}

    def observe_phase(value: str) -> None:
        if value == "ADMISSION":
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])

    port, store, _probe, configs = make_port(tmp_path, phase_observer=observe_phase)
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert exc.value.details == {}
    assert configs == []
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "FAILED"
    assert not (port.output_directory / ".task036-publications").exists()


def test_r2c_capture_and_apply_request_cancel_use_exact_live_coordinate(
    tmp_path: Path,
) -> None:
    holder: dict[str, object] = {}
    captured = []

    def observe_phase(value: str) -> None:
        if value != "ADMISSION":
            return
        port = holder["port"]
        assert isinstance(port, Task036RuntimeManagedLocalTranscriptionPortV2)
        snapshot = port.capture_runtime_transcription_control(
            project_id=PROJECT_ID,
            source_asset_id=ASSET_ID,
            source_asset_sha256=holder["digest"],
        )
        assert snapshot.public_projection()["available_action"] == "REQUEST_CANCEL"
        captured.append(snapshot)
        result = port.apply_runtime_transcription_control(
            snapshot,
            action="REQUEST_CANCEL",
            project_id=PROJECT_ID,
            source_asset_id=ASSET_ID,
            source_asset_sha256=holder["digest"],
        )
        assert result["cancel_state"] == "CANCEL_REQUESTED"
        assert result["available_action"] == "NONE"

    port, store, _probe, configs = make_port(tmp_path, phase_observer=observe_phase)
    source, digest = source_file(tmp_path)
    holder.update(port=port, digest=digest)
    with pytest.raises(ProductError) as cancelled:
        execute(port, source, digest)
    assert cancelled.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert configs == []
    assert len(captured) == 1
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "FAILED"
    assert port._runtime_active_worker_coordinate is None
    assert port._runtime_phase_coordinate is None


@pytest.mark.parametrize(
    ("cancel_phase", "expected_factory_calls", "expected_code", "expected_status"),
    [
        ("PROVIDER_STARTING", 0, "ERR_TASK098_RUNTIME_CANCELLED", "FAILED"),
        (
            "PROVIDER_RUNNING", 1,
            "ERR_TASK098_RUNTIME_STOP_NOT_CONFIRMED", "IN_PROGRESS",
        ),
    ],
)
def test_v2_phase_boundary_cancel_is_rechecked_before_next_provider_effect(
    tmp_path: Path, cancel_phase: str, expected_factory_calls: int,
    expected_code: str, expected_status: str,
) -> None:
    holder: dict[str, object] = {}
    model_calls: list[str] = []

    class CountingModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            model_calls.append("transcribe")
            return super().transcribe(source, **kwargs)

    def provider_factory(config: FasterWhisperConfig):
        return FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: CountingModel(),
        )

    def observe_phase(value: str) -> None:
        if value == cancel_phase:
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])

    port, store, _probe, configs = make_port(
        tmp_path, provider_factory=provider_factory, phase_observer=observe_phase,
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == expected_code
    assert len(configs) == expected_factory_calls
    assert model_calls == []
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == expected_status
    slot = store.find_operation(
        port.production_job_id,
        derive_output_slot_key(production_job_id=port.production_job_id, project_id=PROJECT_ID),
    )
    assert slot is not None
    assert slot.status == ("PENDING" if expected_status == "FAILED" else "IN_PROGRESS")
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_missing_iterator_close_binds_stop_not_confirmed_and_retains_slot(tmp_path: Path) -> None:
    holder: dict[str, object] = {}

    class CancelBeforeFirstPullModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
            return [SimpleNamespace(start=0.0, end=1.0, text="unused", words=[])], SimpleNamespace(language="ja")

    def provider_factory(config: FasterWhisperConfig):
        return FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: CancelBeforeFirstPullModel(),
        )

    port, store, _probe, _configs = make_port(
        tmp_path, provider_factory=provider_factory,
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_STOP_NOT_CONFIRMED"
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    slot = store.find_operation(
        port.production_job_id,
        derive_output_slot_key(production_job_id=port.production_job_id, project_id=PROJECT_ID),
    )
    assert operation is not None and operation.status == "IN_PROGRESS"
    assert operation.result_ref.startswith("task098-runtime-admission:v2:")
    assert slot is not None and (slot.status, slot.result_ref) == ("IN_PROGRESS", operation.operation_id)
    assert not (port.output_directory / ".task036-publications").exists()


@pytest.mark.parametrize("close_throws", [False, True])
def test_v2_exact_iterator_close_controls_terminal_cancellation(
    tmp_path: Path, close_throws: bool,
) -> None:
    holder: dict[str, object] = {}
    close_calls: list[str] = []
    pull_calls: list[str] = []

    class ControlledIterator:
        def __iter__(self):
            return self

        def __next__(self):
            pull_calls.append("next")
            raise StopIteration

        def close(self):
            close_calls.append("close")
            if close_throws:
                raise RuntimeError("synthetic close failure")

    class ControlledModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
            return ControlledIterator(), SimpleNamespace(language="ja")

    def provider_factory(config: FasterWhisperConfig):
        return FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: ControlledModel(),
        )

    port, store, _probe, _configs = make_port(
        tmp_path, provider_factory=provider_factory,
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == (
        "ERR_TASK098_RUNTIME_STOP_NOT_CONFIRMED"
        if close_throws else "ERR_TASK098_RUNTIME_CANCELLED"
    )
    assert close_calls == ["close"]
    assert pull_calls == []
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None
    assert operation.status == ("IN_PROGRESS" if close_throws else "FAILED")
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_cancel_after_one_segment_closes_before_later_pull(tmp_path: Path) -> None:
    holder: dict[str, object] = {}
    close_calls: list[str] = []
    next_calls: list[str] = []

    class CancelAfterFirstIterator:
        def __init__(self) -> None:
            self.done = False

        def __iter__(self):
            return self

        def __next__(self):
            next_calls.append("next")
            if self.done:
                raise AssertionError("a later segment pull must not occur")
            self.done = True
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
            return SimpleNamespace(start=0.0, end=1.0, text="first", words=[])

        def close(self):
            close_calls.append("close")

    class CancelAfterFirstModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            return CancelAfterFirstIterator(), SimpleNamespace(language="ja")

    def provider_factory(config: FasterWhisperConfig):
        return FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: CancelAfterFirstModel(),
        )

    port, store, _probe, _configs = make_port(
        tmp_path, provider_factory=provider_factory,
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert next_calls == ["next"]
    assert close_calls == ["close"]
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "FAILED"
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_cancel_observed_immediately_after_provider_return_writes_nothing(tmp_path: Path) -> None:
    holder: dict[str, object] = {}

    class RequestOnExhaustion:
        def __iter__(self):
            return self

        def __next__(self):
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
            raise StopIteration

        def close(self):
            raise AssertionError("synchronous Provider return does not require iterator close")

    class ExhaustingModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            return RequestOnExhaustion(), SimpleNamespace(language="ja")

    port, store, _probe, _configs = make_port(
        tmp_path,
        provider_factory=lambda config: FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: ExhaustingModel(),
        ),
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_cancel_after_temporary_validation_wins_before_publication_barrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict[str, object] = {}
    original = _Task036LocalTranscriptionOperationEngine._validate_publication
    requested = False

    def validate_then_request(self, *args, **kwargs):
        nonlocal requested
        result = original(self, *args, **kwargs)
        if not requested:
            requested = True
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
        return result

    monkeypatch.setattr(
        _Task036LocalTranscriptionOperationEngine, "_validate_publication",
        validate_then_request,
    )
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert requested is True
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_final_barrier_cas_loser_uses_cancel_path_and_old_writer_stays_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_acquire = RuntimeTranscriptionCoordinatorV1.acquire_publication_barrier
    writer_calls: list[str] = []

    def request_then_acquire(self, coordinates, writer, **kwargs):
        self.request_cancel(coordinates)
        return original_acquire(self, coordinates, writer, **kwargs)

    original_store = Task036RuntimeManagedLocalTranscriptionPortV2._store_v2_publication_set

    def counted_store(self, *args, **kwargs):
        writer_calls.append("write")
        return original_store(self, *args, **kwargs)

    monkeypatch.setattr(
        RuntimeTranscriptionCoordinatorV1, "acquire_publication_barrier",
        request_then_acquire,
    )
    monkeypatch.setattr(
        Task036RuntimeManagedLocalTranscriptionPortV2,
        "_store_v2_publication_set", counted_store,
    )
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK098_RUNTIME_CANCELLED"
    assert writer_calls == []
    assert not (port.output_directory / ".task036-publications").exists()


def test_v2_provider_zero_recovery_completes_open_publication_control_before_promotion(
    tmp_path: Path,
) -> None:
    def crash_after_main_bind(value: str) -> None:
        if value == "AFTER_MAIN_PUBLICATION_CAS":
            raise RuntimeError("synthetic crash after main publication bind")

    port, store, _probe, _configs = make_port(
        tmp_path, lifecycle_observer=crash_after_main_bind,
    )
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN"
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "PARTIAL"
    control = store.find_operation(
        port.production_job_id,
        derive_control_key(
            production_job_id=port.production_job_id,
            project_id=PROJECT_ID,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
            runtime_operation_id=operation.operation_id,
        ),
    )
    assert control is not None and control.status == "IN_PROGRESS"
    assert not (port.output_directory / "transcript.json").exists()

    provider_calls: list[str] = []
    recovered_port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=port.settings,
        runtime_request=port.runtime_request,
        capability_probe=Probe(True),
        provider_factory=lambda _config: provider_calls.append("provider"),  # type: ignore[arg-type,return-value]
        clock=port.clock,
        output_directory=port.output_directory,
        store=store,
        production_job_id=port.production_job_id,
        language=port.language,
    )
    recovered = recovered_port.recover_local_media(
        project_id=PROJECT_ID, source_path=source,
        source_asset_id=ASSET_ID, source_asset_sha256=digest,
    )
    assert provider_calls == []
    assert recovered.recovered_from_durable_result is True
    assert store.get_operation(operation.operation_id).status == "COMPLETED"
    assert store.get_operation(control.operation_id).status == "COMPLETED"
    assert (port.output_directory / "transcript.json").is_file()


@pytest.mark.parametrize(
    ("event", "drift"),
    [
        ("AFTER_CONTROL_PUBLICATION_COMPLETION", "lease"),
        ("AFTER_CONTROL_PUBLICATION_COMPLETION", "main-attempt"),
        ("AFTER_CONTROL_PUBLICATION_COMPLETION", "control"),
        ("AFTER_CONTROL_PUBLICATION_COMPLETION", "slot"),
        ("AFTER_FIXED_PROMOTION", "slot"),
    ],
)
def test_v2_publication_revalidates_exact_rows_after_observable_boundaries(
    tmp_path: Path, event: str, drift: str,
) -> None:
    holder: dict[str, object] = {}
    mutated = False

    def observe_lifecycle(value: str) -> None:
        nonlocal mutated
        if value != event or mutated:
            return
        mutated = True
        port = holder["port"]
        store = holder["store"]
        digest = holder["digest"]
        assert isinstance(port, Task036RuntimeManagedLocalTranscriptionPortV2)
        assert isinstance(store, SQLiteProductStore)
        operation = store.find_operation(
            port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
        )
        slot = store.find_operation(
            port.production_job_id,
            derive_output_slot_key(
                production_job_id=port.production_job_id, project_id=PROJECT_ID,
            ),
        )
        assert operation is not None and slot is not None
        if drift == "lease":
            key = derive_cross_version_guard_key(
                project_id=PROJECT_ID, source_asset_id=ASSET_ID,
                source_asset_sha256=digest,
            )
            row = store.find_operation(port.production_job_id, key)
            assert row is not None
            _changed_row, changed = store.compare_and_set_operation_status(
                row.operation_id,
                expected_statuses=("IN_PROGRESS",),
                expected_result_refs=(row.result_ref,),
                expected_attempt=row.attempt,
                status="PARTIAL",
                result_ref=row.result_ref,
                replace_result_ref=True,
            )
        elif drift == "main-attempt":
            _changed_row, changed = store.compare_and_set_operation_status(
                operation.operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(operation.result_ref,),
                expected_attempt=operation.attempt,
                status="PARTIAL",
                result_ref=operation.result_ref,
                replace_result_ref=True,
                increment_attempt=True,
            )
        elif drift == "control":
            key = derive_control_key(
                production_job_id=port.production_job_id,
                project_id=PROJECT_ID,
                source_asset_id=ASSET_ID,
                source_asset_sha256=digest,
                runtime_operation_id=operation.operation_id,
            )
            row = store.find_operation(port.production_job_id, key)
            assert row is not None
            _changed_row, changed = store.compare_and_set_operation_status(
                row.operation_id,
                expected_statuses=("COMPLETED",),
                expected_result_refs=(row.result_ref,),
                expected_attempt=0,
                status="FAILED",
                result_ref=row.result_ref,
                replace_result_ref=True,
            )
        else:
            _changed_row, changed = store.compare_and_set_operation_status(
                slot.operation_id,
                expected_statuses=("IN_PROGRESS",),
                expected_result_refs=(operation.operation_id,),
                expected_attempt=slot.attempt,
                status="PENDING",
                result_ref=operation.operation_id,
                replace_result_ref=True,
            )
        assert changed

    port, store, _probe, _configs = make_port(
        tmp_path, lifecycle_observer=observe_lifecycle,
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    assert mutated is True
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status != "COMPLETED"
    fixed = port.output_directory / "transcript.json"
    assert fixed.exists() is (event == "AFTER_FIXED_PROMOTION")


@pytest.mark.parametrize(
    "crash_event",
    [
        "AFTER_IMMUTABLE_WRITE",
        "AFTER_CONTROL_PUBLICATION_COMPLETION",
        "AFTER_FIXED_PROMOTION",
        "AFTER_MAIN_COMPLETION",
    ],
)
def test_v2_crash_matrix_is_provider_zero_and_preserves_exact_durable_boundary(
    tmp_path: Path, crash_event: str,
) -> None:
    def crash(value: str) -> None:
        if value == crash_event:
            raise RuntimeError("synthetic lifecycle crash")

    port, store, _probe, _configs = make_port(tmp_path, lifecycle_observer=crash)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN"
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None
    expected_status = "IN_PROGRESS" if crash_event == "AFTER_IMMUTABLE_WRITE" else (
        "COMPLETED" if crash_event == "AFTER_MAIN_COMPLETION" else "PARTIAL"
    )
    assert operation.status == expected_status
    slot = store.find_operation(
        port.production_job_id,
        derive_output_slot_key(production_job_id=port.production_job_id, project_id=PROJECT_ID),
    )
    assert slot is not None and (slot.status, slot.result_ref) == (
        "IN_PROGRESS", operation.operation_id,
    )
    generation = port.output_directory / ".task036-publications" / operation.operation_id
    immutable_before = {
        path.name: path.read_bytes() for path in generation.iterdir() if path.is_file()
    }
    fixed_names = ("transcript.json", "subtitles.srt", "transcription-report.json")
    fixed_before = {
        name: (port.output_directory / name).read_bytes()
        for name in fixed_names if (port.output_directory / name).is_file()
    }
    provider_calls: list[str] = []
    recovered_port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=port.settings,
        runtime_request=port.runtime_request,
        capability_probe=Probe(True),
        provider_factory=lambda _config: provider_calls.append("provider"),  # type: ignore[arg-type,return-value]
        clock=port.clock,
        output_directory=port.output_directory,
        store=store,
        production_job_id=port.production_job_id,
        language=port.language,
    )
    if crash_event == "AFTER_IMMUTABLE_WRITE":
        with pytest.raises(ProductError) as rejected:
            recovered_port.recover_local_media(
                project_id=PROJECT_ID, source_path=source,
                source_asset_id=ASSET_ID, source_asset_sha256=digest,
            )
        assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE"
        assert recovered_port.recovery_state(
            project_id=PROJECT_ID, source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
        ) == "CORRUPT_BLOCKED"
    else:
        recovered = recovered_port.recover_local_media(
            project_id=PROJECT_ID, source_path=source,
            source_asset_id=ASSET_ID, source_asset_sha256=digest,
        )
        assert recovered.recovered_from_durable_result is True
        assert store.get_operation(operation.operation_id).status == "COMPLETED"
    assert provider_calls == []
    assert {
        path.name: path.read_bytes() for path in generation.iterdir() if path.is_file()
    } == immutable_before
    if fixed_before:
        assert {
            name: (port.output_directory / name).read_bytes() for name in fixed_names
        } == fixed_before


def test_v2_recovery_rejects_attempt_aba_before_terminal_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(value: str) -> None:
        if value == "AFTER_MAIN_PUBLICATION_CAS":
            raise RuntimeError("synthetic crash")

    port, store, _probe, _configs = make_port(tmp_path, lifecycle_observer=crash)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "PARTIAL"
    admitted_attempt = operation.attempt
    original_promote = _Task036LocalTranscriptionOperationEngine._promote_publication
    drifted = False

    def promote_then_drift(self, *args, **kwargs):
        nonlocal drifted
        result = original_promote(self, *args, **kwargs)
        if not drifted:
            drifted = True
            current = store.get_operation(operation.operation_id)
            _row, changed = store.compare_and_set_operation_status(
                current.operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(current.result_ref,),
                expected_attempt=current.attempt,
                status="PARTIAL",
                result_ref=current.result_ref,
                replace_result_ref=True,
                increment_attempt=True,
            )
            assert changed
        return result

    monkeypatch.setattr(
        _Task036LocalTranscriptionOperationEngine, "_promote_publication",
        promote_then_drift,
    )
    provider_calls: list[str] = []
    recovered_port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=port.settings,
        runtime_request=port.runtime_request,
        capability_probe=Probe(True),
        provider_factory=lambda _config: provider_calls.append("provider"),  # type: ignore[arg-type,return-value]
        clock=port.clock,
        output_directory=port.output_directory,
        store=store,
        production_job_id=port.production_job_id,
        language=port.language,
    )
    with pytest.raises(ProductError) as rejected:
        recovered_port.recover_local_media(
            project_id=PROJECT_ID, source_path=source,
            source_asset_id=ASSET_ID, source_asset_sha256=digest,
        )
    assert rejected.value.code == "ERR_TASK098_CONTROL_CONFLICT"
    assert provider_calls == []
    current = store.get_operation(operation.operation_id)
    assert (current.status, current.attempt) == ("PARTIAL", admitted_attempt + 1)


def test_v2_recovery_does_not_accept_completed_cas_loser_from_another_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(value: str) -> None:
        if value == "AFTER_MAIN_PUBLICATION_CAS":
            raise RuntimeError("synthetic crash")

    port, store, _probe, _configs = make_port(tmp_path, lifecycle_observer=crash)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "PARTIAL"
    original_compare = SQLiteProductStore.compare_and_set_operation_status
    collided = False

    def complete_from_new_attempt(self, operation_id, **kwargs):
        nonlocal collided
        if (
            operation_id == operation.operation_id
            and kwargs.get("status") == "COMPLETED"
            and not collided
        ):
            collided = True
            current = self.get_operation(operation_id)
            winner, changed = original_compare(
                self,
                operation_id,
                expected_statuses=("PARTIAL",),
                expected_result_refs=(current.result_ref,),
                expected_attempt=current.attempt,
                status="COMPLETED",
                result_ref=current.result_ref,
                replace_result_ref=True,
                increment_attempt=True,
            )
            assert changed and winner.attempt == current.attempt + 1
            return winner, False
        return original_compare(self, operation_id, **kwargs)

    monkeypatch.setattr(
        SQLiteProductStore, "compare_and_set_operation_status", complete_from_new_attempt,
    )
    provider_calls: list[str] = []
    recovered_port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=port.settings,
        runtime_request=port.runtime_request,
        capability_probe=Probe(True),
        provider_factory=lambda _config: provider_calls.append("provider"),  # type: ignore[arg-type,return-value]
        clock=port.clock,
        output_directory=port.output_directory,
        store=store,
        production_job_id=port.production_job_id,
        language=port.language,
    )
    with pytest.raises(ProductError) as rejected:
        recovered_port.recover_local_media(
            project_id=PROJECT_ID, source_path=source,
            source_asset_id=ASSET_ID, source_asset_sha256=digest,
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    assert collided is True
    assert provider_calls == []
    current = store.get_operation(operation.operation_id)
    assert (current.status, current.attempt) == ("COMPLETED", operation.attempt + 1)


@pytest.mark.parametrize(
    "replacement_ref",
    [
        "task098-runtime-cancel-outcome:v1:short",
        "task098-runtime-cancel-outcome:v1:" + "f" * 64,
    ],
)
def test_v2_recovery_state_rejects_malformed_or_unbound_active_control(
    tmp_path: Path, replacement_ref: str,
) -> None:
    holder: dict[str, object] = {}

    class CancelModel(FakeModel):
        def transcribe(self, source: str, **kwargs):
            request_runtime_cancel(holder["port"], holder["store"], holder["digest"])
            return [SimpleNamespace(start=0.0, end=1.0, text="unused", words=[])], SimpleNamespace(language="ja")

    port, store, _probe, _configs = make_port(
        tmp_path,
        provider_factory=lambda config: FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: CancelModel(),
        ),
    )
    source, digest = source_file(tmp_path)
    holder.update(port=port, store=store, digest=digest)
    with pytest.raises(ProductError) as stopped:
        execute(port, source, digest)
    assert stopped.value.code == "ERR_TASK098_RUNTIME_STOP_NOT_CONFIRMED"
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None
    control = store.find_operation(
        port.production_job_id,
        derive_control_key(
            production_job_id=port.production_job_id,
            project_id=PROJECT_ID,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
            runtime_operation_id=operation.operation_id,
        ),
    )
    assert control is not None
    _row, changed = store.compare_and_set_operation_status(
        control.operation_id,
        expected_statuses=("IN_PROGRESS",),
        expected_result_refs=(control.result_ref,),
        expected_attempt=0,
        status="IN_PROGRESS",
        result_ref=replacement_ref,
        replace_result_ref=True,
    )
    assert changed
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    ) == "CORRUPT_BLOCKED"


def test_v2_bound_publication_recovers_and_finalize_releases_fixed_slot(tmp_path: Path) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    first = execute(port, source, digest)
    assert first.operation_id and first.slot_operation_id and first.publication_set_sha256
    fixed_bytes_before_recovery = {
        name: (port.output_directory / name).read_bytes()
        for name in ("transcript.json", "subtitles.srt", "transcription-report.json")
    }
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == "VERIFICATION_ONLY"

    recovered = port.recover_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert recovered.provider_execution_started is False
    assert recovered.recovered_from_durable_result is True
    assert recovered.publication_set_sha256 == first.publication_set_sha256
    port.finalize_local_media_binding(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
        transcript_manifest_sha256=recovered.transcript.to_dict()["manifest_sha256"],
        operation_id=recovered.operation_id,
        slot_operation_id=recovered.slot_operation_id,
        publication_set_sha256=recovered.publication_set_sha256,
    )
    slot = store.get_operation(recovered.slot_operation_id)
    assert slot.status == "PENDING"
    assert slot.result_ref == recovered.operation_id
    assert fixed_bytes_before_recovery == {
        name: (port.output_directory / name).read_bytes()
        for name in fixed_bytes_before_recovery
    }


@pytest.mark.parametrize("control_drift", ["missing", "foreign"])
def test_v2_verification_only_requires_exact_publication_control(
    tmp_path: Path, control_drift: str,
) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.operation_id and outcome.slot_operation_id
    control_key = derive_control_key(
        production_job_id=port.production_job_id,
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
        runtime_operation_id=outcome.operation_id,
    )
    control = store.find_operation(port.production_job_id, control_key)
    assert control is not None and control.status == "COMPLETED"
    with sqlite3.connect(store.path) as connection:
        if control_drift == "missing":
            connection.execute(
                "DELETE FROM operations WHERE operation_id=?", (control.operation_id,),
            )
        else:
            connection.execute(
                "UPDATE operations SET command_type=? WHERE operation_id=?",
                ("foreign.publication.control", control.operation_id),
            )
    fixed_before = {
        name: (port.output_directory / name).read_bytes()
        for name in ("transcript.json", "subtitles.srt", "transcription-report.json")
    }
    provider_calls: list[str] = []
    recovered_port = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=port.settings,
        runtime_request=port.runtime_request,
        capability_probe=Probe(True),
        provider_factory=lambda _config: provider_calls.append("provider"),  # type: ignore[arg-type,return-value]
        clock=port.clock,
        output_directory=port.output_directory,
        store=store,
        production_job_id=port.production_job_id,
        language=port.language,
    )
    with pytest.raises(ProductError) as rejected:
        recovered_port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
        )
    assert rejected.value.code == "ERR_TASK098_CONTROL_CONFLICT"
    assert provider_calls == []
    slot = store.get_operation(outcome.slot_operation_id)
    assert (slot.status, slot.result_ref) == ("IN_PROGRESS", outcome.operation_id)
    assert fixed_before == {
        name: (port.output_directory / name).read_bytes() for name in fixed_before
    }


def test_v2_same_version_different_config_continues_after_exact_finalize(tmp_path: Path) -> None:
    first, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(first, source, digest)
    assert outcome.operation_id and outcome.slot_operation_id and outcome.publication_set_sha256
    first.finalize_local_media_binding(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
        transcript_manifest_sha256=outcome.transcript.to_dict()["manifest_sha256"],
        operation_id=outcome.operation_id,
        slot_operation_id=outcome.slot_operation_id,
        publication_set_sha256=outcome.publication_set_sha256,
    )
    second = Task036RuntimeManagedLocalTranscriptionPortV2(
        settings=FasterWhisperProviderSettingsV2(model="small", beam_size=6),
        runtime_request=FasterWhisperRuntimeRequestV1.create("cpu"),
        capability_probe=Probe(True),
        provider_factory=lambda config: FasterWhisperProvider(
            config, model_factory=lambda *_args, **_kwargs: FakeModel(),
        ),
        clock=lambda: T0,
        output_directory=first.output_directory,
        store=store,
        production_job_id=first.production_job_id,
        language="ja",
    )
    continued = execute(second, source, digest)
    assert continued.provider_execution_started is True
    assert continued.operation_id != outcome.operation_id


def test_v2_outcome_projection_is_copy_immutable_and_contains_no_digest_private_fields(tmp_path: Path) -> None:
    port, _store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    request_projection = outcome.runtime_request_public
    decision_projection = outcome.runtime_decision_public
    request_projection["requested_device"] = "cuda"
    decision_projection["outcome"] = "BLOCKED"
    assert outcome.runtime_request_public["requested_device"] == "cpu"
    assert outcome.runtime_decision_public["outcome"] == "READY_CPU"
    assert "record_sha256" not in outcome.runtime_request_public
    assert "record_sha256" not in outcome.runtime_decision_public


def test_v2_provider_factory_raw_exception_is_redacted_and_durable_admission_is_partial(tmp_path: Path) -> None:
    secret = "private-factory-secret"

    def exploding_factory(_config: FasterWhisperConfig):
        raise RuntimeError(secret)

    port, store, _probe, _configs = make_port(tmp_path, provider_factory=exploding_factory)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_UNCERTAIN"
    assert secret not in str(exc.value)
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None
    assert operation.status == "PARTIAL"
    assert operation.result_ref is not None and operation.result_ref.startswith("task098-runtime-admission:v2:")
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == "ADJUDICATION_REQUIRED_NO_PUBLICATION"


def test_r2c_human_apply_builds_fixed_attestation_and_terminal_closure(tmp_path: Path) -> None:
    def exploding_factory(_config: FasterWhisperConfig):
        raise RuntimeError("synthetic disconnected provider")

    port, store, _probe, _configs = make_port(
        tmp_path, provider_factory=exploding_factory,
    )
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    prepared = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert prepared.active_worker_coordinate is None
    assert prepared.public_projection()["available_action"] == (
        "CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY"
    )
    result = port.apply_runtime_transcription_control(
        prepared,
        action="CONFIRM_PROVIDER_STOPPED_CLOSE_FAILED_NO_REPLAY",
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert result["adjudication_state"] == "CLOSED_FAILED_NO_REPLAY"
    assert result["provider_stop_confirmed"] is False
    assert result["stop_evidence"] == "HUMAN_ATTESTATION"
    assert result["slot_release_allowed"] is True
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == "FAILED"
    assert operation.result_ref.startswith("task098-runtime-adjudicated-failed:v1:")


def test_r2c_capture_keeps_uncommitted_terminal_record_blocked_until_control_commit(
    tmp_path: Path,
) -> None:
    def exploding_factory(_config: FasterWhisperConfig):
        raise RuntimeError("synthetic disconnected provider")

    port, store, _probe, _configs = make_port(
        tmp_path, provider_factory=exploding_factory,
    )
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    prepared = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    coordinates = prepared.coordinates
    assert coordinates is not None
    coordinator = RuntimeTranscriptionCoordinatorV1(
        store=store,
        output_directory=port.output_directory.resolve(strict=True),
        clock=port.clock,
    )
    decision = RuntimeTranscriptionAdjudicationDecisionV1.create(
        adjudication_id=generate_id(IdKind.OPERATION),
        runtime_operation_id=coordinates.runtime_operation_id,
        slot_operation_id=coordinates.slot_operation_id,
        source_asset_sha256=coordinates.source_asset_sha256,
        runtime_admission_ref=coordinates.runtime_admission_ref,
        runtime_request_sha256=coordinates.runtime_request.record_sha256,
        runtime_decision_sha256=coordinates.runtime_decision_sha256,
        expected_attempt=coordinates.expected_attempt,
        decided_at=coordinator._now(),
    )

    def crash(stage: str) -> None:
        if stage == "after_terminal_commit_write":
            raise RuntimeError("synthetic terminal commit crash")

    with pytest.raises(RuntimeError, match="terminal commit crash"):
        coordinator.close_human_adjudication_from_durable_coordinates(
            coordinates, decision, fault_hook=crash,
        )
    main = store.get_operation(coordinates.runtime_operation_id)
    control = store.find_operation(
        coordinates.production_job_id, coordinates.control_key,
    )
    slot = store.get_operation(coordinates.slot_operation_id)
    assert main.status == "FAILED"
    assert control is not None and control.status == "PARTIAL"
    assert slot.status == "IN_PROGRESS"

    blocked = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert blocked.control_chain_identity[-1] is not None
    assert blocked.public_projection()["phase"] == "BLOCKED"
    assert blocked.public_projection()["available_action"] == "NONE"
    assert blocked.public_projection()["slot_release_allowed"] is False

    committed = coordinator.close_human_adjudication_from_durable_coordinates(
        coordinates, decision,
    )
    assert committed.closure_kind == "HUMAN_ADJUDICATED_FAILED"
    assert store.find_operation(
        coordinates.production_job_id, coordinates.control_key,
    ).status == "COMPLETED"
    assert store.get_operation(coordinates.slot_operation_id).status == "PENDING"
    closed = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    ).public_projection()
    assert closed["adjudication_state"] == "CLOSED_FAILED_NO_REPLAY"
    assert closed["slot_release_allowed"] is True


def test_v2_crash_after_publication_barrier_before_first_write_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def crash_before_publication(*_args, **_kwargs):
        raise RuntimeError("synthetic crash")

    monkeypatch.setattr(Task036RuntimeManagedLocalTranscriptionPortV2, "_store_v2_publication_set", crash_before_publication)
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN"
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == "IN_PROGRESS"
    assert operation.result_ref is not None and operation.result_ref.startswith("task098-runtime-admission:v2:")
    assert not (port.output_directory / ".task036-publications" / operation.operation_id).exists()
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == "CORRUPT_BLOCKED"


def test_v2_promotion_failure_leaves_bound_publication_recoverable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_promotion(*_args, **_kwargs):
        raise ProductError("ERR_SYNTHETIC_PROMOTION_FAILURE", "promotion failed", ProductErrorCategory.DATA_INTEGRITY)

    monkeypatch.setattr(_Task036LocalTranscriptionOperationEngine, "_promote_publication", fail_promotion)
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert exc.value.code == "ERR_SYNTHETIC_PROMOTION_FAILURE"
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == "PARTIAL"
    assert operation.result_ref is not None and operation.result_ref.startswith("sha256:")
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == "RECOVERABLE_PUBLICATION"
    capture = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert capture.recovery_state == "RECOVERABLE_PUBLICATION"
    assert capture.public_projection()["phase"] == "PUBLICATION_COMMITTING"
    assert capture.public_projection()["available_action"] == "NONE"


@pytest.mark.parametrize("durable_state", ["PARTIAL", "COMPLETED"])
@pytest.mark.parametrize("control_drift", ["missing-row-and-evidence", "wrong-status"])
def test_r2c_publication_capture_requires_exact_publication_control_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    durable_state: str,
    control_drift: str,
) -> None:
    if durable_state == "PARTIAL":
        monkeypatch.setattr(
            _Task036LocalTranscriptionOperationEngine,
            "_promote_publication",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ProductError(
                "ERR_SYNTHETIC_PROMOTION_FAILURE", "promotion failed",
                ProductErrorCategory.DATA_INTEGRITY,
            )),
        )
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    if durable_state == "PARTIAL":
        with pytest.raises(ProductError):
            execute(port, source, digest)
    else:
        execute(port, source, digest)
    operation = store.find_operation(
        port.production_job_id,
        port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None and operation.status == durable_state
    control_key = derive_control_key(
        production_job_id=port.production_job_id,
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
        runtime_operation_id=operation.operation_id,
    )
    control = store.find_operation(port.production_job_id, control_key)
    assert control is not None
    if control_drift == "missing-row-and-evidence":
        with sqlite3.connect(store.path) as connection:
            connection.execute(
                "DELETE FROM operations WHERE operation_id=?", (control.operation_id,),
            )
        evidence = (
            port.output_directory / ".task036-runtime-control"
            / operation.operation_id
        )
        assert evidence.is_dir()
        shutil.rmtree(evidence)
    else:
        with sqlite3.connect(store.path) as connection:
            connection.execute(
                "UPDATE operations SET status='PENDING', result_ref=NULL "
                "WHERE operation_id=?",
                (control.operation_id,),
            )
    capture = port.capture_runtime_transcription_control(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert capture.recovery_state == "CORRUPT_BLOCKED"
    assert capture.public_projection() == {
        "control_mode": "PHASE_ONLY_V1",
        "phase": "BLOCKED",
        "cancel_state": "STOP_NOT_CONFIRMED",
        "adjudication_state": "NOT_REQUIRED",
        "available_action": "NONE",
        "status_label": "状態が不正なため操作できません",
        "provider_execution_started": False,
        "provider_execution_known": False,
        "provider_stop_confirmed": False,
        "stop_evidence": "NONE",
        "slot_release_allowed": False,
        "no_replay": True,
    }


def test_v2_bound_partial_rolls_forward_with_zero_provider_reentry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = _Task036LocalTranscriptionOperationEngine._promote_publication
    failed = False

    def fail_once(self, *args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise ProductError(
                "ERR_SYNTHETIC_PROMOTION_FAILURE", "promotion failed",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return original(self, *args, **kwargs)

    monkeypatch.setattr(_Task036LocalTranscriptionOperationEngine, "_promote_publication", fail_once)
    port, _store, probe, configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    assert len(configs) == 1
    probe_calls = list(probe.calls)
    recovered = port.recover_local_media(
        project_id=PROJECT_ID, source_path=source, source_asset_id=ASSET_ID,
        source_asset_sha256=digest,
    )
    assert recovered.recovered_from_durable_result is True
    assert len(configs) == 1
    assert probe.calls == probe_calls


def test_v2_recovery_completion_collision_is_idempotent_and_keeps_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_promote = _Task036LocalTranscriptionOperationEngine._promote_publication
    failed = False

    def fail_once(self, *args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise ProductError("ERR_SYNTHETIC_PROMOTION_FAILURE", "promotion failed", ProductErrorCategory.DATA_INTEGRITY)
        return original_promote(self, *args, **kwargs)

    monkeypatch.setattr(_Task036LocalTranscriptionOperationEngine, "_promote_publication", fail_once)
    port, store, _probe, configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError):
        execute(port, source, digest)
    monkeypatch.setattr(_Task036LocalTranscriptionOperationEngine, "_promote_publication", original_promote)
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == "PARTIAL" and operation.result_ref
    fixed_before = {
        name: (port.output_directory / name).read_bytes()
        for name in ("transcript.json", "subtitles.srt", "transcription-report.json")
        if (port.output_directory / name).exists()
    }
    original_cas = SQLiteProductStore.compare_and_set_operation_status

    def report_completion_collision(self, operation_id, **kwargs):
        if kwargs.get("status") == "COMPLETED":
            row, changed = original_cas(self, operation_id, **kwargs)
            assert changed is True
            return row, False
        return original_cas(self, operation_id, **kwargs)

    monkeypatch.setattr(SQLiteProductStore, "compare_and_set_operation_status", report_completion_collision)
    recovered = port.recover_local_media(
        project_id=PROJECT_ID, source_path=source,
        source_asset_id=ASSET_ID, source_asset_sha256=digest,
    )
    assert recovered.recovered_from_durable_result is True
    assert len(configs) == 1
    completed = store.get_operation(operation.operation_id)
    assert completed.status == "COMPLETED" and completed.result_ref == operation.result_ref
    slot = store.get_operation(recovered.slot_operation_id)
    assert slot.status == "IN_PROGRESS" and slot.result_ref == operation.operation_id
    assert fixed_before == {
        name: (port.output_directory / name).read_bytes()
        for name in fixed_before
    }


def _v2_operation_snapshot(port, store, operation_id: str, digest: str) -> tuple[object, tuple[object, ...], dict[str, bytes]]:
    operation = store.get_operation(operation_id)
    lease = store.find_operation(
        port.production_job_id,
        port._engine()._cross_version_guard_key(PROJECT_ID, ASSET_ID, digest),
    )
    rows = store.list_operations_by_command_prefix(
        port.production_job_id, command_type_prefix="task036.local_transcription", limit=256,
    )
    fixed = {
        name: (port.output_directory / name).read_bytes()
        for name in ("transcript.json", "subtitles.srt", "transcription-report.json")
        if (port.output_directory / name).exists()
    }
    return operation, rows, {**fixed, "__lease__": repr(lease).encode("utf-8")}


def _mutate_v2_lease(port, store, digest: str, mode: str) -> None:
    key = port._engine()._cross_version_guard_key(PROJECT_ID, ASSET_ID, digest)
    lease = store.find_operation(port.production_job_id, key)
    if mode == "missing":
        with sqlite3.connect(store.path) as connection:
            connection.execute("DELETE FROM operations WHERE job_id=? AND idempotency_key=?", (port.production_job_id, key))
        return
    assert lease is not None
    if mode == "pending":
        changed, ok = store.compare_and_set_operation_status(
            lease.operation_id, expected_statuses=("IN_PROGRESS",), status="PENDING",
            expected_result_refs=(lease.result_ref,), result_ref=None, replace_result_ref=True,
        )
        assert ok and changed.status == "PENDING" and changed.result_ref is None
    elif mode == "wrong-version":
        with sqlite3.connect(store.path) as connection:
            connection.execute("UPDATE operations SET command_type=? WHERE operation_id=?", ("task036.local_transcription", lease.operation_id))
    elif mode == "malformed":
        changed, ok = store.compare_and_set_operation_status(
            lease.operation_id, expected_statuses=("IN_PROGRESS",), status="IN_PROGRESS",
            expected_result_refs=(lease.result_ref,), result_ref="malformed-lease", replace_result_ref=True,
        )
        assert ok and changed.result_ref == "malformed-lease"
    elif mode == "positive-attempt":
        changed, ok = store.compare_and_set_operation_status(
            lease.operation_id, expected_statuses=("IN_PROGRESS",), status="IN_PROGRESS",
            expected_result_refs=(lease.result_ref,), result_ref=lease.result_ref,
            replace_result_ref=True, increment_attempt=True,
        )
        assert ok and changed.attempt == 1
    else:
        raise AssertionError(mode)


@pytest.mark.parametrize("durable_state", ["PARTIAL", "COMPLETED"])
@pytest.mark.parametrize("lease_mode", ["missing", "pending", "wrong-version", "malformed", "positive-attempt"])
def test_v2_direct_recovery_invalid_lease_is_zero_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, durable_state: str, lease_mode: str,
) -> None:
    port, store, probe, configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    if durable_state == "PARTIAL":
        original = _Task036LocalTranscriptionOperationEngine._promote_publication
        monkeypatch.setattr(
            _Task036LocalTranscriptionOperationEngine, "_promote_publication",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ProductError(
                "ERR_SYNTHETIC_PROMOTION_FAILURE", "promotion failed", ProductErrorCategory.DATA_INTEGRITY,
            )),
        )
        with pytest.raises(ProductError):
            execute(port, source, digest)
        monkeypatch.setattr(_Task036LocalTranscriptionOperationEngine, "_promote_publication", original)
    else:
        first = execute(port, source, digest)
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == durable_state
    operation_id = operation.operation_id
    before = _v2_operation_snapshot(port, store, operation_id, digest)
    immutable_before = {
        path.name: path.read_bytes()
        for path in (port.output_directory / ".task036-publications" / operation_id).iterdir()
        if path.is_file()
    }
    _mutate_v2_lease(port, store, digest, lease_mode)
    after_mutation = _v2_operation_snapshot(port, store, operation_id, digest)
    probe_before = list(probe.calls)
    configs_before = list(configs)
    with pytest.raises(ProductError) as rejected:
        port.recover_local_media(
            project_id=PROJECT_ID, source_path=source,
            source_asset_id=ASSET_ID, source_asset_sha256=digest,
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE"
    after = _v2_operation_snapshot(port, store, operation_id, digest)
    assert after == after_mutation
    assert after[0] == before[0]
    assert after[2] == after_mutation[2]
    assert {
        path.name: path.read_bytes()
        for path in (port.output_directory / ".task036-publications" / operation_id).iterdir()
        if path.is_file()
    } == immutable_before
    assert configs == configs_before
    assert probe.calls == probe_before


@pytest.mark.parametrize("lease_mode", ["missing", "pending", "wrong-version", "malformed", "positive-attempt"])
def test_v2_finalize_invalid_lease_keeps_slot_held(tmp_path: Path, lease_mode: str) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.operation_id and outcome.slot_operation_id and outcome.publication_set_sha256
    _mutate_v2_lease(port, store, digest, lease_mode)
    before = store.get_operation(outcome.slot_operation_id)
    with pytest.raises(ProductError) as rejected:
        port.finalize_local_media_binding(
            project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
            transcript_manifest_sha256=outcome.transcript.to_dict()["manifest_sha256"],
            operation_id=outcome.operation_id, slot_operation_id=outcome.slot_operation_id,
            publication_set_sha256=outcome.publication_set_sha256,
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_OPERATION_INVALID"
    assert store.get_operation(outcome.slot_operation_id) == before


def test_v2_publication_bind_cas_failure_does_not_fabricate_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_compare = SQLiteProductStore.compare_and_set_operation_status
    failed_once = False

    def fail_publication_bind(self, operation_id, **kwargs):
        nonlocal failed_once
        if (
            kwargs.get("status") == "PARTIAL"
            and isinstance(kwargs.get("result_ref"), str)
            and kwargs["result_ref"].startswith("sha256:")
            and not failed_once
        ):
            failed_once = True
            return self.get_operation(operation_id), False
        return original_compare(self, operation_id, **kwargs)

    monkeypatch.setattr(SQLiteProductStore, "compare_and_set_operation_status", fail_publication_bind)
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)
    assert failed_once is True
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_COMPLETION_UNCERTAIN"
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == "IN_PROGRESS"
    assert operation.result_ref is not None and operation.result_ref.startswith("task098-runtime-admission:v2:")
    assert (port.output_directory / ".task036-publications" / operation.operation_id).is_dir()
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == "CORRUPT_BLOCKED"


@pytest.mark.parametrize("field", ["model", "beam_size", "vad_filter", "cache_directory"])
def test_v2_execution_and_operation_digests_bind_all_settings(tmp_path: Path, field: str) -> None:
    base = FasterWhisperProviderSettingsV2(model="small", cache_directory=tmp_path / "cache")
    changed = {
        "model": "medium",
        "beam_size": 6,
        "vad_filter": False,
        "cache_directory": tmp_path / "other-cache",
    }[field]
    first, _store, _probe, _configs = make_port(tmp_path, settings=base)
    second, _store2, _probe2, _configs2 = make_port(tmp_path / "second", settings=replace(base, **{field: changed}))
    key_a = first._operation_key(PROJECT_ID, ASSET_ID, "sha256:" + "a" * 64)
    key_b = second._operation_key(PROJECT_ID, ASSET_ID, "sha256:" + "a" * 64)
    assert key_a != key_b
    assert first._execution_identity()[2] != second._execution_identity()[2]


def test_v2_golden_key_and_execution_config_bytes_remain_unchanged(tmp_path: Path) -> None:
    port, _store, _probe, _configs = make_port(tmp_path, settings=FasterWhisperProviderSettingsV2(model="small"))
    source_sha = "sha256:" + "a" * 64
    assert port._execution_identity()[2] == "sha256:1c63c68c6dba14799755475fd6b3327339f44d460356fb627c2615d4ce603b5d"
    assert port._operation_key(PROJECT_ID, ASSET_ID, source_sha) == "task036-transcription-0d6fda3ba5e613937aa6517181c400ba9a6391493c7ff0164b78e3679a6a7441"
    provider_id, model_id, execution_sha = port._execution_identity()
    assert port._operation_key(PROJECT_ID, ASSET_ID, source_sha) == derive_runtime_operation_key_v2(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=source_sha,
        provider_id=provider_id,
        model_id=model_id,
        execution_config_sha256=execution_sha,
        runtime_request=port.runtime_request,
    )


def test_v2_cross_process_provider_entry_is_exclusive(tmp_path: Path) -> None:
    source, digest = source_file(tmp_path)
    seed = SQLiteProductStore(tmp_path / "product.sqlite3", clock=lambda: T0)
    job = seed.create_job(ProfileSnapshot.create("task098-process", "1.0.0", {}).profile_snapshot_id)
    seed.close()
    marker = tmp_path / "provider-entry.txt"
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [
        context.Process(
            target=_v2_process_worker,
            args=(str(tmp_path / "product.sqlite3"), str(tmp_path / "transcription"), job.job_id, str(source), digest, str(marker), barrier, queue),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0
    observed = sorted(queue.get(timeout=2) for _ in processes)
    assert observed[0] == "COMPLETED"
    assert observed[1] in {
        "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED",
        "ERR_TASK098_RUNTIME_ADMISSION_STALE",
    }
    assert marker.read_text(encoding="utf-8").splitlines() == ["provider-entry"]


def test_v1_v2_cross_process_version_lease_allows_only_one_provider_entry(tmp_path: Path) -> None:
    source, digest = source_file(tmp_path)
    seed = SQLiteProductStore(tmp_path / "product.sqlite3", clock=lambda: T0)
    job = seed.create_job(ProfileSnapshot.create("task098-cross-version", "1.0.0", {}).profile_snapshot_id)
    seed.close()
    marker = tmp_path / "cross-version-provider-entry.txt"
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    queue = context.Queue()
    common = (
        str(tmp_path / "product.sqlite3"), str(tmp_path / "transcription"),
        job.job_id, str(source), digest, str(marker), barrier, queue,
    )
    processes = [
        context.Process(target=_v1_process_worker, args=common),
        context.Process(target=_v2_process_worker, args=common),
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0
    observed = sorted(queue.get(timeout=2) for _ in processes)
    assert observed[0] == "COMPLETED"
    assert observed[1] in {
        "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_OWNER_EXISTS",
        "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CONFLICT",
    }
    assert marker.read_text(encoding="utf-8").splitlines() == ["provider-entry"]


def test_v2_blocked_probe_reaches_no_factory_and_leaves_unadmitted_operation(tmp_path: Path) -> None:
    probe = Probe(False)
    port, store, _probe, configs = make_port(tmp_path, probe=probe)
    source, digest = source_file(tmp_path)

    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)

    assert exc.value.code == "ERR_TASK098_RUNTIME_ADMISSION_BLOCKED"
    assert configs == []
    assert probe.calls == [("cpu", "int8")]
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None
    assert operation.status == "PENDING"
    assert operation.result_ref is None
    assert operation.attempt == 0


def test_v2_stale_cas_reaches_no_factory_and_does_not_increment_attempt(tmp_path: Path) -> None:
    port, store, _probe, configs = make_port(
        tmp_path,
        store_clock=T0 + timedelta(minutes=5),
    )
    source, digest = source_file(tmp_path)

    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)

    assert exc.value.code == "ERR_TASK098_RUNTIME_ADMISSION_STALE"
    assert configs == []
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None
    assert operation.status == "PENDING"
    assert operation.result_ref is None
    assert operation.attempt == 0


def test_v2_factory_preloaded_or_mismatched_provider_is_rejected_before_transcription(tmp_path: Path) -> None:
    calls = 0

    def foreign_factory(config: FasterWhisperConfig):
        nonlocal calls
        calls += 1
        return FasterWhisperProvider(
            replace(config, model="foreign-model"),
            model_factory=lambda *_args, **_kwargs: FakeModel(),
        )

    port, store, _probe, _configs = make_port(tmp_path, provider_factory=foreign_factory)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)

    assert calls == 1
    assert exc.value.code == "ERR_TASK098_RUNTIME_PROVIDER_INVALID"
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None
    assert operation.status == "PARTIAL"
    assert operation.result_ref is not None and operation.result_ref.startswith("task098-runtime-admission:v2:")


def test_v2_preloaded_factory_result_is_rejected_without_second_model_load(tmp_path: Path) -> None:
    model_calls = 0
    preloaded = None

    def factory(config: FasterWhisperConfig):
        nonlocal model_calls, preloaded

        def model_factory(*_args, **_kwargs):
            nonlocal model_calls
            model_calls += 1
            return FakeModel()

        preloaded = FasterWhisperProvider(config, model_factory=model_factory)
        preloaded._model()  # fake-only preloading for the admission negative case
        return preloaded

    port, _store, _probe, _configs = make_port(tmp_path, provider_factory=factory)
    source, digest = source_file(tmp_path)
    with pytest.raises(ProductError) as exc:
        execute(port, source, digest)

    assert exc.value.code == "ERR_TASK098_RUNTIME_PROVIDER_INVALID"
    assert model_calls == 1
    assert preloaded is not None and preloaded.model_loaded is True


@pytest.mark.parametrize("requested_device", ["cpu", "cuda", "auto"])
def test_v2_operation_key_binds_request_variant_but_not_observation_time(tmp_path: Path, requested_device: str) -> None:
    first, _store, _probe, _configs = make_port(tmp_path / "first", requested_device=requested_device, port_clock=T0)
    second, _store2, _probe2, _configs2 = make_port(tmp_path / "second", requested_device=requested_device, port_clock=T0 + timedelta(seconds=1))
    digest = "sha256:" + "c" * 64
    assert first._execution_identity()[2] == second._execution_identity()[2]
    assert first._operation_key(PROJECT_ID, ASSET_ID, digest) == second._operation_key(PROJECT_ID, ASSET_ID, digest)

    other, _store3, _probe3, _configs3 = make_port(tmp_path / "other", requested_device="cuda" if requested_device != "cuda" else "cpu")
    assert other._operation_key(PROJECT_ID, ASSET_ID, digest) != first._operation_key(PROJECT_ID, ASSET_ID, digest)


def classifier_facts(status: str, ref: str | None, attempt: int = 0):
    source_sha = "sha256:" + "a" * 64
    operation_key = "task036-transcription-operation-key"
    owner_ref = "task098-runtime-owner:v2:guard-digest"
    lease = SimpleNamespace(status="IN_PROGRESS", attempt=0, result_ref=owner_ref)
    slot = SimpleNamespace(status="PENDING", result_ref=None)
    operation = SimpleNamespace(
        operation_id="operation-id",
        idempotency_key=operation_key,
        status=status,
        result_ref=ref,
        attempt=attempt,
    )
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    _observation, decision = evaluate_runtime_preflight(
        request,
        Probe(True),
        observed_at="2026-09-19T12:00:00Z",
        ttl_seconds=300,
    )
    return operation, lease, slot, operation_key, owner_ref, source_sha, decision


@pytest.mark.parametrize(
    "status,ref,attempt,validated,expected",
    [
        ("PENDING", None, 0, False, "PENDING_ADMISSION"),
        ("IN_PROGRESS", "task098-runtime-admission:v2:" + "a" * 64 + ":" + "b" * 64, 1, False, "ACTIVE_UNKNOWN"),
        ("PARTIAL", "sha256:" + "a" * 64, 1, True, "RECOVERABLE_PUBLICATION"),
        ("COMPLETED", "sha256:" + "a" * 64, 1, True, "VERIFICATION_ONLY"),
        ("PARTIAL", "task098-runtime-admission:v2:" + "a" * 64 + ":" + "b" * 64, 1, False, "ADJUDICATION_REQUIRED_NO_PUBLICATION"),
        ("FAILED", None, 0, False, "FAILED_TERMINAL"),
        ("FAILED", "task098-runtime-admission:v2:" + "a" * 64 + ":" + "b" * 64, 1, False, "CORRUPT_BLOCKED"),
        ("FAILED", "sha256:" + "a" * 64, 1, True, "CORRUPT_BLOCKED"),
    ],
)
def test_v2_recovery_classifier_covers_public_and_failed_states(status, ref, attempt, validated, expected) -> None:
    operation, lease, slot, operation_key, owner_ref, source_sha, decision = classifier_facts(status, ref, attempt)
    assert Task036RuntimeManagedLocalTranscriptionPortV2.classify_runtime_recovery(
        operation,
        lease=lease,
        slot=slot,
        expected_operation_key=operation_key,
        expected_owner_ref=owner_ref,
        expected_source_sha256=source_sha,
        validated_publication_ref=ref if validated else None,
        validated_decision=decision if validated else None,
    ) == expected


def test_v2_failed_typed_admission_requires_complete_validated_chain() -> None:
    source_sha = "sha256:" + "a" * 64
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    observation, decision = evaluate_runtime_preflight(
        request, Probe(True), observed_at="2026-09-19T12:00:00Z", ttl_seconds=300,
    )
    ref = (
        "task098-runtime-admission:v2:"
        + "a" * 64
        + ":"
        + decision.record_sha256.removeprefix("sha256:")
    )
    operation, lease, slot, operation_key, owner_ref, _source, _decision = classifier_facts(
        "FAILED", ref, 1,
    )
    classify = Task036RuntimeManagedLocalTranscriptionPortV2.classify_runtime_recovery
    common = dict(
        lease=lease, slot=slot, expected_operation_key=operation_key,
        expected_owner_ref=owner_ref, expected_source_sha256=source_sha,
    )
    assert classify(operation, **common) == "CORRUPT_BLOCKED"
    assert classify(
        operation, **common, validated_request=request,
        validated_observation=observation, validated_decision=decision,
    ) == "FAILED_TERMINAL"
    changed = FasterWhisperRuntimeRequestV1.create("cuda")
    assert classify(
        operation, **common, validated_request=changed,
        validated_observation=observation, validated_decision=decision,
    ) == "CORRUPT_BLOCKED"


@pytest.mark.parametrize("failed_shape", ["null", "publication", "typed-admission"])
def test_v2_failed_runtime_rows_are_zero_effect(
    tmp_path: Path, failed_shape: str,
) -> None:
    port, store, probe, configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.operation_id and outcome.slot_operation_id and outcome.publication_set_sha256
    operation = store.get_operation(outcome.operation_id)
    if failed_shape == "null":
        changed, ok = store.compare_and_set_operation_status(
            operation.operation_id, expected_statuses=("COMPLETED",),
            expected_result_refs=(outcome.publication_set_sha256,), status="FAILED",
            result_ref=None, replace_result_ref=True,
        )
        assert ok and changed.result_ref is None
    elif failed_shape == "publication":
        changed, ok = store.compare_and_set_operation_status(
            operation.operation_id, expected_statuses=("COMPLETED",),
            expected_result_refs=(outcome.publication_set_sha256,), status="FAILED",
            result_ref=outcome.publication_set_sha256, replace_result_ref=True,
        )
        assert ok and changed.result_ref == outcome.publication_set_sha256
    else:
        request = FasterWhisperRuntimeRequestV1.create("cpu")
        _observation, decision = evaluate_runtime_preflight(
            request, Probe(True), observed_at="2026-09-19T12:00:00Z", ttl_seconds=300,
        )
        typed_ref = (
            "task098-runtime-admission:v2:"
            + digest.removeprefix("sha256:") + ":" + decision.record_sha256.removeprefix("sha256:")
        )
        changed = store.update_operation_status(operation.operation_id, "FAILED", result_ref=typed_ref)
        assert changed.result_ref == typed_ref
    before_rows = store.list_operations_by_command_prefix(
        port.production_job_id, command_type_prefix="task036.local_transcription", limit=256,
    )
    before_fixed = {
        name: (port.output_directory / name).read_bytes()
        for name in ("transcript.json", "subtitles.srt", "transcription-report.json")
    }
    before_publication = {
        path.name: path.read_bytes()
        for path in (port.output_directory / ".task036-publications" / operation.operation_id).iterdir()
        if path.is_file()
    }
    before_slot = store.get_operation(outcome.slot_operation_id)
    probe_before, configs_before = list(probe.calls), list(configs)
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) in {"FAILED_TERMINAL", "CORRUPT_BLOCKED"}
    with pytest.raises(ProductError) as rejected:
        port.recover_local_media(
            project_id=PROJECT_ID, source_path=source,
            source_asset_id=ASSET_ID, source_asset_sha256=digest,
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE"
    assert store.list_operations_by_command_prefix(
        port.production_job_id, command_type_prefix="task036.local_transcription", limit=256,
    ) == before_rows
    assert store.get_operation(outcome.slot_operation_id) == before_slot
    assert probe.calls == probe_before and configs == configs_before
    assert before_fixed == {
        name: (port.output_directory / name).read_bytes()
        for name in before_fixed
    }
    assert before_publication == {
        path.name: path.read_bytes()
        for path in (port.output_directory / ".task036-publications" / operation.operation_id).iterdir()
        if path.is_file()
    }


@pytest.mark.parametrize("attempt", [True, False, -1])
def test_v2_recovery_classifier_rejects_bool_and_negative_attempt(attempt) -> None:
    operation, lease, slot, operation_key, owner_ref, source_sha, _decision = classifier_facts(
        "PENDING", None, 0,
    )
    operation.attempt = attempt
    assert Task036RuntimeManagedLocalTranscriptionPortV2.classify_runtime_recovery(
        operation, lease=lease, slot=slot, expected_operation_key=operation_key,
        expected_owner_ref=owner_ref, expected_source_sha256=source_sha,
    ) == "CORRUPT_BLOCKED"


def test_v2_slot_contention_rolls_back_to_retryable_pending_attempt(tmp_path: Path) -> None:
    port, store, _probe, configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    engine = port._engine()
    occupied = engine._acquire_output_slot(PROJECT_ID, "foreign-operation")
    with pytest.raises(ProductError) as busy:
        execute(port, source, digest)
    assert busy.value.code == "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY"
    operation = store.find_operation(
        port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest),
    )
    assert operation is not None
    assert (operation.status, operation.result_ref, operation.attempt) == ("PENDING", None, 1)
    assert configs == []
    engine._release_output_slot(occupied.operation_id, "foreign-operation")
    outcome = execute(port, source, digest)
    assert outcome.provider_execution_started is True
    retried = store.get_operation(outcome.operation_id)
    assert retried.attempt == 2


def test_v1_foreign_audit_validates_complete_v2_chain_and_allows_different_source(tmp_path: Path) -> None:
    v2, store, _probe, _configs = make_port(tmp_path)
    foreign_source, foreign_digest = source_file(tmp_path, b"foreign source bytes")
    execute(v2, foreign_source, foreign_digest)
    v1 = Task036LocalTranscriptionPort(
        FasterWhisperProvider(
            FasterWhisperConfig(model="small", allow_model_download=False),
            model_factory=lambda *_args, **_kwargs: FakeModel(),
        ),
        v2.output_directory,
        store,
        v2.production_job_id,
        language="ja",
    )
    other_sha = "sha256:" + "f" * 64
    guard_id = v1._acquire_cross_version_lease(
        PROJECT_ID, "ASSET-11111111111111111111111111", other_sha, version="v1",
    )
    assert store.get_operation(guard_id).result_ref is not None


def test_v1_foreign_audit_rejects_fully_rebound_blocked_v2_chain_without_requester_row(tmp_path: Path) -> None:
    v2, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(v2, source, digest)
    assert outcome.operation_id and outcome.publication_set_sha256
    publication = v2.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    document = json.loads(publication.read_text(encoding="utf-8"))
    request = FasterWhisperRuntimeRequestV1.create("cpu")
    observation, decision = evaluate_runtime_preflight(
        request, Probe(False), observed_at="2026-09-19T12:00:00Z", ttl_seconds=300,
    )
    document.update({
        "runtime_request": request.to_dict(),
        "runtime_capability_observation": observation.to_dict(),
        "runtime_decision": decision.to_dict(),
        "runtime_admission_ref": (
            "task098-runtime-admission:v2:"
            + digest.removeprefix("sha256:") + ":" + decision.record_sha256.removeprefix("sha256:")
        ),
        "admission_evaluated_at": "2026-09-19T12:00:00Z",
    })
    body = dict(document)
    old_ref = body.pop("publication_set_sha256")
    new_ref = sha256_bytes(canonical_json_bytes(body))
    document["publication_set_sha256"] = new_ref
    publication.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    changed, rebound = store.compare_and_set_operation_status(
        outcome.operation_id, expected_statuses=("COMPLETED",), expected_result_refs=(old_ref,),
        status="COMPLETED", result_ref=new_ref, replace_result_ref=True,
    )
    assert rebound and changed.result_ref == new_ref
    v1 = Task036LocalTranscriptionPort(
        FasterWhisperProvider(
            FasterWhisperConfig(model="small", allow_model_download=False),
            model_factory=lambda *_args, **_kwargs: FakeModel(),
        ),
        v2.output_directory, store, v2.production_job_id, language="ja",
    )
    guard_key = v1._cross_version_guard_key(PROJECT_ID, ASSET_ID, digest)
    foreign_guard = store.find_operation(v1.production_job_id, guard_key)
    assert foreign_guard is not None
    with pytest.raises(ProductError) as rejected:
        v1._acquire_cross_version_lease(PROJECT_ID, ASSET_ID, digest, version="v1")
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT"
    assert store.find_operation(v1.production_job_id, v1._operation_key(PROJECT_ID, ASSET_ID, digest)) is None
    assert store.find_operation(v1.production_job_id, guard_key) == foreign_guard


def test_v1_foreign_audit_rejects_checksum_valid_unknown_v2_field(tmp_path: Path) -> None:
    v2, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(v2, source, digest)
    assert outcome.operation_id and outcome.publication_set_sha256
    path = v2.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    old_ref = document.pop("publication_set_sha256")
    document["unknown_field"] = "must fail closed"
    new_ref = sha256_bytes(canonical_json_bytes(document))
    document["publication_set_sha256"] = new_ref
    path.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    changed, rebound = store.compare_and_set_operation_status(
        outcome.operation_id,
        expected_statuses=("COMPLETED",),
        expected_result_refs=(old_ref,),
        status="COMPLETED",
        result_ref=new_ref,
        replace_result_ref=True,
    )
    assert rebound and changed.result_ref == new_ref
    v1 = Task036LocalTranscriptionPort(
        FasterWhisperProvider(
            FasterWhisperConfig(model="small", allow_model_download=False),
            model_factory=lambda *_args, **_kwargs: FakeModel(),
        ),
        v2.output_directory,
        store,
        v2.production_job_id,
        language="ja",
    )
    with pytest.raises(ProductError) as corrupt:
        v1._acquire_cross_version_lease(PROJECT_ID, ASSET_ID, digest, version="v1")
    assert corrupt.value.code == "ERR_TASK036_TRANSCRIPTION_CROSS_VERSION_CORRUPT"


@pytest.mark.parametrize(
    "mutation",
    [
        {"lease": SimpleNamespace(status="IN_PROGRESS", attempt=1, result_ref="task098-runtime-owner:v2:guard-digest")},
        {"lease": SimpleNamespace(status="IN_PROGRESS", attempt=0, result_ref="task098-runtime-owner:v2:foreign")},
        {"slot": SimpleNamespace(status="CORRUPT", result_ref=None)},
        {"operation_key": "foreign-operation-key"},
        {"source_sha": "sha256:" + "b" * 64},
    ],
)
def test_v2_recovery_classifier_blocks_concrete_lease_key_slot_and_source_mismatch(mutation) -> None:
    status, ref, attempt = ("FAILED", None, 0) if "slot" in mutation else ("PARTIAL", "sha256:" + "a" * 64, 1)
    operation, lease, slot, operation_key, owner_ref, source_sha, decision = classifier_facts(status, ref, attempt)
    if "source_sha" in mutation:
        operation.result_ref = "task098-runtime-admission:v2:" + "a" * 64 + ":" + "b" * 64
    values = {
        "lease": lease,
        "slot": slot,
        "operation_key": operation_key,
        "source_sha": source_sha,
    }
    values.update(mutation)
    assert Task036RuntimeManagedLocalTranscriptionPortV2.classify_runtime_recovery(
        operation,
        lease=values["lease"],
        slot=values["slot"],
        expected_operation_key=values["operation_key"],
        expected_owner_ref=owner_ref,
        expected_source_sha256=values["source_sha"],
        validated_publication_ref="sha256:" + "a" * 64,
        validated_decision=decision if "source_sha" not in mutation else None,
    ) == "CORRUPT_BLOCKED"


def test_v2_publication_chain_tamper_is_not_recoverable(tmp_path: Path) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.publication_set_sha256 is not None
    publication = port.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    original = publication.read_bytes()
    publication.write_bytes(original + b"tampered")

    assert port.recovery_required(PROJECT_ID, ASSET_ID, digest) is False
    with pytest.raises(ProductError) as exc:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
        )
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    operation = store.find_operation(port.production_job_id, port._operation_key(PROJECT_ID, ASSET_ID, digest))
    assert operation is not None and operation.status == "COMPLETED"


def test_v2_checksum_valid_chain_tamper_is_rejected_after_operation_ref_is_rebound(tmp_path: Path) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.operation_id and outcome.publication_set_sha256
    publication = port.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    document = json.loads(publication.read_text(encoding="utf-8"))
    old_ref = document["publication_set_sha256"]
    document["runtime_request"]["requested_device"] = "cuda"
    body = dict(document)
    body.pop("publication_set_sha256")
    new_ref = sha256_bytes(canonical_json_bytes(body))
    document["publication_set_sha256"] = new_ref
    publication.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    changed, bound = store.compare_and_set_operation_status(
        outcome.operation_id,
        expected_statuses=("COMPLETED",),
        expected_result_refs=(old_ref,),
        status="COMPLETED",
        result_ref=new_ref,
        replace_result_ref=True,
    )
    assert bound and changed.result_ref == new_ref
    with pytest.raises(ProductError) as exc:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=digest,
        )
    assert exc.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"


@pytest.mark.parametrize("admission_at,expected_state", [
    ("2026-09-19T12:00:00Z", "VERIFICATION_ONLY"),
    ("2026-09-19T12:04:59.999999Z", "VERIFICATION_ONLY"),
    ("2026-09-19T12:05:00Z", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00.1Z", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00.123Z", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00.1234567Z", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00.000000Z", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00+00:00", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00Z ", "CORRUPT_BLOCKED"),
    ("2026-09-19T12:00:00", "CORRUPT_BLOCKED"),
    ("2026-02-30T12:00:00Z", "CORRUPT_BLOCKED"),
])
def test_v2_historical_admission_timestamp_canonicality_and_freshness(admission_at: str, expected_state: str, tmp_path: Path) -> None:
    port, store, _probe, _configs = make_port(tmp_path)
    source, digest = source_file(tmp_path)
    outcome = execute(port, source, digest)
    assert outcome.operation_id and outcome.publication_set_sha256
    publication = port.output_directory / ".task036-publications" / outcome.operation_id / "publication-set.json"
    document = json.loads(publication.read_text(encoding="utf-8"))
    old_ref = document["publication_set_sha256"]
    document["admission_evaluated_at"] = admission_at
    body = dict(document)
    body.pop("publication_set_sha256")
    new_ref = sha256_bytes(canonical_json_bytes(body))
    document["publication_set_sha256"] = new_ref
    publication.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    changed, bound = store.compare_and_set_operation_status(
        outcome.operation_id,
        expected_statuses=("COMPLETED",),
        expected_result_refs=(old_ref,),
        status="COMPLETED",
        result_ref=new_ref,
        replace_result_ref=True,
    )
    assert bound and changed.result_ref == new_ref
    assert port.recovery_state(
        project_id=PROJECT_ID, source_asset_id=ASSET_ID, source_asset_sha256=digest,
    ) == expected_state


def test_v2_settings_reject_relative_locator_and_download_authority() -> None:
    with pytest.raises(ValueError):
        FasterWhisperProviderSettingsV2(model="models/private")
    settings = FasterWhisperProviderSettingsV2(model="small")
    assert settings.model_id == "small"
    assert settings.normalized_cache_directory() is None
