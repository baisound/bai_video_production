# TASK-036 — Minimum Editing Application Service Contract Ver.1.0

- Date: 2026-08-13
- Status: `AUTOMATED_INTEGRATION_FOUNDATION_PASS / NATIVE_GATE_PENDING`
- Visual contract: `VREW_PREMIERE_RESOLVE_NLE`
- External native truth: TASK-011 / TASK-012 / Windows shell gates remain separate

## 1. Why this integration slice exists

The backend capabilities were already individually implemented, but a user-facing editing application cannot be considered integrated if Human CUT/KEEP review, Edit Plan approval, Resolve preparation, render QA and EDITOR_WORK handoff live as disconnected service objects.

This slice introduces a bounded application composition root without creating a second editing core.

## 2. Composition

```text
Task036EditingApplication
  ├─ DesktopEditingCoordinator
  │    └─ ShellApplicationService / stage-aware command gate
  ├─ Task036ReviewFacade
  │    └─ TASK-024 Cut Candidates -> TASK-007 Human Review
  ├─ DesktopEditingProjectionService
  │    └─ Transcript / Subtitle / CUT overlay / Timeline blocks
  ├─ Task036ResolveWorkflowFacade
  │    └─ TASK-010 compile + exact one-shot Resolve apply confirmation
  └─ Task036PostResolveWorkflowFacade
       ├─ TASK-011 native-render request handoff
       ├─ Render QA identity binding
       └─ TASK-012 deterministic EDITOR_WORK creation
```

## 3. Human edit review -> workflow authority

CUT/KEEP gestures immediately change the deterministic draft projection.

Final Edit Plan approval remains a separate Human Final Authority action. After approval, the exact `plan_sha256` is bound into `EditingSessionState`, enabling `resolve.assembly.prepare` at the Application Service layer. This closes the earlier gap where UI review could complete without advancing the workflow command surface.

## 4. Resolve wiring

`Task036ResolveWorkflowFacade.compile_assembly()` reuses TASK-010 and performs no external mutation.

Before apply:

- exact `BAI_AUTO_*` Timeline required;
- non-empty Resolve Project required;
- target Project/Timeline is bound into Shell context;
- a one-shot confirmation is bound to Edit Plan hash, Assembly hash and exact target hash.

Apply delegates to the injected TASK-010 adapter and passes explicit external-write authorization only after Shell confirmation has been consumed.

Changing Project/Timeline after confirmation causes authorization failure before adapter execution.

## 5. Render boundary

The Desktop application can now produce an exact TASK-011 native-gate request:

- Resolve sandbox Project;
- exact Automation-owned Timeline;
- expected duration frames;
- exact rational Timeline rate;
- explicit external-write authorization required.

It **does not** claim real native render completion. TASK-011 real-machine Evidence remains required before final product wiring is labeled native validated.

## 6. Render QA binding

A RenderQAReport may bind only when:

- TASK-010 apply is recorded complete;
- expected duration equals the applied Assembly;
- Timeline rate equals the applied Assembly.

PASS exposes `handoff.create`; FAIL exposes QA inspection/recovery rather than silently continuing.

## 7. EDITOR_WORK wiring

After exact PASS QA, `handoff.create` delegates to TASK-012 `EditorHandoffService`.

The Shell state then records the deterministic handoff manifest hash and reaches `HANDOFF / NONE`.

Host path is runtime-only and is not persisted in workflow Evidence.

## 8. Crash recovery

`DesktopEditingApplicationCheckpointStore` extends the Shell-only checkpoint by preserving in-progress Human CUT/KEEP decisions.

It persists:

- canonical Shell/editing identities;
- Cut Candidate manifest hash;
- CUT/KEEP decisions;
- selected candidate / playhead;
- approved plan identity and Human approver when applicable.

It never persists:

- one-shot confirmation tokens;
- background job objects;
- media bytes;
- arbitrary host paths.

Recovery requires the caller's current canonical Cut Candidate manifest. Identity mismatch fails closed.

## 9. Automated acceptance

Required automated acceptance now includes:

1. candidate review immediately updates Timeline projection;
2. plan approval advances stage authority;
3. partial review survives crash-safe recovery;
4. approved plan survives recovery without recreating authorization tokens;
5. Resolve target change invalidates confirmation;
6. confirmed fake-adapter TASK-010 apply advances to render stage;
7. exact native-render gate request is generated without mutation;
8. mismatched QA rate/duration is rejected;
9. PASS QA enables deterministic EDITOR_WORK creation;
10. handoff completion reaches `next_recommended_action=NONE`.

## 10. Remaining native blockers

- TASK-011 real DaVinci Resolve render gate
- TASK-012 real Cubase round-trip gate
- TASK-036 Windows pywebview/WebView2 layout/DPI/focus/packaging acceptance

No PowerShell/JSON may remain in the final normal-user acceptance route after these gates close.
