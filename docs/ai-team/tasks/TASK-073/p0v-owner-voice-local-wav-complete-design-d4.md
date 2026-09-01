# TASK-073 P0-V Owner Voice Local WAV — Complete Design Packet D4

## 1. Identity

- Task: `TASK-073`
- Atomic responsibility: `OWNER_VOICE_LOCAL_WAV_PRODUCT_COMPOSITION_V4`
- Base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- State: `DESIGN_REVIEW_PENDING / SOURCE_START0`
- Product entry: unified `BAI Video Production.exe`
- Runtime: installed local/free only; paid/cloud fallback absent

D1, D2 and D3 are immutable failed review inputs.  D4 preserves D3's
accepted organization, three completion results, scoped TASK-036 Gate,
canonical V6.1.1 navigation, two-design/three-outcome execution lines and
serialized TASK-072 amendments.  It replaces D3 sections 3, 7–10 and the
affected acceptance/fault clauses with the exact contracts below.

## 2. Stable organization and one-direction graph

The coequal P0 outcomes remain:

- `P0-V`: Owner voice → best currently accepted local WAV;
- `P0-L`: Codex/Canonical SKILL learning-data bridge;
- `P0-E`: UI model selection → planning → scene split → generation → export
  and installed EXE QA.

Design A owns Product semantics/UI; Design B owns platform trust/delivery.
Outcome V, L and E implement their respective user results.  TASK-036 remains
the sole Shell/package integration owner in Outcome E.  Missing real receipts
park only real binding; ABI, fixtures, UI, negative tests and unrelated Tasks
continue.

```text
TASK-074 TASK-072 registry V2 merge
→ fresh-main TASK-075 TASK-072 registry V3

PR #470 canonical V1 callable evidence
+ TASK-014 V2 callable/sink amendment
+ TASK-074 private audio/transcript leases
+ TASK-066 Voice admission
+ TASK-071 Human plan
+ TASK-072 V3 ticket
+ TASK-076 durable Job
→ TASK-075 execute once
→ TASK-014 POST WAV publication/alignment
→ TASK-048 QA
→ TASK-075 playback
→ TASK-071 + TASK-041 decision
→ TASK-046 lifecycle V2 CAS/readback
→ TASK-075 join
→ TASK-073 composition
→ TASK073_IMPLEMENTATION_COMPLETE
→ separate TASK-036 P0-V integration
→ private Owner E3–E5 Gate
```

## 3. Four exact result classes

1. `TASK073_IMPLEMENTATION_PR_READY`: accepted D4; TASK-073 source/schema/tests
   complete; focused/negative/regression checks pass; independent C/H=0 Judge
   PASS; exact commit is pushed and one coherent Draft PR exists.
2. `TASK073_IMPLEMENTATION_COMPLETE`: the exact accepted PR head is merged to
   canonical main, required hosted checks are successful and fresh-main
   source/receipt readback matches.
3. `TASK036_P0V_INTEGRATION_COMPLETE`: separately authorized P0-V TASK-036
   amendment and installed synthetic E2E complete after canonical D4/mock,
   exact Owner mock check and producer completions.
4. `P0V_OWNER_OUTCOME_VERIFIED`: separate explicit private native Human Gate
   completes real Owner E3–E5 with exact-current PASS receipts.

No earlier result implies a later result.  Fixture/`NOT_CONFIRMED` evidence
never creates a real result.

## 4. TASK-014 V2 PRE authority closure

The TASK-014 amendment does not replace PR #470 V1.  It consumes a pinned,
freshly verified `ZeroShotCallableEnvelope` V1 and derives one V2 call
capability only when the V1 chain is fully bound.  Because current PR #470
uses only `BLOCKED|UNKNOWN`, the amendment must add the new terminal decision
`READY_FOR_TASK075_DISPATCH`; a V1 object cannot be relabelled or rehashed into
that decision.

### 4.1 `LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2`

Closed serializable Evidence fields:

```text
schema
record_type
task_owner
profile_id
profile_revision
parent_profile_sha256
compiled_at
expires_at
project_id
project_manifest_revision
project_manifest_sha256
installed_session_sha256
operation_plan_id
operation_plan_sha256
callable_envelope_id
callable_envelope_sha256
render_admission_sha256
preflight_sha256
canonical_plan_sha256
subject_binding_receipt_sha256
plan_derivation_receipt_sha256
reference_transcript_receipt_sha256
reference_transcript_revision_sha256
reference_transcript_body_sha256
script_text_revision_sha256
preview_call_text_body_sha256
voice_profile_revision_sha256
route_selection_revision_sha256
registered_job_revision_sha256
render_operation_identity_sha256
authorization_sha256
engine_revision_sha256
model_artifact_sha256
runtime_sha256
code_revision_sha256
reference_asset_checksum_sha256
reference_profile_sha256
destination_policy_sha256
call_surface_sha256
required_artifact_class
required_sample_rate_hz
required_channels
required_sample_format
max_attempts
automatic_retry_allowed
fixture_lineage_sha256
decision
reason_codes
profile_sha256
```

Types and values:

- IDs are bounded logical ASCII identifiers; digests are canonical SHA-256;
- revisions are positive integers; parent is null only for revision 1;
- times are Product-authored RFC3339 UTC and expiry is later;
- `route_mode=ZERO_SHOT_LOCAL`, `intended_usage=PREVIEW`;
- artifact/format is
  `STAGED_NARRATION_PCM_WAV_48000_MONO / 48000 / 1 / PCM_S24LE`;
- `max_attempts=1`, `automatic_retry_allowed=false`;
- decision is
  `READY_FOR_TASK075_DISPATCH | BLOCKED | UNKNOWN`;
- reason codes are a sorted unique bounded tuple from the closed Task014 enum.

`call_surface_sha256` is the canonical hash of every PR #470 callable field
from `model_loader_operation` through `ambiguous_dispatch_replay_allowed`, in
the V1 `_ENVELOPE_BODY_FIELDS` order.  Compilation requires exact equality of
V1 admission/preflight/plan/subject/derivation/transcript/job/operation/
authorization/engine/model/runtime/code/reference/destination coordinates.
Every V1 currentness/expiry predicate is re-evaluated under one trusted Task014
observation.  Any missing/mismatch/unknown input prevents READY.

`profile_sha256` is SHA-256 of canonical UTF-8 JSON containing every field
above except itself, in schema order.  Public JSON remains Evidence only and
cannot mint the live capability.

### 4.2 `TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1`

Task014 mints a private in-process one-use capability from the exact READY
profile plus current producer capabilities:

- TASK-074 `REFERENCE_AUDIO_READ_LEASE_V1`;
- TASK-074 `REFERENCE_TRANSCRIPT_READ_LEASE_V1`;
- TASK-014 `APPROVED_SCRIPT_BODY_READ_LEASE_V1`;
- TASK-066 admitted model/runtime read handles;
- TASK-071 Human plan capability;
- TASK-072 V3 operation ticket;
- TASK-076 exact Job generation.

The capability has no public constructor/serializer and exposes only:

```text
inspect_profile() -> immutable LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2
open_reference_audio() -> one bounded read-only body lease
open_reference_transcript() -> one bounded UTF-8 body lease
open_script_text() -> one bounded UTF-8 body lease
inspect_model_runtime() -> pinned read-only runtime snapshot
begin_dispatch(task075_consumer_identity) -> DISPATCH_LEASE | CALL_REJECTED
fail_closed(reason_code) -> FAILED_CLOSED
```

State:

```text
READY → IN_FLIGHT → RESULT_BOUND → CONSUMED
READY/IN_FLIGHT/RESULT_BOUND → FAILED_CLOSED
```

Every method validates exact consumer, current handles, call/profile/operation
identity and invocation count.  Any `BaseException`, mismatch, second,
concurrent or out-of-order call burns the object.  Restart never resurrects a
live capability.

## 5. TASK-014 output sink contract

### 5.1 `NARRATION_OUTPUT_SINK_CAPABILITY_V1`

Private exact fields bound inside the live object:

```text
sink_id
project_id
installed_session_sha256
operation_plan_sha256
call_profile_sha256
destination_policy_sha256
expected_predecessor_sha256
expected_artifact_class
sample_rate_hz
channels
sample_format
max_frames
max_output_bytes
staging_handle_identity_sha256
writer_build_sha256
```

Only Task014 can mint/inspect the object.  It exposes:

```text
begin(call_dispatch_lease) -> SINK_WRITE_SESSION | SINK_REJECTED
inspect_terminal(task014_owner_identity) -> SINK_TERMINAL_SNAPSHOT
fail_closed(reason_code) -> FAILED_CLOSED
```

`SINK_WRITE_SESSION` exposes:

```text
write_pcm24(frame_bytes) -> WRITE_ACCEPTED | WRITE_REJECTED
finish(frame_count, waveform_sha256) -> SINK_WRITE_RESULT
abort(reason_code) -> FAILED_CLOSED
```

Writes are streaming, bounded, sequential and exact-once.  Partial, empty,
misaligned or extra writes fail closed.  `finish` recomputes byte count,
waveform digest and format from the same owned handle.  State is:

```text
READY → WRITING → BODY_VERIFIED → RESULT_BOUND → CONSUMED
any nonterminal → FAILED_CLOSED
```

No path, mapping, self-hash or serialized receipt recreates the capability.
No caller can choose, reopen, replace, publish, abort-clean, or inspect the
staging target.

## 6. TASK-075 result ABI

`TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1` exact fields:

```text
schema
record_type
task_owner
result_id
result_revision
created_at
completed_at
project_id
installed_session_sha256
operation_plan_sha256
call_profile_sha256
callable_envelope_sha256
sink_id
sink_write_result_sha256
task066_admission_sha256
task071_human_plan_sha256
task072_ticket_sha256
task076_job_generation_sha256
worker_build_sha256
sandbox_profile_sha256
network_isolation_receipt_sha256
engine_revision_sha256
model_artifact_sha256
runtime_sha256
effective_backend
child_count
generation_attempt_count
waveform_count
sample_rate_hz
channels
sample_format
frame_count
waveform_sha256
output_handle_identity_sha256
outcome
reason_codes
fixture_only
authority_created
production_eligible
result_sha256
```

Enums: `effective_backend=CPU|CUDA`; `outcome=SUCCESS|FAILED_KNOWN|UNKNOWN`.
On SUCCESS all digest/format/count fields are non-null, counts are exactly one
except positive frame count, format is 48000/1/PCM_S24LE, and reason codes are
empty.  On FAILED_KNOWN/UNKNOWN, output/result body fields from
`sink_write_result_sha256` through `output_handle_identity_sha256` are null,
child/attempt counts are 0 or 1 as observed, and at least one closed reason is
required.  No silent backend switch is allowed.  Fixture output is always
authority false/production ineligible.

`result_sha256` is canonical JSON hash of all preceding fields in schema
order.  It is Evidence only.  The live Task014 call and sink objects are moved
to `RESULT_BOUND` by an in-process callback carrying this exact typed result;
a deserialized result cannot do so.

## 7. TASK-014 POST ABI

`TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` exact fields:

```text
schema
record_type
task_owner
post_receipt_id
post_revision
parent_post_sha256
created_at
project_id
project_manifest_revision
project_manifest_sha256
installed_session_sha256
operation_plan_sha256
call_profile_sha256
callable_envelope_sha256
task075_result_sha256
sink_id
sink_terminal_snapshot_sha256
destination_policy_sha256
publication_generation
publication_predecessor_sha256
staged_wav_ref
staged_wav_sha256
staged_wav_identity_sha256
sample_rate_hz
channels
sample_format
sample_count
duration_us
script_text_revision_sha256
alignment_receipt_sha256
boundary_receipt_sha256
publication_readback_sha256
outcome
reason_codes
fixture_only
authority_created
production_eligible
post_receipt_sha256
```

Enums: `outcome=PUBLISHED_READBACK_VERIFIED|FAILED_KNOWN|UNKNOWN`.
For success every WAV/publication/alignment field is non-null and exact-current;
format is 48000/1/PCM_S24LE; duration equals rounded sample-count duration;
parent/predecessor and generation are one CAS chain.  Failure/unknown has no
new staged-WAV authority.  Same operation + same result + same predecessor may
return the identical receipt; any different collision stops.  No automatic
retry, overwrite, cleanup or new publication occurs.

`post_receipt_sha256` is canonical JSON hash of preceding fields in schema
order.  The Task014 owner consumes the live call/sink objects only after pinned
publication and readback.  Entry or exception burns them.  Fault seams cover
before/after sink begin, first/final write, body verification, result binding,
publication, alignment and readback.

## 8. TASK-041 → TASK-046 V2 CAS

### 8.1 `TASK041_OWNER_VOICE_LISTENING_DECISION_V2`

Exact fields:

```text
schema
record_type
task_owner
decision_id
created_at
project_id
quick_clone_flow_id
expected_flow_revision
expected_flow_revision_sha256
task014_post_receipt_sha256
staged_wav_sha256
task048_qa_receipt_sha256
task075_playback_receipt_sha256
task071_human_receipt_sha256
decision
reason_codes
decision_sha256
```

`decision=ACCEPT|REJECT|RETEST`.  ACCEPT requires exact QA PASS and full
playback completion.  REJECT/RETEST require a current bounded playback
observation and exact Human receipt.  All values bind the same candidate and
flow head.  `decision_sha256` is canonical JSON hash excluding itself.  The
public record is Evidence only; TASK-071 supplies a private one-use decision
capability to the TASK-046 owner method.

### 8.2 V2 lifecycle

`QuickCloneFlowRevisionV2` preserves all V1 fields and adds schema version plus
`listening_cycle`.  Owner listening states are:

```text
NOT_AVAILABLE → REQUIRED
REQUIRED → ACCEPTED | REJECTED | RETEST_REQUIRED
RETEST_REQUIRED → REQUIRED
ACCEPTED and REJECTED are terminal for that candidate generation
```

Methods:

```text
apply_owner_listening_decision(
  expected_current_flow,
  private_task071_capability,
  TASK041_OWNER_VOICE_LISTENING_DECISION_V2
) -> APPLIED | EXACT_DUPLICATE | CAS_CONFLICT | REJECTED

apply_retest_playback_completion(
  expected_retest_flow,
  new_task075_playback_receipt
) -> APPLIED | EXACT_DUPLICATE | CAS_CONFLICT | REJECTED
```

Both methods lock the canonical TASK-046 owner transaction, re-read exact
parent/head and all bound WAV/QA/playback identities, then append one revision.
Same parent + same decision/playback receipt returns the existing revision.
Same parent + different body, stale head, candidate mismatch, second decision,
or replay after terminal state returns conflict/effect zero.  RETEST increments
`listening_cycle`; playback completion for the same WAV creates REQUIRED at the
new cycle; a fresh Task071 decision is then required.  REGENERATE is not a
lifecycle transition: it creates a separate Task014 operation/new candidate.

V1 bytes and parsers remain unchanged.  A canonical one-way V1→V2 migration
copies the four existing V1 states and sets `listening_cycle=0`; ACCEPTED and
REJECTED remain terminal.  V1 cannot represent RETEST_REQUIRED and never
silently maps it.  `QUICK_CLONE_FLOW_READBACK_V2` is compiled only from the V2
canonical head and includes flow revision/head, cycle, decision receipt,
candidate WAV, QA and latest playback bindings.

Candidate owner amendment files are limited to the TASK-041 source/test and
the TASK-046 quick-clone source, V2 schema/mirror/readback and focused tests.
They are separate owner Tasks; TASK-073/TASK-075 edit none of them.

## 9. Closed TASK-073 composition V4

### 9.1 Top-level fields

```text
schema
record_type
task_owner
composition_id
composition_revision
parent_composition_sha256
observed_at
project_id
project_manifest_revision
project_manifest_sha256
installed_session_sha256
operation_plan_sha256
receipts
derived_state
reason_codes
fixture_lineage
composition_sha256
```

`receipts` is an object with exactly these 14 keys; every value is null or one
`ReceiptRefV1`:

```text
installed_session
quick_clone
selection
reference
call_profile
compute_admission
human_plan
operation_ticket
durable_job
inference
wav
qa
playback
listening_join
```

`ReceiptRefV1` exact fields:

```text
owner_task
receipt_type
schema_version
opaque_ref
receipt_sha256
producer_build_sha256
project_id
project_manifest_sha256
installed_session_sha256
operation_plan_sha256
quick_clone_flow_sha256
revision
head_sha256
observed_at
expires_at
current
fixture_only
authority_created
production_eligible
```

### 9.2 Exact allowlist

| Slot | Owner/type/version |
|---|---|
| installed_session | TASK-036 / `INSTALLED_STARTUP_CONTEXT_V1` / 1 |
| quick_clone | TASK-046 / `QUICK_CLONE_FLOW_READBACK_V2` / 2 |
| selection | TASK-074 / `VOICE_PROFILE_ROUTE_SELECTION_READBACK_V1` / 1 |
| reference | TASK-074 / `OWNER_VOICE_PRIVATE_REFERENCE_READBACK_V1` / 1 |
| call_profile | TASK-014 / `LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2` / 2 |
| compute_admission | TASK-066 / `AUDIO_VOICE_COMPUTE_ADMISSION_V1` / 1 |
| human_plan | TASK-071 / `OWNER_VOICE_LOCAL_INFERENCE_PLAN_V1` / 1 |
| operation_ticket | TASK-072 / `OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3` / 3 |
| durable_job | TASK-076 / `DURABLE_PRODUCT_JOB_READBACK_V1` / 1 |
| inference | TASK-075 / `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1` / 1 |
| wav | TASK-014 / `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` / 1 |
| qa | TASK-048 / `OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1` / 1 |
| playback | TASK-075 / `VOICE_PLAYBACK_OBSERVATION_V1` / 1 |
| listening_join | TASK-075 / `VOICE_QA_LISTENING_BINDING_V1` / 1 |

Unknown owner/type/version/field is rejected.  Null is allowed only when the
state table below does not yet require that slot.

### 9.3 Derived-state requirements

| State | Required non-null slots and predicates |
|---|---|
| `SETUP_REQUIRED` | installed_session missing; no later success state. |
| `REFERENCE_REQUIRED` | installed_session + quick_clone current; reference missing. |
| `MODEL_SELECTION_REQUIRED` | reference current; selection missing. |
| `READY_TO_RENDER` | installed_session through call_profile + compute_admission current; no human_plan/ticket. |
| `CONFIRMATION_REQUIRED` | human_plan current; operation_ticket null. |
| `QUEUED/RUNNING/RECOVERY_REQUIRED/UNKNOWN` | ticket + durable_job; exact Job terminal/predicate chooses label. |
| `QA_REQUIRED` | inference SUCCESS + wav PUBLISHED_READBACK_VERIFIED; qa missing. |
| `LISTENING_REQUIRED` | qa PASS; playback/listening_join or Quick Clone decision incomplete. |
| `WAV_RETEST_REQUIRED` | quick_clone V2 RETEST_REQUIRED and all candidate bindings exact. |
| `WAV_ACCEPTED/WAV_REJECTED` | quick_clone V2 terminal readback + listening_join exact-current and same candidate. |
| `BLOCKED` | any missing-required, stale, mismatch, conflict, unknown version or fixture promotion attempt. |

### 9.4 Currentness/conflict/digest

Every non-null receipt must match top-level Project/manifest/install/operation
coordinates when the field is applicable; not-applicable coordinates are
explicit null.  Required current flags are true, trusted observation is before
expiry, and all Quick Clone/candidate heads agree.  For a slot, repeated exact
same hash observations collapse; two different current receipts are
`MULTIPLE_CURRENT_RECEIPTS`.  No newest/highest/mtime/first selection exists.

`reason_codes` is a sorted unique tuple, maximum 16, from:

```text
MISSING_REQUIRED_RECEIPT
UNKNOWN_RECEIPT_TYPE
UNKNOWN_RECEIPT_VERSION
STALE_RECEIPT
EXPIRED_RECEIPT
PROJECT_MISMATCH
INSTALL_MISMATCH
OPERATION_MISMATCH
QUICK_CLONE_HEAD_MISMATCH
CANDIDATE_MISMATCH
MULTIPLE_CURRENT_RECEIPTS
PRODUCER_BLOCKED
PRODUCER_UNKNOWN
FIXTURE_ONLY
FIXTURE_TAINT_MISMATCH
PRIVACY_BOUNDARY_VIOLATION
```

`fixture_lineage` has exact fields
`fixture_only, authority_created, production_eligible, fixture_set_sha256,
producer_fixture_count`.  Values are calculated over all 14 slots in fixed
order.  Any fixture or non-authoritative/non-production receipt makes output
`true,false,false`; the fixture-set hash binds every tainted non-null receipt.
Marker removal/mixing/relabel is blocked.

`composition_sha256` hashes canonical UTF-8 JSON of every preceding top-level
field in schema order.  `receipts` keys use the fixed order above and reason
codes are sorted.  Parsing/re-hashing does not create authority.

## 10. Successor mock terminal rules

The D4 mock retains 14 V6.1.1 destinations and distinct Play, Stop, Accept,
Reject, Retest and Regenerate.  Terminal candidate rules:

- Accept/Reject set an internal terminal state and disable Play/Stop/decision
  controls for that candidate;
- Reject may leave the separate Regenerate action available;
- Retest keeps the same candidate, resets playback to frame zero and requires
  a full new playback before a new decision;
- Regenerate invalidates the displayed candidate decision controls and creates
  a new in-memory operation, not a replay;
- Stop resets progress to zero and next Play starts at zero.

All operations remain in-memory mock effects only.

## 11. Verification matrix

Required positives:

- PR #470 V1 chain exact-current → Task014 V2 READY; any missing link not READY;
- call capability late-binds audio/transcript/script/model handles and burns on
  success/error;
- sink call order and one-write stream; Task075 result and Task014 POST agree;
- Task041 decision performs one Task046 CAS; RETEST cycle and new decision;
- each composition state from the exact 14-slot matrix;
- fixture taint over every slot and deterministic composition hash;
- mock terminal cannot reopen decision; Stop starts next playback at zero.

Required negatives:

- V1 public object relabelled READY, callable-envelope/hash chain mismatch;
- missing subject/plan/transcript/job/operation/auth/engine/model/runtime/
  destination/currentness;
- copied/deserialized call/sink capability, wrong consumer, out-of-order,
  second/concurrent/exception reuse;
- sink partial/empty/extra/misaligned writes, forged result, result without live
  callback, publish/readback CAS collision;
- Task041 copied receipt, stale parent, different decision same parent,
  terminal accept/reject replay, RETEST wrong WAV/cycle/playback;
- unknown receipt slot/type/version/field, missing required slot, cross-project/
  install/operation/head/candidate and multiple-current conflict;
- fixture marker drop, mixed real/fixture promotion, reason/digest reordering;
- mock Reject→Play→Accept, Accept→Play, Stop retaining progress, Retest creating
  a new candidate, Regenerate reusing the old operation;
- raw/private audio, transcript, path, SID/PID/token/secret/OS error in public
  UI/log/Evidence.

Every fault/negative asserts separate Project, Quick Clone, reference, Job,
WAV, QA, Asset, Timeline, Export and unrelated-sentinel deltas.  Unknown state
is preserved for the producer owner; TASK-073 never retries, repairs or cleans.

## 12. Implementation, PR and Gate order

1. Freeze D4/mock/manifest and obtain independent C/H=0 Judge PASS.
2. Each producer completes its own design and one coherent owner amendment PR.
3. TASK-074 TASK-072 V2 merges before TASK-075 V3 begins from fresh main.
4. TASK-073 implements schema/composition/projection with fixtures while real
   bindings remain parked.
5. Producer completions are rebound and one coherent TASK-073 implementation
   PR reaches PR_READY, then canonical COMPLETE.
6. Only then may separately authorized Outcome E TASK-036 P0-V integration run
   packaged synthetic E2E.
7. Real Owner audio runs only through the separate private native Human Gate.

The P0-V TASK-036 Gate applies only to the new Voice Studio amendment and
requires canonical D4/mock/manifest, hosted success, fresh-main hash readback,
exact Owner mock check and separate TASK-036 Task/Allowed Files/lock.  It does
not block unrelated TASK-036 work.

## 13. Prohibitions and review gate

- no TASK-073 Product source until exact D4 has independent C/H=0 Judge PASS;
- no Task036 P0-V source until its narrower Gate passes;
- no paid/cloud provider, model download, Release, Deploy or Production
  Activation;
- no real Owner audio/transcript/embedding/model weight in Git/public evidence;
- no Dataset adoption, training dispatch, ModelCandidate approval, Asset
  adoption, Timeline placement or Export;
- no raw path/backend/clock/security-hook, automatic retry/fallback, public
  capability mint, unknown-state repair, force push or unknown dirty discard.

Owner authorization cannot waive an unresolved Critical/High finding.
