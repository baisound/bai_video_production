# TASK-051 R7H — Shared Preview Delivery Hardening & Opt-In Diagnostics Detailed Design

## 1. Document control

- Task: `TASK-051`
- Unit: `R7H`
- Profile: `DEV-3 HIGH ASSURANCE`
- Status: `IMPLEMENTED / LOCAL PASS / WINDOWS HA PENDING`
- Trigger: Windows Human Acceptance finding `R7H-001 / SHARED_PREVIEW_FRAME_NOT_PAINTED`
- Scope: shared Training Studio preview delivery/render boundary plus opt-in diagnostics
- Out of scope: teacher-data extraction semantics, OCR/ASR/Crop correctness, model changes, release/deploy

## 2. Problem statement

R7G canonicalized five Training Studio video surfaces onto the persistent PyAV playback contract, but Windows Human Acceptance showed that the transport clock and frame counter advance while the preview remains black. The existing shared session allows the decoder worker callback to invoke `root.after(...)` from the background decoder thread and silently discards exceptions. Automated tests use fake roots and therefore did not prove the real Windows Tk delivery/render path.

The fix must preserve the R7G shared-player architecture. Reverting individual tabs to separate FFmpeg/Tk implementations is prohibited because it would restore duplicated playback specifications.

## 3. Root-cause findings and safety conclusion

R7H investigation confirmed two independent defects in the shared display boundary. The first is deterministic and directly reproducible with a real Tk interpreter: the R7E/R7G renderer passed a **base64 text string** while forcing `format="PGM"`; real Tk returned `TclError: image format "PGM" is not supported`. The same binary PGM payload succeeds when passed as raw `bytes` and allowed to auto-detect from the `P5` header. R7H therefore changes `PersistentPreviewFrame.tk_photo_data()` to return binary PGM bytes and removes the forced `format="PGM"`.

The second defect is architectural: the worker-to-Tk delivery boundary allowed a background decoder callback to invoke `root.after(...)` and swallowed failures. Even after the image-format defect is fixed, that ownership model is not accepted for the shared playback foundation.

The prior boundary was:

```text
Persistent PyAV worker thread
  -> callback
  -> root.after(...)
  -> Tk event queue/render
```

Tk ownership is made explicit in R7H:

```text
Decoder thread
  -> Python-only one-slot mailbox

Tk main thread
  -> periodic mailbox drain via root.after
  -> PhotoImage
  -> Label/Canvas paint
```

No Tk API is callable from the decoder worker after R7H.

## 4. Canonical architecture

### 4.1 Producer side

`PersistentPreviewWorker` remains latest-request-wins and owns the PyAV container/decoder. A completed result calls a Python callback whose only effect is to replace the one-slot `_LatestFrameMailbox` payload. The callback may run on the worker thread but must not call Tk.

### 4.2 Consumer side

`TkTrainingVideoSession` starts a self-rescheduling UI poll only when attached to a real Tk root. The poll drains at most the newest mailbox item and performs all source-staleness checks, error surfacing and `on_frame(...)` invocation on the UI thread.

### 4.3 Boundedness

The UI mailbox has capacity one. A newer completed frame replaces an older unpainted frame. This preserves the R7E/R7F design objective: playback follows wall time instead of accumulating an unbounded callback backlog.

### 4.4 Exact evidence boundary

The shared preview remains noncanonical display state. HUD/Crop/OCR/Trivia registration continues to use the existing exact-source/frame domain services. Preview frame dropping cannot silently become teacher-data evidence.

## 5. Diagnostics foundation

### 5.1 Operator contract

Diagnostics are OFF by default. They are enabled only when the following empty marker exists beside the packaged EXE:

```text
BAI_DIAGNOSTICS.ENABLE
```

When enabled, the Product creates:

```text
<EXE directory>/diagnostics/latest.jsonl
```

The UI shows `診断ログ: ON` and the relative log location.

### 5.2 Runtime path rule

- Packaged mode: marker/log root = `Path(sys.executable).parent`.
- Source/development mode: marker/log root = current working directory.

No environment variable or hidden registry setting is required for normal operator use.

### 5.3 Structured events

At minimum the shared playback path records:

- `APP_START` / `APP_EXIT`
- `DIAGNOSTICS_ENABLED`
- `PLAYBACK_CLOCK_STARTED` / `PLAYBACK_TICK` / `TRANSPORT_ACTION`
- `FRAME_REQUESTED`
- `PYAV_DECODER_OPEN_STARTED` / `PYAV_DECODER_OPENED`
- `FRAME_DECODE_STARTED` / `FRAME_DECODED` / `FRAME_DECODE_FAILED`
- `FRAME_REQUEST_COALESCED`
- `FRAME_MAILBOX_PUT` / `FRAME_MAILBOX_DROP` / `FRAME_MAILBOX_GET`
- `FRAME_UI_STALE_SOURCE`
- `FRAME_UI_CALLBACK_STARTED` / `FRAME_UI_CALLBACK_COMPLETED` / `FRAME_UI_CALLBACK_FAILED`
- `TK_IMAGE_CREATE_STARTED` / `TK_IMAGE_CREATED` / `TK_IMAGE_CREATE_FAILED`
- `TK_WIDGET_UPDATE_STARTED` / `TK_FRAME_PAINTED`

Each event includes the shared `feature` and `player_id` so all five surfaces are distinguishable in one log.

### 5.4 Five feature identities

- `HUD_CALIBRATION / hud-calibration-player`
- `VIDEO_LEARNING / video-learning-player`
- `VISUAL_REGISTRATION / visual-registration-player`
- `NOTIFICATION_LEARNING / notification-learning-player`
- `TRIVIA_MINING / trivia-mining-player`

### 5.5 Performance rule

The decoder and Tk/UI threads never synchronously write log files. `DiagnosticLogger.emit()` uses a bounded non-blocking queue; a background diagnostics writer serializes JSONL. If the diagnostics queue fills, diagnostic events may be dropped and a later `DIAGNOSTIC_EVENTS_DROPPED` record summarizes the loss. Primary Product behavior must not block on diagnostics.

### 5.6 Retention

- `latest.jsonl` is the current session/operator handoff file.
- maximum file size: 20 MiB;
- up to five rotated generations are retained;
- previous `latest.jsonl` is rotated at next diagnostics-enabled startup.

### 5.7 Privacy / secret boundary

Diagnostics must not persist API keys, passwords, access tokens, cookies, Authorization headers or credential bodies. Path/source values are reduced to basename plus a short SHA-256 identity. Raw video frames, OCR bodies and transcript bodies are not logged by the playback diagnostics foundation.

## 6. Failure handling

Silent `except Exception: pass/return` at the shared playback delivery/render boundary is prohibited. A caught error that must not terminate Product execution is emitted as a structured `ERROR` event with stage, exception type, message and traceback. User-facing status remains concise.

Closing/destroyed Tk roots are treated as bounded lifecycle events: the UI poll is cancelled when possible, the mailbox is cleared, transport is stopped and the persistent worker is closed.

## 7. Test design

### 7.1 Deterministic unit tests

- worker callback deposits mailbox content but does not invoke Tk;
- main-thread mailbox drain invokes the frame callback;
- one-slot mailbox replaces older completed frames;
- source switching rejects stale deliveries;
- diagnostics are disabled without the marker;
- marker enables asynchronous JSONL;
- path values are privacy-minimized;
- diagnostics failures never become Product failures.

### 7.2 Real Tk contract

A real `tk.Tk()` test creates an in-memory binary PGM `PhotoImage`, binds it to a widget and runs `update_idletasks()`. During R7H implementation this test first reproduced the pre-fix failure (`image format "PGM" is not supported`) and then PASSed after changing the renderer to raw PGM bytes with header auto-detection. The test is skipped only when a display is unavailable. On the target Windows environment this must PASS.

### 7.3 Packaged smoke

The R7 packaged launcher/runner must:

1. create `BAI_DIAGNOSTICS.ENABLE` beside the packaged EXE;
2. load jsonschema resources and PyAV;
3. create a hidden real Tk root;
4. render a synthetic in-memory PGM image;
5. write `PACKAGED_TK_SMOKE_PASS` through the EXE-relative diagnostics logger;
6. verify `diagnostics/latest.jsonl` contains that event;
7. remove the marker after the smoke.

## 8. Human Acceptance

With `BAI_DIAGNOSTICS.ENABLE` beside the normal `BAI DbD Training Studio.exe`, use a real DBD recording on each shared playback surface. `再生` must visibly paint frames, not only advance the counter. If any surface fails, attach only `diagnostics/latest.jsonl` plus the action/screenshot; no source ZIP is required for ordinary follow-up diagnosis.

## 9. Stop conditions

R7H must not be accepted if any of the following remains:

- worker-thread code invokes Tk APIs;
- frame counter advances without `TK_FRAME_PAINTED` under normal playback;
- diagnostics can block decoder/UI execution;
- marker-off mode creates diagnostics files;
- logs expose secret values or full local source paths;
- packaged real-Tk smoke is absent or fails on Windows;
- a five-surface Human Acceptance blocker remains.
