# P-UX-1C Quick Intent projection closure

Date: 2026-08-16
Atomic unit: `QUICK_INTENT_PROJECTION_CLOSURE_R0`

## Design and Critic

The V6.1.1 Quick page was still a static form even though TASK-042 already owns
an immutable, CAS-bound Quick Intent registry. The missing Shell composition
meant persisted Intent, Prompt, Production, route, rights, cost, reference, and
authority-boundary facts were invisible.

This slice conditionally composes `Task042QuickGenerationApplication` only when
its persisted Prompt and Production prerequisites are regular non-symlink
files. The bridge exposes a read-only snapshot. The Quick page projects current
Intent rows, their exact references, and the three snapshot identities.

Builder Critic: a realistic Quick form without every execution-decision,
rights, cost, route, and compilation input could create an invalid authority
shortcut. Correction: new Intent creation remains disabled with the exact
missing-input reason. Security/Completeness Critic: rendering a Provider/model
identity could be mistaken for execution. Correction: every Intent displays
the canonical execution/candidate/media-write booleans and no prepare/apply or
Provider call is exposed.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- The trusted composition root binds TASK-042 only when both prerequisite
  snapshots exist as regular, non-symlink files.
- An unbound Quick application returns `available=false` rather than invented
  sample rows.
- Persisted Intent mode, Scene/Slot, Prompt/compilation, Provider profile,
  route/capability, rights, cost ceiling, and execution decision are projected.
- Reference rows preserve exact role, source kind, Asset SHA, Slot, Candidate,
  Intent ID, and version.
- Quick, Prompt, and Production snapshot SHA identities remain visible.
- Intent creation, Provider execution, paid execution, Candidate creation, and
  media write are not added.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `193 passed`.
- Full regression: `1262 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
