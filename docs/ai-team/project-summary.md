# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product aims to analyze source video/audio/images/subtitles/AI-generated assets, produce auditable edit plans, automate safe deterministic assembly around DaVinci Resolve, and preserve human-controlled finishing surfaces.

## Completed foundation

TASK-001 completed the domain contracts required before operational media/NLE tasks: Product IDs, state/recovery, manifests, schemas, assets/rights, logical paths, atomic persistence primitives, errors/evidence, ownership, profiles/plugins, SQLite persistence and idempotency.

## Active Resolve capability spike

TASK-002 has implemented the capability-measurement harness needed before production Resolve Gateway development. It performs version/product/readiness discovery through a strict safe-read allowlist, emits schema-validated capability evidence, keeps mutation operations unresolved until behavioral evidence exists, and compares IPC candidates without promoting a final transport from non-target observations.

Local implementation verification is complete, including wheel installation outside the checkout. Windows Attempt 01 has now supplied valid Windows-local HTTP/JSON and Named Pipe evidence, but Resolve returned no live root object and WSL2 reachability remains unverified. Attempt 01 also exposed an Evidence-source labeling defect, corrected in package 0.2.1. TASK-002 therefore remains open for Attempt 02 rather than promoting unresolved capabilities.

## Current boundary

Production Resolve Gateway Server/Controller, timeline assembly, rendering, deletion, process termination and writes to human-owned timelines remain outside TASK-002. No later Consumer TASK is authorized.
