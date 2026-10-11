# TASK-111 Atomic Unit A — Immutable Audit Input Bridge Design

## Boundary

The existing durable path remains:

```text
V6.1.1 Shell
  -> Task111AuditInputController (ephemeral confirmation only)
    -> Task038AuditApplication.record_audit
      -> CandidateAuditSnapshotStore
```

TASK-111 introduces no store, schema, Candidate lifecycle transition or Human
Candidate-decision API. Structured AI inspection remains on the existing
TASK-013 path:

```text
VisualComplianceGate
  -> VisualComplianceAuditAdapter
    -> Task013GenerationSafetyApplication.record_visual_compliance
      -> Task038AuditApplication.record_audit
```

## Prepare contract

The Shell supplies structured Human input together with the Candidate ID,
Asset ID, Asset SHA-256 and both current snapshot hashes. The controller:

1. constructs a strict TASK-038 `AuditRecord` with `auditor_kind=HUMAN`;
2. rereads the canonical Audit Workspace;
3. rejects recovery-required state or snapshot mismatch;
4. resolves exactly one Candidate and verifies it is `READY_FOR_AUDIT`;
5. verifies exact Asset ID and SHA-256;
6. admits only the first Audit (`audit_count == 0`);
7. requires at least one contract reference and one finite numeric score,
   bounds refs/findings/failure codes/proposals and caps one canonical record
   at 1 MiB;
8. loads the current TASK-038 Audit registry, adds the record only in memory,
   and rejects the operation unless the full serialized snapshot plus trailing
   newline remains within TASK-038's existing 8 MiB load boundary;
9. retains the record in memory under a unique one-shot confirmation token;
10. returns the canonical record SHA-256 and exact identity for Human review.

Prepare performs no canonical write.

## Apply and cancel contract

Apply requires both the confirmation token and literal
`explicit_human_confirmation: true`. The token is consumed before the write so
double submission cannot replay the operation. The controller delegates to
`Task038AuditApplication.record_audit`, which rechecks both snapshot hashes and
the Candidate/Asset binding. The returned canonical snapshot must contain one
record with the prepared audit ID and exact record digest.

Cancel consumes the token without calling TASK-038. A failed save also leaves
the token consumed; the operator must refresh and prepare again rather than
blindly replay an ambiguous request.

## UI contract

Only a `READY_FOR_AUDIT` Candidate with zero Audits and no active recovery
shows `監査記録を入力`. The operator enters:

- unique Audit ID and auditor ID/version;
- contract references;
- dimension scores from 0 through 100;
- structured findings;
- failure codes and alternate-use proposals.

Each JSON prompt is evaluated sequentially, so cancel or invalid JSON stops all
later prompts and remains effect-zero. Prepare/apply/cancel RPC failures use one
fixed public-safe message and never render a backend exception or private path.
After successful prepare, the confirmation
shows Candidate, Asset, Asset digest, Audit/auditor identity and immutable
record digest, plus the explicit statement that no Candidate decision, LOCK or
Provider execution occurs. Decline calls cancel; confirm calls apply and then
rereads the canonical Production/Audit projection.

## Failure modes

- wrong or missing Candidate: fail before confirmation;
- Candidate not `READY_FOR_AUDIT`: fail before confirmation;
- Asset ID or digest mismatch: fail before confirmation;
- stale Production or Audit snapshot: fail before confirmation or at TASK-038
  apply recheck;
- recovery-required state: no input action and controller fail-closed;
- existing Audit: no second manual Shell Audit;
- invalid IDs, enums, fields, score range or JSON: effect-zero;
- empty required review evidence, non-numeric/non-finite score, unbounded item
  count, record over 1 MiB or complete projected snapshot over 8 MiB: reject
  before confirmation/write;
- projected-snapshot rejection preserves the existing canonical file byte for
  byte and it remains reopenable;
- duplicate or reused confirmation: rejected;
- persistence failure: public-safe error, no blind replay, reopen remains
  authoritative;
- readback mismatch: data-integrity failure;
- Human Candidate ACCEPT/REJECT/ALTERNATE/REGENERATE and LOCK remain separate
  existing confirmations after an Audit is visible.

## Verification plan

- red-before-green dedicated controller contract;
- real TASK-038 save/reopen and lifecycle/decision assertions;
- wrong identity, stale snapshots, duplicate, save-failure, one-shot, bounded
  malformed-input and real near-limit store/no-mutation/reopen tests;
- exact Shell request allowlist and meter invalidation test;
- extracted real V6.1.1 JavaScript interaction scenarios for input, confirm,
  cancel, invalid JSON, early prompt stop and public-safe backend failures;
- existing TASK-038 Human decision/recovery regression;
- existing TASK-013 Visual Compliance adapter/application regression;
- V6.1.1 visual contract, trusted-launch and packaged-entry source tests;
- compileall, diff check and exact Allowed Files review;
- independent DEV-4 Critic and Tester, followed by bounded fixes/retests if
  required.
