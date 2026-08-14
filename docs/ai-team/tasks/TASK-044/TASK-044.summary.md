# TASK-044 Summary

- Name: Interactive Timeline / Unified NLE / Export Queue
- Priority: `OWNER_MAXIMUM / CURRENT_RUNNABLE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Current Phase: `P-NLE-1 TIMELINE SEMANTIC PROJECTION IMPLEMENTATION LOCAL PASS`
- Current Gate: `IMPLEMENTATION_PASS / HOSTED_PENDING`
- Source baseline: `f8b901c143f6a4987cacb46429cf0caf85aa2ab7`
- Prerequisites: TASK-043 and TASK-042 P-V6-4 `HOSTED_CLOSED`
- Stable release: `v0.20.1`; no development version selected

The design splits implementation into four hosted Atomic Units: P-NLE-1 Timeline
semantic projection/interaction reducer, P-NLE-2 trim/snap/IN-OUT and history,
P-NLE-3 durable Export Queue composition, and P-NLE-4 existing Shell/UI plus
native interaction acceptance. Each unit uses a fresh main checkout and dedicated
branch after the previous hosted closure.

Provider, paid execution, new credentials, Production Deploy and TASK-044 release
operations are not authorized. Native interaction is limited to the P-NLE-4
sandbox acceptance gate. Exact version/Tag/Release remains TASK-045 ownership.

Design PR #68 passed hosted `9 / 9`, merged at exact main
`f8b901c143f6a4987cacb46429cf0caf85aa2ab7` and completed branch/checkout cleanup.
Fresh-main P-NLE-1 implements frame-authoritative tracks/clips, selection/seek
separation, rational viewport transform, bounded 10,000-clip windowing and exact
TASK-036/TASK-042 read adapters. Focused `42 / 42` and full
`1083 passed, 1 skipped` pass locally; hosted closure is pending.

