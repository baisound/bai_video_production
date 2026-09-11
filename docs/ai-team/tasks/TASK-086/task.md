# TASK-086 — Release Metadata / CHANGELOG Policy Simplification

## Status and authority

- Status: `IMPLEMENTED_LOCAL_VALIDATED_COMMIT_READY`
- Profile: `DEV-3 HIGH ASSURANCE`
- Authority: Owner instruction on `2026-09-11` to loosen the BAI VIDEO PRODUCTION CHANGELOG rule and update GitHub Actions.
- Base: `76491758583ca17a0a26e41b09e13a6242e8b0c9`
- Branch: `codex/task-086-relax-changelog-policy`

## Problem

The current pull-request check requires `CHANGELOG.md` for any Product source,
schema or Windows-tool change. That serializes unrelated ordinary PRs and makes
the shared file a routine merge bottleneck. Dependency-only edits to
`pyproject.toml` are also classified as Product changes even when the Product
version is unchanged.

## Bound policy

1. Keep `CHANGELOG.md` as the canonical release history.
2. Ordinary feature, fix, test, schema, tooling and documentation PRs do not
   need to edit or reserve it.
3. Version constants must be internally consistent on every PR.
4. Compare the actual consistent Product version at the PR base and head. Only
   an actual version-value change requires `CHANGELOG.md` in the diff and an
   exact heading for the new version.
5. Missing/unreadable refs, missing version values and inconsistent base, head
   or working-tree version values fail closed.
6. Actor identity does not exempt a version bump from release metadata.
7. The workflow checks out the exact PR head before comparing the supplied base
   and head identities, so working-tree consistency is checked against the
   candidate that the policy evaluates.

## Allowed files

- `tools/ci/check-release-metadata.py`
- `tests/test_release_metadata_check.py`
- `.github/workflows/release-metadata-check.yml`
- `.github/pull_request_template.md`
- `docs/ai-team/tasks/TASK-086/task.md`
- `docs/ai-team/current-state.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/task-index.md`

No Product runtime, shared Lock registry, `CHANGELOG.md`, version constant,
Release, Deploy or Production state is changed by this unit.

## Acceptance

- ordinary source/tool/schema changes pass without `CHANGELOG.md`;
- a dependency-only `pyproject.toml` change passes when the version is stable;
- a real version bump without `CHANGELOG.md` fails;
- a real version bump with the matching release heading passes;
- current version mismatch and invalid refs fail cleanly;
- workflow and PR guidance express the same policy;
- focused tests, syntax/static checks, diff scope review and independent-style
  Critic/Judge review pass before publication.

## Local completion evidence

- Exact base/current remote main read-back: `76491758583ca17a0a26e41b09e13a6242e8b0c9`.
- Changed scope: the exact eight Allowed Files above; `CHANGELOG.md`, Product
  version constants, runtime source, shared Lock registry and BAI Development OS
  are unchanged.
- Focused policy plus OSS readiness regression: `25 PASS`.
- Python compile, direct no-version-change checker execution and `git diff
  --check`: `PASS`.
- Workflow contract coverage verifies the renamed `release-metadata` job, exact
  PR-head checkout, exact base/head arguments and removal of actor exemption.
  Hosted GitHub Actions execution remains pending until Draft PR publication.
- Critic: `APPROVE`, unresolved `Critical / High / Medium / Low = 0 / 0 / 0 / 0`.
- Tester: `PASS`. Judge: `COMMIT_READY`.
- Successful final test root:
  `C:\Users\user\AppData\Local\Temp\task086-final-focused-r2-a65032c98fe7495c928a5f19a99f34ed`.
- Preserved diagnostic roots: `task086-release-metadata-fdde5680e9394045923238011d9d0eb4`,
  `task086-release-metadata-r2-a1e13e4867764507957e82397b534822`
  and `task086-final-focused-acc49d47beb7465da9841c021db78c97`
  beneath the same system Temp root. The last root records a collection-only
  dependency failure before the successful existing-site-packages rerun.
- Native, Provider, paid, Release, Deploy and Production effects: `NOT_EXECUTED`.
