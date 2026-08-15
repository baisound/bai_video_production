# TASK-046 — Voice Studio / Voice Dataset & Local Voice Profile

- Status: `FORMALLY_ALLOCATED / DESIGN_ONLY / IMPLEMENTATION_PENDING_HOSTED_AUTHORIZATION`
- Authorization: `OWNER_DIRECTED_ROADMAP_AND_DESIGN`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Exact allocation base: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`
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

1. `P-VS-0` — current-state intake, Crosswalk, architecture, roadmap and Task
   allocation. Documentation only.
2. `P-VS-1` — project-local VoiceProfile/Consent/License contracts, immutable
   revisions, non-executing local-engine capability preflight and Shell-neutral
   application boundary. No model download or generation.
3. `P-VS-2` — Japanese, one-speaker, local/free zero-shot 60–90 second vertical
   slice through TASK-014, Asset/Candidate, Placement, Timeline, Export Queue
   and QA. Native execution needs exact model/license/runtime Evidence and the
   applicable explicit Human Gate.
4. `P-VS-3` — 48 kHz/24-bit/mono teleprompter recording, preflight,
   pause/resume/checkpoint and Dataset review.
5. `P-VS-4` — 30/60/90/120 minute fine-tuning revisions, exclusive resource
   mode, comparison and Production approval.
6. `P-VS-5` — style coverage, Semantic Direction, recording-coach proposals,
   Japanese linguistic processing and later locale gates.

## Shell and mock authority

Voice Studio must be reachable from `BAI Video Production.exe`, but it may not
be added ad hoc to the packaged Shell. TASK-036 P-UX-1C first closes the
current V6.1.1 mock acceptance. A later Voice Studio UI unit must create and
approve a successor canonical mock revision that preserves the V6.1.1 design
language before changing the EXE. Runtime-only divergence is an acceptance
failure. The Owner-directed sequence places that successor mock immediately
after P-UX-1C and before P-VS-1 even though P-VS-1 itself is Shell-neutral.

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
- no paid, Cloud, credential, external-app or release authority is inferred.
