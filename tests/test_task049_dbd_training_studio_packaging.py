from pathlib import Path

from ai_video_production.dbd_training_studio import ensure_csv_templates


ROOT = Path(__file__).resolve().parents[1]


def test_training_studio_build_contract_and_entrypoint_exist():
    batch = ROOT / "build-dbd-training-studio-exe.bat"
    spec = ROOT / "packaging" / "task049_training_studio.spec"
    entry = ROOT / "packaging" / "task049_training_studio_windows_entry.py"
    assert batch.is_file() and spec.is_file() and entry.is_file()
    text = batch.read_text(encoding="utf-8")
    assert "BAI DbD Training Studio.exe" in text
    assert "task049_training_studio.spec" in text
    assert "PyInstaller" in text
    spec_text = spec.read_text(encoding="utf-8")
    assert "BAI DbD Training Studio" in spec_text
    assert '"faster_whisper"' in spec_text
    assert "collect_data_files" in spec_text
    assert 'collect_data_files("jsonschema_specifications")' in spec_text
    assert '"av"' in spec_text
    assert "dbd_training_studio" in entry.read_text(encoding="utf-8")


def test_training_studio_templates_cover_single_bulk_and_video_learning(tmp_path):
    templates = ensure_csv_templates(tmp_path)
    assert len(templates) == 4
    names = {path.name for path in templates}
    assert "visual-training-template.csv" in names
    assert "upper-right-ocr-vocabulary-template.csv" in names
    assert "commentary-trivia-template.csv" in names
    assert "video-training-ranges-template.csv" in names
    video = (tmp_path / "templates" / "video-training-ranges-template.csv").read_text(encoding="utf-8-sig")
    assert "video_path" in video
    assert "start_frame" in video
    assert "end_frame_exclusive" in video
    assert "frame_step" in video


def test_training_studio_exposes_portable_backup_restore_and_user_guide():
    source = (ROOT / "src" / "ai_video_production" / "dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'notebook.add(migration_tab, text="バックアップ・復元")' in source
    assert "DbDDataMigrationService" in source
    guide = ROOT / "docs" / "user" / "DBD-DATA-BACKUP-RESTORE.md"
    assert guide.is_file()
    text = guide.read_text(encoding="utf-8")
    assert "Preview restore" in text
    assert "credentials" in text.lower()
    assert "migration-restore-backups" in text


def test_training_studio_exposes_hud_calibration_profile_and_anchor_controls():
    source = (ROOT / "src" / "ai_video_production" / "dbd_training_studio.py").read_text(encoding="utf-8")
    assert 'notebook.add(calibration_page, text="HUD位置を設定")' in source
    assert "HUD設定を保存" in source
    assert "自動補正をテスト" in source
    assert "登録済みHUD設定" in source
    assert "HudProfileRegistry" in source
    assert "DBDHudVideoProfileResolver" in source
    assert "HudAnchorAligner" in source
