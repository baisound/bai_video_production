# P-UX-1C Export Job projection correction

Date: 2026-08-16
Atomic unit: `EXPORT_JOB_PROJECTION_CORRECTION_R0`

## Design and Critic

The V6.1.1 Export page used `cancel_available` and `progress_percent`, neither
of which exists in the TASK-044 Export Queue snapshot. The Product contract
returns `stage`, shell `state`, `safe_cancel`, `progress_kind`, optional
`progress_value`, operation identity, state version, recovery actions, and the
per-Job confirmation predicate.

This slice corrects the projection to those exact fields. A READY Job can only
prepare its own individual dispatch confirmation. Safe cancellation appears
only when the Product row states `safe_cancel=true`; UNKNOWN recovery is
limited to the three existing allowlisted Human actions.

Builder Critic: a button labelled only `実行` could imply that the browser
dispatches the external Export. Correction: it is labelled `このJobの実行確認を
準備` and the receipt states that the private launcher still performs a
separate confirmation. Security Critic: recovery or cancel controls inferred
from shell state could replay an ambiguous external effect. Correction: the UI
consumes only exact `safe_cancel`, `individual_confirmation_required`, and
`recovery_actions` values with the current `state_version`.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Every row projects exact stage, shell state, operation identity, progress,
  safe-cancel status, recovery set, confirmation requirement, error, and
  Evidence identity.
- Progress uses `progress_kind` when no numeric value exists and converts the
  canonical `0..1` value to a display percentage otherwise.
- Dispatch preparation remains per Job and does not start external execution.
- Cancel appears only for exact safe states and binds the current state
  version.
- UNKNOWN recovery consumes only `ACCEPT_PROVEN_SUCCESS`, `MARK_FAILED`, or
  `REQUIRE_HUMAN`; no automatic replay is added.
- Undefined `cancel_available` and `progress_percent` reads were removed.
- Blanket Execute All and persisted host output paths remain prohibited.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `189 passed`.
- Full regression: `1258 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
