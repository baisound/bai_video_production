from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading

import pytest

import ai_video_production.montage_learning_file_bridge as file_bridge
from ai_video_production.montage_learning_bridge_application import (
    ExactAdmissionCoordinates,
    GenericObservationCoordinates,
    MontageLearningBridgeApplication,
    MontageLearningBridgeApplicationError,
)
from ai_video_production.montage_learning_bridge_contracts import (
    canonical_learning_sha256,
)
from ai_video_production.montage_learning_canonical_admission_transaction import (
    MontageLearningCanonicalAdmissionTransactionStore,
)
from ai_video_production.montage_learning_file_bridge import (
    BridgeLayout,
    MontageLearningFileBridgeError,
    PRODUCTION_BRIDGE_ROOT,
    claim_delivery,
    load_bridge_owner,
    provision_bridge,
    snapshot_delivery,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import canonical_json_bytes
from test_task058_montage_learning_canonical_admission_transaction import (
    _arguments as _exact_arguments,
    _stage as _stage_exact,
)


def _payload(record_id: str = "observation-001") -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "message_type": "MontageLearningExport",
        "record_id": record_id,
        "source_feedback_id": "feedback-001",
        "proposal_id": "proposal-001",
        "timeline_fps": {"numerator": 60, "denominator": 1},
        "style_profile": "dbd-aggressive",
        "music_context": {"anchor_kind": "DROP"},
        "video_context": {"event_type": "PALLET_DROP"},
        "proposal": {"timeline_frame": 600},
        "human_final": {
            "timeline_frame": 604,
            "status": "moved",
            "provenance": {"actor_role": "owner-editor"},
        },
        "delta_frames": 4,
        "result": "moved",
        "privacy": {
            "safe_export": True,
            "raw_actor_exported": False,
            "redacted_field_paths": [],
        },
        "validation_status": {
            "planning": "PASS",
            "static": "PASS",
            "package": "PASS",
            "runtime": "NOT_RUN",
        },
        "adapter_metadata": {
            "canonical_timeline": False,
            "absolute_host_path_included": False,
        },
    }


def _delivery(record_id: str = "observation-001") -> dict[str, object]:
    payload = _payload(record_id)
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "record_id": record_id,
        "learning_sha256": canonical_learning_sha256(payload),
        "canonical_timeline": False,
        "auto_admit_authorized": False,
        "payload": payload,
    }


def _stage(layout: BridgeLayout, delivery: dict[str, object]) -> Path:
    source_sha256 = delivery.get("learning_sha256", delivery.get("evidence_sha256"))
    assert isinstance(source_sha256, str)
    digest = source_sha256.removeprefix("sha256:")
    path = layout.inbox / f"{delivery['record_id']}--{digest}.json"
    path.write_bytes(canonical_json_bytes(delivery) + b"\n")
    return path


def _layout(tmp_path: Path) -> BridgeLayout:
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    return layout


def _canonical_store(tmp_path: Path) -> MontageLearningCanonicalAdmissionTransactionStore:
    project = tmp_path / "canonical-project"
    anchor = tmp_path / "canonical-anchor"
    project.mkdir()
    anchor.mkdir()
    manifest = ProductProjectManifest.create(
        project_id="proj-test",
        project_revision=1,
        product_version="0.1.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
    )
    ProductProjectManifestStore.save(project, manifest)
    return MontageLearningCanonicalAdmissionTransactionStore(
        project,
        anchor,
        canonical_store_id="task058-file-bridge-canonical",
        bridge_instance_id="bridge-fixture-001",
    )


def _exact_fixture(
    layout: BridgeLayout,
    canonical_store: MontageLearningCanonicalAdmissionTransactionStore,
) -> tuple[Path, dict[str, object], ExactAdmissionCoordinates]:
    delivery, staged = _stage_exact(canonical_store.project_root)
    return (
        _stage(layout, delivery),
        delivery,
        ExactAdmissionCoordinates(**_exact_arguments(staged)),
    )


def _pending_paths(layout: BridgeLayout) -> list[Path]:
    return list(layout.receipts.glob(".*.pending.json"))


def test_provision_is_idempotent_and_never_claims_isolated_root_as_production(tmp_path):
    layout = _layout(tmp_path)
    first = load_bridge_owner(layout)
    second = provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    assert first == second
    assert second.production_path is False
    assert all(
        path.is_dir()
        for path in (
            layout.processing,
            layout.quarantine,
            layout.state,
            layout.import_journal,
        )
    )
    assert layout.root != PRODUCTION_BRIDGE_ROOT
    with pytest.raises(MontageLearningFileBridgeError):
        BridgeLayout(PRODUCTION_BRIDGE_ROOT.parent / "alternate", True)
    with pytest.raises(MontageLearningFileBridgeError):
        BridgeLayout.for_isolated_test(PRODUCTION_BRIDGE_ROOT)


def test_claim_crash_before_snapshot_restarts_from_processing_journal(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery("claim-restart-001")
    staged = _stage(layout, delivery)
    canonical_store = _canonical_store(tmp_path)

    def fail(phase: str, path: Path) -> None:
        if phase == "after_claim_rename_before_snapshot":
            assert path.parent == layout.processing
            raise RuntimeError("crash-after-claim")

    coordinates = GenericObservationCoordinates(expected_revision=0)
    with pytest.raises(RuntimeError, match="crash-after-claim"):
        MontageLearningBridgeApplication(
            layout=layout,
            canonical_port=canonical_store,
            failure_hook=fail,
        ).import_path(staged, generic_coordinates=coordinates)

    assert not staged.exists()
    processing = layout.processing / staged.name
    assert processing.is_file()
    journal_path = next(layout.import_journal.glob("*.import-journal.json"))
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "CLAIMED"
    assert "payload" not in journal
    assert "secret" not in json.dumps(journal).lower()

    results = MontageLearningBridgeApplication(
        layout=layout,
        canonical_port=canonical_store,
    ).import_once(
        generic_coordinates_by_record={delivery["record_id"]: coordinates}
    )

    assert len(results) == 1
    assert results[0].status == "ACCEPTED"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "RECEIPT_PUBLISHED"
    assert processing.is_file()


def test_snapshot_requires_claim_and_records_non_inheritable_pinned_handle(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("pinned-handle-001"))
    claim = claim_delivery(staged, layout)

    snapshot = snapshot_delivery(claim, layout)

    assert snapshot.path == claim.processing_path
    assert snapshot.file_identity == claim.pre_claim_file_identity
    assert snapshot.handle_inheritable is False
    with pytest.raises(MontageLearningFileBridgeError, match="validated delivery claim"):
        snapshot_delivery(claim.processing_path, layout)  # type: ignore[arg-type]


def test_malformed_claim_is_journaled_and_quarantined_before_admission(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("malformed-quarantine-001"))
    staged.write_text(
        '{"record_id":"malformed-quarantine-001",'
        '"record_id":"malformed-quarantine-001"}',
        encoding="utf-8",
    )
    canonical_store = _canonical_store(tmp_path)

    with pytest.raises(MontageLearningFileBridgeError, match="duplicate"):
        MontageLearningBridgeApplication(
            layout=layout,
            canonical_port=canonical_store,
        ).import_path(
            staged,
            generic_coordinates=GenericObservationCoordinates(expected_revision=0),
        )

    quarantined = layout.quarantine / staged.name
    assert quarantined.is_file()
    assert not (layout.processing / staged.name).exists()
    journal_path = next(layout.import_journal.glob("*.import-journal.json"))
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "QUARANTINED"
    assert journal["states"] == [
        "PREPARED",
        "CLAIMED",
        "QUARANTINE_PREPARED",
        "QUARANTINED",
    ]
    assert set(journal).isdisjoint({"payload", "source_delivery", "secret"})
    assert not canonical_store.generic_observation_path.exists()


def test_processing_collision_never_overwrites_or_claims(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("processing-collision-001"))
    collision = layout.processing / staged.name
    collision.write_bytes(b"collision-evidence")

    with pytest.raises(MontageLearningFileBridgeError, match="processing collision"):
        claim_delivery(staged, layout)

    assert staged.is_file()
    assert collision.read_bytes() == b"collision-evidence"
    assert list(layout.import_journal.glob("*.import-journal.json")) == []


def test_claim_rechecks_ancestors_after_rename_durability(tmp_path, monkeypatch):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("claim-post-rename-swap-001"))
    displaced = layout.root / "processing-post-rename-displaced"
    durability_paths: list[Path] = []
    real_directory_fsync = file_bridge._directory_fsync

    def swap_after_durability(path: Path) -> None:
        real_directory_fsync(path)
        durability_paths.append(path)
        if durability_paths == [layout.inbox, layout.processing]:
            layout.processing.rename(displaced)
            layout.processing.mkdir()

    monkeypatch.setattr(file_bridge, "_directory_fsync", swap_after_durability)

    with pytest.raises(MontageLearningFileBridgeError, match="root/ancestor"):
        claim_delivery(staged, layout)

    assert durability_paths == [layout.inbox, layout.processing]
    assert (displaced / staged.name).is_file()
    journal = json.loads(
        next(layout.import_journal.glob("*.import-journal.json")).read_text(
            encoding="utf-8"
        )
    )
    assert journal["state"] == "PREPARED"


def test_quarantine_rechecks_ancestors_after_rename_durability(
    tmp_path, monkeypatch
):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("quarantine-post-rename-swap-001"))
    claim = claim_delivery(staged, layout)
    displaced = layout.root / "quarantine-post-rename-displaced"
    durability_paths: list[Path] = []
    real_directory_fsync = file_bridge._directory_fsync

    def swap_after_durability(path: Path) -> None:
        real_directory_fsync(path)
        durability_paths.append(path)
        if durability_paths == [layout.processing, layout.quarantine]:
            layout.quarantine.rename(displaced)
            layout.quarantine.mkdir()

    monkeypatch.setattr(file_bridge, "_directory_fsync", swap_after_durability)

    with pytest.raises(MontageLearningFileBridgeError, match="root/ancestor"):
        file_bridge.quarantine_claim(claim, layout)

    assert durability_paths == [layout.processing, layout.quarantine]
    assert (displaced / staged.name).is_file()
    journal = json.loads(claim.journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "QUARANTINE_PREPARED"


def test_quarantine_recovery_rechecks_ancestors_after_rename_durability(
    tmp_path, monkeypatch
):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("quarantine-recovery-swap-001"))
    claim = claim_delivery(staged, layout)
    real_atomic_rename = file_bridge._atomic_rename_noreplace

    def interrupt_quarantine_rename(source: Path, destination: Path) -> None:
        raise RuntimeError(f"interrupted before {source.name} -> {destination.name}")

    monkeypatch.setattr(
        file_bridge, "_atomic_rename_noreplace", interrupt_quarantine_rename
    )
    with pytest.raises(RuntimeError, match="interrupted before"):
        file_bridge.quarantine_claim(claim, layout)
    monkeypatch.setattr(file_bridge, "_atomic_rename_noreplace", real_atomic_rename)

    displaced = layout.root / "quarantine-recovery-displaced"
    durability_paths: list[Path] = []
    real_directory_fsync = file_bridge._directory_fsync

    def swap_after_durability(path: Path) -> None:
        real_directory_fsync(path)
        durability_paths.append(path)
        if durability_paths == [layout.processing, layout.quarantine]:
            layout.quarantine.rename(displaced)
            layout.quarantine.mkdir()

    monkeypatch.setattr(file_bridge, "_directory_fsync", swap_after_durability)

    with pytest.raises(MontageLearningFileBridgeError, match="root/ancestor"):
        claim_delivery(staged, layout)

    assert durability_paths == [layout.processing, layout.quarantine]
    assert (displaced / staged.name).is_file()
    journal = json.loads(claim.journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "QUARANTINE_PREPARED"


def test_directory_durability_contract_is_platform_honest(tmp_path):
    missing = tmp_path / "missing-directory"
    if os.name == "nt":
        file_bridge._directory_fsync(missing)
    else:
        with pytest.raises(
            MontageLearningFileBridgeError, match="directory durability failed"
        ):
            file_bridge._directory_fsync(missing)


def test_processing_ancestor_swap_fails_closed_before_canonical_call(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery("ancestor-swap-001"))
    canonical_store = _canonical_store(tmp_path)
    displaced = layout.root / "processing-displaced"

    def swap(phase: str, path: Path) -> None:
        if phase == "after_claim_rename_before_snapshot":
            assert path.is_file()
            layout.processing.rename(displaced)
            layout.processing.mkdir()

    with pytest.raises(MontageLearningBridgeApplicationError, match="RECOVERY_REQUIRED"):
        MontageLearningBridgeApplication(
            layout=layout,
            canonical_port=canonical_store,
            failure_hook=swap,
        ).import_path(
            staged,
            generic_coordinates=GenericObservationCoordinates(expected_revision=0),
        )

    assert (displaced / staged.name).is_file()
    assert not canonical_store.generic_observation_path.exists()
    journal = json.loads(
        next(layout.import_journal.glob("*.import-journal.json")).read_text(
            encoding="utf-8"
        )
    )
    assert journal["state"] == "QUARANTINE_PREPARED"


def test_generic_import_revalidates_commits_and_publishes_matching_v1_receipt(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)
    canonical_store = _canonical_store(tmp_path)
    app = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store
    )

    coordinates = GenericObservationCoordinates(expected_revision=0)
    first = app.import_path(staged, generic_coordinates=coordinates)

    assert first.status == "ACCEPTED"
    assert first.canonical_store_written is True
    assert first.learning_adoption_authorized is False
    assert first.timeline_mutation_authorized is False
    ledger = json.loads(
        canonical_store.generic_observation_path.read_text(encoding="utf-8")
    )
    assert ledger["revision"] == 1
    assert ledger["entries"][0]["record_id"] == delivery["record_id"]
    assert ledger["entries"][0]["learning_sha256"] == delivery["learning_sha256"]
    assert ledger["canonical_store_written"] is True
    assert ledger["learning_adoption_authorized"] is False
    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["record_id"] == delivery["record_id"]
    assert receipt["learning_sha256"] == delivery["learning_sha256"]
    assert receipt["status"] == "ACCEPTED"


def test_generic_durable_a_commit_before_receipt_recovers_as_provable_duplicate(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)
    canonical_store = _canonical_store(tmp_path)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_canonical_commit_before_receipt":
            raise RuntimeError("generic-crash-after-a")

    failed = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store, failure_hook=fail
    )
    coordinates = GenericObservationCoordinates(expected_revision=0)
    with pytest.raises(RuntimeError, match="generic-crash-after-a"):
        failed.import_path(staged, generic_coordinates=coordinates)
    pending_path = _pending_paths(layout)[0]
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert pending["directory_durability_confirmed"] is False
    assert pending["output_receipt_relative_path"].startswith("learning-receipts/")
    assert "payload" not in pending
    assert "source_delivery" not in pending
    assert list(layout.receipts.glob("*.receipt.json")) == []

    restarted = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store
    )
    result = restarted.import_path(staged, generic_coordinates=coordinates)
    ledger = json.loads(canonical_store.generic_observation_path.read_text(encoding="utf-8"))

    assert result.status == "DUPLICATE"
    assert ledger["revision"] == 2
    assert ledger["entries"][-1]["receipt"]["status"] == "DUPLICATE"
    assert ledger["entries"][-1]["receipt"]["duplicate_of_receipt_sha256"]
    assert _pending_paths(layout) == []


def test_existing_generic_receipt_cleans_pending_without_another_ledger_revision(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)
    canonical_store = _canonical_store(tmp_path)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_receipt_publish_before_pending_cleanup":
            raise RuntimeError("generic-crash-after-receipt")

    coordinates = GenericObservationCoordinates(expected_revision=0)
    with pytest.raises(RuntimeError, match="generic-crash-after-receipt"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store, failure_hook=fail
        ).import_path(staged, generic_coordinates=coordinates)
    assert _pending_paths(layout)
    assert list(layout.receipts.glob("*.receipt.json"))

    recovered = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store
    ).import_path(staged, generic_coordinates=coordinates)
    ledger = json.loads(canonical_store.generic_observation_path.read_text(encoding="utf-8"))

    assert recovered.status == "ACCEPTED"
    assert ledger["revision"] == 1
    assert _pending_paths(layout) == []


def test_tampered_pending_rejects_before_recovery_a_call(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery())
    canonical_store = _canonical_store(tmp_path)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_canonical_commit_before_receipt":
            raise RuntimeError("leave-pending")

    coordinates = GenericObservationCoordinates(expected_revision=0)
    with pytest.raises(RuntimeError, match="leave-pending"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store, failure_hook=fail
        ).import_path(staged, generic_coordinates=coordinates)
    pending = _pending_paths(layout)
    assert len(pending) == 1
    pending[0].write_text("{}", encoding="utf-8")

    with pytest.raises(MontageLearningBridgeApplicationError, match="RECOVERY_REQUIRED"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store
        ).import_path(staged, generic_coordinates=coordinates)
    assert list(layout.receipts.glob("*.receipt.json")) == []


def test_generic_revision_leap_requires_recovery_and_does_not_publish_target_receipt(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery("recovery-target-001")
    staged = _stage(layout, delivery)
    canonical_store = _canonical_store(tmp_path)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_canonical_commit_before_receipt":
            raise RuntimeError("leave-generic-pending")

    coordinates = GenericObservationCoordinates(expected_revision=0)
    with pytest.raises(RuntimeError, match="leave-generic-pending"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store, failure_hook=fail
        ).import_path(staged, generic_coordinates=coordinates)
    canonical_store.record_exact_generic_observation(
        _delivery("unrelated-revision-002"), expected_revision=1
    )

    with pytest.raises(MontageLearningBridgeApplicationError, match="RECOVERY_REQUIRED"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store
        ).import_path(staged, generic_coordinates=coordinates)
    assert list(layout.receipts.glob("recovery-target-001--*.receipt.json")) == []


def test_exact_a_commit_before_receipt_uses_trusted_reader_to_publish_matching_v2(tmp_path):
    layout = _layout(tmp_path)
    canonical_store = _canonical_store(tmp_path)
    staged, delivery, coordinates = _exact_fixture(layout, canonical_store)

    def fail(phase: str, path: Path) -> None:
        del path
        if phase == "after_canonical_commit_before_receipt":
            raise RuntimeError("exact-crash-after-a")

    with pytest.raises(RuntimeError, match="exact-crash-after-a"):
        MontageLearningBridgeApplication(
            layout=layout, canonical_port=canonical_store, failure_hook=fail
        ).import_path(staged, exact_coordinates=coordinates)
    assert _pending_paths(layout)
    assert list(layout.receipts.glob("*.admission-v2.json")) == []

    recovered = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store
    ).import_path(staged, exact_coordinates=coordinates)
    receipt = json.loads(recovered.receipt_path.read_text(encoding="utf-8"))

    assert recovered.status == "ACCEPTED"
    assert receipt["source_record_id"] == delivery["record_id"]
    assert receipt["source_sha256"] == delivery["evidence_sha256"]
    assert canonical_store.get_verified_receipt(
        receipt_sha256=receipt["receipt_sha256"]
    ).to_public_projection()["canonical_currentness_verified"] is True
    assert _pending_paths(layout) == []


def test_tightly_concurrent_exact_and_generic_publish_both_and_keep_exact_current(tmp_path):
    layout = _layout(tmp_path)
    canonical_store = _canonical_store(tmp_path)
    exact_path, _exact_delivery, exact_coordinates = _exact_fixture(layout, canonical_store)
    generic_path = _stage(layout, _delivery("concurrent-generic-001"))
    generic_coordinates = GenericObservationCoordinates(expected_revision=0)
    exact_committed = threading.Event()
    publish_barrier = threading.Barrier(2)

    def synchronize(phase: str, path: Path) -> None:
        del path
        if phase == "after_canonical_commit_before_receipt":
            exact_committed.set()
            publish_barrier.wait(timeout=10)

    app = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store, failure_hook=synchronize
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        exact_future = executor.submit(
            app.import_path, exact_path, exact_coordinates=exact_coordinates
        )
        assert exact_committed.wait(timeout=10)
        generic_future = executor.submit(
            app.import_path, generic_path, generic_coordinates=generic_coordinates
        )
        exact_result = exact_future.result(timeout=20)
        generic_result = generic_future.result(timeout=20)
    assert exact_result.receipt_path.is_file()
    assert generic_result.receipt_path.is_file()
    exact_receipt = json.loads(exact_result.receipt_path.read_text(encoding="utf-8"))
    assert canonical_store.get_verified_receipt(
        receipt_sha256=exact_receipt["receipt_sha256"]
    ).to_public_projection()["canonical_currentness_verified"] is True


def test_missing_generic_coordinates_raise_without_publishing_receipt(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery())
    canonical_store = _canonical_store(tmp_path)
    app = MontageLearningBridgeApplication(
        layout=layout,
        canonical_port=canonical_store,
    )
    with pytest.raises(MontageLearningBridgeApplicationError, match="generic delivery"):
        app.import_path(staged)
    assert list(layout.receipts.glob("*.receipt.json")) == []


def test_snapshot_rejects_filename_body_digest_malformed_duplicate_and_oversize(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)

    wrong = layout.inbox / f"other--{str(delivery['learning_sha256'])[7:]}.json"
    staged.replace(wrong)
    with pytest.raises(MontageLearningFileBridgeError, match="record_id"):
        snapshot_delivery(claim_delivery(wrong, layout), layout)

    malformed = layout.inbox / ("bad--" + "a" * 64 + ".json")
    malformed.write_text('{"record_id":"bad","record_id":"bad"}', encoding="utf-8")
    with pytest.raises(MontageLearningFileBridgeError, match="duplicate"):
        snapshot_delivery(claim_delivery(malformed, layout), layout)

    oversized = layout.inbox / ("huge--" + "b" * 64 + ".json")
    with oversized.open("wb") as handle:
        handle.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(MontageLearningFileBridgeError, match="size"):
        snapshot_delivery(claim_delivery(oversized, layout), layout)


def test_symlink_delivery_and_owner_manifest_collision_fail_closed(tmp_path):
    layout = _layout(tmp_path)
    if hasattr(os, "symlink"):
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = layout.inbox / ("linked--" + "a" * 64 + ".json")
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation not available")
        with pytest.raises(MontageLearningFileBridgeError):
            claim_delivery(link, layout)

    manifest = json.loads(layout.owner_manifest.read_text(encoding="utf-8"))
    manifest["bridge_instance_id"] = "other-owner"
    layout.owner_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(MontageLearningFileBridgeError):
        provision_bridge(layout, bridge_instance_id="bridge-fixture-001")


def test_exact_and_generic_lanes_never_silently_mix(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    delivery["message_type"] = "BvpMontageExactEvidenceDelivery"
    path = layout.inbox / (
        f"{delivery['record_id']}--{str(delivery['learning_sha256'])[7:]}.json"
    )
    path.write_bytes(canonical_json_bytes(delivery) + b"\n")
    app = MontageLearningBridgeApplication(
        layout=layout, canonical_port=_canonical_store(tmp_path)
    )
    with pytest.raises((MontageLearningFileBridgeError, MontageLearningBridgeApplicationError)):
        app.import_path(path)
