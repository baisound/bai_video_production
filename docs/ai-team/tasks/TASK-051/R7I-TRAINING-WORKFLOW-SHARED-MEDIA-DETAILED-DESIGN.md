# TASK-051 R7I — Training Workflow & Shared Media UX Consolidation Detailed Design

## 1. Document control

- Task: `TASK-051 — DbD Training Studio Operational UX Hardening / Unified Learning Workflow`
- Unit: `R7I`
- Profile: `DEV-3 HIGH ASSURANCE`
- Owner direction: reorganize video-learning/image/OCR/trivia workflows, preserve all twelve media controls, add audible playback, guarantee full-video Fit-to-View, and eliminate duplicated media implementations.
- Status: `IMPLEMENTED / LOCAL VERIFICATION PASS / WINDOWS HUMAN ACCEPTANCE REQUIRED`
- Parent units: R7E persistent playback, R7F callback starvation fix, R7G shared playback canonicalization, R7H Tk-main-thread delivery + diagnostics.
- Product boundary: BAI VIDEO PRODUCTION only. BAI Development OS is governance, not runtime dependency.

## 2. Authority and bounded implementation scope

The Owner explicitly requested detailed design and development for this bounded Training Studio continuation. This unit remains inside TASK-051 R7 Windows/Human Acceptance responsibility and does not reopen completed TASK-050.

Allowed implementation files are bounded to:

- `src/ai_video_production/dbd_training_studio.py`
- `src/ai_video_production/dbd_training_video_player.py`
- `src/ai_video_production/dbd_training_audio.py`
- `src/ai_video_production/dbd_video_transport.py`
- `src/ai_video_production/dbd_training_ui_components.py`
- `src/ai_video_production/dbd_training_workspace.py`
- `src/ai_video_production/dbd_safe_visual_learning.py`
- impacted TASK-049/050/051 compatibility tests
- new `tests/test_task051_r7i_*.py`
- TASK-051 design/evidence/current-state/task-index documents.

No Release, Deploy, paid-provider execution, destructive Product migration, production credential use or direct main push is authorized by R7I.

## 3. Problem statement

Human Acceptance exposed four architectural UX defects rather than isolated button bugs:

1. media behavior had diverged between HUD calibration and the other learning surfaces;
2. `動画から学習` and `画像を追加登録` overlapped without a clear responsibility boundary;
3. form-heavy screens could consume the viewport until important video regions, including perk slots, were clipped or practically unusable;
4. playback was video-only from the operator's perspective even though trivia/learning decisions depend on the source audio.

R7I therefore treats playback as a **Shared Media** concern and training registration as a **Shared Visual Registration** concern. A screen may specialize workflow and exact-evidence extraction, but it may not own its own transport/audio/playback implementation.

## 4. Canonical workflow boundary

### 4.1 Video batch learning vs. single image registration

The two functions are not separate storage domains.

```text
動画から一括学習
  -> range x selected HUD slots
  -> multiple exact Crop candidates
  -> human preview/review
  -> bulk confirmation
  -> VisualTrainingSample

画像学習データ > 動画から登録
  -> one precise frame + one selected slot/game element
  -> exact Crop candidate
  -> human confirmation
  -> VisualTrainingSample

画像学習データ > 手動で登録
  -> existing still image + canonical game element
  -> VisualTrainingSample
```

The difference is **workflow cardinality and operator intent**, not the final training-data model.

- Batch path: efficient range/slot sampling and bulk confirmation.
- Video single path: precise one-frame, one-game-element registration.
- Manual path: no video dependency.

The final `VisualTrainingSample` records additive provenance:

- `registration_origin = LEGACY | VIDEO_BATCH | VIDEO_SINGLE | MANUAL_IMAGE`
- `slot`
- `display_state`
- `source_video`
- `source_frame`

Legacy CSV rows remain readable with defaults.

## 5. Top-level UI architecture

### 5.1 Video batch learning

Top-level name becomes `動画から一括学習`.

The page is vertically split. The upper settings pane may consume **at most approximately half** the usable height and is scrollable. The lower media pane retains at least half of the usable height.

```text
+---------------------------------------------------------------+
| upper scrollable form (max ~50%)                              |
| +-----------------------------+-----------------------------+ |
| | 学習元と学習対象            | 学習条件                    | |
| | 学習元動画 *                | 表示状態                    | |
| | 学習対象                    | 画像グループ                | |
| | perk1 up / perk2 right       | HUD JSON (advanced/optional)| |
| | perk3 down / perk4 left      | frame range / step / max   | |
| +-----------------------------+-----------------------------+ |
+---------------------------------------------------------------+
| lower Shared Media (>= ~50%)                                  |
| full video Fit-to-View + audio + canonical twelve controls   |
+---------------------------------------------------------------+
```

For PERK learning, slot labels remain canonical:

- `パーク1（上向き）`
- `パーク2（右向き）`
- `パーク3（下向き）`
- `パーク4（左向き）`

Other existing visual domains remain supported through the same dynamic slot specification rather than duplicating a separate screen.

### 5.2 Image training data

The former `画像を追加登録` surface becomes `画像学習データ` and owns three subtabs:

1. `動画から登録`
2. `手動で登録`
3. `登録済み一覧`

`既存画像から直接登録` is not a fourth workflow; it is moved into `手動で登録`.

#### Video registration

Upper half is media-first:

```text
+----------------------------------+----------------------------+
| full video preview              | 学習元動画 *               |
| + audible 1x playback           | optional HUD JSON          |
|                                  | twelve transport controls  |
|                                  | volume / mute              |
+----------------------------------+----------------------------+
```

Lower half is a two-column scrollable registration form:

- left: learning target + dynamic slot/game-element selector;
- right: display state, image group, source, notes, exact Crop preview/confirm.

Dynamic target behavior:

- PERK -> four perk slots, each with Search;
- ITEM -> item slot with Search;
- ADDON -> add-on 1 / add-on 2, each with Search.

Search opens the shared canonical `open_game_element_selector` modal. The persisted value is canonical `entity_id`, never the display alias.

#### Manual registration

Manual registration keeps still-image intake, target/game-element search, display state, image group, information source and notes. No video player is duplicated here.

#### Registered list

`登録済み一覧` supports direct modal edit. The modal can change target, canonical game element, slot, display state, group and notes while preserving original image/provenance identity unless an explicitly separate replacement workflow is introduced later.

## 6. Upper-right notification learning

`右上通知を学習` uses three subtabs:

1. `動画から抽出`
2. `手動で登録`
3. `登録済み一覧`

The video extraction tab uses the Shared Media player in its upper media pane. The lower two-column scrollable pane separates:

- OCR extraction/candidate list;
- corrected canonical notification data and semantic meaning.

Registered notification edits are modal and use the existing OCR vocabulary + semantic stores. OCR output is candidate evidence, not automatically verified truth.

## 7. Trivia/commentary workflow

The tab order is fixed as:

1. `動画から候補を作る`
2. `手動で登録`
3. `登録済み・候補一覧`

Video mining uses Shared Media so the operator can hear exactly what is being transcribed. Model/device/compute/language configuration is kept in the scrollable form pane, not allowed to compress the media viewport.

Editing an existing/candidate trivia record opens a modal and produces a new revision through the existing knowledge store. Historical revisions are not rewritten.

## 8. Shared Media contract

### 8.1 Canonical ownership

The canonical user-facing media classes are:

- `TkTrainingMediaSession`
- `TkTrainingMediaPlayer`

Legacy aliases `TkTrainingVideoSession` and `TkTrainingVideoPlayer` remain export-compatible for older callers/tests, but Training Studio R7I source must use the Media names.

The five surfaces are:

- HUD calibration -> shared MediaSession directly because it has custom ROI overlay painting;
- video batch learning -> Shared MediaPlayer;
- image video registration -> Shared MediaPlayer;
- upper-right notification extraction -> Shared MediaPlayer;
- trivia candidate mining -> Shared MediaPlayer.

### 8.2 Mandatory twelve transport controls

No surface may remove or reorder the canonical twelve actions:

```text
[最初へ] [巻き戻し] [停止] [再生] [早送り] [最後へ]
[-10秒]  [-1秒]     [-1フレーム] [+1フレーム] [+1秒] [+10秒]
```

The exact contract remains `BUTTON_LAYOUT` in `dbd_video_transport.py`.

### 8.3 Audio

Normal 1x `再生` includes source audio.

R7I uses a bounded `FfplayAudioController` because the Product already requires the FFmpeg toolchain for exact frame/OCR work. The controller:

- starts `ffplay -nodisp` at the transport position;
- supports volume 0..100;
- supports mute;
- terminates on stop/pause-like manual operation, source change or session close;
- mutes rewind/fast-forward/frame stepping rather than introducing unsafe time-stretch behavior;
- can resolve `ffplay` from explicit `BVP_FFPLAY`, PATH, or a sibling of configured `BVP_FFMPEG` / `BVP_FFPROBE`.

If ffplay is unavailable, video remains usable and the UI reports the missing audio backend rather than crashing. Windows Human Acceptance must nevertheless prove audible normal playback on the intended packaged environment.

### 8.4 Playback timing

Video continues to use the R7E/R7H wall-clock persistent PyAV pipeline. The transport position is the synchronization origin. Audio starts at that exact position when entering normal PLAYING state. Rewind/fast-forward/step operations stop audio; returning to PLAY restarts audio from the resulting position.

## 9. Fit-to-View safety floor

A media workflow is unusable if any source edge or HUD element is clipped. Therefore **Fit-to-View is mandatory, not an optional zoom mode**.

Rules:

- preserve source aspect ratio;
- never Crop source content to fill a widget;
- black letterboxing is allowed;
- forms scroll instead of consuming the media viewport;
- the vertical split reserves at least ~50% for media; HUD uses ~55% because ROI work is precision-critical;
- resizing the window triggers refit;
- HUD overlay coordinates use the displayed preview geometry plus letterbox offset;
- mouse drag coordinates subtract the letterbox offset before source-coordinate conversion.

Human Acceptance requires all four video corners and all four perk positions to remain visible at normal supported window sizes.

## 10. Exact evidence boundary

Shared Media frames are preview state only. They may be dropped/coalesced for playback responsiveness.

Canonical teacher data still uses exact source operations:

- `SafeVisualLearningService` exact Crop extraction;
- HUD ROI/profile exact source coordinates;
- OCR exact frame + ROI extraction;
- FasterWhisper source media/transcript pipeline.

A displayed preview frame is never silently persisted as teacher data.

## 11. Batch range safety

`動画から一括学習` now makes the displayed frame-range controls operational.

`SafeVisualLearningService.preview_video_batch()` creates exact staged samples for:

```text
frames = range(start_frame, end_frame_exclusive, frame_step)
total = len(frames) * len(selected_targets)
```

`total` must not exceed `max_samples`. This is a **total Crop candidate ceiling across frames and selected slots**, not a per-slot loophole. The operation stages exact Crop files first; only explicit bulk confirmation appends them to the visual manifest.

The UI renders a bounded thumbnail subset (first 12) when the candidate set is larger, while preserving all staged candidates for confirmation. Long extraction runs off the Tk event loop.

## 12. Background-thread UI ownership

R7H established that worker threads must not invoke Tk APIs. R7I extends this rule to generic long-running Training Studio jobs.

`run_background()` uses a Python `queue.Queue`; the worker only places an outcome. A Tk-main-thread `root.after` poll owns status/dialog callbacks. This avoids reintroducing the R7H cross-thread Tk problem in batch/OCR/ASR workflows.

## 13. Diagnostics

The existing opt-in marker remains canonical:

```text
<EXE directory>/BAI_DIAGNOSTICS.ENABLE
```

When present, `diagnostics/latest.jsonl` records shared media stages. R7I adds audio events including:

- `AUDIO_OUTPUT_STARTED`
- `AUDIO_OUTPUT_STOPPED`
- `AUDIO_OUTPUT_UNAVAILABLE`
- `AUDIO_OUTPUT_START_FAILED`
- `AUDIO_VOLUME_CHANGED`
- `AUDIO_MUTE_CHANGED`

Paths are sanitized by the existing diagnostics foundation. Audio/video content itself is never logged.

## 14. Failure modes and controls

| Failure | Control |
|---|---|
| form growth clips video | scrollable form + media minimum-height binding |
| hidden perk/HUD corner | Fit-to-View, no fill-crop |
| one tab develops different playback controls | one canonical Shared Media component |
| audio continues after stop/source switch | session state listener terminates controller |
| ffplay missing | visible status + diagnostic event; no Product crash |
| batch range explodes to thousands of Crops | total `max_samples` bound |
| background job touches Tk | Python outcome queue + Tk-owned poll |
| visual relabel loses new provenance fields | review service preserves additive metadata |
| selector display alias persisted as truth | modal returns canonical `entity_id` |
| preview frame becomes teacher data | exact evidence services remain separate |

## 15. Automated acceptance

R7I requires:

- all twelve transport labels exact and ordered;
- normal play audio-controller start at requested position;
- stop/rewind/fast-forward stop audio;
- four standard surfaces use `TkTrainingMediaPlayer` and HUD uses `TkTrainingMediaSession`;
- five media surfaces reserve minimum height;
- Fit-to-View implementation contains no Crop-to-fill path;
- three-tab image workflow;
- three-tab notification workflow;
- required trivia tab ordering;
- modal edit routes present;
- visual registration metadata round-trips and survives relabel;
- batch range/total candidate bound;
- TASK-049/050/051 regressions pass;
- source accepted-hash gate rebased only after final source is frozen.

## 16. Windows Human Acceptance

The unit remains open until the packaged Windows EXE passes, using real DBD media:

1. every media surface displays the entire frame without clipping;
2. perk 1..4 are all visible and selectable in HUD work;
3. all twelve controls function consistently on all five surfaces;
4. `再生` produces both moving video and audible source audio;
5. stop/jump/frame-step do not leave stale audio playing;
6. volume and mute work;
7. image video/manual/list tabs work and modal editing persists;
8. OCR extraction/manual/list + edit work;
9. trivia video/manual/list + edit work;
10. batch range stages the expected bounded candidate count and requires confirmation;
11. diagnostics can be enabled by marker and `latest.jsonl` is sufficient for ordinary follow-up.

## 17. Stop conditions

R7I must not be accepted or committed as Human-Accepted if:

- any required media surface still owns a duplicate transport implementation;
- any of the twelve transport actions is missing;
- source audio is unavailable during normal playback in the accepted Windows environment;
- the video is clipped such that a corner/perk slot cannot be seen;
- batch/single/manual visual registration diverges into incompatible storage semantics;
- exact evidence can be replaced by a dropped/coalesced preview frame;
- a High/Critical regression remains unresolved.
