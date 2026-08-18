import inspect

from ai_video_production.game_intelligence_export import GameIntelligenceAnalysisExporter


def test_export_accepts_optional_observations_without_breaking_existing_callers():
    signature = inspect.signature(GameIntelligenceAnalysisExporter.export)
    assert "observations" in signature.parameters
    assert signature.parameters["observations"].default == ()
