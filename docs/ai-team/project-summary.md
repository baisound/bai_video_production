# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product analyzes video/audio/images/subtitles/AI-generated assets, produces auditable edit plans, automates safe deterministic assembly around DaVinci Resolve, and preserves human-controlled finishing surfaces.

## Completed foundation

TASK-001 completed Product IDs, state/recovery, manifests, schemas, assets/rights, logical paths, atomic persistence, errors/evidence, ownership, profiles/plugins, SQLite persistence and idempotency.

## Active Resolve capability spike

TASK-002 has now passed the target read-only Resolve connection gate. Attempt 02 connected to `DaVinci Resolve Studio 21.0.2.4` and measured seven safe read capabilities as `SUPPORTED`, while leaving sixteen mutation/behavior-dependent rows `PROBE_REQUIRED` rather than inferring support from method presence.

Windows-local HTTP/JSON and Named Pipe authentication/restart evidence is valid. Package 0.2.2 adds a narrow Resolve sandbox behavioral runner and WSL2-to-Windows IPC topology runner. TASK-002 remains open until those live outputs, Final IPC ADR and DEV-4 final review are complete.

## Project roadmap

The new canonical roadmap defines the Critical Path from foundation to Technical MVP, Production Pilot and Enhanced Product. Existing TASK-001 through TASK-021 identities are preserved. A historical external-SKILL numbering collision is resolved by assigning those additions to TASK-022 through TASK-026 without rewriting historical evidence.

No later Consumer TASK is authorized by the roadmap itself.

## Current local verification

- `pytest`: 74 / 74 PASS
- `compileall`: PASS
- package 0.2.2 wheel + installed-package schema verification: PASS
