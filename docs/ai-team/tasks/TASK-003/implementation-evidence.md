# TASK-003 — Implementation Evidence

Package `0.3.0` implements secure source ingestion, Asset Registry v2, rights metadata, ffprobe structural inspection, checksum/deduplication, Logical URI resolution, atomic promotion, versioned source manifests, append-only Evidence and recovery/idempotency.

## Major implementation files

- `src/ai_video_production/ingest.py`
- `src/ai_video_production/ingest_cli.py`
- `src/ai_video_production/media_probe.py`
- `src/ai_video_production/assets.py`
- `src/ai_video_production/paths.py`
- `src/ai_video_production/store.py`
- `src/ai_video_production/manifest.py`
- `schemas/asset-record.schema.json`
- `schemas/source-manifest-payload.schema.json`
- packaged schema resources
- `tests/test_task003_asset_ingest.py`

## Installed-package golden fixture

The built `0.3.0` wheel was installed outside the repository. A generated 1-second WAV was ingested through `python -m ai_video_production.ingest_cli`, producing a `COMPLETED` operation, `asset://` canonical URI, versioned `source-manifest`, ffprobe metadata and packaged JSON Schemas without emitting the raw source path in successful output.
