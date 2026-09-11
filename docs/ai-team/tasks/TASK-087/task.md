# TASK-087 — Fast PR CI / Release-Train Full Regression

## Status and authority

- Status: `CORRECTED_LOCAL_VALIDATED_DRAFT_REVIEW_PENDING`
- Profile: `DEV-3 HIGH ASSURANCE`
- Authority: Owner instruction on `2026-09-11` to adopt release-branch and
  release-time full regression instead of running the full suite on every push.
- Allocation base: `4cda0b418324fc24c3f871cc27a9e92340653021`
- Current integration base: `bd47c7ae4973d441ab471d5900876ee20f69acac`
- Original public candidate: `7a5ba3201c3654346b69ca724ee600b2d0b59fc8`
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

## Current-source corrections and verification

- H1: baseline-only対象は明示した文書path/prefixに固定する。
  `src/`、`schemas/`、`tools/`、`tests/`以外の未知path、native、packaging、
  scripts、requirements lock、config、profiles、root build entrypointは
  単一Fast環境の全testへ倒す。対応不明のProduct変更も同様。
- M1: NUL-safe `--name-status -z --find-renames`を解析し、削除・rename・copy・
  type変更は関連する旧新pathを保持して全testへ倒す。不明・切断statusは失敗で閉じる。
- H3: Fullの各OS/Python jobはrun/attempt付きの新規・canonical・containedな
  operation rootを一度だけ作成する。download、parallel、installerの各childは
  effect直前に不存在を確認し、pytestによる既存childの削除・再利用を許さない。
  Release build/distも同じ仕組みを使い、既存asset名への上書きを拒否する。
- H2: strict tag名、annotated tag object、peeled commit SHAをremote exact refと照合し、
  六Full jobとbuildを同じimmutable commitへ固定してcheckout HEADを確認する。
  Release直前にremote tag objectとpeeled SHAを再照合し、同一tagのworkflowを直列化する。
  外部からのtag強制移動禁止・tag保護は別のHuman/repository Gateであり、直前照合を
  GitHub publicationとの原子的transactionとは主張しない。
- 元の公開候補は45 PASS。修正後focused/negative/workflow/metadata testsは
  **105 PASS / 0 FAIL / 0 SKIP**。合成Git repositoriesは各testの新規一時領域だけを使用。
- 実remote/tag/Releaseへの書込み、native installer、Provider、private dataの実行は
  `NOT_EXECUTED`。これらの権限をローカル合成testから導かない。
- 修正設計Critic C/Hは0/0。最終実装review、修正headのhosted Fast/metadata/Security、
  DEV-3 Full六環境は公開後に確認し、完了前にReady/mergeしない。
- YAMLは構造・依存関係のstatic contractを検証する。GitHub workflow engineによる
  実際の構文/実行受理は新headのhosted実行で確認する。

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
