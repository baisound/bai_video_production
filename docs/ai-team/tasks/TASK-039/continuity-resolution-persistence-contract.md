# TASK-039 — Continuity Resolution / Persistence Contract Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED / HUMAN_VISUAL_REVIEW_REMAINS`

## 1. Boundary semantics

### DIRECT_CONTINUATION
The next Start boundary must use the **exact same Asset identity and SHA-256** as the previous End boundary. A Human may not override an identity mismatch. The Asset or boundary type must be corrected instead.

### SOFT_CONTINUITY
A different Asset is allowed only after explicit Human inspection/approval. Human approval is stored separately from machine validation.

### DISCONTINUOUS
No continuity identity requirement blocks generation.

## 2. Generation admission

Generation-safe status is granted only for:

- machine `PASS`; or
- explicit `HUMAN_APPROVED` soft continuity.

`FAIL`, `HUMAN_REVIEW_REQUIRED`, missing inspection and missing edge state all fail closed.

## 3. TASK-037 stale integration

Continuity edges map into TASK-037 DependencyGraph as `DependencyKind.CONTINUITY`.

When an upstream End Slot becomes STALE, downstream Start Slot staleness propagates through the existing dependency graph. This propagation **does not start regeneration automatically**.

## 4. Persistence

`ContinuityRegistryStore` provides:

- atomic JSON write;
- deterministic SHA-256 identity;
- compare-and-swap replacement;
- symlink refusal;
- bounded file size;
- recovery validation;
- machine/Human resolution persistence.

The persisted state contains relationship/decision metadata only, not media bytes.

## 5. Safety

- Rejecting a continuity target does not delete an Asset.
- DIRECT_CONTINUATION exact identity is not weakened by Human approval.
- SOFT_CONTINUITY approval requires a non-empty Human identity.
- STALE propagation never silently regenerates downstream media.
- Tampered persistence fails closed.
