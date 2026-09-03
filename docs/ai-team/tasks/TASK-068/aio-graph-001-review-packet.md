# AIO-GRAPH-001 immutable review packet

- Repository: BAI VIDEO PRODUCTION; branch `codex/task-068-aio-graph-001`.
- Canonical parent after rebase: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`.
- Status: Recovery after hosted Windows failure on prior candidate `e34093b`;
  the current corrective successor is uncommitted.
- Changed paths: TASK-068 task-local acceptance, `secure_authority_io.py`,
  `test_task068_secure_authority_io.py`,
  `test_task068_secure_authority_io_windows.py`, and this TASK-068 packet only.
- Diff check: PASS (line-ending warnings only).
- Recovery source/test/task acceptance diff SHA-256:
  `92cd60f6e72ec84a4967b577192e7e780a0023dcabe7d308c29799106ca72d53`
  from `git diff --no-ext-diff e34093b --` over `secure_authority_io.py`, both
  focused TASK-068 test files, and TASK-068 `task.md`.

## Executed evidence

- Initial-lock focused including repeated two-contender stress, fresh-classifier
  fd-close/parent-close/both-close fault matrix, body-free completion-unknown,
  and unrelated sentinel identity/inventory preservation: `5 passed` for the
  final fault-focused selection.
- Full TASK-068 focused suites after Windows-recovery correction: `174 passed,
  85 skipped in 3.68s`; the extra skip is the new Windows-only locked-target
  negative and remains `NOT_CONFIRMED` locally.
- Current-main rebase readback on the prior candidate: `174 passed, 84 skipped in 4.39s` on the
  rebased candidate; the four upstream commits touch TASK-036 documentation
  only and the rebase completed without conflict.
- Immutable graph verifier exception/effect-zero focused coverage: `3 passed`.
- All 85 skips are Windows-native authority-I/O cases on Linux and remain
  `NOT_CONFIRMED`, not PASS: the prior 84 plus the new locked-competitor
  negative.

## Delta and open review scope

The delta adds a fresh read-only initial-lock loser classifier after native
destination-exists. Only a stable regular foreign target or one-byte live lock
winner with retained identity/security checks becomes collision; other
observations become completion-unknown and preserve data. The stress requires
exact one winner and one collision per run, preserved root identity, marker,
and inventory. The M1
cleanup matrix proves that target-fd close, parent close, and combined failure
still attempt both closers, leave all captured handles unusable, burn the
loser's capability, and leave foreign marker/sentinel bytes, inode, and
inventory unchanged. The public error retains only
`LOCK_INITIALIZATION_UNKNOWN`, without primary or suppressed private details.

M2 is resolved: this packet is an explicit TASK-068 changed path in the pending
Recovery successor; the diff hash above intentionally covers the stable
source/test/task-acceptance delta rather than recursively hashing this evidence
packet.

## Hosted-failure recovery

PR #514 hosted Windows 3.11/3.12/3.13 established two prior acceptance failures:
the two-contender stress returned one `WINNER` plus
`LOCK_INITIALIZATION_UNKNOWN`, and the Windows foreign-competitor test returned
`LOCK_INITIALIZATION_UNKNOWN` instead of `LOCK_CREATE_COLLISION`.  Linux and
Security jobs remained green, but the former local acceptance is invalidated.

The root cause is Windows share-mode symmetry.  A winner retains a write-capable
handle, while the loser's fresh read-only classifier opened the same target
without write sharing and therefore received a sharing violation.  Recovery
keeps the observation read-only but enables write sharing.  It confirms native
collision, live source identity, fresh regular target identity, repeated target
and namespace-security observation, and pinned ancestors.  No target bytes are
read: a stable arbitrary foreign file or stable live winner is a collision;
sharing-blocked, swapped, drifted, or close-ambiguous observations remain
completion-unknown and preserve data.

Local Windows execution was checked without installation: this worktree has no
test venv, and the available Windows Python runtimes lack the declared
`jsonschema` dependency.  Hosted Windows jobs are therefore the required
successor reproduction route.

## Superseded prior review

- Prior Critic rereview: `C/H/M/L = 0/0/0/0`. Its local replay was
  `NOT_CONFIRMED` because that isolated reviewer environment lacks `jsonschema`;
  this did not replace the primary test evidence.
- Prior Tester: Linux evidence `PASS`, `C/H/M = 0/0/0`; independently replayed the
  final close/classifier matrix (`5 passed`) and verifier-fault selection
  (`3 passed`).
- Prior Judge: `ACCEPT` for the prior local acceptance checkpoint, `C/H = 0/0`.
  All three results are superseded by the hosted Windows failure and must be
  re-established for this Recovery successor.

## Recovery successor review

- Critic: `C/H/M/L = 0/0/0/0`; the scoped recovery hash and all five changed
  paths were independently rechecked.
- Tester: static `PASS`, `C/H = 0/0`; the available local Windows Python has no
  `jsonschema`, so native collection remains `NOT_CONFIRMED` without install.
- Judge: `ACCEPT`, `C/H = 0/0`; the successor is authorized for non-force PR
  update and hosted Windows rerun only.

Known open item: Windows-native contention/fault execution must pass on the
successor hosted jobs. No secret values, artifact bodies, external effects,
commit, push, or PR are included in this Recovery checkpoint.
