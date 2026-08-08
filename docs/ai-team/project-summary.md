# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product aims to analyze source video/audio/images/subtitles/AI-generated assets, produce auditable edit plans, automate safe deterministic assembly around DaVinci Resolve, and preserve human-controlled finishing surfaces.

## Completed foundation

TASK-001 completed the domain contracts required before operational media/NLE tasks: Product IDs, state/recovery, manifests, schemas, assets/rights, logical paths, atomic persistence primitives, errors/evidence, ownership, profiles/plugins, SQLite persistence and idempotency.

## Active Resolve capability spike

TASK-002 has implemented the capability-measurement harness needed before production Resolve Gateway development. It performs version/product/readiness discovery through a strict safe-read allowlist, emits schema-validated capability evidence, keeps mutation operations unresolved until behavioral evidence exists, and compares IPC candidates without promoting a final transport from non-target observations.

Local implementation verification is complete, including wheel installation outside the checkout. The task remains open because the build container cannot supply target Windows DaVinci Resolve or WSL2-to-Windows topology evidence.

## Current boundary

Production Resolve Gateway Server/Controller, timeline assembly, rendering, deletion, process termination and writes to human-owned timelines remain outside TASK-002. No later Consumer TASK is authorized.
