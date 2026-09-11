"""Select and run bounded tests for ordinary pull-request feedback."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


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


def _git_output(arguments: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        rendered = " ".join(arguments)
        raise SystemExit(f"fast test selection: git {rendered} failed") from exc


def changed_files(base: str, head: str) -> set[str]:
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
            return {
                line.strip().replace("\\", "/")
                for line in output.split("\0")
                if line.strip()
            }
    output = _git_output(
        ["diff", "--name-only", "-z", f"{normalized_base}...{normalized_head}"]
    )
    return {
        line.strip().replace("\\", "/")
        for line in output.split("\0")
        if line.strip()
    }


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


def _requires_all_tests(changed_paths: set[str]) -> bool:
    if changed_paths & BROAD_IMPACT_PATHS:
        return True
    return any(
        (path.startswith("requirements") and path.endswith((".in", ".txt")))
        or (path.startswith("tests/") and path.endswith("/conftest.py"))
        or (path.startswith("src/") and path.endswith("/__init__.py"))
        for path in changed_paths
    )


def select_tests(changed: Iterable[str], *, root: Path = ROOT) -> list[str]:
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
    changed_paths = {path.replace("\\", "/") for path in changed}

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
        if path.startswith(("src/", "schemas/", "tools/", "tests/"))
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
    if resolved_target == resolved_allowed or resolved_allowed not in resolved_target.parents:
        raise SystemExit("fast test selection: basetemp is outside the allowed temp root")
    if len(resolved_target.parts) <= 2 or resolved_target.parent == Path(resolved_target.anchor):
        raise SystemExit("fast test selection: basetemp is too close to a filesystem root")
    if resolved_target.exists():
        raise SystemExit("fast test selection: basetemp already exists")
    return resolved_target


def _run_pytest(tests: list[str], *, basetemp: Path, timeout: int) -> int:
    if not tests:
        return 0
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--allowed-temp-root", type=Path, required=True)
    parser.add_argument("--basetemp", type=Path, required=True)
    args = parser.parse_args(argv)

    selected = select_tests(changed_files(args.base, args.head))
    parallel = [path for path in selected if path not in SERIAL_TESTS]
    serial = [path for path in selected if path in SERIAL_TESTS]
    safe_root = validate_basetemp(args.basetemp, args.allowed_temp_root)
    print(f"fast test selection: {len(selected)} files")
    for path in selected:
        print(f"  {path}")

    result = _run_pytest(parallel, basetemp=safe_root / "parallel", timeout=120)
    if result != 0:
        return result
    return _run_pytest(serial, basetemp=safe_root / "serial", timeout=300)


if __name__ == "__main__":
    raise SystemExit(main())
