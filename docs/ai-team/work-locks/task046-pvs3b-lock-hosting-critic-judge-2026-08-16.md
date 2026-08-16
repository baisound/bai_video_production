# TASK-046 / P-VS-3B Lock Hosting Critic / Judge Evidence

## Operation

- Authorization: `BVP-AUTH-20260816-TASK046-PVS3B-LH0`
- Unit: `TASK-046/P-VS-3B-LH0`
- Authority: exact two-file governance hosting only
- Owner agent: 開発担当2
- Owner thread: `01a00490-f4a3-7ab1-a3ea-fbda2ea50a02`
- Hosting branch: `codex/task-046-pvs3b-lock-hosting`
- Implementation branch reserved by the Lock: `codex/task-046-p-vs-3b-voice-dataset-revision-contract`
- Fresh pre-host main: `40b0567991ea8f7bd4342010cd52ef1e63ab6486`
- Registry prestate: revision `11`, blob `08a8fd44a6e5b713da9d7852b8ce2fc18bcb513f`
- Registry proposed state: revision `12`, audit base equal to the fresh pre-host main
- Repository mutation scope: the two authorized files only

This unit hosts a path reservation and fail-closed metadata contract boundary. It does not authorize implementation, Dataset persistence, canonical receipt issuance, TrainingInput effects, jobs, training, models, recording, OBS operations, release, or deployment.

## Fresh operation-time audit

- `origin/main` matched the authorized base.
- Registry revision, blob, state, and main-only activation scope matched the authorized prestate.
- Active implementation Locks: `0`.
- Active Integration Locks: `0`.
- Open pull requests: `0`.
- Existing `BVP-LOCK-TASK046-PVS3B` records: `0`.
- The five reserved implementation paths and this Evidence path were absent from main.
- The hosting and implementation branch names were absent locally and remotely.
- The isolated hosting worktree started clean at the exact base.

Any drift in these facts before push or merge invalidates the current transaction and requires a fresh read-only audit. No automatic rebase, retry, reset, rollback, or conflict resolution is authorized.

## Authorized Registry delta

The canonical edit is limited to:

1. `registry_revision`: `11` to `12`.
2. `audit_base_main_sha`: the exact fresh pre-host main.
3. One new `BVP-LOCK-TASK046-PVS3B` record with `status=ACTIVE`.

All other Registry root fields, existing Lock records, Integration Lock history, shared integration files, roadmap dependency gates, global denied operations, merge order, and parallel-safe units must remain byte-semantically unchanged. There is no roadmap delta.

The Lock becomes authoritative only through the existing root `activation_scope=AUTHORITATIVE_ONLY_WHEN_READ_FROM_MAIN`, the record `status=ACTIVE`, and an exact merged-main read-back. Computing a proposal, pushing a branch, or opening a Draft PR does not activate it.

## Reserved implementation surface

The implementation Lock reserves exactly:

1. `docs/ai-team/tasks/TASK-046/p-vs-3b-implementation-readiness-and-evidence-2026-08-16.md`
2. `schemas/voice-dataset-revision.schema.json`
3. `src/ai_video_production/schema_resources/voice-dataset-revision.schema.json`
4. `src/ai_video_production/voice_dataset_revision.py`
5. `tests/test_task046_voice_dataset_revision_contract.py`

Fixtures, `__init__.py`, `CHANGELOG.md`, workflows, shared integration files, existing P-VS-1A/P-VS-3A/P-QC files, and all effect adapters remain denied.

## Canonical contract set

The Lock fixes the accepted thirteen serialized types:

1. `VoiceDatasetStore`
2. `VoiceDatasetCommitIntent`
3. `VoiceDatasetRevision`
4. `VoiceDatasetMembershipEntry`
5. `DatasetMemberExclusion`
6. `DatasetCandidateReviewBinding`
7. `DatasetAdoptionReceipt`
8. `VoiceDatasetCommitEnvelope`
9. `DatasetStorePersistenceCapabilityBinding`
10. `StoreCommitBinding`
11. `DurableDatasetAdoptionJobBinding`
12. `DatasetReadinessCoverageIndicator`
13. `TrainingInputSnapshot`

The pure contract must keep the acyclic `CommitIntent -> Revision -> Receipt preimage -> Envelope` graph, context-complete first-revision CAS, parent/head/generation/full-store normal CAS, outer authoritative commit proof, and UNKNOWN versus actual corruption classification. `store_generation` is the sole store CAS counter; `store_revision`, fake genesis, revision zero, backward Envelope references, and aliases of accepted type names are rejected.

## Authority and dependency boundaries

- P-VS-1A, P-VS-3A, and the P-QC pure contract are hosted canonical dependencies.
- P-VS-4A and P-VS-2A runtime admission are not hosted by this transaction.
- Formal TASK-003 AssetRevision mapping, TASK-020 resource admission, a voice-dataset TASK-043 job kind, persistence capability, runtime capture/staging receipts, real quality-calibration receipts, and a canonical privacy-policy instance remain structured unresolved dependencies.
- A generic durable job does not authorize reuse of `PROJECT_MAINTENANCE` for Dataset adoption or training.
- P-VS-3A candidate review and P-QC readiness evidence are referenced; this unit creates no second Review, Asset, quality-policy, job, Consent, or store truth.
- The future canonical Dataset adoption effect issuer remains TASK-046/P-VS-3B, but the reserved pure five-file unit is not an issuer or persistence adapter.
- `TrainingInputSnapshot.training_start_authorized` remains false and no TrainingInput effect is authorized.

## Validation plan and separate gates

Lock hosting, Lock-host Ready/Merge, implementation authorization, implementation Draft PR, optional CHANGELOG Integration Lock, implementation Ready/Merge, H2 closure, cleanup, and future Dataset/Training effects are separate Gates.

The future implementation must validate at least:

- exact type names and body-free schema projection;
- first and normal CAS, stale parent/head/generation/store, fork, and revision-gap rejection;
- DAG cycle and backward-reference rejection;
- partial/tampered persistence classification;
- authoritative current-head or valid-ancestor inclusion, with orphan/fork rejection;
- UNKNOWN read/reconcile without duplicate effects;
- capability versus commit-proof state separation;
- candidate/review/Asset/Consent/quality and approved-label bindings;
- exclusion, unique integer-sample duration, null/UNKNOWN readiness, and low-count suppression;
- Job identity separation and `PROJECT_MAINTENANCE` rejection;
- public/private leakage controls and no filesystem, network, audio, job, store, training, or model effect surface;
- schema mirror parity, focused tests, Windows and WSL regression, hosted checks, and post-merge CI/Security.

## Critic pass 1: domain integrity

Checked for prior blocking drift:

- `VoiceDatasetStore` is present in the canonical type set.
- persistence capability and `StoreCommitBinding` proof are separate.
- `DatasetMemberExclusion` uses the accepted name.
- Receipt and Envelope hashes form no cycle.
- first and normal CAS fields are complete.
- preimages do not claim canonical commitment.
- current-head/ancestor inclusion does not accept orphan or fork history.

Residual Critical / High / Medium: `0 / 0 / 0`.

## Critic pass 2: governance and authority

- The record uses consumer-compatible `branch`, `base_sha`, and `status=ACTIVE`.
- Lock-host authority and implementation authority are separate.
- The two hosting files and five implementation files have no ownership overlap.
- Hosted contracts are not promoted into runtime receipts or effect authority.
- P-VS-4A stays parked until P-VS-3B is canonically hosted and re-audited.
- CHANGELOG, workflow, cleanup, persistence, Dataset, Job, Training, Model, and production authorities are not inferred.
- The Owner sleep signal does not expand this repository governance unit.

Residual Critical / High / Medium: `0 / 0 / 0`.

## Read-only Judge carried into hosting

- Domain readiness: `PASS`.
- Exact thirteen canonical types: `PASS`.
- Exact five-file implementation reservation: `PASS`.
- Lock record readiness: `PASS`.
- This H0 transaction readiness: `PASS` at the recorded fresh audit.
- Implementation authority: `NOT_AUTHORIZED`.
- Dataset persistence, receipt issuance, TrainingInput, Job, Training, Model, and production effects: `BLOCKED`.
- P-VS-4A: `PARKED`.
- Residual Critical / High / Medium: `0 / 0 / 0`.

Draft PR creation and hosted-check results are subsequent workflow evidence. Ready/Merge requires a separate exact-state authorization.
