# TASK-014 D4 Three-Phase Runtime Contract R19

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-014`

Contract identity: `TASK014_D4_THREE_PHASE_RUNTIME_CONTRACT_R19_V1`

Bound design: `TASK074-R19-ACYCLIC-RUNTIME-AND-EXACT-FAILURE-V1`

## Contract boundary

TASK-014 separates source eligibility, dispatch authorization, receipt-only
preparation, live execution and POST publication. None may substitute for the
next.

### Phase A — pre-dispatch authorization

`TASK014_LOCAL_VOICE_CALL_CAPABILITY_V2` is structurally parent-authority-zero.
It has no reference-open/body-return/map/hash/copy/callback/path/URI surface.
Its one-use method:

```text
begin_dispatch(
    Task074DirectTransferOperationReadyCurrentV1,
    task075_consumer_identity
) -> Task014CallDispatchLeaseV2
```

binds the exact call profile, sink, Project, operation, consumer, TASK-074 V2
lease and `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1`. It runs before TASK-076 arm.
It authorizes no child creation by itself and no reference/script body, model,
sink write, WAV or publication effect.

### Phase B — child-bound receipt-only preparation

After exact `Task074DirectTransferChildPairReadyCurrentV1`,
`JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3` and
`JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3`, TASK-014 may use the already
bound dispatch lease to prepare the call/sink receipt-only session. It returns
only `TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1`. TASK-076 commits that truth into
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1` and
`JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3` before release.

Phase B does not read a reference body, load/call a model, write PCM/WAV or mint
a publication receipt. Failure or uncertainty follows the exact TASK-076 V3
prepare/abort graph; there is no second preparation.

### Phase C — release winner, execution and POST

Only exact `JOB_CHILD_STARTED_READBACK_V3` may enter authenticated TASK-075
consumer execution and use bounded script bytes plus the parent-owned sink.
TASK-075 result and sink terminal truth are outputs, never dispatch prerequisites.

POST minting is a later action requiring the exact TASK-075 result, exact
`Task074DirectTransferTerminalCurrentV1`, sink terminal truth and all TASK-014
publication prerequisites. Only TASK-014 publication write/readback can mint
`Task014NarrationPostLiveBoundCurrentV1` and body-free
`NarrationPublicationReceipt`.

## Source order and authority

The effect-zero restricted consumer/POST source unit requires only accepted
TASK-014/TASK-074 owner contracts and exact current TASK-074 effect-zero output.
It does not require an operation-ready, child-ready, terminal or TASK-075 result.

The pre-dispatch capability source, live receipt-only preparation source and
POST publisher are separate later allocations. Equal hashes, public mappings,
fixtures and R18's rejected `Task074DirectTransferLiveBoundCurrentV1` cannot
substitute for any R19 type.

## Acceptance mechanism

This file is immutable. Review and acceptance never edit it. After exact R19
review PASS, only a separately allocated TASK-014 owner writer may issue
`docs/ai-team/tasks/TASK-014/d4-r19-owner-acceptance.json` under R19's stable
envelope rules.

Until that envelope verifies: contract acceptance, source, private handle/body,
child/process, model, audio/WAV, publication and downstream PASS authority are
all `false`.
