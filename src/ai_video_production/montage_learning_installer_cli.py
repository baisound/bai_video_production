"""Private command boundary used by the Windows installer and acceptance tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .montage_learning_installation import (
    discover_installed_bridge,
    provision_installed_bridge,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("operation", choices=("provision", "discover"))
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--installer-manifest-sha256")
    parser.add_argument("--receipt-output")
    args = parser.parse_args(None if argv is None else list(argv))

    if args.operation == "provision":
        if not args.installer_manifest_sha256:
            parser.error("provision requires --installer-manifest-sha256")
        discovery = provision_installed_bridge(
            args.install_root,
            installer_manifest_sha256=args.installer_manifest_sha256,
        )
    else:
        if args.installer_manifest_sha256:
            parser.error("discover does not accept --installer-manifest-sha256")
        discovery = discover_installed_bridge(args.install_root)

    if args.receipt_output:
        output = Path(args.receipt_output)
        if not output.is_absolute() or output.is_symlink():
            parser.error("receipt output must be an absolute non-symlink path")
        output.write_text(
            json.dumps(
                discovery.public_receipt(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


__all__ = ["main"]
