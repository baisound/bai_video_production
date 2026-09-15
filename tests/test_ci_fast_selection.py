from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess

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

    assert MODULE.changed_files("", "abc123") == [
        MODULE.ChangedPath("A", "pyproject.toml"),
        MODULE.ChangedPath("A", "src/ai_video_production/widget.py"),
    ]
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
        return "M\0src/ai_video_production/widget.py\0A\0tests/test_line\nbreak.py\0"

    monkeypatch.setattr(MODULE, "_git_output", fake_git_output)

    assert MODULE.changed_files(" base ", " head ") == [
        MODULE.ChangedPath("M", "src/ai_video_production/widget.py"),
        MODULE.ChangedPath("A", "tests/test_line\nbreak.py"),
    ]
    assert calls == [["diff", "--name-status", "-z", "--find-renames", "base...head"]]


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


@pytest.mark.parametrize("path", [
    "native/task047_obs_voice_capture/controller/BaiVoiceCaptureController.cs",
    "packaging/task047_obs_voice_capture_installer.iss", "scripts/worker.py",
    "requirements/task054-training.lock", "config/runtime.toml",
    "profiles/production.json", "build-windows-exe.bat", "unknown-product/engine.bin",
    ".github/workflows/new-policy.yml", "README-new-product.md",
])
def test_unknown_or_native_product_paths_select_all(tmp_path: Path, path: str) -> None:
    _test_tree(tmp_path)
    assert MODULE.select_tests({path}, root=tmp_path) == sorted(
        item.relative_to(tmp_path).as_posix() for item in (tmp_path / "tests").rglob("test_*.py")
    )


@pytest.mark.parametrize("path", ["README.md", "docs/ai-team/tasks/TASK-087/task.md", ".github/ISSUE_TEMPLATE/bug_report.yml"])
def test_exact_documentation_allowlist_is_baseline_only(tmp_path: Path, path: str) -> None:
    _test_tree(tmp_path)
    assert MODULE.select_tests({path}, root=tmp_path) == sorted(MODULE.ALWAYS_TESTS)


@pytest.mark.parametrize("status", ["D", "R100", "C100", "T", "U"])
def test_destructive_status_and_prefix_collision_select_all(tmp_path: Path, status: str) -> None:
    _test_tree(tmp_path)
    (tmp_path / "tests/test_connection_settings_store.py").write_text("", encoding="utf-8")
    item = MODULE.ChangedPath(status, "tests/test_connection_settings.py", "tests/test_old.py" if status[0] in "RC" else None)
    assert MODULE.select_tests([item], root=tmp_path) == sorted(
        path.relative_to(tmp_path).as_posix() for path in (tmp_path / "tests").rglob("test_*.py")
    )


def test_status_parser_preserves_both_rename_copy_paths_and_newlines() -> None:
    assert MODULE.parse_changed_files("R100\0old\nname.py\0new.py\0C090\0src.py\0copy.py\0") == [
        MODULE.ChangedPath("R100", "new.py", "old\nname.py"),
        MODULE.ChangedPath("C090", "copy.py", "src.py"),
    ]


@pytest.mark.parametrize("raw", ["M", "M\0file", "M\0", "M\0\0", "R100\0old\0", "Q\0file\0", "R101\0old\0new\0", "C\0old\0new\0", "M\0../outside.py\0", "M\0docs/../src/engine.py\0", "M\0/absolute.py\0", "M\0C:/absolute.py\0"])
def test_malformed_status_fails_closed(raw: str) -> None:
    with pytest.raises(SystemExit):
        MODULE.parse_changed_files(raw)


def test_existing_pytest_child_is_rejected_without_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    child = tmp_path / "parallel"
    child.mkdir()
    marker = child / "foreign-marker"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: pytest.fail("must not run pytest"))
    with pytest.raises(SystemExit, match="already exists"):
        MODULE._run_pytest(["tests/test_widget.py"], basetemp=child, timeout=120)
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_prepare_and_child_modes_never_select_or_run_tests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(MODULE, "changed_files", lambda *a: pytest.fail("selection not allowed"))
    monkeypatch.setattr(MODULE, "_run_pytest", lambda *a, **k: pytest.fail("pytest not allowed"))
    root = tmp_path / "operation"
    assert MODULE.main(["--prepare-only", "--allowed-temp-root", str(tmp_path), "--basetemp", str(root)]) == 0
    child = root / "parallel"
    assert MODULE.main(["--check-child", "--allowed-temp-root", str(root), "--basetemp", str(child)]) == 0
    assert not child.exists()
    child.mkdir()
    with pytest.raises(SystemExit, match="already exists"):
        MODULE.main(["--check-child", "--allowed-temp-root", str(root), "--basetemp", str(child)])


@pytest.mark.parametrize("arguments", [
    ["--prepare-only"], ["--check-child"], ["--prepare-only", "--check-child"],
    ["--resolve-release-tag", "v1.0.0", "--prepare-only"],
    ["--verify-release-tag", "v1.0.0"], ["--expected-commit-sha", "a" * 40],
])
def test_partial_or_mixed_modes_fail_before_effects(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> None:
    monkeypatch.setattr(MODULE, "_git_output", lambda *a: pytest.fail("Git must not execute"))
    monkeypatch.setattr(MODULE, "prepare_basetemp_root", lambda *a: pytest.fail("no output creation"))
    with pytest.raises(SystemExit):
        MODULE.main(arguments)


def test_basetemp_rejects_symlink_escape_where_supported(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    link = allowed / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        # Native symlink privilege is not assumed; the resolve/containment case
        # is exercised on supported hosts, not reported as a native PASS here.
        pytest.skip("native symlink creation privilege is unavailable")
    with pytest.raises(SystemExit, match="outside the allowed temp root"):
        MODULE.validate_basetemp(link / "new-operation", allowed)
    assert not (outside / "new-operation").exists()


def test_allowed_operation_root_alias_cannot_reauthorize_external_child(tmp_path: Path) -> None:
    original = tmp_path / "operation"
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    try:
        original.symlink_to(replacement, target_is_directory=True)
    except OSError:
        pytest.skip("native symlink creation privilege is unavailable")
    with pytest.raises(SystemExit, match="noncanonical alias"):
        MODULE.validate_basetemp(original / "parallel", original)
    assert not (replacement / "parallel").exists()


def _fixture_git(root: Path, *arguments: str) -> str:
    return subprocess.check_output([
        "git", "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "tag.gpgSign=false", "-c", "init.templateDir=",
        "-c", f"core.hooksPath={root / 'unused-hooks'}", *arguments,
    ], cwd=root, text=True, encoding="utf-8", stderr=subprocess.PIPE, timeout=20).strip()


@pytest.fixture
def tag_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "source"
    remote = tmp_path / "local-origin.git"
    repo.mkdir()
    _fixture_git(repo, "init", "--quiet")
    _fixture_git(repo, "init", "--bare", "--quiet", str(remote))
    _fixture_git(repo, "remote", "add", "origin", str(remote))
    _fixture_git(repo, "commit", "--allow-empty", "-m", "synthetic identity one")
    _fixture_git(repo, "tag", "-a", "v1.0.0", "-m", "synthetic annotated tag")
    _fixture_git(repo, "push", "--quiet", "origin", "refs/tags/v1.0.0")
    monkeypatch.setattr(MODULE, "ROOT", repo)
    return repo, remote


def test_annotated_tag_resolution_and_remote_verification(tag_repository: tuple[Path, Path]) -> None:
    repo, _ = tag_repository
    identity = MODULE.resolve_release_tag("v1.0.0")
    assert identity == {"tag_object_sha": _fixture_git(repo, "rev-parse", "refs/tags/v1.0.0"), "commit_sha": _fixture_git(repo, "rev-parse", "HEAD")}
    MODULE.verify_release_tag("v1.0.0", **identity)


def test_lightweight_and_absent_tag_fail_closed(tag_repository: tuple[Path, Path]) -> None:
    repo, _ = tag_repository
    _fixture_git(repo, "tag", "v1.0.1")
    _fixture_git(repo, "push", "--quiet", "origin", "refs/tags/v1.0.1")
    with pytest.raises(SystemExit, match="annotated tag required"):
        MODULE.resolve_release_tag("v1.0.1")
    with pytest.raises(SystemExit, match="failed"):
        MODULE.resolve_release_tag("v9.9.9")


@pytest.mark.parametrize("move_commit", [False, True])
def test_remote_tag_object_or_peeled_commit_move_is_rejected(tag_repository: tuple[Path, Path], move_commit: bool) -> None:
    repo, remote = tag_repository
    identity = MODULE.resolve_release_tag("v1.0.0")
    if move_commit:
        _fixture_git(repo, "commit", "--allow-empty", "-m", "synthetic identity two")
    _fixture_git(repo, "tag", "-a", "v1.0.2", "-m", "different synthetic tag object")
    _fixture_git(repo, "push", "--quiet", "origin", "refs/tags/v1.0.2")
    replacement = _fixture_git(repo, "rev-parse", "refs/tags/v1.0.2")
    # CAS only inside this test's freshly created local bare repository. No
    # external remote, force-push, real tag, or user repository is modified.
    _fixture_git(repo, "--git-dir", str(remote), "update-ref", "refs/tags/v1.0.0", replacement, identity["tag_object_sha"])
    with pytest.raises(SystemExit, match="changed or is absent"):
        MODULE.verify_release_tag("v1.0.0", **identity)


@pytest.mark.parametrize("tag", ["--help", "main", "refs/tags/v1.0.0", "v1..0", "v1.0.0\n", "v1;echo", "v1$(echo)", "v1.0.0."])
def test_invalid_tag_never_reaches_git(monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    monkeypatch.setattr(MODULE, "_git_output", lambda *a: pytest.fail("invalid tag must not reach Git"))
    with pytest.raises(SystemExit, match="invalid version tag"):
        MODULE.resolve_release_tag(tag)


@pytest.mark.parametrize("response", [
    "not-a-tag", "a" * 40 + "\trefs/tags/v1.0.0\n", "a" * 40 + "\trefs/tags/unexpected\n",
    "a" * 40 + "\trefs/tags/v1.0.0\n" + "a" * 40 + "\trefs/tags/v1.0.0\n",
    "INVALID\trefs/tags/v1.0.0\n",
])
def test_malformed_or_incomplete_remote_tag_response_fails(monkeypatch: pytest.MonkeyPatch, response: str) -> None:
    monkeypatch.setattr(MODULE, "_git_output", lambda args: "" if args[0] == "check-ref-format" else response)
    with pytest.raises(SystemExit):
        MODULE.verify_release_tag("v1.0.0", tag_object_sha="a" * 40, commit_sha="b" * 40)


def test_git_command_failure_and_timeout_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for error in [subprocess.CalledProcessError(1, ["git"]), subprocess.TimeoutExpired(["git"], 30)]:
        def fail(*args: object, **kwargs: object) -> str:
            raise error
        monkeypatch.setattr(MODULE.subprocess, "check_output", fail)
        with pytest.raises(SystemExit, match="failed"):
            MODULE.resolve_release_tag("v1.0.0")


def test_real_git_status_keeps_deletion_collision_and_rename(tag_repository: tuple[Path, Path]) -> None:
    repo, _ = tag_repository
    _test_tree(repo)
    old = repo / "tests/test_connection_settings.py"
    old.write_text("original unique fixture", encoding="utf-8")
    (repo / "tests/test_connection_settings_store.py").write_text("", encoding="utf-8")
    _fixture_git(repo, "add", "--", "tests")
    _fixture_git(repo, "commit", "-m", "synthetic selection base")
    base = _fixture_git(repo, "rev-parse", "HEAD")
    old.unlink()
    _fixture_git(repo, "mv", "tests/test_widget.py", "tests/test_renamed_widget.py")
    _fixture_git(repo, "add", "--", "tests/test_connection_settings.py")
    _fixture_git(repo, "commit", "-m", "synthetic delete and rename")
    changes = MODULE.changed_files(base, "HEAD")
    assert any(item.status == "D" and item.path == "tests/test_connection_settings.py" for item in changes)
    assert any(item.status.startswith("R") and item.old_path == "tests/test_widget.py" and item.path == "tests/test_renamed_widget.py" for item in changes)
    assert MODULE.select_tests(changes, root=repo) == sorted(path.relative_to(repo).as_posix() for path in (repo / "tests").rglob("test_*.py"))
