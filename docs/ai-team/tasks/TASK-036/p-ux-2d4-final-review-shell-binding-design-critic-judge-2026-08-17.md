# TASK-036 P-UX-2D4 Final Review Shell Binding

Date: 2026-08-17
Atomic unit: `P-UX-2D4_FINAL_REVIEW_SHELL_BINDING_R0`

## Boundary

P-UX-2D1 already computes Final Review readiness, P-UX-2D2 defines the typed
Human approval receipt and P-UX-2D3 persists approvals append-only. P-UX-2D4
connects those contracts to the trusted Shell without manufacturing any of the
five external Gate decisions.

The Shell accepts only typed `FinalReviewExternalGateReceipt` values supplied by
a trusted provider. Each wrapper binds the exact lower receipt identity/hash,
closed owner, Project, Timeline, state, evaluation time and invalidation epoch.
Its canonical checksum is independently recomputed. The provider is called for
every readiness snapshot, prepare and apply operation, so a revocation between
Human confirmation and application invalidates the pending approval.

## Human operation and effects

The Final Review page exposes the exact sequence:

1. read current Product sources and all external Gate receipts;
2. show blockers and the durable approval-history state;
3. prepare one approval against the exact readiness and history CAS hashes;
4. request an explicit Human confirmation and logical actor ID;
5. recompute all current inputs and append the typed approval only if unchanged.

The trusted launcher binds the P-UX-2D3 application but binds no external Gate
provider by default. Therefore a normal launch remains blocked until an owning
composition root supplies current typed receipts. This unit creates no Audio
receipt, Export preparation or job, dispatch, render, publication or automatic
retry.

## Critic

### Builder / Completeness

Finding: connecting only the approval store would leave all five required Gate
rows permanently missing. Correction: add a closed typed wrapper and exact
provider collection, while retaining `MISSING` for every unsupplied owner row.

### Security / Authority

Finding: a launch-time PASS tuple could remain trusted after a lower receipt was
revoked. Correction: invoke and validate the provider at snapshot, prepare and
apply; full readiness byte equality then rejects confirmation-time drift. Raw
mappings, duplicate Gate IDs, owner mismatch, checksum tamper and authority
inflation all fail closed.

### Operations / Compatibility

Finding: exposing approval through the page could accidentally imply Export.
Correction: every bridge result and durable snapshot keeps Export Job, render and
publication false. Existing read-only readiness API remains source-compatible;
the launcher adds only an optional provider injection and otherwise stays
blocked.

Residual C/H/M: `0/0/0`.

## Judge

Required Evidence includes typed receipt round-trip/tamper tests, owner/state and
cap checks, missing/duplicate/raw injection negatives, revocation between
prepare/apply, durable approval currentness, UI contract checks, trusted-launcher
no-effect binding, D1-D3 regression, full repository regression, compileall and
clean diff.

Provisional Judge: `PASS_NO_EFFECT_SHELL_BINDING`, Residual C/H/M `0/0/0`.

## Next boundary

P-UX-2D5 may compile one private `ExportPreparation`, validate a selected preset
and logical destination, and enqueue one durable TASK-044 job from the current
typed approval. It must not expose host paths to the WebView or combine queue
creation with dispatch/render authority.
