# P-UX-2L Recovery Checkpoint

Date: 2026-08-24
Task: TASK-036 / P-UX-2L
Governance: DEV-3 HIGH ASSURANCE
State: RECOVERY / TECHNICAL NO-GO

## Repository checkpoint

- Branch: `codex/task-036-pux2l-subtitle-cut-controls`
- Checkpoint base HEAD: `3b7f425e1934fdf44c74dfd34c55b871716386e1`
- Product code HEAD: `f5a3d9bcc6e50223db2c090d8e840303e00cd6d1`
- Worktree at checkpoint: clean except user-owned untracked `tmp/`
- `tmp/` ownership: user-owned; not read, staged, modified, or deleted
- Push / PR / merge: not performed

## Completed implementation

- Subtitle and first Cut generation use the existing deterministic Product stages.
- Optional Subtitle route is preserved for the first Cut generation only.
- Cut regeneration after Cut binding or Human approval is rejected before port execution.
- Source, Transcript, Project, Shell context, and session revision are checked at final state CAS.
- Shell context mutators and coordinator CAS share one re-entrant lock.
- Factory failure, wrong application identity, and pre-CAS context drift do not publish canonical Cut state or runtime cache.
- Home/Edit controls share a behavior-tested JavaScript single-flight route.
- Subtitle and Cut bridge calls hold the trusted-launch lifetime through completion and expose closed privacy-safe envelopes.

## Verification evidence

- Local directly impacted regression: 175 passed.
- Independent Tester regression: 201 passed.
- Python compile/AST checks: PASS.
- Embedded JavaScript `node --check`: PASS.
- Node single-flight behavior harness: PASS.
- `git diff --check`: PASS.
- Allowed-file scope: PASS after design synchronization.
- Provider, paid service, model download, Resolve mutation, render, native GUI, and Owner media execution: not performed.

## Independent final review

- Tester: FAIL / Recovery NO-GO.
- Critic: Technical NO-GO.
- Judge: Technical NO-GO / Recovery checkpoint.
- Severity: Critical 0 / High 1 / Medium 0 / Low 0.

### Unresolved High

`Task036PreEditRuntime.generate_cut_candidates()` commits the coordinator Cut state CAS before invoking the optional workflow-runtime publisher. It publishes `self.application` and `_promoted_workflow_runtime` only after that callback returns.

If the publisher raises or blocks:

- the canonical coordinator already contains the Cut manifest;
- the runtime application and promoted workflow runtime remain unpublished;
- the bridge call fails or remains blocked;
- the first-generation-only admission rejects retry;
- a partially published, non-recoverable Cut state remains.

The current tests cover factory failure, wrong application identity, pre-CAS drift with no publisher call, and successful post-CAS publication. They do not cover publisher exception or blocking behavior.

## Recovery reason

The DEV-3 limit of two review/fix cycles was reached. Additional mutation in this session is prohibited by the bounded rework rule. No completion, merge, or release claim is made.

## Next Recovery Atomic Unit

Goal: remove the fallible publisher from the post-CAS mandatory path or redesign Cut state, application, and runtime publication as one recoverable atomic boundary.

Acceptance criteria:

1. Publisher exception cannot leave Cut state advanced by itself.
2. Publisher blocking cannot expose committed Cut state while application/runtime are unavailable.
3. Failure leaves cache unpublished and permits an exact retry.
4. Successful publication occurs exactly once and preserves the trusted runtime identity.
5. Optional Subtitle first-Cut route and post-approval regeneration rejection remain green.
6. Independent Tester, Critic, and Judge agree on C0/H0 before merge eligibility.

## Minimal next-session read list

1. `docs/ai-team/tasks/TASK-036/p-ux-2l-subtitle-cut-controls-design-2026-08-24.md`
2. this checkpoint
3. `src/ai_video_production/task036_pre_edit_runtime.py`
4. `src/ai_video_production/task036_trusted_launcher.py`
5. `src/ai_video_production/desktop_pre_edit_binding.py`
6. `src/ai_video_production/desktop_editing_coordinator.py`
7. `tests/test_task036_pre_edit_runtime.py`
8. directly impacted trusted-launch tests only if the recovery design changes the launcher boundary

## Do not touch on resume

- user-owned `tmp/`
- CHANGELOG or shared lock Registry without a separate exact integration lock
- Provider/model/download configuration
- Audio, Resolve apply, render, export, handoff, or native authority
- BAI Development OS repository
