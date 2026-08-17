"""Create an exact, path-free third-party notice from the build environment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import sys


_DISTRIBUTIONS = (
    "pyinstaller",
    "jsonschema",
    "attrs",
    "jsonschema-specifications",
    "referencing",
    "rpds-py",
)
_LICENSE_MARKERS = ("license", "copying", "notice", "copyright")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_license(path: pathlib.Path, logical_name: str) -> tuple[str, dict[str, object]]:
    if not path.is_file():
        raise RuntimeError(f"license source is missing: {logical_name}")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"license source is not UTF-8: {logical_name}") from exc
    return text.replace("\r\n", "\n").rstrip(), {
        "logical_name": logical_name,
        "bytes": len(data),
        "sha256": _sha256(data),
    }


def _distribution_license(name: str) -> tuple[str, dict[str, object]]:
    distribution = importlib.metadata.distribution(name)
    candidates = [
        item
        for item in distribution.files or ()
        if any(marker in str(item).lower() for marker in _LICENSE_MARKERS)
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"{name} must expose exactly one license file; observed {len(candidates)}")
    logical_name = f"{name}-{distribution.version}/{candidates[0].name}"
    text, receipt = _read_license(pathlib.Path(distribution.locate_file(candidates[0])), logical_name)
    receipt.update(
        {
            "component": name,
            "version": distribution.version,
            "license": distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "UNKNOWN",
        }
    )
    return text, receipt


def collect_notice(output: pathlib.Path) -> dict[str, object]:
    if not output.is_absolute():
        raise RuntimeError("output must be an absolute path")
    if output.exists():
        raise RuntimeError("output must not already exist")
    python_text, python_receipt = _read_license(
        pathlib.Path(sys.base_prefix) / "LICENSE.txt",
        f"CPython-{platform.python_version()}/LICENSE.txt",
    )
    python_receipt.update(
        {"component": "CPython", "version": platform.python_version(), "license": "PSF-2.0"}
    )
    tk_text, tk_receipt = _read_license(
        pathlib.Path(sys.base_prefix) / "tcl" / "tk8.6" / "license.terms",
        "Tcl-Tk-8.6/license.terms",
    )
    tk_receipt.update({"component": "Tcl/Tk", "version": "8.6", "license": "TCL"})

    entries: list[tuple[str, dict[str, object], str]] = [
        ("CPython", python_receipt, python_text),
        ("Tcl/Tk", tk_receipt, tk_text),
    ]
    for name in _DISTRIBUTIONS:
        license_text, receipt = _distribution_license(name)
        entries.append((name, receipt, license_text))

    parts = [
        "BAI Voice Model Builder — Third-Party Notices",
        "",
        "This file is generated from the exact contained Windows build environment.",
        "Absolute build paths and credentials are deliberately excluded.",
    ]
    for title, receipt, license_text in entries:
        parts.extend(
            [
                "",
                "=" * 78,
                f"{title} {receipt['version']} — {receipt['license']}",
                f"Source license SHA-256: {receipt['sha256']}",
                "=" * 78,
                license_text,
            ]
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output_bytes = ("\n".join(parts).rstrip() + "\n").encode("utf-8")
    output.write_bytes(output_bytes)
    return {
        "schema_version": 1,
        "components": [receipt for _, receipt, _ in entries],
        "notice_bytes": len(output_bytes),
        "notice_sha256": _sha256(output_bytes),
        "private_path_exposed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(collect_notice(args.output), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
