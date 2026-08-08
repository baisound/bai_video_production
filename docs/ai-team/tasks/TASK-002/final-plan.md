# TASK-002 — Final Implementation Plan

## Authorized implementation order

1. Add canonical capability/report models and JSON Schema.
2. Add Resolve scripting discovery/connection boundary.
3. Add read-only readiness and capability probing with fail-closed classification.
4. Add explicit sandbox mutation authorization guard; do not execute live mutations in the build container.
5. Add IPC comparison probe and provisional/final ADR gating.
6. Add Windows execution wrapper with timeout and evidence output.
7. Add DEV-4 unit/negative/integration/contract/fault tests and run full TASK-001 regression.
8. Run Critic review, fix blocking findings and repeat targeted tests.
9. Update Project/current-state/task-index/README and capture implementation evidence.
10. Commit implementation as `TASK-002` work. Keep Task open if live Windows/Resolve evidence is absent.

## Prohibited actions

- Do not edit BAI Development OS Core.
- Do not start OS-internal TASK-016.
- Do not mark mutation capability `SUPPORTED` from method presence alone.
- Do not automatically delete Projects, kill Resolve, or write to non-sandbox/human timelines.
- Do not claim final IPC selection without target topology evidence.
