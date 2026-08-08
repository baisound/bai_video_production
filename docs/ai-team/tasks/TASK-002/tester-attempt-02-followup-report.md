# TASK-002 — Tester Attempt 02 Follow-up Report

## Decision

`PASS_FOR_FINAL_LIVE_EVIDENCE / NOT_TASK_COMPLETE`

## Automated regression

- Full project suite: `74 / 74 PASS`.
- Python compileall across source/tests/WSL helper code: PASS.
- Canonical vs packaged Resolve/IPC/WSL report Schema parity: PASS.
- Package `0.2.2` wheel build: PASS.
- Installed-wheel execution outside source checkout: PASS.

## Safety/negative coverage added

- Existing non-sandbox Project blocks mutation.
- Existing Project whose name cannot be positively verified blocks mutation before media/timeline behavior.
- Newly created sandbox Project whose identity cannot be re-verified stops before subsequent mutation.
- Fail-closed sandbox errors remain Schema-valid `mutation_error` Evidence and keep a non-zero exit code.
- Supervisor preserves exact Schema-valid worker refusal Evidence rather than replacing it with generic failure JSON.
- WSL2 report refuses missing unauthenticated rejection and endpoint changes.
- WSL2 client requires HTTP 401 for unauthenticated access before measuring authenticated calls.

## Live Evidence state

Attempt 02 read-only Windows/Resolve Evidence is accepted. Sandbox behavior and WSL2-to-Windows topology still require target-machine execution; they are not simulated as PASS by local tests.
