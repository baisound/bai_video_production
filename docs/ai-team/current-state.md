# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `MEDIA_INGEST_READY`
- Last Completed Task: `TASK-003 — Asset Registry / Ingest / Path Resolver`
- Active Consumer Task: `NONE`
- TASK-003 Profile: `DEV-4 FOUNDATION CRITICAL` / score `33`
- TASK-003 Status: `COMPLETED`
- Package: `0.3.0`
- Next Consumer Task: `NONE AUTHORIZED`
- Recommended next route: `TASK-004 — Timebase / Proxy / Normalization`

## TASK-003 completed foundation

- raw source files are accepted only through explicit allowlisted roots and symlinks/path escapes are rejected before Product Job state mutation;
- source bytes are copied, never moved or destructively modified;
- exact staged bytes are structurally inspected with fixed-argv `ffprobe` and SHA-256 is calculated during copy;
- canonical targets are deterministic `asset://` URIs, promoted atomically and made read-only;
- Job-local checksum dedupe is supported while rights/classification conflicts require human review;
- Asset Registry stores owner, rights, commercial/derivative/reuse permissions, audio-rights state and safe media metadata;
- SQLite schema v2 is additive and preserves producer-operation history;
- versioned `source-manifest` revisions are reserved transactionally and cannot collide/roll back under concurrent ingest;
- append-only Evidence omits raw machine source paths;
- idempotent replay, PARTIAL repair and hard-crash recovery are implemented and refuse missing/tampered canonical assets.

## Current verification

- `pytest`: `110 / 110 PASS`
- `compileall`: PASS
- package `0.3.0` wheel build: PASS
- installed-wheel real ffprobe/CLI golden ingest: PASS
- packaged schema resources: PASS
- final Critic: `PASS / 0 BLOCKING FINDINGS`
- final Judge: `APPROVED / COMPLETED`

## Roadmap

Canonical roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.3. The Owner-directed editing-first policy remains in force. TASK-004 is the next minimum dependency because reliable SRT/cut/placement requires a normalized timebase contract; TASK-022 then establishes exact timeline mapping. Later TASKs remain `NOT_STARTED / NOT_AUTHORIZED`.

## Safety boundaries

- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.
- normalization/proxy/audio extraction are not silently absorbed into TASK-003; they remain TASK-004.
- downstream publishing/usage rights enforcement remains with later owning workflows; TASK-003 records the canonical rights facts and review gate.
