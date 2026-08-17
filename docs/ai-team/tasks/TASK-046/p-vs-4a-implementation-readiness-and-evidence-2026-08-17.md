# TASK-046 / P-VS-4A Training Run Contract — Implementation Evidence

Date: 2026-08-17
Base: `main@43a5afc392b8c0f4e034d73db01af1ea79e4b182`
Branch: `codex/task-046-p-vs-4a-training-run-contract`

## Outcome boundary

This unit implements a body-free, pure metadata contract for fine-tuning Run,
checkpoint, Model artifact composition, Candidate registration, held-out
evaluation and Owner approval.  It provides parsing, canonical hashing,
validation, state/CAS lineage checks, fail-closed preflight/dispatch/resume
classification and public/private projections.

It does **not** create a durable Job, reserve GPU/CPU/RAM/VRAM/disk, start a
process, load/train/infer a Model, read/analyze audio, persist/merge an artifact,
issue Owner approval, bind a VoiceProfile, render narration, publish or deploy.

## Canonical serialized types

1. `EngineAdmissionBinding`
2. `OutputArtifactDestinationBinding`
3. `TargetResourceFeasibilityBinding`
4. `ExecutionResourceReservationBinding`
5. `TrainingDurableJobBinding`
6. `TrainingExecutionAuthorizationBinding`
7. `CurrentUseRightsBinding`
8. `EvaluationInputSnapshot`
9. `ContaminationProofBinding`
10. `TrainingRunIntent`
11. `TrainingRunRevision`
12. `TrainingComputeTerminalReceipt`
13. `CheckpointArtifactBinding`
14. `GPUProcessObservationBinding`
15. `ModelArtifactBinding`
16. `ModelCandidateRevision`
17. `EvaluationReceipt`
18. `OwnerModelApprovalDecisionBinding`
19. `TrainingPreflightReport`
20. `TrainingDispatchAdmissionReport`

`EngineAdmissionBinding` is the canonical public/root name.  The rejected
`EngineModelRuntimeLicenseBinding` alias is not accepted.

## Hosted and unresolved dependencies

- P-VS-1A VoiceProfile/Consent and P-VS-3A Recording Session are
  `HOSTED_CANONICAL` read-only dependencies.
- P-VS-3B `TrainingInputSnapshot` is `HOSTED_CANONICAL` and is the only Dataset
  input boundary.
- TASK-020 and P-QC-1A are `HOSTED_CANONICAL` contracts; a concrete current
  probe/reservation/evaluation receipt still must be `BOUND_VERIFIED` per Run.
- TASK-043 durable Job truth remains external.  `PROJECT_MAINTENANCE` and
  Dataset Adoption Job identities are rejected.
- P-VS-2A engine/model selection is technical-candidate evidence only.  It is
  not training, install, commercial or license admission.
- P-VS-4B and TASK-014 consume approved Model/narration boundaries later and
  receive no authority from this unit.

## Fail-closed invariants

- Evaluation selection is immutable metadata bound into the Intent.  Training
  projection includes only Evaluation snapshot ID/hash and contamination proof
  digest, never selected item/Asset/range/body/credential detail.
- Contamination PASS requires identity, Asset mapping, checksum, half-open
  sample range, source lineage and hosted semantic near-duplicate policy PASS.
- FULL/PEFT/LoRA feasibility is mode-specific.  A short load/step or another
  mode's PASS cannot be reused.
- Feasibility and live reservation are separate.  QUEUED/RUNNING require a
  fresh admitted reservation after Owner Gate.
- Training Job identity is distinct from Dataset Adoption and
  `PROJECT_MAINTENANCE`.
- timeout/unknown process state never auto-replays.  An observed live process
  blocks duplicate dispatch.
- checkpoint URI/bytes alone never authorize resume.  Canonical persistence,
  checksum, Dataset, base Model, runtime, code, config, license/Consent,
  optimizer/step compatibility and one-shot Owner RESUME gate are required.
- compute completion, artifact binding, Candidate registration, Evaluation,
  Owner approval, VoiceProfile binding, narration production and publication
  are separate states/effects.
- FULL_MODEL, adapter, merged and engine-native artifact composition use strict
  state-dependent fields.  Adapter is not displayed as a standalone full Model;
  merge creates a new binding with provenance.
- BOUND artifact still blocks Evaluation/approval when load compatibility or
  inherited license is UNKNOWN/MISMATCH/REVOKED.
- Owner approval requires exact Candidate/Evaluation/artifact/current-rights
  hashes plus external Owner Human Gate evidence.  Approval has no production
  or publication effect.
- raw audio/text, credentials, absolute paths, selected held-out items and
  voice-linkable hashes are absent from Public projection.

## Lifecycle

The append-only lifecycle distinguishes:

`DRAFT` → `PREFLIGHT_PENDING` → `READY_FOR_OWNER_HUMAN_GATE` → `QUEUED` →
`RUNNING` → `TRAINING_COMPLETED_ARTIFACT_UNBOUND` →
`MODEL_CANDIDATE_REGISTERED` → `EVALUATION_PENDING` → `EVALUATED_CANDIDATE`.

`BLOCKED`, `CHECKPOINTED`, `PAUSED_SAFE`, `STOP_REQUESTED`, `FAILED_KNOWN`,
`UNKNOWN` and `CANCELLED_SAFE` retain separate failure/reconciliation meaning.
`UNKNOWN` has no direct automatic transition back to `RUNNING`.

## Acceptance inventory

Focused synthetic tests cover:

- canonical schema/mirror payloads and digest tamper;
- legal/Consent/rights UNKNOWN/REVOKED fail-closed preflight;
- training-mode admission non-reuse;
- same Asset overlapping held-out ranges and unknown near-duplicate policy;
- absolute/traversal output destinations;
- missing/expired Job/reservation/Owner gate;
- Dataset Adoption/PROJECT_MAINTENANCE identity reuse;
- checkpoint path-only resume and stale Dataset/Model/runtime/code/config;
- unknown/orphan GPU process duplicate-run prevention;
- adapter-as-full misuse, wrong composition and missing merge provenance;
- unbound artifact Candidate registration;
- unknown license inheritance Evaluation/approval block;
- compute/artifact/Candidate/Evaluation/approval Gate skipping;
- immutable state/CAS lineage and Public leakage suppression;
- training dispatch projection exclusion of Evaluation item details;
- static no-filesystem/network/process/model/audio effect surface.

## Validation

- focused tests: `20 passed`;
- public/schema-resource mirror: byte exact;
- Python compile: PASS;
- Windows full regression: `1780 passed, 1 skipped, 1 failed`; the sole failure
  is the unrelated TASK-047 Windows installer acceptance.  Its Inno Setup log
  proves managed-host denial when creating a Start Menu directory and HKCU
  uninstall key (`WinError/code 5`); all P-VS-4A tests pass.  The first run's
  inherited pytest temp root was also inaccessible, so the recorded run uses a
  fresh explicit task test root and does not misclassify that environment error
  as product evidence;
- WSL2 full regression: `1781 passed, 1 skipped` in `69.31s`; the skip is the
  intentionally Windows-only TASK-047 installer acceptance.

## Critic pass 1

Initial findings:

- High: resume acceptance needed an explicit exact Dataset/Model/runtime/code/
  config/current-rights comparison rather than relying on artifact existence.
- High: Evaluation selection needed a dedicated training projection proving
  selected item/Asset/range details never reach the training adapter.
- Medium: ModelArtifactBinding needed state-dependent nullability for full,
  adapter and merged composition.

Corrections are implemented and covered by negative tests.

## Critic pass 2

- Builder: canonical 20-type surface and lifecycle/Gate separation PASS.
- Security/privacy: body/path/credential suppression and no-effect surface PASS.
- Compatibility: P-VS-3B snapshot, TASK-020/P-QC bindings and TASK-014 consumer
  boundary remain reference-only and unmodified PASS.
- Residual Critical/High/Medium: `0 / 0 / 0`.

## Read-only/effect Judge

- DOMAIN_READINESS: `PASS`
- PURE_METADATA_IMPLEMENTATION: `PASS`
- WINDOWS_FULL_REGRESSION: `PASS_WITH_UNRELATED_TASK047_SANDBOX_DENIAL`
- WSL2_FULL_REGRESSION: `PASS`
- TRAINING/MODEL/AUDIO/PRODUCTION/PUBLICATION_EFFECT: `BLOCKED`
- OWNER_TRAINING_HUMAN_GATE_ISSUED: `NO`
