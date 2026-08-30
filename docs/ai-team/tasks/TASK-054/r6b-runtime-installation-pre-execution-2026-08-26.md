# TASK-054 R6B Runtime Installation Runbook (Pre-execution)

Status: `PRE_EXECUTION`
Date: `2026-08-26`
Task: `TASK-054`
Atomic Unit: `R6B model acquisition and training runtime preparation`

## Authority

Owner approved R3D execution, R6B acquisition/training, and real-data evaluation. The active sleep-window authority also permits application download, installation, required settings, and application launch until the next Owner message `おはよう`. This document does not broaden those permissions.

## Purpose

Prepare an isolated WSL2 training runtime for the approved R6B work. Installation is not model promotion, release, deployment, Production Activation, or authority to upload private data.

## Planned installation scope

- Create an isolated virtual environment at `/home/baisound/.venvs/bvp-task054-training`.
- Install only reviewed, version-pinned Python packages needed for CUDA inference, QLoRA training, dataset validation, and evaluation.
- Resolve and record package hashes before the final installation step.
- Acquire `Qwen/Qwen3-8B` only at immutable revision `b968826d9c46dd6066d109eabc6255188de91218`.
- Store the public model outside Git and compute SHA-256 digests after acquisition.
- Do not enable arbitrary remote code (`trust_remote_code=false`).

## Preconditions

- WSL2 Ubuntu, Python 3.12.3, NVIDIA GeForce RTX 4070 SUPER (12282 MiB), and sufficient storage were observed as available by the bounded R6A environment probe.
- The selected model is public and non-gated; no access token is planned.
- Dependency compatibility and exact wheel availability must be verified before installation.
- Training may start only after an admitted dataset manifest, rights/consent record, split policy, and storage boundary exist.

## Planned procedure

1. Reconfirm branch, HEAD, clean worktree, Python, CUDA/GPU, storage, and package resolver availability.
2. Resolve compatible pinned package versions from primary publisher indexes.
3. Download candidate wheels into a bounded temporary wheelhouse and compute hashes.
4. Review the generated lock and reject unexpected source distributions, remote-code requirements, or incompatible CUDA artifacts.
5. Create the isolated virtual environment.
6. Install strictly from the reviewed lock/wheelhouse.
7. Run import, CUDA visibility, four-bit quantization capability, and minimal inference smoke checks.
8. Download the pinned model revision, verify the resolved commit, inventory every file, and compute SHA-256 digests.
9. Record observed results in a separate result runbook and notify the BAI Development OS task titled `秘書`.

## Safety and rollback

- Never print or record secrets, tokens, private keys, passphrases, or private dataset contents.
- Do not install into the system Python environment.
- Do not write model binaries, caches, datasets, or checkpoints into Git.
- On failure, preserve logs that exclude secrets and remove only the exact isolated environment or temporary wheelhouse after path validation.
- Do not delete shared caches or unrelated environments.

## Expected evidence

- immutable model revision and post-download file SHA-256 inventory;
- package lock with hashes and installation report;
- environment and GPU capability report;
- smoke-test result;
- separate execution-result document identity.
