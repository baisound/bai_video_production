# TASK-074 R19 Direct-Transfer Runtime Phases Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-074`

Contract identity: `TASK074_DIRECT_TRANSFER_RUNTIME_PHASES_R19_V1`

Bound design: `TASK074-R19-ACYCLIC-RUNTIME-AND-EXACT-FAILURE-V1`

## Three non-substitutable runtime types

### `Task074DirectTransferOperationReadyCurrentV1`

Minted before TASK-014 dispatch only after current route/reference, TASK-074
domain transaction, V2 lease `ISSUED`, exact operation/ticket/consumer binding
and one current `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1`. It binds no child and
proves no transfer, body read, model or output effect. It is consumed once by
TASK-014 `begin_dispatch` and TASK-076 arm lineage.

### `Task074DirectTransferChildPairReadyCurrentV1`

Minted only after selected TASK-076 V3 `IN_FLIGHT`, bootstrap child/process/Job
custody, exact two-role child transfer, both parent-original close readbacks,
`parent_sensitive_handle_count=0`, TASK-072 external binding record and
authenticated external-input validation. It is minted before Artifact prepare,
TASK-075 consumer entry or result. It enables only receipt-only preparation and
the next TASK-076 vector stages; it does not authorize body/model execution.

### `Task074DirectTransferTerminalCurrentV1`

Minted only after exact TASK-075/TASK-076 terminal union, per-role remote close,
TASK-074 lease terminal/retirement currentness and same-operation readback. It
is an input to TASK-014 POST publication only and cannot authorize dispatch,
transfer, retry or a second child.

R18's rejected `Task074DirectTransferLiveBoundCurrentV1` is not an R19 type and
cannot satisfy any phase.

## Producer boundary

TASK-074 owns exactly `REFERENCE_AUDIO_READ_HANDLE` then
`REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`. Both are read-only, non-inheritable,
non-exportable, one-use and share one V2 lease. TASK-014 parent sensitive-handle
authority is permanently `0`.

TASK-074 `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` consumes the
TASK-043-owned `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_PORT_V1` and
exact `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_READBACK_V1`; TASK-043
never mints TASK-074 domain truth.

Partial transfer preserves per-role accepted/closed truth. Unknown TASK-074
close/terminal truth remains `FAILED_CLOSED / NOT_CONFIRMED`, non-retireable and
non-replayable under R13. TASK-076 may separately own vector-wide
`BURNED_UNKNOWN`.

## Acceptance mechanism

This file is immutable. Review and acceptance never edit it. After exact R19
review PASS, only a separately allocated TASK-074 owner writer may issue
`docs/ai-team/tasks/TASK-074/r19-owner-acceptance.json` under R19's stable
envelope rules.

Until that envelope verifies: contract acceptance, source, live broker/native,
private handle/body, model, audio/WAV, publication and downstream PASS authority
are all `false`.
