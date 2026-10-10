# TASK-106 Atomic Unit A — Builder Evidence

Run identity: `builder-atomic-unit-a-20261011-01`

Result: `PASS / FIX CYCLE 1 BUILDER CANDIDATE / INDEPENDENT RE-REVIEW PENDING`

## Identity and authority

- Active Project: BAI VIDEO PRODUCTION
- Active Task: TASK-106 Planning Generation Deadlock Recovery
- Atomic Unit: A — Failure Classification and Shell Recovery
- Governance: DEV-4 FOUNDATION CRITICAL
- Worktree: `C:\Users\user\.codex\worktrees\task106-planning-deadlock\bai-video-production`
- Branch: `codex/task-106-planning-generation-deadlock`
- HEAD / base / observed `origin/main`:
  `8d96406f34f0fc0d2c9e84622a5aa5c9f971c422`
- Initial pre-reconciliation base:
  `a5caf3668c7e248ac5bb8819279e82c8b3f13778`
- Commit, push, PR, merge, Release, Deploy and Production Activation: not performed

Dependencies remain TASK-027 canonical Proposal storage, TASK-036 Planning
facade/Shell, and TASK-102 `PMST-R009` writer admission. No dependency or
authority boundary was changed.

## Builder candidate

The candidate:

- consumes each confirmation once and never retries inference automatically;
- classifies an apply-time `OSError` through exact canonical Proposal read-back;
- reprojects an exact committed Proposal as `COMMITTED_READBACK`;
- returns distinct non-retryable typed errors for confirmed absence and
  unreadable/conflicting canonical state without exposing the raw OS message;
- makes the V6.1.1 Planning action single-flight and clears busy state in
  `finally` after success, cancellation or failure;
- uses fixed Japanese public-safe Planning error copy;
- synchronizes pane/button/`aria-busy`/global Planning-AI readiness state.

It does not claim durable cross-process exactly-once provider execution.

## Changed-path and scope audit

Observed dirty paths after implementation, all within Atomic Unit A Allowed
Files:

- `docs/ai-team/tasks/TASK-106/task.md`
- `docs/ai-team/tasks/TASK-106/atomic-unit-a-design.md`
- `docs/ai-team/tasks/TASK-106/evidence/builder-atomic-unit-a-20261011.md`
- `src/ai_video_production/task036_planning_generation_application.py`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_planning_generation_application.py`
- `tests/test_task036_v611_interaction_contract.py`

Shared lock helpers, schemas, `planning_application.py`,
`production_proposal_store.py`, `task036_trusted_launcher.py`, and unrelated
Product paths were not modified. `git diff --check` returned `PASS` with no
output.

## Verification

All tests used fake adapters and local temporary project roots. No provider,
model, network, native Product, build, package or installer was invoked.

1. New failure/interaction cases:
   - command: focused pytest selection for `apply_os_error` and Planning
     single-flight behavior;
   - result: `PASS` — 5 passed, 50 deselected;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-atomic-a-20261011-01\pytest-new-tests`.
2. Allowed related regression set:
   - files: Planning generation application, V6.1.1 interaction contract,
     Shell UI, trusted launcher tests;
   - result: `PASS` — 171 passed in 30.14 seconds;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-atomic-a-20261011-02\pytest-focused`.
3. Direct `py_compile` preflight:
   - result: `NOT_CONFIRMED` because the sandbox denied creation of
     `src/ai_video_production/__pycache__` in the separately attached worktree;
   - no source mutation occurred from this attempt;
   - successful pytest collection/execution subsequently parsed and exercised
     the changed Python modules.

Both resolved test roots are beneath the OS-provided user temporary root, are
not drive-root children, were unique to this TASK-106 operation, and remain as
intentional residual test artifacts pending ordinary environment cleanup.

## Independent review fix cycle 1

The first independent review returned the Builder candidate for correction:

- Critic: `REJECT`, Critical/High/Medium/Low = `0/0/3/0`;
- Tester: `FAIL / RETURN`, Critical/High/Medium/Low = `0/0/4/0`.

The bounded response within the original Allowed Files is:

1. Home initialization and Home refresh now update the global Planning-AI
   header from a read-only four-RPC readiness helper. Successful central
   AI-model settings save and Settings close also refresh the same header.
2. Missing selection maps to `未設定`; a configured selection with a
   connection/route/model blocker maps to `要確認`. `設定済み`, `生成中` and
   `準備中` remain distinct.
3. `provider_execution_started` remains false during adapter factory and prompt
   preparation and changes immediately before the `generate` invocation.
4. Recovery-negative tests cover Project drift, connection/route/policy drift,
   deterministic identity conflict and raw-error suppression without a second
   adapter call or successful response.
5. An Event-controlled overlapping apply test holds the first provider call,
   starts a contended second apply, commits the first exact Proposal, injects a
   Windows `EDEADLK`-shaped `OSError` for the second guard, and proves one
   provider call, one complete Proposal, idempotent exact read-back and consumed
   confirmations.

Fix-cycle verification:

1. New and directly affected cases:
   - result: `PASS` — 12 passed, 49 deselected in 3.10 seconds;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-fix-cycle1-20261011-03\pytest-new`.
2. Full Allowed related regression set:
   - result: `PASS` — 177 passed in 27.06 seconds;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-fix-cycle1-20261011-04\pytest-focused`.
3. Final primary/fallback lifecycle and header-mapping rerun:
   - result: `PASS` — 3 passed, 17 deselected in 1.86 seconds;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-fix-cycle1-20261011-05\pytest-lifecycle`.
4. Final full Allowed related regression after unknown-selection handling:
   - result: `PASS` — 177 passed in 34.72 seconds;
   - root: `C:\Users\user\AppData\Local\Temp\bvp-task106-fix-cycle1-20261011-06\pytest-focused`.
5. `git diff --check` after the fix cycle:
   - result: `PASS` with no output.

No fix-cycle test command failed. The earlier sandbox-blocked direct
`py_compile` attempt remains recorded above as `NOT_CONFIRMED`; it was not
silently reclassified. All seven run-specific temporary roots remain
intentional residual artifacts. No provider, model, network, native Product,
build, package, installer, commit or push effect occurred.

## Current-main reconciliation

Current reconciliation run identity:
`builder-current-main-reconcile-20261011-04`

External Evidence checkpoint history:

- `builder-current-main-reconcile-20261011-04` is retained as immutable
  historical Evidence. Its copied header incorrectly retained the initial
  Builder run identity and is not the latest checkpoint.
- `builder-current-main-reconcile-correction-20261011-05` is the corrected and
  latest current-main reconciliation checkpoint.

The owned TASK-106 diff was safely preserved, the worktree was fast-forwarded
to merged PR607 current main, and the owned diff was restored. Final identities
are branch `codex/task-106-planning-generation-deadlock` with HEAD, base and
observed `origin/main` all equal to
`8d96406f34f0fc0d2c9e84622a5aa5c9f971c422`.

Reconciliation audit confirmed both change sets remain present:

- TASK-106 typed Planning apply recovery, single-flight UI, public-safe
  Planning errors and Home/header lifecycle remain in the owned diff;
- current-main PR607 folder selection uses fixed public Japanese errors for
  folder and media operations, and its native `FolderBrowserDialog` roots at
  `MyComputer`;
- `native_file_dialog.py`, `test_native_file_dialog.py` and all other PR607
  paths are clean current-main content and were not modified by TASK-106;
- the only dirty paths remain the seven original Allowed Files.

Reconciliation verification:

- suite: the four TASK-106 related test files plus
  `tests/test_native_file_dialog.py`;
- result: `PASS` — 191 passed in 39.09 seconds;
- root:
  `C:\Users\user\AppData\Local\Temp\bvp-task106-current-main-reconcile-20261011-07\pytest-reconcile`;
- `git diff --check`: `PASS` with no output;
- reconciliation test failures: none.

The new root is OS-temp-contained, is not a drive-root child, is bound to this
reconciliation run and remains an intentional residual test artifact. No
native dialog was opened because the native-dialog tests use injected runners.

## Candidate artifact hashes

- `src/ai_video_production/task036_planning_generation_application.py`:
  `sha256:1b9786c605740f70abaa0c1eb9ff7a51a55aaf2e3ba8354f859653bf861d2b15`
- `src/ai_video_production/task036_shell_v611.py`:
  `sha256:5be6db2e410061d93a7178cd067ea139899b5f8048f491e34a961a1f3561e02b`
- `tests/test_task036_planning_generation_application.py`:
  `sha256:0723037f57d1746625d5ffe96e13169b5529801b678b3e2cdf97e44b9f140652`
- `tests/test_task036_v611_interaction_contract.py`:
  `sha256:e728c8ec1b34601f772b37679acf7674167e3cb8898c3acc1222fa1fa87bbc89`
- `docs/ai-team/tasks/TASK-106/task.md`:
  `sha256:b35415fe39e7ec8d97a7b63776c794bf2d5e09664b08e048eebeb98488c30e04`
- `docs/ai-team/tasks/TASK-106/atomic-unit-a-design.md`:
  `sha256:d9295726f0c444434f003eaabcffd995d2f5d702c3af0c868705866032b123aa`

Current-main reconciliation anchors, observed but not modified by TASK-106:

- `src/ai_video_production/native_file_dialog.py`:
  `sha256:099bea363c622b1b76f3e5617da2a0e941102993d1c9b5355c9a426f64fde377`
- `tests/test_native_file_dialog.py`:
  `sha256:8c7def6a64d8fab0020f2418dfc03abee8b6f6da5b5c7481963f7fc816a697f4`
- `tests/test_task036_shell_ui.py`:
  `sha256:b137d2a3632d499ec63a29e152729a2ef220079252c2178d1fb08b14b7965c30`
- `tests/test_task036_trusted_launcher.py`:
  `sha256:288b8337f5f4d486bbfacc4e261e90d7572ba57d9ef6c681aed39f9aa6801c8d`

## Gates and next action

Unresolved Critical/High Builder findings: zero known. All returned Critic and
Tester findings have a bounded code-and-test response, but the Builder cannot
self-accept them. DEV-4 still requires independent Tester/Critic re-review of
this current-main reconciled candidate followed by a Judge decision. PR607
folder-chooser reconciliation is complete at current main
`8d96406f34f0fc0d2c9e84622a5aa5c9f971c422`; it is no longer a pending
dependency. Human GO, paid/provider execution, native Product execution,
commit/push/PR/merge, Release, Deploy and Production Activation remain blocked
or outside this Atomic Unit.
