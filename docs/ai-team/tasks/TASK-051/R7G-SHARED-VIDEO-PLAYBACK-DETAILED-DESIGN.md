# TASK-051 R7G — Shared Video Playback / Preview Canonicalization Detailed Design

Governance: `DEV-3 HIGH ASSURANCE`
Status: `IMPLEMENTED / HOSTED_VERIFICATION_PENDING_WINDOWS_HUMAN_ACCEPTANCE`

## 1. Problem statement

TASK-051 Human Acceptance exposed two incompatible video-preview implementations inside one Training Studio:

1. `HUD位置を設定` used the R7E/R7F persistent PyAV preview pipeline.
2. `動画から学習`、`画像を追加登録`、`右上通知を学習`、`実況・豆知識を登録 > 動画から候補を作る` still created per-surface preview functions around `FFmpegFrameInspector.extract_preview_pgm()` and `TkVideoTransportBar`.

This duplicated playback policy and let a performance/correctness fix land in only one surface. The result was a split Product contract: the HUD tab had current playback behavior while other user-facing learning flows retained the older preview path.

## 2. Owner intent

All user-facing Training Studio video playback MUST resolve through one canonical implementation so future fixes are made once and inherited by every learning flow.

The following five surfaces are in scope:

- HUD位置を設定;
- 動画から学習;
- 画像を追加登録;
- 右上通知を学習;
- 実況・豆知識を登録 > 動画から候補を作る.

## 3. Critical boundary — preview is not training evidence

Commonization applies to **interactive preview and transport only**.

Exact training/crop/OCR/HUD evidence extraction remains owned by the existing exact-frame services:

- `FFmpegFrameInspector` where exact geometry/frame material is required;
- `SafeVisualLearningService` for staged/confirmed visual evidence;
- OCR/trivia workspace services for candidate generation;
- HUD profile resolver/editor for canonical ROI state.

The shared player MUST NOT cause a displayed/rescaled preview frame to become canonical teacher data.

## 4. Canonical architecture

```text
Training Studio surface
  │
  ├─ source_getter / frame_getter / frame_setter
  │
  ▼
TkTrainingVideoSession                 <- canonical playback controller
  ├─ TkVideoTransportBar               <- 12-button transport / monotonic clock
  ├─ metadata resolution/cache
  ├─ source-staleness guard
  ├─ Tk UI-thread dispatch
  ├─ lifecycle cleanup
  └─ PersistentPreviewWorker
       └─ PyAVPersistentFrameDecoder
            ├─ one persistent decoder/container per surface
            ├─ latest-request-wins coalescing
            ├─ bounded ring cache
            └─ in-memory grayscale preview
```

Standard learning tabs use:

```text
TkTrainingVideoPlayer
  ├─ left: 動画プレビュー
  └─ right: canonical TkVideoTransportBar
```

HUD calibration uses the same `TkTrainingVideoSession`, but keeps its custom Canvas renderer because ROI overlays and drag editing are domain-specific UI responsibilities.

## 5. State isolation

The implementation shares **code and behavior**, not one mutable decoder across all tabs.

Each video surface owns one `TkTrainingVideoSession` instance. This prevents:

- one tab changing another tab's selected source;
- frame-position coupling across independent forms;
- stale frame callbacks painting into a different tab;
- cross-tab decoder lifecycle ambiguity.

## 6. Playback contract

Every in-scope surface receives the same behavior:

- persistent PyAV decode;
- no per-frame FFmpeg subprocess for interactive playback;
- no per-frame preview PGM file for interactive playback;
- monotonic-clock transport;
- latest-request coalescing;
- completed-frame delivery preserved by R7F;
- bounded recent-frame cache;
- source change staleness rejection;
- Tk callback dispatch through `root.after(0, ...)`;
- bounded worker shutdown on root destruction.

## 7. UI contract

Standard video learning panels use the shared split composition:

```text
┌───────────────────────────────┬────────────────────────────┐
│ 動画プレビュー                │ 動画操作                   │
│ persistent PyAV preview       │ first/rewind/stop/play/... │
└───────────────────────────────┴────────────────────────────┘
```

HUD calibration preserves its existing lower split:

- left: ROI overlay Canvas;
- right: video transport + HUD profile controls.

## 8. Failure handling

- no source: show/status `動画を選択してください。`;
- metadata failure: report through the surface status/error callback;
- stale source completion: discard before UI paint;
- worker decode failure: report without killing the worker owner/UI thread;
- root destruction: stop transport and close worker;
- exact extraction failure: remains handled by the existing feature-specific operation error path.

## 9. Allowed files

- `src/ai_video_production/dbd_training_video_player.py`
- `src/ai_video_production/dbd_training_studio.py`
- TASK-051 video/UI integration tests
- TASK-051 R7G design/evidence/review/checklist artifacts
- `tests/test_task051_r7a_source_gate.py` only to bind the new accepted source revision
- `docs/ai-team/current-state.md` for current R7 Human Acceptance position synchronization

## 10. Explicitly out of scope

- changing OCR recognition semantics;
- changing visual teacher-data schemas;
- changing trivia extraction semantics;
- changing HUD ROI math;
- GPU-specific decode activation;
- Release/Deploy/Production changes;
- committing or pushing the user's worktree.

## 11. Acceptance criteria

Automated:

- all TASK-051 tests pass;
- shared session tests prove metadata caching, source-stale rejection and cleanup;
- Training Studio source contains four `TkTrainingVideoPlayer` instances and one custom-HUD `TkTrainingVideoSession`;
- old per-tab `render_*_frame` preview implementations are absent;
- py_compile/compileall/diff-check pass;
- full repository pytest has no new failure.

Windows Human Acceptance:

- all five surfaces display and operate the same persistent playback behavior;
- play/stop/jump controls update the corresponding preview;
- no surface falls back to old disk-PGM interactive playback;
- exact Crop/OCR/HUD registration still uses the selected canonical frame and remains correct.
