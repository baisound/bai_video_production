from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from ai_video_production.atomic import AtomicJsonWriter
from ai_video_production.audio_placement_application import Task026AudioPlacementApplication
from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import ProductProjectSaveCoordinator, ProjectSaveJournalStore
from ai_video_production.project_migration_application import ProductProjectMigrationApplication
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task102_project_manifest_transaction import (
    PROTOCOL_VERSION,
    ContractRecord,
    seal_record,
)
from ai_video_production.task102_project_writer_migration import (
    ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
    PmstWriterMigrationRouter,
)
from ai_video_production.voice_quality_meter_policy_store import MeterPolicyProjectStore, MeterPolicyStoreError


CREATED = "2026-09-29T00:00:00Z"
UPDATED = "2026-09-29T00:01:00Z"


def h(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def manifest(revision: int, *bindings: ProjectChildBinding) -> ProductProjectManifest:
    return ProductProjectManifest.create(
        project_id="project-1",
        project_revision=revision,
        product_version="0.24.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=bindings,
        created_at=CREATED,
        updated_at=CREATED if revision == 1 else UPDATED,
    )


def child_binding(data: bytes) -> ProjectChildBinding:
    return ProjectChildBinding(
        "TASK-043",
        "state/child.json",
        "bai.test-child",
        "1.0.0",
        sha256_bytes(data),
        True,
    )


def enrollment() -> dict:
    return seal_record(
        {
            "record_type": "PMST_ENROLLMENT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "project_id": "project-1",
            "root_physical_identity_ref": "root-physical-1",
            "control_physical_identity_ref": "control-physical-1",
            "manifest_physical_identity_ref": "manifest-physical-1",
            "volume_binding_sha256": h("volume"),
            "owner_dacl_binding_sha256": h("dacl"),
            "writer_migration_matrix_sha256": ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
            "broker_install_binding_sha256": h("install"),
            "enrollment_epoch": "epoch-1",
            "created_at": CREATED,
            "status": "ACTIVE",
        },
        kind="enrollment",
    )


def private_request(
    successor: ProductProjectManifest,
    *,
    profile_id: str,
    predecessor_sha256: str | None = None,
) -> dict:
    successor_document = successor.to_dict()
    successor_document_sha256 = sha256_bytes(canonical_json_bytes(successor_document))
    if predecessor_sha256 is None:
        kind = "MANIFEST_CREATE_V1"
        payload = {
            "successor_manifest": successor_document,
            "successor_manifest_sha256": successor_document_sha256,
            "semantic_authorization_sha256": h("authority"),
        }
    else:
        kind = "MANIFEST_TRANSITION_V1"
        payload = {
            "prior_manifest_sha256": predecessor_sha256,
            "prior_manifest_physical_identity_ref": "manifest-physical-1",
            "successor_manifest": successor_document,
            "successor_manifest_sha256": successor_document_sha256,
            "participant_plan_sha256": h("no-participant-plan"),
            "semantic_authorization_sha256": h("authority"),
        }
    intent = seal_record(
        {
            "protocol_version": PROTOCOL_VERSION,
            "record_type": "PMST_OPERATION_INTENT_V1",
            "project_registration_id": "registration-1",
            "operation_id": "operation-1",
            "operation_kind": kind,
            "operation_profile_id": profile_id,
            "caller_task_id": "TASK-043",
            "caller_build_sha256": h("build"),
            "caller_policy_sha256": h("policy"),
            "requested_at": CREATED,
            "expires_at": "2026-09-29T00:05:00Z",
            "payload": payload,
        },
        kind="intent",
    )
    return seal_record(
        {
            "protocol_version": PROTOCOL_VERSION,
            "record_type": "PMST_PRIVATE_REQUEST_V1",
            "broker_instance_id": "broker-1",
            "session_id": "session-1",
            "request_nonce_id": "nonce-1",
            "intent": intent,
        },
        kind="request",
    )


def public_status(request: ContractRecord) -> dict:
    intent = request.data["intent"]
    return seal_record(
        {
            "record_type": "PMST_PUBLIC_OPERATION_STATUS_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": request.data["request_sha256"],
            "status": "COMMITTED_WITH_READBACK",
            "reason_codes": [],
            "operation_witness_sha256": h("witness"),
            "readback_sha256": h("readback"),
            "retry_allowed": False,
            "human_recovery_required": False,
            "effect_count": 1,
        },
        kind="public",
    )


class Resolver:
    @staticmethod
    def resolve(project_root: Path) -> dict:
        assert project_root.is_absolute()
        return enrollment()


class Port:
    def __init__(self, effect: Callable[[ContractRecord], None]) -> None:
        self.effect = effect
        self.calls: list[tuple[str, ContractRecord, ContractRecord]] = []

    def execute(
        self,
        *,
        route_id: str,
        request: ContractRecord,
        enrollment: ContractRecord,
    ) -> dict:
        self.calls.append((route_id, request, enrollment))
        self.effect(request)
        return public_status(request)


def active_router(effect: Callable[[ContractRecord], None]) -> tuple[PmstWriterMigrationRouter, Port]:
    port = Port(effect)
    return PmstWriterMigrationRouter(enrollment_resolver=Resolver(), writer_port=port), port


def assert_error(code: str, call) -> ProductError:
    with pytest.raises(ProductError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def test_enrolled_manifest_create_requires_request_before_control_directory_effect(tmp_path: Path) -> None:
    target = manifest(1)
    router, port = active_router(lambda request: None)

    assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: ProductProjectManifestStore.save(tmp_path, target, pmst_router=router),
    )

    assert port.calls == []
    assert not (tmp_path / ".bai-project").exists()


def test_enrolled_manifest_create_routes_and_requires_exact_canonical_readback(tmp_path: Path) -> None:
    target = manifest(1)

    def write_manifest(request: ContractRecord) -> None:
        AtomicJsonWriter.write(
            tmp_path / ".bai-project/project.json",
            request.to_dict()["intent"]["payload"]["successor_manifest"],
        )

    router, port = active_router(write_manifest)
    request = private_request(target, profile_id="task043-manifest-create-v1")
    result = ProductProjectManifestStore.save(
        tmp_path,
        target,
        pmst_router=router,
        pmst_private_request=request,
    )

    assert result.checksum == sha256_bytes(canonical_json_bytes(target.to_dict()))
    assert ProductProjectManifestStore.load(tmp_path) == target
    assert [call[0] for call in port.calls] == ["PMST-R001"]
    assert not (tmp_path / ".bai-project/.project.json.lock").exists()

    missing_root = tmp_path / "missing-readback"
    missing_root.mkdir()
    missing_router, missing_port = active_router(lambda routed: None)
    assert_error(
        "ERR_PMST_MANIFEST_READBACK_INVALID",
        lambda: ProductProjectManifestStore.save(
            missing_root,
            target,
            pmst_router=missing_router,
            pmst_private_request=request,
        ),
    )
    assert len(missing_port.calls) == 1


def test_manifest_request_mismatch_and_direct_unlocked_bypass_fail_before_port(tmp_path: Path) -> None:
    target = manifest(1)
    other = ProductProjectManifest.create(
        project_id="project-other",
        project_revision=1,
        product_version="0.24.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at=CREATED,
        updated_at=CREATED,
    )
    router, port = active_router(lambda request: None)
    request = private_request(other, profile_id="task043-manifest-create-v1")
    assert_error(
        "ERR_PMST_MANIFEST_REQUEST_MISMATCH",
        lambda: ProductProjectManifestStore.save(
            tmp_path,
            target,
            pmst_router=router,
            pmst_private_request=request,
        ),
    )
    assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: ProductProjectManifestStore._save_unlocked(
            tmp_path,
            target,
            expected_previous_manifest_sha256=None,
            pmst_router=router,
        ),
    )
    assert port.calls == []


def test_enrolled_direct_transition_preserves_exact_predecessor_and_revision_rules(tmp_path: Path) -> None:
    current = manifest(1)
    target = manifest(2)
    ProductProjectManifestStore.save(tmp_path, current)
    (tmp_path / ".bai-project/.project.json.lock").unlink()

    def commit(request: ContractRecord) -> None:
        AtomicJsonWriter.write(
            tmp_path / ".bai-project/project.json",
            request.to_dict()["intent"]["payload"]["successor_manifest"],
        )

    router, port = active_router(commit)
    transition = private_request(
        target,
        profile_id="task043-manifest-transition-v1",
        predecessor_sha256=current.project_manifest_sha256,
    )
    result = ProductProjectManifestStore.save(
        tmp_path,
        target,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        pmst_router=router,
        pmst_private_request=transition,
    )
    assert result.checksum == sha256_bytes(canonical_json_bytes(target.to_dict()))
    assert len(port.calls) == 1

    empty = tmp_path / "empty"
    empty.mkdir()
    revision_two_create = private_request(target, profile_id="task043-manifest-create-v1")
    empty_router, empty_port = active_router(lambda request: None)
    assert_error(
        "ERR_PMST_MANIFEST_PREDECESSOR_MISMATCH",
        lambda: ProductProjectManifestStore.save(
            empty,
            target,
            pmst_router=empty_router,
            pmst_private_request=revision_two_create,
        ),
    )
    assert empty_port.calls == []


def setup_coordinated_project(root: Path) -> tuple[ProductProjectManifest, ProductProjectManifest, dict[str, bytes]]:
    old = b"old-child"
    new = b"new-child"
    child = root / "state/child.json"
    child.parent.mkdir()
    child.write_bytes(old)
    current = manifest(1, child_binding(old))
    target = manifest(2, child_binding(new))
    ProductProjectManifestStore.save(root, current)
    (root / ".bai-project/.project.json.lock").unlink()
    return current, target, {"state/child.json": new}


def test_enrolled_coordinated_save_routes_without_legacy_lock_or_journal(tmp_path: Path) -> None:
    current, target, documents = setup_coordinated_project(tmp_path)

    def commit(request: ContractRecord) -> None:
        (tmp_path / "state/child.json").write_bytes(documents["state/child.json"])
        AtomicJsonWriter.write(
            tmp_path / ".bai-project/project.json",
            request.to_dict()["intent"]["payload"]["successor_manifest"],
        )

    router, port = active_router(commit)
    coordinator = ProductProjectSaveCoordinator(pmst_router=router)
    request = private_request(
        target,
        profile_id="task043-coordinated-save-v1",
        predecessor_sha256=current.project_manifest_sha256,
    )
    result = coordinator.save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        pmst_private_request=request,
    )

    assert result == target
    assert [call[0] for call in port.calls] == ["PMST-R002"]
    assert not ProjectSaveJournalStore.path(tmp_path).exists()
    assert not (tmp_path / ".bai-project/.project.json.lock").exists()


def test_enrolled_coordinator_blocks_legacy_and_requires_child_readback(tmp_path: Path) -> None:
    current, target, documents = setup_coordinated_project(tmp_path)
    router, port = active_router(lambda request: None)
    coordinator = ProductProjectSaveCoordinator(pmst_router=router)
    assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: coordinator.save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        ),
    )
    assert port.calls == []
    assert not ProjectSaveJournalStore.path(tmp_path).exists()

    def manifest_only(request: ContractRecord) -> None:
        AtomicJsonWriter.write(
            tmp_path / ".bai-project/project.json",
            request.to_dict()["intent"]["payload"]["successor_manifest"],
        )

    readback_router, readback_port = active_router(manifest_only)
    request = private_request(
        target,
        profile_id="task043-coordinated-save-v1",
        predecessor_sha256=current.project_manifest_sha256,
    )
    assert_error(
        "ERR_PMST_COORDINATED_SAVE_READBACK_INVALID",
        lambda: ProductProjectSaveCoordinator(pmst_router=readback_router).save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            pmst_private_request=request,
        ),
    )
    assert len(readback_port.calls) == 1


def test_enrolled_coordinator_requires_readback_for_a_selected_optional_child(tmp_path: Path) -> None:
    current, target, documents = setup_coordinated_project(tmp_path)
    optional_data = b"selected-optional-child"
    optional_binding = ProjectChildBinding(
        "TASK-043",
        "state/optional.json",
        "bai.test-child",
        "1.0.0",
        sha256_bytes(optional_data),
        False,
    )
    target = manifest(2, *target.child_bindings, optional_binding)
    documents = {**documents, "state/optional.json": optional_data}

    def omit_optional_child(request: ContractRecord) -> None:
        (tmp_path / "state/child.json").write_bytes(documents["state/child.json"])
        AtomicJsonWriter.write(
            tmp_path / ".bai-project/project.json",
            request.to_dict()["intent"]["payload"]["successor_manifest"],
        )

    router, port = active_router(omit_optional_child)
    request = private_request(
        target,
        profile_id="task043-coordinated-save-v1",
        predecessor_sha256=current.project_manifest_sha256,
    )
    assert_error(
        "ERR_PMST_COORDINATED_SAVE_READBACK_INVALID",
        lambda: ProductProjectSaveCoordinator(pmst_router=router).save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            pmst_private_request=request,
        ),
    )
    assert len(port.calls) == 1


def test_semantic_callers_derive_the_router_from_a_supplied_coordinator(tmp_path: Path) -> None:
    setup_coordinated_project(tmp_path)
    router, _ = active_router(lambda request: None)
    coordinator = ProductProjectSaveCoordinator(pmst_router=router)

    audio = Task026AudioPlacementApplication(
        project_root=tmp_path,
        project_id="project-1",
        save_coordinator=coordinator,
    )
    migration = ProductProjectMigrationApplication(
        tmp_path,
        supported_formats=(),
        save_coordinator=coordinator,
    )
    meter = MeterPolicyProjectStore(
        tmp_path,
        "project-1",
        coordinator=coordinator,
    )

    assert audio._pmst_router is router
    assert migration._pmst_router is router
    assert meter._pmst_router is router


def test_semantic_callers_reject_a_split_router_composition(tmp_path: Path) -> None:
    setup_coordinated_project(tmp_path)
    coordinator_router, _ = active_router(lambda request: None)
    explicit_router, _ = active_router(lambda request: None)
    coordinator = ProductProjectSaveCoordinator(pmst_router=coordinator_router)

    with pytest.raises(ProductError) as audio_error:
        Task026AudioPlacementApplication(
            project_root=tmp_path,
            project_id="project-1",
            save_coordinator=coordinator,
            pmst_router=explicit_router,
        )
    assert audio_error.value.code == "ERR_PMST_ROUTER_COMPOSITION_MISMATCH"

    with pytest.raises(ProductError) as migration_error:
        ProductProjectMigrationApplication(
            tmp_path,
            supported_formats=(),
            save_coordinator=coordinator,
            pmst_router=explicit_router,
        )
    assert migration_error.value.code == "ERR_PMST_ROUTER_COMPOSITION_MISMATCH"

    with pytest.raises(MeterPolicyStoreError) as meter_error:
        MeterPolicyProjectStore(
            tmp_path,
            "project-1",
            coordinator=coordinator,
            pmst_router=explicit_router,
        )
    assert meter_error.value.reason == "PMST_ROUTER_COMPOSITION_MISMATCH"


def test_enrolled_legacy_recovery_and_integrity_routes_are_deterministically_unavailable(tmp_path: Path) -> None:
    current, target, documents = setup_coordinated_project(tmp_path)
    router, port = active_router(lambda request: None)
    coordinator = ProductProjectSaveCoordinator(pmst_router=router)
    assert_error(
        "ERR_PMST_ENROLLED_RECOVERY_QUERY_REQUIRED",
        lambda: coordinator.recovery_status(tmp_path),
    )
    assert_error(
        "ERR_PMST_ENROLLED_READ_LEASE_REQUIRED",
        lambda: coordinator.require_current_integrity(tmp_path, current),
    )
    assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: coordinator.recover_complete(tmp_path, transaction_id="save-" + "a" * 64),
    )
    assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: coordinator.recover_rollback(tmp_path, transaction_id="save-" + "a" * 64),
    )
    assert port.calls == []
    assert not ProjectSaveJournalStore.path(tmp_path).exists()


def test_enrolled_participant_path_requires_future_closed_adapter_before_port(tmp_path: Path) -> None:
    current, target, documents = setup_coordinated_project(tmp_path)
    router, port = active_router(lambda request: None)
    request = private_request(
        target,
        profile_id="task043-coordinated-save-v1",
        predecessor_sha256=current.project_manifest_sha256,
    )
    assert_error(
        "ERR_PMST_ENROLLED_PARTICIPANT_ADAPTER_REQUIRED",
        lambda: ProductProjectSaveCoordinator(pmst_router=router).save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            participant=object(),
            pmst_private_request=request,
        ),
    )
    assert port.calls == []
