# TASK-014 D4 Reservation and Closed-Terminal Contract R20

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-014`

Contract identity: `TASK014_D4_RESERVATION_AND_CLOSED_TERMINAL_CONTRACT_R20_V1`

Bound design: `TASK074-R20-RESERVATION-AND-TAGGED-TERMINAL-CLOSURE-V1`

## 1. Pre-arm reservation is not call dispatch

TASK-014 may create one sealed `Task014DispatchReservationV1` after exact
`Task074DirectTransferOperationReadyCurrentV1` and before TASK-076 arm. The
reservation binds one Project, operation, ticket, consumer, selected
DISPATCHING generation, `JOB_DISPATCH_PLAN_V3`, TASK-074 attachment/V2 lease,
`TASK076_EXTERNAL_BINDING_SLOT_V1`, call profile and parent-owned sink
coordinate.

It is metadata-only and nonserializable. It contains no script/reference body,
handle, callback, path, URI, child, process, model, sink session, WAV or
publication authority. In particular it does not call TASK-014
`begin_dispatch`; canonical call dispatch remains after exact
`JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3`.

The future cross-owner contract
`TASK014_TASK072_TASK075_TASK076_PREARM_RESERVATION_ARM_ADAPTER_AMENDMENT_V1`
must be accepted independently by TASK-014, TASK-072, TASK-075 and TASK-076.
Its private TASK-072 adapter validates that the reservation, exact current
DISPATCHING readback, plan, private consumer inputs and external binding slot
all name the same immutable coordinates. It then atomically consumes the
reservation and invokes the unchanged canonical ABI:

```text
issue_and_arm_job_child_v3(
    EXACT_CURRENT_DISPATCHING_READBACK,
    JOB_DISPATCH_PLAN_V3,
    exact_private_consumer_inputs,
    TASK076_EXTERNAL_BINDING_SLOT_V1
)
```

The adapter returns exactly one tagged pair:

```text
ARMED {
    Task014DispatchReservationArmedConsumedReadbackV1,
    JOB_CHILD_ARMED_READBACK_V3
}
| ARM_REJECTED {
    Task014DispatchReservationArmRejectedReadbackV1,
    JOB_CHILD_REJECTED_READBACK_V3
}
| ARM_UNKNOWN {
    Task014DispatchReservationBurnedUnknownReadbackV1,
    JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
}
```

Wrong, stale, foreign or cross-operation inputs are rejected before mutation.
After the matching reservation CAS is entered, exception, cancellation, timeout
or reply uncertainty burns the reservation and can return only `ARM_UNKNOWN`.
Exact same-operation reply recovery queries the durable reservation state and
matching TASK-076 result; it never invokes arm twice. None of the three
reservation terminals is reusable.

The owner store returns sealed
`Task014DispatchReservationTerminalCurrentReadV1` only when the exact latest,
intact, predecessor-correct reservation record and its matching TASK-076 arm
outcome are current. Its closed states are
`ARMED_CONSUMED | ARM_REJECTED | BURNED_UNKNOWN`. A later operation-terminal
record may join this immutable reservation terminal but never rewrites it.

## 2. Call and sink begin only under Artifact-prepare pending

Only the exact conjunction below may begin TASK-014 call dispatch and the
parent-owned sink session:

- `Task014DispatchReservationArmedConsumedReadbackV1`;
- `Task074DirectTransferChildPairReadyCurrentV1`;
- `JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3`;
- `JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3`;
- one current TASK-014 call profile/sink coordinate for the same operation.

The one-use `begin_dispatch` and sink-open transition are inside one TASK-014
owner transaction. Its closed states are:

```text
PREPARE_OPEN
  -> RECEIPT_ONLY_PREPARED
  -> RELEASED_RUNNING
  -> RESULT_BOUND
  -> POST_CONSUMED

PREPARE_OPEN | RECEIPT_ONLY_PREPARED | RELEASED_RUNNING
  -> FAILED_CLOSED

any entered state with unknown durable truth
  -> BURNED_UNKNOWN
```

Successful preparation returns sealed
`TASK014_RECEIPT_ONLY_PREPARED_RESULT_R20_V1`. It has no body/model/audio
effect and is the exact receipt-only input to
`commit_job_child_artifact_prepare_v3`. A known preparation failure first
durably closes call and sink and returns
`Task014ReceiptOnlyPrepareFailedClosedReadbackV1`; the separately accepted
`TASK014_TASK072_TASK075_TASK076_RECEIPT_ONLY_TERMINAL_ADAPTER_AMENDMENT_V1`
may then create only the exact TASK-076
`JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1` for that retained operation. An
unknown TASK-014 close or prepare result requires vector-wide
`JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`; it cannot be translated to known
no-create or receipt-only prepared truth.

## 3. Exact failure closure after a session exists

Every branch is one-shot, queryable and bound to the same reservation,
operation, TASK-076 vector and TASK-074 lease:

| Observation | Required TASK-014 terminal | Required TASK-076 relation |
| --- | --- | --- |
| prepare abort wins before TASK-014 transaction enters | no call/sink session exists | exact `JOB_CHILD_ABORT_PENDING_READBACK_V3` or earlier known terminal |
| abort-wait races `PREPARE_OPEN` and preparation is known failed | `Task014ReceiptOnlyPrepareFailedClosedReadbackV1` | same pending lease commits known-no-create and resolves to exact abort-pending |
| abort-wait races a completed receipt-only preparation | `Task014PreReleaseAbortedReadbackV1` over exact prepared result | same pending lease commits receipt-only truth and resolves to exact abort-pending |
| bind/preflight/prepare failure before TASK-014 entry | no call/sink session exists | canonical phase-correct abort or known terminal |
| release is rejected after preparation | `Task014PreReleaseAbortedReadbackV1` | exact release-rejected -> abort-pending -> abort commit |
| release wins, then compute/network becomes noncurrent | `Task014NoncurrentFailedClosedReadbackV1` with durable call and sink `FAILED_CLOSED` | sole input to the exact noncurrent terminal branch |
| TASK-075 result wins | `Task014SuccessResultBoundReadbackV1` with call and sink `RESULT_BOUND` | sole input to the exact success branch |
| any Task014 terminal/close/reply truth is uncertain | `Task014BurnedUnknownReadbackV1` | TASK-076 burned-unknown containment only |

For an abort-wait, only the original live prepare continuation may commit the
same retained operation. A Product/broker restart cannot recreate it. An exact
already-durable abort-pending claim may be queried and finished; otherwise the
operation becomes burned unknown plus containment.

Same-event reply loss is query-only for reservation, preparation, fail-close,
result-bound and POST. A query never starts a call/sink session, closes a role,
releases a child, writes audio or publishes.

The owner store returns sealed
`Task014ReceiptOnlySessionTerminalCurrentReadV1` only for the exact latest,
intact session chain and one branch terminal below. Missing, stale, forked,
foreign, ambiguous or broken-chain state is a named noncurrent result. The
current reader performs no close, retry, body read, sink write or publication.

## 4. Four disjoint operation terminals

TASK-014 exposes sealed, non-convertible branch types:

1. `Task014SuccessResultBoundReadbackV1` — exact TASK-075 result, call and sink
   `RESULT_BOUND`; may proceed to POST only with TASK-074 success-terminal;
2. `Task014NoncurrentFailedClosedReadbackV1` — post-release noncurrent closure;
   cannot create a TASK-075 result or POST;
3. `Task014PreReleaseAbortedReadbackV1` — known pre-release closure; cannot
   create a TASK-075 result or POST;
4. `Task014BurnedUnknownReadbackV1` — uncertain closure; containment only.

Equal fields/hashes, mapping, copy, pickle, fixture, public JSON or a terminal
from another branch cannot substitute. `RESULT_BOUND` is accepted only by the
success branch. `FAILED_CLOSED` is accepted only by the noncurrent or aborted
branch with its exact predecessor.

## 5. POST and publication current read

Only `Task014SuccessResultBoundReadbackV1` plus exact
`Task074DirectTransferSuccessTerminalCurrentV1`, current publication
prerequisites and a successful TASK-014 owner write/readback may mint a
body-free `NarrationPublicationReceipt` and sealed
`Task014NarrationPublicationCurrentReadV1`. The current read binds the latest
intact owner chain, Project/timeline/item/policy, exact TASK-075 result,
TASK-074 success terminal, matching `JOB_CHILD_TERMINAL_READBACK_V3`, exact
`TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1` and publication
revision/head. A POST may already be durably written while either later
terminal is unavailable, but its owner read remains noncurrent and downstream
PASS remains impossible.

Noncurrent, aborted and burned-unknown branches have no POST edge. Missing,
stale, revoked, foreign, ambiguous, forked, broken-chain or non-latest
publication data returns a named non-PASS result and never a positive current
read.

## 6. Acceptance mechanism

This file is immutable. Review and acceptance never edit it. After exact R20
review PASS, only a separately allocated TASK-014 owner writer may issue
`docs/ai-team/tasks/TASK-014/d4-r20-owner-acceptance.json` under the exact R20
envelope rules. The four-owner pre-arm adapter amendment, four-owner
receipt-only terminal adapter amendment, source and runtime remain separately
gated.

Until those gates verify, contract acceptance, source, child/process, private
handle/body, model, audio/WAV, publication and downstream PASS authority are all
`false`.
