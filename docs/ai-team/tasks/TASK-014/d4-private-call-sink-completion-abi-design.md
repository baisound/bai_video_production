# TASK-014 D4 — Private Call/Sink Completion ABI Design

Status: `DESIGN_ONLY / DEV-4 / EFFECT0 / SOURCE_START0`

Design identity: `TASK014-D4-PRIVATE-CALL-SINK-COMPLETION-ABI-V1`

Current design carrier: `codex/task-014-p0v-sealed-producer-boundary-handoff`
at `99d2ba2703b396b4725add4315b2de03967d3771`, based on
`origin/main@b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`.

## 1. Responsibility and effect boundary

This is a genuine continuation of TASK-014. TASK-014 already owns the
narration plan, the Local Primary admission, the call capability, the output
sink, and the post-render receipt. TASK-075 is only the future private
execution/listening consumer; it cannot recreate any TASK-014 authority.

This design creates no source, schema, test, capability, receipt, model
runtime, process, audio body, WAV, persistence, provider, playback, or Product
effect. It grants no implementation start authority.

The DEV-4 floor applies because the later implementation will bind one-use
nonserializable authority across TASK-046, TASK-066, TASK-071, TASK-072,
TASK-074, TASK-075, and TASK-076; protect private reference custody; and close
terminal/recovery behavior at a native-adjacent boundary.

## 2. Current source fact and compatibility correction

`owner_narration_local_primary.py` produces only the public, body-free
preflight. `owner_narration_local_render_admission.py` produces only the
body-free, immutable admission whose strongest decision is
`READY_FOR_EXTERNAL_DISPATCH_GATE`; every execution, dispatch, model, audio,
and Asset flag is fixed false. Neither module currently defines the call, sink,
or POST ABI below.

TASK-075 R6 records the required correction: a prior D4 call shape exposes
`open_reference_audio()` and `open_reference_transcript()` to its parent-side
consumer, while TASK-074 requires direct transfer into a child-local broker
and parent reference-body authority zero. These are not equivalent surfaces.

The required TASK-014/TASK-074 cross-owner amendment is fixed to the
versioned `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2` contract. TASK-074
owns the broker-held direct transfer of the two already-opened pinned reference
handles into the child-local broker; TASK-014 is its consumer and has parent
reference-body authority permanently zero. The amendment must bind one exact
TASK-074 reference-delegation lease, one consumer identity, one call profile,
and the call/sink/result terminal transition. It removes both parent
reference-open operations structurally, not merely by documenting a promise
not to call them. The replacement preserves the exact call/result/sink bindings
and does not permit TASK-014 to open, copy, serialize, log, retain, or
reconstruct reference audio or transcript data.

Until that amendment is canonical and its owner completion identity is
available, every prospective call/sink operation is `NOT_BOUND` and has effect
zero.

## 3. Future exact implementation allocation

The following names are fixed by this design for a later, separately allocated
source unit. They are not authorized in this unit. This section supersedes only
the future-file ceiling in the carrier handoff sections 5 and 9.2: the earlier
two-path callable recovery stays a mandatory predecessor, but its former
four-path implementation ceiling is replaced by this exact five-path unit.

| Future path | Purpose |
| --- | --- |
| `src/ai_video_production/task014_private_call_sink.py` | private nonserializable call, sink, terminal-readback, and POST composition |
| `tests/test_task014_private_call_sink.py` | focused state, authority, concurrency, and fault tests for the private composition |
| `schemas/task014-local-primary-narration-post-receipt.schema.json` | closed body-free public POST receipt contract |
| `src/ai_video_production/schema_resources/task014-local-primary-narration-post-receipt.schema.json` | byte-identical packaged schema resource |
| `tests/test_task014_local_primary_narration_post_receipt.py` | POST schema/runtime parity, redaction, and tamper tests |

The later allocation must not expand this list without a fresh authority
decision. It must not modify the existing preflight/admission source or their
schemas/tests merely to promote an admission into authority. The affected
existing symbols are read-only inputs: `LocalPrimaryNarrationPreflight`,
`compile_local_primary_preflight`, `parse_local_primary_preflight`,
`LocalPrimaryNarrationRenderAdmission`, `compile_render_admission`,
`parse_render_admission`, and `RenderAdmissionDecision`.

The preserved `task014_zero_shot_callable_contract.py` branch pair is not in
current main and is outside this future unit until its owner disposition and
current-main recovery are separately accepted. Recovery, rather than
supersession or a second callable contract, is required before this unit starts.
The synthetic
`task014_local_inference_worker.py` branch remains a behavioral oracle only;
it must never be widened into the production executor.

## 4. Private ABI

`TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1` is an in-process, nonserializable,
noncopyable, one-use object. It is minted only by a future private resolver
after it resolves all owner inputs in the same operation. It has no public
constructor, factory, mapping parser, pickle representation, `__all__` export,
or body-opening API.

This ABI mints only `ZERO_SHOT_LOCAL` plus `PREVIEW`, the exact values of
`LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2`. `FINE_TUNED_LOCAL` is a reject-only
negative input with `ROUTE_NOT_SUPPORTED_BY_CALL_PROFILE` and effect zero until
a separately versioned TASK-014 profile and a fresh TASK-075 review accept it.

Call state machine:

```text
UNBOUND -> ARMED -> DISPATCHING -> IN_FLIGHT -> RESULT_BOUND -> CONSUMED
                 \----------------> FAILED_CLOSED
ARMED -----------\-> FAILED_CLOSED
```

The complete successor callable surface is exactly `inspect_profile()`,
`open_script_text()`, `inspect_model_runtime()`,
`begin_dispatch(task075_consumer_identity)`, and `fail_closed(reason_code)`.
The reference-open methods are absent. `begin_dispatch` returns one opaque
`CALL_DISPATCH_LEASE` bound to the exact TASK-075 consumer identity, operation,
and call state. Only the exact authenticated executor handoff can move `ARMED`
to `DISPATCHING`. The mandated successor sequence is: selected TASK-076 V3
dispatch consumes the lease once; `issue_and_arm_job_child_v3` creates the
selected child/job custody; TASK-072 `REFERENCE_ATTACHMENT_BEGIN_ABI_V1` then
consumes the exact TASK-074 attachment and closes the parent reference-body
authority; only its exact successful readback permits the selected TASK-076
`DISPATCHING -> IN_FLIGHT` transition. Each earlier or later state is rejected;
TASK-076 cannot skip TASK-072 or infer that parent body authority closed. A
`TASK014_CALL_PRECLOSE_SNAPSHOT_V1` is valid only for this explicit `IN_FLIGHT`
state, the exact TASK-072 attachment-begin readback, and its exact selected
TASK-076 vector; `DISPATCHING` never aliases it. A duplicate, concurrent caller, direct
construction, copied object, deserialized data, stale binding, consumer
mismatch, or any exception burns the old object. `CONSUMED` and
`FAILED_CLOSED` are terminal. Neither retry nor mode switch is allowed on that
object.

`NARRATION_OUTPUT_SINK_CAPABILITY_V1` is a second private one-use object bound
to the exact call, operation, installed session, writer identity, PCM S24LE
48 kHz mono format, frame/output bounds, and TASK-014-owned staging identity.
The child exposes only the fixed TASK-075 authenticated bootstrap/control
channel. It is a one-use, process-local, nonserializable channel capability;
its authentication material remains internal and it never exposes a sink,
session, handle, path, or PCM body through a control result. This D4 design does
not create a parallel envelope or JSON wire format. The byte wire is exactly
TASK-075 §11.2: **one-byte kind followed by unsigned little-endian uint32
payload length**, with only `HANDSHAKE`, `CONTROL`, `PCM24`, and `TERMINAL`.
`CONTROL` alone is strict closed UTF-8 JSON (maximum 65,536 bytes); `PCM24` is
positive, divisible by three, and at most 49,152 bytes per frame. The existing
TASK-075 fixed bootstrap/control authentication binds the exact operation,
`CALL_DISPATCH_LEASE`, selected worker instance, selected child-process custody,
and one-use channel nonce before the sole `HANDSHAKE`; it is not represented by
caller-controlled JSON fields. `HANDSHAKE` and `TERMINAL` are exact-once;
TASK-075's ordered frame accounting binds each accepted PCM payload to the
same authenticated channel, contiguous frame order, fixed S24LE/48 kHz/mono
format, and configured cumulative byte/frame limits.

The parent verifies that fixed channel authentication and exact lease/operation/
worker/process custody before passing a PCM payload to its private write session.
A foreign worker, authentication mismatch, duplicate or replayed
handshake/frame/terminal, reordered or gapped frame, late frame after terminal,
wrong PCM alignment/bounds, malformed CONTROL JSON, or unknown kind causes one
parent-side abort and `FAILED_CLOSED`; it never falls back to syntactic
acceptance or a new child. The parent alone validates received PCM24 frames
through its private write session. The child cannot obtain a session, call
`write_pcm24`, `finish`, or `abort`, select a destination, reopen a handle,
publish, delete, or replace a WAV.

```text
UNBOUND -> READY -> WRITING -> BODY_VERIFIED -> RESULT_BOUND -> COMMITTED
                    \---------------------------------------> FAILED_CLOSED
READY -------------------------------------------------------> FAILED_CLOSED
```

The sink capability surface is exactly `begin(call_dispatch_lease)`,
`inspect_terminal(task014_owner_identity)`, and `fail_closed(reason_code)`.
`begin` may return only a parent-held `SINK_WRITE_SESSION` or `SINK_REJECTED`.
The worker/child never receives the session, the sink, or a staging handle.
The parent receives authenticated frames over the worker protocol and alone
invokes `write_pcm24(frame_bytes)`, `finish(frame_count, waveform_sha256)`, or
`abort(reason_code)` on the session. The session is bound to one
`CALL_DISPATCH_LEASE`; it rejects a second begin, a foreign/expired lease, a
second finish, non-PCM-S24LE data, wrong channel/rate, frame-sequence gaps, and
cumulative frame/output bound overflow. `finish` verifies the owned staged
bytes, digest, and format and returns one body-free completion coordinate; it
never returns a path, handle, or body and cannot reopen after terminalization.

The live call/sink objects may bind an exact TASK-075 result only after a
matching in-process callback. The future `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1`
is body-free and may be published only after that result binding and an
independent current readback. It cannot itself authorize Asset publication,
profile promotion, training, playback, regeneration, or a later call.

POST state machine:

```text
UNBOUND -> RESULT_VERIFIED -> PREPARED -> PUBLISHED -> READBACK_VERIFIED
                         \-> FAILED_CLOSED | UNKNOWN
PREPARED ------------------\-> FAILED_CLOSED | UNKNOWN
PUBLISHED -----------------\-> FAILED_CLOSED | UNKNOWN
```

`PREPARED` is private and binds the exact call, sink completion, TASK-075
result, staged-WAV identity, and currentness generation. Publication happens
once only after the required TASK-014-owned write/readback boundary succeeds.
A post-publish readback mismatch, publication ambiguity, or observer loss
cannot be repaired by repeating POST, dispatch, sink finish, or result binding;
the old operation reaches `FAILED_CLOSED` or `UNKNOWN`.

The versioned TASK-014/TASK-074 capability contract must make
`open_reference_audio`, `open_reference_transcript`, and every indirect
parent-side body-return operation structurally absent. Its serializable/public
projection contains no reference body or reconstructable body accessor.

### 4.1 Normative POST public projection

`TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` is the sole public, body-free
projection of an otherwise private prepared result. Its Draft 2020-12 schema is
a closed object (`additionalProperties: false`), uses UTF-8 canonical JSON, and
requires every field below. `schema_version` and `receipt_type` are `const`;
all `*_sha256` values are lowercase 64-hex digests, and opaque IDs are bounded
ASCII opaque identifiers. The parser rejects duplicate keys, nonfinite values,
BOM/trailing bytes, unexpected control data, wrong type, unknown key, or missing
field before any receipt/publication effect.

| Field | Type / fixed value | Required binding |
| --- | --- | --- |
| `receipt_type` | const `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` | receipt ABI identity |
| `schema_version` | const `1` | schema/parser version |
| `status` | const `PREPARED_RESULT` | not Asset/profile/training authority |
| `operation_id` | opaque ID | exact one-use call and TASK-075 operation |
| `call_id` | opaque ID | exact `TASK014_LOCAL_VOICE_CALL_CAPABILITY_V1` result |
| `task075_result_sha256` | SHA-256 | sealed TASK-075 result binding |
| `sink_completion_sha256` | SHA-256 | exact parent-held sink completion coordinate |
| `currentness_generation_sha256` | SHA-256 | independent current-readback generation |
| `correlation_id` | opaque ID | exact POST publication/readback correlation |
| `projection_sha256` | SHA-256 | SHA-256 of canonical UTF-8 JSON containing all preceding fields, with this field omitted |

No field may contain a WAV/body byte, transcript, private voice identity,
credential, host path, handle, staging path, file name, or reconstructable body
locator. Runtime parsing constructs an immutable private parsed-receipt object
only after schema validation; publication and independent readback compare every
field and recompute `projection_sha256` from the same canonical bytes. The
expected readback result is the exact same closed public projection and digest
bound to the same correlation; any missing, added, substituted, or changed field
is a body-free failed-closed/unknown outcome. Future focused tests assert
schema/parser parity and every table field, including canonical-digest,
closed-key, tamper, and redaction negatives.

The Task014-owned noncurrent amendment must expose exact
`TASK014_CALL_PRECLOSE_SNAPSHOT_V1`, `TASK014_SINK_PRECLOSE_SNAPSHOT_V1`,
`TASK014_CALL_FAILED_CLOSED_READBACK_V1`,
`TASK014_SINK_FAILED_CLOSED_READBACK_V1`, and
`TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1`. The first two bind respectively
`IN_FLIGHT` and `WRITING|BODY_VERIFIED` state. Exactly one fail-closed call or
sink-abort transition may produce the two durable failed-closed readbacks. Only
the exact `TASK014_RECEIPT_ONLY_PREPARED_RESULT_V1`, bound to
`JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`, may be supplied as TASK-076
V3's mandatory fourth terminal-consumer argument. It must be joined with the
exact TASK-075 `TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2` then
`TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2`, and the exact selected
Task076 V3 custody/terminal vector; a generic result, equal digest, alternate
receipt-only type, a V1 union, or a relabelled vector is rejected. Compute/network
currentness loss must use that exact tagged union through its owner amendment;
it must not resume, re-dispatch, mint a D4 result, or invent a TASK-014 terminal
snapshot.

## 5. Required input binding

One private resolver operation must bind all of the following exact current
owner outputs; a public receipt, display projection, fixture, digest, or
matching caller field is never a substitute.

1. TASK-014 Project, narration-plan, preflight, render-admission, and trusted
   current-time coordinates;
2. TASK-046 private current reference/transcript binding for zero-shot, or the
   distinct Dataset/ModelCandidate/artifact chain for fine-tuned, never both;
3. TASK-066 private one-use compute admission tied to workload, runtime/process,
   profile, and readback;
4. TASK-071 exact live `OWNER_VOICE_LOCAL_INFERENCE_V1` authority together with
   the TASK-072 consumer ticket and worker-begin profile;
5. TASK-074 sealed route/reference and broker-delegation handoff; and
6. TASK-075 exact executor/result ABI plus TASK-076 custody and terminal
   readback identities.

Fine-tuned and zero-shot routes are disjoint. The future resolver must reject
both/neither route input, a route discriminator mismatch, and any attempt to
use zero-shot reference authority as fine-tuned model authority.

## 6. Negative and fault matrix

| ID | Input or fault | Required result |
| --- | --- | --- |
| N1 | selected route lacks exact engine, resource, rights, or reference authority | no mint; executor/model/audio/persistence delta 0 |
| N2 | TASK-046 public readback/projection supplied as authority | reject before mint; no child call |
| N3 | copied/self-created callable receipt, envelope, or matching digest | reject; no capability |
| N4 | TASK-048 calibration fixture/projection used as authority | reject; no model/provider/Asset/profile effect |
| N5a | fine-tuned route, even with otherwise matching model inputs | `ROUTE_NOT_SUPPORTED_BY_CALL_PROFILE`; no executor call |
| N5b | zero-shot/fine-tuned substitution or mixed route inputs | closed route rejection; no executor call |
| N6 | stale/wrong Project, plan, profile, reference, model, runtime, compute, Human ticket, or time | fail closed; no recompute or retry |
| N7 | direct/copy/replace/pickle/deserialized capability | type/seal rejection; no child call |
| N8 | double/concurrent use or reuse after exception | at most one executor entry; old object terminal |
| N8b | child attempts to obtain/call the parent session or a write/finalize/abort method, or emits foreign/authentication-mismatched/replayed/reordered/late TASK-075 frames | structural/fixed-channel rejection; parent aborts once, old sink is `FAILED_CLOSED`, no handle/body/path disclosure |
| N9 | raw script/audio/transcript, private voice ID, credential, or host path | reject without persistence or diagnostic disclosure |
| N10 | executor reply lacks sealed result and independent current readback | no POST/Product PASS/Asset or profile effect |
| F1 | resolver exception before mint | no capability and no external effect |
| F2 | call/sink begin rejection | both relevant objects fail closed; child/release/POST 0 |
| F3a | exception after dispatch entry or partial sink write | exact one fail-closed transition; retain exactly the same TASK-014-owned staging identity as `FAILED_CLOSED` for separately authorized owner recovery/purge, with no create/replace/delete after fault, body/path/handle disclosure, retry, or second child. The immutable failed-closed inventory/readback binds staging identity, writer/session identity, PCM format, accepted contiguous frame sequence and count, cumulative byte count, incremental digest, staged-byte digest, and immutable disposition. Partial-write/readback mismatch, staging substitution, and recovery/purge with any nonmatching field are rejected without effect |
| F3b | loss after `BODY_VERIFIED` but before result binding | no RESULT_BOUND/POST; exact terminal readback is required |
| F3c | loss after result binding but before sink commit/readback | no public POST; no second dispatch; terminal currentness decides `FAILED_CLOSED` or `UNKNOWN` |
| F3d | compute/network becomes noncurrent after release | consume only the exact tagged TASK-075 terminal union; no resume, re-dispatch, D4 result, or fabricated TASK-014 snapshot |
| F3e | wrong/missing Task076 V3 selected vector, `JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1`, fourth argument, `TASK075_NONCURRENT_OPERATION_PRE_CLOSE_ARM_V2`, or `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V2` | reject terminal crosswalk; durable readback is `FAILED_CLOSED` or `UNKNOWN`; no resume, re-dispatch, or substitute result |
| F4a | POST prepare/write failure before publication | no public receipt; old operation terminal; no second dispatch/sink finish |
| F4b | POST publish success followed by readback loss, mismatch, or observer failure | `FAILED_CLOSED` or `UNKNOWN`; no fabricated receipt or repeat publish on the old operation |

All matrix rows require body-free diagnostics, no absolute path or secret
leakage, and no provider, network, process, model, GPU, playback, WAV, Asset,
or persistence effect in the future unit's dependency-absent test mode.

The POST suite must also prove a Draft 2020-12 closed-key schema, runtime
parser/schema parity, byte-identical public/resource schema mirrors, digest and
field tamper rejection, and redaction of every body/path/handle/credential
field. A schema-valid public receipt alone remains Evidence and cannot mint a
call, sink, result, or POST authority.

## 7. Source-start gate

The source unit may start only after all conditions are true:

1. this design receives independent DEV-4 Critic, Tester, and Judge decisions
   with unresolved Critical/High equal to zero;
2. a fresh main rebind confirms the design carrier's ownership and exact path
   overlap are clear;
3. `TASK014_TASK074_CHILD_LOCAL_DIRECT_TRANSFER_V2` is canonical with its exact
   TASK-074 owner completion identity, delegation-lease identity, and
   TASK-014 consumer/port identity bound into the future fixture; the fixture
   must prove parent reference-open authority is structurally absent;
4. TASK-046, TASK-066, TASK-071, TASK-072, TASK-074, TASK-075, and TASK-076
   publish the required private completion identities/ports;
5. the preserved callable-contract branch has an explicit preserve, recover, or
   supersede disposition; and
6. a separate source allocation names the five paths in section 3, validates
   fresh branch/worktree/dirty/lock state, and retains effect zero until a
   later native Human Gate.

Before those conditions, the only valid result is `DEPENDENCY_NC` / effect zero.
