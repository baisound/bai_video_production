# TASK-046 / P-VS-4B — OBS-to-Model-to-Narration WAV Vertical Slice R0

## Decision

The primary deliverable is an end-to-end vertical slice that turns reviewed OBS
voice recordings into an approved local model and then into one natural,
style-aware narration Master WAV.  The Owner-requested beginner client is the
test and acceptance tool for that slice; it is not the final product goal.

This integration slice belongs to `TASK-046`, while final narration rendering
ownership remains in `TASK-014`.
`TASK-014` consumes an already admitted VoiceProfile/ModelCandidate to render
narration.  `P-VS-4B` is the vertical-slice integration and acceptance surface
over the following canonical owners:

1. `TASK-047` records WAV and capture Evidence.
2. `TASK-048` supplies calibration and acoustic-quality Evidence.
3. `TASK-003` owns AssetRevision truth.
4. `P-VS-3B` owns Dataset review, adoption and TrainingInputSnapshot truth.
5. `P-VS-4A` owns TrainingRun, checkpoint, ModelCandidate and evaluation truth.
6. `P-VS-4B` composes the workflow, style-Cue/Master lineage and test client,
   and validates external receipts.  It does not create a second Dataset, Job,
   Model, Consent or Asset truth.
7. `TASK-014` may bind an Owner-approved candidate for local narration only
   after its independent render-admission Gate.

This design adds the vertical slice, its test client and installer to the
roadmap immediately after P-VS-4A and before P-VS-5.  It does not claim that
training or narration has run, that a model has been created, or that a Master
WAV is accepted for publication.

## Priority outcome

The first complete acceptance path is deliberately narrow:

1. record the Owner in OBS with start/pause/resume/stop and immutable capture
   Evidence;
2. review exact WAV ranges and adopt only approved material into a Dataset;
3. freeze one `TrainingInputSnapshot` and run one exact admitted training
   recipe with durable checkpoint/reconciliation;
4. register, evaluate and explicitly approve one `ModelCandidateRevision`;
5. take one approved narration script whose style plan contains multiple
   ordered style segments;
6. render each segment with the same approved speaker/model lineage and exact
   style direction;
7. assemble one canonical 48 kHz Master WAV; and
8. pass automatic boundary checks plus an Owner listening acceptance.

The Master is not a naïve concatenation.  The assembly contract binds segment
order, source Cue hashes, measured sample ranges, pause policy, gain/loudness
continuity, sample format, optional bounded crossfade, speaker-similarity
continuity and boundary artifact results.  A failed segment may be regenerated
as a new Cue revision without silently changing its neighbours.  If an engine
cannot express a requested style or the analyzer/policy is unavailable, that
style/whole-Master decision is `UNKNOWN` or `FAIL`, not synthetic PASS.

## Beginner test-client workflow

The client uses one guided screen per decision and keeps advanced identifiers
behind a details disclosure.

1. **Choose recordings** — select a known OBS capture session or reviewed
   Asset set.  The default picker does not crawl a drive and never treats every
   WAV in a directory as approved training data.
2. **Check the recordings** — show format, unique duration, clipping/dropout,
   calibration, quality and missing-Evidence states.  `UNKNOWN` is displayed as
   “Not checked”, never as zero or PASS.
3. **Review the Dataset proposal** — list included/excluded clips, duplicate or
   overlapping ranges, consent/rights state and the exact immutable snapshot.
   The Owner explicitly confirms Dataset adoption.
4. **Choose a training recipe** — display engine, base model, exact revision,
   artifact kind, license, mode, target hardware and probe result.  A recipe is
   selectable only when its exact engine-supported recipe and mode-specific
   resource Evidence are verified.
5. **Review the run** — show Dataset hash, estimated disk/time when measured,
   output destination, checkpoint policy and what remains private.  No raw
   path, credential or voice-linkable digest appears in public metadata.
6. **Start training** — require a fresh Owner Human Gate bound to this run.
   The UI submits an external durable-job request; it does not forge a boolean
   authorization and it does not infer success from a process or file.
7. **Monitor safely** — show queued/running/checkpointed/paused/stopped/unknown
   separately.  A crash or unobservable GPU process becomes `UNKNOWN`; the
   client reconciles before allowing a new run and never auto-replays.
8. **Register the output** — training completion, artifact persistence,
   verified artifact binding and ModelCandidate registration are separate
   receipts.  An unbound checkpoint or model is never shown as usable.
9. **Evaluate and approve** — evaluation uses a separately authorized held-out
   EvaluationInputSnapshot.  The Owner may approve, reject or request retest.
10. **Generate a style test** — select a short approved script containing at
    least two style segments, render separate immutable Cue revisions and show
    their exact order and boundary policy.
11. **Listen to one Master WAV** — assemble a contained 48 kHz candidate and
    show join, silence, level, identity and style QA separately.  Owner
    acceptance is required before it can become a canonical narration Asset.
12. **Use for narration** — linking to VoiceProfile/TASK-014 is another Gate.
    It does not publish, deploy, or automatically replace the active model.

## Required client states

The user-facing state is derived from canonical receipts and cannot be edited
directly:

- `RECORDINGS_NOT_SELECTED`
- `RECORDINGS_REVIEW_REQUIRED`
- `DATASET_PROPOSAL_READY`
- `DATASET_ADOPTION_BLOCKED`
- `TRAINING_RECIPE_NOT_VERIFIED`
- `READY_FOR_OWNER_TRAINING_CONFIRMATION`
- `QUEUED`, `RUNNING`, `CHECKPOINTED`, `PAUSED_SAFE`, `STOP_REQUESTED`
- `TRAINING_COMPLETED_ARTIFACT_UNBOUND`
- `MODEL_CANDIDATE_REGISTERED`
- `EVALUATION_PENDING`, `EVALUATED_CANDIDATE`
- `OWNER_APPROVED`, `OWNER_REJECTED`, `RETEST_REQUIRED`
- `STYLE_CUES_PENDING`, `MASTER_ASSEMBLY_PENDING`, `MASTER_REVIEW_REQUIRED`
- `MASTER_ACCEPTED`, `MASTER_REJECTED`
- `UNKNOWN`, `FAILED_KNOWN`, `CANCELLED_SAFE`

UI labels may be friendly Japanese/English text, but serialized values remain
closed and exact.  “100%”, “95%”, “completed”, “ready” and “usable model” are
not shown unless their canonical policy and Evidence support that exact claim.

## Installer contract

The completed feature ships with a beginner-oriented Windows installer.  The
installer is a separate signed/release candidate from the OBS Plugin installer
and follows these rules:

- installs the Model Builder client, its versioned application files, schema
  resources, launcher and Japanese/English help;
- shows required disk space and optional model/runtime downloads before any
  acquisition;
- pins every bundled or acquired runtime/model by version, bytes, SHA-256,
  source and license Evidence;
- uses contained application, model-cache, job, checkpoint and log roots;
- rejects reparse traversal and unknown existing-target disposition;
- never bundles Owner WAV, Dataset, checkpoint, model output, credentials or
  absolute private paths;
- never starts training, downloads a model, launches OBS or changes device
  settings merely because installation succeeded;
- preserves user recordings, Datasets, checkpoints and models on uninstall by
  default; deletion is a separate, explicit retention action;
- provides repair/rollback receipts and does not claim rollback from a partial
  or unknown transaction without read-back;
- includes an offline manifest and integrity-verification command;
- is linked from `README.md` and from a Japanese/English beginner guide before
  any public Release candidate is approved.

The R0 packaging candidate is expected to use the repository's established
Windows packaging conventions, while retaining a distinct product/component
identity from `bai-voice-capture`.  Installer creation does not itself authorize
GitHub Release, Deploy, Production activation or model redistribution.

## Qwen3-TTS technical probe captured for planning

The current isolated target-machine probe is suitable only as local inference
feasibility Evidence:

- engine package: `qwen-tts==0.1.1`;
- model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`;
- immutable model revision:
  `5d83992436eae1d760afd27aff78a71d676296fc`;
- runtime: Python 3.12.4, PyTorch `2.11.0+cu130`, torchaudio
  `2.11.0+cu130`;
- GPU: NVIDIA GeForce RTX 4070 SUPER, 12,878,086,144 bytes reported VRAM;
- model load without inference: PASS;
- load peak allocated: 2,175,147,520 bytes;
- load peak reserved: 2,306,867,200 bytes;
- model or audio generation: not run by this probe;
- full/PEFT/LoRA training feasibility: `UNKNOWN / PROBE_REQUIRED`.

The official repository contains fine-tuning material, but current public
reports show unresolved 0.6B recipe compatibility problems.  Therefore the R0
client must not enable Qwen3-TTS 0.6B training merely because inference load
passed.  An exact official recipe revision, successful representative step,
optimizer/checkpoint overhead, peak VRAM/RAM, thermal/disk floor, recovery and
expected duration are all required per training mode.  One mode's PASS cannot
be reused for another mode.

## Implementation sequence

### Gate 1 — P-VS-3B pure contract

Implement the previously accepted body-free VoiceDatasetStore,
TrainingInputSnapshot and CommitIntent/Revision/Receipt/Envelope DAG contract.
No Dataset/store mutation or canonical receipt issuance is included.

### Gate 2 — P-VS-4A pure contract

Implement TrainingRun, checkpoint/artifact binding, ModelCandidate,
EvaluationInputSnapshot/Receipt and OwnerModelApprovalDecision metadata.  No
Job, reservation, GPU, training, merge or publication effect is included.

### Gate 3 — P-VS-4B vertical-slice application service

Implement a pure application/service layer that composes Gate 1, Gate 2 and the
TASK-014 render-admission contract, projects beginner-friendly states and
produces exact external-operation requests.  It also defines immutable style
Cue order and Master assembly/QA bindings.  It may not access a WAV body or
execute training/rendering in unit tests.

### Gate 4 — bounded runtime adapter

Implement contained WAV inspection, Dataset preparation, an engine adapter and
style-Cue/Master assembly only for exact admitted recipes.  Dataset adoption,
training start, model approval, narration render and Master acceptance retain
separate Owner Gates.  Runtime acceptance uses synthetic/non-Owner audio until
an explicit Owner recording/training/render Gate is reached.

### Gate 5 — Windows test client and installer

Package the standalone client, Japanese/English guide and offline manifest.
Only after the standalone workflow is accepted may a later successor Shell
revision embed the same application service in BAI Video Production.  This
avoids overlapping the current TASK-036 Shell work.

## Acceptance negatives

The following must fail closed:

- arbitrary WAV folder automatically becomes a Dataset;
- OBS capture success automatically starts training;
- duplicate/overlapping ranges inflate duration or readiness;
- post-filter/RX audio is labeled raw capture;
- missing transcript, Consent, rights, license or Asset mapping is treated as
  PASS;
- a short inference load is treated as 12 GB training feasibility;
- 0.6B training is enabled from an unresolved/community-only recipe;
- checkpoint path or hash alone enables resume;
- orphan GPU process causes automatic retry or duplicate run;
- adapter artifact is displayed as a standalone full/merged model;
- completed training is displayed as approved, production-bound or published;
- different style Cues silently use different ModelCandidate/VoiceProfile
  revisions;
- style Cues are concatenated without measured pause, level, identity and
  boundary-artifact checks;
- successful Cue renders are treated as an accepted natural Master WAV;
- installer contains voice audio, model output, credentials or private paths;
- uninstall silently deletes recordings, Dataset, checkpoints or models;
- install success launches training or changes OBS/device configuration;
- public UI leaks low-count labels, item hashes or voice-linked provenance.

## R0 Judge

- Task placement: `TASK-046/P-VS-4B`, after P-VS-4A and before P-VS-5 — PASS.
- TASK-014 boundary: consumer-only — PASS.
- Primary outcome: OBS recording → trained ModelCandidate → multi-style Cue
  renders → one natural 48 kHz Master WAV — fixed.
- Client/installer role: acceptance tool subordinate to the vertical slice.
- Standalone-first overlap with current TASK-036 Shell work: zero by design.
- Qwen3-TTS inference load evidence: PASS, training admission remains UNKNOWN.
- Installer requirement: accepted and mandatory before public client Release.
- Dataset mutation/training/model approval/narration/publication authority:
  not granted by this design.
- Residual Critical/High: `0 / 0`.
