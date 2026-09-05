# TASK-048 P-QC-P0V-FINISH-1 design and evidence

## Status

- Atomic Unit: `TASK-048 / P-QC-P0V-FINISH-1`
- DEV profile: `DEV-4 FOUNDATION CRITICAL`
- Owner: Development 3
- Base: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`
- State: fixture contract implemented; native audio execution is `NOT_EXECUTED / NOT_CONFIRMED`
- Production, Release, Dataset adoption, model training and real audio effects remain gated.

## Allowed files

1. `src/ai_video_production/voice_quality_audio_finishing.py`
2. `tests/test_task048_voice_quality_audio_finishing.py`
3. this document

No existing TASK-048 module or schema, TASK-014/041/046/047/073/075 source,
Asset/Timeline/Export source, shared document or CHANGELOG is modified.

## Responsibility boundary

This unit adds four deliberately separate fixture-only operations/contracts:

1. `GENERATED_WAV_FINISH` describes conservative head/tail trimming, the fixed
   low-impact `60 Hz high-pass -> 18 kHz low-pass` cleanup chain, two-pass
   `-16 LUFS / -1 dBTP / 11 LU` normalization policy and final technical
   measurement for a generated narration WAV.
2. `TRAINING_COPY_QA` evaluates a finalized TASK-047 recording coordinate and
   describes an exact-range, format-only derivative copy for a current admitted
   model recipe. It never applies loudness normalization, limiting, compression,
   denoising or arbitrary filters.
3. `ENVIRONMENT_AB_QA` compares air-conditioner OFF/ON sessions only when the
   microphone, filter, gain, transport format and currentness coordinates are
   identical. It measures three effort classes (`WHISPER`, `NORMAL`, `SHOUT`),
   per-session room tone, noise floor, SNR/approximate-SNR, RMS, peak, clipping,
   non-finite samples, DC offset, dropout, speech ratio and low/mid/high-band
   stationary noise. ON/OFF is never itself an accept/reject rule.
4. `SPEECH_CONTINUOUS_TRAINING_FINISH` plans a separate processed training WAV
   from strict WAV/VAD/quality Evidence. It removes only long confirmed
   non-speech, preserving uncertain intervals, short natural pauses, breaths,
   speech padding and hangover. The processed WAV is the user-facing candidate;
   the immutable raw recording remains available for recovery/audit.

The generated and training output operations require `PCM_S24LE / 48000 Hz /
mono`. The training format is
bound to an exact engine recipe digest; a later engine with another requirement
needs a fresh contract. No model-name inference or caller format override is
accepted.

The current TASK-047 Controller records IEEE float32 WAVE format 3 and its live
meter/five-second gain receipt does not provide final Peak/RMS/clip/non-finite,
room/session or current capture-chain authority. Therefore live meter values
cannot mint final quality PASS. TASK-048 requires a current TASK-047 terminal
receipt plus a verified canonical-input, transport-format and capture-chain
receipt before training QA. Raw-to-canonical conversion remains TASK-047
responsibility; TASK-048 rejects raw float32 or unproven multichannel input.

The module performs no filesystem or subprocess work. Its deterministic runner
has fixed `fixture_only=true`, `authority_created=false`,
`production_eligible=false`, and `external_effect_count=0`. Its receipts may be
used in tests and UI composition only. They do not authorize Task-014
publication, TASK-046 Dataset adoption, TASK-075 execution/playback, Owner
acceptance, training or Production use.

## MUST

- Preserve the exact OBS/TASK-047 raw source bytes and physical identity as an
  immutable recovery/audit parent.
- Derive the user-facing training candidate only from a strict current
  `PCM_S24LE / 48000 Hz / mono` WAV and exact contiguous VAD evidence.
- Remove only long confirmed non-speech; retain short pauses, every uncertain
  interval, pre-speech padding, post-speech padding and hangover.
- Require verified zero-crossing or a short equal-power crossfade at every
  edit boundary plus independent consonant-attack and speech-tail readback.
- Bind the lossless output hash/identity, exact range map, final sample count,
  durability/readback and a non-authoritative TASK-046 lineage-candidate hash.
- Measure OFF/ON air-conditioner sessions over whisper/normal/shout with the
  same current capture chain and closed quality axes.

## PROHIBITED

- Raw source overwrite, move, delete or in-place processing.
- Lossy codecs, silence-based zero-gap compression, unproved resampling,
  implicit downmix, noise-condition preference or automatic Dataset adoption.
- Treating a fixture receipt, public hash, live meter or size reduction as
  TASK-046 adoption authority or Production quality proof.
- Persisting audio bodies, transcripts, host paths, external stderr or private
  account/recording coordinates in public receipts.

## Acceptance and receipt candidates

`FIXTURE_SPEECH_CONTINUOUS_TRAINING_WAV_RECEIPT_V1` is the only receipt
candidate added for the speech-continuous operation. It reports input/output
PCM payload bytes and reduction bytes using
`LOSSLESS_SAMPLE_RANGE_REMOVAL_PLUS_BOUNDARY_CROSSFADE`; a continuous-speech
source with no edit boundary correctly reports zero reduction. Each joined
boundary uses the fixed 240-sample equal-power overlap, and the plan/readback
bind exact boundary count, overlap sample count, and one evidence digest per
boundary. A PASS also carries
`task046_lineage_candidate_sha256`, while explicitly fixing
`task046_lineage_authority_created=false` and
`dataset_adoption_started=false`. Any boundary, range-map, durability,
readback, attack/tail or raw-preservation failure emits no lineage candidate.
This remains fixture-only and cannot satisfy TASK-046 by itself.

## Generated WAV contract

The future native owner operation must pin and retain the raw source, verify a
regular single-link non-reparse file and ancestor/current identity, execute a
fixed shell-free backend, and write only through a private TASK-014 sink. It
must perform final independent measurement and bind exact output hash, physical
identity, format, sample count, directory durability and readback. The raw WAV
is never overwritten, moved or deleted.

The fixture receipt is deliberately named
`FIXTURE_OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1`; it cannot occupy the TASK-073
D4 `OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1` slot. The native producer ABI and
trusted backend composition are intentionally not invented here.

## Training-copy contract

There is no E-drive crawl, newest/mtime selection or implicit recording import.
The source must be an exact bounded coordinate with a terminal TASK-047 receipt,
current Consent/review digests and a pinned same-open identity snapshot. A size
that merely appears stable once is not proof that recording has finished.

The future source owner must prove all of the following before the copy runner:

- terminal/finalized recording state and complete RIFF/WAVE structure;
- write-close/current identity, regular file, one link, no reparse point and
  current ancestor security;
- exact source bytes/hash and approved half-open sample range;
- current analyzer/profile, Consent, Human review, canonical-input,
  transport-format, capture-chain and engine-recipe identities.

Clipping, SNR, silence and minimum speech length are closed measured axes.
Other-speaker and BGM absence require admitted classifier receipts; FFmpeg alone
cannot prove either. Missing classifier or noise reference yields `UNKNOWN`,
not PASS. Any UNKNOWN blocks later Dataset adoption.

TASK-048 does not own a Dataset store. A future successful copy must be written
through the Dataset/staging owner's private operation sink. Human approval and
canonical Dataset adoption remain TASK-046/Voice Dataset owner effects.

## Air-conditioner OFF/ON comparison

TASK-047 owns capture triggers, display and capture receipts. TASK-048 owns the
quality policy and segment classifications. TASK-046 alone owns later Dataset
adoption.

Each OFF/ON session has its own room-tone baseline. A valid comparison requires
the exact same current mic, filter, gain, sample rate, channel and transport
identities. Each capture also seals the source physical identity, capture and
room-tone currentness, current ancestor/read/identity facts, and matching
capture/room-tone generation. Any mismatch produces `UNKNOWN`; no runner is
called. Complete comparison requires six exact, typed measurements in canonical
order (two conditions times whisper/normal/shout) and six exact raw-vs-denoised
pairs. The receipt reports
noise-floor and low/mid/high-band ON-minus-OFF deltas in dBFS. Without acoustic
calibration it never claims dBA or SPL and never automatically recommends ON or
OFF.

Segment policy returns only `TRAINING_ELIGIBLE`, `REVIEW` or `REJECT` with
closed reason codes. Non-finite input, clipping, dropout, excessive DC, severe
low SNR and low speech ratio reject. Approximate or marginal SNR and missing
measurement facts, including RMS or peak, require review. Top-level comparison
is `PASS` only when every segment and denoise assessment is eligible; review or
reject is reflected as `UNKNOWN` or `FAIL`. Denoise improvement is assessed separately
from voice distortion/overprocessing risk and both artifacts bind the same
input source; a large noise reduction cannot override detected voice damage.

## Speech-continuous training WAV

The pure range planner requires strict current WAV evidence: valid RIFF/format
chunks, exact data length, validated odd chunks, no non-finite samples and
source hash/physical-identity equality. VAD intervals must exactly and
contiguously cover the complete input. All-silence and insufficient-speech
inputs stop with effect zero.

Only non-speech with fixed confidence `>= 0.95` and duration of at least one
second is removable. The equal-power boundary overlap is likewise fixed at
exactly 240 samples; a caller cannot alter the fade to manipulate the reported
capacity reduction or select a longer fade that consumes preserved speech
padding. Lower-confidence non-speech is retained exactly like an
uncertain interval. A short pause
(up to 0.5 seconds) is always retained; uncertain intervals are also retained
so low-SNR whisper, BGM/Discord ambiguity or fan noise cannot cause destructive
speech removal. Every speech interval receives pre-padding, post-padding and
hangover before retained ranges are merged. Thus joining retained ranges does
not create an unnatural zero-gap stream.

The future runner must bind exact retained/removed source ranges, removed
sample count, fixed short equal-power crossfade length, exact boundary count,
per-boundary evidence, overlap accounting, input/output hashes and identities,
format, sample count and quality-measurement receipt. Each boundary requires a
verified zero crossing or short equal-power crossfade, while separate checks
must prove consonant attack and speech tail preservation. Partial output is
never published; target collision, crash, fsync or readback failure remains
effect zero/failed evidence.

Capacity optimization is limited to removing admitted source sample ranges and
the exact overlap introduced by its click-safe equal-power boundary crossfade.
Every retained range participating in a boundary must contain at least the
fixed overlap length; a tiny uncertain island stops the plan rather than being
discarded or over-read. The resulting output sample count must remain positive.
The contract computes input/output PCM payload bytes at three bytes per mono
sample and records the exact byte reduction. It does not claim RIFF container
compression and cannot trade fidelity for a smaller file.

The canonical policy forbids lossy codecs. Mono preservation is required for
the verified canonical input. A raw float32 or multichannel source needs an
explicit TASK-047 conversion decision, resampler/dither policy and, for
downmix, selected-channel or phase-safety Evidence before TASK-048 can consume
the canonical derivative. TASK-048 does not silently downmix, resample or
dither raw capture.

## State and recovery

Operation IDs are consumed at method entry under a lock in one service
instance. Success and every exception burn the ID; double, concurrent and
cross-purpose reuse are rejected. Reconstructing the fixture service resets its
in-memory set, but every resulting receipt remains non-authoritative. This is
not durable one-shot proof. The fixture service performs no automatic retry
and cannot return an authoritative duplicate. A native recovery flow requires
a fresh authoritative source read and the relevant owner transaction.

Every public receipt is body-free: no audio, transcript, absolute path, OS
detail or external stderr is retained. Rejections expose stable contract text,
not source bodies.

## Negative and fault matrix

Covered in the focused test file:

- still-writing, stale read/ancestor, changed identity, hardlink/reparse and
  incomplete WAV source stop before the runner;
- caller cleanup/filter/loudness/format injection is rejected;
- clipping, loudness, true peak, silence and output durability/readback failures
  cannot PASS generated QA;
- training requires a terminal recording receipt and exact sample range;
- low/unknown SNR, excessive silence, short speech, detected or unverified other
  speaker and detected or unverified BGM cannot PASS;
- training readback must match exact range and format;
- runner-build drift, runner exception, double/concurrent call and cross-purpose
  operation reuse burn without retry;
- non-finite measurements, noncanonical format, mutated raw and claimed external
  effect are rejected;
- receipts remain fixture-only, body-free and Dataset-effect-free.
- cross-family receipt relabelling and integer lookalikes for boolean authority
  markers are rejected; nested source/format bindings and format scalar fields
  require exact JSON-compatible types (integer rate/channels, string format);
- source and public identifier fields reject drive paths, traversal and URIs;
- OFF/ON capture/room-tone generation, source physical identity/currentness,
  chain mismatch, stale capture receipts, incomplete or permuted six-cell grids,
  missing RMS/peak, non-finite or positive-invalid dBFS meter scalars, and fixed
  no-dBA/no-SPL/no-condition-recommendation projection,
  non-finite/dBFS bounds, threshold boundaries, approximate SNR, stationary
  band deltas, denoise source mismatch and distortion-over-improvement;
- strict RIFF/format/data/odd-chunk/non-finite/currentness rejection, all
  silence, incomplete/overlapping VAD coverage, continuous speech, short pause,
  uncertain low-SNR/BGM-like intervals, missing/wrong/stale post-stop TASK-047
  terminal receipt, raw float32/multichannel handoff,
  lossy/phase/dither policy rejection, click-safe boundary and attack/tail
  readback, tiny retained-island/crossfade feasibility, partial publication,
  output count and source-lineage mismatch.

Native follow-up tests must additionally cover stat-open/read-post swaps, same
bytes/different file identity, partial/trailing RIFF writes, target appearance,
operation-owned temp identity, fsync/readback failures, foreign cleanup, every
crash seam, backend/process replacement and public error/log leakage. These are
not reported PASS by this unit.

## Verification

- Python 3.13 `py_compile` for the new source and test: PASS.
- Bundled workspace Python `py_compile` for the new source: PASS.
- Isolated fixture-only focused pytest after Critic authority, identity,
  cardinality, scalar strictness, meter-calibration and crossfade-accounting
  closure, including the missing-room-tone A/B delta fail-closed case and the
  exact `0 dBFS` peak-versus-clipping fact boundary: `169 passed`.
- Existing TASK-048 regression collection: `NOT_EXECUTED` because the available
  pytest runtime lacks `jsonschema`; no dependency was installed and this is
  not reported as PASS.
- `git diff --check`: PASS.
- Static effect scan: the new source imports no filesystem or subprocess API.

Actual FFmpeg, audio files, E-drive recordings, private Owner voice and
paid/cloud execution were not used by this unit.
