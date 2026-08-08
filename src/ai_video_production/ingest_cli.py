from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .assets import AssetType, AudioRightsStatus, PermissionState, RetentionClass, RightsStatus
from .errors import ProductError
from .ingest import AssetIngestRequest, AssetIngestService
from .paths import LogicalPathResolver, PathMapping, SourcePathPolicy
from .store import SQLiteProductStore


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Secure local Asset Registry ingest reference CLI")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--source-root", type=Path, action="append", required=True)
    p.add_argument("--asset-root", type=Path, required=True)
    p.add_argument("--job-root", type=Path, required=True)
    p.add_argument("--asset-type", choices=[x.value for x in AssetType], required=True)
    p.add_argument("--rights-status", choices=[x.value for x in RightsStatus], required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--idempotency-key", required=True)
    p.add_argument("--retention-class", choices=[x.value for x in RetentionClass], default=RetentionClass.STANDARD.value)
    p.add_argument("--commercial-use", choices=[x.value for x in PermissionState], default=PermissionState.UNKNOWN.value)
    p.add_argument("--derivative-allowed", choices=[x.value for x in PermissionState], default=PermissionState.UNKNOWN.value)
    p.add_argument("--reuse-allowed", choices=[x.value for x in PermissionState], default=PermissionState.ALLOWED.value)
    p.add_argument("--audio-rights-status", choices=[x.value for x in AudioRightsStatus], default=AudioRightsStatus.NOT_APPLICABLE.value)
    p.add_argument("--human-lock", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        store = SQLiteProductStore(args.db)
        resolver = LogicalPathResolver([
            PathMapping("asset://", args.asset_root.resolve()),
            PathMapping("job://", args.job_root.resolve()),
        ])
        service = AssetIngestService(
            store=store,
            resolver=resolver,
            source_policy=SourcePathPolicy(tuple(path.resolve() for path in args.source_root)),
        )
        result = service.ingest(AssetIngestRequest(
            production_job_id=args.job_id,
            source_path=args.source,
            asset_type=AssetType(args.asset_type),
            rights_status=RightsStatus(args.rights_status),
            owner=args.owner,
            idempotency_key=args.idempotency_key,
            retention_class=RetentionClass(args.retention_class),
            human_lock=args.human_lock,
            commercial_use=PermissionState(args.commercial_use),
            derivative_allowed=PermissionState(args.derivative_allowed),
            reuse_allowed=PermissionState(args.reuse_allowed),
            audio_rights_status=AudioRightsStatus(args.audio_rights_status),
        ))
    except ProductError as exc:
        sys.stderr.write(json.dumps(exc.to_envelope(), ensure_ascii=False, sort_keys=True) + "\n")
        return 2
    except (ValueError, OSError) as exc:
        sys.stderr.write(json.dumps({"error": {"code": "ERR_INPUT_INGEST_CLI", "message": str(exc)}}, ensure_ascii=False) + "\n")
        return 2
    sys.stdout.write(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
