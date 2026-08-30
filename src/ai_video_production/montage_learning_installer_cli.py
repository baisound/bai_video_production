"""Private command boundary used by the Windows installer and acceptance tests."""

from __future__ import annotations

import argparse
from typing import Sequence

from .montage_learning_installation import (
    discover_installed_bridge,
    provision_installed_bridge,
    write_installer_readback,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("operation", choices=("provision", "discover"))
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--installer-manifest-sha256")
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
        write_installer_readback(discovery)
    return 0


__all__ = ["main"]
