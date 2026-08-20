from pathlib import Path


def test_observation_artifact_policy_contract():
    from ai_video_production import game_intelligence_export as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "if observation_rows:" in source
    assert 'observations_jsonl_path = root / "observations.jsonl"' in source
    assert 'observations_csv_path = root / "observations.csv"' in source
