# TASK-022 — Verification

- Package: `0.5.0`
- Status: `COMPLETED / NATIVE_WINDOWS_FULL_REGRESSION_PASS`

## Owner native-Windows result — 2026-08-10

- package version: `0.5.0`
- pytest: `263 passed in 28.98s`
- compileall: PASS
- decision: native-Windows regression Gate PASS; TASK-022 completed

## Completed checks

- compileall for `src` and `tests`: PASS;
- `git diff --check`: PASS;
- exact NTSC `30000/1001` 10-second mapping: 300 frames PASS;
- exact 2x playback duration mapping: PASS;
- affine source/normalized forward and reverse boundary mapping: PASS;
- Win32 schema canonical/package semantic equality: PASS;
- invalid range, binding, duplicate and overlap guards: implemented and regression-pinned.

## Native Windows gate

Completed on the Owner machine: `263 / 263 PASS` and compileall PASS.
