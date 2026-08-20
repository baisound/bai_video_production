# TASK-051 R7J — Human Acceptance Stabilization Detailed Design

## 1. Document control

- Task: `TASK-051 — DbD Training Studio Operational UX Hardening / Unified Learning Workflow`
- Unit: `R7J`
- Development profile: `DEV-3 HIGH ASSURANCE`
- Status: `IMPLEMENTED / LOCAL VERIFICATION PASS / WINDOWS HUMAN ACCEPTANCE REQUIRED`
- Parent baseline: R7H diagnostics + R7I Shared Media / Unified Learning Workflow.
- Owner direction: treat the real-Windows Human Acceptance findings as current Product blockers, preserve one Shared Media architecture, and fix the workflow rather than asking the operator to hand-edit configuration or code.
- Product boundary: BAI VIDEO PRODUCTION only. BAI Development OS remains development governance and is not a runtime dependency.

## 2. Authority and bounded scope

The Owner supplied real Windows screenshots, operation failures and diagnostics and explicitly authorized continued detailed design and development. R7J is a bounded corrective slice inside TASK-051; it does not reopen completed TASK-050 and does not create Release/Deploy/paid-provider authority.

Allowed implementation scope:

- `src/ai_video_production/dbd_training_studio.py`
- `src/ai_video_production/dbd_training_video_player.py`
- `src/ai_video_production/dbd_video_transport.py`
- `src/ai_video_production/dbd_training_studio_foundation.py`
- `src/ai_video_production/dbd_training_studio_foundation_ui.py`
- `src/ai_video_production/dbd_training_review_ui_v2.py`
- `src/ai_video_production/dbd_training_workspace.py`
- `src/ai_video_production/dbd_notification_semantics.py`
- impacted TASK-051 compatibility / accepted-source tests
- new `tests/test_task051_r7j_human_acceptance_stabilization.py`
- TASK-051 design/evidence/current-state/task-index documents.

No direct `main` push, Release, Deploy, production credential activation, paid external provider execution or destructive data migration is authorized.

## 3. Human Acceptance findings converted to design requirements

### R7J-HA-001 — HUD calibration playback flicker

Observed: `HUD位置を設定` flickers during playback while other Shared Media surfaces do not.

Root cause family: HUD calibration uses a custom Canvas overlay path. Recreating/deleting the complete Canvas scene per frame causes visible invalidation/flicker and is distinct from the standard shared player.

Design:

- create the Canvas preview image item once;
- update only its coordinates/image through `coords` + `itemconfigure`;
- redraw ROI overlays separately;
- remove per-frame `update_idletasks()` forcing.

The HUD screen remains a Shared `TkTrainingMediaSession` consumer; a second video decoder is forbidden.

### R7J-HA-002 — HUD automatic correction looks frozen

Observed: `自動補正をテスト` can run long enough to appear hung.

Design:

- all expensive profile resolver / anchor alignment work executes through the existing bounded background-operation queue;
- worker code never invokes Tk APIs;
- the status line reports `実行中...` and returns success/failure on Tk-owned polling;
- the active Runtime Profile FFmpeg path is reused.

### R7J-HA-003 — multiple HUD profiles block batch/single/OCR workflow

Observed batch failure: `Multiple DbD HUD profiles match; calibration selection is required`.

This is a correct fail-closed domain rule but an incomplete operator workflow. Silent first-match selection is prohibited.

Design:

1. exact resolver runs normally;
2. only `ERR_DBD_HUD_PROFILE_AMBIGUOUS` enters disambiguation;
3. UI opens a bounded modal listing the exact candidate profile IDs;
4. Owner/operator selects one or cancels;
5. selected `profile.json` is written into the workflow's explicit HUD profile field;
6. the exact resolver runs again with that manual profile;
7. diagnostics record `HUD_PROFILE_DISAMBIGUATED` without weakening the resolver contract.

The same helper is reused by batch Crop, single-image Crop and OCR routes.

### R7J-HA-004 — non-HUD video view is too small

Observed: media views outside HUD calibration can become impractically small.

Design:

- standard media-first panes reserve at least `60%` / `420 px` where practical;
- batch learning reserves at least `55%` / `400 px`;
- Shared Media preview columns change from 3:2 to 2:1 so the preview receives more width;
- persistent preview target is bounded to `720 x 405`, avoiding integer Tk downsampling from 960x540 to 480x270 on half-height windows;
- forms scroll instead of shrinking the media safety floor;
- full-source Fit-to-View from R7I remains mandatory.

### R7J-HA-005 — long videos need a timeline seek bar

Design adds one canonical time seek bar to `TkVideoTransportBar`, therefore to every Shared Media consumer.

Contract:

- range `0..1000` represents normalized source duration;
- drag previews target timestamp in the status text;
- drag cancels the active playback timer so the clock cannot fight the operator;
- release maps the normalized position to the exact canonical frame;
- transport enters a stopped state, renders the selected frame and notifies media/audio state;
- diagnostics record `TRANSPORT_ACTION action=seek_bar` and failures record `TRANSPORT_SEEK_FAILED`;
- the existing canonical 12 buttons remain unchanged.

### R7J-HA-006 — OCR extraction failure / saved runtime ignored

Root cause family: Training Studio workflow code used literal `tesseract`, `ffmpeg` and default tool resolution in places even after the operator selected a saved Runtime Profile.

Design:

- `resolve_workspace_runtime_profile()` first loads `workspace.selected_runtime_profile_id`;
- if the selected profile is missing/stale, only then fall back to deterministic autodetection;
- Training Studio derives runtime FFmpeg, ffprobe, Tesseract and model-cache paths once from the active profile;
- OCR extraction resolves ambiguous HUD profile on the Tk thread, then runs Tesseract work in the background queue;
- no candidate result is a success condition; it is reported clearly rather than crashing.

### R7J-HA-007 — notification type only exposes chase

The original UI effectively surfaced one known Japanese notification type. R7J introduces an extensible baseline notification taxonomy without changing stored canonical IDs.

Built-in Japanese labels:

- `MATCH`
- `CHASE`
- `INJURY`
- `DOWN`
- `HOOK`
- `UNHOOK`
- `WINDOW`
- `PALLET`
- `KILL`
- `ESCAPE`
- `SYSTEM`

Existing signal IDs already present in the workspace are shown first; known categories are then appended. Unknown historical IDs remain displayable instead of being discarded.

### R7J-HA-008 — FasterWhisper transcription failure

The attached HuggingFace/Xet log proves logging/bootstrap activity but does not contain the underlying transcription exception, so R7J must not fabricate a provider diagnosis.

Concrete corrective design:

- use the selected Runtime Profile's model/device/compute defaults in the trivia workflow;
- propagate selected model-cache directory into `FasterWhisperConfig` through `mine_trivia_from_video()`;
- preserve download authorization semantics;
- long ASR work remains backgrounded;
- `BACKGROUND_OPERATION_FAILED` diagnostics now records ProductError code/details and the chained root-cause exception type/message when available;
- the modal reports the root cause when safely available.

This is a configuration/observability correction, not a claim that every Windows FasterWhisper runtime is now proven healthy. Real Windows transcription remains Human Acceptance evidence.

### R7J-HA-009 — registration review can show stale upper-right notification data

`右上通知を学習 > 登録済み一覧` and `学習・登録データを確認 > 右上通知` are not separate stores. They both read the active workspace OCR vocabulary; Notification semantics are read from the same workspace semantic store.

Therefore permanent divergence is a bug, not intended specification.

Design:

- review builder returns a canonical `refresh_all` callback;
- entering/changing a review subtab triggers `refresh_all`;
- entering the top-level `学習・登録データを確認` tab also triggers the same callback;
- OCR review includes current semantic meaning and normalized Japanese signal label;
- manual `一覧を更新 / すべて更新` remains available, but correctness no longer depends on remembering to press it.

This is navigation-triggered refresh, not polling. No duplicate review database is introduced.

### R7J-HA-010 — Human Gold meaning/registration is unclear

Current Product behavior is preserved truthfully:

- Human Gold means externally supplied or separately human-corrected ground-truth Evidence used by review/intelligence workflows;
- the current Training Studio review panel scans recognized Human-Gold CSV/JSONL locations;
- there is **no direct Human Gold registration workflow in the Training Studio yet**;
- R7J makes this explicit in the UI rather than implying that another Training Studio button creates Human Gold;
- adding a governed Human Gold authoring/import workflow requires a separate explicit contract because provenance/verification authority differs from ordinary local training registration.

## 4. Shared runtime profile contract

`resolve_workspace_runtime_profile(workspace, store)` is the single foundation resolver for Training Studio runtime defaults.

Precedence:

1. saved `selected_runtime_profile_id` if loadable;
2. deterministic local autodetection fallback.

This prevents the application from showing one runtime profile in Settings while OCR/ASR silently execute with unrelated PATH/default values.

## 5. Background-operation contract

Long operations covered by R7J:

- HUD automatic correction;
- OCR exact-frame extraction + Tesseract;
- FasterWhisper transcription/mining;
- pre-existing long candidate jobs already routed through the common helper.

Rules:

- at most one bounded Training Studio background operation at a time;
- worker thread never calls Tk APIs;
- Tk owns polling and success/failure UI;
- ProductError code/details and chained cause are captured by diagnostics;
- failures are fail-visible and never silently promoted to candidates/training truth.

## 6. Diagnostics contract

R7H opt-in diagnostics remain the canonical support path. R7J extends operation-level observability with:

- `TRAINING_OPERATION_FAILED`
- `BACKGROUND_OPERATION_FAILED`
- `HUD_PROFILE_DISAMBIGUATED`
- `TRANSPORT_ACTION action=seek_bar`
- `TRANSPORT_SEEK_FAILED`

When `BAI_DIAGNOSTICS.ENABLE` exists beside the packaged EXE, `diagnostics/latest.jsonl` is sufficient for the next support iteration unless source state itself becomes ambiguous.

## 7. Acceptance criteria

### Local/source gates

- new R7J focused tests PASS;
- TASK-049/050/051 regression PASS except display-only skip where no Tk display exists;
- R7A accepted-source hash synchronized;
- `py_compile`, `compileall`, `git diff --check` PASS.

### Windows Human Acceptance gates

1. HUD playback no longer visibly flickers.
2. HUD auto-correction keeps the window responsive and exposes progress/failure.
3. Ambiguous HUD profiles open a choice modal in batch, single-image and OCR routes; no silent first-match.
4. non-HUD Shared Media views retain a practically usable, full-source Fit-to-View.
5. timeline seek bar can move through long recordings without button-only stepping.
6. OCR uses the saved Runtime Profile and can extract/register a real candidate, or emits a diagnostic root cause.
7. notification categories are not limited to chase.
8. FasterWhisper uses selected runtime/cache settings and either produces candidates or emits actionable diagnostics with underlying cause.
9. a notification registered/edited under `右上通知を学習` appears in `学習・登録データを確認 > 右上通知` upon navigation without a separate manual refresh requirement.
10. Human Gold explanation matches actual Product behavior and does not falsely claim a direct registration path.

Any correctness failure remains a TASK-051 blocker. R7J does not itself authorize Task closure or Release.
