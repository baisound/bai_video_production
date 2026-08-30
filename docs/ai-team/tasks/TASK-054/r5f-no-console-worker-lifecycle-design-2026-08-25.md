# TASK-054 R5F No-console Worker Lifecycle Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / COMMIT_READY`

## Goal

Training Studioの長時間処理をUI threadから分離できる、bounded・no-console・checkpoint-awareなProduct-local lifecycleを実装し、R5E presentationへ正確に投影する。R5F testはinjected fake processだけを使い、model/runtime/training/Providerを実行しない。

## Request boundary

Immutable requestは次をexact digestへ束縛する。

- action kind / idempotency key / Workspace
- expected Dataset revision / Binding revision
- plan SHA-256 / authorization reference（reference only）
- max seconds / peak memory MiB / output bytes
- total work units / retry external-or-paid表示
- cancel policy `AT_VERIFIED_CHECKPOINT`

`authority_effect`は`REQUEST_ONLY_NO_EXECUTION_AUTHORITY`固定であり、authorization referenceの存在を実行許可に読み替えない。同じidempotency keyとexact requestは既存recordを返し、異なるrequestとの再利用はfail closedとする。

## Lifecycle

```text
QUEUED -> RUNNING -> CHECKPOINTING -> RUNNING -> COMPLETED
   |         |              |          |
CANCELLED    +----------> CANCELLING -> CANCELLED
             +----------> FAILED | RECOVERY_REQUIRED
```

Every mutation requires exact previous `state_revision`; progress and elapsed time cannot regress. Terminal progress uses only `complete`. A cancel after positive progress requires a verified checkpoint. Failure with a checkpoint becomes RECOVERY_REQUIRED; without one it is terminal FAILED. R5E snapshot is derived from the record, not a second mutable state.

## Resource enforcement

Observed elapsed seconds, peak memory and output bytes are checked against the immutable request ceiling. Any exceeded dimension creates stable `ERR_TASK054_RESOURCE_LIMIT`, stops safely and retains the last verified checkpoint when present. No hyperparameter, budget or retry is changed automatically.

## Process isolation

The launch boundary accepts only an absolute executable and bounded argument vector; it always uses `shell=False` and DEVNULL stdin/stdout/stderr. Windows adds `CREATE_NO_WINDOW`. Common secret-like argument forms are rejected. The child receives only an allowlisted minimal environment and cannot inherit API keys/password variables by default. Stop first requests terminate, then performs one bounded kill fallback.

## Canonical responsibility

R5F owns the TASK-054 in-process lifecycle and exact-idempotency registry. R5E owns presentation only. The process adapter owns OS launch/termination only. R6 owns any authorized model/runtime/training adapter. Durable restart/replay and real packaged-worker observations remain R7 acceptance work and are currently `NOT_CONFIRMED`; this is not hidden as PASS.

## Failure modes covered

- stale revision / invalid transition / progress or elapsed regression
- duplicate click with conflicting exact inputs
- positive-progress cancel without checkpoint
- time/memory/output ceiling breach
- duplicate active child process
- shell or console creation regression
- secret-bearing arguments/environment
- unresponsive child requiring bounded kill

## Verification and gates

Focused R5F + R5E tests use deterministic fake process/records. They do not start a real subprocess. Actual runtime acquisition, model execution, Dataset adoption, training, Provider/paid calls, promotion, Timeline/Resolve mutation, Product Activation, release and deploy remain Human-Gated.
