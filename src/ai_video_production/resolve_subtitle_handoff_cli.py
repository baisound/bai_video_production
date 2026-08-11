"""Build a private canonical subtitle-placement handoff for DaVinci Resolve."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .resolve_subtitle_handoff import ResolveSubtitleHandoffService
from .subtitle_workspace import SubtitleWorkspaceStore
from .timebase import FrameRate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="Subtitle Workspace JSON")
    parser.add_argument(
        "--output",
        type=Path,
        help="Private handoff JSON; defaults beside Workspace under .bai-resolve-handoff/",
    )
    parser.add_argument("--timeline-rate", default="30000/1001")
    parser.add_argument("--timeline-origin-frame", type=int, default=0)
    parser.add_argument("--track-index", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        workspace_path = args.workspace.expanduser().resolve()
        output_path = (
            args.output.expanduser().resolve()
            if args.output
            else workspace_path.parent
            / ".bai-resolve-handoff"
            / "resolve-subtitle-placement.json"
        )
        if output_path == workspace_path:
            raise ValueError("Resolve handoff output must not overwrite the Subtitle Workspace")
        workspace = SubtitleWorkspaceStore.load(workspace_path)
        plan, result = ResolveSubtitleHandoffService.write(
            output_path,
            workspace,
            timeline_rate=FrameRate.parse(args.timeline_rate),
            timeline_origin_frame=args.timeline_origin_frame,
            track_index=args.track_index,
        )
        payload = plan.to_dict()
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": str(result.path.resolve()),
                    "bytes": result.bytes_written,
                    "workspace_id": plan.workspace_id,
                    "workspace_revision": plan.workspace_revision,
                    "placement_count": len(plan.placements),
                    "ready_for_resolve_write": plan.ready_for_resolve_write,
                    "plan_sha256": payload["plan_sha256"],
                    "execution_owner": "TASK-010",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"error": {"code": "ERR_SUBTITLE_HANDOFF_INPUT", "message": str(exc)}},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
