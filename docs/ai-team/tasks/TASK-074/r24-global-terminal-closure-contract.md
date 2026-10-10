# TASK-074 R24 Global Terminal Closure Contract

Status: `IMMUTABLE_CONTRACT_CANDIDATE / OWNER_ACCEPTANCE_NOT_ISSUED / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Owner: `TASK-074`

Contract identity: `TASK074_GLOBAL_TERMINAL_CLOSURE_CONTRACT_R24_V1`

Bound design: `TASK074-R24-BRANCH-PREDICATE-AND-POST-RELEASE-RECOVERY-V1`

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
  TASK-075 result, `RESULT_BOUND`, D4 result and POST write; its global POST
  observation is therefore exact `FALSE`.
- `Task074DirectTransferAbortedCloseFactV1` requires the exact pre-release V3
  terminal, phase-correct TASK-014 closure if a session existed, role-close and
  lease facts. It forbids TASK-075 result and POST write; its global POST
  observation is therefore exact `FALSE`.

The success fact rejects `FAILED_KNOWN` and `UNKNOWN`. It requires
`outcome=SUCCESS`, `terminal_stage=RESULT_VERIFIED`, empty reasons,
48000/mono/PCM_S24LE, positive frame count, one child/generation/waveform, exact
non-null waveform/sink/output identities, the canonical stage matrix and
same-operation currentness. Known facts never become false because a later join
is uncertain.

## 3. Deterministic predecessor kind and expected join vectors

One atomic TASK-074 owner snapshot derives exactly one `predecessor_kind`:

```text
SUCCESS
| NONCURRENT
| ABORTED
| UNKNOWN
```

`SUCCESS`, `NONCURRENT` or `ABORTED` requires exactly one corresponding valid
owner-local close fact and forbids either other close fact. No valid close fact,
multiple facts, a fork, stale/foreign fact or broken chain gives `UNKNOWN`.

The complete expected join vector is branch-specific:

| `predecessor_kind` | required POST | required TASK-076 Job terminal | required TASK-074 retirement | eligible known-closed branch |
| --- | --- | --- | --- | --- |
| `SUCCESS` | `TRUE` | exact matching `TRUE` | exact matching `TRUE` | `SUCCESS_CLOSED` |
| `NONCURRENT` | `FALSE` | exact matching `TRUE` | exact matching `TRUE` | `NONCURRENT_CLOSED` |
| `ABORTED` | `FALSE` | exact matching `TRUE` | exact matching `TRUE` | `ABORTED_CLOSED` |
| `UNKNOWN` | any | any | any | none |

Each `TRUE` additionally means the exact owner-issued nominal readback with the
same Project, operation, ticket, generation/vector and predecessor. Boolean,
mapping, equal fields/hash, missing provenance or a mismatched terminal is not
exact `TRUE`.

## 4. Exactly-one global branch decision

A one-winner TASK-074 owner CAS selects at most one branch. The branch input is
one atomic snapshot containing `predecessor_kind` and every actual join value.
The decision function is exhaustive and ordered by exact predicate, not by
writer choice:

```text
if predecessor_kind == SUCCESS
   and POST == TRUE and Job-terminal == exact TRUE
   and retirement == exact TRUE:
       SUCCESS_CLOSED
else if predecessor_kind == NONCURRENT
   and POST == FALSE and Job-terminal == exact TRUE
   and retirement == exact TRUE:
       NONCURRENT_CLOSED
else if predecessor_kind == ABORTED
   and POST == FALSE and Job-terminal == exact TRUE
   and retirement == exact TRUE:
       ABORTED_CLOSED
else:
       CONTAINED_PARTIAL_TRUTH
```

No tuple can satisfy more than one row because `predecessor_kind` is exactly one
value and containment is only the complement of all three complete known-closed
predicates. A lost CAS reply exact-queries the same slot; it cannot choose again.

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

`SUCCESS_CLOSED` alone enables TASK-014 publication-current. `NONCURRENT_CLOSED`
and `ABORTED_CLOSED` preserve correct POST `FALSE`; that value never by itself
selects containment.

## 5. Total containment record

`CONTAINED_PARTIAL_TRUTH` requires all of the following:

1. the latest intact TASK-074 global-terminal slot and one-winner owner CAS;
2. the exact `predecessor_kind` and the failed/missing expected-vector fields;
3. owner-authenticated same-operation current reads for every owner store that
   remains readable, plus an explicit `UNKNOWN` field and last durable coordinate
   for each unreadable/missing/ambiguous upstream join;
4. all durable provisional owner facts available before containment;
5. separate `TRUE | FALSE | UNKNOWN` values for POST, Job-terminal, owner
   terminal, retirement, lease, role-close, child/process/effect/exit and
   TASK-014 session/prepare truth; and
6. exact TASK-076/TASK-074 containment observation binding the same Project,
   operation, ticket, generation and vector when a vector exists.

It preserves exactly one prepare continuity context:

```text
NO_PREPARE_RECOVERY_EVENT
| LIVE_CONTINUATION_INTERRUPTION
| RESTART_CLASS_LOSS
```

`NO_PREPARE_RECOVERY_EVENT` is the exact owner-read context for uninterrupted
forward execution with no prepare recovery-class transition, including an
ordinary late Job-terminal or retirement uncertainty. It is not inferred from
missing evidence. The other two meanings are fixed by the TASK-014 R24 contract.
Uncertain/missing continuity evidence is `RESTART_CLASS_LOSS`.

An unavailable upstream read does not block containment; it is represented as
`UNKNOWN`. Unavailability or uncertainty of the TASK-074 global-terminal slot
itself does not authorize a new mint: it returns owner-store `NOT_CONFIRMED`,
permits containment actions only and forbids retry until exact same-slot
readback resolves the CAS truth.

Containment never rewrites or discards a durable result, POST or close fact,
never claims effect zero when an effect is true/unknown, and has no edge to
result, POST, publication-current, retry, new owner close or downstream PASS.

## 6. Known abort and no-child set

The exact known-no-child set is closed:

1. `JOB_CHILD_REJECTED_READBACK_V3`;
2. `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`;
3. `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3`;
4. `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`.

`JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` is known-aborted but truthfully has a
created process and is excluded from no-child. Public, absent, later-phase or
unknown observations cannot prove no child.

## 7. Producer and pre-release restart boundary

TASK-074 owns exactly the one-use read-only audio then transcript reference
roles under one V2 lease. TASK-014 parent sensitive-handle authority is zero.
TASK-074 domain truth consumes the TASK-043-owned transaction port/readback;
TASK-043 never mints TASK-074 truth.

Unknown close remains R13 `FAILED_CLOSED / NOT_CONFIRMED`; TASK-076 separately
owns vector `BURNED_UNKNOWN`. Partial transfer preserves per-role facts.

After Product, broker, worker, adapter or coordinator restart, worker
replacement, or loss of the original private prepare continuation:

- only a DISPATCHING-current exact unselected orphan may use
  `abort_armed_orphan_job_child_v3`, whose CAS proves process-create was never
  entered, followed by the exact aborted close/global join;
- an exact durable pre-restart abort-pending claim may be queried and finished
  as that same claim only; and
- only selected prebootstrap, `BOOTSTRAP_WAITING`, `BOUND`, `BINDING_FAILED`,
  `VALIDATED`, `INPUT_FAILED`, `PREPARE_PENDING`, `PREPARED`, `PREPARE_FAILED`
  or `RELEASE_REJECTED` without that durable abort-pending becomes TASK-076
  burned-unknown and `CONTAINED_PARTIAL_TRUTH` only.

Those are pre-release states. Restart never starts owner `NEVER_ENTERED`,
abort-wait, normal owner close, bind, preflight, prepare, commit, release, resume
or retry. Known pre-release terminal vectors are query-only. Missing continuity
evidence is restart-class loss.

## 8. Post-release restart recovery

`JOB_CHILD_STARTED_READBACK_V3` is explicitly excluded from section 7's
pre-release burned-unknown set. After restart, the fixed child exits. Only the
separately accepted exact same-event
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1` defined by pinned TASK-075
section 9.7.2, plus exact already durable TASK-014 and TASK-074 owner truth, may
produce the matching Job terminal and continue through the deterministic branch
decision in section 4.

If the accepted union/amendments are absent, the fixed-child exit or required
TASK-014/TASK-074 truth is unknown, or the exact terminal cannot be read, the
fallback is TASK-076 burned unknown and `CONTAINED_PARTIAL_TRUTH`. There is no
arm-only call, new result, D4 result, reattach, resume, new owner close, second
child, model/sink retry or POST retry. Existing result/result-bound/POST/close
facts remain immutable and are preserved by containment.

## 9. Acceptance mechanism

This file is immutable. After exact R24 review PASS, only a separately allocated
TASK-074 owner writer may issue
`docs/ai-team/tasks/TASK-074/r24-owner-acceptance.json` under R24's exact
envelope rules.

Until that envelope verifies, contract acceptance, source, live broker/native,
private handle/body, model, audio/WAV, publication-current and downstream PASS
authority are all false.
