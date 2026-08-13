# R2 Locked Asset Trace Contract — TASK-027 / 037 / 038

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`

A read-only trace service now proves the R2 production-control chain:

`Plan(Blueprint) -> Scene -> Asset Slot -> Candidate -> Audit -> Human ACCEPT -> Locked Asset`

The service fails closed if any graph link, exact Asset audit, Human ACCEPT or lock state is missing/inconsistent. It does not infer a missing plan, repair state, delete rejected Assets, or start regeneration.

This is the minimum auditable trace needed before later UI/Generation Queue layers may present a Candidate as the locked production input.
