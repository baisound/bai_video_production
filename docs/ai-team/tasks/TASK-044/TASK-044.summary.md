# TASK-044 Summary

- Name: Interactive Timeline / Unified NLE / Export Queue
- Priority: `OWNER_MAXIMUM / CURRENT_RUNNABLE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Current Phase: `CURRENT-MAIN AUDIT / BUILDER DESIGN / CRITIC LOCAL PASS`
- Current Gate: `DESIGN_LOCAL_PASS / HOSTED_PENDING`
- Source baseline: `19f1a94f11a783f475141af015351f64aff1b7d8`
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

