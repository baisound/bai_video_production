from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dbd_kamigame_collector import KamigameDbDKnowledgeCollector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Kamigame DbD pages into reviewable knowledge candidate files")
    parser.add_argument("--output", required=True, help="Output bundle directory")
    parser.add_argument("--no-killer-details", action="store_true", help="Do not follow killer detail pages")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-killer-details", type=int, default=128)
    args = parser.parse_args(argv)
    manifest = KamigameDbDKnowledgeCollector(Path(args.output)).collect(
        follow_killer_details=not args.no_killer_details,
        max_pages=args.max_pages,
        max_killer_details=args.max_killer_details,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
