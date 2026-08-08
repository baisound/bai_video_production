# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `RESOLVE_SPIKE_AWAITING_LIVE_EVIDENCE`
- Last Completed Task: `TASK-001 — Project Foundation / Domain Model`
- Active Consumer Task: `TASK-002 — Resolve Capability Spike`
- TASK-002 Profile: `DEV-4 FOUNDATION CRITICAL` / score `22`
- TASK-002 Authorization: `AUTHORIZED_FOR_IMPLEMENTATION` by explicit Owner instruction on 2026-08-09
- TASK-002 Stage: `IMPLEMENTED_AWAITING_LIVE_EVIDENCE`
- Next Consumer Task: `NONE AUTHORIZED`

## TASK-002 implementation state

The repository now contains a read-only-by-default Resolve scripting discovery/capability probe, strict capability report schema, local IPC comparison probe, Windows evidence runner, external-side-effect mutation guard and DEV-4 test coverage. Installed-wheel execution and packaged schema-resource loading have been verified outside the source checkout.

The build environment has no target Windows DaVinci Resolve scripting installation. Local evidence therefore records the Resolve capability matrix as unresolved rather than inventing support. Local HTTP/JSON authentication and same-endpoint restart are measured; Windows Named Pipe and WSL2-to-Windows reachability remain live-evidence items.

## Completion gate

TASK-002 is **not COMPLETED**. Completion requires target-machine evidence sufficient to classify the actual Resolve version/product behavior and review the IPC ADR against the Windows + WSL2 topology. Mutation capabilities are not promoted from method presence alone.

## Safety boundaries

- Default probe mode performs no Project/Timeline/media/render mutation.
- Optional mutation authorization is fail-closed and sandbox-prefixed; the current implementation does not auto-run mutation sequences.
- Project deletion, forced Resolve termination and writes to existing non-sandbox/human-owned timelines are prohibited.
- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.

## Evidence

TASK-002 design, implementation review and local evidence are under `docs/ai-team/tasks/TASK-002/`.
