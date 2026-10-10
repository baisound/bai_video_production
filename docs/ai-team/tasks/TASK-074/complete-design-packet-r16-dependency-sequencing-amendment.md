# TASK-074 R16 Dependency Sequencing Amendment

Status: `DESIGN_CANDIDATE_R16 / DEV-4 / EFFECT0 / SOURCE_START0 / INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-10`

Design identity: `TASK074-R16-NONCIRCULAR-CONTRACT-THEN-LIVE-SEQUENCE-V1`

Owner direction: proceed into the upstream prerequisite design work after the
TASK-014/TASK-036 gates were confirmed blocked on `2026-10-10`.

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Historical inputs only:

- accepted TASK-074 R9-R13 design and current-main pure contracts;
- unmerged R15 candidate at
  `codex/task-074-b-current-main-verification-closure-r1@ec3714b6c53cccadba6bd4b1fd4acf07f5b14b78`;
- unmerged TASK-014 D4 carrier at
  `codex/task-014-p0v-sealed-producer-boundary-handoff@4dfd3a09e16f048e6d34024b8eaae3fbb6f37c25`.

This amendment is a review candidate. It creates no source-start, implementation,
native, private-audio, model, process, publication, provider, Release, Deploy or
Production authority.

## 1. Blocking finding

The available current and candidate records contain a cross-owner dependency
cycle.

1. TASK-014 D4 source-start gate requires the exact TASK-074 owner completion
   identity and its private completion ports before TASK-014 may implement the
   call/sink/POST unit.
2. The unmerged TASK-074 R15 candidate requires the accepted TASK-014 D4
   completion identity before a future TASK074-C producer source amendment may
   begin.
3. TASK-075 and TASK-076 retain their own producer/consumer completion gates and
   cannot serve as a substitute first owner.

Under those conditions no owner is eligible to produce the first completion
identity. Waiting longer cannot close the cycle, and treating a design hash,
fixture, matching field set or public receipt as implementation completion would
violate the existing fail-closed boundary.

This is a `Critical` sequencing finding against R15 as written. It does not
invalidate the R13 pure contracts or R15's privacy invariants. R15 remains
unmerged Evidence and must not be promoted or implemented without correction.

## 2. Preserved invariants

R16 changes dependency order only. The following requirements remain mandatory:

1. TASK-074 owns the two-role private-reference producer and broker boundary.
2. TASK-014 has permanently zero parent authority to open, read, map, hash,
   copy, serialize, log, retain or reconstruct reference audio or transcript.
3. The only sensitive roles are
   `REFERENCE_AUDIO_READ_HANDLE` and
   `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`, in that order, read-only,
   non-inheritable, non-exportable and bound to one shared lease.
4. The selected child is the first and only participant that may read either
   role after the exact TASK-072 begin and TASK-076 custody sequence.
5. Public projections, schemas, receipts and hashes are body-free and cannot
   mint a live capability, select a process or authorize a body read.
6. TASK-014 owns narration call, sink, result, POST publication and POST
   currentness. TASK-074 cannot mint or reinterpret those records.
7. A real child, handle transfer, body read, model action, PCM/WAV write, Asset
   publication, Project mutation or provider action remains behind its exact
   producer, native and Human Gates.

## 3. Three non-aliasable completion levels

Every affected owner must use three distinct completion levels. A later level
may consume an earlier level, but no earlier level may be relabelled as a later
one.

| Level | Meaning | Permitted evidence | Prohibited claim |
| --- | --- | --- | --- |
| `CONTRACT_ACCEPTED` | exact type, state, field, failure and ownership rules are frozen | source/schema validators, body-free fixtures, parser/schema parity and independent review | live producer exists, native boundary verified, operation runnable |
| `PRODUCER_IMPLEMENTED_EFFECT0` | the owning implementation enforces the contract with non-biometric or fake ports and no sensitive effect | exact typed objects, negative/fault tests, owner-issued implementation receipt with all effect flags false | private body custody, child transfer, model/audio execution or Product readiness |
| `LIVE_BOUND_CURRENT` | exact producer, consumer, native and currentness receipts are mutually bound for one operation | live private owner readbacks issued only after the required Human/native gates | reusable authority, retry, automatic Production eligibility or cross-operation reuse |

The word `completion` without one of these exact levels is insufficient at a
cross-owner gate.

## 4. Non-circular implementation sequence

### R16-S0 — independent design acceptance

Independent DEV-4 Tester, Critic and Judge review this exact amendment with the
frozen R13 semantics, R15 candidate and TASK-014 D4 carrier. Unresolved
`Critical/High` must be `0/0`. Review creates no source authority.

### R16-S1 — TASK-074 effect-zero producer contract

TASK-074 may implement or complete only the missing body-free producer-side
contract for `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`. Its exact input
dependency is the accepted contract-level TASK-014 consumer-port identity, not
a TASK-014 implementation completion receipt.

S1 may validate:

- the closed two-role set and order;
- one-use lease and child-binding coordinates;
- structural absence of parent body-return operations;
- exact TASK-072/TASK-076 coordinate slots without claiming those owners are
  implemented;
- failure, close, stale and replay outcomes;
- nonserializability and public redaction.

S1 must use fake/non-biometric ports, must not create or open a child process or
sensitive handle, and must issue only
`TASK074_DIRECT_TRANSFER_V2_PRODUCER_IMPLEMENTED_EFFECT0`. Missing TASK-072,
TASK-075 or TASK-076 live owners remains explicit `DEPENDENCY_NOT_CONFIRMED`.

### R16-S2 — TASK-014 effect-zero consumer and publication contract

After S1 is current, TASK-014 may implement the exact restricted consumer type
plus the body-free `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` contract and
its owner-selected current-read interface. S2 may use only sealed synthetic
fixtures and fake persistence ports.

S2 must prove:

- no reference-open, body-return, callback substitution or reconstructed
  accessor exists;
- caller-created mappings, copied objects and equal hashes cannot satisfy the
  consumer type;
- POST records bind exact Project, operation, candidate, call/sink/result and
  publication-readback coordinates;
- owner history is append-only, Project-scoped, tamper-evident and selects only
  one intact latest head;
- missing receipt, missing store, stale upstream coordinate, broken chain,
  foreign Project and unsafe authority flags remain distinct fail-closed
  outcomes;
- the contract can represent `PUBLISHED_READBACK_VERIFIED` only when a future
  owner mint path supplies the exact live prerequisites; S2 itself cannot mint
  that state from a fixture or public constructor.

S2 issues only `TASK014_POST_CONTRACT_PRODUCER_IMPLEMENTED_EFFECT0`. It does not
issue a real narration receipt, canonical Asset, TASK-041 PASS or TASK-036 Gate
receipt.

### R16-S3 — external-owner contract acceptances

TASK-072 and TASK-076 may independently implement and accept their exact
effect-zero begin/custody contracts. TASK-075 may then implement the consumer
composition against S1, S2 and those exact owner types. Equal fields, historical
hashes or public projections cannot substitute for owner-issued types.

No S3 owner may require another owner's `LIVE_BOUND_CURRENT` result merely to
implement an effect-zero contract. Each may require the other owner's accepted
contract identity and leave the live edge closed.

### R16-S4 — live producer binding

Only after S1-S3 owner implementations, TASK-046 current private-production
binding, TASK-066 native compute proof, exact owner locks and a separate
implementation allocation may TASK-074 add the real broker/child-transfer
binding. That unit retains all native, private-body and Human Gates and issues a
live owner completion only after exact readback.

### R16-S5 — TASK-014 live call/sink and POST minting

Only after S4 is current may TASK-014 add the real call/sink execution binding
and the POST mint path. A real `PUBLISHED_READBACK_VERIFIED` receipt still
requires the exact TASK-075 result, TASK-014-owned publication write/readback and
all current upstream coordinates. No retry or authority is inferred from the S2
contract implementation.

### R16-S6 — TASK-041 and TASK-036 consumers

TASK-041 may integrate the S2 owner-current interface without minting PASS while
no real current narration receipt exists. TASK-036 may compile only an exact
TASK-041 verified-current PASS result. Neither consumer creates TASK-014 or
TASK-041 authority.

## 5. Gate matrix

| Requested action | Minimum required level | Result before that level |
| --- | --- | --- |
| parse/validate body-free TASK-074 V2 contract | TASK-074 `CONTRACT_ACCEPTED` | reject unknown type |
| implement TASK-014 restricted consumer/POST store with fixtures | TASK-074 `PRODUCER_IMPLEMENTED_EFFECT0` plus TASK-014 accepted contract | source start blocked |
| compose TASK-072/075/076 fake-port contracts | every referenced owner `CONTRACT_ACCEPTED` | dependency not confirmed |
| transfer private reference roles to a real child | all participating owners implemented, native/Human gates current | effect zero |
| read reference body or start model inference | exact `LIVE_BOUND_CURRENT` operation | effect zero and fail closed |
| publish a real TASK-014 POST receipt | exact live result plus TASK-014 publication readback | no receipt |
| mint TASK-041 canonical PASS | every required owner current-read result PASS | `SOURCE_REVALIDATION_REQUIRED / NOT_MINTED` |
| close TASK-036 audio Gate | exact TASK-041 verified-current PASS result | Gate remains open |

## 6. Negative and recovery requirements

1. A contract-level or effect-zero completion supplied to a live gate is a type
   error, not a degraded PASS.
2. A live completion supplied to a different Project, operation, candidate,
   child, lease, call, sink or currentness generation is stale/mismatched and
   cannot be rebound.
3. Loss or ambiguity after any live side effect requires exact same-operation
   owner readback. It never authorizes replay, a second transfer, a second child
   or a fabricated terminal receipt.
4. An unmerged branch, closed pull request, fixture manifest, design receipt or
   self-hash is Evidence only.
5. Historical R14/R15 names may be retained only when the current owner freezes
   their semantics and issues a current contract identity. Historical bytes do
   not become current authority automatically.
6. No stage modifies another owner's source without its explicit Allowed Files,
   owner lock and implementation allocation.

## 7. R16 review and source-start decision

This document records one unresolved `Critical` finding against the R15
dependency order and proposes the correction above. It does not self-accept.

R16 acceptance requires:

1. independent DEV-4 Tester validation of the dependency graph and type-level
   non-aliasing;
2. independent Critic review with unresolved `Critical/High = 0/0`;
3. independent Judge `PASS` over the exact R16 bytes and current-main bind;
4. confirmation that R13 invariants and the R15 direct-transfer safety model are
   preserved; and
5. a separate named source allocation for each of S1 through S6.

Before those reviews, source start remains `0`. The only changed Product path in
this unit is this R16 design candidate. Audio, model, provider, process, private
voice, WAV, publication, ledger, Final Review, Release, Deploy and Production
effects are all `0`.
