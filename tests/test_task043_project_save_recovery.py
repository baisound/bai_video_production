from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.errors import ProductError
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import (
    ProductProjectSaveCoordinator,
    ProjectSaveJournalStore,
    ProjectSaveState,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


CREATED = "2026-08-15T00:00:00.000Z"
UPDATED = "2026-08-15T00:01:00.000Z"


def binding(path: str, data: bytes, *, owner: str = "TASK-037", required: bool = True) -> ProjectChildBinding:
    return ProjectChildBinding(owner, path, "bai.test-child", "1.0.0", sha256_bytes(data), required)


def project_manifest(revision: int, *bindings: ProjectChildBinding) -> ProductProjectManifest:
    return ProductProjectManifest.create(
        project_id="project-1",
        project_revision=revision,
        product_version="0.20.1",
        timebase=ProjectTimebase(30, 1),
        child_bindings=bindings,
        created_at=CREATED,
        updated_at=CREATED if revision == 1 else UPDATED,
    )


def setup_project(root: Path, *, second_child: bool = False):
    first_path = root / "state/first.json"
    first_path.parent.mkdir()
    first_path.write_bytes(b"old-first")
    current_bindings = [binding("state/first.json", b"old-first")]
    target_bindings = [binding("state/first.json", b"new-first")]
    documents = {"state/first.json": b"new-first"}
    if second_child:
        second_path = root / "state/second.json"
        second_path.write_bytes(b"old-second")
        current_bindings.append(binding("state/second.json", b"old-second", owner="TASK-041"))
        target_bindings.append(binding("state/second.json", b"new-second", owner="TASK-041"))
        documents["state/second.json"] = b"new-second"
    current = project_manifest(1, *current_bindings)
    target = project_manifest(2, *target_bindings)
    ProductProjectManifestStore.save(root, current)
    return current, target, documents


def fail_once_at(stage_name: str):
    fired = False

    def inject(stage: str, _root: Path) -> None:
        nonlocal fired
        if stage == stage_name and not fired:
            fired = True
            raise RuntimeError(f"injected:{stage}")

    return inject


def test_journal_schema_is_valid_and_packaged_copy_is_exact() -> None:
    public = Path(__file__).parents[1] / "schemas/project-save-journal.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    Draft202012Validator.check_schema(json.loads(public.read_text(encoding="utf-8")))


def test_coordinated_save_commits_children_before_manifest_and_is_reopenable(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    result = ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    assert result == target
    assert (tmp_path / "state/first.json").read_bytes() == b"new-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"new-second"
    assert ProductProjectManifestStore.load(tmp_path) == target
    journal = ProjectSaveJournalStore.load(tmp_path)
    assert journal.state is ProjectSaveState.COMMITTED
    assert all(entry.committed for entry in journal.entries)
    assert ProductProjectSaveCoordinator().recovery_status(tmp_path)["required"] is False


def test_failure_after_first_child_requires_recovery_and_keeps_old_manifest(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError, match="injected"):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    assert ProductProjectManifestStore.load(tmp_path) == current
    status = coordinator.recovery_status(tmp_path)
    assert status["required"] is True
    assert set(status["available_actions"]) == {"COMPLETE", "ROLLBACK"}
    with pytest.raises(ProductError) as admission:
        ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    assert admission.value.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED"


def test_current_integrity_rejects_manifest_bound_child_drift(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    (tmp_path / "state/first.json").write_bytes(b"tampered")
    with pytest.raises(ProductError) as rejected:
        ProductProjectSaveCoordinator().require_current_integrity(tmp_path, current)
    assert rejected.value.code == "ERR_PROJECT_SAVE_RECOVERY_TARGET_CONFLICT"


def test_recovery_complete_finishes_same_transaction_without_duplicate_write(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    transaction_id = coordinator.recovery_status(tmp_path)["transaction_id"]
    result = ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=transaction_id)
    assert result == target
    assert ProductProjectManifestStore.load(tmp_path) == target
    assert (tmp_path / "state/first.json").read_bytes() == b"new-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"new-second"


def test_recovery_rollback_restores_every_previous_child(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path, second_child=True)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    transaction_id = coordinator.recovery_status(tmp_path)["transaction_id"]
    result = ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=transaction_id)
    assert result == current
    assert ProductProjectManifestStore.load(tmp_path) == current
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"
    assert (tmp_path / "state/second.json").read_bytes() == b"old-second"
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.ABANDONED


def test_failure_after_manifest_commit_offers_finalize_only(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_manifest_commit"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    assert status["available_actions"] == ["FINALIZE"]
    assert ProductProjectManifestStore.load(tmp_path) == target
    ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=status["transaction_id"])
    assert ProjectSaveJournalStore.load(tmp_path).state is ProjectSaveState.COMMITTED


def test_finalize_revalidates_every_target_child(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_manifest_commit"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    (tmp_path / "state/first.json").write_bytes(b"changed-after-commit")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=status["transaction_id"])
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_TARGET_CONFLICT"


def test_new_save_is_blocked_while_recovery_is_pending(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_staged"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_REQUIRED"


def test_preflight_rejects_unbound_child_without_creating_journal(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    documents["state/unbound.json"] = b"unbound"
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_UNBOUND_CHILD"
    assert not ProjectSaveJournalStore.path(tmp_path).exists()


def test_preflight_rejects_target_checksum_mismatch(tmp_path: Path) -> None:
    current, target, _documents = setup_project(tmp_path)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            {"state/first.json": b"wrong"},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_CHILD_CHECKSUM"


def test_preflight_rejects_source_child_drift(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    (tmp_path / "state/first.json").write_bytes(b"human-change")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_SOURCE_CHILD_CONFLICT"


def test_removing_existing_binding_requires_explicit_migration(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path, second_child=True)
    target = project_manifest(2, binding("state/first.json", b"old-first"))
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().save(
            tmp_path,
            target,
            {},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_BINDING_REMOVAL_REQUIRES_MIGRATION"


def test_recovery_rollback_removes_new_child_that_did_not_exist_before(tmp_path: Path) -> None:
    current, _target, _documents = setup_project(tmp_path)
    new_binding = binding("state/new.json", b"new-child", owner="TASK-041")
    target = project_manifest(2, *current.child_bindings, new_binding)
    documents = {"state/new.json": b"new-child"}
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    assert (tmp_path / "state/new.json").exists()
    status = coordinator.recovery_status(tmp_path)
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=status["transaction_id"])
    assert not (tmp_path / "state/new.json").exists()
    assert ProductProjectManifestStore.load(tmp_path) == current


def test_tampered_staging_blocks_complete_but_valid_backup_allows_rollback(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_validated"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    journal = ProjectSaveJournalStore.load(tmp_path)
    staged = tmp_path / ".bai-project" / journal.entries[0].staged_relative_path
    staged.write_bytes(b"tampered")
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id=journal.transaction_id)
    assert exc.value.code == "ERR_PROJECT_SAVE_STAGING_INVALID"
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=journal.transaction_id)
    assert (tmp_path / "state/first.json").read_bytes() == b"old-first"


def test_wrong_recovery_identity_is_rejected(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_journal_staged"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    with pytest.raises(ProductError) as exc:
        ProductProjectSaveCoordinator().recover_complete(tmp_path, transaction_id="save-" + "f" * 64)
    assert exc.value.code == "ERR_PROJECT_SAVE_RECOVERY_IDENTITY"


def test_journal_checksum_tampering_is_detected(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    path = ProjectSaveJournalStore.path(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["journal_revision"] += 1
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProjectSaveJournalStore.load(tmp_path)
    assert exc.value.code == "ERR_PROJECT_SAVE_JOURNAL_INVALID"


def test_journal_cannot_redirect_staging_path_outside_transaction_scope(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    path = ProjectSaveJournalStore.path(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["entries"][0]["staged_relative_path"] = "save-journal.json"
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    value["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        ProjectSaveJournalStore.load(tmp_path)
    assert exc.value.code == "ERR_PROJECT_SAVE_JOURNAL_INVALID"


def test_retry_after_rollback_reuses_identical_staging_safely(tmp_path: Path) -> None:
    current, target, documents = setup_project(tmp_path)
    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_once_at("after_child_replace"))
    with pytest.raises(RuntimeError):
        coordinator.save(tmp_path, target, documents, expected_previous_manifest_sha256=current.project_manifest_sha256)
    status = coordinator.recovery_status(tmp_path)
    ProductProjectSaveCoordinator().recover_rollback(tmp_path, transaction_id=status["transaction_id"])
    ProductProjectSaveCoordinator().save(
        tmp_path,
        target,
        documents,
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    assert ProductProjectManifestStore.load(tmp_path) == target
