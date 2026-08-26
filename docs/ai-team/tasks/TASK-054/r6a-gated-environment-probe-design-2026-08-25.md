# TASK-054 R6A Gated Environment Probe Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `PROBE_CONTRACT_IMPLEMENTED / REAL_HOST_NOT_EXECUTED`

## Goal and authority

R6A implements the exact read-only Windows/WSL probe required before any runtime acquisition or training. Actual host commands require an active `HOST_RUNTIME_PROBE_ONLY` Gate A binding. Current local tests use an injected runner only; they do not treat the Owner's general sleep-window machine-operation permission as the separate Dataset/model/device/download/training receipt required by the runbook.

## Fixed command set

The adapter can execute only the exact allowlisted argument vectors for:

- `wsl.exe --status`
- Ubuntu `python3 --version`
- Ubuntu `nvidia-smi` bounded GPU name/memory/driver query
- Ubuntu `df -Pk /home/baisound`

There is no shell interpolation. Commands use the R5F no-console/minimal-environment boundary, a 15-second timeout and 64-KiB combined stdout/stderr ceiling.

## Evidence boundary

The canonical report stores only:

- Gate reference and authority-Evidence digest;
- observation timestamp and exact command-set digest;
- WSL/PYTHON/GPU/STORAGE status, bounded version summary, stable detail code and raw-observation digest;
- derived overall `AVAILABLE / BLOCKED_RUNTIME / NOT_CONFIRMED`;
- fixed `EVIDENCE_ONLY_NO_INSTALL_DOWNLOAD_TRAINING_OR_EXECUTION_AUTHORITY` state.

Raw command output, host absolute paths and credentials are not persisted. Schema and packaged mirror require canonical check order and exact fields. Admission recomputes the report digest/status and rejects tampering.

## Failure behavior

Non-zero exit, empty/malformed observation, timeout or output ceiling yields `BLOCKED_RUNTIME`. It never authorizes silent install or fallback. An expired/wrong-scope/rejected Gate fails before the first command. Python/GPU/storage parsing is bounded; WSL success records only the non-sensitive summary `WSL configured`.

## Verification

Deterministic fixtures cover all-available, missing GPU, malformed version, timeout, output ceiling, Gate expiry/scope, command allowlist, canonical admission/checksum and schema mirror/order. No real subprocess is called.

## Remaining gates

The real host probe remains `NOT_EXECUTED / NOT_CONFIRMED` until Gate A contains current Dataset rights, model license/download authority, target runtime/storage/encryption, resource ceilings and device ownership. Runtime/dependency install, model download, training, Provider execution/upload, promotion, activation, release and deploy remain separately Human-Gated.
