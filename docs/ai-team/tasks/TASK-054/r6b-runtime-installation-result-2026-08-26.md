# TASK-054 R6B Runtime Installation Runbook (Execution Result)

Status: `EXECUTED / PASS`
Observed at: `2026-08-26T00:12:52Z`
Task: `TASK-054`
Atomic Unit: `R6B model acquisition and training runtime preparation`

## Authority used

- Owner approval: R3D execution, R6B acquisition/training, and real-data evaluation.
- Active sleep-window authority: application download, installation, required settings, and application launch until the next Owner message `おはよう`.
- No release, deployment, Production Activation, model promotion, private-data upload, or paid-provider authority was inferred.

## Installation result

- Isolated WSL2 virtual environment: created at the predeclared local path; PASS.
- System Python packages: unchanged.
- Binary wheelhouse: 77 wheels, 3.9 GiB, no source distribution admitted.
- Hash lock: `requirements/task054-training.lock`.
- Hash-lock SHA-256: `c0c9a049df8609ba70d393cc958d88ed379873b7a0ec4c2ca3401615eb43eed3`.
- Installation mode: offline, `--no-index`, local wheelhouse, `--require-hashes`.
- Installed environment size: 7.2 GiB.
- Installed distribution count including bootstrap packages: 78.
- `pip check`: PASS, no broken requirements.

## Principal installed versions

- Python 3.12
- PyTorch `2.11.0+cu128`
- CUDA runtime `12.8`
- Transformers `5.15.1`
- Accelerate `1.14.0`
- PEFT `0.20.0`
- TRL `1.10.0`
- Datasets `5.0.1`
- bitsandbytes `0.50.1`

## Model acquisition result

- Candidate: `Qwen/Qwen3-8B`
- Immutable revision: `b968826d9c46dd6066d109eabc6255188de91218`
- Public/non-gated acquisition: PASS without credentials.
- Model file count: 15.
- Weight shard count: 5.
- Total verified bytes: 16,397,461,266.
- Sorted inventory SHA-256: `5e063d7779d5affb32b480e70534d667aef407cd5258a507ec8cd83afff116f6`.
- Verification report: `reports/task054/r6b-qwen3-8b-b968826d/base-model-verification.json`.
- Verification report SHA-256: `38e8e0d0398bd6661b519cf70188ffa7527893d3db086a1e153e477863046e0c`.
- Model binaries remain outside Git.

## Runtime verification

- GPU: NVIDIA GeForce RTX 4070 SUPER, 12,282 MiB.
- Compute capability: 8.9.
- PyTorch CUDA tensor operation: PASS.
- bitsandbytes NF4 CUDA operation: PASS.
- Offline Qwen3-8B NF4 load and synthetic Japanese inference: PASS.
- Model load: 11.596 seconds.
- 24-token synthetic generation: 2.19 seconds.
- Peak allocated GPU memory: 6,140,123,136 bytes.
- All seven configured LoRA target-module names exist in the real model: PASS.
- Smoke report: `reports/task054/r6b-qwen3-8b-b968826d/local-nf4-smoke.json`.
- Smoke report SHA-256: `c4eaba097ad76d85f595d28d9619c3cfdebdd87fd1968490ba9b8f703ff6824e`.

## Deviations and remaining gates

- No secret or access token was required or recorded.
- Installation and acquisition completed as planned.
- Training did not start because `datasets/task054/**/manifest.json` is absent. Rights, consent, provenance, split, retention, and redaction admission therefore remain unsatisfied.
- Real-data evaluation did not start for the same Dataset-admission reason.
- No adapter, checkpoint, R6C seal, EVALUATED Binding, approval, promotion, or activation was created.

## Rollback status

`NOT_REQUIRED`: installation, dependency, CUDA, NF4, and local-inference checks passed. If later rollback is authorized, remove only the exact dedicated virtual environment, wheelhouse, and model-cache paths after resolving and validating each absolute path. Shared caches and unrelated environments must not be removed.
