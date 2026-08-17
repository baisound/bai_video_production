# TASK-036 P-UX-2D2 Final Approval / Export Binding

Date: 2026-08-17
Atomic unit: `P-UX-2D2_FINAL_APPROVAL_EXPORT_BINDING_R0`

## Finding

P-UX-2D1 closes read-only readiness, while TASK-044 already owns durable
Export preparation, queue, dispatch and reconciliation.  The remaining exact
gap is between them: `ExportPreparation` binds Project Manifest, Timeline,
Edit Plan, Assembly Plan and Preset, but not the element contract's required
`final_approval_receipt_sha256`.  A queue item could therefore be authored
without proof that the exact Timeline passed the full Final Review gate set.

## Design

`FinalReviewApprovalReceipt` records one explicit Human `APPROVE` decision over
an exact `READY_FOR_TYPED_FINAL_REVIEW` projection.  It binds:

- Project and Project Manifest;
- edited Timeline;
- P-UX-2D1 projection;
- exact Production, Audit, Visual Handoff, Timeline and Project Manifest source
  snapshot set;
- exact PASS receipt set for Audio completion, Edit persistence, Privacy,
  Resource and Rights/License;
- explicit actor and canonical UTC decision time.

The constructor rejects unavailable/non-ready projections, any blocker,
missing/extra/duplicate/non-PASS gate, invalid digest, source-key mismatch and
readiness carrying forbidden authority.  Its deterministic receipt explicitly
states that no Export Job, render or publication was started.

`ExportPreparation` now consumes the typed object, requires exact
Project/Manifest/Timeline equality, includes its digest in `input_hashes`, and
serializes `final_approval_receipt_sha256`.  Existing TASK-044 enqueue,
preflight, per-job confirmation, dispatch and UNKNOWN recovery remain unchanged.

## Caps and boundaries

- Source snapshot set: exact 5 scalar SHA coordinates.
- External gate set: exact 5 scalar SHA coordinates.
- Final decision: exact `APPROVE`; absence is not approval.
- No path, bytes, runner, callback, filesystem, network or process field.
- No persistent approval is created by the Shell in this unit.
- Audio receipt ownership remains Developer2; this unit only validates its
  exact coordinate.
- Export queue creation, dispatch, render, QA, publication, Native H3, Release
  and Deploy remain separate Gates.

## Critic

### Builder / Completeness

Finding: adding only a free-form approval digest to `ExportPreparation` would
not prove the digest came from the current Project and Timeline.  Correction:
the preparation consumes a typed receipt object and independently checks the
three scope equalities before including its canonical digest.

### Security / Authority

Finding: readiness could be relabeled approval or a blocked gate could be
omitted.  Correction: approval creation requires exact ready state, zero
blockers, the complete fixed five-gate PASS registry and all no-effect flags
false.  It still does not authorize or start Export.

### Operations / Compatibility

Finding: changing TASK-044 input hashes could invalidate callers silently.
Repository-wide search found one synthetic constructor.  Correction: that
fixture now supplies the typed approval, idempotency derives from the new exact
input hash set, and the full queue lifecycle regression remains required.

Residual C/H/M: `0/0/0`.

## Judge and verification

- deterministic receipt/digest: required;
- missing/UNKNOWN/duplicate/authority-inflated gate rejection: required;
- invalid source/hash/time and cross-scope Export rejection: required;
- TASK-044 queue lifecycle regression: required;
- P-UX-2D1 readiness regression: required;
- full repository regression, compileall and `git diff --check`: required;
- changed paths exact6: required.

Provisional Judge: `PASS_NO_EFFECT_CONTRACT`, Residual C/H/M `0/0/0`.

## Next boundary

P-UX-2D3 may add durable Final Review storage/application composition and bind
real external owner receipts.  P-UX-2D4 may expose preset/destination validation
and queue creation in the Shell.  No such authority is inferred here.
