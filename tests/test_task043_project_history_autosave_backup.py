from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_history import (
    ProductProjectAutosaveCoordinator,
    ProductProjectBackupStore,
    ProjectAutosavePolicy,
    ProjectCommandAction,
    ProjectCommandHistory,
    ProjectCommandHistoryStore,
    parse_project_command_history,
)
from ai_video_production.project_save import ProductProjectSaveCoordinator
from ai_video_production.serialization import sha256_bytes


CREATED = "2026-08-15T00:00:00.000Z"


def checksum(label: str) -> str:
    return sha256_bytes(label.encode())


def binding(data: bytes, *, path: str = "state/project.json", owner: str = "TASK-037") -> ProjectChildBinding:
    return ProjectChildBinding(owner, path, "bai.test-child", "1.0.0", sha256_bytes(data), True)


def manifest(revision: int, data: bytes, *, path: str = "state/project.json", owner: str = "TASK-037") -> ProductProjectManifest:
    return ProductProjectManifest.create(
        project_id="project-1", project_revision=revision, product_version="0.20.1",
        timebase=ProjectTimebase(30, 1), child_bindings=(binding(data, path=path, owner=owner),),
        created_at=CREATED, updated_at=f"2026-08-15T00:0{min(revision, 9)}:00.000Z",
    )


def setup_project(root: Path, data: bytes = b"one") -> ProductProjectManifest:
    child = root / "state/project.json"
    child.parent.mkdir()
    child.write_bytes(data)
    current = manifest(1, data)
    ProductProjectManifestStore.save(root, current)
    return current


def save_revision(root: Path, current: ProductProjectManifest, data: bytes) -> ProductProjectManifest:
    target = manifest(current.project_revision + 1, data)
    return ProductProjectSaveCoordinator().save(
        root, target, {"state/project.json": data},
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )


def test_history_schema_is_valid_and_packaged_copy_is_exact() -> None:
    public = Path(__file__).parents[1] / "schemas/project-command-history.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(ProjectCommandHistory.create("project-1").to_dict())


def test_history_is_append_only_and_supports_compensating_undo_redo() -> None:
    history = ProjectCommandHistory.create("project-1")
    history = history.append_apply(
        command_kind="timeline.trim", target_identity="clip:1",
        source_manifest_sha256=checksum("m1"), result_manifest_sha256=checksum("m2"),
        source_revision=1, stale_target_ids=("asset:2",), recorded_at=CREATED,
    )
    applied = history.records[0]
    history = history.append_undo(
        source_manifest_sha256=checksum("m2"), result_manifest_sha256=checksum("m3"),
        source_revision=2, recorded_at="2026-08-15T00:01:00.000Z",
    )
    assert history.records[1].action is ProjectCommandAction.UNDO
    assert history.records[1].compensates_record_id == applied.record_id
    assert history.undo_candidate() is None
    assert history.redo_candidate() == applied
    history = history.append_redo(
        source_manifest_sha256=checksum("m3"), result_manifest_sha256=checksum("m4"),
        source_revision=3, recorded_at="2026-08-15T00:02:00.000Z",
    )
    assert len(history.records) == 3
    assert history.records[2].compensates_record_id == history.records[1].record_id
    assert history.undo_candidate() == history.records[2]
    assert parse_project_command_history(history.to_dict()) == history


def test_new_command_after_undo_preserves_records_and_invalidates_redo() -> None:
    history = ProjectCommandHistory.create("project-1").append_apply(
        command_kind="timeline.trim", target_identity="clip:1",
        source_manifest_sha256=checksum("m1"), result_manifest_sha256=checksum("m2"), source_revision=1,
    ).append_undo(
        source_manifest_sha256=checksum("m2"), result_manifest_sha256=checksum("m3"), source_revision=2,
    ).append_apply(
        command_kind="timeline.move", target_identity="clip:2",
        source_manifest_sha256=checksum("m3"), result_manifest_sha256=checksum("m4"), source_revision=3,
    )
    assert len(history.records) == 3
    assert history.redo_candidate() is None
    with pytest.raises(ProductError) as exc:
        history.append_redo(source_manifest_sha256=checksum("m4"), result_manifest_sha256=checksum("m5"), source_revision=4)
    assert exc.value.code == "ERR_PROJECT_HISTORY_REDO_EMPTY"


def test_history_store_requires_exact_cas(tmp_path: Path) -> None:
    history = ProjectCommandHistory.create("project-1")
    ProjectCommandHistoryStore.save(tmp_path, history)
    changed = history.append_apply(
        command_kind="timeline.trim", target_identity="clip:1",
        source_manifest_sha256=checksum("m1"), result_manifest_sha256=checksum("m2"), source_revision=1,
    )
    with pytest.raises(ProductError) as exc:
        ProjectCommandHistoryStore.save(tmp_path, changed, expected_previous_history_sha256=checksum("wrong"))
    assert exc.value.code == "ERR_PROJECT_HISTORY_CAS_CONFLICT"
    ProjectCommandHistoryStore.save(tmp_path, changed, expected_previous_history_sha256=history.history_sha256)
    assert ProjectCommandHistoryStore.load(tmp_path) == changed


def test_autosave_waits_for_quiescence_then_commits_and_snapshots(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    target = manifest(2, b"two")
    coordinator = ProductProjectAutosaveCoordinator(ProjectAutosavePolicy(debounce_seconds=30, quiescence_seconds=5, max_snapshots=2))
    skipped = coordinator.autosave(
        tmp_path, target, {"state/project.json": b"two"},
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        last_edit_at="2026-08-15T00:00:58.000Z", now="2026-08-15T00:01:00.000Z",
    )
    assert skipped.state == "SKIPPED_NOT_QUIESCENT"
    result = coordinator.autosave(
        tmp_path, target, {"state/project.json": b"two"},
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        last_edit_at="2026-08-15T00:00:50.000Z", now="2026-08-15T00:01:00.000Z",
    )
    assert result.state == "SAVED"
    assert result.snapshot_path is not None and result.snapshot_path.is_file()
    assert ProductProjectManifestStore.load(tmp_path) == target


def test_autosave_debounce_does_not_mutate_project(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    target = manifest(2, b"two")
    result = ProductProjectAutosaveCoordinator().autosave(
        tmp_path, target, {"state/project.json": b"two"},
        expected_previous_manifest_sha256=current.project_manifest_sha256,
        last_edit_at="2026-08-15T00:00:00.000Z", previous_autosave_at="2026-08-15T00:00:50.000Z",
        now="2026-08-15T00:01:00.000Z",
    )
    assert result.state == "SKIPPED_DEBOUNCE"
    assert ProductProjectManifestStore.load(tmp_path) == current


def test_autosave_retention_is_bounded(tmp_path: Path) -> None:
    current = setup_project(tmp_path)
    coordinator = ProductProjectAutosaveCoordinator(ProjectAutosavePolicy(max_snapshots=2))
    for revision, data, minute in ((2, b"two", 2), (3, b"three", 3), (4, b"four", 4)):
        target = manifest(revision, data)
        result = coordinator.autosave(
            tmp_path, target, {"state/project.json": data},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            last_edit_at=f"2026-08-15T00:0{minute - 1}:00.000Z",
            now=f"2026-08-15T00:0{minute}:00.000Z",
        )
        assert result.state == "SAVED"
        current = target
    snapshots = list((tmp_path / ".bai-project/autosave").glob("autosave-*.json"))
    assert len(snapshots) == 2


def test_autosave_rejects_private_binding(tmp_path: Path) -> None:
    root = tmp_path
    path = root / "state/credential-vault.json"
    path.parent.mkdir()
    path.write_bytes(b"old")
    current = manifest(1, b"old", path="state/credential-vault.json", owner="TASK-034")
    ProductProjectManifestStore.save(root, current)
    target = manifest(2, b"new", path="state/credential-vault.json", owner="TASK-034")
    with pytest.raises(ProductError) as exc:
        ProductProjectAutosaveCoordinator().autosave(
            root, target, {"state/credential-vault.json": b"new"},
            expected_previous_manifest_sha256=current.project_manifest_sha256,
            last_edit_at="2026-08-15T00:00:00.000Z", now="2026-08-15T00:01:00.000Z",
        )
    assert exc.value.code == "ERR_PROJECT_SNAPSHOT_PRIVATE_BINDING"


def test_backup_preview_and_restore_use_new_cas_transaction(tmp_path: Path) -> None:
    first = setup_project(tmp_path)
    backup_id = ProductProjectBackupStore.create(tmp_path)
    second = save_revision(tmp_path, first, b"two")
    preview = ProductProjectBackupStore.preview_restore(tmp_path, backup_id)
    assert (preview.backup_revision, preview.current_revision) == (1, 2)
    restored = ProductProjectBackupStore.restore(
        tmp_path, backup_id, expected_current_manifest_sha256=second.project_manifest_sha256,
    )
    assert restored.project_revision == 3
    assert (tmp_path / "state/project.json").read_bytes() == b"one"
    assert restored.child_bindings[0].content_sha256 == first.child_bindings[0].content_sha256


def test_backup_restore_conflict_is_a_human_gate(tmp_path: Path) -> None:
    setup_project(tmp_path)
    backup_id = ProductProjectBackupStore.create(tmp_path)
    with pytest.raises(ProductError) as exc:
        ProductProjectBackupStore.restore(tmp_path, backup_id, expected_current_manifest_sha256=checksum("stale"))
    assert exc.value.code == "ERR_PROJECT_BACKUP_RESTORE_CONFLICT"
    assert exc.value.category is ProductErrorCategory.HUMAN_REVIEW_REQUIRED


def test_tampered_backup_child_is_rejected(tmp_path: Path) -> None:
    setup_project(tmp_path)
    backup_id = ProductProjectBackupStore.create(tmp_path)
    child = tmp_path / ".bai-project/backups" / backup_id / "children/state/project.json"
    child.write_bytes(b"tampered")
    with pytest.raises(ProductError) as exc:
        ProductProjectBackupStore.preview_restore(tmp_path, backup_id)
    assert exc.value.code == "ERR_PROJECT_BACKUP_INVALID"


def test_backup_retention_is_bounded(tmp_path: Path) -> None:
    first = setup_project(tmp_path)
    first_id = ProductProjectBackupStore.create(tmp_path, max_backups=1, created_at="2026-08-15T00:00:00.000Z")
    second = save_revision(tmp_path, first, b"two")
    second_id = ProductProjectBackupStore.create(tmp_path, max_backups=1, created_at="2026-08-15T00:01:00.000Z")
    assert first_id != second_id
    backups = list((tmp_path / ".bai-project/backups").glob("backup-*"))
    assert [path.name for path in backups] == [second_id]
