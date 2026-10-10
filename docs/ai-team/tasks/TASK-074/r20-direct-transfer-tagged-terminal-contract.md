# TASK-074 R20 Direct-Transfer Tagged-Terminal Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-074`

Contract identity: `TASK074_DIRECT_TRANSFER_TAGGED_TERMINAL_CONTRACT_R20_V1`

Bound design: `TASK074-R20-RESERVATION-AND-TAGGED-TERMINAL-CLOSURE-V1`

## 1. Forward-only runtime types

### `Task074DirectTransferOperationReadyCurrentV1`

Minted after current route/reference, TASK-074 domain transaction, V2 lease
`ISSUED`, exact operation/ticket/consumer binding and one current
`TASK074_REFERENCE_BEGIN_ATTACHMENT_V1`. It binds the selected TASK-076
DISPATCHING generation, dispatch plan and metadata-only external binding slot.
It proves no child, transfer, body read, model or output effect. TASK-014 may use
it only to create `Task014DispatchReservationV1`; it never authorizes call
dispatch.

### `Task074DirectTransferChildPairReadyCurrentV1`

Minted only after selected TASK-076 V3 `IN_FLIGHT`, bootstrap
child/process/Job custody, exact two-role child transfer, both parent-original
close readbacks, `parent_sensitive_handle_count=0`, TASK-072 external-binding
record and authenticated external-input validation. It is before Artifact
prepare, TASK-014 call/sink entry and TASK-075 consumer entry/result.

## 2. Branch-specific terminal types

There is no generic positive terminal type. Exactly one sealed tagged branch
may win for an operation:

```text
Task074DirectTransferTerminalBranchV1 :=
    SUCCESS {
        Task074DirectTransferSuccessTerminalCurrentV1
    }
  | NONCURRENT {
        Task074DirectTransferNoncurrentTerminalCurrentV1
    }
  | ABORTED {
        Task074DirectTransferAbortedTerminalCurrentV1
    }
  | BURNED_UNKNOWN {
        Task074DirectTransferUnknownTerminalReadbackV1
    }
```

`SUCCESS` requires the exact TASK-075 result, TASK-014
`Task014SuccessResultBoundReadbackV1`, exact two-role worker remote close,
parent-handle count zero and V2 lease `CONSUMED`. It is the only branch accepted
by TASK-014 POST publication. It does not require POST or a TASK-076 terminal,
so the graph remains forward-only.

`NONCURRENT` requires exactly one
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`, TASK-014
`Task014NoncurrentFailedClosedReadbackV1`, exact child exit, two-role close and
lease terminal truth. It allows the existing TASK-076 terminal read only and
forbids TASK-075 result, `RESULT_BOUND`, D4 result and POST.

`ABORTED` requires one exact pre-release known terminal and any phase-required
TASK-014 terminal. It allows no TASK-075 result or POST. The exact known-no-child
set is closed:

- `JOB_CHILD_REJECTED_READBACK_V3` — pre-vector arm rejection;
- `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3` — unselected orphan, no process;
- `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3` — selected vector, no process;
- `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3` — atomic known-no-process create
  rejection with all five budgets terminal.

`JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` is also a known `ABORTED` terminal but
truthfully has `child_process_created=true` and therefore is never a
known-no-child result. Later phase or public observations cannot prove no child.

`BURNED_UNKNOWN` preserves TASK-074 R13
`FAILED_CLOSED / NOT_CONFIRMED`, exact role/handle truth as
`TRUE | FALSE | UNKNOWN`, and TASK-076 containment coordinates. It cannot be
converted to success, noncurrent, known abort or effect zero.

## 3. Producer and recovery boundary

TASK-074 owns exactly `REFERENCE_AUDIO_READ_HANDLE` then
`REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`. Both are read-only, non-inheritable,
non-exportable, one-use and share one V2 lease. TASK-014 parent
sensitive-handle authority is permanently zero.

TASK-074 `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` consumes the
TASK-043-owned `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_PORT_V1` and
exact TASK-043 readback. TASK-043 never mints TASK-074 domain truth.

Partial transfer preserves per-role accepted/closed truth. Unknown close or
terminal truth remains R13 `FAILED_CLOSED / NOT_CONFIRMED`, non-retireable and
non-replayable until exact R13 retirement conditions are met. TASK-076 separately
owns vector-wide `BURNED_UNKNOWN`; neither state aliases the other.

After restart, only the canonical DISPATCHING-current exact unselected-orphan
exception may invoke `abort_armed_orphan_job_child_v3`, whose CAS must prove
process-create was never entered, followed by the exact TASK-074 aborted
terminal join. An exact already-durable abort-pending claim may otherwise be
queried and finished. Selected/prebootstrap or later nonterminal state without
that durable claim becomes burned unknown plus containment; it cannot start a
new abort, bind, preflight, close, prepare, release or resume.

## 4. Acceptance mechanism

This file is immutable. Review and acceptance never edit it. After exact R20
review PASS, only a separately allocated TASK-074 owner writer may issue
`docs/ai-team/tasks/TASK-074/r20-owner-acceptance.json` under the exact R20
envelope rules.

Until that envelope verifies, contract acceptance, source, live broker/native,
private handle/body, model, audio/WAV, publication and downstream PASS authority
are all `false`.
