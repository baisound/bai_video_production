from pathlib import Path


def test_project_requires_standalone_application_without_bai_os_runtime_dependency() -> None:
    project = (Path(__file__).resolve().parents[1] / "PROJECT.md").read_text(encoding="utf-8")

    assert "STANDALONE_APPLICATION_REQUIRED" in project
    assert "Product runtimeはBAI Development OS repository" in project
    assert "0.17.0以降のOS差し替えは「開発方法の更新」" in project
    assert "OWNERSHIP_NOT_PATH_BASED" in project
    assert "docs/ai-team/`配下のBAI Video Production固有Task / Design / Evidence / Current StateはProduct-owned" in project
    assert "`docs/ai-team/`を一律READ ONLYとする運用は禁止する" in project
    assert "Product runtime does not depend on BAI OS unless an authorized Task" not in project
