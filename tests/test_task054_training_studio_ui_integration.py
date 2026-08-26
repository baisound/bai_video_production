from __future__ import annotations

from pathlib import Path


SOURCE = Path("src/ai_video_production/dbd_training_studio.py")


def test_training_studio_exposes_one_reasoning_operator_tab() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count('text="実況・解説AI"') == 1
    for label in (
        "現在の実況・解説", "モデルと事前チェック", "Datasetと評価", "処理状況と復旧",
    ):
        assert f'text="{label}"' in source
    assert "reasoning_tab," in source[source.index("ordered_tabs = ("):]


def test_all_r5_panels_are_connected_without_an_execution_callback() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for panel in (
        "CommentaryPreviewPanel", "ReasoningModelPanel", "DatasetEvaluationPanel",
        "TrainingStudioOperationPanel",
    ):
        assert panel in source
    assert "ERR_TASK054_R3D_REQUIRED" in source
    assert "取消要求は未送信です" in source
    assert "再開計画要求は未送信です" in source
    assert "opening the tab never starts inference" in source


def test_packaged_training_studio_entry_remains_the_existing_entrypoint() -> None:
    entry = Path("packaging/task049_training_studio_windows_entry.py").read_text(encoding="utf-8")
    spec = Path("packaging/task049_training_studio.spec").read_text(encoding="utf-8")
    assert "from ai_video_production.dbd_training_studio import main" in entry
    assert "task049_training_studio_windows_entry.py" in spec


def test_operator_copy_keeps_model_and_worker_effects_blocked() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "実行可能な承認済みBinding/routeはまだありません" in source
    assert "レビュー対象はまだありません" in source
    assert "動画Evidence読込後にseekします" in source
