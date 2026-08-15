from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.product_project import (
    ProductProjectManifest,
    ProjectChildBinding,
    ProjectTimebase,
)
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_history import ProductProjectBackupStore
from ai_video_production.project_migration import (
    MigrationRegistry,
    MigrationTransformer,
    MigrationTransformerRegistry,
    MigrationTransition,
    SupportedFormatRange,
)
from ai_video_production.project_migration_application import (
    LegacyProjectBindingRule,
    ProductProjectMigrationApplication,
)
from ai_video_production.project_save import ProductProjectSaveCoordinator
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


FIXTURES = Path(__file__).parent / "fixtures" / "task045"
CREATED = "2026-08-15T00:00:00.000Z"
FORMAT_ID = "bai.production-control"
RULE = LegacyProjectBindingRule(
    domain_owner="TASK-037",
    relative_path="state/production-control.json",
    format_id=FORMAT_ID,
    format_version="1.0.0",
)
SUPPORTED = (SupportedFormatRange(FORMAT_ID, "1.0.0", "1.0.0", "1.0.0"),)


def copy_fixture(root: Path, name: str) -> Path:
    project = root / name
    shutil.copytree(FIXTURES / name, project)
    return project


def old_to_current(source: bytes) -> bytes:
    value = json.loads(source.decode("utf-8"))
    if set(value) != {"format_version", "items", "owner"} or value["format_version"] != "0.9.0":
        raise ValueError("unexpected legacy production-control document")
    return canonical_json_bytes(
        {
            "format_version": "1.0.0",
            "items": value["items"],
            "owner": value["owner"],
            "migration": "LOSSLESS_0_9_TO_1_0",
        }
    )


def validate_current(source: bytes) -> None:
    value = json.loads(source.decode("utf-8"))
    if set(value) != {"format_version", "items", "owner", "migration"}:
        raise ValueError("current production-control fields are not exact")
    if value["format_version"] != "1.0.0" or value["migration"] != "LOSSLESS_0_9_TO_1_0":
        raise ValueError("current production-control identity is invalid")


def migration_components():
    transition = MigrationTransition(FORMAT_ID, "0.9.0", "1.0.0", True, False)
    migrations = MigrationRegistry((transition,))
    transformers = MigrationTransformerRegistry(
        (
            MigrationTransformer(
                transition=transition,
                transformer_id="task045.production-control-v1",
                transform=old_to_current,
                validate_target=validate_current,
            ),
        )
    )
    return migrations, transformers


def setup_migration_project(root: Path) -> tuple[Path, ProductProjectManifest, bytes]:
    project = copy_fixture(root, "migration-090")
    child = project / "state" / "production-control.json"
    source = child.read_bytes()
    manifest = ProductProjectManifest.create(
        project_id="migration-project",
        project_revision=1,
        product_version="0.20.1",
        timebase=ProjectTimebase(30000, 1001),
        child_bindings=(
            ProjectChildBinding(
                "TASK-037",
                "state/production-control.json",
                FORMAT_ID,
                "0.9.0",
                sha256_bytes(source),
                True,
            ),
        ),
        created_at=CREATED,
        updated_at=CREATED,
    )
    ProductProjectManifestStore.save(project, manifest)
    return project, manifest, source


def test_explicit_legacy_discovery_import_and_reopen_are_idempotent(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path, "legacy-v0201")
    application = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        token_factory=lambda: "legacy-confirmation",
    )

    prepared = application.prepare_legacy_import(
        project_id="legacy-project",
        product_version="0.20.1",
        timebase=ProjectTimebase(30000, 1001),
        rules=(RULE,),
    )

    assert prepared["store_write_performed"] is False
    assert not (project / ".bai-project" / "project.json").exists()
    result = application.apply_legacy_import(confirmation_id=prepared["confirmation_id"])
    reopened = ProductProjectManifestStore.load(project)
    assert result["project_manifest_sha256"] == reopened.project_manifest_sha256
    assert reopened.project_revision == 1
    assert reopened.child_bindings[0].format_version == "1.0.0"
    assert application.apply_legacy_import(confirmation_id=prepared["confirmation_id"]) == result


def test_legacy_import_revalidates_bytes_and_never_writes_stale_preview(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path, "legacy-v0201")
    application = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        token_factory=lambda: "legacy-stale",
    )
    prepared = application.prepare_legacy_import(
        project_id="legacy-project",
        product_version="0.20.1",
        timebase=ProjectTimebase(24, 1),
        rules=(RULE,),
    )
    (project / RULE.relative_path).write_text("changed", encoding="utf-8")

    with pytest.raises(ProductError) as exc:
        application.apply_legacy_import(confirmation_id=prepared["confirmation_id"])

    assert exc.value.code == "ERR_PROJECT_LEGACY_PREVIEW_STALE"
    assert not (project / ".bai-project" / "project.json").exists()


def test_legacy_unknown_newer_format_fails_closed_without_manifest(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path, "legacy-v0201")
    newer = LegacyProjectBindingRule(
        "TASK-037", RULE.relative_path, FORMAT_ID, "2.0.0", True
    )
    application = ProductProjectMigrationApplication(project, supported_formats=SUPPORTED)

    with pytest.raises(ProductError) as exc:
        application.prepare_legacy_import(
            project_id="legacy-project",
            product_version="0.20.1",
            timebase=ProjectTimebase(24, 1),
            rules=(newer,),
        )

    assert exc.value.code == "ERR_PROJECT_LEGACY_COMPATIBILITY_BLOCKED"
    assert not (project / ".bai-project" / "project.json").exists()


def test_legacy_symlink_child_is_rejected_without_write(tmp_path: Path) -> None:
    project = tmp_path / "legacy-link"
    project.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    target = project / RULE.relative_path
    target.parent.mkdir()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    application = ProductProjectMigrationApplication(project, supported_formats=SUPPORTED)

    with pytest.raises(ProductError) as exc:
        application.prepare_legacy_import(
            project_id="legacy-project",
            product_version="0.20.1",
            timebase=ProjectTimebase(24, 1),
            rules=(RULE,),
        )

    assert exc.value.code == "ERR_PROJECT_LEGACY_CHILD_INVALID"
    assert not (project / ".bai-project" / "project.json").exists()


def test_lossless_copy_on_write_migration_reopen_backup_restore_roundtrip(tmp_path: Path) -> None:
    project, source_manifest, source_bytes = setup_migration_project(tmp_path)
    migrations, transformers = migration_components()
    application = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        migration_registry=migrations,
        transformer_registry=transformers,
        token_factory=lambda: "migration-confirmation",
    )

    prepared = application.prepare_lossless_migration()
    assert prepared["store_write_performed"] is False
    assert not (project / ".bai-project" / "backups").exists()
    result = application.apply_lossless_migration(confirmation_id=prepared["confirmation_id"])

    migrated = ProductProjectManifestStore.load(project)
    assert result["reopen_verified"] is True
    assert migrated.project_revision == 2
    assert migrated.child_bindings[0].format_version == "1.0.0"
    assert (project / RULE.relative_path).read_bytes() == old_to_current(source_bytes)
    assert application.apply_lossless_migration(confirmation_id=prepared["confirmation_id"]) == result

    preview = ProductProjectBackupStore.preview_restore(project, result["backup_id"])
    restored = ProductProjectBackupStore.restore(
        project,
        result["backup_id"],
        expected_current_manifest_sha256=preview.current_manifest_sha256,
    )
    assert restored.project_revision == 3
    assert restored.child_bindings[0].format_version == "0.9.0"
    assert (project / RULE.relative_path).read_bytes() == source_bytes
    assert source_manifest.project_manifest_sha256 == preview.backup_manifest_sha256


def test_migration_missing_transformer_and_invalid_target_never_write(tmp_path: Path) -> None:
    project, manifest, source_bytes = setup_migration_project(tmp_path)
    transition = MigrationTransition(FORMAT_ID, "0.9.0", "1.0.0", True, False)
    missing = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        migration_registry=MigrationRegistry((transition,)),
    )
    with pytest.raises(ProductError) as exc:
        missing.prepare_lossless_migration()
    assert exc.value.code == "ERR_PROJECT_MIGRATION_TRANSFORMER_MISSING"

    invalid_registry = MigrationTransformerRegistry(
        (
            MigrationTransformer(
                transition,
                "task045.invalid-target",
                lambda _: b"not-json",
                validate_current,
            ),
        )
    )
    invalid = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        migration_registry=MigrationRegistry((transition,)),
        transformer_registry=invalid_registry,
    )
    with pytest.raises(ProductError) as invalid_exc:
        invalid.prepare_lossless_migration()
    assert invalid_exc.value.code == "ERR_PROJECT_MIGRATION_TARGET_INVALID"
    assert ProductProjectManifestStore.load(project) == manifest
    assert (project / RULE.relative_path).read_bytes() == source_bytes
    assert not (project / ".bai-project" / "backups").exists()


def test_interrupted_migration_uses_existing_recovery_without_replay(tmp_path: Path) -> None:
    project, manifest, source_bytes = setup_migration_project(tmp_path)
    migrations, transformers = migration_components()

    def fail_after_validation(stage: str, _root: Path) -> None:
        if stage == "after_journal_validated":
            raise RuntimeError("injected interruption")

    coordinator = ProductProjectSaveCoordinator(failure_injector=fail_after_validation)
    application = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        migration_registry=migrations,
        transformer_registry=transformers,
        save_coordinator=coordinator,
        token_factory=lambda: "migration-interrupted",
    )
    prepared = application.prepare_lossless_migration()

    with pytest.raises(RuntimeError, match="injected"):
        application.apply_lossless_migration(confirmation_id=prepared["confirmation_id"])

    status = coordinator.recovery_status(project)
    assert status["required"] is True
    assert set(status["available_actions"]) == {"COMPLETE", "ROLLBACK"}
    coordinator.recover_rollback(project, transaction_id=status["transaction_id"])
    assert ProductProjectManifestStore.load(project) == manifest
    assert (project / RULE.relative_path).read_bytes() == source_bytes


def test_migration_rejects_ambiguous_duplicate_dependency_hash_before_write(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path, "migration-090")
    first = project / "state" / "production-control.json"
    duplicate = project / "state" / "duplicate.json"
    dependent = project / "state" / "dependent.json"
    duplicate.write_bytes(first.read_bytes())
    dependent.write_text('{"format_version":"1.0.0"}', encoding="utf-8")
    source_hash = sha256_bytes(first.read_bytes())
    manifest = ProductProjectManifest.create(
        project_id="ambiguous-dependency-project",
        project_revision=1,
        product_version="0.20.1",
        timebase=ProjectTimebase(24, 1),
        child_bindings=(
            ProjectChildBinding("TASK-037", "state/production-control.json", FORMAT_ID, "0.9.0", source_hash, True),
            ProjectChildBinding("TASK-038", "state/duplicate.json", FORMAT_ID, "1.0.0", source_hash, True),
            ProjectChildBinding(
                "TASK-039",
                "state/dependent.json",
                FORMAT_ID,
                "1.0.0",
                sha256_bytes(dependent.read_bytes()),
                True,
                (source_hash,),
            ),
        ),
        created_at=CREATED,
        updated_at=CREATED,
    )
    ProductProjectManifestStore.save(project, manifest)
    migrations, transformers = migration_components()
    application = ProductProjectMigrationApplication(
        project,
        supported_formats=SUPPORTED,
        migration_registry=migrations,
        transformer_registry=transformers,
        token_factory=lambda: "ambiguous-dependency",
    )
    prepared = application.prepare_lossless_migration()

    with pytest.raises(ProductError) as exc:
        application.apply_lossless_migration(confirmation_id=prepared["confirmation_id"])

    assert exc.value.code == "ERR_PROJECT_MIGRATION_DEPENDENCY_AMBIGUOUS"
    assert ProductProjectManifestStore.load(project) == manifest
    assert first.read_bytes() == duplicate.read_bytes()
    assert not (project / ".bai-project" / "backups").exists()
