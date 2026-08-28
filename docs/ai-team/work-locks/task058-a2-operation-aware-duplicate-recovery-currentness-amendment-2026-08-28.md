# TASK-058 A2 Operation-Aware Duplicate Recovery Currentness Amendment

## Identity

- Evidence date: 2026-08-28
- Base main: `1e7f67a1dc6c56d345629c24e464c609fb36ea87`
- Registry preimage revision: `134`
- Registry candidate revision: `135`
- Active lock count before and after: `1`
- Lock ID: `BVP-INTEGRATION-LOCK-TASK058-A2-POST-MAIN-DIRECTORY-RACE-CORRECTIVE-CHANGELOG-20260828`
- Changed paths: the Registry plus this Evidence file only.

## Lifecycle audit and decision

The revision-134 lock does not contain an unconditional hosted-check-failure expiry.
Its exact expiry list is limited to target-head mismatch, a closed or merged target PR,
main or Registry drift before effect, new shared overlap, corrective source or test blob
drift, target branch collision or unauthorized push, forbidden effect or workflow-policy
violation, and completed integration with a recorded release.

PR 432 remains OPEN and Draft at exact head
`2e52f929408b121534e349d0ac521f03dce09a98`. The target head therefore matches and
the closed-or-merged condition is false. Hosted CI run `33129092469` finished 5 of 6
green with only Windows 3.13 failing. Security run `33129092432` finished 2 of 2 green.
Release metadata run `33129092420` failed as expected because the approved corrective
CHANGELOG line is not in the target. Unchanged-head retry count is zero.

The lock is therefore not silently released or treated as successful. This amendment
records the failed current hosted coordinate and a separately typed, Owner-approved
operation-aware recovery candidate. It does not replace the current expected target
head before canonical main read-back. The recovery updates the existing PR 432 branch;
creation of a new pull request is not authorized.

## Current target coordinate

- Target branch: `codex/task-058-p1ce-canonical-promotion-transaction-store`
- Current remote target head: `2e52f929408b121534e349d0ac521f03dce09a98`
- Current pull request: `432`
- Current PR state: `OPEN_DRAFT_HOSTED_CI_5_OF_6_WINDOWS_313_FAILED_RECOVERY_REQUIRED`
- Current corrective source blob: `c3f134c7460b7e9675dcc25c5ebd3ef1f3dc5615`
- Current corrective source SHA-256: `73efb3f3c644c4fa0e6e588e695301477fd45f643ae9beae3726b4cf077ccc40`
- Current corrective test blob: `5450d862a9cc94dbf062cd344f6fa160be9810ca`
- Current corrective test SHA-256: `08e574c571a6668e0804b4e91d3b0f23693bb32dfe3b221fab296fc6ac567389`
- First one-shot push: consumed, force-less, no retry.

## Approved recovery candidate

- Authority source: `OWNER_ESCALATION_OPERATION_AWARE_DUPLICATE_RECOVERY_UNIT_MAX2_20260828`
- Parent: `f2b779a864cb2072b5f9af08d703bc540f32fba3`
- Head: `795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`
- Verified ancestry: current remote `2e52f929...` -> `f2b779a...` -> `795093cf...`.
- Source path: `src/ai_video_production/montage_learning_canonical_admission_transaction.py`
- Source blob: `91eeabdf3e95081def272311d3fed6e910e915e4`
- Source SHA-256: `233d108dd7fe99278a133216933f3cabcb410ff691907152f6111c888fe5dab1`
- Test path: `tests/test_task058_montage_learning_canonical_admission_transaction.py`
- Test blob: `611a51e15c69aef154799e351b666f7d013f670a`
- Test SHA-256: `457a602e752fee78630bd4b6ce326fdaa5e17651b9e7f3c375445d35602f2a34`
- Exact changed path count: `2`
- Independent DEV-4: Critical/High/Medium/Low `0/0/0/0`, Technical GO.
- Independent tests: duplicate 3 pass; operation-aware positive and negative 7 pass;
  focused 76 pass with 5 platform skips; feasible direct 368 pass with 5 skips;
  same-writer and fresh-writer reproduction pass; pending recovery zero.
- Existing environment limitation: TASK-043 project-save-recovery collection is not
  confirmed because `referencing` is absent. No dependency was installed.
- Recovery pull request: existing PR `432` only.
- Pre-push expected head: `2e52f929408b121534e349d0ac521f03dce09a98`.
- Approved post-push expected head: `795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`.
- New pull-request creation authority: `false`.

## Phase-scoped target currentness

- Before revision-135 main read-back and the authorized push, PR 432 must remain OPEN
  and its exact head must remain `2e52f929...`.
- After the authorized one-shot push and before the second amendment, the only accepted
  transient coordinate is the same PR 432 at approved head `795093cf...`.
- Any other PR or head is `TARGET_HEAD_MISMATCH`; this phase rule prevents the approved
  same-PR transition itself from being treated as self-expiry.
- The second amendment must bind exact PR 432, head `795093cf...`, Hosted CI and
  Security results, and retry count zero. It must then make `795093cf...` the current
  expected head before any CHANGELOG effect or Ready decision.

## Canonical continuation order

1. Merge and read back this exact revision-135 amendment on canonical main.
2. Re-read main, Registry revision 135, active-lock identity, target branch, current
   remote head `2e52f929...`, branch and PR collision, exact recovery blobs, and overlap.
3. Obtain a separate exact Owner one-shot push Gate.
4. Push `795093cf...` to the target branch once, without force, rebase, or retry.
5. Read back existing PR 432 at updated head `795093cf...` and verify its exact two files;
   creation of a new PR is prohibited.
6. Require Hosted CI and Security terminal success on the unchanged head.
7. Host a second currentness amendment that binds exact PR 432, head `795093cf...`,
   Hosted checks, retry count zero, and current expected head before any CHANGELOG effect.
8. Only after that canonical read-back may the exact approved corrective CHANGELOG line
   be composed. Ready, merge, post-main verification, and append-only closure remain
   separate exact Gates.

## Authority and effect boundary

- Main read-back of this amendment does not push or mutate the target branch.
- Target merge authority remains NOT_GRANTED and its authority ID remains null.
- Integration effect remains reserved; CHANGELOG effect is zero in this Unit.
- The allowed shared effect remains exactly `CHANGELOG.md` for a later Gate.
- The approved CHANGELOG line is updated to describe both the directory first-use race
  correction and the operation-aware DUPLICATE recovery that the final exact two blobs
  must contain.
- No new admission, Exact ledger or anchor revision, public receipt meaning, Profile,
  automatic promotion, B+C connector activation, Timeline, Resolve, native/provider,
  network, paid, Release, Deploy, or Production authority is created.
- Automatic retry and automatic rollback or revert remain false.
- All existing expiry conditions, workflow policy, denied operations, shared ordering,
  and post-hosted second-amendment requirement remain active.
