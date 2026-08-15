# TASK-026 P-AUDIO-1 Product Promotion Critic, Judge and Authorization

Date: `2026-08-15`
Reviewed baseline: exact main
`5e061fb5d7463c00ad893d28fdf0cbb9b480b1ba`
Builder design:
`post-v0.21-product-promotion-current-main-audit-and-builder-design-2026-08-15.md`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`

## Critic round 1 - scope, ownership and Human authority

1. `CRITICAL / CLOSED`: the stale Task Index could cause duplicate TASK-026
   domain implementation. The design retains the existing compiler/binding and
   adds only the missing Product Application, persistence and Shell route.
2. `CRITICAL / CLOSED`: a button named compile could silently execute
   TASK-010/Resolve. The Application records only a TASK-026 Plan, exposes no
   execution callback and never calls the TASK-010 conversion method.
3. `CRITICAL / CLOSED`: caller fields could forge Candidate, Asset, range,
   fade, gain or Plan Evidence. Only review ID, track index, bed mode and exact
   snapshot expectations are accepted; all production facts are derived.
4. `HIGH / CLOSED`: TASK-026 could bypass Human creative authority. Exact
   TASK-041 ACCEPT, TASK-037 LOCK and one new plan-persistence confirmation are
   all required.
5. `HIGH / CLOSED`: TASK-026 could become a competing Timeline truth. TASK-042
   stays authoritative; TASK-026 stores immutable derived Evidence bound to its
   exact current item/revision/hash.
6. `HIGH / CLOSED`: `task010_compatible=true` could be presented as execution
   authorization. The field is labelled structural compatibility only; every
   persisted/UI execution authority remains false.
7. `HIGH / CLOSED`: automatic compile on ACCEPT or restart could hide a new
   action. Neither lifecycle event invokes TASK-026; prepare/apply is explicit
   and one-shot.

## Critic round 2 - persistence, currentness and recovery

1. `CRITICAL / CLOSED`: binding the newly written Product Manifest hash into
   compilation identity would make every record stale immediately. Identity
   uses exact upstream snapshots and Plan truth; the pre-save Manifest is audit
   provenance/CAS only and not a self-referential currentness dependency.
2. `CRITICAL / CLOSED`: a standalone file could escape TASK-043 atomic save.
   The store is an exact Product child; file and incremented Manifest commit
   through the existing coordinator, and unbound files fail closed.
3. `CRITICAL / CLOSED`: a crash could automatically repeat an operation. A
   pending TASK-043 journal blocks prepare/apply; only existing explicit
   COMPLETE/ROLLBACK recovery proceeds. No external operation exists to replay.
4. `HIGH / CLOSED`: cross-store state may change after prepare. Apply consumes
   the token, locks, reloads all inputs, re-derives the Plan and compares exact
   values before append.
5. `HIGH / CLOSED`: upstream may change immediately after a successful commit.
   The immutable record remains truthful for its captured inputs and derives as
   STALE on the next read; it can authorize no external work.
6. `HIGH / CLOSED`: Project upgrade could rewrite legacy child stores. Missing
   TASK-026 child is empty-compatible and no existing file/schema is migrated.
7. `HIGH / CLOSED`: history could grow without bound or expose paths/secrets.
   Count/byte/projection caps are strict and the schema excludes host paths,
   bodies, credentials and media.
8. `HIGH / CLOSED`: user-selected track index could imply proven NLE topology.
   It is confirmed Plan intent only. No track existence or Resolve readiness is
   claimed until a later TASK-010 integration validates the target.
9. `HIGH / CLOSED`: fade/gain could be lost during compatibility conversion.
   P-AUDIO-1 stores the exact TASK-026 Plan; incompatible fields remain visible
   and conversion/execution is absent.
10. `MEDIUM / CLOSED`: the Product could claim full TASK-026/audio completion.
    Status is bounded to `P_AUDIO_1_PRODUCT_PROMOTION`; generation, mixing,
    TASK-010 application and Native acceptance remain separate.
11. `HIGH / CLOSED`: ordinary legacy launcher Projects could be forced into a
    Product Manifest migration merely by opening Audio Workspace. Composition
    is optional: without an existing exact Manifest, TASK-041 remains usable and
    TASK-026 is unavailable. No Manifest or Timeline is inferred or created.

Unresolved Critical/High after two correction rounds: `0 / 0`.

## Final Plan

1. Preserve the existing TASK-026 compiler and cross-task binding.
2. Add a strict append-only Product child store with derived currentness.
3. Add project-scoped prepare/apply with complete revalidation and TASK-043
   coordinated persistence.
4. Add only narrow Audio Workspace plan-persistence controls and bounded status.
5. Prove legacy compatibility, tamper/stale/concurrency/recovery/privacy and no
   external side effect.
6. Synchronize the stale Task Index and publish through a design PR before any
   implementation branch exists.

## Judge

`P_AUDIO_1_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

Implementation is conditionally authorized only after this exact design passes
hosted checks, merges to main, its branch/checkout cleanup completes and a
fresh-main audit confirms no newer conflicting Source of Truth. Implementation
must remain inside the exact Allowed Files and order.

Provider execution, paid work, Credential input, media-byte mutation,
TASK-010/Resolve/Cubase mutation, Native H3 retry, Audit/ACCEPT/LOCK creation,
Production Deploy, version change, Tag and Release are not authorized by this
decision.
