from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.desktop_shell import JobState as ShellJobState
from ai_video_production.durable_product_job import (
    DurableProductJob,
    DurableProductJobCollection,
    DurableProductJobService,
    DurableProductJobState,
    DurableProductJobStore,
    durable_job_shell_projection,
    parse_durable_product_job_collection,
)
from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import sha256_bytes


def setup_project(root: Path) -> ProductProjectManifest:
    manifest = ProductProjectManifest.create(
        project_id="project-1", project_revision=1, product_version="0.20.1",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-08-14T00:00:00.000Z", updated_at="2026-08-14T00:00:00.000Z",
    )
    ProductProjectManifestStore.save(root, manifest)
    return manifest


def inputs(label: str = "one") -> dict[str, str]:
    return {"timeline": sha256_bytes(label.encode())}


def enqueue(root: Path, label: str = "one") -> DurableProductJob:
    return DurableProductJobService().enqueue(
        root, kind="EXPORT", target_identity="timeline:main", input_hashes=inputs(label),
        estimated_cost=0, currency="USD", estimate_source="local-free",
    )


def advance(root: Path, job: DurableProductJob, *states: DurableProductJobState) -> DurableProductJob:
    service = DurableProductJobService()
    current = job
    for state in states:
        kwargs = {}
        if state is DurableProductJobState.SUCCEEDED:
            kwargs = {"result_ref": "artifact://exports/final.mp4", "actual_cost": 0}
        elif state in {DurableProductJobState.FAILED, DurableProductJobState.UNKNOWN, DurableProductJobState.HUMAN_REQUIRED}:
            kwargs = {"error_code": "ERR_PRODUCT_JOB_TEST_STATE"}
        current = service.transition(root, current.job_id, state, expected_state_version=current.state_version, **kwargs)
    return current


def test_schema_is_valid_packaged_and_accepts_real_store(tmp_path: Path) -> None:
    public = Path(__file__).parents[1] / "schemas/durable-product-job.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    setup_project(tmp_path)
    enqueue(tmp_path)
    document = json.loads(DurableProductJobStore.path(tmp_path).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(document)
    assert parse_durable_product_job_collection(document) == DurableProductJobStore.load(tmp_path)


def test_enqueue_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    setup_project(tmp_path)
    first = enqueue(tmp_path)
    store_after_first = DurableProductJobStore.load(tmp_path)
    second = enqueue(tmp_path)
    assert second == first
    assert DurableProductJobStore.load(tmp_path) == store_after_first
    assert len(store_after_first.jobs) == 1
    assert first.operation_identity.startswith("operation-")
    assert first.job_id.endswith(first.operation_identity.removeprefix("operation-"))


def test_exact_inputs_create_distinct_export_jobs(tmp_path: Path) -> None:
    setup_project(tmp_path)
    first = enqueue(tmp_path, "one")
    second = enqueue(tmp_path, "two")
    assert first.job_id != second.job_id
    assert len(DurableProductJobStore.load(tmp_path).jobs) == 2


def test_full_local_job_state_machine_and_cost_truth(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = enqueue(tmp_path)
    final = advance(
        tmp_path, job,
        DurableProductJobState.PREFLIGHT,
        DurableProductJobState.READY,
        DurableProductJobState.DISPATCHING,
        DurableProductJobState.RUNNING,
        DurableProductJobState.SUCCEEDED,
    )
    assert final.state is DurableProductJobState.SUCCEEDED
    assert final.attempt == 1
    assert final.result_ref == "artifact://exports/final.mp4"
    assert final.estimated_cost == 0 and final.actual_cost == 0 and final.currency == "USD"
    assert final.recovery_actions == ()


def test_invalid_transition_fails_closed(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = enqueue(tmp_path)
    with pytest.raises(ProductError) as exc:
        DurableProductJobService().transition(
            tmp_path, job.job_id, DurableProductJobState.RUNNING,
            expected_state_version=job.state_version,
        )
    assert exc.value.code == "ERR_PRODUCT_JOB_TRANSITION"


def test_transition_requires_exact_state_version(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = enqueue(tmp_path)
    with pytest.raises(ProductError) as exc:
        DurableProductJobService().transition(
            tmp_path, job.job_id, DurableProductJobState.PREFLIGHT,
            expected_state_version=99,
        )
    assert exc.value.code == "ERR_PRODUCT_JOB_CAS_CONFLICT"


@pytest.mark.parametrize("interrupted", [DurableProductJobState.DISPATCHING, DurableProductJobState.RUNNING])
def test_restart_moves_dispatched_or_running_job_to_unknown_without_replay(tmp_path: Path, interrupted: DurableProductJobState) -> None:
    setup_project(tmp_path)
    states = [DurableProductJobState.PREFLIGHT, DurableProductJobState.READY, DurableProductJobState.DISPATCHING]
    if interrupted is DurableProductJobState.RUNNING:
        states.append(DurableProductJobState.RUNNING)
    job = advance(tmp_path, enqueue(tmp_path), *states)
    recovered = DurableProductJobService().recover_interrupted(tmp_path)
    assert len(recovered) == 1
    unknown = recovered[0]
    assert unknown.state is DurableProductJobState.UNKNOWN
    assert unknown.attempt == 1
    assert unknown.unknown_since is not None
    assert unknown.recovery_actions == ("ACCEPT_PROVEN_SUCCESS", "MARK_FAILED", "REQUIRE_HUMAN")
    assert DurableProductJobService().recover_interrupted(tmp_path) == ()


def test_unknown_cannot_retry_and_requires_typed_reconciliation(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = advance(
        tmp_path, enqueue(tmp_path), DurableProductJobState.PREFLIGHT,
        DurableProductJobState.READY, DurableProductJobState.DISPATCHING,
    )
    unknown = DurableProductJobService().recover_interrupted(tmp_path)[0]
    service = DurableProductJobService()
    with pytest.raises(ProductError) as exc:
        service.transition(tmp_path, job.job_id, DurableProductJobState.READY, expected_state_version=unknown.state_version)
    assert exc.value.code == "ERR_PRODUCT_JOB_TRANSITION"
    with pytest.raises(ProductError) as exc:
        service.transition(
            tmp_path, job.job_id, DurableProductJobState.SUCCEEDED,
            expected_state_version=unknown.state_version, result_ref="artifact://exports/final.mp4",
        )
    assert exc.value.code == "ERR_PRODUCT_JOB_RECOVERY_ACTION_REQUIRED"
    reconciled = service.transition(
        tmp_path, job.job_id, DurableProductJobState.SUCCEEDED,
        expected_state_version=unknown.state_version, result_ref="artifact://exports/final.mp4",
        actual_cost=0, recovery_action="ACCEPT_PROVEN_SUCCESS",
    )
    assert reconciled.state is DurableProductJobState.SUCCEEDED


def test_human_required_can_resume_only_with_recorded_action(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = advance(tmp_path, enqueue(tmp_path), DurableProductJobState.PREFLIGHT)
    human = DurableProductJobService().transition(
        tmp_path, job.job_id, DurableProductJobState.HUMAN_REQUIRED,
        expected_state_version=job.state_version, error_code="ERR_PRODUCT_JOB_TARGET_REVIEW",
    )
    with pytest.raises(ProductError) as exc:
        DurableProductJobService().transition(
            tmp_path, job.job_id, DurableProductJobState.PREFLIGHT,
            expected_state_version=human.state_version,
        )
    assert exc.value.code == "ERR_PRODUCT_JOB_RECOVERY_ACTION_REQUIRED"
    resumed = DurableProductJobService().transition(
        tmp_path, job.job_id, DurableProductJobState.PREFLIGHT,
        expected_state_version=human.state_version, recovery_action="RESUME_PREFLIGHT",
    )
    assert resumed.state is DurableProductJobState.PREFLIGHT


@pytest.mark.parametrize("target", ["C:/secret/output", "/root/output", "timeline:credential-token"])
def test_target_identity_rejects_host_paths_and_private_terms(target: str) -> None:
    with pytest.raises(ValueError):
        DurableProductJob.create(kind="EXPORT", target_identity=target, input_hashes=inputs())


def test_provider_job_kind_is_not_owned_by_product_background_jobs() -> None:
    with pytest.raises(ValueError):
        DurableProductJob.create(kind="PROVIDER_GENERATION", target_identity="scene:1", input_hashes=inputs())


def test_transition_rejects_job_store_copied_from_another_project(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = enqueue(tmp_path)
    wrong = DurableProductJobCollection.create("other-project").replace(job)
    DurableProductJobStore._save_unlocked(tmp_path, wrong)
    with pytest.raises(ProductError) as exc:
        DurableProductJobService().transition(
            tmp_path, job.job_id, DurableProductJobState.PREFLIGHT,
            expected_state_version=job.state_version,
        )
    assert exc.value.code == "ERR_PRODUCT_JOB_PROJECT_CONFLICT"


def test_store_checksum_tamper_is_detected(tmp_path: Path) -> None:
    setup_project(tmp_path)
    enqueue(tmp_path)
    path = DurableProductJobStore.path(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["store_revision"] += 1
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        DurableProductJobStore.load(tmp_path)
    assert exc.value.code == "ERR_PRODUCT_JOB_STORE_INVALID"


def test_store_does_not_replace_generation_queue_or_authorize_execution(tmp_path: Path) -> None:
    setup_project(tmp_path)
    enqueue(tmp_path)
    document = json.loads(DurableProductJobStore.path(tmp_path).read_text(encoding="utf-8"))
    assert document["authority"] == {
        "generation_queue_replaced": False,
        "provider_execution_authorized": False,
        "external_replay_authorized": False,
    }
    assert document["jobs"][0]["authority"] == {
        "provider_execution_authorized": False,
        "paid_execution_authorized": False,
        "external_replay_authorized": False,
    }


def test_shell_projection_is_read_only_and_unknown_waits_for_human(tmp_path: Path) -> None:
    setup_project(tmp_path)
    job = advance(
        tmp_path, enqueue(tmp_path), DurableProductJobState.PREFLIGHT,
        DurableProductJobState.READY, DurableProductJobState.DISPATCHING,
    )
    unknown = DurableProductJobService().recover_interrupted(tmp_path)[0]
    snapshot = durable_job_shell_projection(unknown)
    assert snapshot.state is ShellJobState.WAITING_HUMAN
    assert snapshot.safe_cancel is False
    assert snapshot.command_id == unknown.operation_identity
    assert snapshot.error_code == "ERR_PRODUCT_JOB_RESTART_UNKNOWN"
