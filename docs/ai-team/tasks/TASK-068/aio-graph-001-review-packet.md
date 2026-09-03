# AIO-GRAPH-001 immutable review packet

- Repository: BAI VIDEO PRODUCTION; branch `codex/task-068-aio-graph-001`.
- Canonical parent after rebase: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`.
- Status: local committed candidate; its current-main rebase had no conflict and
  the upstream four-commit delta touches TASK-036 docs only.
- Changed paths: TASK-068 task-local acceptance, `secure_authority_io.py`,
  `test_task068_secure_authority_io.py`, and this TASK-068 packet only.
- Diff check: PASS (line-ending warnings only).
- Source/test/task acceptance diff SHA-256: `b99842b790fc955867aae1f8a5546bb45f97ef8661da083df3e4ad72a2a7bf90`.

## Executed evidence

- Initial-lock focused including repeated two-contender stress, fresh-classifier
  fd-close/parent-close/both-close fault matrix, body-free completion-unknown,
  and unrelated sentinel identity/inventory preservation: `5 passed` for the
  final fault-focused selection.
- Full TASK-068 focused suites after M1/M2 correction: `174 passed, 84 skipped`;
  this source/test delta is unchanged by the non-overlapping current-main rebase.
- Current-main rebase readback: `174 passed, 84 skipped in 4.39s` on the
  rebased candidate; the four upstream commits touch TASK-036 documentation
  only and the rebase completed without conflict.
- Immutable graph verifier exception/effect-zero focused coverage: `3 passed`.
- The 84 skips are Windows-native authority-I/O cases on Linux and remain
  `NOT_CONFIRMED`, not PASS.

## Delta and open review scope

The delta adds a fresh read-only initial-lock loser classifier after native
destination-exists. Only a stable regular one-byte lock marker with retained
identity/security checks becomes collision; other observations become
completion-unknown and preserve data. The stress requires exact one winner and
one collision per run, preserved root identity, marker, and inventory. The M1
cleanup matrix proves that target-fd close, parent close, and combined failure
still attempt both closers, leave all captured handles unusable, burn the
loser's capability, and leave foreign marker/sentinel bytes, inode, and
inventory unchanged. The public error retains only
`LOCK_INITIALIZATION_UNKNOWN`, without primary or suppressed private details.

M2 is resolved: this packet is an explicit, committed TASK-068 changed path;
the diff hash above intentionally covers the stable source/test/task-acceptance
delta rather than recursively hashing this evidence packet.

## Independent final review

- Critic rereview: `C/H/M/L = 0/0/0/0`. Its local replay was
  `NOT_CONFIRMED` because that isolated reviewer environment lacks `jsonschema`;
  this did not replace the primary test evidence.
- Tester: Linux evidence `PASS`, `C/H/M = 0/0/0`; independently replayed the
  final close/classifier matrix (`5 passed`) and verifier-fault selection
  (`3 passed`).
- Judge: `ACCEPT` for this uncommitted local acceptance checkpoint, `C/H = 0/0`.

Known open item: Windows-native contention/fault execution remains
`NOT_CONFIRMED`. No secret values, artifact bodies, external effects, commit,
push, or PR are included.
