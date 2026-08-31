"""CLI for the TASK-036 native desktop layout/runtime spike."""

from __future__ import annotations

import argparse
import json
import os

from .errors import ProductError
from .task036_first_run_bootstrap import ensure_first_run_launch_configuration
from .task036_shell_ui import run_native_layout_spike
from .task036_trusted_launcher import run_trusted_native_shell


class _Task036ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        # Product hosts have no console. Preserve a typed, body-free failure so
        # the packaged boundary can show one actionable native dialog.
        raise ValueError("TASK-036 startup arguments are invalid")


def _parser() -> argparse.ArgumentParser:
    parser = _Task036ArgumentParser(
        description="BAI Video Production TASK-036 native desktop Shell"
    )
    parser.add_argument("--launch-config")
    parser.add_argument("--layout-spike", action="store_true")
    return parser


def run(argv: list[str] | None = None) -> None:
    """Run the Shell while preserving typed startup failures for Product hosts."""

    args = _parser().parse_args(argv)
    configured = args.launch_config or os.environ.get("BAI_TASK036_LAUNCH_CONFIG")
    if configured and args.layout_spike:
        raise ValueError("--launch-config and --layout-spike cannot be combined")
    if args.layout_spike:
        run_native_layout_spike()
    else:
        run_trusted_native_shell(
            configured if configured else ensure_first_run_launch_configuration()
        )


def main(argv: list[str] | None = None) -> int:
    try:
        run(argv)
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", **exc.to_envelope()["error"]}, ensure_ascii=False))
        return 2
    except ValueError as exc:
        print(json.dumps({"status": "ERROR", "code": "ERR_TASK036_SHELL_CLI", "message": str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
