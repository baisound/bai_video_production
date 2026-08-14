# TASK-044 — Interactive Timeline / Unified NLE / Export Queue

## Identity

- Priority: `OWNER_MAXIMUM / AFTER_TASK_043_AND_P_V6_4`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Status: `ACTIVE / P-NLE-2_HOSTED_CLOSED / P-NLE-3_IMPLEMENTATION_LOCAL_PASS_HOSTED_PENDING`
- Depends on: TASK-043 and TASK-042 P-V6-4 — both `HOSTED_CLOSED`

## Goal

Promote the released minimum editing Shell into a practical Product-owned NLE:
dynamic tracks, real clip selection/seek, viewport/zoom/scroll, trim/snap/IN-OUT,
keyboard-accessible commands, durable background jobs and a restart-safe Export
Queue. Reuse TASK-010/011/012 for external Resolve/render/handoff ownership.

## Boundaries

- Cut Candidate click-to-review remains distinct from generic clip seek.
- UI commands dispatch through the Shell/Application Service; JavaScript is not
  a second Product state store.
- Export preparation is local and deterministic. External Resolve mutation keeps
  its existing confirmation, operation identity and recovery gates.
- No Provider, paid, credential or Production Deploy authority is added.

## Exit gate

Focused interaction/state tests, long-project performance fixtures, Export Queue
restart/idempotency tests, full regression and native Windows interaction
acceptance pass. Release remains a TASK-045 decision.

