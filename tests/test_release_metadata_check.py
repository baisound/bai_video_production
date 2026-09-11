from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "ci" / "check-release-metadata.py"
SPEC = spec_from_file_location("release_metadata", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=repo, text=True, encoding="utf-8"
    ).strip()


def _write_versions(repo: Path, version: str, *, pyproject_extra: str = "") -> None:
    values = {
        "pyproject.toml": f'[project]\nversion = "{version}"\n{pyproject_extra}',
        "CITATION.cff": f'version: "{version}"\n',
        "src/ai_video_production/__init__.py": f'__version__ = "{version}"\n',
        "src/ai_video_production/connection_settings_web.py": f'PRODUCT_VERSION = "{version}"\n',
        "src/ai_video_production/subtitle_workspace_web.py": f'PRODUCT_VERSION = "{version}"\n',
    }
    for name, content in values.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def metadata_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    repo = tmp_path / "metadata-repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "release-metadata@example.invalid")
    _git(repo, "config", "user.name", "Release Metadata Test")
    _write_versions(repo, "1.2.3")
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3] - 2026-01-01\n", encoding="utf-8")
    base = _commit(repo, "base")
    monkeypatch.setattr(MODULE, "ROOT", repo)
    return repo, base


def _run(repo: Path, base: str) -> int:
    return MODULE.main(["--base", base, "--head", _git(repo, "rev-parse", "HEAD")])


def test_release_versions_are_consistent() -> None:
    values = MODULE.versions()
    assert len(set(values.values())) == 1


def test_workflow_checks_exact_head_without_actor_exemption() -> None:
    workflow = (SCRIPT.parents[2] / ".github/workflows/release-metadata-check.yml").read_text(
        encoding="utf-8"
    )
    assert "release-metadata:" in workflow
    assert "ref: ${{ github.event.pull_request.head.sha }}" in workflow
    assert '--base "${{ github.event.pull_request.base.sha }}"' in workflow
    assert '--head "${{ github.event.pull_request.head.sha }}"' in workflow
    assert "--actor" not in workflow


@pytest.mark.parametrize(
    ("path", "content"),
    [
        ("src/ai_video_production/feature.py", "ENABLED = True\n"),
        ("schemas/example.schema.json", "{}\n"),
        ("tools/windows/run-example.ps1", "Write-Output 'ok'\n"),
    ],
)
def test_ordinary_product_change_does_not_require_changelog(
    metadata_repo: tuple[Path, str],
    path: str,
    content: str,
) -> None:
    repo, base = metadata_repo
    source = repo / path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(content, encoding="utf-8")
    _commit(repo, "ordinary product change")

    assert _run(repo, base) == 0


def test_pyproject_dependency_change_does_not_require_changelog(
    metadata_repo: tuple[Path, str],
) -> None:
    repo, base = metadata_repo
    _write_versions(repo, "1.2.3", pyproject_extra='dependencies = ["example>=2"]\n')
    _commit(repo, "dependency change")

    assert _run(repo, base) == 0


def test_version_change_without_changelog_fails(metadata_repo: tuple[Path, str]) -> None:
    repo, base = metadata_repo
    _write_versions(repo, "1.3.0")
    _commit(repo, "version only")

    with pytest.raises(SystemExit, match="version changes require CHANGELOG.md"):
        _run(repo, base)


def test_actor_does_not_exempt_version_change(metadata_repo: tuple[Path, str]) -> None:
    repo, base = metadata_repo
    _write_versions(repo, "1.3.0")
    head = _commit(repo, "automated version only")

    with pytest.raises(SystemExit, match="version changes require CHANGELOG.md"):
        MODULE.main(
            [
                "--base",
                base,
                "--head",
                head,
                "--actor",
                "dependabot[bot]",
            ]
        )


def test_version_change_with_release_heading_passes(metadata_repo: tuple[Path, str]) -> None:
    repo, base = metadata_repo
    _write_versions(repo, "1.3.0")
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [1.3.0] - 2026-02-01\n", encoding="utf-8"
    )
    _commit(repo, "release metadata")

    assert _run(repo, base) == 0


def test_version_change_with_only_unreleased_heading_fails(
    metadata_repo: tuple[Path, str],
) -> None:
    repo, base = metadata_repo
    _write_versions(repo, "1.3.0")
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    _commit(repo, "incomplete release metadata")

    with pytest.raises(SystemExit, match=r"has no \[1\.3\.0\] release heading"):
        _run(repo, base)


def test_mismatched_head_versions_fail(metadata_repo: tuple[Path, str]) -> None:
    repo, base = metadata_repo
    (repo / "CITATION.cff").write_text('version: "9.9.9"\n', encoding="utf-8")
    _commit(repo, "mismatched versions")

    with pytest.raises(SystemExit, match="version mismatch at working tree"):
        _run(repo, base)


def test_missing_working_tree_version_file_fails_cleanly(
    metadata_repo: tuple[Path, str],
) -> None:
    repo, base = metadata_repo
    (repo / "CITATION.cff").unlink()

    with pytest.raises(SystemExit, match="cannot read CITATION.cff in working tree"):
        MODULE.main(["--base", base, "--head", base])


def test_invalid_base_ref_fails_cleanly(metadata_repo: tuple[Path, str]) -> None:
    repo, _base = metadata_repo
    source = repo / "src/ai_video_production/feature.py"
    source.write_text("ENABLED = True\n", encoding="utf-8")
    _commit(repo, "ordinary product change")

    with pytest.raises(SystemExit, match="cannot compare base missing-base-ref"):
        MODULE.main(["--base", "missing-base-ref", "--head", "HEAD"])
