"""Contained Windows entry point for the TASK-046 beginner client."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from ai_video_production.voice_model_builder_beginner_client import (
    MAX_WORKFLOW_JSON_BYTES,
    assert_no_forbidden_effect_surface,
    build_demo_snapshot,
    compile_beginner_snapshot_from_workflow_json,
    launch_demo,
    validate_snapshot,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_workflow_json(path: Path) -> tuple[bytes, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("workflow JSON must be one regular file")
    before = path.stat()
    if not 1 <= before.st_size <= MAX_WORKFLOW_JSON_BYTES:
        raise ValueError("workflow JSON must be between 1 byte and 1 MiB")
    payload = path.read_bytes()
    after = path.stat()
    if (
        len(payload) != before.st_size
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
    ):
        raise ValueError("workflow JSON changed while it was being read")
    return payload, _utc_now()


def _choose_workflow_json() -> tuple[bytes, str] | None:
    from tkinter import filedialog

    selected = filedialog.askopenfilename(
        title="workflow JSONを選ぶ / Choose workflow JSON",
        filetypes=(("JSON", "*.json"), ("All files", "*.*")),
    )
    if not selected:
        return None
    try:
        return _read_workflow_json(Path(selected))
    except (OSError, ValueError) as exc:
        raise ValueError("selected workflow JSON cannot be read safely") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BAI Voice Model Builder")
    parser.add_argument("--locale", choices=("ja", "en"), default="ja")
    parser.add_argument(
        "--workflow-json",
        type=Path,
        help="validate and preview one VerticalSliceWorkflowRevision JSON file",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="validate the contained synthetic preview and exit without opening a window",
    )
    args = parser.parse_args(argv)
    assert_no_forbidden_effect_surface()
    if args.workflow_json is None:
        snapshot = build_demo_snapshot(locale=args.locale).to_dict()
    else:
        payload, created_at = _read_workflow_json(args.workflow_json)
        snapshot = compile_beginner_snapshot_from_workflow_json(
            payload=payload, locale=args.locale, created_at=created_at,
        ).to_dict()
    validate_snapshot(snapshot)
    if args.self_check:
        return 0
    launch_demo(
        locale=args.locale,
        initial_snapshot=snapshot if args.workflow_json is not None else None,
        workflow_loader=_choose_workflow_json,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
