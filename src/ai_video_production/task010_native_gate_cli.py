"""CLI wrapper for the internal TASK-010 Resolve native gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .errors import ProductError
from .task010_native_gate import Task010NativeGateRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded TASK-010 native validation in an explicit Resolve sandbox Project."
    )
    parser.add_argument("--sandbox-project", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--output", default="task010-native-gate.json")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument(
        "--allow-replay-only",
        action="store_true",
        help="Allow existing deterministic BAI_AUTO timelines instead of requiring fresh APPLIED mutations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runner = Task010NativeGateRunner(
            sandbox_project=args.sandbox_project,
            evidence_root=Path(args.evidence_root),
            ffmpeg_executable=args.ffmpeg,
            ffprobe_executable=args.ffprobe,
            require_fresh_assembly=not args.allow_replay_only,
        )
        report = runner.run(output_path=args.output)
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "message": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "code": "ERR_TASK010_NATIVE_CLI", "message": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps({
        "status": report["status"],
        "task_owner": report["task_owner"],
        "gate": report["gate"],
        "linked_av_status": report["linked_av_semantic_probe"]["status"],
    }, ensure_ascii=False))
    return 0 if report["status"] in {"PASS", "PASS_WITH_FINDING"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
