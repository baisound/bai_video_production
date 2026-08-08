# TASK-002 — Implementation Evidence: Attempt 01 Corrective Package 0.2.1

## Trigger

Owner returned `resolve-spike-evidence.zip` generated on the target Windows workstation.

## Intake

The two returned JSON files were copied verbatim under `evidence/windows-live-attempt-01/` and hashed before corrective edits.

## Implemented correction

- Package version advanced from 0.2.0 to 0.2.1.
- `ResolveModuleLoader.connect()` preserves discovery source on post-discovery errors.
- Resolve worker serializes exact module-source/error semantics.
- Root `resolve.connection` capability row preserves exact failure code/category.
- Windows live runner reports Resolve process/standard bridge preflight and fails completion evidence when no live Resolve root object is obtained.
- Canonical project/task/current-state/design/readme documents were synchronized.

## Verification Evidence

See `evidence/retry-package-0.2.1/`:

- `pytest-final.txt`
- `compileall-final.txt`
- `wheel-build-final.txt`
- `wheel-sha256.txt`
- `installed-wheel-verification.txt`
- `git-diff-check.txt`

## Live Evidence decision

Attempt 01 Windows IPC data is retained as accepted partial evidence. Resolve capability classification is not promoted from the failed connection attempt.
