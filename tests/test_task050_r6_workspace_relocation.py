from pathlib import Path
from ai_video_production.dbd_training_studio_foundation import WorkspaceRegistry, WorkspaceService
from ai_video_production.dbd_workspace_relocation import WorkspaceRelocationService

def test_workspace_relocation_preserves_source_and_identity(tmp_path):
    registry=WorkspaceRegistry(tmp_path/"settings"/"registry.json")
    service=WorkspaceService(registry)
    ws=service.create(display_name="DBD",parent_directory=tmp_path/"old")
    (ws.root/"training-data"/"x.txt").write_text("abc",encoding="utf-8")
    receipt=WorkspaceRelocationService(registry).relocate(ws,tmp_path/"new")
    assert Path(receipt.source_path).is_dir()
    assert Path(receipt.destination_path).is_dir()
    assert service.open(receipt.destination_path).workspace_id==ws.workspace_id
