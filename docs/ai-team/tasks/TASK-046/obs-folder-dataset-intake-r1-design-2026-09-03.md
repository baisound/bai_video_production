# TASK-046 P-VS-3B/P-VS-4B OBS folder Dataset intake R1 design

Date: `2026-09-03`

## Authority and Git bind

- Active Product: BAI VIDEO PRODUCTION.
- Existing Task: `TASK-046` continuation; no new Task ID.
- DEV profile: `DEV-4 FOUNDATION CRITICAL` because this boundary handles the
  Owner's private voice, consent, Dataset identity and training admission.
- Design base: `origin/main@4d233c8c77c7328f5b221642040faf06c0a6a15c`.
- Dedicated branch/worktree:
  `codex/task-046-obs-folder-dataset-intake-r1` /
  `.worktrees/task-046-obs-folder-dataset-intake-r1`.
- TASK-047 is a completed technical capture foundation. Production training
  capture remains `NOT_CONFIRMED` until exact capture, Consent, encrypted
  storage and Owner Gate receipts are bound. This amendment does not change OBS
  capture, recording tracks, recording controls or installation.

Owner intent is to select an arbitrary local OBS recording folder once in Voice
Studio, continue recording long-form game commentary into that folder, and
incrementally turn eligible microphone speech into a local fine-tuning Dataset.
The selected path is not hard-coded and is never emitted in a public receipt.

## Current-source findings

The amendment reuses these existing canonical owners instead of creating a
parallel store:

- `SourcePathPolicy` authorizes an explicitly selected import root.
- `AssetIngestService` owns ordinary Asset copy, same-handle size/content
  revalidation, SHA-256 dedupe and logical URI publication. Its current route
  writes plaintext media and retains the original basename in Asset/manifest
  evidence, so it is **not** an eligible production private-voice custody port.
  TASK-046 must reuse the Asset Registry identity while a bounded encrypted
  private-media port supplies the managed Asset binding.
- `SQLiteProductStore` and `AssetRecord` remain the canonical Asset Registry.
- `FasterWhisperProvider` and `ResumableTranscriptionService` own local/offline
  transcription, chunked long-media processing and source-change detection.
  Their current publication/work files are plaintext, so production private
  audio/text remains `NOT_BOUND` until an encrypted private transcript port
  wraps bounded decrypt/work, DACL, key custody, retention, revoke/delete and
  crash recovery. Automatic model download remains disabled.
- `voice_quality_calibration.py` owns canonical measurement/quality receipt
  semantics. The intake adapter may consume current verified receipts but may
  not invent `PASS` when an analyzer or receipt is missing.
- `VoiceDatasetStore`, `VoiceDatasetRevision`, membership/exclusion records,
  `DatasetAdoptionReceipt` and `TrainingInputSnapshot` in
  `voice_dataset_revision.py` remain Dataset truth.
- `ProductProjectManifestStore` remains Project truth. The selected OBS folder
  is a private local preference, not a Project/Dataset/Asset identity.

The concrete gap is a bounded adapter between a private selected folder and the
existing Asset/Transcript/Quality/Dataset owners: terminal-file discovery, OBS
track classification, body-free eligibility projection, detailed review
reasons, incremental dedupe and compilation of an Owner-reviewable Dataset
proposal. No current canonical type owns that orchestration.

Unit A is deliberately limited to `SYNTHETIC_CONTRACT_TEST`. Every serialized
input and output fixes `synthetic_input_only=true` and `owner_audio_used=false`;
production authority or real Owner audio is rejected. Current Q1–Q3 producers
cannot yet satisfy the required canonical receipt coordinates, so real
candidate coverage remains `NOT_CONFIRMED` until a successor amendment imports
their landed canonical types. Caller-supplied state strings cannot upgrade this
unit to production.

Current TASK-047 source proves selected-source transport/control, meter,
disk/max-duration stops, partial-to-final WAV and a body-free transport receipt;
it does not prove training-material quality. Its writer currently emits 48 kHz
WAVE format-3 float32 with OBS plane count, while the wire header carries no
sample-rate truth. There is no verified input-rate binding, resample/downmix/
PCM24 canonicalization, final Peak/RMS/clip receipt binding, end-to-end queue
drop/sample-map receipt, SNR/speech-ratio/contamination analyzer or encrypted
private staging. Unit A therefore treats capture terminal, capture format,
track, quality, private Asset and Transcript facts as `NOT_BOUND` unless future
effect owners provide exact current receipts; it generates none of them.

The shortest implementation order is fixed as:

1. Q1 TASK-047 capture terminal/format truth and canonicalization;
2. Q2 TASK-048 capture-quality analyzer/policy receipts;
3. Q3 TASK-046 private folder discovery, encrypted ingest/transcript,
   segmentation and training-copy creation;
4. Q4 existing Dataset review/adoption, then separately authorized fine-tune.

This order preserves the completed TASK-047 transport denominator and counts
only quality/intake work as remaining. It does not reopen the recording UI.

## Exact responsibility boundary

```text
private Voice Studio folder selection
  -> private folder preference (host path; never public)
  -> terminal-file discovery snapshot (private custody; public status only)
  -> encrypted private-media port + TASK-003 Asset Registry identity
  -> encrypted/offline FasterWhisper transcript of the managed copy
  -> speech-range proposals
  -> existing quality/consent/rights/label bindings
  -> TASK-046 intake proposal and review summary (Unit A synthetic only)
  -> one Owner Dataset-adoption Human Gate
  -> existing VoiceDatasetRevision + TrainingInputSnapshot
  -> separate Owner training-start Human Gate
  -> existing P-VS-4A training/ModelCandidate evaluation
```

Folder selection does not adopt a Dataset. Discovery does not ingest a file.
Ingest does not transcribe. Transcription does not classify quality. A proposal
does not commit a Dataset. Dataset adoption does not start training. Training
completion does not approve or activate a model.

## Private preference and public readback

The native picker returns an absolute host path only to the trusted local Voice
Studio process. The private preference is stored under the existing protected
Product settings directory, with symlink/reparse-point checks, restrictive
permissions and atomic replacement. It is a replaceable UI preference, not a
new canonical Dataset/Asset/Project store.

The public readback contains only:

- preference revision and currentness;
- a random opaque folder-binding ID that is not derived from the path;
- selection timestamp and `configured=true|false`;
- availability/readability state and reason codes;
- `source_path_body_present=false`.

The canonical path and any installation/project-scoped keyed digest remain
inside the protected preference record. An unsalted path digest is forbidden.
The public projection contains no path/content/audio fingerprint digest,
absolute/UNC path, directory basename, file name, prompt text, transcript text,
audio bytes, secret or environment value. The private Voice
Studio screen may display the locally loaded path to the Owner, but that view
must not be serialized into operational receipts, logs or test fixtures.

## Stable-file discovery

Discovery is recursive only when the Owner explicitly selects that policy. It
accepts regular non-symlink files inside the selected root and rejects path
escapes. Candidate extensions are allowlisted; extension alone never proves
media validity.

A file is eligible for private-media copy only after two observations separated
by the configured settle interval have the same canonical file identity, size
and last-write timestamp, a producer-terminal receipt binds that exact file or
a Windows handle excluding write sharing is held through the full copy and
post-copy revalidation, and a same-handle hash pass confirms the observed size.
Without one of those terminal proofs, the file remains `WRITE_IN_PROGRESS` even
if two passive observations happen to match. Empty files,
partial/temp suffixes, locked files, unstable files, reparse points and files
outside the selected root are skipped with a reason. Skips are retriable on a
later scan and are not exclusions from the Dataset.

The adapter does not move, rename, overwrite, truncate or delete source files.
The encrypted private-media port independently repeats source authorization and
same-handle content revalidation while publishing a canonical Asset identity.

## Track and source classification

The preferred source is an OBS microphone-only track. Discovery facts bind
track index, codec/layout metadata and a track-role classification receipt; no
track label alone is trusted as proof.

Priority:

1. verified `MIC_ISOLATED` track;
2. `MIXED_OR_UNKNOWN` material is not accepted by R1. A future bounded
   contamination/speaker-classification effect owner must issue an exact
   current receipt before a later revision can admit it;
3. verified desktop/game/Discord/BGM-only tracks are excluded.

Mixed/unknown material cannot silently receive a quality `PASS`, and Owner
review cannot upgrade UNKNOWN machine evidence to PASS. R1 accepts only an
exact current `MIC_ISOLATED` receipt; everything else is excluded or remains
review-only.

## Segment eligibility and exclusions

Long recordings are transcribed locally from the managed Asset copy. Candidate
ranges are derived from transcript timestamps plus bounded speech padding;
overlap is merged before dedupe. Transcript text is private and is referenced by
digest/logical identity only in public intake records.

Each accepted range must bind all of the following in this order:

- encrypted managed source Asset revision/checksum and a half-open microsecond
  source range;
- canonical TASK-006/023 `TranscriptManifest` `source_asset_id`, manifest
  SHA-256, provider ID, model ID, language and exact range binding; no second
  Transcript truth is created;
- exact Owner VoiceProfile/speaker binding;
- current consent and rights evaluations;
- current canonical quality evaluation;
- Owner-approved label binding;
- normalized training-copy Asset revision/checksum, actual sample count and the
  exact `PCM_S24LE_48000_MONO` format profile;
- existing `VoiceDatasetMembershipEntry` pointing to the normalized
  training-copy Asset with `[0, sample_count)`;
- content/audio-fingerprint dedupe identity.

Only after the membership draft is reviewed and adopted does the existing
`VoiceDatasetRevision` become canonical. Only that committed revision can be
selected by an existing `TrainingInputSnapshot`. The source Asset, normalized
training-copy Asset, membership, Dataset revision and TrainingInputSnapshot are
distinct identities and are never collapsed.

Detailed intake reasons include `SILENCE`, `CLIPPING`, `LOW_SNR`,
`OTHER_SPEAKER`, `MUSIC_OR_GAME_AUDIO`, `DESKTOP_ONLY`, `TRANSCRIPT_MISSING`,
`LOW_TRANSCRIPT_CONFIDENCE`, `DUPLICATE`, `OVERLAP`, `CONSENT_BLOCKED`,
`RIGHTS_BLOCKED`, `VOICE_PROFILE_MISMATCH`, `PRIVATE_OR_SECRET_CONTENT`, and
`OWNER_EXCLUDED`. Canonical Dataset exclusions map to the existing bounded
reason vocabulary; the detailed proposal receipt remains attached evidence.
Unknown facts fail closed and never become accepted duration.

The canonical TASK-048 segment quality receipt consumed here must be current to
the recording session and bind the exact processed source Asset/range. Its
downstream Q2 acceptance includes HVAC OFF/ON room tone and same-content
whisper/normal/shout comparisons, noise floor, reproducible SNR or proxy,
low-frequency/fan noise profile, RMS/peak/peak-hold, clip/nonfinite, DC,
dropout, speech ratio and voice-distortion checks. Pre/post denoise are separate
Assets/receipts, not overwritten states. The receipt uses dBFS for digital level
and never claims SPL/dBA without calibrated physical measurement. Unit A does
not duplicate these measurements; it consumes their exact quality receipt and
subject range. Until Q2 lands, production quality is `NOT_BOUND` and cannot be
upgraded by Owner review alone.

TASK-046 accepts only the TASK-048 processed speech-continuous artifact as the
user-facing Dataset source. Raw capture is immutable private recovery evidence,
never displayed or labeled as the canonical training source. The processed
artifact must carry an exact raw-to-processed receipt binding input/output
hashes, retained and removed source ranges, uncertain preserved ranges, fade/
crossfade samples, final format, duration/size, quality state and atomic
no-clobber/idempotent publication. All-silence becomes
`NO_ELIGIBLE_SPEECH`; partial output is never published. TASK-046 then creates a
separate engine-format training-copy Asset with its own normalization/sample-map
receipt. The raw, processed source and training copy never share identity.

The review UI lets the Owner exclude a file or segment for privacy, secrets or
personal information without requiring a fixed script. Transcript text shown
for review remains private local UI data.

## Training copy and Dataset adoption

Source originals remain read-only and preserve their original format, including
48 kHz/24-bit material. Normalization creates a separate Product-managed Asset
for each accepted training segment in the exact engine input format. That
operation has a separate operation identity and receipt from discovery,
transcription and Dataset adoption.

Unit A computes proposal **coverage**, not canonical Dataset/training readiness.
All admitted training-copy Assets are already 48 kHz mono before Unit A; source
ranges use integer microseconds. Coverage sums actual unique normalized Asset
sample counts, so unlike source-rate sample arithmetic it cannot mix timebases.
R1 proposal coverage states are:

- `COVERAGE_LT_30`: less than 30 minutes accepted clean speech;
- `REVIEW_BLOCKED`: any unresolved binding or pending Owner exclusion review;
- `MINIMUM_COVERAGE_MET`: at least 30 minutes and less than 60 minutes;
- `TARGET_COVERAGE_MET`: at least 60 minutes.

Thirty minutes is the first coverage floor and 60 minutes is the initial
coverage target. `TRAINING_READY` remains owned by the existing canonical
Dataset readiness receipt combined with current recipe/license/resource and
training Human-Gate facts; Unit A never issues it. Additional recordings compile a new proposal and immutable
Dataset revision; prior source Assets, receipts and revisions remain unchanged.

Prior committed Dataset members win dedupe. New candidates are ordered by
source Asset checksum, source start/end microseconds and candidate ID; the first
non-overlapping unique fingerprint wins. Later duplicates/overlaps are excluded.
The proposal binds the prior Dataset head and private fingerprint-index digest.

One Dataset-adoption Human Gate is bound to the exact proposal digest, Dataset
summary, VoiceProfile revision, consent/rights evaluations, accepted/excluded
ranges, unique accepted duration and policy revision. After adoption, a
separate one-shot training authorization binds the exact
`TrainingInputSnapshot`. Authoritative replay/idempotency and Dataset-head CAS
remain with the existing Dataset adoption owner; Unit A only binds operation,
idempotency and expected-head inputs and does not claim replay classification.
Stale consent/profile/policy, digest mismatch or Dataset head change fails
closed at that owner.

## Body-free intake contract

The first implementation unit is a pure validator/compiler. It accepts facts
already obtained by effect owners and emits no path/audio/text body:

- `ObsFolderBinding`: random opaque binding ID, preference revision and
  currentness only; no path-derived digest in the public projection;
- `ObservedRecording`: synthetic source identity digest, stability/media/track
  facts, producer-terminal proof, capture-format receipt, encrypted
  private-media custody receipt and optional canonical Asset binding;
- `SpeechRangeCandidate`: source microsecond range; exact canonical Transcript
  manifest fields; voice, consent, rights, quality, label and private dedupe
  bindings; transcript/training private-custody receipts; normalized 48 kHz
  training-copy Asset, actual sample count and an exact source/output sample-map
  normalization receipt;
- `ExistingFingerprintIndexBinding`: bounded sorted private fingerprints bound
  to the exact Dataset ID and expected Dataset head; an omitted/unbound index
  cannot produce accepted coverage;
- `ObsFolderDatasetIntakeProposal`: deterministic accepted/review/excluded
  partitions, reason counts, unique accepted samples/duration, proposal coverage
  state, operation/idempotency/prior Dataset head/VoiceProfile/policy bindings
  and proposal digest.

The compiler never opens a path, hashes a file, reads audio/text, invokes an
analyzer/ASR/model, creates an Asset, commits a Dataset or issues training
authority. It rejects any extra/raw body field and any path-shaped public value.
It also never creates a canonical `VoiceDatasetMembershipEntry`; Unit A only
checks compatibility. Membership is issued solely by the existing Dataset
adoption owner after the exact proposal and Human Gate are verified.

### Unit A closed contract

All objects reject unknown fields. Lists contain at most 4,096 items, reason
lists at most 64 sorted unique codes from a closed vocabulary, typed IDs at most
256 ASCII-safe characters with mandatory domain prefixes and no slash/path/URI
form, and digests use the repository
`sha256:<64 lowercase hex>` form. Record digests are SHA-256 over canonical JSON
excluding only their own digest field and including `record_type` plus a fixed
`contract_version=TASK046_OBS_FOLDER_INTAKE_R1` domain field.

- every record: `authority_kind=SYNTHETIC_CONTRACT_TEST`,
  `synthetic_input_only=true`, `owner_audio_used=false`. The authority value is a
  fixed contract literal; the exported compatibility constant is not an
  authority switch and runtime mutation cannot widen the boundary;
- `ObsFolderBinding`: `folder_binding_id` (random opaque),
  `preference_revision>=1`, `currentness=CURRENT|STALE|UNKNOWN`,
  `configured`, `availability=AVAILABLE|UNAVAILABLE|UNKNOWN`, sorted reasons
  derived exactly from those states (contradictory reasons are invalid),
  body/path flags false and `binding_sha256`. It contains no path digest.
- `ObservedRecording`: exact `scan_operation_id`, random `recording_id`, private
  `source_identity_sha256`,
  `finalization_state=BOUND_VERIFIED|NOT_BOUND|MISMATCH|STALE|UNKNOWN`,
  nullable exact finalization receipt, capture-format binding/receipt with exact
  `PCM_S24LE_48000_MONO` when verified, and private-media custody binding/receipt,
  `stability=STABLE|WRITE_IN_PROGRESS|LOCKED|PARTIAL_OR_TEMP|UNSUPPORTED|UNKNOWN`,
  media fact, `track_class=MIC_ISOLATED|MIXED_OR_UNKNOWN|NON_MIC_ONLY|UNKNOWN`,
  exact track receipt SHA-256, and encrypted source Asset binding. Asset fields
  are all present only for `BOUND_VERIFIED` and otherwise all null.
- `SpeechRangeCandidate`: exact observation binding; integer
  `[source_start_us, source_end_us)`; canonical Transcript `source_asset_id`,
  manifest SHA-256, provider ID, model ID, language and exact range SHA-256
  deterministically bound to source Asset ID, manifest digest and start/end;
  current VoiceProfile/consent/rights/quality/label states and digests; quality
  subject Asset checksum and exact range; private fingerprint; Owner exclusion
  state; transcript/training custody receipts; normalized training Asset ID,
  revision and checksum binding,
  `PCM_S24LE_48000_MONO`, sample rate 48,000, one channel, 24 bits and actual
  positive sample count; and normalization receipt input checksum/range plus
  output Asset ID/revision reference/revision digest/checksum/sample count. Normalization output coordinates
  must equal the training Asset coordinates. Output samples may not exceed the 48 kHz source
  range ceiling. Transcript/Asset fields are nullable only when their
  contract state is not bound, and then the candidate cannot be accepted.
- `ExistingFingerprintIndexBinding`: exact Dataset ID/head, state, sorted unique
  fingerprint list and exact count, bounded to 4,096. Non-bound indexes contain
  zero entries.
- `ObsFolderDatasetIntakeProposal`: exact `operation_id`, `idempotency_key`,
  Project/Dataset IDs, nullable expected Dataset head, folder/VoiceProfile/
  policy/private fingerprint-index bindings, sorted candidate results and reason
  counts, unique 48 kHz sample total, integer floor milliseconds,
  `coverage_state`, Owner Dataset Gate required, `canonical_training_readiness`
  fixed to `NOT_CONFIRMED`, `canonical_membership_issued=false`,
  `training_input_snapshot_issued=false`, all effect/body/path flags false, timestamp and
  proposal SHA-256.

Stable processing order is `(source_asset_checksum, source_start_us,
source_end_us, candidate_id)`. Existing committed fingerprint identities are
inserted before new candidates. Only otherwise-admissible candidates enter the
interval/fingerprint winner set. A candidate whose private fingerprint already
exists is `EXCLUDED/DUPLICATE`; a later intersecting range on the same encrypted
source Asset is `EXCLUDED/OVERLAP`. A training Asset ID, revision reference,
revision digest or checksum can contribute coverage at most once; reuse is
`EXCLUDED/TRAINING_ASSET_DUPLICATE`. A failed quality fact must carry at least
one reason from the closed quality vocabulary.
Any missing/unknown required fact is
`REVIEW_REQUIRED`; explicit fail, mismatch, stale, revoked, non-mic, privacy,
Owner exclusion, duplicate or overlap is `EXCLUDED`.

`public_projection()` exposes only synthetic/not-owner-audio status,
configured/current/availability, aggregate
accepted/review/excluded counts, aggregate reason counts, accepted duration,
coverage state and false effect flags. It exposes no IDs, digests, paths,
basenames, file names, fingerprints, transcript/model/provider/language values
or per-candidate data.

## P0V cross-task ABI

The coherent batch keeps distinct operations and receipts:

- TASK-047: completed technical capture foundation; production file identity is
  `NOT_CONFIRMED` without exact terminal/capture/Consent/storage receipts.
- TASK-046: folder intake, Dataset adoption, `TrainingInputSnapshot`, fine-tune
  job, `ModelCandidate` and Owner model approval.
- TASK-013: model inventory/readback only. Fine-tuned artifact receipt
  missing/stale/revoked means unselectable. Zero-shot and fine-tuned candidates
  never collapse merely because an engine reports the same model ID. Listing,
  readback and selection must perform no load/start/download.
- TASK-014: local narration execution consumes the exact approved route/model
  candidate revision and returns a body-free WAV result receipt. The actual
  Qwen load/inference worker remains a separate missing effect surface.
- TASK-048: current source supplies calibration/quality receipt semantics. The
  Owner-authorized but not-yet-merged P0V finishing amendment is a separate
  dependency and operation from Dataset source preparation. Until its exact ABI
  lands it is `NOT_BOUND`; it never owns TASK-046 training copies.
- TASK-075: playback/listen boundary consumes only the accepted finished Asset.
- TASK-073: composition/Voice Studio projection consumes body-free statuses and
  exact identities; it does not infer model usability or Dataset readiness.

Required cross-task negatives: stale/revoked fine-tuned artifact; wrong route,
candidate or revision; model-ID collapse; raw OBS path/body leakage; model load,
runtime start or download during inventory/readback/selection; TASK-014 output
receipt mismatch; and accidental use of TASK-048 finishing receipt as a
training-copy receipt.

## Bounded implementation units and Allowed Files

### Unit A — pure intake proposal contract

Allowed Files:

1. `src/ai_video_production/voice_obs_folder_dataset_intake.py`
2. `tests/test_task046_voice_obs_folder_dataset_intake.py`
3. this task-local design/evidence document

No schema is added in Unit A. Serialization remains task-local Python contract
until the consumer ABI is independently accepted; this avoids prematurely
creating a second canonical Dataset schema.

Effect ceiling: zero. No filesystem/audio/transcript body/model/native/provider
operation. Production Owner audio is rejected; positive coverage fixtures are
non-biometric synthetic metadata only.

### Unit B — private selection/discovery and managed ingest orchestration

Requires a fresh exact Allowed Files amendment after Unit A review. Candidate
new TASK-046 files are a private preference adapter, discovery runtime and
focused tests. Any shared `VoiceStudio`, trusted launcher or native-dialog file
requires sole-writer confirmation. Unit B must call TASK-003 ingest rather than
copying its storage/Asset logic.

### Unit C — transcript/quality/segment/training-copy orchestration

Requires current runtime, encrypted Product storage and private-audio Human
Gates. It reuses FasterWhisper, quality receipts, Asset Registry and Dataset
contracts. Real audio reads, conversion and transcription are not authorized by
Unit A.

### Unit D — Voice Studio UI and EXE integration

Requires sole-writer ownership of the current Shell/application ports. It adds
folder picker/readback, scan status, accepted duration, exclusion reasons,
readiness and the Dataset-summary approval dialog. It does not expose raw paths
in public receipts and does not start training from folder selection.

## Unit A required tests

- deterministic canonical digest and stable ordering;
- accepted/review/excluded partition and exact duration/sample totals;
- 30-minute `MINIMUM_COVERAGE_MET` and 60-minute
  `TARGET_COVERAGE_MET` thresholds without claiming training readiness;
- incremental duplicate and overlap handling;
- exact current isolated-mic requirement; mixed/unknown always non-accepted in
  R1 regardless of Owner review;
- missing/stale/mismatched Asset, transcript, VoiceProfile, consent, rights,
  quality, label, policy or Dataset binding;
- silence, clipping, low SNR, other-speaker, BGM/game audio and privacy/secret
  exclusions;
- owner exclusion overrides otherwise eligible facts;
- prior-Dataset-wins dedupe, stable overlap tie-break and operation/idempotency/
  expected-head binding; authoritative replay remains Dataset-owner scope;
- absolute/UNC/private path, transcript text and raw body leakage rejection;
- `dataset_mutation_authorized=false`, `training_authorized=false`,
  `model_load_started=false`, `provider_execution_started=false` always;
- compatibility fixture mapping accepted candidates to the existing
  `VoiceDatasetMembershipEntry` requirements without issuing a canonical
  Membership record or Dataset commit. This mapping exists only in focused test
  evidence; Unit A exposes no Membership-producing API;
- production/Owner-audio self-assertion rejection;
- encrypted source/transcript/training custody receipt missing/mismatch;
- Dataset-head-bound fingerprint index omission, overflow or mismatch;
- source/training Asset ID, revision reference, revision digest or checksum
  collision and normalization sample-map mismatch;
- repeated training Asset ID/revision reference/revision digest/checksum cannot inflate coverage;
- exact Transcript Asset/manifest/range digest binding, terminal folder/index/
  media currentness, and generic public projection synthetic-boundary retention;
- direct folder-state vectors: `STALE`/`UNAVAILABLE` exclude, while a wholly
  `UNKNOWN` state remains review-required;
- closed reason vocabulary and typed-ID path/URI smuggling rejection.

## Acceptance and gates

Unit A is commit-ready only after syntax/static checks, focused positive and
negative tests, TASK-046 targeted regressions, independent Critic, independent
Tester, independent Judge, diff/scope review and zero Critical/High findings.

The following remain parked Human/effect Gates: local folder I/O, private path
persistence, private audio copy/read, FasterWhisper execution, ffmpeg
conversion, Dataset mutation, training, model load/inference, playback, native
UI operation, paid/cloud/provider call, Release, Deploy and Production
Activation. A gate blocks only its effect; it does not weaken contract
validation or authorize another task's shared path.
