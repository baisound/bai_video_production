# TASK-046 / P-VS-4B Gate 4 R2 — Engine Capability Probe Evidence

## Outcome

R2 defines a body-free, provider-neutral boundary for measuring one exact
engine/model/runtime/recipe and one exact training mode on the target machine.
It prevents a package check or model-load success from becoming a fabricated
training-feasibility PASS.

This unit is a pure metadata validator. It does not download, install, load a
model, reserve a GPU, execute a training step, write a checkpoint, register a
ModelCandidate, or use Owner audio.

## Canonical records

1. EngineCapabilityProbePlan binds exact engine, package, model, weight
   manifest, runtime, recipe, probe profile, target resource profile and one of
   FULL_FINE_TUNE, PARAMETER_EFFICIENT_FINE_TUNE or ADAPTER_OR_LORA. Requested
   phases are unique and in canonical order. The plan is synthetic-only and all
   effect-started flags are false.
2. EngineCapabilityProbeReceipt validates externally supplied phase Evidence
   for package verification, model load, representative step, checkpoint
   roundtrip, OOM-safe recovery and thermal/duration behavior. UNKNOWN remains
   UNKNOWN. A known FAIL or unsupported phase remains FAILED_KNOWN. Genuine
   integer resource measurements are required for a PASS that depends on them.
3. EngineAdmissionEvidenceProjection maps one exact receipt into the fact
   fields consumed by R1. It never issues EngineRecipeAdmissionBinding and
   never dispatches training. Missing phases are NOT_APPLICABLE and keep the
   training Evidence state UNKNOWN.

## Qwen load-probe boundary

The previously captured qwen-tts 0.1.1 / Qwen3-TTS 0.6B model-load probe may
produce PACKAGE_VERIFY=PASS and MODEL_LOAD=PASS Evidence. It has no compatible
representative-step, checkpoint, recovery or thermal-duration receipt in this
unit, so its training Evidence remains UNKNOWN. No engine family is selected or
commercially admitted by this contract.

## Acceptance and negative cases

- each training mode is isolated; one mode's Evidence cannot admit another;
- canonical phase order, duplicate phase and revision lineage are enforced;
- representative-step PASS requires exact peak VRAM, RAM, optimizer overhead
  and duration measurements;
- checkpoint PASS requires checkpoint bytes;
- thermal-duration PASS requires exact disk floor and temperature evidence;
- UNKNOWN is never converted to zero, completed or PASS;
- load-only Evidence remains UNKNOWN for training;
- body, absolute path, credential and unknown fields are rejected;
- public projection hides engine/model identities, hashes and measurements;
- all module effect flags remain false;
- schema/runtime parity, digest tamper, caps and no-effect static surface are
  covered by focused tests.

## Critic passes

Builder Critic verifies the three record types, deterministic hashing and R1
projection boundary. Security Critic verifies body/path/credential exclusion,
effect-free imports and public suppression. Compatibility Critic verifies
closed states, mode separation and exact measurement prerequisites.

Critic pass 1 found two fail-closed gaps: a receipt needed an explicit
cross-record plan/mode/phase validator, and UNKNOWN process reconciliation
needed to block both probe completion and admission Evidence. R2 adds
validate_receipt_against_plan and carries process_reconciliation_state into the
projection. Focused tests were expanded to cover both corrections.

Validation after correction:

- focused: 19 passed;
- Windows full: 1893 passed, 1 skipped, 1 unrelated TASK-047 effect test
  deselected;
- WSL full: 1894 passed, 1 skipped;
- schema mirror: byte exact;
- compileall and diff-check: PASS.

Residual Critical/High/Medium after correction: 0 / 0 / 0.

## Judge

- PURE ENGINE PROBE METADATA CONTRACT: PASS after validation.
- MODEL LOAD AS TRAINING FEASIBILITY: REJECTED.
- REAL DOWNLOAD / INSTALL / MODEL LOAD / TRAINING STEP: NOT PERFORMED.
- ENGINE ADMISSION / JOB / GPU / TRAINING / MODEL CANDIDATE: BLOCKED by
  separate exact receipts and Owner Gate.
- OWNER AUDIO / DATASET EFFECT / PUBLICATION / RELEASE: NOT AUTHORIZED.
