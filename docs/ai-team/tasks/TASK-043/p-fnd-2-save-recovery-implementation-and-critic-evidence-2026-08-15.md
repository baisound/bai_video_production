# TASK-043 — P-FND-2 Save/Recovery Implementation and Critic Evidence

- Baseline: `main@e2930baa2cd66e92514e538e2834e89a8119d19f`
- Unit: `P-FND-2 coordinated save journal / manifest-last commit / recovery`
- External/Provider/paid/native/media operation: `false`
- Real user Project mutation: `false`; temporary fixtures only

## Implemented

- Project-scoped cross-process lock reused across final validation, child commit
  and manifest switch;
- deterministic save operation identity and transaction-scoped staging/backup;
- PREPARING -> STAGED -> VALIDATED -> COMMITTING -> COMMITTED journal;
- bounded child/total staging and streaming backup/copy;
- source Manifest and every changed child revalidation before commit;
- child replacement followed by manifest-last atomic CAS commit;
- `RECOVERY_REQUIRED` on injected interruption;
- typed `COMPLETE`, `ROLLBACK` and post-manifest `FINALIZE` recovery;
- exact-child idempotency during resume and same-operation retry after rollback;
- new-save refusal while a non-terminal recovery exists;
- closed public/package Project Save Journal Schema and focused failure-injection
  tests.

The coordinator never deletes Audit/Prompt Evidence, never replays an external
operation and never applies a format migration. Binding removal remains an
explicit migration/Human Gate.

## Local validation

- WSL2 Python 3.12 compileall: PASS.
- public API import: PASS.
- Manifest + Journal Draft 2020-12 schema validity/parity: PASS.
- normal child-first/manifest-last save and reopen: PASS.
- injected post-child interruption -> COMPLETE: PASS.
- injected post-child interruption -> ROLLBACK: PASS.
- rollback -> identical operation retry: PASS.
- post-Critic normal save/journal terminal smoke: PASS.
- Full pytest/compile/security: `HOSTED_PENDING`.

## Implementation Critic

1. `CRITICAL / CLOSED` — a tampered journal entry could redirect a staged path to
   another control file. Journal validation now binds every staged/backup path to
   `staging/<transaction>/new|backup/<exact child path>`, checks the target Manifest
   binding and recomputes operation identity.
2. `HIGH / CLOSED` — FINALIZE originally trusted the target Manifest without
   rechecking children. Recovery now verifies every required target child and exact
   checksum before terminalizing the journal.
3. `HIGH / CLOSED` — a second save could start while an interrupted transaction
   remained. Non-terminal journals now block new saves with a typed recovery Gate.
4. `HIGH / CLOSED` — removal of a current child binding could silently orphan
   Product truth. Removal is rejected until an explicit migration plan authorizes
   it.
5. `MEDIUM / CLOSED` — backup/restore read whole child files into memory. Both are
   now streamed through bounded chunks and atomic replacement.
6. `MEDIUM / CLOSED` — rollback followed by the same operation collided with safe
   leftover staging. Exact identical staging/backup is reusable; differing content
   fails closed.
7. `MEDIUM / CLOSED` — read-only recovery status could create the control folder.
   Journal path lookup no longer creates directories unless writing.

## Final Judge

P-FND-2 is `LOCAL_FAILURE_INJECTION_PASS / HOSTED_PENDING`. Unresolved
Critical/High is `0 / 0`. It may enter hosted review. P-FND-3 Undo/Redo,
Autosave and Backup retention remains not started. A foundation-only merge is not
a Release candidate.

