from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audacity_openvino import AudacityOpenVinoService
from .paths import LogicalPathResolver, PathMapping
from .store import SQLiteProductStore
from .errors import ProductError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TASK-004 Audacity OpenVINO capability probe")
    p.add_argument("--db", required=True)
    p.add_argument("--asset-root", required=True)
    p.add_argument("--job-root", required=True)
    p.add_argument("--work-root", required=True)
    args = p.parse_args(argv)
    try:
        service = AudacityOpenVinoService(
            store=SQLiteProductStore(args.db),
            resolver=LogicalPathResolver([
                PathMapping("asset://", Path(args.asset_root).resolve()),
                PathMapping("job://", Path(args.job_root).resolve()),
            ]),
        )
        report = service.capability_report(work_root=Path(args.work_root).resolve())
        print(json.dumps({"ok": True, **report}, ensure_ascii=False, sort_keys=True))
        return 0
    except ProductError as exc:
        print(json.dumps({"ok": False, "error": exc.to_envelope()["error"]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
