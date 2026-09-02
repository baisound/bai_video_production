# TASK-081 — Windows Atomic Lock Flush Regression Corrective

Date: 2026-09-02
Profile: `DEV-4 FOUNDATION CRITICAL`
State: `IMPLEMENTATION / VERIFICATION PENDING`
Canonical base: `6121ef2e9322501b391688998485918d10173f32`

## Objective

Correct the Windows Python 3.12 fresh-lock race observed in post-merge CI run
`33604510933`. Two spawned TASK-029 R9D consumers may both observe a new
zero-length sibling lock before either initializes it. The current
pre-acquisition buffered marker write can then target byte zero after the peer has
locked that byte and fail with `PermissionError`.

TASK-081 changes the common lock primitive without reopening historical
TASK-029 R9D or TASK-045 evidence. The journal consumer test is changed only
to synchronize initial contention; its exact-one-success contract is retained.

## Exact Allowed Files

1. `docs/ai-team/tasks/TASK-081/task.md`
2. `docs/ai-team/tasks/TASK-081/windows-atomic-lock-flush-regression-design.md`
3. `docs/ai-team/tasks/TASK-081/acceptance-negative-matrix.md`
4. `docs/ai-team/tasks/TASK-081/verification.md`
5. `src/ai_video_production/atomic.py`
6. `tests/test_atomic.py`
7. `tests/test_task029_knowledge_pack_durable_signing_journal.py`

No shared current-state, task-index, roadmap, CHANGELOG/version, TASK-080,
TASK-068, Montage, Release, Deploy, Production, native user-data, or other
source/test mutation is authorized.

## Acceptance

- Windows lock acquisition precedes the immediate raw marker write.
- A fresh zero-length lock serializes contenders and becomes exactly `b"0"`.
- An existing nonempty marker is never rewritten.
- Acquisition failure runs neither the protected body nor unlock.
- Marker initialization or protected-body failure releases the acquired lock
  and closes the handle.
- Nonregular and symlink lock paths fail before target effects.
- The synchronized TASK-029 spawned consumers produce exactly one success and
  one already-final result.
- Focused Windows, atomic, consumer and relevant regression evidence is fresh.
- Independent Tester, Critic and Judge report Critical/High `0/0` before the
  exact-seven commit.

The lock is cooperative coordination metadata. It does not select Product
currentness or create release, deployment, Production, provider, native, or
external-account authority.
