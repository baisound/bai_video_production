# TASK-074 Complete Design Packet R12 Addendum

Status: `DESIGN_CANDIDATE_R12_ADDENDUM / DEV-4 / SOURCE_START0 / EFFECT0 / NOT_REVIEWED`

## 1. Parent freeze and precedence

The effective R12 design is the following immutable chain plus the current authority record:

- R9 packet `complete-design-packet.md` SHA-256 `4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0`;
- R10 addendum `complete-design-packet-r10-addendum.md` SHA-256 `EF9CEA3DF0B4C86ABC0A2198E45F08A368DB0E50A99231744A81BA6014131364`;
- R11 addendum `complete-design-packet-r11-addendum.md` SHA-256 `CD73E8C6584C96B39D68C3A0D32E635DEC17EFC98145C7344779816400397690`;
- this R12 addendum;
- current `task.md`, whose pre-R12 SHA-256 `FFA0309D0BA908175482E06C07E5AAB3DF448B672B3F8ABF1F4531080669A9A8` is historical review input and no longer the current authority hash.

R12 supersedes only two R11 areas:

1. R11 sections 2.2 and 2.3 are supplemented and narrowed by the joint V1/V2 fence in sections 2 through 4 below. A V2-only tuple is never sufficient without the exact joint V1/V2 predecessor;
2. R11 fault F34 is replaced in full by R12 F34 in section 6. R11 F33 and F35-F36 remain unchanged.

Every unrelated R9/R10/R11 contract remains unchanged. R12 records no Critic, Tester or Judge PASS and creates no implementation, source, native process, private-audio, model, commit, push, PR or Production authority.

## 2. Joint V1/V2 lease authority

### 2.1 Closed typed namespaces

The following are distinct typed namespaces and cannot be converted by string, hash, mapping, receipt or public constructor:

- `CapabilityLeaseV1Current`: `NONE | ISSUED | IN_FLIGHT | BODY_READ_STARTED | CONSUMED | BURNED | FAILED_CLOSED`;
- `CapabilityLeaseV2Current`: `V2_ABSENT | ISSUED | IN_FLIGHT_PARENT_DELEGATION | CHILD_TRANSFER_IN_FLIGHT | CHILD_PAIR_READY | BODY_READ_STARTED | CONSUMED | BURNED | FAILED_CLOSED`.

`NONE` and `V2_ABSENT` are cardinality-zero current-state sentinels, not live capabilities. Historical terminal V1/V2 ledger entries remain immutable Evidence and are not current lease objects. No state name shared by the two enums establishes version equivalence.

`TASK074_REFERENCE_LEASE_VERSION_FENCE_V1` is the single broker-private durable CAS authority for one reference operation. It binds at least:

- exact Project, VoiceProfile, Consent, reference-pair, selection revision and semantic operation identities;
- current `ReferenceLifecycle` (`RL`) revision/head and current `RetainedObject` (`RO`) publication generation;
- current V1 lease identity/state, V1 live-handle count and latest terminal-history digest;
- current V2 lease identity/state, V2 live-handle count and latest terminal-history digest;
- broker/domain identity, process/session/build/protocol identity and trusted-time domain;
- revoke/expiry event identity and state;
- fence revision, predecessor digest, committed-event identity and self-hash.

The fence and its live-handle inventory are read under the same trusted broker/domain lock. A serialized projection is body-free audit Evidence only and cannot mint, retire, burn, revoke, execute or reconstruct a capability.

### 2.2 Exact V2 mint predecessor

The only state from which a V2 capability may be minted is the complete joint invariant:

```text
RL                    = PREPARED
current V1 state      = NONE
current V1 handle     = 0
current V2 state      = V2_ABSENT
current V2 handle     = 0
RO                    = PUBLISHED
revoke/expiry intent  = ABSENT
fence/readback        = current under one broker/domain CAS generation
```

Every conjunct is mandatory. `PREPARED` alone, `PUBLISHED` alone, a terminal V1 receipt, an empty public registry, process restart, missing file, caller assertion or equal hash cannot establish this predecessor.

### 2.3 Legacy V1 closure

After the R10/R12 protocol version is active, legacy V1 issuance is closed and non-executable:

- new V1 issuance count is always zero;
- a legacy current V1 `ISSUED` capability cannot advance to `IN_FLIGHT` or read a body. The broker may only burn/close it or consume an exact revoke/expiry transition;
- a legacy current V1 already at `IN_FLIGHT` or `BODY_READ_STARTED` cannot be rewound or converted to V2. It may only follow its original bounded recovery/terminal path. No new body/model edge is authorized;
- any nonterminal V1 state, any unknown V1 state or any V1 live-handle count other than the state-bound exact count makes V2 mint count zero;
- a V1 terminal (`CONSUMED | BURNED | FAILED_CLOSED`) with zero live handles is still not the V2 predecessor. The same broker must retain its immutable terminal evidence and CAS-retire the *current* V1 identity to `NONE/handle0` in a separate transaction;
- terminal retirement and V2 issuance are never combined. V2 issuance requires a fresh post-retirement fence readback;
- absence of a V1 file/receipt or a process restart never implies `NONE/handle0`.

For V1, `NONE` requires handle count zero; `ISSUED | IN_FLIGHT | BODY_READ_STARTED` require the exact one live capability owned by the current broker; every terminal requires handle count zero. Any mismatch is `FAILED_CLOSED / NOT_CONFIRMED`, not a repair or V2 migration opportunity.

### 2.4 Complete joint delta table

This table is the complete joint delta to R9 section 5.5, R9 N40 and R11 section 2.2. The R9/R11 guard for the named state still applies. Every tuple or outgoing edge not listed is rejected.

| RL | Current V1 / handles | Current V2 | RO | Only permitted next action |
|---|---|---|---|---|
| `UNBOUND | PREPARE_PLANNED | PREPARING | PREPARE_FAILED_NO_DERIVATIVE | PREPARE_FAILED_RETAINED` | `NONE / 0` | `V2_ABSENT` | exact R11 RO set | R9 preparation/reconciliation only; V1/V2 mint zero |
| `PREPARED` | `NONE / 0` | `V2_ABSENT` | `PUBLISHED` | one joint V2-issue versus revoke/expiry CAS from section 3 |
| `PREPARED` | `ISSUED / 1` | `V2_ABSENT` | `PUBLISHED` | legacy V1 burn/close or revoke; V1 execution and V2 mint zero |
| `PREPARED` | `IN_FLIGHT / 1` or `BODY_READ_STARTED / 1` | `V2_ABSENT` | `PUBLISHED` | exact legacy V1 terminal recovery; revoke enters `REVOKE_PENDING`; V2 mint zero |
| `PREPARED` | `CONSUMED / 0`, `BURNED / 0` or `FAILED_CLOSED / 0` | `V2_ABSENT` | `PUBLISHED` | separate exact V1-current retirement CAS to `NONE/0`; V2 mint zero in that transaction |
| `PREPARED` | `NONE / 0` | any R11 V2 nonterminal or terminal | `PUBLISHED` | only the exact R11 V2 edge for that state; V1 mint zero |
| `REVOKE_PENDING` | legacy V1 nonterminal with exact one handle | `V2_ABSENT` | `PUBLISHED` | freeze new entry, finish exact V1 terminal/close readback, then finalize revoke |
| `REVOKE_PENDING` | `NONE / 0` | exact R11 V2 nonterminal or terminal | `PUBLISHED` | exact R11 V2 abort/terminal/finalize path only |
| `REVOKED | PURGE_PENDING | PURGED | PURGE_NOT_CONFIRMED` | `NONE / 0` | `V2_ABSENT` or one exact terminal V2 | exact R11 RO set | R9/R11 terminal or purge path only; V1/V2 mint zero |

V1 and V2 cannot both be non-absent. A V1 current terminal and a V2 lease also cannot coexist. `current V1=NONE/handle0` is mandatory for every V2 row, including V2 terminal rows. Historical V1 terminal evidence remains separately addressable and never changes that current-state rule.

## 3. V2 issue versus revoke/expiry arbitration

### 3.1 One broker/domain CAS winner

`TASK074_REFERENCE_V2_ISSUE_OR_REVOKE_CAS_V1` is the sole transition from the section 2.2 predecessor. V2 issue, explicit revoke and trusted-time expiry all use the same broker, same domain lock, same fence revision and same compare-and-swap event namespace.

- If V2 issue wins, the CAS commits `current V2=ISSUED` while retaining `RL=PREPARED / current V1=NONE/handle0 / RO=PUBLISHED`. Only the broker-owned pending live capability associated with that exact CAS may subsequently be returned.
- If explicit revoke or expiry wins, the CAS commits `RL=REVOKED / current V2=V2_ABSENT / current V1=NONE/handle0`; V2 capability and handle creation count is zero. Retained-object key/purge transitions remain separate R9 operations.
- A loser observes a stale predecessor and performs no automatic retry, remint, time recalculation or alternate-version fallback. It must obtain a fresh typed readback and a fresh authorized operation where required.
- If revoke/expiry arrives after issue committed, R11 section 2.3 applies to the exact V2 state: `ISSUED` is atomically burned into revoke, while later active states enter `REVOKE_PENDING`. This is not a second winner for the initial CAS.

The broker may allocate an unpublished in-memory candidate before CAS, but it cannot expose it, duplicate it or count it as issued. If issue loss is proven, the broker closes that exact candidate and records no live V2 handle. If commit truth is not proven, it closes only the exact candidate it still owns, returns no authority and records the issuance/live-handle effect as `NOT_CONFIRMED` until authoritative fence readback; it never converts uncertainty into effect zero.

### 3.2 Typed outcome and reply-loss readback

The body-free private `TASK074_REFERENCE_V2_ISSUE_OR_REVOKE_READBACK_V1` returns one exact result:

- `V2_ISSUE_COMMITTED_DELIVERY_ACKNOWLEDGED`;
- `V2_ISSUE_COMMITTED_DELIVERY_NOT_CONFIRMED`;
- `REVOKE_COMMITTED`;
- `EXPIRY_COMMITTED`;
- `NO_COMMIT_STALE_PREDECESSOR`;
- `OUTCOME_NOT_CONFIRMED`.

It binds the request/operation identity, expected and committed fence revisions, predecessor/result digests, committed-event identity, trusted-time observation, broker/domain/session identity, V1/V2/handle cardinalities and the exact live-capability delivery acknowledgement when applicable.

Reply loss never authorizes replay:

- if issue commit is proven but live-capability delivery acknowledgement is absent, the exact unpublished/undelivered capability is burned and its handle is closed by the original broker. A later caller receives only `FAILED_CLOSED` Evidence and cannot retrieve or remint it;
- if revoke/expiry commit is proven, readback reports the already-committed event without executing it again;
- if no commit is proven, stale-predecessor is effect zero and requires a fresh operation decision;
- if exact outcome, handle closure or broker continuity is not proven, the result is `FAILED_CLOSED / NOT_CONFIRMED`; no capability may be returned, the actual issuance/live-handle effect remains `NOT_CONFIRMED`, and no public projection becomes authority.

Only the original in-flight call may receive the nonserializable live V2 capability, and only after commit readback plus delivery acknowledgement are bound in the same broker session. JSON, event digest, public receipt, copied object, restart or a repeated method call cannot reconstruct it.

## 4. Corrected child-creation and abort boundary

### 4.1 F34 is split by observed child creation truth

R11 F34 is superseded. A failed TASK-076 child creation/custody/handshake sequence must first resolve `child_created` as one of `PROVEN_FALSE | PROVEN_TRUE | NOT_CONFIRMED` from the exact spawn operation, pinned process-handle/Job evidence and TASK-072/TASK-076 operation lineage.

**Child not created (`PROVEN_FALSE`).** The readback must prove spawn did not commit, no child process handle or Job member ever existed, no child role/remote handle was transferred, the body gate remained closed and model invocation count is zero. Only then may the result claim child/body/model effect zero. No abort or wait is fabricated.

**Child created (`PROVEN_TRUE`).** A custody or handshake failure after creation is not child effect zero. The exact lifecycle is durably recorded and bounded:

```text
SPAWN_COMMITTED
-> ABORT_REQUESTED
-> EXIT_WAIT_STARTED
-> CHILD_EXITED
-> REMOTE_CLOSE_VERIFIED
-> ABORT_COMPLETE
```

Every transition binds the same operation, attachment, begin nonce, V2 lease, TASK-076 Job, pinned child creation identity/process handle and predecessor event. Abort uses R11 section 3.2: close the sole Job handle only when exact sole custody/last-handle authority is current; otherwise terminate/wait only through the already-pinned expected-child process handle. PID/name search, broad Job/process kill and an unrelated-member effect are forbidden.

The wait is bounded by the TASK-076 trusted timeout. `REMOTE_CLOSE_VERIFIED` means each expected remote audio/transcript role is independently `ABSENT_PROVEN` or `CREATED_THEN_CLOSED_VERIFIED`; silence or missing receipt is neither. `ABORT_COMPLETE` requires exact child exit, active expected-child count zero, no surviving exact child, that remote-role proof and no unrelated member affected. A crash or reply loss resumes only from the exact durable predecessor event; it does not spawn, abort or wait twice.

**Creation not confirmed (`NOT_CONFIRMED`).** The system does not infer child absence. It closes every authority/body gate it still controls, performs only an exact already-pinned-child recovery when such identity exists, and returns `FAILED_CLOSED / NOT_CONFIRMED`. It cannot claim child/body/model effect zero.

### 4.2 Body/model effect-zero proof

For a created child, `body_effect=0` and `model_effect=0` may be reported only when all of the following are proven together:

- TASK-072/TASK-076 body gate never opened and V2 never reached `BODY_READ_STARTED`;
- both child-local role read counts are zero;
- TASK-075 model admission/invocation-start count is zero;
- the exact child exited and no surviving child remains;
- each remote audio/transcript role is `ABSENT_PROVEN` or its handle close is verified;
- the bounded abort ledger reached `ABORT_COMPLETE` with current physical/process identity readback.

If body-gate history, remote close, model-start, child exit or any predecessor identity is missing, stale or ambiguous, the terminal is `FAILED_CLOSED / NOT_CONFIRMED`. Authority remains zero, but effect zero is not inferred. If body read or model start actually occurred, its exact observed effect is retained rather than relabeled as zero.

## 5. Acceptance and negative additions

### 5.1 Acceptance additions

| ID | Acceptance |
|---|---|
| A44 | One broker-private version fence binds RL, RO, current V1/state/handle count, current V2/state/handle count, revoke/expiry and one CAS generation; public projections create no authority. |
| A45 | The only V2 mint predecessor is exactly `PREPARED + current V1 NONE/handle0 + V2_ABSENT/handle0 + PUBLISHED + no revoke/expiry`, freshly read under the same broker/domain. |
| A46 | Legacy V1 issuance/execution is closed; any V1 nonterminal or handle-count mismatch makes V2 mint zero, and V1 terminal retirement to `NONE/0` is a separate exact CAS before a fresh V2 decision. |
| A47 | V2 issue and revoke/expiry have one same-broker/domain CAS winner; a loser has effect zero and no automatic retry, remint or version fallback. |
| A48 | Commit/reply-loss readback distinguishes issue delivered/not-confirmed, revoke, expiry, stale no-commit and unknown; no serialized Evidence reconstructs a capability. |
| A49 | Corrected F34 distinguishes child `PROVEN_FALSE`, `PROVEN_TRUE` and `NOT_CONFIRMED`; created-child failure records the bounded spawn-to-abort/wait lifecycle instead of claiming child effect zero. |
| A50 | A created child reaches abort success only after exact child exit, no-survivor and remote-close readbacks; PID/name/broad kill and unrelated effect remain zero. |
| A51 | Body/model effect zero after child creation requires closed body gate, read/model-start counts zero, exact exit and remote-close proof; otherwise the terminal is `FAILED_CLOSED / NOT_CONFIRMED`. |

### 5.2 Negative additions

| ID | Condition | Required result |
|---|---|---|
| N62 | V1 and V2 are both non-absent, a V1 current terminal coexists with V2, or a handle count disagrees with its state | reject joint tuple; new V2 mint/body/model entry zero; retain observed prior effects and mark unknown effects `NOT_CONFIRMED` |
| N63 | V2 issue is requested while V1 is `ISSUED`, `IN_FLIGHT`, `BODY_READ_STARTED`, unknown or has any live handle | V2 mint zero; preserve exact V1 burn/recovery/revoke path |
| N64 | caller requests new V1 issue, executes legacy V1 `ISSUED`, converts V1 to V2 or supplies a V1/public receipt as V2 | reject before body/model; no compatibility fallback |
| N65 | any exact mint predecessor conjunct is missing, stale or inferred from file/receipt absence, restart, equality or caller assertion | no V2 issue; fresh broker-private joint readback required |
| N66 | V1 terminal retirement and V2 issue are combined, or V2 issue uses the pre-retirement fence generation | stale/CAS reject; V2 mint zero |
| N67 | V2 issue and revoke/expiry use different broker/domain locks, split transactions, caller time or automatic loser retry | authority zero; no winner/success claim; `FAILED_CLOSED / NOT_CONFIRMED` if effects are ambiguous |
| N68 | reply loss is recovered by remint, a new lease identity, copied/readback JSON, hash, restart or second delivery | reject; burn/close exact undelivered capability; replay zero |
| N69 | child creation is unknown or spawn reply is lost but is classified as not-created | no effect-zero claim; exact spawn readback or `FAILED_CLOSED / NOT_CONFIRMED` |
| N70 | child was created but abort/wait/exit/no-survivor lifecycle is absent, out of order, stale or bound to another process | no abort-success; exact child effect retained; replay zero |
| N71 | created-child body/model effect zero is claimed without closed body-gate history, zero body/model-start counts or remote-close proof | reject Evidence; `FAILED_CLOSED / NOT_CONFIRMED` |
| N72 | created-child cleanup uses PID/name/broad Job close, affects an unrelated member or fabricates a missing wait/close event | operation fails closed; unrelated effect zero; no abort/effect-zero PASS |

## 6. Fault additions and F34 replacement

| ID | Crash/race seam | Required recovery truth |
|---|---|---|
| F34 (R12 replacement) | atomic begin commits, then TASK-076 child creation/custody/handshake fails or its reply is lost | first resolve `PROVEN_FALSE | PROVEN_TRUE | NOT_CONFIRMED`; false proves no child and effect zero, true records bounded spawn->abort/wait->exit->remote-close with no surviving child, unknown remains `FAILED_CLOSED / NOT_CONFIRMED`; body/model zero only with section 4.2 proof; begin/attachment/V2 replay zero |
| F37 | legacy V1 terminalization/handle close/retirement races a V2 issue request | stale joint fence rejects V2; exact V1 terminal and history are preserved; only a later fresh `NONE/0` readback may enter a new V2 decision |
| F38 | V2 issue races explicit revoke or trusted-time expiry at the exact mint predecessor, including CAS response loss | one same-domain CAS winner; exact outcome readback reports issue/revoke/expiry/no-commit/unknown; no dual winner, remint or automatic loser retry |
| F39 | V2 issue commits but reply/delivery acknowledgement is lost, or a broker crash occurs after unpublished handle allocation | original broker burns/closes the exact undelivered candidate when provable; no later capability reconstruction; unknown handle/commit truth is `FAILED_CLOSED / NOT_CONFIRMED` |
| F40 | child spawn call/reply fails at the commit boundary before custody/handshake classification | exact spawn/process/Job readback determines child false or true; absence is never inferred; a known created child enters exact bounded abort/wait, otherwise N.C. |
| F41 | created child fails or crashes at any edge from `SPAWN_COMMITTED` through `REMOTE_CLOSE_VERIFIED`, including abort/wait reply loss | resume only the exact durable predecessor with pinned child identity; prove exit/no survivor/remote close once; missing proof remains N.C. and cannot claim body/model zero |
| F42 | child exit is proven but body-gate, model-start or remote-close readback is lost/stale | child-survivor result may be zero, but body/model effect remains `NOT_CONFIRMED` until exact readback; no replay, respawn or success inference |

## 7. Effective verification and freeze gate

The effective matrix totals are A01-A51, N01-N72 and F01-F42, with R12 F34 replacing R11 F34 and no duplicate effective row. Deterministic tests must cover:

- every row in section 2.4 plus one-outside/cross-version tuples;
- legacy V1 `ISSUED` non-execution, V1 in-flight/handle blocking, terminal retirement as a separate CAS and fresh post-retirement V2 issue;
- both V2 issue-vs-revoke and issue-vs-expiry winners, stale loser, split-broker rejection and reply loss before/after commit/delivery acknowledgement;
- child not-created, child-created and creation-unknown branches at the same spawn seam;
- failure/restart at every `SPAWN_COMMITTED -> ABORT_REQUESTED -> EXIT_WAIT_STARTED -> CHILD_EXITED -> REMOTE_CLOSE_VERIFIED -> ABORT_COMPLETE` edge;
- child-created exit proven with body gate or remote close unknown, proving `NOT_CONFIRMED` rather than effect zero;
- exact unrelated process/member sentinel survival and no PID/name/broad-kill path.

R12 design completion requires fresh independent Tester, Critic and Judge over the exact current `task.md`, R9, R10, R11 and R12 hashes, with unresolved Critical/High `0/0` and Judge PASS. TASK-072, TASK-076 and TASK-075 owner acceptances remain separate G11 requirements. This addendum performs source/schema/test/native/process/private-audio/model/commit/push/PR effects zero.
