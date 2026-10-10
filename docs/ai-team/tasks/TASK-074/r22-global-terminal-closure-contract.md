# TASK-074 R22 Global Terminal Closure Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-074`

Contract identity: `TASK074_GLOBAL_TERMINAL_CLOSURE_CONTRACT_R22_V1`

Bound design: `TASK074-R22-RESTART-SPLIT-AND-REACHABLE-CONTAINMENT-V1`

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
same-operation currentness. Known facts never become false because a later join
is uncertain.

## 3. Exactly-one global terminal with branch-specific prerequisites

A one-winner TASK-074 owner CAS selects at most one branch. A retry after lost
reply exact-queries that same slot and never issues another CAS. Branch
prerequisites are disjoint; there is no common requirement for exact TASK-076
terminal or exact TASK-074 retirement before the containment branch.

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

Those three known-closed branches alone require exact Job-terminal and exact
retirement inputs. They are rejected if any required join is `FALSE | UNKNOWN`.

## 4. Reachable containment branch

`CONTAINED_PARTIAL_TRUTH` is selected when any late POST, Job-terminal, owner
terminal or retirement join is `FALSE | UNKNOWN`, or when restart-class loss
without an exact pre-restart abort-pending claim yields TASK-076 burned unknown.
It requires all of the following, rather than exact positive terminal/retirement:

1. the latest intact TASK-074 global-terminal slot and one-winner owner CAS;
2. owner-authenticated same-operation current reads for every owner store that
   remains readable, plus an explicit `UNKNOWN` field and last durable coordinate
   for each unreadable/missing/ambiguous upstream join;
3. all durable provisional owner facts available before containment;
4. separate `TRUE | FALSE | UNKNOWN` values for POST, Job-terminal, owner
   terminal, retirement, lease, role-close, child/process/effect/exit and
   TASK-014 session/prepare truth; and
5. exact TASK-076/TASK-074 containment observation binding the same Project,
   operation, ticket, generation and vector when a vector exists.

The branch preserves independently:

- intended predecessor branch `SUCCESS | NONCURRENT | ABORTED | UNKNOWN`;
- exact TASK-075 result and result-bound truth when present;
- POST write/readback truth `TRUE | FALSE | UNKNOWN`;
- per-role transfer/remote-close and parent-handle facts;
- V2 lease fact including already durable `CONSUMED`;
- child/process/effect/exit truth;
- TASK-076 terminal and TASK-074 retirement truth;
- continuity class `LIVE_CONTINUATION_INTERRUPTION | RESTART_CLASS_LOSS`; and
- containment observation.

An unavailable upstream read does not block this branch; it is represented as
`UNKNOWN`. Unavailability or uncertainty of the TASK-074 global-terminal slot
itself does not authorize a new mint: it returns owner-store
`NOT_CONFIRMED`, permits containment actions only and forbids retry until exact
same-slot readback resolves the CAS truth.

Containment never rewrites or discards a durable result, POST or close fact,
never claims effect zero when an effect is true/unknown, and has no edge to
result, POST, publication-current, retry, new owner close or downstream PASS.

## 5. Known abort and no-child set

The exact known-no-child set is closed:

1. `JOB_CHILD_REJECTED_READBACK_V3`;
2. `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`;
3. `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3`;
4. `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`.

`JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` is known-aborted but truthfully has a
created process and is excluded from no-child. Public, absent, later-phase or
unknown observations cannot prove no child.

## 6. Producer, restart and recovery boundary

TASK-074 owns exactly the one-use read-only audio then transcript reference
roles under one V2 lease. TASK-014 parent sensitive-handle authority is zero.
TASK-074 domain truth consumes the TASK-043-owned transaction port/readback;
TASK-043 never mints TASK-074 truth.

Unknown close remains R13 `FAILED_CLOSED / NOT_CONFIRMED`; TASK-076 separately
owns vector `BURNED_UNKNOWN`. Partial transfer preserves per-role facts.

`LIVE_CONTINUATION_INTERRUPTION` and `RESTART_CLASS_LOSS` have the exact meanings
in the bound TASK-014 contract and are mutually exclusive. After Product,
broker, worker, adapter or coordinator restart, worker replacement, or any loss
of the original private prepare continuation:

- only a DISPATCHING-current exact unselected orphan may use
  `abort_armed_orphan_job_child_v3`, whose CAS proves process-create was never
  entered, followed by the exact aborted close/global join;
- an exact durable pre-restart abort-pending claim may be queried and finished
  as that same claim only; and
- every selected/prebootstrap or later nonterminal state without that durable
  abort-pending becomes TASK-076 burned-unknown and reachable
  `CONTAINED_PARTIAL_TRUTH` only.

Restart never starts owner `NEVER_ENTERED`, abort-wait, normal owner close, bind,
preflight, prepare, commit, release, resume or retry. Known terminal vectors are
query-only. Missing continuity evidence is restart-class loss.

## 7. Acceptance mechanism

This file is immutable. After exact R22 review PASS, only a separately allocated
TASK-074 owner writer may issue
`docs/ai-team/tasks/TASK-074/r22-owner-acceptance.json` under R22's exact
envelope rules.

Until that envelope verifies, contract acceptance, source, live broker/native,
private handle/body, model, audio/WAV, publication-current and downstream PASS
authority are all false.
