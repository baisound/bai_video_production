"""Contained Windows entry point for the TASK-046 beginner client."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ai_video_production.voice_model_builder_beginner_client import (
    assert_no_forbidden_effect_surface,
    build_demo_snapshot,
    launch_demo,
    validate_snapshot,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BAI Voice Model Builder")
    parser.add_argument("--locale", choices=("ja", "en"), default="ja")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="validate the contained synthetic preview and exit without opening a window",
    )
    args = parser.parse_args(argv)
    assert_no_forbidden_effect_surface()
    snapshot = build_demo_snapshot(locale=args.locale).to_dict()
    validate_snapshot(snapshot)
    if args.self_check:
        return 0
    launch_demo(locale=args.locale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
