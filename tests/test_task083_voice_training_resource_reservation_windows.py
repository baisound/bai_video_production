"""Effect-zero tests for the TASK-083 Windows reservation boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task083_voice_training_resource_reservation import (
    compile_resource_reservation_plan,
)
from ai_video_production.task083_voice_training_resource_reservation_windows import (
    Task083WindowsReservationBackend,
    Task083WindowsResourceEffectBlocked,
    open_task083_windows_reservation_backend,
)
from ai_video_production.voice_dataset_revision import add_record_digest as dataset_digest
from ai_video_production.voice_training_run import add_record_digest as training_digest


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_SOURCE = (
    ROOT
    / "src"
    / "ai_video_production"
    / "task083_voice_training_resource_reservation_windows.py"
)
H = lambda value: sha256_bytes(value.encode("utf-8"))


def make_plan():
    snapshot = dataset_digest(
        {
            "record_type": "TrainingInputSnapshot",
            "snapshot_id": "snapshot-083-windows-1",
            "revision": 1,
            "parent_snapshot_sha256": None,
            "project_id": "project-083-windows",
            "dataset_id": "dataset-owner-voice",
            "voice_dataset_revision_ref": "voice-dataset-revision:8",
            "voice_dataset_revision_sha256": H("dataset-revision"),
            "selected_member_entry_sha256s": [H("member-1")],
            "exclusion_sha256s": [],
            "policy_revision_sha256": H("dataset-policy"),
            "readiness_sha256": H("readiness"),
            "current_consent_evaluation_sha256": H("consent"),
            "current_rights_evaluation_sha256": H("rights"),
            "created_at": "2026-09-07T00:00:00Z",
            "audio_body_persisted": False,
            "text_body_persisted": False,
            "dataset_mutation_authorized": False,
            "training_authorized": False,
        },
        "snapshot_sha256",
    )
    job = training_digest(
        {
            "record_type": "TrainingDurableJobBinding",
            "contract_state": "BOUND_VERIFIED",
            "job_id": "job-voice-training-083-windows",
            "operation_id": "operation-voice-training-083-windows",
            "idempotency_key": "idempotency-voice-training-083-windows",
            "job_kind": "VOICE_MODEL_TRAINING",
            "job_revision": 1,
            "job_revision_sha256": H("job-revision"),
            "job_state": "READY",
            "canonical_job_evidence_ref": "job-evidence:083:windows",
            "canonical_job_evidence_sha256": H("job-evidence"),
            "identity_shared_with_dataset_adoption_job": False,
        },
        "binding_sha256",
    )
    return compile_resource_reservation_plan(
        training_input_snapshot=snapshot,
        training_job_binding=job,
        run_id="run-083-windows-1",
        training_input_snapshot_ref="training-snapshot:083:windows:1",
        recipe_revision_ref="training-recipe:083:windows:1",
        recipe_revision_sha256=H("recipe"),
        backend_id="task083-windows-boundary",
        backend_build_sha256=H("backend"),
        runtime_revision="runtime-1",
        runtime_sha256=H("runtime"),
        device_profile_ref="device-profile:083:windows:1",
        device_profile_sha256=H("device-profile"),
        capability_admission_sha256=H("capability-admission"),
        resource_floor={
            "cpu_units": 4,
            "ram_bytes": 8_000_000_000,
            "vram_bytes": 6_000_000_000,
            "disk_bytes": 20_000_000_000,
        },
        resource_ceiling={
            "cpu_units": 12,
            "ram_bytes": 32_000_000_000,
            "vram_bytes": 24_000_000_000,
            "disk_bytes": 100_000_000_000,
        },
        policy_revision_sha256=H("policy"),
        issued_at="2026-09-07T01:00:00Z",
        expires_at="2026-09-07T02:00:00Z",
    )


def test_windows_boundary_returns_only_current_blocked_admission() -> None:
    backend = open_task083_windows_reservation_backend()
    admission = backend.compile_production_admission(
        make_plan(), evaluated_at="2026-09-07T01:15:00Z"
    ).to_dict()

    assert admission["decision"] == "BLOCKED"
    assert "NATIVE_BACKEND_NOT_IMPLEMENTED" in admission["reason_codes"]
    assert admission["resource_effect_count"] == backend.resource_effect_count == 0
    assert admission["authority_created"] is False
    assert admission["native_reservation_invoked"] is False
    assert admission["training_dispatched"] is False
    assert b"private" not in canonical_json_bytes(admission)


@pytest.mark.parametrize(
    "method_name",
    ["observe_native_resources", "reserve_native_resources", "start_training_process"],
)
def test_windows_effect_entrypoints_are_pre_effect_h3_stops(method_name: str) -> None:
    backend = open_task083_windows_reservation_backend()

    with pytest.raises(Task083WindowsResourceEffectBlocked):
        getattr(backend, method_name)()

    assert backend.resource_effect_count == 0


def test_windows_boundary_rejects_invalid_plan_before_any_effect() -> None:
    backend = open_task083_windows_reservation_backend()

    with pytest.raises(ValueError):
        backend.compile_production_admission({}, evaluated_at="2026-09-07T01:15:00Z")

    assert backend.resource_effect_count == 0


def test_windows_boundary_is_not_extensible() -> None:
    with pytest.raises(TypeError):
        type("ForgedTask083WindowsBackend", (Task083WindowsReservationBackend,), {})


def test_windows_source_has_no_native_or_process_import_route() -> None:
    tree = ast.parse(WINDOWS_SOURCE.read_text(encoding="utf-8"))
    banned_roots = {"ctypes", "os", "psutil", "subprocess", "win32api", "wmi"}
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not imported & banned_roots
