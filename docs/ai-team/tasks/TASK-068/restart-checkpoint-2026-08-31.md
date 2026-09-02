# TASK-068 restart checkpoint (2026-08-31)

## Bind

- Repository: `baisound/bai_video_production`
- Worktree: `TASK-068 dedicated worktree (historical checkpoint label)`
- Branch: `codex/task-068-secure-authority-io`
- HEAD/base: `35cdf1ad475633dcf035e0616e979b5a8fde0c88`
- Development depth: `DEV-4`
- Authority: TASK-068 Allowed Files only; shared documents, release, install, deploy, Production Activation, and native real-data effects remain prohibited.

## Dirty ownership and preservation

All listed paths are TASK-068 Builder-owned partial work and must be preserved exactly. Do not reset, discard, clean, or overwrite them.

- staged additions: `docs/ai-team/tasks/TASK-068/design.md`, `negative-matrix.md`, `task.md`
- staged plus later unstaged edits: `docs/ai-team/tasks/TASK-068/verification.md`, `src/ai_video_production/secure_authority_io.py`, `tests/test_task068_secure_authority_io.py`, `tests/test_task068_secure_authority_io_windows.py`
- untracked task-local evidence: `docs/ai-team/tasks/TASK-068/review.md`, this checkpoint

## Completed minimum work

- Built the initial secure authority I/O module and focused POSIX/Windows test surfaces.
- Added pinned read/strict JSON/lock/publish/CAS/cleanup foundations and began the independent Critic P0 correction.
- Introduced live temp leases, handle-bound/native publish and delete helpers, required writer leases, immutable-read direction, bounded writer validation, Windows component restrictions, and initial-lock rollback/durability handling.
- Completed the bounded Windows handle-rename correction and retained the live source handle through final readback. Added native race/fault coverage for target reparse/hardlink rejection, case-insensitive initial-lock collision, temp-bind failure, rollback durability ambiguity, and post-delete close ambiguity.
- Added hard caller/path ceilings, exact late-collision classification, untransferred ancestor-fd cleanup, lock/read close-failure handling, and body-free completion-unknown classification after namespace effects.

## Verification state

- Current Python syntax compilation on Windows bundled runtime: PASS.
- Current WSL focused suite: `88 passed`, `23 skipped`; every skip is Windows-native.
- Current Windows-native test functions, executed unchanged through the dependency-free runner: `23 passed`, `0 skipped`.
- Current `git diff --check`: PASS.
- Full repository collection is `NOT_CONFIRMED` because the WSL cryptography build lacks Argon2id. A collection-compatible broader run recorded `4320 passed`, `43 skipped`, and 9 unrelated environment failures (2 Argon2id imports, 7 Windows PowerShell exec-format failures); TASK-068 failures were zero.
- Independent DEV-4 rereview remains unexecuted.

## Active dependencies and gates

- Independent Critic P0 COMMIT STOP remains active. P0-2 atomic identity-conditional mutable CAS and POSIX P0-3 exact handle-bound cleanup remain safely effect0-parked acceptance blockers; independent DEV-4 rereview has not re-established C/H=0.
- No commit, push, or PR until focused negative coverage is complete and independent DEV-4 Critic/Tester/Judge records Critical/High = 0.
- TASK-069 source/schema/test mutation remains START0 until TASK-068 canonical completion receipt.
- Owner restart gate was released by the explicit resume instruction; no other Authority or Human Gate was waived.

## First reads after restart

1. `AGENTS.md`
2. `docs/ai-team/tasks/TASK-068/restart-checkpoint-2026-08-31.md`
3. `docs/ai-team/tasks/TASK-068/review.md`
4. exact ranges around `replace_json_cas`, `_unlink_live_name`, and `cleanup_owned_file` in `src/ai_video_production/secure_authority_io.py`
5. P0-2/P0-3 rows in `docs/ai-team/tasks/TASK-068/negative-matrix.md`

## First action after explicit resume

Fresh-bind repository/HEAD/branch/status/overlap first. Then confirm whether an approved platform primitive/design change can close P0-2/P0-3 without pathname TOCTOU or foreign-object effects. If not, retain the explicit effect0 park and do not claim acceptance; obtain independent DEV-4 rereview before any commit.

## Resume readback

- Owner explicit resume received on 2026-08-31.
- Canonical remote `main` remains `35cdf1ad475633dcf035e0616e979b5a8fde0c88`; TASK-068 HEAD/base matches it.
- Upstream overlap on TASK-068 Allowed Files: none.
- Current focused evidence: POSIX/WSL `88 passed`, Windows-only collection `23 skipped`; Windows-native existing test functions `23 passed`, `0 skipped` through an in-memory dependency-free runner.
- `COMMIT STOP` remains active; resume did not waive independent DEV-4 C/H=0 or the CAS/POSIX-cleanup acceptance blockers.

## Queued TASK-069 acceptance delta (source START0)

- TASK-069 source/schema/test mutation remains prohibited until TASK-068 canonical completion.
- Its task-local acceptance must add a Windows-native directory-durability port: file content flush, rename publication durability, and parent-directory/mkdir durability are separate contracts.
- Unsupported/unknown/durability failure must be fail-closed with receipt zero. Temp/write/fsync/publish/parent-durability fault seams must preserve foreign targets, foreign temps, unrelated artifacts, and operation-owned recoverable state.
- Linux directory-fsync evidence must never be reused as Windows Production evidence.

## Post-resume checkpoint

- Fresh GitHub main bind remains `35cdf1ad475633dcf035e0616e979b5a8fde0c88`; TASK-068 remote branch/PR overlap remains zero.
- Closed after resume: Windows final-symlink publication escape, POSIX writer-lease root rebinding, and Windows late-hardlink cleanup. Independent rereview found no new regression.
- Current focused WSL result: `89 passed`, `25 skipped` (all Windows-native). Windows bundled-Python syntax is PASS. The bundled Windows runtime has no pytest, so no install was attempted.
- Independent Tester rebound source SHA-256 `A0F37468C35325D976366D504AA480489A0A5F0C9A66686D487FB5FB101FA6CF`, repeated `89 passed / 25 skipped`, and ran all 25 Windows-native focused functions unchanged with isolated temporary roots and an in-memory dependency-free shim: `25 passed / 0 skipped / 0 failed`. Git state and source hash remained unchanged.
- Current independent Critical/High: `0/2`. P0-2 identity-conditional mutable CAS and POSIX P0-3 exact handle-bound cleanup remain unimplemented, safely effect-zero, and acceptance-blocking.
- Linux `renameat2` exposes replace/no-replace/exchange but no expected-inode predicate; `unlinkat` remains pathname-conditioned. Windows rename exposes replace/no-replace against a destination name but no expected-target-identity predicate. Therefore the current nontransactional ports cannot safely close the two remaining requirements without a contract/architecture change.
- Independent post-restart Architecture/Critic rereview reached the same conclusion after checking exchange, advisory writer lease, versioned immutable, Windows non-TxF rename, and TxF directions. Exchange detects a mismatch only after moving the foreign target, advisory locks do not bind non-cooperating writers, and TxF is NTFS-local/deprecated-direction and cannot satisfy the cross-platform contract. Exact resume condition for P0-2/P0-3 is an Owner-approved design change that either changes the fixed-path/uncooperative-writer requirement or supplies a proven platform-specific transaction primitive with equivalent negatives.
- `COMMIT STOP`, TASK-069 `START0`, shared-write prohibition, and all Release/Deploy/Production/native gates remain active.
