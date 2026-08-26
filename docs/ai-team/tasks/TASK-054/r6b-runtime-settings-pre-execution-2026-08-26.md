# TASK-054 R6B Runtime Settings Runbook (Pre-execution)

Status: `PRE_EXECUTION`
Date: `2026-08-26`
Task: `TASK-054`
Atomic Unit: `R6B model acquisition and training runtime preparation`

## Purpose

Define the planned local-only settings for reproducible, fail-closed R6B acquisition, training, and evaluation. This is the pre-execution version; observed values and outcomes belong in a separate result document.

## Planned settings

- Base model: `Qwen/Qwen3-8B`
- Immutable model revision: `b968826d9c46dd6066d109eabc6255188de91218`
- Remote code: disabled
- Runtime boundary: isolated WSL2 virtual environment
- GPU strategy: single local NVIDIA GPU
- Initial tuning strategy: four-bit QLoRA/LoRA, subject to capability smoke-test PASS
- Artifact storage: local external paths outside Git
- Dataset admission: deny by default until manifest, rights/consent, provenance, split, retention, and redaction checks pass
- Network use: limited to approved public dependency and model acquisition
- Credential policy: no credential is expected; if a provider unexpectedly requests one, stop without entering or recording it
- Telemetry/reporting integrations: disabled unless separately reviewed and authorized
- Model promotion and Production Activation: disabled

## Planned reproducibility controls

- Pin model by immutable revision rather than a moving branch name.
- Pin Python packages and hashes.
- Record CUDA, driver, Python, package, and GPU observations.
- Record training profile, random seeds as non-secret reproducibility values, dataset manifest digest, adapter digest, and evaluation-policy digest.
- Keep raw data, prepared data, splits, checkpoints, and evaluation output in separate directories.
- Prevent evaluation-only confirmation mode from writing training examples or updating adapters.

## Planned training/evaluation gates

1. Dataset admission PASS.
2. Leakage-resistant train/validation/test split PASS.
3. Baseline inference and resource smoke PASS.
4. Bounded training dry run PASS.
5. Approved real-data evaluation executes read-only against the frozen candidate.
6. Evaluation results remain advisory; promotion requires a separate decision and authority.

## Operator-facing behavior

- Clearly label `学習モード` and `確認モード`.
- `確認モード` produces narration/commentary candidates from a video but must not learn or mutate the training store.
- `学習モード` must show dataset admission status, active profile, estimated resource use, start confirmation, progress, cancellation, and artifact identity.
- Spoken cues such as `チェイス` are candidate semantic evidence and must not alone establish the canonical game event without corroborating video/event evidence.

## Safety and recovery

- Fail closed on missing manifests, digest mismatch, unexpected remote-code requirements, insufficient storage, incompatible CUDA, or missing rights/consent.
- Cancellation must leave the last valid artifact immutable and mark partial output as non-promotable.
- Never place secrets or private media content in documentation, Git, CI, prompts, or logs.

## Expected result record

After settings are applied and verified, create a separate execution-result document with exact non-secret settings, deviations, validation results, artifact identities, and rollback status, then notify the BAI Development OS task titled `秘書`.
