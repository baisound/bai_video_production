# TASK-063 R01 / read-only LC01 implementation evidence

Date: 2026-09-02

## Binding

- Base: `origin/main@f46179ec2c32d1d81635ff9eaf1ff9c6a1efeee8`
- Branch: `codex/task-063-r01-readonly-lc01-r0`
- TASK-068 ABI: `IMMUTABLE_SECURE_IO_V1`
- DEV profile: DEV-3 HIGH ASSURANCE

## Implemented bounded unit

- `_read_descriptor` now consumes `SecureAuthorityIO.read_json()` for a bounded,
  strict UTF-8, no-follow, opened-identity-checked descriptor snapshot.
- Ambiguous JSON, link/reparse conditions, size violations, and read identity
  changes fail closed with a stable body-free public error.
- Discovery remains read-only and retains the disabled audit projection.
- Focused negatives cover duplicate keys, non-finite numbers, BOM/trailing data,
  controls, depth/size limits, same-bytes/different-inode replacement, and
  hardlinks.

This unit does not mint descriptor/owner pair authority. It does not implement
the TASK-070 secure operation lease, pair publication, mutable CAS, rollback,
cleanup, or directory durability responsibilities. Public receipt/hash data
remains audit evidence only.

## Verification

- `python -m py_compile`: PASS
- fixture JSON parse: PASS
- `git diff --check`: PASS
- host pytest through a package-initialization bypass and worktree-local
  `--basetemp`: 17 PASS
  - strict descriptor negatives: 12 PASS
  - identity/link/read-only and historical focused regressions: 5 PASS
- complete target test-file attempt: 23 PASS / 12 FAIL
  - 10 failures are sandbox ancestor-resolution `PermissionError` at
    `C:\Users\user`; the tested write/readback paths did not execute
  - 2 packaged-entry failures are the same absent `jsonschema` dependency
  - no new focused descriptor test failed
- normal host pytest collection: NOT_EXECUTED because `jsonschema` is absent
- bundled Python pytest route: NOT_EXECUTED because `pytest`/`jsonschema` are absent
- WSL Ubuntu pytest route: NOT_EXECUTED (`Wsl/Service/E_ACCESSDENIED`)
- dependency installation: 0
- native installer/install/repair/uninstall execution: 0

## Remaining gates

- TASK-070 owns descriptor+owner physical-generation authority and write-side
  transaction guarantees.
- TASK-072-A canonical dependency remains absent from current main.
- No TASK-063 corrective completion or Production linkage PASS is claimed by
  this bounded unit.
