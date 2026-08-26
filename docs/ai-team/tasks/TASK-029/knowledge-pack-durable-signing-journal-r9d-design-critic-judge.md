# TASK-029 R9D Durable Signing Ceremony Journal — Design, Critic and Judge

Date: 2026-08-26
Profile: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
State: LOCAL IMPLEMENTATION COMPLETE / INDEPENDENT REVIEW PENDING

## Atomic Unit

R9D closes only the durable replay gap explicitly left by R9C. It stores a body-free, checksum-bound journal reservation before the R9C signing boundary and commits only receipt hashes after immediate R9A verification.

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

- Atomic JSON replace and directory durability reuse the Product atomic writer.
- The target path and lock are caller-supplied local Product state.
- Final and recovery records contain hashes and fixed authority flags only.
- Private seed, public-key bytes and detached signature bytes never enter the journal.
- A failed final replace leaves `SIGNING_RESERVED`; the next exact call converts it to `RECOVERY_REQUIRED` without signing again.
- Parent-directory trust is `COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY`. Hostile parent replacement or handle-race resistance is not claimed and remains a later platform-hardening concern.

## Authority boundary

The journal authorizes one exact local R9C attempt already covered by explicit Human confirmation. It does not authorize key creation/import/export, signature export, Knowledge Pack write or promotion, automatic promotion, runtime Profile apply, rollback execution, Timeline/Resolve/provider/cloud effects, Release, Deploy or Production.

Real Owner key creation and real signing remain `NOT_EXECUTED` in this Unit. Tests use synthetic keys and a synthetic cipher only.

## Failure modes

| Failure | Required result |
|---|---|
| stale/tampered R8 request or inactive policy | reject before journal and custody access |
| current custody receipt drift | reject before reservation |
| existing journal for another exact ceremony | conflict; do not mutate existing record |
| concurrent exact execution | serialize on journal lock |
| known exception after reservation | atomically mark `RECOVERY_REQUIRED` |
| process interruption after reservation | leave `SIGNING_RESERVED`; next call marks recovery and does not replay |
| final atomic replace failure | retain reservation; next call marks recovery and does not replay |
| receipt tamper, unknown field or symlink target | integrity failure |

## Critic

Builder self-Critic findings resolved before the local gate:

- High: a different request could reuse the same path and mutate an interrupted reservation. Resolved by exact five-coordinate identity comparison before recovery transition.
- High: a known custody/policy mismatch could poison a journal before any signing possibility. Resolved by request/policy/custody identity preflight before reservation while retaining R9C revalidation before signing.
- High: releasing the journal lock during signing would let a concurrent caller misclassify a live reservation. Resolved by holding the cross-process lock through final commit.
- High: catching process-level interruption could falsely classify an unknown result as a known failure. Resolved by catching `Exception` only; `BaseException` leaves a durable reservation for later recovery.
- Medium: final write failure could tempt a retry. Resolved by preserving the reservation and requiring recovery.
- Medium: persisted bodies could expose key or signature material. Resolved by fixed hashes and false authority/body flags with schema and byte-level tests.

Independent Critic/Tester/Judge: `PENDING` before PR Ready/merge. This document does not mislabel the Builder self-review as independent evidence.

## Local acceptance

- focused R9D state-machine, crash, conflict, atomic-failure, schema and privacy tests: `9 PASS`;
- R8/R9A/R9B/R9C/R9D direct regression: `42 PASS`;
- TASK-029 regression: `110 PASS`;
- current broad Product regression excluding the exact low-disk-gated TASK-036 test: `3914 PASS / 6 SKIP / 1 DESELECT`;
- unfiltered Product run: `3913 PASS / 6 SKIP / 1 FAIL`; the sole failure was `ERR_RESOURCE_LOCAL_DISK_LOW` from the unrelated TASK-036 native image CLI with actual C-drive free space `8.78 GiB`, so the unfiltered technical result remains `NOT_CONFIRMED` without deleting Owner data;
- compile, schema mirror and exact6 diff/scope check: `PASS`.

## Judge

Current decision: `DRAFT_SOURCE_CONTINUE`. Merge and shared CHANGELOG integration remain prohibited until required tests and independent DEV-4 review are complete. Shared lock order is TASK-058 P1B closure, TASK-054, then a separate TASK-029 R9D transaction from fresh main.
