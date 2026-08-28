# TASK-058 A2 Accepted Recovery Currentness Amendment

## Identity

- Evidence date: 2026-08-28
- Base main: `2025c0fcbbbf492bae3cbadbd9aa47c1c048c14a`
- Registry preimage revision: `135`
- Registry candidate revision: `136`
- Registry lock count before and after: `9`
- Registry history count before and after: `64`
- Target active lock count before and after: `1`
- Lock ID: `BVP-INTEGRATION-LOCK-TASK058-A2-POST-MAIN-DIRECTORY-RACE-CORRECTIVE-CHANGELOG-20260828`
- Changed paths: the Registry plus this Evidence file only.

## Fresh currentness read-back

Canonical main and origin/main both identify
`2025c0fcbbbf492bae3cbadbd9aa47c1c048c14a`. Registry revision 135 contains one
matching active corrective lock. The amendment branch, Evidence path, remote branch,
and all-state pull-request lookup had no collision. Seventeen open pull requests were
read, and none changes either exact metadata path in this Unit.

Existing PR 432 remains OPEN, Draft, and MERGEABLE on branch
`codex/task-058-p1ce-canonical-promotion-transaction-store`. Its exact current head is
`795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`, and its changed paths remain the exact
source and test paths governed by this corrective lifecycle.

Hosted CI run `33135366027` completed 4 of 6 jobs successfully. Ubuntu 3.11, 3.12,
and 3.13 and Windows 3.13 passed. Windows 3.11 and 3.12 failed the same accepted
recovery convergence case. Security run `33135366068` completed 2 of 2 successfully.
Release metadata run `33135366019` failed as expected because the separately approved
corrective CHANGELOG line has not been integrated. Unchanged-head retry count is zero.

## Lifecycle audit and decision

The revision-135 expiry list has no unconditional hosted-check-failure condition.
PR 432 is not closed or merged, its current head is exactly the phase-approved
`795093cf...`, the exact source and test paths remain stable, and there is no shared
metadata overlap. The lock is therefore still nonterminal and may carry one separately
typed Owner-approved recovery head without ignoring an expiry guard.

The prior one-shot update to `795093cf...` is consumed and cannot be retried. This
amendment keeps PR 432 and head `795093cf...` as the current target until revision 136
is merged and read back from canonical main. It records `aa0f63e...` only as the next
approved same-PR update. It creates no pull request and grants no target merge authority.

## Approved accepted-recovery candidate

- Authority source: `OWNER_BOUNDED_CORRECTIVE_UNIT_PR432_HOSTED_ACCEPTED_RECOVERY_H1_20260828`
- Parent: `795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`
- Head: `aa0f63ec1bb41595c1bbc70dd863d278b9041fa5`
- Verified ancestry: `795093cf...` is the direct parent of `aa0f63e...`.
- Source path: `src/ai_video_production/montage_learning_canonical_admission_transaction.py`
- Source Git blob: `165c095684a71f29a3593baed063880fb0ef35cd`
- Source SHA-256: `6e6514f904d726c6319eb1e0736262fb606ed0a2a498ce0613fef79bcd567e8f`
- Test path: `tests/test_task058_montage_learning_canonical_admission_transaction.py`
- Test Git blob: `6a08ee752ba0646d7eea0eb5764cfd97f73f52f3`
- Test SHA-256: `7e6854e442af4d175090a867472df5a3acdea9498d44e0fd15ebb8d178c44c31`
- Exact changed path count: `2`
- Independent DEV-4: Critical/High/Medium/Low `0/0/0/0`, Technical GO.

Independent WSL execution used a fresh process, disabled bytecode and pytest cache,
and installed no dependency. The new operation, atomicity, and negative selection
passed 7 tests. The focused file passed 83 tests with 5 Windows-only skips. The feasible
TASK-043, TASK-055, and TASK-058 direct set passed 375 tests with the same 5 skips.
Compilation passed. Pre-test and post-test HEAD, clean state, Git blobs, and SHA-256
coordinates were unchanged.

Windows-only HANDLE and junction fixtures are not confirmed because a local Windows
pytest runtime was unavailable. One TASK-043 file is also not confirmed because the
existing WSL environment lacks `referencing`. Neither limitation is recorded as PASS.
The next exact Hosted run must provide the Windows and full-matrix evidence.

## Phase-scoped target currentness

- Before revision-136 main read-back, PR 432 must remain OPEN and Draft at exact head
  `795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`.
- After revision-136 main read-back and an exact Owner one-shot push Gate, the only
  accepted transient update is the same PR 432 at exact head
  `aa0f63ec1bb41595c1bbc70dd863d278b9041fa5`.
- New pull-request creation is false. A different PR, branch, or head is
  `TARGET_HEAD_MISMATCH`.
- The one-shot update is force-less, has no retry, and requires `795093cf...` to remain
  the direct parent of `aa0f63e...`.
- After the update, a second currentness amendment must bind exact PR 432, head
  `aa0f63e...`, Hosted CI and Security results, and retry count zero. That amendment
  must make `aa0f63e...` the current expected head before CHANGELOG or Ready activity.

## Protected-field equality

The following authority and lifecycle controls are byte-for-byte unchanged from
revision 135: activation scope, target merge authority and null authority ID, allowed
shared file list, denied operations, controlled shared paths, merge order, successor
reservation, prerequisites, expiry conditions, release condition, workflow policy,
composition rule, roadmap delta, post-integration null coordinate, automatic retry,
and automatic rollback or revert.

The approved shared scope remains exactly one later `CHANGELOG.md` effect. No CHANGELOG
content is changed in this Unit. No admission, Product Project data, Exact or Generic
ledger, anchor, receipt, Profile, B+C connector, Timeline, Resolve, native/provider,
network, paid, Release, Deploy, or Production effect is authorized or performed.

## Canonical continuation order

1. Review this exact revision-136 two-file candidate under independent DEV-4.
2. Host it on a Draft pull request and require all metadata checks to pass.
3. Obtain a separate exact Owner merge Gate, merge it normally, and read Registry
   revision 136 from canonical main.
4. Re-read PR 432 as OPEN and Draft at exact head `795093cf...`, recheck branch and PR
   collisions, exact source and test coordinates, ancestry, and shared overlap.
5. Obtain a separate exact Owner one-shot Gate and push `aa0f63e...` to the existing
   PR 432 branch once, without force, rebase, or retry. Create no new pull request.
6. Read back PR 432 at exact head `aa0f63e...` and require Hosted CI and Security to
   complete on that unchanged head. Classify any failure without same-head retry.
7. Host and merge a second currentness amendment that binds exact PR 432, head
   `aa0f63e...`, Hosted checks, retry count zero, and current expected head.
8. Only after that canonical read-back may the exact approved corrective CHANGELOG
   line be composed. Ready, merge, post-main verification, and append-only closure
   remain separate exact Gates.
