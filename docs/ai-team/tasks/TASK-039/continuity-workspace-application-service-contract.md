# TASK-039 — Continuity Workspace / Human Soft-Boundary Review Contract

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / AUTOMATED_VALIDATED`
- Runtime owner: TASK-039
- Safety boundary: no provider execution, no automatic regeneration, no override of `DIRECT_CONTINUATION`

## Purpose

Expose the current Continuity Map as a reviewable Product surface while preserving the hard distinction between exact `DIRECT_CONTINUATION` and reviewable `SOFT_CONTINUITY`.

## Projection

`Task039ContinuityWorkspaceProjection` combines TASK-039 continuity state with TASK-037 Production Control state. Every row verifies that the source Candidate still matches the exact Asset ID/SHA recorded by the continuity edge. The projection also shows the current target Slot state and any existing target inspection result.

A Human soft-approval action is available only when all of the following are true:

1. boundary type is `SOFT_CONTINUITY`;
2. a target has already been inspected;
3. validation is `HUMAN_REVIEW_REQUIRED`;
4. the target Slot is currently `LOCKED`;
5. the locked target Candidate is still `LOCKED`;
6. Candidate Asset ID/SHA exactly matches the inspected target.

`DIRECT_CONTINUATION` never exposes a Human override action. Exact End/Start Asset identity remains mandatory.

## One-shot Human authority

Preparing a soft approval produces a one-shot confirmation bound to:

- continuity edge ID;
- exact target Candidate ID;
- exact target Asset SHA-256;
- exact current continuity-resolution hash.

Applying the confirmation revalidates all four bindings plus current Slot/Candidate lifecycle. If anything changed, the operation fails closed as stale and a new Human review is required.

## Non-goals

This workspace does not:

- start image/video generation;
- silently repair continuity;
- unlock or replace a Production Candidate;
- override `DIRECT_CONTINUATION`;
- approve a target that has not been inspected;
- convert a Human soft approval into a general learned rule.

## Acceptance

Automated acceptance covers projection integrity, exact soft-boundary approval, stale-confirmation rejection and hard-boundary non-overridability. Native GUI acceptance remains part of the later unified Product shell.
