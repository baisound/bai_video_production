"""Private command boundary used by the Windows installer and acceptance tests."""

from __future__ import annotations

import argparse
from typing import Sequence

from .montage_learning_installation import (
    discover_installed_bridge,
    provision_and_write_installer_readback,
    provision_installed_bridge,
    write_installer_readback,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "operation", choices=("provision", "discover", "provision-readback")
    )
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--installer-manifest-sha256")
    args = parser.parse_args(None if argv is None else list(argv))

    if args.operation in {"provision", "provision-readback"}:
        if not args.installer_manifest_sha256:
            parser.error(
                f"{args.operation} requires --installer-manifest-sha256"
            )
        if args.operation == "provision-readback":
            provision_and_write_installer_readback(
                args.install_root,
                installer_manifest_sha256=args.installer_manifest_sha256,
            )
        else:
            provision_installed_bridge(
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
