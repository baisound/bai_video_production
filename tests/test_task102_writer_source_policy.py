from __future__ import annotations

import ast
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "ai_video_production"
MATRIX_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "ai-team"
    / "tasks"
    / "TASK-102"
    / "pmst-d1-protected-control-mutation-matrix-r0.json"
)

DELEGATIONS = {
    "product_project_store.py:_exclusive_project_lock": (
        "product_project_store.py:ProductProjectManifestStore.save",
    ),
    "project_history.py:_rotate_files": (
        "project_history.py:ProductProjectAutosaveCoordinator.autosave",
    ),
    "project_history.py:_rotate_directories": (
        "project_history.py:ProductProjectBackupStore.create",
    ),
    "atomic.py:exclusive_file_update_lock": (
        "voice_profile_store.py:VoiceProfileRevisionStore.create",
        "voice_profile_store.py:VoiceProfileRevisionStore.append",
    ),
    "montage_learning_canonical_admission_transaction.py:_exclusive_existing_project_lock": (
        "montage_learning_canonical_admission_transaction.py:MontageLearningCanonicalAdmissionTransactionStore.__init__",
    ),
}

FILE_ROUTE_CLOSURES = {
    "audio_placement_application.py": ("PMST-R012",),
    "interactive_timeline_application.py": ("PMST-R008",),
    "project_migration_application.py": ("PMST-R011", "PMST-R012"),
    "project_history.py": ("PMST-R005", "PMST-R006"),
    "timeline_audio_application.py": ("PMST-R012",),
    "voice_quality_meter_policy_store.py": ("PMST-R012",),
    "montage_learning_canonical_admission_transaction.py": ("PMST-R010",),
}

MUTATOR_CALLS = {
    "ProductProjectManifestStore.save",
    "_exclusive_project_lock",
}
PROTECTED_LITERALS = {
    ".bai-project",
    "jobs.json",
    "history.json",
    "save-journal.json",
    "voice-profile-revisions.json",
    "timeline-edit-command-recovery.json",
}


def _matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _node_for(source: str) -> tuple[str, ast.AST]:
    filename, symbol = source.split(":", 1)
    text = (SOURCE_ROOT / filename).read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=filename)
    parts = symbol.split(".")
    nodes: list[ast.AST] = list(tree.body)
    selected: ast.AST | None = None
    for part in parts:
        selected = next(
            (
                node
                for node in nodes
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == part
            ),
            None,
        )
        if selected is None:
            raise AssertionError(f"matrix source symbol is missing: {source}")
        nodes = list(getattr(selected, "body", ()))
    if len(parts) > 1:
        selected = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == parts[0]
        )
    assert selected is not None
    return text, selected


def _contains_route_marker(source: str, route_id: str) -> bool:
    text, node = _node_for(source)
    segment = ast.get_source_segment(text, node)
    return segment is not None and route_id in segment


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _protected_mutation_signals(text: str) -> set[str]:
    tree = ast.parse(text)
    calls = {
        name
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        for name in [_dotted_name(call.func)]
        if name is not None
    }
    imports_coordinator = any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "ProductProjectSaveCoordinator" for alias in node.names)
        for node in ast.walk(tree)
    )
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    signals = calls & MUTATOR_CALLS
    if imports_coordinator and any(name.endswith(".save") for name in calls):
        signals.add("ProductProjectSaveCoordinator.*.save")
    if literals & PROTECTED_LITERALS and any(
        name.endswith((".write", ".unlink", ".mkdir", ".rmdir")) for name in calls
    ):
        signals.add("protected-literal-with-mutation")
        if "AtomicJsonWriter.write" in calls:
            signals.add("AtomicJsonWriter.write")
    return signals


def test_every_d1_source_has_a_machine_checked_route_closure() -> None:
    matrix = _matrix()
    assert [row["route_id"] for row in matrix["routes"]] == [
        f"PMST-R{index:03d}" for index in range(1, 14)
    ]
    for row in matrix["routes"]:
        route_id = row["route_id"]
        if route_id == "PMST-R013":
            assert row["disposition"] == "UNSUPPORTED_BLOCKED"
            assert row["profile"] == "NONE"
            continue
        for source in row["sources"]:
            if ":" not in source:
                markers = FILE_ROUTE_CLOSURES[source]
                text = (SOURCE_ROOT / source).read_text(encoding="utf-8-sig")
                assert all(marker in text for marker in markers), source
                continue
            if _contains_route_marker(source, route_id):
                continue
            delegates = DELEGATIONS[source]
            assert delegates
            assert all(_contains_route_marker(delegate, route_id) for delegate in delegates)


def test_repository_has_no_unregistered_protected_mutation_source() -> None:
    matrix_files = {
        source.split(":", 1)[0]
        for row in _matrix()["routes"]
        for source in row["sources"]
        if source.endswith(".py") or ".py:" in source
    }
    uncovered: dict[str, list[str]] = {}
    for path in sorted(SOURCE_ROOT.glob("*.py")):
        signals = _protected_mutation_signals(path.read_text(encoding="utf-8-sig"))
        if signals and path.name not in matrix_files and path.name != "__init__.py":
            uncovered[path.name] = sorted(signals)
    assert uncovered == {}


def test_source_policy_rejects_a_synthetic_unregistered_project_lock() -> None:
    source = """
def unsafe(project_root):
    with _exclusive_project_lock(ProductProjectManifestStore.path(project_root)):
        AtomicJsonWriter.write(project_root / '.bai-project' / 'unknown.json', {})
"""
    assert _protected_mutation_signals(source) == {
        "AtomicJsonWriter.write",
        "_exclusive_project_lock",
        "protected-literal-with-mutation",
    }
