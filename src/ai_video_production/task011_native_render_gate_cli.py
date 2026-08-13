"""CLI wrapper for TASK-011 native Resolve render/QA validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .errors import ProductError
from .render_qa import LoudnessProfile
from .task011_native_render_gate import Task011NativeRenderGateRunner, Task011NativeRenderRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render one TASK-010 Automation Timeline in an explicit Resolve sandbox and run TASK-011 QA."
    )
    parser.add_argument("--sandbox-project", required=True)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assembly-plan", type=Path)
    parser.add_argument("--timeline-name")
    parser.add_argument("--expected-duration-frames", type=int)
    parser.add_argument("--duration-tolerance-frames", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--render-format")
    parser.add_argument("--render-codec")
    parser.add_argument("--target-lufs", type=float, default=-16.0)
    parser.add_argument("--tolerance-lu", type=float, default=2.0)
    parser.add_argument("--max-true-peak-dbtp", type=float, default=-1.0)
    parser.add_argument("--max-lra-lu", type=float)
    parser.add_argument(
        "--authorize-resolve-render",
        action="store_true",
        help="Explicitly authorize the real Resolve Render Queue mutation for this invocation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = LoudnessProfile(
        target_lufs=args.target_lufs,
        tolerance_lu=args.tolerance_lu,
        max_true_peak_dbtp=args.max_true_peak_dbtp,
        max_lra_lu=args.max_lra_lu,
    )
    try:
        if args.assembly_plan is not None:
            if args.timeline_name is not None or args.expected_duration_frames is not None:
                raise ValueError("--assembly-plan cannot be combined with --timeline-name/--expected-duration-frames")
            request = Task011NativeRenderRequest.from_assembly_plan(
                args.assembly_plan,
                sandbox_project=args.sandbox_project,
                evidence_root=args.evidence_root,
                duration_tolerance_frames=args.duration_tolerance_frames,
                timeout_seconds=args.timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
                render_format=args.render_format,
                render_codec=args.render_codec,
                loudness_profile=profile,
            )
        else:
            if args.timeline_name is None or args.expected_duration_frames is None:
                raise ValueError("provide --assembly-plan or both --timeline-name and --expected-duration-frames")
            request = Task011NativeRenderRequest(
                sandbox_project=args.sandbox_project,
                timeline_name=args.timeline_name,
                expected_duration_frames=args.expected_duration_frames,
                evidence_root=args.evidence_root,
                duration_tolerance_frames=args.duration_tolerance_frames,
                timeout_seconds=args.timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
                render_format=args.render_format,
                render_codec=args.render_codec,
                loudness_profile=profile,
            )
        report = Task011NativeRenderGateRunner(request).run(
            explicit_external_write_authorization=args.authorize_resolve_render,
            output_path=args.output,
        )
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "message": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "code": "ERR_TASK011_NATIVE_CLI", "message": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps({
        "status": report["status"],
        "task_owner": report["task_owner"],
        "gate": report["gate"],
        "qa_status": report["qa_report"]["status"],
    }, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
