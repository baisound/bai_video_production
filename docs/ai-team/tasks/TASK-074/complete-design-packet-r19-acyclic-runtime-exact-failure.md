# TASK-074 R19 Acyclic Runtime and Exact Failure Amendment

Status: `DESIGN_CANDIDATE_R19 / DEV-4 / SOURCE_START0 / EFFECT0 / FRESH_INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-11`

Design identity: `TASK074-R19-ACYCLIC-RUNTIME-AND-EXACT-FAILURE-V1`

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Reviewed predecessor: R18 at
`f4f01a14ef845c54936d0c113dafe2a786e60ef5`, Tester `FAIL`
`0/2/0/0`, Critic `REVISE` `0/3/1/0`, Judge withheld. Exact identities and
findings are fixed in `design-r18-independent-review-receipt.md`.

R19 is a corrected design candidate only. It creates no owner acceptance,
source, child, process, private handle, body read, model action, audio/WAV,
publication, provider, ledger PASS, Final Review PASS, Release, Deploy or
Production authority.

## 1. Precedence and retained boundaries

R19 supersedes R18 as a candidate. R16-R18 remain immutable rejected Evidence
and cannot be source authority. The accepted TASK-074 R9-R13 design and
current-main pure contracts remain in force.

R19 retains the R18 corrections that passed independent review:

- immutable contract bodies and separate owner acceptance envelopes;
- no self-digest or post-review byte mutation;
- source eligibility separated from runtime values;
- TASK-043 port ownership separated from TASK-074 domain truth;
- TASK-066 LOCAL-only compute plus TASK-073 AUDIO/no-alias rejection;
- TASK-041 nominal type -> TASK-036 binder -> TASK-041 reader source order;
- TASK-041 AUDIO_COMPLETION owner migration and generic/legacy injection block;
- TASK-076 vector `BURNED_UNKNOWN` separated from TASK-074 R13 failed-closed.

R19 replaces R18's overloaded live type with three runtime phases, restores the
pre-arm TASK-014 dispatch lease, normatively binds the complete TASK-076 V3
failure graph and closes canonical finishing policy.

## 2. Immutable contract quartet

Fresh R19 review covers exactly:

| Owner | Immutable body | Contract identity |
| --- | --- | --- |
| TASK-014 | `../TASK-014/d4-three-phase-runtime-contract-r19.md` | `TASK014_D4_THREE_PHASE_RUNTIME_CONTRACT_R19_V1` |
| TASK-074 | `r19-direct-transfer-runtime-phases-contract.md` | `TASK074_DIRECT_TRANSFER_RUNTIME_PHASES_R19_V1` |
| TASK-041 | `../TASK-041/audio-completion-pass-contract-r19.md` | `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R19_V1` |
| TASK-036 | `../TASK-036/audio-completion-exclusive-binder-contract-r19.md` | `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R19_V1` |

The reviewed bodies are never edited to add status, hash or acceptance.

## 3. Stable owner acceptance envelopes

After exact-byte Tester/Critic `Critical/High = 0/0` and Judge `PASS`, four
separate administrative owner units may issue only:

| Owner | Envelope | Record type |
| --- | --- | --- |
| TASK-014 | `../TASK-014/d4-r19-owner-acceptance.json` | `TASK014_D4_R19_OWNER_ACCEPTANCE_V1` |
| TASK-074 | `r19-owner-acceptance.json` | `TASK074_R19_OWNER_ACCEPTANCE_V1` |
| TASK-041 | `../TASK-041/audio-completion-r19-owner-acceptance.json` | `TASK041_AUDIO_COMPLETION_R19_OWNER_ACCEPTANCE_V1` |
| TASK-036 | `../TASK-036/audio-completion-r19-owner-acceptance.json` | `TASK036_AUDIO_COMPLETION_R19_OWNER_ACCEPTANCE_V1` |

Each envelope has the closed field set from R18: version, record type, owner,
contract identity/path/hash, R19 path/hash, Judge receipt path/hash, predecessor
owner-status path/hash, `source_authority=false`, `effect_authority=false`,
`issued_at`, and `record_sha256`.

Canonicalization is exactly RFC 8785 JSON Canonicalization Scheme, never an
implementation-defined approximation. Before JCS, validation rejects floats, non-NFC strings,
unpaired surrogates, unknown fields and non-UTC timestamps. `issued_at` is exact
RFC 3339 UTC second precision `YYYY-MM-DDTHH:MM:SSZ`. `record_sha256` is SHA-256
over `BAI:R19:OWNER-ACCEPTANCE:V1\0` plus JCS UTF-8 bytes of all fields except
`record_sha256`; it never hashes itself.

The envelope binds a reviewed predecessor record. A later status successor
references the already-fixed envelope and is never fed back into its digest:

| Owner | Predecessor | Status successor |
| --- | --- | --- |
| TASK-014 | reviewed `../TASK-014/task.md` | same Task record references fixed envelope |
| TASK-074 | reviewed `task.md` | same Task record references fixed envelope |
| TASK-041 | `../TASK-041/audio-completion-r2-owner-revalidation-readiness-evidence-2026-09-29.md` | `../TASK-041/audio-completion-r19-status.md` |
| TASK-036 | `../TASK-036/p-ux-2d1-final-review-readiness-design-critic-judge-2026-08-17.md` | `../TASK-036/audio-completion-r19-status.md` |

The Judge result is first persisted in
`design-r19-independent-review-receipt.md`, binding the exact reviewed head and
all eight reviewed hashes. Each owner writer holds its own lock, writes only its
directory, atomically writes/readbacks its envelope, then updates only its own
status. Independent deterministic verification follows. No owner or reviewer
may issue another owner's envelope.

## 4. Non-substitutable authority and runtime types

All owner contract/effect/live/PASS types are private, sealed, nonserializable,
owner-read and non-convertible. Mapping, `from_dict`, copy, pickle, public JSON,
fixture, equal fields/hash and historical types cannot substitute.

TASK-074 runtime is split exactly:

1. `Task074DirectTransferOperationReadyCurrentV1` — current route/reference,
   V2 lease `ISSUED`, exact operation/ticket/consumer and one current begin
   attachment; no child/transfer/body/model/output effect.
2. `Task074DirectTransferChildPairReadyCurrentV1` — selected child, exact pair
   transfer, both parent closes, external binding record and validated preflight;
   before Artifact prepare, consumer entry or result.
3. `Task074DirectTransferTerminalCurrentV1` — exact terminal union, per-role
   remote close, lease terminal/retirement and same-operation readback; POST only.

R18's rejected `Task074DirectTransferLiveBoundCurrentV1` is never accepted.

TASK-014 runtime is split exactly:

1. `Task014CallDispatchLeaseV2` from one-use `begin_dispatch` before TASK-076
   arm, consuming the TASK-074 operation-ready type;
2. `TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1` after child-pair-ready plus exact
   V3 Artifact prepare pending, before release and body/model effects;
3. `Task014NarrationPostLiveBoundCurrentV1` only after TASK-075 result,
   TASK-074 terminal current and publication write/readback.

TASK-041 positive type remains
`Task041AudioCompletionVerifiedCurrentPassV1`; TASK-036 accepts only that exact
private type through `bind_audio_completion_gate_receipt`.

## 5. Closed source eligibility

Source eligibility contains no operation-time runtime value. Each row is an
accepted contract/implementation plus a separate owner lock/allocation:

| Owner | Required source dependency | Missing result |
| --- | --- | --- |
| TASK-014/TASK-074 | accepted R19 envelope pair and effect-zero implementations | `R19_VOICE_OWNER_EFFECT0_NOT_CONFIRMED / SOURCE_START0` |
| TASK-035 | implemented owner reader for `AudioRoundTripCurrentRead` and `Task035OptionalFinishingSkipCurrentV1` | `TASK035_FINISHING_CURRENT_READ_NOT_CONFIRMED / SOURCE_START0` |
| TASK-036/TASK-041 | accepted R19 envelope pair, TASK-041 class-only surface, then TASK-036 exclusive binder | `AUDIO_COMPLETION_TYPED_BINDER_NOT_CONFIRMED / SOURCE_START0` |
| TASK-043 | accepted `TASK043_OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_PORT_V1` | `TASK043_PROJECT_PORT_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-046 | accepted private-production voice/reference semantic-binding interface | `TASK046_PRIVATE_BINDING_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-066 | implemented `LOCAL_VOICE_COMPUTE_ADMISSION_V1` and child-network producer ABI | `TASK066_LOCAL_COMPUTE_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-068 | accepted immutable secure-I/O contracts for used primitives | `TASK068_SECURE_IO_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-071 | accepted same-operation live Human authority contract | `TASK071_LIVE_AUTHORITY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-072 | implemented V3 arm/bootstrap/bind/preflight/prepare/release/abort/containment ABI | `TASK072_V3_BROKER_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-073 | accepted LOCAL-only D4 allowlist amendment rejecting AUDIO/alias/dual acceptance | `TASK073_LOCAL_COMPUTE_ALLOWLIST_NOT_CONFIRMED / SOURCE_START0` |
| TASK-075 | accepted consumer/result plus V2 pre-close/terminal-union ABI | `TASK075_CONSUMER_TERMINAL_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-076 | implemented V3 selected-IN_FLIGHT through terminal and recovery ABI | `TASK076_V3_CUSTODY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |

`AUDIO_VOICE_COMPUTE_ADMISSION_V1` is a type error. A live receipt, lease, child,
runtime current read or source unit's own output is forbidden in this table.

## 6. Acyclic runtime order

The exact positive runtime graph is:

```text
current Project/voice/compute/Human/ticket preflight
  -> prepare, publish and select TASK-076 V3 DISPATCHING
  -> TASK-074 V2 lease ISSUED + begin attachment
  -> Task074DirectTransferOperationReadyCurrentV1
  -> TASK-014 begin_dispatch
  -> Task014CallDispatchLeaseV2
  -> exact TASK076_EXTERNAL_BINDING_SLOT_V1
  -> issue_and_arm_job_child_v3 consumes the dispatch lineage
  -> JOB_CHILD_ARMED_READBACK_V3 (process/body/model/artifact/effect zero)
  -> TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1
  -> TASK-074 lease IN_FLIGHT_PARENT_DELEGATION
  -> select exact TASK-076 V3 IN_FLIGHT
  -> create_bootstrap_job_child_v3
  -> JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3
  -> exact worker-begin/process/Job-custody/network readbacks
  -> TASK-074 direct two-role child transfer and parent close
  -> OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1
  -> record_job_child_external_binding_v3
  -> JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3
  -> validate_job_child_external_input_v3
  -> JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3
  -> Task074DirectTransferChildPairReadyCurrentV1
  -> claim_job_child_artifact_prepare_v3
  -> JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3
  -> TASK-014 receipt-only preparation using existing dispatch lease
  -> TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1
  -> commit_job_child_artifact_prepare_v3
  -> JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1
  -> JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3
  -> attach_artifact_and_release_job_child_v3
  -> JOB_CHILD_STARTED_READBACK_V3
  -> authenticated TASK-075 consumer entry/body/model/inference/sink
  -> exact TASK-075 result and four-owner terminal union
  -> Task074DirectTransferTerminalCurrentV1
  -> TASK-014 publication write/readback and POST receipt
  -> TASK-041 closed-input latest PASS
  -> TASK-036 exclusive AUDIO_COMPLETION wrapper
```

There is no backward edge. Operation-ready does not require child/consumer
truth. Child-pair-ready does not require Artifact prepare, consumer entry or
result. TASK-075 result gates only terminal/POST, never dispatch or transfer.

## 7. Exact live readbacks by phase

### Operation-ready

Requires current TASK-043 Project/port readback, TASK-046 private binding,
TASK-066 LOCAL compute, TASK-071 live authority, TASK-072 ticket, TASK-073
LOCAL-only allowlist, TASK-074 domain transaction/lease/attachment and current
DISPATCHING plan. It returns no child or transfer claim.

### Child-pair-ready

Requires the same operation plus selected V3 IN_FLIGHT, bootstrap child,
worker/process/Job custody, network enforcement/projection, TASK-074 per-role
transfer and both parent-close readbacks, TASK-072 external-binding record and
validated preflight. It explicitly excludes TASK-075 entry/result and every
Artifact prepare/release output.

### Terminal-current

Requires exact receipt-only prepared truth, release winner or exact abort path,
authenticated TASK-075 result when started, the applicable four-owner terminal
union, per-role remote-close truth and TASK-074 lease terminal/retirement. It
cannot be reused for another dispatch, child or POST.

Every missing/stale/revoked/foreign/ambiguous/broken-chain input yields a named
non-PASS/effect-zero result. Generic gates, public projections, historical
receipts and matching hashes never satisfy a phase.

## 8. Normative TASK-076 V3 failure graph

R19 normatively incorporates, without shortening or overriding, current-main:

- `docs/ai-team/tasks/TASK-076/complete-design-packet.md` SHA-256
  `C2B94DCA029EDB2BE8E3024A65BCD2E0A171E68E12E478EB3834DEDD7588BF86`,
  section `7.8.1 Sensitive-input bootstrap/bind/release V3`;
- `docs/ai-team/tasks/TASK-075/complete-design-packet.md` SHA-256
  `2F35E01A6EC3BAFB4703E74CC4DBA34EBFC972157AFDF26B07C61F064B5D7B3B`,
  section `9.3.1 Task066 post-admission currentness and V3 closure`.

If either exact file hash or section identity differs, R19 runtime eligibility is
`DEPENDENCY_CHANGED / SOURCE_START0 / EFFECT0` until fresh review.

The required exact APIs and results include all of the following:

1. `abort_armed_orphan_job_child_v3` returns exact
   `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3` or
   `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`. Child/effect zero is claimed only by
   the exact aborted result, never by unknown.
2. `abort_armed_prebootstrap_job_child_v3` races bootstrap create. Exact
   `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3` alone proves no child; later
   phase/race/unknown never does.
3. `claim_job_child_artifact_prepare_v3` returns exact prepare pending, abort
   pending or burned unknown.
4. `commit_job_child_artifact_prepare_v3` accepts only `PREPARE_ONLY` or
   `PREPARE_WITH_ABORT_WAIT` and exact prepared/known-no-create/receipt-only
   truth. It returns exact `JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3`,
   `JOB_CHILD_ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED_READBACK_V3`,
   `JOB_CHILD_ABORT_PENDING_READBACK_V3` or burned unknown.
5. A `PREPARE_IN_PROGRESS` abort can return only
   `JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3`, later started truth or burned
   unknown until the same prepare lease commits exact truth. This state is
   `ABORT_WAITING_ARTIFACT_TRUTH`; release is blocked and no second abort exists.
6. `attach_artifact_and_release_job_child_v3` returns started,
   `JOB_CHILD_RELEASE_REJECTED_ABORT_REQUIRED_READBACK_V3` or burned unknown.
   Release rejection cannot retry.
7. `claim_job_child_abort_v3` uses the exact closed union
   `BEFORE_PREPARE | PREPARE_IN_PROGRESS | AFTER_PREPARE |
   AFTER_RELEASE_REJECTED` and returns abort pending, abort wait, started or
   burned unknown.
8. Only exact `JOB_CHILD_ABORT_PENDING_READBACK_V3` authorizes TASK-074 owner
   role close, exact child terminate/wait and `commit_job_child_abort_v3`.
   Commit returns exact bootstrap-aborted or burned unknown.
9. Any uncertainty without an already durable abort-pending claim permits only
   `contain_burned_unknown_job_child_v3` for the exact original operation.
   Containment never binds, preflights, prepares, releases, resumes, reads a
   body, deletes an Artifact or converts the Job to success/failed-known.
10. Restart may finish/query the same durable abort-pending claim only. Without
    it, no fresh abort, owner close, bind, prepare or release is allowed.

TASK-074 unknown close/terminal truth remains R13
`FAILED_CLOSED / NOT_CONFIRMED`; TASK-076 vector unknown remains
`BURNED_UNKNOWN`. Neither can be relabelled as the other.

## 9. Closed TASK-041 PASS inputs and finishing policy

All rows bind the same Project/timeline/policy and latest ledger head:

| Owner | Required exact current input |
| --- | --- |
| TASK-041 | `AudioMediaReviewCurrentRead` for selected `AudioMediaReviewDecision` plus `ExternalAudioReviewReceiptBinding` |
| TASK-026 | `AudioPlacementCurrentRead` for selected `AudioPlacementCompilationRecord` |
| TASK-014 | `Task014NarrationPublicationCurrentReadV1` for every narration item; exact empty set only for a plan with no narration |
| TASK-035 | finishing branch below |
| TASK-041 ledger | `AudioCompletionLatestObservation` plus store readback proving latest intact current entry |

Finishing is exactly:

- `REQUIRED` -> `AudioRoundTripCurrentRead(state=CURRENT,
  owner_origin_authenticated=true, currentness_verified=true)`;
- `OPTIONAL` -> the same current read or sealed
  `Task035OptionalFinishingSkipCurrentV1` issued by TASK-035 from an
  owner-selected SKIP decision and exact current no-selected-manifest snapshot;
- `NOT_APPLICABLE` -> exact null and no manifest/skip coordinate.

The skip result binds Project/item/policy, semantic manifest key, store
revision/snapshot, decision revision and latest head. Mapping, boolean, absence,
NOT_FOUND, caller self-hash or fixture cannot create it. Missing, stale, revoked,
foreign, ambiguous and broken-chain results are distinct non-PASS outcomes.

## 10. Non-circular source and runtime stages

1. `R19-S0`: exact-byte review of R19, four contracts, two Task records and R18
   review receipt; require Tester/Critic `0/0` and Judge `PASS`.
2. `R19-S0A`: four separate owner acceptance envelope units; authority remains
   effect-zero.
3. `R19-S1`: TASK-074 fake/non-biometric effect-zero producer.
4. `R19-S2`: TASK-014 restricted consumer/POST effect-zero store/current read.
5. `R19-S3`: external TASK-035/043/046/066/068/071/072/073/075/076 owner
   contracts and implementations, independently allocated.
6. `R19-S4`: TASK-041 class-only PASS surface, no issuer/positive fixture.
7. `R19-S5`: TASK-036 exclusive binder and TASK-041 registry migration,
   negative paths only.
8. `R19-S6`: TASK-041 owner reader/issuer source; remains NOT_MINTED while any
   section 9 input is unavailable.
9. `R19-S7A`: TASK-074 three-phase runtime producer source, gated only by section
   5 source dependencies; source completion mints no runtime instance.
10. `R19-S7B`: TASK-014 V2 dispatch, receipt-only preparation, sink/terminal and
    POST source, gated by contracts/implementations only; source completion
    mints no runtime instance.
11. `R19-R0..R8`: execute the positive graph in section 6 for one authorized
    operation. Each runtime type is minted only at its forward phase.

Every source unit requires a separate named allocation, owner lock, Allowed
Files and completion receipt. No R19 design or envelope allocates source.

## 11. AUDIO_COMPLETION injection closure

Canonical `AUDIO_COMPLETION` owner becomes `TASK-041` in registry, schema,
readiness projection and tests together. Legacy `DEVELOPER2` stays historical
read-only and always noncurrent/non-PASS. No conversion exists.

Direct/public gate construction, generic validators, shell/runtime providers,
public mappings/self-hashes, R0/R1 candidates, effect-zero outputs, stale,
revoked, missing, ambiguous, foreign-Project or broken-chain records all fail.

## 12. R19 design-review Allowed Files

Exactly these eight files may change:

- `docs/ai-team/tasks/TASK-014/task.md`;
- `docs/ai-team/tasks/TASK-014/d4-three-phase-runtime-contract-r19.md`;
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r19.md`;
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r19.md`;
- `docs/ai-team/tasks/TASK-074/task.md`;
- `docs/ai-team/tasks/TASK-074/design-r18-independent-review-receipt.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r19-acyclic-runtime-exact-failure.md`;
- `docs/ai-team/tasks/TASK-074/r19-direct-transfer-runtime-phases-contract.md`.

Owner envelopes, source, schema, tests, current-state, task-index, roadmap,
CHANGELOG, runtime/native/private state and every other file are forbidden.

## 13. Acceptance gate

Fresh review must prove:

1. owner envelopes are exact-JCS, stable, non-self-referential and owner-local;
2. source graph and runtime graph are both acyclic;
3. dispatch lease precedes TASK-076 arm while parent reference authority is zero;
4. operation-ready, child-pair-ready and terminal types cannot substitute;
5. exact TASK-076 prepare/abort/release/containment graph is preserved in full;
6. no-child claims occur only from exact aborted readbacks;
7. finishing policy is canonical and OPTIONAL skip is owner-issued/current;
8. TASK-041/TASK-036 ordering and generic/legacy injection closure remain sound;
9. unresolved `Critical/High = 0/0` and Judge `PASS`.

Before that exact decision and four later owner envelope readbacks, every source,
native, private voice, model, audio/WAV, publication, TASK-041 PASS,
TASK-036 AUDIO_COMPLETION PASS, Release, Deploy and Production effect remains
`0`.
