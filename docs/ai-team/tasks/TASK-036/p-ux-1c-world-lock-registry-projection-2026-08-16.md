# P-UX-1C WORLD LOCK registry projection

Date: 2026-08-16
Atomic unit: `WORLD_LOCK_REGISTRY_PROJECTION_R0`

## Design and Critic

The WORLD LOCK page currently displays the entire Production workspace as a
generic JSON projection. The released Product schema already distinguishes the
canonical reference roles as `CHARACTER_REFERENCE`, `SPACE_REFERENCE` and
`COMPOSITION_REFERENCE`; no new schema or inference is needed.

Project the three role tabs and search over exact canonical Slot fields. Show
Scene, Slot, kind, status, required state, revision, stale state, Candidate
count and exact locked Candidate/Asset/SHA where present. Keep all non-reference
Slots visible in the central Production workspace and do not treat absence from
the left filtered Registry as deletion.

Builder Critic: a role filter could silently discard other Slot kinds.
Correction: only the dedicated left Registry is filtered; the central workspace
continues to render every Slot. Security Critic: a mock-like Registry could
invent Candidate creation or Provider execution. Correction: tabs and search
are read-only UI selection; the only durable action remains the existing exact
`production_prepare_lock` / `production_apply_lock` contract.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- The three tabs bind exact `SlotKind` values and expose ARIA tab state.
- Search filters only canonical Slot fields and never searches host paths or
  media bytes.
- The left Registry shows exact locked Candidate/Asset/SHA identity; the
  central workspace still renders every Slot kind.
- Candidate creation, generation and Provider execution methods remain absent.
- The pre-existing per-Candidate LOCK prepare/apply contract is unchanged.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `169 passed`.
- Full regression: `1238 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
