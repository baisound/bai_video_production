# TASK-051 R7 Human Acceptance Checklist

After automated R7 passes, launch the normal Training Studio with a real DBD recording and verify:

- HUD位置を設定: saved perk slots visually match the calibrated frame.
- 動画から学習: active HUD profile is shown; perk 1–4 Crop positions match calibration.
- 12-button transport: all transport/jump buttons operate at the expected positions.
- 画像を追加登録: video-first Crop path works; direct-image path is clearly secondary.
- 右上通知を学習: upper-right OCR candidate can be extracted, corrected, and registered.
- 実況・豆知識を登録: candidate mining/list/edit/verify/reject flows are understandable.
- 学習・登録データを確認: six review subtabs and counts/zero states are correct.
- Backup/Restore still targets the active workspace.

Record failures with tab, action, source video resolution, frame number, and screenshot.
Do not close TASK-051 while a correctness-affecting Human Acceptance issue remains.

## R7E Playback Finalization acceptance

Before continuing the remaining checklist, verify the HUD Calibration playback blocker is closed with a real DBD recording:

- `プレビューを読み込む` returns a usable frame without multi-second repeated extraction stalls.
- `再生` begins promptly and looks like continuous video rather than repeated frozen still frames.
- playback clock remains close to wall time; if rendering falls behind, obsolete frames are dropped instead of accumulating delay.
- `停止` responds while playback is active.
- `-1フレーム` / `+1フレーム` are responsive near the current position.
- `-1秒` / `+1秒` and `-10秒` / `+10秒` do not freeze the GUI.
- `巻き戻し` and `早送り` advance/retreat the canonical frame position without unbounded lag.
- HUD ROI overlays remain aligned with the displayed frame after play, stop and seek.
- changing the source video never paints a stale frame from the previous source.
- closing the window leaves no visible decoder error and the next packaged rebuild is not blocked by a leaked Training Studio process.

If any item fails, record it as a new bounded Human Acceptance finding and do not close TASK-051.

## R7G Shared Video Playback Canonicalization

Before TASK-051 closure, verify the same persistent playback behavior on all five surfaces:

1. `HUD位置を設定`
2. `動画から学習`
3. `画像を追加登録`
4. `右上通知を学習`
5. `実況・豆知識を登録 > 動画から候補を作る`

For each surface:

- select a real DbD video;
- Play visibly advances the preview, not only the frame counter;
- Stop responds promptly;
- ±1 frame and ±1/±10 second jumps update the preview;
- no long-term playback lag accumulates;
- switching the source never paints a stale frame from the previous video;
- the UI remains responsive during playback.

Feature-specific correctness remains separate: HUD/Crop/OCR/Trivia outputs must still be generated from the selected exact source/frame through their existing domain services. A preview image alone is not acceptance evidence for teacher-data correctness.

## R7H Shared Preview Delivery + Diagnostics acceptance

Before continuing TASK-051 closure, verify the R7H shared delivery boundary on Windows:

1. Place an empty `BAI_DIAGNOSTICS.ENABLE` beside `BAI DbD Training Studio.exe`.
2. Launch the EXE and confirm `診断ログ: ON` is visible.
3. Confirm `<EXE>/diagnostics/latest.jsonl` is created.
4. On each of the five R7G shared playback surfaces, select the same real DBD recording and press `再生`.
5. The preview must visibly paint moving frames; frame-counter-only progression is FAIL.
6. Stop, ±1 frame, ±1/±10 seconds and source switching must remain responsive.
7. When a frame is visible, the log must contain the chain `FRAME_DECODED -> FRAME_MAILBOX_PUT -> FRAME_MAILBOX_GET -> ... -> TK_FRAME_PAINTED` for the corresponding `feature/player_id`.
8. No full local video path, credential, token or raw frame payload may appear in the JSONL.
9. Remove `BAI_DIAGNOSTICS.ENABLE`, relaunch, and confirm detailed diagnostics are OFF and no new diagnostics session is created.

If playback fails, send `diagnostics/latest.jsonl` with the screenshot/action. Do not request a new repository ZIP unless the log and current patch state are insufficient to reconstruct the defect.

## R7I Shared Media + Training Workflow acceptance

R7I is not accepted until the same real DBD recording proves the following on the packaged Windows Training Studio.

### Shared Media safety floor — all five media surfaces

Surfaces:

1. `HUD位置を設定`
2. `動画から一括学習`
3. `画像学習データ > 動画から登録`
4. `右上通知を学習 > 動画から抽出`
5. `実況・豆知識を登録 > 動画から候補を作る`

For every surface:

- the **entire source frame** is visible by default with aspect ratio preserved; Crop-to-fill is forbidden;
- top-left, top-right, bottom-left and bottom-right source corners remain visible;
- for a normal survivor HUD frame, perk 1/2/3/4 remain visible and selectable;
- form overflow scrolls instead of shrinking/cropping the media surface below its protected minimum;
- window resize refits the full frame without losing HUD/ROI alignment;
- all canonical 12 controls are present and preserve this order/meaning: `最初へ / 巻き戻し / 停止 / 再生 / 早送り / 最後へ / -10秒 / -1秒 / -1フレーム / +1フレーム / +1秒 / +10秒`;
- normal `再生` produces **audible source audio** together with moving video;
- volume slider changes output level and mute silences/restores audio;
- Stop, manual seek, frame step, rewind and fast-forward do not leave stale audio playing;
- the UI remains responsive and no obsolete frame from an earlier source is painted;
- with `BAI_DIAGNOSTICS.ENABLE`, `diagnostics/latest.jsonl` can distinguish video-decode/render and audio-output stages without exposing raw media, credentials or full local paths.

### 動画から一括学習

- upper settings pane is scrollable and approximately bounded to half the usable height;
- lower Shared Media remains usable and fully visible;
- PERK slot labels are exactly `パーク1（上向き） / パーク2（右向き） / パーク3（下向き） / パーク4（左向き）`;
- display state, image group, optional HUD JSON and frame extraction range are available;
- a bounded frame range x selected targets produces staged exact Crop candidates;
- candidates are not silently promoted before explicit operator confirmation;
- bulk-confirmed records use the same visual-registration model as single/manual image registration and preserve `VIDEO_BATCH` provenance.

### 画像学習データ

- tab order is exactly `動画から登録 / 手動で登録 / 登録済み一覧`;
- direct still-image intake exists under `手動で登録`, not as a competing fourth workflow;
- `動画から登録` provides dynamic PERK / ITEM / ADDON controls and Search buttons;
- Search opens the common game-element picker and persists canonical `entity_id`;
- registered records can be opened through an Edit modal without rewriting the original image/provenance identity;
- video single registration preserves `VIDEO_SINGLE`; still-image registration preserves `MANUAL_IMAGE`.

### 右上通知を学習

- tab order is exactly `動画から抽出 / 手動で登録 / 登録済み一覧`;
- video extraction uses the same Shared Media surface and audible playback;
- OCR candidate, corrected notification data and semantics remain clearly separated;
- registered notification edit opens a modal and persists through the existing governed stores.

### 実況・豆知識を登録

- tab order is exactly `動画から候補を作る / 手動で登録 / 登録済み・候補一覧`;
- the operator can hear the source audio while selecting/transcribing the candidate range;
- model/device/compute/language settings do not clip the media viewport;
- list editing opens a modal and creates a new revision rather than rewriting historical revisions.

### Stop conditions

Any clipped source edge, invisible perk slot, missing canonical media control, silent normal playback when the source has audio, stale audio after stop/seek, incorrect exact Crop/ROI, or modal edit that corrupts provenance is a TASK-051 Human Acceptance blocker. Do not commit/close TASK-051 as complete while such a finding remains unresolved.

## R7J Human Acceptance Stabilization

After R7I/R7H media acceptance, verify the Human Acceptance findings promoted into R7J:

### HUD calibration

- playback no longer visibly flickers while frame/ROI overlay advances;
- `自動補正をテスト` immediately shows an executing state and the window remains responsive;
- successful automatic correction returns normally; failure is fail-visible and writes diagnostics;
- the full source frame and all four perk positions remain visible.

### HUD profile ambiguity

For `動画から一括学習`, `画像学習データ > 動画から登録` and `右上通知を学習 > 動画から抽出`:

- when multiple profiles match, a HUD selection modal appears;
- the operator can select the intended profile or cancel;
- no first profile is silently selected;
- after selection, the workflow continues using that exact profile and the explicit HUD JSON/profile field reflects it.

### Shared Media size and long-video navigation

- non-HUD media surfaces are large enough to judge gameplay/HUD detail without source clipping;
- the common `タイムシーク` bar is present on every Shared Media transport;
- dragging/releasing seeks to the expected approximate timestamp and displays the exact resulting canonical frame;
- the canonical 12 buttons remain present and unchanged;
- seek does not leave stale audio/video state.

### Upper-right notification learning

- notification type choices include the expanded baseline set, not only `チェイス関連通知`;
- `現在フレームからOCR候補を抽出` uses the selected Runtime Profile Tesseract path;
- a real candidate can be corrected/registered, or failure produces an actionable `diagnostics/latest.jsonl` entry;
- a record visible in `右上通知を学習 > 登録済み一覧` appears in `学習・登録データを確認 > 右上通知` when navigating to the review screen without requiring an extra manual refresh;
- review semantics/meaning matches the registered value.

### Trivia / commentary mining

- model/device/compute settings initially reflect the active Runtime Profile;
- the configured model cache is reused;
- real source transcription either produces candidates or records `BACKGROUND_OPERATION_FAILED` with ProductError code/details and chained-cause information;
- no failed transcript is silently promoted to verified trivia/commentary.

### Human Gold clarity

- `Human Gold / その他` explicitly explains that Human Gold is externally supplied or separately human-corrected ground-truth Evidence;
- the UI does not claim that ordinary Training Studio image/OCR/trivia registration automatically creates Human Gold;
- absence of a direct Human Gold authoring/import operation is visible as the current Product boundary.

Any failure above remains a TASK-051 Human Acceptance blocker and must be corrected before final commit/closure.
