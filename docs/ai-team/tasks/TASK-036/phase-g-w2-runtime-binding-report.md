# TASK-036 Phase G W2 Runtime Binding Report

- Date: 2026-08-13
- Status: `W2_DOWNSTREAM_RUNTIME_BOUND / FULL_E2E_PENDING`
- Product completion claim: **NOT MADE**

## Implemented boundary

The native pywebview Shell can now continue from Human-approved Cut Review through the existing TASK-010/011/012 Application Services without accepting adapters, host paths, Resolve targets or external-write authority from JavaScript.

- the trusted desktop composition root binds the exact Resolve adapter, source binding, frame rate, sandbox Project and runtime-only render/handoff inputs before launch;
- the bridge exposes only fixed allowlisted operations;
- Resolve compile is non-mutating;
- Resolve apply uses the existing Shell one-shot confirmation bound to the exact Project, Timeline, Edit Plan and Assembly identities;
- JavaScript passes only the one-shot `confirmation_id` for apply and cannot replace the target, adapter or source path;
- Render QA and EDITOR_WORK creation consume only trusted objects/paths already bound in the Python runtime;
- no host path is returned by workflow status.

## Native UI

The Shell now has one stage-aware `Continue` action. It displays the exact `next_recommended_action` and invokes only the corresponding allowlisted bridge operation. External Resolve apply still presents the exact Python-created target confirmation before consuming the one-shot token.

## Remaining W2 gaps

- Project open, media ingest, local transcription, Subtitle Workspace and Cut Candidate generation are not yet composed into the packaged runtime entrypoint;
- the packaged entrypoint still launches the bounded demo composition unless a trusted W2 runtime is supplied;
- real native render execution must return a trusted TASK-011 QA report before binding;
- final packaged conversation-free `Open Project -> ... -> EDITOR_WORK` has not run.

Therefore `SHELL_INTEGRATED`, TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS` and `MINIMUM_EDITING_PRODUCT_MVP_PASS` remain unclaimed.

## Verification

- focused workflow/runtime/Shell/Resolve/post/package tests: `26 passed`;
- Windows full regression: `782 passed, 1 skipped` (the skip is the intentional non-Windows contract test);
- WSL2 Ubuntu full regression: `783 passed`;
- corrected one-dir package built with PyInstaller `6.22.0` and the project virtual environment;
- packaged EXE SHA-256: `370938272d23c6f7a9ab34ef62beaac7be4bf1fdf59514ea9c0091085c5e1934`;
- packaged native top-level window launch and normal close: `PASS`;
- the frozen module graph contains `task036_workflow_runtime` and the pywebview hooks.

Machine-readable Evidence: `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-runtime-binding.json`.
