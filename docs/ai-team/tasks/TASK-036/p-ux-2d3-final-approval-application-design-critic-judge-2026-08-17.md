# TASK-036 P-UX-2D3 Final Approval Application

Date: 2026-08-17
Atomic unit: `P-UX-2D3_FINAL_APPROVAL_APPLICATION_R0`

## Finding and boundary

P-UX-2D2 defines an immutable typed approval receipt but intentionally owns no
persistence.  Reconstructing an approval from UI state, a digest alone, or a
stale readiness projection would let the Export boundary consume a decision
that was never durably recorded.  P-UX-2D3 therefore adds only a Project-scoped
append-only application.  It does not bind Shell actions or create Export jobs.

The application uses a two-step Human confirmation.  Preparation freezes the
entire canonical readiness document and its current approval-history CAS
coordinate.  Apply requires byte-identical readiness, consumes the confirmation
once, creates a deterministic receipt identity, and atomically appends one row.
The maximum is 256 approvals.  A repeated approval for one exact readiness is
rejected rather than treated as a new decision.

## Integrity and lifecycle

- The readiness projection SHA is independently recomputed before approval.
- Stored receipts are round-tripped through the D2 typed parser; missing,
  additional, reordered coordinate sets and checksum/effect inflation reject.
- Snapshot revision equals the exact append-only row count.
- Receipt IDs and receipt hashes are unique.
- Replacing a snapshot requires the exact prior snapshot SHA.
- A current readiness different from the latest receipt is `APPROVAL_STALE`;
  absence is `NO_APPROVAL`, never an implicit approval.
- The store is bounded to 2 MiB and 256 rows and rejects symlinks/non-files.

## Authority boundary

The receipt records an explicit Human decision only.  The application reports
`export_job_created=false` and `render_or_publish_started=false`.  It does not
create external owner receipts, especially the Developer2-owned Audio receipt.
It accepts no output path, media bytes, runner, Provider, process, network or
dispatch callback.  Shell UI, queue creation, individual dispatch, rendering,
publication, Native H3, Release and Deploy remain later Gates.

## Critic

### Builder / Completeness

Finding: a single mutable approval file would erase decision history and make
staleness unauditable.  Correction: persist revisioned rows append-only and
project current/stale status against the latest exact receipt.

### Security / Authority

Finding: trusting the `projection_sha256` field would permit changed readiness
content to reuse an old digest.  Correction: recompute the canonical projection
hash, freeze the full document across prepare/apply and reject every no-effect
flag inflation.

### Operations / Compatibility

Finding: process-local confirmation cannot safely survive a crash as approval.
Correction: only the atomically validated receipt is durable; a lost pending
confirmation creates no row and a fresh prepare is required.  Existing D1/D2
and TASK-044 APIs remain source-compatible.

Residual C/H/M: `0/0/0`.

## Judge

Required evidence: deterministic receipt, CAS conflict, stale readiness,
single-use confirmation, duplicate decision, tamper, symlink, cap+1, atomic
failure and no-effect negatives; D1/D2/TASK-044 regression; full repository
regression; exact6 paths and clean diff.

Provisional Judge: `PASS_NO_EFFECT_APPLICATION`, Residual C/H/M `0/0/0`.

## Next boundary

P-UX-2D4 may bind independently supplied current external receipts into the
Shell, expose prepare/apply to the owning Human surface, compile the private
Export preparation and create one durable queued job.  It must not infer Audio
completion or dispatch/render authority.
