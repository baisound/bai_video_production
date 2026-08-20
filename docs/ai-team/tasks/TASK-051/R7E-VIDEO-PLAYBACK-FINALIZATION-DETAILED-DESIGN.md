# TASK-051 R7E — Human Acceptance Video Playback Finalization Detailed Design

## 1. Control

- Task: `TASK-051 — DbD Training Studio UX Hardening`
- Atomic Unit: `R7E — HUMAN ACCEPTANCE VIDEO PLAYBACK FINALIZATION`
- Governance: `DEV-3 HIGH ASSURANCE`
- Trigger: Human Acceptance found that HUD Calibration video load/playback was too slow to execute the remaining acceptance checklist.
- Owner authority: explicit request on 2026-08-19 to perform detailed design and implementation through the final playback improvement.
- Scope class: bounded correction inside TASK-051 video-transport / HUD-calibration responsibility; no new Product domain or external side-effect authority.

## 2. Problem statement

The prior HA-003 performance correction removed decode-from-frame-zero behavior, moved FFmpeg work off the Tk thread, cached ffprobe data and coalesced stale requests. It still retained a structurally expensive playback loop:

1. Tk transport advanced by callback count rather than elapsed wall time;
2. each displayed frame could create a new FFmpeg subprocess;
3. each displayed frame was materialized to a PGM file and reopened by Tk;
4. continuous playback had no persistent decoder or recent-frame cache;
5. a slow preview renderer could make the displayed timeline permanently lag source time.

The Human Acceptance gate cannot proceed while the preview behaves like repeated still-image extraction rather than a responsive video preview.

## 3. Goals

R7E MUST:

- make `再生` use a persistent decoder rather than one FFmpeg process per frame;
- keep video decode outside Tk's UI thread;
- make continuous transport position derive from `time.monotonic()` wall time;
- bound rendering to a useful display cadence while dropping obsolete work;
- keep only the newest pending frame request;
- keep a bounded recent-frame ring for responsive nearby stepping/reverse operations;
- carry grayscale preview pixels in memory, avoiding per-frame preview-file writes;
- preserve exact source frame index as the canonical UI/ROI coordinate;
- discard stale results after source changes;
- close the decoder when the Training Studio window closes;
- preserve the existing 12-button transport contract and HUD ROI behavior;
- preserve the accepted-source drift gate while making its content hash portable across LF/CRLF checkout policy;
- keep PyAV explicitly available in the Windows build profile and packaged smoke gate.

## 4. Non-goals

R7E does NOT:

- introduce GPU/NVDEC/DXVA/QSV-specific decode policy;
- change recognition, OCR, FasterWhisper, Knowledge or HUD-profile schemas;
- change saved ROI normalization contracts;
- add audio playback/synchronization;
- claim Human Acceptance PASS without real DBD media verification;
- broaden Release, Deploy or external-effect authority.

## 5. Architecture

### 5.1 Continuous transport clock

`TkVideoTransportBar` keeps an immutable anchor of:

- transport state;
- source frame at start;
- monotonic start time.

Each UI refresh computes the desired source frame from elapsed wall time:

```text
PLAY             rate +1x
FAST_FORWARD     rate +4x
REWIND           rate -1x
```

The UI callback count no longer defines playback speed. If rendering is slow, intermediate source frames are skipped and the timeline catches up to elapsed wall time.

Preview refresh is bounded:

- normal play: no more than 30 visual refreshes/sec;
- fast-forward: no more than 20 visual refreshes/sec;
- rewind: no more than 10 visual refreshes/sec because reverse decode may require seeks.

The canonical `frame_index` remains source-FPS based.

### 5.2 Persistent PyAV decoder

New module: `src/ai_video_production/dbd_persistent_video_preview.py`.

`PyAVPersistentFrameDecoder`:

- opens one PyAV container for the active source;
- keeps the video decoder/iterator alive;
- uses sequential decode for nearby forward requests;
- uses PyAV seek only for backward or large jumps;
- scales to the bounded HUD preview geometry inside libav;
- converts to 8-bit grayscale in memory;
- strips plane row padding safely;
- retains a bounded `OrderedDict` ring of 24 recent preview frames;
- never persists Product media content outside the existing workspace contract.

The ring upper bound at 960x540 grayscale is approximately 12 MiB of raw pixel payload plus object overhead, preventing unbounded playback memory growth.

### 5.3 Latest-request-wins worker

`PersistentPreviewWorker` owns the decoder on one daemon worker thread.

Contract:

```text
Tk transport request N
        ↓
atomic pending slot
        ↓
request N+1 replaces N if N has not started
        ↓
decoder resolves latest target
        ↓
stale/newer generation check
        ↓
callback only for current/latest request
```

There is no unbounded frame queue.

### 5.4 Source generation / stale-result guard

Changing source increments a generation. A result generated for a prior source/generation is not painted into the current canvas.

Training Studio also checks exact source identity immediately before Tk painting.

### 5.5 In-memory Tk preview

The decoder returns `PersistentPreviewFrame` with:

- source identity;
- source frame index;
- source geometry;
- preview geometry;
- grayscale bytes.

The frame is converted to binary PGM **in memory**, base64 encoded, and passed to `tk.PhotoImage(data=..., format="PGM")`.

Continuous HUD playback no longer creates `transport-XXXXXXXXX.pgm` files.

The current displayed grayscale frame is stored as `GrayImage` in `calibration_state["preview_image"]`. HUD anchor creation uses that in-memory image; a legacy `preview_path` remains only as compatibility fallback.

### 5.6 Manual/jump behavior

The same persistent decoder handles:

- ±1 frame;
- ±1 second;
- ±10 seconds;
- first / last;
- play / rewind / fast-forward.

Nearby frame requests hit the ring cache. Large jumps seek inside the already-open PyAV container. Reverse requests backfill a bounded neighborhood so repeated reverse stepping does not force a seek for every single frame.

### 5.7 Packaging

The existing `windows-build` profile already installs PyAV through the pinned FasterWhisper dependency chain. R7E does not widen the dependency surface solely to duplicate that transitive pin. Instead, the normal PyInstaller spec explicitly includes `av` as a hidden import and R7 packaged smoke imports PyAV and requires a non-empty `av.__version__`. This makes the native runtime requirement observable and fail-closed at packaging acceptance.

## 6. Thread-safety and lifecycle

- All PyAV container operations occur on one worker thread.
- Tk widgets are touched only through `root.after(0, ...)` on the Tk thread.
- Worker callback exceptions cannot terminate the decoder thread.
- `<Destroy>` on the root closes the worker and invalidates pending requests.
- Source changes invalidate old results before repaint.

## 7. Failure modes / safe behavior

| Failure | Required behavior |
|---|---|
| PyAV missing | fail with actionable `.[windows-build]` instruction; no silent dependency install |
| no video stream | bounded error in HUD preview status; no GUI crash |
| source changed during decode | old generation discarded |
| decoder slower than source | obsolete frame requests dropped; clock remains current |
| reverse leaves ring | bounded PyAV seek/backfill |
| end of stream | return last available bounded result or explicit preview error |
| window closes | worker invalidated/closed; no new Tk update |

## 8. Allowed implementation files

- `src/ai_video_production/dbd_video_transport.py`
- `src/ai_video_production/dbd_persistent_video_preview.py` (new)
- `src/ai_video_production/dbd_training_studio.py`
- `pyproject.toml`
- `packaging/task049_training_studio.spec`
- `tools/task051/task051_training_studio_launcher.py`
- exact TASK-049/051 tests needed for packaging, transport and HUD preview
- this TASK-051 R7E design/evidence set

No schema, Knowledge DB, OCR, ASR, release metadata or BAI Development OS repository mutation is authorized by this unit.

## 9. Test plan

Required focused validation:

1. pure monotonic playback clock calculations and endpoint clamping;
2. in-memory PGM payload contract;
3. latest-request-wins coalescing;
4. source-generation stale result rejection;
5. fake-PyAV persistent open / seek / ring behavior;
6. Training Studio integration source contract;
7. existing R2 transport tests;
8. existing HUD-calibration / layout tests;
9. PyInstaller packaging contract and R7 smoke contract;
10. `py_compile` / `compileall` and `git diff --check`.

After local PASS, Windows Human Acceptance must still prove:

- prompt startup/load;
- smooth normal playback using real DBD recording;
- responsive ±1f / ±1s / ±10s;
- correct HUD overlay/frame alignment;
- no UI freeze;
- packaged runtime includes PyAV;
- no regression in the 12-button control positions.

## 10. Completion boundary

R7E implementation may be reported locally complete after required focused tests pass with Critical/High findings `0/0`. TASK-051 itself remains open until the real-media Human Acceptance checklist passes.
