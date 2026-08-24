# TASK-054 R7 Windows Package Acceptance

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `PARTIAL PASS / ACCESSIBILITY INTERACTION NOT_CONFIRMED`

## Scope

This Atomic Unit verifies the existing authoritative Windows entrypoints after
the R7 `実況・解説AI` integration. It does not install/download a runtime or
model, load private media, invoke a Provider, train, mutate Dataset/Binding,
promote a model, release or deploy.

## Environment

- OS: `Windows 11 10.0.26200`
- Python: `3.12.4`
- PyInstaller: `6.22.0`
- source commit: `ab4725ced0e2fc102c9746a36a23a5f437949b3b`
- canonical entry/spec: `packaging/task049_training_studio_windows_entry.py`
  and `packaging/task049_training_studio.spec`

## Build Evidence

Unified Product shell:

- command: `cmd.exe /d /c build-windows-exe.bat`
- result: `PASS` (`exit 0`)
- output: `builds/BAI Video Production/BAI Video Production.exe`
- size: `16,156,493` bytes
- SHA-256: `C2D233400CBBBD62C8ADB3442B6AC1EA8765C2E7B48752EFBB4C3A15227F09E6`

DbD Training Studio:

```text
Python -m PyInstaller --clean --noconfirm \
  --distpath builds/task049-dist \
  --workpath builds/work/task049-r7 \
  packaging/task049_training_studio.spec
```

- result: `PASS` (`exit 0`)
- output: `builds/task049-dist/BAI DbD Training Studio/BAI DbD Training Studio.exe`
- size: `15,430,791` bytes
- SHA-256: `1873504D657DD216496BBE075C1E092FE1299CCD9E26E66144826E8222059903`
- the existing TASK-049 entry/spec were unchanged; no second entrypoint exists.

## Native Startup Evidence

The new Training Studio EXE was launched normally on Windows. The first
10-second observation did not expose its main window. After 20 more seconds the
same process was alive and responsive:

- process/title: `BAI DbD Training Studio`
- non-zero main-window handle: `74844`
- responding: `True`
- unhandled-exception window/title observed: none

`CloseMainWindow` was accepted and the process exited within the bounded wait.
Packaged startup and graceful shutdown are `PASS`. Initial window availability
took between 10 and 30 seconds and remains a performance concern.

## Interaction Evidence

The Computer Use skill's required safety guidance was read before initialization.
Its Windows helper failed twice during app enumeration with
`helper_unknown_error: setup refresh had errors`. No stale window, screenshot,
coordinate or accessibility index was reused and no unapproved fallback UI
automation was attempted.

- packaged process startup/graceful shutdown: `PASS`
- static tab wiring/callback behavior: existing focused tests `94 PASS`
- native accessibility tree, DPI/scroll rendering and click/keyboard traversal
  of all four R7 subtabs: `NOT_CONFIRMED`
- real Evidence loading, inference, training and Provider execution:
  `NOT_EXECUTED / HUMAN-GATED`

## Regression Evidence

- R7 integration plus R5B-R5E panels: `36 passed in 5.76s`
- TASK-054 plus direct TASK-049 and OSS boundary:
  `716 passed in 41.06s`
- `git diff --check`: `PASS`

## Critic / Boundary Review

1. The package uses the canonical TASK-049 entry/spec and creates no duplicate
   EXE responsibility.
2. Startup creates no training, Provider, Dataset, Binding, Timeline or Resolve
   side effect.
3. A responsive top-level window disproves the original startup exception class
   for this exact build, but does not prove every native interaction.
4. UI interaction is not reported as PASS. Deterministic tests remain separate
   evidence, not a substitute claim of observed clicks.
5. No settings change or installation occurred, so the sleep-window settings /
   installation runbook obligation was not triggered.

## Decision

R7 packaged build/startup acceptance is `PASS` for the exact artifacts above.
Native click/DPI/accessibility interaction remains `NOT_CONFIRMED` and may be
re-observed when the approved helper is healthy. This does not widen R3D, R6B,
promotion, release, deploy or Product Activation authority.
