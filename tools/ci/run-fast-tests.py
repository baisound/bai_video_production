"""Select and run bounded tests for ordinary pull-request feedback."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, NamedTuple


ROOT = Path(__file__).resolve().parents[2]
ALWAYS_TESTS = (
    "tests/test_ci_fast_selection.py",
    "tests/test_oss_readiness.py",
    "tests/test_release_metadata_check.py",
)
SERIAL_TESTS = {"tests/test_task047_obs_installer_contract.py"}
BROAD_IMPACT_PATHS = {
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "tests/conftest.py",
    "tox.ini",
    "uv.lock",
}
ZERO_SHA = "0" * 40
CORRESPONDENCE_PREFIXES = ("src/", "schemas/", "tools/", "tests/")
BASELINE_ONLY_PREFIXES = ("docs/", ".github/ISSUE_TEMPLATE/")
BASELINE_ONLY_PATHS = {
    "README.md", "README.en.md", "LICENSE.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "GOVERNANCE.md", "SUPPORT.md",
    "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "CITATION.cff", "AGENTS.md",
    "PROJECT.md", ".gitignore", ".gitattributes", ".editorconfig",
    ".github/pull_request_template.md",
}
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
TAG_PATTERN = re.compile(r"v[0-9][A-Za-z0-9._+-]*")


class ChangedPath(NamedTuple):
    status: str
    path: str
    old_path: str | None = None


def _git_output(arguments: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        rendered = " ".join(arguments)
        raise SystemExit(f"fast test selection: git {rendered} failed") from exc


def parse_changed_files(output: str) -> list[ChangedPath]:
    """Preserve NUL-delimited status/path records; never guess truncated data."""
    if not output:
        return []
    if not output.endswith("\0"):
        raise SystemExit("fast test selection: truncated change status")
    tokens = output.split("\0")[:-1]
    result: list[ChangedPath] = []
    cursor = 0
    while cursor < len(tokens):
        status = tokens[cursor]
        cursor += 1
        if not re.fullmatch(r"(?:[ADTU]|M(?:[0-9]{1,3})?|[RC][0-9]{1,3})", status):
            raise SystemExit("fast test selection: unknown change status")
        if len(status) > 1 and int(status[1:]) > 100:
            raise SystemExit("fast test selection: invalid change score")
        count = 2 if status[0] in "RC" else 1
        paths = tokens[cursor:cursor + count]
        if len(paths) != count or any(not path for path in paths):
            raise SystemExit("fast test selection: truncated change paths")
        if any(
            path.startswith("/") or re.match(r"[A-Za-z]:", path)
            or any(part in {"", ".", ".."} for part in path.split("/"))
            for path in paths
        ):
            raise SystemExit("fast test selection: non-relative change path")
        cursor += count
        result.append(ChangedPath(status, paths[-1], paths[0] if count == 2 else None))
    return result


def changed_files(base: str, head: str) -> list[ChangedPath]:
    normalized_base = base.strip()
    normalized_head = head.strip() or "HEAD"
    if not normalized_base or normalized_base == ZERO_SHA:
        try:
            normalized_base = _git_output(
                ["rev-parse", f"{normalized_head}^{{commit}}^"]
            ).strip()
        except SystemExit:
            # A root commit has no parent. Treat every tracked path as changed so
            # selection remains conservative instead of silently running only the
            # baseline tests.
            output = _git_output(
                ["ls-tree", "-r", "--name-only", "-z", normalized_head]
            )
            if output and not output.endswith("\0"):
                raise SystemExit("fast test selection: truncated tracked paths")
            return [ChangedPath("A", path) for path in output.split("\0") if path]
    output = _git_output(
        ["diff", "--name-status", "-z", "--find-renames", f"{normalized_base}...{normalized_head}"]
    )
    return parse_changed_files(output)


def _normalized_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _selection_needles(path: str) -> set[str]:
    item = Path(path)
    suffixes = "".join(item.suffixes)
    stem = item.name[: -len(suffixes)] if suffixes else item.name
    normalized = _normalized_token(stem)
    needles = {item.name, path.replace("\\", "/")}
    if len(normalized) >= 6 and normalized not in {"init", "conftest"}:
        needles.add(normalized)
    normalized_path = path.replace("\\", "/")
    if normalized_path.startswith("src/") and normalized_path.endswith(".py"):
        module_path = normalized_path[len("src/") : -len(".py")]
        if module_path.endswith("/__init__"):
            module_path = module_path[: -len("/__init__")]
        needles.add(module_path.replace("/", "."))
    return needles


def _baseline_only(path: str) -> bool:
    return path in BASELINE_ONLY_PATHS or path.startswith(BASELINE_ONLY_PREFIXES)


def _requires_all_tests(changed_paths: set[str]) -> bool:
    if changed_paths & BROAD_IMPACT_PATHS:
        return True
    return any(
        path.startswith("requirements")
        or (path.startswith("tests/") and path.endswith("/conftest.py"))
        or (path.startswith("src/") and path.endswith("/__init__.py"))
        or (not path.startswith(CORRESPONDENCE_PREFIXES) and not _baseline_only(path))
        for path in changed_paths
    )


def select_tests(changed: Iterable[str | ChangedPath], *, root: Path = ROOT) -> list[str]:
    available = {
        path.relative_to(root).as_posix(): path
        for path in (root / "tests").rglob("test_*.py")
        if path.is_file()
    }
    missing_baseline = sorted(set(ALWAYS_TESTS) - available.keys())
    if missing_baseline:
        raise SystemExit(
            "fast test selection: required baseline test is missing: "
            + ", ".join(missing_baseline)
        )
    selected = {name for name in ALWAYS_TESTS if name in available}
    records = [item if isinstance(item, ChangedPath) else ChangedPath("M", item) for item in changed]
    changed_paths = {path for item in records for path in (item.path, item.old_path) if path is not None}

    if any(
        item.status[0] not in "AM"
        and any(not _baseline_only(path) for path in (item.path, item.old_path) if path is not None)
        for item in records
    ):
        return sorted(available)

    if _requires_all_tests(changed_paths):
        return sorted(available)

    for path in changed_paths:
        if (
            path.startswith("tests/")
            and Path(path).name.startswith("test_")
            and path.endswith(".py")
            and path in available
        ):
            selected.add(path)

    relevant_changes = [
        path
        for path in changed_paths
        if path.startswith(CORRESPONDENCE_PREFIXES)
    ]
    content_cache: dict[str, str] = {}
    for changed_path in relevant_changes:
        needles = _selection_needles(changed_path)
        normalized_needles = {
            needle
            for needle in needles
            if "/" not in needle and "\\" not in needle
        }
        matched: set[str] = set()
        for name, test_path in available.items():
            normalized_name = _normalized_token(test_path.stem)
            if any(
                needle in normalized_name
                for needle in normalized_needles
                if len(needle) >= 6
            ):
                matched.add(name)
                continue
            if name not in content_cache:
                content_cache[name] = test_path.read_text(
                    encoding="utf-8", errors="replace"
                )
            content = content_cache[name]
            if any(needle in content for needle in needles):
                matched.add(name)

        if not matched:
            return sorted(available)
        selected.update(matched)

    return sorted(selected)


def validate_basetemp(target: Path, allowed_root: Path) -> Path:
    try:
        resolved_allowed = allowed_root.resolve(strict=True)
    except OSError as exc:
        raise SystemExit("fast test selection: allowed temp root is unavailable") from exc
    resolved_target = target.resolve(strict=False)
    if resolved_allowed != allowed_root.absolute():
        raise SystemExit("fast test selection: allowed temp root uses a noncanonical alias")
    if resolved_target == resolved_allowed or resolved_allowed not in resolved_target.parents:
        raise SystemExit("fast test selection: basetemp is outside the allowed temp root")
    if resolved_target != target.absolute():
        raise SystemExit("fast test selection: basetemp uses a noncanonical alias")
    if len(resolved_target.parts) <= 2 or resolved_target.parent == Path(resolved_target.anchor):
        raise SystemExit("fast test selection: basetemp is too close to a filesystem root")
    if resolved_target.exists():
        raise SystemExit("fast test selection: basetemp already exists")
    return resolved_target


def prepare_basetemp_root(target: Path, allowed_root: Path) -> Path:
    safe_root = validate_basetemp(target, allowed_root)
    try:
        safe_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as exc:
        raise SystemExit("fast test selection: basetemp could not be created") from exc
    return safe_root


def _run_pytest(tests: list[str], *, basetemp: Path, timeout: int) -> int:
    if not tests:
        return 0
    # pytest owns/deletes its basetemp. Never let it reuse an existing child.
    validate_basetemp(basetemp, basetemp.parent)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-n",
        "2",
        "--dist",
        "loadfile",
        f"--timeout={timeout}",
        "--max-worker-restart=0",
        "--durations=20",
        "--basetemp",
        str(basetemp),
        *tests,
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def _release_tag_ref(tag: str) -> str:
    if not TAG_PATTERN.fullmatch(tag) or ".." in tag or tag.endswith("."):
        raise SystemExit("release identity: invalid version tag name")
    ref = f"refs/tags/{tag}"
    _git_output(["check-ref-format", ref])
    return ref


def _sha(value: str) -> str:
    if not SHA_PATTERN.fullmatch(value):
        raise SystemExit("release identity: invalid object SHA")
    return value


def resolve_release_tag(tag: str) -> dict[str, str]:
    """Read one annotated remote tag identity; do not create or move any ref."""
    ref = _release_tag_ref(tag)
    if _git_output(["cat-file", "-t", ref]).strip() != "tag":
        raise SystemExit("release identity: annotated tag required")
    identity = {
        "tag_object_sha": _sha(_git_output(["rev-parse", "--verify", ref]).strip()),
        "commit_sha": _sha(_git_output(["rev-parse", "--verify", f"{ref}^{{commit}}"]).strip()),
    }
    verify_release_tag(tag, **identity)
    return identity


def verify_release_tag(tag: str, *, tag_object_sha: str, commit_sha: str) -> None:
    ref = _release_tag_ref(tag)
    expected = {ref: _sha(tag_object_sha), f"{ref}^{{}}": _sha(commit_sha)}
    output = _git_output(["ls-remote", "--exit-code", "--tags", "origin", ref, f"{ref}^{{}}"])
    observed: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or fields[1] not in expected or fields[1] in observed:
            raise SystemExit("release identity: malformed remote tag response")
        observed[fields[1]] = _sha(fields[0])
    if observed != expected:
        raise SystemExit("release identity: remote annotated tag changed or is absent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--allowed-temp-root", type=Path)
    parser.add_argument("--basetemp", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--check-child", action="store_true")
    modes.add_argument("--resolve-release-tag")
    modes.add_argument("--verify-release-tag")
    parser.add_argument("--expected-tag-object-sha")
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args(argv)

    if args.resolve_release_tag or args.verify_release_tag:
        if args.allowed_temp_root or args.basetemp or args.base or args.head != "HEAD":
            parser.error("release identity mode cannot accept selection/temp arguments")
        if args.resolve_release_tag:
            if args.expected_tag_object_sha or args.expected_commit_sha:
                parser.error("resolution mode does not accept expected identities")
            for key, value in resolve_release_tag(args.resolve_release_tag).items():
                print(f"{key}={value}")
        else:
            if not args.expected_tag_object_sha or not args.expected_commit_sha:
                parser.error("verification requires both expected identities")
            verify_release_tag(args.verify_release_tag, tag_object_sha=args.expected_tag_object_sha, commit_sha=args.expected_commit_sha)
            print("release identity: PASS")
        return 0
    if args.expected_tag_object_sha or args.expected_commit_sha:
        parser.error("expected release identities require verification mode")
    if args.allowed_temp_root is None or args.basetemp is None:
        parser.error("both allowed-temp-root and basetemp are required")
    if args.prepare_only or args.check_child:
        if args.base or args.head != "HEAD":
            parser.error("output-root modes cannot accept selection arguments")
        safe = (prepare_basetemp_root if args.prepare_only else validate_basetemp)(args.basetemp, args.allowed_temp_root)
        print(f"operation_root={safe}")
        return 0

    selected = select_tests(changed_files(args.base, args.head))
    parallel = [path for path in selected if path not in SERIAL_TESTS]
    serial = [path for path in selected if path in SERIAL_TESTS]
    safe_root = prepare_basetemp_root(args.basetemp, args.allowed_temp_root)
    print(f"fast test selection: {len(selected)} files")
    for path in selected:
        print(f"  {path}")

    result = _run_pytest(parallel, basetemp=safe_root / "parallel", timeout=120)
    if result != 0:
        return result
    return _run_pytest(serial, basetemp=safe_root / "serial", timeout=300)


if __name__ == "__main__":
    raise SystemExit(main())
