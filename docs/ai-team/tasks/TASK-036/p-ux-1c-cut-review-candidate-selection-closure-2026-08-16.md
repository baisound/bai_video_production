# P-UX-1C Cut Review candidate selection closure

Date: 2026-08-16
Atomic unit: `CUT_REVIEW_CANDIDATE_SELECTION_CLOSURE_R0`

## Design and Critic

The V6.1.1 Edit inspector exposed KEEP and CUT, but it had no visible control
that selected one of the canonical Cut Review candidates. Timeline clip
selection belongs to the non-durable TASK-044 interaction state and therefore
cannot substitute for `Task036ReviewFacade.select_candidate`.

This slice renders every candidate returned by `review_snapshot` in the Edit
inspector and selects it through the exact `select_candidate` bridge method.
The selected row exposes candidate kind, strength, Evidence codes, range, and
current review state. KEEP/CUT remain a separate explicit Human Decision.

Builder Critic: making a Timeline clip click silently decide or select a Cut
candidate would conflate two state machines. Correction: candidate selection
has its own labelled button and `aria-pressed` state. Security/Completeness
Critic: the prior `all_reviewed` predicate was not present in the canonical
snapshot, so approval could never be enabled and a UI-local substitute would
be unsafe. Correction: approval consumes exact `unresolved_count == 0` and
requires the absence of an existing approved plan.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- `review_snapshot.candidates` is the only candidate population rendered.
- Candidate selection calls `select_candidate` with the exact candidate ID.
- Selection never implies KEEP, CUT, final plan approval, Resolve, render, or
  another external effect.
- KEEP/CUT continue to call the existing Human Decision bridge only after a
  candidate is selected.
- Candidate Evidence, time range, review state, reviewed count, and unresolved
  count are projected from the canonical snapshot.
- Edit Plan approval is enabled only when the workspace is available,
  `unresolved_count` is zero, and no approved plan exists.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `191 passed`.
- Full regression: `1260 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
