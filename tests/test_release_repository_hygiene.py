from pathlib import Path


def test_local_subtitle_workspace_state_is_gitignored() -> None:
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")

    assert "/subtitle-workspace.json" in gitignore
