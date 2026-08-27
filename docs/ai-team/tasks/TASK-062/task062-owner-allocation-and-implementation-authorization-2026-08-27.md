# TASK-062 Owner Allocation and Implementation Authorization Boundary

## Decision and coordinates

- Task: `TASK-062`
- Capability: `BVP-MONTAGE-DESKTOP-UX-001`
- State: `DEPENDENCY_BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED`
- Profile: `DEV_4_FOUNDATION_CRITICAL`; maximum review/fix cycles: `2`
- Design commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- BVP base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`; Registry: `128`
- Reservation: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`
- Target branch: `codex/task-060-task062-authorization-metadata`
- Preflight collision/overlap: `0/0`

Current metadata effect is exactly: task-index `0`, Registry `0`, source `0`,
schema `0`, test `0`, connector activation `0`, runtime/native/paid/external
execution `0`, and Release/Deploy/Production `0`.

## Objective and dependencies

Integrate the released local ConsumerRuntimeService into the single BVP desktop
application with a pinned package manifest, durable Product jobs, verified
TASK-055 admission, and Human review. Hard prerequisites are a released and
SHA-256-pinned wheel and exact current TASK-055 schema/admission identity.

TASK-062 remains blocked until both are read back in the future implementation
Unit. Internet, Codex, ChatGPT, OpenAI API, and paid AI are not Product runtime
dependencies.

| Unit | Goal | Mandatory gate |
|---|---|---|
| `UX-A` | pinned runtime package manifest and load preflight | clean packaged fixture PASS |
| `UX-B` | Product-local job application/worker and verified TASK-055 handoff | fault/cancel/restart PASS |
| `UX-C` | shell workspace, accessible UI, and installer integration | real packaged Windows interaction PASS |

Order: released wheel + TASK-055 -> `UX-A -> UX-B -> UX-C`.

## Closed future implementation Allowed Files

```text
src/ai_video_production/montage_consumer_runtime_package.py
src/ai_video_production/montage_consumer_job_application.py
src/ai_video_production/montage_consumer_commit_transaction.py
src/ai_video_production/montage_consumer_worker.py
src/ai_video_production/montage_review_workspace.py
src/ai_video_production/montage_review_application.py
src/ai_video_production/montage_workspace_projection.py
src/ai_video_production/desktop_shell.py
src/ai_video_production/task036_shell_ui.py
src/ai_video_production/task036_packaged_entry.py
src/ai_video_production/task036_trusted_launcher.py
src/ai_video_production/__init__.py
packaging/task036_shell.spec
packaging/montage-runtime.lock.json
schemas/montage-consumer-runtime-package-manifest.schema.json
schemas/montage-consumer-commit-journal.schema.json
schemas/montage-review-workspace.schema.json
src/ai_video_production/schema_resources/montage-consumer-runtime-package-manifest.schema.json
src/ai_video_production/schema_resources/montage-consumer-commit-journal.schema.json
src/ai_video_production/schema_resources/montage-review-workspace.schema.json
tools/windows/verify-montage-runtime-package.ps1
tests/test_montage_consumer_runtime_package.py
tests/test_montage_consumer_job_application.py
tests/test_montage_consumer_commit_recovery.py
tests/test_montage_consumer_worker.py
tests/test_montage_review_workspace.py
tests/test_montage_review_application.py
tests/test_montage_workspace_ui.py
tests/test_montage_windows_package_contract.py
docs/ai-team/tasks/TASK-062/task.md
docs/ai-team/tasks/TASK-062/task062-owner-allocation-and-implementation-authorization-2026-08-27.md
```

The accepted composition chain is packaged entry -> shell CLI -> trusted
launcher -> `build_trusted_launch` -> `Task036ShellBridge`; therefore the
trusted-launcher entry listed above is the only added composition-root path
from the accepted amendment. If implementation proves
another composition-root edit necessary, STOP and obtain a design amendment.

## Responsibility non-overlap

- Reuse the existing TASK-043 `DurableProductJobService` and Product locks; do
  not replace its algorithms or create another job authority.
- Reuse exact TASK-055 parsers, proposal admission, approved-plan, and Human
  edit evidence contracts; do not alter their schemas.
- Consume TASK-058 contracts only; do not change its store, receipt, transport,
  Profile producer, or readiness behavior.
- Existing BVP Timeline/Human/Resolve gates remain canonical. Runtime success
  advances only to review and never implies approval or Timeline authority.
- Do not reproduce beat analysis, scoring, preset composition, or montage
  generation algorithms inside BVP.

## Acceptance and validation

Package/runtime:

- wheel/dependency hash, resource, version/ABI, shadowing, and source-checkout negatives;
- real packaged local preflight without network, Codex, or API;
- schema/style resource byte verification and upgrade/rollback preservation.

Job/worker:

- double-click idempotency and explicit new-attempt retry identity;
- exact CAS transitions and illegal-transition rejection;
- Project/asset/preset/Profile/runtime drift checks before every effect;
- cancellation and restart at every state with no automatic `UNKNOWN` replay;
- corrupt, escaped, symlinked, or incomplete artifact rejection;
- bounded progress and non-blocking UI; one running job globally/per Project.

TASK-055/review:

- exact BVP input/proposal admission and preset allowlist;
- result/job/request/Project binding and Product save crash recovery;
- transaction fault injection, especially Review admitted before Job success;
- no `SUCCEEDED` before durable Review/marker read-back;
- same-result replay is read-only duplicate; collision fails closed;
- placement decided exactly once; frame bounds and composition binding;
- approved plan passes existing TASK-055 admission;
- Timeline/Resolve mutation count `0`.

Native UX:

- clean-profile packaged Windows launch;
- mouse, keyboard, focus, screen reader, DPI, and long-data behavior;
- start/progress/cancel/recovery/review/reopen flows;
- localized actionable errors without path/trace leakage;
- real UI evidence for controls, focus, scroll, and dead-control negatives.

Command families:

```text
python -m pytest -q -p no:cacheprovider tests/test_montage_consumer_runtime_package.py tests/test_montage_consumer_job_application.py tests/test_montage_consumer_commit_recovery.py tests/test_montage_consumer_worker.py tests/test_montage_review_workspace.py tests/test_montage_review_application.py tests/test_montage_workspace_ui.py tests/test_montage_windows_package_contract.py
python -m pytest -q -p no:cacheprovider tests/test_task043_durable_product_job.py tests/test_task043_product_project.py tests/test_task043_project_save_recovery.py tests/test_task055_montage_contract_recovery.py
python -m compileall -q src tests
python -m pytest -q -p no:cacheprovider
git diff --check
```

Future focused tests are executable only after their owning Unit creates them.
Native/package acceptance requires separately authorized real Windows Evidence.

## DEV-4 responsibilities

- Builder: one UX Unit, exact Allowed Files, exact-head local Evidence.
- Critic: independent supply-chain, state-machine, UX, privacy, and authority review.
- Tester: independent fault/dependency/regression and authorized native execution.
- Judge: exact immutable Evidence with unresolved Critical/High `0/0`.

## Prohibited and stop conditions

Prohibited: TASK-055 schemas; ConsumerRuntimeService algorithm duplication or
changes; TASK-058 store/receipt/Profile source; Timeline/Resolve application;
real Product Projects; credentials/providers/paid calls; runtime downloads by
the shipped Product; Release, Deploy, Production activation; automatic approval
or unknown-job replay; any CLI-only substitute for the unified desktop UX.

Stop on unreleased/unverified wheel, missing TASK-055 identity, ambiguous
Product root, runtime SKILL-instruction parsing, arbitrary UI path, automatic
`UNKNOWN` retry, proposal persistence without TASK-055 admission, second
Timeline, private-data leakage, shared-lock overlap, Resolve publish/apply,
composition-root expansion, or any Allowed Files expansion.

## Expiry and later activation

Accepted-design, main, Registry, Task/branch/PR/path/blob, package, or dependency
drift; Critical/High finding; Owner revocation; or forbidden effect expires this
boundary. Future implementation and native gates require separate exact Owner
authority after canonical metadata activation and dependency read-back.
