import json

from ai_video_production.quickstart_cli import build_demo_document, main


def test_quickstart_is_credential_free_and_builds_exact_timeline() -> None:
    document = build_demo_document()
    assert document["network_used"] is False
    assert document["credentials_used"] is False
    assert document["paid_provider_used"] is False
    assert document["selected_route"]["route_id"] == "local-planning-demo"
    assert document["timeline_plan"]["placements"][1]["timeline_range_frames"]["start"] == 75
    assert str(document["demo_sha256"]).startswith("sha256:")


def test_quickstart_cli_writes_auditable_json(tmp_path) -> None:
    output = tmp_path / "demo.json"
    assert main(["--output", str(output)]) == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["demo_version"] == "1.0.0"
    assert len(document["timeline_plan"]["placements"]) == 2
