"""CLI for TASK-012 EDITOR_WORK / Cubase-return native acceptance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .errors import ProductError
from .task012_native_handoff_gate import Task012NativeHandoffGate, Task012NativeHandoffRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a TASK-012 EDITOR_WORK package and optional real Cubase return.")
    parser.add_argument("editor_work_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--require-cubase-return",
        action="store_true",
        help="Require the accepted 48 kHz Cubase return; use this for final native close.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = Task012NativeHandoffGate(
            Task012NativeHandoffRequest(args.editor_work_root, require_cubase_return=args.require_cubase_return)
        ).run(output_path=args.output)
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "message": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "code": "ERR_TASK012_NATIVE_CLI", "message": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps({
        "status": report["status"],
        "task_owner": report["task_owner"],
        "gate": report["gate"],
        "cubase_status": report["cubase_roundtrip"]["status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
