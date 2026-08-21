from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.task036_element_contract import (
    BROWSER_AUDIT_BASELINE,
    ElementContractState,
    ElementKind,
    MAX_ELEMENTS_PER_SURFACE,
    MAX_MARKUP_BYTES,
    PAGE_SERVICE_REGISTRY,
    SurfaceLifecycleState,
    assert_effect_free_inventory,
    compile_element_selection_inventory,
    count_source_controls,
)
from ai_video_production.task036_shell_v611 import HTML as RUNTIME_HTML


ROOT = Path(__file__).resolve().parents[1]
MOCK_HTML = (
    ROOT / "docs" / "ai-team" / "product-design" / "v6-integration" / "BVP-UI-MOCK-V6.1.1.html"
).read_text(encoding="utf-8")


def _minimal_surface(body: str = "") -> str:
    pages = (
        "home", "planning", "scenes", "locks", "sceneDesign", "imageGen", "videoGen",
        "audio", "assetReview", "edit", "finalReview", "export", "assets", "quick",
    )
    return "".join(f'<section class="page" data-page="{page}">{body}</section>' for page in pages)


def test_canonical_mock_and_runtime_source_counts_remain_explicit() -> None:
    assert count_source_controls(MOCK_HTML) == {
        "pages": 14,
        "stable_ids": 203,
        "buttons": 231,
        "selects": 41,
        "inputs_and_textareas": 75,
        "contract_elements": 449,
    }
    assert count_source_controls(RUNTIME_HTML) == {
        "pages": 14,
        "stable_ids": 118,
        "buttons": 126,
        "selects": 1,
        "inputs_and_textareas": 6,
        "contract_elements": 180,
    }
    assert BROWSER_AUDIT_BASELINE == {
        "mock": {"pages": 14, "buttons": 253, "stable_ids": 205, "selects": 57, "inputs_and_textareas": 83},
        "runtime": {"pages": 14, "buttons": 126, "stable_ids": 109, "selects": 2, "inputs_and_textareas": 7},
    }


def test_inventory_is_deterministic_and_preserves_current_incompleteness() -> None:
    first = compile_element_selection_inventory(MOCK_HTML, RUNTIME_HTML)
    second = compile_element_selection_inventory(MOCK_HTML, RUNTIME_HTML)
    assert first == second
    assert first.inventory_sha256 == second.inventory_sha256
    assert first.inventory_sha256.startswith("sha256:")
    assert len(first.elements) == 582
    states = first.to_dict()["state_counts"]
    assert states == {
        "BOUND": 48,
        "NAVIGATION": 43,
        "DISABLED_WITH_REASON": 32,
        "DYNAMIC_CONDITIONAL": 43,
        "INTENT_ONLY": 14,
        "MISSING": 402,
    }
    assert states["MISSING"] > 0
    assert first.provider_execution_authorized is False
    assert first.human_decision_inferred is False
    assert first.external_effects_started is False


def test_every_required_page_has_exact_owner_and_cross_screen_handoff() -> None:
    assert len(PAGE_SERVICE_REGISTRY) == 15
    assert len({item.page_id for item in PAGE_SERVICE_REGISTRY}) == 15
    assert PAGE_SERVICE_REGISTRY[0].page_id == "shell"
    for page in PAGE_SERVICE_REGISTRY:
        assert page.owner_tasks
        assert page.source_contracts
        assert page.next_identity_fields
        if page.page_id != "export":
            assert page.next_page_id is not None


def test_selectable_elements_have_a_total_required_lifecycle_without_claiming_success() -> None:
    inventory = compile_element_selection_inventory(MOCK_HTML, RUNTIME_HTML)
    selectable_kinds = {
        ElementKind.BUTTON,
        ElementKind.INPUT,
        ElementKind.TEXTAREA,
        ElementKind.SELECT,
        ElementKind.TAB,
        ElementKind.CARD,
    }
    for item in inventory.elements:
        if item.kind in selectable_kinds:
            assert item.lifecycle is not None
            assert item.lifecycle.selected_coordinate == item.coordinate
            assert item.lifecycle.required_choice_source
            assert item.lifecycle.required_validation == (
                "CURRENT_VALID",
                "RIGHTS_LICENSE",
                "CAPABILITY",
                "RESOURCE",
                "FRESHNESS",
            )
            assert item.lifecycle.current_state is item.state
        else:
            assert item.lifecycle is None


def test_missing_mock_control_cannot_be_promoted_by_a_runtime_label_or_toast() -> None:
    mock = _minimal_surface('<select id="modelChoice"><option>Canonical</option></select>')
    runtime = _minimal_surface('<div role="status">Canonical selected</div>')
    inventory = compile_element_selection_inventory(mock, runtime)
    row = next(item for item in inventory.elements if item.coordinate == "home/id/modelChoice")
    assert row.state is ElementContractState.MISSING
    assert row.mock_present is True
    assert row.runtime_present is False


def test_disabled_control_requires_a_reason_to_enter_disabled_contract_state() -> None:
    mock = _minimal_surface('<button id="run">Run</button>')
    runtime_without_reason = _minimal_surface('<button id="run" disabled>Run</button>')
    runtime_with_reason = _minimal_surface('<button id="run" disabled data-disabled-reason="Owner Gate">Run</button>')
    first = compile_element_selection_inventory(mock, runtime_without_reason)
    second = compile_element_selection_inventory(mock, runtime_with_reason)
    assert next(item for item in first.elements if item.coordinate == "home/id/run").state is ElementContractState.INTENT_ONLY
    row = next(item for item in second.elements if item.coordinate == "home/id/run")
    assert row.state is ElementContractState.DISABLED_WITH_REASON
    assert row.disabled_reason == "Owner Gate"


def test_navigation_is_not_misreported_as_product_apply() -> None:
    markup = _minimal_surface('<button data-nav="planning">Plan</button>')
    inventory = compile_element_selection_inventory(markup, markup)
    row = next(item for item in inventory.elements if item.page_id == "home")
    assert row.state is ElementContractState.NAVIGATION
    assert row.lifecycle is not None
    assert row.lifecycle.required_choice_source == ("Task036RouteRegistry",)


def test_lifecycle_state_enum_is_total_and_closed() -> None:
    assert [item.value for item in SurfaceLifecycleState] == [
        "LOADING",
        "EMPTY",
        "READY",
        "BLOCKED",
        "ERROR",
        "STALE",
        "UNKNOWN",
        "RECOVERY_REQUIRED",
    ]


def test_inventory_rejects_missing_page_duplicate_id_and_caps() -> None:
    with pytest.raises(ValueError, match="page registry is incomplete"):
        compile_element_selection_inventory('<section data-page="home"></section>', RUNTIME_HTML)
    duplicate = _minimal_surface('<button id="same">A</button><button id="same">B</button>')
    with pytest.raises(ValueError, match="duplicate element coordinates"):
        compile_element_selection_inventory(duplicate, duplicate)
    over_cap = _minimal_surface("".join(f'<button id="b{index}">B</button>' for index in range(MAX_ELEMENTS_PER_SURFACE + 1)))
    with pytest.raises(ValueError, match="surface element cap exceeded"):
        compile_element_selection_inventory(over_cap, over_cap)
    with pytest.raises(ValueError, match="bounded markup size"):
        compile_element_selection_inventory("x" * (MAX_MARKUP_BYTES + 1), RUNTIME_HTML)


def test_effect_flags_are_fail_closed() -> None:
    inventory = compile_element_selection_inventory(MOCK_HTML, RUNTIME_HTML)
    assert_effect_free_inventory(inventory)
    with pytest.raises(ValueError, match="cannot authorize"):
        assert_effect_free_inventory(replace(inventory, provider_execution_authorized=True))
    with pytest.raises(ValueError, match="cannot authorize"):
        assert_effect_free_inventory(replace(inventory, human_decision_inferred=True))
    with pytest.raises(ValueError, match="cannot authorize"):
        assert_effect_free_inventory(replace(inventory, external_effects_started=True))


def test_module_has_no_filesystem_process_network_or_provider_surface() -> None:
    source = (ROOT / "src" / "ai_video_production" / "task036_element_contract.py").read_text(encoding="utf-8")
    for forbidden in (
        "from pathlib",
        "import os",
        "import subprocess",
        "import socket",
        "import requests",
        "urlopen",
        "open(",
        "provider_client",
        "run_generation",
    ):
        assert forbidden not in source
