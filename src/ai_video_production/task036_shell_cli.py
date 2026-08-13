"""CLI for the TASK-036 native desktop layout/runtime spike."""

from __future__ import annotations

import argparse
import json
import os

from .errors import ProductError
from .task036_shell_ui import run_native_layout_spike
from .task036_trusted_launcher import run_trusted_native_shell


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BAI Video Production TASK-036 native desktop Shell")
    parser.add_argument("--launch-config")
    parser.add_argument("--layout-spike", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        configured = args.launch_config or os.environ.get("BAI_TASK036_LAUNCH_CONFIG")
        if configured and args.layout_spike:
            raise ValueError("--launch-config and --layout-spike cannot be combined")
        if configured:
            run_trusted_native_shell(configured)
        else:
            run_native_layout_spike()
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", **exc.to_envelope()["error"]}, ensure_ascii=False))
        return 2
    except ValueError as exc:
        print(json.dumps({"status": "ERROR", "code": "ERR_TASK036_SHELL_CLI", "message": str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
