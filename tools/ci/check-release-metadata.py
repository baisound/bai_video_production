"""Fail a pull request when product changes omit release metadata."""

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
    output = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...{head}"], cwd=ROOT, text=True
    )
    return {line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()}


def is_product_change(path: str) -> bool:
    return path == "pyproject.toml" or path.startswith(("src/", "schemas/", "tools/windows/"))


def versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for name, pattern in VERSION_FILES.items():
        match = re.search(pattern, (ROOT / name).read_text(encoding="utf-8"), re.MULTILINE)
        if not match:
            raise SystemExit(f"release metadata check: version not found in {name}")
        found[name] = match.group(1)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--actor", default="")
    args = parser.parse_args(argv)
    changed = changed_files(args.base, args.head)
    product_changed = any(is_product_change(path) for path in changed)
    dependabot = args.actor == "dependabot[bot]"
    if product_changed and not dependabot and "CHANGELOG.md" not in changed:
        raise SystemExit("release metadata check: product changes require CHANGELOG.md in this PR")
    version_values = versions()
    unique = set(version_values.values())
    if len(unique) != 1:
        details = ", ".join(f"{name}={value}" for name, value in version_values.items())
        raise SystemExit(f"release metadata check: version mismatch: {details}")
    version = unique.pop()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if product_changed and not dependabot and f"## [{version}]" not in changelog:
        raise SystemExit(f"release metadata check: CHANGELOG.md has no [{version}] heading")
    print(f"release metadata check: OK ({version}; {len(changed)} changed files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
