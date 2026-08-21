# TASK-051 R7E — Video Playback Finalization Implementation and Verification

## Status

`IMPLEMENTED / LOCAL_HIGH_ASSURANCE_PASS / WINDOWS_HUMAN_ACCEPTANCE_PENDING`

TASK-051 itself remains open. This record does not claim Human Acceptance, release, deployment or Product completion.

## Implemented scope

- Added `dbd_persistent_video_preview.py` with a single persistent PyAV container/decoder owned by one worker thread.
- Added bounded 24-frame recent preview ring.
- Added latest-request-wins coalescing and source-generation stale-result rejection.
- Replaced per-frame HUD calibration preview files with in-memory binary PGM -> Tk `PhotoImage(data=...)` rendering.
- Added in-memory `GrayImage` retention for HUD anchor creation.
- Changed continuous transport progression to `time.monotonic()` wall-clock anchoring.
- Capped visual refresh while allowing canonical source-frame position to catch up when decoding/rendering is slower than source FPS.
- Preserved the 12-button transport layout and exact frame-index field semantics.
- Added worker shutdown on root-window destruction.
- Added an explicit PyInstaller `av` hidden import and packaged runtime smoke; the existing Windows build profile already installs PyAV through the pinned FasterWhisper dependency chain.
- Strengthened R7 packaged smoke to require a working PyAV runtime.
- Rebased the TASK-051 accepted-source SHA gate to the R7E Training Studio source.

## Changed files

Product/runtime:

- `src/ai_video_production/dbd_persistent_video_preview.py` (new)
- `src/ai_video_production/dbd_video_transport.py`
- `src/ai_video_production/dbd_training_studio.py`
- `pyproject.toml`
- `packaging/task049_training_studio.spec`
- `tools/task051/task051_training_studio_launcher.py`

Tests:

- `tests/test_task051_r7e_persistent_video_playback.py` (new)
- `tests/test_task051_r7e_training_studio_playback_integration.py` (new)
- `tests/test_task051_r2_training_studio_transport_integration.py`
- `tests/test_task051_ha003_hud_media_performance.py`
- `tests/test_task049_dbd_training_studio_packaging.py`
- `tests/test_task051_r7_acceptance_gate.py`
- `tests/test_task051_r7a_source_gate.py`

Documentation:

- `R7E-VIDEO-PLAYBACK-FINALIZATION-DETAILED-DESIGN.md` (new)
- `R7E-IMPLEMENTATION-AND-VERIFICATION.md` (this file)
- `R7-HUMAN-ACCEPTANCE-CHECKLIST.md` (R7E acceptance extension)

## Verification

### Focused playback / HUD / packaging

```text
56 passed
```

Coverage includes:

- monotonic playback clock;
- in-memory PGM frame contract;
- latest-request coalescing;
- source-generation invalidation;
- fake-PyAV persistent open/seek/ring behavior;
- HUD calibration integration;
- existing R2 transport and HUD-layout regression;
- normal PyInstaller package contract;
- R7 packaged smoke contract.

### TASK-051 lineage

```text
41 passed
```

R1–R6 and TASK-050 follow-up lineage remained green.

### Repository-wide partitioned regression in supplied snapshot

The supplied snapshot is missing the README-linked file
`docs/design/TASK-006_SUBTITLE-WORKSPACE_詳細設計_Ver1.0.md`. The same failure reproduces on the untouched supplied baseline, so it is not caused by R7E.

After deselecting only that baseline-missing-document test, the repository was run in four partitions to stay within the execution timeout:

```text
Group 0: 620 passed
Group 1: 542 passed
Group 2: 624 passed, 1 deselected
Group 3: 481 passed, 1 skipped
---------------------------------
Total : 2267 passed, 1 skipped, 1 baseline-only deselected
```

The real Owner worktree must run the ordinary full repository pytest after patch application; no permanent deselection is introduced by this patch.

### Static validation

```text
py_compile: PASS
compileall : PASS
git diff --check: PASS
```

### Accepted-source gate

Final R7E Training Studio canonical-text SHA-256 (LF/CRLF portable):

```text
f02ba417cceb78989543cfd55f0f78e79a3997a26ff37d14b1dd7a1d58bd2c6d
```

`tests/test_task051_r7a_source_gate.py` is intentionally rebased to this authorized R7E Product source and hashes universal-newline canonical text so Windows `core.autocrlf` cannot create a false drift failure.

## Remaining gate

Windows Human Acceptance with a real DBD recording is mandatory. In particular:

- PyAV native runtime/package loading;
- prompt initial preview;
- smooth normal playback;
- responsive ±1 frame / ±1 second / ±10 second controls;
- rewind / fast-forward behavior;
- no stale source frame painting;
- ROI/frame alignment;
- clean window shutdown.

No TASK-051 completion is claimed before that gate passes.
