from __future__ import annotations

from pathlib import Path

import pytest

import ai_video_production.durable_product_job as durable_job_module
import ai_video_production.project_history as history_module
import ai_video_production.voice_profile_store as voice_store_module
from ai_video_production.durable_product_job import (
    DurableProductJobCollection,
    DurableProductJobService,
    DurableProductJobState,
    DurableProductJobStore,
)
from ai_video_production.errors import ProductError
from ai_video_production.project_history import ProjectCommandHistory, ProjectCommandHistoryStore
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task102_project_manifest_transaction import PROTOCOL_VERSION, seal_record
from ai_video_production.task102_project_writer_migration import (
    ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
    PmstWriterMigrationRouter,
)
from ai_video_production.voice_profile_store import VoiceProfileRevisionStore


def _hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _enrollment(status: str) -> dict:
    return seal_record(
        {
            "record_type": "PMST_ENROLLMENT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "project_id": "project-1",
            "root_physical_identity_ref": "root-physical-1",
            "control_physical_identity_ref": "control-physical-1",
            "manifest_physical_identity_ref": "manifest-physical-1",
            "volume_binding_sha256": _hash("volume"),
            "owner_dacl_binding_sha256": _hash("dacl"),
            "writer_migration_matrix_sha256": ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
            "broker_install_binding_sha256": _hash("install"),
            "enrollment_epoch": "epoch-1",
            "created_at": "2026-09-29T00:00:00Z",
            "status": status,
        },
        kind="enrollment",
    )


class _Resolver:
    def __init__(self, status: str | None) -> None:
        self._value = None if status is None else _enrollment(status)

    def resolve(self, project_root: Path) -> dict | None:
        del project_root
        return self._value


def _router(status: str | None) -> PmstWriterMigrationRouter:
    return PmstWriterMigrationRouter(enrollment_resolver=_Resolver(status))


def _lock_must_not_run(*args, **kwargs):
    del args, kwargs
    raise AssertionError("legacy lock was reached")


@pytest.mark.parametrize("status", ["PREPARED", "ACTIVE", "SUSPENDED", "REVOKED"])
def test_enrolled_object_routes_block_before_legacy_lock_or_control_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    router = _router(status)
    monkeypatch.setattr(durable_job_module, "_exclusive_project_lock", _lock_must_not_run)
    monkeypatch.setattr(history_module, "_exclusive_project_lock", _lock_must_not_run)
    monkeypatch.setattr(voice_store_module, "exclusive_file_update_lock", _lock_must_not_run)
    job_service = DurableProductJobService(pmst_router=router)

    attempts = (
        lambda: job_service.enqueue(
            root,
            kind="EXPORT",
            target_identity="export-1",
            input_hashes={"manifest": _hash("manifest")},
        ),
        lambda: job_service.query_by_input_binding(
            root,
            kind="EXPORT",
            input_name="manifest",
            input_sha256=_hash("manifest"),
        ),
        lambda: job_service.transition(
            root,
            "job-1",
            DurableProductJobState.RUNNING,
            expected_state_version=1,
        ),
        lambda: job_service.recover_interrupted(root),
        lambda: ProjectCommandHistoryStore.save(
            root,
            ProjectCommandHistory.create("project-1"),
            pmst_router=router,
        ),
        lambda: VoiceProfileRevisionStore.create(root, object(), pmst_router=router),
    )

    for attempt in attempts:
        with pytest.raises(ProductError) as captured:
            attempt()
        assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"
    assert not (root / ".bai-project").exists()


def test_package_private_object_writers_cannot_bypass_enrolled_guard(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    router = _router("ACTIVE")

    attempts = (
        lambda: DurableProductJobStore._save_unlocked(
            root,
            DurableProductJobCollection.create("project-1"),
            pmst_router=router,
        ),
        lambda: ProjectCommandHistoryStore._save_unlocked(
            root,
            ProjectCommandHistory.create("project-1"),
            pmst_router=router,
        ),
    )
    for attempt in attempts:
        with pytest.raises(ProductError) as captured:
            attempt()
        assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"
    assert not (root / ".bai-project").exists()


def test_unenrolled_guard_preserves_existing_job_service_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    router = _router(None)

    route = router.require_legacy_access(root, route_id="PMST-R003", access_kind="LOCK")

    assert route.route_id == "PMST-R003"
    assert not (root / ".bai-project").exists()
