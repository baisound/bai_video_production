from ai_video_production.dbd_training_studio import knowledge_detail_search_text


def test_knowledge_detail_search_text_accepts_nested_json_values() -> None:
    details = {
        "empty": "",
        "missing": None,
        "scalar": "generator",
        "nested": {"name_ja": "発電機", "states": ["修理中", "完了"]},
        "sections": [{"title": "固有情報", "value": "回転進行"}],
    }

    text = knowledge_detail_search_text(details)

    assert "generator" in text
    assert "発電機" in text
    assert "修理中" in text
    assert "固有情報" in text
    assert "None" not in text


def test_inventory_startup_path_uses_unhashable_safe_detail_formatter() -> None:
    # The packaged crash occurred before mainloop while the initial inventory
    # refresh consumed a nested dict from the real Owner workspace.
    assert knowledge_detail_search_text({"nested": {"key": "value"}})
