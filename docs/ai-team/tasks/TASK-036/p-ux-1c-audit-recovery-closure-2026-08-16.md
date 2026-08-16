# P-UX-1C Audit recovery closure

Date: 2026-08-16
Atomic unit: `AUDIT_RECOVERY_CLOSURE_R0`

## Design and Critic

The Asset Review projection correctly blocked new Human Decisions while a
TASK-038 transaction required recovery, but did not expose the exact recovery
actions already computed by `Task038AuditApplication`. This could leave an
otherwise recoverable `OLD_OLD`, one-sided write, or `NEW_NEW` state parked.

This slice renders only the canonical `recovery.available_actions` intersection
with the closed UI allowlist `COMPLETE | ABANDON | FINALIZE`. Each action needs
an explicit confirmation that identifies the recovery state, transaction, and
candidate before calling `audit_apply_recovery`.

Builder Critic: adding a generic Recovery button could hide materially
different persistence outcomes. Correction: each exact action is labelled and
ABANDON receives the destructive visual treatment. Security/Completeness
Critic: the browser must not manufacture COMPLETE for an UNKNOWN mixture.
Correction: the action must occur in both the closed allowlist and the current
snapshot; an empty action set remains a manual-investigation blocker.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Recovery controls appear only when `recovery.required` is true.
- COMPLETE, ABANDON, and FINALIZE are the only UI-recognized actions.
- The selected action must also be present in the exact current
  `available_actions` set.
- UNKNOWN mixtures display no recovery control and remain fail-closed.
- New Candidate Human Decisions remain blocked for the entire recovery state.
- No action runs automatically and no provider, regeneration, LOCK, physical
  deletion, or external editor operation is introduced.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `191 passed`.
- Full regression: `1260 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
