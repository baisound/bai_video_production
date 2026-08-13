from __future__ import annotations

import json

from .task036_native_probe import Task036NativeProbe


def main() -> int:
    report = Task036NativeProbe().run().to_dict()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_to_launch_layout_spike"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
