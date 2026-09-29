# TASK-035 Audio Round-trip Current Read R0 Evidence

- Date: 2026-09-29
- Development profile: DEV-4 Foundation Critical
- Status: `IMPLEMENTED / FOCUSED_PASS / HOSTED_PENDING / EFFECT0`
- Base: `origin/main` at `1d9f4a471ea8540a9fb2df19a0e2cd933e8374e2`
- Branch: `codex/task-035-round-trip-current-read-r0`
- Worktree: `C:\Users\user\.codex\worktrees\1a51\bai-video-production\task035-r1-current-read-worktree`
- Run identity: `TASK-035/audio-round-trip-current-read-r0/20260929T000000JST`
- Durable checkpoint: `C:\home\baisound\evidence\bai-video-production\TASK-035\audio-round-trip-current-read-r0\20260929T000000JST\checkpoint.md`

## Result

This bounded R0 source unit closes the TASK-035 owner-current-read gap found by
the TASK-041 Audio Completion R2 readiness audit. It adds a fixed Product
Project history for body-free `AudioRoundTripManifest` records and a sealed
read result that distinguishes `CURRENT`, `STALE`, `NOT_FOUND` and
`STORE_NOT_FOUND`.

The owner history accepts only exact append order. Every manifest lineage must
start at revision 1 and each later revision must identify the exact previous
owner head. Exact duplicate replay is idempotent. Revision gaps, wrong parents,
foreign Projects, malformed records, unsafe authority claims, unknown fields,
checksum changes and stale save attempts fail closed.

The current read selects only the latest owner head for a manifest identity.
It is `CURRENT` only when the requested Session Plan still matches and, when
supplied, the expected manifest head still matches. Either difference becomes
a deterministic stale reason. Missing store and missing manifest remain
separate results and cannot claim currentness.

## Boundary

The fixed store contains metadata only. Its public read projection omits
Session Plan, project snapshot and execution receipt hashes. The sealed result
cannot be forged with audio-read, external execution, REAPER launch, render,
Asset promotion, Resolve mutation or publication authority.

This unit does not read or render audio, launch REAPER or iZotope, promote an
Asset, mutate Resolve, invoke a Provider, mint an Audio Completion PASS, write
the completion ledger, release, deploy or activate Production.

## Verification

- Python compile check for the changed source and test: `PASS`.
- Direct TASK-035 contract/store gate: `34 / 34 PASS`.
- TASK-035 plus downstream TASK-026/TASK-041/TASK-036 regression:
  `176 / 176 PASS`.
- Public and packaged schemas are byte-identical and validate the exact shared
  TASK-035 manifest definition.
- Static changed-source inspection found no audio or external-execution
  primitive.
- Hosted clean-environment checks remain required and pending.

## Remaining TASK-041 Audio Completion R2 dependencies

1. TASK-014 implemented `NarrationPublicationReceipt` and owner current read;
2. TASK-036 typed TASK-041 audio-completion wrapper.

Until both are provided and freshly reviewed, Audio Completion R2 remains
dependency-blocked and cannot mint canonical PASS.
