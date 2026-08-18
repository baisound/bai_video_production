from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

from ai_video_production.dbd_data_migration import (
    DbDDataMigrationError,
    DbDDataMigrationService,
)


def _make_sqlite(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS payload(value TEXT NOT NULL)")
        conn.execute("DELETE FROM payload")
        conn.execute("INSERT INTO payload(value) VALUES (?)", (value,))
        conn.commit()


def _read_sqlite(path: Path) -> str:
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT value FROM payload").fetchone()[0]


def test_backup_restore_roundtrip_across_project_training_and_trivia(tmp_path: Path) -> None:
    source_training = tmp_path / "source-training"
    source_training.mkdir()
    (source_training / "visual-training.csv").write_text("label,image\nperk-a,a.pgm\n", encoding="utf-8")
    (source_training / "indexes").mkdir()
    (source_training / "indexes" / "perk.json").write_text('{"index":"a"}', encoding="utf-8")
    _make_sqlite(source_training / "dbd-commentary-knowledge.sqlite3", "training-trivia")

    source_trivia = tmp_path / "source-trivia.sqlite3"
    _make_sqlite(source_trivia, "global-trivia")

    source_project = tmp_path / "source-project"
    project_state = source_project / ".bvp" / "game-intelligence"
    _make_sqlite(project_state / "analysis.sqlite3", "analysis-a")
    _make_sqlite(project_state / "perk-knowledge.sqlite3", "perk-a")

    service = DbDDataMigrationService(
        training_root=source_training,
        trivia_database_path=source_trivia,
        safety_backup_root=tmp_path / "safety",
    )
    bundle = tmp_path / "migration.zip"
    receipt = service.create_backup(bundle, project_root=source_project)
    assert receipt.entry_count == 6
    assert receipt.total_bytes > 0
    assert set(receipt.scopes) == {"project-game-intelligence", "training-workspace", "global-trivia"}

    target_training = tmp_path / "target-training"
    target_trivia = tmp_path / "target-trivia.sqlite3"
    target_project = tmp_path / "target-project"
    target = DbDDataMigrationService(
        training_root=target_training,
        trivia_database_path=target_trivia,
        safety_backup_root=tmp_path / "target-safety",
    )
    preview = target.preview_restore(bundle, project_root=target_project)
    assert preview.conflicts == ()
    assert preview.requires_project_root is False

    restored = target.restore(bundle, project_root=target_project)
    assert restored.restored_files == receipt.entry_count
    assert restored.replaced_files == 0
    assert restored.new_files == receipt.entry_count
    assert (target_training / "visual-training.csv").read_text(encoding="utf-8").startswith("label,image")
    assert _read_sqlite(target_training / "dbd-commentary-knowledge.sqlite3") == "training-trivia"
    assert _read_sqlite(target_trivia) == "global-trivia"
    assert _read_sqlite(target_project / ".bvp" / "game-intelligence" / "analysis.sqlite3") == "analysis-a"
    assert _read_sqlite(target_project / ".bvp" / "game-intelligence" / "perk-knowledge.sqlite3") == "perk-a"


def test_restore_conflict_requires_explicit_replace_and_creates_safety_backup(tmp_path: Path) -> None:
    source_training = tmp_path / "source-training"
    source_training.mkdir()
    (source_training / "visual-training.csv").write_text("new", encoding="utf-8")
    source_project = tmp_path / "source-project"
    service = DbDDataMigrationService(training_root=source_training, trivia_database_path=tmp_path / "missing.sqlite3")
    bundle = tmp_path / "migration.zip"
    service.create_backup(bundle, project_root=source_project, include_project=False, include_trivia=False)

    target_training = tmp_path / "target-training"
    target_training.mkdir()
    (target_training / "visual-training.csv").write_text("old", encoding="utf-8")
    target = DbDDataMigrationService(
        training_root=target_training,
        trivia_database_path=tmp_path / "target-trivia.sqlite3",
        safety_backup_root=tmp_path / "safety",
    )
    preview = target.preview_restore(bundle)
    assert preview.conflicts == ("training-workspace/visual-training.csv",)
    with pytest.raises(DbDDataMigrationError, match="explicitly authorize replacement"):
        target.restore(bundle)

    receipt = target.restore(bundle, allow_replace=True)
    assert receipt.replaced_files == 1
    assert receipt.safety_backup_path is not None and receipt.safety_backup_path.is_file()
    assert (target_training / "visual-training.csv").read_text(encoding="utf-8") == "new"


def test_preview_rejects_tampered_payload(tmp_path: Path) -> None:
    training = tmp_path / "training"
    training.mkdir()
    (training / "visual-training.csv").write_text("original", encoding="utf-8")
    service = DbDDataMigrationService(training_root=training, trivia_database_path=tmp_path / "missing.sqlite3")
    bundle = tmp_path / "migration.zip"
    service.create_backup(bundle, include_project=False, include_trivia=False)

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle, "r") as src, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            payload = src.read(name)
            if name.endswith("visual-training.csv"):
                payload = b"tampered"
            dst.writestr(name, payload)
    with pytest.raises(DbDDataMigrationError, match="checksum mismatch"):
        service.preview_restore(tampered)


def test_backup_excludes_credentials_and_private_key_material(tmp_path: Path) -> None:
    training = tmp_path / "training"
    training.mkdir()
    (training / "visual-training.csv").write_text("safe", encoding="utf-8")
    (training / ".env").write_text("OPENAI_API_KEY=secret", encoding="utf-8")
    (training / "credentials.json").write_text('{"secret":"x"}', encoding="utf-8")
    (training / "client.pem").write_text("secret", encoding="utf-8")
    service = DbDDataMigrationService(training_root=training, trivia_database_path=tmp_path / "missing.sqlite3")
    bundle = tmp_path / "migration.zip"
    receipt = service.create_backup(bundle, include_project=False, include_trivia=False)
    assert set(receipt.excluded_paths) == {
        "training-workspace/.env",
        "training-workspace/client.pem",
        "training-workspace/credentials.json",
    }
    with zipfile.ZipFile(bundle, "r") as archive:
        names = set(archive.namelist())
        assert "data/training-workspace/visual-training.csv" in names
        assert all("credential" not in x.lower() and not x.endswith(".pem") and not x.endswith("/.env") for x in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["credentials_included"] is False


def test_project_scope_requires_target_project_root_on_restore(tmp_path: Path) -> None:
    project = tmp_path / "source-project"
    _make_sqlite(project / ".bvp" / "game-intelligence" / "analysis.sqlite3", "x")
    service = DbDDataMigrationService(training_root=tmp_path / "training", trivia_database_path=tmp_path / "missing.sqlite3")
    bundle = tmp_path / "migration.zip"
    service.create_backup(bundle, project_root=project, include_training=False, include_trivia=False)
    preview = service.preview_restore(bundle)
    assert preview.requires_project_root is True
    with pytest.raises(DbDDataMigrationError, match="project_root is required"):
        service.restore(bundle)
