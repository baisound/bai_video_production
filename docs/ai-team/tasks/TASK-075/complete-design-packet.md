# TASK-075 — Local Voice Execution and Listening

Status: DESIGN_CANDIDATE_R6 / INDEPENDENT_REVIEW_PENDING / SOURCE_START0

Profile: DEV-4 FOUNDATION CRITICAL

Design identity: TASK075-PTD-LOCAL-VOICE-EXECUTION-LISTENING-V6

Canonical design base: origin/main@354ea2534ad5739a099d9eeaf0f1da9a7210ddb6

Owner allocation: 2026-09-01 / Platform Trust & Delivery / Design B

R6 review parent: TASK-074 DESIGN_ACCEPTED_R13, TASK-073 D4 plus R1/R2/R3
closures, and TASK-076 V5.

## 1. Decision

TASK-075 owns the Product-private execution and listening composition that turns
one fresh TASK-014 Local Primary narration call into at most one local native
inference, one TASK-014-owned verified PCM WAV, one bounded playback observation,
and one listening/QA binding.

The exact Product chain is:

    unified BAI Video Production.exe startup and current Project
      -> free local model-route request
      -> LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2
      -> TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1
      -> NARRATION_OUTPUT_SINK_CAPABILITY_V1
      -> TASK-074 R13 route/reference handoff and required Gates
      -> LOCAL_VOICE_COMPUTE_ADMISSION_V1
      -> TASK-071 OWNER_VOICE_LOCAL_INFERENCE_V1 live Human receipt
      -> OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3
      -> TASK-076 durable Job and exact child custody
      -> TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1
      -> TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1
      -> OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1
      -> VOICE_PLAYBACK_OBSERVATION_V1
      -> TASK-071 OWNER_VOICE_LISTENING_DECISION_V1 live Human receipt
      -> TASK041_OWNER_VOICE_LISTENING_DECISION_V2
      -> QUICK_CLONE_FLOW_READBACK_V2
      -> VOICE_QA_LISTENING_BINDING_V1

No step may be skipped, reordered, recreated from public fields, or replaced by
an equal hash. Public records are Evidence. Authority remains in exact current
producer transactions, live nonserializable capabilities, pinned handles and
one-use broker state.

Inference, playback, listening decision, retest and regeneration are separate
operations. Rendering does not authorize playback. Playback does not mean that
the Human accepted the audio. RETEST replays the same candidate through a fresh
bounded playback operation. REGENERATE creates a wholly fresh TASK-014
operation and never reuses the prior call, sink, Human receipt, ticket, Job,
child or model execution.

TASK-075 does not train or download a model, choose or mutate a Voice Profile,
own a reference lifecycle, publish an Asset, place audio on a Timeline, call a
paid or Cloud Provider, grant Production use, release, deploy, or activate
Production.

## 2. R6 authority, precedence and supersession

### 2.1 Accepted producer design coordinates

R6 binds TASK-074 at DESIGN_ACCEPTED_R13:

- accepted task SHA-256:
  838349D63E6A390727BE58EB7B887372C34BFB7AA2A7E733BF8BE6AE3A945CA5;
- R9 packet SHA-256:
  4F1B127F34C1B61D191F8E17485DCC38F08AC991544C554C0AC3AF346EC95CF0;
- R10 addendum SHA-256:
  EF9CEA3DF0B4C86ABC0A2198E45F08A368DB0E50A99231744A81BA6014131364;
- R11 addendum SHA-256:
  CD73E8C6584C96B39D68C3A0D32E635DEC17EFC98145C7344779816400397690;
- R12 addendum SHA-256:
  38FB784A74C7A51397B3B4243566F62CB87B4CF49AAB7724986061B65DF54687;
- R13 addendum SHA-256:
  E49E35DBA314EA8D170AE182DA5983D2703DBD9E103BD387AFC32EEE03132FF5;
- independent R13 review: Critical/High/Medium/Low 0/0/0/0 and Judge PASS.

R9 is historical input, not the current completion coordinate. R10 through R13
freeze the accepted producer-side TASK074_TO_TASK075_EXECUTION_INPUT_V2,
TASK072 owner-worker begin, TASK076 process readback, child-created truth,
abort/retirement and repeated-operation boundaries. R6 consumes their semantics
and does not re-author them. TASK-074 R10 nevertheless names the older
JOB_CHILD_ARMED_READBACK_V2 lineage, while TASK-076 V5 requires the separate V3
sensitive-input protocol and explicitly forbids aliasing V2 as V3. Section 9.5
therefore records a required cross-owner version reconciliation; R13 acceptance
does not silently close that later implementation dependency.

R6 also consumes:

- TASK-073 D4 and D4-R1/R2/R3 exact call, sink, result, POST, listening and
  terminal-stage contracts;
- TASK-076 V5 durable Job and sensitive-input child custody contract;
- TASK-066 GPU-first desktop execution design;
- current TASK-014, TASK-041, TASK-046 and TASK-048 owner semantics.

### 2.2 Dependency canonicality and implementation state

The current TASK-071 V2 packet is a design candidate, not executable Authority.
TASK-072 R4 is the canonical owner-voice consumer contract, but its exact
implementation/completion receipts remain N.C. R6 consumes the R4 broker
contract without reporting TASK-071 or TASK-072 runtime effects as implemented,
current or PASS.

The required TASK-071 V2 registry has exactly these six actions:

1. OWNER_VOICE_REFERENCE_PREPARE_V1;
2. OWNER_VOICE_LOCAL_INFERENCE_V1;
3. OWNER_VOICE_LISTENING_DECISION_V1;
4. OWNER_VOICE_REGENERATE_V1;
5. OWNER_VOICE_REFERENCE_REVOKE_V1;
6. OWNER_VOICE_REFERENCE_PURGE_V1.

Only an exact live TASK071_V2_LIVE_BROKER_RECEIPT can authorize the matching
action. A fixture, confirmation string, public plan, serialized receipt,
dataclass, mapping, module sentinel, timestamp or equal hash cannot.

TASK-072 R4 canonically defines the consumer-side
OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3,
TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1, an owner-voice playback
machine-operation profile, and the runtime network-isolation readback described
in section 9. It does not own the Task066 compute or network-enforcement
producers. Until the required producer and consumer completion receipts exist,
the affected native effect is zero.

TASK-072, TASK-074 and TASK-076 must also freeze a version-discriminated
owner-voice amendment that binds TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1,
TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1 and
TASK074_REFERENCE_WORKER_DELEGATION_V1 to the exact Task076 V3 arm, five-budget,
bootstrap, abort and terminal lineage. JOB_CHILD_ARMED_READBACK_V2 cannot be
relabeled, rehashed or compatibility-promoted to V3. Until that owner amendment
is canonical, Task074 G11 remains OPEN / DEPENDENCY_NC / EFFECT_ZERO for native
TASK-075 execution.

That amendment must also supersede, and not silently reinterpret, TASK-074 R11's
older statement that a TASK-076 producer broker owns the live Job handle. In the
V3 lineage, TASK-072 alone owns the sole noninheritable live Job containment
handle and executes the serialized abort/kill-on-close operation. TASK-076 owns
the durable Job record, selected current generation and body-free process/Job
custody readback only. TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1 must be
explicitly frozen/versioned for the V3 vector; an older custody identity cannot
be reused, relabeled or aliased. Until the coordinated amendment is accepted,
neither wording nor ABI creates native Authority.

TASK-073 D4 currently freezes its `compute_admission` allowlist to TASK-066
`AUDIO_VOICE_COMPUTE_ADMISSION_V1` version 1 and rejects every unknown
owner/type/version. TASK-075 cannot supersede that consumer contract. Before R6
can consume `LOCAL_VOICE_COMPUTE_ADMISSION_V1` version 1, a TASK-073-owned
non-alias allowlist amendment must retire AUDIO for this D4 chain, accept LOCAL
exactly, preserve the existing result field/nullability/stage rules and prove
that equal hashes, relabeling and dual acceptance are rejected. The Task066
producer amendment and Task073 consumer amendment are separate completion
receipts. Until both exist, compute admission is DEPENDENCY_NC and execution
effect is zero.

The same amendment must freeze one non-circular order and its adapter bindings:
pre-issue gates -> atomic G07 OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3 issue -> one
Task074 attachment plus one metadata-only TASK076_EXTERNAL_BINDING_SLOT_V1 ->
Task076 V3 arm -> TASK074/TASK072 attachment-begin CAS bound to the armed vector
-> selected TASK076 IN_FLIGHT -> bootstrap/process/custody -> owner bind and
preflight. The slot must name exact Task074 child-bind, body-free preflight and
remote-close/recovery adapter ABIs plus their accepted owner receipts. Those
three adapter ABIs are not yet canonically frozen. TASK074_REFERENCE_BEGIN_ATTACHMENT_V1,
TASK074_TO_TASK075_EXECUTION_INPUT_V2 and a generic issue/revoke CAS cannot be
miscast as those slot ABIs. The live attachment is never serialized into the
slot. Until the exact adapter identities, issue/arm/begin transaction boundary
and recovery semantics are accepted, this order is DEPENDENCY_NC / EFFECT_ZERO,
not executable sequence Authority.

The coordinated Task075/Task072/Task074/Task076 owner amendment must separately
accept TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1 and
TASK075_NETWORK_NONCURRENT_OPERATION_TERMINAL_V1 for post-release currentness
loss as private arm payloads, plus exactly one
TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 as the sole Task076 V3 consumer
terminal input. It must bind
the Task074 post-release remote-close/BURNED-or-FAILED_CLOSED rules, Task076
durable terminal/currentness and the exact Task014 receipt-only result without
creating a D4 result. A separate Task014-owned amendment must expose exact call
and sink terminal readbacks. Until both amendment layers are accepted, the
post-release path is BURNED_UNKNOWN containment only.

There is a separate Task014 compatibility gap. The exact D4
TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1 is minted with both Task074 reference
leases and publicly exposes open_reference_audio and open_reference_transcript
to its in-process consumer. Task074 R10-R13 instead requires Task074 to transfer
both handles directly into the child-local broker while the TASK-075 parent has
reference body authority zero. Those surfaces cannot be treated as structurally
equivalent. A Task014/Task074 owner amendment must freeze a broker-held or
consumer-restricted capability revision that preserves the D4 call/result/sink
bindings while making parent reference open structurally impossible. Until it
is accepted, native reference-body/model effect is zero. TASK-075 does not hide
the conflict by promising not to call an available method.

### 2.3 R6 compute/network-currentness correction

R6 supersedes R5 only where R5 omitted the exact Task076 V3 closure after a
previously admitted Task066 compute coordinate or network producer/projection
becomes expired, stale, cross-build, cross-model or otherwise noncurrent. The
correction freezes:

- orphan/prebootstrap closure before process creation;
- the exact V3 tagged abort claim/commit sequence after bootstrap;
- Task074 remote-close/terminal-retirement and Task076 durable terminal joins;
- no reissue, rebind, second release, model retry or second child;
- no D4 result when exact current compute or network receipt requirements are
  not met, plus private post-release terminal or BURNED_UNKNOWN containment; and
- body-free operational status plus exact durable safety terminal only.

R5's independent design-only review is Evidence, not R6 acceptance. No R5
receipt, public result or equal hash authorizes this correction.

### 2.4 R5 inheritance and R4 supersession

This R6 packet supersedes the R5 identity and all R4 names, hashes and orderings
listed in section 20. Valid R5/R4 fail-closed, privacy, no-paid-provider,
no-download, no-blind-retry, no-foreign-cleanup and body/path-free diagnostics
clauses remain in force where they do not conflict with R6.

## 3. Fresh source-backed gap

Current canonical source still stops before this complete boundary:

- owner_narration_local_primary.py stops at READY_FOR_OWNER_HUMAN_GATE;
- owner_narration_local_render_admission.py stops at
  READY_FOR_EXTERNAL_DISPATCH_GATE;
- Task014 has no completed D4 call/sink/POST implementation receipt;
- public TASK-066 probe/capability data is not a trusted launch capability;
- TASK-071 producer implementation and TASK-072 R4 consumer implementation
  receipts are not canonical-complete;
- Task076 owns the durable Job/child protocol, but TASK-075 has no implemented
  adapter that follows its V3 custody sequence;
- no exact runtime network-isolation receipt exists for the TASK-075 result ABI;
- no implementation streams signed PCM24 frames from one attested worker into
  the Task014-owned sink;
- voice_quality_calibration.py does not perform inference or playback;
- audio_workspace_media_review.py does not prove Product playback;
- task036_packaged_entry.py and task036_shell_ui.py do not yet expose the
  complete model-selection, Auto/GPU/CPU and generate/listen flow.

Historical fixtures and passing unit tests remain regression Evidence. They do
not prove native execution, Human authority, offline isolation, WAV durability,
playback or Production eligibility.

## 4. Responsibility boundary

TASK-075 owns:

- the exact consumer composition of accepted producer ABIs;
- one local inference semantic key and state machine;
- the parent-side authenticated worker protocol and PCM24 stream validation;
- TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1 production;
- one bounded local playback observation;
- VOICE_PLAYBACK_OBSERVATION_V1;
- VOICE_QA_LISTENING_BINDING_V1;
- body/path-free public status;
- focused, fault, restart, packaging and Windows-native QA for this boundary.

TASK-075 does not own:

- Project and installed-startup currentness: TASK-036;
- narration plan, call capability, output sink and POST: TASK-014;
- selection, reference lifecycle, reference-domain transaction, direct
  reference delegation or retained-object purge: TASK-074;
- compute preference, workload admission, effective backend and enforceable
  network-isolation producer: TASK-066;
- Human challenge, user-presence or live Human receipt: TASK-071;
- ticket/config, child broker, begin readback, broker abort/kill-on-close handle,
  network-isolation consumer projection or playback machine profile: TASK-072;
- durable Job record, selected current generation and exact child/process/Job
  custody readback: TASK-076;
- technical QA: TASK-048;
- listening decision: TASK-041;
- Quick Clone lifecycle and current head: TASK-046;
- generic authority I/O: TASK-068;
- installer, package, Provider, Credential, Asset, Timeline, Release, Deploy or
  Production Activation.

The accepted Task074 topology requires the TASK-075 parent to receive, open,
duplicate, inherit, close and reopen exactly zero zero-shot reference roles.
TASK-074 transfers both roles directly to the exact Task076/Task072 child-local
broker. The parent does own the authenticated control/PCM channel and the
Task014 live sink session. The child never receives a destination path, Task014
WAV handle or permission to publish the WAV. Because the current exact D4 call
capability still exposes parent reference-open methods, this topology remains
the section 2.2 Task014 compatibility N.C. rather than a claimed current PASS.

## 5. Canonical documents and source references

MUST READ for R6 implementation:

- docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4.md;
- docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r1-closure.md;
- docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r2-closure.md;
- docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r3-closure.md;
- docs/ai-team/tasks/TASK-074/task.md;
- docs/ai-team/tasks/TASK-074/complete-design-packet-r10-addendum.md;
- docs/ai-team/tasks/TASK-074/complete-design-packet-r11-addendum.md;
- docs/ai-team/tasks/TASK-074/complete-design-packet-r12-addendum.md;
- docs/ai-team/tasks/TASK-074/complete-design-packet-r13-addendum.md;
- docs/ai-team/tasks/TASK-074/design-r13-review-receipt.md;
- docs/ai-team/tasks/TASK-076/complete-design-packet.md;
- docs/ai-team/tasks/TASK-066/gpu-first-desktop-execution-design-2026-08-31.md.

Exact current source references:

- src/ai_video_production/owner_narration_local_primary.py;
- src/ai_video_production/owner_narration_local_render_admission.py;
- src/ai_video_production/voice_quality_calibration.py;
- src/ai_video_production/audio_workspace_media_review.py;
- src/ai_video_production/durable_product_job.py;
- src/ai_video_production/task036_packaged_entry.py;
- src/ai_video_production/task036_shell_ui.py.

TASK-071 candidate worktree material may be read only to evaluate the named
dependency and cannot be consumed as canonical Authority. TASK-072 R4 may be
consumed only as its canonical consumer contract; unmerged worktree effects,
fixtures and missing implementation receipts remain non-Authority.

## 6. Design and implementation scope

This R6 Atomic Unit may change exactly:

- docs/ai-team/tasks/TASK-075/complete-design-packet.md.

Source, schema, test and native effects are zero. A future implementation
requires:

- independent R6 Critic with Critical/High 0/0;
- Judge PASS;
- exact completion receipts for every N.C. dependency in section 19;
- fresh main, branch, worktree, dirty, overlap and lock audit;
- a separate exact implementation start receipt and Allowed Files.

Potential source names in an earlier design are not implementation authority.
In particular, a filename does not authorize edits to Task014, Task036, Task041,
Task046, Task048, Task066, Task071, Task072, Task074 or Task076.

Changes to shared current-state, task-index, roadmap, CHANGELOG, installer/build
specs, pyproject.toml, another Task, Release, Deploy or Production Activation are
not allowed by this design.

## 7. Trust and threat boundary

### 7.1 Trusted Production composition

Production fixes and attests:

- packaged BVP parent image/build and installed startup session;
- one packaged TASK-075 worker image/build/protocol;
- Task014 live call and sink capabilities;
- Task074 live reference delegation and domain transaction;
- Task066 admitted compute/model/runtime handles;
- Task071 live Human receipt;
- Task072 ticket, child broker and machine-operation profile;
- Task076 selected Job generation and child-process readback;
- Windows user/session/token/Job/handle/currentness implementation;
- trusted UTC plus monotonic/boot/session time supplied by the owning broker.

No argv, environment, current directory, raw path, model label, UI mapping,
public JSON, module token, Python hook, injected backend or caller clock selects
the Production engine, model, compute route, child, reference, sink, player,
Human action or receipt verifier.

### 7.2 Protected failures and attacks

R6 fails closed against:

- public-object construction, copy, replace, pickle, deserialization and rehash;
- caller-selected script, profile, model, action, ticket, path, time or backend;
- replay, concurrent consume, exception reuse and random-ID retry;
- wrong Project/install/build/process/user/session/token/parent;
- same bytes at a different physical identity;
- hardlink, reparse, ancestor, DACL and operation-root drift;
- partial reference-pair transfer and wrong worker;
- missing or forged network isolation;
- malformed, oversized, reordered, replayed or trailing child frames;
- partial, empty, malformed or oversized PCM/WAV;
- output/sink/result/POST/QA/playback/decision cross-operation substitution;
- path, script, voice, PCM, model, OS detail or secret leakage;
- cleanup of an unknown or foreign object.

### 7.3 Explicit non-goals

R6 does not claim resistance to administrator/kernel compromise, debugger or
process injection into a trusted process, compromised release signing, memory
extraction, speaker/microphone recapture, or a Human deliberately sharing the
generated audio.

## 8. Exact producer and consumer ABI table

| Slot/phase | Owner and exact ABI | TASK-075 use | Authority class |
|---|---|---|---|
| startup | TASK-036 INSTALLED_STARTUP_CONTEXT_V1 | exact install/session and unified EXE currentness | durable readback |
| quick clone | TASK-046 QUICK_CLONE_FLOW_READBACK_V2 | candidate/head/listening lifecycle | durable readback |
| selection | TASK-074 VOICE_PROFILE_ROUTE_SELECTION_READBACK_V1 | selected local route | durable readback |
| reference | TASK-074 OWNER_VOICE_PRIVATE_REFERENCE_READBACK_V1 | reference currentness only | private readback |
| reference lifecycle | TASK-074 OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1 | prepare/revoke/retained/purge CAS | durable transaction |
| call profile | TASK-014 LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2 | exact narration call | immutable Evidence |
| call authority | TASK-014 TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1 | one dispatch | live one-use capability |
| output | TASK-014 NARRATION_OUTPUT_SINK_CAPABILITY_V1 | parent-side PCM24 stream and WAV commit | live one-use capability |
| route handoff | TASK-074 TASK074_TO_TASK075_EXECUTION_INPUT_V2 | exact route-neutral execution input | live sealed handoff |
| begin attachment | TASK-074 TASK074_REFERENCE_BEGIN_ATTACHMENT_V1 | bind one reference lease to one child begin | live one-use attachment |
| attachment begin | TASK-072 TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1 | atomically consume attachment and advance lease | owner broker transaction |
| reference transfer | TASK-074 TASK074_REFERENCE_WORKER_DELEGATION_V1 | direct exact-child audio/transcript pair transfer | live delegation |
| child custody | TASK-076 TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1, V3 freeze pending/no alias | exact dedicated Job membership/containment truth | private readback, DEPENDENCY_NC |
| remote close | TASK-074 TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1 | exact child role close/exit proof | private readback |
| terminal retirement | TASK-074 TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1 | immutable terminal history plus fresh fence | private readback |
| compute producer | TASK-066 LOCAL_VOICE_COMPUTE_ADMISSION_V1 | admitted workload/model/runtime and effective CPU/CUDA route | sealed producer admission; TASK-073 D4 allowlist amendment DEPENDENCY_NC |
| Human plan | TASK-071 OWNER_VOICE_LOCAL_INFERENCE_PLAN_V1 | composition Evidence | durable/public Evidence |
| Human authority | TASK-071 TASK071_V2_LIVE_BROKER_RECEIPT | exact action | live nonserializable receipt |
| ticket | TASK-072 OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3 | one inference child operation | one-use ticket |
| owner begin | TASK-072 TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1 | exact child-operation begin | required readback |
| Job | TASK-076 DURABLE_PRODUCT_JOB_READBACK_V1 | selected durable generation | durable readback |
| process | TASK-076 TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1 | child/process/Job identity | required readback |
| network enforcement producer | TASK-066 owner amendment, exact ABI pending | enforceable Windows child-network denial and executed observation | producer receipt, DEPENDENCY_NC |
| network broker projection | TASK-072 TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 | exact-child consumer projection over the Task066 enforcement receipt | required consumer readback, DEPENDENCY_NC |
| inference | TASK-075 TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1 | terminal execution Evidence | typed Evidence plus live callback |
| compute-noncurrent arm | TASK-075 TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1 | private COMPUTE_ONLY arm payload; never independently passed to Task076 | required private ABI, DEPENDENCY_NC |
| network-noncurrent arm | TASK-075 TASK075_NETWORK_NONCURRENT_OPERATION_TERMINAL_V1 | private NETWORK_ONLY arm payload; never independently passed to Task076 | required private ABI, DEPENDENCY_NC |
| noncurrent terminal union | TASK-075 TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 | sole post-release compute/network/combined child-owner-Task014 terminal coordinate; never D4 output | required private ABI, DEPENDENCY_NC |
| WAV | TASK-014 TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1 | committed staged WAV truth | durable receipt |
| QA | TASK-048 OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1 | technical PASS/FAIL/UNKNOWN | durable receipt |
| playback | TASK-075 VOICE_PLAYBACK_OBSERVATION_V1 | full bounded local playback | typed observation |
| decision | TASK-041 TASK041_OWNER_VOICE_LISTENING_DECISION_V2 | ACCEPT/REJECT/RETEST | durable Human decision |
| final join | TASK-075 VOICE_QA_LISTENING_BINDING_V1 | POST+QA+playback+decision+flow join | bounded binding |

TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 is a required Task072 consumer
projection, not an enforcement producer and not an implemented or accepted
Authority. A separate TASK-066-owned amendment must first freeze and implement
the enforceable network producer receipt. TASK-072 must then freeze the exact
consumer projection over that receipt, and TASK-075 must be re-reviewed against
both accepted identities.

The compute row likewise does not modify TASK-073 D4. Its current AUDIO allowlist
remains authoritative until the separate TASK-073 owner amendment accepts LOCAL
version 1 and rejects AUDIO/no-alias. TASK-075 matching fields or a Task066
producer receipt cannot bypass that consumer Gate.

Unknown owner, name, version, additional field or fixture lineage is rejected.
An ABI-compatible public mapping cannot replace a live capability.

## 9. Required producer contracts

### 9.1 Task014 call profile and sink

LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2 is the D4/R1 exact profile. It binds one
Project, installed session, operation plan, Quick Clone flow/head, private
reference revision, Voice Profile and route selection, script/style/language,
model/runtime recipe, and:

- route_mode = ZERO_SHOT_LOCAL;
- intended_usage = PREVIEW;
- sample_rate_hz = 48000;
- channels = 1;
- sample_format = PCM_S24LE;
- positive max_frames and current expiry.

The profile contains no script body, reference body, model path, output path,
OS handle, backend choice or capability.

TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1 is live and one-use:

    READY -> IN_FLIGHT -> RESULT_BOUND -> CONSUMED
    any nonterminal -> FAILED_CLOSED

Its begin_dispatch method returns the exact dispatch lease. Entry, mismatch,
concurrency or BaseException burns the capability. Restart never resurrects it.

The complete current D4 callable surface is:

    inspect_profile()
    open_reference_audio()
    open_reference_transcript()
    open_script_text()
    inspect_model_runtime()
    begin_dispatch(task075_consumer_identity)
    fail_closed(reason_code)

The two reference-open methods are precisely the section 2.2 compatibility
N.C. They cannot be omitted from the review model, called by the parent, or
treated as harmless merely because trusted TASK-075 code intends not to call
them. A future compatible owner capability must make the Task074 direct-child
delegation and parent-authority-zero property structural.

NARRATION_OUTPUT_SINK_CAPABILITY_V1 binds the exact call profile, operation,
installed session, format, max_frames, max_output_bytes, Task014-owned staging
handle identity and writer build. Its exact surface is:

    begin(call_dispatch_lease) -> SINK_WRITE_SESSION | SINK_REJECTED
    inspect_terminal(task014_owner_identity) -> SINK_TERMINAL_SNAPSHOT
    fail_closed(reason_code) -> FAILED_CLOSED

The write session exposes:

    write_pcm24(frame_bytes) -> WRITE_ACCEPTED | WRITE_REJECTED
    finish(frame_count, waveform_sha256) -> SINK_WRITE_RESULT
    abort(reason_code) -> FAILED_CLOSED

State is:

    READY -> WRITING -> BODY_VERIFIED -> RESULT_BOUND -> CONSUMED
    any nonterminal -> FAILED_CLOSED

TASK-075 never chooses, opens, reopens, replaces, publishes, deletes or exposes
the destination. The worker never receives this sink or its handle.

### 9.2 Task074 R13 handoff and Gates

TASK-075 accepts only TASK074_TO_TASK075_EXECUTION_INPUT_V2 and
TASK074_REFERENCE_WORKER_DELEGATION_V1 from the accepted R13 producer. It does
not reconstruct the handoff from public selection/reference records.

The accepted route union remains closed. The exact V2 subvariant names are:

- ZERO_SHOT_REFERENCE_INPUT_V2 under route_mode ZERO_SHOT_LOCAL requires the
  exact reference audio plus UTF-8 transcript pair, media policy,
  TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1 and one shared lease.
  ModelCandidate fields are forbidden.
- FINE_TUNED_MODEL_INPUT_V2 under route_mode FINE_TUNED_LOCAL requires the
  exact admitted ModelCandidate and forbids every reference field, role, handle
  and body read.

The accepted Task074 union is broader than the current Task073 D4/R1 call ABI.
R6 execution V1 accepts only ZERO_SHOT_LOCAL with intended_usage PREVIEW because
LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2 fixes those exact values. The
FINE_TUNED_LOCAL branch remains schema/currentness Evidence and a negative-test
input; it returns ROUTE_NOT_SUPPORTED_BY_CALL_PROFILE / effect zero until a
separately versioned Task014 profile and fresh TASK-075 review exist. It is never
silently projected into ZERO_SHOT_LOCAL.

TASK-075 requires the accepted Task074 Gate truth, including:

| Gate | Exact required truth |
|---|---|
| G01 | CANONICAL_PROJECT_STORE_BOOTSTRAP_V1 |
| G02 | INSTALLED_STARTUP_CONTEXT_V1 |
| G06 | exact TASK-071 V2 live receipt for the requested action |
| G07 | exact TASK-072 one-use private ticket/profile |
| G08 | trusted picker/resolver, pinned source and custody capability |
| G09 | prepared/revoked/retained state plus exact-owned identity and separate purge authority |
| G10 | TASK046_VOICE_ROUTE_SELECTION_AMENDMENT_ACCEPTANCE_V1 |
| G12 | OWNER_VOICE_TRUSTED_TIME_RECEIPT_V1 |
| G14 | TASK046_OWNER_REFERENCE_TRANSCRIPT_BINDING_V1 |

The remaining accepted R13 Gates G03-G05, G11 and G13 must also be current
inside the producer handoff. G11 additionally requires the exact Task076 V3
version reconciliation in section 2.2; an R10 V2 begin lineage is not executable
against the V3 sensitive-input path. TASK-075 may not synthesize a missing Gate.

The effective Task074 V2 delegation lease path is:

    ISSUED
      -> IN_FLIGHT_PARENT_DELEGATION
      -> CHILD_TRANSFER_IN_FLIGHT
      -> CHILD_PAIR_READY
      -> BODY_READ_STARTED
      -> CONSUMED | BURNED | FAILED_CLOSED

CHILD_PAIR_READY requires both child-local roles verified and both parent
originals exact-close read back. The child may open bodies only after its single
BODY_READ_STARTED CAS. CONSUMED requires exact two-role read completion, child
role close proof and the bound TASK-075 consumer terminal. BURNED requires exact
abort and all-handle close proof. FAILED_CLOSED retains every unknown effect and
cannot be relabeled.

After any terminal V2 lease with proven handle count zero, the same broker/domain
calls TASK074_REFERENCE_V2_TERMINAL_RETIRE_CAS_V1 and obtains
TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1. The indivisible R13 operation
preserves one immutable terminal history event, clears current V2 to
V2_ABSENT/0 and advances the fresh fence. A later operation may issue only from
that fresh fence with distinct ticket, lease, attachment, begin, child and
operation identities. Retirement, revoke or expiry have one CAS winner. Reply
loss is resolved only from exact history and current-fence readback; no second
append, clear, issue or PASS inference is permitted.

### 9.3 Task066 compute

Task066 alone resolves the user preference, workload class and actual admitted
backend. The effective backend in TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1 is
CPU or CUDA only. AUTO is a preference, never an effective result.

The post-amendment target compute producer ABI is
LOCAL_VOICE_COMPUTE_ADMISSION_V1. It binds the current install, Project,
operation, workload, selected model and runtime, requested preference, effective
backend, build identity, expiry and producer currentness. Current TASK-073 D4
still allowlists AUDIO_VOICE_COMPUTE_ADMISSION_V1. R6 does not retire or rewrite
that canonical consumer. Only the section 2.2/19 TASK-073 owner amendment may
retire AUDIO and accept LOCAL version 1; it must provide no alias, relabel,
rehash, dual-acceptance or compatibility form. Until then this target is
DEPENDENCY_NC / EFFECT_ZERO.

No fallback is permitted after the operation is admitted or child dispatch
begins. A CUDA failure terminates the operation; it does not silently retry on
CPU under the same call, ticket or Job.

### 9.3.1 Task066 post-admission currentness and V3 closure

LOCAL_VOICE_COMPUTE_ADMISSION_V1 is revalidated before V3 arm, before bootstrap
creation, immediately after bootstrap/current process custody, before owner bind,
before preflight, before Artifact prepare, before release and before result
formation. Expiry, stale producer generation, install/Project/operation drift,
worker-build mismatch, model/runtime digest mismatch, effective-backend drift or
revocation is `COMPUTE_ADMISSION_NONCURRENT`, a body-free Product operational
status outside the closed D4 reason-code ABI. It never refreshes or replaces the
admission inside the operation.

The only legal closure depends on the exact durable V3 phase:

| Exact observation | Required Task076 V3 closure | Forbidden effect |
|---|---|---|
| before a Task076 DISPATCHING candidate is published/selected | reject/burn the matching G07 operation with child/vector/candidate effect zero | candidate, arm, child or retry |
| exact Task076 DISPATCHING selected but V3 arm/vector not created | exact Task072 pre-effect rejection returns JOB_CHILD_REJECTED_READBACK_V3; append a predecessor-correct immutable FAILED_KNOWN candidate and select it only through TASK043 currentness, or append/select BURNED_UNKNOWN if rejection/commit truth is unknown; exact Task074 ABSENT_PROVEN-or-ISSUED attachment/V2 lease closure is mandatory | candidate zero claim, inferred attachment absence, arm, child or retry |
| ARMED with exact unselected IN_FLIGHT candidate while DISPATCHING is current | abort_armed_orphan_job_child_v3 -> JOB_CHILD_ORPHAN_ABORTED_READBACK_V3 or JOB_CHILD_BURNED_UNKNOWN_READBACK_V3; exact-read and terminalize either ISSUED attachment/lease or CONSUMED attachment/IN_FLIGHT_PARENT_DELEGATION | select, bootstrap or second arm |
| exact selected IN_FLIGHT before bootstrap process creation | abort_armed_prebootstrap_job_child_v3 -> JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3 or JOB_CHILD_BURNED_UNKNOWN_READBACK_V3; terminalize exact CONSUMED attachment/IN_FLIGHT_PARENT_DELEGATION | create or second child |
| BOOTSTRAP_WAITING before any owner role transfer | claim_job_child_abort_v3 with BEFORE_PREPARE/NONE_IF_NEVER_BOUND and JOB_CHILD_ARTIFACT_NEVER_ENTERED_READBACK_V3 | bind, preflight, prepare or release |
| JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3, JOB_CHILD_EXTERNAL_BINDING_FAILED_CLOSED_READBACK_V3, JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3 or JOB_CHILD_EXTERNAL_INPUT_FAILED_CLOSED_READBACK_V3 | claim_job_child_abort_v3 with BEFORE_PREPARE and that exact tagged current_phase | another bind/preflight or release |
| JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3 | PREPARE_IN_PROGRESS with that exact pending readback; only the matching prepare transaction may resolve Artifact truth and return ABORT_PENDING or BURNED_UNKNOWN | guessed NONE/PREPARED truth, second prepare or release |
| JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3 or JOB_CHILD_ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED_READBACK_V3 | AFTER_PREPARE with that exact readback | target cleanup, replacement or release retry |
| JOB_CHILD_RELEASE_REJECTED_ABORT_REQUIRED_READBACK_V3 | AFTER_RELEASE_REJECTED with that exact readback | second release |
| release already won and JOB_CHILD_STARTED_READBACK_V3 is returned | no bootstrap abort; fixed child exits and only an accepted section 9.7.2 exactly-one terminal union, four-owner consumer amendment, exact Task014 call/sink FAILED_CLOSED plus receipt-only fourth argument and exact Task074 owner-lease third argument permit read_job_child_terminal_v3; otherwise BURNED_UNKNOWN | arm-only terminal call, rebind, second release, resume, D4 result or model retry |

The selected-DISPATCHING/pre-arm, process-not-created orphan and prebootstrap
rows also require an exact Task074 terminal join; a Task072 rejection or Task076
no-process terminal is not sufficient by itself. The owner broker reads the
exact attachment and V2 lease generation:

- selected-DISPATCHING/pre-arm exact-reads either an authoritative attachment
  `ABSENT_PROVEN` plus V2 lease `ISSUED`, or attachment `ISSUED` plus V2 lease
  `ISSUED`. Missing path, receipt silence or an absent live object is not
  ABSENT_PROVEN. In the first tuple there is no attachment to burn, but the
  exact lease, parent originals and remote-role absence still terminalize. An
  ARMED/unselected orphan reads either the ISSUED tuple or the consumed tuple
  below and must not guess which atomic begin outcome won;
- for an unconsumed attachment, the only valid predecessor is attachment
  `ISSUED` plus V2 lease `ISSUED`; it burns that exact attachment, closes the
  two exact parent originals without reading them, and proves both child roles
  `ABSENT_PROVEN`;
- for a consumed attachment, the only valid predecessor is attachment
  `CONSUMED` plus V2 lease `IN_FLIGHT_PARENT_DELEGATION`; it closes the begun
  lease and the two exact parent originals, proves both child roles
  `ABSENT_PROVEN`, and never reopens the parent body gate. The selected
  prebootstrap row necessarily has this begin lineage;
- `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3` or
  `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3` must prove
  `child_process_created=false`. That proof forbids fabricating child
  terminate/wait, remote-created or model-effect receipts;
- only exact attachment/lease consumption or burn, parent close, remote-role
  absence, child-process false and handle count zero permits Task074 `BURNED`.
  Any unknown or mixed generation is `FAILED_CLOSED / NOT_CONFIRMED` and blocks
  R13 retirement and a new issue;
- R13 retirement consumes the current BURNED or retireable FAILED_CLOSED
  terminal only after handle count zero. It never upgrades FAILED_CLOSED to
  BURNED and never clears an unknown current lease.

For the BOOTSTRAP_WAITING/no-transfer case, the exact call is:

    claim_job_child_abort_v3(
        EXACT_CURRENT_TASK076_IN_FLIGHT_READBACK,
        JOB_CHILD_ARMED_READBACK_V3,
        JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3,
        BEFORE_PREPARE {
            current_phase: NONE_IF_NEVER_BOUND,
            artifact_truth: JOB_CHILD_ARTIFACT_NEVER_ENTERED_READBACK_V3
        },
        COMPUTE_ADMISSION_NONCURRENT
    )

Only JOB_CHILD_ABORT_PENDING_READBACK_V3 authorizes close. With no transferred
role, Task074 proves both child roles were never accepted, closes the exact two
parent originals under the already body-disabled lease and supplies
NONE_IF_NO_ROLE_TRANSFER. With partial or complete transfer, it supplies only the
exact OWNER_EXTERNAL_INPUT_CLOSED_READBACK_V1 for that tagged phase. Task072 then
terminates and waits the exact contained child exactly once and supplies
JOB_CHILD_TERMINATED_WAITED_READBACK_V3. The matching
commit_job_child_abort_v3 returns JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3 or
JOB_CHILD_BURNED_UNKNOWN_READBACK_V3; no other closure spelling is legal.

Known abort completion proceeds only as JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3
-> TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1 -> Task074 V2 BURNED terminal
-> TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1 -> predecessor-correct
Task076 durable terminal/current-generation readback. Each arrow consumes only
the exact prior readback; it is not a retry or authority transfer.
Unknown owner-close, terminate/wait, Artifact truth, Task074 lease or Task076
terminal truth uses contain_burned_unknown_job_child_v3 and remains UNKNOWN; it
is never relabeled as known abort or effect zero.

Every row above is a live, same-broker observation path except one canonical
restart-safe no-process CAS. After Product, broker or worker restart, a
DISPATCHING-current exact unselected orphan may use only
`abort_armed_orphan_job_child_v3`; its CAS must prove process-create was never
entered. An already durable `JOB_CHILD_ABORT_PENDING_READBACK_V3` may otherwise
only be exact-queried and finished as that same claim. Every other unselected or
selected prebootstrap state, and every BOOTSTRAP_WAITING, BOUND,
BINDING_FAILED, VALIDATED, INPUT_FAILED, PREPARE_PENDING, PREPARED,
PREPARE_FAILED or RELEASE_REJECTED observation without the exact pre-crash
ABORT_PENDING is `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3` and proceeds only
through `contain_burned_unknown_job_child_v3`. Restart never initiates a fresh
selected-prebootstrap or tagged abort claim, normal V3 owner-close, bind,
preflight, prepare, release or retry. The orphan-only exception still closes
Task074 through its exact durable recovery state; it never reconstructs a live
attachment or delegation object. Existing ORPHAN_ABORTED,
PREBOOTSTRAP_ABORTED, BOOTSTRAP_REJECTED or BOOTSTRAP_ABORTED terminals are
query-only and never invoke another abort.

Before a release winner, currentness failure forbids admission reissue,
config/model rebind, release, body read, model load/call, PCM sink write/commit,
POST, playback, listening decision and a second child. An already-started
Task014 receipt-only prepare/sink session is exact-terminalized, not counted as
output effect zero and not restarted. After a release winner, the release and
any already-started model, consumer or sink effect are retained as exact
`TRUE | FALSE | UNKNOWN`; only *new* or retried effects are forbidden. POST,
playback and listening decision remain zero. Every phase preserves every
foreign or uncertain object and performs cleanup/delete zero.

R6 mints no TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1 for this noncurrent compute
path because task066_admission_sha256 is no longer a current producer binding.
Independently, if the exact current Task066 network producer plus Task072
projection cannot provide the mandatory non-null network receipt hash, D4 also
permits no result from CHILD_CREATED onward. The only Product-visible output is
stable body-free operational status plus the exact Task074/Task076 durable safety
terminal; no fabricated FAILED_KNOWN or UNKNOWN result is allowed.

### 9.3.2 Post-release compute private terminal arm N.C.

After JOB_CHILD_STARTED_READBACK_V3, Task076 cannot call
read_job_child_terminal_v3 without an exact child-exit/result coordinate, exact
owner-lease terminal and a semantic consumer-result digest. The public D4 result
cannot supply them when compute admission is noncurrent. R6 therefore requires a
separate owner-reviewed private ABI:

    TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1

It is a body-free, path-free, nonserializable arm payload and never a substitute
for TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1. Its domain-only fields bind:

- the exact previously current Task066 admission identity/digest and its bound
  install, Project, operation, workload, model/runtime, effective backend and
  producer-build coordinates;
- one nonempty, sorted, unique and bounded mismatch-code set drawn only from
  EXPIRED, PRODUCER_GENERATION_DRIFT,
  INSTALL_PROJECT_OPERATION_DRIFT, WORKER_BUILD_DRIFT,
  MODEL_RUNTIME_DRIFT, EFFECTIVE_BACKEND_DRIFT or REVOKED;
- the trusted pinned result-formation observation identity/digest and one
  domain-arm digest. It contains no child-exit, Task014, Task074, Task076 or
  shared effect/terminal field.

This compute object is a private arm payload, not an independently callable
Task076 coordinate. Only section 9.7.2's exactly-one tagged union may carry this
arm; it never calls read_job_child_terminal_v3 by itself.

Until TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1, the section 9.7.2 union,
its four-owner consumer amendment and the Task014 terminal/receipt-only
amendment are accepted, any compute drift observed after release is
JOB_CHILD_BURNED_UNKNOWN_READBACK_V3 plus exact recovery containment only.
Task076 may not report an unspecified exact terminal and Task074 may not retire
an unproven live-handle state.

### 9.4 Task071 Human actions

The six Task071 V2 actions are not interchangeable:

| Action | Exact purpose | Terminal/effect rule |
|---|---|---|
| OWNER_VOICE_REFERENCE_PREPARE_V1 | prepare private reference domain | terminal prepare receipt; not inference authority |
| OWNER_VOICE_LOCAL_INFERENCE_V1 | authorize one exact call/compute/ticket/Job | success, denial, expiry or exception burns it |
| OWNER_VOICE_LISTENING_DECISION_V1 | authorize one ACCEPT/REJECT/RETEST decision | one Task041 decision only |
| OWNER_VOICE_REGENERATE_V1 | request a new narration operation | creates a fresh Task014 chain; never replays |
| OWNER_VOICE_REFERENCE_REVOKE_V1 | prevent future use | no body deletion |
| OWNER_VOICE_REFERENCE_PURGE_V1 | separately authorize exact-owned purge | only after G09 and exact domain transaction |

Playback itself is not a Task071 Human action. The Play button is an explicit
request for a bounded machine operation. Human authority is required for the
subsequent listening decision. Treating playback as an approval is forbidden.

### 9.5 Task072 and Task076 child custody

The following is the only post-amendment target order. It is not executable
Authority until the coordinated section 2.2 amendment and section 19 completion
receipts are accepted:

1. resolve current Project, call, Task074, compute, Task071 Human and all exact
   TASK-072 R4 pre-issue gates;
2. TASK-072 atomically issues G07 and returns exactly one current
   OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3; G11 is not a ticket prerequisite;
3. prepare, publish and select the exact Task076 DISPATCHING plan/candidate for
   that ticket;
4. from Task074 PREPARED/ISSUED, create exactly one
   TASK074_REFERENCE_BEGIN_ATTACHMENT_V1 for this ticket/Job/consumer;
5. construct exactly one metadata-only TASK076_EXTERNAL_BINDING_SLOT_V1 for the
   Task074 owner adapter under the accepted amendment; it contains no live
   attachment, handle, body, callback or Authority;
6. call issue_and_arm_job_child_v3 with the exact current DISPATCHING readback,
   JOB_DISPATCH_PLAN_V3, exact private ticket/consumer inputs and that exact
   TASK076_EXTERNAL_BINDING_SLOT_V1;
7. receive JOB_CHILD_ARMED_READBACK_V3 with child/model/artifact/body effect zero;
8. the V3-reconciled TASK072_REFERENCE_ATTACHMENT_BEGIN_ABI_V1 atomically
   consumes the exact attachment, binds ticket/slot/armed vector, commits the
   begin readback and advances the Task074 lease
   ISSUED -> IN_FLIGHT_PARENT_DELEGATION;
9. select the exact Task076 IN_FLIGHT generation;
10. call create_bootstrap_job_child_v3;
11. receive JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3;
12. verify the V3-reconciled TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1 and
   TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1;
13. verify the V3-frozen TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1;
14. resolve and verify the exact Task066 network-enforcement producer receipt and
    TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 projection over that same
    child/process/Job custody;
15. have Task074 transfer the reference pair directly to that child-local broker;
16. call record_job_child_external_binding_v3;
17. call validate_job_child_external_input_v3;
18. call claim_job_child_artifact_prepare_v3 with
    FIXED_RECEIPT_ONLY_DECLARATION_V1 and win
    JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3;
19. only that pending winner begins the Task014 call dispatch and Task014 sink
    session as the external receipt-only preparation;
20. call commit_job_child_artifact_prepare_v3 with exact success/failure/unknown
    receipt-only truth; an exception after pending must still commit observed
    truth or become vector-wide BURNED_UNKNOWN;
21. call attach_artifact_and_release_job_child_v3 with no Task014 WAV handle;
22. only the release winner may enter body read/model load/inference;
23. terminalize the exact Task076 Job and Task074 lease from authenticated
    consumer, role-read and remote-close truth.

There is no child before the exact selected IN_FLIGHT state. The bootstrap child
has no model entry, reference body, script body, output handle or artifact body.
Abort and release are competing one-use CAS outcomes. Unknown process-create,
release or abort state is BURNED_UNKNOWN and forbids another child.

The Task072 broker alone retains the noninheritable last handle to the dedicated
kill-on-close, no-breakaway Job Object. Task076 binds that custody identity,
membership and selected currentness in its durable readback; it does not hold a
second containment handle. Task075 owns no Job handle and never implements a
second process owner, child registry, abort path or Job state machine.

### 9.6 Task066 -> Task072 -> Task075 compute/network crosswalk

Authority flows in one direction:

    TASK-066 compute producer: LOCAL_VOICE_COMPUTE_ADMISSION_V1
      -> TASK-072 broker consumer: ticket/begin/child binding
      -> TASK-075 execution consumer: task066_admission_sha256

    TASK-066 network-enforcement producer amendment: exact ABI pending
      -> TASK-072 broker consumer projection:
         TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1
      -> TASK-075 execution consumer: network_isolation_receipt_sha256

The TASK-066 compute admission is terminal/current only while every bound
install, Project, operation, workload, model, runtime, preference, effective
backend, build and expiry coordinate remains exact. The TASK-066 network
producer must bind the enforceable policy and executed exact-child observation.
TASK-072 consumes, but does not produce or independently assert, that
enforcement. Its projection additionally binds the exact ticket, selected
Task076 generation, child/process/Job custody and consumer currentness.

The Task066 compute admission is revalidated at ticket issue, child bootstrap,
before Task074 reference transfer, before child release and when the TASK-075
result is formed. The network producer receipt and Task072 projection are first
resolved only after the exact child bootstrap exists; they are then verified
before reference transfer and release, and revalidated for result formation.
Missing, stale, terminally noncurrent, fixture, public-only, cross-operation or
mismatched input is DEPENDENCY_NC; it is never repaired, refreshed or retried
inside the same operation. Before release, every not-yet-entered dependent
effect remains zero and the phase-correct abort path applies. After release,
any effect already entered is retained as exact `TRUE | FALSE | UNKNOWN`, no new
or retried effect is allowed, and the applicable private operational terminal
or BURNED_UNKNOWN containment applies.

### 9.7 Network isolation N.C. gate

The bootstrap readback statement that network policy was applied is not by
itself the receipt required by TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1.

The TASK-066-owned enforcement receipt must bind the policy implementation and
executed denial facts. TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 must
consume that exact live/current receipt and bind:

- exact installed session, operation, ticket, Task076 Job generation and child;
- process ID plus pinned process/token/session/image/build identities;
- exact Task066 network-producer receipt identity and currentness;
- exact Windows isolation implementation and policy version from that producer;
- no network capability, no inherited socket, no proxy/provider credential;
- firewall/AppContainer or equivalent enforceable denial coordinates;
- an executed outbound-denial observation for the exact child;
- observation and expiry currentness;
- fixture_only, authority_created and production_eligible truth;
- a body/path/secret-free digest.

The Task072 projection's closed terminal outcome, derived from the exact Task066
producer result rather than self-asserted by Task072, must distinguish:

- ENFORCED_VERIFIED: exact policy and outbound denial current; release may
  continue;
- FAILED_KNOWN: exact policy/denial failure and exact terminal child readback are
  known; the receipt hash may support a FAILED_KNOWN TASK-075 result at
  CHILD_CREATED;
- UNKNOWN: enforcement or observation truth is not known; release and model
  effect are zero, but no TASK-075 result may be minted because D4 does not allow
  UNKNOWN at CHILD_CREATED.

The producer receipt and Task072 projection must be verified after exact
bootstrap/process/custody readback and before reference transfer, script
dispatch, model load or child release. Only an exact current Task066 producer
outcome FAILED_KNOWN plus its matching exact current Task072 projection may mint
a FAILED_KNOWN TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1 at CHILD_CREATED with
NETWORK_ISOLATION_FAILED and the real projection hash.

Missing, stale, fixture, public-only, cross-operation, mismatched, unverifiable,
unreadable, publication-unknown or terminal UNKNOWN producer/projection truth
has no conforming TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1: D4 requires a
non-null, exact current network_isolation_receipt_sha256 from CHILD_CREATED
onward and does not admit UNKNOWN there. If detected before the release winner,
the child follows the phase-correct V3 abort/containment path; body/model and PCM
sink output effects remain zero, while an already-open Task014 receipt-only
prepare/sink session is exact-terminalized. If detected after release, any
release, model, consumer or sink effect already entered is preserved as exact
`TRUE | FALSE | UNKNOWN`; no new or retried effect is allowed. In both cases
POST, playback and listening decision remain zero, and public status reports a
stable body-free operational failure outside the result ABI. It must not
fabricate a FAILED_KNOWN result or a null/fake receipt hash.

### 9.7.1 Post-release network private terminal arm N.C.

Post-release loss of network producer/projection currentness requires a second,
non-aliased private ABI:

    TASK075_NETWORK_NONCURRENT_OPERATION_TERMINAL_V1

It is a body-free, path-free, nonserializable arm payload and never a substitute
for TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1. Its domain-only fields bind:

- the exact previously current Task066 network producer and
  TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 identities/digests plus
  their policy/build, observation, expiry and child/Job coordinates;
- one nonempty, sorted, unique and bounded mismatch-code set drawn only from
  PRODUCER_EXPIRED, PRODUCER_GENERATION_DRIFT,
  POLICY_BUILD_DRIFT, EXECUTED_OBSERVATION_NONCURRENT,
  CHILD_JOB_CUSTODY_DRIFT, PROJECTION_EXPIRED or PROJECTION_MISMATCH;
- the same trusted pinned result-formation observation identity/digest used by
  the compute arm and one domain-arm digest. It contains no child-exit, Task014,
  Task074, Task076 or shared effect/terminal field.

This network object is a private arm payload, not an independently callable
Task076 coordinate. Only section 9.7.2's exactly-one tagged union may carry this
arm. The arm never calls read_job_child_terminal_v3 by itself and does not
transfer producer ownership to Task072 or Task075.

Until this private ABI, the section 9.7.2 union, four-owner consumer amendment
and Task014 terminal/receipt-only amendment are accepted, post-release loss of
network currentness is JOB_CHILD_BURNED_UNKNOWN_READBACK_V3 plus exact recovery
containment only. A public projection, old ENFORCED_VERIFIED value or equal hash
cannot close the Task076 semantic terminal.

### 9.7.2 Exactly-one compute/network terminal union N.C.

One result-formation currentness snapshot derives two closed sets:
`compute_noncurrent_codes` and `network_noncurrent_codes`. Each set is sorted,
unique, bounded and complete for every predicate observed noncurrent in that
same pinned snapshot. Exactly one must be selected:

    TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 :=
        COMPUTE_ONLY {
            nonempty compute_noncurrent_codes,
            empty network_noncurrent_codes
        }
      | NETWORK_ONLY {
            empty compute_noncurrent_codes,
            nonempty network_noncurrent_codes
        }
      | COMPUTE_AND_NETWORK {
            nonempty compute_noncurrent_codes,
            nonempty network_noncurrent_codes
        }

The union binds the selected arm payload(s), installed session, Project,
operation, ticket, armed vector, selected Job, child process/build, one trusted
observation snapshot, exact `JOB_CHILD_STARTED_READBACK_V3`, one child exit/wait
and exact `TRUE | FALSE | UNKNOWN` model/body/consumer/output-effect truth.
Shared fields occur once. The two named arm ABIs provide only domain-specific
identities and closed predicate sets; they cannot independently invoke
read_job_child_terminal_v3.

The union also binds exactly one Task014 close set: call-dispatch lineage and
`IN_FLIGHT` pre-close snapshot; sink `WRITING | BODY_VERIFIED` pre-close
snapshot with partial/body-verified truth; one owner fail_closed/sink-abort
transition; durable call and sink `FAILED_CLOSED` readbacks; and the exact
receipt-only prepare/result bound to
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`. `RESULT_BOUND` is excluded
because it means a D4 result already won and belongs to a different
reconciliation seam. The union further binds exactly one Task074 lease state,
role-close and TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1 terminal set,
outcome `FAILED_KNOWN` only when every effect and close fact is exact, otherwise
`UNKNOWN`, `fixture_only=false`, `authority_created=false`,
`production_eligible=false` and one private semantic digest.

Only the accepted Task075/Task072/Task074/Task076 consumer amendment may pass the
sealed union as read_job_child_terminal_v3's
`exact_child_exit_and_result_coordinate` and semantic consumer-result digest.
It must pass the exact Task014 receipt-only result as Task076's mandatory fourth
argument. A separate Task014-owned amendment must expose the exact pre-state and
durable fail-closed readbacks. Fail-closed reply loss or restart-invalid live
Task014 capability makes the union UNKNOWN and the Job BURNED_UNKNOWN; it never
synthesizes FAILED_CLOSED, SINK_TERMINAL_SNAPSHOT or receipt-only truth.

Task074 may reach BURNED only when exact child exit, exact two-role remote close,
exact parent-handle count zero and the union prove all bounded effect facts. If
body/model effect, Task014 terminal, role close, child exit or terminal
publication is unknown, Task074 reaches FAILED_CLOSED / NOT_CONFIRMED, not
BURNED. Either terminal may use R13 retirement only with proven handle count
zero; retirement preserves FAILED_CLOSED as NOT_CONFIRMED and never relabels it.
The union authorizes no D4 result, POST, playback, decision, retry, second release
or new model/sink effect.

Omitted observed predicates, extra predicates, duplicate or unsorted codes,
wrong arm, two arms submitted as two terminals, mismatched observation snapshots
or a second terminal call are BURNED_UNKNOWN. One operation has one union CAS
winner. Exact same-event reply recovery is query-only; it never mints a second
union or reexecutes Task014/Task074/Task076 closure.

If enforceable Windows isolation remains N.C., Product local inference remains
disabled. Absence of a URL, internet call or Provider configuration is not an
offline proof.

## 10. Unified EXE startup, model UI and compute preference

The Product surface remains the unified BAI Video Production.exe:

1. task036_packaged_entry.py enforces the Product single-instance contract;
2. installed startup and current Project are resolved;
3. Task066 compute profile and local companion readiness are resolved;
4. the local companion is started at most once when required;
5. task036_shell_ui.py remains visible even when local inference is unavailable;
6. only the affected model/generate/listen controls are disabled with a stable
   reason.

The model selector:

- shows only free local models/routes that Task013/Task074 currently admits;
- contains no paid-provider fallback;
- never displays or accepts a raw model path;
- treats selection as a request, not Authority;
- requires a current Task074 selection handoff and Task014 call profile before
  Generate can become enabled;
- enables R6 execution only for ZERO_SHOT_LOCAL / PREVIEW; a fine-tuned or full
  render request remains visible only with a stable unsupported reason until a
  new Task014/TASK-075 ABI is accepted;
- displays selected model/route and actual compute route;
- shows unavailable/fallback reason before the Human inference action.

Top-right Settings exposes:

| UI choice | Task066 preference | Legal effective backend | Rule |
|---|---|---|---|
| 自動 | AUTO_GPU_FIRST | CUDA, or CPU only for a declared CPU-allowed workload | GPU-first; CPU reason shown before Human confirmation; no mid-run fallback |
| GPU | GPU_REQUIRED | CUDA only | unavailable means child effect zero; CPU fallback forbidden |
| CPU | CPU_EXPLICIT | CPU only | CUDA route/probe is not selected |

For audio.voice.local, a CPU fallback under AUTO is allowed only when Task066
declares GPU_PREFERRED_CPU_ALLOWED and returns the exact reason before the Human
action. The setting is user-visible policy; TASK-075 does not own its persistent
store.

Task036/UI and Task066 changes require their owners' separate implementation
amendments. R6 records the integration contract but grants no edit authority.

## 11. Worker protocol and one execution sequence

### 11.1 Channel roles

The child receives only:

- the fixed authenticated bootstrap/control channel;
- exact Task074 child-local reference roles after network proof;
- exact model/runtime handles admitted by Task066 and released by Task072;
- bounded script bytes supplied through the live Task014 call capability;
- no destination path and no Task014 sink/WAV handle.

The parent receives authenticated control and PCM frames. It validates every
frame and calls SINK_WRITE_SESSION.write_pcm24. The child cannot publish,
inspect, reopen, delete or replace the WAV.

### 11.2 Frame grammar

Each frame has a fixed one-byte kind and unsigned 32-bit little-endian payload
length. Allowed kinds are HANDSHAKE, CONTROL, PCM24 and TERMINAL.

- CONTROL is strict closed UTF-8 JSON, maximum 65,536 bytes;
- PCM24 payload is positive, divisible by three, maximum 49,152 bytes per frame;
- cumulative PCM bytes and frames cannot exceed Task014 sink limits;
- HANDSHAKE and TERMINAL are exact-once;
- unknown, duplicate, reordered, replayed, trailing or post-terminal frames fail
  closed;
- no script/reference/PCM/model/path is copied into logs, errors or public JSON.

JSON rejects duplicate keys, NaN/Infinity, BOM, trailing data, invalid UTF-8,
control characters, unknown fields, excessive depth/items/string/document size.

### 11.3 Exact inference sequence

After section 9.5 release:

1. worker validates the authenticated operation and handle role set;
2. the child-local Task074 broker wins CHILD_PAIR_READY -> BODY_READ_STARTED;
3. worker validates both zero-shot reference roles under the shared lease;
4. parent supplies the bounded script through the live call lease;
5. worker loads the exact admitted runtime/model;
6. worker performs at most one generation attempt;
7. worker emits bounded PCM_S24LE frames;
8. parent validates frame alignment/count/ceiling and streams them to the sink;
9. parent computes the same waveform digest and positive frame count;
10. sink.finish verifies bytes, digest, format and owned handle;
11. TASK-075 constructs TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1;
12. an in-process callback moves the live Task014 call and sink to RESULT_BOUND;
13. TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1 plus the exact consumer
    terminal moves the Task074 V2 lease to CONSUMED, or exact abort/unknown proof
    moves it to BURNED/FAILED_CLOSED;
14. Task014 alone consumes and publishes the POST receipt;
15. Task076 terminalizes the exact Job;
16. the same Task074 broker obtains
    TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1 before any new reference
    operation may issue.

Any exception burns the current live capabilities. Recovery must re-read exact
durable coordinates and never restarts the same unknown generation.

## 12. TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1

Exact D4/R1 field order is:

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
    terminal_stage
    outcome
    reason_codes
    fixture_only
    authority_created
    production_eligible
    result_sha256

Enums:

- effective_backend = CPU or CUDA;
- outcome = SUCCESS, FAILED_KNOWN or UNKNOWN;
- terminal_stage =
  PRE_SPAWN, CHILD_CREATED, GENERATION_DISPATCHED, WAVEFORM_OBSERVED,
  SINK_WRITE_ATTEMPTED, SINK_WRITE_COMMITTED or RESULT_VERIFIED.

Exact stage field matrix:

| terminal_stage | network receipt | child | attempts | waveform count | format/frame/hash | sink result | output handle |
|---|---:|---:|---:|---:|---|---|---|
| PRE_SPAWN | null | 0 | 0 | 0 | null | null | null |
| CHILD_CREATED | required | 1 | 0 | 0 | null | null | null |
| GENERATION_DISPATCHED | required | 1 | 1 | 0 | null | null | null |
| WAVEFORM_OBSERVED | required | 1 | 1 | 1 | required | null | null |
| SINK_WRITE_ATTEMPTED | required | 1 | 1 | 1 | required | null | null |
| SINK_WRITE_COMMITTED | required | 1 | 1 | 1 | required | required | required |
| RESULT_VERIFIED | required | 1 | 1 | 1 | required | required | required |

SUCCESS is legal only at RESULT_VERIFIED with 48000/1/PCM_S24LE, positive
frame_count, one child, one generation, one waveform and empty reasons.
UNKNOWN is legal only at GENERATION_DISPATCHED with
EXECUTION_OUTCOME_UNKNOWN or at SINK_WRITE_ATTEMPTED with
SINK_COMMIT_OUTCOME_UNKNOWN. It never authorizes automatic retry.

reason_codes is sorted, unique and empty on SUCCESS. FAILED_KNOWN or UNKNOWN
requires one through four closed reasons. For multiple reasons, terminal_stage
must be legal for every member of the tuple; if the legal-stage sets do not have
one declared intersection, the result is rejected. A later-effect reason cannot
be attached to an earlier terminal stage. Unknown, additional, duplicate or
unsorted codes are rejected. EXECUTION_OUTCOME_UNKNOWN and
SINK_COMMIT_OUTCOME_UNKNOWN are legal only with outcome UNKNOWN; every other
non-success reason tuple is legal only with outcome FAILED_KNOWN.

The result is Evidence. A deserialized result cannot move the live Task014
objects to RESULT_BOUND or publish a WAV.

## 13. PCM24 and WAV grammar

The fixed synthesis format is:

- sample rate 48,000 Hz;
- one channel;
- signed PCM_S24LE;
- three bytes per frame;
- byte rate 144,000;
- block alignment three.

The worker emits raw PCM24 frames, not a WAV file. Task014's sink owns the RIFF
writer and must publish exactly:

| Offset/order | Required value |
|---|---|
| 0 | ASCII RIFF |
| 4 | little-endian uint32 file_length minus 8 |
| 8 | ASCII WAVE |
| 12 | ASCII fmt and one trailing space |
| 16 | little-endian uint32 16 |
| 20 | format tag 1 |
| 22 | channels 1 |
| 24 | sample rate 48000 |
| 28 | byte rate 144000 |
| 32 | block align 3 |
| 34 | bits per sample 24 |
| 36 | ASCII data |
| 40 | little-endian uint32 data_length |
| 44 | first PCM byte |

Required equations:

    data_length = frame_count * 3
    pad_length = data_length & 1
    file_length = 44 + data_length + pad_length
    RIFF.size = file_length - 8

frame_count and data_length are positive and within sink max_frames,
max_output_bytes and uint32 RIFF bounds. Arithmetic is checked before write.
The file has exactly one fmt chunk followed by exactly one data chunk. Unknown,
duplicate, reordered, extended, zero-length or trailing chunks are forbidden.
The data chunk's uint32 size is the unpadded data_length. When pad_length is one,
exactly one zero pad byte follows the PCM bytes; when zero, no pad byte exists.
The pad is RIFF word alignment, not PCM, not part of data_length or the waveform
digest, and not a trailing chunk. Missing, nonzero, duplicate or extra pad bytes,
partial frames, nonmultiple-of-three data, header/data mismatch, overflow,
NaN-derived counts or post-close identity substitution fail closed. The staged
WAV digest includes the required pad while the PCM waveform digest excludes it.

The valid fixture must be named for 48000-mono-PCM24. A PCM16 fixture or a file
whose header merely claims PCM24 cannot satisfy R6.

## 14. POST, QA, playback and listening

Task014 alone publishes TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1 after
the live call/sink objects and exact TASK-075 result are RESULT_BOUND. The POST
binds exact Project/operation/call/result/sink, staged WAV bytes and identity,
48000/mono/PCM24/sample count/duration, alignment, publication generation and
readback.

Task048 alone issues OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1. Playback remains
disabled unless the exact POST and QA PASS are current and bind the same WAV.

VOICE_PLAYBACK_OBSERVATION_V1 is TASK-075-owned Evidence. It binds:

- Project/install/operation/Quick Clone candidate;
- exact POST, WAV identity/hash and QA PASS;
- exact Task072 playback machine-operation readback;
- fixed full-range start/end and normal-speed policy;
- pinned local player process/build/device-policy identity;
- started/completed/stopped/failed-known/unknown outcome;
- frame-zero start and full-playback completion truth;
- body/path-free reasons and fixture lineage.

It is not a Human receipt, does not select a Task041 decision, and cannot grant
Asset, Timeline or Production authority.

TASK041_OWNER_VOICE_LISTENING_DECISION_V2 uses:

- decision = ACCEPT, REJECT or RETEST;
- exact current flow head;
- exact POST/WAV/QA/playback observation;
- a fresh Task071 OWNER_VOICE_LISTENING_DECISION_V1 live receipt.

Quick Clone V2 lifecycle remains:

    NOT_AVAILABLE -> REQUIRED
    REQUIRED -> ACCEPTED | REJECTED | RETEST_REQUIRED
    RETEST_REQUIRED -> REQUIRED
    ACCEPTED and REJECTED are terminal for that candidate generation

RETEST retains the same candidate and requires a fresh full playback before a
new Human decision. REGENERATE is not a Quick Clone transition.

VOICE_QA_LISTENING_BINDING_V1 binds the exact POST, QA, latest playback,
Task041 decision and current QUICK_CLONE_FLOW_READBACK_V2 for the same candidate.
TASK-073 receives this binding only. Raw Task041, Task046 or public playback
data cannot be passed downstream as equivalent Authority.

## 15. Human decision and terminal table

| UI/Human operation | Required authority | Candidate/result effect | Terminal rule |
|---|---|---|---|
| prepare reference | OWNER_VOICE_REFERENCE_PREPARE_V1 | Task074 domain prepare only | terminal prepare receipt; inference zero |
| generate | OWNER_VOICE_LOCAL_INFERENCE_V1 | one fresh Task014/Task074/Task066/Task072/Task076 chain | capability burns on entry/exception |
| play/listen | no Task071 approval action; explicit UI request plus Task072 playback machine profile | one bounded playback observation | completion is observation, not acceptance |
| accept | OWNER_VOICE_LISTENING_DECISION_V1 | Quick Clone ACCEPTED | terminal for candidate |
| reject | OWNER_VOICE_LISTENING_DECISION_V1 | Quick Clone REJECTED | terminal for candidate |
| retest | OWNER_VOICE_LISTENING_DECISION_V1 | RETEST_REQUIRED, same candidate | decision terminal; fresh playback then REQUIRED |
| regenerate | OWNER_VOICE_REGENERATE_V1 | wholly new Task014 operation/candidate | old authority never reused |
| revoke reference | OWNER_VOICE_REFERENCE_REVOKE_V1 | prevent future use | no deletion |
| purge reference | OWNER_VOICE_REFERENCE_PURGE_V1 plus G09 | exact-owned purge | separate terminal transaction |

Human deny, cancel, expiry, user/session mismatch, clock rollback or unknown
broker state leaves the gated effect zero. The Product never asks a generic
confirmation string and never accepts caller-provided evidence ID or time.

## 16. Runtime state sequence

The Product-visible inference states are:

    BLOCKED
      -> READY_TO_CONFIRM
      -> DISPATCHING
      -> CHILD_ARMED
      -> JOB_IN_FLIGHT
      -> CHILD_BOOTSTRAP_WAITING
      -> EXTERNAL_INPUT_VALIDATED
      -> SINK_READY
      -> RUNNING
      -> WAVEFORM_OBSERVED
      -> SINK_COMMITTED
      -> RESULT_VERIFIED
      -> POST_VERIFIED
      -> QA_REQUIRED
      -> LISTENING_REQUIRED
      -> ACCEPTED | REJECTED | RETEST_REQUIRED

RECOVERY_REQUIRED or UNKNOWN may replace a nonterminal state only from exact
durable producer truth. The UI cannot infer progress from process existence,
file presence, newest receipt, mtime, equal bytes or a prior screen state.

No operation may move backward. RETEST is a new playback operation over the same
candidate. REGENERATE creates a new operation identifier and new forward chain.

## 17. Restart and fault matrix

### 17.1 Cross-component restart seams

| Seam | Required classification | Allowed recovery/effect |
|---|---|---|
| before Human/ticket/Job | PRE_SPAWN rejection | no child; fresh currentness resolution |
| Task066 admission noncurrent before Task076 DISPATCHING publication/selection | COMPUTE_ADMISSION_NONCURRENT outside D4 | burn/reject matching G07 operation; candidate/vector/child/result zero |
| Task066 admission noncurrent after selected DISPATCHING before V3 arm/vector | pre-effect Task072 rejection | JOB_CHILD_REJECTED_READBACK_V3 -> predecessor-correct FAILED_KNOWN candidate + TASK043 CAS/readback, or BURNED_UNKNOWN candidate if truth is unknown; exact Task074 ABSENT_PROVEN-or-ISSUED attachment/V2 terminal, parent close and handle0; child/result zero |
| child armed, IN_FLIGHT not selected | armed orphan | Task072 V3 broker executes the exact orphan abort under current Task076 durable Job/process coordinates |
| Task066 admission noncurrent with ARMED/unselected IN_FLIGHT candidate | armed orphan compute closure | abort_armed_orphan_job_child_v3 exact once; exact Task074 ISSUED-or-CONSUMED attachment/V2 terminal; select/bootstrap/result zero; terminate/wait receipt zero because process=false |
| IN_FLIGHT selected, bootstrap not created | prebootstrap | exact abort or exact create CAS; never both |
| Task066 admission noncurrent after selected IN_FLIGHT before bootstrap | prebootstrap compute closure | abort_armed_prebootstrap_job_child_v3 exact once; exact Task074 CONSUMED/IN_FLIGHT_PARENT_DELEGATION terminal; process/model/result zero and no fabricated terminate/wait |
| child-created false | FAILED_KNOWN | exact Task074 parent-close/remote ABSENT_PROVEN/handle0 terminal; no process, no terminate/wait receipt and no retry under same operation |
| child-created true | CHILD_CREATED | exact contained child; Task072 V3 broker-owned abort/kill-on-close under exact current Task076 durable Job/process coordinates |
| child-created N.C. | BURNED_UNKNOWN | no respawn; manual/exact durable recovery |
| live same-broker Task066 admission expires/drifts after BOOTSTRAP_WAITING before owner bind | COMPUTE_ADMISSION_NONCURRENT outside D4 | BEFORE_PREPARE/NONE_IF_NEVER_BOUND -> ABORT_PENDING -> no-role close -> terminate/wait exact1 -> BOOTSTRAP_ABORTED or BURNED_UNKNOWN |
| live same-broker Task066 admission expires/drifts after bind or preflight | COMPUTE_ADMISSION_NONCURRENT outside D4 | BEFORE_PREPARE with exact BOUND/FAILED/VALIDATED tag; owner close + terminate/wait exact1; no new bind/preflight |
| live same-broker Task066 admission expires/drifts during Artifact prepare | exact V3 prepare/abort tagged state | PREPARE_IN_PROGRESS pending truth or matching prepare commit only; no guessed Artifact truth or release |
| live same-broker Task066 admission expires/drifts after prepare or release rejection | exact V3 AFTER_PREPARE/AFTER_RELEASE_REJECTED | one abort claim/commit; preserve Artifact/foreign targets; no release retry |
| Task066 compute admission expires/drifts after release winner | JOB_CHILD_STARTED_READBACK_V3 | fixed child exits; COMPUTE_ONLY arm + exact shared closure -> exactly one TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 only after owner amendments, otherwise BURNED_UNKNOWN; no D4 result/model retry/second release |
| Task066 network producer/projection becomes noncurrent before release | NETWORK_CURRENTNESS_NONCURRENT outside D4 | exact live phase-correct V3 abort/containment; model/PCM output/POST/playback/decision zero; receipt-only prepare state exact-terminalized |
| Task066 network producer/projection becomes noncurrent after release | JOB_CHILD_STARTED_READBACK_V3 | preserve exact TRUE/FALSE/UNKNOWN model/sink truth; NETWORK_ONLY arm + exact shared closure -> exactly one TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 only after owner amendments, otherwise BURNED_UNKNOWN; no D4 result or new/retried effect |
| compute and network become noncurrent in one result-formation snapshot after release | JOB_CHILD_STARTED_READBACK_V3 | COMPUTE_AND_NETWORK union with both complete sorted predicate sets and one shared Task014/Task074/Task076 closure; never two terminal calls |
| Product/broker restart with DISPATCHING-current exact unselected orphan | restart-safe orphan-only exception | abort_armed_orphan_job_child_v3 exact once plus Task074 durable terminal; process=false and terminate/wait receipt zero; no other live capability reconstructed |
| Product/broker restart with exact durable pre-crash ABORT_PENDING | same claim recovery | exact-query/finish that claim only; owner-close and terminate/wait are not restarted or duplicated |
| Product/broker restart with selected prebootstrap, BOOTSTRAP_WAITING, BOUND, VALIDATED, prepare or release-rejected state and no pre-crash ABORT_PENDING | BURNED_UNKNOWN | contain_burned_unknown_job_child_v3 only; no fresh abort claim, normal owner close, bind, preflight, prepare or release |
| Product/broker restart after JOB_CHILD_STARTED_READBACK_V3 | post-release terminal recovery | accepted exact same-event TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1 plus Task014/Task074 truth only; missing live Task014 terminal is UNKNOWN/BURNED_UNKNOWN; no arm-only call, D4 result, reattach, resume or retry |
| compute-abort owner close, terminate/wait or terminal reply unknown | BURNED_UNKNOWN | same-operation containment/readback only; no reissue, rebind, release or second child |
| network FAILED_KNOWN terminal receipt | NETWORK_ISOLATION_FAILED | result CHILD_CREATED with exact receipt hash; abort child; later effects zero |
| network receipt absent/unreadable/UNKNOWN before release | no conforming TASK-075 result | phase-correct abort plus durable Job recovery only; model/PCM output effect zero; fake/null receipt hash forbidden |
| reference transfer partial | REFERENCE_DELEGATION_FAILED_CLOSED | pair lease closes; parent handle count zero |
| reference preflight failure | REFERENCE_PAIR_FAILED_CLOSED | model/sink/POST zero |
| call dispatch/sink begin failure | SINK_REJECTED | release zero; child abort |
| receipt-only prepare unknown | BURNED_UNKNOWN | no release and no second prepare |
| release CAS unknown | BURNED_UNKNOWN | no second release/child generation |
| model load failure | MODEL_LOAD_FAILED | sink abort; no backend fallback |
| inference failure | INFERENCE_FAILED | generation attempt one; no retry |
| malformed/oversized PCM | INVALID_WAVEFORM | sink abort; POST zero |
| sink write failure | SINK_WRITE_FAILED | no rewrite/cleanup |
| sink commit outcome unknown | SINK_COMMIT_OUTCOME_UNKNOWN | exact Task014 reconciliation only |
| sink committed, verify failure | SINK_VERIFY_FAILED | FAILED_KNOWN; no new write |
| result callback or POST response lost | exact Task014 terminal readback | Task075 cannot republish or regenerate |
| QA FAIL/UNKNOWN/stale | QUALITY_NOT_ADMITTED | playback/decision zero |
| playback crash/receipt loss | playback UNKNOWN | same operation not replayed; candidate retained |
| decision CAS conflict | CAS_CONFLICT | Task046 unchanged; fresh Human decision required |
| Task046 transition applied, join lost | exact current Task046 readback | rebuild binding only; decision not reapplied |
| Task074 revoke/expiry races attachment, transfer, pair-ready or body-start | one domain CAS winner | pre-body winner aborts/closes; post-body winner enters REVOKE_PENDING and waits for exact terminal |
| Task074 remote role close or child exit proof missing | FAILED_CLOSED / NOT_CONFIRMED | no CONSUMED/BURNED retirement, new issue or purge |
| Task074 terminal retirement reply lost | exact immutable history plus current fence | return existing retired result or bounded same-event recovery; no duplicate clear/history |
| old operation retries after fresh-fence issue | stale old generation | new operation remains sole current lease; old effect zero |

### 17.2 Exact TASK-073 R3 reason/stage table

| Reason | terminal_stage |
|---|---|
| PRE_SPAWN_ADMISSION_REJECTED | PRE_SPAWN |
| SANDBOX_START_FAILED | PRE_SPAWN |
| NETWORK_ISOLATION_FAILED | CHILD_CREATED |
| WORKER_PROTOCOL_FAILED | CHILD_CREATED or GENERATION_DISPATCHED |
| MODEL_LOAD_FAILED | CHILD_CREATED |
| RESOURCE_LIMIT_EXCEEDED | CHILD_CREATED or GENERATION_DISPATCHED |
| INFERENCE_FAILED | GENERATION_DISPATCHED |
| INVALID_WAVEFORM | WAVEFORM_OBSERVED |
| SINK_WRITE_FAILED | SINK_WRITE_ATTEMPTED |
| SINK_VERIFY_FAILED | SINK_WRITE_COMMITTED |
| EXECUTION_OUTCOME_UNKNOWN | GENERATION_DISPATCHED with UNKNOWN |
| SINK_COMMIT_OUTCOME_UNKNOWN | SINK_WRITE_ATTEMPTED with UNKNOWN |

Recovery reads exact IDs and current generations only. It never scans for
latest/current, never uses first-existing or mtime, never reopens by caller path,
never deletes an unknown object and never silently changes backend.

## 18. Negative and verification matrix

Every negative separately asserts child count, generation count, sink delta,
POST delta, QA delta, playback delta, Task041/Task046 delta, unrelated
overwrite/delete delta and public leakage.

### T75-AUTH

- direct/copy/replace/pickle/deserialization/subclass/duck public call, handoff,
  compute, Human, ticket, Job, result, POST, QA, playback or decision objects;
- module token/sentinel access and recomputed self-hash;
- fixture receipt promoted to native Authority;
- wrong/cross Project/install/operation/candidate/build/user/session;
- reused/expired/wrong-action Task071 receipt;
- reused/cross-action Task072 ticket;
- caller-selected clock, backend, path, model, process or handle;
- same fields/hash with a different live capability.

Expected: gated effect zero and old live object burned only after authenticated
entry.

### T75-JOB-CHILD

- G11 or attachment/begin used as a pre-G07 ticket prerequisite;
- missing/extra TASK076_EXTERNAL_BINDING_SLOT_V1, live attachment serialized into
  the slot, or attachment-begin before ARMED/after bootstrap;
- slot bind/preflight/recovery roles filled by the Task074 attachment,
  execution-input envelope or generic issue/revoke CAS without the accepted
  coordinated owner adapter ABIs;
- spawn before exact selected IN_FLIGHT;
- create/abort race, repeated create, repeated release, release after abort;
- child process identity false/true/N.C. seams;
- wrong image/build/token/session/parent/Job;
- grandchild/breakaway or extra inherited handle;
- Task076 or TASK-075 holding/duplicating the Task072 broker's sole live Job
  handle, or either component executing an independent abort;
- a pre-V3 or unfrozen custody readback relabeled as
  TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1;
- Task074 pair delivered to parent, wrong child, partial pair or after release;
- network projection resolved before exact process/custody readback;
- Task066 producer and Task072 projection cross-child/cross-Job mismatch;
- network policy absent, public-only, stale, fixture, UNKNOWN, unreadable or no
  executed denial, including attempts to mint NETWORK_ISOLATION_FAILED from any
  case other than an exact current FAILED_KNOWN producer/projection;
- model or sink effect in bootstrap/preflight phase.

Expected: Task076 exact terminal truth, child effect 0/1, no second child.

### T75-IPC-PCM-WAV

- unknown/duplicate/reordered/trailing/replayed frame;
- duplicate JSON key, NaN/Infinity, BOM, invalid UTF-8 or oversize;
- PCM empty, nonmultiple-of-three, chunk/total/frame ceiling breach;
- wrong sample rate/channel/format;
- RIFF tag/size/fmt/data/order/length/alignment/byte-rate mismatch;
- odd-frame PCM24 with missing/nonzero/duplicate pad, even-frame PCM24 with an
  unexpected pad, data chunk size including pad, RIFF/file length excluding the
  required pad, or waveform digest including the pad;
- duplicate/unknown/trailing WAV chunk;
- output target/ancestor/hardlink/reparse/DACL/identity substitution;
- sink finish/flush/readback failure;
- same WAV bytes at a different identity.

Expected: result/POST/QA/playback zero as applicable; foreign object preserved.

### T75-COMPUTE

- AUTO presented as effective backend;
- CPU under GPU_REQUIRED;
- CUDA under CPU_EXPLICIT;
- CPU fallback for GPU_REQUIRED workload or without pre-Human reason;
- backend switch after admission/child start;
- expiry, stale generation, cross-build, cross-model/runtime, Project/install,
  operation, backend or revocation drift injected before arm, before bootstrap,
  after BOOTSTRAP_WAITING, after bind, after preflight, during/after prepare,
  after release rejection and after release winner;
- wrong V3 abort tag, NONE_IF_NEVER_BOUND after a role transfer, reconstructed
  Artifact truth, second claim/commit, reissued admission, rebind or release;
- selected DISPATCHING/pre-arm drift falsely reported as candidate zero instead
  of exact Task072 rejection plus predecessor-correct TASK043-selected terminal,
  or with Task074 attachment absence inferred rather than ABSENT_PROVEN;
- orphan/prebootstrap closure with wrong ABSENT/ISSUED/CONSUMED attachment or V2
  lease generation, missing parent close/remote ABSENT_PROVEN/handle0, fabricated
  terminate/wait for process=false, or R13 retirement from unknown handle truth;
- restart at selected prebootstrap, BOOTSTRAP_WAITING, BOUND, VALIDATED, prepare
  or release-rejected without a pre-crash ABORT_PENDING followed by a fresh abort
  claim, owner close, bind, preflight, prepare or release; and restart-safe orphan
  attempted without DISPATCHING-current exact unselected lineage;
- missing/forged/public/cross-operation compute or network arm, either arm passed
  directly to Task076, or an arm used as D4/POST/playback authority;
- missing/forged/stale/public/cross-operation
  TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1; COMPUTE_ONLY, NETWORK_ONLY or
  COMPUTE_AND_NETWORK selected against the observed predicate sets; omitted,
  extra, duplicate or unsorted predicate; two arm-specific terminal calls; or a
  second union call after the one winner;
- simultaneous compute+network drift represented by only one arm, by two unions,
  by arms from different observation snapshots or by two shared closure digests;
- union with missing/stale/forged Task014 call pre-state/FAILED_CLOSED terminal,
  sink pre-state/FAILED_CLOSED terminal or exact receipt-only Task076 fourth
  argument, including restart after loss of the live Task014 capability;
- compute drift with owner close/remote-close, exact child terminate/wait or
  Task076 durable terminal missing/duplicated/unknown;
- compute drift followed by a fabricated D4 FAILED_KNOWN/UNKNOWN result or a
  null/fake/noncurrent network receipt hash;
- AUDIO_VOICE_COMPUTE_ADMISSION_V1 relabeled or hashed as
  LOCAL_VOICE_COMPUTE_ADMISSION_V1;
- LOCAL_VOICE_COMPUTE_ADMISSION_V1 presented to the unamended TASK-073 D4 AUDIO
  allowlist, dual AUDIO/LOCAL acceptance, wrong version or Task075-side allowlist
  override;
- public TASK066 probe substituted for current admission.

Expected: exact legal V3 closure; Task072 terminate/wait count exactly one when a
child exists and zero when process=false; Task074 terminal/retirement exact once;
second child and foreign cleanup zero. Before release, release/body/model/PCM sink
output/POST/playback/decision deltas are zero and any prior receipt-only prepare
state is exact-terminalized. After release, pre-existing release/model/consumer/
sink truth remains exact `TRUE | FALSE | UNKNOWN`, new or retried effects and
POST/playback/decision remain zero, and no TASK-075 result is minted for a
noncurrent compute or network binding. Never automatic rerun.

### T75-LISTENING

- playback before current POST and QA PASS;
- playback treated as a Task071 Human action or as ACCEPT;
- external player or receipt-only completion;
- wrong range, speed, WAV, device policy, candidate or cycle;
- double/concurrent Play;
- RETEST with changed candidate or old playback authority;
- REGENERATE reusing any previous call/sink/handoff/compute/Human/ticket/Job;
- Task041 decision without exact Task071 listening receipt;
- raw Task041/Task046 data passed to TASK073;
- stale/forked/cross-candidate Quick Clone head.

Expected: exact playback 0/1, decision/join effect zero on mismatch.

### T75-PRIVACY-RESOURCE

- script/reference/PCM/model/path/account/SID/device/OS detail in public
  status/log/stdout/receipt;
- child crash dump or upload attempt;
- unbounded control/PCM/progress/reason data;
- output quota, memory, GPU/runtime or duration ceiling breach;
- fixture/native/installed status promoted beyond evidence level.

Expected: stable body-free reason, service remains available, sensitive bytes
absent from public artifacts.

### Static and focused verification

- exact ABI names and versions from section 8;
- TASK-073 D4 compute allowlist amendment accepts only Task066
  LOCAL_VOICE_COMPUTE_ADMISSION_V1 version 1 and rejects AUDIO/no-alias;
- D4/R1 result field order and stage/nullability matrix;
- Task074 R13 G01/G02/G06-G10/G12/G14 and full handoff currentness;
- Task071 exact six-action closure and cross-action rejection;
- Task072 owner begin/network/playback dependency N.C. fail-closed tests;
- exact pre-issue -> G07 ticket -> attachment/one metadata slot -> V3 arm ->
  attachment/begin -> selected IN_FLIGHT -> bootstrap order and every illegal
  permutation;
- Task066 producer -> Task072 consumer projection -> Task075 hash crosswalk,
  currentness and FAILED_KNOWN-versus-no-result closure;
- both private compute/network arm ABIs, the exactly-one tagged union including
  COMPUTE_AND_NETWORK, exact Task014 call/sink terminals and Task076 receipt-only
  fourth-argument binding;
- Task072 sole live Job-handle/abort ownership and Task076 V3-frozen durable
  custody readback no-alias tests;
- unmodified Task076 arm/IN_FLIGHT/bootstrap/bind/preflight/receipt-only
  prepare/release/abort integration;
- parent sink ownership and child Task014 handle count zero;
- frame parser and PCM24/WAV property/boundary corpus;
- Human decision terminal table;
- Auto/GPU/CPU routing table and no mid-run fallback;
- every restart seam and exact reason/stage pair, including orphan-only restart,
  existing-ABORT_PENDING-only completion and no-new-abort containment;
- public leakage scan;
- relevant Task014/041/046/048/066/074/076 regression.

The Development-4 QA plan at
`090A0A94744D48574AF02B4AF9C4ED528B715BC78CCBCB7FF5122064B117570E`
and static fixture vectors at
`568F62605DDB0FB8D9E567753BA863A4E88142024F3BB7D804FAA768F09E69EB`
are connection-planning Evidence only. They cover TASK036 central model/GPU,
TASK048 QA, TASK041 listening, TASK046 Quick Clone and the V3 sequence expected
readback/log-classifier/forbidden-promotion axes. Their status remains
`HIGH_CORRECTION_PENDING / VERSIONED_NC`; neither hash nor a static vector closes
an R6 Gate. They must be rebound to the final exact R6 hash after independent
Critical/High 0/0 and then executed under the applicable test/native Gates.

### Windows native verification

- exact packaged worker image/build/protocol;
- one child inside no-breakaway kill-on-close Job;
- restricted token/session/parent and handle list;
- exact Task074 direct pair transfer, parent reference-handle count zero;
- enforceable no-network policy plus executed outbound-denial readback;
- actual CPU run and, when admitted, actual CUDA run;
- Auto fallback reason before Human confirmation;
- mutate Task066 expiry, producer generation, build, model/runtime, Project,
  install, operation and backend currentness after real child bootstrap at every
  bind/preflight/prepare/release boundary;
- mutate the exact Task066 network producer and Task072 projection expiry,
  generation, policy/build, observation, child/Job binding and currentness before
  and after the real release winner, including result formation;
- prove the exact V3 tagged abort/terminal selected for each boundary, Task072
  terminate/wait count one, Task074 remote close plus retirement and Task076
  durable terminal/currentness;
- assert release/model/sink/POST/playback/decision effects zero where release has
  not won except the exact prior receipt-only prepare state, and assert its
  Task014 terminal; where release has won, preserve exact TRUE/FALSE/UNKNOWN
  model/sink truth and permit no new model/sink effect or retry; POST/playback/
  decision stay zero, foreign sentinel identity/bytes remain unchanged and
  second-child count stays zero;
- restart after each real boundary: finish only an exact durable pre-crash
  ABORT_PENDING, permit only the DISPATCHING-current unselected orphan exception,
  otherwise prove BURNED_UNKNOWN containment; terminate/wait exact1 only for an
  existing child and exact0 for process=false;
- one rights/consent-approved non-sensitive sentence under a separate native
  private-voice Human Gate;
- exact PCM24/WAV bytes, counts and pinned identity;
- crash/cancel/timeout/suspend/restart/time-change at every seam;
- NTFS reparse/hardlink/ancestor/DACL/race matrix;
- real bounded playback and stop;
- public logs/UI/stdout sensitive-data leakage zero.

Until the separate native Gate is opened, native inference, private voice data
processing and playback remain NOT_EXECUTED / NOT_CONFIRMED. Fixture tests never
change that status.

### Package and unified EXE verification

- clean unified EXE launch without Codex, ChatGPT, OpenAI key or internet;
- single instance and local companion count at most one;
- Shell remains visible when model/compute is unavailable;
- free-local model selector and Auto/GPU/CPU Settings currentness;
- no paid Provider or model/runtime download fallback;
- exact worker/model/runtime/protocol installed manifests and hashes;
- repair/upgrade invalidates live tickets/capabilities;
- multiple installs cannot cross-redeem operation data;
- installer/build changes only through their owners.

## 19. Remaining N.C. gates

R6 design can be reviewed, but source/native work remains blocked on exact
completion receipts for:

1. TASK-014 D4 LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2,
   TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1,
   NARRATION_OUTPUT_SINK_CAPABILITY_V1 and
   TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1, plus a Task014-owned
   noncurrent-operation amendment that exposes exact call/sink pre-state,
   one fail-closed/abort transition, durable FAILED_CLOSED readbacks and the
   exact Task014 receipt-only result consumed by Task076 to publish
   JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1;
2. TASK-074 R13 implementation and current G01-G14 producer receipts, including
   TASK074_TO_TASK075_EXECUTION_INPUT_V2,
   TASK074_REFERENCE_BEGIN_ATTACHMENT_V1,
   TASK074_REFERENCE_WORKER_DELEGATION_V1,
   TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1,
   TASK074_REFERENCE_V2_TERMINAL_RETIRE_READBACK_V1 and
   OWNER_VOICE_REFERENCE_DOMAIN_TRANSACTION_V1;
3. a Task014/Task074 compatibility amendment that makes parent reference-open
   authority structurally impossible while preserving exact D4 call/result/sink
   bindings;
4. a TASK-073-owned D4 compute-admission allowlist amendment that retires
   AUDIO_VOICE_COMPUTE_ADMISSION_V1 without aliasing, accepts only Task066
   LOCAL_VOICE_COMPUTE_ADMISSION_V1 version 1 and preserves exact D4 result/
   stage/nullability rules; TASK-066 audio.voice.local mapping, current
   LOCAL_VOICE_COMPUTE_ADMISSION_V1 for CPU/CUDA, stage-current revalidation and
   terminal currentness readback, and the separately owned enforceable
   network-isolation producer amendment/receipt;
5. TASK-071 V2 exact six actions and live broker adapter;
6. TASK-072 OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3,
   TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1, exact playback
   machine-operation profile and the accepted
   TASK072_OWNER_VOICE_NETWORK_ISOLATION_READBACK_V1 consumer projection over
   the exact Task066 producer, plus the cross-owner amendment that replaces the
   non-aliasable R10 V2 child-arm lineage with exact Task076 V3 lineage for G11,
   freezes G07 ticket -> attachment/metadata slot -> V3 arm -> attachment/begin
   ordering, and names the exact Task074 child-bind, body-free preflight and
   remote-close/recovery adapter ABIs accepted by
   TASK076_EXTERNAL_BINDING_SLOT_V1, and implements the exact orphan,
   prebootstrap, tagged bootstrap abort/commit and unknown-containment broker
   paths used for post-admission compute drift;
7. TASK-076 implemented DURABLE_PRODUCT_JOB_READBACK_V1 and
   TASK076_OWNER_VOICE_WORKER_PROCESS_READBACK_V1 plus
   an explicitly V3-frozen/no-alias TASK076_EXACT_CHILD_JOB_CUSTODY_READBACK_V1,
   with the coordinated owner amendment fixing TASK-072 as sole live Job-handle
   and abort owner and TASK-076 as durable custody readback owner, plus all exact
   V3 abort tagged variants and predecessor-correct durable terminal/currentness;
8. TASK-048 OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1;
9. TASK-041 TASK041_OWNER_VOICE_LISTENING_DECISION_V2 and TASK-046
   QUICK_CLONE_FLOW_READBACK_V2 producer implementations;
10. TASK-036 unified EXE/model selector/Auto-GPU-CPU integration;
11. TASK-075 packaged worker, strict protocol, CPU/CUDA native evidence and
     enforceable no-network Windows observation; owner-accepted private
     TASK075_COMPUTE_NONCURRENT_OPERATION_TERMINAL_V1 and
     TASK075_NETWORK_NONCURRENT_OPERATION_TERMINAL_V1 arm payloads; exactly one
     TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1; the explicit four-owner
     TASK075/TASK072/TASK074/TASK076 consumer amendment; and its exact Task014
     receipt-only, Task074 lease/role and Task076 terminal bindings;
12. separate Owner native/private-voice execution Gate.

Each missing Gate blocks only its dependent effect. No N.C. item may be promoted
by a fixture, public document, equal hash, design acceptance or a successful
unrelated test.

## 20. Explicit R4/R5 clauses superseded by R6

R6 explicitly supersedes:

- R5/V5 design status and identity, plus the R4/V4 identity and
  origin/main@70ba9e base;
- TASK-074 R9 as sole accepted producer coordinate and its old REVISE result;
- the R4 inline TASK074_TO_TASK075 ABI hash and R9-only worker assumptions;
- LOCAL_PRIMARY_NARRATION_PRE_V2;
- LOCAL_PRIMARY_NARRATION_RESULT_SINK_V2;
- LOCAL_VOICE_NATIVE_RESULT_V1;
- LOCAL_PRIMARY_NARRATION_POST_WAV_V2;
- VOICE_QUALITY_ADMISSION_READBACK_V2;
- LOCAL_VOICE_LISTENING_RECEIPT_V1;
- LOCAL_VOICE_REVIEW_JOIN_V1;
- invented TASK071 Local Voice V3 inference/playback capabilities;
- invented TASK072 Local Voice V3 profiles, begin method and registry order;
- any R4/R5 proposal to alias or compatibility-promote
  AUDIO_VOICE_COMPUTE_ADMISSION_V1 to LOCAL_VOICE_COMPUTE_ADMISSION_V1. Current
  TASK-073 D4 AUDIO allowlisting remains canonical until its owner amendment;
  R6 itself creates no retirement or LOCAL acceptance;
- LOCAL_VOICE_PLAYBACK_AUTHORIZATION_V2 and any Task071 playback approval;
- any direct OUTPUT_PCM_WAV_WRITE_HANDLE or child-owned WAV publication;
- any worker creation before Task076 exact IN_FLIGHT selection;
- any Task075 process/abort state parallel to Task076;
- PCM16, block alignment two and byte rate 96,000;
- fixture-first authority and fixture completion as B/C/D execution proof;
- any R5 interpretation that a post-admission Task066 expiry/drift may refresh,
  retry, reuse a child or mint a D4 result without exact current compute/network
  producer truth and exact V3/Task074/Task076 closure;
- acceptance text that requires a fresh Human approval to Play rather than to
  decide after playback;
- old completion template hashes and any implied PASS receipt.

R6 preserves:

- fail-closed and effect-zero boundaries;
- no paid/Cloud Provider, download, Release, Deploy or Production Activation;
- exact-one operation and burn-on-entry/exception;
- no blind retry, scan, foreign cleanup or backend switch;
- same-handle/identity currentness and same-bytes/different-identity rejection;
- body/path/secret-free public surfaces;
- retained evidence on unknown outcome;
- independent DEV-4 Critic/Tester/Judge requirements.

## 21. Acceptance criteria

Independent R6 design review may PASS only when:

1. exact ownership and the current one-file Allowed Files are respected;
2. all R4 supersessions are unambiguous and no obsolete ABI remains normative;
3. the one worker order exactly matches Task076 V3 custody and Task074 R13;
4. child output is PCM24 over authenticated IPC and Task014 alone owns WAV;
5. the D4/R1 result ABI, field order, terminal stages and nullability are exact;
6. network isolation is an explicit N.C. producer Gate and not inferred;
7. CPU/CUDA/AUTO behavior and unified EXE/model UI are testable;
8. all six Task071 V2 actions and the playback-versus-decision separation are
   exact;
9. ACCEPT/REJECT/RETEST/REGENERATE/revoke/purge terminal effects are closed;
10. restart/fault behavior forbids blind replay and unknown-state cleanup;
11. PCM_S24LE 48000 mono and strict RIFF grammar are exact;
12. no fixture, public mapping, hash or design receipt creates authority;
13. verification covers focused, negative, fault, Windows native, package and
    unified EXE integration;
14. post-admission compute and/or network expiry/drift selects exactly one
    phase-correct V3 abort or exactly-one tagged private terminal union, observes
    every noncurrent predicate, terminates/waits at most once, fail-closes the
    exact Task014 call/sink or preserves UNKNOWN, closes and retires the Task074
    lease only with handle0, preserves foreign objects, creates no second child
    and mints no D4 result without exact current compute and network bindings;
15. unresolved design Critical/High findings are 0/0 and Judge returns PASS.

Design acceptance does not close any section 19 N.C. dependency and does not
authorize source, test, native, model, Human, Release, Deploy or Production
effects.

## 22. Completion receipt template

This template is design-review administrative Evidence only. It cannot be used
as an implementation completion receipt, and any omitted/missing gate remains
DEPENDENCY_NC. No PASS is recorded in R6.

    task: TASK-075
    design_identity: TASK075-PTD-LOCAL-VOICE-EXECUTION-LISTENING-V6
    base: origin/main@354ea2534ad5739a099d9eeaf0f1da9a7210ddb6
    worktree_head_at_r6_edit: 76652c5954e11166f91415d5adb7bb80dd648650
    allowed_files: docs/ai-team/tasks/TASK-075/complete-design-packet.md
    review_target_sha256: PENDING_R6
    critic: INDEPENDENT_REVIEW_PENDING
    judge: INDEPENDENT_REVIEW_PENDING
    design_frozen: false
    task074_design_dependency: DESIGN_ACCEPTED_R13
    task074_task_sha256: 838349D63E6A390727BE58EB7B887372C34BFB7AA2A7E733BF8BE6AE3A945CA5
    task074_r13_sha256: E49E35DBA314EA8D170AE182DA5983D2703DBD9E103BD387AFC32EEE03132FF5
    task014_d4_implementation_gate: DEPENDENCY_NC
    task074_r13_g01_g14_implementation_gate: DEPENDENCY_NC
    task014_task074_reference_compatibility_gate: DEPENDENCY_NC
    task073_dependency: D4_PLUS_R1_R2_R3
    task073_compute_allowlist_amendment_gate: DEPENDENCY_NC
    task076_dependency: V5
    task076_v3_implementation_custody_gate: DEPENDENCY_NC
    task066_post_admission_currentness_gate: DEPENDENCY_NC
    network_isolation_gate: DEPENDENCY_NC
    task014_noncurrent_call_sink_terminal_gate: DEPENDENCY_NC
    task075_compute_noncurrent_arm_gate: DEPENDENCY_NC
    task075_network_noncurrent_arm_gate: DEPENDENCY_NC
    task075_noncurrent_terminal_union_gate: DEPENDENCY_NC
    task075_072_074_076_consumer_amendment_gate: DEPENDENCY_NC
    task071_v2_gate: DEPENDENCY_NC
    task072_owner_voice_gate: DEPENDENCY_NC
    task048_technical_qa_gate: DEPENDENCY_NC
    task041_046_listening_flow_gate: DEPENDENCY_NC
    task036_unified_exe_model_ui_gate: DEPENDENCY_NC
    task075_worker_protocol_cpu_cuda_native_gate: DEPENDENCY_NC
    owner_native_private_voice_gate: HUMAN_GATE_CLOSED
    development4_qa_plan_status: HIGH_CORRECTION_PENDING
    development4_fixture_vectors_status: VERSIONED_NC
    implementation_completion_authority: false
    source_effect: 0
    schema_effect: 0
    test_effect: 0
    native_effect: 0
    model_provider_effect: 0
    release_deploy_production_effect: 0
    authority_created: false

Any technical change after an eventual PASS requires a new exact file hash and
fresh independent review.
