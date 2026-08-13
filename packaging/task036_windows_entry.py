"""Frozen Windows entry point for the TASK-036 desktop shell."""

from ai_video_production.task036_packaged_entry import packaged_main


if __name__ == "__main__":
    raise SystemExit(packaged_main())
