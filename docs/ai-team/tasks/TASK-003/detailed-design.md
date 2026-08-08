# TASK-003 — Detailed Design

## 1. Canonical flow

`raw allowlisted source -> target-local staging -> ffprobe structure check -> SHA-256 -> rights/dedupe decision -> atomic promotion -> Asset Registry/version -> source-manifest -> Evidence`

TASK-003 stops before proxy/timebase/audio normalization, which remains TASK-004.

## 2. Source path boundary

Raw OS paths are accepted only at the ingestion edge through `SourcePathPolicy`. Allowed roots must already exist and be absolute directories. Source authorization canonicalizes the requested file, rejects symlinks and refuses any resolved file outside the allowlist. Authorization happens before the `CREATED -> INGESTING` Product Job transition so a denied source has zero Job-state side effect.

Raw machine source paths are not persisted into Asset, Manifest, successful CLI output or Evidence. Canonical records use `asset://` and `job://` Logical URIs.

## 3. Staging and checksum

The source is opened read-only with `O_NOFOLLOW` where supported. Bytes are copied in bounded chunks to a target-root-local staging file, SHA-256 is calculated during that copy, staging is fsynced and source `fstat` values are compared before/after to detect mutation during ingest. Empty sources are rejected.

Using target-local staging allows `os.replace` to provide the intended atomic promotion boundary on the same filesystem.

## 4. Media probe

`FFprobeMediaProbe` invokes `ffprobe` with a fixed argv list and `shell=False`. Only sanitized structural metadata is persisted: duration, size, format, codec type/name, frame-rate/time-base and relevant audio/video dimensions. Stderr and raw source paths are not canonicalized. Asset type must be compatible with discovered streams.

## 5. Asset identity and rights

The canonical target is deterministic from Job ID + SHA-256 + safe suffix. Job-local duplicate bytes share an Asset. Duplicate bytes with conflicting type/rights/reuse classification are not silently merged; the operation returns `HUMAN_REVIEW_REQUIRED`.

Asset metadata includes owner, rights status, commercial/derivative/reuse permission state, audio-rights state, attribution/territory/term, publication restrictions, approved segments, source provenance and safe media metadata. Unknown/review-required rights can be registered but are exposed as not automatically usable.

## 6. SQLite v2 migration

Schema v2 is an additive migration from the TASK-001 database. It extends `assets`, `operations` and `manifests`, creates Job-local checksum uniqueness, preserves existing rows/default semantics and records schema version history. `asset_versions` preserves producer-operation binding, enabling recovery after process death between Registry commit and operation completion.

## 7. Atomic promotion and immutable source asset

A new source is promoted from target-local staging using `os.replace`. A pre-existing deterministic target must have the same checksum. Newly promoted bytes are marked read-only. Failure before Registry commit removes only a target created by the failing operation; the original source is never deleted.

## 8. Concurrency-safe source manifest

Manifest revision allocation is reserved in SQLite using an immediate transaction. The reservation is inserted as `PENDING`, then the Asset snapshot is taken and a versioned canonical manifest is atomically written and schema-validated. The DB record transitions to `COMMITTED` only after the canonical file succeeds.

The convenience `source-manifest.json` pointer is derived and updated only when the writer owns the latest committed revision, so a slower older concurrent writer cannot roll it backwards. `latest_manifest` never exposes `PENDING` reservations.

## 9. Idempotency and recovery

Operations bind command + Job + idempotency key. Reuse of a key for a different command is rejected. A completed replay returns the prior Asset even after the Product Job has advanced beyond INGESTING.

If failure occurs after Asset Registry commit but before manifest/evidence completion, the operation is `PARTIAL` and can repair metadata without the raw source. A hard process failure is also recoverable via `asset_versions.producer_operation_id`. Source-free repair first verifies the canonical target exists and still matches the registered SHA-256; tampered/missing bytes remain `PARTIAL` with an explicit integrity error.

## 10. Evidence

Each successful/repair operation appends `ASSET_INGEST` Evidence containing IDs, Logical URI, checksums, rights review state, safe media metadata and dedupe/repair flags. No raw source OS path is stored.

## 11. Interfaces

- Python: `AssetIngestService.ingest(AssetIngestRequest)`
- Local reference CLI: `ai-video-ingest`
- Canonical schemas: `asset-record.schema.json`, `source-manifest-payload.schema.json`, canonical manifest envelope
- Persistence: `SQLiteProductStore` schema v2

## 12. Safety properties

- fail closed on path uncertainty;
- no shell evaluation of filenames;
- no destructive source mutation;
- no cross-Job Logical URI access;
- no silent rights metadata overwrite;
- no partially committed manifest exposed as latest;
- no recovery metadata commit over missing/tampered canonical bytes.
