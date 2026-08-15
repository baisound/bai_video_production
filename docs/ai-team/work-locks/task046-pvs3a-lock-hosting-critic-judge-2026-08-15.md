# TASK-046 / P-VS-3A Lock Hosting Critic / Judge — 2026-08-15

## Authority and effect boundary

- Umbrella authority: `BVP-AUTH-20260815-VOICE-CONTRACT-LH-SEQ-R0`
- Child authority: `BVP-AUTH-20260815-TASK046-PVS3A-LH0`
- Authority scope: `LOCK_HOSTING_ONLY`
- Implementation authority: `NOT_AUTHORIZED_AWAITING_SEPARATE_OWNER_DECISION`
- Implementation state: `NOT_STARTED`
- Recording, OBS, audio, Asset, Dataset, Training, Model, Release and Deploy effects: `NOT_AUTHORIZED`

This unit hosts governance metadata only. It neither implements the recording
contract nor dispatches any runtime or external effect.

## Fresh source of truth

- Repository: `baisound/bai_video_production`
- Fresh pre-host main: `a73dea0899e5eb8e70f69d986c7c47f8fd85445c`
- Immutable main tree: `8cebd437a19af8ab12f16f1df9f0f19dc2942b8f`
- Registry before this change: revision `3`, state `ACTIVE`
- Open pull requests at pre-host audit: `0`
- Active implementation locks at pre-host audit: `0`
- Active integration locks at pre-host audit: `0`
- Proposed implementation allowed-file overlap: `0`
- Remote hosting branch collision: `0`

The existing local user worktree was not used or changed. The hosting branch
was created from the exact fetched `origin/main` in an isolated clean checkout.

## Exact hosting transaction

The transaction changes exactly two files:

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task046-pvs3a-lock-hosting-critic-judge-2026-08-15.md`

The registry edit is one atomic governance delta:

- `registry_revision`: `3` -> `4`
- `audit_base_main_sha`: exact fresh pre-host main
- append `BVP-LOCK-TASK046-PVS3A` with `status=ACTIVE`
- retain separate Lock-host and implementation authority states
- insert exactly one merge-order dependency before `TASK-047/P-OBS-1`:
  `TASK-046/P-VS-3A_CONTRACT_HOSTED_BEFORE_TASK-047/P-OBS-1`

No `CHANGELOG.md`, workflow, shared integration, implementation, schema,
module or test file is part of this hosting unit.

## Active lock invariants

- Consumer keys are `branch`, `base_sha` and `status=ACTIVE`.
- `base_sha` is the exact fresh main at Lock-host transaction start; it does
  not self-reference the future merge commit.
- Activation proof is the combination of the root main-only activation scope,
  the `ACTIVE` record and exact merged-main read-back.
- Canonical serialized types remain exactly:
  - `VoiceRecordingSessionRevision`
  - `VoiceSegmentAttemptRevision`
  - `TeleprompterCheckpointRevision`
  - `DatasetCandidateRevision`
  - `DatasetCandidateReviewDecision`
- `CANCELLED_WITH_RETAINED_EVIDENCE`, structured
  `ExecutionAuthorizationBinding`, and exact RESUME attempt lineage remain
  mandatory implementation invariants even though no implementation file is
  changed here.
- P-VS-3B, P-VS-4A and P-QC-1A remain design references only and are not
  represented as hosted contracts by this transaction.

## Critic pass 1 — source, Registry and overlap

- Fresh main, Registry revision, open PRs, active Locks and remote branch were
  independently re-read immediately before branch creation.
- The five future P-VS-3A implementation paths do not overlap any active Lock,
  shared integration file or open PR.
- The hosting unit owns only the two paths listed above.
- No stale Registry revision or stale audit base is reused.

Result: unresolved Critical / High = `0 / 0`.

## Critic pass 2 — authority and scope

- The Owner child authorization is recorded independently from implementation
  authorization.
- The `ACTIVE` record does not claim implementation start, Production READY,
  recording, Dataset adoption or any external dispatch.
- Workflow weakening, CI exception, CHANGELOG edits and shared-file expansion
  are absent.
- The merge-order delta is the exact Owner-authorized single line.
- Failure, drift or unknown hosted state requires parking; there is no automatic
  rollback or continuation to the second child unit.

Result: unresolved Critical / High / Medium = `0 / 0 / 0`.

## Pre-host Judge

- Exact two-file governance diff: `PASS`
- Registry revision and audit-base transition: `PASS`
- Active lock discovery compatibility: `PASS`
- Owner authority separation: `PASS`
- Implementation and effect escalation: `0`
- Ready for Draft PR: `PASS`
- Lock canonical on main: `PENDING_MERGE_AND_READ_BACK`
- Child 2 effective: `NO_UNTIL_CHILD_1_POST_MERGE_GREEN`

Hosted checks must all reach terminal `SUCCESS`. After merge, the exact Registry
record must be read from main and both post-merge CI and Security must succeed
before any second hosting unit can start.
