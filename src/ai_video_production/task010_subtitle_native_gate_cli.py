from __future__ import annotations

import argparse
import json
from pathlib import Path

from .errors import ProductError
from .task010_subtitle_native_gate import Task010SubtitleNativeGateRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TASK-010 edit-aware subtitle semantic native validation.")
    parser.add_argument("--sandbox-project", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--output", default="task010-subtitle-native-gate.json")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)
    try:
        report = Task010SubtitleNativeGateRunner(
            sandbox_project=args.sandbox_project,
            evidence_root=Path(args.evidence_root),
            ffmpeg_executable=args.ffmpeg,
        ).run(output_path=args.output)
    except (ProductError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ProductError) else "ERR_TASK010_SUBTITLE_NATIVE_CLI"
        print(json.dumps({"status": "ERROR", "code": code, "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": report["status"],
        "gate": report["gate"],
        "decision": report["decision"],
        "project_timeline_rate": report["project_timeline_rate"],
        "timing_verified": report["observation"]["timing_verified"],
        "text_verified": report["observation"]["text_verified"],
    }, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
