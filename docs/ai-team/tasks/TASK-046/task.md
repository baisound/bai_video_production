# TASK-046 — Voice Studio / Voice Dataset & Local Voice Profile

- Status: `P_VS_1A_PROFILE_FOUNDATION_HOSTED_CLOSED / P_VS_3A_3B_4A_4B_CONTRACT_FOUNDATION_HOSTED_CLOSED / BEGINNER_CLIENT_UNSIGNED_TECHNICAL_PREVIEW_HOSTED_CLOSED / PRODUCTION_RECORDING_TRAINING_MODEL_AUDIO_GATED`
- Authorization: `HOSTED_CLOSED_BODY_FREE_SYNTHETIC_AND_TECHNICAL_PREVIEW_FOUNDATION / OWNER_VOICE_PRODUCTION_EFFECTS_REQUIRE_FRESH_AUTHORITY`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Exact allocation base: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`
- P-VS-0 hosted closure: PR #90 / exact main `25e2e04fb3360af77017a4a42e868fc95b15ec80`
- P-VS-1A body-free VoiceProfile foundation: PR #93 / exact main `52284d77b8b42c09181256f68374d90b9b0375ab`
- Canonical input: `docs/ai-team/product-design/voice-studio/BAI_VIDEO_PRODUCTION_VOICE_STUDIO_LOCAL_AI_OBS_統合詳細設計書_Ver1.2.md`

## Goal

Integrate an owner-only Voice Studio into the single BAI Video Production
desktop product. The Task owns private Voice Profile and Dataset revisions,
zero-shot and fine-tuned local-engine admission, teleprompter recording,
capture preflight, review, style coverage and AI recording-coach proposals.

TASK-046 does not replace TASK-014 narration rendering, TASK-006/023 subtitle
and ASR truth, TASK-003/037 Asset and Candidate truth, TASK-041 Human audio
review, TASK-026/022 placement/frame truth, TASK-043 durable jobs or TASK-044
Timeline/Export Queue.

## Hosted implementation closure and remaining Gates

The repository already contains more than the historical P-VS-1A active-Lock
status implied. The following bounded foundations each passed `9 / 9` hosted
checks and merged to main:

- P-VS-1A body-free VoiceProfile foundation: PR #93 / exact main
  `52284d77b8b42c09181256f68374d90b9b0375ab`;
- P-VS-3A recording-session contract and P-VS-4B vertical-slice design:
  PR #101 / `a7690917b2c05c44372a1c7ea6dd81d422b1aa88` and PR #163 /
  `4a8599cec34622421708f3a7b6737323a69f572d`;
- P-VS-3B Dataset revision, P-VS-4A Training/ModelCandidate and P-VS-4B
  application contracts: PR #165 / `13a6e430400a1a5af6ba4800069c5b766eb1bcd3`,
  PR #168 / `868548ebec65ebec565b62dd45bc45da99db2fb1` and PR #170 /
  `75e813f54eb1b00d0b14468643972639e397b57f`;
- bounded synthetic WAV runtime, Dataset/engine admission and engine Evidence
  contracts: PR #173 / `c5a42a93df09f68ab4c4fd82f13757072200645e`,
  PR #174 / `7f427c845fc0ff47e255dc5adc5349b21e025151` and PR #175 /
  `cf2e37605b0d138181e0d5f7c56ce67b00f30aab`;
- beginner client, Windows installer, license composition, workflow import and
  next-action UX: PR #180 / `bb4f9aa717638712afaa9b9b11f34a55647643fc`,
  PR #181 / `a380c03977a0f09f2b90e6d3c7fb23c85a7e46f2`, PR #182 /
  `da834ccbd370b527c1cc6c4ba03806ea4a6ac669`, PR #183 /
  `511dc5122347c63a9dd7241f4bfcf2f383f16057` and PR #184 /
  `dc5710a11b45176962ca70a5398ddd705bc61f60`.

These closures establish body-free contracts, synthetic fail-closed behavior
and an unsigned development Technical Preview client/installer. They do not
establish production Voice Studio admission. The Qwen3-TTS load/dependency
probes remain diagnostic compatibility Evidence; the official representative
training recipe is `FAILED_KNOWN / BLOCKED`. P-VS-1B Shell integration, P-VS-2
real zero-shot narration, real recording/private-audio persistence, Dataset
adoption, Training start, model approval, narration generation and Master WAV
acceptance all remain separate fresh Gates. They require exact runtime/path
Evidence, current Consent and rights, verified encrypted storage and explicit
Owner authorization; no merged receipt or Technical Preview artifact is an
execution capability.

## Product boundaries

- Initial formal subject is the Owner's own voice only.
- Local/free is the default; Cloud and paid execution are explicit opt-in and
  remain outside this Task's automatic authority.
- Raw voice, Dataset, VoiceProfile, ModelArtifact and speaker data are private,
  encrypted Product data with explicit retention, consent and recovery rules.
- Recording and training are separate. No recording is automatically adopted
  into a Dataset and no Dataset automatically starts training.
- Raw recordings and previous revisions are immutable; processing creates
  derived Assets and new revisions.
- Model, Code, Weight, Dataset and Output license evidence remain separate.
- Unknown license, identity or consent fails closed.

## Slices

1. `P-VS-0` — hosted-closed current-state intake, Crosswalk, architecture,
   roadmap and Task allocation. Documentation only.
2. `P-VS-1A` — project-local `VoiceProfileRevision`/Consent/License references,
   immutable metadata revisions, public/private projection, atomic/CAS store,
   tamper/restart and non-executing local-engine capability description. It is
   Shell-independent and stores no voice/audio body. The existing
   `owner_narration.py::VoiceProfile` remains the canonical narration identity;
   P-VS-1A must not create a second `VoiceProfile` class or narration planner.
3. `P-VS-1B` — successor-mock-governed Voice destination, Shell and TASK-014
   integration. It requires a separate Authorization and does not inherit
   Engine execution authority from P-VS-1A.
4. `P-VS-2` — Japanese, one-speaker, local/free zero-shot 60–90 second vertical
   slice through TASK-014, Asset/Candidate, Placement, Timeline, Export Queue
   and QA. Native execution needs exact model/license/runtime Evidence and the
   applicable explicit Human Gate.
5. `P-VS-3` — 48 kHz/24-bit/mono production training-material recording,
   preflight, pause/resume/checkpoint and Dataset review. Contract/synthetic
   design may precede capture, but real recording requires P-OBS-1 hosted
   completion, P-OBS-0 exact-path probe PASS, recording Consent, verified
   encrypted storage and explicit Owner GO.
6. `P-VS-4A` — 30/60/90/120 minute fine-tuning revisions, exclusive resource
   mode, checkpoint/restart, ModelCandidate evaluation and Owner approval.  A
   completed Training job is not automatically a usable or active model.
7. `P-VS-4B` — **OBS-to-Model-to-Narration WAV vertical slice**.  Starting from
   Owner-approved OBS recordings, compose TASK-048 quality Evidence, P-VS-3B
   Dataset/TrainingInputSnapshot, P-VS-4A training/ModelCandidate and TASK-014
   local narration.  Generate style-specific Cue WAVs from one approved model,
   then assemble and QA one natural 48 kHz Master WAV with stable speaker
   identity, intended pauses, consistent level and no audible joins.  A simple
   Windows client and installer are the acceptance tool for this slice, not the
   product goal.  Dataset adoption, training start, model approval, narration
   generation and final Master acceptance remain separate Owner Gates.
8. `P-VS-5` — style coverage, Semantic Direction, recording-coach proposals,
   Japanese linguistic processing and later locale gates.

## Shell and mock authority

Voice Studio must be reachable from `BAI Video Production.exe`, but it may not
be added ad hoc to the packaged Shell. TASK-036 P-UX-1C first closes the
current V6.1.1 mock acceptance. A later Voice Studio UI unit must create and
approve a successor canonical mock revision that preserves the V6.1.1 design
language before changing the EXE. Runtime-only divergence is an acceptance
failure. P-VS-1A may develop in parallel because it is Shell-independent and
body-free, but it may merge only after P-UX-1C hosted closure and fresh-main
rebase. The successor mock remains immediately after P-UX-1C and before
P-VS-1B changes the Shell or connects TASK-014.

## Exit criteria

- all OR-01..OR-32 and Q1..Q44 remain traceable;
- the 60–90 second Japanese local/free path has exact VoiceProfile, Consent,
  Model/License, Text, WAV, Asset, Scene/Cue, Placement, Timeline, Export and QA
  lineage;
- actual WAV is 48 kHz and measured duration, not estimated reading speed,
  drives frame placement;
- failure, cancel and restart never synthesize success or replay UNKNOWN work;
- Human review remains required for Dataset adoption, VoiceProfile production
  approval, text changes, Candidate acceptance and commercial export;
- P-OBS-1 capture completion never implies Dataset adoption or training start;
- P-VS-3 production recording and P-VS-4 fine-tuning remain blocked until the
  complete OBS/Consent/encryption/Owner Gate is satisfied;
- no paid, Cloud, credential, external-app or release authority is inferred.
