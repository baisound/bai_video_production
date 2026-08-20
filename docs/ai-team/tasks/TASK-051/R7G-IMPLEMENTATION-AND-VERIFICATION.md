# TASK-051 R7G — Implementation and Verification Evidence

Status: `IMPLEMENTED / HOSTED_PASS / WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

## Implemented

- added `dbd_training_video_player.py` as the single Training Studio playback composition boundary;
- added `TkTrainingVideoSession` for persistent worker ownership, metadata caching, stale-source rejection, UI dispatch, transport composition and cleanup;
- added `TkTrainingVideoPlayer` for the standard split preview + transport UI;
- migrated `動画から学習` to `TkTrainingVideoPlayer`;
- migrated `画像を追加登録` to `TkTrainingVideoPlayer`;
- migrated `右上通知を学習` to `TkTrainingVideoPlayer`;
- migrated `実況・豆知識を登録 > 動画から候補を作る` to `TkTrainingVideoPlayer`;
- migrated HUD calibration playback plumbing to `TkTrainingVideoSession` while retaining the ROI Canvas painter;
- retained exact `FFmpegFrameInspector` only where canonical Crop/HUD/OCR extraction still requires exact-frame evidence;
- rebound accepted-source SHA to the R7G Training Studio revision.

## Architectural result

Before:

```text
HUD calibration -> Persistent PyAV
other four flows -> per-tab FFmpeg PGM preview
```

After:

```text
all five flows -> TkTrainingVideoSession -> PersistentPreviewWorker -> PyAV
```

Standard tabs additionally share the same `TkTrainingVideoPlayer` split UI.

## Verification

The bounded TASK-051 test suite and broader repository regression are recorded by the delivery README generated with this patch. Windows EXE build and Human Acceptance remain required because hosted tests cannot prove real Tk/PyInstaller rendering performance on the Owner machine.
