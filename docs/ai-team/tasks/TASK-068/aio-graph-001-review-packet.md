# AIO-GRAPH-001 immutable review packet

- Repository: BAI VIDEO PRODUCTION; branch `codex/task-068-aio-graph-001`.
- Canonical parent after rebase: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`.
- Status: Recovery R2 after hosted Windows 3.11/3.12/3.13 failure on
  `ff7d1f03e77bd86a9f20a21e80c5d868d397b625`; the current corrective
  successor is uncommitted.
- Changed paths in R2: `secure_authority_io.py`,
  `test_task068_secure_authority_io_windows.py`, and this TASK-068 packet only.
- Diff check: PASS (line-ending warnings only).
- Recovery source/test/task acceptance diff SHA-256:
  `92cd60f6e72ec84a4967b577192e7e780a0023dcabe7d308c29799106ca72d53`
  from `git diff --no-ext-diff e34093b --` over `secure_authority_io.py`, both
  focused TASK-068 test files, and TASK-068 `task.md`.
- R2 source/test textual diff SHA-256:
  `452b95c5729fef96e4371c9e10b91040fa5445d644d8bb1dd5a3babea0c118ed`
  from the current `git diff --no-ext-diff --` over the two R2 source/test
  paths. The packet is deliberately excluded from that scoped hash.

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

## Hosted Windows R2 recovery

All three hosted Windows variants failed the same exact assertion in
`test_initial_lock_contention_has_one_winner_and_one_stable_loser_per_run`:
the two outcomes were `WINNER` and `LOCK_INITIALIZATION_UNKNOWN`, with no
`LOCK_CREATE_COLLISION`. Ubuntu 3.11/3.12/3.13 and Security checks passed.

The remaining root cause is the other half of Windows share-mode symmetry. The
live winner has `DELETE` access because its operation-owned temporary handle
must support handle-bound cleanup. The fresh read-only classifier already
shares write access, but must also share that existing `DELETE` access before
Windows permits its read open. R2 adds a default-deny `share_delete` parameter
to the Windows open adapter and forwards it through the private target opener.
Only the fresh read-only initial-lock classifier opts in; it never receives
delete access. Authority-bearing writer opens and pinned ancestors retain
default delete-sharing denial, so a third party cannot obtain delete access
while the live winner remains open.

The added Windows-native regression creates and holds the exact live winner
handle (`create_new`, writable, delete-capable, write-shared), then requires a
body-free `LOCK_CREATE_COLLISION`, unchanged marker bytes, and no temporary
residue. Existing sharing-blocked observation coverage still requires
`LOCK_INITIALIZATION_UNKNOWN` and preservation. Local syntax/compileall and
`git diff --check` pass. WSL was unavailable after restart (`E_ACCESS_DENIED`);
the available local Windows Python still lacks `jsonschema` at collection, and
no dependency installation was performed.

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

## Recovery R2 review

- Critic: `C/H/M/L = 0/0/0/0`; the read-only share-delete exception is isolated
  to the fresh classifier and retains all identity/security/ancestor checks.
- Tester: static `PASS`, `C/H = 0/0`; the native live-winner regression and
  existing sharing-blocked negative cover the positive and fail-closed paths.
- Judge: `ACCEPT`, `C/H = 0/0`; hosted Windows remains the required final gate.

Open item: commit/push is deferred until this R2 checkpoint is reviewed for
scope and a current Owner-authorized PR update path is reconfirmed. Hosted
Windows must pass before TASK-068 completion can be claimed.
