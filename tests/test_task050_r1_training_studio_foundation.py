from __future__ import annotations

import json
from pathlib import Path

from ai_video_production.dbd_training_studio_foundation import (
    RuntimeProfileStore,
    WorkspaceRegistry,
    WorkspaceService,
)
from ai_video_production.dbd_training_studio_i18n import (
    STAGE_JA,
    STAGE_ORDER,
    UserFacingError,
)


def test_workspace_is_created_at_user_selected_parent(tmp_path):
    registry = WorkspaceRegistry(tmp_path / "settings" / "registry.json")
    service = WorkspaceService(registry)
    selected_parent = tmp_path / "D-drive-like"
    workspace = service.create(display_name="大会DBD学習", parent_directory=selected_parent)

    assert Path(workspace.root_path).parent == selected_parent.resolve()
    assert Path(workspace.root_path, "workspace.json").is_file()
    assert workspace.workspace_id.startswith("dbdws-")
    assert Path(workspace.root_path, "human-gold").is_dir()
    assert registry.default_candidate() == Path(workspace.root_path)


def test_workspace_rename_preserves_identity_and_path(tmp_path):
    registry = WorkspaceRegistry(tmp_path / "registry.json")
    service = WorkspaceService(registry)
    workspace = service.create(display_name="最初の名前", parent_directory=tmp_path / "data")
    renamed = service.rename(workspace, "大会用")

    assert renamed.workspace_id == workspace.workspace_id
    assert renamed.root_path == workspace.root_path
    assert renamed.display_name == "大会用"


def test_existing_legacy_folder_can_be_adopted_without_moving_data(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    sentinel = legacy / "visual-training.csv"
    sentinel.write_text("existing", encoding="utf-8")

    registry = WorkspaceRegistry(tmp_path / "registry.json")
    service = WorkspaceService(registry)
    workspace = service.adopt_existing(legacy, display_name="既存データ")

    assert sentinel.read_text(encoding="utf-8") == "existing"
    assert workspace.root == legacy.resolve()
    assert (legacy / "workspace.json").is_file()


def test_migration_preflight_is_non_mutating(tmp_path):
    registry = WorkspaceRegistry(tmp_path / "registry.json")
    service = WorkspaceService(registry)
    workspace = service.create(display_name="DBD", parent_directory=tmp_path / "old")
    (workspace.root / "training-data" / "sample.bin").write_bytes(b"abc")

    destination_parent = tmp_path / "new"
    before = sorted(str(p.relative_to(workspace.root)) for p in workspace.root.rglob("*"))
    report = service.migration_preflight(workspace, destination_parent)
    after = sorted(str(p.relative_to(workspace.root)) for p in workspace.root.rglob("*"))

    assert report.can_migrate
    assert report.source_file_count >= 2  # workspace.json + sample
    assert before == after
    assert not Path(report.destination_path).exists()


def test_runtime_profile_autodetect_and_save_contains_no_credentials(tmp_path):
    mapping = {
        "ffmpeg": r"D:\Tools\ffmpeg.exe",
        "ffprobe": r"D:\Tools\ffprobe.exe",
        "tesseract": None,
    }
    profile = RuntimeProfileStore.autodetect(which=mapping.get)
    store = RuntimeProfileStore(tmp_path / "runtime")
    path = store.save(profile)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["ffmpeg"]["effective_path"] == r"D:\Tools\ffmpeg.exe"
    assert payload["ffprobe"]["health"] == "AVAILABLE"
    assert payload["tesseract"]["health"] == "MISSING"
    serialized = json.dumps(payload).lower()
    assert '"api_key"' not in serialized
    assert '"password"' not in serialized
    assert '"token"' not in serialized


def test_stage_order_is_japanese_first_operational_order():
    assert STAGE_ORDER[:5] == (
        "INTRODUCTION",
        "RUNTIME_ENVIRONMENT",
        "KNOWLEDGE_IMPORT",
        "HUD_CALIBRATION",
        "VIDEO_LEARNING",
    )
    assert STAGE_JA["HUD_CALIBRATION"] == "HUD位置を設定"
    assert STAGE_JA["TRAINING_DATA_REVIEW"] == "学習データを確認"


def test_user_error_rejects_bare_none():
    try:
        UserFacingError("ERR_X", "None", "処理できませんでした。", "設定を確認してください。")
    except ValueError:
        pass
    else:
        raise AssertionError("bare None must be rejected")
