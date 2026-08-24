# TASK-057 R0 Snapshot Lock Race — Design / Critic / Judge

## Incident evidence

- source PR: #293 (docs-only TASK-019 lock proposal)
- failed run/job: CI 32729880844 / Windows 3.12 job 97439478849
- failed test: `test_concurrent_go_publication_allows_exactly_one_writer`
- exception: `PermissionError [Errno 13]` at empty lock file `handle.flush()`
- other hosted jobs: 8 / 9 PASS
- product/source overlap with PR #293: zero

## Design decision

Move the existing empty-file byte initialization after the existing platform OS lock is acquired. Windows `msvcrt.locking` was probed on an empty temporary file and returned PASS; therefore the initialization itself can be serialized without a second lock primitive or retry loop.

## Negative / recovery matrix

- 8 simultaneous first callers on one empty lock
- 8 repeated fresh lock races with four callers
- mutual exclusion peak remains exactly one
- lock byte is exactly `b"0"`
- existing concurrent GO publication regression
- existing TASK-037 store regressions
- no unchanged-head CI rerun used as recovery

## Critic

Finding: adding retry around `flush()` would mask an ordering defect and introduce timing-dependent authority.

Correction: acquire the already-canonical OS lock before the only initialization write. No retry, sleep, alternate lock or fallback is added.

Residual C/H/M: `0/0/0`.

## Judge

- exact root cause addressed: PASS
- Windows/POSIX lock semantics preserved: PASS
- CAS/atomic/symlink boundaries unchanged: PASS
- focused stress/exact failure/TASK-037 regression: 12 PASS
- full local regression: 3657 PASS / 5 SKIP / 0 FAIL
- compile/diff check: PASS
- hosted regression: PENDING EVIDENCE
- residual C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
