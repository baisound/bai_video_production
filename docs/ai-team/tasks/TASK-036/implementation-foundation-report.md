# TASK-036 — Desktop Shell Foundation Implementation Report

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED / PHASE_G_NATIVE_W0_W1_PARTIAL`
- Scope: transport-neutral shell authority boundary + native layout spike only
- Product wiring: NOT CLAIMED
- Native Windows validation: PARTIAL — see `phase-g-native-acceptance-report.md`
- One-dir Windows packaging: REAL LAUNCH PASS / W0 REMAINS PARTIAL

> Phase G supersession note: the original foundation snapshot below is retained as implementation history. Native dialogs and reproducible one-dir packaging have since been added and executed; the current truth is `phase-g-native-acceptance-report.md` and `windows-native-acceptance-matrix.md`.

## Implemented

New Product files:

- `src/ai_video_production/desktop_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_cli.py`

New tests:

- `tests/test_task036_desktop_shell.py`
- `tests/test_task036_shell_ui.py`

The foundation implements the previously designed Shell/Application Service boundary without adding a GUI dependency to the Product package.

## Authority / safety semantics

The new shell core provides:

- allowlisted Shell command registry;
- command risk/category metadata owned by Python Product code, not JavaScript;
- exact Project identity and monotonic context revision checks;
- stale command rejection;
- one-shot confirmation tokens for `EXTERNAL_MUTATION` and `HUMAN_FINAL_AUTHORITY` commands;
- confirmation binding to command type, Project context and upstream hashes;
- confirmation invalidation on Project/Asset context change;
- one-shot consumption before downstream mutation dispatch, so an ambiguous failure cannot be silently retried with the same confirmation;
- background job snapshots and unsafe-close guard;
- deterministic/path-free ShellSnapshot identity;
- no arbitrary shell/process/file bridge.

## UI spike

`task036_shell_ui.py` contains an embedded-WebView NLE layout spike based on the Owner direction:

- Vrew-style Transcript / text-entry editing affordance;
- Premiere/Resolve-style Viewer / Inspector / Timeline organization;
- dark professional dense layout;
- video, subtitle, source audio, SE and narration tracks;
- AI shown as a structured Inspector assistant rather than the primary canvas.

The spike uses optional `pywebview` only at runtime. It does not add/install the dependency and does not perform Product mutations.

## Native spike command

After formal native-spike authorization and manual installation/packaging of the candidate dependency:

```powershell
python -m ai_video_production.task036_shell_cli
```

Required Evidence remains `windows-native-acceptance-matrix.md` and ADR-036-001.

## Not implemented in this foundation

- real Project persistence integration;
- TASK-003 media ingest binding;
- TASK-006 transcript/subtitle binding;
- TASK-024/TASK-007 candidate/review binding;
- TASK-010 Resolve application binding;
- TASK-011 render/QA binding;
- TASK-012 handoff binding;
- pywebview dependency/package metadata;
- Windows executable packaging;
- real file/folder dialog consolidation;
- WebView2 runtime bootstrap.

These remain the next implementation slices after automated validation and R0 native closure.

## Automated validation result

Executed after adding the shell core, bridge/layout spike and projection service:

```text
TASK-036 shell core/UI focused tests: 13 passed
TASK-036 projection focused tests: 3 passed
Full Product regression: 511 passed
python -m compileall -q src tests: PASS
```

The initially extracted cross-platform ZIP represented several tracked Unicode document names as `#Uxxxx` aliases. The OSS readiness test therefore failed before Product behavior was evaluated. In the isolated validation copy only, equivalent Unicode aliases were restored and the full regression then passed at `511 passed`. This packaging/extraction artifact is not part of the TASK-036 patch.

## Stage-aware command authority hardening — 2026-08-13

Added `DesktopEditingCoordinator` and a stage-aware command policy hook in `ShellApplicationService`.
The minimum editing state now narrows both visible and executable Shell commands. A future-stage action such as `render.start` is rejected by the Application Service even if a caller manually fabricates the command instead of using the UI.

Every upstream workflow identity change advances the Shell Project context revision and invalidates outstanding one-shot external mutation/Human Final Authority confirmations. This prevents a confirmation prepared against one Edit Plan/Assembly state from being replayed after the session changes.

No GUI toolkit dependency or external mutation was added by this hardening slice.
