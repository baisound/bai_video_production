# TASK-074 R15 — TASK-014 Direct-Transfer Current-Main Amendment

Status: `DESIGN_ONLY / DEV-4 / EFFECT0 / SOURCE_START0`

Design identity: `TASK074-R15-TASK014-CHILD-LOCAL-DIRECT-TRANSFER-V1`

Current-main bind: `origin/main@b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`

Carrier: `codex/task-074-b-current-main-verification-closure-r1` at
`dd38e93f2f441bd0601659618958a212faafc6ed`.

## 1. Decision and scope

This amendment rebinds, but does not copy or merge, the required R14 producer
semantics to the current-main dependency graph. It is a genuine TASK-074
continuation: TASK-074 remains the sole private-reference producer/broker owner;
TASK-014 is only the restricted Local Primary consumer of the resulting live
delegation.

The invariant is fixed as
`TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`:

1. TASK-074 holds and transfers the two already-opened, pinned reference roles
   directly into its selected child-local broker.
2. TASK-014 has zero parent sensitive handles and permanently zero authority to
   open, read, map, hash, copy, serialize, log, retain, or reconstruct reference
   audio or transcript.
3. TASK-014 receives only the consumer-restricted, nonserializable live
   delegation/call binding; no public receipt, digest, path, callback, or
   reconstructed object can replace it.
4. The child is the first and only execution participant eligible to read the
   roles, after the exact TASK-072 begin and the exact TASK-074/TASK-076 custody
   sequence. This amendment itself does not create a child, body read, process,
   model action, audio output, Asset, Project mutation, or provider effect.

It preserves R14's direct two-role transfer, parent-handle-zero, child-only
body gate, failure/close matrix, and TASK-075 V2 terminal semantics as immutable
semantic requirements. Historical R14 files, their reviewed bytes, and their
old dependency hashes are Evidence only; they are not imported as current-main
authority.

## 2. Current dependency rebind

The following are the exact current-source observations. A row marked
`NOT_CONFIRMED` is not promoted by matching historical wording or an equal
digest.

| Owner | Current source/record | Current status | R15 use |
| --- | --- | --- | --- |
| TASK-014 | D4 design carrier `4dfd3a09e16f048e6d34024b8eaae3fbb6f37c25`, `d4-private-call-sink-completion-abi-design.md` | `DESIGN_ONLY / SOURCE_START0` | defines the required V2 contract and private call/sink boundary; no source capability exists |
| TASK-046 | `docs/ai-team/tasks/TASK-046/task.md` | recording/training/model/audio remain gated | semantic source/Consent/reference receipt must be current and producer-issued; its public projection never authorizes transfer |
| TASK-066 | `docs/ai-team/tasks/TASK-066/task.md` | `OWNER_AUTHORIZED / P0 DESIGN_ACCEPTED / IMPLEMENTATION_ALLOCATED_BY_DEPENDENCY / NATIVE_PROOF_PENDING` | later compute proof is a live dependency only; no GPU/runtime action here |
| TASK-071 | `docs/ai-team/tasks/TASK-071/complete-design-packet.md` | `DESIGN_COMPLETE / DEV-4 / SOURCE_START0` | no live Human broker/ticket receipt is available |
| TASK-072 | no current-main TASK-072 task record or source owner implementation is present | `DEPENDENCY_NOT_CONFIRMED` | the required attachment-begin ABI is a named dependency, not an implementable local substitute |
| TASK-075 | `complete-design-packet.md` plus `r6-independent-design-review-receipt-v1.md` | packet remains `DESIGN_CANDIDATE_R6 / SOURCE_START0`; review receipt is effect-zero only | V2 pre-close/terminal ABI may be named but no consumer implementation/acceptance is available |
| TASK-076 | `docs/ai-team/tasks/TASK-076/complete-design-packet.md` | `DESIGN_COMPLETE / DEV-4 / SOURCE_START0` | selected V3 custody/readback is a future external-owner dependency only |

The current TASK-074 pure source does not satisfy this amendment by itself.
`owner_voice_private_reference.py` is explicitly metadata/state validation and
`owner_voice_private_reference_windows.py` is explicitly a nonnative fixture
trace; neither is a live private-reference broker. Their existing body-free
fixtures remain valid but cannot be widened, relabelled, or treated as a
direct-transfer implementation.

## 3. Required exact crosswalk

### 3.1 Begin and child custody

The only permitted forward sequence is:

```text
TASK-074 V2 reference lease = ISSUED
  -> TASK074_REFERENCE_BEGIN_ATTACHMENT_V1 (one private attachment)
  -> selected TASK-076 V3 = DISPATCHING with exact external binding slot
  -> issue_and_arm_job_child_v3
  -> TASK072_JOB_CHILD_ARMED_READBACK_V3 for that same child/job/operation
  -> TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1
  -> TASK-074 lease = IN_FLIGHT_PARENT_DELEGATION
  -> selected TASK-076 V3 = IN_FLIGHT / exact child custody readback
  -> TASK-074 direct two-role child transfer
  -> CHILD_PAIR_READY (parent sensitive handle count = 0)
  -> body-free child preflight
  -> TASK-075 consumer entry
  -> only then child body-read start
```

`TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1` may occur only after the selected
TASK-076 `DISPATCHING` slot, `issue_and_arm_job_child_v3`, and exact
`TASK072_JOB_CHILD_ARMED_READBACK_V3` for the same child/job/operation. It then
atomically consumes the exact attachment, advances the same TASK-074 V2 lease,
and enables—not aliases—the selected TASK-076 `IN_FLIGHT` transition. Its
private readback must bind operation, consumer, nonce, reference-delegation
lease, selected child, arm readback, and Task076 custody identity. A missing,
stale, copied, different, or public equivalent attachment/readback has effect
zero. TASK-014 cannot call the ABI, provide a callback, or obtain any reference
role; it can only be bound by the TASK-074 broker after all preceding proofs are
current.

The R14 semantic records retain their role as required future descriptors:
`TASK074_REFERENCE_CHILD_ROLE_SET_V1`,
`TASK074_REFERENCE_CHILD_SHARED_LEASE_POLICY_V1`,
`TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1`, and
`TASK074_REFERENCE_CHILD_BOUND_READBACK_V1`. The two roles are exactly
`REFERENCE_AUDIO_READ_HANDLE` and `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`, in
that order, read-only, non-inheritable, non-exportable, and leased together.
Successful bind requires two accepted child roles, confirmed parent closure,
closed child body gate until admission, and `parent_sensitive_handle_count=0`.

### 3.2 TASK-014 restricted consumer binding

The broker emits no `open_reference_audio`, `open_reference_transcript`, raw
handle, URI, path, body digest capable of reconstruction, or generic body-return
method. It binds the selected TASK-014 live consumer only to the exact
`TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2` identity, one call profile,
one operation, one selected child/worker identity, and the sealed Task072/076
lineage. TASK-014's D4 private call/sink can receive worker output through the
fixed TASK-075 channel; it never receives reference input authority.

No direct replacement is allowed: a public TASK-046 receipt, TASK-074 snapshot,
TASK-072 ticket/digest, TASK-075 result, copied live object, deserialized
mapping, same fields, callback, inherited handle, or caller-selected process is
not a consumer binding.

### 3.3 Noncurrent terminal path

For same-snapshot compute/network noncurrentness after release, the exact path
is:

```text
TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2
  -> one current TASK-074 owner terminal close with parent/child role truth
  -> TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2
  -> one selected TASK-076 V3 terminal
```

The exact fourth terminal-consumer argument is
`TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1` **bound to** the exact
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`; the JOB receipt alone is not
a fourth argument and cannot be relabelled as one. That bound TASK-014 result
then joins the exact V2 pre-close/terminal path only as specified by the
TASK-014 D4 design. V1 final-union input, split/multiple pre-close arms, generic
terminal receipt, JOB-receipt-only substitution, copied digest, automatic
re-dispatch, or a fabricated TASK-014 result is rejected.

## 4. Required failure and close truth

The semantic R14 matrix is re-bound to the following non-negotiable outcomes:

| Case | Required outcome |
| --- | --- |
| attachment/begin rejected before child creation | attachment and V2 lease burn/fail closed; child/body/model/consumer effect zero |
| partial direct transfer or parent-close proof missing | never `CHILD_PAIR_READY`; preserve per-role truth and use only exact Task072 abort or containment path |
| foreign/extra/reordered/writable/inheritable role | reject before preflight; no role retry or new child |
| parent reference body open/read after atomic begin | reject and burn/fail closed; body/model/Artifact/consumer entry zero |
| stale/mixed Task046/066/071/072/075/076 input | next forward edge zero; no currentness refresh, rebind, or replacement ticket |
| crash/reply loss after begin, bind, close, or terminal edge | query exactly the same durable operation/generation; no replay/second transfer; unresolved truth remains failed closed or not confirmed |
| post-release compute/network drift | one V2 pre-close arm, one owner terminal close, one V2 terminal union, one Task076 terminal; no V1 input or split winner |

All public diagnostics remain body-free and omit paths, handles, voice identity,
credentials, source media, transcript, and private channel material.

## 5. R15 acceptance and source-start gate

R15 is accepted only after independent DEV-4 Critic, Tester, and Judge review
the exact current-main bind with unresolved `Critical/High = 0/0`. It must prove:

1. R14 semantic requirements are retained without copying historical hashes as
   current authority;
2. every table in section 2 is individually current, missing, or gated exactly
   as recorded; no `NOT_CONFIRMED` dependency is silently substituted;
3. the Task014 D4 V2 contract, Task072 attachment begin, Task075 V2 terminal
   union, and selected Task076 V3 custody are one non-circular crosswalk;
4. parent read/handle authority is structurally zero after atomic begin and
   TASK-014 is consumer-restricted; and
5. the failure/close rows preserve no-retry, body-free, per-role truth.

This document starts no source work. A future TASK074-C source amendment may
begin only after a fresh main/currentness rebind supplies canonical TASK-046,
066, 071, 072, 075, and 076 receipts **and** the canonical accepted TASK-014 D4
completion identity for the exact V2 direct-transfer consumer port, including
its compatible POST and terminal crosswalk version. The current TASK-014 D4
carrier is design-only Evidence and cannot satisfy that condition. Until its
accepted identity is available, TASK074-C is `DEPENDENCY_NOT_CONFIRMED` with
effect zero. The gate also requires exact cross-owner owner locks and Allowed
Files, an accepted R15 review identity, a clean dedicated worktree, and a
separate implementation allocation. No future source allocation may include
TASK-014/072/075/076-owned files.

## 6. Allowed and prohibited effects

This R15 unit changes only this design document. It must not modify source,
schema, tests, `task.md`, TASK-014/072/075/076 documents or source,
`current-state.md`, task-index, roadmap, CHANGELOG, historical branch contents,
or any native/provider/model/audio/Project/Production state.

Its validation is static document scope and independent review only. It neither
creates nor observes private reference bodies, a broker, a ticket, a child
process, a model runtime, WAV data, or a Product receipt.
