# TASK-074 R21 Global Terminal Closure Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-074`

Contract identity: `TASK074_GLOBAL_TERMINAL_CLOSURE_CONTRACT_R21_V1`

Bound design: `TASK074-R21-COORDINATED-CLOSURE-AND-LATE-TRUTH-V1`

## 1. Forward runtime phases

`Task074DirectTransferOperationReadyCurrentV1` binds one current Project,
operation, ticket, consumer, V2 lease `ISSUED`, begin attachment, selected
DISPATCHING plan and metadata-only external binding slot. It proves no child,
transfer, body, model or output effect and enables only TASK-014 reservation.

`Task074DirectTransferChildPairReadyCurrentV1` requires selected V3 IN_FLIGHT,
bootstrap child/process/Job custody, exact two-role child transfer, both parent
original closes, parent sensitive-handle count zero and validated external
input. It is before Artifact prepare, TASK-014 session and TASK-075 execution.

## 2. Owner-local close facts are provisional

These immutable facts do not select a global terminal branch:

- `Task074DirectTransferSuccessCloseFactV1` requires the full canonical
  TASK-075 success predicate, TASK-014 `Task014SuccessResultBoundFactV1`, exact
  two-role remote close, parent-handle count zero and V2 lease `CONSUMED`. It
  enables only a TASK-014 POST candidate.
- `Task074DirectTransferNoncurrentCloseFactV1` requires exactly one
  `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`, exact TASK-014 durable
  fail-close, child exit, role closes and lease terminal truth. It forbids
  TASK-075 result, `RESULT_BOUND`, D4 result and POST.
- `Task074DirectTransferAbortedCloseFactV1` requires the exact pre-release V3
  terminal, phase-correct TASK-014 closure if a session existed, role-close and
  lease facts. It forbids TASK-075 result and POST.

The success fact rejects `FAILED_KNOWN` and `UNKNOWN`. It requires
`outcome=SUCCESS`, `terminal_stage=RESULT_VERIFIED`, empty reasons,
48000/mono/PCM_S24LE, positive frame count, one child/generation/waveform, exact
non-null waveform/sink/output identities, the canonical stage matrix and
same-operation currentness.

Known facts never become false because a later join is uncertain.

## 3. Exactly-one global terminal after all late joins

Only after the applicable TASK-076 terminal vector/readback and exact TASK-074
R13 retirement observation may the owner select one global branch:

```text
Task074DirectTransferGlobalTerminalCurrentV1 :=
    SUCCESS_CLOSED {
        Task074DirectTransferSuccessClosedCurrentV1
    }
  | NONCURRENT_CLOSED {
        Task074DirectTransferNoncurrentClosedCurrentV1
    }
  | ABORTED_CLOSED {
        Task074DirectTransferAbortedClosedCurrentV1
    }
  | CONTAINED_PARTIAL_TRUTH {
        Task074DirectTransferContainedPartialTruthCurrentV1
    }
```

`SUCCESS_CLOSED` requires the success close fact, TASK-014 POST write/readback
`TRUE`, exact matching `JOB_CHILD_TERMINAL_READBACK_V3` and exact
`TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1`. It alone enables TASK-014
publication-current.

`NONCURRENT_CLOSED` requires the noncurrent close fact, exact TASK-076 terminal
from the noncurrent union, exact retirement and POST `FALSE`.

`ABORTED_CLOSED` requires the aborted close fact, exact phase terminal vector,
exact retirement and POST `FALSE`.

`CONTAINED_PARTIAL_TRUTH` is selected when a late POST, Job-terminal, owner
terminal or retirement join is `FALSE | UNKNOWN`. It preserves independently:

- intended predecessor branch `SUCCESS | NONCURRENT | ABORTED | UNKNOWN`;
- exact TASK-075 result and result-bound truth when present;
- POST write/readback truth `TRUE | FALSE | UNKNOWN`;
- per-role transfer/remote-close and parent-handle facts;
- V2 lease fact including already durable `CONSUMED`;
- child/process/effect/exit truth;
- TASK-076 terminal and TASK-074 retirement truth;
- containment observation.

It never rewrites or discards a durable result, POST or close fact, never claims
effect zero when an effect is true/unknown, and has no edge to result, POST,
publication-current, retry or downstream PASS.

## 4. Known abort and no-child set

The exact known-no-child set is closed:

1. `JOB_CHILD_REJECTED_READBACK_V3`;
2. `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`;
3. `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3`;
4. `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`.

`JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` is known-aborted but truthfully has a
created process and is excluded from no-child. Public, absent, later-phase or
unknown observations cannot prove no child.

## 5. Producer and recovery boundary

TASK-074 owns exactly the one-use read-only audio then transcript reference
roles under one V2 lease. TASK-014 parent sensitive-handle authority is zero.
TASK-074 domain truth consumes the TASK-043-owned transaction port/readback;
TASK-043 never mints TASK-074 truth.

Unknown close remains R13 `FAILED_CLOSED / NOT_CONFIRMED`; TASK-076 separately
owns vector `BURNED_UNKNOWN`. Partial transfer preserves per-role facts.

After restart, only a DISPATCHING-current exact unselected orphan may use
`abort_armed_orphan_job_child_v3`, whose CAS proves process-create was never
entered, followed by the exact aborted close/global join. An already durable
abort-pending claim may otherwise be queried and finished. Known terminal
vectors are query-only. Selected/prebootstrap or later nonterminal state without
durable abort-pending becomes containment-only; no new abort, bind, prepare,
release, resume or owner close begins.

## 6. Acceptance mechanism

This file is immutable. After exact R21 review PASS, only a separately allocated
TASK-074 owner writer may issue
`docs/ai-team/tasks/TASK-074/r21-owner-acceptance.json` under R21's exact
envelope rules.

Until that envelope verifies, contract acceptance, source, live broker/native,
private handle/body, model, audio/WAV, publication-current and downstream PASS
authority are all false.
