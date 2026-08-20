# TASK-051 R7H — Implementation and Verification Evidence

## Result

`LOCAL_IMPLEMENTATION_PASS / WINDOWS_PACKAGED_AND_REAL_MEDIA_HUMAN_ACCEPTANCE_REQUIRED`

## Implemented scope

- Added `dbd_training_diagnostics.py` with EXE-relative `BAI_DIAGNOSTICS.ENABLE` opt-in, asynchronous bounded JSONL writing, five-generation/20 MiB rotation, `latest.jsonl`, privacy-minimized path identities and secret-key redaction.
- Replaced decoder-worker `root.after(...)` delivery with a one-slot Python mailbox. Worker callbacks perform no Tk API calls. Real Tk drains the mailbox on its own `root.after` loop and invokes painting only on the UI thread.
- Preserved latest-frame-wins behavior and stale-source rejection.
- Added structured playback/decoder/mailbox/Tk-render diagnostics shared by all five R7G video surfaces.
- Added per-feature/player identities for HUD Calibration, Video Learning, Visual Registration, Notification Learning and Trivia Mining.
- Removed silent shared-playback exception swallowing in favor of structured ERROR evidence plus bounded user-facing status.
- **Confirmed and fixed a real Tk renderer defect:** base64 PGM text plus forced `format="PGM"` reproduced `TclError: image format "PGM" is not supported`. `PersistentPreviewFrame.tk_photo_data()` now returns raw binary PGM bytes and Tk auto-detects the `P5` header. The same real-Tk contract PASSes after the fix.
- Extended R7 packaged smoke to create the diagnostics marker beside the EXE, exercise real hidden Tk `PhotoImage` rendering and verify `PACKAGED_TK_SMOKE_PASS` in `diagnostics/latest.jsonl`.

## Local verification

### TASK-051

```text
xvfb-run -a python -m pytest -q tests/test_task051*.py
61 passed
```

### TASK-049 / TASK-050 / TASK-051 bounded regression

```text
xvfb-run -a python -m pytest -q tests/test_task049*.py tests/test_task050*.py tests/test_task051*.py
310 passed
```

### Real Tk renderer contract

The test was deliberately run with a real Tk interpreter under Xvfb. Before the raw-PGM fix it reproduced:

```text
TclError: image format "PGM" is not supported
```

After the fix:

```text
1 passed
```

### Broad repository regression

The repository snapshot contains one pre-existing README link failure because `docs/design/TASK-006_SUBTITLE-WORKSPACE_詳細設計_Ver1.0.md` is absent. The same failure reproduces on the pre-R7H R7G baseline and is not modified by R7H.

With only that exact pre-existing test excluded, the split broad regression is:

```text
Group 0: 620 passed
Group 1: 546 passed
Group 2: 626 passed, 1 deselected (the pre-existing README-link test)
Group 3: 483 passed, 1 Windows-only skipped
Total: 2275 passed / 1 Windows-only skipped / 1 known-baseline deselected
```

### Static validation

```text
python -m compileall -q src/ai_video_production tools/task051 : PASS
git diff --check                                           : PASS
```

LF->CRLF messages are Git working-copy warnings only; `git diff --check` returns PASS.

## Target-platform gates still required

- `git apply --check` and patch application on the Owner's current Windows worktree.
- Focused R7H tests on that worktree.
- Normal Training Studio EXE rebuild.
- R7 packaged smoke on Windows, including hidden real-Tk render and EXE-relative diagnostics evidence.
- Real DBD video Human Acceptance on all five shared playback surfaces.
- Marker ON/OFF behavior and privacy review of `diagnostics/latest.jsonl`.

## Safety boundary

No release, deploy, external provider action, model download, paid execution or teacher-data semantic change is authorized or performed by R7H.
