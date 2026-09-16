# TASK-096/A1 CI Consistency Correction — 2026-09-16 r02

- PR: `#560`
- Failed run: `35056681158`
- Failed matrix: Ubuntu and Windows / Python 3.11, 3.12, and 3.13
- Shared failure: `tests/test_development_os_consumer_baseline.py::test_product_canonical_docs_keep_release_state_consistent_with_architecture_228`
- Failure count per matrix: one; the remaining test suites passed in each job

## Cause

TASK-096 changed the canonical `Package` field in `docs/ai-team/current-state.md`
from `0.24.2` to `0.24.3`, while `PROJECT.md` still owns `0.24.2` under the
existing Architecture Ver.2.28 consistency contract. Updating `PROJECT.md` or the
Architecture contract is outside TASK-096's allowed files and tooling
responsibility.

## Correction

Restore the release-governance fields in `current-state.md` to their exact
pre-TASK-096 values. Keep the bounded TASK-096 tooling-unit entry and its exact
v0.24.3 source-base identity. No implementation, build output, version metadata,
CHANGELOG, tag, Release, or Product behavior changes.

## Verification

- Former failing canonical-document contract plus TASK-096, release hygiene, and
  release-metadata tests: `23 PASS`
- `git diff --check`: `PASS`
- Full native artifact build / installation / publication: `NOT_EXECUTED`

The correction is documentation-only and restores the current repository's
pre-existing source-of-truth boundary instead of expanding TASK-096 into release
architecture synchronization.
