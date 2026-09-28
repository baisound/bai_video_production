from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import textwrap


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
    "project_save.py:ProductProjectSaveCoordinator._internal_path": (
        "project_save.py:ProductProjectSaveCoordinator.save",
    ),
    "montage_learning_canonical_admission_transaction.py:MontageLearningCanonicalAdmissionTransactionStore._generic_recover_v1_locked": (
        "montage_learning_canonical_admission_transaction.py:MontageLearningCanonicalAdmissionTransactionStore.recover_generic_observation",
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


def _node_for_text(text: str, symbol: str, *, filename: str) -> ast.AST:
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
            raise AssertionError(f"matrix source symbol is missing: {filename}:{symbol}")
        nodes = list(getattr(selected, "body", ()))
    assert selected is not None
    return selected


def _node_for(source: str) -> tuple[str, ast.AST]:
    filename, symbol = source.split(":", 1)
    text = (SOURCE_ROOT / filename).read_text(encoding="utf-8-sig")
    selected = _node_for_text(text, symbol, filename=filename)
    return text, selected


def _route_markers_in_text(text: str, symbol: str, *, filename: str) -> set[str]:
    node = _node_for_text(text, symbol, filename=filename)
    segment = ast.get_source_segment(text, node) or ""
    markers = set(re.findall(r"PMST-R\d{3}", segment))
    parts = symbol.split(".")
    if len(parts) != 2 or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return markers
    class_name = parts[0]
    helper_names = {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id in {"self", "cls"}
    }
    for helper_name in helper_names:
        try:
            helper = _node_for_text(
                text,
                f"{class_name}.{helper_name}",
                filename=filename,
            )
        except AssertionError:
            continue
        helper_segment = ast.get_source_segment(text, helper) or ""
        markers.update(re.findall(r"PMST-R\d{3}", helper_segment))
    return markers


def _contains_route_marker_in_text(text: str, symbol: str, route_id: str, *, filename: str) -> bool:
    return route_id in _route_markers_in_text(text, symbol, filename=filename)


def _contains_route_marker(source: str, route_id: str) -> bool:
    filename, symbol = source.split(":", 1)
    text = (SOURCE_ROOT / filename).read_text(encoding="utf-8-sig")
    return _contains_route_marker_in_text(text, symbol, route_id, filename=filename)


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _protected_mutation_signals(text: str, *, imports_coordinator: bool = False) -> set[str]:
    tree = ast.parse(textwrap.dedent(text))
    calls = {
        name
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        for name in [
            _dotted_name(call.func)
            or (call.func.attr if isinstance(call.func, ast.Attribute) else None)
        ]
        if name is not None
    }
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    signals = calls & MUTATOR_CALLS
    if imports_coordinator and any(name.endswith(".save") for name in calls):
        signals.add("ProductProjectSaveCoordinator.*.save")
    protected_path_helper = any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "with_name"
        and any(
            _dotted_name(inner.func) in {"_manifest_path", "ProductProjectManifestStore.path"}
            for inner in ast.walk(call.func.value)
            if isinstance(inner, ast.Call)
            )
        for call in ast.walk(tree)
    )
    manifest_path_write = (
        "ProductProjectManifestStore.path" in calls
        and "AtomicJsonWriter.write" in calls
    )
    protected_target = bool(literals & PROTECTED_LITERALS) or protected_path_helper or manifest_path_write
    mutation_calls = {
        name
        for name in calls
        if name.rsplit(".", 1)[-1]
        in {"write", "write_bytes", "write_text", "replace", "rename", "unlink", "mkdir", "rmdir"}
    }
    if protected_target and mutation_calls:
        signals.add("protected-literal-with-mutation")
        if "AtomicJsonWriter.write" in calls:
            signals.add("AtomicJsonWriter.write")
    signals.update(calls & {"_exclusive_project_lock"})
    if protected_target:
        signals.update(calls & {"exclusive_file_update_lock"})
    return signals


def _registered_sources() -> set[str]:
    return {
        source
        for row in _matrix()["routes"]
        for source in row["sources"]
        if ".py:" in source
    }


def _iter_function_sources(filename: str, text: str) -> list[tuple[str, str]]:
    tree = ast.parse(text, filename=filename)
    lines = text.splitlines(keepends=True)

    def segment(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        assert node.end_lineno is not None
        return "".join(lines[node.lineno - 1 : node.end_lineno])

    result: list[tuple[str, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append((f"{filename}:{node.name}", segment(node)))
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result.append(
                        (
                            f"{filename}:{node.name}.{child.name}",
                            segment(child),
                        )
                    )
    return result


def _imports_save_coordinator(text: str) -> bool:
    if "ProductProjectSaveCoordinator" not in text:
        return False
    return any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "ProductProjectSaveCoordinator" for alias in node.names)
        for node in ast.walk(ast.parse(text))
    )


def _may_contain_protected_mutation(segment: str, *, imports_coordinator: bool) -> bool:
    direct_tokens = (
        "AtomicJsonWriter",
        "ProductProjectManifestStore.save",
        "_exclusive_project_lock",
        "exclusive_file_update_lock",
        ".bai-project",
        "jobs.json",
        "history.json",
        "save-journal.json",
        "voice-profile-revisions.json",
        "timeline-edit-command-recovery.json",
        "_manifest_path",
        "ProductProjectManifestStore.path",
    )
    return any(token in segment for token in direct_tokens) or (
        imports_coordinator and ".save(" in segment
    )


def _is_registered_or_guarded(
    source: str,
    registered: set[str],
    *,
    text: str | None = None,
) -> bool:
    if source in registered or source in DELEGATIONS:
        return True
    filename, symbol = source.split(":", 1)
    if text is None:
        text = (SOURCE_ROOT / filename).read_text(encoding="utf-8-sig")
    return bool(_route_markers_in_text(text, symbol, filename=filename))


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
    registered = _registered_sources()
    uncovered: dict[str, list[str]] = {}
    for path in sorted(SOURCE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8-sig")
        imports_coordinator = _imports_save_coordinator(text)
        for source, segment in _iter_function_sources(path.name, text):
            if not _may_contain_protected_mutation(
                segment,
                imports_coordinator=imports_coordinator,
            ):
                continue
            signals = _protected_mutation_signals(
                segment,
                imports_coordinator=imports_coordinator,
            )
            if signals and not _is_registered_or_guarded(source, registered, text=text):
                uncovered[source] = sorted(signals)
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


def test_source_policy_detects_every_d1_protected_mutation_shape() -> None:
    snippets = (
        "(root / '.bai-project' / 'x').write_text('x')",
        "source.replace(root / '.bai-project' / 'x')",
        "source.rename(root / '.bai-project' / 'x')",
        "AtomicJsonWriter.write(ProductProjectManifestStore.path(root).with_name('x'), {})",
        "AtomicJsonWriter.write(ProductProjectManifestStore.path(root), {})",
        "with _exclusive_project_lock(ProductProjectManifestStore.path(root)): pass",
        "with _exclusive_project_lock(_manifest_path(root)): pass",
        "with exclusive_file_update_lock(ProductProjectManifestStore.path(root).with_name('x')): pass",
    )
    for snippet in snippets:
        assert _protected_mutation_signals(f"def unsafe(root, source):\n    {snippet}\n"), snippet


def test_source_policy_does_not_accept_a_marker_in_a_sibling_method() -> None:
    text = """
class Example:
    def guarded(self):
        return 'PMST-R003'

    def unsafe(self, root):
        AtomicJsonWriter.write(root / '.bai-project' / 'jobs.json', {})
"""
    assert not _contains_route_marker_in_text(
        text,
        "Example.unsafe",
        "PMST-R003",
        filename="synthetic.py",
    )


def test_source_policy_uses_module_import_context_for_coordinator_save() -> None:
    module_text = """
from ai_video_production.project_save import ProductProjectSaveCoordinator

class Example:
    def unsafe(self, coordinator, root):
        coordinator.save(root, object(), {})
"""
    segment = ast.get_source_segment(
        module_text,
        _node_for_text(module_text, "Example.unsafe", filename="synthetic.py"),
    )
    assert segment is not None
    assert _protected_mutation_signals(
        segment,
        imports_coordinator=_imports_save_coordinator(module_text),
    ) == {
        "ProductProjectSaveCoordinator.*.save"
    }


def test_class_registration_does_not_register_every_method() -> None:
    text = """
class Example:
    def unsafe(self, root):
        AtomicJsonWriter.write(root / '.bai-project' / 'x', {})
"""
    assert not _is_registered_or_guarded(
        "synthetic.py:Example.unsafe",
        {"synthetic.py:Example"},
        text=text,
    )
