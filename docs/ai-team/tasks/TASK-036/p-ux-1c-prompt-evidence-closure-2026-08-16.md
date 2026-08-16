# P-UX-1C Prompt Evidence closure

Date: 2026-08-16
Atomic unit: `PROMPT_EVIDENCE_CLOSURE_R0`

## Design and Critic

The V6.1.1 Scene Design and Quick pages previously rendered the existing
Prompt Evidence snapshot as generic JSON. TASK-040 already provides a typed,
versioned Application boundary for Prompt metadata, completed Generation
Evidence, recovery, and a Human `NEEDS_REGENERATION`-derived next Prompt
version.

This slice connects only those existing metadata and Evidence operations. A
Prompt stores a private body reference and SHA-256 rather than embedding the
Prompt body. A completed Generation attempt is imported as Evidence; it does
not run a Provider. Regeneration records a new Prompt version only after the
existing Human decision is present and never starts generation.

Builder Critic: generic rendering did not expose the one-shot confirmation,
snapshot binding, or recovery boundary. Correction: each mutation uses the
existing prepare/apply pair with exact Prompt, Production, and where required
Audit snapshot identities; recovery suppresses new registration actions.
Security Critic: a Prompt or attempt row could be mistaken for Provider
authority, or a claim-only attempt could expose regeneration. Correction: the
UI requires `actions_allowed`, `human_regeneration_available`, and an exact
output Candidate ID, keeps the Quick generation action disabled, and states
that no Provider, paid, Candidate, automatic regeneration, or Human-decision
effect occurs.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Scene Design renders versioned Prompt metadata, input hashes, keep
  conditions, completed attempt receipts, and recovery state.
- Quick renders a bounded read-only Prompt index and explicit execution/paid
  authority state; it does not acquire an execution call site.
- Prompt registration binds current Prompt and Production snapshots.
- Attempt Evidence binds current Prompt and Production snapshots and enforces
  the PASS/output-Candidate null predicate.
- Next-version metadata additionally binds the current Audit snapshot and is
  offered only for an exact Human regeneration Candidate.
- Prompt body content is not embedded; only its private reference and digest
  are projected.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `181 passed`.
- Full regression: `1250 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
