# P-UX-1C Final Review aggregate projection

Date: 2026-08-16
Atomic unit: `FINAL_REVIEW_AGGREGATE_R0`

## Design and Critic

The Final Review page currently dumps the Audit snapshot and displays an
unexplained disabled approval. The screen contract requires an aggregate read
projection and forbids synthetic ACCEPT.

Aggregate exact Production required/LOCKED/STALE counts and exact Audit
Candidate/Human-pending/Critical/recovery counts. List unresolved canonical
Slot and Candidate identities. Keep state `UNKNOWN` when either source is
unavailable and `REVIEW_REQUIRED` otherwise; do not emit PASS because no typed
Final Review service exists. Add only navigation back to the owning Asset Review
and WORLD LOCK surfaces.

Builder Critic: all required Slots being LOCKED is insufficient to manufacture
final approval. Correction: the final action remains statically disabled even
when blocker counts are zero. Security Critic: aggregation could conceal an
Audit recovery or STALE state. Correction: both are separately counted/listed
from the exact source snapshots.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- The projection consumes both current Production and Audit snapshots.
- Required/LOCKED/STALE Slot and Candidate/Human-pending/Critical/recovery
  states remain separately visible with exact source checksums.
- Missing source state is `UNKNOWN`; an available aggregate is always
  `REVIEW_REQUIRED`, never synthetic PASS.
- The only enabled actions navigate to Asset Review and WORLD LOCK.
- No final-approval bridge method or mutation was added.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `173 passed`.
- Full regression: `1242 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
