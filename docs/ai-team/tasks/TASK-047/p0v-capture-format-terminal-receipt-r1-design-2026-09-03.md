# TASK-047 P0V capture-format and terminal-receipt R1 design

## Status

- Atomic Unit: `TASK-047 / P-OBS-1B-CAPTURE-TRUTH-R1`.
- DEV profile: `DEV-4 FOUNDATION CRITICAL`.
- Base: `origin/main@4e150c17f3cd2fe9398d75518473dc8428fae322`.
- State: design only; implementation/native recording authority is false.
- Responsibility: close Q1 between authenticated OBS callback frames and a
  canonical private `PCM_S24LE/48000/mono` capture Asset receipt.

## Existing implementation truth

`native/task047_obs_voice_capture/controller/BaiVoiceCaptureController.cs`
currently creates `WaveFloatWriter(partialPath, planes, 48000)`. The writer
emits RIFF format tag 3, callback plane count and 32-bit float samples. The final
receipt records byte/hash and transport counters but not an authoritative WAV
format, actual source sample rate, channel selection/downmix, resampler/sample
map, final acoustic facts or full capture-chain currentness.

The live Peak/RMS meter and gain receipt observe float samples. They do not
prove the final file format or mint TASK-048 quality PASS.

## MUST requirements

### Native input and callback

- Observe and bind actual OBS source format, sample rate, planes/layout, callback
  frame count, source timestamps and selected-source private identity.
- The real-time callback remains bounded and non-blocking. It performs no file
  I/O, encryption, resampling, bit-depth conversion, analysis or formatted log.
- Every callback packet is authenticated and sequence checked. Overflow,
  missing packet, non-finite sample, disconnect, source/graph drift and process
  replacement are explicit facts.
- Only one Owner-selected isolated microphone is in R1. Mixed, non-mic and
  unknown track classification cannot become canonical training material.

### Canonicalization worker

- The private non-real-time worker consumes exact authenticated frame ranges.
- Output is RIFF/WAVE signed packed PCM24 little-endian, 48,000 Hz, one channel.
- Native float32 is never labeled PCM24. Input and output staged objects remain
  distinct until separate TASK-003 adoption/readback.
- Downmix requires an exact channel-selection or phase-safe downmix receipt.
- Resampling requires actual source-rate evidence and a pinned library/version,
  license, configuration, filter, delay, tail, dither/quantization and rational
  cumulative sample-map receipt.
- Saturation, NaN/Inf, rounding, delay/tail and output sample-count policy are
  deterministic and covered by known vectors.
- Publication is atomic, no-clobber and idempotent. Partial files are hidden and
  never promoted. Raw private recovery bytes remain immutable.

### Meter and recording screen

- 0 dBFS is the digital upper bound. Target, warning and true-clip thresholds
  are separate values supplied only by a current TASK-048 policy producer,
  which is presently `NOT_BOUND`; they are never constants disguised as quality
  truth.
- Show instantaneous Peak/RMS, peak hold, session maximum, clip count,
  non-finite count, silence/dropout state and transport loss state.
- Identify the measurement point: callback pre-filter or selected OBS post-filter.
- Bind current source, device, filter graph, gain, limiter, mute, mixer, sample
  format/rate/layout and OBS process/build. Any drift becomes `UNKNOWN` or
  terminal failure, not silent continuation.
- UI states are visible and distinct: `録音準備`, `録音中`, `一時停止中`,
  `保存処理中`, `品質確認待ち`, `復旧が必要`, `失敗`.
- Meter display thresholds come from a current pre-capture TASK-048 policy
  revision that depends on no Q1 audio. Missing policy shows observation values
  with `適正判定 未確定`; it never blocks emergency stop or invents thresholds.

## Exact receipt chain

Q1 uses separate body-free receipts; one hash cannot stand for all truths.

1. `CaptureSourceCurrentnessReceiptV1`: selected source/device/OBS build/process,
   graph/filter/gain/mute/mixer identity, measurement point and observed time.
2. `CaptureTransportIntegrityReceiptV2` (TASK-047 owner): operation/session/
   attempt, exact callback-to-capture-worker IPC packet range, frame/sample
   counts, source timestamps, gaps/overruns/reconnects, non-finite observations,
   capture-transport HMAC key epoch and verification state. It contains no key
   or audio body and grants no durable Product-job or inference-frame authority.
3. `NativeCaptureTerminalReceiptV1`: exact stop cause, start/finish, pause ranges,
   terminal write-close/readback, raw staged-object identity/hash and incomplete
   state.
4. One `PrivateCaptureCustodyReceiptV1` for the raw staged object (future
   canonical secure-custody owner, consumed by TASK-047): exactly one object role,
   logical staged-object/revision identity, encrypted-at-rest state,
   key-availability state, retention class, revoke/delete-policy revision,
   publication/readback and currentness. It carries no key, path or body.
5. `CanonicalFormatConversionReceiptV1`: consumes the exact custodied raw staged
   object and binds actual native format/rate/layout, selection/downmix policy,
   resampler/dither/sample map, output canonical-format staged-object
   revision/hash, exact `PCM_S24LE/48000/mono`, sample count and duration.
6. A second `PrivateCaptureCustodyReceiptV1` for the canonical-format staged
   object: exactly one `CANONICAL_FORMAT` role and a distinct object, operation,
   revision and receipt digest. A combined raw+canonical receipt, identity reuse
   or cross-role replay is invalid. The custody owner is currently
   `PRIVATE_MEDIA_CUSTODY_OWNER_NOT_ALLOCATED`; this is a hard Q1 START blocker,
   not authority for TASK-047 to invent an owner, encryption system or store.
7. A future exact TASK-003-owned capture-Asset sink/registration/adoption ABI
   adopts the separately custodied raw and canonical staged objects and returns
   canonical Asset readback. It is currently
   `TASK003_CAPTURE_ASSET_ADOPTION_READBACK_NOT_BOUND`; TASK-047 cannot mint,
   store or self-attest canonical Asset truth.
8. `CaptureChainTerminalCandidateV1`: hashes the exact receipts above, including
   TASK-003 adoption/readback, and binds the expected TASK-043 predecessor head.
   It contains no claim that it is current.
9. TASK-043 CAS-selects that exact candidate and returns a separate
   `TASK043_CAPTURE_CURRENT_TERMINAL_READBACK_V1` over the new Project/Job head.
10. `CaptureChainTerminalReceiptV1` is a body-free consumer projection over the
    candidate plus that post-CAS readback and yields `BOUND_VERIFIED`, `NOT_BOUND`,
    `MISMATCH`, `STALE`, `REVOKED` or `UNKNOWN`. TASK-048 requires both the exact
    candidate and separate current-terminal readback; only `BOUND_VERIFIED` is
    consumable.

Every receipt binds Project, recording session, segment attempt, operation,
idempotency key, canonical Owner-subject and closed-purpose capture-Consent
snapshot, producer code/runtime version, created/observed time and its own
canonical digest. Initial capture does not
require a future local VoiceProfile and cannot mint one. Public projections
contain no path, filename, device identifier, audio body, secret or voice
fingerprint.

### Receipt ABI and trusted currentness

The future TASK-047 receipt implementation uses closed, version-discriminated
records. Every record has the exact common envelope
`record_type`, `schema_version`, `project_id`, `recording_session_id`,
`segment_attempt_id`, `operation_id`, `idempotency_key`,
`owner_subject_binding_sha256`, `consent_evaluation_sha256`,
`producer_code_sha256`, `runtime_sha256`, `trusted_time_binding_sha256`,
`capture_job_id`, `capture_job_revision_sha256`,
`capture_job_predecessor_readback_sha256`, `created_at`, `observed_at`, `fresh_until`,
`predecessor_receipt_sha256` and `receipt_sha256`, plus only the
receipt-specific fields frozen in the schema. JSON member order is not semantic.
The digest preimage explicitly excludes `receipt_sha256`, then uses UTF-8
canonical JSON with recursively sorted keys, no insignificant whitespace,
duplicate keys, NaN/Infinity or unknown fields, and a record-type/version domain
separator; the resulting lowercase SHA-256 is appended as `receipt_sha256` and
verified by recomputing the same excluded-field preimage. Enums are closed to the
values named by each schema; chain state is exactly `BOUND_VERIFIED`, `NOT_BOUND`,
`MISMATCH`, `STALE`, `REVOKED` or `UNKNOWN`. Reason codes are closed/versioned,
sorted and deduplicated. `predecessor_receipt_sha256` is null only for the first
`CaptureSourceCurrentnessReceiptV1`, whose domain includes `INITIAL`; every later
record must bind the exact preceding receipt digest.

This envelope is a candidate ABI family, not a landed exact producer ABI. The
receipt-specific required fields, closed enums, nullability and cross-field
matrix must be frozen byte-exactly in the schema/mirror/runtime parser and pass a
fresh DEV-4 review before implementation START; this document does not allow a
producer to invent or omit them.

`OwnerSubjectBindingV1` is presently
`OWNER_SUBJECT_BINDING_OWNER_NOT_ALLOCATED`. Its future canonical owner must bind
an opaque subject ref/digest, revision and predecessor/currentness. A separate
versioned Consent evaluation must cross-bind that identical subject/revision and
the closed purpose `OWNER_VOICE_CAPTURE`, decision=`ALLOW`, policy revision,
evaluation time, expiry and revocation-currentness evidence. Every Q1 receipt
binds both exact records. Capture Consent grants capture and its explicitly bound
private-custody operation only; it grants neither
`OWNER_VOICE_DATASET_ADOPTION` nor `OWNER_VOICE_MODEL_TRAINING`. Those later
purposes require separate current evaluations that cross-bind the same subject
and exact adopted Asset/snapshot lineage. Arbitrary digests, wrong-subject or
wrong-purpose Consent, non-ALLOW decisions, policy-revision mismatch,
expired/stale/revoked evaluations, stale/revoked subject revisions and
placeholder VoiceProfile credentials fail closed. Initial capture consumes these
bindings but still does not require or mint a local VoiceProfile.

The current canonical TASK-047 `task.md` names a P-VS-1A
`VoiceProfileRevision` as a P-OBS-1 START dependency. Replacing that dependency
with the OwnerSubject plus closed-purpose capture-Consent boundary requires an
accepted canonical TASK-047 amendment; until then
`TASK047_OWNER_SUBJECT_START_AMENDMENT_NOT_ACCEPTED` blocks implementation START.
This design document does not silently amend the canonical Task.

The required TASK-043 recovery producer is currently
`TASK043_CAPTURE_JOB_CURRENTNESS_READBACK_NOT_BOUND`. It alone owns the durable
capture Job/head and returns exact current Project, `capture_job_id`, attempt,
revision and selected terminal coordinates. TASK-047 may produce a candidate
attempt/terminal receipt but cannot select, rewrite or self-attest currentness.
Pre-terminal receipts and the terminal candidate bind only the fresh predecessor
readback. The separate post-CAS current-terminal readback cannot appear in its
own candidate digest.

`TrustedCaptureTimeBindingV1` is presently `TRUSTED_TIME_BINDING_NOT_BOUND`. Its
future canonical owner must bind a trusted-time domain/receipt digest, boot and
session digests, monotonic revision/counter, wall-clock observation,
`fresh_until`, predecessor and rollback/replay decision. Wall clock alone is not
authority. Counter/predecessor regression, boot/session substitution, expired
freshness, missing trusted-time receipt or rollback uncertainty yields `UNKNOWN`
or `STALE`, never current Consent, retention, key-availability or custody truth.
The binding contains no raw machine identifier, secret or private path.
Every receipt must satisfy `created_at <= observed_at < fresh_until`, use the
same trusted-time domain as its binding, and stay within that policy's closed
maximum future-skew interval. Equality at expiry, cross-domain time, negative or
excessive future skew is stale/unknown rather than current.

This capture-transport ABI is distinct from narration execution. TASK-076 later
owns only durable Product Job candidates/validation and child/process/Job custody
after TASK-071/072 authorization; TASK-068 owns immutable candidate publication/
readback and TASK-043 alone owns CAS selection/current readback. TASK-076 owns no
audio semantics and no terminal CAS.
TASK-075 owns the authenticated narration-worker channel and PCM24 frame grammar,
while TASK-014 owns the sink, RIFF/WAV publication and POST. These ABIs use
different operation namespaces, key epochs and receipts; none may satisfy or
alias another. TASK-076 is not a START dependency for Q1 capture.

## Acoustic observations boundary

The terminal receipt reports exact Peak/RMS/clip/non-finite/session-max and
sequence/drop facts for its stated measurement point so the saved bytes can be
cross-checked. It does not decide SNR, noise floor, HVAC preference,
other-speaker/BGM absence, speech ratio or Dataset eligibility; TASK-048 owns
those policy decisions and must measure the exact canonical Asset/ranges.

Known synthetic validation includes exact dBFS tones, digital silence,
non-finite samples, clipping and deterministic whisper/normal/shout-shaped
signals. A later Human native QA uses real whisper/normal/shout without exposing
private audio in Evidence.

## Recovery and fault behavior

- Stop is single-terminal and idempotent. Repeated stop returns the same receipt;
  a different payload conflicts.
- Crash after partial write leaves a quarantined recovery record, never a final
  Asset. Restart begins from one fresh TASK-043 capture Job/head readback and
  reconciles the exact session/attempt journal, raw file, canonical file and
  receipt hashes. A lost publish/CAS reply never authorizes a new attempt or a
  second terminal; `UNKNOWN` remains until TASK-043 selects or rejects the exact
  candidate and returns fresh currentness.
- Source/OBS process replacement, graph drift, device loss, disk floor, lock,
  HMAC failure, sample-map mismatch, write/readback mismatch and durability
  failure stop or quarantine the affected attempt.
- Pause/resume binds drained packet and source/canonical sample boundaries. It
  cannot conceal packet loss or splice discontinuity.
- `UNKNOWN` is preserved until new authoritative evidence resolves it. Cleanup
  does not delete unknown private media automatically.

## Prohibited

- hard-coded 48 kHz used as observed source truth;
- float32 WAVE format 3 described as PCM24;
- implicit channel 0 selection or unproved multichannel downmix;
- meter target/warning/clip policy invented by TASK-047;
- final quality PASS, Dataset adoption, Training, model load or inference;
- multiple OBS/controller instances for the same operation;
- in-place raw overwrite, lossy intermediate, visible partial output;
- public absolute path, device/voice identifier, transcript/audio body, HMAC key
  or other secret.

## Negative and fault matrix

- unsupported/unknown input format, rate or layout;
- declared/measured format mismatch and header/body mismatch;
- 44.1/48/96 kHz vectors, one/multiple planes, phase-cancelling stereo;
- NaN, positive/negative infinity, out-of-range float, rounding and saturation;
- resampler delay/tail/remainder and rational sample-map tamper;
- packet gap, duplicate, reorder, overrun, reconnect and wrong HMAC epoch;
- source/filter/gain/limiter/mute/mixer/OBS build or process drift;
- stop/pause race, duplicate stop, lost reply, crash at each publish boundary;
- raw/canonical identity collision, existing destination and partial visibility;
- missing TASK-003 adoption/readback, staged object presented as canonical Asset,
  or TASK-047 minting canonical Asset truth;
- missing/stale/revoked encrypted custody, unavailable key, retention/delete
  policy mismatch or custody receipt that aliases a path/body;
- missing/expired trusted-time binding, clock rollback, boot/session substitution,
  predecessor/counter regression or stale Consent/custody evaluation;
- WAV wrong media type, format tag, rate, channel, bit depth or sample count;
- final hash/durability/readback mismatch and replayed terminal receipt;
- missing/stale TASK-043 capture Job/head, wrong attempt/revision, unselected
  terminal candidate, lost reply, concurrent head change or duplicate terminal;
- arbitrary/stale/revoked OwnerSubject binding, Consent subject/revision mismatch,
  wrong-purpose Consent, capture Consent reused for Dataset adoption/training,
  non-ALLOW decision, policy-revision mismatch, expiry/revocation-currentness
  failure, or placeholder local VoiceProfile credential;
- path/body/secret leakage and unknown fields/reason codes;
- meter vectors for silence, -60/-24/-12/-1/0 dBFS, clipping and non-finite input.

## Future implementation allocation candidate

Implementation remains unallocated. After design acceptance and overlap audit, a
bounded start receipt may allow only the paths below. START additionally requires
allocated exact producers for `OwnerSubjectBindingV1`,
the closed-purpose `OWNER_VOICE_CAPTURE` Consent evaluation and the accepted
canonical TASK-047 OwnerSubject START amendment,
`TrustedCaptureTimeBindingV1`, private raw/canonical custody,
`TASK043_CAPTURE_CURRENT_TERMINAL_READBACK_V1` and TASK-003 capture-Asset
adoption/readback; any missing producer keeps implementation `NOT_BOUND`.

- `native/task047_obs_voice_capture/controller/BaiVoiceCaptureController.cs`;
- `native/task047_obs_voice_capture/VERSION`;
- `native/task047_obs_voice_capture/CMakeLists.txt`;
- `native/task047_obs_voice_capture/package-manifest.schema.json`;
- `native/task047_obs_voice_capture/scripts/generate-manifest.ps1`;
- `native/task047_obs_voice_capture/include/bai_obs_capture/capture_protocol.hpp`;
- `native/task047_obs_voice_capture/include/bai_obs_capture/capture_core.hpp`;
- `native/task047_obs_voice_capture/include/bai_obs_capture/ipc_client.hpp`;
- `native/task047_obs_voice_capture/src/obs_plugin.cpp`;
- `native/task047_obs_voice_capture/src/capture_core.cpp`;
- `native/task047_obs_voice_capture/src/ipc_client.cpp`;
- `native/task047_obs_voice_capture/tests/capture_core_tests.cpp`;
- `native/task047_obs_voice_capture/tests/security_tests.cpp`;
- `native/task047_obs_voice_capture/tests/obs-stubs/obs-module.h`;
- `tests/test_task047_obs_runtime_source_contract.py`;
- `src/ai_video_production/task047_capture_receipt_chain.py`;
- `schemas/task047-capture-receipt-chain.schema.json`;
- `src/ai_video_production/schema_resources/task047-capture-receipt-chain.schema.json`;
- `tests/test_task047_capture_receipt_chain.py`.

Installer/package/shared UI/current-state/roadmap/CHANGELOG changes are excluded.
The bounded unit must advance the wire protocol from V1 to V2 and one package
version coherently across `VERSION`, CMake compile identity and
generated-manifest validation; old V1 frames/receipts are never relabeled as
`CaptureTransportIntegrityReceiptV2`. The OBS stub must expose only the source-format
facts needed by synthetic tests and cannot become production evidence.
Native Owner recording, private-file mutation and actual OBS operation remain a
separate Human Gate even after source implementation.

## Acceptance

- source rate/layout is observed, not assumed;
- canonical output is byte-proven PCM24/48k/mono with exact sample map;
- raw, canonical and receipt identities are separate and current;
- final acoustic/sequence/chain facts are complete but do not claim TASK-048
  quality PASS;
- known synthetic format/dBFS/packet/fault vectors pass;
- static/focused/TASK-047 targeted regression passes;
- independent Critic, Tester and Judge report zero Critical/High;
- native/private/production effects remain `NOT_EXECUTED` until their Human Gate.
