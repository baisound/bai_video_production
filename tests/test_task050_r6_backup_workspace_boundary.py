from ai_video_production.dbd_data_migration import DbDDataMigrationService
from ai_video_production.dbd_training_studio_foundation import WorkspaceRegistry, WorkspaceService

def test_existing_backup_service_accepts_selected_workspace_root(tmp_path):
    registry=WorkspaceRegistry(tmp_path/"settings"/"registry.json")
    ws=WorkspaceService(registry).create(display_name="DBD",parent_directory=tmp_path/"workspaces")
    (ws.root/"training-data"/"sample.txt").write_text("sample",encoding="utf-8")
    migration=DbDDataMigrationService(training_root=ws.root,trivia_database_path=tmp_path/"missing.sqlite")
    receipt=migration.create_backup(tmp_path/"backup.zip",include_project=False,include_training=True,include_trivia=False)
    assert receipt.path.is_file()
