# TASK-110 Atomic Unit A — Implementation Validation

Date: `2026-10-11 JST`

Technical result: `PASS`

## Identity and scope

- Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-110 / A — Stable AI Model Identity Labels`
- operation identity: `task110-atomic-unit-a-20261011-r01`
- worktree:
  `C:\Users\user\.codex\worktrees\task110-model-identity-labels\bai-video-production`
- branch: `codex/task-110-model-identity-labels-20261011`
- base / HEAD before mutation / observed `origin/main`:
  `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04`
- initial dirty state: clean
- changed paths:
  - `docs/ai-team/tasks/TASK-110/task.md`
  - `docs/ai-team/tasks/TASK-110/evidence/atomic-unit-a-implementation-validation-20261011.md`
  - `src/ai_video_production/task036_shell_ui.py`
  - `tests/test_task036_shell_ui.py`
  - `tests/test_task036_v611_interaction_contract.py`
- Allowed Files result: `PASS`

## Implementation result

The Shell no longer assigns model display names from the route's current
ordinal position. It projects the canonical `model_id` only through the
existing `_safe_public_model_label()` boundary and otherwise returns the
generic `登録済みローカルAIモデル` fallback. The selected-model display is
derived from the already projected preferred route, so save-induced priority
reordering cannot rename the same model.

No connection-settings schema, store mutation, route identity, revision/CAS,
frontend save handler or Provider execution behavior changed.

Frozen implementation/test hashes before this Evidence file was added:

- `src/ai_video_production/task036_shell_ui.py`:
  `4556806b2c75ec47c53125b630d08eae64742f06447a2caf7a9191d9a4a6c33e`
- `tests/test_task036_shell_ui.py`:
  `cc952721331df462c1dd1a8612ad697c31fa6d445c962764c94ed2b2a8683e88`
- `tests/test_task036_v611_interaction_contract.py`:
  `4d880f9757d4805b885423d916f93639e6b7faeae8af32671cfc57fa0c2ee1f0`

## Verification

### Red gate

Using the existing dependency-complete Python `3.12.10` environment, the four
new/affected focused cases against the old implementation produced the
expected result:

- `3 FAIL / 1 PASS`
- failures proved ordinal labels, generic selected-model readback and unstable
  route-to-label identity.

An earlier Python 3.13 invocation did not collect tests because `jsonschema`
was unavailable; it is environment bootstrap evidence, not a technical test
result.

### Corrected focused gate

- exact affected cases: `4 PASS`
- elapsed: `1.34 s`

### Related regression

Files:

- `tests/test_connection_settings.py`
- `tests/test_task036_model_selection.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_interaction_contract.py`

Result: `102 PASS` in `2.52 s`.

The first related attempt reported `97 PASS / 5 setup error` because pytest's
`--basetemp` does not recursively create a missing parent. No product case
failed. After creating only the already-authorized operation parent, the same
suite passed in full.

### Static and diff checks

- compileall for the changed source and tests: `PASS`
- `git diff --check`: `PASS`
- scope check: `PASS`

## Output and residual roots

- corrected related-test root:
  `C:\Users\user\AppData\Local\Temp\bai-video-production\TASK-110\atomic-unit-a\20261011-r01\pytest-related`
- compile cache root:
  `C:\Users\user\AppData\Local\Temp\bai-video-production\TASK-110\atomic-unit-a\20261011-r01\pycache`
- red-gate pytest root observed under the OS temporary root:
  `C:\Users\user\AppData\Local\Temp\pytest-of-user\pytest-1919`

All are intentional test residuals. No cleanup is authorized or performed.

## Safety and gates

- Provider/inference/model download: `NOT_EXECUTED`
- billing/generation: `NOT_EXECUTED`
- build/package/installer/Product launch: `NOT_EXECUTED`
- Resolve/Cubase: `NOT_EXECUTED`
- Release/Deploy/Production: `NOT_EXECUTED`
- secret, endpoint or credential display added: `NO`
- commit/push/PR: `NOT_EXECUTED`
- replacement package/native acceptance: separate later gate

## Verdict

Atomic Unit A is `PASS / COMMIT_READY`. The repository worktree remains the
only mutable source copy until the required external Evidence checkpoint is
persisted and read back.
