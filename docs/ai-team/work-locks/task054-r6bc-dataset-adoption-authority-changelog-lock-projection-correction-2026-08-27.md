# TASK-054 R6B-C CHANGELOG Lock Projection Correction

Date: `2026-08-27`
Status: `PENDING_HOST_PR_PROJECTION_CORRECTION`
Registry revision proposal: `117`

## Correction identity

- lock_id:
  `BVP-INTEGRATION-LOCK-TASK054-R6BC-DATASET-ADOPTION-AUTHORITY-CHANGELOG-20260827`
- correction branch: `codex/task-054-r6bc-lock-projection-correction`
- correction base / lock-host merge:
  `f89081843773b858c78b42016d52a6d6ecf22fe2`
- target PR: `#404`
- expected pre-integration target head:
  `27b6db0b74f4e2fe5bab2f17d8221ba281e804d2`
- predecessor Registry revision: `116`

## Pre-effect finding

Revision 116 recorded immutable target projection digest `2a31ca...`, but that
value is not reproducible from the declared
`LF_JOINED_GIT_LS_TREE_LINES_FOR_SORTED_MAIN_TRIPLE_DOT_TARGET_CHANGED_PATHS`
specification. Recalculation over the sorted eight target paths, with one final
LF matching the previously verified TASK-059 projection convention, produces:

`a089f0a4fa58193a94fc9d3c63fd0ad1fe69d66ecf6b3a1deb0fdc30a1ddb724`

The eight `git ls-tree` lines at expected target head `27b6db0...` are exactly
identical to the eight lines after the local fresh-main merge. Therefore this is
a Registry digest recording defect, not target blob drift.

## Safety read-back

- lock-host PR `#405`: merged
- lock-host head: `a0cbf5a601147a14ed3d6297f739b953ef391d64`
- lock-host merge: `f89081843773b858c78b42016d52a6d6ecf22fe2`
- lock-host Hosted checks: `9 / 9 PASS`
- lock-host post-main CI: `33026855176 / PASS (6 / 6)`
- lock-host post-main Security: `33026855246 / PASS`
- target remote head remains `27b6db0...`; no target integration push occurred
- `CHANGELOG.md` effect: not started
- prior hosting Evidence: unchanged
- active nonclosed integration locks after this proposal: exactly `1`
- TASK-029 R10D successor reservation: preserved

## Exact correction scope

This correction changes only the Registry digest and records this new immutable
Evidence document. It does not change the approved CHANGELOG bullet, target
implementation/schema/test/design/task/operation-Evidence blobs, lock order,
successor order or any authority boundary.

No Dataset body read/copy/adoption, Dataset Store mutation, training, model
evaluation, Provider/paid execution, Binding promotion, Timeline/Resolve,
Release, Deploy or Production effect is authorized.
