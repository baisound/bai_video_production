# TASK-074 Complete Design Packet R13 Addendum

Status: `DESIGN_CANDIDATE_R13_ADDENDUM / DEV-4 / SOURCE_START0 / EFFECT0 / NOT_REVIEWED`

## 1. Parent freeze and precedence

The effective R13 design is the following immutable chain plus the current authority record:

- R9 packet `complete-design-packet.md` SHA-256 `4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0`;
- R10 addendum `complete-design-packet-r10-addendum.md` SHA-256 `EF9CEA3DF0B4C86ABC0A2198E45F08A368DB0E50A99231744A81BA6014131364`;
- R11 addendum `complete-design-packet-r11-addendum.md` SHA-256 `CD73E8C6584C96B39D68C3A0D32E635DEC17EFC98145C7344779816400397690`;
- R12 addendum `complete-design-packet-r12-addendum.md` SHA-256 `38FB784A74C7A51397B3B4243566F62CB87B4CF49AAB7724986061B65DF54687`;
- this R13 addendum;
- current `task.md`, whose pre-R13 SHA-256 `44F9608FC01BB3019B9BDFB64ED0E6F40B40729155E7236781BC642ACCCA2D8C` is historical review input and no longer the current authority hash.

R13 supersedes or narrows only two R12 gaps:

1. R12 section 2.4's `PREPARED / V1 NONE/0 / V2 terminal / PUBLISHED` row gains the exact terminal-current retirement/revoke arbitration defined in sections 2 and 3 below;
2. R12 section 2.4's legacy V1 `REVOKE_PENDING` path gains the explicit terminal/zero-handle finalize-only tuple in section 4, so recovery cannot reject its own valid intermediate state.

Every unrelated R9-R12 contract remains immutable. R13 records no Critic, Tester or Judge PASS and creates no implementation, source, native process, private-audio, model, commit, push, PR or Production authority.

## 2. V2 terminal current-identity retirement

### 2.1 Exact terminal-three predecessor

`TASK074_REFERENCE_V2_TERMINAL_RETIRE_CAS_V1` may begin only from this same-broker/domain fence snapshot:

```text
RL                        = PREPARED
current V1 state          = NONE
current V1 handle count   = 0
current V2 state          = CONSUMED | BURNED | FAILED_CLOSED
current V2 handle count   = 0
RO                        = PUBLISHED
revoke/expiry intent      = ABSENT for the retire action
terminal result/readback  = exact and current
fence generation          = exact expected predecessor
```

The three terminal states have separate admission predicates:

- `CONSUMED`: exact TASK-075 consumer terminal, two-role completion and parent/child handle-close readbacks are current;
- `BURNED`: the exact burn/abort/failure event and every capability/attachment/parent/child handle close are current;
- `FAILED_CLOSED`: every authority/body gate is closed and live-handle count zero is positively proven, while every unknown semantic/effect fact remains explicitly `NOT_CONFIRMED`.

`FAILED_CLOSED` with unknown handle closure or inferred handle absence is not retireable. A public terminal receipt, enum value, equal hash, restart or missing handle record cannot satisfy any predecessor.

### 2.2 One atomic retirement

The retirement CAS performs one indivisible state change:

```text
verify the existing exact terminal-history entry or seal it exactly once
current V2 identity/state  -> V2_ABSENT
current V2 handle count    -> 0
current V1                 = NONE/0 (unchanged)
RL                         = PREPARED (unchanged)
RO                         = PUBLISHED (unchanged)
fence generation           -> predecessor + 1
```

The immutable history entry binds the retired lease identity/version, semantic operation, TASK-072 ticket/attachment/begin lineage, terminal kind, terminal/readback digest, body/model effect classification, broker/domain/session/build, trusted time and predecessor/result fence digests. Its preimage is closed: `ABSENT` permits exactly one seal in the retirement CAS; `EXACT_PRESENT` permits verification/preservation with history-count delta zero; unknown, different or multiple entries reject. `FAILED_CLOSED` history remains `NOT_CONFIRMED`; retirement never duplicates or relabels it as `BURNED`, `CONSUMED` or PASS.

There is no observable history-appended/current-terminal intermediate state and no current-cleared/history-missing state. A partial storage result is `FAILED_CLOSED / NOT_CONFIRMED`, never a repair by inference.

Retirement creates no V2 capability, attachment, child, body read or model call. V2 issue concurrency during this CAS is exactly zero. Retirement and issue are not one transaction and cannot share an operation identity.

### 2.3 Fresh fence and repeated operations

After retirement, a new operation may request a V2 issue only after a fresh private fence readback proves the complete R12 mint predecessor at the new generation:

`PREPARED / current V1 NONE/0 / current V2 V2_ABSENT/0 / PUBLISHED / no revoke-or-expiry intent`.

The next operation must have a new semantic operation identity, TASK-071 authority event as applicable, TASK-072 ticket, V2 lease identity, attachment and begin nonce. The retired operation's ticket, capability, attachment, begin nonce, child lineage and terminal readback are replay-invalid. Reuse of the same prepared reference is permitted only while its Project/Profile/Consent/selection/retention/currentness remain valid; body authority is always newly minted.

The repeated-operation sequence is therefore closed:

```text
fresh mint predecessor at generation n
-> issue operation i
-> one V2 terminal/handle0
-> terminal retirement at generation n+k
-> fresh mint-predecessor readback at generation n+k+1
-> issue distinct operation i+1
```

An issue request captured before retirement always loses on stale generation, even if retirement later succeeds. It cannot be automatically retried against the new generation.

## 3. Terminal retirement versus revoke/expiry and reply loss

### 3.1 Single winner at a terminal current state

Terminal retirement, explicit revoke and trusted-time expiry use the same broker/domain fence and one CAS winner.

- If retirement wins, it produces section 2.2's fresh-but-not-yet-read predecessor. Any concurrent revoke/expiry or issue request using the terminal generation is stale. A fresh revoke/expiry then competes with a fresh new-operation issue under R12 section 3; one of those later operations wins, never both.
- If revoke or expiry wins from a terminal-three predecessor, one atomic `TERMINAL_REVOKE_FINALIZE` verifies the existing exact terminal-history entry or seals it exactly once, clears current V2 to `V2_ABSENT/0`, retains V1 `NONE/0`, and commits `RL=REVOKED`. New issue count is zero.
- A pre-existing or concurrently observed revoke/expiry intent makes plain retirement ineligible. Caller time, split locks, split brokers and retirement-then-hidden-issue are prohibited.

Thus a terminal current identity has exactly one of two exits: retire to the R12 fresh predecessor, or terminal-finalize to `REVOKED`. It cannot remain hidden while a second V2 current identity is issued.

### 3.2 Terminal-three typed readback

The private body-free `TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1` returns one exact result:

- `CONSUMED_RETIRED`;
- `BURNED_RETIRED`;
- `FAILED_CLOSED_RETIRED_NOT_CONFIRMED`;
- `TERMINAL_REVOKE_COMMITTED`;
- `TERMINAL_EXPIRY_COMMITTED`;
- `NO_COMMIT_TERMINAL_STILL_CURRENT`;
- `STALE_OTHER_COMMIT`;
- `OUTCOME_NOT_CONFIRMED`.

It binds the retire/revoke/expiry operation, terminal kind and lease identity, exact predecessor/result generations and digests, immutable history event/digest, resulting current V1/V2 cardinalities, RL/RO, trusted-time and broker/domain/session identity.

If a CAS reply is lost:

- a matching committed history event plus the exact new fence returns the already-committed typed result without a second append, clear, revoke or expiry;
- exact no-commit plus the same terminal predecessor permits only the original broker's bounded recovery of the same retirement event identity. No new operation or capability may start before that recovery is resolved;
- a different committed event is `STALE_OTHER_COMMIT`; its exact current state is respected and never overwritten;
- missing, split or ambiguous history/current-state evidence is `FAILED_CLOSED / NOT_CONFIRMED`. No issue, revoke-success or retirement-success is inferred.

Public JSON, terminal receipt, history digest or caller idempotency key is Evidence only and cannot invoke recovery or recreate a current capability.

## 4. Legacy V1 `REVOKE_PENDING` recovery closure

### 4.1 Explicit terminal finalize-only tuple

R13 adds this exact row to the R12 section 2.4 complete joint table:

| RL | Current V1 / handles | Current V2 | RO | Only permitted next action |
|---|---|---|---|---|
| `REVOKE_PENDING` | `CONSUMED / 0`, `BURNED / 0` or `FAILED_CLOSED / 0` | `V2_ABSENT` | `PUBLISHED` | same-broker V1 terminal finalize CAS only; V1/V2 issue, body/model entry, return to `PREPARED` and purge are zero |

This row is reached only from R12's existing `REVOKE_PENDING / V1 nonterminal+exact one handle / V2_ABSENT / PUBLISHED` row through the original V1 operation's exact bounded terminal transition. For `FAILED_CLOSED`, zero live handles and closed authority/body gates must be positively proven; otherwise the current state remains recovery-blocked and `NOT_CONFIRMED`.

The intermediate terminal tuple is valid and readable. A generic joint validator must not reject it merely because it is terminal, and no other outgoing edge is legal.

### 4.2 V1 terminal finalize CAS

`TASK074_REFERENCE_V1_REVOKE_PENDING_FINALIZE_CAS_V1` atomically:

- verifies the existing exact V1 terminal-history entry or seals it exactly once without relabeling its terminal/effect truth;
- retires current V1 identity/state to `NONE/0`;
- keeps current V2 at `V2_ABSENT/0`;
- commits `RL=REVOKED` and preserves `RO=PUBLISHED` for later R9 key/purge transitions;
- advances the same broker/domain fence generation exactly once.

The finalize CAS neither issues V2 nor returns to `PREPARED`. It accepts only the exact terminal tuple and matching revoke/expiry event. A V1 terminal receipt or public mapping cannot invoke it.

### 4.3 Self-recovery and reply loss

`TASK074_REFERENCE_V1_REVOKE_FINALIZE_READBACK_V1` distinguishes:

- `V1_CONSUMED_REVOKE_FINALIZED`;
- `V1_BURNED_REVOKE_FINALIZED`;
- `V1_FAILED_CLOSED_REVOKE_FINALIZED_NOT_CONFIRMED`;
- `V1_TERMINAL_AWAITING_FINALIZE`;
- `V1_ACTIVE_RECOVERY_REQUIRED`;
- `STALE_OTHER_COMMIT`;
- `OUTCOME_NOT_CONFIRMED`.

If the active-to-terminal reply is lost, a fresh readback may observe the explicit terminal finalize-only tuple and proceed only to finalize. If finalize reply is lost, matching immutable history plus `REVOKED / V1 NONE/0 / V2_ABSENT/0` returns the already-finalized result. If the prior CAS did not commit and the exact terminal tuple remains, only the original broker may recover the same finalize event. Duplicate history, second revoke, V2 issue and automatic return to `PREPARED` are zero.

If handle closure, terminal identity, revoke lineage or current fence is ambiguous, the result remains `FAILED_CLOSED / NOT_CONFIRMED`; the validator does not self-reject a valid terminal tuple and does not admit an invalid one.

## 5. Acceptance and negative additions

### 5.1 Acceptance additions

| ID | Acceptance |
|---|---|
| A52 | Each V2 terminal-three current identity with exact handle0 has one same-broker retirement CAS that verifies or seals exactly one immutable history entry and clears current V2 to `V2_ABSENT/0` while preserving `PREPARED / V1 NONE/0 / PUBLISHED`. |
| A53 | `CONSUMED` retirement requires exact consumer/role/close readbacks and preserves its exact terminal/effect history. |
| A54 | `BURNED` retirement requires exact burn/abort/close readbacks and preserves its exact terminal/effect history. |
| A55 | `FAILED_CLOSED` retirement requires positively proven handle0 and closed authority/body gates, while retaining every unknown effect as `NOT_CONFIRMED`. |
| A56 | Retirement and issue concurrency is zero; a new operation may mint only from a fresh post-retirement fence and uses distinct ticket/lease/attachment/begin identities. |
| A57 | Terminal retirement versus revoke/expiry has one same-broker/domain CAS winner; a later fresh issue versus revoke/expiry uses the existing R12 single-winner gate. |
| A58 | Terminal-three reply loss is resolved by exact history/current-fence readback with no duplicate append, remint, hidden retry or PASS inference. |
| A59 | `REVOKE_PENDING / V1 terminal/0 / V2_ABSENT / PUBLISHED` is an explicit finalize-only tuple and cannot self-reject or authorize any other edge. |
| A60 | V1 finalize atomically verifies or seals exactly one terminal-history entry, retires current V1 to `NONE/0` and commits `REVOKED`; active-to-terminal/finalize reply loss resolves without duplicate effect. |

### 5.2 Negative additions

| ID | Condition | Required result |
|---|---|---|
| N73 | V2 retirement is requested from nonterminal, unknown, nonzero-handle, wrong RL/RO/V1 or stale terminal state | retirement/issue zero; preserve current operation and return fail-closed/N.C. |
| N74 | `CONSUMED` lacks exact consumer/two-role/handle-close readback | no retirement or new issue |
| N75 | `BURNED` lacks exact burn/abort/all-handle-close readback | no retirement or new issue |
| N76 | `FAILED_CLOSED` has inferred/unknown handle closure or an open authority/body gate | no retirement; effect remains N.C.; new issue zero |
| N77 | retirement and V2 issue are combined, overlap, share an operation identity, or issue uses the terminal/pre-retirement generation | stale/CAS reject; new V2 current count zero |
| N78 | terminal history is dropped, overwritten, duplicated or relabeled, including `FAILED_CLOSED` to `BURNED/CONSUMED` | reject retirement/readback; retain exact prior truth |
| N79 | reply loss is handled by a second append, clear, new lease, public receipt/hash or caller-selected recovery | reject; exact typed readback only; no new issue |
| N80 | retirement and revoke/expiry use split locks/brokers, both claim success, or retirement ignores a current revoke/expiry intent | authority zero; exact effect N.C. until one current fence is proven |
| N81 | repeated operation reuses the retired ticket, lease, capability, attachment, begin nonce, child lineage or old fence readback | reject before issue/body/model; immutable history unchanged |
| N82 | new operation issues before fresh post-retirement fence/Project/Profile/Consent/selection/currentness readback | issue zero; fresh operation plan required |
| N83 | `REVOKE_PENDING` V1 terminal tuple is rejected as impossible or is allowed to issue V1/V2, return to PREPARED, read body/model or purge | contract failure; only exact finalize remains legal |
| N84 | V1 terminal finalize has nonzero/unknown handle, wrong terminal/revoke lineage, public-only Evidence or a foreign fence | no finalize-success; remain recovery-blocked/N.C. |
| N85 | V1 active-to-terminal/finalize reply loss causes duplicate history/revoke, resets to active, or starts a new operation | reject replay; exact current readback and same-event recovery only |

## 6. Fault additions

| ID | Crash/race seam | Required recovery truth |
|---|---|---|
| F43 | `CONSUMED` terminal retirement commits or loses reply at the CAS boundary | exact history/current-fence readback returns one `CONSUMED_RETIRED`; no duplicate history or issue; stale/unknown remains N.C. |
| F44 | `BURNED` terminal retirement commits or loses reply at the CAS boundary | exact history/current-fence readback returns one `BURNED_RETIRED`; no duplicate history or issue; stale/unknown remains N.C. |
| F45 | `FAILED_CLOSED` terminal retirement commits or loses reply at the CAS boundary | retire only with proven handle0/gates closed; history remains N.C.; reply recovery never relabels it or remints |
| F46 | terminal retirement races a new issue and explicit revoke/expiry | issue based on terminal generation is zero; retirement or revoke/expiry has one winner; after retirement only a fresh R12 issue-vs-revoke CAS may proceed |
| F47 | crash/storage fault occurs between logical terminal-history verify/seal and current-V2 clear | indivisible CAS exposes one exact history entry plus clear, or neither; partial/ambiguous readback is `FAILED_CLOSED / NOT_CONFIRMED`, with no new issue |
| F48 | operation i retires, operation i+1 issues after fresh readback, then operation i retries retirement/attachment/begin | old generation and identities reject; operation i+1 remains the sole current lease and immutable history is unchanged |
| F49 | legacy V1 under `REVOKE_PENDING` reaches terminal/handle0, then crashes before finalize | explicit terminal finalize-only tuple is accepted on restart; only exact V1 finalize may proceed, closing the former self-reject gap |
| F50 | V1 finalize commits but reply/readback is lost | matching immutable history plus `REVOKED / V1 NONE/0 / V2_ABSENT/0` returns one already-finalized result; duplicate revoke/history/issue zero |
| F51 | V1 reaches `FAILED_CLOSED` but handle-close or terminal lineage is unknown | no finalize-success or new issue; remain `FAILED_CLOSED / NOT_CONFIRMED` until exact evidence exists |

## 7. Effective verification and freeze gate

The effective matrix totals are A01-A60, N01-N85 and F01-F51, with R12 F34 still replacing R11 F34 and no duplicate effective row. Deterministic tests must additionally cover:

- `CONSUMED`, `BURNED` and `FAILED_CLOSED` retirement positive paths and every missing terminal/handle/gate proof;
- terminal retirement with issue concurrency zero, fresh-fence-only new issue and distinct repeated-operation identities;
- retirement-vs-revoke and post-retirement issue-vs-revoke both winner orders;
- reply loss before/after CAS commit for all terminal three, history append/current clear atomicity and stale old-operation replay;
- V1 `REVOKE_PENDING` active-to-terminal, explicit terminal finalize-only tuple, finalize success and both reply-loss seams;
- V1/V2 `FAILED_CLOSED` with handle closure unknown, proving N.C. rather than retirement/finalize success.

R13 design completion requires fresh independent Tester, Critic and Judge over the exact current `task.md` and R9-R13 hashes, with unresolved Critical/High `0/0` and Judge PASS. TASK-072, TASK-076 and TASK-075 owner acceptances remain separate G11 requirements. This addendum performs source/schema/test/native/process/private-audio/model/commit/push/PR effects zero.
