# TASK-014 D4 Coordinated Closure Contract R24

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-014`

Contract identity: `TASK014_D4_COORDINATED_CLOSURE_CONTRACT_R24_V1`

Bound design: `TASK074-R24-BRANCH-PREDICATE-AND-POST-RELEASE-RECOVERY-V1`

## 1. Durable reservation coordinator

`Task014DispatchReservationV1` is sealed, metadata-only and nonserializable. It
binds one Project, operation, ticket, consumer, selected DISPATCHING generation,
`JOB_DISPATCH_PLAN_V3`, TASK-074 attachment/V2 lease,
`TASK076_EXTERNAL_BINDING_SLOT_V1`, call profile and parent sink coordinate. It
contains no script/reference body, handle, callback, path, child, process,
model, call/sink session, WAV or publication authority.

The separately accepted four-owner amendment
`TASK014_TASK072_TASK075_TASK076_COORDINATED_PREARM_RESERVATION_AMENDMENT_V1`
must freeze this durable state machine:

```text
RESERVED
  -> CANCEL_PENDING
       -> CANCELLED_KNOWN
       -> CANCEL_UNKNOWN
  -> ARMING
       -> JOIN_PENDING
            -> ARMED_CONSUMED
            -> ARM_REJECTED
            -> ARM_UNKNOWN
```

Wrong/foreign/cross-operation inputs fail before mutation and leave RESERVED.
Same-operation expiry, currentness loss or owner cancel uses `CANCEL_PENDING`;
silence or absence cannot cancel it. Only one TASK-014 owner CAS may claim
`CANCEL_PENDING` or `ARMING`.

The future TASK-072 coordinator persists the matching arm-attempt identity and
whether canonical TASK-076 call entry occurred. Its owner-authenticated query
returns exactly one sealed variant:

```text
NOT_ENTERED_KNOWN
| JOB_CHILD_ARMED_READBACK_V3
| JOB_CHILD_REJECTED_READBACK_V3
| JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
| ATTEMPT_TRUTH_UNKNOWN
```

The coordinator has exact monotonic microstates:

```text
CLAIM_INTENT
  -> TASK014_CLAIMED
  -> ARM_CALL_ENTERING
  -> TASK076_RESULT_OBSERVED
  -> JOINED
```

`CLAIM_INTENT` is durable before the TASK-014 `RESERVED -> ARMING` CAS and
contains its random one-use claim identity. A failure before that CAS observes
RESERVED and closes through cancel/no-vector. A failure after the CAS observes
the same claim identity in ARMING; absence of `ARM_CALL_ENTERING` is exact
`NOT_ENTERED_KNOWN`. Once `ARM_CALL_ENTERING` is durable, absence of a TASK-076
result is attempt-truth-unknown, never inferred not-entered. This ordering closes
the cross-owner gap without a second arm call.

For `NOT_ENTERED_KNOWN`, the future TASK-076 owner method
`close_prearm_without_vector_v1` consumes the exact coordinator proof and issues
one `JOB_CHILD_REJECTED_READBACK_V3` with
`budget_vector_created=false`, process/child/effect zero. It neither invokes nor
retries arm. For `ATTEMPT_TRUTH_UNKNOWN`, only the TASK-076 owner may issue the
same-operation `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`; TASK-014 cannot
synthesize it.

`ARMING` is persisted before the unchanged canonical arm call. `JOIN_PENDING`
is persisted after an owner query observes a TASK-076 result and before the
TASK-014 terminal CAS. Failure/reply loss at every point performs only the exact
query and one terminal join:

```text
ARMED_CONSUMED  <-> JOB_CHILD_ARMED_READBACK_V3
ARM_REJECTED    <-> JOB_CHILD_REJECTED_READBACK_V3
ARM_UNKNOWN     <-> JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
CANCELLED_KNOWN <-> JOB_CHILD_REJECTED_READBACK_V3
CANCEL_UNKNOWN  <-> JOB_CHILD_BURNED_UNKNOWN_READBACK_V3
```

No terminal is written before the owner-issued TASK-076 partner exists. The arm
call is never invoked twice. Exact current readers join the immutable coordinator
and both owner stores; missing/forked/ambiguous/broken truth is noncurrent and
authorizes only containment.

## 2. Prepare coordinator and continuity context

After child-pair-ready and before TASK-076 prepare claim, TASK-014 persists
metadata-only `Task014ReceiptOnlyPrepareReservationV1` in `PREPARE_RESERVED`.
The future adapter persists `PREPARE_CLAIM_ENTERING`, passes that exact
reservation identity together with the unchanged
`FIXED_RECEIPT_ONLY_DECLARATION_V1` only inside its private coordinator, then
calls `claim_job_child_artifact_prepare_v3` with the unchanged declaration.
Exact pending advances the coordinator through `PREPARE_PENDING_OBSERVED` to
`PENDING_CLAIMED`. This all occurs before `begin_dispatch`, sink open or any
call/sink session. The same pending prepare continuation is retained by the
future four-owner
`TASK014_TASK072_TASK075_TASK076_RECEIPT_ONLY_PREPARE_TERMINAL_AMENDMENT_V1`.

```text
PREPARE_RESERVED
  -> PREPARE_CLAIM_ENTERING
       -> PREPARE_PENDING_OBSERVED
            -> PENDING_CLAIMED
       -> PREPARE_NOT_WON
       -> PREPARE_CLAIM_UNKNOWN

PENDING_CLAIMED
  -> NEVER_ENTERED
  -> SESSION_ENTERED
       -> RECEIPT_ONLY_PREPARED
       -> FAILED_CLOSED
       -> BURNED_UNKNOWN

RECEIPT_ONLY_PREPARED
  -> RELEASED_RUNNING
       -> RESULT_BOUND
       -> FAILED_CLOSED
       -> BURNED_UNKNOWN
  -> PRE_RELEASE_ABORTED
```

Every operation has exactly one
`Task014PrepareContinuityContextV1` value:

```text
NO_PREPARE_RECOVERY_EVENT
| LIVE_CONTINUATION_INTERRUPTION
| RESTART_CLASS_LOSS
```

`NO_PREPARE_RECOVERY_EVENT` is owner-read exact only when the coordinator chain
shows uninterrupted forward execution and no recovery-class transition. It is
not inferred from missing evidence. `LIVE_CONTINUATION_INTERRUPTION` means the
original broker, worker and accepted private prepare continuation remain live
and identity-equal; only caller reply, coordinator write or delivery was
interrupted. No process was restarted and no private continuation was
reconstructed. `RESTART_CLASS_LOSS` means Product, broker, worker, adapter or
coordinator process restart, worker replacement, or any loss/uncertainty of the
original private continuation. A restarted component can never claim the live
class. Missing, foreign, forked, ambiguous or broken continuity evidence is
`RESTART_CLASS_LOSS`, never no-event or live.

`LIVE_CONTINUATION_INTERRUPTION` alone may recover an interrupted pending
observation: it uses exact same-vector TASK-076 query plus the retained prepare
reservation, and the still-live adapter advances to
`PREPARE_PENDING_OBSERVED`, then `PENDING_CLAIMED`. This query/rejoin step is
never used by `NO_PREPARE_RECOVERY_EVENT`.

After either (a) uninterrupted forward execution has already durably reached
`PENDING_CLAIMED` under `NO_PREPARE_RECOVERY_EVENT`, or (b) the live-interruption
query has rejoined that same state, the exact original live continuation may
issue owner-sealed `NEVER_ENTERED` without starting a session and may enter the
section 3 abort-wait path. `PREPARE_NOT_WON` binds an exact abort-pending or other
known prepare-claim result. `PREPARE_CLAIM_UNKNOWN` binds only exact TASK-076
burned unknown. No prepare claim is invoked twice.

For pre-release `RESTART_CLASS_LOSS`, canonical TASK-075 section 9.3.1 controls.
If exact durable pre-restart `JOB_CHILD_ABORT_PENDING_READBACK_V3` exists,
recovery may only query and finish that same claim. Otherwise PREPARE_PENDING,
PREPARED, PREPARE_FAILED or RELEASE_REJECTED becomes exact TASK-076-owner
`JOB_CHILD_BURNED_UNKNOWN_READBACK_V3` and
`contain_burned_unknown_job_child_v3` only. TASK-014 may append only a body-free
`Task014RestartContainedUnknownFactV1` preserving its latest durable
reservation/session/prepare facts as `TRUE | FALSE | UNKNOWN`. It must not mint
`NEVER_ENTERED`, start or reconstruct a session, initiate abort-wait, prepare,
commit, release or normal owner close.

## 3. Live abort-wait and complete pre-release abort mapping

While `PENDING_CLAIMED` and the exact original live continuation exists, an
abort winner may make canonical TASK-076 `PREPARE_IN_PROGRESS` return. This is
legal for both an ordinary uninterrupted abort under
`NO_PREPARE_RECOVERY_EVENT` and a `LIVE_CONTINUATION_INTERRUPTION` after its
exact pending query/rejoin. It is never legal for `RESTART_CLASS_LOSS`. The
canonical call returns
`JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3`. That continuation then issues
owner-sealed `Task014ReceiptOnlyPrepareNeverEnteredReadbackV1`, converts it
through the accepted adapter into exact TASK-076-owner
`JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1`, and invokes
`commit_job_child_artifact_prepare_v3` with `PREPARE_WITH_ABORT_WAIT`. Only that
commit may return exact `JOB_CHILD_ABORT_PENDING_READBACK_V3`.

After `SESSION_ENTERED`, successful TASK-014 preparation returns
`Task014ReceiptOnlyPreparedEvidenceV1`. The accepted adapter validates its
owner/currentness and issues exact
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`; that canonical TASK-076 type,
not the TASK-014 evidence, is passed to prepare commit. Known TASK-014 failure
durably fail-closes call/sink and yields exact TASK-076-owner known-no-create.
Unknown preparation/close truth yields vector-wide burned unknown.

If abort-wait races a live preparation, the same retained continuation must
finish one exact prepared or known-no-create truth and commit it with
`PREPARE_WITH_ABORT_WAIT`; there is no second prepare or abort. Any restart or
loss of that continuation follows section 2 restart-class containment and may
not resume this path.

| Exact observation | TASK-014 action | TASK-076 action |
| --- | --- | --- |
| live pending, session never entered, abort requested | owner `NEVER_ENTERED` readback | `PREPARE_IN_PROGRESS -> ABORT_WAIT -> PREPARE_WITH_ABORT_WAIT(known-no-create) -> ABORT_PENDING` |
| live pending, session entered, known preparation failure | durable TASK-014 `FAILED_CLOSED` | same live abort-wait continuation commits known-no-create -> abort-pending |
| live pending, receipt-only preparation succeeds while abort waits | `Task014PreReleaseAbortedReadbackV1` preserving prepared truth | same live continuation commits canonical receipt-only -> abort-pending |
| exact `JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3`, live cancel/currentness loss before release | `Task014PreReleaseAbortedReadbackV1` | `AFTER_PREPARE -> ABORT_PENDING`, then owner/session close and abort commit |
| exact live release-rejected readback | `Task014PreReleaseAbortedReadbackV1` | `AFTER_RELEASE_REJECTED -> ABORT_PENDING`, then close and abort commit |
| pre-release restart class with exact pre-restart abort-pending | no new close; preserve durable facts | exact-query/finish that same claim only |
| pre-release restart class without exact pre-restart abort-pending | restart-contained unknown fact only | burned-unknown containment only; no fresh abort or owner close |
| any Task014 close/prepare/commit truth uncertain | preserve known facts plus `UNKNOWN` fields | TASK-076 burned-unknown containment only |

Bind/preflight failure before pending has no Task014 prepare attempt or session.
Every exact live abort-pending claim alone authorizes TASK-074 reference-role
close; then TASK-072 terminates/waits and commits the canonical
bootstrap-aborted readback. Reply recovery is same-event query-only.

## 4. Post-release restart recovery is not pre-release containment

`JOB_CHILD_STARTED_READBACK_V3` marks release already won and is excluded from
the pre-release restart rule. After restart, TASK-014 starts no new call/sink,
model, result, POST or owner-close action. The fixed child exits. Only the
separately accepted TASK-075 section 9.7.2 same-event noncurrent terminal union,
with the exact already durable TASK-014 terminal truth and exact TASK-074 owner
truth, may complete post-release Job terminal recovery.

If the required live TASK-014 terminal never became durable, its truth is
`UNKNOWN` and TASK-076 burned-unknown/global containment is the fallback. There
is no arm-only call, D4 result, reattach, resume, second child, model retry,
sink retry, POST retry or reconstructed TASK-014 session. Existing durable
result/result-bound/POST facts, if any, remain immutable provisional facts.

## 5. Provisional local facts are not global terminals

After release, TASK-014 may persist owner-local facts without selecting the
global operation branch:

- `Task014SuccessResultBoundFactV1` for an exact canonical success result;
- `Task014NoncurrentFailedClosedFactV1` for the exact noncurrent union path;
- `Task014PostWriteFactV1` with write/readback truth
  `TRUE | FALSE | UNKNOWN`.

These facts are immutable and never relabelled. `RESULT_BOUND` remains true if a
later Job terminal is unknown. A written POST remains true even if it cannot be
made current. Unknown later closure adds containment facts; it does not replace
known success/result/close facts with a contradictory earlier-state terminal.

The exact TASK-075 success predicate required everywhere is:

```text
outcome = SUCCESS
terminal_stage = RESULT_VERIFIED
reason_codes = []
sample_rate_hz = 48000
channels = 1
sample_format = PCM_S24LE
frame_count > 0
child_count = 1
generation_attempt_count = 1
waveform_count = 1
waveform_sha256, sink_write_result_sha256 and
output_handle_identity_sha256 are exact non-null current values
```

The complete canonical stage-field matrix, same-operation currentness and
authenticated live callback must also verify. `FAILED_KNOWN` and `UNKNOWN` are
type errors for result-bound, POST, publication-current and TASK-041 PASS,
regardless of matching hashes or fields.

## 6. POST candidate and publication-current

TASK-014 may write/readback a body-free `NarrationPublicationReceipt` candidate
only from `Task014SuccessResultBoundFactV1` plus exact
`Task074DirectTransferSuccessCloseFactV1` and all publication prerequisites.
This write is a durable local fact, not yet a positive current read.

Only exact global `Task074DirectTransferSuccessClosedCurrentV1`, matching
`JOB_CHILD_TERMINAL_READBACK_V3`, exact
`TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1`, latest intact owner chain
and the full success predicate may mint sealed
`Task014NarrationPublicationCurrentReadV1`.

Exact global `Task074DirectTransferContainedPartialTruthCurrentV1` returns
`Task014NarrationPublicationContainmentCurrentReadV1`, which preserves result,
result-bound, POST write/readback, role-close, lease, Job-terminal and retirement
truth independently as `TRUE | FALSE | UNKNOWN`. It is non-PASS and has no
conversion to publication-current. Missing, stale, revoked, foreign, forked,
ambiguous or broken-chain state is likewise noncurrent.

## 7. Acceptance mechanism

This file is immutable. After exact R24 review PASS, only a separately allocated
TASK-014 owner writer may issue
`docs/ai-team/tasks/TASK-014/d4-r24-owner-acceptance.json` under R24's exact
envelope rules. The two four-owner amendments, source and runtime remain
separately gated.

Until those gates verify, contract acceptance, source, child/process, private
handle/body, model, audio/WAV, publication-current and downstream PASS authority
are all false.
