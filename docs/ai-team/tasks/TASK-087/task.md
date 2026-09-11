# TASK-087 — Fast PR CI / Release-Train Full Regression

## Status and authority

- Status: `IMPLEMENTED_LOCAL_VALIDATED_DRAFT_PUBLICATION_PENDING`
- Profile: `DEV-3 HIGH ASSURANCE`
- Authority: Owner instruction on `2026-09-11` to adopt release-branch and
  release-time full regression instead of running the full suite on every push.
- Allocation base: `4cda0b418324fc24c3f871cc27a9e92340653021`
- Finalization parent/current main: `19140f230cbb1b95d7f21e4f116fdc70a79e5b38`
- Branch: `codex/task-087-release-train-ci`

## Bound design

1. Ordinary PR and main pushes run one Ubuntu/Python 3.13 Fast CI job.
2. Fast CI always runs stable repository/readiness checks, every changed Python
   test and tests corresponding by filename or direct reference to changed
   Product source, schemas, tools and test fixtures. Dependency manifests and
   shared pytest configuration conservatively select every test on the single
   Fast CI environment; an unmapped Product change does the same instead of
   silently accepting baseline-only coverage. It also runs compileall.
3. The existing six-environment full suite is preserved in a reusable Full
   regression workflow.
4. Full regression runs on pushes to `integration/**` and `release/**`, manual
   invocation, a weekly main safety net and as a blocking prerequisite of the
   formal Release workflow.
5. A new commit/tree receives a new run; an older green result never certifies
   changed source.
6. Explicit DEV-3/DEV-4, security, native, package or other high-risk gates may
   require Full regression earlier and remain authoritative.
7. Release publication cannot begin until all six reusable matrix jobs pass for
   the exact supplied annotated tag.

## Allowed files

- `.github/workflows/ci.yml`
- `.github/workflows/full-regression.yml`
- `.github/workflows/release.yml`
- `.github/workflows/monthly-release-readiness.yml`
- `.github/pull_request_template.md`
- `tools/ci/run-fast-tests.py`
- `tests/test_ci_fast_selection.py`
- `tests/test_oss_readiness.py`
- `CONTRIBUTING.md`
- `docs/ai-team/tasks/TASK-087/task.md`
- `docs/ai-team/current-state.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/task-index.md`

No Product runtime, version, CHANGELOG, Provider, paid, native, Release, Deploy
or Production effect is authorized by this implementation unit.

## Acceptance

- ordinary workflow has no six-environment matrix or unconditional full pytest;
- selector behavior and output-root safety are unit tested;
- full workflow retains all prior Linux/Windows/Python/FFmpeg/installer checks;
- integration/release/manual/weekly triggers are explicit;
- formal Release calls and waits for exact-ref Full regression before build and
  publication;
- workflow contract tests, focused regression, compileall and diff scope pass;
- unresolved Critical/High review findings are zero before Draft publication.
