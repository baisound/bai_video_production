# TASK-078 — E-C Downstream Complete Design

Date: `2026-09-02`

State: `DESIGN_FROZEN / JUDGE_ACCEPTED / IMPLEMENTATION_EFFECTS_NOT_AUTHORIZED`

## 1. Outcome and non-duplication boundary

The designed vertical is:

```text
central model selection
  -> approved Planning proposal
  -> TASK-077 public development-completion Gate (implementation dependency)
  -> TASK-027 canonical Scene-finalization receipt
  -> E-C1 current Scene epoch binding
  -> TASK-027 AI Video Queue entry
  -> TASK-013 local/free execution terminal + typed media receipt
  -> TASK-027 adoption as TASK-003 GENERATED_VIDEO Asset
  -> TASK-038 Audit/Human Review -> TASK-037 LOCK
  -> E-C3 generated-video-only TASK-044 Timeline placement
  -> E-C4 current canonical owner Gate receipts
  -> TASK-036 typed Human Final Approval
  -> TASK-044 Export Queue/dispatch/result read-back
  -> TASK-036 packaged EXE F0-F10 aggregate
```

No arrow transfers canonical ownership. TASK-036 is a composition/UI consumer;
it does not mint Scene truth, generated media facts, Audit decisions, Timeline
history, owner Gate decisions or Export results.

## 2. Dependency graph and implementation allocation

```text
TASK-077 public development completion
          |
       E-C1 / TASK-079
       /              \
E-C2 / TASK-080    E-C4 / TASK-081
       \              /
        E-C3 / TASK-082
               |
        E-C5 / TASK-083
```

E-C3 depends on both E-C2 and E-C4 by Owner direction. The E-C4 dependency is
an admission dependency, not permission for placement to mint or bypass Final
Gate receipts. E-C2 and E-C4 have disjoint canonical write owners and may be
implemented/reviewed in parallel after E-C1 reaches a public merged boundary.

## 3. Cross-unit invariants

1. Every new generated-video record binds exact `project_id`, `scene_id`, an
   explicit non-negative `scene_epoch`, current Scene-epoch receipt hash and
   upstream snapshot hashes. Explicit epoch `0` is valid only for the current
   canonical root/no-structure-change epoch; a missing field is never inferred
   as `0`.
2. A missing epoch, an epoch lower than the current canonical epoch, any other
   non-current epoch or an unavailable TASK-027 Proposal/finalization source is
   history-only. A missing TASK-077 public development-completion receipt
   blocks implementation start rather than acting as runtime Scene truth.
   Provider call, adoption, Audit promotion,
   LOCK use, Timeline placement, Final Approval and Export effect counts remain
   zero.
3. Checksums prove canonical bytes only; they never prove authority, rights,
   currentness, runtime execution or Human approval.
4. Every Human operation is prepare -> explicit confirmation -> apply, with a
   single-use bounded token and apply-time current-source revalidation.
5. Browser/UI input contains logical IDs and checksums only. Host paths, media
   bytes, Prompt bodies, credentials, adapters and callbacks remain private.
6. A state persisted before an uncertain external effect is never blindly
   replayed after restart. `DISPATCHING`/partial state becomes explicit
   `RECOVERY_REQUIRED` or `UNKNOWN` and requires owner reconciliation.
7. Existing IMAGE placement remains byte- and behavior-compatible. E-C3 accepts
   `AssetType.GENERATED_VIDEO` only and cannot widen P-UX-2H IMAGE eligibility.
8. Final Gate PASS can be issued only by each canonical owner. TASK-036 parses,
   scopes and consumes; it never wraps a fixture, cached tuple or self-hashed
   project JSON into authority.
9. Queue insertion and Export dispatch remain separate Human confirmations.
10. Release, Deploy, publication and Production Activation remain outside all
    five implementation candidates.

## 4. Shared receipt conventions

Every new ABI is exact-field, canonical-JSON and checksum closed. It carries:

- semantic version and record type;
- canonical `task_owner`;
- logical record identity and monotonically ordered revision/epoch where
  applicable;
- exact Project/Scene/Timeline coordinates required by its owner;
- upstream receipt/snapshot SHA-256 coordinates;
- closed state enum and explicit currentness/invalidation semantics;
- explicit false effect flags;
- canonical `receipt_sha256` over every prior field.

Unknown fields, unknown enum values, duplicate coordinates, unsorted closed
sets, cross-project borrowing, invalid hashes, cap+1, symlinks, oversized
documents, forked latest chains and version downgrades fail closed.

## 5. Vertical UI rule

E-C5 presents one F0-F10 progress model. It does not create a second workflow.
Each stage links to the existing owning workspace and invokes only that
workspace's already-authorized prepare/apply command. Status is re-read from
canonical sources after every action and after restart; JavaScript state is
never durable.

## 6. Global failure/restart contract

| Condition | Required projection | Automatic effect |
|---|---|---|
| TASK-077 public development completion absent at implementation start | `BLOCKED_IMPLEMENTATION_DEPENDENCY` | 0 |
| TASK-027 finalization receipt absent/unparseable | `BLOCKED_SCENE_RECEIPT` | 0 |
| current Scene epoch differs | `STALE_SCENE_EPOCH` | 0 |
| execution terminal lacks typed media | `MEDIA_READBACK_REQUIRED` | 0 |
| output bytes or media facts drift | `DATA_INTEGRITY_BLOCKED` | 0 |
| Audit/LOCK missing | `HUMAN_REVIEW_REQUIRED` | 0 |
| ProjectSave participant/journal incomplete | `RECOVERY_REQUIRED` | 0; no placement replay |
| any owner Gate MISSING/UNKNOWN/STALE/REVOKED | exact Gate blocker | 0 |
| Final Approval stale | `APPROVAL_STALE` | 0 |
| Export Job interrupted after dispatch admission | `UNKNOWN_RECONCILIATION_REQUIRED` | 0; no render replay |
| canonical source unavailable | `SOURCE_UNAVAILABLE` with exact source names | 0 |

## 7. Unit documents

- `ec1-scene-epoch-downstream-binding.md`
- `ec2-generated-video-readback-review.md`
- `ec4-final-gate-owner-readers.md`
- `ec3-generated-video-timeline-placement.md`
- `ec5-packaged-vertical-exe-f0-f10.md`

The apparent E-C4/E-C3 filename order matches the dependency order rather than
the numeric label order.

## 8. Completion gates

TASK-078 is complete only after every Unit document passes independent
completeness, security/authority, compatibility/recovery Critic review and an
independent Judge with unresolved Critical/High `0 / 0`. The design PR may be
created only after that result and local static/diff/scope validation.
