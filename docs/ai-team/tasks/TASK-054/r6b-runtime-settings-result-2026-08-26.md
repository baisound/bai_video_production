# TASK-054 R6B Runtime Settings Runbook (Execution Result)

Status: `APPLIED / PASS WITH DATASET GATE OPEN`
Observed at: `2026-08-26T00:12:52Z`
Task: `TASK-054`

## Applied settings

- Base-model candidate config: `config/task054/base-model-candidates.yaml`.
- Candidate ID: `qwen3-8b-b968826d`.
- Model revision is immutable and remote code is disabled.
- Training profile: `config/task054/training-profile.yaml`.
- Method: QLoRA SFT, NF4 four-bit, double quantization, BF16 compute.
- LoRA rank/alpha/dropout: `32 / 64 / 0.05`.
- Evaluation policy: `config/task054/evaluation-policy.yaml`.
- Runtime is isolated in WSL2 and model/data/checkpoint roots are outside Git.
- Acquisition and smoke inference used public endpoints/local files without credentials.
- Telemetry was disabled for model acquisition and smoke inference.
- Offline inference used `local_files_only=true` and `trust_remote_code=false`.
- Automatic approval, promotion, route activation, and Product activation remain disabled.

## Validated behavior

- Candidate config, training profile, evaluation policy, and verification-report digest cross-check: PASS.
- QLoRA target modules exist on the pinned architecture: PASS.
- Confirmation/evaluation remains non-learning by contract.
- Training output, when eligible, remains quarantined with no approval or activation.
- Hard evaluation gates cannot be averaged away.

## Dataset and execution state

- Dataset directory: absent.
- Admitted Dataset manifest: absent.
- Rights/consent/provenance/split Evidence: absent.
- Training state: `NOT_STARTED_DATASET_ADMISSION_REQUIRED`.
- Real-data evaluation state: `NOT_STARTED_DATASET_ADMISSION_REQUIRED`.
- Base-model acquisition state: `VERIFIED_PUBLIC_BASE_MODEL_ACQUIRED_NO_TRAINING_NO_PROMOTION`.

Owner approval is recorded, but approval alone does not invent an admissible Dataset. The next safe unit is Dataset identity discovery/admission or creation of a body-free manifest from Owner-controlled source material. No private data may be uploaded or copied into Git, prompts, reports, or CI.

## Rollback and recovery

No rollback was required. The last verified state consists of the immutable base-model acquisition report, the local NF4 smoke report, the hash lock, and three fail-closed config files. Partial training artifacts do not exist.
