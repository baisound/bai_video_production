# TASK-074 R18 Stable Acceptance and Split-Gate Amendment

Status: `DESIGN_CANDIDATE_R18 / DEV-4 / SOURCE_START0 / EFFECT0 / FRESH_INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-10`

Design identity: `TASK074-R18-STABLE-ACCEPTANCE-SPLIT-GATES-V1`

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Owner direction: continue the upstream prerequisite design work after the
TASK-014/TASK-036 gates were confirmed blocked.

Reviewed predecessor: R17 at
`28c49f9cd3937f976e82c5c1179e2b335860a79b`, Tester `FAIL`
`0/3/0/0`, Critic `REVISE` `0/4/2/0`, Judge withheld. Exact identities and
findings are fixed in `design-r17-independent-review-receipt.md`.

R18 is a corrected review candidate only. It creates no implementation, child,
process, private handle, body read, model action, audio/WAV, publication,
provider, ledger PASS, Final Review PASS, Release, Deploy or Production
authority.

## 1. Precedence

R18 supersedes R17 as a candidate in full. R16 and R17 remain immutable rejected
Evidence and cannot be used as source authority. R18 supersedes only the
dependency ordering of historical unmerged R15; R15 is not current authority.

The accepted TASK-074 R9-R13 design and current-main pure contracts remain in
force. R18 adds only:

- stable post-review owner acceptance envelopes;
- separate source-eligibility and same-operation live-mint gates;
- the complete TASK-076 V3 bootstrap/bind/preflight order;
- corrected TASK-043/TASK-074 transaction ownership;
- `LOCAL_VOICE_COMPUTE_ADMISSION_V1` plus TASK-073 no-alias acceptance;
- a non-circular TASK-041/TASK-036 source order and closed PASS inputs;
- AUDIO_COMPLETION registry migration and generic-path rejection.

The old TASK-014 D4 gate that required completed TASK-074 live implementation
before every effect-zero contract unit is replaced only after R18 review and the
required owner acceptance envelopes. Real TASK-014 call/sink/POST minting remains
blocked on exact current TASK-074 live completion.

## 2. Non-substitutable authority layers

```text
IMMUTABLE_CONTRACT_BODY
  -> OWNER_ACCEPTANCE_ENVELOPE
  -> PRODUCER_IMPLEMENTED_EFFECT0
  -> LIVE_BOUND_CURRENT
  -> PRODUCT_CONSUMER_PASS
```

Each layer has an owner-issued nominal type. A lower layer at a higher gate is a
type error. Equal fields, equal hashes, public JSON, fixtures, review receipts
and historical records cannot substitute. Reviewers validate bytes but never
issue owner authority.

Future private types remain:

| Layer | Owner | Exact nominal type |
| --- | --- | --- |
| contract acceptance | TASK-014 | `Task014RestrictedConsumerPortContractAcceptanceV1` |
| contract acceptance | TASK-074 | `Task074DirectTransferProducerContractAcceptanceV1` |
| contract acceptance | TASK-041 | `Task041AudioCompletionPassContractAcceptanceV1` |
| contract acceptance | TASK-036 | `Task036AudioCompletionBinderContractAcceptanceV1` |
| effect-zero | TASK-074 | `Task074DirectTransferProducerEffectZeroV1` |
| effect-zero | TASK-014 | `Task014PostContractProducerEffectZeroV1` |
| live | TASK-074 | `Task074DirectTransferLiveBoundCurrentV1` |
| live | TASK-014 | `Task014NarrationPostLiveBoundCurrentV1` |
| consumer PASS | TASK-041 | `Task041AudioCompletionVerifiedCurrentPassV1` |

Private construction is owner-token guarded; mappings, `from_dict`, copying,
pickle/`__reduce__`, public schemas and caller self-hashes cannot construct or
serialize the types. The owner reader reparses canonical owner state, verifies
the private seal, Project/operation lineage, latest head and currentness, and
returns a new sealed read result. No conversion API exists between layers.

## 3. Immutable owner contract quartet

Fresh R18 review covers these exact immutable bodies:

| Owner | Contract body | Contract identity |
| --- | --- | --- |
| TASK-014 | `../TASK-014/d4-restricted-consumer-port-contract-r18.md` | `TASK014_D4_RESTRICTED_CONSUMER_PORT_CONTRACT_R18_V1` |
| TASK-074 | `r18-direct-transfer-producer-contract.md` | `TASK074_DIRECT_TRANSFER_V2_PRODUCER_CONTRACT_R18_V1` |
| TASK-041 | `../TASK-041/audio-completion-pass-contract-r18.md` | `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R18_V1` |
| TASK-036 | `../TASK-036/audio-completion-exclusive-binder-contract-r18.md` | `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R18_V1` |

No status, hash or acceptance value is ever inserted into a reviewed contract
body. Any byte change creates a new contract revision and requires fresh review.

## 4. Stable post-review owner acceptance envelopes

After exact-byte R18 Tester/Critic `Critical/High = 0/0` and Judge `PASS`, each
owner requires a separate named administrative allocation. Its writer may write
only its own Task directory and produces exactly one closed JSON envelope:

| Owner writer | Output path | Record type |
| --- | --- | --- |
| TASK-014 | `../TASK-014/d4-r18-owner-acceptance.json` | `TASK014_D4_R18_OWNER_ACCEPTANCE_V1` |
| TASK-074 | `r18-owner-acceptance.json` | `TASK074_R18_OWNER_ACCEPTANCE_V1` |
| TASK-041 | `../TASK-041/audio-completion-r18-owner-acceptance.json` | `TASK041_AUDIO_COMPLETION_R18_OWNER_ACCEPTANCE_V1` |
| TASK-036 | `../TASK-036/audio-completion-r18-owner-acceptance.json` | `TASK036_AUDIO_COMPLETION_R18_OWNER_ACCEPTANCE_V1` |

The predecessor and later status coordinates are closed:

| Owner | Predecessor record bound by envelope | Later status successor |
| --- | --- | --- |
| TASK-014 | `../TASK-014/task.md` at the reviewed commit | the same Task record, updated only to reference the fixed envelope |
| TASK-074 | `task.md` at the reviewed commit | the same Task record, updated only to reference the fixed envelope |
| TASK-041 | `../TASK-041/audio-completion-r2-owner-revalidation-readiness-evidence-2026-09-29.md` | `../TASK-041/audio-completion-r18-status.md` |
| TASK-036 | `../TASK-036/p-ux-2d1-final-review-readiness-design-critic-judge-2026-08-17.md` | `../TASK-036/audio-completion-r18-status.md` |

The exact field set is:

```text
acceptance_version
record_type
owner_task
contract_identity
contract_body_path
contract_body_sha256
r18_path
r18_sha256
judge_receipt_path
judge_receipt_sha256
predecessor_task_record_path
predecessor_task_record_sha256
source_authority=false
effect_authority=false
issued_at
record_sha256
```

`record_sha256` is SHA-256 over domain
`BAI:R18:OWNER-ACCEPTANCE:V1\0` plus RFC 8785-style canonical UTF-8 JSON of all
fields except `record_sha256`. It is never included in its own digest. The
envelope binds the predecessor Task record, not the later status update, so no
digest cycle exists.

Each owner writer must:

1. acquire its own exact administrative owner lock;
2. read R18, its immutable contract body, the Judge receipt and predecessor Task
   record from the same commit;
3. write the envelope atomically with source/effect authority false;
4. read back and recompute every digest;
5. update only its own Task status to reference the already-fixed envelope hash;
6. read back the Task status without rewriting the envelope;
7. receive independent deterministic envelope/readback verification.

The Judge result is first persisted separately as
`design-r18-independent-review-receipt.md`, bound to the exact reviewed head and
all eight reviewed file hashes. The four owner envelopes bind that receipt. The
receipt records review truth only and issues no owner acceptance itself.

One owner cannot write another owner's envelope. A Task status, PR approval,
review receipt or three of four envelopes cannot substitute. Before the required
pair for a stage exists, that stage is
`OWNER_CONTRACT_ACCEPTANCE_MISSING / SOURCE_START0 / EFFECT0`.

## 5. Source eligibility is not live-mint eligibility

R18 uses two disjoint gate classes.

`SOURCE_ELIGIBILITY` contains only immutable accepted contracts, completed
effect-zero owner implementations, exact owner locks, Allowed Files and a named
source allocation. It never requires a lease, child, operation-time ticket,
runtime readback or an output produced by the source unit being started.

`LIVE_MINT_ELIGIBILITY` is evaluated only after source exists. It contains the
same-operation live receipts, selected child, custody, close and currentness
readbacks. It never authorizes source creation and alone can mint
`Task074DirectTransferLiveBoundCurrentV1`.

Any design or implementation that combines these classes is invalid.

## 6. Complete normative TASK-076 V3 direct-transfer order

The current order is exactly:

```text
current compute/Human/ticket preflight
  -> prepare, publish and select TASK-076 V3 DISPATCHING
  -> TASK-074 V2 lease ISSUED
  -> TASK074_REFERENCE_BEGIN_ATTACHMENT_V1
  -> exact TASK076_EXTERNAL_BINDING_SLOT_V1
  -> issue_and_arm_job_child_v3
  -> JOB_CHILD_ARMED_READBACK_V3 (process/model/artifact/body/effect zero)
  -> TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1
  -> TASK-074 lease IN_FLIGHT_PARENT_DELEGATION
  -> select exact TASK-076 V3 IN_FLIGHT through canonical Project currentness
  -> create_bootstrap_job_child_v3
  -> JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3
  -> TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1
  -> TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1
  -> TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1
  -> TASK-066 network-enforcement producer readback
  -> TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1
  -> TASK-074 direct two-role transfer to that exact child-local broker
  -> OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1
  -> TASK074_REFERENCE_CHILD_BOUND_READBACK_V1
  -> record_job_child_external_binding_v3
  -> JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3
  -> validate_job_child_external_input_v3
  -> JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3
  -> claim_job_child_artifact_prepare_v3 with FIXED_RECEIPT_ONLY_DECLARATION_V1
  -> JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
  -> authenticated TASK-014 call/sink preparation
  -> commit exact receipt-only prepared truth
  -> attach_artifact_and_release_job_child_v3
  -> only the release winner may enter reference body/model/inference
```

The role order is exactly `REFERENCE_AUDIO_READ_HANDLE` then
`REFERENCE_TRANSCRIPT_UTF8_READ_HANDLE`. Both are read-only, non-inheritable,
non-exportable and one-use. TASK-014 parent authority to open, read, map, hash,
copy, serialize, log, retain or reconstruct either role is permanently `0`.

There is no child before selected `IN_FLIGHT`. `ARMED_V3` proves process zero.
The bootstrap child has no model entry, reference body, script body, output
handle or artifact body. `BODY_READ_STARTED` is forbidden until the exact
validated external input, prepared receipt-only truth and release winner.

## 7. Failure, unknown and recovery rules

| Condition | Required outcome |
| --- | --- |
| arm succeeds, IN_FLIGHT candidate unselected | exact `abort_armed_orphan_job_child_v3`; no child; select only the exact orphan before predecessor-correct terminal |
| selected IN_FLIGHT before bootstrap | exact `abort_armed_prebootstrap_job_child_v3` or create CAS, never both |
| bootstrap rejected with known no-process proof | `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`; every budget closed rejected |
| bootstrap create/identity uncertainty | TASK-076 vector-wide `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`; no replay or second child |
| only one reference role transfers, order/type/access differs | never pair ready; preserve independent per-role accepted/closed truth; no role retry/replacement |
| parent close missing, mismatched or unknown | `parent_sensitive_handle_count=0` not proven; preflight/body/model forbidden; same-operation containment only |
| external bind or preflight fails known | exact V3 failed-closed readback then serialized abort claim |
| reply loss after begin/create/transfer/close/release/terminal | query the same durable operation and generation only; no replay or fabricated receipt |
| post-release compute/network noncurrentness | exact TASK-075 V2 pre-close arms -> one TASK-074 terminal close -> exact TASK-075 terminal union -> one selected TASK-076 terminal |

TASK-076 may own its defined vector-wide `BURNED_UNKNOWN` process result.
TASK-074 R13 lease truth does not gain that state: unknown TASK-074 close or
terminal truth remains `FAILED_CLOSED / NOT_CONFIRMED`, non-retireable, blocks
new issue/replay/PASS and requires exact same-operation resolution.

The fourth TASK-075 terminal-union argument remains exactly
`TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1` bound to
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`. No generic receipt, V1 union,
copied bytes or equal digest can substitute.

## 8. Closed source-eligibility table for TASK-074 live source

This table controls whether the TASK-074 live producer source unit may start.
It contains contracts and implementations only, never operation-time output.

| Owner | Required accepted contract/implementation | Missing result |
| --- | --- | --- |
| TASK-043 | accepted TASK-043-owned `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_PORT_V1` canonical Product Project transaction/currentness port contract | `TASK043_PROJECT_PORT_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-046 | accepted private-production VoiceProfile/Consent/reference semantic-binding interface | `TASK046_PRIVATE_BINDING_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-066 | implemented `LOCAL_VOICE_COMPUTE_ADMISSION_V1` and exact Windows child-network enforcement producer ABI | `TASK066_LOCAL_COMPUTE_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-068 | accepted immutable secure I/O contracts for each primitive used | `TASK068_SECURE_IO_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-071 | accepted same-operation owner-voice live Human authority contract | `TASK071_LIVE_AUTHORITY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-072 | implemented V3 arm/bootstrap/bind/preflight/release and accepted attachment-begin owner adapter | `TASK072_V3_BROKER_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-073 | accepted D4 allowlist amendment that accepts only TASK-066 `LOCAL_VOICE_COMPUTE_ADMISSION_V1` and rejects AUDIO, alias and dual acceptance | `TASK073_LOCAL_COMPUTE_ALLOWLIST_NOT_CONFIRMED / SOURCE_START0` |
| TASK-074 | accepted TASK-014/TASK-074 envelope pair plus current TASK-074 effect-zero producer implementation | `TASK074_EFFECT0_PRODUCER_NOT_CONFIRMED / SOURCE_START0` |
| TASK-075 | accepted consumer composition/result ABI plus V2 pre-close and terminal union | `TASK075_CONSUMER_TERMINAL_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-076 | implemented V3 selected-IN_FLIGHT/bootstrap/custody/external-bind/preflight/receipt-only/terminal ABI | `TASK076_V3_CUSTODY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |

Every row is conjunctive. A separate S5 allocation, owner locks and exact
Allowed Files are also required. `AUDIO_VOICE_COMPUTE_ADMISSION_V1` is a type
error and cannot satisfy any row.

## 9. Closed same-operation live-mint table

Only after section 8 source is implemented can the producer evaluate this
runtime table. Every row must bind the same Project, operation, ticket, Job,
child, broker generation and current time.

| Owner | Required current live readback | Missing result |
| --- | --- | --- |
| TASK-043 | current `ProductProjectManifest` plus `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_READBACK_V1` under the canonical coordinator lock | `TASK043_TRANSACTION_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-046 | current private-production VoiceProfile/Consent/reference semantic binding including `TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1` | `TASK046_PRIVATE_PRODUCTION_BINDING_NOT_CONFIRMED / EFFECT0` |
| TASK-066 | current `LOCAL_VOICE_COMPUTE_ADMISSION_V1` plus exact native compute and network-enforcement producer readbacks | `TASK066_NATIVE_COMPUTE_NOT_CONFIRMED / EFFECT0` |
| TASK-068 | current pinned immutable secure-I/O readbacks for every used primitive, or the contract's exact null case | `TASK068_SECURE_IO_NOT_CONFIRMED / EFFECT0` |
| TASK-071 | exact live `TASK071_V2_LIVE_BROKER_RECEIPT` for `OWNER_VOICE_LOCAL_INFERENCE_V1` | `TASK071_LIVE_AUTHORITY_NOT_CONFIRMED / EFFECT0` |
| TASK-072 | current ticket, attachment-begin, worker-begin and network-isolation readbacks for the selected child | `TASK072_LIVE_BROKER_READBACK_NOT_CONFIRMED / EFFECT0` |
| TASK-073 | current owner allowlist read accepting LOCAL only and rejecting AUDIO/no-alias/dual acceptance | `TASK073_LOCAL_ALLOWLIST_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-074 | current TASK-074-owned `OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1`, V2 lease, broker generation, per-role transfer and parent-close readbacks | `TASK074_PRODUCER_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-075 | current authenticated consumer entry and applicable V2 terminal contracts | `TASK075_CONSUMER_CURRENTNESS_NOT_CONFIRMED / EFFECT0` |
| TASK-076 | selected V3 IN_FLIGHT, bootstrap waiting, process/Job custody, external bind, validated preflight and receipt-only preparation readbacks | `TASK076_V3_CUSTODY_NOT_CONFIRMED / EFFECT0` |

Generic “Human Gates”, public projections, fixtures, historical receipts and
matching hashes never satisfy a row. Only this table may mint
`Task074DirectTransferLiveBoundCurrentV1`.

## 10. Non-circular staged source order

### R18-S0 — exact-byte design review

Independent Tester, Critic and Judge review R18, the four immutable contract
bodies, both canonical Task record updates and the R17 failure receipt. Required
result: unresolved `Critical/High = 0/0`, Judge `PASS`.

### R18-S0A — separate owner acceptance envelopes

Four separate owner administrative units issue and read back section 4
envelopes. They create no source or effect authority. TASK-014/TASK-074 envelope
pair unlocks eligibility for S1. TASK-041/TASK-036 envelope pair unlocks S4A.

### R18-S1 — TASK-074 effect-zero producer

Requires accepted TASK-014/TASK-074 envelopes. Uses fake/non-biometric ports;
tests role order, private construction rejection, nonserialization, failure and
redaction. It opens no process, private object or sensitive handle. Output is
only `Task074DirectTransferProducerEffectZeroV1` through the owner reader.

### R18-S2 — TASK-014 restricted consumer/POST effect-zero

Requires exact current S1 and the accepted pair. Implements only the restricted
consumer, body-free POST parser/schema, append-only Project owner history and
latest/current read using sealed synthetic fixtures and fake persistence ports.
It cannot mint a real publication receipt or PASS. Output is only
`Task014PostContractProducerEffectZeroV1`.

### R18-S3 — external effect-zero owner contracts

TASK-043/046/066/068/071/072/073/075/076 owners independently close the exact
section 8 interfaces with their own locks, allocations and Allowed Files. They
do not require a TASK-074 live receipt.

### R18-S4A — TASK-041 nominal PASS type surface only

Requires accepted TASK-041/TASK-036 envelopes. Implements the private class
identity, direct-construction/serialization rejection and protocol shape only.
It has no issuer, owner reader or positive fixture and cannot create an instance.
This narrow unit is the only exception to the older TASK-041 readiness ordering.

### R18-S4B — TASK-036 exclusive binder effect-zero

Requires S4A. Implements `bind_audio_completion_gate_receipt`, generic/provider
rejection, registry/schema/readiness owner migration from legacy `DEVELOPER2`
to canonical `TASK-041`, and negative tests. It cannot fabricate a positive
TASK-041 instance. Historical DEVELOPER2 receipts are read-only and never PASS.

### R18-S4C — TASK-041 owner reader/issuer source

Requires completed S4B and the owner-current read interfaces in section 11.
Implements the reader and issuer but remains `NOT_MINTED` while any live input is
missing. Thus TASK-036 wrapper first and TASK-041 live PASS later are acyclic.

### R18-S5 — TASK-074 live producer source

Requires every section 8 row, separate allocation, locks and Allowed Files. It
implements the broker and section 9 evaluator. Source completion does not mint
a live type. Runtime mint requires every section 9 row for one operation.

### R18-S6 — TASK-014 live call/sink and POST mint

Requires exact current TASK-074 live type, TASK-075 result and all TASK-014
publication prerequisites. Only TASK-014 publication write/readback mints
`Task014NarrationPostLiveBoundCurrentV1` and body-free
`NarrationPublicationReceipt`.

### R18-S7 — TASK-041 live PASS and TASK-036 wrapper

Only after S6 and every section 11 input is current may the TASK-041 owner reader
mint `Task041AudioCompletionVerifiedCurrentPassV1`. S4B then consumes that exact
instance and canonical reread to produce the bounded Final Review gate wrapper.

## 11. Closed TASK-041 PASS inputs

All rows are conjunctive for the same Project/timeline and current ledger head.

| Input owner | Exact current input | Non-PASS behavior |
| --- | --- | --- |
| TASK-041 | `AudioMediaReviewCurrentRead` proving the selected `AudioMediaReviewDecision` and `ExternalAudioReviewReceiptBinding` are current and mutually bound | missing/stale/revoked/mismatch -> named non-PASS |
| TASK-026 | `AudioPlacementCurrentRead` proving the selected `AudioPlacementCompilationRecord` is current | missing/stale/foreign/broken chain -> named non-PASS |
| TASK-014 | `Task014NarrationPublicationCurrentReadV1` with exact `NarrationPublicationReceipt` for every narration item; exact empty set only when the plan has no narration | missing/stale/foreign/broken chain -> named non-PASS |
| TASK-035 | `AudioRoundTripCurrentRead` when finishing is REQUIRED; when OPTIONAL, either current manifest or an owner-selected explicit SKIPPED decision; when FORBIDDEN, exact null only | missing required/current policy mismatch -> named non-PASS |
| TASK-041 ledger | canonical `AudioCompletionLatestObservation` plus store readback proving the candidate is the latest intact current entry | absent/ambiguous/tampered/nonlatest -> named non-PASS |

The reader also verifies exact Project, timeline, policy, source item set and
closed receipt coordinates. “All other reads” is not a valid implementation.

## 12. AUDIO_COMPLETION ownership and injection closure

The future source unit must update the canonical registry, schema, readiness
projection and tests together so `AUDIO_COMPLETION` owner is exactly `TASK-041`.
Legacy `DEVELOPER2` is accepted only when reading historical records and is
always noncurrent/non-PASS. There is no automatic conversion.

The following must all fail:

- direct/public `FinalReviewExternalGateReceipt` AUDIO_COMPLETION construction;
- generic validator or shell/runtime provider injection;
- DEVELOPER2 legacy receipt submission;
- mapping, public schema, self-hash or equal-field imitation;
- R0/R1 candidate or effect-zero output;
- stale, revoked, missing, ambiguous, foreign-Project or broken-chain input.

## 13. R18 design-review Allowed Files

This review unit may modify only:

- `docs/ai-team/tasks/TASK-014/task.md`;
- `docs/ai-team/tasks/TASK-014/d4-restricted-consumer-port-contract-r18.md`;
- `docs/ai-team/tasks/TASK-074/task.md`;
- `docs/ai-team/tasks/TASK-074/design-r17-independent-review-receipt.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r18-stable-acceptance-split-gates.md`;
- `docs/ai-team/tasks/TASK-074/r18-direct-transfer-producer-contract.md`;
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r18.md`;
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r18.md`.

It must not create acceptance envelopes, modify source/schema/tests,
current-state, task-index, roadmap, CHANGELOG, runtime/native/private state or
another file. Every later S-stage requires a new allocation and Allowed Files.

## 14. Acceptance gate

Fresh review must prove:

1. immutable contract bodies plus separate digest-stable owner envelopes create
   no post-review byte mutation, self-reference or owner impersonation;
2. source eligibility and live mint are disjoint and non-self-dependent;
3. the TASK-076 bootstrap/bind/preflight sequence and every failure branch are
   complete;
4. TASK-043/TASK-074 ownership and LOCAL-only compute admission are correct;
5. TASK-041/TASK-036 source order is acyclic and PASS inputs are closed;
6. AUDIO_COMPLETION generic/legacy injection is rejected;
7. unresolved `Critical/High = 0/0` and Judge `PASS`.

Before that decision and four later owner envelope readbacks, all source,
native, private voice, model, audio, WAV, publication, TASK-041 PASS,
TASK-036 AUDIO_COMPLETION PASS, Release, Deploy and Production effects remain
`0`.
