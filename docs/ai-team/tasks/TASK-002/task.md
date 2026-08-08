# TASK-002 — Resolve Capability Spike

## Status

`COMPLETED`

## Historical alias

`VIDEO-TASK-002`

## Objective

Convert the product design's Resolve Gateway assumptions into measured capability evidence for the actual target DaVinci Resolve installation, without treating documentation or method presence as proof of safe write behavior.

## Scope

1. Implement a version-aware Resolve scripting loader and read-only readiness/capability probe.
2. Produce a machine-readable Capability Matrix using `SUPPORTED / LIMITED / UNSUPPORTED / PROBE_REQUIRED`.
3. Record exact Resolve version/product, observed return behavior, elapsed time, Studio requirement evidence state and manual fallback.
4. Keep mutation probes disabled by default and permit them only in an explicitly named sandbox project.
5. Implement a local IPC comparison probe and an ADR evidence model for localhost HTTP/JSON, Windows Named Pipe, gRPC and ZeroMQ.
6. Provide a Windows runner that writes evidence without storing secrets or arbitrary user paths.
7. Add Schema, unit, negative, integration, contract and fault/recovery tests.
8. Preserve TASK-001 regression behavior.

## Out of scope

- Production Resolve Gateway API Server/Controller implementation.
- Production Timeline assembly, subtitle placement or rendering.
- Automatic deletion of Resolve Projects or media.
- `taskkill` / forced Resolve termination.
- Writing to an existing non-sandbox Project or human-owned Timeline.
- Final IPC promotion without Windows + WSL2 live evidence.
- BAI Development OS Core changes or OS-internal TASK-016.

## Acceptance criteria

- DEV-4 profile and Owner authorization are recorded.
- Probe report and IPC report validate against project JSON Schemas.
- No mutation occurs in default probe mode.
- Mutation mode fails closed unless a sandbox project name uses the required prefix and explicit mutation permission is supplied.
- Read-only fake-Resolve integration tests prove version/project/media/timeline readiness discovery.
- Negative tests prove missing module, disconnected Resolve and unsafe mutation requests do not become false `SUPPORTED` results.
- IPC probe proves localhost HTTP restart/auth behavior locally and marks target-Windows-only candidates as unresolved when not actually measured there.
- Full regression suite passes.
- **Completion gate:** SATISFIED. Attempt 03 established sandbox behavioral Evidence and WSL2-to-Windows IPC Evidence on the target topology. Final IPC ADR, final DEV-4 Critic/Judge and Completion Record are recorded. The post-run probe-asset retention fix is locally regression-tested; per Owner direction, another live run solely to confirm the visual online state is not required for TASK-002 completion.
