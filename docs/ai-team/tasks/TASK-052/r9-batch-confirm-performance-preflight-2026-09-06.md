# TASK-052 R9 Batch-confirm Performance Preflight

Date: `2026-09-06 JST`

Status: `IMPLEMENTED / SYNTHETIC_NO_MEDIA_ONLY`

## Atomic Unit

- Task / Unit: `TASK-052 / R9-BATCH-CONFIRM-PERFORMANCE-PREFLIGHT`
- Profile: `DEV-3 HIGH ASSURANCE`
- Goal: make the existing R2B staged batch-confirm transaction independently
  reproducible and measurable without media, Provider, model, Dataset-adoption or
  native-application effects.
- Allowed files:
  - `tools/task052/run-r9-batch-confirm-performance-preflight.py`
  - `tests/test_task052_r9_batch_confirm_performance_preflight.py`
  - this report and the bounded TASK-052 status paragraph
- Prohibited files/effects: TASK-054 Dataset/model/provider source, Owner Voice
  TASK-014/046/047/048/075, private media, real Human Gold, automatic Dataset
  adoption/training, model download, Provider/paid execution, native app mutation,
  CHANGELOG, Release, Deploy and Production Activation.

## Source-truth finding

`TASK-052/task.md` says no further safe implementation unit remained after R9,
but the R0 traceability matrix still marks `DBD-GAP-003` GENERATOR_REMAINING
detector/teacher support as `STUB`. Current source has the temporal state machine,
but no dedicated `VisualTrainingDomain`, calibrated HUD ROI or Teacher detector
route for GENERATOR_REMAINING. R9 also keeps the exact `発電機 残0` real-video
flow `NOT_CONFIRMED`.

This preflight therefore does not invent that canonical boundary. It uses an
explicit `PERK_ICON` transaction surrogate only to exercise the already-owned
batch-confirm path. The receipt fixes `exact_generator_teacher_contract_available`,
`real_media`, Human Gold and all production claim/effect flags to false.

## Harness contract

The tool requires an existing authorized root and a new, strictly contained run
root. Existing run roots are never reused. It stages deterministic PGM fixtures,
then verifies:

- all hashes are re-admitted before commit;
- the manifest is atomically written once;
- Confirm starts zero subprocesses;
- one affected-domain reference index is built;
- manifest, index and batch receipt read back;
- stage/confirm/subprocess and phase timings are retained;
- the configured preflight time ceiling is met.

The run root and authorized root are represented in the receipt only by SHA-256,
so a repository-safe summary does not disclose a private absolute path.

## Remaining gates

- exact GENERATOR_REMAINING Teacher/detector/ROI ownership: `DESIGN_BOUNDARY_REQUIRED`;
- Windows packaged `発電機 残0` real-video responsiveness/process observation:
  `NOT_CONFIRMED / HUMAN_DATA_NATIVE_GATE`;
- Multi-Killer/resolution/compression/UI-scale video: `NOT_CONFIRMED`;
- complete 5–10 match Human Gold and production accuracy: `NOT_CONFIRMED`;
- TASK-054 Dataset adoption/training/provider execution: unchanged separate Human
  Gates; no TASK-054 source was modified.

## Verification

- focused new harness plus existing R2B transaction/fault regression: `9 PASS`;
- all TASK-052 tests on Windows Python 3.13: `144 PASS`;
- all direct TASK-049 tests on Windows Python 3.13: `186 PASS`;
- final combined TASK-049/TASK-052 regression after receipt-path hardening:
  `330 PASS`;
- 64-sample external preflight run:
  - result: `PASS`;
  - Confirm: `64 / 64`;
  - manifest writes: `1`;
  - Confirm subprocesses: `0`;
  - reference-index rebuilds: `1`;
  - total transaction time: `1.4684153999987757 s`;
  - all receipt checks: `PASS`;
- durable receipt locator:
  `TASK-052/r9-batch-confirm-performance-preflight/20260906-codex-01a07419-d97a004-r3/task052-r9-batch-confirm-performance-preflight.json`;
- durable receipt SHA-256:
  `e8d34844052d2f82d187ce7912143227fe0a915476a8ec454c07838d8f5b5f53`;
- derived reference-index SHA-256:
  `5e1f069cff315cffb8edee5053108545e8b308533680ef7b7ce287f0587a2160`.

The first 64-sample run is retained as `FAIL` Evidence: a deterministic PGM
fixture could start with an ASCII whitespace-valued first pixel, which the current
PGM reader consumed while normalizing header whitespace and then rejected for an
invalid body length. The fixture was corrected to force a non-whitespace first pixel,
covered by increasing the regression sample set to 40, and rerun under a new
operation identity. No historical run was overwritten or deleted.
