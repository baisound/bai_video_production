# TASK-098 A3-R2 Guarded Model Settings Pre-Mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A3-R2`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `a2dca633e8f5398e56df435a456c3f37e51a8a2f`
- Base/current-main identity at review: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Status: `DESIGN_ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## 1. Goal

Connect one explicit native model-folder selection to the existing private
TASK-036 launch configuration without creating a second settings authority.
The selected directory must pass A3-R1, receive a server-local one-use Human
confirmation, and update only `asr.model` through an expected-config-digest
guarded atomic replace. The existing `paths.asr_cache_directory` is validated,
digest-bound and preserved unchanged for cache reuse.

## 2. Canonical boundary

- `Task036LaunchConfiguration` remains the validation authority for the private
  launch configuration and its existing ASR/cache fields.
- A3-R1 remains the model-directory observation authority.
- The new A3-R2 service coordinates selection, validation and guarded write; it
  does not become a second canonical ASR settings document.
- The native chooser returns an ephemeral host path only inside the local
  Python process. Shell prepare/apply projections never return that path.
- TASK-006/023 Provider/transcript, TASK-041 review media, TASK-046/097 voice
  model training and TASK-047/048 capture quality ownership remain unchanged.

## 3. State machine

### PREPARE

1. Require the caller's exact current launch-config SHA-256.
2. Stably read the existing regular, non-symlink/reparse, single-link config
   file without creating a lock artifact, and require it to remain inside its
   validated TASK-036 `project_root`.
3. Reject stale digest before opening any native chooser.
4. Validate the existing config through `Task036LaunchConfiguration`.
5. Ask the injected TASK-036 dialog boundary for one existing model directory.
6. On cancel, return path-free `CANCELLED` with no pending state.
7. Inspect the selection through A3-R1. On BLOCKED, return only its closed
   public reason projection and retain no selected path.
8. For READY, retain the canonical path only in a server-local expiring pending
   record and return an opaque one-use confirmation ID plus path-free model ID.

### APPLY

1. Consume exactly one unexpired pending confirmation.
2. Reacquire the config lock and re-read the config stably.
3. Require the original config digest and original cache locator digest.
4. Re-run A3-R1 and require the exact prepared inspection record digest.
5. Deep-copy the validated raw document and modify only `asr.model`.
6. Preserve `allow_model_download=false` and the exact existing cache value.
7. Validate the proposed document through `Task036LaunchConfiguration`.
8. Use the existing atomic JSON writer, validate/read back, and return only
   before/after digests, model ID, cache-preserved and restart-required facts.

Failures before atomic replace perform no settings update. A retry after a
successful but interrupted replace fails the stale expected digest.

## 4. Privacy and effect boundary

- No raw model/cache/config path, file body, model-file digest or exception text
  enters Shell output or public Evidence.
- Pending private state is process-local, bounded, expiring and single-use.
- Prepare is fully read-only. Apply writes only the bound launch config and its
  local lock/temp artifacts inside the same validated Product Project root.
- Model load, inference, Provider execution, network/download and audio access
  remain false/not started.
- Native Windows execution is not performed in A3-R2; only a fixed-script method
  and fake backend tests are added.

## 5. Allowed files

- `src/ai_video_production/task098_faster_whisper_model_settings.py`
- `src/ai_video_production/task036_native_dialog.py`
- `src/ai_video_production/native_file_dialog.py`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task098_faster_whisper_model_settings.py`
- bounded meter-guard expectation in `tests/test_task036_shell_ui.py`
- this review
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r2-guarded-model-settings-20260922-r01.md`
- bounded `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md` status
  synchronization at completion only

No schema, launch-config version/shape, Provider/runtime, dependency, package,
installer, Product version or private asset may change.

## 6. Acceptance tests

- stale/invalid expected config digest fails before picker invocation or write;
- cancel and blocked inspection retain no pending private selection;
- READY prepare is path-free and effect-zero;
- wrong, expired, repeated or malformed confirmation fails before write;
- config or cache drift and model-directory drift fail before write;
- apply modifies only `asr.model`, preserves cache and download=false, validates
  and reads back the exact TASK-036 config, and returns no path;
- injected pre-replace failure preserves original config and cleans temp files;
- fake native backend and fixed Windows folder-dialog script are validated
  without opening a real dialog;
- Shell endpoints have exact closed requests and only apply is meter/write
  guarded;
- focused A3-R2/A3-R1/A3-R0/direct A2 regression passes;
- Allowed Files, diff check and external Evidence read-back pass.

## 7. Critic / Tester / Judge decision

### Critic

- High: persisting a new model-settings document would duplicate TASK-036.
  Corrected by guarded in-place update of the existing launch config only.
- High: picker selection alone cannot authorize persistence. Corrected with a
  server-local expiring prepare/apply confirmation.
- High: config-only CAS permits the model directory to drift. Corrected by exact
  A3-R1 record-digest reinspection at apply.
- High: atomic rewrite could accidentally change cache/download authority.
  Corrected by exact cache binding, semantic one-field diff and full config
  validation before replace.
- Medium: exposing the picker path through Shell would leak private operational
  state. Corrected with minimized prepare/apply projections.

Final design finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.

### Tester

The planned tests use only pytest-owned temporary configurations and fake
dialog backends. Native execution and private model/audio data remain absent.

Decision: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.

### Judge

The bounded fake-only implementation is inside A3 authority. Real Product
settings mutation and real native dialog execution remain A6/native acceptance
activities and are not performed by this Unit.

Decision: `ACCEPT / A3-R2_IMPLEMENTATION_ALLOCATED`.
