from __future__ import annotations

import argparse
import json
from pathlib import Path

from .normalization import MediaNormalizationService, NormalizationProfile, NormalizationRequest
from .paths import LogicalPathResolver, PathMapping
from .store import SQLiteProductStore
from .timebase import FrameRate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TASK-004 media normalization reference CLI")
    p.add_argument("--db", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--source-asset-id", required=True)
    p.add_argument("--asset-root", required=True)
    p.add_argument("--job-root", required=True)
    p.add_argument("--idempotency-key", required=True)
    p.add_argument("--target-fps", default="30000/1001")
    p.add_argument("--force-proxy", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    resolver = LogicalPathResolver([
        PathMapping("asset://", Path(args.asset_root).resolve()),
        PathMapping("job://", Path(args.job_root).resolve()),
    ])
    result = MediaNormalizationService(store=SQLiteProductStore(args.db), resolver=resolver).normalize(
        NormalizationRequest(
            args.job_id,
            args.source_asset_id,
            args.idempotency_key,
            NormalizationProfile(target_frame_rate=FrameRate.parse(args.target_fps), force_cfr_proxy=args.force_proxy),
        )
    )
    print(json.dumps({
        "operation_id": result.operation.operation_id,
        "status": result.operation.status,
        "timing": result.timing.to_dict(),
        "video_reference_asset_id": result.video_reference_asset.asset_id if result.video_reference_asset else None,
        "proxy_asset_id": result.proxy_asset.asset_id if result.proxy_asset else None,
        "analysis_audio_asset_id": result.analysis_audio_asset.asset_id if result.analysis_audio_asset else None,
        "manifest_uri": result.manifest_uri,
        "evidence_uri": result.evidence_uri,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
