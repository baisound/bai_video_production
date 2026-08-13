# TASK-039 — Continuity Map / Boundary Integrity & Stale Propagation
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_NOT_AUTHORIZED_BY_THIS_DOCUMENT`
- Depends on: TASK-037, TASK-013 contracts

## Objective

Make cross-scene continuity a graph contract instead of an informal prompt convention.

## Boundary types

- `DIRECT_CONTINUATION`
- `SOFT_CONTINUITY`
- `DISCONTINUOUS`

For `DIRECT_CONTINUATION`, next Start must reference the exact prior End Asset identity/hash. Similar-looking regeneration is not equivalent.

## Continuity edge

- edge_id
- from_scene/from_slot/from_candidate/from_asset_sha256
- to_scene/to_slot
- boundary_type
- character_contract_refs[]
- space_contract_refs[]
- locked_at
- stale_state

## Stale propagation

If an upstream locked Asset/Contract changes:

1. mark direct dependents STALE;
2. traverse dependency graph deterministically;
3. record root cause path;
4. do not regenerate;
5. do not clear prior Human decisions;
6. require Human resolution/acceptance before downstream lock can become current again.

Cycle detection is mandatory.

## Continuity inspection

May compare:

- exact hash for DIRECT_CONTINUATION;
- Character Contract attributes;
- Scene/Space anchors;
- allowed motion vs identity-stable attributes;
- temporal boundary metadata.

Vision judgement is Evidence, not automatic Human approval.

## Acceptance draft

- exact End->Start identity pinned for DIRECT_CONTINUATION;
- stale root cause path explainable;
- cycles rejected;
- no silent regeneration/replace;
- Human resolution preserved;
- downstream high-cost generation blocked while required inputs are STALE.
