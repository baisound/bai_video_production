# TASK-098 A2-R0 Runtime Contract Evidence

- Result: `PASS`
- Date: `2026-09-19 JST`
- Task / Atomic Unit: `TASK-098 / A2-R0 pure FasterWhisper runtime contract`
- Run identity: `20260919T202512+0900`
- Governance: `DEV-3 HIGH ASSURANCE`
- Base/current main: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-universal-wav-review-integration`
- HEAD before A2-R0 commit: `d55949240dd61e665af78402a9d8a28430355ada`

## Scope and contract result

- Implemented immutable request and request-bound decision values only.
- The decision API accepts one validated request object; digest/device cannot be
  supplied independently.
- Runtime and schema close the exact outcome/reason/effective
  device/effective compute/fallback matrix.
- Request and decision use separate domain-prefixed canonical JSON SHA-256
  preimages and lowercase `sha256:<64 hex>` wire values.
- TTL is `1..300` seconds and freshness is
  `issued_at <= evaluated_at < expires_at`.
- Unknown fields, tamper, mismatched request, invalid constructors and unsafe
  cross-products fail closed.
- Public projections omit all digests and timestamps; authority/effect flags are
  constant `false`.
- No OS/GPU/DLL probe, Provider construction, inference, retry, download, UI,
  persistence or TASK-036 integration is present.

## Changed paths and allowed-files result

- `src/ai_video_production/faster_whisper_runtime_contract.py`
- `schemas/faster-whisper-runtime-contract.schema.json`
- `src/ai_video_production/schema_resources/faster-whisper-runtime-contract.schema.json`
- `tests/test_task098_faster_whisper_runtime_contract.py`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a2-r0-runtime-contract-20260919-r01.md`

All paths are inside the accepted A2-R0 allowed-file set: `PASS`. No package,
version, `CHANGELOG.md`, legacy Provider/config, TASK-036 state machine or
unrelated Task path changed.

## Immutable artifact identities

- canonical schema and packaged mirror SHA-256:
  `1e41f4de6082a92b6cdecdeac97c56a686914f1c58bda371811d30f4ee7acf43`
- runtime contract source SHA-256:
  `dde12e07709d358ca4df2f47fc50c923756abc103707b7ddf7443194978a397e`
- focused test source SHA-256:
  `8362ce85da850205fb5fef5dd7cfb42b2253db39793edb104b38cee2d8cf4693`

## Verification

| Check | Result |
|---|---|
| Python compile | `PASS` |
| schema JSON parse and byte-identical mirror | `PASS` |
| `git diff --check` | `PASS` |
| focused A2-R0 contract tests | `48 PASS` |
| A2-R0 plus direct-dependency regression | `88 PASS` |
| independent Critic first pass | `0 Critical / 2 High / 1 Medium / 0 Low` |
| independent Critic final | `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT` |
| independent Tester | `PASS / 0 unresolved Critical or High` |
| independent Judge | `ACCEPT / commit-ready / 0 Critical / 0 High / 0 Medium / 0 Low` |

Tests used the existing WSL Ubuntu Python environment with `PYTHONPATH=src` and
pytest cache disabled. Windows Python dependency availability remained
`NOT_CONFIRMED`; no package installation occurred.

## Output and residual roots

- Build/runtime/native output: `NONE`.
- Test temporary output: existing WSL/system temporary facility only; no
  intentional test artifact retained.
- Ignored Python bytecode cache under the dedicated Task worktree may remain from
  compile/test execution; it is not durable Evidence or Product output.
- Worktree residual: the dedicated TASK-098 worktree above, intentionally retained.
- Durable external Evidence root:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r0-runtime-contract\20260919T202512+0900`.

## Gates and next action

A2-R1 is a new design/overlap checkpoint. It may inspect the exact TASK-006/023
Provider and TASK-036 operation boundaries, but cannot mutate them until its own
allowed files, successor identity, migration/recovery rules, fake-only test plan
and independent review are accepted. No model/runtime download, real Provider
inference, private audio processing, recording, Dataset adoption, training,
installation, Release, Deploy or Production Activation occurred or is authorized
by this Evidence.
