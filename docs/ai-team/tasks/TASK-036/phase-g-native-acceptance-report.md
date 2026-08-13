# TASK-036 — Phase G Native Acceptance Report

- Date: 2026-08-14
- Status: `W0_PARTIAL / W1_PARTIAL / W2_PACKAGED_NATIVE_E2E_PASS`
- Product completion claim: **NOT MADE**

## Passed in the real Windows environment

- native pywebview window using EdgeChromium/WebView2 `151.0.4129.78`;
- professional NLE layout at observed `1600x900` and `1366x768` window sizes;
- workspace bridge update and visible keyboard focus;
- HTML-reachable allowlisted Project, Media and EDITOR_WORK native chooser controls;
- Media selection and all tested cancel paths return focus to the Shell and terminate the chooser child process;
- selection remains ephemeral and starts no ingest, Project open or handoff operation;
- reproducible PyInstaller one-dir bundle and windowed EXE launch without a terminal;
- two simultaneous instances without a shared localhost port collision;
- normal close terminates all owned WebView2 processes;
- Unicode install-path launch;
- packaged EXE path length 166 launch.

## Findings and remaining gates

- packaged EXE path length 245 fails because an internal `_cffi_backend` path exceeds the Windows filename/path limit; an explicit supported-install-path policy is required;
- clean-user-profile startup is not yet tested;
- missing-WebView2 recovery/bootstrap is not yet tested;
- the full 100/125/150/200% DPI and mixed-monitor matrix is incomplete;
- Windows screen-reader smoke is incomplete;
- W2 now passes in the real packaged Windows application: trusted launch, TASK-003 ingest, cached TASK-006 FasterWhisper with no network/model download, Subtitle Workspace, TASK-024 candidates, Human plan approval, exact TASK-010 Resolve apply, TASK-011 native Render QA and atomic TASK-012 EDITOR_WORK all completed in one Shell session; final `next_recommended_action` was `NONE`.

W2 is now `SHELL_INTEGRATED / PACKAGED_NATIVE_E2E_PASS` at the scoped workflow gate. Overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS` and `MINIMUM_EDITING_PRODUCT_MVP_PASS` remain unclaimed until the W0/W1 findings and Phase G restart/Context Cost boundaries are closed or formally parked.

## Evidence

- `evidence/native/phase-g-task036-20260813-01/task036-native-shell-phase-g.json`
- `evidence/native/phase-g-task036-packaging-20260813-01/task036-w0-w1-evidence.json`
- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-packaged-native-e2e.json`
