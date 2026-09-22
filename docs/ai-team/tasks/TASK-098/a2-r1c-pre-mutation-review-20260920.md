# TASK-098 A2-R1c Fresh Pre-Mutation Review

## 1. Identity, authority and depth

- Active Project / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R1c`
- Base commit for this review: `84af057c2b0a0c3d5641c01c17f6b7836ec6e429`
- Branch: `codex/task-098-universal-wav-review-integration`
- Governance: `DEV-3 HIGH ASSURANCE`
- Authority: Owner AUTONOMY continuation on `2026-09-20`, bounded by the
  accepted A2-R1 design and all existing Human Gates.
- Design status: `ACCEPTED / IMPLEMENTATION_COMPLETE / COMMIT_READY`.

R1c is the next reserved continuation of TASK-098, not a new Task. It composes
the completed R1b runtime-managed port into trusted Python application seams and
projects body-free runtime/recovery state. It does not own Provider behavior,
Transcript identity, durable operation state, progress/cancel/adjudication or a
native production adapter.

## 2. Authority boundary

R1c must not add, accept or activate a serialized v2 launch-config version.
`Task036LaunchConfiguration` versions `1.0.0` through `1.3.0`, the first-run
document and CLI/native entrypoints remain byte/behavior-compatible v1 routes.
New-version acceptance and real adapter activation remain reserved for the later
Human-gated native/A6 unit.

R1c may add one explicit Python-only test-composition entrypoint named
`build_runtime_managed_trusted_launch_for_tests`. It requires a frozen
`Task036RuntimeManagedTranscriptionInjectionV2` containing typed runtime
settings/request, fake capability probe, unloaded-provider factory and clock.
It is not selected by config, environment, JavaScript or the existing Product
entrypoint. Missing, mixed v1/v2 or malformed injection fails with
`ERR_TASK098_RUNTIME_ADAPTER_NOT_BOUND` before directory creation, SQLite,
Project/Job bootstrap or Provider construction and never falls back to v1.

The common trusted-launch composition is factored once behind a private port
factory seam. Existing
`build_trusted_launch()` supplies the legacy v1 port factory; the Python-only
test entrypoint supplies the actual R1b v2 port factory. Legacy config
device/compute values do not become v2 authority.

## 3. Runtime outcome projection

V2 success/recovery results must be validated as the completed R1b
`RuntimeManagedLocalTranscriptionOutcomeV2`. Because Product ports already
import the pre-edit base outcome, validation must use a local import or another
explicitly non-circular seam, never a new top-level reverse import.

The existing TASK-036 transcript-binding result remains canonical and separate
from runtime admission metadata. V2 adds one `runtime_transcription` object with
exactly these keys:

- `requested_device`;
- `outcome`;
- `reason_code`;
- `effective_device`;
- `effective_compute_type`;
- `fallback_applied`;
- `model_download_authorized=false`;
- `provider_configuration_from_javascript=false`;
- `transcript_text_exposed=false`;
- `host_path_exposed=false`.

Values must be derived only from the immutable copies returned by
`runtime_request_public` and `runtime_decision_public`. Reject missing/unknown
keys, wrong scalar types, inconsistent READY/BLOCKED combinations and private
extras. Do not expose record digests, timestamps, paths, exception text, raw
probe/config records or Transcript bodies. V1 result bytes and bridge payloads
remain unchanged.

Only `RuntimeManagedLocalTranscriptionOutcomeV2` may create this object. Dicts,
subclasses/foreign outcome types, independently caller-supplied projections,
unknown keys and wrong scalar types fail with
`ERR_TASK098_RUNTIME_OUTCOME_INVALID`. The runtime copies the two typed public
dicts before constructing the nested projection; later caller mutation cannot
alter the returned payload.

## 4. Exact v2 recovery presentation and actions

V2 status calls the port's exact `recovery_state()` capability and exposes these
exact additional keys:

- `transcription_runtime_mode="RUNTIME_MANAGED_V2"`;
- `transcription_recovery_state=<exact classifier>` when an exact source is
  bound, otherwise `null`;
- `transcription_available_action` in `START|RECOVER|VERIFY|NONE`;
- `transcription_status_label` from the fixed table below.

It omits `transcription_recovery_required`; that legacy boolean never acts as v2
authority. Missing, throwing, non-string or unknown classifier output is
projected as `CORRUPT_BLOCKED / NONE` and direct actions fail closed; it never
falls back to the legacy boolean. V1 status remains byte-for-key unchanged,
including `transcription_recovery_required`, and adds no v2 keys.

| V2 classifier | Public action | Fixed label | Permitted operation |
|---|---|---|---|
| `PENDING_ADMISSION` | `START` | `文字起こしを開始できます` | prepare/apply ordinary transcription |
| `RECOVERABLE_PUBLICATION` | `RECOVER` | `文字起こし結果を復旧できます` | prepare/apply Provider-zero recovery |
| `VERIFICATION_ONLY` | unbound restart: `VERIFY`; already bound/later stage: `NONE` | unbound: `文字起こし結果を検証できます`; bound: `文字起こし結果は検証済みです` | unbound distinct Provider-zero verification; bound read-only redisplay |
| `ACTIVE_UNKNOWN` | `NONE` | `文字起こし処理の状態を確認できません` | status only |
| `ADJUDICATION_REQUIRED_NO_PUBLICATION` | `NONE` | `人による確認が必要です` | status only; A2-R2 later owns adjudication |
| `FAILED_TERMINAL` | `NONE` | `文字起こしは失敗しました` | terminal status only |
| `CORRUPT_BLOCKED` | `NONE` | `文字起こし状態が破損しているため停止しました` | integrity-blocked status only |

Unknown states are `CORRUPT_BLOCKED` at the application boundary and permit no
start/recover/verify action. A v2 status payload does not expose the legacy
boolean as authority.

The runtime checks the permitted action both when creating a confirmation and
immediately before applying it. A confirmation is single-use and binds exact
Project, source Asset/SHA, session/context revision and requested action. State
drift cannot upgrade authority. Direct bridge calls are rejected even when a UI
control is hidden. Existing operation locks and source-drift checks remain.

Action selection is contextual and must not shadow later editing stages:

- without an exact selected source, the classifier is not called, state is
  `null`, action is `NONE` and the existing media-selection action remains;
- `START`, `RECOVER` and unbound `VERIFY` are available only while the source is
  bound, no Transcript is bound and `next_recommended_action` is
  `transcription.start`;
- when the exact Transcript is already bound or the workflow has advanced to
  `subtitle.save` or later, `VERIFICATION_ONLY` is read-only status with action
  `NONE` and label `文字起こし結果は検証済みです`; it performs no port call and
  the existing subtitle/cut/resolve/render/handoff workflow action keeps button
  priority.

Unbound `VERIFICATION_ONLY` has exact methods
`prepare_local_transcription_verification()` and
`verify_local_transcription(confirmation_id)` in the runtime and bridge. The
apply method may call the R1b port's existing `recover_local_media()` exactly
once because that method performs Provider-zero COMPLETED verification; the
public action/label must remain VERIFY and it never calls
`transcribe_local_media`. All `NONE` states perform zero recovery, Provider,
probe, factory, slot-release or durable-row effects. `PENDING_ADMISSION` also
performs zero recovery calls; `RECOVERABLE_PUBLICATION` alone exposes the
public recovery control.

The existing JavaScript v1 route remains behavior-compatible. The v2 branch of
the workflow button is used only for `next_recommended_action` equal to
`transcription.start`. It must call prepare, show an explicit affirmative Human
confirmation using the fixed status label, then apply with the returned
`confirmation_id`; it must never call apply with `{}`. A negative answer calls
the existing cancel method with that confirmation and performs zero apply,
probe, factory or Provider calls. The visible transcription button uses the
fixed label and is disabled for `NONE`; every later editing-stage button retains
its existing route and label.

After the port returns, the runtime validates the concrete
`RuntimeManagedLocalTranscriptionOutcomeV2` type, exact copied public keys/types
and READY-consistent projection before Transcript binding, finalization or slot
release. An invalid outcome raises `ERR_TASK098_RUNTIME_OUTCOME_INVALID` with
zero binding/finalization/slot-release effects; its already durable port state is
not repaired or released implicitly.

## 5. Proposed allowed files

Implementation source ceiling:

- `src/ai_video_production/task036_trusted_launcher.py`
- `src/ai_video_production/task036_pre_edit_runtime.py`
- `src/ai_video_production/task036_shell_ui.py`

Focused test ceiling:

- `tests/test_task036_trusted_launcher.py`
- `tests/test_task036_pre_edit_runtime.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_first_run_bootstrap.py`
- `tests/test_task036_shell_cli.py`

Bounded documentation/Evidence:

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a2-r1-runtime-integration-design-20260919.md`
- this review and one R1c Evidence record.

First-run and CLI production source, Product ports, store, runtime contract/schema,
dependencies and other Tasks are read-only. Any required mutation outside this
ceiling returns to review rather than expanding implicitly.

## 6. Acceptance matrix

1. Existing launch-config versions and first-run/CLI routes still construct v1;
   unsupported versions or runtime keys fail closed.
2. Incomplete or mixed v2 injection fails with the fixed error before filesystem/store/project/job or
   Provider effects; a complete fake injection composes the actual R1b port with
   zero native probe/import/model/download.
3. V1 trusted launch, pre-edit, bridge payload and recovery behavior remain
   unchanged. First-run serialized bytes/config identity, CLI default bootstrap,
   legacy fake ASR execution and legacy recovery result key sets are golden.
4. V2 outcome projection is exact, copied and body/path/digest/timestamp free;
   malformed or extra private fields fail before binding, finalization or slot
   release and leave the durable port state unchanged.
5. Every classifier row yields the exact label/action above. Prepare and apply
   both reject unauthorized or drifted actions and consume confirmations once.
6. Status and rejected recover/verify calls are effect-zero.
   `PENDING_ADMISSION` status/prepare has zero Provider/probe/factory effects,
   while apply after affirmative confirmation performs the normal fake
   probe/factory/Provider and durable admission path. `RECOVERABLE_PUBLICATION`
   performs one Provider-zero recovery call;
   `VERIFICATION_ONLY` performs one distinctly named Provider-zero verification
   call without repair only for an unbound restart. Bound/later-stage
   `VERIFICATION_ONLY`, every `NONE` state and a source-less status perform zero
   recovery/Provider/probe/factory/slot/row effects.
7. Positive, negative and stale Human confirmation paths are covered. Negative
   confirmation consumes/cancels the token and has zero apply/provider effects.
8. Source/context drift, concurrency, exact transcript finalization and slot
   preservation remain covered.
9. Focused launcher/pre-edit/bridge/bootstrap/CLI regression passes; independent
   Critic/Tester and final Judge report zero unresolved Critical/High.
10. External Evidence is written beneath
   `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r1c-trusted-composition\<run-id>\`
   and read back before completion.

## 7. Exclusions and stop conditions

No real capability probe, model construction/inference/download, private audio,
native/packaged launch, config migration, old-binary activation, installation,
training, Release, Deploy or Production Activation is authorized. A2-R2
progress/cancel/Human adjudication remains separate and mandatory before any
real v2 activation.

## 8. Design review outcome

- Independent Critic: first `REJECT / 0/1/3/0`; all stage/action, effect-scope,
  Human-confirmation and outcome-order findings were incorporated; final
  `ACCEPT / 0/0/0/0`.
- Independent Tester: first `FAIL / 0/1/0/0`; the PENDING effect-scope conflict
  was closed; final `PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / implementation allocated / 0/0/0/0`.
- Implementation may now change only the section 5 ceiling. It remains
  `NOT_COMMIT_READY` until focused regression, completion reviews and external
  Evidence read-back pass.
