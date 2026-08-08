# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product analyzes source media, creates auditable edit intelligence and safely assembles human-finishable timelines around DaVinci Resolve.

## Completed foundation

**TASK-001** completed IDs, Product Job state/recovery, manifests, schemas, base Asset/rights, Logical URI, atomic persistence, Evidence/Checkpoint, ownership, profiles/plugins, SQLite and idempotency.

**TASK-002** completed DaVinci Resolve Studio 21.0.2.4 capability verification and the WSL2→Windows authenticated HTTP/JSON IPC architecture.

**TASK-003** completed secure source Asset ingestion. Raw source paths are boundary-only; accepted bytes are staged, structurally probed, checksummed, rights-classified and atomically promoted to immutable `asset://` storage. SQLite schema v2 records extended Asset metadata and operation/version history. Concurrent source-manifest revisions are transactionally reserved and idempotent/partial/hard-crash recovery is supported without rewriting historical Evidence.

## Editing-first roadmap

The Owner prioritizes editing value. The minimum dependency route is now `TASK-004 -> TASK-022`, after which SRT/subtitle creation and Resolve placement, filler/silence/disfluency cuts, and SE/BGM/narration generation/placement are moved forward as dependencies safely permit. TASK numbers remain stable; execution order may change.

## Current verification

- TASK-001: COMPLETED
- TASK-002: COMPLETED
- TASK-003: COMPLETED / DEV-4 score 33
- package: `0.3.0`
- `pytest`: `110 / 110 PASS`
- compileall: PASS
- wheel/installed-package real ingest verification: PASS
- active Consumer TASK: none
- recommended next: TASK-004, not authorized
