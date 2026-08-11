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


def test_product_canonical_docs_keep_release_state_consistent_with_architecture_228() -> None:
    import re

    project = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
    current = (ROOT / "docs" / "ai-team" / "current-state.md").read_text(encoding="utf-8")

    assert "STANDALONE_APPLICATION_REQUIRED" in project
    assert "OWNERSHIP_NOT_PATH_BASED" in project
    assert "Architecture Ver.2.28" in project

    package_pattern = re.compile(r"- Package: `([0-9]+\.[0-9]+\.[0-9]+)`")
    candidate_pattern = re.compile(r"- Development Candidate: `([^`]+)`")

    project_package = package_pattern.search(project)
    current_package = package_pattern.search(current)
    project_candidate = candidate_pattern.search(project)
    current_candidate = candidate_pattern.search(current)

    assert project_package is not None
    assert current_package is not None
    assert project_candidate is not None
    assert current_candidate is not None
    assert project_package.group(1) == current_package.group(1)
    assert project_candidate.group(1) == current_candidate.group(1)

    candidate = project_candidate.group(1)
    if candidate == "NONE":
        return

    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", candidate)
    formal = tuple(int(part) for part in project_package.group(1).split("."))
    candidate_version = tuple(int(part) for part in candidate.split("."))
    assert candidate_version > formal
