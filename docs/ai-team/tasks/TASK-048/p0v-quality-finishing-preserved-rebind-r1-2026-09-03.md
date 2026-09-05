# TASK-048 P0V quality/finishing preserved rebind R1

## Status

- Atomic Unit: `TASK-048 / P-QC-P0V-FINISH-REBIND-R1`.
- DEV profile: `DEV-4 FOUNDATION CRITICAL`.
- Bound current base: `origin/main@b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`.
- Voice-scope source snapshot: `4e150c17f3cd2fe9398d75518473dc8428fae322`;
  the intervening main delta changes only TASK-036 launcher tests.
- State: read-only preservation and dependency rebind; implementation authority
  is false.

The current path-scoped preservation identity is immutable commit
`b44ec1ff316d241e5afc94149b8902f7e306c9b3` on
`codex/task-048-p0v-finishing-r0`. Relative to bound main, its TASK-048 delta is
the following exact4:

- `docs/ai-team/tasks/TASK-048/p0v-native-environment-ab-runbook-candidate-2026-09-05.md`;
- `docs/ai-team/tasks/TASK-048/p0v-real-wav-finishing-design-and-evidence.md`;
- `src/ai_video_production/voice_quality_audio_finishing.py`;
- `tests/test_task048_voice_quality_audio_finishing.py`.

The preserved worktree is clean at `b44ec1f`; its exact4 is absent from current
main and is preserved only as a path-scoped successor. Historical commit
`3361023bab02bf2d7a593231ccc81ba6b2d0b9b3` is not an ancestor of `b44ec1f` and
is superseded for this preservation decision. This unit does not modify, discard,
copy, merge or rebase either branch or consume any uncommitted bytes. The
`b44ec1f` fixture-only snapshot reports focused 167 PASS plus `py_compile` and
diff-check PASS; the Native A/B runbook is an inventory of future native checks,
not execution Evidence. These results do not establish real/native/private audio
quality or Product authority, which remain `NOT_CONFIRMED`.

## Reusable design content

The preserved design already separates four fixture-only operations:

1. generated narration WAV finishing;
2. training-copy QA without loudness normalization;
3. HVAC OFF/ON environment comparison;
4. conservative speech-continuous training-WAV planning.

It correctly records that current TASK-047 writes float32 WAVE format 3 and
cannot mint canonical-format or final-quality PASS. It requires
`PCM_S24LE/48000/mono`, separate raw/processed Assets, current terminal/capture
chain evidence, body-free receipts and effect zero.

## Mandatory rebind to Q1

The candidate may become current only after TASK-047 Q1 lands exact producer
ABIs for:

- canonical capture Asset identity, PCM24/48k/mono format and sample count;
- native-to-canonical source/sample map;
- capture source/format/filter/gain/mute/mixer/OBS currentness;
- authenticated frame sequence, HMAC epoch, gaps/drops/reconnects;
- terminal write-close, durability and readback.

TASK-048 must verify these exact identities before analysis. Metadata claiming a
format, a live meter value or a filename/hash-only receipt is insufficient.

## MUST quality and finishing behavior

- Use per-session room tone and exact segment coordinates.
- HVAC comparison requires OFF and ON sessions with identical current microphone,
  filter, gain, transport and policy coordinates plus whisper, normal and shout
  observations in both conditions.
- All six OFF/ON × whisper/normal/shout observations bind one shared
  `same_content_prompt_sha256` and prompt revision plus their distinct effort
  class. Each OFF/ON effort pair must therefore match, and all six observations
  bind one comparison-plan digest; a missing, duplicate, replayed, cross-prompt
  or cross-revision observation is `UNKNOWN` and cannot be compared.
- Report noise floor, approximate SNR/SNR authority, RMS, peak, clipping,
  non-finite samples, DC offset, dropout, speech ratio and bounded low/mid/high
  stationary-band noise.
- Keep raw and denoised Assets/measurements distinct. Compare before/after without
  silently replacing the raw truth.
- Digital level is dBFS/dBTP only. Do not claim SPL or dBA without a physical
  calibration chain.
- Other-speaker and BGM/game/Discord absence require admitted classifier facts;
  missing classifiers yield `UNKNOWN`, not PASS.
- Segment decisions are `TRAINING_ELIGIBLE`, `REVIEW` or `REJECT`; one session
  aggregate cannot erase a bad/unknown segment.

Speech-continuous finishing MUST:

- retain immutable raw private recovery audio under the separately allocated
  secure-custody owner;
- create separate processed and later engine-format training-copy staged objects,
  each with its own custody receipt, then require distinct TASK-003 Asset
  adoption/registration/readback before either becomes a canonical Product Asset;
- remove only long confirmed non-speech; preserve short natural pauses, breaths,
  endings, uncertain/low-SNR regions and configured speech padding/hangover;
- use `boundary_mode=EQUAL_POWER_CROSSFADE` and `fade_samples=240` exactly at
  every speech-continuous join; bind one boundary-evidence digest per join with
  the retained/removed map and boundary count, and reject every other mode or
  239/241-sample fade;
- calculate `crossfade_overlap_samples=boundary_count*240` and
  `output_sample_count=retained_sample_count-crossfade_overlap_samples`; for
  mono `PCM_S24LE`, bind input/output payload bytes respectively as
  `input/output_sample_count*3` and reduction bytes as
  `(removed_sample_count+crossfade_overlap_samples)*3`, rejecting every
  boundary/overlap/output-count/PCM24-byte mismatch or receipt tamper;
- prove consonant attack and speech-tail preservation;
- avoid forced loudness normalization/limiting/denoising unless the exact
  operation policy owns it;
- remain lossless or use controlled canonical PCM conversion, never lossy audio;
- publish atomically, no-clobber, idempotently and crash-safely with partial
  outputs hidden;
- return `NO_ELIGIBLE_SPEECH` for all-silence/insufficient-speech input;
- bind exact retained, removed and uncertain ranges, input/output hashes,
  sample counts, format, policy, analyzer and quality receipts.

Every Q2 operation and resulting receipt must also bind one current
`OWNER_VOICE_DATA_PREPARATION` Consent/use-rights evaluation for the same opaque
OwnerSubject revision and exact Q1 Asset lineage. Its closed allowed-operation
set must include the operation actually performed (`QUALITY_FINISHING` and/or
`TRAINING_COPY_CREATION`), its output purpose, decision=`ALLOW`, policy revision,
evaluation time, expiry and revocation-currentness evidence. Capture-only,
Dataset-adoption, training or narration Consent is not interchangeable.

## Boundary with TASK-046

TASK-048 issues quality/finishing evidence only. It does not scan folders,
create Transcript truth, mutate Dataset Membership, issue a
`TrainingInputSnapshot`, train a model or seal a model artifact.

TASK-046 Q3 consumes only current TASK-003-read-back Q2 processed-Asset/range and
training-copy Asset receipts. TASK-048/Q2 is the sole producer of the
training-copy staged object and must obtain its separate custody plus TASK-003
adoption/readback before Q3. TASK-046 Q3 never creates, converts, custodies or
adopts that copy. TASK-046 Q4 independently performs Human review, Dataset
adoption and snapshot issuance. No Q1/Q2/Q3 producer may mint or self-attest
canonical Asset truth.
Raw, processed, training-copy, Dataset, TrainingSnapshot and ModelArtifact
lineage remains explicit and non-collapsing.

The future Q2 terminal handoff to TASK-046 Q3 is a single sealed body-free
record over the exact processed and training-copy Asset pairs. It must bind each
Asset's logical ref/revision/checksum/sample count, custody, TASK-003 adoption
and current readback; quality/speech-continuous/range-map/sample-map receipts;
the exact `EQUAL_POWER_CROSSFADE`/240-sample boundary binding, boundary count
and evidence digest per join, overlap/output-sample equations and mono PCM24
payload-byte arithmetic; and reject 239/241 fades, other boundary modes, receipt
tamper and all related arithmetic mismatches;
the current data-preparation Consent; policy/analyzer/code/runtime digests; and
the assigned durable candidate, immutable publication/readback and post-
selection currentness receipts. The owner of that durable Q2 transaction is
still unallocated. TASK-048 cannot self-attest currentness, and the handoff does
not borrow TASK-076/TASK-068/TASK-043 narration-Job authority.

TASK-046 may consume the handoff only when the terminal and current readback are
both `BOUND_VERIFIED`, exact and fresh. Otherwise Q3 remains
`PREFLIGHT_BLOCKED`. The handoff contains no host path, filename, audio or
transcript body, prompt, secret, device identity or voice fingerprint. A future
synthetic mapping fixture remains `SYNTHETIC_CONTRACT_TEST`, uses no Owner audio
and creates no Product receipt or authority.

## Negative and fault requirements

- missing/stale/mismatched Q1 terminal, format, chain or sequence receipt;
- raw float32/multichannel bytes mislabeled as canonical input;
- missing room tone, wrong HVAC pair or mismatched mic/filter/gain/transport;
- missing whisper/normal/shout coordinate or duplicate observation;
- OFF/ON prompt revision/content digest mismatch, cross-effort substitution or
  comparison-plan mismatch;
- noise/SNR/silence/dropout/DC/clip/non-finite threshold boundary and UNKNOWN;
- dBFS promoted to dBA/SPL without calibration;
- missing other-speaker/BGM classifier promoted to PASS;
- overlapping/incomplete VAD coverage, all silence, short pause removal and
  uncertain interval removal;
- consonant attack or speech tail damage, click boundary, non-equal-power mode,
  239/241 fade, boundary-evidence/overlap/output-sample/PCM24-byte arithmetic
  mismatch, receipt tamper or sample-map mismatch;
- raw/processed/training-copy identity collision or in-place overwrite;
- staged/private object presented as canonical without secure custody and exact
  TASK-003 adoption/readback;
- missing/stale/revoked/non-ALLOW data-preparation Consent, wrong OwnerSubject or
  Q1 Asset lineage, wrong-purpose/scope, missing allowed operation, output-
  purpose mismatch, policy-revision mismatch or expiry;
- fixture/in-memory ledger, local rename or successful function return promoted
  to durable Product transaction/currentness proof;
- lossy input/output, wrong RIFF/PCM/rate/channel/bit-depth/sample count;
- partial visibility, destination collision, crash/lost reply/replay and
  durability/readback mismatch, stale candidate, CAS conflict, duplicate
  terminal, restart reconciliation mismatch or orphaned output;
- Dataset/training/model/effect flags true, private path/body/transcript/secret
  leakage or fixture promoted as Product receipt.

## Adoption and implementation START conditions

The independent P0 meter-display policy is also `NOT_BOUND`. A later exact
allocation candidate is limited to
`src/ai_video_production/voice_quality_meter_display_policy.py` and
`tests/test_task048_voice_quality_meter_display_policy.py`; it may produce only
body-free target/warning/true-clip display thresholds and currentness. It consumes
no Q1 audio, issues no quality PASS, and remains subject to a clean worktree,
sole-writer and fresh DEV-4 review before mutation. Its absence does not block
capture transport or emergency stop, but suppresses readiness/target labels and
forces `適正判定 未確定`.

The preserved `b44ec1f` exact4 may be rebound into the coherent integration only
when:

1. immutable commit `b44ec1f`, its clean owner worktree and sole-writer scope
   are revalidated without consuming uncommitted bytes; historical `3361023b`
   remains superseded and is never reintroduced;
2. current `origin/main`, exact4 path overlap and the committed patch
   applicability are revalidated at integration time without mutating the
   preserved worktree or merging/rebasing the branch wholesale;
3. this Q1/Q2/Q3 dependency rebind, including secure custody and TASK-003
   adoption/readback, is incorporated without weakening the preserved
   conservative policy;
4. an exact current `OWNER_VOICE_DATA_PREPARATION` Consent/use-rights producer
   and receipt ABI are allocated, and each Q2 receipt plus TASK-003 processed/
   training-copy adoption request/readback cross-binds it; capture Consent or a
   generic native Human Gate cannot substitute;
5. a canonical Q2 durable transaction/currentness owner and exact non-aliasing
   candidate, immutable publication/readback, CAS/current readback and
   restart/lost-reply reconciliation ABI are allocated. This dependency is
   presently `TASK048_Q2_DURABLE_TRANSACTION_CURRENTNESS_OWNER_NOT_ALLOCATED`;
   the preserved fixture/in-memory ledger, atomic local write or function return
   is never Product durability/currentness proof;
6. a clean dedicated worktree is based on current `origin/main`;
7. exact Allowed Files are issued;
8. syntax/static, focused negative/fault and TASK-047/048/046 targeted regression
   pass;
9. independent Critic, Tester and Judge report zero Critical/High.

Native/private audio execution remains a separate Human Gate. Dataset adoption,
Training, model load/inference, playback, Release, Deploy and Production
Activation are prohibited.

## Acceptance for this rebind

- current `b44ec1f` exact4 preservation identity, historical `3361023b`
  supersession and no-touch/no-wholesale-branch condition are explicit;
- 167-PASS fixture evidence and the Native A/B runbook inventory are recorded
  without promoting native/private audio to PASS;
- all Owner HVAC, dBFS, segment and speech-continuous requirements are formal;
- exact Q1 inputs and Q3 outputs are identified;
- MUST/prohibited/negative/recovery boundaries are testable;
- no dirty/preserved/source/shared path changes occur;
- implementation remains `NOT_AUTHORIZED` pending the START conditions above.
