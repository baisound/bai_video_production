# TASK-022 — Verification

- Package: `0.5.0`
- Status: `LOCAL_TARGETED_VERIFIED / NATIVE_WINDOWS_FULL_REGRESSION_PENDING`

## Completed checks

- compileall for `src` and `tests`: PASS;
- `git diff --check`: PASS;
- exact NTSC `30000/1001` 10-second mapping: 300 frames PASS;
- exact 2x playback duration mapping: PASS;
- affine source/normalized forward and reverse boundary mapping: PASS;
- Win32 schema canonical/package semantic equality: PASS;
- invalid range, binding, duplicate and overlap guards: implemented and regression-pinned.

## Native Windows gate

Run the complete suite after installing package 0.5.0. Expected test count is `263`. TASK-022 remains incomplete until that run and compileall pass.
