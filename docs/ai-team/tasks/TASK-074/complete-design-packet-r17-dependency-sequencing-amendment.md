# TASK-074 R17 Non-Circular Owner Contract and Live-Gate Amendment

Status: `DESIGN_CANDIDATE_R17 / DEV-4 / SOURCE_START0 / EFFECT0 / FRESH_INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-10`

Design identity: `TASK074-R17-NONCIRCULAR-OWNER-CONTRACT-LIVE-GATE-V1`

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Owner direction: proceed into the upstream prerequisite design work after the
TASK-014/TASK-036 gates were confirmed blocked on `2026-10-10`.

Reviewed predecessor:

- R16 exact SHA-256
  `42490B33BB7061A6BCE65F537CB82DFBF51CEB3B3F9E24B1249D5E8B0789D732`;
- Tester `FAIL`, `C/H/M/L = 0/1/1/0`;
- Critic `REVISE`, `C/H/M/L = 0/4/2/0`;
- durable findings: `design-r16-independent-review-receipt.md`.

R17 is a corrected review candidate. It creates no implementation, child,
process, private handle, body read, model action, audio/WAV, publication,
provider, ledger PASS, Final Review PASS, Release, Deploy or Production
authority.

## 1. Precedence and exact scope

R17 supersedes the R16 candidate in full. It supersedes only the dependency
ordering of the unmerged R15 candidate. R15 remains historical Evidence and is
not current authority.

The accepted TASK-074 R9-R13 design and current-main pure contracts remain in
force except where this amendment explicitly adds owner-acceptance types,
non-circular ordering, exact live prerequisites, direct-transfer recovery rules
and downstream PASS hardening.

The preserved TASK-014 D4 carrier is design input only. Its old source-start
rule that requires TASK-074 implementation completion before every TASK-014
effect-zero contract unit is replaced, if and only if R17 and both section 3
owner acceptances pass independent review, by the split gates in sections 8 and
9. The real call/sink/POST mint path remains blocked on TASK-074 live completion.

## 2. Blocking finding and correction principle

The old ordering is unreachable:

```text
TASK-074 implementation completion
  -> TASK-014 D4 implementation
  -> TASK-014 completion
  -> TASK-074 producer implementation start
```

R17 does not weaken a live gate to escape that cycle. It separates four
non-aliasable layers:

```text
OWNER_CONTRACT_ACCEPTED
  -> PRODUCER_IMPLEMENTED_EFFECT0
  -> LIVE_BOUND_CURRENT
  -> PRODUCT_CONSUMER_PASS
```

Each layer has its own owner-issued nominal type. Reviewers validate design but
cannot issue an owner type. A lower layer supplied to a higher gate is a type
error. Equal fields, equal hashes, public JSON, fixtures and historical receipts
cannot substitute for a nominal type.

## 3. Required pre-source owner acceptance pair

No R17 source unit may start until both candidate records below have passed the
same exact-byte independent Tester/Critic/Judge review as R17 and have been
administratively marked accepted without changing their frozen contract bodies.

| Owner | Exact acceptance type | Candidate record | Meaning |
| --- | --- | --- | --- |
| TASK-014 | `TASK014_D4_RESTRICTED_CONSUMER_PORT_CONTRACT_ACCEPTANCE_V1` | `../TASK-014/d4-restricted-consumer-port-contract-acceptance-r0.md` | accepts only the parent-authority-zero consumer port, POST contract/current-read boundary and staged source ordering |
| TASK-074 | `TASK074_DIRECT_TRANSFER_V2_PRODUCER_CONTRACT_ACCEPTANCE_V1` | `r17-direct-transfer-producer-contract-acceptance-r0.md` | accepts only the two-role child-local producer contract, close/recovery rules and staged source ordering |

The pair must bind:

- R17 SHA-256;
- both owner acceptance body SHA-256 values;
- `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2`;
- exact owner and consumer identities;
- parent sensitive-handle authority `0`;
- source, native, private-body, model and publication authority `false`.

A reviewer receipt, PR approval, R17 hash or one owner's acceptance cannot stand
in for the other owner. Before both are accepted, the result is
`OWNER_CONTRACT_ACCEPTANCE_PAIR_MISSING / SOURCE_START0 / EFFECT0`.

## 4. Owner-specific nominal type rules

Future implementation may use only the following non-substitutable types.
These names are frozen by R17; their source paths and implementation allocations
remain separate later units.

| Layer | Owner | Exact nominal type | Construction/read rule |
| --- | --- | --- | --- |
| contract | TASK-014 | `Task014RestrictedConsumerPortContractAcceptanceV1` | private token factory from the accepted owner record; body-free; canonical reparse; no runtime capability |
| contract | TASK-074 | `Task074DirectTransferProducerContractAcceptanceV1` | private token factory from the accepted owner record; body-free; canonical reparse; no runtime capability |
| effect-zero | TASK-074 | `Task074DirectTransferProducerEffectZeroV1` | issued only by TASK-074 fake/non-biometric verifier after both contract acceptances; current owner read required |
| effect-zero | TASK-014 | `Task014PostContractProducerEffectZeroV1` | issued only by TASK-014 fake-port verifier after exact TASK-074 effect-zero current read; cannot represent a published receipt |
| live | TASK-074 | `Task074DirectTransferLiveBoundCurrentV1` | issued only by the private producer broker after the complete section 7 readback chain and exact same-operation current read |
| live | TASK-014 | `Task014NarrationPostLiveBoundCurrentV1` | issued only after exact TASK-075 result plus TASK-014 publication write/readback; contains the exact `NarrationPublicationReceipt` coordinate |
| consumer PASS | TASK-041 | `Task041AudioCompletionVerifiedCurrentPassV1` | issued only by the TASK-041 owner reader after all exact owner reads pass and the canonical latest ledger entry is current |

Every implementation type above must satisfy all of the following:

1. direct construction is token-guarded or private;
2. `from_dict`, public schema data, a mapping, dataclass field equality or a
   matching digest never creates the nominal private type;
3. pickle/`__reduce__`, copying and serialization of private/effect types fail;
4. public projections contain no private seal, capability, path, handle, body,
   credential, voice identity or reconstructable accessor;
5. the owner reader reparses canonical owner state, verifies the private seal,
   exact Project/operation lineage, latest head and currentness, and returns a
   sealed read result rather than the caller's object;
6. stale, revoked, missing, ambiguous, foreign-Project, broken-chain and unsafe
   authority results are distinct non-PASS results;
7. no conversion API exists between contract, effect-zero, live and consumer
   PASS types.

## 5. Normative direct-transfer sequence

The R15 sequence is restated here as current normative R17 text. Historical R15
bytes are not required authority.

```text
TASK-074 V2 reference lease = ISSUED
  -> TASK074_REFERENCE_BEGIN_ATTACHMENT_V1
  -> selected TASK-076 V3 = DISPATCHING with exact external binding slot
  -> issue_and_arm_job_child_v3
  -> TASK072_JOB_CHILD_ARMED_READBACK_V3
  -> TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1
  -> TASK-074 lease = IN_FLIGHT_PARENT_DELEGATION
  -> selected TASK-076 V3 = IN_FLIGHT with exact child custody readback
  -> TASK074_REFERENCE_CHILD_BIND_DELEGATION_V1
  -> TASK074_REFERENCE_CHILD_BOUND_READBACK_V1
  -> CHILD_PAIR_READY and parent_sensitive_handle_count = 0
  -> body-free child preflight
  -> TASK-075 authenticated consumer entry
  -> only then BODY_READ_STARTED
```

`TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1` must atomically consume the exact
one-use attachment, bind the selected child/job/operation and advance the same
TASK-074 V2 lease. It is valid only after the exact
`TASK072_JOB_CHILD_ARMED_READBACK_V3`. Its readback enables but does not alias
the TASK-076 `IN_FLIGHT` transition.

The closed role set is exactly, in this order:

1. `REFERENCE_AUDIO_READ_HANDLE`;
2. `REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`.

Both are read-only, non-inheritable, non-exportable, one-use and governed by one
shared lease. The TASK-014 parent receives no raw handle, open method, callback,
path, URI, body, body-return method or reconstructable digest. It receives only
the exact nonserializable consumer binding after the producer chain is current.

## 6. Normative failure, terminal and recovery rules

| Condition | Required exact outcome |
| --- | --- |
| attachment/begin fails before child creation | attachment and lease burn/fail closed; child/body/model/consumer effects `0` |
| only one role transfers or role order/type/access is wrong | never `CHILD_PAIR_READY`; preserve independent per-role accepted/closed truth; no role retry and no replacement child |
| parent close is missing, mismatched or unknown | `parent_sensitive_handle_count=0` is not proven; preflight/body/model entry forbidden; use only same-operation containment |
| child custody, process, Project or operation identity differs | fail closed before transfer; no PID, path, public receipt or equal-hash fallback |
| parent opens/reads after atomic begin | burn/fail closed; body/model/artifact/consumer effects `0` |
| crash/reply loss after begin, transfer, close or terminal edge | query only the same durable operation/generation; no replay, second transfer, second child or fabricated receipt |
| partial-transfer containment | exact TASK-072 abort or accepted containment path only; close known owned roles; unknown role truth remains failed closed/not confirmed |
| post-release compute/network noncurrentness | exact `TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2` -> one TASK-074 owner terminal close -> exact `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2` -> one selected TASK-076 V3 terminal |

The fourth terminal-consumer argument is exactly
`TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1` bound to
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`. Neither the JOB receipt alone,
a V1 terminal union, a generic receipt, copied bytes nor an equal digest can
substitute. Unresolved close or terminal truth is `FAILED_CLOSED`, `UNKNOWN` or
`BURNED_UNKNOWN` as owned by the exact producer; it is never success or retry.

## 7. Closed live prerequisite table

TASK-074 live producer binding cannot start until every applicable row is
current and owner-issued. The exact type names below are normative coordinates;
a missing implementation remains missing even when a design uses the same name.

| Owner | Required current coordinate | Missing result |
| --- | --- | --- |
| TASK-043 | accepted `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1` canonical Project transaction/currentness port | `TASK043_TRANSACTION_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-046 | current private-production VoiceProfile/Consent/reference semantic binding including `TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1` | `TASK046_PRIVATE_PRODUCTION_BINDING_NOT_CONFIRMED / EFFECT0` |
| TASK-066 | owner-issued `AUDIO_VOICE_COMPUTE_ADMISSION_V1` plus exact native compute/isolation proof | `TASK066_NATIVE_COMPUTE_NOT_CONFIRMED / EFFECT0` |
| TASK-068 | accepted immutable secure I/O completion for every storage primitive actually used; otherwise exact null/not-applicable | `TASK068_SECURE_IO_NOT_CONFIRMED / EFFECT0` |
| TASK-071 | exact live `OWNER_VOICE_LOCAL_INFERENCE_V1` Human authority for the same Project/operation | `TASK071_LIVE_AUTHORITY_NOT_CONFIRMED / EFFECT0` |
| TASK-072 | current operation ticket/profile, `TASK072_JOB_CHILD_ARMED_READBACK_V3` and `TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1` owner acceptance | `TASK072_BEGIN_OWNER_NOT_CONFIRMED / EFFECT0` |
| TASK-074 | accepted contract pair, current effect-zero producer, exact V2 lease and current broker generation | `TASK074_PRODUCER_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-075 | accepted consumer composition/result ABI and V2 pre-close/terminal union owner implementation | `TASK075_CONSUMER_TERMINAL_NOT_CONFIRMED / EFFECT0` |
| TASK-076 | selected V3 process/job custody and terminal implementation including `JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1` | `TASK076_V3_CUSTODY_NOT_CONFIRMED / EFFECT0` |

Every row is conjunctive. `NOT_APPLICABLE` is permitted only where the row
defines an exact null/not-applicable case. Generic “Human Gates”, matching
hashes, fixtures, design receipts and public projections never satisfy a row.

## 8. Non-circular staged source order

### R17-S0 — exact-byte design and owner acceptance review

Independent Tester, Critic and Judge review R17, both section 3 owner acceptance
candidates, both canonical Task record updates and the R16 failure receipt.
Unresolved `Critical/High` must be `0/0`; Judge must return `PASS`.

After that decision, a body-preserving administrative update may mark the two
owner records accepted and insert exact R17/acceptance hashes. That update must
receive hash/readback verification. It still creates no source authority by
itself; it only makes separately allocated effect-zero units eligible.

### R17-S1 — TASK-074 producer effect-zero implementation

Input root: both accepted owner contract types. TASK-074 may implement the
closed producer contract with fake/non-biometric ports only. It may validate the
role set, lease, child coordinate slots, direct-construction rejection,
nonserializability, parent body-return absence, failures and redaction. It must
not open a process, private object or sensitive handle.

Output: `Task074DirectTransferProducerEffectZeroV1` through a TASK-074 owner
current reader. It cannot satisfy section 7 or authorize live transfer.

### R17-S2 — TASK-014 restricted consumer and POST effect-zero implementation

Input root: exact current S1 type plus both accepted owner contract types.
TASK-014 may implement only:

- the restricted consumer type with no reference-open/body-return surface;
- body-free `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` parser/schema;
- append-only, Project-scoped, tamper-evident owner history and latest/current
  read result;
- sealed synthetic fixtures and fake persistence ports.

S2 cannot mint `PUBLISHED_READBACK_VERIFIED`, a real receipt, Asset, TASK-041
PASS or TASK-036 Gate result. Its output is only
`Task014PostContractProducerEffectZeroV1`.

### R17-S3 — TASK-072/TASK-075/TASK-076 effect-zero owner contracts

Each external owner may implement its exact accepted contract against S1/S2
types without requiring `LIVE_BOUND_CURRENT`. Each retains its own Allowed Files,
owner lock and allocation. Equal public fields or historical hashes are rejected.

### R17-S4 — TASK-074 live producer binding

S4 may begin only when every applicable section 7 row is current, all cross-owner
locks/Allowed Files are exact, and a separate S4 allocation exists. S4 retains
every native, private-body, model and Human Gate. It alone may return
`Task074DirectTransferLiveBoundCurrentV1` after exact same-operation readback.

### R17-S5 — TASK-014 live call/sink and POST minting

S5 requires exact current S4 plus the TASK-075 result and all TASK-014
call/sink/publication prerequisites. Only a TASK-014-owned publication
write/readback may mint `Task014NarrationPostLiveBoundCurrentV1` and its body-free
`NarrationPublicationReceipt`. There is no retry, relabelling or effect-zero
promotion.

### R17-S6A — TASK-041 verified-current PASS

TASK-041 may integrate the S2 reader before a real receipt exists but must remain
`SOURCE_REVALIDATION_REQUIRED / NOT_MINTED`. Only after S5 and all other owner
reads are exact/current may the TASK-041 owner reader issue the nominal sealed
`Task041AudioCompletionVerifiedCurrentPassV1`.

### R17-S6B — TASK-036 exclusive AUDIO_COMPLETION binder

TASK-036 must add `bind_audio_completion_gate_receipt` that accepts only
`Task041AudioCompletionVerifiedCurrentPassV1`, reparses the canonical TASK-041
body through the owner reader, verifies Project/timeline/currentness and creates
the bounded Final Review wrapper without reissuing TASK-041 authority.

The current generic path must be closed before AUDIO_COMPLETION can pass:

1. direct/public `FinalReviewExternalGateReceipt` construction for
   `AUDIO_COMPLETION` is rejected;
2. `validate_external_gate_receipts` rejects generic/provider-supplied
   AUDIO_COMPLETION receipts not created by the exclusive binder;
3. shell/runtime generic providers cannot inject AUDIO_COMPLETION;
4. public mappings, self-hashes, R0/R1 candidates, effect-zero outputs, stale,
   revoked or foreign-Project records cannot produce PASS;
5. focused negative tests prove every prohibited route.

Until S6B is implemented and current, the TASK-036 AUDIO_COMPLETION Gate remains
open even when another gate wrapper has matching public fields.

## 9. Source allocation and Allowed Files rule

R17 acceptance never authorizes S1-S6 source. Each stage needs a separate named
allocation, fresh main/branch/worktree/dirty/overlap checks, exact Allowed Files
owned by that stage, independent validation appropriate to DEV-4 and an exact
completion receipt.

This design-review unit may modify only:

- `docs/ai-team/tasks/TASK-074/task.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r16-dependency-sequencing-amendment.md`;
- `docs/ai-team/tasks/TASK-074/design-r16-independent-review-receipt.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r17-dependency-sequencing-amendment.md`;
- `docs/ai-team/tasks/TASK-074/r17-direct-transfer-producer-contract-acceptance-r0.md`;
- `docs/ai-team/tasks/TASK-014/task.md`;
- `docs/ai-team/tasks/TASK-014/d4-restricted-consumer-port-contract-acceptance-r0.md`.

It must not modify source, schema, tests, current-state, task-index, roadmap,
CHANGELOG, another owner's documents, or any runtime/native/private state.

## 10. R17 acceptance gate

Fresh independent review must verify:

1. the owner acceptance pair provides a reachable source root without importing
   implementation or live authority;
2. the four nominal layers cannot substitute for one another;
3. the section 5-6 direct-transfer and recovery rules fully preserve the R15
   safety model without depending on R15 as authority;
4. section 7 is a closed conjunctive live gate;
5. the current TASK-036 generic AUDIO_COMPLETION injection path is explicitly
   rejected before S6B PASS;
6. canonical TASK-014/TASK-074 records own the candidate and exact Allowed Files;
7. unresolved `Critical/High = 0/0` and Judge `PASS`.

Before that exact decision and the administrative owner-acceptance readback,
all source, native, private voice, model, audio, WAV, publication, TASK-041 PASS,
TASK-036 AUDIO_COMPLETION PASS, Release, Deploy and Production effects remain
`0`.
