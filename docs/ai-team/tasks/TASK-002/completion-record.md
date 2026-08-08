# TASK-002 Completion Record — Resolve Capability Spike

- Status: `COMPLETED`
- Governance: `DEV-4 FOUNDATION CRITICAL` / score `22`
- Package: `0.2.4`
- Target: `DaVinci Resolve Studio 21.0.2.4`
- Final sandbox matrix: `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`
- WSL2 IPC: authenticated HTTP/JSON PASS; same-endpoint restart PASS; p50 `1.255 ms`, p95 `1.699 ms`
- Final IPC ADR: `ACCEPTED`
- Final regression: `81 passed`
- Critic: `PASS / 0 BLOCKING FINDINGS`
- Judge: `APPROVED / COMPLETED`

## Delivered contracts

- version-aware Resolve scripting discovery and connection diagnostics;
- machine-readable capability matrix with no false unsupported inference;
- fail-closed sandbox mutation guard;
- minimal sandbox behavioral capability probe;
- Windows-local IPC comparison Evidence;
- WSL2 -> Windows authenticated/restart topology Evidence;
- Final IPC ADR for the production Gateway boundary;
- persistent TASK-002 probe assets for stable post-run sandbox inspection;
- schema-valid Evidence and packaging support.

## Residual non-blocking items

- subtitle mutation remains `PROBE_REQUIRED` until the editing-first subtitle/Resolve placement task needs it;
- render setting/submit/start/status/cancel and relink remain `PROBE_REQUIRED` until their owning TASKs;
- no extra live rerun is required solely to confirm that package 0.2.4 retained probe WAV stays online after process exit; Owner explicitly accepted this as non-mandatory.

## Next route

Recommended: `TASK-003 — Asset Registry / Ingest / Path Resolver`, then the minimum `TASK-004` timebase and `TASK-022` mapping foundations needed to bring SRT/subtitle, filler/silence cut and SE/BGM/narration generation/placement forward.

Recommendation is not authorization. TASK-003 remains `NOT_STARTED / NOT_AUTHORIZED` until explicit Owner instruction.
