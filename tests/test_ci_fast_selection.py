from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "ci" / "run-fast-tests.py"
SPEC = spec_from_file_location("ci_fast_selection", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _test_tree(root: Path) -> None:
    tests = root / "tests"
    tests.mkdir(parents=True)
    for name, content in {
        "test_ci_fast_selection.py": "",
        "test_oss_readiness.py": "",
        "test_release_metadata_check.py": "",
        "test_widget.py": "from ai_video_production.widget import Widget\n",
        "test_feature_flow.py": (
            "from ai_video_production.widget import Widget\n"
            'FIXTURE = "tests/fixtures/widget.json"\n'
        ),
        "test_schema_user.py": 'SCHEMA = "widget-state.schema.json"\n',
        "test_unrelated.py": "",
        "test_task047_obs_installer_contract.py": "",
    }.items():
        (tests / name).write_text(content, encoding="utf-8")


def test_baseline_tests_are_always_selected(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests([], root=tmp_path)

    assert selected == sorted(MODULE.ALWAYS_TESTS)


def test_changed_test_and_corresponding_source_test_are_selected(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(
        {"src/ai_video_production/widget.py", "tests/test_unrelated.py"},
        root=tmp_path,
    )

    assert "tests/test_widget.py" in selected
    assert "tests/test_feature_flow.py" in selected
    assert "tests/test_unrelated.py" in selected


def test_schema_reference_selects_consumer_test(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests({"schemas/widget-state.schema.json"}, root=tmp_path)

    assert "tests/test_schema_user.py" in selected
    assert "tests/test_unrelated.py" not in selected


def test_changed_fixture_selects_referencing_test(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(
        {"tests/fixtures/widget.json"}, root=tmp_path
    )

    assert "tests/test_feature_flow.py" in selected
    assert "tests/test_unrelated.py" not in selected


def test_changed_installer_contract_is_kept_for_serial_execution(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(
        {"tests/test_task047_obs_installer_contract.py"}, root=tmp_path
    )

    assert "tests/test_task047_obs_installer_contract.py" in selected


def test_changed_nested_test_is_selected(tmp_path: Path) -> None:
    _test_tree(tmp_path)
    nested = tmp_path / "tests" / "integration" / "test_nested.py"
    nested.parent.mkdir()
    nested.write_text("", encoding="utf-8")

    selected = MODULE.select_tests(
        {"tests/integration/test_nested.py"}, root=tmp_path
    )

    assert "tests/integration/test_nested.py" in selected


def test_deleted_test_falls_back_to_every_remaining_test(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(
        {"tests/test_removed.py"}, root=tmp_path
    )

    expected = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "tests").rglob("test_*.py")
    )
    assert selected == expected


def test_unmapped_product_change_falls_back_to_every_test(tmp_path: Path) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(
        {"src/ai_video_production/unknown_boundary.py"}, root=tmp_path
    )

    expected = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "tests").rglob("test_*.py")
    )
    assert selected == expected


@pytest.mark.parametrize(
    "changed",
    [
        {"pyproject.toml"},
        {"tests/conftest.py"},
        {"tests/integration/conftest.py"},
        {"requirements-dev.txt"},
        {"src/ai_video_production/__init__.py"},
    ],
)
def test_dependency_or_shared_test_configuration_selects_every_test(
    tmp_path: Path, changed: set[str]
) -> None:
    _test_tree(tmp_path)

    selected = MODULE.select_tests(changed, root=tmp_path)

    expected = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "tests").rglob("test_*.py")
    )
    assert selected == expected


def test_missing_baseline_test_fails_closed(tmp_path: Path) -> None:
    _test_tree(tmp_path)
    (tmp_path / "tests" / "test_oss_readiness.py").unlink()

    with pytest.raises(SystemExit, match="required baseline test is missing"):
        MODULE.select_tests([], root=tmp_path)


def test_root_commit_fallback_treats_all_tracked_paths_as_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_git_output(arguments: list[str]) -> str:
        calls.append(arguments)
        if arguments[0] == "rev-parse":
            raise SystemExit("no parent")
        return "pyproject.toml\0src/ai_video_production/widget.py\0"

    monkeypatch.setattr(MODULE, "_git_output", fake_git_output)

    assert MODULE.changed_files("", "abc123") == {
        "pyproject.toml",
        "src/ai_video_production/widget.py",
    }
    assert calls == [
        ["rev-parse", "abc123^{commit}^"],
        ["ls-tree", "-r", "--name-only", "-z", "abc123"],
    ]


def test_changed_files_uses_nul_delimited_merge_base_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_git_output(arguments: list[str]) -> str:
        calls.append(arguments)
        return "src/ai_video_production/widget.py\0tests/test_line\nbreak.py\0"

    monkeypatch.setattr(MODULE, "_git_output", fake_git_output)

    assert MODULE.changed_files(" base ", " head ") == {
        "src/ai_video_production/widget.py",
        "tests/test_line\nbreak.py",
    }
    assert calls == [["diff", "--name-only", "-z", "base...head"]]


def test_invalid_explicit_base_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_git_output(arguments: list[str]) -> str:
        raise SystemExit("bad ref")

    monkeypatch.setattr(MODULE, "_git_output", fake_git_output)

    with pytest.raises(SystemExit, match="bad ref"):
        MODULE.changed_files("missing", "HEAD")


def test_basetemp_must_be_new_and_below_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "runner-temp"
    allowed.mkdir()
    target = allowed / "unique-run"

    assert MODULE.validate_basetemp(target, allowed) == target.resolve()

    with pytest.raises(SystemExit, match="outside the allowed temp root"):
        MODULE.validate_basetemp(tmp_path / "foreign", allowed)
    target.mkdir()
    with pytest.raises(SystemExit, match="already exists"):
        MODULE.validate_basetemp(target, allowed)


def test_basetemp_parent_is_created_once_for_parallel_and_serial_children(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "runner-temp"
    allowed.mkdir()
    target = allowed / "unique-run"

    prepared = MODULE.prepare_basetemp_root(target, allowed)

    assert prepared == target.resolve()
    assert prepared.is_dir()
    assert not (prepared / "parallel").exists()
    assert not (prepared / "serial").exists()
    with pytest.raises(SystemExit, match="already exists"):
        MODULE.prepare_basetemp_root(target, allowed)


def test_pytest_runner_uses_bounded_parallel_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed: dict[str, object] = {}

    class Result:
        returncode = 7

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> Result:
        observed.update(command=command, cwd=cwd, check=check)
        return Result()

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    basetemp = tmp_path / "bounded"

    assert MODULE._run_pytest(
        ["tests/test_widget.py"], basetemp=basetemp, timeout=120
    ) == 7

    command = observed["command"]
    assert isinstance(command, list)
    assert command[:4] == [MODULE.sys.executable, "-m", "pytest", "-q"]
    assert ["-n", "2"] == command[4:6]
    assert "--dist" in command and "loadfile" in command
    assert "--timeout=120" in command
    assert "--max-worker-restart=0" in command
    assert command[-3:] == ["--basetemp", str(basetemp), "tests/test_widget.py"]
    assert observed["cwd"] == MODULE.ROOT
    assert observed["check"] is False
