# TASK-036 — Phase G Native Acceptance Report

- Date: 2026-08-13
- Status: `W0_PARTIAL / W1_PARTIAL / W2_BLOCKED_NOT_WIRED`
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
- W2 does not yet bind the native Shell to the real TASK-003/006/007/010/011/012 end-to-end route.

Therefore `DESKTOP_RUNTIME_SPIKE_PASS`, `DESKTOP_SHELL_NATIVE_UX_PASS`, `SHELL_INTEGRATED`, `NATIVE_VALIDATED` for TASK-036 and `MINIMUM_EDITING_PRODUCT_MVP_PASS` remain unclaimed.

## Evidence

- `evidence/native/phase-g-task036-20260813-01/task036-native-shell-phase-g.json`
- `evidence/native/phase-g-task036-packaging-20260813-01/task036-w0-w1-evidence.json`
