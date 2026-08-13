# TASK-037 — Slot -> Candidate Dependency Contract

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`

Every Candidate append now creates a deterministic internal dependency:

`Scene Asset Slot -> Asset Candidate`

This relationship is not optional bookkeeping. It ensures upstream Slot/Scene/Plan STALE propagation reaches all non-terminal dependent Candidates without requiring callers to remember a separate graph write.

The dependency is preflighted for identity conflict/cycle before Candidate mutation, is persisted by the existing crash-safe TASK-037 snapshot, and never starts regeneration automatically.
