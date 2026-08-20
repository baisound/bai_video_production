# TASK-046 / P-VS-4B Gate 4 R1 — Dataset Preparation and Engine Admission

## Outcome

R1 connects the synthetic WAV receipts from Gate 4 R0 to a body-free Dataset
preparation manifest and an exact engine-recipe admission boundary.  It emits
only an undispatched Training proposal.  No Dataset, TrainingInputSnapshot,
durable Job, resource reservation, model load, training or artifact effect is
performed.

## Canonical records

1. `SyntheticDatasetPreparationManifest` binds ordered immutable WAV
   inspection receipts, source hashes, non-overlapping half-open sample ranges
   and approved-label hashes.  Unique selected duration is integer frame truth;
   duplicate or overlapping ranges cannot inflate it.
2. `EngineRecipeAdmissionBinding` keeps engine/package/model/runtime/weights,
   exact recipe revision, training mode, official-recipe, representative-step,
   target-resource, checkpoint and license Evidence together.  FULL, PEFT and
   LoRA modes are distinct.  Canonical binding and admission are orthogonal:
   `admission_state=PASS` requires every fact PASS and an approved synthetic
   technical-test license, while a correctly bound legal-review state remains
   representable but cannot run.
3. `TrainingExecutionProposal` composes the preparation manifest, engine
   admission, output-destination hash, durable-job state and rights/Consent
   state.  Even a ready proposal is `READY_FOR_OWNER_HUMAN_GATE`, never a
   dispatch authority.

## Current real-engine boundary

The existing Qwen3-TTS 0.6B load probe is not promoted.  It proves only that a
pinned model loaded on the target GPU.  It does not prove an official compatible
training recipe, representative training step, optimizer/checkpoint overhead,
mode-specific 12 GB feasibility, recovery, duration or license admission.
Therefore the real engine binding remains unresolved/blocked until those exact
Evidence items exist.

## Privacy and effects

No audio body, text body, absolute path, credential or private engine root is
serialized.  Public projections suppress source/item/engine identifiers and
all hashes.  `owner_audio_used`, Dataset adoption, TrainingInput issuance,
dispatch, GPU reservation, training and artifact-write flags remain false.

## Acceptance and Critic

- sample range and unique-duration arithmetic;
- overlap, duplicate ID, order, revision and cap rejection;
- three training modes validated independently;
- unresolved binding cannot invent exact coordinates;
- LEGAL_REVIEW_REQUIRED or missing representative step cannot bind;
- engine, durable Job and rights/Consent blockers classified separately;
- ready proposal still requires Owner Human Gate and dispatch=false;
- schema/mirror/runtime parity, digest tamper, unknown fields and public leak
  rejection;
- static no-filesystem/no-network/no-process/no-model surface.

Builder, Security and Compatibility Critic passes record residual
Critical/High/Medium `0 / 0 / 0` after focused/full validation.

## Judge

- SYNTHETIC_DATASET_PREPARATION_METADATA: PASS after validation.
- EXACT_ENGINE_RECIPE_ADMISSION_CONTRACT: PASS after validation.
- REAL DATASET ADOPTION / JOB / GPU / TRAINING / MODEL: BLOCKED, separate Gate.
- OWNER AUDIO / CONSENT / PRODUCTION / RELEASE: NOT AUTHORIZED.
