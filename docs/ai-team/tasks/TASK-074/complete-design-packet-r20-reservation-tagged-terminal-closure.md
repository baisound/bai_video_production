# TASK-074 R20 Reservation and Tagged-Terminal Closure Amendment

Status: `DESIGN_CANDIDATE_R20 / DEV-4 / SOURCE_START0 / EFFECT0 / FRESH_INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-11`

Design identity: `TASK074-R20-RESERVATION-AND-TAGGED-TERMINAL-CLOSURE-V1`

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Reviewed predecessor: R19 at
`8246792e6e475bf98d54b0cc14c2cd890f62a7f5`, Tester `FAIL`
`0/3/0/0`, Critic `REVISE` `0/3/1/0`, Judge withheld. Exact identities and
findings are fixed in `design-r19-independent-review-receipt.md`.

R20 is a corrected design candidate only. It creates no owner acceptance,
source, child, process, private handle/body read, model action, audio/WAV,
publication, provider, ledger PASS, Final Review PASS, Release, Deploy or
Production authority.

## 1. Precedence and corrections

R20 supersedes R19 as a candidate. R16-R19 remain immutable rejected Evidence
and cannot authorize source. Accepted TASK-074 R9-R13 and current-main pure
contracts remain in force.

R20 retains the independently verified R19 properties: source and positive/
failure graphs are syntactically acyclic; TASK-074 parent reference authority
and TASK-014 sensitive-handle authority are zero; TASK-076 V3 failure semantics,
LOCAL-only compute, TASK-073 no-alias, canonical finishing policy and
TASK-041-to-TASK-036 exclusive binding remain required.

R20 corrects R19 by:

- replacing the invalid pre-arm call-dispatch lease with an effect-zero
  `Task014DispatchReservationV1`;
- requiring a separately accepted TASK-014/072/075/076 arm-adapter amendment
  that consumes that reservation while preserving the exact TASK-076 arm ABI;
- requiring a second exact four-owner receipt-only terminal adapter amendment
  for TASK-014 prepare/close truth consumed by TASK-076;
- beginning real TASK-014 call/sink dispatch only after exact
  `ARTIFACT_PREPARE_PENDING`, as canonical TASK-075 section 9.5 requires;
- defining queryable TASK-014 reservation/session terminal state machines;
- splitting SUCCESS, NONCURRENT, ABORTED and BURNED_UNKNOWN into disjoint
  nominal terminal branches;
- listing the complete exact known-no-child set and canonical restart exception;
- freezing a complete byte-exact R20 owner-envelope schema.

## 2. Immutable contract quartet

Fresh R20 review covers exactly:

| Owner | Immutable body | Contract identity |
| --- | --- | --- |
| TASK-014 | `../TASK-014/d4-reservation-closed-terminal-contract-r20.md` | `TASK014_D4_RESERVATION_AND_CLOSED_TERMINAL_CONTRACT_R20_V1` |
| TASK-074 | `r20-direct-transfer-tagged-terminal-contract.md` | `TASK074_DIRECT_TRANSFER_TAGGED_TERMINAL_CONTRACT_R20_V1` |
| TASK-041 | `../TASK-041/audio-completion-pass-contract-r20.md` | `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R20_V1` |
| TASK-036 | `../TASK-036/audio-completion-exclusive-binder-contract-r20.md` | `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R20_V1` |

These bodies are immutable after review. Owner acceptance is always a separate
record and never edits a reviewed body.

## 3. Exact stable owner acceptance envelope

Only after exact-byte Tester/Critic `Critical/High = 0/0` and Judge `PASS`, four
separate administrative owner units may issue:

| Owner | Envelope path | Exact `record_type` |
| --- | --- | --- |
| TASK-014 | `docs/ai-team/tasks/TASK-014/d4-r20-owner-acceptance.json` | `TASK014_D4_R20_OWNER_ACCEPTANCE_V1` |
| TASK-074 | `docs/ai-team/tasks/TASK-074/r20-owner-acceptance.json` | `TASK074_R20_OWNER_ACCEPTANCE_V1` |
| TASK-041 | `docs/ai-team/tasks/TASK-041/audio-completion-r20-owner-acceptance.json` | `TASK041_AUDIO_COMPLETION_R20_OWNER_ACCEPTANCE_V1` |
| TASK-036 | `docs/ai-team/tasks/TASK-036/audio-completion-r20-owner-acceptance.json` | `TASK036_AUDIO_COMPLETION_R20_OWNER_ACCEPTANCE_V1` |

Each envelope has exactly these sixteen keys and no others:

```text
version
record_type
owner_task
contract_identity
contract_path
contract_sha256
r20_path
r20_sha256
judge_receipt_path
judge_receipt_sha256
predecessor_owner_status_path
predecessor_owner_status_sha256
source_authority
effect_authority
issued_at
record_sha256
```

The count, exact spelling and every value are normative. `version` is JSON
integer `1`. `owner_task`, record type,
contract identity and all paths are exact owner-row constants. `source_authority`
and `effect_authority` are JSON `false`.

`contract_path`, `r20_path`, `judge_receipt_path` and
`predecessor_owner_status_path` are repository-relative UTF-8 paths using only
forward slash `/`; absolute paths, backslash, `.`/`..` segments, percent
encoding and alternate Unicode spellings are rejected. Every `*_sha256` and
`record_sha256` is exactly 64 uppercase hexadecimal characters over the exact
repository bytes. `r20_path` is exactly
`docs/ai-team/tasks/TASK-074/complete-design-packet-r20-reservation-tagged-terminal-closure.md`.
`judge_receipt_path` is exactly
`docs/ai-team/tasks/TASK-074/design-r20-independent-review-receipt.md`.

Owner-specific predecessor paths are:

| Owner | `predecessor_owner_status_path` |
| --- | --- |
| TASK-014 | `docs/ai-team/tasks/TASK-014/task.md` |
| TASK-074 | `docs/ai-team/tasks/TASK-074/task.md` |
| TASK-041 | `docs/ai-team/tasks/TASK-041/audio-completion-r2-owner-revalidation-readiness-evidence-2026-09-29.md` |
| TASK-036 | `docs/ai-team/tasks/TASK-036/p-ux-2d1-final-review-readiness-design-critic-judge-2026-08-17.md` |

Validation rejects floats, non-NFC strings, unpaired surrogates, duplicate or
unknown keys, and non-UTC timestamps. `issued_at` is exact RFC 3339 UTC second
precision `YYYY-MM-DDTHH:MM:SSZ`. Canonicalization is RFC 8785 JCS UTF-8.
`record_sha256` is uppercase SHA-256 over this exact byte sequence:

```text
ASCII("BAI:R20:OWNER-ACCEPTANCE:V1")
+ one NUL byte 0x00
+ RFC8785_JCS_UTF8(the other fifteen keys, omitting record_sha256)
```

The NUL is one byte, not the two characters backslash-zero. The envelope never
hashes itself. Each owner holds its own lock, atomically writes/readbacks only
its own envelope, then may update only its own later status to reference that
fixed envelope. No reviewer or other owner may issue it.

## 4. Non-substitutable authority types

Every positive authority/current/PASS type is private, sealed,
nonserializable, owner-read and non-convertible. Mapping, `from_dict`, copy,
pickle, public JSON, fixture, equal fields/hash and historical types fail.

TASK-074 has two forward phases and four disjoint terminal branches:

1. `Task074DirectTransferOperationReadyCurrentV1` — exact operation/ticket/
   consumer, V2 lease `ISSUED`, begin attachment, DISPATCHING plan and external
   slot; no child/transfer/body/model/output effect.
2. `Task074DirectTransferChildPairReadyCurrentV1` — selected V3 IN_FLIGHT,
   bootstrap child/custody, exact two-role transfer/parent closes and validated
   external input; before Artifact prepare and consumer entry.
3. `Task074DirectTransferSuccessTerminalCurrentV1` — exact TASK-075 result,
   TASK-014 result-bound and two-role close; the only POST input.
4. `Task074DirectTransferNoncurrentTerminalCurrentV1` — exact TASK-075
   noncurrent union; no result or POST.
5. `Task074DirectTransferAbortedTerminalCurrentV1` — exact known pre-release
   terminal; no result or POST.
6. `Task074DirectTransferUnknownTerminalReadbackV1` — R13 failed-closed/
   not-confirmed plus containment; no result, POST or effect-zero inference.

TASK-014 has a pre-arm reservation, a post-prepare-pending call/sink session and
four matching success/noncurrent/aborted/unknown terminal types. No reservation
contains or aliases a call-dispatch lease.

TASK-041 positive type remains
`Task041AudioCompletionVerifiedCurrentPassV1`; TASK-036 accepts only that exact
type through `bind_audio_completion_gate_receipt`.

## 5. Closed source eligibility

Source eligibility contains no operation-time runtime value or a source unit's
own output:

| Owner | Required accepted source dependency | Missing result |
| --- | --- | --- |
| TASK-014/TASK-074 | R20 owner envelope pair and effect-zero implementations | `R20_VOICE_OWNER_EFFECT0_NOT_CONFIRMED / SOURCE_START0` |
| TASK-014/072/075/076 | accepted `TASK014_TASK072_TASK075_TASK076_PREARM_RESERVATION_ARM_ADAPTER_AMENDMENT_V1` and `TASK014_TASK072_TASK075_TASK076_RECEIPT_ONLY_TERMINAL_ADAPTER_AMENDMENT_V1`, each with four owner receipts | `D4_CROSS_OWNER_ADAPTERS_NOT_CONFIRMED / SOURCE_START0` |
| TASK-035 | owner readers for `AudioRoundTripCurrentRead` and sealed optional-finishing skip | `TASK035_FINISHING_CURRENT_READ_NOT_CONFIRMED / SOURCE_START0` |
| TASK-036/TASK-041 | R20 owner envelope pair, TASK-041 class-only surface, then TASK-036 exclusive binder | `AUDIO_COMPLETION_TYPED_BINDER_NOT_CONFIRMED / SOURCE_START0` |
| TASK-043 | accepted Project transaction port contract | `TASK043_PROJECT_PORT_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-046 | accepted private-production reference binding interface | `TASK046_PRIVATE_BINDING_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-066 | LOCAL compute admission and child-network producer ABI | `TASK066_LOCAL_COMPUTE_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-068 | accepted secure-I/O contracts for used primitives | `TASK068_SECURE_IO_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-071 | accepted same-operation live Human authority contract | `TASK071_LIVE_AUTHORITY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-072 | V3 broker plus accepted reservation-arm adapter | `TASK072_V3_BROKER_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-073 | accepted LOCAL-only D4 allowlist, AUDIO/alias/dual acceptance rejected | `TASK073_LOCAL_COMPUTE_ALLOWLIST_NOT_CONFIRMED / SOURCE_START0` |
| TASK-075 | accepted consumer/result, noncurrent union and reservation amendment | `TASK075_CONSUMER_TERMINAL_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-076 | V3 custody plus accepted reservation adapter | `TASK076_V3_CUSTODY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |

`AUDIO_VOICE_COMPUTE_ADMISSION_V1` is a type error. A runtime receipt, lease,
reservation, child, current read or publication is forbidden in this table.

## 6. Non-circular source stages

1. `R20-S0`: review R20, four contracts, two Task records and R19 receipt;
   require Tester/Critic `0/0` and Judge `PASS`.
2. `R20-S0A`: four separate owner acceptance-envelope units; effect zero.
3. `R20-S1`: TASK-074 fake/non-biometric effect-zero producer.
4. `R20-S2`: TASK-014 restricted store/current-read effect-zero source.
5. `R20-S3`: independent four-owner reservation-arm and receipt-only-terminal
   amendment designs, acceptances and effect-zero adapter source; the arm
   adapter may wrap but never change the exact TASK-076 arm signature.
6. `R20-S4`: external TASK-035/043/046/066/068/071/072/073/075/076 contracts
   and implementations, independently allocated.
7. `R20-S5`: TASK-041 class-only PASS surface, no issuer/positive fixture.
8. `R20-S6`: TASK-036 exclusive binder plus owner-registry migration, negative
   paths only.
9. `R20-S7`: TASK-041 owner reader/issuer source; remains NOT_MINTED while any
   closed PASS input is unavailable.
10. `R20-S8A`: TASK-074 runtime producer source, gated only by accepted source
    dependencies; source completion mints no runtime instance.
11. `R20-S8B`: TASK-014 reservation, receipt-only preparation, terminal and
    POST source; source completion mints no runtime instance.
12. `R20-R0..R9`: one separately authorized operation follows sections 7-10.

Every source unit requires a separate named allocation, owner lock, Allowed
Files and completion receipt. R20 itself allocates none.

## 7. Exact positive runtime order

```text
current Project/voice/LOCAL-compute/Human/ticket preflight
  -> prepare, publish and select TASK-076 V3 DISPATCHING
  -> TASK-074 V2 lease ISSUED + begin attachment
  -> metadata-only TASK076_EXTERNAL_BINDING_SLOT_V1
  -> Task074DirectTransferOperationReadyCurrentV1
  -> Task014DispatchReservationV1 (no call/sink session)
  -> four-owner TASK-072 arm adapter consumes reservation
  -> unchanged issue_and_arm_job_child_v3
  -> reservation ARMED-consumed + JOB_CHILD_ARMED_READBACK_V3
  -> TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1
  -> TASK-074 lease IN_FLIGHT_PARENT_DELEGATION
  -> select exact TASK-076 V3 IN_FLIGHT
  -> create_bootstrap_job_child_v3
  -> bootstrap/process/Job-custody/network readbacks
  -> TASK-074 two-role child transfer and both parent closes
  -> record and validate external input
  -> Task074DirectTransferChildPairReadyCurrentV1
  -> claim_job_child_artifact_prepare_v3
  -> JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
  -> TASK-014 begin_dispatch + sink session + receipt-only preparation
  -> TASK014_RECEIPT_ONLY_PREPARED_RESULT_R20_V1
  -> commit_job_child_artifact_prepare_v3
  -> JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3
  -> attach_artifact_and_release_job_child_v3
  -> JOB_CHILD_STARTED_READBACK_V3
  -> authenticated TASK-075 body/model/inference/sink execution
  -> TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1
  -> Task014SuccessResultBoundReadbackV1
  -> exact two-role remote close and TASK-074 V2 lease CONSUMED
  -> Task074DirectTransferSuccessTerminalCurrentV1
  -> TASK-014 publication write/readback and POST receipt
  -> JOB_CHILD_TERMINAL_READBACK_V3
  -> TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1
  -> Task014NarrationPublicationCurrentReadV1
  -> TASK-041 closed-input latest PASS
  -> TASK-036 exclusive AUDIO_COMPLETION wrapper
```

Call dispatch remains at canonical TASK-075 section 9.5 step 19. Operation-ready
does not require a child. Child-pair-ready does not require Artifact prepare or
consumer result. TASK-074 success terminal does not require POST or TASK-076
terminal. Publication-current requires later Job terminal and lease retirement,
so downstream PASS cannot observe a partially closed success.

## 8. Exact disjoint terminal branches

### SUCCESS

Requires exact TASK-075 result and TASK-014 call/sink `RESULT_BOUND`. It never
uses `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`. After TASK-074 success
terminal, TASK-014 may write/readback POST; TASK-076 then reads its exact
terminal using the TASK-075 result coordinate, TASK-074 lease terminal and
receipt-only prepared result. Publication-current is sealed only after the
matching Job terminal and TASK-074 retirement are current.

### NONCURRENT

Post-release loss of compute/network currentness before result formation uses
exactly one `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`. It includes exact
TASK-014 durable call/sink `FAILED_CLOSED`, receipt-only truth and TASK-074
role/lease terminal truth. `RESULT_BOUND`, TASK-075 result, D4 result and POST
are forbidden. The union feeds the existing TASK-076 terminal ABI once.

### ABORTED

Pre-release known closure uses the phase-correct TASK-076 result, phase-required
TASK-014 terminal readback and TASK-074 aborted terminal. The closed exact
known-no-child set is:

1. `JOB_CHILD_REJECTED_READBACK_V3`;
2. `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`;
3. `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3`;
4. `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`.

`JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` is known-aborted but has a truthful
created process and is excluded from no-child. Later-phase or unknown readings
never prove no child. ABORTED has no TASK-075 result or POST.

### BURNED_UNKNOWN

Any uncertain reservation, process, transfer, Task014 session, owner close,
prepare/release, child exit or terminal publication selects only
`Task014BurnedUnknownReadbackV1`, TASK-074 R13
`FAILED_CLOSED / NOT_CONFIRMED` as applicable, TASK-076 `BURNED_UNKNOWN` and
recovery containment. It cannot convert to any known branch, effect zero,
result or POST.

## 9. TASK-014 reservation/session closure

Before Artifact-prepare pending, only the reservation exists. Arm success,
rejection and unknown atomically yield the three exact reservation terminals.
Orphan, prebootstrap, bootstrap rejection, bind failure and preflight failure
therefore have no TASK-014 call/sink session to close.

TASK-014 owner readers expose only sealed
`Task014DispatchReservationTerminalCurrentReadV1` and
`Task014ReceiptOnlySessionTerminalCurrentReadV1` from latest intact owner
chains. They join immutable records without rewriting them and return named
noncurrent results for missing, stale, forked, foreign, ambiguous or
broken-chain state.

After pending, TASK-014 has one closed session machine. Prepare failure returns
an exact TASK-014 failed-close readback and only an owner-adapter-derived
TASK-076 known-no-create result. Abort-wait is resolved only by the original
pending prepare continuation with exact receipt-only or known-no-create truth.
Release rejection closes the prepared session before abort completion.
Post-release noncurrent closes call/sink into the noncurrent branch. A TASK-075
result moves both to result-bound for success. Every reply-loss path is an exact
same-event query and never repeats an action.

## 10. Normative V3 failure and restart graph

R20 incorporates without shortening or overriding:

- `docs/ai-team/tasks/TASK-076/complete-design-packet.md`, SHA-256
  `C2B94DCA029EDB2BE8E3024A65BCD2E0A171E68E12E478EB3834DEDD7588BF86`,
  section `7.8.1 Sensitive-input bootstrap/bind/release V3`;
- `docs/ai-team/tasks/TASK-075/complete-design-packet.md`, SHA-256
  `2F35E01A6EC3BAFB4703E74CC4DBA34EBFC972157AFDF26B07C61F064B5D7B3B`,
  sections `9.3.1`, `9.5`, `9.7.2` and `11.3`.

A changed file hash or section identity yields
`DEPENDENCY_CHANGED / SOURCE_START0 / EFFECT0` pending fresh review.

The full V3 graph remains mandatory: arm rejection/unknown; orphan and
prebootstrap abort; bootstrap rejection; bind/preflight failure; Artifact
prepare pending, abort-wait, prepared or failed; release rejection; exact abort
pending, owner close, terminate/wait and commit; and burned-unknown containment.
Only exact abort-pending authorizes owner role close. No result is retryable.

Restart behavior is exact:

- a DISPATCHING-current exact unselected orphan may use only
  `abort_armed_orphan_job_child_v3`; its CAS must prove process-create was never
  entered, and the exact TASK-074 aborted terminal join follows;
- an already durable abort-pending claim may be queried and finished with its
  exact embedded Artifact truth;
- known bootstrap-rejected/prebootstrap-aborted/orphan-aborted/bootstrap-aborted
  terminal vectors are query-only;
- selected/prebootstrap onward without durable abort-pending becomes
  burned-unknown containment-only;
- no restart begins a new bind, preflight, prepare, release, resume, ordinary
  close or second abort.

TASK-074 unknown close remains R13 `FAILED_CLOSED / NOT_CONFIRMED`; TASK-076
vector unknown remains `BURNED_UNKNOWN`. Neither aliases the other.

## 11. Closed TASK-041 PASS and finishing inputs

One atomic currentness snapshot requires:

| Owner | Exact current input |
| --- | --- |
| TASK-041 | selected `AudioMediaReviewCurrentRead` plus `ExternalAudioReviewReceiptBinding` |
| TASK-026 | selected `AudioPlacementCurrentRead` |
| TASK-014 | latest intact `Task014NarrationPublicationCurrentReadV1` for each narration item; exact empty set only for a no-narration current plan |
| TASK-035 | canonical finishing branch below |
| TASK-041 ledger | `AudioCompletionLatestObservation` plus latest intact store readback |

Finishing is exactly `REQUIRED` -> current authenticated TASK-035 round-trip;
`OPTIONAL` -> that current read or sealed owner-issued optional skip from an
owner SKIP decision plus exact no-selected-manifest snapshot;
`NOT_APPLICABLE` -> exact null with no finishing/skip coordinate. Missing,
stale, revoked, foreign, ambiguous, forked and broken-chain values are distinct
non-PASS outcomes.

## 12. AUDIO_COMPLETION injection closure

Canonical `AUDIO_COMPLETION` owner becomes TASK-041 in registry, schema,
readiness projection and tests together. Legacy `DEVELOPER2` is historical
read-only and always noncurrent/non-PASS. No conversion exists.

Direct/public generic gate construction or validation, shell/runtime providers,
mappings/self-hashes, R0/R1 candidates, effect-zero outputs and any stale,
revoked, missing, ambiguous, foreign or broken-chain record fail. TASK-036 may
bind only the exact private TASK-041 PASS and cannot fabricate it.

## 13. R20 design-review Allowed Files

Exactly these eight files may change:

- `docs/ai-team/tasks/TASK-014/task.md`;
- `docs/ai-team/tasks/TASK-014/d4-reservation-closed-terminal-contract-r20.md`;
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r20.md`;
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r20.md`;
- `docs/ai-team/tasks/TASK-074/task.md`;
- `docs/ai-team/tasks/TASK-074/design-r19-independent-review-receipt.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r20-reservation-tagged-terminal-closure.md`;
- `docs/ai-team/tasks/TASK-074/r20-direct-transfer-tagged-terminal-contract.md`.

Owner envelopes, cross-owner amendments, source, schema, tests, current-state,
task-index, roadmap, CHANGELOG, runtime/native/private state and every other file
are forbidden.

## 14. Acceptance gate

Fresh review must prove:

1. the sixteen-key owner envelope is exact-JCS, stable, owner-local and
   non-self-referential;
2. source, positive runtime and failure/recovery graphs are acyclic;
3. pre-arm reservation is effect-zero, is consumed exactly once by the future
   four-owner adapter and never aliases call dispatch;
4. actual call/sink dispatch begins only after exact Artifact-prepare pending;
5. success/result and noncurrent-union branches are mutually exclusive;
6. all TASK-014 reservation/session failure and reply-loss states close exactly;
7. the four known-no-child results, bootstrap-aborted distinction and restart
   orphan exception match pinned TASK-075/TASK-076;
8. TASK-041 closed inputs, canonical finishing and TASK-036 generic/legacy
   injection closure remain sound;
9. unresolved `Critical/High = 0/0` and independent Judge `PASS`.

Before that decision and four later owner-envelope readbacks, every source,
native, private voice, model, audio/WAV, publication, TASK-041 PASS, TASK-036
Gate PASS, Release, Deploy and Production effect remains zero.
