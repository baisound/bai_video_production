# TASK-075 — Local Voice Execution and Listening

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK075-PTD-LOCAL-VOICE-EXECUTION-LISTENING-V1`

Canonical design base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-075 owns the Product-private execution and listening boundary that turns one
fresh TASK-014 Local Primary narration plan into at most one local native
inference, one verified staged PCM WAV and, after TASK-048 quality admission, at
most one local playback operation.

The exact one-way Product contract is:

```text
TASK-014 PRE
    -> TASK-066 compute admission
    -> TASK-071 Human authorization
    -> TASK-072 one-use child operation
    -> TASK-075 native local inference
    -> TASK-014 POST WAV
    -> TASK-048 quality admission
    -> TASK-071 playback Human authorization
    -> TASK-072 one-use playback operation
    -> TASK-075 local playback
    -> TASK-041 audio review inclusion
```

No step may be skipped, reordered or inferred from an equal public hash. The
inference and playback operations are separate one-use operations with separate
stable semantic keys, tickets, child processes, configs, states and terminal
receipts. Rendering does not authorize playback. Playback does not mean the
Human accepted the audio. TASK-041 remains the owner of the review decision.

TASK-075 does not train or download a model, choose a voice, change a Voice
Profile, publish an Asset, place audio on a Timeline, call a paid/Cloud Provider,
or grant Production use. It supplies a fail-closed execution/listening bridge
for already admitted local Product inputs.

## 2. Fresh source-backed gap

The current canonical source does not implement this boundary:

- `owner_narration_local_primary.py` explicitly stops at
  `READY_FOR_OWNER_HUMAN_GATE`; all execution/model/GPU/Asset flags remain false.
- `owner_narration_local_render_admission.py` explicitly stops at
  `READY_FOR_EXTERNAL_DISPATCH_GATE`; it renders no audio and its public
  `ExecutionAuthorizationBinding` is reconstructible data.
- the TASK-014 render admission binds a registered TASK-043 Job and private WAV
  destination metadata, but does not start a worker, retain an output handle,
  validate WAV bytes, publish a post-render receipt or reconcile a crash.
- public TASK-066 probe/capability objects are evidence and are not a trusted
  Product launch capability.
- TASK-071 candidate v1 supports only preference promote/rollback and connector
  activate/deactivate. It has no Local Voice Human action.
- TASK-072 candidate v1 has no Local Voice inference or playback action profile.
  `GPU_REQUIRED_LAUNCH` authorizes only its exact GPU worker launch and cannot be
  reinterpreted as narration inference.
- `voice_quality_calibration.py` classifies typed quality evidence but performs
  no audio read, analyzer launch, inference or playback.
- `audio_workspace_media_review.py` validates an external review binding but
  explicitly performs no playback/waveform effect. Its public record/self-hash
  cannot prove that sound was played by the Product.
- no canonical source binds one actual local inference process, its exact input
  handles, compute route, output file identity/bytes, quality receipt and later
  playback process into one current operation chain.

Historical TASK-014/TASK-041/TASK-048 tests remain regression evidence. They do
not constitute native execution, Human authority, output durability or listening
proof.

## 3. Responsibility boundary

TASK-075 owns:

- the closed Local Voice action family and versioned consumer ABIs;
- private Product composition for local narration inference and playback;
- exact inference/listening semantic operation keys;
- Product-private input-handle and output-handle transfer contracts;
- the native worker protocol and fixed process/image/currentness checks;
- inference and playback state machines, one-use entry and burn behavior;
- staged PCM WAV structural, length, checksum and physical-identity validation;
- correlation of TASK-014 PRE, compute, Human, operation, native result,
  TASK-014 POST WAV, TASK-048 quality and TASK-041 review coordinates;
- body/path-free public status and audit projections;
- versioned fixture bundles for Voice (`V`), Listening (`L`) and Evidence (`E`);
- fault, recovery, focused, packaging and Windows-native QA contracts.

TASK-075 does not own:

- script approval, narration semantics, Voice Profile, consent, rights, model
  admission, TASK-014 PRE or POST domain semantics (TASK-014);
- compute profile, adapter selection, workload admission or GPU proof (TASK-066);
- Human challenge/UI/user-presence authority (TASK-071);
- operation ticket/config, generic broker state or child authority (TASK-072);
- generic immutable authority I/O (TASK-068);
- durable Product Job semantics/currentness (TASK-043 and future TASK-076);
- quality policy, analyzer semantics or quality decision (TASK-048);
- Audio Workspace review decision, Asset proposal or placement (TASK-041);
- Project, Timeline, Asset, Provider, Credential, installer or package ownership;
- TASK-074 Product semantics;
- Release, Deploy, Production Activation, paid execution, model/runtime download,
  private-media upload, training, destructive cleanup or external-account change.

TASK-074 remains Design A-owned. TASK-075 may perform security/authority review
of a TASK-074 integration port but may not define or change TASK-074 semantics.

## 4. One-way artifact/phase dependency graph

Task completion names are too coarse because fixtures can freeze before real
native producers. The graph therefore uses exact phase artifacts:

```text
TASK-014 LOCAL_PRIMARY_NARRATION_PRE_V2 fixture
TASK-066 LOCAL_VOICE_COMPUTE_ADMISSION_V1 fixture
TASK-071 TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2 fixture
TASK-071 TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2 fixture
TASK-072 LOCAL_VOICE_ACTION_PROFILE_V2 fixture
    -> TASK-075-A V/L/E_FIXTURE_BUNDLE_V1

TASK-014 canonical LOCAL_PRIMARY_NARRATION_PRE_V2
TASK-066 private current LOCAL_VOICE_COMPUTE_CAPABILITY_V1
TASK-071 live TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2
TASK-072 live LOCAL_VOICE_INFERENCE_TICKET_V2
    -> TASK-075-B native inference

TASK-075-B exact native terminal + exact staged-WAV readback
    -> TASK-014 LOCAL_PRIMARY_NARRATION_POST_WAV_V1

TASK-014 POST WAV V1
TASK-048 VOICE_QUALITY_ADMISSION_READBACK_V2
TASK-071 live TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2
TASK-072 live LOCAL_VOICE_PLAYBACK_TICKET_V2
    -> TASK-075-C local playback

TASK-075-C LOCAL_VOICE_LISTENING_RECEIPT_V1
    -> TASK-041 EXTERNAL_AUDIO_REVIEW_INCLUSION_V2
```

TASK-075-A is fixture-only and may complete before the producer implementations.
TASK-075-B/C remain `DEPENDENCY_NC` until every exact real producer receipt and
installed native package readback exists. A fixture, public dataclass, mapping,
hash or old version cannot satisfy B/C.

TASK-071 and TASK-072 candidate v1 packets are read-only design inputs and are
not canonical on this base. Their frozen action registries omit Local Voice.
TASK-075 therefore requires separate cross-owner versioned registry amendments;
it does not silently extend v1 or edit those Tasks.

## 5. Design PR and future implementation scope

This design PR may change exactly:

- `docs/ai-team/tasks/TASK-075/complete-design-packet.md`

After independent Critic `C/H=0`, Judge `PASS`, canonical dependency receipts,
fresh overlap/lock checks and a separate implementation start receipt, a future
TASK-075 implementation may change exactly:

- `src/ai_video_production/local_voice_execution.py`
- `src/ai_video_production/local_voice_listening.py`
- `src/ai_video_production/local_voice_windows.py`
- `schemas/local-voice-operation-event.schema.json`
- `schemas/local-voice-native-result.schema.json`
- `schemas/local-voice-listening-receipt.schema.json`
- `src/ai_video_production/schema_resources/local-voice-operation-event.schema.json`
- `src/ai_video_production/schema_resources/local-voice-native-result.schema.json`
- `src/ai_video_production/schema_resources/local-voice-listening-receipt.schema.json`
- `native/task075_local_voice_worker/CMakeLists.txt`
- `native/task075_local_voice_worker/include/bvp_local_voice/protocol.hpp`
- `native/task075_local_voice_worker/include/bvp_local_voice/wav_contract.hpp`
- `native/task075_local_voice_worker/src/main.cpp`
- `native/task075_local_voice_worker/src/protocol.cpp`
- `native/task075_local_voice_worker/src/wav_contract.cpp`
- `native/task075_local_voice_worker/tests/protocol_tests.cpp`
- `native/task075_local_voice_worker/tests/wav_contract_tests.cpp`
- `native/task075_local_voice_worker/scripts/build.ps1`
- `native/task075_local_voice_worker/scripts/test.ps1`
- `native/task075_local_voice_worker/scripts/package.ps1`
- `tests/test_task075_local_voice_execution.py`
- `tests/test_task075_local_voice_listening.py`
- `tests/test_task075_local_voice_windows.py`
- `tests/test_task075_local_voice_packaging.py`
- `tests/fixtures/task075/voice-inference-fixture-v1.json`
- `tests/fixtures/task075/voice-listening-fixture-v1.json`
- `tests/fixtures/task075/voice-evidence-fixture-v1.json`
- `tests/fixtures/task075/voice-wav-valid-mono-48000-pcm16.wav`
- `tests/fixtures/task075/voice-wav-malformed-corpus-v1.json`
- `docs/ai-team/tasks/TASK-075/complete-design-packet.md`

No executable fixture helper, alternate receipt, supplemental Evidence document
or additional file is implied by a directory name. Any new filename requires a
separately reviewed Atomic Unit allocation receipt before it may be written.

Changes to TASK-014, TASK-036, TASK-041, TASK-043, TASK-048, TASK-063, TASK-066,
TASK-068, TASK-070, TASK-071, TASK-072, TASK-074, TASK-076, installer/build specs,
`pyproject.toml`, shared current-state/task-index/roadmap, CHANGELOG or another
Task require that owner's separate exact amendment and fresh lock/overlap.

## 6. Trust and threat boundary

### 6.1 Trusted Production components

Production fixes and attests:

- the packaged BVP Product parent process/image/build;
- the packaged TASK-075 native worker image/build/protocol;
- the TASK-066 trusted compute capability verifier/version;
- the TASK-071 Human broker and exact Local Voice action profile version;
- the TASK-072 broker/ticket/config/channel implementation/version;
- the TASK-014 PRE/POST and TASK-048/TASK-041 trusted reader ports;
- the Product-owned script, model/reference and output handles;
- the Windows process/token/session/handle currentness implementation;
- the trusted monotonic/boot/session clock supplied by the broker.

No argv, environment, current directory, public JSON, model name, path, UI
mapping, module token, Python monkeypatch, hook, injected backend or caller clock
selects a Production engine, model, compute route, process, output, player or
receipt verifier. Test doubles exist only in a separate fixture composition and
always report `production_eligible=false`.

### 6.2 Protected attackers

V1 protects against:

- public-object construction, copy/replace, pickle/deserialization and rehash;
- caller-selected script/Profile/model/action/ticket/time/path/backend;
- replay, concurrent consume, exception reuse and new-random-ID retry;
- wrong process, build, Windows user/session/logon or inherited handle;
- script/model/reference/output/config substitution before, during or after use;
- same bytes at a different physical file identity;
- hardlink, reparse, ancestor, DACL and operation-root drift;
- malformed, oversized, reordered or replayed child frames;
- partial/malformed WAV, header/data length mismatch and post-close swap;
- quality/listening/Task041 receipt forgery or cross-operation substitution;
- path, script, voice, model, OS-detail or secret leakage through public surfaces.

### 6.3 Explicit non-goals

V1 does not resist administrator/kernel compromise, process injection, debugger
or memory extraction from a trusted Product/worker, compromised release signing,
physical audio capture from speakers, or a user deliberately sharing generated
audio. These are not claimed negatives.

## 7. Versioned producer and consumer ports

### 7.1 `LOCAL_PRIMARY_NARRATION_PRE_V2`

TASK-014 supplies a private current readback, not its current public dataclass.
It binds:

- exact project, preflight, admission and revision/predecessor identities;
- route `ZERO_SHOT_LOCAL` or `FINE_TUNED_LOCAL`;
- usage `PREVIEW` or `FULL_RENDER`;
- approved script revision and exact private script-content handle identity,
  byte length, UTF-8 canonical digest and privacy policy;
- current Voice Profile revision, consent and rights evaluations;
- engine/model/runtime/code/license and exact model/reference handle identities;
- TASK-043 registered Job identity/idempotency/currentness;
- private output-staging parent, policy, quota, retention and expected artifact
  class `STAGED_NARRATION_PCM_WAV_48000_MONO`;
- expiry, trusted reader/build identity and complete preflight fingerprint.

The handle set remains in the trusted Product process. Paths, script body, voice
bytes and model bytes are not serialized into the TASK-072 config or public
receipt. The current `LocalPrimaryNarrationPreflight`,
`LocalPrimaryNarrationRenderAdmission` and `ExecutionAuthorizationBinding` are
audit/compatibility evidence with `authority_created=false`.

### 7.2 `TASK066_LOCAL_VOICE_COMPUTE_CAPABILITY_V1`

TASK-066 supplies a private one-use compute capability bound to:

- exact Local Voice workload profile and required/allowed backend;
- actual Product-owned probe run/process/runtime/adapter evidence;
- InstallLayout, helper/model/runtime/build identities;
- selected adapter LUID digest and resource ceilings;
- current DesktopCompute profile revision;
- exact TASK-075 inference operation key basis;
- Product boot/session/deadline and invocation budget one.

Public `ProbeResult`, `ProbeCommand`, `RuntimeModuleEvidence`,
`capability_from_probe_result`, self-hashes and module tokens create no
capability. `GPU_REQUIRED_LAUNCH` is not reused as a generic narration command.
The TASK-066 amendment must freeze an explicit Local Voice workload class and
its fallback policy. Unknown or unsupported compute state is effect zero.

The capability is a private broker object, not a Python/public-data object. Its
closed lifecycle is `ISSUED -> ATTACHED -> IN_FLIGHT` or
`ISSUED|ATTACHED -> BURNED`. TASK-066 exposes only these Product-private calls:

```text
attach_local_voice_compute(operation_key, expected_fingerprint,
                           task072_broker_channel) -> ATTACHMENT_HANDLE
consume_attached_compute(ATTACHMENT_HANDLE, BROKER_BEGIN_NONCE)
        -> COMPUTE_IN_FLIGHT_READBACK
terminalize_compute(COMPUTE_IN_FLIGHT_READBACK, terminal_class)
        -> COMPUTE_TERMINAL_READBACK
```

`attach` validates the still-current run/helper/backend/layout/profile and
irreversibly transfers the invocation budget to the TASK-072 broker. The handle
cannot be returned, copied or attached to another broker. The single TASK-072
begin transaction invokes `consume_attached_compute`; success, exception,
channel loss or concurrent entry burns it. `COMPUTE_IN_FLIGHT_READBACK` binds
the exact operation, broker begin nonce, backend and adapter currentness. No
TASK-075 call can validate or burn a public TASK-066 receipt by itself.

### 7.3 TASK-071 Local Voice amendment

TASK-071 must add a versioned registry, not mutate the meaning of v1:

| Human action | Exact TASK-075 producer ABI | Meaning |
|---|---|---|
| `LOCAL_VOICE_PREVIEW_RENDER` | `TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2` with exact preview action | one preview inference for the displayed script/Profile/revision |
| `LOCAL_VOICE_FULL_RENDER` | `TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2` with exact full action | one full-render inference for the displayed script/Profile/revision |
| `LOCAL_VOICE_PLAYBACK` | `TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2` | one whole-file playback of the displayed admitted narration |

The private action plan binds PRE V2, compute profile, operation key, output
class, current user/session/build, expiry and closed Japanese display digest.
The display shows only fixed action copy, approved script title/opaque revision,
Voice Profile display label and Preview/Full Render. It never displays the
script body, path, hash, account, SID, model path or backend detail.

Human capability remains broker-side live state plus the exact authenticated
channel. Public evidence, a click, confirmation boolean/string, caller time or
serialized receipt is not authority. Preview, Full Render and Playback are not
mutually substitutable. Playback display binds the exact POST, quality admission
and opaque narration label, but never audio/path content. Cancel, timeout,
failed verification, exception and first consume burn the capability.

### 7.4 TASK-072 Local Voice action profiles

TASK-072 must add a versioned closed registry:

| Action profile | Required private producers | Exact effect |
|---|---|---|
| `LOCAL_VOICE_INFERENCE_PREVIEW` | TASK-014 PRE V2, TASK-066 compute capability, TASK-071 `TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2` preview action, TASK-075 authorization | start one exact native preview inference |
| `LOCAL_VOICE_INFERENCE_FULL` | TASK-014 PRE V2, TASK-066 compute capability, TASK-071 `TASK071_LOCAL_VOICE_INFERENCE_CAPABILITY_V2` full action, TASK-075 authorization | start one exact native full inference |
| `LOCAL_VOICE_PLAYBACK` | TASK-014 POST WAV V1, TASK-048 quality readback V2, TASK-071 `TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2`, TASK-075 `LOCAL_VOICE_PLAYBACK_AUTHORIZATION_V1` | play one exact admitted WAV once |

The immutable operation config contains only opaque IDs/digests, exact profile,
fixed command, expected handle roles, build/protocol digests, expiry and budget
one. It contains no path, script/body, voice/model bytes, audio bytes, raw
handle value, backend selector, player selector, clock or failure hook.

Inference receives the TASK-066 and matching TASK-071 live capabilities before
child start. Playback receives a distinct
`TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2`; a
public request/click is request-only and cannot mint it. It uses a fresh exact
ticket after quality PASS. All capabilities/tickets enter through the one
TASK-072 broker begin transaction below and burn on success or exception.

### 7.5 `TASK075_INFERENCE_AUTHORIZATION_V1`

The trusted TASK-075 Product operation derives a stable semantic key from:

- exact PRE V2 fingerprint and admission revision;
- route, usage, script and Voice Profile revisions;
- model/runtime/reference identities;
- output policy and expected WAV contract;
- compute operation fingerprint;
- Human action-plan fingerprint;
- Product/worker/broker protocol and build identities.

UI request ID, ticket ID, nonce and timestamps do not change the semantic key.
An unresolved prior reservation/IN_FLIGHT/unknown terminal blocks issuance with
all evidence preserved. Only an exact trusted no-effect reconciliation may
produce a predecessor-bound fresh admission revision.

The live authorization is supplied over the Product/broker channel and cannot
be constructed from a Python class or JSON mapping.

### 7.6 TASK-072 broker-owned atomic begin

TASK-072 owns one private `begin_local_voice_operation_v2` entrypoint. TASK-075
cannot individually consume TASK-066, TASK-071 or TASK-072 authorities:

```text
begin_local_voice_operation_v2(
    OPERATION_CHANNEL,
    TASK075_PREPARED_RESERVATION_HANDLE,
    TASK066_ATTACHED_COMPUTE_HANDLE | NONE_FOR_PLAYBACK,
    TASK071_ATTACHED_HUMAN_HANDLE,
    TASK072_LIVE_TICKET_HANDLE,
    exact_producer_currentness
) -> TASK072_LOCAL_VOICE_IN_FLIGHT_LEASE_V2

abort_prepared_local_voice_operation_v2(
    OPERATION_CHANNEL,
    TASK075_PREPARED_RESERVATION_HANDLE | NONE,
    attached_handle_set,
    closed_no_effect_reason
) -> TASK072_LOCAL_VOICE_ABORTED_READBACK_V2
```

Before this call TASK-075 may durably publish only one immutable `PREPARED`
reservation containing no output and no authority. The broker revalidates all
handles, action/profile equality, semantic key, predecessor, session/build,
deadline and producer currentness inside one serialized broker transaction. At
authenticated entry it durably records the exact begin nonce and burns the
Human, compute (for inference) and operation budgets together. Success returns
one live child-launch lease. Any exception, process/channel loss, concurrent
entry or partial durable failure burns every attached budget and records or
reconciles `BURNED_UNKNOWN`; none can be returned or reissued.

After the first attachment, every pre-begin denial, cancel, expiry, currentness
failure, PREPARED failure or caller exception must enter `abort_prepared...` on
that same broker channel. The broker serializes abort against begin, burns all
attached budgets and writes a durable, body-free, proven-no-child terminal. An
abort exception or channel loss is `BURNED_UNKNOWN`, never reusable. A public
cancel or direct TASK-066/TASK-071 abort cannot release an attached capability.

The durable TASK-072 begin journal is authoritative when TASK-075's local event
is absent. Recovery queries only the exact semantic key/begin nonce through a
private broker readback; it never scans or retries. TASK-075 publishes its
`IN_FLIGHT` event only from that readback. Failure to publish it leaves output
and child-start effect zero and the broker operation burned. Output creation
occurs only after both the broker begin and TASK-075 `IN_FLIGHT` readbacks are
durable. Thus there is no state in which an output exists while Human denial,
expiry or an unconsumed capability is reported as effect zero.

### 7.7 Native inference handle manifest

Immediately before child creation the parent revalidates every already-open
handle and transmits only role metadata over the authenticated channel:

- `SCRIPT_UTF8_READ_HANDLE`;
- `MODEL_READ_HANDLE_SET`;
- optional `REFERENCE_AUDIO_READ_HANDLE_SET` for zero-shot;
- `OUTPUT_PCM_WAV_WRITE_HANDLE` created exclusively for this operation;
- `CONTROL_CHANNEL_HANDLE`.

All handles are non-inheritable by default. The restricted child handle list
contains only the exact duplicates required by the fixed profile. No path or
glob is sent. The child rejects missing/extra/duplicate roles, wrong access,
wrong physical identity, wrong size/digest, a seekability mismatch or a handle
that is inheritable to a grandchild.

The Product holds the domain/operation leases and output handle from final input
currentness through child exit, output flush, validation and POST readback.

### 7.8 Fixed synthesis engine ABI and package readback

TASK-075 does not select a synthesis engine by arbitrary library, path, command,
Python import or serialized backend name. Before TASK-075-B implementation may
start, TASK-014 must publish the separately owned private
`LOCAL_VOICE_ENGINE_PACKAGE_READBACK_V1` and matching fixture. It binds:

- closed engine ID and ABI version `BVP_LOCAL_VOICE_SYNTH_ENGINE_ABI_V1`;
- exact packaged adapter/engine/runtime/model-set file identities and SHA-256;
- exact signed Product build/install instance and loader search policy;
- supported route, locale, sample format and bounded model-manifest grammar;
- engine-specific license/redistribution and offline/network-disabled facts;
- exact TASK-066 backend/context class and device-memory ceilings;
- native cold-start, shutdown, cancellation and deterministic error mapping.

The worker-side ABI is a fixed in-process native interface with these semantic
operations only:

```text
engine_open(PINNED_MODEL_HANDLE_SET, COMPUTE_IN_FLIGHT_READBACK,
            CLOSED_ENGINE_OPTIONS) -> ENGINE_CONTEXT
engine_synthesize(ENGINE_CONTEXT, PINNED_SCRIPT_HANDLE,
                  OPTIONAL_PINNED_REFERENCE_HANDLES,
                  OUTPUT_PCM_WAV_WRITE_HANDLE, CANCEL_HANDLE)
        -> ENGINE_TERMINAL
engine_close(ENGINE_CONTEXT)
```

Arguments are already-open handles/private readbacks; there is no filesystem
path, dynamic provider name, DLL search path, network URL, shell command,
environment-variable selector or caller callback. The build pins a single
adapter implementation and dependency manifest for each supported engine ID.
Unknown engine/ABI/model format, missing packaged identity, loader drift or a
TASK-066 backend/context mismatch is child/output effect zero. Adding an engine,
dependency, build file or runtime adapter requires an exact TASK-014 amendment
and a new TASK-075 implementation allocation; the present Allowed Files do not
authorize an invented backend.

### 7.9 Native child protocol

The child protocol is a 4-byte little-endian length-prefixed strict canonical
UTF-8 JSON frame stream, maximum frame 64 KiB and transcript 256 KiB. Exact
sequence:

```text
HELLO -> HELLO_ACCEPTED
HANDLE_MANIFEST -> INPUTS_PINNED
BEGIN_INFERENCE -> INFERENCE_IN_FLIGHT
PROGRESS* -> OUTPUT_FLUSHED
RESULT_SUMMARY -> CHILD_EXITED
```

Progress frames contain only bounded phase, integer completed/total and elapsed
monotonic buckets. They contain no script/model/audio/path/process output. Frame
duplication, reordering, unknown fields, wrong transcript, oversize/truncation,
extra bytes or child identity drift burns the ticket and yields completion
unknown after inference entry.

### 7.10 `LOCAL_VOICE_NATIVE_RESULT_V1`

The private result binds:

- inference operation/ticket/event identities;
- exact PRE, compute and Human fingerprints;
- Product/worker/model/runtime/backend/adapter identities;
- child process/token/session and handle-manifest digest;
- trusted start/end monotonic coordinates;
- exit/result state and stable body-free reason code;
- output handle physical identity, exact byte length and SHA-256;
- fixed WAV facts: RIFF/WAVE, PCM integer, mono, 48,000 Hz, 16-bit,
  block-align 2 and byte-rate 96,000;
- exact data-chunk offset/length, frame count and rational duration;
- flush/durability/readback state;
- predecessor event and terminal self-hash.

The parent parses the WAV from the same still-open output handle after the child
has closed its duplicate. It rejects extra/overlapping/truncated chunks,
multiple conflicting format/data chunks, integer overflow, odd frame length,
header/file length mismatch, non-PCM/extensible ambiguity and trailing bytes not
explicitly allowed by the closed v1 grammar. It does not reopen by path to
establish identity.

### 7.11 `LOCAL_PRIMARY_NARRATION_POST_WAV_V1`

TASK-014 owns the post-render semantic receipt. TASK-075 supplies its exact
native terminal and pinned output snapshot to TASK-014's private verifier. POST
binds:

- exact PRE/admission/Job/operation lineage;
- exact script, Voice Profile, engine/model/runtime and route/usage;
- exact staged-WAV identity/bytes/WAV facts;
- TASK-066/TASK-071/TASK-072/TASK-075 terminal identities;
- output storage/quota/retention/currentness;
- `asset_published=false`, `timeline_mutated=false`,
  `production_use_authorized=false`.

TASK-075 cannot mint POST from its own result. The current TASK-014 public
records and equal hashes cannot substitute for the private POST verifier.

### 7.12 Exact WAV custody and TASK-048 quality gate

TASK-014 owns `LOCAL_PRIMARY_WAV_CUSTODY_READBACK_V1`. During the live Product
operation it retains the original handle and duplicates read-only handles to
TASK-048 and TASK-075 playback over authenticated Product channels. Across a
Product restart, TASK-014 alone may reacquire the file beneath the same pinned
staging ancestor using nofollow open and exact persisted volume/file identity,
bytes, DACL/owner, length and hash. It rejects same bytes at another identity,
ancestor drift, reparse/hardlink, replacement or ambiguous absence. Path plus
equal bytes is never custody proof. The custody readback binds its acquisition
mode (`LIVE_DUPLICATE` or `IDENTITY_REACQUIRED`), open-handle identity and
current retention revision. TASK-048 and playback keep their duplicate handle
through their own terminal readback; neither reopens by path.

TASK-048 produces `VOICE_QUALITY_ADMISSION_READBACK_V2` from the exact POST WAV
opened snapshot and its own trusted analyzer execution. It binds analyzer,
policy, calibration/capture chain, measurement facts, currentness and exact WAV
identity. Only `PASS` permits playback in v1. `FAIL`, `UNKNOWN`, stale,
conflicting or different-identity evidence makes playback effect zero.

TASK-075 does not infer PASS from current public quality dataclasses, public
self-hashes, reason strings or matching measurements. TASK-048 performs no
playback and TASK-075 performs no quality-policy decision.

### 7.13 `LOCAL_VOICE_PLAYBACK_AUTHORIZATION_V1`

The stable playback operation key binds exact POST, quality PASS, WAV physical
identity/bytes, requested whole-file sample range, fixed system-default output
device policy, Product/player build and one TASK-071 authenticated playback
capability. The Product UI invocation only creates a request; it is not itself
authority. Changing a UI request ID does not create another operation.

V1 plays the whole admitted WAV once. Seeking, looping, speed change, alternate
device selection, waveform generation, export and DAW handoff are outside this
profile. Playback uses a dedicated child with one read handle and control
channel; it cannot write the WAV or create another artifact.

### 7.14 `LOCAL_VOICE_LISTENING_RECEIPT_V1`

After first authenticated playback entry, a private immutable terminal binds:

- playback operation/ticket/event and child identities;
- exact POST, TASK-048 and WAV snapshot identities;
- exact requested and observed sample range;
- fixed player/backend/build and output-device-policy digest;
- trusted start/end coordinates;
- `PLAYED_COMPLETE`, `CANCELED`, `FAILED_KNOWN` or `BURNED_UNKNOWN`;
- playback-started/completed booleans derived by the trusted child;
- predecessor and self-hash.

The public projection contains opaque IDs, bounded duration/counts and stable
status/reason only. It contains no audio, path, device/account, OS error, handle,
script, voice/model identity or timestamp usable as authority.

### 7.15 TASK-041 inclusion

TASK-041 must add a private `EXTERNAL_AUDIO_REVIEW_INCLUSION_V2` reader that
accepts only the exact TASK-075 listening receipt and the exact current
AudioMediaReviewIntent/source/range. Existing public
`ExternalAudioReviewReceiptBinding` is audit compatibility evidence only.

TASK-041 may create a Human review decision only after exact inclusion. A
complete playback never preselects ACCEPT/REJECT/STRIP, never creates an Asset or
placement, and never authorizes DAW/Timeline mutation.

### 7.16 Early V/L/E fixture bundles

TASK-075 publishes three versioned JSON fixtures at the exact filenames listed
in section 5 in the future implementation Task:

- `TASK075-V-LOCAL-VOICE-INFERENCE-FIXTURE-V1`;
- `TASK075-L-LOCAL-VOICE-LISTENING-FIXTURE-V1`;
- `TASK075-E-LOCAL-VOICE-EVIDENCE-FIXTURE-V1`.

Every fixture declares:

- `fixture_only=true`;
- `authority_created=false`;
- `native_worker_executed=false`;
- `real_voice_processed=false`;
- `audio_played=false`;
- `production_eligible=false`;
- fixed fake build/receipt/handle-identity digests;
- effect expectations and exact negative reason codes.

Consumers may compile against them. Fixture PASS cannot satisfy native,
installed, Human, quality, listening, Product completion or Production gates.

## 8. Operation states and transaction order

### 8.1 Inference state machine

```text
REQUESTED (public only)
 -> PRE_CURRENT
 -> COMPUTE_CURRENT
 -> HUMAN_GRANTED (live only)
 -> OP_TICKET_ISSUED
 -> INPUTS_PINNED
 -> PREPARED (output zero)
 -> BROKER_IN_FLIGHT (all attached budgets burned)
 -> TASK075_IN_FLIGHT
 -> OUTPUT_CREATED_EXCLUSIVE
 -> OUTPUT_FLUSHED
 -> OUTPUT_VALIDATED_PINNED
 -> NATIVE_COMMITTED
 -> POST_WAV_BOUND
```

Any failure after `IN_FLIGHT` is terminal or `BURNED_UNKNOWN`; the same
operation is never replayed. Absence of POST does not prove no inference.

### 8.2 Playback state machine

```text
REQUESTED (public only)
 -> POST_CURRENT
 -> QUALITY_PASS_CURRENT
 -> PLAYBACK_HUMAN_GRANTED (live only)
 -> PLAYBACK_TICKET_ISSUED
 -> WAV_PINNED
 -> PREPARED
 -> BROKER_IN_FLIGHT (Human/ticket budgets burned)
 -> TASK075_IN_FLIGHT
 -> PLAYED_COMPLETE | CANCELED | FAILED_KNOWN | BURNED_UNKNOWN
 -> TASK041_INCLUDED (only for exact admissible terminal)
```

Cancel after playback entry does not restore the ticket. A new user click
cannot replay an unresolved semantic operation with a new random ID.

### 8.3 Commit order

Inference order is fixed:

1. pin and verify PRE and all domain inputs;
2. prepare TASK-075 authorization and TASK-071 closed display;
3. obtain the unarmed TASK-072 ticket/config/channel for the exact action;
4. obtain and attach the private compute capability to TASK-072;
5. obtain and attach the live Human capability to TASK-072;
6. reacquire and revalidate all producer currentness;
7. publish/read back the output-free TASK-075 `PREPARED` reservation;
8. call the one TASK-072 broker begin transaction, which durably burns all
   attached budgets and returns the exact `IN_FLIGHT` lease;
9. publish/read back TASK-075 `IN_FLIGHT` from the broker begin readback;
10. create the output handle exclusively under the bound staging parent;
11. start one fixed child with the restricted handle list;
12. capture protocol/result and child exit;
13. flush and validate the still-open output handle;
14. publish/read back immutable TASK-075 terminal;
15. request TASK-014 POST/custody binding;
16. preserve output/evidence under the owning retention policy.

Failure after step 4 but before step 8 invokes the broker abort ABI and records
the proven-no-child terminal. Abort failure is burned unknown, never retryable.

Playback repeats the same discipline with a fresh ticket, read-only WAV handle,
TASK-014 custody readback, TASK-071
`TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2`, quality revalidation
and TASK-041 inclusion after terminal. It has no compute attachment.

## 9. Secure output and cleanup rules

- Output creation uses an operation-owned exclusive handle and no-replace
  coordinate supplied by the private TASK-014 staging binding.
- The output parent/ancestor/security snapshot is revalidated before create,
  child start, post-child validation and terminal publication.
- Existing target, including identical bytes, is collision STOP. TASK-075 does
  not adopt it as this operation's output.
- The child never receives a directory handle capable of selecting another
  output and never closes/reopens the output by path.
- File flush and directory durability failure are FAIL/completion-unknown, never
  PASS.
- Temp/output cleanup is not correctness. TASK-075 deletes nothing in v1.
  Foreign, swapped, hardlinked, reparse or ambiguous files are preserved.
- POST/quality/listening receipts bind the same physical output identity. Same
  bytes at a different identity fail.
- Raw audio and script bytes never enter JSON, logs, errors, receipts or stdout.

TASK-075 installs no Product crash-dump handler and never uploads a crash report.
The packaged worker starts under a fixed no-interactive-error/no-Product-dump
policy whose effective process flags and Product-controlled dump/error-report
directories are attested before sensitive handles are duplicated. If Windows
Error Reporting, local-dump policy, debugger attachment or another OS policy can
capture worker memory and its no-upload/private ACL disposition cannot be
attested, native entry fails closed with `DUMP_POLICY_NOT_PROVEN`. OS-owned
artifacts outside BVP custody are never searched, copied, deleted or reported by
path. Native QA must use a non-sensitive fixture to crash the worker and prove
Product dump zero, report upload zero and body/path-free public diagnostics.

## 10. Clock, cancellation and restart

Production time comes only from the TASK-071/072 fixed broker time domain. The
operation binds boot/session plus monotonic issue/deadline and bounded UTC audit.
Caller `now`, filesystem mtime, timezone or a test clock cannot extend it.

- wall-clock rollback/timezone change: no authority change;
- forward jump/suspend: fail closed when currentness cannot be proven;
- Product/broker/worker restart: every nonterminal live capability is gone;
- cancellation before `IN_FLIGHT`: effect zero and operation terminal burned;
- cancellation after entry: bounded worker stop, no replay, output preserved;
- hard timeout: bounded terminate then kill, result `BURNED_UNKNOWN` unless an
  exact native terminal and output readback already prove a known outcome;
- recovery reads exact coordinates only; it never scans for latest/current;
- a missing terminal or output does not authorize another inference/playback.

## 11. Fault and recovery matrix

| Seam | Required classification | Recovery/effect rule |
|---|---|---|
| PRE/compute/Human/ticket invalid | `REJECTED` | child/output/playback/TASK041 delta zero |
| reservation or output collision | `COLLISION_STOP` | winner/foreign artifact preserved; retry zero |
| input/ancestor/security drift | `SECURITY_STOP` | child start zero; preserve all |
| Human deny/cancel/expiry | `NOT_AUTHORIZED` | worker/output effect zero |
| broker begin burns, local IN_FLIGHT write fails | `BURNED_UNKNOWN` | worker/output zero; exact broker query only; replay zero |
| ticket/config durability failure | completion unknown or FAIL | child start zero |
| child start failure | `BURNED` | no second start under same operation |
| protocol failure before entry | `REJECTED` | inference zero |
| protocol/child failure after entry | `BURNED_UNKNOWN` | preserve output/evidence; no replay |
| output flush/readback failure | `BURNED_UNKNOWN` | POST/quality/playback zero |
| malformed WAV | `FAILED_KNOWN` | POST/quality/playback zero; preserve artifact |
| TASK-014 POST failure | completion unknown | no quality/playback; no rerender |
| quality FAIL/UNKNOWN/stale | `QUALITY_NOT_ADMITTED` | playback/TASK041 delta zero |
| playback child start/entry failure | burned/unknown | no second play under same ticket |
| playback completion receipt loss | `BURNED_UNKNOWN` | no replay; TASK041 inclusion zero |
| TASK041 inclusion mismatch | `REVIEW_NOT_INCLUDED` | TASK041 decision/effect zero |
| same exact committed query | audit `DUPLICATE` | no child/audio/playback delta |
| different terminal/body/identity | `RECEIPT_COLLISION` | STOP and preserve |

## 12. Negative matrix

Every negative separately asserts inference-child count, playback-child count,
output-file delta, TASK-014 POST delta, TASK-048 delta, TASK-041 delta and
unrelated overwrite/delete delta.

### T75-AUTH

- direct/copy/replace/pickle/deserialization/subclass/duck public PRE,
  authorization, compute, Human, ticket, POST, quality or listening object;
- module sentinel/token access and recomputed valid self-hash;
- caller-selected action, route, usage, script/Profile/model, ID, time or expiry;
- test backend/clock/hook/failure injector selected in Production;
- v1 TASK-071/072 registry receipt relabeled as Local Voice;
- preview authorization reused for full render or the reverse;
- render capability reused for playback or playback capability reused for render;
- UI request/click supplied without
  `TASK071_LOCAL_VOICE_PLAYBACK_CAPABILITY_V2`;
- TASK-071 playback capability substituted for TASK-075
  `LOCAL_VOICE_PLAYBACK_AUTHORIZATION_V1`, or the reverse;
- TASK-066 capability attached twice, returned after attach or consumed outside
  the one TASK-072 broker begin transaction;
- crash/exception between Human, compute and ticket attachment/begin steps;
- broker begin committed but TASK-075 `IN_FLIGHT` publication failed, followed
  by retry with a new ID or capability.

Expected: worker/playback/output/domain mutation zero.

### T75-CURRENTNESS

- stale/cross-project PRE, Job, script, Voice Profile, consent, rights or engine;
- wrong/different install, Product, worker, model/runtime or build;
- missing/wrong `LOCAL_VOICE_ENGINE_PACKAGE_READBACK_V1`, engine ABI, dependency
  manifest, loader policy or TASK-066 backend/context class;
- TASK-066 public-only/helper-unsealed/stale/wrong-workload evidence;
- TASK-071 wrong user/session/process/challenge/action;
- TASK-072 wrong command/profile/config/child/session;
- currentness drift between prepare, Human verification, ticket, child start,
  output validation, POST, quality or playback;
- same bytes at a different script/model/reference/output identity.

Expected: effect zero before entry; after entry authority burned and no replay.

### T75-IPC-PROCESS

- direct worker invocation without inherited channel/handles;
- shell command, argv path/model/backend selection or environment injection;
- wrong child image/signature/build/token/SID/session/parent;
- extra/missing/duplicate/grandchild-inheritable handles;
- oversized/truncated/trailing/reordered/duplicate/unknown frames;
- transcript/nonce/sequence replay or output after terminal;
- timeout/cancel/exception/crash at every child transition.

Expected: exact child effect 0/1, one-use burn, body-free status.

### T75-WAV

- output target appears before create; identical/different collision;
- output handle/path/ancestor/reparse/hardlink/DACL swap;
- child closes handle then foreign replacement appears;
- wrong RIFF/WAVE/PCM/mono/48k/16-bit/block-align/byte-rate;
- truncated header/data, duplicate conflicting chunks, odd byte count, overflow,
  header/file mismatch, unauthorized trailing bytes or oversized duration;
- flush, directory durability, pinned readback and POST publication failure;
- same WAV bytes/different inode supplied to POST/quality/playback;
- live-handle transfer failure or restart reacquire with wrong volume/file
  identity, ancestor, DACL/owner, retention revision or custody mode;
- cleanup attempt against foreign/unknown output.

Expected: POST/quality/playback/TASK041 zero; unrelated delete/overwrite zero.

### T75-QUALITY-LISTENING

- public TASK-048 record/self-hash without trusted analyzer readback;
- quality FAIL, UNKNOWN, stale, conflicting or wrong analyzer/policy/calibration;
- playback before TASK-014 POST or TASK-048 PASS;
- wrong/cross operation WAV/range/device policy;
- double/concurrent click, loop/replay/seek/speed/alternate-device injection;
- playback child crash/cancel/receipt loss then retry;
- forged/receipt-only/external-player-only completion;
- TASK041 inclusion with missing/wrong intent/source/range/receipt;
- playback complete treated as Human ACCEPT or Asset/placement authority.

Expected: playback exact 0/1, TASK041 decision/Asset/Timeline delta zero.

### T75-PRIVACY-RESOURCE

- script/audio/model/path/username/SID/device/OS error in public status/log/stdout;
- control/NUL/oversized script metadata or reason-code/body echo;
- oversized protocol frame/transcript/progress count;
- output quota, memory, GPU, runtime or duration ceiling breach;
- malformed raw native exception and binary stdout/stderr;
- Product crash dump/heap report created, report upload attempted, dump/error
  directory ACL unproven, debugger/OS policy currentness unknown;
- fixture/native/installed status promoted beyond its evidence level.

Expected: stable body-free rejection, service remains available, sensitive raw
bytes absent from config/event/receipt/log/stdout.

## 13. Product UX contract

TASK-075 supplies read-only Japanese states to the owning Product surface:

- `音声生成を準備しています`
- `確認が必要です`
- `音声を生成しています`
- `音声を確認しています`
- `再生できます`
- `音声を再生しています`
- `完了しました`
- `安全のため停止しました`
- `状態を確認できないため、同じ操作は再実行できません`

The UI never shows a path, handle, SID/account, ticket, nonce, backend selector,
model path, receipt body or OS error. Cancel is always explicit. An unresolved
operation offers status/recovery guidance, not blind retry. `音声を聴く` is
enabled only after exact POST and quality PASS currentness. Listening completion
does not select a TASK-041 review decision.

## 14. Verification plan

### Static and focused

- strict schema/mirror identity and canonical serialization;
- exhaustive Local Voice action/profile mapping;
- deterministic semantic operation keys and no-random-ID replay;
- fixture-only V/L/E positive and negative vectors;
- parent/child frame parser and closed handle-role validation;
- WAV parser property/boundary tests with exact size ceilings;
- state/fault/crash matrix and one-use concurrency tests;
- broker atomic-begin/partial-commit reconciliation and all-budget burn tests;
- fixed synthesis-engine ABI/package/dependency/loader rejection tests;
- live duplicate and restart identity-reacquisition WAV custody tests;
- TASK-014/TASK-066/TASK-071/TASK-072/TASK-048/TASK-041 fixture adapters;
- secret/path/body scan, diff/scope and compile checks;
- relevant existing TASK-014/TASK-041/TASK-048/TASK-066 regression.

### Windows native

- exact packaged worker image/build/protocol readback;
- restricted inherited handle list and grandchild denial;
- wrong process/user/session/build/channel rejection;
- actual local model/runtime and compute route readback;
- one real rights/consent-approved non-sensitive test sentence only under a
  separate native/private-voice Human Gate;
- PCM WAV format/length/duration/checksum and still-open identity readback;
- concurrent two-process inference and playback each exact one;
- cancel, timeout, terminate/kill and crash at every seam;
- non-sensitive forced crash proving Product dump zero, report upload zero,
  private dump-policy attestation and body/path-free diagnostics;
- suspend/restart/time-change expiry behavior;
- NTFS ancestor/reparse/hardlink/output race matrix;
- real default-device playback completion and cancel observation;
- public UI/log/stdout path/body/voice/secret leakage zero.

Until that gate is explicitly opened, native inference, private voice processing
and playback remain `NOT_EXECUTED / NOT_CONFIRMED`; fixture tests cannot change
that status.

### Package/install

- clean packaged launch without Codex, ChatGPT, OpenAI key or internet;
- exact worker/model/runtime/protocol manifests and installed hashes;
- no model/runtime download or Provider fallback;
- repair/upgrade invalidates live tickets and preserves compatible immutable
  audit evidence;
- multiple installs cannot cross-redeem handles/tickets/outputs;
- installer/build-spec changes occur only through their owners;
- uninstall/cleanup is not a TASK-075 effect.

## 15. Acceptance criteria

Design acceptance requires:

1. Owner, responsibility, exact Allowed Files and prohibited paths are fixed.
2. The artifact graph is one-way and matches PRE -> compute/Human/ticket ->
   inference -> POST -> quality -> playback -> review.
3. Current public TASK-014/TASK-066/TASK-041/TASK-048 records are evidence only
   and cannot mint execution/listening authority.
4. TASK-071/072 Local Voice profiles are explicit versioned cross-owner Gates;
   their v1 registries are not silently extended.
5. Production capability exists only as exact live broker/OS handle state.
6. Inference and playback each have a stable semantic key, invocation budget
   one and burn on authenticated entry success or exception.
7. Script/model/reference/output use pinned handles; no path-based reopen is an
   authority proof.
8. Output is exclusive, no-replace, flushed, strictly validated and read back
   from the same handle; same bytes/different identity fails.
9. Only TASK-014 may issue POST and only TASK-048 may issue quality PASS.
10. Playback requires exact current POST plus quality PASS and cannot imply a
    TASK-041 Human decision.
11. Crash/unknown state never permits blind replay or cleanup-based recovery.
12. Public errors/status/receipts are body/path/identity-secret free.
13. V/L/E fixtures are early and useful but never Production/native authority.
14. Focused, fault, packaging and native QA matrices are executable and assert
    unrelated overwrite/delete zero.
15. TASK-072 atomically begins/burns attached TASK-066/TASK-071/TASK-072
    authorities before output creation, with exact partial-commit recovery.
16. TASK-014 supplies the fixed engine package readback and exact WAV custody;
    TASK-075 cannot invent a backend or use path/equal-bytes reacquisition.
17. Worker crash-report policy is attested before sensitive handles; Product
    dump/upload is zero and unproven OS policy fails closed.
18. Independent Critic returns `Critical=0 / High=0` and Judge returns `PASS`.

## 16. Completion receipt template

This section is administrative only until the complete technical payload is
frozen and independently reviewed.

```text
task: TASK-075
design_identity: TASK075-PTD-LOCAL-VOICE-EXECUTION-LISTENING-V1
base: origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38
allowed_files: docs/ai-team/tasks/TASK-075/complete-design-packet.md
review_target_sha256: 0577033ED4D8B132D490E662D324D49E04BF7870037BEDBAE79A869298670443
critic: C0/H0/M0/L0
judge: PASS
design_frozen: true
administrative_receipt_appended_after_review: true
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
release_deploy_production_effect: 0
authority_created: false
```

The completed design creates no implementation, native, Human, model/runtime,
Release, Deploy or Production authority. Any technical content change after a
PASS receipt requires a new exact hash and independent review.
