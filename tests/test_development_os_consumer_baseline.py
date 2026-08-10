from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_development_os_adapter_is_governance_only_and_external() -> None:
    adapter = json.loads((ROOT / ".bai-os" / "project.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert adapter["schema_version"] == "1.0.0"
    assert adapter["os_version"] == "1.0.0"
    assert adapter["project_evidence_root"] == "docs/ai-team/tasks"
    assert adapter["commands"]["test"] == "python -m pytest -q"
    assert "Architecture Ver.2.28" in adapter["notes"]
    assert "runtime dependency" in adapter["notes"]
    assert "bai-development-os" not in pyproject


def test_product_canonical_docs_pin_v0164_and_architecture_228() -> None:
    project = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
    current = (ROOT / "docs" / "ai-team" / "current-state.md").read_text(encoding="utf-8")

    assert "STANDALONE_APPLICATION_REQUIRED" in project
    assert "OWNERSHIP_NOT_PATH_BASED" in project
    assert "Architecture Ver.2.28" in project
    assert "Package: `0.16.4`" in project
    assert "Package: `0.16.4`" in current
    assert "402 / 402 PASS" in current
    assert "TASK-006 Slice D" in current
