# TASK-048 P-QC-P0V-FINISH-1 native environment A/B runbook candidate

## Status and authority

- Date: `2026-09-05`
- State: `DESIGN_ONLY / NOT_EXECUTED / NOT_CONFIRMED`
- Scope: future OBS Owner-voice air-conditioner OFF/ON quality Evidence and a
  separate speech-continuous training WAV candidate.
- This document does not authorize OBS recording, private audio access, native
  analyzer execution, WAV publication, Dataset adoption, model training,
  Release, Deploy, or Production use.
- The current implementation remains fixture-only. Its receipts have
  `authority_created=false`, `production_eligible=false`, and
  `external_effect_count=0`.

The future native operation MUST have an explicit Owner/Human Gate, an exact
TASK-047 finalized recording readback, and a private output-sink authority. A
fixture receipt, file path, live meter, or this runbook cannot substitute for
those authorities.

## Non-destructive invariants

1. Every OBS source WAV is an immutable parent. Never overwrite, move, rename,
   truncate, normalize, filter, or delete it.
2. All reads use one pinned regular-file, single-link, no-reparse identity and
   bind the bytes parsed and measured to that same open snapshot.
3. Air-conditioner OFF and ON captures use distinct session IDs but the exact
   same current microphone, filter chain, gain, transport format, sample rate,
   channel count, analyzer build, and quality policy.
4. A processed speech-continuous WAV is a new operation-owned derivative. It
   is never the only recovery copy.
5. No partial or failed output becomes current. Unknown state is preserved for
   Human review; it is not repaired, overwritten, or deleted automatically.

## Windows output-root preflight (mandatory)

This is a pre-effect STOP rule for every future build, QA, analyzer, capture,
fixture, temporary file, runtime-state, log, derivative-output and Evidence
write. It does not grant native authority and an Owner/Human approval cannot
waive it.

1. Before creating a process or file, resolve each destination to an absolute
   physical path. Stop if the destination or its task-owned top-level directory
   is a drive root or a direct child of one (for example `C:\\BVP-QA-x`,
   `D:\\build` or `E:\\runtime-state`).
2. The private target and derivative output must be contained below the exact
   authorized private sink root and bind the active Task, operation ID and
   expected-absent identity. Existing foreign or unknown-ownership paths stop
   before effect; they are never reused, overwritten or cleaned up.
3. Temporary material uses a unique, operation-owned root allocated beneath the
   operating system temporary root. Public-safe Evidence uses only
   `C:\\home\\baisound\\evidence\\bai-video-production\\TASK-048\\<unit>\\<run-id>\\`.
   Private body, audio, machine path and secret material remain outside public
   Evidence under the applicable custody/Consent contract.
4. `C:\\BVP-QA-471-*` is preserved historical QA material. This operation must
   not read for reuse, write, append, overwrite, delete or clean it.
5. Record the resolved output/temp/runtime/Evidence roots and intentional
   residuals in the private operation receipt and path-free public projection.
   Cleanup is eligible only for an artifact this same operation created after
   its physical identity is revalidated.

## Private input manifest

The runner receives a sealed private manifest. It is canonical UTF-8 JSON with
closed fields, duplicate-key rejection, finite numbers only, bounded strings,
arrays, depth, and total bytes. Absolute paths may exist only in the private
operation envelope and MUST NOT enter a public receipt or error.

### Operation binding

- `operation_id`: fresh opaque one-use identifier.
- `project_id`, `project_manifest_sha256`, `installed_session_sha256`.
- `operation_plan_sha256`, `runner_build_sha256`.
- `analyzer_profile_sha256`, `quality_policy_sha256`.
- `issued_at_utc`, `expires_at_utc`, trusted user/session/build binding.
- `private_manifest_bytes_sha256` over the full canonical private manifest;
  separately, `path_free_projection_digest` covers the canonical projection
  with path values replaced by private coordinate tokens. The two digests have
  distinct Evidence and public-receipt uses.

### Capture binding, once for OFF and once for ON

- condition: exactly `AIR_CONDITIONER_OFF` or `AIR_CONDITIONER_ON`.
- distinct `session_id` and exact TASK-047 terminal receipt identity/hash.
- TASK-047 has two immutable staging lineages: the callback parent
  (`OBS_CALLBACK_AUDIO_STAGING`) and the canonical processing parent
  (`CANONICAL_48K_S24_MONO_STAGING`). Bind both private receipt references,
  revisions, digests, physical identities, byte sizes, sample counts,
  write-close proof, and currentness facts; never call either lineage a public
  or interchangeable “raw source”.
- matching capture and room-tone generation digest.
- `PCM_S24LE`, `48000 Hz`, mono canonical-input proof. Raw OBS float32 or an
  unproved multichannel source is inadmissible.
- microphone, filter-chain, gain, and transport-format digests.
- room-tone range plus whisper, normal, and shout speech ranges. Ranges are
  half-open sample coordinates and MUST stay within the pinned source.
- exact ordered cells are `[ROOM_TONE, WHISPER, NORMAL, SHOUT]`; every range is
  nonempty, bounded, disjoint, strictly increasing, and taken from the same
  finalized canonical WAV snapshot. OFF/ON counterpart cells use equal sample
  counts and the same analysis-window policy. Bind private script, microphone
  distance/setup, range-set, and per-cell VAD receipt digests. No sample may be
  reused between cells.

### Speech-continuous binding

- strict RIFF/WAVE decode receipt and decoder build digest.
- exact source content and identity hashes matching the capture snapshot.
- exact contiguous VAD intervals covering sample `0` through the complete
  input sample count, each with class, confidence, range, and Evidence digest.
- current format policy and continuity policy receipts.
- current quality-measurement receipt digest.
- private target namespace reservation and expected-absent state.

## Capture procedure candidate

The following is an operator protocol, not an automated capture authorization.

1. Freeze the operation manifest and verify the selected OBS source, consent,
   user/session, OBS process/build, microphone, filters, gain, and transport.
2. Record the actual acquisition order in private Evidence. Public projection
   is always canonical OFF then ON; it must not imply an acquisition order.
3. For each condition, wait for the environment to stabilize without changing
   mic position, input gain, filters, room layout, or transport.
4. Capture a dedicated room-tone range, then whisper, normal, and shout ranges
   using the same script and intended microphone distance. Speech text remains
   private and is never copied to the public receipt.
5. Stop and finalize through TASK-047. Do not measure a still-open WAV or rely
   on a single stable-size observation.
6. Reopen through the trusted reader, verify exact terminal receipt, complete
   RIFF/WAVE structure, content identity, ancestor/currentness, and capture /
   room-tone generation before any analyzer call.
7. If either condition cannot satisfy the same-chain comparison, emit UNKNOWN
   Evidence with effect zero. Do not recapture automatically.

## Deterministic measurement candidate

All calculations operate on normalized finite PCM samples from the same pinned
snapshot. Decode S24LE as integer `q ∈ [-8388608, 8388607]` and normalize
`x=q/8388608.0`; use the manifest-bound clip threshold and analyzer version.
Accumulate sums/counts exactly, convert to binary64 once for `sqrt`/`log10`,
and serialize measurements with the bound decimal round-half-even policy and
algorithm digest. Use `L=10^(-300/20)` as the finite amplitude floor.

For every OFF/ON x whisper/normal/shout cell record:

- `peak_dbfs = 20*log10(max(max(abs(x)), L))`;
- `rms_dbfs = 20*log10(max(sqrt(sum(x*x)/N), L))` over the exact admitted
  window;
- clipped count where `abs(q) >= clip_threshold_q24` (inclusive), with the
  integer threshold frozen in the profile;
- non-finite sample count before any aggregate calculation;
- absolute DC offset `abs(sum(x)/N)` in normalized full-scale units;
- dropout count using the profile-bound definition;
- speech ratio as VAD-class `SPEECH` sample count divided by the total cell
  sample count; `UNCERTAIN` and `NON_SPEECH` are never numerator samples;
- room-tone noise floor dBFS from that condition's own room-tone range;
- `SNR=10*log10(max(P_segment-P_noise,L^2)/max(P_noise,L^2))`, where each
  power is the exact mean square of the pinned window; if segment power is no
  greater than noise power, emit UNKNOWN rather than fabricate a value;
- `snr_approximate=true` whenever speech/noise separation is VAD-derived rather
  than independently calibrated;
- stationary low/mid/high-band noise levels in dBFS, with filter coefficients,
  windowing, and backend digest bound in the manifest.

Zero-energy inputs never serialize `-Infinity`. They produce a stable UNKNOWN
reason. NaN, Infinity, invalid positive dBFS levels, missing peak/RMS, or a
source/identity mismatch invalidate the cell.

Closed policy edges are:

- SNR below `15.0 dB`: REJECT; `15.0 <= SNR < 20.0 dB`: REVIEW; exact
  `20.0 dB` is eligible when all other axes pass.
- approximate SNR: REVIEW even when its numeric value is otherwise eligible.
- speech ratio below `0.5`: REJECT; exact `0.5` is eligible.
- absolute DC offset above `0.01`: REJECT; exact `0.01` is eligible.
- any non-finite sample, clip, or dropout: REJECT.

The result reports OFF-to-ON deltas in `dB` (absolute levels remain `dBFS`). It
never claims dBA/SPL and
never recommends air conditioner ON or OFF automatically. Denoise improvement
and voice damage are separate axes; noise reduction cannot override detected
distortion or overprocessing.

## Speech-continuous edit plan

The edit planner consumes Evidence; it does not rediscover speech from file
paths.

1. Preserve every SPEECH interval and every UNCERTAIN interval.
2. Preserve NON_SPEECH shorter than `48000` samples. This includes every short
   natural pause at or below `24000` samples.
3. A NON_SPEECH interval is removable only when its confidence is at least
   `0.95` and its duration is at least `48000` samples.
4. Extend each speech range by `2400` pre-speech samples, `3600` post-speech
   samples, and `2400` hangover samples, clipped to the source bounds. Merge
   overlapping retained ranges.
5. The complement of the merged retained ranges is the exact removed map.
   All-silence, insufficient-speech, gaps/overlap in VAD coverage, or a retained
   island shorter than the boundary fade stops before the runner.
6. Join each pair of retained ranges with an exact `240`-sample equal-power
   crossfade. For `j=0..239`, bind a private coefficient-table digest for
   `theta=j*pi/(2*239)`, `gL=cos(theta)`, `gR=sin(theta)`; endpoints are left
   only then right only. Quantize `y*8388608` with deterministic
   round-half-away-from-zero to S24LE; any out-of-range value is a failure,
   not silent saturation. Bind table, rounding, and overflow evidence.
7. Independently verify each joined boundary, consonant attack, and speech tail.
   One boundary Evidence digest is required per join.

There is no zero-gap compression, lossy encoding, resampling, implicit downmix,
denoising, limiting, normalization, or arbitrary filter in this operation.

## Capacity accounting

Capacity is an exact consequence of retained sample ranges, not a quality
objective.

- `input_pcm_payload_bytes = input_sample_count * 3`.
- `crossfade_overlap_samples = boundary_count * 240`.
- `output_sample_count = retained_sample_count - crossfade_overlap_samples`.
- `output_pcm_payload_bytes = output_sample_count * 3`.
- `size_reduction_bytes = (removed_sample_count +
  crossfade_overlap_samples) * 3`.

These values describe mono PCM payload only. RIFF header/chunk bytes are
reported separately in private readback; no container-compression claim is
allowed. Continuous speech with no removed range and no boundary has exactly
zero reduction.

## Publication and exact readback

Future native publication is a separate private sink operation:

1. Reserve an operation-specific target under a pinned, attested ancestor and
   durably publish `PREPARED` with no-replace semantics.
2. Create an exclusive operation-owned temp and retain its open physical
   identity through write and file flush; CAS-publish `WRITTEN` with that
   temp identity and expected bytes.
3. Reconfirm source/current policy, target expected-absent state, target
   ancestor, and operation lease immediately before no-replace publish.
4. Publish the target, then durably CAS-publish `PUBLISHED` recording the
   target identity. A target appearance or journal CAS collision is STOP.
5. Flush the directory; only then durably CAS `DURABLE`.
6. Reopen nofollow and verify exact output bytes/hash, physical identity,
   format, sample count, range map, boundary count/evidence, and durability;
   finally CAS `VERIFIED`.

Cleanup may remove only the exact temp identity created by this operation.
After target publish but before the `PUBLISHED` CAS, a crash may leave the
journal at `WRITTEN` while the target exists. If and only if the target
identity and bytes exactly match the `WRITTEN`-bound expected values, the same
private recovery handle may CAS `PUBLISHED` and continue to `DURABLE`/`VERIFIED`.
Any unknown or different identity is STOP and preserve, never delete or
overwrite. Current pointer, Dataset, and both TASK 047 parents remain delta
zero. Raw capture cleanup is always zero.

## Privacy-safe public receipt candidate

The public receipt is a closed body-free projection containing only:

- receipt/contract version, operation kind, and salted opaque references only;
- contract/profile/policy revisions and a private-evidence receipt digest (no
  project, session, plan, build, or audio/body hash is exposed);
- OFF/ON opaque receipt references, measurement-bundle receipt digest, segment
  eligibility, controlled reason codes, and coarse status only;
- private evidence retains all source/output content and identity hashes,
  ranges, counts, fade facts, PCM byte arithmetic, and measurements;
- public projection contains no audio/body hash, physical identity, timing
  range, sample/count detail, or host coordinate; it exposes only opaque
  receipt digest, policy revisions, state, and bounded reason codes;
- exact readback/durability/raw-preserved flags are private evidence;
- `recommended_condition=null`, `dba_or_spl_claimed=false`,
  `audio_body_persisted=false`, `transcript_body_persisted=false`,
  `host_absolute_path_persisted=false`, `dataset_adoption_started=false`.

It MUST NOT contain an absolute/UNC/home/repository path, source or target
basename, account/SID, transcript, spoken phrase, audio bytes, environment
variable, command line, stderr, stack trace, or offending private value.
Failures expose only stable reason codes and bounded opaque IDs.

## Failure matrix and effect-zero rule

Each of the following stops or yields UNKNOWN/FAIL without publishing a current
output, adopting a Dataset item, or altering the raw sources. Before target
publish, derivative delta is zero; after target publish an immutable
journal-bound orphan may exist and is not an effect-zero claim:

- absent/nonterminal/stale TASK-047 receipt; still-writing or incomplete WAV;
- stat-open/read-post identity change, same bytes on a different file, hardlink,
  reparse point, or ancestor/currentness drift;
- OFF/ON microphone, filter, gain, format, analyzer, or policy mismatch;
- room-tone/capture generation mismatch or an incomplete/permuted eight-cell
  set (four ordered cells for each of OFF and ON);
- missing/non-finite/invalid peak, RMS, SNR, DC, speech ratio, band, clipping,
  dropout, or denoise Evidence;
- clipping, dropout, severe low SNR, excessive DC, low speech ratio, voice
  distortion, or overprocessing;
- malformed/incomplete/overlapping VAD, all silence, insufficient speech,
  low-confidence deletion request, uncertain-range deletion, or tiny retained
  island;
- fade length/mode/evidence mismatch, output sample/byte arithmetic mismatch,
  attack/tail damage, or source-lineage mismatch;
- target appearance, temp identity swap, partial write, file/directory flush
  failure, post-publish swap, exact readback failure, or runner crash;
- privacy projection failure or attempted public path/body/error leakage;
- double/concurrent/cross-purpose operation ID reuse.

The execution capability is burned at entry on success or exception. A
journal-bound recovery handle is a separate, private capability: it may only
continue an exact recorded identity—`WRITTEN -> PUBLISHED` when target bytes/
identity match, then `PUBLISHED -> DURABLE -> VERIFIED`—and is burned after
recovery or exception. Any new analysis/publish attempt requires a fresh
operation ID, source reread, and target reservation; there is no automatic
retry or overwrite.

## Reproducibility and completion checklist

Before a future Human-authorized run can be called complete, Evidence must show:

- private full-manifest bytes hash plus the distinct path-free projection
  digest, and exact tool/profile/build digests;
- two current same-chain capture bindings and eight capture cells: six speech
  measurement cells plus one room-tone baseline for each of OFF and ON;
- deterministic plan hash and exact retained/removed/boundary maps;
- original source hashes/identities unchanged after the run;
- output no-replace publication, directory durability, and pinned exact
  readback;
- privacy validator PASS for the public projection;
- one operation produced at most one current output and one receipt;
- negative/fault injection at every pre-publish seam produced derivative delta
  zero; post-publish seams prove current/Dataset/TASK-047-parent delta zero and
  classify an orphan as exact `0/1` with same-operation recovery only. No
  blanket effect-zero claim is permitted after `PUBLISHED`.

Until those facts are obtained from a real authorized native run, the technical
result remains `NOT_CONFIRMED`; fixture PASS must not be promoted.
