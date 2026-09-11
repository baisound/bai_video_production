"""Validate version consistency and release-only changelog metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
VERSION_FILES = {
    "pyproject.toml": r'^version = "([^"]+)"',
    "CITATION.cff": r'^version: "([^"]+)"',
    "src/ai_video_production/__init__.py": r'^__version__ = "([^"]+)"',
    "src/ai_video_production/connection_settings_web.py": r'^PRODUCT_VERSION = "([^"]+)"',
    "src/ai_video_production/subtitle_workspace_web.py": r'^PRODUCT_VERSION = "([^"]+)"',
}


def changed_files(base: str, head: str) -> set[str]:
    output = _git_output(
        ["diff", "--name-only", f"{base}...{head}"],
        failure=f"cannot compare base {base} with head {head}",
    )
    return {line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()}


def _git_output(arguments: list[str], *, failure: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"release metadata check: {failure}") from exc


def _extract_version(name: str, text: str) -> str:
    match = re.search(VERSION_FILES[name], text, re.MULTILINE)
    if not match:
        raise SystemExit(f"release metadata check: version not found in {name}")
    return match.group(1)


def versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in VERSION_FILES:
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SystemExit(
                f"release metadata check: cannot read {name} in working tree"
            ) from exc
        found[name] = _extract_version(name, text)
    return found


def versions_at_ref(ref: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in VERSION_FILES:
        text = _git_output(
            ["show", f"{ref}:{name}"],
            failure=f"cannot read {name} at {ref}",
        )
        found[name] = _extract_version(name, text)
    return found


def consistent_version(values: dict[str, str], *, label: str) -> str:
    unique = set(values.values())
    if len(unique) != 1:
        details = ", ".join(f"{name}={value}" for name, value in values.items())
        raise SystemExit(f"release metadata check: version mismatch at {label}: {details}")
    return unique.pop()


def changelog_has_version(changelog: str, version: str) -> bool:
    return re.search(rf"^## \[{re.escape(version)}\](?:\s|$)", changelog, re.MULTILINE) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--actor", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    changed = changed_files(args.base, args.head)
    working_version = consistent_version(versions(), label="working tree")
    base_version = consistent_version(versions_at_ref(args.base), label=f"base {args.base}")
    head_version = consistent_version(versions_at_ref(args.head), label=f"head {args.head}")
    if working_version != head_version:
        raise SystemExit(
            "release metadata check: working tree version "
            f"{working_version} does not match head {args.head} version {head_version}"
        )

    version_changed = base_version != head_version
    if version_changed and "CHANGELOG.md" not in changed:
        raise SystemExit("release metadata check: version changes require CHANGELOG.md in this PR")
    if version_changed:
        changelog = _git_output(
            ["show", f"{args.head}:CHANGELOG.md"],
            failure=f"cannot read CHANGELOG.md at {args.head}",
        )
        if not changelog_has_version(changelog, head_version):
            raise SystemExit(
                f"release metadata check: CHANGELOG.md has no [{head_version}] release heading"
            )

    change_summary = f"{base_version} -> {head_version}" if version_changed else "no version change"
    print(
        f"release metadata check: OK ({head_version}; {change_summary}; "
        f"{len(changed)} changed files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
