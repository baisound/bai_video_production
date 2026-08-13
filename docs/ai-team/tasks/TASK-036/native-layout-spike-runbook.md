# TASK-036 — Native Layout Spike Runbook

- Date: 2026-08-13
- Mutation class: UI-only / no Product external write
- Native environment: Windows
- Dependency change authorization: separate from this runbook

## Purpose

Prove the chosen `pywebview -> EdgeChromium/WebView2` host can render the BAI professional NLE shell before wiring business capabilities.

## Preflight

1. Work on a feature branch/worktree; never protected `main`.
2. Preserve existing local changes.
3. Confirm Python package imports/tests are green.
4. Install/test `pywebview` only under the explicit dependency-spike decision; do not silently add it to Product dependencies from this runbook.
5. No Resolve/Cubase mutation is part of this spike.

## Run

```powershell
python -m ai_video_production.task036_shell_cli
```

## Visual acceptance

- native top-level window, not external browser;
- no user-visible localhost URL;
- dark professional NLE appearance;
- top Project/Workspace bar;
- left Transcript / Cut Candidate panel;
- central Viewer;
- right Inspector / AI panel;
- bottom multi-track Timeline;
- workspace buttons update through the bounded Python bridge;
- window remains usable at 1366x768 and 1920x1080;
- Windows 150% scaling remains legible;
- keyboard focus is visible;
- close does not leave a helper browser/server process.

## Security acceptance

Inspect the JS bridge and prove it exposes only the explicitly allowlisted spike methods. No arbitrary Python attribute/shell/file execution capability is permitted.

## Evidence

Record:

- OS build;
- Python version;
- pywebview version;
- renderer identity;
- WebView2 runtime version;
- resolution/DPI;
- launch/close result;
- screenshots;
- focus/keyboard result;
- errors.

A successful layout spike is not `SHELL_INTEGRATED` and does not close TASK-036.

## Read-only preflight helper

Before launching the window, run:

```powershell
.\tools\windows\run-task036-native-layout-spike.ps1
```

This reports whether Python can discover `pywebview` and whether an installed WebView2 runtime directory can be found. It does not install either dependency and does not claim the renderer is validated.

After review, launch explicitly:

```powershell
.\tools\windows\run-task036-native-layout-spike.ps1 -Launch
```

The operator must still confirm the actual renderer/window behavior and complete the Windows acceptance matrix. Preflight availability is not `NATIVE_VALIDATED` evidence.
