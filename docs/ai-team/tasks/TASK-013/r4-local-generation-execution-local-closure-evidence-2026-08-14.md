# TASK-013 — R4 Local Generation Execution Control Local Closure Evidence

- Date: `2026-08-14`
- Branch: `codex/task-013-r4-local-generation-execution`
- Starting main: `3c4dd8d283d9c2c68740db93c89fed6e4880d5a2`
- Gate: `LOCAL PRODUCT GATE PASS / HOSTED CLOSURE PENDING`
- DEV Profile: `DEV-4 EXTERNAL EXECUTION CRITICAL`

## Delivered

- strict project-scoped `generation-executions.json` Event history with checksum, serialized CAS and exact transitions;
- exact current TASK-027 Queue re-derivation from Approved Plan, Feasibility, LOCK/STALE, Continuity and Prompt stores before execution;
- project-contained, non-symlink, bounded private Prompt resolution and SHA-256 verification;
- exact current AI Connection Profile and canonical route resolution;
- hard `LOCAL_FREE_AI` plus no-credential boundary;
- one-shot Human execution confirmation consumed before stale revalidation;
- durable `DISPATCHING` write before the injected port side effect;
- terminal `COMPLETED`/`FAILED` Evidence and restart-visible `RECOVERY_REQUIRED` for uncertain interrupted dispatch;
- no automatic replay, no second execution for one Queue entry and exact result identity checks;
- optional unified Generation Queue UI control with body-private status, recovery warning and explicit local execution confirmation.

## Validation

- focused TASK-013 / TASK-027 / TASK-036 regression: `58 / 58 PASS`;
- full WSL2 Ubuntu regression: `904 / 904 PASS`;
- Windows Python 3.12 compileall: `PASS`;
- WSL2 compileall: `PASS`;
- embedded Desktop JavaScript syntax: `PASS`;
- git diff check: `PASS`;
- unresolved Critical/High Critic findings: `0 / 0`.

## Negative / recovery Evidence

- paid or credential-bearing route is rejected before the port is called;
- private Prompt checksum drift is rejected before `DISPATCHING`;
- current upstream Evidence drift makes a stored Queue entry stale and non-executable;
- a known Provider failure records terminal `FAILED` and cannot be replayed;
- an uncertain interruption leaves durable `DISPATCHING`, reports `RECOVERY_REQUIRED` and exposes no automatic retry;
- replayed/stale confirmation is rejected after the token is consumed;
- checksum-valid unknown fields, terminal identity drift and unsafe output references are rejected.

## Claim boundary

This local closure proves the Product execution-control contract using an injected fake port. It does **not** prove a live ComfyUI/H3 generation, Provider-native output, Candidate creation, TASK-038 Audit result, TASK-040 Attempt import, paid execution, Resolve/Cubase mutation or publishing.

Real local adapter composition remains a separate renewed target audit because the trusted launch contract does not yet identify an exact endpoint, workflow, input staging root or output containment root.

No package version, Tag or GitHub Release is selected at this checkpoint. Stable release remains `v0.20.1`.
