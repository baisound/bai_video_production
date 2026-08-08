# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `FOUNDATION_READY`
- Last Completed Task: `TASK-002 — Resolve Capability Spike`
- Active Consumer Task: `NONE`
- TASK-002 Profile: `DEV-4 FOUNDATION CRITICAL` / score `22`
- TASK-002 Status: `COMPLETED`
- TASK-002 Package: `0.2.4`
- Next Consumer Task: `NONE AUTHORIZED`
- Recommended next route: `TASK-003 — Asset Registry / Ingest / Path Resolver`

## TASK-002 final live evidence

Target Resolve sandbox Evidence is accepted:

- Windows 11 / Python 3.12.4
- DaVinci Resolve Studio `21.0.2.4`
- scripting bridge: `WINDOWS_PROGRAMDATA`
- sandbox mutation Project: `BAI_CAPABILITY_PROBE_MANUAL`
- mutation authorized/executed: true / true
- final capability matrix: `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`

Measured WSL2 -> Windows IPC:

- transport: authenticated HTTP/JSON
- Windows host resolution: `DEFAULT_GATEWAY`
- unauthenticated rejection: PASS
- authenticated roundtrip: PASS
- same-endpoint restart/reconnect: PASS
- 16 round trips
- p50 `1.255 ms`
- p95 `1.699 ms`
- bearer token persisted to Evidence: false

Final IPC ADR selects authenticated HTTP/JSON as the WSL2 -> Windows primary transport. Windows Named Pipe remains a Windows-local optimization candidate.

## Final corrective change

Package 0.2.4 retains generated probe WAV/DRP files under the Evidence directory instead of deleting them with a temporary directory. It also restricts Sandbox Project names to a path-safe grammar. This addresses the Owner-observed post-process offline/red Timeline media without changing the measured Resolve capability result or weakening mutation safeguards.

Per Owner direction, another live run solely to verify the visual post-run online state is not required for TASK-002 completion.

## Project roadmap

Project-level roadmap canonical: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` (Ver.1.2 editing-first).

TASK-002 is complete. The roadmap now recommends the minimum dependency foundation `TASK-003 -> TASK-004 -> TASK-022`, then moves SRT/subtitle, filler/silence cut and SE/BGM/narration generation/placement forward as early as dependencies safely permit. Later TASKs remain `NOT_STARTED / NOT_AUTHORIZED`.

## Safety boundaries

- default Resolve probe remains read-only;
- mutation remains explicit and fail-closed;
- a non-sandbox or unverifiable Project is never mutated;
- sandbox name grammar blocks project-name-derived path traversal;
- sandbox probe does not delete Projects, start/cancel render, relink media or terminate Resolve;
- bearer tokens are ephemeral and not written to Evidence;
- BAI Development OS Core and OS-internal TASK-016 remain untouched;
- DistributedOS remains disabled.

## Current verification

- `pytest`: `81 / 81 PASS`
- `compileall`: PASS
- package `0.2.4` wheel build: PASS
- wheel SHA-256: `4309d3ddb3d83608decc8ad55e7a11385517a23264050e34afec3fde2cc8273b`
- installed-package schema verification: PASS
- installed-package sandbox path guard: PASS
- final Critic: `PASS / 0 BLOCKING FINDINGS`
- final Judge: `APPROVED / COMPLETED`
