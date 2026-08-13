"""CLI for the TASK-036 native desktop layout/runtime spike."""

from __future__ import annotations

import json

from .errors import ProductError
from .task036_shell_ui import run_native_layout_spike


def main() -> int:
    try:
        run_native_layout_spike()
    except ProductError as exc:
        print(json.dumps({"status": "ERROR", **exc.to_envelope()["error"]}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
