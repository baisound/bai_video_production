# TASK-074 Complete Design Packet R11 Addendum

Status: `DESIGN_CANDIDATE_R11_ADDENDUM / DEV-4 / SOURCE_START0 / EFFECT0 / NOT_REVIEWED`

## 1. Parent freeze and precedence

The effective R11 design is the following immutable chain plus the current authority record:

- R9 packet `complete-design-packet.md` SHA-256 `4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0`;
- R10 addendum `complete-design-packet-r10-addendum.md` SHA-256 `EF9CEA3DF0B4C86ABC0A2198E45F08A368DB0E50A99231744A81BA6014131364`;
- this R11 addendum;
- current `task.md`, whose prior R9 SHA-256 `265ECB0C95CF5459BB611FE5C4E50068C35EFB8DAF57BBE200EE42D1B08F7D65` is historical review input and no longer the current authority hash。

R11 supersedes only the R10 V2 lease/lifecycle integration、child Job custody/abort proof and TASK-072 begin-order clauses. Every unrelated R9/R10 contract remains unchanged. This addendum records no Critic、Tester or Judge PASS and creates no implementation、source、native process、private-audio、commit or Production authority.

## 2. V2 lease integration with R9 section 5.5 and N40

### 2.1 Typed domain

`CapabilityLeaseV2` is the R10 closed enum:

`ISSUED | IN_FLIGHT_PARENT_DELEGATION | CHILD_TRANSFER_IN_FLIGHT | CHILD_PAIR_READY | BODY_READ_STARTED | CONSUMED | BURNED | FAILED_CLOSED`。

It is a different typed namespace from R9 `CapabilityLease` V1. A V1 value、string alias or public receipt cannot satisfy a V2 tuple. R11's table applies whenever a V2 capability identity exists or any R10/R11 attachment、delegation or V2 execution input is requested. `V2_LEASE_ABSENT` below means cardinality zero and is not an enum value. A prepared reference without a V2 lease remains non-executable for G11 and cannot mint an attachment or V2 input.

### 2.2 Complete delta table

This table is the complete V2 delta to R9 section 5.5. The R9 `RetainedObject` sets remain typed and exact. A V2 tuple、cardinality or guard not listed here is rejected by R9 N40.

| ReferenceLifecycle (`RL`) | CapabilityLeaseV2 | RetainedObject (`RO`) | Exact guard |
|---|---|---|---|
| `UNBOUND` | `V2_LEASE_ABSENT` | `NONE` | initial identity; V2 lease count zero |
| `PREPARE_PLANNED` | `V2_LEASE_ABSENT` | `NONE` | exact R9 plan/Human/ticket guard; V2 lease count zero |
| `PREPARING` | `V2_LEASE_ABSENT` | `NONE｜ALLOCATED｜ENCRYPTED_UNPUBLISHED` | exact R9 prepare operation/currentness; V2 lease count zero |
| `PREPARE_FAILED_NO_DERIVATIVE` | `V2_LEASE_ABSENT` | `NONE｜PURGED` | exact R9 failure/no-retained-object readback; V2 lease count zero |
| `PREPARE_FAILED_RETAINED` | `V2_LEASE_ABSENT` | `RECONCILIATION_REQUIRED｜RECOVERABLE_RETAINED｜KEY_REVOKED｜FOREIGN_PRESERVED` | exact R9 failed operation/retained ledger; V2 lease count zero |
| `PREPARED` | `ISSUED` | `PUBLISHED` | exact prepared/custody pair readback、current G13/trusted time、parent owns both originals、one current V2 capability and unconsumed attachment budget |
| `PREPARED` | `IN_FLIGHT_PARENT_DELEGATION` | `PUBLISHED` | exact `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1` consumed by the same atomic TASK-072 begin、current begin nonce/private delegation handle、parent body gate permanently closed |
| `PREPARED` | `CHILD_TRANSFER_IN_FLIGHT` | `PUBLISHED` | previous V2 state plus exact current TASK-076 child/Job custody readback、handshake/body gate closed、transfer begun under the one delegation handle |
| `PREPARED` | `CHILD_PAIR_READY` | `PUBLISHED` | both child-local roles verified、both parent originals close-read back、exact child/Job custody still current、body read count zero |
| `PREPARED` | `BODY_READ_STARTED` | `PUBLISHED` | exact `CHILD_PAIR_READY` predecessor plus one winning TASK-075 child-local body-start CAS、both role readers under one lease |
| `PREPARED` | `CONSUMED` | `PUBLISHED` | exact two-role read completion、both child handles terminal-closed and TASK-075 consumer terminal readback |
| `PREPARED` | `BURNED` | `PUBLISHED` | exact known failure/revoke/abort readback、all parent/child handles closed、replay zero |
| `PREPARED` | `FAILED_CLOSED` | `PUBLISHED` | failure/close truth incomplete but every authority gate closed; evidence retained、replay zero、no success claim |
| `REVOKE_PENDING` | `IN_FLIGHT_PARENT_DELEGATION` | `PUBLISHED` | revoke/expiry won RL CAS after atomic begin; no child creation/progress may start and exact abort is required |
| `REVOKE_PENDING` | `CHILD_TRANSFER_IN_FLIGHT` | `PUBLISHED` | revoke/expiry won RL CAS during transfer; body gate closed、exact abort/remote-close required |
| `REVOKE_PENDING` | `CHILD_PAIR_READY` | `PUBLISHED` | revoke/expiry won before body-start CAS; body start count zero、exact child abort/close required |
| `REVOKE_PENDING` | `BODY_READ_STARTED` | `PUBLISHED` | body-start CAS won first; revoke blocks every later entry and waits for the one active lease terminal |
| `REVOKE_PENDING` | `CONSUMED` | `PUBLISHED` | active lease reached exact consumed/closed terminal; finalize-only guard |
| `REVOKE_PENDING` | `BURNED` | `PUBLISHED` | exact burn/close terminal readback; finalize-only guard |
| `REVOKE_PENDING` | `FAILED_CLOSED` | `PUBLISHED` | authority zero and exact terminal classification/readback attempt complete; finalize-only guard without PASS inference |
| `REVOKED` | `V2_LEASE_ABSENT` or `CONSUMED｜BURNED｜FAILED_CLOSED` | `PUBLISHED｜KEY_REVOKED｜PURGED｜FOREIGN_PRESERVED` | no V2 lease ever existed or exact revoke/expiry terminal readback from `PREPARED｜REVOKE_PENDING`; no nonterminal lease |
| `PURGE_PENDING` | `V2_LEASE_ABSENT` or `CONSUMED｜BURNED｜FAILED_CLOSED` | `RECOVERABLE_RETAINED｜PUBLISHED｜KEY_REVOKED` | exact R9 non-foreign purge predecessor/new Human receipt/ownership recovery; no nonterminal lease |
| `PURGED` | `V2_LEASE_ABSENT` or `CONSUMED｜BURNED｜FAILED_CLOSED` | `PURGED` | exact R9 key/ciphertext/directory readbacks; no nonterminal lease |
| `PURGE_NOT_CONFIRMED` | `V2_LEASE_ABSENT` or `CONSUMED｜BURNED｜FAILED_CLOSED` | `RECOVERABLE_RETAINED｜PUBLISHED｜KEY_REVOKED｜FOREIGN_PRESERVED` | exact R9 incomplete/foreign readback; `FOREIGN_PRESERVED` terminal and no nonterminal lease |

No V2 lease is permitted in `PREPARING` or either failed-preparation state. `REVOKED`、`PURGE_PENDING`、`PURGED` and `PURGE_NOT_CONFIRMED` permit cardinality zero or exactly one terminal V2 lease only. All R9 RL/RO predecessor and purge guards continue to apply in addition to this table.

### 2.3 Revoke/expiry arbitration

- At `RL=PREPARED / CLV2=ISSUED`, attachment consume/begin and revoke/expiry use one broker/domain CAS fence. If revoke/expiry wins, it atomically burns `ISSUED` and commits `PREPARED -> REVOKED`; attachment/begin/child/model counts remain zero.
- If atomic begin wins `ISSUED -> IN_FLIGHT_PARENT_DELEGATION`, any later revoke/expiry commits `PREPARED -> REVOKE_PENDING`, freezes the next V2 lease edge and enters exact abort/close.
- The same `PREPARED -> REVOKE_PENDING` rule applies during `CHILD_TRANSFER_IN_FLIGHT`、`CHILD_PAIR_READY` and `BODY_READ_STARTED`.
- At `CHILD_PAIR_READY`, revoke and child body-start share one winner fence. If revoke wins, `BODY_READ_STARTED` count is zero; if body-start wins, revoke enters `REVOKE_PENDING` and waits for that one lease terminal.
- `REVOKE_PENDING` finalizes to `REVOKED` only after exact terminal V2 lease and parent/child/remote-close readbacks. Unknown close remains fail-closed and never authorizes purge or success by inference.

## 3. Exact dedicated child Job custody

### 3.1 `TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1`

Before child-handle transfer and again immediately before any abort, TASK-076 must issue a fresh private readback binding:

- exact Project、Job、operation、attachment、TASK-072 begin、child process and expected current TASK-076 head;
- a dedicated one-operation Windows Job object whose membership is exactly the expected child and whose active-process count is exactly `1`;
- exact member process creation identity/time and pinned process-handle identity, not PID equality;
- `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE=true`;
- active-process limit exactly `1`;
- breakaway and silent-breakaway both disabled;
- the sole Job handle is noninheritable and held only by the TASK-076 producer broker;
- producer custody proves no duplicate Job handle、no inherited handle and an exact last-handle-close contract;
- exact installed instance、Windows user/session/logon/token、image physical identity、signature/hash/build and worker protocol/channel;
- `handshake_only=true` and `body_gate=CLOSED` until R10 `CHILD_PAIR_READY`。

The readback is live/private and cannot be reconstructed from a Job name、PID、count、public receipt or copied hash. Membership other than expected-child-one, active count other than one, an unknown duplicate handle or any limit/custody mismatch is `JOB_CUSTODY_NOT_PROVEN`.

### 3.2 Abort ownership and post-readback

`TASK076_EXACT_CHILD_JOB_ABORT_READBACK_V1` binds the exact pre-abort custody readback、abort request、winner、Job-handle action、pinned process wait/exit identity、remote audio/transcript handle-close proof and terminal TASK-072/TASK-076 coordinates.

If sole custody、no duplicate and last-handle semantics are all proven, TASK-076 may close its sole Job handle as kill authority, wait on the separately pinned expected-child process handle and return the post-abort readback. If any Job custody fact is unproven, Job close is not kill authority: the trusted producer terminates only the expected child through its already-pinned process handle, waits for that exact process exit, proves remote role closure, and only after exit closes/preserves the Job handle according to producer recovery. PID lookup、name search、broad Job close or termination of an extra/unrelated member is forbidden.

Abort success requires both fresh pre-abort membership/custody readback and post-abort exact child-exit/remote-close readback. Missing either leaves `FAILED_CLOSED / NOT_CONFIRMED`; it never fabricates effect zero after body start.

## 4. `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1`

### 4.1 Attachment creation

At exact `RL=PREPARED / CLV2=ISSUED`, TASK-074 may create one private live `TASK074_REFERENCE_BEGIN_ATTACHMENT_V1`. It binds the V2 capability/lease、reference pair、Project/Profile/Consent/currentness、semantic operation、expected TASK-072 ticket/profile、expected TASK-076 Job/worker plan、parent broker session、consumer/build/protocol and a broker-generated attachment nonce. State is exactly `ISSUED | CONSUMED | BURNED | FAILED_CLOSED`; terminals have no outgoing edge.

The attachment is noncopyable、nonserializable、nonpickleable、restart-invalid and contains no body、path、PID、native/raw handle value or public bearer secret. Exactly one attachment may exist for one V2 lease; creating a second、cross-operation use or public reconstruction is authority zero.

### 4.2 Atomic TASK-072 begin

TASK-072 must accept the owner-amended `TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1`. Its one serialized begin transaction:

1. revalidates exact current ticket、attachment、V2 lease `ISSUED`、RL/RO tuple、G13/trusted time and expected child plan;
2. consumes the exact attachment;
3. commits the TASK-072 begin event/nonce;
4. CASes the same V2 lease `ISSUED -> IN_FLIGHT_PARENT_DELEGATION`, permanently closing parent body entry;
5. returns one private nonserializable delegation handle plus the exact begin nonce and body-free begin readback。

These facts have one transaction outcome. Success is `attachment=CONSUMED` plus current TASK-072 begin plus CLV2 `IN_FLIGHT_PARENT_DELEGATION`; every other combination is invalid. Begin rejection、partial commit、reply loss、broker crash or unknown CAS burns/fails the attachment and lease, authorizes no child creation and produces body/model effect zero. It is never repaired by replay or a copied nonce.

TASK-076 child creation and `TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1` must bind the same attachment identity/digest、begin nonce、private delegation-handle identity、operation and V2 lease lineage. `TASK074_TO_TASK075_EXECUTION_INPUT_V2` must bind that same lineage and the final child process readback. Cross-attachment、cross-begin、cross-child or cross-operation joining is rejected before transfer/body/model access.

## 5. Acceptance additions

| ID | Acceptance |
|---|---|
| A40 | The complete RL × CapabilityLeaseV2 × RO × guard delta is bound to R9 N40; every nonlisted V2 tuple/cardinality/guard is rejected. |
| A41 | Revoke/expiry and attachment/begin/transfer/pair-ready/body-start have one CAS winner, exact `REVOKE_PENDING` semantics and terminal-readback-only finalize. |
| A42 | The child is the sole member of one dedicated kill-on-close/no-breakaway/active-limit-one Job with producer sole noninheritable last-handle custody, or Job close grants kill authority zero. |
| A43 | TASK-074 one-use attachment is consumed by one atomic TASK-072 begin that also advances the V2 lease, and TASK-076/V2 input bind the same attachment/begin/process lineage. |

## 6. Negative additions

| ID | Condition | Required result |
|---|---|---|
| N56 | any RL × CLV2 × RO tuple/cardinality/guard is absent from section 2.2, including V2 lease in preparing/failed state or nonterminal lease after revoke/purge | R9 N40 reject; authority/effect zero |
| N57 | Job membership is not exact expected child one, active count is not one, kill-on-close/active-limit/no-breakaway differs, or process identity mismatches | no transfer and no Job-close kill authority |
| N58 | Job handle is inheritable、duplicated、not producer-sole/last, or custody proof is missing/stale | use only pinned expected-process terminate/wait fallback; unrelated kill zero; G11 remains open |
| N59 | attachment missing、copied、replayed、wrong ticket/operation/reference/lease/consumer or second attachment exists | TASK-072 begin/child/body/model zero; attachment/lease burned as applicable |
| N60 | TASK-072 begin、TASK-076 child/readback or V2 input binds a different attachment、begin nonce、delegation handle、process or operation lineage | reject before transfer/body/model; replay zero |
| N61 | abort lacks fresh pre-membership/custody or post child-exit/remote-close readback, or caller PID/name/broad Job close is requested | no abort-success/effect-zero claim; `FAILED_CLOSED / NOT_CONFIRMED`; unrelated kill zero |

## 7. Fault additions

| ID | Crash/race seam | Required recovery truth |
|---|---|---|
| F33 | revoke/expiry races atomic attachment begin at `PREPARED/ISSUED` | one CAS winner: revoke burns and commits REVOKED with child/model zero, or begin commits parent-delegation and revoke enters REVOKE_PENDING; never both |
| F34 | atomic begin commits but TASK-076 child creation or handshake/custody readback fails | attachment remains consumed、lease burns/fails closed、exact abort readback required、child/body/model effect zero、new begin/replay zero |
| F35 | abort-time Job readback shows extra member、duplicate/unknown handle or custody drift | do not use Job close; terminate/wait only the pinned expected child、prove exit/remote close、preserve unrelated member、terminal remains N.C. if proof incomplete |
| F36 | revoke/expiry races transfer、pair-ready or body-start, or crash loses abort post-readback | transition to REVOKE_PENDING, freeze next edge; pair-ready revoke winner gives body-start zero; terminal readback finalizes REVOKED, otherwise FAILED_CLOSED/N.C. and replay zero |

## 8. Effective verification and freeze gate

The effective matrix totals are A01-A43、N01-N61 and F01-F36 with no duplicates. Required deterministic tests must cover every V2 table row and one-outside negative, ISSUED revoke-vs-begin both winners, transfer/pair/body revoke races, exact-child-one versus extra member, duplicated/inheritable Job handle, pinned-process fallback with unrelated kill zero, attachment missing/cross/replay, begin-to-child failure and missing abort post-readback.

R11 design completion requires fresh independent Tester、Critic and Judge over the exact current task hash、R9 packet hash、R10 addendum hash and R11 addendum hash, with C/H `0/0` and Judge PASS. TASK-072、TASK-076 and TASK-075 owner acceptances remain separate G11 requirements. This addendum performs source/schema/test/native/process/private-audio/model/commit/push/PR effects zero.
