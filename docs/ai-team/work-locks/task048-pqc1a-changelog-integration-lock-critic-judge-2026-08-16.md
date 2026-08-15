# TASK-048 / P-QC-1A CHANGELOG Integration Lock Hosting Critic / Judge — 2026-08-16

## Authority and effect boundary

- Authorization: `BVP-AUTH-20260816-TASK048-PQC1A-CHANGELOG-INT-H0`
- Task: `TASK-048/P-QC-1A CHANGELOG INTEGRATION LOCK HOSTING H0`
- Authority: `IMPLEMENT_AND_HOST_EXACT_GOVERNANCE_UNIT_ONLY`
- Integration effect authority: `NOT_AUTHORIZED_AWAITING_SEPARATE_DESIGN_JUDGE`
- PR #106 Ready / merge authority: `NOT_AUTHORIZED`
- Implementation file mutation: `NOT_AUTHORIZED`
- CMake, native, audio, analyzer, OBS, RX, device, Asset, Dataset, Job,
  Training, Production, Release and Deploy effects: `NOT_AUTHORIZED`

This H0 transaction hosts governance metadata only. It does not change PR #106,
`CHANGELOG.md`, the P-QC implementation, schemas, tests, workflows or external
state.

## Fresh source of truth

- Repository: `baisound/bai_video_production`
- Fresh pre-host `origin/main`:
  `a7c9f0c7276249dd93b32508fe920007e7074c80`
- Registry before H0: revision `9`, state `ACTIVE`
- Registry audit base before H0:
  `00e1c75f186b0ba0240d75a96c5bf33fde224e19`
- Active implementation Locks: exact one,
  `BVP-LOCK-TASK048-PQC1A`
- P-OBS contract Lock: `HOSTED_CLOSED_RELEASED`
- Active Integration Locks: `0`
- Open pull requests: exactly PR `#106`
- PR #106 state: `OPEN / Draft / MERGEABLE`
- PR #106 exact base / head:
  `a7c9f0c7276249dd93b32508fe920007e7074c80` /
  `4f4453851b49aa2dc9a7c62a7626e52faa0f4675`
- PR #106 changed files: exact approved implementation `5`
- H0 two-path overlap with active Locks and open PRs: `0`
- Target implementation path overlap with other Locks and open PRs: `0`
- Remote H0 branch collision at transaction start: `0`

The existing implementation worktree and user work were not switched, cleaned,
stashed or rewritten. H0 uses an isolated clean worktree created from the exact
fetched `origin/main`.

## Exact H0 transaction

The H0 transaction changes exactly two files:

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task048-pqc1a-changelog-integration-lock-critic-judge-2026-08-16.md`

The Registry delta is:

- `registry_revision`: `9` -> `10`
- `audit_base_main_sha`: exact fresh pre-host main `a7c9f0c7276249dd93b32508fe920007e7074c80`
- append `BVP-INTEGRATION-LOCK-TASK048-PQC1A-CHANGELOG-20260816`
  with `status=ACTIVE`
- bind target PR `#106`, target branch and expected pre-integration head
  `4f4453851b49aa2dc9a7c62a7626e52faa0f4675`
- allow only `CHANGELOG.md` for a later separately authorized integration
  effect
- retain implementation file ownership under `BVP-LOCK-TASK048-PQC1A`
- roadmap delta: `NONE`

No other Registry root, Lock record, roadmap or merge-order field is changed.

## Canonical CHANGELOG entry

The sole later CHANGELOG delta is this exact one-line bullet:

> - Added TASK-048 P-QC-1A body-free voice-quality calibration metadata contracts with 23 canonical types, exact eight-stage capture-chain validation, declared/measured metric states, staging-versus-Asset separation, ordered single/SNR/before-after input bindings, interval-union readiness evidence, public/private projections and fail-closed P-VS-3A calibration binding. It records or analyzes no audio, changes no hardware/OBS/RX setting, performs no Asset/Dataset/Job/Training/Model/production effect, and adds no CMake/native/download/install/Release/Deploy operation.

H0 records this proposal but does not write it to `CHANGELOG.md`.

## Immutable implementation binding

The exact PR #106 implementation baseline is head
`4f4453851b49aa2dc9a7c62a7626e52faa0f4675`. Its five authorized blobs are:

| Path | Git blob |
|---|---|
| `docs/ai-team/tasks/TASK-048/p-qc-1a-implementation-readiness-and-evidence-2026-08-15.md` | `0b4fc953d42d15a1c8b836ba966558c8f8219857` |
| `schemas/voice-quality-calibration.schema.json` | `14eb39636cf96e7e1a9f204607940ed17b5cac36` |
| `src/ai_video_production/schema_resources/voice-quality-calibration.schema.json` | `14eb39636cf96e7e1a9f204607940ed17b5cac36` |
| `src/ai_video_production/voice_quality_calibration.py` | `df9f5148c1cc33e4047c9014b67357463e42e515` |
| `tests/test_task048_voice_quality_calibration_contract.py` | `f43c0d8e8be3bdcf3898128b55f8c1dcfc944710` |

The later target composition must be exactly these unchanged five files plus
one Integration-owned `CHANGELOG.md`. Any implementation blob drift, seventh
path or different CHANGELOG content expires the effect scope and parks the
unit.

## Current hosted Evidence and expected policy blocker

On exact head `4f4453851...`:

- CI Ubuntu Python 3.11 / 3.12 / 3.13: `SUCCESS`
- CI Windows Python 3.11 / 3.12 / 3.13: `SUCCESS`
- dependency audit: `SUCCESS`
- secret scan: `SUCCESS`
- changelog-and-version: `FAILURE`

The sole failure is `EXPECTED_INTEGRATION_POLICY_BLOCKER`. The exact hosted
message states that product changes require `CHANGELOG.md` in the PR. The
failed unchanged head is not retried and the workflow is not weakened.

Local validation for the immutable implementation baseline remains:

- focused suite: `14 passed`
- WSL2 compile: `PASS`
- WSL2 full regression: `1229 passed`
- public/package schema mirror: byte-exact `PASS`
- Critic residual Critical / High / Medium: `0 / 0 / 0`

## Sequencing and lifetime

1. Create the H0 Draft PR with exact two-file governance diff.
2. Require every H0 hosted check to reach terminal `SUCCESS`.
3. Ready and merge H0 only after a separate design Judge decision.
4. Verify the ACTIVE record by exact merged-main read-back and require
   post-merge CI and Security `SUCCESS`.
5. Only then may a separately authorized normal non-fast-forward merge of the
   exact fresh main into the PR #106 target branch occur. No rebase, force push
   or manual conflict resolution is permitted.
6. Prove all five implementation blobs remain unchanged, then add the exact
   one-line CHANGELOG entry in a separate atomic Japanese commit.
7. Require a normal push and fresh hosted run on the new material head. Do not
   retry the failed unchanged head.
8. Before target merge, prove exact six paths, implementation blob invariance,
   one-line CHANGELOG scope, schema mirror parity, fresh main, overlap zero and
   all nine checks terminal `SUCCESS`.
9. Target Ready / merge requires a separate design Judge authorization.
10. Verify merged-main exact content and post-merge CI / Security terminal
    `SUCCESS`.
11. Close the P-QC implementation Lock and this Integration Lock in one later
    separately authorized append-only H2 Registry transaction.
12. Branch or worktree cleanup is a final separate effect after H2 post-green.

Registry hosting transactions remain serialized because they share the
canonical Registry file.

## Main drift and failure policy

If main advances, a fresh main / Registry / PR / target-head / path-overlap
audit and a new exact limited integration authorization are required. The only
allowed target integration mechanism is the explicitly authorized normal
main-into-target merge. A merge conflict stops the unit; no manual resolution,
push or retry follows.

Park and report on Registry revision mismatch, target-head drift, path overlap,
implementation blob mismatch, non-exact six-file composition, extra CHANGELOG
line, H0 / target / post-merge non-success, timeout or any other UNKNOWN.
Timeout is read-reconciled and never guessed as success. No automatic retry,
rebase, reset, force, rollback, revert, Lock release or cleanup is permitted.

## Critic pass 1 — source, collision and ownership

- Fresh main, Registry revision, active Locks, Integration Lock history, open
  PRs and remote H0 branch were re-read immediately before branch creation.
- The H0 two paths overlap no active Lock or open PR.
- The later integration owns only `CHANGELOG.md`; it neither widens nor
  transfers ownership of the implementation five.
- The implementation baseline and all five Git blobs are exact and immutable.
- The P-OBS Lock is closed; the only active implementation Lock is P-QC.

Result: unresolved Critical / High / Medium = `0 / 0 / 0`.

## Critic pass 2 — authorization, CI and lifecycle

- H0 hosting, target main integration plus CHANGELOG, target Ready / merge,
  H2 closure and cleanup remain separate effects and decisions.
- The exact expected CI blocker is handled with an Integration-owned file, not
  an implementation edit, workflow exception or unchanged-head retry.
- H0 records the bullet but does not mutate CHANGELOG or PR #106.
- Drift, conflict, failure or UNKNOWN parks the mutation and requires exact
  read-only Evidence; none is converted to PASS.
- No CMake, native, audio, analyzer, OBS, RX, device, Asset, Dataset, Job,
  Training, Production, Release or Deploy authority is inferred.

Result: unresolved Critical / High / Medium = `0 / 0 / 0`.

## Pre-host Judge

- Exact two-file governance diff: `PASS`
- Registry revision / audit-base transition: `PASS`
- Active Integration Lock record discoverability: `PASS`
- Target head and five-blob binding: `PASS`
- Allowed-file and ownership separation: `PASS`
- Roadmap delta: `0`
- Workflow weakening / unchanged-head retry: `0`
- Authority or effect escalation: `0`
- Ready for atomic Japanese commit, normal push and Draft PR: `PASS`
- Integration Lock canonical on main: `PENDING_H0_MERGE_AND_READ_BACK`
- PR #106 main integration / CHANGELOG mutation: `NOT_AUTHORIZED`
- PR #106 Ready / merge: `NOT_AUTHORIZED`
- H2 closure / cleanup: `NOT_AUTHORIZED`

H0 hosted checks must all reach terminal `SUCCESS`. No later integration effect
is permitted until the H0 merged-main read-back and post-merge CI and Security
postconditions pass and a separate authorization is issued.
