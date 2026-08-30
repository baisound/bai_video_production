# TASK-058 A2 Atomic Recovery Carrier Evidence

## Authority and objective

- Evidence date: 2026-08-28
- Owner Gate: `REV136_ATOMIC_RECOVERY_CARRIER`
- Carrier mode: `ATOMIC_RECOVERY_CARRIER_TWO_COMMIT_V1`
- Canonical base main: `2025c0fcbbbf492bae3cbadbd9aa47c1c048c14a`
- Pull request: `434`
- Target branch: `codex/task-058-a2-accepted-recovery-currentness-amendment`
- Pre-update remote head: `19831a43e9f548f070d8dc45ca92b17ab5956d79`
- Registry revision: `135 -> 136`
- Registry locks: `9 -> 9`
- Registry integration history: `64 -> 64`
- Matching active TASK-058 corrective lock: `1 -> 1`

PR 434 previously carried only the Registry and this Evidence. Its Hosted CI run
`33138614278` passed five of six jobs and failed Windows 3.13 with the canonical
TASK-058 A2 directory-initialization race. Security run `33138614238` passed two of
two checks. Release metadata run `33138614209` passed. Retry count is zero.

The Owner approved one atomic carrier so that the corrected source, its exact test,
the already approved corrective CHANGELOG bullet, and the Registry transition reach
main through one pull request. This Unit does not authorize a retry or merge of PR 432.

## Failed predecessor

- Pull request: `432`
- Branch: `codex/task-058-p1ce-canonical-promotion-transaction-store`
- Head: `795093cf2c7e9a35bd67b87ff6aa16a4abcd263d`
- Hosted CI: `33135366027`, four of six passed
- Security: `33135366068`, two of two passed
- Release metadata: `33135366019`, expected failure before CHANGELOG integration
- State: `FAILED_PREDECESSOR_NO_FURTHER_PUSH_OR_MERGE`

The previously planned PR 432 update to `aa0f63e...` is superseded and not authorized.
PR 432 remains historical failure evidence only.

## Two-commit topology

The carrier avoids an impossible commit self-reference by using two local commits.

### Payload commit C

- Parent: `19831a43e9f548f070d8dc45ca92b17ab5956d79`
- Head: `b9ce90c16c60cb8476c2be13f2142f72d0775556`
- Exact changed paths: `3`
- Intermediate push authorized: `false`

The exact payload paths are:

1. `CHANGELOG.md`
2. `src/ai_video_production/montage_learning_canonical_admission_transaction.py`
3. `tests/test_task058_montage_learning_canonical_admission_transaction.py`

The source and test Git blobs are byte-identical to approved recovery head
`aa0f63ec1bb41595c1bbc70dd863d278b9041fa5`. The CHANGELOG contains the exact
`approved_changelog_bullet` from the active Registry record exactly once.

### Metadata wrapper commit M

- Parent: exact payload commit C
- Exact changed paths: `2`
- Paths: `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json` and this Evidence
- Head value stored inside M: `null`
- Head state: `EXTERNAL_EXACT_PR_HEAD_REQUIRED`

The final M SHA cannot be stored inside M without a circular dependency. Its exact
SHA is frozen externally by independent DEV-4 review, Hosted checks, and the Owner
Ready and merge Gate. C and M must be complete before a single force-less branch push.

## Payload coordinates

All SHA-256 values in this section hash raw Git blob bytes, not checkout bytes. This
avoids CRLF or LF working-tree conversion ambiguity.

The pre-existing Registry fields `accepted_recovery_source_sha256` and
`accepted_recovery_test_sha256` remain byte-for-byte historical opaque coordinates.
Their legacy values are not carrier authority and are not silently reinterpreted or
corrected by this Unit. Carrier authority uses only the explicitly named
`sha256_git_blob_bytes` fields below together with the exact Git blob object IDs.

- CHANGELOG mode: `100644`
- CHANGELOG Git blob: `874a2994ba9a020b32bd62e7fce5cc4f39b59e48`
- CHANGELOG blob SHA-256: `1f73e323cb07063492ab22037b0c7fdd158a1699ff76b25bd361d45f441d2894`
- Source mode: `100644`
- Source Git blob: `165c095684a71f29a3593baed063880fb0ef35cd`
- Source blob SHA-256: `0b026e525a5bd08a939dcf4cff705f74bb1ad0d1489ce2351b0bb6db7ea78642`
- Test mode: `100644`
- Test Git blob: `6a08ee752ba0646d7eea0eb5764cfd97f73f52f3`
- Test blob SHA-256: `f007035cb42bda04d46a211f8138488c39b1957b399ef63fb4c1a473cb7aec83`

## Final exact path set

The pull request final diff must contain exactly these five paths:

1. `CHANGELOG.md`
2. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
3. `docs/ai-team/work-locks/task058-a2-accepted-recovery-currentness-amendment-2026-08-28.md`
4. `src/ai_video_production/montage_learning_canonical_admission_transaction.py`
5. `tests/test_task058_montage_learning_canonical_admission_transaction.py`

The Registry binds this Evidence blob and a sorted exact-four projection containing
this Evidence, CHANGELOG, source, and test. The Registry excludes itself from that
projection to avoid self-reference. The projection format and digest are recorded in
the Registry after this Evidence blob is fixed.

## Target and authority transition

- Active target becomes PR 434 and its exact branch.
- PR 432 and head `795093c...` become a failed predecessor with no future push or merge.
- Implementation mutation is limited to the exact source and test blobs in payload C.
- Shared integration effect is limited to the exact approved CHANGELOG bullet.
- Registry and Evidence mutation is limited to metadata wrapper M.
- Target Ready and merge authority remain `NOT_GRANTED`; authority ID remains `null`.
- B+C, PP-A, other source, schema, test, runtime, native, provider, network, paid,
  Release, Deploy, and Production effects remain unauthorized.

## Local carrier validation

- TASK-058 canonical admission transaction focused: `83 passed, 5 Windows-only skipped`
- TASK-043, TASK-055, and TASK-058 feasible direct regression: `375 passed, 5 Windows-only skipped`
- Python compileall for `src` and `tests`: `PASS`
- OSS readiness: `12 passed`
- New dependency installation: `0`
- Source, test, and CHANGELOG payload C remained unchanged through validation.

Windows-only HANDLE and junction fixtures remain for the Hosted Windows matrix. The
next exact M must pass all six CI jobs; these local results do not replace that Gate.

## Head-currentness phases

1. Before carrier construction, PR 434 must be exact head `19831a43...`.
2. Local C and M may exist without remote effect. C alone must never be pushed.
3. After independent DEV-4 approval, one force-less push may move PR 434 from
   `19831a43...` to the externally frozen exact M head.
4. The pushed M must have parent C, C must have parent `19831a43...`, the final diff
   must be exact five paths, and the non-self-referential projection must match.
5. Any other PR, parent chain, path set, projection, or content is
   `TARGET_HEAD_MISMATCH`.
6. The exact M head must pass CI six of six, Security two of two, and Release metadata
   one of one with unchanged-head retry zero.
7. Independent DEV-4 must remain Critical and High zero. A separate Owner Gate must
   bind the exact M head before Ready or merge.

## Continuation and closure

1. Complete C and M locally and verify their exact topology and five-path diff.
2. Obtain independent Critic, Tester, and Judge approval for exact M.
3. Re-read main, PR 434 head, collisions, overlaps, and all carrier coordinates.
4. Push C and M together once without force, rebase, or retry.
5. Require Hosted CI, Security, and Release metadata to pass on exact M.
6. Obtain a separate exact Owner Ready and merge Gate.
7. Merge normally and verify fresh main, Registry revision 136, payload bytes, and
   post-main CI and Security.
8. Record PR 434 head, merge SHA, Hosted and post-main runs, and PR 432 supersession
   in an append-only Registry revision 137 closure.

No new implementation starts before the revision-137 closure is canonical.
