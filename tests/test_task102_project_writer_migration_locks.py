from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import ai_video_production.montage_learning_canonical_admission_transaction as montage_module
from ai_video_production.creative_generation_execution_application import (
    Task013CreativeGenerationExecutionApplication,
)
from ai_video_production.errors import ProductError
from ai_video_production.generation_output_adoption_application import (
    Task027GenerationOutputAdoptionApplication,
)
from ai_video_production.interactive_timeline_application import (
    Task044TimelineEditApplication,
    _TimelineHistoryParticipant,
)
from ai_video_production.montage_learning_canonical_admission_transaction import (
    MontageLearningCanonicalAdmissionError,
    MontageLearningCanonicalAdmissionTransactionStore,
)
from ai_video_production.planning_application import Task027PlanningApplication
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task102_project_manifest_transaction import PROTOCOL_VERSION, seal_record
from ai_video_production.task102_project_writer_migration import (
    ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
    PmstWriterMigrationRouter,
)


def _hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


class _Resolver:
    def resolve(self, project_root: Path) -> dict:
        del project_root
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
                "status": "ACTIVE",
            },
            kind="enrollment",
        )


def _router() -> PmstWriterMigrationRouter:
    return PmstWriterMigrationRouter(enrollment_resolver=_Resolver())


@pytest.mark.parametrize(
    ("application_type", "invoke"),
    [
        (
            Task044TimelineEditApplication,
            lambda app: app.apply(confirmation_id="confirmation-1", timeline=object()),
        ),
        (
            Task027PlanningApplication,
            lambda app: app.append_initial_proposal(
                intent=None,
                proposal=None,
                expected_snapshot_sha256=_hash("snapshot"),
                expected_project_manifest_sha256=_hash("manifest"),
            ),
        ),
        (
            Task013CreativeGenerationExecutionApplication,
            lambda app: app.apply_execution(confirmation_id="confirmation-1"),
        ),
    ],
)
def test_enrolled_r008_r009_callers_block_before_legacy_lock(
    tmp_path: Path,
    application_type: type,
    invoke,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    application = application_type.__new__(application_type)
    application.project_root = root
    application._pmst_router = _router()

    with pytest.raises(ProductError) as captured:
        invoke(application)

    assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"
    assert not (root / ".bai-project").exists()


def test_enrolled_adoption_blocks_without_consuming_confirmation(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    application = Task027GenerationOutputAdoptionApplication.__new__(
        Task027GenerationOutputAdoptionApplication
    )
    pending = SimpleNamespace(consumed=False)
    application.project_root = root
    application._pmst_router = _router()
    application._confirmations = {"confirmation-1": pending}

    with pytest.raises(ProductError) as captured:
        application.apply_adoption(confirmation_id="confirmation-1")

    assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"
    assert pending.consumed is False
    assert not (root / ".bai-project").exists()


def test_enrolled_timeline_participant_blocks_before_recovery_write(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    participant = _TimelineHistoryParticipant(
        project_id="project-1",
        recovery_path=root / ".bai-project" / "timeline-edit-command-recovery.json",
        pmst_router=_router(),
    )

    with pytest.raises(ProductError) as captured:
        participant.prepare_locked(root, "transaction-1", object())

    assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"
    assert not (root / ".bai-project").exists()


def test_enrolled_timeline_recovery_status_does_not_read_legacy_journal(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    application = Task044TimelineEditApplication.__new__(Task044TimelineEditApplication)
    application.project_root = root
    application._pmst_router = _router()
    application._save_coordinator = SimpleNamespace(
        recovery_status=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy recovery journal was read")
        )
    )

    with pytest.raises(ProductError) as captured:
        application.project_save_recovery_status()

    assert captured.value.code == "ERR_PMST_LEGACY_WRITER_BLOCKED"


def test_enrolled_task029_store_blocks_before_project_lock_or_directory_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    anchor_root = tmp_path / "anchor"
    project_root.mkdir()
    anchor_root.mkdir()

    def lock_must_not_run(*args, **kwargs):
        del args, kwargs
        raise AssertionError("legacy TASK-029 Project lock was reached")

    monkeypatch.setattr(montage_module, "_exclusive_existing_project_lock", lock_must_not_run)
    with pytest.raises(MontageLearningCanonicalAdmissionError, match="requires the PMST TASK-029 adapter"):
        MontageLearningCanonicalAdmissionTransactionStore(
            project_root,
            anchor_root,
            canonical_store_id="canonical-store-1",
            bridge_instance_id="bridge-1",
            pmst_router=_router(),
        )

    assert not (project_root / "state").exists()
    assert tuple(anchor_root.iterdir()) == ()


def test_task029_existing_instance_rechecks_enrollment_before_each_lock_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    store = MontageLearningCanonicalAdmissionTransactionStore.__new__(
        MontageLearningCanonicalAdmissionTransactionStore
    )
    store.project_root = root
    store._pmst_router = _router()

    attempts = (
        lambda: store.admit_exact(
            {},
            staging_store_id="store-1",
            expected_owner_scope_hash=_hash("scope"),
            expected_staging_revision=1,
            expected_staging_entry_sha256=_hash("entry"),
            expected_canonical_store_commit_sha256=None,
            expected_external_anchor_document_sha256=None,
        ),
        lambda: store.admit_generic_observation({}, expected_revision=0),
        lambda: store.recover_generic_observation({}),
        lambda: store.get_verified_generic_observation(
            record_id="record-1",
            learning_sha256=_hash("learning"),
            canonical_commit_sha256=_hash("commit"),
        ),
    )

    for attempt in attempts:
        with pytest.raises(MontageLearningCanonicalAdmissionError, match="requires the PMST TASK-029 adapter"):
            attempt()
    assert not (root / ".bai-project").exists()
