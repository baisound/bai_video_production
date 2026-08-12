# TASK-010 — Resolve Assembly MVP Detailed Design Ver.1.0

- Date: 2026-08-12
- Base release: `v0.19.0`
- Product architecture: `PRODUCT-ARCH-001`
- Governance: `DEV-4`
- Implementation branch target: `feature/task-007-012-technical-mvp`

## 1. Objective

Compile an approved TASK-007 Edit Plan through TASK-022 timing into an Automation-owned Resolve assembly and execute only after an explicit external-write authorization.

## 2. Contract

### Inputs

Approved Edit Plan, exact rational timeline rate/origin, optional approved TASK-006 subtitle plan, optional generic audio placement contracts, source/normalized media bindings and its probed frame rate.

### Outputs

Deterministic `BAI_AUTO_*` assembly plan/hash, exact timeline mapping, optional subtitle/audio execution state, and idempotent assembly result.

### Safety / ownership

Never mutate a human Timeline. Only `BAI_AUTO_*` Timeline names are allowed. Real write requires explicit runtime authorization. Existing matching marker => no-op; conflicting/partial deterministic Timeline => fail closed. Source frame rate is mandatory and may never be substituted with timeline FPS. Subtitle/audio scripting semantics remain native validation gates.

## 3. Determinism and Evidence

Canonical JSON uses stable ordering and SHA-256 identity. Unknown external/native state is never guessed. Hashes identify plan/report content; file-system paths are excluded from persisted QA/Evidence where not required. Retry is allowed only where the operation is demonstrably idempotent.

## 4. Failure semantics

Validation, authorization, state conflict, data-integrity and external-dependency failures are distinct. Destructive or external writes fail closed. A quality failure that is itself a valid measurement is represented as a FAIL report rather than hidden as an exception.

## 5. Unified Application Integration

- User-facing classification: `USER_FACING` / `OPERATOR_FACING`
- Integration state at start: `BACKEND_CAPABILITY_ONLY`
- Target integration state at exit: `INTEGRATION_DESIGNED`
- User Entry Point: `BAI Video Production.exe`
- Shell / Workspace Location: `Edit Workspace > Apply Approved Plan + External Integration > DaVinci Resolve`
- Project Context: reuse current Project; do not make the user reselect project context between editing stages.
- Asset Context: bind current source/normalized Asset and downstream artifacts by canonical IDs/checksums.
- Timeline/Edit Plan Context: carry TASK-007 plan identity through TASK-010/011/012.
- Primary User Flow: Project -> Media -> Edit approval -> Resolve assembly -> Render QA -> Editor handoff.
- Running/Progress UX: Shell shows queued/running/completed/failed stage and immutable result identity.
- Success UX: show next enabled stage and Evidence/report summary.
- Failure UX: show structured error code, non-destructive recovery instruction and affected stage.
- Cancel/Retry/Recovery: cancellation before external mutation; idempotent retry only when marker/hash proves state; ambiguous partial external state requires inspection/recovery.
- Open/Save/Import/Export UX: native file/folder chooser; no typed-path-only normal workflow.
- Settings / Provider configuration: reuse Product settings; no new credentials are created by these tasks.
- Background worker lifecycle: Shell owns helper lifecycle; no user-managed localhost/terminal process.
- Review / Approval: explicit human review before any destructive/external edit application.
- External application interaction: Resolve/Cubase is bounded and visible; no silent writes.
- CLI / localhost role: internal/diagnostic only; no normal-user CLI added.
- Keyboard / Accessibility / Focus: review state and errors must not rely on color alone; native dialogs must foreground correctly.
- Native Windows acceptance: On Windows with the supported Resolve version: use real 30/60/30000-1001 media, verify source ranges and end-frame semantics, create BAI_AUTO Timeline only, import reviewed SRT into expected subtitle track, validate generic audio placement when requested, save/reopen, rerun and prove marker-based no-op. Interrupt after Timeline creation to verify partial-Timeline recovery UX.

## 6. Test strategy

1. deterministic/hash fixtures;
2. authorization and human-review negative tests;
3. boundary/range/timebase tests;
4. schema validation plus packaged-schema equality;
5. idempotency and partial-state tests where external mutation exists;
6. full Product regression;
7. compileall and `git diff --check`;
8. native Windows/Resolve/Cubase Evidence before `NATIVE_VALIDATED`.

## 7. Non-goals

This slice does not implement TASK-005 scene intelligence, TASK-008 multimodal scoring, TASK-026 creative audio-placement generation, a finished Unified Desktop Shell, or unverified DAW/NLE automation beyond the named bounded contracts.
