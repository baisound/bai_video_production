from pathlib import Path
from ai_video_production.dbd_trivia_editor import default_trivia_database_path


def test_trivia_editor_database_path_can_be_overridden(monkeypatch,tmp_path):
    target=tmp_path/'trivia.sqlite3'; monkeypatch.setenv('BVP_DBD_TRIVIA_DB',str(target))
    assert default_trivia_database_path() == target
