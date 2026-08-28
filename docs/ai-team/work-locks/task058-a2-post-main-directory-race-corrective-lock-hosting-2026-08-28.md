# TASK-058 A2 Post-Main Directory Race Corrective Lock Hosting

Date: 2026-08-28
Unit: TASK-058/A2-POST-MAIN-DIRECTORY-RACE-CORRECTIVE-LOCK-HOSTING
Authority: OWNER_EXACT_OLD_LOCK_FAILURE_CLOSURE_AND_NEW_CORRECTIVE_LOCK_HOST_GATE_20260828
Status: LOCAL_CANDIDATE_NOT_HOSTED

## Atomic Registry transition

- canonical base main: `829e7de18a9b99446f270465c190e22233e1faef`
- Registry revision: `133 -> 134`
- old active lock moves to append-only history as `HOSTED_TARGET_AND_CHANGELOG_EFFECT_CONSUMED_POST_MAIN_FAILED_RECOVERY_REQUIRED`
- old PR #417 merged exact head `ce174bc3f90c1d89ac47f8ef5dacdabe1a22f89d` at main `829e7de18a9b99446f270465c190e22233e1faef`
- old post-main CI run `33123723593` remains four of six PASS with Ubuntu Python 3.12 and 3.13 directory first-use race failures
- old post-main Security run `33123723623` remains two of two PASS
- old PR #417 exact six target blobs and its approved CHANGELOG bullet were merged and consumed as an exact seven-path target effect
- post-main verification failed, so implementation release is not final and corrective recovery is required; retry and rollback remain false
- the replacement corrective lock is the only active nonclosed lock

## New corrective coordinates

- lock: `BVP-INTEGRATION-LOCK-TASK058-A2-POST-MAIN-DIRECTORY-RACE-CORRECTIVE-CHANGELOG-20260828`
- superseded lock: `BVP-INTEGRATION-LOCK-TASK058-A2-CANONICAL-READBACK-LOOKUP-CHANGELOG-20260828`
- hosting branch: `codex/task-058-a2-post-main-directory-race-corrective-lock-hosting`
- target branch: `codex/task-058-p1ce-canonical-promotion-transaction-store`
- future target PR: `null`
- exact corrective head: `2e52f929408b121534e349d0ac521f03dce09a98`
- direct parent: `f43015752863f60130d40b8dc6d7dec438395bc5`
- source blob: `c3f134c7460b7e9675dcc25c5ebd3ef1f3dc5615`
- source SHA-256: `73efb3f3c644c4fa0e6e588e695301477fd45f643ae9beae3726b4cf077ccc40`
- test blob: `5450d862a9cc94dbf062cd344f6fa160be9810ca`
- test SHA-256: `08e574c571a6668e0804b4e91d3b0f23693bb32dfe3b221fab296fc6ac567389`

The replacement lock freezes one separate corrective CHANGELOG bullet in the
Registry `approved_changelog_bullet` field. It is not a replay or relabel of
the already-consumed PR #417 bullet.

Builder Evidence remains unpromoted: directory safety and race 14 PASS;
focused 69 PASS with 5 platform skips; TASK-043/TASK-055/TASK-058 direct
292 PASS; compile, diff and exact-scope PASS. WSL full is NOT_CONFIRMED
because `referencing` is unavailable and Windows is NOT_EXECUTED. Independent
DEV-4 final review remains PENDING.

## Authority and effect boundary

- corrective implementation authority is limited to the exact source and test paths above
- allowed shared effect remains exactly `CHANGELOG.md`; only the separate corrective bullet above is authorized after every prerequisite is met
- target Ready and merge authority are not granted and their identifiers are null
- `TARGET_HEAD_MISMATCH` and `TARGET_PR_CLOSED_OR_MERGED` apply only after revision 134 main read-back, the one-shot target push and future PR binding; target branch collision applies before push
- no new admission, revision advance, public receipt, Profile meaning, B+C, Timeline, Resolve, runtime, native, Release, Deploy or Production effect is granted
- no force, rebase, unchanged-head retry, automatic retry or rollback is authorized

## Continuation order

1. Independently review the exact corrective source and test candidate to C/H zero.
2. Host and merge this exact2 lock transition under separate exact gates.
3. Read Registry revision 134 and the single replacement lock from canonical main.
4. Under a separate exact Owner gate, perform one force-free, no-retry push of the exact corrective head to the target branch.
5. Create and read back the future corrective PR identity and exact head.
6. Require all Hosted checks, then bind the exact remote head, PR and checks through a second canonical currentness amendment; `post_integration_head` remains `null` until the later main merge plus corrective CHANGELOG commit exists.
7. Only after a separate Owner gate may Ready, merge or the exact new corrective CHANGELOG effect be evaluated.
8. Require post-main CI and Security success, then append-only close the replacement lock.

Any branch collision, head or blob mismatch, Registry drift, failed review,
failed Hosted check, overlap or forbidden effect fails closed.
