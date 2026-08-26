# TASK-029 R9D Path-local Signing Ceremony Journal — Design, Critic and Judge

Date: 2026-08-26
Profile: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
State: THIRD INDEPENDENT NO-GO REWORK COMPLETE / FOURTH REVIEW PENDING

## Atomic Unit

R9D provides a cooperative path-local no-replay state machine around R9C. It stores a body-free, checksum-bound reservation before the R9C signing boundary and commits only fully cross-bound typed R9C/R9A receipt hashes after immediate verification. Canonical project binding, deletion detection, directory durability and power-loss-safe persistent replay prevention remain explicitly NOT_CONFIRMED.

Allowed exact paths:

1. `docs/ai-team/tasks/TASK-029/task.md`
2. `docs/ai-team/tasks/TASK-029/knowledge-pack-durable-signing-journal-r9d-design-critic-judge.md`
3. `schemas/knowledge-pack-durable-signing-journal-receipt.schema.json`
4. `src/ai_video_production/knowledge_pack_durable_signing_journal.py`
5. `src/ai_video_production/schema_resources/knowledge-pack-durable-signing-journal-receipt.schema.json`
6. `tests/test_task029_knowledge_pack_durable_signing_journal.py`

`CHANGELOG.md`, `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`, R9B/R9C source, TASK-058 and TASK-054 paths are prohibited in this source Unit.

## State machine

```text
ABSENT
  -> atomic SIGNING_RESERVED before R9C signing
  -> SIGNED_AND_VERIFIED only after R9C + R9A receipt hashes are atomically committed

SIGNING_RESERVED after process interruption
  -> RECOVERY_REQUIRED on the next exact access
  -> no automatic replay

known exception after reservation
  -> RECOVERY_REQUIRED
  -> no automatic replay

SIGNED_AND_VERIFIED or RECOVERY_REQUIRED
  -> terminal; execute_once rejects
```

The journal lock is held across reservation, R9C execution and final commit. A competing process therefore cannot classify a live reservation as interrupted. Existing journal identity must match journal ID, ceremony ID, custody receipt hash, signature request hash and confirmation hash before any state transition.

## Persistence and privacy boundary

- Atomic file replacement reuses the Product writer, but its swallowed directory-fsync failure cannot prove reservation durability before signing.
- The target path and lock are caller-selected local Product state; canonical project binding is absent.
- `persistent_replay_prevention_present`, `canonical_project_binding_present`, `journal_deletion_detection_present`, `reservation_directory_durability_confirmed` and `power_loss_replay_prevention_confirmed` are fixed `false`; only `path_local_replay_prevention_present` is `true`.
- An alternate path or deletion can permit another signing attempt and is directly tested as an explicit noncanonical limitation.
- Final and recovery records contain hashes and fixed authority flags only. Private seed, public-key bytes and detached signature bytes never enter the journal.
- Within one retained path, a failed final replace leaves `SIGNING_RESERVED`; the next exact call converts it to `RECOVERY_REQUIRED` without signing again.
- Parent-directory trust is `COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY`. Hostile mutation, deletion, power loss and handle-race resistance are not claimed.

## Authority boundary

The journal authorizes one exact local R9C attempt already covered by explicit Human confirmation. It does not authorize key creation/import/export, signature export, Knowledge Pack write or promotion, automatic promotion, runtime Profile apply, rollback execution, Timeline/Resolve/provider/cloud effects, Release, Deploy or Production.

Real Owner key creation and real signing remain `NOT_EXECUTED` in this Unit. Tests use synthetic keys and a synthetic cipher only.

## Failure modes

| Failure | Required result |
|---|---|
| stale/tampered R8 request or inactive policy | reject before journal and custody access |
| current custody receipt drift | after successful reservation, mark `RECOVERY_REQUIRED` before signing |
| existing journal for another exact ceremony | conflict; do not mutate existing record |
| concurrent exact execution | serialize on journal lock |
| known exception after reservation | atomically mark `RECOVERY_REQUIRED` |
| process interruption after reservation | leave `SIGNING_RESERVED`; next call marks recovery and does not replay |
| final atomic replace failure | retain reservation; next call marks recovery and does not replay |
| receipt tamper, unknown field or symlink target | integrity failure |
| alternate path or externally deleted journal | another attempt is possible; receipt flags must not claim persistent prevention |
| fully forged typed success result | no public success callback exists; reject unexpected argument before reservation/key access |
| invalid completion-time type | reject before reservation or key access |

## Critic

Builder self-Critic findings resolved before the local gate:

- High: a different request could reuse the same path and mutate an interrupted reservation. Resolved by exact five-coordinate identity comparison before recovery transition.
- High: a stale request or policy mismatch is rejected before reservation. Current encrypted-custody drift is revalidated only after reservation succeeds so a reserve-write failure performs zero custody decrypt/key access; drift becomes terminal recovery before signing.
- High: releasing the journal lock during signing would let a concurrent caller misclassify a live reservation. Resolved by holding the cross-process lock through final commit.
- High: catching process-level interruption could falsely classify an unknown result as a known failure. Resolved by catching `Exception` only; `BaseException` leaves a durable reservation for later recovery.
- Medium: final write failure could tempt a retry. Resolved by preserving the reservation and requiring recovery.
- Medium: persisted bodies could expose key or signature material. Resolved by fixed hashes and false authority/body flags with schema and byte-level tests.

Independent DEV-4 review on head `a22fe41`: `NO-GO`, C/H/M/L=`0/3/2/0`. H1 alternate-path/deletion bypass and H3 unconfirmed directory durability are closed by explicit path-local downscope and fixed false claims. H2 arbitrary executor success is closed by exact concrete result types plus ceremony/custody/request/confirmation/receipt/completion/signature-verification cross-binding before final commit. M1 completion time is now positive-integer preflight. M2 direct negative fixtures cover alternate path/deletion, fake typed success, invalid completion time, corrupt/unknown/symlink state; independent re-review remains required.

Independent re-review on head `064f186`: `NO-GO`, C/H/M/L=`0/1/2/0`. The remaining High identified that public constructible typed receipts could still be injected through the success callback without cryptographic origin. Rework removes the success callback completely and directly calls trusted `execute_local_signing_ceremony`. The only test seam is a no-result after-reservation fault hook. A fully forged, coordinate-valid typed result fixture proves that no public injection parameter remains and fails before reservation/key access. Machine-readable path security flags and actual multiprocess, reserve-write failure, and all-five-coordinate conflict fixtures close the Medium requests. Third independent review is required.

Third independent review on `d32c019`: implementation authority C/H=`0/0` and Tester local GO, but Final Judge `NO-GO` for one test-harness Medium. The multiprocess fixture could leave live children on timeout/assertion. Rework adds a shared bounded cleanup helper that joins every started child, terminates survivors, joins again, kills any remaining survivor, performs a final bounded join and asserts all are dead. Queue close/join_thread is guaranteed in `finally`. A live-child fixture directly exercises the forced cleanup path. Fourth independent review is required.

## Local acceptance

- focused R9D state-machine, crash, conflict, atomic-failure, downscope, typed-cross-binding, schema and privacy tests: `20 PASS`;
- R8/R9A/R9B/R9C/R9D direct regression: `59 PASS`;
- TASK-029 regression: `121 PASS`;
- current unfiltered Product regression: `3954 PASS / 6 SKIP / 0 FAIL`;

- compile, schema mirror and exact6 diff/scope check: `PASS`.

## Judge

Current decision: `DRAFT_REVIEW_REQUIRED`. Three independent decisions were NO-GO; the third bounded rework is locally green but does not become GO until fourth independent review accepts the current head. Ready, merge and shared CHANGELOG integration remain prohibited. Shared lock order is TASK-054 closure, then a separate TASK-029 R9D transaction from fresh main.
