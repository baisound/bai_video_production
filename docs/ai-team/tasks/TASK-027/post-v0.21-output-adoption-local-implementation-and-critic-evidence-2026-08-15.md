# TASK-027 P-ORCH-1 Output Adoption Local Implementation and Critic Evidence

Date: `2026-08-15`
Implementation base: exact main
`4532bb29c0ace58c720016f7ec313bb2037788ea`
Implementation branch: `feature/task-027-generation-output-adoption`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
Release state: stable `v0.21.0`; no new version selected

## Result

`P_ORCH_1_IMPLEMENTATION_HOSTED_CLOSED`

The bounded initial-generation route is implemented:

`TASK-013 COMPLETED`
-> contained output/hash/media validation
-> canonical TASK-003 Asset ingest
-> deterministic TASK-037 Candidate
-> TASK-040 PASS Attempt and `GENERATED_FROM` edge
-> Candidate `READY_FOR_AUDIT`.

The user-facing unified Generation Queue workspace exposes the exact action
`検証して監査候補へ登録`. It requires a new one-shot confirmation and does
not reuse the earlier Provider-execution confirmation.

## Canonical implementation

- `generation-output-adoptions.json` is a checksum-closed orchestration history,
  not another Asset, Candidate, Prompt or Audit truth.
- Durable phases are `PREPARED`, `ASSET_REGISTERED`,
  `CANDIDATE_REGISTERED`, `ATTEMPT_BOUND`, `READY_FOR_AUDIT` and
  `FAILED_KNOWN`.
- Every phase retains the exact execution, Queue, Slot, Prompt, output hash,
  Candidate and canonical Asset identity. Identity drift between records is
  rejected.
- Recovery revalidates Product output bytes and the canonical TASK-003 Asset,
  then continues only the missing suffix. It never replays Provider execution.
- TASK-040's existing prepared transaction is completed/finalized only when its
  persisted recovery state exposes one exact safe suffix. Unknown mixtures
  remain a Human Gate.
- Generated Asset rights remain `UNKNOWN`, reuse/commercial/derivative
  permission remains unknown, and `PUBLICATION_NOT_AUTHORIZED` plus Human
  rights review are retained.
- The Product output root is launcher-private. Every reference must use
  `project-output://`, remain below the configured root, traverse no symlink,
  name a non-empty bounded regular file and match the execution SHA-256.

## Explicit authority boundary

All durable and Shell projections keep these facts false:

- Provider execution started or replayed;
- paid execution authorized;
- Human Audit decision created;
- Candidate ACCEPT or LOCK;
- publication authorized;
- Resolve/Cubase/NLE mutation started.

No Credential, paid Provider, Native H3 retry, Production Deploy, Tag or Release
operation was performed.

## Final Critic review

### Authority and canonical truth

- `CRITICAL / CLOSED`: the orchestration store cannot replace TASK-003/037/040;
  real integration tests verify all authoritative state is written through
  those existing stores.
- `CRITICAL / CLOSED`: completion does not imply publish or Human acceptance;
  the final automatic state is only `READY_FOR_AUDIT`.
- `HIGH / CLOSED`: caller-forged Asset/Candidate/Prompt lineage is prevented by
  deriving every identity from the current completed execution and current
  Queue, with exact snapshot checks.

### Crash, concurrency and filesystem safety

- `CRITICAL / CLOSED`: interruption after each cross-store side effect is
  recoverable through exact-state inspection and idempotent continuation.
- `HIGH / CLOSED`: simultaneous stale confirmations are rejected by the
  adoption snapshot checksum and a cross-process update lock.
- `HIGH / CLOSED`: missing, changed, oversized, escaping or symlinked output is
  rejected before Candidate/Prompt creation.
- `HIGH / CLOSED`: recovery rechecks the output bytes and canonical Asset
  provenance; a different or missing Asset cannot be silently accepted.

### Evidence correctness corrective

- `HIGH / CLOSED FOR THIS UNIT`: a regenerated Prompt version does not currently
  persist the exact Strategy/Parent binding in TASK-027 Queue state. Recording
  strategy `0` would create false Evidence. Therefore only exact initial Prompt
  version `1` adoption is runnable. Later versions are visibly
  `PARKED_STRATEGY_BINDING_REQUIRED` and create no adoption side effect.
- A later bounded unit must add an immutable Queue-time Strategy/Parent binding
  before regenerated-output adoption can be authorized. This does not block the
  exact initial-generation route implemented here.

Unresolved Critical/High after implementation Critic: `0 / 0`.

## Verification

- TASK-027/TASK-013/TASK-037/TASK-040/TASK-036 final integrated focused
  regression: `94 / 94 PASS`.
- Full final-tree WSL2 regression: `1134 / 1134 PASS`.
- Full final-tree Windows-native regression: `1133 passed / 1 expected
  non-Windows-contract skip`.
- Real TASK-003 SQLite Asset + TASK-037 Production + TASK-040 Prompt end-to-end
  store test: PASS.
- Canonical/package schema parity and JSON Schema validation: PASS.
- `git diff --check`: PASS after final documentation synchronization.

## Hosted closure

- Commit: `0e3575a5bd11f8664409d03078b4ed0dc0b7e52b`.
- PR: `#80`, Ready/MERGEABLE, hosted `9 / 9 PASS`.
- Exact main merge: `66d97fd9d0bfbfebca339197fed2103011f56616`.
- Remote implementation branch removal: PASS.
- Dedicated implementation checkout removal: PASS.
- Fresh-main restart at exact merge SHA: PASS.

Stable Release remains `v0.21.0`; this unit created no Tag or GitHub Release.
P-ORCH-2 Strategy/Parent binding is only the next audit/design candidate and has
no implementation claim in this closure.
