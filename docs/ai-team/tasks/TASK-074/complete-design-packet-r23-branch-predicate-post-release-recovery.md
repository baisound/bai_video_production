# TASK-074 R23 Branch Predicate and Post-Release Recovery Amendment

Status: `DESIGN_CANDIDATE_R23 / DEV-4 / SOURCE_START0 / EFFECT0 / FRESH_INDEPENDENT_REVIEW_REQUIRED`

Date: `2026-10-11`

Design identity: `TASK074-R23-BRANCH-PREDICATE-AND-POST-RELEASE-RECOVERY-V1`

Current-main bind: `origin/main@53e4f0ea8e219b773a2976ba40b956830ff2e1df`

Reviewed predecessor: R22 at
`f80da528f0ff0d8d05f1ebf09e6255a02fb8ce47`, Tester `FAIL`
`0/2/0/0`, Critic `REVISE` `0/2/0/0`, Judge withheld. Exact identities and
findings are fixed in `design-r22-independent-review-receipt.md`.

R23 is a corrected design candidate only. It creates no owner acceptance,
source, child, process, private handle/body read, model action, audio/WAV,
publication-current, provider, ledger PASS, Final Review PASS, Release, Deploy
or Production authority.

## 1. Precedence and R23 corrections

R23 supersedes R22 as a candidate. R16-R22 remain immutable rejected Evidence.
Accepted TASK-074 R9-R13 and current-main pure contracts remain in force.

R23 retains the verified R22 correction that prepare recovery has disjoint live
continuation and restart-class paths. Only the original same-broker live
continuation may issue prepare `NEVER_ENTERED` and complete abort-wait. Restart
or continuation loss follows pinned TASK-075 section 9.3.1: finish only a
pre-restart abort-pending claim; otherwise pre-release burned-unknown
containment.

R23 closes the three R22 findings:

1. global branch selection derives exactly one predecessor kind, compares it to
   its own complete expected join vector, and selects containment only as the
   complement of all three known-closed predicates. POST `FALSE` is therefore
   normal for NONCURRENT/ABORTED and cannot make those tuples ambiguous;
2. prepare continuity context has the total union
   `NO_PREPARE_RECOVERY_EVENT | LIVE_CONTINUATION_INTERRUPTION |
   RESTART_CLASS_LOSS`, so ordinary uninterrupted late uncertainty is truthfully
   representable; and
3. restart burned-unknown enumeration is limited to explicit pre-release states.
   `JOB_CHILD_STARTED_READBACK_V3` instead follows pinned TASK-075 section 9.7.2
   post-release fixed-child exit and exact noncurrent terminal recovery, with
   burned unknown only as fallback.

## 2. Immutable contract quartet and exact paths

| Owner | Exact repository-relative `contract_path` | Contract identity |
| --- | --- | --- |
| TASK-014 | `docs/ai-team/tasks/TASK-014/d4-coordinated-closure-contract-r23.md` | `TASK014_D4_COORDINATED_CLOSURE_CONTRACT_R23_V1` |
| TASK-074 | `docs/ai-team/tasks/TASK-074/r23-global-terminal-closure-contract.md` | `TASK074_GLOBAL_TERMINAL_CLOSURE_CONTRACT_R23_V1` |
| TASK-041 | `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r23.md` | `TASK041_AUDIO_COMPLETION_VERIFIED_CURRENT_PASS_CONTRACT_R23_V1` |
| TASK-036 | `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r23.md` | `TASK036_AUDIO_COMPLETION_EXCLUSIVE_BINDER_CONTRACT_R23_V1` |

These exact bodies are never edited after review. Relative display aliases are
not accepted as envelope values.

## 3. Exact stable owner acceptance envelope

Only after Tester/Critic `Critical/High/Medium = 0/0/0` and Judge `PASS`, four
separate owner units may issue:

| Owner | Exact envelope path | Exact `record_type` |
| --- | --- | --- |
| TASK-014 | `docs/ai-team/tasks/TASK-014/d4-r23-owner-acceptance.json` | `TASK014_D4_R23_OWNER_ACCEPTANCE_V1` |
| TASK-074 | `docs/ai-team/tasks/TASK-074/r23-owner-acceptance.json` | `TASK074_R23_OWNER_ACCEPTANCE_V1` |
| TASK-041 | `docs/ai-team/tasks/TASK-041/audio-completion-r23-owner-acceptance.json` | `TASK041_AUDIO_COMPLETION_R23_OWNER_ACCEPTANCE_V1` |
| TASK-036 | `docs/ai-team/tasks/TASK-036/audio-completion-r23-owner-acceptance.json` | `TASK036_AUDIO_COMPLETION_R23_OWNER_ACCEPTANCE_V1` |

Every envelope has exactly these sixteen keys and no others:

```text
version
record_type
owner_task
contract_identity
contract_path
contract_sha256
r23_path
r23_sha256
judge_receipt_path
judge_receipt_sha256
predecessor_owner_status_path
predecessor_owner_status_sha256
source_authority
effect_authority
issued_at
record_sha256
```

`version` is integer `1`; authority values are JSON `false`. `contract_path`
is the exact owner row in section 2. `r23_path` is exactly
`docs/ai-team/tasks/TASK-074/complete-design-packet-r23-branch-predicate-post-release-recovery.md`.
`judge_receipt_path` is exactly
`docs/ai-team/tasks/TASK-074/design-r23-independent-review-receipt.md`.

Exact predecessor paths are:

| Owner | `predecessor_owner_status_path` |
| --- | --- |
| TASK-014 | `docs/ai-team/tasks/TASK-014/task.md` |
| TASK-074 | `docs/ai-team/tasks/TASK-074/task.md` |
| TASK-041 | `docs/ai-team/tasks/TASK-041/audio-completion-r2-owner-revalidation-readiness-evidence-2026-09-29.md` |
| TASK-036 | `docs/ai-team/tasks/TASK-036/p-ux-2d1-final-review-readiness-design-critic-judge-2026-08-17.md` |

All paths are repository-relative NFC UTF-8 with `/` only; absolute paths,
backslash, `.`/`..`, percent encoding and alternate Unicode forms fail. Hashes
are exactly 64 uppercase hex characters over repository bytes. Validation
rejects floats, non-NFC, unpaired surrogates, duplicate/unknown keys and
non-UTC timestamps. `issued_at` is RFC 3339 UTC seconds.

Canonicalization is RFC 8785 JCS UTF-8. `record_sha256` is uppercase SHA-256
over ASCII `BAI:R23:OWNER-ACCEPTANCE:V1`, one NUL byte `0x00`, then JCS bytes of
the other fifteen keys. It never hashes itself. Each owner writes/readbacks only
its envelope under its own lock, then may update only its status. No reviewer or
other owner may issue it.

## 4. Non-substitutable types and success predicate

All positive types are private, sealed, nonserializable, owner-read and
non-convertible. Mapping, `from_dict`, copy, pickle, fixture, public JSON, equal
fields/hash and historical types fail.

The TASK-075 result is success only when all are exact:

- `outcome=SUCCESS`, `terminal_stage=RESULT_VERIFIED`, `reason_codes=[]`;
- `sample_rate_hz=48000`, `channels=1`, `sample_format=PCM_S24LE`;
- `frame_count>0`, `child_count=1`, `generation_attempt_count=1`,
  `waveform_count=1`;
- non-null current waveform digest, sink-write result and output-handle identity;
- canonical stage-field matrix, authenticated live callback and same-operation
  Project/ticket/Job/call/sink/currentness.

`FAILED_KNOWN` and `UNKNOWN` are rejected from result-bound, POST,
publication-current, TASK-041 PASS and TASK-036 binding.

TASK-074 operation-ready and child-pair-ready remain forward-only. Owner-local
success/noncurrent/aborted close facts are provisional. The sole global terminal
tag is chosen by one owner CAS under the deterministic branch function in
section 10.

## 5. Closed source eligibility

| Owner | Required accepted source dependency | Missing result |
| --- | --- | --- |
| TASK-014/TASK-074 | R23 owner envelope pair and effect-zero implementations | `R23_VOICE_OWNER_EFFECT0_NOT_CONFIRMED / SOURCE_START0` |
| TASK-014/072/075/076 | accepted coordinated-prearm and receipt-only-prepare-terminal amendments, each with four owner receipts | `D4_COORDINATED_ADAPTERS_NOT_CONFIRMED / SOURCE_START0` |
| TASK-035 | round-trip current reader and sealed optional-skip reader | `TASK035_FINISHING_CURRENT_READ_NOT_CONFIRMED / SOURCE_START0` |
| TASK-036/TASK-041 | R23 envelope pair, TASK-041 class-only surface, then exclusive binder | `AUDIO_COMPLETION_TYPED_BINDER_NOT_CONFIRMED / SOURCE_START0` |
| TASK-043 | accepted Project transaction port | `TASK043_PROJECT_PORT_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-046 | private reference semantic-binding interface | `TASK046_PRIVATE_BINDING_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-066 | LOCAL compute admission and child-network producer | `TASK066_LOCAL_COMPUTE_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-068 | secure-I/O contracts for used primitives | `TASK068_SECURE_IO_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-071 | same-operation live Human authority | `TASK071_LIVE_AUTHORITY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-072 | V3 broker plus both coordinated adapters | `TASK072_V3_BROKER_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-073 | LOCAL-only D4 allowlist; AUDIO/alias/dual acceptance rejected | `TASK073_LOCAL_COMPUTE_ALLOWLIST_NOT_CONFIRMED / SOURCE_START0` |
| TASK-075 | consumer/result, noncurrent union and both coordinated amendments | `TASK075_CONSUMER_TERMINAL_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |
| TASK-076 | V3 custody plus both coordinated adapters | `TASK076_V3_CUSTODY_CONTRACT_NOT_CONFIRMED / SOURCE_START0` |

Source eligibility contains no runtime value, reservation, lease, child,
current read, publication or source unit's own output.

## 6. Non-circular source stages

1. `R23-S0`: exact-byte review of these eight files; Tester/Critic 0/0/0 and
   Judge PASS.
2. `R23-S0A`: four separate owner acceptance envelopes; effect zero.
3. `R23-S1`: TASK-074 fake/non-biometric effect-zero producer.
4. `R23-S2`: TASK-014 restricted store/current-read effect-zero source.
5. `R23-S3`: independent four-owner coordinated-prearm amendment and adapter.
6. `R23-S4`: independent four-owner receipt-only-prepare-terminal amendment and
   adapter including exact prepare continuity context.
7. `R23-S5`: external TASK-035/043/046/066/068/071/072/073/075/076 contracts
   and implementations under their owners.
8. `R23-S6`: TASK-041 class-only PASS surface, no issuer/positive fixture.
9. `R23-S7`: TASK-036 exclusive binder and owner-registry migration, negative
   paths only.
10. `R23-S8`: TASK-041 owner reader/issuer, NOT_MINTED until all closed inputs.
11. `R23-S9A/S9B`: separately allocated TASK-074 and TASK-014 runtime source;
    source completion mints no runtime instance.
12. `R23-R0..R10`: one separately authorized operation follows sections 7-10.

Every source unit requires its own allocation, owner lock, Allowed Files and
completion receipt. R23 allocates none.

## 7. Positive runtime order

```text
Project current
  -> TASK-074 operation-ready
  -> TASK-014 metadata-only dispatch reservation: RESERVED
  -> four-owner coordinator: CLAIM_INTENT
  -> TASK-014 reservation CAS: ARMING
  -> coordinator: TASK014_CLAIMED -> ARM_CALL_ENTERING
  -> unchanged issue_and_arm_job_child_v3 once
  -> owner query observes exact TASK-076 result
  -> JOIN_PENDING
  -> ARMED_CONSUMED + JOB_CHILD_ARMED_READBACK_V3
  -> attachment-begin CAS and lease IN_FLIGHT_PARENT_DELEGATION
  -> select TASK-076 IN_FLIGHT
  -> bootstrap/process/Job/network truth
  -> two-role transfer, parent closes, external bind/preflight
  -> child-pair-ready
  -> Task014ReceiptOnlyPrepareReservationV1: PREPARE_RESERVED
  -> four-owner prepare coordinator: PREPARE_CLAIM_ENTERING
  -> claim Artifact prepare -> ARTIFACT_PREPARE_PENDING
  -> PREPARE_PENDING_OBSERVED -> PENDING_CLAIMED
  -> TASK-014 begin_dispatch/sink: SESSION_ENTERED
  -> Task014ReceiptOnlyPreparedEvidenceV1
  -> four-owner adapter issues JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1
  -> commit Artifact prepare -> JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3
  -> release -> JOB_CHILD_STARTED_READBACK_V3
  -> authenticated TASK-075 execution
  -> exact canonical SUCCESS result
  -> Task014SuccessResultBoundFactV1
  -> Task074DirectTransferSuccessCloseFactV1
  -> TASK-014 POST candidate write/readback TRUE
  -> JOB_CHILD_TERMINAL_READBACK_V3
  -> TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1
  -> predecessor_kind SUCCESS + exact expected join vector
  -> Task074DirectTransferSuccessClosedCurrentV1
  -> Task014NarrationPublicationCurrentReadV1
  -> TASK-041 latest closed-input PASS
  -> TASK-036 exclusive AUDIO_COMPLETION wrapper
```

No global success exists before POST, Job terminal and retirement. Call/sink
entry remains after prepare pending. No backward edge exists.

## 8. Reservation failure/recovery closure

The four-owner coordinated-prearm amendment must define durable
`RESERVED -> CANCEL_PENDING | ARMING -> JOIN_PENDING -> terminal` and exact
owner-store current reads. Foreign input leaves RESERVED. Same-operation
cancel/expiry/stale uses a one-winner cancel CAS.

Its coordinator writes `CLAIM_INTENT` before the TASK-014 claim, then
`TASK014_CLAIMED`, `ARM_CALL_ENTERING`, `TASK076_RESULT_OBSERVED` and `JOINED`.
This proves not-entered only when the call-entry marker is absent; after that
marker, missing result is unknown unless an owner query resolves it.

The TASK-072 owner query distinguishes exact not-entered, armed, rejected,
burned-unknown and attempt-truth-unknown. Known no-call entry is closed by the
TASK-076-owner `close_prearm_without_vector_v1` and exact
`JOB_CHILD_REJECTED_READBACK_V3`; it never retries arm. Uncertain call entry is
closed only by owner-issued `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`. A durable
TASK-076 result is joined to the matching TASK-014 terminal after query. No
terminal is guessed, rewritten or paired with a contradictory result.

## 9. Prepare continuity, restart and post-release recovery

Before TASK-076 prepare claim, TASK-014 persists metadata-only
`PREPARE_RESERVED` and the adapter persists `PREPARE_CLAIM_ENTERING`. Exact
pending is query-joined as `PREPARE_PENDING_OBSERVED -> PENDING_CLAIMED` before
session entry.

Every operation has exactly one prepare continuity context:

```text
NO_PREPARE_RECOVERY_EVENT
| LIVE_CONTINUATION_INTERRUPTION
| RESTART_CLASS_LOSS
```

No-event requires an exact uninterrupted owner chain and is never inferred from
absence. Only the live class may query the same vector, advance the retained
reservation, issue owner `NEVER_ENTERED` and use:

```text
PREPARE_IN_PROGRESS
  -> JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3
  -> Task014ReceiptOnlyPrepareNeverEnteredReadbackV1
  -> exact JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1
  -> PREPARE_WITH_ABORT_WAIT commit
  -> JOB_CHILD_ABORT_PENDING_READBACK_V3
```

For restart-class loss, an exact durable pre-restart abort-pending claim may
only be queried/finished as that same claim. Otherwise only explicit pre-release
selected/prebootstrap, BOOTSTRAP_WAITING, BOUND, BINDING_FAILED, VALIDATED,
INPUT_FAILED, PREPARE_PENDING, PREPARED, PREPARE_FAILED or RELEASE_REJECTED
states become TASK-076 burned unknown plus containment. No fresh
`NEVER_ENTERED`, abort, prepare, commit, normal owner close, release or session
reconstruction exists.

Successful live TASK-014 evidence is converted only by the accepted adapter into
exact TASK-076-owner `JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1` before
prepare commit. Known live failure similarly yields exact known-no-create.
Unknown truth burns the vector. Ordinary live cancellation/currentness loss
after exact `JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3` uses `AFTER_PREPARE ->
ABORT_PENDING`; live release rejection uses `AFTER_RELEASE_REJECTED`.

`JOB_CHILD_STARTED_READBACK_V3` is not a pre-release state. After restart, the
fixed child exits. The separately accepted exact TASK-075 section 9.7.2
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1` plus already durable exact
TASK-014 and TASK-074 truth may form the Job terminal. Missing union/amendment, unknown child
exit or unknown owner truth falls back to burned unknown/containment. There is no
arm-only call, new result, reattach, resume, new owner close, second child,
model/sink retry or POST retry.

## 10. Deterministic late global terminal closure

An atomic owner snapshot derives `predecessor_kind` as exactly one of
`SUCCESS | NONCURRENT | ABORTED | UNKNOWN`. Each known kind requires exactly one
valid corresponding provisional close fact and forbids the others; no/multiple/
invalid/forked facts yield UNKNOWN.

The complete expected join vectors are:

| Kind | POST | Job-terminal | retirement | Known branch |
| --- | --- | --- | --- | --- |
| SUCCESS | TRUE | exact TRUE | exact TRUE | SUCCESS_CLOSED |
| NONCURRENT | FALSE | exact TRUE | exact TRUE | NONCURRENT_CLOSED |
| ABORTED | FALSE | exact TRUE | exact TRUE | ABORTED_CLOSED |
| UNKNOWN | any | any | any | none |

The first matching complete row selects its known branch. All other tuples
select `CONTAINED_PARTIAL_TRUTH`. Because kind is exclusive and containment is
the complement, no tuple is eligible for two branches. POST FALSE is expected
for NONCURRENT/ABORTED and does not itself select containment.

Containment preserves kind, the failed/missing expected-vector fields,
result/result-bound, POST `TRUE|FALSE|UNKNOWN`, role closes, lease,
session/prepare, effect/exit, Job-terminal, retirement, exact prepare continuity
context and containment facts. Ordinary uninterrupted late uncertainty uses
`NO_PREPARE_RECOVERY_EVENT`; it does not invent an interruption or restart.

Containment requires the current TASK-074 terminal slot, all readable
owner-authenticated same-operation reads, explicit UNKNOWN for unavailable
upstream joins with their last durable coordinates, all durable provisional
facts and exact same-operation containment. An unavailable upstream join is data
for containment, not a blocker.

If the TASK-074 global-terminal slot itself is uncertain, no new mint is
authorized: owner-store `NOT_CONFIRMED` and containment actions only remain
until exact same-slot readback resolves CAS truth. Containment never overwrites
a durable result/POST/close fact, never infers effect zero, and has no retry,
result, POST, publication-current, owner-close or PASS edge.

The exact known-no-child set is arm rejected, orphan aborted, prebootstrap
aborted and bootstrap rejected. Bootstrap aborted is known-aborted with a
created process. Restart permits only the canonical DISPATCHING-current exact
unselected-orphan CAS, finishing an already durable pre-restart abort-pending
claim, explicit pre-release burned-unknown containment, pinned post-release
terminal recovery/fallback or exact known-terminal queries. No other new action
starts.

## 11. Normative dependencies

R23 incorporates without shortening:

- TASK-076 `complete-design-packet.md` SHA-256
  `C2B94DCA029EDB2BE8E3024A65BCD2E0A171E68E12E478EB3834DEDD7588BF86`,
  section 7.8.1;
- TASK-075 `complete-design-packet.md` SHA-256
  `2F35E01A6EC3BAFB4703E74CC4DBA34EBFC972157AFDF26B07C61F064B5D7B3B`,
  sections 9.3.1, 9.5, 9.7.2, 11.3, 12 and 17.1.

A changed hash/section gives `DEPENDENCY_CHANGED / SOURCE_START0 / EFFECT0`.
TASK-074 unknown close remains R13 `FAILED_CLOSED / NOT_CONFIRMED`; TASK-076
unknown remains `BURNED_UNKNOWN`; neither aliases the other.

## 12. TASK-041 PASS and finishing closure

One atomic currentness snapshot requires selected TASK-041 media/external
review, selected TASK-026 placement, latest TASK-014 publication-current for
every narration item (or exact empty no-narration plan), canonical TASK-035
finishing and latest intact TASK-041 ledger observation/store readback.

Finishing: `REQUIRED` accepts current authenticated round-trip;
`OPTIONAL` accepts that or sealed owner-issued skip from owner SKIP plus exact
no-selected-manifest snapshot; `NOT_APPLICABLE` requires exact null. Skip
non-PASS outcomes distinctly include missing, stale, revoked, foreign, forked,
ambiguous and broken-chain.

Containment publication reads, FAILED_KNOWN/UNKNOWN results, missing/forked/
noncurrent inputs and public/equal-hash substitutes never PASS.

Canonical `AUDIO_COMPLETION` owner migrates to TASK-041 with registry, schema,
projection and tests together. `DEVELOPER2` remains historical noncurrent.
TASK-036 accepts only the exact private TASK-041 PASS; generic construction,
validation, providers, mappings and legacy records fail.

## 13. R23 design-review Allowed Files

Exactly these eight files may change:

- `docs/ai-team/tasks/TASK-014/task.md`;
- `docs/ai-team/tasks/TASK-014/d4-coordinated-closure-contract-r23.md`;
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r23.md`;
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r23.md`;
- `docs/ai-team/tasks/TASK-074/task.md`;
- `docs/ai-team/tasks/TASK-074/design-r22-independent-review-receipt.md`;
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r23-branch-predicate-post-release-recovery.md`;
- `docs/ai-team/tasks/TASK-074/r23-global-terminal-closure-contract.md`.

Owner envelopes, amendments, source, schema, tests, current-state, task-index,
roadmap, CHANGELOG, runtime/native/private state and all other files are
forbidden.

## 14. Acceptance gate

Fresh review must prove:

1. reservation coordinator closes pre-entry, mid-call, post-result, cancel,
   expiry, stale, process loss and reply loss without second arm or invented
   result;
2. live pending-to-session interruption alone may use retained-continuation
   query, owner `NEVER_ENTERED` and canonical abort-wait output;
3. pre-release restart-class loss exactly follows pinned TASK-075 section 9.3.1
   and cannot start `NEVER_ENTERED`, abort-wait, owner close, prepare, release or
   session;
4. post-release STARTED restart recovery preserves pinned TASK-075 section 9.7.2
   exact union path and uses burned unknown only as fallback;
5. predecessor kind and expected join vector make four branches exhaustive and
   mutually exclusive, including correct POST FALSE for noncurrent/aborted;
6. prepare continuity context is total and ordinary late uncertainty uses exact
   no-recovery-event rather than a false interruption/restart;
7. prepared-to-release ordinary live abort uses exact `AFTER_PREPARE`;
8. provisional facts and the global branch cannot contradict, and containment
   preserves all known effect facts;
9. full TASK-075 success predicate gates result-bound, POST,
   publication-current and TASK-041 PASS;
10. envelope path constants/JCS and optional-skip forked outcome are exact;
11. source, positive, failure and recovery graphs are acyclic;
12. unresolved `Critical/High/Medium = 0/0/0` and Judge `PASS`.

Before that decision and later owner-envelope readbacks, all source, native,
private voice, model, audio/WAV, publication-current, TASK-041 PASS, TASK-036
Gate PASS, Release, Deploy and Production effect remains zero.
