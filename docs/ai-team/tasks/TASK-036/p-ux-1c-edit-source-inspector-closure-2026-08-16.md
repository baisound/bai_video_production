# P-UX-1C Edit Source and Inspector closure

Date: 2026-08-16
Atomic unit: `EDIT_SOURCE_INSPECTOR_CLOSURE_R0`

## Design and Critic

The V6.1.1 Edit page left its Source panel as a static placeholder and did not
project the selected Timeline Clip into the Inspector. TASK-044 already returns
a bounded viewport projection containing up to 500 exact Clips with Source
owner/ref/SHA-256, media kind, frame range, state, and optional Cut Review
Candidate identity.

This slice reuses that exact projection. The left panel filters only the Clips
in the current bounded viewport and selects a Clip through the existing Python
Timeline interaction controller. The Inspector projects the same snapshot and
reports when a selected Clip has moved outside the current viewport.

Builder Critic: presenting viewport Clips as a complete Asset Library would
inflate Product coverage. Correction: the panel explicitly identifies itself
as a maximum-500 viewport projection and does not expose import or add actions.
Security Critic: a UI selection could become browser-local durable editing
truth or expose host paths. Correction: selection uses the existing
`interactive_timeline_select` call with exact Timeline SHA, the UI states that
selection is non-durable, and only Product source identities/digests are
displayed.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Source rows project exact Clip, Track/media kind, Product Source owner/ref,
  SHA-256, frame range, state, and optional Review Candidate.
- Search is local filtering over the current bounded Product projection only.
- Row selection binds the current Timeline SHA and refreshes from Python.
- Inspector handles no selection, visible selection, and selected IDs outside
  the current bounded viewport without fabricating fields.
- Timeline review styling now uses the canonical `review_candidate_id` field;
  the stale `cut_candidate_id` lookup was removed.
- No complete Asset Library, host path, import, add, replacement, or durable
  JavaScript state is claimed.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `187 passed`.
- Full regression: `1256 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
