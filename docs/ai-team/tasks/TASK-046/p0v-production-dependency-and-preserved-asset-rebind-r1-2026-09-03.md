# TASK-046 P0V production dependency and preserved-asset rebind R1

## Status and authority

- Active Project: BAI VIDEO PRODUCTION.
- Atomic Unit: `TASK-046 / P0V-PRODUCTION-DEPENDENCY-REBIND-R1`.
- DEV profile: `DEV-4 FOUNDATION CRITICAL`.
- Bound current base: `origin/main@b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`.
- Voice-scope source snapshot: `4e150c17f3cd2fe9398d75518473dc8428fae322`;
  the intervening main delta changes only TASK-036 launcher tests.
- State: design and read-only preservation audit only.
- Owner intent: shortest path from an OBS Owner-microphone capture to a
  speech-continuous training WAV, reviewed Dataset, sealed voice model and local
  narration WAV in the unified Product.

This document creates no production, private-audio, model-load, training,
provider, native, Release or Deploy authority. It does not make a diagnostic
receipt authoritative.

## Allowed files for this design batch

Only the following new task-local documents may be changed:

1. this document;
2. `docs/ai-team/tasks/TASK-047/p0v-capture-format-terminal-receipt-r1-design-2026-09-03.md`;
3. `docs/ai-team/tasks/TASK-048/p0v-quality-finishing-preserved-rebind-r1-2026-09-03.md`.

Shared current state, task index, roadmap, CHANGELOG, Product source, schemas,
tests and preserved worktrees are prohibited in this design batch.

## Current-main facts

Canonical main records TASK-047 capture as a hosted technical foundation and
TASK-048 P-QC-1A/1B as hosted metadata/gain-admission foundations. It explicitly
does not confirm production recording, encrypted private-audio custody,
canonical quality receipt issuance, Dataset adoption, Training, model approval,
Master WAV or production use.

The current TASK-047 controller writes RIFF/WAVE format tag 3, float32, with the
callback plane count and a hard-coded 48 kHz header. Its terminal capture receipt
contains a filename, byte/hash and transport counters but not authoritative
format, source-rate, channel-selection, sample-map, acoustic measurements or
capture-chain currentness. The live meter and five-second gain receipt are useful
observations but are not a final quality authority.

## Preserved implementation inventory

| Preserved asset | Exact identity | Current-main relation | Rebind decision |
|---|---|---|---|
| TASK-046 Quick Clone recovery R3 | merge `4e150c1`; implementation `2bcf859`; metadata `f95ab55`; exact8 source/schema/test plus shared CHANGELOG | landed on current main through PR #513 | canonical central-model read-only UI/lifecycle/restart/readback contract; it is not a model worker or training path, and no preserved R1/R2/alternate branch may be replayed in parallel |
| TASK-046 Quick Clone historical alternatives | R2 tip `948f9ef`; coherent merge `831ea764` | superseded by current-main R3 and retained only as history | do not integrate, select, merge or treat as a second model selector |
| TASK-073 reference-binding A | tip `d58c3ea`; exact3; historical merge-base `4d233c8` | not on bound main `b7b2f33`; standalone patch does not apply because it depends on predecessor work | preserve its nominal TASK-046/TASK-014 binding pattern only; a fresh-current successor must re-author it against Q1/Q2/Q3 receipts rather than merge/rebase the old branch |
| TASK-073 local-WAV composition V4 | staged exact4 on base `d1c41e2`; patch applies textually to current main | not committed or reviewed independently | preserve fixed-slot/topology/currentness ideas only; receipt names and owners must be regenerated from landed producer ABIs |
| TASK-075 R7 correction proposal | tip `3cbdf21`; design-only | not on main | supplement for playback/listening, failure totality and phase separation; creates no producer or implementation authority |
| TASK-078 E-C downstream design | `e549e13`; PR #495 design | not on main | out of the Owner-voice WAV/training critical path; retain only as unrelated downstream video design |
| TASK-014 synthetic executor | `9d52e923a216bc11b7ecba4004dd63951657aab3`; exact2; historical base `4d233c8` | not on bound main `b7b2f33`; ahead 1/behind 6 with no exact-path collision; current-main successor recovery is separately owned | consume only after that successor lands; it remains synthetic and satisfies no production producer, compute, Human, custody, model-load or result-adoption dependency |
| TASK-046 OBS intake synthetic Unit A | `c918d5ca95f0aa920ffd0e782928f832d6b94d99`; exact3; historical base `4d233c8` | pushed task branch, not on bound main `b7b2f33`; fresh patch/currentness revalidation required | recover only through a fresh-current successor as `SYNTHETIC_CONTRACT_TEST`; it rejects Owner audio and cannot be called by the production Q3 producer |
| TASK-048 P-QC-P0V-FINISH-1 | immutable commit `3361023bab02bf2d7a593231ccc81ba6b2d0b9b3`; exact3; historical parent/base `4d233c8` | HEAD remains `3361023`, ahead 1/behind 6 and not on bound main `b7b2f33`; the owner worktree now has concurrent unstaged exact3 edits, which this unit preserves and does not inspect as authority | coherent-integration candidate is the committed `3361023` snapshot only; local rerun 156/156 PASS and independent C/H/M/L 0/0/0/0 apply to that commit, while later dirty bytes and native/audio remain NOT_CONFIRMED |

Apart from the Quick Clone R3 already merged by PR #513, no preserved branch is
merged, rebased or copied wholesale by this unit. Staged composition bytes and
every remaining branch-only commit remain with their original owners.

## Current-main authority-zero integration acceptance

The landed Quick Clone R3 public flow/readback is deliberately authority zero:
`task014_result_admission_producer_state=NOT_BOUND`, `model_loaded=false`, no
Product result, and no audio-body persistence. TASK-048 fixture receipt/hash and
calibration projections are likewise validation evidence only. Before both an
accepted exact TASK-014/TASK-046 owner amendment and a sealed, current
`BOUND_VERIFIED` real-producer receipt arrive, every Product flow revision must
remain `DRAFT` or `PREFLIGHT_BLOCKED`. Neither arrival is inferred from a field
flip, branch history, fixture, callable presence or successful local test.

The coherent voice-line integration must reject these N1-N7 vectors:

- **N1 — producer-state forgery:** the current R3 type/public readback reports a
  producer state other than `NOT_BOUND`, or a caller substitutes an unaccepted
  producer-bound subtype/amendment;
- **N2 — premature transition:** execution moves beyond `DRAFT` or
  `PREFLIGHT_BLOCKED` while the exact owner amendment or sealed
  `BOUND_VERIFIED` producer receipt is absent, stale, revoked or mismatched;
- **N3 — effect/result forgery:** `model_loaded`, `product_result_bound`, staged
  Product WAV, listening, profile/Asset adoption or audio-body persistence is
  asserted while producer state remains unbound;
- **N4 — fixture promotion:** TASK-048 fixture receipt/hash/calibration,
  synthetic Quick Clone request/output/readback, or diagnostic PASS is accepted
  as Product quality, admission, custody, currentness or result authority;
- **N5 — owner/amendment mismatch:** a receipt from the wrong Task/owner,
  schema/version, Product route or capability is used to satisfy the exact
  TASK-014/TASK-046 amendment and real-producer seam;
- **N6 — identity/replay mismatch:** operation, Job/generation, route, model,
  runtime/code, VoiceProfile/OwnerSubject, admission, output hash/format or
  replay=false binding differs anywhere across request, producer receipt and
  readback;
- **N7 — unsealed/non-current result:** a partial, self-attested, duplicate,
  replayed or lost-reply result bypasses the required TASK-076 candidate,
  TASK-068 immutable publication/readback, TASK-043 CAS/current readback and
  later Human/TASK-003 adoption sequence.

## Canonical non-cyclic dependency graph

There are two separate lanes. Inference authority never retroactively authorizes
training, and capture transport never aliases inference custody.

### Training and artifact lane

0. **P0 / TASK-048 meter-display policy — currently NOT_BOUND.** A future exact
   policy producer may supply a current display-only target/warning/true-clip
   threshold revision before capture. It consumes no Q1 audio and issues no
   quality PASS, so there is no Q1/Q2 cycle. Absence does not block capture
   transport start or emergency stop, but the UI must suppress target/readiness
   labels, show `適正判定 未確定`, and must not claim quality-targeted readiness.
1. **Q1 / TASK-047 — capture truth, encrypted custody and canonicalization.** A
   terminal source receipt, actual native format, TASK-047-owned
   callback-to-worker `CaptureTransportIntegrityReceiptV2`, capture-chain
   currentness, and staged `PCM_S24LE/48000/mono` bytes must exist. Raw and
   canonical private staged objects each bind a separately authorized
   secure-custody receipt. Only a separately authorized TASK-003 Asset
   sink/registration/adoption and canonical readback may turn either staged
   object into a canonical Product Asset; TASK-047 cannot mint that truth. No
   current Task is accepted here as the secure-custody owner, and no exact
   capture-Asset adoption ABI is landed:
   `PRIVATE_MEDIA_CUSTODY_OWNER_NOT_ALLOCATED` is a hard START blocker until an
   existing canonical owner is proven or a new bounded owner is allocated;
   `TASK003_CAPTURE_ASSET_ADOPTION_READBACK_NOT_BOUND` is a separate START
   blocker. TASK-047 owns neither encryption keys nor a new Asset store.
2. **Q2 / TASK-048 — quality, processed custody and conservative finishing.**
   Current room/session and segment quality plus speech-continuous finishing bind
   the exact TASK-003-read-back Q1 canonical Asset/range. The processed private
   staged object and one distinct engine-format training-copy staged object each
   have their own secure-custody receipt, then require separate TASK-003 Asset
   adoption/readback before Q3 may consume them. TASK-048 is the sole producer of
   the training copy. Unknown is never PASS, and TASK-048 cannot self-mint a
   canonical Asset. Q2 additionally requires a current closed-purpose
   `OWNER_VOICE_DATA_PREPARATION` Consent/use-rights evaluation bound to the same
   OwnerSubject revision, exact Q1 Asset lineage, the allowed
   `QUALITY_FINISHING` and `TRAINING_COPY_CREATION` operations, output purposes,
   decision=`ALLOW`, policy revision, expiry and revocation currentness.
3. **Q3 / TASK-046 — production private ingest and Dataset proposal.** Folder
   discovery, canonical Transcript identity, segment review, fingerprint dedupe
   and Dataset proposal bind the exact TASK-003-read-back Q2 processed and
   training-copy Assets. Q3 consumes but never creates, converts, custodies or
   adopts the training copy. Production requires a new nominal ABI and validator
   with explicit authority ingress; it must not call, patch or relabel the
   `SYNTHETIC_CONTRACT_TEST` Unit A from branch `c918d5ca`. Q3 must consume the
   same current data-preparation evaluation with the separately enumerated
   `TRANSCRIPT_DERIVATION` and `DATASET_CANDIDATE_PROPOSAL` operations and bind
   it into the Transcript/proposal receipts. This scope grants neither Dataset
   Membership adoption nor training execution.
4. **Q4 / TASK-046 — Human adoption and training snapshot.** Only the Dataset
   owner may commit Membership, advance the Dataset head and issue an exact
   `TrainingInputSnapshot`. Q1-Q3 never issue these records.
5. **TASK-046 training START.** Existing `voice_training_run.py` boundaries
   require an exact `TrainingRunIntent`/preflight, a distinct
   `TrainingDurableJobBinding`, live `ExecutionResourceReservationBinding`, and
   one-shot `TrainingExecutionAuthorizationBinding` before a
   `TrainingDispatchAdmissionReport` may admit execution. These bind the Q4
   snapshot, recipe, runtime/code, backend/device, expiry and recovery policy;
   they are not the TASK-066 narration inference capability. Evaluation and
   model approval are downstream and are not prerequisites for training START.
   The actual training engine/worker/checkpoint producer is currently
   `TASK046_TRAINING_ENGINE_ADAPTER_NOT_BOUND`. The canonical 0.6B official
   representative recipe remains `FAILED_KNOWN / BLOCKED`; a diagnostic probe,
   installed package or unmerged upstream recipe cannot change that state.
   TASK-043 must supply the distinct current `VOICE_MODEL_TRAINING` durable
   Job/head behind `TrainingDurableJobBinding`. A system-wide training compute/
   resource reservation owner is not allocated, so
   `TRAINING_COMPUTE_RESOURCE_OWNER_NOT_ALLOCATED` blocks a live
   `ExecutionResourceReservationBinding`.
6. **TASK-046 compute terminal and artifact registration.** The durable training
   Job owns checkpoint/restart reconciliation. Completion must produce a
   `TrainingComputeTerminalReceipt`; UNKNOWN/failed/cancelled results remain
   non-promotable. Only a successful current terminal may register a sealed,
   atomically persisted and read-back `ModelArtifactBinding`. The encrypted model
   artifact destination/currentness owner is not allocated:
   `MODEL_ARTIFACT_CUSTODY_OWNER_NOT_ALLOCATED` blocks a current
   `OutputArtifactDestinationBinding` and artifact registration.
7. **TASK-046 candidate, evaluation and Owner approval.** A
   `ModelCandidateRevision` binds the exact terminal and `ModelArtifactBinding`
   and remains non-selectable. A held-out `EvaluationReceipt` bound to the exact
   TrainingSnapshot/artifact/runtime, safety and voice-identity review, followed
   by a current `OwnerModelApprovalDecisionBinding`, must PASS/APPROVE. TASK-014,
   not TASK-046 or TASK-074, owns the body-free `FineTunedModelBinding` admission
   seam that consumes the Dataset revision, TrainingInputSnapshot,
   ModelCandidateRevision, ModelArtifactBinding, Owner approval and current
   Consent/rights. Reject/retest/revoke/stale keeps the candidate quarantined.

### Narration inference and result lane

8. **Discriminated route selection before arm.** The request is exactly one of
   `ZERO_SHOT_REFERENCE` or `FINE_TUNED_MODEL`, never both. Zero-shot binds one
   current TASK-074 reference. Fine-tuned binds the current
   VoiceProfile/ModelCandidate coordinate that can satisfy TASK-014
   `FineTunedModelBinding` and must prove reference attachment/roles/lease absent
   plus reference read count zero before any ticket/arm. Neither route loads a
   model. Their identities never collapse even when a text model ID is equal.
   Current `VoiceProfile` requires provider credential/private voice fields and
   cannot represent a local fine-tuned profile; a versioned TASK-014 evolution is
   `TASK014_LOCAL_VOICE_PROFILE_BINDING_NOT_BOUND`.
9. **TASK-066 GF-C narration compute.** The current `audio.voice.local` desktop
   policy is `DISABLED_UNTIL_MAPPED`. A private OS-backed one-use broker
   capability binds narration workload, backend, device/profile,
   process/runtime and expiry. Public probes remain advisory.
10. **TASK-071/TASK-072 Human plan/ticket.** Missing producers issue current
   confirmation and one non-replayable narration operation ticket. TASK-074
   fixtures cannot substitute.
11. **TASK-014 pre-execution call/sink capabilities — currently NOT_BOUND.** Current main
    contains preflight/render admission but no landed production callable/result
    producer. `TASK014_CALLABLE_RESULT_PRODUCER_NOT_LANDED` remains a START
    dependency. Before child release, TASK-014 alone may issue the exact live call
    and `NARRATION_OUTPUT_SINK_CAPABILITY_V1`; it must not begin the sink session
    yet. Neither capability exposes a destination path or authorizes a completed
    WAV/result.
12. **TASK-076 candidate, TASK-068 publication and TASK-043 currentness.** TASK-076
    validates exact DISPATCHING/IN_FLIGHT immutable Job candidates; TASK-068
    publishes and reads back their pinned immutable bytes; TASK-043 alone
    CAS-selects each exact candidate and returns fresh Project/current-Job readback.
    For `ZERO_SHOT_REFERENCE`, after selected DISPATCHING TASK-074 creates the
    exact begin attachment before TASK-072 arms the child. For
    `FINE_TUNED_MODEL`, attachment/roles/lease must instead be `ABSENT_PROVEN`
    before arm. TASK-043 then selects IN_FLIGHT and bootstrap/process/Job custody
    and network readbacks must pass. Only zero-shot lets TASK-074 transfer its
    reference pair directly to the child-local broker; fine-tuned retains
    reference read count zero. External binding validation passes,
    and the one-winner artifact-prepare claim is current. Only that winner may
    begin TASK-014 call dispatch and the sink write session; prepare commit and
    attach/release must complete before body read/model load/inference. TASK-076
    owns candidate construction/validation and custody, not publication,
    selection or audio semantics.
13. **TASK-075 execution, reference closure and TASK-014 result/POST.** Contained
    execution consumes steps 8-12. TASK-075 owns the authenticated parent/worker
    protocol, strict PCM24 frame grammar and sequence/MAC validation, and streams
    only into the live TASK-014 sink. The causal order is child terminal, sink
    finish/private staged-WAV receipt, `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1`,
    TASK-014 live `RESULT_BOUND`, exact
    `TASK074_REFERENCE_WORKER_REMOTE_CLOSE_PROOF_V1` plus Task074 lease terminal
    (`CONSUMED` or fail-closed `BURNED`/`FAILED_CLOSED`), then TASK-014 durable
    POST. A partial/aborted sink or nonterminal reference lease creates no
    successful POST. A fine-tuned route must instead prove reference-not-required
    and reference read count zero.
14. **TASK-076 terminal candidate plus TASK-043 CAS.** Only after the exact
    TASK-072 child terminal, TASK-075 execution result, TASK-014 durable POST and
    applicable TASK-074 remote-close/lease terminal are current may TASK-076
    validate the terminal candidate and TASK-068 publish/read back its pinned
    immutable bytes. TASK-043 alone CAS-selects it against the same current Job
    generation and returns fresh readback. Operation/
    generation mismatch, duplicate terminal, reply loss or replay fails closed.
15. **Human listening and TASK-003 Asset adoption.** Playback and Owner listening
    are separate TASK-075/TASK-041 observations. Only a separate current Human
    adoption decision and TASK-003 Asset sink/registration/readback may create a
    canonical `AUDIO` Asset; the staged narration output is never itself
    canonical adoption.

No later step may infer or mint a missing earlier receipt. The TASK-014
synthetic worker stays a test-only fake backend and must not acquire Dataset,
store, model-load or training authority.

TASK-047 owns only OBS callback-to-capture-worker transport authentication.
TASK-075 owns narration worker authentication and PCM semantics. TASK-076 owns
only immutable Job candidate construction/validation and exact child/process/Job custody;
TASK-068 owns immutable publication/readback, and TASK-043 owns Project/current-
Job CAS selection/readback. Their operation IDs,
HMAC key epochs, receipts and replay domains are non-aliasing; none is a
substitute for another.

Current TASK-075 enables only `ZERO_SHOT_LOCAL / PREVIEW`. Fine-tuned or full
render remains `TASK014_TASK075_FINE_TUNED_FULL_RENDER_ABI_NOT_BOUND` until a
separately accepted versioned TASK-014/TASK-075 amendment exists. Training
success does not bypass that execution dependency.

## TASK-046 phase gates

### Training START gate

Training execution remains `NOT_BOUND` until all of the following are current
and exact:

- Q1 TASK-003-read-back canonical capture Assets, format, chain and terminal
  receipts;
- Q2 TASK-003-read-back canonical processed and training-copy Assets plus
  segment-quality and speech-continuous finishing receipts;
- Q3 Transcript identity and production intake receipt over those exact Q2
  Assets;
- encrypted private raw/canonical/processed/transcript/training-copy custody,
  including key availability, retention, revocation/delete policy and current
  custody receipts;
- current canonical OwnerSubject binding plus separate current Consent/use-rights
  evaluations for the closed `OWNER_VOICE_DATA_PREPARATION`,
  `OWNER_VOICE_DATASET_ADOPTION` and
  `OWNER_VOICE_MODEL_TRAINING` scopes. Each evaluation must bind the same opaque
  subject/revision, decision=`ALLOW`, policy revision, expiry and revocation
  currentness. The Q1 `OWNER_VOICE_CAPTURE` evaluation cannot satisfy either
  later scope, and data preparation cannot satisfy Dataset adoption or training;
- Human-reviewed Dataset Membership and current Dataset head;
- one exact `TrainingInputSnapshot` that cross-binds the same OwnerSubject,
  Dataset-adoption Consent/use-rights evaluation and adopted Asset lineage, plus
  recipe digest and deterministic split;
- model license, runtime/code digest, hardware policy and output format contract;
- an exact official compatible recipe revision, successful synthetic
  representative-step admission and a separately implemented TASK-046 training
  engine/worker/checkpoint/terminal adapter; current 0.6B recipe remains
  `FAILED_KNOWN / BLOCKED`;
- `TrainingDurableJobBinding`, live `ExecutionResourceReservationBinding`,
  one-shot `TrainingExecutionAuthorizationBinding` and PASS
  `TrainingDispatchAdmissionReport` that do not alias narration inference
  authority. `TrainingRunIntent`, its versioned current-use-rights binding, the
  authorization binding and dispatch admission must all cross-bind that exact
  snapshot, OwnerSubject revision and current
  `OWNER_VOICE_MODEL_TRAINING` evaluation. The landed `TrainingInputSnapshot`
  and `CurrentUseRightsBinding` lack the complete subject, closed-purpose,
  policy-revision, expiry and revocation coordinates required for this chain, so
  versioned amendments are START dependencies rather than permission to infer
  them.
- a fresh TASK-043 `VOICE_MODEL_TRAINING` Job/head readback; the Dataset adoption
  Job identity cannot be reused;
- a current `OutputArtifactDestinationBinding` from an allocated encrypted model-
  artifact custody/currentness owner. Both the training compute/resource owner
  and model-artifact custody owner are currently unallocated hard blockers.

### Compute terminal and candidate-registration gate

Artifact registration requires the same durable Job/run lineage, current
checkpoint/recovery evidence, a successful `TrainingComputeTerminalReceipt`,
atomic/no-clobber publication, sealed hash, inventory readback and a
`ModelArtifactBinding`. UNKNOWN, failed or cancelled compute cannot register a
`ModelCandidateRevision`.

### Evaluation and selectable-binding gate

Selection requires a current `ModelCandidateRevision`, exact held-out
`EvaluationReceipt`, safety/voice-identity review and explicit
`OwnerModelApprovalDecisionBinding`. Only then may TASK-014 admit a body-free
`FineTunedModelBinding`; an unevaluated/retest/rejected/revoked/stale candidate
remains quarantined.

Fine-tuned and zero-shot identities must remain distinct even if a model ID is
textually equal. Missing, stale, revoked or mismatched artifacts are not
selectable. Inventory, selection and readback perform no download, process
start, model load or inference.

## UI flow

The unified Product presents one progressive flow:

`録音設定` -> `録音` -> `品質確認` -> `発話連続WAVを確認` ->
`Dataset候補を確認` -> `学習開始を確認` -> `学習中／復旧確認` ->
`モデル候補を評価` -> `Owner承認` -> `モデルを選択` ->
`ナレーション生成` -> `試聴`.

Each screen shows `未確認`, `確認が必要`, `準備完了`, `失敗` or `取消済み`
from canonical readback. Folder selection, capture completion, quality PASS,
Dataset adoption, training, candidate registration, evaluation, Owner approval,
model selection and inference are separate actions. An unevaluated or unapproved
candidate is visibly quarantined and cannot be selected. Required held-out and
30/60-minute narration-coverage observations show `未確認`/`UNKNOWN` and the next
action until their current policy is satisfied; missing coverage is never PASS.
There is no Voice-side duplicate model selector; central AI settings remain the
read-only model source.

## Required negative and fault vectors

- raw float32 or multichannel bytes presented as PCM24/mono;
- hard-coded 48 kHz without observed input-rate evidence;
- missing/mismatched terminal, format, capture-chain, sequence, HMAC or custody;
- TASK-047 capture-transport receipt presented as TASK-075 narration-worker
  transport or TASK-076 durable Job custody, or the reverse;
- stale/revoked/expired or non-ALLOW Consent, rights, VoiceProfile, Dataset head
  or TrainingSnapshot;
- arbitrary/stale OwnerSubject, wrong-subject Consent, wrong-purpose Consent
  (including capture Consent reused for preparation/adoption/training or
  preparation Consent reused for adoption/training), missing allowed-operation
  binding, policy-revision mismatch, or provider-shaped profile used to
  authorize initial local training;
- quality UNKNOWN promoted to PASS, missing HVAC/session/segment identity, or
  dBFS mislabeled as SPL/dBA;
- raw and processed Asset identity collapse, lossy input, in-place overwrite,
  partial output visibility or all-silence promotion;
- duplicate fingerprints, overlapping ranges, replay, operation mismatch or
  double-counted Asset identities;
- diagnostic/fixture receipt promoted to Product, model artifact or authority;
- equal text model IDs collapsing zero-shot and fine-tuned identities;
- route union with both/neither arm, fine-tuned attachment/role/lease not
  `ABSENT_PROVEN`, or reference read count nonzero;
- compute capability without exact private broker binding;
- unauthenticated PCM metadata, frame count/hash mismatch or durable-job replay;
- TASK-076 candidate self-selected without TASK-043 CAS/current readback, stale
  Project head, orphan candidate, lost CAS reply or terminal replay;
- sink session begun before selected IN_FLIGHT/bootstrap/reference bind/artifact
  prepare, or body/model/inference before attach/release;
- missing/stale/replayed TASK-074 reference remote-close/lease terminal, leaked
  reference handle, or fine-tuned route with nonzero reference reads;
- fine-tuned/full render passed into current ZERO_SHOT/PREVIEW-only TASK-075 ABI,
  or provider-shaped `VoiceProfile` relabeled as local;
- missing TASK-003 adoption/readback or a capture/quality/intake producer minting
  canonical Asset truth itself;
- training start without durable Job/resource/Owner authorization, compute
  terminal replay, checkpoint/recovery mismatch or candidate promotion before a
  successful terminal;
- absolute path, private body, transcript, secret or voice fingerprint in public
  projection/logs.

## Bounded implementation allocation candidates

This design does not start these units. A later start receipt must give a clean
dedicated worktree, sole writer and exact files.

| Candidate | Owner | Scope | START dependency |
|---|---|---|---|
| P0 meter policy | TASK-048 | new exact body-free display-policy producer; no Q1 audio or quality PASS | design/Allowed Files/sole writer allocated; absence suppresses labels but does not block transport capture |
| Q1 capture/canonical receipt | TASK-047 | controller worker, versioned receipt parser, synthetic format vectors | this design accepted; canonical TASK-047 START dependency amended from future local VoiceProfileRevision to current OwnerSubject plus closed-purpose Consent; OwnerSubject/private-custody/trusted-time owners and exact receipts allocated; TASK-043 capture Job and TASK-003 Asset adoption/readback ABIs allocated; no owner overlap |
| Q2 quality/finishing | TASK-048 | adopt or supersede preserved exact3 without changing its frozen bytes | Q1 producer and TASK-003 canonical readback landed; original dirty ownership/freeze resolved; design/Critic/Judge current; Q2 durable transaction/currentness owner and candidate/publication/readback/CAS/reconcile ABI separately allocated—fixture in-memory ledger is never Product proof |
| Q3 production intake adapter | TASK-046 | new nominal production ABI; no call/relabel of synthetic Unit A | Q2 producer and TASK-003 processed/training-copy adoption/readback landed; `c918d5ca` synthetic branch separately reviewed/landed |
| Q4 adoption/snapshot | TASK-046 | existing Dataset owner APIs only | Q3 exact candidate review complete |
| training durable Job/head | TASK-043 | distinct `VOICE_MODEL_TRAINING` currentness behind `TrainingDurableJobBinding` | exact Project/head producer landed; no Dataset-adoption Job identity reuse |
| training compute/resource reservation | owner not allocated | system-wide CPU/GPU/RAM/VRAM/disk/thermal reservation producer | canonical owner allocation and live `ExecutionResourceReservationBinding`; currently hard-blocked |
| training START | TASK-046 | existing `voice_training_run.py` intent/preflight/job/reservation/authorization/admission boundaries | Q4 current snapshot, TASK-043 Job, live resource reservation and explicit Owner training Gate |
| training engine/worker | TASK-046 | new `task046_voice_training_engine_adapter.py`, worker protocol, checkpoint and terminal producer plus schema/mirror/tests | exact official compatible recipe and representative-step PASS; runtime acquisition/download has separate Human Gate; current 0.6B recipe is `FAILED_KNOWN / BLOCKED` |
| artifact/candidate/evaluation | TASK-046 | terminal/recovery, `ModelArtifactBinding`, `ModelCandidateRevision`, `EvaluationReceipt`, Owner decision | successful current compute terminal, then held-out evaluation and explicit Owner approval in order |
| encrypted model artifact destination | owner not allocated | `OutputArtifactDestinationBinding`, encrypted persistence/currentness/readback | canonical owner and exact receipt ABI allocated; currently hard-blocked |
| Quick Clone UI rebind | TASK-046/TASK-073 | consume current-main R3 exact8 and later rebind only the non-duplicating A adapter | R3 is already landed; required production producer receipts must land before enabling the flow; no replay of historical exact8 and no duplicate selector |
| local VoiceProfile evolution | TASK-014 | versioned local binding without provider credential/private voice alias | separate accepted TASK-014 design/schema/source/test allocation; current `VoiceProfile` is provider-shaped |
| fine-tuned/full-render execution | TASK-014/TASK-075 | versioned amendment beyond current ZERO_SHOT/PREVIEW | separate accepted cross-owner design/implementation and reference-not-required/read-count-zero proof |
| narration compute/Human ticket | TASK-066/071/072 | compute/network admission and exact one-use Human/child ticket only | separate task-local accepted design and implementation authority |
| durable Job candidates/custody | TASK-076 | immutable DISPATCHING/IN_FLIGHT/terminal candidate construction/validation and child/process/Job custody | TASK-068 publication and TASK-043 currentness ports landed; TASK-076 never physically publishes/selects by itself |
| immutable Job publication | TASK-068 | pinned candidate publication/readback only | exact TASK-076 candidate bytes; no selection/currentness claim |
| Project/Job currentness | TASK-043 | exact candidate CAS selection and fresh readback | separately accepted TASK-043 implementation; stale head/orphan/reply loss fail closed |
| reference lifecycle | TASK-074 | begin attachment, direct child pair transfer, remote-close proof and lease terminal | zero-shot only; exact selected Job/ticket/child; no parent body read |
| narration execution | TASK-075 | authenticated worker/PCM/result and reference closure consumption | current ZERO_SHOT/PREVIEW only; exact bootstrap/prepare/release order |
| call/sink/result/POST | TASK-014 | pre-exec capabilities, phase-correct sink begin, staged WAV and durable POST | callable producer landed; applicable Task074 terminal precedes POST |
| private-media custody | owner not allocated | encrypted raw/canonical/processed/transcript/training-copy custody | canonical owner allocation and exact private receipt ABI required before Q1 implementation |

The future TASK-046 training-engine/worker candidate above means exactly:

- `src/ai_video_production/task046_voice_training_engine_adapter.py`;
- `src/ai_video_production/task046_voice_training_worker_protocol.py`;
- `schemas/task046-voice-training-engine-adapter.schema.json`;
- `src/ai_video_production/schema_resources/task046-voice-training-engine-adapter.schema.json`;
- `tests/test_task046_voice_training_engine_adapter.py`;
- `tests/test_task046_voice_training_worker_protocol.py`.

These are candidate Allowed Files only, not present implementation authority.
Runtime/model acquisition, recipe retrieval, representative execution and real
training remain separate Human/effect gates.

## Acceptance

- source-backed dependency and preservation inventory is complete;
- no preserved branch/worktree bytes are changed;
- Q1/Q2/Q3/Q4 and model/runtime START gates are explicit;
- MUST/prohibited/negative/UI/recovery boundaries are testable;
- independent DEV-4 Critic and Judge return zero Critical/High before design
  acceptance;
- implementation remains `NOT_AUTHORIZED` until a later exact allocation.
