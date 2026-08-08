# TASK-003 — Asset Registry / Ingest / Path Resolver

- Status: `COMPLETED`
- Authorization: `OWNER_AUTHORIZED_IMPLEMENTATION`
- Historical alias: `VIDEO-TASK-003`
- Package target: `0.3.0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Adaptive score: `33`

## Objective

Implement the canonical source-asset ingestion boundary required by later normalization, ASR, cut planning, subtitle placement, SE/BGM/narration assets and Resolve assembly. Ingest must preserve source bytes, register auditable rights/checksum metadata, remove machine-specific source paths from canonical records, and atomically promote accepted bytes into logical project storage.

## In scope

- raw-source allowlist and symlink/canonical-path protection;
- `asset://` / `job://` Logical URI resolution and Job scope enforcement;
- fixed-argv `ffprobe` structural inspection for media inputs;
- streaming SHA-256 checksum during staged copy;
- Job-local checksum deduplication and rights-conflict review gate;
- extended Asset Registry rights/reuse metadata;
- SQLite schema v2 additive migration and asset version history;
- target-local staging and atomic source-asset promotion;
- immutable/read-only canonical source bytes;
- canonical versioned `source-manifest` plus derived latest pointer;
- concurrency-safe manifest revision reservation;
- append-only ingest Evidence and idempotent/partial recovery;
- local reference CLI `ai-video-ingest`;
- JSON Schema contracts and package resources.

## Out of scope

- VFR/CFR conversion, proxy creation, 48 kHz WAV extraction and normalization (`TASK-004`);
- exact frame/time mapping (`TASK-022`);
- ASR/SRT, filler cuts, edit intelligence and Resolve editing;
- production storage GC, archive/legal hold (`TASK-017`);
- resource/disk admission policy beyond safe file handling (`TASK-020`);
- downstream publication/usage enforcement beyond recording rights facts and review status.

## Acceptance criteria

1. Source file outside an explicit allowlist, symlink source or cross-Job Logical URI is rejected before Product Job state changes.
2. Accepted source is copied, not moved or destructively modified.
3. Structural media probe and checksum occur against the exact staged bytes.
4. Canonical source target is deterministic, checksum-bound, read-only and atomically promoted.
5. Duplicate bytes are deduplicated; materially different rights/classification metadata causes human review rather than silent merge.
6. Asset Registry persists required rights/reuse metadata and version history.
7. Versioned source manifests are schema-valid, immutable and monotonically revisioned under concurrent ingest.
8. Idempotent replay and crash/partial recovery do not require the original source once canonical bytes are safely registered.
9. Historical/canonical Evidence never stores the raw machine source path.
10. Full regression, boundary-negative, integration, contract, concurrency and fault-recovery tests pass; internal canonical documentation is synchronized and Git-ready.
